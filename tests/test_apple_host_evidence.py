"""Check sanitized host-tool evidence without invoking a VM or compiler."""

import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class AppleHostEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/apple-host-tools.json").read_text())

    def test_tool_projects_match_completed_source_snapshot(self):
        data = (ROOT / self.record["source_snapshot"]).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.record["source_snapshot_sha256"])
        projects = {node.get("path", node.get("name")): node.get("revision")
                    for node in ET.fromstring(data).findall("project")}
        for path, head in self.record["project_heads"].items():
            self.assertEqual(projects[path], head)

    def test_every_recorded_check_succeeded_without_claiming_platform_build(self):
        self.assertEqual(len(self.record["tests"]), 13)
        for test in self.record["tests"]:
            self.assertTrue(test["passed"])
            self.assertEqual(test["exit_code"], 0)
        for flag in ("all_tests_passed", "input_hashes_unchanged"):
            self.assertTrue(self.record[flag])
        for flag in ("full_android_build_verified", "android_module_built",
                     "android_bionic_link_or_runtime_tested", "phone_modified"):
            self.assertFalse(self.record[flag])

    def test_inputs_and_outputs_have_hashes_and_distinct_target_architectures(self):
        for artifact in self.record["inputs"] + self.record["outputs"]:
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(artifact["bytes"], 0)
            path = PurePosixPath(artifact.get("source_path", artifact.get("path")))
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
        inputs = {item["source_path"]: item for item in self.record["inputs"]}
        for name, artifact in inputs.items():
            if name.endswith(("/bin/clang", "/bin/ld.lld", "/bin/ninja", "/bin/java", "/bin/javac", "/bin/go")):
                self.assertEqual(artifact["elf_machine"], 62)
        outputs = {item["path"]: item for item in self.record["outputs"]}
        self.assertEqual(outputs["android-arm64.o"]["elf_machine"], 183)
        self.assertEqual(outputs["probe"]["elf_machine"], 62)
        self.assertEqual(outputs["hello-go"]["elf_machine"], 62)
        self.assertTrue(self.record["private_receipt"]["host_path"].startswith("reports/"))


class SoongBootstrapEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/soong-bootstrap.json").read_text())
        cls.snapshot = (ROOT / cls.record["source_snapshot"]).read_bytes()
        cls.projects = {
            node.get("path", node.get("name")): node.get("revision")
            for node in ET.fromstring(cls.snapshot).findall("project")
        }

    def test_bootstrap_projects_match_the_resolved_source_snapshot(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(hashlib.sha256(self.snapshot).hexdigest(),
                         self.record["source_snapshot_sha256"])
        self.assertEqual(set(self.record["project_heads"]), {
            "build/soong", "build/blueprint", "build/make",
            "prebuilts/build-tools", "prebuilts/go/linux-x86",
        })
        for path, head in self.record["project_heads"].items():
            with self.subTest(project=path):
                self.assertRegex(head, r"^[0-9a-f]{40}$")
                self.assertEqual(self.projects[path], head)

    def test_success_is_the_exact_out_dir_query_without_a_timeout(self):
        self.assertEqual(self.record["command"], [
            "build/soong/soong_ui.bash", "--dumpvar-mode", "OUT_DIR",
        ])
        out_dir = PurePosixPath(self.record["out_dir"])
        self.assertEqual(out_dir.parent, PurePosixPath("/work/out"))
        self.assertTrue(out_dir.name.startswith("soong-bootstrap-"))
        self.assertEqual(self.record["stdout"], str(out_dir) + "\n")
        self.assertEqual(self.record["stderr"], "")
        self.assertEqual(self.record["exit_code"], 0)
        self.assertFalse(self.record["timed_out"])
        self.assertTrue(self.record["passed"])
        self.assertLess(datetime.fromisoformat(self.record["started_at"]),
                        datetime.fromisoformat(self.record["completed_at"]))

    def test_existing_translated_uname_does_not_change_native_architecture(self):
        self.assertEqual(self.record["native_arch"], "aarch64")
        self.assertEqual(self.record["translated_uname_arch"], "x86_64")
        self.assertEqual(self.record["path_prefix"],
                         "/work/evolution/prebuilts/build-tools/path/linux-x86")
        self.assertEqual(self.record["uname_symlink_target"],
                         "../../linux-x86/bin/toybox")
        self.assertNotIn("prebuilts/go/linux-arm64", self.projects)

    def test_five_preserved_inputs_and_four_compiled_outputs_are_hashed(self):
        self.assertEqual(set(self.record["input_sha256"]), {
            "build/soong/soong_ui.bash",
            "build/soong/scripts/microfactory.bash",
            "build/blueprint/microfactory/microfactory.bash",
            "prebuilts/build-tools/linux-x86/bin/toybox",
            "prebuilts/go/linux-x86/bin/go",
        })
        for name, digest in self.record["input_sha256"].items():
            with self.subTest(input=name):
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
                self.assertFalse(PurePosixPath(name).is_absolute())
                self.assertNotIn("..", PurePosixPath(name).parts)
        self.assertEqual(len(self.record["outputs"]), 4)
        self.assertEqual({item["name"] for item in self.record["outputs"]},
                         {"soong_ui", "mk2rbc", "rbcrun", "release-config"})
        for artifact in self.record["outputs"]:
            with self.subTest(output=artifact["name"]):
                self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(artifact["size"], 0)
                self.assertEqual(artifact["elf_machine"], 62)
        self.assertTrue(self.record["input_hashes_unchanged"])
        self.assertTrue(self.record["source_unchanged"])

    def test_bootstrap_does_not_claim_product_sandbox_or_device_validation(self):
        self.assertEqual(self.record["checks_disabled_by_this_probe"], [])
        for flag in ("module_or_rom_build_attempted",
                     "kati_product_configuration_tested", "ninja_sandbox_tested",
                     "full_android_build_verified", "phone_accessed"):
            with self.subTest(flag=flag):
                self.assertFalse(self.record[flag])
        self.assertTrue(self.record["limits"])

    def test_later_audit_covers_all_projects_and_preserves_receipt_references(self):
        audit = self.record["post_bootstrap_source_audit"]
        for field in ("project_count", "head_match_count", "clean_project_count",
                      "origin_match_count"):
            self.assertEqual(audit[field], len(self.projects))
        self.assertTrue(audit["manifest_and_repo_pins_verified_before_and_after"])
        self.assertTrue(audit["project_list_matches_manifest"])
        self.assertEqual(audit["failure_count"], 0)
        self.assertLess(datetime.fromisoformat(self.record["completed_at"]),
                        datetime.fromisoformat(audit["completed_at"]))
        for receipt in (self.record["private_receipt"], audit):
            with self.subTest(receipt=receipt["host_path"]):
                self.assertRegex(receipt["sha256"], r"^[0-9a-f]{64}$")
                host_path = PurePosixPath(receipt["host_path"])
                self.assertFalse(host_path.is_absolute())
                self.assertNotIn("..", host_path.parts)
                self.assertEqual(host_path.parent,
                                 PurePosixPath("reports/source-sync-20260827"))
                self.assertTrue(receipt["guest_path"].startswith("/work/validation/"))
                self.assertEqual(PurePosixPath(receipt["guest_path"]).name, "receipt.json")
        self.assertNotEqual(self.record["private_receipt"]["host_path"], audit["host_path"])

    def test_host_guides_link_the_bootstrap_evidence(self):
        for name in ("apple-container.md", "build-host.md"):
            with self.subTest(guide=name):
                guide = (ROOT / "docs" / name).read_text()
                self.assertIn("../research/soong-bootstrap.json", guide)


if __name__ == "__main__":
    unittest.main()
