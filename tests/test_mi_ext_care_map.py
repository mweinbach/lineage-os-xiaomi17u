"""Execute the new public source patch offline with explicit native-tool seams.

No private images or source checkout are needed. AVB parsing, RangeSet and the
protobuf process are doubles here; the ignored captured-source probe uses the
real pinned AVB parser and RangeSet separately. Neither is a native build or a
runtime test. Legacy tests are retained, not bypassed by a skip decorator.
"""

import ast
import copy
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile
import types
import unittest
from unittest import mock
import zipfile

from scripts.partition_build_props import _apply_patch


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/evolution/0013-direct-mi-ext-care-map.patch"
CONTRACT = ROOT / "patches/evolution/direct-mi-ext-care-map.json"
SELECTOR = "nezha_direct_mi_ext_care_map"
VALUE = "factory-system-fingerprint-v1"
PROPERTY = "ro.system.build.fingerprint"
FINGERPRINT = "example/nezha/nezha:16/BP4A/test:user/test-keys"
REQUIRED = ["system", "system_ext", "product", "vendor", "odm",
            "vendor_dlkm", "system_dlkm", "mi_ext"]
LEGACY = ["system", "vendor", "product", "system_ext", "odm",
          "vendor_dlkm", "odm_dlkm", "system_dlkm"]
CANONICAL = ["SYSTEM/build.prop", "SYSTEM_EXT/etc/build.prop",
             "PRODUCT/etc/build.prop", "VENDOR/build.prop", "ODM/etc/build.prop",
             "VENDOR_DLKM/etc/build.prop", "SYSTEM_DLKM/etc/build.prop",
             "VENDOR/odm_dlkm/etc/build.prop"]


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def public_hunk(after=True):
    lines = PATCH.read_text().splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("@@ ")]
    if len(starts) != 1 or not lines[starts[0]].startswith("@@ -1,"):
        raise AssertionError("expected one self-contained reviewed source hunk")
    markers = (" ", "+") if after else (" ", "-")
    return "".join(line[1:] for line in lines[starts[0] + 1:]
                   if line.startswith(markers)).encode()


def functions(raw):
    text = raw.decode()
    start = text.index("def ParseAvbFooter(")
    end = text.index("\ndef AddSystem(", start)
    return ast.parse(text[start:end]).body


class ExternalError(RuntimeError):
    pass


class Props:
    def __init__(self, values):
        self.values = values

    def GetProp(self, key):
        return self.values.get(key)


class RangeSetDouble:
    """Small interface double; the captured-source probe checks actual ranges."""
    def __init__(self, value=None, data=None):
        if data is None:
            match = re.fullmatch(r"0-(\d+)", value)
            if not match:
                raise AssertionError("unexpected range seam input")
            data = [0, int(match.group(1)) + 1]
        self.data = tuple(data)
        self.monotonic = all(a < b for a, b in zip(self.data, self.data[1:]))

    def __bool__(self):
        return bool(self.data)

    @classmethod
    def parse_raw(cls, value):
        values = [int(part) for part in value.split(",")]
        assert values[0] == len(values) - 1 and values[0] % 2 == 0
        return cls(data=values[1:])

    def to_string_raw(self):
        return ",".join(str(value) for value in (len(self.data), *self.data))


class HashtreeDouble:
    """Encode only the already public original mi_ext descriptor metadata."""
    def __init__(self):
        self.partition_name = "mi_ext"
        self.dm_verity_version = 1
        self.image_size = self.tree_offset = 109445120
        self.tree_size = 868352
        self.fec_offset = 110313472
        self.fec_size = 876544
        self.data_block_size = self.hash_block_size = 4096
        self.fec_num_roots = 2
        self.flags = 0
        self.hash_algorithm = "sha256"
        self.salt = bytes.fromhex("4dcefe592c7dbe6d5ede4a7f3de84b31ff21ed0d627885fb4845e36fc8101c03")
        self.root_digest = bytes.fromhex("d751fdcbe81abcb481ba8931567c8782d6c6e193dea8a40f52abd82e2fd776f4")

    def encode(self):
        name = self.partition_name.encode()
        body = struct.pack("!QQLQQQLLLQQ32sLLLL60s", 1, 240,
                           self.dm_verity_version, self.image_size, self.tree_offset,
                           self.tree_size, self.data_block_size, self.hash_block_size,
                           self.fec_num_roots, self.fec_offset, self.fec_size,
                           self.hash_algorithm.encode(), len(name), len(self.salt),
                           len(self.root_digest), self.flags, bytes(60))
        body += name + self.salt + self.root_digest
        return body + bytes((-len(body)) % 8)


def make_namespace(after=True):
    namespace = {
        "os": os, "stat": stat, "hashlib": hashlib, "tempfile": tempfile,
        "shutil": shutil, "zipfile": zipfile, "ExternalError": ExternalError,
        "logger": logging.getLogger("mi-ext-care-map-tests"),
        "PARTITIONS_WITH_CARE_MAP": LEGACY[:],
        "rangelib": types.SimpleNamespace(RangeSet=RangeSetDouble),
        "avbtool": types.SimpleNamespace(AvbFooter=types.SimpleNamespace(SIZE=64),
                                         AvbHashtreeDescriptor=HashtreeDouble),
        "OPTIONS": types.SimpleNamespace(info_dict={}, input_tmp=None,
                                          replace_updated_files_list=[]),
    }
    exec(compile(ast.Module(body=functions(public_hunk(after)), type_ignores=[]),
                 "<actual direct-mi-ext-care-map patch>", "exec"), namespace)
    return namespace


class SourceContractTests(unittest.TestCase):
    def test_patch_is_exactly_bound_to_one_pinned_source_transition(self):
        contract = json.loads(CONTRACT.read_bytes())
        self.assertEqual(contract["patch"], {"path": str(PATCH.relative_to(ROOT)),
                                              **identity(PATCH.read_bytes())})
        self.assertEqual(contract["project"]["commit"], "a438ca40c6ed779042f806142b1165ba1360a7b2")
        self.assertEqual(len(contract["source_files"]), 1)
        self.assertEqual(contract["source_files"][0]["path"],
                         "build/make/tools/releasetools/add_img_to_target_files.py")
        self.assertEqual(contract["source_files"][0]["before"], {
            "sha256": "ef2e4014238ad323e8157a3bf80190d1795f01b6dd0c087b5e8c2cc167a43c51",
            "size_bytes": 48289})
        self.assertEqual(_apply_patch(public_hunk(False), PATCH.read_bytes()), public_hunk())
        self.assertEqual(re.findall(rb"^--- (.+)$", PATCH.read_bytes(), re.M),
                         [b"a/tools/releasetools/add_img_to_target_files.py"])

    def test_unmodified_upstream_range_and_footer_functions_remain_identical(self):
        before = {node.name: ast.dump(node) for node in functions(public_hunk(False))}
        after = {node.name: ast.dump(node) for node in functions(public_hunk())}
        self.assertEqual(before["ParseAvbFooter"], after["ParseAvbFooter"])
        self.assertEqual(before["GetCareMap"], after["GetCareMap"])
        self.assertEqual(set(after) - set(before), {
            "_NezhaCareMapPath", "_NezhaCareMapSystemFingerprint", "_NezhaCareMapAvbImage",
            "_NezhaDirectMiExtCareMap", "_CheckNezhaCareMapCoverage"})

    def test_public_descriptor_fixture_matches_preserved_identity(self):
        self.assertEqual(hashlib.sha256(HashtreeDouble().encode()).hexdigest(),
                         "c7251f78926feb64f83671a61b4a164f9851948cf12291f1106069f8fac35269")
        config = json.loads((ROOT / "config/nezha-mi-ext.json").read_bytes())
        contract = json.loads(CONTRACT.read_bytes())
        self.assertEqual(contract["retained_image"], {
            "sha256": config["image"]["sha256"], "size_bytes": config["image"]["size_bytes"]})
        self.assertEqual(contract["selection"], {"misc_info_key": SELECTOR, "value": VALUE,
                                                 "absent_keeps_legacy_behavior": True})


class CareMapTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="care-map-offline-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.namespace = make_namespace()
        self.options = self.namespace["OPTIONS"]
        self.options.input_tmp = str(self.root)
        for name in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(name, side_effect=AssertionError("offline test: " + name)))

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw.encode() if isinstance(raw, str) else raw)
        return path

    def property_fixture(self):
        for relative in CANONICAL:
            self.write(relative, "ro.example.fixture=true\n")
        self.write("SYSTEM/build.prop", PROPERTY + "=" + FINGERPRINT + "\n")
        self.options.info_dict["system.build.prop"] = Props({PROPERTY: FINGERPRINT})

    def selected_info(self):
        self.property_fixture()
        self.options.info_dict.update({SELECTOR: VALUE, "ab_update": "true", "avb_enable": "true",
            "dynamic_partition_list": " ".join(REQUIRED),
            "avb_custom_images_partition_list": "mi_ext",
            "avb_custom_images_direct_partition_list": "mi_ext",
            "avb_mi_ext_image_list": "mi_ext.img"})
        return self.options.info_dict


class SystemMarkerTests(CareMapTestCase):
    def marker(self):
        return self.namespace["_NezhaCareMapSystemFingerprint"]()

    def test_canonical_real_system_pair_is_used_without_synthesis(self):
        self.property_fixture()
        self.assertEqual([PROPERTY, FINGERPRINT], self.marker())
        self.assertFalse((self.root / "MI_EXT").exists())

    def test_matching_etc_alias_and_later_definition_are_accepted(self):
        self.property_fixture()
        for relative in ("SYSTEM/etc/build.prop", "VENDOR/default.prop"):
            self.write(relative, PROPERTY + "=" + FINGERPRINT + "\n")
        self.assertEqual([PROPERTY, FINGERPRINT], self.marker())

    def test_missing_runtime_canonical_path_cannot_use_preferred_alias(self):
        self.property_fixture()
        (self.root / "SYSTEM/build.prop").rename(self.root / "SYSTEM/other.prop")
        self.write("SYSTEM/etc/build.prop", PROPERTY + "=" + FINGERPRINT)
        with self.assertRaisesRegex(ExternalError, "Missing.*SYSTEM/build.prop"):
            self.marker()

    def test_missing_named_boot_default_input_fails(self):
        self.property_fixture()
        (self.root / "VENDOR/odm_dlkm/etc/build.prop").unlink()
        with self.assertRaisesRegex(ExternalError, "Missing.*odm_dlkm"):
            self.marker()

    def test_missing_empty_unknown_thumbprint_or_computed_fingerprint_fails(self):
        self.property_fixture()
        for line in ("", PROPERTY + "=", PROPERTY + "=unknown",
                     "ro.system.build.thumbprint=example", "ro.build.fingerprint=example",
                     PROPERTY + "=value with spaces", PROPERTY + "=emoji😀"):
            with self.subTest(line=line):
                self.write("SYSTEM/build.prop", line)
                with self.assertRaisesRegex(ExternalError, "canonical SYSTEM fingerprint"):
                    self.marker()

    def test_conflicting_etc_or_later_vendor_definition_fails(self):
        self.property_fixture()
        for relative in ("SYSTEM/etc/build.prop", "VENDOR/default.prop", "ODM/build.prop"):
            with self.subTest(relative=relative):
                self.write(relative, PROPERTY + "=different\n")
                with self.assertRaisesRegex(ExternalError, "Conflicting"):
                    self.marker()
                (self.root / relative).unlink()

    def test_preferred_etc_without_fingerprint_fails(self):
        self.property_fixture()
        self.write("SYSTEM/etc/build.prop", "ro.example=true\n")
        with self.assertRaisesRegex(ExternalError, "Preferred SYSTEM property path"):
            self.marker()

    def test_loader_pair_must_match_canonical_file(self):
        self.property_fixture()
        for props in (None, Props({PROPERTY: "different"}), Props({})):
            self.options.info_dict["system.build.prop"] = props
            with self.subTest(props=props), self.assertRaisesRegex(ExternalError, "Packaged SYSTEM"):
                self.marker()

    def test_duplicate_identical_fingerprint_is_still_ambiguous(self):
        self.property_fixture()
        self.write("SYSTEM/build.prop", (PROPERTY + "=" + FINGERPRINT + "\n") * 2)
        with self.assertRaisesRegex(ExternalError, "Duplicate"):
            self.marker()

    def test_any_unqualified_import_fails_even_without_observed_conflict(self):
        self.property_fixture()
        for line in ("import /odm/etc/region_${ro.boot.hwc}.prop",
                     "import /odm/etc/foo.prop ro.product.*", "import /vendor/other.prop"):
            with self.subTest(line=line):
                self.write("ODM/etc/build.prop", line + "\n")
                with self.assertRaisesRegex(ExternalError, "Unqualified.*import.*ODM"):
                    self.marker()

    def test_symlinked_canonical_file_or_parent_fails(self):
        self.property_fixture()
        original = self.root / "SYSTEM/build.prop"
        original.rename(self.root / "fingerprint.prop")
        original.symlink_to(self.root / "fingerprint.prop")
        with self.assertRaisesRegex(ExternalError, "Symlinked"):
            self.marker()
        original.unlink()
        (self.root / "fingerprint.prop").rename(original)
        (self.root / "ODM/etc").rename(self.root / "odm-etc")
        (self.root / "ODM/etc").symlink_to(self.root / "odm-etc", target_is_directory=True)
        with self.assertRaisesRegex(ExternalError, "Symlinked"):
            self.marker()

    def test_directory_property_and_non_directory_alias_parent_fail(self):
        self.property_fixture()
        (self.root / "SYSTEM/build.prop").unlink()
        (self.root / "SYSTEM/build.prop").mkdir()
        with self.assertRaisesRegex(ExternalError, "Non-regular"):
            self.marker()
        (self.root / "SYSTEM/build.prop").rmdir()
        self.write("SYSTEM/build.prop", PROPERTY + "=" + FINGERPRINT)
        self.write("SYSTEM/etc", "not a directory")
        with self.assertRaisesRegex(ExternalError, "Non-directory"):
            self.marker()

    def test_bounded_malformed_property_files_fail(self):
        self.property_fixture()
        for raw in (b"x" * (1024 * 1024 + 1), b"a=b\0c", b"a=b\r\n", b"not-a-property"):
            with self.subTest(size=len(raw)):
                self.write("ODM/etc/build.prop", raw)
                with self.assertRaisesRegex(ExternalError, "Invalid"):
                    self.marker()

    def test_native_lf_only_parsing_cannot_hide_a_later_conflict(self):
        self.property_fixture()
        for separator in ("\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                self.write("PRODUCT/etc/build.prop", PROPERTY + "=" + FINGERPRINT + separator + "foo=bar\n")
                with self.assertRaises(ExternalError):
                    self.marker()

    def test_unicode_whitespace_is_not_normalized_into_the_canonical_pair(self):
        self.property_fixture()
        for whitespace in ("\x85", "\u00a0", "\u2028", "\u2029", "\u2003"):
            for relative in ("SYSTEM/build.prop", "PRODUCT/etc/build.prop"):
                with self.subTest(whitespace=repr(whitespace), relative=relative):
                    self.write(relative, PROPERTY + "=" + FINGERPRINT + whitespace + "\n")
                    with self.assertRaises(ExternalError):
                        self.marker()
                    self.write(relative, PROPERTY + "=" + FINGERPRINT + "\n")

    def test_debug_ramdisk_properties_are_not_silently_ignored(self):
        self.property_fixture()
        self.write("INIT_BOOT/RAMDISK/adb_debug.prop", "ro.debuggable=1")
        with self.assertRaisesRegex(ExternalError, "debug ramdisk"):
            self.marker()


class ImageReadTests(CareMapTestCase):
    def setUp(self):
        super().setUp()
        self.raw = b"inert non-AVB test bytes " * 8
        self.path = self.write("IMAGES/example.img", self.raw)
        self.opened = []
        self.sparse = False
        self.parser_error = None
        test = self

        class ImageHandlerDouble:
            def __init__(self, path, read_only=False):
                test.assertTrue(read_only)
                self._image = open(path, "rb")
                self.is_sparse = test.sparse
                test.opened.append(self)

        class AvbDouble:
            def _parse_image(self, image):
                if test.parser_error:
                    raise test.parser_error
                return "synthetic parsed AVB seam"

        self.namespace["avbtool"].ImageHandler = ImageHandlerDouble
        self.namespace["avbtool"].Avb = AvbDouble

    def read(self, **kwargs):
        return self.namespace["_NezhaCareMapAvbImage"]("IMAGES/example.img", **kwargs)

    def test_reads_hashes_and_closes_ordinary_bytes_before_return(self):
        self.assertEqual("synthetic parsed AVB seam", self.read(
            expected_size=len(self.raw), expected_sha256=hashlib.sha256(self.raw).hexdigest()))
        self.assertTrue(self.opened[0]._image.closed)
        self.assertEqual(self.raw, self.path.read_bytes())

    def test_wrong_size_or_digest_fails_before_avb_parser(self):
        for kwargs in ({"expected_size": len(self.raw) + 1}, {"expected_size": len(self.raw) - 1},
                       {"expected_sha256": "0" * 64}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ExternalError):
                self.read(**kwargs)
        self.assertEqual([], self.opened)

    def test_root_vbmeta_size_is_bounded(self):
        self.path.write_bytes(bytes(1024 * 1024 + 1))
        with self.assertRaisesRegex(ExternalError, "size"):
            self.read()

    def test_sparse_image_fails_and_closes_handle(self):
        self.sparse = True
        with self.assertRaisesRegex(ExternalError, "Sparse"):
            self.read()
        self.assertTrue(self.opened[0]._image.closed)

    def test_malformed_avb_does_not_leak_handle_or_become_skipped(self):
        self.parser_error = LookupError("inert malformed AVB")
        with self.assertRaisesRegex(LookupError, "malformed"):
            self.read()
        self.assertTrue(self.opened[0]._image.closed)


class DirectEntryTests(CareMapTestCase):
    def setUp(self):
        super().setUp()
        self.selected_info()
        self.tree = HashtreeDouble()
        self.footer = types.SimpleNamespace(original_image_size=109445120,
                                            vbmeta_offset=111190016, vbmeta_size=832)
        self.header = types.SimpleNamespace(algorithm_type=0, flags=0)
        self.root_header = types.SimpleNamespace(flags=0)
        self.root_descriptors = [copy.deepcopy(self.tree)]
        self.leaf_descriptors = [self.tree]
        self.calls = []

        def avb(relative, *expected):
            self.calls.append((relative, expected))
            if relative == "IMAGES/mi_ext.img":
                return self.footer, self.header, self.leaf_descriptors, 111198208
            self.assertEqual(relative, "IMAGES/vbmeta.img")
            return None, self.root_header, self.root_descriptors, 12288

        self.namespace["_NezhaCareMapAvbImage"] = avb
        self.images = {"mi_ext": str(self.root / "IMAGES/mi_ext.img")}

    def entry(self, selected=None):
        return self.namespace["_NezhaDirectMiExtCareMap"](selected or REQUIRED, self.images)

    def test_direct_entry_binds_exact_image_root_descriptor_and_system_pair(self):
        self.assertEqual(["mi_ext", "2,0,26720", PROPERTY, FINGERPRINT], self.entry())
        self.assertEqual(self.calls, [
            ("IMAGES/mi_ext.img", (111198208, "60f791178bed4694870be74190b4487d9371af575e18ffbc950fb91fdb97e196")),
            ("IMAGES/vbmeta.img", ())])
        self.assertEqual(LEGACY, self.namespace["PARTITIONS_WITH_CARE_MAP"])

    def test_missing_duplicate_or_partial_ab_logical_set_fails(self):
        for selected in (REQUIRED[:-1], REQUIRED + ["mi_ext"], ["system", "mi_ext"]):
            with self.subTest(selected=selected), self.assertRaisesRegex(ExternalError, "complete unique"):
                self.entry(selected)

    def test_partial_or_extra_dynamic_partition_set_fails(self):
        for selected in (REQUIRED[:-1], REQUIRED + ["odm_dlkm"], REQUIRED + ["mi_ext"]):
            self.options.info_dict["dynamic_partition_list"] = " ".join(selected)
            with self.subTest(selected=selected), self.assertRaisesRegex(ExternalError, "logical set"):
                self.entry()

    def test_direct_registration_and_normal_ab_avb_mode_are_required(self):
        for key, value in (("avb_custom_images_direct_partition_list", ""),
                           ("avb_custom_images_partition_list", "mi_ext other"),
                           ("avb_mi_ext_image_list", "wrong.img"), ("ab_update", "false"),
                           ("avb_enable", "false"), ("allow_non_ab", "true")):
            with self.subTest(key=key), mock.patch.dict(self.options.info_dict, {key: value}):
                with self.assertRaisesRegex(ExternalError, "original direct AVB"):
                    self.entry()

    def test_empty_signing_or_invented_verity_metadata_is_rejected(self):
        for key in ("avb_mi_ext_key_path", "avb_mi_ext_algorithm", "avb_mi_ext_rollback_index",
                    "avb_mi_ext_rollback_index_location", "avb_mi_ext_partition_size",
                    "avb_mi_ext_add_hashtree_footer_args", "avb_mi_ext_hashtree_enable",
                    "mi_ext_verity_block_device"):
            with self.subTest(key=key), mock.patch.dict(self.options.info_dict, {key: ""}):
                with self.assertRaises(ExternalError):
                    self.entry()

    def test_chain_owner_selection_or_chain_descriptor_is_rejected(self):
        with mock.patch.dict(self.options.info_dict, {"avb_vbmeta_vendor": "vendor mi_ext"}):
            with self.assertRaisesRegex(ExternalError, "chained"):
                self.entry()
        self.root_descriptors[:] = [types.SimpleNamespace(partition_name="mi_ext")]
        with self.assertRaisesRegex(ExternalError, "Root vbmeta"):
            self.entry()

    def test_missing_or_noncanonical_image_map_fails(self):
        for image in (None, str(self.root / "PREBUILT_IMAGES/mi_ext.img")):
            self.images["mi_ext"] = image
            with self.subTest(image=image), self.assertRaisesRegex(ExternalError, "selected Nezha"):
                self.entry()

    def test_missing_or_duplicate_leaf_tree_fails(self):
        for descriptors in ([], [self.tree, self.tree]):
            self.leaf_descriptors = descriptors
            with self.subTest(count=len(descriptors)), self.assertRaisesRegex(ExternalError, "sole original"):
                self.entry()

    def test_changed_descriptor_fails_even_with_same_partition_name(self):
        self.tree.flags = 1
        with self.assertRaisesRegex(ExternalError, "descriptor differs"):
            self.entry()

    def test_missing_footer_and_inconsistent_geometry_fail(self):
        original_footer = self.footer
        self.footer = None
        with self.assertRaisesRegex(ExternalError, "geometry disagree"):
            self.entry()
        self.footer = original_footer
        for field, value in (("original_image_size", 109445119), ("vbmeta_offset", 111190015),
                             ("vbmeta_size", 831)):
            with self.subTest(field=field), mock.patch.object(self.footer, field, value):
                with self.assertRaisesRegex(ExternalError, "geometry disagree"):
                    self.entry()

    def test_tree_parser_geometry_must_agree_even_if_encoded_identity_matches(self):
        encoded = self.tree.encode()
        self.tree.encode = lambda: encoded  # deliberate inconsistent parser seam
        for field, value in (("image_size", 109445119), ("data_block_size", 16384),
                             ("hash_block_size", 16384), ("fec_num_roots", 0),
                             ("fec_offset", 110313473), ("tree_size", 868353)):
            with self.subTest(field=field), mock.patch.object(self.tree, field, value):
                with self.assertRaisesRegex(ExternalError, "geometry disagree"):
                    self.entry()

    def test_root_must_not_disable_verity_omit_duplicate_or_change_descriptor(self):
        cases = [[], [self.tree, self.tree], [HashtreeDouble()]]
        cases[-1][0].root_digest = bytes(32)
        for descriptors in cases:
            self.root_descriptors = descriptors
            with self.subTest(count=len(descriptors)), self.assertRaisesRegex(ExternalError, "Root vbmeta"):
                self.entry()
        self.root_descriptors = [self.tree]
        self.root_header.flags = 2
        with self.assertRaisesRegex(ExternalError, "Root vbmeta"):
            self.entry()


class CareMapPipelineTests(CareMapTestCase):
    def setUp(self):
        super().setUp()
        self.commands = []
        self.text = None
        self.corrupt_roundtrip = False
        self.calls = []
        self.output = self.root / "care_map.pb"
        self.namespace["MakeTempFile"] = self.temp_file
        self.namespace["RunAndCheckOutput"] = self.run_tool_seam
        self.namespace["GetCareMap"] = self.get_care_map_seam
        self.images = {}
        self.options.info_dict = {}
        for name in REQUIRED:
            self.images[name] = str(self.write("IMAGES/" + name + ".img", "inert image"))
            self.options.info_dict["avb_" + name + "_hashtree_enable"] = "true"
            self.options.info_dict[name + ".build.prop"] = Props({
                "ro." + name + ".build.fingerprint": FINGERPRINT if name == "system" else "fixture/" + name})

    def temp_file(self, prefix, suffix):
        handle, name = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=self.root)
        os.close(handle)
        return name

    def run_tool_seam(self, command):
        self.commands.append(command)
        if command[1] == "--parse_proto":
            Path(command[3]).write_text(self.text + ("\ncorrupt" if self.corrupt_roundtrip else ""))
        else:
            self.text = Path(command[1]).read_text()
            Path(command[2]).write_bytes(b"explicitly not a protobuf; inert process seam")

    def get_care_map_seam(self, name, path):
        self.calls.append((name, path))
        return [name, "2,0,10"]

    def enable(self):
        self.options.info_dict[SELECTOR] = VALUE
        self.namespace["_NezhaDirectMiExtCareMap"] = lambda selected, images: [
            "mi_ext", "2,0,26720", PROPERTY, FINGERPRINT]

    def add(self, selected=None):
        return self.namespace["AddCareMapForAbOta"](str(self.output), selected or REQUIRED, self.images)

    def test_legacy_profiles_still_skip_mi_ext_and_make_only_original_tool_call(self):
        self.add()
        self.assertNotIn("mi_ext", self.text.splitlines())
        self.assertEqual(1, len(self.commands))
        self.assertEqual(LEGACY, self.namespace["PARTITIONS_WITH_CARE_MAP"])

    def test_legacy_unknown_marker_and_missing_image_behavior_stays_unchanged(self):
        self.options.info_dict["vendor.build.prop"] = None
        del self.images["odm"]
        with self.assertLogs("mi-ext-care-map-tests", level="WARNING"):
            self.add()
        self.assertIn("unknown\nunknown", self.text)
        self.assertNotIn("odm", self.text.splitlines())

    def test_legacy_output_matches_actual_prepatch_function(self):
        self.add()
        after = self.text
        before = make_namespace(False)
        for key in ("OPTIONS", "MakeTempFile", "RunAndCheckOutput", "GetCareMap"):
            before[key] = self.namespace[key]
        before["AddCareMapForAbOta"](str(self.output), REQUIRED, self.images)
        self.assertEqual(after, self.text)

    def test_invalid_explicit_selector_cannot_fall_back_to_legacy(self):
        for value in ("", "true", "future", False, 1):
            self.options.info_dict[SELECTOR] = value
            with self.subTest(value=value), self.assertRaisesRegex(ExternalError, "Unknown"):
                self.add()
        self.assertEqual([], self.commands)

    def test_selected_text_contains_all_eight_unique_rows_and_roundtrip_is_required(self):
        self.enable()
        self.add()
        lines = self.text.splitlines()
        self.assertEqual(REQUIRED, lines[::4])
        self.assertEqual(32, len(lines))
        self.assertEqual([PROPERTY, FINGERPRINT], lines[-2:])
        self.assertEqual(2, len(self.commands))
        self.assertEqual("--parse_proto", self.commands[1][1])
        self.assertNotIn("--no_fingerprint", self.commands[0])

    def test_selected_unknown_thumbprint_or_missing_standard_row_fails_before_generator(self):
        self.enable()
        for change in ("unknown", "thumbprint", "missing"):
            with self.subTest(change=change):
                originals = copy.deepcopy(self.options.info_dict)
                if change == "unknown":
                    self.options.info_dict["vendor.build.prop"] = None
                elif change == "thumbprint":
                    self.options.info_dict["system.build.prop"] = Props({"ro.system.build.thumbprint": FINGERPRINT})
                else:
                    self.options.info_dict["avb_vendor_hashtree_enable"] = "false"
                with self.assertRaises(ExternalError):
                    self.add()
                self.options.info_dict = originals
        self.assertEqual([], self.commands)
        self.assertFalse(self.output.exists())

    def test_selected_duplicate_or_empty_range_fails_before_generator(self):
        self.enable()
        with self.assertRaisesRegex(ExternalError, "Incomplete"):
            self.add(REQUIRED + ["system"])
        for ranges in ("0", "2,10,0", "2,-1,10", "2,0,0", "4,0,10", "2,00,10"):
            with self.subTest(ranges=ranges):
                self.namespace["GetCareMap"] = lambda name, path: [name, ranges]
                with self.assertRaisesRegex(ExternalError, "Invalid required"):
                    self.add()
        self.assertEqual([], self.commands)

    def test_native_generator_failure_cannot_become_partial_success(self):
        self.enable()
        self.namespace["RunAndCheckOutput"] = mock.Mock(side_effect=ExternalError("native failure seam"))
        with self.assertRaisesRegex(ExternalError, "native failure"):
            self.add()
        self.assertFalse(self.output.exists())

    def test_proto_roundtrip_loss_fails_before_output_is_written(self):
        self.enable()
        self.corrupt_roundtrip = True
        with self.assertRaisesRegex(ExternalError, "protobuf did not preserve"):
            self.add()
        self.assertEqual(2, len(self.commands))
        self.assertFalse(self.output.exists())

    def test_real_import_guard_cannot_reach_native_generator(self):
        self.enable()
        self.namespace["_NezhaDirectMiExtCareMap"] = make_namespace()["_NezhaDirectMiExtCareMap"]
        # Recompile the actual functions into this namespace instead of using
        # the other function's independent globals.
        actual = next(node for node in functions(public_hunk())
                      if node.name == "_NezhaDirectMiExtCareMap")
        exec(compile(ast.Module(body=[actual], type_ignores=[]), "<actual source>", "exec"), self.namespace)
        self.options.info_dict.clear()
        self.selected_info()
        self.write("ODM/etc/build.prop", "import /odm/etc/${ro.boot.hwc}.prop\n")
        with self.assertRaisesRegex(ExternalError, "Unqualified.*import"):
            self.add()
        self.assertEqual([], self.commands)


if __name__ == "__main__":
    unittest.main()
