"""Offline consistency checks for the admitted development product."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildProgressTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "research/build-progress.json").read_text())

    def test_development_target_is_separate_from_complete_rom_admission(self):
        device = json.loads((ROOT / "config/sources.json").read_text())["device"]
        self.assertFalse(device["build_ready"])
        self.assertIsNone(device["lunch_target"])
        target = device["development_target"]
        self.assertEqual(target["lunch_target"], self.record["lunch_target"])
        self.assertEqual(target["profile"], "framework-checks")
        self.assertTrue(target["configuration_verified"])
        self.assertFalse(self.record["full_rom_verified"])
        self.assertFalse(self.record["device_boot_verified"])
        self.assertFalse(self.record["phone_modifications_performed"])
        products = (ROOT / "device/xiaomi/nezha/AndroidProducts.mk").read_text()
        self.assertIn(target["lunch_target"], products)

    def test_configuration_result_binds_nezha_and_enabled_avb(self):
        result = self.record["product_configuration"]
        self.assertEqual(result["exit_code"], 0)
        expected = {"TARGET_PRODUCT": "lineage_nezha", "TARGET_DEVICE": "nezha",
                    "TARGET_ARCH": "arm64", "TARGET_BOARD_PLATFORM": "canoe",
                    "BOARD_KERNEL_PAGESIZE": "4096", "BOARD_AVB_ENABLE": "true",
                    "PRODUCT_SHIPPING_API_LEVEL": "36", "BOARD_SHIPPING_API_LEVEL": "202504"}
        for key, value in expected.items():
            self.assertEqual(result["values"][key], value)
        self.assertEqual(result["disabled_checks"], [])
        self.assertRegex(result["sha256"], r"^[a-f0-9]{64}$")

    def test_base_snapshot_and_property_adjustment_are_bound(self):
        record = self.record
        snapshot = ROOT / record["base_source_snapshot"]
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), record["base_source_snapshot_sha256"])
        adjustment = record["source_adjustments"][0]
        self.assertEqual(hashlib.sha256((ROOT / adjustment["patch"]).read_bytes()).hexdigest(), adjustment["patch_sha256"])
        self.assertEqual(adjustment["project"], "vendor/lineage")
        self.assertEqual(record["kernel_bundle"]["module_instances"], 914)
        self.assertGreaterEqual(record["kernel_bundle"]["file_count"], record["kernel_bundle"]["module_instances"])

    def test_current_admission_is_bound_to_installed_source_updates(self):
        record = self.record
        updates = record["installation"]["device_source_updates"]
        versions = [item["version"] for item in updates]
        self.assertEqual(versions, list(range(2, versions[-1] + 1)))
        self.assertEqual(updates[-1]["admission_sha256"], record["device_admission"]["sha256"])
        for update in updates:
            self.assertRegex(update["sha256"], r"^[a-f0-9]{64}$")
            self.assertTrue(update["changes"])
            for change in update["changes"]:
                self.assertTrue(change["path"].startswith("device/xiaomi/nezha/"))
                self.assertNotEqual(change["before_sha256"], change["after_sha256"])

    def test_relative_output_alias_preserves_physical_output_and_checks(self):
        module = self.record["module_build"]
        alias = module["output_alias"]
        self.assertEqual(module["out_dir"], alias["lexical_out_dir"])
        self.assertEqual(module["physical_out_dir"], alias["physical_out_dir"])
        self.assertTrue(module["out_dir"].startswith("out-"))
        self.assertNotIn("/", module["out_dir"])
        self.assertTrue(alias["same_inode"])
        self.assertTrue(alias["output_markers_preserved"])
        self.assertFalse(alias["source_modified"])
        self.assertEqual(alias["disabled_checks"], [])
        docs = (ROOT / "docs/build-progress.md").read_text()
        self.assertIn("OUT_DIR=" + module["out_dir"] + " \\", docs)
        for attempt in module["attempts"]:
            if attempt["result"] == "running":
                continue
            self.assertRegex(attempt["sha256"], r"^[a-f0-9]{64}$")
            self.assertIn("exit_code", attempt)
            self.assertIn("completed_at", attempt)

    def test_android_output_is_distinct_from_host_tool_and_rom(self):
        record = self.record
        self.assertTrue(record["android_modules_verified"])
        self.assertEqual(record["module_build"]["state"], "passed")
        successful = record["module_build"]["attempts"][-1]
        self.assertEqual(successful["exit_code"], 0)
        self.assertTrue(successful["passed"])
        self.assertFalse(successful["sandbox_fallback_observed"])
        proof = record["module_build"]["output_verification"]
        outputs = {row["path"]: row for row in proof["outputs"]}
        self.assertEqual(outputs["target/product/nezha/system/lib64/libbase.so"]["elf_machine"], 183)
        self.assertEqual(outputs["host/linux-x86/bin/checkvintf"]["elf_machine"], 62)
        for output in outputs.values():
            self.assertEqual(output["elf_class"], 64)
            self.assertRegex(output["sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(proof["android_binary_executed"])
        self.assertFalse(record["full_rom_verified"])
        self.assertFalse(record["device_boot_verified"])

    def test_product_sandbox_observation_is_not_the_standalone_readonly_claim(self):
        sandbox = self.record["module_build"]["sandbox_observation"]
        self.assertTrue(sandbox["ninja_ran_under_nsjail"])
        self.assertTrue(all(sandbox["namespace_separation"].values()))
        self.assertFalse(sandbox["source_read_only"])
        self.assertTrue(sandbox["output_read_write"])
        self.assertEqual(sandbox["checks_disabled_by_this_probe"], [])
        camera = self.record["camera_build"]
        self.assertTrue(camera["ninja_read_only_source_required"])
        self.assertTrue(camera["strict_elf_checks_required"])
        self.assertFalse(camera["camera_function_verified"])
        self.assertEqual(camera["input_admission_sha256"], self.record["device_admission"]["sha256"])
        self.assertEqual(len(camera["targets"]), 9)

    def test_camera_source_mount_is_observed_not_just_requested(self):
        sandbox = self.record["camera_build"]["sandbox_observation"]
        self.assertRegex(sandbox["sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(sandbox["ninja_ran_under_nsjail"])
        self.assertEqual(set(sandbox["namespace_separation"]), {"mnt", "net", "pid", "user"})
        self.assertTrue(all(sandbox["namespace_separation"].values()))
        self.assertTrue(sandbox["source_read_only"])
        self.assertTrue(sandbox["output_read_write"])
        self.assertEqual(sandbox["checks_disabled_by_this_probe"], [])
        self.assertFalse(self.record["camera_build"]["camera_function_verified"])


if __name__ == "__main__":
    unittest.main()
