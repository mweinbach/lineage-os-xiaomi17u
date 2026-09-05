"""Stage the pinned, Nezha-only Aperture camera admission patch off-device."""
import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from .partition_build_props import _apply_patch
else:
    from partition_build_props import _apply_patch

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "patches/evolution/aperture-nezha-camera-admission.json"


def candidate(source):
    record = json.loads(CONTRACT.read_bytes())
    patch = (ROOT / record["patch"]).read_bytes()
    if hashlib.sha256(patch).hexdigest() != record["patch_sha256"]:
        raise ValueError("Aperture admission patch hash differs")
    parts = patch.split(b"diff --git ")
    if parts[0] or len(parts) != len(record["files"]) + 1:
        raise ValueError("Unexpected patch source count")
    result = {}
    for (path, identity), body in zip(record["files"].items(), parts[1:]):
        if not body.startswith(f"a/{path} b/{path}\n".encode()):
            raise ValueError("Unexpected patch file/order")
        original = Path(source) / path
        if identity["before_sha256"] is None:
            if original.exists():
                raise ValueError("New Nezha camera factory already exists")
            lines = body.splitlines(keepends=True)
            after = b"".join(line[1:] for line in lines if line.startswith(b"+")
                             and not line.startswith(b"+++"))
        else:
            before = original.read_bytes()
            if hashlib.sha256(before).hexdigest() != identity["before_sha256"]:
                raise ValueError("Aperture source differs: " + path)
            after = _apply_patch(before, b"diff --git " + body)
        if (hashlib.sha256(after).hexdigest() != identity["after_sha256"]
                or len(after) != identity["after_bytes"]):
            raise ValueError("Patched Aperture source differs: " + path)
        result[path] = after
    return result


def stage(source, output):
    files = candidate(source)
    output = Path(output)
    if output.exists():
        raise ValueError("Output exists; choose a new directory")
    output.mkdir(parents=True)
    for name, data in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o644)
    return {"files": list(files), "source_modified": False, "built": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.source, args.output), indent=2))
