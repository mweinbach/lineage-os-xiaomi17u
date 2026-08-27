"""Offline source-contract checks; these do not run init or inspect a phone."""

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InitBootPropertiesPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/evolution/init-boot-properties.json").read_text())
        cls.raw = (ROOT / cls.record["patch"]).read_bytes()
        cls.patch = cls.raw.decode()
        cls.sections = cls.patch.split("diff --git ")[1:]

    def test_exact_project_patch_and_source_versions_are_bound(self):
        self.assertEqual(self.record["project"], "system/core")
        self.assertEqual(self.record["base_commit"], "241488ea392c01079941d86ddc458b8a0c9ae6e1")
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), self.record["patch_sha256"])
        self.assertEqual([row["path"] for row in self.record["files"]],
                         ["init/Android.bp", "init/property_service.cpp"])
        self.assertEqual(len(self.sections), 2)
        for section, row in zip(self.sections, self.record["files"]):
            with self.subTest(path=row["path"]):
                self.assertTrue(section.startswith(f'a/{row["path"]} b/{row["path"]}\n'))
                self.assertIn(row["before_git_blob"] + ".." + row["after_git_blob"], section)
                for key in ("before_sha256", "after_sha256"):
                    self.assertRegex(row[key], r"^[0-9a-f]{64}$")
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
                self.assertGreater(row["before_size_bytes"], 0)
                self.assertGreater(row["after_size_bytes"], 0)

    def test_both_init_stage_defaults_disable_the_known_spoofing_helpers(self):
        section = self.sections[0]
        removed = [line[1:] for line in section.splitlines()
                   if line.startswith("-") and not line.startswith("---")]
        added = [line[1:] for line in section.splitlines()
                 if line.startswith("+") and not line.startswith("+++")]
        self.assertEqual(removed, ['        "-DSPOOF_SAFETYNET=1",'] * 2)
        self.assertEqual(added, ['        "-DSPOOF_SAFETYNET=0",'] * 2)
        self.assertEqual(self.record["spoof_safetynet_default"], 0)
        self.assertEqual(self.record["default_definitions_changed"], 2)
        self.assertNotIn("ALLOW_PERMISSIVE_SELINUX", section)

    def test_release_debug_and_vbmeta_helpers_are_inside_the_disabled_guards(self):
        self.assertIn("+    if (SPOOF_SAFETYNET) {\n+        LoadReleaseBuildProperties();\n+    }", self.patch)
        self.assertIn(
            "+            if (SPOOF_SAFETYNET) {\n"
            "+                weaken_prop_override_security = true;\n"
            "+                LoadDebugProperties();\n"
            "+                LoadVbMetaOverrides();\n"
            "+                weaken_prop_override_security = false;\n"
            "+            }", self.patch)
        self.assertEqual(self.record["newly_guarded_helpers"],
                         ["LoadReleaseBuildProperties", "LoadDebugProperties", "LoadVbMetaOverrides"])
        self.assertEqual(self.record["guarded_helpers"],
                         ["SetSafetyNetProps", *self.record["newly_guarded_helpers"]])

    def test_existing_boot_properties_stay_read_only_during_vendor_overrides(self):
        self.assertIn(
            '+            if (StartsWith(name, "ro.") &&\n'
            '+                    (!weaken_prop_override_security || StartsWith(name, "ro.boot."))) {',
            self.patch)
        self.assertIn('         if (pi != nullptr) {', self.patch)
        self.assertIn('                 return {PROP_ERROR_READ_ONLY_PROPERTY};', self.patch)
        for name, present, override, rejected in (
            ("ro.boot.verifiedbootstate", True, False, True),
            ("ro.boot.verifiedbootstate", True, True, True),
            ("ro.boot.vbmeta.digest", True, False, True),
            ("ro.boot.vbmeta.digest", True, True, True),
            ("ro.boot.verifiedbootstate", False, True, False),
            ("ro.build.type", True, False, True),
            ("ro.build.type", True, True, False),
            ("ro.build.type", False, False, False),
            ("persist.sys.example", True, False, False),
            ("sys.example", True, True, False),
            ("ro.bootloader", True, True, False),
        ):
            with self.subTest(name=name, present=present, override=override):
                # Evaluate the exact condition asserted above, including its enclosing guard.
                actual = present and name.startswith("ro.") and (
                    not override or name.startswith("ro.boot."))
                self.assertEqual(actual, rejected)

    def test_patch_hunk_counts_and_size_deltas_are_consistent(self):
        count = 0
        for section, row in zip(self.sections, self.record["files"]):
            delta = 0
            hunks = re.split(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@[^\n]*\n", section, flags=re.M)
            self.assertEqual((len(hunks) - 1) % 5, 0)
            for i in range(1, len(hunks), 5):
                _, old_count, _, new_count, body = hunks[i:i + 5]
                lines = body.splitlines(keepends=True)
                self.assertTrue(all(line[:1] in (" ", "+", "-") for line in lines))
                self.assertEqual(sum(line.startswith((" ", "-")) for line in lines), int(old_count))
                self.assertEqual(sum(line.startswith((" ", "+")) for line in lines), int(new_count))
                delta += sum(len(line[1:].encode()) for line in lines if line.startswith("+"))
                delta -= sum(len(line[1:].encode()) for line in lines if line.startswith("-"))
                count += 1
            self.assertEqual(row["before_size_bytes"] + delta, row["after_size_bytes"])
        self.assertEqual(count, 5)
        self.assertTrue(self.raw.endswith(b"\n"))

    def test_property_checks_and_known_limits_are_preserved(self):
        self.assertEqual(self.record["read_only_behavior"], {
            "existing_ro_boot_replacement_allowed": False,
            "initial_property_creation_changed": False,
            "other_vendor_read_only_override_behavior_changed": False,
        })
        for flag in ("vendor_property_hooks_removed", "vendor_api_derivation_changed",
                     "signature_checks_changed", "rollback_checks_changed"):
            self.assertIs(self.record[flag], False)
        for untouched in ("CheckPermissions", "IsLegalPropertyName", "IsLegalPropertyValue",
                          "vendor_load_properties", "property_initialize_ro_vendor_api_level"):
            self.assertNotIn(untouched, self.patch)
        requirements = " ".join(self.record["verification_requirements"])
        self.assertIn("Build both init stages", requirements)
        self.assertIn("actual compiled SPOOF_SAFETYNET=0", requirements)
        self.assertIn("libinit hooks", requirements)
        self.assertIn("does not prove that all property masking paths are absent", requirements)
        self.assertNotIn("device_tested", self.record)

    def test_private_source_capture_receipts_are_hash_bound_without_private_content(self):
        self.assertEqual(len(self.record["source_capture_receipts"]), 2)
        for row in self.record["source_capture_receipts"]:
            self.assertTrue(row["path"].startswith("artifacts/source-contracts/nezha-init-helper-"))
            self.assertTrue(row["path"].endswith("/receipt.json"))
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(row["size_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
