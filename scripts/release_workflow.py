#!/usr/bin/env python3
"""Plan and check the Nezha release sequence for one build identity.

`plan` prints the ordered stages from docs/release-runbook.md with concrete
command templates for the selected identity. `check` reports which stage
receipts already exist for that identity under the ignored artifact roots.
Neither command dispatches a build, signs, assembles, or contacts a phone, and
neither reads an image body: only small JSON receipts are opened.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD_NUMBER = re.compile(r"^nezha\.[0-9a-f]{24}$")
ARTIFACT_SET = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")
MAX_RECEIPT_BYTES = 4 * 1024 * 1024
SIGNING_STAGES = (
    "01-inventory", "02-materialize", "03-prepare",
    "04-sign", "05-reconcile", "06-published-inventory",
)

STAGES = (
    {
        "id": "source", "title": "Select source and record the inventory",
        "owner": "host", "runs": "reviewed source transaction",
        "commands": ["python3 reports/<run>/prepare_*.py  # per-build transaction; records source-installed.json"],
        "receipts": ["reports/*/source-installed.json with build_number {build}"],
    },
    {
        "id": "candidate", "title": "Generate the device candidate",
        "owner": "host", "runs": "scripts/generate_device_tree.py",
        "commands": [
            "python3 scripts/generate_device_tree.py generate <complete recipe> "
            "--rom-construction-source-contract config/nezha-rom-construction-source-v1.json "
            "--output artifacts/device-candidates/{set}",
            "python3 scripts/generate_device_tree.py validate --output artifacts/device-candidates/{set}",
        ],
        "receipts": ["artifacts/device-candidates/{set}/admission.json"],
    },
    {
        "id": "native", "title": "Native preflight and target-files package",
        "owner": "guest", "runs": "per-build runner over build/soong/soong_ui.bash",
        "commands": [
            "python3 reports/<run>/build_successor.py nothing",
            "python3 reports/<run>/build_successor.py recoveryimage mi_extimage vendorimage odmimage "
            "plat_sepolicy_and_mapping.sha256 system_ext_sepolicy_and_mapping.sha256 product_sepolicy_and_mapping.sha256",
            "python3 reports/<run>/build_successor.py target-files-package",
        ],
        "receipts": ["guest /work/validation/<family>/<timestamp>/result.json exit 0; package admission"],
    },
    {
        "id": "transfer", "title": "Transfer the archive to the host",
        "owner": "host", "runs": "scripts/target_files_archive_copy.py",
        "commands": ["python3 reports/<run>/package_transfer_*.py  # wraps target_files_archive_copy.py"],
        "receipts": ["artifacts/build-validation/*-package-transfer-v*/lineage_nezha-target_files.zip and transfer receipt"],
    },
    {
        "id": "signing", "title": "Inventory, materialize, sign, reconcile",
        "owner": "host", "runs": "six maintained scripts driven by the signing orchestrator",
        "commands": [
            "python3 scripts/target_files_avb_inventory.py inspect --target-files <zip> --expected-sha256 <sha> --expected-size-bytes <n> --output artifacts/avb/nezha/{set}/original-inventory.json",
            "python3 scripts/materialize_target_files_inputs.py ...  --output artifacts/avb/nezha/{set}/inputs-v1",
            "python3 scripts/avb_signing.py prepare --input <input manifest> --output-dir artifacts/avb/nezha/{set}/prepared-v1",
            "python3 scripts/avb_signing.py sign --input <prepared> --expected-sha256 <sha> --local-config .tools/recovery-local.json --output-dir artifacts/avb/nezha/{set}/signed-v1",
            "python3 scripts/reconcile_signed_target_files.py --request artifacts/avb/nezha/{set}/stage-logs/reconcile-request.json",
            "python3 scripts/target_files_avb_inventory.py inspect --target-files <reconciled zip> ... --output artifacts/avb/nezha/{set}/published-inventory.json",
        ],
        "receipts": [f"artifacts/avb/nezha/{{set}}/stage-logs/{stage}.exit.json" for stage in SIGNING_STAGES]
        + ["artifacts/avb/nezha/{set}/published-inventory.json"],
    },
    {
        "id": "super", "title": "Assemble Super and read it back",
        "owner": "guest then host", "runs": "per-build Super adapter over lpmake and scripts/logical_partitions.py",
        "commands": [
            "python3 reports/<run>/super-prep/run.py prepare-current ...",
            "python3 reports/<run>/super-prep/run.py assemble --manifest <prepared manifest> --expected-sha256 <sha>",
            "python3 scripts/logical_partitions.py inspect --image <super.img> --expected-sha256 <sha>",
        ],
        "receipts": ["artifacts/build-validation/*-super-transfer-v*/transfer.json"],
    },
    {
        "id": "qualification", "title": "Qualify off-device",
        "owner": "host and guest", "runs": "qualification adapters and the joined summary",
        "commands": ["python3 reports/<run>/qualification-prep/host/verify.py --config <actual> --expected-sha256 <sha> --execute"],
        "receipts": ["reports/<run>/qualification-summary.json for build {build}"],
    },
    {
        "id": "bundle", "title": "Plan and assemble the bundle",
        "owner": "host", "runs": "scripts/experimental_flash_bundle.py",
        "commands": [
            "python3 scripts/experimental_flash_bundle.py assemble --plan <delivery-plan.json> --expected-plan-sha256 <sha> "
            "--super <super.img> --output " + str(ROOT / "artifacts/flash/nezha/{set}"),
            "python3 scripts/experimental_flash_bundle.py verify --bundle artifacts/flash/nezha/{set} --expected-manifest-sha256 <sha>",
        ],
        "receipts": ["artifacts/flash/nezha/{set}/manifest.json", "artifacts/flash/nezha/{set}/SHA256SUMS"],
    },
    {
        "id": "record", "title": "Record",
        "owner": "host", "runs": "documentation",
        "commands": ["edit docs/workspace-status.md; add a dated docs page; index it in docs/README.md"],
        "receipts": ["docs/workspace-status.md names build {build} and bundle artifacts/flash/nezha/{set}"],
    },
)


class ReleaseWorkflowError(ValueError):
    pass


def identity(build_number, artifact_set):
    if not BUILD_NUMBER.fullmatch(build_number or ""):
        raise ReleaseWorkflowError("build number must look like nezha.<24 lowercase hex>")
    if not ARTIFACT_SET.fullmatch(artifact_set or ""):
        raise ReleaseWorkflowError("artifact set must be a lowercase, hyphenated name")
    return {"build_number": build_number, "artifact_set": artifact_set}


def plan(build_number, artifact_set):
    ids = identity(build_number, artifact_set)
    substitutions = {"build": build_number, "set": artifact_set}
    stages = []
    for index, stage in enumerate(STAGES, start=1):
        stages.append({
            "order": index, "id": stage["id"], "title": stage["title"], "owner": stage["owner"],
            "runs": stage["runs"],
            "commands": [command.format(**substitutions) for command in stage["commands"]],
            "receipts": [receipt.format(**substitutions) for receipt in stage["receipts"]],
        })
    return {
        "operation": "release-workflow-plan", "schema_version": 1, **ids,
        "runbook": "docs/release-runbook.md", "dispatches": False, "phone_operations": [],
        "stages": stages,
    }


def _small_json(path):
    """Read a receipt without following symlinks or opening large files."""
    if path.is_symlink():
        raise ReleaseWorkflowError(f"receipt is a symlink: {path}")
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_RECEIPT_BYTES:
        raise ReleaseWorkflowError(f"receipt larger than {MAX_RECEIPT_BYTES} bytes: {path}")
    try:
        return json.loads(path.read_bytes())
    except ValueError as exc:
        raise ReleaseWorkflowError(f"receipt is not JSON: {path}") from exc


def _source_records(root, build_number):
    found = []
    reports = root / "reports"
    if not reports.is_dir():
        return found
    for path in sorted(reports.glob("*/source-installed.json")):
        record = _small_json(path)
        if isinstance(record, dict) and record.get("build_number") == build_number:
            rows = record.get("source_inventory")
            found.append({
                "path": str(path.relative_to(root)),
                "source_files": len(rows) if isinstance(rows, list) else None,
                "transaction": record.get("transaction"),
            })
    return found


def _signing(root, artifact_set):
    base = root / "artifacts/avb/nezha" / artifact_set
    stages = {}
    for stage in SIGNING_STAGES:
        receipt = _small_json(base / "stage-logs" / f"{stage}.exit.json")
        if receipt is None:
            stages[stage] = "missing"
        else:
            code = receipt.get("exit_code", receipt.get("returncode"))
            stages[stage] = "passed" if code == 0 else f"failed:{code}"
    published = base / "published-inventory.json"
    stages["published-inventory"] = "present" if published.is_file() and not published.is_symlink() else "missing"
    return stages


def _bundle(root, artifact_set):
    base = root / "artifacts/flash/nezha" / artifact_set
    manifest = _small_json(base / "manifest.json")
    sums = base / "SHA256SUMS"
    if manifest is None:
        return {"status": "missing"}
    payloads = manifest.get("images", manifest.get("payloads"))
    return {
        "status": "present",
        "payload_count": len(payloads) if isinstance(payloads, (list, dict)) else None,
        "sha256sums": sums.is_file() and not sums.is_symlink(),
        "build_number": manifest.get("build_number"),
        "manifest_status": manifest.get("status"),
        "flash_ready": manifest.get("flash_ready"),
    }


def check(build_number, artifact_set, root=ROOT):
    ids = identity(build_number, artifact_set)
    root = Path(root)
    sources = _source_records(root, build_number)
    candidate = root / "artifacts/device-candidates" / artifact_set / "admission.json"
    signing = _signing(root, artifact_set)
    supers = sorted(str(p.relative_to(root)) for p in (root / "artifacts/build-validation").glob("*-super-transfer-v*/transfer.json")) \
        if (root / "artifacts/build-validation").is_dir() else []
    bundle = _bundle(root, artifact_set)
    stages = {
        "source": "complete" if sources else "missing",
        "candidate": "complete" if candidate.is_file() and not candidate.is_symlink() else "missing",
        "native": "not-checked-on-host",
        "transfer": "not-checked-on-host",
        "signing": "complete" if all(value in ("passed", "present") for value in signing.values()) else "incomplete",
        "super": "receipts-found" if supers else "missing",
        "qualification": "not-checked",
        "bundle": "complete" if bundle["status"] == "present" and bundle.get("sha256sums") else "missing",
    }
    if bundle.get("build_number") not in (None, build_number):
        stages["bundle"] = f"identity-mismatch:{bundle['build_number']}"
    complete = all(value in ("complete", "receipts-found", "not-checked-on-host", "not-checked") for value in stages.values())
    return {
        "operation": "release-workflow-check", "schema_version": 1, **ids,
        "root": str(root), "dispatches": False, "phone_operations": [],
        "stages": stages,
        "details": {"source_records": sources, "signing": signing, "super_transfers": supers, "bundle": bundle},
        "all_host_receipts_present": complete,
        "note": "Receipt presence is not qualification, admission or a device result.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "check"):
        command = commands.add_parser(name)
        command.add_argument("--build-number", required=True)
        command.add_argument("--artifact-set", required=True)
        if name == "check":
            command.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan(args.build_number, args.artifact_set)
            code = 0
        else:
            result = check(args.build_number, args.artifact_set, args.root)
            code = 0 if result["all_host_receipts_present"] else 1
    except ReleaseWorkflowError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
