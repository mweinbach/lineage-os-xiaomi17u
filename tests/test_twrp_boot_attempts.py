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

    def test_scaffold_progress_does_not_hide_the_unknown_later_failure(self):
        trial = self.record['attempts'][3]
        self.assertEqual(trial['image_sha256'],
                         '4da77ae4bd8e5a30d036b23ae2e8939fada75023a16588a6f4456fce8e866093')
        self.assertEqual(trial['ramdisk_sha256'],
                         '1f1c61c9c8d473d1e9753cc971c13e0d71b23318e6080e5e9615bec7b5d196ff')
        suffix = trial['canonical_ramdisk_suffix']
        self.assertEqual(suffix['sha256'], self.milestone['artifact']['compressed_ramdisk_sha256'])
        self.assertEqual(suffix['offset_within_ramdisk_bytes'], 1037)
        self.assertTrue(suffix['unchanged'])
        self.assertEqual(trial['directory_scaffold']['directories'],
                         ['debug_ramdisk', 'dev', 'metadata', 'mnt', 'proc', 'second_stage_resources', 'sys'])
        self.assertFalse(trial['directory_scaffold']['contains_files_or_symlinks'])
        observed = trial['runtime_observations']
        for key in ('missing_first_stage_mount_points_resolved', 'vendor_module_loading_observed',
                    'monolithic_sepolicy_loading_observed', 'recovery_init_selinux_enforcing_observed',
                    'second_stage_init_started_observed', 'init_log_rate_limit_suppression_observed',
                    'bootloader_after_trial_verified', 'stock_authorized_adb_returned'):
            self.assertTrue(observed[key])
        self.assertFalse(observed['fatal_cause_identified'])
        self.assertFalse(observed['recovery_ui_verified'])
        self.assertFalse(observed['recovery_adb_verified'])
        self.assertFalse(trial['twrp_runtime_verified'])
        self.assertLess(observed['second_stage_init_started_seconds'], observed['reboot_requested_seconds'])

    def test_logging_trial_records_the_fresh_apex_failure_without_reusing_stale_logs(self):
        previous, trial = self.record['attempts'][3:5]
        self.assertEqual(trial['image_sha256'],
                         '74b1cbad15dfefcad96b0f77dbb340ae4df9461d70e28ad19a144308bb0c1bb1')
        for key in ('kernel_sha256', 'ramdisk_sha256', 'ramdisk_size_bytes',
                    'directory_scaffold', 'canonical_ramdisk_suffix', 'avb'):
            self.assertEqual(trial[key], previous[key])
        self.assertEqual(trial['diagnostic_parameter'], 'printk.devkmsg=on')
        self.assertEqual(trial['command_line_size_bytes'], 287)
        self.assertEqual(trial['command_line_sha256'],
                         'b9730753e0d94e6bc6f8b4d0af5bab77ba0b87eaa8bcb89c0135f7243c659077')
        observed = trial['runtime_observations']
        self.assertEqual((observed['fatal_mount_point'], observed['fatal_errno'], observed['fatal_signal']),
                         ('/apex', 'ENOENT', 6))
        self.assertEqual(observed['vendor_modules_loaded'], 426)
        for key in ('fatal_cause_identified', 'recovery_init_selinux_enforcing_observed',
                    'twrp_build_identity_observed', 'initial_stale_kernel_log_rejected',
                    'fresh_log_newer_than_diagnostic_reboot', 'stock_authorized_adb_returned'):
            self.assertTrue(observed[key])
        self.assertEqual(observed['fresh_log_entry_local'], '2026-08-29 00:22:41')
        self.assertEqual(observed['fresh_log_timezone'], 'America/New_York')
        self.assertNotEqual(trial['evidence']['last_kernel_log']['sha256'],
                            trial['evidence']['rejected_stale_kernel_log']['sha256'])
        self.assertFalse(trial['twrp_runtime_verified'])
        self.assertFalse(observed['recovery_ui_verified'])
        self.assertFalse(observed['recovery_adb_verified'])
        self.assertLess(observed['second_stage_init_started_seconds'], observed['fatal_signal_seconds'])
        self.assertLess(observed['fatal_signal_seconds'], observed['reboot_requested_seconds'])

    def test_empty_apex_trial_does_not_treat_missing_usb_as_runtime_success_or_failure(self):
        previous, trial = self.record['attempts'][4:6]
        self.assertEqual(trial['image_sha256'],
                         '8278aa15d2aa21e5553a332787580716e3d7b43b88ad505c73e8141e37dd9e7f')
        self.assertEqual(trial['ramdisk_sha256'],
                         '56c155fe7beed5a836faee93b48e51fe545f58cce112d136d89ba7ef15476dc2')
        for key in ('kernel_sha256', 'command_line_sha256', 'command_line_size_bytes', 'avb'):
            self.assertEqual(trial[key], previous[key])
        suffix = trial['canonical_ramdisk_suffix']
        self.assertEqual(suffix['offset_within_ramdisk_bytes'], 1551)
        self.assertEqual(suffix['sha256'], self.milestone['artifact']['compressed_ramdisk_sha256'])
        self.assertTrue(suffix['unchanged'])
        self.assertEqual(trial['directory_scaffold']['directories'],
                         ['apex', 'debug_ramdisk', 'dev', 'metadata', 'mnt', 'proc',
                          'second_stage_resources', 'sys'])
        self.assertFalse(trial['directory_scaffold']['contains_files_or_symlinks'])
        observed = trial['runtime_observations']
        self.assertEqual(observed['usb_presence_poll_count'], 20)
        self.assertGreater(observed['usb_presence_poll_span_seconds'], 57)
        for key in ('adb_seen_during_observation', 'fastboot_seen_during_observation',
                    'current_runtime_identified', 'recovery_ui_verified', 'recovery_adb_verified',
                    'apex_mount_success_verified'):
            self.assertFalse(observed[key])
        self.assertTrue(observed['source_directory_fix_is_not_runtime_proof'])
        self.assertTrue(observed['no_reboot_sent_after_this_trial'])
        self.assertFalse(trial['twrp_runtime_verified'])
        self.assertTrue(trial['boot_command_succeeded'])

    def test_prepared_usb_mount_point_candidate_is_separate_from_hardware_attempts(self):
        candidate = self.record['next_candidate']
        previous = self.record['attempts'][5]
        self.assertEqual(candidate['status'], 'constructed_verified_not_booted')
        self.assertEqual(candidate['image_sha256'],
                         '8cbc355d68750c32f1b3ba4dec1953732bd32a3924731553b16204a699ee730f')
        self.assertNotIn(candidate['image_sha256'], [trial['image_sha256'] for trial in self.record['attempts']])
        self.assertEqual(candidate['ramdisk_sha256'],
                         'dbaeab4b0cf35ea537fef9cf9a7cd10586f581ca964782d9ef63b39576f727db')
        for key in ('kernel_sha256', 'command_line_sha256', 'command_line_size_bytes',
                    'canonical_ramdisk_suffix', 'avb'):
            self.assertEqual(candidate[key], previous[key])
        self.assertEqual(candidate['directory_scaffold']['directories'],
                         ['apex', 'config', 'debug_ramdisk', 'dev', 'metadata', 'mnt',
                          'proc', 'second_stage_resources', 'sys'])
        self.assertFalse(candidate['directory_scaffold']['contains_files_or_symlinks'])
        for key in ('runtime_cause_of_missing_usb_verified', 'configfs_mount_verified',
                    'usb_runtime_verified', 'boot_command_sent', 'boot_tested',
                    'partition_write_command_sent'):
            self.assertFalse(candidate[key])
        self.assertTrue(candidate['requires_current_phone_state_resolution'])
        for receipt in candidate['evidence'].values():
            self.assertEqual(set(receipt), {'sha256', 'size_bytes'})
            self.assertRegex(receipt['sha256'], r'^[a-f0-9]{64}$')
            self.assertGreater(receipt['size_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
