#!/usr/bin/env python3
"""Prepare explicit Camera DEX runtime inputs without importing or modifying an APK.

Preparation binds the existing factory selection and reviewed Soong patch. It
does not claim that the patch is installed; verify-source performs that separate
read-only check. vendor_inputs.py stages and validates actual XML/JAR bytes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from . import vendor_inputs as vendor
    from .artifact_files import publish_new_directory
    from .firmware import IntakeError, _directory, _open_regular, _signature
else:
    import vendor_inputs as vendor
    from artifact_files import publish_new_directory
    from firmware import IntakeError, _directory, _open_regular, _signature


ROOT = Path(__file__).resolve().parents[1]
MAX_CONTROL_BYTES = 8 * 1024 * 1024
SOURCE_FILES = {"java/java.go", "java/Android.bp", "java/dex_import_test.go"}
SCOPE = {
    "camera_apk_included": False,
    "permission_grants_added": False,
    "signature_changed": False,
    "uses_library_checks_relaxed": False,
    "guest_patch_verified_by_preparation": False,
    "native_build_verified_by_preparation": False,
    "runtime_camera_verified": False,
}
CameraRuntimeError = vendor.VendorInputError


def _require(condition, message):
    if not condition:
        raise CameraRuntimeError(message)


def _relative(value):
    _require(isinstance(value, str) and 0 < len(value) <= 1024, "invalid control path")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and path.as_posix() == value
             and all(part not in ("", ".", "..") for part in value.split("/"))
             and "\\" not in value, "control path must be canonical and relative")
    return path


def _read(path, states):
    state = vendor._file_state(path)
    with _open_regular(state["file"]) as stream:
        _require(state["signature"] == _signature(os.fstat(stream.fileno())), "control changed before opening")
        raw = stream.read(MAX_CONTROL_BYTES + 1)
        _require(state["signature"] == _signature(os.fstat(stream.fileno())), "control changed while reading")
    vendor._unchanged(state)
    _require(len(raw) <= MAX_CONTROL_BYTES, "control exceeds size bound")
    states.append(state)
    return raw, {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _json(raw):
    try:
        value = json.loads(raw, object_pairs_hook=vendor._unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CameraRuntimeError("invalid camera metadata JSON") from exc
    _require(isinstance(value, dict) and type(value.get("schema_version")) is int
             and value["schema_version"] == 1, "expected schema-1 camera metadata")
    return value


def _bound(reference, root, states):
    _require(isinstance(reference, dict) and set(reference) == {"path", "sha256", "size_bytes"},
             "control reference must include exact path, hash and size")
    path = root / _relative(reference["path"])
    vendor._sha(reference["sha256"])
    vendor._positive(reference["size_bytes"], MAX_CONTROL_BYTES)
    raw, identity = _read(path, states)
    _require(all(reference[key] == value for key, value in identity.items()), "bound control hash/size mismatch")
    return raw


def _contract(path, root):
    states = []
    raw, identity = _read(path, states)
    contract = _json(raw)
    _require(set(contract) == {"schema_version", "device", "purpose", "package_sha256", "base_selection",
                              "factory_record", "provider_record", "source_patch", "source", "libraries", "scope"}
             and contract["device"] == "nezha" and contract["purpose"] == "camera-runtime-dependency-inputs",
             "unexpected camera runtime contract")
    _require(contract["scope"] == SCOPE and all(value is False for value in contract["scope"].values()),
             "camera runtime contract cannot admit APKs, permissions or skipped checks")
    vendor._sha(contract["package_sha256"])
    selection = _json(_bound(contract["base_selection"], root, states))
    factory = _json(_bound(contract["factory_record"], root, states))
    provider = _json(_bound(contract["provider_record"], root, states))
    _bound(contract["source_patch"], root, states)
    _require(factory["evidence"]["factory_camera_selection"] == contract["base_selection"]
             and factory["packages"]["factory"]["sha256"] == contract["package_sha256"]
             and selection["package_sha256"] == contract["package_sha256"],
             "Camera runtime selection must retain its recorded factory package")
    source = contract["source"]
    _require(set(source) == {"project", "revision", "files"} and source["project"] == "build/soong"
             and source["project"] == provider["source"]["project"]
             and source["revision"] == provider["source"]["revision"]
             and source["files"] == provider["patch"]["files"]
             and len(source["files"]) == len(SOURCE_FILES)
             and {row["path"] for row in source["files"]} == SOURCE_FILES,
             "provider patch must retain its reviewed source/file binding")
    _require(contract["source_patch"]["path"] == provider["patch"]["path"]
             and contract["source_patch"]["sha256"] == provider["patch"]["sha256"],
             "provider patch identity differs from its reviewed record")
    for row in source["files"]:
        _require(set(row) == {"path", "before_sha256", "after_sha256", "added_file"}
                 and type(row["added_file"]) is bool and row["added_file"] == (row["before_sha256"] is None),
                 "invalid patched-file contract")
        _relative(row["path"])
        vendor._sha(row["after_sha256"])
        if row["before_sha256"] is not None:
            vendor._sha(row["before_sha256"])
    libraries = contract["libraries"]
    _require(isinstance(libraries, list) and len(libraries) == 4, "expected four explicit Camera runtime JARs")
    selected = {row["runtime_path"]: row for row in selection["modules"]}
    _require(len(selected) == 9 and len(selection["modules"]) == 9
             and {row["runtime_path"] for row in libraries}
             == {row["runtime_path"] for row in selection["modules"] if row["type"] == "dex_jar"},
             "Camera runtime profile must preserve the nine-file selection and all four DEX JARs")
    for row in libraries:
        _require(set(row) == {"runtime_path", "name", "registration", "uses_libs"},
                 "unexpected Camera runtime library fields")
        _require(row["registration"] in selected and selected[row["registration"]]["type"] == "xml",
                 "Camera library registration is absent from the selected XML inputs")
    return contract, selection, identity, states


def prepare(contract_path, output, *, workspace_root=ROOT):
    """Publish new metadata only; actual blob checks occur in vendor staging."""
    root = vendor._real_directory(workspace_root)
    contract, base, identity, states = _contract(contract_path, root)
    destination = Path(os.path.abspath(output))
    _require(any(private in destination.parents for private in (root / "artifacts", root / "evidence")),
             "camera preparation output must stay in ignored artifacts/ or evidence/")
    _require(not os.path.lexists(destination), "camera preparation output already exists")
    selection = copy.deepcopy(base)
    runtime = {row["runtime_path"]: {key: row[key] for key in ("name", "registration", "uses_libs")}
               for row in contract["libraries"]}
    for module in selection["modules"]:
        if module["runtime_path"] in runtime:
            _require("runtime_library" not in module, "base selection must retain its historical definitions")
            module["runtime_library"] = runtime[module["runtime_path"]]
    parent = _directory(destination.parent)
    staging = Path(tempfile.mkdtemp(prefix="." + destination.name + "-", dir=parent))
    try:
        payload = (json.dumps(selection, indent=2, sort_keys=True) + "\n").encode()
        selected = vendor._write_file(staging, "camera-runtime-selection.json", payload)
        modules, _ = vendor._selection(staging / selected["path"], contract["package_sha256"], states)
        receipt = {"schema_version": 1, "device": "nezha", "operation": "camera-runtime-prepare",
                   "contract": identity, "base_selection": contract["base_selection"],
                   "selection": selected, "source": contract["source"], "source_patch": contract["source_patch"],
                   "runtime_modules": [row["module_name"] for row in modules if "runtime_library" in row],
                   "actual_xml_and_blob_hashes_checked": False, "scope": SCOPE}
        admission = vendor._write_file(staging, "camera-runtime-admission.json",
                                       (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        for row in (selected, admission):
            states.append(vendor._verify_output(staging / row["path"], row))
        for state in states:
            vendor._unchanged(state)
        publish_new_directory(staging, destination)
        staging = None
        return receipt
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def verify_source(contract_path, soong_root, *, workspace_root=ROOT, state="patched"):
    """Check the actual source revision and all patch preimages or postimages."""
    _require(state in {"base", "patched"}, "source state must be base or patched")
    contract, _, identity, states = _contract(contract_path, vendor._real_directory(workspace_root))
    source_root = vendor._real_directory(soong_root)
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(["git", "-C", str(source_root), "rev-parse", "--show-toplevel", "HEAD"],
                            check=False, capture_output=True, text=True, timeout=30, env=environment)
    _require(result.returncode == 0 and result.stdout.splitlines()
             == [str(source_root), contract["source"]["revision"]], "Soong source root or revision differs from pin")
    files = []
    for row in contract["source"]["files"]:
        path = source_root / _relative(row["path"])
        expected = row["after_sha256"] if state == "patched" else row["before_sha256"]
        if expected is None:
            _require(not os.path.lexists(path), "new provider test must be absent in pristine source")
            files.append({"path": row["path"], "absent": True})
        else:
            _, actual = _read(path, states)
            _require(actual["sha256"] == expected, "Soong source file differs from reviewed provider patch")
            files.append({"path": row["path"], **actual})
    for item in states:
        vendor._unchanged(item)
    return {"schema_version": 1, "device": "nezha", "operation": "camera-runtime-source-check",
            "contract": identity, "revision": contract["source"]["revision"], "state": state, "files": files,
            "source_modified": False, "native_build_executed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=ROOT / "config/nezha-camera-runtime.json")
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--output", type=Path, required=True)
    source = commands.add_parser("verify-source")
    source.add_argument("--soong-root", type=Path, required=True)
    source.add_argument("--state", choices=("base", "patched"), default="patched")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.contract, args.output, workspace_root=args.workspace_root)
        else:
            result = verify_source(args.contract, args.soong_root, workspace_root=args.workspace_root, state=args.state)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (CameraRuntimeError, IntakeError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"camera runtime admission failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
