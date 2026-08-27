#!/usr/bin/env python3
"""Generate an offline Nezha framework-build candidate, never a flash admission.

Only authored source and generated configuration are published. Proprietary
bundles stay external and are bound by full file hashes. No build, network,
firmware executable or device command is run by this module.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile

try:
    from .artifact_files import publish_new_directory
except ImportError:
    from artifact_files import publish_new_directory


ROOT = Path(__file__).resolve().parents[1]
DEVICE_PATH = PurePosixPath("device/xiaomi/nezha")
TEMPLATE_FILES = (
    "AndroidProducts.mk", "Android.bp", "BoardConfig.mk", "device.mk",
    "lineage_nezha.mk", "README.md", "recovery/root/init.recovery.qcom.rc",
)
SECURITY_RECORD = PurePosixPath("patches/evolution/security-properties.json")
SECURITY_PATCH = PurePosixPath("patches/evolution/0001-allow-device-to-enforce-security-properties.patch")
RECORD_NAMES = ("device-baseline", "boot-contract", "firmware-layout", "vintf-contract")
BUILD_VARIANTS = ("user", "userdebug")
FRAMEWORK_PARTITIONS = (
    "system", "system_ext", "product", "vendor", "odm", "vendor_dlkm", "system_dlkm",
)
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_TEXT_BYTES = 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 ** 3
MAX_BUNDLE_FILES = 20000
CHUNK_SIZE = 1024 * 1024
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
MAKE_TOKEN = re.compile(r"[A-Za-z0-9_.:+/=-]+\Z")
BOOTCONFIG_KEYS = frozenset({
    "androidboot.hardware", "androidboot.memcg", "androidboot.usbcontroller",
    "androidboot.load_modules_parallel", "androidboot.hypervisor.protected_vm.supported",
    "androidboot.hypervisor.version", "androidboot.vendor.qspa", "androidboot.serialconsole",
})


class CandidateError(ValueError):
    """An input cannot safely describe this candidate profile."""


def _require(condition, message):
    if not condition:
        raise CandidateError(message)


def _build_variant(value):
    _require(isinstance(value, str) and value in BUILD_VARIANTS,
             "build variant must be exactly user or userdebug; eng is not admitted")
    return value


def _integer(value, label, maximum=MAX_FILE_BYTES):
    _require(type(value) is int and 0 < value <= maximum, f"invalid {label}")
    return value


def _digest(value, label):
    _require(isinstance(value, str) and SHA256.fullmatch(value), f"invalid {label} SHA256")
    return value


def _relative(value):
    _require(isinstance(value, str) and value, "missing relative file path")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and value == path.as_posix(), "noncanonical file path")
    _require(path.parts and all(part not in (".", "..") for part in path.parts), "unsafe file path")
    _require(re.fullmatch(r"[A-Za-z0-9_./+@-]+", value), "unsafe file name")
    return path


def _no_symlinks(path, *, existing=True):
    _require(".." not in Path(path).parts, "parent traversal refused")
    path = Path(os.path.abspath(os.fspath(path)))
    for parent in reversed([path, *path.parents]):
        try:
            mode = parent.lstat().st_mode
        except FileNotFoundError:
            if existing:
                raise CandidateError(f"input does not exist: {parent}") from None
            continue
        _require(not stat.S_ISLNK(mode), f"symlink refused: {parent}")
    return path


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read_file(path, *, limit=MAX_FILE_BYTES, collect=False):
    path = _no_symlinks(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode), f"not a regular file: {path}")
        _require(0 <= before.st_size <= limit, f"file exceeds size limit: {path}")
        digest, count, chunks = hashlib.sha256(), 0, []
        while block := os.read(descriptor, CHUNK_SIZE):
            count += len(block)
            _require(count <= limit, f"file grew beyond size limit: {path}")
            digest.update(block)
            if collect:
                chunks.append(block)
        after = os.fstat(descriptor)
        _require(count == before.st_size and _identity(before) == _identity(after),
                 f"input changed while reading: {path}")
        _require(_identity(after) == _identity(path.stat(follow_symlinks=False)),
                 f"input path changed while reading: {path}")
        return {"sha256": digest.hexdigest(), "size_bytes": count}, b"".join(chunks)
    finally:
        os.close(descriptor)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _read_json(path):
    identity, data = _read_file(path, limit=MAX_JSON_BYTES, collect=True)
    try:
        value = json.loads(data, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CandidateError(f"invalid JSON: {path}") from exc
    _require(isinstance(value, dict) and value.get("schema_version") == 1,
             f"unsupported record schema: {path}")
    return value, identity


def _codename(record):
    device = record.get("device")
    return device.get("codename") if isinstance(device, dict) else device


def _patch_date(value):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value),
             "invalid security patch date")
    date.fromisoformat(value)
    return value


def _file_entries(root, entries):
    _require(isinstance(entries, list) and len(entries) <= MAX_BUNDLE_FILES,
             "invalid bundle file inventory")
    result, seen = {}, set()
    for item in entries:
        _require(isinstance(item, dict), "invalid bundle entry")
        path = _relative(item.get("path"))
        _require(path.as_posix().casefold() not in seen, "duplicate or case-colliding bundle path")
        seen.add(path.as_posix().casefold())
        expected = _digest(item.get("sha256"), "bundle file")
        size = item.get("size_bytes")
        _require(type(size) is int and 0 <= size <= MAX_FILE_BYTES, "invalid bundle file size")
        actual, _ = _read_file(root / path)
        _require(actual == {"sha256": expected, "size_bytes": size},
                 f"bundle file hash/size mismatch: {path}")
        result[path.as_posix()] = actual
    return result


def derive_plan(records, identities, *, variant="userdebug"):
    """Pure derivation from sanitized records; physical fit is never inferred."""
    variant = _build_variant(variant)
    _require(set(records) == set(RECORD_NAMES), "all four source records are required")
    for name, record in records.items():
        _require(_codename(record) == "nezha", f"not a Nezha record: {name}")
    baseline, boot, layout, vintf = (records[name] for name in RECORD_NAMES)
    identity = baseline["device"]
    _require(identity.get("reported_hwc") == "CN", "China device baseline required")
    _require(identity.get("soc") == "SM8850" and identity.get("board_platform") == "canoe",
             "unsupported SoC or board baseline")
    _require(identity.get("abi") == "arm64-v8a", "unsupported device ABI")
    _require(baseline["firmware"].get("sdk") == 36, "this product targets Android API 36")
    kernel = boot["kernel"]
    _require(kernel.get("architecture") == "arm64", "unsupported kernel architecture")
    _require(kernel.get("runtime_page_size_bytes") == 4096, "only captured 4 KiB kernels supported")
    for option in ("CONFIG_ARM64_4K_PAGES", "CONFIG_MODULES", "CONFIG_MODVERSIONS",
                   "CONFIG_DM_VERITY", "CONFIG_SECURITY_SELINUX"):
        _require(kernel["selected_config"].get(option) == "y", f"required kernel setting absent: {option}")
    _require(MAKE_TOKEN.fullmatch(kernel["release"]), "unsafe kernel release")
    boot_package = _digest(boot["provenance"]["package_sha256"], "boot package")
    vendor_package = _digest(layout["package"]["sha256"], "layout package")
    images = {item["path"]: item for item in boot["image_files"]}
    budgets = {}
    for name in ("boot", "init_boot", "vendor_boot", "recovery", "dtbo"):
        item = images[name + ".img"]
        size = _integer(item["size_bytes"], name + " image length", 2 * 1024 ** 3)
        _require(size % 4096 == 0, "unaligned package image budget")
        budgets[name] = {"bytes": size, "basis": "package image length; physical capacity unverified"}
        if name != "dtbo":
            _require(item["boot_header"]["version"] == 4, f"unsupported {name} header")
    metadata = layout["logical_metadata"]
    _require(len(metadata["physical_devices"]) == 1, "one super device is required")
    super_device = metadata["physical_devices"][0]
    _require(super_device["partition_name"] == "super", "unexpected super device name")
    super_size = _integer(super_device["size_bytes"], "super declaration")
    populated = [part for part in layout["partitions"] if part["size_bytes"] > 0]
    _require(all(part["name"].endswith("_a") for part in populated), "only A-populated baseline supported")
    partitions = {part["name"][:-2]: part for part in populated}
    _require(len(partitions) == len(populated), "duplicate populated partition")
    _require(set(FRAMEWORK_PARTITIONS) <= set(partitions), "required logical partitions missing")
    groups = {part["group_index"] for part in populated}
    _require(len(groups) == 1, "one populated dynamic-partition group is required")
    group = next(item for item in metadata["groups"] if item["index"] in groups)
    _require(group["name"].endswith("_a"), "expected slot-suffixed group name")
    group_name = group["name"][:-2]
    _require(re.fullmatch(r"[a-z][a-z0-9_]*", group_name), "unsafe group name")
    group_size = _integer(group["maximum_size"], "group declaration")
    _require(group_size < super_size, "group must leave metadata room in super")
    _require(sum(part["size_bytes"] for part in populated) <= group_size, "group overcommitted")
    filesystems = {}
    for name, part in partitions.items():
        _require(re.fullmatch(r"[a-z][a-z0-9_]*", name), "unsafe logical partition name")
        filesystem = part["filesystem"]["format"].lower()
        _require(filesystem in ("erofs", "ext4"), "unsupported logical filesystem")
        filesystems[name] = filesystem
        _digest(part["extraction"]["sha256"], "logical image")
    owners = {}
    for descriptor in boot["avb"]["logical_partition_checks"]:
        name, owner = descriptor["partition"], descriptor["descriptor_source"]
        _require(owner in ("vbmeta", "vbmeta_system"), "unsupported logical AVB owner")
        _require(name not in owners or owners[name] == owner, "conflicting AVB descriptor owners")
        owners[name] = owner
    _require(set(partitions) <= set(owners), "logical AVB ownership missing")
    chains = {}
    for item in boot["avb"]["chain_key_checks"]:
        name = item["partition"]
        if name in ("boot", "recovery", "vbmeta_system"):
            location = _integer(item["rollback_index_location"], "rollback location", 31)
            _require(name not in chains, "duplicate AVB chain")
            rollback = images[name + ".img"]["avb"]["rollback_index"]
            _require(type(rollback) is int and 0 <= rollback < 2 ** 64, "invalid rollback value")
            chains[name] = {"location": location, "rollback_index": rollback}
    _require(set(chains) == {"boot", "recovery", "vbmeta_system"}, "required AVB chains missing")
    _require(len({item["location"] for item in chains.values()}) == len(chains), "AVB locations collide")
    root_rollback = images["vbmeta.img"]["avb"]["rollback_index"]
    _require(type(root_rollback) is int and 0 <= root_rollback < 2 ** 64,
             "invalid top-level rollback index")
    props = vintf["properties_by_source"]
    first_api = int(props["/odm/etc/build.prop"]["ro.product.first_api_level"])
    board_api = int(props["/vendor/build.prop"]["ro.board.first_api_level"])
    _require(first_api == 36 and 202404 <= board_api <= 209912, "unsupported shipping API facts")
    bootconfig = {}
    for key, value in boot["vendor_ramdisk"]["bootconfig"].items():
        if key in BOOTCONFIG_KEYS:
            _require(isinstance(value, str) and MAKE_TOKEN.fullmatch(value), "unsafe bootconfig value")
            bootconfig[key] = value
    return {
        "schema_version": 1,
        "profile": "framework-checks",
        "device": {"codename": "nezha", "hardware_region": "CN", "soc": "SM8850"},
        "product": "lineage_nezha", "release_config": "bp4a", "variant": variant,
        "input_records": identities,
        "source_packages": {"kernel": boot_package, "vendor": vendor_package},
        "mixed_package_sources": boot_package != vendor_package,
        "kernel": {"release": kernel["release"], "sha256": kernel["sha256"], "page_size_bytes": 4096},
        "image_budgets": budgets,
        "super": {"bytes": super_size, "group_name": group_name, "group_bytes": group_size,
                  "basis": "LP metadata declarations; physical capacity unverified"},
        "packaged_logical_partitions": list(FRAMEWORK_PARTITIONS),
        "required_unpacked_partitions": sorted(set(partitions) - set(FRAMEWORK_PARTITIONS)),
        "logical_filesystems": filesystems, "avb_descriptor_owners": owners,
        "avb_chains": chains, "avb_root_rollback_index": root_rollback, "bootconfig": bootconfig,
        "shipping_api_level": first_api, "board_shipping_api_level": board_api,
        "vendor_security_patch": _patch_date(props["/vendor/build.prop"]["ro.vendor.build.security_patch"]),
        "avb_policy": {"enabled": True, "key_class": "public AOSP engineering test key",
                       "oem_authentication": False, "disabled_flags": [],
                       "source_image_set_verified": boot["avb"]["full_image_set_verification_passed"]},
        "admission": {"configuration_allowed": True, "complete_target_files_allowed": False,
                      "flash_allowed": False, "physical_partition_fit_verified": False,
                      "bootloader_state_verified": False, "kernel_abi_verified": False,
                      "native_features_tested": False},
        "required_source_adjustments": [{
            "path": "vendor/lineage/config/common.mk",
            "reference_commit": "11d2966a3294a0a692fc958127c770cfe9c00a3c",
            "change": "Make inherited downgrade and privapp defaults optional, without allowing duplicate properties",
            "assignments": {"ro.ota.allow_downgrade=true": "ro.ota.allow_downgrade?=true",
                            "ro.control_privapp_permissions=log": "ro.control_privapp_permissions?=log"},
            "applied_by_generator": False,
        }],
        "limitations": [
            "Framework-checks profile is not complete target-files or a flashable ROM.",
            "Required unpackaged logical mounts are retained and block complete packaging.",
            "Raw vendor/ODM images may require normal new AVB signing or repacking; copy rules do not sign them.",
            "Preserved vendor init/fstab contents are not patched by copying files into vendor staging.",
            "No image length, LP declaration, successful compile or engineering signature establishes physical fit or OEM trust.",
            "VINTF, SELinux, kernel/provider CRC and signature compatibility remain build/device checks.",
        ],
    }


def _bind_bundles(plan, records, kernel_path, vendor_path):
    kernel, kernel_identity = _read_json(kernel_path)
    vendor, vendor_identity = _read_json(vendor_path)
    _require(_codename(kernel) == "nezha" and _codename(vendor) == "nezha", "wrong bundle device")
    _require(kernel["provenance"]["parent_package_sha256"] == plan["source_packages"]["kernel"],
             "kernel bundle package mismatch")
    _require(vendor["source"]["package_sha256"] == plan["source_packages"]["vendor"],
             "vendor bundle package mismatch")
    _require(vendor["source"]["source_record_sha256"] == plan["input_records"]["firmware-layout"]["sha256"],
             "vendor bundle was generated from a different layout record")
    _require(kernel["kernel"]["release"] == plan["kernel"]["release"], "kernel release mismatch")
    page_size = kernel["kernel"].get("page_size", kernel["kernel"].get("page_size_bytes"))
    _require(page_size == plan["kernel"]["page_size_bytes"], "kernel page-size mismatch")
    _require(all(item.get("readback_verified") is True for item in kernel["files"]),
             "unverified kernel output")
    kernel_files = _file_entries(Path(kernel_path).parent, kernel["files"])
    _require(kernel_files.get("kernel/Image", {}).get("sha256") == plan["kernel"]["sha256"],
             "kernel Image does not match the boot contract")
    for name, module_set in records["boot-contract"]["dlkm_followup"]["sets"].items():
        bundled = kernel["module_sets"][name]
        _require(bundled["module_count"] == module_set["file_count"],
                 f"kernel module count mismatch: {name}")
        _require(len(bundled["modules"]) == bundled["module_count"] and
                 len(set(bundled["modules"])) == bundled["module_count"] and
                 all(path in kernel_files for path in bundled["modules"]),
                 f"kernel module inventory is not covered by verified files: {name}")
    entries = [*vendor["images"].values(), *vendor.get("extras", []), *vendor["generated_files"]]
    _require(all(item.get("readback_verified") is True for item in entries), "unverified vendor output")
    vendor_files = _file_entries(Path(vendor_path).parent, entries)
    partitions = {part["name"]: part for part in records["firmware-layout"]["partitions"]}
    for name in ("vendor", "odm"):
        image = vendor["images"][name]
        source = partitions[name + "_a"]
        _require(image["source_partition"] == name + "_a", "wrong source partition")
        _require(image["sha256"] == source["extraction"]["sha256"] and
                 image["size_bytes"] == source["size_bytes"], "vendor image is not the selected source image")
    plan["bundles"] = {
        "kernel": {**kernel_identity, "files_verified": len(kernel_files),
                   "source_path": "vendor/xiaomi/nezha-kernel",
                   "input_avb_status": kernel["validation"]["input_avb_status"],
                   "origin_verified": kernel["provenance"]["origin_verified"]},
        "vendor": {**vendor_identity, "files_verified": len(vendor_files),
                   "source_path": "vendor/xiaomi/nezha",
                   "input_avb_status": vendor["source"]["input_avb_status"]},
    }
    _require(plan["bundles"]["kernel"]["input_avb_status"] in ("failed", "unverified", "verified-external"),
             "unknown kernel AVB status")
    _require(type(plan["bundles"]["kernel"]["origin_verified"]) is bool,
             "invalid kernel origin status")
    plan["kernel"]["boot_security_patch"] = _patch_date(kernel["kernel"]["boot_security_patch"])
    return kernel


def _bind_vendor_header(plan, boot, workspace_root):
    """Read the already verified unpacker report; never run the firmware/tool."""
    evidence = boot["evidence"]
    directory = Path(workspace_root) / _relative(evidence["private_directory"])
    receipt, identity = _read_json(directory / "final-receipt.json")
    _require(identity["sha256"] == evidence["final_receipt_sha256"], "boot evidence receipt mismatch")
    _require(receipt["parent_package_sha256"] == plan["source_packages"]["kernel"],
             "boot evidence package mismatch")
    name = "logs/unpack-vendor_boot.stdout.txt"
    entries = [item for item in receipt["artifacts"] if item.get("path") == name]
    _require(len(entries) == 1 and entries[0]["kind"] == "regular", "vendor_boot report missing")
    info, data = _read_file(directory / name, limit=MAX_TEXT_BYTES, collect=True)
    _require(info == {key: entries[0][key] for key in ("sha256", "size_bytes")},
             "vendor_boot report hash mismatch")
    text = data.decode("utf-8")
    def number(label):
        values = re.findall(r"^" + re.escape(label) + r": (0x[0-9a-fA-F]+|[0-9]+)$", text, re.M)
        _require(len(values) == 1, f"missing/ambiguous vendor_boot field: {label}")
        return int(values[0], 0)
    _require(number("vendor boot image header version") == 4 and number("page size") == 4096,
             "vendor_boot report format mismatch")
    addresses = {name: number(label) for name, label in (
        ("kernel", "kernel load address"), ("ramdisk", "ramdisk load address"),
        ("tags", "kernel tags load address"), ("dtb", "dtb address"))}
    _require(all(0 <= value < 2 ** (64 if name == "dtb" else 32)
                 for name, value in addresses.items()), "invalid vendor_boot load address")
    cmdline = re.findall(r"^vendor command line args: (.*)$", text, re.M)
    _require(len(cmdline) == 1, "missing/ambiguous vendor command line")
    selected = [token for token in cmdline[0].split()
                if token == "bootconfig" or token.startswith(("video=", "erofs.reserved_pages="))]
    _require(all(re.fullmatch(r"[A-Za-z0-9_.:,=+-]+", token) for token in selected),
             "unsafe selected kernel command line")
    plan["vendor_boot_header"] = {
        "receipt": identity, "report": {"path": name, **info}, "load_addresses": addresses,
        "mkbootimg_base": 0, "selected_cmdline": selected,
        "stock_fingerprint_cmdline_adopted": False,
        "basis": "hash-bound unpacker report; zero base encodes the observed absolute addresses",
    }


def _bind_security_patch(plan, source_root, payloads):
    metadata, identity = _read_json(Path(source_root) / SECURITY_RECORD)
    _require(metadata["project"] == "vendor/lineage" and
             metadata["base_commit"] == "11d2966a3294a0a692fc958127c770cfe9c00a3c" and
             metadata["patch"] == SECURITY_PATCH.as_posix(), "unexpected security-property patch target")
    info, patch = _read_file(Path(source_root) / SECURITY_PATCH, limit=MAX_TEXT_BYTES, collect=True)
    _require(info["sha256"] == _digest(metadata["patch_sha256"], "security patch"),
             "security-property patch hash mismatch")
    _require(len(metadata["files"]) == 1 and metadata["files"][0]["path"] == "config/common.mk",
             "unexpected security-property patch file set")
    for key in ("before_sha256", "after_sha256"):
        _digest(metadata["files"][0][key], "source " + key)
    _, raw = _read_file(Path(source_root) / SECURITY_RECORD, limit=MAX_JSON_BYTES, collect=True)
    payloads[SECURITY_RECORD.as_posix()] = raw
    payloads[SECURITY_PATCH.as_posix()] = patch
    plan["required_source_adjustments"] = [{**metadata, "metadata_identity": identity,
                                            "applied_by_generator": False}]


def render_fstab(plan, boot, source):
    identity, raw = _read_file(source, limit=MAX_TEXT_BYTES, collect=True)
    _require(identity["sha256"] == boot["first_stage_fstab"]["sha256"], "fstab source hash mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise CandidateError("fstab is not UTF-8") from exc
    logical = {}
    for entry in boot["first_stage_fstab"]["logical_mounts"]:
        name = entry["source"]
        if name in plan["logical_filesystems"] and entry["filesystem"] == plan["logical_filesystems"][name]:
            logical[name] = entry
    _require(set(logical) == set(plan["logical_filesystems"]), "recorded logical mounts incomplete")
    lines = ["# Generated Nezha candidate fstab; no flash authorization.",
             "# Logical AVB flags are authored; physical mount/crypto fields retain verified input."]
    for name, entry in logical.items():
        mount = entry["mount_point"]
        _require(re.fullmatch(r"/[A-Za-z0-9_/-]+", mount), "unsafe mount point")
        owner = plan["avb_descriptor_owners"][name]
        lines.append(f"{name} {mount} {plan['logical_filesystems'][name]} ro "
                     f"wait,slotselect,avb={owner},logical,first_stage_mount")
    physical = []
    for line in text.splitlines():
        content = line.split("#", 1)[0].strip()
        if not content:
            continue
        fields = content.split()
        _require(len(fields) == 5, "malformed source fstab row")
        if fields[0] in logical:
            continue
        if not fields[0].startswith("/dev/block/"):
            continue  # Stock framework overlay/bind mounts are not adopted.
        _require(all(re.fullmatch(r"[A-Za-z0-9_./,:=+@%-]+", value) for value in fields),
                 "unsafe physical fstab field")
        _require(fields[2] in ("ext4", "f2fs", "vfat", "emmc", "erofs"), "unsupported physical filesystem")
        physical.append(fields)
        lines.append(" ".join(fields))
    _require({"/metadata", "/data"} <= {row[1] for row in physical}, "source lacks metadata/data mounts")
    data_rows = [row for row in physical if row[1] == "/data"]
    _require(all("fileencryption=" in row[4] and "metadata_encryption=" in row[4] for row in data_rows),
             "encrypted userdata contract is required")
    plan["fstab"] = {**identity, "logical_mounts": list(logical),
                     "physical_mounts": [row[1] for row in physical],
                     "stock_overlay_mounts_adopted": False,
                     "logical_avb_enabled": True, "vendor_image_replacement_applied": False}
    return "\n".join(lines) + "\n"


def _bound_reference(reference, workspace_root):
    """Bind a prior inspection without executing its tools or trusting a path alone."""
    path = Path(workspace_root) / _relative(reference["path"])
    record, identity = _read_json(path)
    _require(identity == {key: reference[key] for key in ("sha256", "size_bytes")},
             "factory inspection reference hash/size mismatch")
    return record


def _factory_profile(plan, kernel, factory_boot_path, partition_path, workspace_root):
    """Admit package geometry and a factory fstab, retaining mixed-source provenance."""
    factory, factory_identity = _read_json(factory_boot_path)
    partitions, partition_identity = _read_json(partition_path)
    _require(_codename(factory) == _codename(partitions) == "nezha", "wrong factory device")
    _require(factory["device"]["hardware_region"] == partitions["device"]["hardware_region"] == "CN",
             "factory profile requires China hardware records")
    package = factory["packages"]["factory"]
    package_sha = _digest(package["sha256"], "factory package")
    _require(package_sha == partitions["package"]["sha256"] == plan["source_packages"]["vendor"],
             "factory profile and vendor package disagree")
    _require(factory["packages"]["xiaomi_eu"]["sha256"] == plan["source_packages"]["kernel"],
             "factory comparison does not cover this kernel bundle")
    _require(package["source_kind"] == "user-provided" and package["source_url"] is None
             and package["origin_verified"] is False, "factory origin must not be promoted")
    _require(all(partitions["package"][key] == package[key]
                 for key in ("source_kind", "source_url", "origin_verified")),
             "factory package provenance differs")
    image_readback = _bound_reference(factory["image_readback"]["receipt"], workspace_root)
    _require(image_readback["package_sha256"] == package_sha and image_readback["all_images_match"] is True
             and all(image_readback[key] == package[key]
                     for key in ("source_kind", "source_url", "origin_verified")),
             "factory image readback package/provenance differs")
    images = {item["path"]: item for item in image_readback["images"]}
    _require(len(images) == len(image_readback["images"]) == image_readback["image_count"],
             "factory image readback contains duplicate or missing entries")
    for item in images.values():
        expected = {"sha256": _digest(item["expected_sha256"], "factory image"),
                    "size_bytes": _integer(item["expected_size_bytes"], "factory image length")}
        _require(item["both_match_verified_archive"] is True, "factory image copies do not match")
        for copy_name in ("archive_image", "user_extracted_image"):
            copy = item[copy_name]
            _require(all(copy[key] == value for key, value in expected.items()) and
                     all(copy[key] is True for key in
                         ("regular_nonsymlink", "identity_stable", "matches_expected_sha256")),
                     "factory image copy hash/size/identity mismatch")

    header = factory["header_component_readback"]
    header_receipt = _bound_reference(header["receipt"], workspace_root)
    _require(header_receipt["factory_package_sha256"] == package_sha
             and header_receipt["xiaomi_eu_package_sha256"] == plan["source_packages"]["kernel"]
             and header_receipt["components"] == header["components"],
             "factory component comparison differs from its receipt")
    components = {item["path"]: item for item in header["components"]}
    _require(len(components) == len(header["components"]), "duplicate factory component")
    bundle_files = {item["path"]: item for item in kernel["files"]}
    for role, component_path in (("kernel", "unpacked/boot/kernel"),
                                 ("dtb", "unpacked/vendor_boot/dtb"),
                                 ("bootconfig", "unpacked/vendor_boot/bootconfig")):
        item = components[component_path]
        bundled = bundle_files[kernel["roles"][role]]
        _require(item["bytes_match_eu"] is True and
                 item["factory_sha256"] == item["xiaomi_eu_sha256"] == bundled["sha256"] and
                 item["size_bytes"] == bundled["size_bytes"],
                 f"factory {role} does not match the verified kernel bundle")
    _require(factory["vendor_bootconfig"]["declarations"] == plan["bootconfig"],
             "factory bootconfig declarations differ")
    ramdisk = _bound_reference(factory["ramdisk_comparison"]["receipt"], workspace_root)
    _require(ramdisk["factory_package_sha256"] == package_sha and
             ramdisk["inputs_identity_and_hash_rechecked"] is True,
             "factory ramdisk inspection does not cover this package")
    fstab = factory["normal_vendor_fstab"]
    fstab_members = [item for item in ramdisk["artifacts"]
                     if item["path"] == "text-members/vendor_boot-0001.txt"]
    _require(len(fstab_members) == 1 and fstab_members[0]["sha256"] == fstab["factory_sha256"]
             and fstab_members[0]["size_bytes"] == fstab["factory_size_bytes"],
             "factory fstab is not bound by the ramdisk inspection")

    inspection = partitions["inspection"]
    receipt = _bound_reference(inspection["receipt"], workspace_root)
    analysis = _bound_reference(inspection["analysis"], workspace_root)
    _require(receipt["parent_package_sha256"] == package_sha and
             receipt["input_hashes_and_identity_rechecked"] is True and
             receipt["output"]["readback_verified"] is True and
             all(receipt["output"][key] == inspection["analysis"][key]
                 for key in ("sha256", "size_bytes")), "GPT analysis receipt does not bind its output")
    _require(analysis["sector_size_bytes"] == 4096 and
             analysis["physical_phone_geometry_verified"] is False and
             analysis["flashable_gpt_admitted"] is False, "package GPT is not a live or flash admission")
    sizes = {item["name"]: item for item in partitions["build_relevant_sizes"]}
    _require(len(sizes) == len(partitions["build_relevant_sizes"]), "duplicate factory budget")
    luns = {item["lun"]: item for item in analysis["luns"]}
    _require(len(luns) == len(analysis["luns"]), "duplicate factory LUN")
    for name in (*plan["image_budgets"], "super"):
        item = sizes[name]
        image = images[name + ".img"]
        _require(item["stored_image_bytes"] == image["expected_size_bytes"] and
                 item["stored_image_sha256"] == image["expected_sha256"],
                 "factory stored-image summary differs from its image readback")
        labels = [name] if name == "super" else [name + "_a", name + "_b"]
        _require(item["labels"] == labels, "factory partition labels differ")
        extent = _integer(item["package_extent_bytes"], "factory partition extent")
        _require(extent % 4096 == 0, "unaligned factory extent")
        lun = luns[item["lun"]]
        _require(lun["primary_backup_entry_arrays_identical"] is True and
                 lun["sector_size_bytes"] == 4096, "unverified GPT main/backup pair")
        for side in ("main", "backup"):
            headers = lun["gpt"][side]["headers"]
            _require(len(headers) == 1, "ambiguous factory GPT header")
            gpt = headers[0]
            _require(gpt["header_crc32_verified"] is True and gpt["entry_array_crc32_verified"] is True,
                     "unverified GPT checksums")
            for label in labels:
                matches = [entry for entry in gpt["entries"] if entry["label"] == label]
                _require(len(matches) == 1, "missing or duplicate factory partition")
                entry = matches[0]
                _require(entry["type_guid_zero"] is False and entry["size_bytes"] == extent
                         and type(entry["first_lba"]) is int and entry["first_lba"] >= 0
                         and type(entry["last_lba"]) is int and entry["last_lba"] >= entry["first_lba"]
                         and (entry["last_lba"] - entry["first_lba"] + 1) * 4096 == extent,
                         "factory extent differs from its finite GPT entry")
        if name == "super":
            _require(extent == plan["super"]["bytes"], "factory GPT and LP super sizes disagree")
        else:
            _require(_integer(item["stored_image_bytes"], "factory image length") <= extent,
                     "factory image exceeds its package extent")
            plan["image_budgets"][name] = {
                "bytes": extent, "basis": "verified factory package GPT extent; live capacity unverified",
                "stored_image_bytes": item["stored_image_bytes"],
            }
    dtbo = bundle_files[kernel["roles"]["dtbo"]]
    _require(dtbo["sha256"] == sizes["dtbo"]["stored_image_sha256"] and
             dtbo["size_bytes"] == sizes["dtbo"]["stored_image_bytes"], "factory DTBO payload differs")
    plan["factory_profile"] = {
        "package_sha256": package_sha, "origin_verified": False,
        "factory_boot_record": factory_identity, "partition_record": partition_identity,
        "image_readback_receipt": factory["image_readback"]["receipt"],
        "header_receipt": header["receipt"], "gpt_receipt": inspection["receipt"],
        "ramdisk_receipt": factory["ramdisk_comparison"]["receipt"],
        "gpt_analysis": inspection["analysis"], "kernel_dtb_dtbo_bootconfig_bytes_match": True,
        "kernel_bundle_provenance_relabelled": False, "physical_phone_geometry_verified": False,
    }
    return fstab


def render_factory_fstab(plan, contract, source):
    """Select observed filesystems without removing factory AVB or crypto flags."""
    identity, raw = _read_file(source, limit=MAX_TEXT_BYTES, collect=True)
    _require(identity == {"sha256": contract["factory_sha256"],
                          "size_bytes": contract["factory_size_bytes"]}, "factory fstab hash/size mismatch")
    text = raw.decode("utf-8")
    rows, comments = [], []
    for line in text.splitlines():
        content = line.split("#", 1)[0].strip()
        if not content:
            if not rows:
                comments.append(line)
            continue
        fields = content.split()
        _require(len(fields) == 5 and
                 re.fullmatch(r"[A-Za-z0-9_./,:=+@%*-]+", fields[0]) and
                 all(re.fullmatch(r"[A-Za-z0-9_./,:=+@%-]+", f) for f in fields[1:]),
                 "malformed or unsafe factory fstab row")
        _require("*" not in fields[0] or fields[0].startswith("/devices/"),
                 "factory device-node glob is not a /devices path")
        rows.append(fields)
    _require(len(rows) == contract["rows_in_each"], "factory fstab row count differs")
    selected, logical, physical, verified_boot = [], [], [], []
    for fields in rows:
        name, mount, filesystem, _, flags_text = fields
        flags = flags_text.split(",")
        if name in plan["logical_filesystems"]:
            if filesystem != plan["logical_filesystems"][name]:
                continue
            _require(name not in logical, "duplicate factory logical mount")
            _require([f for f in flags if f == "avb" or f.startswith("avb=")] ==
                     ["avb=" + plan["avb_descriptor_owners"][name]] and
                     {"wait", "slotselect", "logical", "first_stage_mount"} <= set(flags),
                     "factory logical mount lacks the required verified-boot flags")
            logical.append(name)
        elif name.startswith(("/dev/block/", "/devices/")):
            _require(filesystem in ("ext4", "f2fs", "vfat", "emmc", "erofs"),
                     "unsupported factory physical filesystem")
            if name.startswith("/devices/"):
                _require(mount.startswith("/storage/") and filesystem == "vfat" and
                         any(flag.startswith("voldmanaged=") for flag in flags),
                         "factory device-node pattern requires a vold-managed storage row")
            physical.append(fields)
            if mount[1:] in plan["image_budgets"]:
                _require(name == "/dev/block/by-name/" + mount[1:] and filesystem == "emmc"
                         and [f for f in flags if f == "avb" or f.startswith("avb=")] == ["avb=vbmeta"]
                         and {"slotselect", "first_stage_mount"} <= set(flags),
                         "factory boot row lacks its verified-boot contract")
                verified_boot.append(mount[1:])
        else:
            continue  # Framework overlay/bind mounts require a separate integration.
        selected.append(" ".join(fields))
    _require(set(logical) == set(plan["logical_filesystems"]), "factory logical mounts incomplete")
    _require(sorted(verified_boot) == sorted(plan["image_budgets"]), "factory boot mounts incomplete")
    for expected in contract["normal_data_rows"]:
        matches = [row for row in physical if row[1] == expected["mount_point"]]
        fields = [expected["source"], expected["mount_point"], expected["filesystem"],
                  ",".join(expected["mount_options"]), ",".join(expected["fs_mgr_flags"])]
        _require(matches == [fields], "factory data/metadata mount or encryption flags changed")
    _require({"/data", "/metadata"} == {row["mount_point"] for row in contract["normal_data_rows"]},
             "factory encrypted data/metadata contract missing")
    data = next(row for row in physical if row[1] == "/data")
    _require(all(token in data[4] for token in ("fileencryption=", "metadata_encryption=", "keydirectory=")),
             "factory userdata lacks encryption requirements")
    plan["fstab"] = {
        **identity, "logical_mounts": logical, "physical_mounts": [row[1] for row in physical],
        "source": "factory vendor ramdisk", "stock_overlay_mounts_adopted": False,
        "logical_avb_enabled": True, "factory_logical_flags_preserved": True,
        "factory_boot_verification_rows": verified_boot, "vendor_image_replacement_applied": False,
        "device_node_globs_preserved": sum("*" in row[0] for row in physical),
        "device_node_globs_expanded": False,
    }
    return "\n".join([*comments, "# Selected factory rows for Nezha framework checks; no flash admission.",
                      "# Original flags retained; other filesystem alternatives and overlays not selected.",
                      *selected, ""])


def _render_board(plan):
    budget_note = ("# Factory GPT extents and LP declarations are not live partition measurements."
                   if "factory_profile" in plan else
                   "# Image lengths and LP sizes are candidate budgets, not physical measurements.")
    lines = ["# Generated from receipt-bound Nezha facts. Framework-checks only.",
             budget_note,
             "BOARD_BOOT_HEADER_VERSION := 4", "BOARD_INIT_BOOT_HEADER_VERSION := 4",
             "BOARD_MKBOOTIMG_ARGS += --header_version 4",
             "BOARD_MKBOOTIMG_INIT_ARGS += --header_version 4", "BOARD_KERNEL_PAGESIZE := 4096"]
    header = plan["vendor_boot_header"]
    lines.append("BOARD_KERNEL_BASE := 0x00000000")
    for name, value in header["load_addresses"].items():
        lines.append(f"BOARD_MKBOOTIMG_ARGS += --{name}_offset 0x{value:x}")
    lines.append("BOARD_KERNEL_CMDLINE += " + " ".join(header["selected_cmdline"]))
    lines += [f"BOOT_SECURITY_PATCH := {plan['kernel']['boot_security_patch']}",
              f"NEZHA_EXPECTED_KERNEL_PACKAGE_SHA256 := {plan['source_packages']['kernel']}",
              f"NEZHA_EXPECTED_KERNEL_RELEASE := {plan['kernel']['release']}",
              f"NEZHA_EXPECTED_KERNEL_AVB_STATUS := {plan['bundles']['kernel']['input_avb_status']}",
              "NEZHA_EXPECTED_KERNEL_ORIGIN_VERIFIED := " +
              str(plan['bundles']['kernel']['origin_verified']).lower()]
    variable = {"boot": "BOOTIMAGE", "init_boot": "INIT_BOOT_IMAGE", "vendor_boot": "VENDOR_BOOTIMAGE",
                "recovery": "RECOVERYIMAGE", "dtbo": "DTBOIMG"}
    for name, budget in plan["image_budgets"].items():
        lines.append(f"BOARD_{variable[name]}_PARTITION_SIZE := {budget['bytes']}")
    group = plan["super"]["group_name"]
    lines += [f"BOARD_SUPER_PARTITION_SIZE := {plan['super']['bytes']}",
              f"BOARD_SUPER_PARTITION_GROUPS := {group}",
              f"BOARD_{group.upper()}_SIZE := {plan['super']['group_bytes']}",
              f"BOARD_{group.upper()}_PARTITION_LIST := {' '.join(FRAMEWORK_PARTITIONS)}"]
    for name in FRAMEWORK_PARTITIONS:
        lines += [f"TARGET_COPY_OUT_{name.upper()} := {name}",
                  f"BOARD_{name.upper()}IMAGE_FILE_SYSTEM_TYPE := {plan['logical_filesystems'][name]}"]
    lines += [f"BOARD_SHIPPING_API_LEVEL := {plan['board_shipping_api_level']}",
              "BOARD_SYSTEMSDK_VERSIONS := 36",
              f"VENDOR_SECURITY_PATCH := {plan['vendor_security_patch']}",
              "BOARD_AVB_ENABLE := true",
              "NEZHA_ENGINEERING_AVB_KEY := external/avb/test/data/testkey_rsa4096.pem",
              "BOARD_AVB_KEY_PATH := $(NEZHA_ENGINEERING_AVB_KEY)",
              "BOARD_AVB_ALGORITHM := SHA256_RSA4096",
              f"BOARD_AVB_ROLLBACK_INDEX := {plan['avb_root_rollback_index']}"]
    for name, chain in plan["avb_chains"].items():
        upper = name.upper()
        lines += [f"BOARD_AVB_{upper}_KEY_PATH := $(NEZHA_ENGINEERING_AVB_KEY)",
                  f"BOARD_AVB_{upper}_ALGORITHM := SHA256_RSA4096",
                  f"BOARD_AVB_{upper}_ROLLBACK_INDEX := {chain['rollback_index']}",
                  f"BOARD_AVB_{upper}_ROLLBACK_INDEX_LOCATION := {chain['location']}"]
    chained = [name for name in FRAMEWORK_PARTITIONS if plan["avb_descriptor_owners"][name] == "vbmeta_system"]
    lines.append("BOARD_AVB_VBMETA_SYSTEM := " + " ".join(chained))
    for key, value in sorted(plan["bootconfig"].items()):
        lines.append(f"BOARD_BOOTCONFIG += {key}={value}")
    return "\n".join(lines) + "\n"


def _render_product(plan):
    partitions = ["boot", "dtbo", "init_boot", "recovery", "vendor_boot", "vbmeta", "vbmeta_system",
                  *FRAMEWORK_PARTITIONS]
    return "\n".join([
        "# Generated framework-checks configuration. Complete packaging is not admitted.",
        f"PRODUCT_SHIPPING_API_LEVEL := {plan['shipping_api_level']}",
        "PRODUCT_USE_DYNAMIC_PARTITIONS := true", "PRODUCT_USE_DYNAMIC_PARTITION_SIZE := true",
        "PRODUCT_BUILD_SUPER_PARTITION := true", "AB_OTA_UPDATER := true",
        "AB_OTA_PARTITIONS += " + " ".join(partitions),
        "PRODUCT_BUILD_BOOT_IMAGE := true", "PRODUCT_BUILD_INIT_BOOT_IMAGE := true",
        "PRODUCT_BUILD_VENDOR_BOOT_IMAGE := true", "PRODUCT_BUILD_RECOVERY_IMAGE := true",
        "PRODUCT_ENFORCE_VINTF_MANIFEST := true", "",
    ])


def _load_records(record_paths):
    records, identities = {}, {}
    for name in RECORD_NAMES:
        records[name], identities[name] = _read_json(record_paths[name])
    return records, identities


def generate(output, *, record_paths, kernel_receipt, vendor_receipt, fstab_source=None,
             variant="userdebug", workspace_root=ROOT, template_root=ROOT / DEVICE_PATH,
             patch_source_root=ROOT, factory_boot_contract=None, partition_metadata=None):
    variant = _build_variant(variant)
    factory_selected = factory_boot_contract is not None or partition_metadata is not None
    if factory_selected:
        _require(factory_boot_contract is not None and partition_metadata is not None and fstab_source is not None,
                 "factory generation requires boot contract, partition metadata and explicit fstab source")
    records, identities = _load_records(record_paths)
    plan = derive_plan(records, identities, variant=variant)
    kernel = _bind_bundles(plan, records, kernel_receipt, vendor_receipt)
    _bind_vendor_header(plan, records["boot-contract"], workspace_root)
    if factory_selected:
        contract = _factory_profile(plan, kernel, factory_boot_contract, partition_metadata, workspace_root)
        fstab = render_factory_fstab(plan, contract, fstab_source)
    elif fstab_source is None:
        role = _relative(kernel.get("roles", {}).get("fstab"))
        fstab_source = Path(kernel_receipt).parent / role
        fstab = render_fstab(plan, records["boot-contract"], fstab_source)
    else:
        fstab = render_fstab(plan, records["boot-contract"], fstab_source)
    payloads = {}
    _bind_security_patch(plan, patch_source_root, payloads)
    for name in TEMPLATE_FILES:
        _, payloads[(DEVICE_PATH / name).as_posix()] = _read_file(
            Path(template_root) / name, limit=MAX_TEXT_BYTES, collect=True)
    generated = DEVICE_PATH / "generated"
    for name, content in (("BoardConfigCandidate.mk", _render_board(plan)),
                          ("device-candidate.mk", _render_product(plan)), ("fstab.qcom", fstab)):
        payloads[(generated / name).as_posix()] = content.encode()
    plan["files"] = [{"path": path, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
                     for path, data in sorted(payloads.items())]
    plan["schema_version"] = 1
    output = _no_symlinks(output, existing=False)
    artifacts = _no_symlinks(Path(workspace_root) / "artifacts", existing=False)
    _require(output != artifacts and output.is_relative_to(artifacts), "output must be a new artifacts subdirectory")
    _require(not output.exists() and not output.is_symlink(), "output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    _no_symlinks(output.parent)
    staging = Path(tempfile.mkdtemp(prefix=".nezha-device-", dir=output.parent))
    try:
        for name, data in sorted(payloads.items()):
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
        (staging / "admission.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
        validate(staging, purpose="configuration")
        _no_symlinks(output.parent)
        publish_new_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return plan


def validate(output, *, purpose="configuration"):
    _require(purpose in ("configuration", "target-files", "flash"), "unsupported admission purpose")
    plan, _ = _read_json(Path(output) / "admission.json")
    _require(plan.get("profile") == "framework-checks" and _codename(plan) == "nezha", "wrong candidate profile")
    _build_variant(plan.get("variant"))
    admission = plan["admission"]
    _require(admission["flash_allowed"] is False and admission["complete_target_files_allowed"] is False,
             "candidate receipt cannot promote itself to flash/complete packaging")
    _require(plan["avb_policy"]["enabled"] is True and not plan["avb_policy"]["disabled_flags"],
             "AVB policy was weakened")
    files = _file_entries(Path(output), plan["files"])
    expected = {(DEVICE_PATH / name).as_posix() for name in TEMPLATE_FILES}
    expected |= {(DEVICE_PATH / "generated" / name).as_posix()
                 for name in ("BoardConfigCandidate.mk", "device-candidate.mk", "fstab.qcom")}
    expected |= {SECURITY_PATCH.as_posix(), SECURITY_RECORD.as_posix()}
    _require(set(files) == expected, "generated file set is incomplete or unexpected")
    present = set()
    for directory, subdirectories, filenames in os.walk(output, followlinks=False):
        for name in [*subdirectories, *filenames]:
            path = Path(directory) / name
            _require(not path.is_symlink(), "symlink in candidate directory")
        for name in filenames:
            path = Path(directory) / name
            _require(stat.S_ISREG(path.lstat().st_mode), "non-regular candidate file")
            present.add(path.relative_to(output).as_posix())
            _require(len(present) <= len(expected) + 1, "unexpected candidate file")
    _require(present == expected | {"admission.json"}, "unlisted or missing candidate file")
    board = (Path(output) / DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
    _require("BOARD_AVB_ENABLE := true" in board, "generated AVB setting absent")
    _require(not re.search(r"--flags\s+[123]|--set_hashtree_disabled_flag|androidboot.selinux=permissive", board),
             "unsafe generated boot policy")
    _require(purpose == "configuration", f"{purpose} admission refused: framework-checks is not a complete signed partition set")
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "generate"):
        sub = commands.add_parser(command)
        sub.add_argument("--variant", choices=BUILD_VARIANTS, default="userdebug",
                         help="framework-checks build variant (default: userdebug); never a flash admission")
        for name in RECORD_NAMES:
            sub.add_argument("--" + name, type=Path, default=ROOT / "research" / (name + ".json"))
        if command == "generate":
            sub.add_argument("--kernel-receipt", type=Path, required=True)
            sub.add_argument("--vendor-receipt", type=Path, required=True)
            sub.add_argument("--fstab-source", type=Path)
            sub.add_argument("--factory-boot-contract", type=Path,
                             help="factory component/fstab comparison, requires partition metadata and explicit fstab")
            sub.add_argument("--partition-metadata", type=Path,
                             help="verified factory package GPT record; never a live-capacity or flash admission")
            sub.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("validate")
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--purpose", choices=("configuration", "target-files", "flash"), default="configuration")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = validate(args.output, purpose=args.purpose)
        else:
            paths = {name: getattr(args, name.replace("-", "_")) for name in RECORD_NAMES}
            if args.command == "plan":
                result = derive_plan(*_load_records(paths), variant=args.variant)
            else:
                result = generate(args.output, record_paths=paths, kernel_receipt=args.kernel_receipt,
                                  vendor_receipt=args.vendor_receipt, fstab_source=args.fstab_source,
                                  variant=args.variant, factory_boot_contract=args.factory_boot_contract,
                                  partition_metadata=args.partition_metadata)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (CandidateError, OSError, KeyError, TypeError, StopIteration, ValueError) as exc:
        print(f"device generation refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
