"""Check public TWRP source/stock records without a phone, network or blobs."""

import copy
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse

from scripts import twrp_dependencies, twrp_patch_state, twrp_workspace


ROOT = Path(__file__).resolve().parents[1]


def reviewed_patch_inputs():
    """Read the public controls with the same validators used by source tools."""
    snapshot = ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
    frozen = twrp_workspace.parse_manifest(snapshot.read_text(), resolved=True)
    config = twrp_workspace.load_config(ROOT / "config/twrp.json")
    reviewed = twrp_patch_state.patch_inventory(config, ROOT)
    reviewed["supplementary_projects"] = twrp_dependencies.descriptor(ROOT)
    return frozen, reviewed


def validate_record_owners(frozen, reviewed):
    """Resolve ownership from pins; an optional label cannot override it."""
    owners = twrp_patch_state.validate_patch_bases(frozen, reviewed)
    for patch in reviewed["patches"]:
        if ("source_owner" in patch
                and patch["source_owner"] != owners[patch["project"]]["kind"]):
            raise ValueError("Patch ownership label conflicts with its pinned source catalog")
    return owners


def single_patch_fixture(frozen, reviewed, patch):
    """Use a real pinned row for mutations without rescanning unrelated owners."""
    project = patch["project"]
    fixture = {"patches": [copy.deepcopy(patch)]}
    if project in frozen:
        return {project: copy.deepcopy(frozen[project])}, fixture
    matches = [row for row in reviewed["supplementary_projects"]["projects"]
               if row["path"] == project]
    if len(matches) != 1:
        raise ValueError("Fixture requires one real pinned supplementary owner")
    fixture["supplementary_projects"] = {"projects": copy.deepcopy(matches)}
    return {}, fixture


class TwrpRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = json.loads((ROOT / "research/twrp-upstream.json").read_text())
        cls.stock = json.loads((ROOT / "research/twrp-stock-contract.json").read_text())
        cls.previous = json.loads((ROOT / "research/recovery-plan.json").read_text())

    def test_minimal_manifest_selection_and_counts(self):
        manifest = self.upstream["manifest"]
        self.assertEqual(manifest["branch"], "twrp-16.0")
        self.assertEqual(manifest["commit"], "d2188a9345857fb078c391e8cb3e259a21e941e5")
        self.assertEqual(manifest["default_revision"], "refs/tags/android-16.0.0_r1")
        counts = manifest["project_counts"]
        self.assertEqual(counts["baseline"] - counts["baseline_replaced"]
                         + counts["overlay_added"] - counts["minimal_removals"], counts["final"])
        self.assertEqual(counts["aosp"] + counts["github"], counts["final"])
        self.assertEqual(counts["final"], 392)
        followup = manifest["linux_selection_followup"]
        self.assertEqual(counts["selected_linux"], 391)
        self.assertEqual(followup["selected_linux_count"], counts["final"] - 1)
        self.assertEqual(followup["excluded_project"]["path"], "prebuilts/bazel/darwin-x86_64")
        self.assertTrue(followup["all_other_expanded_project_paths_present"])
        self.assertFalse(followup["count_difference_is_incomplete_download"])

    def test_moving_project_references_are_explicit_full_pins(self):
        projects = self.upstream["pinned_projects"]
        self.assertEqual(len(projects), 36)
        self.assertEqual(len({row["path"] for row in projects}), len(projects))
        for row in projects:
            with self.subTest(project=row["path"]):
                self.assertRegex(row["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(row["branch"])
                self.assertEqual(urlparse(row["repository"]).hostname, "github.com")
                self.assertFalse(Path(row["path"]).is_absolute())
                self.assertNotIn("..", Path(row["path"]).parts)

    def test_patch_bases_match_the_reviewed_source_projects(self):
        pins = {row["path"]: row["commit"] for row in self.upstream["pinned_projects"]}
        for row in self.upstream["aosp_project_pins"]:
            pins[row["path"]] = row["commit"]
        frozen_catalog, reviewed = reviewed_patch_inputs()
        frozen = {path: row["revision"] for path, row in frozen_catalog.items()}
        self.assertEqual(len(frozen), 391)
        for path, commit in pins.items():
            with self.subTest(known_project=path):
                self.assertEqual(frozen[path], commit)
        series = json.loads((ROOT / "patches/twrp/series.json").read_text())
        self.assertEqual(series["manifest"]["commit"], self.upstream["manifest"]["commit"])
        supplements = json.loads((ROOT / "config/twrp-dependencies.json").read_text())
        self.assertEqual(supplements["base"]["manifest_commit"], self.upstream["manifest"]["commit"])
        self.assertEqual(supplements["base"]["project_count"], 391)
        supplementary = {row["path"]: row for row in supplements["projects"]}
        self.assertEqual(len(supplementary), len(supplements["projects"]))
        self.assertTrue(set(frozen).isdisjoint(supplementary))
        self.assertEqual(reviewed["patches"], series["patches"])
        owners = validate_record_owners(frozen_catalog, reviewed)
        self.assertEqual(set(owners), set(frozen) | set(supplementary))
        # The original queue still belongs to the unchanged Repo snapshot.
        # Additional standalone owners never overwrite a baseline identity.
        for patch in series["patches"][:14]:
            self.assertIn(patch["project"], frozen)
        for patch in series["patches"]:
            with self.subTest(patch=patch["id"]):
                resolved = owners[patch["project"]]
                self.assertEqual(patch["base_commit"], resolved["commit"])
                self.assertEqual(patch["repository"], resolved["url"])
                if patch["project"] in frozen:
                    self.assertEqual(resolved["kind"], "base")
                    self.assertEqual(patch["base_commit"], frozen[patch["project"]])
                else:
                    self.assertTrue(patch["project"] in supplementary,
                                    "Missing pinned supplementary owner: " + patch["project"])
                    owner = supplementary[patch["project"]]
                    # The catalog is authoritative even when an older immutable
                    # entry omits this descriptive label. Pins, origin and both
                    # Git blob identities remain mandatory in the real validator.
                    self.assertEqual(resolved["kind"], "supplementary")
                    self.assertEqual(patch["base_commit"], owner["commit"])
                    self.assertEqual(patch["repository"], owner["url"])

    def test_owner_labels_are_optional_but_cannot_conflict_with_pinned_ownership(self):
        frozen, reviewed = reviewed_patch_inputs()
        expected = validate_record_owners(frozen, reviewed)
        for patch in reviewed["patches"]:
            with self.subTest(patch=patch["id"]):
                fixture_base, fixture = single_patch_fixture(frozen, reviewed, patch)
                without_label = copy.deepcopy(fixture)
                without_label["patches"][0].pop("source_owner", None)
                self.assertEqual(validate_record_owners(fixture_base, without_label)[patch["project"]],
                                 expected[patch["project"]])
                mislabeled = copy.deepcopy(fixture)
                kind = expected[patch["project"]]["kind"]
                mislabeled["patches"][0]["source_owner"] = (
                    "base" if kind == "supplementary" else "supplementary")
                with self.assertRaisesRegex(ValueError, "ownership label conflicts"):
                    validate_record_owners(fixture_base, mislabeled)

    def test_supplementary_owner_validation_rejects_bad_pins_origins_and_git_blobs(self):
        frozen, reviewed = reviewed_patch_inputs()
        owners = validate_record_owners(frozen, reviewed)
        for patch in reviewed["patches"]:
            if owners[patch["project"]]["kind"] != "supplementary":
                continue
            fixture_base, fixture = single_patch_fixture(frozen, reviewed, patch)
            for case in ("unknown_owner", "wrong_commit", "wrong_origin", "missing_origin",
                         "missing_before_blob", "missing_after_blob"):
                with self.subTest(patch=patch["id"], case=case):
                    changed = copy.deepcopy(fixture)
                    item = changed["patches"][0]
                    # A descriptive label must never authorize any of these.
                    item["source_owner"] = "supplementary"
                    if case == "unknown_owner":
                        item["project"] = "unreviewed/source-owner"
                    elif case == "wrong_commit":
                        item["base_commit"] = "0" * 40
                    elif case == "wrong_origin":
                        item["repository"] = "https://example.invalid/unreviewed-source"
                    elif case == "missing_origin":
                        del item["repository"]
                    else:
                        phase = "before" if case == "missing_before_blob" else "after"
                        del item["files"][0][phase + "_git_blob"]
                    with self.assertRaises(ValueError):
                        validate_record_owners(fixture_base, changed)

    def test_supplementary_owners_cannot_overlap_the_base_or_device_target(self):
        frozen, reviewed = reviewed_patch_inputs()
        for path in (next(iter(frozen)), "device/xiaomi/nezha"):
            with self.subTest(path=path):
                changed = copy.deepcopy(reviewed)
                changed["supplementary_projects"]["projects"][0]["path"] = path
                with self.assertRaisesRegex(ValueError, "overlaps"):
                    validate_record_owners(frozen, changed)

    def test_source_review_does_not_claim_device_or_build_success(self):
        self.assertTrue(all(value is False for value in self.upstream["scope"].values()))
        self.assertFalse(self.upstream["encryption_constraints"]["runtime_decryption_verified"])
        self.assertFalse(self.upstream["first_stage_module_contract"]["actual_module_loading_verified"])
        self.assertFalse(self.upstream["validation"]["android_build_or_device_test_claimed"])

    def test_recovery_header_matches_prior_independent_factory_evidence(self):
        layout = self.stock["layout"]
        fresh = layout["fresh_header"]
        previous = self.previous["stock"]["headers"]["recovery"]
        for key in ("header_version", "kernel_size_bytes", "ramdisk_size_bytes"):
            self.assertEqual(fresh[key], previous[key])
        self.assertEqual((fresh["header_version"], fresh["header_size_bytes"],
                          fresh["page_size_bytes"], fresh["kernel_size_bytes"]), (4, 1584, 4096, 0))
        self.assertEqual(fresh["cmdline"], "")
        self.assertEqual(layout["stock_image"]["sha256"], previous["image_sha256"])
        self.assertEqual(layout["stock_image"]["size_bytes"], 104857600)
        self.assertFalse(layout["physical_phone_capacity_verified"])
        self.assertFalse(layout["kernel_embedded"])

    def test_stock_and_compile_only_contract_do_not_replace_vendor_boot(self):
        contract = self.stock["initial_target_contract"]
        self.assertEqual(contract["kernel_source_partition"], "boot")
        self.assertEqual(contract["dtb_bootconfig_modules_source_partition"], "vendor_boot")
        self.assertEqual(contract["max_package_image_bytes"], 104857600)
        for key in ("replace_vendor_boot", "copy_stock_init_adbd_recovery_or_monolithic_policy",
                    "duplicate_vendor_ramdisk_module_payloads",
                    "automatically_decrypt_mount_format_or_upgrade_userdata_keys"):
            self.assertFalse(contract[key])
        self.assertTrue(contract["authenticated_adb"])
        self.assertTrue(contract["enforcing_selinux"])

    def test_module_stage_and_touch_are_separate_runtime_dependencies(self):
        loading = self.stock["module_loading"]
        self.assertEqual(loading["recovery_ramdisk_module_count"], 0)
        self.assertEqual(loading["vendor_ramdisk_module_count"], 430)
        self.assertTrue(loading["do_not_reload_entire_vendor_ramdisk_list_from_recovery_rc"])
        self.assertFalse(loading["hard_closure_and_crc_matches_prove_runtime_admission"])
        touch = self.stock["display_and_input"]["touch"]
        self.assertTrue(touch["both_drivers_absent_from_vendor_boot"])
        self.assertEqual({row["filename"] for row in touch["driver_modules"]},
                         {"synaptics_tcm2.ko", "xiaomi_touch.ko"})
        self.assertEqual({row["source"] for row in touch["driver_modules"]}, {"vendor_dlkm"})
        for row in touch["crc_provider_coverage"].values():
            self.assertEqual(row["versioned_import_count"],
                             row["kernel_crc_match"] + row["module_crc_match_unique_payload"])
            self.assertEqual(row["unmatched_versioned_imports"], 0)
            self.assertFalse(row["module_loaded"])

    def test_display_requires_drm_and_has_no_runtime_proof(self):
        display = self.stock["display_and_input"]
        facts = display["kernel_config"]["facts"]
        self.assertEqual(facts["CONFIG_DRM"], "y")
        self.assertEqual(facts["CONFIG_DRM_KMS_HELPER"], "y")
        self.assertEqual(facts["CONFIG_FB"], "n")
        self.assertEqual(facts["CONFIG_DRM_FBDEV_EMULATION"], "n")
        self.assertTrue(all(value is False for value in display["runtime_claims"].values()))

    def test_crypto_policy_and_signing_checks_are_not_waived(self):
        self.assertFalse(self.stock["fstab"]["decryption_test_passed"])
        self.assertIn("wrappedkey_v0", self.stock["fstab"]["normal_fileencryption"])
        self.assertTrue(self.stock["policy_and_services"]["target_neverallow_checks_must_remain_enabled"])
        self.assertTrue(self.stock["policy_and_services"]["target_requires_enforcing_without_permissive_domains"])
        for key in ("oem_signing_keys_available", "custom_image_is_stock_signed",
                    "verification_disable_flags_allowed", "phone_stored_rollback_counters_verified"):
            self.assertFalse(self.stock["avb"][key])

    def test_public_records_contain_no_personal_identifiers_or_private_payloads(self):
        forbidden = {"serial", "serialno", "imei", "imsi", "meid", "email", "phone_number"}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertNotIn("/Users/", value)
                self.assertNotRegex(value, r"-----BEGIN .*PRIVATE KEY-----")
        check(self.upstream)
        check(self.stock)


if __name__ == "__main__":
    unittest.main()
