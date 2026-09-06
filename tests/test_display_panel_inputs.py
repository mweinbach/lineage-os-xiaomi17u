"""Synthetic, offline validation of panel mapping, publication and build guards."""
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import warnings
import xml.etree.ElementTree as ET
import zipfile

from scripts import display_panel_inputs as panel


def array(name, values):
    return f"    resource 0x7f010000 array/{name}\n      () (array) size={len(values)}\n        [{', '.join(map(str, values))}]\n"


def scalar(kind, name, value):
    return f"    resource 0x7f020000 {kind}/{name}\n      () {value}\n"


def fixture():
    points = [(Decimal(i) / 10, i * 100) for i in range(1, 10)]
    xml = "<displayConfiguration><screenBrightnessMap>" + "".join(
        f"<point><value>{v}</value><nits>{n}</nits></point>" for v, n in points)
    xml += "</screenBrightnessMap><highBrightnessMode enabled='true'><transitionPoint>0.5</transitionPoint></highBrightnessMode></displayConfiguration>"
    dump = array("config_autoBrightnessLevels", range(1, 133))
    dump += array("config_autoBrightnessDisplayValuesNits", range(0, 1330, 10))
    values = {"config_screenBrightnessSettingMinimumFloat": "0.1",
              "config_screenBrightnessSettingDefaultFloat": "0.2"}
    for name, value in values.items():
        dump += scalar("dimen", name, value)
    for name in ("config_autoBrightnessBrighteningLightDebounce", "config_autoBrightnessDarkeningLightDebounce"):
        dump += scalar("integer", name, "1000")
    common = scalar("bool", "config_automatic_brightness_available", "true")
    target = ET.Element("resources")
    ET.SubElement(target, "bool", name="config_automatic_brightness_available")
    for name in (*values, "config_screenBrightnessSettingMaximumFloat", "config_screenBrightnessDimFloat"):
        ET.SubElement(target, "item", name=name, type="dimen", format="float")
    for name in ("config_autoBrightnessBrighteningLightDebounce", "config_autoBrightnessDarkeningLightDebounce"):
        ET.SubElement(target, "integer", name=name)
    ET.SubElement(target, "integer-array", name="config_autoBrightnessLevels")
    ET.SubElement(target, "array", name="config_autoBrightnessDisplayValuesNits")
    return xml.encode(), dump, common, ET.tostring(target)


class MappingTests(unittest.TestCase):
    def test_cap_normalization_and_auto_plateau(self):
        files, details = panel.calibration(*fixture())
        self.assertEqual(details["normal_nits_ceiling"], "500")
        self.assertEqual(details["normalized_default"], "0.25")
        # AOSP DDC maps normalized 0..1 to the constrained HAL range.
        low, high, original_default = Decimal("0.1"), Decimal("0.5"), Decimal("0.2")
        self.assertEqual(low + Decimal(details["normalized_default"]) * (high - low), original_default)
        self.assertEqual(low + Decimal(1) * (high - low), high)
        xml = ET.fromstring(files[panel.DISPLAY])
        self.assertIsNone(xml.find("highBrightnessMode"))
        self.assertEqual(len(xml.findall("screenBrightnessMap/point")), 9)
        overlay = ET.fromstring(files[panel.OVERLAY])
        nits = overlay.find("array[@name='config_autoBrightnessDisplayValuesNits']")
        values = [Decimal(e.text) for e in nits]
        self.assertEqual(len(values), 133)
        self.assertEqual(max(values), 500)
        self.assertEqual(values[-1], values[-2])
        self.assertTrue(all("." in e.text for e in nits))
        self.assertIsNone(overlay.find("integer-array[@name='config_autoBrightnessLcdBacklightValues']"))

    def test_rejects_nonmonotonic_lux(self):
        xml, dump, common, target = fixture()
        with self.assertRaisesRegex(ValueError, "invalid auto"):
            panel.calibration(xml, dump.replace("[1, 2, 3,", "[1, 1, 3,"), common, target)

    def test_rejects_wrong_target_resource_type(self):
        xml, dump, common, target = fixture()
        with self.assertRaisesRegex(ValueError, "incompatible"):
            panel.calibration(xml, dump, common, target.replace(b"<bool", b"<integer"))

    def test_rejects_ambiguous_resource(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            panel.resource(scalar("bool", "test", "true") * 2, "bool", "test")

    def test_rejects_out_of_range_default(self):
        xml, dump, common, target = fixture()
        with self.assertRaisesRegex(ValueError, "constraints"):
            panel.calibration(xml, dump.replace("() 0.2", "() 0.8"), common, target)

    def test_private_output_must_be_in_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "ignored artifacts"):
                panel.prepare(Path(directory), Path(directory) / "public")

    def test_wrong_input_hash_fails_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "artifacts").mkdir()
            (root / "bad").write_bytes(b"bad")
            with patch.object(panel, "ROOT", root), patch.object(panel, "INPUTS", {"bad": "0" * 64}):
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    panel.prepare(root, root / "artifacts" / "packet")
            self.assertFalse((root / "artifacts" / "packet").exists())

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "artifacts").mkdir()
            (root / "actual").write_bytes(b"bytes")
            (root / "link").symlink_to(root / "actual")
            with patch.object(panel, "ROOT", root), patch.object(panel, "INPUTS", {"link": panel.sha(b"bytes")}):
                with self.assertRaises(ValueError):
                    panel.prepare(root, root / "artifacts" / "packet")


class DeliveryTests(unittest.TestCase):
    def check_archive(self, duplicate=False, contents=b"fixture"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            raw = b"fixture"
            (root / panel.DISPLAY).write_bytes(raw)
            hashes = {panel.DISPLAY: panel.sha(raw)}
            (root / "display-panel-inputs.json").write_text(json.dumps({"contract": "nezha-normal-brightness-v1", "inputs": panel.INPUTS, "outputs": hashes}))
            archive = root / "target.zip"
            with zipfile.ZipFile(archive, "w") as z, warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("PRODUCT/etc/displayconfig/" + panel.DISPLAY, contents)
                if duplicate:
                    z.writestr("PRODUCT/etc/displayconfig/" + panel.DISPLAY, contents)
            with patch.object(panel, "OUTPUT_HASHES", hashes):
                return panel.verify_delivery(archive, root)

    def test_exact_delivery(self):
        self.assertTrue(self.check_archive()["target_files_panel_delivered"])

    def test_wrong_bytes(self):
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.check_archive(contents=b"changed")

    def test_duplicate_archive_member(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check_archive(duplicate=True)


class MakeTests(unittest.TestCase):
    def run_make(self, value):
        include = panel.ROOT / "device/xiaomi/nezha/display-panel.mk"
        # Mirror inherit-product's mandatory-include behavior without Android.
        text = ("inherit-product = $(eval include $(1))\n"
                f"NEZHA_CALIBRATED_DISPLAY := {value}\ninclude {include}\nall:\n\t@true\n")
        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(["make", "-f", "-", "all"], input=text, cwd=directory,
                                  text=True, capture_output=True)

    def test_unset_and_false_skip_packet(self):
        for value in ("", "false"):
            self.assertEqual(self.run_make(value).returncode, 0)

    def test_true_requires_packet(self):
        for value in ("true", "true "):
            result = self.run_make(value)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("display-product.mk", result.stderr)

    def test_invalid_and_multiword_fail(self):
        for value in ("tru", "true false", "true true", "false true"):
            result = self.run_make(value)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("NEZHA_CALIBRATED_DISPLAY", result.stderr)


if __name__ == "__main__":
    unittest.main()
