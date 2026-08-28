"""Offline supplementary patch contract tests; no real Git or device processes."""

from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import twrp_build as build
from scripts import twrp_dependencies as dependencies
from scripts import twrp_workspace
from test_twrp_build import BuildFixture


def blob_sha1(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def patch_record(project, relative, before, after, identifier="0002-supplement-fixture"):
    return {
        "id": identifier,
        "project": project["path"],
        "base_commit": project["commit"],
        "repository": project["url"],
        "patch": f"patches/twrp/{identifier}.patch",
        "patch_sha256": "d" * 64,
        "files": [{
            "path": relative,
            "before_sha256": hashlib.sha256(before).hexdigest(),
            "after_sha256": hashlib.sha256(after).hexdigest(),
            "before_size_bytes": len(before),
            "after_size_bytes": len(after),
            "before_git_blob": blob_sha1(before),
            "after_git_blob": blob_sha1(after),
        }],
    }


class SupplementFixture(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.source = self.root / "source"
        self.project = {
            "path": "frameworks/libs/supplement_fixture",
            "url": "https://example.org/platform/frameworks/libs/supplement_fixture",
            "commit": "b" * 40,
            "tag": "android-16.0.0_r1",
            "reason": "Synthetic reviewed source used only by offline tests.",
        }
        self.target = self.source / self.project["path"]
        (self.target / ".git").mkdir(parents=True)
        self.before, self.after = b"old source\n", b"new source\n"
        self.relative = "animation/Android.bp"
        self.source_file = self.target / self.relative
        self.source_file.parent.mkdir()
        self.source_file.write_bytes(self.before)
        self.source_file.chmod(0o644)
        self.entry = patch_record(self.project, self.relative, self.before, self.after)
        self.status = ""
        self.flags = f"H {self.relative}\0"
        self.tree_mode = "100644"
        self.overrides = {}
        self.run_mock = self.stack.enter_context(
            patch.object(twrp_workspace, "run", side_effect=self.fake_git))
        self.process_mock = self.stack.enter_context(
            patch.object(dependencies.subprocess, "run", side_effect=AssertionError("Unexpected process")))

    def fake_git(self, args, **kwargs):
        self.assertEqual(args[0], "git")
        index = args.index("-C")
        self.assertEqual(Path(args[index + 1]), self.target)
        command = tuple(args[index + 2:])
        if command in self.overrides:
            return SimpleNamespace(stdout=self.overrides[command], returncode=0)
        values = {
            ("rev-parse", "--show-toplevel"): str(self.target),
            ("rev-parse", "--absolute-git-dir"): str(self.target / ".git"),
            ("rev-parse", "HEAD"): self.project["commit"],
            ("remote", "get-url", "origin"): self.project["url"],
            ("ls-files", "-v", "-z"): self.flags,
            ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"): self.status,
            ("ls-tree", "-z", self.project["commit"], "--", self.relative):
                f"{self.tree_mode} blob {blob_sha1(self.before)}\t{self.relative}\0",
        }
        self.assertIn(command, values, f"Unexpected Git command: {command!r}")
        return SimpleNamespace(stdout=values[command], returncode=0)

    def make_after(self):
        self.source_file.write_bytes(self.after)
        self.status = f" M {self.relative}\0"

    def verify(self, phase="after", patches=None):
        return dependencies.verify_project(
            self.project, self.target,
            patches=[self.entry] if patches is None else patches,
            phase=phase,
        )


class SupplementProjectTests(SupplementFixture):
    def test_default_remains_pristine_and_does_not_infer_a_patch(self):
        self.assertTrue(dependencies.verify_project(self.project, self.target)["clean"])
        self.make_after()
        with self.assertRaises(ValueError):
            dependencies.verify_project(self.project, self.target)
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.process_mock.assert_not_called()

    def test_explicit_preimage_is_pristine_and_postimage_is_not_reported_clean(self):
        self.assertTrue(self.verify("before")["clean"])
        self.make_after()
        result = self.verify()
        self.assertFalse(result["clean"])
        self.assertEqual(result["actual_head"], self.project["commit"])
        self.assertEqual(result["actual_origin"], self.project["url"])
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))
        self.process_mock.assert_not_called()

    def test_postimage_requires_exact_raw_unstaged_status_with_nul_terminator(self):
        self.make_after()
        self.verify()
        statuses = (
            "", f"M {self.relative}\0", f" M {self.relative}",
            f" M {self.relative}\0\0", f" M {self.relative}\0 M {self.relative}\0",
            f"M  {self.relative}\0", f"MM {self.relative}\0", f"A  {self.relative}\0",
            f" D {self.relative}\0", f" T {self.relative}\0", f"UU {self.relative}\0",
            f"R  {self.relative}\0old-name\0", f"?? {self.relative}\0", f"!! {self.relative}\0",
        )
        for status in statuses:
            self.status = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.verify()
        self.assertEqual(self.source_file.read_bytes(), self.after)

    def test_approved_patch_never_hides_other_tracked_untracked_or_ignored_files(self):
        self.make_after()
        for extra in (" M other.bp", "?? new-source", "!! ignored/Android.bp", "M  other.bp"):
            self.status = f" M {self.relative}\0{extra}\0"
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.verify()

    def test_declared_phase_cannot_be_inferred_from_live_bytes(self):
        with self.assertRaises(ValueError):
            self.verify("after")
        self.make_after()
        with self.assertRaises(ValueError):
            self.verify("before")
        self.status = ""
        with self.assertRaises(ValueError):
            self.verify("before")
        for phase in ("", "prepared", "either", None):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                self.verify(phase)

    def test_patch_project_commit_and_repository_must_match_the_supplement(self):
        self.make_after()
        for key, value in (("project", "frameworks/libs/other"),
                           ("base_commit", "f" * 40),
                           ("repository", "https://example.org/wrong")):
            changed = copy.deepcopy(self.entry)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(patches=[changed])

    def test_postimage_does_not_relax_head_origin_root_or_git_metadata_checks(self):
        self.make_after()
        for command, value in (
            (("rev-parse", "HEAD"), "f" * 40),
            (("remote", "get-url", "origin"), "https://example.org/wrong"),
            (("rev-parse", "--show-toplevel"), str(self.source)),
            (("rev-parse", "--absolute-git-dir"), str(self.root / "outside.git")),
        ):
            self.overrides = {command: value}
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.verify()

    def test_hidden_malformed_and_unmerged_index_records_are_never_accepted(self):
        self.make_after()
        for flags in (f"h {self.relative}\0", f"S {self.relative}\0", f"s {self.relative}\0",
                      f"M {self.relative}\0", "", "H \0", f"H {self.relative}",
                      f"H {self.relative}\0\0"):
            self.flags = flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                self.verify()

    def test_postimage_requires_exact_bytes_size_and_declared_git_blob(self):
        self.make_after()
        for data in (b"bad source\n", b"another source\n"):
            self.source_file.write_bytes(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.verify()
            self.assertEqual(self.source_file.read_bytes(), data)
        self.source_file.write_bytes(self.after)
        for field in ("before_git_blob", "after_git_blob", "after_sha256", "after_size_bytes"):
            changed = copy.deepcopy(self.entry)
            changed["files"][0][field] = 999 if field.endswith("size_bytes") else "0" * (64 if field.endswith("sha256") else 40)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(patches=[changed])

    def test_approved_postimage_requires_the_canonical_pinned_file_mode(self):
        self.make_after()
        for mode in (0o600, 0o664, 0o744, 0o755):
            self.source_file.chmod(mode)
            with self.subTest(mode=oct(mode)), self.assertRaises(ValueError):
                self.verify()
        self.source_file.chmod(0o644)
        self.verify()

    def test_pinned_executable_mode_is_preserved_without_chmod(self):
        self.tree_mode = "100755"
        self.source_file.chmod(0o755)
        self.verify("before")
        self.make_after()
        self.verify()
        self.assertEqual(self.source_file.stat().st_mode & 0o777, 0o755)
        self.source_file.chmod(0o644)
        with self.assertRaises(ValueError):
            self.verify()

    def test_pinned_blob_queries_never_use_mutable_head(self):
        self.make_after()
        self.verify()
        queries = [call.args[0] for call in self.run_mock.call_args_list if "ls-tree" in call.args[0]]
        self.assertTrue(queries)
        self.assertTrue(all(args[args.index("ls-tree") + 2] == self.project["commit"] for args in queries))

    def test_symlinked_patch_file_is_preserved_and_rejected(self):
        self.make_after()
        outside = self.root / "outside.bp"
        outside.write_bytes(self.after)
        self.source_file.unlink()
        self.source_file.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.verify()
        self.assertTrue(self.source_file.is_symlink())
        self.assertEqual(outside.read_bytes(), self.after)

    def test_verify_filters_the_validated_queue_to_each_supplement_owner(self):
        other = dict(self.project, path="external/unpatched_fixture", commit="c" * 40)
        base_patch = dict(self.entry, id="0001-base", project="bootable/recovery", base_commit="a" * 40)
        reviewed = {"configuration_sha256": "d" * 64, "base": {}, "projects": [self.project, other]}
        context = {"reviewed": reviewed, "source": self.source, "frozen": {
            "bootable/recovery": {"revision": "a" * 40, "url": self.project["url"]},
        }}
        with patch.object(dependencies, "base_context", return_value=context), \
             patch.object(dependencies, "verify_project", return_value={"verified": True}) as verify:
            report = dependencies.verify(self.root, self.source, patches=[base_patch, self.entry], phase="after")
        self.assertTrue(report["verified"])
        self.assertEqual(verify.call_count, 2)
        first, second = verify.call_args_list
        self.assertEqual(first.args, (self.project, self.target))
        self.assertEqual(first.kwargs, {"patches": [self.entry], "phase": "after"})
        self.assertEqual(second.args, (other, self.source / other["path"]))
        self.assertEqual(second.kwargs, {"patches": [], "phase": "after"})

    def test_missing_active_checkout_is_never_recreated_by_fetch(self):
        shutil.rmtree(self.target)
        with self.assertRaises(ValueError):
            dependencies.fetch_project(self.project, self.source, patches=[self.entry], phase="after")
        self.run_mock.assert_not_called()
        self.assertFalse(self.target.exists())


class SupplementRegistryTests(SupplementFixture):
    def reviewed(self):
        return {"patches": [self.entry], "supplementary_projects": {
            "configuration_sha256": "c" * 64,
            "base": {"project_count": 1, "frozen_manifest_sha256": "e" * 64},
            "projects": [self.project],
        }}

    def test_patch_can_only_target_an_explicit_supplementary_pin_in_the_contract(self):
        build.validate_patch_bases({}, self.reviewed())
        reviewed = self.reviewed()
        del reviewed["supplementary_projects"]
        with self.assertRaises(ValueError):
            build.validate_patch_bases({}, reviewed)

    def test_supplementary_patch_base_and_origin_must_both_match(self):
        for key, value in (("base_commit", "f" * 40), ("repository", "https://example.org/wrong")):
            reviewed = copy.deepcopy(self.reviewed())
            reviewed["patches"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                build.validate_patch_bases({}, reviewed)

    def test_supplementary_pin_cannot_shadow_a_frozen_project(self):
        frozen = {self.project["path"]: {"revision": self.project["commit"], "url": self.project["url"]}}
        with self.assertRaises(ValueError):
            build.validate_patch_bases(frozen, self.reviewed())

    def test_supplementary_patch_requires_explicit_origin_and_both_git_blobs(self):
        for field in ("repository", "before_git_blob", "after_git_blob"):
            reviewed = copy.deepcopy(self.reviewed())
            target = reviewed["patches"][0] if field == "repository" else reviewed["patches"][0]["files"][0]
            del target[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                build.validate_patch_bases({}, reviewed)


class SupplementBuildFixture(BuildFixture):
    def setUp(self):
        super().setUp()
        self.config.update({name: str(path) for name, path in self.paths.items()})
        (self.control / "config").mkdir()
        (self.control / "config/twrp.json").write_text(json.dumps(self.config))
        self.stack.enter_context(patch.object(twrp_workspace, "load_config",
                                             side_effect=lambda path: json.loads(path.read_text())))
        self.supplement = {
            "path": "frameworks/libs/supplement_fixture",
            "url": "https://example.org/platform/frameworks/libs/supplement_fixture",
            "commit": "e" * 40,
            "tag": "android-16.0.0_r1",
            "reason": "Synthetic reviewed source used only by offline tests.",
        }
        self.supplement_dir = self.source / self.supplement["path"]
        (self.supplement_dir / ".git").mkdir(parents=True)
        (self.supplement_dir / "README.txt").write_text("pristine fixture\n")
        self.supplement_inputs = {}
        self.supplement_prechecks = []
        self.supplement_extra_status = []
        self.after_supplement_apply = None
        self.supplement_config = {
            "schema_version": 1,
            "device": "nezha",
            "base": {
                "source_dir": str(self.source),
                "manifest_commit": self.config["manifest"]["commit"],
                "repo_commit": self.config["repo_tool"]["commit"],
                "frozen_manifest_sha256": build.sha256(
                    (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes()),
                "project_count": 1,
            },
            "projects": [self.supplement],
        }
        self.write_supplement_config()

    def write_supplement_config(self):
        (self.control / dependencies.CONFIG).write_text(json.dumps(self.supplement_config))

    def append_supplement_patch(self, relative="animation/Android.bp"):
        before, after = b"old source\n", b"reviewed source\n"
        source_file = self.supplement_dir / relative
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_bytes(before)
        source_file.chmod(0o644)
        identifier = f"{len(self.series['patches']) + 1:04d}-supplement-fixture"
        entry = patch_record(self.supplement, relative, before, after, identifier)
        payload = self.control / entry["patch"]
        payload.write_text(f"diff --git a/{relative} b/{relative}\n"
                           f"index {blob_sha1(before)}..{blob_sha1(after)} 100644\n"
                           f"--- a/{relative}\n+++ b/{relative}\n@@ -1 +1 @@\n-old source\n+reviewed source\n")
        entry["patch_sha256"] = build.sha256(payload.read_bytes())
        self.supplement_inputs[relative] = {"entry": entry, "before": before, "after": after}
        self.series["patches"].append(entry)
        self.write_series()
        return entry

    def fake_git(self, args, **kwargs):
        if not hasattr(self, "supplement_dir"):
            return super().fake_git(args, **kwargs)
        index = args.index("-C")
        directory, command = Path(args[index + 1]), tuple(args[index + 2:])
        if directory != self.supplement_dir:
            return super().fake_git(args, **kwargs)
        changed = [" M " + relative for relative, item in self.supplement_inputs.items()
                   if (directory / relative).read_bytes() != item["before"]]
        values = {
            ("rev-parse", "--show-toplevel"): str(directory),
            ("rev-parse", "--absolute-git-dir"): str(directory / ".git"),
            ("rev-parse", "HEAD"): self.supplement["commit"],
            ("remote", "get-url", "origin"): self.supplement["url"],
            ("ls-files", "-v", "-z"): "H README.txt\0" + "".join(
                f"H {relative}\0" for relative in sorted(self.supplement_inputs)),
            ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"):
                "".join(entry + "\0" for entry in sorted(changed + self.supplement_extra_status)),
        }
        if command in values:
            return SimpleNamespace(stdout=values[command], returncode=0)
        if command[0] == "ls-tree":
            self.assertEqual(command[:4], ("ls-tree", "-z", self.supplement["commit"], "--"))
            relative = command[-1]
            self.assertIn(relative, self.supplement_inputs)
            item = self.supplement_inputs[relative]
            return SimpleNamespace(stdout=f"100644 blob {blob_sha1(item['before'])}\t{relative}\0", returncode=0)
        self.assertEqual(command[0], "apply", f"Unexpected Git command: {command!r}")
        digest = build.sha256(Path(args[-1]).read_bytes())
        matches = [(relative, item) for relative, item in self.supplement_inputs.items()
                   if item["entry"]["patch_sha256"] == digest]
        self.assertEqual(len(matches), 1)
        relative, item = matches[0]
        if "--check" in command:
            self.assertEqual((directory / relative).read_bytes(), item["before"])
            self.supplement_prechecks.append(item["entry"]["id"])
        else:
            self.assertIn(item["entry"]["id"], self.supplement_prechecks)
            (directory / relative).write_bytes(item["after"])
            if self.after_supplement_apply is not None:
                self.after_supplement_apply()
        return SimpleNamespace(stdout="", returncode=0)

    def preserve_previous(self):
        self.previous = self.root / "previous-control"
        shutil.copytree(self.control, self.previous)
        self.before_state = (self.paths["report_dir"] / build.STATE).read_bytes()
        self.run_mock.reset_mock()

    def revise(self):
        return build.revise(self.config, self.paths, "native", self.previous, self.control)

    def fetch(self, previous=True):
        kwargs = {"previous_control_root": self.previous} if previous else {}
        return dependencies.fetch(self.control, self.source, "native", paths=self.paths, **kwargs)


class SupplementPreparationTests(SupplementBuildFixture):
    def test_prepare_applies_supplement_patch_and_records_exact_contract(self):
        entry = self.append_supplement_patch()
        report = self.prepare()
        state = json.loads((self.paths["report_dir"] / build.STATE).read_text())
        self.assertIn(entry["id"], report["patch_ids"])
        self.assertEqual(state["controls"]["patches"], self.series["patches"])
        self.assertEqual(state["controls"]["supplementary_projects"], dependencies.descriptor(self.control))
        self.assertEqual(self.check()["source"], state["source"])
        self.assertEqual(state["source"]["project_count"], 1)
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.process_mock.assert_not_called()

    def test_prepare_postvalidation_rejects_extra_supplement_changes_before_receipt(self):
        entry = self.append_supplement_patch()
        self.after_supplement_apply = lambda: self.supplement_extra_status.append("!! generated/Android.bp")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.paths["report_dir"] / build.STATE).exists())
        self.assertEqual((self.supplement_dir / entry["files"][0]["path"]).read_bytes(), b"reviewed source\n")
        self.assertTrue(list(self.paths["report_dir"].glob("prepare-start-*.json")))

    def test_prepare_rejects_controls_changed_after_supplement_application(self):
        entry = self.append_supplement_patch()

        def change_controls():
            entry["reason"] = "changed after the preparation contract was read"
            self.write_series()

        self.after_supplement_apply = change_controls
        with self.assertRaisesRegex(ValueError, "controls changed"):
            self.prepare()
        self.assertFalse((self.paths["report_dir"] / build.STATE).exists())
        self.assertEqual((self.supplement_dir / entry["files"][0]["path"]).read_bytes(), b"reviewed source\n")
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.assertTrue(list(self.paths["report_dir"].glob("prepare-start-*.json")))
        self.assertEqual(json.loads((self.control / build.SERIES).read_text()), self.series)

    def test_prepare_rejects_a_patched_supplement_without_existing_receipt(self):
        entry = self.append_supplement_patch()
        path = self.supplement_dir / entry["files"][0]["path"]
        path.write_bytes(b"reviewed source\n")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.source / build.TARGET).exists())
        self.assertFalse((self.paths["report_dir"] / build.STATE).exists())
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_check_rejects_later_supplement_edits_and_preserves_receipt(self):
        entry = self.append_supplement_patch()
        self.prepare()
        state = (self.paths["report_dir"] / build.STATE).read_bytes()
        path = self.supplement_dir / entry["files"][0]["path"]
        path.write_bytes(b"unknown local change\n")
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), state)
        self.assertEqual(path.read_bytes(), b"unknown local change\n")

    def test_check_rejects_receipt_changed_after_source_verification(self):
        self.append_supplement_patch()
        self.prepare()
        state_path = self.paths["report_dir"] / build.STATE
        original_state = state_path.read_bytes()
        reports_before = sorted(path.name for path in self.paths["report_dir"].iterdir())
        changed_states = []
        original_verify = build.verify_sources

        def verify_then_change_receipt(*args, **kwargs):
            report = original_verify(*args, **kwargs)
            state = json.loads(state_path.read_text())
            state["controls"]["patches"][-1]["reason"] = "receipt changed during verification"
            changed = (json.dumps(state, indent=2) + "\n").encode()
            state_path.write_bytes(changed)
            changed_states.append(changed)
            return report

        with patch.object(build, "verify_sources", side_effect=verify_then_change_receipt), \
             self.assertRaises(ValueError):
            build.check(self.config, self.paths, "native", self.control, record=False)
        self.assertEqual(len(changed_states), 1)
        self.assertNotEqual(changed_states[0], original_state)
        self.assertEqual(state_path.read_bytes(), changed_states[0])
        self.assertEqual(sorted(path.name for path in self.paths["report_dir"].iterdir()), reports_before)

    def test_check_rejects_controls_changed_after_source_verification(self):
        entry = self.append_supplement_patch()
        self.prepare()
        state_path = self.paths["report_dir"] / build.STATE
        original_state = state_path.read_bytes()
        reports_before = sorted(path.name for path in self.paths["report_dir"].iterdir())
        changed_controls = []
        original_verify = build.verify_sources

        def verify_then_change_controls(*args, **kwargs):
            report = original_verify(*args, **kwargs)
            entry["reason"] = "controls changed during verification"
            self.write_series()
            changed_controls.append((self.control / build.SERIES).read_bytes())
            return report

        with patch.object(build, "verify_sources", side_effect=verify_then_change_controls), \
             self.assertRaises(ValueError):
            build.check(self.config, self.paths, "native", self.control, record=False)
        self.assertEqual(len(changed_controls), 1)
        self.assertEqual((self.control / build.SERIES).read_bytes(), changed_controls[0])
        self.assertEqual(state_path.read_bytes(), original_state)
        self.assertEqual(sorted(path.name for path in self.paths["report_dir"].iterdir()), reports_before)


class SupplementRevisionTests(SupplementBuildFixture):
    def assert_failed_revision_kept_partial_source_and_receipt(self, entry):
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        archives = list((self.paths["report_dir"] / "build-revisions").iterdir())
        self.assertEqual(len(archives), 1)
        archive = archives[0]
        relative = self.supplement["path"] + "/" + entry["files"][0]["path"]
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.before_state)
        self.assertEqual((archive / "source-before" / relative).read_bytes(), b"old source\n")
        self.assertEqual((archive / "source-after" / relative).read_bytes(), b"reviewed source\n")
        self.assertEqual((self.source / relative).read_bytes(), b"reviewed source\n")
        failures = list(self.paths["report_dir"].glob("revise-failed-*.json"))
        self.assertEqual(len(failures), 1)
        failure = json.loads(failures[0].read_text())
        self.assertEqual(failure["applied_patch_ids"], [entry["id"]])
        self.assertFalse(failure.get("revision_committed", False))

    def test_revision_admits_first_supplement_patch_without_changing_base_snapshot(self):
        self.prepare()
        self.preserve_previous()
        entry = self.append_supplement_patch()
        report = self.revise()
        archive = Path(report["revision_archive"])
        relative = self.supplement["path"] + "/" + entry["files"][0]["path"]
        self.assertEqual(report["added_patch_ids"], [entry["id"]])
        self.assertEqual((archive / "source-before" / relative).read_bytes(), b"old source\n")
        self.assertEqual((archive / "source-after" / relative).read_bytes(), b"reviewed source\n")
        self.assertEqual(report["source"], json.loads(self.before_state)["source"])
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.before_state)
        self.assertEqual(self.check()["build_state_sha256"], report["build_state_sha256"])

    def test_revision_preserves_previous_supplement_postimage_and_appends_a_new_file(self):
        first = self.append_supplement_patch()
        self.prepare()
        self.preserve_previous()
        second = self.append_supplement_patch("animation/tests/Android.bp")
        report = self.revise()
        self.assertEqual(report["added_patch_ids"], [second["id"]])
        self.assertEqual(self.supplement_prechecks.count(first["id"]), 1)
        self.assertEqual(self.supplement_prechecks.count(second["id"]), 1)
        self.assertEqual(self.check()["build_state_sha256"], report["build_state_sha256"])
        self.run_mock.reset_mock()
        self.assertTrue(self.revise()["already_current"])
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_revision_postvalidation_does_not_advance_receipt_after_extra_changes(self):
        self.prepare()
        self.preserve_previous()
        self.append_supplement_patch()
        self.after_supplement_apply = lambda: self.supplement_extra_status.append("?? new-file")
        with self.assertRaises(ValueError):
            self.revise()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertTrue(list(self.paths["report_dir"].glob("revise-failed-*.json")))
        self.run_mock.reset_mock()
        with self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_revision_rejects_current_controls_changed_after_supplement_application(self):
        self.prepare()
        self.preserve_previous()
        entry = self.append_supplement_patch()

        def change_controls():
            entry["reason"] = "changed after the revision contract was read"
            self.write_series()

        self.after_supplement_apply = change_controls
        with self.assertRaisesRegex(ValueError, "control bundle changed"):
            self.revise()
        self.assert_failed_revision_kept_partial_source_and_receipt(entry)
        self.assertEqual(json.loads((self.control / build.SERIES).read_text()), self.series)

    def test_revision_rejects_previous_controls_changed_after_supplement_application(self):
        self.prepare()
        self.preserve_previous()
        entry = self.append_supplement_patch()
        previous_target = self.previous / build.TARGET_SOURCE / "device.mk"
        changed = "# previous control changed after the old state check\n"
        self.after_supplement_apply = lambda: previous_target.write_text(changed)
        with self.assertRaisesRegex(ValueError, "control bundle changed"):
            self.revise()
        self.assert_failed_revision_kept_partial_source_and_receipt(entry)
        self.assertEqual(previous_target.read_text(), changed)

    def test_revision_cannot_rewrite_the_old_supplement_patch_entry(self):
        first = self.append_supplement_patch()
        self.prepare()
        self.preserve_previous()
        self.append_supplement_patch("animation/tests/Android.bp")
        first["reason"] = "unapproved replacement of an existing entry"
        self.write_series()
        with self.assertRaises(ValueError):
            self.revise()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())


class SupplementFetchTests(SupplementBuildFixture):
    def setUp(self):
        super().setUp()
        self.active_entry = self.append_supplement_patch()
        self.prepare()
        self.preserve_previous()

    def test_fetch_accepts_only_the_exact_active_previous_bundle_without_applying(self):
        report = self.fetch()
        self.assertTrue(report["verified"])
        self.assertFalse(report["projects"][0]["clean"])
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse(any("apply" in call.args[0] or "fetch" in call.args[0] or "checkout" in call.args[0]
                             for call in self.run_mock.call_args_list))
        self.process_mock.assert_not_called()

    def test_fetch_without_previous_bundle_does_not_adopt_patched_sources(self):
        with self.assertRaises(ValueError):
            self.fetch(previous=False)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse(list(self.paths["report_dir"].glob("dependencies-fetch-*.json")))

    def test_fetch_accepts_active_postimages_while_proposed_patch_remains_unapplied(self):
        proposed = self.append_supplement_patch("animation/tests/Android.bp")
        report = self.fetch()
        self.assertTrue(report["verified"])
        self.assertEqual((self.supplement_dir / proposed["files"][0]["path"]).read_bytes(), b"old source\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_new_project_is_fetched_pristine_without_its_proposed_patch_exception(self):
        added = dict(self.supplement, path="external/added_fixture", commit="f" * 40,
                     url="https://example.org/platform/external/added_fixture")
        self.supplement_config["projects"].append(added)
        self.write_supplement_config()
        proposed = patch_record(added, "Android.bp", b"old source\n", b"reviewed source\n", "0003-added-fixture")
        payload = self.control / proposed["patch"]
        payload.write_text("diff --git a/Android.bp b/Android.bp\n"
                           "--- a/Android.bp\n+++ b/Android.bp\n@@ -1 +1 @@\n-old source\n+reviewed source\n")
        proposed["patch_sha256"] = build.sha256(payload.read_bytes())
        self.series["patches"].append(proposed)
        self.write_series()
        original_fetch = dependencies.fetch_project
        original_git = self.run_mock.side_effect
        added_dir = self.source / added["path"]
        added_calls = []

        def git(args, **kwargs):
            index = args.index("-C")
            if Path(args[index + 1]) != added_dir:
                return original_git(args, **kwargs)
            command = tuple(args[index + 2:])
            values = {
                ("rev-parse", "--show-toplevel"): str(added_dir),
                ("rev-parse", "--absolute-git-dir"): str(added_dir / ".git"),
                ("rev-parse", "HEAD"): added["commit"],
                ("remote", "get-url", "origin"): added["url"],
                ("ls-files", "-v", "-z"): "H Android.bp\0",
                ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"): "",
            }
            self.assertIn(command, values)
            return SimpleNamespace(stdout=values[command], returncode=0)

        def fetch_project(project, source, *args, **kwargs):
            if project["path"] != added["path"]:
                return original_fetch(project, source, *args, **kwargs)
            added_calls.append((args, kwargs))
            self.assertFalse(kwargs.get("patches", args[0] if args else ()))
            (added_dir / ".git").mkdir(parents=True)
            (added_dir / "Android.bp").write_bytes(b"old source\n")
            return dependencies.verify_project(project, added_dir)

        self.run_mock.side_effect = git
        with patch.object(dependencies, "fetch_project", side_effect=fetch_project):
            report = self.fetch()
        self.assertEqual(len(added_calls), 1)
        self.assertTrue(report["projects"][-1]["clean"])
        self.assertEqual((added_dir / "Android.bp").read_bytes(), b"old source\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_proposed_patch_cannot_authorize_unrecorded_postimage_during_fetch(self):
        proposed = self.append_supplement_patch("animation/tests/Android.bp")
        source_file = self.supplement_dir / proposed["files"][0]["path"]
        source_file.write_bytes(b"reviewed source\n")
        with self.assertRaises(ValueError):
            self.fetch()
        self.assertEqual(source_file.read_bytes(), b"reviewed source\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_wrong_previous_bundle_does_not_authorize_the_installed_patch(self):
        (self.previous / build.TARGET_SOURCE / "device.mk").write_text("# unrelated prior target\n")
        with self.assertRaises(ValueError):
            self.fetch()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)

    def test_fetch_rejects_rewriting_or_removing_a_recorded_patch_from_current_controls(self):
        original = copy.deepcopy(self.series)
        for change in ("rewrite", "remove"):
            self.series = copy.deepcopy(original)
            if change == "rewrite":
                self.series["patches"][-1]["reason"] = "unapproved rewrite of active entry"
            else:
                self.series["patches"].pop()
            self.write_series()
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.fetch()
            self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)

    def test_verify_previous_bundle_uses_only_active_patches_and_does_not_write_reports(self):
        self.append_supplement_patch("animation/tests/Android.bp")
        before_reports = sorted(path.name for path in self.paths["report_dir"].iterdir())
        result = dependencies.verify(self.control, self.source, paths=self.paths,
                                     previous_control_root=self.previous)
        self.assertTrue(result["verified"])
        self.assertEqual(result["projects"][0]["patch_ids"], [self.active_entry["id"]])
        self.assertEqual(sorted(path.name for path in self.paths["report_dir"].iterdir()), before_reports)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_verify_rejects_previous_bundle_changed_during_source_verification(self):
        previous_target = self.previous / build.TARGET_SOURCE / "device.mk"
        changed = "# prior controls changed during source verification\n"
        reports_before = sorted(path.name for path in self.paths["report_dir"].iterdir())
        original_verify = dependencies.twrp_patch_state.verify_sources
        changed_controls = []

        def verify_then_change_previous(*args, **kwargs):
            report = original_verify(*args, **kwargs)
            previous_target.write_text(changed)
            changed_controls.append(previous_target.read_bytes())
            return report

        with patch.object(dependencies.twrp_patch_state, "verify_sources", side_effect=verify_then_change_previous), \
             self.assertRaises(ValueError):
            dependencies.verify(self.control, self.source, paths=self.paths,
                                previous_control_root=self.previous)
        self.assertEqual(changed_controls, [changed.encode()])
        self.assertEqual(previous_target.read_text(), changed)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertEqual(sorted(path.name for path in self.paths["report_dir"].iterdir()), reports_before)
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_missing_or_changed_receipt_blocks_previous_bundle_fetch(self):
        state_path = self.paths["report_dir"] / build.STATE
        state_path.unlink()
        with self.assertRaises(ValueError):
            self.fetch()
        state = json.loads(self.before_state)
        state["controls"]["patches"][0]["id"] = "wrong-active-contract"
        state_path.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            self.fetch()
        self.assertEqual(json.loads(state_path.read_text()), state)

    def test_active_build_lock_blocks_fetch_without_clearing_or_mutating_state(self):
        lock = self.paths["report_dir"] / "build-operation.lock"
        lock.write_text("existing operation")
        with self.assertRaises(ValueError):
            self.fetch()
        self.assertEqual(lock.read_text(), "existing operation")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
