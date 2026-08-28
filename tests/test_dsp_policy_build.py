"""Offline invariants for actual v9 policy evidence; no private files or phone."""
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class DspPolicyBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/dsp-policy-build.json").read_bytes())
        cls.prior = json.loads((ROOT / "research/user-security-build.json").read_bytes())
        cls.contract = json.loads((ROOT / "research/dsp-policy-integration.json").read_bytes())

    def test_scope_keeps_factory_origin_runtime_and_rom_unverified(self):
        r = self.record
        self.assertEqual(r["schema_version"], 1)
        self.assertEqual(r["device"], {"codename": "nezha", "hardware_region": "CN"})
        self.assertEqual(r["snapshot"], "dsp-source-user-v9-policy-build")
        for key, value in r["limits"].items():
            self.assertEqual(value, [] if key == "checks_disabled" else False, key)
        p = r["provenance"]
        self.assertEqual(p["factory_package_sha256"], self.contract["generator_contract"]["factory_package_sha256"])
        self.assertIsNone(p["factory_source_url"])
        for key in ("factory_origin_authenticated", "oem_trust_root_authenticated",
                    "historical_contract_or_receipts_rewritten", "proprietary_cil_or_logs_published"):
            self.assertIs(p[key], False)
        self.assertEqual(p["kernel_package_sha256"],
                         "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69")
        self.assertNotEqual(p["kernel_package_sha256"], p["factory_package_sha256"])
        self.assertIn("Xiaomi.eu", p["kernel_provenance"])

    def test_original_contract_is_unchanged_and_not_reclassified_as_a_build(self):
        p = self.record["provenance"]
        self.assertEqual(p["source_integration_commit"], "2475343c70d75912719f0663941011a7143ec5b0")
        self.assertEqual(p["source_contract"]["sha256"],
                         "30720967a28cb558a0e3f90ed26a1f8e7c5b6befde55fea8428bbe8e693cd1f9")
        for key in ("source_contract", "previous_user_v8_record", "source_snapshot"):
            ref = p[key]
            raw = (ROOT / ref["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref["sha256"])
            self.assertEqual(len(raw), ref["size_bytes"])
        self.assertIs(self.contract["compiler_fixture"]["fresh_soong_or_m4_build_performed"], False)
        self.assertIs(self.record["source_integration"]["actual_soong_evaluation_verified"], True)
        self.assertIs(self.record["source_integration"]["preprocessed_fixture_reclassified_as_build"], False)

    def test_private_receipts_are_bounded_metadata_without_reading_evidence(self):
        refs = self.record["receipts"]
        self.assertEqual(set(refs), {"generation", "admission", "installation", "build", "capture", "capture_readback",
                                    "policy_check", "policy_result_readback", "cil_and_diagnostic_delta", "source_audit",
                                    "prior_v8_snapshot", "strict_check_plan"})
        self.assertEqual(len({v["sha256"] for v in refs.values()}), len(refs))
        for ref in refs.values():
            path = PurePosixPath(ref["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertIn(path.parts[0], {"reports", "artifacts"})
            self.assertRegex(ref["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(ref["size_bytes"], 0)
        self.assertEqual(refs["build"]["sha256"], "64fdf29e9ee07885c6efce95e512be73e417a68fa041b87ccbfedb838955977a")
        self.assertEqual(refs["policy_check"]["sha256"], "419b1a6e4993322ec1a533862ae4c18c5f7d7a42e611243b46c2328e39156d00")
        self.assertEqual(refs["source_audit"]["sha256"], "2ea91f7862f09e7f8b41a56ce0df52db151dc9d22027658bca11838acaf344b8")

    def test_adoption_is_optional_device_only_and_preserves_v8(self):
        a = self.record["adoption"]
        self.assertEqual(a["generator_option"], "--dsp-policy-contract")
        self.assertEqual(a["admission_sha256"], "50fea6a4e94d86ee94ba5514d7dc7b1420c15f5bb4e850ea0c5dcb66c377fb4d")
        self.assertEqual(a["previous_admission_sha256"], self.prior["build"]["input_admission_sha256"])
        self.assertEqual((a["candidate_added_files"], a["candidate_changed_files"], a["candidate_unchanged_files"]), (3, 1, 11))
        self.assertEqual(a["candidate_file_count"], 15)
        self.assertEqual((a["installed_device_file_count"], a["installed_device_bytes"]), (12, 24435))
        self.assertEqual(a["unchanged_output_guards"], 63)
        self.assertIs(a["output_files_written"], False)
        for key in ("only_device_source_exchanged", "atomic_directory_exchange", "old_device_source_preserved",
                    "kernel_vendor_receipts_unchanged", "readback_verified", "security_and_variant_guards_preserved"):
            self.assertIs(a[key], True)
        self.assertEqual(a["source_required_revisions_verified"], self.contract["generator_contract"]["required_source_revisions"])

    def test_actual_build_has_exact_sixteen_policy_targets_and_201_actions(self):
        b = self.record["build"]
        self.assertEqual((b["target_product"], b["target_release"], b["target_variant"]), ("lineage_nezha", "bp4a", "user"))
        self.assertEqual(b["targets"], ["precompiled_sepolicy", "secilc", "sepolicy-analyze", "checkfc", "checkseapp",
            "property_info_checker", "plat_sepolicy.cil", "plat_mapping_file", "plat_sepolicy_genfs_202504.cil",
            "system_ext_sepolicy.cil", "system_ext_mapping_file", "product_sepolicy.cil", "product_mapping_file",
            "sepolicy_neverallows", "sepolicy_test", "sepolicy_dev_type_test"])
        self.assertEqual((b["target_count"], b["ninja_actions_completed"], b["exit_code"]), (16, 201, 0))
        self.assertIs(b["passed"], True)
        self.assertLess(datetime.fromisoformat(b["started_at"]), datetime.fromisoformat(b["completed_at"]))
        self.assertEqual(b["input_admission_sha256"], self.record["adoption"]["admission_sha256"])
        self.assertEqual(b["installation_sha256"], self.record["receipts"]["installation"]["sha256"])
        self.assertIs(b["incremental_user_output_reused"], True)
        self.assertEqual(b["physical_out_dir"], self.prior["build"]["physical_out_dir"])
        for key in ("timed_out", "old_output_reset_or_installclean_requested", "source_sync_repeated",
                    "captured_factory_vendor_cil_in_source_targets", "images_rebuilt", "full_rom_build_verified"):
            self.assertIs(b[key], False)

    def test_previous_outputs_remain_distinct_preserved_sets(self):
        b = self.record["build"]
        for key in ("source_inputs_unchanged_after_build", "all_eleven_old_userdebug_artifacts_unchanged",
                    "prior_user_policy_tools_and_config_preserved", "v8_sealed_snapshot_unchanged", "v8_boot_artifacts_unchanged"):
            self.assertIs(b[key], True)
        self.assertEqual(b["unchanged_v8_boot_artifact_count"], 12)
        self.assertEqual(b["preserved_user_files"], 33)
        self.assertEqual(b["preservation_manifest_sha256"], "52bc06062a6bdb760d0afc2ddc767d2f62936aea04429410618f8b4de819612e")

    def test_authored_source_hashes_and_split_policy_wiring_match_the_contract(self):
        s = self.record["source_integration"]
        self.assertEqual(s["source_files"], self.contract["generator_contract"]["source_files"])
        self.assertEqual(s["wiring"], self.contract["generator_contract"]["wiring"])
        statements = []
        for row in s["source_files"]:
            raw = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
            self.assertEqual(len(raw), row["size_bytes"])
            statements.extend(line.strip() for line in raw.decode().splitlines() if line.strip() and not line.startswith("#"))
        self.assertEqual(statements, ["attribute vendor_hal_dspmanager_client;", "typeattribute isolated_compute_app vendor_hal_dspmanager_client;"])
        self.assertIs(s["generated_fragments_match_prior_fixture"], True)
        self.assertIs(s["authored_source_and_four_patched_files_unchanged"], True)
        self.assertEqual((s["new_source_allow_rules"], s["assertions_removed"]), (0, 0))
        self.assertIs(s["platform_public_api_mapping_modified"], False)

    def test_observed_source_directories_and_security_flags_are_actual_config(self):
        config = self.record["observed_configuration"]
        v = config["values"]
        self.assertIs(config["required_configuration_matched"], True)
        self.assertIs(config["actual_treble_labeling_test_pass_verified"], False)
        self.assertIs(config["policy_api_version_spoofed"], False)
        for key in ("Debuggable", "Eng", "SelinuxIgnoreNeverallows"):
            self.assertIs(v[key], False)
        self.assertIs(v["EnforceSELinuxTrebleLabeling"], True)
        self.assertEqual(v["SELinuxTrebleLabelingTrackingListFile"], "")
        self.assertEqual((v["Platform_sdk_version"], v["PlatformSepolicyVersion"], v["BoardSepolicyVers"]), (36, "202504", "202504"))
        wiring = self.record["source_integration"]["wiring"]
        self.assertEqual(v["SystemExtPublicSepolicyDirs"], [wiring["SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS"]])
        self.assertEqual(v["ProductPrivateSepolicyDirs"], [wiring["PRODUCT_PRIVATE_SEPOLICY_DIRS"]])
        for key in ("BoardVendorSepolicyDirs", "BoardOdmSepolicyDirs", "SystemExtPrivateSepolicyDirs", "ProductPublicSepolicyDirs",
                    "SystemExtSepolicyPrebuiltApiDirs", "ProductSepolicyPrebuiltApiDirs"):
            self.assertEqual(v[key], [])

    def test_both_actual_binary_analyses_are_unfiltered_and_empty(self):
        a = self.record["source_policy_analysis"]
        self.assertIs(a["unfiltered"], True)
        for key in ("permissive_allowlists_applied", "factory_odm_prebuilt_policy_replaced", "runtime_enforcement_verified"):
            self.assertIs(a[key], False)
        binaries = a["binaries"]
        self.assertEqual([r["name"] for r in binaries], ["source-precompiled", "source-neverallows"])
        self.assertEqual([r["size_bytes"] for r in binaries], [721536, 775162])
        self.assertEqual([r["sha256"] for r in binaries], ["8ba4d0fa829bf2f4fe8a759953b2afcf886a0ac76933bda6c2e2a28771c8563a",
                                                           "0175482614a6c8aed02fe202df903a1cef8b4fb0b0e1a4b1c30398783aca5a0f"])
        for row, previous in zip(binaries, self.prior["source_policy_analysis"]["binaries"]):
            self.assertEqual(row["previous_v8_sha256"], previous["input"]["sha256"])
            self.assertEqual(row["previous_v8_size_bytes"], previous["input"]["size_bytes"])
            self.assertEqual(row["exit_code"], 0)
            self.assertEqual(row["reported_domains"], [])
            self.assertIs(row["zero_permissive_domains"], True)
            self.assertEqual(row["analysis_argv_tail"][-1], "permissive")
            self.assertEqual(len(row["analysis_argv_tail"]), 3)
            self.assertEqual(row["stdout"], {"sha256": hashlib.sha256(b"").hexdigest(), "size_bytes": 0})
            self.assertEqual(row["stderr"]["size_bytes"], 315)
        self.assertEqual(binaries[0]["sha256"], binaries[0]["previous_v8_sha256"])
        self.assertEqual(binaries[1]["size_bytes"] - binaries[1]["previous_v8_size_bytes"], 56)

    def test_ten_input_order_preserves_exact_factory_hashes_and_all_assertion_forms(self):
        s = self.record["strict_factory_check"]
        old = self.prior["strict_factory_check"]
        self.assertEqual([r["runtime_path"] for r in s["input_order"]], [r["runtime_path"] for r in old["input_order"]])
        self.assertEqual((s["input_count"], s["framework_input_count"], s["unchanged_factory_input_count"]), (10, 7, 3))
        self.assertEqual(s["input_bytes"], sum(r["size_bytes"] for r in s["input_order"]))
        self.assertEqual(s["input_bytes"], 5361292)
        factory = {r["runtime_path"]: r for r in self.contract["generator_contract"]["policy_inputs"]}
        for row in s["input_order"]:
            if row["runtime_path"] in factory:
                self.assertEqual((row["sha256"], row["size_bytes"]), (factory[row["runtime_path"]]["sha256"], factory[row["runtime_path"]]["size_bytes"]))
        self.assertEqual(s["assertion_forms"], {"neverallow": 5976, "neverallowx": 390})
        for form, count in s["assertion_forms"].items():
            self.assertEqual(sum(row["assertions"][form] for row in s["input_order"]), count)
        self.assertEqual(sum(s["assertion_forms"].values()), s["total_assertions"])
        self.assertEqual(s["total_assertions"], 6366)
        self.assertIs(s["assertion_form_multisets_equal_to_v8"], True)

    def test_five_to_four_is_a_removed_failure_not_a_removed_assertion(self):
        s = self.record["strict_factory_check"]
        self.assertEqual(s["compiler_flags"], ["-m", "-M", "true", "-G", "-c", "30"])
        self.assertNotIn("-N", s["compiler_flags"])
        self.assertEqual((s["previous_v8_assertion_sites"], s["neverallow_assertion_sites"], s["exit_code"]), (5, 4, 255))
        self.assertEqual(s["removed_assertion_failure"], {"runtime_path": "/vendor/etc/selinux/vendor_sepolicy.cil", "line": 6044})
        self.assertIs(s["assertion_itself_removed"], False)
        self.assertEqual(s["remaining_groups"], self.prior["strict_factory_check"]["remaining_groups"][1:])
        self.assertEqual([r["lines"] for r in s["remaining_groups"]], [[5931, 5746], [24641, 24636]])
        self.assertEqual(sum(len(r["lines"]) for r in s["remaining_groups"]), 4)
        self.assertIs(s["remaining_diagnostics_equal_to_v8"], True)
        self.assertEqual(s["displayed_allow_locations"], 10)
        self.assertIs(s["displayed_allows_are_exhaustive"], False)
        for key in ("passed", "policy_binary_produced", "file_contexts_produced", "assertions_or_diagnostics_filtered"):
            self.assertIs(s[key], False)
        self.assertIsNone(s["combined_policy_permissive_analysis"])
        self.assertEqual((s["stderr"]["sha256"], s["stderr"]["size_bytes"]),
                         ("ca8e4ca97fdc0b1bc5a39c19da90b43a52ed5eef3ab6cca9ce4fc05e60b7e090", 3773))

    def test_only_the_two_compiler_fragments_differ_from_v8(self):
        d = self.record["compiled_cil_delta"]
        self.assertEqual((d["framework_files_unchanged"], d["framework_files_changed"], d["factory_files_unchanged"]), (5, 2, 3))
        self.assertEqual(d["combined_input_bytes_added"], 117)
        self.assertEqual(self.record["strict_factory_check"]["input_bytes"] - self.prior["strict_factory_check"]["input_bytes"], 117)
        changes = {r["runtime_path"]: r for r in d["changes"]}
        self.assertEqual(set(changes), {"/system_ext/etc/selinux/system_ext_sepolicy.cil", "/product/etc/selinux/product_sepolicy.cil"})
        expected = {"/system_ext/etc/selinux/system_ext_sepolicy.cil": (46, "7bee774aff706c539a1617c5c2c8f47100fd8987eedeb00e31ab40e1281068ec"),
                    "/product/etc/selinux/product_sepolicy.cil": (73, "238af2a9cee8a300b574de03a0d26620fb23c6af0a7814e8ff0b6b84da7d2f5d")}
        for old, new in zip(self.prior["strict_factory_check"]["input_order"], self.record["strict_factory_check"]["input_order"]):
            path = new["runtime_path"]
            if path not in changes:
                self.assertEqual((old["sha256"], old["size_bytes"]), (new["sha256"], new["size_bytes"]))
                continue
            delta = changes[path]
            self.assertEqual((delta["old_sha256"], delta["old_size_bytes"]), (hashlib.sha256(b"\n").hexdigest(), 1))
            self.assertEqual((delta["new_size_bytes"], delta["new_sha256"]), expected[path])
            self.assertEqual((new["size_bytes"], new["sha256"]), expected[path])
        self.assertEqual((d["new_cil_forms"], d["new_assertion_forms"], d["removed_assertion_forms"]), (2, 0, 0))
        self.assertIs(d["input_cil_manually_modified"], False)

    def test_source_audit_binds_all_project_pins_and_only_the_three_existing_patches(self):
        a = self.record["source_audit"]
        self.assertIs(a["passed"], True)
        self.assertEqual(a["summary"], {"project_count": 1179, "head_match_count": 1179, "remote_match_count": 1179,
            "clean_project_count": 1176, "intentional_modified_project_count": 3, "accepted_worktree_count": 1179, "unexpected_projects": []})
        self.assertEqual(a["source_snapshot_sha256"], self.record["provenance"]["source_snapshot"]["sha256"])
        revisions = {e.get("path", e.get("name")): e.get("revision") for e in ET.parse(ROOT / self.record["provenance"]["source_snapshot"]["path"]).findall("project")}
        self.assertEqual(len(revisions), 1179)
        for project, revision in self.record["adoption"]["source_required_revisions_verified"].items():
            self.assertEqual(revision, revisions[project])
        self.assertEqual({p["project"] for p in a["source_patches"]}, {"vendor/lineage", "system/sepolicy", "system/core"})
        self.assertEqual(sum(len(p["files"]) for p in a["source_patches"]), 4)
        previous = {p["project"]: p for p in self.prior["source_patches"]}
        for patch in a["source_patches"]:
            self.assertEqual(patch["base_commit"], revisions[patch["project"]])
            self.assertEqual(hashlib.sha256((ROOT / patch["patch"]).read_bytes()).hexdigest(), patch["patch_sha256"])
            self.assertEqual(patch["patch_sha256"], previous[patch["project"]]["patch_sha256"])
            self.assertEqual(patch["files"], [{"path": f["path"], "after_sha256": f["after_sha256"]} for f in previous[patch["project"]]["files"]])

    def test_audit_limits_do_not_claim_lfs_or_authored_directory_coverage(self):
        a = self.record["source_audit"]
        self.assertIs(a["project_list_matches"], True)
        self.assertEqual(a["local_manifest_files"], [])
        for key in ("source_writes_performed", "lfs_payloads_independently_rehashed", "ignored_files_audited", "authored_non_repo_directories_audited"):
            self.assertIs(a[key], False)

    def test_build_and_compiler_sandboxes_have_distinct_write_scopes(self):
        s = self.record["sandbox_and_preservation"]
        self.assertEqual(s["build_namespace_separation"], dict.fromkeys(("mnt", "net", "pid", "user"), True))
        for key in ("build_source_read_only", "build_out_read_write", "policy_check_all_four_namespaces_separate",
                    "policy_source_both_outs_and_sealed_inputs_read_only", "namespace_tmp_backed_inside_validation",
                    "all_sealed_hashes_and_identities_unchanged", "all_host_copies_rehashed"):
            self.assertIs(s[key], True)
        for key in ("build_sandbox_fallback_observed", "source_or_out_written_by_policy_check", "historical_outputs_rewritten"):
            self.assertIs(s[key], False)
        self.assertEqual((s["policy_check_count"], s["sealed_file_count"], s["policy_guard_count_including_capture_receipt"]), (3, 28, 29))
        self.assertEqual((s["sealed_file_bytes"], s["policy_result_file_count"], s["policy_result_bytes"]), (14838838, 9, 8180))
        self.assertEqual(s["policy_writable_directory"], "/work/validation/nezha-factory-policy-v9-1")

    def test_copied_tools_include_the_exact_four_nsjail_runtime_libraries(self):
        rows = self.record["tools_and_runtime"]
        pins = {"secilc": "1481d17c86dfc4b0ac47bd150f604425e718386379b690d06f60e417376b9a34",
            "sepolicy-analyze": "a271e82042286276651db28a34928bd149c745ccb6ba7cacf18b51258b909669",
            "nsjail": "3f97556c3cf8a83d3f5ae854e6dfc2f345355ead547dd661d07a369b6c2ba280",
            "libprotobuf-cpp-full.so": "28dbf3fdfb989552cbd7b1afa62c462d9e15f95eed13d063f0581dd569173bb7",
            "libnl.so": "7db8e04b8c9aee6c1f426f03e5b638fa089626c10ee4b83e688ff455dff13700",
            "libc++.so": "debd1e923abe6fe535980b69be8d1b66ca3a214ab865b46f4e3ce5c929d158f0",
            "libz-host.so": "b3fd753b1ccca89b8c339adbd4fec0fcd902f0e6a15310a2a2ccb5021cf248ec"}
        self.assertEqual({r["name"]: r["sha256"] for r in rows}, pins)
        self.assertEqual(len(rows), 7)
        for row in rows:
            self.assertGreater(row["size_bytes"], 0)
            self.assertEqual(row["captured_path"], ("bin/lib64/" if row["name"].endswith(".so") else "bin/") + row["name"])

    def test_publication_is_compact_metadata_not_raw_policy_or_private_logs(self):
        data = (ROOT / "research/dsp-policy-build.json").read_bytes()
        self.assertLess(len(data), 30000)
        text = data.decode()
        for forbidden in ("(allow ", "(neverallow ", "(neverallowx ", "/Users/", "BEGIN PRIVATE KEY", "androidboot.serialno="):
            self.assertNotIn(forbidden, text)
        document = (ROOT / "docs/dsp-policy-build.md").read_text()
        self.assertIn("../research/dsp-policy-build.json", document)
        self.assertIn("not a", document)
        self.assertIn("four assertions instead of five", document)
        self.assertIn("vendor_sepolicy.cil:6044", document)
        self.assertIn("390 `neverallowx`", document)


if __name__ == "__main__":
    unittest.main()
