#!/usr/bin/env python3
"""Create a fresh metadata-authoritative tar, never an EROFS image.

This experimental helper is for the root agent's synthetic validation first.
It executes no native tools, extracts nothing, and never changes its inputs.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types
import uuid

sys.dont_write_bytecode = True
PIN = "2c190a73fceb29f00da0558e44bb88ce19ec5bf4"
MAX_PAX = 512  # Below the minimum plain-file iostream buffer in pinned tar.c.
MAX_TAR_FILE = 0o77777777777
BLOCK = 512


def require(condition, message):
    if not condition:
        raise ValueError(message)


def signature(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


@contextmanager
def directory(path):
    value = os.fsencode(os.path.abspath(path))
    parts = [] if value == b"/" else value.split(b"/")[1:]
    require(all(p not in {b"", b".", b".."} for p in parts), "noncanonical directory")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(b"/", flags)
    try:
        for component in parts:
            newfd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = newfd
        yield fd
    finally:
        os.close(fd)


@contextmanager
def regular(rootfd, path):
    require(path.startswith(b"/") and path != b"/", "expected image-relative file path")
    parts = path[1:].split(b"/")
    require(all(p not in {b"", b".", b".."} for p in parts), "noncanonical file path")
    fd = os.dup(rootfd)
    try:
        for component in parts[:-1]:
            newfd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = newfd
        initial = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
        require(stat.S_ISREG(initial.st_mode), "selected byte source is not regular")
        datafd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        with os.fdopen(datafd, "rb") as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and signature(initial) == signature(before), "byte source changed before open")
            yield stream, before
            require(signature(before) == signature(os.fstat(stream.fileno()))
                    == signature(os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)), "byte source changed during read")
    finally:
        os.close(fd)


@contextmanager
def absolute_regular(path):
    absolute = os.fsencode(os.path.abspath(path))
    parent, name = absolute.rsplit(b"/", 1)
    with directory(parent) as rootfd:
        with regular(rootfd, b"/" + name) as opened:
            yield opened


def bounded_bytes(path, maximum):
    with absolute_regular(path) as (stream, st):
        require(st.st_size <= maximum, "control file exceeds bound")
        data = stream.read(maximum + 1)
        require(len(data) == st.st_size, "control file changed length")
        return data


def load_validator(path, digest):
    raw = bounded_bytes(path, 1024 * 1024)
    require(hashlib.sha256(raw).hexdigest() == digest, "validator source hash mismatch")
    module = types.ModuleType("erofs_writer_bound_validator")
    module.__file__ = os.path.abspath(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module


def pax_record(key, value):
    require(key and not any(c in key for c in (b"\0", b"=", b"\n")), "unrepresentable PAX key")
    base = len(key) + len(value) + 3
    length = base + len(str(base))
    while base + len(str(length)) != length:
        length = base + len(str(length))
    result = str(length).encode() + b" " + key + b"=" + value + b"\n"
    require(len(result) == length and length <= MAX_PAX, "PAX record exceeds pinned reader bound")
    return result


def tar_header(name, kind, size=0, mode=0o644, devmajor=0, devminor=0):
    require(0 <= size <= MAX_TAR_FILE, "file too large for bounded USTAR schema")
    require(0 <= mode <= 0o7777 and 0 < len(name) <= 100, "invalid tar header fields")
    h = bytearray(512)
    h[:len(name)] = name
    for offset, width, number in ((100, 8, mode), (108, 8, 0), (116, 8, 0),
                                  (124, 12, size), (136, 12, 0), (329, 8, devmajor), (337, 8, devminor)):
        h[offset:offset + width] = f"{number:0{width - 1}o}".encode() + b"\0"
    h[148:156] = b"        "
    h[156:157] = kind
    h[257:263] = b"ustar\0"
    h[263:265] = b"00"
    h[148:156] = f"{sum(h):06o}".encode() + b"\0 "
    return bytes(h)


class TarOutput:
    def __init__(self, stream):
        self.stream, self.digest, self.size = stream, hashlib.sha256(), 0

    def write(self, data):
        self.stream.write(data)
        self.digest.update(data)
        self.size += len(data)

    def padding(self, size):
        self.write(b"\0" * (-size % BLOCK))


def entry_headers(out, path, row, *, size, link=None, hardlink=False):
    rel = b"." if path == b"/" else path[1:]
    records = [pax_record(b"path", rel),
               pax_record(b"uid", str(row["uid"]).encode()),
               pax_record(b"gid", str(row["gid"]).encode()),
               pax_record(b"mtime", f'{row["mtime_sec"]}.{row["mtime_nsec"]:09d}'.encode())]
    if link is not None:
        records.append(pax_record(b"linkpath", link))
    if not hardlink:
        for attr in row["xattrs"]:
            name = bytes.fromhex(attr["name_hex"])
            value = bytes.fromhex(attr["value_hex"])
            records.append(pax_record(b"SCHILY.xattr." + name, value))
    payload = bytearray()
    for record in records:
        if payload and len(payload) + len(record) > MAX_PAX:
            out.write(tar_header(b"PaxHeader", b"x", len(payload)))
            out.write(payload)
            out.padding(len(payload))
            payload.clear()
        payload.extend(record)
    if payload:
        out.write(tar_header(b"PaxHeader", b"x", len(payload)))
        out.write(payload)
        out.padding(len(payload))
    kind = b"1" if hardlink else {"regular": b"0", "directory": b"5", "symlink": b"2",
                                  "char": b"3", "block": b"4", "fifo": b"6"}[row["type"]]
    rdev = row["rdev"] or 0
    major, minor = ((rdev >> 8) & 0xfff), ((rdev & 255) | ((rdev >> 12) & 0xfffff00))
    out.write(tar_header(b"entry", kind, size, stat.S_IMODE(row["mode"]), major, minor))


def copy_verified(opened, expected, out=None):
    stream, st = opened
    require(st.st_size == expected["size_bytes"], "byte source size mismatch")
    digest, count = hashlib.sha256(), 0
    while data := stream.read(1024 * 1024):
        count += len(data)
        require(count <= expected["size_bytes"], "byte source grew")
        digest.update(data)
        if out is not None:
            out.write(data)
    require(count == expected["size_bytes"] and digest.hexdigest() == expected["sha256"], "byte source content mismatch")
    return count


def admit(manifest):
    sb = manifest.header["superblock"]
    require(sb["build_time_nsec"] == 0, "pinned CLI cannot preserve fractional superblock build time")
    require(sb["feature_compat"] in {3, 7} and sb["feature_incompat"] == 1
            and sb["available_compression_algorithms"] == 1, "unsupported source feature combination")
    label = bytes.fromhex(sb["volume_name_hex"])
    text = label.split(b"\0", 1)[0]
    require(len(text) <= 15 and label == text.ljust(16, b"\0")
            and all(32 <= c < 127 for c in text), "unrepresentable volume label")
    for path, row in manifest.entries.items():
        require(row["type"] in {"regular", "directory", "symlink", "char", "block", "fifo"}, "socket inode has no admitted tar representation")
        require(row["mtime_nsec"] == 0, "nonzero nanoseconds require a proven native stat-macro build")
        require(row["size_bytes"] <= MAX_TAR_FILE, "file too large for bounded USTAR schema")
        for attr in row["xattrs"]:
            name, value = bytes.fromhex(attr["name_hex"]), bytes.fromhex(attr["value_hex"])
            if name.startswith(b"system.posix_acl_"):
                require(name in {b"system.posix_acl_access", b"system.posix_acl_default"}, "unrepresentable ACL xattr name")
            prefix = next((p for p in (b"user.", b"trusted.", b"security.",
                                      b"system.posix_acl_access", b"system.posix_acl_default") if name.startswith(p)), None)
            require(prefix is not None and len(name) - len(prefix) <= 255 and len(value) <= 65535, "unrepresentable xattr")
            pax_record(b"SCHILY.xattr." + name, value)
        pax_record(b"path", b"." if path == b"/" else path[1:])
        if row["type"] == "symlink":
            pax_record(b"linkpath", bytes.fromhex(row["symlink_target_hex"]))
    for group in manifest.hardlinks:
        require(manifest.entries[group[0]]["type"] == "regular", "nonregular hardlink group requires separate proof")
    return text.decode("ascii")


def assemble(manifest, staging, replacements, output):
    admit(manifest)
    aliases = {path: group[0] for group in manifest.hardlinks for path in group[1:]}
    order = sorted((p for p, r in manifest.entries.items() if r["type"] == "directory"), key=lambda p: (p.count(b"/"), p))
    order += sorted(p for p, r in manifest.entries.items() if r["type"] != "directory")
    checked, source_bytes = 0, 0
    with directory(staging) as rootfd:
        for path in order:
            row = manifest.entries[path]
            if row["type"] == "directory":
                entry_headers(output, path, row, size=0)
                continue
            if row["type"] == "symlink":
                entry_headers(output, path, row, size=0, link=bytes.fromhex(row["symlink_target_hex"]))
                continue
            if row["type"] in {"char", "block", "fifo"}:
                entry_headers(output, path, row, size=0)
                continue
            original = {"size_bytes": row["size_bytes"], "sha256": row["content_sha256"]}
            if path in aliases:
                with regular(rootfd, path) as opened:
                    source_bytes += copy_verified(opened, original)
                entry_headers(output, path, row, size=0, link=aliases[path][1:], hardlink=True)
            elif path in replacements:
                replacement = replacements[path]
                with regular(rootfd, path) as opened:
                    source_bytes += copy_verified(opened, original)
                entry_headers(output, path, row, size=replacement["size_bytes"])
                with absolute_regular(replacement["source"]) as opened:
                    source_bytes += copy_verified(opened, replacement, output)
                output.padding(replacement["size_bytes"])
            else:
                entry_headers(output, path, row, size=row["size_bytes"])
                with regular(rootfd, path) as opened:
                    source_bytes += copy_verified(opened, original, output)
                output.padding(row["size_bytes"])
            checked += 1
    output.write(b"\0" * 1024)
    return {"regular_paths_verified": checked, "source_bytes_read": source_bytes}


def replacement_plan(validator, manifest, plan):
    require(type(plan) is dict, "replacement plan must be an object")
    require(set(plan) == {"schema_version", "partition", "replacements"}
            and type(plan["schema_version"]) is int and plan["schema_version"] == 1,
            "unexpected replacement plan")
    require(type(plan["partition"]) is str and plan["partition"] in validator.REPLACEMENT_PATHS
            and type(plan["replacements"]) is list, "unsupported partition or replacement array")
    replacements = {}
    for row in plan["replacements"]:
        require(type(row) is dict and set(row) == {"path", "before", "after"}, "unexpected replacement fields")
        require(type(row["path"]) is str and row["path"] in validator.REPLACEMENT_PATHS[plan["partition"]], "unreviewed replacement path")
        path = row["path"].encode("ascii")
        require(path not in replacements and path in manifest.entries, "duplicate/missing replacement")
        old = manifest.entries[path]
        require(old["type"] == "regular" and old["nlink"] == 1, "replacement must be single-link regular")
        validator._content_identity(row["before"])
        require(type(row["before"]) is dict and set(row["before"]) == {"sha256", "size_bytes"}
                and row["before"] == {"sha256": old["content_sha256"], "size_bytes": old["size_bytes"]}, "replacement original identity mismatch")
        new = row["after"]
        require(type(new) is dict and set(new) == {"sha256", "size_bytes", "source"}, "unexpected replacement output fields")
        validator._digest(new["sha256"], "replacement SHA256")
        validator._integer(new["size_bytes"], "replacement size", MAX_TAR_FILE)
        require(type(new["source"]) is str and new["source"].startswith("/"), "replacement source must be absolute")
        replacements[path] = new
    require(set(path.decode() for path in replacements) == validator.REPLACEMENT_PATHS[plan["partition"]], "incomplete replacement set")
    return replacements


def destinations(staging, output_tar, receipt):
    source = Path(os.path.abspath(staging))
    output, report = Path(os.path.abspath(output_tar)), Path(os.path.abspath(receipt))
    require(not output.is_relative_to(source) and not report.is_relative_to(source), "outputs must be outside the read-only staging tree")
    require(output != report, "tar and receipt destinations must differ")
    return output, report


def mkfs_command(sb, label, output_tar):
    command = ["env", "-u", "SOURCE_DATE_EPOCH", "PINNED_MKFS_EROFS", "--tar=f", "--clean=data", "--mkfs-time",
               "--preserve-mtime", "-T", str(sb["build_time_sec"]), "-U", str(uuid.UUID(hex=sb["uuid_hex"])),
               "-L", label, "-b4096", "-zlz4hc,level=9", "-C4096",
               # Pinned worker parsing checks stale errno. This identity offset
               # clears errno immediately before parsing the worker count.
               "--uid-offset=0", "--workers=0", "--ovlfs-strip=0"]
    if not sb["feature_compat"] & 4:
        command += ["-E", "^xattr-name-filter"]
    command += ["NEW_IMAGE_PATH", os.path.abspath(output_tar)]
    return command


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("build-tar",))
    for name in ("validator", "validator-sha256", "manifest", "manifest-sha256", "image-sha256", "staging-root", "replacements", "output-tar", "receipt"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args(argv)
    destination, receipt_path = destinations(a.staging_root, a.output_tar, a.receipt)
    validator = load_validator(a.validator, a.validator_sha256)
    manifest = validator.read_manifest(Path(a.manifest), expected_image_sha256=a.image_sha256,
                                       expected_manifest_sha256=a.manifest_sha256)
    label = admit(manifest)
    raw = bounded_bytes(a.replacements, 1024 * 1024)
    plan = validator._json(raw)
    replacements = replacement_plan(validator, manifest, plan)
    require(not os.path.lexists(a.receipt), "receipt already exists")
    with directory(destination.parent) as parentfd:
        fd = os.open(os.fsencode(destination.name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parentfd)
    with os.fdopen(fd, "wb") as stream:
        out = TarOutput(stream)
        counts = assemble(manifest, a.staging_root, replacements, out)
        stream.flush()
        os.fsync(stream.fileno())
    sb = manifest.header["superblock"]
    command = mkfs_command(sb, label, a.output_tar)
    receipt = {"schema_version": 1, "operation": "prepare-metadata-authoritative-full-tar",
               "pinned_erofs_commit": PIN, "manifest_sha256": manifest.identity["sha256"],
               "validator_source_sha256": a.validator_sha256,
               "input_image_sha256": a.image_sha256, "replacement_plan_sha256": hashlib.sha256(raw).hexdigest(),
               "tar": {"sha256": out.digest.hexdigest(), "size_bytes": out.size}, "counts": counts,
               "replacement_bindings": plan["replacements"],
               "entry_count": len(manifest.entries), "hardlink_groups": len(manifest.hardlinks),
               "metadata_from_extracted_tree": False, "native_commands_executed": False,
               "images_accessed": False, "image_adoption_authorized": False,
               "proposed_mkfs_argv": command, "complete": True}
    with directory(receipt_path.parent) as parentfd:
        receiptfd = os.open(os.fsencode(receipt_path.name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parentfd)
    with os.fdopen(receiptfd, "w", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print("full-tar preparation failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
