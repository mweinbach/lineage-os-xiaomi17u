"""Offline patch/evidence consistency; real Go/checker tests are separate receipts."""

import hashlib
import json
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/dex-import-uses-library.json"


def patch_files(text):
    """Validate the committed unified diff and expose its changed fragments."""
    files = {}
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        old = lines[index].removeprefix("--- ").strip()
        if not lines[index].startswith("--- "):
            raise ValueError("expected old-file header")
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ b/"):
            raise ValueError("expected new-file header")
        name = lines[index][6:].strip()
        if name in files or Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("unsafe or duplicate patch path")
        if old not in ("/dev/null", "a/" + name):
            raise ValueError("old and new paths differ")
        index += 1
        entry = {"old": old, "before": "", "after": "", "added": "", "hunks": 0}
        while index < len(lines) and not lines[index].startswith("--- "):
            match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n", lines[index])
            if not match:
                raise ValueError("expected hunk header")
            old_count = int(match[2] or 1)
            new_count = int(match[4] or 1)
            before = after = 0
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@ ", "--- ")):
                line = lines[index]
                if line[:1] not in (" ", "+", "-"):
                    raise ValueError("invalid hunk line")
                if line[0] in " -":
                    before += 1
                    entry["before"] += line[1:]
                if line[0] in " +":
                    after += 1
                    entry["after"] += line[1:]
                if line[0] == "+":
                    entry["added"] += line[1:]
                index += 1
            if (before, after) != (old_count, new_count):
                raise ValueError("incorrect hunk counts")
            entry["hunks"] += 1
        if not entry["hunks"]:
            raise ValueError("empty patch file")
        files[name] = entry
    return files


class DexImportPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.patch_path = ROOT / cls.record["patch"]["path"]
        cls.patch = cls.patch_path.read_text()
        cls.files = patch_files(cls.patch)
        cls.production = cls.files["java/java.go"]["added"]
        cls.fixtures = cls.files["java/dex_import_test.go"]["after"]

    def test_patch_and_resolved_source_snapshot_are_bound(self):
        record = self.record
        self.assertEqual(hashlib.sha256(self.patch_path.read_bytes()).hexdigest(), record["patch"]["sha256"])
        source = record["source"]
        snapshot = ROOT / source["snapshot"]
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), source["snapshot_sha256"])
        projects = {p.attrib.get("path", p.attrib["name"]): p.attrib["revision"]
                    for p in ET.parse(snapshot).getroot().findall("project")}
        self.assertEqual(source["revision"], "cbcbea9e65503ca15b363a0b06dda88fdbcb0154")
        self.assertEqual(projects[source["project"]], source["revision"])
        archives = record["verification"]["source_archives"]
        self.assertTrue(archives["all_archives_rehashed"])
        self.assertEqual(len(archives["projects"]), 7)
        for project in archives["projects"]:
            self.assertEqual(projects[project["path"]], project["revision"])
            self.assertRegex(project["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(project["regular_files"], 0)

    def test_patch_only_changes_the_importer_and_its_registered_tests(self):
        expected = {"java/java.go", "java/Android.bp", "java/dex_import_test.go"}
        self.assertEqual(set(self.files), expected)
        self.assertEqual({row["path"] for row in self.record["patch"]["files"]}, expected)
        for row in self.record["patch"]["files"]:
            self.assertRegex(row["after_sha256"], r"^[a-f0-9]{64}$")
            self.assertEqual(row["added_file"], row["before_sha256"] is None)
            if row["added_file"]:
                self.assertEqual(self.files[row["path"]]["old"], "/dev/null")
                self.assertEqual(hashlib.sha256(self.files[row["path"]]["after"].encode()).hexdigest(), row["after_sha256"])
            else:
                self.assertRegex(row["before_sha256"], r"^[a-f0-9]{64}$")
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
        self.assertEqual(self.files["java/Android.bp"]["added"].strip(), '"dex_import_test.go",')

    def test_patch_syntax_validation_rejects_bad_counts_and_paths(self):
        bad_count = "--- a/java/a.go\n+++ b/java/a.go\n@@ -1,2 +1 @@\n-old\n+new\n"
        traversal = "--- a/../a.go\n+++ b/../a.go\n@@ -1 +1 @@\n-old\n+new\n"
        wrong_base = "--- a/other.go\n+++ b/java/a.go\n@@ -1 +1 @@\n-old\n+new\n"
        for text in (bad_count, traversal, wrong_base):
            with self.subTest(text=text), self.assertRaises(ValueError):
                patch_files(text)

    def test_provider_exports_actual_paths_and_computed_context(self):
        production = self.production
        self.assertIn("func (j *DexImport) DexJarInstallPath() android.Path", production)
        self.assertIn("return j.dexpreopter.installPath", production)
        self.assertIn("func (j *DexImport) ClassLoaderContexts() dexpreopt.ClassLoaderContextMap", production)
        self.assertIn("return j.classLoaderContexts", production)
        self.assertIn("var _ UsesLibraryDependency = (*DexImport)(nil)", production)
        self.assertIn("j.classLoaderContexts = j.usesLibrary.classLoaderContextForUsesLibDeps(ctx)", production)
        after = self.files["java/java.go"]["after"]
        self.assertLess(after.index("j.classLoaderContexts ="), after.index("j.dexpreopt(ctx,"))
        self.assertNotIn('"/system/framework/"', production)
        self.assertNotIn("HeaderJars:", production)

    def test_only_required_jar_dependency_property_is_added(self):
        self.assertIn("Uses_libs proptools.Configurable[[]string]", self.production)
        self.assertIn("j.usesLibrary.deps(ctx, false)", self.production)
        for property_name in ("Provides_uses_lib", "Optional_uses_libs", "Enforce_uses_libs", "Exclude_uses_libs"):
            self.assertNotIn(property_name, self.production)
        self.assertNotIn("func (j *DexImport) ProvidesUsesLib", self.production)
        self.assertNotIn("module.AddProperties(&module.usesLibrary", self.patch)
        contract = self.record["contract"]
        self.assertEqual(contract["required_jar_dependency_property"], "uses_libs")
        self.assertTrue(contract["optional_app_dependency_supported"])
        self.assertFalse(contract["optional_aliases_supported"])
        self.assertEqual(contract["unsupported_dex_import_properties"],
                         ["provides_uses_lib", "optional_uses_libs", "enforce_uses_libs", "exclude_uses_libs"])

    def test_required_dependency_validation_fails_closed(self):
        for guard in ("info.UsesLibraryDependencyInfo == nil", "info.DexJarBuildPath.PathOrNil() == nil",
                      "info.UsesLibraryDependencyInfo.DexJarInstallPath == nil", "if ctx.Failed()"):
            self.assertIn(guard, self.production)
        self.assertIn('ctx.ModuleErrorf("uses-library dependency %q must provide a DEX jar and an install path"', self.production)
        self.assertNotIn("AllowMissingDependencies", self.production)
        self.assertNotIn("shouldDisableDexpreopt =", self.production)
        self.assertEqual(self.record["contract"]["dependency_errors"],
                         ["missing_required", "class_only", "not_java", "sdk_stubs_only", "cycle"])

    def test_go_fixtures_cover_context_shape_and_strict_app_rule(self):
        functions = set(re.findall(r"func (Test\w+)\(t \*testing.T\)", self.fixtures))
        self.assertEqual(functions, {"TestDexImportUsesLibraryProvider", "TestDexImportUsesLibraryNamespaceAndNestedContexts",
                                     "TestDexImportUsesLibraryInvalidDependency", "TestDexImportUsesLibraryUnsupportedProperties",
                                     "TestDexImportUsesLibraryDependencyCycle"})
        for assertion in ("no invented class-file provider", "preserved subtree", "ordered manifest names",
                          "no relaxed manifest check", "parent install path", "second install partition",
                          "nested host path", "no nested library promoted to manifest"):
            self.assertIn(assertion, self.fixtures)
        self.assertIn('app.Rule("dexpreopt")', self.fixtures)
        self.assertIn('"//vendor/example:runtime.parent"', self.fixtures)
        self.assertIn('uses_libs: ["runtime.required", "runtime.second"]', self.fixtures)

    def test_full_go_suite_result_is_not_misreported_as_a_pass(self):
        go = self.record["verification"]["go_fixtures"]
        self.assertEqual(go["baseline"]["test_and_subtest_actions"], {"pass": 853, "fail": 35, "skip": 28})
        self.assertEqual(go["patched"]["test_and_subtest_actions"], {"pass": 869, "fail": 35, "skip": 28})
        self.assertEqual(go["baseline"]["failed_tests_and_subtests"], go["patched"]["failed_tests_and_subtests"])
        self.assertEqual(len(go["added_passing_tests_and_subtests"]), 16)
        self.assertTrue(all(name.startswith("TestDexImportUsesLibrary") for name in go["added_passing_tests_and_subtests"]))
        self.assertTrue(go["unchanged_existing_named_results"])
        self.assertFalse(go["full_suite_passed"])
        self.assertEqual(go["package_exit_code"], 1)
        self.assertEqual(go["package_failure_events"], 1)
        self.assertEqual(sum(go["known_failure_families_named_count"].values()), 35)
        diagnostics = go["failure_diagnostic_comparison"]
        self.assertEqual(diagnostics["failed_tests_and_subtests_compared"], 35)
        self.assertTrue(diagnostics["all_normalized_diagnostic_sets_equal"])
        self.assertRegex(diagnostics["sha256"], r"^[a-f0-9]{64}$")

    def test_host_fixtures_have_offline_toolchain_and_execution_limits(self):
        go = self.record["verification"]["go_fixtures"]
        environment = go["environment"]
        self.assertEqual(environment["test_os"], "darwin")
        self.assertEqual(environment["test_arch"], "amd64")
        self.assertEqual(environment["GOPROXY"], "off")
        self.assertEqual(environment["GOSUMDB"], "off")
        self.assertEqual(environment["GOTOOLCHAIN"], "local")
        self.assertEqual(environment["GOENV"], "off")
        self.assertFalse(go["fixture_tests_execute_build_rules"])
        self.assertFalse(go["linux_guest_go_test_executed"])

    def test_roundtrip_executes_pinned_checkers_and_rejects_mismatches(self):
        check = self.record["verification"]["python_roundtrip"]
        expected = {"all-runtime-names": 0, "required-subtree-retained": 0, "wrong-alias-filtered": 0,
                    "manifest-exact": 0, "manifest-reordered": 255, "manifest-wrong-runtime-name": 255,
                    "manifest-missing-direct-library": 255, "manifest-nested-library-promoted": 255}
        self.assertEqual({row["name"]: row["exit_code"] for row in check["command_results"]}, expected)
        self.assertEqual(check["expected_results_passed"], 8)
        self.assertEqual(check["strict_negative_cases"], 4)
        self.assertTrue(check["actual_pinned_scripts_executed"])
        self.assertTrue(check["synthetic_inputs_only"])
        self.assertFalse(check["dex2oat_executed"])
        self.assertEqual(check["tools"]["scripts/construct_context.py"]["sha256"],
                         "cc42f3665864e2082aab59238e245fab479860e43d7102a227880b05203d7d1a")
        self.assertEqual(check["tools"]["scripts/manifest_check.py"]["sha256"],
                         "ad2be68446c693befc2c4729016c57046a97783ff87567f2ca0221e84fead7b6")

    def test_scope_preserves_apk_and_device_gates(self):
        self.assertTrue(all(value is False for value in self.record["scope"].values()))
        self.assertFalse(self.record["patch"]["guest_source_modified_by_this_work"])
        for key in ("class_file_compilation_provider_added", "permission_xml_generated_or_validated_by_patch",
                    "app_manifest_validation_modified", "dexpreopt_disabled_or_relaxed"):
            self.assertFalse(self.record["contract"][key])
        self.assertGreaterEqual(len(self.record["remaining_work"]), 6)
        docs = (ROOT / "docs/dex-import-uses-library.md").read_text()
        self.assertIn("full suite **does not pass**", docs)
        self.assertIn("No APK is rewritten, signed, imported or installed here", docs)

    def test_private_receipts_are_references_not_test_dependencies(self):
        verification = self.record["verification"]
        receipts = [verification["source_archives"], verification["patch_application"],
                    verification["go_fixtures"]["receipt"], verification["python_roundtrip"]["receipt"],
                    verification["python_roundtrip"]["generated_context"]]
        for receipt in receipts:
            self.assertTrue(receipt["path"].startswith("reports/dex-import-clc-20260827/"))
            self.assertNotIn("..", Path(receipt["path"]).parts)
            self.assertRegex(receipt["sha256"], r"^[a-f0-9]{64}$")
        proof = verification["patch_application"]
        for key in ("base_files_from_pinned_archive", "whitespace_check_passed", "patched_file_hashes_match",
                    "reverse_check_passed", "gofmt_clean"):
            self.assertTrue(proof[key])


if __name__ == "__main__":
    unittest.main()
