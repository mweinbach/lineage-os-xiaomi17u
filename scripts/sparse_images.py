#!/usr/bin/env python3
"""Inspect or reconstruct numbered Android sparse overlays without flashing.

Format: AOSP system/core 68be0c2c0006a0740d0b1809abe4717308f90d15,
libsparse/sparse_format.h. Overlay semantics were checked against LineageOS
extract-utils 19a1e68e47bbe9ba446e167b2d402953bd7e0c87, sparse_img.py.
There is no runtime dependency on either checkout. Checksums embedded in sparse
images are deliberately unsupported and rejected, never silently ignored.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys
import tempfile

from artifact_files import publish_new_directory


MAGIC = 0xED26FF3A
HEADER = struct.Struct("<I4H4I")
CHUNK_HEADER = struct.Struct("<2H2I")
RAW, FILL, DONT_CARE, CRC32 = 0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4
CHUNK_NAMES = {RAW: "raw", FILL: "fill", DONT_CARE: "dont_care"}
BUFFER_SIZE = 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024**3
MAX_PIECES = 1024
MAX_CHUNKS = 100_000
DISK_RESERVE_BYTES = 64 * 1024**2


class SparseError(ValueError):
    """The inputs cannot safely be reconstructed as one sparse overlay set."""


def _absolute(path) -> Path:
    return Path(os.path.abspath(Path(path).expanduser()))


def _directory(path: Path):
    """Require existing real directories, including every path ancestor."""
    for parent in [*reversed(path.parents), path]:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise SparseError(f"path contains a symlink or non-directory: {parent}")


def _signature(details):
    return (details.st_dev, details.st_ino, details.st_size,
            details.st_mtime_ns, details.st_ctime_ns)


def _unchanged(entry):
    path, stream, signature = entry
    _directory(path.parent)
    if (_signature(os.fstat(stream.fileno())) != signature
            or _signature(path.lstat()) != signature):
        raise SparseError(f"input changed while being read: {path.name}")


def _ordered_paths(paths, expected_pieces):
    if type(expected_pieces) is not int or not 1 <= expected_pieces <= MAX_PIECES:
        raise SparseError(f"expected pieces must be between 1 and {MAX_PIECES}")
    paths = [_absolute(path) for path in paths]
    if len(paths) != expected_pieces:
        raise SparseError(f"expected {expected_pieces} pieces, received {len(paths)}")
    indexed = []
    family = None
    for path in paths:
        match = re.fullmatch(r"(.+\.img)\.(0|[1-9][0-9]*)", path.name)
        if not match or not path.name.isprintable():
            raise SparseError("inputs must be numbered image paths such as super.img.0")
        current = (path.parent, match[1])
        if family is not None and current != family:
            raise SparseError("all pieces must have the same image basename and directory")
        family = current
        indexed.append((int(match[2]), path))
    indexed.sort()
    if [number for number, _ in indexed] != list(range(expected_pieces)):
        raise SparseError("split sequence must start at 0 with no gaps or duplicates")
    return [path for _, path in indexed]


@contextmanager
def _inputs(paths, expected_pieces):
    with ExitStack() as stack:
        entries = []
        inodes = set()
        for path in _ordered_paths(paths, expected_pieces):
            _directory(path.parent)
            details = path.lstat()
            if not stat.S_ISREG(details.st_mode):
                raise SparseError(f"input is not a regular file: {path.name}")
            descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
            stream = stack.enter_context(os.fdopen(descriptor, "rb"))
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or _signature(opened) != _signature(details):
                raise SparseError(f"input changed while opening: {path.name}")
            identity = (opened.st_dev, opened.st_ino)
            if identity in inodes:
                raise SparseError("different pieces must not alias the same input inode")
            inodes.add(identity)
            entries.append((path, stream, _signature(opened)))
        yield entries


def _parse(entry, max_output_bytes, max_chunks, output=None):
    path, stream, signature = entry
    _unchanged(entry)
    stream.seek(0)
    digest = hashlib.sha256()

    def read(size):
        data = stream.read(size)
        if len(data) != size:
            raise SparseError(f"truncated sparse data in {path.name}")
        digest.update(data)
        return data

    magic, major, minor, header_size, chunk_header_size, block_size, blocks, count, checksum = (
        HEADER.unpack(read(HEADER.size))
    )
    if magic != MAGIC:
        raise SparseError(f"invalid sparse magic in {path.name}")
    if (major, minor) != (1, 0):
        raise SparseError("only Android sparse version 1.0 is supported")
    if header_size < HEADER.size or chunk_header_size < CHUNK_HEADER.size:
        raise SparseError("sparse header sizes are smaller than the version 1.0 fields")
    if not block_size or block_size % 4 or not blocks:
        raise SparseError("block geometry must be nonempty with a block size divisible by 4")
    expanded = block_size * blocks
    if expanded > max_output_bytes:
        raise SparseError(f"expanded image exceeds the {max_output_bytes}-byte size limit")
    if not count or count > max_chunks:
        raise SparseError(f"invalid chunk count or set exceeds {MAX_CHUNKS} chunks")
    if checksum:
        raise SparseError("nonzero sparse header checksum is unsupported; verification is required")
    if header_size + count * chunk_header_size > signature[2]:
        raise SparseError("truncated sparse file: declared headers exceed input size")
    read(header_size - HEADER.size)
    cursor = 0
    ranges = []
    counts = dict.fromkeys(CHUNK_NAMES.values(), 0)
    bytes_by_type = dict.fromkeys(CHUNK_NAMES.values(), 0)
    for _ in range(count):
        kind, reserved, chunk_blocks, total_size = CHUNK_HEADER.unpack(read(CHUNK_HEADER.size))
        read(chunk_header_size - CHUNK_HEADER.size)
        if reserved:
            raise SparseError("chunk reserved field must be zero")
        if kind == CRC32:
            raise SparseError("CRC32 sparse chunks are unsupported; verification is required")
        if kind not in CHUNK_NAMES:
            raise SparseError(f"unknown sparse chunk type: {kind:#x}")
        if not chunk_blocks or cursor + chunk_blocks > blocks:
            raise SparseError("chunk block range is empty or exceeds declared output geometry")
        length = chunk_blocks * block_size
        expected_data = {RAW: length, FILL: 4, DONT_CARE: 0}[kind]
        if total_size != chunk_header_size + expected_data:
            raise SparseError("chunk total size does not match its type and block count")
        if stream.tell() + expected_data > signature[2]:
            raise SparseError(f"truncated chunk payload in {path.name}")
        counts[CHUNK_NAMES[kind]] += 1
        bytes_by_type[CHUNK_NAMES[kind]] += length
        if kind != DONT_CARE:
            ranges.append((cursor * block_size, (cursor + chunk_blocks) * block_size, path.name))
            if output is not None:
                output.seek(cursor * block_size)
        if kind == RAW:
            remaining = length
            while remaining:
                data = read(min(remaining, BUFFER_SIZE))
                if output is not None:
                    output.write(data)
                remaining -= len(data)
        elif kind == FILL:
            pattern = read(4)
            if output is not None:
                tile = pattern * (min(length, BUFFER_SIZE) // 4)
                remaining = length
                while remaining:
                    data = tile[:min(remaining, len(tile))]
                    output.write(data)
                    remaining -= len(data)
        # DONT_CARE never overwrites data from earlier pieces.
        cursor += chunk_blocks
    if cursor != blocks:
        raise SparseError("chunk blocks do not cover the declared output geometry")
    if stream.read(1):
        raise SparseError(f"trailing data after the declared chunks in {path.name}")
    _unchanged(entry)
    return {
        "path": str(path), "name": path.name, "size_bytes": signature[2],
        "sha256": digest.hexdigest(), "block_size": block_size, "total_blocks": blocks,
        "total_chunks": count, "chunk_counts": counts, "bytes_by_type": bytes_by_type,
        "sparse_header_checksum": checksum,
        "identity": dict(zip(("device", "inode", "size", "mtime_ns", "ctime_ns"), signature)),
    }, ranges


def _inspect(entries, max_output_bytes, output=None):
    if type(max_output_bytes) is not int or max_output_bytes < 1:
        raise SparseError("maximum output bytes must be a positive integer")
    records, ranges = [], []
    chunk_budget = MAX_CHUNKS
    geometry = None
    for entry in entries:
        record, writes = _parse(entry, max_output_bytes, chunk_budget, output)
        current = (record["block_size"], record["total_blocks"])
        if geometry is not None and current != geometry:
            raise SparseError("pieces declare different output geometry")
        geometry = current
        chunk_budget -= record["total_chunks"]
        records.append(record)
        ranges.extend(writes)
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if previous[1] > current[0]:
            raise SparseError(f"RAW/FILL overlap between {previous[2]} and {current[2]}")
    for entry in entries:
        _unchanged(entry)
    expanded = geometry[0] * geometry[1]
    written = sum(end - start for start, end, _ in ranges)
    return {
        "schema_version": 1, "format": "android-sparse-split-1.0",
        "piece_count": len(records), "inputs": records,
        "block_size": geometry[0], "total_blocks": geometry[1],
        "expanded_size_bytes": expanded, "written_bytes": written,
        "unwritten_zero_bytes": expanded - written, "write_range_count": len(ranges),
        "checksum_policy": "reject nonzero header checksums and all CRC32 chunks",
    }


def inspect_images(paths, *, expected_pieces, max_output_bytes=MAX_OUTPUT_BYTES):
    """Fully parse and hash inputs without creating any output files."""
    with _inputs(paths, expected_pieces) as entries:
        return _inspect(entries, max_output_bytes)


def _hash_output(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    while data := stream.read(BUFFER_SIZE):
        digest.update(data)
    return digest.hexdigest()


def reconstruct_images(paths, *, expected_pieces, output_dir, parent_sha256,
                       max_output_bytes=MAX_OUTPUT_BYTES):
    """Publish a new directory containing super.raw.img and its JSON receipt.

    The parent package hash is supplied by the caller, not independently linked
    to these input paths. Keep the archive-extraction receipt alongside this one.
    A per-destination exclusive lock coordinates concurrent uses of this tool.
    """
    if not isinstance(parent_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", parent_sha256):
        raise SparseError("parent SHA256 must contain exactly 64 hexadecimal characters")
    destination = _absolute(output_dir)
    _directory(destination.parent)
    if os.path.lexists(destination):
        raise SparseError("output directory already exists; refusing to overwrite evidence")
    lock = destination.parent / f".{destination.name}.sparse.lock"
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    staging = None
    try:
        os.close(descriptor)
        with _inputs(paths, expected_pieces) as entries:
            report = _inspect(entries, max_output_bytes)
            expanded = report["expanded_size_bytes"]
            if shutil.disk_usage(destination.parent).free < expanded + DISK_RESERVE_BYTES:
                raise SparseError("insufficient free disk for expanded image and safety reserve")
            staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=destination.parent))
            image_name = "super.raw.img"
            with (staging / image_name).open("x+b") as output:
                output.truncate(expanded)
                if _inspect(entries, max_output_bytes, output) != report:
                    raise SparseError("input changed between inspection and reconstruction")
                output.flush()
                os.fsync(output.fileno())
                before_hash = _signature(os.fstat(output.fileno()))
                checksum = _hash_output(output)
                if (before_hash[2] != expanded
                        or _signature(os.fstat(output.fileno())) != before_hash):
                    raise SparseError("staged output changed during hashing")
            receipt = {
                **report, "operation": "reconstruct",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "parent_package_sha256": parent_sha256.lower(),
                "parent_linkage": "caller-provided; verify with the separate extraction receipt",
                "origin_verified": False,
                "output": {"name": image_name, "size_bytes": expanded, "sha256": checksum},
                "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "semantics": "nonoverlapping RAW/FILL overlays; DONT_CARE preserves prior data; unwritten bytes are zero",
            }
            with (staging / "receipt.json").open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            for entry in entries:
                _unchanged(entry)
            _directory(destination.parent)
            if os.path.lexists(destination):
                raise SparseError("output directory appeared during reconstruction; refusing to overwrite it")
            publish_new_directory(staging, destination)
            staging = None
        return {"output_dir": str(destination), "receipt": receipt}
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("inspect", "reconstruct"):
        command = subparsers.add_parser(operation)
        command.add_argument("inputs", nargs="+", type=Path, help="explicit numbered image pieces; sorted numerically")
        command.add_argument("--expected-pieces", required=True, type=int, help="count verified from the complete archive inventory")
        command.add_argument("--max-output-bytes", type=int, default=MAX_OUTPUT_BYTES)
        if operation == "reconstruct":
            command.add_argument("--output-dir", required=True, type=Path, help="new directory under an existing real parent")
            command.add_argument("--parent-sha256", required=True, help="parent package SHA256 from the extraction receipt")
    args = parser.parse_args(argv)
    options = {"expected_pieces": args.expected_pieces, "max_output_bytes": args.max_output_bytes}
    try:
        if args.operation == "inspect":
            result = inspect_images(args.inputs, **options)
        else:
            result = reconstruct_images(args.inputs, output_dir=args.output_dir,
                                        parent_sha256=args.parent_sha256, **options)
    except (SparseError, OSError) as exc:
        print(f"sparse images: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
