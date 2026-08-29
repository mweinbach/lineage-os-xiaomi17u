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
from scripts import recovery_source_contracts as composition
from scripts import target_files_metadata as metadata


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
        core, common = b"reviewed patched core fixture\n", b"pinned releasetools fixture\n"
        patch = b"diff --git a/core/Makefile b/core/Makefile\nsynthetic patch fixture\n"
        self.source = {
            "schema_version": 1,
            "project": copy.deepcopy(composition.PROJECT),
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

    def enable_composition(self):
        """Bind inert source bytes to the actual composition record schema."""
        original_core = (self.checkout / recovery.CORE_PATH).read_bytes()
        final_core = b"synthetic recovery and direct-custom-image core\n"
        consumer = b"synthetic A/B-only recovery packaging consumer\n"
        packaging_patch = b"diff --git a/tools/releasetools/add_img_to_target_files.py b/tools/releasetools/add_img_to_target_files.py\nfixture\n"
        custom_patch = b"diff --git a/core/Makefile b/core/Makefile\nfixture\n"
        data = {recovery.COMMON_PATH: (self.checkout / recovery.COMMON_PATH).read_bytes(),
                recovery.CORE_PATH: original_core, composition.ADD_IMG_PATH: consumer}
        for paths in composition.SEMANTIC_PATHS.values():
            for path in paths:
                data.setdefault(path, ("synthetic " + path + "\n").encode())
        packaging_record = {
            "schema_version": 1, "contract_id": "nezha-ab-only-recovery-packaging-v1",
            "project": copy.deepcopy(composition.PROJECT), "requires_patch": recovery.PATCH_PATH,
            "patch": {"path": composition.PACKAGING_PATCH, **recovery._identity(packaging_patch)},
            "source_files": [{"path": composition.ADD_IMG_PATH,
                              "before": recovery._identity(b"synthetic original consumer\n"),
                              "after": recovery._identity(consumer)}],
            "semantic_files": [{"path": path, **recovery._identity(data[path])}
                               for path in composition.SEMANTIC_PATHS[composition.PACKAGING_PATH]],
            "validation_scope": {"python_recovery_branch_only": True, "full_target_files_verified": False,
                                 "ota_verified": False, "super_verified": False,
                                 "signed_rom_chain_verified": False, "phone_operations": []},
        }
        custom_record = {
            "schema_version": 1, "contract_id": "nezha-direct-avb-custom-images-v1",
            "project": copy.deepcopy(composition.PROJECT), "requires_patch": recovery.PATCH_PATH,
            "patch": {"path": composition.COMPOSED_PATCH, **recovery._identity(custom_patch)},
            "source_files": [{"path": recovery.CORE_PATH, "before": recovery._identity(original_core),
                              "after": recovery._identity(final_core)}],
            "semantic_files": [{"path": path, **recovery._identity(data[path])}
                               for path in composition.SEMANTIC_PATHS[composition.COMPOSED_PATH]],
            "composed_semantic_files": [{"path": composition.ADD_IMG_PATH,
                                          "requires_patch": composition.PACKAGING_PATCH,
                                          **recovery._identity(consumer)}],
        }
        for relative, raw in ((composition.PACKAGING_PATCH, packaging_patch),
                              (composition.COMPOSED_PATCH, custom_patch),
                              (composition.PACKAGING_PATH, recovery._canonical(packaging_record)),
                              (composition.COMPOSED_PATH, recovery._canonical(custom_record))):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        data[recovery.CORE_PATH] = final_core
        for relative, raw in data.items():
            path = self.checkout / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.options["composed_source_contract"] = self.root / composition.COMPOSED_PATH
        return packaging_record, custom_record, original_core

    def stage(self, bundle=None):
        return recovery.stage_inputs(self.image, bundle or self.bundle, **self.options)

    def enable_metadata_composition(self):
        """Extend inert source fixtures through the separate metadata contract."""
        self.enable_composition()
        # The metadata composer validates complete unified-patch file headers.
        for contract_path in metadata.SOURCE_CONTRACTS[:3]:
            path = self.root / contract_path
            record = json.loads(path.read_bytes())
            patch_path = self.root / record["patch"]["path"]
            short = record["source_files"][0]["path"].removeprefix("build/make/")
            raw = patch_path.read_bytes() + f"--- a/{short}\n+++ b/{short}\n".encode()
            patch_path.write_bytes(raw)
            record["patch"].update(recovery._identity(raw))
            path.write_bytes(recovery._canonical(record))
        self.source = json.loads((self.root / recovery.SOURCE_CONTRACT_PATH).read_bytes())
        original_core = (self.checkout / recovery.CORE_PATH).read_bytes()
        original_common = (self.checkout / recovery.COMMON_PATH).read_bytes()
        for index, source_path, new_bytes in (
                (3, recovery.COMMON_PATH, b"synthetic optional partition property source\n"),
                (4, recovery.CORE_PATH, b"synthetic metadata build core\n")):
            old_bytes = (self.checkout / source_path).read_bytes()
            short = source_path.removeprefix("build/make/")
            patch_bytes = (f"diff --git a/{short} b/{short}\n--- a/{short}\n+++ b/{short}\n"
                           "fixture\n").encode()
            (self.root / metadata.SOURCE_PATCHES[index]).write_bytes(patch_bytes)
            record = {
                "schema_version": 1, "contract_id": metadata.SOURCE_IDS[index],
                "project": copy.deepcopy(composition.PROJECT),
                "patch": {"path": metadata.SOURCE_PATCHES[index], **recovery._identity(patch_bytes)},
                "source_files": [{"path": source_path, "before": recovery._identity(old_bytes),
                                  "after": recovery._identity(new_bytes)}],
                "semantic_files": [],
            }
            for path in metadata.SOURCE_SEMANTICS[index]:
                data = ("synthetic " + path + "\n").encode()
                target = self.checkout / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                record["semantic_files"].append({"path": path, **recovery._identity(data)})
            if index == 4:
                record["scope"] = copy.deepcopy(metadata.SCOPE)
                record["required_predecessor_contracts"] = [
                    {"path": path, **recovery._identity((self.root / path).read_bytes())}
                    for path in metadata.SOURCE_CONTRACTS[:4]]
            (self.root / metadata.SOURCE_CONTRACTS[index]).write_bytes(recovery._canonical(record))
            (self.checkout / source_path).write_bytes(new_bytes)
        self.options["composed_source_contract"] = self.root / composition.METADATA_PATH
        return original_core, original_common

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

    def test_explicit_composed_source_binds_ordered_patches_and_all_final_files(self):
        self.enable_composition()
        staged = self.stage()
        self.assertEqual(staged["status"], "staged")
        self.assertEqual((self.bundle / "recovery.img").read_bytes(), self.image_bytes)
        self.assertEqual((self.bundle / recovery.PUBLIC_KEY_MEMBER).read_bytes(), self.public_key_bytes)
        receipt = json.loads((self.bundle / "receipt.json").read_bytes())
        source = receipt["build_source"]
        chain = source["composition"]
        self.assertEqual(chain["project"], composition.PROJECT)
        self.assertEqual([item["path"] for item in chain["ordered_patches"]],
                         [recovery.PATCH_PATH, composition.PACKAGING_PATCH, composition.COMPOSED_PATCH])
        self.assertEqual(chain["core_transitions"][0]["after"], chain["core_transitions"][1]["before"])
        self.assertEqual(len(source["files"]), 7)
        for row in source["files"]:
            self.assertEqual({key: row[key] for key in ("sha256", "size_bytes")},
                             recovery._identity((self.checkout / row["path"]).read_bytes()))
        self.assertFalse(chain["patches_applied_by_this_tool"])
        self.assertFalse(chain["whole_source_tree_verified"])
        include = (self.bundle / "recovery-inputs.mk").read_text()
        self.assertIn("NEZHA_RECOVERY_CORE_COMPOSITION_SHA256 := " + source["contract"]["sha256"], include)
        self.assertEqual(receipt["scope"], recovery.SCOPE)
        self.assertEqual(self.verify()["status"], "verified")
        self.assertEqual(self.native.call_args.kwargs["public_key"], self.bundle / recovery.PUBLIC_KEY_MEMBER)
        plan = recovery.plan(composed_source_contract=self.options["composed_source_contract"])
        self.assertEqual(plan["source_composition"], chain)
        self.assertFalse(plan["image_verified"])

    def test_composed_core_is_not_selected_implicitly(self):
        self.enable_composition()
        options = {key: value for key, value in self.options.items() if key != "composed_source_contract"}
        with self.assertRaisesRegex(recovery.RecoveryInputsError, "required prebuilt-recovery patch"):
            recovery.stage_inputs(self.image, self.bundle, **options)
        self.native.assert_not_called()
        self.assertFalse(self.bundle.exists())

    def test_metadata_composition_stages_exact_five_patch_nine_source_bundle(self):
        self.enable_metadata_composition()
        self.stage()
        receipt = json.loads((self.bundle / "receipt.json").read_bytes())
        source = receipt["build_source"]
        self.assertEqual(source["composition"], metadata.compose_sources(self.root))
        self.assertEqual([row["path"] for row in source["composition"]["ordered_patches"]],
                         list(metadata.SOURCE_PATCHES))
        self.assertEqual(len(source["files"]), 9)
        self.assertEqual(receipt["scope"], recovery.SCOPE)
        self.assertEqual((self.bundle / "recovery.img").read_bytes(), self.image_bytes)
        self.assertEqual((self.bundle / recovery.PUBLIC_KEY_MEMBER).read_bytes(), self.public_key_bytes)
        self.assertEqual(self.verify()["status"], "verified")

    def test_metadata_source_is_not_admitted_by_either_legacy_selection(self):
        self.enable_metadata_composition()
        for contract in (None, self.root / composition.COMPOSED_PATH):
            with self.subTest(contract=contract):
                options = {**self.options, "composed_source_contract": contract}
                with self.assertRaisesRegex(ValueError, "required prebuilt-recovery patch"):
                    recovery.stage_inputs(self.image, self.bundle, **options)
                self.assertFalse(self.bundle.exists())
        self.native.assert_not_called()

    def test_metadata_selection_checks_each_final_source_before_native_verification(self):
        self.enable_metadata_composition()
        chain = metadata.compose_sources(self.root)
        for row in chain["final_source_files"]:
            with self.subTest(path=row["path"]):
                path = self.checkout / row["path"]
                original = path.read_bytes()
                path.write_bytes(original + b"unexpected edit\n")
                with self.assertRaisesRegex(ValueError, "required prebuilt-recovery patch"):
                    self.stage()
                self.assertFalse(self.bundle.exists())
                path.write_bytes(original)
        self.native.assert_not_called()

    def test_metadata_composition_rejects_noncanonical_selection_and_common_gap(self):
        self.enable_metadata_composition()
        selected = self.root / "copied-metadata.json"
        selected.write_bytes((self.root / composition.METADATA_PATH).read_bytes() + b" ")
        self.options["composed_source_contract"] = selected
        with self.assertRaisesRegex(ValueError, "explicit metadata composition differs"):
            self.stage()
        self.options["composed_source_contract"] = self.root / composition.METADATA_PATH
        path = self.root / metadata.SOURCE_CONTRACTS[3]
        record = json.loads(path.read_bytes())
        record["source_files"][0]["before"]["sha256"] = "0" * 64
        path.write_bytes(recovery._canonical(record))
        with self.assertRaisesRegex(ValueError, "source patch chain has a gap"):
            self.stage()
        self.native.assert_not_called()
        self.assertFalse(self.bundle.exists())

    def test_new_metadata_receipt_cannot_replace_an_older_composed_receipt(self):
        original_core, original_common = self.enable_metadata_composition()
        old_contract = self.root / composition.COMPOSED_PATH
        (self.checkout / recovery.CORE_PATH).write_bytes(original_core)
        (self.checkout / recovery.COMMON_PATH).write_bytes(original_common)
        old_options = {**self.options, "composed_source_contract": old_contract}
        recovery.stage_inputs(self.image, self.bundle, **old_options)
        preserved = {path.name: path.read_bytes() for path in self.bundle.iterdir()}
        for row in json.loads((self.root / composition.METADATA_PATH).read_bytes())["source_files"]:
            (self.checkout / row["path"]).write_bytes(b"synthetic metadata build core\n")
        (self.checkout / recovery.COMMON_PATH).write_bytes(b"synthetic optional partition property source\n")
        new_bundle = self.root / "new" / recovery.BUNDLE_PATH
        self.stage(new_bundle)
        self.assertEqual(preserved, {path.name: path.read_bytes() for path in self.bundle.iterdir()})
        with self.assertRaisesRegex(ValueError, "receipt identity"):
            self.verify()
        (self.checkout / recovery.CORE_PATH).write_bytes(original_core)
        (self.checkout / recovery.COMMON_PATH).write_bytes(original_common)
        self.assertEqual(recovery.verify_bundle(self.bundle, **old_options)["status"], "verified")

    def test_legacy_bundle_and_contract_remain_unchanged_during_separate_composed_stage(self):
        self.stage()
        original_bundle = {path.name: path.read_bytes() for path in self.bundle.iterdir()}
        original_contract = (self.root / recovery.SOURCE_CONTRACT_PATH).read_bytes()
        _, _, original_core = self.enable_composition()
        composed_bundle = self.root / "composed" / recovery.BUNDLE_PATH
        self.stage(composed_bundle)
        self.assertEqual(original_bundle, {path.name: path.read_bytes() for path in self.bundle.iterdir()})
        self.assertEqual(original_contract, (self.root / recovery.SOURCE_CONTRACT_PATH).read_bytes())
        with self.assertRaisesRegex(recovery.RecoveryInputsError, "receipt identity"):
            self.verify()
        (self.checkout / recovery.CORE_PATH).write_bytes(original_core)
        self.options.pop("composed_source_contract")
        self.assertEqual(self.verify()["status"], "verified")
        self.assertNotIn(b"CORE_COMPOSITION", original_bundle["recovery-inputs.mk"])

    def test_composition_rejects_wrong_base_consumer_semantics_and_patch_order(self):
        packaging_record, custom, _ = self.enable_composition()
        cases = [
            (composition.COMPOSED_PATH, custom, lambda row: row["project"].update(commit="0" * 40)),
            (composition.COMPOSED_PATH, custom, lambda row: row.update(requires_patch=composition.PACKAGING_PATCH)),
            (composition.COMPOSED_PATH, custom, lambda row: row["source_files"][0]["before"].update(sha256="0" * 64)),
            (composition.COMPOSED_PATH, custom, lambda row: row["composed_semantic_files"][0].update(sha256="0" * 64)),
            (composition.COMPOSED_PATH, custom, lambda row: row["semantic_files"][0].update(sha256="0" * 64)),
            (composition.COMPOSED_PATH, custom, lambda row: row["semantic_files"].append(copy.deepcopy(row["semantic_files"][0]))),
            (composition.PACKAGING_PATH, packaging_record, lambda row: row["semantic_files"][0].update(sha256="0" * 64)),
        ]
        for relative, original, mutate in cases:
            with self.subTest(relative=relative, mutation=mutate):
                changed = copy.deepcopy(original)
                mutate(changed)
                path = self.root / relative
                path.write_bytes(recovery._canonical(changed))
                self.assert_refused(self.stage)
                self.assertFalse(self.bundle.exists())
                path.write_bytes(recovery._canonical(original))
        self.native.assert_not_called()

    def test_composition_rejects_unreviewed_control_copy_or_extra_patch_target(self):
        self.enable_composition()
        selected = self.root / "unreviewed.json"
        selected.write_bytes((self.root / composition.COMPOSED_PATH).read_bytes() + b" ")
        self.options["composed_source_contract"] = selected
        with self.assertRaisesRegex(ValueError, "explicit composition differs"):
            self.stage()
        self.options["composed_source_contract"] = self.root / composition.COMPOSED_PATH
        patch = self.root / composition.COMPOSED_PATCH
        raw = patch.read_bytes() + b"diff --git a/unrelated b/unrelated\n"
        patch.write_bytes(raw)
        record = json.loads((self.root / composition.COMPOSED_PATH).read_bytes())
        record["patch"].update(recovery._identity(raw))
        (self.root / composition.COMPOSED_PATH).write_bytes(recovery._canonical(record))
        with self.assertRaisesRegex(ValueError, "only its declared source file"):
            self.stage()
        self.native.assert_not_called()

    def test_composed_stage_rejects_changed_semantic_source_and_public_patch(self):
        self.enable_composition()
        path = self.checkout / "build/make/tools/releasetools/build_super_image.py"
        original = path.read_bytes()
        path.write_bytes(original + b"changed\n")
        self.assert_refused(self.stage)
        path.write_bytes(original)
        self.stage()
        patch = self.root / composition.COMPOSED_PATCH
        patch.write_bytes(patch.read_bytes() + b"changed\n")
        self.assert_refused(self.verify)

    def test_composed_control_change_during_native_verification_fails_before_publication(self):
        self.enable_composition()

        def changed(*args, **kwargs):
            path = self.root / composition.COMPOSED_PATH
            record = json.loads(path.read_bytes())
            record["review_note"] = "changed during native verification"
            path.write_bytes(recovery._canonical(record))
            return copy.deepcopy(self.report)

        self.native.side_effect = changed
        with self.assertRaisesRegex(recovery.RecoveryInputsError, "control contracts changed"):
            self.stage()
        self.assertFalse(self.bundle.exists())

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
    def test_metadata_renderer_preserves_legacy_template_and_mode_guards(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / composition.RECOVERY_TEMPLATE).read_bytes()
        legacy, legacy_identity = composition.compose(root, root / composition.COMPOSED_PATH)
        selected, selected_identity = composition.compose(root, root / composition.METADATA_PATH)
        rendered = composition.render_metadata_recovery_include(
            template, root=root, selected_contract=root / composition.METADATA_PATH)
        self.assertEqual((root / composition.RECOVERY_TEMPLATE).read_bytes(), template)
        self.assertEqual(legacy_identity, {"sha256": "fe4ac5f9c0db04df0d8af9e5867edf2090310b34f03d96f7856d105aa35c5abe",
                                           "size_bytes": 3516})
        self.assertNotIn(legacy_identity["sha256"].encode(), rendered)
        self.assertNotIn(legacy["source_files"][0]["after"]["sha256"].encode(), rendered)
        self.assertIn(selected_identity["sha256"].encode(), rendered)
        for row in selected["composition"]["final_source_files"]:
            path, digest, size = row["path"], row["sha256"], row["size_bytes"]
            self.assertIn(f"test -f {path} && test ! -L {path}".encode(), rendered)
            self.assertIn(f"wc -c < {path} 2>/dev/null)),{size})".encode(), rendered)
            self.assertIn(f"sha256sum < {path} 2>/dev/null | cut -d ' ' -f 1),{digest})".encode(), rendered)
        # Everything from the actual payload checks onward, including the A/B
        # and no-two-step guards, must be retained literally, not reconstructed.
        boundary = b"ifneq ($(shell test -f vendor/xiaomi/nezha-recovery/recovery.img"
        self.assertEqual(rendered.split(boundary, 1)[1], template.split(boundary, 1)[1])
        prefix = b"ifeq ($(origin NEZHA_RECOVERY_CORE_COMPOSITION_SHA256),undefined)\n"
        self.assertTrue(rendered.startswith(template.split(prefix, 1)[0]))
        self.assertEqual(selected["composition"], metadata.compose_sources(root))

    def test_metadata_renderer_rejects_legacy_selection_or_changed_template(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / composition.RECOVERY_TEMPLATE).read_bytes()
        with self.assertRaisesRegex(ValueError, "requires explicit metadata composition"):
            composition.render_metadata_recovery_include(
                template, root=root, selected_contract=root / composition.COMPOSED_PATH)
        with self.assertRaisesRegex(ValueError, "unchanged authored template"):
            composition.render_metadata_recovery_include(
                template + b"# changed\n", root=root, selected_contract=root / composition.METADATA_PATH)

    def test_composed_make_guard_binds_the_ordered_current_public_contracts(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "device/xiaomi/nezha/recovery-prebuilt.mk").read_text()
        source, identity = composition.compose(root, root / composition.COMPOSED_PATH)
        self.assertIn("ifneq ($(value NEZHA_RECOVERY_CORE_COMPOSITION_SHA256)," + identity["sha256"] + ")", text)
        self.assertIn("ifneq ($(origin NEZHA_RECOVERY_CORE_COMPOSITION_SHA256),file)", text)
        self.assertIn("ifneq ($(NEZHA_RECOVERY_CORE_SHA256)," + source["source_files"][0]["after"]["sha256"] + ")", text)
        self.assertIn("ifneq ($(shell sha256sum < build/make/core/Makefile 2>/dev/null | cut -d ' ' -f 1),$(NEZHA_RECOVERY_CORE_SHA256))", text)
        baseline = json.loads((root / recovery.SOURCE_CONTRACT_PATH).read_bytes())
        self.assertNotEqual(baseline["source_files"][0]["after"], source["source_files"][0]["after"])
        self.assertIn(baseline["source_files"][0]["after"]["sha256"], text)

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
