"""Exact source projection for the reviewed Nezha device framework matrix.

This module reads inert XML and JSON only. It never edits factory inputs, runs
Android tools, changes a numbered platform FCM, or establishes runtime support.
The device generator supplies its bounded no-symlink reader for private inputs.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import PurePosixPath
import re
import xml.etree.ElementTree as ET


CONTRACT_PATH = "config/nezha-framework-matrix.json"
CONTRACT_ID = "nezha-exact-factory-framework-matrix-v1"
CONTRACT_SHA256 = "0300ab7fc9896bb85583d2a400959c91788dc79446bbe5c3219fc35dd2b5f56e"
SOURCE_PATH = "device/xiaomi/nezha/generated/framework-compatibility-matrix.xml"
SELECTOR = "DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE"
MODULE = "framework_compatibility_matrix.device.xml"
INSTALLED_PATH = "system/etc/vintf/compatibility_matrix.device.xml"
SCOPE = {
    "source_projection_only": True,
    "original_proprietary_inputs_changed": False,
    "numbered_platform_matrices_changed": False,
    "normal_android_selinux_enforcing": True,
    "native_matrix_built": False,
    "full_vintf_compatibility_verified": False,
    "runtime_services_verified": False,
    "hardware_tested": False,
    "complete_rom_admitted": False,
    "phone_operations": [],
}
_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)+")
_INTERFACE = re.compile(r"I[A-Za-z_0-9]+")
_INSTANCE = re.compile(r"[A-Za-z_0-9]+(?:[/-][A-Za-z_0-9]+)*")
_DIGEST = re.compile(r"[0-9a-f]{64}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def tuple_key(row):
    return row["name"], row["version"], row["interface"], row["instance"]


def _relative(value):
    require(type(value) is str and value != "" and "\\" not in value,
            "matrix input path is malformed")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in (".", "..") for part in path.parts),
            "matrix input path must be canonical and relative")
    return path


def _file_identity(row):
    _relative(row["path"])
    require(type(row["sha256"]) is str and _DIGEST.fullmatch(row["sha256"]) and
            type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= 16 * 1024 * 1024,
            "matrix input identity is malformed")


def validate_contract(contract, actual_identity):
    require(actual_identity["sha256"] == CONTRACT_SHA256,
            "unknown or changed framework matrix contract")
    require(contract["schema_version"] == 1 and contract["contract_id"] == CONTRACT_ID and
            contract["device"] == "nezha" and contract["profile"] == "framework-checks" and
            contract["platform"] == {"branch": "bka", "release_config": "bp4a",
                                     "shipping_api_level": 36, "target_fcm_level": 202504},
            "framework matrix target or platform differs")
    require(contract["selection"] == {"variable": SELECTOR, "source_path": SOURCE_PATH,
                                      "module": MODULE, "installed_path": INSTALLED_PATH,
                                      "matrix_version": "9.0", "matrix_type": "framework",
                                      "level": None},
            "framework matrix producer or selection differs")
    require(contract["scope"] == SCOPE and contract["source_patches"] == [],
            "framework matrix cannot promote native success or patch upstream checks")
    files = contract["factory_xml_inputs"]
    require(type(files) is list and files and
            len({row["path"] for row in files}) == len(files),
            "factory matrix inputs are absent or duplicated")
    for row in files:
        _file_identity(row)
        require(row["kind"] in ("device_manifest", "framework_matrix") and
                row["runtime_path"].startswith(("/system/", "/product/", "/vendor/", "/odm/")),
                "factory matrix input role differs")
    entries = contract["entries"]
    require(type(entries) is list and len(entries) == 155 and
            [tuple_key(row) for row in entries] == sorted({tuple_key(row) for row in entries}),
            "framework matrix entries are missing, duplicated or unsorted")
    for row in entries:
        require(type(row["name"]) is str and _NAME.fullmatch(row["name"]) and
                type(row["interface"]) is str and _INTERFACE.fullmatch(row["interface"]) and
                type(row["instance"]) is str and _INSTANCE.fullmatch(row["instance"]) and
                type(row["version"]) is int and 1 <= row["version"] <= 100,
                "framework matrix must contain exact AIDL names, versions and instances")
        for role, expected_kind in (("manifest_inputs", "device_manifest"),
                                    ("matrix_inputs", "framework_matrix")):
            indexes = row[role]
            require(type(indexes) is list and indexes and indexes == sorted(set(indexes)) and
                    all(type(index) is int and 0 <= index < len(files) and
                        files[index]["kind"] == expected_kind for index in indexes),
                    "framework matrix entry lacks exact original XML evidence")
    for row in (contract["source_lock"], contract["source_snapshot"],
                *contract["source_preconditions"], *contract["evidence_records"]):
        _file_identity(row)
    for row in contract["source_preconditions"]:
        _relative(row["captured_path"])
        require(row["project"] in contract["required_source_revisions"] and
                row["path"].startswith(row["project"] + "/"),
                "framework matrix source precondition has the wrong project")
    return contract


def _xml(raw, root_tag, kind):
    require(len(raw) <= 1024 * 1024 and b"<!DOCTYPE" not in raw.upper() and
            b"<!ENTITY" not in raw.upper(), "matrix XML exceeds limits or contains a DTD")
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, ValueError) as exc:
        raise ValueError("invalid original matrix XML") from exc
    require(root.tag == root_tag and root.get("type") == kind,
            "original matrix XML has the wrong direction")
    return root


def _aidl_supports(root, row, *, matrix):
    for hal in root.findall("hal"):
        if hal.get("format", "hidl") != "aidl" or hal.findtext("name") != row["name"]:
            continue
        versions = [node.text for node in hal.findall("version")] or ["1"]
        matches_version = False
        for version in versions:
            match = re.fullmatch(r"([1-9][0-9]*)(?:-([1-9][0-9]*))?", version or "")
            require(match is not None and (matrix or match[2] is None),
                    "unsupported original AIDL version declaration")
            minimum, maximum = int(match[1]), int(match[2] or match[1])
            require(minimum <= maximum, "reversed original AIDL version range")
            matches_version |= minimum <= row["version"] <= maximum
        if not matches_version:
            continue
        expected = row["interface"] + "/" + row["instance"]
        if expected in [node.text for node in hal.findall("fqname")]:
            return True
        for interface in hal.findall("interface"):
            if interface.findtext("name") == row["interface"] and row["instance"] in [
                    node.text for node in interface.findall("instance")]:
                return True
    # No regex matching is performed, even when the original has regex-instance.
    # The authored projection needs an original exact instance on both sides.
    return False


def verify_inputs(contract, reader):
    """Reopen every pinned evidence file and verify the exact tuple derivation.

    ``reader(path)`` must return bounded bytes from a regular, no-symlink file.
    Only the caller chooses the private workspace root. No output is written.
    """
    records = {}
    for row in (contract["source_lock"], contract["source_snapshot"],
                *contract["evidence_records"]):
        raw = reader(row["path"])
        require(identity(raw) == {key: row[key] for key in ("sha256", "size_bytes")},
                "framework matrix evidence or source lock changed: " + row["path"])
        records[row["path"]] = raw
    for row in contract["source_preconditions"]:
        require(identity(reader(row["captured_path"])) == {key: row[key] for key in ("sha256", "size_bytes")},
                "captured matrix source precondition changed: " + row["path"])
    xml_roots = []
    for row in contract["factory_xml_inputs"]:
        raw = reader(row["path"])
        require(identity(raw) == {key: row[key] for key in ("sha256", "size_bytes")},
                "original framework matrix or device manifest changed: " + row["path"])
        matrix = row["kind"] == "framework_matrix"
        xml_roots.append(_xml(raw, "compatibility-matrix" if matrix else "manifest",
                              "framework" if matrix else "device"))
        partition = contract["factory_partitions"][row["partition"]]
        require(row["capture_receipt"] == partition["capture_receipt"]["path"],
                "original matrix input has a different partition receipt")
        receipt = json.loads(records[row["capture_receipt"]])
        members = [member for member in receipt["files"] if member["output_path"] == row["capture_output_path"]]
        require(len(members) == 1, "original matrix input lacks an unambiguous capture member")
        member = members[0]
        require(member["path"] == row["image_path"] and member["nid"] == row["nid"] and
                member["type"] == "regular" and member["readback_verified"] is True and
                all(member[key] == row[key] for key in ("sha256", "size_bytes")),
                "original matrix capture member differs")
        require(receipt["image"]["sha256"] == partition["image"]["sha256"] and
                receipt["inventory_sha256"] == partition["inventory"]["sha256"] and
                receipt["inventory_receipt_sha256"] == partition["inventory_receipt"]["sha256"],
                "original matrix capture image or inventory link differs")
        inventory = json.loads(records[partition["inventory"]["path"]])
        members = [member for member in inventory["entries"] if member["path"] == row["image_path"]]
        require(members == [{"nid": row["nid"], "path": row["image_path"], "type": "regular"}],
                "original matrix input is not its recorded regular inventory inode")
    for row in contract["entries"]:
        require(all(_aidl_supports(xml_roots[index], row, matrix=False)
                    for index in row["manifest_inputs"]),
                "matrix tuple is not declared in its original device manifest")
        require(all(_aidl_supports(xml_roots[index], row, matrix=True)
                    for index in row["matrix_inputs"]),
                "matrix tuple is not supported by its original framework matrix")
    return {"factory_xml_inputs": len(xml_roots), "exact_aidl_tuples": len(contract["entries"])}


def render(contract):
    """Render exact AIDL declarations, without regex, version ranges or optional."""
    root = ET.Element("compatibility-matrix", {"version": "9.0", "type": "framework"})
    grouped = {}
    for row in contract["entries"]:
        grouped.setdefault((row["name"], row["version"]), {}).setdefault(row["interface"], []).append(row["instance"])
    for (name, version), interfaces in sorted(grouped.items()):
        hal = ET.SubElement(root, "hal", {"format": "aidl"})
        ET.SubElement(hal, "name").text = name
        ET.SubElement(hal, "version").text = str(version)
        for interface_name, instances in sorted(interfaces.items()):
            interface = ET.SubElement(hal, "interface")
            ET.SubElement(interface, "name").text = interface_name
            for instance in sorted(instances):
                ET.SubElement(interface, "instance").text = instance
    ET.indent(root, space="    ")
    return ("<!-- Authored exact Nezha projection; original input hashes are in " + CONTRACT_PATH +
            ". Native compatibility and runtime support require separate evidence. -->\n" +
            ET.tostring(root, encoding="unicode", short_empty_elements=False) + "\n").encode("ascii")


def wiring_lines():
    return [
        "# Exact stock-backed AIDL declarations; native compatibility remains a separate check.",
        "ifneq ($(filter command line environment override,$(origin DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE) $(origin DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE)),)",
        "$(error Nezha framework matrix selector cannot come from command-line or environment overrides)",
        "endif",
        "ifneq ($(strip $(DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE) $(DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE)),)",
        "$(error Nezha framework matrix capability requires no other device or product matrix selector)",
        "endif",
        f"{SELECTOR} := {SOURCE_PATH}",
        "DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE :=",
        ".KATI_READONLY := DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE",
    ]


def admission(plan, contract, contract_identity):
    require(plan["profile"] == "framework-checks" and plan["product"] == "lineage_nezha" and
            plan["release_config"] == "bp4a" and plan["shipping_api_level"] == 36 and
            plan["admission"]["configuration_allowed"] is True and
            all(value is False for key, value in plan["admission"].items() if key != "configuration_allowed"),
            "framework matrix cannot change the target or ROM admission")
    require(plan.get("factory_profile", {}).get("package_sha256") == contract["factory_package"]["sha256"] and
            plan["source_packages"]["vendor"] == contract["factory_package"]["sha256"],
            "framework matrix requires its exact original factory vendor profile")
    return {"contract_record": {"path": CONTRACT_PATH, **contract_identity},
            "generated_source": {"path": SOURCE_PATH, **identity(render(contract))},
            **{key: copy.deepcopy(contract[key]) for key in (
                "contract_id", "platform", "selection", "source_lock", "source_snapshot",
                "required_source_revisions", "source_preconditions", "required_native_checks", "scope")}}
