"""Standard-library patch integrity and JVM orchestration tests, entirely offline."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import test_nezha_ims_api as validation


class ImsTelephonyApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = json.loads((validation.WORKSPACE / validation.METADATA).read_text())

    def write_contract(self):
        target = self.root / validation.METADATA
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.record))

    def test_source_has_only_the_reviewed_hidden_property_api(self):
        source = validation.source_from_patch()
        self.assertIn("@hide", source)
        self.assertIn("public static boolean isMiuiRom()", source)
        self.assertEqual(source.count("SystemProperties.get("), 2)
        self.assertNotIn("SystemProperties.set", source)
        self.assertNotIn("UnsupportedAppUsage", source)
        self.assertEqual(len(self.record["callsites"]), 4)
        self.assertFalse(self.record["hidden_api"]["new_allowlist"])

    def test_changed_patch_is_rejected(self):
        self.write_contract()
        patch = self.root / self.record["patch"]
        patch.write_bytes((validation.WORKSPACE / self.record["patch"]).read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "patch digest mismatch"):
            validation.source_from_patch(self.root)

    def test_wrong_hunk_count_is_rejected_even_with_updated_patch_digest(self):
        patch = (validation.WORKSPACE / self.record["patch"]).read_bytes().replace(
            b"+1,32", b"+1,30")
        self.record["patch_sha256"] = hashlib.sha256(patch).hexdigest()
        self.write_contract()
        (self.root / self.record["patch"]).write_bytes(patch)
        with self.assertRaisesRegex(ValueError, "patch header"):
            validation.source_from_patch(self.root)

    def test_fixture_compiles_exact_source_and_checks_commands(self):
        source = validation.source_from_patch()
        with mock.patch.object(validation.subprocess, "run") as run:
            validation.run_validation(self.root, source)
        self.assertEqual(run.call_count, 2)
        compile_call, execute_call = run.call_args_list
        target = self.root / "android/telephony/TelephonyBaseUtilsStub.java"
        self.assertEqual(target.read_text(), source)
        self.assertEqual(compile_call.args[0][0], "javac")
        self.assertIn(str(target), compile_call.args[0])
        self.assertTrue(compile_call.kwargs["check"])
        self.assertEqual(execute_call.args[0][0], "java")
        self.assertTrue(execute_call.kwargs["check"])

    def test_compiler_failure_does_not_execute_stale_classes(self):
        with mock.patch.object(validation.subprocess, "run", side_effect=RuntimeError("compile failed")) as run:
            with self.assertRaisesRegex(RuntimeError, "compile failed"):
                validation.run_validation(self.root, validation.source_from_patch())
        self.assertEqual(run.call_count, 1)

    def source_basis_fixture(self):
        source = self.root / "source"
        source.mkdir()
        for name in self.record["source_basis"]:
            raw = ("fixture " + name).encode()
            self.record["source_basis"][name] = hashlib.sha256(raw).hexdigest()
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self.write_contract()
        return source

    def test_source_basis_check_is_read_only_and_does_not_activate(self):
        source = self.source_basis_fixture()
        before = {str(p): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        result = validation.verify_source_basis(source, self.root)
        self.assertTrue(result["source_basis_verified"])
        self.assertFalse(result["source_changed"])
        self.assertFalse(result["activation_allowed"])
        self.assertEqual(before, {str(p): p.read_bytes() for p in source.rglob("*") if p.is_file()})

    def test_changed_framework_selection_rejected(self):
        source = self.source_basis_fixture()
        (source / "telephony/java/Android.bp").write_text("changed selection")
        with self.assertRaisesRegex(ValueError, "basis differs"):
            validation.verify_source_basis(source, self.root)

    def test_existing_api_is_preserved_and_requires_review(self):
        source = self.source_basis_fixture()
        target = source / self.record["file"]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("user implementation")
        with self.assertRaisesRegex(ValueError, "already exists"):
            validation.verify_source_basis(source, self.root)
        self.assertEqual(target.read_text(), "user implementation")


if __name__ == "__main__":
    unittest.main()
