#!/usr/bin/env python3
"""Preserve the exact factory Nezha mi_ext image for guarded native packaging.

Staging verifies bytes and their existing extraction provenance. It does not
authenticate Xiaomi, alter the image, enable factory framework overlays, sign
the ROM, or admit target-files/super/OTA/device operations. The native consumer
separately verifies AVB and keeps the descriptor directly in root vbmeta.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile

if __package__:
    from .artifact_files import publish_new_directory
else:
    from artifact_files import publish_new_directory


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "config/nezha-mi-ext.json"
SOURCE_CONTRACT_PATH = "patches/evolution/direct-avb-custom-images.json"
PATCH_PATH = "patches/evolution/0007-direct-avb-custom-images.patch"
FACTORY_RECORD_PATH = "research/factory-firmware-validation.json"
CORE_PATH = "build/make/core/Makefile"
BUILD_COMMIT = "a438ca40c6ed779042f806142b1165ba1360a7b2"
BUNDLE_PATH = "vendor/xiaomi/nezha-mi-ext"
RECEIPT_NAME = "mi-ext-inputs.json"
LOGICAL_RECEIPT_MEMBER = "logical-receipt.json"
IMAGE_MEMBER = "mi_ext.img"
EXPECTED_PACKAGE = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
EXPECTED_IMAGE = {"sha256": "60f791178bed4694870be74190b4487d9371af575e18ffbc950fb91fdb97e196",
                  "size_bytes": 111198208}
EXPECTED_CORE_BEFORE = {"sha256": "61a40da9741cae2119263ca0a92cd717874a88320e28fb0ee67505bed6829d31",
                        "size_bytes": 382008}
SEMANTIC_PATHS = {
    "build/make/tools/releasetools/common.py",
    "build/make/tools/releasetools/build_super_image.py",
    "build/make/tools/releasetools/validate_target_files.py",
}
COMPOSED_PATH = "build/make/tools/releasetools/add_img_to_target_files.py"
COMPOSED_PATCH = "patches/evolution/0006-ab-only-recovery-packaging.patch"
MAX_TEXT_BYTES = 4 * 1024**2
MAX_IMAGE_BYTES = 128 * 1024**2
SCOPE = {
    "prebuilt_preserved": True,
    "factory_overlays_activated": False,
    "complete_rom_admitted": False,
    "target_files_verified": False,
    "super_verified": False,
    "complete_avb_chain_verified": False,
    "hardware_tested": False,
    "phone_operations": [],
}


class MiExtInputsError(ValueError):
    """A selected image, provenance, native source, or private bundle differs."""


def require(condition, message):
    if not condition:
        raise MiExtInputsError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def expected(row, maximum=MAX_TEXT_BYTES):
    require(type(row) is dict and type(row.get("sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
            and type(row.get("size_bytes")) is int and 0 < row["size_bytes"] <= maximum,
            "invalid expected file identity")
    return {key: row[key] for key in ("sha256", "size_bytes")}


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    result = json.loads(data, object_pairs_hook=unique,
                        parse_constant=lambda _: require(False, "invalid JSON constant"))
    require(type(result) is dict, "expected a JSON object")
    return result


def _relative(value):
    require(type(value) is str and value and "\\" not in value and "\0" not in value,
            "invalid relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and all(part not in {".", ".."} for part in path.parts), "unsafe relative path")
    return value


def real_directory(path):
    path = Path(os.path.abspath(path))
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        require(stat.S_ISDIR(current.lstat().st_mode), "real directory required; symlinks are refused")
    return path


def _signature(details):
    return (details.st_dev, details.st_ino, details.st_mode, details.st_nlink,
            details.st_size, details.st_mtime_ns, details.st_ctime_ns)


class Reader:
    """Read bounded regular files and rehash every dependency before publishing."""

    def __init__(self):
        self.bindings = {}

    def read(self, path, row=None, *, maximum=MAX_TEXT_BYTES):
        path = Path(os.path.abspath(path))
        parent = real_directory(path.parent)
        parent_identity = _signature(parent.stat())[:2]
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 <= before.st_size <= maximum, "bounded regular file with one link required")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            require(_signature(before) == _signature(os.fstat(stream.fileno())), "input replaced before read")
            data = stream.read(maximum + 1)
            require(len(data) == before.st_size and _signature(before) == _signature(os.fstat(stream.fileno()))
                    == _signature(path.lstat()), "input changed during read")
        require(parent_identity == _signature(real_directory(path.parent).stat())[:2],
                "input directory replaced during read")
        measured = identity(data)
        require(row is None or measured == expected(row, maximum), "file identity differs from reviewed input")
        binding = (measured, _signature(before), maximum)
        require(path not in self.bindings or self.bindings[path] == binding, "input changed between reads")
        self.bindings[path] = binding
        return data

    def recheck(self):
        for path, (row, _, maximum) in list(self.bindings.items()):
            self.read(path, row, maximum=maximum)


def _controls(reader):
    paths = (CONTRACT_PATH, SOURCE_CONTRACT_PATH, PATCH_PATH, FACTORY_RECORD_PATH,
             "scripts/mi_ext_inputs.py", "scripts/artifact_files.py")
    controls = {path: reader.read(ROOT / path) for path in paths}
    contract = _json(controls[CONTRACT_PATH])
    require(type(contract.get("schema_version")) is int and contract["schema_version"] == 1
            and contract.get("contract_id") == "nezha-mi-ext-factory-v1"
            and contract.get("device") == {"codename": "nezha", "hardware_region": "CN"}
            and contract.get("platform") == {"branch": "bka", "release": "bp4a"}
            and contract.get("bundle") == BUNDLE_PATH
            and contract.get("factory_package_sha256") == EXPECTED_PACKAGE,
            "unexpected Nezha mi_ext contract")
    require(contract.get("source_contract") == SOURCE_CONTRACT_PATH
            and contract.get("filesystem") == "erofs"
            and encoded(contract.get("scope")) == encoded(SCOPE), "contract changes native scope")
    image = contract.get("image")
    require(expected(image, MAX_IMAGE_BYTES) == EXPECTED_IMAGE
            and image.get("partition") == "mi_ext_a" and image.get("filename") == "mi_ext_a.img"
            and image.get("readback_verified") is True, "only the exact factory mi_ext_a is admitted")
    factory_ref = contract.get("factory_record")
    require(type(factory_ref) is dict and factory_ref.get("path") == FACTORY_RECORD_PATH
            and expected(factory_ref) == identity(controls[FACTORY_RECORD_PATH]),
            "factory validation record differs from the reviewed identity")
    factory = _json(controls[FACTORY_RECORD_PATH])
    require(factory.get("device") == "nezha" and factory.get("hardware_region") == "CN"
            and type(factory.get("package")) is dict and factory["package"].get("sha256") == EXPECTED_PACKAGE
            and factory["package"].get("origin_verified") is False,
            "factory package provenance differs or claims authentication")
    logical = factory.get("logical_partitions", {})
    require(type(logical) is dict, "invalid factory logical-partition record")
    rows = logical.get("outputs")
    require(type(rows) is list and all(type(row) is dict for row in rows)
            and [row for row in rows if row.get("partition") == "mi_ext_a"] == [image],
            "mi_ext extraction differs from the validated factory record")
    require(contract.get("logical_receipt") == logical.get("receipt")
            and contract.get("source_super") == logical.get("source_image"), "logical provenance differs")
    _relative(contract["logical_receipt"]["path"])
    expected(contract["logical_receipt"])
    expected(contract["source_super"], 32 * 1024**3)
    require(image["parent_image_sha256"] == contract["source_super"]["sha256"], "wrong parent super image")
    avb = contract.get("avb")
    require(type(factory.get("avb")) is dict, "invalid factory AVB record")
    avb_rows = factory["avb"].get("hashtree_preflight")
    require(type(avb) is dict and avb.get("partition") == "mi_ext" and avb.get("source") == "vbmeta"
            and avb.get("file_size_bytes") == EXPECTED_IMAGE["size_bytes"]
            and avb.get("hash_algorithm") == "sha256"
            and avb.get("bounds") == {"data_fits": True, "tree_fits": True, "fec_fits": True}
            and type(avb_rows) is list and all(type(row) is dict for row in avb_rows)
            and [row for row in avb_rows if row.get("partition") == "mi_ext"] == [avb],
            "mi_ext must retain its evidenced direct root-vbmeta hashtree")
    layout = contract.get("dynamic_layout")
    require(type(layout) is dict and layout.get("partition_name") == "mi_ext"
            and layout.get("source_slot") == "a" and type(layout.get("source_b_slot_size_bytes")) is int
            and layout["source_b_slot_size_bytes"] == 0
            and layout.get("first_stage_mount_point") == "/mnt/vendor/mi_ext"
            and layout.get("fstab_avb_owner") == "vbmeta"
            and layout.get("group_name") == "qti_dynamic_partitions"
            and type(layout.get("super_size_bytes")) is int and layout["super_size_bytes"] == 15300820992
            and type(layout.get("group_maximum_bytes")) is int and layout["group_maximum_bytes"] == 15290335232
            and layout.get("logical_partition_names") == ["system", "system_ext", "product", "vendor", "odm",
                                                          "vendor_dlkm", "system_dlkm", "mi_ext"],
            "mi_ext must use the exact reviewed Nezha dynamic layout")
    source = _json(controls[SOURCE_CONTRACT_PATH])
    require(type(source.get("schema_version")) is int and source["schema_version"] == 1
            and source.get("contract_id") == "nezha-direct-avb-custom-images-v1"
            and type(source.get("project")) is dict and source["project"].get("path") == "build/make"
            and source["project"].get("commit") == BUILD_COMMIT
            and source.get("requires_patch") == "patches/evolution/0005-verified-prebuilt-recovery.patch",
            "unexpected native source patch contract")
    patch = source.get("patch")
    require(type(patch) is dict and patch.get("path") == PATCH_PATH
            and expected(patch) == identity(controls[PATCH_PATH]), "native patch differs from its contract")
    files = source.get("source_files")
    require(type(files) is list and len(files) == 1 and type(files[0]) is dict
            and files[0].get("path") == CORE_PATH and files[0].get("before") == EXPECTED_CORE_BEFORE,
            "direct-image patch must follow the preserved recovery consumer")
    expected(files[0].get("after"))
    semantic = source.get("semantic_files")
    require(type(semantic) is list and all(type(row) is dict for row in semantic)
            and len(semantic) == len(SEMANTIC_PATHS) and {row.get("path") for row in semantic} == SEMANTIC_PATHS,
            "missing or duplicate native packaging semantics")
    composed = source.get("composed_semantic_files")
    require(type(composed) is list and len(composed) == 1 and type(composed[0]) is dict
            and composed[0].get("path") == COMPOSED_PATH
            and composed[0].get("requires_patch") == COMPOSED_PATCH,
            "native packaging requires the reviewed A/B-only recovery path")
    for row in [*semantic, *composed]:
        expected(row)
    return contract, source, controls


def _logical_receipt(reader, path, contract):
    raw = reader.read(path, contract["logical_receipt"])
    value = _json(raw)
    require(type(value.get("schema_version")) is int and value["schema_version"] == 1
            and value.get("status") == "complete" and value.get("authentication_verified") is False
            and all(value.get(name) is True for name in ("all_geometry_and_metadata_copies_valid",
                                                        "all_primary_backup_pairs_match", "all_slots_identical")),
            "logical extraction provenance is incomplete or overclaims authentication")
    require(expected(value.get("source_image"), 32 * 1024**3) == contract["source_super"],
            "logical extraction parent differs")
    rows = value.get("outputs")
    require(type(rows) is list and all(type(row) is dict for row in rows)
            and [row for row in rows if row.get("partition") == "mi_ext_a"] == [contract["image"]],
            "logical extraction does not contain exactly the admitted mi_ext image")
    return raw


def _source_files(source):
    return ([{"path": row["path"], **row["after"]} for row in source["source_files"]]
            + [{"path": row["path"], **expected(row)}
               for row in [*source["semantic_files"], *source["composed_semantic_files"]]])


def _manifest(contract, source, controls, logical_raw):
    return {
        "schema_version": 1, "operation": "stage-nezha-mi-ext-inputs", "status": "staged",
        "device": "nezha", "bundle": BUNDLE_PATH, "factory_package_sha256": EXPECTED_PACKAGE,
        "controls": [{"path": path, **identity(data)} for path, data in sorted(controls.items())],
        "source_image": copy.deepcopy(contract["image"]), "source_super": copy.deepcopy(contract["source_super"]),
        "avb_descriptor": copy.deepcopy(contract["avb"]), "dynamic_layout": copy.deepcopy(contract["dynamic_layout"]),
        "files": [{"path": IMAGE_MEMBER, **EXPECTED_IMAGE},
                  {"path": LOGICAL_RECEIPT_MEMBER, **identity(logical_raw)}],
        "required_native_source": {"project_commit": BUILD_COMMIT, "files": _source_files(source)},
        "native_source_checked_by_staging": False, "native_avb_run_by_staging": False,
        "readback_verified": True, "scope": copy.deepcopy(SCOPE),
    }


def _members(bundle):
    require(stat.S_IMODE(bundle.stat().st_mode) == 0o700, "private mi_ext bundle must have mode 0700")
    members = set()
    for path in bundle.iterdir():
        details = path.lstat()
        require(stat.S_ISREG(details.st_mode) and details.st_nlink == 1
                and stat.S_IMODE(details.st_mode) in (0o400, 0o600), "unexpected or non-private bundle member")
        members.add(path.name)
    require(members == {IMAGE_MEMBER, LOGICAL_RECEIPT_MEMBER, RECEIPT_NAME}, "missing or extra bundle members")


def _output_path(output):
    output = Path(os.path.abspath(output))
    parent = real_directory(output.parent)
    require(not os.path.lexists(output), "mi_ext output already exists; originals cannot be replaced")
    if output.is_relative_to(ROOT):
        relative = output.relative_to(ROOT).as_posix()
        require(relative.startswith(("artifacts/", "evidence/", "reports/")),
                "stage workspace mi_ext inputs into an ignored artifact directory")
    return output, parent


def stage_inputs(image, output, *, logical_receipt):
    """Copy to a fresh private directory; never alter an image or run a device."""
    output, parent = _output_path(output)
    image = Path(os.path.abspath(image))
    logical_receipt = Path(os.path.abspath(logical_receipt))
    require(not output.is_relative_to(image.parent) and not output.is_relative_to(logical_receipt.parent),
            "output cannot add files inside preserved input directories")
    reader = Reader()
    contract, source, controls = _controls(reader)
    logical_raw = _logical_receipt(reader, logical_receipt, contract)
    image_raw = reader.read(image, EXPECTED_IMAGE, maximum=MAX_IMAGE_BYTES)
    receipt = _manifest(contract, source, controls, logical_raw)
    files = {IMAGE_MEMBER: image_raw, LOGICAL_RECEIPT_MEMBER: logical_raw, RECEIPT_NAME: encoded(receipt)}
    require(shutil.disk_usage(parent).free >= sum(map(len, files.values())) + MAX_TEXT_BYTES,
            "insufficient free disk for private mi_ext staging")
    staging = Path(tempfile.mkdtemp(prefix=".mi-ext-stage-", dir=parent))
    try:
        for name, data in files.items():
            with os.fdopen(os.open(staging / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            require(identity((staging / name).read_bytes()) == identity(data), "staged readback differs")
        _members(staging)
        reader.recheck()
        publish_new_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"status": "staged", "receipt": {"path": RECEIPT_NAME, **identity(files[RECEIPT_NAME])},
            "files": copy.deepcopy(receipt["files"]), "scope": copy.deepcopy(SCOPE)}


def verify_bundle(bundle, *, source_tree=None):
    """Rehash a relocated private bundle using trusted workspace controls.

    With source_tree supplied, also check the actual composed native consumers.
    Without it, no installed Android source or native verification is claimed.
    """
    bundle = real_directory(bundle)
    _members(bundle)
    reader = Reader()
    contract, source, controls = _controls(reader)
    logical_raw = _logical_receipt(reader, bundle / LOGICAL_RECEIPT_MEMBER, contract)
    reader.read(bundle / IMAGE_MEMBER, EXPECTED_IMAGE, maximum=MAX_IMAGE_BYTES)
    raw = reader.read(bundle / RECEIPT_NAME)
    receipt = _json(raw)
    require(encoded(receipt) == encoded(_manifest(contract, source, controls, logical_raw)),
            "mi_ext receipt differs from the exact current controls, inputs, or scope")
    native_checked = source_tree is not None
    if native_checked:
        source_tree = real_directory(source_tree)
        for row in _source_files(source):
            reader.read(source_tree / row["path"], row)
    reader.recheck()
    return {"schema_version": 1, "status": "verified", "device": "nezha", "bundle": BUNDLE_PATH,
            "factory_package_sha256": EXPECTED_PACKAGE, "image": copy.deepcopy(EXPECTED_IMAGE),
            "dynamic_layout": copy.deepcopy(contract["dynamic_layout"]),
            "receipt": {"path": RECEIPT_NAME, **identity(raw)},
            "native_source": {"project_commit": BUILD_COMMIT, "files": _source_files(source)},
            "actual_native_source_bytes_checked": native_checked, "native_avb_run": False,
            "scope": copy.deepcopy(SCOPE)}


def validate_admission(receipt_path, *, expected_package_sha256):
    """Offline generator hook; native Make rechecks the actual source later."""
    receipt_path = Path(os.path.abspath(receipt_path))
    require(receipt_path.name == RECEIPT_NAME, "mi_ext receipt must retain its canonical filename")
    require(expected_package_sha256 == EXPECTED_PACKAGE, "mi_ext and admitted factory vendor packages differ")
    verified = verify_bundle(receipt_path.parent)
    return {key: copy.deepcopy(verified[key]) for key in
            ("bundle", "factory_package_sha256", "image", "dynamic_layout", "receipt", "native_source", "scope")}


def render_board_include(binding):
    """Emit a final board include from a separately verified admission binding."""
    reader = Reader()
    contract, source, _ = _controls(reader)
    require(type(binding) is dict and binding.get("bundle") == BUNDLE_PATH
            and binding.get("factory_package_sha256") == EXPECTED_PACKAGE
            and binding.get("image") == EXPECTED_IMAGE and encoded(binding.get("scope")) == encoded(SCOPE)
            and encoded(binding.get("dynamic_layout")) == encoded(contract["dynamic_layout"])
            and binding.get("native_source") == {"project_commit": BUILD_COMMIT, "files": _source_files(source)},
            "invalid mi_ext admission binding")
    receipt = binding.get("receipt")
    require(type(receipt) is dict and receipt.get("path") == RECEIPT_NAME, "unexpected mi_ext receipt member")
    expected(receipt)
    lines = ["# Generated exact factory mi_ext input; normal Android remains enforcing.",
             "# Direct root-vbmeta descriptor; no overlay activation or complete-ROM admission.",
             "ifneq ($(BOARD_AVB_ENABLE),true)", "$(error Nezha mi_ext requires AVB)", "endif"]
    for row in _source_files(source):
        lines += [f"ifneq ($(shell sha256sum < {row['path']} 2>/dev/null | cut -d ' ' -f 1),{row['sha256']})",
                  f"$(error Nezha mi_ext requires its reviewed composed native source: {row['path']})", "endif"]
    for member, digest in ((IMAGE_MEMBER, EXPECTED_IMAGE["sha256"]), (RECEIPT_NAME, receipt["sha256"]),
                           (LOGICAL_RECEIPT_MEMBER, contract["logical_receipt"]["sha256"])):
        path = BUNDLE_PATH + "/" + member
        lines += [f"ifneq ($(shell test -f {path} && test ! -L {path} && echo regular),regular)",
                  f"$(error Nezha mi_ext input must be a regular file: {member})", "endif",
                  f"ifneq ($(shell sha256sum < {path} 2>/dev/null | cut -d ' ' -f 1),{digest})",
                  f"$(error Nezha mi_ext input differs from its reviewed receipt: {member})", "endif"]
    forbidden = ["BOARD_AVB_MI_EXT_KEY_PATH", "BOARD_AVB_MI_EXT_ALGORITHM", "BOARD_AVB_MI_EXT_ROLLBACK_INDEX",
                 "BOARD_AVB_MI_EXT_ROLLBACK_INDEX_LOCATION", "BOARD_AVB_MI_EXT_ADD_HASHTREE_FOOTER_ARGS",
                 "BOARD_AVB_MI_EXT_PARTITION_SIZE", "BOARD_AVB_MI_EXT_IMAGE_LIST", "BOARD_MI_EXT_IMAGE_NO_FLASHALL"]
    for key in forbidden:
        lines += [f"ifneq ($(origin {key}),undefined)",
                  f"$(error Nezha mi_ext forbids child signing, alternate-image, or ZIP-exclusion settings: {key})", "endif"]
    lines += ["ifneq ($(filter mi_ext,$(BOARD_AVB_VBMETA_SYSTEM) $(BOARD_AVB_VBMETA_VENDOR) $(foreach p,$(BOARD_AVB_VBMETA_CUSTOM_PARTITIONS),$(BOARD_AVB_VBMETA_$(call to-upper,$(p))))),)",
              "$(error Nezha mi_ext descriptor must remain directly in root vbmeta)", "endif"]
    values = {"BOARD_CUSTOMIMAGES_PARTITION_LIST": "mi_ext", "BOARD_AVB_CUSTOMIMAGES_DIRECT_PARTITION_LIST": "mi_ext",
              "BOARD_MI_EXT_IMAGE_LIST": BUNDLE_PATH + "/" + IMAGE_MEMBER,
              "BOARD_MI_EXT_IMAGE_SHA256": EXPECTED_IMAGE["sha256"]}
    for key, value in values.items():
        lines += [f"ifneq ($(origin {key}),undefined)", f"$(error Nezha mi_ext selector must be assigned exactly once: {key})", "endif",
                  f"{key} := {value}", f"ifneq ($({key}),{value})", f"$(error Nezha mi_ext selector was overridden: {key})", "endif"]
    lines += [".KATI_READONLY := " + " ".join(values),
              "# Core rejects intervening child-setting definitions before freezing them.",
              "# This avoids relying on the origin of an undefined variable marked readonly.",
              "# Core also assigns and freezes the derived AVB image-list alias.", ""]
    reader.recheck()
    return "\n".join(lines)


def check_packaging(misc_info, fastboot_info, ab_partitions, images):
    """Check actual selected metadata and image bytes, without claiming full OTA/AVB."""
    reader = Reader()
    contract, _, _ = _controls(reader)
    raw = reader.read(misc_info)
    info = {}
    for line in raw.decode().splitlines():
        if not line or line.startswith("#"):
            continue
        require("=" in line, "malformed misc_info line")
        key, value = line.split("=", 1)
        require(key and key not in info, "duplicate misc_info key")
        info[key] = value
    for key in ("avb_enable", "ab_update", "use_dynamic_partitions", "virtual_ab"):
        require(info.get(key) == "true", "required Nezha AVB/dynamic/A-B metadata differs: " + key)
    require(info.get("allow_non_ab") != "true" and info.get("dynamic_partition_retrofit") != "true",
            "Nezha mi_ext requires its launch A/B-only layout")
    for key in ("avb_custom_images_partition_list", "avb_custom_images_direct_partition_list"):
        require(info.get(key, "").split() == ["mi_ext"], "mi_ext AVB custom registration differs")
    require("mi_ext" not in info.get("custom_images_partition_list", "").split()
            and info.get("avb_mi_ext_image_list") == IMAGE_MEMBER, "mi_ext is not the direct AVB custom prebuilt")
    forbidden = {"avb_mi_ext_key_path", "avb_mi_ext_algorithm", "avb_mi_ext_rollback_index_location",
                 "avb_mi_ext_rollback_index", "avb_mi_ext_add_hashtree_footer_args", "avb_mi_ext_partition_size"}
    require(not forbidden.intersection(info), "mi_ext metadata must omit child signing fields, even empty ones")
    require(all("mi_ext" not in value.split() for key, value in info.items()
                if key.startswith("avb_vbmeta_") and not key.endswith(("_args", "_key_path", "_algorithm", "_rollback_index_location"))),
            "mi_ext was assigned to a chained vbmeta")
    layout = contract["dynamic_layout"]
    names = layout["logical_partition_names"]
    for key in ("dynamic_partition_list", "super_qti_dynamic_partitions_partition_list"):
        values = info.get(key, "").split()
        require(len(values) == len(set(values)) and set(values) == set(names), "logical partition inventory differs")
    require(info.get("super_partition_groups") == layout["group_name"]
            and info.get("super_partition_size") == str(layout["super_size_bytes"])
            and info.get("super_qti_dynamic_partitions_group_size") == str(layout["group_maximum_bytes"]),
            "super/group budgets differ from Nezha metadata")
    ab_raw = reader.read(ab_partitions)
    ab_names = ab_raw.decode().split()
    require(len(ab_names) == len(set(ab_names)) and set(names) <= set(ab_names),
            "A/B payload omits a logical partition or duplicates entries")
    fastboot_raw = reader.read(fastboot_info)
    commands = [line.strip() for line in fastboot_raw.decode().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    require(commands.count("reboot fastboot") == commands.count("update-super") == commands.count("flash mi_ext") == 1
            and commands.index("reboot fastboot") < commands.index("update-super") < commands.index("flash mi_ext"),
            "mi_ext must have exactly one flash entry after userspace fastboot/update-super")
    require(sum("mi_ext" in line.split() or "mi_ext.img" in line.split() for line in commands) == 1,
            "duplicate or alternate mi_ext flash command")
    images = real_directory(images)
    reader.read(images / IMAGE_MEMBER, EXPECTED_IMAGE, maximum=MAX_IMAGE_BYTES)
    reader.recheck()
    return {"status": "verified", "operation": "check-nezha-mi-ext-packaging-metadata",
            "image": copy.deepcopy(EXPECTED_IMAGE), "logical_partition_names": names,
            "metadata": {"misc_info": identity(raw), "fastboot_info": identity(fastboot_raw), "ab_partitions": identity(ab_raw)},
            "scope": copy.deepcopy(SCOPE), "selected_metadata_and_image_only": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--image", type=Path, required=True)
    stage.add_argument("--logical-receipt", type=Path, required=True)
    stage.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--source-tree", type=Path)
    check = sub.add_parser("check-packaging")
    for name in ("misc-info", "fastboot-info", "ab-partitions", "images"):
        check.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            result = stage_inputs(args.image, args.output, logical_receipt=args.logical_receipt)
        elif args.command == "verify":
            result = verify_bundle(args.bundle, source_tree=args.source_tree)
        else:
            result = check_packaging(args.misc_info, args.fastboot_info, args.ab_partitions, args.images)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"mi_ext inputs refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
