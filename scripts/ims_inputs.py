#!/usr/bin/env python3
"""Reproduce and verify the disabled Nezha IMS private-input candidate offline.

No build, source installation, signing, framework shim or device operation is
implemented. Admission always fails while the reviewed closure gaps are open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile

if __package__:
    from .artifact_files import publish_new_directory
else:
    from artifact_files import publish_new_directory


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-ims.json"
CONTRACT_SHA256 = "dec7a21ce71b66713f16bac80279a62695d16fcc451d453b2893918a3f4f7866"
TEMPLATES = ROOT / "templates/ims"
RECEIPT = "ims-inputs.json"
PRIVATE = "vendor/xiaomi/nezha-ims"
PUBLIC = "device/xiaomi/nezha/ims"
LIMIT = 16 * 1024 * 1024


class ImsInputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ImsInputError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def relative(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./@+-]+", value),
            "unsafe relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in {"", ".", ".."} for part in value.split("/")),
            "noncanonical relative path")
    return value


def directory(path):
    path = Path(os.path.abspath(path))
    for parent in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(parent.lstat().st_mode), "non-directory or symlink ancestor")
    return path


def read_regular(path, expected=None):
    path = Path(os.path.abspath(path))
    directory(path.parent)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= LIMIT,
            "input is not a bounded regular file")
    signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mode,
                              info.st_mtime_ns, info.st_ctime_ns)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        require(signature(before) == signature(os.fstat(stream.fileno())), "input replaced")
        raw = stream.read(LIMIT + 1)
        require(signature(before) == signature(os.fstat(stream.fileno())) ==
                signature(path.lstat()) and len(raw) == before.st_size, "input changed during read")
    if expected is not None:
        require(digest(raw) == expected["sha256"] and len(raw) == expected["size_bytes"],
                "input hash or size mismatch: " + path.name)
    return raw


def contract():
    raw = read_regular(CONTRACT)
    require(digest(raw) == CONTRACT_SHA256, "unreviewed IMS contract")
    result = json.loads(raw)
    require(result["activated"] is False and result["device"] == "nezha",
            "contract must remain an inactive Nezha candidate")
    return result, raw


def templates(spec):
    result = {}
    for item in spec["templates"]:
        name = relative(item["path"])
        raw = read_regular(TEMPLATES / name)
        require(digest(raw) == item["sha256"], "unreviewed IMS template: " + name)
        result[f"{PUBLIC}/{name}"] = raw
    return result


def layout(spec, contract_raw, source):
    """Return an immutable byte plan; callers publish only after every check passes."""
    source = directory(source)
    result = templates(spec)
    paths, groups = set(), set()
    filegroups = []
    for item in spec["files"]:
        name = relative(item["path"])
        group = item["filegroup"]
        require(re.fullmatch(r"nezha_ims_[A-Za-z0-9_]+", group), "unsafe filegroup")
        require(name not in paths and group not in groups, "duplicate input path or filegroup")
        require(name.startswith("proprietary/") and item["runtime_path"] ==
                "/" + name.removeprefix("proprietary/"), "runtime path does not match input")
        paths.add(name)
        groups.add(group)
        result[f"{PRIVATE}/{name}"] = read_regular(source / name, item)
        filegroups.extend(['filegroup {', f'    name: "{group}",',
                           f'    srcs: [":nezha_ims_verified_inputs{{verified/{name}}}"],',
                           f'    visibility: ["//{PUBLIC}:__pkg__"],', '}', ''])
    guard_template = spec["build_guard_template"]
    guard = read_regular(TEMPLATES / relative(guard_template["path"]))
    require(digest(guard) == guard_template["sha256"], "unreviewed IMS build guard")
    expected = {row["path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                for row in spec["files"]}
    marker = b"EXPECTED = {}  # Replaced by the reviewed generator; never loaded from a receipt."
    require(guard.count(marker) == 1, "missing IMS build guard identity marker")
    result[f"{PRIVATE}/tools/verify_inputs.py"] = guard.replace(
        marker, ("EXPECTED = " + repr(expected)).encode())
    producer = [
        '// Disabled candidate; review admission before creating Android.bp.',
        'soong_namespace {}', '',
        'python_binary_host {', '    name: "nezha_ims_input_verifier",',
        '    main: "tools/verify_inputs.py",', '    srcs: ["tools/verify_inputs.py"],',
        '    visibility: [":__pkg__"],', '}', '',
        'genrule {', '    name: "nezha_ims_verified_inputs",',
        '    tools: ["nezha_ims_input_verifier"],',
        '    visibility: [":__pkg__"],',
        '    srcs: ' + json.dumps(sorted(paths)) + ',',
        '    out: ' + json.dumps(["verified/" + name for name in sorted(paths)]) + ',',
        '    cmd: "$(location nezha_ims_input_verifier) --output-dir $(genDir) $(in)",',
        '}', '',
    ]
    result[f"{PRIVATE}/Android.bp.in"] = ("\n".join(producer + filegroups) + "\n").encode()
    result[f"{PUBLIC}/admission.mk"] = (
        "# Never include this candidate in a product until its closure is implemented.\n"
        "$(error Nezha IMS admission blocked: OEM API, qtelephony policy and component/image gates remain open)\n"
    ).encode()
    receipt = {
        "schema_version": 1, "device": "nezha", "contract_sha256": digest(contract_raw),
        "input_count": len(paths), "input_bytes": sum(item["size_bytes"] for item in spec["files"]),
        "private_bytes_verified": True, "activation_allowed": False,
        "android_build_verified": False, "signing_performed": False,
        "phone_accessed": False, "open_gates": spec["blockers"],
        "files": [{"path": name, "sha256": digest(raw), "size_bytes": len(raw)}
                  for name, raw in sorted(result.items())],
    }
    result[RECEIPT] = encoded(receipt)
    return result


def verify(packet, spec=None, contract_raw=None):
    if spec is None:
        spec, contract_raw = contract()
    packet = directory(packet)
    expected = layout(spec, contract_raw, packet / PRIVATE)
    actual = set()
    for parent, dirs, files in os.walk(packet, followlinks=False):
        for name in dirs:
            require(not (Path(parent) / name).is_symlink(), "symlink directory in packet")
        for name in files:
            full = Path(parent) / name
            rel = full.relative_to(packet).as_posix()
            require(rel in expected, "unexpected packet file: " + rel)
            require(read_regular(full) == expected[rel], "packet content mismatch: " + rel)
            actual.add(rel)
    require(actual == set(expected), "packet file missing")
    return json.loads(expected[RECEIPT])


def prepare(source, destination):
    spec, raw = contract()
    source = directory(source)
    destination = Path(os.path.abspath(destination))
    require(not destination.exists() and not destination.is_symlink(), "destination already exists")
    directory(destination.parent)
    require(not source.is_relative_to(destination) and not destination.is_relative_to(source),
            "input and output trees overlap")
    plan = layout(spec, raw, source)
    staging = Path(tempfile.mkdtemp(prefix=".ims-candidate-", dir=destination.parent))
    try:
        for name, content in plan.items():
            output = staging / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        receipt = verify(staging, spec, raw)
        # Rejoin original inputs immediately before publication as well as copied bytes.
        require(layout(spec, raw, source) == plan, "inputs changed before publication")
        publish_new_directory(staging, destination)
        return receipt
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def require_admission(receipt):
    # Receipts cannot turn known open engineering work into an approval switch.
    raise ImsInputError("IMS activation blocked: OEM telephony API, qtelephony policy, "
                        "permission/signing, strict component/image and carrier gates remain open")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("prepare", help="copy exact private inputs into an ignored disabled packet")
    stage.add_argument("--private-root", type=Path, required=True)
    stage.add_argument("--output", type=Path, required=True)
    for name in ("verify", "assert-ready"):
        command = sub.add_parser(name)
        command.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            destination = Path(os.path.abspath(args.output))
            artifacts = ROOT / "artifacts"
            require(destination.is_relative_to(artifacts) and destination != artifacts,
                    "output must be a new directory below this worktree's ignored artifacts/")
            receipt = prepare(args.private_root, destination)
        else:
            receipt = verify(args.packet)
        if args.command == "assert-ready":
            require_admission(receipt)
        print(json.dumps({key: receipt[key] for key in
                          ("device", "input_count", "input_bytes", "private_bytes_verified",
                           "activation_allowed", "android_build_verified", "open_gates")}, indent=2))
        return 0
    except (ImsInputError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("IMS candidate: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
