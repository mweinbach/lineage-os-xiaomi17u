"""Offline coverage of the camera scheduling input and native selection gates."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import camera_task_profiles as camera

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "device/xiaomi/nezha"
spec = importlib.util.spec_from_file_location("camera_native_verifier", DEVICE / "camera-task-profiles/verify.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(camera.CONTRACT.read_text())
        self.candidate = json.loads(camera.CANDIDATE.read_text())
        self.factory = {"AggregateProfiles": [{"Name": "CAMERA_CAPTURE_SCHED", "Profiles": [
            "CameraProcessCapacityLevel6", "CameraPerformanceLevel2"]}], "Profiles": [
            {"Name": name, "Actions": [{"Name": "JoinCgroup", "Params": params}]}
            for name, params in zip(["CameraProcessCapacityLevel6", "CameraPerformanceLevel2"],
                                    self.contract["oem_capture_actions"])]}

    def test_exact_mapping_and_non_oem_semantics(self):
        camera.validate_mapping(self.factory, self.candidate, self.contract)
        self.assertEqual(self.candidate, native.EXPECTED)
        self.assertNotEqual(self.contract["candidate_actions"], self.contract["oem_capture_actions"])

    def test_missing_duplicate_or_changed_oem(self):
        for mutation in ("missing", "duplicate", "action", "path", "aggregate"):
            with self.subTest(mutation=mutation):
                factory = copy.deepcopy(self.factory)
                if mutation == "missing":
                    factory["Profiles"].pop()
                elif mutation == "duplicate":
                    factory["Profiles"].append(copy.deepcopy(factory["Profiles"][0]))
                elif mutation == "action":
                    factory["Profiles"][0]["Actions"][0]["Name"] = "SetAttribute"
                elif mutation == "path":
                    factory["Profiles"][0]["Actions"][0]["Params"]["Path"] = "top-app"
                else:
                    factory["AggregateProfiles"][0]["Profiles"].reverse()
                with self.assertRaises(ValueError):
                    camera.validate_mapping(factory, self.candidate, self.contract)

    def test_extra_noop_or_unsupported_candidate_rejected(self):
        for mutation in ("empty", "extra", "boost", "oem"):
            with self.subTest(mutation=mutation):
                candidate = copy.deepcopy(self.candidate)
                if mutation == "empty":
                    candidate["Profiles"][0]["Actions"] = []
                elif mutation == "extra":
                    candidate["Attributes"] = []
                elif mutation == "boost":
                    candidate["Profiles"][0]["Actions"].append({"Name": "SetAttribute"})
                else:
                    candidate["Profiles"][0]["Actions"][0]["Params"]["Path"] += "/limit-level6"
                with self.assertRaises(ValueError):
                    camera.validate_mapping(self.factory, candidate, self.contract)

    def test_native_pins_match_public_record(self):
        self.assertEqual(native.SOURCE_PINS, self.contract["upstream"]["source_sha256"])
        self.assertFalse(self.contract["hardware_verified"])
        self.assertFalse(self.contract["runtime_loader_verified"])
        self.assertFalse(self.contract["native_build_verified"])
        self.assertEqual(self.contract["loader"]["input"], "/system_ext/etc/task_profiles_cameraopt.json")


class NativeGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source.json"
        self.source.write_bytes(b"synthetic source\n")
        self.pins = {"source.json": hashlib.sha256(self.source.read_bytes()).hexdigest()}
        self.profile = self.root / "profile.json"
        self.profile.write_text(json.dumps(native.EXPECTED))

    def test_verified_sources_and_candidate(self):
        with patch.object(native, "SOURCE_PINS", self.pins):
            self.assertEqual(native.verify(self.root, self.profile), "verified-camera-task-profiles")

    def test_changed_or_missing_source_fails_closed(self):
        with patch.object(native, "SOURCE_PINS", self.pins):
            self.source.write_text("changed")
            with self.assertRaises(ValueError):
                native.verify(self.root, self.profile)
            self.source.unlink()
            with self.assertRaises(OSError):
                native.verify(self.root, self.profile)

    def test_changed_profile_fails_closed(self):
        with patch.object(native, "SOURCE_PINS", self.pins):
            for raw in ('{}', '{"Profiles":[],"Profiles":[]}'):
                self.profile.write_text(raw)
                with self.assertRaises(ValueError):
                    native.verify(self.root, self.profile)

    def test_symlink_and_large_source_rejected(self):
        self.source.rename(self.root / "real")
        self.source.symlink_to("real")
        with self.assertRaises(ValueError):
            native.read_regular(self.source)
        self.source.unlink()
        self.source.write_bytes(b"x" * (1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            native.read_regular(self.source)


class MakeGateTests(unittest.TestCase):
    def run_make(self, value):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            makefile = root / "Makefile"
            makefile.write_text(f"NEZHA_DEVICE_PATH := {DEVICE}\n"
                                "TARGET_COPY_OUT_SYSTEM_EXT := system_ext\n"
                                f"NEZHA_CAMERA_TASK_PROFILES := {value}\n"
                                f"include {DEVICE}/camera-task-profiles.mk\n"
                                "all:\n\t@echo COPY=$(PRODUCT_COPY_FILES)\n")
            return subprocess.run(["make", "--no-print-directory", "-f", str(makefile)],
                                  cwd=root, text=True, capture_output=True, timeout=10)

    def test_unset_false_do_not_add_file_or_require_source(self):
        for value in ("", "false"):
            result = self.run_make(value)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "COPY=")

    def test_invalid_or_repeated_selector_rejected(self):
        for value in ("yes", "1", "true true", "true false"):
            result = self.run_make(value)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("NEZHA_CAMERA_TASK_PROFILES", result.stderr)

    def test_enabled_without_pinned_source_rejected(self):
        result = self.run_make("true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Camera task-profile admission failed", result.stderr)
        self.assertNotIn("COPY=", result.stdout)


if __name__ == "__main__":
    unittest.main()
