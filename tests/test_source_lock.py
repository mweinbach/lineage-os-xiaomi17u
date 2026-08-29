"""Offline source-lock selection, preservation, and checkout-audit tests."""

import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts import workspace


class SourceLockTests(unittest.TestCase):
    def setUp(self):
        self.config = workspace.load_config()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.parent = Path(self.directory.name).resolve()
        self.root = self.parent / "control"
        self.root.mkdir()
        self.source = self.parent / "source"
        self.descriptor = self.root / "config/source-lock.json"
        self.snapshot = self.root / "research/source-snapshots/locked.xml"
        self.descriptor.parent.mkdir(parents=True)
        self.snapshot.parent.mkdir(parents=True)
        manifest = workspace.reference_named(self.config, self.config["platform"]["reference"])
        repo = workspace.reference_named(self.config, "repo-tool")
        self.record = {
            "schema_version": 1,
            "manifest": {"reference": manifest["name"], "url": manifest["url"], "commit": manifest["commit"]},
            "repo": {"url": repo["url"], "commit": repo["commit"]},
            "snapshot": {"path": "research/source-snapshots/locked.xml", "project_count": 2},
        }
        self.document = ET.fromstring(
            '<manifest><remote name="github" fetch=".." revision="refs/heads/moving"/>'
            '<remote name="aosp" fetch="https://android.googlesource.com"/>'
            '<remote name="private" fetch="ssh://git@github.com"/>'
            '<default remote="github" revision="refs/heads/moving"/>'
            '<project name="LineageOS/test" path="frameworks/test" revision="' + "a" * 40 + '">'
            '<linkfile src="build.bp" dest="Android.bp"/></project>'
            '<project name="platform/test" path="system/test" remote="aosp" revision="' + "b" * 40 + '"/>'
            '<contactinfo bugurl="https://example.test/bugs"/></manifest>'
        )
        self.save()

    def save(self):
        data = ET.tostring(self.document, encoding="utf-8")
        self.snapshot.write_bytes(data)
        self.record["snapshot"].update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        self.descriptor.write_text(json.dumps(self.record))

    def load(self):
        return workspace.load_source_lock(self.config, self.descriptor, root=self.root)

    def prepare_source(self, locked=False, projects=True):
        for name in ("repo", "manifests", "manifests.git"):
            (self.source / ".repo" / name).mkdir(parents=True, exist_ok=True)
        selector = self.source / ".repo/manifest.xml"
        selector.write_bytes(self.snapshot.read_bytes() if locked else b'<manifest><include name="default.xml"/></manifest>')
        if projects:
            lock = self.load()
            for relative in lock["projects"]:
                target = self.source / relative
                target.mkdir(parents=True)
                (target / ".git").write_text("gitdir: fixture-only\n")
            (self.source / ".repo/project.list").write_text("\n".join(lock["projects"]) + "\n")
        return selector

    def git(self, target, *args):
        target = Path(target)
        if target.parent == self.source / ".repo":
            ref = workspace.reference_named(self.config, "repo-tool" if target.name == "repo" else "evolution-manifest")
            values = {
                ("rev-parse", "--show-toplevel"): str(target),
                ("rev-parse", "--absolute-git-dir"): str(self.source / ".repo" / (target.name + ".git")),
                ("rev-parse", "HEAD"): ref["commit"],
                ("remote", "get-url", "origin"): ref["url"],
                ("status", "--porcelain", "--untracked-files=all"): "",
            }
        else:
            relative = target.relative_to(self.source).as_posix()
            project = self.load()["projects"][relative]
            values = {
                ("rev-parse", "--show-toplevel"): str(target),
                ("rev-parse", "--absolute-git-dir"): str(self.source / ".repo/projects" / (relative + ".git")),
                ("rev-parse", "HEAD"): project["revision"],
                ("remote", "get-url", project["remote"]): project["url"],
                ("status", "--porcelain", "--untracked-files=all"): "",
            }
        return values[args]

    def test_committed_lock_matches_pins_and_all_1179_projects(self):
        lock = workspace.load_source_lock(self.config, "config/evolution-source-lock.json")
        self.assertEqual(len(lock["projects"]), 1179)
        self.assertEqual(hashlib.sha256(lock["data"]).hexdigest(), lock["record"]["snapshot"]["sha256"])
        summary = workspace.source_lock_summary(lock)
        self.assertEqual(summary["bytes"], 287546)
        self.assertEqual(summary["project_count"], 1179)
        self.assertIn("not prove", lock["record"]["scope"])

    def test_root_argument_and_relative_remote_preserve_original_origin(self):
        lock = self.load()
        self.assertEqual(lock["descriptor"], "config/source-lock.json")
        self.assertEqual(lock["projects"]["frameworks/test"]["url"], "https://github.com/LineageOS/test")
        self.assertEqual(lock["projects"]["system/test"]["url"], "https://android.googlesource.com/platform/test")
        relative = workspace.load_source_lock(self.config, "config/source-lock.json", root=self.root)
        self.assertEqual(relative["data"], lock["data"])

    def test_descriptor_origins_and_commits_are_bound_to_config(self):
        original = copy.deepcopy(self.record)
        for section, field, value in (("manifest", "reference", "other"), ("manifest", "url", "https://wrong.test/m"),
                                      ("manifest", "commit", "c" * 40), ("repo", "url", "https://wrong.test/r"),
                                      ("repo", "commit", "c" * 40)):
            with self.subTest(section=section, field=field):
                self.record = copy.deepcopy(original)
                self.record[section][field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "configured"):
                    self.load()

    def test_snapshot_hash_size_and_count_are_all_required(self):
        original = copy.deepcopy(self.record)
        for field, value in (("sha256", "0" * 64), ("bytes", 1), ("project_count", 3),
                             ("project_count", True), ("sha256", 3)):
            with self.subTest(field=field):
                self.record = copy.deepcopy(original)
                self.record["snapshot"][field] = value
                self.descriptor.write_text(json.dumps(self.record))
                with self.assertRaises(ValueError):
                    self.load()

    def test_descriptor_and_snapshot_symlinks_are_rejected(self):
        for target in (self.descriptor, self.snapshot):
            with self.subTest(target=target):
                data = target.read_bytes()
                backing = target.with_suffix(".backing")
                target.rename(backing)
                target.symlink_to(backing)
                with self.assertRaisesRegex(ValueError, "Symlink"):
                    self.load()
                target.unlink()
                target.write_bytes(data)

    def test_descriptor_must_stay_inside_control_and_snapshot_directory(self):
        with self.assertRaisesRegex(ValueError, "control workspace"):
            workspace.load_source_lock(self.config, self.parent / "outside.json", root=self.root)
        for path in ("../outside.xml", "/outside.xml", "config/other.xml"):
            with self.subTest(path=path):
                self.record["snapshot"]["path"] = path
                self.descriptor.write_text(json.dumps(self.record))
                with self.assertRaises(ValueError):
                    self.load()

    def test_lock_rejects_overrides_hooks_and_nested_projects(self):
        for tag in ("include", "remove-project", "extend-project", "submanifest", "repo-hooks", "superproject"):
            with self.subTest(tag=tag):
                node = ET.SubElement(self.document, tag)
                self.save()
                with self.assertRaisesRegex(ValueError, "flattened"):
                    self.load()
                self.document.remove(node)
        ET.SubElement(self.document.find("project"), "project", name="nested", revision="a" * 40)
        self.save()
        with self.assertRaisesRegex(ValueError, "project child"):
            self.load()

    def test_lock_requires_explicit_shas_unique_paths_and_known_public_remotes(self):
        project = self.document.findall("project")[1]
        original = dict(project.attrib)
        for field, value in (("revision", "refs/heads/moving"), ("path", "frameworks/test"),
                             ("remote", "unknown"), ("remote", "private"), ("groups", "pdk,notdefault")):
            with self.subTest(field=field, value=value):
                project.attrib = dict(original, **{field: value})
                self.save()
                with self.assertRaises(ValueError):
                    self.load()
        project.attrib = dict(original)
        del project.attrib["revision"]
        self.save()
        with self.assertRaisesRegex(ValueError, "explicit full commit"):
            self.load()

    def test_unsafe_project_and_copy_link_paths_are_rejected(self):
        project = self.document.find("project")
        original = dict(project.attrib)
        for value in ("../escape", "/outside", ".", "foo/../bar", "foo//bar", ".repo/manifest.xml", "foo/.git", "foo bar"):
            for attribute in ("path", "name"):
                with self.subTest(value=value, attribute=attribute):
                    project.attrib = dict(original, **{attribute: value})
                    self.save()
                    with self.assertRaisesRegex(ValueError, "Unsafe"):
                        self.load()
        project.attrib = original
        project.find("linkfile").set("dest", "../escape")
        self.save()
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.load()

    def test_duplicate_remote_and_credentialed_https_url_are_rejected(self):
        node = ET.SubElement(self.document, "remote", name="github", fetch="https://example.test")
        self.save()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load()
        self.document.remove(node)
        self.document.find("remote").set("fetch", "https://user:password@example.test")
        self.save()
        with self.assertRaisesRegex(ValueError, "without credentials"):
            self.load()

    def test_selector_requires_explicit_lock_and_exact_bytes(self):
        selector = self.prepare_source(locked=True)
        lock = self.load()
        self.assertEqual(workspace.verify_manifest_selection(self.source, lock), "source-lock")
        with self.assertRaises(ValueError):
            workspace.verify_manifest_selection(self.source)
        selector.write_bytes(lock["data"] + b"\n")
        with self.assertRaisesRegex(ValueError, "does not equal"):
            workspace.verify_manifest_selection(self.source, lock)

    def test_default_selector_allowed_only_for_read_only_audit(self):
        self.prepare_source()
        lock = self.load()
        with self.assertRaisesRegex(ValueError, "check-source"):
            workspace.verify_manifest_selection(self.source, lock)
        self.assertEqual(workspace.verify_manifest_selection(self.source, lock, allow_default=True), "default.xml")

    def test_locked_selector_does_not_allow_local_manifest_or_symlink(self):
        selector = self.prepare_source(locked=True)
        local = self.source / ".repo/local_manifests"
        local.mkdir()
        (local / "extra.xml").write_text("<manifest/>")
        with self.assertRaisesRegex(ValueError, "Local manifests"):
            workspace.verify_manifest_selection(self.source, self.load())
        (local / "extra.xml").unlink()
        selector.unlink()
        selector.symlink_to(self.snapshot)
        with self.assertRaises(ValueError):
            workspace.verify_manifest_selection(self.source, self.load())

    def test_dry_runs_validate_lock_but_do_not_probe_run_or_create_source(self):
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "run") as run, \
             patch.object(workspace, "require_host") as host, contextlib.redirect_stdout(io.StringIO()) as output:
            workspace.initialize(self.config, self.source, dry_run=True, source_lock=self.descriptor)
            workspace.synchronize(self.config, self.source, 4, dry_run=True, source_lock=self.descriptor)
        self.assertFalse(self.source.exists())
        host.assert_not_called()
        run.assert_not_called()
        self.assertIn(self.record["snapshot"]["sha256"], output.getvalue())

    def test_host_failure_prevents_init_or_selector_write(self):
        with patch.object(workspace, "ROOT", self.root), \
             patch.object(workspace, "require_host", side_effect=ValueError("unsupported host")), \
             patch.object(workspace, "run") as run:
            with self.assertRaisesRegex(ValueError, "unsupported host"):
                workspace.initialize(self.config, self.source, source_lock=self.descriptor)
        run.assert_not_called()
        self.assertFalse(self.source.exists())

    def test_fresh_init_uses_original_pinned_origin_then_installs_exact_lock(self):
        def init(args, **kwargs):
            self.assertIn("init", args)
            self.assertIn(self.record["manifest"]["url"], args)
            self.assertIn(self.record["manifest"]["commit"], args)
            self.assertNotIn("--standalone-manifest", args)
            self.assertNotIn("--no-repo-verify", args)
            self.prepare_source(projects=False)

        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command"), patch.object(workspace, "git_value", side_effect=self.git), \
             patch.object(workspace, "run", side_effect=init) as run, contextlib.redirect_stdout(io.StringIO()):
            workspace.initialize(self.config, self.source, source_lock=self.descriptor)
        self.assertEqual(run.call_count, 1)
        self.assertEqual((self.source / ".repo/manifest.xml").read_bytes(), self.snapshot.read_bytes())
        self.assertEqual(list((self.source / ".repo/manifests").iterdir()), [])
        self.assertFalse(list((self.source / ".repo").glob(".source-lock-*")))

    def test_existing_default_is_never_converted_or_reinitialized(self):
        selector = self.prepare_source()
        before = selector.read_bytes()
        patch_file = self.source / "frameworks/test/local-patch.txt"
        patch_file.write_text("preserve local work")
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command"), patch.object(workspace, "git_value", side_effect=self.git), \
             patch.object(workspace, "run") as run:
            with self.assertRaisesRegex(ValueError, "check-source"):
                workspace.initialize(self.config, self.source, source_lock=self.descriptor)
        self.assertEqual(selector.read_bytes(), before)
        self.assertEqual(patch_file.read_text(), "preserve local work")
        run.assert_not_called()

    def test_existing_locked_tree_is_only_verified(self):
        selector = self.prepare_source(locked=True)
        before = selector.read_bytes()
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command"), patch.object(workspace, "git_value", side_effect=self.git), \
             patch.object(workspace, "run") as run, contextlib.redirect_stdout(io.StringIO()):
            workspace.initialize(self.config, self.source, source_lock=self.descriptor)
        self.assertEqual(selector.read_bytes(), before)
        run.assert_not_called()

    def test_locked_sync_refuses_default_selector_before_network(self):
        self.prepare_source()
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command"), patch.object(workspace, "git_value", side_effect=self.git), \
             patch.object(workspace.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "check-source"):
                workspace.synchronize(self.config, self.source, 4, source_lock=self.descriptor)
        run.assert_not_called()

    def test_locked_sync_retains_guards_and_audits_result(self):
        self.prepare_source(locked=True)
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "require_host"), \
             patch.object(workspace, "repo_command", return_value=["python3", "repo"]), \
             patch.object(workspace, "git_value", side_effect=self.git), \
             patch.object(workspace, "run") as run, patch.object(workspace.subprocess, "run") as process, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            workspace.synchronize(self.config, self.source, 4, source_lock=self.descriptor)
        args = process.call_args.args[0]
        self.assertIn("--no-manifest-update", args)
        self.assertFalse(any(arg.startswith("--force") for arg in args))
        self.assertEqual(process.call_args.kwargs["env"]["REPO_SKIP_SELF_UPDATE"], "1")
        self.assertNotIn("GIT_LFS_SKIP_SMUDGE", process.call_args.kwargs["env"])
        self.assertIn("manifest", run.call_args.args[0])
        self.assertIn('"clean_base_checkout": true', output.getvalue())

    def test_read_only_audit_checks_original_selector_without_requiring_host(self):
        selector = self.prepare_source()
        before = selector.read_bytes()
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "git_value", side_effect=self.git), \
             patch.object(workspace, "run") as run, patch.object(workspace, "require_host") as host:
            report = workspace.check_source(self.config, self.source, self.descriptor)
        self.assertEqual(report["active_selector"], "default.xml")
        self.assertTrue(report["base_revisions_match"])
        self.assertTrue(report["clean_base_checkout"])
        self.assertTrue(report["read_only"])
        self.assertEqual(report["clean_project_count"], 2)
        self.assertEqual(selector.read_bytes(), before)
        self.assertIn("private firmware and signing inputs", report["excluded_inputs"])
        host.assert_not_called()
        run.assert_not_called()

    def test_read_only_audit_reports_local_changes_and_preserves_patch(self):
        self.prepare_source()
        patch_file = self.source / "frameworks/test/change.patch"
        patch_file.write_text("local patch bytes\n")

        def git(target, *args):
            if Path(target).name == "test" and args == ("status", "--porcelain", "--untracked-files=all"):
                return "?? change.patch"
            return self.git(target, *args)

        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "git_value", side_effect=git):
            report = workspace.check_source(self.config, self.source, self.descriptor)
        self.assertTrue(report["base_revisions_match"])
        self.assertFalse(report["clean_base_checkout"])
        self.assertEqual({issue["kind"] for issue in report["issues"]}, {"local-changes"})
        self.assertEqual(patch_file.read_bytes(), b"local patch bytes\n")

    def test_read_only_audit_reports_revision_remote_and_project_list_drift(self):
        self.prepare_source()
        (self.source / ".repo/project.list").write_text("frameworks/test\nextra/project\n")

        def git(target, *args):
            if Path(target).name == "test" and args == ("rev-parse", "HEAD"):
                return "c" * 40
            if args == ("remote", "get-url", "github"):
                return "https://wrong.test/repo"
            return self.git(target, *args)

        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "git_value", side_effect=git):
            report = workspace.check_source(self.config, self.source, self.descriptor)
        self.assertFalse(report["base_revisions_match"])
        self.assertFalse(report["clean_base_checkout"])
        self.assertEqual({issue["kind"] for issue in report["issues"]},
                         {"project-list-mismatch", "revision-mismatch", "origin-mismatch"})

    def test_project_missing_or_external_metadata_is_reported_not_repaired(self):
        self.prepare_source()
        missing = self.source / "system/test/.git"
        missing.unlink()

        def git(target, *args):
            if Path(target).name == "test" and args == ("rev-parse", "--absolute-git-dir"):
                return str(self.parent / "external-git")
            return self.git(target, *args)

        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "git_value", side_effect=git):
            report = workspace.check_source(self.config, self.source, self.descriptor)
        self.assertFalse(report["clean_base_checkout"])
        self.assertEqual(len(report["issues"]), 2)
        self.assertFalse(missing.exists())

    def test_project_list_and_project_path_symlinks_are_refused(self):
        self.prepare_source()
        listing = self.source / ".repo/project.list"
        other = self.parent / "other-list"
        other.write_bytes(listing.read_bytes())
        listing.unlink()
        listing.symlink_to(other)
        project = self.source / "frameworks/test"
        (project / ".git").unlink()
        project.rmdir()
        project.symlink_to(self.source / "system/test")
        with patch.object(workspace, "ROOT", self.root), patch.object(workspace, "git_value", side_effect=self.git):
            report = workspace.check_source(self.config, self.source, self.descriptor)
        self.assertFalse(report["project_list_matches"])
        self.assertFalse(report["clean_base_checkout"])
        self.assertTrue(any(issue["path"] == "frameworks/test" and issue["kind"] == "unreadable-or-unsafe"
                            for issue in report["issues"]))

    def test_check_source_cli_exit_status_keeps_audit_json_on_dirty_result(self):
        for clean in (True, False):
            report = {"clean_base_checkout": clean, "read_only": True, "issues": [] if clean else [{"kind": "local-changes"}]}
            with self.subTest(clean=clean), patch.object(workspace, "check_source", return_value=report) as check, \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                status = workspace.main(["check-source", "--source-dir", str(self.source),
                                         "--source-lock", "config/source-lock.json"])
            self.assertEqual(status, 0 if clean else 2)
            self.assertEqual(json.loads(output.getvalue()), report)
            self.assertEqual(check.call_args.args[-1], Path("config/source-lock.json"))

    def test_cli_forwards_lock_without_changing_host_mode(self):
        for command, method in (("init", "initialize"), ("sync", "synchronize")):
            with self.subTest(command=command), patch.object(workspace, method) as operation:
                self.assertEqual(workspace.main([command, "--source-dir", str(self.source), "--dry-run",
                                                 "--host-mode", "apple-rosetta", "--source-lock", "config/source-lock.json"]), 0)
            self.assertEqual(operation.call_args.args[-1], "apple-rosetta")
            self.assertEqual(operation.call_args.kwargs["source_lock"], Path("config/source-lock.json"))

    def test_read_only_git_disables_optional_locks_monitors_and_lazy_fetch(self):
        with patch.object(workspace.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            workspace.git_value(self.source, "status", "--porcelain", "--untracked-files=all")
        args = run.call_args.args[0]
        self.assertIn("--no-optional-locks", args)
        self.assertIn("core.fsmonitor=false", args)
        self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
        self.assertFalse(run.call_args.kwargs["shell"])


if __name__ == "__main__":
    unittest.main()
