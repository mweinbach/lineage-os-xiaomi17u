#!/usr/bin/env python3
"""Inspect the Nezha recovery image envelope offline; never admit it for flashing.

The factory contract is Android boot header v4, no kernel, 4096-byte pages,
and a 104857600-byte recovery partition in the *package GPT*, not a live
capacity measurement. See research/recovery-plan.json and
research/factory-boot-contract.json. This is not a general boot-image parser.

Layouts were checked against aosp-mkbootimg 954bc3ead5e679005fddf3484d247f2557b3c2c9
and aosp-avb c92ce4cb9a1b6d20a1bc11b7e5864af9f78615bb. LZ4 envelope reference:
https://github.com/lz4/lz4/blob/v1.10.0/doc/lz4_Frame_format.md
No ramdisk decompression, executable/policy audit, signature verification,
boot test, partition-capacity check, or device operation is performed.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys

if __package__:
    from .firmware import IntakeError, _signature
else:
    from firmware import IntakeError, _signature


PAGE_SIZE = 4096
HEADER_SIZE = 1584
MAX_IMAGE_BYTES = 104857600
MAX_REPORT_BYTES = 64 * 1024
MAX_LZ4_BLOCKS = 1024
MAX_AVB_DESCRIPTORS = 128
LZ4_LEGACY_MAGIC = b"\x02\x21\x4c\x18"
LZ4_FRAME_MAGIC = b"\x04\x22\x4d\x18"
AVB_FOOTER = struct.Struct(">4sIIQQQ28s")


class ImageInspectionError(ValueError):
    """An image does not meet the supported structural recovery contract."""


def _require(condition, message):
    if not condition:
        raise ImageInspectionError(message)


def _aligned(size):
    return (size + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def _span(offset, size, limit, label):
    _require(0 <= offset <= limit and 0 <= size <= limit - offset,
             f"{label} is truncated or out of bounds")
    return offset, offset + size


def _zero(data, start, end, label):
    _require(not any(data[start:end]), f"nonzero {label}")


def _disjoint(ranges, label):
    nonempty = sorted((start, end) for start, end in ranges if start != end)
    _require(all(left[1] <= right[0] for left, right in zip(nonempty, nonempty[1:])),
             f"overlapping {label}")


def _absolute_path(path):
    value = os.fspath(path)
    _require(isinstance(value, str) and 0 < len(value) <= 4096 and value.isprintable(),
             "path must be bounded printable text")
    return Path(os.path.abspath(value))


@contextmanager
def _parent_directory(path):
    """Anchor traversal and final access to directory inodes, not mutable names."""
    _require(hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW"),
             "safe directory traversal is unavailable on this platform")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:-1]:
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ImageInspectionError(
                        "path ancestors must be real directories, not symlinks") from exc
                raise
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _lz4_envelope(data):
    """Validate one frame's envelope, not its encoded blocks or checksums."""
    _require(len(data) >= 8, "truncated LZ4 ramdisk")
    magic = bytes(data[:4])
    count, block_bytes = 0, 0
    if magic == LZ4_LEGACY_MAGIC:
        position = 4
        maximum = 8 * 1024**2
        maximum += maximum // 255 + 16  # LZ4_COMPRESSBOUND for an 8 MiB block.
        while position < len(data):
            _span(position, 4, len(data), "legacy LZ4 block header")
            size = struct.unpack_from("<I", data, position)[0]
            position += 4
            _require(0 < size <= maximum, "invalid legacy LZ4 block size")
            _, position = _span(position, size, len(data), "legacy LZ4 block")
            count += 1
            block_bytes += size
            _require(count <= MAX_LZ4_BLOCKS, "too many LZ4 blocks")
        kind = "lz4-legacy"
    elif magic == LZ4_FRAME_MAGIC:
        flags, descriptor = data[4], data[5]
        block_id = (descriptor >> 4) & 7
        _require(flags >> 6 == 1 and not flags & 2 and not descriptor & 0x8F
                 and 4 <= block_id <= 7, "invalid LZ4 frame descriptor")
        _require(not flags & 1, "dictionary-backed LZ4 frames are unsupported")
        maximum = 1 << (8 + 2 * block_id)
        position = 6 + (8 if flags & 8 else 0)
        _span(6, position - 6 + 1, len(data), "LZ4 frame header")
        position += 1  # Header checksum exists, but is not verified here.
        while True:
            _span(position, 4, len(data), "LZ4 frame block header or end marker")
            raw_size = struct.unpack_from("<I", data, position)[0]
            position += 4
            if raw_size == 0:
                break
            size = raw_size & 0x7FFFFFFF
            _require(size <= maximum, "LZ4 frame block exceeds declared maximum")
            _, position = _span(position, size + (4 if flags & 16 else 0),
                                len(data), "LZ4 frame block and checksum")
            count += 1
            block_bytes += size
            _require(count <= MAX_LZ4_BLOCKS, "too many LZ4 blocks")
        _, position = _span(position, 4 if flags & 4 else 0, len(data),
                            "LZ4 content checksum")
        _require(position == len(data), "trailing or concatenated LZ4 frame data")
        kind = "lz4-frame"
    else:
        raise ImageInspectionError("ramdisk must use legacy or framed LZ4 compression")
    _require(count > 0 and block_bytes > 0, "empty LZ4 ramdisk")
    return {
        "format": kind,
        "block_count": count,
        "envelope_valid": True,
        "compressed_blocks_decoded": False,
        "checksums_verified": False,
    }


def _vbmeta(data):
    """Inspect the vbmeta envelope and descriptor headers as untrusted data."""
    _require(len(data) >= 256 and data[:4] == b"AVB0", "invalid AVB vbmeta header")
    _, major, minor, auth_size, aux_size, algorithm = struct.unpack_from(">4sIIQQI", data)
    _require(major == 1, "unsupported AVB vbmeta major version")
    _require(auth_size % 64 == 0 and aux_size % 64 == 0
             and 256 + auth_size + aux_size == len(data), "invalid AVB block sizes")
    _zero(data, 176, 256, "AVB header reserved bytes")
    _require(0 in data[128:176], "unterminated AVB release string")
    pairs = [struct.unpack_from(">QQ", data, offset) for offset in range(32, 112, 16)]
    auth_ranges = [_span(*pair, auth_size, "AVB authentication field") for pair in pairs[:2]]
    aux_ranges = [_span(*pair, aux_size, "AVB auxiliary field") for pair in pairs[2:]]
    _disjoint(auth_ranges, "AVB authentication fields")
    _disjoint(aux_ranges, "AVB auxiliary fields")
    start, end = aux_ranges[-1]
    _require(start % 8 == 0 and (end - start) % 8 == 0, "unaligned AVB descriptors")
    auxiliary = data[256 + auth_size:]
    descriptors = []
    while start < end:
        _span(start, 16, end, "AVB descriptor header")
        tag, following = struct.unpack_from(">QQ", auxiliary, start)
        _require(following % 8 == 0, "unaligned AVB descriptor size")
        _, stop = _span(start + 16, following, end, "AVB descriptor")
        _require(len(descriptors) < MAX_AVB_DESCRIPTORS, "too many AVB descriptors")
        descriptors.append({
            "tag": tag,
            "size_bytes": stop - start,
            "sha256": hashlib.sha256(auxiliary[start:stop]).hexdigest(),
            "payload_semantics_parsed": False,
        })
        start = stop
    rollback_index = struct.unpack_from(">Q", data, 112)[0]
    flags, rollback_location = struct.unpack_from(">II", data, 120)
    return {
        "required_libavb_version": [major, minor],
        "algorithm_type": algorithm,
        "flags": flags,
        "rollback_index": rollback_index,
        "rollback_index_location": rollback_location,
        "authentication_size_bytes": auth_size,
        "auxiliary_size_bytes": aux_size,
        "descriptor_headers": descriptors,
        "descriptor_payloads_verified": False,
        "signature_verified": False,
        "trusted_key_verified": False,
    }


def _avb(data, payload_end):
    footer_start = len(data) - AVB_FOOTER.size
    if data[footer_start:footer_start + 4] != b"AVBf":
        _zero(data, payload_end, len(data), "unrecognized image trailer")
        return {"footer_present": False, "vbmeta_parsed": False,
                "signature_verified": False, "trusted_key_verified": False}
    _, major, minor, original_size, offset, size, reserved = AVB_FOOTER.unpack_from(data, footer_start)
    _require((major, minor) == (1, 0) and not any(reserved), "invalid AVB footer")
    _require(payload_end <= original_size <= offset and offset % PAGE_SIZE == 0,
             "AVB metadata overlaps the recovery payload or is unaligned")
    _, end = _span(offset, size, footer_start, "AVB vbmeta block")
    _zero(data, payload_end, offset, "padding before AVB metadata")
    _zero(data, end, footer_start, "padding after AVB metadata")
    vbmeta = _vbmeta(data[offset:end])
    return {
        "footer_present": True,
        "footer_version": [major, minor],
        "original_image_size_bytes": original_size,
        "vbmeta_offset_bytes": offset,
        "vbmeta_size_bytes": size,
        "vbmeta_sha256": hashlib.sha256(data[offset:end]).hexdigest(),
        "vbmeta_parsed": True,
        "vbmeta": vbmeta,
        "signature_verified": False,
        "trusted_key_verified": False,
    }


def _inspect(data):
    _require(PAGE_SIZE <= len(data) <= MAX_IMAGE_BYTES, "image size exceeds recovery bounds")
    _require(len(data) % PAGE_SIZE == 0, "image is truncated or not page-aligned")
    _require(data[:8] != b"VNDRBOOT", "vendor_boot is not a dedicated recovery image")
    _require(data[:8] == b"ANDROID!", "invalid Android boot-image magic")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", data, 8)
    version = struct.unpack_from("<I", data, 40)[0]
    _require(version == 4 and header_size == HEADER_SIZE, "expected Android header v4 of size 1584")
    _require(kernel_size == 0, "Nezha recovery must not contain a kernel")
    _require(ramdisk_size > 0, "recovery ramdisk is empty")
    _zero(data, 24, 40, "Android header reserved bytes")
    _zero(data, HEADER_SIZE, PAGE_SIZE, "Android header padding")
    cmdline = data[44:1580]
    _require(0 in cmdline, "unterminated Android command line")
    signature_size = struct.unpack_from("<I", data, 1580)[0]
    _, ramdisk_end = _span(PAGE_SIZE, ramdisk_size, len(data), "recovery ramdisk")
    signature_start = PAGE_SIZE + _aligned(ramdisk_size)
    _, signature_end = _span(signature_start, signature_size, len(data), "boot signature")
    payload_end = signature_start + _aligned(signature_size)
    _span(0, payload_end, len(data), "padded recovery payload")
    _zero(data, ramdisk_end, signature_start, "ramdisk padding")
    _zero(data, signature_end, payload_end, "boot signature padding")
    ramdisk = data[PAGE_SIZE:ramdisk_end]
    compression = _lz4_envelope(ramdisk)
    return {
        "schema_version": 1,
        "operation": "inspect-twrp-image",
        "contract": {
            "device": "nezha",
            "hardware_region": "CN",
            "image_role": "dedicated-recovery",
            "maximum_image_size_bytes": MAX_IMAGE_BYTES,
            "size_limit_source": "research/recovery-plan.json:stock.package_gpt_contract",
            "physical_phone_capacity_verified": False,
        },
        "image": {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
        "header": {
            "version": version,
            "size_bytes": header_size,
            "page_size_bytes": PAGE_SIZE,
            "kernel_size_bytes": kernel_size,
            "os_version_raw": os_version,
            "command_line_sha256": hashlib.sha256(cmdline).hexdigest(),
            "boot_signature_size_bytes": signature_size,
            "boot_signature_offset_bytes": signature_start if signature_size else None,
            "boot_signature_verified": False,
            "padded_payload_size_bytes": payload_end,
        },
        "ramdisk": {"offset_bytes": PAGE_SIZE, "size_bytes": ramdisk_size,
                    "sha256": hashlib.sha256(ramdisk).hexdigest(), "compression": compression},
        "avb": _avb(data, payload_end),
        "validation": {
            "structurally_valid": True,
            "scope": "header, payload ranges, LZ4 envelope, optional AVB envelope and descriptor headers",
            "ramdisk_decompressed": False,
            "twrp_contents_verified": False,
            "compiled_selinux_policy_verified": False,
            "boot_tested": False,
            "avb_trusted": False,
            "rollback_compatibility_verified": False,
            "device_compatibility_verified": False,
            "flash_admitted": False,
            "phone_accessed": False,
            "image_mutated": False,
        },
    }


def inspect_image(path):
    """Read one bounded, stable regular file without following symlinks."""
    path = _absolute_path(path)
    with _parent_directory(path) as parent:
        initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(initial.st_mode):
            raise IntakeError("image is not a regular file")
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            details = os.fstat(stream.fileno())
            _require(stat.S_ISREG(details.st_mode), "image is not a regular file")
            before = _signature(initial)
            _require(before == _signature(details), "image changed before read")
            _require(PAGE_SIZE <= before[2] <= MAX_IMAGE_BYTES, "image size exceeds recovery bounds")
            data = stream.read(before[2] + 1)
            _require(len(data) == before[2], "image changed or was truncated while read")
            report = _inspect(memoryview(data))
            _require(before == _signature(os.fstat(stream.fileno()))
                     and before == _signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                     "image changed while inspected")
    report["image"]["name"] = path.name
    report["validation"]["input_stable_during_read"] = True
    return report


def write_report(path, report):
    """Create a small private JSON artifact exclusively; never replace a path.

    Failed writes retain any partial artifact: removing a name after an inode
    check is not atomic and could delete an unrelated replacement.
    """
    path = _absolute_path(path)
    _require(path.suffix == ".json", "output must have a .json suffix")
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _require(len(encoded) <= MAX_REPORT_BYTES, "report exceeds output bound")
    with _parent_directory(path) as parent:
        descriptor = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb") as stream:
            try:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            except OSError as exc:
                raise ImageInspectionError(
                    "report write failed; any partial artifact is preserved, not a completed report") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="regular local recovery image to inspect read-only")
    parser.add_argument("--output", type=Path, help="new .json report in an existing nonsymlink directory")
    args = parser.parse_args(argv)
    try:
        report = inspect_image(args.image)
        if args.output is not None:
            write_report(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (ImageInspectionError, IntakeError, OSError) as exc:
        print(f"recovery image inspection failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
