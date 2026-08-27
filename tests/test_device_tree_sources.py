"""Offline tests for complete FDT graphs and inert device-tree source contracts."""

import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

from scripts import device_tree_sources as sources


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def node(name, properties=(), children=()):
    return {"name": name, "properties": list(properties), "children": list(children)}


def graph_fixture():
    cells = lambda *values: struct.pack(">" + str(len(values)) + "I", *values)
    return node("", [
        ("model", b"Nezha based on SM8850\0"),
        ("compatible", b"qcom,canoe\0qcom,canoep\0"),
        ("qcom,board-id", cells(8, 0)),
        ("xiaomi,miboard-id", cells(5, 0)),
        ("boolean-property", b""),
    ], [
        node("soc", [("#address-cells", cells(2))], [
            node("serial@a600000", [("phandle", cells(1)), ("reg", cells(0, 0xa600000, 0x1000)),
                                     ("binary-property", b"\xff\x00\x80\x01")]),
        ]),
        node("fragment@0", [("target", cells(0xffffffff))], [
            node("__overlay__", [("clocks", cells(1, 2)), ("linux,phandle", cells(2))]),
        ]),
        node("__fixups__", [("soc", b"/fragment@0:target:0\0")]),
        node("__local_fixups__", children=[
            node("fragment@0", children=[node("__overlay__", [("clocks", cells(0, 4))])]),
        ]),
        node("__symbols__", [("uart0", b"/soc/serial@a600000\0")]),
    ])


def synthetic_fdt(tree=None, *, reservations=(), boot_cpuid=0, reverse_strings=False,
                  nops=False, gap=0, strings_first=False):
    """Emit FDT bytes independently of the parser, allowing layout variations."""
    tree = graph_fixture() if tree is None else tree
    property_names = []

    def collect(item):
        for name, _ in item["properties"]:
            if name not in property_names:
                property_names.append(name)
        for child in item["children"]:
            collect(child)

    collect(tree)
    if reverse_strings:
        property_names.reverse()
    strings = bytearray()
    offsets = {}
    for name in property_names:
        offsets[name] = len(strings)
        strings.extend(name.encode() + b"\0")
    structure = bytearray()

    def word(value):
        structure.extend(struct.pack(">I", value))

    def emit(item):
        if nops:
            word(4)
        word(1)
        structure.extend(item["name"].encode() + b"\0")
        structure.extend(b"\0" * (-len(structure) % 4))
        for name, value in item["properties"]:
            if nops:
                word(4)
            structure.extend(struct.pack(">3I", 3, len(value), offsets[name]))
            structure.extend(value)
            structure.extend(b"\0" * (-len(structure) % 4))
        for child in item["children"]:
            emit(child)
        word(2)

    emit(tree)
    if nops:
        word(4)
    word(9)
    reserved = b"".join(struct.pack(">2Q", address, size) for address, size in reservations) + bytes(16)
    prefix = bytes(40) + reserved + bytes(gap)
    if strings_first:
        strings_at = len(prefix)
        prefix += strings
        prefix += bytes(-len(prefix) % 4)
        structure_at = len(prefix)
        data = bytearray(prefix + structure)
    else:
        structure_at = len(prefix)
        strings_at = structure_at + len(structure)
        data = bytearray(prefix + structure + strings)
    struct.pack_into(">10I", data, 0, 0xd00dfeed, len(data), structure_at, strings_at,
                     40, 17, 16, boot_cpuid, len(strings), len(structure))
    return bytes(data)


def field(data, index, value):
    changed = bytearray(data)
    struct.pack_into(">I", changed, index * 4, value)
    return bytes(changed)


def replace_structure(data, replacement):
    structure_at, strings_at = struct.unpack_from(">2I", data, 8)
    strings_size = struct.unpack_from(">I", data, 32)[0]
    strings = data[strings_at:strings_at + strings_size]
    changed = data[:structure_at] + replacement + strings
    changed = field(changed, 1, len(changed))
    changed = field(changed, 3, structure_at + len(replacement))
    return field(changed, 9, len(replacement))


def synthetic_dtbo(trees=None, *, page_size=4096, version=0):
    trees = [synthetic_fdt()] if trees is None else trees
    payload_at = 32 + 32 * len(trees)
    entries = bytearray()
    payload = bytearray()
    for index, tree in enumerate(trees):
        entries.extend(struct.pack(">8I", len(tree), payload_at + len(payload), index,
                                   0, 0, 0, 0, 0))
        payload.extend(tree)
    return (struct.pack(">8I", 0xd7b7ab1e, payload_at + len(payload), 32, 32,
                        len(trees), 32, page_size, version) + entries + payload)


class FdtParserTests(unittest.TestCase):
    def assert_invalid(self, data):
        with self.assertRaises(sources.DeviceTreeSourceError):
            sources.parse_fdt(data)

    def test_complete_graph_preserves_nested_raw_properties_and_order(self):
        graph = sources.parse_fdt(synthetic_fdt(boot_cpuid=3, reservations=[(0x100000000, 0x2000)]))
        self.assertEqual(graph["boot_cpuid_phys"], 3)
        self.assertEqual(graph["reservations"], [[0x100000000, 0x2000]])
        self.assertEqual(graph["nodes"]["/"]["children"],
                         ["soc", "fragment@0", "__fixups__", "__local_fixups__", "__symbols__"])
        self.assertEqual(graph["nodes"]["/soc"]["children"], ["serial@a600000"])
        self.assertEqual(graph["nodes"]["/soc/serial@a600000"]["properties"]["binary-property"], "ff008001")
        self.assertEqual(graph["nodes"]["/"]["properties"]["boolean-property"], "")

    def test_fixups_phandles_and_symbols_are_not_discarded(self):
        graph = sources.parse_fdt(synthetic_fdt())["nodes"]
        self.assertEqual(graph["/soc/serial@a600000"]["properties"]["phandle"], "00000001")
        self.assertEqual(graph["/fragment@0/__overlay__"]["properties"]["linux,phandle"], "00000002")
        self.assertEqual(bytes.fromhex(graph["/__fixups__"]["properties"]["soc"]), b"/fragment@0:target:0\0")
        self.assertEqual(graph["/__local_fixups__/fragment@0/__overlay__"]["properties"]["clocks"], "0000000000000004")
        self.assertEqual(bytes.fromhex(graph["/__symbols__"]["properties"]["uart0"]), b"/soc/serial@a600000\0")

    def test_layout_string_table_order_nops_and_padding_do_not_change_graph(self):
        baseline = synthetic_fdt()
        expected = sources.parse_fdt(baseline)
        for options in ({"reverse_strings": True}, {"nops": True}, {"gap": 16},
                        {"strings_first": True}, {"reverse_strings": True, "nops": True, "gap": 32}):
            with self.subTest(options=options):
                data = synthetic_fdt(**options)
                self.assertNotEqual(data, baseline)
                self.assertEqual(sources.parse_fdt(data), expected)

    def test_property_order_is_ignored_but_child_order_is_preserved(self):
        tree = graph_fixture()
        original = sources.parse_fdt(synthetic_fdt(tree))
        tree["properties"].reverse()
        self.assertEqual(sources.parse_fdt(synthetic_fdt(tree)), original)
        tree["children"].reverse()
        self.assertNotEqual(sources.parse_fdt(synthetic_fdt(tree)), original)

    def test_changed_property_fixup_reservation_or_cpu_changes_graph(self):
        original = sources.parse_fdt(synthetic_fdt())
        tree = graph_fixture()
        tree["children"][2]["properties"][0] = ("soc", b"/fragment@0:target:4\0")
        self.assertNotEqual(sources.parse_fdt(synthetic_fdt(tree)), original)
        self.assertNotEqual(sources.parse_fdt(synthetic_fdt(boot_cpuid=1)), original)
        self.assertNotEqual(sources.parse_fdt(synthetic_fdt(reservations=[(0, 4096)])), original)

    def test_header_magic_sizes_offsets_and_versions_are_bounded(self):
        raw = synthetic_fdt()
        mutations = [(0, 0), (1, len(raw) + 4), (1, 39), (2, len(raw)),
                     (3, len(raw)), (4, len(raw) - 8), (5, 1),
                     (8, len(raw) + 1), (9, len(raw) + 1)]
        for index, value in mutations:
            with self.subTest(index=index, value=value):
                self.assert_invalid(field(raw, index, value))
        self.assert_invalid(raw[:39])

    def test_structure_and_strings_must_not_overlap(self):
        raw = synthetic_fdt()
        structure_at = struct.unpack_from(">I", raw, 8)[0]
        self.assert_invalid(field(raw, 3, structure_at))

    def test_reserve_map_requires_terminator_before_structure(self):
        raw = bytearray(synthetic_fdt(reservations=[(0x1000, 0x1000)]))
        raw[56:72] = struct.pack(">2Q", 0x2000, 0x1000)
        self.assert_invalid(bytes(raw))

    def test_root_name_and_duplicate_siblings_are_rejected(self):
        self.assert_invalid(synthetic_fdt(node("named-root")))
        self.assert_invalid(synthetic_fdt(node("", children=[node("same"), node("same")])))

    def test_duplicate_properties_are_rejected_even_when_bytes_agree(self):
        for properties in ([('x', b'a'), ('x', b'a')], [('x', b'a'), ('x', b'b')]):
            with self.subTest(properties=properties):
                self.assert_invalid(synthetic_fdt(node("", properties)))

    def test_same_child_basename_under_distinct_parents_is_allowed(self):
        tree = node("", children=[node("left", children=[node("same")]),
                                   node("right", children=[node("same")])])
        graph = sources.parse_fdt(synthetic_fdt(tree))
        self.assertIn("/left/same", graph["nodes"])
        self.assertIn("/right/same", graph["nodes"])

    def test_property_data_and_string_name_bounds_are_checked(self):
        raw = synthetic_fdt()
        structure_at = struct.unpack_from(">I", raw, 8)[0]
        for location in (structure_at + 12, structure_at + 16):
            with self.subTest(location=location):
                changed = bytearray(raw)
                struct.pack_into(">I", changed, location, 0xffffffff)
                self.assert_invalid(bytes(changed))
        changed = bytearray(raw)
        changed[-1] = ord('x')
        self.assert_invalid(bytes(changed))

    def test_unknown_tokens_unbalanced_nodes_and_missing_end_are_rejected(self):
        raw = synthetic_fdt(node(""))
        begin = struct.unpack_from(">I", raw, 8)[0]
        length = struct.unpack_from(">I", raw, 36)[0]
        structure = raw[begin:begin + length]
        replacements = [struct.pack(">I", 42) + structure[4:], structure[:-4],
                        structure[:-8] + structure[-4:], struct.pack(">I", 2) + structure]
        for replacement in replacements:
            with self.subTest(replacement=replacement.hex()):
                self.assert_invalid(replace_structure(raw, replacement))

    def test_second_root_and_tokens_after_end_are_not_silently_ignored(self):
        raw = synthetic_fdt(node(""))
        begin = struct.unpack_from(">I", raw, 8)[0]
        length = struct.unpack_from(">I", raw, 36)[0]
        structure = raw[begin:begin + length]
        self.assert_invalid(replace_structure(raw, structure[:-4] + structure))
        self.assert_invalid(replace_structure(raw, structure + struct.pack(">I", 3)))

    def test_nonbyte_buffers_graph_limits_and_reservation_overflow_are_refused(self):
        for value in (None, "not bytes", bytearray(synthetic_fdt()), memoryview(synthetic_fdt())):
            with self.subTest(type=type(value).__name__):
                self.assert_invalid(value)
        with mock.patch.object(sources, "MAX_NODES", 2):
            self.assert_invalid(synthetic_fdt())
        with mock.patch.object(sources, "MAX_PROPERTIES", 2):
            self.assert_invalid(synthetic_fdt())
        self.assert_invalid(synthetic_fdt(reservations=[(2**64 - 1, 2)]))


class DeviceTreeSplitTests(unittest.TestCase):
    def test_concatenated_dtbs_keep_exact_bytes_and_order(self):
        first = synthetic_fdt()
        second = synthetic_fdt(boot_cpuid=1, reverse_strings=True)
        self.assertEqual(sources.split_dtbs(first + second), [first, second])

    def test_dtb_split_rejects_empty_truncated_or_junk_tail(self):
        for data in (b"", synthetic_fdt()[:-1], synthetic_fdt() + b"junk"):
            with self.subTest(size=len(data)), self.assertRaises(sources.DeviceTreeSourceError):
                sources.split_dtbs(data)

    def test_dtbo_split_keeps_table_payload_order_and_ignores_external_padding(self):
        trees = [synthetic_fdt(), synthetic_fdt(boot_cpuid=1)]
        metadata, actual = sources.split_dtbo(synthetic_dtbo(trees) + bytes(64))
        self.assertIsInstance(metadata, dict)
        self.assertEqual(actual, trees)

    def test_dtbo_split_rejects_wrong_page_version_magic_or_table_bounds(self):
        raw = synthetic_dtbo()
        cases = [synthetic_dtbo(page_size=16384), synthetic_dtbo(version=1),
                 field(raw, 0, 0), field(raw, 1, len(raw) + 1), field(raw, 2, 4096),
                 field(raw, 3, 16), field(raw, 4, 257), field(raw, 5, len(raw)), raw[:31]]
        for data in cases:
            with self.subTest(sha256=sha256(data)), self.assertRaises(sources.DeviceTreeSourceError):
                sources.split_dtbo(data)

    def test_dtbo_entries_cannot_overlap_table_or_each_other(self):
        raw = synthetic_dtbo([synthetic_fdt(), synthetic_fdt()])
        table_overlap = bytearray(raw)
        struct.pack_into(">I", table_overlap, 36, 32)
        payload_overlap = bytearray(raw)
        struct.pack_into(">I", payload_overlap, 68, struct.unpack_from(">I", raw, 36)[0])
        for data in (bytes(table_overlap), bytes(payload_overlap)):
            with self.subTest(sha256=sha256(data)), self.assertRaises(sources.DeviceTreeSourceError):
                sources.split_dtbo(data)

    def test_splitters_enforce_maximum_tree_count(self):
        tree = synthetic_fdt(node(""))
        with self.assertRaises(sources.DeviceTreeSourceError):
            sources.split_dtbs(tree * 257)
        with self.assertRaises(sources.DeviceTreeSourceError):
            sources.split_dtbo(synthetic_dtbo([tree] * 257))


class DeviceTreeSourcePreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bundle = self.root / "artifacts/kernel-inputs/fixture"
        self.bundle.mkdir(parents=True)
        self.output = self.root / "artifacts/source-contracts/nezha-fixture"
        self.output.parent.mkdir(parents=True)
        self.tool = self.root / "tools/dtc"
        self.tool.parent.mkdir()
        self.tool.write_bytes(b"trusted synthetic compiler fixture, never executed")
        self.tool.chmod(0o755)
        self.version = "Version: DTC 1.7.2"
        self.recipe_path = self.root / "recipe.json"
        self.source_config = self.root / "sources.json"
        references = [
            {"name": "micode-popsicle-kernel", "url": "https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git",
             "branch": "popsicle-w-oss", "commit": "1" * 40},
            {"name": "micode-popsicle-devicetree", "url": "https://github.com/MiCode/kernel_devicetree.git",
             "branch": "popsicle-w-oss", "commit": "2" * 40},
        ]
        self.recipe = {"schema_version": 1,
                       "device": {"codename": "nezha", "hardware_region": "CN", "soc": "SM8850"},
                       "dtc": {"sha256": sha256(self.tool.read_bytes()), "version": self.version},
                       "references": copy.deepcopy(references)}
        self.source_config.write_text(json.dumps({"references": references}))
        self.base_trees = [synthetic_fdt(), synthetic_fdt(boot_cpuid=1)]
        self.overlay_trees = [synthetic_fdt()]
        self.payloads = {"dtb/vendor.dtb": b"".join(self.base_trees),
                         "dtbo/dtbo.img": synthetic_dtbo(self.overlay_trees) + bytes(64)}
        self.bundle_receipt = {
            "schema_version": 1, "operation": "prepare-nezha-kernel-inputs", "purpose": "build-candidate",
            "device": self.recipe["device"],
            "kernel": {"dtb_count": 2, "dtbo_count": 1, "dtbo_board_id": [8, 0], "dtbo_miboard_id": [5, 0]},
            "provenance": {"parent_package_sha256": "3" * 64, "source_kind": "user-provided",
                           "source_url": None, "origin_verified": False,
                           "package_kind": "unknown-origin modified package fixture"},
            "validation": {"input_avb_status": "failed", "kernel_abi_verified": False,
                           "module_signatures_verified": False, "device_tested": False,
                           "build_verified": False, "phone_accessed": False, "firmware_executed": False},
            "roles": {"dtb": "dtb/vendor.dtb", "dtbo": "dtbo/dtbo.img"}, "files": [],
        }
        self.write_bundle()
        self.write_recipe()
        self.rebuilt = {sha256(synthetic_fdt(boot_cpuid=cpu)):
                        synthetic_fdt(boot_cpuid=cpu, reverse_strings=True, nops=True, gap=16)
                        for cpu in (0, 1)}
        self.decompiled = {}
        self.compiler_failure = None
        self.rebuild_transform = None
        self.calls = []
        self.run_dtc = self.enterContext(mock.patch.object(sources, "_run_dtc", side_effect=self.fake_dtc))
        self.popen = self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("No real compiler or device tools")))
        self.system = self.enterContext(mock.patch("os.system", side_effect=AssertionError("No shell execution")))

    def write_recipe(self):
        self.recipe_path.write_text(json.dumps(self.recipe))

    def write_bundle(self):
        self.bundle_receipt["files"] = []
        for member, data in self.payloads.items():
            target = self.bundle / member
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            self.bundle_receipt["files"].append({"path": member, "size_bytes": len(data),
                                                 "sha256": sha256(data), "readback_verified": True})
        self.write_bundle_receipt()

    def write_bundle_receipt(self):
        data = (json.dumps(self.bundle_receipt) + "\n").encode()
        (self.bundle / "receipt.json").write_bytes(data)
        self.expected_receipt_sha256 = sha256(data)

    def fake_dtc(self, tool_path, arguments, input_path, output_path, stderr_path,
                 *, timeout=30, max_output_bytes=134217728):
        self.assertEqual(Path(tool_path), self.tool)
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 60)
        self.assertLessEqual(max_output_bytes, 134217728)
        arguments = list(arguments)
        self.assertNotIn("-f", arguments)
        self.assertNotIn("-q", arguments)
        self.assertNotIn("-@", arguments)
        self.calls.append({"arguments": arguments, "input_path": input_path,
                           "output_path": output_path, "stderr_path": stderr_path})
        output_path, stderr_path = Path(output_path), Path(stderr_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        status = 0
        error = b""
        if arguments == ["--version"]:
            self.assertIsNone(input_path)
            data = (self.version + "\n").encode()
        elif arguments == ["-I", "dtb", "-O", "dts", "-o", "-"]:
            original = Path(input_path).read_bytes()
            data = ("// synthetic source for " + sha256(original) + "\n/dts-v1/;\n/ {};\n").encode()
            self.decompiled[output_path] = original
            error = b"Warning: synthetic decompiler warning retained\n"
            if self.compiler_failure == "decompile":
                status, data = 1, b"partial source"
        elif arguments == ["-I", "dts", "-O", "dtb", "-o", "-"]:
            original = self.decompiled[Path(input_path)]
            data = self.rebuilt[sha256(original)]
            if self.rebuild_transform:
                data = self.rebuild_transform(original, data)
            error = b"Warning: synthetic compiler warning retained\n"
            if self.compiler_failure == "compile":
                status, data = 1, b"partial rebuilt output"
        else:
            raise AssertionError(f"Unexpected compiler arguments: {arguments}")
        output_path.write_bytes(data)
        stderr_path.write_bytes(error)
        return {"argv": [str(tool_path), *arguments], "exit_code": status,
                "stdout_sha256": sha256(data), "stdout_size_bytes": len(data),
                "stderr_sha256": sha256(error), "stderr_size_bytes": len(error)}

    def prepare(self, **options):
        return sources.prepare_sources(self.bundle, self.expected_receipt_sha256, self.output,
                                       recipe_path=self.recipe_path, dtc_path=self.tool,
                                       source_config=self.source_config, workspace_root=self.root, **options)

    def assert_prevalidation_rejected(self):
        before = set(self.output.parent.iterdir())
        with self.assertRaises(sources.DeviceTreeSourceError):
            self.prepare()
        self.assertFalse(os.path.lexists(self.output))
        self.assertEqual(set(self.output.parent.iterdir()), before)

    def assert_failed_contract_retained(self):
        with self.assertRaises(sources.DeviceTreeSourceError):
            self.prepare()
        receipt_path = self.output / "receipt.json"
        self.assertTrue(receipt_path.is_file())
        receipt = json.loads(receipt_path.read_bytes())
        self.assertEqual(receipt["status"], "failed")
        self.assertIsInstance(receipt["error"], str)
        self.assertTrue(receipt["error"])
        self.assertIsNot(receipt.get("full_graphs_match"), True)
        return receipt

    def test_small_pipeline_compares_full_graphs_and_preserves_original_bytes(self):
        before = {p: p.read_bytes() for p in self.bundle.rglob("*") if p.is_file()}
        receipt = self.prepare()
        self.assertEqual(json.loads((self.output / "receipt.json").read_bytes()), receipt)
        self.assertEqual(receipt["status"], "complete")
        self.assertTrue(receipt["full_graphs_match"])
        self.assertEqual(len(receipt["trees"]), 3)
        self.assertEqual((self.output / "originals/vendor.dtb").read_bytes(), self.payloads["dtb/vendor.dtb"])
        self.assertEqual((self.output / "originals/dtbo.img").read_bytes(), self.payloads["dtbo/dtbo.img"])
        for name in ("dtb-0000", "dtb-0001", "nezha-overlay-0000"):
            directory = self.output / "trees" / name
            self.assertTrue((directory / "source.dts").is_file())
            original, rebuilt = (directory / "original.dtb").read_bytes(), (directory / "rebuilt.dtb").read_bytes()
            self.assertNotEqual(original, rebuilt)
            self.assertEqual(sources.parse_fdt(original), sources.parse_fdt(rebuilt))
            first = json.loads((directory / "original.graph.json").read_bytes())
            second = json.loads((directory / "rebuilt.graph.json").read_bytes())
            self.assertEqual(first, second)
            self.assertIn("/__fixups__", first["nodes"])
        for tree in receipt["trees"]:
            self.assertTrue(tree["graph_equal"])
            self.assertEqual(tree["source_graph_sha256"], tree["rebuilt_graph_sha256"])
            self.assertGreater(tree["node_count"], 5)
            self.assertGreater(tree["property_count"], 8)
        self.assertEqual(before, {p: p.read_bytes() for p in self.bundle.rglob("*") if p.is_file()})
        self.assertEqual(len(self.calls), 7)
        self.popen.assert_not_called()
        self.system.assert_not_called()

    def test_every_recorded_output_and_compiler_warning_is_hash_bound(self):
        receipt = self.prepare()
        for record in receipt["files"]:
            path = self.output / record["path"]
            self.assertFalse(path.is_symlink())
            self.assertEqual(sha256(path.read_bytes()), record["sha256"])
            self.assertEqual(path.stat().st_size, record["size_bytes"])
        warnings = [p.read_text() for p in self.output.rglob("*.stderr*")]
        self.assertTrue(any("synthetic decompiler warning" in text for text in warnings))
        self.assertTrue(any("synthetic compiler warning" in text for text in warnings))

    def test_unknown_origin_failed_avb_and_unverified_build_are_not_upgraded(self):
        receipt = self.prepare()
        self.assertEqual(receipt["provenance"], self.bundle_receipt["provenance"])
        self.assertFalse(receipt["provenance"]["origin_verified"])
        self.assertEqual(receipt["input_validation"], self.bundle_receipt["validation"])
        self.assertEqual(receipt["input_validation"]["input_avb_status"], "failed")
        for key in ("kernel_abi_verified", "module_signatures_verified", "device_tested", "build_verified",
                    "phone_accessed", "firmware_executed"):
            self.assertIs(receipt["input_validation"][key], False)
        for key in ("phone_accessed", "vm_accessed", "firmware_executed", "full_kernel_build_tested",
                    "device_compatibility_verified", "sibling_device_sources_substituted",
                    "warning_or_error_checks_disabled"):
            self.assertIs(receipt[key], False)

    def test_receipt_or_selected_payload_tampering_is_rejected_before_staging(self):
        path = self.bundle / "receipt.json"
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        self.assert_prevalidation_rejected()
        path.write_bytes(original)
        (self.bundle / "dtb/vendor.dtb").write_bytes(b"tampered")
        self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_tool_hash_and_reference_pins_must_match_recipe(self):
        original = copy.deepcopy(self.recipe)
        for change in ("tool", "reference"):
            with self.subTest(change=change):
                self.recipe = copy.deepcopy(original)
                if change == "tool":
                    self.recipe["dtc"]["sha256"] = "0" * 64
                else:
                    self.recipe["references"][0]["commit"] = "f" * 40
                self.write_recipe()
                self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_source_role_paths_cannot_escape_bundle(self):
        self.bundle_receipt["roles"]["dtb"] = "../../escape.dtb"
        self.write_bundle_receipt()
        self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_source_payload_symlink_is_rejected(self):
        path = self.bundle / "dtb/vendor.dtb"
        target = self.root / "source-target.dtb"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
        self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_unexpected_base_platform_or_overlay_board_identity_is_rejected(self):
        original = copy.deepcopy(self.payloads)
        for field, value in (("compatible", b"qcom,unrelated\0"),
                             ("qcom,board-id", struct.pack(">2I", 7, 0)),
                             ("xiaomi,miboard-id", struct.pack(">2I", 4, 0)),
                             ("model", b"Other phone based on SM8850\0")):
            with self.subTest(field=field):
                self.payloads = copy.deepcopy(original)
                changed = graph_fixture()
                changed["properties"] = [(name, value if name == field else data)
                                           for name, data in changed["properties"]]
                if field == "compatible":
                    self.payloads["dtb/vendor.dtb"] = synthetic_fdt(changed) + self.base_trees[1]
                else:
                    self.payloads["dtbo/dtbo.img"] = synthetic_dtbo([synthetic_fdt(changed)])
                self.write_bundle()
                self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_tree_count_must_match_hashed_kernel_receipt(self):
        self.bundle_receipt["kernel"]["dtb_count"] = 3
        self.write_bundle_receipt()
        self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_compiler_from_payload_bundle_or_nonexecutable_file_is_rejected(self):
        self.tool.chmod(0o600)
        self.assert_prevalidation_rejected()
        self.tool.chmod(0o755)
        bundled_tool = self.bundle / "dtc"
        bundled_tool.write_bytes(self.tool.read_bytes())
        bundled_tool.chmod(0o755)
        self.tool = bundled_tool
        self.assert_prevalidation_rejected()
        self.run_dtc.assert_not_called()

    def test_output_must_be_new_and_inside_source_contracts(self):
        self.output.mkdir()
        marker = self.output / "preserve.txt"
        marker.write_text("unchanged")
        with self.assertRaises(sources.DeviceTreeSourceError):
            self.prepare()
        self.assertEqual(marker.read_text(), "unchanged")
        self.output = self.root / "artifacts/unapproved-bundle"
        self.assert_prevalidation_rejected()
        self.output = self.bundle / "nested"
        self.assert_prevalidation_rejected()

    def test_output_symlink_parent_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.output.parent / "alias"
        link.symlink_to(outside, target_is_directory=True)
        self.output = link / "bundle"
        self.assert_prevalidation_rejected()
        self.assertEqual(list(outside.iterdir()), [])

    def test_compiler_error_retains_failed_receipt_and_diagnostics(self):
        self.compiler_failure = "compile"
        receipt = self.assert_failed_contract_retained()
        paths = {record["path"] for record in receipt["files"]}
        self.assertTrue(any("source.dts" in path for path in paths))
        self.assertTrue(any("compile.stderr" in path for path in paths))

    def test_decompiler_error_retains_original_and_failed_receipt(self):
        self.compiler_failure = "decompile"
        receipt = self.assert_failed_contract_retained()
        self.assertIn("originals/vendor.dtb", {r["path"] for r in receipt["files"]})

    def test_version_probe_mismatch_retains_diagnostics_and_does_not_compile(self):
        self.version = "Version: DTC unexpected-version"
        receipt = self.assert_failed_contract_retained()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(receipt["trees"], [])
        self.assertTrue(any("dtc-version.stdout" in row["path"] for row in receipt["files"]))

    def test_source_receipt_change_during_compilation_cannot_publish_success(self):
        def change_receipt(original, rebuilt):
            path = self.bundle / "receipt.json"
            path.write_bytes(path.read_bytes() + b" ")
            return rebuilt

        self.rebuild_transform = change_receipt
        self.assert_failed_contract_retained()

    def test_failed_contract_is_never_overwritten_by_retry(self):
        self.compiler_failure = "compile"
        self.assert_failed_contract_retained()
        original = (self.output / "receipt.json").read_bytes()
        previous_calls = len(self.calls)
        self.compiler_failure = None
        with self.assertRaises(sources.DeviceTreeSourceError):
            self.prepare()
        self.assertEqual((self.output / "receipt.json").read_bytes(), original)
        self.assertEqual(len(self.calls), previous_calls)

    def test_compiler_semantic_change_cannot_be_reported_as_roundtrip_success(self):
        changed = graph_fixture()
        changed["children"][0]["children"][0]["properties"][0] = ("phandle", struct.pack(">I", 99))
        self.rebuild_transform = lambda original, rebuilt: synthetic_fdt(changed)
        self.assert_failed_contract_retained()

    def test_compiler_fixup_loss_is_detected(self):
        changed = graph_fixture()
        changed["children"] = [item for item in changed["children"] if item["name"] != "__fixups__"]
        self.rebuild_transform = lambda original, rebuilt: synthetic_fdt(changed)
        self.assert_failed_contract_retained()

    def test_compiler_child_reordering_is_detected(self):
        changed = graph_fixture()
        changed["children"].reverse()
        self.rebuild_transform = lambda original, rebuilt: synthetic_fdt(changed)
        self.assert_failed_contract_retained()

    def test_compiler_reservation_change_is_detected(self):
        self.rebuild_transform = lambda original, rebuilt: synthetic_fdt(reservations=[(0x1000, 0x1000)])
        self.assert_failed_contract_retained()


if __name__ == "__main__":
    unittest.main()
