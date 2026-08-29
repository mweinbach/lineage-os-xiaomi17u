"""Offline tests for the narrow host/guest Apple Container workflow."""

import contextlib
import io
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import apple_container as apple
from scripts import container_task as guest


class ContainerConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = apple.load_config()

    def test_resources_and_experimental_mode_are_explicit(self):
        self.assertEqual(self.config["host_mode"], "apple-rosetta")
        self.assertEqual(self.config["volume_size_gib"], 800)
        self.assertEqual(self.config["cpus"], 16)
        self.assertEqual(self.config["memory_gib"], 128)

    def test_invalid_configuration(self):
        for key, value in (("cpus", 0), ("memory_gib", True), ("volume", "../outside"),
                           ("image", "image; command"), ("source_dir", "/host/source"),
                           ("source_dir", "/work/../outside"), ("host_mode", "native")):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                config = dict(self.config, **{key: value})
                path = Path(directory) / "config.json"
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    apple.load_config(path)

    def test_run_command_mounts_only_bundle_and_named_volume(self):
        command = apple.task_command(self.config, "init", Path("/project/.tools/bundle"), "a" * 64, "test")
        mounts = [command[index + 1] for index, value in enumerate(command) if value == "--mount"]
        self.assertEqual(mounts, [
            "type=volume,source=evolution-nezha-work,target=/work",
            "type=bind,source=/project/.tools/bundle,target=/control,readonly",
        ])
        self.assertIn("--rosetta", command)
        self.assertIn("--rm", command)
        for unsafe in ("--cap-add", "--ssh", "--privileged"):
            self.assertNotIn(unsafe, command)

    def test_detached_sync_preserves_named_container_for_logs(self):
        command = apple.task_command(self.config, "sync", Path("/bundle"), "a" * 64, "test", detach=True)
        self.assertIn("--detach", command)
        self.assertNotIn("--rm", command)

    def test_mount_delimiter_in_host_path_rejected(self):
        with self.assertRaises(ValueError):
            apple.task_command(self.config, "init", Path("/bad,path"), "a" * 64, "test")

    def test_build_context_is_only_recipe_directory(self):
        command = apple.build_command(self.config)
        self.assertEqual(command[-1], str(apple.ROOT / "containers/apple"))
        self.assertNotEqual(command[-1], str(apple.ROOT))

    def test_dry_run_never_calls_container_or_creates_bundle(self):
        with patch.object(apple, "run") as run, patch.object(apple, "prepare_bundle") as bundle, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(apple.main(["setup", "--dry-run"]), 0)
            self.assertEqual(apple.main(["sync", "--detach", "--dry-run"]), 0)
            run.assert_not_called()
            bundle.assert_not_called()

    def test_invalid_jobs_or_detach_option_stop_before_runtime(self):
        with patch.object(apple, "run") as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(apple.main(["init", "--detach"]), 2)
            self.assertEqual(apple.main(["sync", "--jobs", "0"]), 2)
            run.assert_not_called()

    def test_lock_is_forwarded_as_a_bundle_relative_path(self):
        for operation in ("init", "sync"):
            command = apple.task_command(self.config, operation, Path("/host/bundle"),
                                         "a" * 64, "test", source_lock=guest.SOURCE_LOCK_FILES[0])
            self.assertEqual(command[-2:], ["--source-lock", guest.SOURCE_LOCK_FILES[0]])
            self.assertNotIn("/host/bundle/config/evolution-source-lock.json", command)

    def test_unreviewed_or_non_source_lock_option_stops_before_runtime(self):
        with patch.object(apple, "run") as run, patch.object(apple, "prepare_bundle") as bundle, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(apple.main(["status", "--source-lock", guest.SOURCE_LOCK_FILES[0]]), 2)
            run.assert_not_called()
            bundle.assert_not_called()
        for operation, source_lock in (("shell", guest.SOURCE_LOCK_FILES[0]),
                                       ("init", "/host/config/evolution-source-lock.json")):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                apple.task_command(self.config, operation, Path("/bundle"), "a" * 64,
                                   "test", source_lock=source_lock)

    def test_locked_preview_validates_without_creating_bundle_or_running_container(self):
        output = io.StringIO()
        with patch.object(apple, "source_lock_path", return_value=guest.SOURCE_LOCK_FILES[0]) as selected, \
             patch.object(apple, "run") as run, patch.object(apple, "prepare_bundle") as bundle, \
             contextlib.redirect_stdout(output):
            self.assertEqual(apple.main(["init", "--source-lock", "/host/reviewed-lock.json", "--dry-run"]), 0)
        selected.assert_called_once_with("/host/reviewed-lock.json")
        self.assertIn("--source-lock config/evolution-source-lock.json", output.getvalue())
        self.assertNotIn("/host/reviewed-lock.json", output.getvalue())
        run.assert_not_called()
        bundle.assert_not_called()


class VolumeTests(unittest.TestCase):
    def setUp(self):
        self.config = apple.load_config()
        self.volume = {"name": self.config["volume"], "format": "ext4", "sizeInBytes": 800 * apple.GIB,
                       "labels": {"project": "evonezha"}, "source": "/private/volume.img"}

    def test_existing_matching_volume_is_never_recreated(self):
        with patch.object(apple, "volume_info", return_value=self.volume), patch.object(apple, "run") as run:
            self.assertEqual(apple.ensure_volume(self.config), self.volume)
            run.assert_not_called()

    def test_wrong_volume_ownership_or_format_rejected(self):
        for change in ({"format": "apfs"}, {"labels": {}}, {"sizeInBytes": 50 * apple.GIB}):
            volume = dict(self.volume, **change)
            with self.subTest(change=change), patch.object(apple, "json_command", return_value=[{"configuration": volume}]):
                with self.assertRaises(ValueError):
                    apple.volume_info(self.config)

    def test_new_volume_requires_capacity_and_host_reserve(self):
        with patch.object(apple, "volume_info", return_value=None), patch.object(apple.shutil, "disk_usage") as disk, \
             patch.object(apple, "run") as run:
            disk.return_value.free = 899 * apple.GIB
            with self.assertRaises(ValueError):
                apple.ensure_volume(self.config)
            run.assert_not_called()

    def test_active_volume_detection_checks_backing_file_and_name(self):
        items = [
            {"id": "a", "status": {"state": "running"}, "configuration": {"mounts": [{"source": self.volume["source"]}]}},
            {"id": "b", "status": {"state": "starting"}, "configuration": {"mounts": [{"source": self.config["volume"]}]}},
            {"id": "c", "status": {"state": "stopped"}, "configuration": {"mounts": [{"source": self.config["volume"]}]}},
            {"id": "unrelated", "status": {"state": "running"}, "configuration": {"mounts": []}},
        ]
        with patch.object(apple, "json_command", return_value=items):
            self.assertEqual([item["id"] for item in apple.active_volume_users(self.config, self.volume)], ["a", "b"])

    def test_buildkit_memory_mount_does_not_block_unrelated_volume(self):
        items = [{"id": "buildkit", "status": {"state": "running"}, "configuration": {"mounts": [
            {"source": "", "destination": "/run", "type": {"tmpfs": {}}, "options": []},
            {"source": "/private/unrelated-builder", "type": {"virtiofs": {}}},
        ]}}]
        with patch.object(apple, "json_command", return_value=items):
            self.assertEqual(apple.active_volume_users(self.config, self.volume), [])

    def test_tmpfs_label_does_not_hide_nonempty_volume_identity(self):
        for source in (self.config["volume"], self.volume["source"]):
            items = [{"id": "writer", "status": {"state": "running"}, "configuration": {"mounts": [
                {"source": source, "type": {"tmpfs": {}}},
            ]}}]
            with self.subTest(source=source), patch.object(apple, "json_command", return_value=items):
                self.assertEqual([item["id"] for item in apple.active_volume_users(self.config, self.volume)], ["writer"])

    def test_only_exact_memory_mount_shape_accepts_empty_source(self):
        mounts = [
            {"source": ""},
            {"source": "", "type": {"virtiofs": {}}},
            {"source": "", "type": {"tmpfs": None}},
            {"source": "", "type": {"tmpfs": {}, "virtiofs": {}}},
            {"source": "", "type": "tmpfs"},
            {"source": None, "type": {"tmpfs": {}}},
            {"type": {"tmpfs": {}}},
        ]
        for mount in mounts:
            items = [{"id": "unknown", "status": {"state": "running"}, "configuration": {"mounts": [mount]}}]
            with self.subTest(mount=mount), patch.object(apple, "json_command", return_value=items):
                with self.assertRaisesRegex(ValueError, "Cannot interpret an active container mount"):
                    apple.active_volume_users(self.config, self.volume)

    def test_second_writer_refused_before_image_or_bundle_operations(self):
        with patch.object(apple, "volume_info", return_value=self.volume), \
             patch.object(apple, "active_volume_users", return_value=[{"id": "existing-sync"}]), \
             patch.object(apple, "prepare_bundle") as bundle, patch.object(apple, "run") as run:
            with self.assertRaisesRegex(ValueError, "already attached"):
                apple.execute_task(self.config, "init")
            bundle.assert_not_called()
            run.assert_not_called()

    def test_backing_file_symlink_alias_is_also_an_active_user(self):
        with tempfile.TemporaryDirectory() as directory:
            backing = Path(directory) / "disk.img"
            backing.write_text("fixture")
            alias = Path(directory) / "alias.img"
            alias.symlink_to(backing)
            items = [{"id": "alias-user", "status": {"state": "running"},
                      "configuration": {"mounts": [{"source": str(alias)}]}}]
            with patch.object(apple, "json_command", return_value=items):
                self.assertEqual(len(apple.active_volume_users(self.config, dict(self.volume, source=str(backing)))), 1)

    def test_unknown_backing_or_mount_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            apple.active_volume_users(self.config, dict(self.volume, source=None))
        items = [{"id": "unknown", "status": {"state": "running"},
                  "configuration": {"mounts": [{"source": None}]}}]
        with patch.object(apple, "json_command", return_value=items), self.assertRaises(ValueError):
            apple.active_volume_users(self.config, self.volume)

    def test_volume_is_rechecked_after_bundle_preparation(self):
        with patch.object(apple, "volume_info", return_value=self.volume), \
             patch.object(apple, "active_volume_users", side_effect=[[], [{"id": "new-writer"}]]), \
             patch.object(apple, "image_info", return_value="sha256:fixture"), \
             patch.object(apple, "prepare_bundle", return_value=(Path("/bundle"), "a" * 64)), \
             patch.object(apple, "write_state") as state, patch.object(apple, "run") as run:
            with self.assertRaisesRegex(ValueError, "became active"):
                apple.execute_task(self.config, "sync", detach=True)
            state.assert_not_called()
            run.assert_not_called()

    def test_operation_lock_prevents_concurrent_launch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(apple, "LOCAL", Path(directory)):
            with apple.operation_lock():
                with self.assertRaises(ValueError):
                    with apple.operation_lock():
                        self.fail("Second lock was accepted")


class ControlBundleTests(unittest.TestCase):
    def bundle(self, directory):
        root = Path(directory)
        for name in guest.CONTROL_FILES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture " + name)
        commit = "a" * 40
        (root / "config/sources.json").write_text(json.dumps({"references": [
            {"name": "repo-tool", "path": ".tools/git-repo", "commit": commit},
        ]}))
        repository = root / ".tools/git-repo"
        repository.mkdir(parents=True)
        (repository / "repo").write_text("fixture repo launcher")
        files = {name: guest.sha256(root / name) for name in guest.CONTROL_FILES}
        identity = guest.bundle_digest(files, commit)
        (root / "bundle.json").write_text(json.dumps({"schema_version": 1, "files": files, "repo_commit": commit}))
        return root, identity

    def locked_bundle(self, directory):
        root, _ = self.bundle(directory)
        config = apple.workspace.load_config()
        (root / "config/sources.json").write_text(json.dumps(config))
        tool = apple.workspace.reference_named(config, "repo-tool")
        manifest = apple.workspace.reference_named(config, config["platform"]["reference"])
        snapshot = root / guest.SOURCE_LOCK_FILES[1]
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text('<manifest><remote name="github" fetch="https://github.com/" />'
                            '<default remote="github" /><project name="Evolution-X/build" '
                            'path="build/make" revision="' + "b" * 40 + '" /></manifest>\n')
        descriptor = {"schema_version": 1,
                      "manifest": {key: manifest[key] for key in ("url", "commit")},
                      "repo": {key: tool[key] for key in ("url", "commit")},
                      "snapshot": {"path": guest.SOURCE_LOCK_FILES[1], "sha256": guest.sha256(snapshot),
                                   "bytes": snapshot.stat().st_size, "project_count": 1}}
        descriptor["manifest"]["reference"] = manifest["name"]
        (root / guest.SOURCE_LOCK_FILES[0]).write_text(json.dumps(descriptor))
        files = {name: guest.sha256(root / name) for name in guest.CONTROL_FILES + guest.SOURCE_LOCK_FILES}
        identity = guest.bundle_digest(files, tool["commit"])
        (root / "bundle.json").write_text(json.dumps({"schema_version": 1, "files": files,
                                                      "repo_commit": tool["commit"]}))
        return root, identity

    def reseal_bundle(self, root, files=None):
        record = json.loads((root / "bundle.json").read_text())
        record["files"] = {name: guest.sha256(root / name) for name in (files or record["files"])}
        (root / "bundle.json").write_text(json.dumps(record))
        return guest.bundle_digest(record["files"], record["repo_commit"])

    def test_control_allowlist_excludes_private_evidence_and_credentials(self):
        self.assertEqual(set(guest.CONTROL_FILES), {"config/sources.json", "config/apple-container.json",
                                                  "scripts/workspace.py", "scripts/container_task.py"})

    def test_content_changes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source, identity = self.bundle(directory)
            guest.verify_bundle(source, identity)
            (source / "scripts/workspace.py").write_text("changed")
            with self.assertRaises(ValueError):
                guest.verify_bundle(source, identity)

    def test_copy_is_persistent_and_does_not_modify_host_bundle(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, identity = self.bundle(directory)
            volume = Path(volume_dir)
            control = guest.prepare_control(source, volume, identity)
            self.assertEqual(control, volume / "control" / identity)
            self.assertEqual(guest.prepare_control(source, volume, identity), control)
            guest.verify_bundle(source, identity)

    def test_changed_existing_snapshot_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, identity = self.bundle(directory)
            volume = Path(volume_dir)
            control = guest.prepare_control(source, volume, identity)
            modified = control / "scripts/workspace.py"
            modified.write_text("local work")
            with self.assertRaises(ValueError):
                guest.prepare_control(source, volume, identity)
            self.assertEqual(modified.read_text(), "local work")

    def test_invalid_identity_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, identity = self.bundle(directory)
            volume = Path(volume_dir)
            with self.assertRaises(ValueError):
                guest.prepare_control(source, volume, "../escape")
            (volume / "control").symlink_to(source, target_is_directory=True)
            with self.assertRaises(ValueError):
                guest.prepare_control(source, volume, identity)

    def test_guest_explicitly_selects_rosetta_host_policy(self):
        command = guest.workspace_command(Path("/control-copy"), "init", Path("/work/evolution"))
        self.assertEqual(command[-2:], ["--host-mode", "apple-rosetta"])
        self.assertNotIn("--force-sync", command)

    def test_unrelated_bundle_files_are_not_copied_into_guest(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, identity = self.bundle(directory)
            (source / "private-note.txt").write_text("not a control input")
            control = guest.prepare_control(source, Path(volume_dir), identity)
            self.assertFalse((control / "private-note.txt").exists())
            self.assertTrue((control / ".tools/git-repo/repo").exists())

    def test_control_parent_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source, identity = self.bundle(directory)
            (source / "scripts").rename(source / "actual-scripts")
            (source / "scripts").symlink_to(source / "actual-scripts", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                guest.verify_bundle(source, identity)

    def test_recorded_repo_pin_must_match_hashed_source_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _ = self.bundle(directory)
            record = json.loads((source / "bundle.json").read_text())
            record["repo_commit"] = "b" * 40
            (source / "bundle.json").write_text(json.dumps(record))
            identity = guest.bundle_digest(record["files"], record["repo_commit"])
            with self.assertRaisesRegex(ValueError, "Repo pin"):
                guest.verify_bundle(source, identity)

    def test_extended_bundle_copies_exact_descriptor_and_xml_bytes(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, identity = self.locked_bundle(directory)
            record = guest.verify_bundle(source, identity)
            self.assertEqual(guest.bundled_source_lock(record), guest.SOURCE_LOCK_FILES[0])
            control = guest.prepare_control(source, Path(volume_dir), identity)
            for name in guest.SOURCE_LOCK_FILES:
                self.assertEqual((source / name).read_bytes(), (control / name).read_bytes())
            self.assertEqual(guest.prepare_control(source, Path(volume_dir), identity), control)

    def test_locked_bundle_verification_is_independent_of_the_imported_workspace_root(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as unrelated_dir:
            source, identity = self.locked_bundle(directory)
            unrelated = Path(unrelated_dir)
            (unrelated / "upstream").symlink_to(source, target_is_directory=True)
            with patch.object(guest.workspace, "ROOT", unrelated):
                self.assertEqual(guest.bundled_source_lock(guest.verify_bundle(source, identity)),
                                 guest.SOURCE_LOCK_FILES[0])

    def test_lock_files_participate_in_bundle_identity(self):
        for name in guest.SOURCE_LOCK_FILES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                source, identity = self.locked_bundle(directory)
                (source / name).write_text((source / name).read_text() + " ")
                with self.assertRaisesRegex(ValueError, "Control file changed"):
                    guest.verify_bundle(source, identity)
                self.assertNotEqual(self.reseal_bundle(source), identity)

    def test_partial_or_extra_lock_membership_is_rejected(self):
        for names in ((guest.SOURCE_LOCK_FILES[0],), (guest.SOURCE_LOCK_FILES[1],),
                      (*guest.SOURCE_LOCK_FILES, "private-note.txt")):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as directory:
                source, _ = self.locked_bundle(directory)
                (source / "private-note.txt").write_text("not a control input")
                identity = self.reseal_bundle(source, (*guest.CONTROL_FILES, *names))
                with self.assertRaisesRegex(ValueError, "Unexpected control bundle contents"):
                    guest.verify_bundle(source, identity)

    def test_unrecorded_lock_does_not_activate_or_enter_legacy_snapshot(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, _ = self.locked_bundle(directory)
            identity = self.reseal_bundle(source, guest.CONTROL_FILES)
            record = guest.verify_bundle(source, identity)
            self.assertIsNone(guest.bundled_source_lock(record))
            control = guest.prepare_control(source, Path(volume_dir), identity)
            for name in guest.SOURCE_LOCK_FILES:
                self.assertFalse((control / name).exists())

    def test_extended_bundle_requires_descriptor_to_bind_exact_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _ = self.locked_bundle(directory)
            path = source / guest.SOURCE_LOCK_FILES[0]
            descriptor = json.loads(path.read_text())
            descriptor["snapshot"]["sha256"] = "0" * 64
            path.write_text(json.dumps(descriptor))
            with self.assertRaisesRegex(ValueError, "reviewed size and SHA256"):
                guest.verify_bundle(source, self.reseal_bundle(source))

    def test_damaged_existing_locked_snapshot_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as volume_dir:
            source, identity = self.locked_bundle(directory)
            control = guest.prepare_control(source, Path(volume_dir), identity)
            changed = control / guest.SOURCE_LOCK_FILES[1]
            changed.write_text("local change")
            with self.assertRaises(ValueError):
                guest.prepare_control(source, Path(volume_dir), identity)
            self.assertEqual(changed.read_text(), "local change")

    def test_guest_lock_argument_uses_ext4_control_path(self):
        control = Path("/work/control/" + "a" * 64)
        for operation in ("init", "sync"):
            command = guest.workspace_command(control, operation, Path("/work/evolution"),
                                              source_lock=guest.SOURCE_LOCK_FILES[0])
            self.assertEqual(command[-2:], ["--source-lock", str(control / guest.SOURCE_LOCK_FILES[0])])
            self.assertNotIn("--force-sync", command)
        with self.assertRaises(ValueError):
            guest.workspace_command(control, "doctor", Path("/work/evolution"),
                                    source_lock=guest.SOURCE_LOCK_FILES[0])

    def test_host_lock_path_is_reviewed_and_root_relative(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _ = self.locked_bundle(directory)
            config = json.loads((source / "config/sources.json").read_text())
            with patch.object(apple, "ROOT", source), patch.object(apple.workspace, "load_config", return_value=config):
                self.assertEqual(apple.source_lock_path(source.resolve() / guest.SOURCE_LOCK_FILES[0]), guest.SOURCE_LOCK_FILES[0])
                self.assertEqual(apple.source_lock_path(guest.SOURCE_LOCK_FILES[0]), guest.SOURCE_LOCK_FILES[0])
                with self.assertRaisesRegex(ValueError, "inside the control workspace"):
                    apple.source_lock_path("/another-host/config/evolution-source-lock.json")

    def test_host_lock_and_snapshot_symlinks_are_not_followed(self):
        for name in guest.SOURCE_LOCK_FILES:
            for broken in (False, True):
                with self.subTest(name=name, broken=broken), tempfile.TemporaryDirectory() as directory:
                    source, _ = self.locked_bundle(directory)
                    config = json.loads((source / "config/sources.json").read_text())
                    original = source / name
                    moved = original.with_name("moved")
                    original.rename(moved)
                    original.symlink_to(moved.with_name("absent") if broken else moved)
                    with patch.object(apple, "ROOT", source), patch.object(apple.workspace, "load_config", return_value=config), \
                         patch.object(apple.workspace, "verify_reference"), patch.object(apple.workspace, "run") as run:
                        with self.assertRaisesRegex(ValueError, "Symlink"):
                            apple.prepare_bundle(guest.SOURCE_LOCK_FILES[0])
                    run.assert_not_called()

    def test_host_base_control_symlink_is_not_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _ = self.bundle(directory)
            config = json.loads((source / "config/sources.json").read_text())
            (source / "scripts").rename(source / "actual-scripts")
            (source / "scripts").symlink_to(source / "actual-scripts", target_is_directory=True)
            with patch.object(apple, "ROOT", source), patch.object(apple.workspace, "load_config", return_value=config), \
                 patch.object(apple.workspace, "verify_reference"), patch.object(apple.workspace, "run") as run:
                with self.assertRaisesRegex(ValueError, "Symlink"):
                    apple.prepare_bundle()
            run.assert_not_called()

    def test_host_prepares_and_reuses_a_bundle_with_both_lock_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _ = self.locked_bundle(directory)
            config = json.loads((source / "config/sources.json").read_text())
            def mocked_git(command):
                if "clone" in command:
                    repository = Path(command[-1])
                    repository.mkdir()
                    (repository / "repo").write_text("fixture repo")
            with patch.object(apple, "ROOT", source), patch.object(apple, "LOCAL", source / ".tools/apple-container"), \
                 patch.object(apple.workspace, "load_config", return_value=config), \
                 patch.object(apple.workspace, "verify_reference"), \
                 patch.object(apple.workspace, "run", side_effect=mocked_git) as run:
                bundle, identity = apple.prepare_bundle(guest.SOURCE_LOCK_FILES[0])
                clone_calls = run.call_count
                self.assertEqual(apple.prepare_bundle(guest.SOURCE_LOCK_FILES[0]), (bundle, identity))
                self.assertEqual(run.call_count, clone_calls)
            self.assertEqual(set(guest.verify_bundle(bundle, identity)["files"]),
                             set(guest.CONTROL_FILES + guest.SOURCE_LOCK_FILES))
            for name in guest.SOURCE_LOCK_FILES:
                self.assertEqual((bundle / name).read_bytes(), (source / name).read_bytes())


class TaskLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.config = apple.load_config()
        self.record = {"container": "task-id", "operation": "sync", "control_id": "a" * 64,
                       "volume": self.config["volume"], "detached": True, "launch_exit_code": 0}
        self.volume = {"format": "ext4", "sizeInBytes": 800 * apple.GIB, "source": "/private/volume.img"}

    def status_output(self, items, logs="", record=None):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text(json.dumps(record or self.record))
            output = io.StringIO()
            result = subprocess.CompletedProcess([], 0, logs, "")
            with patch.object(apple, "STATE", state), patch.object(apple, "volume_info", return_value=self.volume), \
                 patch.object(apple, "json_command", return_value=items), patch.object(apple, "run", return_value=result) as run, \
                 contextlib.redirect_stdout(output):
                apple.status(self.config)
            return output.getvalue(), run

    def test_missing_detached_container_has_unknown_completion(self):
        output, _ = self.status_output([])
        self.assertIn('"state": "missing"', output)
        self.assertIn('"task_status": "unknown"', output)
        self.assertNotIn("removed after foreground", output)

    def test_removed_foreground_success_retains_known_exit(self):
        output, _ = self.status_output([], record=dict(self.record, detached=False, exit_code=0))
        self.assertIn('"state": "removed"', output)
        self.assertIn('"task_status": "complete"', output)

    def test_live_external_volume_user_is_reported_despite_removed_last_task(self):
        items = [{"id": "twrp-active", "status": {"state": "running"}, "configuration": {
            "mounts": [{"source": self.volume["source"]}]}}]
        output, run = self.status_output(items, record=dict(self.record, detached=False, exit_code=0))
        self.assertIn('"active_volume_users": [', output)
        self.assertIn('"container": "twrp-active"', output)
        self.assertIn('"record_kind": "last_recorded_task"', output)
        self.assertIn('"active_volume_user": false', output)
        self.assertIn('"state": "removed"', output)
        self.assertIn("receipt was preserved unchanged", output)
        self.assertFalse(any("exec" in call.args[0] or "run" in call.args[0] for call in run.call_args_list))

    def test_live_volume_users_are_visible_without_a_last_task_receipt(self):
        items = [{"id": "external-vm", "status": {"state": "running"}, "configuration": {
            "mounts": [{"source": self.config["volume"]}]}}]
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, patch.object(apple, "STATE", Path(directory) / "absent"), \
             patch.object(apple, "volume_info", return_value=self.volume), patch.object(apple, "json_command", return_value=items), \
             patch.object(apple, "run"), patch.object(apple, "write_state") as state, contextlib.redirect_stdout(output):
            apple.status(self.config)
        state.assert_not_called()
        self.assertIn('"container": "external-vm"', output.getvalue())
        self.assertIn("not adopted", output.getvalue())

    def test_status_does_not_replace_the_historical_receipt(self):
        items = [{"id": "external-vm", "status": {"state": "running"}, "configuration": {
            "mounts": [{"source": self.volume["source"]}]}}]
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            original = json.dumps(self.record).encode()
            state.write_bytes(original)
            with patch.object(apple, "STATE", state), patch.object(apple, "volume_info", return_value=self.volume), \
                 patch.object(apple, "json_command", return_value=items), patch.object(apple, "run"), \
                 contextlib.redirect_stdout(io.StringIO()):
                apple.status(self.config)
            self.assertEqual(state.read_bytes(), original)

    def test_running_record_without_volume_attachment_is_not_inventoried(self):
        output, run = self.status_output([{"id": "task-id", "status": {"state": "running"},
                                         "configuration": {"mounts": []}}])
        self.assertIn('"active_volume_user": false', output)
        self.assertFalse(any("exec" in call.args[0] for call in run.call_args_list))

    def test_stopped_detached_task_needs_explicit_guest_result(self):
        items = [{"id": "task-id", "status": {"state": "stopped"}}]
        output, _ = self.status_output(items)
        self.assertIn('"task_status": "unknown"', output)
        marker = "EVOLUTION_TASK_RESULT=" + json.dumps({"operation": "sync", "exit_code": 2,
                  "status": "failed", "control_id": self.record["control_id"]})
        output, _ = self.status_output(items, logs=marker)
        self.assertIn('"task_status": "failed"', output)
        self.assertIn('"guest_result": {', output)

    def test_invalid_or_mismatched_result_markers_are_ignored(self):
        for result in ({"operation": "init", "exit_code": 0, "status": "complete"},
                       {"operation": "sync", "exit_code": True, "status": "complete"},
                       {"operation": "sync", "exit_code": 1, "status": "complete"},
                       {"operation": "sync", "exit_code": 0, "status": "complete", "control_id": "b" * 64}):
            with self.subTest(result=result):
                self.assertIsNone(apple.task_result("EVOLUTION_TASK_RESULT=" + json.dumps(result), self.record))
        self.assertIsNone(apple.task_result("EVOLUTION_TASK_RESULT=not-json", self.record))

    def test_legacy_live_guest_markers_remain_readable(self):
        marker = "EVOLUTION_TASK_RESULT=" + json.dumps({"operation": "sync", "exit_code": 0, "status": "complete"})
        self.assertEqual(apple.task_result(marker, self.record)["exit_code"], 0)

    def test_atomic_state_write_replaces_complete_record(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(apple, "STATE", Path(directory) / "last.json"):
            apple.write_state(self.record)
            self.assertEqual(json.loads(apple.STATE.read_text()), self.record)
            self.assertEqual(list(Path(directory).iterdir()), [apple.STATE])

    def test_launch_exception_is_recorded_without_claiming_completion(self):
        with patch.object(apple, "volume_info", return_value=self.volume), \
             patch.object(apple, "active_volume_users", return_value=[]), \
             patch.object(apple, "image_info", return_value="sha256:fixture"), \
             patch.object(apple, "prepare_bundle", return_value=(Path("/bundle"), "a" * 64)), \
             patch.object(apple, "write_state") as state, \
             patch.object(apple, "run", side_effect=FileNotFoundError("container unavailable")):
            with self.assertRaises(FileNotFoundError):
                apple.execute_task(self.config, "sync", detach=True)
        record = state.call_args.args[0]
        self.assertEqual(record["lifecycle"], "launch_failed")
        self.assertNotIn("exit_code", record)

    def test_launch_forwards_and_records_reviewed_lock(self):
        with patch.object(apple, "volume_info", return_value=self.volume), \
             patch.object(apple, "active_volume_users", return_value=[]), \
             patch.object(apple, "image_info", return_value="sha256:fixture"), \
             patch.object(apple, "source_lock_path", return_value=guest.SOURCE_LOCK_FILES[0]), \
             patch.object(apple, "prepare_bundle", return_value=(Path("/bundle"), "a" * 64)) as bundle, \
             patch.object(apple, "write_state") as state, \
             patch.object(apple, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            apple.execute_task(self.config, "init", source_lock=guest.SOURCE_LOCK_FILES[0])
        bundle.assert_called_once_with(guest.SOURCE_LOCK_FILES[0])
        self.assertEqual(run.call_args.args[0][-2:], ["--source-lock", guest.SOURCE_LOCK_FILES[0]])
        self.assertEqual(state.call_args.args[0]["source_lock"], guest.SOURCE_LOCK_FILES[0])

    def test_guest_preflight_failure_emits_completion_marker(self):
        output = io.StringIO()
        with patch.object(guest, "prepare_control", side_effect=ValueError("broken bundle")), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(guest.main(["--control-id", "a" * 64, "sync"]), 2)
        self.assertEqual(apple.task_result(output.getvalue(), self.record)["exit_code"], 2)

    def test_guest_rejects_missing_or_unrecorded_lock_before_running_workspace(self):
        for selected, files in ((None, guest.CONTROL_FILES + guest.SOURCE_LOCK_FILES),
                                (guest.SOURCE_LOCK_FILES[0], guest.CONTROL_FILES)):
            arguments = ["--control-id", "a" * 64, "sync"]
            if selected:
                arguments += ["--source-lock", selected]
            with self.subTest(selected=selected), \
                 patch.object(guest, "prepare_control", return_value=Path("/work/control/fixture")), \
                 patch.object(guest, "verify_bundle", return_value={"files": dict.fromkeys(files, "a" * 64)}), \
                 patch.object(guest, "run_workspace") as run, patch.object(Path, "mkdir") as mkdir, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(guest.main(arguments), 2)
            run.assert_not_called()
            mkdir.assert_not_called()

    def test_guest_runs_workspace_with_verified_ext4_lock_path(self):
        control = Path("/work/control/" + "a" * 64)
        record = {"files": dict.fromkeys(guest.CONTROL_FILES + guest.SOURCE_LOCK_FILES, "a" * 64)}
        for operation in ("init", "sync"):
            with self.subTest(operation=operation), patch.object(guest, "prepare_control", return_value=control), \
                 patch.object(guest, "verify_bundle", return_value=record), \
                 patch.object(Path, "read_text", return_value=json.dumps(self.config)), \
                 patch.object(Path, "mkdir"), patch.dict(guest.os.environ), \
                 patch.object(guest, "run_workspace", return_value=0) as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(guest.main(["--control-id", "a" * 64, operation,
                                            "--source-lock", guest.SOURCE_LOCK_FILES[0]]), 0)
            self.assertEqual(run.call_args.args[0][-2:], ["--source-lock", str(control / guest.SOURCE_LOCK_FILES[0])])

    def test_inventory_does_not_copy_control_or_create_directories(self):
        with patch.object(guest, "verify_bundle"), patch.object(guest, "prepare_control") as prepare, \
             patch.object(Path, "read_text", return_value=json.dumps(self.config)), \
             patch.object(Path, "mkdir") as mkdir, patch.object(guest, "inventory") as inventory:
            self.assertEqual(guest.main(["--control-id", "a" * 64, "inventory"]), 0)
        prepare.assert_not_called()
        mkdir.assert_not_called()
        inventory.assert_called_once_with(Path(self.config["source_dir"]))

    def test_network_phase_inventory_does_not_claim_zero_planned_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            (source / ".repo/project-objects/platform/example.git/objects").mkdir(parents=True)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                guest.inventory(source)
            record = json.loads(output.getvalue())
        self.assertTrue(record["project_list_pending"])
        self.assertIsNone(record["listed_projects"])
        self.assertEqual(record["prepared_object_git_dirs"], 1)

    def test_guest_forwards_termination_to_repo_process_group(self):
        process = Mock(pid=12345)
        handlers = {}
        def set_handler(number, handler):
            handlers[number] = handler
        def wait():
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            return -signal.SIGTERM
        process.wait.side_effect = wait
        with patch.object(guest.subprocess, "Popen", return_value=process) as popen, \
             patch.object(guest.signal, "getsignal", return_value=signal.SIG_DFL), \
             patch.object(guest.signal, "signal", side_effect=set_handler), \
             patch.object(guest.os, "killpg") as kill:
            self.assertEqual(guest.run_workspace(["python3", "workspace.py", "sync"]), 143)
        kill.assert_called_once_with(12345, signal.SIGTERM)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertEqual(handlers[signal.SIGTERM], signal.SIG_DFL)


if __name__ == "__main__":
    unittest.main()
