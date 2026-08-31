#!/usr/bin/env python3
"""Read-only Nezha target-files input inventory, never AVB or boot validation.

No images are extracted, changed or signed. ZIP locators in this report are not
filesystem inputs for avb_signing. The optional retained manifest selects only
the two original firmware inputs absent from the reviewed A/B payload list.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile
import zlib

sys.dont_write_bytecode = True

if __package__:
    from . import avb_signing as signing
else:
    import avb_signing as signing

avb = signing.avb
MAX_ARCHIVE = 128 * 1024**3
MAX_CENTRAL_DIRECTORY = 32 * 1024**2
MAX_MEMBERS = 250_000
MAX_DECLARED_BYTES = 128 * 1024**3
MAX_METADATA = 1024**2
MAX_NAME = 4096
PREFIXES = ("IMAGES", "BOOTABLE_IMAGES", "PREBUILT_IMAGES")
REQUIRED_METADATA = ("META/misc_info.txt", "META/ab_partitions.txt",
                     "META/dynamic_partitions_info.txt", "META/vbmeta_digest.txt")
OPTIONAL_METADATA = ("META/apkcerts.txt", "META/apexkeys.txt", "META/otakeys.txt",
                     "META/apex_info.pb", "META/care_map.pb", "META/care_map.txt",
                     "META/otacert", "OTA/android-info.txt", "OTA/android-info-extra.txt",
                     "SYSTEM/etc/security/otacerts.zip",
                     "RECOVERY/RAMDISK/system/etc/security/otacerts.zip",
                     "RECOVERY/RAMDISK/res/keys")
SCOPE = ("image_format_verified", "signatures_verified", "complete_chain_verified",
         "fec_payload_verified", "source_provenance_verified",
         "target_files_compatibility_verified", "physical_partition_fit_verified",
         "runtime_verified", "complete_rom_ready", "native_commands_run",
         "private_key_or_local_config_accessed", "images_extracted_or_modified",
         "signing_manifest_created", "guest_accessed", "phone_accessed")


class TargetFilesInventoryError(ValueError):
    """An unsafe, unreviewed or inconsistent inventory input."""


def _require(condition, message):
    if not condition:
        raise TargetFilesInventoryError(message)


def _base():
    return {"schema_version": 1, "operation": "inspect-nezha-target-files-avb-inputs-v1",
            "status": "blocked", "complete_input_inventory": False,
            "complete_zip_role_inventory": False, "archive_identity_verified": False,
            "inputs_unchanged": False, "scope": {key: False for key in SCOPE},
            "final_images": {}, "generated_vbmeta_images": {}, "aliases": {},
            "metadata": {}, "retained_inputs": {}, "errors": [],
            "missing_final_images": [], "missing_generated_vbmeta_images": [],
            "missing_metadata": [], "missing_retained_inputs": ["countrycode", "pvmfw"]}


def _read_at(stream, offset, length):
    _require(offset >= 0 and length >= 0, "invalid ZIP offset")
    stream.seek(offset)
    data = stream.read(length)
    _require(len(data) == length, "truncated ZIP structure")
    return data


def _zip_bounds(stream, size):
    """Bound stdlib's central-directory allocation before constructing ZipFile.

    This accepts ordinary single-disk ZIP and fixed-size ZIP64 end records, as
    emitted by Android packaging. It does not support prepended executables,
    concatenated archives, multipart archives or ZIP64 extensible end records.
    Member bodies remain entirely the standard library decoder's responsibility.
    """
    _require(_read_at(stream, 0, 4) == b"PK\x03\x04", "expected a native ZIP archive")
    tail = _read_at(stream, max(0, size - 65557), min(size, 65557))
    index = tail.rfind(b"PK\x05\x06")
    _require(index >= 0 and len(tail) - index >= 22, "missing ZIP end record")
    end = struct.unpack_from("<4s4H2IH", tail, index)
    _require(index + 22 + end[7] == len(tail), "ZIP end or comment length differs")
    end_offset = size - len(tail) + index
    disk, directory_disk, disk_count, count, length, offset = end[1:7]
    _require(disk == directory_disk == 0, "multipart ZIP is not supported")
    boundary = end_offset
    locator = _read_at(stream, end_offset - 20, 20) if end_offset >= 20 else b""
    if locator[:4] == b"PK\x06\x07":
        _, locator_disk, zip64_offset, total_disks = struct.unpack("<4sIQI", locator)
        _require(locator_disk == 0 and total_disks == 1 and zip64_offset + 56 == end_offset - 20,
                 "invalid ZIP64 locator")
        record = struct.unpack("<4sQ2H2I4Q", _read_at(stream, zip64_offset, 56))
        _require(record[0] == b"PK\x06\x06" and record[1] == 44
                 and record[4] == record[5] == 0 and record[6] == record[7],
                 "invalid ZIP64 end record")
        for ordinary, sentinel, actual in ((disk_count, 65535, record[6]),
                                           (count, 65535, record[7]),
                                           (length, 0xffffffff, record[8]),
                                           (offset, 0xffffffff, record[9])):
            _require(ordinary in (sentinel, actual), "ZIP and ZIP64 end records disagree")
        disk_count, count, length, offset = record[6:10]
        boundary = zip64_offset
    _require(disk_count == count and 0 < count <= MAX_MEMBERS,
             "ZIP member count exceeds bound or differs")
    _require(0 < length <= MAX_CENTRAL_DIRECTORY and offset > 0 and offset + length == boundary,
             "ZIP central directory bounds differ")
    # Count actual framed records as well as the untrusted declared count. This
    # prevents a false small count from reaching ZipFile's object allocation.
    cursor, found = offset, 0
    while cursor < boundary:
        header = _read_at(stream, cursor, 46)
        _require(header[:4] == b"PK\x01\x02", "invalid central-directory record")
        name, extra, comment = struct.unpack_from("<3H", header, 28)
        _require(0 < name <= MAX_NAME, "ZIP member name exceeds bound")
        cursor += 46 + name + extra + comment
        found += 1
        _require(cursor <= boundary and found <= MAX_MEMBERS,
                 "central-directory record exceeds bound")
    _require(cursor == boundary and found == count, "actual ZIP member count differs")
    return {"member_count": count, "central_directory_size_bytes": length,
            "central_directory_offset": offset}


def _stream_identity(stream, size):
    stream.seek(0)
    digest, count = hashlib.sha256(), 0
    while count < size:
        part = stream.read(min(avb.CHUNK, size - count))
        _require(part, "truncated input")
        count += len(part)
        digest.update(part)
    _require(not stream.read(1), "input grew during read")
    return {"sha256": digest.hexdigest(), "size_bytes": count}


def _regular_member(info):
    mode = info.external_attr >> 16
    return (not info.is_dir() and not (info.external_attr & 0x10)
            and stat.S_IFMT(mode) in (0, stat.S_IFREG))


def _members(archive, bounds, roles):
    entries = archive.infolist()
    _require(len(entries) == bounds["member_count"] and archive.start_dir == bounds["central_directory_offset"],
             "stdlib ZIP directory interpretation differs")
    members, total = {}, 0
    selected = {f"{prefix}/{role}.img" for prefix in PREFIXES for role in roles}
    selected.update(REQUIRED_METADATA + OPTIONAL_METADATA)
    folded = {name.casefold(): name for name in selected}
    for info in entries:
        name = info.filename
        _require(name == info.orig_filename and 0 < len(name) <= MAX_NAME and name.isprintable()
                 and "\\" not in name and not name.startswith("/") and ":" not in name,
                 "noncanonical ZIP member name")
        parts = name.removesuffix("/").split("/")
        _require(all(part and part not in (".", "..") for part in parts),
                 "unsafe ZIP member path")
        _require(name not in members, "duplicate ZIP member name")
        _require(name.casefold() not in folded or name == folded[name.casefold()],
                 "selected ZIP member case alias")
        _require(info.file_size >= 0 and info.compress_size >= 0
                 and info.header_offset >= 0 and info.header_offset < bounds["central_directory_offset"],
                 "invalid ZIP member geometry")
        total += info.file_size
        _require(total <= MAX_DECLARED_BYTES, "declared ZIP payload exceeds bound")
        members[name] = info
    # A selected path cannot sit beneath a symlink/file entry. Do not interpret
    # ordinary unselected symlink targets, nor globally reject Android symlinks.
    for name in selected:
        parts = name.split("/")
        for count in range(1, len(parts)):
            parent = "/".join(parts[:count])
            _require(parent not in members, "selected ZIP ancestor is not a directory")
            if parent + "/" in members:
                entry = members[parent + "/"]
                _require(stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFDIR),
                         "selected ZIP ancestor has non-directory mode")
    return members


def _selected_span(archive, info):
    """Check selected local headers/descriptors which ZipFile treats as hints."""
    local = struct.unpack("<4s5H3I2H", _read_at(archive.fp, info.header_offset, 30))
    _require(local[0] == b"PK\x03\x04" and local[2] == info.flag_bits and local[3] == info.compress_type,
             "selected local/central ZIP header flags differ")
    _require(0 < local[9] <= MAX_NAME, "invalid selected local ZIP name size")
    extra = _read_at(archive.fp, info.header_offset + 30 + local[9], local[10])
    size, compressed, zip64, cursor, seen_zip64 = local[8], local[7], b"", 0, False
    while cursor < len(extra):
        _require(cursor + 4 <= len(extra), "truncated selected local ZIP extra")
        tag, length = struct.unpack_from("<HH", extra, cursor)
        cursor += 4
        _require(cursor + length <= len(extra), "invalid selected local ZIP extra length")
        if tag == 1:
            _require(not seen_zip64, "duplicate selected local ZIP64 extra")
            zip64, seen_zip64 = extra[cursor:cursor + length], True
        cursor += length
    needed = 8 * ((size == 0xffffffff) + (compressed == 0xffffffff))
    _require(len(zip64) == needed and (bool(needed) == seen_zip64), "selected local ZIP64 sizes differ")
    values = iter(struct.unpack("<" + "Q" * (needed // 8), zip64))
    used_zip64 = bool(needed)
    if size == 0xffffffff:
        size = next(values)
    if compressed == 0xffffffff:
        compressed = next(values)
    expected = (info.CRC, info.compress_size, info.file_size)
    if info.flag_bits & 8:
        _require(all(actual in (0, wanted) for actual, wanted in zip((local[6], compressed, size), expected)),
                 "selected local ZIP placeholders differ")
    else:
        _require((local[6], compressed, size) == expected, "selected local/central ZIP sizes or CRC differ")
    start = info.header_offset + 30 + local[9] + local[10]
    end = start + info.compress_size
    following = min([archive.start_dir] + [row.header_offset for row in archive.infolist()
                                           if row.header_offset > info.header_offset])
    _require(start <= end <= following, "selected ZIP compressed span overlaps another record")
    if info.flag_bits & 8:
        fmt = "<IQQ" if used_zip64 or max(info.file_size, info.compress_size) > 0xffffffff else "<III"
        length = struct.calcsize(fmt)
        candidates = [end]
        if end + 4 <= following and _read_at(archive.fp, end, 4) == b"PK\x07\x08":
            candidates.append(end + 4)
        matches = [offset for offset in candidates if offset + length <= following and
                   struct.unpack(fmt, _read_at(archive.fp, offset, length)) == expected]
        _require(len(matches) == 1, "selected ZIP data descriptor differs")
    return start


def _deflate_complete(stream, start, info):
    # ZipExtFile deliberately accepts some truncated DEFLATE streams and clips
    # excess decoded data to the declared size. Independently require the end
    # marker, exact decoded length and no trailing compressed bytes. This uses
    # zlib's bounded decoder, not ZipExtFile's private decompressor state.
    decoder = zlib.decompressobj(-15)
    remaining, cursor, total = info.compress_size, start, 0
    while remaining:
        length = min(avb.CHUNK, remaining)
        data = _read_at(stream, cursor, length)
        cursor += length
        remaining -= length
        while True:
            limit = min(avb.CHUNK, info.file_size - total + 1)
            part = decoder.decompress(data, limit)
            total += len(part)
            _require(total <= info.file_size and not decoder.unused_data,
                     "selected DEFLATE payload exceeds declared span")
            tail = decoder.unconsumed_tail
            _require(not tail or part or tail != data, "selected DEFLATE decoder made no progress")
            data = tail
            if decoder.eof or (not tail and len(part) < limit):
                break
            # Hitting max_length may leave decoded output buffered even when
            # unconsumed_tail is empty. Drain it with the same finite limit.
        _require(not decoder.eof or not remaining, "selected DEFLATE has trailing compressed bytes")
    _require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
             and total == info.file_size, "selected DEFLATE stream is incomplete")


def _member_identity(archive, info, maximum, *, collect=False, allow_empty=False):
    _require(_regular_member(info), "selected ZIP member is not a regular file")
    _require(not (info.flag_bits & (1 | 64)) and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
             "selected ZIP encryption or compression is unsupported")
    _require((0 if allow_empty else 1) <= info.file_size <= maximum,
             "selected ZIP member size exceeds bound")
    start = _selected_span(archive, info)
    if info.compress_type == zipfile.ZIP_STORED:
        _require(info.compress_size == info.file_size, "stored ZIP sizes differ")
    digest, total, chunks = hashlib.sha256(), 0, []
    with archive.open(info, "r") as stream:
        while True:
            part = stream.read(min(avb.CHUNK, maximum - total + 1))
            if not part:
                break
            total += len(part)
            _require(total <= maximum and total <= info.file_size, "selected ZIP member grew")
            digest.update(part)
            if collect:
                chunks.append(part)
    _require(total == info.file_size, "selected ZIP member size differs")
    if info.compress_type == zipfile.ZIP_DEFLATED:
        _deflate_complete(archive.fp, start, info)
    return {"member": info.filename, "sha256": digest.hexdigest(), "size_bytes": total,
            "compression": "stored" if info.compress_type == zipfile.ZIP_STORED else "deflate",
            "crc32": f"{info.CRC:08x}", "locator_kind": "zip-member-not-signing-filesystem-input"}, b"".join(chunks)


def _text(raw):
    value = raw.decode("ascii")
    _require(all(char in "\n\t" or 32 <= ord(char) <= 126 for char in value),
             "noncanonical metadata text")
    return value


def _pairs(raw):
    result = {}
    selected = {"avb_enable", "use_dynamic_partitions", "dynamic_partition_list"}
    for line in _text(raw).split("\n"):
        line = line.strip(" \t")
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        _require(sep and re.fullmatch(r"[a-zA-Z0-9_.-]+", key), "invalid metadata key")
        if key in selected:
            _require(key not in result, "duplicate partition-scope metadata key")
            result[key] = value.strip(" \t")
        # Other fields are hashed, not interpreted. Pinned Android dump macros
        # legitimately repeat some unrelated settings; this is no replacement
        # for common.LoadInfoDict or any native target-files compatibility check.
    return result


def _roles(value, expected):
    _require(type(value) is str, "partition list missing")
    roles = re.split(r"[ \t]+", value.strip(" \t"))
    _require(len(roles) == len(set(roles)) and set(roles) == set(expected),
             "partition list differs or has duplicates")
    return roles


def _metadata_lists(payloads, roles, logical):
    ab = [line.strip(" \t") for line in _text(payloads["META/ab_partitions.txt"]).split("\n") if line.strip(" \t")]
    _require(len(ab) == len(set(ab)) and set(ab) == set(roles), "A/B partition list differs or has duplicates")
    misc = _pairs(payloads["META/misc_info.txt"])
    dynamic = _pairs(payloads["META/dynamic_partitions_info.txt"])
    _require(misc.get("avb_enable") == "true" and misc.get("use_dynamic_partitions") == "true"
             and dynamic.get("use_dynamic_partitions") == "true", "AVB/dynamic metadata scope differs")
    first = _roles(misc.get("dynamic_partition_list"), logical)
    second = _roles(dynamic.get("dynamic_partition_list"), logical)
    digest = _text(payloads["META/vbmeta_digest.txt"])
    _require(re.fullmatch(r"[0-9a-f]{64}\n?", digest), "invalid vbmeta digest text")
    return {"ab_partitions": ab, "dynamic_partitions_in_misc": first,
            "dynamic_partitions_in_dynamic_info": second,
            "vbmeta_digest_recorded_not_verified": digest.removesuffix("\n")}


def _factory_record(contract):
    row = next(row for row in contract["source_evidence"]
               if row["path"] == "research/factory-firmware-validation.json")
    evidence = avb._json(avb._small(signing.ROOT / row["path"], avb.MAX_TEXT, row))
    record = evidence["archive_extraction_receipt"]
    avb._identity_spec(record, path=True)
    return {key: record[key] for key in ("sha256", "size_bytes")}


def _retained(manifest_path, expected_sha, contract, contract_sha, profile):
    value, raw = signing.load_input(manifest_path, expected_sha, contract, contract_sha, profile)
    names = set(profile["raw_leaf_partitions"])
    _require(set(value["images"]) == names, "retained manifest must contain exactly the two raw roles")
    records = value["source_records"]
    expected_record = _factory_record(contract)
    _require(len(records) == 1 and {key: records[0][key] for key in expected_record} == expected_record,
             "retained manifest must pin the recorded factory extraction receipt")
    record = records[0]
    provenance_raw = signing._json_file(record["path"], avb.MAX_TEXT, record)
    _require(type(avb._json(provenance_raw)) is dict, "factory provenance is not a JSON object")
    images, signatures = {}, {}
    for name in sorted(names):
        row = value["images"][name]
        with avb._input(row["path"], profile["image_budgets"][name]) as (stream, info):
            _require(info.st_size == row["size_bytes"], "retained image size differs")
            identity = _stream_identity(stream, info.st_size)
            _require(identity == contract["raw_descriptor_sources"][name]["image"],
                     "retained image identity differs")
            signatures[name] = avb._signature(info)
        images[name] = {**identity, "path": str(row["path"]), "locator_kind": "retained-filesystem-input"}
    return value, raw, images, signatures


def inspect_target_files(target_files: Path, expected_identity: dict, *,
                         retained_input_manifest: Path | None = None,
                         expected_retained_manifest_sha256: str | None = None) -> dict:
    """Return an inventory or a blocked report; never materialize/sign inputs."""
    result = _base()
    try:
        avb._identity_spec(expected_identity)
        _require(expected_identity["size_bytes"] <= MAX_ARCHIVE, "archive exceeds size bound")
        _require((retained_input_manifest is None) == (expected_retained_manifest_sha256 is None),
                 "retained manifest and external digest must be paired")
        contract, contract_sha, profile, profile_sha = signing.load_contract()
        raw_roles = set(profile["raw_leaf_partitions"])
        data_roles = set(contract["input_partitions"]) - raw_roles
        generated = avb.PARTITIONS - set(contract["input_partitions"])
        zip_roles = data_roles | generated
        result["contracts"] = {"signing": {"contract_id": contract["contract_id"], "sha256": contract_sha},
                               "image_set": {"profile_id": profile["profile_id"], "sha256": profile_sha}}
        result["required_roles"] = {"final_data_images": sorted(data_roles),
                                    "generated_vbmeta_images": sorted(generated),
                                    "retained_inputs": sorted(raw_roles)}
        target_files = avb.envelope._absolute_path(target_files)
        with avb._input(target_files, MAX_ARCHIVE) as (stream, info):
            _require(info.st_size == expected_identity["size_bytes"], "archive size differs")
            bounds = _zip_bounds(stream, info.st_size)
            _require(_stream_identity(stream, info.st_size) == expected_identity, "archive identity differs")
            result["archive"] = {"path": str(target_files), **expected_identity, **bounds}
            result["archive_identity_verified"] = True
            with zipfile.ZipFile(stream, "r") as archive:
                members = _members(archive, bounds, zip_roles)
                selected_names = {f"{prefix}/{role}.img" for prefix in PREFIXES for role in zip_roles}
                selected_names.update(REQUIRED_METADATA + OPTIONAL_METADATA)
                read_budget = len(PREFIXES) * sum(profile["image_budgets"][role] for role in zip_roles)
                read_budget += len(REQUIRED_METADATA + OPTIONAL_METADATA) * MAX_METADATA
                _require(sum(members[name].file_size for name in selected_names if name in members) <= read_budget,
                         "selected ZIP read budget exceeded")
                for role in sorted(zip_roles):
                    name = f"IMAGES/{role}.img"
                    field = "final_images" if role in data_roles else "generated_vbmeta_images"
                    missing = "missing_final_images" if role in data_roles else "missing_generated_vbmeta_images"
                    if name not in members:
                        result[missing].append(role)
                        continue
                    row, _ = _member_identity(archive, members[name], profile["image_budgets"][role])
                    if role == "recovery":
                        _require({key: row[key] for key in ("sha256", "size_bytes")} == profile["working76"]["image"],
                                 "selected recovery differs from fixed working76 input")
                    result[field][role] = row
                for prefix in PREFIXES[1:]:
                    for role in sorted(zip_roles):
                        name = f"{prefix}/{role}.img"
                        if name not in members:
                            continue
                        row, _ = _member_identity(archive, members[name], profile["image_budgets"][role])
                        final = result["final_images"].get(role, result["generated_vbmeta_images"].get(role))
                        result["aliases"][name] = {**row, "image_role": role,
                            "matches_final_image": None if final is None else all(row[k] == final[k] for k in ("sha256", "size_bytes"))}
                _require(sum(result["final_images"][role]["size_bytes"] for role in avb.LOGICAL
                             if role in result["final_images"]) <= profile["logical_group_budget"],
                         "selected logical images exceed package group budget")
                payloads = {}
                for name in REQUIRED_METADATA + OPTIONAL_METADATA:
                    if name not in members:
                        if name in REQUIRED_METADATA:
                            result["missing_metadata"].append(name)
                        continue
                    row, payload = _member_identity(archive, members[name], MAX_METADATA,
                                                     collect=name in REQUIRED_METADATA, allow_empty=name in OPTIONAL_METADATA)
                    result["metadata"][name] = row
                    payloads[name] = payload
                if not result["missing_metadata"]:
                    result["partition_lists"] = _metadata_lists(payloads, zip_roles, avb.LOGICAL)
                result["unselected_member_count"] = len(members) - len(result["final_images"]) - len(result["generated_vbmeta_images"]) - len(result["aliases"]) - len(result["metadata"])
                result["complete_zip_role_inventory"] = not any(result[key] for key in
                    ("missing_final_images", "missing_generated_vbmeta_images", "missing_metadata"))
            retained = None
            if retained_input_manifest is not None:
                retained = _retained(retained_input_manifest, expected_retained_manifest_sha256,
                                     contract, contract_sha, profile)
                value, raw, images, signatures = retained
                result["retained_inputs"] = images
                result["retained_manifest"] = {"sha256": avb._sha(raw), "size_bytes": len(raw),
                                               "artifact_set_id": value["artifact_set_id"]}
                result["retained_factory_record"] = {key: value["source_records"][0][key] for key in ("sha256", "size_bytes")}
                result["missing_retained_inputs"] = []
            _require(_stream_identity(stream, info.st_size) == expected_identity, "archive changed during inventory")
            if retained:
                signing._json_file(retained_input_manifest, avb.MAX_TEXT, avb._identity(raw))
                for row in value["source_records"]:
                    signing._json_file(row["path"], avb.MAX_TEXT, row)
                for name, row in value["images"].items():
                    avb._rehash(row["path"], row, signature=signatures[name])
        result["inputs_unchanged"] = True
        result["complete_input_inventory"] = result["complete_zip_role_inventory"] and not result["missing_retained_inputs"]
        result["status"] = "complete" if result["complete_input_inventory"] else "blocked"
    except TargetFilesInventoryError as exc:
        result["errors"].append(str(exc))
    except (avb.AvbImageSetError, signing.AvbSigningError, avb.io.TwrpWorkingError,
            OSError, ValueError, TypeError, KeyError, struct.error, zipfile.BadZipFile,
            RuntimeError, NotImplementedError, EOFError, zlib.error) as exc:
        result["errors"].append("invalid, unavailable or unstable inventory input (" + type(exc).__name__ + ")")
    if result["errors"]:
        result["status"] = "blocked"
        result["complete_input_inventory"] = False
        result["complete_zip_role_inventory"] = False
        result["inputs_unchanged"] = False
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    command = commands.add_parser("inspect")
    command.add_argument("--target-files", required=True, type=Path)
    command.add_argument("--expected-sha256", required=True)
    command.add_argument("--expected-size-bytes", required=True, type=int)
    command.add_argument("--retained-input-manifest", type=Path)
    command.add_argument("--expected-retained-manifest-sha256")
    command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    result = inspect_target_files(args.target_files,
        {"sha256": args.expected_sha256, "size_bytes": args.expected_size_bytes},
        retained_input_manifest=args.retained_input_manifest,
        expected_retained_manifest_sha256=args.expected_retained_manifest_sha256)
    try:
        avb.io._write(args.output, (json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "error": "report output must be a fresh safe path",
                          "error_class": type(exc).__name__, "scope": {key: False for key in SCOPE}}), file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "complete_input_inventory": result["complete_input_inventory"]}))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
