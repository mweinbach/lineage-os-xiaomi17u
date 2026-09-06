#!/usr/bin/env python3
"""Enumerate every non-upstream input a Nezha build depends on, by hash.

The source lock pins the 1,179 upstream projects. This tool records the rest:
the authored device, kernel, policy, recovery and tooling files in this
repository, every patch and the contract that pins it, the container image
pins, and the identities of the private input bundles the caller names. It
never copies private file lists or bytes into the manifest; a private receipt
contributes its own hash and a few declared totals.

`generate` writes the manifest and prints its closure hash. `verify` recomputes
the manifest from the same tree and receipts and reports what changed. Neither
command runs Git, a build, a container or a phone command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
OPERATION = "nezha-input-closure"
AUTHORED_ROOTS = (
    "Makefile", "config", "device", "kernel", "policy", "recovery", "patches",
    "containers", "templates", "tools", "manifests", "scripts",
)
SKIP_NAMES = frozenset({"__pycache__", ".DS_Store"})
SKIP_SUFFIXES = (".pyc", ".pyo")
# Suffixes .gitignore excludes everywhere; such a file under an authored root is
# a stray local artifact, listed but never part of the closure.
IGNORED_SUFFIXES = (".img", ".bin", ".apk", ".apex", ".zip", ".tgz", ".tar",
                    ".pem", ".pk8", ".key", ".sparseimage", ".dmg")
SOURCE_LOCK = "config/evolution-source-lock.json"
SOURCES = "config/sources.json"
BASE_IMAGE = "containers/apple/base-image.json"
APPLE_CONFIG = "config/apple-container.json"
MAX_JSON_BYTES = 8 * 1024 * 1024
DECLARED_RECEIPT_KEYS = (
    "schema_version", "operation", "purpose", "contract_sha256", "file_count",
    "total_bytes", "build_number", "transaction", "artifact_set_id", "created_at_utc",
)


class InputClosureError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputClosureError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _regular(path, description):
    require(not path.is_symlink(), f"{description} is a symlink: {path}")
    require(path.is_file(), f"{description} is missing: {path}")
    return path


def _json(path, description):
    _regular(path, description)
    require(path.stat().st_size <= MAX_JSON_BYTES, f"{description} exceeds {MAX_JSON_BYTES} bytes: {path}")
    try:
        return json.loads(path.read_bytes())
    except ValueError as exc:
        raise InputClosureError(f"{description} is not valid JSON: {path}") from exc


def _row(root, path):
    digest, size = sha256_file(path)
    return {"path": path.relative_to(root).as_posix(), "size_bytes": size, "sha256": digest}


def _is_ignored(name):
    lowered = name.lower()
    return lowered.endswith(IGNORED_SUFFIXES) or ".tar." in lowered


def _walk(root, start):
    """Yield regular files below start in a deterministic order; refuse symlinks."""
    pending = [start]
    while pending:
        current = pending.pop()
        require(not current.is_symlink(), f"symlink under an authored root: {current}")
        if current.is_dir():
            children = sorted(current.iterdir(), key=lambda child: child.name, reverse=True)
            for child in children:
                if child.name in SKIP_NAMES or child.name.endswith(SKIP_SUFFIXES):
                    continue
                pending.append(child)
        elif current.is_file():
            yield current


def authored(root):
    files, excluded = [], []
    for name in AUTHORED_ROOTS:
        start = root / name
        if not start.exists() and not start.is_symlink():
            continue
        for path in _walk(root, start):
            if _is_ignored(path.name):
                excluded.append(path.relative_to(root).as_posix())
            else:
                files.append(_row(root, path))
    files.sort(key=lambda row: row["path"])
    return {"roots": list(AUTHORED_ROOTS), "file_count": len(files), "files": files,
            "excluded_ignored_files": sorted(excluded)}


def upstream(root):
    lock = _json(root / SOURCE_LOCK, "source lock")
    snapshot = lock["snapshot"]
    snapshot_path = root / snapshot["path"]
    digest, size = sha256_file(_regular(snapshot_path, "source snapshot"))
    require(digest == snapshot["sha256"] and size == snapshot["bytes"],
            "source snapshot bytes do not match the source lock")
    sources = _json(root / SOURCES, "source configuration")
    references = sorted(
        ({"name": item["name"], "url": item["url"], "commit": item["commit"]} for item in sources["references"]),
        key=lambda item: item["name"],
    )
    return {
        "source_lock": {"path": SOURCE_LOCK, "manifest": lock["manifest"], "repo": lock["repo"],
                        "snapshot": {**snapshot, "verified": True}},
        "references": references,
    }


def _declared_patch(contract, contract_path):
    """Return (patch path, declared sha256) for the two contract styles, or None."""
    patch = contract.get("patch")
    if isinstance(patch, dict) and isinstance(patch.get("sha256"), str) and isinstance(patch.get("path"), str):
        return patch["path"], patch["sha256"]
    if isinstance(patch, str) and isinstance(contract.get("patch_sha256"), str):
        return patch, contract["patch_sha256"]
    return None


def patches(root):
    base = root / "patches"
    patch_rows = {}
    bindings = {}
    unbound = []
    if base.is_dir():
        for path in _walk(root, base):
            if path.suffix == ".patch":
                row = _row(root, path)
                row["contracts"] = []
                patch_rows[row["path"]] = row
        for path in _walk(root, base):
            if path.suffix != ".json":
                continue
            contract = _json(path, "patch contract")
            declared = _declared_patch(contract, path) if isinstance(contract, dict) else None
            relative = path.relative_to(root).as_posix()
            if declared is None:
                unbound.append(relative)
                continue
            declared_path, declared_sha = declared
            target = (root / declared_path) if "/" in declared_path else (path.parent / declared_path)
            target_key = target.resolve().relative_to(root.resolve()).as_posix() if target.exists() else None
            require(target_key in patch_rows, f"{relative} names a patch that is not present: {declared_path}")
            require(patch_rows[target_key]["sha256"] == declared_sha,
                    f"{relative} pins a different hash than its patch file {target_key}")
            patch_rows[target_key]["contracts"].append(relative)
            bindings[relative] = target_key
    for row in patch_rows.values():
        row["contracts"].sort()
    return {
        "patch_files": [patch_rows[key] for key in sorted(patch_rows)],
        "contracts_checked": dict(sorted(bindings.items())),
        "unbound_contracts": sorted(unbound),
    }


def environment(root):
    result = {}
    base_image = root / BASE_IMAGE
    if base_image.exists() or base_image.is_symlink():
        image = _json(base_image, "base image record")
        result["base_image"] = {key: image.get(key) for key in
                                ("registry", "tag_used_for_discovery", "platform", "index_digest",
                                 "arm64_manifest_digest", "config_digest")}
    apple = root / APPLE_CONFIG
    if apple.exists() or apple.is_symlink():
        config = _json(apple, "Apple Container configuration")
        result["builder"] = {key: config.get(key) for key in ("image", "volume") if key in config}
    return result


def private_receipts(root, receipt_paths):
    rows = []
    seen = set()
    for raw in receipt_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        _regular(path, "private receipt")
        resolved = path.resolve()
        require(resolved.is_relative_to(root.resolve()), f"private receipt is outside the workspace: {raw}")
        relative = resolved.relative_to(root.resolve()).as_posix()
        require(relative not in seen, f"private receipt listed twice: {relative}")
        seen.add(relative)
        receipt = _json(path, "private receipt")
        require(isinstance(receipt, dict), f"private receipt must be a JSON object: {relative}")
        digest, size = sha256_file(path)
        declared = {key: receipt[key] for key in DECLARED_RECEIPT_KEYS
                    if key in receipt and isinstance(receipt[key], (str, int, float, bool))}
        rows.append({
            "path": relative, "size_bytes": size, "sha256": digest, "declared": declared,
            "inventory_rows": next((len(receipt[key]) for key in ("source_inventory", "files")
                                    if isinstance(receipt.get(key), list)), None),
        })
    rows.sort(key=lambda row: row["path"])
    return rows


def generate(root=ROOT, receipt_paths=()):
    root = Path(root)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "upstream": upstream(root),
        "patches": patches(root),
        "authored": authored(root),
        "environment": environment(root),
        "private_receipts": private_receipts(root, receipt_paths),
        "scope": {
            "upstream_projects_pinned_by_source_lock": True,
            "private_bytes_or_file_lists_copied": False,
            "build_dispatched": False,
            "reproducibility_proven": False,
            "note": "Matching closure hashes mean the same inputs were selected, not that a build from them is bit-identical.",
        },
    }
    manifest["closure_sha256"] = hashlib.sha256(canonical(manifest)).hexdigest()
    return manifest


def _index(rows):
    return {row["path"]: row["sha256"] for row in rows}


def _diff(before, after):
    old, new = _index(before), _index(after)
    return {
        "added": sorted(set(new) - set(old)),
        "removed": sorted(set(old) - set(new)),
        "changed": sorted(path for path in set(old) & set(new) if old[path] != new[path]),
    }


def verify(manifest_path, root=ROOT):
    root = Path(root)
    recorded = _json(Path(manifest_path), "closure manifest")
    require(recorded.get("schema_version") == SCHEMA_VERSION and recorded.get("operation") == OPERATION,
            "unsupported closure manifest")
    body = {key: value for key, value in recorded.items() if key != "closure_sha256"}
    require(hashlib.sha256(canonical(body)).hexdigest() == recorded.get("closure_sha256"),
            "closure manifest was edited after generation")
    current = generate(root, [row["path"] for row in recorded["private_receipts"]])
    report = {
        "operation": "nezha-input-closure-verify",
        "recorded_closure_sha256": recorded["closure_sha256"],
        "current_closure_sha256": current["closure_sha256"],
        "matches": recorded["closure_sha256"] == current["closure_sha256"],
        "authored": _diff(recorded["authored"]["files"], current["authored"]["files"]),
        "patches": _diff(recorded["patches"]["patch_files"], current["patches"]["patch_files"]),
        "private_receipts": _diff(recorded["private_receipts"], current["private_receipts"]),
        "upstream_changed": recorded["upstream"] != current["upstream"],
        "environment_changed": recorded["environment"] != current["environment"],
    }
    return report


def _write_new(path, data):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(data, indent=2, sort_keys=True) + "\n").encode())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    generate_command = commands.add_parser("generate", help="Write a new closure manifest")
    generate_command.add_argument("--output", type=Path, required=True)
    generate_command.add_argument("--root", type=Path, default=ROOT)
    generate_command.add_argument("--private-receipt", action="append", default=[],
                                  help="Receipt JSON of a private input bundle; repeatable")
    verify_command = commands.add_parser("verify", help="Recompute a manifest and report differences")
    verify_command.add_argument("--manifest", type=Path, required=True)
    verify_command.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            manifest = generate(args.root, args.private_receipt)
            _write_new(args.output, manifest)
            print(json.dumps({"output": str(args.output), "closure_sha256": manifest["closure_sha256"],
                              "authored_files": manifest["authored"]["file_count"],
                              "patch_files": len(manifest["patches"]["patch_files"]),
                              "private_receipts": len(manifest["private_receipts"])}, indent=2))
            return 0
        report = verify(args.manifest, args.root)
        print(json.dumps(report, indent=2))
        return 0 if report["matches"] else 1
    except (InputClosureError, KeyError, OSError) as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
