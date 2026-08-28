#!/usr/bin/env python3
"""Inspect one compiled, uncompressed TWRP newc ramdisk without extracting it.

This checks the CPIO structure, selected property literals and ARM64 ELF files.
It does not establish SELinux enforcement, ADB authentication, bootability,
runtime property values or permission to flash. Run the real sepolicy-analyze
tool separately against the compiled policy. No subprocess or device is used.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

if __package__:
    from .apex_inputs import ApexError, elf_dynamic
    from .firmware import _signature
    from .inspect_twrp_image import ImageInspectionError, _absolute_path, _parent_directory
    from .inspect_twrp_image import write_report as _write_report
else:
    from apex_inputs import ApexError, elf_dynamic
    from firmware import _signature
    from inspect_twrp_image import ImageInspectionError, _absolute_path, _parent_directory
    from inspect_twrp_image import write_report as _write_report


ROOT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE_BYTES = 512 * 1024**2
MAX_ENTRIES = 20000
MAX_NAME_BYTES = 4096
MAX_PROPERTY_BYTES = 1024**2
MAX_KEY_BYTES = 128 * 1024**2
MAX_ELF_DYNAMIC_BYTES = 64 * 1024
MAX_TRAILER_PADDING = 511
HEADER_BYTES = 110
SECURE_PROPERTIES = {"ro.secure": "1", "ro.adb.secure": "1", "ro.debuggable": "0"}
KINDS = {stat.S_IFREG: "regular", stat.S_IFDIR: "directory", stat.S_IFLNK: "symlink",
         stat.S_IFCHR: "character", stat.S_IFBLK: "block", stat.S_IFIFO: "fifo",
         stat.S_IFSOCK: "socket"}
HEX = re.compile(rb"[0-9a-fA-F]{104}\Z")
PROPERTY_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")


class RamdiskInspectionError(ValueError):
    """The ramdisk does not meet the bounded, static inspection contract."""


def _require(condition, message):
    if not condition:
        raise RamdiskInspectionError(message)


def _span(start, size, limit, label):
    _require(0 <= start <= limit and 0 <= size <= limit - start,
             f"truncated or out-of-bounds {label}")
    return start + size


def _padding(data, start):
    end = _span(start, (-start) % 4, len(data), "newc alignment padding")
    _require(not any(data[start:end]), "nonzero newc alignment padding")
    return end


def _name(raw):
    _require(raw.endswith(b"\0") and b"\0" not in raw[:-1], "invalid newc filename termination")
    try:
        value = raw[:-1].decode("utf-8")
    except UnicodeError as exc:
        raise RamdiskInspectionError("newc filename is not UTF-8") from exc
    _require(value and value.isprintable() and not value.startswith("/")
             and "\\" not in value,
             "unsafe or absolute newc path")
    if value == ".":
        return value
    # GNU cpio may prefix names with './'; normalize before duplicate checks.
    if value.startswith("./"):
        value = value[2:]
    parts = value.split("/")
    _require(not re.match(r"^[A-Za-z]:", value) and 1 <= len(parts) <= 64
             and all(part not in ("", ".", "..") for part in parts),
             "noncanonical or traversing newc path")
    return value


def _archive(data):
    """Parse exactly one newc archive; retain only bounded member metadata."""
    _require(HEADER_BYTES <= len(data) <= MAX_ARCHIVE_BYTES and len(data) % 4 == 0,
             "ramdisk size is outside bounds or not 4-byte aligned")
    members, position = {}, 0
    while True:
        header_start = position
        end = _span(position, HEADER_BYTES, len(data), "newc header or trailer")
        header = bytes(data[position:end])
        _require(header[:6] == b"070701" and HEX.fullmatch(header[6:]),
                 "expected a complete uncompressed newc header (070701)")
        fields = [int(header[index:index + 8], 16) for index in range(6, HEADER_BYTES, 8)]
        inode, mode, uid, gid, links, _, size, devmajor, devminor, rdevmajor, rdevminor, namesize, check = fields
        _require(1 < namesize <= MAX_NAME_BYTES and check == 0, "invalid newc name size or check field")
        name_end = _span(end, namesize, len(data), "newc filename")
        raw_name = bytes(data[end:name_end])
        name = _name(raw_name)
        content_start = _padding(data, name_end)
        content_end = _span(content_start, size, len(data), "newc member payload")
        position = _padding(data, content_end)
        if raw_name == b"TRAILER!!!\0":
            _require(mode == uid == gid == size == rdevmajor == rdevminor == 0 and links in (0, 1),
                     "invalid newc trailer fields")
            padding = len(data) - position
            _require(padding <= MAX_TRAILER_PADDING and not any(data[position:]),
                     "extra archive, nonzero data or excessive padding after newc trailer")
            break
        _require(name != "TRAILER!!!", "noncanonical newc trailer name")
        _require(name not in members, "duplicate normalized newc path")
        _require(len(members) < MAX_ENTRIES, "too many newc members")
        _require(mode <= 0xFFFF and links > 0, "invalid newc mode or link count")
        kind = KINDS.get(stat.S_IFMT(mode))
        _require(kind is not None, "invalid newc file type")
        _require(kind in ("regular", "symlink") or size == 0, "non-file newc member has payload")
        _require(name != "." or kind == "directory", "newc root entry is not a directory")
        row = {"kind": kind, "mode": f"0o{mode:o}", "uid": uid, "gid": gid,
               "nlink": links, "inode": inode, "device": [devmajor, devminor],
               "size_bytes": size, "offset_bytes": content_start}
        if kind == "symlink":
            _require(0 < size <= MAX_NAME_BYTES, "invalid newc symlink size")
            target = bytes(data[content_start:content_end])
            _require(b"\0" not in target, "NUL in newc symlink target")
            try:
                row["symlink_target"] = target.decode("utf-8")
            except UnicodeError as exc:
                raise RamdiskInspectionError("newc symlink target is not UTF-8") from exc
            _require(row["symlink_target"].isprintable(), "nonprintable newc symlink target")
        members[name] = row
    for name in members:
        parts = name.split("/")
        for length in range(1, len(parts)):
            ancestor = members.get("/".join(parts[:length]))
            _require(ancestor is None or ancestor["kind"] == "directory",
                     "newc member descends through a non-directory or symlink")
    return members, {"format": "newc", "archive_count": 1, "entry_count": len(members),
                     "file_type_counts": dict(sorted(Counter(row["kind"] for row in members.values()).items())),
                     "trailer_offset_bytes": header_start, "trailing_zero_padding_bytes": padding}


def _key_member(members, data, name, *, symlink=False):
    _require(name in members, f"required ramdisk member is absent: {name}")
    row = members[name]
    _require(row["kind"] == "regular" or (symlink and row["kind"] == "symlink"),
             f"key member must be a regular file: {name}")
    _require(row["nlink"] == 1, f"hard-linked key member is not admitted: {name}")
    _require(0 < row["size_bytes"] <= MAX_KEY_BYTES, f"key member size is invalid: {name}")
    if row["kind"] == "regular":
        _require(not int(row["mode"], 8) & 0o022,
                 f"group- or world-writable key member is not admitted: {name}")
    parts = name.split("/")
    ancestors = [members["."]] if "." in members else []
    for length in range(1, len(parts)):
        ancestor = members.get("/".join(parts[:length]))
        _require(ancestor is not None and ancestor["kind"] == "directory",
                 f"key member has an absent or non-directory ancestor: {name}")
        ancestors.append(ancestor)
    _require(all(not int(ancestor["mode"], 8) & 0o022 for ancestor in ancestors),
             f"key member has a group- or world-writable directory ancestor: {name}")
    start = row["offset_bytes"]
    content = data[start:start + row["size_bytes"]]
    return {**row, "sha256": hashlib.sha256(content).hexdigest()}, content


def _properties(data):
    _require(len(data) <= MAX_PROPERTY_BYTES and 0 not in data, "invalid property file size or NUL byte")
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeError as exc:
        raise RamdiskInspectionError("property file is not UTF-8") from exc
    properties = {}
    for raw_line in text.split("\n"):
        line = raw_line.strip(" \t\r")
        if not line or line.startswith("#"):
            continue
        _require("=" in line, "property imports or invalid assignments are unsupported")
        key, value = (part.strip(" \t\r") for part in line.split("=", 1))
        _require(PROPERTY_NAME.fullmatch(key) is not None and key not in properties,
                 "invalid or duplicate property assignment")
        _require(value.isprintable() or value == "", "nonprintable property value")
        properties[key] = value
    _require(all(properties.get(key) == value for key, value in SECURE_PROPERTIES.items()),
             "required secure properties must be ro.secure=1, ro.adb.secure=1, ro.debuggable=0")
    return properties


def _elf(row, content, name):
    _require(int(row["mode"], 8) & 0o111, f"key executable has no execute mode: {name}")
    _require(len(content) >= 64 and content[:7] == b"\x7fELF\x02\x01\x01",
             f"key executable is not a little-endian ELF64 file: {name}")
    elf_type, machine, version = struct.unpack_from("<HHI", content, 16)
    header_size = struct.unpack_from("<H", content, 52)[0]
    program_offset = struct.unpack_from("<Q", content, 32)[0]
    _require(elf_type in (2, 3) and machine == 183 and version == 1
             and header_size == 64 and program_offset >= 64,
             f"key executable lacks a valid AArch64 ELF header: {name}")
    program_size, program_count = struct.unpack_from("<HH", content, 54)
    _require(program_size == 56 and 0 < program_count <= 4096,
             f"invalid ELF program table: {name}")
    _span(program_offset, program_size * program_count, len(content), "ELF program table")
    executable_load = False
    for index in range(program_count):
        kind, flags, offset, _, _, file_size, memory_size, _ = struct.unpack_from(
            "<IIQQQQQQ", content, program_offset + 56 * index)
        _span(offset, file_size, len(content), "ELF segment")
        if kind == 1:
            _require(memory_size >= file_size, f"ELF load memory is smaller than file data: {name}")
            executable_load |= bool(flags & 1 and file_size)
        elif kind == 2:
            _require(file_size <= MAX_ELF_DYNAMIC_BYTES, f"ELF dynamic table exceeds inspection bound: {name}")
    _require(executable_load, f"ELF executable load segment is absent: {name}")
    try:
        parsed = elf_dynamic(bytes(content))
    except (ApexError, UnicodeError) as exc:
        raise RamdiskInspectionError(f"key executable has malformed ELF segments: {name}") from exc
    return {"class_bits": parsed["class_bits"], "endianness": parsed["endianness"],
            "machine": parsed["machine"], "type": elf_type,
            "declared_needed_library_count": len(parsed["needed"]),
            "dependencies_resolved": False, "executed": False}


def inspect_cpio(data):
    """Inspect supplied bytes without creating archive paths or running tools."""
    data = memoryview(data)
    members, archive = _archive(data)
    keys = {}
    policy, _ = _key_member(members, data, "sepolicy")
    defaults, content = _key_member(members, data, "prop.default")
    properties = _properties(content)
    keys["sepolicy"], keys["prop.default"] = policy, defaults
    default_relation = "absent"
    if "default.prop" in members:
        row, alias_content = _key_member(members, data, "default.prop", symlink=True)
        if row["kind"] == "symlink":
            _require(row["symlink_target"] in ("prop.default", "./prop.default", "/prop.default"),
                     "default.prop symlink must point directly to prop.default")
            default_relation = "symlink-to-prop.default"
        else:
            _require(_properties(alias_content) == properties,
                     "default.prop introduces a property override")
            default_relation = "identical-property-map"
        keys["default.prop"] = row
    for name in ("system/bin/init", "system/bin/adbd"):
        row, content = _key_member(members, data, name)
        row["elf"] = _elf(row, content, name)
        keys[name] = row
    if "init" in members:
        row, content = _key_member(members, data, "init", symlink=True)
        if row["kind"] == "symlink":
            _require(row["symlink_target"] in ("system/bin/init", "./system/bin/init", "/system/bin/init"),
                     "root init symlink must point directly to system/bin/init")
        else:
            row["elf"] = _elf(row, content, "init")
        keys["init"] = row
    return {
        "schema_version": 1,
        "operation": "inspect-twrp-ramdisk",
        "archive": {**archive, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
        "key_members": keys,
        "properties": {"source": "prop.default", "required_values": dict(SECURE_PROPERTIES),
                       "property_count": len(properties), "default_prop_relation": default_relation,
                       "duplicate_assignments_found": False, "cross_file_overrides_found": False,
                       "other_property_sources_audited": False},
        "validation": {
            "structurally_valid": True, "secure_property_literals_verified": True,
            "key_elf_headers_verified": True, "member_paths_unique": True,
            "ramdisk_extracted": False, "firmware_executed": False, "phone_accessed": False,
            "archive_mutated": False, "effective_runtime_properties_verified": False,
            "twrp_build_provenance_verified": False, "compressed_ramdisk_binding_verified": False,
            "adb_authentication_verified": False, "sepolicy_contents_parsed": False,
            "compiled_selinux_policy_verified": False, "selinux_enforcement_verified": False,
            "boot_tested": False, "avb_trusted": False, "flash_admitted": False,
        },
    }


def inspect_ramdisk(path):
    """Read a bounded regular file through the shared no-symlink FD traversal."""
    path = _absolute_path(path)
    with _parent_directory(path) as parent:
        initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(stat.S_ISREG(initial.st_mode), "ramdisk input is not a regular file")
        _require(HEADER_BYTES <= initial.st_size <= MAX_ARCHIVE_BYTES, "ramdisk input exceeds size bounds")
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            before = _signature(initial)
            details = os.fstat(stream.fileno())
            _require(stat.S_ISREG(details.st_mode) and before == _signature(details),
                     "ramdisk input changed before read")
            raw = stream.read(initial.st_size + 1)
            _require(len(raw) == initial.st_size, "ramdisk input changed or was truncated")
            report = inspect_cpio(raw)
            _require(before == _signature(os.fstat(stream.fileno()))
                     and before == _signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                     "ramdisk input changed during inspection")
    report["archive"]["name"] = path.name
    report["validation"]["input_stable_during_read"] = True
    return report


def write_report(path, report):
    """Only publish a new private JSON report beneath ignored artifact roots."""
    path = _absolute_path(path)
    _require(any(path.is_relative_to(ROOT / directory) for directory in ("artifacts", "reports")),
             "output must be beneath this workspace's ignored artifacts/ or reports/ directory")
    _write_report(path, report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ramdisk", type=Path, help="uncompressed ramdisk-recovery.cpio input")
    parser.add_argument("--output", type=Path, help="new .json under ignored artifacts/ or reports/; parent must exist")
    args = parser.parse_args(argv)
    try:
        report = inspect_ramdisk(args.ramdisk)
        if args.output is not None:
            write_report(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (RamdiskInspectionError, ImageInspectionError, OSError) as exc:
        print(f"ramdisk inspection failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
