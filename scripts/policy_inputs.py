#!/usr/bin/env python3
"""Stage the reviewed Nezha policy corpus and context inputs privately.

The sealed v9 corpus is classification provenance for the vendor correction.
Native Android modules compile CURRENT framework outputs with the derived vendor
CIL. Staging never derives policy, compiles it, replaces an image, or uses a phone.
Run verification again after transferring this bundle to an Android checkout.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile

if __package__:
    from . import vendor_policy
    from .artifact_files import publish_new_directory
else:
    import vendor_policy
    from artifact_files import publish_new_directory


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = "vendor/xiaomi/nezha-policy"
RECEIPT_NAME = "policy-inputs.json"
CONTRACT_PATH = "config/nezha-policy-inputs.json"
FACTORY_RECORD_PATH = "research/factory-framework-contract.json"
CONTROL_FILES = {
    "Android.bp": "policy/nezha/Android.bp",
    "tools/vendor_policy.py": "scripts/vendor_policy.py",
    "tools/artifact_files.py": "scripts/artifact_files.py",
    "tools/vendor-policy-correction.json": "config/vendor-policy-correction.json",
    "tools/nezha-policy-inputs.json": CONTRACT_PATH,
    "provenance/factory-framework-contract.json": FACTORY_RECORD_PATH,
}
FACTORY_RECEIPT_MEMBER = "provenance/factory-policy-capture.json"
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
SCOPE = {
    "classification_corpus": "sealed-v9-framework-and-original-factory-vendor-odm",
    "combined_framework_inputs": "current-native-Android-module-outputs",
    "vendor_derivation": "native-Android-genrule-from-original-corpus",
    "policy_compiled": False,
    "contexts_validated": False,
    "treble_labeling_validated": False,
    "opaque_vendor_or_odm_images_changed": False,
    "image_integration_verified": False,
    "full_rom_verified": False,
    "complete_rom_admitted": False,
    "hardware_tested": False,
    "device_operations": [],
}


class PolicyInputsError(ValueError):
    """A policy bundle did not satisfy its exact private-input contract."""


def require(condition, message):
    if not condition:
        raise PolicyInputsError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def _unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "duplicate JSON object key")
        value[key] = item
    return value


def _json(raw):
    value = json.loads(raw, object_pairs_hook=_unique)
    require(type(value) is dict, "JSON record must be an object")
    return value


def _relative(value):
    require(type(value) is str and value and "\\" not in value and "\0" not in value,
            "invalid relative bundle path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and all(part not in {".", ".."} for part in path.parts), "unsafe bundle path")
    return value


def _runtime(value):
    require(type(value) is str and value.startswith("/"), "runtime path must be absolute")
    return _relative(value[1:])


def _expected(row):
    require(type(row) is dict and type(row.get("sha256")) is str
            and len(row["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in row["sha256"])
            and type(row.get("size_bytes")) is int and 0 <= row["size_bytes"] <= MAX_BUNDLE_BYTES,
            "invalid input identity")
    return {key: row[key] for key in ("sha256", "size_bytes")}


def _read_exact(reader, path, expected):
    expected = _expected(expected)
    return reader.read(path, expected["sha256"], expected["size_bytes"])


def _contracts(reader):
    controls = {destination: reader.read(ROOT / source) for destination, source in CONTROL_FILES.items()}
    contract = _json(controls["tools/nezha-policy-inputs.json"])
    require(type(contract.get("schema_version")) is int and contract["schema_version"] == 1
            and contract.get("device") == "nezha" and contract.get("bundle") == BUNDLE_PATH,
            "unexpected Nezha policy-input contract")
    correction = vendor_policy.load_contract(ROOT / "config/vendor-policy-correction.json", reader)
    require(type(correction.get("inputs")) is list and len(correction["inputs"]) == 10,
            "expected the complete ten-file classification corpus")
    paths = [_runtime(row.get("runtime_path")) for row in correction["inputs"]]
    require(len(set(paths)) == 10 and len({p.casefold() for p in paths}) == 10,
            "classification corpus contains duplicate paths")
    for row in correction["inputs"]:
        _expected(row)
    factory = _json(controls["provenance/factory-framework-contract.json"])
    require(type(factory.get("schema_version")) is int and factory["schema_version"] == 1
            and factory.get("device") == {"codename": "nezha", "hardware_region": "CN"},
            "unexpected factory record")
    public_capture = factory.get("receipts", {}).get("policy_capture")
    require(public_capture == contract.get("factory_policy_capture"),
            "factory context capture differs from the reviewed factory record")
    _expected(public_capture)
    _relative(public_capture["path"])
    require(factory.get("provenance", {}).get("factory", {}).get("sha256") == contract.get("package_sha256"),
            "factory package identity differs from the policy-input contract")
    require(correction.get("factory_package_sha256") == contract.get("package_sha256"),
            "vendor derivation and context capture must use the same factory package")
    contexts = contract.get("contexts")
    require(type(contexts) is list and contexts, "factory contexts are required")
    context_paths, runtimes = [], []
    for row in contexts:
        runtime = _runtime(row.get("runtime_path"))
        partition = runtime.split("/", 1)[0]
        require(partition in {"vendor", "odm"} and runtime.startswith(partition + "/etc/selinux/")
                and runtime.endswith("_contexts"), "only exact vendor/ODM SELinux context files may be staged")
        destination = _relative(row.get("path"))
        require(destination == "factory/" + partition + "/" + PurePosixPath(runtime).name,
                "factory context destination must retain its runtime basename")
        _relative(row.get("capture_path"))
        _expected(row)
        context_paths.append(destination)
        runtimes.append(runtime)
    require(len(set(context_paths)) == len(contexts) and len(set(runtimes)) == len(contexts),
            "duplicate factory context selection")
    require(len({p.casefold() for p in context_paths}) == len(contexts), "case-colliding context paths")
    return contract, correction, controls


def _capture(reader, receipt_path, contract):
    raw = _read_exact(reader, receipt_path, contract["factory_policy_capture"])
    capture = _json(raw)
    require(type(capture.get("schema_version")) is int and capture["schema_version"] == 1
            and capture.get("operation") == "factory-policy-capture-and-comparison"
            and capture.get("parent_package_sha256") == contract["package_sha256"],
            "unexpected factory context provenance")
    rows = capture.get("files")
    require(type(rows) is list and all(type(row) is dict for row in rows), "invalid factory capture files")
    paths = [row.get("runtime_path") for row in rows]
    require(all(type(path) is str for path in paths) and len(set(paths)) == len(paths),
            "factory capture contains duplicate runtime paths")
    files = dict(zip(paths, rows))
    capture_parent = PurePosixPath(contract["factory_policy_capture"]["path"]).parent
    for expected in contract["contexts"]:
        row = files.get(expected["runtime_path"])
        require(row is not None and _expected(row) == _expected(expected),
                "factory context is missing or differs from the bound capture")
        source_path = PurePosixPath(_relative(row.get("path")))
        require(source_path.is_relative_to(capture_parent)
                and source_path.relative_to(capture_parent).as_posix() == expected["capture_path"],
                "factory context capture path does not match its reviewed selection")
        runtime = PurePosixPath(expected["runtime_path"])
        require(row.get("partition") == runtime.parts[1]
                and row.get("image_path") == "/" + "/".join(runtime.parts[2:]),
                "factory context partition or image path differs")
    return raw


def _manifest(contract, correction, files, stage_tool):
    return {
        "schema_version": 1, "operation": "stage-nezha-policy-inputs", "status": "staged",
        "device": "nezha", "bundle": BUNDLE_PATH,
        "factory_package_sha256": contract["package_sha256"],
        "factory_policy_capture": copy.deepcopy(contract["factory_policy_capture"]),
        "classification_inputs": copy.deepcopy(correction["inputs"]),
        "contexts": copy.deepcopy(contract["contexts"]),
        "native_targets": copy.deepcopy(contract["native_targets"]),
        "expected_vendor_derivative": copy.deepcopy(correction["output"]),
        "files": [{"path": name, **identity(data)} for name, data in sorted(files.items())],
        "staging_tool": identity(stage_tool),
        "scope": copy.deepcopy(SCOPE), "readback_verified": True,
    }


def _members(bundle):
    paths = set()
    for parent, directories, files in os.walk(bundle, followlinks=False):
        for name in [*directories, *files]:
            path = Path(parent) / name
            mode = path.lstat().st_mode
            require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), "bundle contains a symlink or special file")
            if stat.S_ISREG(mode):
                paths.add(path.relative_to(bundle).as_posix())
    return paths


def verify_bundle(bundle):
    """Verify a relocated bundle against current reviewed workspace controls.

    The caller must supply a trusted copy of this workspace's control files;
    a self-reported bundle receipt is never the authority for input hashes.
    """
    bundle = vendor_policy.real_directory(bundle)
    reader = vendor_policy.Reader()
    contract, correction, controls = _contracts(reader)
    expected = dict(controls)
    expected[FACTORY_RECEIPT_MEMBER] = _capture(reader, bundle / FACTORY_RECEIPT_MEMBER, contract)
    for row in correction["inputs"]:
        member = "corpus/" + _runtime(row["runtime_path"])
        expected[member] = _read_exact(reader, bundle / member, row)
    for row in contract["contexts"]:
        expected[row["path"]] = _read_exact(reader, bundle / row["path"], row)
    for member, data in controls.items():
        _read_exact(reader, bundle / member, identity(data))
    raw = reader.read(bundle / RECEIPT_NAME)
    stage_tool = reader.read(ROOT / "scripts/policy_inputs.py")
    require(_json(raw) == _manifest(contract, correction, expected, stage_tool),
            "policy-input receipt differs from the reviewed files or scope")
    require(_members(bundle) == set(expected) | {RECEIPT_NAME}, "bundle has missing or unexpected files")
    reader.recheck()
    return {
        "schema_version": 1, "operation": "verify-nezha-policy-inputs", "status": "verified",
        "device": "nezha", "bundle": BUNDLE_PATH,
        "factory_package_sha256": contract["package_sha256"],
        "files": [{"path": name, **identity(data)} for name, data in sorted(expected.items())],
        "receipt": {"path": RECEIPT_NAME, **identity(raw)},
        "scope": copy.deepcopy(SCOPE),
    }


def _output_path(output):
    output = Path(os.path.abspath(output))
    parent = vendor_policy.real_directory(output.parent)
    require(not os.path.lexists(output), "policy bundle output already exists")
    # Factory material must never enter a tracked source directory accidentally.
    if output.is_relative_to(ROOT):
        relative = output.relative_to(ROOT).as_posix()
        require(relative.startswith(("artifacts/", "evidence/", "reports/")) or relative == BUNDLE_PATH,
                "workspace output must be in an ignored private directory")
    return output, parent


def stage_inputs(corpus_root, output, *, factory_capture_root=None, factory_policy_receipt=None):
    """Publish a fresh private bundle atomically; originals remain untouched."""
    require((factory_capture_root is None) != (factory_policy_receipt is None),
            "choose exactly one factory capture root or receipt")
    output, parent = _output_path(output)
    corpus_root = vendor_policy.real_directory(corpus_root)
    if factory_capture_root is not None:
        capture_root = vendor_policy.real_directory(factory_capture_root)
        receipt_path = capture_root / "policy-receipt.json"
    else:
        receipt_path = Path(os.path.abspath(factory_policy_receipt))
        capture_root = vendor_policy.real_directory(receipt_path.parent)
    require(not output.is_relative_to(corpus_root) and not output.is_relative_to(capture_root),
            "private output must not add files inside the preserved input roots")
    reader = vendor_policy.Reader()
    contract, correction, controls = _contracts(reader)
    files = dict(controls)
    files[FACTORY_RECEIPT_MEMBER] = _capture(reader, receipt_path, contract)
    for row in correction["inputs"]:
        member = "corpus/" + _runtime(row["runtime_path"])
        files[member] = _read_exact(reader, corpus_root / _runtime(row["runtime_path"]), row)
    for row in contract["contexts"]:
        files[row["path"]] = _read_exact(reader, capture_root / row["capture_path"], row)
    require(sum(len(data) for data in files.values()) <= MAX_BUNDLE_BYTES, "policy bundle exceeds its byte limit")
    stage_tool = reader.read(ROOT / "scripts/policy_inputs.py")
    receipt = _manifest(contract, correction, files, stage_tool)
    files[RECEIPT_NAME] = encoded(receipt)
    required_bytes = sum(len(data) for data in files.values())
    require(shutil.disk_usage(parent).free >= required_bytes + 16 * 1024 * 1024,
            "insufficient free space for a fresh policy bundle")
    staging = Path(tempfile.mkdtemp(prefix=".nezha-policy-inputs-", dir=parent))
    published = False
    try:
        staging.chmod(0o700)
        for member, data in sorted(files.items()):
            path = staging / _relative(member)
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for directory in path.parents:
                if directory == staging:
                    break
                directory.chmod(0o700)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        # Readback checks use exact controls and bytes, before exclusive publish.
        verify_bundle(staging)
        reader.recheck()
        require(vendor_policy.real_directory(parent) == parent, "output parent changed during staging")
        publish_new_directory(staging, output)
        published = True
        return receipt
    finally:
        if not published:
            shutil.rmtree(staging)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage", help="stage exact private inputs without deriving or compiling policy")
    stage.add_argument("--corpus-root", required=True, type=Path)
    factory = stage.add_mutually_exclusive_group(required=True)
    factory.add_argument("--factory-capture-root", type=Path)
    factory.add_argument("--factory-policy-receipt", type=Path)
    stage.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("verify", help="verify every transferred file against reviewed workspace controls")
    verify.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            result = stage_inputs(args.corpus_root, args.output, factory_capture_root=args.factory_capture_root,
                                  factory_policy_receipt=args.factory_policy_receipt)
        else:
            result = verify_bundle(args.bundle)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}), file=sys.stderr)
        return 2
    print(encoded(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
