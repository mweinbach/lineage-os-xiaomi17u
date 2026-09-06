#!/usr/bin/env python3
"""Verify retained Nezha haptics calibration without modifying it or a phone."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

if __package__:
    from .camera_apk_inputs import Reader, metadata
else:
    from camera_apk_inputs import Reader, metadata

VENDOR_HASH = "c9c2a03b61cd7c96466f09ffebf723382f430fd1389b1b73186270f3e15dfb20"
CALIBRATION = {
    "/etc/HapticsPolicy.xml": {
        "output_path": "files/0001", "size_bytes": 3975,
        "sha256": "45be7db06467a3eae8823eb189571fa1e9a4fa20d06eec47db7a8e265d1c5e33",
    },
    "/etc/Hapticsconfig.xml": {
        "output_path": "files/0002", "size_bytes": 21375,
        "sha256": "27be444399dddad40cea831245026cc8018fe696d92f0742b8d905de205fca2a",
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(policy, config):
    policy_root, config_root = ET.fromstring(policy), ET.fromstring(config)
    require(policy_root.tag == "hapticsPolicyConfiguration", "wrong haptics policy root")
    require(config_root.tag == "haptics_param_values", "wrong haptics calibration root")
    effects = config_root.findall("predefined_effect/Hapticseffect")
    strengths = {}
    for effect in effects:
        identifier = effect.get("effect")
        require(identifier is not None and identifier not in strengths, "ambiguous effect identifier")
        values = {}
        for level in ("low", "mid", "high"):
            nodes = effect.findall(level + "_pulse_intensity")
            require(len(nodes) == 1, "missing or ambiguous effect strength")
            value = int(nodes[0].text)
            require(0 <= value <= 100, "effect strength out of range")
            values[level] = value
        strengths[identifier] = values
    require(strengths, "no predefined effect strength calibration")
    # Factory tables are not uniformly monotonic (DOUBLE_CLICK mid is 100,
    # high is 90). Report exact values; do not normalize or claim perception.
    return {
        "perform_open_loop_effects": policy_root.findtext("hapticsPerformAPI/effect_id"),
        "compose_open_loop": policy_root.findtext("hapticsComposeAPI/SupportCompose"),
        "predefined_effect_strengths": strengths,
        "all_strength_rows_monotonic": all(
            v["low"] <= v["mid"] <= v["high"] for v in strengths.values()),
    }


def verify_capture(capture):
    reader = Reader()
    capture = Path(capture)
    receipt = metadata(reader.read(capture / "receipt.json"))
    require(receipt.get("operation") == "erofs-capture"
            and receipt.get("image", {}).get("sha256") == VENDOR_HASH,
            "capture is not from the selected factory vendor image")
    require(all(receipt.get(key) is False for key in
                ("firmware_executed", "image_mounted", "symlinks_followed")),
            "capture does not attest offline regular-file inspection")
    files = {}
    for path, expected in CALIBRATION.items():
        records = [entry for entry in receipt.get("files", []) if entry.get("path") == path]
        require(len(records) == 1, "missing or duplicate calibration capture: " + path)
        entry = records[0]
        require(all(entry.get(key) == value for key, value in expected.items())
                and entry.get("type") == "regular" and entry.get("readback_verified") is True,
                "calibration capture identity mismatch: " + path)
        raw = reader.read(capture / expected["output_path"], maximum=expected["size_bytes"])
        require(len(raw) == expected["size_bytes"]
                and hashlib.sha256(raw).hexdigest() == expected["sha256"],
                "calibration bytes changed: " + path)
        files[path] = raw
    details = summarize(files["/etc/HapticsPolicy.xml"], files["/etc/Hapticsconfig.xml"])
    reader.recheck()
    return {"schema_version": 1, "factory_calibration_capture_verified": True,
            "vendor_image_sha256": VENDOR_HASH, "calibration": CALIBRATION,
            "details": details, "calibration_modified": False,
            "hardware_behavior_verified": False, "phone_accessed": False}


def verify_delivery(target_files):
    # Read only the two bounded, uniquely identified members. Do not extract
    # archives or trust filenames from an input receipt.
    with zipfile.ZipFile(target_files) as archive:
        for path, expected in CALIBRATION.items():
            name = "VENDOR" + path
            entries = [entry for entry in archive.infolist() if entry.filename == name]
            require(len(entries) == 1, "missing or duplicate delivered calibration: " + name)
            entry = entries[0]
            require(entry.file_size == expected["size_bytes"], "delivered calibration size mismatch")
            with archive.open(entry) as source:
                raw = source.read(expected["size_bytes"] + 1)
            require(len(raw) == expected["size_bytes"]
                    and hashlib.sha256(raw).hexdigest() == expected["sha256"],
                    "delivered calibration hash mismatch: " + name)
    return {"factory_calibration_target_files_verified": True,
            "calibration": CALIBRATION, "compiled_controls_verified": False,
            "complete_hal_delivery_verified": False, "hardware_behavior_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("verify-stock")
    capture.add_argument("--capture", required=True, type=Path)
    delivery = commands.add_parser("verify-delivery")
    delivery.add_argument("--target-files", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = (verify_capture(args.capture) if args.command == "verify-stock"
                  else verify_delivery(args.target_files))
    except (ValueError, OSError, ET.ParseError, zipfile.BadZipFile) as error:
        print("haptics-controls: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
