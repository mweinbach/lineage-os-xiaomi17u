"""Check public sandbox evidence without invoking a VM or requiring private logs."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AppleSandboxRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "research/apple-sandbox.json").read_text())

    def test_snapshot_and_pinned_tools_match_recorded_inputs(self):
        record = self.record
        self.assertEqual(hashlib.sha256((ROOT / record["source_snapshot"]).read_bytes()).hexdigest(),
                         record["source_snapshot_sha256"])
        bootstrap = json.loads((ROOT / "research/soong-bootstrap.json").read_text())
        self.assertEqual(record["soong_commit"], bootstrap["project_heads"]["build/soong"])
        self.assertEqual(record["build_tools_commit"], bootstrap["project_heads"]["prebuilts/build-tools"])
        for item in record["input_files"]:
            self.assertEqual(item["elf_machine"], 62)
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_checks_distinguish_standalone_execution_from_product_build(self):
        record = self.record
        for key in ("passed", "source_write_refused_with_erofs", "ninja_and_clang_executed_inside_jail",
                    "host_program_executed_inside_jail"):
            self.assertIs(record[key], True)
        self.assertEqual(record["network_interfaces_inside_jail"], ["lo"])
        self.assertEqual(record["uid_inside_jail"], 65534)
        self.assertEqual(record["global_uid_mapping"], 0)
        self.assertEqual(record["checks_disabled_by_this_probe"], [])
        self.assertFalse(record["android_module_build_verified"])
        self.assertFalse(record["full_rom_build_verified"])
        self.assertFalse(record["phone_accessed"])
        self.assertEqual([item["elf_machine"] for item in record["outputs"]], [62, 183])
        self.assertIn("--disable_clone_newcgroup", record["cgroup_namespace"])
        self.assertTrue(any("fallback" in item for item in record["limits"]))


if __name__ == "__main__":
    unittest.main()
