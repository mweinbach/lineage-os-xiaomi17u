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

    def test_v4_wrapper_acceptance_does_not_claim_twrp_runtime(self):
        wrapper = self.record['attempts'][1]
        self.assertEqual(wrapper['image_sha256'],
                         '70c2d3ab2aee6c216a2c8d6a38d05ddeb76b1e3313a3602d3a2f1fdc1a155de2')
        self.assertEqual((wrapper['header_version'], wrapper['header_size_bytes']), (4, 1584))
        self.assertEqual(wrapper['image_size_bytes'], 100663296)
        self.assertEqual(wrapper['kernel_size_bytes'], 39963136)
        self.assertEqual(wrapper['ramdisk_sha256'], self.milestone['artifact']['compressed_ramdisk_sha256'])
        self.assertTrue(wrapper['download_succeeded'])
        self.assertTrue(wrapper['boot_command_succeeded'])
        self.assertEqual(wrapper['returncode'], 0)
        self.assertFalse(wrapper['twrp_runtime_verified'])
        self.assertEqual(wrapper['status'], 'boot_command_accepted_stock_android_observed')
        avb = wrapper['avb']
        self.assertEqual((avb['partition_name'], avb['algorithm'], avb['flags']),
                         ('boot', 'SHA256_RSA4096', 0))
        self.assertEqual((avb['rollback_index'], avb['rollback_index_location']), (1769904000, 0))
        self.assertTrue(avb['local_development_signature_verified'])
        self.assertFalse(avb['oem_signature'])
        self.assertEqual(avb['properties'], {'com.android.build.boot.os_version': '16',
                                           'com.android.build.boot.security_patch': '2026-02-01'})
        runtime = wrapper['runtime_observations']
        self.assertEqual(runtime['sys_boot_completed'], '1')
        for name in ('zygote_running', 'system_server_running', 'surfaceflinger_running'):
            self.assertTrue(runtime[name])
        self.assertFalse(runtime['twrp_version_property_present'])
        self.assertFalse(runtime['recovery_service_present'])
        self.assertFalse(runtime['proc_cmdline_read_permitted'])
        self.assertFalse(runtime['proc_bootconfig_read_permitted'])

    def test_v3_trial_preserves_measured_first_stage_abort(self):
        trial = self.record['attempts'][2]
        self.assertEqual(trial['image_sha256'],
                         'f8c2a3696036faea4401dacfabcde5ad092bb9b56adeffb9444f5d4adae52118')
        self.assertEqual((trial['header_version'], trial['header_size_bytes']), (3, 1580))
        self.assertEqual(trial['ramdisk_sha256'], self.milestone['artifact']['compressed_ramdisk_sha256'])
        self.assertTrue(trial['boot_command_succeeded'])
        self.assertFalse(trial['twrp_runtime_verified'])
        self.assertEqual(trial['status'], 'boot_command_accepted_first_stage_abort_then_stock_android')
        observed = trial['runtime_observations']
        self.assertTrue(observed['stock_android_boot_completed'])
        self.assertTrue(observed['saved_log_first_stage_abort_observed'])
        self.assertTrue(observed['last_kernel_log_available_via_android_dropbox'])
        self.assertTrue(observed['saved_log_contains_some_corrupted_characters'])
        self.assertFalse(observed['direct_pstore_read_permitted'])
        self.assertLess(observed['saved_log_init_started_seconds'], observed['saved_log_abort_seconds'])
        self.assertLess(observed['saved_log_abort_seconds'], observed['saved_log_reboot_seconds'])


if __name__ == '__main__':
    unittest.main()
