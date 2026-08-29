#!/usr/bin/env python3
"""Validate native EROFS metadata exports and compare explicit policy replacements.

This command reads JSONL evidence, never an image or an extracted filesystem.
It does not authenticate an exporter binary, rerun a native scan, validate
SELinux policy, sign AVB, or admit a ROM. The caller must retain the native
execution receipt and trusted tool/image identities separately.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


MAX_MANIFEST_BYTES = 256 * 1024 * 1024
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_CONTRACT_BYTES = 1024 * 1024
MAX_ENTRIES = 100_000
MAX_PATH_BYTES = 4096
MAX_PATH_DEPTH = 128
MAX_IMAGE_BYTES = 64 * 1024**3
MAX_FILE_BYTES = 16 * 1024**3
MAX_XATTR_BYTES = 1024 * 1024
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
TOOL_NAME = "nezha_erofs_metadata"
TYPE_MODES = {
    "regular": stat.S_IFREG, "directory": stat.S_IFDIR,
    "symlink": stat.S_IFLNK, "char": stat.S_IFCHR, "block": stat.S_IFBLK,
    "fifo": stat.S_IFIFO, "socket": stat.S_IFSOCK,
}
HEADER_FIELDS = {
    "record", "schema_version", "tool", "image_size_bytes", "image_sha256",
    "superblock", "superblock_checksum_verified",
}
SUPERBLOCK_FIELDS = {
    "block_size", "root_nid", "inode_count", "primary_blocks", "total_blocks",
    "meta_blkaddr", "xattr_blkaddr", "feature_compat", "feature_incompat",
    "build_time_sec", "build_time_nsec", "uuid_hex", "volume_name_hex",
    "extra_devices", "packed_nid", "xattr_prefix_count",
    "available_compression_algorithms",
}
SUPERBLOCK_SEMANTICS = SUPERBLOCK_FIELDS - {
    "root_nid", "primary_blocks", "total_blocks", "meta_blkaddr", "xattr_blkaddr",
}
ENTRY_FIELDS = {
    "record", "path_hex", "nid", "type", "mode", "uid", "gid", "nlink",
    "size_bytes", "mtime_sec", "mtime_nsec", "rdev", "xattrs",
}
REPLACEMENT_PATHS = {
    "vendor": frozenset({"/etc/selinux/vendor_sepolicy.cil"}),
    "odm": frozenset({
        "/etc/selinux/precompiled_sepolicy",
        "/etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256",
        "/etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256",
        "/etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256",
    }),
}
BOUNDARIES = {
    "native_exporter_reexecuted": False,
    "exporter_binary_authenticated": False,
    "image_data_rehashed_by_this_command": False,
    "image_mutated": False,
    "policy_validated": False,
    "avb_verified": False,
    "phone_accessed": False,
    "complete_rom_admitted": False,
}


class MetadataError(ValueError):
    """Evidence is incomplete, ambiguous, unsupported, or differs from its contract."""


def require(condition, message):
    if not condition:
        raise MetadataError(message)


def _integer(value, name, maximum=2**64 - 1, minimum=0):
    require(type(value) is int and minimum <= value <= maximum,
            f"{name} must be a bounded integer")
    return value


def _digest(value, name):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            f"{name} must be a lowercase SHA256")
    return value


def _hex(value, name, maximum, minimum=0):
    require(type(value) is str and len(value) % 2 == 0
            and minimum * 2 <= len(value) <= maximum * 2
            and re.fullmatch(r"[0-9a-f]*", value) is not None,
            f"{name} must be bounded lowercase hexadecimal bytes")
    return bytes.fromhex(value)


def _path(value):
    path = _hex(value, "path_hex", MAX_PATH_BYTES, 1)
    require(path.startswith(b"/") and b"\0" not in path, "path must be absolute POSIX bytes")
    if path != b"/":
        components = path[1:].split(b"/")
        require(len(components) <= MAX_PATH_DEPTH
                and all(part not in {b"", b".", b".."} and len(part) <= 255
                    for part in components), "path contains an ambiguous component")
    return path


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON object key")
        result[key] = value
    return result


def _constant(value):
    raise MetadataError(f"non-finite JSON value: {value}")


def _json_integer(value):
    require(re.fullmatch(r"[0-9]{1,20}", value) is not None, "JSON integer exceeds the unsigned 64-bit representation bound")
    number = int(value)
    require(number <= 2**64 - 1, "JSON integer exceeds uint64")
    return number


def _json(raw):
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=_constant, parse_int=_json_integer)
    except MetadataError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise MetadataError("invalid UTF-8 JSON evidence") from exc
    require(type(value) is dict, "JSON record must be an object")
    return value


def _signature(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mode,
            value.st_mtime_ns, value.st_ctime_ns)


def _real_parents(path):
    for parent in reversed(path.parents):
        require(stat.S_ISDIR(parent.lstat().st_mode), "evidence ancestors must be real directories")


@contextmanager
def _regular(path, maximum):
    path = Path(os.path.abspath(path))
    _real_parents(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), "evidence must be a regular file")
        require(0 < before.st_size <= maximum, "evidence exceeds its size bound or is empty")
        require(_signature(before) == _signature(path.lstat()), "evidence identity changed before read")
        yield stream, before.st_size
        _real_parents(path)
        require(_signature(before) == _signature(os.fstat(stream.fileno()))
                == _signature(path.lstat()), "evidence changed during read")


def _header(row):
    require(set(row) == HEADER_FIELDS and row["record"] == "header"
            and type(row["schema_version"]) is int and row["schema_version"] == 1
            and row["tool"] == TOOL_NAME
            and row["superblock_checksum_verified"] is True, "unsupported or incomplete native header")
    _digest(row["image_sha256"], "header image hash")
    size = _integer(row["image_size_bytes"], "image size", MAX_IMAGE_BYTES, 16384)
    sb = row["superblock"]
    require(type(sb) is dict and set(sb) == SUPERBLOCK_FIELDS, "unexpected superblock fields")
    for name in SUPERBLOCK_FIELDS - {"uuid_hex", "volume_name_hex"}:
        _integer(sb[name], name)
    _hex(sb["uuid_hex"], "UUID", 16, 16)
    _hex(sb["volume_name_hex"], "volume name", 16, 16)
    require(sb["block_size"] == 4096, "only 4 KiB EROFS exports are admitted")
    require(sb["feature_compat"] & 1 and not sb["feature_compat"] & ~0x7
            and not sb["feature_incompat"] & ~0x1, "unsupported EROFS feature flags")
    require(sb["extra_devices"] == 0 and sb["packed_nid"] == 0
            and sb["xattr_prefix_count"] == 0, "external devices, packed inodes, and long xattr prefixes are not admitted")
    require(sb["root_nid"] <= 0xFFFF, "root NID exceeds the admitted on-disk field")
    require(1 <= sb["inode_count"] <= MAX_ENTRIES, "invalid superblock inode count")
    require(4 <= sb["primary_blocks"] == sb["total_blocks"]
            and sb["total_blocks"] * 4096 <= size, "filesystem data extent exceeds the image")
    require(sb["meta_blkaddr"] < sb["primary_blocks"]
            and sb["xattr_blkaddr"] < sb["primary_blocks"], "metadata block address exceeds the filesystem")
    require(sb["build_time_nsec"] < 10**9, "invalid superblock nanoseconds")
    require(sb["build_time_sec"] <= 2**63 - 1, "superblock timestamp exceeds the admitted range")
    require(sb["available_compression_algorithms"] in {0, 1}, "unsupported compression algorithms")
    return row


def _entry(row, sb):
    kind = row.get("type")
    require(type(kind) is str and kind in TYPE_MODES, "unknown inode type")
    extra = {"content_sha256"} if kind == "regular" else {"symlink_target_hex"} if kind == "symlink" else set()
    require(set(row) == ENTRY_FIELDS | extra and row["record"] == "entry", "unexpected inode fields")
    path = _path(row["path_hex"])
    nid = _integer(row["nid"], "NID")
    require(sb["meta_blkaddr"] * 4096 + nid * 32 + 32 <= sb["primary_blocks"] * 4096,
            "inode lies outside filesystem data")
    mode = _integer(row["mode"], "mode", 0xFFFF)
    require(stat.S_IFMT(mode) == TYPE_MODES[kind], "inode type and mode disagree")
    for name in ("uid", "gid"):
        _integer(row[name], name, 2**32 - 1)
    _integer(row["nlink"], "link count", MAX_ENTRIES, 1)
    size = _integer(row["size_bytes"], "inode size", MAX_FILE_BYTES)
    _integer(row["mtime_sec"], "mtime seconds", 2**63 - 1)
    _integer(row["mtime_nsec"], "mtime nanoseconds", 10**9 - 1)
    if kind in {"char", "block"}:
        # Pinned new_decode_dev consumes a 32-bit 12:20 device encoding;
        # Linux makedev retains those bits in the low 32 bits of dev_t.
        _integer(row["rdev"], "device number", 2**32 - 1)
    else:
        require(row["rdev"] is None, "non-device inode has a device number")
    if kind in {"char", "block", "fifo", "socket"}:
        require(size == 0, "special inode must have zero data size")
    if kind == "directory":
        require(27 <= size <= 16 * 1024 * 1024, "directory size cannot contain a bounded dot-entry table")
    if kind == "regular":
        _digest(row["content_sha256"], "file content hash")
        require(size != 0 or row["content_sha256"] == EMPTY_SHA256, "empty file has a nonempty content hash")
    if kind == "symlink":
        target = _hex(row["symlink_target_hex"], "symlink target", MAX_PATH_BYTES, 1)
        require(b"\0" not in target and len(target) == size, "symlink target and size disagree")
    xattrs = row["xattrs"]
    require(type(xattrs) is list and len(xattrs) <= 1024, "xattrs must be a bounded complete list")
    previous, total = None, 0
    for attr in xattrs:
        require(type(attr) is dict and set(attr) == {"name_hex", "value_hex"}, "invalid xattr record")
        name = _hex(attr["name_hex"], "xattr name", 255, 1)
        value = _hex(attr["value_hex"], "xattr value", 65535)
        require(b"\0" not in name, "xattr name contains NUL")
        require(previous is None or previous < name, "xattr names must be unique and sorted")
        previous = name
        total += len(name) + len(value)
        require(total <= MAX_XATTR_BYTES, "inode xattrs exceed the byte bound")
    return path


@dataclass
class Manifest:
    header: dict
    entries: dict[bytes, dict]
    hardlinks: tuple[tuple[bytes, ...], ...]
    identity: dict


def _directory_links_match(nlink, child_directories):
    expected = 2 + child_directories
    return nlink == expected or (expected > 65535 and nlink == 1)


def read_manifest(path, *, expected_image_sha256=None, expected_manifest_sha256=None):
    """Validate one complete native JSONL capture; do not re-read its image."""
    if expected_image_sha256 is not None:
        _digest(expected_image_sha256, "expected image hash")
    if expected_manifest_sha256 is not None:
        _digest(expected_manifest_sha256, "expected manifest hash")
    digest, count, entries, header, summary = hashlib.sha256(), 0, {}, None, None
    with _regular(path, MAX_MANIFEST_BYTES) as (stream, declared_size):
        while raw := stream.readline(MAX_RECORD_BYTES + 1):
            count += len(raw)
            require(len(raw) <= MAX_RECORD_BYTES and count <= MAX_MANIFEST_BYTES,
                    "native export exceeds its record or total byte bound")
            require(raw.endswith(b"\n"), "native export has a truncated record")
            digest.update(raw)
            row = _json(raw)
            require(summary is None, "native export has records after its summary")
            if header is None:
                header = _header(row)
            elif row.get("record") == "summary":
                require(set(row) == {"record", "entry_count", "image_sha256", "complete"}
                        and row["complete"] is True, "incomplete native summary")
                _integer(row["entry_count"], "summary entry count", MAX_ENTRIES, 1)
                require(row["entry_count"] == len(entries), "summary entry count differs")
                require(row["image_sha256"] == header["image_sha256"], "image changed across native export")
                summary = row
            else:
                require(len(entries) < MAX_ENTRIES, "native export has too many entries")
                name = _entry(row, header["superblock"])
                require(name not in entries, "native export contains a duplicate path")
                entries[name] = row
        require(count == declared_size, "native export length changed during read")
    require(header is not None and summary is not None, "native export lacks its complete summary")
    require(entries.get(b"/", {}).get("type") == "directory", "native export lacks a root directory")
    require(entries[b"/"]["nid"] == header["superblock"]["root_nid"], "root NID differs from the superblock")
    groups, child_directories = defaultdict(list), defaultdict(int)
    for name, row in entries.items():
        if name != b"/":
            parent = name.rsplit(b"/", 1)[0] or b"/"
            require(entries.get(parent, {}).get("type") == "directory", "inode lacks a real directory parent")
            if row["type"] == "directory":
                child_directories[parent] += 1
        groups[row["nid"]].append(name)
    require(len(groups) == header["superblock"]["inode_count"], "reachable inode count differs from the superblock")
    hardlinks = []
    for names in groups.values():
        first = entries[names[0]]
        if first["type"] == "directory":
            require(len(names) == 1, "directory inode alias or cycle")
            require(_directory_links_match(first["nlink"], child_directories[names[0]]),
                    "directory link count differs from immediate subdirectories")
            continue
        require(first["nlink"] == len(names), "non-directory hardlink count differs from paths")
        base = {k: v for k, v in first.items() if k != "path_hex"}
        require(all({k: v for k, v in entries[name].items() if k != "path_hex"} == base
                    for name in names), "aliased inode has contradictory metadata or data")
        if len(names) > 1:
            hardlinks.append(tuple(sorted(names)))
    checksum = digest.hexdigest()
    require(expected_image_sha256 is None or header["image_sha256"] == expected_image_sha256,
            "native export belongs to a different image")
    require(expected_manifest_sha256 is None or checksum == expected_manifest_sha256,
            "native export SHA256 differs from its contract")
    return Manifest(header, entries, tuple(sorted(hardlinks)), {"sha256": checksum, "size_bytes": count})


def manifest_report(manifest):
    counts = {kind: sum(row["type"] == kind for row in manifest.entries.values()) for kind in TYPE_MODES}
    return {
        "schema_version": 1, "operation": "validate-erofs-native-export",
        "manifest": manifest.identity,
        "declared_image": {"sha256": manifest.header["image_sha256"],
                           "size_bytes": manifest.header["image_size_bytes"]},
        "entry_count": len(manifest.entries), "type_counts": counts,
        "hardlink_group_count": len(manifest.hardlinks),
        "superblock": manifest.header["superblock"],
        "structural_validation_passed": True, "boundaries": dict(BOUNDARIES),
    }


def _content_identity(row):
    require(type(row) is dict and set(row) == {"sha256", "size_bytes"}, "unexpected replacement identity")
    _digest(row["sha256"], "replacement content hash")
    _integer(row["size_bytes"], "replacement content size", MAX_FILE_BYTES)


def _contract(value):
    require(set(value) == {"schema_version", "operation", "partition", "before", "after", "replacements"}
            and type(value["schema_version"]) is int and value["schema_version"] == 1
            and value["operation"] == "erofs-policy-data-replacements"
            and type(value["partition"]) is str and value["partition"] in REPLACEMENT_PATHS,
            "unexpected policy replacement contract")
    for name in ("before", "after"):
        identity = value[name]
        require(type(identity) is dict and set(identity) == {"image_sha256", "image_size_bytes", "manifest_sha256"},
                "contract must bind image and native manifest identities")
        _digest(identity["image_sha256"], "contract image hash")
        _digest(identity["manifest_sha256"], "contract manifest hash")
        _integer(identity["image_size_bytes"], "contract image size", MAX_IMAGE_BYTES, 16384)
    rows = value["replacements"]
    require(type(rows) is list and len(rows) == len(REPLACEMENT_PATHS[value["partition"]]),
            "policy replacement set is incomplete")
    replacements = {}
    for row in rows:
        require(type(row) is dict and set(row) == {"path", "before", "after"}
                and type(row["path"]) is str and row["path"] in REPLACEMENT_PATHS[value["partition"]],
                "unreviewed replacement path")
        require(row["path"] not in replacements, "duplicate replacement path")
        _content_identity(row["before"])
        _content_identity(row["after"])
        replacements[row["path"]] = row
    require(set(replacements) == REPLACEMENT_PATHS[value["partition"]], "policy replacement set differs")
    return replacements


def compare(before_path, after_path, contract_path):
    """Permit exactly the bound policy data changes; all other semantics must match."""
    with _regular(contract_path, MAX_CONTRACT_BYTES) as (stream, size):
        raw = stream.read(MAX_CONTRACT_BYTES + 1)
        require(len(raw) == size, "replacement contract changed length")
    contract = _json(raw)
    replacements = _contract(contract)
    manifests = []
    for name, path in (("before", before_path), ("after", after_path)):
        identity = contract[name]
        manifest = read_manifest(path, expected_image_sha256=identity["image_sha256"],
                                 expected_manifest_sha256=identity["manifest_sha256"])
        require(manifest.header["image_size_bytes"] == identity["image_size_bytes"], "contract image size differs")
        manifests.append(manifest)
    before, after = manifests
    require(set(before.entries) == set(after.entries), "filesystem paths were added or removed")
    require(before.hardlinks == after.hardlinks, "hardlink equivalence groups changed")
    for name in sorted(SUPERBLOCK_SEMANTICS):
        require(before.header["superblock"][name] == after.header["superblock"][name],
                f"superblock semantic field changed: {name}")
    applied = []
    for path in sorted(before.entries):
        old, new = before.entries[path], after.entries[path]
        key = path.decode("ascii") if path.isascii() else None
        recipe = replacements.get(key)
        ignored = {"nid"}
        if recipe is not None:
            require(old["type"] == new["type"] == "regular" and old["nlink"] == new["nlink"] == 1,
                    "policy replacements must be single-link regular files")
            for which, row in (("before", old), ("after", new)):
                require({"sha256": row["content_sha256"], "size_bytes": row["size_bytes"]} == recipe[which],
                        f"policy replacement data differs: {key} ({which})")
            ignored |= {"content_sha256", "size_bytes"}
            applied.append({"path": key, "before": recipe["before"], "after": recipe["after"],
                            "content_changed": recipe["before"] != recipe["after"]})
        require({k: v for k, v in old.items() if k not in ignored}
                == {k: v for k, v in new.items() if k not in ignored},
                f"unapproved inode metadata or data change at path_hex={path.hex()}")
    require(len(applied) == len(replacements), "a required policy replacement file is absent")
    return {
        "schema_version": 1, "operation": "compare-erofs-policy-native-exports",
        "partition": contract["partition"],
        "contract": {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
        "before": {**contract["before"], "manifest_size_bytes": before.identity["size_bytes"]},
        "after": {**contract["after"], "manifest_size_bytes": after.identity["size_bytes"]},
        "entry_count": len(before.entries), "hardlink_group_count": len(before.hardlinks),
        "replacements": applied, "paths_preserved": True, "inode_metadata_preserved": True,
        "hardlink_groups_preserved": True, "unselected_data_preserved": True,
        "superblock_semantics_preserved": True, "comparison_passed": True,
        "boundaries": dict(BOUNDARIES),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    validate = sub.add_parser("validate", help="validate a complete native JSONL export without reading an image")
    validate.add_argument("--manifest", required=True, type=Path)
    validate.add_argument("--expected-image-sha256", required=True)
    validate.add_argument("--expected-manifest-sha256")
    comparison = sub.add_parser("compare", help="compare hash-bound exports against the exact policy replacement set")
    comparison.add_argument("--before", required=True, type=Path)
    comparison.add_argument("--after", required=True, type=Path)
    comparison.add_argument("--contract", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation == "validate":
            result = manifest_report(read_manifest(args.manifest, expected_image_sha256=args.expected_image_sha256,
                                                   expected_manifest_sha256=args.expected_manifest_sha256))
        else:
            result = compare(args.before, args.after, args.contract)
    except (MetadataError, OSError) as exc:
        print(f"EROFS metadata: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
