#!/usr/bin/env python3
"""Verify the Nezha Android AVB closure against independent public keys.

Only verification and public-key export commands exist here. Private signing
keys, device operations, sparse images, partial-chain success, and implicit
engineering keys are not supported. A private manifest pins the final image
bytes and independently selected public PEMs; its digest is supplied separately.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys
import tempfile

sys.dont_write_bytecode = True

if __package__:
    from . import inspect_twrp_image as envelope
    from . import twrp_working as io
else:
    import inspect_twrp_image as envelope
    import twrp_working as io


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "config/nezha-avb-image-set.json"
PROFILE_ID = "nezha-avb-image-set-v1"
MAX_TEXT = 1024 * 1024
MAX_VBMETA = 64 * 1024
MAX_PUBLIC_KEY = 16 * 1024
CHUNK = 1024 * 1024
RESERVE_BYTES = 1024 * 1024 * 1024
HASH = struct.Struct(">QQQ32sIIII60s")
HASHTREE = struct.Struct(">QQIQQQIIIQQ32sIIII60s")
CHAIN = struct.Struct(">QQIIII60s")
FOOTER = struct.Struct(">4sIIQQQ28s")
SIGNED = frozenset(("vbmeta", "boot", "recovery", "vbmeta_system"))
LOGICAL = frozenset(("system", "system_ext", "product", "vendor", "odm", "mi_ext",
                     "vendor_dlkm", "system_dlkm"))
HASHED = frozenset(("boot", "recovery", "countrycode", "dtbo", "init_boot", "pvmfw", "vendor_boot"))
PARTITIONS = SIGNED | LOGICAL | HASHED
OWNERS = {name: ("vbmeta_system" if name in ("system", "system_ext", "product")
                 else name if name in ("boot", "recovery") else "vbmeta")
          for name in LOGICAL | HASHED}


class AvbImageSetError(ValueError):
    """Unreviewed, incomplete, unstable, or unverifiable input."""


def _require(condition, message):
    if not condition:
        raise AvbImageSetError(message)


def _keys(value, expected, label):
    _require(type(value) is dict and set(value) == set(expected), label + " fields differ")


def _integer(value, minimum, maximum, label):
    _require(type(value) is int and minimum <= value <= maximum, "invalid " + label)


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "invalid SHA256")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _identity(data):
    return {"size_bytes": len(data), "sha256": _sha(data)}


def _identity_spec(value, *, path=False):
    _keys(value, ("path", "size_bytes", "sha256") if path else ("size_bytes", "sha256"), "identity")
    _integer(value["size_bytes"], 1, 1 << 40, "identity size")
    _digest(value["sha256"])
    if path:
        _require(type(value["path"]) is str and value["path"] and len(value["path"]) <= 4096
                 and value["path"].isprintable(), "invalid input path")


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_nlink)


@contextmanager
def _input(path, maximum):
    """Hold a regular, singly linked source and its parent during each read."""
    path = envelope._absolute_path(path)
    with envelope._parent_directory(path) as parent:
        initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1,
                 "input must be a regular file without hardlinks")
        _require(0 < initial.st_size <= maximum, "input exceeds size bound")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        # Unbuffered access also keeps a public-key header sniff from fetching
        # the payload of an accidentally selected private PEM into a buffer.
        with os.fdopen(fd, "rb", buffering=0) as stream:
            before = _signature(initial)
            _require(before == _signature(os.fstat(stream.fileno())), "input changed before read")
            yield stream, initial
            _require(before == _signature(os.fstat(stream.fileno())) ==
                     _signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                     "input changed during read")


def _small(path, maximum, expected=None):
    with _input(path, maximum) as (stream, info):
        raw = stream.read(info.st_size + 1)
        _require(len(raw) == info.st_size, "input size changed")
    if expected is not None:
        _require(_identity(raw) == {k: expected[k] for k in ("size_bytes", "sha256")},
                 "input identity differs")
    return raw


def _public_pem(path, expected):
    # Reject a private-key header before reading its payload. No private key
    # selector is accepted in either schema or any native command.
    with _input(path, MAX_PUBLIC_KEY) as (stream, info):
        first = stream.readline(128)
        _require(first in (b"-----BEGIN PUBLIC KEY-----\n", b"-----BEGIN RSA PUBLIC KEY-----\n"),
                 "expected a public PEM; private keys are not read")
        raw = first + stream.read(info.st_size + 1)
        _require(len(raw) == info.st_size and b"PRIVATE KEY" not in raw,
                 "invalid public PEM")
    _require(_identity(raw) == {k: expected[k] for k in ("size_bytes", "sha256")},
             "public PEM identity differs")
    return raw


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except RecursionError as exc:
        raise AvbImageSetError("JSON nesting exceeds parser bound") from exc


def load_profile():
    raw = _small(PROFILE, MAX_TEXT)
    profile = _json(raw)
    _require(type(profile["schema_version"]) is int and profile["schema_version"] == 1
             and profile["profile_id"] == PROFILE_ID and profile["device"] == "nezha"
             and profile["platform"] == {"branch": "bka", "release_config": "bp4a"},
             "unsupported AVB profile")
    _require(set(profile["image_budgets"]) == PARTITIONS
             and profile["descriptor_owners"] == OWNERS
             and set(profile["signed_images"]) == SIGNED
             and set(profile["logical_partitions"]) == LOGICAL
             and set(profile["hashtree_partitions"]) == LOGICAL
             and profile["raw_leaf_partitions"] == ["countrycode", "pvmfw"]
             and profile["chain_locations"] == {"boot": 3, "recovery": 1, "vbmeta_system": 2}
             and profile["required_flags"] == 0 and type(profile["required_flags"]) is int
             and profile["required_algorithm"] == "SHA256_RSA4096",
             "AVB topology or algorithms differ from the reviewed profile")
    evidence = {}
    for row in profile["evidence"]:
        _identity_spec(row, path=True)
        _require(row["path"] not in evidence and row["path"] in (
            "research/factory-firmware-validation.json", "research/partition-metadata.json",
            "config/twrp-working.json"), "unexpected profile evidence")
        evidence[row["path"]] = _json(_small(ROOT / row["path"], MAX_TEXT, row))
    _require(len(evidence) == 3, "missing profile evidence")
    factory = evidence["research/factory-firmware-validation.json"]
    geometry = evidence["research/partition-metadata.json"]
    recovery = evidence["config/twrp-working.json"]
    budgets = {r["name"]: r["package_extent_bytes"] for r in geometry["build_relevant_sizes"]
               if r["name"] != "super"}
    for name in ("countrycode", "pvmfw"):
        sizes = [r["size_bytes"] for lun in geometry["luns"] for r in lun["partitions"]
                 if r["label"] in (name + "_a", name + "_b")]
        _require(len(sizes) == 2 and sizes[0] == sizes[1], "inconsistent A/B package budgets")
        budgets[name] = sizes[0]
    budgets.update({r["name"][:-2]: r["size_bytes"] for r in factory["logical_partitions"]["partitions"]
                    if r["name"].endswith("_a")})
    _require(profile["image_budgets"] == budgets, "image budgets differ from package GPT/LP evidence")
    for name, size in budgets.items():
        _integer(profile["image_budgets"][name], 4096, 1 << 36, "package budget")
        _require(size % 4096 == 0, "unaligned package budget")
    group = [r["maximum_size"] for r in factory["logical_partitions"]["groups"]
             if r["name"] == "qti_dynamic_partitions_a"]
    _require(group == [profile["logical_group_budget"]], "logical group budget differs")
    overrides = profile["dynamic_logical_budget_overrides"]
    _require(type(overrides) is dict and set(overrides) == {"system_ext"},
             "unexpected dynamic logical budget override")
    override = overrides["system_ext"]
    _keys(override, ("stock_budget_bytes", "maximum_size_bytes", "measured_image",
                     "admission_record", "build_number", "additional_measured_images"),
          "dynamic logical budget override")
    _integer(override["stock_budget_bytes"], 4096, profile["logical_group_budget"],
             "stock logical budget")
    _integer(override["maximum_size_bytes"], 4096, profile["logical_group_budget"],
             "successor logical budget")
    _require(override["stock_budget_bytes"] == budgets["system_ext"]
             and override["maximum_size_bytes"] >= override["stock_budget_bytes"]
             and override["maximum_size_bytes"] % 4096 == 0,
             "successor logical budget is not a bounded extension of stock evidence")
    _identity_spec(override["measured_image"])
    _identity_spec(override["admission_record"], path=True)
    _require(override["measured_image"]["size_bytes"] == 778199040
             and override["measured_image"]["sha256"] ==
             "c75d16fa4d06d2d30089cf469df9d845410cbd66446d4018cbec667c24521cc4"
             and override["admission_record"] == {
                 "path": "artifacts/build-validation/feature-successor-package-admit-v3/admission.json",
                 "sha256": "35394333108fdcbb233cd702bca88260e8d2bb452571308465af420583da7238",
                 "size_bytes": 14222}
             and override["build_number"] == "nezha.a6d3109ae93158c498bb30b0",
             "successor logical budget provenance differs")
    additional = override["additional_measured_images"]
    _require(type(additional) is list and len(additional) == len(ADDITIONAL_MEASURED_SYSTEM_EXT),
             "exact additional measured image admissions required")
    for candidate, expected in zip(additional, ADDITIONAL_MEASURED_SYSTEM_EXT):
        _keys(candidate, ("measured_image", "admission_record", "build_number"),
              "additional measured image admission")
        _identity_spec(candidate["measured_image"])
        _identity_spec(candidate["admission_record"], path=True)
        _require(candidate == expected, "additional measured image provenance differs")
        _require(override["stock_budget_bytes"] < candidate["measured_image"]["size_bytes"]
                 <= override["maximum_size_bytes"]
                 and candidate["measured_image"]["size_bytes"] % 4096 == 0,
                 "additional measured image exceeds the logical allowance")
    # The allowance is exactly the largest admitted measured image, never a round-up.
    _require(override["maximum_size_bytes"] == max(
        [override["measured_image"]["size_bytes"]] + [c["measured_image"]["size_bytes"] for c in additional]),
        "successor logical budget is not the largest admitted measured image")
    for name, expected in (("vbmeta", (0, 0)), ("boot", (1769904000, 0)),
                           ("recovery", (1, 1)), ("vbmeta_system", (1769904000, 0))):
        row = profile["signed_images"][name]
        _keys(row, ("rollback_index", "header_rollback_index_location"), "signed role")
        for value in row.values():
            _integer(value, 0, (1 << 64) - 1, "rollback value")
        _require((row["rollback_index"], row["header_rollback_index_location"]) == expected,
                 "rollback role differs")
    _require(profile["maximum_required_libavb_version"] == [1, 2]
             and all(type(v) is int for v in profile["maximum_required_libavb_version"]),
             "unreviewed libavb version")
    _require(all(type(v) is int for v in profile["chain_locations"].values()),
             "invalid chain location type")
    _require(profile["working76"]["image"] == recovery["output"]["image"]
             and profile["working76"]["avb_public_key_sha256"] == recovery["avb"]["public_key_sha256"],
             "working76 identity differs")
    _require(profile["tools"]["avbtool"]["sha256"] ==
             "14dc8d6ec533f551ec05ffd9a986ced0fd1290a201f62c91dad329dd51dfe3ed",
             "unreviewed avbtool")
    _require(profile["tools"]["openssl"] == recovery["tools"]["openssl"],
             "OpenSSL identities differ from the reviewed verification tools")
    _require(profile["forbidden_public_key_sha256"] ==
             ["7728e30f50bfa5cea165f473175a08803f6a8346642b5aa10913e9d9e6defef6"],
             "engineering-key guard differs")
    return profile, _sha(raw)


# Explicitly admitted system_ext images above the stock budget, in admission order.
# Each pairs the exact measured image with the native package-admission record.
ADDITIONAL_MEASURED_SYSTEM_EXT = (
    {"measured_image": {"sha256": "707442120ef680143b653d765c6148617482fa196b951998844d7ed8edfa7432",
                        "size_bytes": 778190848},
     "admission_record": {"path": "artifacts/build-validation/feature-successor-f9e-package-admit-v1/admission.json",
                          "sha256": "aae261fc3bc3974a280426ad7a1711698ee7d5c476a1e8806b4e45b78ad505c7",
                          "size_bytes": 14226},
     "build_number": "nezha.f9e30611efe01b882f9ed0cb"},
    # userdebug diagnostic opt-in build: the debug variant adds 5,300,224 bytes to system_ext.
    {"measured_image": {"sha256": "9d96b82b7123cd1373141aeeae13c5425dc6f18a900536b2b23e92d28624649c", "size_bytes": 783491072},
     "admission_record": {"path": "artifacts/build-validation/variant-opt-in-userdebug-20260906-v1-admit/admission.json", "sha256": "f8b7ee0961f36e73bf17658aaa3af323bfdbf9751518e91bc32815c4a4bd70b6", "size_bytes": 6908},
     "build_number": "nezha.1088ec3b159be6c32e1403f2"},
    # userdebug diagnostic opt-in build with ro.debuggable=1 (fourth guest transaction); same size, new identity.
    {"measured_image": {"sha256": "da5ae04b78369864a5023febf8e9bf03b649a08cb8d8dac1027a6cae34f6c6d2", "size_bytes": 783491072},
     "admission_record": {"path": "artifacts/build-validation/variant-opt-in-userdebug-20260906-v3-admit/admission.json", "sha256": "6a878389deced14ebc735e4e9baa955d224661f0b478e48a960da3afb52dd1ef", "size_bytes": 7056},
     "build_number": "nezha.88dd30980cd24ea68d6b701e"},
    # userdebug opt-in rebuilt with WITH_SU=true: adb_root adds 16,384 bytes to system_ext.
    {"measured_image": {"sha256": "4848f4dabcbaf9669ca8bcf7e74963db81b02538df42d3d122fb359200420761", "size_bytes": 783507456},
     "admission_record": {"path": "artifacts/build-validation/variant-opt-in-userdebug-20260906-v4-admit/admission.json", "sha256": "f5262a914eaa8d6267ebd760ced2ad4f62a4de0a1a710d0b8af326332fc4ff99", "size_bytes": 7056},
     "build_number": "nezha.88dd30980cd24ea68d6b701e"},
)


def image_budget(profile, name):
    """Return a physical stock bound or an explicitly reviewed logical bound."""
    override = profile.get("dynamic_logical_budget_overrides", {}).get(name)
    return override["maximum_size_bytes"] if override is not None else profile["image_budgets"][name]


def validate_image_budget(profile, name, row):
    """Enforce the stock bound or the exact measured image behind an override."""
    _require(row["size_bytes"] <= image_budget(profile, name) and row["size_bytes"] % 4096 == 0,
             "image exceeds package budget or is unaligned")
    override = profile.get("dynamic_logical_budget_overrides", {}).get(name)
    if override is not None and row["size_bytes"] > override["stock_budget_bytes"]:
        admitted = [override["measured_image"]] + [
            item["measured_image"] for item in override.get("additional_measured_images", [])]
        _require({key: row[key] for key in ("sha256", "size_bytes")} in admitted,
                 "image above stock budget is not the admitted successor image")


def load_manifest(path, expected_sha256, profile, profile_sha256):
    _digest(expected_sha256)
    path = envelope._absolute_path(path)
    raw = _small(path, MAX_TEXT)
    _require(_sha(raw) == expected_sha256, "manifest SHA256 differs")
    value = _json(raw)
    _keys(value, ("schema_version", "profile_id", "profile_sha256", "artifact_set_id",
                  "images", "public_keys", "tools"), "manifest")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and value["profile_id"] == PROFILE_ID and value["profile_sha256"] == profile_sha256,
             "manifest profile differs")
    _require(type(value["artifact_set_id"]) is str and
             re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value["artifact_set_id"]),
             "invalid artifact set id")
    _require(type(value["images"]) is dict and set(value["images"]) <= PARTITIONS,
             "unexpected image role")
    _require(type(value["public_keys"]) is dict and set(value["public_keys"]) ==
             set(value["images"]) & SIGNED, "missing or extra per-image public key")
    for name, row in value["images"].items():
        _identity_spec(row, path=True)
        validate_image_budget(profile, name, row)
        if name == "recovery":
            _require({k: row[k] for k in ("size_bytes", "sha256")} == profile["working76"]["image"],
                     "recovery is not exact working76")
    _require(sum(value["images"][p]["size_bytes"] for p in LOGICAL & set(value["images"]))
             <= profile["logical_group_budget"], "logical images exceed package group budget")
    for name, row in value["public_keys"].items():
        _keys(row, ("path", "size_bytes", "sha256", "avb_sha256"), "public-key selector")
        _identity_spec({k: row[k] for k in ("path", "size_bytes", "sha256")}, path=True)
        _digest(row["avb_sha256"])
        _require(row["size_bytes"] <= MAX_PUBLIC_KEY, "public PEM exceeds bound")
        _require(row["avb_sha256"] not in profile["forbidden_public_key_sha256"],
                 "public engineering test key is not an admitted signer")
        if name == "recovery":
            _require({k: row[k] for k in ("size_bytes", "sha256")} == profile["working76"]["public_pem"]
                     and row["avb_sha256"] == profile["working76"]["avb_public_key_sha256"],
                     "recovery public key differs from working76")
    _keys(value["tools"], ("avbtool", "openssl"), "tool selectors")
    for group in (value["images"], value["public_keys"]):
        for row in group.values():
            row["path"] = envelope._absolute_path(path.parent / row["path"])
    for name, selected in value["tools"].items():
        _require(type(selected) is str and selected and selected.isprintable(), "invalid tool path")
        value["tools"][name] = envelope._absolute_path(path.parent / selected)
    return value, raw


def _tail(raw, fixed, lengths):
    end = fixed + sum(lengths)
    _require(end <= len(raw) and (end + 7) // 8 * 8 == len(raw)
             and not any(raw[end:]), "invalid descriptor length or padding")
    parts, at = [], fixed
    for length in lengths:
        parts.append(raw[at:at + length])
        at += length
    return parts


def _name(raw):
    _require(re.fullmatch(rb"[a-z][a-z0-9_]{0,63}", raw), "unsafe AVB partition name")
    value = raw.decode("ascii")
    _require(value in PARTITIONS, "unexpected AVB partition name")
    return value


def _public_blob(raw):
    _require(len(raw) == 1032 and struct.unpack_from(">I", raw)[0] == 4096,
             "expected RSA4096 AVB public key")


def _descriptor(raw):
    tag, following = struct.unpack_from(">QQ", raw)
    _require(len(raw) == following + 16, "descriptor length differs")
    result = {"encoded_sha256": _sha(raw), "size_bytes": len(raw)}
    if tag == 0:
        _require(len(raw) >= 32, "truncated AVB property")
        _, _, key_len, value_len = struct.unpack_from(">4Q", raw)
        _require(0 < key_len <= 256 and value_len <= 2048, "AVB property exceeds bound")
        key, val = _tail(raw, 32, (key_len + 1, value_len + 1))
        _require(key[-1:] == val[-1:] == b"\0" and b"\0" not in key[:-1] + val[:-1],
                 "invalid AVB property strings")
        _require(re.fullmatch(rb"[A-Za-z0-9_.-]+", key[:-1]), "invalid AVB property key")
        return {**result, "kind": "property", "key": key[:-1].decode("ascii"),
                "value_sha256": _sha(val[:-1])}
    if tag == 2:
        _require(len(raw) >= HASH.size, "truncated hash descriptor")
        _, _, size, algorithm, nl, sl, dl, flags, reserved = HASH.unpack_from(raw)
        name, salt, digest = _tail(raw, HASH.size, (nl, sl, dl))
        result.update(kind="hash", image_size=size)
    elif tag == 1:
        _require(len(raw) >= HASHTREE.size, "truncated hashtree descriptor")
        (_, _, version, size, tree_at, tree_size, data_block, hash_block, roots,
         fec_at, fec_size, algorithm, nl, sl, dl, flags, reserved) = HASHTREE.unpack_from(raw)
        name, salt, digest = _tail(raw, HASHTREE.size, (nl, sl, dl))
        _require(version == 1 and data_block == hash_block == 4096 and size % 4096 == 0
                 and roots == 2 and tree_at == size, "unreviewed hashtree geometry")
        blocks, expected_tree = size // 4096, 0
        while blocks > 1:
            blocks = (blocks * 32 + 4095) // 4096
            expected_tree += blocks * 4096
        expected_fec = ((fec_at // 4096 + 252) // 253) * 2 * 4096
        _require(tree_size == expected_tree and tree_size > 0 and fec_at == tree_at + tree_size
                 and fec_size == expected_fec and fec_size > 0, "invalid tree/FEC geometry")
        result.update(kind="hashtree", image_size=size, tree_offset=tree_at, tree_size=tree_size,
                      fec_offset=fec_at, fec_size=fec_size, fec_num_roots=roots,
                      data_block_size=data_block, hash_block_size=hash_block)
    elif tag == 4:
        _require(len(raw) >= CHAIN.size, "truncated chain descriptor")
        _, _, location, nl, kl, flags, reserved = CHAIN.unpack_from(raw)
        name, key = _tail(raw, CHAIN.size, (nl, kl))
        _require(flags == 0 and not any(reserved), "chain flags/reserved bytes are not zero")
        _public_blob(key)
        return {**result, "kind": "chain", "partition": _name(name), "flags": flags,
                "rollback_index_location": location, "public_key_sha256": _sha(key), "_key": key}
    else:
        raise AvbImageSetError("unreviewed descriptor tag (including kernel command lines)")
    # Factory salts are 32 bytes; the pinned build also concatenates SHA256s of
    # build number/date files into a 64-byte salt. Digest width stays SHA256.
    _require(size > 0 and algorithm == b"sha256" + bytes(26) and sl in (32, 64) and dl == 32
             and flags == 0 and not any(reserved), "invalid hash/hashtree algorithm, digest, or flags")
    result.update(partition=_name(name), hash_algorithm="sha256", salt_hex=salt.hex(),
                  digest_hex=digest.hex(), flags=flags)
    return result


def parse_vbmeta(blob):
    _require(len(blob) <= MAX_VBMETA, "vbmeta exceeds bound")
    meta = envelope._vbmeta(blob)
    _require(meta["required_libavb_version"] <= [1, 2] and meta["flags"] == 0,
             "unreviewed libavb version or disabling flags")
    auth_size = meta["authentication_size_bytes"]
    pairs = [struct.unpack_from(">QQ", blob, n) for n in range(32, 112, 16)]
    (ha, hs), (sa, ss), (ka, ks), (ma, ms), (da, ds) = pairs
    aux, auth = blob[256 + auth_size:], blob[256:256 + auth_size]
    _require(ms == 0, "unreviewed public-key metadata")
    if meta["algorithm_type"] == 2:
        _require((auth_size, ha, hs, sa, ss, ks) == (576, 0, 32, 32, 512, 1032),
                 "unexpected SHA256_RSA4096 authentication fields")
        key = aux[ka:ka + ks]
        _public_blob(key)
        _require(auth[:32] == hashlib.sha256(blob[:256] + aux).digest(),
                 "vbmeta authentication hash differs")
    elif meta["algorithm_type"] == 0:
        # avbtool places zero-length key fields at the end of descriptors even
        # for NONE. Their bounded offsets are not key material.
        _require(auth_size == ha == hs == sa == ss == ks == ms == 0,
                 "unsigned vbmeta has authentication or key data")
        key = b""
    else:
        raise AvbImageSetError("unreviewed vbmeta signature algorithm")
    for data, ranges in ((auth, ((ha, ha + hs), (sa, sa + ss))),
                         (aux, ((ka, ka + ks), (da, da + ds)))):
        cursor = 0
        for start, end in sorted((a, b) for a, b in ranges if a != b):
            _require(not any(data[cursor:start]), "nonzero AVB block padding")
            cursor = end
        _require(not any(data[cursor:]), "nonzero AVB block padding")
    descriptors, at = [], da
    names, properties = set(), set()
    for header in meta["descriptor_headers"]:
        row = _descriptor(aux[at:at + header["size_bytes"]])
        at += header["size_bytes"]
        if row["kind"] == "property":
            _require(row["key"] not in properties, "duplicate AVB property")
            properties.add(row["key"])
        else:
            _require(row["partition"] not in names, "duplicate AVB partition descriptor")
            names.add(row["partition"])
        descriptors.append(row)
    return {"algorithm": "SHA256_RSA4096" if key else "NONE", "_key": key,
            "public_key_sha256": _sha(key) if key else None,
            "required_libavb_version": meta["required_libavb_version"], "flags": meta["flags"],
            "rollback_index": meta["rollback_index"],
            "header_rollback_index_location": meta["rollback_index_location"],
            "descriptors": descriptors, "vbmeta_sha256": _sha(blob)}


def read_image_metadata(path, partition, budget):
    with _input(path, budget) as (stream, info):
        first = stream.read(4096)
        _require(first[:4] != b"\x3a\xff\x26\xed", "sparse images are not supported")
        stream.seek(-FOOTER.size, os.SEEK_END)
        footer_raw = stream.read(FOOTER.size)
        footer = None
        if footer_raw[:4] == b"AVBf":
            _, major, minor, original, offset, size, reserved = FOOTER.unpack(footer_raw)
            _require((major, minor) == (1, 0) and not any(reserved)
                     and 0 < original <= offset and offset % 4096 == 0
                     and 256 <= size <= MAX_VBMETA and offset + size <= info.st_size - FOOTER.size,
                     "invalid or overlapping AVB footer")
            footer = {"original_image_size": original, "vbmeta_offset": offset, "vbmeta_size": size}
            stream.seek(offset)
            blob = stream.read(size)
        elif first[:4] == b"AVB0":
            _require(info.st_size <= 131072, "standalone vbmeta exceeds package size")
            auth_size, aux_size = struct.unpack_from(">QQ", first, 12)
            size = 256 + auth_size + aux_size
            _require(256 <= size <= MAX_VBMETA and size <= info.st_size, "truncated standalone vbmeta")
            stream.seek(0)
            blob = stream.read(size)
            _require(not any(stream.read()), "standalone vbmeta has nonzero trailing bytes")
        else:
            _require(partition in ("countrycode", "pvmfw"), "required AVB metadata is missing")
            return {"raw_leaf": True, "size_bytes": info.st_size, "footer": None, "descriptors": []}
        result = parse_vbmeta(blob)
        result.update(raw_leaf=False, size_bytes=info.st_size, footer=footer)
        expected_footer = partition not in ("vbmeta", "vbmeta_system")
        _require(bool(footer) == expected_footer, "wrong standalone/footer image role")
        if footer:
            own = [r for r in result["descriptors"] if r["kind"] != "property"]
            _require(len(own) == 1 and own[0].get("partition") == partition
                     and own[0]["kind"] in ("hash", "hashtree")
                     and own[0]["image_size"] == footer["original_image_size"],
                     "footer does not describe the complete own payload")
            if partition in ("boot", "init_boot", "recovery"):
                _require(first[:8] == b"ANDROID!" and struct.unpack_from("<I", first, 40)[0] == 4
                         and struct.unpack_from("<I", first, 20)[0] == 1584, "expected Android boot v4")
                kernel, ramdisk = struct.unpack_from("<II", first, 8)
                signature = struct.unpack_from("<I", first, 1580)[0]
                payload = 4096 + sum((x + 4095) // 4096 * 4096 for x in (kernel, ramdisk, signature))
                _require((partition == "boot" and kernel > 0) or
                         (partition != "boot" and kernel == 0 and ramdisk > 0), "wrong boot payload role")
            elif partition == "vendor_boot":
                _require(first[:8] == b"VNDRBOOT" and struct.unpack_from("<II", first, 8) == (4, 4096)
                         and struct.unpack_from("<I", first, 2096)[0] == 2128, "expected vendor boot v4")
                sizes = [struct.unpack_from("<I", first, x)[0] for x in (24, 2100, 2112, 2124)]
                payload = 4096 + sum((x + 4095) // 4096 * 4096 for x in sizes)
                count, entry_size = struct.unpack_from("<II", first, 2116)
                _require(1 <= count <= 1024 and entry_size == 108 and sizes[2] == count * entry_size,
                         "invalid vendor ramdisk table geometry")
                table_at = 4096 + sum((x + 4095) // 4096 * 4096 for x in sizes[:2])
                _require(table_at + sizes[2] <= footer["original_image_size"],
                         "vendor ramdisk table exceeds authenticated payload")
                stream.seek(table_at)
                table = stream.read(sizes[2])
                _require(len(table) == sizes[2], "truncated vendor ramdisk table")
                spans = []
                for at in range(0, len(table), entry_size):
                    ramdisk_size, ramdisk_at, kind = struct.unpack_from("<III", table, at)
                    _require(kind in (0, 1, 2, 3) and ramdisk_size > 0
                             and ramdisk_at + ramdisk_size <= sizes[0],
                             "vendor ramdisk fragment exceeds authenticated ramdisk")
                    spans.append((ramdisk_at, ramdisk_at + ramdisk_size))
                ordered = sorted(spans)
                _require(all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:])),
                         "overlapping vendor ramdisk fragments")
            elif partition == "dtbo":
                _require(first[:4] == b"\xd7\xb7\xab\x1e", "expected DTBO table")
                _, payload, header_size, entry_size, count, table_at, page, version = struct.unpack_from(">8I", first)
                _require(header_size == entry_size == 32 and version == 0 and page == 4096
                         and 1 <= count <= 1024 and table_at >= header_size
                         and table_at + count * entry_size <= payload <= footer["original_image_size"],
                         "invalid DTBO table geometry")
                stream.seek(table_at)
                table = stream.read(count * entry_size)
                _require(len(table) == count * entry_size, "truncated DTBO table")
                for at in range(0, len(table), entry_size):
                    dt_size, dt_at = struct.unpack_from(">II", table, at)
                    _require(dt_size > 0 and dt_at >= table_at + len(table)
                             and dt_at + dt_size <= payload,
                             "DTBO entry exceeds authenticated payload")
            elif partition in LOGICAL:
                _require(first[1024:1028] == b"\xe2\xe1\xf5\xe0" and first[1036] == 12,
                         "expected 4096-byte EROFS filesystem")
                payload = struct.unpack_from("<I", first, 1060)[0] * 4096
            else:
                payload = {"countrycode": 32, "pvmfw": 778240}[partition]
            _require(payload == footer["original_image_size"], "AVB payload coverage differs from image header")
        return result


def _data_descriptors(metadata):
    return {r["partition"]: r for r in metadata["descriptors"] if r["kind"] != "property"}


def validate_metadata(images, profile, public_blobs):
    """Validate all available structures; callers separately require completeness."""
    for name, meta in images.items():
        rows = _data_descriptors(meta)
        if name in SIGNED:
            _require(not meta["raw_leaf"] and meta["algorithm"] == "SHA256_RSA4096",
                     "signed role is unsigned")
            expected = profile["signed_images"][name]
            _require(all(meta[k] == v for k, v in expected.items()), "signed rollback role differs")
            _require(meta["_key"] == public_blobs[name], "embedded signer key differs from selected public PEM")
        elif not meta["raw_leaf"]:
            _require(meta["algorithm"] == "NONE" and meta["rollback_index"] ==
                     meta["header_rollback_index_location"] == 0,
                     "direct leaf has an unreviewed signing/rollback role")
        if name in ("vbmeta", "vbmeta_system"):
            expected = {p for p, owner in OWNERS.items() if owner == name}
            if name == "vbmeta":
                expected |= set(profile["chain_locations"])
            _require(set(rows) == expected, "missing, extra, or wrongly owned AVB descriptor")
        elif not meta["raw_leaf"]:
            _require(set(rows) == {name}, "image contains another partition descriptor")
        for target, row in rows.items():
            expected_kind = ("chain" if name == "vbmeta" and target in profile["chain_locations"]
                             else "hashtree" if target in LOGICAL else "hash")
            _require(row["kind"] == expected_kind, "wrong descriptor kind for the required owner")
            if row["kind"] == "chain":
                _require(name == "vbmeta" and target in profile["chain_locations"]
                         and row["rollback_index_location"] == profile["chain_locations"][target],
                         "unexpected chain or rollback location")
                if target in public_blobs:
                    _require(row["_key"] == public_blobs[target], "parent chain key differs from intended child key")
                if target in images:
                    _require(row["_key"] == images[target]["_key"], "parent and child embedded keys differ")
                continue
            if target not in images:
                continue  # Structural inspection only; complete verification forbids this case.
            leaf = images[target]
            limit = leaf["footer"]["vbmeta_offset"] if leaf["footer"] else leaf["size_bytes"]
            end = row["fec_offset"] + row["fec_size"] if row["kind"] == "hashtree" else row["image_size"]
            _require(end <= limit and row["image_size"] <= image_budget(profile, target),
                     "descriptor exceeds payload/metadata/package bounds")
            if leaf["raw_leaf"]:
                _require(row["image_size"] == {"countrycode": 32, "pvmfw": 778240}[target],
                         "raw firmware payload coverage differs")
            elif name != target:
                child_row = _data_descriptors(leaf).get(target)
                _require(child_row and child_row["encoded_sha256"] == row["encoded_sha256"],
                         "signed parent descriptor differs from leaf footer")


def _copy_image(source, destination, expected, maximum):
    digest, count = hashlib.sha256(), 0
    with _input(source, maximum) as (stream, info):
        _require(info.st_size == expected["size_bytes"], "image size differs from manifest")
        with envelope._parent_directory(destination) as parent:
            fd = os.open(destination.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            with os.fdopen(fd, "wb") as target:
                for chunk in iter(lambda: stream.read(CHUNK), b""):
                    count += len(chunk)
                    _require(count <= info.st_size, "image grew during snapshot")
                    digest.update(chunk)
                    target.write(chunk)
        signature = _signature(info)
    identity = {"size_bytes": count, "sha256": digest.hexdigest()}
    _require(identity == {k: expected[k] for k in identity}, "image identity differs from manifest")
    return signature


def _rehash(path, expected, signature=None):
    digest, count = hashlib.sha256(), 0
    with _input(path, expected["size_bytes"]) as (stream, info):
        _require(signature is None or _signature(info) == signature, "input identity/mode changed")
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            count += len(chunk)
            digest.update(chunk)
    _require({"size_bytes": count, "sha256": digest.hexdigest()} ==
             {k: expected[k] for k in ("size_bytes", "sha256")}, "verification input changed")


def _file_signature(path, maximum):
    with _input(path, maximum) as (_, info):
        return _signature(info)


def _native(label, args, env, work, records):
    io._run(label, args, env, work, records, max_file_bytes=MAX_TEXT)
    records[-1]["argv"] = [str(a.relative_to(work)) if isinstance(a, Path) and a.is_relative_to(work)
                            else str(a) for a in args]


def _safe_report(value):
    if isinstance(value, dict):
        return {k: _safe_report(v) for k, v in value.items() if not k.startswith("_")}
    if isinstance(value, list):
        return [_safe_report(v) for v in value]
    return value


def verify(manifest_path, expected_manifest_sha256, *, inspect_only=False):
    profile, profile_sha = load_profile()
    manifest, original_manifest = load_manifest(manifest_path, expected_manifest_sha256, profile, profile_sha)
    manifest_signature = _file_signature(manifest_path, MAX_TEXT)
    implementation = {name: _identity(_small(ROOT / name, MAX_TEXT)) for name in (
        "scripts/avb_image_set.py", "scripts/twrp_working.py", "scripts/inspect_twrp_image.py")}
    missing = sorted(PARTITIONS - set(manifest["images"]))
    base = {"schema_version": 1, "operation": "inspect-artifacts" if inspect_only else "verify-image-set",
            "profile_id": PROFILE_ID, "profile_sha256": profile_sha,
            "implementation": implementation, "python_version": sys.version.split()[0],
            "manifest_sha256": expected_manifest_sha256, "artifact_set_id": manifest["artifact_set_id"],
            "missing_partitions": missing, "complete_chain_verified": False,
            "complete_rom_ready": False, "signing_performed": False, "phone_accessed": False,
            "oem_trust_established": False, "device_rollback_compatibility_verified": False,
            "physical_partition_fit_verified": False, "fec_payload_verified": False,
            "scope": "Selected public keys and package GPT/LP budgets; Android AVB closure only."}
    if missing and not inspect_only:
        return {**base, "status": "blocked", "reason": "complete image set is missing",
                "native_commands_run": False, "verified_artifacts": []}
    _require(bool(manifest["images"]), "no artifacts selected for inspection")
    size = sum(r["size_bytes"] for r in manifest["images"].values())
    records, images, source_signatures = [], {}, {}
    with io._private_creation(), tempfile.TemporaryDirectory(prefix="nezha-avb-verify-") as temporary:
        work = Path(temporary).resolve()
        _require(shutil.disk_usage(work).free >= size + RESERVE_BYTES,
                 "insufficient disk for private image verification snapshots")
        paths, tool_ids, tools_snapshot, env = io._prepare_tools(profile, work, **manifest["tools"])
        tool_checks = {path: (identity, _file_signature(path, io.MAX_TOOL))
                       for path, identity in tools_snapshot.items()}
        for name, path in paths.items():
            tool_checks[path] = (tool_ids[name], _file_signature(path, io.MAX_TOOL))

        def checked_native(label, args):
            # Include the executable script copy, not only its source. Neither
            # native success nor an unchanged original proves this copy stable.
            for path, (identity, signature) in tool_checks.items():
                _rehash(path, identity, signature)
            _native(label, args, env, work, records)
            for path, (identity, signature) in tool_checks.items():
                _rehash(path, identity, signature)

        keydir = work / "keys"
        io._mkdir(keydir)
        public_blobs, key_snapshots, snapshot_signatures, source_key_signatures = {}, {}, {}, {}
        for name, row in manifest["public_keys"].items():
            pem = _public_pem(row["path"], row)
            source_key_signatures[name] = _file_signature(row["path"], MAX_PUBLIC_KEY)
            selected, exported = keydir / (name + ".pem"), keydir / (name + ".avbpubkey")
            io._write(selected, pem)
            checked_native("export-" + name.replace("_", "-"),
                           io._python(paths["avbtool"], "extract_public_key", "--key", selected, "--output", exported))
            blob = _small(exported, MAX_PUBLIC_KEY)
            _public_blob(blob)
            _require(_sha(blob) == row["avb_sha256"] and _sha(blob) not in profile["forbidden_public_key_sha256"],
                     "exported public key differs or is an engineering key")
            public_blobs[name] = blob
            key_snapshots[selected] = _identity(pem)
            key_snapshots[exported] = _identity(blob)
            snapshot_signatures[selected] = _file_signature(selected, MAX_PUBLIC_KEY)
            snapshot_signatures[exported] = _file_signature(exported, MAX_PUBLIC_KEY)
        for name, row in manifest["images"].items():
            copied = work / (name + ".img")
            budget = image_budget(profile, name)
            source_signatures[name] = _copy_image(row["path"], copied, row, budget)
            snapshot_signatures[copied] = _file_signature(copied, budget)
            images[name] = read_image_metadata(copied, name, budget)
        _require(len({sig[:2] for sig in source_signatures.values()}) == len(source_signatures),
                 "different image roles alias one inode")
        validate_metadata(images, profile, public_blobs)
        verified, unverified = [], []
        targets = sorted(images) if inspect_only else ["vbmeta", "boot", "recovery", "vbmeta_system"]
        for name in targets:
            rows = _data_descriptors(images[name])
            required_images = set(rows) - {name}
            required_keys = {r["partition"] for r in rows.values() if r["kind"] == "chain"}
            if images[name]["raw_leaf"] or not required_images <= set(images) or not required_keys <= set(public_blobs):
                unverified.append(name)
                continue
            args = io._python(paths["avbtool"], "verify_image", "--image", work / (name + ".img"))
            if name in SIGNED:
                args += ["--key", keydir / (name + ".pem")]
            if name == "vbmeta":
                for child, location in sorted(profile["chain_locations"].items()):
                    args += ["--expected_chain_partition", f"{child}:{location}:keys/{child}.avbpubkey"]
            checked_native("verify-" + name.replace("_", "-"), args)
            verified.append(name)
        _require(inspect_only or (set(verified) == SIGNED and not unverified),
                 "a complete signed-image verification was not performed")
        for name, row in manifest["images"].items():
            copied = work / (name + ".img")
            _rehash(copied, row, snapshot_signatures[copied])
            _rehash(row["path"], row, source_signatures[name])
        for path, identity in key_snapshots.items():
            _rehash(path, identity, snapshot_signatures[path])
        for name, row in manifest["public_keys"].items():
            _public_pem(row["path"], row)
            _require(_file_signature(row["path"], MAX_PUBLIC_KEY) == source_key_signatures[name],
                     "source public-key identity/mode changed")
        io._unchanged_tools(tools_snapshot)
        _require(_small(manifest_path, MAX_TEXT) == original_manifest, "manifest changed during verification")
        _require(_file_signature(manifest_path, MAX_TEXT) == manifest_signature,
                 "manifest identity/mode changed during verification")
        _require(load_profile()[1] == profile_sha, "profile changed during verification")
        for name, identity in implementation.items():
            _small(ROOT / name, MAX_TEXT, identity)
    return {**base, "status": "artifacts-inspected" if inspect_only else "verified",
            "complete_chain_verified": not inspect_only, "native_commands_run": bool(records),
            "package_budget_fit_verified": True, "inputs_unchanged": True,
            "verified_artifacts": verified, "artifacts_without_native_payload_verification": unverified,
            "partial_results_are_chain_verification": False,
            "public_keys": {name: {k: row[k] for k in ("size_bytes", "sha256", "avb_sha256")}
                            for name, row in manifest["public_keys"].items()},
            "images": {name: {"identity": {k: manifest["images"][name][k] for k in ("size_bytes", "sha256")},
                              "metadata": _safe_report(meta)} for name, meta in images.items()},
            "tools": tool_ids, "native_results": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("verify", "inspect"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, help="new private JSON receipt; existing files are never replaced")
    args = parser.parse_args(argv)
    try:
        result = verify(args.manifest, args.expected_manifest_sha256, inspect_only=args.operation == "inspect")
        if args.output:
            raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
            _require(len(raw) <= MAX_TEXT, "receipt exceeds size bound")
            io._write(args.output, raw)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] != "blocked" else 2
    except (AvbImageSetError, io.TwrpWorkingError, envelope.ImageInspectionError,
            OSError, ValueError, TypeError, KeyError, struct.error) as exc:
        print(json.dumps({"schema_version": 1, "status": "failed", "complete_chain_verified": False,
                          "complete_rom_ready": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
