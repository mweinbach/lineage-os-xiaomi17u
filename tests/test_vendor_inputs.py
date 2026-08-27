"""Synthetic offline checks for private, deterministic vendor generation."""

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import vendor_inputs as vendor
from scripts.firmware import IntakeError

VendorInputError = vendor.VendorInputError


def elf_library(bits=64):
    size = 64 if bits == 64 else 52
    data = bytearray(size)
    data[:7] = b"\x7fELF" + bytes([2 if bits == 64 else 1, 1, 1])
    struct.pack_into("<HHI", data, 16, 3, 183 if bits == 64 else 40, 1)
    struct.pack_into("<H", data, 52 if bits == 64 else 40, size)
    return bytes(data)


def dex_jar(members=None):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name, content in (members or {"classes.dex": b"dex\n039\x00" + b"\x00" * 104}).items():
            archive.writestr(name, content)
    return data.getvalue()


class VendorInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.addCleanup(patch.stopall)
        patch.object(vendor, "WORKSPACE_ROOT", self.root).start()
        self.package_sha = "1" * 64
        self.super_sha = "2" * 64
        self.analysis = self.root / "artifacts/analysis"
        self.logical = self.analysis / "logical-partitions"
        self.logical.mkdir(parents=True)
        self.source_record = self.root / "source-record.json"
        self.output = self.root / "artifacts/vendor-inputs/first"
        self.layout = {"schema_version": 1, "device": {"codename": "nezha", "hardware_region": "CN"},
                       "package": {"sha256": self.package_sha, "source_kind": "user-provided", "origin_verified": False},
                       "raw_image": {"sha256": self.super_sha}, "partitions": [],
                       "verification_boundaries": {"avb_partition_set_status": "failed"}}
        self.receipt = {"schema_version": 1, "status": "complete", "source_image": {"sha256": self.super_sha},
                        "all_geometry_and_metadata_copies_valid": True,
                        "all_primary_backup_pairs_match": True, "all_slots_identical": True, "outputs": []}
        for index, name in enumerate(("vendor_a", "odm_a")):
            content = bytearray([index + 10] * 2048)
            content[1024:1028] = b"\xe2\xe1\xf5\xe0"
            data = bytes(content)
            (self.logical / (name + ".img")).write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            extraction = {"status": "extracted", "sha256": digest, "size_bytes": len(data),
                          "parent_image_sha256": self.super_sha, "readback_verified": True}
            self.layout["partitions"].append({"name": name, "size_bytes": len(data), "extraction": extraction,
                                               "filesystem": {"format": "EROFS"}})
            self.receipt["outputs"].append({"partition": name, "filename": name + ".img",
                                             "sha256": digest, "size_bytes": len(data),
                                             "parent_image_sha256": self.super_sha, "readback_verified": True})
        self.save_metadata()

    def save_metadata(self):
        self.source_record.write_text(json.dumps(self.layout))
        (self.logical / "receipt.json").write_text(json.dumps(self.receipt))

    def stage(self, output=None, **kwargs):
        return vendor.stage_inputs(self.analysis, self.source_record, output or self.output,
                                   expected_package_sha256=self.package_sha, **kwargs)

    def snapshot(self):
        return {str(p): p.read_bytes() for p in [self.source_record, *sorted(self.logical.iterdir())] if p.is_file()}

    def assert_preserved(self, before):
        self.assertEqual(before, {name: Path(name).read_bytes() for name in before})

    def assert_no_output(self):
        self.assertFalse(self.output.exists())
        if self.output.parent.exists():
            self.assertEqual(list(self.output.parent.iterdir()), [])

    def add_extras(self, specs):
        """Build tiny synthetic LP/inventory/capture chains without external tools."""
        image = b"system-ext-synthetic-image"
        digest = hashlib.sha256(image).hexdigest()
        name = "system_ext_a"
        (self.logical / (name + ".img")).write_bytes(image)
        self.layout["partitions"].append({
            "name": name, "size_bytes": len(image), "filesystem": {"format": "EROFS"},
            "extraction": {"status": "extracted", "sha256": digest, "parent_image_sha256": self.super_sha,
                           "readback_verified": True},
        })
        self.receipt["outputs"].append({"partition": name, "filename": name + ".img", "sha256": digest,
                                       "size_bytes": len(image), "parent_image_sha256": self.super_sha,
                                       "readback_verified": True})
        self.save_metadata()
        inventory_dir = self.analysis / "erofs/system_ext_a-inventory"
        inventory_dir.mkdir(parents=True)
        self.capture_dir = self.analysis / "erofs/system_ext-contract-capture"
        (self.capture_dir / "files").mkdir(parents=True)
        image_record = {"path": str(self.logical / (name + ".img")), "sha256": digest, "size_bytes": len(image)}
        inventory = {"schema_version": 1, "image": image_record, "entries": []}
        capture = {"schema_version": 1, "operation": "erofs-capture", "firmware_executed": False,
                   "image_mounted": False, "symlinks_followed": False, "image": image_record, "files": []}
        modules = []
        for index, spec in enumerate(specs, 1):
            runtime, kind, content = spec[:3]
            image_path = runtime.removeprefix("/system_ext")
            filename = f"files/{index:04d}"
            (self.capture_dir / filename).write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            inventory["entries"].append({"path": image_path, "type": "regular", "nid": index})
            capture["files"].append({"path": image_path, "type": "regular", "nid": index,
                                     "output_path": filename, "sha256": digest, "size_bytes": len(content),
                                     "readback_verified": True})
            module = {"runtime_path": runtime, "type": kind, "sha256": digest, "size_bytes": len(content)}
            if kind == "shared_library":
                module["shared_libs"] = spec[3] if len(spec) > 3 else ["libc", "libm", "libdl"]
            modules.append(module)
        raw = json.dumps(inventory).encode()
        (inventory_dir / "inventory.json").write_bytes(raw)
        inventory_sha = hashlib.sha256(raw).hexdigest()
        scan = {"schema_version": 1, "operation": "erofs-scan", "image": image_record,
                "inventory": {"sha256": inventory_sha}, "image_mounted": False, "symlinks_followed": False}
        raw = json.dumps(scan).encode()
        (inventory_dir / "receipt.json").write_bytes(raw)
        capture.update(inventory_sha256=inventory_sha, inventory_receipt_sha256=hashlib.sha256(raw).hexdigest())
        self.capture = capture
        self.capture_path = self.capture_dir / "receipt.json"
        self.capture_path.write_text(json.dumps(capture))
        self.selection = {"schema_version": 1, "device": "nezha", "package_sha256": self.package_sha, "modules": modules}
        self.selection_path = self.root / "selection.json"
        self.selection_path.write_text(json.dumps(self.selection))
        return self.selection_path

    def add_registration(self, *, old_file=None):
        self.registration_name = "camerax-vendor-extensions.jar"
        target = "/system_ext/framework/camerax-vendor-extensions.jar"
        self.registration_old_file = old_file or target
        source = (f'<permissions><library name="{self.registration_name}" '
                  f'file="{self.registration_old_file}"/>'
                  '<library name="unrelated" file="/system_ext/framework/unrelated.jar"/>'
                  '<app-data-isolation-whitelisted-app package="unrelated"/></permissions>').encode()
        self.add_extras([
            (target, "dex_jar", dex_jar()),
            ("/system_ext/etc/permissions/platform-miui.xml", "xml", source),
        ])
        self.registration_output = ('<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n'
                                    f'    <library name="{self.registration_name}" file="{target}" />\n'
                                    '</permissions>\n').encode()
        captured = self.selection["modules"].pop()
        self.recipe = {"kind": "library-registration-v1",
                       "source": {key: captured[key] for key in ("runtime_path", "sha256", "size_bytes")},
                       "library_name": self.registration_name, "source_library_file": self.registration_old_file,
                       "library_file": target}
        self.derived_module = {"runtime_path": "/system_ext/etc/permissions/camerax-vendor-extensions.xml",
                               "sha256": hashlib.sha256(self.registration_output).hexdigest(),
                               "size_bytes": len(self.registration_output), "type": "xml", "derivation": self.recipe}
        self.selection["modules"].append(self.derived_module)
        self.selection_path.write_text(json.dumps(self.selection))
        self.registration_source = self.capture_dir / "files/0002"
        return self.selection_path

    def replace_registration_source(self, content):
        self.registration_source.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        self.capture["files"][1].update(sha256=digest, size_bytes=len(content))
        self.capture_path.write_text(json.dumps(self.capture))
        self.recipe["source"].update(sha256=digest, size_bytes=len(content))
        self.selection_path.write_text(json.dumps(self.selection))

    def test_plan_is_metadata_only_and_does_not_create_outputs(self):
        before = self.snapshot()
        with patch.object(vendor, "_copy_blob", side_effect=AssertionError("not a staging operation")):
            result = vendor.plan_inputs(self.analysis, self.source_record, expected_package_sha256=self.package_sha)
        self.assertEqual(result["operation"], "vendor-inputs-plan")
        self.assertEqual(result["total_blob_bytes"], 4096)
        self.assertFalse(result["verification"]["input_blob_hashes_checked"])
        self.assertTrue(all(not item["readback_verified"] for item in result["images"].values()))
        self.assert_no_output()
        self.assert_preserved(before)

    def test_default_stage_copies_images_and_generates_expected_contract(self):
        before = self.snapshot()
        result = self.stage()
        self.assertEqual(result["operation"], "vendor-inputs-stage")
        self.assertEqual(result["install_path"], "vendor/xiaomi/nezha")
        self.assertEqual(result["source"]["package_sha256"], self.package_sha)
        self.assertEqual(result["source"]["source_record_sha256"], hashlib.sha256(self.source_record.read_bytes()).hexdigest())
        self.assertEqual(result["source"]["input_avb_status"], "failed")
        self.assertFalse(result["source"]["origin_verified"])
        self.assertEqual(result["extras"], [])
        self.assertTrue(result["verification"]["input_blob_hashes_checked"])
        self.assertFalse(result["verification"]["avb_checked_by_this_tool"])
        self.assertFalse(result["verification"]["signature_or_elf_checks_disabled"])
        for part, item in result["images"].items():
            self.assertEqual(item["path"], f"proprietary/images/{part}.img")
            self.assertEqual((self.output / item["path"]).read_bytes(), (self.logical / f"{part}_a.img").read_bytes())
        for item in [*result["images"].values(), *result["generated_files"]]:
            data = (self.output / item["path"]).read_bytes()
            self.assertEqual(len(data), item["size_bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            self.assertTrue(item["readback_verified"])
        board = (self.output / "BoardConfigVendor.mk").read_text()
        self.assertIn("BOARD_PREBUILT_VENDORIMAGE := $(NEZHA_VENDOR_PATH)/proprietary/images/vendor.img", board)
        self.assertIn("BOARD_PREBUILT_ODMIMAGE := $(NEZHA_VENDOR_PATH)/proprietary/images/odm.img", board)
        self.assertNotIn("AVB", board)
        self.assertNotIn("vbmeta", board)
        product = (self.output / "nezha-vendor.mk").read_text()
        self.assertIn("PRODUCT_SOONG_NAMESPACES += $(NEZHA_VENDOR_PATH)", product)
        self.assertNotIn("PRODUCT_COPY_FILES", product)
        self.assertNotIn("PRODUCT_PACKAGES", product)
        self.assertEqual(json.loads((self.output / "vendor-inputs.json").read_text()), result)
        self.assert_preserved(before)

    def test_generation_is_byte_deterministic_across_new_destinations(self):
        self.stage()
        other = self.output.with_name("second")
        self.stage(other)
        first_files = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        second_files = {p.relative_to(other): p.read_bytes() for p in other.rglob("*") if p.is_file()}
        self.assertEqual(first_files, second_files)

    def test_all_generated_host_files_are_private_and_not_executable(self):
        self.stage()
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for path in self.output.rglob("*"):
            self.assertFalse(path.is_symlink())
            if path.is_file():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.output / ".gitignore").read_text(), "*\n!.gitignore\n")

    def test_existing_destination_is_never_changed(self):
        self.output.mkdir(parents=True)
        marker = self.output / "keep"
        marker.write_text("existing")
        with self.assertRaises(VendorInputError):
            self.stage()
        self.assertEqual(marker.read_text(), "existing")

    def test_wrong_package_or_device_is_rejected(self):
        for field, value in (("codename", "other"), ("hardware_region", "GLOBAL")):
            with self.subTest(field=field):
                original = self.layout["device"][field]
                self.layout["device"][field] = value
                self.save_metadata()
                with self.assertRaises(VendorInputError):
                    self.stage()
                self.layout["device"][field] = original
        self.layout["package"]["sha256"] = "3" * 64
        self.save_metadata()
        with self.assertRaises(VendorInputError):
            self.stage()
        self.assert_no_output()

    def test_mismatched_parent_or_partition_receipt_is_rejected(self):
        original = copy.deepcopy(self.receipt)
        for key, value in (("sha256", "3" * 64), ("parent_image_sha256", "4" * 64),
                           ("filename", "../vendor_a.img"), ("readback_verified", False), ("size_bytes", 1)):
            with self.subTest(key=key):
                self.receipt = copy.deepcopy(original)
                self.receipt["outputs"][0][key] = value
                self.save_metadata()
                with self.assertRaises(VendorInputError):
                    self.stage()
                self.assert_no_output()

    def test_duplicate_record_names_and_json_keys_are_rejected(self):
        self.receipt["outputs"].append(copy.deepcopy(self.receipt["outputs"][0]))
        self.save_metadata()
        with self.assertRaises(VendorInputError):
            self.stage()
        self.source_record.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(VendorInputError):
            self.stage()
        self.assert_no_output()

    def test_input_hash_mismatch_cleans_staging_and_preserves_inputs(self):
        path = self.logical / "vendor_a.img"
        data = bytearray(path.read_bytes())
        data[0] ^= 1
        path.write_bytes(data)
        before = self.snapshot()
        with self.assertRaisesRegex(VendorInputError, "SHA256"):
            self.stage()
        self.assert_no_output()
        self.assert_preserved(before)

    def test_metadata_mutation_during_copy_prevents_publication(self):
        real_copy = vendor._copy_blob

        def copy_then_mutate(source, target):
            real_copy(source, target)
            if source["record"]["source_partition"] == "vendor_a":
                self.source_record.write_bytes(self.source_record.read_bytes() + b"\n")

        with patch.object(vendor, "_copy_blob", side_effect=copy_then_mutate):
            with self.assertRaisesRegex(VendorInputError, "changed"):
                self.stage()
        self.assert_no_output()

    def test_corruption_after_first_readback_is_detected_before_publication(self):
        real_copy = vendor._copy_blob

        def copy_then_corrupt(source, target):
            real_copy(source, target)
            if source["record"]["source_partition"] == "vendor_a":
                data = bytearray(target.read_bytes())
                data[0] ^= 1
                target.write_bytes(data)

        before = self.snapshot()
        with patch.object(vendor, "_copy_blob", side_effect=copy_then_corrupt):
            with self.assertRaisesRegex(VendorInputError, "readback"):
                self.stage()
        self.assert_no_output()
        self.assert_preserved(before)

    def test_blob_mutation_after_copy_prevents_publication(self):
        real_copy = vendor._copy_blob

        def copy_then_mutate(source, target):
            real_copy(source, target)
            if source["record"]["source_partition"] == "vendor_a":
                source["file"].write_bytes(source["file"].read_bytes() + b"x")

        with patch.object(vendor, "_copy_blob", side_effect=copy_then_mutate):
            with self.assertRaisesRegex(VendorInputError, "changed"):
                self.stage()
        self.assert_no_output()

    def test_image_format_mismatch_is_not_hidden_by_matching_hash(self):
        path = self.logical / "vendor_a.img"
        path.write_bytes(b"x" * 2048)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.layout["partitions"][0]["extraction"]["sha256"] = digest
        self.receipt["outputs"][0]["sha256"] = digest
        self.save_metadata()
        with self.assertRaisesRegex(VendorInputError, "EROFS"):
            self.stage()
        self.assert_no_output()

    def test_symlink_input_or_output_parent_is_rejected(self):
        path = self.logical / "vendor_a.img"
        saved = path.with_suffix(".saved")
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaises((VendorInputError, IntakeError)):
            self.stage()
        path.unlink()
        saved.rename(path)
        self.output.parent.parent.mkdir(parents=True, exist_ok=True)
        self.output.parent.symlink_to(self.logical, target_is_directory=True)
        with self.assertRaises((VendorInputError, IntakeError)):
            self.stage()
        self.assertFalse((self.logical / self.output.name).exists())

    def test_output_must_be_private_and_outside_input_analysis(self):
        for output in (self.root / "vendor/xiaomi/nezha", self.analysis / "vendor-tree"):
            with self.subTest(output=output):
                with self.assertRaises(VendorInputError):
                    self.stage(output)
                self.assertFalse(output.exists())

    def test_size_and_free_disk_bounds_prevent_copying(self):
        with self.assertRaises(VendorInputError):
            self.stage(max_bytes=4095)
        usage = type("Usage", (), {"free": 1})()
        with patch.object(vendor.shutil, "disk_usage", return_value=usage):
            with self.assertRaisesRegex(VendorInputError, "disk space"):
                self.stage()
        self.assert_no_output()

    def test_concurrent_destination_is_preserved_by_exclusive_publication(self):
        real_publish = vendor.publish_new_directory

        def race(staging, destination):
            destination.mkdir()
            (destination / "sentinel").write_text("other writer")
            real_publish(staging, destination)

        before = self.snapshot()
        with patch.object(vendor, "publish_new_directory", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.stage()
        self.assertEqual((self.output / "sentinel").read_text(), "other writer")
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])
        self.assert_preserved(before)

    def test_earlier_output_mutation_during_later_final_readback_is_detected(self):
        real_verify = vendor._verify_output
        calls = {}

        def verify_then_mutate(path, record):
            result = real_verify(path, record)
            calls[path.name] = calls.get(path.name, 0) + 1
            if path.name == "odm.img" and calls[path.name] == 2:
                earlier = path.with_name("vendor.img")
                data = bytearray(earlier.read_bytes())
                data[0] ^= 1
                earlier.write_bytes(data)
            return result

        with patch.object(vendor, "_verify_output", side_effect=verify_then_mutate):
            with self.assertRaisesRegex(VendorInputError, "changed"):
                self.stage()
        self.assert_no_output()

    def test_nonobject_nested_metadata_fails_without_attribute_errors(self):
        for key in ("device", "package", "raw_image", "verification_boundaries"):
            with self.subTest(key=key):
                original = self.layout[key]
                self.layout[key] = []
                self.save_metadata()
                with self.assertRaises(VendorInputError):
                    self.stage()
                self.layout[key] = original
        self.save_metadata()
        for key in ("extraction", "filesystem"):
            with self.subTest(key=key):
                original = self.layout["partitions"][0][key]
                self.layout["partitions"][0][key] = None
                self.save_metadata()
                with self.assertRaises(VendorInputError):
                    self.stage()
                self.layout["partitions"][0][key] = original
        self.assert_no_output()

    def test_selected_so_dex_and_xml_keep_partition_architecture_and_names(self):
        permission = b'<permissions><library name="miui-test" file="/system/framework/miui-test.jar"/></permissions>'
        selection = self.add_extras([
            ("/system_ext/lib64/libxiaomi.so", "shared_library", elf_library()),
            ("/system_ext/lib/libxiaomi32.so", "shared_library", elf_library(32)),
            ("/system_ext/framework/miui-test.jar", "dex_jar", dex_jar()),
            ("/system_ext/etc/permissions/miui-test.xml", "xml", permission),
        ])
        result = self.stage(selection=selection)
        self.assertEqual(len(result["extras"]), 4)
        bp = (self.output / "Android.bp").read_text()
        self.assertEqual(bp.count("cc_prebuilt_library_shared {"), 2)
        self.assertIn("android_arm64: {", bp)
        self.assertIn("android_arm: {", bp)
        self.assertIn('compile_multilib: "64"', bp)
        self.assertIn('compile_multilib: "32"', bp)
        self.assertIn('stem: "libxiaomi"', bp)
        self.assertIn("check_elf_files: true", bp)
        self.assertNotIn("check_elf_files: false", bp)
        self.assertIn("strip: { none: true }", bp)
        self.assertNotIn("system_shared_libs", bp)
        self.assertIn("dex_import {", bp)
        self.assertIn('stem: "miui-test"', bp)
        self.assertIn("prebuilt_etc_xml {", bp)
        self.assertIn('relative_install_path: "permissions"', bp)
        self.assertNotIn("provides_uses_lib", bp)
        self.assertNotIn("enforce_uses_libs", bp)
        product = (self.output / "nezha-vendor.mk").read_text()
        for entry in result["extras"]:
            self.assertTrue(entry["readback_verified"])
            self.assertTrue(entry["module_name"].startswith("nezha_"))
            self.assertEqual(entry["path"], "proprietary" + entry["runtime_path"])
            self.assertIn(entry["module_name"], product)
            self.assertEqual(hashlib.sha256((self.output / entry["path"]).read_bytes()).hexdigest(), entry["sha256"])
        self.assertEqual((self.output / "proprietary/system_ext/etc/permissions/miui-test.xml").read_bytes(), permission)
        self.assertFalse(result["verification"]["full_dependency_closure_verified"])

    def test_selection_reordering_is_normalized_for_make_and_blueprint_outputs(self):
        selection = self.add_extras([
            ("/system_ext/lib64/libxiaomi.so", "shared_library", elf_library(), ["libm", "libc", "libdl"]),
            ("/system_ext/framework/miui-test.jar", "dex_jar", dex_jar()),
        ])
        self.stage(selection=selection)
        self.selection["modules"].reverse()
        self.selection_path.write_text(json.dumps(self.selection))
        other = self.output.with_name("second")
        self.stage(other, selection=selection)
        for filename in ("Android.bp", "BoardConfigVendor.mk", "nezha-vendor.mk"):
            self.assertEqual((self.output / filename).read_bytes(), (other / filename).read_bytes())

    def test_selection_rejects_framework_conflicts_unsafe_paths_or_bypass_fields(self):
        selection = self.add_extras([("/system_ext/framework/miui-test.jar", "dex_jar", dex_jar())])
        original = copy.deepcopy(self.selection)
        for path in ("/vendor/framework/miui-test.jar", "/system/framework/miui-test.jar",
                     "/system_ext/framework/framework.jar", "/system_ext/../framework/a.jar",
                     "/system_ext/framework/$(id).jar", "/system_ext/framework/a jar.jar"):
            with self.subTest(path=path):
                self.selection = copy.deepcopy(original)
                self.selection["modules"][0]["runtime_path"] = path
                selection.write_text(json.dumps(self.selection))
                with self.assertRaises(VendorInputError):
                    self.stage(selection=selection)
        self.selection = original
        self.selection["modules"][0]["check_elf_files"] = False
        selection.write_text(json.dumps(self.selection))
        with self.assertRaises(VendorInputError):
            self.stage(selection=selection)
        self.assert_no_output()

    def test_selection_rejects_apk_and_conflicting_module_names(self):
        selection = self.add_extras([("/system_ext/framework/miui-test.jar", "dex_jar", dex_jar())])
        self.selection["modules"][0]["type"] = "apk"
        selection.write_text(json.dumps(self.selection))
        with self.assertRaises(VendorInputError):
            self.stage(selection=selection)
        self.selection["modules"][0]["type"] = "dex_jar"
        other = dict(self.selection["modules"][0], runtime_path="/system_ext/framework/miui.test.jar")
        self.selection["modules"].append(other)
        selection.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(VendorInputError, "colliding"):
            self.stage(selection=selection)
        self.assert_no_output()

    def test_selection_hash_and_capture_parent_identity_must_match(self):
        selection = self.add_extras([("/system_ext/framework/miui-test.jar", "dex_jar", dex_jar())])
        original = copy.deepcopy(self.capture)
        for change in ("parent", "inventory", "inode", "symlink", "readback", "flat-path"):
            with self.subTest(change=change):
                self.capture = copy.deepcopy(original)
                if change == "parent":
                    self.capture["image"]["sha256"] = "a" * 64
                elif change == "inventory":
                    self.capture["inventory_sha256"] = "a" * 64
                elif change == "inode":
                    self.capture["files"][0]["nid"] = 999
                elif change == "symlink":
                    self.capture["files"][0]["type"] = "symlink"
                elif change == "readback":
                    self.capture["files"][0]["readback_verified"] = False
                else:
                    self.capture["files"][0]["output_path"] = "../outside.jar"
                self.capture_path.write_text(json.dumps(self.capture))
                with self.assertRaises(VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_selected_blob_hash_mismatch_is_rejected_even_with_valid_receipts(self):
        selection = self.add_extras([("/system_ext/framework/miui-test.jar", "dex_jar", dex_jar())])
        blob = self.capture_dir / "files/0001"
        data = bytearray(blob.read_bytes())
        data[-1] ^= 1
        blob.write_bytes(data)
        with self.assertRaisesRegex(VendorInputError, "SHA256"):
            self.stage(selection=selection)
        self.assert_no_output()

    def test_elf_architecture_directory_mismatch_or_truncation_is_rejected(self):
        for content in (elf_library(32), elf_library()[:52]):
            with self.subTest(size=len(content)):
                path = self.root / "bad.so"
                path.write_bytes(content)
                with self.assertRaises(VendorInputError):
                    vendor._validate_format(path, {"runtime_path": "/system_ext/lib64/bad.so"}, "shared_library")

    def test_class_jar_fake_dex_unsafe_zip_and_malformed_xml_are_rejected(self):
        for members in ({"A.class": b"class"}, {"classes.dex": b"not dex"},
                        {"classes.dex": b"dex\n039\x00" + bytes(104), "../escape": b"x"},
                        {"classes.dex": b"dex\n049\x00" + bytes(104)},
                        {"classes.dex": b"dex\n039\x00" + bytes(104), "classes10.dex": b"not dex"},
                        {"classes.dex": b"dex\n039\x00" + bytes(104), "classes100.dex": b"not dex"}):
            with self.subTest(members=list(members)):
                path = self.root / "bad.jar"
                path.write_bytes(dex_jar(members))
                with self.assertRaises(VendorInputError):
                    vendor._validate_format(path, {}, "dex_jar")
        path = self.root / "bad.xml"
        path.write_bytes(b"<not-closed>")
        with self.assertRaises(VendorInputError):
            vendor._validate_format(path, {"size_bytes": path.stat().st_size}, "xml")

    def test_no_phone_or_external_process_is_needed(self):
        with patch("subprocess.run", side_effect=AssertionError("no external commands")), \
                patch("subprocess.Popen", side_effect=AssertionError("no external commands")):
            self.stage()

    def test_registration_plan_neither_reads_source_bytes_nor_claims_verified_inputs(self):
        selection = self.add_registration()
        real_open = vendor._open_regular

        def metadata_only(path):
            if path == self.registration_source or path.parent == self.capture_dir / "files" or path.suffix == ".img":
                raise AssertionError("plan cannot read blob bytes")
            return real_open(path)

        with patch.object(vendor, "_derive_registration", side_effect=AssertionError("plan cannot derive")), \
                patch.object(vendor, "_copy_blob", side_effect=AssertionError("plan cannot copy")), \
                patch.object(vendor, "_open_regular", side_effect=metadata_only):
            result = vendor.plan_inputs(self.analysis, self.source_record, selection=selection,
                                       expected_package_sha256=self.package_sha)
        derived = next(entry for entry in result["extras"] if "derivation" in entry)
        self.assertFalse(derived["readback_verified"])
        self.assertFalse(derived["derivation"]["source"]["hash_verified"])
        self.assertFalse(result["verification"]["input_blob_hashes_checked"])
        self.assert_no_output()

    def test_registration_stage_selects_only_one_library_and_records_full_derivation(self):
        selection = self.add_registration()
        before = self.snapshot()
        before.update({str(path): path.read_bytes() for path in
                       (self.registration_source, self.selection_path, self.capture_path)})
        with patch("subprocess.run", side_effect=AssertionError("no external commands")), \
                patch("subprocess.Popen", side_effect=AssertionError("no external commands")):
            result = self.stage(selection=selection)
        derived = next(entry for entry in result["extras"] if "derivation" in entry)
        self.assertEqual((self.output / derived["path"]).read_bytes(), self.registration_output)
        self.assertEqual(derived["sha256"], hashlib.sha256(self.registration_output).hexdigest())
        self.assertTrue(derived["readback_verified"])
        self.assertNotIn("nid", derived)  # The output is derived, not an original image inode.
        provenance = derived["derivation"]
        self.assertEqual(provenance["kind"], "library-registration-v1")
        self.assertEqual(provenance["recipe_sha256"], hashlib.sha256(
            json.dumps(self.recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(provenance["source"]["sha256"], self.recipe["source"]["sha256"])
        self.assertTrue(provenance["source"]["hash_verified"])
        self.assertEqual(provenance["source"]["nid"], 2)
        self.assertEqual(provenance["source"]["image_sha256"], self.capture["image"]["sha256"])
        self.assertEqual(provenance["source"]["capture_receipt_sha256"],
                         hashlib.sha256(self.capture_path.read_bytes()).hexdigest())
        self.assertFalse((self.output / "proprietary/system_ext/etc/permissions/platform-miui.xml").exists())
        self.assertNotIn(b"unrelated", self.registration_output)
        self.assertFalse(result["verification"]["signature_or_elf_checks_disabled"])
        self.assertFalse(result["verification"]["full_dependency_closure_verified"])
        self.assert_preserved(before)

    def test_registration_path_correction_keeps_original_source_and_records_old_and_new(self):
        selection = self.add_registration(old_file="/system/framework/camerax-vendor-extensions.jar")
        original = self.registration_source.read_bytes()
        result = self.stage(selection=selection)
        derived = next(entry for entry in result["extras"] if "derivation" in entry)
        recipe = derived["derivation"]
        self.assertEqual(recipe["source_library_file"], "/system/framework/camerax-vendor-extensions.jar")
        self.assertEqual(recipe["library_file"], "/system_ext/framework/camerax-vendor-extensions.jar")
        self.assertEqual(self.registration_source.read_bytes(), original)
        self.assertEqual((self.output / derived["path"]).read_bytes(), self.registration_output)
        self.assertTrue(all(not path.is_symlink() for path in self.output.rglob("*")))

    def test_derived_registration_is_deterministic_and_never_changes_earlier_bundle(self):
        self.stage()
        base = {path: path.read_bytes() for path in self.output.rglob("*") if path.is_file()}
        selection = self.add_registration()
        first, second = self.output.with_name("camera-1"), self.output.with_name("camera-2")
        self.stage(first, selection=selection)
        self.stage(second, selection=selection)
        self.assertEqual({path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()},
                         {path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()})
        self.assertEqual(base, {path: path.read_bytes() for path in base})

    def test_registration_rejects_extra_attributes_tags_nested_entries_and_duplicate_names(self):
        selection = self.add_registration()
        selected = f'<library name="{self.registration_name}" file="{self.registration_old_file}"/>'
        with_dependency = selected.replace("/>", ' dependency="hidden"/>')
        bad_sources = [
            f'<permissions bad="1">{selected}</permissions>',
            f'<permissions>{with_dependency}</permissions>',
            f'<permissions>{selected.replace("library ", "permission ")}</permissions>',
            f'<permissions><group>{selected}</group></permissions>',
            f'<permissions>{selected}{selected}</permissions>',
            f'<permissions>{selected.replace("/>", "><permission/></library>")}</permissions>',
            f'<permissions>{selected.replace(self.registration_old_file, "/system/framework/other.jar")}</permissions>',
            '<permissions/>',
            '<wrong-root/>',
            '<permissions><library',
        ]
        for content in bad_sources:
            with self.subTest(content=content):
                self.replace_registration_source(content.encode())
                before = self.snapshot()
                with self.assertRaises(VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()
                self.assert_preserved(before)

    def test_registration_rejects_dtd_entity_and_non_utf8_sources(self):
        selection = self.add_registration()
        selected = f'<library name="{self.registration_name}" file="{self.registration_old_file}"/>'
        for content in (f'<!DOCTYPE permissions [<!ENTITY hidden "secret">]><permissions>{selected}</permissions>'.encode(),
                        f'<permissions>{selected}</permissions>'.encode("utf-16"),
                        b'\xff<permissions/>'):
            with self.subTest(content=content):
                self.replace_registration_source(content)
                with self.assertRaises(VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_registration_requires_selected_dex_target_and_rejects_filename_changes(self):
        selection = self.add_registration()
        original = copy.deepcopy(self.selection)
        for change in ("missing-target", "wrong-type", "wrong-name", "wrong-partition", "duplicate-name"):
            with self.subTest(change=change):
                self.selection = copy.deepcopy(original)
                if change == "missing-target":
                    del self.selection["modules"][0]
                elif change == "wrong-type":
                    self.selection["modules"][0]["type"] = "xml"
                elif change == "wrong-name":
                    self.selection["modules"][1]["derivation"]["source_library_file"] = "/system/framework/other.jar"
                elif change == "wrong-partition":
                    self.selection["modules"][1]["derivation"]["library_file"] = "/system/framework/camerax-vendor-extensions.jar"
                else:
                    duplicate = copy.deepcopy(self.selection["modules"][1])
                    duplicate["runtime_path"] = "/system_ext/etc/permissions/another.xml"
                    self.selection["modules"].append(duplicate)
                selection.write_text(json.dumps(self.selection))
                with self.assertRaises(VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_registration_rejects_unbound_sources_unknown_recipes_and_output_hash_changes(self):
        selection = self.add_registration()
        original = copy.deepcopy(self.selection)
        for change in ("source-hash", "source-size", "source-path", "source-bound", "kind", "extra-field",
                       "unsafe-name", "output-hash", "output-size", "output-path"):
            with self.subTest(change=change):
                self.selection = copy.deepcopy(original)
                module = self.selection["modules"][1]
                recipe = module["derivation"]
                if change == "source-hash":
                    recipe["source"]["sha256"] = "a" * 64
                elif change == "source-size":
                    recipe["source"]["size_bytes"] += 1
                elif change == "source-path":
                    recipe["source"]["runtime_path"] = "/system_ext/etc/permissions/missing.xml"
                elif change == "source-bound":
                    recipe["source"]["size_bytes"] = vendor.MAX_XML_BYTES + 1
                elif change == "kind":
                    recipe["kind"] = "arbitrary-xml-transform"
                elif change == "extra-field":
                    recipe["allow_checks_off"] = True
                elif change == "unsafe-name":
                    recipe["library_name"] = 'injected"/>'
                elif change == "output-hash":
                    module["sha256"] = "a" * 64
                elif change == "output-size":
                    module["size_bytes"] += 1
                else:
                    module["runtime_path"] = "/system_ext/etc/init/register.xml"
                selection.write_text(json.dumps(self.selection))
                with self.assertRaises(VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_registration_source_corruption_and_symlink_are_rejected(self):
        selection = self.add_registration()
        original = self.registration_source.read_bytes()
        self.registration_source.write_bytes(original.replace(b"unrelated", b"different"))
        before = self.registration_source.read_bytes()
        with self.assertRaisesRegex(VendorInputError, "SHA256"):
            self.stage(selection=selection)
        self.assert_no_output()
        self.assertEqual(self.registration_source.read_bytes(), before)
        saved = self.registration_source.with_suffix(".saved")
        self.registration_source.rename(saved)
        self.registration_source.symlink_to(saved)
        with self.assertRaises((VendorInputError, IntakeError)):
            self.stage(selection=selection)
        self.assert_no_output()
        self.assertEqual(saved.read_bytes(), before)

    def test_registration_readback_corruption_cleans_staging_and_preserves_captures(self):
        selection = self.add_registration()
        original = self.registration_source.read_bytes()
        real_write = vendor._write_file

        def write_then_corrupt(staging, name, content):
            result = real_write(staging, name, content)
            if name == "camerax-vendor-extensions.xml":
                (staging / name).write_bytes(content + b"x")
            return result

        with patch.object(vendor, "_write_file", side_effect=write_then_corrupt):
            with self.assertRaisesRegex(VendorInputError, "readback"):
                self.stage(selection=selection)
        self.assert_no_output()
        self.assertEqual(self.registration_source.read_bytes(), original)

    def test_registration_source_mutation_after_derivation_prevents_publication(self):
        selection = self.add_registration()
        real_derive = vendor._derive_registration

        def derive_then_mutate(source, destination):
            real_derive(source, destination)
            source["file"].write_bytes(source["file"].read_bytes() + b"\n")

        with patch.object(vendor, "_derive_registration", side_effect=derive_then_mutate):
            with self.assertRaisesRegex(VendorInputError, "changed"):
                self.stage(selection=selection)
        self.assert_no_output()


if __name__ == "__main__":
    unittest.main()
