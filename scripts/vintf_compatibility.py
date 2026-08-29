#!/usr/bin/env python3
"""Audit the actual generated Kati VINTF graph without running a build.

The native check-vintf-all alias may omit the full compatibility check for a
product that uses opaque vendor/ODM images. An absent optional product manifest
module is also different from a missing required artifact. This tool reports
both facts and inventories the graph's actual framework XML and APEX inputs.
It never infers compatibility from a target name or from a successful audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys


MAX_GRAPH_BYTES = 4 * 1024**3
MAX_LINE_BYTES = 32 * 1024**2
MAX_METADATA_BYTES = 16 * 1024**2
MAX_APEX_BYTES = 1024**3
MODULES = (
    "system_manifest.xml", "system_ext_manifest.xml", "product_manifest.xml",
    "system_compatibility_matrix.xml", "product_compatibility_matrix.xml",
    "checkvintf", "apexd_host",
)
CHECK_OUTPUTS = (
    "check_vintf_system.log", "check_vintf_vendor.log",
    "check_vintf_compatible.log", "vintffm.log", "apex/apex-info-list.xml",
    "kernel_version.txt", "kernel_configs.txt",
)
PARTITIONS = {"system", "system_ext", "product", "vendor", "odm"}


class VintfAuditError(ValueError):
    """The bounded graph audit could not establish an unambiguous input set."""


def require(condition, message):
    if not condition:
        raise VintfAuditError(message)


def relative_path(value):
    require(isinstance(value, str) and value and "\\" not in value
            and all(ord(c) >= 32 for c in value), "invalid relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and all(p not in {".", ".."} for p in path.parts), "unsafe relative path")
    return value


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _real_parents(path):
    for parent in reversed(path.parents):
        require(stat.S_ISDIR(parent.lstat().st_mode),
                "input ancestors must be real directories, not symlinks")


def _open_regular(path):
    path = Path(os.path.abspath(path))
    _real_parents(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), "input must be a regular file, not a symlink")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, "rb")
    if _signature(before) != _signature(os.fstat(stream.fileno())):
        stream.close()
        raise VintfAuditError("input changed while being opened")
    return path, stream, _signature(before)


def _unchanged(path, stream, signature):
    _real_parents(path)
    require(signature == _signature(os.fstat(stream.fileno()))
            == _signature(path.lstat()), "input changed during audit")


def _tokens(value):
    """Decode only literal Ninja path tokens; reject variable expansion.

    Kati emits literal paths for the selected edges. Silently approximating
    variables or unsupported syntax here would risk dropping dependencies.
    """
    tokens, token = [], []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "$":
            index += 1
            require(index < len(value) and value[index] in "$ :",
                    "selected Ninja edge contains unsupported variable expansion")
            token.append(value[index])
        elif char.isspace():
            if token:
                tokens.append("".join(token))
                token = []
        elif char == ":":
            if token:
                tokens.append("".join(token))
                token = []
            tokens.append(":")
        elif char == "|":
            if token:
                tokens.append("".join(token))
                token = []
            separator = "|"
            if index + 1 < len(value) and value[index + 1] in "|@":
                index += 1
                separator += value[index]
            tokens.append(separator)
        else:
            token.append(char)
        index += 1
    if token:
        tokens.append("".join(token))
    return tokens


def _edge(line):
    tokens = _tokens(line[6:])
    require(tokens.count(":") == 1, "selected Ninja build edge is ambiguous")
    split = tokens.index(":")
    require(split > 0 and split + 1 < len(tokens), "selected Ninja build edge is incomplete")
    outputs = [x for x in tokens[:split] if x != "|"]
    dependencies = [x for x in tokens[split + 2:] if x not in {"|", "||", "|@"}]
    require(outputs and len(set(outputs)) == len(outputs), "duplicate Ninja output")
    return {"outputs": outputs, "rule": tokens[split + 1], "inputs": dependencies}


def _output_header(raw):
    """Return the output region, including secondary and implicit outputs."""
    if not raw.startswith(b"build "):
        return b""
    index = 6
    while index < len(raw):
        if raw[index] == ord("$"):
            index += 2
        elif raw[index] == ord(":"):
            return raw[6:index]
        else:
            index += 1
    return raw[6:]


def inspect_graph(stream, product_out, *, max_bytes=MAX_GRAPH_BYTES,
                  max_line_bytes=MAX_LINE_BYTES):
    """Read one Kati graph and return selected edges and its complete identity."""
    product_out = relative_path(product_out)
    require("/target/product/" in product_out, "expected a generated product output prefix")
    checks = product_out + "/obj/PACKAGING/check_vintf_all_intermediates/"
    selected = {"check-vintf-all", *MODULES, *(checks + x for x in CHECK_OUTPUTS)}
    # Preselect within the complete output region, not just the first output.
    # The token decoder then verifies exact membership; input references do not
    # create targets and duplicate secondary outputs cannot evade the guard.
    needles = tuple(name.encode() for name in sorted(selected))
    edges, digest, size = {}, hashlib.sha256(), 0
    pending = bytearray()
    while line := stream.readline(max_line_bytes + 1):
        size += len(line)
        require(size <= max_bytes, "Ninja graph exceeds the size bound")
        require(len(line) <= max_line_bytes, "Ninja physical line exceeds the size bound")
        digest.update(line)
        pending.extend(line.lstrip(b" \t") if pending else line)
        require(len(pending) <= max_line_bytes, "Ninja logical line exceeds the size bound")
        # An odd run of dollars before newline escapes that newline; $$ is a
        # literal dollar. Strip indentation on the continuation as Ninja does.
        offset = len(pending) - (2 if pending.endswith(b"\n") else 1)
        dollars = 0
        while offset >= 0 and pending[offset] == ord("$"):
            dollars += 1
            offset -= 1
        if pending.endswith(b"\n") and dollars % 2:
            del pending[-2:]
            continue
        raw = bytes(pending)
        pending.clear()
        header = _output_header(raw)
        if not any(name in header for name in needles):
            continue
        decoded = raw.decode("utf-8")
        edge = _edge(decoded)
        for output in set(edge["outputs"]) & selected:
            require(output not in edges, "duplicate selected Ninja target")
            edges[output] = edge
    require(not pending, "unterminated Ninja continuation")
    require("check-vintf-all" in edges, "check-vintf-all is absent from this Kati graph")
    require(checks + "apex/apex-info-list.xml" in edges,
            "native APEX activation input edge is absent")
    return edges, {"sha256": digest.hexdigest(), "size_bytes": size}


def summarize(edges, product_out):
    product_out = relative_path(product_out)
    checks = product_out + "/obj/PACKAGING/check_vintf_all_intermediates/"
    alias = edges["check-vintf-all"]
    full = checks + "check_vintf_compatible.log"
    metadata, apex = set(), set()
    for suffix in ("check_vintf_system.log", "check_vintf_vendor.log",
                   "check_vintf_compatible.log", "vintffm.log"):
        for value in edges.get(checks + suffix, {}).get("inputs", []):
            if value.startswith(product_out + "/"):
                tail = relative_path(value[len(product_out) + 1:])
                parts = PurePosixPath(tail).parts
                if len(parts) >= 4 and parts[0] in PARTITIONS and parts[1:3] == ("etc", "vintf"):
                    metadata.add(value)
    apex_edge = edges[checks + "apex/apex-info-list.xml"]
    for value in apex_edge["inputs"]:
        if value.startswith(product_out + "/"):
            tail = relative_path(value[len(product_out) + 1:])
            parts = PurePosixPath(tail).parts
            if len(parts) >= 3 and parts[0] in PARTITIONS and parts[1] == "apex":
                apex.add(value)
    check_targets = {name: checks + name in edges for name in CHECK_OUTPUTS}
    issues = []
    if full not in edges or full not in alias["inputs"]:
        issues.append("native-all-target-does-not-include-full-compatibility")
    if not apex:
        issues.append("native-APEX-input-set-is-empty")
    if not metadata:
        issues.append("native-VINTF-input-set-is-empty")
    for suffix in ("kernel_version.txt", "kernel_configs.txt"):
        if checks + suffix not in edges:
            issues.append("native-kernel-input-target-missing:" + suffix)
    return {
        "schema_version": 1,
        "scope": "generated-Kati-graph-and-selected-inputs-only",
        "product_out": product_out,
        "modules": {name: name in edges for name in MODULES},
        "native_check_targets": check_targets,
        "native_all_target_dependencies": alias["inputs"],
        "native_full_check_defined": full in edges,
        "native_full_check_in_all_target": full in edges and full in alias["inputs"],
        "selected_partition_vintf_inputs": sorted(metadata),
        "selected_apex_package_inputs": sorted(apex),
        "selected_input_scope": "Only inputs of the recorded native checks; absent checks may omit partitions.",
        "issues": issues,
        "full_compatibility_executed": False,
        "compatibility_verified": False,
        "image_adoption_verified": False,
        "device_operations": [],
    }


def inspect_artifact(path, *, max_bytes, with_signature=False):
    """A missing build input is evidence, not a pass. Refuse links and races."""
    path = Path(os.path.abspath(path))
    # Missing parents mean the input was not built. Existing non-real parents
    # are errors, including a symlink to a missing directory.
    for parent in reversed(path.parents):
        try:
            mode = parent.lstat().st_mode
        except FileNotFoundError:
            return ({"state": "missing"}, None) if with_signature else {"state": "missing"}
        require(stat.S_ISDIR(mode), "artifact ancestor is not a real directory")
    try:
        path.lstat()
    except FileNotFoundError:
        return ({"state": "missing"}, None) if with_signature else {"state": "missing"}
    path, stream, signature = _open_regular(path)
    with stream:
        require(signature[3] <= max_bytes, "artifact exceeds its size bound")
        digest, size = hashlib.sha256(), 0
        while data := stream.read(1024 * 1024):
            digest.update(data)
            size += len(data)
            require(size <= max_bytes, "artifact exceeds its size bound")
        _unchanged(path, stream, signature)
    result = {"state": "present", "sha256": digest.hexdigest(), "size_bytes": size}
    return (result, signature) if with_signature else result


def audit(graph_path, product_out, *, output_root=None):
    product_out = relative_path(product_out)
    path, stream, signature = _open_regular(graph_path)
    with stream:
        edges, identity = inspect_graph(stream, product_out)
        result = summarize(edges, product_out)
        _unchanged(path, stream, signature)
    result["graph"] = {"path": str(path), **identity}
    result["selected_edges"] = edges
    if output_root is not None:
        root = Path(os.path.abspath(output_root))
        _real_parents(root)
        require(stat.S_ISDIR(root.lstat().st_mode), "output root must be a real directory")
        graph_output_prefix, suffix = product_out.split("/target/product/", 1)
        require(graph_output_prefix and suffix and "/" not in suffix,
                "unsupported product output prefix")
        artifacts, signatures = {}, {}
        apex = set(result["selected_apex_package_inputs"])
        for value in sorted(apex | set(result["selected_partition_vintf_inputs"])):
            relative = relative_path(value[len(graph_output_prefix) + 1:])
            target = root / relative
            artifacts[value], signatures[value] = inspect_artifact(
                target, max_bytes=MAX_APEX_BYTES if value in apex else MAX_METADATA_BYTES,
                with_signature=True)
        result["artifacts"] = artifacts
        result["missing_artifact_count"] = sum(row["state"] == "missing" for row in artifacts.values())
        result["output_root"] = str(root)
        # A producer changing the graph while artifact files are inspected must
        # not yield a receipt spanning two different product configurations.
        _real_parents(path)
        require(signature == _signature(path.lstat()), "Ninja graph changed during artifact audit")
        for value, expected in signatures.items():
            target = root / relative_path(value[len(graph_output_prefix) + 1:])
            if expected is None:
                # Check ancestors even if the leaf is still absent: a replaced
                # output directory must not turn captured absence into a lie.
                for parent in reversed(target.parents):
                    try:
                        mode = parent.lstat().st_mode
                    except FileNotFoundError:
                        break
                    require(stat.S_ISDIR(mode), "artifact ancestor changed after capture")
                require(not os.path.lexists(target), "missing artifact appeared after capture")
                continue
            _real_parents(target)
            require(expected == _signature(target.lstat()), "artifact changed after its capture")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-ninja", type=Path, required=True,
                        help="existing generated build-PRODUCT.ninja, not the combined or Soong graph")
    parser.add_argument("--product-out", required=True,
                        help="literal relative product-output prefix used by that graph")
    parser.add_argument("--output-root", type=Path,
                        help="optional real physical OUT directory for guarded artifact hashing")
    args = parser.parse_args(argv)
    try:
        result = audit(args.build_ninja, args.product_out, output_root=args.output_root)
    except (OSError, UnicodeError, VintfAuditError) as exc:
        print(f"VINTF audit: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    # Zero means this inventory ran, never that VINTF compatibility passed.
    return 0


if __name__ == "__main__":
    sys.exit(main())
