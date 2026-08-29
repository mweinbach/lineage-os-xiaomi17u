#!/usr/bin/env python3
"""Project captured factory metadata into target-files without rebuilding images.

This is a content-only projection, not a filesystem extraction/repack, OEM
authentication, VINTF pass, APK inventory, signing operation or ROM admission.
The reviewed capture receipts and full inventories remain distinct evidence.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "config/nezha-target-files-metadata.json"
SOURCE_CONTRACT = "patches/evolution/target-files-metadata.json"
BUNDLE = "vendor/xiaomi/nezha-target-files-metadata"
RECEIPT = "target-files-metadata.json"
CORE = "build/make/core/Makefile"
COMMON = "build/make/tools/releasetools/common.py"
PATCH = "patches/evolution/0009-prebuilt-target-files-metadata.patch"
PROJECT = {"path": "build/make", "commit": "a438ca40c6ed779042f806142b1165ba1360a7b2",
           "repository": "https://github.com/Evolution-X/build", "branch": "bka"}
SOURCE_CONTRACTS = (
    "patches/evolution/prebuilt-recovery.json",
    "patches/evolution/ab-only-recovery-packaging.json",
    "patches/evolution/direct-avb-custom-images.json",
    "patches/evolution/optional-partition-build-props.json",
    SOURCE_CONTRACT,
)
SOURCE_PATCHES = (
    "patches/evolution/0005-verified-prebuilt-recovery.patch",
    "patches/evolution/0006-ab-only-recovery-packaging.patch",
    "patches/evolution/0007-direct-avb-custom-images.patch",
    "patches/evolution/0008-optional-partition-build-props.patch", PATCH,
)
SOURCE_IDS = (None, "nezha-ab-only-recovery-packaging-v1", "nezha-direct-avb-custom-images-v1",
              "nezha-optional-partition-build-props-v1", "nezha-prebuilt-target-files-metadata-v1")
ADD_IMG = "build/make/tools/releasetools/add_img_to_target_files.py"
SOURCE_SEMANTICS = (
    (COMMON,),
    (CORE, COMMON, "build/make/tools/releasetools/non_ab_ota.py", "build/make/tools/releasetools/ota_from_target_files.py"),
    (COMMON, "build/make/tools/releasetools/build_super_image.py", "build/make/tools/releasetools/validate_target_files.py"),
    (),
    ("build/make/tools/releasetools/check_target_files_vintf.py", "build/make/tools/releasetools/apex_utils.py"),
)
CONTROL_TOOLS = ("scripts/target_files_metadata.py",)
MAX_TEXT = 8 * 1024**2
MAX_PAYLOAD = 64 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_IMAGE = 8 * 1024**3
EXPECTED_IMAGES = {
    "vendor": {"sha256": "c9c2a03b61cd7c96466f09ffebf723382f430fd1389b1b73186270f3e15dfb20", "size_bytes": 959709184},
    "odm": {"sha256": "4a269421a596c1eb1d90c982ef5497591ed1091e424a21bb9e7a83cf1a943ff5", "size_bytes": 4767621120},
}
EXPECTED_COUNTS = {"vendor": {"properties": 2, "apex": 3}, "odm": {"properties": 22, "apex": 0}}
EXPECTED_PACKAGE = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
SCOPE = {
    "metadata_only": True, "original_images_preserved": True,
    "complete_filesystem_projection": False, "apk_inventory_complete": False,
    "filesystem_metadata_reproduced": False, "oem_authentication_verified": False,
    "vintf_verified": False, "target_files_verified": False, "ota_verified": False,
    "complete_rom_admitted": False, "hardware_tested": False, "phone_operations": [],
}


class TargetFilesMetadataError(ValueError):
    """An input, closure, native source or output path differs from admission."""


def require(condition, message):
    if not condition:
        raise TargetFilesMetadataError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def expected(row, maximum=MAX_TEXT):
    require(type(row) is dict and type(row.get("sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
            and type(row.get("size_bytes")) is int and 0 <= row["size_bytes"] <= maximum,
            "invalid bounded input identity")
    return {key: row[key] for key in ("sha256", "size_bytes")}


def relative(value):
    require(type(value) is str and 0 < len(value) <= 4096
            and all(re.fullmatch(r"[A-Za-z0-9_.+@-]+", part) is not None
                    and part not in {".", ".."} for part in value.split("/")),
            "unsafe relative path or make expression")
    return value


def real_directory(path):
    path = Path(os.path.abspath(path))
    for parent in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(parent.lstat().st_mode), "real directory required; symlinks refused")
    return path


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=unique,
                           parse_constant=lambda _: require(False, "invalid JSON constant"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise TargetFilesMetadataError("invalid JSON object") from exc
    require(type(value) is dict, "expected JSON object")
    return value


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _inode(info):
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _open_directory(path):
    path = real_directory(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    if _inode(os.fstat(descriptor)) != _inode(path.lstat()):
        os.close(descriptor)
        raise TargetFilesMetadataError("directory replaced while opening")
    return descriptor


def _publish_at(source_fd, source, destination_fd, destination):
    """Exclusive atomic publication anchored to already opened directories."""
    require("/" not in source and "/" not in destination, "publication requires basenames")
    library = ctypes.CDLL(None, use_errno=True)
    try:
        if sys.platform == "darwin":
            rename, flags = library.renameatx_np, 0x00000004  # RENAME_EXCL
        elif sys.platform == "linux":
            rename, flags = library.renameat2, 1  # RENAME_NOREPLACE
        else:
            raise OSError(errno.ENOTSUP, "exclusive publication requires macOS or Linux")
    except AttributeError as exc:
        raise OSError(errno.ENOSYS, "exclusive rename unavailable") from exc
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(source_fd, os.fsencode(source), destination_fd, os.fsencode(destination), flags):
        error = ctypes.get_errno() or errno.EIO
        raise OSError(error, os.strerror(error), destination)


def publish_new_directory(staging, destination):
    """Publish a prepared bundle without replacing any existing destination."""
    old_fd = _open_directory(Path(staging).parent)
    try:
        new_fd = _open_directory(Path(destination).parent)
        try:
            _publish_at(old_fd, Path(staging).name, new_fd, Path(destination).name)
        finally:
            os.close(new_fd)
    finally:
        os.close(old_fd)


class Reader:
    """Bounded, no-follow readers; streamed image hashes never hold images in RAM."""

    def __init__(self):
        self.bindings = {}

    def read(self, path, row=None, *, maximum=MAX_TEXT, data=True):
        path = Path(os.path.abspath(path))
        parent = real_directory(path.parent)
        parent_id = signature(parent.stat())[:2]
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size <= maximum, "bounded regular single-link input required")
        digest, size, parts = hashlib.sha256(), 0, []
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            require(signature(before) == signature(os.fstat(stream.fileno())), "input replaced before read")
            while block := stream.read(1024**2):
                size += len(block)
                require(size <= maximum, "input grew beyond bound")
                digest.update(block)
                if data:
                    parts.append(block)
            require(signature(before) == signature(os.fstat(stream.fileno())) == signature(path.lstat())
                    and size == before.st_size, "input changed during read")
        require(parent_id == signature(real_directory(path.parent).stat())[:2], "input directory changed")
        measured = {"sha256": digest.hexdigest(), "size_bytes": size}
        require(row is None or measured == expected(row, maximum), "input identity differs")
        binding = (measured, signature(before), maximum, data)
        require(path not in self.bindings or self.bindings[path][:2] == binding[:2], "input changed between reads")
        self.bindings.setdefault(path, binding)
        return b"".join(parts) if data else measured

    def recheck(self):
        for path, (row, _, maximum, data) in list(self.bindings.items()):
            self.read(path, row, maximum=maximum, data=data)


def _files(root):
    root = real_directory(root)
    result, seen_directories = set(), set()
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            directory = Path(current) / name
            require(stat.S_ISDIR(directory.lstat().st_mode), "bundle directory is a symlink")
            seen_directories.add(relative(directory.relative_to(root).as_posix()))
        for name in files:
            path = Path(current) / name
            result.add(relative(path.relative_to(root).as_posix()))
        require(len(result) + len(seen_directories) <= 4096, "bundle tree exceeds inventory bound")
    require(all(any(path.startswith(directory + "/") for path in result) for directory in seen_directories),
            "unlisted empty bundle directory")
    return result


def compose_sources(root=ROOT):
    """Explicit 0005–0009 composition; do not change historical contracts."""
    reader, rows, records, refs, patches = Reader(), {}, [], [], []
    for index, path in enumerate(SOURCE_CONTRACTS):
        raw = reader.read(Path(root) / path)
        record = _json(raw)
        require(record.get("schema_version") == 1 and record.get("project") == PROJECT,
                "source composition changed pinned bka project")
        require(record.get("contract_id") == SOURCE_IDS[index], "unexpected source contract identity")
        patch = record.get("patch", {})
        patch_path = relative(patch.get("path"))
        require(patch_path == SOURCE_PATCHES[index], "unreviewed patch path")
        patch_data = reader.read(Path(root) / patch_path, patch)
        changed = record.get("source_files")
        require(type(changed) is list and len(changed) == 1, "one source transition per patch required")
        row = changed[0]
        name = relative(row.get("path"))
        before, after = expected(row.get("before")), expected(row.get("after"))
        require(name.startswith("build/make/") and before != after, "invalid source transition")
        short = name.removeprefix("build/make/")
        require(re.findall(rb"^--- (.+)$", patch_data, re.M) == [f"a/{short}".encode()]
                and re.findall(rb"^\+\+\+ (.+)$", patch_data, re.M) == [f"b/{short}".encode()],
                "patch source scope differs")
        headers = re.findall(rb"^diff --git (.+)$", patch_data, re.M)
        require(headers in ([], [f"a/{short} b/{short}".encode()]), "unexpected git patch scope")
        semantics = record.get("semantic_files", [])
        require(type(semantics) is list and all(type(row) is dict for row in semantics)
                and [row.get("path") for row in semantics] == list(SOURCE_SEMANTICS[index]),
                "missing, duplicate or unreviewed source semantics")
        if index in {1, 2}:
            require(record.get("requires_patch") == SOURCE_PATCHES[0], "missing recovery predecessor")
        if index == 2:
            require(record.get("composed_semantic_files") == [
                {**rows[ADD_IMG], "requires_patch": SOURCE_PATCHES[1]}], "A/B packaging composition differs")
        if name in rows:
            require(expected(rows[name]) == before, "source patch chain has a gap")
        rows[name] = {"path": name, **after}
        for semantic in semantics:
            path_name = relative(semantic.get("path"))
            normalized = {"path": path_name, **expected(semantic)}
            # An earlier core/common semantic row is only the historical preimage.
            if path_name in rows:
                require(rows[path_name] == normalized, "source semantic identity conflicts")
            else:
                rows[path_name] = normalized
        refs.append({"path": path, **identity(raw)})
        records.append(record)
        patches.append({"path": patch_path, **identity(patch_data)})
    require([r["source_files"][0]["path"] for r in records] == [
        CORE, "build/make/tools/releasetools/add_img_to_target_files.py", CORE, COMMON, CORE],
        "unexpected ordered source composition")
    require(records[-1].get("contract_id") == "nezha-prebuilt-target-files-metadata-v1"
            and records[-1].get("required_predecessor_contracts") == refs[:-1],
            "metadata hook predecessor contracts differ")
    require(records[-1].get("scope") == SCOPE, "source contract changes admission scope")
    reader.recheck()
    return {"schema_version": 1, "project": copy.deepcopy(PROJECT), "contracts": refs,
            "ordered_patches": patches, "final_source_files": [rows[p] for p in sorted(rows)],
            "patches_applied_by_this_tool": False, "whole_source_tree_verified": False}


def _controls(root, reader):
    root = real_directory(root)
    profile_raw = reader.read(root / PROFILE)
    profile = _json(profile_raw)
    require(profile.get("schema_version") == 1
            and profile.get("contract_id") == "nezha-factory-target-files-metadata-v1"
            and profile.get("device") == "nezha" and profile.get("branch") == "bka"
            and profile.get("release") == "bp4a" and profile.get("bundle") == BUNDLE
            and profile.get("factory_package_sha256") == EXPECTED_PACKAGE
            and profile.get("scope") == SCOPE, "unexpected metadata profile or scope")
    partitions = profile.get("partitions")
    require(type(partitions) is dict and set(partitions) == {"vendor", "odm"}, "exact vendor/ODM pair required")
    for name, row in partitions.items():
        require(expected(row.get("image"), MAX_IMAGE) == EXPECTED_IMAGES[name], "factory image identity differs")
        require(row.get("counts", {}).get("properties") == EXPECTED_COUNTS[name]["properties"]
                and row["counts"].get("apex") == EXPECTED_COUNTS[name]["apex"], "factory metadata counts differ")
    composition = compose_sources(root)
    paths = [PROFILE, *CONTROL_TOOLS, *SOURCE_CONTRACTS,
             *(row["path"] for row in composition["ordered_patches"])]
    controls = {path: reader.read(root / path) for path in paths}
    return profile, composition, controls


def _kind(path):
    if path.endswith(".prop"):
        return "properties"
    if path.startswith("/etc/vintf/") or path in {
        "/manifest.xml", "/compatibility_matrix.xml", "/etc/manifest.xml", "/etc/compatibility_matrix.xml"
    }:
        return "vintf"
    if path.startswith("/apex/"):
        require(path.endswith((".apex", ".capex")), "unsupported file in factory APEX directory")
        return "apex"
    return None


def _inventory(raw, partition):
    inventory = _json(raw)
    require(type(inventory.get("schema_version")) is int and inventory["schema_version"] == 1
            and expected(inventory.get("image"), MAX_IMAGE) == EXPECTED_IMAGES[partition],
            "inventory schema or image binding differs")
    entries = inventory.get("entries")
    require(type(entries) is list and 1 <= len(entries) <= 100_000, "missing complete inventory")
    found, selected, inode_types, directory_nids = {}, {}, {}, set()
    for row in entries:
        require(type(row) is dict and set(row) == {"path", "nid", "type"}
                and type(row.get("path")) is str and row["path"].startswith("/"),
                "invalid factory inventory row")
        path = row["path"]
        if path != "/":
            require(len(path) <= 4096 and all(part not in {"", ".", ".."}
                    and len(part.encode("utf-8")) <= 255 and not any(ord(c) < 32 for c in part)
                    for part in path[1:].split("/")), "unsafe image inventory path")
        require(path not in found and type(row.get("nid")) is int and 0 <= row["nid"] < 2**64
                and row.get("type") in {"regular", "directory", "character", "block", "fifo", "socket", "symlink"},
                "duplicate or invalid inventory path")
        require(inode_types.setdefault(row["nid"], row["type"]) == row["type"]
                and not (row["type"] == "directory" and row["nid"] in directory_nids),
                "inconsistent inventory inode type or directory alias")
        found[path] = row
        if row.get("type") == "directory":
            directory_nids.add(row["nid"])
            continue
        kind = _kind(path)
        if kind is not None:
            require(row.get("type") == "regular", "selected factory metadata must be a regular file")
            relative(path[1:])  # Selected output names also become Make dependencies.
            selected[path] = {"partition": partition, "path": path, "nid": row["nid"], "kind": kind}
    require(found.get("/", {}).get("type") == "directory", "factory inventory has no root directory")
    for path in found:
        if path != "/":
            parent = path.rsplit("/", 1)[0] or "/"
            require(found.get(parent, {}).get("type") == "directory", "inventory has missing real parent")
    return selected, len(entries)


def _property_closure(files):
    properties = {"/" + row["partition"] + row["path"]: data for row, data in files.values()
                  if row["kind"] == "properties"}
    imports, api = [], []
    for path, raw in sorted(properties.items()):
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise TargetFilesMetadataError("property input must be UTF-8") from exc
        require("\0" not in text, "property input contains NUL")
        for number, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if line.split()[:1] == ["import"]:
                parts = line.split()
                require(len(parts) in {2, 3} and parts[1].startswith(("/vendor/", "/odm/")),
                        "unsupported property import")
                template = parts[1]
                tokens = re.split(r"(\$\{[A-Za-z0-9_.]+\})", template)
                pattern = "".join(r"[^/]+" if token.startswith("${") else re.escape(token) for token in tokens)
                require("$" not in "".join(t for t in tokens if not t.startswith("${")),
                        "unsupported property expansion")
                matches = sorted(p for p in properties if re.fullmatch(pattern, p))
                require(matches, "property import has no captured target")
                imports.append({"source": path, "line": number, "template": template,
                                "filter": parts[2] if len(parts) == 3 else None, "captured_targets": matches,
                                "runtime_selector_value_inferred": False})
            elif line.startswith("ro.product.first_api_level="):
                value = line.partition("=")[2].strip()
                require(value == "36", "factory shipping API differs from Nezha")
                api.append({"path": path, "line": number, "value": value})
    require(len(api) == 1 and api[0]["path"] == "/odm/etc/build.prop",
            "shipping API must come from the original ODM build properties")
    edges = {path: set() for path in properties}
    for row in imports:
        edges[row["source"]].update(row["captured_targets"])
    visiting, visited = set(), set()
    def visit(path):
        require(path not in visiting, "property import cycle")
        if path in visited:
            return
        visiting.add(path)
        for child in edges[path]:
            visit(child)
        visiting.remove(path)
        visited.add(path)
    for path in edges:
        visit(path)
    return {"imports": imports, "shipping_api_evidence": api,
            "runtime_imports_resolved": False, "property_bytes_modified": False}


def _captured(profile, reader, locate):
    """Bind every selected path to a reviewed capture and complete inventory."""
    files, provenance, selected = {}, {}, {}
    for partition, rule in sorted(profile["partitions"].items()):
        inventory_ref = rule["inventory"]
        raw = reader.read(locate(inventory_ref["path"]), inventory_ref)
        provenance[f"provenance/{partition}-inventory.json"] = raw
        entries, count = _inventory(raw, partition)
        require(count == rule["entry_count"], "factory inventory count differs")
        require({kind: sum(row["kind"] == kind for row in entries.values())
                 for kind in ("properties", "vintf", "apex")} == rule["counts"],
                "selected factory metadata closure differs")
        selected.update({(partition, path): row for path, row in entries.items()})
        inventory_receipt = rule["inventory_receipt"]
        inv_raw = reader.read(locate(inventory_receipt["path"]), inventory_receipt)
        provenance[f"provenance/{partition}-inventory-receipt.json"] = inv_raw
        inv = _json(inv_raw)
        require(inv.get("schema_version") == 1 and inv.get("operation") == "erofs-scan"
                and inv.get("entry_count") == count
                and expected(inv.get("image"), MAX_IMAGE) == EXPECTED_IMAGES[partition]
                and expected(inv.get("inventory")) == expected(inventory_ref)
                and inv.get("image_mounted") is False and inv.get("origin_verified") is False
                and inv.get("symlinks_followed") is False, "inventory receipt binding differs")
        for index, ref in enumerate(rule["captures"]):
            capture_raw = reader.read(locate(ref["path"]), ref)
            provenance[f"provenance/{partition}-capture-{index:02}.json"] = capture_raw
            capture = _json(capture_raw)
            require(capture.get("schema_version") == 1 and capture.get("operation") == "erofs-capture"
                    and expected(capture.get("image"), MAX_IMAGE) == EXPECTED_IMAGES[partition]
                    and capture.get("inventory_sha256") == inventory_ref["sha256"]
                    and capture.get("inventory_receipt_sha256") == inventory_receipt["sha256"]
                    and capture.get("origin_verified") is False
                    and capture.get("image_mounted") is False
                    and capture.get("firmware_executed") is False
                    and capture.get("symlinks_followed") is False
                    and expected(capture.get("tool")) == expected(inv.get("tool")), "capture provenance differs")
            rows = capture.get("files")
            require(type(rows) is list and len(rows) <= 100_000, "invalid capture file list")
            seen = set()
            for captured in rows:
                path = captured.get("path")
                require(type(path) is str and path not in seen, "duplicate capture path")
                seen.add(path)
                key = (partition, path)
                if key not in selected:
                    continue
                row = selected[key]
                require(captured.get("readback_verified") is True and captured.get("type") == "regular"
                        and captured.get("nid") == row["nid"], "capture differs from inventory")
                member = relative(captured.get("output_path"))
                source = (Path(ref["path"]).parent / member).as_posix()
                data = reader.read(locate(source), captured, maximum=MAX_PAYLOAD)
                output = partition.upper() + path
                normalized = {**row, **identity(data), "target_path": output,
                              "capture": {"path": ref["path"], **expected(ref)},
                              "capture_member": member}
                require(output not in files, "metadata path appears in more than one admitted capture")
                files[output] = (normalized, data)
    require(set((row["partition"], row["path"]) for row, _ in files.values()) == set(selected),
            "required metadata file lacks a capture")
    require(sum(len(data) for _, data in files.values()) <= MAX_TOTAL, "projection exceeds size bound")
    return files, provenance, _property_closure(files)


def _check_source(source_tree, composition, reader):
    root = real_directory(source_tree)
    for row in composition["final_source_files"]:
        reader.read(root / row["path"], row)


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def stage(inputs_root, output, *, vendor_image, odm_image, controls_root=None):
    """Prepare a new private bundle; unchanged images stay external and read-only."""
    reader = Reader()
    controls_root = ROOT if controls_root is None else controls_root
    profile, composition, controls = _controls(controls_root, reader)
    inputs = real_directory(inputs_root)
    files, provenance, closure = _captured(profile, reader, lambda path: inputs / relative(path))
    images = {"vendor": vendor_image, "odm": odm_image}
    for partition, path in images.items():
        reader.read(path, EXPECTED_IMAGES[partition], maximum=MAX_IMAGE, data=False)
    payloads = {"tree/" + path: raw for path, (_, raw) in files.items()}
    payloads.update(provenance)
    payloads.update({"controls/" + path: raw for path, raw in controls.items()})
    # Native entrypoint shares the exact public code; controls retain its receipt.
    payloads.update({"tools/" + Path(path).name: controls[path] for path in CONTROL_TOOLS})
    receipt = {"schema_version": 1, "operation": "stage-factory-target-files-metadata",
               "profile": {"path": PROFILE, **identity(controls[PROFILE])},
               "images": copy.deepcopy(EXPECTED_IMAGES), "source_composition": composition,
               "files": [files[path][0] for path in sorted(files)], "property_closure": closure,
               "bundle_files": [{"path": path, **identity(raw)} for path, raw in sorted(payloads.items())],
               "scope": copy.deepcopy(SCOPE)}
    output = Path(os.path.abspath(output))
    real_directory(output.parent)
    require(not output.exists() and not output.is_symlink(), "new bundle destination required")
    temporary = Path(tempfile.mkdtemp(prefix=".nezha-metadata-", dir=output.parent))
    try:
        for path, raw in payloads.items():
            _write(temporary / path, raw)
        _write(temporary / RECEIPT, encoded(receipt))
        reader.recheck()
        publish_new_directory(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return receipt


def verify_bundle(bundle, *, expected_receipt, source_tree=None, vendor_image=None, odm_image=None):
    """Recompute the full projection from its hash-bound copied provenance."""
    require(type(expected_receipt) is str and re.fullmatch(r"[0-9a-f]{64}", expected_receipt),
            "an external expected bundle receipt SHA256 is required")
    bundle, reader = real_directory(bundle), Reader()
    raw = reader.read(bundle / RECEIPT)
    require(identity(raw)["sha256"] == expected_receipt, "bundle receipt differs from selected digest")
    receipt = _json(raw)
    profile, composition, controls = _controls(bundle / "controls", reader)
    require(receipt.get("schema_version") == 1
            and receipt.get("operation") == "stage-factory-target-files-metadata"
            and receipt.get("profile") == {"path": PROFILE, **identity(controls[PROFILE])}
            and receipt.get("images") == EXPECTED_IMAGES and receipt.get("source_composition") == composition
            and receipt.get("scope") == SCOPE, "bundle profile or scope differs")
    bindings = receipt.get("bundle_files")
    require(type(bindings) is list and len(bindings) <= 2048, "invalid bundle file inventory")
    mapping = {}
    for row in bindings:
        path = relative(row.get("path"))
        require(path not in mapping, "duplicate bundle file")
        mapping[path] = reader.read(bundle / path, row, maximum=MAX_PAYLOAD)
    require(_files(bundle) == set(mapping) | {RECEIPT}, "unlisted or missing bundle file")
    source_map = {}
    for partition, rule in profile["partitions"].items():
        source_map[rule["inventory"]["path"]] = bundle / f"provenance/{partition}-inventory.json"
        source_map[rule["inventory_receipt"]["path"]] = bundle / f"provenance/{partition}-inventory-receipt.json"
        for index, ref in enumerate(rule["captures"]):
            source_map[ref["path"]] = bundle / f"provenance/{partition}-capture-{index:02}.json"
            capture = _json(mapping[f"provenance/{partition}-capture-{index:02}.json"])
            for row in capture["files"]:
                if row.get("type") == "regular" and _kind(row["path"]) is not None:
                    original = (Path(ref["path"]).parent / relative(row["output_path"])).as_posix()
                    source_map[original] = bundle / ("tree/" + partition.upper() + row["path"])
    def locate(path):
        require(path in source_map, "unbound captured metadata source")
        return source_map[path]
    files, provenance, closure = _captured(profile, reader, locate)
    payloads = {"tree/" + path: data for path, (_, data) in files.items()}
    payloads.update(provenance)
    payloads.update({"controls/" + path: data for path, data in controls.items()})
    payloads.update({"tools/" + Path(path).name: controls[path] for path in CONTROL_TOOLS})
    require(mapping == payloads and receipt.get("files") == [files[path][0] for path in sorted(files)]
            and receipt.get("property_closure") == closure, "bundle derivation differs")
    if source_tree is not None:
        _check_source(source_tree, composition, reader)
    require((vendor_image is None) == (odm_image is None), "both packaged images are required")
    if vendor_image is not None:
        for partition, path in {"vendor": vendor_image, "odm": odm_image}.items():
            reader.read(path, EXPECTED_IMAGES[partition], maximum=MAX_IMAGE, data=False)
    reader.recheck()
    require(_files(bundle) == set(mapping) | {RECEIPT}, "bundle inventory changed during verification")
    return receipt, files, reader


def install(bundle, target_files, *, expected_receipt, source_tree):
    """Inject only new metadata trees before native AddImages; never touch images."""
    target = real_directory(target_files)
    real_directory(target / "META")
    for name in ("VENDOR", "ODM", "META/nezha_target_files_metadata.json"):
        require(not (target / name).exists() and not (target / name).is_symlink(),
                "target-files metadata collision")
    receipt, files, reader = verify_bundle(
        bundle, expected_receipt=expected_receipt, source_tree=source_tree,
        vendor_image=target / "IMAGES/vendor.img", odm_image=target / "IMAGES/odm.img")
    misc = reader.read(target / "META/misc_info.txt").decode("utf-8")
    fields = {}
    for line in misc.splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            require(key not in fields, "duplicate misc_info field")
            fields[key] = value
    require(fields.get("building_vendor_image") == "" and fields.get("building_odm_image") == ""
            and fields.get("ab_update") == "true" and fields.get("allow_non_ab") != "true"
            and fields.get("vintf_enforce") == "true", "native target-files mode differs")
    for name in ("META/kernel_version.txt", "META/kernel_configs.txt"):
        require(reader.read(target / name), "kernel VINTF metadata is missing or empty")
    report = {"schema_version": 1, "operation": "project-factory-target-files-metadata",
              "bundle_receipt_sha256": expected_receipt, "images": receipt["images"],
              "files": receipt["files"], "property_closure": receipt["property_closure"],
              "source_composition": receipt["source_composition"], "scope": copy.deepcopy(SCOPE)}
    target_fd, meta_fd = _open_directory(target), None
    temporary, temporary_fd, published = None, None, []
    expected_bundle = {row["path"] for row in receipt["bundle_files"]} | {RECEIPT}
    def parents_unchanged():
        require(_inode(real_directory(target).lstat()) == _inode(os.fstat(target_fd)),
                "target-files directory changed")
        require(_inode(real_directory(target / "META").lstat()) == _inode(os.fstat(meta_fd)),
                "target-files META directory changed")
    def check_destination():
        parents_unchanged()
        output_reader = Reader()
        for name in ("VENDOR", "ODM"):
            owner = next(row for row in published if row[1] == name)
            require(_inode((target / name).lstat()) == owner[2], "published metadata directory replaced")
            wanted = {path.removeprefix(name + "/") for path in files if path.startswith(name + "/")}
            require(_files(target / name) == wanted, "published metadata inventory differs")
        for path, (row, _) in files.items():
            output_reader.read(target / path, row, maximum=MAX_PAYLOAD)
        output_reader.recheck()
        reader.recheck()
        require(_files(bundle) == expected_bundle, "bundle inventory changed during installation")
        parents_unchanged()
    try:
        meta_fd = _open_directory(target / "META")
        temporary = Path(tempfile.mkdtemp(prefix=".nezha-metadata-", dir=target))
        temporary_fd = _open_directory(temporary)
        for path, (_, data) in files.items():
            _write(temporary / path, data)
        _write(temporary / "receipt.json", encoded(report))
        reader.recheck()
        require(_files(bundle) == expected_bundle, "bundle inventory changed before installation")
        parents_unchanged()
        for name in ("VENDOR", "ODM"):
            owner = _inode(os.stat(name, dir_fd=temporary_fd, follow_symlinks=False))
            _publish_at(temporary_fd, name, target_fd, name)
            published.append((target_fd, name, owner))
        check_destination()
        owner = _inode(os.stat("receipt.json", dir_fd=temporary_fd, follow_symlinks=False))
        _publish_at(temporary_fd, "receipt.json", meta_fd, "nezha_target_files_metadata.json")
        published.append((meta_fd, "nezha_target_files_metadata.json", owner))
        require(_inode(os.stat("nezha_target_files_metadata.json", dir_fd=meta_fd, follow_symlinks=False)) == owner,
                "metadata receipt replaced during publication")
        result_reader = Reader()
        result_reader.read(target / "META/nezha_target_files_metadata.json", identity(encoded(report)))
        check_destination()
    except BaseException:
        # Keep another writer's replacement. Cleanup is anchored to the opened
        # parent and limited to names still identifying this invocation's inodes.
        for parent_fd, name, owner in reversed(published):
            try:
                if _inode(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != owner:
                    continue
                if owner[2] == stat.S_IFDIR:
                    require(shutil.rmtree.avoids_symlink_attacks, "safe directory cleanup unavailable")
                    shutil.rmtree(name, dir_fd=parent_fd)
                else:
                    os.unlink(name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        raise
    finally:
        if temporary_fd is not None:
            owner = _inode(os.fstat(temporary_fd))
            os.close(temporary_fd)
            try:
                if _inode(os.stat(temporary.name, dir_fd=target_fd, follow_symlinks=False)) == owner:
                    shutil.rmtree(temporary.name, dir_fd=target_fd)
            except FileNotFoundError:
                pass
        if meta_fd is not None:
            os.close(meta_fd)
        os.close(target_fd)
    return report


def selection(bundle, *, expected_receipt):
    receipt, _, _ = verify_bundle(bundle, expected_receipt=expected_receipt)
    return ("# Exact content-only factory metadata projection; no ROM readiness admission.\n"
            "BOARD_NEZHA_PREBUILT_METADATA := true\n"
            f"BOARD_NEZHA_PREBUILT_METADATA_RECEIPT_SHA256 := {expected_receipt}\n"
            f"BOARD_NEZHA_PREBUILT_METADATA_TOOL_SHA256 := "
            f"{next(row['sha256'] for row in receipt['bundle_files'] if row['path'] == 'tools/target_files_metadata.py')}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    stage_parser = sub.add_parser("stage")
    stage_parser.add_argument("--inputs-root", type=Path, required=True)
    stage_parser.add_argument("--output", type=Path, required=True)
    stage_parser.add_argument("--vendor-image", type=Path, required=True)
    stage_parser.add_argument("--odm-image", type=Path, required=True)
    for name in ("verify", "install", "selection"):
        check = sub.add_parser(name)
        check.add_argument("--bundle", type=Path, required=True)
        check.add_argument("--expected-receipt", required=True)
        if name == "install":
            check.add_argument("--target-files", type=Path, required=True)
            check.add_argument("--source-tree", type=Path, required=True)
        elif name == "verify":
            check.add_argument("--source-tree", type=Path)
            check.add_argument("--vendor-image", type=Path)
            check.add_argument("--odm-image", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            profile, composition, _ = _controls(ROOT, Reader())
            result = {"profile": profile, "source_composition": composition, "scope": SCOPE}
        elif args.command == "stage":
            result = stage(args.inputs_root, args.output, vendor_image=args.vendor_image, odm_image=args.odm_image)
        elif args.command == "install":
            result = install(args.bundle, args.target_files, expected_receipt=args.expected_receipt,
                             source_tree=args.source_tree)
        elif args.command == "selection":
            print(selection(args.bundle, expected_receipt=args.expected_receipt), end="")
            return 0
        else:
            result, _, _ = verify_bundle(args.bundle, expected_receipt=args.expected_receipt,
                                         source_tree=args.source_tree, vendor_image=args.vendor_image,
                                         odm_image=args.odm_image)
        print(encoded(result).decode(), end="")
        return 0
    except (TargetFilesMetadataError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print(f"target-files metadata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
