"""Execute the actual patched helper offline; no Kati, source tree or phone."""

from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "patches/evolution/pinned-version-date.json"


def patch_files():
    record = json.loads(CONTRACT.read_text())
    patch = (ROOT / record["patch"]["path"]).read_bytes()
    sections = patch.decode().split("diff --git ")[1:]
    files = []
    for section in sections:
        lines = section.splitlines(keepends=True)
        starts = [i for i, line in enumerate(lines) if line.startswith("@@ ")]
        if len(starts) != 1:
            raise AssertionError("Each small source file must have one complete hunk")
        index = starts[0]
        match = re.fullmatch(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", lines[index])
        if not match:
            raise AssertionError("Invalid complete-file hunk")
        old_start, old_count, new_start, new_count = map(int, match.groups())
        if old_start != (1 if old_count else 0) or new_start != 1:
            raise AssertionError("Tests require complete source preimages and postimages")
        body = lines[index + 1:]
        if not all(line.startswith((" ", "+", "-")) for line in body):
            raise AssertionError("Unexpected hunk contents")
        before = "".join(line[1:] for line in body if line.startswith((" ", "-")))
        after = "".join(line[1:] for line in body if line.startswith((" ", "+")))
        if len(before.splitlines()) != old_count or len(after.splitlines()) != new_count:
            raise AssertionError("Hunk counts do not match actual source")
        files.append((before.encode(), after.encode()))
    return record, patch, files


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class PinnedVersionDateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record, cls.patch, cls.files = patch_files()
        cls.before = cls.files[0][0].decode()
        cls.after = cls.files[0][1].decode()

    def test_patch_and_complete_source_bytes_are_hash_bound(self):
        self.assertEqual(self.record["patch"], {
            "path": "patches/evolution/0012-pinned-version-date.patch", **identity(self.patch)})
        self.assertEqual(len(self.files), 2)
        self.assertEqual(self.record["project"]["path"], "vendor/lineage")
        self.assertEqual(self.record["project"]["commit"],
                         "11d2966a3294a0a692fc958127c770cfe9c00a3c")
        for (before, after), row in zip(self.files, self.record["source_files"]):
            with self.subTest(path=row["path"]):
                self.assertEqual(row["before"], identity(before) if before else None)
                self.assertEqual(row["after"], identity(after))
                self.assertEqual(row["after_git_blob"], git_blob(after))
                if before:
                    self.assertEqual(row["before_git_blob"], git_blob(before))
        self.assertEqual(identity(self.files[0][0])["sha256"],
                         "d416c5abb8504f181b5f20362b3a8b4ec7405c729ba8c87e3707f9cb1f431b8e")

    def test_disabled_branch_preserves_original_date_and_property_sources(self):
        original_versions = self.before.split("# Internal version\n", 1)[1].split(
            "\n# Evolution X version properties", 1)[0]
        self.assertIn("else\n# Internal version\n" + original_versions + "endif\n", self.after)
        for marker in ("# Evolution X version properties",):
            self.assertEqual(self.before.split(marker, 1)[1], self.after.split(marker, 1)[1])
        self.assertEqual(self.before.split("# Internal version", 1)[0],
                         self.after.split("# Optional reproducible version dates", 1)[0])
        self.assertEqual(self.after.count("$(shell date +%Y%m%d)"), 2)

    def test_opt_in_uses_one_isolated_helper_without_shell_epoch_interpolation(self):
        branch = self.after.split("ifeq ($(_nezha_use_pinned_build_datetime),true)\n", 1)[1]
        branch = branch.split("\nelse\n# Internal version", 1)[0]
        self.assertEqual(branch.count("$(shell "), 1)
        self.assertIn("$(shell python3 -I -S -B vendor/lineage/build/tools/nezha_pinned_build_date.py)",
                      branch)
        self.assertNotIn("$(BUILD_DATETIME)", branch)
        self.assertNotIn("$(shell date", branch)
        self.assertIn("ifneq ($(origin BUILD_DATETIME),environment)\n$(error ", branch)
        self.assertIn("ifeq ($(_nezha_pinned_version_date),)\n$(error ", branch)
        for variable in ("LINEAGE_VERSION", "LINEAGE_DISPLAY_VERSION"):
            assignment = next(line for line in branch.splitlines()
                              if line.startswith(variable + " := "))
            self.assertEqual(assignment.count("$(_nezha_pinned_version_date)"), 1)

    def test_capability_and_reserved_variables_are_explicitly_guarded(self):
        self.assertIn("ifneq ($(origin NEZHA_USE_PINNED_BUILD_DATETIME),undefined)", self.after)
        self.assertIn("_nezha_use_pinned_build_datetime := $(value NEZHA_USE_PINNED_BUILD_DATETIME)",
                      self.after)
        self.assertNotIn("_nezha_use_pinned_build_datetime := $(NEZHA_USE_PINNED_BUILD_DATETIME)",
                         self.after)
        guard = "\n".join([
            "ifneq ($(_nezha_use_pinned_build_datetime),)",
            "ifneq ($(_nezha_use_pinned_build_datetime),false)",
            "ifneq ($(_nezha_use_pinned_build_datetime),true)",
            "$(error NEZHA_USE_PINNED_BUILD_DATETIME must be true, false, or unset)",
            "endif", "endif", "endif"])
        self.assertIn(guard, self.after)
        for variable in ("_nezha_use_pinned_build_datetime", "_nezha_pinned_version_date"):
            self.assertIn("ifneq ($(filter-out undefined file,$(origin " + variable + ")),)",
                          self.after)
        self.assertFalse(self.record["capability"]["enabled_automatically"])
        self.assertFalse(self.record["composition"]["existing_source_compositions_automatically_extended"])

    def test_native_adoption_matrix_includes_raw_make_expressions(self):
        cases = self.record["capability"]["required_rejected_fixture_values"]
        for value in ("$(strip true)", "$(shell printf true)", "true false", " true", "true "):
            self.assertIn(value, cases)
        self.assertFalse(self.record["validation_scope"]["native_kati_verified"])

    def test_source_order_evidence_and_unverified_gates_remain_explicit(self):
        evidence = {row["path"]: row for row in self.record["source_order_evidence"]}
        for path in ("build/soong/ui/build/config.go", "build/soong/ui/build/exec.go",
                     "build/soong/ui/build/dumpvars.go", "build/soong/ui/build/kati.go",
                     "build/make/core/config.mk", "build/make/core/envsetup.mk",
                     "build/make/core/product_config.mk", "vendor/lineage/config/common.mk"):
            self.assertIn(path, evidence)
            self.assertRegex(evidence[path]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(evidence[path]["commit"], r"^[0-9a-f]{40}$")
        scope = self.record["validation_scope"]
        for key in ("native_kati_verified", "actual_product_configuration_verified",
                    "guest_source_installed", "images_rebuilt", "complete_rom_reproducibility_verified"):
            self.assertFalse(scope[key])
        self.assertEqual(scope["phone_operations"], [])
        self.assertIn("Order-only date dependencies", " ".join(self.record["verification_requirements"]))


class PinnedVersionDateHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, files = patch_files()
        cls.namespace = {"__name__": "pinned_date_test"}
        exec(compile(files[1][1], "<actual patched pinned date helper>", "exec"), cls.namespace)

    def format_date(self, value):
        return self.namespace["format_build_date"](value)

    def main(self, environment):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, environment, clear=True), \
                mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            code = self.namespace["main"]()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_known_utc_day_and_leap_year_boundaries(self):
        for epoch, date in (("0", "19700101"), ("86399", "19700101"),
                            ("86400", "19700102"), ("951782399", "20000228"),
                            ("951782400", "20000229"), ("951868799", "20000229"),
                            ("951868800", "20000301"), ("1709164800", "20240229"),
                            ("253402300799", "99991231")):
            with self.subTest(epoch=epoch):
                self.assertEqual(self.format_date(epoch), date)

    def test_invalid_epoch_has_no_date_output_or_raw_input_diagnostic(self):
        invalid = ("", "00", "01", "+1", "-1", "1.0", " 1", "1 ", "1\n", "1\t", "1 2",
                   "1e9", "١", "１", "253402300800", "999999999999", "1" * 5000,
                   "$(touch sentinel)", "`touch sentinel`", "0; touch sentinel", "'quoted'")
        for epoch in invalid:
            with self.subTest(epoch=epoch[:80]):
                code, stdout, stderr = self.main({"BUILD_DATETIME": epoch})
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertTrue(stderr.startswith("nezha_pinned_build_date: BUILD_DATETIME "))
                self.assertNotIn("sentinel", stderr)

    def test_missing_epoch_and_alternative_date_sources_do_not_fall_back(self):
        for environment in ({}, {"SOURCE_DATE_EPOCH": "0"},
                            {"BUILD_DATETIME_FILE": "/an/unread/file"},
                            {"BUILD_DATETIME": "", "SOURCE_DATE_EPOCH": "0"}):
            with self.subTest(environment=environment):
                code, stdout, stderr = self.main(environment)
                self.assertEqual((code, stdout), (1, ""))
                self.assertIn("canonical nonnegative ASCII decimal", stderr)

    def test_timezone_and_locale_do_not_change_success_output(self):
        for timezone in ("UTC", "Pacific/Kiritimati", "America/Los_Angeles", "Etc/GMT+12"):
            with self.subTest(timezone=timezone):
                self.assertEqual(self.main({"BUILD_DATETIME": "86400", "TZ": timezone,
                                            "LC_ALL": "ar_EG.UTF-8"}), (0, "19700102\n", ""))

    def test_same_epoch_does_not_consult_any_datetime_clock_or_host_conversion(self):
        class NoClock(datetime):
            @classmethod
            def now(cls, *args, **kwargs):
                raise AssertionError("wall clock must not be read")

            today = now
            utcnow = now
            fromtimestamp = now
            utcfromtimestamp = now

        with mock.patch.dict(self.namespace, {"datetime": NoClock}):
            self.assertEqual(self.format_date("951782400"), "20000229")
            self.assertEqual(self.format_date("951782400"), "20000229")

    def test_non_string_values_are_rejected_before_integer_conversion(self):
        for value in (None, 0, 1, True, 1.0, b"0", [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "canonical nonnegative ASCII decimal"):
                    self.format_date(value)


if __name__ == "__main__":
    unittest.main()
