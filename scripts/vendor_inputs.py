#!/usr/bin/env python3
"""Generate private Nezha vendor inputs from verified extraction receipts.

The default profile preserves complete vendor/ODM images. Optional, explicit
system_ext selections use Soong prebuilts, never generic ELF/JAR/APK copies.
No firmware code, installer, ADB command, or external program is executed.
Selection JSON uses schema_version=1, device=nezha, package_sha256, and modules.
Each module requires runtime_path, sha256, size_bytes, and type (shared_library,
dex_jar, or xml); shared_library additionally requires explicit shared_libs.
XML may carry a library-registration-v1 derivation: extract one verified stock
library registration and map it to an explicitly selected system_ext DEX JAR.
DEX JARs may explicitly bind runtime_library names, registration XML and ordered
required dependencies. These need the reviewed dex_import provider patch; the
old, unnamed dependency-only selections are unchanged.
Soong properties were reviewed at Evolution-X/build_soong
cbcbea9e65503ca15b363a0b06dda88fdbcb0154 and extract-utils
19a1e68e47bbe9ba446e167b2d402953bd7e0c87. Their build checks remain enabled.
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
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

if __package__:
    from .artifact_files import publish_new_directory
    from .firmware import IntakeError, _directory, _open_regular, _signature
else:
    from artifact_files import publish_new_directory
    from firmware import IntakeError, _directory, _open_regular, _signature


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
BUFFER_SIZE = 1024 * 1024
MAX_JSON_BYTES = 64 * 1024**2
MAX_OUTPUT_BYTES = 64 * 1024**3
MAX_EXTRA_BYTES = 512 * 1024**2
MAX_XML_BYTES = 4 * 1024**2
DISK_RESERVE = 64 * 1024**2
INSTALL_PATH = "vendor/xiaomi/nezha"
MODULE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+@-]*\Z")
FLAT_CAPTURE = re.compile(r"files/[0-9]{4}\Z")
DEX_HEADERS = {b"dex\n" + version + b"\0" for version in (b"035", b"037", b"038", b"039", b"040", b"041")}


class VendorInputError(ValueError):
    """Inputs do not meet the private vendor-generation contract."""


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise VendorInputError("expected a lowercase SHA256 digest")
    return value


def _positive(value, maximum=MAX_OUTPUT_BYTES):
    if type(value) is not int or not 0 < value <= maximum:
        raise VendorInputError("invalid or excessive declared byte count")
    return value


def _object(value):
    if not isinstance(value, dict):
        raise VendorInputError("nested metadata must be an object")
    return value


def _real_directory(path):
    path = Path(os.path.abspath(path))
    for parent in [*reversed(path.parents), path]:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise VendorInputError("input/output ancestors must be real directories")
    return path


def _file_state(path):
    path = Path(os.path.abspath(path))
    _real_directory(path.parent)
    details = path.lstat()
    if not stat.S_ISREG(details.st_mode):
        raise VendorInputError("input is not a regular file")
    return {"file": path, "signature": _signature(details)}


def _unchanged(source):
    _real_directory(source["file"].parent)
    if source["signature"] != _signature(source["file"].lstat()):
        raise VendorInputError("an input changed during generation")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise VendorInputError("JSON contains duplicate keys")
        result[key] = value
    return result


def _load(path, metadata):
    source = _file_state(path)
    with _open_regular(source["file"]) as stream:
        if source["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("metadata changed before opening")
        raw = stream.read(MAX_JSON_BYTES + 1)
        if source["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("metadata changed while reading")
    _unchanged(source)
    if len(raw) > MAX_JSON_BYTES:
        raise VendorInputError("metadata exceeds the size bound")
    try:
        record = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VendorInputError("invalid metadata JSON") from exc
    if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise VendorInputError("expected a schema-1 metadata object")
    source["sha256"] = hashlib.sha256(raw).hexdigest()
    metadata.append(source)
    return record, source["sha256"]


def _list_by_name(items, key):
    if not isinstance(items, list) or len(items) > 100_000:
        raise VendorInputError("invalid or excessive record list")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or item[key] in result:
            raise VendorInputError("record names must be unique strings")
        result[item[key]] = item
    return result


def _runtime_path(path):
    if (not isinstance(path, str) or len(path) > 1024
            or not re.fullmatch(r"/[A-Za-z0-9_.+@/-]+", path)
            or str(PurePosixPath(path)) != path
            or any(part in ("", ".", "..") or len(part) > 255 for part in path[1:].split("/"))):
        raise VendorInputError("unsafe or noncanonical runtime path")
    return path


def _registration_xml(recipe):
    # Names and paths are restricted to XML-safe ASCII by _registration_recipe.
    return ('<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n'
            f'    <library name="{recipe["library_name"]}" file="{recipe["library_file"]}" />\n'
            '</permissions>\n').encode("utf-8")


def _registration_recipe(module):
    recipe = _object(module["derivation"])
    if (set(recipe) != {"kind", "source", "library_name", "source_library_file", "library_file"}
            or recipe["kind"] != "library-registration-v1"):
        raise VendorInputError("unsupported XML derivation recipe")
    source = _object(recipe["source"])
    if set(source) != {"runtime_path", "sha256", "size_bytes"}:
        raise VendorInputError("XML derivation must bind the exact captured source")
    _sha(source["sha256"])
    _positive(source["size_bytes"], MAX_XML_BYTES)
    for runtime in (module["runtime_path"], _runtime_path(source["runtime_path"])):
        if PurePosixPath(runtime).parent != PurePosixPath("/system_ext/etc/permissions") or not runtime.endswith(".xml"):
            raise VendorInputError("XML derivation is limited to system_ext library permission files")
    name = recipe["library_name"]
    if not isinstance(name, str) or len(name) > 255 or not MODULE_NAME.fullmatch(name):
        raise VendorInputError("invalid library registration name")
    old = PurePosixPath(_runtime_path(recipe["source_library_file"]))
    new = PurePosixPath(_runtime_path(recipe["library_file"]))
    if (old.parent not in {PurePosixPath("/system/framework"), PurePosixPath("/system_ext/framework")}
            or new.parent != PurePosixPath("/system_ext/framework")
            or new.suffix != ".jar" or old.name != new.name):
        raise VendorInputError("derived registration must preserve the JAR filename in system_ext/framework")
    content = _registration_xml(recipe)
    if len(content) != module["size_bytes"] or hashlib.sha256(content).hexdigest() != module["sha256"]:
        raise VendorInputError("derived XML output SHA256/size does not match its recipe")


def _selection(path, expected_package, metadata):
    if path is None:
        return [], None
    selection, digest = _load(path, metadata)
    if set(selection) != {"schema_version", "device", "package_sha256", "modules"}:
        raise VendorInputError("unsupported selection fields")
    if selection["device"] != "nezha" or selection["package_sha256"] != expected_package:
        raise VendorInputError("selection does not match the selected Nezha package")
    modules = selection["modules"]
    if not isinstance(modules, list) or len(modules) > 2048:
        raise VendorInputError("too many selected modules")
    seen_paths, seen_modules = set(), set()
    result = []
    for module in modules:
        if not isinstance(module, dict):
            raise VendorInputError("module selection must be an object")
        kind = module.get("type")
        allowed = {"runtime_path", "sha256", "size_bytes", "type"}
        if kind == "shared_library":
            allowed.add("shared_libs")
        elif kind == "dex_jar" and "runtime_library" in module:
            allowed.add("runtime_library")
        elif kind == "xml" and "derivation" in module:
            allowed.add("derivation")
        if kind not in {"shared_library", "dex_jar", "xml"} or set(module) != allowed:
            raise VendorInputError("only explicit shared_library, dex_jar and xml selections are supported")
        runtime = _runtime_path(module["runtime_path"])
        parts = PurePosixPath(runtime).parts
        if parts[1] != "system_ext":
            raise VendorInputError("extras must be explicit system_ext files; vendor/ODM stay in complete images")
        if kind == "shared_library" and (len(parts) < 4 or parts[2] not in {"lib", "lib64"} or not runtime.endswith(".so")):
            raise VendorInputError("shared library path does not preserve an Android library directory")
        if kind == "dex_jar" and (len(parts) != 4 or parts[2] != "framework" or not runtime.endswith(".jar")
                                   or parts[-1] in {"framework.jar", "services.jar", "ext.jar", "core-oj.jar", "core-libart.jar"}):
            raise VendorInputError("unsupported or conflicting framework JAR path")
        if kind == "xml" and (len(parts) < 4 or parts[2] != "etc" or not runtime.endswith(".xml")):
            raise VendorInputError("XML selection must preserve its system_ext/etc path")
        name = "nezha_" + re.sub(r"[^A-Za-z0-9_]", "_", runtime[1:])
        if "runtime_library" in module:
            library = _object(module["runtime_library"])
            if set(library) != {"name", "registration", "uses_libs"}:
                raise VendorInputError("runtime library must bind name, registration and required dependencies")
            name = library["name"]
            if (not isinstance(name, str) or len(name) > 255 or not MODULE_NAME.fullmatch(name)
                    or name.startswith("prebuilt_")):
                raise VendorInputError("runtime library needs an exact unqualified module name")
            registration = PurePosixPath(_runtime_path(library["registration"]))
            if registration.parent != PurePosixPath("/system_ext/etc/permissions") or registration.suffix != ".xml":
                raise VendorInputError("runtime library registration must be a system_ext permission XML")
            dependencies = library["uses_libs"]
            if (not isinstance(dependencies, list) or len(dependencies) > 256
                    or any(not isinstance(d, str) or len(d) > 255 or not MODULE_NAME.fullmatch(d)
                           or d.startswith("prebuilt_") for d in dependencies)
                    or len({d.casefold() for d in dependencies}) != len(dependencies)):
                raise VendorInputError("runtime uses_libs must be ordered unique exact names")
        if runtime.casefold() in seen_paths or name.casefold() in seen_modules:
            raise VendorInputError("selected files have duplicate or case-colliding paths/module names")
        seen_paths.add(runtime.casefold())
        seen_modules.add(name.casefold())
        entry = dict(module, module_name=name, path="proprietary" + runtime)
        _sha(entry["sha256"])
        _positive(entry["size_bytes"], MAX_EXTRA_BYTES)
        if "derivation" in entry:
            _registration_recipe(entry)
        if kind == "shared_library":
            dependencies = entry["shared_libs"]
            if (not isinstance(dependencies, list) or len(dependencies) > 1024
                    or any(not isinstance(d, str) or not MODULE_NAME.fullmatch(d) for d in dependencies)
                    or len(set(dependencies)) != len(dependencies)):
                raise VendorInputError("shared_libs must be explicit unique Soong module names")
            entry["shared_libs"] = sorted(dependencies)
        result.append(entry)
    jars = {entry["runtime_path"] for entry in result if entry["type"] == "dex_jar"}
    registrations = set()
    for entry in result:
        if "derivation" not in entry:
            continue
        recipe = entry["derivation"]
        if recipe["library_file"] not in jars:
            raise VendorInputError("derived registration must name an explicitly selected DEX JAR")
        if recipe["library_name"] in registrations:
            raise VendorInputError("duplicate derived library registration name")
        registrations.add(recipe["library_name"])
    _runtime_graph(result)
    return sorted(result, key=lambda entry: entry["runtime_path"]), digest


def _runtime_graph(modules):
    """Require one selected registration per library and a closed acyclic graph."""
    libraries = {entry["module_name"]: entry for entry in modules if "runtime_library" in entry}
    xmls = {entry["runtime_path"] for entry in modules if entry["type"] == "xml"}
    registrations = set()
    for name, entry in libraries.items():
        runtime = entry["runtime_library"]
        registration = runtime["registration"]
        if registration not in xmls or registration in registrations:
            raise VendorInputError("runtime registration must identify one separately selected XML")
        registrations.add(registration)
        if any(dependency not in libraries for dependency in runtime["uses_libs"]):
            raise VendorInputError("runtime dependency must be another explicitly registered DEX JAR")
    # Iterative topological traversal also handles maliciously deep graphs.
    pending = {name: len(entry["runtime_library"]["uses_libs"]) for name, entry in libraries.items()}
    dependents = {name: [] for name in libraries}
    for name, entry in libraries.items():
        for dependency in entry["runtime_library"]["uses_libs"]:
            dependents[dependency].append(name)
    ready = [name for name, count in pending.items() if count == 0]
    visited = 0
    while ready:
        visited += 1
        for parent in dependents[ready.pop()]:
            pending[parent] -= 1
            if pending[parent] == 0:
                ready.append(parent)
    if visited != len(libraries):
        raise VendorInputError("runtime uses-library dependencies contain a cycle")
    return libraries


def _validate_runtime_registrations(staging, modules):
    """Match runtime metadata to the actual copied XML, not caller assertions."""
    libraries = _runtime_graph(modules)
    if not libraries:
        return
    registrations = {}
    paths = {entry["runtime_path"]: name for name, entry in libraries.items()}
    for entry in modules:
        if entry["type"] != "xml":
            continue
        path = staging / entry["path"]
        _verify_output(path, entry)
        with _open_regular(path) as stream:
            raw = stream.read(MAX_XML_BYTES + 1)
        if len(raw) != entry["size_bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise VendorInputError("runtime registration changed during validation")
        try:
            text = raw.decode("utf-8-sig")
            if len(raw) > MAX_XML_BYTES or "\x00" in text or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
                raise VendorInputError("runtime registrations reject DTDs, entities and non-UTF-8 XML")
            root = ET.fromstring(text)
        except (UnicodeError, ET.ParseError) as exc:
            raise VendorInputError("runtime registration XML is invalid") from exc
        for node in root.iter():
            name, jar = node.get("name"), node.get("file")
            if name not in libraries and jar not in paths:
                continue
            if name not in libraries or paths.get(jar) != name:
                raise VendorInputError("runtime registration aliases or remaps a selected JAR")
            library = libraries[name]["runtime_library"]
            attributes = {"name": name, "file": libraries[name]["runtime_path"]}
            if library["uses_libs"]:
                attributes["dependency"] = ":".join(library["uses_libs"])
            if (name in registrations or entry["runtime_path"] != library["registration"]
                    or root.tag != "permissions" or root.attrib or (root.text or "").strip()
                    or list(root) != [node] or node.tag != "library" or node.attrib != attributes
                    or len(node) or (node.text or "").strip() or (node.tail or "").strip()):
                raise VendorInputError("runtime XML name, path, dependency order or single-registration scope differs")
            registrations[name] = entry["runtime_path"]
    if set(registrations) != set(libraries):
        raise VendorInputError("selected runtime library has no matching XML registration")


def _capture_sources(analysis, outputs, modules, paths, metadata):
    if not modules and not paths:
        return {}, []
    capture_paths = list(paths)
    default = analysis / "erofs/system_ext-contract-capture/receipt.json"
    if modules and default.exists():
        capture_paths.append(default)
    if len(capture_paths) > 64:
        raise VendorInputError("too many capture receipts")
    captures, receipt_hashes = {}, []
    for path in sorted({Path(os.path.abspath(p)) for p in capture_paths}):
        capture, capture_sha = _load(path, metadata)
        if (capture.get("operation") != "erofs-capture"
                or any(capture.get(k) is not False for k in ("firmware_executed", "image_mounted", "symlinks_followed"))):
            raise VendorInputError("capture must be a read-only regular-file EROFS receipt")
        image = _object(capture.get("image"))
        names = [name for name, output in outputs.items() if output["sha256"] == image.get("sha256")]
        if len(names) != 1 or names[0] != "system_ext_a":
            raise VendorInputError("capture has the wrong parent image")
        name = names[0]
        if image.get("size_bytes") != outputs[name]["size_bytes"]:
            raise VendorInputError("capture parent image size conflicts")
        inventory_dir = analysis / "erofs" / (name + "-inventory")
        inventory, inventory_sha = _load(inventory_dir / "inventory.json", metadata)
        scan, scan_sha = _load(inventory_dir / "receipt.json", metadata)
        if (inventory_sha != capture.get("inventory_sha256")
                or scan_sha != capture.get("inventory_receipt_sha256")
                or _object(scan.get("inventory")).get("sha256") != inventory_sha
                or scan.get("operation") != "erofs-scan"
                or scan.get("symlinks_followed") is not False or scan.get("image_mounted") is not False
                or _object(inventory.get("image")).get("sha256") != image["sha256"]
                or _object(scan.get("image")).get("sha256") != image["sha256"]):
            raise VendorInputError("capture/inventory receipt chain does not match")
        entries = _list_by_name(inventory.get("entries"), "path")
        files = _list_by_name(capture.get("files"), "path")
        if len(files) > 4096:
            raise VendorInputError("capture file count exceeds bound")
        output_names = set()
        for image_path, item in files.items():
            runtime = "/system_ext" + _runtime_path(image_path)
            entry = entries.get(image_path, {})
            if (item.get("type") != "regular" or item.get("readback_verified") is not True
                    or entry.get("type") != "regular" or entry.get("nid") != item.get("nid")
                    or type(item.get("nid")) is not int or not 0 <= item["nid"] < 2**64):
                raise VendorInputError("capture file is not an inventoried regular inode")
            filename = item.get("output_path")
            if not isinstance(filename, str) or not FLAT_CAPTURE.fullmatch(filename) or filename in output_names:
                raise VendorInputError("capture output paths must be unique flat filenames")
            output_names.add(filename)
            _sha(item.get("sha256"))
            _positive(item.get("size_bytes"), MAX_EXTRA_BYTES)
            candidate = {"file": path.parent / filename, "sha256": item["sha256"],
                         "size_bytes": item["size_bytes"], "source_image_sha256": image["sha256"],
                         "capture_receipt_sha256": capture_sha, "nid": item["nid"]}
            if runtime in captures:
                if any(captures[runtime][key] != candidate[key] for key in ("sha256", "size_bytes", "source_image_sha256", "nid")):
                    raise VendorInputError("capture receipts disagree about a selected runtime path")
            else:
                captures[runtime] = candidate
        receipt_hashes.append(capture_sha)
    for module in modules:
        expected = module["derivation"]["source"] if "derivation" in module else module
        captured = captures.get(expected["runtime_path"])
        if captured is None or any(expected[key] != captured[key] for key in ("sha256", "size_bytes")):
            raise VendorInputError("selected extra is absent from verified captures or its hash/size conflicts")
    return captures, sorted(set(receipt_hashes))


def _context(analysis, source_record, expected_package_sha256, selection, capture_receipts, max_bytes):
    expected = _sha(expected_package_sha256)
    _positive(max_bytes)
    analysis = _real_directory(analysis)
    metadata = []
    layout, layout_sha = _load(source_record, metadata)
    device = _object(layout.get("device"))
    package = _object(layout.get("package"))
    if (device.get("codename") != "nezha" or device.get("hardware_region") != "CN"
            or package.get("sha256") != expected):
        raise VendorInputError("source record is not the explicitly selected China Nezha package")
    if type(package.get("origin_verified")) is not bool or package.get("source_kind") not in {"url", "user-provided"}:
        raise VendorInputError("source provenance must be explicit")
    avb_status = _object(layout.get("verification_boundaries")).get("avb_partition_set_status")
    if avb_status not in {"failed", "unverified", "verified", "passed"}:
        raise VendorInputError("source record must explicitly classify its AVB status")
    raw_sha = _sha(_object(layout.get("raw_image")).get("sha256"))
    partitions = _list_by_name(layout.get("partitions"), "name")
    logical, logical_sha = _load(analysis / "logical-partitions/receipt.json", metadata)
    if (logical.get("status") != "complete" or _object(logical.get("source_image")).get("sha256") != raw_sha
            or any(logical.get(k) is not True for k in ("all_geometry_and_metadata_copies_valid",
                                                       "all_primary_backup_pairs_match", "all_slots_identical"))):
        raise VendorInputError("logical extraction is incomplete or has a different parent")
    outputs = _list_by_name(logical.get("outputs"), "partition")
    for name, output in outputs.items():
        recorded = _object(partitions.get(name))
        extraction = _object(recorded.get("extraction"))
        if (not re.fullmatch(r"[a-z][a-z0-9_]*_[ab]", name) or output.get("filename") != name + ".img"
                or output.get("readback_verified") is not True or output.get("parent_image_sha256") != raw_sha
                or extraction.get("sha256") != output.get("sha256") or extraction.get("readback_verified") is not True
                or extraction.get("parent_image_sha256") != raw_sha or extraction.get("status") != "extracted"
                or type(recorded.get("size_bytes")) is not int
                or recorded.get("size_bytes") != output.get("size_bytes")):
            raise VendorInputError("logical image and source record disagree")
        _sha(output.get("sha256"))
        _positive(output.get("size_bytes"))
    modules, selection_sha = _selection(selection, expected, metadata)
    captures, capture_hashes = _capture_sources(analysis, outputs, modules, capture_receipts, metadata)
    blobs, images, extras = [], {}, []
    for partition in ("vendor", "odm"):
        name = partition + "_a"
        output = outputs.get(name)
        if output is None or _object(partitions[name].get("filesystem")).get("format") != "EROFS":
            raise VendorInputError("vendor_a and odm_a must have recorded EROFS extraction")
        entry = {"source_partition": name, "path": f"proprietary/images/{partition}.img",
                 "sha256": output["sha256"], "size_bytes": output["size_bytes"], "readback_verified": False}
        source = _file_state(analysis / "logical-partitions" / output["filename"])
        blobs.append(dict(source, record=entry, kind="image"))
        images[partition] = entry
    for module in modules:
        input_record = module["derivation"]["source"] if "derivation" in module else module
        captured = captures[input_record["runtime_path"]]
        entry = dict(module, source_image_sha256=captured["source_image_sha256"],
                     capture_receipt_sha256=captured["capture_receipt_sha256"], readback_verified=False)
        if "derivation" in module:
            recipe = module["derivation"]
            recipe_sha = hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            entry["derivation"] = dict(
                recipe, recipe_sha256=recipe_sha,
                source=dict(recipe["source"], image_sha256=captured["source_image_sha256"],
                            capture_receipt_sha256=captured["capture_receipt_sha256"], nid=captured["nid"],
                            hash_verified=False))
        else:
            entry["nid"] = captured["nid"]
        blobs.append(dict(_file_state(captured["file"]), record=entry, input_record=input_record,
                          kind="derived_xml" if "derivation" in module else module["type"]))
        extras.append(entry)
    required = sum(blob["record"]["size_bytes"] for blob in blobs)
    if required > max_bytes or any(blob["signature"][2] != blob.get("input_record", blob["record"])["size_bytes"]
                                   for blob in blobs):
        raise VendorInputError("source size differs from receipt or exceeds the output bound")
    receipt = {
        "schema_version": 1, "device": "nezha", "operation": "vendor-inputs-plan",
        "install_path": INSTALL_PATH, "profile": "prebuilt-vendor-odm-with-explicit-system-ext-extras",
        "source": {"package_sha256": expected, "source_record_sha256": layout_sha,
                   "raw_super_sha256": raw_sha, "logical_receipt_sha256": logical_sha,
                   "origin_verified": package["origin_verified"], "source_kind": package["source_kind"],
                   "input_avb_status": "verified" if avb_status == "passed" else avb_status,
                   "source_trust_is_from_record_not_reauthenticated": True,
                   "selection_sha256": selection_sha, "capture_receipt_sha256": capture_hashes},
        "images": images, "extras": extras, "generated_files": [], "total_blob_bytes": required,
        "verification": {"input_blob_hashes_checked": False, "avb_checked_by_this_tool": False,
                         "full_dependency_closure_verified": False, "firmware_executed": False,
                         "phone_modified": False, "kernel_or_dlkm_files_generated": False,
                         "retained_vbmeta_reused": False, "signature_or_elf_checks_disabled": False},
        "limits": ["Input AVB status is preserved; staging does not create valid AVB footers or approve flashing.",
                   "Complete vendor/ODM images preserve their file metadata; generated extras still need policy and dependency review.",
                   "DEX imports do not establish app uses-library/class-loader compatibility; APK import is not supported.",
                   "Explicit shared_libs are caller-selected Soong modules; Soong must validate dependencies and symbols.",
                   "Permission XML and its referenced paths are copied unchanged, including unresolved mappings."]}
    if any("derivation" in module for module in modules):
        receipt["limits"][-1] = ("Explicit library-registration-v1 XML recipes select one verified stock registration; "
                                "the recorded path transformation does not establish runtime or class-loader compatibility.")
    return analysis, metadata, blobs, receipt


def _derive_registration(source, destination):
    entry = source["record"]
    recipe = entry["derivation"]
    expected = recipe["source"]
    _unchanged(source)
    with _open_regular(source["file"]) as stream:
        if source["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("registration source changed before opening")
        raw = stream.read(MAX_XML_BYTES + 1)
        if source["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("registration source changed while reading")
    _unchanged(source)
    if len(raw) != expected["size_bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise VendorInputError("registration source SHA256/size mismatch")
    try:
        text = raw.decode("utf-8-sig")
        if "\x00" in text or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise VendorInputError("XML derivation does not accept DTDs, entities or non-UTF-8 input")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as exc:
        raise VendorInputError("registration source is not a supported XML document") from exc
    matches = [node for node in root.iter() if node.get("name") == recipe["library_name"]]
    if (root.tag != "permissions" or root.attrib or (root.text or "").strip()
            or len(matches) != 1 or matches[0] not in list(root)):
        raise VendorInputError("expected one direct stock library registration in permissions")
    selected = matches[0]
    if (selected.tag != "library" or selected.attrib != {"name": recipe["library_name"], "file": recipe["source_library_file"]}
            or len(selected) or (selected.text or "").strip() or (selected.tail or "").strip()):
        raise VendorInputError("stock library registration has unexpected attributes, content or file path")
    content = _registration_xml(recipe)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _write_file(destination.parent, destination.name, content)
    _verify_output(destination, entry)
    expected["hash_verified"] = True
    entry["readback_verified"] = True


def _copy_blob(source, destination):
    expected = source["record"]
    _unchanged(source)
    digest, size = hashlib.sha256(), 0
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _open_regular(source["file"]) as stream, destination.open("xb") as copied:
        os.chmod(destination, 0o600)
        if source["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("blob changed before opening")
        while data := stream.read(BUFFER_SIZE):
            size += len(data)
            if size > expected["size_bytes"]:
                raise VendorInputError("blob grew during copying")
            digest.update(data)
            copied.write(data)
        copied.flush()
        os.fsync(copied.fileno())
        if source["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("blob changed during copying")
    _unchanged(source)
    if size != expected["size_bytes"] or digest.hexdigest() != expected["sha256"]:
        raise VendorInputError("input blob SHA256/size mismatch")
    _verify_output(destination, expected)
    expected["readback_verified"] = True


def _verify_output(path, expected):
    before = _file_state(path)
    digest, size = hashlib.sha256(), 0
    with _open_regular(path) as stream:
        if before["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("staged output changed before readback")
        while data := stream.read(BUFFER_SIZE):
            size += len(data)
            digest.update(data)
        if before["signature"] != _signature(os.fstat(stream.fileno())):
            raise VendorInputError("staged output changed during readback")
    _unchanged(before)
    if size != expected["size_bytes"] or digest.hexdigest() != expected["sha256"]:
        raise VendorInputError("staged output failed SHA256 readback")
    return before


def _validate_format(path, entry, kind):
    with _open_regular(path) as stream:
        if kind == "image":
            stream.seek(1024)
            if stream.read(4) != b"\xe2\xe1\xf5\xe0":
                raise VendorInputError("recorded EROFS image has the wrong magic")
        elif kind == "shared_library":
            header = stream.read(64)
            if len(header) < 52 or header[:4] != b"\x7fELF" or header[5:7] != b"\x01\x01":
                raise VendorInputError("extra is not a supported little-endian ELF library")
            elf_type, machine = struct.unpack_from("<HH", header, 16)
            bits = 64 if header[4] == 2 else 32 if header[4] == 1 else 0
            if elf_type != 3 or (bits, machine) not in {(64, 183), (32, 40)}:
                raise VendorInputError("ELF class/machine/type does not match an ARM shared library")
            header_size = 64 if bits == 64 else 52
            if (len(header) < header_size or struct.unpack_from("<I", header, 20)[0] != 1
                    or struct.unpack_from("<H", header, 52 if bits == 64 else 40)[0] != header_size):
                raise VendorInputError("truncated or malformed ELF header")
            directory = PurePosixPath(entry["runtime_path"]).parts[2]
            if directory != ("lib64" if bits == 64 else "lib"):
                raise VendorInputError("ELF architecture conflicts with the selected partition path")
            entry.update(elf_bits=bits, elf_machine=machine)
        elif kind == "xml":
            if entry["size_bytes"] > MAX_XML_BYTES:
                raise VendorInputError("XML exceeds the validation bound")
            try:
                ET.fromstring(stream.read())
            except ET.ParseError as exc:
                raise VendorInputError("selected XML is not well formed") from exc
        elif kind == "dex_jar":
            try:
                with zipfile.ZipFile(stream) as archive:
                    entries = archive.infolist()
                    names = [item.filename for item in entries]
                    if (not entries or len(entries) > 4096 or len(set(names)) != len(names)
                            or "classes.dex" not in names or any(name.endswith(".class") for name in names)
                            or sum(item.file_size for item in entries) > MAX_EXTRA_BYTES):
                        raise VendorInputError("expected a bounded DEX JAR, not a class JAR")
                    for item in entries:
                        kind_bits = stat.S_IFMT(item.external_attr >> 16)
                        if (item.flag_bits & 1 or item.filename != item.orig_filename
                                or ".." in PurePosixPath(item.filename).parts or item.filename.startswith("/")
                                or "\\" in item.filename or kind_bits not in (0, stat.S_IFREG, stat.S_IFDIR)):
                            raise VendorInputError("unsafe DEX JAR entry")
                        with archive.open(item) as member:
                            if item.filename.endswith(".dex"):
                                header = member.read(8)
                                if item.file_size < 112 or header not in DEX_HEADERS:
                                    raise VendorInputError("JAR member is not a recognized DEX header")
                            while member.read(BUFFER_SIZE):
                                pass  # Stream CRC verification without extracting archive members.
            except (zipfile.BadZipFile, NotImplementedError) as exc:
                raise VendorInputError("invalid or unsupported DEX JAR") from exc


def _bp_value(value):
    return json.dumps(value, ensure_ascii=True)


def _module_text(entry):
    runtime = PurePosixPath(entry["runtime_path"])
    kind = entry["type"]
    properties = {"name": entry["module_name"], "owner": "xiaomi", "system_ext_specific": True}
    if kind == "shared_library":
        module_type = "cc_prebuilt_library_shared"
        properties.update(stem=runtime.name[:-3], compile_multilib=str(entry["elf_bits"]))
        relative = "/".join(runtime.parts[3:-1])
        if relative:
            properties["relative_install_path"] = relative
    elif kind == "dex_jar":
        module_type = "dex_import"
        properties.update(stem=runtime.name[:-4], jars=[entry["path"]])
        if "runtime_library" in entry:
            # Emit even an empty list: unpatched dex_import must reject this
            # profile instead of silently producing a provider-less import.
            properties["uses_libs"] = entry["runtime_library"]["uses_libs"]
    else:
        module_type = "prebuilt_etc_xml"
        properties.update(src=entry["path"], filename=runtime.name)
        relative = "/".join(runtime.parts[3:-1])
        if relative:
            properties["relative_install_path"] = relative
    lines = [module_type + " {"]
    lines += [f"    {name}: {_bp_value(value)}," for name, value in properties.items()]
    if kind == "shared_library":
        architecture = "android_arm64" if entry["elf_bits"] == 64 else "android_arm"
        lines += ["    target: {", f"        {architecture}: {{",
                  f"            srcs: {_bp_value([entry['path']])},",
                  f"            shared_libs: {_bp_value(entry['shared_libs'])},",
                  "        },", "    },", "    strip: { none: true },", "    check_elf_files: true,"]
    return "\n".join([*lines, "}", ""])


def _generated_text(receipt):
    comment = "# Generated by vendor_inputs.py; private proprietary inputs, not a flash approval.\n"
    board = comment + "NEZHA_VENDOR_PATH ?= vendor/xiaomi/nezha\n"
    for partition in ("vendor", "odm"):
        board += f"BOARD_PREBUILT_{partition.upper()}IMAGE := $(NEZHA_VENDOR_PATH)/proprietary/images/{partition}.img\n"
    product = comment + "NEZHA_VENDOR_PATH ?= vendor/xiaomi/nezha\nPRODUCT_SOONG_NAMESPACES += $(NEZHA_VENDOR_PATH)\n"
    modules = sorted(entry["module_name"] for entry in receipt["extras"])
    if modules:
        product += "PRODUCT_PACKAGES += \\\n    " + " \\\n    ".join(modules) + "\n"
    bp = "// Generated private inputs; original files and validation checks are preserved.\nsoong_namespace {}\n\n"
    if any("derivation" in entry for entry in receipt["extras"]):
        bp = "// Generated private inputs; XML derivations are recorded and validation checks are preserved.\nsoong_namespace {}\n\n"
    bp += "\n".join(_module_text(entry) for entry in receipt["extras"])
    readme = ("Private Nezha vendor inputs\n\n"
              f"Install the complete tree at {INSTALL_PATH} in the Linux source checkout.\n"
              "Inherit nezha-vendor.mk; include BoardConfigVendor.mk from the device BoardConfig.\n"
              f"Parent package: {receipt['source']['package_sha256']}\n"
              f"Recorded input AVB status: {receipt['source']['input_avb_status']}\n\n"
              + "\n".join(receipt["limits"]) + "\n")
    return {".gitignore": "*\n!.gitignore\n", "BoardConfigVendor.mk": board,
            "nezha-vendor.mk": product, "Android.bp": bp, "README.vendor-inputs.txt": readme}


def _write_file(staging, name, content):
    path = staging / name
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    record = {"path": name, "sha256": hashlib.sha256(content).hexdigest(),
              "size_bytes": len(content), "readback_verified": True}
    _verify_output(path, record)
    return record


def plan_inputs(analysis, source_record, *, expected_package_sha256, selection=None,
                capture_receipts=(), max_bytes=MAX_OUTPUT_BYTES):
    """Validate metadata and show a plan; do not claim source blob hashes checked."""
    _, metadata, blobs, receipt = _context(analysis, source_record, expected_package_sha256,
                                         selection, capture_receipts, max_bytes)
    for source in [*metadata, *blobs]:
        _unchanged(source)
    return receipt


def stage_inputs(analysis, source_record, output_dir, *, expected_package_sha256,
                 selection=None, capture_receipts=(), max_bytes=MAX_OUTPUT_BYTES):
    """Hash/copy inputs and atomically publish a new, deterministic private tree."""
    destination = Path(os.path.abspath(output_dir))
    private_roots = [WORKSPACE_ROOT / "artifacts", WORKSPACE_ROOT / "evidence"]
    if not any(parent in destination.parents for parent in private_roots):
        raise VendorInputError("vendor output must be a new private artifacts/ or evidence/ directory")
    if os.path.lexists(destination):
        raise VendorInputError("output already exists; no existing tree is replaced")
    analysis = _real_directory(analysis)
    for ancestor in destination.parents:
        try:
            if os.path.samestat(ancestor.stat(), analysis.stat()):
                raise VendorInputError("vendor output must remain outside the input analysis directory")
        except FileNotFoundError:
            pass
    analysis, metadata, blobs, receipt = _context(analysis, source_record, expected_package_sha256,
                                                selection, capture_receipts, max_bytes)
    parent = _directory(destination.parent)
    if shutil.disk_usage(parent).free < receipt["total_blob_bytes"] + DISK_RESERVE:
        raise VendorInputError("insufficient disk space for the private vendor tree")
    lock = parent / ("." + destination.name + ".lock")
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    staging = None
    try:
        staging = Path(tempfile.mkdtemp(prefix="." + destination.name + "-", dir=parent))
        for source in blobs:
            target = staging / source["record"]["path"]
            if source["kind"] == "derived_xml":
                _derive_registration(source, target)
                _validate_format(target, source["record"], "xml")
            else:
                _copy_blob(source, target)
                _validate_format(target, source["record"], source["kind"])
        _validate_runtime_registrations(staging, receipt["extras"])
        if any("runtime_library" in entry for entry in receipt["extras"]):
            receipt["verification"]["runtime_registration_graph_checked"] = True
            receipt["limits"].append(
                "Runtime DEX names, selected registration XML and ordered required dependencies agree; "
                "the reviewed Soong provider patch, real class-loader contexts and runtime still need validation.")
        receipt["operation"] = "vendor-inputs-stage"
        receipt["verification"]["input_blob_hashes_checked"] = True
        for name, content in sorted(_generated_text(receipt).items()):
            receipt["generated_files"].append(_write_file(staging, name, content.encode()))
        raw = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
        receipt_file = _write_file(staging, "vendor-inputs.json", raw)
        output_states = []
        for record in [*receipt["images"].values(), *receipt["extras"], *receipt["generated_files"], receipt_file]:
            output_states.append(_verify_output(staging / record["path"], record))
        for source in [*metadata, *blobs, *output_states]:
            _unchanged(source)
        _real_directory(parent)
        publish_new_directory(staging, destination)
        staging = None
        return receipt
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "stage"):
        command = commands.add_parser(name)
        command.add_argument("--analysis", required=True, type=Path)
        command.add_argument("--source-record", required=True, type=Path)
        command.add_argument("--expected-package-sha256", required=True)
        command.add_argument("--selection", type=Path, help="explicit system_ext module selection JSON")
        command.add_argument("--capture-receipt", action="append", default=[], type=Path)
        command.add_argument("--max-bytes", type=int, default=MAX_OUTPUT_BYTES)
        if name == "stage":
            command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    options = dict(expected_package_sha256=args.expected_package_sha256, selection=args.selection,
                   capture_receipts=args.capture_receipt, max_bytes=args.max_bytes)
    try:
        if args.command == "plan":
            result = plan_inputs(args.analysis, args.source_record, **options)
        else:
            result = stage_inputs(args.analysis, args.source_record, args.output, **options)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (VendorInputError, IntakeError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"vendor inputs: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
