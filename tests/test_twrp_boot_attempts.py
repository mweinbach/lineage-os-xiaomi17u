"""Offline consistency checks for sanitized hardware-attempt metadata."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TwrpBootAttemptsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / 'research/twrp-boot-attempts.json').read_text())
        cls.milestone_bytes = (ROOT / 'research/twrp-artifact-milestone.json').read_bytes()
        cls.milestone = json.loads(cls.milestone_bytes)

    def test_static_milestone_stays_a_separate_historical_record(self):
        self.assertEqual(self.record['schema_version'], 1)
        self.assertEqual(self.record['operation'], 'twrp-authorized-temporary-boot-attempts')
        self.assertEqual(self.record['static_milestone'], {
            'sha256': hashlib.sha256(self.milestone_bytes).hexdigest(),
            'size_bytes': len(self.milestone_bytes)})
        self.assertFalse(self.milestone['unverified']['boot_tested'])
        self.assertFalse(self.milestone['phone_changed'])

    def test_first_rejection_is_not_relabelled_as_runtime_success(self):
        first = self.record['attempts'][0]
        artifact = self.milestone['artifact']
        self.assertEqual(first['image_sha256'], artifact['image_sha256'])
        self.assertEqual(first['image_size_bytes'], artifact['image_size_bytes'])
        self.assertEqual(first['ramdisk_sha256'], artifact['compressed_ramdisk_sha256'])
        self.assertEqual(first['ramdisk_size_bytes'], artifact['compressed_ramdisk_size_bytes'])
        self.assertEqual((first['header_version'], first['kernel_size_bytes']), (4, 0))
        self.assertTrue(first['download_succeeded'])
        self.assertFalse(first['boot_command_succeeded'])
        self.assertFalse(first['twrp_runtime_verified'])
        self.assertEqual(first['status'], 'bootloader_rejected')
        self.assertEqual(first['returncode'], 1)
        self.assertFalse(first['timed_out'])
        self.assertEqual(first['bootloader_error'],
                         'Failed to load/authenticate boot image: Bad Buffer Size')

    def test_authorization_and_receipts_do_not_include_device_identifiers(self):
        self.assertFalse(self.record['partition_write_command_sent'])
        self.assertEqual([a['number'] for a in self.record['attempts']],
                         list(range(1, len(self.record['attempts']) + 1)))
        for attempt in self.record['attempts']:
            self.assertEqual(attempt['operation'], 'fastboot boot')
            for name in ('partition_write_command_sent', 'unlock_or_relock_command_sent',
                         'wipe_command_sent', 'slot_change_command_sent'):
                self.assertIs(attempt[name], False)
            for receipt in attempt['evidence'].values():
                self.assertEqual(set(receipt), {'sha256', 'size_bytes'})
                self.assertRegex(receipt['sha256'], r'^[a-f0-9]{64}$')
                self.assertGreater(receipt['size_bytes'], 0)
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key, {'serial', 'selected_serial', 'device_row',
                                           'private_key', 'public_key_pem', 'argv', 'stdout', 'stderr'})
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(self.record)

    def test_live_identity_does_not_infer_region_or_hide_lock_disagreement(self):
        device = self.record['device_observations']
        self.assertEqual((device['product'], device['board']), ('nezha', 'canoe'))
        self.assertEqual(device['model'], '2512BPNDAG')
        self.assertEqual(device['adb_product_odm_device'], 'nezha')
        self.assertEqual(device['adb_product_vendor_device'], 'mivendor')
        self.assertFalse(device['physical_sales_region_verified'])
        self.assertTrue(device['android_reported_locked'])
        self.assertTrue(device['bootloader_reported_unlocked'])
        self.assertTrue(device['bootloader_reported_secure'])
        self.assertEqual(device['slot'], 'a')
        self.assertEqual(device['recovery_slot_size_bytes'], 104857600)
        self.assertEqual(device['boot_slot_size_bytes'], 100663296)


if __name__ == '__main__':
    unittest.main()
