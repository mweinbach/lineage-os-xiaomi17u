#!/usr/bin/env python3
"""Offline Make admission for the camera scheduling compatibility candidate.

No device access, subprocesses, writes, generated sysctls or policy changes.
Full input hashes deliberately reject unreviewed platform drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat

SOURCE_PINS = {
    "system/core/libprocessgroup/profiles/task_profiles.json": "31ca4240ca1aa71f745a048a9c68e0c060a92fe87dc7eafe48ea51f8633ee6b9",
    "system/core/libprocessgroup/profiles/cgroups.json": "ab2ed667ff45958843fb0c6ee953a5512def0ae87470c4358aa9576a6a4b2e22",
    "system/core/rootdir/init.rc": "ab5c2219e622d9ab3753e73b74dfe2f71d87d1431d235cc029b538ccf6f9654d",
}
EXPECTED = {"Profiles": [{"Name": "CAMERA_CAPTURE_SCHED", "Actions": [
    {"Name": "JoinCgroup", "Params": {"Controller": "cpuset", "Path": "camera-daemon"}},
    {"Name": "JoinCgroup", "Params": {"Controller": "cpu", "Path": "camera-daemon"}},
]}]}


def read_regular(path):
    path = Path(path).absolute()
    for parent in path.parents:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError("symlink or non-directory source ancestor")
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > 1024 * 1024:
        raise ValueError("source must be a bounded regular file")
    raw = path.read_bytes()
    if before != path.lstat() or len(raw) != before.st_size:
        raise ValueError("source changed during verification")
    return raw


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def verify(source_root, profile_path):
    for name, expected in SOURCE_PINS.items():
        if hashlib.sha256(read_regular(Path(source_root) / name)).hexdigest() != expected:
            raise ValueError("unreviewed camera scheduling source: " + name)
    candidate = json.loads(read_regular(profile_path), object_pairs_hook=unique)
    if candidate != EXPECTED:
        raise ValueError("camera scheduling candidate must contain exactly two supported cgroup joins")
    return "verified-camera-task-profiles"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--profile", type=Path,
                        default=Path(__file__).with_name("task_profiles_cameraopt.json"))
    args = parser.parse_args()
    try:
        print(verify(args.source_root, args.profile))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
