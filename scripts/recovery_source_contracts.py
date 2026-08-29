"""Explicit composition of reviewed recovery and custom-image source patches.

The original recovery contract remains the 0005-only contract. This optional
path binds the ordered 0005/0006/0007 changes and their complete final source
bytes, without applying patches, changing files, or admitting a ROM build.
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


def compose(root, selected_contract, *, expected_base=None, expected_base_identity=None):
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
