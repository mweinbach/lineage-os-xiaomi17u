#!/usr/bin/env python3
"""Inspect an Android A/B OTA package without applying, extracting or trusting it.

The inspector reads the package's `META-INF/com/android/metadata`,
`payload_properties.txt` and the payload header and manifest, recomputes the
payload and metadata hashes the properties file claims, and optionally compares
every partition's manifest hash with a published image inventory so the OTA is
tied to the same bytes the signed bundle carries. It reports whether the
package carries a whole-file signature footer; it does not verify that
signature cryptographically, which stays with the pinned
`check_ota_package_signature.py` in the build guest.

Payload parsing uses a minimal protobuf wire reader for the fields needed. No
partition data is decoded and nothing is written except the optional report.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

PAYLOAD = "payload.bin"
PROPERTIES = "payload_properties.txt"
METADATA = "META-INF/com/android/metadata"
OPTIONAL = ("META-INF/com/android/metadata.pb", "care_map.pb", "apex_info.pb")
MAGIC = b"CrAU"
HEADER = struct.Struct(">4sQQI")
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_TEXT_BYTES = 1024 * 1024
OPERATION_TYPES = {0: "REPLACE", 1: "REPLACE_BZ", 2: "MOVE", 3: "BSDIFF", 4: "SOURCE_COPY",
                   5: "SOURCE_BSDIFF", 6: "ZERO", 7: "DISCARD", 8: "REPLACE_XZ", 9: "PUFFDIFF",
                   10: "BROTLI_BSDIFF", 11: "ZUCCHINI", 12: "LZ4DIFF_BSDIFF", 13: "LZ4DIFF_PUFFDIFF", 14: "ZSTD"}


class OtaPackageError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise OtaPackageError(message)


def _varint(buffer, position):
    result, shift = 0, 0
    while True:
        require(position < len(buffer), "truncated varint")
        byte = buffer[position]
        position += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, position
        shift += 7
        require(shift < 70, "varint too long")


def fields(buffer):
    """Yield (field number, wire type, value) for one protobuf message."""
    position = 0
    while position < len(buffer):
        key, position = _varint(buffer, position)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, position = _varint(buffer, position)
        elif wire == 1:
            value, position = buffer[position:position + 8], position + 8
            require(len(value) == 8, "truncated fixed64")
        elif wire == 2:
            length, position = _varint(buffer, position)
            value, position = buffer[position:position + length], position + length
            require(len(value) == length, "truncated length-delimited field")
        elif wire == 5:
            value, position = buffer[position:position + 4], position + 4
            require(len(value) == 4, "truncated fixed32")
        else:
            raise OtaPackageError(f"unsupported wire type {wire}")
        yield number, wire, value


def _partition_info(buffer):
    info = {"size_bytes": None, "sha256": None}
    for number, wire, value in fields(buffer):
        if number == 1 and wire == 0:
            info["size_bytes"] = value
        elif number == 2 and wire == 2:
            info["sha256"] = value.hex()
    return info


def _partition(buffer):
    row = {"name": None, "old": None, "new": None, "operations": 0, "operation_types": {},
           "version": None, "run_postinstall": False, "estimate_cow_size": None}
    for number, wire, value in fields(buffer):
        if number == 1 and wire == 2:
            row["name"] = value.decode("utf-8")
        elif number == 2 and wire == 0:
            row["run_postinstall"] = bool(value)
        elif number == 6 and wire == 2:
            row["old"] = _partition_info(value)
        elif number == 7 and wire == 2:
            row["new"] = _partition_info(value)
        elif number == 8 and wire == 2:
            row["operations"] += 1
            kind = next((v for n, w, v in fields(value) if n == 1 and w == 0), None)
            label = OPERATION_TYPES.get(kind, f"type-{kind}")
            row["operation_types"][label] = row["operation_types"].get(label, 0) + 1
        elif number == 17 and wire == 2:
            row["version"] = value.decode("utf-8")
        elif number == 19 and wire == 0:
            row["estimate_cow_size"] = value
    require(row["name"], "partition without a name")
    require(row["new"] and row["new"]["sha256"], f"partition {row['name']} lacks new_partition_info")
    return row


def _dynamic_metadata(buffer):
    result = {"groups": [], "snapshot_enabled": None, "vabc_enabled": None,
              "vabc_compression_param": None, "cow_version": None}
    for number, wire, value in fields(buffer):
        if number == 1 and wire == 2:
            group = {"name": None, "size_bytes": None, "partitions": []}
            for n, w, v in fields(value):
                if n == 1 and w == 2:
                    group["name"] = v.decode("utf-8")
                elif n == 2 and w == 0:
                    group["size_bytes"] = v
                elif n == 3 and w == 2:
                    group["partitions"].append(v.decode("utf-8"))
            result["groups"].append(group)
        elif number == 2 and wire == 0:
            result["snapshot_enabled"] = bool(value)
        elif number == 3 and wire == 0:
            result["vabc_enabled"] = bool(value)
        elif number == 4 and wire == 2:
            result["vabc_compression_param"] = value.decode("utf-8")
        elif number == 5 and wire == 0:
            result["cow_version"] = value
    return result


def parse_manifest(buffer):
    manifest = {"block_size": None, "minor_version": None, "max_timestamp": None,
                "partial_update": False, "security_patch_level": None,
                "partitions": [], "dynamic_partition_metadata": None}
    for number, wire, value in fields(buffer):
        if number == 3 and wire == 0:
            manifest["block_size"] = value
        elif number == 12 and wire == 0:
            manifest["minor_version"] = value
        elif number == 13 and wire == 2:
            manifest["partitions"].append(_partition(value))
        elif number == 14 and wire == 0:
            manifest["max_timestamp"] = value
        elif number == 15 and wire == 2:
            manifest["dynamic_partition_metadata"] = _dynamic_metadata(value)
        elif number == 16 and wire == 0:
            manifest["partial_update"] = bool(value)
        elif number == 18 and wire == 2:
            manifest["security_patch_level"] = value.decode("utf-8")
    names = [row["name"] for row in manifest["partitions"]]
    require(len(names) == len(set(names)), "duplicate partition in payload manifest")
    manifest["is_full_update"] = all(row["old"] is None for row in manifest["partitions"])
    return manifest


def _text_member(archive, name):
    info = archive.getinfo(name)
    require(info.file_size <= MAX_TEXT_BYTES, f"{name} exceeds {MAX_TEXT_BYTES} bytes")
    return archive.read(name).decode("utf-8")


def parse_properties(text):
    values = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        require("=" in line, f"malformed property line: {line!r}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def read_payload(archive):
    """Stream the payload once: header, manifest, whole-file and metadata hashes."""
    info = archive.getinfo(PAYLOAD)
    whole = hashlib.sha256()
    with archive.open(PAYLOAD) as stream:
        head = stream.read(HEADER.size)
        require(len(head) == HEADER.size, "payload shorter than its header")
        magic, version, manifest_size, signature_size = HEADER.unpack(head)
        require(magic == MAGIC, "payload magic is not CrAU")
        require(version == 2, f"unsupported payload major version {version}")
        require(0 < manifest_size <= MAX_MANIFEST_BYTES, "payload manifest size out of bounds")
        manifest_raw = stream.read(manifest_size)
        require(len(manifest_raw) == manifest_size, "payload manifest truncated")
        metadata_size = HEADER.size + manifest_size
        metadata_hash = hashlib.sha256(head + manifest_raw).hexdigest()
        whole.update(head)
        whole.update(manifest_raw)
        consumed = metadata_size
        while chunk := stream.read(8 * 1024 * 1024):
            whole.update(chunk)
            consumed += len(chunk)
    require(consumed == info.file_size, "payload member size differs from its central directory entry")
    return {
        "major_version": version, "manifest_size": manifest_size, "metadata_size": metadata_size,
        "metadata_signature_size": signature_size, "file_size": info.file_size,
        "file_sha256": whole.hexdigest(), "metadata_sha256": metadata_hash,
        "manifest": parse_manifest(manifest_raw),
    }


def signature_footer(archive):
    comment = archive.comment
    if len(comment) < 6:
        return {"present": False, "reason": "zip comment shorter than the six-byte footer"}
    signature_start, marker, comment_size = struct.unpack("<HHH", comment[-6:])
    if marker != 0xFFFF or comment_size != len(comment):
        return {"present": False, "reason": "footer markers do not match a signed package"}
    return {"present": True, "comment_bytes": len(comment), "signature_start_from_end": signature_start,
            "cryptographically_verified_here": False}


def _b64(hex_digest):
    return base64.b64encode(bytes.fromhex(hex_digest)).decode("ascii")


def inspect(package, inventory_path=None):
    package = Path(package)
    require(not package.is_symlink() and package.is_file(), f"package is missing or a symlink: {package}")
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        for name in (PAYLOAD, PROPERTIES, METADATA):
            require(name in names, f"package lacks {name}")
        metadata = parse_properties(_text_member(archive, METADATA))
        properties = parse_properties(_text_member(archive, PROPERTIES))
        payload = read_payload(archive)
        footer = signature_footer(archive)
        optional = {name: name in names for name in OPTIONAL}
    require(metadata.get("ota-type") == "AB", f"ota-type is {metadata.get('ota-type')!r}, not AB")
    checks = {
        "file_size_matches": properties.get("FILE_SIZE") == str(payload["file_size"]),
        "file_hash_matches": properties.get("FILE_HASH") == _b64(payload["file_sha256"]),
        "metadata_size_matches": properties.get("METADATA_SIZE") == str(payload["metadata_size"]),
        "metadata_hash_matches": properties.get("METADATA_HASH") == _b64(payload["metadata_sha256"]),
    }
    manifest = payload["manifest"]
    report = {
        "operation": "inspect-nezha-ota-package", "package": str(package),
        "metadata": metadata, "payload_properties": properties,
        "payload": {key: payload[key] for key in ("major_version", "manifest_size", "metadata_size",
                                                   "metadata_signature_size", "file_size", "file_sha256")},
        "manifest": {
            "block_size": manifest["block_size"], "minor_version": manifest["minor_version"],
            "max_timestamp": manifest["max_timestamp"], "partial_update": manifest["partial_update"],
            "security_patch_level": manifest["security_patch_level"],
            "is_full_update": manifest["is_full_update"],
            "dynamic_partition_metadata": manifest["dynamic_partition_metadata"],
            "partitions": [{"name": row["name"], "new": row["new"], "old": row["old"],
                            "operations": row["operations"], "operation_types": row["operation_types"],
                            "version": row["version"], "run_postinstall": row["run_postinstall"],
                            "estimate_cow_size": row["estimate_cow_size"]} for row in manifest["partitions"]],
        },
        "optional_members": optional, "whole_file_signature": footer, "property_checks": checks,
        "incremental": "pre-build" in metadata,
        "inventory_comparison": None,
        "scope": {"applied": False, "extracted": False, "signature_verified": False, "device_accessed": False},
    }
    if inventory_path is not None:
        report["inventory_comparison"] = compare_inventory(manifest, Path(inventory_path))
    report["structurally_consistent"] = all(checks.values())
    report["matches_inventory"] = (report["inventory_comparison"] or {}).get("all_match")
    return report


def compare_inventory(manifest, inventory_path):
    require(not inventory_path.is_symlink() and inventory_path.is_file(), "published inventory is missing")
    inventory = json.loads(inventory_path.read_bytes())
    roles = {**inventory.get("final_images", {}), **inventory.get("generated_vbmeta_images", {})}
    expected = inventory.get("partition_lists", {}).get("ab_partitions")
    require(isinstance(expected, list) and expected, "published inventory lacks its ab_partitions list")
    rows = {row["name"]: row for row in manifest["partitions"]}
    result = {"matched": [], "mismatched": [], "missing_from_payload": [], "unexpected_in_payload": [],
              "missing_from_inventory": []}
    for name in expected:
        if name not in rows:
            result["missing_from_payload"].append(name)
            continue
        record = roles.get(name)
        if record is None:
            result["missing_from_inventory"].append(name)
            continue
        new = rows[name]["new"]
        if new["sha256"] == record.get("sha256") and new["size_bytes"] == record.get("size_bytes"):
            result["matched"].append(name)
        else:
            result["mismatched"].append({"name": name, "payload": new,
                                         "inventory": {"sha256": record.get("sha256"), "size_bytes": record.get("size_bytes")}})
    result["unexpected_in_payload"] = sorted(set(rows) - set(expected))
    result["all_match"] = (len(result["matched"]) == len(expected)
                           and not result["mismatched"] and not result["unexpected_in_payload"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("inspect")
    command.add_argument("--package", type=Path, required=True)
    command.add_argument("--published-inventory", type=Path)
    command.add_argument("--output", type=Path, help="Write the report here; refuses an existing path")
    args = parser.parse_args(argv)
    try:
        report = inspect(args.package, args.published_inventory)
        if args.output:
            require(not args.output.exists() and not args.output.is_symlink(), f"output exists: {args.output}")
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (OtaPackageError, zipfile.BadZipFile, KeyError, OSError, UnicodeDecodeError, ValueError) as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    ok = report["structurally_consistent"] and report["matches_inventory"] is not False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
