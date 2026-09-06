"""Offline exact-source/patch checks; JVM fake-factory tests run separately."""
import hashlib
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from scripts import aperture_camera_admission as admission

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/aperture-camera-admission"
PREFIX = "app/src/main/java/org/lineageos/aperture/"
VIEW_MODEL = PREFIX + "viewmodels/CameraViewModel.kt"


class ApertureCameraAdmissionTest(unittest.TestCase):
    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(target, side_effect=AssertionError("offline: " + target)))

    def test_exact_originals_replay_to_recorded_candidates(self):
        files = admission.candidate(FIXTURE)
        record = json.loads(admission.CONTRACT.read_bytes())
        self.assertEqual(record["revision"], "88625a9b7c4178601169dbda2c38cd845b68cd38")
        self.assertEqual(len(files), 5)
        for path, data in files.items():
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["files"][path]["after_sha256"])

    def test_direct_script_cli_help_is_available_without_process_calls(self):
        script = ROOT / "scripts/aperture_camera_admission.py"
        with mock.patch.object(sys, "path", [str(script.parent)] + sys.path), \
                mock.patch.object(sys, "argv", [str(script), "--help"]), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--source", stdout.getvalue())

    def test_changed_original_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            shutil.copytree(FIXTURE, source)
            with (source / PREFIX / "ApertureApplication.kt").open("ab") as stream:
                stream.write(b"// unrelated change\n")
            with self.assertRaisesRegex(ValueError, "Aperture source differs"):
                admission.stage(source, root / "output")
            self.assertFalse((root / "output").exists())

    def test_changed_view_model_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            shutil.copytree(FIXTURE, source)
            with (source / VIEW_MODEL).open("ab") as stream:
                stream.write(b"// unrelated change\n")
            with self.assertRaisesRegex(ValueError, "Aperture source differs"):
                admission.stage(source, root / "output")
            self.assertFalse((root / "output").exists())

    def test_existing_factory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            shutil.copytree(FIXTURE, source)
            factory = source / PREFIX / "compat/NezhaCameraFactory.java"
            factory.parent.mkdir()
            factory.write_text("preserve user implementation")
            with self.assertRaisesRegex(ValueError, "already exists"):
                admission.candidate(source)
            self.assertEqual(factory.read_text(), "preserve user implementation")

    def test_stage_never_modifies_source_and_refuses_output_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "output"
            before = {str(p): p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()}
            self.assertFalse(admission.stage(FIXTURE, output)["source_modified"])
            self.assertEqual(before, {str(p): p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()})
            with self.assertRaisesRegex(ValueError, "Output exists"):
                admission.stage(FIXTURE, output)

    def test_patch_scope_and_empty_provider_handling(self):
        files = admission.candidate(FIXTURE)
        factory = files[PREFIX + "compat/NezhaCameraFactory.java"].decode()
        repository = files[PREFIX + "repositories/CameraRepository.kt"].decode()
        self.assertIn('if (!"nezha".equals(Build.DEVICE)) return base;', factory)
        self.assertIn("delegate.onCameraIdsUpdated(filter(ids))", factory)
        self.assertIn("getAvailableCameraIds(filtered)", factory)
        self.assertIn("REQUEST_AVAILABLE_CAPABILITIES_SYSTEM_CAMERA", factory)
        self.assertIn("REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE", factory)
        for forbidden in ("getPhysicalCameraIds", "SCALER_STREAM_CONFIGURATION_MAP", "openCamera(",
                          'id.equals("0")', 'id.equals("1")', "setAvailableCamerasLimiter"):
            self.assertNotIn(forbidden, factory)
        self.assertIn('if (Build.DEVICE != "nezha") throw error', repository)
        self.assertEqual(repository.count("cameraProvider?.availableCameraInfos.orEmpty()"), 2)

    def test_null_initialization_race_has_nonfatal_source_contract(self):
        # Source-level regression only; native coroutine execution belongs to the Aperture build.
        view_model = admission.candidate(FIXTURE)[VIEW_MODEL].decode()
        helper_start = view_model.index(
            "private inline fun <reified T : CameraConfiguration> updateConfiguration("
        )
        helper_end = view_model.index("\n    companion object", helper_start)
        helper = view_model[helper_start:helper_end]
        guard = "val currentCameraConfiguration = _cameraConfiguration.value ?: return false"

        self.assertIn(guard, helper)
        self.assertNotIn('error(\n                "Camera configuration is null"', helper)
        self.assertLess(helper.index("return try {"), helper.index(guard))
        self.assertLess(helper.index(guard), helper.index("rebindMutex.unlock()"))

        mode_start = view_model.index("fun setCameraMode(")
        mode_end = view_model.index("\n    /**", mode_start)
        self.assertIn(
            "updateConfiguration<CameraConfiguration>",
            view_model[mode_start:mode_end],
        )

    def test_native_blueprint_selects_exact_java_helper_with_existing_kotlin(self):
        files = admission.candidate(FIXTURE)
        before = (FIXTURE / "app/Android.bp").read_bytes()
        old = b'    srcs: ["src/main/java/**/*.kt"],\n'
        new = (b'    srcs: [\n'
               b'        "src/main/java/**/*.kt",\n'
               b'        "src/main/java/org/lineageos/aperture/compat/NezhaCameraFactory.java",\n'
               b'    ],\n')
        self.assertEqual(files["app/Android.bp"], before.replace(old, new, 1))
        self.assertIn(PREFIX + "compat/NezhaCameraFactory.java", files)
        self.assertEqual(files["app/Android.bp"].count(b'compat/NezhaCameraFactory.java"'), 1)


if __name__ == "__main__":
    unittest.main()
