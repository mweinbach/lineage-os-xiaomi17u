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
UPSTREAM_ICON_WIDTH_UM = 6000  # the fixed upstream default the overlay replaces


class NezhaUdfpsGeometryTests(unittest.TestCase):
    def _float_dimen(self, name):
        matches = [item for item in ET.parse(OVERLAY).getroot() if item.get("name") == name]
        self.assertEqual(len(matches), 1, name)
        item = matches[0]
        self.assertEqual(item.get("format"), "float", name)
        # Either declaration form resolves to a float dimen resource.
        if item.tag == "item":
            self.assertEqual(item.get("type"), "dimen", name)
        else:
            self.assertEqual(item.tag, "dimen", name)
        return float(item.text)

    def pitch(self):
        return self._float_dimen("pixel_pitch")

    def icon_um(self):
        return self._float_dimen("udfps_icon_size")

    def test_resource_is_a_positive_physical_pitch_float(self):
        pitch = self.pitch()
        self.assertGreater(pitch, 0)
        self.assertAlmostEqual(pitch, 25400 / PANEL_X_DPI, delta=0.001)
        self.assertAlmostEqual(pitch, 25400 / PANEL_Y_DPI, delta=0.001)
        # A negative upstream default would place padding beyond the sensor and
        # invert the content box, so the resource has to stay a positive pitch.
        self.assertGreater(abs(pitch - 25400 / 480), 5,
                           "logical display density must not become physical pitch")

    def test_icon_is_larger_than_upstream_and_still_fits_the_sensor(self):
        # Consumer contract: truncate icon pixels, then integer-divide native padding.
        pitch = self.pitch()
        icon_um = self.icon_um()
        icon_pixels = int(icon_um / pitch)
        native_padding = (SENSOR_WIDTH_PX - icon_pixels) // 2
        upstream_pixels = int(UPSTREAM_ICON_WIDTH_UM / pitch)
        self.assertEqual(upstream_pixels, 99)  # what the 6 mm default drew
        self.assertGreater(icon_pixels, upstream_pixels, "the overlay is meant to enlarge the icon")
        # The selected 8 mm icon: 132 px with 8 px of padding per side.
        self.assertEqual(icon_um, 8000)
        self.assertEqual(icon_pixels, 132)
        self.assertEqual(native_padding, 8)
        # It must never exceed the sensor, or the padding clamps to zero and the icon clips.
        self.assertLessEqual(icon_pixels, SENSOR_WIDTH_PX)
        self.assertGreaterEqual(native_padding, 0)
        self.assertLess(icon_um, SENSOR_WIDTH_PX * pitch)
        for scale in (1.0, 0.9, 0.75):
            padding = max(0, int(native_padding * scale))
            view_width = int(SENSOR_WIDTH_PX * scale)
            visible_width = view_width - 2 * padding
            with self.subTest(scale=scale):
                self.assertGreater(visible_width, 0)
                self.assertLess(2 * padding, view_width)
                # Integer rounding may leave up to two scaled pixels extra.
                self.assertLess(abs(visible_width / scale * pitch - icon_um), 200)


if __name__ == "__main__":
    unittest.main()
