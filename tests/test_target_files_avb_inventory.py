"""Offline target-files inventory tests: synthetic bytes are not ROM evidence.

No real image, key, guest, native process or device is used. The ZIP payloads
are deliberately not Android images. Passing inventory must not claim otherwise.
"""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile
import zlib

from scripts import target_files_avb_inventory as inventory

REAL_LOAD_CONTRACT = inventory.signing.load_contract


# Explicit fixture roles make omissions detectable independently of the helper.
FINAL_ROLES = frozenset((
    "boot", "dtbo", "init_boot", "mi_ext", "odm", "product", "recovery",
    "system", "system_dlkm", "system_ext", "vendor", "vendor_boot", "vendor_dlkm",
))
GENERATED_ROLES = frozenset(("vbmeta", "vbmeta_system"))
RAW_ROLES = frozenset(("countrycode", "pvmfw"))
DYNAMIC_ROLES = frozenset((
    "mi_ext", "odm", "product", "system", "system_dlkm", "system_ext", "vendor", "vendor_dlkm",
))
SCOPE_FIELDS = frozenset((
    "image_format_verified", "signatures_verified", "complete_chain_verified",
    "fec_payload_verified", "source_provenance_verified", "target_files_compatibility_verified",
    "physical_partition_fit_verified", "runtime_verified", "complete_rom_ready",
    "native_commands_run", "private_key_or_local_config_accessed", "images_extracted_or_modified",
    "signing_manifest_created", "guest_accessed", "phone_accessed",
))
REQUIRED_METADATA = frozenset((
    "META/misc_info.txt", "META/dynamic_partitions_info.txt",
    "META/ab_partitions.txt", "META/vbmeta_digest.txt",
))


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def json_bytes(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


def inert_image(name):
    raw = ("SYNTHETIC NONBOOTABLE INVENTORY FIXTURE " + name + "\n").encode()
    return raw + bytes(4096 - len(raw))


class TargetFilesAvbInventoryTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native execution forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("shell execution forbidden")))
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-target-files-avb-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.archive = self.root / "synthetic-target-files.zip"
        self.images = {name: inert_image(name) for name in FINAL_ROLES | GENERATED_ROLES | RAW_ROLES}
        dynamic = " ".join(sorted(DYNAMIC_ROLES))
        self.members = {"IMAGES/" + name + ".img": self.images[name]
                        for name in FINAL_ROLES | GENERATED_ROLES}
        self.members.update({
            "META/misc_info.txt": ("avb_enable=true\nuse_dynamic_partitions=true\n"
                                   "dynamic_partition_list=" + dynamic + "\n").encode(),
            "META/dynamic_partitions_info.txt": ("use_dynamic_partitions=true\n"
                                                 "dynamic_partition_list=" + dynamic + "\n").encode(),
            "META/ab_partitions.txt": ("\n".join(sorted(FINAL_ROLES | GENERATED_ROLES)) + "\n").encode(),
            "META/vbmeta_digest.txt": b"a" * 64 + b"\n",
        })
        self.profile = {
            "profile_id": "nezha-avb-image-set-v1",
            "image_budgets": {name: 16384 for name in self.images},
            "logical_partitions": sorted(DYNAMIC_ROLES),
            "raw_leaf_partitions": sorted(RAW_ROLES),
            "logical_group_budget": 8 * 16384,
            "working76": {"image": identity(self.images["recovery"])},
        }
        self.profile_sha = identity(json_bytes(self.profile))["sha256"]
        self.factory_record = self.root / "synthetic-factory-extraction.json"
        self.factory_record.write_bytes(b'{"synthetic":true,"device_operations":false}\n')
        self.factory_identity = identity(self.factory_record.read_bytes())
        self.contract = {
            "contract_id": "nezha-host-avb-signing-v1",
            "input_partitions": sorted(FINAL_ROLES | RAW_ROLES),
            "verifier_profile": {"sha256": self.profile_sha},
            "raw_descriptor_sources": {name: {"image": identity(self.images[name])} for name in RAW_ROLES},
            "source_evidence": [{"path": "research/factory-firmware-validation.json", **self.factory_identity}],
        }
        self.contract_sha = identity(json_bytes(self.contract))["sha256"]
        self.enterContext(mock.patch.object(inventory.signing, "load_contract", side_effect=self.load_contract))
        self.enterContext(mock.patch.object(inventory, "_factory_record", return_value=self.factory_identity))
        self.retained = self.root / "retained-inputs.json"
        self.retained_value = {
            "schema_version": 1, "contract_id": "nezha-host-avb-signing-v1",
            "contract_sha256": self.contract_sha, "artifact_set_id": "synthetic-not-a-rom",
            "images": {}, "source_records": [{"path": self.factory_record.name, **self.factory_identity}],
        }
        for name in RAW_ROLES:
            path = self.root / (name + ".raw")
            path.write_bytes(self.images[name])
            self.retained_value["images"][name] = {"path": path.name, **identity(self.images[name])}
        self.save_retained()

    def load_contract(self):
        return deepcopy(self.contract), self.contract_sha, deepcopy(self.profile), self.profile_sha

    def save_retained(self):
        raw = json_bytes(self.retained_value)
        self.retained.write_bytes(raw)
        return identity(raw)["sha256"]

    def write_zip(self, *, members=None, extra=(), modes=None, compression=zipfile.ZIP_STORED):
        rows = list((self.members if members is None else members).items()) + list(extra)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # Intentional duplicate-name fixtures.
            with zipfile.ZipFile(self.archive, "w") as archive:
                for name, raw in rows:
                    entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    mode = (modes or {}).get(name, stat.S_IFREG | 0o600)
                    entry.external_attr = mode << 16
                    entry.compress_type = compression
                    archive.writestr(entry, raw)
        return identity(self.archive.read_bytes())

    def inspect(self, *, retained=False, wanted=None, archive=None):
        chosen = self.archive if archive is None else archive
        expected = identity(self.archive.read_bytes()) if wanted is None else wanted
        kwargs = ({"retained_input_manifest": self.retained,
                   "expected_retained_manifest_sha256": identity(self.retained.read_bytes())["sha256"]}
                  if retained else {})
        return inventory.inspect_target_files(chosen, expected, **kwargs)

    def assert_scope_false(self, report):
        self.assertEqual(SCOPE_FIELDS, set(report["scope"]))
        self.assertTrue(all(value is False for value in report["scope"].values()))
        json.dumps(report)  # API returns a serializable report, including failures.

    def assert_blocked(self, report, *, require_errors=True):
        self.assertEqual("blocked", report["status"])
        self.assertIs(report["complete_input_inventory"], False)
        if require_errors:
            self.assertTrue(report["errors"])
        self.assert_scope_false(report)

    def patch_member_headers(self, name, *, flags=None, compression=None, size=None):
        """Edit independent ZIP fixture headers without repairing CRC/data bytes."""
        raw = bytearray(self.archive.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            local = archive.getinfo(name).header_offset
            central = archive.start_dir
        while raw[central:central + 4] == b"PK\x01\x02":
            nl, el, cl = struct.unpack_from("<HHH", raw, central + 28)
            selected = bytes(raw[central + 46:central + 46 + nl]).decode() == name
            if selected:
                break
            central += 46 + nl + el + cl
        self.assertEqual(b"PK\x01\x02", raw[central:central + 4])
        for value, local_at, central_at, fmt in (
            (flags, 6, 8, "<H"), (compression, 8, 10, "<H"), (size, 22, 24, "<I"),
        ):
            if value is not None:
                struct.pack_into(fmt, raw, local + local_at, value)
                struct.pack_into(fmt, raw, central + central_at, value)
        self.archive.write_bytes(raw)

    def test_valid_zip_without_raw_inputs_is_incomplete_and_cannot_claim_validation(self):
        self.write_zip()
        report = self.inspect()
        self.assert_blocked(report, require_errors=False)
        self.assertIs(report["complete_zip_role_inventory"], True)
        self.assertEqual(sorted(RAW_ROLES), report["missing_retained_inputs"])
        self.assertEqual(FINAL_ROLES, set(report["final_images"]))
        self.assertEqual(GENERATED_ROLES, set(report["generated_vbmeta_images"]))
        self.assertEqual(REQUIRED_METADATA, set(report["metadata"]))
        for name, row in report["final_images"].items():
            self.assertEqual(identity(self.images[name]), {key: row[key] for key in ("sha256", "size_bytes")})

    def test_exact_retained_raw_inputs_complete_inventory_but_not_image_or_signature_validation(self):
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        before = {p.name: identity(p.read_bytes()) for p in self.root.iterdir()}
        report = self.inspect(retained=True)
        self.assertEqual("complete", report["status"])
        self.assertIs(report["complete_input_inventory"], True)
        self.assertIs(report["complete_zip_role_inventory"], True)
        self.assertEqual([], report["missing_retained_inputs"])
        self.assertEqual([], report["errors"])
        self.assert_scope_false(report)
        self.assertEqual(before, {p.name: identity(p.read_bytes()) for p in self.root.iterdir()})

    def test_reviewed_logical_override_admits_image_above_stock_member_bound(self):
        role = "system_ext"
        self.images[role] = inert_image(role) + bytes(4 * 4096)
        self.members["IMAGES/" + role + ".img"] = self.images[role]
        self.profile["dynamic_logical_budget_overrides"] = {
            role: {"stock_budget_bytes": self.profile["image_budgets"][role],
                   "maximum_size_bytes": len(self.images[role]),
                   "measured_image": identity(self.images[role])}}
        self.write_zip()
        report = self.inspect(retained=True)
        self.assertEqual("complete", report["status"], report["errors"])
        self.assertGreater(report["final_images"][role]["size_bytes"],
                           self.profile["image_budgets"][role])
        self.assertLessEqual(report["final_images"][role]["size_bytes"],
                             inventory.avb.image_budget(self.profile, role))

        substituted = bytearray(self.images[role])
        substituted[-1] = 1
        self.members["IMAGES/" + role + ".img"] = bytes(substituted)
        self.write_zip()
        blocked = self.inspect(retained=True)
        self.assertEqual("blocked", blocked["status"])
        self.assertTrue(blocked["errors"])

    def test_generated_metadata_is_not_a_final_signing_input(self):
        self.write_zip()
        report = self.inspect(retained=True)
        self.assertEqual(GENERATED_ROLES, set(report["generated_vbmeta_images"]))
        self.assertTrue(GENERATED_ROLES.isdisjoint(report["final_images"]))
        for name, row in report["generated_vbmeta_images"].items():
            self.assertEqual(identity(self.images[name]), {key: row[key] for key in ("sha256", "size_bytes")})
        self.assert_scope_false(report)

    def test_recovery_must_match_working76_even_for_inventory_only(self):
        members = dict(self.members)
        members["IMAGES/recovery.img"] = inert_image("unapproved-recovery")
        self.write_zip(members=members)
        self.assert_blocked(self.inspect(retained=True))

    def test_optional_public_metadata_is_hashed_without_interpretation(self):
        optional = {"META/" + name: b"synthetic opaque public record " + name.encode()
                    for name in ("apkcerts.txt", "apexkeys.txt", "otakeys.txt", "apex_info.pb",
                                 "care_map.pb", "care_map.txt")}
        optional.update({name: b"INERT PUBLIC RECORD; NOT A KEY OR CERTIFICATE\n" for name in (
            "META/otacert", "SYSTEM/etc/security/otacerts.zip",
            "RECOVERY/RAMDISK/system/etc/security/otacerts.zip", "RECOVERY/RAMDISK/res/keys",
        )})
        self.write_zip(extra=optional.items())
        report = self.inspect(retained=True)
        self.assertEqual("complete", report["status"])
        for name, raw in optional.items():
            row = report["metadata"][name]
            self.assertEqual(identity(raw), {key: row[key] for key in ("sha256", "size_bytes")})
        self.assert_scope_false(report)

    def test_duplicate_unconsumed_metadata_keys_do_not_reject_legacy_dump_output(self):
        members = dict(self.members)
        for name in ("META/misc_info.txt", "META/dynamic_partitions_info.txt"):
            members[name] += b"build_non_sparse_super_partition=true\nbuild_non_sparse_super_partition=true\n"
        self.write_zip(members=members)
        report = self.inspect(retained=True)
        self.assertEqual("complete", report["status"])
        self.assert_scope_false(report)

    def test_equal_and_different_aliases_are_reported_without_fallback(self):
        same = "BOOTABLE_IMAGES/boot.img"
        different = "PREBUILT_IMAGES/boot.img"
        self.write_zip(extra=((same, self.images["boot"]), (different, inert_image("older-boot"))))
        report = self.inspect(retained=True)
        self.assertEqual("complete", report["status"])
        self.assertEqual({same, different}, set(report["aliases"]))
        self.assertEqual("boot", report["aliases"][same]["image_role"])
        self.assertIs(report["aliases"][same]["matches_final_image"], True)
        self.assertIs(report["aliases"][different]["matches_final_image"], False)
        members = dict(self.members)
        del members["IMAGES/boot.img"]
        self.write_zip(members=members, extra=((same, self.images["boot"]),))
        self.assert_blocked(self.inspect(retained=True), require_errors=False)

    def test_legitimate_unselected_android_symlink_is_not_extracted_or_rejected(self):
        name = "SYSTEM/bin/sh"
        self.write_zip(extra=((name, b"mksh"),), modes={name: stat.S_IFLNK | 0o777})
        report = self.inspect(retained=True)
        self.assertEqual("complete", report["status"])
        self.assertFalse((self.root / "SYSTEM").exists())
        self.assert_scope_false(report)

    def test_missing_each_required_image_or_metadata_member_blocks(self):
        for name in sorted(self.members):
            with self.subTest(member=name):
                members = dict(self.members)
                del members[name]
                self.write_zip(members=members)
                self.assert_blocked(self.inspect(retained=True), require_errors=False)

    def test_duplicate_names_are_rejected_even_with_identical_bytes(self):
        for name in ("IMAGES/boot.img", "META/misc_info.txt", "SYSTEM/unselected.txt"):
            with self.subTest(member=name):
                raw = self.members.get(name, b"synthetic")
                extra = [(name, raw)] if name in self.members else [(name, raw), (name, raw)]
                self.write_zip(extra=extra)
                self.assert_blocked(self.inspect(retained=True))

    def test_noncanonical_and_traversal_names_are_rejected(self):
        for name in ("../outside", "/IMAGES/boot.img", "IMAGES/../boot.img",
                     "IMAGES//boot.img", "./IMAGES/boot.img", "IMAGES\\boot.img"):
            with self.subTest(member=name):
                self.write_zip(extra=((name, b"synthetic"),))
                self.assert_blocked(self.inspect(retained=True))

    def test_nul_filename_is_not_silently_truncated_to_a_canonical_image(self):
        members = dict(self.members)
        members["IMAGES/boot.imgX"] = members.pop("IMAGES/boot.img")
        self.write_zip(members=members)
        raw = self.archive.read_bytes()
        self.assertEqual(2, raw.count(b"IMAGES/boot.imgX"))
        self.archive.write_bytes(raw.replace(b"IMAGES/boot.imgX", b"IMAGES/boot.img\0"))
        self.assert_blocked(self.inspect(retained=True))

    def test_case_aliases_cannot_supply_or_shadow_selected_roles(self):
        for name in ("images/boot.img", "IMAGES/BOOT.img", "IMAGES/boot.IMG",
                     "meta/misc_info.txt", "BOOTABLE_IMAGES/BOOT.img"):
            with self.subTest(member=name):
                self.write_zip(extra=((name, self.images["boot"]),))
                self.assert_blocked(self.inspect(retained=True))

    def test_selected_image_and_metadata_entries_must_be_regular(self):
        for name in ("IMAGES/boot.img", "META/misc_info.txt", "BOOTABLE_IMAGES/boot.img"):
            for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK, stat.S_IFDIR):
                with self.subTest(member=name, kind=kind):
                    extra = () if name in self.members else ((name, self.images["boot"]),)
                    self.write_zip(extra=extra, modes={name: kind | 0o600})
                    self.assert_blocked(self.inspect(retained=True))

    def test_selected_parent_entry_cannot_be_a_file_or_symlink(self):
        for name in ("IMAGES", "IMAGES/", "META", "META/"):
            for kind in (stat.S_IFREG, stat.S_IFLNK):
                with self.subTest(member=name, kind=kind):
                    self.write_zip(extra=((name, b"synthetic-parent"),), modes={name: kind | 0o700})
                    self.assert_blocked(self.inspect(retained=True))

    def test_selected_entries_reject_encryption_and_unsupported_compression(self):
        for field, value in (("flags", 1), ("compression", 99)):
            for name in ("IMAGES/boot.img", "META/misc_info.txt"):
                with self.subTest(field=field, member=name):
                    self.write_zip()
                    self.patch_member_headers(name, **{field: value})
                    self.assert_blocked(self.inspect(retained=True))

    def test_selected_local_and_central_compression_or_flags_must_agree(self):
        for offset in (6, 8):
            with self.subTest(local_header_offset=offset):
                self.write_zip()
                raw = bytearray(self.archive.read_bytes())
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    start = archive.getinfo("IMAGES/boot.img").header_offset
                struct.pack_into("<H", raw, start + offset, 8)
                self.archive.write_bytes(raw)
                self.assert_blocked(self.inspect(retained=True))

    def test_crc_corruption_is_rejected_even_when_whole_archive_identity_matches(self):
        self.write_zip()
        raw = bytearray(self.archive.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            start = archive.getinfo("IMAGES/boot.img").header_offset
        name_len, extra_len = struct.unpack_from("<HH", raw, start + 26)
        raw[start + 30 + name_len + extra_len + 128] ^= 1
        self.archive.write_bytes(raw)
        self.assert_blocked(self.inspect(retained=True))

    def test_empty_oversize_and_false_declared_image_sizes_block(self):
        for raw in (b"", b"x" * 16385):
            with self.subTest(size=len(raw)):
                members = dict(self.members)
                members["IMAGES/boot.img"] = raw
                self.write_zip(members=members)
                self.assert_blocked(self.inspect(retained=True))
        self.write_zip()
        self.patch_member_headers("IMAGES/boot.img", size=16385)
        self.assert_blocked(self.inspect(retained=True))

    def test_bad_archive_hash_size_and_identity_schema_block(self):
        wanted = self.write_zip()
        for changed in ({**wanted, "sha256": "0" * 64}, {**wanted, "size_bytes": wanted["size_bytes"] + 1},
                        {**wanted, "size_bytes": True}, {**wanted, "sha256": "F" * 64},
                        {"sha256": wanted["sha256"]}, {**wanted, "extra": "unreviewed"}):
            with self.subTest(identity=changed):
                self.assert_blocked(self.inspect(retained=True, wanted=changed))

    def test_nonzip_truncated_and_missing_archives_return_blocked_reports(self):
        for raw in (b"not a zip archive", b"PK\x03\x04", b""):
            with self.subTest(raw=raw):
                self.archive.write_bytes(raw)
                self.assert_blocked(self.inspect(retained=True))
        wanted = self.write_zip()
        self.assert_blocked(self.inspect(archive=self.root / "missing.zip", wanted=wanted))

    def test_archive_symlink_hardlink_directory_and_symlink_parent_are_rejected(self):
        wanted = self.write_zip()
        alias = self.root / "alias.zip"
        alias.symlink_to(self.archive)
        self.assert_blocked(self.inspect(archive=alias, wanted=wanted))
        alias.unlink()
        os.link(self.archive, alias)
        self.assert_blocked(self.inspect(archive=self.archive, wanted=wanted))
        alias.unlink()
        self.assert_blocked(self.inspect(archive=self.root, wanted=wanted))
        parent = self.root / "parent-alias"
        parent.symlink_to(self.root, target_is_directory=True)
        self.assert_blocked(self.inspect(archive=parent / self.archive.name, wanted=wanted))

    def test_archive_mutation_during_member_reads_is_rejected(self):
        self.write_zip()
        original = zipfile.ZipFile.open
        changed = False
        def opening(archive, *args, **kwargs):
            nonlocal changed
            result = original(archive, *args, **kwargs)
            if not changed:
                changed = True
                with self.archive.open("ab") as output:
                    output.write(b"mutation after archive preflight")
            return result
        with mock.patch.object(zipfile.ZipFile, "open", new=opening):
            self.assert_blocked(self.inspect(retained=True))
        self.assertTrue(changed)

    def test_same_byte_archive_replacement_during_read_does_not_reuse_an_old_inode(self):
        self.write_zip()
        original = zipfile.ZipFile.open
        replaced = False
        def opening(archive, *args, **kwargs):
            nonlocal replaced
            result = original(archive, *args, **kwargs)
            if not replaced:
                replaced = True
                raw = self.archive.read_bytes()
                self.archive.rename(self.root / "held-old-archive.zip")
                self.archive.write_bytes(raw)
            return result
        with mock.patch.object(zipfile.ZipFile, "open", new=opening):
            self.assert_blocked(self.inspect(retained=True))
        self.assertTrue(replaced)

    def test_misc_dynamic_and_ab_lists_must_agree_with_exact_role_sets(self):
        cases = [
            ("META/misc_info.txt", self.members["META/misc_info.txt"].replace(b"avb_enable=true", b"avb_enable=false")),
            ("META/dynamic_partitions_info.txt", self.members["META/dynamic_partitions_info.txt"].replace(b"use_dynamic_partitions=true", b"use_dynamic_partitions=false")),
            ("META/misc_info.txt", self.members["META/misc_info.txt"].replace(b"mi_ext ", b"")),
            ("META/misc_info.txt", self.members["META/misc_info.txt"].replace(b"dynamic_partition_list=", b"dynamic_partition_list=unknown ")),
            ("META/dynamic_partitions_info.txt", self.members["META/dynamic_partitions_info.txt"] + b"dynamic_partition_list=system\n"),
            ("META/misc_info.txt", self.members["META/misc_info.txt"] + b"avb_enable=true\n"),
            ("META/ab_partitions.txt", self.members["META/ab_partitions.txt"] + b"boot\n"),
            ("META/ab_partitions.txt", self.members["META/ab_partitions.txt"].replace(b"boot\n", b"countrycode\n", 1)),
            ("META/ab_partitions.txt", self.members["META/ab_partitions.txt"].replace(b"\n", b" ")),
        ]
        for name, raw in cases:
            with self.subTest(member=name, payload=raw):
                members = dict(self.members)
                members[name] = raw
                self.write_zip(members=members)
                self.assert_blocked(self.inspect(retained=True))

    def test_vbmeta_digest_is_required_lowercase_hex_without_extra_records(self):
        for raw in (b"", b"F" * 64 + b"\n", b"a" * 63 + b"\n", b"g" * 64 + b"\n",
                    b"a" * 64 + b"\n" + b"b" * 64 + b"\n"):
            with self.subTest(payload=raw):
                members = dict(self.members)
                members["META/vbmeta_digest.txt"] = raw
                self.write_zip(members=members)
                self.assert_blocked(self.inspect(retained=True))

    def test_retained_manifest_arguments_must_be_paired_and_digest_bound(self):
        wanted = self.write_zip()
        for kwargs in ({"retained_input_manifest": self.retained},
                       {"expected_retained_manifest_sha256": "a" * 64},
                       {"retained_input_manifest": self.retained,
                        "expected_retained_manifest_sha256": "0" * 64}):
            with self.subTest(kwargs=kwargs):
                self.assert_blocked(inventory.inspect_target_files(self.archive, wanted, **kwargs))

    def test_retained_manifest_rejects_extra_missing_conflicting_roles_or_provenance(self):
        self.write_zip()
        original = deepcopy(self.retained_value)
        changes = (
            lambda value: value["images"].pop("pvmfw"),
            lambda value: value["images"].update(boot=deepcopy(value["images"]["countrycode"])),
            lambda value: value["images"]["countrycode"].update(sha256="0" * 64),
            lambda value: value["source_records"].clear(),
            lambda value: value["source_records"].append(deepcopy(value["source_records"][0])),
            lambda value: value["source_records"][0].update(sha256="0" * 64),
        )
        for index, mutate in enumerate(changes):
            with self.subTest(change=index):
                self.retained_value = deepcopy(original)
                mutate(self.retained_value)
                self.save_retained()
                self.assert_blocked(self.inspect(retained=True))

    def test_retained_raw_and_factory_record_bodies_must_match_exact_hashes(self):
        self.write_zip()
        for path in (self.root / "countrycode.raw", self.root / "pvmfw.raw", self.factory_record):
            with self.subTest(path=path.name):
                before = path.read_bytes()
                path.write_bytes(before[:-1] + bytes([before[-1] ^ 1]))
                self.assert_blocked(self.inspect(retained=True))
                path.write_bytes(before)

    def test_retained_raw_manifest_and_provenance_symlinks_or_hardlinks_are_rejected(self):
        self.write_zip()
        for path in (self.root / "countrycode.raw", self.retained, self.factory_record):
            original = path.read_bytes()
            for link in ("symbolic", "hard"):
                with self.subTest(path=path.name, link=link):
                    held = self.root / (path.name + ".held")
                    path.rename(held)
                    if link == "symbolic":
                        path.symlink_to(held)
                    else:
                        os.link(held, path)
                    self.assert_blocked(self.inspect(retained=True))
                    path.unlink()
                    held.rename(path)
                    self.assertEqual(original, path.read_bytes())

    def test_cli_writes_fresh_report_and_returns_zero_only_for_complete_inventory(self):
        wanted = self.write_zip()
        for retained in (False, True):
            with self.subTest(retained=retained):
                destination = self.root / ("complete.json" if retained else "blocked.json")
                args = ["inspect", "--target-files", str(self.archive), "--expected-sha256", wanted["sha256"],
                        "--expected-size-bytes", str(wanted["size_bytes"]), "--output", str(destination)]
                if retained:
                    args += ["--retained-input-manifest", str(self.retained),
                             "--expected-retained-manifest-sha256", identity(self.retained.read_bytes())["sha256"]]
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    code = inventory.main(args)
                self.assertEqual(0 if retained else 2, code)
                report = json.loads(destination.read_bytes())
                self.assertEqual("complete" if retained else "blocked", report["status"])
                self.assert_scope_false(report)
                before = destination.read_bytes()
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(2, inventory.main(args))
                self.assertEqual(before, destination.read_bytes())

    def test_real_contract_loads_without_a_custom_profile_or_private_input(self):
        # Exercise the production public closure, separately from tiny fixtures.
        with mock.patch.object(inventory.signing, "load_contract", REAL_LOAD_CONTRACT), mock.patch.object(
                inventory.signing, "_local", side_effect=AssertionError("key config forbidden")):
            contract, digest, profile, _ = inventory.signing.load_contract()
            self.assertEqual("nezha-host-avb-signing-v1", contract["contract_id"])
            self.assertEqual(104857600, profile["working76"]["image"]["size_bytes"])
            self.write_zip()
            report = self.inspect()
            self.assert_blocked(report)  # Inert recovery cannot satisfy real working76.
            self.assertEqual(digest, report["contracts"]["signing"]["sha256"])

    def test_zip64_archive_and_local_extra_fields_keep_full_inventory(self):
        # Lowering the stdlib writer threshold produces real ZIP64 records in a
        # small inert archive; no large or sparse image fixture is necessary.
        with mock.patch.object(zipfile, "ZIP64_LIMIT", 1):
            self.write_zip(compression=zipfile.ZIP_DEFLATED)
        self.assertIn(b"PK\x06\x06", self.archive.read_bytes())
        result = self.inspect(retained=True)
        self.assertEqual("complete", result["status"], result["errors"])
        self.assert_scope_false(result)

    def test_directory_byte_count_and_actual_count_are_bounded_before_zipfile(self):
        self.write_zip()
        original = self.archive.read_bytes()
        for change in ("size", "declared-count", "actual-count"):
            with self.subTest(change=change):
                raw = bytearray(original)
                end = raw.rfind(b"PK\x05\x06")
                if change == "size":
                    struct.pack_into("<I", raw, end + 12, inventory.MAX_CENTRAL_DIRECTORY + 1)
                elif change == "declared-count":
                    struct.pack_into("<HH", raw, end + 8, 0, 0)
                else:
                    struct.pack_into("<HH", raw, end + 8, 1, 1)
                self.archive.write_bytes(raw)
                with mock.patch.object(inventory.zipfile, "ZipFile", side_effect=AssertionError("index constructed early")):
                    self.assert_blocked(self.inspect())
        self.archive.write_bytes(original)
        with mock.patch.object(inventory, "MAX_MEMBERS", 1), mock.patch.object(
                inventory.zipfile, "ZipFile", side_effect=AssertionError("index constructed early")):
            self.assert_blocked(self.inspect())

    def test_wrong_zip_magic_is_rejected_before_payload_hashing(self):
        self.archive.write_bytes(b"NOT A ZIP: inert unrelated payload that must not be scanned")
        with mock.patch.object(inventory, "_stream_identity", side_effect=AssertionError("payload scanned")):
            self.assert_blocked(self.inspect())


class SelectedZipStreamTests(unittest.TestCase):
    """Independent framing/decoder regressions found during bounded review."""

    @staticmethod
    def fixture(payload, compression=zipfile.ZIP_DEFLATED, *, descriptor=False, zip64=False):
        class Unseekable(io.BytesIO):
            def seek(self, *args):
                raise OSError("synthetic streaming writer")
        output = Unseekable() if descriptor else io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=compression) as archive:
            entry = zipfile.ZipInfo("IMAGES/boot.img")
            entry.compress_type = compression
            with archive.open(entry, "w", force_zip64=zip64) as stream:
                stream.write(payload)
        raw = bytearray(output.getvalue())
        header = struct.unpack_from("<4s5H3I2H", raw)
        start = 30 + header[-2] + header[-1]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            central = archive.start_dir
        return raw, start, central

    @staticmethod
    def replace_compressed(raw, start, central, compressed):
        result = bytearray(raw[:start] + compressed + raw[central:])
        new_central = start + len(compressed)
        struct.pack_into("<I", result, 18, len(compressed))
        struct.pack_into("<I", result, new_central + 20, len(compressed))
        end = result.index(b"PK\x05\x06", new_central)
        struct.pack_into("<I", result, end + 16, new_central)
        return result

    @staticmethod
    def selected(raw, maximum=16384):
        stream = io.BytesIO(raw)
        bounds = inventory._zip_bounds(stream, len(raw))
        with zipfile.ZipFile(stream) as archive:
            members = inventory._members(archive, bounds, {"boot"})
            return inventory._member_identity(archive, members["IMAGES/boot.img"], maximum)

    def test_valid_stored_deflated_zip64_and_streaming_descriptors(self):
        payload = b"synthetic selected bytes" * 80
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            for descriptor in (False, True):
                for zip64 in (False, True):
                    with self.subTest(compression=compression, descriptor=descriptor, zip64=zip64):
                        raw, _, _ = self.fixture(payload, compression, descriptor=descriptor, zip64=zip64)
                        row, _ = self.selected(raw)
                        self.assertEqual(identity(payload), {key: row[key] for key in ("sha256", "size_bytes")})

    def test_truncated_deflate_with_complete_plaintext_is_rejected(self):
        payload = b"A" * 4096
        raw, start, central = self.fixture(payload)
        compressed = bytes(raw[start:central])[:-1]
        check = zlib.decompressobj(-15)
        self.assertEqual(check.decompress(compressed), payload)
        self.assertFalse(check.eof)
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            self.selected(self.replace_compressed(raw, start, central, compressed))

    def test_valid_deflate_drains_output_at_chunk_boundaries(self):
        for length in (inventory.avb.CHUNK - 1, inventory.avb.CHUNK, inventory.avb.CHUNK + 1,
                       2 * inventory.avb.CHUNK + 1):
            for pattern in (b"A", b"repeated fixture data "):
                with self.subTest(length=length, pattern=pattern):
                    payload = (pattern * (length // len(pattern) + 1))[:length]
                    raw, _, _ = self.fixture(payload)
                    row, _ = self.selected(raw, maximum=length)
                    self.assertEqual(identity(payload), {key: row[key] for key in ("sha256", "size_bytes")})

    def test_excess_deflate_output_hidden_by_declared_size_is_rejected(self):
        payload = b"A" * 4096
        raw, _, central = self.fixture(payload + b"B")
        for offset in (22, central + 24):
            struct.pack_into("<I", raw, offset, len(payload))
        for offset in (14, central + 16):
            struct.pack_into("<I", raw, offset, zlib.crc32(payload))
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            self.selected(raw)

    def test_trailing_compressed_payload_is_rejected(self):
        raw, start, central = self.fixture(b"synthetic selected bytes" * 80)
        broken = self.replace_compressed(raw, start, central, bytes(raw[start:central]) + b"trailing junk")
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            self.selected(broken)

    def test_ordinary_local_header_contradictions_are_rejected(self):
        for field, offset, value in (("crc", 14, 0), ("compressed_size", 18, 123), ("size", 22, 123)):
            raw, _, _ = self.fixture(b"synthetic stored bytes", zipfile.ZIP_STORED)
            struct.pack_into("<I", raw, offset, value)
            with self.subTest(field=field), self.assertRaises((ValueError, zipfile.BadZipFile)):
                self.selected(raw)

    def test_zip64_and_streaming_descriptor_contradictions_are_rejected(self):
        for zip64 in (False, True):
            raw, _, central = self.fixture(b"synthetic stored bytes", descriptor=True, zip64=zip64)
            descriptor = raw.index(b"PK\x07\x08")
            struct.pack_into("<I", raw, descriptor + 4, 0)
            with self.subTest(zip64=zip64), self.assertRaises((ValueError, zipfile.BadZipFile)):
                self.selected(raw)
        raw, _, _ = self.fixture(b"synthetic stored bytes", zip64=True)
        name_size = struct.unpack_from("<H", raw, 26)[0]
        struct.pack_into("<Q", raw, 30 + name_size + 4, 999)
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            self.selected(raw)


if __name__ == "__main__":
    unittest.main()
