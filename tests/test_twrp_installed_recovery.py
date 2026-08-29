"""Offline checks for the installed image and bounded runtime claims."""
import json
from pathlib import Path
import unittest


class TwrpInstalledRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'research/twrp-installed-recovery.json'
        cls.record = json.loads(path.read_text())

    def test_exact_provided_image_and_kernel_free_header_are_preserved(self):
        image = self.record['image']
        self.assertEqual(image['sha256'], '56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323')
        self.assertTrue(image['copy_bit_for_bit_verified'])
        self.assertEqual((image['size_bytes'], image['header_version'], image['kernel_size_bytes']), (104857600, 4, 0))
        self.assertEqual(image['compressed_ramdisk_size_bytes'], 75416321)
        self.assertEqual(image['compressed_ramdisk_sha256'],
                         '7e444cec10294c43097ca5e96bbba5300fb83412a6ce21aa838cb9ee32aaa3db')

    def test_disclosed_avb_failure_has_exact_authorization_without_a_bypass(self):
        self.assertEqual(self.record['authorization'], {
            'explicit_user_confirmation_received': True, 'exact_image_to_recovery_a_and_reboot_authorized': True,
            'confirmation_after_avb_disclosure': True})
        avb = self.record['image']['avb']
        self.assertEqual(avb['algorithm'], 'NONE')
        self.assertTrue(avb['verification_failure_disclosed_before_flash'])
        for key in ('embedded_hash_verification_passed', 'oem_trust_established', 'bypass_flags_used'):
            self.assertFalse(avb[key])

    def test_installation_and_live_partition_readback_match_the_user_file(self):
        install = self.record['installation']
        self.assertEqual((install['partition'], install['reboot_target']), ('recovery_a', 'recovery'))
        self.assertTrue(install['flash_succeeded'] and install['reboot_succeeded'])
        readback = install['live_partition_readback']
        self.assertTrue(readback['matches_exact_user_supplied_image'])
        self.assertEqual(readback['sha256'], self.record['image']['sha256'])

    def test_visible_ui_and_runtime_vibration_trial_preserve_input_limits(self):
        runtime = self.record['runtime']
        self.assertEqual((runtime['device'], runtime['slot_suffix'], runtime['adb_uid']), ('nezha', '_a', 0))
        self.assertEqual(runtime['twrp_version'], '3.7.1_16-Xiaomi_17_Ultra')
        self.assertEqual((runtime['recovery_service'], runtime['sys_boot_completed']), ('running', '1'))
        self.assertTrue(runtime['ui_visible'] and runtime['drm_atomic_commits_succeeded_in_recovery_log'])
        self.assertEqual((runtime['usb_state'], runtime['tcp_adb_property']), ('adb', ''))
        self.assertEqual(runtime['initial_touch_observation']['reported_latency_seconds'], [5, 10])
        self.assertTrue(runtime['touch']['responsive'] and runtime['touch']['latency_greatly_improved_reported'])
        self.assertFalse(runtime['touch']['fully_working_input_verified'])
        haptic = self.record['runtime_haptic_diagnostic']
        self.assertEqual(haptic['values_before'], {'tw_disable_haptics': 0, 'action': 160, 'button': 80, 'keyboard': 40})
        self.assertEqual(haptic['duration_values_after'], {'action': 0, 'button': 0, 'keyboard': 0})
        self.assertTrue(haptic['readback_confirmed'] and haptic['latency_greatly_improved_reported'])
        self.assertEqual(haptic['user_report'], 'oh yea way faster')
        for key in ('quantitative_latency_benchmark_performed', 'input_driver_changed', 'service_stop_commands_sent',
                    'service_restart_causality_established', 'image_or_partition_write_commands_during_runtime_tuning'):
            self.assertFalse(haptic[key])

    def test_initial_loaded_policy_is_separate_from_the_temporary_permissive_test(self):
        policy = self.record['selinux']
        initial = policy['initial_runtime_measurement']
        self.assertEqual((initial['global_getenforce'], initial['native_analysis_returncode']), ('Enforcing', 0))
        self.assertEqual(initial['permissive_domains'],
                         ['adbd', 'fastbootd', 'init', 'logd', 'postinstall', 'recovery', 'su', 'ueventd'])
        self.assertEqual(initial['loaded_policy'], {'size_bytes': 725594,
                         'sha256': '1c00fbcddf27a6ac219f851d234d86bfbd242386be851f1849977e773ddb6c18'})
        self.assertFalse(policy['all_domains_enforcing_verified'])
        diagnostic = policy['diagnostics'][0]
        self.assertEqual((diagnostic['operation'], diagnostic['scope']), ('setenforce 0', 'running_recovery_only'))
        self.assertEqual((diagnostic['returncode'], diagnostic['global_getenforce_after']), (0, 'Permissive'))
        self.assertTrue(diagnostic['user_authorized'])
        self.assertFalse(diagnostic['installed_image_modified'] or diagnostic['stock_android_modified'])
        self.assertEqual(diagnostic['touch_latency_retest'], 'partial_improvement_still_slow')

    def test_logs_are_bound_without_publishing_contents(self):
        self.assertEqual(self.record['collected_private_logs'], {
            'recovery': {'size_bytes': 89760,
                         'sha256': 'c9b8838c5b9c85854800733d76c86de774042593a652f20a4c537bb5ecb4a60b'},
            'dmesg': {'size_bytes': 580465,
                      'sha256': 'c970321738d5845f2ef3a93525730dc3b52b6c0d9bf63c4201eafbff71edee68'}})

    def test_write_scope_and_unverified_followup_are_preserved(self):
        boundaries = self.record['command_boundaries']
        self.assertTrue(boundaries['partition_write_command_sent'])
        self.assertFalse(any(value for key, value in boundaries.items() if key != 'partition_write_command_sent'))
        for key in ('data_mounted', 'decryption_verified', 'adb_authentication_verified'):
            self.assertFalse(self.record['runtime'][key])
        self.assertEqual(self.record['remaining_validation']['additional_recovery_reboot_test'], 'pending')
        candidate = self.record['persistent_configuration_candidate_at_this_checkpoint']
        self.assertFalse(candidate['flash_authorized'] or candidate['flashed'])
        self.assertTrue(candidate['original_provided75_image_and_partition_unchanged_by_runtime_tuning'])


if __name__ == '__main__':
    unittest.main()
