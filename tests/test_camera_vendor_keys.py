"""Check the scoped selection and recompute the vendor-key patch evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'config/nezha-camera-vendor-keys.json'
FRAGMENT = ROOT / 'device/xiaomi/nezha/camera-vendor-keys.mk'


class CameraVendorKeySelectionTests(unittest.TestCase):
    def select(self, selector=None, **overrides):
        make = shutil.which('make')
        if not make:
            self.skipTest('host Make unavailable')
        values = {'NEZHA_CAMERA_VENDOR_KEYS': selector, 'TARGET_PRODUCT': 'lineage_nezha',
                  'TARGET_DEVICE': 'nezha', 'NEZHA_DEVICE_PATH': 'device/xiaomi/nezha',
                  'NEZHA_CAMERA_FRAMEWORK': 'true', 'NEZHA_XIAOMI_CAMERA': 'true',
                  'NEZHA_CAMERA_PLATFORM_SIGNED': 'true', 'PRODUCT_PACKAGE_OVERLAYS': 'existing'}
        values.update(overrides)
        body = ''.join(f'{key} := {value}\n' for key, value in values.items() if value is not None)
        body += f"include {FRAGMENT}\nall:\n\t@printf '%s\\n' '$(PRODUCT_PACKAGE_OVERLAYS)'\n"
        return subprocess.run([make, '--no-print-directory', '-f', '-'], input=body,
                              text=True, capture_output=True, timeout=10,
                              env={'PATH': '/usr/bin:/bin'})

    def test_default_and_false_preserve_existing_product(self):
        for value in (None, '', ' ', 'false', ' false '):
            with self.subTest(value=value):
                r = self.select(value, NEZHA_CAMERA_FRAMEWORK='false', TARGET_PRODUCT='other')
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), 'existing')

    def test_enabled_only_adds_the_reviewed_overlay(self):
        for device in ('nezha', '', None):
            with self.subTest(device=device):
                r = self.select(' true ', TARGET_DEVICE=device)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.split(), [
                    'existing', 'device/xiaomi/nezha/camera-vendor-keys/overlay'])

    def test_malformed_selection_fails(self):
        for value in ('yes', '1', 'TRUE', 'true true', 'true false', 'false false'):
            with self.subTest(value=value):
                r = self.select(value)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('NEZHA_CAMERA_VENDOR_KEYS', r.stderr)
                self.assertEqual(r.stdout, '')

    def test_missing_prerequisites_fail(self):
        for key in ('NEZHA_CAMERA_FRAMEWORK', 'NEZHA_XIAOMI_CAMERA', 'NEZHA_CAMERA_PLATFORM_SIGNED'):
            for value in (None, '', 'false', 'yes', 'true true'):
                with self.subTest(key=key, value=value):
                    r = self.select('true', **{key: value})
                    self.assertNotEqual(r.returncode, 0)
                    self.assertIn(key + '=true', r.stderr)
                    self.assertEqual(r.stdout, '')

    def test_wrong_product_or_device_fails(self):
        for key, values in [('TARGET_PRODUCT', (None, '', 'other', 'lineage_nezha other')),
                            ('TARGET_DEVICE', ('other', 'nezha other'))]:
            for value in values:
                with self.subTest(key=key, value=value):
                    r = self.select('true', **{key: value})
                    self.assertNotEqual(r.returncode, 0)
                    self.assertIn(key, r.stderr)

    def test_patch_hash_and_new_class_recomputed(self):
        contract = json.loads(CONTRACT.read_text())
        for path_key, hash_key in (('fragment', 'fragment_sha256'),
                                   ('patch', 'patch_sha256'), ('template', 'template_sha256')):
            self.assertEqual(hashlib.sha256((ROOT / contract[path_key]).read_bytes()).hexdigest(),
                             contract[hash_key])
        patch = (ROOT / contract['patch']).read_text()
        java_path = 'core/java/android/hardware/camera2/impl/NezhaCameraVendorKeyCompat.java'
        section = patch.split('diff --git a/' + java_path + ' b/' + java_path + '\n', 1)[1]
        self.assertIn('--- /dev/null\n', section)
        emitted = ''.join(line[1:] for line in section.splitlines(True)
                          if line.startswith('+') and not line.startswith('+++'))
        self.assertEqual(emitted, (ROOT / contract['template']).read_text())
        self.assertEqual(hashlib.sha256(emitted.encode()).hexdigest(),
                         contract['files'][java_path]['after_sha256'])
        self.assertEqual(len(emitted.encode()), contract['files'][java_path]['after_bytes'])

    def test_resource_selection_matches_compiled_symbol_and_defaults_off(self):
        contract = json.loads(CONTRACT.read_text())
        patch = (ROOT / contract['patch']).read_text()
        added = ''.join(line[1:] for line in patch.splitlines(True)
                        if line.startswith('+') and not line.startswith('+++'))
        name = contract['resource']
        # These are build-decision pins: an enabled framework default would apply
        # without the product selector; a missing symbol would not compile.
        self.assertIn(f'<bool name="{name}">false</bool>', added)
        self.assertNotIn(f'<bool name="{name}">true</bool>', added)
        self.assertIn(f'<java-symbol type="bool" name="{name}" />', added)
        overlay = ET.parse(ROOT / ('device/xiaomi/nezha/camera-vendor-keys/overlay/'
                                   'frameworks/base/core/res/res/values/config.xml'))
        self.assertEqual([(node.tag, node.get('name'), node.text) for node in overlay.getroot()],
                         [('bool', name, 'true')])
        self.assertIn('com.android.internal.R.bool.' + name,
                      (ROOT / contract['template']).read_text())


if __name__ == '__main__':
    unittest.main()
