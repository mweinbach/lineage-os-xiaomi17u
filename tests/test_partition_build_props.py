"""Offline behavioral regressions for the pinned partition-property patch.

The changed function bodies come directly from the public patch hunks. The
separate integration probe loads the full hash-bound common.py. No checkout,
phone, image tool, network connection or proprietary input is needed here.
"""

from contextlib import redirect_stderr, redirect_stdout
import copy
import difflib
import io
import json
from pathlib import Path
import re
import tempfile
import textwrap
import unittest
from unittest import mock
import zipfile

from scripts import partition_build_props as props


ROOT = Path(__file__).resolve().parents[1]

# Fixtures for the unchanged byte-reading helpers, with shorter error text.
# These exercise real directory and ZIP reads rather than mock the corrected
# function's return value. The source-bound probe loads the exact full helpers.
HELPERS = '''def ReadBytesFromInputFile(input_file, fn):
  if isinstance(input_file, zipfile.ZipFile):
    return input_file.read(fn)
  elif zipfile.is_zipfile(input_file):
    with zipfile.ZipFile(input_file, "r", allowZip64=True) as zfp:
      return zfp.read(fn)
  else:
    if not os.path.isdir(input_file):
      raise ValueError("Invalid input_file: " + input_file)
    path = os.path.join(input_file, *fn.split("/"))
    try:
      with open(path, "rb") as f:
        return f.read()
    except IOError as e:
      if e.errno == errno.ENOENT:
        raise KeyError(fn)

def ReadFromInputFile(input_file, fn):
  return ReadBytesFromInputFile(input_file, fn).decode()
'''


def fixture_source(*, after=True):
    patch = (ROOT / props.PATCH_PATH).read_text()
    chunks = re.split(r"^@@ -\d+,\d+ \+\d+,\d+ @@\n", patch, flags=re.M)[1:]
    if len(chunks) != 2:
        raise ValueError("expected the two reviewed common.py hunks")
    markers = (" ", "+") if after else (" ", "-")
    source = "".join(line[1:] for chunk in chunks for line in chunk.splitlines(keepends=True)
                     if line.startswith(markers))

    def function(name, indent):
        lines = source.splitlines(keepends=True)
        matches = [index for index, line in enumerate(lines)
                   if line.startswith(" " * indent + "def " + name + "(")]
        if len(matches) != 1:
            raise ValueError("expected one patch function: " + name)
        start = matches[0]
        stop = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].strip() and len(lines[index]) - len(lines[index].lstrip()) <= indent:
                stop = index
                break
        return textwrap.dedent("".join(lines[start:stop])).rstrip() + "\n"

    return (HELPERS + "\nclass PartitionBuildProps:\n  @staticmethod\n"
            + textwrap.indent(function("_ReadPartitionPropFile", 2), "  ")
            + "\n" + function("PartitionMapFromTargetFiles", 0)).encode()


class PartitionBuildPropsBehaviorTests(unittest.TestCase):
    def setUp(self):
        for name in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(name, side_effect=AssertionError("offline test: " + name)))
        self.namespace, self.log = props._namespace(fixture_source())
        self.reader = self.namespace["PartitionBuildProps"]._ReadPartitionPropFile
        self.mapping = self.namespace["PartitionMapFromTargetFiles"]

    def test_actual_patch_functions_pass_all_python_probe_cases(self):
        cases = props._exercise(fixture_source())
        self.assertEqual(len(cases), 24)
        self.assertEqual(len({case["name"] for case in cases}), len(cases))
        self.assertTrue(all(case["passed"] is True for case in cases))

    def test_original_reader_fails_for_absent_optional_partition(self):
        original, _ = props._namespace(fixture_source(after=False))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(KeyError, "odm_dlkm"):
                original["PartitionBuildProps"]._ReadPartitionPropFile(directory, "odm_dlkm")
            self.assertEqual(self.reader(directory, "odm_dlkm"), "")
            self.assertIn("Failed to find directory for partition odm_dlkm", self.log.getvalue())

    def test_original_mapper_fails_for_open_zip_but_reader_helper_does_not(self):
        original, _ = props._namespace(fixture_source(after=False))
        with zipfile.ZipFile(io.BytesIO(), "w") as archive:
            archive.writestr("SYSTEM/build.prop", "ro.test=system\n")
            self.assertEqual(original["ReadFromInputFile"](archive, "SYSTEM/build.prop"), "ro.test=system\n")
            with self.assertRaises(TypeError):
                original["PartitionMapFromTargetFiles"](archive)
            self.assertEqual(self.reader(archive, "system"), "ro.test=system\n")

    def test_original_reader_fails_for_zip_path(self):
        original, _ = props._namespace(fixture_source(after=False))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target-files.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("VENDOR/build.prop", "ro.test=vendor\n")
            with self.assertRaisesRegex(KeyError, "vendor"):
                original["PartitionBuildProps"]._ReadPartitionPropFile(str(path), "vendor")
            self.assertEqual(self.reader(str(path), "vendor"), "ro.test=vendor\n")

    def test_every_original_partition_mapping_and_fallback_remains(self):
        paths = {
            "system": "SYSTEM", "vendor": "SYSTEM/vendor",
            "product": "SYSTEM/product", "system_ext": "SYSTEM/system_ext",
            "odm": "SYSTEM/vendor/odm", "vendor_dlkm": "SYSTEM/vendor/vendor_dlkm",
            "odm_dlkm": "SYSTEM/vendor/odm_dlkm", "system_dlkm": "SYSTEM/system_dlkm",
        }
        with zipfile.ZipFile(io.BytesIO(), "w") as archive:
            for name, path in paths.items():
                archive.writestr(path + "/etc/build.prop", "ro.test=" + name)
            self.assertEqual(self.mapping(target_files_dir=archive), paths)
            for name in paths:
                self.assertEqual(self.reader(archive, name), "ro.test=" + name)

    def test_primary_directory_missing_properties_does_not_fall_through(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "VENDOR").mkdir()
            (root / "SYSTEM/vendor").mkdir(parents=True)
            (root / "SYSTEM/vendor/build.prop").write_text("ro.test=wrong fallback")
            self.assertEqual(self.mapping(directory)["vendor"], "VENDOR")
            self.assertEqual(self.reader(directory, "vendor"), "")
            self.assertIn("Failed to read VENDOR/build.prop", self.log.getvalue())

    def test_implicit_and_explicit_zip_directories_have_same_mapping(self):
        with zipfile.ZipFile(io.BytesIO(), "w") as implicit, zipfile.ZipFile(io.BytesIO(), "w") as explicit:
            implicit.writestr("VENDOR/odm_dlkm/etc/build.prop", "actual nested prop")
            explicit.writestr("VENDOR/", "")
            explicit.writestr("VENDOR/odm_dlkm/", "")
            explicit.writestr("VENDOR/odm_dlkm/etc/build.prop", "actual nested prop")
            self.assertEqual(self.mapping(implicit), self.mapping(explicit))
            self.assertEqual(self.mapping(implicit), {"vendor": "VENDOR", "odm_dlkm": "VENDOR/odm_dlkm"})

    def test_malformed_zip_path_is_rejected_without_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.zip"
            path.write_bytes(b"not a ZIP archive")
            with self.assertRaisesRegex(ValueError, "Expected a target-files"):
                self.reader(str(path), "vendor")

    def test_missing_property_only_returns_empty_without_creating_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "VENDOR").mkdir()
            before = sorted(str(entry.relative_to(path)) for entry in path.rglob("*"))
            self.assertEqual(self.reader(directory, "vendor"), "")
            self.assertEqual(self.reader(directory, "odm"), "")
            self.assertEqual(sorted(str(entry.relative_to(path)) for entry in path.rglob("*")), before)


class PartitionBuildPropsContractTests(unittest.TestCase):
    def test_public_contract_binds_the_exact_upstream_and_patch(self):
        record, identity, patch = props._contract()
        self.assertEqual(identity, props._identity((ROOT / props.CONTRACT_PATH).read_bytes()))
        self.assertEqual(record["project"]["commit"], props.PROJECT_COMMIT)
        self.assertEqual(record["source_files"][0]["before"], {
            "sha256": "78b74437cb9916eda2b25ac4c8afd13b50847648f10c2e4fd66df0e02ab90bc2", "size_bytes": 156263,
        })
        self.assertEqual(patch, (ROOT / props.PATCH_PATH).read_bytes())
        self.assertEqual(record["validation_scope"], props.SCOPE)
        for field in ("property_parser_or_import_semantics_changed", "images_extracted_or_changed",
                      "missing_partitions_or_properties_fabricated", "signature_or_avb_rules_changed",
                      "readiness_flags_changed"):
            self.assertIs(record["semantics"][field], False)

    def test_historical_source_contracts_still_require_original_common(self):
        digest = props._contract()[0]["source_files"][0]["before"]["sha256"]
        for filename in ("prebuilt-recovery.json", "ab-only-recovery-packaging.json",
                         "direct-avb-custom-images.json"):
            data = (ROOT / "patches/evolution" / filename).read_text()
            self.assertIn(digest, data)
            self.assertNotIn(props._contract()[0]["source_files"][0]["after"]["sha256"], data)

    def test_patch_replay_requires_exact_hunk_context_and_positions(self):
        before = b"zero\none\ntwo\nthree\n"
        after = b"zero\nONE\ntwo\nthree\n"
        patch = "".join(difflib.unified_diff(before.decode().splitlines(keepends=True),
                                             after.decode().splitlines(keepends=True),
                                             fromfile="a/test", tofile="b/test")).encode()
        self.assertEqual(props._apply_patch(before, patch), after)
        with self.assertRaisesRegex(props.PartitionBuildPropsError, "preimage"):
            props._apply_patch(before.replace(b"two", b"different"), patch)
        with self.assertRaisesRegex(props.PartitionBuildPropsError, "output position"):
            props._apply_patch(before, patch.replace(b"+1,4", b"+2,4"))
        with self.assertRaisesRegex(props.PartitionBuildPropsError, "counts"):
            props._apply_patch(before, patch.replace(b"-1,4", b"-1,5"))


class PartitionBuildPropsGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.before = fixture_source(after=False)
        self.after = fixture_source()
        self.record = copy.deepcopy(props._contract()[0])
        self.record["source_files"][0]["before"] = props._identity(self.before)
        self.record["source_files"][0]["after"] = props._identity(self.after)
        self.source_tree = self.root / "source"
        source = self.source_tree / props.SOURCE_PATH
        source.parent.mkdir(parents=True)
        source.write_bytes(self.after)
        patch = self.root / props.PATCH_PATH
        patch.parent.mkdir(parents=True)
        patch.write_bytes((ROOT / props.PATCH_PATH).read_bytes())
        self.save_contract()
        self.enterContext(mock.patch.object(props, "ROOT", self.root))
        for name in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(name, side_effect=AssertionError("offline test: " + name)))

    def save_contract(self):
        (self.root / props.CONTRACT_PATH).write_text(json.dumps(self.record))

    def test_source_and_branch_probe_only_report_their_actual_scope(self):
        result = props.verify(self.source_tree, run_probe=True)
        self.assertEqual(result["status"], "verified-source-and-python-probe")
        self.assertEqual(result["scope"], props.SCOPE)
        self.assertIs(result["whole_source_tree_verified"], False)
        self.assertIs(result["exact_patch_replayed_in_memory"], False)
        self.assertEqual(len(result["cases"]), 24)

    def test_full_source_mismatch_is_refused_before_loading(self):
        (self.source_tree / props.SOURCE_PATH).write_bytes(self.after + b"# drift\n")
        with mock.patch.object(props, "_namespace", side_effect=AssertionError("must not load")):
            with self.assertRaisesRegex(props.PartitionBuildPropsError, "reviewed patched source"):
                props.verify(self.source_tree, run_probe=True)

    def test_changed_patch_is_refused(self):
        patch = self.root / props.PATCH_PATH
        patch.write_bytes(patch.read_bytes() + b"# drift\n")
        with self.assertRaisesRegex(props.PartitionBuildPropsError, "patch differs"):
            props.verify(self.source_tree)

    def test_wrong_project_or_promoted_scope_is_refused(self):
        self.record["project"]["branch"] = "newer-unreviewed"
        self.save_contract()
        with self.assertRaisesRegex(props.PartitionBuildPropsError, "reviewed bka"):
            props.verify(self.source_tree)
        self.record["project"]["branch"] = "bka"
        self.record["validation_scope"]["full_target_files_verified"] = True
        self.save_contract()
        with self.assertRaisesRegex(props.PartitionBuildPropsError, "readiness"):
            props.verify(self.source_tree)

    def test_duplicate_json_key_is_refused(self):
        path = self.root / props.CONTRACT_PATH
        path.write_text(path.read_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
        with self.assertRaises(props.KernelInputsError):
            props.verify(self.source_tree)

    def test_source_symlink_is_refused(self):
        source = self.source_tree / props.SOURCE_PATH
        target = self.root / "actual-common.py"
        source.rename(target)
        source.symlink_to(target)
        with self.assertRaises((props.KernelInputsError, ValueError)):
            props.verify(self.source_tree)

    def test_cli_failure_has_no_success_json(self):
        (self.source_tree / props.SOURCE_PATH).write_bytes(self.before)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = props.main(["--source-tree", str(self.source_tree), "--probe"])
        self.assertEqual(status, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("reviewed patched source", err.getvalue())


if __name__ == "__main__":
    unittest.main()
