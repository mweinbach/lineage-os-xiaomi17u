#!/usr/bin/env python3
"""Plan and check the Nezha release sequence for one build identity.

`plan` prints the ordered stages from docs/release-runbook.md with concrete
command templates for the selected identity. `check` reports which stage
receipts already exist for that identity under the ignored artifact roots. It
recognizes two layouts: the f9e-era layout (`reports/<run>/source-installed.json`,
`*-package-transfer-v*`, `*-super-transfer-v*`) and the per-set delivery layout
used from the userdebug sets onward (`reports/<topic>/source-revision-N/`,
`artifacts/build-validation/<set>-admit`, `<set>-transfer`, a host workflow
status file and a reviewed delivery plan bound to the bundle by hash).

Neither command dispatches a build, signs, assembles, or contacts a phone, and
neither reads an image body: only small JSON receipts are opened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD_NUMBER = re.compile(r"^nezha\.[0-9a-f]{24}$")
ARTIFACT_SET = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_RECEIPT_BYTES = 4 * 1024 * 1024
SIGNING_STAGES = (
    "01-inventory", "02-materialize", "03-prepare",
    "04-sign", "05-reconcile", "06-published-inventory",
)
SOURCE_RECORD_GLOBS = ("*/source-installed.json", "*/*/source-installed.json")
QUALIFICATION_GLOBS = ("*/*-host-workflow-status.json", "*/qualification-summary.json")
PLAN_GLOBS = ("*/*delivery-plan*.json", "*/*/*delivery-plan*.json")
ACCEPTABLE = frozenset({
    "complete", "receipts-found", "not-checked-on-host", "not-checked", "in-guest-not-checked-on-host",
    "admitted", "verified", "host-workflow:passed",
})

STAGES = (
    {
        "id": "source", "title": "Select source and record the inventory",
        "owner": "host", "runs": "reviewed source transaction",
        "commands": ["python3 reports/<run>/prepare_*.py  # per-build transaction; records source-installed.json"],
        "receipts": ["reports/*/source-installed.json or reports/*/source-revision-*/source-installed.json "
                     "with build_number {build}"],
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
        "receipts": ["artifacts/device-candidates/{set}/admission.json, or the tree generated in the guest "
                     "behind the package admission of {build}"],
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
        "receipts": ["guest /work/validation/<family>/<timestamp>/result.json exit 0",
                     "artifacts/build-validation/{set}-admit/admission.json with build_number {build} (package admission)"],
    },
    {
        "id": "transfer", "title": "Transfer the archive to the host",
        "owner": "host", "runs": "scripts/target_files_archive_copy.py",
        "commands": ["python3 reports/<run>/package_transfer_*.py  # wraps target_files_archive_copy.py"],
        "receipts": ["artifacts/build-validation/{set}-transfer/transfer.json verified, archive hash equal to the admission",
                     "or artifacts/build-validation/*-package-transfer-v*/transfer.json for {build}"],
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
        "receipts": ["super entry in artifacts/build-validation/{set}-transfer/transfer.json",
                     "or artifacts/build-validation/*-super-transfer-v*/transfer.json for {build}; "
                     "the hash must equal the bundle's Super"],
    },
    {
        "id": "qualification", "title": "Qualify off-device",
        "owner": "host and guest", "runs": "qualification adapters and the joined summary",
        "commands": ["python3 reports/<run>/qualification-prep/host/verify.py --config <actual> --expected-sha256 <sha> --execute",
                     "python3 reports/<run>/finish_*_host_delivery.py  # per-set host gates and workflow status"],
        "receipts": ["reports/*/<ver>-host-workflow-status.json with build_number {build} and passed true",
                     "or reports/*/qualification-summary.json for build {build}"],
    },
    {
        "id": "bundle", "title": "Plan and assemble the bundle",
        "owner": "host", "runs": "scripts/experimental_flash_bundle.py",
        "commands": [
            "python3 scripts/experimental_flash_bundle.py assemble --plan <delivery-plan.json> --expected-plan-sha256 <sha> "
            "--super <super.img> --output " + str(ROOT / "artifacts/flash/nezha/{set}"),
            "python3 scripts/experimental_flash_bundle.py verify --bundle artifacts/flash/nezha/{set} --expected-manifest-sha256 <sha>",
        ],
        "receipts": ["artifacts/flash/nezha/{set}/manifest.json", "artifacts/flash/nezha/{set}/SHA256SUMS",
                     "manifest build_number {build}, or reviewed_plan_sha256 equal to a reports/*/*delivery-plan*.json "
                     "that names {build} and {set}"],
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


def _small_bytes(path):
    """Read a receipt without following symlinks or opening large files."""
    if path.is_symlink():
        raise ReleaseWorkflowError(f"receipt is a symlink: {path}")
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_RECEIPT_BYTES:
        raise ReleaseWorkflowError(f"receipt larger than {MAX_RECEIPT_BYTES} bytes: {path}")
    return path.read_bytes()


def _small_json(path):
    raw = _small_bytes(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ReleaseWorkflowError(f"receipt is not JSON: {path}") from exc


def _scan(root, base, globs):
    """Yield (path, raw bytes) for glob matches, skipping symlinks and oversized files.

    A broad scan over ignored report trees must not fail on an unrelated file;
    fixed-path receipts keep the strict behaviour of `_small_bytes`.
    """
    if not base.is_dir():
        return
    seen = set()
    for pattern in globs:
        for path in sorted(base.glob(pattern)):
            if path in seen or path.is_symlink() or not path.is_file():
                continue
            seen.add(path)
            if path.stat().st_size > MAX_RECEIPT_BYTES:
                continue
            yield path, path.read_bytes()


def _json_or_none(raw):
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _rel(root, path):
    return str(path.relative_to(root))


def _source_records(root, build_number):
    found = []
    for path, raw in _scan(root, root / "reports", SOURCE_RECORD_GLOBS):
        record = _json_or_none(raw)
        if record and record.get("build_number") == build_number:
            rows = record.get("source_inventory")
            found.append({
                "path": _rel(root, path),
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


def _package_admission(root, artifact_set):
    path = root / "artifacts/build-validation" / f"{artifact_set}-admit" / "admission.json"
    record = _small_json(path)
    if not isinstance(record, dict):
        return None
    archive = record.get("archive") if isinstance(record.get("archive"), dict) else {}
    return {
        "path": _rel(root, path), "operation": record.get("operation"),
        "build_number": record.get("build_number"), "archive_sha256": archive.get("sha256"),
        "phone_accessed": record.get("phone_accessed"), "complete_rom_ready": record.get("complete_rom_ready"),
    }


def _candidate_status(build_number, candidate, admission):
    """The f9e layout writes a host device-candidate admission; the per-set layout
    generates the tree inside the guest and leaves only the package admission."""
    if candidate.is_file() and not candidate.is_symlink():
        return "complete"
    if admission and admission["build_number"] == build_number:
        return "in-guest-not-checked-on-host"
    return "missing"


def _native_status(build_number, admission):
    if admission is None:
        return "not-checked-on-host"
    if admission["build_number"] != build_number:
        return f"identity-mismatch:{admission['build_number']}"
    if admission["phone_accessed"] or admission["complete_rom_ready"]:
        return "admission-overclaims"
    return "admitted"


def _transfer(root, build_number, artifact_set, admission):
    validation = root / "artifacts/build-validation"
    candidates = [validation / f"{artifact_set}-transfer" / "transfer.json"]
    if validation.is_dir():
        candidates += sorted(path for path in validation.glob("*-package-transfer-v*/transfer.json")
                             if not path.is_symlink())
    for path in candidates:
        record = _small_json(path)
        if not isinstance(record, dict):
            continue
        if "build_number" in record and record["build_number"] != build_number:
            continue
        archive = record.get("archive") or record.get("file") or {}
        super_image = record.get("super") if isinstance(record.get("super"), dict) else {}
        row = {
            "path": _rel(root, path), "operation": record.get("operation"),
            "verified": record.get("verified") is True,
            "archive_sha256": archive.get("sha256") if isinstance(archive, dict) else None,
            "super_sha256": super_image.get("sha256"), "super_size_bytes": super_image.get("size_bytes"),
        }
        if admission and admission.get("archive_sha256") and row["archive_sha256"]:
            row["archive_matches_admission"] = admission["archive_sha256"] == row["archive_sha256"]
        return row
    return None


def _transfer_status(transfer):
    if transfer is None:
        return "not-checked-on-host"
    if transfer["verified"] and transfer.get("archive_matches_admission") is not False:
        return "verified"
    return "unverified"


def _super_receipts(root, build_number, transfer):
    rows = []
    if transfer and transfer.get("super_sha256"):
        rows.append({"path": transfer["path"], "kind": "set-transfer", "sha256": transfer["super_sha256"],
                     "size_bytes": transfer.get("super_size_bytes"), "verified": transfer["verified"]})
    validation = root / "artifacts/build-validation"
    if validation.is_dir():
        for path in sorted(validation.glob("*-super-transfer-v*/transfer.json")):
            if path.is_symlink():
                continue
            record = _small_json(path)
            if isinstance(record, dict) and record.get("build_number") == build_number:
                image = record.get("file") if isinstance(record.get("file"), dict) else {}
                rows.append({"path": _rel(root, path), "kind": "super-transfer", "sha256": image.get("sha256"),
                             "size_bytes": image.get("size_bytes"), "verified": record.get("verified") is True})
    return rows


def _super_status(receipts, bundle_super_sha256):
    if not receipts:
        return "missing"
    known = {row["sha256"] for row in receipts if row.get("sha256")}
    if bundle_super_sha256 and known and bundle_super_sha256 not in known:
        return "bundle-mismatch"
    return "receipts-found"


def _qualification(root, build_number):
    rows = []
    for path, raw in _scan(root, root / "reports", QUALIFICATION_GLOBS):
        record = _json_or_none(raw)
        if record and record.get("build_number") == build_number:
            rows.append({
                "path": _rel(root, path),
                "kind": "host-workflow" if path.name.endswith("-host-workflow-status.json") else "qualification-summary",
                "passed": record.get("passed"), "stage": record.get("stage"),
                "completed": record.get("completed"), "phone_accessed": record.get("phone_accessed"),
                "flash_authorized": record.get("flash_authorized"),
            })
    return rows


def _qualification_status(rows):
    if not rows:
        return "not-checked"
    if any(row["passed"] is False for row in rows):
        return "host-workflow:failed"
    if all(row["passed"] is True for row in rows):
        return "host-workflow:passed"
    return "host-workflow:incomplete"


def _reviewed_plan(root, plan_sha256):
    if not isinstance(plan_sha256, str) or not SHA256.fullmatch(plan_sha256):
        return None
    for path, raw in _scan(root, root / "reports", PLAN_GLOBS):
        if hashlib.sha256(raw).hexdigest() != plan_sha256:
            continue
        record = _json_or_none(raw) or {}
        return {"path": _rel(root, path), "sha256": plan_sha256,
                "build_number": record.get("build_number"), "artifact_set_id": record.get("artifact_set_id")}
    return None


def _bundle(root, artifact_set):
    base = root / "artifacts/flash/nezha" / artifact_set
    manifest = _small_json(base / "manifest.json")
    sums = base / "SHA256SUMS"
    if manifest is None:
        return {"status": "missing"}
    payloads = manifest.get("images", manifest.get("payloads"))
    super_sha256 = None
    if isinstance(manifest.get("super"), dict):
        super_sha256 = manifest["super"].get("sha256")
    if super_sha256 is None and isinstance(payloads, list):
        for row in payloads:
            if isinstance(row, dict) and row.get("role") == "super":
                super_sha256 = row.get("sha256")
    build_number = manifest.get("build_number")
    identity_source = "manifest" if build_number else None
    reviewed_plan = None
    if build_number is None:
        reviewed_plan = _reviewed_plan(root, manifest.get("reviewed_plan_sha256"))
        if reviewed_plan:
            build_number = reviewed_plan["build_number"]
            identity_source = "reviewed-plan"
    return {
        "status": "present",
        "payload_count": len(payloads) if isinstance(payloads, (list, dict)) else None,
        "sha256sums": sums.is_file() and not sums.is_symlink(),
        "build_number": build_number, "identity_source": identity_source, "reviewed_plan": reviewed_plan,
        "super_sha256": super_sha256,
        "manifest_status": manifest.get("status"),
        "flash_ready": manifest.get("flash_ready"),
    }


def _bundle_status(build_number, artifact_set, bundle):
    if bundle["status"] != "present" or not bundle.get("sha256sums"):
        return "missing"
    if bundle.get("build_number") not in (None, build_number):
        return f"identity-mismatch:{bundle['build_number']}"
    plan_set = (bundle.get("reviewed_plan") or {}).get("artifact_set_id")
    if plan_set not in (None, artifact_set):
        return f"set-mismatch:{plan_set}"
    return "complete"


def check(build_number, artifact_set, root=ROOT):
    ids = identity(build_number, artifact_set)
    root = Path(root)
    sources = _source_records(root, build_number)
    candidate = root / "artifacts/device-candidates" / artifact_set / "admission.json"
    admission = _package_admission(root, artifact_set)
    transfer = _transfer(root, build_number, artifact_set, admission)
    signing = _signing(root, artifact_set)
    supers = _super_receipts(root, build_number, transfer)
    qualification = _qualification(root, build_number)
    bundle = _bundle(root, artifact_set)
    stages = {
        "source": "complete" if sources else "missing",
        "candidate": _candidate_status(build_number, candidate, admission),
        "native": _native_status(build_number, admission),
        "transfer": _transfer_status(transfer),
        "signing": "complete" if all(value in ("passed", "present") for value in signing.values()) else "incomplete",
        "super": _super_status(supers, bundle.get("super_sha256")),
        "qualification": _qualification_status(qualification),
        "bundle": _bundle_status(build_number, artifact_set, bundle),
    }
    complete = all(value in ACCEPTABLE for value in stages.values())
    return {
        "operation": "release-workflow-check", "schema_version": 2, **ids,
        "root": str(root), "dispatches": False, "phone_operations": [],
        "stages": stages,
        "details": {"source_records": sources, "package_admission": admission, "transfer": transfer,
                    "signing": signing, "super_receipts": supers, "qualification": qualification, "bundle": bundle},
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
