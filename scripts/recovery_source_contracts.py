"""Explicit composition of reviewed recovery and custom-image source patches.

The original recovery contract remains the 0005-only contract. The optional
paths bind 0005/0006/0007, its explicit 0010 readonly follow-up, or the separate
0005/0006/0007/0008/0009 metadata composition. A separate combined selection
adds the reviewed 0010 initialization and 0011 VINTF shipping-API follow-ups.
An explicit checksum successor adds only the reviewed 0023 Makefile change.
Each route binds its complete final source bytes without applying patches or
admitting a ROM build.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re

if __package__:
    from .kernel_inputs import _json, _read
else:
    from kernel_inputs import _json, _read


BASE_PATH = "patches/evolution/prebuilt-recovery.json"
BASE_PATCH = "patches/evolution/0005-verified-prebuilt-recovery.patch"
PACKAGING_PATH = "patches/evolution/ab-only-recovery-packaging.json"
PACKAGING_PATCH = "patches/evolution/0006-ab-only-recovery-packaging.patch"
COMPOSED_PATH = "patches/evolution/direct-avb-custom-images.json"
COMPOSED_PATCH = "patches/evolution/0007-direct-avb-custom-images.patch"
METADATA_PATH = "patches/evolution/target-files-metadata.json"
METADATA_ID = "nezha-prebuilt-target-files-metadata-v1"
TARGET_FILES_PATH = "patches/evolution/target-files-source-composition.json"
TARGET_FILES_ID = "nezha-target-files-source-composition-v1"
CHECKSUM_PATH = "patches/evolution/target-files-metadata-checksum.json"
CHECKSUM_ID = "nezha-target-files-metadata-checksum-v1"
READONLY_PATH = "patches/evolution/direct-avb-readonly.json"
READONLY_PATCH = "patches/evolution/0010-initialize-direct-avb-readonly.patch"
READONLY_ID = "nezha-direct-avb-readonly-v1"
PRODUCT_PATH = "build/make/core/product.mk"
RECOVERY_TEMPLATE = "device/xiaomi/nezha/recovery-prebuilt.mk"
CORE_PATH = "build/make/core/Makefile"
ADD_IMG_PATH = "build/make/tools/releasetools/add_img_to_target_files.py"
COMMON_PATH = "build/make/tools/releasetools/common.py"
PROJECT = {"path": "build/make", "commit": "a438ca40c6ed779042f806142b1165ba1360a7b2",
           "repository": "https://github.com/Evolution-X/build", "branch": "bka"}
SEMANTIC_PATHS = {
    BASE_PATH: (COMMON_PATH,),
    PACKAGING_PATH: (CORE_PATH, COMMON_PATH,
                     "build/make/tools/releasetools/non_ab_ota.py",
                     "build/make/tools/releasetools/ota_from_target_files.py"),
    COMPOSED_PATH: (COMMON_PATH, "build/make/tools/releasetools/build_super_image.py",
                    "build/make/tools/releasetools/validate_target_files.py"),
    READONLY_PATH: (PRODUCT_PATH,),
}
READONLY_SCOPE = {
    "source_patch_applied": False, "native_kati_verified": False,
    "native_image_copy_verified": False, "target_files_verified": False,
    "complete_rom_admitted": False, "original_prebuilt_bytes_changed": False,
    "incoming_override_guard_relaxed": False, "phone_operations": [],
}
MAX_BYTES = 4 * 1024 * 1024


class RecoverySourceError(ValueError):
    """A source composition differs from the explicit reviewed patch chain."""


def _require(condition, message):
    if not condition:
        raise RecoverySourceError(message)


def _identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def _canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _valid_identity(value):
    return (type(value) is dict and set(value) == {"sha256", "size_bytes"}
            and type(value["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
            and type(value["size_bytes"]) is int and 0 < value["size_bytes"] <= MAX_BYTES)


def _row(row):
    _require(type(row) is dict and type(row.get("path")) is str,
             "invalid composed source row")
    result = {key: row.get(key) for key in ("sha256", "size_bytes")}
    _require(_valid_identity(result), "invalid composed source identity")
    return {"path": row["path"], **result}


def _load(root, path, patch_path, changed_path, contract_id=None):
    raw = _read(root / path, limit=MAX_BYTES)
    record = _json(raw)
    _require(type(record.get("schema_version")) is int and record["schema_version"] == 1
             and record.get("project") == PROJECT,
             "composition must retain the exact pinned build project")
    if contract_id is not None:
        _require(record.get("contract_id") == contract_id, "unexpected source composition contract")
    patch = record.get("patch")
    _require(type(patch) is dict and patch.get("path") == patch_path
             and _valid_identity({key: patch.get(key) for key in ("sha256", "size_bytes")}),
             "unexpected composed patch")
    patch_bytes = _read(root / patch_path, limit=MAX_BYTES)
    _require(_identity(patch_bytes) == {key: patch[key] for key in ("sha256", "size_bytes")},
             "composed patch bytes differ from their contract")
    relative = changed_path.removeprefix("build/make/")
    headers = re.findall(rb"^diff --git a/(\S+) b/(\S+)\n", patch_bytes, re.M)
    _require(headers == [(relative.encode(), relative.encode())],
             "composed patch must change only its declared source file")
    source_files = record.get("source_files")
    _require(type(source_files) is list and len(source_files) == 1
             and type(source_files[0]) is dict and source_files[0].get("path") == changed_path
             and _valid_identity(source_files[0].get("before"))
             and _valid_identity(source_files[0].get("after"))
             and source_files[0]["before"] != source_files[0]["after"],
             "invalid composed patch source transition")
    semantics = record.get("semantic_files")
    _require(type(semantics) is list and all(type(row) is dict for row in semantics)
             and [row.get("path") for row in semantics] == list(SEMANTIC_PATHS[path]),
             "missing, duplicate or unreviewed composed semantic source")
    for row in semantics:
        _row(row)
    return record, {"path": path, **_identity(raw)}


def _compose_legacy(root, selected_contract, *, expected_base=None, expected_base_identity=None):
    """Select the complete 0005 + 0006 + 0007 source identity explicitly."""
    root = Path(root)
    selected = _read(Path(selected_contract), limit=MAX_BYTES)
    canonical = _read(root / COMPOSED_PATH, limit=MAX_BYTES)
    _require(selected == canonical, "explicit composition differs from the current reviewed contract")
    base, base_ref = _load(root, BASE_PATH, BASE_PATCH, CORE_PATH)
    packaging, packaging_ref = _load(root, PACKAGING_PATH, PACKAGING_PATCH, ADD_IMG_PATH,
                                     "nezha-ab-only-recovery-packaging-v1")
    extra, extra_ref = _load(root, COMPOSED_PATH, COMPOSED_PATCH, CORE_PATH,
                            "nezha-direct-avb-custom-images-v1")
    if expected_base is not None:
        _require(base == expected_base and {key: base_ref[key] for key in ("sha256", "size_bytes")} ==
                 expected_base_identity, "base recovery contract changed during composition")
    _require(packaging.get("requires_patch") == BASE_PATCH and extra.get("requires_patch") == BASE_PATCH,
             "composition must preserve the prebuilt recovery prerequisite")
    first, last = base["source_files"][0], extra["source_files"][0]
    _require(first["after"] == last["before"], "0007 must follow the exact 0005 core output")
    _require(packaging["semantic_files"][0] == {"path": CORE_PATH, **first["after"]},
             "0006 semantic core must be the recorded 0005 output")
    consumers = extra.get("composed_semantic_files")
    _require(type(consumers) is list and len(consumers) == 1
             and type(consumers[0]) is dict and consumers[0].get("path") == ADD_IMG_PATH
             and consumers[0].get("requires_patch") == PACKAGING_PATCH
             and _row(consumers[0]) == {"path": ADD_IMG_PATH, **packaging["source_files"][0]["after"]},
             "0007 requires the exact reviewed A/B packaging consumer")

    final_rows = {CORE_PATH: {"path": CORE_PATH, **last["after"]},
                  ADD_IMG_PATH: {"path": ADD_IMG_PATH, **packaging["source_files"][0]["after"]}}
    for record in (base, packaging, extra):
        for row in record["semantic_files"]:
            if row["path"] == CORE_PATH:
                continue  # The exact intermediate core was checked above.
            normalized = _row(row)
            _require(row["path"] not in final_rows or final_rows[row["path"]] == normalized,
                     "composed semantic source identities conflict")
            final_rows[row["path"]] = normalized
    composition = {
        "schema_version": 1, "project": copy.deepcopy(PROJECT),
        "contracts": [base_ref, packaging_ref, extra_ref],
        "ordered_patches": [copy.deepcopy(record["patch"]) for record in (base, packaging, extra)],
        "core_transitions": [copy.deepcopy(first), copy.deepcopy(last)],
        "final_source_files": [final_rows[path] for path in sorted(final_rows)],
        "patches_applied_by_this_tool": False, "whole_source_tree_verified": False,
    }
    identity = _identity(_canonical(composition))
    result = copy.deepcopy(base)
    result["source_files"][0]["after"] = copy.deepcopy(last["after"])
    result["semantic_files"] = [final_rows[path] for path in sorted(final_rows) if path != CORE_PATH]
    result["composition"] = composition
    result["composition_identity"] = identity
    return result, identity


def _compose_readonly(root, selected, *, expected_base=None, expected_base_identity=None):
    _require(selected == _read(root / READONLY_PATH, limit=MAX_BYTES),
             "explicit readonly composition differs from the current reviewed contract")
    legacy, legacy_identity = _compose_legacy(root, root / COMPOSED_PATH,
                                             expected_base=expected_base,
                                             expected_base_identity=expected_base_identity)
    extension, reference = _load(root, READONLY_PATH, READONLY_PATCH, CORE_PATH, READONLY_ID)
    previous = legacy["composition"]
    _require(extension.get("predecessor_composition") == legacy_identity
             and extension.get("required_predecessor_contracts") == previous["contracts"],
             "readonly initialization requires the exact base 0005/0006/0007 composition")
    transition = extension["source_files"][0]
    _require(transition["before"] == legacy["source_files"][0]["after"],
             "readonly initialization must follow the exact 0007 core output")
    _require(extension.get("readonly_macro") == {
        "name": "readonly-variables", "source": PRODUCT_PATH,
        "body_sha256": "1169e184965a0352a1b2f3b13d5aad83fca34edac18c67f488dd41c74b425bdb",
    }, "readonly initialization must use the reviewed product macro")
    _require(_canonical(extension.get("semantics")) == _canonical({
        "incoming_definitions_rejected_before_initialization": True,
        "undefined_settings_initialized_to_empty": True, "existing_derived_values_preserved": True,
        "all_selected_settings_frozen": True, "no_flashall_default": "",
        "empty_signing_fields_emitted_to_misc_info": False,
        "direct_vbmeta_descriptor_preserved": True, "readiness_flags_changed": False,
    }) and _canonical(extension.get("scope")) == _canonical(READONLY_SCOPE),
             "readonly initialization changes its reviewed semantics or admission scope")
    rows = {row["path"]: copy.deepcopy(row) for row in previous["final_source_files"]}
    rows[CORE_PATH] = {"path": CORE_PATH, **transition["after"]}
    for row in extension["semantic_files"]:
        normalized = _row(row)
        _require(row["path"] not in rows or rows[row["path"]] == normalized,
                 "readonly macro source conflicts with the predecessor composition")
        rows[row["path"]] = normalized
    composition = copy.deepcopy(previous)
    composition["contracts"].append(reference)
    composition["ordered_patches"].append(copy.deepcopy(extension["patch"]))
    composition["core_transitions"].append(copy.deepcopy(transition))
    composition["final_source_files"] = [rows[path] for path in sorted(rows)]
    result = copy.deepcopy(legacy)
    result["source_files"][0]["after"] = copy.deepcopy(transition["after"])
    result["semantic_files"] = [rows[path] for path in sorted(rows) if path != CORE_PATH]
    result["composition"] = composition
    identity = _identity(_canonical(composition))
    result["composition_identity"] = identity
    _require(selected == _read(root / READONLY_PATH, limit=MAX_BYTES),
             "readonly source contract changed during selection")
    return result, identity


def compose(root, selected_contract, *, expected_base=None, expected_base_identity=None):
    """Select one exact reviewed composition; never infer it from source hashes."""
    root = Path(root)
    selected = _read(Path(selected_contract), limit=MAX_BYTES)
    record = _json(selected)
    if record.get("contract_id") == READONLY_ID:
        return _compose_readonly(root, selected, expected_base=expected_base,
                                 expected_base_identity=expected_base_identity)
    if record.get("contract_id") == TARGET_FILES_ID:
        return _compose_target_files(root, selected, expected_base=expected_base,
                                     expected_base_identity=expected_base_identity)
    if record.get("contract_id") == CHECKSUM_ID:
        return _compose_target_files(root, selected, expected_base=expected_base,
                                     expected_base_identity=expected_base_identity, checksum=True)
    if record.get("contract_id") != METADATA_ID:
        # This keeps the original validation and serialized result unchanged.
        return _compose_legacy(root, selected_contract, expected_base=expected_base,
                               expected_base_identity=expected_base_identity)
    _require(selected == _read(root / METADATA_PATH, limit=MAX_BYTES),
             "explicit metadata composition differs from the current reviewed contract")
    legacy, _ = _compose_legacy(root, root / COMPOSED_PATH,
                               expected_base=expected_base,
                               expected_base_identity=expected_base_identity)
    if __package__:
        from . import target_files_metadata
    else:
        import target_files_metadata
    try:
        composition = target_files_metadata.compose_sources(root)
    except target_files_metadata.TargetFilesMetadataError as exc:
        raise RecoverySourceError("metadata source composition refused: " + str(exc)) from exc
    _require(composition["contracts"][:3] == legacy["composition"]["contracts"]
             and composition["ordered_patches"][:3] == legacy["composition"]["ordered_patches"],
             "metadata composition must preserve the reviewed recovery predecessors")
    rows = composition["final_source_files"]
    core = next(row for row in rows if row["path"] == CORE_PATH)
    result = copy.deepcopy(legacy)
    result["source_files"][0]["after"] = {key: core[key] for key in ("sha256", "size_bytes")}
    result["semantic_files"] = [row for row in rows if row["path"] != CORE_PATH]
    result["composition"] = composition
    identity = _identity(_canonical(composition))
    result["composition_identity"] = identity
    _require(selected == _read(root / METADATA_PATH, limit=MAX_BYTES),
             "metadata composition contract changed during selection")
    return result, identity


def _compose_target_files(root, selected, *, expected_base=None, expected_base_identity=None, checksum=False):
    """Admit the explicit combined composition or its checksum-only successor."""
    selected_path = CHECKSUM_PATH if checksum else TARGET_FILES_PATH
    _require(selected == _read(root / selected_path, limit=MAX_BYTES),
             "explicit target-files composition differs from the current reviewed contract")
    legacy, _ = _compose_legacy(root, root / COMPOSED_PATH,
                               expected_base=expected_base,
                               expected_base_identity=expected_base_identity)
    if checksum:
        if __package__:
            from . import target_files_metadata_checksum
        else:
            import target_files_metadata_checksum
        try:
            composition = target_files_metadata_checksum.compose_sources(root, source_contract=selected_path)
        except target_files_metadata_checksum.TargetFilesMetadataError as exc:
            raise RecoverySourceError("target-files checksum source composition refused: " + str(exc)) from exc
    else:
        if __package__:
            from . import target_files_source_composition
        else:
            import target_files_source_composition
        try:
            composition = target_files_source_composition.compose_sources(root)
        except target_files_source_composition.TargetFilesSourceCompositionError as exc:
            raise RecoverySourceError("target-files source composition refused: " + str(exc)) from exc
    _require(composition["contracts"][:3] == legacy["composition"]["contracts"]
             and composition["ordered_patches"][:3] == legacy["composition"]["ordered_patches"]
             and composition["contracts"][-1] == {"path": selected_path, **_identity(selected)},
             "target-files composition must preserve the reviewed recovery predecessors and selector")
    rows = composition["final_source_files"]
    core = next(row for row in rows if row["path"] == CORE_PATH)
    result = copy.deepcopy(legacy)
    result["source_files"][0]["after"] = {key: core[key] for key in ("sha256", "size_bytes")}
    result["semantic_files"] = [row for row in rows if row["path"] != CORE_PATH]
    result["composition"] = composition
    identity = _identity(_canonical(composition))
    result["composition_identity"] = identity
    _require(selected == _read(root / selected_path, limit=MAX_BYTES),
             "target-files composition contract changed during selection")
    return result, identity


def render_metadata_recovery_include(template, *, root, selected_contract):
    """Render only the explicit metadata recovery variant from the legacy file.

    The authored template and its default renderings remain byte-for-byte
    unchanged. The selected variant retains every recovery/AVB/A-B mode guard
    and replaces only the source-composition and source-file checks.
    """
    return _render_recovery_include(template, root=root, selected_contract=selected_contract,
                                    metadata=True)


def render_readonly_recovery_include(template, *, root, selected_contract):
    """Select the base 0005/0006/0007/0010 variant without adopting metadata."""
    return _render_recovery_include(template, root=root, selected_contract=selected_contract,
                                    metadata=False)


def render_target_files_recovery_include(template, *, root, selected_contract):
    """Select the combined source guard, optionally its checksum successor."""
    return _render_recovery_include(template, root=root, selected_contract=selected_contract,
                                    metadata=True, target_files=True)


def _render_recovery_include(template, *, root, selected_contract, metadata, target_files=False):
    root = Path(root)
    label = "metadata" if metadata else "readonly initialization"
    ordered = "0005/0006/0007/0008/0009" if metadata else "0005/0006/0007/0010"
    last_patch = "0009" if metadata else "0010"
    expected_path = METADATA_PATH if metadata else READONLY_PATH
    if target_files:
        label = "target-files source"
        ordered = "0005/0006/0007/0008/0009/0010/0011"
        last_patch = "0009/0010"
        expected_path = TARGET_FILES_PATH
    _require(type(template) is bytes and template == _read(root / RECOVERY_TEMPLATE, limit=MAX_BYTES),
             f"{label} recovery rendering requires the unchanged authored template")
    source, identity = compose(root, selected_contract)
    if target_files and source["composition"]["contracts"][-1]["path"] == CHECKSUM_PATH:
        ordered += "/0023"
        last_patch = "0023"
        expected_path = CHECKSUM_PATH
    _require(source["composition"]["contracts"][-1]["path"] == expected_path,
             f"{label} recovery rendering requires explicit {label} composition")
    core = source["source_files"][0]["after"]
    text = template.decode("ascii")

    def replace_between(start, end, replacement):
        nonlocal text
        _require(text.count(start) == 1 and text.count(end) == 1,
                 "authored recovery source guard boundaries differ")
        first, last = text.index(start), text.index(end)
        _require(first < last, "authored recovery source guard order differs")
        text = text[:first] + replacement + text[last:]

    selection = (
        f"# Explicit {label} composition; legacy bundles cannot select this variant.\n"
        "ifneq ($(origin NEZHA_RECOVERY_CORE_COMPOSITION_SHA256),file)\n"
        f"$(error Recovery {label} composition must come from the verified bundle include)\nendif\n"
        f"ifneq ($(value NEZHA_RECOVERY_CORE_COMPOSITION_SHA256),{identity['sha256']})\n"
        f"$(error Recovery {label} composition differs from reviewed {ordered} inputs)\nendif\n"
        f"ifneq ($(NEZHA_RECOVERY_CORE_SHA256),{core['sha256']})\n"
        f"$(error Recovery {label} input requires the exact reviewed {last_patch} build core)\nendif\n"
    )
    replace_between("ifeq ($(origin NEZHA_RECOVERY_CORE_COMPOSITION_SHA256),undefined)\n",
                    "ifneq ($(NEZHA_RECOVERY_PUBLIC_KEY_SHA256),", selection)
    checks = f"# Exact final source bytes for the explicitly selected {ordered} composition.\n"
    for row in source["composition"]["final_source_files"]:
        path = row["path"]
        checks += (
            f"ifneq ($(shell test -f {path} && test ! -L {path} && echo regular),regular)\n"
            f"$(error Recovery {label} composition requires a regular {path})\nendif\n"
            f"ifneq ($(strip $(shell wc -c < {path} 2>/dev/null)),{row['size_bytes']})\n"
            f"$(error Recovery {label} source size changed: {path})\nendif\n"
            f"ifneq ($(shell sha256sum < {path} 2>/dev/null | cut -d ' ' -f 1),{row['sha256']})\n"
            f"$(error Recovery {label} source bytes changed: {path})\nendif\n"
        )
    replace_between("# The upstream tree has no prebuilt-recovery selector.",
                    "ifneq ($(shell test -f vendor/xiaomi/nezha-recovery/recovery.img", checks)
    return text.encode("ascii")
