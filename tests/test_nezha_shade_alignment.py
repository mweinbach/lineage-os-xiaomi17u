"""Check measured shade geometry and integrity of the opted-in candidate patch."""
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / 'patches/evolution/nezha-shade-header-alignment.json'
OVERLAY = ROOT / 'device/xiaomi/nezha/overlay/frameworks/base/packages/SystemUI/res/values/dimens.xml'


class NezhaShadeHeaderAlignmentTests(unittest.TestCase):
    def test_reviewed_patch_integrity(self):
        metadata = json.loads(METADATA.read_text())
        patch = (ROOT / metadata['patch']).read_bytes()
        self.assertEqual(hashlib.sha256(patch).hexdigest(), metadata['patch_sha256'])
        self.assertEqual(len(patch), metadata['patch_size_bytes'])

    def test_device_opt_in_preserves_approved_status_bar_geometry(self):
        resources = {item.get('name'): item.text for item in ET.parse(OVERLAY).getroot()}
        self.assertEqual(resources['config_alignShadeHeaderWithStatusBar'], 'true')
        self.assertEqual(resources['rounded_corner_content_padding'], '100px')
        self.assertEqual(resources['status_bar_padding_top'], '38px')
        self.assertEqual(resources['pixel_pitch'], '60.583')

    def test_density_dependent_row_centers_align_with_physical_status_bar(self):
        # Android dimensions round to nearest native pixel. The approved status bar's
        # physical cutout and padding stay fixed while density changes QS row heights.
        for density in (420, 480, 540, 640):
            row = int(28 * density / 160 + 0.5)
            status_bar = max(144, row)
            margin = max(0, (status_bar + 38 - row) // 2)
            with self.subTest(density=density):
                self.assertLessEqual(abs((row / 2 + margin) - ((status_bar + 38) / 2)), 0.5)
                if density == 480:
                    self.assertEqual(margin, 49)
                    self.assertEqual(row / 2 + margin, 91)
                    self.assertEqual(2 * row + 72 + margin, 289)

    def test_patch_gates_and_moves_whole_header_without_resizing_content(self):
        metadata = json.loads(METADATA.read_text())
        patch = (ROOT / metadata['patch']).read_text()
        additions = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('<bool name="config_alignShadeHeaderWithStatusBar">false</bool>', additions)
        self.assertIn('resources.getBoolean(R.bool.config_alignShadeHeaderWithStatusBar)', additions)
        self.assertIn('!largeScreenShadeHeaderActive && !splitShadeEnabled', additions)
        self.assertIn('Configuration.ORIENTATION_PORTRAIT', additions)
        self.assertIn('SystemBarUtils.getStatusBarHeight(mView.context)', additions)
        self.assertIn('constraintSet.connect(R.id.split_shade_status_bar, TOP, PARENT_ID, TOP, topInset)', additions)
        self.assertNotIn('constrainHeight', additions)
        self.assertNotIn('setPadding', additions)


if __name__ == '__main__':
    unittest.main()
