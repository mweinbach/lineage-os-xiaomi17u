#!/usr/bin/env python3
"""Drive the six host signing stages for any Nezha build identity.

This is the maintained form of the per-build f9e signing orchestrator. Every
constant that orchestrator carried is now a field of a selection JSON that the
caller pins with `--expected-sha256`. `plan` validates the selection and prints
the stage commands without running anything. `run --execute-host-signing`
performs the sequence and writes the same stage logs the f9e run left behind,
so `release_workflow.py check` recognizes the result.

The stages call maintained scripts only: target_files_avb_inventory,
materialize_target_files_inputs, avb_signing (prepare, then sign),
reconcile_signed_target_files, and target_files_avb_inventory again on the
reconciled archive. No stage contacts a phone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 2
BUILD_NUMBER = re.compile(r"^nezha\.[0-9a-f]{24}$")
ARTIFACT_SET = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")
OPERATION = re.compile(r"^[a-z0-9][a-z0-9-]{2,120}$")
MAX_SELECTION_BYTES = 1 << 20
MAX_RECORD_BYTES = 64 << 20
STAGE_TIMEOUT_SECONDS = 7200
PIN_KEYS = ("path", "sha256", "size_bytes")
STAGE_NAMES = ("01-inventory", "02-materialize", "03-prepare",
               "04-sign", "05-reconcile", "06-published-inventory")
EXPECTED_STATUS = {
    "01-inventory": "complete",
    "02-materialize": "materialized-inputs-only",
    "03-prepare": "prepared_public_only",
    "04-sign": "signed_and_verified",
    "05-reconcile": "signed-image-archive-reconciled-only",
    "06-published-inventory": "complete",
}


class ReleaseSigningError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseSigningError(message)


def pin(path):
    """Hash a file in chunks and return the path, sha256, size triple."""
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), f"pinned file is missing or a symlink: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 ** 2):
            digest.update(chunk)
            size += len(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": size}


def _pin_shape(row, label):
    require(isinstance(row, dict) and set(row) >= set(PIN_KEYS), f"{label} needs path, sha256 and size_bytes")
    require(Path(row["path"]).is_absolute(), f"{label} path must be absolute")
    require(isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), f"{label} sha256 is invalid")
    require(type(row["size_bytes"]) is int and row["size_bytes"] > 0, f"{label} size must be a positive integer")
    return {key: row[key] for key in PIN_KEYS}


def _read_json(row, label):
    path = Path(row["path"])
    require(path.stat().st_size <= MAX_RECORD_BYTES, f"{label} exceeds {MAX_RECORD_BYTES} bytes")
    actual = pin(path)
    require(actual == _pin_shape(row, label), f"{label} bytes differ from the selection pin")
    try:
        return json.loads(path.read_bytes())
    except ValueError as exc:
        raise ReleaseSigningError(f"{label} is not JSON") from exc


def validate_selection(selection, *, hash_target_files=True):
    """Check the selection's shape, pins and the admission and transfer records."""
    require(isinstance(selection, dict) and selection.get("schema_version") == SCHEMA_VERSION,
            "selection schema_version must be 2")
    expected_keys = {"schema_version", "artifact_set_id", "build_number", "source", "target_files",
                     "package_admission", "package_transfer", "retained_input_manifest", "local_config"}
    require(set(selection) - {"artifact_base"} == expected_keys, "selection keys differ from the schema")
    artifact_set, build = selection["artifact_set_id"], selection["build_number"]
    require(ARTIFACT_SET.fullmatch(artifact_set or ""), "artifact_set_id must be a lowercase hyphenated name")
    require(BUILD_NUMBER.fullmatch(build or ""), "build_number must look like nezha.<24 hex>")

    source = selection["source"]
    source_pin = _pin_shape(source, "source record")
    require(type(source.get("entry_count")) is int and source["entry_count"] > 0
            and type(source.get("total_bytes")) is int and source["total_bytes"] > 0
            and isinstance(source.get("transaction"), str) and source["transaction"].startswith("/"),
            "source record needs entry_count, total_bytes and an absolute transaction")
    source_body = _read_json(source, "source record")
    rows = source_body.get("source_inventory")
    require(source_body.get("build_number") == build and source_body.get("transaction") == source["transaction"],
            "source record build number or transaction differs from the selection")
    require(isinstance(rows, list) and len(rows) == source["entry_count"], "source inventory entry count differs")
    require(sum(row["size_bytes"] for row in rows) == source["total_bytes"], "source inventory byte total differs")

    target = _pin_shape(selection["target_files"], "target-files archive")
    require(Path(target["path"]).suffix == ".zip", "target-files must be a .zip")
    archive_path = Path(target["path"])
    require(not archive_path.is_symlink() and archive_path.is_file(), "target-files archive is missing")
    require(archive_path.stat().st_size == target["size_bytes"], "target-files archive size differs")
    if hash_target_files:
        require(pin(archive_path) == target, "target-files archive bytes differ from the selection pin")

    records = {}
    for role in ("package_admission", "package_transfer"):
        row = selection[role]
        _pin_shape(row, role)
        require(isinstance(row.get("operation"), str) and OPERATION.fullmatch(row["operation"]),
                f"{role} must name its expected operation")
        records[role] = _read_json(row, role)
    admission, transfer = records["package_admission"], records["package_transfer"]
    require(admission.get("operation") == selection["package_admission"]["operation"], "package admission operation differs")
    require(admission.get("verified") is True and admission.get("build_number") == build, "package admission is not a verified record for this build")
    source_identity = {key: source_pin[key] for key in ("sha256", "size_bytes")}
    require(admission.get("source_inventory_record") == source_identity, "package admission binds a different source record")
    require(transfer.get("operation") == selection["package_transfer"]["operation"], "package transfer operation differs")
    require(transfer.get("kind") == "package" and transfer.get("verified") is True and transfer.get("build_number") == build,
            "package transfer is not a verified package record for this build")
    require(transfer.get("source_inventory_record") == source_identity, "package transfer binds a different source record")
    require(transfer.get("source_admission") == _pin_shape(selection["package_admission"], "package_admission"),
            "package transfer does not bind this admission")
    require(transfer.get("file") == target, "package transfer does not name this archive")
    require(transfer.get("source") == admission.get("archive"), "package transfer source differs from the admitted archive")
    archive_identity = {key: target[key] for key in ("sha256", "size_bytes")}
    require(transfer.get("stream_identity") == transfer.get("host_readback_identity")
            == transfer.get("guest_final_rehash_identity") == archive_identity,
            "package transfer identities do not all match the archive")
    require(all(transfer.get(key) is False for key in
                ("guest_writes", "source_or_android_output_written", "phone_accessed", "complete_rom_ready")),
            "package transfer asserts a write, phone access or readiness")

    retained = _pin_shape(selection["retained_input_manifest"], "retained input manifest")
    require(pin(retained["path"]) == retained, "retained input manifest bytes differ from the selection pin")
    local = Path(selection["local_config"])
    require(local.is_absolute() and not local.is_symlink() and local.is_file(), "local configuration must be an existing absolute file")
    base = Path(selection.get("artifact_base") or (ROOT / "artifacts/avb/nezha" / artifact_set))
    require(base.is_absolute() and base.name == artifact_set, "artifact base must end with the artifact set id")
    return {
        "artifact_set_id": artifact_set, "build_number": build, "source": source_pin,
        "source_provenance": {**source_pin, "entry_count": source["entry_count"],
                              "total_bytes": source["total_bytes"], "transaction": source["transaction"]},
        "target_files": target, "package_admission": _pin_shape(selection["package_admission"], "package_admission"),
        "package_transfer": _pin_shape(selection["package_transfer"], "package_transfer"),
        "retained_input_manifest": retained, "local_config": str(local), "artifact_base": str(base),
    }


def stage_commands(bound, resolved=None):
    """Return the six stage invocations; unresolved later inputs use placeholders."""
    resolved = resolved or {}
    base = Path(bound["artifact_base"])
    logs = base / "stage-logs"
    archive = bound["target_files"]
    archive_args = ["--target-files", archive["path"], "--expected-sha256", archive["sha256"],
                    "--expected-size-bytes", str(archive["size_bytes"])]
    retained = bound["retained_input_manifest"]
    retained_args = ["--retained-input-manifest", retained["path"],
                     "--expected-retained-manifest-sha256", retained["sha256"]]
    inventory = resolved.get("inventory", {"path": str(base / "original-inventory.json"),
                                           "sha256": "<01-inventory output sha256>"})
    source_args = []
    for role in ("source", "package_transfer"):
        row = bound[role]
        source_args += ["--source-record", row["path"], row["sha256"], str(row["size_bytes"])]
    materialized = resolved.get("input_manifest", {"path": "<02-materialize input_manifest.path>",
                                                   "sha256": "<02-materialize input_manifest.sha256>"})
    preparation = resolved.get("preparation", {"path": str(base / "prepared-v1/preparation.json"),
                                               "sha256": "<03-prepare output sha256>"})
    request_path = str(logs / "reconcile-request.json")
    request_sha = resolved.get("request_sha256", "<reconcile request sha256>")
    published = resolved.get("published", {"path": "<05-reconcile archive.path>",
                                           "sha256": "<05-reconcile archive.sha256>",
                                           "size_bytes": "<05-reconcile archive.size_bytes>"})
    return [
        ("01-inventory", "target_files_avb_inventory.py",
         ["inspect", *archive_args, *retained_args, "--output", str(base / "original-inventory.json")]),
        ("02-materialize", "materialize_target_files_inputs.py",
         [*archive_args, *retained_args, "--inventory", inventory["path"], "--expected-inventory-sha256",
          inventory["sha256"], "--artifact-set-id", bound["artifact_set_id"],
          "--output-dir", str(base / "inputs-v1"), *source_args]),
        ("03-prepare", "avb_signing.py",
         ["prepare", "--input", materialized["path"], "--expected-sha256", materialized["sha256"],
          "--local-config", bound["local_config"], "--output-dir", str(base / "prepared-v1")]),
        ("04-sign", "avb_signing.py",
         ["sign", "--input", preparation["path"], "--expected-sha256", preparation["sha256"],
          "--local-config", bound["local_config"], "--output-dir", str(base / "signed-v1")]),
        ("05-reconcile", "reconcile_signed_target_files.py",
         ["--request", request_path, "--expected-sha256", request_sha, "--output-dir", str(base / "reconciled-v1")]),
        ("06-published-inventory", "target_files_avb_inventory.py",
         ["inspect", "--target-files", published["path"], "--expected-sha256", published["sha256"],
          "--expected-size-bytes", str(published["size_bytes"]), *retained_args,
          "--output", str(base / "published-inventory.json")]),
    ]


def load_selection(path, expected_sha256):
    raw = Path(path).read_bytes()
    require(len(raw) <= MAX_SELECTION_BYTES, "selection exceeds the size bound")
    require(hashlib.sha256(raw).hexdigest() == expected_sha256, "selection sha256 differs from --expected-sha256")
    try:
        return raw, json.loads(raw)
    except ValueError as exc:
        raise ReleaseSigningError("selection is not JSON") from exc


def plan(selection):
    bound = validate_selection(selection, hash_target_files=False)
    return {
        "operation": "release-signing-plan", "schema_version": SCHEMA_VERSION,
        "artifact_set_id": bound["artifact_set_id"], "build_number": bound["build_number"],
        "artifact_base": bound["artifact_base"], "dispatches": False, "phone_operations": [],
        "target_files_hash_deferred_to_run": True,
        "stages": [{"name": name, "script": f"scripts/{script}", "argv": argv, "expected_status": EXPECTED_STATUS[name]}
                   for name, script, argv in stage_commands(bound)],
    }


def run(selection, raw_selection, *, runner=subprocess.run, host_check=True):
    if host_check:
        require(platform.system() == "Darwin" and platform.machine() == "arm64",
                "host signing runs on the Darwin arm64 signer only")
    require(not sys.flags.optimize, "Python optimization must be disabled for signing")
    bound = validate_selection(selection)
    base = Path(bound["artifact_base"])
    require(not base.exists() and not base.is_symlink(), f"artifact base already exists: {base}")
    base.mkdir(parents=True, mode=0o700)
    logs = base / "stage-logs"
    logs.mkdir()
    (logs / "selection.json").write_bytes(raw_selection)
    resolved = {}

    def execute(name, script, argv):
        with (logs / f"{name}.stdout.json").open("xb") as stdout, (logs / f"{name}.stderr").open("xb") as stderr:
            try:
                result = runner([sys.executable, "-B", str(ROOT / "scripts" / script), *argv],
                                cwd=ROOT, stdout=stdout, stderr=stderr, timeout=STAGE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                (logs / f"{name}.exit.json").write_text(json.dumps({
                    "timed_out": True, "incomplete": True, "timeout_seconds": STAGE_TIMEOUT_SECONDS,
                    "native_descendant_cleanup_verified": False}) + "\n")
                raise
        (logs / f"{name}.exit.json").write_text(json.dumps({"returncode": result.returncode}) + "\n")
        require(result.returncode == 0, f"{name} failed; logs preserved at {logs}")
        value = json.loads((logs / f"{name}.stdout.json").read_bytes())
        require(value.get("status") == EXPECTED_STATUS[name], f"{name} reported status {value.get('status')!r}")
        return value

    for index in range(len(STAGE_NAMES)):
        name, script, argv = stage_commands(bound, resolved)[index]
        value = execute(name, script, argv)
        if name == "01-inventory":
            resolved["inventory"] = pin(base / "original-inventory.json")
        elif name == "02-materialize":
            resolved["input_manifest"] = value["input_manifest"]
        elif name == "03-prepare":
            resolved["preparation"] = pin(base / "prepared-v1/preparation.json")
        elif name == "04-sign":
            request = {"schema_version": 1, "operation": "reconcile-nezha-signed-target-files-v1",
                       "target_files": bound["target_files"], "inventory": resolved["inventory"],
                       "retained_input_manifest": bound["retained_input_manifest"],
                       "signing_preparation": resolved["preparation"],
                       "signing_receipt": pin(base / "signed-v1/signing-receipt.json"),
                       "verification_manifest": pin(base / "signed-v1/verification-manifest.json")}
            request_path = logs / "reconcile-request.json"
            request_path.write_text(json.dumps(request, indent=2) + "\n")
            resolved["request"] = request
            resolved["request_sha256"] = pin(request_path)["sha256"]
        elif name == "05-reconcile":
            resolved["published"] = value["archive"]
    return {"status": "signing-sequence-completed", "artifact_set_id": bound["artifact_set_id"],
            "build_number": bound["build_number"], "archive": resolved["published"],
            "published_inventory": pin(base / "published-inventory.json"),
            "verification_manifest": resolved["request"]["verification_manifest"],
            "signing_receipt": resolved["request"]["signing_receipt"], "flash_ready": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = commands.add_parser(name)
        command.add_argument("--selection", type=Path, required=True)
        command.add_argument("--expected-sha256", required=True)
        if name == "run":
            command.add_argument("--execute-host-signing", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        raw, selection = load_selection(args.selection, args.expected_sha256)
        if args.command == "run":
            os.umask(0o077)  # Process-wide on purpose: the CLI owns this process; the library does not.
        result = plan(selection) if args.command == "plan" else run(selection, raw)
    except (ReleaseSigningError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
