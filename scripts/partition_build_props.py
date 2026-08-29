#!/usr/bin/env python3
"""Verify and probe the pinned optional-partition property reader correction.

Only hash-bound Python functions are loaded. The probe uses inert properties in
temporary directories and ZIPs; it neither imports Android's source checkout nor
builds, signs, extracts or verifies any Android image or target-files package.
"""

from __future__ import annotations

import argparse
import ast
import copy
import errno
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile

if __package__:
    from .kernel_inputs import KernelInputsError, _json, _read
else:
    from kernel_inputs import KernelInputsError, _json, _read


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "patches/evolution/optional-partition-build-props.json"
PATCH_PATH = "patches/evolution/0008-optional-partition-build-props.patch"
SOURCE_PATH = "build/make/tools/releasetools/common.py"
PROJECT_COMMIT = "a438ca40c6ed779042f806142b1165ba1360a7b2"
MAX_BYTES = 1024 * 1024
SCOPE = {
    "python_partition_property_reader_only": True,
    "full_target_files_verified": False, "metadata_projection_verified": False,
    "vintf_verified": False, "ota_verified": False,
    "source_modified": False, "phone_operations": [],
}


class PartitionBuildPropsError(ValueError):
    """The selected source, patch or actual property reader check mismatched."""


def _require(condition, message):
    if not condition:
        raise PartitionBuildPropsError(message)


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _valid_identity(value):
    return (type(value) is dict and set(value) == {"sha256", "size_bytes"}
            and type(value["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
            and type(value["size_bytes"]) is int
            and 0 < value["size_bytes"] <= MAX_BYTES)


def _contract():
    raw = _read(ROOT / CONTRACT_PATH, limit=MAX_BYTES)
    record = _json(raw)
    _require(type(record.get("schema_version")) is int
             and record["schema_version"] == 1
             and record.get("contract_id") == "nezha-optional-partition-build-props-v1",
             "unsupported partition property contract")
    _require(record.get("project") == {
        "path": "build/make", "commit": PROJECT_COMMIT,
        "repository": "https://github.com/Evolution-X/build", "branch": "bka",
    }, "partition properties require the reviewed bka project")
    patch_row = record.get("patch", {})
    _require(type(patch_row) is dict and patch_row.get("path") == PATCH_PATH,
             "unexpected partition property patch")
    patch = _read(ROOT / PATCH_PATH, limit=MAX_BYTES)
    _require(_identity(patch) == {key: patch_row.get(key)
                                 for key in ("sha256", "size_bytes")},
             "partition property patch differs from its contract")
    _require(re.findall(rb"^--- (.+)$", patch, re.M) == [b"a/tools/releasetools/common.py"]
             and re.findall(rb"^\+\+\+ (.+)$", patch, re.M) == [b"b/tools/releasetools/common.py"],
             "partition property patch must change only common.py")
    rows = record.get("source_files")
    _require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict
             and rows[0].get("path") == SOURCE_PATH
             and _valid_identity(rows[0].get("before"))
             and _valid_identity(rows[0].get("after"))
             and rows[0]["before"] != rows[0]["after"],
             "expected one reviewed common.py transition")
    _require(record.get("validation_scope") == SCOPE,
             "property reader verification must not promote artifact readiness")
    return record, _identity(raw), patch


def _apply_patch(before, patch):
    """Replay exact unified hunks in memory; never invoke patch or write source."""
    lines = before.decode().splitlines(keepends=True)
    patch_lines = patch.decode().splitlines(keepends=True)
    headers = [i for i, line in enumerate(patch_lines) if line.startswith("@@ ")]
    _require(bool(headers), "patch has no source hunks")
    output, cursor = [], 0
    for index, start in enumerate(headers):
        match = re.fullmatch(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", patch_lines[start])
        _require(match is not None, "unexpected source hunk header")
        old_line, old_count, new_line, new_count = map(int, match.groups())
        body = patch_lines[start + 1:headers[index + 1] if index + 1 < len(headers) else None]
        _require(all(line.startswith((" ", "+", "-")) for line in body),
                 "unexpected source hunk content")
        old = [line[1:] for line in body if line.startswith((" ", "-"))]
        new = [line[1:] for line in body if line.startswith((" ", "+"))]
        _require(len(old) == old_count and len(new) == new_count,
                 "source hunk counts differ")
        position = old_line - 1
        _require(position >= cursor and lines[position:position + old_count] == old,
                 "source hunk preimage differs")
        output.extend(lines[cursor:position])
        _require(len(output) == new_line - 1, "source hunk output position differs")
        output.extend(new)
        cursor = position + old_count
    output.extend(lines[cursor:])
    return "".join(output).encode()


def _verified_source(source_tree, before_source_tree=None):
    record, identity, patch = _contract()
    row = record["source_files"][0]
    source = _read(Path(source_tree) / SOURCE_PATH, limit=MAX_BYTES)
    _require(_identity(source) == row["after"], "common.py differs from reviewed patched source")
    replayed = False
    if before_source_tree is not None:
        before = _read(Path(before_source_tree) / SOURCE_PATH, limit=MAX_BYTES)
        _require(_identity(before) == row["before"], "common.py differs from reviewed original source")
        _require(_apply_patch(before, patch) == source, "patch does not reproduce selected common.py")
        replayed = True
    return source, {
        "schema_version": 1, "status": "verified-source", "contract": identity,
        "expected_build_commit": PROJECT_COMMIT,
        "whole_source_tree_verified": False,
        "source": {"path": SOURCE_PATH, **_identity(source)},
        "exact_patch_replayed_in_memory": replayed, "scope": copy.deepcopy(SCOPE),
    }


def _namespace(source):
    """Load only the actual reader and its standard-library helper functions."""
    tree = ast.parse(source)
    names = ("ReadBytesFromInputFile", "ReadFromInputFile", "PartitionMapFromTargetFiles")
    nodes = []
    for name in names:
        matches = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == name]
        _require(len(matches) == 1, "expected one source function: " + name)
        nodes.extend(matches)
    classes = [node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "PartitionBuildProps"]
    _require(len(classes) == 1, "expected one PartitionBuildProps class")
    methods = [node for node in classes[0].body
               if isinstance(node, ast.FunctionDef) and node.name == "_ReadPartitionPropFile"]
    _require(len(methods) == 1, "expected one partition property reader")
    selected_class = copy.deepcopy(classes[0])
    selected_class.body = methods
    selected_class.decorator_list = []
    selected_class.bases = []
    selected_class.keywords = []
    nodes.append(selected_class)
    log = io.StringIO()
    logger = logging.Logger("verified-partition-properties")
    logger.addHandler(logging.StreamHandler(log))
    namespace = {"os": os, "zipfile": zipfile, "errno": errno, "logger": logger}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),
                 "<verified-partition-property-source>", "exec"), namespace)
    return namespace, log


def _exercise(source):
    namespace, log = _namespace(source)
    mapping = namespace["PartitionMapFromTargetFiles"]
    reader = namespace["PartitionBuildProps"]._ReadPartitionPropFile
    results = []

    def check(name, function, *, error=None):
        try:
            value = function()
        except Exception as exc:
            _require(error is not None and isinstance(exc, error),
                     name + " raised unexpected " + type(exc).__name__ + ": " + str(exc))
        else:
            _require(error is None and value is True, name + " did not meet its expected result")
        results.append({"name": name, "passed": True})

    with tempfile.TemporaryDirectory(prefix="partition-props-") as temporary:
        root = Path(temporary)
        tree = root / "target-files"
        tree.mkdir()
        files = {
            "SYSTEM/etc/build.prop": b"ro.test=preferred\n",
            "SYSTEM/build.prop": b"ro.test=legacy\n",
            "VENDOR/build.prop": b"ro.test=vendor\n",
            "SYSTEM/vendor/build.prop": b"ro.test=lower-priority\n",
            "ODM/etc/build.prop": b"import /odm/etc/${ro.boot.hardware.sku}.prop\n",
            "VENDOR/odm_dlkm/etc/build.prop": b"ro.test=nested-odm-dlkm\n",
            "VENDOR_EXTRA/etc/build.prop": b"ro.test=wrong-prefix\n",
        }
        for path, data in files.items():
            output = tree / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        archive_path = root / "target-files.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            for path, data in files.items():
                archive.writestr(path, data)
        with zipfile.ZipFile(archive_path, "r") as archive:
            for mode, input_file in (("directory", str(tree)), ("zip-path", str(archive_path)),
                                     ("open-zip", archive)):
                check(mode + "-property-file-priority", lambda: reader(input_file, "system") == "ro.test=preferred\n")
                check(mode + "-partition-priority", lambda: reader(input_file, "vendor") == "ro.test=vendor\n")
                check(mode + "-nested-partition", lambda: mapping(input_file)["odm_dlkm"] == "VENDOR/odm_dlkm"
                      and reader(input_file, "odm_dlkm") == "ro.test=nested-odm-dlkm\n")
                check(mode + "-missing-partition", lambda: "product" not in mapping(input_file)
                      and reader(input_file, "product") == "")
                check(mode + "-original-import-bytes", lambda: reader(input_file, "odm") == files["ODM/etc/build.prop"].decode())
            check("caller-zip-remains-open", lambda: archive.fp is not None
                  and archive.read("VENDOR/build.prop") == files["VENDOR/build.prop"])
        closed_archive = archive
        check("missing-partition-was-reported", lambda: "Failed to find directory for partition product" in log.getvalue())

        isolated = root / "isolated"
        isolated.mkdir()
        (isolated / "VENDOR").write_bytes(b"not a directory")
        check("regular-file-is-not-partition", lambda: "vendor" not in mapping(str(isolated)))
        empty_path = root / "empty.zip"
        with zipfile.ZipFile(empty_path, "w") as archive:
            archive.writestr("VENDOR/", b"")
            archive.writestr("SYSTEM/vendor/build.prop", b"must not replace empty primary\n")
            archive.writestr("PRODUCT_EXTRA/etc/build.prop", b"wrong-prefix\n")
        check("explicit-empty-directory-priority", lambda: mapping(str(empty_path))["vendor"] == "VENDOR"
              and reader(str(empty_path), "vendor") == "")
        check("zip-prefix-is-not-partition", lambda: "product" not in mapping(str(empty_path)))

        (tree / "SYSTEM/etc/build.prop").write_bytes(b"")
        check("empty-preferred-property-keeps-priority", lambda: reader(str(tree), "system") == "")
        (tree / "SYSTEM/etc/build.prop").write_bytes(b"\xff")
        check("invalid-utf8-propagates", lambda: reader(str(tree), "system"), error=UnicodeDecodeError)
        check("invalid-input-rejected", lambda: mapping(str(root / "absent.zip")), error=ValueError)
        check("closed-zip-error-propagates", lambda: reader(closed_archive, "system"), error=ValueError)
    return results


def verify(source_tree, *, before_source_tree=None, run_probe=False):
    source, result = _verified_source(source_tree, before_source_tree)
    if run_probe:
        result["cases"] = _exercise(source)
        result["status"] = "verified-source-and-python-probe"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tree", type=Path, required=True)
    parser.add_argument("--before-source-tree", type=Path)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(args.source_tree, before_source_tree=args.before_source_tree,
                        run_probe=args.probe)
    except (OSError, ValueError, KernelInputsError) as exc:
        print("partition-build-props: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
