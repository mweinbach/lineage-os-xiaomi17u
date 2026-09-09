"""Offline checks for the release plan/check helper; nothing is dispatched."""

import hashlib
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
        self.write("artifacts/build-validation/example-super-transfer-v1/transfer.json",
                   {"verified": True, "build_number": BUILD, "file": {"sha256": "a" * 64, "size_bytes": 9}})
        self.write(f"artifacts/flash/nezha/{SET}/manifest.json", {"images": [{}] * 8, "status": "verified",
                                                                   "flash_ready": False,
                                                                   "super": {"sha256": "a" * 64, "size_bytes": 9}})
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


class LiveLayoutCheckTests(unittest.TestCase):
    """The per-set delivery layout the userdebug sets use: nested source revision,
    package admission, set transfer with a Super entry, host workflow status and a
    reviewed delivery plan bound to the bundle manifest by hash."""

    LIVE_SET = "variant-opt-in-example-20260909-v2"

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.archive_sha = "1" * 64
        self.super_sha = "2" * 64
        self.write("reports/topic-20260909/source-revision-12/source-installed.json",
                   {"build_number": BUILD, "transaction": "/work/validation/t", "source_inventory": [{"path": "/w"}] * 5})
        self.write(f"artifacts/build-validation/{self.LIVE_SET}-admit/admission.json",
                   {"operation": "admit-variant-opt-in-userdebug-package-v2", "build_number": BUILD,
                    "archive": {"sha256": self.archive_sha, "size_bytes": 11}, "phone_accessed": False,
                    "complete_rom_ready": False})
        self.write(f"artifacts/build-validation/{self.LIVE_SET}-transfer/transfer.json",
                   {"operation": "transfer-variant-opt-in-userdebug-v2", "verified": True,
                    "archive": {"sha256": self.archive_sha, "size_bytes": 11},
                    "super": {"sha256": self.super_sha, "size_bytes": 9475836016}})
        for stage in workflow.SIGNING_STAGES:
            self.write(f"artifacts/avb/nezha/{self.LIVE_SET}/stage-logs/{stage}.exit.json", {"returncode": 0})
        self.write(f"artifacts/avb/nezha/{self.LIVE_SET}/published-inventory.json", {"status": "complete"})
        self.write("reports/topic-20260909/v2-host-workflow-status.json",
                   {"delivery_set": "v2", "build_number": BUILD, "phone_accessed": False, "flash_authorized": False,
                    "completed": ["admit-package", "signing-workflow", "bundle-workflow"],
                    "stage": "host-delivery-complete-no-phone-action", "passed": True})
        self.plan_path = self.write("reports/delivery-20260906/v2-delivery-plan.json",
                                    {"schema_version": 1, "build_number": BUILD, "artifact_set_id": self.LIVE_SET,
                                     "super": {"sha256": self.super_sha}})
        self.plan_sha = hashlib.sha256(self.plan_path.read_bytes()).hexdigest()
        self.write(f"artifacts/flash/nezha/{self.LIVE_SET}/manifest.json",
                   {"schema_version": 1, "status": "byte-identities-verified-not-device-admitted-not-flash-ready",
                    "flash_ready": False, "reviewed_plan_sha256": self.plan_sha,
                    "images": [{"role": "boot", "sha256": "3" * 64}, {"role": "super", "sha256": self.super_sha}]})
        (self.root / f"artifacts/flash/nezha/{self.LIVE_SET}/SHA256SUMS").write_text("x  super.img\n")

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def test_live_layout_receipts_are_recognized_and_bound_by_hash(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")):
            result = workflow.check(BUILD, self.LIVE_SET, self.root)
        self.assertEqual(result["stages"], {
            "source": "complete", "candidate": "in-guest-not-checked-on-host", "native": "admitted",
            "transfer": "verified", "signing": "complete", "super": "receipts-found",
            "qualification": "host-workflow:passed", "bundle": "complete"})
        self.assertTrue(result["all_host_receipts_present"])
        details = result["details"]
        self.assertEqual(details["source_records"][0]["source_files"], 5)
        self.assertTrue(details["transfer"]["archive_matches_admission"])
        self.assertEqual(details["super_receipts"][0]["kind"], "set-transfer")
        self.assertEqual(details["bundle"]["identity_source"], "reviewed-plan")
        self.assertEqual(details["bundle"]["build_number"], BUILD)
        self.assertEqual(details["bundle"]["reviewed_plan"]["path"], "reports/delivery-20260906/v2-delivery-plan.json")
        self.assertEqual(details["qualification"][0]["kind"], "host-workflow")
        self.write(f"artifacts/device-candidates/{self.LIVE_SET}/admission.json", {"variant": "userdebug"})
        result = workflow.check(BUILD, self.LIVE_SET, self.root)
        self.assertEqual(result["stages"]["candidate"], "complete")
        os.remove(self.root / f"artifacts/build-validation/{self.LIVE_SET}-admit/admission.json")
        os.remove(self.root / f"artifacts/device-candidates/{self.LIVE_SET}/admission.json")
        result = workflow.check(BUILD, self.LIVE_SET, self.root)
        self.assertEqual((result["stages"]["candidate"], result["stages"]["native"]),
                         ("missing", "not-checked-on-host"))
        self.assertFalse(result["all_host_receipts_present"])

    def test_mismatches_between_live_receipts_are_reported(self):
        cases = {
            "identity-mismatch:" + "nezha." + "e" * 24: lambda: self.write(
                f"artifacts/build-validation/{self.LIVE_SET}-admit/admission.json",
                {"operation": "admit-x", "build_number": "nezha." + "e" * 24, "archive": {"sha256": self.archive_sha},
                 "phone_accessed": False, "complete_rom_ready": False}),
            "admission-overclaims": lambda: self.write(
                f"artifacts/build-validation/{self.LIVE_SET}-admit/admission.json",
                {"operation": "admit-x", "build_number": BUILD, "archive": {"sha256": self.archive_sha},
                 "phone_accessed": True, "complete_rom_ready": False}),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected=expected):
                mutate()
                self.assertEqual(workflow.check(BUILD, self.LIVE_SET, self.root)["stages"]["native"], expected)
        self.write(f"artifacts/build-validation/{self.LIVE_SET}-transfer/transfer.json",
                   {"verified": True, "archive": {"sha256": "9" * 64}, "super": {"sha256": self.super_sha}})
        result = workflow.check(BUILD, self.LIVE_SET, self.root)
        self.assertEqual(result["stages"]["transfer"], "unverified")
        self.assertFalse(result["all_host_receipts_present"])
        self.write(f"artifacts/build-validation/{self.LIVE_SET}-transfer/transfer.json",
                   {"verified": True, "archive": {"sha256": self.archive_sha}, "super": {"sha256": "8" * 64}})
        self.assertEqual(workflow.check(BUILD, self.LIVE_SET, self.root)["stages"]["super"], "bundle-mismatch")
        self.write("reports/topic-20260909/v2-host-workflow-status.json", {"build_number": BUILD, "passed": False})
        self.assertEqual(workflow.check(BUILD, self.LIVE_SET, self.root)["stages"]["qualification"],
                         "host-workflow:failed")
        self.plan_path.write_text(json.dumps({"build_number": BUILD, "artifact_set_id": "other-set-v1"}))
        manifest = self.root / f"artifacts/flash/nezha/{self.LIVE_SET}/manifest.json"
        document = json.loads(manifest.read_text())
        document["reviewed_plan_sha256"] = hashlib.sha256(self.plan_path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(document))
        self.assertEqual(workflow.check(BUILD, self.LIVE_SET, self.root)["stages"]["bundle"], "set-mismatch:other-set-v1")
        document["reviewed_plan_sha256"] = "0" * 64
        manifest.write_text(json.dumps(document))
        result = workflow.check(BUILD, self.LIVE_SET, self.root)
        self.assertIsNone(result["details"]["bundle"]["build_number"])
        self.assertEqual(result["stages"]["bundle"], "complete")

    def test_scans_skip_symlinks_and_oversized_files_but_fixed_receipts_stay_strict(self):
        link = self.root / "reports/topic-20260909/linked-delivery-plan.json"
        os.symlink(self.plan_path, link)
        big = self.root / "reports/topic-20260909/big-delivery-plan.json"
        with big.open("wb") as stream:
            stream.truncate(workflow.MAX_RECEIPT_BYTES + 1)
        result = workflow.check(BUILD, self.LIVE_SET, self.root)
        self.assertEqual(result["details"]["bundle"]["reviewed_plan"]["path"],
                         "reports/delivery-20260906/v2-delivery-plan.json")
        admission = self.root / f"artifacts/build-validation/{self.LIVE_SET}-admit/admission.json"
        os.remove(admission)
        os.symlink(self.plan_path, admission)
        with self.assertRaisesRegex(workflow.ReleaseWorkflowError, "symlink"):
            workflow.check(BUILD, self.LIVE_SET, self.root)


if __name__ == "__main__":
    unittest.main()
