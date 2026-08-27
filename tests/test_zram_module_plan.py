"""Offline consistency checks for the captured Nezha allocator/provider plan."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
EXPECTED_MODULES = {
    ("vendor", "zram"): (266528, "7315cd4effbe0bc8e4ada9364732a1adb3219988bc9b8c3337ed2dde1b5efea4"),
    ("vendor", "zsmalloc"): (56296, "5d936bcf3972ad25411f03440794d29abb1133bc77492cde63b79c2d47b168da"),
    ("gki", "zram"): (77338, "ecacbd66a0be40d52524dfd56d6782d698512fa15495c7cae4e42ae25a6d34ac"),
    ("gki", "zsmalloc"): (62066, "f5d5ce5e8a3f58151f1dc9070cbf5efaf65de515a74707c442977cbdb79b30fd"),
}


class ZramModulePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/zram-module-plan.json").read_text())
        cls.doc = (ROOT / "docs/zram-module-plan.md").read_text()

    def module(self, family, name):
        return self.record["module_families"][family]["modules"][name]

    def stock_list(self, area, kind):
        matches = [x for x in self.record["load_lists"] if x["area"] == area and x["kind"] == kind]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def stage(self, name):
        return next(x for x in self.record["stages"] if x["id"] == name)

    def test_modified_package_trust_is_not_upgraded(self):
        self.assertEqual(self.record["device"], "nezha")
        self.assertEqual(self.record["provenance"]["package_sha256"], PACKAGE)
        self.assertIsNone(self.record["provenance"]["origin_url"])
        self.assertFalse(self.record["provenance"]["origin_verified"])
        self.assertEqual(self.record["provenance"]["input_avb_status"], "failed")

    def test_additive_receipt_and_original_receipts_are_explicit(self):
        evidence = self.record["evidence"]
        self.assertEqual(evidence["receipt"]["sha256"], "44669f2a0d2830957f3227ced8bd79d155b82a32c82e00bd3462b3b4c38efa41")
        self.assertTrue(evidence["receipt"]["path"].startswith("artifacts/source-contracts/nezha-zram-plan-v1/"))
        self.assertEqual(evidence["original_boot_receipt_sha256"], "3615d62f4e4a61a11ff476ca47a245fa63a462136c53e688db66979f437879db")
        self.assertEqual(evidence["original_crc_receipt_sha256"], "c57b374acf5830a23ba79b0437674e1a9f8d26d68eecc55eea65f43230dd2c4a")
        self.assertIn(evidence["receipt"]["sha256"], self.doc)

    def test_four_exact_payloads_remain_distinct(self):
        for (family, name), (size, digest) in EXPECTED_MODULES.items():
            item = self.module(family, name)
            self.assertEqual((item["size_bytes"], item["sha256"]), (size, digest))
            self.assertEqual(item["internal_module_name"], name)
        self.assertEqual(len({v[1] for v in EXPECTED_MODULES.values()}), 4)

    def test_six_instances_keep_stage_identity(self):
        items = self.record["instances"]
        self.assertEqual(len(items), 6)
        self.assertEqual(len({x["sha256"] for x in items}), 4)
        for item in items:
            path = Path(item["bundle_path"])
            area = path.parts[1]
            family = "gki" if area == "system_dlkm" else "vendor"
            self.assertEqual(item["family"], family)
            self.assertEqual(item["sha256"], self.module(family, path.stem)["sha256"])
        self.assertEqual({Path(x["bundle_path"]).parts[1] for x in items},
                         {"vendor_ramdisk", "vendor_dlkm", "system_dlkm"})

    def test_each_pair_matches_all_ten_allocator_symbols(self):
        symbols = self.record["allocator_abi"]["symbols"]
        self.assertEqual(len(symbols), 10)
        for name, families in symbols.items():
            for family, values in families.items():
                self.assertEqual(values["zram_expected_crc"], values["zsmalloc_export_crc"])
                self.assertEqual(values["zsmalloc_export_crc"], self.module(family, "zsmalloc")["exports"][name]["crc"])

    def test_mixed_pairs_fail_only_zs_malloc(self):
        symbols = self.record["allocator_abi"]["symbols"]
        for consumer, provider in [("vendor", "gki"), ("gki", "vendor")]:
            differences = [name for name, values in symbols.items()
                           if values[consumer]["zram_expected_crc"] != values[provider]["zsmalloc_export_crc"]]
            self.assertEqual(differences, ["zs_malloc"])
        self.assertEqual(symbols["zs_malloc"]["vendor"]["zram_expected_crc"], "0x1804f5bc")
        self.assertEqual(symbols["zs_malloc"]["gki"]["zram_expected_crc"], "0x36f39fe1")

    def test_provider_crc_is_bound_to_export_record(self):
        for family, offset in [("vendor", 236), ("gki", 208)]:
            export = self.module(family, "zsmalloc")["exports"]["zs_malloc"]
            self.assertEqual(export["crc_file_offset"], offset)
            self.assertEqual(export["crc_section"], "__kcrctab_gpl")
            self.assertEqual(export["ksymtab_section_offset"] // 12, export["crc_section_offset"] // 4)
            self.assertEqual(export["checked_export_relocations"], 3)
            self.assertEqual(export["namespace"], "")
            self.assertEqual(export["function_section"], ".text")

    def test_extra_vendor_exports_are_not_silently_substituted(self):
        vendor = self.module("vendor", "zsmalloc")["exports"]
        gki = self.module("gki", "zsmalloc")["exports"]
        self.assertEqual((len(vendor), len(gki)), (12, 10))
        self.assertEqual(set(vendor) - set(gki), {"zs_lookup_class_index", "zs_map_object_straddle_info"})
        self.assertEqual(self.module("vendor", "zram")["exports"]["wakeup_xswapds"]["crc"], "0xd272d446")
        self.assertEqual(self.module("gki", "zram")["exports"], {})

    def test_remaining_imports_do_not_become_kernel_proof(self):
        for family, counts, remaining in [("vendor", (236, 46), 244), ("gki", (90, 53), 115)]:
            self.assertEqual(tuple(self.module(family, name)["import_version_count"] for name in ["zram", "zsmalloc"]), counts)
            data = self.record["module_families"][family]
            self.assertEqual(data["remaining_distinct_import_expectations"], remaining)
            self.assertFalse(data["remaining_import_providers_verified"])
        self.assertFalse(self.record["kernel"]["base_kernel_export_crcs_verified"])

    def test_normal_ramdisk_does_not_promote_pair(self):
        stage = self.stage("normal_first_stage")
        self.assertEqual(stage["pair_explicitly_requested"], [])
        self.assertIsNone(stage["selected_family"])
        source = self.stock_list("vendor_ramdisk", "modules.load")
        self.assertEqual(source["noncomment_count"], 157)
        self.assertEqual(source["relevant_entries"], [])
        self.assertEqual(self.stock_list("vendor_ramdisk", "modules.softdep")["relevant_entries"], [])

    def test_recovery_preserves_requests_but_requires_provider_first(self):
        source = self.stock_list("vendor_ramdisk", "modules.load.recovery")
        self.assertEqual(source["noncomment_count"], 435)
        self.assertEqual([(x["text"], x["noncomment_index_1based"]) for x in source["relevant_entries"]],
                         [("zram.ko", 152), ("zsmalloc.ko", 408)])
        stage = self.stage("recovery_first_stage")
        self.assertEqual(stage["selected_family"], "vendor")
        self.assertEqual(stage["required_insertion_order"], ["zsmalloc", "zram"])

    def test_vendor_requests_matching_pair_and_preserves_duplicate_evidence(self):
        source = self.stock_list("vendor_dlkm", "modules.load")
        self.assertEqual((source["noncomment_count"], source["unique_noncomment_count"]), (576, 381))
        self.assertEqual([(x["text"], x["noncomment_index_1based"]) for x in source["relevant_entries"]],
                         [("zram.ko", 1), ("zsmalloc.ko", 257)])
        stage = self.stage("normal_vendor_dlkm")
        self.assertEqual(stage["selected_family"], "vendor")
        self.assertEqual(stage["required_insertion_order"], ["zsmalloc", "zram"])

    def test_system_pair_is_present_but_excluded_from_loading(self):
        source = self.stock_list("system_dlkm", "modules.load")
        self.assertEqual(source["noncomment_count"], 82)
        self.assertEqual([(Path(x["text"]).name, x["noncomment_index_1based"]) for x in source["relevant_entries"]],
                         [("zsmalloc.ko", 3), ("zram.ko", 13)])
        stage = self.stage("normal_system_dlkm")
        self.assertIsNone(stage["selected_family"])
        self.assertEqual(stage["blocked_family"], "gki")
        self.assertEqual(stage["excluded_names"], ["zram", "zsmalloc"])

    def test_local_dependency_indexes_never_choose_other_family(self):
        for area in ["vendor_ramdisk", "vendor_dlkm", "system_dlkm"]:
            source = self.stock_list(area, "modules.dep")
            self.assertEqual(len(source["relevant_entries"]), 2)
            dependencies = {line["text"].split(":")[0]: line["text"].split(":")[1].split()
                            for line in source["relevant_entries"]}
            zram = next(k for k in dependencies if Path(k).name == "zram.ko")
            allocator = next(k for k in dependencies if Path(k).name == "zsmalloc.ko")
            self.assertEqual(dependencies[zram], [allocator])
            self.assertEqual(dependencies[allocator], [])

    def test_stock_discovery_differs_from_list_driven_loading(self):
        system = self.record["stock_loader_policy"]["system"]
        self.assertEqual(system["inventory_module_count"], 103)
        self.assertEqual(system["eligible_file_count"], 101)
        self.assertEqual(system["load_list_entry_count"], 82)
        self.assertEqual(system["load_list_after_exclusions"], 80)
        self.assertEqual(len(system["extra_eligible_beyond_modules_load"]), 21)
        self.assertNotIn("zram.ko", system["extra_eligible_beyond_modules_load"])
        self.assertFalse(system["find_order_recorded"])
        self.assertTrue(system["successful_initial_modprobe_needed_before_remaining_attempts"])
        self.assertFalse(system["runtime_tested"])

    def test_stock_service_order_and_concurrency_are_qualified(self):
        policy = self.record["stock_loader_policy"]
        self.assertEqual(policy["service_order"], [{"action": "exec_start", "service": "gki.modprobe"},
                                                   {"action": "start", "service": "vendor.modprobe"}])
        self.assertTrue(policy["vendor"]["first_module_invoked_synchronously"])
        self.assertTrue(policy["vendor"]["remaining_invocations_parallel"])
        self.assertFalse(policy["vendor"]["successful_runtime_loads_inferred"])
        self.assertFalse(policy["vendor_modprobe_binary_implementation_verified"])
        self.assertFalse(policy["scripts_executed"])

    def test_two_blocklist_paths_have_different_consumers(self):
        integration = self.record["candidate_integration"]
        paths = integration["install_paths_required"]
        self.assertEqual({x["path"] for x in paths}, {
            "vendor_dlkm/lib/modules/system_dlkm.modules.blocklist",
            "system_dlkm/lib/modules/modules.blocklist"})
        for item in paths:
            self.assertEqual(item["names"], ["zram", "zsmalloc"])
        self.assertTrue(integration["vendor_general_blocklist_must_exclude_pair"])
        self.assertTrue(integration["wrapper_only_is_not_proof_of_stock_selector_installation"])

    def test_general_vendor_blocklist_does_not_block_selected_pair(self):
        for area in ["vendor_ramdisk", "vendor_dlkm"]:
            self.assertEqual(self.stock_list(area, "modules.blocklist")["relevant_entries"], [])
        selection = self.stock_list("vendor_dlkm", "system_dlkm.modules.blocklist")
        self.assertEqual(selection["sha256"], "370cb88e7e8915f34e94bd6b93616f263be8a3523adc15fb554a712dc016a03f")
        self.assertEqual([x["text"] for x in selection["relevant_entries"]], ["blocklist zram", "blocklist zsmalloc"])

    def test_historical_v5_snapshot_is_separate_from_later_authored_fix(self):
        integration = self.record["candidate_integration"]
        snapshot = integration["inspected_snapshot"]
        fix = integration["authored_selector_fix"]
        self.assertEqual(snapshot["name"], "nezha-xiaomi-eu-framework-v5")
        self.assertEqual(snapshot["admission_sha256"], "b08915e0328cb87da5829bc55df2a2b851bbdfad6981ef08c3bab9a50adc7ca7")
        self.assertEqual(snapshot["installation_receipt_sha256"], "d391deb862f4254b1018d30d02d4da2cf64cba2d53810cc5e5a726a7c5c0a23c")
        self.assertEqual(snapshot["product_source"]["sha256"], "81f49aa8ece7f367457094684b159b9a2182557c298262b2eb5d3c692b57be9f")
        self.assertEqual(snapshot["product_source"]["size_bytes"], 822)
        self.assertFalse(snapshot["stock_vendor_selector_copy_requested"])
        self.assertEqual(snapshot["later_authored_fix_commit"], fix["commit"])
        self.assertEqual(fix["commit"], "3de727e76a5d7fb92bf25682aabe0ffc3c0235bd")
        self.assertEqual(fix["product_source"]["sha256"], "81243400a8c5bbd2e8fb83d3f250ccffcd4fa60f4be5b4bb1266d5cc0a07adac")
        self.assertEqual(fix["product_source"]["size_bytes"], 1611)
        self.assertIn(fix["commit"], self.doc)
        self.assertIn(snapshot["product_source"]["sha256"], self.doc)
        self.assertIn(fix["product_source"]["sha256"], self.doc)

    def test_authored_selector_request_does_not_claim_installation(self):
        fix = self.record["candidate_integration"]["authored_selector_fix"]
        for key in ["kernel_inputs_included_at_product_scope", "missing_selector_is_error",
                    "separate_system_blocklist_retained", "stock_vendor_selector_copy_requested"]:
            self.assertTrue(fix[key], key)
        for key in ["staged_into_guest_at_review", "target_image_path_readback_verified",
                    "vendor_general_blocklist_changed"]:
            self.assertFalse(fix[key], key)

    def test_sources_are_pinned_and_roles_do_not_claim_identity(self):
        sources = self.record["source_integration"]
        refs = sources["references"]
        self.assertEqual(refs["micode"]["commit"], "45705be1220b4cfa8100516ad86711656c0b634e")
        self.assertEqual(refs["ack"]["commit"], "f1bdb13583da85a47fcf1632a78ef52d6e6da651")
        self.assertEqual(refs["evolution_system_core"]["commit"], "241488ea392c01079941d86ddc458b8a0c9ae6e1")
        self.assertEqual(len(sources["files"]), 34)
        self.assertEqual(len({(x["group"], x["path"]) for x in sources["files"]}), 34)
        for item in sources["files"]:
            key = item["group"].replace("-", "_")
            self.assertEqual(item["commit"], refs[key]["commit"])
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_source_module_rules_keep_qpace_as_a_declared_dependency(self):
        source = self.record["source_integration"]
        self.assertEqual({x["name"] for x in source["vendor_required_targets"]},
                         {"mm/zsmalloc", "drivers/block/zram/zram"})
        zram = next(x for x in source["vendor_required_targets"] if x["out"] == "zram.ko")
        self.assertEqual(set(zram["declared_ddk_dependencies"]), {"mm/zsmalloc", "drivers/soc/qcom/qpace/qpace_drv"})
        self.assertEqual(source["qpace"]["canoe_literal_request"], "n")
        self.assertEqual(source["qpace"]["captured_qpace_modules"], 0)
        self.assertFalse(source["qpace"]["effective_config_or_runtime_hardware_inferred"])

    def test_extra_export_and_matching_prototype_do_not_prove_source_equivalence(self):
        gaps = self.record["source_integration"]["source_equivalence_gaps"]
        self.assertEqual(gaps["captured_vendor_zram_extra_export"], "wakeup_xswapds")
        self.assertFalse(gaps["export_present_in_pinned_micode_source_text"])
        self.assertEqual(gaps["source_search"]["matching_lines"], 0)
        self.assertEqual(gaps["source_search"]["exit_code"], 1)
        self.assertTrue(gaps["ack_and_micode_zs_malloc_literal_prototypes_match"])
        self.assertFalse(gaps["different_crc_cause_established"])
        self.assertTrue(gaps["matching_prototype_is_not_abi_proof"])

    def test_signing_and_validation_limits_are_preserved(self):
        for name in ["zram", "zsmalloc"]:
            self.assertFalse(self.module("vendor", name)["appended_signature_marker_present"])
            self.assertTrue(self.module("gki", name)["appended_signature_marker_present"])
            self.assertIsNone(self.module("gki", name)["signature_trusted_by_kernel"])
        checks = self.record["validation"]
        for name in ["complete_kernel_kmi_verified", "signature_trust_verified", "runtime_load_tested",
                     "kernel_rebuilt", "source_binary_equivalence_verified", "target_images_verified",
                     "phone_accessed", "guest_accessed", "firmware_executed", "checks_disabled"]:
            self.assertFalse(checks[name], name)
        self.assertEqual(checks["llvm_export_records_crosschecked"], 36)
        self.assertEqual(checks["synthetic_inspector_tests_passed"], 11)
        for stage in self.record["stages"]:
            self.assertIsNone(stage["runtime_loaded"])

    def test_kernel_config_and_wrapper_do_not_disable_checks(self):
        config = self.record["kernel"]["explicit_config"]
        self.assertEqual((config["CONFIG_ZRAM"], config["CONFIG_ZSMALLOC"]), ("m", "m"))
        for key in ["CONFIG_MODVERSIONS", "CONFIG_MODULE_SIG", "CONFIG_MODULE_SIG_PROTECT"]:
            self.assertEqual(config[key], "y")
        wrapper = (ROOT / "kernel/xiaomi/nezha/stock-prebuilt.mk").read_text()
        self.assertIn("BOARD_SYSTEM_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)", wrapper)
        self.assertTrue(self.record["candidate_integration"]["kernel_modversions_signing_selinux_and_avb_checks_preserved"])

    def test_public_record_has_no_host_paths_or_private_payloads(self):
        text = json.dumps(self.record)
        self.assertNotIn("/Users/", text)
        self.assertNotIn("PRIVATE KEY-----", text)
        self.assertNotIn("base64", text)
        self.assertIn("not a successful module", self.doc)
        self.assertIn("never executed", self.doc)


if __name__ == "__main__":
    unittest.main()
