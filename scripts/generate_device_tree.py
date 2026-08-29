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
    "lineage_nezha.mk", "README.md", "recovery-prebuilt.mk", "init-helper-capability.mk",
    "recovery/root/init.recovery.qcom.rc",
)
DSP_POLICY_RECORD = PurePosixPath("research/dsp-policy-integration.json")
DSP_POLICY_CONTRACT_ID = "nezha-dsp-membership-v1"
DSP_POLICY_CONTRACT_SHA256 = "30720967a28cb558a0e3f90ed26a1f8e7c5b6befde55fea8428bbe8e693cd1f9"
DSP_POLICY_FILES = (
    "sepolicy/system_ext/public/attributes",
    "sepolicy/product/private/isolated_compute_app.te",
)
DSP_POLICY_WIRING = {
    "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/public",
    "PRODUCT_PRIVATE_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/product/private",
}
INIT_HELPER_RECORD = PurePosixPath("config/nezha-init-helper-capability.json")
INIT_HELPER_CONTRACT_ID = "nezha-init-helper-no-property-writes-v1"
INIT_HELPER_CONTRACT_SHA256 = "9a4728a13efac5a974507557c8130591c1cf1f29cfdeb749872d3e42c28e96d7"
INIT_HELPER_PATCH = PurePosixPath("patches/evolution/0004-gate-init-dev-config-property-writes.patch")
INIT_HELPER_METADATA = PurePosixPath("patches/evolution/init-helper-property-writes.json")
INIT_HELPER_AUDIT = PurePosixPath("research/init-helper-capability-audit.json")
INIT_HELPER_SYMBOL = "target_init_dev_config_property_writes"
INIT_HELPER_CAPABILITY = {
    "board_variable": "BOARD_SEPOLICY_M4DEFS", "symbol": INIT_HELPER_SYMBOL,
    "value": "false", "api_version_inference_used": False,
}
INIT_HELPER_LIMITS = {
    "component_configuration_only": True,
    "complete_installed_input_closure_verified": False,
    "runtime_helper_absence_verified": False,
    "runtime_apex_media_camera_verified": False,
    "complete_rom_admitted": False,
    "phone_mutations_authorized": False,
}
POLICY_INPUTS_PATH = "vendor/xiaomi/nezha-policy"
POLICY_INPUTS_RECEIPT = "policy-inputs.json"
MI_EXT_INPUTS_PATH = "vendor/xiaomi/nezha-mi-ext"
MI_EXT_INPUTS_RECEIPT = "mi-ext-inputs.json"
MI_EXT_BOARD_INCLUDE = DEVICE_PATH / "generated/mi-ext-prebuilt.mk"
OEM_POLICY_RECORD = PurePosixPath("config/nezha-oem-policy.json")
OEM_POLICY_CONTRACT_ID = "nezha-oem-system-ext-policy-v1"
OEM_POLICY_CONTRACT_SHA256 = "3de325f5ff8ba52dc8e43e20556fe876cc44905b04d40ed3b0ff038eaff10cc7"
OEM_POLICY_FILES = (
    "sepolicy/system_ext/oem/public/nezha_oem_service.te",
    "sepolicy/system_ext/oem/private/nezha_oem_data.te",
)
OEM_POLICY_WIRING = {
    "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/oem/public",
    "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/oem/private",
}
OEM_POLICY_TYPES = {
    "vendor_hal_atfwd_hwservice": {
        "scope": "system_ext_public", "role": "object_r",
        "attributes": ["coredomain_hwservice", "hwservice_manager_type", "protected_hwservice"],
        "versioned_attribute": "vendor_hal_atfwd_hwservice_202504",
        "mapping_members": ["vendor_hal_atfwd_hwservice"],
    },
    "vendor_hal_systemhelper_aidl_service": {
        "scope": "system_ext_public", "role": "object_r",
        "attributes": ["hal_service_type", "protected_service", "service_manager_type"],
        "versioned_attribute": "vendor_hal_systemhelper_aidl_service_202504",
        "mapping_members": ["vendor_hal_systemhelper_aidl_service"],
    },
    "offlinelog_file": {
        "scope": "system_ext_private", "role": "object_r",
        "attributes": ["core_data_file_type", "data_file_type", "file_type"],
        "versioned_attribute": None, "mapping_members": [],
    },
}
OEM_POLICY_LIMITS = frozenset({
    "complete_rom_admitted", "device_runtime_support_proven", "new_allow_statements_added",
    "oem_framework_imported_wholesale", "original_neverallows_removed",
    "phone_mutations_authorized", "service_objects_promoted_to_process_domains",
})
OEM_PROPERTY_RECORD = PurePosixPath("config/nezha-oem-properties.json")
OEM_PROPERTY_CONTRACT_ID = "nezha-oem-properties-v1"
OEM_PROPERTY_CONTRACT_SHA256 = "f5796d6df4b7232d32ffdece83bc2d5726669fbb6f34f0ba2ef86be6cbc1d711"
OEM_PROPERTY_FILES = (
    "sepolicy/system_ext/oem_properties/public/property.te",
    "sepolicy/system_ext/oem_properties/private/mediaextractor.te",
    "sepolicy/system_ext/oem_properties/private/mediaserver.te",
    "sepolicy/system_ext/oem_properties/private/property_contexts",
)
OEM_PROPERTY_WIRING = {
    "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/oem_properties/public",
    "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/oem_properties/private",
}
OEM_PROPERTY_TYPES = {
    name: {"scope": "system_ext_public", "role": "object_r", "source_macro": "system_public_prop",
           "attributes": ["property_type", "system_property_type", "system_public_property_type"],
           "versioned_attribute": name + "_202504", "mapping_members": [name]}
    for name in ("vendor_mm_parser_prop", "vendor_persist_dpm_prop", "vendor_sys_video_prop", "vendor_wlc_public_prop")
}
OEM_PROPERTY_CONTEXTS = {
    "persist.vendor.dpm.": "vendor_persist_dpm_prop",
    "vendor.mm.enable.qcom_parser": "vendor_mm_parser_prop",
    "vendor.qcom_parser.": "vendor_mm_parser_prop",
    "vendor.mpctl.init.complete": "vendor_wlc_public_prop",
    "vendor.sys.media.target.version": "vendor_sys_video_prop",
    "vendor.sys.video.disable.ubwc": "vendor_sys_video_prop",
    "vendor.sys.media.target.qssi": "vendor_sys_video_prop",
    "persist.dpm.feature": "vendor_persist_dpm_prop",
}
OEM_PROPERTY_ALLOW_BUDGET = {
    "vendor_mm_parser_prop": {"count": 26, "sha256_sorted_compact_json_rows": "a701124306a8f89e4867d314f8c72a17dc278f77bbba4d98d6ad7b8ec614ebb9"},
    "vendor_persist_dpm_prop": {"count": 27, "sha256_sorted_compact_json_rows": "984920c434a04ea145b30502dd29ec7c4064a89c1dd956827f037b42710b7afb"},
    "vendor_sys_video_prop": {"count": 26, "sha256_sorted_compact_json_rows": "dae03ee5d6afe516b40a948b947293767a5062d82cb851658d7664a470ae32d5"},
    "vendor_wlc_public_prop": {"count": 26, "sha256_sorted_compact_json_rows": "30596a656bd7c88503d5e48ac52734733ce745b426b5e80cd6f9a0248870f2da"},
}
OEM_PROPERTY_LIMITS = frozenset({
    "complete_rom_admitted", "context_or_treble_tests_proven", "default_profile_changed",
    "denial_logging_unchanged", "device_runtime_support_proven", "factory_policy_files_modified",
    "framework_vendor_dpmd_provider_restored", "native_policy_compilation_proven", "original_neverallows_removed",
    "phone_mutations_authorized", "source_set_prop_rules_added", "vendor_wlc_private_property_or_app_restored",
    "wireless_charging_support_inferred",
})
OEM_PROPERTY_EVIDENCE = ("finite_impact_audit", "finite_impact_readback", "independent_finite_impact_review")
FRAMEWORK_PROVIDER_RECORD = PurePosixPath("config/nezha-framework-provider-policy.json")
FRAMEWORK_PROVIDER_CONTRACT_SHA256 = "6515395854a7cdc08f2d9c9ed5f7119164a9c0376ca8710a152ffb1999dc52f8"
FRAMEWORK_PROVIDER_INPUT_RECORD = PurePosixPath("config/nezha-framework-providers.json")
FRAMEWORK_PROVIDER_INPUT_SHA256 = "467667d20399469d0b5621a4a7891e896ce6c3f785830ee0ad0dd17a06b8c45f"
FRAMEWORK_PROVIDER_INPUTS_PATH = "vendor/xiaomi/nezha-framework-providers"
FRAMEWORK_PROVIDER_INPUTS_RECEIPT = "framework-provider-inputs.json"
FRAMEWORK_PROVIDER_MODULE_PACKAGE = "device/xiaomi/nezha/framework-providers"
FRAMEWORK_PROVIDER_BLUEPRINT = FRAMEWORK_PROVIDER_MODULE_PACKAGE + "/Android.bp"
FRAMEWORK_PROVIDER_FILES = (
    "sepolicy/system_ext/framework_providers/private/file_contexts",
    "sepolicy/system_ext/framework_providers/private/service_contexts",
    "sepolicy/system_ext/framework_providers/private/vendor_qccsyshal_qti.te",
    "sepolicy/system_ext/framework_providers/private/vendor_sigmahal_qti.te",
)
FRAMEWORK_PROVIDER_WIRING = {
    "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/framework_providers/private",
}
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


def _dsp_contract(path):
    """Accept only the reviewed publication, never an arbitrary policy recipe."""
    record, identity = _read_json(path)
    _require(identity["sha256"] == DSP_POLICY_CONTRACT_SHA256,
             "unknown or changed DSP policy contract")
    _require(_codename(record) == "nezha" and record["device"]["hardware_region"] == "CN",
             "DSP policy contract requires China Nezha")
    contract = record["generator_contract"]
    _require(contract["contract_id"] == DSP_POLICY_CONTRACT_ID and
             contract["profile"] == "framework-checks", "unsupported DSP policy contract")
    _require(contract["factory_origin_verified"] is False,
             "DSP policy contract cannot authenticate factory origin")
    _digest(contract["factory_package_sha256"], "DSP factory package")
    _require(contract["wiring"] == DSP_POLICY_WIRING, "unexpected DSP policy source wiring")
    expected = {(DEVICE_PATH / name).as_posix() for name in DSP_POLICY_FILES}
    sources = contract["source_files"]
    _require(isinstance(sources, list) and len(sources) == 2 and
             {entry["path"] for entry in sources} == expected, "unexpected DSP policy source files")
    for entry in sources:
        _digest(entry["sha256"], "DSP source file")
        _integer(entry["size_bytes"], "DSP source file length", MAX_TEXT_BYTES)
    return contract, identity


def _dsp_admission(contract, identity):
    """A source-only admission; later Soong/device results cannot be inferred."""
    return {
        "contract_id": DSP_POLICY_CONTRACT_ID,
        "contract_record": {"path": DSP_POLICY_RECORD.as_posix(), **identity},
        "factory_package_sha256": contract["factory_package_sha256"],
        "factory_origin_verified": False,
        "required_source_revisions": contract["required_source_revisions"],
        "source_files": contract["source_files"],
        "wiring": dict(DSP_POLICY_WIRING),
        "factory_policy_inputs_rehashed": 3,
        "fixture_readback_files_rehashed": 77,
        "fixture_original_assertions_retained": 6366,
        "fixture_assertion_sites_before": 5,
        "fixture_assertion_sites_after": 4,
        "source_checkout_inspected": False,
        "fresh_soong_or_m4_build_performed": False,
        "strict_full_policy_compiled": False,
        "native_dsp_access_verified": False,
    }


def _dsp_wiring_lines():
    # The complete preceding comment terminates any continued comment before
    # this section, so neither actual directive can become part of that comment.
    return ["# Reviewed DSP source interface; full SELinux compatibility remains unverified.",
            *(f"{name} += {path}" for name, path in DSP_POLICY_WIRING.items())]


def _dsp_factory_binding(plan, contract):
    profile, packages = plan.get("factory_profile"), plan.get("source_packages")
    _require(isinstance(profile, dict) and isinstance(packages, dict) and
             profile.get("package_sha256") == packages.get("vendor") == contract["factory_package_sha256"],
             "DSP policy contract requires its reviewed factory vendor package")
    _require(profile.get("origin_verified") is False,
             "DSP policy admission cannot promote factory origin")


def _bind_dsp_policy(plan, records, path, workspace_root, template_root, payloads):
    contract, identity = _dsp_contract(path)
    _dsp_factory_binding(plan, contract)
    partitions = {part["name"]: part for part in records["firmware-layout"]["partitions"]}
    _require(set(contract["vendor_images"]) == {"vendor", "odm"},
             "DSP policy contract requires both factory images")
    for name, expected in contract["vendor_images"].items():
        source = partitions[name + "_a"]
        _require(expected == {"sha256": source["extraction"]["sha256"],
                              "size_bytes": source["size_bytes"]},
                 "DSP policy vendor image differs from its reviewed factory input")
    policy = _bound_reference(contract["policy_capture_receipt"], workspace_root)
    _require(policy["parent_package_sha256"] == contract["factory_package_sha256"] and
             policy["origin_verified"] is False, "DSP policy capture package differs")
    inputs = contract["policy_inputs"]
    expected_paths = {"/vendor/etc/selinux/plat_pub_versioned.cil",
                      "/vendor/etc/selinux/vendor_sepolicy.cil",
                      "/odm/etc/selinux/odm_sepolicy.cil"}
    _require(len(inputs) == 3 and {row["runtime_path"] for row in inputs} == expected_paths,
             "DSP policy contract requires the exact three factory policy inputs")
    for row in inputs:
        matches = [item for item in policy["input_order"]
                   if item["runtime_path"] == row["runtime_path"]]
        _require(len(matches) == 1 and all(matches[0][key] == row[key]
                 for key in ("path", "sha256", "size_bytes")), "DSP policy capture binding differs")
        actual, _ = _read_file(Path(workspace_root) / _relative(row["path"]), limit=MAX_JSON_BYTES)
        _require(actual == {key: row[key] for key in ("sha256", "size_bytes")},
                 "DSP factory policy input hash/size mismatch")
    _bound_reference(contract["source_ownership_receipt"], workspace_root)
    fixture = _bound_reference(contract["fixture_receipt"], workspace_root)
    _require(fixture["proof_completed"] is True and not fixture["errors"] and
             not fixture["guard_errors"] and fixture["complete_assertion_multiset_equal"] is True and
             fixture["complete_assertion_count"] == 6366 and
             fixture["corresponding_dsp_failure_removed"] is True and
             fixture["all_four_other_diagnostics_preserved"] is True and
             len(fixture["baseline_diagnostics"]) == 5 and len(fixture["candidate_diagnostics"]) == 4,
             "DSP source fixture does not establish the reviewed assertion reduction")
    _require(all(fixture[key] is False for key in (
        "neverallow_checks_disabled", "original_assertions_removed", "new_allow_statements_added",
        "fresh_soong_or_m4_build_performed", "strict_compilation_passed",
        "android_source_or_out_written", "user_out_accessed", "phone_accessed", "firmware_executed")),
        "DSP fixture scope or security checks changed")
    readback = _bound_reference(contract["readback_receipt"], workspace_root)
    _require(readback["receipt_sha256"] == contract["fixture_receipt"]["sha256"] and
             readback["guest_writes"] is False and len(readback["files"]) == 77,
             "DSP readback does not bind the reviewed fixture")
    _integer(readback["total_bytes"], "DSP readback byte count", 64 * 1024 * 1024)
    _require(all(type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= MAX_JSON_BYTES
                 for row in readback["files"]) and
             sum(row["size_bytes"] for row in readback["files"]) == readback["total_bytes"],
             "DSP readback file sizes differ from its bounded total")
    entries = [{"path": row["host_path"], "sha256": row["sha256"],
                "size_bytes": row["size_bytes"]} for row in readback["files"]]
    files = _file_entries(Path(workspace_root), entries)
    _require(sum(row["size_bytes"] for row in files.values()) == readback["total_bytes"],
             "DSP readback byte count differs")
    for entry in contract["source_files"]:
        relative = _relative(entry["path"]).relative_to(DEVICE_PATH)
        actual, raw = _read_file(Path(template_root) / relative, limit=MAX_TEXT_BYTES, collect=True)
        _require(actual == {key: entry[key] for key in ("sha256", "size_bytes")},
                 "DSP policy source file hash/size mismatch")
        payloads[entry["path"]] = raw
    actual, raw = _read_file(path, limit=MAX_JSON_BYTES, collect=True)
    _require(actual == identity, "DSP policy contract changed before publication")
    payloads[DSP_POLICY_RECORD.as_posix()] = raw
    plan["dsp_policy"] = _dsp_admission(contract, identity)


def _init_helper_contract(path):
    contract, identity = _read_json(path)
    _require(identity["sha256"] == INIT_HELPER_CONTRACT_SHA256,
             "unknown or changed init-helper capability contract")
    _require(contract["device"] == {"codename": "nezha", "hardware_region": "CN"} and
             contract["profile"] == "framework-checks" and
             contract["contract_id"] == INIT_HELPER_CONTRACT_ID,
             "unsupported init-helper capability contract")
    _require(contract["capability"] == INIT_HELPER_CAPABILITY and
             contract["provider_contract"] is None and contract["limits"] == INIT_HELPER_LIMITS,
             "init-helper capability or scope changed")
    _require(contract["factory_origin_verified"] is False,
             "init-helper contract cannot authenticate factory origin")
    _digest(contract["factory_package_sha256"], "init-helper factory package")
    _require(contract["source_patch"]["path"] == INIT_HELPER_PATCH.as_posix() and
             contract["patch_metadata"]["path"] == INIT_HELPER_METADATA.as_posix() and
             contract["prior_component_audit"]["path"] == INIT_HELPER_AUDIT.as_posix(),
             "unexpected init-helper source patch")
    guards = contract["device_guards"]
    _require(len(guards) == 2 and {row["path"] for row in guards} == {
        (DEVICE_PATH / "BoardConfig.mk").as_posix(),
        (DEVICE_PATH / "init-helper-capability.mk").as_posix(),
    }, "unexpected init-helper device guards")
    return contract, identity


def _init_helper_factory_binding(plan, contract):
    _require("factory_profile" in plan and "dsp_policy" in plan and
             plan["factory_profile"]["package_sha256"] ==
             plan["source_packages"]["vendor"] == contract["factory_package_sha256"],
             "init-helper capability requires the reviewed factory and DSP profile")
    _require(plan["factory_profile"]["origin_verified"] is False,
             "init-helper admission cannot promote factory origin")


def _init_helper_admission(contract, identity):
    return {
        "contract_id": INIT_HELPER_CONTRACT_ID,
        "contract_record": {"path": INIT_HELPER_RECORD.as_posix(), **identity},
        "capability": dict(INIT_HELPER_CAPABILITY),
        "factory_package_sha256": contract["factory_package_sha256"],
        "factory_origin_verified": False,
        "required_source_revisions": contract["required_source_revisions"],
        "required_patched_source": contract["required_patched_source"],
        "prior_component_audit": contract["prior_component_audit"],
        "static_factory_files_rehashed": contract["static_input_file_count"],
        "static_factory_bytes_rehashed": contract["static_input_total_bytes"],
        "source_checkout_inspected": False,
        "fresh_soong_or_m4_build_performed": False,
        "strict_full_policy_compiled": False,
        "limits": dict(INIT_HELPER_LIMITS),
    }


def _init_helper_conflicts(raw, label):
    # A deliberately conservative literal check, not an init/import evaluator.
    # The only admitted invocation is the pinned upstream optional service;
    # authored and selected factory inputs may not add another provider.
    terms = (b"init_dev_config", b"ro.boot.init_rc", b"androidboot.init_rc",
             b"TARGET_INIT_VENDOR_LIB", b"vendor_init_lib")
    _require(not any(term in raw for term in terms),
             f"uncontracted init-helper provider, invocation, label or boot selector: {label}")


def _bind_init_helper_capability(plan, records, path, workspace_root, patch_source_root,
                                 vendor_receipt, payloads):
    contract, identity = _init_helper_contract(path)
    _init_helper_factory_binding(plan, contract)
    partitions = {part["name"]: part for part in records["firmware-layout"]["partitions"]}
    _require(set(contract["vendor_images"]) == {"vendor", "odm"},
             "init-helper contract requires both factory images")
    for name, expected in contract["vendor_images"].items():
        source = partitions[name + "_a"]
        _require(expected == {"sha256": source["extraction"]["sha256"],
                              "size_bytes": source["size_bytes"]},
                 "init-helper image differs from its reviewed factory input")
    metadata = _bound_reference(contract["patch_metadata"], patch_source_root)
    _require(metadata["base_commit"] == contract["required_source_revisions"]["system/sepolicy"] and
             metadata["patch_sha256"] == contract["source_patch"]["sha256"] and
             len(metadata["files"]) == 1 and contract["required_patched_source"] == {
                 "path": "system/sepolicy/" + metadata["files"][0]["path"],
                 "sha256": metadata["files"][0]["after_sha256"],
                 "size_bytes": metadata["files"][0]["after_size_bytes"],
             }, "init-helper source metadata differs from its reviewed patch")
    audit = _bound_reference(contract["prior_component_audit"], workspace_root)
    _require(audit["source_pins"] == contract["required_source_revisions"] and
             audit["selected_factory_evidence"]["factory_package_sha256"] == contract["factory_package_sha256"] and
             audit["selected_init_rc"]["upstream_optional_service_preserved"] is True and
             audit["validation"]["final_init_hook_bytes_and_text_identity_passed"] is True and
             audit["validation"]["selected_init_rc_identity_passed"] is True and
             audit["proposed_capability"]["complete_rom_admission"] is False,
             "init-helper prior component audit does not bind the selected source and inputs")
    for row in contract["source_captures"]:
        _require(row["commit"] == contract["required_source_revisions"][row["project"]],
                 "init-helper captured source revision differs")
    _file_entries(Path(workspace_root), contract["source_captures"])
    scan = _bound_reference(contract["static_input_scan"], workspace_root)
    _require(scan["factory_package_sha256"] == contract["factory_package_sha256"] and
             scan["factory_origin_authenticated"] is False and
             len(scan["partitions"]) == 2 and
             {row["partition"] for row in scan["partitions"]} == {"vendor", "odm"},
             "init-helper static scan has different factory inputs")
    count, total, selected = 0, 0, set()
    for partition in scan["partitions"]:
        name = partition["partition"]
        _require(partition["image_sha256"] == contract["vendor_images"][name]["sha256"],
                 "init-helper static scan image differs")
        entries = [{"path": row["host_path"], "sha256": row["sha256"],
                    "size_bytes": row["size_bytes"]} for row in partition["files"]]
        _require(len(entries) == partition["file_count"] and
                 sum(row["size_bytes"] for row in entries) == partition["total_bytes"],
                 "init-helper static scan inventory differs")
        verified = _file_entries(Path(workspace_root), entries)
        for row in partition["files"]:
            runtime = (name, row["image_path"])
            _require(runtime not in selected, "duplicate init-helper static input")
            selected.add(runtime)
            actual, raw = _read_file(Path(workspace_root) / _relative(row["host_path"]),
                                     limit=MAX_TEXT_BYTES, collect=True)
            _require(actual == verified[row["host_path"]], "init-helper static input changed")
            _init_helper_conflicts(raw, f"{name}{row['image_path']}")
            count += 1
            total += actual["size_bytes"]
    _require(count == contract["static_input_file_count"] and
             total == contract["static_input_total_bytes"], "init-helper static scan totals differ")
    guarded = {row["path"] for row in contract["device_guards"]}
    for row in contract["device_guards"]:
        raw = payloads[row["path"]]
        _require({"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)} ==
                 {key: row[key] for key in ("sha256", "size_bytes")},
                 "init-helper device guard differs from the reviewed contract")
    for name, raw in payloads.items():
        if name.startswith(DEVICE_PATH.as_posix() + "/") and name not in guarded and not name.endswith("README.md"):
            _init_helper_conflicts(raw, name)
    vendor, vendor_identity = _read_json(vendor_receipt)
    _require(all(vendor_identity[key] == plan["bundles"]["vendor"][key]
                 for key in ("sha256", "size_bytes")), "init-helper vendor receipt changed")
    for row in [*vendor["generated_files"], *vendor.get("extras", [])]:
        if Path(row["path"]).suffix in (".mk", ".bp", ".rc", ".prop", ".te", ".cil", ".json", ".xml") or "contexts" in Path(row["path"]).name:
            actual, raw = _read_file(Path(vendor_receipt).parent / _relative(row["path"]),
                                     limit=MAX_TEXT_BYTES, collect=True)
            _require(actual == {key: row[key] for key in ("sha256", "size_bytes")},
                     "init-helper selected vendor configuration changed")
            _init_helper_conflicts(raw, row["path"])
    for row in (contract["source_patch"], contract["patch_metadata"]):
        actual, raw = _read_file(Path(patch_source_root) / _relative(row["path"]),
                                 limit=MAX_TEXT_BYTES, collect=True)
        _require(actual == {key: row[key] for key in ("sha256", "size_bytes")},
                 "init-helper patch hash/size mismatch")
        payloads[row["path"]] = raw
    actual, raw = _read_file(Path(workspace_root) / INIT_HELPER_AUDIT, limit=MAX_JSON_BYTES, collect=True)
    _require(actual == {key: contract["prior_component_audit"][key] for key in ("sha256", "size_bytes")},
             "init-helper prior component audit changed before publication")
    payloads[INIT_HELPER_AUDIT.as_posix()] = raw
    actual, raw = _read_file(path, limit=MAX_JSON_BYTES, collect=True)
    _require(actual == identity, "init-helper contract changed before publication")
    payloads[INIT_HELPER_RECORD.as_posix()] = raw
    plan["init_helper_capability"] = _init_helper_admission(contract, identity)


def _init_helper_wiring_lines():
    definitions = ("$(strip $(foreach _nezha_m4def,$(BOARD_SEPOLICY_M4DEFS),"
                   f"$(if $(findstring {INIT_HELPER_SYMBOL},$(_nezha_m4def)),$(_nezha_m4def))))")
    return [
        "# Explicit reviewed init-helper capability; never inferred from an API level.",
        "ifneq ($(origin NEZHA_INIT_HELPER_CAPABILITY_CONTRACT),undefined)",
        "$(error Nezha init-helper capability marker must be generated exactly once)",
        "endif",
        f"NEZHA_INIT_HELPER_CAPABILITY_CONTRACT := {INIT_HELPER_CONTRACT_ID}",
        "ifneq ($(filter undefined file,$(origin BOARD_SEPOLICY_M4DEFS)),$(origin BOARD_SEPOLICY_M4DEFS))",
        "$(error Nezha init-helper M4 definitions cannot be supplied by an override)",
        "endif",
        f"ifneq ({definitions},)",
        "$(error Nezha init-helper M4 definition must be generated exactly once)",
        "endif",
        f"BOARD_SEPOLICY_M4DEFS += {INIT_HELPER_SYMBOL}=false",
    ]


def _oem_policy_contract(path):
    contract, identity = _read_json(path)
    _require(identity["sha256"] == OEM_POLICY_CONTRACT_SHA256,
             "unknown or changed OEM policy contract")
    _require(contract["device"] == {"codename": "nezha", "hardware_region": "CN"} and
             contract["profile"] == "framework-checks" and
             contract["contract_id"] == OEM_POLICY_CONTRACT_ID,
             "unsupported OEM policy contract")
    _require(contract["platform"] == {"branch": "bka", "release": "bp4a", "board_api": "202504"} and
             contract["wiring"] == OEM_POLICY_WIRING,
             "OEM policy platform or source wiring differs from the reviewed contract")
    _require(contract["factory_origin_verified"] is False and
             set(contract["limits"]) == OEM_POLICY_LIMITS and
             all(value is False for value in contract["limits"].values()) and
             contract["types"] == OEM_POLICY_TYPES,
             "OEM policy type ownership, permissions or scope changed")
    _digest(contract["factory_package_sha256"], "OEM factory package")
    sources = contract["source_files"]
    _require(isinstance(sources, list) and len(sources) == len(OEM_POLICY_FILES) and
             {row["path"] for row in sources} == {(DEVICE_PATH / name).as_posix() for name in OEM_POLICY_FILES},
             "unexpected OEM policy source files")
    for row in sources:
        expected_scope = "system_ext_public" if "/public/" in row["path"] else "system_ext_private"
        _require(row["scope"] == expected_scope, "OEM policy source ownership changed")
        _digest(row["sha256"], "OEM policy source")
        _integer(row["size_bytes"], "OEM policy source length", MAX_TEXT_BYTES)
    expected_factory = {"/vendor/etc/selinux/plat_pub_versioned.cil",
                        "/vendor/etc/selinux/vendor_sepolicy.cil", "/odm/etc/selinux/odm_sepolicy.cil"}
    inputs = contract["unchanged_factory_inputs"]
    _require(len(inputs) == 3 and {row["runtime_path"] for row in inputs} == expected_factory,
             "OEM policy requires the original three factory policy inputs")
    evidence = contract["evidence"]["source_rows"]
    _require(len(evidence) == 3 and {row["runtime_path"] for row in evidence} == {
        "/system_ext/etc/selinux/system_ext_sepolicy.cil",
        "/system_ext/etc/selinux/mapping/202504.cil",
        "/product/etc/selinux/product_sepolicy.cil",
    }, "OEM policy requires the reviewed framework ownership evidence")
    for row in [*inputs, *evidence]:
        _digest(row["sha256"], "OEM factory policy input")
        _integer(row["size_bytes"], "OEM factory policy length", MAX_JSON_BYTES)
    return contract, identity


def _oem_policy_binding(plan, contract, dsp_contract):
    _require("factory_profile" in plan and "dsp_policy" in plan and "init_helper_capability" in plan,
             "OEM policy requires the explicit factory, DSP and helper capabilities")
    _require(plan["source_packages"]["vendor"] == plan["factory_profile"]["package_sha256"] ==
             contract["factory_package_sha256"] and plan["factory_profile"]["origin_verified"] is False,
             "OEM policy requires the reviewed unauthenticated factory package")
    _require(str(plan["board_shipping_api_level"]) == contract["platform"]["board_api"],
             "OEM policy mapping requires the exact reviewed board API")
    helper = plan["init_helper_capability"]
    _require(contract["required_capability_contract"] == {
        "path": INIT_HELPER_RECORD.as_posix(), "sha256": helper["contract_record"]["sha256"],
        "symbol": INIT_HELPER_SYMBOL, "value": "false",
    }, "OEM policy requires the exact reviewed helper capability contract")
    revisions = {**helper["required_source_revisions"], **plan["dsp_policy"]["required_source_revisions"]}
    required_projects = {"system/sepolicy", "external/selinux", "build/soong"}
    _require(set(contract["required_source_revisions"]) == required_projects and
             all(revisions[project] == revision for project, revision in contract["required_source_revisions"].items()),
             "OEM policy source revisions differ from the reviewed framework inputs")
    expected = {row["runtime_path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                for row in dsp_contract["policy_inputs"]}
    actual = {row["runtime_path"]: {key: row[key] for key in ("sha256", "size_bytes")}
              for row in contract["unchanged_factory_inputs"]}
    _require(actual == expected, "OEM policy original factory inputs differ from the DSP admission")


def _oem_policy_admission(contract, identity):
    return {
        "contract_id": OEM_POLICY_CONTRACT_ID,
        "contract_record": {"path": OEM_POLICY_RECORD.as_posix(), **identity},
        "factory_package_sha256": contract["factory_package_sha256"],
        "source_files": contract["source_files"],
        "required_source_revisions": contract["required_source_revisions"],
        "unchanged_factory_inputs": contract["unchanged_factory_inputs"],
        "types": contract["types"],
        "wiring": dict(OEM_POLICY_WIRING),
        "api_mapping": "generated-by-pinned-source-pipeline-at-202504",
        "factory_framework_evidence_files_rehashed": 3,
        "triage_receipt": contract["evidence"]["triage"],
        "source_checkout_inspected": False,
        "fresh_soong_or_m4_build_performed": False,
        "strict_full_policy_compiled": False,
        "complete_context_or_treble_checks_passed": False,
        "image_integration_verified": False,
        "hardware_tested": False,
    }


def _bind_oem_policy(plan, path, workspace_root, template_root, payloads):
    contract, identity = _oem_policy_contract(path)
    dsp = json.loads(payloads[DSP_POLICY_RECORD.as_posix()], object_pairs_hook=_unique_object)["generator_contract"]
    _oem_policy_binding(plan, contract, dsp)
    capture = _bound_reference(dsp["policy_capture_receipt"], workspace_root)
    _require(capture["parent_package_sha256"] == contract["factory_package_sha256"] and
             capture["origin_verified"] is False, "OEM factory framework capture package differs")
    for row in contract["evidence"]["source_rows"]:
        matches = [source for source in capture["input_order"] if source["runtime_path"] == row["runtime_path"]]
        _require(len(matches) == 1 and all(matches[0][key] == row[key] for key in ("sha256", "size_bytes")),
                 "OEM framework ownership evidence differs from the factory capture")
        actual, _ = _read_file(Path(workspace_root) / _relative(matches[0]["path"]), limit=MAX_JSON_BYTES)
        _require(actual == {key: row[key] for key in ("sha256", "size_bytes")},
                 "OEM factory framework evidence hash/size mismatch")
    triage = _bound_reference(contract["evidence"]["triage"], workspace_root)
    _require(triage["all_inputs_rehashed_unchanged"] is True and triage["compiler_invoked"] is False and
             triage["oem_te_source_recovered"] is False and triage["source_or_guest_mutated"] is False,
             "OEM source evidence must remain a bounded generated-CIL observation")
    for row in contract["source_files"]:
        relative = _relative(row["path"]).relative_to(DEVICE_PATH)
        actual, raw = _read_file(Path(template_root) / relative, limit=MAX_TEXT_BYTES, collect=True)
        _require(actual == {key: row[key] for key in ("sha256", "size_bytes")},
                 "OEM policy source file hash/size mismatch")
        payloads[row["path"]] = raw
    actual, raw = _read_file(path, limit=MAX_JSON_BYTES, collect=True)
    _require(actual == identity, "OEM policy contract changed before publication")
    payloads[OEM_POLICY_RECORD.as_posix()] = raw
    plan["oem_policy"] = _oem_policy_admission(contract, identity)


def _oem_policy_wiring_lines():
    return ["# Reviewed OEM system_ext source restoration; complete ROM admission remains false.",
            *(f"{name} += {path}" for name, path in OEM_POLICY_WIRING.items())]


def _oem_property_contract(path):
    contract, identity = _read_json(path)
    _require(identity["sha256"] == OEM_PROPERTY_CONTRACT_SHA256, "unknown or changed OEM property contract")
    _require(contract["contract_id"] == OEM_PROPERTY_CONTRACT_ID and
             contract["device"] == {"codename": "nezha", "hardware_region": "CN"} and
             contract["profile"] == "framework-checks" and
             contract["platform"] == {"branch": "bka", "release": "bp4a", "board_api": "202504"} and
             contract["wiring"] == OEM_PROPERTY_WIRING,
             "OEM property platform or source ownership differs from the reviewed contract")
    _require(contract["factory_origin_verified"] is False and contract["types"] == OEM_PROPERTY_TYPES and
             set(contract["limits"]) == OEM_PROPERTY_LIMITS and all(value is False for value in contract["limits"].values()) and
             contract["native_effective_ordinary_allow_edges"] == OEM_PROPERTY_ALLOW_BUDGET,
             "OEM property types, membership budget or scope changed")
    sources = contract["source_files"]
    expected = {(DEVICE_PATH / name).as_posix(): ("system_ext_public", "system_public_prop") if "/public/" in name else
                ("system_ext_private", "property_contexts" if name.endswith("property_contexts") else "get_prop")
                for name in OEM_PROPERTY_FILES}
    _require(type(sources) is list and len(sources) == 4 and {row["path"] for row in sources} == set(expected),
             "OEM property contract requires exactly the four reviewed source files")
    for row in sources:
        _require((row["scope"], row["kind"]) == expected[row["path"]], "OEM property source scope or kind changed")
        _digest(row["sha256"], "OEM property source")
        _integer(row["size_bytes"], "OEM property source length", MAX_TEXT_BYTES)
    reads = contract["read_clauses"]
    _require(type(reads) is list and len(reads) == 2 and
             {(row["source_type"], row["target_type"]) for row in reads} == {
                 ("mediaextractor", "vendor_mm_parser_prop"), ("mediaserver", "vendor_sys_video_prop")} and
             all(row["source_macro"] == "get_prop" and row["class"] == "file" and
                 row["permissions"] == ["getattr", "map", "open", "read"] for row in reads),
             "OEM property source grants differ from the two reviewed read clauses")
    contexts = contract["property_contexts"]
    _require(type(contexts) is list and len(contexts) == 8 and
             {row["property_pattern"]: row["type"] for row in contexts} == OEM_PROPERTY_CONTEXTS and
             all(row["match"] == "prefix" and row["value_type"] is None and row["legacy_implicit_prefix"] is True and
                 row["context"] == "u:object_r:" + row["type"] + ":s0" for row in contexts),
             "OEM property prefixes, labels or matching semantics changed")
    assertions = contract["finite_impact"]["assertions"]
    _require(assertions["exact_statement_multisets_unchanged"] is True and assertions["total_statements_retained"] == 6366 and
             assertions["new_ordinary_conflict_edges"] == 0 and assertions["ordinary_semantic_restriction_edges_removed"] == 0,
             "OEM property assertion preservation evidence changed")
    for key in OEM_PROPERTY_EVIDENCE:
        row = contract["evidence"][key]
        _relative(row["path"])
        _digest(row["sha256"], "OEM property evidence")
        _integer(row["size_bytes"], "OEM property evidence length", MAX_JSON_BYTES)
    return contract, identity


def _oem_property_binding(plan, contract, base):
    _require("oem_policy" in plan and "init_helper_capability" in plan and "dsp_policy" in plan and "factory_profile" in plan,
             "OEM properties require the explicit OEM, helper, DSP and factory capabilities")
    _require(contract["base_oem_contract"] == plan["oem_policy"]["contract_record"] and
             contract["factory_package_sha256"] == plan["source_packages"]["vendor"] == base["factory_package_sha256"] and
             contract["required_capability_contract"] == base["required_capability_contract"] and
             contract["unchanged_factory_inputs"] == base["unchanged_factory_inputs"] and
             contract["existing_vendor_derivation"] == base["existing_vendor_derivation"],
             "OEM properties must retain the exact OEM base, helper, factory inputs and Binder derivation")
    revisions = {**plan["init_helper_capability"]["required_source_revisions"], **plan["dsp_policy"]["required_source_revisions"]}
    _require(set(contract["required_source_revisions"]) == {"build/soong", "external/selinux", "system/core", "system/sepolicy"} and
             all(revisions[project] == revision for project, revision in contract["required_source_revisions"].items()) and
             str(plan["board_shipping_api_level"]) == contract["platform"]["board_api"],
             "OEM property source revisions or mapping API differ from the reviewed inputs")
    original = {row["runtime_path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                for row in base["evidence"]["source_rows"]}
    for key in ("factory_system_ext_cil", "factory_system_ext_mapping"):
        row = contract["evidence"][key]
        _require(original.get(row["runtime_path"]) == {field: row[field] for field in ("sha256", "size_bytes")},
                 "OEM property ownership evidence differs from the admitted OEM base")


def _oem_property_admission(contract, identity):
    return {
        "contract_id": OEM_PROPERTY_CONTRACT_ID,
        "contract_record": {"path": OEM_PROPERTY_RECORD.as_posix(), **identity},
        **{key: contract[key] for key in ("base_oem_contract", "factory_package_sha256", "required_source_revisions",
                                        "required_capability_contract", "unchanged_factory_inputs", "existing_vendor_derivation",
                                        "source_files", "types", "read_clauses", "property_contexts", "limits")},
        "wiring": dict(OEM_PROPERTY_WIRING),
        "expected_native_effective_ordinary_allow_edges": contract["native_effective_ordinary_allow_edges"],
        "inherited_denial_logging_effects": contract["finite_impact"]["denial_logging"],
        "evidence_receipts": {key: contract["evidence"][key] for key in OEM_PROPERTY_EVIDENCE},
        "factory_property_contexts": contract["evidence"]["factory_system_ext_property_contexts"],
        "api_mapping": "generated-by-pinned-source-pipeline-at-202504",
        "source_checkout_inspected": False,
        "fresh_soong_or_m4_build_performed": False,
        "native_effective_allow_budget_verified": False,
        "strict_full_policy_compiled": False,
        "complete_context_or_treble_checks_passed": False,
        "image_integration_verified": False,
        "hardware_tested": False,
    }


def _verify_oem_property_sources(contents, contract):
    if __package__:
        from . import oem_policy
    else:
        import oem_policy
    try:
        oem_policy.verify_property_source_contents(contents, contract)
    except oem_policy.OemPolicyError as exc:
        raise CandidateError(f"OEM property sources refused: {exc}") from exc


def _bind_oem_properties(plan, path, workspace_root, template_root, payloads):
    contract, identity = _oem_property_contract(path)
    base = json.loads(payloads[OEM_POLICY_RECORD.as_posix()], object_pairs_hook=_unique_object)
    _oem_property_binding(plan, contract, base)
    dsp = json.loads(payloads[DSP_POLICY_RECORD.as_posix()], object_pairs_hook=_unique_object)["generator_contract"]
    capture = _bound_reference(dsp["policy_capture_receipt"], workspace_root)
    row = contract["evidence"]["factory_system_ext_property_contexts"]
    matches = [item for item in capture["files"] if item["runtime_path"] == row["runtime_path"]]
    _require(len(matches) == 1 and all(matches[0][key] == row[key] for key in ("sha256", "size_bytes")),
             "OEM property contexts differ from the admitted factory capture")
    actual, _ = _read_file(Path(workspace_root) / _relative(matches[0]["path"]), limit=MAX_JSON_BYTES)
    _require(actual == {key: row[key] for key in ("sha256", "size_bytes")}, "OEM factory property contexts changed")
    audit, readback, review = [_bound_reference(contract["evidence"][key], workspace_root) for key in OEM_PROPERTY_EVIDENCE]
    _require(audit["all_inputs_rehashed_unchanged"] is True and audit["assertions"] == contract["finite_impact"]["assertions"] and
             all(audit[key] is False for key in ("native_compiler_invoked", "native_m4_invoked", "source_or_input_files_modified",
                                                 "guest_accessed", "phone_accessed")) and audit["permissive_declarations_in_model"] == 0,
             "OEM property finite audit is not the reviewed enforcing static projection")
    for name, budget in contract["native_effective_ordinary_allow_edges"].items():
        actual = audit["per_property"][name]["effective_all_ordinary_allow_edges_after"]
        _require({key: actual[key] for key in budget} == budget, "OEM property native member budget differs from the finite audit")
    report = contract["evidence"]["finite_impact_audit"]
    _require(readback["report"] == report and readback["all_direct_inputs_unchanged"] is True and
             readback["all_ordinary_delta_group_encodings_and_digests_verified"] is True and
             readback["per_property_full_allow_sets_reproduced_from_global_additions"] is True and
             review["reviewed_report"] == report and review["current_correctness_findings"] == [] and
             all(record[key] is False for record, keys in (
                 (readback, ("guest_accessed", "native_compiler_invoked", "phone_accessed")),
                 (review, ("compiler_executed", "guest_accessed", "phone_accessed", "parent_files_modified", "tracked_files_modified")))
                 for key in keys), "OEM property readback or independent review does not bind the static projection")
    contents = {}
    source_paths = {Path(template_root) / _relative(row["path"]).relative_to(DEVICE_PATH) for row in contract["source_files"]}
    for parent in {source.parent for source in source_paths}:
        _no_symlinks(parent)
        _require(set(parent.iterdir()) == {source for source in source_paths if source.parent == parent},
                 "unreviewed file or directory in an OEM property source directory")
    for row in contract["source_files"]:
        actual, raw = _read_file(Path(template_root) / _relative(row["path"]).relative_to(DEVICE_PATH), limit=MAX_TEXT_BYTES, collect=True)
        _require(actual == {key: row[key] for key in ("sha256", "size_bytes")}, "OEM property source hash/size mismatch")
        contents[row["path"]] = raw
    _verify_oem_property_sources(contents, contract)
    payloads.update(contents)
    actual, raw = _read_file(path, limit=MAX_JSON_BYTES, collect=True)
    _require(actual == identity, "OEM property contract changed before publication")
    payloads[OEM_PROPERTY_RECORD.as_posix()] = raw
    plan["oem_properties"] = _oem_property_admission(contract, identity)


def _oem_property_wiring_lines():
    return ["# Explicit four-property OEM source profile; native and hardware checks remain separate.",
            *(f"{name} += {path}" for name, path in OEM_PROPERTY_WIRING.items())]


def _framework_provider_contract(path):
    if __package__:
        from . import framework_provider_policy as provider_policy
    else:
        import framework_provider_policy as provider_policy
    contract, identity = _read_json(path)
    _require(identity["sha256"] == FRAMEWORK_PROVIDER_CONTRACT_SHA256,
             "unknown or changed framework provider policy contract")
    _require(contract["schema_version"] == 1 and contract["device"] == "nezha" and
             contract["contract_id"] == "nezha-private-framework-aidl-provider-policy-v1" and
             contract["platform"] == {"branch": "bka", "release": "bp4a", "board_api": "202504"} and
             contract["scope"] == provider_policy.SCOPE,
             "framework provider policy platform or scope changed")
    sources = contract["source_files"]
    _require(type(sources) is list and len(sources) == 4 and
             {row["path"] for row in sources} == {(DEVICE_PATH / name).as_posix() for name in FRAMEWORK_PROVIDER_FILES},
             "framework providers require exactly four reviewed private policy sources")
    _require(len(contract["types"]) == 8 and all(row["scope"] == "system_ext_private" and
             row["versioned_attribute"] is None for row in contract["types"].values()),
             "framework provider types must remain private without public mappings")
    for row in sources:
        _require(row["kind"] == ("source" if row["path"].endswith(".te") else "contexts"),
                 "framework provider policy source kind changed")
        _digest(row["sha256"], "framework provider source")
        _integer(row["size_bytes"], "framework provider source length", MAX_TEXT_BYTES)
    return contract, identity


def _framework_provider_input_contract(path):
    if __package__:
        from . import framework_provider_inputs as provider_inputs
    else:
        import framework_provider_inputs as provider_inputs
    contract, identity = _read_json(path)
    _require(identity["sha256"] == FRAMEWORK_PROVIDER_INPUT_SHA256,
             "unknown or changed framework provider input contract")
    _require(contract["schema_version"] == 1 and contract["device"] == "nezha" and
             contract["platform"] == {"branch": "bka", "release": "bp4a", "board_api": "202504"} and
             contract["bundle"] == FRAMEWORK_PROVIDER_INPUTS_PATH and
             contract["module_package"] == FRAMEWORK_PROVIDER_MODULE_PACKAGE and
             contract["scope"] == provider_inputs.SCOPE and
             contract["native_output_recipe"] == provider_inputs.NATIVE_OUTPUT_RECIPE,
             "framework provider input namespace, verified producer or scope changed")
    return contract, identity


def _framework_provider_blueprint(contract):
    if __package__:
        from . import framework_provider_inputs as provider_inputs
    else:
        import framework_provider_inputs as provider_inputs
    return provider_inputs._module_bp(contract)


def _framework_provider_product(contract):
    if __package__:
        from . import framework_provider_inputs as provider_inputs
    else:
        import framework_provider_inputs as provider_inputs
    # This renderer's product selection does not use the private capture data.
    return provider_inputs._generated(contract, b"", {})["framework-providers.mk"]


def _framework_provider_native_controls(contract, native_files):
    if __package__:
        from . import framework_provider_inputs as provider_inputs
    else:
        import framework_provider_inputs as provider_inputs
    return {
        "Android.bp": provider_inputs._bp(contract, native_files),
        "tools/verify_framework_provider_inputs.py": provider_inputs._native_checker(
            dict(sorted(native_files.items())), provider_inputs._native_outputs(contract)),
    }


def _framework_provider_receipt_identity(verification):
    if __package__:
        from . import framework_provider_inputs as provider_inputs
    else:
        import framework_provider_inputs as provider_inputs
    raw = provider_inputs.encoded({key: value for key, value in verification.items() if key not in ("status", "receipt")})
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _verify_framework_provider_bundle(receipt, contract_path):
    if __package__:
        from . import framework_provider_inputs as provider_inputs
    else:
        import framework_provider_inputs as provider_inputs
    try:
        return provider_inputs.verify_bundle(receipt.parent, contract_path=contract_path)
    except provider_inputs.FrameworkProviderError as exc:
        raise CandidateError(f"framework provider inputs refused: {exc}") from exc


def _framework_provider_external_inventory(receipt, verification):
    root = _no_symlinks(receipt.parent)
    expected = {row["path"] for row in verification["files"]} | {FRAMEWORK_PROVIDER_INPUTS_RECEIPT}
    directories = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents if parent.as_posix() != "."}
    seen = set()
    for directory, subdirectories, filenames in os.walk(root, followlinks=False):
        for name in subdirectories:
            path = Path(directory) / name
            _require(stat.S_ISDIR(path.lstat().st_mode) and path.relative_to(root).as_posix() in directories,
                     "unexpected directory or symlink in framework provider bundle")
        for name in filenames:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            _require(stat.S_ISREG(path.lstat().st_mode) and relative in expected,
                     "unexpected file or symlink in framework provider bundle")
            seen.add(relative)
    _require(seen == expected, "framework provider bundle has missing files")


def _framework_provider_binding(plan, contract, input_contract, input_identity, verification):
    _require(all(key in plan for key in ("oem_policy", "init_helper_capability", "dsp_policy", "factory_profile")),
             "framework providers require the explicit OEM, helper, DSP and factory capabilities")
    expected_contracts = {
        "oem_policy": {key: plan["oem_policy"]["contract_record"][key] for key in ("path", "sha256")},
        "init_helper": {key: plan["init_helper_capability"]["contract_record"][key] for key in ("path", "sha256")},
        "provider_inputs": {"path": FRAMEWORK_PROVIDER_INPUT_RECORD.as_posix(), "sha256": input_identity["sha256"]},
    }
    _require(contract["required_contracts"] == expected_contracts and
             contract["factory_package_sha256"] == input_contract["factory_package_sha256"] == plan["source_packages"]["vendor"] and
             contract["platform"] == input_contract["platform"] and
             str(plan["board_shipping_api_level"]) == contract["platform"]["board_api"],
             "framework provider source, helper, OEM and factory bindings differ")
    project = contract["pinned_android_source_project"]
    _require(project["path"] == "system/sepolicy" and
             project["head"] == plan["oem_policy"]["required_source_revisions"]["system/sepolicy"],
             "framework provider policy source revision differs")
    selected = {row["runtime_path"].removeprefix("/system_ext"): {key: row[key] for key in ("sha256", "size_bytes")}
                for row in input_contract["files"] if row["kind"] in ("binary", "init_rc", "vintf_fragment")}
    _require(len(contract["selected_provider_artifacts"]) == 6 and selected == {
        row["path"]: {key: row[key] for key in ("sha256", "size_bytes")} for row in contract["selected_provider_artifacts"]},
        "framework provider policy does not describe the selected executables, init rules and VINTF fragments")
    packages = [row["module"] for row in input_contract["files"] if "module" in row]
    expected_fields = {
        "schema_version": 1, "operation": "stage-framework-provider-inputs", "status": "verified",
        "device": "nezha", "bundle": FRAMEWORK_PROVIDER_INPUTS_PATH,
        "module_package": FRAMEWORK_PROVIDER_MODULE_PACKAGE, "contract": input_identity,
        "factory_package_sha256": input_contract["factory_package_sha256"],
        "factory_image": input_contract["factory_image"], "source_lock": input_contract["source_lock"],
        "native_check_target": "nezha_framework_provider_inputs_check",
        "native_output_recipe": input_contract["native_output_recipe"], "packages": packages,
        "providers": input_contract["providers"], "scope": input_contract["scope"], "readback_verified": True,
    }
    _require(type(verification) is dict and set(verification) == set(expected_fields) | {"files", "receipt", "module_blueprint"} and
             all(verification.get(key) == value for key, value in expected_fields.items()),
             "framework provider bundle differs from its reviewed source admission")
    _require(verification["readback_verified"] is True, "framework provider readback was not verified")
    blueprint = _framework_provider_blueprint(input_contract)
    _require(verification["module_blueprint"] == {
        "path": "framework-providers.Android.bp", "sha256": hashlib.sha256(blueprint).hexdigest(), "size_bytes": len(blueprint)},
        "framework provider Blueprint differs from the strict verified-output renderer")
    receipt = verification["receipt"]
    _require(set(receipt) == {"path", "sha256", "size_bytes"} and receipt["path"] == FRAMEWORK_PROVIDER_INPUTS_RECEIPT,
             "unexpected framework provider receipt")
    _digest(receipt["sha256"], "framework provider receipt")
    _integer(receipt["size_bytes"], "framework provider receipt length", MAX_JSON_BYTES)
    known_files = {"proprietary" + row["runtime_path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                   for row in input_contract["files"]}
    known_files.update({"provenance/captures/" + name + ".json": {key: row[key] for key in ("sha256", "size_bytes")}
                        for name, row in input_contract["captures"].items()})
    known_files["provenance/nezha-framework-providers.json"] = input_identity
    known_files["framework-providers.Android.bp"] = {key: verification["module_blueprint"][key] for key in ("sha256", "size_bytes")}
    controls = _framework_provider_native_controls(input_contract, known_files)
    known_files.update({name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                        for name, raw in controls.items()})
    product = _framework_provider_product(input_contract)
    known_files["framework-providers.mk"] = {"sha256": hashlib.sha256(product).hexdigest(), "size_bytes": len(product)}
    files = verification["files"]
    _require(type(files) is list and len(files) == len(known_files),
             "framework provider bundle file inventory changed")
    identities = {}
    for row in files:
        name = _relative(row["path"]).as_posix()
        _require(set(row) == {"path", "sha256", "size_bytes"} and name not in identities,
                 "duplicate or malformed framework provider input")
        _digest(row["sha256"], "framework provider input")
        _integer(row["size_bytes"], "framework provider input length", MAX_FILE_BYTES)
        identities[name] = {key: row[key] for key in ("sha256", "size_bytes")}
    _require(set(identities) == set(known_files) and
             all(identities[name] == value for name, value in known_files.items()),
             "framework provider input inventory differs from the reviewed files")
    _require({key: receipt[key] for key in ("sha256", "size_bytes")} == _framework_provider_receipt_identity(verification),
             "framework provider receipt identity differs from its exact canonical manifest")


def _framework_provider_admission(contract, identity, input_contract, input_identity, verification):
    return {
        "contract_id": contract["contract_id"],
        "contract_record": {"path": FRAMEWORK_PROVIDER_RECORD.as_posix(), **identity},
        "inputs_contract_record": {"path": FRAMEWORK_PROVIDER_INPUT_RECORD.as_posix(), **input_identity},
        "inputs": verification, "source_files": contract["source_files"], "types": contract["types"],
        "wiring": dict(FRAMEWORK_PROVIDER_WIRING),
        "module_blueprint": {**verification["module_blueprint"], "path": FRAMEWORK_PROVIDER_BLUEPRINT},
        "required_source_patches": input_contract["required_source_patches"], "source_lock": input_contract["source_lock"],
        "required_contracts": contract["required_contracts"], "pinned_android_source_project": contract["pinned_android_source_project"],
        "pinned_android_sources": contract["pinned_android_sources"],
        "source_checkout_inspected": False, "source_patches_applied": False,
        "fresh_soong_or_m4_build_performed": False, "strict_native_elf_checks_passed": False,
        "strict_full_policy_compiled": False, "complete_context_or_treble_checks_passed": False,
        "image_integration_verified": False, "hardware_tested": False,
    }


def _verify_framework_provider_sources(contents, contract):
    if __package__:
        from . import framework_provider_policy as provider_policy
    else:
        import framework_provider_policy as provider_policy
    try:
        provider_policy.verify_source_contents(contents, contract)
    except provider_policy.FrameworkProviderPolicyError as exc:
        raise CandidateError(f"framework provider sources refused: {exc}") from exc


def _bind_framework_providers(plan, path, receipt, workspace_root, template_root, patch_source_root, payloads):
    contract, identity = _framework_provider_contract(path)
    input_path = Path(workspace_root) / FRAMEWORK_PROVIDER_INPUT_RECORD
    input_contract, input_identity = _framework_provider_input_contract(input_path)
    receipt = _no_symlinks(receipt)
    _require(receipt.name == FRAMEWORK_PROVIDER_INPUTS_RECEIPT, "framework provider receipt must use its reviewed name")
    receipt_identity, _ = _read_file(receipt, limit=MAX_JSON_BYTES)
    verification = _verify_framework_provider_bundle(receipt, input_path)
    _framework_provider_binding(plan, contract, input_contract, input_identity, verification)
    _framework_provider_external_inventory(receipt, verification)
    _require(receipt_identity == {key: verification["receipt"][key] for key in ("sha256", "size_bytes")},
             "framework provider receipt changed during verification")
    paths = {Path(template_root) / _relative(row["path"]).relative_to(DEVICE_PATH) for row in contract["source_files"]}
    for directory in {source.parent for source in paths}:
        _no_symlinks(directory)
        _require(set(directory.iterdir()) == {source for source in paths if source.parent == directory},
                 "unreviewed file or directory in framework provider policy sources")
    contents = {row["path"]: _read_file(Path(template_root) / _relative(row["path"]).relative_to(DEVICE_PATH),
                                      limit=MAX_TEXT_BYTES, collect=True)[1] for row in contract["source_files"]}
    _verify_framework_provider_sources(contents, contract)
    payloads.update(contents)
    blueprint_identity, blueprint = _read_file(receipt.parent / "framework-providers.Android.bp", limit=MAX_TEXT_BYTES, collect=True)
    _require(blueprint_identity == {key: verification["module_blueprint"][key] for key in ("sha256", "size_bytes")} and
             blueprint == _framework_provider_blueprint(input_contract), "framework provider Blueprint changed after verification")
    payloads[FRAMEWORK_PROVIDER_BLUEPRINT] = blueprint
    for row, root in [(input_contract["source_lock"], workspace_root),
                      *((row, patch_source_root) for row in input_contract["required_source_patches"])]:
        actual, raw = _read_file(Path(root) / _relative(row["path"]), limit=MAX_TEXT_BYTES, collect=True)
        _require(actual == {key: row[key] for key in ("sha256", "size_bytes")},
                 "framework provider source lock or required patch changed")
        payloads[row["path"]] = raw
    for source, destination, expected in ((path, FRAMEWORK_PROVIDER_RECORD, identity),
                                          (input_path, FRAMEWORK_PROVIDER_INPUT_RECORD, input_identity)):
        actual, raw = _read_file(source, limit=MAX_JSON_BYTES, collect=True)
        _require(actual == expected, "framework provider contract changed before publication")
        payloads[destination.as_posix()] = raw
    plan["framework_providers"] = _framework_provider_admission(contract, identity, input_contract, input_identity, verification)


def _framework_provider_wiring_lines():
    return ["# Explicit enforcing framework-provider source profile; runtime support remains unverified.",
            *(f"{name} += {path}" for name, path in FRAMEWORK_PROVIDER_WIRING.items())]


def _verify_policy_input_bundle(receipt, *, framework_provider_inputs_receipt=None):
    if __package__:
        from . import policy_inputs
    else:
        import policy_inputs
    if framework_provider_inputs_receipt is None:
        return policy_inputs.verify_bundle(receipt.parent)
    return policy_inputs.verify_bundle(receipt.parent, framework_provider_inputs_receipt=framework_provider_inputs_receipt)


def _policy_inputs_binding(plan, verification):
    if __package__:
        from . import policy_inputs
    else:
        import policy_inputs
    _require("init_helper_capability" in plan and "dsp_policy" in plan,
             "native policy inputs require the explicit helper and DSP capabilities")
    _require(isinstance(verification, dict) and verification.get("schema_version") == 1 and
             verification.get("operation") == "verify-nezha-policy-inputs" and
             verification.get("status") == "verified" and verification.get("device") == "nezha" and
             verification.get("bundle") == POLICY_INPUTS_PATH and
             verification.get("factory_package_sha256") == plan["source_packages"]["vendor"] and
             verification.get("scope") == policy_inputs.SCOPE,
             "native policy bundle binding differs from the reviewed component scope")
    expected_oem = plan.get("oem_policy", {}).get("contract_record")
    _require(verification.get("oem_policy_contract") == expected_oem,
             "native policy bundle and OEM source capability must use the same reviewed contract")
    _require(verification.get("oem_property_contract") == plan.get("oem_properties", {}).get("contract_record"),
             "native policy bundle and OEM property source capability must use the same reviewed contract")
    providers = plan.get("framework_providers", {})
    _require(verification.get("framework_provider_policy_contract") == providers.get("contract_record") and
             verification.get("framework_provider_inputs") == providers.get("inputs"),
             "framework provider inputs require the same separately supported source capability and complete bundle")
    receipt = verification["receipt"]
    _require(receipt["path"] == POLICY_INPUTS_RECEIPT, "unexpected native policy receipt name")
    _digest(receipt["sha256"], "native policy receipt")
    _integer(receipt["size_bytes"], "native policy receipt length", MAX_JSON_BYTES)
    entries = verification["files"]
    _require(isinstance(entries, list) and 0 < len(entries) <= MAX_BUNDLE_FILES,
             "invalid native policy file inventory")
    names = set()
    for row in entries:
        name = _relative(row["path"]).as_posix()
        _require(name.casefold() not in names and name != POLICY_INPUTS_RECEIPT,
                 "duplicate native policy file inventory entry")
        names.add(name.casefold())
        _digest(row["sha256"], "native policy file")
        _require(type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= MAX_JSON_BYTES,
                 "invalid native policy file length")
    _require("android.bp" in names, "native policy namespace has no reviewed Android.bp")


def _bind_policy_inputs(plan, path, *, framework_provider_inputs_receipt=None):
    path = _no_symlinks(path)
    _require(path.name == POLICY_INPUTS_RECEIPT, "native policy receipt must be named policy-inputs.json")
    identity, _ = _read_file(path, limit=MAX_JSON_BYTES)
    verification = (_verify_policy_input_bundle(path) if framework_provider_inputs_receipt is None else
                    _verify_policy_input_bundle(path, framework_provider_inputs_receipt=framework_provider_inputs_receipt))
    _policy_inputs_binding(plan, verification)
    _require(identity == {key: verification["receipt"][key] for key in ("sha256", "size_bytes")},
             "native policy input receipt changed during verification")
    # This records completed generation-time verification of an external bundle.
    # Candidate validation cannot rehash an unmounted private bundle or build it.
    plan["policy_inputs"] = verification


def _verify_mi_ext_inputs(path, *, expected_package_sha256):
    if __package__:
        from . import mi_ext_inputs
    else:
        import mi_ext_inputs
    try:
        return mi_ext_inputs.validate_admission(path, expected_package_sha256=expected_package_sha256)
    except mi_ext_inputs.MiExtInputsError as exc:
        raise CandidateError(f"mi_ext inputs refused: {exc}") from exc


def _render_mi_ext_include(binding):
    if __package__:
        from . import mi_ext_inputs
    else:
        import mi_ext_inputs
    try:
        return mi_ext_inputs.render_board_include(binding)
    except mi_ext_inputs.MiExtInputsError as exc:
        raise CandidateError(f"mi_ext native source binding refused: {exc}") from exc


def _mi_ext_binding(plan, binding):
    """Bind the external factory prebuilt to this candidate's selected layout."""
    _require(type(binding) is dict and set(binding) == {
        "bundle", "factory_package_sha256", "image", "receipt", "native_source", "dynamic_layout", "scope",
    }, "invalid mi_ext input binding")
    _require(binding["bundle"] == MI_EXT_INPUTS_PATH and "factory_profile" in plan and
             binding["factory_package_sha256"] == plan["source_packages"]["vendor"] ==
             plan["factory_profile"]["package_sha256"],
             "mi_ext requires the same explicitly admitted factory vendor package")
    layout = binding["dynamic_layout"]
    _require(type(layout) is dict and
             layout["logical_partition_names"] == [*FRAMEWORK_PARTITIONS, "mi_ext"] and
             set(plan["logical_filesystems"]) == set(layout["logical_partition_names"]) and
             plan["super"]["bytes"] == layout["super_size_bytes"] and
             plan["super"]["group_bytes"] == layout["group_maximum_bytes"] and
             plan["super"]["group_name"] == layout["group_name"] and
             plan["logical_filesystems"]["mi_ext"] == "erofs" and
             plan["avb_descriptor_owners"]["mi_ext"] == layout["fstab_avb_owner"] == "vbmeta" and
             "mi_ext" not in plan["avb_chains"],
             "mi_ext differs from the reviewed dynamic layout or direct root-vbmeta ownership")
    fstab = plan["fstab"]
    _require(fstab.get("source") == "factory vendor ramdisk" and
             fstab.get("factory_logical_flags_preserved") is True and
             fstab.get("logical_avb_enabled") is True and
             fstab.get("stock_overlay_mounts_adopted") is False and
             fstab.get("vendor_image_replacement_applied") is False and
             fstab["logical_mounts"].count("mi_ext") == 1,
             "mi_ext requires the preserved factory logical mount without framework overlays")
    _require(plan["profile"] == "framework-checks" and plan["release_config"] == "bp4a" and
             plan["admission"]["configuration_allowed"] is True and
             all(value is False for key, value in plan["admission"].items() if key != "configuration_allowed"),
             "mi_ext input binding cannot promote build, packaging or hardware readiness")
    # The renderer checks the exact current source, image, receipt and scope
    # contracts. This cannot rehash an unmounted private bundle or guest source.
    return _render_mi_ext_include(binding)


def _logical_partition_selection(plan):
    expected = [*FRAMEWORK_PARTITIONS, *(["mi_ext"] if "mi_ext_inputs" in plan else [])]
    _require(plan["packaged_logical_partitions"] == expected and
             plan["required_unpacked_partitions"] == sorted(set(plan["logical_filesystems"]) - set(expected)),
             "logical partition selection requires the matching explicit input capability")
    return expected


def _validate_mi_ext_fstab(binding, text):
    rows = [line.split("#", 1)[0].split() for line in text.splitlines()]
    rows = [row for row in rows if row]
    mount = binding["dynamic_layout"]["first_stage_mount_point"]
    matches = [row for row in rows if row[0] == "mi_ext" or len(row) > 1 and row[1] == mount]
    _require(len(matches) == 1 and len(matches[0]) == 5,
             "mi_ext requires exactly one selected factory mount")
    row = matches[0]
    # The selected factory row retains nofail as well as every verified-boot
    # flag. Additional key paths or alternate sources are separate integrations.
    _require(row == ["mi_ext", mount, "erofs", "ro",
                     "wait,slotselect,avb=vbmeta,logical,first_stage_mount,nofail"] and
             all(len(fields) == 5 and fields[2] != "overlay" and
                 not {"bind", "rbind"}.intersection(fields[3].split(",")) for fields in rows),
             "mi_ext mount, AVB flags or framework-overlay exclusion changed")


def _bind_mi_ext_inputs(plan, records, path, payloads, fstab):
    path = _no_symlinks(path)
    _require(path.name == MI_EXT_INPUTS_RECEIPT, "mi_ext receipt must be named mi-ext-inputs.json")
    identity, _ = _read_file(path, limit=MAX_JSON_BYTES)
    binding = _verify_mi_ext_inputs(path, expected_package_sha256=plan["source_packages"]["vendor"])
    include = _mi_ext_binding(plan, binding)
    _require(identity == {key: binding["receipt"][key] for key in ("sha256", "size_bytes")},
             "mi_ext input receipt changed during verification")
    rows = records["firmware-layout"]["partitions"]
    a = [row for row in rows if row["name"] == "mi_ext_a"]
    b = [row for row in rows if row["name"] == "mi_ext_b"]
    _require(len(a) == len(b) == 1 and
             a[0]["size_bytes"] == binding["image"]["size_bytes"] and
             a[0]["extraction"]["sha256"] == binding["image"]["sha256"] and
             a[0]["extraction"].get("readback_verified") is True and
             a[0]["filesystem"]["format"].lower() == "erofs" and
             type(b[0]["size_bytes"]) is int and
             b[0]["size_bytes"] == binding["dynamic_layout"]["source_b_slot_size_bytes"] == 0 and
             b[0]["extents"] == [],
             "mi_ext input is not the selected factory logical image and empty B slot")
    _validate_mi_ext_fstab(binding, fstab)
    plan["mi_ext_inputs"] = binding
    plan["packaged_logical_partitions"] = [*FRAMEWORK_PARTITIONS, "mi_ext"]
    plan["required_unpacked_partitions"] = sorted(set(plan["logical_filesystems"]) - set(plan["packaged_logical_partitions"]))
    plan["limitations"] = [
        "The factory mi_ext input is selected; native packaging, the complete AVB chain and hardware remain unverified."
        if note == "Required unpackaged logical mounts are retained and block complete packaging." else note
        for note in plan["limitations"]
    ]
    payloads[MI_EXT_BOARD_INCLUDE.as_posix()] = include.encode("ascii")


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
    partitions = _logical_partition_selection(plan)
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
    for name in ("kernel", "ramdisk", "tags", "dtb"):
        value = header["load_addresses"][name]
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
    for name in ("boot", "init_boot", "vendor_boot", "recovery", "dtbo"):
        budget = plan["image_budgets"][name]
        lines.append(f"BOARD_{variable[name]}_PARTITION_SIZE := {budget['bytes']}")
    group = plan["super"]["group_name"]
    lines += [f"BOARD_SUPER_PARTITION_SIZE := {plan['super']['bytes']}",
              f"BOARD_SUPER_PARTITION_GROUPS := {group}",
              f"BOARD_{group.upper()}_SIZE := {plan['super']['group_bytes']}",
              f"BOARD_{group.upper()}_PARTITION_LIST := {' '.join(partitions)}"]
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
    for name in ("boot", "recovery", "vbmeta_system"):
        chain = plan["avb_chains"][name]
        upper = name.upper()
        lines += [f"BOARD_AVB_{upper}_KEY_PATH := $(NEZHA_ENGINEERING_AVB_KEY)",
                  f"BOARD_AVB_{upper}_ALGORITHM := SHA256_RSA4096",
                  f"BOARD_AVB_{upper}_ROLLBACK_INDEX := {chain['rollback_index']}",
                  f"BOARD_AVB_{upper}_ROLLBACK_INDEX_LOCATION := {chain['location']}"]
    chained = [name for name in FRAMEWORK_PARTITIONS if plan["avb_descriptor_owners"][name] == "vbmeta_system"]
    lines.append("BOARD_AVB_VBMETA_SYSTEM := " + " ".join(chained))
    for key, value in sorted(plan["bootconfig"].items()):
        lines.append(f"BOARD_BOOTCONFIG += {key}={value}")
    if "mi_ext_inputs" in plan:
        lines += ["# Exact factory mi_ext custom image; the native consumer rechecks source and image bytes.",
                  "include $(NEZHA_DEVICE_PATH)/generated/mi-ext-prebuilt.mk"]
    if "init_helper_capability" in plan:
        lines.extend(_init_helper_wiring_lines())
    if "oem_policy" in plan:
        lines.extend(_oem_policy_wiring_lines())
    if "oem_properties" in plan:
        lines.extend(_oem_property_wiring_lines())
    if "framework_providers" in plan:
        lines.extend(_framework_provider_wiring_lines())
    if "dsp_policy" in plan:
        lines.extend(_dsp_wiring_lines())
    return "\n".join(lines) + "\n"


def _render_product(plan):
    partitions = ["boot", "dtbo", "init_boot", "recovery", "vendor_boot", "vbmeta", "vbmeta_system",
                  *_logical_partition_selection(plan)]
    lines = [
        "# Generated framework-checks configuration. Complete packaging is not admitted.",
        f"PRODUCT_SHIPPING_API_LEVEL := {plan['shipping_api_level']}",
        "PRODUCT_USE_DYNAMIC_PARTITIONS := true", "PRODUCT_USE_DYNAMIC_PARTITION_SIZE := true",
        "PRODUCT_BUILD_SUPER_PARTITION := true", "AB_OTA_UPDATER := true",
        "AB_OTA_PARTITIONS += " + " ".join(partitions),
        "PRODUCT_BUILD_BOOT_IMAGE := true", "PRODUCT_BUILD_INIT_BOOT_IMAGE := true",
        "PRODUCT_BUILD_VENDOR_BOOT_IMAGE := true", "PRODUCT_BUILD_RECOVERY_IMAGE := true",
        "PRODUCT_ENFORCE_VINTF_MANIFEST := true",
    ]
    if "policy_inputs" in plan:
        lines += ["# Explicit private policy bundle; native component checks only.",
                  f"PRODUCT_SOONG_NAMESPACES += {POLICY_INPUTS_PATH}"]
    if "framework_providers" in plan:
        lines += ["# Exact verified provider bundle owns its two namespaces and native package list.",
                  f"$(call inherit-product, {FRAMEWORK_PROVIDER_INPUTS_PATH}/framework-providers.mk)"]
    return "\n".join([*lines, ""])


def _load_records(record_paths):
    records, identities = {}, {}
    for name in RECORD_NAMES:
        records[name], identities[name] = _read_json(record_paths[name])
    return records, identities


def generate(output, *, record_paths, kernel_receipt, vendor_receipt, fstab_source=None,
             variant="userdebug", workspace_root=ROOT, template_root=ROOT / DEVICE_PATH,
             patch_source_root=ROOT, factory_boot_contract=None, partition_metadata=None,
             dsp_policy_contract=None, init_helper_capability_contract=None,
             policy_inputs_receipt=None, oem_policy_contract=None, mi_ext_inputs_receipt=None,
             oem_property_contract=None, framework_provider_policy_contract=None,
             framework_provider_inputs_receipt=None):
    variant = _build_variant(variant)
    factory_selected = factory_boot_contract is not None or partition_metadata is not None
    if factory_selected:
        _require(factory_boot_contract is not None and partition_metadata is not None and fstab_source is not None,
                 "factory generation requires boot contract, partition metadata and explicit fstab source")
    if dsp_policy_contract is not None:
        _require(factory_selected, "DSP policy integration requires the explicit factory profile")
    if init_helper_capability_contract is not None:
        _require(factory_selected and dsp_policy_contract is not None,
                 "init-helper capability requires the explicit factory and DSP profile")
    if policy_inputs_receipt is not None:
        _require(init_helper_capability_contract is not None and dsp_policy_contract is not None,
                 "native policy inputs require the explicit helper and DSP capabilities")
    if oem_policy_contract is not None:
        _require(policy_inputs_receipt is not None and init_helper_capability_contract is not None and
                 dsp_policy_contract is not None,
                 "OEM policy requires explicit factory, DSP, helper and native policy inputs")
    if mi_ext_inputs_receipt is not None:
        _require(factory_selected, "mi_ext inputs require the explicit factory profile")
    if oem_property_contract is not None:
        _require(oem_policy_contract is not None and policy_inputs_receipt is not None,
                 "OEM properties require an explicit OEM source contract and matching native policy inputs")
    providers_selected = framework_provider_policy_contract is not None or framework_provider_inputs_receipt is not None
    if providers_selected:
        _require(framework_provider_policy_contract is not None and framework_provider_inputs_receipt is not None and
                 oem_policy_contract is not None and policy_inputs_receipt is not None,
                 "framework providers require explicit paired provider source and input receipts, OEM sources and native policy inputs")
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
    if dsp_policy_contract is not None:
        _bind_dsp_policy(plan, records, dsp_policy_contract, workspace_root, template_root, payloads)
    if init_helper_capability_contract is not None:
        _bind_init_helper_capability(plan, records, init_helper_capability_contract,
                                    workspace_root, patch_source_root, vendor_receipt, payloads)
    if oem_policy_contract is not None:
        _bind_oem_policy(plan, oem_policy_contract, workspace_root, template_root, payloads)
    if oem_property_contract is not None:
        _bind_oem_properties(plan, oem_property_contract, workspace_root, template_root, payloads)
    if providers_selected:
        _bind_framework_providers(plan, framework_provider_policy_contract, framework_provider_inputs_receipt,
                                  workspace_root, template_root, patch_source_root, payloads)
    if policy_inputs_receipt is not None:
        _bind_policy_inputs(plan, policy_inputs_receipt, framework_provider_inputs_receipt=framework_provider_inputs_receipt)
    if mi_ext_inputs_receipt is not None:
        _bind_mi_ext_inputs(plan, records, mi_ext_inputs_receipt, payloads, fstab)
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
    if providers_selected:
        for receipt in (framework_provider_inputs_receipt, policy_inputs_receipt):
            protected = _no_symlinks(Path(receipt).parent)
            _require(not output.is_relative_to(protected) and not any(
                parent.exists() and parent.samefile(protected) for parent in output.parents),
                "candidate output must not be nested inside a provider or policy input bundle")
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
        if providers_selected:
            # The policy verifier also reopens this external bundle. Check it again
            # after candidate validation so late file/directory additions cannot
            # be hidden by a portable receipt or the earlier source-file readback.
            _require(_verify_framework_provider_bundle(_no_symlinks(framework_provider_inputs_receipt),
                     Path(workspace_root) / FRAMEWORK_PROVIDER_INPUT_RECORD) == plan["framework_providers"]["inputs"],
                     "framework provider bundle changed before candidate publication")
            _framework_provider_external_inventory(Path(framework_provider_inputs_receipt), plan["framework_providers"]["inputs"])
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
    _logical_partition_selection(plan)
    files = _file_entries(Path(output), plan["files"])
    expected = {(DEVICE_PATH / name).as_posix() for name in TEMPLATE_FILES}
    expected |= {(DEVICE_PATH / "generated" / name).as_posix()
                 for name in ("BoardConfigCandidate.mk", "device-candidate.mk", "fstab.qcom")}
    expected |= {SECURITY_PATCH.as_posix(), SECURITY_RECORD.as_posix()}
    if "mi_ext_inputs" in plan:
        mi_ext_include = _mi_ext_binding(plan, plan["mi_ext_inputs"])
        expected.add(MI_EXT_BOARD_INCLUDE.as_posix())
        identity, raw = _read_file(Path(output) / MI_EXT_BOARD_INCLUDE, limit=MAX_TEXT_BYTES, collect=True)
        _require(identity == files.get(MI_EXT_BOARD_INCLUDE.as_posix()) and raw == mi_ext_include.encode("ascii"),
                 "generated mi_ext native input guard differs from its reviewed binding")
        _, raw = _read_file(Path(output) / DEVICE_PATH / "generated/fstab.qcom", limit=MAX_TEXT_BYTES, collect=True)
        _validate_mi_ext_fstab(plan["mi_ext_inputs"], raw.decode("utf-8"))
    if "dsp_policy" in plan:
        _require(isinstance(plan["dsp_policy"], dict), "invalid DSP policy admission")
        contract, identity = _dsp_contract(Path(output) / DSP_POLICY_RECORD)
        _require(plan["dsp_policy"] == _dsp_admission(contract, identity),
                 "DSP policy admission differs from the reviewed source contract")
        _dsp_factory_binding(plan, contract)
        expected |= {(DEVICE_PATH / name).as_posix() for name in DSP_POLICY_FILES}
        expected.add(DSP_POLICY_RECORD.as_posix())
        for entry in contract["source_files"]:
            _require(files.get(entry["path"]) == {key: entry[key] for key in ("sha256", "size_bytes")},
                     "DSP policy source file differs from the reviewed contract")
    if "init_helper_capability" in plan:
        contract, identity = _init_helper_contract(Path(output) / INIT_HELPER_RECORD)
        _require(plan["init_helper_capability"] == _init_helper_admission(contract, identity),
                 "init-helper admission differs from the reviewed capability contract")
        _init_helper_factory_binding(plan, contract)
        expected |= {INIT_HELPER_RECORD.as_posix(), INIT_HELPER_PATCH.as_posix(),
                     INIT_HELPER_METADATA.as_posix(), INIT_HELPER_AUDIT.as_posix()}
        for row in [*contract["device_guards"], contract["source_patch"], contract["patch_metadata"],
                    contract["prior_component_audit"]]:
            _require(files.get(row["path"]) == {key: row[key] for key in ("sha256", "size_bytes")},
                     "init-helper public input differs from the reviewed contract")
    if "oem_policy" in plan:
        oem_contract, oem_identity = _oem_policy_contract(Path(output) / OEM_POLICY_RECORD)
        _require(plan["oem_policy"] == _oem_policy_admission(oem_contract, oem_identity),
                 "OEM policy admission differs from the reviewed source contract")
        oem_dsp, _ = _dsp_contract(Path(output) / DSP_POLICY_RECORD)
        _oem_policy_binding(plan, oem_contract, oem_dsp)
        _require("policy_inputs" in plan, "OEM policy requires its verified native input bundle")
        expected.add(OEM_POLICY_RECORD.as_posix())
        for row in oem_contract["source_files"]:
            expected.add(row["path"])
            _require(files.get(row["path"]) == {key: row[key] for key in ("sha256", "size_bytes")},
                     "OEM policy source file differs from the reviewed contract")
    if "oem_properties" in plan:
        property_contract, property_identity = _oem_property_contract(Path(output) / OEM_PROPERTY_RECORD)
        _require(plan["oem_properties"] == _oem_property_admission(property_contract, property_identity),
                 "OEM property admission differs from the reviewed source contract")
        property_base, _ = _oem_policy_contract(Path(output) / OEM_POLICY_RECORD)
        _oem_property_binding(plan, property_contract, property_base)
        _require("policy_inputs" in plan, "OEM properties require their verified native policy input bundle")
        expected.add(OEM_PROPERTY_RECORD.as_posix())
        property_contents = {}
        for row in property_contract["source_files"]:
            expected.add(row["path"])
            _require(files.get(row["path"]) == {key: row[key] for key in ("sha256", "size_bytes")},
                     "OEM property source file differs from the reviewed contract")
            _, property_contents[row["path"]] = _read_file(Path(output) / row["path"], limit=MAX_TEXT_BYTES, collect=True)
        _verify_oem_property_sources(property_contents, property_contract)
    if "framework_providers" in plan:
        provider_contract, provider_identity = _framework_provider_contract(Path(output) / FRAMEWORK_PROVIDER_RECORD)
        provider_inputs, provider_input_identity = _framework_provider_input_contract(Path(output) / FRAMEWORK_PROVIDER_INPUT_RECORD)
        providers = plan["framework_providers"]
        _framework_provider_binding(plan, provider_contract, provider_inputs, provider_input_identity, providers["inputs"])
        _require(providers == _framework_provider_admission(provider_contract, provider_identity, provider_inputs,
                                                          provider_input_identity, providers["inputs"]),
                 "framework provider admission differs from its reviewed source contract")
        _require("policy_inputs" in plan, "framework providers require their verified native policy input bundle")
        expected |= {FRAMEWORK_PROVIDER_RECORD.as_posix(), FRAMEWORK_PROVIDER_INPUT_RECORD.as_posix(),
                     FRAMEWORK_PROVIDER_BLUEPRINT}
        provider_contents = {}
        for row in provider_contract["source_files"]:
            expected.add(row["path"])
            _require(files.get(row["path"]) == {key: row[key] for key in ("sha256", "size_bytes")},
                     "framework provider policy source differs from its reviewed contract")
            _, provider_contents[row["path"]] = _read_file(Path(output) / row["path"], limit=MAX_TEXT_BYTES, collect=True)
        _verify_framework_provider_sources(provider_contents, provider_contract)
        for row in [provider_inputs["source_lock"], *provider_inputs["required_source_patches"]]:
            expected.add(row["path"])
            _require(files.get(row["path"]) == {key: row[key] for key in ("sha256", "size_bytes")},
                     "framework provider source lock or required patch changed")
        _, blueprint = _read_file(Path(output) / FRAMEWORK_PROVIDER_BLUEPRINT, limit=MAX_TEXT_BYTES, collect=True)
        _require(blueprint == _framework_provider_blueprint(provider_inputs), "generated framework provider Blueprint changed")
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
    if "policy_inputs" in plan:
        _policy_inputs_binding(plan, plan["policy_inputs"])
    product_name = (DEVICE_PATH / "generated/device-candidate.mk").as_posix()
    product_identity, product_bytes = _read_file(Path(output) / product_name, limit=MAX_TEXT_BYTES, collect=True)
    _require(product_identity == files[product_name], "generated product changed during validation")
    if "policy_inputs" in plan:
        _require(product_bytes == _render_product(plan).encode("ascii"),
                 "native policy namespace export changed")
    else:
        _require(POLICY_INPUTS_PATH.encode("ascii") not in product_bytes,
                 "native policy namespace requires an explicit verified bundle")
    if "mi_ext_inputs" in plan:
        _require(product_bytes == _render_product(plan).encode("ascii"), "generated mi_ext A/B partition wiring changed")
    else:
        _require(not re.search(rb"\bmi_ext\b", product_bytes), "mi_ext A/B wiring requires an explicit verified bundle")
    if "framework_providers" in plan:
        _require(product_bytes == _render_product(plan).encode("ascii"), "framework provider product selection changed")
    else:
        _require(b"framework-providers" not in product_bytes and b"nezha_framework_" not in product_bytes,
                 "framework provider product selection requires an explicit source capability")
    for name in files:
        if name.startswith(DEVICE_PATH.as_posix() + "/") and name.endswith(".mk") and name != product_name:
            _, raw = _read_file(Path(output) / name, limit=MAX_TEXT_BYTES, collect=True)
            _require(POLICY_INPUTS_PATH.encode("ascii") not in raw,
                     "native policy namespace may only be exported by the reviewed generator")
        if name.startswith(DEVICE_PATH.as_posix() + "/") and name.endswith((".mk", ".bp")) and name not in {product_name, FRAMEWORK_PROVIDER_BLUEPRINT}:
            _, raw = _read_file(Path(output) / name, limit=MAX_TEXT_BYTES, collect=True)
            _require(b"framework-providers" not in raw and b"nezha_framework_" not in raw,
                     "framework provider modules and namespaces may only use the reviewed generated product and Blueprint")
    board_name = (DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix()
    board_identity, board_bytes = _read_file(Path(output) / board_name, limit=MAX_TEXT_BYTES, collect=True)
    _require(board_identity == files[board_name], "generated board changed during validation")
    board = board_bytes.decode("utf-8")
    _require("BOARD_AVB_ENABLE := true" in board, "generated AVB setting absent")
    _require(not re.search(r"--flags\s+[123]|--set_hashtree_disabled_flag|androidboot.selinux=permissive", board),
             "unsafe generated boot policy")
    if "mi_ext_inputs" in plan:
        _require(board_bytes == _render_board(plan).encode("ascii"), "generated mi_ext board wiring changed")
    else:
        _require("mi-ext-prebuilt.mk" not in board and not re.search(r"\bmi_ext\b|\b(?:BOARD|TARGET_COPY_OUT)_MI_EXT", board),
                 "mi_ext board wiring requires an explicit verified bundle")
    group_variable = f"BOARD_{plan['super']['group_name'].upper()}_PARTITION_LIST".encode("ascii")
    for name in files:
        if name.startswith(DEVICE_PATH.as_posix() + "/") and name.endswith(".mk"):
            _, raw = _read_file(Path(output) / name, limit=MAX_TEXT_BYTES, collect=True)
            if name not in {board_name, MI_EXT_BOARD_INCLUDE.as_posix()}:
                _require(not re.search(rb"\b(?:BOARD_(?:AVB_)?MI_EXT|BOARD_(?:AVB_)?CUSTOMIMAGES_(?:DIRECT_)?PARTITION_LIST|TARGET_COPY_OUT_MI_EXT)", raw)
                         and b"mi-ext-prebuilt.mk" not in raw and MI_EXT_INPUTS_PATH.encode("ascii") not in raw,
                         "mi_ext native input selection may only use the reviewed generated include")
            _require(name == product_name or not re.search(rb"\bAB_OTA_PARTITIONS\b", raw),
                     "A/B partition selection may only use the reviewed generated product")
            _require(name == board_name or not re.search(rb"\b" + re.escape(group_variable) + rb"\b", raw),
                     "dynamic group partition selection may only use the reviewed generated board")
            _require(name == board_name or (not re.search(rb"\bSYSTEM_EXT_(?:PUBLIC|PRIVATE)_SEPOLICY_DIRS\b", raw) and
                                           not any(path.encode("ascii") in raw for path in OEM_PROPERTY_WIRING.values())),
                     "OEM property source selection may only use the reviewed generated board")
    if "init_helper_capability" in plan:
        wiring = "\n" + "\n".join(_init_helper_wiring_lines()) + "\n"
        _require(board_bytes == _render_board(plan).encode("ascii") and board.count(wiring) == 1 and
                 INIT_HELPER_SYMBOL not in board.replace(wiring, "\n") and
                 "NEZHA_INIT_HELPER_CAPABILITY_CONTRACT" not in board.replace(wiring, "\n"),
                 "generated init-helper board wiring changed")
        guarded = {row["path"] for row in contract["device_guards"]}
        for name in files:
            if name.startswith(DEVICE_PATH.as_posix() + "/") and name not in guarded | {board_name} and not name.endswith("README.md"):
                _, raw = _read_file(Path(output) / name, limit=MAX_TEXT_BYTES, collect=True)
                _init_helper_conflicts(raw, name)
    else:
        _require(INIT_HELPER_SYMBOL not in board and "NEZHA_INIT_HELPER_CAPABILITY_CONTRACT" not in board,
                 "init-helper policy wiring requires an explicit reviewed contract")
    if "dsp_policy" in plan:
        wiring = ("\n" + "\n".join(_dsp_wiring_lines()) + "\n").encode("ascii")
        _require(board_bytes.endswith(wiring) and
                 all(board_bytes.count(name.encode("ascii")) ==
                     (1 + int("oem_policy" in plan and name in OEM_POLICY_WIRING) +
                      int("oem_properties" in plan and name in OEM_PROPERTY_WIRING))
                     for name in DSP_POLICY_WIRING),
                 "generated DSP board wiring changed")
    else:
        _require(not any(name in board for name in DSP_POLICY_WIRING),
                 "DSP policy wiring requires an explicit reviewed contract")
    if "oem_policy" in plan:
        wiring = "\n" + "\n".join(_oem_policy_wiring_lines()) + "\n"
        _require(board.count(wiring) == 1 and board.count("SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS") ==
                 1 + int("oem_properties" in plan) + int("framework_providers" in plan),
                 "generated OEM policy wiring changed")
    else:
        _require(not any(path in board for path in OEM_POLICY_WIRING.values()) and
                 "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS" not in board,
                 "OEM policy wiring requires an explicit reviewed contract")
    if "oem_properties" in plan:
        wiring = "\n" + "\n".join(_oem_property_wiring_lines()) + "\n"
        _require(board.count(wiring) == 1 and board_bytes == _render_board(plan).encode("ascii"),
                 "generated OEM property wiring changed")
    else:
        _require(not any(path in board for path in OEM_PROPERTY_WIRING.values()),
                 "OEM property wiring requires an explicit reviewed contract")
    if "framework_providers" in plan:
        wiring = "\n" + "\n".join(_framework_provider_wiring_lines()) + "\n"
        _require(board.count(wiring) == 1 and board_bytes == _render_board(plan).encode("ascii"),
                 "generated framework provider private policy wiring changed")
    else:
        _require(not any(path in board for path in FRAMEWORK_PROVIDER_WIRING.values()),
                 "framework provider policy wiring requires an explicit reviewed contract")
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
            sub.add_argument("--dsp-policy-contract", type=Path,
                             help="explicit reviewed DSP source contract; requires the factory profile, not a policy compatibility admission")
            sub.add_argument("--init-helper-capability-contract", type=Path,
                             help="explicit reviewed helper capability; requires factory and DSP profiles, never a ROM admission")
            sub.add_argument("--policy-inputs-receipt", type=Path,
                             help="verified separate native policy bundle; requires explicit helper and DSP capabilities")
            sub.add_argument("--oem-policy-contract", type=Path,
                             help="reviewed OEM system_ext source restoration; requires matching native policy inputs")
            sub.add_argument("--mi-ext-inputs-receipt", type=Path,
                             help="verified exact factory mi_ext prebuilt; requires factory profile, never complete packaging admission")
            sub.add_argument("--oem-property-contract", type=Path,
                             help="explicit four-property system_ext source contract; requires matching OEM base and native policy inputs")
            sub.add_argument("--framework-provider-policy-contract", type=Path,
                             help="explicit private Sigma/QCC source policy; requires paired provider inputs and matching native policy bundle")
            sub.add_argument("--framework-provider-inputs-receipt", type=Path,
                             help="exact external provider bundle; requires paired source policy and does not establish runtime support")
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
                                  partition_metadata=args.partition_metadata,
                                  dsp_policy_contract=args.dsp_policy_contract,
                                  init_helper_capability_contract=args.init_helper_capability_contract,
                                  policy_inputs_receipt=args.policy_inputs_receipt,
                                  oem_policy_contract=args.oem_policy_contract,
                                  mi_ext_inputs_receipt=args.mi_ext_inputs_receipt,
                                  oem_property_contract=args.oem_property_contract,
                                  framework_provider_policy_contract=args.framework_provider_policy_contract,
                                  framework_provider_inputs_receipt=args.framework_provider_inputs_receipt)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (CandidateError, OSError, KeyError, TypeError, StopIteration, ValueError) as exc:
        print(f"device generation refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
