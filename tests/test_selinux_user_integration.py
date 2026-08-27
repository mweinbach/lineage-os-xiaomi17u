"""Offline checks of the public user-policy snapshot; never open private evidence."""

from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
POLICY_COMMIT = "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27"
USER_BUILD_SHA = "5dff46fcbbbe5ffd0d8a8a046ac93c070b61ebf2c63dc70c2ae3dd573df25fc8"
USER_CHECK_SHA = "e544850869664a710bdf3ab1eb34975fe309723055a35a2bbe5e53b4139ed98e"
PLATFORM_SHA = "ab01b223e9004c41964330b1b7ebe9b0a7a3250bda622eeecc988bc1bce21961"
INPUT_ORDER = [
    "/system/etc/selinux/plat_sepolicy.cil",
    "/system/etc/selinux/mapping/202504.cil",
    "/system_ext/etc/selinux/system_ext_sepolicy.cil",
    "/system_ext/etc/selinux/mapping/202504.cil",
    "/product/etc/selinux/product_sepolicy.cil",
    "/product/etc/selinux/mapping/202504.cil",
    "/vendor/etc/selinux/plat_pub_versioned.cil",
    "/vendor/etc/selinux/vendor_sepolicy.cil",
    "/odm/etc/selinux/odm_sepolicy.cil",
    "/system/etc/selinux/plat_sepolicy_genfs_202504.cil",
]


class SelinuxUserIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/selinux-user-integration.json").read_text())
        cls.prior = json.loads((ROOT / "research/factory-framework-contract.json").read_text())
        cls.strict = cls.record["strict_check"]
        cls.inputs = {row["runtime_path"]: row for row in cls.strict["input_order"]}
        cls.prior_checks = cls.prior["strict_policy_checks"]["checks"]
        cls.prior_userdebug = cls.prior_checks["evolution_factory_userdebug"]
        cls.groups = cls.record["remaining_group_analysis"]
        cls.build = cls.record["framework_build"]
        cls.observed = cls.record["observed_configuration"]["values"]
        cls.treble = cls.record["treble_labeling"]

    def test_historical_user_snapshot_keeps_device_and_unverified_origin(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        snapshot = self.record["snapshot"]
        self.assertEqual(snapshot["name"], "user-v7-framework-with-exact-factory-vendor-v2")
        self.assertLess(datetime.fromisoformat(snapshot["compiler_started_at"]),
                        datetime.fromisoformat(snapshot["compiler_completed_at"]))
        self.assertIs(snapshot["historical_result_not_replaced_by_later_source_hardening"], True)
        provenance = self.record["provenance"]
        self.assertEqual(provenance["factory_package_sha256"], FACTORY)
        self.assertEqual(FACTORY, self.prior["provenance"]["factory"]["sha256"])
        self.assertIn("user-provided", provenance["factory_source_kind"])
        self.assertIsNone(provenance["source_url"])
        for key in ("origin_verified", "oem_trust_root_authenticated", "internal_avb_pass_authenticates_origin"):
            self.assertIs(provenance[key], False)
        self.assertEqual(provenance["factory_capture_record"], "research/factory-framework-contract.json")
        self.assertEqual(provenance["historical_userdebug_record"], provenance["factory_capture_record"])

    def test_receipt_identities_link_new_and_preserved_checks_without_opening_them(self):
        receipts = self.record["receipts"]
        self.assertEqual(receipts["user_build"]["sha256"], USER_BUILD_SHA)
        self.assertEqual(receipts["user_check"]["sha256"], USER_CHECK_SHA)
        self.assertEqual(receipts["policy_capture"], self.prior["receipts"]["policy_capture"])
        self.assertEqual(receipts["userdebug_check"], self.prior["receipts"]["strict_evolution_factory"])
        self.assertEqual(receipts["variant_source"], self.prior["receipts"]["variant_source"])
        self.assertNotEqual(receipts["user_check"]["sha256"], receipts["userdebug_check"]["sha256"])
        self.assertEqual(len({row["path"] for row in receipts.values()}), len(receipts))
        for key, row in receipts.items():
            with self.subTest(receipt=key):
                path = PurePosixPath(row["path"])
                self.assertFalse(path.is_absolute())
                self.assertIn(path.parts[0], {"artifacts", "reports"})
                self.assertNotIn("..", path.parts)
                self.assertEqual(str(path), row["path"])
                self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(row["size_bytes"], 0)

    def test_public_source_files_and_projects_match_the_resolved_snapshot(self):
        snapshot_path = "research/source-snapshots/evolution-bka-20260827.xml"
        self.assertEqual(self.record["provenance"]["source_snapshot"], snapshot_path)
        snapshot = ET.parse(ROOT / snapshot_path)
        revisions = {row.get("path", row.get("name")): row.get("revision")
                     for row in snapshot.findall("project")}
        projects = self.record["source_projects"]
        self.assertEqual(projects["system/sepolicy"]["commit"], POLICY_COMMIT)
        for name, project in projects.items():
            self.assertEqual(project["commit"], revisions[name])
            self.assertTrue(project["repository"].startswith("https://"))
        files = self.record["source_files"]
        self.assertEqual(len({(row["project"], row["path"]) for row in files}), len(files))
        for row in files:
            with self.subTest(source=(row["project"], row["path"])):
                self.assertEqual(row["commit"], projects[row["project"]]["commit"])
                self.assertIn(row["receipt"], self.record["receipts"])
                self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(row["size_bytes"], 0)
                self.assertFalse(PurePosixPath(row["path"]).is_absolute())
                self.assertNotIn("..", PurePosixPath(row["path"]).parts)

    def test_framework_build_is_user_in_a_separate_out_not_a_rom_result(self):
        self.assertEqual((self.build["product"], self.build["release"], self.build["variant"]),
                         ("lineage_nezha", "bp4a", "user"))
        self.assertIs(self.build["passed"], True)
        self.assertEqual(self.build["receipt"], "user_build")
        self.assertEqual(self.build["out"], "/work/out/nezha-user-policy-20260827T2220Z")
        self.assertEqual(self.build["prior_out"], "/work/out/nezha-framework-20260827T1835Z")
        self.assertNotEqual(self.build["out"], self.build["prior_out"])
        self.assertIs(self.build["eleven_prior_artifacts_unchanged"], True)
        self.assertIs(self.build["is_complete_rom_build"], False)

    def test_observed_user_configuration_preserves_actual_flags_and_api(self):
        config = self.record["observed_configuration"]
        self.assertEqual(config["source_path"], self.build["out"] + "/soong/soong.lineage_nezha.variables")
        self.assertEqual(config["readback"]["sha256"],
                         "e00daa42d329e0c8495079854554dd1f6fe38c348da1a22bc2dfc4381545f3f7")
        self.assertIs(config["snapshot_not_post_hardening_configuration"], True)
        self.assertEqual(self.observed["DeviceName"], "nezha")
        self.assertEqual(self.observed["DeviceProduct"], self.build["product"])
        self.assertEqual(self.observed["Platform_sdk_version"], 36)
        self.assertEqual(self.observed["PlatformSepolicyVersion"], "202504")
        self.assertEqual(self.observed["BoardSepolicyVers"], "202504")
        for key in ("Debuggable", "Eng", "SelinuxIgnoreNeverallows", "EnforceSELinuxTrebleLabeling"):
            self.assertIs(self.observed[key], False)
        self.assertEqual(self.observed["SELinuxTrebleLabelingTrackingListFile"], "")
        for key in ("BoardVendorSepolicyDirs", "BoardOdmSepolicyDirs", "SystemExtPublicSepolicyDirs",
                    "SystemExtPrivateSepolicyDirs", "ProductPublicSepolicyDirs", "ProductPrivateSepolicyDirs"):
            self.assertEqual(self.observed[key], [])

    def test_ten_inputs_keep_order_origins_and_total_bytes(self):
        rows = self.strict["input_order"]
        self.assertEqual([row["runtime_path"] for row in rows], INPUT_ORDER)
        self.assertEqual(self.strict["input_count"], len(rows))
        self.assertEqual(len(self.inputs), 10)
        self.assertEqual(self.strict["input_bytes"], sum(row["size_bytes"] for row in rows))
        self.assertEqual(self.strict["input_bytes"], 5361195)
        origins = Counter(row["origin"] for row in rows)
        self.assertEqual(origins, {"generated-evolution-framework": 7, "exact-captured-factory": 3})
        self.assertEqual(self.strict["framework_input_count"], origins["generated-evolution-framework"])
        self.assertEqual(self.strict["factory_input_count"], origins["exact-captured-factory"])
        self.assertEqual(self.strict["framework_input_count"] + self.strict["factory_input_count"], 10)
        for row in rows:
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(row["size_bytes"], 0)

    def test_factory_vendor_and_odm_bytes_match_both_prior_assemblies(self):
        factory = {row["runtime_path"]: row for row in self.prior_checks["factory"]["input_order"]}
        old = {row["runtime_path"]: row for row in self.prior_userdebug["input_order"]}
        exact = [row for row in self.strict["input_order"] if row["origin"] == "exact-captured-factory"]
        self.assertEqual([row["runtime_path"] for row in exact], INPUT_ORDER[6:9])
        for row in exact:
            for key in ("sha256", "size_bytes"):
                self.assertEqual(row[key], factory[row["runtime_path"]][key])
                self.assertEqual(row[key], old[row["runtime_path"]][key])

    def test_only_the_generated_platform_cil_changed_from_userdebug(self):
        old = {row["runtime_path"]: row for row in self.prior_userdebug["input_order"]}
        changed = [path for path in INPUT_ORDER if self.inputs[path]["sha256"] != old[path]["sha256"]]
        self.assertEqual(changed, [INPUT_ORDER[0]])
        self.assertEqual(self.inputs[INPUT_ORDER[0]]["sha256"], PLATFORM_SHA)
        self.assertEqual(self.inputs[INPUT_ORDER[0]]["size_bytes"], 3012624)
        self.assertEqual(self.prior_userdebug["input_bytes"] - self.strict["input_bytes"],
                         old[INPUT_ORDER[0]]["size_bytes"] - self.inputs[INPUT_ORDER[0]]["size_bytes"])
        framework = [row["runtime_path"] for row in self.strict["input_order"]
                     if row["origin"] == "generated-evolution-framework"]
        self.assertEqual(framework, INPUT_ORDER[:6] + INPUT_ORDER[9:])

    def test_four_newline_files_are_included_as_generated_framework_inputs(self):
        newline = hashlib.sha256(b"\n").hexdigest()
        self.assertEqual({path for path, row in self.inputs.items() if row["size_bytes"] == 1},
                         set(INPUT_ORDER[2:6]))
        for path in INPUT_ORDER[2:6]:
            self.assertEqual(self.inputs[path]["sha256"], newline)
            self.assertEqual(self.inputs[path]["origin"], "generated-evolution-framework")
        self.assertEqual(self.strict["input_files_omitted"], 0)

    def test_actual_tools_bind_to_user_build_and_keep_observer_separate(self):
        self.assertEqual(self.strict["tool_build_receipt"], self.build["receipt"])
        tools = self.strict["tools"]
        self.assertEqual(set(tools), {"secilc", "sepolicy-analyze", "nsjail", "sandbox-observer"})
        for name in ("secilc", "sepolicy-analyze"):
            self.assertEqual(tools[name]["path"], self.build["out"] + "/host/linux-x86/bin/" + name)
            self.assertEqual(tools[name]["elf_machine"], 62)
        self.assertEqual(tools["secilc"]["sha256"],
                         "1481d17c86dfc4b0ac47bd150f604425e718386379b690d06f60e417376b9a34")
        for name in ("sepolicy-analyze", "nsjail"):
            self.assertEqual(tools[name]["sha256"], self.prior["strict_policy_checks"]["tools"][name]["sha256"])
        self.assertEqual(tools["nsjail"]["path"], "/work/evolution/prebuilts/build-tools/linux-x86/bin/nsjail")
        self.assertEqual(tools["sandbox-observer"]["elf_machine"], 183)
        self.assertEqual(tools["sandbox-observer"]["path"], "/usr/bin/python3.12")
        self.assertIn("not a policy compiler", tools["sandbox-observer"]["provenance"])
        for tool in tools.values():
            self.assertRegex(tool["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(tool["size_bytes"], 0)

    def test_strict_failure_cannot_be_reclassified_as_binary_or_permissive_pass(self):
        self.assertEqual(self.strict["receipt"], "user_check")
        self.assertEqual(self.strict["compiler_flags"], ["-m", "-M", "true", "-G", "-c", "30"])
        self.assertEqual(self.strict["compiler_flags"], self.prior["strict_policy_checks"]["compiler_flags"])
        self.assertNotIn("-N", self.strict["compiler_flags"])
        self.assertEqual(self.strict["exit_code"], 255)
        self.assertIs(self.strict["passed"], False)
        self.assertEqual(self.strict["binary_outputs"], [])
        self.assertIsNone(self.strict["permissive_analysis"])
        for key in ("neverallow_checks_disabled", "source_or_policy_rules_changed", "stock_precompiled_policy_used"):
            self.assertIs(self.strict[key], False)
        self.assertEqual(self.strict["diagnostic_log"]["sha256"],
                         "05e912ac0c74087ac314333958d44782f51017d56645b77d76980285fe0f4fab")
        self.assertEqual(self.strict["diagnostic_log"]["size_bytes"], 4316)

    def test_hash_identity_and_source_guards_cover_every_input_and_old_artifact(self):
        guards = self.record["guards"]
        self.assertEqual(guards["input_files_before_after"], self.strict["input_count"])
        self.assertEqual(guards["framework_source_files_before_after"], self.strict["framework_input_count"])
        self.assertEqual(guards["tools_before_after"], len(self.strict["tools"]))
        self.assertEqual(guards["provenance_files_before_after"], 3)
        self.assertEqual(guards["historical_artifacts_before_after"], 11)
        self.assertIs(guards["all_hashes_and_identities_unchanged"], True)
        self.assertEqual(guards["errors"], [])
        self.assertEqual(set(guards["source_projects_clean_before_and_after"]), {"external/selinux", "system/sepolicy"})
        for project, row in guards["source_projects_clean_before_and_after"].items():
            self.assertEqual(row["head"], self.record["source_projects"][project]["commit"])
            self.assertIs(row["tracked_worktree_clean"], True)
        for key in ("android_source_modified", "android_out_modified", "new_build_or_vm_started_by_check",
                    "phone_accessed", "firmware_executed"):
            self.assertIs(guards[key], False)

    def test_sandbox_observation_keeps_tmp_inside_the_fresh_validation_directory(self):
        sandbox = self.record["sandbox"]
        destination = PurePosixPath(sandbox["validation_directory"])
        self.assertEqual(str(destination), "/work/validation/nezha-selinux-evolution-user-factory-v2")
        self.assertEqual(sandbox["namespace_tmp_backing_path"], str(destination / "tmp"))
        self.assertNotEqual(sandbox["namespace_tmp_backing_path"], "/tmp")
        self.assertEqual(sandbox["writable_backing_paths"], [str(destination)])
        expected_read_only = {
            "/", "/work/evolution", self.build["out"], self.build["prior_out"],
            str(destination / "inputs"), str(destination / "provenance"),
        }
        observed = sandbox["observed_read_only"]
        self.assertEqual({path for path, value in observed.items() if value is True}, expected_read_only)
        self.assertEqual({path for path, value in observed.items() if value is False}, {str(destination), "/tmp"})
        for key in ("source_and_both_outs_and_inputs_read_only", "mount_flags_observed_by_trusted_python_before_compile",
                    "observed_matches_expected", "compiler_sandbox_recipe_preserved_in_receipt"):
            self.assertIs(sandbox[key], True)
        for path in (self.build["out"], self.build["prior_out"], "/work/evolution"):
            self.assertFalse(PurePosixPath(path).is_relative_to(destination))
        self.assertEqual(sandbox["observer_stdout"]["sha256"],
                         "4f30e20186f2ef3f1a9ac5b0e09d5ca0e4df6155f9bbb857d48d9736c0efd869")

    def test_five_assertion_sites_bind_eleven_locations_to_exact_inputs(self):
        diagnostics = self.strict["diagnostics"]
        sites = [(row["assertion"]["runtime_path"], row["assertion"]["line"]) for row in diagnostics]
        self.assertEqual(sites, [(INPUT_ORDER[7], 6044), (INPUT_ORDER[6], 5931), (INPUT_ORDER[6], 5746),
                                 (INPUT_ORDER[0], 24642), (INPUT_ORDER[0], 24637)])
        self.assertEqual(len(set(sites)), self.strict["assertion_sites"])
        self.assertEqual(self.strict["assertion_sites"], 5)
        self.assertEqual(sum(len(row["displayed_allow_locations"]) for row in diagnostics), 11)
        self.assertEqual(self.strict["displayed_allow_locations"], 11)
        for row in diagnostics:
            for location in [row["assertion"], *row["displayed_allow_locations"]]:
                self.assertIn(location["runtime_path"], self.inputs)
                self.assertGreater(location["line"], 0)
                if "source_location" in location:
                    source = location["source_location"]
                    self.assertTrue(source["path"].startswith("system/sepolicy/private/"))
                    self.assertGreater(source["line"], 0)
        sources = [row["displayed_allow_locations"][0]["source_location"] for row in diagnostics[:3]]
        self.assertEqual([(row["path"], row["line"]) for row in sources], [
            ("system/sepolicy/private/isolated_compute_app.te", 17),
            ("system/sepolicy/private/init_dev_config.te", 10),
            ("system/sepolicy/private/init_dev_config.te", 9),
        ])

    def test_binder_abbreviations_preserve_four_of_35_and_four_of_32(self):
        self.assertIs(self.strict["displayed_locations_are_complete_conflict_inventory"], False)
        short = [row for row in self.strict["diagnostics"] if row["abbreviated_matching_rules"] is not None]
        self.assertEqual(len(short), 2)
        self.assertEqual([(row["abbreviated_matching_rules"]["displayed"],
                           row["abbreviated_matching_rules"]["total"]) for row in short], [(4, 35), (4, 32)])
        for row in short:
            counts = row["abbreviated_matching_rules"]
            self.assertEqual(len(row["displayed_allow_locations"]), counts["displayed"])
            self.assertLess(counts["displayed"], counts["total"])
            self.assertTrue(all(item["runtime_path"] == INPUT_ORDER[7] for item in row["displayed_allow_locations"]))
        self.assertEqual([row["assertion"]["source_location"]["line"] for row in short], [2224, 2223])
        self.assertEqual([[location["line"] for location in row["displayed_allow_locations"]] for row in short],
                         [[5536, 5540, 7728, 11491], [5537, 5539, 7729, 11492]])
        self.assertEqual(sum(row["abbreviated_matching_rules"]["total"] for row in short),
                         self.groups["binder_objects"]["distinct_source_locations"])

    def test_variant_delta_preserves_the_failed_userdebug_record(self):
        comparison = self.record["variant_comparison"]
        self.assertEqual(comparison["historical_userdebug_assertion_sites"], self.prior_userdebug["assertion_sites_reported"])
        self.assertEqual(comparison["historical_userdebug_displayed_locations"], self.prior_userdebug["displayed_allow_locations"])
        self.assertEqual(comparison["user_assertion_sites"], self.strict["assertion_sites"])
        self.assertEqual(comparison["user_displayed_locations"], self.strict["displayed_allow_locations"])
        self.assertEqual(comparison["debug_guarded_sites_no_longer_reported"], {"llkd_ptrace": 15, "codec2_su_tcp": 1})
        removed = sum(comparison["debug_guarded_sites_no_longer_reported"].values())
        self.assertEqual(removed, comparison["historical_userdebug_assertion_sites"] - comparison["user_assertion_sites"])
        self.assertEqual(removed, comparison["historical_userdebug_displayed_locations"] - comparison["user_displayed_locations"])
        self.assertEqual(comparison["changed_runtime_path"], INPUT_ORDER[0])
        for key in ("only_one_of_seven_framework_input_hashes_changed", "same_factory_vendor_odm_hashes", "historical_receipts_preserved"):
            self.assertIs(comparison[key], True)
        self.assertIs(comparison["user_variant_is_compatible"], False)
        self.assertIs(self.prior["variant_source_analysis"]["actual_user_policy_compile_performed"], False)

    def test_su_is_one_historical_cil_declaration_not_a_binary_analysis(self):
        declaration = self.record["permissive_declaration"]
        self.assertEqual(declaration["declared_types"], ["su"])
        self.assertEqual(declaration["top_level_declaration_count_across_ten_inputs"], 1)
        self.assertEqual(declaration["runtime_path"], INPUT_ORDER[0])
        self.assertEqual(declaration["line"], 4231)
        self.assertEqual(declaration["input_sha256"], self.inputs[INPUT_ORDER[0]]["sha256"])
        self.assertEqual(declaration["normalized_form_sha256"], hashlib.sha256(b"(typepermissive su)").hexdigest())
        for key in ("binary_analysis_performed", "runtime_enforcement_inferred", "historical_v7_input_modified"):
            self.assertIs(declaration[key], False)
        self.assertIsNone(self.strict["permissive_analysis"])
        self.assertIn("not a compiled or loaded binary", declaration["scope"])

    def test_su_source_is_pinned_and_outside_the_closed_variant_guard(self):
        source = self.record["permissive_declaration"]["source"]
        self.assertEqual(source["project"], "system/sepolicy")
        self.assertEqual(source["commit"], POLICY_COMMIT)
        self.assertEqual((source["path"], source["line"]), ("private/su.te", 137))
        self.assertEqual(source["userdebug_macro_closes_at_line"], 134)
        self.assertGreater(source["line"], source["userdebug_macro_closes_at_line"])
        self.assertIs(source["declaration_is_outside_variant_guard"], True)
        captured = next(row for row in self.record["source_files"]
                        if (row["project"], row["path"]) == (source["project"], source["path"]))
        for key in ("commit", "sha256", "size_bytes"):
            self.assertEqual(source[key], captured[key])

    def test_upstream_allowlists_cannot_substitute_for_unfiltered_analysis(self):
        limits = self.record["upstream_permissive_check_limits"]
        self.assertIs(limits["checks_only_nondebuggable_nonrecovery_binary"], True)
        self.assertEqual(limits["precompiled_user_allowlist"], ["backuptool", "su"])
        self.assertEqual(limits["base_platform_user_allowlist"], ["su"])
        self.assertEqual(limits["consumer_path"], "system/sepolicy/build/soong/policy.go")
        self.assertEqual((limits["consumer_line"], limits["filter_allowlist_line"]), (542, 548))
        self.assertEqual(limits["precompiled_allowlist_path"], "system/sepolicy/Android.bp")
        self.assertEqual(limits["compatibility_generator_path"], "system/sepolicy/build/soong/compat_cil.go")
        self.assertEqual((limits["compatibility_ignore_neverallow_line"], limits["compatibility_allowlist_line"]), (169, 171))
        self.assertIs(limits["compatibility_target_is_not_our_strict_compiler"], True)
        self.assertIs(limits["unfiltered_permissive_analysis_required_after_strict_binary"], True)
        self.assertIs(limits["normal_target_pass_proves_zero_permissive_domains"], False)
        self.assertNotIn("-N", self.strict["compiler_flags"])

    def test_treble_warning_flag_is_distinct_from_neverallow_enforcement(self):
        self.assertEqual(self.treble["observed_flag"], "EnforceSELinuxTrebleLabeling")
        self.assertIs(self.treble["observed_value"], self.observed[self.treble["observed_flag"]])
        self.assertEqual(self.treble["product_variable"], "PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING")
        for key in ("unset_or_nontrue_exports_false", "ordinary_violations_are_warnings_unless_true"):
            self.assertIs(self.treble[key], True)
        self.assertIs(self.treble["same_as_secilc_neverallow_switch"], False)
        self.assertIs(self.treble["flag_changed_by_this_probe"], False)
        captured = {(row["project"], row["path"]) for row in self.record["source_files"]}
        for consumer in self.treble["consumers"]:
            self.assertIn((consumer["project"], consumer["path"]), captured)
            self.assertGreater(consumer["line"], 0)
        self.assertEqual(len(self.treble["consumers"]), 5)

    def test_treble_automatic_dependency_threshold_does_not_match_this_platform(self):
        dependency = self.treble["automatic_dependency"]
        self.assertEqual(dependency["minimum_platform_sepolicy_version"], "202604")
        self.assertEqual(dependency["observed_platform_sepolicy_version"], self.observed["PlatformSepolicyVersion"])
        meets = int(dependency["observed_platform_sepolicy_version"]) >= int(dependency["minimum_platform_sepolicy_version"])
        self.assertIs(dependency["observed_version_meets_threshold"], meets)
        self.assertIs(meets, False)
        self.assertEqual(dependency["kati_target"], "droidcore")
        self.assertEqual((dependency["kati_path"], dependency["kati_line"]), ("build/make/core/Makefile", 3567))
        self.assertEqual((dependency["soong_path"], dependency["soong_line"]), ("build/soong/filesystem/android_device.go", 438))
        self.assertIs(dependency["soong_also_requires_system_image"], True)

    def test_treble_missing_inputs_and_hard_errors_remain_separate_from_a_pass(self):
        skip = self.treble["missing_input_skip"]
        self.assertIs(skip["flag_true_does_not_prevent_skip"], True)
        self.assertIs(skip["skip_timestamp_is_not_test_pass"], True)
        self.assertEqual((skip["kati_source_line"], skip["soong_source_line"]), (3513, 1903))
        self.assertEqual(set(self.treble["required_input_classes"]), {
            "platform APK list", "vendor APK list", "platform seapp contexts", "vendor seapp contexts",
            "vendor file contexts", "combined precompiled binary", "framework-only precompiled binary", "aapt2",
        })
        self.assertEqual(len(self.treble["required_input_classes"]), 8)
        self.assertIs(self.treble["more_than_one_combined_binary_is_error"], True)
        hard = self.treble["user_violator_attribute_is_separate_hard_error"]
        self.assertEqual(hard["attribute"], "treble_labeling_violators")
        self.assertIs(hard["warning_switch_does_not_bypass"], True)
        self.assertIs(self.treble["tracking_list_observed_empty"], True)
        self.assertEqual(self.observed["SELinuxTrebleLabelingTrackingListFile"], "")
        self.assertIs(self.treble["test_executed"], False)
        self.assertIs(self.treble["test_passed"], False)
        self.assertIn("non-skipped", self.treble["source_based_next_requirement"])
        self.assertIn("no waivers", self.treble["source_based_next_requirement"])

    def test_three_static_analysis_groups_account_for_the_five_remaining_sites(self):
        expected = {"init_properties": 2, "isolated_compute": 1, "binder_objects": 2}
        self.assertEqual({name: self.groups[name]["assertion_sites"] for name in expected}, expected)
        self.assertEqual(sum(self.groups[name]["assertion_sites"] for name in expected), self.strict["assertion_sites"])
        for name in expected:
            self.assertIs(self.groups[name]["candidate_compiled"], False)
            self.assertGreater(self.groups[name]["tests_passed"], 0)
        for key in ("all_analysis_inputs_preserved", "all_assertions_retained", "full_private_inventories_not_redistributed"):
            self.assertIs(self.groups[key], True)
        self.assertIs(self.groups["source_changes_or_derivative_compiles_performed"], False)

    def test_rejected_init_mapping_widening_keeps_its_broad_static_footprint(self):
        init = self.groups["init_properties"]
        mapping = init["factory_evolution_and_source_identity_map"]
        self.assertEqual((mapping["attribute"], mapping["members"]), ("init_202504", ["init"]))
        self.assertEqual(mapping["source_path"], "private/compat/202504/202504.cil")
        self.assertIs(init["mapping_split_hypothesis_supported"], False)
        difference = init["mapping_difference"]
        self.assertEqual((difference["factory_only_form_count"], difference["evolution_only_form_count"]), (3, 0))
        self.assertEqual(difference["only_differing_symbol"], "sysfs_therm_202504")
        self.assertIs(difference["init_mapping_difference_observed"], False)
        footprint = init["rejected_widening_static_footprint"]
        self.assertEqual(footprint["direct_atom_occurrences_audited"], 2107)
        self.assertEqual(footprint["changed_attribute_sets"], 17)
        self.assertIs(footprint["adds_mlstrustedsubject"], True)
        self.assertEqual(footprint["affected_allow_forms"], 1414)
        self.assertEqual(sum(footprint[key] for key in (
            "allow_forms_with_new_subject", "allow_forms_with_new_target", "allow_forms_with_removed_target")),
            footprint["affected_allow_forms"])
        self.assertEqual(footprint["affected_neverallow_forms"], 108)
        self.assertEqual(footprint["neverallow_forms_exempting_helper"], 100)
        self.assertLess(footprint["neverallow_forms_exempting_helper"], footprint["affected_neverallow_forms"])
        self.assertEqual(footprint["affected_dontaudit_forms"], 336)
        self.assertEqual(footprint["affected_transition_forms"], 331)
        self.assertEqual(footprint["affected_mls_constraint_forms"], 96)
        self.assertIs(footprint["counts_are_not_unique_effective_permission_deltas"], True)

    def test_init_helper_is_a_new_object_with_unverified_device_execution_requirements(self):
        init = self.groups["init_properties"]
        new = init["helper_is_explicit_new_object"]
        self.assertEqual(new["types"], ["init_dev_config", "init_dev_config_exec"])
        self.assertEqual(new["source_path"], "private/compat/202504/202504.ignore.cil")
        self.assertEqual(new["source_lines"], [12, 13])
        helper = init["helper_execution_contract"]
        self.assertEqual(helper["project"], "system/core")
        self.assertEqual(helper["commit"], self.record["source_projects"]["system/core"]["commit"])
        self.assertEqual(helper["path"], "rootdir/init.rc")
        self.assertEqual((helper["exec_start_line"], helper["service_line"], helper["process_label_line"]), (79, 1352, 1355))
        self.assertEqual(helper["exec_path_property"], "ro.vendor.init_dev_config.path")
        self.assertIs(helper["device_executable_or_required_property_writes_verified"], False)
        self.assertIn("Keep the identity mapping and both assertions", init["source_direction"])

    def test_isolated_compute_cause_is_missing_product_membership_not_changed_mapping(self):
        isolated = self.groups["isolated_compute"]
        assignment = isolated["factory_assignment"]
        self.assertEqual((assignment["runtime_path"], assignment["line"]), (INPUT_ORDER[4], 15))
        self.assertEqual((assignment["member"], assignment["attribute"]),
                         ("isolated_compute_app", "vendor_hal_dspmanager_client"))
        self.assertEqual(isolated["allowed_service_assignment"], {"runtime_path": INPUT_ORDER[7], "line": 659})
        self.assertIs(isolated["same_service_is_allowed_for_isolated_compute_in_both_assemblies"], True)
        self.assertIs(isolated["historical_isolated_compute_mapping_identical"], True)
        hypothetical = isolated["hypothetical_exact_membership"]
        self.assertIs(hypothetical["applied_to_source_or_input"], False)
        self.assertEqual(hypothetical["changed_attribute_sets"], 2)
        self.assertEqual(hypothetical["newly_applicable_existing_vendor_rule_lines"], list(range(6035, 6042)))
        self.assertEqual(hypothetical["neverallow_intersections_on_five_edges"], 0)
        for key in ("product_vendor_source_ownership_verified", "runtime_privacy_and_feature_behavior_verified"):
            self.assertIs(isolated[key], False)
        self.assertIs(hypothetical["complete_policy_pass_verified"], False)

    def test_dsp_permission_deltas_sum_to_four_binder_two_fd_and_zero_find(self):
        isolated = self.groups["isolated_compute"]
        edges = isolated["edges"]
        self.assertEqual(len(edges), 5)
        self.assertEqual(len({(row["source"], row["target"], row["class"]) for row in edges}), 5)
        added = Counter()
        for edge in edges:
            self.assertEqual(edge["after_hypothetical"], edge["factory"])
            self.assertEqual(set(edge["added"]), set(edge["after_hypothetical"]) - set(edge["before"]))
            self.assertLessEqual(set(edge["before"]), set(edge["after_hypothetical"]))
            added[edge["class"]] += len(edge["added"])
        self.assertEqual(added, {"binder": 4, "fd": 2, "service_manager": 0})
        hypothetical = isolated["hypothetical_exact_membership"]
        for cls, key in (("binder", "added_directed_binder_permissions"),
                         ("fd", "added_directed_fd_permissions"), ("service_manager", "added_service_find_permissions")):
            self.assertEqual(added[cls], hypothetical[key])
        directions = {("isolated_compute_app", "vendor_dspservice"), ("vendor_dspservice", "isolated_compute_app")}
        for cls, permissions in (("binder", {"call", "transfer"}), ("fd", {"use"})):
            rows = [row for row in edges if row["class"] == cls]
            self.assertEqual({(row["source"], row["target"]) for row in rows}, directions)
            for row in rows:
                self.assertEqual(set(row["added"]), permissions)
        service, = [row for row in edges if row["class"] == "service_manager"]
        self.assertEqual((service["source"], service["target"]), ("isolated_compute_app", "vendor_hal_dspmanager_aidlservice"))
        self.assertEqual(service["before"], ["find"])
        self.assertEqual(service["added"], [])
        self.assertIs(hypothetical["all_five_audited_edges_match_factory"], True)

    def test_binder_role_audit_counts_objects_without_promoting_them_to_processes(self):
        binder = self.groups["binder_objects"]
        self.assertEqual(binder["assertion_match_counts"], {"target_non_domain": 35, "source_non_domain": 32})
        objects = binder["objects"]
        self.assertEqual(len(objects), 5)
        self.assertEqual(len({row["type"] for row in objects}), 5)
        self.assertEqual(sum(row["source_matches"] for row in objects), binder["assertion_match_counts"]["source_non_domain"])
        self.assertEqual(sum(row["target_matches"] for row in objects), binder["assertion_match_counts"]["target_non_domain"])
        self.assertEqual(sum(binder["assertion_match_counts"].values()), binder["distinct_source_locations"])
        self.assertEqual((binder["distinct_source_locations"], binder["distinct_normalized_statements"]), (67, 65))
        self.assertEqual((binder["directed_concrete_edges"], binder["distinct_directed_permission_tuples"]), (39, 70))
        self.assertEqual(binder["related_fd_allow_forms"], 32)
        self.assertEqual(binder["role_r_domain_count"], 596)
        self.assertIs(binder["role_r_types_exactly_equal_domain_members"], True)
        self.assertEqual((binder["factory_context_files_audited"], binder["factory_context_bytes"]), (34, 562898))
        self.assertIs(binder["all_matches_from_factory_vendor_cil"], True)
        for row in objects:
            self.assertEqual(row["roles"], ["object_r"])
            self.assertIs(row["in_domain"], False)
            self.assertIs(row["provider_identity_verified_on_device"], False)
        single = [row for row in objects if len(row["eligible_provider_domains"]) == 1]
        self.assertEqual(len(single), 4)
        display, = [row for row in objects if len(row["eligible_provider_domains"]) != 1]
        self.assertEqual(display["type"], "vendor_hal_display_config_hwservice")
        self.assertEqual(len(display["eligible_provider_domains"]), 4)
        self.assertEqual(binder["process_transition_allow_and_entrypoint_matches_for_objects"], 0)
        self.assertIs(binder["normal_process_ipc_authorized_by_mistyped_rules"], False)
        self.assertIs(binder["all_four_single_provider_cases_already_have_process_binder_grants"], True)
        self.assertIn("not actual running server SIDs", binder["display_provider_limit"])
        for key in ("full_rule_inventory_public", "source_macro_origins_proven", "live_change_safety_verified"):
            self.assertIs(binder[key], False)

    def test_private_payloads_and_unperformed_rom_or_device_success_stay_absent(self):
        for value in self.record["limits"].values():
            self.assertIs(value, False)
        requirements = " ".join(self.record["remaining_validation"])
        for phrase in ("all assertions", "unfiltered permissive-domain analysis", "non-skipped Treble",
                       "without API spoofing", "separately authorized device tests"):
            self.assertIn(phrase, requirements)
        forbidden = {"raw_cil", "raw_xml", "raw_key", "private_key", "raw_log", "raw_rule", "rule_text",
                     "allow_rule", "neverallow_rule", "base64", "data_base64", "content", "serial", "imei", "imsi"}

        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for key, child in value.items():
                    if key.endswith("sha256") and child is not None:
                        self.assertRegex(child, r"^[0-9a-f]{64}$")
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
            elif isinstance(value, str):
                for marker in ("-----BEGIN PRIVATE KEY-----", "(allow ", "(neverallow ", "<manifest"):
                    self.assertNotIn(marker, value)

        inspect(self.record)


if __name__ == "__main__":
    unittest.main()
