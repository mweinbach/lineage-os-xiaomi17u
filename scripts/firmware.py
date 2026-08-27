#!/usr/bin/env python3
"""Preserve a local firmware package and its provenance; never flash it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
import zipfile


DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "firmware"
CHUNK_SIZE = 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20_000
MAX_METADATA_BYTES = 64 * 1024


class IntakeError(ValueError):
    """A package cannot be safely accepted without changing existing evidence."""


def _text(value: str, label: str, limit: int = 512) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > limit
        or not value.isprintable()
    ):
        raise IntakeError(f"{label} must be nonempty printable text without outer whitespace")
    return value


def _filename(value: str) -> str:
    _text(value, "filename", 255)
    if (
        value in (".", "..")
        or "/" in value
        or "\\" in value
        or value.endswith(".")
        or value.casefold() == "metadata.json"
    ):
        raise IntakeError("unsafe or reserved firmware filename")
    return value


def _source_url(value: str) -> str:
    _text(value, "source URL", 4096)
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise IntakeError("invalid source URL") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or any(character.isspace() for character in value)
        or "\\" in value
        or (port is not None and port < 1)
    ):
        raise IntakeError("source URL must be HTTPS with a host, no credentials, and no fragment")
    return value


def _checksum(value: str | None) -> str | None:
    if value is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", value):
        raise IntakeError("expected SHA256 must contain exactly 64 hexadecimal characters")
    return value.lower() if value is not None else None


def _open_regular(path: Path):
    """Reject symlinks and nonregular inputs, including FIFOs that could block."""
    if not stat.S_ISREG(path.lstat().st_mode):
        raise IntakeError(f"not a regular file: {path.name}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
    stream = os.fdopen(descriptor, "rb")
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        stream.close()
        raise IntakeError(f"not a regular file: {path.name}")
    return stream


def _signature(details: os.stat_result) -> tuple[int, int, int, int, int]:
    return details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns, details.st_ctime_ns


def _hash_file(path: Path, output=None) -> tuple[str, int]:
    checksum = hashlib.sha256()
    size = 0
    with _open_regular(path) as stream:
        before = _signature(os.fstat(stream.fileno()))
        while chunk := stream.read(CHUNK_SIZE):
            checksum.update(chunk)
            size += len(chunk)
            if output is not None:
                output.write(chunk)
        if before != _signature(os.fstat(stream.fileno())) or before != _signature(path.lstat()):
            raise IntakeError("firmware changed while being read; retry with a stable local file")
    return checksum.hexdigest(), size


def _directory(path: Path) -> Path:
    """Create only real directories, refusing symlinks along the output path."""
    absolute = Path(os.path.abspath(path))
    for parent in [*reversed(absolute.parents), absolute]:
        try:
            parent.mkdir(mode=0o700)
        except FileExistsError:
            pass
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise IntakeError(f"output path contains a symlink or non-directory: {parent}")
    return absolute


def _existing(bucket: Path, expected: dict) -> dict:
    if not stat.S_ISDIR(bucket.lstat().st_mode):
        raise IntakeError("existing checksum directory is a symlink or non-directory")
    with _open_regular(bucket / "metadata.json") as stream:
        raw = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise IntakeError("existing metadata is unexpectedly large")
    try:
        metadata = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise IntakeError("existing metadata is not valid JSON") from exc
    if not isinstance(metadata, dict):
        raise IntakeError("existing metadata is not a JSON object")
    if set(metadata) != {*expected, "collected_at_utc"}:
        raise IntakeError("existing metadata has an unexpected schema")
    for key, value in expected.items():
        if type(metadata.get(key)) is not type(value) or metadata.get(key) != value:
            raise IntakeError(f"existing metadata conflicts with {key}; existing evidence was not changed")
    try:
        timestamp = datetime.fromisoformat(metadata["collected_at_utc"])
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("timestamp must be UTC")
    except (TypeError, ValueError, AttributeError) as exc:
        raise IntakeError("existing metadata has an invalid collection timestamp") from exc
    actual, size = _hash_file(bucket / expected["filename"])
    if actual != expected["sha256"] or size != expected["size_bytes"]:
        raise IntakeError("stored firmware failed integrity verification; existing evidence was not changed")
    return metadata


def _unsafe_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    return (
        not name
        or not name.isprintable()
        or path.is_absolute()
        or ".." in path.parts
        or re.match(r"^[A-Za-z]:", normalized) is not None
    )


def inspect_archive(path: Path) -> dict:
    """Inventory member metadata without extracting or executing any content."""
    members = []
    with _open_regular(path) as stream:
        if zipfile.is_zipfile(stream):
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                for entry in archive.infolist():
                    if len(members) >= MAX_ARCHIVE_MEMBERS:
                        raise IntakeError(f"archive exceeds {MAX_ARCHIVE_MEMBERS} inventory entries")
                    mode = entry.external_attr >> 16
                    kind = "symlink" if stat.S_ISLNK(mode) else "directory" if entry.is_dir() else "file"
                    members.append({
                        "name": entry.orig_filename,
                        "size_bytes": entry.file_size,
                        "kind": kind,
                        "unsafe_path": _unsafe_member(entry.orig_filename),
                    })
            archive_type = "zip"
        else:
            stream.seek(0)
            try:
                with tarfile.open(fileobj=stream, mode="r|*") as archive:
                    for entry in archive:
                        if len(members) >= MAX_ARCHIVE_MEMBERS:
                            raise IntakeError(f"archive exceeds {MAX_ARCHIVE_MEMBERS} inventory entries")
                        kind = "file" if entry.isfile() else "directory" if entry.isdir() else "other"
                        if entry.issym():
                            kind = "symlink"
                        elif entry.islnk():
                            kind = "hardlink"
                        member = {
                            "name": entry.name,
                            "size_bytes": entry.size,
                            "kind": kind,
                            "unsafe_path": _unsafe_member(entry.name),
                        }
                        if entry.issym() or entry.islnk():
                            member["link_target"] = entry.linkname
                            member["unsafe_link_target"] = _unsafe_member(entry.linkname)
                        members.append(member)
                archive_type = "tar"
            except tarfile.TarError as exc:
                raise IntakeError("inspection supports ZIP or TAR (including .tgz/.tar.gz) archives") from exc
    return {"format": archive_type, "member_count": len(members), "members": members}


def intake_firmware(
    source: str | Path,
    *,
    device: str,
    build: str,
    region: str,
    source_url: str | None = None,
    source_kind: str = "url",
    expected_sha256: str | None = None,
    inspect: bool = False,
    artifacts_dir: str | Path = DEFAULT_ARTIFACTS_DIR,
) -> dict:
    """Copy a package once using an atomic directory rename and verify reuse."""
    source = Path(source).expanduser().absolute()
    filename = _filename(source.name)
    expected_sha256 = _checksum(expected_sha256)
    if source_kind not in ("url", "user-provided"):
        raise IntakeError("source kind must be url or user-provided")
    if source_kind == "url" and source_url is None:
        raise IntakeError("source URL is required unless source kind is explicitly user-provided")
    fields = {
        "schema_version": 1,
        "filename": filename,
        "device": _text(device, "device"),
        "build": _text(build, "build"),
        "region": _text(region, "region", 80),
        "source_url": _source_url(source_url) if source_url is not None else None,
    }
    if source_kind == "user-provided":
        fields.update({"schema_version": 2, "source_kind": "user-provided", "origin_verified": False})
    checksum, size = _hash_file(source)
    if size == 0:
        raise IntakeError("firmware package is empty")
    if expected_sha256 is not None and checksum != expected_sha256:
        raise IntakeError(f"SHA256 mismatch: expected {expected_sha256}, got {checksum}")
    fields.update({"sha256": checksum, "size_bytes": size})
    root = _directory(Path(artifacts_dir))
    bucket = root / checksum
    lock = root / f".{checksum}.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise IntakeError(f"intake lock already exists: {lock}; another intake may be active") from exc
    staging = None
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(f"pid={os.getpid()}\n")
        reused = os.path.lexists(bucket)
        if reused:
            metadata = _existing(bucket, fields)
        else:
            staging = Path(tempfile.mkdtemp(prefix=f".{checksum}.intake-", dir=root))
            with (staging / filename).open("xb") as output:
                copied_hash, copied_size = _hash_file(source, output)
                output.flush()
                os.fsync(output.fileno())
            if copied_hash != checksum or copied_size != size:
                raise IntakeError("firmware changed between hashing and copying; nothing was accepted")
            stored_hash, stored_size = _hash_file(staging / filename)
            if stored_hash != checksum or stored_size != size:
                raise IntakeError("temporary firmware copy failed integrity verification; nothing was accepted")
            metadata = {**fields, "collected_at_utc": datetime.now(timezone.utc).isoformat()}
            with (staging / "metadata.json").open("x", encoding="utf-8") as stream:
                json.dump(metadata, stream, ensure_ascii=True, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            if os.path.lexists(bucket):
                raise IntakeError("checksum directory appeared during intake; refusing to overwrite it")
            staging.rename(bucket)
            staging = None
        result = {
            "firmware_path": str(bucket / filename),
            "metadata_path": str(bucket / "metadata.json"),
            "reused": reused,
            "metadata": metadata,
        }
        if inspect:
            result["archive"] = inspect_archive(bucket / filename)
        return result
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="existing local firmware package")
    parser.add_argument("--device", required=True, help="verified product/device identifier")
    parser.add_argument("--build", required=True, help="exact declared firmware build identifier")
    parser.add_argument("--region", required=True, help="verified firmware region, not an inferred country")
    parser.add_argument("--source-kind", choices=("url", "user-provided"), default="url", help="provenance mode; user-provided explicitly permits an unknown download origin")
    parser.add_argument("--source-url", help="HTTPS source provenance; required unless source-kind is user-provided")
    parser.add_argument("--expected-sha256", help="independently supplied SHA256, when available")
    parser.add_argument("--inspect", action="store_true", help="include ZIP/TAR member inventory without extraction")
    args = parser.parse_args(argv)
    if args.source_kind == "url" and args.source_url is None:
        parser.error("--source-url is required unless --source-kind user-provided is explicitly selected")
    try:
        result = intake_firmware(
            args.file,
            device=args.device,
            build=args.build,
            region=args.region,
            source_url=args.source_url,
            source_kind=args.source_kind,
            expected_sha256=args.expected_sha256,
            inspect=args.inspect,
        )
    except (IntakeError, OSError, zipfile.BadZipFile, EOFError) as exc:
        print(f"firmware intake: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
