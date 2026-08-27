"""Offline public metadata checks; never open ignored firmware or run tools."""

import json
from pathlib import Path, PurePosixPath
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
ACK = "f1bdb13583da85a47fcf1632a78ef52d6e6da651"
PACKAGE = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
IMAGE = "4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8"
RECEIPTS = {
    "primary_receipt": ("result-v2", 233902, "a19a8da010446dfaba4f5e902091912efd54f57cb1ee1de05db43925e5a64a99"),
    "llvm_receipt": ("llvm-readback-v1", 773216, "c58781b550608defd5552c6d6eda4ed786915d35d34a854abe71d8de0012d581"),
    "final_readback_receipt": ("final-readback-v1", 601701, "31fa6168b902a14b89ef34ff72f543a29af97e4211b7bce94e9f450b14bfd015"),
}
LIMITS = {
    "full_kernel_abi_verified", "signature_trust_verified", "protected_symbol_or_kmi_policy_verified",
    "runtime_namespace_admission_verified", "runtime_gpl_license_admission_verified", "actual_module_load_verified",
    "provider_availability_at_each_stage_verified", "dependency_closure_and_load_order_verified",
    "automatic_provider_selection_verified", "native_features_device_tested", "stock_source_rebuilt",
    "firmware_or_build_inputs_adopted", "kernel_or_module_bytes_modified", "signature_bytes_modified",
    "firmware_executed", "firmware_uploaded", "phone_accessed", "guest_accessed", "image_mounted", "origin_authenticated",
}


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


class ModuleProviderAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "research/module-provider-audit.json").read_text()
        cls.record = json.loads(cls.raw)
        cls.doc = (ROOT / "docs/module-provider-audit.md").read_text()
        cls.kernel = json.loads((ROOT / "research/kernel-export-contract.json").read_text())
        cls.zram = json.loads((ROOT / "research/zram-module-plan.json").read_text())

    def test_exact_kernel_and_modified_package_provenance_are_retained(self):
        row = self.record
        self.assertEqual((row["schema_version"], row["device"], row["observed_date"]), (1, "nezha", "2026-08-27"))
        self.assertEqual(row["provenance"], self.kernel["provenance"])
        self.assertEqual(row["provenance"]["package_sha256"], PACKAGE)
        self.assertEqual(row["provenance"]["input_avb_status"], "failed")
        self.assertIn("modified Xiaomi.eu", row["provenance"]["package_kind"])
        self.assertIsNone(row["provenance"]["origin_url"])
        self.assertIs(row["provenance"]["origin_verified"], False)
        self.assertIs(row["provenance"]["existing_input_avb_failures_changed"], False)
        self.assertEqual(row["kernel"]["image_sha256"], IMAGE)
        self.assertEqual(row["kernel"]["image_file_size_bytes"], 39963136)
        self.assertEqual(row["kernel"]["page_size_bytes"], 4096)
        for key, value in row["kernel"].items():
            self.assertEqual(value, self.kernel["kernel"][key])

    def test_global_pool_scope_does_not_promote_stage_or_loader_admission(self):
        scope = self.record["scope"]
        self.assertIs(scope["all_captured_module_instances_checked"], True)
        self.assertIs(scope["every_expectation_has_a_crc_matching_candidate"], True)
        self.assertIn("all three locations", scope["provider_pool"])
        self.assertIs(scope["stage_availability_or_load_selection_inferred"], False)
        self.assertIs(scope["firmware_or_build_inputs_adopted"], False)
        self.assertIs(scope["historical_records_modified"], False)
        self.assertEqual(scope["prior_records"], ["research/zram-module-plan.json", "research/kernel-export-contract.json"])
        self.assertIs(self.kernel["scope"]["all_stock_module_imports_checked"], False)

    def test_module_copies_are_not_counted_as_distinct_payloads(self):
        row = self.record["population"]
        self.assertEqual(row["instances_by_location"], {"vendor_ramdisk": 430, "vendor_dlkm": 381, "system_dlkm": 103})
        self.assertEqual(row["instance_count"], sum(row["instances_by_location"].values()))
        self.assertEqual(row["unique_payload_count"], 637)
        self.assertEqual(row["single_instance_payloads"] + row["two_instance_identical_payloads"], 637)
        self.assertEqual(row["single_instance_payloads"] + row["two_instance_identical_payloads"] * 2, 914)
        self.assertEqual((row["instance_bytes"], row["unique_payload_bytes"]), (190666422, 155867526))
        self.assertGreater(row["instance_bytes"], row["unique_payload_bytes"])
        self.assertIn("whole module SHA256", row["parsing_deduplication_key"])
        self.assertIs(row["stage_paths_and_raw_load_request_order_and_duplicates_preserved"], True)

    def test_all_export_records_have_complete_class_and_relocation_counts(self):
        row = self.record["provider_tables"]
        self.assertEqual(row["kernel_export_count"], self.kernel["recovered_exports"]["total"])
        self.assertEqual(row["kernel_export_count"], 8897)
        self.assertEqual(row["module_export_records_by_class"], {"normal": 2872, "gpl": 1956})
        self.assertEqual(sum(row["module_export_records_by_class"].values()), row["module_export_records_unique_payloads"])
        self.assertEqual(row["module_export_records_unique_payloads"], 4828)
        self.assertEqual(row["module_export_functions"] + row["module_export_data_objects"], 4828)
        self.assertEqual((row["module_export_functions"], row["module_export_data_objects"]), (4391, 437))
        self.assertEqual(row["prel32_relocations"], 4828 * 3)
        self.assertEqual((row["exporting_payload_count"], row["distinct_module_export_names"]), (290, 4818))
        self.assertIs(row["required_namespaces_and_gpl_classes_retained"], True)

    def test_distinct_payload_expectations_include_implicit_module_layout(self):
        row = self.record["expectations"]["unique_payloads"]
        self.assertEqual(row["classification_counts"], {
            "kernel_crc_match": 31686, "module_crc_match_unique_payload": 5259, "module_crc_match_multiple_payloads": 18,
        })
        self.assertEqual(row["expectation_count"], sum(row["classification_counts"].values()))
        self.assertEqual(row["expectation_count"], 36963)
        self.assertEqual(row["reference_role_counts"], {"undefined_symbol": 36326, "implicit_module_layout": 637})
        self.assertEqual(sum(row["reference_role_counts"].values()), row["expectation_count"])

    def test_instance_weighted_counts_preserve_the_same_distinction(self):
        row = self.record["expectations"]["captured_instances"]
        self.assertEqual(row["classification_counts"], {
            "kernel_crc_match": 42946, "module_crc_match_unique_payload": 7466, "module_crc_match_multiple_payloads": 27,
        })
        self.assertEqual(row["expectation_count"], 50439)
        self.assertEqual(row["expectation_count"], sum(row["classification_counts"].values()))
        self.assertEqual(row["reference_role_counts"], {"undefined_symbol": 49525, "implicit_module_layout": 914})
        self.assertEqual(sum(row["reference_role_counts"].values()), row["expectation_count"])

    def test_location_totals_do_not_claim_provider_availability(self):
        row = self.record["expectations"]
        self.assertIn("Consumer location only", row["location_count_meaning"])
        self.assertIn("complete captured pool", row["location_count_meaning"])
        locations = row["by_consumer_location"]
        expected = {"vendor_ramdisk": (20936, 17920, 3007, 9), "vendor_dlkm": (23761, 19823, 3929, 9),
                    "system_dlkm": (5742, 5203, 530, 9)}
        for name, (total, kernel, unique, multiple) in expected.items():
            actual = locations[name]
            self.assertEqual(actual["expectation_count"], total)
            self.assertEqual(actual["classification_counts"], {
                "kernel_crc_match": kernel, "module_crc_match_unique_payload": unique, "module_crc_match_multiple_payloads": multiple,
            })
            self.assertEqual(actual["reference_role_counts"]["implicit_module_layout"], self.record["population"]["instances_by_location"][name])
        for classification, total in row["captured_instances"]["classification_counts"].items():
            self.assertEqual(sum(loc["classification_counts"][classification] for loc in locations.values()), total)

    def test_symbol_names_and_crc_pairs_are_not_expectation_counts(self):
        row = self.record["expectations"]
        self.assertEqual((row["distinct_symbol_names"], row["distinct_name_crc_pairs"]), (6684, 6685))
        self.assertLess(row["distinct_name_crc_pairs"], row["unique_payloads"]["expectation_count"])
        self.assertEqual(row["without_any_crc_matching_provider"], 0)
        self.assertEqual(row["kernel_crc_mismatches"], 0)
        self.assertEqual(row["module_provider_candidates_all_crc_mismatched"], 0)

    def test_wrong_family_candidate_conflicts_are_not_hidden_by_positive_matches(self):
        row = self.record["provider_ambiguity"]
        self.assertEqual((row["duplicate_export_names"], row["same_crc_shared_allocator_names"]), (10, 9))
        self.assertEqual(self.record["provider_tables"]["module_export_records_unique_payloads"] -
                         self.record["provider_tables"]["distinct_module_export_names"], row["duplicate_export_names"])
        self.assertEqual(row["only_conflicting_crc_name"], "zs_malloc")
        self.assertEqual(row["vendor_expected_and_matching_provider_crc"], "0x1804f5bc")
        self.assertEqual(row["gki_expected_and_matching_provider_crc"], "0x36f39fe1")
        self.assertNotEqual(row["vendor_expected_and_matching_provider_crc"], row["gki_expected_and_matching_provider_crc"])
        self.assertEqual((row["matching_and_conflicting_candidates_per_unique_payloads"], row["matching_and_conflicting_candidates_per_instances"]), (2, 3))
        self.assertEqual((row["matching_crc_ambiguous_expectations_per_unique_payloads"], row["matching_crc_ambiguous_expectations_per_instances"]), (18, 27))
        self.assertIs(row["same_family_pairs_match"], True)
        self.assertIs(row["wrong_family_crc_accepted"], False)
        self.assertIs(row["automatic_provider_selection_performed"], False)
        self.assertIs(self.kernel["selected_imports"]["mixed_family_zs_malloc_mismatch_unchanged"], True)

    def test_same_name_variants_cannot_supply_each_other(self):
        row = self.record["provider_ambiguity"]
        self.assertIs(row["same_internal_name_external_providers_excluded"], True)
        self.assertEqual(row["actual_same_name_provider_exclusion_count"], 0)
        self.assertEqual(self.record["expectations"]["unique_payloads"]["same_name_excluded_provider_count"], 0)

    def test_extended_versions_accept_long_rust_names_without_dropping_imports(self):
        row = self.record["version_and_declaration_checks"]
        self.assertEqual(row["classic_and_extended_payloads"], 637)
        self.assertEqual((row["classic_entries"], row["extended_entries"]), (36903, 36963))
        self.assertEqual(row["extended_entries"] - row["classic_entries"], row["extended_only_entries"])
        self.assertEqual(row["extended_only_entries"], 60)
        self.assertEqual((row["rust_binder_classic_entries"], row["rust_binder_extended_entries"]), (166, 226))
        self.assertEqual(row["rust_binder_extended_entries"] - row["rust_binder_classic_entries"], 60)
        self.assertEqual((row["extended_only_name_bytes_min"], row["extended_only_name_bytes_max"]), (56, 117))
        self.assertIs(row["every_classic_entry_matches_extended"], True)
        self.assertIs(row["extended_table_is_canonical_when_present"], True)
        self.assertEqual(row["version_only_name"], "module_layout")
        self.assertEqual(row["undefined_global_references_unique_payloads"], 36326)
        self.assertEqual(row["undefined_weak_references"], 0)
        self.assertEqual(row["undefined_symbols_without_recorded_version"], 0)

    def test_namespace_and_license_results_are_static_matching_candidate_observations(self):
        row = self.record["version_and_declaration_checks"]
        self.assertEqual(row["required_namespace_counts"], {"DMA_BUF": 103, "EXPORTED_FOR_KUNIT_TESTING": 3, "MINIDUMP": 8, "PWM": 4})
        self.assertIn("CRC-matching provider candidate", row["namespace_count_unit"])
        self.assertEqual(row["matching_candidates_missing_namespace_declarations"], 0)
        self.assertEqual(row["matching_candidates_with_gpl_declaration_conflicts"], 0)
        self.assertIs(row["license_declarations_preserved_in_order"], True)
        self.assertEqual((row["payloads_with_multiple_license_declarations"], row["maximum_license_declarations_per_payload"]), (24, 31))
        self.assertIs(row["loader_first_license_and_modpost_all_declarations_checked_statically"], True)
        self.assertIs(row["declarations_prove_runtime_or_legal_admission"], False)

    def test_loader_format_guards_and_crc_representation_are_explicit(self):
        row = self.record["format"]
        self.assertEqual(row["reference_commit"], ACK)
        self.assertIs(row["reference_establishes_stock_source_identity"], False)
        self.assertEqual((row["export_record_bytes"], row["crc_record_bytes"], row["export_relocation_type"]), (12, 4, 261))
        self.assertIn("section offset, not the CRC", row["crc_encoding"])
        self.assertIn("separately name-sorted", row["pairing"])
        for name in ["allocated_export_crc_and_version_sections_required", "modinfo_may_be_nonallocated",
                     "all_records_labels_and_export_relocations_accounted_for", "data_and_bss_exports_supported",
                     "unsupported_layouts_refused", "weak_or_missing_version_evidence_not_equated_to_crc_mismatch"]:
            self.assertIs(row[name], True, name)

    def test_source_format_references_are_exact_pinned_primary_sources(self):
        rows = self.record["format"]["sources"]
        self.assertEqual({r["path"] for r in rows}, {
            "include/linux/export-internal.h", "include/linux/license.h", "include/linux/module.h",
            "kernel/module/main.c", "kernel/module/version.c", "scripts/mod/modpost.c",
            "scripts/module.lds.S", "arch/arm64/kernel/module.c",
        })
        self.assertEqual(len(rows), 8)
        for row in rows:
            url = urlsplit(row["url"])
            self.assertEqual((url.scheme, url.netloc, url.query, url.fragment), ("https", "android.googlesource.com", "", ""))
            self.assertEqual(url.path, "/kernel/common/+/" + ACK + "/" + row["path"])
            self.assertEqual(row["commit"], ACK)
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(row["size_bytes"], 0)

    def test_llvm_corroborates_all_crcs_but_not_relocations_or_namespace_values(self):
        row = self.record["corroboration"]["llvm"]
        self.assertEqual((row["tool"], row["ndk_version"]), ("llvm-readobj", "28.2.13676358"))
        self.assertEqual(row["tool_sha256"], "37e565359be0c9f2868348dd314416a420d137ee84c891ec8474cf7d29cfd995")
        self.assertEqual((row["exporting_payloads"], row["export_records"], row["command_count"]), (290, 4828, 625))
        self.assertIs(row["all_crcs_classes_indexes_and_table_label_file_offsets_match"], True)
        self.assertIs(row["primary_values_read_after_llvm_map_complete"], True)
        for key in ("primary_elf_parser_imported", "independent_export_relocations_checked",
                    "independent_namespace_values_checked", "independent_firmware_acquisition"):
            self.assertIs(row[key], False, key)

    def test_final_readback_counts_unique_files_separately_from_references_and_streams(self):
        row = self.record["corroboration"]
        self.assertEqual((row["prior_import_records_exactly_match"], row["independent_format_census_instances_match"],
                          row["independent_format_census_payloads_match"]), (914, 914, 637))
        final = row["final_readback"]
        self.assertEqual((final["input_references"], final["unique_input_files_rehashed"], final["llvm_stdout_and_stderr_files_rehashed"]), (1859, 943, 1250))
        self.assertGreater(final["input_references"], final["unique_input_files_rehashed"])
        self.assertEqual(final["llvm_stdout_and_stderr_files_rehashed"], row["llvm"]["command_count"] * 2)
        self.assertIs(final["all_receipt_and_output_hashes_match"], True)
        self.assertIs(final["classification_aggregates_recounted_without_importing_producers"], True)
        self.assertIs(final["new_elf_parse_performed"], False)

    def test_final_receipts_producers_and_original_kernel_binding_are_exact(self):
        evidence = self.record["evidence"]
        base = evidence["private_directory"]
        self.assertEqual(base, "artifacts/source-contracts/nezha-full-module-audit-v1")
        for key, (directory, size, sha) in RECEIPTS.items():
            self.assertEqual(evidence[key], {"path": base + "/" + directory + "/receipt.json", "sha256": sha, "size_bytes": size})
            self.assertIn(sha, self.doc)
        self.assertEqual(evidence["primary_producer"]["sha256"], "75cf5ad7c39a6177ed8210566a944c958b9606ec0e5100ce85bb7c005b36fe96")
        self.assertEqual(evidence["llvm_producer"]["sha256"], "5f8d38bdb88bb299632c0bdf9315a645cf286a021cf3539c9c9ad34bef074988")
        self.assertEqual(evidence["final_readback_producer"]["sha256"], "d472a7b371dcad157466db424dd4ecd900c6728b98c1f53ed46b44a73d910a8a")
        self.assertEqual(evidence["bundle_receipt"]["sha256"], "4ce149410ba2ab5f24653ebd8c4020a7401ba5172e2648c19f3c8bf726a7e9bb")
        self.assertEqual(evidence["kernel_export_corroboration_receipt"], self.kernel["evidence"]["corroboration_receipt"])
        self.assertIn(evidence["kernel_export_map"], self.kernel["evidence"]["primary_outputs"])
        self.assertEqual(evidence["historical_import_receipt"]["sha256"], "c57b374acf5830a23ba79b0437674e1a9f8d26d68eecc55eea65f43230dd2c4a")

    def test_primary_outputs_and_independent_export_map_bindings_are_complete(self):
        evidence = self.record["evidence"]
        expected = {
            "payloads.json": "21fecfcbec146bae32fb94168aaa42f63e665ba7db5407cefe3e788f375a5561",
            "instances-and-load-requests.json": "de42a72b406cedba2507e97650eb443274bd9227854368aab1437182c51f4280",
            "provider-comparisons.json": "97c0c22bd373c47854e5712d6e1850f3e2ea175bf37508f32c9d7a1fc8605f00",
            "provider-collisions.json": "03417354008548c671f3d0c49e8b1eaf10c107dafb9bdd821e1e26a153d5d808",
            "notable-comparisons.json": "83ead280a30d76424de331627a140290046febe474e34de26334408b973ed037",
            "summary.json": "ea1cc9ec0a6b15e8e9c6347316e19d35b1c939936d3e7beb7e989efb5d3a3877",
        }
        self.assertEqual({PurePosixPath(row["path"]).name: row["sha256"] for row in evidence["primary_outputs"]}, expected)
        self.assertEqual(len(evidence["primary_outputs"]), 6)
        self.assertEqual(evidence["llvm_export_output"]["sha256"], "3538aa5b50f41e753a87d35d66f25281364d94e29a855bb3209799a46910deeb")

    def test_provisional_results_and_failed_regressions_remain_separate(self):
        history = self.record["preserved_history"]
        self.assertEqual(history["provisional_result_v1"]["sha256"], "6097753d47d549cf3b674dec0ad2845cf4bddf9826322fa1e15283cd98abad18")
        self.assertNotEqual(history["provisional_result_v1"]["sha256"], self.record["evidence"]["primary_receipt"]["sha256"])
        self.assertIn("Superseded", history["provisional_result_status"])
        self.assertEqual(history["provisional_producer_snapshot"]["sha256"], "506291d2e302c56090b9ce280f1d034c0814cc85113e34eff8adc83927c569ef")
        self.assertEqual({row["sha256"] for row in history["red_regression_logs"]}, {
            "bad6d6def996049a7bb46570c934a32d152d754b9a0f2b940a64a4d8fb00de1a",
            "6f26a5c504128039a00c8683963b7584e651647bc9fcee7d866e15d404a092c7",
        })
        self.assertIn("invalid JSON", history["probe_failure"])
        self.assertIs(history["old_receipts_or_outputs_rewritten"], False)
        self.assertIs(history["history_is_not_final_evidence"], True)

    def test_private_evidence_references_are_canonical_hashed_metadata_only(self):
        for section in (self.record["evidence"], self.record["preserved_history"], self.record["validation"]):
            for row in objects(section):
                if {"path", "sha256", "size_bytes"} <= row.keys():
                    path = PurePosixPath(row["path"])
                    self.assertEqual(path.as_posix(), row["path"])
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertIn(path.parts[0], ("artifacts", "reports"))
                    self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
                    self.assertIs(type(row["size_bytes"]), int)
                    self.assertGreater(row["size_bytes"], 0)

    def test_historical_private_validation_is_not_required_for_public_tests(self):
        row = self.record["validation"]
        self.assertEqual((row["primary_synthetic_test_count"], row["llvm_synthetic_test_count"], row["independent_format_census_helper_tests"]), (40, 12, 5))
        self.assertEqual(row["sealed_private_audit_workspace_test_count"], 1029)
        self.assertIs(row["sealed_workspace_shell_syntax_passed"], True)
        self.assertIs(row["tracked_tests_require_private_files_or_tools"], False)
        self.assertEqual([entry["test_count"] for entry in row["private_test_logs"]], [40, 12, 1029])

    def test_runtime_security_mutation_and_origin_limits_stay_false(self):
        limits = self.record["validation_limits"]
        self.assertEqual(set(limits), LIMITS)
        for key, value in limits.items():
            self.assertIs(value, False, key)

    def test_public_record_is_aggregate_metadata_not_raw_proprietary_data(self):
        self.assertLess(len(self.raw.encode()), 24000)
        forbidden = {"exports", "imported_symbol_versions", "undefined_symbols", "raw_bytes", "base64",
                     "private_key", "commands", "modinfo", "payloads", "instance_records"}
        for row in objects(self.record):
            self.assertFalse(forbidden & row.keys())
        for text in ("/Users/", "/work/", "BEGIN CERTIFICATE", "BEGIN PRIVATE KEY", "ro.serialno", "ro.boot.serialno"):
            self.assertNotIn(text, self.raw)


if __name__ == "__main__":
    unittest.main()
