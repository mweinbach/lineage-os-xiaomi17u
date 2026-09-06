"""Offline negative checks for the exact-stock power-input evidence reader."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts import power_inputs as power


PROFILE = '''E: device (line=1)
  A: name="Android" (Raw: "Android")
    E: item (line=2)
      A: name="battery.capacity" (Raw: "battery.capacity")
        T: '1000'
    E: array (line=3)
      A: name="cpu.clusters.cores" (Raw: "cpu.clusters.cores")
        E: value (line=4)
            T: '1'
    E: array (line=5)
      A: name="cpu.speeds.cluster0" (Raw: "cpu.speeds.cluster0")
        E: value (line=6)
            T: '400000'
    E: item (line=7)
      A: name="screen.on.display0" (Raw: "screen.on.display0")
        T: '0.1'
'''
SEAPP = 'user=_app seinfo=platform name=com.qualcomm.qti.workloadclassifier domain=vendor_wlc_app type=app_data_file levelFrom=all'
CONTEXTS = '''vendor.perf.workloadclassifier.enable u:object_r:vendor_wlc_prop:s0
persist.vendor.build.date.utc u:object_r:vendor_wlc_prop:s0
vendor.mpctl.init.complete u:object_r:vendor_wlc_public_prop:s0
'''


class PowerEvidenceTests(unittest.TestCase):
    def test_placeholder_is_not_admitted_as_calibration(self):
        result = power.profile_findings(power.decode_tree(PROFILE))
        self.assertTrue(result['placeholder_detected'])
        self.assertFalse(result['calibrated_nezha_profile_admitted'])

    def test_nonplaceholder_is_not_sufficient_for_admission(self):
        result = power.profile_findings(power.decode_tree(PROFILE.replace("'1000'", "'6000'")))
        self.assertFalse(result['placeholder_detected'])
        self.assertFalse(result['calibrated_nezha_profile_admitted'])

    def test_duplicate_profile_component_rejected(self):
        tree = power.decode_tree(PROFILE)
        tree.append(ET.fromstring('<item name="battery.capacity">1000</item>'))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            power.profile_findings(tree)

    def test_nonfinite_negative_and_malformed_values_rejected(self):
        for bad in ['NaN', 'inf', '-0.1', 'nonsense']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                power.profile_findings(power.decode_tree(PROFILE.replace("'0.1'", repr(bad))))

    def test_decoder_preserves_manifest_attribute_owner(self):
        raw = '''N: android=http://schemas.android.com/apk/res/android (line=1)
  E: manifest (line=1)
    A: package="com.miui.powerkeeper" (Raw: "com.miui.powerkeeper")
    A: http://schemas.android.com/apk/res/android:sharedUserId(0x0101000b)="android.uid.system" (Raw: "android.uid.system")
      E: uses-permission (line=2)
        A: http://schemas.android.com/apk/res/android:name(0x01010003)="example" (Raw: "example")
'''
        root = power.decode_tree(raw)
        self.assertEqual(root.get('sharedUserId'), 'android.uid.system')
        self.assertIsNone(root.get('name'))
        self.assertEqual(root[0].get('name'), 'example')

    def test_unknown_decoder_output_fails_closed(self):
        for raw in [PROFILE + 'warning: invalid\n', 'T: \'orphan\'\n', PROFILE + PROFILE]:
            with self.subTest(raw=raw[-30:]), self.assertRaises(ValueError):
                power.decode_tree(raw)

    def test_wlc_is_workload_classifier_not_charging(self):
        result = power.wlc_findings(SEAPP, CONTEXTS, ET.fromstring('<manifest package="com.qualcomm.qti.workloadclassifier"/>'))
        self.assertEqual(result['meaning'], 'Qualcomm workload classifier')
        self.assertFalse(result['wireless_or_reverse_charging_support_inferred'])

    def test_wlc_package_and_context_drift_rejected(self):
        for seapp, contexts, name in [
            (SEAPP.replace('workloadclassifier', 'charger'), CONTEXTS, 'com.qualcomm.qti.workloadclassifier'),
            (SEAPP, CONTEXTS + 'vendor.charge.enable u:object_r:vendor_wlc_prop:s0\n', 'com.qualcomm.qti.workloadclassifier'),
            (SEAPP, CONTEXTS, 'com.example.charger')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                power.wlc_findings(seapp, contexts, ET.fromstring(f'<manifest package="{name}"/>'))

    def test_capture_hash_binding_and_path_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            group = root / 'system-ext'
            (group / 'files').mkdir(parents=True)
            (group / 'files/0001').write_bytes(b'exact captured content')
            pin = power.identity(b'exact captured content')
            contract = {'system_ext_image_sha256': 'a' * 64,
                        'captures': {'system-ext': {'/etc/test': pin}}}
            row = {'path': '/etc/test', 'output_path': 'files/0001', 'type': 'regular',
                   'readback_verified': True, **pin}
            receipt = {'operation': 'erofs-capture', 'image': {'sha256': 'a' * 64},
                       'image_mounted': False, 'firmware_executed': False, 'files': [row]}
            receipt_path = group / 'receipt.json'
            receipt_path.write_text(json.dumps(receipt))
            self.assertEqual(power.capture_files(power.Reader(), root, contract)['/etc/test'][1], b'exact captured content')
            for bad in ['../outside', '/absolute', 'files/../0001']:
                row['output_path'] = bad
                receipt_path.write_text(json.dumps(receipt))
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    power.capture_files(power.Reader(), root, contract)
            row['output_path'] = 'files/0001'
            receipt_path.write_text(json.dumps(receipt))
            (group / 'files/0001').write_bytes(b'changed captured data!')
            with self.assertRaisesRegex(ValueError, 'hash or size'):
                power.capture_files(power.Reader(), root, contract)


if __name__ == '__main__':
    unittest.main()
