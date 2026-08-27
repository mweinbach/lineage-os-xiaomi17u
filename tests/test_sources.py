"""Offline validation of source and build-host safety checks."""

import contextlib
import io
import json
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
        self.assertNotIn("--no-repo-verify", command)

    def test_sync_never_forces_local_changes(self):
        command = workspace.sync_command(self.config, 8)
        self.assertIn("--jobs=8", command)
        self.assertNotIn("--force-sync", command)
        self.assertNotIn("--force-checkout", command)
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


if __name__ == "__main__":
    unittest.main()
