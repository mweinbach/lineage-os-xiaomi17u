#!/usr/bin/env python3
"""Inspect the pinned Nezha RAM-boot wrapper offline, without admitting boot/flash.

This is a separate kernel-containing contract, not the kernel-free dedicated
recovery image. Header v4 is the default; v3 requires explicit selection and an
exact stock-derived command line. Layouts follow mkbootimg 954bc3ead5e679005
and avb c92ce4cb9a1b6d20 sources used by inspect_twrp_image. Hash checks do not
verify the RSA signature, trust its embedded public key, or establish that a
device supports this wrapper. No key files, native tools, or devices are used.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

if __package__:
    from . import inspect_twrp_image as envelope
    from . import twrp_ram_boot_scaffold as scaffold
else:
    import inspect_twrp_image as envelope
    import twrp_ram_boot_scaffold as scaffold


PAGE_SIZE = 4096
HEADER_SIZE = 1584
V3_HEADER_SIZE = 1580
MAX_IMAGE_BYTES = 100663296
MAX_VBMETA_BYTES = 64 * 1024
ROLLBACK_INDEX = 1769904000
ROLLBACK_INDEX_LOCATION = 0
ALGORITHM_TYPE = 2  # AVB_ALGORITHM_TYPE_SHA256_RSA4096.
HASH_DESCRIPTOR = struct.Struct(">QQQ32sIIII60s")
EXPECTED_PROPERTIES = {
    b"com.android.build.boot.os_version": b"16",
    b"com.android.build.boot.security_patch": b"2026-02-01",
}
V3_COMMAND_LINE = (
    "androidboot.hardware=qcom androidboot.memcg=1 "
    "androidboot.usbcontroller=a600000.dwc3 androidboot.load_modules_parallel=true "
    "androidboot.hypervisor.protected_vm.supported=true androidboot.hypervisor.version=gunyah "
    "androidboot.vendor.qspa=true androidboot.serialconsole=0"
)
INIT_LOGGING_SUFFIX = " printk.devkmsg=on"


@dataclass(frozen=True)
class RamBootContract:
    """Expected sizes/hashes; explicit alternatives are for synthetic tests."""

    image_size_bytes: int
    kernel_size_bytes: int
    kernel_sha256: str
    ramdisk_size_bytes: int
    ramdisk_sha256: str
    header_version: int = 4
    command_line: str = ""
    scaffold: bool = False
    ramdisk_suffix_size_bytes: int | None = None
    ramdisk_suffix_sha256: str | None = None
    init_logging: bool = False
    apex_scaffold: bool = False
    config_scaffold: bool = False


EXPECTED_CONTRACT = RamBootContract(
    image_size_bytes=100663296,
    kernel_size_bytes=39963136,
    kernel_sha256="4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8",
    ramdisk_size_bytes=25192233,
    ramdisk_sha256="8713a11b399bec1704bec14f1d06869ec6e615bbaed851945a2ef0e4b74db333",
)
V3_EXPECTED_CONTRACT = replace(EXPECTED_CONTRACT, header_version=3, command_line=V3_COMMAND_LINE)
V3_SCAFFOLD_EXPECTED_CONTRACT = replace(
    V3_EXPECTED_CONTRACT, scaffold=True, ramdisk_size_bytes=25193270,
    ramdisk_sha256="1f1c61c9c8d473d1e9753cc971c13e0d71b23318e6080e5e9615bec7b5d196ff",
    ramdisk_suffix_size_bytes=EXPECTED_CONTRACT.ramdisk_size_bytes,
    ramdisk_suffix_sha256=EXPECTED_CONTRACT.ramdisk_sha256,
)
V3_SCAFFOLD_INITLOG_EXPECTED_CONTRACT = replace(
    V3_SCAFFOLD_EXPECTED_CONTRACT, init_logging=True,
    command_line=V3_COMMAND_LINE + INIT_LOGGING_SUFFIX,
)
V3_APEX_SCAFFOLD_INITLOG_EXPECTED_CONTRACT = replace(
    V3_SCAFFOLD_INITLOG_EXPECTED_CONTRACT, apex_scaffold=True,
    ramdisk_size_bytes=25193784,
    ramdisk_sha256="56c155fe7beed5a836faee93b48e51fe545f58cce112d136d89ba7ef15476dc2",
)
V3_CONFIG_SCAFFOLD_INITLOG_EXPECTED_CONTRACT = replace(
    V3_APEX_SCAFFOLD_INITLOG_EXPECTED_CONTRACT, config_scaffold=True,
    ramdisk_sha256="dbaeab4b0cf35ea537fef9cf9a7cd10586f581ca964782d9ef63b39576f727db",
)


class RamBootInspectionError(ValueError):
    """The input does not satisfy the selected RAM-boot wrapper contract."""


def _require(condition, message):
    if not condition:
        raise RamBootInspectionError(message)


def _contract(contract):
    _require(type(contract) is RamBootContract, "expected an explicit RamBootContract")
    _require(type(contract.header_version) is int and contract.header_version in (3, 4),
             "expected header version must be 3 or 4")
    _require(type(contract.init_logging) is bool, "init logging selection must be boolean")
    if contract.init_logging:
        _require(contract.header_version == 3 and contract.scaffold is True,
                 "init logging requires the explicit v3 scaffold contract")
    _require(type(contract.apex_scaffold) is bool, "apex scaffold selection must be boolean")
    if contract.apex_scaffold:
        _require(contract.header_version == 3 and contract.scaffold is True and contract.init_logging is True,
                 "apex scaffold requires explicit v3 scaffold and init logging")
    _require(type(contract.config_scaffold) is bool, "config scaffold selection must be boolean")
    if contract.config_scaffold:
        _require(contract.header_version == 3 and contract.scaffold is True and contract.init_logging is True
                 and contract.apex_scaffold is True,
                 "config scaffold requires explicit v3 scaffold, init logging and apex")
    expected_command_line = V3_COMMAND_LINE if contract.header_version == 3 else ""
    if contract.init_logging:
        expected_command_line += INIT_LOGGING_SUFFIX
    _require(type(contract.command_line) is str and contract.command_line == expected_command_line,
             "expected contract has an unreviewed command line")
    for size in (contract.image_size_bytes, contract.kernel_size_bytes, contract.ramdisk_size_bytes):
        _require(type(size) is int and 0 < size <= MAX_IMAGE_BYTES, "invalid expected size")
    _require(contract.image_size_bytes % PAGE_SIZE == 0, "expected image size is not page-aligned")
    for digest in (contract.kernel_sha256, contract.ramdisk_sha256):
        _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest), "invalid expected SHA256")
    _require(type(contract.scaffold) is bool, "scaffold selection must be boolean")
    if contract.scaffold:
        _require(contract.header_version == 3, "directory scaffold requires the explicit v3 contract")
        prefix_size = (scaffold.CONFIG_PREFIX_SIZE if contract.config_scaffold else
                       scaffold.APEX_PREFIX_SIZE if contract.apex_scaffold else scaffold.PREFIX_SIZE)
        _require(type(contract.ramdisk_suffix_size_bytes) is int and 0 < contract.ramdisk_suffix_size_bytes <= MAX_IMAGE_BYTES
                 and contract.ramdisk_size_bytes == prefix_size + contract.ramdisk_suffix_size_bytes,
                 "scaffold/suffix sizes differ from the expected ramdisk size")
        _require(type(contract.ramdisk_suffix_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", contract.ramdisk_suffix_sha256),
                 "invalid expected ramdisk suffix SHA256")
    else:
        _require(contract.ramdisk_suffix_size_bytes is None and contract.ramdisk_suffix_sha256 is None,
                 "suffix metadata requires explicit scaffold selection")
    payload_size = PAGE_SIZE + envelope._aligned(contract.kernel_size_bytes) + envelope._aligned(contract.ramdisk_size_bytes)
    _require(payload_size + 2 * PAGE_SIZE <= contract.image_size_bytes, "expected payload has no room for AVB metadata/footer")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _payload(data, start, size, expected_sha, label):
    _, end = envelope._span(start, size, len(data), label)
    padded_end = start + envelope._aligned(size)
    envelope._span(end, padded_end - end, len(data), label + " padding")
    envelope._zero(data, end, padded_end, label + " padding")
    digest = _sha(data[start:end])
    _require(digest == expected_sha, label + " SHA256 differs from expected contract")
    return {"offset_bytes": start, "end_offset_bytes": end, "size_bytes": size,
            "padded_end_offset_bytes": padded_end, "sha256": digest}


def _scaffold_ramdisk(data, contract, image_offset):
    prefix_size = (scaffold.CONFIG_PREFIX_SIZE if contract.config_scaffold else
                   scaffold.APEX_PREFIX_SIZE if contract.apex_scaffold else scaffold.PREFIX_SIZE)
    prefix = scaffold.inspect_scaffold_prefix(bytes(data[:prefix_size]), include_apex=contract.apex_scaffold,
                                              include_config=contract.config_scaffold)
    suffix = data[prefix_size:]
    _require(len(suffix) == contract.ramdisk_suffix_size_bytes
             and _sha(suffix) == contract.ramdisk_suffix_sha256,
             "ramdisk suffix differs from the unchanged expected bytes")
    _require(suffix[:4] == scaffold.LEGACY_MAGIC, "scaffold suffix must retain legacy-LZ4 encoding")
    suffix_envelope = envelope._lz4_envelope(suffix)
    return {
        "compression": {"format": "concatenated-lz4-legacy-archives", "archive_count": 2,
                        "envelope_valid": True, "compressed_blocks_decoded": False,
                        "checksums_verified": False, "full_kernel_decompression_verified": False},
        "scaffold": prefix,
        "canonical_suffix": {"ramdisk_offset_bytes": prefix_size,
                             "image_offset_bytes": image_offset + prefix_size,
                             "size_bytes": len(suffix), "sha256": contract.ramdisk_suffix_sha256,
                             "compression": suffix_envelope,
                             "build66_bytes_verified": len(suffix) == EXPECTED_CONTRACT.ramdisk_size_bytes
                             and contract.ramdisk_suffix_sha256 == EXPECTED_CONTRACT.ramdisk_sha256},
    }


def _boot_avb(data, payload_end):
    avb = envelope._avb(data, payload_end)
    _require(avb["footer_present"] and avb["vbmeta_parsed"], "AVB footer and vbmeta are required")
    _require(avb["original_image_size_bytes"] == avb["vbmeta_offset_bytes"] == payload_end,
             "AVB original image size and metadata offset must equal the padded boot payload")
    offset, size = avb["vbmeta_offset_bytes"], avb["vbmeta_size_bytes"]
    _require(256 <= size <= MAX_VBMETA_BYTES, "vbmeta exceeds supported bounds")
    _require(envelope._aligned(offset + size) <= len(data) - PAGE_SIZE, "AVB metadata overlaps the footer page")
    blob = data[offset:offset + size]
    meta = avb["vbmeta"]
    _require(meta["required_libavb_version"] == [1, 0], "expected libavb requirement 1.0")
    _require(meta["algorithm_type"] == ALGORITHM_TYPE, "expected SHA256_RSA4096 AVB algorithm")
    _require(meta["flags"] == 0, "AVB flags must be zero")
    _require(meta["rollback_index"] == ROLLBACK_INDEX and meta["rollback_index_location"] == ROLLBACK_INDEX_LOCATION,
             "unexpected AVB rollback index or location")
    auth_size, aux_size = meta["authentication_size_bytes"], meta["auxiliary_size_bytes"]
    pairs = [struct.unpack_from(">QQ", blob, field) for field in range(32, 112, 16)]
    (hash_offset, hash_size), (sig_offset, sig_size), (key_offset, key_size), (pkmd_offset, pkmd_size), (desc_offset, desc_size) = pairs
    _require(auth_size == 576 and (hash_offset, hash_size, sig_offset, sig_size) == (0, 32, 32, 512),
             "unexpected RSA4096 authentication spans")
    _require(desc_offset == 0 and key_offset == desc_size and key_size == 1032
             and pkmd_offset == key_offset + key_size and pkmd_size == 0
             and aux_size == (key_offset + key_size + 63) // 64 * 64,
             "unexpected AVB descriptor/key/metadata spans")
    release = bytes(blob[128:176])
    envelope._zero(blob, 128 + release.index(0), 176, "AVB release-string padding")
    authentication = blob[256:256 + auth_size]
    auxiliary = blob[256 + auth_size:]
    envelope._zero(authentication, sig_offset + sig_size, auth_size, "AVB authentication padding")
    envelope._zero(auxiliary, key_offset + key_size, aux_size, "AVB auxiliary padding")
    _require(struct.unpack_from(">I", auxiliary, key_offset)[0] == 4096, "AVB public-key bit count differs from RSA4096")
    computed_auth = hashlib.sha256()
    computed_auth.update(blob[:256])
    computed_auth.update(auxiliary)
    _require(bytes(authentication[:32]) == computed_auth.digest(), "AVB authentication hash mismatch")
    descriptors = meta["descriptor_headers"]
    _require(len(descriptors) == 3 and [row["tag"] for row in descriptors] == [2, 0, 0],
             "expected one boot hash descriptor and two boot properties only")
    hash_desc_size = descriptors[0]["size_bytes"]
    _require(HASH_DESCRIPTOR.size <= hash_desc_size <= desc_size, "truncated boot hash descriptor")
    descriptor = auxiliary[:hash_desc_size]
    tag, following, image_size, algorithm, partition_len, salt_len, digest_len, flags, reserved = HASH_DESCRIPTOR.unpack_from(descriptor)
    _require(tag == 2 and following + 16 == hash_desc_size, "invalid boot hash descriptor size")
    _require(image_size == payload_end, "boot hash descriptor covers the wrong image span")
    _require(algorithm == b"sha256" + bytes(26), "boot hash descriptor must use SHA256")
    _require(partition_len == 4 and digest_len == 32 and flags == 0, "invalid boot partition/digest length or descriptor flags")
    _require(not any(reserved), "nonzero boot hash descriptor reserved bytes")
    variable_end = HASH_DESCRIPTOR.size + partition_len + salt_len + digest_len
    _require((variable_end + 7) // 8 * 8 == hash_desc_size, "boot hash descriptor variable spans differ")
    partition_start = HASH_DESCRIPTOR.size
    salt_start = partition_start + partition_len
    digest_start = salt_start + salt_len
    _require(bytes(descriptor[partition_start:salt_start]) == b"boot", "hash descriptor partition must be boot")
    envelope._zero(descriptor, variable_end, hash_desc_size, "boot hash descriptor padding")
    salt = descriptor[salt_start:digest_start]
    digest = bytes(descriptor[digest_start:variable_end])
    computed_digest = hashlib.sha256()
    computed_digest.update(salt)
    computed_digest.update(data[:image_size])
    _require(digest == computed_digest.digest(), "salted boot image digest mismatch")
    properties = {}
    position = hash_desc_size
    for row in descriptors[1:]:
        prop = auxiliary[position:position + row["size_bytes"]]
        _require(len(prop) >= 32, "truncated AVB property descriptor")
        _, following, key_len, value_len = struct.unpack_from(">4Q", prop)
        value_start = 32 + key_len + 1
        value_end = value_start + value_len
        _require(0 < key_len <= 128 and 0 < value_len <= 64
                 and (value_end + 1 + 7) // 8 * 8 == len(prop) == following + 16,
                 "invalid AVB property spans")
        key, value = bytes(prop[32:32 + key_len]), bytes(prop[value_start:value_end])
        _require(key in EXPECTED_PROPERTIES and key not in properties and value == EXPECTED_PROPERTIES[key],
                 "unexpected, duplicate, or changed AVB boot property")
        envelope._zero(prop, 32 + key_len, value_start, "AVB property key terminator")
        envelope._zero(prop, value_end, len(prop), "AVB property terminator/padding")
        properties[key] = value
        row["payload_semantics_parsed"] = True
        position += len(prop)
    _require(position == desc_size and set(properties) == set(EXPECTED_PROPERTIES), "missing AVB boot property")
    meta.update(algorithm_name="SHA256_RSA4096", authentication_hash_verified=True,
                descriptor_payloads_verified=True, reserved_and_padding_zero=True)
    meta["descriptor_headers"][0]["payload_semantics_parsed"] = True
    avb["hash_descriptor"] = {
        "partition_name": "boot", "hash_algorithm": "sha256", "flags": flags,
        "offset_bytes": offset + 256 + auth_size, "size_bytes": hash_desc_size,
        "image_offset_bytes": 0, "image_size_bytes": image_size,
        "salt_size_bytes": salt_len, "salt_sha256": _sha(salt),
        "digest_hex": digest.hex(), "digest_verified": True,
    }
    avb["public_key"] = {"offset_bytes": offset + 256 + auth_size + key_offset,
                         "size_bytes": key_size, "sha256": _sha(auxiliary[key_offset:key_offset + key_size]),
                         "bit_count": 4096, "trusted_key_verified": False}
    avb["properties"] = {key.decode("ascii"): value.decode("ascii") for key, value in properties.items()}
    return avb


def inspect_bytes(data, *, contract=EXPECTED_CONTRACT):
    """Pure structural parser of immutable bytes using an explicit expected contract."""
    _contract(contract)
    _require(type(data) is bytes, "image input must be immutable bytes")
    _require(len(data) == contract.image_size_bytes, "image size differs from expected contract")
    view = memoryview(data)
    try:
        _require(view[:8] == b"ANDROID!", "invalid Android boot-image magic")
        kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", view, 8)
        version = struct.unpack_from("<I", view, 40)[0]
        expected_header_size = V3_HEADER_SIZE if contract.header_version == 3 else HEADER_SIZE
        _require(version == contract.header_version and header_size == expected_header_size,
                 f"expected Android header v{contract.header_version} of size {expected_header_size}")
        _require(os_version == 0, "OS version must be zero")
        if version == 4:
            signature_size = struct.unpack_from("<I", view, 1580)[0]
            _require(signature_size == 0, "boot signature size must be zero")
        _require(kernel_size == contract.kernel_size_bytes and ramdisk_size == contract.ramdisk_size_bytes,
                 "header kernel/ramdisk sizes differ from expected contract")
        envelope._zero(view, 24, 40, "Android header reserved bytes")
        command_line = contract.command_line.encode("ascii")
        if version == 3:
            _require(bytes(view[44:1580]) == command_line.ljust(1536, b"\0"),
                     "Android command line differs from expected v3 contract")
        else:
            envelope._zero(view, 44, 1580, "Android command line")
        envelope._zero(view, expected_header_size, PAGE_SIZE, "Android header padding")
        kernel = _payload(view, PAGE_SIZE, kernel_size, contract.kernel_sha256, "kernel")
        ramdisk = _payload(view, kernel["padded_end_offset_bytes"], ramdisk_size, contract.ramdisk_sha256, "ramdisk")
        ramdisk_bytes = view[ramdisk["offset_bytes"]:ramdisk["end_offset_bytes"]]
        if contract.scaffold:
            ramdisk.update(_scaffold_ramdisk(ramdisk_bytes, contract, ramdisk["offset_bytes"]))
        else:
            ramdisk["compression"] = envelope._lz4_envelope(ramdisk_bytes)
        payload_end = ramdisk["padded_end_offset_bytes"]
        avb = _boot_avb(view, payload_end)
    except (envelope.ImageInspectionError, scaffold.ScaffoldError) as exc:
        raise RamBootInspectionError(str(exc)) from exc
    pinned_contract = contract in (EXPECTED_CONTRACT, V3_EXPECTED_CONTRACT, V3_SCAFFOLD_EXPECTED_CONTRACT,
                                   V3_SCAFFOLD_INITLOG_EXPECTED_CONTRACT, V3_APEX_SCAFFOLD_INITLOG_EXPECTED_CONTRACT,
                                   V3_CONFIG_SCAFFOLD_INITLOG_EXPECTED_CONTRACT)
    header = {"version": version, "size_bytes": header_size, "page_size_bytes": PAGE_SIZE,
              "kernel_size_bytes": kernel_size, "ramdisk_size_bytes": ramdisk_size, "os_version_raw": 0,
              "command_line_empty": not command_line, "command_line": contract.command_line,
              "command_line_size_bytes": len(command_line), "command_line_sha256": _sha(command_line),
              "init_logging_selected": contract.init_logging,
              "padded_payload_size_bytes": payload_end, "reserved_and_padding_zero": True}
    if version == 4:
        header["boot_signature_size_bytes"] = signature_size
    return {
        "schema_version": 1, "operation": "inspect-twrp-ram-boot",
        "status": "structurally_valid_expected_ram_boot_wrapper",
        "contract": {**asdict(contract), "stock_kernel_build66_contract_selected": pinned_contract,
                     "image_role": "ram-boot-wrapper", "physical_phone_capacity_verified": False},
        "image": {"size_bytes": len(data), "sha256": _sha(view)},
        "header": header,
        "kernel": kernel, "ramdisk": ramdisk, "avb": avb,
        "validation": {
            "structurally_valid": True, "expected_payload_hashes_verified": True,
            "boot_hash_descriptor_verified": True, "reserved_and_padding_zero": True,
            "stock_kernel_build66_payloads_verified": pinned_contract,
            "directory_scaffold_verified": contract.scaffold, "full_kernel_decompression_verified": False,
            "empty_apex_directory_verified": contract.apex_scaffold,
            "apex_packages_verified": False, "apex_runtime_verified": False,
            "empty_config_directory_verified": contract.config_scaffold,
            "configfs_mount_verified": False, "usb_runtime_verified": False,
            "kernel_devkmsg_ratelimit_behavior_verified": False,
            "signature_verified": False, "trusted_key_verified": False, "avb_trusted": False,
            "ramdisk_decompressed": False, "twrp_contents_verified": False,
            "compiled_selinux_policy_verified": False, "boot_tested": False,
            "authenticated_adb_verified": False, "runtime_verified": False,
            "rollback_compatibility_verified": False, "device_compatibility_verified": False,
            "flash_admitted": False, "phone_accessed": False, "image_mutated": False,
        },
    }


def inspect_image(path, *, contract=EXPECTED_CONTRACT):
    """Read one stable regular file with anchored, nonsymlink path traversal."""
    _contract(contract)
    try:
        path = envelope._absolute_path(path)
        with envelope._parent_directory(path) as parent:
            initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            _require(stat.S_ISREG(initial.st_mode), "image is not a regular file")
            before = envelope._signature(initial)
            _require(before[2] == contract.image_size_bytes, "image size differs from expected contract")
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, "rb") as stream:
                details = os.fstat(stream.fileno())
                _require(stat.S_ISREG(details.st_mode) and before == envelope._signature(details), "image changed before read")
                data = stream.read(before[2] + 1)
                _require(len(data) == before[2], "image changed or was truncated while read")
                report = inspect_bytes(data, contract=contract)
                _require(before == envelope._signature(os.fstat(stream.fileno()))
                         and before == envelope._signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                         "image changed while inspected")
    except envelope.ImageInspectionError as exc:
        raise RamBootInspectionError(str(exc)) from exc
    report["image"]["name"] = path.name
    report["validation"]["input_stable_during_read"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="regular RAM-boot wrapper to inspect read-only")
    parser.add_argument("--header-version", type=int, choices=(3, 4), default=4,
                        help="explicit wrapper contract; defaults to v4")
    parser.add_argument("--scaffold", action="store_true", help="verify the exact directory-only prefix; requires --header-version 3")
    parser.add_argument("--init-logging", action="store_true",
                        help="require only the reviewed printk.devkmsg=on addition; requires --header-version 3 --scaffold")
    parser.add_argument("--apex", action="store_true",
                        help="require the eight-directory prefix with empty /apex; requires v3, scaffold and init logging")
    parser.add_argument("--usb-config", action="store_true",
                        help="require the nine-directory prefix with empty /config; requires v3, scaffold, init logging and apex")
    parser.add_argument("--output", type=Path, help="new metadata .json report; existing paths are never replaced")
    args = parser.parse_args(argv)
    if args.usb_config and (args.header_version != 3 or not args.scaffold or not args.init_logging or not args.apex):
        parser.error("--usb-config requires --header-version 3 --scaffold --init-logging --apex")
    if args.apex and (args.header_version != 3 or not args.scaffold or not args.init_logging):
        parser.error("--apex requires --header-version 3 --scaffold --init-logging")
    if args.init_logging and (args.header_version != 3 or not args.scaffold):
        parser.error("--init-logging requires --header-version 3 --scaffold")
    if args.scaffold and args.header_version != 3:
        parser.error("--scaffold requires --header-version 3")
    try:
        contract = (V3_CONFIG_SCAFFOLD_INITLOG_EXPECTED_CONTRACT if args.usb_config else
                    V3_APEX_SCAFFOLD_INITLOG_EXPECTED_CONTRACT if args.apex else
                    V3_SCAFFOLD_INITLOG_EXPECTED_CONTRACT if args.init_logging else
                    V3_SCAFFOLD_EXPECTED_CONTRACT if args.scaffold else
                    V3_EXPECTED_CONTRACT if args.header_version == 3 else EXPECTED_CONTRACT)
        report = inspect_image(args.image, contract=contract)
        if args.output is not None:
            envelope.write_report(args.output, report)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (RamBootInspectionError, envelope.ImageInspectionError, envelope.IntakeError, OSError) as exc:
        print(f"RAM-boot image inspection failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
