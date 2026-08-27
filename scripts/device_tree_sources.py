#!/usr/bin/env python3
"""Derive private Nezha DTS sources and verify complete FDT round-trip graphs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time

if __package__:
    from .artifact_files import publish_new_directory
    from .firmware import IntakeError, _directory, _open_regular, _signature
    from .kernel_inputs import KernelInputsError, _digest, _json, _read, _real_parents, _relative
else:
    from artifact_files import publish_new_directory
    from firmware import IntakeError, _directory, _open_regular, _signature
    from kernel_inputs import KernelInputsError, _digest, _json, _read, _real_parents, _relative


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = WORKSPACE_ROOT / "kernel/xiaomi/nezha/dts/recipe.json"
MAX_BLOB_BYTES = 128 * 1024**2
MAX_JSON_BYTES = 16 * 1024**2
MAX_NODES = 100_000
MAX_PROPERTIES = 200_000
MAX_STDERR_BYTES = 8 * 1024**2
DEVICE = {"codename": "nezha", "hardware_region": "CN", "soc": "SM8850"}
REFERENCE_NAMES = {"micode-popsicle-kernel", "micode-popsicle-devicetree"}


class DeviceTreeSourceError(ValueError):
    """A source, tool, graph or output violates the source-bundle contract."""


def _require(condition, message):
    if not condition:
        raise DeviceTreeSourceError(message)


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _cstring(data, start, end, *, limit=1024):
    _require(0 <= start < end <= len(data), "string starts outside its FDT section")
    stop = data.find(b"\0", start, min(end, start + limit + 1))
    _require(stop >= start, "unterminated or overlong FDT string")
    try:
        value = data[start:stop].decode("ascii")
    except UnicodeError as exc:
        raise DeviceTreeSourceError("FDT names must be ASCII") from exc
    _require(all(32 <= ord(char) < 127 for char in value), "control character in FDT name")
    return value, stop + 1


def parse_fdt(data):
    """Parse all nodes and exact property bytes without executing or applying a tree."""
    _require(isinstance(data, bytes) and 40 <= len(data) <= MAX_BLOB_BYTES, "invalid FDT size")
    magic, total, off_struct, off_strings, off_reserve, version, compatible, boot_cpu, strings_size, struct_size = struct.unpack_from(">10I", data)
    _require(magic == 0xD00DFEED and total == len(data) and version == 17
             and compatible <= 17, "unsupported or inconsistent FDT header")
    _require(40 <= off_struct <= total - struct_size and off_struct % 4 == 0
             and 40 <= off_strings <= total - strings_size, "FDT section out of bounds")
    _require(off_struct + struct_size <= off_strings or off_strings + strings_size <= off_struct,
             "FDT sections overlap")
    _require(40 <= off_reserve <= total - 16 and off_reserve % 8 == 0, "invalid FDT reservation offset")
    reservations = []
    pos = off_reserve
    while True:
        _require(pos + 16 <= total and len(reservations) < 4096, "unterminated FDT reservation map")
        address, size = struct.unpack_from(">QQ", data, pos)
        pos += 16
        if address == size == 0:
            break
        _require(address + size <= 2**64, "FDT reservation exceeds uint64")
        reservations.append([address, size])
    _require(pos <= off_struct or off_reserve >= off_struct + struct_size,
             "reservation map overlaps FDT structure")
    _require(pos <= off_strings or off_reserve >= off_strings + strings_size,
             "reservation map overlaps FDT strings")
    graph = {"boot_cpuid_phys": boot_cpu, "reservations": reservations, "nodes": {}}
    nodes, stack = graph["nodes"], []
    root_seen, property_count = False, 0
    pos, end = off_struct, off_struct + struct_size
    while pos + 4 <= end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == 1:
            name, stop = _cstring(data, pos, end, limit=255)
            _require("/" not in name and name not in (".", ".."), "ambiguous FDT node name")
            if not stack:
                _require(not root_seen and name == "", "FDT must have one unnamed root")
                root_seen, path = True, "/"
            else:
                _require(name, "empty non-root FDT node name")
                parent = stack[-1]
                path = (parent.rstrip("/") + "/" + name)
                nodes[parent]["children"].append(name)
            _require(path not in nodes and len(nodes) < MAX_NODES and len(stack) < 128,
                     "duplicate node or FDT graph limit exceeded")
            nodes[path] = {"properties": {}, "children": []}
            stack.append(path)
            pos = (stop + 3) & ~3
        elif token == 2:
            _require(stack, "unbalanced FDT end-node")
            stack.pop()
        elif token == 3:
            _require(stack and pos + 8 <= end, "invalid FDT property token")
            size, name_offset = struct.unpack_from(">II", data, pos)
            pos += 8
            _require(size <= end - pos and name_offset < strings_size, "FDT property out of bounds")
            name, _ = _cstring(data, off_strings + name_offset, off_strings + strings_size, limit=255)
            _require(name and "/" not in name, "invalid FDT property name")
            props = nodes[stack[-1]]["properties"]
            _require(name not in props and property_count < MAX_PROPERTIES, "duplicate property or property limit exceeded")
            props[name] = data[pos:pos + size].hex()
            property_count += 1
            pos = (pos + size + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            _require(root_seen and not stack and not any(data[pos:end]), "invalid FDT end or trailing structure data")
            return graph
        else:
            raise DeviceTreeSourceError("unsupported FDT structure token")
        _require(pos <= end, "FDT token padding exceeds structure")
    raise DeviceTreeSourceError("FDT end token missing")


def split_dtbs(data):
    _require(isinstance(data, bytes) and 40 <= len(data) <= MAX_BLOB_BYTES, "invalid DTB image size")
    result, pos = [], 0
    while pos < len(data):
        _require(pos + 40 <= len(data) and len(result) < 256, "truncated or excessive concatenated DTBs")
        magic, size = struct.unpack_from(">II", data, pos)
        _require(magic == 0xD00DFEED and 40 <= size <= len(data) - pos, "invalid concatenated DTB boundary")
        tree = data[pos:pos + size]
        parse_fdt(tree)
        result.append(tree)
        pos += size
    return result


def split_dtbo(data):
    _require(isinstance(data, bytes) and 32 <= len(data) <= MAX_BLOB_BYTES, "invalid DTBO image size")
    magic, total, header, entry_size, count, offset, page, version = struct.unpack_from(">8I", data)
    _require(magic == 0xD7B7AB1E and 32 <= header <= offset and entry_size == 32
             and 1 <= count <= 256 and page == 4096 and version == 0
             and offset + count * entry_size <= total <= len(data), "unsupported or invalid DTBO table")
    metadata = {"total_size": total, "header_size": header, "entry_size": entry_size,
                "page_size": page, "version": version, "entries": []}
    trees, intervals = [], []
    for index in range(count):
        size, start, ident, revision, *custom = struct.unpack_from(">8I", data, offset + index * entry_size)
        _require(offset + count * entry_size <= start <= total - size, "DTBO entry outside table data")
        _require(all(start + size <= left or right <= start for left, right in intervals),
                 "overlapping DTBO entries")
        intervals.append((start, start + size))
        tree = data[start:start + size]
        parse_fdt(tree)
        trees.append(tree)
        metadata["entries"].append({"index": index, "offset": start, "size": size, "id": ident,
                                    "revision": revision, "custom": custom})
    return metadata, trees


def _run_dtc(tool_path, arguments, input_path, output_path, stderr_path, *, timeout=30,
             max_output_bytes=MAX_BLOB_BYTES):
    """Execute only the pinned host tool, with bounded stdout/stderr and an input FD."""
    source = _open_regular(input_path) if input_path is not None else None
    process = None
    try:
        signature = _signature(os.fstat(source.fileno())) if source else None
        descriptors = (source.fileno(),) if source else ()
        argv = [str(tool_path), *arguments]
        if source:
            argv.append(f"/dev/fd/{source.fileno()}")
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, pass_fds=descriptors,
                                   env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
        sizes = {"stdout": 0, "stderr": 0}
        hashes = {"stdout": hashlib.sha256(), "stderr": hashlib.sha256()}
        deadline = time.monotonic() + timeout
        with output_path.open("xb") as output, stderr_path.open("xb") as errors:
            outputs = {"stdout": output, "stderr": errors}
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, "stdout")
                selector.register(process.stderr, selectors.EVENT_READ, "stderr")
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    _require(remaining > 0, "dtc command timed out")
                    for key, _ in selector.select(min(remaining, 0.25)):
                        chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        name = key.data
                        sizes[name] += len(chunk)
                        limit = max_output_bytes if name == "stdout" else MAX_STDERR_BYTES
                        _require(sizes[name] <= limit, "dtc output exceeds capture limit")
                        outputs[name].write(chunk)
                        hashes[name].update(chunk)
            exit_code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if source:
            _require(signature == _signature(os.fstat(source.fileno()))
                     and signature == _signature(Path(input_path).lstat()), "dtc input changed during execution")
        return {"argv": argv, "exit_code": exit_code,
                **{name + "_sha256": value.hexdigest() for name, value in hashes.items()},
                **{name + "_size_bytes": value for name, value in sizes.items()}}
    except subprocess.TimeoutExpired as exc:
        raise DeviceTreeSourceError("dtc command timed out") from exc
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
        if source:
            source.close()


def _recipe(recipe_path, source_config):
    raw = _read(recipe_path, limit=MAX_JSON_BYTES)
    recipe = _json(raw)
    _require(type(recipe.get("schema_version")) is int and recipe["schema_version"] == 1
             and recipe.get("device") == DEVICE, "recipe does not identify China Nezha")
    _digest(recipe["dtc"]["sha256"])
    _require(isinstance(recipe["dtc"]["version"], str) and recipe["dtc"]["version"].startswith("Version: DTC "),
             "missing expected dtc version")
    references = recipe["references"]
    _require(isinstance(references, list) and len(references) == 2
             and {item["name"] for item in references} == REFERENCE_NAMES, "both pinned MiCode references are required")
    config_raw = _read(source_config, limit=MAX_JSON_BYTES)
    config = _json(config_raw)
    pinned = {item["name"]: item for item in config["references"]}
    for ref in references:
        _require(ref["name"] in pinned and all(ref[key] == pinned[ref["name"]][key]
                                             for key in ("url", "branch", "commit")),
                 "MiCode recipe differs from the configured pinned references")
        _require(len(ref["commit"]) == 40 and all(char in "0123456789abcdef" for char in ref["commit"]),
                 "reference must use a full commit ID")
    return recipe, raw, config_raw


def _identity(graph, kind):
    props = graph["nodes"]["/"]["properties"]
    if kind == "dtb":
        compatibles = bytes.fromhex(props.get("compatible", "")).split(b"\0")
        _require(b"qcom,canoe" in compatibles or b"qcom,canoep" in compatibles,
                 "base DTB is not Canoe/CanoeP")
    else:
        model = bytes.fromhex(props.get("model", "")).lower()
        _require(b"nezha" in model and b"sm8850" in model, "overlay does not identify Nezha SM8850")
        _require(props.get("qcom,board-id") == struct.pack(">2I", 8, 0).hex()
                 and props.get("xiaomi,miboard-id") == struct.pack(">2I", 5, 0).hex(),
                 "overlay uses a different Qualcomm or Xiaomi board identity")


def _files(staging):
    records = []
    for path in sorted(staging.rglob("*")):
        _require(not path.is_symlink(), "generated source bundle contains a symlink")
        if path.is_file():
            data = _read(path, limit=MAX_BLOB_BYTES)
            records.append({"path": path.relative_to(staging).as_posix(), "sha256": hashlib.sha256(data).hexdigest(),
                            "size_bytes": len(data)})
    return records


def _write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    _require(_read(path, limit=MAX_BLOB_BYTES) == data, "source artifact readback failed")


def _prepare_sources(kernel_bundle, expected_receipt_sha256, output_dir, *, recipe_path,
                     dtc_path, source_config, workspace_root):
    kernel_bundle = Path(os.path.abspath(kernel_bundle))
    output_dir = Path(os.path.abspath(output_dir))
    workspace_root = Path(os.path.abspath(workspace_root))
    _real_parents(kernel_bundle)
    _real_parents(workspace_root)
    _require(workspace_root / "artifacts" / "source-contracts" in output_dir.parents,
             "DTS output must be below ignored artifacts/source-contracts/")
    _require(kernel_bundle not in output_dir.parents and output_dir not in kernel_bundle.parents
             and output_dir != kernel_bundle, "source output must not overlap kernel input bundle")
    _require(not os.path.lexists(output_dir), "source output already exists; refusing replacement")
    _relative(output_dir.name)
    source_identity = kernel_bundle.stat()
    for ancestor in output_dir.parents:
        try:
            _require(not os.path.samestat(ancestor.stat(), source_identity), "source output aliases input bundle")
        except FileNotFoundError:
            continue
    receipt_raw = _read(kernel_bundle / "receipt.json", expected_receipt_sha256, limit=MAX_JSON_BYTES)
    receipt = _json(receipt_raw)
    _require(type(receipt.get("schema_version")) is int and receipt["schema_version"] == 1
             and receipt.get("device") == DEVICE, "kernel receipt does not identify China Nezha")
    _digest(receipt["provenance"]["parent_package_sha256"])
    _require(receipt["kernel"]["dtbo_board_id"] == [8, 0] and receipt["kernel"]["dtbo_miboard_id"] == [5, 0],
             "kernel receipt contains another Xiaomi board identity")
    recipe, recipe_raw, config_raw = _recipe(recipe_path, source_config)
    tool = Path(dtc_path).resolve(strict=True)
    _require(tool not in kernel_bundle.parents and kernel_bundle not in tool.parents,
             "compiler must not be a payload from the kernel bundle")
    for private in ("artifacts", "sources", "evidence"):
        _require(workspace_root / private not in tool.parents, "compiler must be an independently installed host tool")
    tool_raw = _read(tool, recipe["dtc"]["sha256"])
    _require(os.access(tool, os.X_OK), "pinned dtc is not executable")
    files = {}
    _require(isinstance(receipt["files"], list) and len(receipt["files"]) <= 4096, "invalid kernel file manifest")
    for row in receipt["files"]:
        name = _relative(row["path"])
        _require(name.casefold() not in files, "duplicate kernel receipt path")
        files[name.casefold()] = row
    originals = {}
    for role in ("dtb", "dtbo"):
        name = _relative(receipt["roles"][role])
        record = files.get(name.casefold())
        _require(record is not None and record["path"] == name and record.get("readback_verified") is True,
                 "required kernel input is not a verified receipt member")
        data = _read(kernel_bundle / name, record["sha256"], limit=MAX_BLOB_BYTES)
        _require(len(data) == record["size_bytes"], "kernel input size mismatch")
        originals[role] = data
    dtbs = split_dtbs(originals["dtb"])
    table, overlays = split_dtbo(originals["dtbo"])
    _require(len(dtbs) == receipt["kernel"]["dtb_count"] and len(overlays) == receipt["kernel"]["dtbo_count"],
             "device-tree count differs from kernel receipt")
    for kind, values in (("dtb", dtbs), ("overlay", overlays)):
        for data in values:
            _identity(parse_fdt(data), kind)
    parent = _directory(output_dir.parent)
    _require(shutil.disk_usage(parent).free >= 512 * 1024**2, "insufficient space for source round trips")
    lock = parent / ("." + output_dir.name + ".lock")
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    staging = None
    try:
        staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + "-", dir=parent))
        report = {"schema_version": 1, "operation": "derive-nezha-dts-sources", "status": "running",
                  "created_at_utc": datetime.now(timezone.utc).isoformat(), "device": DEVICE,
                  "kernel_receipt_sha256": expected_receipt_sha256,
                  "kernel": receipt["kernel"], "provenance": receipt["provenance"],
                  "input_validation": receipt["validation"], "recipe_sha256": hashlib.sha256(recipe_raw).hexdigest(),
                  "source_config_sha256": hashlib.sha256(config_raw).hexdigest(),
                  "references": recipe["references"],
                  "tool": {"requested_path": str(dtc_path), "path": str(tool), **recipe["dtc"]},
                  "generator_sha256": hashlib.sha256(_read(Path(__file__))).hexdigest(),
                  "commands": [], "trees": [], "full_graphs_match": False,
                  "phone_accessed": False, "vm_accessed": False, "firmware_executed": False,
                  "full_kernel_build_tested": False, "device_compatibility_verified": False,
                  "sibling_device_sources_substituted": False, "warning_or_error_checks_disabled": False}
        try:
            _write(staging / "originals/vendor.dtb", originals["dtb"])
            _write(staging / "originals/dtbo.img", originals["dtbo"])
            _write(staging / "dtbo-table.json", _canonical(table))
            logs = staging / "logs"
            logs.mkdir()
            command = _run_dtc(tool, ["--version"], None, logs / "dtc-version.stdout.txt",
                               logs / "dtc-version.stderr.txt", max_output_bytes=4096)
            report["commands"].append(command)
            _require(command["exit_code"] == 0 and command["stderr_size_bytes"] == 0
                     and _read(logs / "dtc-version.stdout.txt").decode().strip() == recipe["dtc"]["version"],
                     "pinned dtc version probe failed")
            for kind, values in (("dtb", dtbs), ("overlay", overlays)):
                for index, original in enumerate(values):
                    name = f"dtb-{index:04d}" if kind == "dtb" else f"nezha-overlay-{index:04d}"
                    folder = staging / "trees" / name
                    _write(folder / "original.dtb", original)
                    before = parse_fdt(original)
                    before_raw = _canonical(before)
                    _write(folder / "original.graph.json", before_raw)
                    command = _run_dtc(tool, ["-I", "dtb", "-O", "dts", "-o", "-"], folder / "original.dtb",
                                       folder / "source.dts", folder / "decompile.stderr.txt")
                    report["commands"].append(command)
                    _require(command["exit_code"] == 0, f"dtc decompilation failed for {name}")
                    command = _run_dtc(tool, ["-I", "dts", "-O", "dtb", "-o", "-"], folder / "source.dts",
                                       folder / "rebuilt.dtb", folder / "compile.stderr.txt")
                    report["commands"].append(command)
                    _require(command["exit_code"] == 0, f"dtc recompilation failed for {name}")
                    rebuilt = _read(folder / "rebuilt.dtb", limit=MAX_BLOB_BYTES)
                    after = parse_fdt(rebuilt)
                    after_raw = _canonical(after)
                    _write(folder / "rebuilt.graph.json", after_raw)
                    fixups = {path: value for path, value in before["nodes"].items()
                              if path == "/__symbols__" or path.startswith("/__fixups__")
                              or path.startswith("/__local_fixups__")}
                    row = {"name": name, "kind": kind, "graph_equal": before == after,
                           "source_sha256": hashlib.sha256(original).hexdigest(),
                           "rebuilt_sha256": hashlib.sha256(rebuilt).hexdigest(),
                           "binary_bytes_equal": original == rebuilt,
                           "source_graph_sha256": hashlib.sha256(before_raw).hexdigest(),
                           "rebuilt_graph_sha256": hashlib.sha256(after_raw).hexdigest(),
                           "node_count": len(before["nodes"]),
                           "property_count": sum(len(node["properties"]) for node in before["nodes"].values()),
                           "fixup_node_count": len(fixups),
                           "fixup_graph_sha256": hashlib.sha256(_canonical(fixups)).hexdigest(),
                           "root_properties": before["nodes"]["/"]["properties"]}
                    report["trees"].append(row)
                    _require(row["graph_equal"], f"FDT semantic graph changed during round trip: {name}")
                    _identity(after, kind)
            _require(_read(tool, recipe["dtc"]["sha256"]) == tool_raw, "host dtc changed during source generation")
            _require(_read(kernel_bundle / "receipt.json", expected_receipt_sha256, limit=MAX_JSON_BYTES) == receipt_raw,
                     "kernel receipt changed during source generation")
            for role in originals:
                path = kernel_bundle / receipt["roles"][role]
                _require(_read(path, limit=MAX_BLOB_BYTES) == originals[role], "original device tree input changed")
            _require(_read(recipe_path, limit=MAX_JSON_BYTES) == recipe_raw
                     and _read(source_config, limit=MAX_JSON_BYTES) == config_raw, "source recipe or references changed")
            report["status"], report["full_graphs_match"] = "complete", True
        except Exception as exc:
            report["status"], report["error"] = "failed", str(exc)
            raise
        finally:
            report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
            report["files"] = _files(staging)
            report["file_count"] = len(report["files"])
            data = _canonical(report)
            _write(staging / "receipt.json", data)
            _write(staging / "receipt.sha256", (hashlib.sha256(data).hexdigest() + "  receipt.json\n").encode())
            publish_new_directory(staging, output_dir)
            staging = None
        return report
    finally:
        # Never delete evidence produced by a failing compiler or comparison.
        # A publication failure leaves the private staging path for inspection.
        lock.unlink()


def prepare_sources(kernel_bundle, expected_receipt_sha256, output_dir, *, recipe_path=DEFAULT_RECIPE,
                    dtc_path=Path("/opt/homebrew/bin/dtc"), source_config=WORKSPACE_ROOT / "config/sources.json",
                    workspace_root=WORKSPACE_ROOT):
    try:
        return _prepare_sources(kernel_bundle, expected_receipt_sha256, output_dir,
                                recipe_path=recipe_path, dtc_path=dtc_path,
                                source_config=source_config, workspace_root=workspace_root)
    except DeviceTreeSourceError:
        raise
    except (KernelInputsError, IntakeError, OSError, KeyError, TypeError, UnicodeError, struct.error) as exc:
        raise DeviceTreeSourceError(str(exc)) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-bundle", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--dtc", type=Path, default=Path("/opt/homebrew/bin/dtc"))
    parser.add_argument("--source-config", type=Path, default=WORKSPACE_ROOT / "config/sources.json")
    args = parser.parse_args(argv)
    try:
        result = prepare_sources(args.kernel_bundle, args.expected_receipt_sha256, args.output,
                                 recipe_path=args.recipe, dtc_path=args.dtc, source_config=args.source_config)
    except DeviceTreeSourceError as exc:
        print(f"device-tree sources: {exc}; inspect any retained output/staging evidence", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "status": result["status"],
                      "trees": len(result["trees"]), "full_graphs_match": result["full_graphs_match"],
                      "file_count": result["file_count"], "full_kernel_build_tested": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
