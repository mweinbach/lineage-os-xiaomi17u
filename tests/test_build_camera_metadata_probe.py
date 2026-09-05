import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / "scripts/build_camera_metadata_probe.py"
SPEC = importlib.util.spec_from_file_location("build_camera_metadata_probe", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CameraProbeBuildTest(unittest.TestCase):
    def test_missing_sdk_fails_without_creating_output_or_running_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            with mock.patch.object(MODULE.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "Missing installed inputs"):
                    MODULE.build(root / "sdk", output, root / "jdk")
            self.assertFalse(output.exists())
            run.assert_not_called()

    def test_existing_output_and_key_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sdk, jdk, output = root / "sdk", root / "jdk", root / "output"
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
            output.mkdir()
            key = output / "diagnostic-only.p12"
            key.write_bytes(b"preserve existing key")
            with mock.patch.object(MODULE.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "Output already exists"):
                    MODULE.build(sdk, output, jdk)
            self.assertEqual(key.read_bytes(), b"preserve existing key")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
