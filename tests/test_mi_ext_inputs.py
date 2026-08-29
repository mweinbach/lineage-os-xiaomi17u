"""Offline mi_ext admission tests with inert fixtures and no native processes.

Synthetic bytes replace the known image only inside each fixture. These tests
exercise provenance, publication, source binding and metadata rejection; they
are not AVB, Android image-build, super-image or device validation.
"""

import copy
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from scripts import mi_ext_inputs as mi


WORKSPACE = mi.ROOT


class MiExtInputsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.controls = self.root / "controls"
        self.inputs = self.root / "incoming"
        self.output_parent = self.root / "prepared"
        self.source = self.root / "source"
        for path in (self.controls, self.inputs, self.output_parent, self.source):
            path.mkdir()
        self.bundle = self.output_parent / "mi-ext-v1"
        self.image = self.inputs / "mi_ext_a.img"
        self.image_data = b"Inert mi_ext fixture. This is not an EROFS or AVB image.\n"
        self.image.write_bytes(self.image_data)
        self.expected = mi.identity(self.image_data)
        self.logical = self.inputs / "receipt.json"
        self.enterContext(mock.patch.object(mi, "ROOT", self.controls))
        self.enterContext(mock.patch.object(mi, "EXPECTED_IMAGE", self.expected))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native process forbidden")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("shell forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.config = json.loads((WORKSPACE / mi.CONTRACT_PATH).read_bytes())
        self.config["image"].update(self.expected)
        self.config["avb"]["file_size_bytes"] = self.expected["size_bytes"]
        self.logical_value = {
            "schema_version": 1, "status": "complete", "authentication_verified": False,
            "all_geometry_and_metadata_copies_valid": True,
            "all_primary_backup_pairs_match": True, "all_slots_identical": True,
            "source_image": {"path": "/private/inert/super.raw.img", **self.config["source_super"]},
            "outputs": [copy.deepcopy(self.config["image"])],
        }
        self.factory = {
            "device": "nezha", "hardware_region": "CN",
            "package": {"sha256": mi.EXPECTED_PACKAGE, "origin_verified": False},
            "logical_partitions": {"outputs": [copy.deepcopy(self.config["image"])],
                                   "source_image": copy.deepcopy(self.config["source_super"])},
            "avb": {"hashtree_preflight": [copy.deepcopy(self.config["avb"])]},
        }
        patch = b"Inert source patch fixture\n"
        core = b"Inert composed native core fixture\n"
        self.source_contract = {
            "schema_version": 1, "contract_id": "nezha-direct-avb-custom-images-v1",
            "project": {"path": "build/make", "commit": mi.BUILD_COMMIT},
            "requires_patch": "patches/evolution/0005-verified-prebuilt-recovery.patch",
            "patch": {"path": mi.PATCH_PATH, **mi.identity(patch)},
            "source_files": [{"path": mi.CORE_PATH, "before": mi.EXPECTED_CORE_BEFORE,
                              "after": mi.identity(core)}],
            "semantic_files": [], "composed_semantic_files": [],
        }
        self.write(self.controls / mi.PATCH_PATH, patch)
        self.write(self.source / mi.CORE_PATH, core)
        for path in sorted(mi.SEMANTIC_PATHS):
            raw = ("Inert source fixture " + path + "\n").encode()
            self.write(self.source / path, raw)
            self.source_contract["semantic_files"].append({"path": path, **mi.identity(raw)})
        composed = b"Inert A/B-only composed releasetools fixture\n"
        self.write(self.source / mi.COMPOSED_PATH, composed)
        self.source_contract["composed_semantic_files"] = [
            {"path": mi.COMPOSED_PATH, "requires_patch": mi.COMPOSED_PATCH, **mi.identity(composed)}]
        for relative in ("scripts/mi_ext_inputs.py", "scripts/artifact_files.py"):
            self.write(self.controls / relative, (WORKSPACE / relative).read_bytes())
        self.save_inputs()
        self.save_source()

    @staticmethod
    def write(path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def save_inputs(self):
        logical_raw = mi.encoded(self.logical_value)
        self.logical.write_bytes(logical_raw)
        self.config["logical_receipt"] = {"path": "artifacts/factory/logical/receipt.json", **mi.identity(logical_raw)}
        self.factory["logical_partitions"]["receipt"] = copy.deepcopy(self.config["logical_receipt"])
        factory_raw = mi.encoded(self.factory)
        self.write(self.controls / mi.FACTORY_RECORD_PATH, factory_raw)
        self.config["factory_record"] = {"path": mi.FACTORY_RECORD_PATH, **mi.identity(factory_raw)}
        self.write(self.controls / mi.CONTRACT_PATH, mi.encoded(self.config))

    def save_config(self):
        self.write(self.controls / mi.CONTRACT_PATH, mi.encoded(self.config))

    def save_source(self):
        self.write(self.controls / mi.SOURCE_CONTRACT_PATH, mi.encoded(self.source_contract))

    def stage(self, output=None):
        return mi.stage_inputs(self.image, output or self.bundle, logical_receipt=self.logical)

    def verify(self, **kwargs):
        return mi.verify_bundle(self.bundle, **kwargs)

    def refused(self, call):
        with self.assertRaises((ValueError, OSError)):
            call()

    def packaging(self):
        self.metadata = self.root / "metadata"
        self.metadata.mkdir()
        self.images = self.root / "images"
        self.images.mkdir()
        (self.images / "mi_ext.img").write_bytes(self.image_data)
        names = self.config["dynamic_layout"]["logical_partition_names"]
        self.info = {
            "avb_enable": "true", "ab_update": "true", "use_dynamic_partitions": "true", "virtual_ab": "true",
            "avb_custom_images_partition_list": "mi_ext", "avb_custom_images_direct_partition_list": "mi_ext",
            "custom_images_partition_list": "", "avb_mi_ext_image_list": "mi_ext.img",
            "avb_vbmeta_system": "system system_ext product",
            "dynamic_partition_list": " ".join(names), "super_qti_dynamic_partitions_partition_list": " ".join(names),
            "super_partition_groups": "qti_dynamic_partitions", "super_partition_size": "15300820992",
            "super_qti_dynamic_partitions_group_size": "15290335232",
        }
        self.misc = self.metadata / "misc_info.txt"
        self.fastboot = self.metadata / "fastboot-info.txt"
        self.ab = self.metadata / "ab_partitions.txt"
        self.save_info()
        self.fastboot.write_text("version 1\nflash boot\nflash --apply-vbmeta vbmeta\nreboot fastboot\nupdate-super\nflash system\nflash mi_ext\n")
        self.ab.write_text("\n".join(["boot", "recovery", *names]) + "\n")

    def save_info(self):
        self.misc.write_text("".join(key + "=" + value + "\n" for key, value in self.info.items()))

    def check(self):
        return mi.check_packaging(self.misc, self.fastboot, self.ab, self.images)

    def test_fresh_stage_preserves_originals_and_relocates_with_exact_provenance(self):
        before = {path: path.read_bytes() for path in (self.image, self.logical)}
        result = self.stage()
        self.assertEqual(result["status"], "staged")
        self.assertEqual(set(path.name for path in self.bundle.iterdir()),
                         {mi.IMAGE_MEMBER, mi.LOGICAL_RECEIPT_MEMBER, mi.RECEIPT_NAME})
        self.assertEqual(stat.S_IMODE(self.bundle.stat().st_mode), 0o700)
        for path in self.bundle.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        verified = self.verify()
        self.assertFalse(verified["actual_native_source_bytes_checked"])
        self.assertFalse(verified["native_avb_run"])
        self.assertEqual(verified["receipt"], result["receipt"])
        self.assertEqual(verified["scope"], mi.SCOPE)
        relocated = self.output_parent / "moved"
        self.bundle.rename(relocated)
        self.bundle = relocated
        self.assertEqual(self.verify(), verified)
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        self.assertNotIn(str(self.root), (self.bundle / mi.RECEIPT_NAME).read_text())

    def test_source_verification_requires_all_actual_composed_files(self):
        self.stage()
        self.assertTrue(self.verify(source_tree=self.source)["actual_native_source_bytes_checked"])
        paths = [mi.CORE_PATH, *mi.SEMANTIC_PATHS, mi.COMPOSED_PATH]
        for relative in paths:
            with self.subTest(path=relative):
                path = self.source / relative
                original = path.read_bytes()
                path.write_bytes(b"unreviewed\n")
                self.refused(lambda: self.verify(source_tree=self.source))
                path.write_bytes(original)

    def test_offline_admission_binds_package_and_generates_fixed_native_guards(self):
        self.stage()
        receipt = self.bundle / mi.RECEIPT_NAME
        self.refused(lambda: mi.validate_admission(receipt, expected_package_sha256="0" * 64))
        bound = mi.validate_admission(receipt, expected_package_sha256=mi.EXPECTED_PACKAGE)
        generated = mi.render_board_include(bound)
        self.assertIn("BOARD_MI_EXT_IMAGE_LIST := vendor/xiaomi/nezha-mi-ext/mi_ext.img", generated)
        self.assertIn(self.expected["sha256"], generated)
        self.assertIn(bound["receipt"]["sha256"], generated)
        for row in bound["native_source"]["files"]:
            self.assertIn(row["sha256"], generated)
        self.assertIn(".KATI_READONLY :=", generated)
        self.assertIn("BOARD_AVB_CUSTOMIMAGES_DIRECT_PARTITION_LIST := mi_ext", generated)
        self.assertNotIn("--flags", generated)
        self.assertFalse(bound["scope"]["complete_rom_admitted"])

    def test_noncanonical_receipt_and_forged_admission_fail(self):
        self.stage()
        self.refused(lambda: mi.validate_admission(self.bundle / "another.json", expected_package_sha256=mi.EXPECTED_PACKAGE))
        binding = mi.validate_admission(self.bundle / mi.RECEIPT_NAME, expected_package_sha256=mi.EXPECTED_PACKAGE)
        for key, value in (("bundle", "elsewhere"), ("image", {}), ("native_source", {}), ("scope", {})):
            with self.subTest(key=key):
                mutated = copy.deepcopy(binding)
                mutated[key] = value
                self.refused(lambda: mi.render_board_include(mutated))
        binding["receipt"]["sha256"] = "x'$(shell bad)"
        self.refused(lambda: mi.render_board_include(binding))

    def test_changed_image_hash_or_length_never_publishes(self):
        for raw in (b"X" + self.image_data[1:], self.image_data[:-1], self.image_data + b"X"):
            with self.subTest(raw=raw):
                self.image.write_bytes(raw)
                self.refused(self.stage)
                self.assertFalse(self.bundle.exists())

    def test_changed_logical_receipt_never_publishes(self):
        self.logical.write_bytes(self.logical.read_bytes() + b" ")
        self.refused(self.stage)
        self.assertFalse(self.bundle.exists())

    def test_resealed_logical_receipt_rejects_wrong_parent_duplicate_image_and_authentication(self):
        original = copy.deepcopy(self.logical_value)
        mutations = [lambda value: value.update(authentication_verified=True),
                     lambda value: value.update(status="partial"),
                     lambda value: value.update(all_slots_identical=False),
                     lambda value: value["source_image"].update(sha256="0" * 64),
                     lambda value: value["outputs"].append(copy.deepcopy(value["outputs"][0]))]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.logical_value = copy.deepcopy(original)
                mutate(self.logical_value)
                self.save_inputs()
                self.refused(self.stage)
                self.assertFalse(self.bundle.exists())

    def test_unreviewed_config_identity_layout_or_readiness_is_rejected(self):
        original = copy.deepcopy(self.config)
        mutations = [lambda value: value.update(schema_version=True),
                     lambda value: value.update(factory_package_sha256="0" * 64),
                     lambda value: value["image"].update(sha256="0" * 64),
                     lambda value: value["avb"].update(source="vbmeta_system"),
                     lambda value: value["dynamic_layout"].update(super_size_bytes=15300820991),
                     lambda value: value["scope"].update(complete_rom_admitted=True),
                     lambda value: value["scope"].update(prebuilt_preserved=1),
                     lambda value: value["logical_receipt"].update(path="../receipt.json")]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.config = copy.deepcopy(original)
                mutate(self.config)
                self.save_config()
                self.refused(self.stage)

    def test_reviewed_source_contract_required_and_duplicate_semantics_refused(self):
        original = copy.deepcopy(self.source_contract)
        mutations = [lambda value: value["project"].update(commit="0" * 40),
                     lambda value: value["source_files"][0].update(before=mi.identity(b"wrong base")),
                     lambda value: value["semantic_files"].append(value["semantic_files"][0]),
                     lambda value: value.update(composed_semantic_files=[]),
                     lambda value: value["composed_semantic_files"][0].update(requires_patch="wrong.patch")]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.source_contract = copy.deepcopy(original)
                mutate(self.source_contract)
                self.save_source()
                self.refused(self.stage)

    def test_changed_native_patch_is_rejected(self):
        (self.controls / mi.PATCH_PATH).write_bytes(b"changed patch\n")
        self.refused(self.stage)
        self.assertFalse(self.bundle.exists())

    def test_duplicate_json_keys_are_rejected(self):
        path = self.controls / mi.CONTRACT_PATH
        path.write_bytes(b'{"schema_version":1,"schema_version":1}')
        self.refused(self.stage)

    def test_existing_output_directory_file_or_symlink_is_never_replaced(self):
        for kind in ("directory", "file", "symlink"):
            with self.subTest(kind=kind):
                output = self.output_parent / kind
                if kind == "directory":
                    output.mkdir()
                    (output / "preserve").write_text("keep")
                elif kind == "file":
                    output.write_text("keep")
                else:
                    output.symlink_to(self.image)
                self.refused(lambda: self.stage(output))
                self.assertTrue(os.path.lexists(output))
        self.assertEqual((self.output_parent / "directory/preserve").read_text(), "keep")
        self.assertEqual((self.output_parent / "file").read_text(), "keep")

    def test_workspace_output_and_output_inside_original_directory_are_refused(self):
        self.refused(lambda: self.stage(self.controls / "tracked-inputs"))
        self.refused(lambda: self.stage(self.inputs / "new-output"))
        self.assertFalse((self.controls / "tracked-inputs").exists())

    def test_symlink_image_and_parent_are_refused(self):
        self.image.unlink()
        original = self.root / "external.img"
        original.write_bytes(self.image_data)
        self.image.symlink_to(original)
        self.refused(self.stage)
        self.image.unlink()
        self.image.write_bytes(self.image_data)
        link = self.root / "linked-inputs"
        link.symlink_to(self.inputs, target_is_directory=True)
        self.refused(lambda: mi.stage_inputs(link / self.image.name, self.bundle, logical_receipt=self.logical))

    def test_hardlinked_image_and_fifo_are_refused_without_blocking(self):
        alias = self.inputs / "alias.img"
        os.link(self.image, alias)
        self.refused(self.stage)
        alias.unlink()
        self.image.unlink()
        os.mkfifo(self.image)
        self.refused(self.stage)

    def test_output_parent_symlink_is_refused(self):
        parent = self.root / "linked-output"
        parent.symlink_to(self.output_parent, target_is_directory=True)
        self.refused(lambda: self.stage(parent / "out"))

    def test_bundle_mutation_and_resealed_receipt_are_refused(self):
        self.stage()
        receipt_path = self.bundle / mi.RECEIPT_NAME
        receipt = json.loads(receipt_path.read_bytes())
        receipt["scope"]["complete_rom_admitted"] = True
        receipt_path.write_bytes(mi.encoded(receipt))
        self.refused(self.verify)

    def test_extra_private_bundle_member_is_refused(self):
        self.stage()
        (self.bundle / "unexpected.key").write_text("not a real key")
        self.refused(self.verify)

    def test_bundle_file_permission_expansion_is_refused(self):
        self.stage()
        (self.bundle / mi.IMAGE_MEMBER).chmod(0o644)
        self.refused(self.verify)

    def test_input_mutation_during_staging_is_rejected_and_partial_output_removed(self):
        original = mi.Reader.recheck
        def change(reader):
            self.image.write_bytes(b"changed")
            original(reader)
        with mock.patch.object(mi.Reader, "recheck", change):
            self.refused(self.stage)
        self.assertFalse(self.bundle.exists())
        self.assertEqual(list(self.output_parent.iterdir()), [])

    def test_publication_race_preserves_other_writer_output(self):
        publish = mi.publish_new_directory
        def collide(staging, output):
            output.mkdir()
            (output / "other-owner").write_text("preserve")
            publish(staging, output)
        with mock.patch.object(mi, "publish_new_directory", side_effect=collide):
            self.refused(self.stage)
        self.assertEqual((self.bundle / "other-owner").read_text(), "preserve")
        self.assertEqual(list(self.output_parent.iterdir()), [self.bundle])

    def test_disk_shortage_fails_without_partial_output(self):
        with mock.patch.object(mi.shutil, "disk_usage", return_value=mock.Mock(free=0)):
            self.refused(self.stage)
        self.assertEqual(list(self.output_parent.iterdir()), [])

    def test_packaging_checks_real_metadata_image_and_exact_flash_order(self):
        self.packaging()
        result = self.check()
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["selected_metadata_and_image_only"])
        self.assertFalse(result["scope"]["target_files_verified"])
        self.assertFalse(result["scope"]["complete_avb_chain_verified"])

    def test_packaging_rejects_even_empty_child_key_and_wrong_owner(self):
        self.packaging()
        original = copy.deepcopy(self.info)
        for key, value in (("avb_mi_ext_key_path", ""), ("avb_mi_ext_algorithm", "NONE"),
                           ("avb_mi_ext_rollback_index_location", "4"),
                           ("avb_vbmeta_system", "system system_ext product mi_ext")):
            with self.subTest(key=key):
                self.info = copy.deepcopy(original)
                self.info[key] = value
                self.save_info()
                self.refused(self.check)

    def test_packaging_rejects_missing_duplicated_or_altered_inventory(self):
        self.packaging()
        original = copy.deepcopy(self.info)
        for key, value in (("avb_custom_images_partition_list", ""),
                           ("avb_custom_images_direct_partition_list", "mi_ext mi_ext"),
                           ("dynamic_partition_list", "system"),
                           ("super_qti_dynamic_partitions_group_size", "15290335233"),
                           ("virtual_ab", "false"), ("avb_mi_ext_image_list", "other.img")):
            with self.subTest(key=key):
                self.info = copy.deepcopy(original)
                self.info[key] = value
                self.save_info()
                self.refused(self.check)

    def test_packaging_rejects_duplicate_misc_keys(self):
        self.packaging()
        self.misc.write_text(self.misc.read_text() + "avb_enable=true\n")
        self.refused(self.check)

    def test_packaging_rejects_missing_or_duplicate_ab_member(self):
        self.packaging()
        for value in ("boot\nsystem\n", "mi_ext\nmi_ext\n"):
            with self.subTest(value=value):
                self.ab.write_text(value)
                self.refused(self.check)

    def test_packaging_rejects_early_duplicate_missing_and_alternate_flash_entries(self):
        self.packaging()
        original = self.fastboot.read_text()
        for value in ("flash mi_ext\n" + original, original.replace("flash mi_ext\n", ""),
                      original.replace("update-super\n", ""),
                      original.replace("flash mi_ext\n", "flash mi_ext other.img\n"),
                      original + "flash --slot-other mi_ext mi_ext.img\n"):
            with self.subTest(value=value):
                self.fastboot.write_text(value)
                self.refused(self.check)

    def test_packaging_rejects_changed_or_missing_image(self):
        self.packaging()
        image = self.images / mi.IMAGE_MEMBER
        image.write_bytes(b"wrong")
        self.refused(self.check)
        image.unlink()
        self.refused(self.check)

    def test_returned_scope_mutation_does_not_change_followup_verification(self):
        staged = self.stage()
        staged["scope"]["phone_operations"].append("forbidden")
        staged["scope"]["complete_rom_admitted"] = True
        self.assertEqual(self.verify()["scope"], mi.SCOPE)
        self.assertEqual(mi.SCOPE["phone_operations"], [])


if __name__ == "__main__":
    unittest.main()
