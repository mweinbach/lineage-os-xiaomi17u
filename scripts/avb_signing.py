#!/usr/bin/env python3
"""Prepare and, only when explicitly invoked, sign new Nezha AVB derivatives.

Planning never opens local signing configuration. Preparation uses public keys
only. Signing runs solely on the pinned Mac host and delegates private-key reads
to native tools without copying or printing the key. No device commands exist.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import struct
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True

if __package__:
    from . import avb_image_set as avb
    from . import twrp_working as io
else:
    import avb_image_set as avb
    import twrp_working as io


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-avb-signing.json"
CONTRACT_ID = "nezha-host-avb-signing-v1"
INPUTS = avb.PARTITIONS - {"vbmeta", "vbmeta_system"}
MAX_TEXT = 1024 * 1024
SECRET_LABEL = "<private-key-from-existing-local-recovery-config>"


class AvbSigningError(ValueError):
    """A reviewed preparation or signing prerequisite is not satisfied."""


def _require(condition, message):
    if not condition:
        raise AvbSigningError(message)


def _identity(path, maximum):
    digest, count = hashlib.sha256(), 0
    with avb._input(path, maximum) as (stream, _):
        for chunk in iter(lambda: stream.read(avb.CHUNK), b""):
            digest.update(chunk)
            count += len(chunk)
    return {"sha256": digest.hexdigest(), "size_bytes": count}


def _json_file(path, maximum, expected=None):
    # Read one byte at a time until the object opener. A PEM selected by mistake
    # is rejected on its first '-' without buffering any private-key payload.
    with avb._input(path, maximum) as (stream, info):
        prefix = bytearray()
        while len(prefix) < min(info.st_size, 4096):
            first = stream.read(1)
            prefix.extend(first)
            if first not in (b" ", b"\t", b"\r", b"\n"):
                break
        _require(prefix[-1:] == b"{", "expected a JSON object; unrelated file payloads are not read")
        raw = bytes(prefix) + stream.read(info.st_size + 1)
        _require(len(raw) == info.st_size, "JSON input size changed")
    if expected is not None:
        _require(avb._identity(raw) == {key: expected[key] for key in ("sha256", "size_bytes")},
                 "JSON input identity differs")
    return raw


def load_contract():
    raw = _json_file(CONTRACT, MAX_TEXT)
    contract = avb._json(raw)
    avb._keys(contract, ("schema_version", "contract_id", "device", "platform", "verifier_profile",
                        "implementation_dependencies", "source_evidence", "input_partitions", "key_roles",
                        "new_avb_key_required", "public_key", "avb_public_key_sha256", "accepted_input_boot_keys",
                        "raw_descriptor_sources", "factory_vbmeta_identity", "root_direct_import_order",
                        "system_import_order", "native_release_string", "native_padding_size", "vbmeta_output_size",
                        "signing_platform", "reproduction", "output_root", "limits"), "signing contract")
    _require(type(contract["schema_version"]) is int and contract["schema_version"] == 1
             and contract["contract_id"] == CONTRACT_ID and contract["device"] == "nezha"
             and contract["platform"] == {"branch": "bka", "release_config": "bp4a"},
             "unsupported signing contract")
    profile, profile_sha = avb.load_profile()
    _require(contract["verifier_profile"]["sha256"] == profile_sha
             == "c5dbd4055c904422581ad511d34ba143672683a54aea3390c0581a4af321ba37",
             "the immutable AVB verifier contract changed")
    _require(contract["verifier_profile"]["path"] == "config/nezha-avb-image-set.json"
             and type(contract["implementation_dependencies"]) is list
             and len(contract["implementation_dependencies"]) == 3
             and {r["path"] for r in contract["implementation_dependencies"]} == {
                 "scripts/avb_image_set.py", "scripts/twrp_working.py", "scripts/inspect_twrp_image.py"}
             and type(contract["source_evidence"]) is list and len(contract["source_evidence"]) == 2
             and {r["path"] for r in contract["source_evidence"]} == {
                 "research/factory-firmware-validation.json", "config/twrp-working.json"},
             "signing implementation or evidence dependency coverage changed")
    evidence = {}
    for row in (contract["implementation_dependencies"] + contract["source_evidence"]
                + [contract["verifier_profile"]]):
        avb._identity_spec(row, path=True)
        _require(not Path(row["path"]).is_absolute() and ".." not in Path(row["path"]).parts,
                 "unsafe contract dependency path")
        data = avb._small(ROOT / row["path"], MAX_TEXT, row)
        if row in contract["source_evidence"]:
            evidence[row["path"]] = avb._json(data)
    _require(contract["input_partitions"] == sorted(INPUTS)
             and contract["key_roles"] == {p: "existing-working76-development-key" for p in avb.SIGNED}
             and contract["new_avb_key_required"] is False
             and contract["public_key"] == profile["working76"]["public_pem"]
             and contract["avb_public_key_sha256"] == profile["working76"]["avb_public_key_sha256"],
             "key roles or input coverage changed")
    factory = evidence["research/factory-firmware-validation.json"]
    _require(contract["accepted_input_boot_keys"] == [contract["avb_public_key_sha256"],
             *profile["forbidden_public_key_sha256"],
             factory["avb"]["embedded_signatures"]["boot"]["embedded_key_sha256"]],
             "boot input key classes differ from the recorded sources")
    factory_images = {row["path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                      for row in factory["user_extracted_images"]["images"]}
    avb._identity_spec(contract["factory_vbmeta_identity"])
    _require(contract["factory_vbmeta_identity"] == factory_images["vbmeta.img"],
             "factory descriptor provenance differs")
    _require(contract["root_direct_import_order"] == ["countrycode", "dtbo", "init_boot", "pvmfw",
             "vendor_boot", "mi_ext", "odm", "system_dlkm", "vendor", "vendor_dlkm"]
             and contract["system_import_order"] == ["system", "system_ext", "product"]
             and contract["native_padding_size"] == 4096 and type(contract["native_padding_size"]) is int
             and contract["vbmeta_output_size"] == 65536 and type(contract["vbmeta_output_size"]) is int
             and contract["native_release_string"] == "avbtool 1.3.0"
             and contract["reproduction"] == {"passes": 2, "compare_images": ["boot", "vbmeta_system", "vbmeta"]}
             and contract["signing_platform"] == {"system": "Darwin", "machine": "arm64"}
             and contract["output_root"] == "artifacts/avb/nezha", "unreviewed signing recipe")
    limit_names = {"private_keys_in_guest", "key_generation", "apk_apex_ota_signing", "logical_filesystem_rebuild",
                   "hashtree_or_fec_regeneration", "device_operations", "complete_rom_ready",
                   "device_rollback_compatibility_verified", "physical_partition_fit_verified",
                   "oem_trust_established", "factory_package_origin_verified"}
    _require(type(contract["limits"]) is dict and set(contract["limits"]) == limit_names
             and all(value is False for value in contract["limits"].values()),
             "signing contract exceeds the reviewed evidence scope")
    _require(set(contract["raw_descriptor_sources"]) == {"countrycode", "pvmfw"},
             "raw descriptor coverage changed")
    for name, size in (("countrycode", 32), ("pvmfw", 778240)):
        row = contract["raw_descriptor_sources"][name]
        avb._keys(row, ("image", "descriptor"), "raw firmware source")
        avb._identity_spec(row["image"])
        _require(row["image"] == factory_images[name + ".img"], "raw firmware identity differs from its source")
        desc = row["descriptor"]
        avb._keys(desc, ("encoded_sha256", "size_bytes", "kind", "image_size", "partition",
                        "hash_algorithm", "salt_hex", "digest_hex", "flags"), "raw firmware descriptor")
        _require(desc["partition"] == name and desc["image_size"] == size and desc["flags"] == 0
                 and type(desc["flags"]) is int and type(desc["image_size"]) is int
                 and desc["size_bytes"] == 208 and type(desc["size_bytes"]) is int
                 and desc["kind"] == "hash" and desc["hash_algorithm"] == "sha256",
                 "unreviewed raw descriptor")
        for field in ("encoded_sha256", "digest_hex", "salt_hex"):
            avb._digest(desc[field])
    return contract, avb._sha(raw), profile, profile_sha


def load_input(path, expected_sha, contract, contract_sha, profile):
    avb._digest(expected_sha)
    path = avb.envelope._absolute_path(path)
    raw = _json_file(path, MAX_TEXT)
    _require(avb._sha(raw) == expected_sha, "input manifest digest differs")
    value = avb._json(raw)
    avb._keys(value, ("schema_version", "contract_id", "contract_sha256", "artifact_set_id",
                      "images", "source_records"), "signing input manifest")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and value["contract_id"] == CONTRACT_ID and value["contract_sha256"] == contract_sha,
             "input signing contract differs")
    _require(type(value["artifact_set_id"]) is str and avb.re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value["artifact_set_id"]), "invalid artifact set id")
    _require(type(value["images"]) is dict and set(value["images"]) <= INPUTS,
             "unexpected input image role; old vbmeta images are never imported")
    _require(type(value["source_records"]) is list and len(value["source_records"]) <= 64,
             "invalid source provenance records")
    for name, row in value["images"].items():
        avb._identity_spec(row, path=True)
        avb.validate_image_budget(profile, name, row)
        required = (profile["working76"]["image"] if name == "recovery" else
                    contract["raw_descriptor_sources"].get(name, {}).get("image"))
        if required:
            _require({k: row[k] for k in ("sha256", "size_bytes")} == required,
                     "retained recovery/raw firmware identity differs")
        row["path"] = avb.envelope._absolute_path(path.parent / row["path"])
    for row in value["source_records"]:
        avb._identity_spec(row, path=True)
        _require(row["size_bytes"] <= MAX_TEXT and Path(row["path"]).suffix == ".json",
                 "provenance must be bounded JSON records, not images or keys")
        row["path"] = avb.envelope._absolute_path(path.parent / row["path"])
    _require(sum(value["images"][p]["size_bytes"] for p in avb.LOGICAL & set(value["images"]))
             <= profile["logical_group_budget"], "logical group exceeds package budget")
    return value, raw


def _base(contract_sha, profile_sha, artifact_id):
    return {"schema_version": 1, "contract_id": CONTRACT_ID, "contract_sha256": contract_sha,
            "verifier_profile_sha256": profile_sha, "artifact_set_id": artifact_id,
            "workflow": _identity(ROOT / "scripts/avb_signing.py", MAX_TEXT),
            "complete_rom_ready": False, "device_operations": [], "keys_generated": False,
            "private_key_copied": False, "private_key_payload_read_by_python": False,
            "guest_accessed": False, "oem_trust_established": False,
            "device_rollback_compatibility_verified": False, "physical_partition_fit_verified": False,
            "apk_apex_ota_signing_performed": False, "fec_payload_verified": False}


def plan(manifest_path, expected_sha):
    contract, digest, profile, profile_sha = load_contract()
    value, _ = load_input(manifest_path, expected_sha, contract, digest, profile)
    missing = sorted(INPUTS - set(value["images"]))
    ready = not missing and bool(value["source_records"])
    return {**_base(digest, profile_sha, value["artifact_set_id"]), "operation": "plan",
            "status": "ready_for_public_preparation" if ready else "blocked",
            "missing_partitions": missing, "provenance_records_supplied": len(value["source_records"]),
            "key_roles": contract["key_roles"], "new_avb_key_required": False,
            "native_commands_run": False, "private_key_accessed": False,
            "signing_performed": False, "complete_chain_verified": False,
            "recipe": ["Verify all 15 sealed input images and public-key provenance.",
                       "Preserve working76 and all direct leaf bytes.",
                       "Re-sign only a fresh boot payload copy, preserving salt and properties.",
                       "Create vbmeta_system from its three exact leaves.",
                       "Create vbmeta from ten exact leaves plus three explicit key/rollback chains.",
                       "Repeat the three signed derivatives and compare their complete bytes.",
                       "Verify the complete 17-image output against intended public keys."]}


def _local(path, contract):
    path = avb.envelope._absolute_path(path)
    raw = _json_file(path, 16 * 1024)
    config = avb._json(raw)
    _require(type(config) is dict and set(config) <= io.LOCAL_FIELDS
             and {"key", "public_key", "openssl"} <= set(config), "existing recovery config is incomplete")
    for value in config.values():
        _require(type(value) is str and 0 < len(value) <= 4096 and value.isprintable()
                 and "PRIVATE KEY" not in value, "local configuration accepts paths only")
    private = avb.envelope._absolute_path(path.parent / config["key"])
    public = avb.envelope._absolute_path(path.parent / config["public_key"])
    openssl = avb.envelope._absolute_path(path.parent / config["openssl"])
    _private_collision(private, path, public, openssl)
    pem = avb._public_pem(public, contract["public_key"])
    return {"config_path": path, "config_identity": avb._identity(raw), "public_path": public,
            "public_bytes": pem, "openssl": openssl,
            "private_selector": config["key"]}  # Normalized only for collisions; never followed or read in prepare.


def _private_path(local):
    # abspath is text normalization only: no resolve(), stat(), or open().
    return avb.envelope._absolute_path(local["config_path"].parent / local["private_selector"])


def _private_collision(private, *paths):
    def normalized(path):
        return unicodedata.normalize("NFD", str(avb.envelope._absolute_path(path))).casefold()
    _require(all(normalized(path) != normalized(private) for path in paths),
             "a public input or tool selector collides with the private signing selector")


def _tool_for_public_read(path, profile, name, protected_key=None):
    """Admit exact-size regular tool files before the generic helper reads bytes.

    Homebrew aliases are allowed, but each selected symlink target is compared
    with the private selector before it is followed. Hardlinks are never read.
    This is accidental-misselection protection, not a hostile same-UID sandbox.
    """
    path = avb.envelope._absolute_path(path)
    expected = (profile["tools"][name]["binaries"] if name == "openssl"
                else [profile["tools"][name]])
    for _ in range(40):
        if protected_key is not None:
            _private_collision(protected_key, path)
        path = path.parent.resolve(strict=True) / path.name
        if protected_key is not None:
            _private_collision(protected_key, path)
        with avb.envelope._parent_directory(path) as parent:
            info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                path = avb.envelope._absolute_path(path.parent / os.readlink(path.name, dir_fd=parent))
                continue
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                 and info.st_size in {row["size_bytes"] for row in expected},
                 "native tool must be a singly linked file of an approved exact size")
        return path
    raise AvbSigningError("native tool symlink chain exceeds bound")


def _key_state(path):
    # Metadata only. The actual key is opened solely by the pinned native tools
    # during the explicit sign operation; it is never copied to a work directory.
    path = avb.envelope._absolute_path(path)
    with avb.envelope._parent_directory(path) as parent:
        info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
             and stat.S_IMODE(info.st_mode) in (0o400, 0o600) and 0 < info.st_size <= 16 * 1024,
             "private key must be an owner-only regular file without links")
    return avb._signature(info)


def _fresh_output(value, contract):
    path = avb.envelope._absolute_path(value)
    allowed = ROOT / contract["output_root"]
    _require(path.is_relative_to(allowed) and path != allowed,
             "output must be a new ignored artifacts/avb/nezha child directory")
    return io._fresh_output(path)


class Native:
    def __init__(self, work, profile, avbtool, openssl, *, protected_key=None):
        self.work = work
        avbtool = _tool_for_public_read(avbtool, profile, "avbtool", protected_key)
        openssl = _tool_for_public_read(openssl, profile, "openssl", protected_key)
        self.paths, self.identities, originals, self.env = io._prepare_tools(
            profile, work, avbtool=avbtool, openssl=openssl)
        self.checks = {p: (i, avb._file_signature(p, io.MAX_TOOL)) for p, i in originals.items()}
        self.checks.update({p: (self.identities[n], avb._file_signature(p, io.MAX_TOOL))
                            for n, p in self.paths.items()})
        self.records = []
        self.private_key = None
        self.private_state = None

    def check(self):
        for path, (identity, signature) in self.checks.items():
            avb._rehash(path, identity, signature)
        if self.private_key is not None:
            _require(_key_state(self.private_key) == self.private_state, "private key metadata changed")

    def call(self, label, args):
        self.check()
        io._run(label, args, self.env, self.work, self.records)
        self.check()
        self.records[-1]["argv"] = [SECRET_LABEL if self.private_key is not None and str(a) == str(self.private_key)
                                    else str(a.relative_to(self.work)) if isinstance(a, Path) and a.is_relative_to(self.work)
                                    else str(a) for a in args]

    def avb(self, *args):
        return io._python(self.paths["avbtool"], *args)


def _prefix(source, count, maximum, destination=None, salt=b""):
    digest, salted, remaining = hashlib.sha256(), hashlib.sha256(salt), count
    _require(type(count) is int and 0 < count <= maximum, "invalid payload prefix")
    target = None
    try:
        if destination is not None:
            with avb.envelope._parent_directory(destination) as parent:
                fd = os.open(destination.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
            target = os.fdopen(fd, "wb")
        with avb._input(source, maximum) as (stream, _):
            while remaining:
                chunk = stream.read(min(avb.CHUNK, remaining))
                _require(bool(chunk), "truncated payload prefix")
                digest.update(chunk)
                salted.update(chunk)
                if target is not None:
                    target.write(chunk)
                remaining -= len(chunk)
    finally:
        if target is not None:
            target.close()
    return {"size_bytes": count, "sha256": digest.hexdigest()}, salted.hexdigest()


def _boot_recipe(path, metadata, work, profile):
    footer = metadata["footer"]
    with avb._input(path, profile["image_budgets"]["boot"]) as (stream, _):
        stream.seek(footer["vbmeta_offset"])
        blob = stream.read(footer["vbmeta_size"])
    auth = struct.unpack_from(">Q", blob, 12)[0]
    start, length = struct.unpack_from(">QQ", blob, 96)
    data = blob[256 + auth + start:256 + auth + start + length]
    properties, at = [], 0
    while at < len(data):
        tag, following = struct.unpack_from(">QQ", data, at)
        desc = data[at:at + 16 + following]
        at += 16 + following
        if tag != 0:
            continue
        kl, vl = struct.unpack_from(">QQ", desc, 16)
        name, value = avb._tail(desc, 32, (kl + 1, vl + 1))
        name, value = name[:-1].decode("ascii"), value[:-1]
        relative = f"boot-properties/{len(properties):03d}.bin"
        io._write(work / relative, value)
        properties.append({"name": name, "path": relative, **avb._identity(value),
                           "encoded_descriptor_sha256": avb._sha(desc)})
    own = avb._data_descriptors(metadata)["boot"]
    payload, digest = _prefix(path, footer["original_image_size"], profile["image_budgets"]["boot"],
                              salt=bytes.fromhex(own["salt_hex"]))
    _require(digest == own["digest_hex"], "boot source hash does not cover its payload")
    return {"payload": payload, "salt_hex": own["salt_hex"], "hash_descriptor_sha256": own["encoded_sha256"],
            "properties": properties}


def _property_data(path, expected):
    """A zero-length AVB property is valid; do not conflate it with a missing file."""
    avb._integer(expected["size_bytes"], 0, 2048, "boot property size")
    avb._digest(expected["sha256"])
    if expected["size_bytes"]:
        return avb._small(path, MAX_TEXT, expected)
    path = avb.envelope._absolute_path(path)
    with avb.envelope._parent_directory(path) as parent:
        initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1 and initial.st_size == 0,
                 "empty property snapshot is not a regular empty file")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb", buffering=0) as stream:
            _require(avb._signature(os.fstat(stream.fileno())) == avb._signature(initial)
                     and stream.read(1) == b"" and avb._signature(os.fstat(stream.fileno())) ==
                     avb._signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                     "empty property snapshot changed")
    _require(expected["sha256"] == avb._sha(b""), "empty property identity differs")
    return b""


def boot_arguments(native, image, private_key, recipe, property_root, profile):
    args = native.avb("add_hash_footer", "--image", image, "--partition_name", "boot",
                      "--partition_size", str(profile["image_budgets"]["boot"]),
                      "--hash_algorithm", "sha256", "--algorithm", "SHA256_RSA4096", "--key", private_key,
                      "--flags", "0", "--rollback_index", "1769904000", "--rollback_index_location", "0",
                      "--salt", recipe["salt_hex"])
    for prop in recipe["properties"]:
        args += ["--prop_from_file", prop["name"] + ":" + str(property_root / prop["path"])]
    return args


def vbmeta_arguments(native, name, output, private_key, image_root, public_blob, contract):
    _require(name in ("vbmeta", "vbmeta_system"), "unexpected signed metadata role")
    args = native.avb("make_vbmeta_image", "--output", output, "--algorithm", "SHA256_RSA4096",
                      "--key", private_key, "--flags", "0", "--rollback_index",
                      "0" if name == "vbmeta" else "1769904000", "--rollback_index_location", "0",
                      "--padding_size", "4096")
    names = contract["root_direct_import_order"] if name == "vbmeta" else contract["system_import_order"]
    for part in names:
        source = (image_root / "metadata" / (part + ".vbmeta") if part in ("countrycode", "pvmfw")
                  else image_root / (part + ".img"))
        args += ["--include_descriptors_from_image", source]
    if name == "vbmeta":
        for part, location in (("boot", 3), ("recovery", 1), ("vbmeta_system", 2)):
            args += ["--chain_partition", f"{part}:{location}:{public_blob}"]
    return args


@contextmanager
def _collect(manifest, local, contract, profile, avbtool):
    _require(set(manifest["images"]) == INPUTS and bool(manifest["source_records"]),
             "all 15 final input images and provenance records are required")
    private = _private_path(local)
    _private_collision(private, *(row["path"] for row in manifest["images"].values()),
                       *(row["path"] for row in manifest["source_records"]))
    size = sum(row["size_bytes"] for row in manifest["images"].values())
    with io._private_creation(), tempfile.TemporaryDirectory(prefix="nezha-avb-prepare-") as temporary:
        work = Path(temporary).resolve()
        _require(shutil.disk_usage(work).free >= size + avb.RESERVE_BYTES, "insufficient preparation snapshot space")
        native = Native(work, profile, avbtool, local["openssl"], protected_key=private)
        io._mkdir(work / "boot-properties")
        io._write(work / "public.pem", local["public_bytes"])
        native.call("export-public", native.avb("extract_public_key", "--key", work / "public.pem",
                                                "--output", work / "public.avbpubkey"))
        public = avb._small(work / "public.avbpubkey", avb.MAX_PUBLIC_KEY)
        avb._public_blob(public)
        _require(avb._sha(public) == contract["avb_public_key_sha256"], "public key provenance differs")
        images, states, carriers = {}, {}, {}
        for name in sorted(INPUTS):
            row = manifest["images"][name]
            copied = work / (name + ".img")
            budget = avb.image_budget(profile, name)
            states[name] = avb._copy_image(row["path"], copied, row, budget)
            images[name] = avb.read_image_metadata(copied, name, budget)
            meta = images[name]
            if name == "recovery":
                avb.validate_metadata({name: meta}, profile, {name: public})
            elif name == "boot":
                _require(avb._data_descriptors(meta)["boot"]["kind"] == "hash",
                         "boot source must carry exactly its own hash descriptor")
                _require(meta["algorithm"] == "NONE" or meta["public_key_sha256"] in contract["accepted_input_boot_keys"],
                         "unreviewed boot input key")
                _require((meta["rollback_index"], meta["header_rollback_index_location"]) ==
                         ((0, 0) if meta["algorithm"] == "NONE" else (1769904000, 0)),
                         "boot input rollback differs")
            elif not meta["raw_leaf"]:
                avb.validate_metadata({name: meta}, profile, {})
            if name in ("countrycode", "pvmfw"):
                expected = contract["raw_descriptor_sources"][name]["descriptor"]
                payload = work / (name + ".payload")
                _, digest = _prefix(copied, expected["image_size"], avb.image_budget(profile, name), payload,
                                     bytes.fromhex(expected["salt_hex"]))
                _require(digest == expected["digest_hex"], "retained raw firmware descriptor differs")
                carrier = work / (name + "-vbmeta.img")
                native.call("raw-" + name, native.avb("add_hash_footer", "--image", payload,
                    "--partition_name", name, "--partition_size", str(avb.image_budget(profile, name)),
                    "--algorithm", "NONE", "--hash_algorithm", "sha256", "--flags", "0",
                    "--rollback_index", "0", "--rollback_index_location", "0", "--salt", expected["salt_hex"],
                    "--output_vbmeta_image", carrier, "--do_not_append_vbmeta_image"))
                carrier_meta = avb.parse_vbmeta(avb._small(carrier, avb.MAX_VBMETA))
                rows = avb._data_descriptors(carrier_meta)
                _require(set(rows) == {name} and rows[name]["encoded_sha256"] == expected["encoded_sha256"]
                         and len(carrier_meta["descriptors"]) == 1 and carrier_meta["algorithm"] == "NONE"
                         and carrier_meta["rollback_index"] == carrier_meta["header_rollback_index_location"] == 0,
                         "raw descriptor carrier is not the exact reviewed descriptor")
                carriers[name] = avb._small(carrier, avb.MAX_VBMETA)
                verify_image = carrier
            else:
                verify_image = copied
            args = native.avb("verify_image", "--image", verify_image)
            if name == "recovery":
                args += ["--key", work / "public.pem"]
            native.call("verify-input-" + name.replace("_", "-"), args)
        _require(len({s[:2] for s in states.values()}) == len(states), "input image roles alias one inode")
        for names in (contract["root_direct_import_order"], contract["system_import_order"]):
            properties = [r["key"] for name in names for r in images[name]["descriptors"] if r["kind"] == "property"]
            _require(len(properties) == len(set(properties)), "imported metadata would contain duplicate properties")
        recipe = _boot_recipe(work / "boot.img", images["boot"], work, profile)
        source_records = []
        for row in manifest["source_records"]:
            data = _json_file(row["path"], MAX_TEXT, row)
            _require(type(avb._json(data)) is dict, "provenance JSON must be an object")
            source_records.append({k: row[k] for k in ("sha256", "size_bytes")})
        summary = {"inputs": {n: {k: r[k] for k in ("sha256", "size_bytes")} for n, r in manifest["images"].items()},
                   "input_metadata": {n: avb._safe_report(m) for n, m in images.items()},
                   "boot_recipe": recipe, "raw_carriers": {n: avb._identity(b) for n, b in carriers.items()},
                   "public_key": avb._identity(local["public_bytes"]), "avb_public_key": avb._identity(public),
                   "local_config_identity": local["config_identity"], "source_records": source_records,
                   "source_record_semantics_verified": False, "tools": native.identities}
        yield work, native, summary, carriers, public
        for name, row in manifest["images"].items():
            avb._rehash(work / (name + ".img"), row)
            avb._rehash(row["path"], row, states[name])
        for row in manifest["source_records"]:
            _json_file(row["path"], MAX_TEXT, row)
        _json_file(local["config_path"], 16 * 1024, local["config_identity"])
        avb._public_pem(local["public_path"], contract["public_key"])
        _require(avb._small(work / "public.pem", avb.MAX_PUBLIC_KEY) == local["public_bytes"]
                 and avb._small(work / "public.avbpubkey", avb.MAX_PUBLIC_KEY) == public,
                 "public-key preparation snapshot changed")
        for prop in recipe["properties"]:
            _property_data(work / prop["path"], prop)
        for name, data in carriers.items():
            _require(avb._small(work / (name + "-vbmeta.img"), avb.MAX_VBMETA) == data,
                     "raw descriptor snapshot changed")
        native.check()


def _input_file(manifest, destination):
    # Preserve resolved image/provenance selectors so the prepared record is
    # portable across output directories. It contains no private key selector.
    value = {**manifest, "images": {n: {**r, "path": str(r["path"])} for n, r in manifest["images"].items()},
             "source_records": [{**r, "path": str(r["path"])} for r in manifest["source_records"]]}
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    io._write(destination, data)
    return avb._identity(data)


def prepare(manifest_path, expected_sha, *, local_config, output_dir, avbtool=None):
    contract, digest, profile, profile_sha = load_contract()
    manifest, original = load_input(manifest_path, expected_sha, contract, digest, profile)
    _require(set(manifest["images"]) == INPUTS and manifest["source_records"], "complete inputs are not ready")
    base = _base(digest, profile_sha, manifest["artifact_set_id"])
    local = _local(local_config, contract)
    avbtool = avbtool or ROOT / profile["tools"]["avbtool"]["path"]
    with io._private_creation():
        out = _fresh_output(output_dir, contract)
        with _collect(manifest, local, contract, profile, avbtool) as (_, native, summary, _, _):
            report = {**base, "operation": "prepare",
                      "status": "prepared_public_only", "input_manifest": _input_file(manifest, out / "input-manifest.json"),
                      "preparation": summary, "native_results": native.records,
                      "private_key_accessed": False, "signing_performed": False, "complete_chain_verified": False,
                      "two_pass_reproduction_verified": False, "source_inputs_unchanged": True}
        _require(_json_file(manifest_path, MAX_TEXT) == original and load_contract()[1] == digest
                 and _identity(ROOT / "scripts/avb_signing.py", MAX_TEXT) == base["workflow"],
                 "manifest, workflow or contract changed during preparation")
        io._save(out / "preparation.json", report)
    return report


def _pad_metadata(path, contract):
    raw = avb._small(path, avb.MAX_VBMETA)
    _require(len(raw) % contract["native_padding_size"] == 0 and len(raw) <= contract["vbmeta_output_size"],
             "signed metadata does not fit the pinned build padding rule")
    with avb.envelope._parent_directory(path) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd, "ab") as stream:
            stream.write(bytes(contract["vbmeta_output_size"] - len(raw)))


def sign(preparation_path, expected_sha, *, local_config, output_dir, avbtool=None):
    contract, digest, profile, profile_sha = load_contract()
    _require(platform.system() == "Darwin" and platform.machine() == "arm64",
             "private-key signing is restricted to the pinned ARM64 Mac host")
    avb._digest(expected_sha)
    preparation_path = avb.envelope._absolute_path(preparation_path)
    prepared_raw = _json_file(preparation_path, MAX_TEXT)
    _require(avb._sha(prepared_raw) == expected_sha, "preparation digest differs")
    prepared = avb._json(prepared_raw)
    workflow = _identity(ROOT / "scripts/avb_signing.py", MAX_TEXT)
    _require(prepared["operation"] == "prepare" and prepared["status"] == "prepared_public_only"
             and prepared["contract_sha256"] == digest and prepared["verifier_profile_sha256"] == profile_sha
             and prepared["workflow"] == workflow
             and prepared["signing_performed"] is False and prepared["complete_chain_verified"] is False,
             "preparation does not match the reviewed public-only workflow")
    input_path = preparation_path.parent / "input-manifest.json"
    _json_file(input_path, MAX_TEXT, prepared["input_manifest"])
    manifest, input_raw = load_input(input_path, prepared["input_manifest"]["sha256"], contract, digest, profile)
    local = _local(local_config, contract)
    _require(local["config_identity"] == prepared["preparation"]["local_config_identity"], "local configuration changed")
    avbtool = avbtool or ROOT / profile["tools"]["avbtool"]["path"]
    size = sum(r["size_bytes"] for r in manifest["images"].values())
    with io._private_creation():
        out = _fresh_output(output_dir, contract)
        _require(shutil.disk_usage(out).free >= 2 * size + profile["image_budgets"]["boot"] + avb.RESERVE_BYTES,
                 "insufficient signing/snapshot space")
        with _collect(manifest, local, contract, profile, avbtool) as (work, precheck, summary, carriers, public):
            _require(summary == prepared["preparation"], "prepared inputs, tools or recipe changed")
            for directory in ("metadata", "boot-properties", "reproduction"):
                io._mkdir(out / directory)
            for name in sorted(INPUTS - {"boot"}):
                avb._copy_image(work / (name + ".img"), out / (name + ".img"),
                                manifest["images"][name], avb.image_budget(profile, name))
            for name, data in carriers.items():
                io._write(out / "metadata" / (name + ".vbmeta"), data)
            for prop in summary["boot_recipe"]["properties"]:
                io._write(out / prop["path"], _property_data(work / prop["path"], prop))
            io._write(out / "public.pem", local["public_bytes"])
            io._write(out / "public.avbpubkey", public)
            native = Native(out, profile, avbtool, local["openssl"], protected_key=_private_path(local))
            _require(any(r["build_allowed"] and r["sha256"] == native.identities["openssl"]["sha256"]
                         for r in profile["tools"]["openssl"]["binaries"]), "OpenSSL is not approved for host signing")
            key = avb.envelope._absolute_path(local["config_path"].parent / local["private_selector"])
            native.private_key, native.private_state = key, _key_state(key)
            native.call("derive-signing-public", [native.paths["openssl"], "pkey", "-in", key,
                                                  "-pubout", "-out", out / "derived-public.pem"])
            avb._public_pem(out / "derived-public.pem", contract["public_key"])
            results = []
            recipe = summary["boot_recipe"]
            for number, destination in enumerate((out, out / "reproduction"), 1):
                payload, _ = _prefix(work / "boot.img", recipe["payload"]["size_bytes"],
                                     profile["image_budgets"]["boot"], destination / "boot.img")
                _require(payload == recipe["payload"], "boot payload copy changed")
                native.call(f"sign-boot-{number}", boot_arguments(native, destination / "boot.img", key,
                                                                   recipe, out, profile))
                boot = avb.read_image_metadata(destination / "boot.img", "boot", profile["image_budgets"]["boot"])
                avb.validate_metadata({"boot": boot}, profile, {"boot": public})
                rows = boot["descriptors"]
                _require(avb._data_descriptors(boot)["boot"]["encoded_sha256"] == recipe["hash_descriptor_sha256"]
                         and [r["encoded_sha256"] for r in rows if r["kind"] == "property"] ==
                         [p["encoded_descriptor_sha256"] for p in recipe["properties"]],
                         "boot signing changed a payload descriptor or property")
                for name in ("vbmeta_system", "vbmeta"):
                    native.call(f"sign-{name.replace('_', '-')}-{number}", vbmeta_arguments(
                        native, name, destination / (name + ".img"), key, out,
                        out / "public.avbpubkey", contract))
                    _pad_metadata(destination / (name + ".img"), contract)
                results.append({n: _identity(destination / (n + ".img"), avb.image_budget(profile, n))
                                for n in contract["reproduction"]["compare_images"]})
            _require(results[0] == results[1], "two signing passes produced different image bytes")
            for name in INPUTS - {"boot"}:
                avb._rehash(out / (name + ".img"), manifest["images"][name])
            for prop in recipe["properties"]:
                _property_data(out / prop["path"], prop)
            _require(avb._small(out / "public.pem", avb.MAX_PUBLIC_KEY) == local["public_bytes"]
                     and avb._small(out / "public.avbpubkey", avb.MAX_PUBLIC_KEY) == public,
                     "signing public-key copy changed")
            native.check()
            signed_results, records, identities = results, native.records, native.identities
        # Release preparation copies before the independent verifier makes its
        # own private snapshots. Every final image is bound to its exact bytes.
        final_identities = {n: {k: manifest["images"][n][k] for k in ("sha256", "size_bytes")}
                            for n in INPUTS - {"boot"}}
        final_identities.update(signed_results[0])
        for name, identity in final_identities.items():
            avb._rehash(out / (name + ".img"), identity)
        verification_manifest = {"schema_version": 1, "profile_id": avb.PROFILE_ID,
            "profile_sha256": profile_sha, "artifact_set_id": manifest["artifact_set_id"],
            "images": {n: {"path": n + ".img", **final_identities[n]}
                       for n in sorted(avb.PARTITIONS)},
            "public_keys": {n: {"path": "public.pem", **contract["public_key"],
                                 "avb_sha256": contract["avb_public_key_sha256"]} for n in sorted(avb.SIGNED)},
            "tools": {"avbtool": "tools/avbtool.py", "openssl": str(native.paths["openssl"])}}
        verification_bytes = (json.dumps(verification_manifest, indent=2, sort_keys=True) + "\n").encode()
        io._write(out / "verification-manifest.json", verification_bytes)
        verification = avb.verify(out / "verification-manifest.json", avb._sha(verification_bytes))
        _require(verification["complete_chain_verified"] is True and verification["status"] == "verified"
                 and verification["operation"] == "verify-image-set" and verification["missing_partitions"] == []
                 and verification["manifest_sha256"] == avb._sha(verification_bytes)
                 and verification["profile_sha256"] == profile_sha
                 and verification["inputs_unchanged"] is True and verification["native_commands_run"] is True
                 and set(verification["verified_artifacts"]) == avb.SIGNED
                 and set(verification["images"]) == avb.PARTITIONS
                 and all(verification["images"][n]["identity"] == final_identities[n] for n in avb.PARTITIONS),
                 "independent complete-chain verification evidence differs")
        for name, identity in final_identities.items():
            avb._rehash(out / (name + ".img"), identity)
        for name, row in manifest["images"].items():
            avb._rehash(row["path"], row)
        for row in manifest["source_records"]:
            _json_file(row["path"], MAX_TEXT, row)
        _json_file(local["config_path"], 16 * 1024, local["config_identity"])
        avb._public_pem(local["public_path"], contract["public_key"])
        _require(_json_file(preparation_path, MAX_TEXT) == prepared_raw
                 and _json_file(input_path, MAX_TEXT) == input_raw and load_contract()[1] == digest
                 and _identity(ROOT / "scripts/avb_signing.py", MAX_TEXT) == workflow,
                 "preparation, workflow or contract changed")
        native.check()
        report = {**_base(digest, profile_sha, manifest["artifact_set_id"]), "operation": "sign",
                  "status": "signed_and_verified", "preparation_sha256": expected_sha,
                  "key_roles": contract["key_roles"], "public_key": contract["public_key"],
                  "private_key_accessed": True, "private_key_reader": "pinned native host tools only",
                  "signing_performed": True, "complete_chain_verified": True,
                  "two_pass_reproduction_verified": True, "signed_derivative_passes": signed_results,
                  "working76_preserved": True, "unchanged_leaf_count": 14, "tools": identities,
                  "source_inputs_unchanged": True, "public_recheck_native_results": precheck.records,
                  "native_results": records, "verification_manifest": avb._identity(verification_bytes),
                  "verification": verification, "provenance": prepared["preparation"]["source_records"],
                  "provenance_semantics_verified": False}
        io._save(out / "signing-receipt.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("plan", "prepare", "sign"):
        command = commands.add_parser(name)
        command.add_argument("--input", required=True, type=Path,
                             help="input manifest, or preparation.json for sign")
        command.add_argument("--expected-sha256", required=True)
        if name != "plan":
            command.add_argument("--local-config", required=True, type=Path)
            command.add_argument("--avbtool", type=Path)
            command.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation == "plan":
            result = plan(args.input, args.expected_sha256)
        else:
            function = prepare if args.operation == "prepare" else sign
            result = function(args.input, args.expected_sha256, local_config=args.local_config,
                              output_dir=args.output_dir, avbtool=args.avbtool)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2 if result["status"] == "blocked" else 0
    except (AvbSigningError, avb.AvbImageSetError, io.TwrpWorkingError) as exc:
        print(json.dumps({"status": "failed", "complete_chain_verified": False,
                          "complete_rom_ready": False, "error": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, struct.error) as exc:
        # Native/configuration failures must not echo a private key path or its
        # bytes. Detailed raw stderr is deliberately not emitted by the runner.
        print(json.dumps({"status": "failed", "complete_chain_verified": False,
                          "complete_rom_ready": False, "error": "invalid or unavailable local signing input",
                          "error_class": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
