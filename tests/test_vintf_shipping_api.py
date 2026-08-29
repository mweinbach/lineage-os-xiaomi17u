"""Execute the actual public patch body offline; no native checker or phone."""

import ast
import copy
import json
import logging
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

from scripts import vintf_shipping_api as api


WORKSPACE = api.ROOT
PROPERTY = api.PROPERTY


def patch_sources():
    patch = (WORKSPACE / api.PATCH).read_bytes()
    lines = patch.decode().splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("@@ ")]
    if len(starts) != 1:
        raise AssertionError("single-function patch must have one hunk")
    start = starts[0]
    position = int(re.match(r"@@ -(\d+),", lines[start]).group(1))
    before_hunk = [line[1:] for line in lines[start + 1:] if line.startswith((" ", "-"))]
    # The exact hunk ends at the following function declaration. Its body and
    # the earlier module lines are inert outside-function sentinels.
    before = (("# inert unexecuted module line\n" * (position - 1)) + "".join(before_hunk)
              + "  raise RuntimeError('unexecuted kernel sentinel')\n").encode()
    after = api._apply_patch(before, patch)
    return before, after, patch


class Props:
    def __init__(self, value):
        self.value = value

    def GetProp(self, name):
        if name != PROPERTY:
            raise AssertionError("an unrelated property was consulted")
        return self.value


class ShippingApiFunctionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        before, after, _ = patch_sources()
        cls.functions = {}
        for name, raw in (("before", before), ("after", after)):
            namespace = {"logger": logging.getLogger("shipping-api-tests")}
            exec(compile(ast.Module(body=[api._function(raw)], type_ignores=[]),
                         "<actual shipping API patch>", "exec"), namespace)
            cls.functions[name] = namespace[api.FUNCTION]

    def call(self, vendor=None, odm=None):
        info = {"vendor.build.prop": Props(vendor), "odm.build.prop": Props(odm)}
        return self.functions["after"](info)

    def test_vendor_only_normal_result_is_unchanged(self):
        info = {"vendor.build.prop": Props("36"), "odm.build.prop": Props(None)}
        self.assertEqual(self.functions["before"](info), self.functions["after"](info))
        self.assertEqual(["--property", PROPERTY + "=36"], self.call("36"))

    def test_original_gap_is_reproduced_and_odm_value_forwarded(self):
        info = {"vendor.build.prop": Props(None), "odm.build.prop": Props("36")}
        with self.assertLogs("shipping-api-tests", level="WARNING"):
            self.assertEqual([], self.functions["before"](info))
        self.assertEqual(["--property", PROPERTY + "=36"], self.functions["after"](info))

    def test_matching_values_produce_exactly_one_property_pair(self):
        self.assertEqual(["--property", PROPERTY + "=36"], self.call("36", "36"))

    def test_conflicting_values_fail(self):
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.call("36", "35")

    def test_both_missing_fail_instead_of_omitting_argument(self):
        with self.assertRaisesRegex(ValueError, "Cannot determine"):
            self.call()

    def test_missing_property_containers_are_handled_as_absence(self):
        for info in ({"vendor.build.prop": Props("36")}, {"odm.build.prop": Props("36")}):
            with self.subTest(info=info):
                self.assertEqual(["--property", PROPERTY + "=36"], self.functions["after"](info))
        with self.assertRaises(ValueError):
            self.functions["after"]({})

    def test_explicit_empty_is_invalid_in_either_source(self):
        for vendor, odm in (("", "36"), ("36", ""), ("", None), (None, "")):
            with self.subTest(vendor=vendor, odm=odm), self.assertRaisesRegex(ValueError, "Invalid"):
                self.call(vendor, odm)

    def test_invalid_secondary_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError, "odm.build.prop"):
            self.call("36", "bogus")

    def test_invalid_vendor_does_not_fall_through_to_valid_odm(self):
        with self.assertRaisesRegex(ValueError, "vendor.build.prop"):
            self.call("bogus", "36")

    def test_noncanonical_or_out_of_range_values_fail(self):
        bad = ("0", "00", "036", "+36", "-36", "0x24", "0X24", " 36", "36 ", "36\n", "36\0",
               "٣٦", "３６", "36.0", "36e0", "36k", "18446744073709551616", "9" * 21)
        for value in bad:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Invalid"):
                self.call(value, "36")

    def test_nonstrings_are_not_coerced(self):
        for value in (0, 36, True, False, 36.0, b"36", [], {}, object()):
            with self.subTest(value=repr(value)), self.assertRaisesRegex(ValueError, "Invalid"):
                self.call(value, "36")

    def test_integer_conversion_is_bounded_before_parsing(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            self.call("9" * 10_000, "36")

    def test_uint64_representation_boundaries(self):
        for value in ("1", "18446744073709551615"):
            with self.subTest(value=value):
                self.assertEqual(["--property", PROPERTY + "=" + value], self.call(value))
                self.assertEqual(["--property", PROPERTY + "=" + value], self.call(None, value))

    def test_input_objects_are_not_modified(self):
        vendor, odm = Props(None), Props("36")
        info = {"vendor.build.prop": vendor, "odm.build.prop": odm}
        self.functions["after"](info)
        self.assertIsNone(vendor.value)
        self.assertEqual("36", odm.value)
        self.assertEqual(2, len(info))

    def test_malformed_container_fails(self):
        with self.assertRaises(AttributeError):
            self.functions["after"]({"vendor.build.prop": {PROPERTY: "36"}, "odm.build.prop": Props("36")})

    def test_only_shipping_function_differs(self):
        before, after, _ = patch_sources()
        self.assertEqual(api._outside_function(before), api._outside_function(after))
        self.assertNotEqual(ast.dump(api._function(before)), ast.dump(api._function(after)))


class SourceGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.controls, self.before_root, self.after_root = [self.root / name for name in ("controls", "before", "after")]
        before, after, patch = patch_sources()
        self.record = json.loads((WORKSPACE / api.CONTRACT).read_bytes())
        self.record["source_files"][0].update(before=api.identity(before), after=api.identity(after))
        common = b"# inert property-reader sentinel; not an Android implementation\n"
        self.record["semantic_files"][0].update(api.identity(common))
        self.write(self.controls / api.PATCH, patch)
        self.write(self.before_root / api.SOURCE, before)
        self.write(self.after_root / api.SOURCE, after)
        self.write(self.after_root / api.COMMON, common)
        self.save_contract()
        self.enterContext(mock.patch.object(api, "ROOT", self.controls))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native processes forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))

    @staticmethod
    def write(path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def save_contract(self):
        self.write(self.controls / api.CONTRACT, (json.dumps(self.record, indent=2) + "\n").encode())

    def check(self):
        return api.check_source(self.after_root, before_source_tree=self.before_root)

    def test_complete_source_identity_and_patch_replay(self):
        result = self.check()
        self.assertTrue(result["patch_replayed"])
        self.assertTrue(result["only_named_function_changed"])
        self.assertFalse(result["scope"]["native_compatibility_verified"])
        self.assertFalse(result["whole_source_tree_verified"])

    def test_changed_source_rejected(self):
        (self.after_root / api.SOURCE).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_property_reader_rejected(self):
        (self.after_root / api.COMMON).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_before_source_rejected(self):
        (self.before_root / api.SOURCE).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_patch_rejected(self):
        with (self.controls / api.PATCH).open("ab") as out:
            out.write(b"extra patch bytes\n")
        with self.assertRaises(ValueError):
            self.check()

    def test_consistent_concurrent_revision_cannot_report_stale_source_hashes(self):
        real_contract = api.contract
        calls = 0

        def changing_contract():
            nonlocal calls
            calls += 1
            if calls == 3:
                # Both revisions individually replay and have the same behavior.
                # Changing the patch, contract and output together must still
                # invalidate a report prepared from the earlier source bytes.
                patch_path = self.controls / api.PATCH
                source_path = self.after_root / api.SOURCE
                new_patch = patch_path.read_bytes().replace(b"+  levels = {}\n", b"+  levels = dict()\n")
                new_source = source_path.read_bytes().replace(b"  levels = {}\n", b"  levels = dict()\n")
                self.assertNotEqual(new_patch, patch_path.read_bytes())
                self.assertNotEqual(new_source, source_path.read_bytes())
                self.write(patch_path, new_patch)
                self.write(source_path, new_source)
                self.record["patch"].update(api.identity(new_patch))
                self.record["source_files"][0]["after"] = api.identity(new_source)
                self.save_contract()
            return real_contract()

        with mock.patch.object(api, "contract", changing_contract):
            with self.assertRaisesRegex(api.ShippingApiError, "source or contract changed"):
                self.check()
        self.assertTrue(self.check()["patch_replayed"])

    def test_conflicting_contract_scope_rejected(self):
        self.record["scope"]["native_compatibility_verified"] = True
        self.save_contract()
        with self.assertRaisesRegex(api.ShippingApiError, "contract or scope"):
            self.check()

    def test_changed_branch_rejected(self):
        self.record["project"]["branch"] = "unreviewed"
        self.save_contract()
        with self.assertRaisesRegex(api.ShippingApiError, "contract or scope"):
            self.check()

    def test_changed_fallback_semantics_rejected(self):
        self.record["semantics"]["fallback_when_vendor_property_missing"] = "system"
        self.save_contract()
        with self.assertRaisesRegex(api.ShippingApiError, "contract or scope"):
            self.check()

    def test_missing_or_duplicate_source_row_rejected(self):
        original = copy.deepcopy(self.record["source_files"])
        for rows in ([], original + original):
            self.record["source_files"] = rows
            self.save_contract()
            with self.subTest(rows=len(rows)), self.assertRaises(api.ShippingApiError):
                self.check()

    def test_symlink_source_rejected(self):
        path = self.after_root / api.SOURCE
        target = self.root / "original"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises((ValueError, OSError)):
            self.check()


if __name__ == "__main__":
    unittest.main()
