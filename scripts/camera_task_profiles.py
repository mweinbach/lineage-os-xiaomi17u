#!/usr/bin/env python3
"""Verify exact private camera scheduling inputs without executing firmware."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .camera_apk_inputs import Reader, identity, metadata, require
    from .dolby_inputs import capture_files
else:
    from camera_apk_inputs import Reader, identity, metadata, require
    from dolby_inputs import capture_files

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-camera-task-profiles.json"
CANDIDATE = ROOT / "device/xiaomi/nezha/camera-task-profiles/task_profiles_cameraopt.json"


def named(rows, name):
    found = [row for row in rows if row["Name"] == name]
    require(len(found) == 1, "missing or ambiguous profile " + name)
    return found[0]


def validate_mapping(factory, candidate, contract):
    aggregate = named(factory["AggregateProfiles"], "CAMERA_CAPTURE_SCHED")
    require(aggregate["Profiles"] == ["CameraProcessCapacityLevel6", "CameraPerformanceLevel2"],
            "OEM scheduling aggregate changed")
    actual = []
    for name in aggregate["Profiles"]:
        actions = named(factory["Profiles"], name)["Actions"]
        require(len(actions) == 1 and actions[0]["Name"] == "JoinCgroup", "OEM action changed")
        actual.append(actions[0]["Params"])
    require(actual == contract["oem_capture_actions"], "OEM cgroup targets changed")
    require(candidate == {"Profiles": [{"Name": "CAMERA_CAPTURE_SCHED", "Actions": [
        {"Name": "JoinCgroup", "Params": row} for row in contract["candidate_actions"]
    ]}]}, "candidate has extra, missing or different actions")
    require(contract["candidate_actions"] == [
        {"Controller": "cpuset", "Path": "camera-daemon"},
        {"Controller": "cpu", "Path": "camera-daemon"}], "unsupported compatibility targets")


def verify(capture_root):
    reader = Reader()
    raw = reader.read(CONTRACT)
    contract = metadata(raw)
    files = capture_files(reader, capture_root, contract)
    validate_mapping(metadata(files["system_ext/etc/task_profiles_cameraopt.json"]),
                     metadata(reader.read(CANDIDATE)), contract)
    loader = files["vendor/lib64/libprocessgroup.so"]
    require(b"/system_ext/etc/task_profiles_cameraopt.json\0" in loader,
            "vendor loader filename absent")
    require(b"CAMERA_CAPTURE_SCHED\0" in files["vendor/lib64/libcameraopt.so"],
            "OEM caller profile name absent")
    reader.recheck()
    return {"contract": identity(raw), "verified_files": len(files),
            "exact_factory_bytes_verified": True, "firmware_executed": False,
            "native_build_verified": False, "runtime_loader_verified": False,
            "hardware_verified": False,
            "scope": "Validates retained bytes and supported mapping, not measured scheduling behavior"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.capture_root), indent=2, sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, "Camera task-profile verification failed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
