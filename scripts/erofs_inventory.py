#!/usr/bin/env python3
"""Inventory EROFS and capture selected regular files without mounting images.

The dump.erofs 1.9.4 text format was checked against erofs-utils commit
f36cadb5c563995ab3aa8572a60ed6b721b9557d (dump/main.c). Only the installed
tool is executed; nothing from the image is executed or materialized as a link.
"""

from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import stat
import subprocess
import sys
import tempfile
import time

if __package__:
    from .artifact_files import publish_new_directory
    from .firmware import _checksum, _directory, _open_regular, _signature
else:
    from artifact_files import publish_new_directory
    from firmware import _checksum, _directory, _open_regular, _signature


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOL = Path("/opt/homebrew/bin/dump.erofs")
TOOL_VERSION = "dump.erofs (erofs-utils) 1.9.4"
BUFFER_SIZE = 64 * 1024
MAX_LISTING_BYTES = 4 * 1024**2
MAX_INVENTORY_BYTES = 64 * 1024**2
MAX_ENTRIES = 100_000
MAX_DEPTH = 64
MAX_CAPTURE_PATHS = 4096
MAX_FILE_BYTES = 512 * 1024**2
MAX_CAPTURE_BYTES = 2 * 1024**3
DISK_RESERVE = 64 * 1024**2
TYPE_NAMES = {1: "regular", 2: "directory", 3: "character", 4: "block",
              5: "fifo", 6: "socket", 7: "symlink"}


class InventoryError(ValueError):
    """Image evidence or tool output does not meet this workflow's safety rules."""


def _real_parents(path):
    for parent in [*reversed(path.parents), path]:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise InventoryError("input/output ancestors must be real directories, not symlinks")


def _unchanged(file):
    _real_parents(file["path"].parent)
    if (file["signature"] != _signature(os.fstat(file["stream"].fileno()))
            or file["signature"] != _signature(file["path"].lstat())):
        raise InventoryError(f"input changed during the batch: {file['path'].name}")


def _hash(stream):
    digest = hashlib.sha256()
    size = 0
    while data := stream.read(BUFFER_SIZE):
        digest.update(data)
        size += len(data)
    return digest.hexdigest(), size


@contextmanager
def _checked_file(path, expected=None):
    path = Path(os.path.abspath(path))
    _real_parents(path.parent)
    with _open_regular(path) as stream:
        signature = _signature(os.fstat(stream.fileno()))
        digest, size = _hash(stream)
        if expected is not None and digest != expected:
            raise InventoryError(f"SHA256 mismatch: {path.name}")
        file = {"path": path, "stream": stream, "signature": signature,
                "sha256": digest, "size_bytes": size}
        _unchanged(file)
        yield file
        _unchanged(file)


def _image_record(file):
    return {"path": str(file["path"]), "sha256": file["sha256"], "size_bytes": file["size_bytes"]}


def _run(tool, arguments, output, *, limit, timeout, image=None):
    """Drain both pipes with bounded buffers, killing a failed/timed-out child."""
    command = [str(tool["path"]), *arguments]
    inherited = ()
    if image is not None:
        inherited = (image["stream"].fileno(),)
        command.append(f"/dev/fd/{inherited[0]}")
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, pass_fds=inherited,
                               env={"LC_ALL": "C", "LANG": "C", "TZ": "UTC", "PATH": "/usr/bin:/bin"})
    deadline = time.monotonic() + timeout
    size, digest, errors = 0, hashlib.sha256(), bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise InventoryError("dump.erofs command timed out")
                for key, _ in selector.select(min(remaining, 1.0)):
                    data = os.read(key.fileobj.fileno(), BUFFER_SIZE)
                    if not data:
                        selector.unregister(key.fileobj)
                    elif key.data == "stderr":
                        if len(errors) + len(data) > BUFFER_SIZE:
                            raise InventoryError("dump.erofs stderr exceeds its size bound")
                        errors.extend(data)
                    else:
                        size += len(data)
                        if size > limit:
                            raise InventoryError("dump.erofs output exceeds its size bound")
                        digest.update(data)
                        output.write(data)
        status = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if status or errors:
            detail = errors[:2048].decode("utf-8", errors="replace")
            raise InventoryError(f"dump.erofs failed or reported diagnostics (exit {status}): {detail}")
        return {"sha256": digest.hexdigest(), "size_bytes": size}
    except subprocess.TimeoutExpired as exc:
        raise InventoryError("dump.erofs command timed out") from exc
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()


def _component(name):
    if (not name or name in (".", "..") or name != name.strip() or not name.isprintable()
            or "/" in name or "\\" in name or len(name.encode("utf-8")) > 255):
        raise InventoryError("unsafe or ambiguous image filename component")
    return name


def _path(path):
    if not isinstance(path, str) or not path.startswith("/") or len(path.encode("utf-8")) > 4096:
        raise InventoryError("image paths must be bounded absolute POSIX paths")
    if path != "/":
        for component in path[1:].split("/"):
            _component(component)
    return path


def _metadata(lines):
    patterns = (
        r"Path : (/.*)", r"Size: ([0-9]+)  On-disk size: ([0-9]+)  (regular file|directory)",
        r"NID: ([0-9]{1,20})   Links: [0-9]+   Layout: [0-9]+   Compression ratio: [-+a-zA-Z0-9.]+%",
        r"Inode size: (?:32|64)   Xattr size: [0-9]+",
        r"Uid: ([0-9]+)   Gid: ([0-9]+)  Access: ([0-7]{4,6})/[rwxstST-]{9}",
        r"Timestamp: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{9}",
    )
    if len(lines) < len(patterns):
        raise InventoryError("truncated dump.erofs inode metadata")
    matches = [re.fullmatch(pattern, line) for pattern, line in zip(patterns, lines)]
    if not all(matches):
        raise InventoryError("unexpected dump.erofs inode metadata")
    result = {"path": _path(matches[0][1]), "nid": int(matches[2][1]),
              "size_bytes": int(matches[1][1]), "type": "regular" if matches[1][3] == "regular file" else "directory",
              "uid": int(matches[4][1]), "gid": int(matches[4][2]), "mode": matches[4][3]}
    if result["nid"] >= 2**64:
        raise InventoryError("inode number exceeds uint64")
    return result


def parse_listing(text, *, path, nid=None, parent_nid=None):
    lines = text.splitlines()
    info = _metadata(lines)
    if (info["path"] != path or info["type"] != "directory"
            or (nid is not None and info["nid"] != nid)):
        raise InventoryError("directory listing does not match its requested path/inode")
    if len(lines) < 8 or lines[6] != "" or lines[7].strip() != "NID TYPE  FILENAME":
        raise InventoryError("missing or unexpected directory table header")
    names, dots, entries = set(), {}, []
    for line in lines[8:]:
        match = re.fullmatch(r" *([0-9]{1,20}) +([1-7])  (.+)", line)
        if not match:
            raise InventoryError("malformed dump.erofs directory entry")
        child, kind, name = int(match[1]), int(match[2]), match[3]
        if child >= 2**64 or name in names:
            raise InventoryError("duplicate directory component or invalid inode number")
        names.add(name)
        if len(names) > MAX_ENTRIES + 2:
            raise InventoryError("directory table exceeds the entry limit")
        if name in (".", ".."):
            if kind != 2:
                raise InventoryError("dot entries must be directories")
            dots[name] = child
        else:
            _component(name)
            child_path = _path((path.rstrip("/") + "/" + name))
            entries.append({"path": child_path, "nid": child, "type": TYPE_NAMES[kind]})
    expected_parent = info["nid"] if parent_nid is None else parent_nid
    if dots != {".": info["nid"], "..": expected_parent}:
        raise InventoryError("directory dot entries do not match the parent/inode")
    return info, entries


def _destination(path):
    path = Path(os.path.abspath(path))
    if not any(root in path.parents for root in (WORKSPACE_ROOT / "artifacts", WORKSPACE_ROOT / "evidence")):
        raise InventoryError("outputs must be private directories under workspace artifacts/ or evidence/")
    if os.path.lexists(path):
        raise InventoryError("output already exists; refusing to replace evidence")
    return path


@contextmanager
def _staging(destination, required_bytes):
    parent = _directory(destination.parent)
    if shutil.disk_usage(parent).free < required_bytes + DISK_RESERVE:
        raise InventoryError("insufficient free disk for bounded outputs")
    lock = parent / ("." + destination.name + ".erofs.lock")
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    staging = None
    try:
        staging = Path(tempfile.mkdtemp(prefix="." + destination.name + ".stage-", dir=parent))
        yield staging
        _real_parents(parent)
        publish_new_directory(staging, destination)
        staging = None
    finally:
        try:
            if staging is not None:
                shutil.rmtree(staging)
        finally:
            lock.unlink()


def _write_json(path, data, limit=MAX_INVENTORY_BYTES):
    size = 0
    digest = hashlib.sha256()
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        for text in json.JSONEncoder(sort_keys=True, indent=2).iterencode(data):
            encoded = text.encode("utf-8")
            size += len(encoded)
            if size > limit:
                raise InventoryError("JSON artifact exceeds its size bound")
            digest.update(encoded)
            stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    with _checked_file(path, digest.hexdigest()) as file:
        return {"name": path.name, "sha256": file["sha256"], "size_bytes": file["size_bytes"]}


@contextmanager
def _batch(image, expected_sha256, timeout, batch_timeout):
    expected = _checksum(expected_sha256)
    if expected is None or not 0 < timeout <= 60 or not 0 < batch_timeout <= 3600:
        raise InventoryError("SHA256 is required; timeouts must be positive and bounded")
    tool_path = DEFAULT_TOOL.resolve(strict=True)
    if not os.access(tool_path, os.X_OK):
        raise InventoryError("installed dump.erofs is not executable")
    with _checked_file(image, expected) as source, _checked_file(tool_path) as tool:
        deadline = time.monotonic() + batch_timeout

        def call(arguments, output=None, limit=MAX_LISTING_BYTES, with_image=True):
            _unchanged(source)
            _unchanged(tool)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InventoryError("EROFS batch timed out")
            buffer = io.BytesIO() if output is None else output
            result = _run(tool, arguments, buffer, limit=limit,
                          timeout=min(timeout, remaining), image=source if with_image else None)
            _unchanged(source)
            _unchanged(tool)
            return buffer.getvalue().decode("utf-8", errors="strict") if output is None else result

        version = call(["--version"], limit=4096, with_image=False).strip()
        if version != TOOL_VERSION:
            raise InventoryError("unsupported dump.erofs version; expected erofs-utils 1.9.4")
        provenance = {"image": _image_record(source), "tool": {**_image_record(tool),
                      "requested_path": str(DEFAULT_TOOL), "version": version}}
        yield call, provenance, source, tool


def scan_image(image, *, expected_sha256, output_dir, max_entries=MAX_ENTRIES,
               max_depth=MAX_DEPTH, timeout=30, batch_timeout=600):
    if (type(max_entries) is not int or not 1 <= max_entries <= MAX_ENTRIES
            or type(max_depth) is not int or not 0 <= max_depth <= MAX_DEPTH):
        raise InventoryError("entry and depth limits must be bounded integers")
    destination = _destination(output_dir)
    with _batch(image, expected_sha256, timeout, batch_timeout) as (call, provenance, source, tool):
        with _staging(destination, MAX_INVENTORY_BYTES) as staging:
            root, children = parse_listing(call(["--ls", "--path=/"]), path="/")
            entries = [{"path": "/", "nid": root["nid"], "type": "directory"}]
            queue = deque([(root["nid"], "/", root["nid"], 0, children)])
            directories = {root["nid"]}
            inode_types = {root["nid"]: "directory"}
            while queue:
                parent, directory_path, parent_nid, depth, children = queue.popleft()
                if children is None:
                    _, children = parse_listing(call(["--ls", f"--nid={parent}"]),
                                                path=directory_path, nid=parent, parent_nid=parent_nid)
                for entry in children:
                    if len(entries) >= max_entries or depth + 1 > max_depth:
                        raise InventoryError("EROFS inventory exceeds its entry or depth limit")
                    previous_type = inode_types.setdefault(entry["nid"], entry["type"])
                    if previous_type != entry["type"]:
                        raise InventoryError("inode appears with inconsistent types")
                    entries.append(entry)
                    if entry["type"] == "directory":
                        if entry["nid"] in directories:
                            raise InventoryError("directory inode loop or alias detected")
                        directories.add(entry["nid"])
                        queue.append((entry["nid"], entry["path"], parent, depth + 1, None))
            entries.sort(key=lambda entry: entry["path"])
            inventory = {"schema_version": 1, "image": provenance["image"], "entries": entries}
            record = _write_json(staging / "inventory.json", inventory)
            receipt = {"schema_version": 1, "operation": "erofs-scan", **provenance,
                       "created_at_utc": datetime.now(timezone.utc).isoformat(),
                       "inventory": record, "entry_count": len(entries),
                       "symlinks_followed": False, "image_mounted": False, "origin_verified": False}
            _write_json(staging / "receipt.json", receipt)
            _unchanged(source)
            _unchanged(tool)
        return receipt


def _read_json(path, limit, expected=None):
    with _checked_file(path, expected) as file:
        if file["size_bytes"] > limit:
            raise InventoryError("inventory/receipt exceeds its size bound")
        file["stream"].seek(0)
        raw = file["stream"].read(limit + 1)
        if len(raw) > limit:
            raise InventoryError("inventory/receipt grew beyond its size bound")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise InventoryError("inventory/receipt must be a JSON object")
        return data, file["sha256"]


def _inventory(directory, image):
    directory = Path(os.path.abspath(directory))
    _real_parents(directory)
    receipt, receipt_hash = _read_json(directory / "receipt.json", 256 * 1024)
    if (type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 1
            or receipt.get("operation") != "erofs-scan"
            or not isinstance(receipt.get("inventory"), dict)
            or receipt["inventory"].get("name") != "inventory.json"):
        raise InventoryError("invalid EROFS scan receipt")
    checksum = receipt["inventory"].get("sha256")
    if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise InventoryError("scan receipt lacks an inventory SHA256")
    inventory, _ = _read_json(directory / "inventory.json", MAX_INVENTORY_BYTES, checksum)
    for document in (receipt, inventory):
        parent = document.get("image", {})
        if (not isinstance(parent, dict) or parent.get("sha256") != image["sha256"]
                or parent.get("size_bytes") != image["size_bytes"]):
            raise InventoryError("inventory belongs to a different parent image")
    entries = inventory.get("entries")
    if (type(inventory.get("schema_version")) is not int or inventory["schema_version"] != 1
            or not isinstance(entries, list) or not 1 <= len(entries) <= MAX_ENTRIES
            or type(receipt.get("entry_count")) is not int or receipt["entry_count"] != len(entries)):
        raise InventoryError("invalid inventory schema or entry count")
    paths, inode_types, directories = {}, {}, set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "nid", "type"}:
            raise InventoryError("invalid inventory entry")
        path, nid, kind = _path(entry["path"]), entry["nid"], entry["type"]
        if (path in paths or type(nid) is not int or not 0 <= nid < 2**64
                or kind not in TYPE_NAMES.values()):
            raise InventoryError("duplicate path or invalid inode/type in inventory")
        if inode_types.setdefault(nid, kind) != kind or (kind == "directory" and nid in directories):
            raise InventoryError("inconsistent inode type or directory alias in inventory")
        if kind == "directory":
            directories.add(nid)
        paths[path] = entry
    if paths.get("/", {}).get("type") != "directory":
        raise InventoryError("inventory lacks its root directory")
    for path in paths:
        if path != "/" and paths.get(str(PurePosixPath(path).parent), {}).get("type") != "directory":
            raise InventoryError("inventory path has no inventoried directory parent")
    return paths, receipt_hash, checksum


def capture_files(image, *, expected_sha256, inventory_dir, output_dir, paths,
                  max_file_bytes=MAX_FILE_BYTES, max_total_bytes=MAX_CAPTURE_BYTES,
                  timeout=30, batch_timeout=600):
    if (type(max_file_bytes) is not int or not 0 < max_file_bytes <= MAX_FILE_BYTES
            or type(max_total_bytes) is not int or not 0 < max_total_bytes <= MAX_CAPTURE_BYTES):
        raise InventoryError("capture byte limits must be positive bounded integers")
    selected = [_path(path) for path in paths]
    if not 1 <= len(selected) <= MAX_CAPTURE_PATHS or len(set(selected)) != len(selected):
        raise InventoryError("capture requires a bounded, nonempty list of unique explicit paths")
    destination = _destination(output_dir)
    with _batch(image, expected_sha256, timeout, batch_timeout) as (call, provenance, source, tool):
        entries, receipt_hash, inventory_hash = _inventory(inventory_dir, provenance["image"])
        for path in selected:
            if entries.get(path, {}).get("type") != "regular":
                raise InventoryError("only explicitly inventoried regular files may be captured")
        infos, total = [], 0
        for path in selected:
            entry = entries[path]
            lines = call([f"--nid={entry['nid']}"]).splitlines()
            info = _metadata(lines)
            if (len(lines) != 6 or info["type"] != "regular"
                    or info["nid"] != entry["nid"] or info["path"] != path):
                raise InventoryError("inode metadata does not match selected regular path; aliases are not followed")
            total += info["size_bytes"]
            if info["size_bytes"] > max_file_bytes or total > max_total_bytes:
                raise InventoryError("selected files exceed the capture byte limit")
            infos.append(info)
        with _staging(destination, total) as staging:
            (staging / "files").mkdir(mode=0o700)
            records = []
            for index, info in enumerate(infos, 1):
                relative = f"files/{index:04d}"
                target = staging / relative
                with target.open("xb") as output:
                    os.chmod(target, 0o600)
                    result = call(["--cat", f"--nid={info['nid']}"], output,
                                  limit=info["size_bytes"])
                    output.flush()
                    os.fsync(output.fileno())
                if result["size_bytes"] != info["size_bytes"]:
                    raise InventoryError("captured file length differs from inode metadata")
                with _checked_file(target, result["sha256"]) as copied:
                    if copied["size_bytes"] != result["size_bytes"]:
                        raise InventoryError("captured output failed size readback")
                records.append({**info, "output_path": relative, "sha256": result["sha256"],
                                "readback_verified": True})
            receipt = {"schema_version": 1, "operation": "erofs-capture", **provenance,
                       "created_at_utc": datetime.now(timezone.utc).isoformat(),
                       "inventory_sha256": inventory_hash, "inventory_receipt_sha256": receipt_hash,
                       "files": records, "total_bytes": total, "image_mounted": False,
                       "symlinks_followed": False, "firmware_executed": False, "origin_verified": False}
            _write_json(staging / "receipt.json", receipt)
            _unchanged(source)
            _unchanged(tool)
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("scan", "capture"):
        command = commands.add_parser(name)
        command.add_argument("--image", required=True, type=Path)
        command.add_argument("--expected-sha256", required=True)
        command.add_argument("--output", required=True, type=Path, help="new directory under artifacts/ or evidence/")
        command.add_argument("--timeout-seconds", type=float, default=30)
        command.add_argument("--batch-timeout-seconds", type=float, default=600)
        if name == "scan":
            command.add_argument("--max-entries", type=int, default=MAX_ENTRIES)
            command.add_argument("--max-depth", type=int, default=MAX_DEPTH)
        else:
            command.add_argument("--inventory", required=True, type=Path, help="complete scan output directory")
            command.add_argument("--path", required=True, action="append", dest="paths")
            command.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
            command.add_argument("--max-total-bytes", type=int, default=MAX_CAPTURE_BYTES)
    args = parser.parse_args(argv)
    options = {"expected_sha256": args.expected_sha256, "output_dir": args.output,
               "timeout": args.timeout_seconds, "batch_timeout": args.batch_timeout_seconds}
    try:
        if args.operation == "scan":
            receipt = scan_image(args.image, max_entries=args.max_entries, max_depth=args.max_depth, **options)
        else:
            receipt = capture_files(args.image, inventory_dir=args.inventory, paths=args.paths,
                                    max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes, **options)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        print(f"EROFS evidence: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "receipt": receipt}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
