#!/usr/bin/env python3
"""Extract inert image files from a verified fastboot TAR/GZIP intake."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile

if __package__:
    from .artifact_files import publish_new_directory
    from .firmware import (CHUNK_SIZE, MAX_ARCHIVE_MEMBERS, MAX_METADATA_BYTES,
                           IntakeError, _checksum, _directory, _open_regular,
                           _signature)
    from .firmware_images import _existing_directory, _intake
else:
    from artifact_files import publish_new_directory
    from firmware import (CHUNK_SIZE, MAX_ARCHIVE_MEMBERS, MAX_METADATA_BYTES,
                          IntakeError, _checksum, _directory, _open_regular,
                          _signature)
    from firmware_images import _existing_directory, _intake


MAX_IMAGE_BYTES = 64 * 1024**3
MAX_ARCHIVE_BYTES = 128 * 1024**3
MAX_TRAILER_BYTES = 1024**2
IMAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\.img(?:\.[0-9]+)?\Z")


class BoundedTarInfo(tarfile.TarInfo):
    """Bound metadata before tarfile reads GNU/PAX extended header bodies."""

    def _proc_member(self, archive):
        metadata_types = (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME,
                          tarfile.GNUTYPE_LONGLINK, tarfile.SOLARIS_XHDTYPE)
        if self.type in metadata_types and not 0 <= self.size <= MAX_METADATA_BYTES:
            raise IntakeError("extended TAR metadata exceeds size limit")
        return super()._proc_member(archive)

    def _proc_sparse(self, archive):
        raise IntakeError("GNU sparse TAR members are unsupported")

    def _proc_gnusparse_00(self, next, pax_headers, buf):
        raise IntakeError("GNU sparse TAR members are unsupported")

    def _proc_gnusparse_01(self, next, pax_headers):
        raise IntakeError("GNU sparse TAR members are unsupported")

    def _proc_gnusparse_10(self, next, pax_headers, archive):
        raise IntakeError("GNU sparse TAR members are unsupported")


class BoundedReader:
    def __init__(self, stream, limit):
        self.stream = stream
        self.limit = limit
        self.count = 0

    def read(self, size):
        if size < 0:
            raise IntakeError("unbounded decompression read refused")
        data = self.stream.read(min(size, self.limit - self.count + 1))
        self.count += len(data)
        if self.count > self.limit:
            raise IntakeError("decompressed archive exceeds size limit")
        return data


def member_name(entry):
    name = entry.name
    if name.startswith("./"):
        name = name[2:]
    if entry.isdir():
        name = name.rstrip("/")
    if name in ("", ".") and entry.isdir():
        return "."
    if (not name or not name.isprintable() or "\\" in name or ":" in name
            or PurePosixPath(name).is_absolute()
            or any(part in ("", ".", "..") for part in name.split("/"))):
        raise IntakeError("unsafe TAR member path")
    return name


def image_destination(name):
    parts = name.split("/")
    if len(parts) not in (2, 3) or parts[-2] != "images":
        return None
    if not IMAGE_NAME.fullmatch(parts[-1]):
        return None
    return "/".join(parts[:-1]), parts[-1]


def _outside_intake(output, intake):
    if os.path.lexists(output):
        raise IntakeError("output already exists; existing evidence was not changed")
    identity = intake.stat()
    if output == intake or intake in output.parents:
        raise IntakeError("outputs must remain outside immutable intake directory")
    for ancestor in output.parents:
        try:
            if os.path.samestat(ancestor.stat(), identity):
                raise IntakeError("outputs must remain outside immutable intake directory")
        except FileNotFoundError:
            pass


def extract_images(intake_dir, output_dir, *, expected_sha256,
                   max_image_bytes=MAX_IMAGE_BYTES, max_archive_bytes=MAX_ARCHIVE_BYTES):
    """Verify the entire gzip stream and publish only regular .img members.

    TAR metadata is never used to create directories, links, owners or modes.
    Installers, programs and other nonimage files are read only as part of the
    gzip integrity check and are never extracted or executed.
    """
    expected = _checksum(expected_sha256)
    if (expected is None or type(max_image_bytes) is not int or max_image_bytes <= 0
            or type(max_archive_bytes) is not int or max_archive_bytes <= 0):
        raise IntakeError("expected SHA256 and positive byte limits are required")
    intake_dir = _existing_directory(Path(intake_dir))
    metadata, metadata_raw = _intake(intake_dir, expected)
    output_dir = Path(os.path.abspath(output_dir))
    _outside_intake(output_dir, intake_dir)
    package = intake_dir / metadata["filename"]
    with _open_regular(package) as source:
        signature = _signature(os.fstat(source.fileno()))
        digest = hashlib.sha256()
        while block := source.read(CHUNK_SIZE):
            digest.update(block)
        if signature[2] != metadata["size_bytes"] or digest.hexdigest() != expected:
            raise IntakeError("package size or SHA256 mismatch")
        source.seek(0)
        if source.read(2) != b"\x1f\x8b":
            raise IntakeError("only a gzip-compressed TAR is supported")
        source.seek(0)
        parent = _directory(output_dir.parent)
        lock = parent / ("." + output_dir.name + ".lock")
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise IntakeError("extraction lock exists; existing lock preserved") from exc
        os.close(descriptor)
        staging = None
        try:
            staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + "-", dir=parent))
            members = []
            images = []
            names = set()
            prefixes = set()
            total_image_bytes = 0
            total_member_bytes = 0
            with gzip.GzipFile(fileobj=source, mode="rb") as compressed:
                bounded = BoundedReader(compressed, max_archive_bytes)
                with tarfile.open(fileobj=bounded, mode="r|", bufsize=CHUNK_SIZE,
                                  tarinfo=BoundedTarInfo) as archive:
                    for entry in archive:
                        if len(members) >= MAX_ARCHIVE_MEMBERS:
                            raise IntakeError("archive member count exceeds limit")
                        name = member_name(entry)
                        if name.casefold() in names:
                            raise IntakeError("duplicate or case-colliding TAR member")
                        names.add(name.casefold())
                        if not (entry.isfile() or entry.isdir()) or entry.issparse():
                            raise IntakeError("TAR links, sparse members and special files are refused")
                        if entry.size < 0 or (entry.isdir() and entry.size):
                            raise IntakeError("invalid TAR member size")
                        total_member_bytes += entry.size
                        if total_member_bytes > max_archive_bytes:
                            raise IntakeError("declared archive size exceeds limit")
                        members.append({"name": name, "size_bytes": entry.size,
                                        "kind": "directory" if entry.isdir() else "file"})
                        selected = image_destination(name) if entry.isfile() else None
                        if selected is None:
                            continue
                        prefix, basename = selected
                        prefixes.add(prefix)
                        if len(prefixes) != 1:
                            raise IntakeError("multiple image directories are ambiguous")
                        if entry.size <= 0:
                            raise IntakeError("image member is empty")
                        total_image_bytes += entry.size
                        if total_image_bytes > max_image_bytes:
                            raise IntakeError("declared extracted image size exceeds limit")
                        if shutil.disk_usage(parent).free < entry.size + 64 * 1024**2:
                            raise IntakeError("insufficient free space for image extraction")
                        target = staging / basename
                        image_hash = hashlib.sha256()
                        size = 0
                        with archive.extractfile(entry) as member, target.open("xb") as output:
                            os.chmod(target, 0o600)
                            while block := member.read(CHUNK_SIZE):
                                size += len(block)
                                if size > entry.size:
                                    raise IntakeError("image expanded beyond declared size")
                                image_hash.update(block)
                                output.write(block)
                            output.flush()
                            os.fsync(output.fileno())
                        if size != entry.size:
                            raise IntakeError("truncated TAR image")
                        readback = hashlib.sha256()
                        with _open_regular(target) as copied:
                            while block := copied.read(CHUNK_SIZE):
                                readback.update(block)
                        if readback.digest() != image_hash.digest():
                            raise IntakeError("extracted image failed SHA256 readback")
                        images.append({"archive_member": name, "path": basename,
                                       "size_bytes": size, "sha256": image_hash.hexdigest(),
                                       "readback_verified": True})
                    # Drain through tarfile's buffered stream, not the underlying
                    # gzip file: otherwise prefetched trailing data can be missed.
                    # Reading to EOF also checks gzip CRC32 and ISIZE trailers.
                    trailer_bytes = 0
                    while block := archive.fileobj.read(CHUNK_SIZE):
                        trailer_bytes += len(block)
                        if trailer_bytes > MAX_TRAILER_BYTES or any(block):
                            raise IntakeError("unexpected data after TAR end marker")
                    if trailer_bytes < tarfile.BLOCKSIZE:
                        raise IntakeError("missing second TAR end marker")
            if not images:
                raise IntakeError("archive has no supported image members")
            if (signature != _signature(os.fstat(source.fileno()))
                    or signature != _signature(package.lstat())):
                raise IntakeError("package changed during extraction")
            with _open_regular(intake_dir / "metadata.json") as current:
                if current.read(MAX_METADATA_BYTES + 1) != metadata_raw:
                    raise IntakeError("intake metadata changed during extraction")
            receipt = {
                "schema_version": 1,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "operation": "extract-image-members-only",
                "archive_format": "tar-gzip",
                "parent_package_sha256": expected,
                "intake_metadata_sha256": hashlib.sha256(metadata_raw).hexdigest(),
                "intake_provenance": metadata,
                "gzip_stream_crc_verified": True,
                "tar_header_checksums_verified": True,
                "decompressed_archive_bytes": bounded.count,
                "image_count": len(images), "images": images,
                "member_count": len(members), "members": members,
                "installers_extracted_or_executed": False,
                "phone_accessed": False,
                "notes": "Integrity only; publisher authenticity and image AVB verification are separate.",
            }
            (staging / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            publish_new_directory(staging, output_dir)
            staging = None
            return receipt
        finally:
            if staging is not None:
                shutil.rmtree(staging)
            lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-image-bytes", type=int, default=MAX_IMAGE_BYTES)
    parser.add_argument("--max-archive-bytes", type=int, default=MAX_ARCHIVE_BYTES)
    args = parser.parse_args(argv)
    try:
        receipt = extract_images(args.intake, args.output, expected_sha256=args.expected_sha256,
                                 max_image_bytes=args.max_image_bytes,
                                 max_archive_bytes=args.max_archive_bytes)
    except (IntakeError, OSError, EOFError, tarfile.TarError) as exc:
        print(f"firmware TAR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "image_count": receipt["image_count"],
                      "parent_package_sha256": receipt["parent_package_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
