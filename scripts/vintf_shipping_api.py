#!/usr/bin/env python3
"""Verify and probe the separate, pinned VINTF shipping-API argument patch.

Only hash-bound Python function/class bodies are executed. No native checker,
APEX activation, image construction, source mutation or device access occurs.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import logging
from pathlib import Path
import re
import sys
import zipfile

if __package__:
    from .kernel_inputs import KernelInputsError, _json, _read
    from .partition_build_props import _apply_patch
else:
    from kernel_inputs import KernelInputsError, _json, _read
    from partition_build_props import _apply_patch


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "patches/evolution/vintf-shipping-api.json"
PATCH = "patches/evolution/0011-vintf-shipping-api-from-odm.patch"
SOURCE = "build/make/tools/releasetools/check_target_files_vintf.py"
COMMON = "build/make/tools/releasetools/common.py"
FUNCTION = "GetArgsForShippingApiLevel"
PROPERTY = "ro.product.first_api_level"
PROJECT = {"path": "build/make", "commit": "a438ca40c6ed779042f806142b1165ba1360a7b2",
           "repository": "https://github.com/Evolution-X/build", "branch": "bka"}
MAX_BYTES = 1024 * 1024
SCOPE = {
    "python_argument_forwarding_verified": False, "native_compatibility_verified": False,
    "target_files_verified": False, "ota_verified": False, "source_modified": False,
    "readiness_flags_changed": False, "phone_operations": [],
}
SEMANTICS = {
    "changed_function": FUNCTION, "property": PROPERTY, "read_partitions": ["vendor", "odm"],
    "preferred_partition_when_both_equal": "vendor", "fallback_when_vendor_property_missing": "odm",
    "missing_value_representation": "None", "empty_present_value_rejected": True,
    "both_missing_rejected": True, "both_nonempty_values_validated": True,
    "conflicting_values_rejected": True, "numeric_form": "canonical positive ASCII decimal uint64",
    "maximum": "18446744073709551615", "maximum_digits": 20,
    "supported_android_api_range_inferred": False, "property_bytes_modified": False,
    "other_vintf_functions_changed": False, "source_composition_automatically_extended": False,
}


class ShippingApiError(ValueError):
    """Source, behavior or input evidence differs from the reviewed boundary."""


def require(condition, message):
    if not condition:
        raise ShippingApiError(message)


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def expected(row):
    require(type(row) is dict and type(row.get("sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
            and type(row.get("size_bytes")) is int and 0 < row["size_bytes"] <= MAX_BYTES,
            "invalid source identity")
    return {key: row[key] for key in ("sha256", "size_bytes")}


def read_bound(path, row):
    raw = _read(path, expected(row)["sha256"], limit=MAX_BYTES)
    require(identity(raw) == expected(row), "input length differs")
    return raw


def contract():
    raw = _read(ROOT / CONTRACT, limit=MAX_BYTES)
    record = _json(raw)
    require(type(record.get("schema_version")) is int and record["schema_version"] == 1
            and record.get("contract_id") == "nezha-vintf-shipping-api-v1"
            and record.get("project") == PROJECT and record.get("scope") == SCOPE
            and record.get("semantics") == SEMANTICS, "shipping API contract or scope differs")
    require(record.get("patch", {}).get("path") == PATCH, "unexpected shipping API patch")
    patch = read_bound(ROOT / PATCH, record["patch"])
    require(re.findall(rb"^--- (.+)$", patch, re.M) == [b"a/tools/releasetools/check_target_files_vintf.py"]
            and re.findall(rb"^\+\+\+ (.+)$", patch, re.M) == [b"b/tools/releasetools/check_target_files_vintf.py"],
            "shipping API patch changes an unexpected file")
    rows = record.get("source_files")
    require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict
            and rows[0].get("path") == SOURCE and expected(rows[0].get("before")) != expected(rows[0].get("after")),
            "one exact VINTF wrapper transition is required")
    semantics = record.get("semantic_files")
    require(type(semantics) is list and len(semantics) == 1 and type(semantics[0]) is dict
            and semantics[0].get("path") == COMMON, "exact common property reader is required")
    expected(semantics[0])
    properties = record.get("factory_property_inputs")
    require(type(properties) is dict and set(properties) == {"vendor", "odm"}, "exact factory property pair is required")
    for partition in properties:
        row = properties[partition]
        require(row.get("runtime_path") == ("/vendor/build.prop" if partition == "vendor" else "/odm/etc/build.prop"),
                "factory property input has an unexpected path")
        expected(row)
        expected(row.get("capture_receipt"))
    return record, identity(raw), patch


def _function(raw, name=FUNCTION):
    tree = ast.parse(raw)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(nodes) == 1, "source function is missing or duplicated")
    return nodes[0]


def _outside_function(raw):
    node = _function(raw)
    lines = raw.splitlines(keepends=True)
    return b"".join(lines[:node.lineno - 1] + [b"<verified shipping API function>\n"] + lines[node.end_lineno:])


def _source(source_tree, before_source_tree=None):
    record, record_identity, patch = contract()
    source_tree = Path(source_tree)
    wrapper = read_bound(source_tree / SOURCE, record["source_files"][0]["after"])
    common = read_bound(source_tree / COMMON, record["semantic_files"][0])
    if before_source_tree is not None:
        before = read_bound(Path(before_source_tree) / SOURCE, record["source_files"][0]["before"])
        require(_apply_patch(before, patch) == wrapper, "patch replay differs from the complete wrapper")
        require(_outside_function(before) == _outside_function(wrapper), "patch changes another function or module content")
    return record, record_identity, wrapper, common


def _callables(wrapper, common):
    """Load only the verified function and actual common property container."""
    common_tree = ast.parse(common)
    classes = [node for node in common_tree.body if isinstance(node, ast.ClassDef)
               and node.name in {"RamdiskFormat", "PartitionBuildProps"}]
    require([node.name for node in classes] == ["RamdiskFormat", "PartitionBuildProps"],
            "property-reader class closure differs")
    logger = logging.getLogger("vintf_shipping_api.probe")
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    def no_import_read(*_args, **_kwargs):
        raise ShippingApiError("unexpected property import file access during argument probe")
    namespace = {"copy": copy, "re": re, "zipfile": zipfile, "logger": logger,
                 "ReadFromInputFile": no_import_read}
    exec(compile(ast.Module(body=classes + [_function(wrapper)], type_ignores=[]),
                 "<hash-bound VINTF property probe>", "exec"), namespace)
    return namespace[FUNCTION], namespace["PartitionBuildProps"]


def check_source(source_tree, *, before_source_tree=None):
    record, record_identity, wrapper, common = _source(source_tree, before_source_tree)
    require(contract()[0:2] == (record, record_identity), "contract changed during source verification")
    require(_source(source_tree, before_source_tree) == (record, record_identity, wrapper, common),
            "source or contract changed during source verification")
    require(contract()[0:2] == (record, record_identity), "contract changed during final source verification")
    return {"schema_version": 1, "operation": "verify-vintf-shipping-api-source",
            "contract": {"path": CONTRACT, **record_identity}, "project": PROJECT,
            "source_files": [{"path": SOURCE, **identity(wrapper)}, {"path": COMMON, **identity(common)}],
            "patch_replayed": before_source_tree is not None,
            "only_named_function_changed": before_source_tree is not None,
            "whole_source_tree_verified": False, "scope": dict(SCOPE)}


def probe(source_tree, *, before_source_tree=None, vendor_build_prop=None, odm_build_prop=None):
    record, record_identity, wrapper, common = _source(source_tree, before_source_tree)
    function, props = _callables(wrapper, common)
    cases = []
    def check(name, vendor, odm, result, *, omit=None):
        info = {partition + ".build.prop": props.FromDictionary(partition, {} if value is None else {PROPERTY: value})
                for partition, value in (("vendor", vendor), ("odm", odm)) if partition != omit}
        try:
            actual = function(info)
        except ValueError:
            require(result is None, f"valid shipping API fixture rejected: {name}")
            cases.append({"case": name, "passed": True, "intended_rejection": True})
        else:
            require(result is not None and actual == ["--property", PROPERTY + "=" + result],
                    f"shipping API fixture result differs: {name}")
            cases.append({"case": name, "passed": True, "arguments": actual})
    check("vendor-only", "36", None, "36")
    check("odm-only", None, "36", "36")
    check("both-equal", "36", "36", "36")
    check("both-missing", None, None, None)
    check("conflicting", "36", "35", None)
    check("missing-vendor-container", None, "36", "36", omit="vendor")
    check("missing-odm-container", "36", None, "36", omit="odm")
    for value in ("1", "18446744073709551615"):
        check("vendor-boundary-" + value, value, None, value)
        check("odm-boundary-" + value, None, value, value)
    invalid = ("", "0", "00", "036", "+36", "-36", "0x24", " 36", "36 ", "36\n", "36\0",
               "36.0", "36k", "٣٦", "３６", "18446744073709551616", "1" * 21, "9" * 10_000,
               36, True, False, 36.0, [], {})
    for index, value in enumerate(invalid):
        check(f"invalid-vendor-{index:02}", value, "36", None)
        check(f"invalid-odm-{index:02}", "36", value, None)
    actual = None
    require((vendor_build_prop is None) == (odm_build_prop is None), "both original property files are required")
    originals = {}
    if vendor_build_prop is not None:
        info, bindings = {}, []
        for partition, path in (("vendor", vendor_build_prop), ("odm", odm_build_prop)):
            raw = read_bound(path, record["factory_property_inputs"][partition])
            originals[partition] = (path, raw)
            value = props("unknown", partition)
            value._LoadBuildProp(raw.decode("utf-8"))
            info[partition + ".build.prop"] = value
            bindings.append({"partition": partition, **identity(raw)})
        require(info["vendor.build.prop"].GetProp(PROPERTY) is None
                and info["odm.build.prop"].GetProp(PROPERTY) == "36", "original factory shipping API evidence differs")
        arguments = function(info)
        require(arguments == ["--property", PROPERTY + "=36"], "factory API argument was not forwarded exactly")
        actual = {"inputs": bindings, "value_source": "odm", "arguments": arguments,
                  "property_bytes_modified": False, "runtime_import_selectors_inferred": False}
    require(_source(source_tree, before_source_tree) == (record, record_identity, wrapper, common),
            "source or contract changed during probe")
    require(contract()[0:2] == (record, record_identity), "contract changed during probe")
    for partition, (path, raw) in originals.items():
        require(read_bound(path, record["factory_property_inputs"][partition]) == raw, "factory property changed during probe")
    return {"schema_version": 1, "operation": "probe-vintf-shipping-api-python",
            "contract": {"path": CONTRACT, **record_identity},
            "source_files": [{"path": SOURCE, **identity(wrapper)}, {"path": COMMON, **identity(common)}],
            "cases": cases, "passed": len(cases), "failed": 0, "skipped": 0,
            "factory_properties": actual, "scope": {**SCOPE, "python_argument_forwarding_verified": True}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tree", type=Path, required=True)
    parser.add_argument("--before-source-tree", type=Path)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--vendor-build-prop", type=Path)
    parser.add_argument("--odm-build-prop", type=Path)
    args = parser.parse_args(argv)
    try:
        require(args.probe or (args.vendor_build_prop is None and args.odm_build_prop is None),
                "factory property inputs require --probe")
        options = {"before_source_tree": args.before_source_tree}
        if args.probe:
            result = probe(args.source_tree, vendor_build_prop=args.vendor_build_prop,
                           odm_build_prop=args.odm_build_prop, **options)
        else:
            result = check_source(args.source_tree, **options)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (ShippingApiError, KernelInputsError, OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        print(f"VINTF shipping API: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
