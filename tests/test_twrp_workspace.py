"""Offline tests of isolated TWRP source provenance and mutation gates."""

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import twrp_workspace as twrp


PROJECT_SHA = "a" * 40
OTHER_SHA = "b" * 40
MANIFEST = """<manifest>
  <remote name="aosp" fetch="https://android.googlesource.com"/>
  <remote name="twrp" fetch="https://github.com/TWRP-Test"/>
  <default remote="aosp" revision="refs/tags/android-16.0.0_r1"/>
  <project name="platform/build" path="build/make" revision="%s"/>
  <project name="android_bootable_recovery" path="bootable/recovery" remote="twrp" revision="%s"/>
</manifest>""" % (PROJECT_SHA, OTHER_SHA)


class TemporaryWorkspace(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config = twrp.load_config()
        self.config["expected_project_count"] = 2
        self.config["pinned_projects"] = {"bootable/recovery": {
            "name": "android_bootable_recovery", "remote": "twrp",
            "url": "https://github.com/TWRP-Test/android_bootable_recovery",
            "branch": "twrp-16.0", "commit": OTHER_SHA}}
        self.paths = twrp.paths_for(self.config, self.root / "source", self.root / "out", self.root / "reports")
        self.source = self.paths["source_dir"]
        self.launcher = self.root / "launcher" / "repo"

    def make_projects(self):
        (self.source / ".repo").mkdir(parents=True, exist_ok=True)
        for relative in twrp.parse_manifest(MANIFEST):
            target = self.source / relative
            target.mkdir(parents=True, exist_ok=True)
            (target / ".git").write_text("mock Git metadata")

    def git_value(self, target, *args):
        relative = str(target.relative_to(self.source))
        expected = twrp.parse_manifest(MANIFEST)[relative]
        if args == ("rev-parse", "--show-toplevel"):
            return str(target)
        if args == ("rev-parse", "--absolute-git-dir"):
            return str(self.source / ".repo" / "projects" / (relative + ".git"))
        if args == ("rev-parse", "HEAD"):
            return expected["revision"]
        if args == ("remote", "get-url", expected["remote"]):
            return expected["url"]
        if args == ("status", "--porcelain", "--untracked-files=all"):
            return ""
        raise AssertionError(f"Unexpected Git read: {args}")

    def save_snapshot(self, text=MANIFEST):
        self.paths["report_dir"].mkdir()
        (self.paths["report_dir"] / twrp.SNAPSHOT).write_text(text)
        state = {**twrp.identity(self.config, self.paths),
                 "resolved_manifest_sha256": hashlib.sha256(text.encode()).hexdigest(),
                 "project_count": len(twrp.parse_manifest(text, resolved=True))}
        (self.paths["report_dir"] / twrp.STATE).write_text(json.dumps(state))


class ConfigurationTests(TemporaryWorkspace):
    def test_exact_source_and_repo_pins(self):
        self.assertEqual(self.config["manifest"]["commit"], "d2188a9345857fb078c391e8cb3e259a21e941e5")
        self.assertEqual(self.config["repo_tool"]["commit"], "b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77")
        self.assertEqual(self.config["manifest"]["branch"], "twrp-16.0")
        self.assertEqual(self.config["manifest"]["name"], "default.xml")

    def test_all_github_pins_match_the_audited_upstream_record(self):
        config = twrp.load_config()
        upstream = json.loads((twrp.ROOT / "research/twrp-upstream.json").read_text())
        self.assertEqual(len(config["pinned_projects"]), 36)
        self.assertEqual(config["expected_project_count"], 392)
        for pin in upstream["pinned_projects"]:
            self.assertEqual(config["pinned_projects"][pin["path"]]["commit"], pin["commit"])
            self.assertEqual(config["pinned_projects"][pin["path"]]["url"], pin["repository"])

    def test_init_is_shallow_pinned_and_keeps_signature_checks(self):
        command = twrp.init_command(self.config, self.launcher)
        for flag in ("--depth=1", "--git-lfs", "--current-branch", "--no-clone-bundle"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--manifest-branch") + 1], self.config["manifest"]["commit"])
        self.assertEqual(command[command.index("--repo-rev") + 1], self.config["repo_tool"]["commit"])
        self.assertNotIn("--no-repo-verify", command)

    def test_sync_has_no_overwrite_or_manifest_drift_flags(self):
        command = twrp.sync_command(self.config, self.launcher, 8)
        for flag in ("-c", "-j8", "--no-clone-bundle", "--no-tags", "--no-manifest-update", "--fail-fast"):
            self.assertIn(flag, command)
        for flag in ("--force-sync", "--force-checkout", "--no-repo-verify", "--prune", "--force-remove-dirty"):
            self.assertNotIn(flag, command)
        for jobs in (0, -1, 65, True, "8"):
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                twrp.sync_command(self.config, self.launcher, jobs)

    def test_default_plan_never_runs_processes_probes_or_writes(self):
        with patch.object(twrp.subprocess, "run", side_effect=AssertionError("No command allowed")), \
             patch.object(twrp, "preflight", side_effect=AssertionError("No probe allowed")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("No write allowed")), \
             patch.object(twrp, "load_config", return_value=self.config), \
             patch.object(twrp, "paths_for", return_value=self.paths), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(twrp.main([]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["action"], "plan")
        self.assertFalse(report["executes_commands"])

    def test_invalid_configuration_is_rejected(self):
        mutations = [("manifest", "commit", "main"), ("repo_tool", "url", "https://user:secret@example.com/repo"),
                     ("manifest", "url", "file:///tmp/repo"), ("manifest", "name", "other.xml"),
                     ("host_requirements", "min_free_disk_gib", 149),
                     ("host_requirements", "min_ram_gib", 15), ("host_requirements", "filesystem", "apfs")]
        path = self.root / "invalid.json"
        for section, field, value in mutations:
            config = copy.deepcopy(self.config)
            config[section][field] = value
            path.write_text(json.dumps(config))
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                twrp.load_config(path)


class PathTests(TemporaryWorkspace):
    def test_sources_outputs_and_reports_must_not_overlap(self):
        for output, reports in ((self.source / "out", self.root / "reports"),
                                 (self.root / "out", self.source),
                                 (self.root / "out", self.root / "out" / "reports")):
            with self.subTest(output=output, reports=reports), self.assertRaisesRegex(ValueError, "overlap"):
                twrp.paths_for(self.config, self.source, output, reports)

    def test_evolution_and_cache_paths_are_reserved(self):
        for source in ("/work/evolution", "/work/evolution/nested", "/work", "/work/out/evolution", "/work/cache"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "reserved"):
                twrp.paths_for(self.config, Path(source), self.root / "out", self.root / "reports")

    def test_nested_or_unrelated_checkouts_are_rejected(self):
        for metadata in (".repo", ".git"):
            with self.subTest(metadata=metadata):
                marker = self.root / metadata
                marker.mkdir()
                with self.assertRaisesRegex(ValueError, "nested"):
                    twrp.paths_for(self.config, self.source, self.root / "out", self.root / "reports")
                marker.rmdir()
        self.source.mkdir()
        (self.source / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "unrelated"):
            twrp.paths_for(self.config, self.source, self.root / "out", self.root / "reports")

    def test_source_metadata_can_exist_without_prior_runner_marker(self):
        (self.source / ".repo").mkdir(parents=True)
        self.assertEqual(twrp.paths_for(self.config, self.source, self.root / "out", self.root / "reports"), self.paths)

    def test_symlinks_and_traversal_are_rejected(self):
        for value in (Path("relative/path"), Path("/"), self.root / ".." / "outside"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                twrp.absolute_path(value)
        link = self.root / "linked"
        link.symlink_to(self.root / "missing", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            twrp.absolute_path(link / "source")


class HostTests(TemporaryWorkspace):
    def host_report(self, output_free=200, filesystem="ext4", checks=None):
        base = {"checks": checks or {"linux": True, "x86_64": True, "free_disk": True},
                "output_free_disk_gib": output_free, "supported_build_host": True,
                "host_status": "native-ready", "note": "Source preflight."}
        with patch.object(twrp.workspace, "host_report", return_value=base) as host, \
             patch.object(twrp, "filesystem_type", return_value=filesystem), \
             patch.object(twrp.workspace.shutil, "disk_usage", return_value=SimpleNamespace(free=output_free * twrp.workspace.GIB)):
            report = twrp.preflight(self.config, self.paths, "native")
        host.assert_called_once_with(self.source, self.config["host_requirements"], "native")
        return report

    def test_exact_ext4_and_output_capacity_are_required(self):
        self.assertTrue(self.host_report()["supported_build_host"])
        for filesystem in ("apfs", "ext2/ext3", "overlay"):
            with self.subTest(filesystem=filesystem):
                self.assertFalse(self.host_report(filesystem=filesystem)["supported_build_host"])
        self.assertFalse(self.host_report(output_free=149.99)["checks"]["output_free_disk"])

    def test_prior_architecture_and_rosetta_failures_stay_blocked(self):
        for check in ("linux", "x86_64", "trusted_apple_builder", "x86_64_execution", "case_sensitive"):
            with self.subTest(check=check):
                self.assertFalse(self.host_report(checks={check: False})["supported_build_host"])

    def test_out_dir_override_restores_environment(self):
        with patch.dict(os.environ, {"OUT_DIR": "/work/out/evolution"}):
            with twrp.output_environment(self.paths["out_dir"]):
                self.assertEqual(os.environ["OUT_DIR"], str(self.paths["out_dir"]))
            self.assertEqual(os.environ["OUT_DIR"], "/work/out/evolution")

    def test_mountinfo_selects_longest_mount_and_unescapes_spaces(self):
        path = self.root / "mountinfo"
        path.write_text("20 1 1:0 / / rw - overlay overlay rw\n"
                        "21 20 7:1 / /work rw - ext4 /dev/vda rw\n"
                        "22 21 7:2 / /work/not\\040ext4 rw - tmpfs tmpfs rw\n")
        self.assertEqual(twrp.filesystem_type(Path("/work/twrp-nezha"), path), "ext4")
        self.assertEqual(twrp.filesystem_type(Path("/work/not ext4/source"), path), "tmpfs")

    def test_failed_host_gate_precedes_launcher_and_network(self):
        with patch.object(twrp, "preflight", return_value={"checks": {"linux": False}}), \
             patch.object(twrp, "verify_launcher") as launcher, patch.object(twrp, "run") as run:
            for action in (lambda: twrp.initialize(self.config, self.paths, self.launcher, "native"),
                           lambda: twrp.synchronize(self.config, self.paths, self.launcher, "native", 8)):
                with self.assertRaisesRegex(ValueError, "host preflight"):
                    action()
            launcher.assert_not_called()
            run.assert_not_called()


class LauncherTests(TemporaryWorkspace):
    def setUp(self):
        super().setUp()
        (self.launcher.parent / ".git").mkdir(parents=True)
        self.launcher.write_text("# synthetic launcher; never executed")

    def values(self, target, *args):
        self.assertEqual(target, self.launcher.parent)
        return {("rev-parse", "--show-toplevel"): str(target),
                ("rev-parse", "HEAD"): self.config["repo_tool"]["commit"],
                ("remote", "get-url", "origin"): self.config["repo_tool"]["url"],
                ("status", "--porcelain", "--untracked-files=all"): ""}[args]

    def test_verified_repo_launcher_is_accepted(self):
        with patch.object(twrp, "git_value", side_effect=self.values):
            self.assertEqual(twrp.verify_launcher(self.config, self.launcher), self.launcher)

    def test_modified_origin_head_or_worktree_is_rejected(self):
        changes = {("rev-parse", "HEAD"): "f" * 40,
                   ("remote", "get-url", "origin"): "https://example.com/repo",
                   ("status", "--porcelain", "--untracked-files=all"): " M repo"}
        for changed, value in changes.items():
            def fake(target, *args):
                return value if args == changed else self.values(target, *args)
            with self.subTest(changed=changed), patch.object(twrp, "git_value", side_effect=fake), self.assertRaises(ValueError):
                twrp.verify_launcher(self.config, self.launcher)

    def test_a_copied_unversioned_launcher_cannot_execute(self):
        launcher = self.root / "repo"
        launcher.write_text("unversioned")
        with self.assertRaisesRegex(ValueError, "pinned standalone"):
            twrp.verify_launcher(self.config, launcher)

    def test_checkout_control_uses_twrp_pin_and_selector_checks(self):
        with patch.object(twrp.workspace, "verify_source_checkout") as checkout, \
             patch.object(twrp.workspace, "verify_manifest_selection") as selection:
            twrp.verify_control(self.config, self.source)
        self.assertEqual(checkout.call_count, 2)
        self.assertEqual(checkout.call_args_list[1].args[2], self.config["manifest"])
        selection.assert_called_once_with(self.source)


class ManifestTests(unittest.TestCase):
    def test_every_resolved_project_has_its_expected_remote_and_sha(self):
        projects = twrp.parse_manifest(MANIFEST, resolved=True)
        self.assertEqual(projects["build/make"]["url"], "https://android.googlesource.com/platform/build")
        self.assertEqual(projects["bootable/recovery"]["url"], "https://github.com/TWRP-Test/android_bootable_recovery")
        self.assertEqual(projects["bootable/recovery"]["revision"], OTHER_SHA)

    def test_unresolved_refs_are_only_allowed_before_the_snapshot(self):
        text = MANIFEST.replace(PROJECT_SHA, "refs/tags/android-16.0.0_r1")
        self.assertEqual(len(twrp.parse_manifest(text)), 2)
        with self.assertRaisesRegex(ValueError, "unresolved"):
            twrp.parse_manifest(text, resolved=True)

    def test_remote_alias_is_respected(self):
        text = MANIFEST.replace('name="twrp" fetch=', 'name="twrp" alias="origin" fetch=')
        self.assertEqual(twrp.parse_manifest(text)["bootable/recovery"]["remote"], "origin")

    def test_unreviewed_manifest_structures_and_paths_are_refused(self):
        variants = [MANIFEST.replace("<manifest>", '<manifest><include name="other.xml"/>'),
                    MANIFEST.replace("<manifest>", '<manifest><remove-project path="build/make"/>'),
                    MANIFEST.replace('path="build/make"', 'path="../outside"'),
                    MANIFEST.replace('path="build/make"', 'path="bootable/recovery"'),
                    MANIFEST.replace('path="build/make"', 'path=".repo/overwrite"'),
                    MANIFEST.replace("<manifest>", '<!DOCTYPE manifest [<!ENTITY x "y">]><manifest>'),
                    MANIFEST.replace("https://android.googlesource.com", "https://user:secret@example.com")]
        for text in variants:
            with self.subTest(text=text[:120]), self.assertRaises(ValueError):
                twrp.parse_manifest(text)


class ReviewedPinsTests(TemporaryWorkspace):
    def test_missing_or_moved_reviewed_github_projects_are_rejected(self):
        projects = twrp.parse_manifest(MANIFEST, resolved=True)
        twrp.validate_project_pins(self.config, projects, resolved=True)
        projects["bootable/recovery"]["revision"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "moved"):
            twrp.validate_project_pins(self.config, projects, resolved=True)
        projects["bootable/recovery"]["url"] = "https://example.com/repo"
        with self.assertRaisesRegex(ValueError, "overrides"):
            twrp.validate_project_pins(self.config, projects, resolved=True)

    def test_aosp_annotated_tags_are_checked_against_peeled_commits(self):
        selected = twrp.parse_manifest(MANIFEST.replace(PROJECT_SHA, "refs/tags/android-16.0.0_r1"))
        resolved = twrp.parse_manifest(MANIFEST, resolved=True)
        with patch.object(twrp, "git_value", return_value=PROJECT_SHA) as git:
            twrp.validate_resolved_selection(self.config, self.source, selected, resolved)
        git.assert_called_once_with(self.source / "build/make", "rev-parse", "--verify", "refs/tags/android-16.0.0_r1^{commit}")
        with patch.object(twrp, "git_value", return_value="f" * 40), self.assertRaisesRegex(ValueError, "differs"):
            twrp.validate_resolved_selection(self.config, self.source, selected, resolved)

    def test_unreviewed_non_github_moving_refs_are_rejected(self):
        selected = twrp.parse_manifest(MANIFEST.replace(PROJECT_SHA, "main"))
        resolved = twrp.parse_manifest(MANIFEST, resolved=True)
        with self.assertRaisesRegex(ValueError, "Unreviewed moving"):
            twrp.validate_resolved_selection(self.config, self.source, selected, resolved)


class ProjectVerificationTests(TemporaryWorkspace):
    def setUp(self):
        super().setUp()
        self.make_projects()

    def test_each_actual_head_remote_worktree_and_metadata_root_is_checked(self):
        with patch.object(twrp, "git_value", side_effect=self.git_value) as git:
            report = twrp.project_report(self.source, twrp.parse_manifest(MANIFEST, resolved=True))
        self.assertTrue(report["verified"])
        self.assertEqual(report["project_count"], 2)
        self.assertEqual(git.call_count, 10)

    def test_all_local_changes_and_revision_or_remote_mismatches_are_reported(self):
        def dirty(target, *args):
            if args == ("status", "--porcelain", "--untracked-files=all"):
                return " M Android.bp\n?? local-file"
            if args == ("rev-parse", "HEAD"):
                return "f" * 40
            if args[:2] == ("remote", "get-url"):
                return "https://example.com/wrong"
            return self.git_value(target, *args)
        with patch.object(twrp, "git_value", side_effect=dirty):
            report = twrp.project_report(self.source, twrp.parse_manifest(MANIFEST, resolved=True))
        self.assertFalse(report["verified"])
        self.assertEqual(len(report["failures"]), 6)
        self.assertTrue(all(not record["clean"] for record in report["projects"]))

    def test_missing_projects_can_resume_but_never_verify_complete(self):
        projects = {"missing/project": {"name": "platform/missing", "path": "missing/project",
                                        "revision": PROJECT_SHA, "remote": "aosp", "url": "https://example.com/project"}}
        report = twrp.project_report(self.source, projects, allow_missing=True)
        self.assertFalse(report["verified"])
        self.assertEqual(report["failures"], [])
        self.assertTrue(report["projects"][0]["missing"])
        self.assertTrue(twrp.project_report(self.source, projects)["failures"])

    def test_missing_git_metadata_does_not_authorize_overwriting_unmanaged_files(self):
        target = self.source / "build/make"
        (target / ".git").unlink()
        (target / "user-file").write_text("preserve me")
        with patch.object(twrp, "git_value", side_effect=self.git_value):
            report = twrp.project_report(self.source, twrp.parse_manifest(MANIFEST), allow_missing=True)
        self.assertTrue(report["failures"])
        self.assertEqual((target / "user-file").read_text(), "preserve me")

    def test_git_metadata_cannot_escape_checkout(self):
        def outside(target, *args):
            return "/somewhere/else/.git" if args == ("rev-parse", "--absolute-git-dir") else self.git_value(target, *args)
        with patch.object(twrp, "git_value", side_effect=outside):
            report = twrp.project_report(self.source, twrp.parse_manifest(MANIFEST))
        self.assertEqual(len(report["failures"]), 2)
        self.assertTrue(all("escapes" in failure for failure in report["failures"]))


class SnapshotTests(TemporaryWorkspace):
    def test_snapshot_requires_all_shas_and_associated_path_pin_identity(self):
        self.save_snapshot()
        self.assertEqual(len(twrp.load_snapshot(self.config, self.paths)), 2)
        changed = copy.deepcopy(self.config)
        changed["manifest"]["commit"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "identity differs"):
            twrp.load_snapshot(changed, self.paths)

    def test_changed_resolved_manifest_is_not_silently_accepted(self):
        self.save_snapshot()
        (self.paths["report_dir"] / twrp.SNAPSHOT).write_text(MANIFEST.replace(PROJECT_SHA, "f" * 40))
        with self.assertRaisesRegex(ValueError, "hash differs"):
            twrp.load_snapshot(self.config, self.paths)

    def test_report_files_are_never_overwritten(self):
        report = twrp.write_report(self.paths, "owned.json", "original")
        with self.assertRaises(FileExistsError):
            twrp.write_report(self.paths, "owned.json", "replacement")
        self.assertEqual(report.read_text(), "original")

    def test_symlinked_snapshot_is_rejected(self):
        self.save_snapshot()
        target = self.paths["report_dir"] / twrp.SNAPSHOT
        target.unlink()
        outside = self.root / "outside.xml"
        outside.write_text(MANIFEST)
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            twrp.load_snapshot(self.config, self.paths)


class OperationTests(TemporaryWorkspace):
    def test_initialization_refuses_nonempty_source_without_touching_it(self):
        self.source.mkdir()
        file = self.source / "do-not-touch"
        file.write_text("original")
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "run") as run, self.assertRaisesRegex(ValueError, "nonempty"):
            twrp.initialize(self.config, self.paths, self.launcher, "native")
        run.assert_not_called()
        self.assertEqual(file.read_text(), "original")

    def test_existing_verified_checkout_needs_no_prior_source_marker(self):
        (self.source / ".repo").mkdir(parents=True)
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "verify_control") as control, patch.object(twrp, "run") as run:
            record = twrp.initialize(self.config, self.paths, self.launcher, "apple-rosetta")
        control.assert_called_once_with(self.config, self.source)
        run.assert_not_called()
        self.assertTrue(record["already_initialized"])
        self.assertEqual(sorted(path.name for path in self.source.iterdir()), [".repo"])

    def test_dirty_sources_block_sync_before_network(self):
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "verify_control"), patch.object(twrp, "manifest_text", return_value=MANIFEST), \
             patch.object(twrp, "project_report", return_value={"failures": ["build/make: Local changes preserved"]}), \
             patch.object(twrp, "run") as run, self.assertRaisesRegex(ValueError, "Sync refused local"):
            twrp.synchronize(self.config, self.paths, self.launcher, "native", 8)
        run.assert_not_called()

    def test_sync_records_complete_manifest_and_provenance_outside_sources(self):
        self.make_projects()
        with patch.object(twrp, "require_host", return_value={"host_status": "native-ready"}), \
             patch.object(twrp, "verify_launcher"), patch.object(twrp, "verify_control"), \
             patch.object(twrp, "manifest_text", return_value=MANIFEST), \
             patch.object(twrp, "git_value", side_effect=self.git_value), patch.object(twrp, "run") as run:
            report = twrp.synchronize(self.config, self.paths, self.launcher, "native", 8)
        self.assertTrue(report["verified"])
        self.assertEqual(run.call_count, 1)
        self.assertIn("sync", run.call_args.args[0])
        self.assertTrue((self.paths["report_dir"] / twrp.SNAPSHOT).is_file())
        self.assertEqual(len(twrp.load_snapshot(self.config, self.paths)), 2)
        self.assertFalse((self.source / twrp.SNAPSHOT).exists())

    def test_repeat_sync_only_verifies_and_never_tracks_branch_drift(self):
        self.save_snapshot()
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "verify_control"), patch.object(twrp, "verify", return_value={"verified": True}) as verify, \
             patch.object(twrp, "run") as run:
            self.assertTrue(twrp.synchronize(self.config, self.paths, self.launcher, "native", 8)["verified"])
        run.assert_not_called()
        verify.assert_called_once()

    def test_freeze_captures_manual_sync_without_network_or_source_commands(self):
        self.make_projects()
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "verify_control"), patch.object(twrp, "manifest_text", return_value=MANIFEST), \
             patch.object(twrp, "git_value", side_effect=self.git_value), patch.object(twrp, "run") as run:
            report = twrp.freeze(self.config, self.paths, self.launcher, "native")
        run.assert_not_called()
        self.assertEqual(report["action"], "freeze-complete")
        self.assertTrue(report["verified"])

    def test_freeze_refuses_incomplete_checkout_without_publishing_snapshot(self):
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "verify_control"), patch.object(twrp, "manifest_text", return_value=MANIFEST), \
             self.assertRaisesRegex(ValueError, "incomplete"):
            twrp.freeze(self.config, self.paths, self.launcher, "native")
        self.assertFalse((self.paths["report_dir"] / twrp.SNAPSHOT).exists())

    def test_freeze_existing_snapshot_does_not_replace_it(self):
        self.save_snapshot()
        with patch.object(twrp, "require_host", return_value={}), patch.object(twrp, "verify_launcher"), \
             patch.object(twrp, "verify_control"), patch.object(twrp, "verify", return_value={"verified": True}) as verify, \
             patch.object(twrp, "run") as run:
            twrp.freeze(self.config, self.paths, self.launcher, "native")
        verify.assert_called_once()
        run.assert_not_called()

    def test_verify_records_local_changes_but_does_not_rebaseline_them(self):
        self.make_projects()
        self.save_snapshot()
        frozen = (self.paths["report_dir"] / twrp.SNAPSHOT).read_bytes()
        def dirty(target, *args):
            return " M Android.bp" if args[0] == "status" else self.git_value(target, *args)
        with patch.object(twrp, "verify_launcher"), patch.object(twrp, "verify_control"), \
             patch.object(twrp, "manifest_text", return_value=MANIFEST), patch.object(twrp, "preflight", return_value={}), \
             patch.object(twrp, "git_value", side_effect=dirty), self.assertRaisesRegex(ValueError, "verification failed"):
            twrp.verify(self.config, self.paths, self.launcher, "native")
        self.assertEqual((self.paths["report_dir"] / twrp.SNAPSHOT).read_bytes(), frozen)
        reports = list(self.paths["report_dir"].glob("verify-*.json"))
        self.assertEqual(len(reports), 1)
        self.assertFalse(json.loads(reports[0].read_text())["verified"])

    def test_subprocess_environment_keeps_lfs_and_signature_defaults(self):
        with patch.dict(os.environ, {"GIT_LFS_SKIP_SMUDGE": "1"}), patch.object(twrp.subprocess, "run") as run:
            twrp.run(["git", "status"], capture=True)
        environment = run.call_args.kwargs["env"]
        self.assertNotIn("GIT_LFS_SKIP_SMUDGE", environment)
        self.assertEqual(environment["REPO_SKIP_SELF_UPDATE"], "1")
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertFalse(run.call_args.kwargs["shell"])


if __name__ == "__main__":
    unittest.main()
