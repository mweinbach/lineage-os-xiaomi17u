"""Exercise the camera hook selector and prerequisite through GNU Make."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/camera-session-inject.mk"
CONTRACT = ROOT / "config/nezha-camera-session-inject.json"


class CameraSessionInjectEvidenceTests(unittest.TestCase):
    def test_reviewed_contract_hashes_match_authored_artifacts(self):
        contract = json.loads(CONTRACT.read_text())
        for path, expected in (
                (contract["fragment"], contract["fragment_sha256"]),
                (contract["patch"], contract["patch_sha256"]),
                *((path, row["sha256"]) for path, row in contract["authored_templates"].items())):
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_patch_installs_exact_authored_adapter_templates(self):
        # Reconstruct each newly added source file from the actual patch that
        # is applied to frameworks/av, independently of the template's pin.
        contract = json.loads(CONTRACT.read_text())
        sections = (ROOT / contract["patch"]).read_text().split("diff --git ")[1:]
        for path in contract["authored_templates"]:
            name = Path(path).name
            destination = "services/camera/libcameraservice/utils/" + name
            matches = [section for section in sections
                       if section.splitlines()[0] == f"a/{destination} b/{destination}"]
            self.assertEqual(len(matches), 1, destination)
            lines = matches[0].splitlines(keepends=True)
            self.assertIn("new file mode 100644\n", lines)
            reconstructed = "".join(line[1:] for line in lines
                                    if line.startswith("+") and not line.startswith("+++"))
            self.assertEqual(reconstructed.encode(), (ROOT / path).read_bytes())


class CameraSessionInjectFragmentTests(unittest.TestCase):
    def run_fragment(self, selector=None, framework=None):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        assignments = ""
        for name, value in (("NEZHA_CAMERA_SESSION_INJECT", selector),
                            ("NEZHA_CAMERA_FRAMEWORK", framework)):
            if value is not None:
                assignments += f"{name} := {value}\n"
        # Capture the function's arguments when the real fragment expands it.
        # This catches a wrong namespace/key/value and unexpected repeated calls.
        makefile = (assignments
                    + "soong_config_set_bool = $(eval CALLS += $(1):$(2):$(3))\n"
                    + f"include {FRAGMENT}\n"
                    + "all:\n\t@printf '%s\\n' '$(CALLS)'\n")
        return subprocess.run([make, "--no-print-directory", "-f", "-"],
                              input=makefile, capture_output=True, text=True,
                              env={"PATH": "/usr/bin:/bin"}, timeout=10)

    def test_enabled_hook_configures_soong_once_with_framework_enabled(self):
        for selector, framework in (("true", "true"),
                                    ("  true  ", "  true  ")):
            with self.subTest(selector=selector, framework=framework):
                result = self.run_fragment(selector, framework)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.split(),
                                 ["nezha_camera_session:enabled:true"])

    def test_disabled_or_unset_hook_emits_no_soong_configuration(self):
        for selector in (None, "", "   ", "false", " false "):
            for framework in (None, "", "false", "true"):
                with self.subTest(selector=selector, framework=framework):
                    result = self.run_fragment(selector, framework)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), "")

    def test_malformed_or_duplicate_selectors_are_rejected(self):
        for selector in ("yes", "1", "0", "TRUE", "False", "true false",
                         "true true", "false false", "true\ttrue"):
            with self.subTest(selector=selector):
                result = self.run_fragment(selector, "true")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERA_SESSION_INJECT", result.stderr)
                self.assertEqual(result.stdout.strip(), "")

    def test_enabled_hook_requires_framework_true(self):
        for framework in (None, "", "false", "yes", "true true", "true false"):
            with self.subTest(framework=framework):
                result = self.run_fragment("true", framework)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERA_FRAMEWORK=true", result.stderr)
                self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
