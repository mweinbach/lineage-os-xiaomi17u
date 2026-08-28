"""Offline public-record checks; no ignored evidence, SDK, network or phone."""

import copy
import json
from pathlib import Path, PurePosixPath
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "normal_first_stage": (157, 154, 154, 7542, 6732, 810, 0),
    "recovery_first_stage": (435, 424, 426, 20345, 17457, 2888, 0),
    "normal_system_loader": (101, 101, 101, 5599, 5070, 529, 0),
    "normal_vendor_loader": (380, 380, 380, 23716, 19787, 3197, 732),
}
FIELDS = ("requests", "unique_requests", "hard_closure_modules", "expectations",
          "kernel_crc_matches", "local_hard_predecessor_crc_matches", "earlier_stage_conditional_crc_matches")
LIMITS = {
    "actual_module_load_verified", "successful_stage_provider_availability_verified",
    "parallel_load_order_verified", "stock_loader_source_identity_verified",
    "full_kernel_abi_verified", "signature_trust_verified", "runtime_namespace_admission_verified",
    "runtime_gpl_license_admission_verified", "protected_symbol_or_kmi_policy_verified",
    "runtime_mounts_or_device_compatibility_verified", "native_features_device_tested",
    "recovery_or_twrp_verified", "bootloader_corruption_protection_proven",
    "kernel_or_module_bytes_modified", "firmware_executed", "firmware_uploaded", "phone_accessed",
    "guest_accessed", "android_source_or_out_modified", "image_mounted", "origin_authenticated",
}
RECEIPTS = {
    "primary_receipt": ("result-v3/receipt.json", 274540, "530610ac2778fd41c2c58977762f1a33cc34f2b8bdb67e44f2ef60765a183252"),
    "final_readback": ("module-stage-final-readback-v2.json", 7820, "6c5d28a77ed4e298b8bacdea4ae802de54ac8930696a67afe83d63fae252e5ce"),
    "factory_link_capture": ("symlink-text-v3/receipt.json", 3488, "06c5dd3ba773114b7861fb9faadd37abb309354ce0ce3fa82a7b4d46f5481880"),
}


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_record(record):
    require(record["schema_version"] == 1 and record["device"] == "nezha", "identity")
    require(set(record["stages"]) == set(STAGES), "stage identities")
    require(set(record["limits"]) == LIMITS, "limit inventory")
    require(all(v is False for v in record["limits"].values()), "runtime/admission claims")
    for name, expected in STAGES.items():
        row = record["stages"][name]
        require(all(type(row[f]) is int and row[f] >= 0 for f in FIELDS), "count types")
        require(tuple(row[f] for f in FIELDS) == expected, "stage evidence count")
        require(row["expectations"] == sum(row[f] for f in FIELDS[-3:]), "expectation arithmetic")
        require(row["implicit_module_layout_expectations"] == row["hard_closure_modules"], "module_layout unit")
        require(row["successful_loading_proven"] is False, "eligibility is not loading")
        for field in ("missing_hard_paths", "hard_or_pre_cycles", "local_crc_matching_provider_ambiguities"):
            require(type(row[field]) is int and row[field] == 0, "unexpected unresolved static path")
    system = record["selection"]["normal_system_loader"]
    require(system["eligible_paths"] == 101, "system discovery cannot be replaced by 82-row list")
    require(system["eligible_listed_paths"] + system["eligible_unlisted_paths"] == system["eligible_paths"], "system arithmetic")
    require(system["discovered_regular_paths"] - len(system["excluded_names"]) == system["eligible_paths"], "system selector")
    vendor = record["selection"]["normal_vendor_loader"]
    require(vendor["modules_load_rows"] - vendor["unique_names"] == vendor["duplicate_occurrences"], "vendor duplicate arithmetic")
    require(vendor["unique_names"] - len(vendor["excluded_names"]) == vendor["eligible_names"] == 380, "vendor selector")
    earlier = record["earlier_stage_requirements"]
    require(earlier["normal_first_stage_expectations"] + earlier["system_stage_expectations"] == earlier["vendor_expectations"] == 732, "earlier stage arithmetic")
    require(earlier["normal_first_stage_provider_payloads"] + earlier["system_stage_provider_payloads"] == earlier["provider_payloads"] == 51, "provider payload unit")
    require(sum(p["expectations"] for p in earlier["system_providers"]) == 14, "system provider expectation sum")
    allocator = record["allocator_families"]
    require(allocator["vendor_zs_malloc_crc"] == "0x1804f5bc" and allocator["gki_zs_malloc_crc"] == "0x36f39fe1", "allocator families")
    require(allocator["wrong_family_crc_accepted"] is False, "wrong-family admission")
    require(record["factory_paths"]["stock_toolbox_source_identity_verified"] is False, "link target is not source identity")
    require(record["factory_paths"]["runtime_mount_or_access_verified"] is False, "package path is not runtime mount")
    for key, (suffix, size, digest) in RECEIPTS.items():
        row = record["evidence"][key]
        require(row["path"].endswith(suffix) and row["size_bytes"] == size and row["sha256"] == digest, "sealed receipt binding")
    for row in objects(record):
        if {"path", "sha256", "size_bytes"} <= row.keys():
            path = PurePosixPath(row["path"])
            require(not path.is_absolute() and str(path) == row["path"] and ".." not in path.parts, "safe evidence path")
            require(path.parts[0] in ("artifacts", "reports"), "private evidence namespace")
            require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None, "digest syntax")
            require(type(row["size_bytes"]) is int and row["size_bytes"] > 0, "receipt size")


class ModuleStageClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "research/module-stage-closure.json").read_text()
        cls.record = json.loads(cls.raw)
        cls.doc = (ROOT / "docs/module-stage-closure.md").read_text()
        cls.pool = json.loads((ROOT / "research/module-provider-audit.json").read_text())

    def test_valid_public_record(self):
        validate_record(self.record)

    def test_provenance_keeps_the_two_packages_distinct(self):
        p = self.record["provenance"]
        self.assertEqual(p["module_bundle_package_sha256"], self.pool["provenance"]["package_sha256"])
        self.assertEqual(p["loader_capture_package_sha256"], "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b")
        self.assertNotEqual(p["module_bundle_package_sha256"], p["loader_capture_package_sha256"])
        self.assertIn("modified Xiaomi.eu", p["module_bundle_package_kind"])
        self.assertIn("factory-named", p["loader_capture_package_kind"])
        for prefix in ("module_bundle", "loader_capture"):
            self.assertIsNone(p[prefix + "_origin_url"])
            self.assertIs(p[prefix + "_origin_verified"], False)
        self.assertIs(p["original_xiaomi_eu_avb_failures_changed"], False)
        self.assertIs(p["new_firmware_authentication_or_avb_validation_performed"], False)
        self.assertEqual(self.pool["provenance"]["input_avb_status"], "failed")
        self.assertIn("26 module metadata", p["byte_equality_scope"])

    def test_same_sealed_kernel_and_module_inventory_are_reused(self):
        r = self.record["inputs"]
        self.assertEqual(r["module_instances"], self.pool["population"]["instance_count"])
        self.assertEqual(r["unique_module_payloads"], self.pool["population"]["unique_payload_count"])
        self.assertEqual(r["instances_by_location"], self.pool["population"]["instances_by_location"])
        self.assertEqual(sum(r["instances_by_location"].values()), 914)
        self.assertEqual(r["kernel_image_sha256"], self.pool["kernel"]["image_sha256"])
        self.assertEqual(r["kernel_export_map_count"], self.pool["provider_tables"]["kernel_export_count"])
        self.assertEqual(self.record["evidence"]["global_provider_receipt"], self.pool["evidence"]["primary_receipt"])
        self.assertEqual(self.record["evidence"]["kernel_export_map"], self.pool["evidence"]["kernel_export_map"])

    def test_reference_pin_is_not_stock_binary_identity(self):
        sources = self.record["reference_sources"]
        self.assertEqual(sources["evolution_system_core"]["commit"], "241488ea392c01079941d86ddc458b8a0c9ae6e1")
        self.assertIn("not stock binary identity", sources["evolution_system_core"]["role"])
        self.assertEqual(sources["erofs_utils"]["commit"], "f36cadb5c563995ab3aa8572a60ed6b721b9557d")
        self.assertIn(sources["evolution_system_core"]["commit"], self.doc)

    def test_stage_rows_are_alternative_scenarios_not_an_added_population(self):
        scope = self.record["scope"]
        self.assertIs(scope["normal_and_recovery_are_alternative_trajectories"], True)
        self.assertIs(scope["stage_rows_are_disjoint_population_counts"], False)
        self.assertIs(scope["counts_include_one_module_layout_expectation_per_consumer"], True)
        for name, expected in STAGES.items():
            self.assertEqual(tuple(self.record["stages"][name][f] for f in FIELDS), expected)

    def test_recovery_retains_dependency_added_modules_and_fallback_rule(self):
        recovery = self.record["selection"]["recovery_first_stage"]
        self.assertEqual(recovery["hard_added_names"], ["hdcp_qseecom_dlkm", "smmu_proxy_dlkm"])
        stage = self.record["stages"]["recovery_first_stage"]
        self.assertEqual(stage["hard_closure_modules"] - stage["unique_requests"], len(recovery["hard_added_names"]))
        self.assertIs(recovery["fallback_to_normal_only_on_stat_failure"], True)
        self.assertIs(recovery["fallback_on_empty_contents"], False)

    def test_system_eligibility_includes_unlisted_discovered_modules(self):
        r = self.record["selection"]["normal_system_loader"]
        self.assertEqual((r["modules_load_rows"], r["discovered_regular_paths"], r["eligible_paths"]), (82, 103, 101))
        self.assertEqual((r["eligible_listed_paths"], r["eligible_unlisted_paths"]), (80, 21))
        self.assertEqual(r["excluded_names"], ["zram", "zsmalloc"])
        self.assertIs(r["modules_load_is_existence_gate_only"], True)
        self.assertIs(r["flatten_mirror_selected"], False)
        self.assertIs(r["find_order_known"], False)

    def test_vendor_duplicates_filters_and_first_request_remain_distinct(self):
        r = self.record["selection"]["normal_vendor_loader"]
        self.assertEqual((r["modules_load_rows"], r["unique_names"], r["duplicate_occurrences"], r["eligible_names"]), (576, 381, 195, 380))
        self.assertEqual(r["excluded_names"], ["ipclite_test"])
        self.assertEqual(r["first_unique_request"], "zram.ko")
        self.assertIs(r["audio_blocklist_files_present"], False)
        self.assertIs(r["retained_duplicate_sort_positions_known"], False)
        self.assertIs(r["fallback_directory_or_filter_environment_behavior_fully_verified"], False)

    def test_script_exit_and_readiness_do_not_prove_loading(self):
        for name in ("normal_system_loader", "normal_vendor_loader"):
            row = self.record["selection"][name]
            self.assertIs(row["first_request_synchronous"], True)
            self.assertIs(row["remaining_requests_parallel"], True)
            self.assertIs(row["child_failures_checked"], False)
        self.assertIs(self.record["selection"]["normal_system_loader"]["exit_zero_proves_modules_loaded"], False)
        self.assertIs(self.record["selection"]["normal_vendor_loader"]["readiness_property_proves_modules_loaded"], False)

    def test_packaged_parallel_declaration_does_not_prove_runtime_order(self):
        r = self.record["selection"]["normal_first_stage"]
        self.assertIs(r["raw_package_bootconfig_declares_parallel_true"], True)
        self.assertIs(r["runtime_proc_bootconfig_representation_verified"], False)
        self.assertIs(r["parallel_schedule_reconstructed"], False)

    def test_reference_dependency_labels_retain_conditional_cases(self):
        r = self.record["dependency_semantics"]
        self.assertIn("reverse recorded order", r["hard_requests"])
        self.assertIn("conditional alias", r["hard_requests"])
        self.assertEqual(r["soft_owner_tokens"], "raw literal comparison")
        self.assertIs(r["soft_pre_failures_ignored_by_reference"], True)
        self.assertIs(r["soft_pre_graph_path_proves_attempt"], False)
        self.assertIs(r["aliases_and_cache_behavior_distinguished"], True)
        self.assertIs(r["sequential_and_parallel_blocklist_root_policies_distinguished"], True)
        self.assertIs(r["missing_or_malformed_config_can_silently_change_requests"], True)
        self.assertIs(r["eexist_identifies_active_payload"], False)
        self.assertIs(r["runtime_command_line_options_and_dynamic_callers_fully_known"], False)

    def test_earlier_provider_counts_are_exact_conditions_not_success(self):
        r = self.record["earlier_stage_requirements"]
        self.assertEqual((r["vendor_expectations"], r["consumer_modules"], r["distinct_symbols"], r["provider_payloads"]), (732, 144, 289, 51))
        self.assertEqual((r["normal_first_stage_expectations"], r["system_stage_expectations"]), (718, 14))
        self.assertEqual(r["system_providers"], [{"name": "rfkill", "expectations": 12, "consumers": ["btpower", "cfg80211"]},
                                                {"name": "libarc4", "expectations": 2, "consumers": ["mac80211"]}])
        self.assertIs(r["earlier_selected_membership_proves_successful_loading"], False)

    def test_missing_soft_targets_are_preserved_without_substitution(self):
        r = self.record["missing_soft_dependencies"]
        self.assertEqual((r["normal_first_stage_edges"], r["recovery_first_stage_edges"], r["normal_system_loader_edges"], r["normal_vendor_loader_edges"]), (0, 1, 0, 15))
        self.assertEqual(r["recovery_target"], "phy-msm-snps-hs")
        self.assertEqual(len(r["vendor_local_missing_but_selected_in_normal_ramdisk"]), 6)
        self.assertEqual(len(r["absent_from_captured_module_pool_and_aliases"]), 3)
        self.assertEqual(r["vendor_unique_target_names"], 9)
        self.assertIs(r["missing_soft_target_implies_unresolved_required_import"], False)
        self.assertIs(r["substitute_modules_added"], False)

    def test_allocator_locality_resolves_global_ambiguity_without_accepting_wrong_crc(self):
        r = self.record["allocator_families"]
        self.assertEqual((r["recovery_vendor_zs_expectations_each"], r["same_crc_global_gki_alternatives_each"]), (10, 9))
        old = self.pool["provider_ambiguity"]
        self.assertEqual(r["vendor_zs_malloc_crc"], old["vendor_expected_and_matching_provider_crc"])
        self.assertEqual(r["gki_zs_malloc_crc"], old["gki_expected_and_matching_provider_crc"])
        self.assertIs(r["matching_local_vendor_hard_predecessor"], True)
        self.assertIs(r["gki_pair_excluded_by_system_selector"], True)
        self.assertIs(r["local_matching_payload_ambiguity"], False)

    def test_factory_path_text_is_separate_from_runtime_and_source_identity(self):
        r = self.record["factory_paths"]
        self.assertEqual(r["vendor_modprobe_link_target"], "toolbox")
        self.assertEqual(r["vendor_modules_link_target"], "/vendor_dlkm/lib/modules")
        self.assertEqual(r["absolute_vendor_dependency_owner_paths_mapped"], 381)
        self.assertIs(r["links_followed_or_created"], False)
        for key in ("raw_link_text_read_by_explicit_inode", "target_and_inode_metadata_readbacks_passed",
                    "inventory_hash_and_parse_share_buffer", "input_stability_checked_before_publication"):
            self.assertIs(r[key], True)

    def test_validation_counts_and_history_are_bound_without_opening_private_files(self):
        r = self.record["validation"]
        self.assertEqual((r["primary_model_synthetic_tests"], r["link_reader_synthetic_tests"], r["independent_graph_synthetic_tests"], r["final_readback_checks"]), (46, 13, 7, 11))
        self.assertEqual((r["bundle_files_freshly_rehashed"], r["final_unique_input_bindings_rehashed_twice"], r["final_output_files_rehashed_twice"]), (950, 1001, 6))
        self.assertEqual((r["workspace_tests_before_public_slice"], r["workspace_shell_syntax_passed"]), (1061, True))
        self.assertEqual((r["prior_result_v2_input_bindings_preserved"], r["prior_result_v2_output_files_preserved"]), (995, 6))
        self.assertEqual(r["independent_vendor_consumer_symbol_crc_payload_tuples_match"], 732)
        history = self.record["history"]
        self.assertIs(history["all_prior_sources_outputs_and_logs_preserved"], True)
        self.assertIn("result-v1", history["provisional_graph_receipt"]["path"])
        self.assertIn("result-v2", history["prior_graph_receipt"]["path"])
        self.assertIn("temporary directory symlink", history["fixture_failure_explanation"])
        self.assertIn("actual captured counts unchanged", history["model_review_fixes"])

    def test_existing_global_audit_is_not_rewritten_into_stage_proof(self):
        self.assertIs(self.record["scope"]["historical_public_records_modified"], False)
        self.assertIs(self.pool["scope"]["stage_availability_or_load_selection_inferred"], False)
        self.assertIs(self.pool["validation_limits"]["dependency_closure_and_load_order_verified"], False)

    def test_document_communicates_bounds_and_keeps_raw_artifacts_private(self):
        for text in ("732", "101 eligible paths", "80 listed and 21", "counterfactual", "full ABI",
                     "signature trust", "TWRP", "bootloader corruption", "earlier stage", "unauthenticated"):
            self.assertIn(text, self.doc)
        self.assertLess(len(self.doc.split()), 1100)
        for forbidden in ("/Users/", "BEGIN PRIVATE KEY", "raw_elf", "payload_base64", "device_serial"):
            self.assertNotIn(forbidden, self.raw + self.doc)

    def test_mutation_rejects_promoted_runtime_claim(self):
        r = copy.deepcopy(self.record)
        r["limits"]["successful_stage_provider_availability_verified"] = True
        with self.assertRaisesRegex(ValueError, "runtime/admission"):
            validate_record(r)

    def test_mutation_rejects_using_list_length_as_system_selection(self):
        r = copy.deepcopy(self.record)
        r["selection"]["normal_system_loader"]["eligible_paths"] = 82
        with self.assertRaisesRegex(ValueError, "system discovery"):
            validate_record(r)

    def test_mutation_rejects_boolean_counts_and_wrong_family(self):
        r = copy.deepcopy(self.record)
        r["stages"]["normal_first_stage"]["earlier_stage_conditional_crc_matches"] = False
        with self.assertRaisesRegex(ValueError, "count types"):
            validate_record(r)
        r = copy.deepcopy(self.record)
        r["allocator_families"]["vendor_zs_malloc_crc"] = r["allocator_families"]["gki_zs_malloc_crc"]
        with self.assertRaisesRegex(ValueError, "allocator families"):
            validate_record(r)

    def test_mutation_rejects_unbound_receipt_and_unsafe_private_path(self):
        r = copy.deepcopy(self.record)
        r["evidence"]["primary_receipt"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sealed receipt"):
            validate_record(r)
        r = copy.deepcopy(self.record)
        r["evidence"]["primary_test_log"]["path"] = "reports/../../secret"
        with self.assertRaisesRegex(ValueError, "safe evidence path"):
            validate_record(r)


if __name__ == "__main__":
    unittest.main()
