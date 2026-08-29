#!/usr/bin/env python3
"""Verify the pinned A/B-only recovery packaging fix without building images.

The optional probe executes the actual verified Python recovery branch with
synthetic prebuilt bytes and stubbed image builders. It never imports a source
checkout, runs a native command, accesses a phone, or makes a target-files/OTA
admission. Source files are read only; temporary synthetic inputs are deleted.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import zipfile

if __package__:
    from .kernel_inputs import KernelInputsError, _json, _read
else:
    from kernel_inputs import KernelInputsError, _json, _read


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "patches/evolution/ab-only-recovery-packaging.json"
PATCH_PATH = "patches/evolution/0006-ab-only-recovery-packaging.patch"
EDIT_PATH = "build/make/tools/releasetools/add_img_to_target_files.py"
COMMON_PATH = "build/make/tools/releasetools/common.py"
OTA_PATH = "build/make/tools/releasetools/ota_from_target_files.py"
SEMANTIC_PATHS = (
    "build/make/core/Makefile", COMMON_PATH,
    "build/make/tools/releasetools/non_ab_ota.py", OTA_PATH,
)
PROJECT_COMMIT = "a438ca40c6ed779042f806142b1165ba1360a7b2"
MAX_SOURCE_BYTES = 1024 * 1024
SCOPE = {
    "python_recovery_branch_only": True, "full_target_files_verified": False,
    "ota_verified": False, "super_verified": False,
    "signed_rom_chain_verified": False, "phone_operations": [],
}


class RecoveryPackagingError(ValueError):
    """The reviewed source or a bounded recovery branch check mismatched."""


def _require(condition, message):
    if not condition:
        raise RecoveryPackagingError(message)


def _identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def _valid_identity(value):
    return (type(value) is dict and set(value) == {"sha256", "size_bytes"}
            and type(value["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
            and type(value["size_bytes"]) is int
            and 0 < value["size_bytes"] <= MAX_SOURCE_BYTES)


def _contract():
    raw = _read(ROOT / CONTRACT_PATH, limit=MAX_SOURCE_BYTES)
    record = _json(raw)
    _require(type(record.get("schema_version")) is int and record["schema_version"] == 1
             and record.get("contract_id") == "nezha-ab-only-recovery-packaging-v1",
             "unsupported recovery packaging contract")
    _require(record.get("project") == {
        "path": "build/make", "commit": PROJECT_COMMIT,
        "repository": "https://github.com/Evolution-X/build", "branch": "bka",
    }, "recovery packaging requires the reviewed bka build project")
    patch = record.get("patch")
    _require(type(patch) is dict and patch.get("path") == PATCH_PATH,
             "unexpected recovery packaging patch")
    _require(_identity(_read(ROOT / PATCH_PATH, limit=MAX_SOURCE_BYTES)) ==
             {key: patch.get(key) for key in ("sha256", "size_bytes")},
             "recovery packaging patch differs from its contract")
    changed = record.get("source_files")
    _require(type(changed) is list and len(changed) == 1
             and type(changed[0]) is dict and changed[0].get("path") == EDIT_PATH
             and _valid_identity(changed[0].get("before"))
             and _valid_identity(changed[0].get("after"))
             and changed[0]["before"] != changed[0]["after"],
             "expected only the reviewed add_img_to_target_files change")
    semantic = record.get("semantic_files")
    _require(type(semantic) is list and len(semantic) == len(SEMANTIC_PATHS)
             and all(type(row) is dict for row in semantic)
             and [row.get("path") for row in semantic] == list(SEMANTIC_PATHS)
             and all(_valid_identity({key: row.get(key) for key in ("sha256", "size_bytes")})
                     for row in semantic), "missing or changed semantic source list")
    _require(record.get("validation_scope") == SCOPE,
             "source verification must not promote ROM or OTA readiness")
    return record, _identity(raw)


def _source(source_tree, record):
    rows = [{"path": EDIT_PATH, **record["source_files"][0]["after"]},
            *record["semantic_files"]]
    data, checked = {}, []
    for row in rows:
        raw = _read(Path(source_tree) / row["path"], limit=MAX_SOURCE_BYTES)
        identity = _identity(raw)
        _require(identity == {key: row[key] for key in ("sha256", "size_bytes")},
                 "recovery packaging source differs: " + row["path"])
        data[row["path"]] = raw
        checked.append({"path": row["path"], **identity})
    return data, checked


def _selected_contract(composed_source_contract=None):
    record, identity = _contract()
    if composed_source_contract is not None:
        if __package__:
            from .recovery_source_contracts import compose
        else:
            from recovery_source_contracts import compose
        composed, composed_identity = compose(ROOT, composed_source_contract)
        refs = composed["composition"]["contracts"]
        _require(refs[1] == {"path": CONTRACT_PATH, **identity},
                 "A/B packaging contract changed during composition")
        rows = composed["composition"]["final_source_files"]
        _require(next(row for row in rows if row["path"] == EDIT_PATH) ==
                 {"path": EDIT_PATH, **record["source_files"][0]["after"]},
                 "composed A/B consumer differs")
        record = copy.deepcopy(record)
        record["semantic_files"] = [row for row in rows if row["path"] != EDIT_PATH]
        record["composition"] = composed["composition"]
        identity = composed_identity
    return record, identity


def check_source(source_tree, *, composed_source_contract=None):
    record, identity = _selected_contract(composed_source_contract)
    _, files = _source(source_tree, record)
    result = {"schema_version": 1, "status": "verified-source",
              "expected_build_commit": PROJECT_COMMIT, "contract": identity,
              "files": files, "whole_source_tree_verified": False,
              "source_modified": False, "scope": copy.deepcopy(SCOPE)}
    if "composition" in record:
        result["composition"] = copy.deepcopy(record["composition"])
    return result


def _function(source, name):
    functions = [node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name == name]
    _require(len(functions) == 1, "expected one source function: " + name)
    return functions[0]


def _load_function(source, name, namespace):
    node = _function(source, name)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, "<verified-recovery-source>", "exec"), namespace)
    return namespace[name]


def _recovery_branch(source):
    function = _function(source, "AddImagesToTargetFiles")
    candidates = [node for node in function.body
                  if isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                  and node.test.id == "has_recovery"]
    _require(len(candidates) == 1, "expected one actual recovery branch")
    module = ast.Module(body=candidates, type_ignores=[])
    return compile(module, "<verified-recovery-branch>", "exec")


def _ota_selection(source, info, force_non_ab):
    function = _function(source, "main")
    starts = [index for index, node in enumerate(function.body)
              if isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id == "ab_update"]
    _require(len(starts) == 1, "expected one OTA mode selection")
    nodes = function.body[starts[0]:starts[0] + 4]
    _require(len(nodes) == 4 and isinstance(nodes[1], ast.Assign)
             and isinstance(nodes[2], ast.If) and isinstance(nodes[3], ast.Assign)
             and ast.unparse(nodes[3].targets[0]) == "generate_ab",
             "unexpected OTA selection structure")
    namespace = {"OPTIONS": SimpleNamespace(info_dict=info, force_non_ab=force_non_ab)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),
                 "<verified-ota-selection>", "exec"), namespace)
    return namespace["generate_ab"]


def _case(data, *, name, info, two_step=False, ordinary=True,
          expected_error=None, has_recovery=True, existing=False, archive=True):
    """Run verified source with inert temporary image bytes and no image builder."""
    ordinary_bytes = b"INERT dedicated recovery fixture; not a boot image\n"
    two_step_bytes = b"INERT distinct non-A/B two-step fixture; not a boot image\n"
    with tempfile.TemporaryDirectory(prefix="nezha-recovery-packaging-") as temporary:
        root = Path(temporary).resolve()
        calls, builder_calls, writes = [], [], []
        for directory in ("BOOTABLE_IMAGES", "IMAGES", "OTA"):
            (root / directory).mkdir()
        if ordinary:
            (root / "BOOTABLE_IMAGES/recovery.img").write_bytes(ordinary_bytes)
        if two_step:
            (root / "BOOTABLE_IMAGES/recovery-two-step.img").write_bytes(two_step_bytes)
        if existing:
            (root / "IMAGES/recovery.img").write_bytes(ordinary_bytes)

        def local_path(path):
            path = Path(path)
            _require(path.resolve().is_relative_to(root) and not path.is_symlink(),
                     "probe tried to leave its synthetic directory")
            return path

        class InertFile:
            @classmethod
            def FromLocalFile(cls, destination, source):
                item = cls()
                item.name, item.data = destination, local_path(source).read_bytes()
                return item

            def WriteToDir(self, directory):
                local_path(Path(directory) / self.name).write_bytes(self.data)
                writes.append(self.name)

            def AddToZip(self, output):
                output.writestr(self.name, self.data)

        def forbidden(*args, **kwargs):
            raise RecoveryPackagingError("probe attempted a signer or other image operation")

        def missing_builder(*args, **kwargs):
            builder_calls.append(args[0])
            return None

        options = SimpleNamespace(input_tmp=str(root), info_dict=info)
        common_namespace = {
            "os": os, "OPTIONS": options, "logger": logging.getLogger(__name__),
            "File": InertFile, "HasRamdisk": lambda *args: True,
            "_BuildBootableImage": missing_builder, "MakeTempFile": forbidden,
            "_SignBootableImage": forbidden,
        }
        get_image = _load_function(data[COMMON_PATH], "GetBootableImage", common_namespace)

        def observed_image(*args, **kwargs):
            calls.append({"name": args[0], "prebuilt_name": args[1],
                          "two_step_image": kwargs.get("two_step_image", False)})
            return get_image(*args, **kwargs)

        output_path = root / "synthetic.zip"
        output = zipfile.ZipFile(output_path, "w") if archive else None
        namespace = {"OPTIONS": options, "os": os, "has_recovery": has_recovery,
                     "banner": lambda *_: None, "partitions": {}, "output_zip": output,
                     "common": SimpleNamespace(GetBootableImage=observed_image)}
        error = None
        try:
            exec(_recovery_branch(data[EDIT_PATH]), namespace)
        except AssertionError as exc:
            error = str(exc)
        finally:
            if output is not None:
                output.close()
        _require(error == expected_error, "unexpected recovery result for " + name)
        expected_calls = [] if not has_recovery else [{
            "name": "IMAGES/recovery.img", "prebuilt_name": "recovery.img", "two_step_image": False}]
        needs_two_step = (has_recovery and ordinary and not existing
                          and (info.get("ab_update") != "true" or info.get("allow_non_ab") == "true"))
        if needs_two_step:
            expected_calls.append({"name": "OTA/recovery-two-step.img",
                                   "prebuilt_name": "recovery-two-step.img", "two_step_image": True})
        _require(calls == expected_calls, "unexpected image request for " + name)
        destination = root / "IMAGES/recovery.img"
        if has_recovery and ordinary:
            _require(destination.read_bytes() == ordinary_bytes, "ordinary recovery bytes changed")
            _require(namespace["partitions"] == {"recovery": str(destination)},
                     "ordinary recovery lost its partition entry")
        else:
            _require(namespace["partitions"] == {}, "unexpected recovery partition entry")
        emitted_two_step = needs_two_step and two_step
        _require((root / "OTA/recovery-two-step.img").exists() == emitted_two_step,
                 "inapplicable or missing two-step artifact")
        if emitted_two_step:
            _require((root / "OTA/recovery-two-step.img").read_bytes() == two_step_bytes,
                     "two-step input was replaced with ordinary recovery")
        if output is not None:
            with zipfile.ZipFile(output_path) as result:
                expected = {}
                if has_recovery and ordinary and not existing:
                    expected["IMAGES/recovery.img"] = ordinary_bytes
                if emitted_two_step:
                    expected["OTA/recovery-two-step.img"] = two_step_bytes
                _require(len(result.namelist()) == len(expected),
                         "archive has missing or duplicate recovery entries")
                _require({key: result.read(key) for key in result.namelist()} == expected,
                         "archive contents differ from selected recovery artifacts")
        return {"name": name, "status": "passed", "expected_error": expected_error,
                "image_requests": calls, "stubbed_missing_image_requests": builder_calls,
                "written_artifacts": writes, "synthetic_inputs_only": True}


def probe(source_tree, *, composed_source_contract=None):
    record, identity = _selected_contract(composed_source_contract)
    data, files = _source(source_tree, record)
    missing_two_step = "Failed to create recovery-two-step.img."
    cases = [
        {"name": "ab-only-fresh-zip", "info": {"ab_update": "true"}},
        {"name": "ab-only-fresh-directory", "info": {"ab_update": "true"}, "archive": False},
        {"name": "ab-only-explicit-false", "info": {"ab_update": "true", "allow_non_ab": "false"}},
        {"name": "ab-only-existing-image", "info": {"ab_update": "true"}, "existing": True},
        {"name": "ab-only-no-recovery", "info": {"ab_update": "true"}, "has_recovery": False, "ordinary": False},
        {"name": "ab-only-missing-real-recovery", "info": {"ab_update": "true"}, "ordinary": False,
         "expected_error": "Failed to create recovery.img."},
        {"name": "non-ab-missing-two-step", "info": {"ab_update": "false"}, "expected_error": missing_two_step},
        {"name": "legacy-missing-two-step", "info": {}, "expected_error": missing_two_step},
        {"name": "hybrid-missing-two-step", "info": {"ab_update": "true", "allow_non_ab": "true"},
         "expected_error": missing_two_step},
        {"name": "non-ab-with-distinct-two-step", "info": {"ab_update": "false"}, "two_step": True},
        {"name": "hybrid-with-distinct-two-step", "info": {"ab_update": "true", "allow_non_ab": "true"}, "two_step": True},
        {"name": "unknown-ab-value-retains-requirement", "info": {"ab_update": "TRUE"}, "expected_error": missing_two_step},
    ]
    results = [_case(data, **case) for case in cases]
    _require(_ota_selection(data[OTA_PATH], {"ab_update": "true"}, False) is True,
             "A/B OTA selection changed")
    try:
        _ota_selection(data[OTA_PATH], {"ab_update": "true"}, True)
    except AssertionError as exc:
        _require(str(exc) == "--force_non_ab only allowed on devices that supports non-A/B",
                 "unexpected force_non_ab error")
    else:
        raise RecoveryPackagingError("force_non_ab no longer fails for A/B-only metadata")
    _require(_ota_selection(data[OTA_PATH], {"ab_update": "true", "allow_non_ab": "true"}, True) is False,
             "explicit hybrid selection changed")
    fstab = _load_function(data[COMMON_PATH], "_FindAndLoadRecoveryFstab", {})
    _require(fstab({"ab_update": "true"}, None, None) is None,
             "A/B-only fstab semantics no longer match packaging")
    _require(_source(source_tree, record) == (data, files), "source changed during probe")
    _require(_selected_contract(composed_source_contract) == (record, identity),
             "control contract changed during probe")
    result = {"schema_version": 1, "status": "verified-python-recovery-branch",
              "contract": identity, "files": files, "cases": results,
              "force_non_ab_without_permission_rejected": True,
              "explicit_hybrid_selection_preserved": True,
              "ab_only_recovery_fstab_not_required": True,
              "source_modified": False, "native_commands_executed": [],
              "scope": copy.deepcopy(SCOPE)}
    if "composition" in record:
        result["composition"] = copy.deepcopy(record["composition"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("check-source", "probe"))
    parser.add_argument("--source-tree", type=Path, required=True)
    parser.add_argument("--composed-source-contract", type=Path,
                        help="explicit reviewed 0007 contract for the ordered 0005/0006/0007 source composition")
    args = parser.parse_args(argv)
    try:
        result = (probe if args.operation == "probe" else check_source)(
            args.source_tree, composed_source_contract=args.composed_source_contract)
    except (OSError, ValueError, KernelInputsError, SyntaxError) as exc:
        print("recovery packaging: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
