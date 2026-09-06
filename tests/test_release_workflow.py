"""Offline checks for the release plan/check helper; nothing is dispatched."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import release_workflow as workflow

BUILD = "nezha." + "0123456789abcdef01234567"
SET = "example-set-20260906-v1"


class ReleasePlanTests(unittest.TestCase):
    def test_plan_substitutes_identity_and_never_dispatches(self):
        result = workflow.plan(BUILD, SET)
        self.assertFalse(result["dispatches"])
        self.assertEqual(result["phone_operations"], [])
        self.assertEqual([stage["order"] for stage in result["stages"]], list(range(1, len(workflow.STAGES) + 1)))
        self.assertEqual([stage["id"] for stage in result["stages"]][:3], ["source", "candidate", "native"])
        signing = next(stage for stage in result["stages"] if stage["id"] == "signing")
        self.assertIn(f"artifacts/avb/nezha/{SET}/stage-logs/04-sign.exit.json", signing["receipts"])
        self.assertTrue(all("{set}" not in text and "{build}" not in text
                            for stage in result["stages"] for text in stage["commands"] + stage["receipts"]))

    def test_identities_are_validated(self):
        for build, artifact_set in ((BUILD[:-1], SET), ("nezha.XYZ", SET), (BUILD, "Bad Set"), ("", "")):
            with self.subTest(build=build, artifact_set=artifact_set):
                with self.assertRaises(workflow.ReleaseWorkflowError):
                    workflow.plan(build, artifact_set)
        self.assertEqual(workflow.main(["plan", "--build-number", "nope", "--artifact-set", SET]), 2)


class ReleaseCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.write("reports/run/source-installed.json", {"build_number": BUILD, "transaction": "/work/t",
                                                          "source_inventory": [{"path": "/work/x"}] * 3})
        self.write(f"artifacts/device-candidates/{SET}/admission.json", {"variant": "user"})
        for stage in workflow.SIGNING_STAGES:
            self.write(f"artifacts/avb/nezha/{SET}/stage-logs/{stage}.exit.json", {"returncode": 0})
        self.write(f"artifacts/avb/nezha/{SET}/published-inventory.json", {"status": "complete"})
        self.write("artifacts/build-validation/example-super-transfer-v1/transfer.json", {"verified": True})
        self.write(f"artifacts/flash/nezha/{SET}/manifest.json", {"images": [{}] * 8, "status": "verified",
                                                                   "flash_ready": False})
        (self.root / f"artifacts/flash/nezha/{SET}/SHA256SUMS").write_text("x  super.img\n")
        # A large payload sits beside the manifest; the checker must never open it.
        with (self.root / f"artifacts/flash/nezha/{SET}/super.img").open("wb") as stream:
            stream.truncate(64 * 1024 * 1024)

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def test_complete_receipts_pass_without_opening_images_or_processes(self):
        original = Path.read_bytes
        opened = []

        def read_bytes(path):
            opened.append(path.name)
            return original(path)

        with mock.patch.object(Path, "read_bytes", read_bytes), \
                mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")):
            result = workflow.check(BUILD, SET, self.root)
        self.assertTrue(result["all_host_receipts_present"])
        self.assertNotIn("super.img", opened)
        self.assertEqual(result["stages"]["signing"], "complete")
        self.assertEqual(result["details"]["source_records"][0]["source_files"], 3)
        self.assertEqual(result["details"]["bundle"]["payload_count"], 8)
        self.assertIs(result["details"]["bundle"]["flash_ready"], False)
        self.assertEqual(workflow.main(["check", "--build-number", BUILD, "--artifact-set", SET,
                                        "--root", str(self.root)]), 0)

    def test_failed_stage_and_wrong_identity_are_reported(self):
        self.write(f"artifacts/avb/nezha/{SET}/stage-logs/04-sign.exit.json", {"returncode": 1})
        result = workflow.check(BUILD, SET, self.root)
        self.assertEqual(result["details"]["signing"]["04-sign"], "failed:1")
        self.assertEqual(result["stages"]["signing"], "incomplete")
        self.assertFalse(result["all_host_receipts_present"])
        other = "nezha." + "f" * 24
        result = workflow.check(other, SET, self.root)
        self.assertEqual(result["stages"]["source"], "missing")
        self.write(f"artifacts/flash/nezha/{SET}/manifest.json", {"images": [], "build_number": other})
        result = workflow.check(BUILD, SET, self.root)
        self.assertEqual(result["stages"]["bundle"], f"identity-mismatch:{other}")
        self.assertEqual(workflow.main(["check", "--build-number", BUILD, "--artifact-set", SET,
                                        "--root", str(self.root)]), 1)

    def test_symlinked_receipt_is_refused(self):
        target = self.root / f"artifacts/avb/nezha/{SET}/stage-logs/01-inventory.exit.json"
        os.remove(target)
        os.symlink(self.root / "reports/run/source-installed.json", target)
        with self.assertRaisesRegex(workflow.ReleaseWorkflowError, "symlink"):
            workflow.check(BUILD, SET, self.root)


if __name__ == "__main__":
    unittest.main()
