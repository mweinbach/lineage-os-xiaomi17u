"""Offline exact-byte WLC packet and unconditional closed-admission tests."""
import copy
import json
from pathlib import Path
import re
import runpy
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import workload_classifier_inputs as wlc


class WorkloadClassifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "capture"
        (self.source / "files").mkdir(parents=True)
        self.output = self.root / "packet"
        self.spec, _ = wlc.contract()
        self.spec = copy.deepcopy(self.spec)
        self.rows = []
        for number, item in enumerate(self.spec["files"]):
            raw = ("WLC fixture %d\n" % number).encode()
            item.update(sha256=wlc.digest(raw), size_bytes=len(raw))
            name = "files/%04d" % (number + 1)
            (self.source / name).write_bytes(raw)
            self.rows.append({"path": item["capture_path"], "output_path": name,
                              "sha256": item["sha256"], "size_bytes": len(raw),
                              "type": "regular", "readback_verified": True})
        self.capture = {"operation": "erofs-capture", "image_mounted": False,
                        "firmware_executed": False, "files": self.rows,
                        "image": {"sha256": self.spec["system_ext_image_sha256"]}}
        self.save_capture()
        self.raw = wlc.encoded(self.spec)

    def save_capture(self):
        (self.source / "receipt.json").write_bytes(wlc.encoded(self.capture))

    def prepare(self):
        with mock.patch.object(wlc, "contract", return_value=(self.spec, self.raw)):
            return wlc.prepare(self.source, self.output)

    def test_reviewed_contract_and_blueprint(self):
        spec, raw = wlc.contract()
        self.assertEqual(wlc.digest(raw), wlc.CONTRACT_SHA256)
        self.assertEqual(len(spec["files"]), 3)
        self.assertEqual(sum(r["size_bytes"] for r in spec["files"]), 197970)
        self.assertFalse(spec["activated"])
        self.assertIn("libtflite.so", spec["native_needed"])
        self.assertEqual(len(spec["original_signer_certificate_sha256"]), 64)
        bp = (wlc.TEMPLATES / "Android.bp.in").read_text()
        self.assertEqual(bp.count("enabled: false"), 4)
        for flag in ("presigned: true", "preprocessed: true", "check_elf_files: true",
                     "allow_undefined_symbols: false", "enforce_uses_libs: true"):
            self.assertIn(flag, bp)
        self.assertNotIn("certificate:", bp)
        self.assertEqual(set(re.findall(r"//vendor/xiaomi/nezha-workload-classifier:([\w]+)", bp)),
                         {r["filegroup"] for r in spec["files"]})

    def test_roundtrip_original_bytes_inactive(self):
        receipt = self.prepare()
        self.assertEqual(receipt, wlc.verify(self.output, self.spec, self.raw))
        self.assertFalse(receipt["activation_allowed"])
        self.assertFalse(receipt["signing_performed"])
        self.assertFalse(receipt["android_build_verified"])
        self.assertTrue(receipt["original_apk_bytes_preserved"])
        self.assertEqual(list(self.output.rglob("Android.bp")), [])

    def test_hash_mismatch_no_output(self):
        (self.source / self.rows[0]["output_path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(wlc.WorkloadInputError, "hash or size mismatch"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_missing_file_no_output(self):
        (self.source / self.rows[0]["output_path"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_existing_destination_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "keep"
        sentinel.write_text("user data")
        with self.assertRaisesRegex(wlc.WorkloadInputError, "already exists"):
            self.prepare()
        self.assertEqual(sentinel.read_text(), "user data")

    def test_input_symlink_rejected(self):
        path = self.source / self.rows[0]["output_path"]
        target = self.root / "original"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(wlc.WorkloadInputError, "regular file"):
            self.prepare()

    def test_directory_symlink_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(wlc.WorkloadInputError, "symlink"):
            wlc.capture_inputs(alias, self.spec)

    def test_unsafe_relative_paths(self):
        for value in ("../escape", "/absolute", "a//b", "a/./b", "a/../b", "a\\b", "$(shell)", ""):
            with self.subTest(value=value), self.assertRaises(wlc.WorkloadInputError):
                wlc.relative(value)

    def test_duplicate_contract_input(self):
        self.spec["files"].append(copy.deepcopy(self.spec["files"][0]))
        with self.assertRaisesRegex(wlc.WorkloadInputError, "duplicate"):
            self.prepare()

    def test_changed_capture_runtime_mapping(self):
        self.spec["files"][0]["capture_path"] = "/app/other.apk"
        with self.assertRaisesRegex(wlc.WorkloadInputError, "path mismatch"):
            self.prepare()

    def test_duplicate_capture_row(self):
        self.rows[1] = copy.deepcopy(self.rows[0])
        self.save_capture()
        with self.assertRaisesRegex(wlc.WorkloadInputError, "duplicate"):
            self.prepare()

    def test_capture_identity_mismatch(self):
        for key, value in (("image_mounted", True), ("firmware_executed", True), ("operation", "other")):
            with self.subTest(key=key):
                original = self.capture[key]
                self.capture[key] = value
                self.save_capture()
                with self.assertRaisesRegex(wlc.WorkloadInputError, "factory readback"):
                    self.prepare()
                self.capture[key] = original

    def test_changed_image(self):
        self.capture["image"]["sha256"] = "0" * 64
        self.save_capture()
        with self.assertRaisesRegex(wlc.WorkloadInputError, "factory readback"):
            self.prepare()

    def test_capture_row_hash_mismatch(self):
        self.rows[0]["sha256"] = "0" * 64
        self.save_capture()
        with self.assertRaisesRegex(wlc.WorkloadInputError, "capture identity"):
            self.prepare()

    def test_capture_path_traversal(self):
        self.rows[0]["output_path"] = "files/../../escape"
        self.save_capture()
        with self.assertRaisesRegex(wlc.WorkloadInputError, "relative path"):
            self.prepare()

    def test_duplicate_capture_output(self):
        self.rows[1]["output_path"] = self.rows[0]["output_path"]
        self.save_capture()
        with self.assertRaisesRegex(wlc.WorkloadInputError, "duplicate capture output"):
            self.prepare()

    def test_tampered_receipt_rejected(self):
        self.prepare()
        path = self.output / wlc.RECEIPT
        receipt = json.loads(path.read_text())
        receipt["activation_allowed"] = True
        path.write_bytes(wlc.encoded(receipt))
        with self.assertRaisesRegex(wlc.WorkloadInputError, "packet content mismatch"):
            wlc.verify(self.output, self.spec, self.raw)

    def test_extra_active_blueprint_rejected(self):
        self.prepare()
        (self.output / wlc.PRIVATE / "Android.bp").write_text("soong_namespace {}")
        with self.assertRaisesRegex(wlc.WorkloadInputError, "unexpected packet file"):
            wlc.verify(self.output, self.spec, self.raw)

    def test_template_drift_rejected(self):
        self.spec["templates"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(wlc.WorkloadInputError, "unreviewed WLC template"):
            self.prepare()

    def test_build_guard_drift_rejected(self):
        self.spec["build_guard"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(wlc.WorkloadInputError, "unreviewed WLC build guard"):
            self.prepare()

    def test_admission_cannot_be_enabled_by_receipt(self):
        for receipt in ({}, {"activation_allowed": True, "open_gates": []}):
            with self.assertRaisesRegex(wlc.WorkloadInputError, "activation blocked"):
                wlc.require_admission(receipt)

    def test_generated_guard_consumes_all_exact_inputs(self):
        self.prepare()
        guard = runpy.run_path(str(self.output / wlc.PRIVATE / "tools/verify_inputs.py"))
        output = self.root / "verified"
        output.mkdir()
        inputs = [str(self.output / wlc.PRIVATE / row["path"]) for row in self.spec["files"]]
        guard["produce"](inputs, output)
        for row in self.spec["files"]:
            self.assertEqual((output / "verified" / row["path"]).read_bytes(),
                             (self.output / wlc.PRIVATE / row["path"]).read_bytes())

    def test_generated_guard_rejects_changed_input_without_outputs(self):
        self.prepare()
        guard = runpy.run_path(str(self.output / wlc.PRIVATE / "tools/verify_inputs.py"))
        output = self.root / "verified"
        output.mkdir()
        inputs = [str(self.output / wlc.PRIVATE / row["path"]) for row in self.spec["files"]]
        path = Path(inputs[-1])
        path.write_bytes(b"x" * path.stat().st_size)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            guard["produce"](inputs, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_generated_guard_rejects_duplicate_and_missing(self):
        self.prepare()
        guard = runpy.run_path(str(self.output / wlc.PRIVATE / "tools/verify_inputs.py"))
        output = self.root / "verified"
        output.mkdir()
        inputs = [str(self.output / wlc.PRIVATE / row["path"]) for row in self.spec["files"]]
        for bad in (inputs[:-1], inputs[:2] + [inputs[0]]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                guard["produce"](bad, output)
        self.assertEqual(list(output.iterdir()), [])


class WorkloadClassifierMakeGateTests(unittest.TestCase):
    def make(self, value=None):
        path = wlc.ROOT / "device/xiaomi/nezha/workload-classifier.mk"
        arguments = ["make", "--no-print-directory", "-f", "-", "all"]
        if value is not None:
            arguments.append("NEZHA_WORKLOAD_CLASSIFIER=" + value)
        return subprocess.run(arguments, input=f"include {path}\nall:\n\t@echo baseline\n", text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)

    def test_default_and_false_preserve_baseline(self):
        for value in (None, "false"):
            with self.subTest(value=value):
                result = self.make(value)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_true_explicitly_fails_closed(self):
        result = self.make("true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workload classifier blocked", result.stderr)

    def test_malformed_flags_fail(self):
        for value in ("", "yes", "TRUE", "false true", "true false", "0", "true "):
            with self.subTest(value=value):
                result = self.make(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("must be exactly true or false", result.stderr)

    def test_make_normalized_leading_space_still_fails_closed(self):
        # GNU make trims assignment-leading whitespace before including the gate.
        result = self.make(" true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workload classifier blocked", result.stderr)


if __name__ == "__main__":
    unittest.main()
