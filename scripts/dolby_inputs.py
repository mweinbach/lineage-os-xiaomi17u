#!/usr/bin/env python3
"""Verify the exact private Dolby research inputs; never contact a device."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

if __package__:
    from .camera_apk_inputs import Reader, identity, metadata, relative, require
else:
    from camera_apk_inputs import Reader, identity, metadata, relative, require

CONTRACT = Path(__file__).resolve().parents[1] / "config/nezha-dolby.json"


def capture_files(reader, root, contract):
    files = {}
    for group, pin in contract["captures"].items():
        base = Path(root) / relative(group)
        receipt = metadata(reader.read(base / "receipt.json"))
        require(receipt["operation"] == "erofs-capture"
                and receipt["image"]["sha256"] == pin["image_sha256"]
                and receipt["image_mounted"] is False
                and receipt["firmware_executed"] is False
                and receipt["symlinks_followed"] is False,
                "not the selected non-executing stock capture")
        rows = receipt["files"]
        require(len(rows) == len(pin["files"])
                and {r["path"] for r in rows} == set(pin["files"]), "capture path mismatch")
        seen = set()
        for row in rows:
            name = relative(row["output_path"])
            require(name.startswith("files/") and name not in seen, "ambiguous capture output")
            seen.add(name)
            expected = pin["files"][row["path"]]
            require(row["readback_verified"] is True and row["type"] == "regular"
                    and {k: row[k] for k in expected} == expected, "capture identity mismatch")
            files[group + row["path"]] = reader.read(base / name, expected, 32 * 1024**2)
    return files


def verify(root):
    reader = Reader()
    contract_raw = reader.read(CONTRACT)
    contract = metadata(contract_raw)
    files = capture_files(reader, root, contract)
    effects = ET.fromstring(files["vendor/etc/audio/sku_canoe/audio_effects_config.xml"])
    ns = {"a": "http://schemas.android.com/audio/audio_effects_conf/v2_0"}
    dap = effects.findall("./a:effects/a:effect[@name='dap_hw']", ns)
    require(len(dap) == 1 and dap[0].get("uuid") == contract["control_interface"]["effect_implementation_uuid"]
            and dap[0].get("library") == "dap_hw", "Dolby effect mapping differs")
    libraries = effects.findall("./a:libraries/a:library[@name='dap_hw']", ns)
    require(len(libraries) == 1 and libraries[0].get("path") == "libhwdapaidl.so", "Dolby library differs")
    defaults = ET.fromstring(files["vendor/etc/dolby/dax-default.xml"])
    profiles = defaults.findall(".//profile")
    require(len(profiles) == len(contract["profiles"])
            and {p.get("id"): p.get("name") for p in profiles} == contract["profiles"], "profile map differs")
    reader.recheck()
    return {"contract": identity(contract_raw), "verified_files": len(files),
            "captured_input_bytes_verified": True, "effective_audio_loader_verified": False,
            "controller_native_build_verified": False, "hardware_verified": False,
            "profiles": contract["profiles"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.capture_root), indent=2, sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, ET.ParseError) as exc:
        parser.exit(1, f"Dolby input verification failed: {exc}\n")


if __name__ == "__main__":
    main()
