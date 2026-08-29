"""Synthetic linear patch chains. All Git/network/process calls are mocked."""

import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import twrp_patch_state as state
from scripts import twrp_build as build
from scripts import twrp_dependencies as dependencies
from test_twrp_build import BuildFixture


class ChainFixture(BuildFixture):
    def setUp(self):
        super().setUp()
        self.roots = {(self.project, "init.rc"): (self.before, 0o644)}
        self.transitions = {}
        self.apply_events = []
        self.live_status_override = None
        self.flags_override = None
        first = self.series["patches"][0]
        first["files"][0].update(before_git_blob=state.git_blob_sha1(self.before),
                                 after_git_blob=state.git_blob_sha1(self.after))
        self.install_payload(first, [("init.rc", self.before, self.after, 0o644)])
        self.write_series()
        self.process_mock.side_effect = self.fake_process
        self.run_mock.side_effect = self.fake_git

    def install_payload(self, entry, changes):
        data = b""
        for relative, before, after, mode in changes:
            diff = "".join(difflib.unified_diff(before.decode().splitlines(keepends=True),
                                               after.decode().splitlines(keepends=True),
                                               fromfile="a/" + relative, tofile="b/" + relative))
            data += (f"diff --git a/{relative} b/{relative}\nindex {state.git_blob_sha1(before)}.."
                     f"{state.git_blob_sha1(after)} 100{mode:o}\n" + diff).encode()
        payload = self.control / entry["patch"]
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(data)
        entry["patch_sha256"] = state.sha256(data)
        self.transitions[entry["patch_sha256"]] = (entry, changes)

    def append(self, changes=None, identifier=None, project=None):
        project = project or self.project
        if changes is None:
            last = next(entry for entry in reversed(self.series["patches"]) if entry["project"] == project)
            last_item = last["files"][0]
            prior = self.transitions[last["patch_sha256"]][1][0][2]
            changes = [(last_item["path"], prior, prior + b"next\n", 0o644, last["id"])]
        entry = {"id": identifier or f"{len(self.series['patches'])+1:04d}-chain", "project": project,
                 "base_commit": self.frozen[project]["revision"], "repository": self.frozen[project]["url"],
                 "patch": f"patches/twrp/chain-{len(self.series['patches'])+1:04d}.patch", "files": []}
        for relative, before, after, mode, predecessor in changes:
            item = {"path": relative, "before_sha256": state.sha256(before), "after_sha256": state.sha256(after),
                    "before_size_bytes": len(before), "after_size_bytes": len(after),
                    "before_git_blob": state.git_blob_sha1(before), "after_git_blob": state.git_blob_sha1(after)}
            if predecessor is not None:
                item["predecessor_patch_id"] = predecessor
            elif (project, relative) not in self.roots:
                self.roots[(project, relative)] = before, mode
                path = self.source / project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(before)
                path.chmod(mode)
            entry["files"].append(item)
        self.install_payload(entry, [item[:4] for item in changes])
        self.series["patches"].append(entry)
        self.write_series()
        return entry

    def inventory(self):
        return build.controls(self.config, self.control)

    def project_report(self, source, projects):
        records = []
        for project, pin in projects.items():
            modified = any((self.source / owner / relative).read_bytes() != raw
                           for (owner, relative), (raw, _) in self.roots.items() if owner == project)
            records.append({**pin, "head": pin["revision"], "actual_url": pin["url"],
                            "clean": not modified, "missing": False,
                            "errors": ["Local changes preserved"] if modified else []})
        return {"projects": records, "project_count": len(records), "all_present": True}

    def fake_apply(self, args):
        directory = Path(args[args.index("-C") + 1])
        payload = Path(args[-1])
        digest = state.sha256(payload.read_bytes())
        entry, changes = self.transitions[digest]
        reverse, check = "--reverse" in args, "--check" in args
        live = directory.is_relative_to(self.source)
        self.assertIn("--whitespace=error-all", args)
        self.assertNotIn("--index", args)
        if live:
            self.assertFalse(reverse, "reverse application is never permitted on live source")
        self.apply_events.append((entry["id"], live, reverse, check))
        for relative, before, after, mode in changes:
            path = directory / relative
            expected, replacement = (after, before) if reverse else (before, after)
            if path.read_bytes() != expected:
                raise subprocess.CalledProcessError(1, args, stderr=b"synthetic context differs")
            if not check:
                path.write_bytes(replacement)
        return SimpleNamespace(stdout=b"", returncode=0)

    def fake_process(self, args, **kwargs):
        self.assertEqual(args[0], "git", "No other real processes")
        self.assertFalse(kwargs.get("shell"))
        env = kwargs["env"]
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(env["GIT_NO_REPLACE_OBJECTS"], "1")
        self.assertNotIn("GIT_INDEX_FILE", env)
        if "init" in args:
            directory = Path(args[-1])
            (directory / ".git").mkdir()
            self.assertFalse(directory.is_relative_to(self.source))
            return SimpleNamespace(stdout=b"", returncode=0)
        if "apply" in args:
            return self.fake_apply(args)
        if "ls-tree" in args:
            directory = Path(args[args.index("-C") + 1])
            owner = directory.relative_to(self.source).as_posix()
            self.assertEqual(args[args.index("ls-tree") + 2], self.frozen[owner]["revision"])
            raw, mode = self.roots[(owner, args[-1])]
            return SimpleNamespace(stdout=f"100{mode:o} blob {state.git_blob_sha1(raw)}\t{args[-1]}\0".encode())
        if "cat-file" in args:
            matched = [raw for raw, _ in self.roots.values() if state.git_blob_sha1(raw) == args[-1]]
            self.assertTrue(matched)
            return SimpleNamespace(stdout=str(len(matched[0])).encode() + b"\n" if "-s" in args else matched[0])
        self.fail(f"Unexpected process: {args}")

    def fake_git(self, args, **kwargs):
        directory = Path(args[args.index("-C") + 1])
        if "apply" in args:
            return self.fake_apply(args)
        owner = directory.relative_to(self.source).as_posix()
        if "status" in args:
            value = self.live_status_override
            if value is None:
                value = "".join(" M " + relative + "\0" for (project, relative), (raw, _) in self.roots.items()
                                if project == owner and (directory / relative).read_bytes() != raw)
            return SimpleNamespace(stdout=value)
        if "ls-tree" in args:
            self.assertEqual(args[args.index("ls-tree") + 2], self.frozen[owner]["revision"])
            raw, mode = self.roots[(owner, args[-1])]
            return SimpleNamespace(stdout=f"100{mode:o} blob {state.git_blob_sha1(raw)}\t{args[-1]}\0")
        if "rev-parse" in args:
            value = {"--show-toplevel": str(directory), "--absolute-git-dir": str(directory / ".git"),
                     "HEAD": self.frozen[owner]["revision"]}[args[-1]]
            return SimpleNamespace(stdout=value)
        if "remote" in args:
            return SimpleNamespace(stdout=self.frozen[owner]["url"])
        if "ls-files" in args:
            value = self.flags_override or "".join("H " + relative + "\0" for project, relative in self.roots if project == owner)
            return SimpleNamespace(stdout=value)
        self.fail(f"Unexpected Git command: {args}")

    def prepare_previous(self):
        self.prepare()
        self.previous = self.root / "previous"
        shutil.copytree(self.control, self.previous)
        self.state_before = (self.paths["report_dir"] / build.STATE).read_bytes()
        self.stack.enter_context(patch.object(build.twrp_workspace, "load_config", return_value=self.config))
        self.apply_events.clear()

    def revise(self):
        return build.revise(self.config, self.paths, "native", self.previous, self.control)


class ChainMetadataTests(ChainFixture):
    def test_existing_twenty_three_entry_prefix_and_payloads_are_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root / build.SERIES).read_bytes()
        series = json.loads(raw)
        self.assertGreaterEqual(len(series["patches"]), 23)
        if len(series["patches"]) == 23:
            self.assertEqual(state.sha256(raw), "cc2fa6b5edf39619be5166d4888ecb8abf108bab6428d3a812df026df18fdd33")
        self.assertEqual(state.sha256(json.dumps(series["patches"][:20], sort_keys=True, separators=(",", ":")).encode()),
                         "dd1a51718b5ebdb4899e05983b668e1b778d1200625907155076b8b7c340295b")
        self.assertEqual(state.sha256(json.dumps(series["patches"][:23], sort_keys=True, separators=(",", ":")).encode()),
                         "8f70a8034f55d4646beac906a3edf9ede454fd9fac512a1c471c90786900d8ed")
        self.assertEqual(state.sha256(json.dumps({k: v for k, v in series.items() if k != "patches"},
                                                sort_keys=True, separators=(",", ":")).encode()),
                         "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22")
        self.assertFalse(state.patch_plan({"patches": series["patches"][:23]})["has_chains"])
        for entry in series["patches"][:23]:
            self.assertEqual(state.sha256((root / entry["patch"]).read_bytes()), entry["patch_sha256"])

    def test_two_explicit_links_retain_root_and_tip(self):
        child = self.append()
        result = state.patch_plan(self.inventory())
        chain = result["projects"][self.project]["files"]["init.rc"]
        self.assertTrue(result["has_chains"])
        self.assertEqual(chain["root"], self.series["patches"][0]["files"][0])
        self.assertEqual(chain["steps"][-1]["item"], child["files"][0])
        self.assertEqual([item["index"] for item in chain["steps"]], [0, 1])

    def test_mixed_successor_and_fresh_file(self):
        first = self.series["patches"][0]
        self.append([("init.rc", self.after, self.after + b"more\n", 0o644, first["id"]),
                     ("Android.mk", b"old\n", b"new\n", 0o644, None)])
        files = state.patch_plan(self.inventory())["projects"][self.project]["files"]
        self.assertEqual([len(files[path]["steps"]) for path in ("init.rc", "Android.mk")], [2, 1])

    def test_multiple_append_requires_immediate_predecessor(self):
        second, third = self.append(), self.append()
        self.inventory()
        third["files"][0]["predecessor_patch_id"] = self.series["patches"][0]["id"]
        self.write_series()
        with self.assertRaisesRegex(ValueError, "immediate predecessor"):
            self.inventory()

    def test_implicit_and_malformed_predecessors_stay_rejected(self):
        child = self.append()
        for value in (None, "", 1, True, [], {}, "missing", child["id"], "future"):
            child["files"][0]["predecessor_patch_id"] = value
            self.write_series()
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Overlapping patch files"):
                self.inventory()
        del child["files"][0]["predecessor_patch_id"]
        self.write_series()
        with self.assertRaisesRegex(ValueError, "Overlapping patch files"):
            self.inventory()

    def test_first_touch_cannot_claim_another_file_or_owner(self):
        for value in (None, "", self.series["patches"][0]["id"], "other-owner"):
            changed = copy.deepcopy(self.series["patches"])
            changed[0]["files"][0]["predecessor_patch_id"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "First patch touch"):
                state.patch_plan({"patches": changed})

    def test_duplicate_path_in_one_patch(self):
        self.series["patches"][0]["files"].append(copy.deepcopy(self.series["patches"][0]["files"][0]))
        self.write_series()
        with self.assertRaisesRegex(ValueError, "Duplicate path"):
            self.inventory()

    def test_each_predecessor_identity_component_is_required(self):
        child = self.append()
        original = copy.deepcopy(child["files"][0])
        for field, value in (("before_sha256", "0" * 64), ("before_size_bytes", 123), ("before_git_blob", "0" * 40)):
            child["files"][0] = {**original, field: value}
            self.write_series()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "discontinuous"):
                self.inventory()

    def test_all_chain_records_need_blob_ids(self):
        self.append()
        original = copy.deepcopy(self.series)
        for index in (0, 1):
            for phase in ("before", "after"):
                self.series = copy.deepcopy(original)
                del self.series["patches"][index]["files"][0][phase + "_git_blob"]
                self.write_series()
                with self.subTest(index=index, phase=phase), self.assertRaisesRegex(ValueError, "complete Git blob"):
                    self.inventory()

    def test_net_revert_and_changed_base_rejected(self):
        self.append([("init.rc", self.after, self.before, 0o644, self.series["patches"][0]["id"])])
        with self.assertRaisesRegex(ValueError, "original root"):
            self.inventory()
        self.series["patches"][1]["base_commit"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "one full pinned"):
            state.patch_plan({"patches": self.series["patches"]})

    def test_full_matching_git_indexes_are_required(self):
        child = self.append()
        for entry in self.series["patches"]:
            payload = self.control / entry["patch"]
            original = payload.read_bytes()
            for replacement in (b"index 1234567..abcdef0 100644", b"index " + b"0" * 40 + b".." + b"1" * 40 + b" 100644"):
                lines = original.splitlines(keepends=True)
                lines[1] = replacement + b"\n"
                payload.write_bytes(b"".join(lines))
                entry["patch_sha256"] = state.sha256(payload.read_bytes())
                self.write_series()
                with self.subTest(entry=entry["id"], replacement=replacement), self.assertRaisesRegex(ValueError, "full matching Git index"):
                    self.inventory()
            payload.write_bytes(original)
            entry["patch_sha256"] = state.sha256(original)
            self.write_series()

    def test_orphan_wrapper_cannot_authorize_a_child(self):
        child = self.append()
        self.source_file.write_bytes(self.after)
        for phase in ("before", "after"):
            with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, "First patch touch"):
                build.verify_patch_files(self.source, {"patches": [child]}, phase)
        self.assertFalse(self.apply_events)

    def test_exact_old_prefix_and_raw_series_identity_remain_required(self):
        old = self.inventory()
        self.append()
        new = self.inventory()
        result = state.validate_patch_extension(old, new)
        self.assertEqual(result["previous_patch_count"], 1)
        self.assertEqual(result["complete_patches"], new["patches"])
        for mutation in ("record", "order", "delete"):
            candidate = copy.deepcopy(new)
            if mutation == "record": candidate["patches"][0]["reason"] = "changed"
            elif mutation == "order": candidate["patches"].reverse()
            else: candidate["patches"] = candidate["patches"][1:]
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "unchanged prefix"):
                state.validate_patch_extension(old, candidate)
        with self.assertRaisesRegex(ValueError, "exact existing patch queue"):
            state.validate_patch_extension(old, {**old, "series_sha256": "f" * 64})


class ChainRehearsalTests(ChainFixture):
    def test_rehearsal_rejects_declared_attributes_before_any_process(self):
        self.append([("init.rc", self.after, self.after + b"more\n", 0o644, self.series["patches"][0]["id"]),
                     ("subdir/.gitattributes", b"*.rc text\n", b"*.rc -whitespace\n", 0o644, None)])
        with self.assertRaisesRegex(ValueError, "does not admit Git attribute files"):
            build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        self.process_mock.assert_not_called()
        self.assertEqual(self.source_file.read_bytes(), self.before)

    def test_ordered_forward_and_reverse_rehearsal_preserves_live_source(self):
        self.append()
        reviewed = self.inventory()
        report = build.rehearse_chain(self.source, reviewed, self.control, 0)
        self.assertTrue(report["forward_and_reverse_verified"])
        self.assertEqual(self.source_file.read_bytes(), self.before)
        self.assertFalse(any(event[1] for event in self.apply_events))
        applied = [(identifier, reverse) for identifier, _, reverse, check in self.apply_events if not check]
        self.assertEqual(applied, [(reviewed["patches"][0]["id"], False), (reviewed["patches"][1]["id"], False),
                                  (reviewed["patches"][1]["id"], True), (reviewed["patches"][0]["id"], True)])

    def test_pinned_root_bytes_never_use_mutable_head_or_live_index(self):
        self.append()
        build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        queries = [call.args[0] for call in self.process_mock.call_args_list if "cat-file" in call.args[0]]
        self.assertTrue(queries)
        self.assertTrue(all(args[-1] == state.git_blob_sha1(self.before) for args in queries))
        self.assertFalse(any("HEAD" in call.args[0] or "--index" in call.args[0] for call in self.process_mock.call_args_list))

    def test_explicit_old_boundary_is_checked_not_inferred(self):
        self.prepare_previous()
        self.append()
        reviewed = self.inventory()
        build.rehearse_chain(self.source, reviewed, self.control, 1)
        self.assertEqual(self.source_file.read_bytes(), self.after)
        for boundary in (0, 2, -1, 3, None, True):
            with self.subTest(boundary=boundary), self.assertRaises(ValueError):
                build.rehearse_chain(self.source, reviewed, self.control, boundary)

    def test_fresh_prepare_never_adopts_matching_chain_tip(self):
        self.append()
        for raw in (self.after, self.after + b"next\n"):
            self.source_file.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.prepare()
            self.assertFalse((self.source / build.TARGET).exists())
            self.assertFalse((self.paths["report_dir"] / build.STATE).exists())
        self.assertFalse(self.apply_events)

    def test_noncanonical_modes_fail_before_rehearsal(self):
        self.append()
        for mode in (0o600, 0o664, 0o744, 0o755):
            self.source_file.chmod(mode)
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "mode differs"):
                build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        self.assertFalse(self.apply_events)

    def test_root_blob_corruption_is_rejected(self):
        self.append()
        original = self.fake_process
        def corrupt(args, **kwargs):
            value = original(args, **kwargs)
            if "cat-file" in args and "blob" in args:
                value.stdout = b"forged\n"
            return value
        self.process_mock.side_effect = corrupt
        with self.assertRaisesRegex(ValueError, "immutable original Git blob"):
            build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        self.assertFalse(self.apply_events)

    def test_reverse_failure_precedes_all_live_source_or_target_mutation(self):
        self.append()
        original = self.fake_process
        def fail_reverse(args, **kwargs):
            if "--reverse" in args:
                raise subprocess.CalledProcessError(1, args, stderr=b"original whitespace rejected")
            return original(args, **kwargs)
        self.process_mock.side_effect = fail_reverse
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertEqual(self.source_file.read_bytes(), self.before)
        self.assertFalse((self.source / build.TARGET).exists())
        self.assertFalse((self.paths["report_dir"] / build.STATE).exists())
        self.assertFalse(any(event[1] for event in self.apply_events))

    def assert_legacy_reverse_mode_failure(self, *, revise):
        before, after = b"legacy before\n", b"legacy after\n"
        legacy = self.append([("legacy.sh", before, after, 0o755, None)])
        payload = self.control / legacy["patch"]
        previous_hash = legacy["patch_sha256"]
        # Historical single-touch hints can disagree with the pinned mode;
        # full chain-header validation still applies to the separate init chain.
        payload.write_bytes(payload.read_bytes().replace(b" 100755\n", b" 100644\n"))
        legacy["files"][0]["mode"] = "100644"
        legacy["patch_sha256"] = state.sha256(payload.read_bytes())
        self.transitions[legacy["patch_sha256"]] = self.transitions.pop(previous_hash)
        self.write_series()
        if revise:
            self.prepare_previous()
            (self.control / build.TARGET_SOURCE / "device.mk").write_text("# proposed revision\n")
        self.append([("init.rc", self.after, self.after + b"next\n", 0o644,
                      self.series["patches"][0]["id"])])
        files = state.patch_plan(self.inventory())["projects"][self.project]["files"]
        self.assertEqual(len(files["legacy.sh"]["steps"]), 1)
        self.assertEqual(len(files["init.rc"]["steps"]), 2)

        def snapshot():
            result = {}
            for path in self.root.rglob("*"):
                name = path.relative_to(self.root).as_posix()
                if path.is_symlink():
                    result[name] = ("symlink", str(path.readlink()))
                elif path.is_file():
                    result[name] = (path.stat().st_mode & 0o777, path.read_bytes())
                else:
                    result[name] = ("directory", path.stat().st_mode & 0o777)
            return result

        unchanged = snapshot()
        recreated = []
        original = self.fake_process
        def reverse_mode_bug(args, **kwargs):
            result = original(args, **kwargs)
            if ("apply" in args and "--reverse" in args and "--check" not in args
                    and state.sha256(Path(args[-1]).read_bytes()) == legacy["patch_sha256"]):
                directory = Path(args[args.index("-C") + 1])
                self.assertFalse(directory.is_relative_to(self.source))
                path = directory / "legacy.sh"
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(path.stat().st_mode & 0o777, 0o755)
                # Git 2.43 can return success after recreating correct bytes at
                # the wrong mode. An in-place write alone cannot model this.
                path.unlink()
                path.write_bytes(before)
                path.chmod(0o644)
                self.assertEqual(result.returncode, 0)
                recreated.append((path.read_bytes(), path.stat().st_mode & 0o777))
            return result
        self.process_mock.side_effect = reverse_mode_bug
        with self.assertRaisesRegex(ValueError, r"File changed.*legacy\.sh"):
            self.revise() if revise else self.prepare()
        self.assertEqual(recreated, [(before, 0o644)])
        self.assertFalse(any(event[1] for event in self.apply_events))
        # Includes target, output alias, receipt, and preparation/revision
        # archive paths: nothing outside the discarded scratch tree changes.
        self.assertEqual(snapshot(), unchanged)
        if revise:
            self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
        else:
            self.assertFalse((self.paths["report_dir"] / build.STATE).exists())

    def test_zero_exit_reverse_mode_change_blocks_preparation(self):
        self.assert_legacy_reverse_mode_failure(revise=False)

    def test_zero_exit_reverse_mode_change_blocks_revision(self):
        self.assert_legacy_reverse_mode_failure(revise=True)

    def test_hostile_git_environment_is_not_inherited(self):
        self.append()
        with patch.dict(os.environ, {"GIT_INDEX_FILE": "/unsafe", "GIT_CONFIG_COUNT": "1", "GIT_DIR": "/unsafe",
                                     "GIT_WORK_TREE": "/unsafe", "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/unsafe"}):
            build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        for call in self.process_mock.call_args_list:
            for key in ("GIT_INDEX_FILE", "GIT_CONFIG_COUNT", "GIT_DIR", "GIT_WORK_TREE", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
                self.assertNotIn(key, call.kwargs["env"])

    def test_scratch_extra_path_is_detected(self):
        self.append()
        original = self.fake_process
        def extra(args, **kwargs):
            result = original(args, **kwargs)
            if "apply" in args and "--check" not in args:
                directory = Path(args[args.index("-C") + 1])
                (directory / "undeclared.bp").write_text("wrong\n")
            return result
        self.process_mock.side_effect = extra
        with self.assertRaisesRegex(ValueError, "undeclared paths"):
            build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        self.assertEqual(self.source_file.read_bytes(), self.before)

    def test_scratch_zero_exit_with_wrong_postimage_is_rejected(self):
        self.append()
        original = self.fake_process
        def wrong(args, **kwargs):
            result = original(args, **kwargs)
            if "apply" in args and "--check" not in args:
                (Path(args[args.index("-C") + 1]) / "init.rc").write_bytes(b"wrong\n")
            return result
        self.process_mock.side_effect = wrong
        with self.assertRaisesRegex(ValueError, "File changed"):
            build.rehearse_chain(self.source, self.inventory(), self.control, 0)
        self.assertEqual(self.source_file.read_bytes(), self.before)

    def test_multiple_owners_keep_global_queue_order_and_independent_roots(self):
        other = "system/example"
        self.frozen[other] = {"name": "system_example", "path": other, "revision": "d" * 40,
                              "remote": "origin", "url": "https://example.org/system/example"}
        second = self.append([("other.rc", b"a\n", b"b\n", 0o644, None)], project=other)
        third = self.append(project=self.project)
        fourth = self.append(project=other)
        reviewed = self.inventory()
        build.rehearse_chain(self.source, reviewed, self.control, 0)
        forwards = [identifier for identifier, live, reverse, check in self.apply_events if not reverse and not check]
        self.assertEqual(forwards, [self.series["patches"][0]["id"], second["id"], third["id"], fourth["id"]])

    def test_composed_fixture_preserves_resource_and_security_properties(self):
        root = b"recovery: true\nresource: absent\nauth: required\nselinux: enforcing\nlegacy-tool: yes\n"
        first_tip = root.replace(b"resource: absent", b"resource: mdpi")
        final_tip = first_tip.replace(b"legacy-tool: yes", b"legacy-tool: no")
        self.before, self.after = root, first_tip
        self.roots[(self.project, "init.rc")] = root, 0o644
        self.source_file.write_bytes(root)
        first = self.series["patches"][0]
        first["files"][0].update(before_sha256=state.sha256(root), before_size_bytes=len(root),
                                 before_git_blob=state.git_blob_sha1(root), after_sha256=state.sha256(first_tip),
                                 after_size_bytes=len(first_tip), after_git_blob=state.git_blob_sha1(first_tip))
        self.install_payload(first, [("init.rc", root, first_tip, 0o644)])
        self.append([("init.rc", first_tip, final_tip, 0o644, first["id"])])
        self.prepare()
        result = self.source_file.read_bytes()
        self.assertEqual(result, final_tip)
        for expected in (b"resource: mdpi", b"auth: required", b"selinux: enforcing", b"recovery: true"):
            self.assertIn(expected, result)

    def test_pinned_index_mode_must_match_full_chain_headers(self):
        self.append()
        first = self.series["patches"][0]
        path = self.control / first["patch"]
        path.write_bytes(path.read_bytes().replace(b" 100644\n", b" 100755\n"))
        first["patch_sha256"] = state.sha256(path.read_bytes())
        self.write_series()
        with self.assertRaisesRegex(ValueError, "pinned mode"):
            build.rehearse_chain(self.source, self.inventory(), self.control, 0)


class ChainTransitionTests(ChainFixture):
    def test_existing_active_chain_can_extend_without_reapplying_its_prefix(self):
        self.append()
        self.prepare_previous()
        child = self.append()
        result = self.revise()
        live = [identifier for identifier, is_live, reverse, check in self.apply_events if is_live]
        self.assertEqual(live, [child["id"]])
        self.assertEqual(result["applied_patch_ids"], [child["id"]])
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\nnext\n")

    def test_active_fetch_context_trusts_old_chain_not_proposed_successor(self):
        self.append()
        self.prepare_previous()
        self.append()
        context = {"config": self.config, "paths": self.paths, "frozen": self.frozen,
                   "source": self.source, "reviewed": None}
        result = dependencies.active_patch_context(self.control, self.previous, context)
        self.assertEqual(len(result["controls"]["patches"]), 2)
        self.assertEqual(result["build_state_sha256"], state.sha256(self.state_before))
        self.source_file.write_bytes(self.after + b"next\nnext\n")
        with self.assertRaises(ValueError):
            dependencies.active_patch_context(self.control, self.previous, context)
        self.assertFalse(any(event[1] for event in self.apply_events))
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_prepare_chain_uses_step_archives_and_final_unique_status(self):
        self.append()
        result = self.prepare()
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertEqual(result["applied_patch_ids"], [entry["id"] for entry in self.series["patches"]])
        archive = Path(result["preparation_archive"])
        self.assertEqual((archive / "source-before/bootable/recovery/init.rc").read_bytes(), self.before)
        self.assertEqual((archive / "steps/0000/source-after/bootable/recovery/init.rc").read_bytes(), self.after)
        self.assertEqual((archive / "steps/0001/source-after/bootable/recovery/init.rc").read_bytes(), self.after + b"next\n")
        self.assertTrue((archive / "steps/0001/complete.json").exists())
        self.assertFalse((archive / "source-after").exists())
        self.assertTrue(self.check()["prepared_sources_verified"])
        self.assertFalse(self.check()["flash_admitted"])

    def test_revision_appends_multiple_links_preserving_old_receipt(self):
        self.prepare_previous()
        second, third = self.append(), self.append()
        result = self.revise()
        self.assertTrue(result["revision_committed"])
        self.assertEqual(result["applied_patch_ids"], [second["id"], third["id"]])
        archive = Path(result["revision_archive"])
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.state_before)
        self.assertEqual((archive / "source-before/bootable/recovery/init.rc").read_bytes(), self.after)
        self.assertEqual((archive / "steps/0001/source-after/bootable/recovery/init.rc").read_bytes(), self.after + b"next\n")
        self.assertEqual((archive / "steps/0002/source-after/bootable/recovery/init.rc").read_bytes(), self.after + b"next\nnext\n")
        self.assertFalse(result["build_for_this_revision_verified"])
        self.assertFalse(result["flash_admitted"])

    def test_completed_retry_has_no_apply_or_reverse(self):
        self.prepare_previous()
        self.append()
        self.revise()
        self.apply_events.clear()
        result = self.revise()
        self.assertTrue(result["already_current"])
        self.assertFalse(self.apply_events)

    def test_mixed_chain_fresh_executable_keeps_canonical_mode(self):
        self.prepare_previous()
        self.append([("init.rc", self.after, self.after + b"more\n", 0o644, self.series["patches"][0]["id"]),
                     ("script.sh", b"old\n", b"new\n", 0o755, None)])
        result = self.revise()
        self.assertEqual((self.source / self.project / "script.sh").stat().st_mode & 0o777, 0o755)
        archive = Path(result["revision_archive"])
        self.assertEqual((archive / "source-before/bootable/recovery/script.sh").stat().st_mode & 0o777, 0o644)

    def test_intent_exists_before_live_apply_completion_only_after_verify(self):
        self.prepare_previous()
        child = self.append()
        original = self.fake_git
        def inspect(args, **kwargs):
            if "apply" in args:
                archive = next((self.paths["report_dir"] / "build-revisions").iterdir())
                intent = json.loads((archive / "steps/0001/intent.json").read_text())
                self.assertEqual(intent["patch_id"], child["id"])
                self.assertEqual(intent["status"], "attempted-not-yet-verified")
                self.assertFalse((archive / "steps/0001/complete.json").exists())
            return original(args, **kwargs)
        self.run_mock.side_effect = inspect
        self.revise()

    def test_partial_apply_preserved_and_retry_refused(self):
        self.prepare_previous()
        second, third = self.append(), self.append()
        original = self.fake_git
        def fail_third(args, **kwargs):
            if "apply" in args and state.sha256(Path(args[-1]).read_bytes()) == third["patch_sha256"]:
                raise subprocess.CalledProcessError(1, args)
            return original(args, **kwargs)
        self.run_mock.side_effect = fail_third
        with self.assertRaises(subprocess.CalledProcessError):
            self.revise()
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
        failure = json.loads(next(self.paths["report_dir"].glob("revise-failed-*.json")).read_text())
        self.assertEqual(failure["attempted_patch_ids"], [second["id"], third["id"]])
        self.assertEqual(failure["applied_patch_ids"], [second["id"]])
        self.run_mock.side_effect = original
        self.apply_events.clear()
        with self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(self.apply_events)

    def test_postimage_corruption_preserves_old_receipt_and_incomplete_intent(self):
        self.prepare_previous()
        self.append()
        original = self.fake_git
        def corrupt(args, **kwargs):
            result = original(args, **kwargs)
            if "apply" in args:
                self.source_file.write_bytes(b"corrupt\n")
            return result
        self.run_mock.side_effect = corrupt
        with self.assertRaises(ValueError):
            self.revise()
        archive = next((self.paths["report_dir"] / "build-revisions").iterdir())
        self.assertTrue((archive / "steps/0001/intent.json").exists())
        self.assertFalse((archive / "steps/0001/complete.json").exists())
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
        self.assertEqual(self.source_file.read_bytes(), b"corrupt\n")

    def test_preimage_changed_after_rehearsal_stops_live_apply(self):
        self.prepare_previous()
        self.append()
        original = build.twrp_workspace.record_action
        def change(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start": self.source_file.write_bytes(b"other\n")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=change), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_receipt_change_stops_live_apply(self):
        self.prepare_previous()
        self.append()
        original = build.twrp_workspace.record_action
        def change(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start":
                (paths["report_dir"] / build.STATE).write_bytes(b"replaced receipt\n")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=change), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))

    def control_drift(self, previous):
        self.prepare_previous()
        self.append()
        original = build.twrp_workspace.record_action
        def change(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start":
                root = self.previous if previous else self.control
                (root / build.TARGET_SOURCE / "device.mk").write_text("# changed bundle\n")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=change), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_previous_bundle_change_stops_live_apply(self):
        self.control_drift(True)

    def test_new_bundle_change_stops_live_apply(self):
        self.control_drift(False)

    def test_archive_parent_symlink_is_rejected_before_creating_outside(self):
        self.append()
        outside = self.root / "outside-archive"
        outside.mkdir()
        (self.paths["report_dir"] / "build-preparations").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.source_file.read_bytes(), self.before)
        self.assertFalse(any(event[1] for event in self.apply_events))

    def test_drift_of_completed_step_evidence_blocks_next_live_step(self):
        self.prepare_previous()
        self.append()
        third = self.append()
        original = build.write_new_file
        def tamper(root, relative, data):
            result = original(root, relative, data)
            if relative == "steps/0002/intent.json":
                (root / "steps/0001/source-after/bootable/recovery/init.rc").write_bytes(b"changed evidence\n")
            return result
        with patch.object(build, "write_new_file", side_effect=tamper), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(identifier == third["id"] and live for identifier, live, _, _ in self.apply_events))
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_archive_plan_tampering_is_rejected_before_live_apply(self):
        self.prepare_previous()
        self.append()
        original = build.twrp_workspace.record_action
        def tamper(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start":
                (Path(report["revision_archive"]) / "chain-plan.json").write_text("{}\n")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=tamper), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))

    def test_late_archived_payload_drift_prevents_receipt_commit(self):
        self.prepare_previous()
        self.append()
        (self.control / build.TARGET_SOURCE / "device.mk").write_text("# revised target\n")
        original = build.replace_target_file
        def tamper(target, relative, expected, data, revision):
            result = original(target, relative, expected, data, revision)
            archive = self.paths["report_dir"] / "build-revisions" / revision
            (archive / "patches/0000.patch").write_text("tampered\n")
            return result
        with patch.object(build, "replace_target_file", side_effect=tamper), self.assertRaises(ValueError):
            self.revise()
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_intent_write_failure_does_not_apply_source(self):
        self.prepare_previous()
        self.append()
        original = build.write_new_file
        def full(root, relative, data):
            if relative.endswith("/intent.json"): raise OSError("disk full")
            return original(root, relative, data)
        with patch.object(build, "write_new_file", side_effect=full), self.assertRaises(OSError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_kill_before_completion_leaves_attempt_uncertain_and_no_auto_resume(self):
        self.prepare_previous()
        self.append()
        original = build.write_new_file
        def killed(root, relative, data):
            if relative.endswith("/complete.json"): raise OSError("interrupted")
            return original(root, relative, data)
        with patch.object(build, "write_new_file", side_effect=killed), self.assertRaises(OSError):
            self.revise()
        self.assertEqual(self.source_file.read_bytes(), self.after + b"next\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)
        self.apply_events.clear()
        with self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(self.apply_events)

    def test_last_preimage_check_occurs_after_intent_write(self):
        self.prepare_previous()
        self.append()
        original = build.write_new_file
        def drift(root, relative, data):
            result = original(root, relative, data)
            if relative.endswith("/intent.json"):
                self.source_file.write_bytes(b"other writer\n")
            return result
        with patch.object(build, "write_new_file", side_effect=drift), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))
        self.assertEqual(self.source_file.read_bytes(), b"other writer\n")

    def test_old_receipt_cannot_authorize_proposed_child_bytes(self):
        self.prepare_previous()
        self.append()
        self.source_file.write_bytes(self.after + b"next\n")
        with self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(self.apply_events)
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_unrelated_modified_owner_path_is_not_hidden_by_chain(self):
        self.prepare_previous()
        self.append()
        original = self.fake_git
        def extra(args, **kwargs):
            result = original(args, **kwargs)
            if "apply" in args:
                self.live_status_override = " M init.rc\0?? undeclared.rc\0"
            return result
        self.run_mock.side_effect = extra
        with self.assertRaisesRegex(ValueError, "exact unstaged patch closure"):
            self.revise()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_base_identity_errors_remain_visible_after_chain(self):
        self.prepare_previous()
        self.append()
        original = self.project_report
        def dirty(source, projects):
            result = original(source, projects)
            if self.source_file.read_bytes() != self.after:
                result["projects"][0]["errors"].append("HEAD differs from frozen project revision")
            return result
        self.projects_mock.side_effect = dirty
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            self.revise()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.state_before)

    def test_archive_backup_tampering_stops_live_apply(self):
        self.prepare_previous()
        self.append()
        original = build.twrp_workspace.record_action
        def tamper(config, paths, action, report):
            result = original(config, paths, action, report)
            if action == "revise-start":
                (Path(report["revision_archive"]) / "source-before/bootable/recovery/init.rc").write_bytes(b"bad\n")
            return result
        with patch.object(build.twrp_workspace, "record_action", side_effect=tamper), self.assertRaises(ValueError):
            self.revise()
        self.assertFalse(any(event[1] for event in self.apply_events))

    def test_numeric_archives_do_not_use_unusual_patch_ids(self):
        self.prepare_previous()
        child = self.append(identifier="../../untrusted-id")
        result = self.revise()
        archive = Path(result["revision_archive"])
        self.assertTrue((archive / "steps/0001/intent.json").exists())
        self.assertFalse((self.paths["report_dir"] / "untrusted-id").exists())
        self.assertEqual(result["applied_patch_ids"], [child["id"]])

    def test_completion_history_failure_preserves_committed_result(self):
        self.prepare_previous()
        self.append()
        original = build.twrp_workspace.record_action
        def fail(config, paths, action, report):
            if action == "revise-complete": raise OSError("history full")
            return original(config, paths, action, report)
        with patch.object(build.twrp_workspace, "record_action", side_effect=fail):
            result = self.revise()
        self.assertTrue(result["revision_committed"])
        self.assertFalse(result["completion_report_written"])
        self.assertTrue(self.revise()["already_current"])

    def test_chain_supplement_unique_status_and_hidden_flags(self):
        self.append()
        self.source_file.write_bytes(self.after + b"next\n")
        (self.source / self.project / ".git").mkdir()
        project = {"path": self.project, "commit": self.base, "url": self.frozen[self.project]["url"]}
        for entry in self.series["patches"]:
            entry["repository"] = project["url"]
        report = dependencies.verify_project(project, self.source / self.project,
                                             patches=self.series["patches"], phase="after")
        self.assertTrue(report["exact_patch_state_verified"])
        for status in ("M  init.rc\0", " M init.rc\0 M init.rc\0", " M init.rc\0!! ignored\0", " M init.rc"):
            self.live_status_override = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                dependencies.verify_project(project, self.source / self.project, patches=self.series["patches"], phase="after")
        self.live_status_override = None
        for flags in ("h init.rc\0", "S init.rc\0", "s init.rc\0", "M init.rc\0"):
            self.flags_override = flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                dependencies.verify_project(project, self.source / self.project, patches=self.series["patches"], phase="after")


if __name__ == "__main__":
    unittest.main()
