"""Validate an operator's saved Nezha hardware evidence; never access a device."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-hardware-qualification.json"


def contract():
    return json.loads(CONTRACT.read_text())


def template(build_identity):
    if not isinstance(build_identity, str) or not build_identity.strip():
        raise ValueError("An explicit installed build identity is required")
    return {
        "schema_version": 1,
        "device": "nezha",
        "build_identity": build_identity,
        "checks": [{"id": item["id"], "status": "not-run"}
                   for item in contract()["checks"]],
    }


def _evidence(root, item):
    if not isinstance(item, dict):
        raise ValueError("Evidence must be a path/sha256 object")
    name = item.get("path")
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Evidence needs a relative POSIX path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Evidence must stay within the saved evidence directory")
    path = root / relative
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("Evidence is missing or resolves outside the saved directory: " + name)
    if path.samefile(root / "results.json"):
        raise ValueError("A ledger cannot serve as its own behavioral evidence")
    expected = item.get("sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Evidence requires a lowercase SHA-256: " + name)
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    if not size or digest.hexdigest() != expected:
        raise ValueError("Evidence is empty or its SHA-256 differs: " + name)
    return {"path": name, "sha256": expected, "bytes": size}


def analyze(evidence_dir, expected_build_identity):
    """Preserve operator verdicts with verified provenance, without judging logs."""
    root = Path(evidence_dir).resolve()
    record = json.loads((root / "results.json").read_text())
    template(expected_build_identity)  # Validate the independent caller selector.
    if (not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("device") != "nezha"
            or record.get("build_identity") != expected_build_identity):
        raise ValueError("Ledger schema, device or installed build identity differs")
    definitions = contract()
    checks = {item["id"]: item for item in definitions["checks"]}
    supplied = record.get("checks")
    if not isinstance(supplied, list):
        raise ValueError("Ledger checks must be a list")
    results = {}
    for entry in supplied:
        if not isinstance(entry, dict):
            raise ValueError("Each check must be an object")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or identifier not in checks or identifier in results:
            raise ValueError("Unknown or duplicate check ID: " + str(identifier))
        status = entry.get("status")
        if status not in ("not-run", "pass", "fail"):
            raise ValueError("Expected not-run, pass or fail: " + identifier)
        result = {"id": identifier, "area": checks[identifier]["area"], "status": status}
        if status == "not-run":
            if any(key in entry for key in ("observed_at", "observation", "evidence")):
                raise ValueError("not-run check must not carry a measured result: " + identifier)
        else:
            observation = entry.get("observation")
            if not isinstance(observation, str) or not observation.strip():
                raise ValueError("Measured pass/fail requires an operator observation: " + identifier)
            timestamp = entry.get("observed_at")
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError()
            except (AttributeError, TypeError, ValueError):
                raise ValueError("Measured pass/fail requires a timezone-aware observed_at: " + identifier) from None
            evidence = entry.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("Measured pass/fail requires saved evidence: " + identifier)
            result.update(observed_at=timestamp, observation=observation,
                          evidence=[_evidence(root, item) for item in evidence])
        results[identifier] = result
    ordered = [results.get(item["id"], {"id": item["id"], "area": item["area"],
                                        "status": "not-run"})
               for item in definitions["checks"]]
    counts = {state: sum(item["status"] == state for item in ordered)
              for state in ("pass", "fail", "not-run")}
    return {
        "schema_version": 1, "device": "nezha", "build_identity": expected_build_identity,
        "evidence_validation": "valid", "verdict_source": "operator-recorded",
        "counts": counts, "checks": ordered,
        "all_scoped_checks_pass": counts["pass"] == len(ordered),
        "excluded_claims": definitions["excluded_claims"],
        "limits": "Hashes bind saved evidence, not its truth. No logs are automatically scored; service registration never creates a pass. Results do not establish stock parity.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("template", help="Print an all-not-run ledger; writes no files")
    create.add_argument("--build-identity", required=True)
    sub.add_parser("plan", help="Print concrete acceptance checks; execute nothing")
    inspect = sub.add_parser("analyze", help="Read results.json and verify evidence hashes")
    inspect.add_argument("--evidence-dir", type=Path, required=True)
    inspect.add_argument("--build-identity", required=True)
    args = parser.parse_args()
    try:
        if args.command == "template":
            report = template(args.build_identity)
        elif args.command == "plan":
            report = contract()
        else:
            report = analyze(args.evidence_dir, args.build_identity)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    if args.command == "analyze":
        return 0 if report["all_scoped_checks_pass"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
