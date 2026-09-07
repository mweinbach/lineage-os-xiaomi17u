"""Exercise the CameraOpt ABI opt-in and its retained patch identities."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/cameraopt-native-compat.mk"


class CameraOptNativeCompatTests(unittest.TestCase):
    def test_contract_hashes_recompute_from_selected_inputs(self):
        contract = json.loads((ROOT / "config/nezha-cameraopt-native-compat.json").read_text())
        for name in ("fragment", "patch"):
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / contract[name]).read_bytes()).hexdigest(),
                                 contract[name + "_sha256"])

    def run_fragment(self, selector, framework):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        assignments = ""
        for name, value in (("NEZHA_CAMERAOPT_NATIVE_COMPAT", selector),
                            ("NEZHA_CAMERA_FRAMEWORK", framework)):
            if value is not None:
                assignments += f"{name} := {value}\n"
        script = (assignments
                  + "soong_config_set_bool = $(eval CALLS += $(1):$(2):$(3))\n"
                  + f"include {FRAGMENT}\n"
                  + "all:\n\t@printf '%s\\n' '$(CALLS)'\n")
        return subprocess.run([make, "--no-print-directory", "-f", "-"], input=script,
                              text=True, capture_output=True, timeout=10,
                              env={"PATH": "/usr/bin:/bin"})

    def test_opt_in_selects_only_the_expected_native_abi_flag(self):
        for selector, framework in (("true", "true"), (" true ", " true ")):
            with self.subTest(selector=selector, framework=framework):
                result = self.run_fragment(selector, framework)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.split(), ["nezha_cameraopt:native_compat:true"])

    def test_unselected_compatibility_emits_no_build_configuration(self):
        for selector in (None, "", " ", "false", " false "):
            for framework in (None, "", "false", "true"):
                with self.subTest(selector=selector, framework=framework):
                    result = self.run_fragment(selector, framework)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), "")

    def test_malformed_or_multiple_values_fail_before_selection(self):
        for selector in ("yes", "1", "TRUE", "False", "true true", "true false",
                         "false false", "true\ttrue"):
            with self.subTest(selector=selector):
                result = self.run_fragment(selector, "true")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERAOPT_NATIVE_COMPAT", result.stderr)
                self.assertEqual(result.stdout.strip(), "")

    def test_enabled_abi_requires_the_camera_framework(self):
        for framework in (None, "", "false", "yes", "true true", "true false"):
            with self.subTest(framework=framework):
                result = self.run_fragment("true", framework)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERA_FRAMEWORK=true", result.stderr)
                self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
