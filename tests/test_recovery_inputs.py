"""Offline staging tests: tiny synthetic images and mocked AVB verification.

These tests do not execute AVB tools or validate a real recovery/ROM. The public
working76 identity is replaced only inside each isolated test fixture.
"""

import copy
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from scripts import recovery_inputs as recovery


class RecoveryInputsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.checkout = self.root / "source"
        self.bundle = self.checkout / recovery.BUNDLE_PATH
        self.image = self.root / "synthetic-recovery.img"
        self.image_bytes = b"INERT recovery fixture; not a bootable image\n"
        self.image.write_bytes(self.image_bytes)
        self.expected = recovery._identity(self.image_bytes)
        self.public_key = self.root / "synthetic-public.pem"
        self.public_key_bytes = b"-----BEGIN PUBLIC KEY-----\nU1lOVEhFVElDIG9ubHk=\n-----END PUBLIC KEY-----\n"
        self.public_key.write_bytes(self.public_key_bytes)
        self.public_key.chmod(0o644)
        self.enterContext(mock.patch.object(recovery, "ROOT", self.root))
        self.enterContext(mock.patch.object(recovery, "EXPECTED_IMAGE", self.expected))
        self.enterContext(mock.patch.object(recovery, "EXPECTED_PUBLIC_KEY_SHA256",
                                            recovery._identity(self.public_key_bytes)["sha256"]))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("no native processes")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("no shell execution")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("no network")))
        self.profile = {"schema_version": 1, "profile_id": recovery.PROFILE_ID,
                        "output": {"image": self.expected.copy()}}
        core, common, patch = b"reviewed patched core fixture\n", b"pinned releasetools fixture\n", b"fixture patch\n"
        self.source = {
            "schema_version": 1,
            "project": {"path": "build/make", "commit": recovery.BUILD_COMMIT},
            "patch": {"path": recovery.PATCH_PATH, **recovery._identity(patch)},
            "source_files": [{"path": recovery.CORE_PATH,
                              "before": recovery._identity(b"old core fixture\n"), "after": recovery._identity(core)}],
            "semantic_files": [{"path": recovery.COMMON_PATH, **recovery._identity(common)}],
        }
        for path, data in ((self.root / recovery.PATCH_PATH, patch),
                           (self.checkout / recovery.CORE_PATH, core),
                           (self.checkout / recovery.COMMON_PATH, common)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.save_profile()
        self.save_source()
        self.report = {
            "schema_version": 1, "status": "verified", "profile_id": recovery.PROFILE_ID,
            "profile_sha256": recovery._identity(recovery._canonical(self.profile))["sha256"],
            "image": self.expected.copy(), "header": {"header_version": 4, "kernel_size_bytes": 0},
            "avb": {"algorithm": "SHA256_RSA4096", "partition_name": "recovery", "rollback_index": 1,
                    "rollback_index_location": 1, "flags": 0, "signature_verified": True,
                    "descriptor_verified": True, "oem_trust_established": False},
            "public_key": {"input_sha256": recovery.EXPECTED_PUBLIC_KEY_SHA256,
                           "avb_sha256": recovery.EXPECTED_KEY, "avb_size_bytes": 1032},
            "tools": {name: recovery._identity(name.encode()) for name in ("avbtool", "openssl")},
            "source_built": False, "device_operations": [],
        }
        self.native = self.enterContext(mock.patch.object(recovery, "_native_verify",
                                                         side_effect=lambda *a, **k: copy.deepcopy(self.report)))
        self.options = {"source_tree": self.checkout,
                        "public_key": self.public_key,
                        **{name: self.root / ("not-opened-" + name) for name in ("avbtool", "openssl")}}

    def save_profile(self):
        path = self.root / recovery.PROFILE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(recovery._canonical(self.profile))

    def save_source(self):
        (self.root / recovery.SOURCE_CONTRACT_PATH).write_bytes(recovery._canonical(self.source))

    def stage(self, bundle=None):
        return recovery.stage_inputs(self.image, bundle or self.bundle, **self.options)

    def verify(self):
        return recovery.verify_bundle(self.bundle, **self.options)

    def assert_refused(self, call):
        with self.assertRaises((ValueError, OSError)):
            call()

    def test_stage_exact_private_bundle_and_verify_again(self):
        before = {path: path.read_bytes() for path in (self.image, self.public_key, self.checkout / recovery.CORE_PATH,
                                                       self.checkout / recovery.COMMON_PATH)}
        staged = self.stage()
        self.assertEqual(staged["status"], "staged")
        self.assertEqual(staged["schema_version"], 2)
        self.assertTrue(staged["readback_verified"])
        self.assertEqual(set(path.name for path in self.bundle.iterdir()), recovery.BUNDLE_FILES)
        self.assertEqual(stat.S_IMODE(self.bundle.stat().st_mode), 0o700)
        self.assertTrue((self.checkout / "vendor/xiaomi").is_dir())
        for path in self.bundle.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual((self.bundle / "recovery.img").read_bytes(), self.image_bytes)
        self.assertEqual((self.bundle / recovery.PUBLIC_KEY_MEMBER).read_bytes(), self.public_key_bytes)
        receipt = json.loads((self.bundle / "receipt.json").read_bytes())
        self.assertEqual(receipt["image"], self.expected)
        self.assertEqual(receipt["schema_version"], 2)
        self.assertEqual(receipt["public_key"], {"path": recovery.PUBLIC_KEY_MEMBER,
                                                **recovery._identity(self.public_key_bytes)})
        self.assertEqual(receipt["public_key"]["sha256"], receipt["verification"]["public_key"]["input_sha256"])
        self.assertEqual(receipt["verification"]["schema_version"], 1)
        self.assertFalse(receipt["build_source"]["whole_source_tree_verified"])
        self.assertTrue(receipt["build_source"]["selected_source_bytes_verified"])
        self.assertEqual(receipt["scope"], recovery.SCOPE)
        verified = self.verify()
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(staged["files"], verified["files"])
        self.assertEqual(self.native.call_count, 2)
        self.assertEqual(self.native.call_args.args, (self.bundle / "recovery.img",))
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        for name in ("avbtool", "openssl"):
            self.assertEqual(self.native.call_args.kwargs[name], self.options[name])
        self.assertEqual(self.native.call_args.kwargs["public_key"], self.bundle / recovery.PUBLIC_KEY_MEMBER)
        self.assertEqual(self.native.call_args_list[0].kwargs["public_key"], self.public_key)
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_plan_opens_no_image_or_native_tool_and_does_not_export_mutable_globals(self):
        original_read = recovery._read

        def public_only(path, **kwargs):
            self.assertIn(Path(path), {self.root / recovery.PROFILE_PATH, self.root / recovery.PATCH_PATH,
                                      self.root / recovery.SOURCE_CONTRACT_PATH})
            return original_read(path, **kwargs)

        with mock.patch.object(recovery, "_read", side_effect=public_only):
            result = recovery.plan()
        self.native.assert_not_called()
        self.assertFalse(result["image_verified"])
        self.assertFalse(result["source_patch_applied"])
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["public_key"]["path"], recovery.PUBLIC_KEY_MEMBER)
        self.assertEqual(result["public_key"]["sha256"], recovery.EXPECTED_PUBLIC_KEY_SHA256)
        self.assertFalse(result["public_key"]["private_key_included"])
        result["image"]["sha256"] = "0" * 64
        result["scope"]["flash_allowed"] = True
        result["scope"]["device_operations"].append("not permitted")
        self.assertEqual(recovery.EXPECTED_IMAGE, recovery._identity(self.image_bytes))
        self.assertFalse(recovery.SCOPE["flash_allowed"])
        self.assertEqual(recovery.SCOPE["device_operations"], [])
        staged = self.stage()
        staged["scope"]["ota_allowed"] = True
        self.assertFalse(self.verify()["scope"]["ota_allowed"])

    def test_wrong_image_hash_or_size_fails_before_native_or_output(self):
        for data in (b"wrong" + self.image_bytes[5:], self.image_bytes[:-1], self.image_bytes + b"x"):
            with self.subTest(size=len(data)):
                self.image.write_bytes(data)
                self.assert_refused(self.stage)
                self.assertFalse(self.bundle.exists())
        self.native.assert_not_called()

    def test_unpatched_or_changed_semantic_source_fails_before_native(self):
        for relative in (recovery.CORE_PATH, recovery.COMMON_PATH):
            path = self.checkout / relative
            original = path.read_bytes()
            with self.subTest(path=relative):
                path.write_bytes(b"unreviewed source bytes\n")
                self.assert_refused(self.stage)
                self.assertFalse(self.bundle.exists())
                path.write_bytes(original)
        self.native.assert_not_called()

    def test_source_contract_or_public_patch_tamper_fails(self):
        mutations = [lambda: self.source.update(schema_version=True),
                     lambda: self.source.update(project=None),
                     lambda: self.source.update(source_files=[None]),
                     lambda: self.source.update(semantic_files=[{"path": []}]),
                     lambda: self.source["project"].update(commit="0" * 40),
                     lambda: self.source["source_files"][0].update(path="../elsewhere"),
                     lambda: self.source.update(semantic_files=[])]
        original = copy.deepcopy(self.source)
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.source = copy.deepcopy(original)
                mutate()
                self.save_source()
                self.assert_refused(self.stage)
        self.source = original
        self.save_source()
        (self.root / recovery.PATCH_PATH).write_bytes(b"changed patch")
        self.assert_refused(self.stage)
        self.native.assert_not_called()

    def test_invalid_profile_is_a_controlled_refusal(self):
        for field, value in (("schema_version", True), ("output", None), ("profile_id", "stock")):
            with self.subTest(field=field):
                original = copy.deepcopy(self.profile)
                self.profile[field] = value
                self.save_profile()
                self.assert_refused(self.stage)
                self.profile = original
        self.native.assert_not_called()

    def test_native_report_rejects_wrong_image_security_and_provenance(self):
        cases = [(("status",), "failed"), (("schema_version",), True), (("profile_sha256",), "0" * 64),
                 (("image", "sha256"), "0" * 64), (("header", "header_version"), 3),
                 (("header", "kernel_size_bytes"), 64), (("header",), None), (("avb",), []),
                 (("avb", "algorithm"), "NONE"), (("avb", "partition_name"), "boot"),
                 (("avb", "flags"), 3), (("avb", "rollback_index"), 0),
                 (("avb", "rollback_index_location"), 0), (("avb", "rollback_index"), True),
                 (("avb", "signature_verified"), False), (("avb", "descriptor_verified"), 1),
                 (("avb", "oem_trust_established"), True), (("public_key",), None),
                 (("public_key", "avb_sha256"), "0" * 64), (("public_key", "input_sha256"), "0" * 64), (("tools",), {}),
                 (("device_operations",), ["flash"]), (("source_built",), True)]
        original = copy.deepcopy(self.report)
        for path, value in cases:
            with self.subTest(path=path, value=value):
                self.report = copy.deepcopy(original)
                item = self.report
                for name in path[:-1]:
                    item = item[name]
                item[path[-1]] = value
                self.assert_refused(self.stage)
                self.assertFalse(self.bundle.exists())

    def test_native_failure_does_not_publish_anything(self):
        self.native.side_effect = ValueError("synthetic AVB failure")
        self.assert_refused(self.stage)
        self.assertFalse(self.bundle.exists())

    def test_input_change_during_native_verification_is_rejected(self):
        def changed(*args, **kwargs):
            self.image.write_bytes(b"x" * len(self.image_bytes))
            return copy.deepcopy(self.report)
        self.native.side_effect = changed
        self.assert_refused(self.stage)
        self.assertFalse(self.bundle.exists())

    def test_missing_or_wrong_public_pem_is_rejected_before_native(self):
        self.public_key.unlink()
        self.assert_refused(self.stage)
        for data in (b"not a PEM", self.public_key_bytes + b"\n", b"x" * (recovery.MAX_PUBLIC_KEY_BYTES + 1),
                     b"-----BEGIN PRIVATE KEY-----\nfixture\n-----END PRIVATE KEY-----\n"):
            with self.subTest(data=data[:30]):
                self.public_key.write_bytes(data)
                self.assert_refused(self.stage)
                self.assertFalse(self.bundle.exists())
        self.native.assert_not_called()

    def test_private_key_is_rejected_even_with_a_matching_fixture_hash(self):
        private = b"-----BEGIN PRIVATE KEY-----\nfixture only\n-----END PRIVATE KEY-----\n"
        self.public_key.write_bytes(private)
        with mock.patch.object(recovery, "EXPECTED_PUBLIC_KEY_SHA256", recovery._identity(private)["sha256"]):
            self.assert_refused(self.stage)
        self.native.assert_not_called()
        self.assertFalse(self.bundle.exists())

    def test_public_key_change_during_native_verification_is_rejected(self):
        def changed(*args, **kwargs):
            self.public_key.write_bytes(self.public_key_bytes + b"changed")
            return copy.deepcopy(self.report)
        self.native.side_effect = changed
        self.assert_refused(self.stage)
        self.assertFalse(self.bundle.exists())

    def test_public_key_symlink_hardlink_fifo_or_symlink_parent_is_rejected(self):
        saved = self.root / "saved-public.pem"
        self.public_key.rename(saved)
        self.public_key.symlink_to(saved)
        self.assert_refused(self.stage)
        self.public_key.unlink()
        os.link(saved, self.public_key)
        self.assert_refused(self.stage)
        self.public_key.unlink()
        os.mkfifo(self.public_key)
        self.assert_refused(self.stage)
        self.public_key.unlink()
        directory = self.root / "public-directory"
        directory.mkdir()
        saved.rename(directory / "public.pem")
        alias = self.root / "public-alias"
        alias.symlink_to(directory, target_is_directory=True)
        self.options["public_key"] = alias / "public.pem"
        self.assert_refused(self.stage)
        self.native.assert_not_called()

    def test_old_three_file_bundle_and_mismatched_key_receipt_are_rejected(self):
        self.stage()
        key = self.bundle / recovery.PUBLIC_KEY_MEMBER
        key.unlink()
        with self.assertRaisesRegex(recovery.RecoveryInputsError, "schema2"):
            self.verify()
        key.write_bytes(self.public_key_bytes)
        key.chmod(0o600)
        receipt_path = self.bundle / "receipt.json"
        original = json.loads(receipt_path.read_bytes())
        profile, source, _ = recovery._contracts()
        for variant in ("schema", "hash", "size", "path"):
            changed = copy.deepcopy(original)
            if variant == "schema":
                changed["schema_version"] = 1
            else:
                field = {"hash": "sha256", "size": "size_bytes", "path": "path"}[variant]
                changed["public_key"][field] = {"hash": "0" * 64, "size": 1, "path": "testkey.pem"}[variant]
            data = recovery._canonical(changed)
            receipt_path.write_bytes(data)
            (self.bundle / "recovery-inputs.mk").write_bytes(recovery._make_include(data, profile, source))
            with self.subTest(variant=variant):
                self.assert_refused(self.verify)
        self.assertEqual(self.native.call_count, 1)

    def test_no_overwrite_or_arbitrary_bundle_path(self):
        self.assert_refused(lambda: self.stage(self.root / "somewhere"))
        self.stage()
        original = {path: path.read_bytes() for path in self.bundle.iterdir()}
        self.assert_refused(self.stage)
        self.assertEqual(original, {path: path.read_bytes() for path in original})
        self.assertEqual(self.native.call_count, 1)

    def test_non_directory_parent_is_rejected_without_replacing_it(self):
        parent = self.checkout / "vendor"
        parent.write_bytes(b"preexisting regular file")
        self.assert_refused(self.stage)
        self.assertEqual(parent.read_bytes(), b"preexisting regular file")

    def test_partial_creation_failure_is_retained_and_never_overwritten(self):
        with mock.patch.object(recovery.os, "fsync", side_effect=OSError("synthetic disk failure")):
            self.assert_refused(self.stage)
        self.assertTrue(self.bundle.is_dir())
        original = {path.name: path.read_bytes() for path in self.bundle.iterdir()}
        self.assert_refused(self.stage)
        self.assertEqual(original, {path.name: path.read_bytes() for path in self.bundle.iterdir()})
        self.assertEqual(self.native.call_count, 1)

    def test_input_symlink_hardlink_fifo_and_symlink_parent_are_rejected(self):
        real = self.root / "real-image"
        self.image.rename(real)
        self.image.symlink_to(real)
        self.assert_refused(self.stage)
        self.image.unlink()
        os.link(real, self.image)
        self.assert_refused(self.stage)
        self.image.unlink()
        os.mkfifo(self.image)
        self.assert_refused(self.stage)
        self.image.unlink()
        real.rename(self.image)
        alternate = self.root / "alternate-parent"
        alternate.mkdir()
        (self.checkout / "vendor").symlink_to(alternate, target_is_directory=True)
        self.assert_refused(self.stage)
        self.assertFalse((alternate / "xiaomi").exists())

    def test_image_receipt_include_or_privacy_tamper_is_rejected(self):
        self.stage()
        for name in sorted(recovery.BUNDLE_FILES):
            path = self.bundle / name
            original = path.read_bytes()
            for operation in ("bytes", "public-mode", "hardlink"):
                with self.subTest(file=name, operation=operation):
                    if operation == "bytes":
                        path.write_bytes(original[:-1] + b"x")
                    elif operation == "public-mode":
                        path.chmod(0o644)
                    else:
                        os.link(path, self.root / "extra-link")
                    self.assert_refused(self.verify)
                    path.write_bytes(original)
                    path.chmod(0o600)
                    if operation == "hardlink":
                        (self.root / "extra-link").unlink()
        self.bundle.chmod(0o755)
        self.assert_refused(self.verify)
        self.bundle.chmod(0o700)
        (self.bundle / "extra").write_bytes(b"not admitted")
        self.assert_refused(self.verify)
        self.assertEqual(self.native.call_count, 1)

    def test_receipt_cannot_promote_scope_even_if_include_is_recomputed(self):
        self.stage()
        path = self.bundle / "receipt.json"
        original = json.loads(path.read_bytes())
        profile, source, _ = recovery._contracts()
        for value in (True, 0):
            with self.subTest(value=value):
                changed = copy.deepcopy(original)
                changed["scope"]["flash_allowed"] = value
                encoded = recovery._canonical(changed)
                path.write_bytes(encoded)
                (self.bundle / "recovery-inputs.mk").write_bytes(recovery._make_include(encoded, profile, source))
                self.assert_refused(self.verify)

    def test_readback_rejects_concurrent_modes_membership_or_replacement(self):
        self.stage()
        original = recovery._read_at
        for change in ("file-mode", "directory-mode", "extra", "replacement"):
            with self.subTest(change=change):
                fired = False

                def changed(directory, name, limit):
                    nonlocal fired
                    result = original(directory, name, limit)
                    if not fired:
                        fired = True
                        if change == "file-mode":
                            (self.bundle / name).chmod(0o644)
                        elif change == "directory-mode":
                            self.bundle.chmod(0o755)
                        elif change == "extra":
                            (self.bundle / "extra").write_bytes(b"unexpected")
                        else:
                            path = self.bundle / name
                            path.rename(self.bundle / "saved")
                            path.write_bytes(result[0])
                            path.chmod(0o600)
                    return result

                with mock.patch.object(recovery, "_read_at", side_effect=changed):
                    self.assert_refused(self.verify)
                self.bundle.chmod(0o700)
                for path in self.bundle.iterdir():
                    path.chmod(0o600)
                for name in ("extra", "saved"):
                    (self.bundle / name).unlink(missing_ok=True)
        self.assertEqual(self.native.call_count, 1)

    def test_verify_rejects_bundle_or_source_change_during_native_call(self):
        self.stage()
        for path in (self.bundle / "recovery.img", self.bundle / recovery.PUBLIC_KEY_MEMBER,
                     self.public_key, self.checkout / recovery.CORE_PATH):
            original = path.read_bytes()

            def changed(*args, **kwargs):
                path.write_bytes(b"x" * len(original))
                return copy.deepcopy(self.report)

            with self.subTest(path=path), mock.patch.object(recovery, "_native_verify", side_effect=changed):
                self.assert_refused(self.verify)
            path.write_bytes(original)

    def test_cli_local_defaults_never_resolve_or_read_the_private_key(self):
        local = self.root / "local.json"
        (self.root / "fake").mkdir()
        (self.root / "fake/public.pem").write_bytes(self.public_key_bytes)
        local.write_text(json.dumps({"avbtool": "fake/avbtool", "public_key": "fake/public.pem",
                                     "openssl": "fake/openssl", "key": "does-not-exist/private.pem"}))
        args = ["stage", "--source-tree", str(self.checkout), "--image", str(self.image),
                "--output-dir", str(self.bundle), "--local-config", str(local), "--avbtool", "explicit-avbtool"]
        with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(recovery.main(args), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "staged")
        self.assertEqual(self.native.call_args.kwargs, {"avbtool": Path("explicit-avbtool"),
                         "public_key": self.root / "fake/public.pem", "openssl": self.root / "fake/openssl"})
        self.assertNotIn("does-not-exist", output.getvalue())
        with mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(recovery.main(["verify", "--source-tree", str(self.checkout),
                                           "--bundle", str(self.bundle)]), 1)


class PublicRecoveryHookTests(unittest.TestCase):
    def test_public_make_guard_matches_reviewed_profile_patch_and_image(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "device/xiaomi/nezha/recovery-prebuilt.mk").read_text()
        source = json.loads((root / recovery.SOURCE_CONTRACT_PATH).read_bytes())
        profile = (root / recovery.PROFILE_PATH).read_bytes()
        for digest in (recovery.EXPECTED_IMAGE["sha256"], recovery.EXPECTED_PUBLIC_KEY_SHA256,
                       recovery.EXPECTED_KEY, recovery._identity(profile)["sha256"],
                       source["source_files"][0]["after"]["sha256"], source["semantic_files"][0]["sha256"]):
            self.assertIn(digest, text)
        self.assertIn("$(BOARD_RECOVERYIMAGE_PARTITION_SIZE),104857600", text)
        self.assertIn("$(BOARD_BOOT_HEADER_VERSION),4", text)
        self.assertIn("$(BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE),true", text)
        self.assertIn("$(BOARD_AVB_ENABLE),true", text)
        self.assertIn("TARGET_PREBUILT_RECOVERY := $(NEZHA_RECOVERY_INPUTS)/recovery.img", text)
        self.assertIn("NEZHA_RECOVERY_RECEIPT_SHA256", text)
        self.assertIn("$(NEZHA_RECOVERY_SCHEMA_VERSION),2", text)
        self.assertIn("recovery-public.pem", text)
        self.assertIn("run recovery_inputs.py stage", text)
        self.assertIn("/vendor/xiaomi/nezha-recovery/", (root / ".gitignore").read_text())
        for forbidden in ("--disable-verity", "--disable-verification", "--flags 3", "androidboot.selinux=permissive",
                          "BOARD_CUSTOM_BOOTIMG_MK :=", "BOARD_AVB_KEY_PATH :=", "include $(NEZHA_DEVICE_PATH)/recovery-prebuilt.mk"):
            self.assertNotIn(forbidden, text)

    def test_public_key_selection_and_override_guards_are_exact(self):
        # Source checks and a small value model; this does not execute Make/Kati.
        root = Path(__file__).resolve().parents[1]
        text = (root / "device/xiaomi/nezha/recovery-prebuilt.mk").read_text()
        self.assertIn("BOARD_AVB_RECOVERY_KEY_PATH := $(NEZHA_RECOVERY_INPUTS)/recovery-public.pem", text)
        required = {"BOARD_AVB_RECOVERY_KEY_PATH": "vendor/xiaomi/nezha-recovery/recovery-public.pem",
                    "BOARD_AVB_RECOVERY_ALGORITHM": "SHA256_RSA4096",
                    "BOARD_AVB_RECOVERY_ROLLBACK_INDEX": "1", "BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION": "1"}
        for variable, expected in required.items():
            with self.subTest(variable=variable):
                self.assertIn(f"ifneq ($({variable}),{expected})\n$(error", text)
                for override in ("", "testkey.pem", "SHA256_RSA2048", "0", "2"):
                    self.assertNotEqual(override, expected)
        self.assertNotIn("BOARD_AVB_KEY_PATH :=", text)
        self.assertNotIn("BOARD_AVB_BOOT_KEY_PATH :=", text)


if __name__ == "__main__":
    unittest.main()
