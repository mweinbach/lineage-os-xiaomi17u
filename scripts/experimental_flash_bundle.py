#!/usr/bin/env python3
"""Copy reviewed Nezha image bytes into a private, non-flash-authorized bundle.

This tool performs no AVB, LP, source, device or hardware qualification. It has
no device commands, subprocesses, network access, signing or image generation.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


BUNDLE_ROOT = Path(__file__).resolve().parents[1] / "artifacts/flash/nezha"
PHYSICAL = ("boot", "dtbo", "init_boot", "recovery", "vbmeta", "vbmeta_system", "vendor_boot")
LOGICAL = ("mi_ext", "odm", "product", "system", "system_dlkm", "system_ext", "vendor", "vendor_dlkm")
REFERENCES = ("countrycode", "pvmfw")
PAYLOADS = (*PHYSICAL, "super")
DEVICE = {"board": "canoe", "codename": "nezha", "soc": "SM8850", "variant": None}
PLATFORM = {"branch": "bka", "release": "bp4a", "page_size_bytes": 4096,
            "normal_android_selinux": "enforcing"}
STATUS = "byte-identities-verified-not-device-admitted-not-flash-ready"
WARNING = ("Writing this shared Super removes the existing logical fallback, including B. "
           "Leaving B physical boot images unchanged does not leave a bootable stock B system.")
LAYOUT = {"candidate_boot_slot": "a", "populated_logical_slot": "a", "empty_logical_slot": "b",
          "physical_super_is_shared_and_unslotted": True, "changes_both_slots_logical_layout": True,
          "preserves_stock_inactive_logical_slot": False, "automatic_reboot": False,
          "automatic_userdata_or_metadata_format": False, "reviewed_write_order": None,
          "slot_switch_is_standalone_fresh_authorization_gate": True}
FALSE_FLAGS = ("flash_ready", "boot_verified", "hardware_verified", "commands_generated",
               "phone_accessed", "private_key_accessed")
PREFLIGHT_FIELDS = frozenset((
    "authorized_exact_device_identifier", "battery_power_usb_and_host_space_sufficient",
    "bootloader_accepts_selected_development_avb_key_under_unlocked_policy",
    "bootloader_mode_and_userspace_fastboot_capabilities",
    "bootloader_recovery_reentry_and_failure_procedure_reviewed", "bootloader_unlocked_confirmed",
    "codename_board_variant_confirmed", "current_slot", "device_preflight_admitted",
    "exact_stock_return_artifacts_and_recovery_companions_reverified",
    "firmware_baseline_compatible_with_selected_vendor_and_kernel", "fresh_collection_authorization",
    "live_logical_metadata_and_current_slot_contents", "live_super_geometry_and_partition_capacities",
    "off_device_personal_data_backup_verified", "retained_countrycode_and_pvmfw_selected_slot_match",
    "slot_count", "slot_success_retry_unbootable_state", "snapshot_update_merge_state_confirmed_idle",
    "stored_avb_rollback_counters_or_reviewed_device_specific_enforcement_evidence",
    "userdata_encryption_migration_or_explicit_fresh_wipe_decision"))
CHUNK = 4 * 1024 * 1024
MAX_TEXT = 1024 * 1024


class BundleError(ValueError):
    """Unsafe, changed, or unreviewed input; no device readiness is implied."""


def require(condition, message):
    if not condition:
        raise BundleError(message)


def digest(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "invalid SHA256")
    return value


def identity(row):
    require(type(row) is dict, "invalid image identity")
    require(type(row.get("size_bytes")) is int and 0 < row["size_bytes"] <= 1 << 40,
            "invalid image size")
    return {"sha256": digest(row.get("sha256")), "size_bytes": row["size_bytes"]}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def absolute(path):
    raw = os.fspath(path)
    require(isinstance(raw, str) and raw.isprintable() and len(raw) <= 4096,
            "invalid path")
    require(os.path.isabs(raw) and str(Path(raw)) == raw and os.path.abspath(raw) == raw,
            "paths must be absolute without traversal or redundant components")
    return Path(raw)


@contextmanager
def directory(path):
    """Traverse using no-follow directory descriptors, including every ancestor."""
    path = absolute(path)
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mode, info.st_nlink,
            info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def input_file(path):
    path = absolute(path)
    with directory(path.parent) as parent:
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                "inputs must be regular files without aliases or hardlinks")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb", buffering=0) as stream:
            def unchanged():
                require(signature(before) == signature(os.fstat(stream.fileno())) ==
                        signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                        "input changed during read")
            unchanged()
            yield stream, before, unchanged


@contextmanager
def json_input(path, expected):
    digest(expected)
    with input_file(path) as (stream, info, unchanged):
        require(0 < info.st_size <= MAX_TEXT, "JSON exceeds size bound")
        raw = stream.read(MAX_TEXT + 1)
        unchanged()
        require(hashlib.sha256(raw).hexdigest() == expected, "JSON digest differs")
        value = json.loads(raw, object_pairs_hook=no_duplicate_keys)
        require(type(value) is dict, "JSON must be an object")
        yield value, unchanged


def pending_preflight(value):
    require(type(value) is dict and set(value) == PREFLIGHT_FIELDS and
            value.get("device_preflight_admitted") is False and
            all(v is None for k, v in value.items() if k != "device_preflight_admitted"),
            "device preflight must remain present, pending and unadmitted")


def avb_safeguards(avb):
    require(type(avb) is dict and avb.get("algorithm") == "SHA256_RSA4096" and
            type(avb.get("flags")) is int and avb["flags"] == 0 and all(avb.get(k) is False for k in
            ("disable_verification_or_verity_allowed", "relock_allowed", "rollback_bypass_allowed")),
            "AVB safeguards differ")
    digest(avb.get("public_key_sha256"))


def validate_plan(plan):
    require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1, "unsupported plan schema")
    require(plan.get("device") == DEVICE and plan.get("platform") == PLATFORM,
            "plan must select nezha/canoe/SM8850 bka/bp4a 4 KiB enforcing")
    require(all(plan.get(k) is False for k in FALSE_FLAGS) and
            plan.get("fresh_experimental_flash_authorization") is None and
            plan.get("source_archive_is_flashable_installer") is False,
            "plan promotes readiness, authorization or installer claims")
    pending_preflight(plan.get("device_preflight"))
    mode = plan.get("delivery_modes", {}).get("current_super_factory_style", {})
    require(all(type(mode.get(k)) is type(v) and mode.get(k) == v for k, v in LAYOUT.items()) and
            mode.get("warning") == WARNING and type(mode.get("payloads")) is list and
            len(mode["payloads"]) == 8 and set(mode["payloads"]) == set(PAYLOADS),
            "plan must preserve shared A-only Super route and its risks")
    rows = plan.get("artifacts")
    require(type(rows) is list and len(rows) == 17, "plan must contain exactly 17 image roles")
    by_role = {}
    for row in rows:
        require(type(row) is dict and type(row.get("role")) is str, "invalid artifact")
        role = row["role"]
        require(role in (*PHYSICAL, *LOGICAL, *REFERENCES) and role not in by_role,
                "unexpected or duplicate image role")
        require(row.get("path") == role + ".img", "artifact path is not its exact role filename")
        expected_role = ("required-physical-slot-image" if role in PHYSICAL else
                         "verification-reference-only-retain-existing-device-firmware" if role in REFERENCES else
                         "embedded-in-current-super-or-separate-logical-image-for-a-different-reviewed-route")
        expected_target = (role + "_a-for-current-super-route" if role in PHYSICAL else
                           role + "_<selected-slot>" if role in REFERENCES else role + "_a")
        require(row.get("delivery_role") == expected_role and row.get("target") == expected_target,
                "artifact delivery role or target differs")
        identity(row)
        by_role[role] = row
    super_info = plan.get("super", {})
    identity(super_info)
    require(super_info.get("expanded_size_bytes") == 15300820992,
            "unexpected Nezha physical Super size")
    avb_safeguards(plan.get("avb_contract"))
    require(set(plan.get("retained_firmware_avb_requirements", {})) == set(REFERENCES),
            "retained firmware requirements are missing")
    return by_role


def manifest_for(plan, plan_sha):
    rows = validate_plan(plan)
    return {
        "schema_version": 1, "status": STATUS, "device": DEVICE, "platform": PLATFORM,
        "reviewed_plan_sha256": digest(plan_sha), "device_preflight": plan["device_preflight"],
        **{key: False for key in FALSE_FLAGS}, "fresh_experimental_flash_authorization": None,
        "validation_scope": "source and copied byte identities only; no fresh AVB, LP, source or hardware validation",
        "delivery": {**LAYOUT, "warning": WARNING},
        "images": [{"role": role, "path": role + ".img", "target": role + "_a" if role != "super" else "super",
                    **identity(rows[role] if role != "super" else plan["super"])} for role in PAYLOADS],
        "super": {"expanded_size_bytes": plan["super"]["expanded_size_bytes"],
                  "populated_logical_partitions": [r + "_a" for r in LOGICAL],
                  "empty_logical_partitions": [r + "_b" for r in LOGICAL]},
        "retained_firmware_references_not_payloads": {
            role: {**identity(rows[role]), "descriptor_requirement": plan["retained_firmware_avb_requirements"][role]}
            for role in REFERENCES},
        "avb_contract_from_plan_not_reverified": plan["avb_contract"],
        "prior_evidence_from_plan_not_reverified": plan.get("evidence", {}),
    }


def support_files(manifest):
    sums = "".join(f"{row['sha256']}  {row['path']}\n" for row in manifest["images"])
    readme = f"""# Experimental Nezha image bundle — NOT FLASH AUTHORIZATION

Evolution X Android 16 QPR2, bka/bp4a, nezha / canoe / SM8850, 4 KiB.
This private bundle contains exactly seven physical images and sparse Super.
Source and copied byte identities matched reviewed plan {manifest['reviewed_plan_sha256']}.
Assembly does not revalidate AVB, LP layout, source provenance or device behavior.
Neither this bundle nor the target-files archive is an OTA or TWRP installer.

WARNING: {WARNING}
Super is shared and unslotted. Only logical A is populated; all logical B images
are empty. Physical images here are candidates for A only. No write order or
device selection has been approved. countrycode and pvmfw are references only;
their images are intentionally absent. Retain and verify existing device firmware.

Device preflight, exact variant, unlocked-key acceptance, rollback counters,
partition capacity, snapshot state, off-device backups, stock return/recovery
procedure and data/encryption handling remain pending. No boot or hardware
success is claimed. A fresh explicit device-action request is still required.
Do not relock, disable verification/verity, bypass rollback, automatically wipe,
cancel snapshots, reboot or activate a slot. This bundle executes none of them.

Keep proprietary images private. Keep the independently supplied manifest SHA256
outside this directory. Run the maintained tool's verify command with that hash
after transfer; SHA256SUMS alone cannot authenticate a changed manifest.
"""
    return {"SHA256SUMS": sums.encode(), "README.md": readme.encode()}


def write_new(parent, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def hash_stream(stream, output=None, limit=1 << 40):
    sha, size = hashlib.sha256(), 0
    while chunk := stream.read(CHUNK):
        sha.update(chunk)
        size += len(chunk)
        require(size <= limit, "image exceeds expected size")
        if output is not None:
            output.write(chunk)
    return {"sha256": sha.hexdigest(), "size_bytes": size}


def assemble(plan_path, expected_plan_sha256, super_path, output):
    completed = []
    with ExitStack() as stack:
        plan, plan_unchanged = stack.enter_context(json_input(plan_path, expected_plan_sha256))
        manifest = manifest_for(plan, expected_plan_sha256)
        rows = {row["role"]: row for row in plan["artifacts"]}
        output = absolute(output)
        require(output != BUNDLE_ROOT and BUNDLE_ROOT in output.parents,
                "assembly destination must be a fresh directory under artifacts/flash/nezha")
        inputs, seen, checks = {}, set(), [plan_unchanged]
        for role in PAYLOADS:
            source = super_path if role == "super" else rows[role]["host_path"]
            inputs[role] = stack.enter_context(input_file(source))
            info = inputs[role][1]
            inode = (info.st_dev, info.st_ino)
            require(inode not in seen, "source roles alias the same file")
            seen.add(inode)
            checks.append(inputs[role][2])
        with directory(output.parent) as parent:
            os.mkdir(output.name, mode=0o700, dir_fd=parent)  # Never reuse any existing output.
            fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            for row in manifest["images"]:
                source, info, unchanged = inputs[row["role"]]
                require(info.st_size == row["size_bytes"], "source image size differs")
                new = os.open(row["path"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=fd)
                with os.fdopen(new, "wb") as target:
                    actual = hash_stream(source, target, row["size_bytes"])
                    target.flush()
                    os.fsync(target.fileno())
                unchanged()
                require(actual == identity(row), "source image digest differs")
                copy, _, stable = stack.enter_context(input_file(output / row["path"]))
                require(hash_stream(copy, limit=row["size_bytes"]) == identity(row), "copied image differs")
                stable()
                checks.append(stable)
                completed.append(row["role"])
            for name, raw in support_files(manifest).items():
                write_new(fd, name, raw)
                stream, info, stable = stack.enter_context(input_file(output / name))
                require(info.st_size == len(raw) and stream.read(len(raw) + 1) == raw,
                        "copied support file differs")
                checks.append(stable)
            for unchanged in checks:
                unchanged()
            expected_names = {row["path"] for row in manifest["images"]} | {"SHA256SUMS", "README.md"}
            require(set(os.listdir(fd)) == expected_names, "unexpected files in assembly output")
            raw = json_bytes(manifest)
            write_new(fd, "manifest.json", raw)  # Success marker is published last.
        except Exception as exc:
            try:
                write_new(fd, "INCOMPLETE.json", json_bytes({"status": "incomplete-not-usable",
                          "flash_ready": False, "completed_roles": completed,
                          "error_type": type(exc).__name__, "error": str(exc)}))
            except OSError:  # A full disk can also prevent writing the failure record.
                pass
            raise
        finally:
            os.close(fd)
    return {"status": STATUS, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "manifest_size_bytes": len(raw), "payload_count": len(PAYLOADS), "flash_ready": False}


def verify(bundle, expected_manifest_sha256):
    bundle = absolute(bundle)
    with ExitStack() as stack:
        manifest, unchanged = stack.enter_context(json_input(bundle / "manifest.json", expected_manifest_sha256))
        return verify_contents(bundle, manifest, expected_manifest_sha256, stack, [unchanged])


def verify_contents(bundle, manifest, expected_manifest_sha256, stack, checks):
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1 and
            manifest.get("status") == STATUS and
            manifest.get("device") == DEVICE and manifest.get("platform") == PLATFORM and
            all(manifest.get(k) is False for k in FALSE_FLAGS) and
            manifest.get("fresh_experimental_flash_authorization") is None,
            "manifest identity, status or safety flags differ")
    pending_preflight(manifest.get("device_preflight"))
    require(json_bytes(manifest.get("delivery")) == json_bytes({**LAYOUT, "warning": WARNING}),
            "manifest layout differs")
    require(set(manifest) == {"schema_version", "status", "device", "platform", "reviewed_plan_sha256",
            "device_preflight", *FALSE_FLAGS, "fresh_experimental_flash_authorization", "validation_scope",
            "delivery", "images", "super", "retained_firmware_references_not_payloads",
            "avb_contract_from_plan_not_reverified", "prior_evidence_from_plan_not_reverified"},
            "unexpected manifest fields")
    require(manifest.get("super") == {"expanded_size_bytes": 15300820992,
            "populated_logical_partitions": [r + "_a" for r in LOGICAL],
            "empty_logical_partitions": [r + "_b" for r in LOGICAL]}, "manifest Super layout differs")
    require(set(manifest.get("retained_firmware_references_not_payloads", {})) == set(REFERENCES),
            "manifest retained firmware references differ")
    avb_safeguards(manifest.get("avb_contract_from_plan_not_reverified"))
    digest(manifest.get("reviewed_plan_sha256"))
    rows = manifest.get("images")
    require(type(rows) is list and len(rows) == len(PAYLOADS), "manifest payload count differs")
    for role, row in zip(PAYLOADS, rows):
        require(type(row) is dict and set(row) == {"role", "path", "target", "sha256", "size_bytes"} and
                row["role"] == role and row["path"] == role + ".img" and
                row["target"] == (role + "_a" if role != "super" else "super"), "manifest image role or path differs")
        identity(row)
    support = support_files(manifest)
    expected_names = {row["path"] for row in rows} | set(support) | {"manifest.json"}
    with directory(bundle) as fd:
        require(set(os.listdir(fd)) == expected_names, "bundle contains missing or extra files")
        for row in rows:
            stream, info, unchanged = stack.enter_context(input_file(bundle / row["path"]))
            require(info.st_size == row["size_bytes"] and
                    hash_stream(stream, limit=row["size_bytes"]) == identity(row), "bundle image differs")
            checks.append(unchanged)
        for name, expected in support.items():
            stream, info, unchanged = stack.enter_context(input_file(bundle / name))
            require(info.st_size == len(expected) and stream.read(len(expected) + 1) == expected,
                    "bundle support file differs")
            checks.append(unchanged)
        for unchanged in checks:
            unchanged()
        require(set(os.listdir(fd)) == expected_names, "bundle file set changed during verification")
    return {"status": STATUS, "manifest_sha256": expected_manifest_sha256,
            "payload_count": len(PAYLOADS), "flash_ready": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("assemble", help="copy exact reviewed bytes; never authorize flashing")
    create.add_argument("--plan", required=True)
    create.add_argument("--expected-plan-sha256", required=True)
    create.add_argument("--super", dest="super_path", required=True)
    create.add_argument("--output", required=True)
    check = sub.add_parser("verify", help="rehash a portable bundle against an independent manifest digest")
    check.add_argument("--bundle", required=True)
    check.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = (assemble(args.plan, args.expected_plan_sha256, args.super_path, args.output)
                  if args.command == "assemble" else verify(args.bundle, args.expected_manifest_sha256))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        print(f"experimental flash bundle: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
