"""Offline validation of source and build-host safety checks."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import workspace


class SourceConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = workspace.load_config()

    def test_all_references_are_pinned(self):
        self.assertGreaterEqual(len(self.config["references"]), 5)
        for reference in self.config["references"]:
            self.assertRegex(reference["commit"], r"^[0-9a-f]{40}$")

    def test_device_is_not_claimed_buildable(self):
        self.assertFalse(self.config["device"]["build_ready"])
        self.assertIsNone(self.config["device"]["lunch_target"])

    def test_init_uses_pinned_manifest_and_repo(self):
        command = workspace.init_command(self.config)
        manifest = workspace.reference_named(self.config, "evolution-manifest")
        tool = workspace.reference_named(self.config, "repo-tool")
        self.assertEqual(command[command.index("--manifest-branch") + 1], manifest["commit"])
        self.assertEqual(command[command.index("--repo-rev") + 1], tool["commit"])
        self.assertIn("--git-lfs", command)
        self.assertEqual(command[command.index("--manifest-name") + 1], "default.xml")
        self.assertNotIn("--no-repo-verify", command)

    def test_sync_never_forces_local_changes(self):
        command = workspace.sync_command(self.config, 8)
        self.assertIn("--jobs=8", command)
        self.assertNotIn("--force-sync", command)
        self.assertNotIn("--force-checkout", command)
        self.assertIn("--no-manifest-update", command)
        for jobs in (0, -1, 65):
            with self.assertRaises(ValueError):
                workspace.sync_command(self.config, jobs)

    def test_invalid_configuration_is_rejected(self):
        for field, value in (("commit", "main"), ("url", "ssh://git@github.com/repo"),
                             ("path", "../../outside"), ("path", "config/overwrite")):
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                config = json.loads(json.dumps(self.config))
                config["references"][0][field] = value
                path = Path(directory) / "invalid.json"
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    workspace.load_config(path)

    def test_overlapping_checkout_paths_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config = json.loads(json.dumps(self.config))
            config["references"][1]["path"] = config["references"][0]["path"] + "/nested"
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                workspace.load_config(path)


class FilesystemTests(unittest.TestCase):
    def test_paths_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("..", "../elsewhere", "/tmp/elsewhere", "."):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    workspace.checked_path(root, path)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "upstream").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                workspace.checked_path(root, "upstream/reference")

    def test_internal_and_dangling_symlinks_are_also_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "elsewhere").mkdir()
            for destination in (root / "elsewhere", root / "missing"):
                with self.subTest(destination=destination):
                    link = root / "upstream"
                    link.symlink_to(destination, target_is_directory=True)
                    with self.assertRaises(ValueError):
                        workspace.checked_path(root, "upstream/reference")
                    link.unlink()

    def test_nested_source_checkout_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".repo").mkdir()
            with self.assertRaisesRegex(ValueError, "Nested Repo"):
                workspace.refuse_nested_source(root / "nested" / "source")

    def test_probe_leaves_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            result = workspace.case_sensitive(Path(directory))
            self.assertIsInstance(result, bool)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_existing_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(workspace.existing_parent(root / "missing/child"), root)


class HostTests(unittest.TestCase):
    def setUp(self):
        self.config = workspace.load_config()

    def report(self, system, machine, case=True, ram=128, free=600):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(workspace.platform, "system", return_value=system), \
             patch.object(workspace.platform, "machine", return_value=machine), \
             patch.object(workspace, "case_sensitive", return_value=case), \
             patch.object(workspace, "memory_gib", return_value=ram), \
             patch.object(workspace.shutil, "which", return_value="/bin/tool"), \
             patch.object(workspace.shutil, "disk_usage") as disk:
            disk.return_value.free = free * workspace.GIB
            return workspace.host_report(Path(directory), self.config["host_requirements"])

    def test_linux_x86_64_passes(self):
        self.assertTrue(self.report("Linux", "x86_64")["supported_build_host"])

    def test_apple_silicon_and_arm_linux_are_not_native_build_hosts(self):
        for system, machine in (("Darwin", "arm64"), ("Linux", "aarch64")):
            self.assertFalse(self.report(system, machine)["supported_build_host"])

    def test_disk_ram_and_case_checks(self):
        for args in ({"free": 399}, {"ram": 32}, {"ram": None}, {"case": False}):
            self.assertFalse(self.report("Linux", "x86_64", **args)["supported_build_host"])

    def test_gpg_is_required_to_keep_repo_signature_verification(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(workspace.platform, "system", return_value="Linux"), \
             patch.object(workspace.platform, "machine", return_value="x86_64"), \
             patch.object(workspace, "case_sensitive", return_value=True), \
             patch.object(workspace, "memory_gib", return_value=128), \
             patch.object(workspace.shutil, "which", side_effect=lambda name: None if name == "gpg" else "/bin/tool"), \
             patch.object(workspace.shutil, "disk_usage") as disk:
            disk.return_value.free = 600 * workspace.GIB
            report = workspace.host_report(Path(directory), self.config["host_requirements"])
        self.assertFalse(report["checks"]["source_tools"])
        self.assertFalse(report["supported_build_host"])

    def test_preflight_failure_prevents_downloads(self):
        with patch.object(workspace, "host_report", return_value={"checks": {"linux": False}}), \
             patch.object(workspace, "run") as run:
            with self.assertRaises(ValueError):
                workspace.initialize(self.config, Path("/not-created"))
            run.assert_not_called()

    def test_dry_run_does_not_download_or_create_tree(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(workspace, "run") as run, contextlib.redirect_stdout(io.StringIO()):
            target = Path(directory) / "new-source-tree"
            workspace.initialize(self.config, target, dry_run=True)
            workspace.synchronize(self.config, target, jobs=4, dry_run=True)
            self.assertFalse(target.exists())
            run.assert_not_called()


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.reference = {"name": "example", "path": "upstream/example",
                          "url": "https://example.com/repo.git", "commit": "a" * 40}

    def test_fetch_refuses_nonempty_nonrepo(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(workspace, "run") as run:
            root = Path(directory)
            target = root / self.reference["path"]
            target.mkdir(parents=True)
            (target / "valuable.txt").write_text("keep me")
            with self.assertRaises(ValueError):
                workspace.fetch_reference(self.reference, root)
            self.assertEqual((target / "valuable.txt").read_text(), "keep me")
            run.assert_not_called()

    def test_verify_refuses_wrong_revision_origin_or_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = (root / self.reference["path"]).resolve()
            (target / ".git").mkdir(parents=True)
            valid = [str(target), self.reference["url"], self.reference["commit"], ""]
            for index, replacement in ((1, "https://other.example/repo"), (2, "b" * 40), (3, " M file")):
                values = valid.copy()
                values[index] = replacement
                with self.subTest(index=index), patch.object(workspace, "git_value", side_effect=values):
                    with self.assertRaises(ValueError):
                        workspace.verify_reference(self.reference, root)

    def test_existing_checkout_is_verified_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / self.reference["path"] / ".git").mkdir(parents=True)
            with patch.object(workspace, "verify_reference", return_value={"ok": True}) as verify, \
                 patch.object(workspace, "run") as run:
                self.assertEqual(workspace.fetch_reference(self.reference, root), {"ok": True})
                verify.assert_called_once_with(self.reference, root)
                run.assert_not_called()

    def test_failed_fetch_does_not_poison_final_path_and_can_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / self.reference["path"]
            with patch.object(workspace, "run", side_effect=subprocess.CalledProcessError(1, ["git", "fetch"])), \
                 patch.object(workspace, "verify_reference") as verify:
                with self.assertRaises(subprocess.CalledProcessError):
                    workspace.fetch_reference(self.reference, root)
                verify.assert_not_called()
            self.assertFalse(target.exists())
            self.assertEqual(list(target.parent.iterdir()), [])
            with patch.object(workspace, "run") as run, \
                 patch.object(workspace, "verify_reference", return_value={"ok": True}) as verify:
                self.assertEqual(workspace.fetch_reference(self.reference, root), {"ok": True})
                self.assertEqual(run.call_count, 4)
                self.assertEqual(verify.call_count, 2)
                first_path = verify.call_args_list[0].args[0]["path"]
                self.assertNotEqual(first_path, self.reference["path"])
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_staging_verification_failure_does_not_publish_checkout(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(workspace, "run"), \
             patch.object(workspace, "verify_reference", side_effect=ValueError("Wrong revision")):
            root = Path(directory).resolve()
            with self.assertRaises(ValueError):
                workspace.fetch_reference(self.reference, root)
            self.assertFalse((root / self.reference["path"]).exists())

    def test_interrupted_fetch_preserves_existing_empty_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / self.reference["path"]
            target.mkdir(parents=True)
            with patch.object(workspace, "run", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    workspace.fetch_reference(self.reference, root)
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_work_created_during_fetch_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / self.reference["path"]
            def verify(reference, root):
                target.mkdir()
                (target / "valuable.txt").write_text("preserve")
            with patch.object(workspace, "run"), patch.object(workspace, "verify_reference", side_effect=verify):
                with self.assertRaisesRegex(ValueError, "changed during fetch"):
                    workspace.fetch_reference(self.reference, root)
            self.assertEqual((target / "valuable.txt").read_text(), "preserve")

    def test_reference_git_directory_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / self.reference["path"]
            target.mkdir(parents=True)
            (root / "external-git").mkdir()
            (target / ".git").symlink_to(root / "external-git", target_is_directory=True)
            with patch.object(workspace, "git_value") as git:
                with self.assertRaises(ValueError):
                    workspace.verify_reference(self.reference, root)
                git.assert_not_called()


class SourceManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name).resolve()
        self.config = workspace.load_config()
        for relative in ("repo", "manifests", "manifests.git"):
            (self.source / ".repo" / relative).mkdir(parents=True, exist_ok=True)
        self.selector = self.source / ".repo/manifest.xml"
        self.selector.write_text('<manifest><include name="default.xml" /></manifest>')

    def fake_git_value(self, target, *arguments):
        target = Path(target)
        reference = workspace.reference_named(self.config, "repo-tool" if target.name == "repo" else "evolution-manifest")
        values = {
            ("rev-parse", "--show-toplevel"): str(target),
            ("rev-parse", "--absolute-git-dir"): str(target / ".git") if target.name == "repo" else str(self.source / ".repo/manifests.git"),
            ("remote", "get-url", "origin"): reference["url"],
            ("rev-parse", "HEAD"): reference["commit"],
            ("status", "--porcelain", "--untracked-files=all"): "",
        }
        return values[arguments]

    def test_both_embedded_repo_and_manifest_are_verified(self):
        with patch.object(workspace, "git_value", side_effect=self.fake_git_value) as git:
            workspace.verify_source_manifest(self.config, self.source)
        self.assertEqual(git.call_count, 10)
        self.assertEqual({call.args[0].name for call in git.call_args_list}, {"repo", "manifests"})

    def test_wrong_embedded_repo_revision_is_refused(self):
        def git_value(target, *arguments):
            if target.name == "repo" and arguments == ("rev-parse", "HEAD"):
                return "b" * 40
            return self.fake_git_value(target, *arguments)
        with patch.object(workspace, "git_value", side_effect=git_value):
            with self.assertRaisesRegex(ValueError, "Repo implementation revision"):
                workspace.verify_source_manifest(self.config, self.source)

    def test_source_git_origin_revision_and_changes_are_all_guarded(self):
        for arguments, replacement in (
            (("remote", "get-url", "origin"), "https://wrong.example/manifest"),
            (("rev-parse", "HEAD"), "b" * 40),
            (("status", "--porcelain", "--untracked-files=all"), " M default.xml"),
        ):
            with self.subTest(arguments=arguments):
                def git_value(target, *actual):
                    if target.name == "manifests" and actual == arguments:
                        return replacement
                    return self.fake_git_value(target, *actual)
                with patch.object(workspace, "git_value", side_effect=git_value):
                    with self.assertRaises(ValueError):
                        workspace.verify_source_manifest(self.config, self.source)

    def test_metadata_outside_source_checkout_is_refused(self):
        def git_value(target, *arguments):
            if arguments == ("rev-parse", "--absolute-git-dir"):
                return str(self.source.parent / "other-git")
            return self.fake_git_value(target, *arguments)
        with patch.object(workspace, "git_value", side_effect=git_value):
            with self.assertRaisesRegex(ValueError, "escapes"):
                workspace.verify_source_manifest(self.config, self.source)

    def test_symlinked_metadata_checkout_is_refused_before_git(self):
        target = self.source / ".repo/repo"
        target.rmdir()
        target.symlink_to(self.source / ".repo/manifests", target_is_directory=True)
        with patch.object(workspace, "git_value") as git:
            with self.assertRaises(ValueError):
                workspace.verify_source_manifest(self.config, self.source)
            git.assert_not_called()

    def test_manifest_selector_cannot_override_pinned_configuration(self):
        invalid = (
            '<manifest><include name="other.xml" /></manifest>',
            '<manifest><include name="default.xml" /><project name="unreviewed" /></manifest>',
            '<manifest><include name="default.xml" groups="other" /></manifest>',
            '<not-manifest><include name="default.xml" /></not-manifest>',
            '<manifest>',
        )
        for content in invalid:
            with self.subTest(content=content):
                self.selector.write_text(content)
                with self.assertRaises(ValueError):
                    workspace.verify_manifest_selection(self.source)

    def test_symlinked_manifest_selector_is_refused(self):
        self.selector.unlink()
        target = self.source / ".repo/manifests/default.xml"
        target.write_text("<manifest/>")
        self.selector.symlink_to(target)
        with self.assertRaises(ValueError):
            workspace.verify_manifest_selection(self.source)

    def test_unreviewed_local_manifests_are_preserved_and_refused(self):
        local = self.source / ".repo/local_manifests"
        local.mkdir()
        override = local / "device.xml"
        override.write_text('<manifest><project name="not-reviewed" /></manifest>')
        with self.assertRaisesRegex(ValueError, "Local manifests"):
            workspace.verify_manifest_selection(self.source)
        self.assertTrue(override.exists())

    def test_empty_local_manifest_directory_is_allowed(self):
        (self.source / ".repo/local_manifests").mkdir()
        workspace.verify_manifest_selection(self.source)

    def test_initialized_tree_is_only_verified_not_reinitialized(self):
        with patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command"), \
             patch.object(workspace, "verify_source_manifest") as verify, \
             patch.object(workspace, "run") as run, contextlib.redirect_stdout(io.StringIO()):
            workspace.initialize(self.config, self.source)
        verify.assert_called_once_with(self.config, self.source)
        run.assert_not_called()

    def test_sync_disables_self_update_and_rechecks_pins_afterward(self):
        with patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command", return_value=["python3", "repo"]), \
             patch.object(workspace, "verify_source_manifest") as verify, \
             patch.object(workspace, "run") as run, \
             patch.object(workspace.subprocess, "run") as process, \
             patch.object(workspace, "ROOT", self.source), \
             patch.dict(os.environ, {"GIT_LFS_SKIP_SMUDGE": "1"}), \
             contextlib.redirect_stdout(io.StringIO()):
            workspace.synchronize(self.config, self.source, jobs=4)
        self.assertEqual(verify.call_count, 2)
        environment = process.call_args.kwargs["env"]
        self.assertEqual(environment["REPO_SKIP_SELF_UPDATE"], "1")
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertNotIn("GIT_LFS_SKIP_SMUDGE", environment)
        self.assertEqual(process.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(process.call_args.kwargs["shell"], False)
        self.assertIn("manifest", run.call_args.args[0])

    def test_sync_failure_does_not_publish_resolved_manifest(self):
        with patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command"), \
             patch.object(workspace, "verify_source_manifest"), \
             patch.object(workspace, "run") as run, \
             patch.object(workspace.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["repo", "sync"])), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError):
                workspace.synchronize(self.config, self.source, jobs=4)
        run.assert_not_called()


class ProcessTests(unittest.TestCase):
    def test_commands_are_noninteractive_and_never_use_a_shell(self):
        with patch.object(workspace.subprocess, "run") as process:
            workspace.run(["git", "version"], capture=True)
        self.assertEqual(process.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(process.call_args.kwargs["shell"], False)
        self.assertEqual(process.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")


if __name__ == "__main__":
    unittest.main()
