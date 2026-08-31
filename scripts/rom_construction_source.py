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
