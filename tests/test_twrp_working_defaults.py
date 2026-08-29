"""Offline consistency checks for the working recovery defaults derivative."""
import json
from pathlib import Path
import unittest


class TwrpWorkingDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'research/twrp-working-defaults.json'
        cls.record = json.loads(path.read_text())

    def test_source_and_derivative_images_remain_distinct_and_exact(self):
        self.assertEqual(self.record['baseline']['image'], {'size_bytes': 104857600,
                         'sha256': '56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323'})
        image = self.record['derivative']
        self.assertEqual(image['image'], {'size_bytes': 104857600,
                         'sha256': 'a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e'})
        self.assertEqual((image['header_version'], image['kernel_size_bytes']), (4, 0))
        self.assertTrue(image['header_unchanged_except_ramdisk_size'])
        self.assertFalse(image['runtime_newly_compiled'])
        self.assertEqual(image['compressed_ramdisk'], {'size_bytes': 75416293,
                         'sha256': '7ab74eb99db06262376fd577b1fbb28a125f28828e925fba47af5eebfc885a35'})

    def test_only_two_text_members_change_and_all_other_members_are_preserved(self):
        changes = self.record['archive_changes']
        self.assertEqual((changes['entry_count'], changes['unchanged_member_count']), (4210, 4208))
        self.assertEqual(changes['changed_text_files'], {
            'system/etc/init/hw/init.rc': {
                'before_sha256': '5adbb3437d4966449b07ea314d537317dbda1f6c5fbc818f419a8029079bc3ae',
                'after_sha256': 'd10f0cecaaa83f9e7d44b98d0cbd6ed0e27f200142b85408ef69485d038f48fa'},
            'twres/ui.xml': {
                'before_sha256': '58bb20b65214bf8313409bf34850a4103595d84f3cee9951d80ba9d013e0066d',
                'after_sha256': '4579ec254db670483fb34889255a61ba6765d1d42ab75f6ef5532ba38d2c296a'}})
        self.assertTrue(changes['all_other_member_payloads_and_metadata_unchanged'])
        self.assertTrue(changes['runtime_binaries_drivers_firmware_policy_unchanged'])

    def test_recovery_avb_uses_its_own_rollback_contract_without_oem_claims(self):
        avb = self.record['avb']
        self.assertEqual((avb['algorithm'], avb['partition_name']), ('SHA256_RSA4096', 'recovery'))
        self.assertEqual((avb['rollback_index'], avb['rollback_index_location'], avb['flags']), (1, 1, 0))
        self.assertTrue(avb['explicit_key_verification_passed'])
        self.assertFalse(avb['oem_trust_established'])

    def test_static_receipt_and_previous_workspace_tests_do_not_claim_hardware_success(self):
        checks = self.record['static_validation']
        self.assertTrue(checks['construction_verified'])
        self.assertEqual(checks['construction_receipt'], {'size_bytes': 1871,
                         'sha256': 'ce6cf315df03e9fb379d6b480e78384aeb566de9296e20fe39aeb7fdd4ce730f'})
        self.assertEqual(checks['construction_device_operations'], [])
        self.assertEqual(checks['previous_workspace_suite']['tests_passed'], 2468)
        self.assertTrue(checks['previous_workspace_suite']['passed'])
        self.assertFalse(checks['previous_workspace_suite']['hardware_validation'])
        self.assertFalse(checks['hardware_success_implied'])

    def test_startup_defaults_are_observed_without_post_boot_mutations(self):
        hardware = self.record['hardware_observation']
        self.assertEqual(hardware['partition_written'], 'recovery_a')
        self.assertTrue(hardware['recovery_a_flash_and_reboot_user_authorized'])
        self.assertTrue(hardware['installation_verified'] and hardware['recovery_adb_verified'])
        self.assertEqual((hardware['flash_returncode'], hardware['reboot_returncode']), (0, 0))
        self.assertEqual((hardware['device'], hardware['slot_suffix'], hardware['adb_uid']), ('nezha', '_a', 0))
        self.assertEqual((hardware['recovery_service'], hardware['sys_boot_completed']), ('running', '1'))
        self.assertEqual((hardware['global_getenforce'], hardware['selinux_enforce_value']), ('Permissive', '0'))
        self.assertEqual(hardware['installed_recovery_sha256'], self.record['derivative']['image']['sha256'])
        self.assertTrue(hardware['installed_readback_matches_derivative'])
        self.assertEqual(hardware['post_boot_mutating_commands_sent'], [])
        self.assertTrue(hardware['startup_defaults_verified_without_post_boot_mutations'])
        defaults = self.record['defaults_changed']
        self.assertEqual(defaults['system/etc/init/hw/init.rc'], {
            'action': 'existing_early_init', 'write_target': '/sys/fs/selinux/enforce',
            'write_value': '0', 'scope': 'recovery_only'})
        self.assertEqual(hardware['vibration_values'],
                         {'tw_action_vibrate': 0, 'tw_button_vibrate': 0, 'tw_keyboard_vibrate': 0})
        self.assertEqual(defaults['twres/ui.xml']['ordinary_theme_default_variables'], hardware['vibration_values'])
        self.assertTrue(defaults['twres/ui.xml']['saved_settings_may_override_defaults'])
        self.assertFalse(defaults['selinux_disabled_in_kernel'] or defaults['normal_android_changed'])

    def test_fresh_boot_confirmation_is_separate_from_prior_runtime_feedback(self):
        hardware = self.record['hardware_observation']
        self.assertEqual(hardware['status'], 'installation_startup_defaults_visual_and_touch_verified')
        self.assertEqual(hardware['new_image_visual_confirmation'], 'user_confirmed')
        self.assertEqual(hardware['new_image_touch_confirmation'], 'user_confirmed')
        self.assertTrue(hardware['recovery_ui_verified'])
        self.assertTrue(hardware['touch_latency_improvement_verified_on_derivative'])
        self.assertEqual(hardware['user_confirmation'], {
            'image': 'working76',
            'prompt': 'Does this fresh boot still show the UI and feel fast?',
            'response': 'yes it does!',
            'quantitative_latency_benchmark_performed': False})
        for key in ('additional_reboot_persistence_tested', 'data_decryption_tested', 'magisk_install_performed',
                    'other_partition_flash_command_sent', 'slot_change_command_sent', 'wipe_command_sent'):
            self.assertFalse(hardware[key])
        self.assertEqual(self.record['prior_runtime_tuning_user_feedback'], {
            'image': 'provided75', 'report': 'oh yea way faster',
            'confirms_working76_visual_or_touch_behavior': False})

    def test_hardware_receipt_identities_preserve_private_outputs(self):
        self.assertEqual(self.record['hardware_evidence'], {
            'runtime_verification': {'size_bytes': 2810,
                                    'sha256': '1c2f3918cebe9adbc94cd3a98b27bf6855d713334d1f1375c906025925211054'},
            'flash_result': {'size_bytes': 281,
                             'sha256': '41893a9e83ebbc38e136a8f9040e11d4b607a00c52d11f8be51dbc9ac2029330'},
            'recovery_reboot_result': {'size_bytes': 216,
                                      'sha256': 'cf978eb1816958f507c78d5d4d20fe7e679561c39f0b9200159b1b3aacad58d4'}})


if __name__ == '__main__':
    unittest.main()
