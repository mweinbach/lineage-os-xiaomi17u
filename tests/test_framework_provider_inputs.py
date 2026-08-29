"""Offline provider admission tests with synthetic ELF/XML/capture data only."""

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import tempfile
import unittest
from unittest import mock

from scripts import framework_provider_inputs as provider


WORKSPACE = Path(__file__).resolve().parents[1]


def elf(needed, *, soname=None, interpreter=None, search_path=None, machine=183):
    """A small bounded ELF64 fixture, never executed or linked."""
    strings = bytearray(b"\0")

    def string(value):
        offset = len(strings)
        strings.extend(value.encode() + b"\0")
        return offset

    dynamic = [(1, string(name)) for name in needed]
    if soname is not None:
        dynamic.append((14, string(soname)))
    if search_path is not None:
        dynamic.append((29, string(search_path)))
    dynamic += [(5, 0x500), (10, len(strings)), (0, 0)]
    data = bytearray(0x900)
    data[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    count = 3 if interpreter is not None else 2
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, 3, machine, 1, 0x400, 64, 0, 0,
                     64, 56, count, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0, 0, len(data), len(data), 4096)
    struct.pack_into("<IIQQQQQQ", data, 120, 2, 6, 0x200, 0x200, 0, len(dynamic) * 16,
                     len(dynamic) * 16, 8)
    if interpreter is not None:
        raw = interpreter.encode() + b"\0"
        struct.pack_into("<IIQQQQQQ", data, 176, 3, 4, 0x400, 0x400, 0, len(raw), len(raw), 1)
        data[0x400:0x400 + len(raw)] = raw
    for index, pair in enumerate(dynamic):
        struct.pack_into("<qQ", data, 0x200 + index * 16, *pair)
    data[0x500:0x500 + len(strings)] = strings
    return bytes(data)


class FrameworkProviderInputsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root / "workspace"
        (self.workspace / "config").mkdir(parents=True)
        (self.workspace / "artifacts").mkdir()
        self.capture = self.root / "capture"
        self.capture.mkdir()
        self.output = self.workspace / "artifacts/bundle"
        self.originals = {}
        self.contract = {
            "schema_version": 1, "device": "nezha", "bundle": provider.BUNDLE,
            "module_package": provider.MODULE_PACKAGE,
            "platform": {"branch": "bka", "release": "bp4a", "board_api": "202504"},
            "factory_package_sha256": "a" * 64,
            "factory_image": {"partition": "system_ext", "sha256": "b" * 64, "size_bytes": 1234567},
            "source_lock": {"path": "config/source-lock.json", **provider.identity(b"synthetic source lock\n")},
            "captures": {}, "files": [], "providers": [],
            "source_dependencies": {"libc.so": "libc"}, "source_replacements": [],
            "required_source_patches": [], "runtime_requirements": ["Runtime is not tested."],
            "scope": copy.deepcopy(provider.SCOPE),
        }
        (self.workspace / "config/source-lock.json").write_bytes(b"synthetic source lock\n")
        self.capture_receipt = {"schema_version": 1, "operation": "erofs-capture",
                                "image": {"sha256": "b" * 64, "size_bytes": 1234567},
                                "image_mounted": False, "firmware_executed": False,
                                "symlinks_followed": False, "files": []}
        for number, name in enumerate(("alpha", "beta"), 1):
            binary = "/system_ext/bin/" + name
            library = "lib" + name + ".so"
            self.add_file(binary, "binary", elf([library, "libc.so"], interpreter="/system/bin/linker64"),
                          needed=[library, "libc.so"], soname=None)
            self.add_file("/system_ext/lib64/" + library, "shared_library", elf(["libc.so"], soname=library),
                          needed=["libc.so"], soname=library)
            init = "/system_ext/etc/init/" + name + ".rc"
            self.add_file(init, "init_rc", ("service " + name + " " + binary +
                                            "\n    class hal\n    user system\n").encode())
            manifest = "/system_ext/etc/vintf/manifest/" + name + ".xml"
            self.add_file(manifest, "vintf_fragment", (
                '<manifest version="9.0" type="framework"><hal format="aidl">'
                '<name>vendor.example.' + name + '</name><fqname>I' + name + '/default</fqname>'
                '</hal></manifest>\n').encode())
            self.contract["providers"].append({"binary": binary, "init_rc": init, "vintf_fragment": manifest,
                                               "hal": "vendor.example." + name, "interface": "I" + name,
                                               "instance": "default", "init_service": name,
                                               "service_context": name + "_service", "domain": name + "_domain",
                                               "exec_type": name + "_exec"})
        self.add_file("/system_ext/etc/settings.xml", "etc", b"<settings/>\n")
        self.write_capture()
        self.write_contract()
        self.enterContext(mock.patch.object(provider, "ROOT", self.workspace))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("no native or firmware processes")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("no shell execution")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("no network")))

    def add_file(self, runtime, kind, data, **extra):
        name = "files/" + str(len(self.contract["files"]) + 1).zfill(4)
        path = self.capture / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        self.originals[path] = data
        mode = "0755" if kind == "binary" else "0644"
        row = {"runtime_path": runtime, "kind": kind, "capture": "capture", "capture_path": name,
               "mode": mode, **provider.identity(data), **extra}
        if kind in {"binary", "shared_library", "etc"}:
            row["module"] = "nezha_framework_" + Path(runtime).name.removesuffix(".so").removesuffix(".xml")
        self.contract["files"].append(row)
        self.capture_receipt["files"].append({"path": runtime.removeprefix("/system_ext"),
                                                "output_path": name, "type": "regular", "mode": mode,
                                                "readback_verified": True, **provider.identity(data)})

    def write_capture(self):
        raw = provider.encoded(self.capture_receipt)
        (self.capture / "receipt.json").write_bytes(raw)
        self.contract["captures"]["capture"] = {"path": "receipt.json", **provider.identity(raw)}
        self.originals[self.capture / "receipt.json"] = raw

    def write_contract(self):
        (self.workspace / provider.CONTRACT).write_bytes(provider.encoded(self.contract))

    def replace_data(self, runtime, data):
        row = next(row for row in self.contract["files"] if row["runtime_path"] == runtime)
        row.update(provider.identity(data))
        path = self.capture / row["capture_path"]
        path.write_bytes(data)
        self.originals[path] = data
        captured = next(item for item in self.capture_receipt["files"] if item["output_path"] == row["capture_path"])
        captured.update(provider.identity(data))
        self.write_capture()
        self.write_contract()

    def stage(self, output=None):
        return provider.stage_inputs(self.capture, output or self.output)

    def reject(self, callback=None):
        with self.assertRaises((ValueError, OSError, KeyError)):
            (callback or self.stage)()

    def native_checker(self, root=None):
        root = root or self.output
        namespace = {"__name__": "offline_test"}
        raw = (root / "tools/verify_framework_provider_inputs.py").read_bytes()
        exec(compile(raw, "generated_provider_checker", "exec"), namespace)
        arguments = [str(root / name) for name in namespace["EXPECTED"]]
        return namespace["main"], arguments

    def test_stage_verifies_originals_private_modes_and_native_definitions(self):
        receipt = self.stage()
        result = provider.verify_bundle(self.output)
        self.assertEqual(result["files"], receipt["files"])
        self.assertEqual(result["scope"], provider.SCOPE)
        self.assertEqual(len(result["providers"]), 2)
        self.assertEqual(len(result["packages"]), 5)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        for row in receipt["files"]:
            self.assertEqual(stat.S_IMODE((self.output / row["path"]).stat().st_mode), 0o600)
        for path, raw in self.originals.items():
            self.assertEqual(path.read_bytes(), raw)
        blueprint = (self.output / provider.MODULE_BLUEPRINT).read_text()
        self.assertEqual(blueprint.count("check_elf_files: true"), 4)
        self.assertEqual(blueprint.count("allow_undefined_symbols: false"), 4)
        self.assertEqual(blueprint.count("vintf_fragments:"), 2)
        self.assertEqual(blueprint.count("init_rc:"), 2)
        self.assertEqual(blueprint.count('required: ["' + provider.CHECK + '"]'), 5)
        self.assertNotIn("PRODUCT_COPY_FILES", (self.output / "framework-providers.mk").read_text())
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_repeat_staging_is_byte_identical(self):
        first = self.stage()
        second = self.stage(self.workspace / "artifacts/second")
        self.assertEqual(first, second)
        self.assertEqual((self.output / provider.RECEIPT).read_bytes(),
                         (self.workspace / "artifacts/second" / provider.RECEIPT).read_bytes())

    def test_product_makefile_selects_only_the_verified_module_tokens(self):
        receipt = self.stage()
        makefile = (self.output / "framework-providers.mk").read_text()
        logical = makefile.replace("\\\n", " ")
        packages = []
        namespaces = []
        for line in logical.splitlines():
            if not line or line.startswith("#"):
                continue
            variable, assignment, values = line.partition("+=")
            self.assertEqual(assignment, "+=")
            if variable.strip() == "PRODUCT_PACKAGES":
                packages.extend(values.split())
            elif variable.strip() == "PRODUCT_SOONG_NAMESPACES":
                namespaces.extend(values.split())
            else:
                self.fail("unexpected generated product assignment")
        self.assertEqual(packages, receipt["packages"] + [provider.CHECK])
        self.assertEqual(namespaces, [provider.BUNDLE, provider.MODULE_PACKAGE])

    def test_private_filegroups_export_only_to_the_exact_device_package(self):
        self.stage()
        private_bp = (self.output / "Android.bp").read_text()
        device_bp = (self.output / provider.MODULE_BLUEPRINT).read_text()
        self.assertEqual(private_bp.count('visibility: ["//' + provider.MODULE_PACKAGE + ':__pkg__"]'), 9)
        self.assertNotIn("cc_prebuilt", private_bp)
        self.assertNotIn("//visibility:public", private_bp)
        self.assertNotIn("//vendor:__subpackages__", private_bp)
        self.assertNotIn('srcs: ["proprietary', device_bp)
        self.assertIn('soong_namespace { imports: ["' + provider.BUNDLE + '"] }', device_bp)

    def test_fresh_relocated_capture_is_accepted_without_rewriting_metadata(self):
        relocated = self.root / "relocated"
        shutil.copytree(self.capture, relocated)
        receipt = provider.stage_inputs(relocated, self.output)
        self.assertEqual(receipt["factory_image"], self.contract["factory_image"])

    def test_existing_directory_is_never_replaced(self):
        self.output.mkdir()
        marker = self.output / "existing"
        marker.write_bytes(b"preserve")
        self.reject()
        self.assertEqual(marker.read_bytes(), b"preserve")

    def test_existing_file_is_never_replaced(self):
        self.output.write_bytes(b"preserve")
        self.reject()
        self.assertEqual(self.output.read_bytes(), b"preserve")

    def test_output_must_remain_in_ignored_locations(self):
        self.reject(lambda: self.stage(self.workspace / "public-bundle"))
        self.assertFalse((self.workspace / "public-bundle").exists())

    def test_changed_blob_hash_fails_before_publication(self):
        path = self.capture / self.contract["files"][0]["capture_path"]
        path.write_bytes(path.read_bytes() + b"unreviewed")
        self.reject()
        self.assertFalse(self.output.exists())

    def test_changed_capture_receipt_fails(self):
        path = self.capture / "receipt.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.reject()

    def test_missing_capture_file_fails(self):
        (self.capture / self.contract["files"][0]["capture_path"]).unlink()
        self.reject()

    def test_symlink_blob_is_rejected_even_with_matching_bytes(self):
        path = self.capture / self.contract["files"][0]["capture_path"]
        target = self.root / "target"
        path.rename(target)
        path.symlink_to(target)
        self.reject()

    def test_symlink_capture_parent_is_rejected(self):
        target = self.root / "real-capture"
        self.capture.rename(target)
        self.capture.symlink_to(target, target_is_directory=True)
        self.reject()

    def test_symlink_output_parent_is_rejected(self):
        parent = self.workspace / "artifacts/link"
        parent.symlink_to(self.root, target_is_directory=True)
        self.reject(lambda: self.stage(parent / "bundle"))

    def test_source_lock_drift_is_rejected(self):
        (self.workspace / "config/source-lock.json").write_bytes(b"different source selection\n")
        self.reject()

    def test_newer_platform_cannot_be_selected_incidentally(self):
        self.contract["platform"]["branch"] = "cnb"
        self.write_contract()
        self.reject()

    def test_readiness_or_relaxed_check_claim_is_rejected(self):
        self.contract["scope"]["complete_rom_admitted"] = True
        self.write_contract()
        self.reject()

    def test_unreviewed_alternate_contract_is_rejected(self):
        different = self.root / "other.json"
        different.write_bytes(provider.encoded({**self.contract, "schema_version": 2}))
        self.reject(lambda: provider.stage_inputs(self.capture, self.output, contract_path=different))

    def test_duplicate_json_key_is_rejected(self):
        path = self.workspace / provider.CONTRACT
        path.write_bytes(path.read_bytes().replace(b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,'))
        self.reject()

    def test_duplicate_destination_is_rejected(self):
        self.contract["files"].append(copy.deepcopy(self.contract["files"][0]))
        self.write_contract()
        self.reject()

    def test_unsafe_capture_path_is_rejected(self):
        for path in ("../secret", "/absolute", "files/./0001", "files//0001", "files/$(command)"):
            with self.subTest(path=path):
                self.contract["files"][0]["capture_path"] = path
                self.write_contract()
                self.reject()

    def test_unsafe_module_name_is_rejected(self):
        self.contract["files"][0]["module"] = "nezha_framework_$(command)"
        self.write_contract()
        self.reject()

    def test_capture_image_mismatch_is_rejected(self):
        self.capture_receipt["image"]["sha256"] = "c" * 64
        self.write_capture()
        self.write_contract()
        self.reject()

    def test_capture_runtime_path_mismatch_is_rejected(self):
        self.capture_receipt["files"][0]["path"] = "/bin/wrong"
        self.write_capture()
        self.write_contract()
        self.reject()

    def test_capture_factory_mode_mismatch_is_rejected(self):
        self.capture_receipt["files"][0]["mode"] = "0644"
        self.write_capture()
        self.write_contract()
        self.reject()

    def test_source_library_cannot_also_be_staged_as_a_prebuilt(self):
        self.contract["source_dependencies"]["libalpha.so"] = "libalpha"
        self.write_contract()
        self.reject()

    def test_missing_dt_needed_module_is_rejected(self):
        self.contract["source_dependencies"].clear()
        self.write_contract()
        self.reject()

    def test_unused_source_dependency_is_rejected(self):
        self.contract["source_dependencies"]["libunused.so"] = "libunused"
        self.write_contract()
        self.reject()

    def test_duplicate_elf_dependencies_are_rejected(self):
        self.contract["files"][0]["needed"].append("libc.so")
        self.write_contract()
        self.reject()

    def test_elf_dynamic_dependencies_are_checked_in_actual_bytes(self):
        self.replace_data("/system_ext/bin/alpha", elf(["libc.so", "libalpha.so"], interpreter="/system/bin/linker64"))
        self.reject()

    def test_wrong_elf_machine_is_rejected(self):
        self.replace_data("/system_ext/bin/alpha", elf(["libalpha.so", "libc.so"], interpreter="/system/bin/linker64", machine=62))
        self.reject()

    def test_elf_interpreter_is_required_for_a_provider_binary(self):
        self.replace_data("/system_ext/bin/alpha", elf(["libalpha.so", "libc.so"]))
        self.reject()

    def test_shared_library_cannot_be_an_executable(self):
        self.replace_data("/system_ext/lib64/libalpha.so", elf(["libc.so"], soname="libalpha.so", interpreter="/system/bin/linker64"))
        self.reject()

    def test_unreviewed_search_path_is_rejected(self):
        self.replace_data("/system_ext/lib64/libalpha.so", elf(["libc.so"], soname="libalpha.so", search_path="/vendor/lib64"))
        self.reject()

    def test_wrong_actual_soname_is_rejected(self):
        self.replace_data("/system_ext/lib64/libalpha.so", elf(["libc.so"], soname="libother.so"))
        self.reject()

    def test_init_must_start_the_selected_executable(self):
        self.replace_data("/system_ext/etc/init/alpha.rc", b"service alpha /system_ext/bin/unselected\n    user system\n")
        self.reject()

    def test_extra_init_service_is_rejected(self):
        self.replace_data("/system_ext/etc/init/alpha.rc", b"service alpha /system_ext/bin/alpha\nservice other /system_ext/bin/other\n")
        self.reject()

    def test_manifest_without_the_selected_binary_is_rejected(self):
        self.contract["providers"][0]["binary"] = "/system_ext/bin/missing"
        self.write_contract()
        self.reject()

    def test_manifest_extra_hal_is_rejected(self):
        path = "/system_ext/etc/vintf/manifest/alpha.xml"
        row = next(row for row in self.contract["files"] if row["runtime_path"] == path)
        raw = (self.capture / row["capture_path"]).read_bytes().replace(b"</manifest>", b'<hal format="aidl"><name>other</name></hal></manifest>')
        self.replace_data(path, raw)
        self.reject()

    def test_xml_entities_are_rejected(self):
        self.replace_data("/system_ext/etc/settings.xml", b'<!DOCTYPE settings [<!ENTITY x "bad">]><settings>&x;</settings>')
        self.reject()

    def test_bundle_generated_definitions_cannot_disable_elf_checks(self):
        self.stage()
        path = self.output / provider.MODULE_BLUEPRINT
        path.write_text(path.read_text().replace("check_elf_files: true", "check_elf_files: false"))
        self.reject(lambda: provider.verify_bundle(self.output))

    def test_bundle_receipt_cannot_claim_runtime_readiness(self):
        self.stage()
        path = self.output / provider.RECEIPT
        record = json.loads(path.read_bytes())
        record["scope"]["runtime_policy_admitted"] = True
        path.write_bytes(provider.encoded(record))
        self.reject(lambda: provider.verify_bundle(self.output))

    def test_bundle_extra_file_and_empty_directory_are_rejected(self):
        self.stage()
        extra = self.output / "extra"
        extra.write_bytes(b"unreviewed")
        self.reject(lambda: provider.verify_bundle(self.output))
        extra.unlink()
        extra.mkdir()
        self.reject(lambda: provider.verify_bundle(self.output))

    def test_native_generated_byte_checker_runs_on_every_real_input(self):
        self.stage()
        checker, arguments = self.native_checker()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            checker(arguments)
        result = json.loads(output.getvalue())
        self.assertEqual(result, {"verified": True, "input_count": 12, "firmware_executed": False})

    def test_native_checker_rejects_missing_duplicate_and_unknown_inputs(self):
        self.stage()
        checker, arguments = self.native_checker()
        cases = [arguments[:-1], arguments[:-1] + [arguments[0]],
                 arguments[:-1] + [str(self.root / "unknown")]]
        for case in cases:
            with self.subTest(arguments=case):
                self.reject(lambda: checker(case))

    def test_native_checker_rejects_same_size_byte_change(self):
        self.stage()
        checker, arguments = self.native_checker()
        path = self.output / "proprietary/system_ext/bin/alpha"
        raw = path.read_bytes()
        path.write_bytes(raw[:-1] + b"X")
        self.reject(lambda: checker(arguments))

    def test_native_checker_rejects_matching_symlink(self):
        self.stage()
        checker, arguments = self.native_checker()
        path = self.output / "proprietary/system_ext/bin/alpha"
        target = self.root / "same-file"
        path.rename(target)
        path.symlink_to(target)
        self.reject(lambda: checker(arguments))

    def test_repository_contract_validates_without_private_inputs(self):
        with mock.patch.object(provider, "ROOT", WORKSPACE):
            contract, _ = provider.load_contract()
        self.assertEqual(len(contract["files"]), 31)
        self.assertEqual(len(contract["providers"]), 2)
        self.assertEqual(sum(row["kind"] == "shared_library" for row in contract["files"]), 24)
        self.assertFalse(any(contract["scope"].values()))


if __name__ == "__main__":
    unittest.main()
