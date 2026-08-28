"""23-entry baseline and fixture-only successors; offline mocked processes.

The real packaging identities below describe the parked public composition.
No fixture entry is placed in the production series. Runtime fixtures use
clearly synthetic source text and do not prove real ADB security semantics.
"""

import copy
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from scripts import twrp_build as build
from scripts import twrp_patch_state as state
from test_twrp_patch_chains import ChainFixture
import test_twrp_patches as patch_tests


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA256 = "cc2fa6b5edf39619be5166d4888ecb8abf108bab6428d3a812df026df18fdd33"
PREFIX_23_SHA256 = "8f70a8034f55d4646beac906a3edf9ede454fd9fac512a1c471c90786900d8ed"
RESOURCES_ID = "0020-restore-common-mdpi-recovery-resources"
AUTH_ID = "0004-require-recovery-adb-auth"
FIXTURE_PACKAGING_ID = "fixture-only-packaging-at-slot24"
FIXTURE_USB_ID = "fixture-only-usb-transport-successor"
PACKAGING_SHA256 = "f3a56977157d0f7bd62e1ae001f815b021fb50aa19371a86a344ef2f68de2647"
PACKAGING_IDENTITIES = [
    {"path": "Android.bp", "mode": "100644", "predecessor_patch_id": RESOURCES_ID,
     "before_sha256": "1049726f463a715bd9e3d4714599de9e2be7185dbec1ceb19d1bbf99d8bd2cbf",
     "before_size_bytes": 20703, "before_git_blob": "87c1a57f513bdc1e1fcc7bca980886739c4ca047",
     "after_sha256": "5738f3924cd2e2cf023069892c61031ab749830e49a8f5f36005be3fa22a2dd2",
     "after_size_bytes": 20673, "after_git_blob": "8bf22f8d021465d425558be0b8e51f4a41cbb624"},
    {"path": "prebuilt/Android.mk", "mode": "100644",
     "before_sha256": "683d6256f3b5d17b6c03087b0ea27cd710911ebb1a91d1b357ada24e3bfd1cc7",
     "before_size_bytes": 29919, "before_git_blob": "8a07a5f1ff3c5811e267ad04d6e7cdc7f2d53e89",
     "after_sha256": "b36ce58dd712793c67985136a3d07fafc517d7525b06234e4128d87718c3874e",
     "after_size_bytes": 38823, "after_git_blob": "15995f7ad81edb39e5087eb3f5960435dfd961e4"},
    {"path": "prebuilt/relink.sh", "mode": "100755",
     "before_sha256": "21cdc935ff21e7047fb6c9e2e5ba0dd6c6d882c31302fb5ccdcdab21ad767010",
     "before_size_bytes": 332, "before_git_blob": "59171146f8db58c09aadf54d541e8be8df2bdb04",
     "after_sha256": "36b93ad83ae03432e2115f2120f1ca66378b079c5892c2ea9c4eb3f98bf2ae3b",
     "after_size_bytes": 4612, "after_git_blob": "91b876b692a3fa07756391b0eecb814beae4b987"},
]


def fixture_packaging_entry():
    return {"id": FIXTURE_PACKAGING_ID, "fixture_only_not_admitted": True,
            "project": "bootable/recovery", "base_commit": "b70f8e998b302381ecefc6e7f46df1614bd61afc",
            "repository": "https://github.com/TWRP-Test/android_bootable_recovery",
            "patch": "patches/twrp/fixture-only-packaging.patch", "patch_sha256": PACKAGING_SHA256,
            "files": copy.deepcopy(PACKAGING_IDENTITIES)}


class ActualCohortMetadataTests(ChainFixture):
    def actual_controls(self):
        raw = (ROOT / build.SERIES).read_bytes()
        rows = json.loads(raw)["patches"][:23]
        self.assertEqual(state.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()),
                         PREFIX_23_SHA256)
        return {"series_sha256": BASELINE_SHA256, "patches": rows}

    def test_actual_20_to_fixture_24_preserves_all_23_records_and_only_one_overlap(self):
        old = self.actual_controls()
        new = {"series_sha256": "f" * 64, "patches": [*old["patches"], fixture_packaging_entry()]}
        extension = state.validate_patch_extension(old, new)
        self.assertEqual(extension["previous_patch_count"], 23)
        self.assertEqual(new["patches"][:23], old["patches"])
        plan = state.patch_plan(new)
        chains = [(project, path, chain) for project, owner in plan["projects"].items()
                  for path, chain in owner["files"].items() if len(chain["steps"]) > 1]
        self.assertEqual(len(chains), 1)
        project, path, chain = chains[0]
        self.assertEqual((project, path), ("bootable/recovery", "Android.bp"))
        self.assertEqual([step["index"] for step in chain["steps"]], [19, 23])
        self.assertEqual([step["patch_id"] for step in chain["steps"]], [RESOURCES_ID, FIXTURE_PACKAGING_ID])
        self.assertEqual(sum(len(entry["files"]) for entry in new["patches"]), 41)
        self.assertEqual(sum(len(owner["files"]) for owner in plan["projects"].values()), 40)
        for path in ("prebuilt/Android.mk", "prebuilt/relink.sh"):
            self.assertEqual(len(plan["projects"][project]["files"][path]["steps"]), 1)
            self.assertNotIn("predecessor_patch_id", plan["projects"][project]["files"][path]["root"])

    def test_previous_global_patch_is_not_a_file_predecessor(self):
        old = self.actual_controls()
        for wrong in [entry["id"] for entry in old["patches"][20:23]] + [AUTH_ID, FIXTURE_PACKAGING_ID, "unknown"]:
            entry = fixture_packaging_entry()
            entry["files"][0]["predecessor_patch_id"] = wrong
            with self.subTest(predecessor=wrong), self.assertRaisesRegex(ValueError, "immediate predecessor"):
                state.patch_plan({"patches": [*old["patches"], entry]})

    def test_all_intervening_records_are_preserved_not_only_original_twenty(self):
        old = self.actual_controls()
        for index in (20, 21, 22):
            new = {"series_sha256": "f" * 64, "patches": copy.deepcopy(old["patches"]) + [fixture_packaging_entry()]}
            new["patches"][index]["reason"] = "unreviewed rewrite"
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "unchanged prefix"):
                state.validate_patch_extension(old, new)

    def test_actual_successor_root_size_hash_and_blob_must_all_continue_0020(self):
        old = self.actual_controls()
        for field, wrong in (("before_size_bytes", 20733), ("before_sha256", "0" * 64), ("before_git_blob", "0" * 40)):
            entry = fixture_packaging_entry()
            entry["files"][0][field] = wrong
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "discontinuous"):
                state.patch_plan({"patches": [*old["patches"], entry]})

    def test_successor_cannot_substitute_a_different_owner_pin(self):
        old = self.actual_controls()
        entry = fixture_packaging_entry()
        entry["base_commit"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "one full pinned"):
            state.patch_plan({"patches": [*old["patches"], entry]})


class NamedCohortFixture(ChainFixture):
    """Synthetic source bytes with the relevant real queue positions and IDs."""
    def setUp(self):
        super().setUp()
        owners = {"packages/modules/adb": "c" * 40, "build/make": "d" * 40,
                  "packages/modules/Virtualization": "e" * 40, "test/vts-testcase/hal": "f" * 40}
        for owner, revision in owners.items():
            self.frozen[owner] = {"name": owner, "path": owner, "revision": revision,
                                  "remote": "origin", "url": "https://example.org/" + owner}
        for number in (2, 3): self.unrelated(number)
        self.auth_before = b"auth_required = false;\ntransport = usb_and_tcp;\nroot = forbidden;\n"
        self.auth_after = self.auth_before.replace(b"auth_required = false", b"auth_required = true")
        self.append([("daemon/main.cpp", self.auth_before, self.auth_after, 0o644, None)],
                    identifier=AUTH_ID, project="packages/modules/adb")
        for number in range(5, 20): self.unrelated(number)
        self.resources_before = b"mdpi: disabled\nrequired: legacy\n"
        self.resources_after = b"mdpi: common\nrequired: legacy\n"
        self.append([("Android.bp", self.resources_before, self.resources_after, 0o644, None)], identifier=RESOURCES_ID)
        self.unrelated(21, "build/make", "0021-native-recovery-generic-system-image")
        self.unrelated(22, "packages/modules/Virtualization", "0022-native-recovery-trusty-avb-test")
        self.unrelated(23, "test/vts-testcase/hal", "0023-native-recovery-trusty-vintf-test")
        self.assertEqual(len(self.series["patches"]), 23)

    def unrelated(self, number, project=None, identifier=None):
        self.append([(f"fixture/{number}.bp", f"old {number}\n".encode(), f"new {number}\n".encode(), 0o644, None)],
                    identifier=identifier or f"{number:04d}-unrelated-fixture", project=project)

    def packaging(self):
        return self.append([("Android.bp", self.resources_after, b"mdpi: common\nrequired: reviewed\n", 0o644, RESOURCES_ID),
                            ("prebuilt/Android.mk", b"legacy install\n", b"explicit providers\n", 0o644, None),
                            ("prebuilt/relink.sh", b"copy unchecked\n", b"copy checked\n", 0o755, None)],
                           identifier=FIXTURE_PACKAGING_ID)

    def usb(self):
        return self.append([("daemon/main.cpp", self.auth_after,
                             self.auth_after.replace(b"transport = usb_and_tcp", b"transport = usb"),
                             0o644, AUTH_ID)], identifier=FIXTURE_USB_ID, project="packages/modules/adb")


class NamedCohortTransitionTests(NamedCohortFixture):
    def legacy_hash_contract(self):
        # A detached case has no running unittest outcome. Its nested subTest
        # therefore propagates assertion failures to our negative fixture's
        # assertRaises instead of recording them as failures of this test.
        probe = patch_tests.TwrpPatchTests("test_patch_bytes_and_source_versions_are_hash_bound")
        probe.patches = {row["id"]: row for row in self.series["patches"]}
        probe.raw = {key: (self.control / row["patch"]).read_bytes() for key, row in probe.patches.items()}
        probe.text = {key: raw.decode() for key, raw in probe.raw.items()}
        probe.test_patch_bytes_and_source_versions_are_hash_bound()

    def test_independent_legacy_hash_contract_accepts_only_explicit_chains(self):
        self.packaging()
        self.usb()
        self.legacy_hash_contract()

    def test_independent_legacy_hash_contract_rejects_wrong_link_and_pin(self):
        entry = self.packaging()
        original = copy.deepcopy(entry)
        for wrong in ("link", "pin", "implicit"):
            entry.clear()
            entry.update(copy.deepcopy(original))
            if wrong == "link": entry["files"][0]["predecessor_patch_id"] = self.series["patches"][22]["id"]
            elif wrong == "pin": entry["base_commit"] = "0" * 40
            else: del entry["files"][0]["predecessor_patch_id"]
            with self.subTest(wrong=wrong), self.assertRaises(AssertionError): self.legacy_hash_contract()

    def test_full_24_queue_rehearsal_uses_20_as_predecessor_and_applies_only_suffix(self):
        self.prepare_previous()
        entry = self.packaging()
        result = self.revise()
        forward = [identifier for identifier, live, reverse, check in self.apply_events if not live and not reverse and not check]
        reverse = [identifier for identifier, live, reversing, check in self.apply_events if not live and reversing and not check]
        self.assertEqual(forward, [row["id"] for row in self.series["patches"]])
        self.assertEqual(reverse, list(reversed(forward)))
        self.assertEqual([identifier for identifier, live, _, _ in self.apply_events if live], [entry["id"]])
        self.assertEqual((self.source / self.project / "Android.bp").read_bytes(), b"mdpi: common\nrequired: reviewed\n")
        self.assertEqual((self.source / "packages/modules/adb/daemon/main.cpp").read_bytes(), self.auth_after)
        archive = Path(result["revision_archive"])
        self.assertTrue((archive / "steps/0023/complete.json").is_file())
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.state_before)

    def test_four_to_later_usb_successor_preserves_auth_and_prior_packaging(self):
        self.prepare_previous()
        package, usb = self.packaging(), self.usb()
        result = self.revise()
        self.assertEqual(result["applied_patch_ids"], [package["id"], usb["id"]])
        plan = state.patch_plan(self.inventory())
        self.assertEqual([step["index"] for step in plan["projects"]["packages/modules/adb"]["files"]["daemon/main.cpp"]["steps"]], [3, 24])
        final = (self.source / "packages/modules/adb/daemon/main.cpp").read_bytes()
        self.assertEqual(final, b"auth_required = true;\ntransport = usb;\nroot = forbidden;\n")
        self.assertIn(b"mdpi: common", (self.source / self.project / "Android.bp").read_bytes())
        self.assertFalse(result["flash_admitted"])
        self.assertFalse(result["build_for_this_revision_verified"])

    def test_failed_usb_suffix_keeps_packaging_result_old_receipt_and_auth(self):
        self.prepare_previous()
        package, usb = self.packaging(), self.usb()
        original = self.fake_git
        def fail_usb(args, **kwargs):
            if "apply" in args and state.sha256(Path(args[-1]).read_bytes()) == usb["patch_sha256"]:
                raise subprocess.CalledProcessError(1, args)
            return original(args, **kwargs)
        self.run_mock.side_effect = fail_usb
        with self.assertRaises(subprocess.CalledProcessError): self.revise()
        self.assertIn(b"required: reviewed", (self.source / self.project / "Android.bp").read_bytes())
        self.assertEqual((self.source / "packages/modules/adb/daemon/main.cpp").read_bytes(), self.auth_after)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
        report = json.loads(next(self.paths["report_dir"].glob("revise-failed-*.json")).read_text())
        self.assertEqual(report["applied_patch_ids"], [package["id"]])
        self.assertEqual(report["attempted_patch_ids"], [package["id"], usb["id"]])
        self.run_mock.side_effect = original
        self.apply_events.clear()
        with self.assertRaises(ValueError): self.revise()
        self.assertFalse(self.apply_events)

    def test_stale_23_receipt_after_rehearsal_blocks_every_live_apply(self):
        self.prepare_previous()
        self.packaging()
        original = build.twrp_workspace.record_action
        def change(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start": (paths["report_dir"] / build.STATE).write_bytes(self.state_before + b" ")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=change), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(live for _, live, _, _ in self.apply_events))
        self.assertEqual((self.source / self.project / "Android.bp").read_bytes(), self.resources_after)

    def test_fresh_executable_mode_mismatch_blocks_full_queue_rehearsal(self):
        self.prepare_previous()
        self.packaging()
        path = self.source / self.project / "prebuilt/relink.sh"
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "mode differs"): self.revise()
        self.assertFalse(self.apply_events)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_reverse_failure_never_applies_24_to_live_sources(self):
        self.prepare_previous()
        self.packaging()
        original = self.fake_process
        def reverse_failure(args, **kwargs):
            if "--reverse" in args: raise subprocess.CalledProcessError(1, args)
            return original(args, **kwargs)
        self.process_mock.side_effect = reverse_failure
        with self.assertRaises(subprocess.CalledProcessError): self.revise()
        self.assertFalse(any(live for _, live, _, _ in self.apply_events))
        self.assertEqual((self.source / self.project / "Android.bp").read_bytes(), self.resources_after)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
