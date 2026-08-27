#!/usr/bin/env python3
"""Prepare exact, inert Nezha kernel inputs from hash-bound capture receipts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
import tempfile

if __package__:
    from .artifact_files import publish_new_directory
    from .firmware import IntakeError, _directory, _open_regular, _signature
else:
    from artifact_files import publish_new_directory
    from firmware import IntakeError, _directory, _open_regular, _signature


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 256 * 1024**2
MAX_JSON_BYTES = 16 * 1024**2
MAX_TOTAL_BYTES = 2 * 1024**3
MAX_FILES = 4096
SETS = ("vendor_ramdisk", "vendor_dlkm", "system_dlkm")
ROLES = {"kernel", "dtb", "dtbo", "kernel_config", "vendor_ramdisk",
         "init_ramdisk", "recovery_ramdisk", "bootconfig"}
OPTIONAL_ROLES = {"fstab"}
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9_+.-]+\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class KernelInputsError(ValueError):
    """The proposed package does not meet the declared input contract."""


def _require(condition, message):
    if not condition:
        raise KernelInputsError(message)


def _integer(value, minimum, maximum, what):
    _require(type(value) is int and minimum <= value <= maximum, f"invalid {what}")
    return value


def _relative(value):
    _require(isinstance(value, str) and 0 < len(value) <= 4096, "invalid relative path")
    parts = value.split("/")
    _require(all(part not in ("", ".", "..") and SAFE_COMPONENT.fullmatch(part)
                 for part in parts), "unsafe path or make expression")
    return value


def _digest(value):
    _require(isinstance(value, str) and SHA256.fullmatch(value), "invalid SHA256")
    return value


def _real_parents(path):
    for parent in [*reversed(path.parents), path]:
        _require(stat.S_ISDIR(parent.lstat().st_mode),
                 "input/output ancestors must be real directories, not symlinks")


def _read(path, expected=None, *, limit=MAX_FILE_BYTES):
    path = Path(os.path.abspath(path))
    _real_parents(path.parent)
    with _open_regular(path) as stream:
        details = os.fstat(stream.fileno())
        _require(details.st_nlink == 1, "hard-linked inputs are not accepted")
        signature = _signature(details)
        _require(details.st_size <= limit, "input exceeds size bound")
        data = stream.read(limit + 1)
        _require(len(data) <= limit, "input exceeds size bound")
        _require(signature == _signature(os.fstat(stream.fileno()))
                 and signature == _signature(path.lstat()), "input changed while read")
    if expected is not None:
        _require(hashlib.sha256(data).hexdigest() == _digest(expected), "input SHA256 mismatch")
    return data


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    try:
        result = json.loads(data, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise KernelInputsError("invalid JSON input") from exc
    _require(isinstance(result, dict), "JSON input must be an object")
    return result


def _contract(data):
    value = _json(data)
    _require(type(value.get("schema_version")) is int and value["schema_version"] == 1,
             "unsupported kernel contract schema")
    _require(value.get("device") == {"codename": "nezha", "hardware_region": "CN", "soc": "SM8850"},
             "contract must identify China Nezha / SM8850")
    kernel = value["kernel"]
    _require(kernel.get("architecture") == "arm64" and kernel.get("page_size_bytes") == 4096
             and kernel.get("boot_header_version") == 4, "only the verified 4K boot-v4 contract is supported")
    _require(isinstance(kernel.get("release"), str)
             and SAFE_COMPONENT.fullmatch(kernel["release"]) and len(kernel["release"]) <= 200,
             "unsafe kernel release")
    for field in ("dtb_count", "dtbo_count"):
        _integer(kernel[field], 1, 256, field)
    _require(kernel.get("dtbo_board_id") == [8, 0] and kernel.get("dtbo_miboard_id") == [5, 0],
             "Nezha board identities must not be substituted with sibling identities")
    provenance = value["provenance"]
    _digest(provenance["parent_package_sha256"])
    _require(type(provenance.get("origin_verified")) is bool, "origin verification must be explicit")
    for field in ("source_kind", "package_kind"):
        _require(isinstance(provenance.get(field), str) and provenance[field], "missing provenance")
    _require("source_url" in provenance, "unknown source URL must be explicit")
    validation = value["validation"]
    _require(validation.get("input_avb_status") in ("failed", "unverified", "verified-external"),
             "input AVB status must be explicit")
    for field in ("kernel_abi_verified", "module_signatures_verified", "device_tested"):
        _require(validation.get(field) is False, "packaging cannot assert ABI, signing trust or device tests")
    _require(set(value["module_sets"]) == set(SETS)
             and set(value["expected_module_counts"]) == set(SETS), "all three module stages are required")
    for count in value["expected_module_counts"].values():
        _integer(count, 1, MAX_FILES, "module count")
    _require(isinstance(value["files"], list), "input roles must be a list")
    roles = [item.get("role") for item in value["files"]]
    _require(len(roles) == len(set(roles)) and ROLES <= set(roles)
             and set(roles) <= ROLES | OPTIONAL_ROLES, "all eight input roles are required, without duplicates")
    return value


def _fdt(data):
    _require(len(data) >= 40, "truncated FDT")
    magic, total, off_struct, off_strings, _, version, _, _, strings_size, struct_size = struct.unpack_from(">10I", data)
    _require(magic == 0xD00DFEED and 40 <= total <= len(data) and version >= 17, "invalid FDT header")
    _require(40 <= off_struct <= total - struct_size and 40 <= off_strings <= total - strings_size,
             "FDT section out of bounds")
    _require(off_struct + struct_size <= off_strings or off_strings + strings_size <= off_struct,
             "overlapping FDT sections")
    pos, depth, root_seen, props = off_struct, 0, False, {}
    end = off_struct + struct_size
    strings = data[off_strings:off_strings + strings_size]
    while pos + 4 <= end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == 1:
            stop = data.find(b"\0", pos, end)
            _require(stop >= pos and stop - pos <= 255 and depth < 128, "invalid FDT node")
            if depth == 0:
                _require(not root_seen and stop == pos, "invalid FDT root")
                root_seen = True
            depth += 1
            pos = (stop + 4) & ~3
        elif token == 2:
            _require(depth > 0, "unbalanced FDT node")
            depth -= 1
        elif token == 3:
            _require(depth > 0 and pos + 8 <= end, "invalid FDT property")
            size, offset = struct.unpack_from(">II", data, pos)
            pos += 8
            _require(size <= end - pos and offset < len(strings), "FDT property out of bounds")
            stop = strings.find(b"\0", offset)
            _require(stop >= offset and stop - offset <= 255, "invalid FDT property name")
            name = strings[offset:stop]
            if depth == 1:
                _require(name not in props, "duplicate FDT root property")
                props[name] = data[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            _require(root_seen and depth == 0, "unbalanced FDT tree")
            return total, props
        else:
            raise KernelInputsError("unknown FDT token")
        _require(pos <= end, "FDT token exceeds section")
    raise KernelInputsError("FDT end token missing")


def _validate_role(role, data, kernel):
    if role == "kernel":
        _require(len(data) >= 64 and data[56:60] == b"ARM\x64", "not an ARM64 Image")
        _require((struct.unpack_from("<Q", data, 24)[0] >> 1) & 3 == 1, "kernel Image is not marked 4K")
        _require(("Linux version " + kernel["release"] + " ").encode() in data,
                 "kernel release does not match its contract")
    elif role == "kernel_config":
        text = data.decode("ascii")
        entries = set(text.splitlines())
        for option in ("ARM64_4K_PAGES", "MODULES", "MODVERSIONS", "MODULE_SIG", "DM_VERITY", "SECURITY_SELINUX"):
            _require(f"CONFIG_{option}=y" in entries, f"required recorded kernel option absent: {option}")
        for option in ("ARM64_16K_PAGES", "ARM64_64K_PAGES", "SECURITY_SELINUX_BOOTPARAM"):
            _require(f"CONFIG_{option}=y" not in entries, f"conflicting recorded kernel option: {option}")
    elif role == "dtb":
        pos, count = 0, 0
        while pos < len(data):
            total, props = _fdt(data[pos:])
            compatibles = props.get(b"compatible", b"").split(b"\0")
            _require(b"qcom,canoe" in compatibles or b"qcom,canoep" in compatibles,
                     "DTB does not describe the captured Canoe platform")
            pos += total
            count += 1
            _require(count <= 256, "too many DTBs")
        _require(count == kernel["dtb_count"], "DTB count does not match contract")
    elif role == "dtbo":
        _require(len(data) >= 32, "truncated DTBO table")
        magic, total, header, entry_size, count, offset, page, version = struct.unpack_from(">8I", data)
        _require(magic == 0xD7B7AB1E and 32 <= header <= offset and entry_size == 32
                 and version == 0 and page == 4096 and count == kernel["dtbo_count"]
                 and offset + count * entry_size <= total <= len(data), "invalid DTBO table")
        intervals = []
        for index in range(count):
            size, start = struct.unpack_from(">II", data, offset + index * entry_size)
            _require(offset + count * entry_size <= start <= total - size, "DTBO entry out of bounds")
            _require(all(start + size <= left or right <= start for left, right in intervals),
                     "overlapping DTBO entries")
            intervals.append((start, start + size))
            tree_size, props = _fdt(data[start:start + size])
            _require(tree_size == size, "DTBO entry size mismatch")
            model = props.get(b"model", b"").lower()
            _require(b"nezha" in model and b"sm8850" in model, "DTBO is not identified as Nezha SM8850")
            for field, name in (("dtbo_board_id", b"qcom,board-id"), ("dtbo_miboard_id", b"xiaomi,miboard-id")):
                _require(props.get(name) == struct.pack(">2I", *kernel[field]), "wrong Nezha DTBO board identity")
    elif role in ("vendor_ramdisk", "init_ramdisk", "recovery_ramdisk"):
        _require(data.startswith(b"\x02\x21\x4c\x18"), "expected captured legacy LZ4 ramdisk")
    elif role in ("bootconfig", "fstab"):
        _require(len(data) <= 1024**2 and b"\0" not in data, "invalid bootconfig reference")
        data.decode("ascii")


def _load_receipts(contract, source_root):
    receipts = {}
    _require(isinstance(contract["receipts"], dict) and 1 <= len(contract["receipts"]) <= 16,
             "invalid receipt count")
    for name, ref in contract["receipts"].items():
        _relative(name)
        path = source_root / _relative(ref["path"])
        raw = _read(path, ref["sha256"], limit=MAX_JSON_BYTES)
        value = _json(raw)
        _require(type(value.get("schema_version")) is int and value["schema_version"] == 1,
                 "unsupported source receipt schema")
        kind = ref["type"]
        if kind in ("boot-analysis", "archive-images"):
            _require(value.get("parent_package_sha256") == contract["provenance"]["parent_package_sha256"],
                     "source receipt belongs to a different firmware package")
            rows = value["artifacts" if kind == "boot-analysis" else "images"]
            if kind == "archive-images":
                provenance = value["intake_provenance"]
                _require(provenance.get("device") == "nezha" and provenance.get("region") == "CN",
                         "intake did not identify China Nezha")
                _require(provenance.get("sha256") == contract["provenance"]["parent_package_sha256"],
                         "intake package SHA256 contradicts source receipt")
                for key in ("source_kind", "source_url", "origin_verified"):
                    _require(provenance.get(key) == contract["provenance"].get(key),
                             "contract contradicts preserved intake provenance")
        elif kind == "avb-verification":
            _require(value.get("parent_package_sha256") == contract["provenance"]["parent_package_sha256"],
                     "AVB receipt belongs to another package")
            _require(value.get("verification_bypass_flags_used") is False
                     and value.get("images_padded_or_patched") is False,
                     "AVB receipt contains verification bypasses or patched inputs")
            if value.get("full_avb_verification_passed") is not True:
                _require(contract["validation"]["input_avb_status"] != "verified-external",
                         "contract conceals an incomplete or failed AVB result")
            rows = []
        elif kind == "erofs-capture":
            _require(value.get("operation") == "erofs-capture"
                     and value.get("firmware_executed") is False
                     and value.get("image_mounted") is False and value.get("symlinks_followed") is False,
                     "unsupported EROFS capture safety contract")
            _require(value.get("origin_verified") == contract["provenance"]["origin_verified"],
                     "capture origin differs from contract")
            if "image_sha256" in ref:
                _require(value["image"]["sha256"] == _digest(ref["image_sha256"]),
                         "module capture belongs to a different logical image")
            rows = value["files"]
        else:
            raise KernelInputsError("unsupported source receipt type")
        _require(isinstance(rows, list) and len(rows) <= MAX_FILES, "invalid receipt file count")
        records = {}
        for row in rows:
            key = row["path"]
            _require(isinstance(key, str) and key not in records, "duplicate receipt file path")
            records[key] = row
        receipts[name] = {"reference": ref, "path": path, "raw": raw, "data": value, "records": records}
    if contract["validation"]["input_avb_status"] == "verified-external":
        audits = [item["data"] for item in receipts.values()
                  if item["reference"]["type"] == "avb-verification"]
        _require(audits and all(item.get("full_avb_verification_passed") is True
                               and item.get("trusted_oem_key_supplied") is True
                               and item.get("inputs_unchanged") is True for item in audits),
                 "verified-external AVB requires a complete, hash-bound trusted-key verification receipt")
    return receipts


def _member(receipt, member):
    record = receipt["records"].get(member)
    _require(record is not None, "requested member is absent from receipt")
    kind = receipt["reference"]["type"]
    if kind == "boot-analysis":
        _require(record.get("kind") == "regular", "selected boot artifact is not regular")
    elif kind == "archive-images":
        _require(record.get("crc_verified") is True or record.get("readback_verified") is True,
                 "archive image integrity was not verified")
    else:
        _require(record.get("type") == "regular" and record.get("readback_verified") is True,
                 "selected capture file is not a verified regular file")
    relative = record.get("output_path", member)
    data = _read(receipt["path"].parent / _relative(relative), record["sha256"])
    _require(len(data) == _integer(record["size_bytes"], 0, MAX_FILE_BYTES, "member size"),
             "member size mismatch")
    return data


def _module_payloads(spec, receipts):
    receipt = receipts[spec["receipt"]]
    if spec["source"] == "erofs-capture":
        _require(receipt["reference"]["type"] == "erofs-capture", "wrong module capture format")
        for member in receipt["records"]:
            if member.startswith("/lib/modules/"):
                yield member.removeprefix("/lib/modules/"), _member(receipt, member), receipt, member
    elif spec["source"] == "cpio-inventory":
        _require(receipt["reference"]["type"] == "boot-analysis", "wrong ramdisk capture format")
        archive = _member(receipt, spec["cpio_member"])
        inventory = _json(_member(receipt, spec["inventory_member"]))
        _require(inventory.get("cpio_sha256") == hashlib.sha256(archive).hexdigest(),
                 "CPIO inventory does not describe the supplied archive")
        entries = inventory["entries"]
        _require(isinstance(entries, list) and len(entries) <= MAX_FILES, "CPIO entry count exceeds bound")
        for entry in entries:
            member = entry["name"]
            _require(isinstance(member, str), "invalid CPIO member name")
            if not member.startswith("lib/modules/"):
                continue
            if entry["kind"] == stat.S_IFDIR:
                continue
            _require(entry["kind"] == stat.S_IFREG and entry["nlink"] == 1,
                     "module CPIO member is a link or special file")
            offset = _integer(entry["content_offset"], 0, len(archive), "CPIO offset")
            size = _integer(entry["size_bytes"], 0, MAX_FILE_BYTES, "CPIO member size")
            _require(size <= len(archive) - offset, "CPIO member extends outside archive")
            data = archive[offset:offset + size]
            _require(hashlib.sha256(data).hexdigest() == _digest(entry["sha256"]), "CPIO member SHA256 mismatch")
            yield member.removeprefix("lib/modules/"), data, receipt, member
    else:
        raise KernelInputsError("unsupported module source")


def _load_list(data, modules):
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise KernelInputsError("module load list must be ASCII") from exc
    entries = []
    names = {PurePosixPath(path).name for path in modules}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        _relative(line)
        name = PurePosixPath(line).name
        _require(name.endswith(".ko") and name in names, "load list references absent module")
        entries.append(name)
    return entries


def _makefile(contract, sets, roles, purpose):
    lines = ["# Generated from verified capture hashes; not a device or signing validation.",
             "NEZHA_STOCK_INPUTS_SCHEMA_VERSION := 1",
             f"NEZHA_STOCK_INPUTS_PURPOSE := {purpose}",
             f"NEZHA_STOCK_KERNEL_RELEASE := {contract['kernel']['release']}",
             f"NEZHA_STOCK_INPUTS_PACKAGE_SHA256 := {contract['provenance']['parent_package_sha256']}",
             f"NEZHA_STOCK_INPUT_AVB_STATUS := {contract['validation']['input_avb_status']}",
             "NEZHA_STOCK_INPUT_ORIGIN_VERIFIED := " + str(contract["provenance"]["origin_verified"]).lower()]
    for role, name in (("kernel", "KERNEL"), ("dtbo", "DTBO")):
        lines.append(f"NEZHA_STOCK_{name} := $(NEZHA_KERNEL_INPUTS)/{roles[role]}")
    lines.append(f"NEZHA_STOCK_DTB_DIR := $(NEZHA_KERNEL_INPUTS)/{PurePosixPath(roles['dtb']).parent}")
    for stage, prefix in (("vendor_ramdisk", "VENDOR_RAMDISK"), ("vendor_dlkm", "VENDOR"), ("system_dlkm", "SYSTEM")):
        item = sets[stage]
        lines.append(f"NEZHA_STOCK_{prefix}_MODULES := " +
                     " \\\n    ".join("$(NEZHA_KERNEL_INPUTS)/" + path for path in item["modules"]))
        lines.append(f"NEZHA_STOCK_{prefix}_MODULES_LOAD := " + " ".join(item["load_list"]["entries"] or ["false"]))
        lines.append(f"NEZHA_STOCK_{prefix}_MODULES_BLOCKLIST_FILE := " +
                     ("$(NEZHA_KERNEL_INPUTS)/" + item["blocklist"] if item["blocklist"] else ""))
    recovery = sets["vendor_ramdisk"]["recovery_load_list"]
    lines.append("NEZHA_STOCK_VENDOR_RAMDISK_RECOVERY_MODULES_LOAD := " +
                 " ".join(recovery["entries"] if recovery else []))
    return ("\n".join(lines) + "\n").encode()


def _package_inputs(contract_path, source_root, output_dir, *, purpose, workspace_root):
    """Copy only hash-bound regular payloads to a new, ignored artifact bundle."""
    _require(purpose in ("research", "build-candidate"), "unsupported packaging purpose")
    source_root = Path(os.path.abspath(source_root))
    workspace_root = Path(os.path.abspath(workspace_root))
    output_dir = Path(os.path.abspath(output_dir))
    _real_parents(source_root)
    _real_parents(workspace_root)
    _require(workspace_root / "artifacts" in output_dir.parents, "output must be inside ignored workspace artifacts/")
    _require(source_root not in output_dir.parents and output_dir not in source_root.parents
             and source_root != output_dir, "output must not overlap immutable source inputs")
    _require(not os.path.lexists(output_dir), "output already exists; refusing replacement")
    source_identity = source_root.stat()
    for ancestor in output_dir.parents:
        try:
            _require(not os.path.samestat(ancestor.stat(), source_identity),
                     "output aliases an immutable source directory")
        except FileNotFoundError:
            continue
    _relative(output_dir.name)
    contract_raw = _read(contract_path, limit=MAX_JSON_BYTES)
    contract = _contract(contract_raw)
    receipts = _load_receipts(contract, source_root)
    parent = _directory(output_dir.parent)
    _require(shutil.disk_usage(parent).free >= MAX_FILE_BYTES + 64 * 1024**2,
             "insufficient free space for kernel inputs")
    lock = parent / ("." + output_dir.name + ".lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    staging = None
    records, names, total = [], set(), 0
    try:
        staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + "-", dir=parent))
        def publish(relative, data, receipt=None, member=None):
            nonlocal total
            _relative(relative)
            folded = relative.casefold()
            _require(folded not in names, "duplicate or case-colliding output")
            names.add(folded)
            total += len(data)
            _require(len(records) < MAX_FILES and total <= MAX_TOTAL_BYTES, "package size or file count exceeds bound")
            _require(shutil.disk_usage(parent).free >= len(data) + 64 * 1024**2, "insufficient output space")
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                os.chmod(destination, 0o600)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            digest = hashlib.sha256(data).hexdigest()
            _read(destination, digest)
            record = {"path": relative, "size_bytes": len(data), "sha256": digest,
                      "source_receipt_sha256": receipt["reference"]["sha256"] if receipt else None,
                      "source_member": member, "readback_verified": True}
            records.append(record)
            return relative

        roles = {}
        for item in contract["files"]:
            receipt = receipts[item["receipt"]]
            data = _member(receipt, item["member"])
            _validate_role(item["role"], data, contract["kernel"])
            roles[item["role"]] = publish(item["output"], data, receipt, item["member"])
        sets = {}
        for stage in SETS:
            modules, metadata, basenames = [], {}, set()
            for relative, data, receipt, member in _module_payloads(contract["module_sets"][stage], receipts):
                _relative(relative)
                output = "modules/" + stage + "/" + relative
                if relative.endswith(".ko"):
                    _require(len(data) >= 64 and data[:6] == b"\x7fELF\x02\x01"
                             and struct.unpack_from("<HH", data, 16) == (1, 183),
                             "module is not an ARM64 ELF relocatable object")
                    name = PurePosixPath(relative).name.casefold()
                    _require(name not in basenames, "duplicate module basename would collide in Android output")
                    basenames.add(name)
                    modules.append(output)
                else:
                    name = PurePosixPath(relative).name
                    _require(name not in metadata, "ambiguous module metadata basename")
                    metadata[name] = {"path": output, "data": data}
                publish(output, data, receipt, member)
            _require(len(modules) == contract["expected_module_counts"][stage], "module count does not match contract")
            _require("modules.load" in metadata, "captured module load list is required")
            load = metadata["modules.load"]
            recovery = metadata.get("modules.load.recovery")
            block = metadata.get("modules.blocklist")
            sets[stage] = {"module_count": len(modules), "modules": modules,
                           "load_list": {"path": load["path"], "entries": _load_list(load["data"], modules)},
                           "recovery_load_list": ({"path": recovery["path"], "entries": _load_list(recovery["data"], modules)}
                                                  if recovery else None),
                           "blocklist": block["path"] if block else None}
        policy = contract["system_dlkm_blocklist"]
        _require(policy["module_set"] in SETS, "invalid system blocklist stage")
        policy_path = "modules/" + policy["module_set"] + "/" + _relative(policy["path"])
        _require(policy_path.casefold() in names, "captured system DLKM blocklist is absent")
        lines = _read(staging / policy_path, limit=1024**2).decode("ascii").splitlines()
        blocked = set()
        for line in lines:
            words = line.split("#", 1)[0].split()
            if words:
                _require(len(words) == 2 and words[0] == "blocklist"
                         and SAFE_COMPONENT.fullmatch(words[1]), "unsupported system blocklist syntax")
                blocked.add(words[1].replace("-", "_"))
        required = contract["required_system_blocklist_modules"]
        _require(isinstance(required, list) and {"zram", "zsmalloc"} <= set(required),
                 "Nezha system zram/zsmalloc selection must be explicit")
        _require(set(required) <= blocked, "required captured system module blocklist was not preserved")
        sets["system_dlkm"]["blocklist"] = policy_path
        publish("kernel-inputs.mk", _makefile(contract, sets, roles, purpose))
        for receipt in receipts.values():
            _require(_read(receipt["path"], receipt["reference"]["sha256"], limit=MAX_JSON_BYTES) == receipt["raw"],
                     "source receipt changed during packaging")
        _require(_read(contract_path, limit=MAX_JSON_BYTES) == contract_raw, "contract changed during packaging")
        result = {"schema_version": 1, "operation": "prepare-nezha-kernel-inputs",
                  "created_at_utc": datetime.now(timezone.utc).isoformat(), "purpose": purpose,
                  "contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
                  "tool": {"path": "scripts/kernel_inputs.py",
                           "sha256": hashlib.sha256(_read(Path(__file__))).hexdigest()},
                  "device": contract["device"], "provenance": contract["provenance"], "kernel": contract["kernel"],
                  "validation": {**contract["validation"], "payload_hashes_verified": True,
                                 "input_avb_reverified_by_packager": False, "publisher_authenticated_by_packager": False,
                                 "build_verified": False, "phone_accessed": False, "firmware_executed": False},
                  "source_receipts": contract["receipts"], "roles": roles, "module_sets": sets,
                  "files": records, "file_count": len(records), "total_bytes": total,
                  "generated_makefile": "kernel-inputs.mk",
                  "ramdisks_and_config_are_reference_only": True,
                  "reference_only_roles": sorted(ROLES - {"kernel", "dtb", "dtbo"}
                                                 | (OPTIONAL_ROLES & set(roles))),
                  "limitations": contract.get("limitations", [])}
        data = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        with (staging / "receipt.json").open("xb") as stream:
            os.chmod(staging / "receipt.json", 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        receipt_hash = hashlib.sha256(data).hexdigest()
        _read(staging / "receipt.json", receipt_hash, limit=MAX_JSON_BYTES)
        (staging / "receipt.sha256").write_text(receipt_hash + "  receipt.json\n")
        os.chmod(staging / "receipt.sha256", 0o600)
        _require(not os.path.lexists(output_dir), "output appeared during preparation")
        publish_new_directory(staging, output_dir)
        staging = None
        return result
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()


def package_inputs(contract_path, source_root, output_dir, *, purpose="research", workspace_root=WORKSPACE_ROOT):
    """Prepare a new bundle; report malformed inputs through one public error type."""
    try:
        return _package_inputs(contract_path, source_root, output_dir,
                               purpose=purpose, workspace_root=workspace_root)
    except KernelInputsError:
        raise
    except (IntakeError, OSError, KeyError, TypeError, UnicodeError, struct.error) as exc:
        raise KernelInputsError(str(exc)) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True, help="reviewed JSON contract, including receipt hashes")
    parser.add_argument("--source-root", type=Path, required=True, help="preserved analysis directory for this package")
    parser.add_argument("--output", type=Path, required=True, help="new directory below this workspace's artifacts/")
    parser.add_argument("--purpose", choices=("research", "build-candidate"), default="research")
    args = parser.parse_args(argv)
    try:
        result = package_inputs(args.contract, args.source_root, args.output, purpose=args.purpose)
    except (KernelInputsError, IntakeError, OSError, KeyError, TypeError, UnicodeError, struct.error) as exc:
        print(f"kernel inputs: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "purpose": result["purpose"],
                      "file_count": result["file_count"], "kernel_release": result["kernel"]["release"],
                      "input_avb_status": result["validation"]["input_avb_status"],
                      "origin_verified": result["provenance"]["origin_verified"],
                      "build_verified": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
