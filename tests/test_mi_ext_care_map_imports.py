"""Exercise the actual inactive 0014 source transition without private inputs.

Synthetic property bytes replace only the 22 content-hash fixtures. The public
path table, selector grammar, real patched functions and all safety checks run.
An ignored, separate replay checks the authentic captured bytes. Neither is a
native init execution, a final SYSTEM artifact or a runtime selector observation.
"""

import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_mi_ext_care_map as base
from scripts.partition_build_props import _apply_patch


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/evolution/0014-direct-mi-ext-care-map-imports.patch"
CONTRACT = ROOT / "patches/evolution/direct-mi-ext-care-map-imports.json"
VALUE = "factory-system-fingerprint-odm-imports-v2"
PREFIX = "nezha_care_map_odm_import_"
IMPORTS = (
    "import /odm/etc/${ro.boot.product.hardware.sku}_${ro.boot.ptcountrycode}_build.prop",
    "import /odm/etc/${ro.boot.product.hardware.sku}_${ro.boot.hwversion}.prop",
)


def source():
    return _apply_patch(base.public_hunk(), PATCH.read_bytes())


def make_namespace():
    namespace = base.make_namespace()
    exec(compile(ast.Module(body=base.functions(source()), type_ignores=[]),
                 "<actual 0014 care-map import successor>", "exec"), namespace)
    return namespace


def synthetic_importer():
    lines = ["# Synthetic unit-test content; never an artifact fingerprint"] * 480
    lines[31:33] = IMPORTS
    lines[479] = "ro.vendor.mitee_support"
    return ("\n".join(lines) + "\n").encode()


class SourceContractTests(unittest.TestCase):
    def test_explicit_single_file_successor_preserves_original_contract(self):
        contract = json.loads(CONTRACT.read_bytes())
        old = json.loads(base.CONTRACT.read_bytes())
        self.assertEqual(contract["patch"], {"path": str(PATCH.relative_to(ROOT)),
                                             **base.identity(PATCH.read_bytes())})
        self.assertEqual(contract["requires_predecessor"], {
            "path": str(base.CONTRACT.relative_to(ROOT)),
            **base.identity(base.CONTRACT.read_bytes())})
        self.assertEqual(contract["source_files"][0]["before"], old["source_files"][0]["after"])
        self.assertEqual(len(contract["source_files"]), 1)
        self.assertEqual(contract["selection"]["value"], VALUE)
        self.assertEqual(contract["selection"]["old_value"], base.VALUE)
        self.assertFalse(contract["validation_scope"]["selected_in_active_composition"])
        self.assertFalse(contract["validation_scope"]["runtime_selector_tuple_verified"])
        self.assertFalse(contract["validation_scope"]["final_system_artifact_verified"])

    def test_public_original_identity_table_is_exactly_bound(self):
        namespace = make_namespace()
        rows = namespace["_NEZHA_CARE_MAP_ODM_PROPERTIES"]
        contract = json.loads(CONTRACT.read_bytes())
        self.assertEqual([{"path": name, "size_bytes": size, "sha256": digest}
                          for name, size, digest in rows], contract["odm_property_files"])
        self.assertEqual(len(rows), 22)
        self.assertEqual(sum(row[1] for row in rows), 30300)
        self.assertEqual(len({row[0] for row in rows}), 22)

    def test_unrelated_image_range_coverage_and_output_functions_are_identical(self):
        old = {node.name: ast.dump(node) for node in base.functions(base.public_hunk())
               if isinstance(node, ast.FunctionDef)}
        new = {node.name: ast.dump(node) for node in base.functions(source())
               if isinstance(node, ast.FunctionDef)}
        changed = {name for name in old if old[name] != new[name]}
        self.assertEqual(changed, {"_NezhaCareMapSystemFingerprint", "AddCareMapForAbOta"})
        self.assertEqual(set(new) - set(old), {
            "_NezhaCareMapPropertyBytes", "_NezhaCareMapOdmStatements",
            "_NezhaCareMapOdmImports", "_NezhaCareMapRecheckOdmImports"})


class ImportCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="care-map-import-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.ns = make_namespace()
        self.options = self.ns["OPTIONS"]
        self.options.input_tmp = str(self.root)
        self.options.info_dict = {base.SELECTOR: VALUE,
            PREFIX + "sku": "nezha", PREFIX + "country": "ru", PREFIX + "hwversion": "5.0.8"}
        for process in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(process, side_effect=AssertionError("offline: " + process)))
        table = []
        for relative, _, _ in self.ns["_NEZHA_CARE_MAP_ODM_PROPERTIES"]:
            data = synthetic_importer() if relative == "ODM/etc/build.prop" else b"ro.vendor.test.fixture=1\n"
            self.write(relative, data)
            table.append((relative, len(data), hashlib.sha256(data).hexdigest()))
        # Explicit content-fixture seam; authentic replay is separate and uses
        # the unmodified public identity table against all original 22 files.
        self.ns["_NEZHA_CARE_MAP_ODM_PROPERTIES"] = tuple(table)

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw.encode() if isinstance(raw, str) else raw)
        return path

    def closure(self):
        return self.ns["_NezhaCareMapOdmImports"]()

    def marker(self):
        return self.ns["_NezhaCareMapSystemFingerprint"]()

    def system_inputs(self):
        for name in base.CANONICAL:
            if name != "ODM/etc/build.prop":
                self.write(name, "ro.test.fixture=1\n")
        self.write("SYSTEM/build.prop", base.PROPERTY + "=" + base.FINGERPRINT + "\n")
        self.options.info_dict["system.build.prop"] = base.Props({base.PROPERTY: base.FINGERPRINT})


class SelectorTests(ImportCase):
    def test_two_exact_imports_resolve_without_rewriting_originals(self):
        before = {p: (self.root / p).read_bytes() for p, _, _ in self.ns["_NEZHA_CARE_MAP_ODM_PROPERTIES"]}
        closure = self.closure()
        self.assertEqual(closure["imports"], [
            {"path": "/odm/etc/nezha_ru_build.prop", "outcome": "captured-file"},
            {"path": "/odm/etc/nezha_5.0.8.prop", "outcome": "captured-file"}])
        self.assertEqual(set(closure["selectors"]), {
            "ro.boot.product.hardware.sku", "ro.boot.ptcountrycode", "ro.boot.hwversion"})
        self.assertEqual(len(closure["inputs"]), 22)
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in before})

    def test_all_54_captured_combinations_have_two_existing_targets(self):
        hardware = [Path(p).name[len("nezha_"):-len(".prop")]
                    for p, _, _ in self.ns["_NEZHA_CARE_MAP_ODM_PROPERTIES"]
                    if p != "ODM/etc/build.prop" and not p.endswith("_build.prop")]
        self.assertEqual(len(hardware), 18)
        for country in ("in", "ru", "tr"):
            for version in hardware:
                with self.subTest(country=country, hwversion=version):
                    self.options.info_dict.update({PREFIX + "country": country, PREFIX + "hwversion": version})
                    self.assertEqual([x["outcome"] for x in self.closure()["imports"]],
                                     ["captured-file", "captured-file"])

    def test_unlisted_safe_basename_is_explicitly_absent_not_loaded(self):
        self.options.info_dict[PREFIX + "country"] = "unlisted_test_country"
        self.assertEqual(self.closure()["imports"][0], {
            "path": "/odm/etc/nezha_unlisted_test_country_build.prop",
            "outcome": "inventory-proven-absent"})

    def test_all_three_selector_declarations_are_required(self):
        for key in ("sku", "country", "hwversion"):
            value = self.options.info_dict.pop(PREFIX + key)
            with self.assertRaisesRegex(base.ExternalError, "exactly three declared"):
                self.closure()
            self.options.info_dict[PREFIX + key] = value

    def test_unknown_selector_field_fails(self):
        self.options.info_dict[PREFIX + "countrycode"] = "ru"
        with self.assertRaisesRegex(base.ExternalError, "exactly three declared"):
            self.closure()

    def test_values_cannot_escape_or_hide_native_expansion_semantics(self):
        for value in ("", None, True, 1, "unknown", ".", "..", "../ru", "ru/../x", "ru\\x",
                      "${ro.boot.hwversion}", "$x", "ru extra.filter", "ru\t", "ru\n", "é", "a" * 93):
            with self.subTest(value=value):
                self.options.info_dict[PREFIX + "country"] = value
                with self.assertRaisesRegex(base.ExternalError, "Unsafe or empty"):
                    self.closure()

    def test_different_sku_is_not_inferred_from_a_filename(self):
        self.options.info_dict[PREFIX + "sku"] = "another_device"
        with self.assertRaisesRegex(base.ExternalError, "hardware SKU"):
            self.closure()

    def test_empty_selector_does_not_count_native_expansion_failure_as_a_load(self):
        self.options.info_dict[PREFIX + "hwversion"] = ""
        with self.assertRaisesRegex(base.ExternalError, "Unsafe or empty"):
            self.closure()


class OriginalInputTests(ImportCase):
    def test_missing_unselected_candidate_fails(self):
        (self.root / "ODM/etc/nezha_in_build.prop").unlink()
        with self.assertRaisesRegex(base.ExternalError, "Missing.*nezha_in_build"):
            self.closure()

    def test_changed_unselected_candidate_fails(self):
        self.write("ODM/etc/nezha_in_build.prop", "ro.vendor.test.fixture=2\n")
        with self.assertRaisesRegex(base.ExternalError, "differs from its captured original"):
            self.closure()

    def test_changed_importer_cannot_admit_another_import_or_marker(self):
        path = self.root / "ODM/etc/build.prop"
        for suffix in (b"import /system/build.prop\n", (base.PROPERTY + "=bad\n").encode()):
            path.write_bytes(synthetic_importer() + suffix)
            with self.assertRaisesRegex(base.ExternalError, "differs from its captured original"):
                self.closure()

    def test_extra_unselected_property_file_rejects_incomplete_projection(self):
        self.write("ODM/etc/nezha_unselected_extra.prop", "ro.foo=bar\n")
        with self.assertRaisesRegex(base.ExternalError, "complete captured closure"):
            self.closure()

    def test_extra_selected_file_cannot_be_treated_as_proven_absent(self):
        self.options.info_dict[PREFIX + "country"] = "extra"
        self.write("ODM/etc/nezha_extra_build.prop", "ro.foo=bar\n")
        with self.assertRaisesRegex(base.ExternalError, "complete captured closure"):
            self.closure()

    def test_symlinked_captured_file_rejected(self):
        path = self.root / "ODM/etc/nezha_ru_build.prop"
        path.unlink()
        path.symlink_to("nezha_in_build.prop")
        with self.assertRaisesRegex(base.ExternalError, "Symlinked"):
            self.closure()

    def test_symlinked_property_parent_rejected(self):
        path = self.root / "ODM/etc"
        path.rename(self.root / "copied-etc")
        path.symlink_to(self.root / "copied-etc", target_is_directory=True)
        with self.assertRaisesRegex(base.ExternalError, "Symlinked"):
            self.closure()

    def test_dangling_extra_import_is_not_absence(self):
        self.options.info_dict[PREFIX + "country"] = "extra"
        (self.root / "ODM/etc/nezha_extra_build.prop").symlink_to("missing")
        with self.assertRaisesRegex(base.ExternalError, "complete captured closure"):
            self.closure()

    def test_same_bytes_in_distinct_files_are_valid_but_hardlinks_are_not(self):
        self.closure()
        path = self.root / "ODM/etc/nezha_ru_build.prop"
        path.unlink()
        os.link(self.root / "ODM/etc/nezha_in_build.prop", path)
        with self.assertRaisesRegex(base.ExternalError, "aliased"):
            self.closure()

    def test_non_regular_candidate_rejected(self):
        path = self.root / "ODM/etc/nezha_ru_build.prop"
        path.unlink()
        path.mkdir()
        with self.assertRaisesRegex(base.ExternalError, "Non-regular"):
            self.closure()

    def test_extra_property_directory_rejected(self):
        (self.root / "ODM/etc/extra.prop").mkdir()
        with self.assertRaisesRegex(base.ExternalError, "complete captured closure"):
            self.closure()

    def test_leaf_reader_detects_file_changed_after_open(self):
        real = os.fdopen
        path = self.root / "ODM/etc/build.prop"
        def changed(*args, **kwargs):
            result = real(*args, **kwargs)
            path.write_bytes(path.read_bytes() + b"# changed\n")
            return result
        with mock.patch.object(os, "fdopen", side_effect=changed):
            with self.assertRaisesRegex(base.ExternalError, "changed while reading"):
                self.ns["_NezhaCareMapPropertyBytes"]("ODM/etc/build.prop")


class NativeGrammarTests(ImportCase):
    def test_exact_bare_factory_key_is_native_ignored_and_only_here(self):
        parser = self.ns["_NezhaCareMapOdmStatements"]
        self.assertEqual(parser(synthetic_importer(), "ODM/etc/build.prop"),
                         [*IMPORTS, "ro.vendor.mitee_support"])
        with self.assertRaisesRegex(base.ExternalError, "nested"):
            parser(b"ro.vendor.mitee_support\n", "ODM/etc/nezha_ru_build.prop")

    def test_filtered_nested_and_additional_imports_fail(self):
        parser = self.ns["_NezhaCareMapOdmStatements"]
        for raw in (b"import /odm/etc/x.prop ro.foo.*\n", b"import /system/build.prop\n",
                    b"import\t/odm/etc/x.prop\n", b"import /odm/etc/${missing}.prop\n"):
            with self.subTest(raw=raw), self.assertRaisesRegex(base.ExternalError, "nested"):
                parser(raw, "ODM/etc/nezha_ru_build.prop")

    def test_marker_assignment_in_leaf_fails_before_permission_assumptions(self):
        parser = self.ns["_NezhaCareMapOdmStatements"]
        for raw in ((base.PROPERTY + "=different\n").encode(),
                    (" \t" + base.PROPERTY + " \t=\t" + base.FINGERPRINT).encode()):
            with self.assertRaisesRegex(base.ExternalError, "SYSTEM fingerprint"):
                parser(raw, "ODM/etc/nezha_ru_build.prop")

    def test_lf_only_parser_does_not_promote_unicode_separators(self):
        parser = self.ns["_NezhaCareMapOdmStatements"]
        raw = ("ro.vendor.foo=x\u2028" + base.PROPERTY + "=hidden\n").encode()
        self.assertEqual(parser(raw, "ODM/etc/nezha_ru_build.prop"), [])
        # Native sees a single assignment to ro.vendor.foo, not a second marker.
        for raw in (b"ro.foo=x\0", b"ro.foo=x\r\n", b"ro.foo=x\v", b"\xff"):
            with self.assertRaises(base.ExternalError):
                parser(raw, "ODM/etc/nezha_ru_build.prop")


class MarkerAndLegacyTests(ImportCase):
    def test_v2_uses_genuine_system_pair_after_qualifying_original_closure(self):
        self.system_inputs()
        self.assertEqual(self.marker(), [base.PROPERTY, base.FINGERPRINT])
        self.assertFalse((self.root / "MI_EXT").exists())

    def test_final_system_is_still_required(self):
        self.system_inputs()
        (self.root / "SYSTEM/build.prop").unlink()
        with self.assertRaisesRegex(base.ExternalError, "Missing.*SYSTEM/build.prop"):
            self.marker()

    def test_missing_or_unknown_final_marker_cannot_be_invented(self):
        self.system_inputs()
        for raw in ("ro.test.fixture=1\n", base.PROPERTY + "=unknown\n", base.PROPERTY + "=\n"):
            self.write("SYSTEM/build.prop", raw)
            with self.assertRaisesRegex(base.ExternalError, "Missing or invalid canonical"):
                self.marker()

    def test_preferred_system_alias_and_packaging_reader_must_agree(self):
        self.system_inputs()
        self.write("SYSTEM/etc/build.prop", base.PROPERTY + "=another\n")
        with self.assertRaisesRegex(base.ExternalError, "Conflicting"):
            self.marker()
        (self.root / "SYSTEM/etc/build.prop").unlink()
        self.options.info_dict["system.build.prop"] = base.Props({base.PROPERTY: "another"})
        with self.assertRaisesRegex(base.ExternalError, "Packaged SYSTEM fingerprint"):
            self.marker()

    def test_other_partition_imports_remain_unqualified(self):
        self.system_inputs()
        self.write("PRODUCT/etc/build.prop", "import /odm/etc/nezha_ru_build.prop\n")
        with self.assertRaisesRegex(base.ExternalError, "Unqualified.*PRODUCT"):
            self.marker()

    def test_old_selector_still_rejects_authentic_shaped_odm_imports(self):
        self.system_inputs()
        self.options.info_dict[base.SELECTOR] = base.VALUE
        with self.assertRaisesRegex(base.ExternalError, "Unqualified.*ODM/etc/build.prop"):
            self.marker()

    def test_original_no_import_profile_behavior_does_not_call_v2(self):
        self.system_inputs()
        self.options.info_dict[base.SELECTOR] = base.VALUE
        self.write("ODM/etc/build.prop", "ro.test.fixture=1\n")
        self.ns["_NezhaCareMapOdmImports"] = mock.Mock(side_effect=AssertionError("v2 not selected"))
        self.assertEqual(self.marker(), [base.PROPERTY, base.FINGERPRINT])
        self.ns["_NezhaCareMapOdmImports"].assert_not_called()

    def test_unknown_top_level_selector_cannot_activate_v2(self):
        self.options.info_dict[base.SELECTOR] = "factory-system-fingerprint-odm-imports-v3"
        with self.assertRaisesRegex(base.ExternalError, "Unknown Nezha"):
            self.ns["AddCareMapForAbOta"]("unused", [], {})

    def test_v2_still_uses_existing_full_logical_set_guard(self):
        with self.assertRaisesRegex(base.ExternalError, "complete unique A/B logical set"):
            self.ns["AddCareMapForAbOta"]("unused", [], {})

    def test_changed_original_after_closure_fails_before_skipping_imports(self):
        self.system_inputs()
        original = self.ns["_NezhaCareMapOdmImports"]
        def changed():
            closure = original()
            path = self.root / "ODM/etc/build.prop"
            path.write_bytes(path.read_bytes() + b"# changed after closure\n")
            return closure
        self.ns["_NezhaCareMapOdmImports"] = changed
        with self.assertRaisesRegex(base.ExternalError, "importer changed"):
            self.marker()

    def test_changed_leaf_or_selector_during_marker_check_fails_final_recheck(self):
        self.system_inputs()
        testcase = self
        class MutatingProps:
            def GetProp(self, key):
                testcase.options.info_dict[PREFIX + "country"] = "in"
                return base.FINGERPRINT
        self.options.info_dict["system.build.prop"] = MutatingProps()
        with self.assertRaisesRegex(base.ExternalError, "closure changed"):
            self.marker()
        class MutatingFileProps:
            def GetProp(self, key):
                testcase.write("ODM/etc/nezha_in_build.prop", "ro.vendor.test.fixture=2\n")
                return base.FINGERPRINT
        self.options.info_dict["system.build.prop"] = MutatingFileProps()
        with self.assertRaisesRegex(base.ExternalError, "captured original"):
            self.marker()


if __name__ == "__main__":
    unittest.main()
