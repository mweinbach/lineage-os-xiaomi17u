#!/usr/bin/env python3
"""Stage exact original-signed WLC bytes offline; never activate the component."""
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
CONTRACT = ROOT / "config/nezha-workload-classifier.json"
CONTRACT_SHA256 = "93f046535ad666ed24bc6c98e963270421fe9baf8cba808e1b699765ce84f8e8"
TEMPLATES = ROOT / "templates/workload-classifier"
PRIVATE = "vendor/xiaomi/nezha-workload-classifier"
PUBLIC = "device/xiaomi/nezha/workload-classifier"
RECEIPT = "workload-classifier-inputs.json"
LIMIT = 2 * 1024 * 1024


class WorkloadInputError(ValueError):
    pass


def require(value, message):
    if not value:
        raise WorkloadInputError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def relative(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./+-]+", value),
            "unsafe relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(p not in {"", ".", ".."} for p in value.split("/")), "noncanonical relative path")
    return value


def directory(path):
    path = Path(os.path.abspath(path))
    for item in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(item.lstat().st_mode), "symlink or non-directory ancestor")
    return path


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_regular(path, expected=None):
    path = Path(os.path.abspath(path))
    directory(path.parent)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= LIMIT, "not a bounded regular file")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        require(signature(before) == signature(os.fstat(stream.fileno())), "input replaced")
        raw = stream.read(LIMIT + 1)
        require(signature(before) == signature(os.fstat(stream.fileno())) == signature(path.lstat())
                and len(raw) == before.st_size, "input changed during read")
    if expected is not None:
        require(digest(raw) == expected["sha256"] and len(raw) == expected["size_bytes"],
                "input hash or size mismatch: " + path.name)
    return raw


def contract():
    raw = read_regular(CONTRACT)
    require(digest(raw) == CONTRACT_SHA256, "unreviewed workload-classifier contract")
    spec = json.loads(raw)
    require(spec["activated"] is False and spec["device"] == "nezha", "inactive Nezha contract required")
    return spec, raw


def selection(spec):
    paths, groups, captures = set(), set(), set()
    for item in spec["files"]:
        name = relative(item["path"])
        capture = item["capture_path"]
        require(name == "proprietary/system_ext" + capture, "capture/runtime path mismatch")
        group = item["filegroup"]
        require(re.fullmatch(r"nezha_wlc_[A-Za-z0-9_]+", group), "unsafe filegroup")
        require(name not in paths and group not in groups and capture not in captures, "duplicate input")
        paths.add(name)
        groups.add(group)
        captures.add(capture)
    require(paths, "empty input selection")
    return paths


def capture_inputs(source, spec):
    source = directory(source)
    selection(spec)
    receipt = json.loads(read_regular(source / "receipt.json"))
    require(receipt["operation"] == "erofs-capture" and
            receipt["image"]["sha256"] == spec["system_ext_image_sha256"] and
            receipt["image_mounted"] is False and receipt["firmware_executed"] is False,
            "capture is not selected non-executing factory readback")
    rows = receipt["files"]
    require(len(rows) == len(spec["files"]) and len({r["path"] for r in rows}) == len(rows),
            "duplicate or missing capture row")
    indexed = {r["path"]: r for r in rows}
    require(set(indexed) == {r["capture_path"] for r in spec["files"]}, "capture selection mismatch")
    result, outputs = {}, set()
    for item in spec["files"]:
        row = indexed[item["capture_path"]]
        name = relative(row["output_path"])
        require(name.startswith("files/") and name not in outputs, "unsafe or duplicate capture output")
        outputs.add(name)
        require(row["type"] == "regular" and row["readback_verified"] is True and
                all(row[k] == item[k] for k in ("sha256", "size_bytes")), "capture identity mismatch")
        result[item["path"]] = read_regular(source / name, item)
    return result


def layout(spec, raw_contract, inputs):
    paths = selection(spec)
    require(set(inputs) == paths, "incomplete inputs")
    result = {}
    for item in spec["files"]:
        raw = inputs[item["path"]]
        require(digest(raw) == item["sha256"] and len(raw) == item["size_bytes"], "input hash or size mismatch")
        result[PRIVATE + "/" + item["path"]] = raw
    for item in spec["templates"]:
        name = relative(item["path"])
        raw = read_regular(TEMPLATES / name)
        require(digest(raw) == item["sha256"], "unreviewed WLC template")
        result[PUBLIC + "/" + name] = raw
    item = spec["build_guard"]
    guard = read_regular(TEMPLATES / relative(item["path"]))
    require(digest(guard) == item["sha256"], "unreviewed WLC build guard")
    marker = b"EXPECTED = {}  # Replaced by the reviewed generator; never loaded from a receipt."
    require(guard.count(marker) == 1, "missing WLC build identity marker")
    expected = {row["path"]: {key: row[key] for key in ("sha256", "size_bytes")} for row in spec["files"]}
    result[PRIVATE + "/tools/verify_inputs.py"] = guard.replace(marker, ("EXPECTED = " + repr(expected)).encode())
    bp = ['// Disabled candidate: no Android.bp is emitted.', 'soong_namespace {}', '',
          'python_binary_host {', '    name: "nezha_wlc_input_verifier",',
          '    main: "tools/verify_inputs.py",', '    srcs: ["tools/verify_inputs.py"],',
          '    visibility: [":__pkg__"],', '}', '', 'genrule {',
          '    name: "nezha_wlc_verified_inputs",', '    tools: ["nezha_wlc_input_verifier"],',
          '    visibility: [":__pkg__"],', '    srcs: ' + json.dumps(sorted(paths)) + ',',
          '    out: ' + json.dumps(["verified/" + p for p in sorted(paths)]) + ',',
          '    cmd: "$(location nezha_wlc_input_verifier) --output-dir $(genDir) $(in)",', '}', '']
    for item in spec["files"]:
        bp += ['filegroup {', '    name: "' + item["filegroup"] + '",',
               '    srcs: [":nezha_wlc_verified_inputs{verified/' + item["path"] + '}"],',
               '    visibility: ["//' + PUBLIC + ':__pkg__"],', '}', '']
    result[PRIVATE + "/Android.bp.in"] = ("\n".join(bp) + "\n").encode()
    receipt = {"schema_version": 1, "device": "nezha", "contract_sha256": digest(raw_contract),
               "input_count": len(paths), "input_bytes": sum(len(v) for v in inputs.values()),
               "private_bytes_verified": True, "activation_allowed": False,
               "original_apk_bytes_preserved": True, "signing_performed": False,
               "android_build_verified": False, "phone_accessed": False,
               "open_gates": spec["blockers"],
               "files": [{"path": p, "sha256": digest(v), "size_bytes": len(v)}
                         for p, v in sorted(result.items())]}
    result[RECEIPT] = encoded(receipt)
    return result


def verify(packet, spec=None, raw=None):
    if spec is None:
        spec, raw = contract()
    packet = directory(packet)
    inputs = {row["path"]: read_regular(packet / PRIVATE / relative(row["path"]), row)
              for row in spec["files"]}
    expected = layout(spec, raw, inputs)
    actual = set()
    for parent, dirs, files in os.walk(packet, followlinks=False):
        for name in dirs:
            require(not (Path(parent) / name).is_symlink(), "symlink packet directory")
        for name in files:
            path = Path(parent) / name
            rel = path.relative_to(packet).as_posix()
            require(rel in expected, "unexpected packet file: " + rel)
            require(read_regular(path) == expected[rel], "packet content mismatch: " + rel)
            actual.add(rel)
    require(actual == set(expected), "missing packet file")
    return json.loads(expected[RECEIPT])


def prepare(source, destination):
    spec, raw = contract()
    source = directory(source)
    destination = Path(os.path.abspath(destination))
    require(not destination.exists() and not destination.is_symlink(), "destination already exists")
    directory(destination.parent)
    require(not source.is_relative_to(destination) and not destination.is_relative_to(source), "input/output overlap")
    plan = layout(spec, raw, capture_inputs(source, spec))
    staging = Path(tempfile.mkdtemp(prefix=".wlc-candidate-", dir=destination.parent))
    try:
        for name, content in plan.items():
            output = staging / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
        receipt = verify(staging, spec, raw)
        require(layout(spec, raw, capture_inputs(source, spec)) == plan, "input changed before publication")
        publish_new_directory(staging, destination)
        return receipt
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def require_admission(receipt):
    raise WorkloadInputError("WLC activation blocked: signer/domain, hidden API/perf JNI, libtflite ABI, "
                             "permissions, broadcast boundary and device gates remain open")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("prepare")
    stage.add_argument("--capture-root", type=Path, required=True)
    stage.add_argument("--output", type=Path, required=True)
    for name in ("verify", "assert-ready"):
        sub.add_parser(name).add_argument("--packet", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            output = Path(os.path.abspath(args.output))
            require(output.is_relative_to(ROOT / "artifacts") and output != ROOT / "artifacts",
                    "output must be a new directory below this worktree's ignored artifacts/")
            receipt = prepare(args.capture_root, output)
        else:
            receipt = verify(args.packet)
        if args.command == "assert-ready":
            require_admission(receipt)
        print(json.dumps({k: receipt[k] for k in ("device", "input_count", "input_bytes",
              "private_bytes_verified", "activation_allowed", "android_build_verified", "open_gates")}, indent=2))
        return 0
    except (WorkloadInputError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("WLC candidate: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
