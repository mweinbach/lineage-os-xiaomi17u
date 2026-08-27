"""Offline validation of source and build-host safety checks."""

import contextlib
import io
import json
import os
from pathlib import Path
import stat
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

    def report(self, system, machine, case=True, ram=128, free=600, host_mode="native", translation=None):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(workspace.platform, "system", return_value=system), \
             patch.object(workspace.platform, "machine", return_value=machine), \
             patch.object(workspace, "case_sensitive", return_value=case), \
             patch.object(workspace, "memory_gib", return_value=ram), \
             patch.object(workspace.shutil, "which", return_value="/bin/tool"), \
             patch.object(workspace, "rosetta_report", return_value=translation) as rosetta, \
             patch.object(workspace.shutil, "disk_usage") as disk:
            disk.return_value.free = free * workspace.GIB
            report = workspace.host_report(Path(directory), self.config["host_requirements"], host_mode)
            if host_mode == "native":
                rosetta.assert_not_called()
            return report

    def test_linux_x86_64_passes(self):
        report = self.report("Linux", "x86_64")
        self.assertTrue(report["supported_build_host"])
        self.assertTrue(report["native_build_host"])
        self.assertFalse(report["experimental_build_host"])
        self.assertEqual(report["host_status"], "native-ready")

    def test_apple_silicon_and_arm_linux_are_not_native_build_hosts(self):
        for system, machine in (("Darwin", "arm64"), ("Linux", "aarch64")):
            self.assertFalse(self.report(system, machine)["supported_build_host"])

    def test_disk_ram_and_case_checks(self):
        for args in ({"free": 399}, {"ram": 32}, {"ram": None}, {"case": False}):
            self.assertFalse(self.report("Linux", "x86_64", **args)["supported_build_host"])

    def test_explicit_rosetta_mode_passes_only_with_verified_execution(self):
        translation = {"marker_trusted": True, "probe_elf_verified": True,
                       "runtime": {"loader": True, "libc": True}, "probe_success": True}
        report = self.report("Linux", "aarch64", host_mode="apple-rosetta", translation=translation)
        self.assertTrue(report["supported_build_host"])
        self.assertFalse(report["native_build_host"])
        self.assertTrue(report["experimental_build_host"])
        self.assertEqual(report["host_status"], "experimental-rosetta-ready")
        self.assertIn("Experimental", report["note"])

    def test_rosetta_does_not_bypass_storage_ram_or_filesystem_checks(self):
        translation = {"marker_trusted": True, "probe_elf_verified": True,
                       "runtime": {"loader": True, "libc": True}, "probe_success": True}
        for options in ({"free": 399}, {"ram": 32}, {"case": False}):
            with self.subTest(options=options):
                report = self.report("Linux", "aarch64", host_mode="apple-rosetta", translation=translation, **options)
                self.assertFalse(report["supported_build_host"])
                self.assertEqual(report["host_status"], "blocked")

    def test_rosetta_needs_marker_runtime_and_real_elf_execution(self):
        valid = {"marker_trusted": True, "probe_elf_verified": True,
                 "runtime": {"loader": True, "libc": True}, "probe_success": True}
        for key, value in (("marker_trusted", False), ("probe_elf_verified", False),
                           ("probe_success", False), ("runtime", {"loader": False})):
            with self.subTest(key=key):
                report = self.report("Linux", "arm64", host_mode="apple-rosetta", translation=dict(valid, **{key: value}))
                self.assertFalse(report["supported_build_host"])

    def test_environment_variable_cannot_enable_rosetta_mode(self):
        with patch.dict(os.environ, {"EVOLUTION_HOST_MODE": "apple-rosetta", "ROSETTA_ENABLED": "1"}):
            self.assertFalse(self.report("Linux", "aarch64")["supported_build_host"])

    def test_source_and_output_free_space_are_not_added(self):
        with patch.dict(os.environ, {"OUT_DIR": "build-out"}):
            report = self.report("Linux", "x86_64", free=450)
        self.assertTrue(report["source_output_share_filesystem"])
        self.assertEqual(report["free_disk_gib"], 450)
        self.assertEqual(report["output_free_disk_gib"], 450)
        self.assertEqual(report["output_dir"], str(Path(report["source_dir"]) / "build-out"))

    def test_unknown_host_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown host mode"):
            workspace.host_report(Path("/not-created"), self.config["host_requirements"], "unsafe-arm")

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

    def test_rosetta_dry_run_does_not_execute_probe(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(workspace, "run") as run, \
             patch.object(workspace, "rosetta_report") as probe, contextlib.redirect_stdout(io.StringIO()):
            target = Path(directory) / "new-source-tree"
            workspace.initialize(self.config, target, dry_run=True, host_mode="apple-rosetta")
            workspace.synchronize(self.config, target, jobs=4, dry_run=True, host_mode="apple-rosetta")
            self.assertFalse(target.exists())
            probe.assert_not_called()
            run.assert_not_called()


class RosettaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.marker = self.root / "marker"
        self.marker.write_bytes(workspace.APPLE_BUILDER_MARKER_CONTENT)
        self.probe = self.root / "probe"
        self.probe.write_bytes(self.elf_header())
        self.probe.chmod(0o755)
        self.library = self.root / "library"
        self.library.write_bytes(self.elf_header(elf_type=3))

    @staticmethod
    def elf_header(machine=62, elf_class=2, endianness=1, elf_type=2):
        header = bytearray(64)
        header[:7] = bytes([0x7f, ord("E"), ord("L"), ord("F"), elf_class, endianness, 1])
        header[16:18] = elf_type.to_bytes(2, "little")
        header[18:20] = machine.to_bytes(2, "little")
        header[20:24] = (1).to_bytes(4, "little")
        return bytes(header)

    def fake_trusted_file(self, path, **kwargs):
        if path == workspace.APPLE_BUILDER_MARKER:
            return self.marker
        if path == workspace.ROSETTA_PROBE:
            self.assertTrue(kwargs["executable"])
            return self.probe
        self.assertIn(path, workspace.AMD64_RUNTIME.values())
        self.assertTrue(kwargs["allow_symlinks"])
        return self.library

    def report(self, stdout=None, exit_code=0, effect=None):
        result = subprocess.CompletedProcess([str(self.probe)], exit_code,
                                             workspace.ROSETTA_PROBE_OUTPUT + "\n" if stdout is None else stdout, "")
        with patch.object(workspace, "trusted_root_file", side_effect=self.fake_trusted_file), \
             patch.object(workspace.subprocess, "run", return_value=result, side_effect=effect) as process:
            report = workspace.rosetta_report("Linux", "aarch64")
        return report, process

    def test_direct_x86_64_execution_is_verified(self):
        report, process = self.report()
        self.assertTrue(report["marker_trusted"])
        self.assertTrue(report["probe_elf_verified"])
        self.assertTrue(all(report["runtime"].values()))
        self.assertTrue(report["probe_attempted"])
        self.assertTrue(report["probe_success"])
        self.assertEqual(process.call_args.args[0], [str(self.probe)])
        self.assertIs(process.call_args.kwargs["shell"], False)
        self.assertEqual(process.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(process.call_args.kwargs["timeout"], 15)

    def test_host_and_non_arm_linux_are_never_probed(self):
        for system, machine in (("Darwin", "arm64"), ("Linux", "x86_64"), ("Linux", "riscv64")):
            with self.subTest(system=system, machine=machine), \
                 patch.object(workspace, "trusted_root_file") as trusted, \
                 patch.object(workspace.subprocess, "run") as process:
                report = workspace.rosetta_report(system, machine)
                trusted.assert_not_called()
                process.assert_not_called()
                self.assertFalse(report["probe_success"])

    def test_missing_marker_prevents_all_execution(self):
        with patch.object(workspace, "trusted_root_file", side_effect=FileNotFoundError("missing marker")), \
             patch.object(workspace.subprocess, "run") as process:
            report = workspace.rosetta_report("Linux", "arm64")
        process.assert_not_called()
        self.assertFalse(report["marker_trusted"])
        self.assertTrue(report["errors"])

    def test_wrong_marker_content_is_refused(self):
        self.marker.write_bytes(b"unreviewed-arm-builder\n")
        report, process = self.report()
        process.assert_not_called()
        self.assertFalse(report["marker_trusted"])

    def test_scripts_and_arm_binaries_are_not_executed(self):
        for content in (b"#!/bin/sh\necho evolution-x86_64-probe-ok\n", self.elf_header(machine=183)):
            with self.subTest(content=content):
                self.probe.write_bytes(content)
                report, process = self.report()
                process.assert_not_called()
                self.assertFalse(report["probe_elf_verified"])
                self.assertFalse(report["probe_success"])

    def test_bad_elf_headers_are_rejected(self):
        for content in (self.elf_header(elf_class=1), self.elf_header(endianness=2),
                        self.elf_header(elf_type=1), self.elf_header()[:24], b"not ELF"):
            with self.subTest(content=content):
                self.probe.write_bytes(content)
                with self.assertRaises(ValueError):
                    workspace.require_x86_64_elf(self.probe)

    def test_runtime_must_be_x86_64_even_when_probe_is_valid(self):
        self.library.write_bytes(self.elf_header(machine=183))
        report, process = self.report()
        process.assert_not_called()
        self.assertFalse(all(report["runtime"].values()))
        self.assertFalse(report["probe_success"])

    def test_missing_loader_prevents_probe_execution(self):
        def trusted(path, **kwargs):
            if path == workspace.AMD64_RUNTIME["loader"]:
                raise FileNotFoundError("amd64 loader missing")
            return self.fake_trusted_file(path, **kwargs)
        with patch.object(workspace, "trusted_root_file", side_effect=trusted), \
             patch.object(workspace.subprocess, "run") as process:
            report = workspace.rosetta_report("Linux", "aarch64")
        process.assert_not_called()
        self.assertFalse(report["runtime"]["loader"])

    def test_probe_success_requires_exact_token_and_exit_zero(self):
        for output, code in (("", 0), (" " + workspace.ROSETTA_PROBE_OUTPUT, 0),
                             (workspace.ROSETTA_PROBE_OUTPUT + "\nextra", 0),
                             (workspace.ROSETTA_PROBE_OUTPUT, 1)):
            with self.subTest(output=output, code=code):
                report, _ = self.report(stdout=output, exit_code=code)
                self.assertFalse(report["probe_success"])
                self.assertTrue(report["errors"])

    def test_probe_timeout_and_exec_failure_do_not_approve_host(self):
        for error in (subprocess.TimeoutExpired([str(self.probe)], 15), OSError("Exec format error")):
            with self.subTest(error=error):
                report, process = self.report(effect=error)
                process.assert_called_once()
                self.assertTrue(report["probe_attempted"])
                self.assertFalse(report["probe_success"])

    def test_probe_environment_excludes_dynamic_loader_injection(self):
        with patch.dict(os.environ, {"LD_PRELOAD": "/untrusted.so", "LD_LIBRARY_PATH": "/untrusted"}):
            report, process = self.report()
        self.assertTrue(report["probe_success"])
        self.assertNotIn("LD_PRELOAD", process.call_args.kwargs["env"])
        self.assertNotIn("LD_LIBRARY_PATH", process.call_args.kwargs["env"])

    @staticmethod
    def metadata(mode, uid=0):
        return os.stat_result((mode, 1, 1, 1, uid, 0, 64, 0, 0, 0))

    def trust_probe(self, file_mode=0o755, uid=0, parent_mode=0o755, accessible=True):
        def lstat(path):
            if path == self.probe:
                return self.metadata(stat.S_IFREG | file_mode, uid)
            return self.metadata(stat.S_IFDIR | (parent_mode if path == self.root else 0o755))
        with patch.object(Path, "lstat", autospec=True, side_effect=lstat), \
             patch.object(Path, "stat", return_value=self.metadata(stat.S_IFREG | file_mode, uid)), \
             patch.object(workspace.os, "access", return_value=accessible):
            return workspace.trusted_root_file(self.probe, executable=True)

    def test_root_owned_immutable_probe_path_is_accepted(self):
        self.assertEqual(self.trust_probe(), self.probe)

    def test_untrusted_owner_permissions_and_parent_are_refused(self):
        for options in ({"uid": 1000}, {"file_mode": 0o777}, {"parent_mode": 0o777},
                        {"file_mode": 0o4755}, {"file_mode": 0o644}, {"accessible": False}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.trust_probe(**options)

    def test_marker_and_probe_symlinks_are_refused(self):
        link = self.root / "linked-probe"
        link.symlink_to(self.probe)
        def lstat(path):
            return self.metadata(stat.S_IFLNK | 0o777) if path == link else self.metadata(stat.S_IFDIR | 0o755)
        with patch.object(Path, "lstat", autospec=True, side_effect=lstat):
            with self.assertRaisesRegex(ValueError, "symlink"):
                workspace.trusted_root_file(link)

    def test_root_owned_multiarch_runtime_symlinks_are_allowed(self):
        link = self.root / "linked-runtime"
        link.symlink_to(self.library)
        def lstat(path):
            return self.metadata(stat.S_IFLNK | 0o777) if path == link else self.metadata(stat.S_IFDIR | 0o755)
        with patch.object(Path, "lstat", autospec=True, side_effect=lstat), \
             patch.object(Path, "stat", return_value=self.metadata(stat.S_IFREG | 0o755)):
            self.assertEqual(workspace.trusted_root_file(link, allow_symlinks=True), self.library)


class HostModeCliTests(unittest.TestCase):
    def test_doctor_passes_explicit_host_mode(self):
        with patch.object(workspace, "host_report", return_value={"supported_build_host": True}) as report, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workspace.main(["doctor", "--host-mode", "apple-rosetta", "--require-build-host"]), 0)
        self.assertEqual(report.call_args.args[2], "apple-rosetta")

    def test_init_and_sync_pass_explicit_host_mode(self):
        for command, method in (("init", "initialize"), ("sync", "synchronize")):
            with self.subTest(command=command), patch.object(workspace, method) as operation:
                self.assertEqual(workspace.main([command, "--host-mode", "apple-rosetta", "--dry-run"]), 0)
                self.assertEqual(operation.call_args.args[-1], "apple-rosetta")

    def test_cli_default_is_native(self):
        with patch.object(workspace, "host_report", return_value={"supported_build_host": False}) as report, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workspace.main(["doctor", "--require-build-host"]), 2)
        self.assertEqual(report.call_args.args[2], "native")


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
