"""Offline tests of haptics preservation evidence and explicit source selection."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from scripts import haptics_controls as haptics

ROOT = Path(__file__).resolve().parents[1]
POLICY = b"<hapticsPolicyConfiguration><hapticsPerformAPI><effect_id>0</effect_id></hapticsPerformAPI><hapticsComposeAPI><SupportCompose>True</SupportCompose></hapticsComposeAPI></hapticsPolicyConfiguration>"
CONFIG = b"<haptics_param_values><predefined_effect><Hapticseffect effect='0'><low_pulse_intensity>20</low_pulse_intensity><mid_pulse_intensity>100</mid_pulse_intensity><high_pulse_intensity>90</high_pulse_intensity></Hapticseffect></predefined_effect></haptics_param_values>"


def fixture(root):
    files = {"/etc/HapticsPolicy.xml": POLICY, "/etc/Hapticsconfig.xml": CONFIG}
    contract, records = {}, []
    (root / "files").mkdir()
    for index, (path, raw) in enumerate(files.items(), 1):
        entry = {"output_path": f"files/{index:04d}", "size_bytes": len(raw),
                 "sha256": hashlib.sha256(raw).hexdigest()}
        contract[path] = entry
        records.append({**entry, "path": path, "type": "regular", "readback_verified": True})
        (root / entry["output_path"]).write_bytes(raw)
    receipt = {"operation": "erofs-capture", "image": {"sha256": haptics.VENDOR_HASH},
               "files": records, "firmware_executed": False, "image_mounted": False,
               "symlinks_followed": False}
    (root / "receipt.json").write_text(json.dumps(receipt))
    return contract, receipt, files


class CaptureTests(unittest.TestCase):
    def test_reports_nonmonotonic_factory_strengths_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contract, _, _ = fixture(root)
            with patch.object(haptics, "CALIBRATION", contract):
                report = haptics.verify_capture(root)
            self.assertFalse(report["details"]["all_strength_rows_monotonic"])
            self.assertFalse(report["calibration_modified"])
            self.assertFalse(report["hardware_behavior_verified"])
            self.assertEqual((root / "files/0002").read_bytes(), CONFIG)

    def test_rejects_changed_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contract, _, _ = fixture(root)
            (root / "files/0002").write_bytes(CONFIG.replace(b">20<", b">21<"))
            with patch.object(haptics, "CALIBRATION", contract), self.assertRaisesRegex(ValueError, "bytes changed"):
                haptics.verify_capture(root)

    def test_rejects_wrong_vendor_and_duplicate_receipt(self):
        for mutation in ("vendor", "duplicate"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                contract, receipt, _ = fixture(root)
                if mutation == "vendor":
                    receipt["image"]["sha256"] = "0" * 64
                else:
                    receipt["files"].append(receipt["files"][0])
                (root / "receipt.json").write_text(json.dumps(receipt))
                with patch.object(haptics, "CALIBRATION", contract), self.assertRaises(ValueError):
                    haptics.verify_capture(root)

    def test_rejects_symlink_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contract, _, _ = fixture(root)
            original = root / "files/0001"
            original.rename(root / "policy")
            original.symlink_to(root / "policy")
            with patch.object(haptics, "CALIBRATION", contract), self.assertRaises(ValueError):
                haptics.verify_capture(root)

    def test_rejects_non_offline_capture_provenance(self):
        for field in ("firmware_executed", "image_mounted", "symlinks_followed"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                contract, receipt, _ = fixture(root)
                receipt[field] = True
                (root / "receipt.json").write_text(json.dumps(receipt))
                with patch.object(haptics, "CALIBRATION", contract), self.assertRaisesRegex(ValueError, "offline"):
                    haptics.verify_capture(root)

    def test_rejects_duplicate_strength_field(self):
        with self.assertRaisesRegex(ValueError, "ambiguous effect strength"):
            haptics.summarize(POLICY, CONFIG.replace(b"<low_pulse_intensity>",
                b"<low_pulse_intensity>20</low_pulse_intensity><low_pulse_intensity>"))


class DeliveryTests(unittest.TestCase):
    def test_requires_exact_unique_files_without_claiming_runtime(self):
        for variant in ("exact", "changed", "missing", "duplicate"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                contract, _, files = fixture(root)
                archive_path = root / "target-files.zip"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    for index, (path, raw) in enumerate(files.items()):
                        if index == 0 and variant == "missing":
                            continue
                        if index == 0 and variant == "changed":
                            raw = b"x" + raw[1:]
                        archive.writestr("VENDOR" + path, raw)
                        if index == 0 and variant == "duplicate":
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore", UserWarning)
                                archive.writestr("VENDOR" + path, raw)
                with patch.object(haptics, "CALIBRATION", contract):
                    if variant == "exact":
                        result = haptics.verify_delivery(archive_path)
                        self.assertTrue(result["factory_calibration_target_files_verified"])
                        self.assertFalse(result["compiled_controls_verified"])
                        self.assertFalse(result["complete_hal_delivery_verified"])
                        self.assertFalse(result["hardware_behavior_verified"])
                    else:
                        with self.assertRaises(ValueError):
                            haptics.verify_delivery(archive_path)


class SelectionTests(unittest.TestCase):
    def test_make_selection_is_explicit_and_rejects_malformed_flags(self):
        include = ROOT / "device/xiaomi/nezha/haptics.mk"
        source = (f"NEZHA_DEVICE_PATH := device/xiaomi/nezha\ninclude {include}\n"
                  "all:\n\t@echo $(DEVICE_PACKAGE_OVERLAYS)\n")
        for value in (None, "false", "true", "yes", "true false"):
            with self.subTest(value=value):
                args = ["make", "--no-print-directory", "-f", "-"]
                if value is not None:
                    args.append("NEZHA_HAPTICS_CONTROLS=" + value)
                result = subprocess.run(args, input=source, text=True, capture_output=True)
                if value in ("yes", "true false"):
                    self.assertNotEqual(result.returncode, 0)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(),
                        "device/xiaomi/nezha/haptics-overlay" if value == "true" else "")


if __name__ == "__main__":
    unittest.main()
