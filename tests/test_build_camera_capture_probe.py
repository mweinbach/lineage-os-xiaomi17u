import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / "scripts/build_camera_capture_probe.py"
SPEC = importlib.util.spec_from_file_location("build_camera_capture_probe", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CameraCaptureProbeBuildTest(unittest.TestCase):
    def fixture(self, root):
        sdk, jdk = root / "sdk", root / "jdk"
        for relative in ("platforms/android-36/android.jar", "build-tools/36.0.0/aapt2",
                         "build-tools/36.0.0/d8", "build-tools/36.0.0/zipalign",
                         "build-tools/36.0.0/apksigner"):
            path = sdk / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")
        for name in ("javac", "keytool"):
            path = jdk / "bin" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")
        source = root / "tools/camera-capture-probe"
        source.mkdir(parents=True)
        (source / "AndroidManifest.xml").write_text("fixture")
        (source / "CaptureActivity.java").write_text("fixture")
        return sdk, jdk

    def test_missing_sdk_does_not_start_process_or_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            output = root / "output"
            with mock.patch.object(MODULE.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "Missing installed inputs"):
                    MODULE.build(root / "sdk", output, root / "jdk")
            run.assert_not_called()
            self.assertFalse(output.exists())

    def test_existing_diagnostic_key_and_capture_artifacts_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            sdk, jdk = self.fixture(root)
            output = root / "artifacts/existing-probe"
            output.mkdir(parents=True)
            key = output / "diagnostic-only.p12"
            key.write_bytes(b"existing diagnostic key")
            with mock.patch.object(MODULE, "ROOT", root), mock.patch.object(MODULE.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "Output already exists"):
                    MODULE.build(sdk, output, jdk)
            run.assert_not_called()
            self.assertEqual(key.read_bytes(), b"existing diagnostic key")

    def test_key_output_outside_private_artifact_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            sdk, jdk = self.fixture(root)
            output = root / "tools/public-probe-output"
            with mock.patch.object(MODULE, "ROOT", root), mock.patch.object(MODULE.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "ignored artifacts/"):
                    MODULE.build(sdk, output, jdk)
            run.assert_not_called()
            self.assertFalse(output.exists())

    def test_missing_git_ignore_rule_rejects_before_build_and_key_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            sdk, jdk = self.fixture(root)
            output = root / "artifacts/not-ignored"
            with mock.patch.object(MODULE, "ROOT", root), mock.patch.object(
                    MODULE.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
                with self.assertRaisesRegex(ValueError, "not Git-ignored"):
                    MODULE.build(sdk, output, jdk)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][:3], ["git", "check-ignore", "--quiet"])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
