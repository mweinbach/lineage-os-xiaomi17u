"""Check the device's physical UDFPS icon sizing contract without a phone."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "device/xiaomi/nezha/overlay/frameworks/base/packages/SystemUI/res/values/dimens.xml"
# Exact installed-device display capture; physical DPI, not logical density480.
PANEL_X_DPI = 419.25723
PANEL_Y_DPI = 419.26074
SENSOR_WIDTH_PX = 148
ICON_WIDTH_UM = 6000


class NezhaUdfpsGeometryTests(unittest.TestCase):
    def pitch(self):
        matches = [item for item in ET.parse(OVERLAY).getroot() if item.get("name") == "pixel_pitch"]
        self.assertEqual(len(matches), 1)
        item = matches[0]
        self.assertEqual(item.tag, "item")
        self.assertEqual(item.get("format"), "float")
        self.assertEqual(item.get("type"), "dimen")
        return float(item.text)

    def test_resource_is_a_positive_physical_pitch_float(self):
        pitch = self.pitch()
        self.assertGreater(pitch, 0)
        self.assertAlmostEqual(pitch, 25400 / PANEL_X_DPI, delta=0.001)
        self.assertAlmostEqual(pitch, 25400 / PANEL_Y_DPI, delta=0.001)
        self.assertGreater(abs(pitch - 25400 / 480), 5,
                           "logical display density must not become physical pitch")

    def test_six_millimetre_icon_fits_sensor_without_excessive_padding(self):
        # Consumer contract: truncate icon pixels, then integer-divide native padding.
        pitch = self.pitch()
        icon_pixels = int(ICON_WIDTH_UM / pitch)
        native_padding = (SENSOR_WIDTH_PX - icon_pixels) // 2
        self.assertEqual(icon_pixels, 99)
        self.assertEqual(native_padding, 24)
        for scale in (1.0, 0.9, 0.75):
            padding = max(0, int(native_padding * scale))
            view_width = int(SENSOR_WIDTH_PX * scale)
            visible_width = view_width - 2 * padding
            with self.subTest(scale=scale):
                self.assertGreater(visible_width, 0)
                self.assertLess(2 * padding, view_width)
                # Integer rounding may leave up to two scaled pixels extra.
                self.assertLess(abs(visible_width / scale * pitch - ICON_WIDTH_UM), 200)

    def test_unspecified_upstream_pitch_reproduces_invalid_content_box(self):
        icon_pixels = int(ICON_WIDTH_UM / -1)
        padding = max(0, (SENSOR_WIDTH_PX - icon_pixels) // 2)
        self.assertEqual(padding, 3074)
        self.assertLess(SENSOR_WIDTH_PX - 2 * padding, 0)


if __name__ == "__main__":
    unittest.main()
