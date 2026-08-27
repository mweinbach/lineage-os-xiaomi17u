#!/usr/bin/env python3
"""Inspect and extract raw Android super images without mounting or executing them.

    python3 scripts/logical_partitions.py inspect --image artifacts/super.raw.img
    python3 scripts/logical_partitions.py extract --image artifacts/super.raw.img \
        --expected-sha256 SHA256 --slot 0 --partition vendor_a \
        --output artifacts/vendor-extraction

Only complete raw images, LP versions 10.0 through 10.2, and LINEAR/ZERO extents
are supported. Extraction requires one physical device, no active overlays or
unknown header flags, all geometry and metadata copies valid, and matching
primary/backup data in every slot. Different slots may
legitimately differ; --slot selects metadata, not a partition suffix or group.
Names are the exact names stored on disk; no slot suffix is added or removed.
Outputs must be in a NEW directory under this workspace's artifacts/ or evidence/.
On failure, partial outputs remain in that new directory without a success receipt.
SHA256 checks prove local integrity, not publisher authenticity or flash safety.

Format reference (read on 2026-08-27): AOSP platform/system/core, refs/heads/main,
commit a3b721a32242006b59cb12bd62c9133632af3a2d, fs_mgr/liblp/{reader.cpp,
utility.cpp,include/liblp/metadata_format.h}:
https://android.googlesource.com/platform/system/core/+/a3b721a32242006b59cb12bd62c9133632af3a2d/fs_mgr/liblp/
Unlike liblp's runtime fallback, this evidence tool does not silently accept a
damaged or disagreeing backup. Its resource and name checks are conservative.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SECTOR_SIZE = 512
GEOMETRY_SIZE = 4096
RESERVED_BYTES = 4096
METADATA_START = RESERVED_BYTES + 2 * GEOMETRY_SIZE
GEOMETRY_MAGIC = 0x616C4467
HEADER_MAGIC = 0x414C5030
SPARSE_MAGIC = 0xED26FF3A
CHUNK_SIZE = 1024 * 1024
MAX_IMAGE_BYTES = 256 * 1024**3
MAX_METADATA_BYTES = 4 * 1024**2
MAX_METADATA_REGION_BYTES = 32 * 1024**2
MAX_METADATA_SLOTS = 32
MAX_TABLE_ENTRIES = 16_384
MAX_LOGICAL_BLOCK_SIZE = 1024 * 1024
FORMAT_COMMIT = "a3b721a32242006b59cb12bd62c9133632af3a2d"

GEOMETRY = struct.Struct("<II32sIII")
HEADER_PREFIX = struct.Struct("<IHHI32sI32s")
DESCRIPTOR = struct.Struct("<III")
PARTITION = struct.Struct("<36sIIII")
EXTENT = struct.Struct("<QIQI")
GROUP = struct.Struct("<36sIQ")
BLOCK_DEVICE = struct.Struct("<QIIQ36sI")
TABLE_FORMATS = {
    "partitions": PARTITION,
    "extents": EXTENT,
    "groups": GROUP,
    "block_devices": BLOCK_DEVICE,
}


class LogicalPartitionError(ValueError):
    """An image or requested output cannot be handled safely."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LogicalPartitionError(message)


def _sha256_argument(value: str | None, *, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None,
             "expected SHA256 must contain exactly 64 hexadecimal characters")
    return value.lower()


def _safe_name(raw: bytes, label: str) -> str:
    name, separator, padding = raw.partition(b"\0")
    _require(not separator or not any(padding), f"{label} has nonzero name padding")
    _require(re.fullmatch(rb"[A-Za-z0-9_]{1,36}", name) is not None,
             f"{label} has an empty, non-ASCII or unsafe name")
    return name.decode("ascii")


def _unique_names(entries: list[dict], label: str, key: str = "name") -> None:
    # Case-folding also protects output on a case-insensitive host filesystem.
    names = [entry[key].casefold() for entry in entries]
    _require(len(set(names)) == len(names), f"{label} contains duplicate or case-colliding names")


def _absolute(path: Path) -> Path:
    _require(".." not in path.parts, "parent traversal is not allowed in input/output paths")
    return Path(os.path.abspath(path))


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _directory_fd(path: Path, *, create: bool = False) -> int:
    """Walk through directory descriptors so no symlink ancestor is followed."""
    path = _absolute(path)
    descriptor = os.open(path.anchor, _directory_flags())
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(component, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _signature(details: os.stat_result) -> tuple[int, int, int, int, int]:
    return details.st_dev, details.st_ino, details.st_size, details.st_mtime_ns, details.st_ctime_ns


class RawImage:
    """One held read-only descriptor, bounded reads, and stable-file checks."""

    def __init__(self, path: Path):
        self.path = _absolute(path)
        self.parent_fd = _directory_fd(self.path.parent)
        self.stream = None
        try:
            descriptor = os.open(
                self.path.name,
                os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=self.parent_fd,
            )
            try:
                details = os.fstat(descriptor)
                _require(stat.S_ISREG(details.st_mode), "input must be a regular file, not a device or pipe")
                _require(METADATA_START <= details.st_size <= MAX_IMAGE_BYTES,
                         f"raw image size must be between {METADATA_START} and {MAX_IMAGE_BYTES} bytes")
                _require(details.st_size % SECTOR_SIZE == 0, "raw image size is not sector-aligned")
                self.before = _signature(details)
                self.size = details.st_size
                self.stream = os.fdopen(descriptor, "rb")
            except BaseException:
                os.close(descriptor)
                raise
        except BaseException:
            os.close(self.parent_fd)
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stream.close()
        os.close(self.parent_fd)

    def unchanged(self) -> None:
        _require(self.before == _signature(os.fstat(self.stream.fileno())),
                 "source image changed while being read")
        current = os.stat(self.path.name, dir_fd=self.parent_fd, follow_symlinks=False)
        _require(stat.S_ISREG(current.st_mode) and self.before == _signature(current),
                 "source image path was replaced while being read")

    def read(self, offset: int, size: int) -> bytes:
        _require(0 <= offset <= self.size and 0 <= size <= self.size - offset,
                 "read extends outside the raw image")
        _require(size <= MAX_METADATA_BYTES, "single read exceeds the bounded buffer limit")
        self.stream.seek(offset)
        value = self.stream.read(size)
        _require(len(value) == size, "truncated raw image")
        return value

    def sha256(self) -> str:
        digest = hashlib.sha256()
        for offset in range(0, self.size, CHUNK_SIZE):
            digest.update(self.read(offset, min(CHUNK_SIZE, self.size - offset)))
        self.unchanged()
        return digest.hexdigest()


def _checksum(raw: bytes, stored: bytes, zero_offset: int | None = None) -> dict:
    if zero_offset is not None:
        raw = raw[:zero_offset] + bytes(32) + raw[zero_offset + 32:]
    computed = hashlib.sha256(raw).hexdigest()
    return {"stored": stored.hex(), "computed": computed, "valid": computed == stored.hex()}


def _geometry(image: RawImage, offset: int, result: dict) -> None:
    raw = image.read(offset, GEOMETRY_SIZE)
    magic, size, checksum, maximum, slots, block_size = GEOMETRY.unpack_from(raw)
    result.update({
        "magic": f"0x{magic:08x}", "struct_size": size,
        "metadata_max_size": maximum, "metadata_slot_count": slots,
        "logical_block_size": block_size,
    })
    _require(magic == GEOMETRY_MAGIC, "invalid geometry magic")
    _require(size == GEOMETRY.size, f"geometry struct size must be {GEOMETRY.size}")
    result["checksum"] = _checksum(raw[:size], checksum, 8)
    _require(result["checksum"]["valid"], "invalid geometry SHA256 checksum")
    _require(SECTOR_SIZE <= maximum <= MAX_METADATA_BYTES and maximum % SECTOR_SIZE == 0,
             "metadata maximum size is zero, unaligned or above the resource limit")
    _require(1 <= slots <= MAX_METADATA_SLOTS, "metadata slot count is outside the resource limit")
    _require(SECTOR_SIZE <= block_size <= MAX_LOGICAL_BLOCK_SIZE and block_size % SECTOR_SIZE == 0,
             "logical block size is invalid or above the resource limit")
    end = METADATA_START + 2 * maximum * slots
    _require(end <= image.size and end <= MAX_METADATA_REGION_BYTES,
             "metadata slots extend outside the image or metadata resource limit")
    result["metadata_region_end"] = end
    result["struct_sha256"] = hashlib.sha256(raw[:size]).hexdigest()


def _tables(raw: bytes, tables_size: int, header: bytes) -> tuple[dict, dict]:
    descriptors = {}
    intervals = []
    for index, (name, entry_format) in enumerate(TABLE_FORMATS.items()):
        offset, count, entry_size = DESCRIPTOR.unpack_from(header, 80 + index * DESCRIPTOR.size)
        descriptors[name] = {"offset": offset, "num_entries": count, "entry_size": entry_size}
        _require(entry_size == entry_format.size, f"invalid {name} entry size")
        _require(count <= MAX_TABLE_ENTRIES, f"{name} entry count exceeds the resource limit")
        length = count * entry_size
        _require(length <= 0x7FFFFFFF and offset <= tables_size and length <= tables_size - offset,
                 f"{name} table extends outside the table region")
        if length:
            intervals.append((offset, offset + length, name))
    cursor = 0
    for start, end, name in sorted(intervals):
        _require(start == cursor, f"{name} table overlaps another table or leaves a gap")
        cursor = end
    _require(cursor == tables_size, "table region contains unclaimed bytes")
    values = {}
    for name, entry_format in TABLE_FORMATS.items():
        descriptor = descriptors[name]
        values[name] = [entry_format.unpack_from(raw, descriptor["offset"] + i * entry_format.size)
                        for i in range(descriptor["num_entries"])]
    return descriptors, values


def _devices(values: list[tuple], geometry: dict, image: RawImage) -> list[dict]:
    devices = []
    _require(bool(values), "metadata does not declare a super block device")
    for index, (first, alignment, alignment_offset, size, raw_name, flags) in enumerate(values):
        name = _safe_name(raw_name, f"block device {index}")
        _require(flags & ~1 == 0, f"block device {name} has unsupported flags")
        _require(0 < size <= MAX_IMAGE_BYTES and size % SECTOR_SIZE == 0,
                 f"block device {name} has an invalid size")
        _require(first <= size // SECTOR_SIZE, f"block device {name} starts past its end")
        _require(alignment % SECTOR_SIZE == 0 and alignment_offset % SECTOR_SIZE == 0,
                 f"block device {name} has unaligned alignment fields")
        _require((alignment == 0 and alignment_offset == 0)
                 or (alignment > 0 and alignment_offset < alignment),
                 f"block device {name} has invalid alignment offset")
        if index == 0:
            _require(first * SECTOR_SIZE >= geometry["metadata_region_end"],
                     "super logical area overlaps reserved geometry or metadata slots")
            _require(size == image.size, "super block device size does not match the complete raw image")
        devices.append({
            "index": index, "partition_name": name, "first_logical_sector": first,
            "alignment": alignment, "alignment_offset": alignment_offset,
            "size_bytes": size, "flags": flags,
            "slot_suffixed": bool(flags & 1), "image_supplied": index == 0,
        })
    _unique_names(devices, "block device table", "partition_name")
    return devices


def _groups(values: list[tuple]) -> list[dict]:
    groups = []
    _require(bool(values), "metadata contains no partition groups")
    for index, (raw_name, flags, maximum) in enumerate(values):
        name = _safe_name(raw_name, f"group {index}")
        _require(flags & ~1 == 0, f"group {name} has unsupported flags")
        groups.append({"index": index, "name": name, "flags": flags,
                       "slot_suffixed": bool(flags & 1), "maximum_size": maximum,
                       "allocated_size": 0})
    _unique_names(groups, "group table")
    return groups


def _extents(values: list[tuple], devices: list[dict], geometry: dict) -> list[dict]:
    extents = []
    ranges = {device["index"]: [] for device in devices}
    for index, (sectors, kind, target, source) in enumerate(values):
        size = sectors * SECTOR_SIZE
        _require(0 < size <= MAX_IMAGE_BYTES, f"extent {index} has an empty or excessive length")
        _require(size % geometry["logical_block_size"] == 0,
                 f"extent {index} length is not aligned to the logical block size")
        _require(kind in (0, 1), f"extent {index} has unsupported target type {kind}")
        if kind == 0:
            _require(source < len(devices), f"extent {index} has an invalid block device index")
            device = devices[source]
            _require(target >= device["first_logical_sector"],
                     f"extent {index} begins before its block device logical area")
            _require(target + sectors <= device["size_bytes"] // SECTOR_SIZE,
                     f"extent {index} extends past its block device")
            ranges[source].append((target, target + sectors, index))
        else:
            _require(target == 0 and source == 0, f"ZERO extent {index} has nonzero target fields")
        extents.append({
            "index": index, "num_sectors": sectors, "size_bytes": size,
            "target_type": kind, "target_type_name": "LINEAR" if kind == 0 else "ZERO",
            "target_data": target, "target_source": source,
            "physical_offset_bytes": target * SECTOR_SIZE if kind == 0 else None,
        })
    for source, intervals in ranges.items():
        previous_end = 0
        for start, end, index in sorted(intervals):
            _require(start >= previous_end, f"extent {index} overlaps another extent on block device {source}")
            previous_end = end
    return extents


def _partitions(values: list[tuple], extents: list[dict], groups: list[dict], minor: int) -> list[dict]:
    partitions = []
    owners = set()
    for index, (raw_name, attributes, first, count, group_index) in enumerate(values):
        name = _safe_name(raw_name, f"partition {index}")
        _require(attributes & ~(3 if minor == 0 else 15) == 0,
                 f"partition {name} has attributes unsupported by its metadata version")
        _require(first <= len(extents) and count <= len(extents) - first,
                 f"partition {name} has an invalid extent range")
        _require(group_index < len(groups), f"partition {name} has an invalid group index")
        indices = set(range(first, first + count))
        _require(not owners.intersection(indices), f"partition {name} shares extent entries with another partition")
        owners.update(indices)
        selected = extents[first:first + count]
        size = sum(extent["size_bytes"] for extent in selected)
        _require(size <= MAX_IMAGE_BYTES, f"partition {name} exceeds the resource limit")
        groups[group_index]["allocated_size"] += size
        partitions.append({
            "index": index, "name": name, "attributes": attributes,
            "readonly": bool(attributes & 1), "slot_suffixed": bool(attributes & 2),
            "updated": bool(attributes & 4), "disabled": bool(attributes & 8),
            "first_extent_index": first, "num_extents": count,
            "group_index": group_index, "group_name": groups[group_index]["name"],
            "size_bytes": size,
        })
    _unique_names(partitions, "partition table")
    _require(len(owners) == len(extents), "extent table contains entries without a partition owner")
    for group in groups:
        _require(group["maximum_size"] == 0 or group["allocated_size"] <= group["maximum_size"],
                 f"group {group['name']} exceeds its maximum size")
    return partitions


def _metadata(image: RawImage, offset: int, geometry: dict, result: dict) -> None:
    prefix = image.read(offset, 128)
    magic, major, minor, header_size, header_sum, tables_size, tables_sum = HEADER_PREFIX.unpack_from(prefix)
    header = {"magic": f"0x{magic:08x}", "major_version": major, "minor_version": minor,
              "header_size": header_size, "tables_size": tables_size}
    result["header"] = header
    _require(magic == HEADER_MAGIC, "invalid metadata magic")
    _require(major == 10 and minor <= 2, "unsupported metadata version (supported: 10.0 through 10.2)")
    _require(header_size == (256 if minor == 2 else 128), "metadata header size does not match its version")
    _require(header_size + tables_size <= geometry["metadata_max_size"],
             "header and tables extend past this metadata slot")
    raw_header = image.read(offset, header_size)
    header["checksum"] = _checksum(raw_header, header_sum, 12)
    _require(header["checksum"]["valid"], "invalid metadata header SHA256 checksum")
    flags = struct.unpack_from("<I", raw_header, 128)[0] if minor == 2 else 0
    header.update({"flags": flags, "virtual_ab_device": bool(flags & 1),
                   "overlays_active": bool(flags & 2), "unknown_flags": flags & ~3})
    if minor == 2:
        _require(not any(raw_header[132:]), "metadata expanded header reserved bytes are nonzero")
    raw_tables = image.read(offset + header_size, tables_size)
    header["tables_checksum"] = _checksum(raw_tables, tables_sum)
    _require(header["tables_checksum"]["valid"], "invalid metadata tables SHA256 checksum")
    descriptors, values = _tables(raw_tables, tables_size, raw_header)
    header["tables"] = descriptors
    result["metadata_size"] = header_size + tables_size
    result["metadata_sha256"] = hashlib.sha256(raw_header + raw_tables).hexdigest()
    result["block_devices"] = _devices(values["block_devices"], geometry, image)
    result["groups"] = _groups(values["groups"])
    result["extents"] = _extents(values["extents"], result["block_devices"], geometry)
    result["partitions"] = _partitions(values["partitions"], result["extents"], result["groups"], minor)


def _capture(parser, image: RawImage, offset: int, *args) -> dict:
    result = {"offset": offset, "valid": False, "errors": []}
    try:
        parser(image, offset, *args, result)
        result["valid"] = True
    except LogicalPartitionError as exc:
        result["errors"].append(str(exc))
    return result


def _inspect(image: RawImage, expected_sha256: str | None) -> dict:
    _require(struct.unpack("<I", image.read(0, 4))[0] != SPARSE_MAGIC,
             "input is Android sparse; reconstruct it to one raw super image first")
    digest = image.sha256()
    _require(expected_sha256 is None or digest == expected_sha256, "source image SHA256 does not match expected value")
    report = {
        "schema_version": 1, "format": "android-logical-partitions",
        "format_reference_commit": FORMAT_COMMIT,
        "image": {"path": str(image.path), "size_bytes": image.size, "sha256": digest},
        "names_are_on_disk": True, "authentication_verified": False,
        "geometry_copies": {}, "slots": [], "errors": [],
        "extraction_constraints": [],
    }
    for copy, offset in (("primary", RESERVED_BYTES), ("backup", RESERVED_BYTES + GEOMETRY_SIZE)):
        record = _capture(_geometry, image, offset)
        report["geometry_copies"][copy] = record
        report["errors"].extend(f"geometry {copy}: {error}" for error in record["errors"])
    primary, backup = report["geometry_copies"].values()
    report["geometry_copies_match"] = (primary["valid"] and backup["valid"]
                                          and primary["struct_sha256"] == backup["struct_sha256"])
    if primary["valid"] and backup["valid"] and not report["geometry_copies_match"]:
        report["errors"].append("primary and backup geometry disagree")
    geometry = primary if primary["valid"] else backup if backup["valid"] else None
    report["selected_geometry_copy"] = "primary" if primary["valid"] else "backup" if backup["valid"] else None
    if geometry is not None:
        maximum, count = geometry["metadata_max_size"], geometry["metadata_slot_count"]
        for slot in range(count):
            entry = {"slot": slot}
            for copy, index in (("primary", slot), ("backup", count + slot)):
                record = _capture(_metadata, image, METADATA_START + maximum * index, geometry)
                entry[copy] = record
                report["errors"].extend(f"slot {slot} {copy}: {error}" for error in record["errors"])
                if record["valid"] and len(record["block_devices"]) != 1:
                    report["extraction_constraints"].append(f"slot {slot} {copy}: extraction requires one physical super device")
                if record["valid"] and record["header"]["unknown_flags"]:
                    report["extraction_constraints"].append(f"slot {slot} {copy}: unknown header flags have unreviewed semantics")
                if record["valid"] and record["header"]["overlays_active"]:
                    report["extraction_constraints"].append(f"slot {slot} {copy}: active overlays cannot be reconstructed from this raw image")
            a, b = entry["primary"], entry["backup"]
            entry["copies_match"] = a["valid"] and b["valid"] and a["metadata_sha256"] == b["metadata_sha256"]
            if a["valid"] and b["valid"] and not entry["copies_match"]:
                report["errors"].append(f"slot {slot} primary and backup metadata disagree")
            report["slots"].append(entry)
    slot_hashes = [slot["primary"].get("metadata_sha256") for slot in report["slots"]]
    report["all_slots_identical"] = bool(slot_hashes) and None not in slot_hashes and len(set(slot_hashes)) == 1
    report["valid"] = not report["errors"]
    report["extraction_supported"] = report["valid"] and not report["extraction_constraints"]
    image.unchanged()
    return report


def inspect_image(path: Path, expected_sha256: str | None = None) -> dict:
    """Return all copies, including errors; never recover silently from a bad copy."""
    expected = _sha256_argument(expected_sha256)
    with RawImage(Path(path)) as image:
        return _inspect(image, expected)


@contextmanager
def _new_output_directory(path: Path):
    path = _absolute(path)
    try:
        relative = path.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise LogicalPartitionError("output must be under this workspace's artifacts/ or evidence/") from exc
    _require(len(relative.parts) >= 2 and relative.parts[0] in ("artifacts", "evidence"),
             "output must be a new directory below artifacts/ or evidence/")
    parent_fd = _directory_fd(path.parent, create=True)
    descriptor = None
    try:
        # mkdir, O_EXCL and dir_fd deliberately avoid a check-then-truncate path.
        os.mkdir(path.name, mode=0o700, dir_fd=parent_fd)
        descriptor = os.open(path.name, _directory_flags(), dir_fd=parent_fd)
        yield path, descriptor
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def _new_file(directory_fd: int, name: str):
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
    return os.fdopen(descriptor, "wb")


def _verify_output(directory_fd: int, name: str, size: int, expected: str) -> None:
    descriptor = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        _require(stat.S_ISREG(before.st_mode) and before.st_size == size, "output size/type changed before verification")
        digest = hashlib.sha256()
        remaining = size
        while remaining:
            chunk = stream.read(min(CHUNK_SIZE, remaining))
            _require(bool(chunk), "output was truncated during verification")
            digest.update(chunk)
            remaining -= len(chunk)
        _require(digest.hexdigest() == expected, "extracted output SHA256 verification failed")
        _require(_signature(before) == _signature(os.fstat(stream.fileno()))
                 == _signature(os.stat(name, dir_fd=directory_fd, follow_symlinks=False)),
                 "output changed during verification")


def _write_partition(image: RawImage, directory_fd: int, partition: dict, extents: list[dict]) -> dict:
    name = partition["name"] + ".img"
    digest = hashlib.sha256()
    written = 0
    with _new_file(directory_fd, name) as output:
        first, count = partition["first_extent_index"], partition["num_extents"]
        for extent in extents[first:first + count]:
            for offset in range(0, extent["size_bytes"], CHUNK_SIZE):
                length = min(CHUNK_SIZE, extent["size_bytes"] - offset)
                if extent["target_type"] == 0:
                    chunk = image.read(extent["physical_offset_bytes"] + offset, length)
                else:
                    chunk = bytes(length)
                output.write(chunk)
                digest.update(chunk)
                written += length
        output.flush()
        os.fsync(output.fileno())
    _require(written == partition["size_bytes"], "extracted partition size mismatch")
    checksum = digest.hexdigest()
    _verify_output(directory_fd, name, written, checksum)
    return {"partition": partition["name"], "filename": name, "size_bytes": written,
            "sha256": checksum, "readback_verified": True}


def extract_image(path: Path, expected_sha256: str, slot: int,
                  partition_names: list[str], output: Path) -> dict:
    """Extract only explicit names from one selected metadata slot to private files."""
    expected = _sha256_argument(expected_sha256, required=True)
    _require(type(slot) is int and slot >= 0, "metadata slot must be a nonnegative integer")
    _require(bool(partition_names), "at least one explicit partition name is required")
    _require(all(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]{1,36}", name) is not None
                 for name in partition_names), "requested partition name is unsafe")
    _require(len(set(name.casefold() for name in partition_names)) == len(partition_names),
             "duplicate or case-colliding partition selections are not allowed")
    with RawImage(Path(path)) as image:
        report = _inspect(image, expected)
        _require(report["extraction_supported"],
                 "extraction refused: " + "; ".join(report["errors"] + report["extraction_constraints"]))
        _require(slot < len(report["slots"]), "requested metadata slot does not exist")
        metadata = report["slots"][slot]["primary"]
        by_name = {partition["name"]: partition for partition in metadata["partitions"]}
        selected = []
        for name in partition_names:
            _require(name in by_name, f"partition {name} is absent from metadata slot {slot}")
            _require(not by_name[name]["disabled"], f"partition {name} is marked disabled")
            selected.append(by_name[name])
        total = sum(partition["size_bytes"] for partition in selected)
        _require(total <= MAX_IMAGE_BYTES, "selected output size exceeds the resource limit")
        with _new_output_directory(Path(output)) as (directory, directory_fd):
            free = os.fstatvfs(directory_fd)
            _require(total + CHUNK_SIZE <= free.f_bavail * free.f_frsize,
                     "insufficient free disk space for selected partition outputs")
            outputs = [_write_partition(image, directory_fd, partition, metadata["extents"])
                       for partition in selected]
            image.unchanged()
            for entry in outputs:
                entry["parent_image_sha256"] = report["image"]["sha256"]
            receipt = {
                "schema_version": 1, "status": "complete",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "format_reference_commit": FORMAT_COMMIT,
                "source_image": report["image"], "authentication_verified": False,
                "output_directory": str(directory), "metadata_slot": slot,
                "metadata_sha256": metadata["metadata_sha256"],
                "all_geometry_and_metadata_copies_valid": True,
                "all_primary_backup_pairs_match": True,
                "all_slots_identical": report["all_slots_identical"],
                "names_are_on_disk": True, "outputs": outputs,
            }
            with _new_file(directory_fd, "receipt.json") as stream:
                stream.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect = subparsers.add_parser("inspect", help="print JSON for every primary/backup metadata slot")
    inspect.add_argument("--image", type=Path, required=True)
    inspect.add_argument("--expected-sha256")
    extract = subparsers.add_parser("extract", help="extract explicit partitions to a new ignored directory")
    extract.add_argument("--image", type=Path, required=True)
    extract.add_argument("--expected-sha256", required=True)
    extract.add_argument("--slot", type=int, required=True, help="metadata slot, independent of partition group/name")
    extract.add_argument("--partition", action="append", required=True, help="exact on-disk name; repeat for each partition")
    extract.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_image(args.image, args.expected_sha256)
            status = 0 if result["valid"] else 2
        else:
            result = extract_image(args.image, args.expected_sha256, args.slot, args.partition, args.output)
            status = 0
        print(json.dumps(result, indent=2, sort_keys=True))
        return status
    except (LogicalPartitionError, OSError) as exc:
        print(f"logical_partitions: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
