"""Offline supplementary-source tests; no real Git, network, VM or phone calls."""

import contextlib
import copy
import errno
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import twrp_dependencies as dependencies
from scripts import twrp_workspace


BASE_SHA = "a" * 40
BASE_MANIFEST = ('<manifest><remote name="aosp" fetch="https://android.googlesource.com"/>'
                 '<default remote="aosp"/><project path="build/make" name="platform/build" revision="'
                 + BASE_SHA + '"/></manifest>')


class Fixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.control = self.root / "control"
        (self.control / "config").mkdir(parents=True)
        self.source = self.root / "source"
        self.source.mkdir()
        self.paths = {"source_dir": self.source, "out_dir": self.root / "out", "report_dir": self.root / "reports"}
        self.paths["report_dir"].mkdir()
        (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).write_text(BASE_MANIFEST)
        self.base = twrp_workspace.load_config()
        self.base.update({key: str(value) for key, value in self.paths.items()})
        self.base["expected_project_count"] = 1
        self.base["project_selection"]["expanded_project_count"] = 2
        (self.control / "config/twrp.json").write_text(json.dumps(self.base))
        self.config = dependencies.load_config()
        self.config["projects"] = [next(project for project in self.config["projects"] if project["path"] == "system/bpf")]
        self.config["base"].update(source_dir=str(self.source), project_count=1,
                                   frozen_manifest_sha256=hashlib.sha256(BASE_MANIFEST.encode()).hexdigest())
        self.save_config()
        self.project = self.config["projects"][0]
        self.target = self.source / self.project["path"]
        self.frozen = twrp_workspace.parse_manifest(BASE_MANIFEST, resolved=True)

    def save_config(self):
        (self.control / dependencies.CONFIG).write_text(json.dumps(self.config))

    @contextlib.contextmanager
    def base_mocks(self):
        with patch.object(twrp_workspace, "verify_control"), \
             patch.object(twrp_workspace, "load_snapshot", return_value=self.frozen), \
             patch.object(twrp_workspace, "manifest_text", return_value=BASE_MANIFEST):
            yield

    def make_project(self):
        (self.target / ".git").mkdir(parents=True)

    def git(self, target, *args):
        return {("rev-parse", "--show-toplevel"): str(target),
                ("rev-parse", "--absolute-git-dir"): str(target / ".git"),
                ("rev-parse", "HEAD"): self.project["commit"],
                ("remote", "get-url", "origin"): self.project["url"],
                ("ls-files", "-v", "-z"): "H Android.bp\0H include/bpf.h\0",
                ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"): "",
                ("rev-parse", "--verify", "FETCH_HEAD^{commit}"): self.project["commit"]}[args]


class ConfigurationTests(Fixture):
    def test_first_four_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:4]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "9eee51c8c2b77a938dad6044243cd8c6c18ecae909c5142b2059adfc4354e0bf")

    def test_first_seven_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:7]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "dfada91f5e31bf4df2de6d68dbbec59e22092c4bc78e8564aa36be4a720ad8cd")

    def test_eleven_supplements_and_original_391_project_snapshot_are_pinned(self):
        config = dependencies.load_config()
        self.assertEqual(config["base"]["project_count"], 391)
        self.assertEqual(config["projects"], [{
            "path": "system/bpf", "url": "https://android.googlesource.com/platform/system/bpf",
            "commit": "4447acd742bf443f9088c300bd69f96ede8eaeb1", "tag": "android-16.0.0_r1",
            "reason": "Official AOSP provider of bpf_cc_defaults required by the selected Connectivity BPF headers. This addition supplements, and does not rewrite, the frozen 391-project Repo baseline."
        }, {
            "path": "packages/modules/NetworkStack",
            "url": "https://android.googlesource.com/platform/packages/modules/NetworkStack",
            "commit": "f9da1fc7154ea007aa835f88e8070c6ac46d54e9", "tag": "android-16.0.0_r1",
            "reason": config["projects"][1]["reason"]
        }, {
            "path": "hardware/google/apf", "url": "https://android.googlesource.com/platform/hardware/google/apf",
            "commit": "40d36d317d9367641e685e88e46343f25b192fc4", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP APF libraries required by NetworkStack JNI test defaults."
        }, {
            "path": "external/libpcap", "url": "https://android.googlesource.com/platform/external/libpcap",
            "commit": "2e9a50d7694425ead7595bf98d3a9c0ab790e4f9", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libpcap provider required by NetworkStack JNI test defaults."
        }, {
            "path": "platform_testing", "url": "https://android.googlesource.com/platform/platform_testing",
            "commit": "7b48625b052b94b1ef24573ef5e8ffa5e2ea9783", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP Tradefed defaults required by retained shared test infrastructure."
        }, {
            "path": "frameworks/libs/native_bridge_support",
            "url": "https://android.googlesource.com/platform/frameworks/libs/native_bridge_support",
            "commit": "b527289974e3883460370012325ab3736d59268a", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP native_bridge_proxy_libc_defaults required by the retained binary translation libc proxy."
        }, {
            "path": "external/skia", "url": "https://android.googlesource.com/platform/external/skia",
            "commit": "bcb0f77c44783b1800ba37641ba7ecab04f05e07", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP skia_deps and skia_renderengine_deps required by retained HWUI and RenderEngine framework code."
        }, {
            "path": "external/harfbuzz_ng", "url": "https://android.googlesource.com/platform/external/harfbuzz_ng",
            "commit": "e489c416b6f8d2a9a2e0e85b781d1e4a0c431401", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libharfbuzz_subset provider required by Skia font subsetting."
        }, {
            "path": "external/webp", "url": "https://android.googlesource.com/platform/external/webp",
            "commit": "7698c1d3a5cbecdf336510eeb3366d1de752454a", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libwebp-decode and libwebp-encode providers required by Skia image codecs."
        }, {
            "path": "external/rust/crabbyavif", "url": "https://android.googlesource.com/platform/external/rust/crabbyavif",
            "commit": "9f3e32a2ffc45466eaed69ad522080cbf67f827b", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libcrabbyavif_ffi provider required by Skia AVIF support."
        }, {
            "path": "external/libjpeg-turbo", "url": "https://android.googlesource.com/platform/external/libjpeg-turbo",
            "commit": "6cedbd6ff13946bef76a015693d02723b0d3226e", "tag": "android-16.0.0_r1",
            "reason": "Real current AOSP libjpeg provider required by Skia image codecs; profile metadata and legacy VNDK prebuilts are not substitutes."}])
        self.assertIn("libnetworkstackutilsjni_deps", config["projects"][1]["reason"])
        self.assertIn("tests/unit/Android.bp", config["projects"][1]["reason"])
        snapshot = dependencies.ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), config["base"]["frozen_manifest_sha256"])

    def test_supplementary_projects_are_outside_the_frozen_repo_project_paths(self):
        config = dependencies.load_config()
        snapshot = dependencies.ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
        frozen = twrp_workspace.parse_manifest(snapshot.read_text(), resolved=True)
        self.assertEqual(len(frozen), 391)
        for project in config["projects"]:
            with self.subTest(path=project["path"]):
                self.assertFalse(any(twrp_workspace.overlap(Path(project["path"]), Path(path)) for path in frozen))

    def test_optional_configuration_preserves_older_control_bundles(self):
        (self.control / dependencies.CONFIG).unlink()
        with patch.object(twrp_workspace, "run", side_effect=AssertionError("No process")):
            self.assertIsNone(dependencies.load_config(self.control))
            self.assertIsNone(dependencies.descriptor(self.control))
            self.assertIsNone(dependencies.verify(self.control, self.source))

    def test_plan_is_default_and_never_runs_commands_probes_or_writes(self):
        with patch.object(twrp_workspace, "run", side_effect=AssertionError("No process")), \
             patch.object(twrp_workspace, "require_host", side_effect=AssertionError("No probe")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("No write")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(dependencies.main(["--control-root", str(self.control)]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["action"], "plan")
        self.assertFalse(report["executes_commands"])
        self.assertFalse(report["writes_files"])

    def test_descriptor_binds_exact_configuration_bytes(self):
        before = dependencies.descriptor(self.control)
        self.config["projects"][0]["reason"] += " Additional review."
        self.save_config()
        after = dependencies.descriptor(self.control)
        self.assertNotEqual(before["configuration_sha256"], after["configuration_sha256"])
        self.assertEqual(after["projects"], self.config["projects"])

    def test_bad_paths_origins_tags_and_pins_are_rejected(self):
        original = copy.deepcopy(self.config)
        for key, value in (("path", "../outside"), ("path", ".repo/manifests"),
                           ("url", "https://user:secret@example.com/repo"),
                           ("url", "file:///private/source"), ("tag", "--upload-pack=evil"),
                           ("tag", "../ref"), ("commit", "main")):
            self.config = copy.deepcopy(original)
            self.config["projects"][0][key] = value
            self.save_config()
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                dependencies.load_config(self.control)

    def test_duplicate_or_overlapping_projects_are_rejected(self):
        for path in ("system/bpf", "system/bpf/nested", "system"):
            self.config["projects"] = [self.project, dict(self.project, path=path)]
            self.save_config()
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "overlap"):
                dependencies.load_config(self.control)

    def test_symlinked_config_is_not_treated_as_optional(self):
        path = self.control / dependencies.CONFIG
        path.unlink()
        path.symlink_to(self.root / "missing.json")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            dependencies.load_config(self.control)


class BaseTests(Fixture):
    def test_base_context_requires_original_snapshot_and_retains_optional_paths(self):
        with self.base_mocks():
            context = dependencies.base_context(self.control, self.source, paths=self.paths)
        self.assertEqual(context["frozen"], self.frozen)
        self.assertEqual(context["paths"], self.paths)

    def test_wrong_source_path_is_rejected_before_git_or_snapshot_reads(self):
        with patch.object(twrp_workspace, "verify_control") as control, self.assertRaisesRegex(ValueError, "explicitly selected"):
            dependencies.base_context(self.control, self.root / "other")
        control.assert_not_called()

    def test_changed_frozen_snapshot_is_never_accepted(self):
        (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).write_text(BASE_MANIFEST + "\n")
        with self.base_mocks(), self.assertRaisesRegex(ValueError, "immutable base"):
            dependencies.base_context(self.control, self.source)

    def test_changed_base_manifest_pin_is_rejected(self):
        self.config["base"]["manifest_commit"] = "f" * 40
        self.save_config()
        with self.base_mocks(), self.assertRaisesRegex(ValueError, "pinned base"):
            dependencies.base_context(self.control, self.source)

    def test_supplementary_sources_cannot_overlap_base_projects(self):
        for path in ("build/make", "build/make/nested", "build"):
            self.config["projects"][0]["path"] = path
            self.save_config()
            with self.subTest(path=path), self.base_mocks(), self.assertRaisesRegex(ValueError, "overlaps"):
                dependencies.base_context(self.control, self.source)

    def test_existing_unrelated_parent_checkout_is_rejected(self):
        (self.source / "system" / ".git").mkdir(parents=True)
        with self.base_mocks(), self.assertRaisesRegex(ValueError, "unrelated checkout"):
            dependencies.base_context(self.control, self.source)


class ProjectTests(Fixture):
    def setUp(self):
        super().setUp()
        self.make_project()

    def test_exact_standalone_project_is_accepted_without_mutation(self):
        with patch.object(dependencies, "git_value", side_effect=self.git):
            report = dependencies.verify_project(self.project, self.target)
        self.assertTrue(report["clean"])
        self.assertTrue(report["mode_changes_checked"])
        self.assertTrue(report["ignored_files_checked"])
        self.assertEqual(report["actual_head"], self.project["commit"])
        self.assertEqual(report["git_dir"], str(self.target / ".git"))

    def test_changed_head_origin_root_metadata_and_dirty_files_are_rejected(self):
        mutations = {("rev-parse", "HEAD"): "b" * 40,
                     ("remote", "get-url", "origin"): "https://example.com/wrong",
                     ("rev-parse", "--show-toplevel"): str(self.source),
                     ("rev-parse", "--absolute-git-dir"): str(self.source / ".repo/other.git"),
                     ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"): " M Android.bp\0"}
        for changed, value in mutations.items():
            def fake(target, *args):
                return value if args == changed else self.git(target, *args)
            with self.subTest(changed=changed), patch.object(dependencies, "git_value", side_effect=fake), self.assertRaises(ValueError):
                dependencies.verify_project(self.project, self.target)

    def test_ignored_files_and_mode_changes_are_not_clean_exceptions(self):
        for status in ("!! ignored/Android.bp\0", " M executable\0", "?? new-source\0"):
            def fake(target, *args):
                return status if args[0] == "status" else self.git(target, *args)
            with self.subTest(status=status), patch.object(dependencies, "git_value", side_effect=fake), self.assertRaisesRegex(ValueError, "local, ignored or mode"):
                dependencies.verify_project(self.project, self.target)

    def test_git_worktree_or_symlink_metadata_is_rejected(self):
        metadata = self.target / ".git"
        metadata.rmdir()
        metadata.write_text("gitdir: /outside")
        with self.assertRaisesRegex(ValueError, "non-standalone"):
            dependencies.verify_project(self.project, self.target)
        metadata.unlink()
        outside = self.root / "outside-git"
        outside.mkdir()
        metadata.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "non-standalone"):
            dependencies.verify_project(self.project, self.target)

    def test_git_process_forces_executable_mode_checks(self):
        with patch.object(twrp_workspace, "run", return_value=SimpleNamespace(stdout="")) as run:
            dependencies.git_value(self.target, "status")
        self.assertEqual(run.call_args.args[0], ["git", "-c", "core.fileMode=true",
                         "-c", "core.fsmonitor=false", "-c", "core.ignoreStat=false", "-C", self.target, "status"])

    def test_assume_unchanged_cannot_hide_modified_tracked_bytes(self):
        def hidden(target, *args):
            if args == ("ls-files", "-v", "-z"):
                return "h Android.bp\0H include/bpf.h\0"
            return self.git(target, *args)
        (self.target / "Android.bp").write_text("modified bytes hidden from ordinary git status")
        with patch.object(dependencies, "git_value", side_effect=hidden), self.assertRaisesRegex(ValueError, "hidden or unexpected"):
            dependencies.verify_project(self.project, self.target)
        self.assertEqual((self.target / "Android.bp").read_text(), "modified bytes hidden from ordinary git status")

    def test_skip_worktree_cannot_hide_modified_tracked_bytes(self):
        for flag in ("S", "s"):
            def hidden(target, *args):
                if args == ("ls-files", "-v", "-z"):
                    return f"{flag} Android.bp\0H include/bpf.h\0"
                return self.git(target, *args)
            with self.subTest(flag=flag), patch.object(dependencies, "git_value", side_effect=hidden), \
                 self.assertRaisesRegex(ValueError, "hidden or unexpected"):
                dependencies.verify_project(self.project, self.target)

    def test_empty_malformed_or_unmerged_index_records_are_rejected(self):
        for flags in ("", "H Android.bp", "H \0", "M conflict\0", "H Android.bp\0\0"):
            def fake(target, *args):
                return flags if args == ("ls-files", "-v", "-z") else self.git(target, *args)
            with self.subTest(flags=flags), patch.object(dependencies, "git_value", side_effect=fake), \
                 self.assertRaisesRegex(ValueError, "hidden or unexpected"):
                dependencies.verify_project(self.project, self.target)

    def test_verify_report_does_not_claim_it_validated_base_patch_contents(self):
        with self.base_mocks(), patch.object(dependencies, "git_value", side_effect=self.git):
            report = dependencies.verify(self.control, self.source)
        self.assertTrue(report["verified"])
        self.assertFalse(report["base_worktrees_checked"])
        self.assertEqual(report["base"]["frozen_manifest_sha256"], self.config["base"]["frozen_manifest_sha256"])

    def test_additive_sources_keep_bpf_and_base_snapshot_unchanged(self):
        original_bpf = copy.deepcopy(self.config["projects"][0])
        self.config["projects"] = dependencies.load_config()["projects"]
        self.save_config()
        projects = {self.source / project["path"]: project for project in self.config["projects"]}
        for project in self.config["projects"][1:]:
            (self.source / project["path"] / ".git").mkdir(parents=True)
        snapshot = (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes()
        def all_projects(target, *args):
            if args == ("rev-parse", "HEAD"):
                return projects[target]["commit"]
            if args == ("remote", "get-url", "origin"):
                return projects[target]["url"]
            return self.git(target, *args)
        with self.base_mocks(), patch.object(dependencies, "git_value", side_effect=all_projects):
            report = dependencies.verify(self.control, self.source)
        self.assertEqual(self.config["projects"][0], original_bpf)
        self.assertEqual([project["path"] for project in report["projects"]],
                         [project["path"] for project in self.config["projects"]])
        self.assertEqual([project["actual_head"] for project in report["projects"]],
                         [project["commit"] for project in self.config["projects"]])
        self.assertEqual((self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes(), snapshot)

    def test_valid_bpf_does_not_hide_any_wrong_supplementary_commit(self):
        self.config["projects"] = dependencies.load_config()["projects"]
        self.save_config()
        projects = {self.source / project["path"]: project for project in self.config["projects"]}
        for project in self.config["projects"][1:]:
            (self.source / project["path"] / ".git").mkdir(parents=True)
        for changed in self.config["projects"][1:]:
            def wrong_project(target, *args):
                if args == ("rev-parse", "HEAD"):
                    return "f" * 40 if target == self.source / changed["path"] else projects[target]["commit"]
                if args == ("remote", "get-url", "origin"):
                    return projects[target]["url"]
                return self.git(target, *args)
            with self.subTest(path=changed["path"]), self.base_mocks(), \
                 patch.object(dependencies, "git_value", side_effect=wrong_project), \
                 self.assertRaisesRegex(ValueError, changed["path"]):
                dependencies.verify(self.control, self.source)


class FetchTests(Fixture):
    def test_existing_verified_clone_is_not_downloaded_or_changed(self):
        self.make_project()
        with patch.object(dependencies, "git_value", side_effect=self.git), patch.object(twrp_workspace, "run") as run:
            report = dependencies.fetch_project(self.project, self.source)
        self.assertTrue(report["clean"])
        run.assert_not_called()

    def test_existing_empty_or_unrelated_directory_is_preserved(self):
        self.target.mkdir(parents=True)
        with patch.object(twrp_workspace, "run") as run, self.assertRaisesRegex(ValueError, "non-standalone"):
            dependencies.fetch_project(self.project, self.source)
        run.assert_not_called()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_fetch_uses_exact_tag_depth_and_verifies_before_exclusive_publish(self):
        calls = []
        def fake_run(args, **kwargs):
            calls.append(args)
            if args[:2] == ["git", "init"]:
                (Path(args[2]) / ".git").mkdir(parents=True)
            return SimpleNamespace(stdout="")
        def publish(staging, target):
            self.assertFalse(target.exists())
            staging.rename(target)
        with patch.object(twrp_workspace, "run", side_effect=fake_run), \
             patch.object(dependencies, "git_value", side_effect=self.git), \
             patch.object(dependencies, "publish_exclusive", side_effect=publish) as publish_mock:
            report = dependencies.fetch_project(self.project, self.source)
        self.assertTrue(report["clean"])
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[2][3:], ["fetch", "--depth=1", "--no-tags", "origin", "refs/tags/android-16.0.0_r1"])
        self.assertEqual(calls[3][3:], ["checkout", "--detach", self.project["commit"]])
        publish_mock.assert_called_once()
        self.assertEqual(sorted(path.name for path in self.target.parent.iterdir()), ["bpf"])

    def test_moved_upstream_tag_is_never_published(self):
        def fake_run(args, **kwargs):
            if args[:2] == ["git", "init"]:
                Path(args[2]).mkdir()
            return SimpleNamespace(stdout="")
        with patch.object(twrp_workspace, "run", side_effect=fake_run), \
             patch.object(dependencies, "git_value", return_value="f" * 40), \
             patch.object(dependencies, "publish_exclusive") as publish, self.assertRaisesRegex(ValueError, "upstream tag differs"):
            dependencies.fetch_project(self.project, self.source)
        publish.assert_not_called()
        self.assertFalse(self.target.exists())

    def test_host_failure_prevents_base_reads_or_downloads(self):
        with patch.object(twrp_workspace, "require_host", side_effect=ValueError("host blocked")), \
             patch.object(dependencies, "base_context") as base, patch.object(dependencies, "fetch_project") as fetch, \
             self.assertRaisesRegex(ValueError, "host blocked"):
            dependencies.fetch(self.control, self.source, "native")
        base.assert_not_called()
        fetch.assert_not_called()

    def test_base_head_or_origin_failures_prevent_source_additions(self):
        report = {"projects": [{"path": "build/make", "errors": ["HEAD differs"], "clean": True}], "all_present": True}
        with self.base_mocks(), patch.object(twrp_workspace, "require_host", return_value={}), \
             patch.object(twrp_workspace, "project_report", return_value=report), \
             patch.object(dependencies, "fetch_project") as fetch, self.assertRaisesRegex(ValueError, "Base project"):
            dependencies.fetch(self.control, self.source, "native")
        fetch.assert_not_called()

    def test_preexisting_base_patch_status_is_recorded_not_silently_marked_clean(self):
        base = {"projects": [{"path": "build/make", "errors": ["Local changes preserved"],
                               "clean": False, "local_changes": " M reviewed.mk"}], "all_present": True}
        self.make_project()
        snapshot = (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes()
        with self.base_mocks(), patch.object(twrp_workspace, "require_host", return_value={"supported_build_host": True}), \
             patch.object(twrp_workspace, "project_report", return_value=base), \
             patch.object(dependencies, "git_value", side_effect=self.git):
            report = dependencies.fetch(self.control, self.source, "native")
        self.assertEqual(report["base_dirty_projects"], [{"path": "build/make", "local_changes": " M reviewed.mk"}])
        self.assertTrue(report["base_worktrees_checked"])
        self.assertEqual((self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes(), snapshot)
        self.assertEqual(len(list(self.paths["report_dir"].glob("dependencies-fetch-*.json"))), 1)


class PublicationAndLockTests(Fixture):
    def test_publish_uses_linux_noreplace_rename(self):
        rename = Mock(return_value=0)
        with patch.object(dependencies.ctypes, "CDLL", return_value=SimpleNamespace(renameat2=rename)):
            dependencies.publish_exclusive(self.root / "staging", self.target)
        self.assertEqual(rename.call_args.args, (-100, bytes(self.root / "staging"), -100, bytes(self.target), 1))

    def test_publish_collision_is_not_retried_as_an_overwrite(self):
        rename = Mock(return_value=-1)
        with patch.object(dependencies.ctypes, "CDLL", return_value=SimpleNamespace(renameat2=rename)), \
             patch.object(dependencies.ctypes, "get_errno", return_value=errno.EEXIST), self.assertRaises(FileExistsError):
            dependencies.publish_exclusive(self.root / "staging", self.target)
        self.assertEqual(rename.call_count, 1)

    def test_missing_atomic_noreplace_support_fails_closed(self):
        with patch.object(dependencies.ctypes, "CDLL", return_value=SimpleNamespace()), self.assertRaisesRegex(ValueError, "renameat2"):
            dependencies.publish_exclusive(self.root / "staging", self.target)

    def test_active_or_stale_build_lock_prevents_fetch_before_mutations(self):
        lock = self.paths["report_dir"] / "build-operation.lock"
        lock.write_text("existing build")
        with patch.object(twrp_workspace, "require_host", return_value={}), \
             patch.object(dependencies, "base_context") as base, self.assertRaisesRegex(ValueError, "owns the lock"):
            dependencies.fetch(self.control, self.source, "native")
        base.assert_not_called()
        self.assertEqual(lock.read_text(), "existing build")

    def test_only_owned_lock_is_released(self):
        lock = self.paths["report_dir"] / "build-operation.lock"
        with dependencies.operation_lock(self.paths):
            self.assertTrue(lock.is_file())
        self.assertFalse(lock.exists())
        with dependencies.operation_lock(self.paths):
            lock.write_text("replacement")
        self.assertEqual(lock.read_text(), "replacement")


if __name__ == "__main__":
    unittest.main()
