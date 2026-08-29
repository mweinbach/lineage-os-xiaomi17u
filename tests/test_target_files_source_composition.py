"""Offline source-closure and exact replay tests; no Android checkout required."""

import builtins
import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import target_files_metadata as metadata
from scripts import target_files_source_composition as source


ROOT = Path(__file__).resolve().parents[1]
CORE = metadata.CORE
PATCH = "patches/evolution/fixture-source.patch"
BEFORE = b"header\nold\nfooter\n"
AFTER = b"header\nnew\nfooter\n"
PATCH_BYTES = (
    b"diff --git a/core/Makefile b/core/Makefile\n"
    b"--- a/core/Makefile\n+++ b/core/Makefile\n"
    b"@@ -1,3 +1,3 @@\n header\n-old\n+new\n footer\n"
)
MACRO = b"define readonly-variables\n# inert fixture definition\nendef\n"


class PublicCompositionTests(unittest.TestCase):
    def test_new_composition_has_exact_order_and_complete_source_closure(self):
        result = source.compose_sources(ROOT)
        self.assertEqual(7, len(result["ordered_patches"]))
        self.assertEqual(8, len(result["contracts"]))
        self.assertEqual(source.CONTRACT, result["contracts"][-1]["path"])
        self.assertEqual(10, len(result["initial_source_files"]))
        self.assertEqual(10, len(result["final_source_files"]))
        self.assertEqual(result["ordered_patches"], [row["patch"] for row in result["source_transitions"]])
        self.assertFalse(result["patches_applied_by_this_tool"])
        self.assertFalse(result["whole_source_tree_verified"])

    def test_original_metadata_composition_serialization_is_unchanged(self):
        self.assertEqual({"sha256": "6cc3a2bc48603a8eb8b15082252350dc550c0dfc669af24d96e6b4e1a317ad0f",
                          "size_bytes": 3971}, metadata.identity(metadata.encoded(metadata.compose_sources(ROOT))))

    def test_adapter_bootstrap_failures_use_the_declared_consumer_exception(self):
        real_import = builtins.__import__
        def failed_adapter(name, globals=None, locals=None, fromlist=(), level=0):
            if "target_files_metadata_combined" in fromlist:
                raise ValueError("fixture: frozen base metadata bytes changed")
            return real_import(name, globals, locals, fromlist, level)
        with mock.patch("builtins.__import__", side_effect=failed_adapter):
            with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "frozen base metadata"):
                source.compose_sources(ROOT)


class ExactPatchTests(unittest.TestCase):
    def test_complete_patch_result_is_exact(self):
        self.assertEqual(AFTER, source._apply_exact_patch(BEFORE, PATCH_BYTES, CORE))

    def test_reviewed_mail_prefix_and_index_do_not_change_hunk_semantics(self):
        mail = b"From: offline fixture\nSubject: patch\n\n" + PATCH_BYTES
        indexed = PATCH_BYTES.replace(b"--- a/", b"index 1111111..2222222 100644\n--- a/", 1)
        for patch in (mail, indexed):
            with self.subTest(patch=patch):
                self.assertEqual(AFTER, source._apply_exact_patch(BEFORE, patch, CORE))

    def test_an_offset_cannot_replace_exact_preimage_verification(self):
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "offsets and fuzz"):
            source._apply_exact_patch(b"extra\n" + BEFORE, PATCH_BYTES, CORE)

    def test_context_mismatch_is_not_fuzzed(self):
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "preimage"):
            source._apply_exact_patch(BEFORE.replace(b"header", b"different"), PATCH_BYTES, CORE)

    def test_declared_old_and_new_counts_are_enforced(self):
        for old in (b"@@ -1,2 +1,3 @@", b"@@ -1,3 +1,2 @@"):
            with self.subTest(header=old), self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "counts"):
                source._apply_exact_patch(BEFORE, PATCH_BYTES.replace(b"@@ -1,3 +1,3 @@", old), CORE)

    def test_output_position_is_not_adjusted(self):
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "output position"):
            source._apply_exact_patch(BEFORE, PATCH_BYTES.replace(b"+1,3 @@", b"+2,3 @@"), CORE)

    def test_an_extra_file_header_is_rejected(self):
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "one declared source"):
            source._apply_exact_patch(BEFORE, PATCH_BYTES + b"--- a/other\n+++ b/other\n", CORE)

    def test_wrong_file_or_project_is_rejected(self):
        for path in ("build/make/core/product.mk", "system/core/Makefile", "build/make/../other"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                source._apply_exact_patch(BEFORE, PATCH_BYTES, path)

    def test_truncated_inputs_are_rejected(self):
        for before, patch in ((BEFORE[:-1], PATCH_BYTES), (BEFORE, PATCH_BYTES[:-1])):
            with self.subTest(before=before, patch=patch), self.assertRaises(ValueError):
                source._apply_exact_patch(before, patch, CORE)

    def test_overlapping_hunks_are_rejected(self):
        second_hunk = PATCH_BYTES[PATCH_BYTES.index(b"@@ "):]
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "preimage"):
            source._apply_exact_patch(BEFORE, PATCH_BYTES + second_hunk, CORE)

    def test_two_ordered_hunks_preserve_unmodified_bytes(self):
        before = b"one\ntwo\nthree\nfour\nfive\n"
        patch = (b"--- a/core/Makefile\n+++ b/core/Makefile\n"
                 b"@@ -1,1 +1,2 @@\n-one\n+ONE\n+inserted\n"
                 b"@@ -4,1 +5,1 @@\n-four\n+FOUR\n")
        self.assertEqual(b"ONE\ninserted\ntwo\nthree\nFOUR\nfive\n",
                         source._apply_exact_patch(before, patch, CORE))


class SourceClosureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.controls, self.before, self.final = [self.root / name for name in ("controls", "before", "final")]
        record = metadata._json((ROOT / source.CONTRACT).read_bytes())
        paths = [row["path"] for row in record["final_source_files"]]
        self.initial = {path: ("# inert source fixture: " + path + "\n").encode() for path in paths}
        self.initial.update({CORE: BEFORE, source.PRODUCT: MACRO})
        self.last = {**self.initial, CORE: AFTER}
        self.patch = {"path": PATCH, **metadata.identity(PATCH_BYTES)}
        self.transition = {"patch": self.patch, "path": CORE,
                           "before": metadata.identity(BEFORE), "after": metadata.identity(AFTER)}
        self.descriptor = {
            "readonly_macro": {"name": "readonly-variables", "source": source.PRODUCT,
                               "body_sha256": metadata.identity(MACRO)["sha256"]},
            "scope": copy.deepcopy(record["scope"]),
            "readonly_upgrade": {"initial_source_files": self.rows(self.initial),
                                 "source_transitions": [self.transition]},
        }
        self.composition = {"project": copy.deepcopy(metadata.PROJECT),
                            "contracts": [], "initial_source_files": self.rows(self.initial),
                            "final_source_files": self.rows(self.last),
                            "source_transitions": [self.transition]}
        self.save_descriptor()
        self.write(self.controls / PATCH, PATCH_BYTES)
        for name, files in ((self.before, self.initial), (self.final, self.last)):
            for path, raw in files.items():
                self.write(name / path, raw)
        self.composer = self.enterContext(mock.patch.object(source, "compose_sources", return_value=self.composition))
        for name in ("subprocess.Popen", "subprocess.run", "socket.socket"):
            self.enterContext(mock.patch(name, side_effect=AssertionError("offline test: " + name)))

    @staticmethod
    def rows(files):
        return [{"path": path, **metadata.identity(raw)} for path, raw in sorted(files.items())]

    @staticmethod
    def write(path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def save_descriptor(self):
        raw = metadata.encoded(self.descriptor)
        self.write(self.controls / source.CONTRACT, raw)
        self.composition["contracts"] = [{"path": source.CONTRACT, **metadata.identity(raw)}]

    def check(self, **options):
        return source.check_source(self.final, root=self.controls, **options)

    def test_all_ten_complete_source_files_are_checked_without_build_claim(self):
        result = self.check()
        self.assertEqual(10, len(result["source_files"]))
        self.assertFalse(result["complete_patch_replay_verified"])
        self.assertFalse(result["whole_source_tree_verified"])
        self.assertFalse(result["scope"]["native_vintf_verified"])
        self.assertFalse(result["scope"]["complete_rom_admitted"])

    def test_every_missing_final_source_is_rejected(self):
        for path, raw in self.last.items():
            with self.subTest(path=path):
                (self.final / path).unlink()
                with self.assertRaises((ValueError, OSError)):
                    self.check()
                self.write(self.final / path, raw)

    def test_changed_final_source_is_rejected(self):
        (self.final / CORE).write_bytes(AFTER + b"extra\n")
        with self.assertRaises(ValueError):
            self.check()

    def test_final_source_symlink_is_rejected(self):
        path = self.final / CORE
        target = self.root / "actual-source"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises((ValueError, OSError)):
            self.check()

    def test_macro_has_a_separate_bound_even_when_file_hash_is_updated(self):
        self.last[source.PRODUCT] = MACRO.replace(b"inert", b"changed")
        self.write(self.final / source.PRODUCT, self.last[source.PRODUCT])
        self.composition["final_source_files"] = self.rows(self.last)
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "macro definition"):
            self.check()

    def test_duplicate_macro_definition_is_rejected(self):
        self.last[source.PRODUCT] = MACRO * 2
        self.write(self.final / source.PRODUCT, self.last[source.PRODUCT])
        self.composition["final_source_files"] = self.rows(self.last)
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "macro definition"):
            self.check()

    def test_explicit_original_route_replays_without_writes(self):
        result = self.check(predecessor_source_tree=self.before)
        self.assertTrue(result["complete_patch_replay_verified"])
        self.assertEqual("pristine", result["predecessor"])
        self.assertEqual([self.transition], result["patches_replayed_in_memory"])
        self.assertEqual(BEFORE, (self.before / CORE).read_bytes())
        self.assertEqual(AFTER, (self.final / CORE).read_bytes())

    def test_explicit_readonly_route_replays_without_inferring_selector(self):
        result = self.check(predecessor_source_tree=self.before, predecessor="readonly")
        self.assertEqual("readonly", result["predecessor"])
        self.assertEqual([self.transition], result["patches_replayed_in_memory"])

    def test_wrong_complete_predecessor_is_rejected(self):
        (self.before / CORE).write_bytes(b"prefix\n" + BEFORE)
        with self.assertRaises(ValueError):
            self.check(predecessor_source_tree=self.before)

    def test_unchanged_semantic_file_must_match_across_the_replay(self):
        path = next(path for path in self.initial if path not in (CORE, source.PRODUCT))
        self.initial[path] = b"different but individually hash-bound semantic source\n"
        self.write(self.before / path, self.initial[path])
        self.composition["initial_source_files"] = self.rows(self.initial)
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "every final source byte"):
            self.check(predecessor_source_tree=self.before)

    def test_a_successful_patch_still_requires_the_complete_expected_output(self):
        self.transition["after"] = metadata.identity(b"some other complete source\n")
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "complete patch output"):
            self.check(predecessor_source_tree=self.before)

    def test_duplicate_final_row_is_rejected(self):
        self.composition["final_source_files"].append(self.composition["final_source_files"][-1])
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "duplicate-free"):
            self.check()

    def test_unknown_or_incomplete_predecessor_selection_is_rejected(self):
        for options in ({"predecessor": "guessed"}, {"predecessor": "readonly"}):
            with self.subTest(options=options), self.assertRaises(source.TargetFilesSourceCompositionError):
                self.check(**options)

    def test_changed_composition_during_final_read_is_rejected(self):
        changed = copy.deepcopy(self.composition)
        changed["unreviewed"] = True
        self.composer.side_effect = [self.composition, changed]
        with self.assertRaisesRegex(source.TargetFilesSourceCompositionError, "composition changed"):
            self.check()

    def test_changed_final_source_during_last_composition_read_is_rejected(self):
        calls = 0
        def concurrent_change(_root):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.final / CORE).write_bytes(AFTER + b"changed during verification\n")
            return self.composition
        self.composer.side_effect = concurrent_change
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_descriptor_during_last_composition_read_is_rejected(self):
        calls = 0
        def concurrent_change(_root):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.controls / source.CONTRACT).write_bytes(b"{}\n")
            return self.composition
        self.composer.side_effect = concurrent_change
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
