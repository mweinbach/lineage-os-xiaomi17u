"""The generated native alias must not hide absent VINTF comparisons."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import vintf_compatibility as vintf


PRODUCT = "out-user/target/product/nezha"
CHECKS = PRODUCT + "/obj/PACKAGING/check_vintf_all_intermediates/"
MANIFEST = PRODUCT + "/system/etc/vintf/manifest.xml"
VENDOR_XML = PRODUCT + "/vendor/etc/vintf/manifest_canoe.xml"
APEX = PRODUCT + "/system/apex/com.android.art.capex"
VENDOR_APEX = PRODUCT + "/vendor/apex/com.android.hardware.cas.apex"


def graph(*, full=False, product_manifest=False, packages=True):
    logs = [CHECKS + "check_vintf_system.log", CHECKS + "vintffm.log"]
    if full:
        logs.append(CHECKS + "check_vintf_compatible.log")
    lines = [
        "# Fixture Kati graph; unrelated module and recipe inputs are not selected.",
        "build check-vintf-all: native_alias " + " ".join(logs),
        "build system_manifest.xml: phony installed_system_manifest",
        "build system_ext_manifest.xml: phony installed_system_ext_manifest",
        "build system_compatibility_matrix.xml: phony matrices",
        "build product_compatibility_matrix.xml: phony product_matrix",
        "build checkvintf: phony host_checker",
        "build apexd_host: phony host_apexd",
        f"build {logs[0]}: check out-user/host/linux-x86/bin/checkvintf {MANIFEST} {CHECKS}apex/apex-info-list.xml",
        f"build {CHECKS}vintffm.log: freeze {MANIFEST}",
        f"build {CHECKS}apex/apex-info-list.xml: activate out-user/host/linux-x86/bin/apexd_host"
        + (f" {APEX} {VENDOR_APEX}" if packages else ""),
        f"build {CHECKS}kernel_configs.txt | {CHECKS}kernel_version.txt: extract {PRODUCT}/kernel",
        f"build unrelated: phony {PRODUCT}/system/etc/vintf/not-selected.xml",
    ]
    if full:
        lines.append(f"build {logs[-1]}: compatibility {MANIFEST} {VENDOR_XML} {CHECKS}kernel_configs.txt")
    if product_manifest:
        lines.append("build product_manifest.xml: phony installed_product_manifest")
    return ("\n".join(lines) + "\n").encode()


class VintfGraphTests(unittest.TestCase):
    def inspect(self, data=None):
        raw = graph() if data is None else data
        edges, identity = vintf.inspect_graph(io.BytesIO(raw), PRODUCT)
        return vintf.summarize(edges, PRODUCT), identity, edges

    def test_native_alias_does_not_imply_full_compatibility(self):
        result, _, _ = self.inspect()
        self.assertFalse(result["native_full_check_defined"])
        self.assertFalse(result["native_full_check_in_all_target"])
        self.assertIn("native-all-target-does-not-include-full-compatibility", result["issues"])
        self.assertFalse(result["compatibility_verified"])
        self.assertFalse(result["full_compatibility_executed"])
        self.assertEqual(result["device_operations"], [])

    def test_full_edge_is_reported_as_defined_never_as_executed(self):
        result, _, _ = self.inspect(graph(full=True))
        self.assertTrue(result["native_full_check_defined"])
        self.assertTrue(result["native_full_check_in_all_target"])
        self.assertFalse(result["full_compatibility_executed"])
        self.assertFalse(result["compatibility_verified"])
        self.assertIn(VENDOR_XML, result["selected_partition_vintf_inputs"])

    def test_orphan_full_edge_does_not_make_alias_complete(self):
        raw = graph(full=True).replace(
            ("build check-vintf-all: native_alias " + CHECKS + "check_vintf_system.log "
             + CHECKS + "vintffm.log " + CHECKS + "check_vintf_compatible.log").encode(),
            ("build check-vintf-all: native_alias " + CHECKS + "check_vintf_system.log").encode())
        result, _, _ = self.inspect(raw)
        self.assertTrue(result["native_full_check_defined"])
        self.assertFalse(result["native_full_check_in_all_target"])

    def test_product_manifest_can_legitimately_have_no_native_action(self):
        result, _, _ = self.inspect()
        self.assertFalse(result["modules"]["product_manifest.xml"])
        self.assertTrue(result["modules"]["system_ext_manifest.xml"])
        self.assertTrue(result["modules"]["product_compatibility_matrix.xml"])
        self.assertFalse(any("product_manifest" in issue for issue in result["issues"]))
        self.assertTrue(self.inspect(graph(product_manifest=True))[0]["modules"]["product_manifest.xml"])

    def test_inventory_uses_native_check_dependencies_not_all_install_rules(self):
        result, _, _ = self.inspect()
        self.assertEqual(result["selected_partition_vintf_inputs"], [MANIFEST])
        self.assertEqual(result["selected_apex_package_inputs"], [APEX, VENDOR_APEX])

    def test_empty_native_apex_set_is_visible(self):
        result, _, _ = self.inspect(graph(packages=False))
        self.assertIn("native-APEX-input-set-is-empty", result["issues"])

    def test_complete_graph_bytes_are_hashed(self):
        data = graph()
        _, identity, _ = self.inspect(data)
        self.assertEqual(identity, {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})

    def test_kernel_implicit_output_is_not_misreported_missing(self):
        result, _, _ = self.inspect()
        self.assertTrue(result["native_check_targets"]["kernel_version.txt"])
        self.assertTrue(result["native_check_targets"]["kernel_configs.txt"])

    def test_missing_kernel_target_is_visible(self):
        raw = b"\n".join(line for line in graph().splitlines() if b": extract " not in line) + b"\n"
        result, _, _ = self.inspect(raw)
        self.assertIn("native-kernel-input-target-missing:kernel_version.txt", result["issues"])
        self.assertIn("native-kernel-input-target-missing:kernel_configs.txt", result["issues"])

    def test_dependency_with_selected_name_cannot_create_a_target(self):
        result, _, _ = self.inspect(graph() + b"build something: phony product_manifest.xml\n")
        self.assertFalse(result["modules"]["product_manifest.xml"])

    def test_duplicate_selected_output_fails(self):
        with self.assertRaisesRegex(vintf.VintfAuditError, "duplicate selected"):
            self.inspect(graph() + b"build checkvintf: phony other\n")

    def test_secondary_outputs_are_included(self):
        for separator in (" ", " | "):
            raw = graph(full=True).replace(
                ("build " + CHECKS + "check_vintf_compatible.log:").encode(),
                ("build unrelated" + separator + CHECKS + "check_vintf_compatible.log:").encode())
            result, _, _ = self.inspect(raw)
            self.assertTrue(result["native_full_check_defined"])
            self.assertTrue(result["native_full_check_in_all_target"])
            raw += ("build other" + separator + "product_manifest.xml: phony input\n").encode()
            self.assertTrue(self.inspect(raw)[0]["modules"]["product_manifest.xml"])

    def test_duplicate_secondary_selected_output_fails(self):
        for separator in (" ", " | "):
            with self.subTest(separator=separator), self.assertRaisesRegex(vintf.VintfAuditError, "duplicate selected"):
                self.inspect(graph() + ("build other" + separator + "checkvintf: phony input\n").encode())

    def test_unknown_selected_variable_expansion_fails(self):
        with self.assertRaisesRegex(vintf.VintfAuditError, "unsupported variable"):
            self.inspect(graph().replace(APEX.encode(), b"${out}/system/apex/example.apex"))

    def test_unrelated_variable_is_not_interpreted_or_executed(self):
        result, _, _ = self.inspect(graph() + b"build unrelated2: phony ${arbitrary}\n")
        self.assertFalse(result["compatibility_verified"])

    def test_escaped_space_and_dollar_are_literal_dependencies(self):
        _, _, edges = self.inspect(graph().replace(b"host_checker", b"host$ checker$$name"))
        self.assertEqual(edges["checkvintf"]["inputs"], ["host checker$name"])

    def test_unspaced_ninja_dependency_separators_are_not_path_characters(self):
        for separator in (b"|", b"||", b"|@"):
            with self.subTest(separator=separator):
                _, _, edges = self.inspect(graph().replace(b"host_checker", b"explicit" + separator + b"implicit"))
                self.assertEqual(edges["checkvintf"]["inputs"], ["explicit", "implicit"])
        result, _, _ = self.inspect(graph() + b"build other|product_manifest.xml: phony input\n")
        self.assertTrue(result["modules"]["product_manifest.xml"])

    def test_ninja_continuations_preserve_token_boundaries(self):
        _, _, edges = self.inspect(graph().replace(b"host_checker", b"host_$\n  checker"))
        self.assertEqual(edges["checkvintf"]["inputs"], ["host_checker"])

    def test_many_continuations_preserve_one_literal_dependency(self):
        value = b"a$\n   " * 2000 + b"end"
        _, _, edges = self.inspect(graph().replace(b"host_checker", value))
        self.assertEqual(edges["checkvintf"]["inputs"], ["a" * 2000 + "end"])

    def test_literal_dollar_at_line_end_is_not_a_continuation(self):
        _, _, edges = self.inspect(graph().replace(b"host_checker", b"host_checker$$"))
        self.assertEqual(edges["checkvintf"]["inputs"], ["host_checker$"])

    def test_graph_and_line_size_bounds_fail(self):
        for options in ({"max_bytes": 40}, {"max_line_bytes": 20}):
            with self.subTest(options=options), self.assertRaises(vintf.VintfAuditError):
                vintf.inspect_graph(io.BytesIO(graph()), PRODUCT, **options)

    def test_incomplete_or_wrong_graph_fails(self):
        for raw in (b"", graph().replace(b"build check-vintf-all:", b"build different:"),
                    graph() + b"build unfinished$\n"):
            with self.subTest(raw=raw[:30]), self.assertRaises(vintf.VintfAuditError):
                self.inspect(raw)

    def test_unsafe_product_prefix_fails(self):
        for prefix in ("/out/target/product/nezha", "out/../out/target/product/nezha",
                       "out//target/product/nezha", "elsewhere", "out\\target/product/nezha"):
            with self.subTest(prefix=prefix), self.assertRaises(vintf.VintfAuditError):
                vintf.inspect_graph(io.BytesIO(graph()), prefix)


class VintfArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.graph = self.root / "build-lineage_nezha.ninja"
        self.graph.write_bytes(graph())
        self.out = self.root / "out"
        self.out.mkdir()

    def test_missing_artifacts_are_explicit_and_do_not_pass_compatibility(self):
        result = vintf.audit(self.graph, PRODUCT, output_root=self.out)
        self.assertEqual(result["missing_artifact_count"], 3)
        self.assertEqual({x["state"] for x in result["artifacts"].values()}, {"missing"})
        self.assertFalse(result["compatibility_verified"])

    def test_present_artifact_hash_and_size_come_from_the_actual_file(self):
        target = self.out / MANIFEST.removeprefix("out-user/")
        target.parent.mkdir(parents=True)
        target.write_bytes(b"<manifest type='framework' version='9.0'/>\n")
        result = vintf.audit(self.graph, PRODUCT, output_root=self.out)
        self.assertEqual(result["missing_artifact_count"], 2)
        self.assertEqual(result["artifacts"][MANIFEST], {
            "state": "present", "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "size_bytes": target.stat().st_size})
        self.assertFalse(result["compatibility_verified"])

    def test_graph_symlink_fails(self):
        alias = self.root / "graph-link"
        alias.symlink_to(self.graph)
        with self.assertRaisesRegex(vintf.VintfAuditError, "regular file"):
            vintf.audit(alias, PRODUCT)

    def test_symlinked_artifact_and_ancestor_fail(self):
        target = self.out / MANIFEST.removeprefix("out-user/")
        target.parent.mkdir(parents=True)
        target.symlink_to(self.graph)
        with self.assertRaises(vintf.VintfAuditError):
            vintf.audit(self.graph, PRODUCT, output_root=self.out)
        target.unlink()
        directory = target.parent
        directory.rmdir()
        directory.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(vintf.VintfAuditError, "ancestor"):
            vintf.audit(self.graph, PRODUCT, output_root=self.out)

    def test_nonregular_artifact_and_size_overflow_fail(self):
        target = self.root / "artifact"
        target.mkdir()
        with self.assertRaisesRegex(vintf.VintfAuditError, "regular file"):
            vintf.inspect_artifact(target, max_bytes=2)
        target.rmdir()
        target.write_bytes(b"abc")
        with self.assertRaisesRegex(vintf.VintfAuditError, "size bound"):
            vintf.inspect_artifact(target, max_bytes=2)

    def test_graph_change_during_artifact_audit_fails(self):
        def change_graph(*args, **kwargs):
            with self.graph.open("ab") as stream:
                stream.write(b"# producer changed the graph\n")
            return {"state": "missing"}, None
        with patch.object(vintf, "inspect_artifact", side_effect=change_graph):
            with self.assertRaisesRegex(vintf.VintfAuditError, "graph changed"):
                vintf.audit(self.graph, PRODUCT, output_root=self.out)

    def test_initially_missing_artifact_created_later_fails(self):
        target = self.out / MANIFEST.removeprefix("out-user/")
        original = vintf.inspect_artifact
        calls = 0
        def create_after_capture(path, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                target.parent.mkdir(parents=True)
                target.write_bytes(b"appeared")
            return original(path, **kwargs)
        with patch.object(vintf, "inspect_artifact", side_effect=create_after_capture):
            with self.assertRaisesRegex(vintf.VintfAuditError, "appeared"):
                vintf.audit(self.graph, PRODUCT, output_root=self.out)

    def test_prior_artifact_change_during_later_capture_fails(self):
        target = self.out / MANIFEST.removeprefix("out-user/")
        target.parent.mkdir(parents=True)
        target.write_bytes(b"original")
        original = vintf.inspect_artifact
        calls = 0
        def change_after_capture(path, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                target.write_bytes(b"changed")
            return original(path, **kwargs)
        with patch.object(vintf, "inspect_artifact", side_effect=change_after_capture):
            with self.assertRaisesRegex(vintf.VintfAuditError, "artifact changed"):
                vintf.audit(self.graph, PRODUCT, output_root=self.out)

    def test_audit_does_not_create_output_files_or_change_inputs(self):
        before = sorted(str(x.relative_to(self.root)) for x in self.root.rglob("*"))
        original = self.graph.read_bytes()
        vintf.audit(self.graph, PRODUCT, output_root=self.out)
        self.assertEqual(self.graph.read_bytes(), original)
        self.assertEqual(sorted(str(x.relative_to(self.root)) for x in self.root.rglob("*")), before)


if __name__ == "__main__":
    unittest.main()
