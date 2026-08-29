"""Explicit target-root additions; public temporary fixtures and mocked processes."""

from contextlib import redirect_stderr, redirect_stdout
import errno
import io
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch

from scripts import twrp_build as build
from test_twrp_build import RevisionFixture
from test_twrp_patch_chains import ChainFixture


class TargetAdditionTests(RevisionFixture):
    def add_control(self, name="Android.bp", data=b"// reviewed source fixture\n"):
        path = self.control / build.TARGET_SOURCE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return data

    def revise_allowed(self, names=("Android.bp",)):
        return build.revise(self.config, self.paths, "native", self.previous, self.control,
                            allow_target_additions=names)

    def assert_old_receipt(self):
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)

    def failure_report(self):
        return json.loads(next(self.paths["report_dir"].glob("revise-failed-*.json")).read_text())

    def test_reviewed_addition_archives_absence_and_keeps_existing_files(self):
        data = self.add_control()
        self.change_target()
        retained = self.paths["out_dir"] / "cache/go/keep"
        retained.write_bytes(b"retained\n")
        report = self.revise_allowed()
        target = self.source / build.TARGET
        self.assertEqual((target / "Android.bp").read_bytes(), data)
        self.assertEqual((target / "Android.bp").stat().st_mode & 0o777, 0o644)
        self.assertEqual((target / "device.mk").read_text(), "# reviewed revision\n")
        self.assertEqual(retained.read_bytes(), b"retained\n")
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.assertEqual(report["added_target_files"], ["Android.bp"])
        self.assertEqual(report["attempted_target_additions"], ["Android.bp"])
        self.assertEqual(report["verified_target_additions"], ["Android.bp"])
        archive = Path(report["revision_archive"])
        intent = json.loads((archive / "target-additions.json").read_text())
        self.assertEqual(intent["before"], {"Android.bp": {"exists": False}})
        self.assertEqual(intent["allowed_target_additions"], ["Android.bp"])
        self.assertEqual(intent["previous_build_state_sha256"], build.sha256(self.before_state))
        self.assertEqual(intent["after"]["Android.bp"]["sha256"], build.sha256(data))
        self.assertEqual((archive / "target-after/Android.bp").read_bytes(), data)
        self.assertFalse((archive / "target-before/Android.bp").exists())
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.before_state)
        self.assertTrue(self.check()["prepared_sources_verified"])
        self.process_mock.assert_not_called()

    def test_multiple_additions_have_an_exact_idempotent_completed_retry(self):
        self.add_control()
        self.add_control("extra.bp")
        first = self.revise_allowed(("extra.bp", "Android.bp"))
        state = (self.paths["report_dir"] / build.STATE).read_bytes()
        second = self.revise_allowed(("Android.bp", "extra.bp"))
        self.assertEqual(first["verified_target_additions"], ["Android.bp", "extra.bp"])
        self.assertTrue(second["already_current"])
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), state)
        self.assertEqual(len(list((self.paths["report_dir"] / "build-revisions").iterdir())), 1)

    def test_default_guard_and_removal_guard_remain(self):
        self.add_control()
        with self.assertRaisesRegex(ValueError, "same file set"):
            self.revise()
        (self.control / build.TARGET_SOURCE / "notes.txt").unlink()
        with self.assertRaisesRegex(ValueError, "same file set"):
            self.revise_allowed()
        self.assert_old_receipt()
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_allowance_requires_the_exact_unique_root_file_set(self):
        self.add_control()
        bad = (True, "Android.bp", [True], ["./Android.bp"], ["../Android.bp"], ["/Android.bp"],
               ["nested/Android.bp"], ["Android.bp", "Android.bp"], ["Android.bp", "extra.bp"], ["*.bp"])
        for names in bad:
            with self.subTest(names=names), self.assertRaises(ValueError):
                self.revise_allowed(names)
        self.assert_old_receipt()
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_stale_allowance_and_nested_additions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly match"):
            self.revise_allowed()
        self.add_control("nested/Android.bp")
        with self.assertRaisesRegex(ValueError, "root-level"):
            self.revise_allowed(("nested/Android.bp",))
        self.assertFalse((self.source / build.TARGET / "nested").exists())
        self.assert_old_receipt()

    def test_existing_files_directories_and_links_are_never_adopted(self):
        data = self.add_control()
        path = self.source / build.TARGET / "Android.bp"
        for kind in ("matching-file", "directory", "dangling-link", "file-link"):
            if kind == "matching-file":
                path.write_bytes(data)
            elif kind == "directory":
                path.mkdir()
            else:
                path.symlink_to(self.root / "absent" if kind == "dangling-link" else self.source_file)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.revise_allowed()
            self.assertTrue(os.path.lexists(path))
            self.assert_old_receipt()
            self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())
            path.rmdir() if kind == "directory" else path.unlink()

    def test_only_enoent_means_absent(self):
        self.add_control()
        original = os.stat
        def denied(path, *args, **kwargs):
            if path == "Android.bp" and kwargs.get("dir_fd") is not None:
                raise PermissionError(errno.EACCES, "fixture stat denied")
            return original(path, *args, **kwargs)
        with patch.object(build.os, "stat", side_effect=denied), self.assertRaises(PermissionError):
            self.revise_allowed()
        self.assert_old_receipt()
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_exclusive_create_preserves_a_leaf_created_after_absence_check(self):
        self.add_control()
        path = self.source / build.TARGET / "Android.bp"
        original = os.open
        def race(name, flags, *args, **kwargs):
            if name == "Android.bp" and flags & os.O_EXCL:
                path.write_bytes(b"concurrent owner\n")
            return original(name, flags, *args, **kwargs)
        with patch.object(build.os, "open", side_effect=race), self.assertRaises(FileExistsError):
            self.revise_allowed()
        self.assertEqual(path.read_bytes(), b"concurrent owner\n")
        self.assert_old_receipt()
        report = self.failure_report()
        self.assertEqual(report["attempted_target_additions"], ["Android.bp"])
        self.assertEqual(report["verified_target_additions"], [])

    def test_ancestor_link_swap_is_not_followed_by_the_directory_walk(self):
        self.add_control()
        target = self.source / build.TARGET
        outside = self.root / "outside"
        outside.mkdir()
        original = os.open
        swapped = []
        def race(name, flags, *args, **kwargs):
            if name == target.name and flags & os.O_DIRECTORY and not swapped:
                target.rename(target.with_name("retained-target"))
                target.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return original(name, flags, *args, **kwargs)
        with patch.object(build.os, "open", side_effect=race), self.assertRaises(OSError):
            self.revise_allowed()
        self.assertEqual(swapped, [True])
        self.assertEqual(list(outside.iterdir()), [])
        self.assert_old_receipt()
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_replaced_identical_target_directory_is_rejected(self):
        self.add_control()
        target = self.source / build.TARGET
        replacement = self.root / "replacement"
        shutil.copytree(target, replacement)
        original = build.twrp_workspace.record_action
        def replace(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start":
                target.rename(self.root / "retained-target")
                replacement.rename(target)
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=replace), \
                self.assertRaisesRegex(ValueError, "Target directory changed"):
            self.revise_allowed()
        self.assertFalse((target / "Android.bp").exists())
        self.assert_old_receipt()

    def test_absence_and_payload_archives_are_checked_before_creation(self):
        self.add_control()
        original = build.twrp_workspace.record_action
        for relative in ("target-additions.json", "target-after/Android.bp"):
            def tamper(config, paths, action, report):
                result = original(config, paths, action, report)
                if action == "revise-start":
                    (Path(report["revision_archive"]) / relative).write_bytes(b"tampered\n")
                return result
            with self.subTest(relative=relative), patch.object(build.twrp_workspace, "record_action", side_effect=tamper), \
                    self.assertRaisesRegex(ValueError, "File changed"):
                self.revise_allowed()
            self.assertFalse((self.source / build.TARGET / "Android.bp").exists())
            self.assert_old_receipt()

    def test_control_drift_is_rejected_before_creation(self):
        self.add_control()
        original = build.twrp_workspace.record_action
        def tamper(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start":
                self.add_control(data=b"unreviewed bytes\n")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=tamper), \
                self.assertRaisesRegex(ValueError, "control bundle changed"):
            self.revise_allowed()
        self.assertFalse((self.source / build.TARGET / "Android.bp").exists())
        self.assert_old_receipt()

    def test_chmod_failure_retains_created_file_and_old_receipt(self):
        self.add_control()
        with patch.object(build.os, "fchmod", side_effect=OSError("fixture chmod failure")), \
                self.assertRaisesRegex(OSError, "fixture chmod failure"):
            self.revise_allowed()
        path = self.source / build.TARGET / "Android.bp"
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), b"")
        self.assertEqual(self.failure_report()["verified_target_additions"], [])
        self.assert_old_receipt()
        with self.assertRaisesRegex(ValueError, "Staged Nezha files differ"):
            self.revise_allowed()

    def test_second_addition_failure_preserves_first_without_adoption(self):
        data = self.add_control()
        self.add_control("extra.bp")
        original = build.create_target_addition
        def fail(target, relative, *args):
            if relative == "extra.bp":
                raise OSError("fixture second addition failure")
            return original(target, relative, *args)
        with patch.object(build, "create_target_addition", side_effect=fail), self.assertRaises(OSError):
            self.revise_allowed(("Android.bp", "extra.bp"))
        self.assertEqual((self.source / build.TARGET / "Android.bp").read_bytes(), data)
        self.assertFalse((self.source / build.TARGET / "extra.bp").exists())
        report = self.failure_report()
        self.assertEqual(report["attempted_target_additions"], ["Android.bp", "extra.bp"])
        self.assertEqual(report["verified_target_additions"], ["Android.bp"])
        self.assert_old_receipt()
        with self.assertRaisesRegex(ValueError, "Staged Nezha files differ"):
            self.revise_allowed(("Android.bp", "extra.bp"))

    def test_receipt_race_does_not_publish_over_another_owner(self):
        self.add_control()
        original = build.create_target_addition
        receipt = self.paths["report_dir"] / build.STATE
        def change(*args):
            result = original(*args)
            receipt.write_bytes(b"concurrent receipt owner\n")
            return result
        with patch.object(build, "create_target_addition", side_effect=change), \
                self.assertRaisesRegex(ValueError, "receipt changed"):
            self.revise_allowed()
        self.assertEqual(receipt.read_bytes(), b"concurrent receipt owner\n")
        self.assertTrue((self.source / build.TARGET / "Android.bp").is_file())
        self.assertEqual(self.failure_report()["verified_target_additions"], ["Android.bp"])

    def test_receipt_publication_failure_retains_added_target(self):
        self.add_control()
        original = build.write_new_file
        def fail(root, relative, data):
            if relative.endswith(".pending.json"):
                raise OSError("fixture state publication failure")
            return original(root, relative, data)
        with patch.object(build, "write_new_file", side_effect=fail), self.assertRaises(OSError):
            self.revise_allowed()
        self.assertTrue((self.source / build.TARGET / "Android.bp").is_file())
        self.assert_old_receipt()
        self.assertEqual(self.failure_report()["verified_target_additions"], ["Android.bp"])

    def test_completion_history_failure_reports_the_committed_addition(self):
        self.add_control()
        original = build.twrp_workspace.record_action
        def fail(config, paths, action, report):
            if action == "revise-complete":
                raise OSError("fixture completion history failure")
            return original(config, paths, action, report)
        with patch.object(build.twrp_workspace, "record_action", side_effect=fail):
            report = self.revise_allowed()
        self.assertTrue(report["revision_committed"])
        self.assertFalse(report["completion_report_written"])
        self.assertTrue(self.revise_allowed()["already_current"])

    def test_cli_rejects_allowance_for_non_revision_without_probes(self):
        with patch.object(build.twrp_workspace, "load_config") as load, redirect_stderr(io.StringIO()):
            self.assertEqual(build.main(["plan", "--allow-target-addition", "Android.bp"]), 2)
        load.assert_not_called()

    def test_cli_forwards_each_explicit_addition_to_revision(self):
        with patch.object(build.twrp_workspace, "load_config", return_value=self.config), \
                patch.object(build.twrp_workspace, "paths_for", return_value=self.paths), \
                patch.object(build, "revise", return_value={}) as revise, redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(["revise", "--previous-control-root", str(self.previous),
                                         "--allow-target-addition", "Android.bp",
                                         "--allow-target-addition", "extra.bp"]), 0)
        revise.assert_called_once_with(self.config, self.paths, "native", self.previous,
                                       allow_target_additions=["Android.bp", "extra.bp"])


class ChainedTargetAdditionTests(ChainFixture):
    def setup_addition(self):
        self.prepare_previous()
        self.append()
        (self.control / build.TARGET_SOURCE / "Android.bp").write_bytes(b"// reviewed fixture\n")

    def revise_allowed(self):
        return build.revise(self.config, self.paths, "native", self.previous, self.control,
                            allow_target_additions=("Android.bp",))

    def test_chain_and_target_addition_preserve_full_evidence(self):
        self.setup_addition()
        report = self.revise_allowed()
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertEqual(report["verified_target_additions"], ["Android.bp"])
        archive = Path(report["revision_archive"])
        self.assertTrue((archive / "chain-plan.json").is_file())
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.state_before)
        self.assertTrue(self.check()["prepared_sources_verified"])

    def test_tampered_addition_after_chain_apply_preserves_partial_source(self):
        self.setup_addition()
        original = build.apply_chain_steps
        def tamper(*args, **kwargs):
            result = original(*args, **kwargs)
            (args[6] / "target-after/Android.bp").write_bytes(b"tampered\n")
            return result
        with patch.object(build, "apply_chain_steps", side_effect=tamper), self.assertRaises(ValueError):
            self.revise_allowed()
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertFalse((self.source / build.TARGET / "Android.bp").exists())
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
