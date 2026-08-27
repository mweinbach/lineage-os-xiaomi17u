"""Check sanitized host-tool evidence without invoking a VM or compiler."""

import hashlib
import json
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


if __name__ == "__main__":
    unittest.main()
