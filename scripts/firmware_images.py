#!/usr/bin/env python3
"""Extract only image members from a verified intake ZIP, never its installers."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import zipfile

from firmware import (
    CHUNK_SIZE, MAX_ARCHIVE_MEMBERS, MAX_METADATA_BYTES, IntakeError,
    _checksum, _directory, _filename, _open_regular, _signature, _unsafe_member,
)


MAX_IMAGE_BYTES = 64 * 1024**3
IMAGE_MEMBER = re.compile(r"images/([A-Za-z0-9][A-Za-z0-9_-]*\.img(?:\.[0-9]+)?)\Z")


def _existing_directory(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    for parent in [*reversed(absolute.parents), absolute]:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise IntakeError("intake directory contains a symlink or non-directory")
    return absolute


def _intake(path: Path, expected_sha256: str) -> tuple[dict, bytes]:
    with _open_regular(path / "metadata.json") as stream:
        raw = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise IntakeError("intake metadata exceeds size limit")
    try:
        metadata = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise IntakeError("invalid intake metadata JSON") from exc
    if not isinstance(metadata, dict):
        raise IntakeError("intake metadata must be an object")
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] not in (1, 2):
        raise IntakeError("unsupported intake metadata schema")
    if metadata.get("sha256") != expected_sha256 or path.name != expected_sha256:
        raise IntakeError("intake directory and metadata must match expected SHA256")
    if not isinstance(metadata.get("filename"), str):
        raise IntakeError("intake metadata requires a filename")
    _filename(metadata["filename"])
    if type(metadata.get("size_bytes")) is not int or metadata["size_bytes"] <= 0:
        raise IntakeError("invalid intake package size")
    return metadata, raw


def _image_entries(archive: zipfile.ZipFile, max_bytes: int) -> list[zipfile.ZipInfo]:
    entries = archive.infolist()
    if len(entries) > MAX_ARCHIVE_MEMBERS:
        raise IntakeError("archive member count exceeds limit")
    names: set[str] = set()
    images = []
    total = 0
    for entry in entries:
        name = entry.orig_filename
        if name != entry.filename or _unsafe_member(name) or "\\" in name:
            raise IntakeError("archive contains an unsafe member name")
        folded = name.casefold()
        if folded in names:
            raise IntakeError("archive contains duplicate or case-colliding member names")
        names.add(folded)
        mode = entry.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or entry.flag_bits & 1:
            raise IntakeError("archive contains a link, special file or encrypted member")
        if entry.is_dir():
            continue
        if not name.startswith("images/"):
            continue
        if not IMAGE_MEMBER.fullmatch(name) or kind == stat.S_IFDIR:
            raise IntakeError("images/ contains an unsupported member; no installer is extracted")
        if entry.file_size <= 0:
            raise IntakeError("image member is empty")
        total += entry.file_size
        if total > max_bytes:
            raise IntakeError("declared extracted image size exceeds limit")
        images.append(entry)
    if not images:
        raise IntakeError("archive has no supported image members")
    return sorted(images, key=lambda entry: entry.filename)


def extract_images(
    intake_dir: Path, output_dir: Path, *, expected_sha256: str,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> dict:
    """Verify provenance/ZIP CRCs and publish a new directory of inert image files."""
    expected = _checksum(expected_sha256)
    if expected is None or type(max_bytes) is not int or max_bytes <= 0:
        raise IntakeError("expected SHA256 and a positive size limit are required")
    intake_dir = _existing_directory(Path(intake_dir))
    metadata, metadata_raw = _intake(intake_dir, expected)
    output_dir = Path(os.path.abspath(output_dir))
    if os.path.lexists(output_dir):
        raise IntakeError("output already exists; existing evidence was not changed")
    if intake_dir == output_dir or intake_dir in output_dir.parents:
        raise IntakeError("outputs must remain outside immutable intake directory")
    package = intake_dir / metadata["filename"]
    staging = None
    lock = None
    with _open_regular(package) as source:
        signature = _signature(os.fstat(source.fileno()))
        package_hash = hashlib.sha256()
        while chunk := source.read(CHUNK_SIZE):
            package_hash.update(chunk)
        if package_hash.hexdigest() != expected or signature[2] != metadata["size_bytes"]:
            raise IntakeError("package size or SHA256 mismatch")
        source.seek(0)
        with zipfile.ZipFile(source) as archive:
            entries = _image_entries(archive, max_bytes)
            parent = _directory(output_dir.parent)
            required = sum(entry.file_size for entry in entries)
            if shutil.disk_usage(parent).free < required + 64 * 1024**2:
                raise IntakeError("insufficient free space for extracted images")
            lock = parent / ("." + output_dir.name + ".lock")
            try:
                descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                raise IntakeError("extraction lock exists; another operation or retained lock needs inspection") from exc
            os.close(descriptor)
            try:
                staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + "-", dir=parent))
                records = []
                for entry in entries:
                    name = IMAGE_MEMBER.fullmatch(entry.filename).group(1)
                    digest = hashlib.sha256()
                    size = 0
                    with archive.open(entry) as member, (staging / name).open("xb") as output:
                        os.chmod(staging / name, 0o600)
                        while chunk := member.read(CHUNK_SIZE):
                            size += len(chunk)
                            if size > entry.file_size:
                                raise IntakeError("member expanded beyond its declared size")
                            digest.update(chunk)
                            output.write(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                    if size != entry.file_size:
                        raise IntakeError("truncated image member")
                    # Reading to EOF above also makes ZipFile verify the member CRC.
                    with _open_regular(staging / name) as copied:
                        copied_hash = hashlib.sha256()
                        while chunk := copied.read(CHUNK_SIZE):
                            copied_hash.update(chunk)
                    if copied_hash.digest() != digest.digest():
                        raise IntakeError("extracted output failed SHA256 readback")
                    records.append({"archive_member": entry.filename, "path": name,
                                    "size_bytes": size, "sha256": digest.hexdigest(),
                                    "zip_crc32": f"{entry.CRC:08x}", "crc_verified": True})
                if signature != _signature(os.fstat(source.fileno())) or signature != _signature(package.lstat()):
                    raise IntakeError("package changed during extraction")
                with _open_regular(intake_dir / "metadata.json") as current:
                    if current.read(MAX_METADATA_BYTES + 1) != metadata_raw:
                        raise IntakeError("intake metadata changed during extraction")
                receipt = {
                    "schema_version": 1,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "operation": "extract-image-members-only",
                    "parent_package_sha256": expected,
                    "intake_metadata_sha256": hashlib.sha256(metadata_raw).hexdigest(),
                    "intake_provenance": metadata,
                    "image_count": len(records), "images": records,
                    "installers_extracted_or_executed": False,
                    "phone_accessed": False,
                    "notes": "Local integrity only; no publisher authenticity, partition geometry or compatibility claim.",
                }
                (staging / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                if os.path.lexists(output_dir):
                    raise IntakeError("output appeared during extraction; refusing replacement")
                staging.rename(output_dir)
                staging = None
                return receipt
            finally:
                if staging is not None:
                    shutil.rmtree(staging)
                lock.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, required=True, help="existing checksum intake directory")
    parser.add_argument("--expected-sha256", required=True, help="previously verified package SHA256")
    parser.add_argument("--output", type=Path, required=True, help="new private output directory")
    parser.add_argument("--max-image-bytes", type=int, default=MAX_IMAGE_BYTES)
    args = parser.parse_args(argv)
    try:
        receipt = extract_images(args.intake, args.output, expected_sha256=args.expected_sha256,
                                 max_bytes=args.max_image_bytes)
    except (IntakeError, OSError, zipfile.BadZipFile, EOFError, NotImplementedError) as exc:
        print(f"firmware images: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "image_count": receipt["image_count"],
                      "parent_package_sha256": receipt["parent_package_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
