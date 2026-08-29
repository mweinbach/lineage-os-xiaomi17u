"""Offline metadata projection tests; fixtures are not Android images or APEXes."""

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from scripts import target_files_metadata as m


WORKSPACE = m.ROOT


class TargetFilesMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.controls, self.inputs, self.source = [self.root / name for name in ("controls", "inputs", "source")]
        for directory in (self.controls, self.inputs, self.source):
            directory.mkdir()
        self.bundle = self.root / "bundle"
        self.composition = m.compose_sources(WORKSPACE)
        for path in (m.PROFILE, *m.CONTROL_TOOLS, *m.SOURCE_CONTRACTS,
                     *(row["path"] for row in self.composition["ordered_patches"])):
            self.write(self.controls / path, (WORKSPACE / path).read_bytes())
        self.composition["final_source_files"] = []
        for path in (m.CORE, m.COMMON):
            data = ("Inert source " + path).encode()
            self.write(self.source / path, data)
            self.composition["final_source_files"].append({"path": path, **m.identity(data)})
        self.enterContext(mock.patch.object(m, "compose_sources", return_value=self.composition))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native processes forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.images = {name: self.root / (name + ".img") for name in ("vendor", "odm")}
        identities = {}
        for name, path in self.images.items():
            path.write_bytes(("Inert " + name + " image; not an EROFS image.\n").encode())
            identities[name] = m.identity(path.read_bytes())
        self.enterContext(mock.patch.object(m, "EXPECTED_IMAGES", identities))
        counts = {"vendor": {"properties": 2, "apex": 1}, "odm": {"properties": 2, "apex": 0}}
        self.enterContext(mock.patch.object(m, "EXPECTED_COUNTS", counts))
        self.payloads = {
            "vendor": {"/build.prop": b"ro.vendor.test=original\n",
                       "/odm_dlkm/etc/build.prop": b"ro.vendor.dlkm=original\n",
                       "/etc/vintf/manifest.xml": b"<manifest/>\n",
                       "/apex/inert.apex": b"Inert complete-package fixture, not executable.\n"},
            "odm": {"/etc/build.prop": b"ro.product.first_api_level=36\nimport /odm/etc/nezha_${ro.boot.region}.prop\n",
                    "/etc/nezha_test.prop": b"ro.odm.test=original\n",
                    "/etc/vintf/manifest.xml": b"<manifest/>\n"},
        }
        self.profile = {"schema_version": 1, "contract_id": "nezha-factory-target-files-metadata-v1",
                        "device": "nezha", "branch": "bka", "release": "bp4a", "bundle": m.BUNDLE,
                        "factory_package_sha256": m.EXPECTED_PACKAGE, "partitions": {}, "scope": copy.deepcopy(m.SCOPE)}
        self.inventories, self.inventory_receipts, self.captures = {}, {}, {}
        for partition, payloads in self.payloads.items():
            directories = {"/"}
            for path in payloads:
                current = Path(path).parent
                while current.as_posix() != "/":
                    directories.add(current.as_posix())
                    current = current.parent
            rows = [{"path": path, "type": "directory", "nid": i + 1}
                    for i, path in enumerate(sorted(directories))]
            rows += [{"path": path, "type": "regular", "nid": len(rows) + i + 1}
                     for i, path in enumerate(sorted(payloads))]
            self.inventories[partition] = {"schema_version": 1, "image": identities[partition], "entries": rows}
            tool = {"sha256": hashlib.sha256(b"inert exporter").hexdigest(), "size_bytes": 14}
            self.inventory_receipts[partition] = {
                "schema_version": 1, "operation": "erofs-scan", "entry_count": len(rows),
                "image": identities[partition], "image_mounted": False, "origin_verified": False,
                "symlinks_followed": False, "tool": tool,
            }
            captured = []
            for index, (path, data) in enumerate(sorted(payloads.items())):
                row = next(row for row in rows if row["path"] == path)
                member = f"files/{index:04}"
                self.write(self.inputs / partition / "capture" / member, data)
                captured.append({**row, "output_path": member, "readback_verified": True, **m.identity(data)})
            self.captures[partition] = {
                "schema_version": 1, "operation": "erofs-capture", "image": identities[partition],
                "image_mounted": False, "origin_verified": False, "symlinks_followed": False,
                "firmware_executed": False, "tool": tool, "files": captured,
            }
            self.profile["partitions"][partition] = {
                "image": identities[partition], "entry_count": len(rows),
                "counts": {**counts[partition], "vintf": 1},
            }
        self.save_inputs()

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def save_inputs(self):
        for partition in ("vendor", "odm"):
            rule = self.profile["partitions"][partition]
            raw = m.encoded(self.inventories[partition])
            path = f"{partition}/inventory.json"
            self.write(self.inputs / path, raw)
            rule["inventory"] = {"path": path, **m.identity(raw)}
            self.inventory_receipts[partition]["inventory"] = m.identity(raw)
            raw = m.encoded(self.inventory_receipts[partition])
            path = f"{partition}/inventory-receipt.json"
            self.write(self.inputs / path, raw)
            rule["inventory_receipt"] = {"path": path, **m.identity(raw)}
            self.captures[partition].update(inventory_sha256=rule["inventory"]["sha256"],
                                           inventory_receipt_sha256=rule["inventory_receipt"]["sha256"])
            raw = m.encoded(self.captures[partition])
            path = f"{partition}/capture/receipt.json"
            self.write(self.inputs / path, raw)
            rule["captures"] = [{"path": path, **m.identity(raw)}]
        self.write(self.controls / m.PROFILE, m.encoded(self.profile))

    def stage(self, destination=None):
        return m.stage(self.inputs, destination or self.bundle, vendor_image=self.images["vendor"],
                       odm_image=self.images["odm"], controls_root=self.controls)

    def digest(self):
        return m.identity((self.bundle / m.RECEIPT).read_bytes())["sha256"]

    def verify(self, **kwargs):
        return m.verify_bundle(self.bundle, expected_receipt=self.digest(), **kwargs)

    def target_files(self):
        target = self.root / "target-files"
        (target / "META").mkdir(parents=True)
        (target / "IMAGES").mkdir()
        for partition, path in self.images.items():
            shutil.copyfile(path, target / "IMAGES" / (partition + ".img"))
        (target / "META/misc_info.txt").write_text(
            "building_vendor_image=\nbuilding_odm_image=\nab_update=true\nvintf_enforce=true\n")
        (target / "META/kernel_version.txt").write_text("inert-kernel-version\n")
        (target / "META/kernel_configs.txt").write_text("CONFIG_INERT=y\n")
        return target

    def install(self, target):
        return m.install(self.bundle, target, expected_receipt=self.digest(), source_tree=self.source)

    def test_stage_verify_and_install_preserve_exact_content_and_images(self):
        first = self.stage()
        verified, _, _ = self.verify(source_tree=self.source, vendor_image=self.images["vendor"], odm_image=self.images["odm"])
        self.assertEqual(first, verified)
        self.assertEqual(7, len(first["files"]))
        self.assertFalse(first["scope"]["vintf_verified"])
        self.assertFalse(first["property_closure"]["runtime_imports_resolved"])
        target = self.target_files()
        self.install(target)
        for partition, payloads in self.payloads.items():
            self.assertEqual(self.images[partition].read_bytes(), (target / "IMAGES" / (partition + ".img")).read_bytes())
            for path, data in payloads.items():
                self.assertEqual(data, (target / (partition.upper() + path)).read_bytes())
        self.assertFalse((target / "ODM_DLKM").exists())
        self.assertFalse((target / "META/vendor_filesystem_config.txt").exists())

    def test_repeated_staging_is_byte_identical(self):
        self.stage()
        second = self.root / "bundle-second"
        self.stage(second)
        self.assertEqual(m._files(self.bundle), m._files(second))
        for path in m._files(self.bundle):
            self.assertEqual((self.bundle / path).read_bytes(), (second / path).read_bytes(), path)

    def test_stage_refuses_existing_output(self):
        self.bundle.mkdir()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "new bundle"):
            self.stage()

    def test_changed_original_image_refused_before_publication(self):
        self.images["vendor"].write_bytes(b"different")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.stage()
        self.assertFalse(self.bundle.exists())

    def test_missing_capture_path_refused(self):
        self.captures["odm"]["files"].pop()
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "lacks a capture"):
            self.stage()

    def test_capture_changed_bytes_refused(self):
        row = self.captures["vendor"]["files"][0]
        (self.inputs / "vendor/capture" / row["output_path"]).write_bytes(b"corrupt")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.stage()

    def test_capture_without_readback_refused(self):
        self.captures["vendor"]["files"][0]["readback_verified"] = False
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "capture differs"):
            self.stage()

    def test_capture_from_another_image_refused(self):
        self.captures["vendor"]["image"] = m.EXPECTED_IMAGES["odm"]
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "provenance"):
            self.stage()

    def test_inventory_missing_parent_refused(self):
        self.inventories["vendor"]["entries"] = [row for row in self.inventories["vendor"]["entries"] if row["path"] != "/apex"]
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "parent"):
            self.stage()

    def test_inventory_receipt_wrong_entry_count_refused(self):
        self.inventory_receipts["vendor"]["entry_count"] += 1
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "inventory receipt"):
            self.stage()

    def test_inventory_internal_image_binding_refused(self):
        self.inventories["vendor"]["image"] = m.EXPECTED_IMAGES["odm"]
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "inventory schema or image"):
            self.stage()

    def test_inventory_unknown_schema_and_oversized_nid_refused(self):
        original = copy.deepcopy(self.inventories["vendor"])
        for mutation in ("schema", "nid", "type", "shape", "directory_alias", "inode_type_alias"):
            self.inventories["vendor"] = copy.deepcopy(original)
            inv = self.inventories["vendor"]
            if mutation == "schema":
                inv["schema_version"] = True
            elif mutation == "nid":
                inv["entries"][-1]["nid"] = 2**64
            elif mutation == "type":
                inv["entries"][-1]["type"] = "unknown"
            elif mutation == "shape":
                inv["entries"][-1]["extra"] = "unreviewed"
            elif mutation == "directory_alias":
                inv["entries"][1]["nid"] = inv["entries"][0]["nid"]
            else:
                inv["entries"][-1]["nid"] = inv["entries"][0]["nid"]
            self.save_inputs()
            with self.subTest(mutation=mutation), self.assertRaises(m.TargetFilesMetadataError):
                self.stage()

    def test_real_factory_shell_name_in_unselected_inventory_does_not_become_a_dependency(self):
        inv = self.inventories["vendor"]
        inv["entries"] += [{"path": "/bin", "nid": 100, "type": "directory"},
                           {"path": "/bin/[", "nid": 101, "type": "regular"}]
        self.profile["partitions"]["vendor"]["entry_count"] += 2
        self.inventory_receipts["vendor"]["entry_count"] += 2
        self.save_inputs()
        receipt = self.stage()
        self.assertNotIn("VENDOR/bin/[", [row["target_path"] for row in receipt["files"]])

    def test_inventory_receipt_wrong_inventory_hash_refused(self):
        self.save_inputs()
        rule = self.profile["partitions"]["vendor"]
        path = self.inputs / rule["inventory_receipt"]["path"]
        value = json.loads(path.read_bytes())
        value["inventory"]["sha256"] = "a" * 64
        raw = m.encoded(value)
        path.write_bytes(raw)
        rule["inventory_receipt"].update(m.identity(raw))
        self.write(self.controls / m.PROFILE, m.encoded(self.profile))
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "inventory receipt"):
            self.stage()

    def test_selected_symlink_refused(self):
        next(row for row in self.inventories["vendor"]["entries"] if row["path"] == "/build.prop")["type"] = "symlink"
        self.save_inputs()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "regular"):
            self.stage()

    def test_symlink_and_hardlinked_payloads_refused(self):
        row = self.captures["vendor"]["files"][0]
        path = self.inputs / "vendor/capture" / row["output_path"]
        other = self.root / "other"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "regular"):
            self.stage()
        path.unlink()
        os.link(other, path)
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "single-link"):
            self.stage()

    def test_wrong_external_receipt_digest_refused(self):
        self.stage()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "receipt differs"):
            m.verify_bundle(self.bundle, expected_receipt="a" * 64)

    def test_no_self_certifying_receipt(self):
        self.stage()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "external"):
            m.verify_bundle(self.bundle, expected_receipt="")

    def test_modified_bundle_payload_refused(self):
        self.stage()
        (self.bundle / "tree/VENDOR/build.prop").write_bytes(b"changed")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.verify()

    def test_unlisted_bundle_file_and_empty_directory_refused(self):
        self.stage()
        path = self.bundle / "extra"
        path.write_bytes(b"unexpected")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "unlisted"):
            self.verify()
        path.unlink()
        path.mkdir()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "empty"):
            self.verify()

    def test_recomputed_receipt_cannot_change_scope(self):
        self.stage()
        receipt = json.loads((self.bundle / m.RECEIPT).read_bytes())
        receipt["scope"]["complete_rom_admitted"] = True
        (self.bundle / m.RECEIPT).write_bytes(m.encoded(receipt))
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "scope"):
            self.verify()

    def test_paired_images_required(self):
        self.stage()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "both"):
            self.verify(vendor_image=self.images["vendor"])

    def test_source_file_change_refused(self):
        self.stage()
        (self.source / m.CORE).write_bytes(b"unreviewed source")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.verify(source_tree=self.source)

    def test_collision_refused_without_touching_existing_tree(self):
        self.stage()
        target = self.target_files()
        self.write(target / "VENDOR/keep", b"preserve")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "collision"):
            self.install(target)
        self.assertEqual(b"preserve", (target / "VENDOR/keep").read_bytes())
        self.assertFalse((target / "ODM").exists())

    def test_packaged_image_change_refused(self):
        self.stage()
        target = self.target_files()
        (target / "IMAGES/odm.img").write_bytes(b"different packaged image")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.install(target)
        self.assertFalse((target / "VENDOR").exists())

    def test_missing_kernel_metadata_refused(self):
        self.stage()
        target = self.target_files()
        (target / "META/kernel_configs.txt").unlink()
        with self.assertRaises(OSError):
            self.install(target)
        self.assertFalse((target / "VENDOR").exists())

    def test_building_false_literal_is_not_empty_native_mode(self):
        self.stage()
        target = self.target_files()
        p = target / "META/misc_info.txt"
        p.write_text(p.read_text().replace("building_vendor_image=", "building_vendor_image=false"))
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "mode"):
            self.install(target)

    def test_missing_required_mode_key_is_not_empty(self):
        self.stage()
        target = self.target_files()
        p = target / "META/misc_info.txt"
        p.write_text(p.read_text().replace("building_vendor_image=\n", ""))
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "mode"):
            self.install(target)

    def test_duplicate_mode_key_refused(self):
        self.stage()
        target = self.target_files()
        p = target / "META/misc_info.txt"
        p.write_text(p.read_text() + "vintf_enforce=false\n")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "duplicate"):
            self.install(target)

    def test_partial_publication_rolls_back_only_owned_trees(self):
        self.stage()
        target = self.target_files()
        real = m._publish_at
        def publish(source_fd, old, destination_fd, new):
            if new == "ODM":
                raise OSError("inert publication failure")
            return real(source_fd, old, destination_fd, new)
        with mock.patch.object(m, "_publish_at", side_effect=publish):
            with self.assertRaises(OSError):
                self.install(target)
        self.assertFalse((target / "VENDOR").exists())
        self.assertFalse((target / "ODM").exists())
        self.assertTrue((target / "IMAGES/vendor.img").exists())

    def test_published_payload_readback_catches_change(self):
        self.stage()
        target = self.target_files()
        real = m._publish_at
        def publish(source_fd, old, destination_fd, new):
            result = real(source_fd, old, destination_fd, new)
            if new == "VENDOR":
                (target / "VENDOR/build.prop").write_bytes(b"changed after publication")
            return result
        with mock.patch.object(m, "_publish_at", side_effect=publish):
            with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
                self.install(target)
        self.assertFalse((target / "META/nezha_target_files_metadata.json").exists())
        self.assertFalse((target / "VENDOR").exists())

    def test_replaced_output_directory_is_not_removed_by_rollback(self):
        self.stage()
        target = self.target_files()
        real = m._publish_at
        def publish(source_fd, old, destination_fd, new):
            if new == "ODM":
                (target / "VENDOR").rename(target / "owned-vendor-moved")
                self.write(target / "VENDOR/foreign", b"preserve foreign writer")
                raise OSError("inert publication failure")
            return real(source_fd, old, destination_fd, new)
        with mock.patch.object(m, "_publish_at", side_effect=publish):
            with self.assertRaises(OSError):
                self.install(target)
        self.assertEqual(b"preserve foreign writer", (target / "VENDOR/foreign").read_bytes())
        self.assertTrue((target / "owned-vendor-moved/build.prop").exists())

    def test_meta_symlink_replacement_does_not_redirect_report(self):
        self.stage()
        target = self.target_files()
        outside = self.root / "outside"
        outside.mkdir()
        real = m._publish_at
        def publish(source_fd, old, destination_fd, new):
            if new == "ODM":
                (target / "META").rename(target / "original-meta")
                (target / "META").symlink_to(outside, target_is_directory=True)
            return real(source_fd, old, destination_fd, new)
        with mock.patch.object(m, "_publish_at", side_effect=publish):
            with self.assertRaisesRegex(m.TargetFilesMetadataError, "real directory"):
                self.install(target)
        self.assertEqual([], list(outside.iterdir()))
        self.assertFalse((target / "original-meta/nezha_target_files_metadata.json").exists())

    def test_late_bundle_addition_refused(self):
        self.stage()
        target = self.target_files()
        real = m._publish_at
        def publish(source_fd, old, destination_fd, new):
            result = real(source_fd, old, destination_fd, new)
            if new == "ODM":
                (self.bundle / "late-added").write_bytes(b"unlisted")
            return result
        with mock.patch.object(m, "_publish_at", side_effect=publish):
            with self.assertRaisesRegex(m.TargetFilesMetadataError, "bundle inventory"):
                self.install(target)
        self.assertFalse((target / "VENDOR").exists())

    def test_receipt_publication_failure_leaves_no_partial_report(self):
        self.stage()
        target = self.target_files()
        real = m._publish_at
        def publish(source_fd, old, destination_fd, new):
            if new == "nezha_target_files_metadata.json":
                raise OSError("inert receipt publication failure")
            return real(source_fd, old, destination_fd, new)
        with mock.patch.object(m, "_publish_at", side_effect=publish):
            with self.assertRaises(OSError):
                self.install(target)
        self.assertFalse((target / "META/nezha_target_files_metadata.json").exists())
        self.assertFalse((target / "VENDOR").exists())
        self.install(target)

    def test_selection_preserves_readiness_and_supplies_external_digest(self):
        self.stage()
        text = m.selection(self.bundle, expected_receipt=self.digest())
        self.assertIn(self.digest(), text)
        self.assertIn("BOARD_NEZHA_PREBUILT_METADATA := true", text)
        self.assertNotIn("NEZHA_COMPLETE_ROM", text)


class PropertyClosureTests(unittest.TestCase):
    def files(self, odm, vendor=b"ro.vendor.original=1\n", variant=b"ro.variant.original=1\n"):
        return {path: ({"partition": partition, "path": name, "kind": "properties"}, data)
                for path, partition, name, data in (
                    ("VENDOR/build.prop", "vendor", "/build.prop", vendor),
                    ("ODM/etc/build.prop", "odm", "/etc/build.prop", odm),
                    ("ODM/etc/nezha_test.prop", "odm", "/etc/nezha_test.prop", variant))}

    def test_literal_template_kept_and_no_selector_inferred(self):
        raw = b"ro.product.first_api_level=36\nimport /odm/etc/nezha_${ro.boot.region}.prop\n"
        result = m._property_closure(self.files(raw))
        self.assertEqual("/odm/etc/nezha_${ro.boot.region}.prop", result["imports"][0]["template"])
        self.assertEqual(["/odm/etc/nezha_test.prop"], result["imports"][0]["captured_targets"])
        self.assertFalse(result["imports"][0]["runtime_selector_value_inferred"])

    def test_missing_import_refused(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "no captured target"):
            m._property_closure(self.files(b"ro.product.first_api_level=36\nimport /odm/etc/missing.prop\n"))

    def test_import_cycle_refused(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "cycle"):
            m._property_closure(self.files(b"ro.product.first_api_level=36\nimport /odm/etc/nezha_test.prop\n",
                                          variant=b"import /odm/etc/build.prop\n"))

    def test_shipping_api_not_invented_in_vendor(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "original ODM"):
            m._property_closure(self.files(b"ro.product.first_api_level=36\n", vendor=b"ro.product.first_api_level=36\n"))

    def test_wrong_shipping_api_refused(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "shipping API differs"):
            m._property_closure(self.files(b"ro.product.first_api_level=35\n"))

    def test_malformed_import_refused(self):
        for line in (b"import", b"import /system/build.prop", b"import /odm/etc/$bad.prop", b"import /odm/etc/x.prop filter extra"):
            with self.subTest(line=line), self.assertRaises(m.TargetFilesMetadataError):
                m._property_closure(self.files(b"ro.product.first_api_level=36\n" + line + b"\n"))


class SourceCompositionTests(unittest.TestCase):
    def test_explicit_five_patch_chain_retains_exact_common_and_add_img(self):
        result = m.compose_sources(WORKSPACE)
        self.assertEqual(5, len(result["ordered_patches"]))
        rows = {row["path"]: row for row in result["final_source_files"]}
        self.assertEqual("66c76097fafb6d4422e617b232babc1fc9f5da3d5e8f0d52d925c8841104792d", rows[m.COMMON]["sha256"])
        self.assertEqual("ef2e4014238ad323e8157a3bf80190d1795f01b6dd0c087b5e8c2cc167a43c51",
                         rows["build/make/tools/releasetools/add_img_to_target_files.py"]["sha256"])
        self.assertFalse(result["patches_applied_by_this_tool"])

    def test_new_hook_is_before_add_images_and_does_not_change_image_rules(self):
        text = (WORKSPACE / m.PATCH).read_text()
        added = "\n".join(line[1:] for line in text.splitlines() if line.startswith("+") and not line.startswith("+++"))
        self.assertIn("$(BUILT_TARGET_FILES_DIR): $(NEZHA_PREBUILT_METADATA_FILES)", added)
        self.assertIn("--expected-receipt '$(subst ','\"'\"',", added)
        for forbidden in ("TARGET_OUT_VENDOR :=", "TARGET_OUT_ODM :=", "BUILDING_VENDOR_IMAGE :=", "BUILDING_ODM_IMAGE :=", "nodeps", "skip_compatibility", "SELINUX_IGNORE_NEVERALLOWS"):
            self.assertNotIn(forbidden, added)

    def test_duplicate_json_and_unsafe_path_refused(self):
        with self.assertRaises(m.TargetFilesMetadataError):
            m._json(b'{"key":1,"key":2}')
        for path in ("../x", "/absolute", "a//b", "a/$x", "a/`x`", "a/x y", "a/./b"):
            with self.subTest(path=path), self.assertRaises(m.TargetFilesMetadataError):
                m.relative(path)
        self.assertEqual("etc/vintf/manifest_vendor.xiaomi.hardware.otrpagent@2.0.xml",
                         m.relative("etc/vintf/manifest_vendor.xiaomi.hardware.otrpagent@2.0.xml"))


if __name__ == "__main__":
    unittest.main()
