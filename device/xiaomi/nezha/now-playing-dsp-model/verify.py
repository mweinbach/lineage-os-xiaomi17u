#!/usr/bin/env python3
"""Offline Make admission for the Now Playing DSP music-detector model bundle.

Every file the contract names must exist in the bundle as a bounded regular file with the
exact size and SHA-256 the contract pins. No device access, subprocesses or writes. A hash
mismatch rejects unreviewed blob drift; the build refuses rather than copies a surprise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat

TOKEN = "verified-now-playing-dsp-model"
MAX_BYTES = 4 * 1024 * 1024


def read_regular(path: Path) -> bytes:
    path = path.absolute()
    for parent in path.parents:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError("symlink or non-directory bundle ancestor: " + str(parent))
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
        raise ValueError("bundle member must be a bounded regular file: " + path.name)
    raw = path.read_bytes()
    if before != path.lstat() or len(raw) != before.st_size:
        raise ValueError("bundle member changed during verification: " + path.name)
    return raw


def verify(bundle: Path, contract_path: Path) -> str:
    contract = json.loads(read_regular(contract_path))
    files = contract["files"]
    if not files:
        raise ValueError("contract names no files")
    for entry in files:
        name = entry["name"]
        if "/" in name or name in ("", ".", ".."):
            raise ValueError("contract file name must be a bare name: " + name)
        raw = read_regular(bundle / name)
        if len(raw) != entry["size_bytes"]:
            raise ValueError("size differs for " + name)
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("sha256 differs for " + name)
    return TOKEN


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="directory holding the model files")
    parser.add_argument("--contract", required=True, help="config/nezha-now-playing-dsp-model.json")
    args = parser.parse_args()
    try:
        print(verify(Path(args.bundle), Path(args.contract)))
        return 0
    except Exception as error:  # Make reads a single line; any failure is a refusal
        print("refused: " + str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
