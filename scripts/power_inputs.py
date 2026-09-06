#!/usr/bin/env python3
"""Reproduce exact-stock power deficiencies without enabling any power controls.

This audits retained local files. It neither contacts a phone nor emits a build
overlay: the factory framework profiles currently inspected are placeholders.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

if __package__:
    from .camera_apk_inputs import Reader, identity, metadata, relative, require
else:
    from camera_apk_inputs import Reader, identity, metadata, relative, require

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-power-evidence.json"
MAX_INPUT = 64 * 1024**2
MAX_DUMP = 2 * 1024**2


def decode_tree(text):
    """Parse the pinned aapt2 XML tree format, preserving element ownership."""
    require(len(text.encode()) <= MAX_DUMP, "XML tree output too large")
    stack, roots = [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        depth = len(line) - len(line.lstrip())
        value = line.strip()
        if value.startswith("N: "):
            continue
        if match := re.fullmatch(r"E: ([\w.-]+) \(line=\d+\)", value):
            while stack and stack[-1][0] >= depth:
                stack.pop()
            node = ET.Element(match[1])
            (stack[-1][1].append(node) if stack else roots.append(node))
            stack.append((depth, node))
        elif value.startswith("A: "):
            require(bool(stack) and depth > stack[-1][0], "orphan XML attribute")
            match = re.fullmatch(r'A: (.+?)(?:\(0x[0-9a-f]+\))?=(.+)', value)
            require(match is not None, "unsupported XML attribute")
            name, raw = match.groups()
            name = name.rsplit(":", 1)[-1]
            if raw.startswith('"'):
                raw_match = re.fullmatch(r'"([^"]*)"(?: \(Raw: "[^"]*"\))?', raw)
                require(raw_match is not None, "unsupported quoted XML attribute")
                raw = raw_match[1]
            require(name not in stack[-1][1].attrib, "duplicate XML attribute")
            stack[-1][1].set(name, raw)
        elif value.startswith("T: "):
            require(bool(stack) and depth > stack[-1][0], "orphan XML text")
            match = re.fullmatch(r"T: '([^']*)'", value)
            require(match is not None and stack[-1][1].text is None, "unsupported XML text")
            stack[-1][1].text = match[1]
        else:
            raise ValueError("unsupported aapt2 tree line")
    require(len(roots) == 1, "one XML root required")
    return roots[0]


def profile_findings(root):
    require(root.tag == "device", "power profile must have a device root")
    values = {}
    for node in root:
        if node.tag not in {"item", "array"}:
            continue  # Modem records are not needed for the placeholder test.
        name = node.get("name")
        require(name and name not in values, "missing or duplicate power component")
        source = [node] if node.tag == "item" else list(node)
        require(node.tag != "array" or all(n.tag == "value" for n in source), "malformed power array")
        numbers = [float(n.text or "") for n in source]
        require(all(math.isfinite(n) and n >= 0 for n in numbers), "invalid power coefficient")
        values[name] = numbers
    placeholder = (values.get("battery.capacity") == [1000.0]
                   and values.get("cpu.clusters.cores") == [1.0]
                   and values.get("cpu.speeds.cluster0") == [400000.0]
                   and values.get("screen.on.display0") == [0.1])
    return {"placeholder_detected": placeholder,
            "battery_capacity_mah": values.get("battery.capacity"),
            "cpu_cluster_cores": values.get("cpu.clusters.cores"),
            "cpu_cluster0_frequencies_khz": values.get("cpu.speeds.cluster0"),
            "screen_on_ma": values.get("screen.on.display0"),
            "calibrated_nezha_profile_admitted": False}


def wlc_findings(seapp, contexts, manifest):
    package = "com.qualcomm.qti.workloadclassifier"
    rows = [dict(field.split("=", 1) for field in line.split())
            for line in seapp.splitlines() if line and not line.startswith("#")]
    matches = [row for row in rows if row.get("domain") == "vendor_wlc_app"]
    require(len(matches) == 1 and matches[0].get("name") == package,
            "WLC package/domain evidence differs")
    require(manifest.tag == "manifest" and manifest.get("package") == package,
            "WLC manifest package differs")
    private = sorted(line.split()[0] for line in contexts.splitlines()
                     if line.strip() and not line.lstrip().startswith("#")
                     and len(line.split()) >= 2 and line.split()[1] == "u:object_r:vendor_wlc_prop:s0")
    require(private == ["persist.vendor.build.date.utc", "vendor.perf.workloadclassifier.enable"],
            "private WLC property contract differs")
    return {"package": package, "domain": "vendor_wlc_app",
            "meaning": "Qualcomm workload classifier", "private_properties": private,
            "wireless_or_reverse_charging_support_inferred": False,
            "restoration_admitted": False}


def capture_files(reader, capture_root, contract):
    """Validate each receipt, exact runtime selection, and every retained byte."""
    result = {}
    for group, expected in contract["captures"].items():
        root = Path(capture_root) / group
        receipt = metadata(reader.read(root / "receipt.json"))
        require(receipt["operation"] == "erofs-capture"
                and receipt["image"]["sha256"] == contract["system_ext_image_sha256"]
                and receipt["image_mounted"] is False and receipt["firmware_executed"] is False,
                "capture is not the selected non-executing stock readback")
        rows = receipt["files"]
        require(len(rows) == len(expected) and {row["path"] for row in rows} == set(expected),
                "missing, repeated, or unexpected capture path")
        output_names = set()
        for row in rows:
            name = relative(row["output_path"])
            require(name.startswith("files/") and name not in output_names, "ambiguous capture output path")
            output_names.add(name)
            pin = expected[row["path"]]
            require(row["readback_verified"] is True and row["type"] == "regular"
                    and {k: row[k] for k in pin} == pin, "capture identity differs")
            path = root / name
            result[row["path"]] = (path, reader.read(path, pin, MAX_INPUT))
    return result


def audit(framework_apk, capture_root, aapt2):
    reader = Reader()
    contract_raw = reader.read(CONTRACT)
    contract = metadata(contract_raw)
    raw = reader.read(framework_apk, contract["framework"], MAX_INPUT)
    files = capture_files(reader, capture_root, contract)
    tool = Path(aapt2).resolve(strict=True)
    tool_raw = reader.read(tool, maximum=MAX_INPUT)
    require(identity(tool_raw)["sha256"] == contract["aapt2_sha256"], "aapt2 does not match pinned decoder")
    dumps = {}

    def decode(path, member, label):
        completed = subprocess.run([str(tool), "dump", "xmltree", str(path), "--file", member],
                                   stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
                                   env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        require(completed.returncode == 0 and not completed.stderr, "aapt2 decoding failed")
        require(len(completed.stdout) <= MAX_DUMP, "aapt2 output too large")
        dumps[label + ":" + member] = identity(completed.stdout)
        return decode_tree(completed.stdout.decode())

    profiles = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for member, digest in contract["framework"]["members"].items():
            entries = [entry for entry in archive.infolist() if entry.filename == member]
            require(len(entries) == 1 and entries[0].file_size <= MAX_DUMP, "ambiguous or oversized profile member")
            require(hashlib.sha256(archive.read(member)).hexdigest() == digest, "profile member hash differs")
            profiles[member] = profile_findings(decode(framework_apk, member, "framework"))
            require(profiles[member]["placeholder_detected"], "pinned placeholder profile evidence changed")
    keeper = decode(files["/app/PowerKeeper/PowerKeeper.apk"][0], "AndroidManifest.xml", "PowerKeeper")
    require(keeper.get("package") == "com.miui.powerkeeper" and keeper.get("sharedUserId") == "android.uid.system",
            "PowerKeeper shared UID evidence differs")
    wlc = wlc_findings(files["/etc/selinux/system_ext_seapp_contexts"][1].decode(),
                       files["/etc/selinux/system_ext_property_contexts"][1].decode(),
                       decode(files["/app/workloadclassifier/workloadclassifier.apk"][0], "AndroidManifest.xml", "workloadclassifier"))
    sysconfig = ET.fromstring(files["/etc/sysconfig/power-save-conf.xml"][1])
    require(sysconfig.tag == "permissions" and all(n.tag == "allow-in-power-save" for n in sysconfig),
            "unexpected power-save sysconfig contract")
    reader.recheck()
    return {"schema_version": 1, "device": "nezha", "evidence_verified": True,
            "contract": identity(contract_raw), "profiles": profiles,
            "wlc": wlc,
            "powerkeeper": {"package": keeper.get("package"), "shared_uid": keeper.get("sharedUserId"),
                            "platform_shared_uid_signer_review_required": True, "restoration_admitted": False},
            "power_save_exemptions": sorted(n.get("package") for n in sysconfig),
            "power_save_exemptions_imported": False,
            "product_changes_admitted": False, "hardware_qualified": False,
            "decoder_outputs": dumps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework-apk", required=True, type=Path)
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--aapt2", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.framework_apk, args.capture_root, args.aapt2)
    except (OSError, ValueError, subprocess.TimeoutExpired, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
