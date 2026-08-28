"""Offline contract checks; private CIL, guest tools and a phone are not inputs."""
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest


ROOT = Path(__file__).resolve().parents[1]
EMPTY_SHA256 = hashlib.sha256(b'').hexdigest()


class HelperPolicyProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / 'research/helper-policy-projection.json').read_bytes())
        cls.dsp = json.loads((ROOT / 'research/dsp-policy-build.json').read_bytes())
        cls.binder = json.loads((ROOT / 'research/binder-policy-correction.json').read_bytes())
        cls.patch = json.loads((ROOT / 'patches/evolution/init-helper-property-writes.json').read_bytes())

    def test_snapshot_is_a_private_projection_not_a_fresh_source_build(self):
        r = self.record
        self.assertEqual(r['schema_version'], 1)
        self.assertEqual(r['device'], {'codename': 'nezha', 'hardware_region': 'CN'})
        self.assertEqual(r['snapshot'], 'v9-binder-corrected-policy-plus-private-helper-set-projection')
        datetime.fromisoformat(r['completed_at_utc'])
        self.assertEqual(r['comparison']['baseline_kind'], 'v9-framework-plus-binder-derived-vendor')
        self.assertEqual(r['comparison']['corrected_kind'], 'two-helper-SET-CIL-projection-not-source-build')
        for key, value in r['limits'].items():
            self.assertEqual(value, [] if key == 'checks_disabled' else False, key)

    def test_unverified_factory_origin_and_modified_inputs_are_explicit(self):
        p = self.record['provenance']
        self.assertEqual(p['factory_package_sha256'], self.dsp['provenance']['factory_package_sha256'])
        self.assertEqual(p['factory_package_sha256'], 'd2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b')
        self.assertEqual(p['factory_source_kind'], 'user-provided factory-named China fastboot TGZ')
        self.assertIsNone(p['factory_source_url'])
        for key in ('factory_origin_authenticated', 'oem_trust_root_authenticated',
                    'original_images_and_vendor_bundle_changed', 'historical_receipts_rewritten',
                    'private_cil_binary_or_raw_logs_published'):
            self.assertIs(p[key], False, key)
        self.assertIs(p['baseline_vendor_cil_is_modified'], True)
        self.assertIs(p['corrected_platform_cil_is_modified'], True)
        self.assertEqual(p['original_factory_vendor_cil_sha256'], self.binder['correction']['original_vendor_sha256'])
        self.assertEqual(p['derived_vendor_cil_sha256'], self.binder['correction']['derived_vendor_sha256'])
        self.assertNotEqual(p['original_factory_vendor_cil_sha256'], p['derived_vendor_cil_sha256'])

    def test_actual_v9_build_sealing_and_source_revisions_are_bound(self):
        p = self.record['provenance']
        for field, reference in (('v9_build_receipt_sha256', 'build'),
                                 ('v9_sealing_receipt_sha256', 'capture'),
                                 ('v9_host_readback_receipt_sha256', 'capture_readback')):
            self.assertEqual(p[field], self.dsp['receipts'][reference]['sha256'])
        self.assertEqual(p['source_base_revisions'], self.dsp['adoption']['source_required_revisions_verified'])
        self.assertEqual(p['source_base_revisions']['system/sepolicy'], 'e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27')
        self.assertEqual(p['source_base_revisions']['external/selinux'], '085c131ad1b984bfa8ffdafee7a976e9d89f403c')
        self.assertEqual(p['v9_observed_configuration'], {
            'Debuggable': False, 'Eng': False, 'SelinuxIgnoreNeverallows': False,
            'EnforceSELinuxTrebleLabeling': True, 'SELinuxTrebleLabelingTrackingListFile': ''})

    def test_receipts_are_private_metadata_not_offline_test_dependencies(self):
        refs = self.record['receipts']
        required = {'source_macro', 'projection', 'projection_final_readback', 'projection_prior_binder_binding',
                    'prior_binder_comparison', 'prior_binder_readback', 'admission', 'manifest',
                    'semantic_revalidation', 'admission_final_host_readback', 'transfer', 'checker',
                    'invocation', 'process', 'comparison_guest_receipt', 'comparison_capture',
                    'comparison_readback'}
        self.assertEqual(required, set(refs))
        for row in refs.values():
            p = PurePosixPath(row['path'])
            self.assertFalse(p.is_absolute())
            self.assertNotIn('..', p.parts)
            self.assertIn(p.parts[0], {'artifacts', 'reports'})
            self.assertRegex(row['sha256'], r'^[0-9a-f]{64}$')
            self.assertIs(type(row['size_bytes']), int)
            self.assertGreater(row['size_bytes'], 0)
        self.assertEqual(refs['comparison_guest_receipt']['sha256'], '32a49f11866bd44b391ba2931a4b7ec22f79a24af000fdb150ce1d11c3e4350e')
        self.assertEqual(refs['comparison_guest_receipt']['size_bytes'], 85767)
        self.assertEqual(refs['comparison_capture']['sha256'], refs['comparison_guest_receipt']['sha256'])
        self.assertEqual(refs['comparison_capture']['size_bytes'], 85767)
        self.assertEqual(refs['comparison_readback']['sha256'], 'd840adba3d1e76562697b517e3865a7829592aea97aa1fd45170ecfe23f86c90')
        self.assertEqual(refs['comparison_readback']['size_bytes'], 52381)
        self.assertEqual(refs['checker']['sha256'], '19700fa48aca3f530424b9e3579b1fd708ade4c09fabfc4705b2a41181d8559e')
        self.assertEqual(refs['manifest']['sha256'], 'e02b07b489f784db5b38c495554222e41adbde899e02c6661f8ec98984656d79')
        self.assertEqual(refs['prior_binder_comparison'], self.binder['receipts']['comparison'])
        self.assertEqual(refs['prior_binder_readback'], self.binder['receipts']['comparison_readback'])

    def test_exact_ten_input_order_uses_derived_vendor_in_both_cases(self):
        rows = self.record['input_order']
        actual = self.dsp['strict_factory_check']['input_order']
        self.assertEqual(len(rows), 10)
        self.assertEqual([r['index'] for r in rows], list(range(10)))
        self.assertEqual([r['runtime_path'] for r in rows], [r['runtime_path'] for r in actual])
        self.assertEqual(len({r['runtime_path'] for r in rows}), 10)
        for i, (row, original) in enumerate(zip(rows, actual)):
            self.assertEqual(row['size_bytes'], original['size_bytes'])
            self.assertEqual(row['assertions'], original['assertions'])
            expected = self.binder['correction']['derived_vendor_sha256'] if i == 7 else original['sha256']
            self.assertEqual(row['baseline_sha256'], expected, i)
            if i != 0:
                self.assertEqual(row['corrected_sha256'], expected, i)
                self.assertEqual(row['baseline_origin'], row['corrected_origin'])
        self.assertEqual(rows[7]['baseline_sha256'], 'b0f3f4f0ca4d9526f3c0a05e7d650a1032ff32b3f81a2677aa6e929d9446d0c2')
        self.assertIn('private Binder correction', rows[7]['baseline_origin'])
        self.assertNotEqual(rows[7]['baseline_sha256'], actual[7]['sha256'])
        self.assertEqual([i for i, row in enumerate(rows) if row['baseline_sha256'] != row['corrected_sha256']], [0])

    def test_platform_projection_hashes_and_unchanged_byte_length_are_exact(self):
        p = self.record['projection']
        row = self.record['input_order'][0]
        self.assertEqual(p['only_replaced_input_index'], 0)
        self.assertEqual(p['original_platform_sha256'], 'b8353ba3f5336ff28b17508808c4617d47e289be6fe7ca6b37cf4da2a9708130')
        self.assertEqual(p['projected_platform_sha256'], '96273e4332ead282eed32ad90bac29f0734365b626b81d2c79d23cc204d2ad7f')
        self.assertEqual((row['baseline_sha256'], row['corrected_sha256']), (p['original_platform_sha256'], p['projected_platform_sha256']))
        self.assertEqual((p['original_platform_size_bytes'], p['projected_platform_size_bytes']), (3012604, 3012604))
        self.assertEqual((p['selected_span_bytes'], p['changed_byte_values'], p['removed_whole_allow_forms']), (133, 125, 2))
        self.assertIn('CR/LF retained', p['replacement'])
        self.assertIs(p['all_other_bytes_newlines_offsets_and_total_size_preserved'], True)

    def test_only_two_exact_set_spans_are_selected(self):
        rows = self.record['projection']['selected_statements']
        self.assertEqual(len(rows), 2)
        self.assertEqual([r['target_property'] for r in rows], ['apexd_select_prop', 'media_variant_prop'])
        self.assertEqual([(r['start_byte'], r['end_byte_exclusive']) for r in rows], [(1733767, 1733833), (1734284, 1734351)])
        self.assertEqual([r['compiled_platform_line'] for r in rows], [41719, 41739])
        self.assertEqual([r['source_line'] for r in rows], [9, 10])
        self.assertEqual(sum(r['size_bytes'] for r in rows), 133)
        for row in rows:
            self.assertEqual((row['source_domain'], row['object_class'], row['permission']), ('init_dev_config', 'property_service', 'set'))
            self.assertEqual(row['runtime_path'], '/system/etc/selinux/plat_sepolicy.cil')
            self.assertEqual(row['source_path'], 'system/sepolicy/private/init_dev_config.te')
            self.assertEqual(row['end_byte_exclusive'] - row['start_byte'], row['size_bytes'])
            self.assertRegex(row['raw_statement_sha256'], r'^[0-9a-f]{64}$')
            self.assertNotIn('cil', row)

    def test_all6366_assertions_and_other_semantics_are_preserved(self):
        p = self.record['preservation']
        self.assertEqual((p['neverallow_occurrences'], p['neverallowx_occurrences'], p['total_assertion_occurrences']), (5976, 390, 6366))
        self.assertEqual(p['total_assertion_occurrences'], sum(sum(r['assertions'].values()) for r in self.record['input_order']))
        self.assertEqual(p['total_assertion_occurrences'], self.binder['preservation']['all_assertions'])
        self.assertEqual(p['assertion_occurrences_sha256'], '8b9ef9c30cfef6f3f4361aed18ba529939a5037af37a49db26bdcf2828f8d88d')
        self.assertEqual(p['non_allow_multiset_sha256'], 'fba60ffaf2e0f92e1f9fcf6968deffaa3590fe94c4542be7cc647e3a028003fa')
        self.assertEqual(p['modeled_closure_sha256'], '6c966dd50e49b4a2e9fd58326c9b5314430056b56aeecb483ac9ae907af80844')
        for key in ('all_non_allow_forms_unchanged', 'type_role_alias_attribute_mapping_sets_unchanged', 'all_original_inputs_unchanged'):
            self.assertIs(p[key], True)
        self.assertEqual((p['assertions_removed_or_changed'], p['new_mapping_or_role_memberships']), (0, 0))
        counts = p['modeled_closure_counts']
        self.assertEqual((counts['concrete_types'], counts['attributes'], counts['aliases'], counts['type_memberships']), (3640, 4006, 2, 664865))
        self.assertEqual((counts['roles'], counts['role_type_pairs'], counts['role_r_types']), (4, 4180, 596))

    def test_binder_and_helper_statement_deltas_are_separate(self):
        rows = self.record['preservation']['corpus_counts']
        self.assertEqual([r['corpus'] for r in rows], ['actual_v9', 'v9_with_binder_correction', 'v9_with_binder_and_capability_projection'])
        self.assertEqual([r['statements'] for r in rows], [57109, 57042, 57040])
        self.assertEqual([r['allow_occurrences'] for r in rows], [24328, 24261, 24259])
        self.assertEqual(rows[0]['statements'] - rows[1]['statements'], self.binder['correction']['removed_occurrences'])
        self.assertEqual(rows[1]['statements'] - rows[2]['statements'], self.record['projection']['removed_whole_allow_forms'])
        p = self.record['projection']
        self.assertEqual((p['modeled_effective_helper_set_grants_before'], p['modeled_effective_helper_set_grants_after']), (2, 0))
        self.assertIs(p['modeled_attribute_closure_checked'], True)
        self.assertIs(p['runtime_provider_absence_proven'], False)
        for key in ('property_reads_and_socket_grants_preserved', 'other_init_and_vendor_init_permissions_preserved',
                    'existing_vendor_init_media_set_grant_preserved', 'both_parsers_agree_for_all_three_ten_input_corpora',
                    'independent_byte_prediction_agrees'):
            self.assertIs(p[key], True)
        self.assertEqual(p['new_permissions'], 0)

    def test_compiler_is_strict_and_every_input_is_retained(self):
        c = self.record['comparison']
        self.assertEqual(c['compiler_flags'], ['-m', '-M', 'true', '-G', '-c', '30'])
        self.assertEqual(c['compiler_flags'], self.binder['comparison']['compiler_flags'])
        self.assertNotIn('-N', c['compiler_flags'])
        self.assertEqual((c['input_count_each'], c['framework_lineage_input_count'], c['factory_vendor_odm_lineage_input_count'], c['unchanged_factory_input_count']), (10, 7, 3, 2))
        self.assertEqual(c['baseline_input_bytes'], sum(r['size_bytes'] for r in self.record['input_order']))
        self.assertEqual((c['baseline_input_bytes'], c['corrected_input_bytes']), (5361292, 5361292))
        self.assertIs(c['fresh_separate_output_directories'], True)
        for key in ('precompiled_policy_fallback_used', 'assertions_or_diagnostics_filtered',
                    'permissive_allowlists_applied', 'expected_site_counts_are_success_gate'):
            self.assertIs(c[key], False)

    def test_one_invocation_two_compilers_one_analyzer_no_retry(self):
        c = self.record['comparison']
        self.assertEqual((c['driver_invocations'], c['strict_compiler_commands'], c['permissive_analyzer_calls']), (1, 2, 1))
        self.assertEqual(c['driver_exit_code'], 0)
        self.assertIs(c['automatic_retry'], False)
        self.assertIs(c['comparison_completed_safely'], True)
        start = datetime.fromisoformat(c['started_at_utc'])
        done = datetime.fromisoformat(c['process_completed_at_utc'])
        self.assertLess(start, datetime.fromisoformat(c['guest_completed_at_utc']))
        self.assertLess(datetime.fromisoformat(c['guest_completed_at_utc']), done)
        self.assertGreater((done - start).total_seconds(), 47)
        self.assertLess((done - start).total_seconds(), 48)

    def test_failed_baseline_does_not_inherit_the_corrected_pass(self):
        c = self.record['comparison']
        baseline, corrected = c['cases']
        self.assertEqual([baseline['name'], corrected['name']], ['baseline', 'corrected'])
        self.assertEqual([baseline['exit_code'], corrected['exit_code']], [255, 0])
        self.assertEqual([baseline['neverallow_assertion_sites'], corrected['neverallow_assertion_sites']], [2, 0])
        self.assertIs(baseline['compilation_passed'], False)
        self.assertIsNone(baseline['policy_binary'])
        self.assertIsNone(baseline['file_contexts'])
        self.assertIsNone(baseline['unfiltered_permissive_analysis'])
        self.assertIs(baseline['policy_passed_strict_and_zero_permissive'], False)
        self.assertIs(c['both_compilations_passed'], False)
        self.assertIs(c['both_policies_passed_strict_and_zero_permissive'], False)
        for row in c['cases']:
            self.assertIs(row['timed_out'], False)
            self.assertIs(row['sandbox_verified'], True)

    def test_new_binary_is_bound_and_analyzed_without_allowlists(self):
        c = self.record['comparison']
        corrected = c['cases'][1]
        self.assertIs(corrected['compilation_passed'], True)
        self.assertIs(corrected['policy_passed_strict_and_zero_permissive'], True)
        self.assertIs(c['corrected_private_policy_passed_strict_and_zero_permissive'], True)
        self.assertEqual(corrected['policy_binary']['sha256'], 'a827e265ee5bd3112eb657b36cf0e20db37328d948b629f97d631d68d8104bf8')
        self.assertEqual(corrected['policy_binary']['size_bytes'], 1515046)
        self.assertEqual(corrected['policy_binary']['guest_relative_path'], 'results/corrected/policy')
        a = corrected['unfiltered_permissive_analysis']
        self.assertEqual((a['exit_code'], a['mode'], a['reported_domains']), (0, 'permissive', []))
        self.assertIs(a['allowlist_applied'], False)
        self.assertIs(a['timed_out'], False)
        self.assertIs(a['sandbox_verified'], True)
        self.assertIs(a['zero_permissive_domains'], True)
        self.assertEqual((a['stdout']['sha256'], a['stdout']['size_bytes']), (EMPTY_SHA256, 0))

    def test_empty_context_output_does_not_establish_context_compatibility(self):
        c = self.record['comparison']
        context = c['cases'][1]['file_contexts']
        self.assertEqual((context['sha256'], context['size_bytes']), (EMPTY_SHA256, 0))
        self.assertEqual(context['guest_relative_path'], 'results/corrected/file_contexts')
        self.assertIs(c['empty_file_contexts_is_context_validation'], False)
        self.assertIs(self.record['limits']['context_files_compatibility_verified'], False)

    def test_full_diagnostic_and_sandbox_hashes_remain_public_metadata(self):
        baseline, corrected = self.record['comparison']['cases']
        a = corrected['unfiltered_permissive_analysis']
        self.assertEqual([row['stderr']['size_bytes'] for row in (baseline, corrected, a)], [1347, 315, 315])
        self.assertEqual([row['stderr']['sha256'] for row in (baseline, corrected, a)], [
            'c34617a427a3aef28b861b8074c49989ef5cf93984b8cbec33858ad01ab777af',
            'a57bbce872d4c4877793ebbcc57cdf0fa94622da200e6ddd251d7be29650add6',
            '575362e54788dd770f98ced248b112f424541889141f0a13a60548f07cb63c43'])
        self.assertEqual([row['sandbox']['size_bytes'] for row in (baseline, corrected, a)], [2752, 2737, 1552])
        for row in (baseline, corrected, a):
            self.assertEqual((row['stdout']['sha256'], row['stdout']['size_bytes']), (EMPTY_SHA256, 0))
            for key in ('stdout', 'stderr', 'sandbox'):
                pin = row[key]
                self.assertRegex(pin['sha256'], r'^[0-9a-f]{64}$')
                p = PurePosixPath(pin['guest_relative_path'])
                self.assertFalse(p.is_absolute())
                self.assertNotIn('..', p.parts)
                self.assertIn(p.parts[0], {'logs', 'results'})
                self.assertNotIn('text', pin)

    def test_compiler_analyzer_and_complete_runtime_bundle_are_pinned(self):
        tools = self.record['tools_and_runtime']
        self.assertEqual(set(tools), {'secilc', 'sepolicy-analyze', 'nsjail', 'libprotobuf-cpp-full.so',
                                     'libnl.so', 'libc++.so', 'libz-host.so', 'observer-python'})
        for row in tools.values():
            self.assertRegex(row['sha256'], r'^[0-9a-f]{64}$')
            self.assertGreater(row['size_bytes'], 0)
        self.assertEqual(tools['secilc']['sha256'], '1481d17c86dfc4b0ac47bd150f604425e718386379b690d06f60e417376b9a34')
        self.assertEqual(tools['sepolicy-analyze']['sha256'], 'a271e82042286276651db28a34928bd149c745ccb6ba7cacf18b51258b909669')
        self.assertEqual(tools['nsjail']['sha256'], '3f97556c3cf8a83d3f5ae854e6dfc2f345355ead547dd661d07a369b6c2ba280')
        self.assertEqual(tools['observer-python']['sha256'], '1401f5c1ddd9e8f9d77622113a8d04b5f7ef57c0e3f40dd29db248a5aa91622e')

    def test_all_three_sandbox_observations_have_precise_scope(self):
        s = self.record['sandbox']
        self.assertEqual(s['observed_command_count'], 3)
        self.assertEqual(s['four_namespaces'], ['mnt', 'net', 'pid', 'user'])
        for key in ('actual_command_observed_before_exec', 'all_four_namespace_ids_differ_from_parent',
                    'root_source_all_out_original_evidence_inputs_tools_provenance_readonly',
                    'only_active_case_outputs_and_tmp_writable', 'binary_readonly_during_analyzer',
                    'observed_capability_sets_all_zero', 'global_root_warnings_preserved'):
            self.assertIs(s[key], True, key)
        self.assertEqual((s['namespace_uid_gid'], s['maps_to_global_uid_gid']), (65534, 0))
        for key in ('host_unprivileged_execution_claimed', 'runtime_is_hermetic',
                    'system_loader_and_libraries_bundled', 'source_or_out_written'):
            self.assertIs(s[key], False, key)
        self.assertEqual((s['maximum_output_file_bytes'], s['child_cpu_limit_seconds']), (16777216, 110))

    def test_source_macro_effect_is_bound_without_claiming_android_adoption(self):
        p = self.record['source_patch_relationship']
        self.assertEqual(p['patch_sha256'], self.patch['patch_sha256'])
        self.assertEqual(p['base_commit'], self.patch['base_commit'])
        self.assertEqual(p['host_macro_receipt_sha256'], self.record['receipts']['source_macro']['sha256'])
        self.assertEqual(p['definition'], 'target_init_dev_config_property_writes=false')
        self.assertEqual((p['source_prefix_preserved_bytes'], p['host_macro_grant_occurrences_before'], p['host_macro_grant_occurrences_after']), (208, 8, 6))
        for key in ('undefined_or_true_preserves_upstream_grants', 'false_removes_only_two_set_grants',
                    'invalid_values_fail_macro_expansion'):
            self.assertIs(p[key], True)
        for key in ('host_macro_proof_is_android_m4', 'source_patch_admitted_or_installed', 'new_definition_installed',
                    'duplicate_definition_admission_guard_implemented', 'new_android_m4_or_source_build_performed',
                    'source_to_cil_effect_matched_in_full_android_build', 'api_version_inference_used', 'runtime_harmlessness_proven'):
            self.assertIs(p[key], False, key)

    def test_transfer_preserves_inputs_and_does_not_run_the_checker(self):
        t = self.record['transfer']
        self.assertEqual((t['file_count'], t['file_bytes'], t['framed_stream_bytes']), (13, 3275909, 3278124))
        self.assertGreater(t['framed_stream_bytes'], t['file_bytes'])
        for key in ('all_host_inputs_unchanged', 'all_file_hashes_read_back_before_and_after_publication',
                    'atomic_no_replace_publication', 'all_files_mode0444'):
            self.assertIs(t[key], True)
        self.assertIs(t['checker_invoked_by_transfer'], False)
        self.assertIs(t['existing_source_out_or_evidence_modified'], False)

    def test_final_readback_counts_bindings_and_outputs_are_distinct(self):
        r = self.record['readback']
        self.assertEqual(r['status'], 'complete')
        self.assertEqual((r['recorded_comparison_bindings'], r['prior_binder_bindings_reverified_by_checker']), (129, 77))
        self.assertEqual(r['observer_bindings_reverified_twice'], 130)
        self.assertEqual(r['observer_bindings_reverified_twice'], r['recorded_comparison_bindings'] + 1)
        self.assertEqual((r['raw_output_file_count'], r['raw_output_bytes']), (12, 1609831))
        outputs = [self.record['receipts']['comparison_capture']]
        for case in self.record['comparison']['cases']:
            outputs.extend(case[k] for k in ('stdout', 'stderr', 'sandbox', 'policy_binary', 'file_contexts') if case[k] is not None)
            if case['unfiltered_permissive_analysis'] is not None:
                outputs.extend(case['unfiltered_permissive_analysis'][k] for k in ('stdout', 'stderr', 'sandbox'))
        self.assertEqual(len(outputs), r['raw_output_file_count'])
        self.assertEqual(sum(row['size_bytes'] for row in outputs), r['raw_output_bytes'])
        for row in outputs[1:]:
            host_path = PurePosixPath(r['host_output_directory']) / row['guest_relative_path']
            self.assertFalse(host_path.is_absolute())
            self.assertNotIn('..', host_path.parts)
        self.assertEqual(r['stream_size_bytes'], 1646632)
        self.assertGreater(r['stream_size_bytes'], r['raw_output_bytes'])
        for key in ('comparison_guest_receipt_copied_and_hash_verified', 'raw_output_layout_matches_guest_relative_paths',
                    'readback_receipt_excluded_from_raw_output_counts', 'raw_outputs_collected_and_rehashed',
                    'all_host_outputs_rehashed_after_write', 'all_recorded_inputs_rehashed_twice',
                    'second_guest_hash_pass_completed', 'independent_local_rehash_of_all_raw_outputs',
                    'host_inputs_rehashed_after_capture'):
            self.assertIs(r[key], True, key)
        for key in ('guest_files_written_by_collector', 'compiler_invoked_by_collector',
                    'source_out_or_phone_modified', 'expected_policy_outcome_assumed'):
            self.assertIs(r[key], False, key)
        self.assertEqual(r['collector_source_sha256'], '3b03c85ec23fdfc042969d95c66cc5e1734bf59071fd054f82d5c97b93034074')
        self.assertEqual(r['guest_reader_source_sha256'], 'cc82457c8df20d9955f3891089a0a2c2f8cfc8997df96c5c917bdddda6fbba39')
        self.assertRegex(r['stream_sha256'], r'^[0-9a-f]{64}$')

    def test_unchanged_factory_policy_retains_its_four_failures(self):
        current = self.record['current_source_and_original_factory_policy']
        self.assertEqual(current['neverallow_assertion_sites'], self.dsp['strict_factory_check']['neverallow_assertion_sites'])
        self.assertEqual(current['neverallow_assertion_sites'], 4)
        self.assertEqual(current['result_record'], 'research/dsp-policy-build.json')
        for key in ('combined_policy_passed', 'helper_or_binder_private_derivative_adopted', 'original_factory_vendor_image_changed'):
            self.assertIs(current[key], False)
        self.assertEqual([r['neverallow_assertion_sites'] for r in self.binder['comparison']['cases']], [4, 2])

    def test_publication_does_not_contain_private_payloads_or_machine_paths(self):
        text = (ROOT / 'research/helper-policy-projection.json').read_text()
        for forbidden in ('/Users/', 'BEGIN PRIVATE KEY', '(allow ', '(neverallow ', 'uid_map', 'capability_status'):
            self.assertNotIn(forbidden, text)
        self.assertLess(len(text.encode()), 32000)
        self.assertNotIn('inputs_and_tools', self.record)
        self.assertNotIn('all_captured_files', self.record)

    def test_doc_states_the_passing_scope_and_remaining_gates(self):
        text = (ROOT / 'docs/helper-policy-projection.md').read_text()
        for phrase in ('zero permissive domains', 'not an Android source build', 'four failures',
                       '6,366 assertions', '315 bytes', 'global root', 'unknown source URL',
                       'Raw CIL, policy binaries and logs remain private', 'TWRP result',
                       'No phone access or modification occurred'):
            self.assertIn(phrase, text)
        self.assertIn('../research/helper-policy-projection.json', text)
        for path in ('docs/dsp-policy-build.md', 'docs/binder-policy-correction.md',
                     'docs/init-helper-capability.md', 'patches/evolution/init-helper-property-writes.json'):
            self.assertTrue((ROOT / path).is_file())


if __name__ == '__main__':
    unittest.main()
