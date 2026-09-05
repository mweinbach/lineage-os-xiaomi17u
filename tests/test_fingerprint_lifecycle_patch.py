"""Offline integrity/fixture tests; actual Java execution is an explicit validation step."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "fingerprint_lifecycle", ROOT / "scripts/test_nezha_fingerprint_lifecycle.py")
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class FingerprintLifecyclePatchTests(unittest.TestCase):
    def test_exact_pinned_new_file_can_be_reconstructed(self):
        source = validation.source_from_patch()
        self.assertIn("final class NezhaFingerprintOverlay", source)

    def test_patch_tampering_fails_before_java_execution(self):
        metadata = json.loads((ROOT / "patches/evolution/nezha-fingerprint-overlay-lifecycle.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / metadata["patch"]
            target.parent.mkdir(parents=True)
            target.write_bytes((ROOT / metadata["patch"]).read_bytes() + b"\n")
            (target.parent / "nezha-fingerprint-overlay-lifecycle.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "patch digest mismatch"):
                validation.source_from_patch(root)

    def test_fixture_compiles_the_exact_candidate_and_propagates_failures(self):
        source = validation.source_from_patch()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(validation.subprocess, "run") as run:
            root = Path(directory)
            validation.run_validation(root, source)
            self.assertEqual(run.call_count, 2)
            compile_args = run.call_args_list[0]
            execute_args = run.call_args_list[1]
            self.assertEqual(compile_args.args[0][0], "javac")
            self.assertTrue(compile_args.kwargs["check"])
            self.assertEqual(execute_args.args[0][0], "java")
            self.assertTrue(execute_args.kwargs["check"])
            emitted = root / "com/android/server/biometrics/sensors/NezhaFingerprintOverlay.java"
            self.assertEqual(emitted.read_text(), source)
            self.assertIn(str(emitted), compile_args.args[0])

    def test_compiler_failure_does_not_run_stale_fixture(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
                validation.subprocess, "run", side_effect=RuntimeError("compiler failed")) as run:
            with self.assertRaisesRegex(RuntimeError, "compiler failed"):
                validation.run_validation(Path(directory), validation.source_from_patch())
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
