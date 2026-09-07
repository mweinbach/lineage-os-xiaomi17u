#!/usr/bin/env python3
"""Reproduce the exact first target-files source derivative, without dispatch.

The normal generator verifies every base input before selecting this capability.
This module binds that complete base admission and changes only the reviewed
BoardConfig block plus its generated guard. Current source, build metadata,
native preflight, artifacts and device readiness remain separate admissions.
"""
from __future__ import annotations

import copy
from pathlib import Path

try:
    from . import target_files_metadata as metadata
except ImportError:
    import target_files_metadata as metadata


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "config/nezha-rom-construction-source-v1.json"
CONTRACT_SHA256 = "52de1c021013a1330f14ff0d6710d61cdf8403e5779e17314c2b35017b8ed6b5"
CONTRACT_ID = "nezha-first-target-files-source-v1"
BOARD = "device/xiaomi/nezha/BoardConfig.mk"
GUARD = "device/xiaomi/nezha/generated/rom-construction.mk"
BINDING = "rom_construction_source"
BASE_ADMISSION = {"sha256": "13b6924419fde3ca9053c28f19d5e5fee9ec7e404ee11fb76a83fd77484f33ae", "size_bytes": 162579}
BOARD_BEFORE = {"sha256": "f7cbc7a3bf92489e53c6d0e80e0443722c043fda5713076902aacb0eeb215332", "size_bytes": 3948}
BOARD_AFTER = {"sha256": "51869a9cdeb61630183a954e239aeca6f14a2f483cffa9c53f4a56110b5f7c5b", "size_bytes": 3560}
GUARD_ID = {"sha256": "fe1e32cffe0d7b7ba20a9fd1d90f1cf8712f9fa6b7aa0e3ec1a90a6b7058c469", "size_bytes": 2553}
BLOCK = (
    b"ifneq ($(strip $(filter evolution droid droid_targets droidcore droidcore-unbundled dist_files checkbuild "
    b"target-files-package target-files-dir otapackage otardppackage partialotapackage updatepackage bacon "
    b"superimage superimage_dist superimage-nodeps supernod superimage_empty super_empty,$(MAKECMDGOALS))),)\n"
    b"$(error Nezha framework-checks profile does not admit complete target-files, OTA or super packaging; see generated admission.json)\n"
    b"endif\n"
)
INCLUDE = b"include $(NEZHA_DEVICE_PATH)/generated/rom-construction.mk\n"
GUARD_TEXT = """# Deterministically derived Nezha first target-files capability.
# Separate source/history admission is mandatory before the native invocation.
# No ROM/flash readiness, signed-image or hardware claim is made here.
ifneq ($(origin NEZHA_FIRST_TARGET_FILES_CAPABILITY),undefined)
$(error Nezha construction capability cannot be supplied or included twice)
endif
NEZHA_FIRST_TARGET_FILES_CAPABILITY := nezha-first-target-files-v1
.KATI_READONLY := NEZHA_FIRST_TARGET_FILES_CAPABILITY
ifneq ($(strip $(filter evolution droid droid_targets droidcore droidcore-unbundled dist_files checkbuild target-files-dir otapackage otardppackage partialotapackage updatepackage bacon superimage superimage_dist superimage-nodeps supernod superimage_empty super_empty,$(MAKECMDGOALS))),)
$(error Nezha first construction does not admit default ROM, super or OTA packaging aliases)
endif
ifneq ($(strip $(filter target-files-package,$(MAKECMDGOALS))),)
ifneq ($(strip $(MAKECMDGOALS)),target-files-package)
$(error Nezha first construction requires the sole target-files-package goal)
endif
ifneq ($(TARGET_PRODUCT),lineage_nezha)
$(error Nezha first construction requires lineage_nezha)
endif
ifneq ($(RELEASE_PLATFORM_VERSION),BP4A)
$(error Nezha first construction requires RELEASE_PLATFORM_VERSION=BP4A)
endif
ifneq ($(RELEASE_PLATFORM_VERSION_CODENAME),REL)
$(error Nezha first construction requires RELEASE_PLATFORM_VERSION_CODENAME=REL)
endif
ifneq ($(RELEASE_PLATFORM_VERSION_LAST_STABLE),16)
$(error Nezha first construction requires RELEASE_PLATFORM_VERSION_LAST_STABLE=16)
endif
ifneq ($(RELEASE_PLATFORM_SDK_VERSION),36)
$(error Nezha first construction requires RELEASE_PLATFORM_SDK_VERSION=36)
endif
ifneq ($(TARGET_BUILD_VARIANT),user)
$(error Nezha first construction requires the user variant)
endif
ifneq ($(WITH_GMS),true)
$(error Nezha first construction requires the reviewed GMS selection)
endif
ifneq ($(value NEZHA_USE_PINNED_BUILD_DATETIME),true)
$(error Nezha first construction requires the reviewed pinned metadata interface)
endif
ifneq ($(value PRODUCT_MAX_PAGE_SIZE_SUPPORTED),4096)
$(error Nezha first construction requires the selected 4 KiB product)
endif
ifneq ($(value PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE),true)
$(error Nezha first construction requires prebuilt alignment checks)
endif
ifneq ($(value PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO),true)
$(error Nezha first construction requires the Bionic page-size guard)
endif
ifneq ($(BOARD_AVB_ENABLE),true)
$(error Nezha first construction requires AVB-enabled ordinary rules)
endif
endif
"""


class ConstructionSourceError(ValueError):
    """The selected source derivative differs from the reviewed capability."""


def require(condition, message):
    if not condition:
        raise ConstructionSourceError(message)


def load_contract(path=None):
    reader = metadata.Reader()
    raw = reader.read(ROOT / CONTRACT)
    require(metadata.identity(raw)["sha256"] == CONTRACT_SHA256,
            "maintained construction source contract changed; review a new binding")
    if path is not None:
        require(reader.read(path) == raw, "construction source selector differs from the maintained contract")
    value = metadata._json(raw)
    require(value["schema_version"] == 1 and type(value["schema_version"]) is int
            and value["contract_id"] == CONTRACT_ID and value["base_admission"] == BASE_ADMISSION
            and value["board_before"] == BOARD_BEFORE and value["board_after"] == BOARD_AFTER
            and value["guard"] == GUARD_ID, "construction source contract identity differs")
    reader.recheck()
    return value, metadata.identity(raw)


def render_guard():
    raw = GUARD_TEXT.encode("ascii")
    require(metadata.identity(raw) == GUARD_ID, "maintained construction guard changed")
    return raw


def derive_board(raw):
    require(type(raw) is bytes and metadata.identity(raw) == BOARD_BEFORE
            and raw.count(BLOCK) == 1 and b"rom-construction" not in raw,
            "construction requires the exact delivery Board predecessor")
    result = raw.replace(BLOCK, INCLUDE, 1)
    require(metadata.identity(result) == BOARD_AFTER, "construction Board derivation differs")
    return result


def restore_board(raw):
    require(type(raw) is bytes and metadata.identity(raw) == BOARD_AFTER
            and raw.count(INCLUDE) == 1 and BLOCK not in raw, "construction Board bytes differ")
    result = raw.replace(INCLUDE, BLOCK, 1)
    require(derive_board(result) == raw, "construction Board changed outside its exact derivation")
    return result


def file_entries(payloads):
    return [{"path": name, **metadata.identity(raw)} for name, raw in sorted(payloads.items())]


def _check_base(plan, payloads):
    require(BINDING not in plan and GUARD not in payloads, "construction source capability selected twice")
    require(plan.get("files") == file_entries(payloads), "base source bytes differ from their admission")
    require(metadata.identity(metadata.encoded(plan)) == BASE_ADMISSION,
            "construction requires the complete exact selected base admission")


def apply(plan, payloads, contract_path):
    """Select after ordinary base generation and every existing input check."""
    contract, identity = load_contract(contract_path)
    _check_base(plan, payloads)
    result, files = copy.deepcopy(plan), dict(payloads)
    files[BOARD] = derive_board(files[BOARD])
    files[GUARD] = render_guard()
    result[BINDING] = {"contract": identity, "contract_id": CONTRACT_ID,
                       "base_admission": BASE_ADMISSION, "scope": copy.deepcopy(contract["scope"])}
    result["files"] = file_entries(files)
    validate(result, files)
    return result, files


def validate(plan, payloads):
    """Reconstruct the complete base; resealing arbitrary new inputs fails."""
    contract, identity = load_contract()
    expected = {"contract": identity, "contract_id": CONTRACT_ID,
                "base_admission": BASE_ADMISSION, "scope": contract["scope"]}
    require(metadata.encoded(plan.get(BINDING)) == metadata.encoded(expected),
            "construction source admission differs from the maintained capability")
    require(plan.get("files") == file_entries(payloads) and payloads.get(GUARD) == render_guard(),
            "construction source files or generated guard differ")
    base, files = copy.deepcopy(plan), dict(payloads)
    del base[BINDING]
    del files[GUARD]
    files[BOARD] = restore_board(files[BOARD])
    base["files"] = file_entries(files)
    _check_base(base, files)
    return base


# Explicit successor only. The original functions above and their default
# Board/guard identities remain unchanged. The new descriptor binds a separate
# complete policy3 base; native output and device admission remain separate.
POLICY3_CONTRACT = "config/nezha-rom-construction-source-policy3-v1.json"
POLICY3_CONTRACT_ID = "nezha-policy3-first-target-files-source-v1"
POLICY3_CONTRACT_SHA256 = "8edf25080891ccd41a7650804f764ddaca0572ac834e294ecfc9e387f50f894c"
POLICY3_BINDINGS = ("base_admission", "board_before", "board_after")
CHECKSUM_CONTRACT = "config/nezha-rom-construction-source-checksum-v1.json"
CHECKSUM_CONTRACT_ID = "nezha-metadata-checksum-first-target-files-source-v1"
# Bound only after the complete checksum base has been generated and measured.
CHECKSUM_CONTRACT_SHA256 = "18f0a6cd6c6e9e59d1ea8d0b0f3a8db3719543691a17e03c8d756a8bf3ce868e"
CHECKSUM_SOURCE_CONTRACT = {
    "path": "patches/evolution/target-files-metadata-checksum.json",
    "contract_id": "nezha-target-files-metadata-checksum-v1",
    "sha256": "ee28f64d09c75d724c0be5dc07d98816cf30c4f59cf09a45c6163f6c96428e01",
    "size_bytes": 1455,
}
MODE_FLAGS_CONTRACT = "config/nezha-rom-construction-source-mode-flags-v1.json"
MODE_FLAGS_CONTRACT_ID = "nezha-metadata-mode-flags-first-target-files-source-v1"
# Bound only after the complete metadata mode-flags base is measured.
MODE_FLAGS_CONTRACT_SHA256 = "8359d6510f76b66961824a89b4d58eeaa950181510c6aa73f8a374e80bd1b227"
AVB_SHA256_CONTRACT = "config/nezha-rom-construction-source-avb-sha256-v1.json"
AVB_SHA256_CONTRACT_ID = "nezha-avb-sha256-first-target-files-source-v1"
AVB_SHA256_CONTRACT_SHA256 = "fdd43bbcad80ffbf135f9f9d614c19ec3b6af7dd3d74a9978c19ca3e45e619d5"
AVB_SHA256_BOARD_AFTER = {
    "sha256": "9047a845e1149c24246223c2a3ee98610fc949b115bf84c1b44be00904da4233",
    "size_bytes": 4131,
}
AVB_SHA256_BLOCK = b"""
# Explicit SHA-256 hashtrees for source-built logical images.
BOARD_AVB_SYSTEM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
BOARD_AVB_SYSTEM_EXT_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
BOARD_AVB_PRODUCT_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
BOARD_AVB_SYSTEM_DLKM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
BOARD_AVB_VENDOR_DLKM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
"""
POLICY3_IMAGE_CONTRACT = "config/nezha-policy-image-delivery-policy3.json"
POLICY3_IMAGE_CONTRACT_ID = "nezha-policy3-final-leaf-metadata-delivery-v1"
POLICY3_BASIS = {
    "image_input_profile": "policy3-evolution",
    "image_input_contract_id": "nezha-five-file-policy-image-inputs-policy3-evolution-v1",
    "policy_build": {"sha256": "344ba909febe8be29479f5bf1d48d122e931e88fb1d4d71dbcdab08708483c18", "size_bytes": 10165316},
    "sidecar_validation": {"sha256": "57e2191f1d948407dda3adf040edb3b58ce018adb6bb4a1d56471bb0226682fd", "size_bytes": 44989},
    "source_files": 539, "source_projects": 13,
    "recorded_basis_only": True, "future_candidate_or_installation_verified": False,
}
_v1_load_contract = load_contract
_v1_derive_board = derive_board
_v1_restore_board = restore_board
_v1_apply = apply
_v1_validate = validate


def _policy3_contract(raw):
    value = metadata._json(raw)
    old, _ = _v1_load_contract()
    keys = (set(old) - {"recorded_source_installation"}) | {"recorded_policy_basis", "selected_policy_image_contract"}
    require(type(value) is dict and set(value) == keys
            and type(value["schema_version"]) is int and value["schema_version"] == 2
            and value["contract_id"] == POLICY3_CONTRACT_ID,
            "unknown policy3 construction source schema or fields")
    for name in keys - {"schema_version", "contract_id", "recorded_policy_basis", "selected_policy_image_contract", *POLICY3_BINDINGS}:
        require(metadata.encoded(value[name]) == metadata.encoded(old[name]),
                "policy3 construction changes preserved context, guard or scope: " + name)
    require(metadata.encoded(value["recorded_policy_basis"]) == metadata.encoded(POLICY3_BASIS),
            "policy3 construction recorded policy basis differs")
    image = value["selected_policy_image_contract"]
    require(type(image) is dict and set(image) == {"path", "contract_id", "sha256", "size_bytes"}
            and image["path"] == POLICY3_IMAGE_CONTRACT and image["contract_id"] == POLICY3_IMAGE_CONTRACT_ID,
            "policy3 construction requires its exact selected image contract reference")
    missing = [name for name in POLICY3_BINDINGS if value[name] is None]
    missing.extend("selected_policy_image_contract." + key for key in ("sha256", "size_bytes") if image[key] is None)
    require(not missing, "policy3 construction is unbound; missing actual bindings: " + ", ".join(missing))
    bindings = {name: value[name] for name in POLICY3_BINDINGS}
    bindings["selected_policy_image_contract"] = {key: image[key] for key in ("sha256", "size_bytes")}
    for name, row in bindings.items():
        require(type(row) is dict and set(row) == {"sha256", "size_bytes"}
                and type(row["sha256"]) is str and len(row["sha256"]) == 64
                and all(character in "0123456789abcdef" for character in row["sha256"])
                and type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= 8 << 20,
                "policy3 construction actual binding is invalid: " + name)
    return value


def _checksum_contract(raw):
    value = metadata._json(raw)
    old, _ = load_contract(ROOT / POLICY3_CONTRACT)
    require(type(value) is dict and set(value) == set(old) | {"selected_source_contract"}
            and type(value["schema_version"]) is int and value["schema_version"] == 3
            and value["contract_id"] == CHECKSUM_CONTRACT_ID,
            "unknown checksum construction source schema or fields")
    # Reuse the policy3 binding checks, then close every field except the new
    # complete base and explicit checksum source selector against that contract.
    projected = {name: value[name] for name in old}
    projected.update(schema_version=2, contract_id=POLICY3_CONTRACT_ID)
    _policy3_contract(metadata.encoded(projected))
    for name in set(old) - {"schema_version", "contract_id", "base_admission"}:
        require(metadata.encoded(value[name]) == metadata.encoded(old[name]),
                "checksum construction changes preserved policy3 field: " + name)
    require(value["base_admission"] != old["base_admission"],
            "checksum construction requires its separately measured complete base")
    require(metadata.encoded(value["selected_source_contract"]) == metadata.encoded(CHECKSUM_SOURCE_CONTRACT),
            "checksum construction source selector differs")
    return value


def _mode_flags_contract(raw):
    value = metadata._json(raw)
    old, _ = load_contract(ROOT / CHECKSUM_CONTRACT)
    require(type(value) is dict and set(value) == set(old)
            and type(value["schema_version"]) is int and value["schema_version"] == 3
            and value["contract_id"] == MODE_FLAGS_CONTRACT_ID,
            "unknown metadata mode-flags construction source schema or fields")
    # The installer fix changes its complete generated base, not source
    # composition, image inputs, BoardConfig, the construction guard or scope.
    _checksum_contract(metadata.encoded(dict(value, contract_id=CHECKSUM_CONTRACT_ID)))
    for name in set(old) - {"contract_id", "base_admission"}:
        require(metadata.encoded(value[name]) == metadata.encoded(old[name]),
                "metadata mode-flags construction changes preserved checksum field: " + name)
    require(value["base_admission"] != old["base_admission"],
            "metadata mode-flags construction requires its separately measured complete base")
    return value


def _avb_sha256_contract(raw):
    value = metadata._json(raw)
    old, _ = load_contract(ROOT / MODE_FLAGS_CONTRACT)
    require(type(value) is dict and set(value) == set(old)
            and value.get("contract_id") == AVB_SHA256_CONTRACT_ID,
            "unknown SHA-256 construction source schema or fields")
    # Reuse every predecessor check; only the selected Board gains footer args.
    projected = dict(value, contract_id=MODE_FLAGS_CONTRACT_ID,
                     board_after=old["board_after"])
    _mode_flags_contract(metadata.encoded(projected))
    for name in set(old) - {"contract_id", "board_after"}:
        require(metadata.encoded(value[name]) == metadata.encoded(old[name]),
                "SHA-256 construction changes preserved mode-flags field: " + name)
    require(value["board_after"] == AVB_SHA256_BOARD_AFTER,
            "SHA-256 construction Board binding differs")
    return value


def load_contract(path=None):
    """Omission retains v1; successors require exact explicit descriptor bytes."""
    if path is None:
        return _v1_load_contract()
    reader = metadata.Reader()
    selected = reader.read(path)
    value = metadata._json(selected)
    if type(value) is not dict or value.get("contract_id") not in (POLICY3_CONTRACT_ID, CHECKSUM_CONTRACT_ID, MODE_FLAGS_CONTRACT_ID, AVB_SHA256_CONTRACT_ID):
        reader.recheck()
        return _v1_load_contract(path)
    mode_flags = value["contract_id"] == MODE_FLAGS_CONTRACT_ID
    checksum = value["contract_id"] == CHECKSUM_CONTRACT_ID
    avb_sha256 = value["contract_id"] == AVB_SHA256_CONTRACT_ID
    record = AVB_SHA256_CONTRACT if avb_sha256 else MODE_FLAGS_CONTRACT if mode_flags else CHECKSUM_CONTRACT if checksum else POLICY3_CONTRACT
    digest = AVB_SHA256_CONTRACT_SHA256 if avb_sha256 else MODE_FLAGS_CONTRACT_SHA256 if mode_flags else CHECKSUM_CONTRACT_SHA256 if checksum else POLICY3_CONTRACT_SHA256
    label = "SHA-256" if avb_sha256 else "metadata mode-flags" if mode_flags else "checksum"
    require(digest is not None, label + " construction is unbound; missing actual complete base")
    raw = reader.read(ROOT / record)
    require(metadata.identity(raw)["sha256"] == digest,
            "maintained construction successor contract changed; review a new binding")
    require(selected == raw, "construction successor selector differs from the maintained contract")
    contract = _avb_sha256_contract(raw) if avb_sha256 else _mode_flags_contract(raw) if mode_flags else _checksum_contract(raw) if checksum else _policy3_contract(raw)
    reader.recheck()
    return contract, metadata.identity(raw)


def _derive_policy3_board(raw, contract):
    require(type(raw) is bytes and metadata.identity(raw) == contract["board_before"]
            and raw.count(BLOCK) == 1 and b"rom-construction" not in raw,
            "policy3 construction requires the exact future delivery Board predecessor")
    result = raw.replace(BLOCK, INCLUDE, 1)
    require(metadata.identity(result) == contract["board_after"], "policy3 construction Board derivation differs")
    return result


def derive_board(raw, contract_path=None):
    if contract_path is None:
        return _v1_derive_board(raw)
    contract, _ = load_contract(contract_path)
    if contract["contract_id"] == AVB_SHA256_CONTRACT_ID:
        old, _ = load_contract(ROOT / MODE_FLAGS_CONTRACT)
        result = _derive_policy3_board(raw, old) + AVB_SHA256_BLOCK
        require(metadata.identity(result) == contract["board_after"],
                "SHA-256 construction Board derivation differs")
        return result
    return (_derive_policy3_board(raw, contract)
            if contract["contract_id"] in (POLICY3_CONTRACT_ID, CHECKSUM_CONTRACT_ID, MODE_FLAGS_CONTRACT_ID) else _v1_derive_board(raw))


def _restore_policy3_board(raw, contract):
    require(type(raw) is bytes and metadata.identity(raw) == contract["board_after"]
            and raw.count(INCLUDE) == 1 and BLOCK not in raw, "policy3 construction Board bytes differ")
    result = raw.replace(INCLUDE, BLOCK, 1)
    require(_derive_policy3_board(result, contract) == raw, "policy3 Board changed outside its exact derivation")
    return result


def restore_board(raw, contract_path=None):
    if contract_path is None:
        return _v1_restore_board(raw)
    contract, _ = load_contract(contract_path)
    if contract["contract_id"] == AVB_SHA256_CONTRACT_ID:
        require(type(raw) is bytes and metadata.identity(raw) == contract["board_after"]
                and raw.endswith(AVB_SHA256_BLOCK) and raw.count(AVB_SHA256_BLOCK) == 1,
                "SHA-256 construction Board bytes differ")
        old, _ = load_contract(ROOT / MODE_FLAGS_CONTRACT)
        result = _restore_policy3_board(raw[:-len(AVB_SHA256_BLOCK)], old)
        require(derive_board(result, contract_path) == raw,
                "SHA-256 Board changed outside its exact derivation")
        return result
    return (_restore_policy3_board(raw, contract)
            if contract["contract_id"] in (POLICY3_CONTRACT_ID, CHECKSUM_CONTRACT_ID, MODE_FLAGS_CONTRACT_ID) else _v1_restore_board(raw))


def _check_policy3_base(plan, payloads, contract):
    require(BINDING not in plan and GUARD not in payloads, "construction source capability selected twice")
    require(plan.get("files") == file_entries(payloads), "base source bytes differ from their admission")
    require(metadata.identity(metadata.encoded(plan)) == contract["base_admission"],
            "policy3 construction requires the complete exact selected base admission")
    delivery = plan.get("target_files_metadata", {}).get("policy_image_delivery", {}).get("contract")
    require(metadata.encoded(delivery) == metadata.encoded(contract["selected_policy_image_contract"]),
            "policy3 complete base uses a different image delivery contract")
    if contract["contract_id"] in (CHECKSUM_CONTRACT_ID, MODE_FLAGS_CONTRACT_ID, AVB_SHA256_CONTRACT_ID):
        if __package__:
            from . import target_files_metadata_checksum as checksum
        else:
            import target_files_metadata_checksum as checksum
        selected = plan["target_files_metadata"]
        require(metadata.encoded(selected.get("source_contract")) == metadata.encoded(CHECKSUM_SOURCE_CONTRACT),
                "checksum complete base uses a different metadata source selector")
        composition = checksum.compose_sources(ROOT, source_contract=CHECKSUM_SOURCE_CONTRACT["path"])
        composition_id = metadata.identity(metadata.encoded(composition))
        require(metadata.encoded(selected.get("native_source")) == metadata.encoded(composition)
                and selected.get("composition_identity") == composition_id,
                "checksum complete base uses a different complete source composition")
        native_source = {"project_commit": composition["project"]["commit"],
                         "files": composition["final_source_files"], "composition": composition,
                         "composition_identity": composition_id}
        require(metadata.encoded(plan.get("mi_ext_inputs", {}).get("native_source")) == metadata.encoded(native_source),
                "checksum complete base requires the matching mi_ext source composition")


def apply(plan, payloads, contract_path):
    contract, identity = load_contract(contract_path)
    if contract["contract_id"] not in (POLICY3_CONTRACT_ID, CHECKSUM_CONTRACT_ID, MODE_FLAGS_CONTRACT_ID, AVB_SHA256_CONTRACT_ID):
        return _v1_apply(plan, payloads, contract_path)
    _check_policy3_base(plan, payloads, contract)
    result, files = copy.deepcopy(plan), dict(payloads)
    files[BOARD] = (derive_board(files[BOARD], contract_path)
                    if contract["contract_id"] == AVB_SHA256_CONTRACT_ID
                    else _derive_policy3_board(files[BOARD], contract))
    files[GUARD] = render_guard()
    result[BINDING] = {"contract": identity, "contract_id": contract["contract_id"],
                       "base_admission": contract["base_admission"], "scope": copy.deepcopy(contract["scope"])}
    result["files"] = file_entries(files)
    validate(result, files)
    return result, files


def validate(plan, payloads):
    binding = plan.get(BINDING)
    if type(binding) is not dict or binding.get("contract_id") not in (POLICY3_CONTRACT_ID, CHECKSUM_CONTRACT_ID, MODE_FLAGS_CONTRACT_ID, AVB_SHA256_CONTRACT_ID):
        return _v1_validate(plan, payloads)
    record = (AVB_SHA256_CONTRACT if binding["contract_id"] == AVB_SHA256_CONTRACT_ID
              else MODE_FLAGS_CONTRACT if binding["contract_id"] == MODE_FLAGS_CONTRACT_ID
              else CHECKSUM_CONTRACT if binding["contract_id"] == CHECKSUM_CONTRACT_ID else POLICY3_CONTRACT)
    contract, identity = load_contract(ROOT / record)
    expected = {"contract": identity, "contract_id": contract["contract_id"],
                "base_admission": contract["base_admission"], "scope": contract["scope"]}
    require(metadata.encoded(binding) == metadata.encoded(expected),
            "policy3 construction admission differs from the maintained capability")
    require(plan.get("files") == file_entries(payloads) and payloads.get(GUARD) == render_guard(),
            "policy3 source files or unchanged construction guard differ")
    base, files = copy.deepcopy(plan), dict(payloads)
    del base[BINDING]
    del files[GUARD]
    files[BOARD] = (restore_board(files[BOARD], ROOT / record)
                    if binding["contract_id"] == AVB_SHA256_CONTRACT_ID
                    else _restore_policy3_board(files[BOARD], contract))
    base["files"] = file_entries(files)
    _check_policy3_base(base, files, contract)
    return base


# Explicit build-variant opt-in successor. The maintained user-only guard above
# and every earlier contract stay unchanged. This derives one guard that keeps
# `user` as the default and admits `userdebug` only when the native invocation
# also sets NEZHA_BUILD_VARIANT_OPT_IN=userdebug; `eng` is never admitted.
# Selecting it is a source change for the build guest, not a build or flash.
VARIANT_OPT_IN_CONTRACT = "config/nezha-rom-construction-variant-opt-in-v1.json"
VARIANT_OPT_IN_CONTRACT_ID = "nezha-first-target-files-variant-opt-in-v1"
VARIANT_OPT_IN_CONTRACT_SHA256 = "0fae7659863f195a9246cd003e7055a524c98def5037c69ee2d8109fcf1750cf"
VARIANT_OPT_IN_ENV = "NEZHA_BUILD_VARIANT_OPT_IN"
VARIANT_DEFAULT = "user"
VARIANTS = ("user", "userdebug")
USER_ONLY_CLAUSE = ("ifneq ($(TARGET_BUILD_VARIANT),user)\n"
                    "$(error Nezha first construction requires the user variant)\n"
                    "endif\n")
VARIANT_OPT_IN_CLAUSE = (
    "ifneq ($(TARGET_BUILD_VARIANT),user)\n"
    "ifneq ($(TARGET_BUILD_VARIANT)/$(NEZHA_BUILD_VARIANT_OPT_IN),userdebug/userdebug)\n"
    "$(error Nezha first construction requires the user variant unless NEZHA_BUILD_VARIANT_OPT_IN=userdebug explicitly selects userdebug; eng is never admitted)\n"
    "endif\n"
    "endif\n")
VARIANT_OPT_IN_GUARD_ID = {"sha256": "a6ae5a08ef2d21ea30d98e589ad4ce49697dbcc613d0bd7365b962a3c99137a3", "size_bytes": 2737}


def render_variant_opt_in_guard():
    """The maintained guard with only its variant clause widened to the opt-in form."""
    base = render_guard().decode("ascii")
    require(base.count(USER_ONLY_CLAUSE) == 1, "maintained guard lost its exact user-only clause")
    raw = base.replace(USER_ONLY_CLAUSE, VARIANT_OPT_IN_CLAUSE, 1).encode("ascii")
    require(metadata.identity(raw) == VARIANT_OPT_IN_GUARD_ID, "variant opt-in guard changed")
    return raw


def variant_environment(variant=VARIANT_DEFAULT):
    """Environment the native runner must add; userdebug needs the explicit opt-in key."""
    require(variant in VARIANTS, "build variant must be exactly user or userdebug; eng is not admitted")
    env = {"TARGET_BUILD_VARIANT": variant}
    if variant != VARIANT_DEFAULT:
        env[VARIANT_OPT_IN_ENV] = variant
    return env


def load_variant_opt_in_contract(path=None):
    reader = metadata.Reader()
    raw = reader.read(ROOT / VARIANT_OPT_IN_CONTRACT)
    require(metadata.identity(raw)["sha256"] == VARIANT_OPT_IN_CONTRACT_SHA256,
            "maintained variant opt-in contract changed; review a new binding")
    if path is not None:
        require(reader.read(path) == raw, "variant opt-in selector differs from the maintained contract")
    value = metadata._json(raw)
    require(type(value) is dict and value.get("schema_version") == 1 and type(value["schema_version"]) is int
            and value.get("contract_id") == VARIANT_OPT_IN_CONTRACT_ID
            and value.get("predecessor") == {"contract_id": CONTRACT_ID, "guard": GUARD_ID}
            and value.get("guard") == VARIANT_OPT_IN_GUARD_ID
            and value.get("environment_key") == VARIANT_OPT_IN_ENV
            and value.get("default_variant") == VARIANT_DEFAULT
            and value.get("admitted_variants") == list(VARIANTS)
            and value.get("rejected_variants") == ["eng"]
            and value.get("metadata_selection", {}).get("before") == METADATA_SELECTION_BEFORE
            and value.get("metadata_selection", {}).get("after") == METADATA_SELECTION_AFTER
            and value.get("product_selection", {}).get("installed") == PRODUCT_SELECTION_INEFFECTIVE
            and value.get("product_selection", {}).get("restored") == PRODUCT_SELECTION_RESTORED
            and value.get("common_selection", {}).get("before") == COMMON_SELECTION_BEFORE
            and value.get("common_selection", {}).get("after") == COMMON_SELECTION_AFTER,
            "variant opt-in contract identity differs")
    reader.recheck()
    return value, metadata.identity(raw)


# The same opt-in also relaxes the prebuilt target-files metadata delivery for the
# userdebug diagnostic build only. That delivery's policy gate pins the exact
# platform SELinux policy the delivered vendor/ODM policy images were verified
# against, which a userdebug platform policy can never satisfy. The derived
# selection keeps the full delivery for user and skips it only for the explicit
# userdebug/userdebug pair; init then compiles policy at boot on that build.
METADATA_SELECTION = "device/xiaomi/nezha/generated/target-files-metadata.mk"
METADATA_SELECTION_HEAD = "# Explicit policy-image metadata delivery; actual packaged-policy checks remain required.\n"
METADATA_SELECTION_BEFORE = {"sha256": "bbf310ccc732bc68bb4ba330c75a3ded899174ff268b0b45ee8aa16ce1289bf8", "size_bytes": 351}
METADATA_SELECTION_AFTER = {"sha256": "615b7ed98c72acf4a2195c2892117ebcc044b41e4732cbab580384d80f35a75c", "size_bytes": 791}
METADATA_SELECTION_EXCEPTION = (
    "# Variant opt-in exception: an explicitly selected userdebug diagnostic build skips the\n"
    "# prebuilt metadata delivery because its framework SELinux policy differs from the policy\n"
    "# the delivered vendor/ODM policy images were verified against; init compiles policy at\n"
    "# boot instead. The default user variant keeps the full delivery and its policy gate.\n"
    "ifneq ($(TARGET_BUILD_VARIANT)/$(NEZHA_BUILD_VARIANT_OPT_IN),userdebug/userdebug)\n")


def derive_metadata_selection(raw):
    """Wrap the exact installed selection in the opt-in conditional; nothing else changes."""
    require(type(raw) is bytes and metadata.identity(raw) == METADATA_SELECTION_BEFORE
            and raw.startswith(METADATA_SELECTION_HEAD.encode("ascii"))
            and raw.count(b"BOARD_NEZHA_PREBUILT_METADATA := true\n") == 1 and b"ifneq" not in raw,
            "metadata selection requires the exact delivered predecessor")
    result = (METADATA_SELECTION_HEAD + METADATA_SELECTION_EXCEPTION).encode("ascii") + raw[len(METADATA_SELECTION_HEAD):] + b"endif\n"
    require(metadata.identity(result) == METADATA_SELECTION_AFTER, "metadata selection derivation differs")
    return result


# The opt-in also restores adb root on the userdebug diagnostic build. Lineage's
# common product config sets PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG for userdebug and
# the build exports it with add_json_bool, which treats any non-empty value,
# including "false", as set; gen_build_prop then emits ro.debuggable=0. The only
# effective override leaves the variable unset, so the derivation wraps the
# assignment in the common config itself for the explicit userdebug/userdebug pair
# and restores the device product, whose ":= false" override from the third guest
# transaction never had an effect.
PRODUCT_SELECTION = "device/xiaomi/nezha/lineage_nezha.mk"
PRODUCT_SELECTION_ANCHOR = "$(call inherit-product, device/xiaomi/nezha/device.mk)\n"
PRODUCT_SELECTION_RESTORED = {"sha256": "b53dc7f36a63ec4db1f5ec134eaab58b836d07f2524944d9db0440737e98d4bf", "size_bytes": 1193}
PRODUCT_SELECTION_INEFFECTIVE = {"sha256": "f9955fd70c79a512f2bdf947e3132b99caee1d1f5c974d95d81dfd56ba91760c", "size_bytes": 1561}
PRODUCT_SELECTION_INEFFECTIVE_OVERRIDE = (
    "# Variant opt-in exception: the explicit userdebug diagnostic build restores\n"
    "# ro.debuggable=1 so adb root works; Lineage's common config otherwise sets\n"
    "# PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG for userdebug. The user build is unchanged.\n"
    "ifeq ($(TARGET_BUILD_VARIANT)/$(NEZHA_BUILD_VARIANT_OPT_IN),userdebug/userdebug)\n"
    "PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG := false\n"
    "endif\n\n")


def restore_product_selection(raw):
    """Remove the ineffective override again; the product returns to its merged predecessor."""
    marker = (PRODUCT_SELECTION_INEFFECTIVE_OVERRIDE + PRODUCT_SELECTION_ANCHOR).encode("ascii")
    require(type(raw) is bytes and metadata.identity(raw) == PRODUCT_SELECTION_INEFFECTIVE and raw.count(marker) == 1,
            "product restore requires the exact installed override")
    result = raw.replace(marker, PRODUCT_SELECTION_ANCHOR.encode("ascii"), 1)
    require(metadata.identity(result) == PRODUCT_SELECTION_RESTORED and b"PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG" not in result,
            "product restore derivation differs")
    return result


COMMON_SELECTION = "vendor/lineage/config/common.mk"
COMMON_SELECTION_SNAPSHOT = "research/source-snapshots/lineage-config-common-20260906.mk"
COMMON_SELECTION_ASSIGNMENT = "# Set ro.debuggable=0 for userdebug\nPRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG := true\n"
COMMON_SELECTION_BEFORE = {"sha256": "2747b367f0a0bc4f758b31ee88833cbb829a24be8a74e3ff9b11bbbae75a36ca", "size_bytes": 10468}
COMMON_SELECTION_AFTER = {"sha256": "38ac0f283b5dd41812fc4efc922ae4afb4a4f383b16429f7f7faa9c4164d99bf", "size_bytes": 10789}
COMMON_SELECTION_EXCEPTION = (
    "# Set ro.debuggable=0 for userdebug\n"
    "# Variant opt-in exception (nezha): the explicitly selected userdebug diagnostic\n"
    "# build leaves this unset so ro.debuggable=1 and adb root work; add_json_bool\n"
    "# treats any non-empty value, including false, as set. user is unchanged.\n"
    "ifneq ($(TARGET_BUILD_VARIANT)/$(NEZHA_BUILD_VARIANT_OPT_IN),userdebug/userdebug)\n"
    "PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG := true\n"
    "endif\n")


def derive_common_selection(raw):
    """Wrap the single assignment in the opt-in conditional; nothing else in the common config changes."""
    assignment = COMMON_SELECTION_ASSIGNMENT.encode("ascii")
    require(type(raw) is bytes and metadata.identity(raw) == COMMON_SELECTION_BEFORE and raw.count(assignment) == 1
            and raw.count(b"PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG") == 1 and b"NEZHA_BUILD_VARIANT_OPT_IN" not in raw,
            "common selection requires the exact installed predecessor")
    result = raw.replace(assignment, COMMON_SELECTION_EXCEPTION.encode("ascii"), 1)
    require(metadata.identity(result) == COMMON_SELECTION_AFTER, "common selection derivation differs")
    return result
