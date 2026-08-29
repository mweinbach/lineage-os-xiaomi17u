#!/usr/bin/env python3
"""Stage the exact working76 recovery for the patched Evolution build consumer.

This does not build a ROM, authorize an OTA/flash, or establish compatibility
with newly built Android companion images. AVB verification uses an explicit
public key through twrp_working; no signing key or device is used.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

if __package__:
    from .kernel_inputs import KernelInputsError, _json, _read, _relative
else:
    from kernel_inputs import KernelInputsError, _json, _read, _relative


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = "config/twrp-working.json"
SOURCE_CONTRACT_PATH = "patches/evolution/prebuilt-recovery.json"
PATCH_PATH = "patches/evolution/0005-verified-prebuilt-recovery.patch"
CORE_PATH = "build/make/core/Makefile"
COMMON_PATH = "build/make/tools/releasetools/common.py"
BUILD_COMMIT = "a438ca40c6ed779042f806142b1165ba1360a7b2"
PROFILE_ID = "nezha-working76"
BUNDLE_PATH = "vendor/xiaomi/nezha-recovery"
BUNDLE_SCHEMA_VERSION = 2
PUBLIC_KEY_MEMBER = "recovery-public.pem"
BUNDLE_FILES = {"recovery.img", "receipt.json", "recovery-inputs.mk", PUBLIC_KEY_MEMBER}
EXPECTED_IMAGE = {"sha256": "a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e", "size_bytes": 104857600}
EXPECTED_KEY = "020d7559b8ddedf153e77cc4a02af26c666e3746408a230650ef8cd1e8f09b03"
EXPECTED_PUBLIC_KEY_SHA256 = "50784f7b5ccd4cfde172f5cbce06f54e33547d1081c7d28b55e494aa37ab0967"
MAX_TEXT_BYTES = 4 * 1024**2
MAX_PUBLIC_KEY_BYTES = 16 * 1024
SCOPE = {"complete_target_files_allowed": False, "ota_allowed": False, "super_allowed": False,
         "flash_allowed": False, "full_rom_verified": False, "evolution_companion_boot_chain_verified": False,
         "normal_android_selinux_changed": False, "device_operations": []}


class RecoveryInputsError(ValueError):
    """A recovery image, verification result, source patch, or bundle mismatched."""


def _require(condition, message):
    if not condition:
        raise RecoveryInputsError(message)


def _canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _identity(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def _valid_identity(value):
    return (type(value) is dict and type(value.get("sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
            and type(value.get("size_bytes")) is int and value["size_bytes"] > 0)


def _contracts(composed_source_contract=None):
    profile_bytes = _read(ROOT / PROFILE_PATH, limit=MAX_TEXT_BYTES)
    profile = _json(profile_bytes)
    _require(type(profile.get("schema_version")) is int and profile["schema_version"] == 1
             and profile.get("profile_id") == PROFILE_ID and type(profile.get("output")) is dict
             and profile["output"].get("image") == EXPECTED_IMAGE,
             "working76 profile must retain the exact reviewed recovery image")
    source_bytes = _read(ROOT / SOURCE_CONTRACT_PATH, limit=MAX_TEXT_BYTES)
    source = _json(source_bytes)
    _require(type(source.get("schema_version")) is int and source["schema_version"] == 1
             and type(source.get("project")) is dict and source["project"].get("path") == "build/make"
             and source["project"].get("commit") == BUILD_COMMIT, "unexpected Evolution source contract")
    _require(type(source.get("patch")) is dict and source["patch"].get("path") == PATCH_PATH,
             "unexpected recovery source patch path")
    patch = _read(ROOT / PATCH_PATH, limit=MAX_TEXT_BYTES)
    _require(_identity(patch) == {k: source["patch"].get(k) for k in ("sha256", "size_bytes")},
             "recovery source patch differs from its reviewed contract")
    _require(type(source.get("source_files")) is list and len(source["source_files"]) == 1
             and type(source["source_files"][0]) is dict
             and source["source_files"][0].get("path") == CORE_PATH, "expected one recovery build-core change")
    row = source["source_files"][0]
    _require(_valid_identity(row.get("before")) and _valid_identity(row.get("after"))
             and row["before"] != row["after"], "invalid prebuilt-recovery source identities")
    semantic = source.get("semantic_files")
    _require(type(semantic) is list and semantic and all(type(r) is dict for r in semantic),
             "missing pinned releasetools semantics")
    paths = [r.get("path") for r in semantic]
    _require(all(type(path) is str for path in paths) and COMMON_PATH in paths
             and len(paths) == len(set(paths)), "missing or duplicate releasetools source")
    for row in semantic:
        _require(type(row.get("path")) is str and _relative(row["path"]).startswith("build/make/")
                 and _valid_identity({k: row.get(k) for k in ("sha256", "size_bytes")}),
                 "invalid releasetools source identity")
    identity = _identity(source_bytes)
    if composed_source_contract is not None:
        if __package__:
            from .recovery_source_contracts import compose
        else:
            from recovery_source_contracts import compose
        source, identity = compose(ROOT, composed_source_contract,
                                   expected_base=source, expected_base_identity=identity)
    return _identity(profile_bytes), source, identity


def _source_check(source_tree, source, contract_identity):
    rows = [{"path": row["path"], **row["after"]} for row in source["source_files"]] + source["semantic_files"]
    checked = []
    for row in rows:
        data = _read(Path(source_tree) / row["path"], limit=MAX_TEXT_BYTES)
        identity = _identity(data)
        _require(identity == {k: row[k] for k in ("sha256", "size_bytes")},
                 f"required prebuilt-recovery patch or pinned semantics not present: {row['path']}")
        checked.append({"path": row["path"], **identity})
    result = {"expected_project_commit": BUILD_COMMIT, "contract": contract_identity,
              "files": checked, "selected_source_bytes_verified": True, "whole_source_tree_verified": False}
    if "composition" in source:
        result["composition"] = copy.deepcopy(source["composition"])
    return result


def _native_verify(image, *, avbtool, public_key, openssl):
    if __package__:
        from .twrp_working import verify_image
    else:
        from twrp_working import verify_image
    return verify_image(Path(image), avbtool=Path(avbtool), public_key=Path(public_key), openssl=Path(openssl))


def _tool_paths(local_config, explicit):
    if __package__:
        from .twrp_working import resolve_paths
    else:
        from twrp_working import resolve_paths
    # Never resolve or open the signing-key entry from a builder configuration.
    return resolve_paths(local_config, explicit)


def _verification(report, profile):
    _require(type(report) is dict and type(report.get("schema_version")) is int and report["schema_version"] == 1
             and report.get("status") == "verified" and report.get("profile_id") == PROFILE_ID
             and report.get("profile_sha256") == profile["sha256"] and report.get("image") == EXPECTED_IMAGE,
             "working recovery verification did not verify the exact current profile/image")
    header = report.get("header", {})
    _require(type(header) is dict and type(header.get("header_version")) is int and header["header_version"] == 4
             and type(header.get("kernel_size_bytes")) is int and header["kernel_size_bytes"] == 0,
             "recovery must be dedicated kernel-free header v4")
    avb = report.get("avb", {})
    _require(type(avb) is dict and avb.get("algorithm") == "SHA256_RSA4096" and avb.get("partition_name") == "recovery"
             and all(type(avb.get(k)) is int and avb[k] == v for k, v in
                     (("rollback_index", 1), ("rollback_index_location", 1), ("flags", 0)))
             and avb.get("signature_verified") is True and avb.get("descriptor_verified") is True
             and avb.get("oem_trust_established") is False, "explicit recovery AVB verification is required")
    key = report.get("public_key", {})
    _require(type(key) is dict and key.get("avb_sha256") == EXPECTED_KEY
             and type(key.get("avb_size_bytes")) is int and key["avb_size_bytes"] == 1032
             and key.get("input_sha256") == EXPECTED_PUBLIC_KEY_SHA256,
             "recovery verification used an unexpected public key")
    _require(type(report.get("tools")) is dict and all(_valid_identity(report["tools"].get(name))
             for name in ("avbtool", "openssl")), "verification tool identities are missing")
    _require(report.get("device_operations") == [] and report.get("source_built") is False,
             "staging verification cannot claim device operations or a source build")
    return report


def _make_include(receipt_bytes, profile, source):
    core = source["source_files"][0]["after"]
    values = {"SCHEMA_VERSION": str(BUNDLE_SCHEMA_VERSION), "IMAGE_SHA256": EXPECTED_IMAGE["sha256"],
              "IMAGE_SIZE": str(EXPECTED_IMAGE["size_bytes"]), "PROFILE_SHA256": profile["sha256"],
              "RECEIPT_SHA256": _identity(receipt_bytes)["sha256"], "CORE_SHA256": core["sha256"],
              "PUBLIC_KEY_SHA256": EXPECTED_PUBLIC_KEY_SHA256, "AVB_PUBLIC_KEY_SHA256": EXPECTED_KEY}
    if "composition_identity" in source:
        values["CORE_COMPOSITION_SHA256"] = source["composition_identity"]["sha256"]
    return ("# Generated by recovery_inputs.py; private verified working76 bundle.\n"
            + "".join(f"NEZHA_RECOVERY_{key} := {value}\n" for key, value in values.items())).encode("ascii")


def _receipt(verification, profile, source_check, public_key):
    return copy.deepcopy({"schema_version": BUNDLE_SCHEMA_VERSION, "operation": "stage-nezha-recovery-inputs", "profile_id": PROFILE_ID,
            "profile": profile, "image": EXPECTED_IMAGE, "build_source": source_check,
            "public_key": public_key, "verification": verification, "scope": SCOPE})


def _bundle_path(path):
    path = Path(os.path.abspath(path))
    _require(path.parts[-3:] == ("vendor", "xiaomi", "nezha-recovery"),
             "bundle must be the private vendor/xiaomi/nezha-recovery directory")
    return path


@contextmanager
def _directory_fd(path, *, create=False):
    """Traverse real directories, optionally creating missing private parents."""
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(os.path.abspath(path)).parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def _file_signature(details):
    return (details.st_dev, details.st_ino, details.st_mode, details.st_nlink,
            details.st_size, details.st_mtime_ns, details.st_ctime_ns)


def _read_at(directory, name, limit, *, private=True):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, "rb") as stream:
        details = os.fstat(stream.fileno())
        _require(stat.S_ISREG(details.st_mode) and details.st_nlink == 1
                 and (not private or stat.S_IMODE(details.st_mode) in (0o400, 0o600)),
                 "expected a regular file with one link and required bundle privacy")
        _require(details.st_size <= limit, "bundle member exceeds size bound")
        signature = _file_signature(details)
        data = stream.read(limit + 1)
        _require(len(data) <= limit and signature == _file_signature(os.fstat(stream.fileno()))
                 and signature == _file_signature(os.stat(name, dir_fd=directory, follow_symlinks=False)),
                 "bundle member changed while read")
    return data, signature


def _public_key_identity(data):
    _require(0 < len(data) <= MAX_PUBLIC_KEY_BYTES and b"PRIVATE KEY" not in data
             and (data.startswith(b"-----BEGIN PUBLIC KEY-----\n")
                  or data.startswith(b"-----BEGIN RSA PUBLIC KEY-----\n"))
             and _identity(data)["sha256"] == EXPECTED_PUBLIC_KEY_SHA256,
             "public PEM bytes do not match the verified working76 public key")
    return {"path": PUBLIC_KEY_MEMBER, **_identity(data)}


def _read_public_key(path):
    path = Path(os.path.abspath(path))
    with _directory_fd(path.parent) as directory:
        details = os.fstat(directory)
        data, _ = _read_at(directory, path.name, MAX_PUBLIC_KEY_BYTES, private=False)
        with _directory_fd(path.parent) as current:
            now = os.fstat(current)
            _require((details.st_dev, details.st_ino) == (now.st_dev, now.st_ino), "public-key directory was replaced")
    return data, _public_key_identity(data)


def _read_bundle(bundle, profile, source, source_check):
    with _directory_fd(bundle) as directory:
        details = os.fstat(directory)
        _require(stat.S_IMODE(details.st_mode) == 0o700, "recovery bundle directory must have mode 0700")
        _require(set(os.listdir(directory)) == BUNDLE_FILES,
                 "schema2 recovery bundle requires the exact four files including recovery-public.pem; restage old bundles")
        limits = {"recovery.img": EXPECTED_IMAGE["size_bytes"], PUBLIC_KEY_MEMBER: MAX_PUBLIC_KEY_BYTES}
        read = {name: _read_at(directory, name, limits.get(name, MAX_TEXT_BYTES))
                for name in sorted(BUNDLE_FILES)}
        _require(_file_signature(details) == _file_signature(os.fstat(directory))
                 and set(os.listdir(directory)) == BUNDLE_FILES
                 and all(signature == _file_signature(os.stat(name, dir_fd=directory, follow_symlinks=False))
                         for name, (_, signature) in read.items()), "bundle changed during readback")
        with _directory_fd(bundle) as current:
            _require(_file_signature(details) == _file_signature(os.fstat(current)), "bundle directory was replaced")
    image = read["recovery.img"][0]
    _require(_identity(image) == EXPECTED_IMAGE, "staged recovery image hash or size differs from working76")
    public_key = _public_key_identity(read[PUBLIC_KEY_MEMBER][0])
    receipt_bytes = read["receipt.json"][0]
    receipt = _json(receipt_bytes)
    verification = _verification(receipt.get("verification"), profile)
    _require(receipt_bytes == _canonical(_receipt(verification, profile, source_check, public_key)),
             "recovery receipt identity, public key or scope changed")
    include = read["recovery-inputs.mk"][0]
    _require(include == _make_include(receipt_bytes, profile, source), "recovery Make include differs from verified receipt")
    return {"image": EXPECTED_IMAGE.copy(), "public_key": public_key,
            "receipt": _identity(receipt_bytes), "make_include": _identity(include)}


def plan(*, composed_source_contract=None):
    profile, source, contract = _contracts(composed_source_contract)
    result = {"schema_version": BUNDLE_SCHEMA_VERSION, "operation": "plan-nezha-recovery-inputs", "profile_id": PROFILE_ID,
            "profile": profile, "image": EXPECTED_IMAGE, "bundle": BUNDLE_PATH,
            "public_key": {"path": PUBLIC_KEY_MEMBER, "sha256": EXPECTED_PUBLIC_KEY_SHA256, "avb_sha256": EXPECTED_KEY,
                           "format": "PEM public key", "native_verification_required": True, "private_key_included": False},
            "required_files": sorted(BUNDLE_FILES), "source_contract": contract,
            "expected_source_files": [{"path": r["path"], **r["after"]} for r in source["source_files"]],
            "image_verified": False, "source_patch_applied": False, "scope": SCOPE}
    if "composition" in source:
        result["source_composition"] = source["composition"]
    return copy.deepcopy(result)


def stage_inputs(image, output_dir, *, source_tree, avbtool, public_key, openssl,
                 composed_source_contract=None):
    profile, source, contract = _contracts(composed_source_contract)
    source_check = _source_check(source_tree, source, contract)
    bundle = _bundle_path(output_dir)
    _require(not os.path.lexists(bundle), "recovery bundle already exists; verify it or choose a new source checkout")
    data = _read(Path(image), limit=EXPECTED_IMAGE["size_bytes"])
    _require(_identity(data) == EXPECTED_IMAGE, "input recovery image hash or size differs from working76")
    key_data, key_identity = _read_public_key(public_key)
    verification = _verification(_native_verify(image, avbtool=avbtool, public_key=public_key, openssl=openssl), profile)
    _require(_read(Path(image), limit=EXPECTED_IMAGE["size_bytes"]) == data, "input recovery changed during verification")
    _require(_read_public_key(public_key) == (key_data, key_identity), "input public key changed during verification")
    _require(_contracts(composed_source_contract) == (profile, source, contract),
             "recovery control contracts changed during verification")
    receipt_bytes = _canonical(_receipt(verification, profile, source_check, key_identity))
    payloads = {"recovery.img": data, "receipt.json": receipt_bytes,
                PUBLIC_KEY_MEMBER: key_data,
                "recovery-inputs.mk": _make_include(receipt_bytes, profile, source)}
    with _directory_fd(bundle.parent, create=True) as parent:
        os.mkdir(bundle.name, 0o700, dir_fd=parent)
        directory = os.open(bundle.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            os.fchmod(directory, 0o700)
            for name, content in payloads.items():
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
                with os.fdopen(fd, "wb") as stream:
                    os.fchmod(stream.fileno(), 0o600)
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.fsync(directory)
        finally:
            os.close(directory)
    _require(_source_check(source_tree, source, contract) == source_check, "Evolution source changed during staging")
    _require(_contracts(composed_source_contract) == (profile, source, contract),
             "recovery control contracts changed during staging")
    checked = _read_bundle(bundle, profile, source, source_check)
    return {"schema_version": BUNDLE_SCHEMA_VERSION, "operation": "stage-nezha-recovery-inputs", "status": "staged",
            "profile_id": PROFILE_ID, "bundle": BUNDLE_PATH, "files": checked,
            "readback_verified": True, "verification": verification, "scope": copy.deepcopy(SCOPE)}


def verify_bundle(bundle, *, source_tree, avbtool, public_key, openssl,
                  composed_source_contract=None):
    profile, source, contract = _contracts(composed_source_contract)
    source_check = _source_check(source_tree, source, contract)
    bundle = _bundle_path(bundle)
    before = _read_bundle(bundle, profile, source, source_check)
    key_data, key_identity = _read_public_key(public_key)
    _require(key_identity == before["public_key"], "explicit public key differs from the staged recovery chain key")
    verification = _verification(_native_verify(bundle / "recovery.img", avbtool=avbtool,
                                                public_key=bundle / PUBLIC_KEY_MEMBER, openssl=openssl), profile)
    _require(_source_check(source_tree, source, contract) == source_check
             and _read_public_key(public_key) == (key_data, key_identity)
             and _read_bundle(bundle, profile, source, source_check) == before,
             "recovery bundle or selected source changed during verification")
    _require(_contracts(composed_source_contract) == (profile, source, contract),
             "recovery control contracts changed during verification")
    return {"schema_version": BUNDLE_SCHEMA_VERSION, "operation": "verify-nezha-recovery-inputs", "status": "verified",
            "profile_id": PROFILE_ID, "bundle": BUNDLE_PATH, "files": before,
            "readback_verified": True, "verification": verification, "scope": copy.deepcopy(SCOPE)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--composed-source-contract", type=Path,
                             help="explicit reviewed 0007, 0009, base 0010 or combined 0011 composition; omission retains the 0005-only contract")
    for command in ("stage", "verify"):
        sub = commands.add_parser(command)
        sub.add_argument("--source-tree", type=Path, required=True)
        sub.add_argument("--composed-source-contract", type=Path,
                         help="explicit reviewed 0007, 0009, base 0010 or combined 0011 composition; omission retains the 0005-only source contract")
        sub.add_argument("--local-config", type=Path, help="optional path-only tool/public-key defaults; signing keys are not used")
        for name in ("avbtool", "public-key", "openssl"):
            sub.add_argument("--" + name, type=Path)
        if command == "stage":
            sub.add_argument("--image", type=Path, required=True)
            sub.add_argument("--output-dir", type=Path, required=True)
        else:
            sub.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan(composed_source_contract=args.composed_source_contract)
        else:
            options = _tool_paths(args.local_config, {name: getattr(args, name) for name in ("avbtool", "public_key", "openssl")})
            options["source_tree"] = args.source_tree
            if args.composed_source_contract is not None:
                options["composed_source_contract"] = args.composed_source_contract
            result = (stage_inputs(args.image, args.output_dir, **options) if args.command == "stage"
                      else verify_bundle(args.bundle, **options))
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (RecoveryInputsError, KernelInputsError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"recovery inputs refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
