"""Inert byte fixtures exercise packaging safety, never ROM or phone readiness."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from scripts import experimental_flash_bundle as bundle


def hashed(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


class ExperimentalFlashBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.allowed = self.root / "artifacts/flash/nezha"
        self.allowed.mkdir(parents=True)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(bundle, "BUNDLE_ROOT", self.allowed).start()
        self.output = self.allowed / "candidate"
        self.super_path = self.sources / "super.img"
        self.super_path.write_bytes(b"inert sparse Super, not usable on hardware")
        self.plan = {
            "schema_version": 1, "device": dict(bundle.DEVICE), "platform": dict(bundle.PLATFORM),
            **{key: False for key in bundle.FALSE_FLAGS},
            "fresh_experimental_flash_authorization": None, "source_archive_is_flashable_installer": False,
            "device_preflight": {**{key: None for key in bundle.PREFLIGHT_FIELDS},
                                 "device_preflight_admitted": False},
            "delivery_modes": {"current_super_factory_style": {
                **bundle.LAYOUT, "warning": bundle.WARNING, "payloads": list(bundle.PAYLOADS)}},
            "avb_contract": {"algorithm": "SHA256_RSA4096", "flags": 0,
                "disable_verification_or_verity_allowed": False, "relock_allowed": False,
                "rollback_bypass_allowed": False, "public_key_sha256": "b" * 64},
            "retained_firmware_avb_requirements": {"countrycode": {}, "pvmfw": {}},
            "super": {**hashed(self.super_path.read_bytes()), "expanded_size_bytes": 15300820992},
            "artifacts": [], "evidence": {},
        }
        for role in (*bundle.PHYSICAL, *bundle.LOGICAL, *bundle.REFERENCES):
            raw = ("inert image fixture for " + role).encode()
            path = self.sources / (role + ".img")
            path.write_bytes(raw)
            delivery_role = ("required-physical-slot-image" if role in bundle.PHYSICAL else
                "verification-reference-only-retain-existing-device-firmware" if role in bundle.REFERENCES else
                "embedded-in-current-super-or-separate-logical-image-for-a-different-reviewed-route")
            target = (role + "_a-for-current-super-route" if role in bundle.PHYSICAL else
                      role + "_<selected-slot>" if role in bundle.REFERENCES else role + "_a")
            self.plan["artifacts"].append({"role": role, "path": role + ".img", "host_path": str(path),
                "delivery_role": delivery_role, "target": target, **hashed(raw)})
        self.plan_path = self.root / "plan.json"

    def write_plan(self):
        raw = bundle.json_bytes(self.plan)
        self.plan_path.write_bytes(raw)
        return hashed(raw)["sha256"]

    def assemble(self):
        return bundle.assemble(self.plan_path, self.write_plan(), self.super_path, self.output)

    def row(self, role):
        return next(row for row in self.plan["artifacts"] if row["role"] == role)

    def mutate_manifest(self, change):
        path = self.output / "manifest.json"
        value = json.loads(path.read_bytes())
        change(value)
        raw = bundle.json_bytes(value)
        path.write_bytes(raw)
        return hashed(raw)["sha256"]

    def test_round_trip_is_portable_and_contains_exactly_eight_payloads(self):
        result = self.assemble()
        self.assertFalse(result["flash_ready"])
        self.assertEqual(8, result["payload_count"])
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertNotIn(str(self.root), json.dumps(manifest))
        self.assertEqual(set(bundle.PAYLOADS), {r["role"] for r in manifest["images"]})
        self.assertFalse((self.output / "countrycode.img").exists())
        self.assertFalse((self.output / "pvmfw.img").exists())
        self.assertEqual(list(bundle.REFERENCES), sorted(manifest["retained_firmware_references_not_payloads"]))
        relocated = self.root / "received"
        shutil.copytree(self.output, relocated)
        checked = bundle.verify(relocated, result["manifest_sha256"])
        self.assertFalse(checked["flash_ready"])
        self.assertEqual(result["status"], checked["status"])

    def test_does_not_read_reference_or_logical_payloads(self):
        for role in (*bundle.REFERENCES, *bundle.LOGICAL):
            (self.sources / (role + ".img")).unlink()
        self.assemble()

    def test_independent_plan_digest_required(self):
        digest = self.write_plan()
        self.plan_path.write_bytes(self.plan_path.read_bytes() + b" ")
        with self.assertRaisesRegex(bundle.BundleError, "JSON digest differs"):
            bundle.assemble(self.plan_path, digest, self.super_path, self.output)
        self.assertFalse(self.output.exists())

    def test_duplicate_plan_json_keys_rejected(self):
        raw = b'{"schema_version":1,"schema_version":1}'
        self.plan_path.write_bytes(raw)
        with self.assertRaisesRegex(bundle.BundleError, "duplicate JSON key"):
            bundle.assemble(self.plan_path, hashed(raw)["sha256"], self.super_path, self.output)

    def test_wrong_device_platform_and_page_size_rejected(self):
        for section, key, value in (("device", "codename", "other"), ("device", "board", "other"),
            ("device", "variant", "unverified"), ("platform", "branch", "newer"),
            ("platform", "release", "bp5a"), ("platform", "page_size_bytes", 16384),
            ("platform", "normal_android_selinux", "permissive")):
            with self.subTest(section=section, key=key):
                plan = deepcopy(self.plan)
                plan[section][key] = value
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)

    def test_readiness_authorization_and_preflight_promotions_rejected(self):
        for key in (*bundle.FALSE_FLAGS, "source_archive_is_flashable_installer",
                    "fresh_experimental_flash_authorization"):
            with self.subTest(key=key):
                plan = deepcopy(self.plan)
                plan[key] = True
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)
        for key in self.plan["device_preflight"]:
            with self.subTest(preflight=key):
                plan = deepcopy(self.plan)
                plan["device_preflight"][key] = True
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)

    def test_unsafe_route_changes_rejected(self):
        for key, value in (("candidate_boot_slot", "b"), ("empty_logical_slot", "a"),
            ("preserves_stock_inactive_logical_slot", True), ("automatic_reboot", True),
            ("automatic_userdata_or_metadata_format", True), ("warning", "safe fallback"),
            ("reviewed_write_order", ["super"])):
            with self.subTest(key=key):
                plan = deepcopy(self.plan)
                plan["delivery_modes"]["current_super_factory_style"][key] = value
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)

    def test_avb_bypasses_rejected(self):
        for key, value in (("flags", 2), ("disable_verification_or_verity_allowed", True),
                           ("rollback_bypass_allowed", True), ("relock_allowed", True)):
            with self.subTest(key=key):
                plan = deepcopy(self.plan)
                plan["avb_contract"][key] = value
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)

    def test_reference_cannot_be_promoted_to_write_payload(self):
        for role in bundle.REFERENCES:
            with self.subTest(role=role):
                saved = self.row(role)["delivery_role"]
                self.row(role)["delivery_role"] = "required-physical-slot-image"
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(self.plan)
                self.row(role)["delivery_role"] = saved

    def test_unknown_duplicate_and_missing_roles_rejected(self):
        for mode in ("extra", "duplicate", "missing"):
            with self.subTest(mode=mode):
                plan = deepcopy(self.plan)
                if mode == "extra":
                    plan["artifacts"][0]["role"] = "bootloader"
                elif mode == "duplicate":
                    plan["artifacts"][0] = dict(plan["artifacts"][1])
                else:
                    plan["artifacts"].pop()
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)

    def test_artifact_path_traversal_and_wrong_target_rejected(self):
        for field, value in (("path", "../boot.img"), ("path", "/boot.img"), ("target", "boot_b")):
            with self.subTest(field=field, value=value):
                plan = deepcopy(self.plan)
                plan["artifacts"][0][field] = value
                with self.assertRaises(bundle.BundleError):
                    bundle.validate_plan(plan)

    def test_noncanonical_source_path_rejected(self):
        self.row("boot")["host_path"] = str(self.sources) + "/../sources/boot.img"
        with self.assertRaisesRegex(bundle.BundleError, "without traversal"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_source_symlink_hardlink_and_directory_rejected(self):
        for kind in ("symlink", "hardlink", "directory"):
            with self.subTest(kind=kind):
                path = self.sources / "unsafe.img"
                if kind == "symlink":
                    path.symlink_to(self.sources / "boot.img")
                elif kind == "hardlink":
                    os.link(self.sources / "boot.img", path)
                else:
                    path.mkdir()
                self.row("boot")["host_path"] = str(path)
                with self.assertRaises(bundle.BundleError):
                    self.assemble()
                self.assertFalse(self.output.exists())
                path.rmdir() if kind == "directory" else path.unlink()

    def test_symlink_source_ancestor_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.sources, target_is_directory=True)
        self.row("boot")["host_path"] = str(alias / "boot.img")
        with self.assertRaises(OSError):
            self.assemble()

    def test_output_outside_private_bundle_root_rejected(self):
        self.output = self.root / "unreviewed-destination"
        with self.assertRaisesRegex(bundle.BundleError, "artifacts/flash/nezha"):
            self.assemble()

    def test_existing_output_and_symlink_are_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "important"
        marker.write_bytes(b"retain")
        with self.assertRaises(FileExistsError):
            self.assemble()
        self.assertEqual(b"retain", marker.read_bytes())
        alias = self.allowed / "alias"
        alias.symlink_to(self.output, target_is_directory=True)
        self.output = alias
        with self.assertRaises(FileExistsError):
            self.assemble()
        self.assertEqual(b"retain", marker.read_bytes())

    def test_source_hash_mismatch_leaves_failure_evidence_and_no_manifest(self):
        original = (self.sources / "dtbo.img").read_bytes()
        (self.sources / "dtbo.img").write_bytes(b"X" * len(original))
        with self.assertRaisesRegex(bundle.BundleError, "source image digest differs"):
            self.assemble()
        self.assertFalse((self.output / "manifest.json").exists())
        failure = json.loads((self.output / "INCOMPLETE.json").read_text())
        self.assertEqual(["boot"], failure["completed_roles"])
        self.assertTrue((self.output / "dtbo.img").exists())
        self.assertFalse(failure["flash_ready"])

    def test_short_source_and_wrong_super_hash_rejected(self):
        for role in ("boot", "super"):
            with self.subTest(role=role):
                self.output = self.allowed / ("bad-" + role)
                if role == "boot":
                    self.row(role)["size_bytes"] += 1
                else:
                    self.row("boot")["size_bytes"] -= 1
                    self.plan["super"]["sha256"] = "c" * 64
                with self.assertRaises(bundle.BundleError):
                    self.assemble()
                self.assertTrue((self.output / "INCOMPLETE.json").exists())
                self.assertFalse((self.output / "manifest.json").exists())

    def test_copy_failure_preserves_partial_payload_and_original(self):
        source = (self.sources / "boot.img").read_bytes()
        def interrupted(stream, output=None, limit=None):
            output.write(stream.read(4))
            raise OSError("simulated full disk")
        with mock.patch.object(bundle, "hash_stream", side_effect=interrupted):
            with self.assertRaisesRegex(OSError, "simulated full disk"):
                self.assemble()
        self.assertEqual(source, (self.sources / "boot.img").read_bytes())
        self.assertEqual(source[:4], (self.output / "boot.img").read_bytes())
        self.assertTrue((self.output / "INCOMPLETE.json").exists())
        self.assertFalse((self.output / "manifest.json").exists())

    def test_source_changed_during_copy_rejected_even_if_read_bytes_match(self):
        original_hash = bundle.hash_stream
        called = False
        def mutate_source(stream, output=None, limit=1 << 40):
            nonlocal called
            result = original_hash(stream, output, limit)
            if output is not None and not called:
                called = True
                (self.sources / "boot.img").write_bytes(b"changed")
            return result
        with mock.patch.object(bundle, "hash_stream", side_effect=mutate_source):
            with self.assertRaisesRegex(bundle.BundleError, "input changed"):
                self.assemble()
        self.assertFalse((self.output / "manifest.json").exists())

    def test_same_singly_linked_source_for_two_roles_rejected(self):
        self.row("dtbo").update(host_path=self.row("boot")["host_path"],
                                **bundle.identity(self.row("boot")))
        with self.assertRaisesRegex(bundle.BundleError, "source roles alias"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_earlier_copy_changed_during_super_copy_blocks_manifest(self):
        original_hash = bundle.hash_stream
        def mutate_earlier(stream, output=None, limit=1 << 40):
            actual = original_hash(stream, output, limit)
            if output is not None and actual == bundle.identity(self.plan["super"]):
                (self.output / "boot.img").write_bytes(b"late tampering")
            return actual
        with mock.patch.object(bundle, "hash_stream", side_effect=mutate_earlier):
            with self.assertRaisesRegex(bundle.BundleError, "input changed"):
                self.assemble()
        self.assertFalse((self.output / "manifest.json").exists())

    def test_late_payload_and_manifest_tampering_blocks_verification(self):
        result = self.assemble()
        original_hash = bundle.hash_stream
        for name in ("boot.img", "manifest.json"):
            with self.subTest(name=name):
                target = self.root / ("late-" + name)
                shutil.copytree(self.output, target)
                def mutate_earlier(stream, output=None, limit=1 << 40):
                    actual = original_hash(stream, output, limit)
                    if actual == bundle.identity(self.plan["super"]):
                        (target / name).write_bytes(b"late tampering")
                    return actual
                with mock.patch.object(bundle, "hash_stream", side_effect=mutate_earlier):
                    with self.assertRaisesRegex(bundle.BundleError, "input changed"):
                        bundle.verify(target, result["manifest_sha256"])

    def test_unexpected_file_inserted_during_copy_blocks_manifest(self):
        original_hash = bundle.hash_stream
        def insert_extra(stream, output=None, limit=1 << 40):
            actual = original_hash(stream, output, limit)
            if output is not None and actual == bundle.identity(self.plan["super"]):
                (self.output / "countrycode.img").write_bytes(b"unexpected firmware")
            return actual
        with mock.patch.object(bundle, "hash_stream", side_effect=insert_extra):
            with self.assertRaisesRegex(bundle.BundleError, "unexpected files"):
                self.assemble()
        self.assertFalse((self.output / "manifest.json").exists())
        self.assertTrue((self.output / "countrycode.img").exists())

    def test_verifier_rejects_wrong_digest_and_changed_payload(self):
        result = self.assemble()
        with self.assertRaisesRegex(bundle.BundleError, "JSON digest differs"):
            bundle.verify(self.output, "f" * 64)
        (self.output / "boot.img").write_bytes(b"tampered")
        with self.assertRaisesRegex(bundle.BundleError, "bundle image differs"):
            bundle.verify(self.output, result["manifest_sha256"])

    def test_verifier_rejects_missing_extra_support_and_aliased_files(self):
        result = self.assemble()
        for mode in ("missing", "extra", "readme", "sums", "symlink", "hardlink"):
            with self.subTest(mode=mode):
                target = self.root / ("verify-" + mode)
                shutil.copytree(self.output, target)
                if mode == "missing":
                    (target / "boot.img").unlink()
                elif mode == "extra":
                    (target / "countrycode.img").write_bytes(b"unexpected firmware")
                elif mode in ("readme", "sums"):
                    (target / ("README.md" if mode == "readme" else "SHA256SUMS")).write_text("changed")
                elif mode == "symlink":
                    (target / "boot.img").unlink()
                    (target / "boot.img").symlink_to(self.sources / "boot.img")
                else:
                    (target / "boot.img").unlink()
                    os.link(self.sources / "boot.img", target / "boot.img")
                with self.assertRaises(bundle.BundleError):
                    bundle.verify(target, result["manifest_sha256"])

    def test_verifier_rejects_resealed_path_role_and_readiness_lies(self):
        result = self.assemble()
        original = (self.output / "manifest.json").read_bytes()
        for change in (lambda m: m.update(flash_ready=True),
            lambda m: m["images"][0].update(path="../sources/boot.img"),
            lambda m: m["images"][0].update(role="countrycode"),
            lambda m: m.update(complete_rom_ready=True),
            lambda m: m["avb_contract_from_plan_not_reverified"].update(flags=2),
            lambda m: m["device_preflight"].pop("current_slot"),
            lambda m: m["delivery"].update(preserves_stock_inactive_logical_slot=True)):
            with self.subTest(change=change):
                (self.output / "manifest.json").write_bytes(original)
                digest = self.mutate_manifest(change)
                with self.assertRaises(bundle.BundleError):
                    bundle.verify(self.output, digest)
        (self.output / "manifest.json").write_bytes(original)
        self.assertEqual(8, bundle.verify(self.output, result["manifest_sha256"])["payload_count"])

    def test_cli_reports_failure_without_traceback(self):
        self.write_plan()
        with redirect_stderr(io.StringIO()) as stderr, redirect_stdout(io.StringIO()) as stdout:
            code = bundle.main(["assemble", "--plan", str(self.plan_path), "--expected-plan-sha256", "a" * 64,
                                "--super", str(self.super_path), "--output", str(self.output)])
        self.assertEqual(1, code)
        self.assertIn("JSON digest differs", stderr.getvalue())
        self.assertEqual("", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
