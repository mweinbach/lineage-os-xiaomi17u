"""Offline public-contract checks; no private firmware, guest, or phone needed."""
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BinderPolicyCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / 'research/binder-policy-correction.json').read_bytes())
        cls.dsp = json.loads((ROOT / 'research/dsp-policy-build.json').read_bytes())

    def test_scope_is_an_unadopted_private_cil_prototype(self):
        r = self.record
        self.assertEqual(r['schema_version'], 1)
        self.assertEqual(r['device'], {'codename': 'nezha', 'hardware_region': 'CN'})
        self.assertEqual(r['snapshot'], 'v9-derived-vendor-binder-cil-prototype')
        datetime.fromisoformat(r['completed_at_utc'])
        for key, value in r['limits'].items():
            self.assertEqual(value, [] if key == 'checks_disabled' else False, key)

    def test_existing_v9_build_capture_and_source_provenance_are_bound(self):
        p = self.record['provenance']
        self.assertEqual(p['v9_build_receipt_sha256'], self.dsp['receipts']['build']['sha256'])
        self.assertEqual(p['v9_sealing_receipt_sha256'], self.dsp['receipts']['capture']['sha256'])
        self.assertEqual(p['v9_host_readback_receipt_sha256'], self.dsp['receipts']['capture_readback']['sha256'])
        self.assertEqual(p['source_base_revisions'], self.dsp['adoption']['source_required_revisions_verified'])
        self.assertEqual(p['factory_package_sha256'], self.dsp['provenance']['factory_package_sha256'])
        self.assertIsNone(p['source_url'])
        for key in ('factory_origin_authenticated', 'original_vendor_macro_source_recovered',
                    'historical_receipts_rewritten', 'private_cil_or_raw_logs_published'):
            self.assertIs(p[key], False)

    def test_private_receipts_are_metadata_not_test_dependencies(self):
        refs = self.record['receipts']
        self.assertEqual(set(refs), {'derivation', 'v9_admission', 'semantic_revalidation', 'reviewed_manifest',
                                    'transfer', 'comparison', 'comparison_readback'})
        for row in refs.values():
            p = PurePosixPath(row['path'])
            self.assertFalse(p.is_absolute())
            self.assertNotIn('..', p.parts)
            self.assertIn(p.parts[0], {'artifacts', 'reports'})
            self.assertRegex(row['sha256'], r'^[0-9a-f]{64}$')
            self.assertGreater(row['size_bytes'], 0)
        self.assertEqual(refs['comparison']['sha256'], '257ad9f0c0a1903b9e339897253bc42684041db997bead3c2d81760410a1d514')
        self.assertEqual(refs['comparison_readback']['sha256'], 'f8308dc4a85ee71ba4095971697cb274f46950996ab6ef611e5738c815a59f7c')

    def test_exact_original_and_derived_vendor_hashes_and_size(self):
        c = self.record['correction']
        original = self.dsp['strict_factory_check']['input_order'][7]
        self.assertEqual((c['original_vendor_sha256'], c['original_size_bytes']), (original['sha256'], original['size_bytes']))
        self.assertEqual(c['original_vendor_sha256'], '38cbf8ed15e7f1dfe75741df453db4b8811a7585ff4e01c19dcf76710c44d500')
        self.assertEqual(c['derived_vendor_sha256'], 'b0f3f4f0ca4d9526f3c0a05e7d650a1032ff32b3f81a2677aa6e929d9446d0c2')
        self.assertEqual(c['original_size_bytes'], c['derived_size_bytes'])
        self.assertEqual(c['derived_size_bytes'], 1708593)

    def test_duplicate_occurrences_and_byte_mask_are_not_collapsed(self):
        c = self.record['correction']
        self.assertEqual((c['removed_occurrences'], c['removed_distinct_normalized_statements']), (67, 65))
        self.assertEqual((c['selected_span_bytes'], c['changed_byte_values']), (5823, 5523))
        self.assertLess(c['changed_byte_values'], c['selected_span_bytes'])
        self.assertIs(c['line_positions_and_all_unselected_bytes_preserved'], True)
        self.assertIn('CR/LF retained', c['replacement'])

    def test_statement_and_binder_count_deltas_equal_only_the_67_removals(self):
        c = self.record['correction']
        for before, after in (('vendor_statement_count_before', 'vendor_statement_count_after'),
                              ('vendor_binder_allow_count_before', 'vendor_binder_allow_count_after'),
                              ('combined_binder_allow_count_before', 'combined_binder_allow_count_after')):
            self.assertEqual(c[before] - c[after], c['removed_occurrences'])
        self.assertEqual((c['combined_binder_allow_count_before'], c['combined_binder_allow_count_after']), (3300, 3233))

    def test_semantics_are_rechecked_on_v9_without_promotions_or_retargeting(self):
        c = self.record['correction']
        self.assertEqual(c['bad_binder_groups_before'], {'source_non_domain': 32, 'target_non_domain': 35})
        self.assertEqual(c['bad_binder_groups_after'], {'source_non_domain': 0, 'target_non_domain': 0})
        self.assertEqual((c['service_object_type_count'], c['process_domain_count'], c['role_r_type_count']), (5, 596, 596))
        for key in ('exact_removal_recomputed_against_v9', 'both_tokenizers_agree_for_all_ten_inputs',
                    'binder_assertions_selected_by_identity_and_closure_not_historical_lines'):
            self.assertIs(c[key], True)
        for key in ('new_permissions', 'service_objects_promoted_into_domain', 'provider_retargetings'):
            self.assertEqual(c[key], 0)

    def test_all6366_assertions_and32_fd_occurrences_remain(self):
        p = self.record['preservation']
        self.assertEqual((p['neverallow_statements'], p['neverallowx_statements'], p['all_assertions']), (5976, 390, 6366))
        self.assertEqual(p['neverallow_statements'] + p['neverallowx_statements'], p['all_assertions'])
        self.assertEqual(p['all_assertions'], self.dsp['strict_factory_check']['total_assertions'])
        self.assertEqual((p['vendor_neverallow_statements'], p['related_fd_occurrences'], p['related_fd_distinct_statements']), (615, 32, 31))
        for key in ('valid_process_binder_grants_changed', 'service_lookup_or_registration_grants_changed',
                    'role_type_or_mapping_declarations_changed', 'assertions_removed_or_changed'):
            self.assertEqual(p[key], 0)
        self.assertIs(p['all_original_inputs_unchanged'], True)

    def test_all_ten_inputs_and_strict_flags_are_preserved(self):
        c = self.record['comparison']
        self.assertEqual(c['input_order'], self.dsp['strict_factory_check']['input_order'])
        self.assertEqual((c['input_count_each'], c['framework_input_count'], c['only_replaced_input_index']), (10, 7, 7))
        self.assertEqual(c['input_order'][7]['runtime_path'], '/vendor/etc/selinux/vendor_sepolicy.cil')
        self.assertEqual(c['compiler_flags'], ['-m', '-M', 'true', '-G', '-c', '30'])
        self.assertNotIn('-N', c['compiler_flags'])
        self.assertEqual(c['baseline_input_bytes'], sum(row['size_bytes'] for row in c['input_order']))
        self.assertEqual(c['baseline_input_bytes'], c['corrected_input_bytes'])
        self.assertIs(c['fresh_separate_output_directories'], True)
        self.assertIs(c['assertions_or_diagnostics_filtered'], False)

    def test_driver_completion_is_not_compiler_success(self):
        c = self.record['comparison']
        self.assertEqual((c['driver_invocations'], c['strict_compiler_commands'], c['driver_exit_code']), (1, 2, 0))
        self.assertIs(c['comparison_completed_safely'], True)
        self.assertEqual([row['name'] for row in c['cases']], ['baseline', 'corrected'])
        self.assertEqual([row['neverallow_assertion_sites'] for row in c['cases']], [4, 2])
        for row in c['cases']:
            self.assertEqual(row['exit_code'], 255)
            for key in ('timed_out', 'compilation_passed', 'policy_binary_produced', 'file_contexts_produced'):
                self.assertIs(row[key], False)
            self.assertIs(row['sandbox_verified'], True)

    def test_no_permissive_analysis_of_a_nonexistent_combined_binary(self):
        c = self.record['comparison']
        self.assertEqual(c['permissive_analyzer_calls'], 0)
        self.assertIsNone(c['combined_permissive_state'])
        self.assertTrue(self.dsp['source_policy_analysis']['unfiltered'])
        self.assertIs(self.record['limits']['full_combined_policy_pass'], False)

    def test_remaining_failure_sites_are_both_original_helper_setters(self):
        rows = self.record['remaining_failures']
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['target_property'] for r in rows}, {'media_variant_prop', 'apexd_select_prop'})
        for row in rows:
            self.assertEqual((row['source_domain'], row['object_class'], row['permission']), ('init_dev_config', 'property_service', 'set'))
            self.assertEqual(row['source_path'], 'system/sepolicy/private/init_dev_config.te')
        self.assertEqual({r['source_line'] for r in rows}, {9, 10})

    def test_raw_diagnostics_and_observers_are_bound_without_loading_them(self):
        cases = self.record['comparison']['cases']
        self.assertEqual([r['stderr']['size_bytes'] for r in cases], [3717, 1311])
        self.assertEqual([r['sandbox']['size_bytes'] for r in cases], [2468, 2451])
        for case in cases:
            self.assertEqual(case['stdout']['size_bytes'], 0)
            self.assertEqual(case['stdout']['sha256'], hashlib.sha256(b'').hexdigest())
            for key in ('stdout', 'stderr', 'sandbox'):
                self.assertRegex(case[key]['sha256'], r'^[0-9a-f]{64}$')
                self.assertTrue(case[key]['path'].startswith('artifacts/'))

    def test_readonly_namespace_proof_does_not_claim_host_unprivileged_execution(self):
        s = self.record['sandbox']
        for key in ('root_source_all_out_inputs_tools_and_provenance_readonly', 'only_active_case_outputs_and_tmp_writable',
                    'actual_command_observed_before_exec', 'all_four_namespace_ids_differ_from_parent',
                    'observed_capability_sets_all_zero', 'global_root_warnings_preserved'):
            self.assertIs(s[key], True)
        self.assertEqual((s['namespace_uid_gid'], s['maps_to_global_uid_gid']), (65534, 0))
        self.assertIs(s['host_unprivileged_execution_claimed'], False)
        self.assertIs(s['runtime_is_hermetic'], False)

    def test_transfer_and_readback_counts_are_distinct(self):
        r = self.record['readback']
        self.assertEqual((r['transferred_admission_files'], r['transferred_admission_bytes']), (14, 1938960))
        self.assertEqual((r['recorded_inputs_rehashed'], r['observer_inputs_rehashed_twice'], r['raw_outputs_copied_and_rehashed']), (76, 77, 7))
        self.assertIs(r['guest_files_written_by_collector'], False)

    def test_prose_keeps_prototype_and_remaining_gates_explicit(self):
        text = (ROOT / 'docs/binder-policy-correction.md').read_text()
        for phrase in ('prototype correction', 'current vendor image', 'no policy binary', '6,366 assertions',
                       '32 related', 'runtime provider remains unresolved', 'No boot or native'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
