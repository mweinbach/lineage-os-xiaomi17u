#!/usr/bin/env python3
"""Reproduce and verify the pinned working76 prebuilt recovery; never access a phone."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

if __package__:
    from . import inspect_twrp_image as envelope
    from .inspect_twrp_ramdisk import MAX_ARCHIVE_BYTES, _archive
    from .twrp_cpio_overlay import replace_files
else:
    import inspect_twrp_image as envelope
    from inspect_twrp_ramdisk import MAX_ARCHIVE_BYTES, _archive
    from twrp_cpio_overlay import replace_files


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "config/twrp-working.json"
MAX_IMAGE = 104857600
MAX_TOOL = 32 * 1024**2
MAX_TEXT = 1024**2
MAX_NATIVE_LOG = 64 * 1024
TIMEOUT = 120
LOCAL_FIELDS = frozenset(("baseline_image", "key", "mkbootimg", "avbtool", "lz4", "openssl", "public_key"))
HASH_DESCRIPTOR = struct.Struct(">QQQ32sIIII60s")


class TwrpWorkingError(ValueError):
    """A pinned input, preservation condition, or native verification failed."""


def _require(condition, message):
    if not condition:
        raise TwrpWorkingError(message)


def _guard(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except TwrpWorkingError:
            raise
        except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as exc:
            raise TwrpWorkingError("invalid or unavailable input for " + function.__name__) from exc
    return checked


def _json(raw):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            _require(name not in result, "duplicate JSON field")
            result[name] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _identity(data):
    return {"sha256": _sha(data), "size_bytes": len(data)}


def _matches(data, expected, label):
    _require(_sha(data) == expected["sha256"], label + " SHA256 differs")
    if "size_bytes" in expected:
        _require(len(data) == expected["size_bytes"], label + " size differs")


def _path(value, *, tool=False):
    path = envelope._absolute_path(value)
    if tool:
        path = path.resolve(strict=True)  # Permit the selected Homebrew tool alias.
    for parent in path.parents:
        _require(stat.S_ISDIR(parent.lstat().st_mode), "input/output ancestor is not a real directory")
    return path


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(path, limit, expected=None):
    path = _path(path)
    with envelope._parent_directory(path) as parent:
        initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(stat.S_ISREG(initial.st_mode), "input is not a regular file")
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            _require(stat.S_ISREG(before.st_mode) and _signature(initial) == _signature(before),
                     "input changed before read")
            _require(0 < before.st_size <= limit, "input size outside bounds")
            data = stream.read(before.st_size + 1)
            _require(len(data) == before.st_size and _signature(before) == _signature(os.fstat(stream.fileno()))
                     == _signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                     "input changed during read")
    if expected is not None:
        _matches(data, expected, "input")
    return data


def _write(path, data):
    path = _path(path)
    with envelope._parent_directory(path) as parent:
        descriptor = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)


def _mkdir(path):
    path = _path(path)
    with envelope._parent_directory(path) as parent:
        os.mkdir(path.name, mode=0o700, dir_fd=parent)
        info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(stat.S_ISDIR(info.st_mode) and info.st_mode & 0o077 == 0, "output directory is not private")


def _fresh_output(value):
    """Create missing output parents without following links; never reuse the leaf."""
    path = envelope._absolute_path(value)
    _require(bool(path.name), "output directory already exists; never overwrite")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:-1]:
            try:
                child = os.open(part, flags, dir_fd=parent)
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=parent)
                except FileExistsError:
                    pass  # A concurrent real parent is admissible, never a symlink.
                child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent)
        except FileExistsError as exc:
            raise TwrpWorkingError("output directory already exists; never overwrite") from exc
        info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(stat.S_ISDIR(info.st_mode) and info.st_mode & 0o077 == 0, "output directory is not private")
    finally:
        os.close(parent)
    return path


def _save(path, report):
    _write(path, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())


@contextmanager
def _private_creation():
    previous = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(previous)


@_guard
def load_profile():
    """Load the maintained public profile, not a caller-selected compatibility mode."""
    raw = _read(PROFILE, MAX_TEXT)
    profile = _json(raw)
    _require(type(profile["schema_version"]) is int and profile["schema_version"] == 1
             and profile["profile_id"] == "nezha-working76"
             and profile["source_built"] is False, "unsupported working recovery profile")
    _require(set(profile["patch"]["files"]) == {"system/etc/init/hw/init.rc", "twres/ui.xml"},
             "profile must select exactly the two working76 text files")
    _require(profile["patch"]["path"] == "recovery/twrp-working/0001-permissive-and-no-vibration-defaults.patch",
             "unexpected public patch path")
    _require(profile["boot"]["kernel_size_bytes"] == 0 and profile["boot"]["header_version"] == 4
             and profile["avb"]["partition_name"] == "recovery"
             and profile["avb"]["flags"] == 0
             and profile["avb"]["rollback_index"] == profile["avb"]["rollback_index_location"] == 1,
             "unsupported recovery or AVB contract")
    return profile, _sha(raw)


@_guard
def load_local_config(path):
    """Read path-only defaults. Relative paths belong to the config's directory."""
    path = _path(path)
    data = _json(_read(path, 16 * 1024))
    _require(type(data) is dict and set(data) <= LOCAL_FIELDS, "unknown local-config fields")
    result = {}
    for name, value in data.items():
        _require(type(value) is str and 0 < len(value) <= 4096
                 and all(ord(c) >= 32 for c in value) and "PRIVATE KEY" not in value,
                 "local config accepts paths only")
        selected = Path(value)
        result[name] = Path(os.path.abspath(selected if selected.is_absolute() else path.parent / selected))
    return result


@_guard
def resolve_paths(local_config, explicit):
    """Resolve only requested inputs; do not open any configured input path."""
    _require(type(explicit) is dict and set(explicit) <= LOCAL_FIELDS, "unknown explicit path fields")
    defaults = load_local_config(local_config) if local_config is not None else {}
    result = {}
    for name, value in explicit.items():
        value = value if value is not None else defaults.get(name)
        _require(value is not None, "required input paths are missing")
        result[name] = Path(value)
    return result


@_guard
def plan():
    """No subprocesses, local defaults, images, or key files are read."""
    profile, digest = load_profile()
    patch = _read(ROOT / profile["patch"]["path"], MAX_TEXT, profile["patch"])
    return {"schema_version": 1, "status": "planned", "profile_id": profile["profile_id"],
            "profile_sha256": digest, "baseline": profile["baseline"], "output": profile["output"],
            "patch": {"path": profile["patch"]["path"], **_identity(patch)},
            "boot": profile["boot"], "avb": profile["avb"], "tools": profile["tools"],
            "source_built": False, "native_commands_run": False, "device_operations": []}


def _run(label, argv, env, work, records, *, max_file_bytes=MAX_IMAGE):
    """Bound native files, pipe output and elapsed time; never execute archive paths."""
    _require(re.fullmatch(r"[a-z0-9-]{1,64}", label) is not None, "invalid native step label")

    def limits():
        os.fchdir(work_fd)
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_file_bytes, max_file_bytes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    output = {"stdout": bytearray(), "stderr": bytearray()}
    process = None
    recorded = False
    deadline = time.monotonic() + TIMEOUT
    try:
        # Relative paths resolve against the inherited directory inode, even if
        # an ancestor is renamed. Native tools/private key remain pinned local
        # inputs, not claimed to be a sandbox against a hostile same-UID host.
        with envelope._parent_directory(work / "native-anchor") as work_fd:
            arguments = [str(x.relative_to(work)) if isinstance(x, Path) and x.is_relative_to(work)
                         else str(x) for x in argv]
            process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                       env=env, start_new_session=True, preexec_fn=limits,
                                       pass_fds=(work_fd,))
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                _require(remaining > 0, label + " timed out")
                for key, _ in selector.select(min(remaining, 0.25)):
                    buffer = output[key.data]
                    chunk = os.read(key.fileobj.fileno(), min(16384, MAX_NATIVE_LOG + 1 - len(buffer)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffer.extend(chunk)
                    _require(len(buffer) <= MAX_NATIVE_LOG, label + " output exceeds bound")
        code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        records.append({"step": label, "returncode": code,
                        **{name: _identity(value) for name, value in output.items()}})
        _save(work / f"native-{len(records):02d}-{label}.json", records[-1])
        recorded = True
        _require(code == 0, label + " failed (native output hashes recorded)")
    except BaseException as exc:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        if not recorded:
            records.append({"step": label, "returncode": process.returncode if process is not None else None,
                            "incomplete": True, **{name: _identity(value) for name, value in output.items()}})
            _save(work / f"native-{len(records):02d}-{label}.json", records[-1])
        if isinstance(exc, (OSError, subprocess.TimeoutExpired)):
            raise TwrpWorkingError(label + " could not complete") from exc
        raise
    finally:
        if process is not None:
            process.stdout.close()
            process.stderr.close()


def _prepare_tools(profile, work, *, avbtool, openssl, mkbootimg=None, lz4=None):
    paths, identities, snapshots = {}, {}, {}
    directory = work / "tools"
    _mkdir(directory)
    for name, value in (("avbtool", avbtool), ("mkbootimg", mkbootimg), ("lz4", lz4), ("openssl", openssl)):
        if value is None:
            continue
        original = _path(value, tool=True)
        data = _read(original, MAX_TOOL)
        if name == "openssl":
            accepted = [row for row in profile["tools"][name]["binaries"]
                        if row["sha256"] == _sha(data) and row["size_bytes"] == len(data)
                        and (mkbootimg is None or row["build_allowed"])]
            _require(bool(accepted) and original.name == "openssl", "unsupported OpenSSL executable")
        else:
            _matches(data, profile["tools"][name], name)
        identities[name] = _identity(data)
        snapshots[original] = identities[name]
        if name in ("avbtool", "mkbootimg"):
            paths[name] = directory / (name + ".py")
            _write(paths[name], data)
            if name == "mkbootimg":
                companion = profile["tools"][name]["companion"]
                source = original.parent / companion["path"]
                content = _read(source, MAX_TEXT, companion)
                destination = directory / companion["path"]
                _mkdir(destination.parent)
                _write(destination, content)
                snapshots[source] = _identity(content)
                identities["mkbootimg_companion"] = _identity(content)
        else:
            _require(bool(original.stat().st_mode & 0o111), name + " is not executable")
            paths[name] = original
    env = {"PATH": str(paths["openssl"].parent) + os.pathsep + "/usr/bin:/bin", "LC_ALL": "C",
           "PYTHONDONTWRITEBYTECODE": "1", "OPENSSL_CONF": "/dev/null"}
    return paths, identities, snapshots, env


def _unchanged_tools(snapshots):
    for path, identity in snapshots.items():
        _read(path, MAX_TOOL, identity)


def _python(tool, *args):
    return [sys.executable, "-B", "-E", "-s", tool, *args]


def _header(data, profile, *, footer_present):
    report = envelope._inspect(memoryview(data))
    header = report["header"]
    expected = profile["boot"]
    _require(header["version"] == expected["header_version"]
             and header["size_bytes"] == expected["header_size_bytes"]
             and header["kernel_size_bytes"] == expected["kernel_size_bytes"]
             and header["boot_signature_size_bytes"] == expected["boot_signature_size_bytes"]
             and header["os_version_raw"] == expected["os_version_raw"]
             and not any(data[44:1580]), "boot header differs from working76")
    _require(report["ramdisk"]["compression"]["format"] == "lz4-legacy", "expected legacy LZ4")
    _require(report["avb"]["footer_present"] is footer_present, "unexpected AVB footer state")
    return report


@_guard
def inspect_image_bytes(data, profile):
    """Exact identity plus structural/hash checks; native RSA verification is separate."""
    _require(type(data) is bytes and 4096 <= len(data) <= MAX_IMAGE, "image must be bounded immutable bytes")
    _matches(data, profile["output"]["image"], "working image")
    report = _header(data, profile, footer_present=True)
    _require(report["ramdisk"]["sha256"] == profile["output"]["ramdisk"]["sha256"]
             and report["ramdisk"]["size_bytes"] == profile["output"]["ramdisk"]["size_bytes"],
             "compressed ramdisk differs")
    avb, contract = report["avb"], profile["avb"]
    meta = avb["vbmeta"]
    payload_end = report["header"]["padded_payload_size_bytes"]
    _require(payload_end == profile["output"]["unsigned_size_bytes"] == avb["original_image_size_bytes"]
             == avb["vbmeta_offset_bytes"], "AVB covers the wrong payload")
    _require(avb["vbmeta_size_bytes"] == contract["vbmeta_size_bytes"] <= 64 * 1024,
             "unexpected vbmeta size")
    for field in ("algorithm_type", "rollback_index", "rollback_index_location", "flags", "required_libavb_version"):
        _require(meta[field] == contract[field], "unexpected AVB " + field)
    blob = data[payload_end:payload_end + avb["vbmeta_size_bytes"]]
    pairs = [struct.unpack_from(">QQ", blob, offset) for offset in range(32, 112, 16)]
    (hash_at, hash_size), (sig_at, sig_size), (key_at, key_size), (pk_at, pk_size), (desc_at, desc_size) = pairs
    auth_size, aux_size = meta["authentication_size_bytes"], meta["auxiliary_size_bytes"]
    _require((auth_size, hash_at, hash_size, sig_at, sig_size) == (576, 0, 32, 32, 512),
             "unexpected RSA4096 authentication layout")
    _require(desc_at == 0 and key_at == desc_size and key_size == contract["public_key_size_bytes"]
             and pk_at == key_at + key_size and pk_size == 0
             and aux_size == (key_at + key_size + 63) // 64 * 64, "unexpected AVB auxiliary layout")
    release = contract["release_string"].encode()
    _require(blob[128:176] == release + bytes(48 - len(release)), "AVB release string differs")
    auth = blob[256:256 + auth_size]
    aux = blob[256 + auth_size:]
    _require(not any(auth[sig_at + sig_size:]) and not any(aux[key_at + key_size:]),
             "nonzero AVB block padding")
    _require(auth[:32] == hashlib.sha256(blob[:256] + aux).digest(), "AVB authentication hash differs")
    key = aux[key_at:key_at + key_size]
    _require(struct.unpack_from(">I", key)[0] == 4096 and _sha(key) == contract["public_key_sha256"],
             "embedded AVB public key differs")
    rows = meta["descriptor_headers"]
    _require(len(rows) == 3 and [row["tag"] for row in rows] == [2, 0, 0], "unexpected AVB descriptors")
    desc = aux[:rows[0]["size_bytes"]]
    _require(len(desc) >= HASH_DESCRIPTOR.size, "short AVB hash descriptor")
    tag, following, image_size, algorithm, name_len, salt_len, digest_len, flags, reserved = HASH_DESCRIPTOR.unpack_from(desc)
    name = contract["partition_name"].encode()
    salt = bytes.fromhex(contract["salt_hex"])
    digest = hashlib.sha256(salt + data[:payload_end]).digest()
    end = HASH_DESCRIPTOR.size + name_len + salt_len + digest_len
    _require(tag == 2 and following + 16 == len(desc) == (end + 7) // 8 * 8
             and image_size == payload_end and algorithm == b"sha256" + bytes(26)
             and (name_len, salt_len, digest_len, flags) == (len(name), 32, 32, 0)
             and not any(reserved), "invalid recovery hash descriptor")
    _require(desc[HASH_DESCRIPTOR.size:end] == name + salt + digest and not any(desc[end:])
             and digest.hex() == contract["digest_hex"], "recovery descriptor salt/digest differs")
    properties, position = {}, len(desc)
    for row in rows[1:]:
        prop = aux[position:position + row["size_bytes"]]
        _require(len(prop) >= 32, "short AVB property")
        tag, following, key_len, value_len = struct.unpack_from(">4Q", prop)
        value_at = 32 + key_len + 1
        value_end = value_at + value_len
        _require(tag == 0 and 0 < key_len <= 128 and 0 < value_len <= 64
                 and (value_end + 1 + 7) // 8 * 8 == len(prop) == following + 16,
                 "invalid AVB property spans")
        key_name = prop[32:32 + key_len].decode("ascii")
        value = prop[value_at:value_end].decode("ascii")
        _require(key_name not in properties and contract["properties"].get(key_name) == value
                 and prop[32 + key_len] == 0 and not any(prop[value_end:]), "AVB property differs")
        properties[key_name] = value
        position += len(prop)
    _require(position == desc_size and properties == contract["properties"], "missing AVB properties")
    return {"header_version": profile["boot"]["header_version"], "kernel_size_bytes": 0,
            "header_size_bytes": 1584, "page_size_bytes": 4096, "command_line": "",
            "os_version_raw": report["header"]["os_version_raw"],
            "ramdisk_size_bytes": report["ramdisk"]["size_bytes"],
            "unsigned_size_bytes": payload_end}


def _public_pem(data):
    _require(len(data) <= 16 * 1024 and b"PRIVATE KEY" not in data
             and (data.startswith(b"-----BEGIN PUBLIC KEY-----\n")
                  or data.startswith(b"-----BEGIN RSA PUBLIC KEY-----\n")),
             "--public-key must be a PEM public key, not a private key or AVB blob")


@_guard
def verify_image(image, *, avbtool, public_key, openssl):
    """Return a verification receipt; only private temporary copies reach native tools."""
    profile, profile_sha = load_profile()
    data = _read(image, MAX_IMAGE, profile["output"]["image"])
    header = inspect_image_bytes(data, profile)
    pem = _read(public_key, 16 * 1024)
    _public_pem(pem)
    records = []
    with _private_creation(), tempfile.TemporaryDirectory(prefix="twrp-working-verify-") as temporary:
        work = Path(temporary).resolve()
        paths, identities, snapshots, env = _prepare_tools(profile, work, avbtool=avbtool, openssl=openssl)
        checked_image, checked_key = work / "recovery.img", work / "input-public.pem"
        normalized, avb_key = work / "public.pem", work / "public.avbpubkey"
        _write(checked_image, data)
        _write(checked_key, pem)
        _run("public-key-parse", [paths["openssl"], "pkey", "-pubin", "-in", checked_key,
                                 "-pubout", "-out", normalized], env, work, records)
        _public_pem(_read(normalized, 16 * 1024))
        _run("public-key-export", _python(paths["avbtool"], "extract_public_key", "--key", normalized,
                                         "--output", avb_key), env, work, records)
        exported = _read(avb_key, 16 * 1024, {"sha256": profile["avb"]["public_key_sha256"],
                                            "size_bytes": profile["avb"]["public_key_size_bytes"]})
        _run("avb-verify", _python(paths["avbtool"], "verify_image", "--image", checked_image,
                                  "--key", normalized), env, work, records)
        _require(_read(checked_image, MAX_IMAGE) == data and _read(checked_key, 16 * 1024) == pem,
                 "verification snapshot changed")
        _unchanged_tools(snapshots)
    _require(_read(image, MAX_IMAGE) == data and _read(public_key, 16 * 1024) == pem,
             "verification input changed")
    avb = profile["avb"]
    return {"schema_version": 1, "status": "verified", "profile_id": profile["profile_id"],
            "profile_sha256": profile_sha, "image": _identity(data), "header": header,
            "avb": {**{name: avb[name] for name in ("algorithm", "partition_name", "rollback_index",
                    "rollback_index_location", "flags")}, "signature_verified": True,
                    "descriptor_verified": True, "oem_trust_established": False},
            "public_key": {"input_sha256": _sha(pem), "avb_sha256": _sha(exported),
                           "avb_size_bytes": len(exported)},
            "tools": identities, "native_results": records, "source_built": False, "device_operations": []}


def _patch_files(cpio, patch, profile):
    """Replay the pinned two additive, full-index hunks without extracting paths."""
    _matches(patch, profile["patch"], "public patch")
    members, _ = _archive(cpio)
    sections = []
    for line in patch.splitlines(keepends=True):
        if line.startswith(b"diff --git "):
            sections.append([])
        _require(bool(sections), "invalid patch prefix")
        sections[-1].append(line)
    replacements = {}
    for lines in sections:
        match = re.fullmatch(rb"diff --git a/(\S+) b/\1\n", lines[0])
        _require(match is not None and len(lines) >= 6, "invalid patch file header")
        name = match[1].decode("ascii")
        _require(name in profile["patch"]["files"] and name not in replacements and name in members,
                 "unexpected or duplicate patch path")
        index = re.fullmatch(rb"index ([0-9a-f]{40})\.\.([0-9a-f]{40})\n", lines[1])
        hunk = re.fullmatch(rb"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", lines[4])
        _require(index is not None and hunk is not None and lines[2] == f"--- a/{name}\n".encode()
                 and lines[3] == f"+++ b/{name}\n".encode(), "unsupported patch shape")
        row = members[name]
        before = cpio[row["offset_bytes"]:row["offset_bytes"] + row["size_bytes"]]
        expected = profile["patch"]["files"][name]
        _require(_sha(before) == expected["before_sha256"], "patch preimage differs")
        old_start, old_count, new_start, new_count = map(int, hunk.groups())
        operations = lines[5:]
        _require(old_start == new_start and all(op[:1] in (b" ", b"+") for op in operations)
                 and sum(op[:1] == b" " for op in operations) == old_count
                 and len(operations) == new_count, "unsupported or malformed patch hunk")
        original = before.splitlines(keepends=True)
        position = old_start - 1
        _require(0 <= position <= len(original), "patch hunk outside file")
        result = original[:position]
        for operation in operations:
            content = operation[1:]
            if operation[:1] == b" ":
                _require(position < len(original) and original[position] == content, "patch context differs")
                position += 1
            result.append(content)
        after = b"".join(result + original[position:])
        for content, expected_blob in ((before, index[1]), (after, index[2])):
            blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest().encode()
            _require(blob == expected_blob, "patch Git blob differs")
        _require(_sha(after) == expected["after_sha256"], "patch postimage differs")
        replacements[name] = before, after
    _require(set(replacements) == set(profile["patch"]["files"]), "missing patch file")
    return replacements


def _overlay_proof(before, after, selected, expected_count):
    old, summary = _archive(before)
    new, new_summary = _archive(after)
    _require(list(old) == list(new) and len(old) == expected_count, "archive membership/order changed")
    old_at = new_at = 0
    for name, row in old.items():
        other = new[name]
        _require({k: v for k, v in row.items() if k not in ("offset_bytes", "size_bytes")}
                 == {k: v for k, v in other.items() if k not in ("offset_bytes", "size_bytes")},
                 "archive member metadata changed")
        old_end = (row["offset_bytes"] + row["size_bytes"] + 3) & ~3
        new_end = (other["offset_bytes"] + other["size_bytes"] + 3) & ~3
        if name not in selected:
            _require(before[old_at:old_end] == after[new_at:new_end], "unselected archive frame changed")
        else:
            _require(before[old_at:old_at + 54] == after[new_at:new_at + 54]
                     and before[old_at + 62:row["offset_bytes"]] == after[new_at + 62:other["offset_bytes"]],
                     "selected archive metadata changed")
        old_at, new_at = old_end, new_end
    _require(before[old_at:] == after[new_at:], "archive trailer changed")
    return {"entry_count": summary["entry_count"], "unchanged_members": len(old) - len(selected),
            "all_other_member_payloads_and_metadata_unchanged": True}


@_guard
def build_recovery(*, baseline_image, key, mkbootimg, avbtool, lz4, openssl, output_dir):
    profile, profile_sha = load_profile()
    baseline = _read(baseline_image, MAX_IMAGE, profile["baseline"]["image"])
    # The exact supplied baseline has an unsigned/stale AVB footer. Its whole
    # image hash admits the source; footer presence does not establish trust.
    original_header = _header(baseline, profile, footer_present=True)
    patch = _read(ROOT / profile["patch"]["path"], MAX_TEXT, profile["patch"])
    key = _path(key)
    key_info = key.lstat()
    _require(stat.S_ISREG(key_info.st_mode) and 0 < key_info.st_size <= 16 * 1024
             and key_info.st_mode & 0o077 == 0, "private key must be a private regular file")
    records = []
    with _private_creation():
        out = _fresh_output(output_dir)
        paths, identities, snapshots, env = _prepare_tools(profile, out, avbtool=avbtool,
                                                          openssl=openssl, mkbootimg=mkbootimg, lz4=lz4)
        public = out / "public-key.pem"
        avb_key = out / "public-key.avbpubkey"
        _run("derive-public-key", [paths["openssl"], "pkey", "-in", key, "-pubout", "-out", public],
             env, out, records)
        _public_pem(_read(public, 16 * 1024))
        _run("export-public-key", _python(paths["avbtool"], "extract_public_key", "--key", public,
                                         "--output", avb_key), env, out, records)
        _read(avb_key, 16 * 1024, {"sha256": profile["avb"]["public_key_sha256"],
                                  "size_bytes": profile["avb"]["public_key_size_bytes"]})
        size = original_header["ramdisk"]["size_bytes"]
        _write(out / "baseline.lz4", baseline[4096:4096 + size])
        _run("decompress-baseline", [paths["lz4"], "-d", out / "baseline.lz4", out / "baseline.cpio"],
             env, out, records, max_file_bytes=profile["baseline"]["cpio"]["size_bytes"])
        cpio = _read(out / "baseline.cpio", MAX_ARCHIVE_BYTES, profile["baseline"]["cpio"])
        replacements = _patch_files(cpio, patch, profile)
        changed = replace_files(cpio, replacements)
        _matches(changed, profile["output"]["cpio"], "patched archive")
        proof = _overlay_proof(cpio, changed, replacements, profile["baseline"]["archive_entries"])
        _write(out / "recovery.cpio", changed)
        _run("compress", [paths["lz4"], "-l", "-12", "--favor-decSpeed", out / "recovery.cpio",
                          out / "recovery.lz4"], env, out, records)
        ramdisk = _read(out / "recovery.lz4", MAX_IMAGE, profile["output"]["ramdisk"])
        _run("compression-roundtrip", [paths["lz4"], "-d", out / "recovery.lz4", out / "roundtrip.cpio"],
             env, out, records, max_file_bytes=profile["output"]["cpio"]["size_bytes"])
        _require(_read(out / "roundtrip.cpio", MAX_ARCHIVE_BYTES) == changed, "LZ4 round trip differs")
        image = out / "recovery.img"
        boot = profile["boot"]
        _run("mkbootimg", _python(paths["mkbootimg"], "--header_version", "4", "--ramdisk", out / "recovery.lz4",
                                 "--cmdline", "", "--os_version", boot["os_version"], "--os_patch_level",
                                 boot["os_patch_level"], "--pagesize", "4096", "--output", image), env, out, records)
        unsigned = _read(image, MAX_IMAGE)
        _header(unsigned, profile, footer_present=False)
        _require(len(unsigned) == profile["output"]["unsigned_size_bytes"]
                 and unsigned[:12] == baseline[:12] and unsigned[16:4096] == baseline[16:4096]
                 and unsigned[4096:4096 + len(ramdisk)] == ramdisk, "mkbootimg changed preserved bytes")
        avb = profile["avb"]
        arguments = _python(paths["avbtool"], "add_hash_footer", "--image", image,
                            "--partition_size", str(avb["partition_size_bytes"]), "--partition_name", "recovery",
                            "--hash_algorithm", "sha256", "--algorithm", avb["algorithm"], "--key", key,
                            "--rollback_index", "1", "--rollback_index_location", "1", "--flags", "0",
                            "--salt", avb["salt_hex"])
        for name, value in avb["properties"].items():
            arguments.extend(("--prop", name + ":" + value))
        _unchanged_tools(snapshots)
        _require(_signature(key.lstat()) == _signature(key_info), "private key changed before signing")
        _run("avb-sign", arguments, env, out, records)
        signed = _read(image, MAX_IMAGE, profile["output"]["image"])
        _require(signed[:len(unsigned)] == unsigned, "signing changed the unsigned payload")
        verification = verify_image(image, avbtool=avbtool, public_key=public, openssl=openssl)
        _require(verification["profile_sha256"] == profile_sha, "profile changed during build")
        _unchanged_tools(snapshots)
        _require(_read(baseline_image, MAX_IMAGE) == baseline and _signature(key.lstat()) == _signature(key_info),
                 "source image or key changed")
        _require(_read(ROOT / profile["patch"]["path"], MAX_TEXT) == patch, "patch changed during build")
        report = {"schema_version": 1, "status": "built_and_verified", "profile_id": profile["profile_id"],
                  "profile_sha256": profile_sha, "image": _identity(signed), "baseline": _identity(baseline),
                  "cpio": _identity(changed), "ramdisk": _identity(ramdisk), "patch": _identity(patch),
                  "archive": proof, "tools": identities, "native_results": records,
                  "verification": verification, "source_built": False, "device_operations": []}
        _save(out / "verification-report.json", verification)
        _save(out / "build-report.json", report)
        _write(out / "SHA256SUMS", (_sha(signed) + "  recovery.img\n").encode())
        for child in out.rglob("*"):
            _require(child.lstat().st_mode & 0o077 == 0, "output permissions are not private")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="show pinned inputs/outputs without native or private input access")
    build = commands.add_parser("build", help="reproduce working76 into a fresh private directory")
    verify = commands.add_parser("verify", help="verify the exact image with the pinned public key and native tools")
    for command in (build, verify):
        command.add_argument("--local-config", type=Path)
        for name in ("avbtool", "openssl"):
            command.add_argument("--" + name, type=Path)
    for name in ("baseline-image", "key", "mkbootimg", "lz4"):
        build.add_argument("--" + name, type=Path)
    build.add_argument("--output-dir", type=Path, required=True)
    verify.add_argument("--image", type=Path, required=True)
    verify.add_argument("--public-key", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            report = plan()
        else:
            needed = ("baseline_image", "key", "mkbootimg", "avbtool", "lz4", "openssl") if args.command == "build" else ("avbtool", "public_key", "openssl")
            values = resolve_paths(args.local_config, {name: getattr(args, name) for name in needed})
            if args.command == "build":
                report = build_recovery(**values, output_dir=args.output_dir)
            else:
                report = verify_image(args.image, **values)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (TwrpWorkingError, OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        # Native stdout, private paths, and key contents never enter public diagnostics.
        message = str(exc) if isinstance(exc, TwrpWorkingError) else "invalid or unavailable input"
        print("twrp_working: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
