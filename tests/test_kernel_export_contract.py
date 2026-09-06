"""Offline public-record checks; do not open firmware, ignored evidence or tools."""

import json
from pathlib import Path, PurePosixPath
import unittest
from urllib.parse import urlsplit

from support import walk_objects


ROOT = Path(__file__).resolve().parents[1]
ACK = "f1bdb13583da85a47fcf1632a78ef52d6e6da651"
IMAGE = "4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8"
PACKAGE = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
RECEIPTS = {
    "primary_receipt": (7128, "840959f47afc410c5bab307275badbb91fa225cf8b4e305d42946fc615948943"),
    "independent_receipt": (7465, "0c0440a6ed599c711e8df304d89e34df127ef3cdbeb053a99e61a4aa691d6a1b"),
    "corroboration_receipt": (9287, "4ae03a7d08afe2a16e91f5e6f38068906882ee56ff0788555f4e24e77d2072f2"),
    "format_source_receipt": (4132, "ccafc6836d762fc270bbf9667455bdca819c7750cfecc1a802aa4db53474268c"),
}


class KernelExportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "research/kernel-export-contract.json").read_text()
        cls.record = json.loads(cls.raw)
        cls.doc = (ROOT / "docs/kernel-export-contract.md").read_text()
        cls.prior = json.loads((ROOT / "research/zram-module-plan.json").read_text())

    def test_exact_input_identity_and_modified_package_provenance_are_retained(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], "nezha")
        self.assertEqual(self.record["observed_date"], "2026-08-27")
        kernel = self.record["kernel"]
        self.assertEqual(kernel["image_sha256"], IMAGE)
        self.assertEqual(kernel["image_file_size_bytes"], 39963136)
        for key in ("release", "ikconfig_sha256", "image_sha256"):
            self.assertEqual(kernel[key], self.prior["kernel"][key])
        provenance = self.record["provenance"]
        self.assertEqual(provenance["package_sha256"], PACKAGE)
        self.assertEqual(provenance["input_avb_status"], "failed")
        self.assertIn("modified Xiaomi.eu", provenance["package_kind"])
        self.assertIsNone(provenance["origin_url"])
        self.assertIs(provenance["origin_verified"], False)
        self.assertIs(provenance["existing_input_avb_failures_changed"], False)

    def test_scope_is_two_selected_pairs_not_all_stock_modules(self):
        scope = self.record["scope"]
        self.assertEqual(scope["families"], ["vendor", "gki"])
        self.assertEqual(scope["prior_public_record"], "research/zram-module-plan.json")
        self.assertEqual(scope["recorded_module_instances_represented"], len(self.prior["instances"]))
        self.assertEqual(scope["distinct_module_payloads_represented"], len({i["sha256"] for i in self.prior["instances"]}))
        self.assertEqual(scope["full_stock_module_instances"], 914)
        self.assertIs(scope["all_stock_module_imports_checked"], False)
        self.assertIs(scope["prior_import_tables_reused"], True)
        self.assertIs(scope["historical_pair_receipts_modified"], False)

    def test_each_remaining_family_expectation_is_present_and_crc_matched(self):
        imports = self.record["selected_imports"]
        for family, count in (("vendor", 244), ("gki", 115)):
            row = imports[family]
            self.assertEqual(row["expectation_count"], count)
            self.assertEqual(row["match_count"], count)
            self.assertEqual(row["missing_count"], 0)
            self.assertEqual(row["mismatch_count"], 0)
            self.assertEqual(count, self.prior["module_families"][family]["remaining_distinct_import_expectations"])
        self.assertIs(imports["selected_crc_check_passed"], True)
        self.assertIs(imports["other_module_imports_checked"], False)

    def test_shared_symbols_are_not_counted_as_distinct_twice(self):
        imports = self.record["selected_imports"]
        total = sum(imports[family]["expectation_count"] for family in ("vendor", "gki"))
        self.assertEqual(total, imports["family_expectation_total"])
        self.assertEqual(total, 359)
        self.assertEqual(imports["shared_kernel_symbols"], 96)
        self.assertEqual(total - imports["shared_kernel_symbols"], imports["distinct_kernel_symbols"])
        self.assertEqual(imports["distinct_kernel_symbols"], 263)

    def test_historical_unknowns_and_mixed_allocator_mismatch_are_not_rewritten(self):
        self.assertIs(self.prior["kernel"]["base_kernel_export_crcs_verified"], False)
        self.assertEqual(self.record["selected_imports"]["pair_owned_expectations_excluded_per_family"], 10)
        self.assertIs(self.record["selected_imports"]["mixed_family_zs_malloc_mismatch_unchanged"], True)
        pairs = self.prior["allocator_abi"]["symbols"]["zs_malloc"]
        self.assertEqual(pairs["vendor"]["zsmalloc_export_crc"], "0x1804f5bc")
        self.assertEqual(pairs["gki"]["zsmalloc_export_crc"], "0x36f39fe1")

    def test_pinned_format_files_are_source_references_not_stock_source_identity(self):
        fmt = self.record["format"]
        self.assertEqual(fmt["reference_commit"], ACK)
        self.assertIs(fmt["reference_identifies_stock_source"], False)
        self.assertIs(self.record["kernel"]["exact_stock_source_identity_verified"], False)
        expected = {
            "arch/arm64/Makefile", "arch/arm64/kernel/vmlinux.lds.S", "include/asm-generic/vmlinux.lds.h",
            "include/linux/export-internal.h", "kernel/kallsyms.c", "kernel/module/internal.h",
            "kernel/module/main.c", "kernel/module/version.c", "scripts/kallsyms.c", "scripts/mksysmap",
        }
        sources = fmt["sources"]
        self.assertEqual(len(sources), len(expected))
        self.assertEqual({x["path"] for x in sources}, expected)
        for source in sources:
            self.assertEqual(source["commit"], ACK)
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(source["size_bytes"], 0)
            url = urlsplit(source["url"])
            self.assertEqual((url.scheme, url.netloc), ("https", "android.googlesource.com"))
            self.assertEqual(url.path, "/kernel/common/+/" + ACK + "/" + source["path"])
        by_path = {x["path"]: x["sha256"] for x in sources}
        self.assertEqual(by_path["scripts/kallsyms.c"], "9da30067d42f0a5bee23f5234c654efa2a59d83b44c0fea71859e583735523f2")
        self.assertEqual(by_path["include/linux/export-internal.h"], "851bacf90bc83a17862d734604dc91d644dfedc173d3ea7218a7873653115d70")
        self.assertEqual(by_path["include/asm-generic/vmlinux.lds.h"], "a225a0f1424e1c8771ebec988d3ef85382d67fac3cf0276842cab73bedc74f3b")

    def test_format_keeps_crc_values_distinct_from_prel32_addresses(self):
        fmt = self.record["format"]
        self.assertIn("offsets 0, 4 and 8", fmt["export_record"])
        self.assertIn("direct little-endian unsigned 32-bit", fmt["crc_record"])
        self.assertIn("not an address or displacement", fmt["crc_record"])
        self.assertIn("same index", fmt["table_pairing"])
        self.assertIs(fmt["individual_crc_names_present_in_kallsyms"], False)
        self.assertEqual(self.record["kernel"]["data_endian"], "little")
        self.assertEqual(self.record["kernel"]["page_size_bytes"], 4096)
        self.assertEqual(set(self.record["kernel"]["format_configuration"]), {
            "CONFIG_KALLSYMS", "CONFIG_KALLSYMS_ALL", "CONFIG_HAVE_ARCH_PREL32_RELOCATIONS", "CONFIG_MODVERSIONS",
        })
        self.assertEqual(set(self.record["kernel"]["format_configuration"].values()), {"y"})

    def test_section_bounds_are_contiguous_aligned_file_offsets_with_matching_counts(self):
        sections = self.record["export_sections"]
        expected = [
            ("__ksymtab", 25714272, 25754772, 3375, 12),
            ("__ksymtab_gpl", 25754772, 25821036, 5522, 12),
            ("__kcrctab", 25821036, 25834536, 3375, 4),
            ("__kcrctab_gpl", 25834536, 25856624, 5522, 4),
        ]
        self.assertEqual(len(sections), 4)
        for row, values in zip(sections, expected):
            self.assertEqual(tuple(row[k] for k in ("section", "start", "stop", "record_count", "record_size_bytes")), values)
            self.assertEqual(row["stop"] - row["start"], row["size_bytes"])
            self.assertEqual(row["size_bytes"], row["record_count"] * row["record_size_bytes"])
            self.assertEqual(row["start"] % 4, 0)
            self.assertLessEqual(row["stop"], self.record["kernel"]["image_file_size_bytes"])
        for first, second in zip(sections, sections[1:]):
            self.assertEqual(first["stop"], second["start"])

    def test_kallsyms_layout_is_bounded_by_count_markers_and_self_symbols(self):
        row = self.record["kallsyms"]
        offsets = row["table_file_offsets"]
        self.assertEqual(offsets, {
            "kallsyms_num_syms": 21079712, "kallsyms_names": 21079720,
            "kallsyms_markers": 23078376, "kallsyms_token_table": 23080344,
            "kallsyms_token_index": 23081256, "kallsyms_offsets": 23081768,
            "kallsyms_relative_base": 23585464, "kallsyms_seqs_of_names": 23585472,
        })
        self.assertEqual(row["symbol_count"], 125924)
        self.assertEqual(row["marker_count"], (row["symbol_count"] + 255) // 256)
        self.assertEqual(row["marker_count"], 492)
        self.assertEqual(len(offsets), row["self_symbol_count_verified"])
        self.assertEqual(row["self_symbol_count_verified"], 8)
        self.assertTrue(all(value % 8 == 0 for value in offsets.values()))
        self.assertEqual(offsets["kallsyms_names"], offsets["kallsyms_num_syms"] + 8)
        names_end = offsets["kallsyms_names"] + row["name_array_bytes"]
        self.assertEqual((names_end + 7) // 8 * 8, offsets["kallsyms_markers"])
        self.assertEqual(offsets["kallsyms_offsets"], offsets["kallsyms_token_index"] + 256 * 2)
        self.assertEqual(offsets["kallsyms_relative_base"], offsets["kallsyms_offsets"] + row["symbol_count"] * 4)
        self.assertEqual(offsets["kallsyms_seqs_of_names"], offsets["kallsyms_relative_base"] + 8)
        self.assertIs(row["all_markers_and_name_index_verified"], True)
        self.assertIs(row["raw_base_used_for_file_mapping"], False)
        self.assertEqual(row["self_anchor_offset_delta"], 0)
        self.assertEqual((row["decimal_anchor_occurrences"], row["structural_token_candidates"], row["verified_layout_candidates"]), (46, 1, 1))

    def test_all_export_records_agree_but_bss_extent_is_not_partition_capacity(self):
        row = self.record["recovered_exports"]
        self.assertEqual((row["normal"], row["gpl"], row["total"]), (3375, 5522, 8897))
        self.assertEqual(row["normal"] + row["gpl"], row["total"])
        self.assertIs(row["all_record_labels_and_value_symbols_crosschecked"], True)
        self.assertIs(row["all_records_equal_between_readers"], True)
        self.assertEqual(row["non_file_backed_values_within_memory_extent"], 58)
        self.assertEqual(row["normalized_map_sha256"], "85514487c8c45c915b29937b8ab235bebbf5c209d011dd1d8cfee3bce661e122")
        kernel = self.record["kernel"]
        self.assertEqual(kernel["declared_memory_size_including_bss"], 40697856)
        self.assertGreater(kernel["declared_memory_size_including_bss"], kernel["image_file_size_bytes"])
        self.assertIs(kernel["memory_extent_is_physical_partition_capacity"], False)

    def test_module_layout_example_uses_the_same_index_in_symbol_and_crc_tables(self):
        sample = self.record["module_layout_example"]
        sections = {x["section"]: x for x in self.record["export_sections"]}
        self.assertEqual((sample["class"], sample["index"], sample["crc"], sample["namespace"]), ("normal", 1983, "0xe976b219", ""))
        self.assertEqual(sample["record_file_offset"], sections["__ksymtab"]["start"] + sample["index"] * 12)
        self.assertEqual(sample["crc_file_offset"], sections["__kcrctab"]["start"] + sample["index"] * 4)
        self.assertLess(sample["crc_file_offset"], sections["__kcrctab"]["stop"])

    def test_namespace_declaration_is_bound_to_vendor_zram_not_loader_admission(self):
        row = self.record["namespace_observation"]
        self.assertEqual((row["module_family"], row["module_name"], row["symbol"]), ("vendor", "zram", "si_swapinfo"))
        self.assertEqual(row["module_sha256"], self.prior["module_families"]["vendor"]["modules"]["zram"]["sha256"])
        self.assertEqual(row["kernel_export_namespace"], "MINIDUMP")
        self.assertEqual(row["selected_fields_in_original_order"], ["license=Dual BSD/GPL", "import_ns=MINIDUMP"])
        self.assertEqual((row["section_file_offset"], row["section_size_bytes"]), (98648, 356))
        self.assertIs(row["static_namespace_declaration_matches_export"], True)
        self.assertIs(row["runtime_namespace_or_license_admission_verified"], False)
        self.assertEqual(self.record["selected_imports"]["vendor"]["nonempty_export_namespace_count"], 1)
        self.assertEqual(self.record["selected_imports"]["gki"]["nonempty_export_namespace_count"], 0)

    def test_exact_receipts_and_distinct_readers_are_bound_without_reopening_private_data(self):
        evidence = self.record["evidence"]
        self.assertEqual(evidence["private_directory"], "artifacts/source-contracts/nezha-kernel-exports-v1")
        directories = {"primary_receipt": "result-v1", "independent_receipt": "independent-v1",
                       "corroboration_receipt": "corroboration-v1", "format_source_receipt": "source-format-v1"}
        for name, identity in RECEIPTS.items():
            self.assertEqual((evidence[name]["size_bytes"], evidence[name]["sha256"]), identity)
            self.assertEqual(evidence[name]["path"], evidence["private_directory"] + "/" + directories[name] + "/receipt.json")
        for name in ("primary_receipt", "independent_receipt", "corroboration_receipt"):
            self.assertIn(evidence[name]["sha256"], self.doc)
        self.assertEqual(evidence["primary_producer"]["sha256"], "be2c6499c33f5d7b2c51cb4a68eeb25707ed070631abf740bf88f7b8bc71d09f")
        self.assertEqual(evidence["independent_producer"]["sha256"], "ebef505c31fc2baa624447a1aad7a0ecf8f71c6b083e6a58e31e1ee87b1743a6")
        self.assertNotEqual(evidence["primary_producer"]["sha256"], evidence["independent_producer"]["sha256"])
        self.assertIs(evidence["shared_input_image_and_source_format"], True)
        self.assertIs(evidence["independent_firmware_acquisitions"], False)

    def test_complete_private_export_maps_and_comparisons_have_exact_bindings(self):
        evidence = self.record["evidence"]
        expected = {
            "primary_outputs": {
                "kallsyms-contract.json": "c5b14ab132f7e03901b14994ca22791eecacdda8b61997993643f3f6e25df73c",
                "kernel-exports.json": "03a9b7b893bfd198d2f9ad80e54c36535799ae4d6cbebe76f4040f85439cc37b",
                "remaining-import-comparison.json": "7cb333ba208d212c3d85a05462b7d78c90ff1ecd7783623d25e2801413103b07",
            },
            "independent_outputs": {
                "recovered-exports.json": "4f8d6af85b809c09d985ea01f95e52498a46b3e22025f6a94e9210e5faa4be7c",
                "import-comparison.json": "b703b265365944467b0ba6b658795a0f5e2710bfccc706a4035866d33d164612",
                "synthetic-tests.txt": "1246f076b90843257e8565686969b4f24742ce4436acbbd63fbfed1536a56ada",
            },
        }
        for key, values in expected.items():
            self.assertEqual(len(evidence[key]), len(values))
            self.assertEqual({PurePosixPath(row["path"]).name: row["sha256"] for row in evidence[key]}, values)

    def test_original_provider_and_import_receipts_remain_explicit(self):
        evidence = self.record["evidence"]
        self.assertEqual(evidence["prior_pair_receipt"]["sha256"], self.prior["evidence"]["receipt"]["sha256"])
        self.assertEqual(evidence["prior_import_expectations"]["sha256"], self.prior["evidence"]["exports_and_pairs_sha256"])
        self.assertEqual(evidence["prior_import_expectations"]["size_bytes"], 80699)

    def test_evidence_references_have_hashes_sizes_and_canonical_private_relative_paths(self):
        evidence = self.record["evidence"]
        for item in walk_objects(evidence):
            if {"path", "sha256", "size_bytes"} <= item.keys():
                path = PurePosixPath(item["path"])
                self.assertEqual(path.as_posix(), item["path"])
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertIn(path.parts[0], ("artifacts", "reports"))
                self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(item["size_bytes"], 0)
        self.assertEqual(len(evidence["primary_outputs"]), 3)
        self.assertEqual(len(evidence["independent_outputs"]), 3)

    def test_synthetic_parser_checks_are_not_a_private_firmware_test_requirement(self):
        row = self.record["synthetic_validation"]
        self.assertEqual((row["primary_parser_tests"], row["independent_parser_tests"], row["modinfo_observer_checks"]), (15, 18, 2))
        self.assertIs(row["tracked_tests_reparse_private_firmware"], False)
        self.assertEqual(row["primary_test_log"]["sha256"], "0116382f261175f2b19841a40531cc78008b71e8ff158ad26115b7bc272197eb")

    def test_all_runtime_signature_full_abi_and_mutation_limits_remain_false(self):
        limits = self.record["validation_limits"]
        self.assertEqual(set(limits), {
            "full_kernel_abi_verified", "all_914_module_instances_checked", "protected_symbol_policy_verified",
            "signature_trust_verified", "runtime_namespace_admission_verified", "runtime_gpl_license_admission_verified",
            "runtime_module_load_tested", "native_features_tested", "stock_source_rebuilt", "kernel_or_module_bytes_modified",
            "firmware_executed", "phone_accessed", "guest_accessed", "image_mounted", "firmware_uploaded", "origin_authenticated",
        })
        for key, value in limits.items():
            self.assertIs(value, False, key)

    def test_public_record_is_compact_metadata_not_a_raw_export_or_firmware_dump(self):
        self.assertLess(len(self.raw.encode()), 20000)
        forbidden = {"exports", "imported_symbol_versions", "raw_bytes", "base64", "token_strings", "expanded_symbols"}
        for item in walk_objects(self.record):
            self.assertFalse(forbidden & item.keys())
        for text in ("/Users/", "/work/", "BEGIN CERTIFICATE", "BEGIN PRIVATE KEY", "ro.serialno", "ro.boot.serialno"):
            self.assertNotIn(text, self.raw)


if __name__ == "__main__":
    unittest.main()
