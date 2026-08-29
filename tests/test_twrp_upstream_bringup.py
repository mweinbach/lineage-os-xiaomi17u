"""Offline checks for the separate, sanitized upstream-prebuilt experiment."""
import json
from pathlib import Path
import unittest


class TwrpUpstreamBringupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'research/twrp-upstream-bringup.json'
        cls.record = json.loads(path.read_text())

    def test_origin_is_pinned_supplied_prebuilts_not_a_new_source_build(self):
        self.assertEqual(self.record['schema_version'], 1)
        source = self.record['upstream']
        self.assertEqual(source['repository'],
                         'https://github.com/antocorvo3000/twrp-xiaomi-17-series')
        self.assertEqual(source['commit'], '4a35185d43782b4dd460a7f456d674c0976c0859')
        self.assertEqual(source['device_subtree'], 'twrp_device_xiaomi_nezha')
        self.assertEqual(source['device_tree_object'], 'cb570a1fe74c49f0698890bafa27df1b264e4785')
        self.assertEqual(source['runtime_origin'], 'supplied_full_prebuilt_root')
        self.assertFalse(source['runtime_newly_compiled'])
        self.assertTrue(source['normal_source_build_overlays_prebuilt_binaries'])
        self.assertFalse(source['equivalent_to_completed_normal_source_build'])

    def test_candidate_sizes_and_hashes_bind_the_actual_repacked_inputs(self):
        candidate = self.record['candidate']
        self.assertEqual(candidate['name'], 'upstream74')
        self.assertEqual(candidate['header_version'], 3)
        expected = {
            'image': (100663296, '53cf3a0eb9f295b40151672fb294f364e9ea9dc6c0f5b24698c0afc1bbabdc2d'),
            'kernel': (39963136, '4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8'),
            'compressed_ramdisk': (59123004, 'a6ceea850eb41035d32eba6cdc1b73749adb4fe4ae56c92ea50bd5e428b8636f'),
            'cpio': (133846272, '0476863f85659c57335a7f6908dac26c87013ea08adf18b53fe08804329ccb87'),
        }
        for name, (size, digest) in expected.items():
            with self.subTest(input=name):
                self.assertEqual(candidate[name]['size_bytes'], size)
                self.assertEqual(candidate[name]['sha256'], digest)
        self.assertEqual(candidate['kernel']['origin'], 'matching_stock')
        self.assertEqual(candidate['cpio']['entry_count'], 3992)

    def test_root_repairs_and_metadata_do_not_claim_prebuilt_patch_coverage(self):
        changed = self.record['adaptations']
        directories = changed['restored_empty_root_directories']
        self.assertEqual(len(directories), len(set(directories)))
        self.assertEqual(set(directories), set(
            'apex bluetooth bootstrap-apex config data data_mirror debug_ramdisk dev '
            'dsp firmware metadata mnt oem persist postinstall proc second_stage_resources '
            'soccp storage sys system_dlkm tmp acct batinfo'.split()))
        self.assertEqual(changed['restored_aliases'],
                         {'/sdcard': '/storage/self/primary', '/cache': '/data/cache'})
        self.assertEqual(changed['unchanged_source_aliases'],
                         {'/init': '/system/bin/init', '/etc': '/system/etc'})
        self.assertTrue(changed['mksh_rc_restored'])
        self.assertTrue(changed['selected_tree_fstab_copied'])
        props = changed['prop_default']
        self.assertEqual((props['device'], props['board'], props['android_version']),
                         ('nezha', 'canoe', '16'))
        self.assertEqual(props['ro.build.version.security_patch'], '2026-07-01')
        self.assertEqual(props['ro.vendor.build.security_patch'], '2026-02-01')
        self.assertTrue(props['security_patch_values_from_selected_stock_phone'])
        self.assertTrue(props['synthetic_platform_and_future_patch_values_replaced'])
        self.assertFalse(props['prebuilt_security_patch_coverage_verified'])

    def test_signature_and_static_checks_are_not_oem_or_hardware_proof(self):
        avb = self.record['candidate']['avb']
        self.assertEqual((avb['partition_name'], avb['flags'], avb['rollback_index'],
                          avb['rollback_index_location']), ('boot', 0, 1769904000, 0))
        self.assertEqual(avb['signing_key_role'], 'existing_local_development_key')
        self.assertEqual(avb['public_key_sha256'],
                         '020d7559b8ddedf153e77cc4a02af26c666e3746408a230650ef8cd1e8f09b03')
        self.assertFalse(avb['oem_signature'])
        self.assertFalse(avb['oem_trust_established'])
        checks = self.record['static_validation']
        for key in ('native_compression_round_trip_passed', 'development_key_signature_verified',
                    'boot_avb_digest_verified'):
            self.assertTrue(checks[key])
        self.assertEqual(checks['unchanged_critical_payload_checks_passed'], 8)
        self.assertEqual(checks['unchanged_critical_payload_checks_expected'], 8)
        self.assertFalse(checks['hardware_success_implied'])

    def test_permissive_authorization_is_explicit_and_does_not_claim_a_stock_change(self):
        security = self.record['authorization_and_security']
        self.assertTrue(security['user_authorized_recovery_only_permissive_trial'])
        self.assertEqual(security['recovery_kernel_parameter'], 'androidboot.selinux=permissive')
        self.assertEqual(security['source_policy_permissive_domain_count'], 8)
        self.assertEqual(security['stock_selinux_before_trial'], 'Enforcing')
        self.assertIsNone(security['stock_selinux_after_trial'])
        self.assertTrue(security['magisk_work_deferred'])
        for key in ('magisk_install_performed', 'partition_write_command_sent', 'flash_command_sent',
                    'wipe_command_sent', 'unlock_or_relock_command_sent', 'slot_change_command_sent'):
            self.assertFalse(security[key])

    def test_black_screen_and_missing_usb_do_not_prove_a_crash_or_recovery_stage(self):
        observed = self.record['hardware_observation']
        self.assertEqual(observed['trial_number'], 8)
        self.assertEqual(observed['operation'], 'fastboot boot')
        self.assertTrue(observed['download_succeeded'])
        self.assertTrue(observed['boot_command_succeeded'])
        self.assertEqual(observed['status'],
                         'boot_command_accepted_black_screen_no_adb_or_fastboot_observed')
        self.assertTrue(observed['bounded_observation_completed'])
        self.assertEqual((observed['screen_source'], observed['screen']), ('user_report', 'black'))
        self.assertEqual(observed['selected_transport_poll_count'], 27)
        self.assertEqual(observed['selected_transport_poll_span_seconds'], 55.73)
        for key in ('recovery_runtime_verified', 'recovery_ui_verified', 'recovery_adb_verified',
                    'recovery_ui_reported_visible', 'adb_seen_during_observation',
                    'fastboot_seen_during_observation', 'qualcomm_usb_device_observed',
                    'edl_usb_device_observed', 'current_phone_mode_verified',
                    'stock_android_return_observed', 'crash_proven', 'failure_cause_identified'):
            self.assertFalse(observed[key])
        self.assertIsNone(observed['recovery_selinux_observed'])
        self.assertTrue(observed['physical_fastboot_return_pending_at_checkpoint'])

    def test_new_user_image_remains_a_separate_unverified_candidate(self):
        candidate = self.record['next_user_supplied_candidate_at_this_checkpoint']
        self.assertEqual(candidate['scope'], 'separate_followup_not_tested_by_this_trial')
        self.assertEqual(candidate['image_basename'],
                         'twrp-3.7.1_16-nezha-antocorvo3000-fix22ZJ-touchfix18.img')
        self.assertEqual(candidate['source'], 'user_provided_claimed_working_image')
        self.assertEqual(candidate['status'], 'pending_independent_inspection_and_separate_trial')
        self.assertFalse(candidate['working_status_verified'])
        self.assertFalse(candidate['used_for_trial_8'])

    def test_public_record_contains_no_private_device_or_key_payloads(self):
        forbidden = {'serial', 'selected_serial', 'device_row', 'private_key', 'public_key_pem',
                     'argv', 'stdout', 'stderr', 'password', 'passphrase'}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & forbidden)
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(self.record)


if __name__ == '__main__':
    unittest.main()
