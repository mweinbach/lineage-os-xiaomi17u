"""Offline mi_ext admission tests with inert fixtures and no native processes.

Synthetic bytes replace the known image only inside each fixture. These tests
exercise provenance, publication, source binding and metadata rejection; they
are not AVB, Android image-build, super-image or device validation.
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

from scripts import mi_ext_inputs as mi
from scripts import recovery_source_contracts as recovery_sources
from scripts import target_files_metadata as metadata


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

    def stage(self, output=None, **kwargs):
        return mi.stage_inputs(self.image, output or self.bundle, logical_receipt=self.logical, **kwargs)

    def verify(self, **kwargs):
        return mi.verify_bundle(self.bundle, **kwargs)

    def refused(self, call):
        with self.assertRaises((ValueError, OSError)):
            call()

    def metadata_controls(self):
        """Use the real composer with inert native bytes, never apply a patch.

        Reviewed patch texts retain their real identities. The source identities
        are consistent synthetic transitions for testing source checks, not
        evidence that the patches produce these fixture files.
        """
        records = [json.loads((WORKSPACE / path).read_bytes()) for path in metadata.SOURCE_CONTRACTS]
        old_common = mi.identity((self.source / metadata.COMMON).read_bytes())
        old_core = self.source_contract["source_files"][0]["after"]
        old_add_img = mi.identity((self.source / metadata.ADD_IMG).read_bytes())
        records[0]["source_files"][0]["after"] = copy.deepcopy(mi.EXPECTED_CORE_BEFORE)
        records[1]["source_files"][0]["after"] = old_add_img
        records[2]["source_files"][0].update(before=copy.deepcopy(mi.EXPECTED_CORE_BEFORE), after=old_core)
        records[2]["composed_semantic_files"] = [
            {"path": metadata.ADD_IMG, "requires_patch": metadata.SOURCE_PATCHES[1], **old_add_img}]
        for index, record in enumerate(records):
            record["semantic_files"] = []
            for relative in metadata.SOURCE_SEMANTICS[index]:
                path = self.source / relative
                if relative == mi.CORE_PATH:
                    row = mi.EXPECTED_CORE_BEFORE
                elif relative == metadata.COMMON:
                    row = old_common
                else:
                    if not path.exists():
                        self.write(path, ("Inert metadata source fixture " + relative + "\n").encode())
                    row = mi.identity(path.read_bytes())
                record["semantic_files"].append({"path": relative, **row})
        new_common = b"Inert optional-properties native common fixture\n"
        new_core = b"Inert target-files metadata native core fixture\n"
        self.write(self.source / metadata.COMMON, new_common)
        self.write(self.source / metadata.CORE, new_core)
        records[3]["source_files"][0].update(before=old_common, after=mi.identity(new_common))
        records[4]["source_files"][0].update(before=old_core, after=mi.identity(new_core))
        refs = []
        for relative, record in zip(metadata.SOURCE_CONTRACTS, records):
            if relative == metadata.SOURCE_CONTRACT:
                record["required_predecessor_contracts"] = refs
            raw = mi.encoded(record)
            self.write(self.controls / relative, raw)
            refs.append({"path": relative, **mi.identity(raw)})
            patch = record["patch"]["path"]
            self.write(self.controls / patch, (WORKSPACE / patch).read_bytes())
        self.write(self.controls / mi.METADATA_COMPOSER_PATH,
                   (WORKSPACE / mi.METADATA_COMPOSER_PATH).read_bytes())
        self.composition = metadata.compose_sources(self.controls)
        self.selected = self.controls / mi.METADATA_SOURCE_CONTRACT_PATH
        self.source_contract = records[2]

    def metadata_binding(self):
        return mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                     expected_package_sha256=mi.EXPECTED_PACKAGE,
                                     composed_source_contract=self.selected)

    def readonly_controls(self):
        """Exercise the actual four-patch composer with inert native bytes."""
        contracts = (recovery_sources.BASE_PATH, recovery_sources.PACKAGING_PATH,
                     recovery_sources.COMPOSED_PATH, mi.READONLY_SOURCE_CONTRACT_PATH)
        records = [json.loads((WORKSPACE / path).read_bytes()) for path in contracts]
        old_core = self.source_contract["source_files"][0]["after"]
        old_add_img = mi.identity((self.source / recovery_sources.ADD_IMG_PATH).read_bytes())
        records[0]["source_files"][0]["after"] = copy.deepcopy(mi.EXPECTED_CORE_BEFORE)
        records[1]["source_files"][0]["after"] = old_add_img
        records[2]["source_files"][0].update(before=copy.deepcopy(mi.EXPECTED_CORE_BEFORE), after=old_core)
        records[2]["composed_semantic_files"] = [
            {"path": recovery_sources.ADD_IMG_PATH,
             "requires_patch": recovery_sources.PACKAGING_PATCH, **old_add_img}]
        for record in records:
            for row in record["semantic_files"]:
                if row["path"] == mi.CORE_PATH:
                    row.update(mi.EXPECTED_CORE_BEFORE)
                else:
                    path = self.source / row["path"]
                    if not path.exists():
                        self.write(path, ("Inert readonly source fixture " + row["path"] + "\n").encode())
                    row.update(mi.identity(path.read_bytes()))
        new_core = b"Inert Kati readonly initialization native core fixture\n"
        self.write(self.source / mi.CORE_PATH, new_core)
        records[-1]["source_files"][0].update(before=old_core, after=mi.identity(new_core))
        refs = []
        for relative, record in zip(contracts, records):
            if relative == mi.READONLY_SOURCE_CONTRACT_PATH:
                record["required_predecessor_contracts"] = copy.deepcopy(refs)
                _, predecessor = recovery_sources.compose(self.controls,
                                                          self.controls / recovery_sources.COMPOSED_PATH)
                record["predecessor_composition"] = predecessor
            raw = mi.encoded(record)
            self.write(self.controls / relative, raw)
            refs.append({"path": relative, **mi.identity(raw)})
            patch = record["patch"]["path"]
            self.write(self.controls / patch, (WORKSPACE / patch).read_bytes())
        for relative in mi.READONLY_COMPOSER_CONTROLS:
            self.write(self.controls / relative, (WORKSPACE / relative).read_bytes())
        self.readonly_selected = self.controls / mi.READONLY_SOURCE_CONTRACT_PATH
        source, self.readonly_identity = recovery_sources.compose(self.controls, self.readonly_selected)
        self.readonly_composition = source["composition"]
        self.source_contract = records[2]

    def readonly_binding(self):
        return mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                     expected_package_sha256=mi.EXPECTED_PACKAGE,
                                     composed_source_contract=self.readonly_selected)

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

    def test_explicit_old_composition_retains_default_receipt_and_rendering(self):
        self.stage()
        old_receipt = (self.bundle / mi.RECEIPT_NAME).read_bytes()
        selected = self.controls / mi.SOURCE_CONTRACT_PATH
        second = self.output_parent / "explicit-old"
        self.stage(second, composed_source_contract=selected)
        self.assertEqual((second / mi.RECEIPT_NAME).read_bytes(), old_receipt)
        bound = mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                     expected_package_sha256=mi.EXPECTED_PACKAGE)
        self.assertEqual(set(bound["native_source"]), {"project_commit", "files"})
        self.assertEqual(len(bound["native_source"]["files"]), 5)
        self.assertEqual(mi.render_board_include(bound),
                         mi.render_board_include(bound, composed_source_contract=selected))
        self.assertEqual(self.verify(), self.verify(composed_source_contract=selected))

    def test_metadata_composition_retains_full_patch_and_native_source_bindings(self):
        self.metadata_controls()
        staged = self.stage(composed_source_contract=self.selected)
        receipt = json.loads((self.bundle / mi.RECEIPT_NAME).read_bytes())
        bound = self.metadata_binding()
        native = bound["native_source"]
        self.assertEqual(native["composition"], self.composition)
        self.assertEqual(native["composition_identity"], mi.identity(mi.encoded(self.composition)))
        self.assertEqual(native["files"], self.composition["final_source_files"])
        self.assertEqual(len(native["files"]), 9)
        self.assertEqual([row["path"] for row in native["composition"]["ordered_patches"]],
                         list(metadata.SOURCE_PATCHES))
        self.assertEqual(receipt["required_native_source"], native)
        self.assertEqual(staged["receipt"], bound["receipt"])
        self.assertFalse(bound["scope"]["complete_rom_admitted"])
        self.assertFalse(bound["scope"]["target_files_verified"])
        self.assertEqual(bound["scope"]["phone_operations"], [])
        self.assertNotIn(str(self.root), mi.encoded(receipt).decode())
        controls = {row["path"]: mi.expected(row) for row in receipt["controls"]}
        expected_paths = {mi.CONTRACT_PATH, mi.FACTORY_RECORD_PATH,
                          "scripts/mi_ext_inputs.py", "scripts/artifact_files.py",
                          mi.METADATA_COMPOSER_PATH, *metadata.SOURCE_CONTRACTS, *metadata.SOURCE_PATCHES}
        self.assertEqual(set(controls), expected_paths)
        for path, row in controls.items():
            self.assertEqual(row, mi.identity((self.controls / path).read_bytes()))

    def test_metadata_composition_requires_every_actual_native_file(self):
        self.metadata_controls()
        self.stage(composed_source_contract=self.selected)
        verified = self.verify(source_tree=self.source, composed_source_contract=self.selected)
        self.assertTrue(verified["actual_native_source_bytes_checked"])
        self.assertFalse(verified["native_avb_run"])
        for row in self.composition["final_source_files"]:
            with self.subTest(path=row["path"]):
                path = self.source / row["path"]
                raw = path.read_bytes()
                path.write_bytes(b"different source\n")
                self.refused(lambda: self.verify(source_tree=self.source,
                                                 composed_source_contract=self.selected))
                path.unlink()
                self.refused(lambda: self.verify(source_tree=self.source,
                                                 composed_source_contract=self.selected))
                path.write_bytes(raw)

    def test_metadata_render_requires_explicit_selection_and_all_nine_guards(self):
        self.metadata_controls()
        self.stage(composed_source_contract=self.selected)
        bound = self.metadata_binding()
        generated = mi.render_board_include(bound, composed_source_contract=self.selected)
        for row in self.composition["final_source_files"]:
            self.assertIn(f"sha256sum < {row['path']} 2>/dev/null | cut -d ' ' -f 1),{row['sha256']}", generated)
        self.refused(lambda: mi.render_board_include(bound))
        self.refused(lambda: mi.render_board_include(bound,
                     composed_source_contract=self.controls / mi.SOURCE_CONTRACT_PATH))
        self.assertIn("BOARD_AVB_CUSTOMIMAGES_DIRECT_PARTITION_LIST := mi_ext", generated)
        self.assertNotIn("BOARD_NEZHA_PREBUILT_METADATA :=", generated)

    def test_metadata_receipt_is_never_implicitly_selected(self):
        self.metadata_controls()
        self.stage(composed_source_contract=self.selected)
        self.refused(self.verify)
        self.refused(lambda: mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                                  expected_package_sha256=mi.EXPECTED_PACKAGE))
        receipt = json.loads((self.bundle / mi.RECEIPT_NAME).read_bytes())
        for name in ("composition", "composition_identity"):
            receipt["required_native_source"].pop(name)
        (self.bundle / mi.RECEIPT_NAME).write_bytes(mi.encoded(receipt))
        self.refused(self.verify)
        self.refused(lambda: self.verify(composed_source_contract=self.selected))

    def test_old_receipt_and_binding_reject_new_explicit_composition(self):
        self.metadata_controls()
        self.stage()
        bound = mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                     expected_package_sha256=mi.EXPECTED_PACKAGE)
        self.refused(lambda: self.verify(composed_source_contract=self.selected))
        self.refused(self.metadata_binding)
        self.refused(lambda: mi.render_board_include(bound, composed_source_contract=self.selected))
        # Availability of a newer contract does not alter default source guards.
        self.assertEqual(len(bound["native_source"]["files"]), 5)
        self.assertNotIn("composition", bound["native_source"])
        self.refused(lambda: self.verify(source_tree=self.source))

    def test_unknown_or_changed_explicit_source_contract_is_rejected(self):
        self.metadata_controls()
        selection = self.inputs / "selected-contract.json"
        for data in (b"", b"{}", self.selected.read_bytes() + b" ",
                     mi.encoded({"contract_id": "nezha-prebuilt-target-files-metadata-v1"})):
            with self.subTest(data=data[:80]):
                selection.write_bytes(data)
                self.refused(lambda: self.stage(composed_source_contract=selection))
                self.assertFalse(self.bundle.exists())

    def test_metadata_selection_can_relocate_only_with_exact_bytes(self):
        self.metadata_controls()
        selected = self.inputs / "relocated-contract.json"
        selected.write_bytes(self.selected.read_bytes())
        self.stage(composed_source_contract=selected)
        self.assertEqual(self.verify(composed_source_contract=selected),
                         self.verify(composed_source_contract=self.selected))
        selected.write_bytes(selected.read_bytes() + b" ")
        self.refused(lambda: self.verify(composed_source_contract=selected))

    def test_metadata_selection_rejects_changed_composition_identity_and_scope(self):
        self.metadata_controls()
        self.stage(composed_source_contract=self.selected)
        binding = self.metadata_binding()
        for mutation in (
                lambda value: value["native_source"]["composition_identity"].update(sha256="0" * 64),
                lambda value: value["native_source"]["composition"]["ordered_patches"].reverse(),
                lambda value: value["native_source"]["composition"].update(whole_source_tree_verified=True),
                lambda value: value["native_source"]["files"].pop(),
                lambda value: value["scope"].update(complete_rom_admitted=True)):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(binding)
                mutation(changed)
                self.refused(lambda: mi.render_board_include(changed, composed_source_contract=self.selected))

    def test_metadata_composition_requires_all_contract_and_patch_dependencies(self):
        self.metadata_controls()
        for relative in (*metadata.SOURCE_CONTRACTS, *metadata.SOURCE_PATCHES, mi.METADATA_COMPOSER_PATH):
            with self.subTest(path=relative):
                path = self.controls / relative
                raw = path.read_bytes()
                path.unlink()
                self.refused(lambda: self.stage(composed_source_contract=self.selected))
                self.assertFalse(self.bundle.exists())
                path.write_bytes(raw)

    def test_metadata_composer_errors_use_mi_ext_admission_error(self):
        self.metadata_controls()
        patch = self.controls / metadata.SOURCE_PATCHES[-1]
        patch.write_bytes(patch.read_bytes() + b"unreviewed patch edit\n")
        with self.assertRaisesRegex(mi.MiExtInputsError, "metadata source composition refused"):
            self.stage(composed_source_contract=self.selected)
        self.assertFalse(self.bundle.exists())

    def test_metadata_composer_control_mutation_before_publication_is_rejected(self):
        self.metadata_controls()
        recheck = mi.Reader.recheck
        for relative in (*metadata.SOURCE_CONTRACTS, *metadata.SOURCE_PATCHES, mi.METADATA_COMPOSER_PATH):
            with self.subTest(path=relative):
                path = self.controls / relative
                raw = path.read_bytes()
                def change(reader):
                    path.write_bytes(raw + b"changed after composition")
                    recheck(reader)
                with mock.patch.object(mi.Reader, "recheck", change):
                    self.refused(lambda: self.stage(composed_source_contract=self.selected))
                self.assertFalse(self.bundle.exists())
                self.assertEqual(list(self.output_parent.iterdir()), [])
                path.write_bytes(raw)

    def test_composer_cannot_change_already_read_source_dependency(self):
        self.metadata_controls()
        compose = metadata.compose_sources
        path = self.controls / mi.SOURCE_CONTRACT_PATH
        def change(root):
            result = compose(root)
            path.write_bytes(path.read_bytes() + b" ")
            for row in result["contracts"]:
                if row["path"] == mi.SOURCE_CONTRACT_PATH:
                    row.update(mi.identity(path.read_bytes()))
            return result
        with mock.patch.object(metadata, "compose_sources", change):
            self.refused(lambda: self.stage(composed_source_contract=self.selected))
        self.assertFalse(self.bundle.exists())

    def test_composer_source_cannot_change_during_composition(self):
        self.metadata_controls()
        compose = metadata.compose_sources
        path = self.controls / mi.METADATA_COMPOSER_PATH
        def change(root):
            result = compose(root)
            path.write_bytes(path.read_bytes() + b"\n# changed during composition\n")
            return result
        with mock.patch.object(metadata, "compose_sources", change):
            self.refused(lambda: self.stage(composed_source_contract=self.selected))
        self.assertFalse(self.bundle.exists())
        self.assertEqual(list(self.output_parent.iterdir()), [])

    def test_cli_forwards_explicit_source_selection_without_implicit_default(self):
        arguments = ["--composed-source-contract", "controls/explicit.json"]
        with mock.patch.object(mi, "stage_inputs", return_value={}) as stage:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(mi.main(["stage", "--image", "image", "--logical-receipt", "logical",
                                          "--output", "output", *arguments]), 0)
            self.assertEqual(stage.call_args.kwargs["composed_source_contract"], Path("controls/explicit.json"))
        with mock.patch.object(mi, "verify_bundle", return_value={}) as verify:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(mi.main(["verify", "--bundle", "bundle", *arguments]), 0)
            self.assertEqual(verify.call_args.kwargs["composed_source_contract"], Path("controls/explicit.json"))
        with mock.patch.object(mi, "verify_bundle", return_value={}) as verify:
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(mi.main(["verify", "--bundle", "bundle"]), 0)
            self.assertIsNone(verify.call_args.kwargs["composed_source_contract"])

    def test_readonly_composition_binds_four_patches_eight_sources_and_runtime_controls(self):
        self.readonly_controls()
        staged = self.stage(composed_source_contract=self.readonly_selected)
        binding = self.readonly_binding()
        native = binding["native_source"]
        self.assertEqual(native["composition"], self.readonly_composition)
        self.assertEqual(native["composition_identity"], self.readonly_identity)
        self.assertEqual(native["composition_identity"], mi.identity(mi.encoded(self.readonly_composition)))
        self.assertEqual(native["files"], self.readonly_composition["final_source_files"])
        self.assertEqual(len(native["files"]), 8)
        self.assertIn("build/make/core/product.mk", [row["path"] for row in native["files"]])
        self.assertEqual(len(native["composition"]["ordered_patches"]), 4)
        self.assertEqual(len(native["composition"]["core_transitions"]), 3)
        receipt = json.loads((self.bundle / mi.RECEIPT_NAME).read_bytes())
        self.assertEqual(receipt["required_native_source"], native)
        self.assertEqual(staged["receipt"], binding["receipt"])
        paths = {row["path"] for row in receipt["controls"]}
        self.assertEqual(paths, {mi.CONTRACT_PATH, mi.FACTORY_RECORD_PATH,
                                "scripts/mi_ext_inputs.py", "scripts/artifact_files.py",
                                *mi.READONLY_COMPOSER_CONTROLS,
                                *(row["path"] for row in self.readonly_composition["contracts"]),
                                *(row["path"] for row in self.readonly_composition["ordered_patches"])})
        self.assertEqual(len(paths), 15)
        self.assertNotIn(mi.METADATA_SOURCE_CONTRACT_PATH, paths)
        self.assertNotIn(mi.METADATA_COMPOSER_PATH, paths)
        self.assertEqual(binding["scope"], mi.SCOPE)
        self.assertNotIn(str(self.root), (self.bundle / mi.RECEIPT_NAME).read_text())

    def test_readonly_composition_does_not_require_metadata_files_or_composer(self):
        self.readonly_controls()
        self.assertFalse((self.controls / mi.METADATA_SOURCE_CONTRACT_PATH).exists())
        self.assertFalse((self.controls / mi.METADATA_COMPOSER_PATH).exists())
        with mock.patch.object(metadata, "compose_sources", side_effect=AssertionError("metadata must not run")):
            self.stage(composed_source_contract=self.readonly_selected)
            self.assertEqual(self.verify(composed_source_contract=self.readonly_selected)["status"], "verified")
            binding = self.readonly_binding()
            mi.render_board_include(binding, composed_source_contract=self.readonly_selected)

    def test_readonly_composition_checks_every_actual_source_and_emits_matching_guards(self):
        self.readonly_controls()
        self.stage(composed_source_contract=self.readonly_selected)
        result = self.verify(source_tree=self.source, composed_source_contract=self.readonly_selected)
        self.assertTrue(result["actual_native_source_bytes_checked"])
        self.assertFalse(result["native_avb_run"])
        generated = mi.render_board_include(self.readonly_binding(),
                                           composed_source_contract=self.readonly_selected)
        for row in self.readonly_composition["final_source_files"]:
            with self.subTest(path=row["path"]):
                self.assertIn(f"sha256sum < {row['path']} 2>/dev/null | cut -d ' ' -f 1),{row['sha256']}", generated)
                path = self.source / row["path"]
                raw = path.read_bytes()
                path.write_bytes(b"unreviewed native source\n")
                self.refused(lambda: self.verify(source_tree=self.source,
                                                 composed_source_contract=self.readonly_selected))
                path.unlink()
                self.refused(lambda: self.verify(source_tree=self.source,
                                                 composed_source_contract=self.readonly_selected))
                path.write_bytes(raw)
        self.assertNotIn("BOARD_MI_EXT_IMAGE_NO_FLASHALL :=", generated)
        self.assertNotIn("BOARD_NEZHA_PREBUILT_METADATA :=", generated)

    def test_readonly_receipt_and_binding_never_select_the_new_mode_implicitly(self):
        self.readonly_controls()
        self.stage(composed_source_contract=self.readonly_selected)
        self.refused(self.verify)
        self.refused(lambda: mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                                  expected_package_sha256=mi.EXPECTED_PACKAGE))
        binding = self.readonly_binding()
        self.refused(lambda: mi.render_board_include(binding))
        self.refused(lambda: mi.render_board_include(binding,
                      composed_source_contract=self.controls / mi.SOURCE_CONTRACT_PATH))

    def test_old_receipt_and_binding_cannot_upgrade_to_readonly_composition(self):
        self.readonly_controls()
        self.stage()
        self.refused(lambda: self.verify(composed_source_contract=self.readonly_selected))
        self.refused(self.readonly_binding)
        binding = mi.validate_admission(self.bundle / mi.RECEIPT_NAME,
                                       expected_package_sha256=mi.EXPECTED_PACKAGE)
        self.refused(lambda: mi.render_board_include(binding,
                                                     composed_source_contract=self.readonly_selected))
        self.assertEqual(len(binding["native_source"]["files"]), 5)

    def test_readonly_selection_rejects_altered_contract_and_relocated_exact_copy_works(self):
        self.readonly_controls()
        selection = self.inputs / "readonly.json"
        original = self.readonly_selected.read_bytes()
        selection.write_bytes(original)
        self.stage(composed_source_contract=selection)
        self.assertEqual(self.verify(composed_source_contract=selection),
                         self.verify(composed_source_contract=self.readonly_selected))
        mutated = json.loads(original)
        mutated["source_files"][0]["after"]["sha256"] = "0" * 64
        for raw in (original + b" ", mi.encoded(mutated), b"{}"):
            selection.write_bytes(raw)
            self.refused(lambda: self.verify(composed_source_contract=selection))

    def test_readonly_composition_identity_and_source_bindings_cannot_be_resealed(self):
        self.readonly_controls()
        self.stage(composed_source_contract=self.readonly_selected)
        original = self.readonly_binding()
        for mutation in (
                lambda value: value["native_source"]["composition_identity"].update(sha256="0" * 64),
                lambda value: value["native_source"]["composition"]["core_transitions"].pop(),
                lambda value: value["native_source"]["composition"].update(whole_source_tree_verified=True),
                lambda value: value["native_source"]["files"].pop(),
                lambda value: value["scope"].update(complete_rom_admitted=True)):
            with self.subTest(mutation=mutation):
                binding = copy.deepcopy(original)
                mutation(binding)
                self.refused(lambda: mi.render_board_include(binding,
                                                             composed_source_contract=self.readonly_selected))

    def test_readonly_composer_result_requires_its_matching_canonical_identity(self):
        self.readonly_controls()
        compose = recovery_sources.compose
        def wrong_identity(*args, **kwargs):
            source, digest = compose(*args, **kwargs)
            digest = {**digest, "sha256": "0" * 64}
            return source, digest
        with mock.patch.object(recovery_sources, "compose", side_effect=wrong_identity):
            with self.assertRaisesRegex(mi.MiExtInputsError, "composition identity differs"):
                self.stage(composed_source_contract=self.readonly_selected)
        self.assertFalse(self.bundle.exists())

    def test_readonly_mode_rechecks_every_composer_dependency_before_publication(self):
        self.readonly_controls()
        recheck = mi.Reader.recheck
        paths = [*mi.READONLY_COMPOSER_CONTROLS,
                 *(row["path"] for row in self.readonly_composition["contracts"]),
                 *(row["path"] for row in self.readonly_composition["ordered_patches"])]
        for relative in paths:
            with self.subTest(path=relative):
                path = self.controls / relative
                original = path.read_bytes()
                def change(reader):
                    path.write_bytes(original + b"\nchanged during staging\n")
                    recheck(reader)
                with mock.patch.object(mi.Reader, "recheck", change):
                    self.refused(lambda: self.stage(composed_source_contract=self.readonly_selected))
                self.assertFalse(self.bundle.exists())
                self.assertEqual(list(self.output_parent.iterdir()), [])
                path.write_bytes(original)

    def test_readonly_composer_runtime_dependencies_are_bound_before_invocation(self):
        self.readonly_controls()
        compose = recovery_sources.compose
        for relative in mi.READONLY_COMPOSER_CONTROLS:
            with self.subTest(path=relative):
                path = self.controls / relative
                original = path.read_bytes()
                def change(*args, **kwargs):
                    result = compose(*args, **kwargs)
                    path.write_bytes(original + b"\n# changed during composition\n")
                    return result
                with mock.patch.object(recovery_sources, "compose", side_effect=change):
                    self.refused(lambda: self.stage(composed_source_contract=self.readonly_selected))
                self.assertFalse(self.bundle.exists())
                self.assertEqual(list(self.output_parent.iterdir()), [])
                path.write_bytes(original)

    def test_readonly_composer_declared_errors_preserve_mi_ext_admission_contract(self):
        self.readonly_controls()
        from scripts.firmware import IntakeError
        from scripts.kernel_inputs import KernelInputsError
        for error in (recovery_sources.RecoverySourceError, KernelInputsError, IntakeError):
            with self.subTest(error=error.__name__):
                cause = error("inert malformed dependency")
                with mock.patch.object(recovery_sources, "compose", side_effect=cause):
                    with self.assertRaisesRegex(mi.MiExtInputsError, "readonly source composition refused") as raised:
                        self.stage(composed_source_contract=self.readonly_selected)
                self.assertIs(raised.exception.__cause__, cause)
                self.assertFalse(self.bundle.exists())

    def test_metadata_and_readonly_receipts_and_bindings_are_not_interchangeable(self):
        # Keep both reviewed compositions available at once. Only the explicitly
        # selected path may influence the receipt, native source set or rendering.
        self.readonly_controls()
        readonly_files = {path: path.read_bytes() for path in self.controls.rglob("*") if path.is_file()}
        self.stage(composed_source_contract=self.readonly_selected)
        readonly_binding = self.readonly_binding()
        readonly_bundle = self.bundle
        # Metadata fixture generation consumes the original fixture native core.
        old_core = b"Inert composed native core fixture\n"
        self.write(self.source / mi.CORE_PATH, old_core)
        self.metadata_controls()
        # Preserve the exact legacy predecessor controls of the readonly receipt.
        for path, raw in readonly_files.items():
            if path not in {self.controls / row["path"] for row in self.readonly_composition["contracts"][:3]}:
                self.write(path, raw)
        self.bundle = self.output_parent / "metadata"
        self.stage(composed_source_contract=self.selected)
        metadata_binding = self.metadata_binding()
        self.refused(lambda: mi.verify_bundle(readonly_bundle, composed_source_contract=self.selected))
        self.refused(lambda: mi.verify_bundle(self.bundle, composed_source_contract=self.readonly_selected))
        self.refused(lambda: mi.render_board_include(readonly_binding, composed_source_contract=self.selected))
        self.refused(lambda: mi.render_board_include(metadata_binding,
                                                     composed_source_contract=self.readonly_selected))


if __name__ == "__main__":
    unittest.main()
