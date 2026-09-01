#!/usr/bin/env python3
"""Join supplied APK selections and EROFS evidence; never admit or run a ROM.

This is an offline, read-only preparation. Native graph/scan/capture provenance,
the actual Package2 binding, APEX-contained APKs, signatures and runtime label
resolution remain separate obligations. Numeric capture filenames are not
passed to the native checker: its proposed paths preserve each APK basename.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
import re

if __package__:
    from . import erofs_inventory as erofs
    from . import target_files_metadata as metadata
else:
    import erofs_inventory as erofs
    import target_files_metadata as metadata


OPERATION = "prepare-nezha-final-apk-projection-v1"
CONTEXT = {"device": "nezha", "product": "lineage_nezha", "branch": "bka",
           "release": "bp4a", "variant": "user", "page_size_bytes": 4096}
PLATFORM = ("system", "system_ext", "product")
NATIVE_PARTITIONS = (*PLATFORM, "vendor", "odm")
PARTITIONS = (*NATIVE_PARTITIONS, "mi_ext", "system_dlkm", "vendor_dlkm")
NATIVE_ROOT = "/nezha-final-apk-projection"
MAX_REQUEST = 8 * 1024**2
MAX_RECORD = 16 * 1024**2
MAX_GRAPH_SOURCE = 64 * 1024**2
MAX_METADATA_TOTAL = 256 * 1024**2
MAX_APKS = 32768
MAX_CAPTURES = 128
MAX_IMAGE = 16 * 1024**3
MAX_PAYLOAD_TOTAL = 16 * 1024**3

# Paths, not historical inode numbers/image hashes, survive the policy3 EROFS
# derivation. Every path below must still have an extracted, rehashed payload.
# Basis: reports/remaining-policy-contexts-20260829/treble-plan/plan.json.
FACTORY_APPS = {
    "vendor": (
        "/app/CACertService/CACertService.apk", "/app/CneApp/CneApp.apk",
        "/app/ConnectionSecurityService/ConnectionSecurityService.apk",
        "/app/IWlanService/IWlanService.apk", "/app/TimeService/TimeService.apk",
        "/app/TrustZoneAccessService/TrustZoneAccessService.apk",
        "/app/TxPwrAdmin/TxPwrAdmin.apk",
        "/app/com.qualcomm.qti.gpudrivers.canoe.api36/com.qualcomm.qti.gpudrivers.canoe.api36.apk",
    ),
    "odm": ("/app/GFDelmarSetting/GFDelmarSetting.apk",
            "/app/QfsFactoryTest/QfsFactoryTest.apk"),
}
FACTORY_OVERLAYS = {
    "vendor": (
        "/overlay/NfcResTarget.apk", "/overlay/SecureElementResTarget_Vendor.apk",
        "/overlay/UwbResTarget_Vendor.apk", "/overlay/WifiResMainlineTarget.apk",
        "/overlay/WifiResMainlineTarget_spf.apk", "/overlay/WifiResTarget.apk",
        "/overlay/WifiResTarget_spf.apk", "/overlay/XpanResTarget_Vendor.apk",
    ),
    "odm": ("/overlay/FrameworksResTarget_Vendor.apk",),
}
FALSE_SCOPE = (
    "package2_admitted", "graph_selection_authenticated", "native_scan_execution_authenticated",
    "native_capture_execution_authenticated", "native_tool_authenticated",
    "image_bytes_rehashed", "complete_installed_apk_inventory_verified",
    "apex_contained_apks_verified", "package_names_verified", "signatures_verified",
    "privileged_permissions_verified", "effective_mac_seapp_labels_verified",
    "treble_labeling_verified", "native_projection_materialized", "native_execution_ready",
    "native_commands_run", "source_or_android_output_modified", "phone_accessed",
    "complete_rom_ready",
)


class ProjectionError(ValueError):
    """Supplied evidence is missing, inconsistent, unsafe or outside this scope."""


def require(value, message):
    if not value:
        raise ProjectionError(message)


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), label + " fields differ")


def integer(value, maximum, label, minimum=0):
    require(type(value) is int and minimum <= value <= maximum, "invalid " + label)
    return value


def pin(value, maximum, *, nonempty=True):
    closed(value, ("sha256", "size_bytes"), "identity")
    result = metadata.expected(value, maximum)
    require(not nonempty or result["size_bytes"] > 0, "empty input identity")
    return result


def reference(value, maximum, *, nonempty=True):
    closed(value, ("path", "sha256", "size_bytes"), "file reference")
    metadata.relative(value["path"])
    pin({key: value[key] for key in ("sha256", "size_bytes")}, maximum, nonempty=nonempty)
    return value


def image_identity(value):
    closed(value, ("path", "sha256", "size_bytes"), "recorded image")
    recorded_path(value["path"])
    return pin({key: value[key] for key in ("sha256", "size_bytes")}, MAX_IMAGE)


def recorded_path(value):
    require(type(value) is str and 0 < len(value) <= 4096 and value.isprintable(),
            "invalid recorded absolute path")
    path = PurePosixPath(value)
    require(path.is_absolute() and path.as_posix() == value and not value.startswith("//")
            and ".." not in path.parts, "noncanonical recorded absolute path")


def timestamp(value):
    require(type(value) is str and 0 < len(value) <= 64, "invalid receipt timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ProjectionError("invalid receipt timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0),
            "receipt timestamp must be UTC")


def tool_identity(value):
    closed(value, ("path", "sha256", "size_bytes", "requested_path", "version"), "EROFS tool")
    recorded_path(value["path"])
    recorded_path(value["requested_path"])
    require(value["version"] == erofs.TOOL_VERSION, "unsupported EROFS receipt producer")
    return pin({key: value[key] for key in ("sha256", "size_bytes")}, erofs.MAX_FILE_BYTES)


def runtime_path(partition, image_root, path):
    """Map an explicit image root; never silently strip a second /system."""
    require(path != image_root and (image_root == "/" or path.startswith(image_root + "/")),
            "APK lies outside the explicitly selected image root")
    suffix = path if image_root == "/" else path[len(image_root):]
    # Only projected APK names need this Make/list-safe grammar. Other inode
    # names, including the legitimate /bin/[ file, use erofs._path instead.
    metadata.relative(suffix[1:])
    require(path.endswith(".apk"), "noncanonical APK suffix requires separate review")
    return "/" + partition + suffix


def included(partition, path):
    parts = PurePosixPath(path).parts
    return partition in NATIVE_PARTITIONS and len(parts) >= 4 and parts[2] in ("app", "priv-app")


def exclusion_reason(partition, path):
    if partition not in NATIVE_PARTITIONS:
        return "outside-native-partition-scope"
    first = PurePosixPath(path).parts[2]
    if first == "overlay":
        return "overlay-path-outside-app-scope"
    if first == "framework":
        return "framework-path-outside-app-scope"
    return "other-path-outside-app-scope"


def inventory_entries(inventory, receipt, selected_image, inventory_pin):
    closed(inventory, ("schema_version", "image", "entries"), "EROFS inventory")
    closed(receipt, ("schema_version", "operation", "image", "tool", "created_at_utc",
                     "inventory", "entry_count", "symlinks_followed", "image_mounted",
                     "origin_verified"), "EROFS scan receipt")
    require(type(inventory["schema_version"]) is int and inventory["schema_version"] == 1
            and type(receipt["schema_version"]) is int and receipt["schema_version"] == 1
            and receipt["operation"] == "erofs-scan", "wrong inventory/scan operation")
    require(all(receipt[key] is False for key in ("symlinks_followed", "image_mounted", "origin_verified")),
            "scan scope differs from the original read-only capture")
    timestamp(receipt["created_at_utc"])
    tool = tool_identity(receipt["tool"])
    require(image_identity(inventory["image"]) == image_identity(receipt["image"]) == selected_image,
            "inventory/scan image identity differs")
    closed(receipt["inventory"], ("name", "sha256", "size_bytes"), "scan inventory reference")
    require(receipt["inventory"]["name"] == "inventory.json"
            and metadata.expected(receipt["inventory"], erofs.MAX_INVENTORY_BYTES) == inventory_pin,
            "scan receipt does not bind the exact full inventory")
    entries = inventory["entries"]
    require(type(entries) is list and 1 <= len(entries) <= erofs.MAX_ENTRIES,
            "complete bounded inventory entries required")
    require(integer(receipt["entry_count"], erofs.MAX_ENTRIES, "entry count", 1) == len(entries),
            "scan inventory count differs")
    paths, inode_types, directories = {}, {}, set()
    for entry in entries:
        closed(entry, ("path", "nid", "type"), "inventory entry")
        path = erofs._path(entry["path"])
        nid = integer(entry["nid"], 2**64 - 1, "inode number")
        kind = entry["type"]
        require(path not in paths and type(kind) is str and kind in erofs.TYPE_NAMES.values(),
                "duplicate path or invalid inventory kind")
        require(inode_types.setdefault(nid, kind) == kind, "inconsistent inventory inode type")
        if kind == "directory":
            require(nid not in directories, "directory inode alias or loop")
            directories.add(nid)
        paths[path] = entry
    require(paths.get("/", {}).get("type") == "directory", "inventory root directory missing")
    for path in paths:
        require(path == "/" or paths.get(str(PurePosixPath(path).parent), {}).get("type") == "directory",
                "inventory entry lacks its complete directory ancestry")
    return paths, tool


class _Inputs:
    """Confine selectors and reuse the existing no-follow streamed reader."""

    def __init__(self, root):
        self.root = metadata.real_directory(root)
        self.reader = metadata.Reader()
        self.roles, self.inodes = {}, {}
        self.metadata_bytes = self.payload_bytes = 0

    def read(self, row, maximum, role, *, payload=False):
        reference(row, maximum, nonempty=not payload)
        path = self.root / row["path"]
        require(path not in self.roles, "input path reused for different evidence roles")
        self.roles[path] = role
        if payload:
            self.payload_bytes += row["size_bytes"]
            require(self.payload_bytes <= MAX_PAYLOAD_TOTAL, "aggregate payload limit exceeded")
        else:
            self.metadata_bytes += row["size_bytes"]
            require(self.metadata_bytes <= MAX_METADATA_TOTAL, "aggregate metadata limit exceeded")
        data = self.reader.read(path, row, maximum=maximum, data=not payload)
        inode = self.reader.bindings[path][1][:2]
        require(inode not in self.inodes, "physical input alias across evidence roles")
        self.inodes[inode] = path
        return data

    def document(self, row, maximum, role):
        return metadata._json(self.read(row, maximum, role))


def capture_payloads(inputs, partition, references, selected_image, scan_pin,
                     inventory_pin, entries, tool):
    require(type(references) is list and len(references) <= MAX_CAPTURES, "invalid capture list")
    captured = {}
    for capture_ref in references:
        reference(capture_ref, MAX_RECORD)
        capture_path = PurePosixPath(capture_ref["path"])
        require(capture_path.name == "receipt.json", "capture must select its original receipt.json")
        receipt = inputs.document(capture_ref, MAX_RECORD, partition + " capture")
        closed(receipt, ("schema_version", "operation", "image", "tool", "created_at_utc",
                         "inventory_sha256", "inventory_receipt_sha256", "files", "total_bytes",
                         "image_mounted", "symlinks_followed", "firmware_executed", "origin_verified"),
               "EROFS capture receipt")
        require(type(receipt["schema_version"]) is int and receipt["schema_version"] == 1
                and receipt["operation"] == "erofs-capture", "wrong capture operation")
        require(all(receipt[key] is False for key in
                    ("image_mounted", "symlinks_followed", "firmware_executed", "origin_verified")),
                "capture scope differs from the original read-only capture")
        timestamp(receipt["created_at_utc"])
        require(image_identity(receipt["image"]) == selected_image
                and receipt["inventory_sha256"] == inventory_pin["sha256"]
                and receipt["inventory_receipt_sha256"] == scan_pin["sha256"]
                and tool_identity(receipt["tool"]) == tool,
                "capture image, scan, inventory or producer identity differs")
        files = receipt["files"]
        require(type(files) is list and 1 <= len(files) <= erofs.MAX_CAPTURE_PATHS,
                "capture files must be a nonempty bounded list")
        total = 0
        for index, row in enumerate(files, 1):
            closed(row, ("path", "nid", "size_bytes", "type", "uid", "gid", "mode",
                         "output_path", "sha256", "readback_verified"), "captured file")
            path = erofs._path(row["path"])
            require(path not in captured, "duplicate captured image path")
            require(path in entries and entries[path]["type"] == row["type"] == "regular"
                    and integer(row["nid"], 2**64 - 1, "capture inode") == entries[path]["nid"],
                    "capture is not the inventoried regular inode")
            integer(row["uid"], 2**32 - 1, "capture uid")
            integer(row["gid"], 2**32 - 1, "capture gid")
            # dump.erofs records permission bits (for example 0644), not
            # st_mode. File type was checked independently against the scan.
            require(type(row["mode"]) is str and re.fullmatch(r"[0-7]{4,6}", row["mode"])
                    and int(row["mode"], 8) <= 0o7777, "invalid capture permission mode")
            require(row["readback_verified"] is True
                    and row["output_path"] == f"files/{index:04d}",
                    "capture lacks its exact original output/readback binding")
            expected = pin({key: row[key] for key in ("sha256", "size_bytes")}, erofs.MAX_FILE_BYTES,
                           nonempty=path.lower().endswith(".apk"))
            total += expected["size_bytes"]
            require(total <= erofs.MAX_CAPTURE_BYTES, "capture byte limit exceeded")
            payload = {"path": str(capture_path.parent / row["output_path"]), **expected}
            inputs.read(payload, erofs.MAX_FILE_BYTES, partition + " payload " + path, payload=True)
            captured[path] = {"payload": payload, "capture_receipt": capture_ref,
                              "nid": row["nid"], "uid": row["uid"], "gid": row["gid"], "mode": row["mode"]}
        require(integer(receipt["total_bytes"], erofs.MAX_CAPTURE_BYTES, "capture total") == total,
                "capture total_bytes differs from all captured records")
    return captured


def _join(request, inputs):
    closed(request, ("schema_version", "operation", "context", "package_binding", "graph",
                     "partitions"), "projection request")
    require(type(request["schema_version"]) is int and request["schema_version"] == 1
            and request["operation"] == OPERATION, "wrong projection operation")
    require(metadata.encoded(request["context"]) == metadata.encoded(CONTEXT),
            "only the Nezha bka/bp4a user 4 KiB context is supported")
    require(request["package_binding"] is None, "actual package admission is not implemented by this preparation")
    closed(request["graph"], ("selected_platform_install_paths", "source_records"), "graph selection")
    selected = request["graph"]["selected_platform_install_paths"]
    require(type(selected) is list and 1 <= len(selected) <= MAX_APKS, "nonempty platform graph scope required")
    for path in selected:
        recorded_path(path)
        metadata.relative(path[1:])
        partition = PurePosixPath(path).parts[1]
        require(partition in PLATFORM and path.endswith(".apk") and included(partition, path),
                "graph path is outside the platform app/priv-app scope")
    require(len(set(selected)) == len(selected), "duplicate graph-selected install path")
    graph_records = request["graph"]["source_records"]
    require(type(graph_records) is list and 1 <= len(graph_records) <= 32,
            "raw graph/source records must be supplied separately from the projected vector")
    for row in graph_records:
        inputs.read(row, MAX_GRAPH_SOURCE, "raw graph/source evidence")
    closed(request["partitions"], PARTITIONS, "all eight logical partition inventories")
    rows, summaries, actual_platform, common_tool = [], {}, set(), None
    for partition in PARTITIONS:
        choice = request["partitions"][partition]
        closed(choice, ("image", "image_root", "inventory", "scan_receipt", "captures", "exclusions"),
               partition + " selection")
        image = pin(choice["image"], MAX_IMAGE)
        image_root = choice["image_root"]
        require(image_root in (("/", "/system") if partition == "system" else ("/",)),
                "unsupported explicit image-root mapping")
        inventory_ref, scan_ref = choice["inventory"], choice["scan_receipt"]
        reference(inventory_ref, erofs.MAX_INVENTORY_BYTES)
        reference(scan_ref, MAX_RECORD)
        inventory_path, scan_path = PurePosixPath(inventory_ref["path"]), PurePosixPath(scan_ref["path"])
        require(inventory_path.name == "inventory.json" and scan_path.name == "receipt.json"
                and inventory_path.parent == scan_path.parent, "original adjacent EROFS scan files required")
        inventory = inputs.document(inventory_ref, erofs.MAX_INVENTORY_BYTES, partition + " inventory")
        scan = inputs.document(scan_ref, MAX_RECORD, partition + " scan")
        inventory_pin, scan_pin = metadata.expected(inventory_ref, erofs.MAX_INVENTORY_BYTES), metadata.expected(scan_ref, MAX_RECORD)
        entries, tool = inventory_entries(inventory, scan, image, inventory_pin)
        require(common_tool is None or tool == common_tool, "mixed EROFS producer identities")
        common_tool = tool
        require(entries.get(image_root, {}).get("type") == "directory", "selected image root is absent")
        captured = capture_payloads(inputs, partition, choice["captures"], image, scan_pin,
                                    inventory_pin, entries, tool)
        apk_entries = {path: entry for path, entry in entries.items() if path.lower().endswith(".apk")}
        require(len(rows) + len(apk_entries) <= MAX_APKS, "APK inventory bound exceeded")
        if partition in FACTORY_APPS:
            require(set(apk_entries) == set(FACTORY_APPS[partition]) | set(FACTORY_OVERLAYS[partition]),
                    "retained factory APK paths changed or are incomplete: " + partition)
        exclusions = choice["exclusions"]
        require(type(exclusions) is list and len(exclusions) <= MAX_APKS, "invalid explicit exclusions")
        excluded = {}
        for exclusion in exclusions:
            closed(exclusion, ("image_path", "reason"), "APK exclusion")
            path = erofs._path(exclusion["image_path"])
            require(path not in excluded and path in apk_entries, "duplicate or nonexistent APK exclusion")
            excluded[path] = exclusion["reason"]
        used_exclusions, count = set(), 0
        for image_path, entry in sorted(apk_entries.items()):
            require(entry["type"] == "regular" and image_path in captured,
                    "every APK, including exclusions, requires a captured regular payload")
            runtime = runtime_path(partition, image_root, image_path)
            native = included(partition, runtime)
            if native:
                require(image_path not in excluded, "in-scope APK cannot be excluded")
                count += 1
                if partition in PLATFORM:
                    actual_platform.add(runtime)
            else:
                require(image_path in excluded and excluded[image_path] == exclusion_reason(partition, runtime),
                        "every out-of-scope APK needs its exact explicit exclusion reason")
                used_exclusions.add(image_path)
            row = {"partition": partition, "image": image, "image_root": image_root,
                   "image_path": image_path, "runtime_install_path": runtime,
                   "apk_basename": PurePosixPath(image_path).name, **captured[image_path],
                   "selected_native_scope": native, "exclusion_reason": excluded.get(image_path),
                   "selection_basis": "supplied-platform-graph-vector" if partition in PLATFORM
                                      else "retained-factory-path-set" if partition in FACTORY_APPS
                                      else "outside-native-checker-partitions",
                   "planned_native_path": NATIVE_ROOT + runtime if native else None}
            rows.append(row)
        require(set(excluded) == used_exclusions, "unused or conflicting APK exclusions")
        summaries[partition] = {"image": image, "image_root": image_root,
                                "inventory": inventory_ref, "scan_receipt": scan_ref,
                                "captures": choice["captures"], "inventory_entries": len(entries),
                                "apk_entries": len(apk_entries), "native_scope_apks": count,
                                "excluded_apks": len(excluded), "captured_files_rehashed": len(captured)}
    require(actual_platform == set(selected),
            "graph-selected platform paths and complete supplied image APK scope differ")
    require(len({row["runtime_install_path"] for row in rows}) == len(rows), "runtime APK mapping collision")
    rows.sort(key=lambda row: row["runtime_install_path"])
    basenames = defaultdict(list)
    for row in rows:
        basenames[row["apk_basename"]].append(row["runtime_install_path"])
    native_lists = {"platform": [], "vendor": []}
    for row in rows:
        if row["selected_native_scope"]:
            native_lists["platform" if row["partition"] in PLATFORM else "vendor"].append(row["planned_native_path"])
    return {"schema_version": 1, "operation": OPERATION,
            "status": "supplied-record-and-payload-join-only", "context": dict(CONTEXT),
            "package_binding": None, "graph_source_records": graph_records,
            "graph_selected_platform_install_paths": sorted(selected), "partitions": summaries,
            "apks": rows, "apk_count": len(rows), "planned_native_lists": native_lists,
            "basename_collisions": {name: paths for name, paths in sorted(basenames.items()) if len(paths) > 1},
            "package_name_collisions": None,
            "missing_admission_roles": ["actual-successful-package2-and-source-binding",
                "current-graph-selection-provenance", "native-scan-and-capture-provenance",
                "final-image-identity-and-payload-derivation", "apex-contained-apk-accounting",
                "aapt2-package-name-evidence", "basename-preserving-read-only-native-projection",
                "current-policy-context-tool-bindings-and-native-treble-execution",
                "signature-privilege-and-effective-mac-seapp-validation"],
            "scope": {**dict.fromkeys(FALSE_SCOPE, False),
                      "all_eight_supplied_inventory_structures_checked": True,
                      "every_inventoried_apk_payload_rehashed": True,
                      "supplied_platform_selection_set_joined": True,
                      "retained_factory_19_paths_accounted": True}}


def project(request_path, *, expected_sha256, input_root):
    """Read a confined request/evidence bundle and return the scoped projection.

    The request's graph vector is supplied data, not an authenticated Ninja
    result. This function reads only the explicitly selected local records and
    extracted payloads, invokes no tools and writes no files. It does not open
    recorded image/tool paths. Callers retain stdout privately.
    """
    require(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
            "external request SHA256 required")
    inputs = _Inputs(input_root)
    name = metadata.relative(str(request_path))
    path = inputs.root / name
    raw = inputs.reader.read(path, maximum=MAX_REQUEST)
    request_pin = metadata.identity(raw)
    require(request_pin["sha256"] == expected_sha256, "request SHA256 differs")
    inputs.roles[path] = "request"
    inputs.inodes[inputs.reader.bindings[path][1][:2]] = path
    inputs.metadata_bytes = len(raw)
    result = _join(metadata._json(raw), inputs)
    inputs.reader.recheck()
    result["request"] = {"path": name, **request_pin}
    result["input_records_and_payloads_unchanged"] = True
    result["metadata_bytes_rehashed"] = inputs.metadata_bytes
    result["payload_bytes_rehashed"] = inputs.payload_bytes
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="request path relative to --input-root")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--input-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = project(args.request, expected_sha256=args.expected_sha256, input_root=args.input_root)
        print(metadata.encoded(result).decode("utf-8"), end="")
        return 0
    except (ProjectionError, metadata.TargetFilesMetadataError, erofs.InventoryError,
            OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(1, "APK projection refused: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
