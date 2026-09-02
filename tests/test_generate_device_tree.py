"""Offline candidate derivation and admission tests; no private inputs required."""

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import generate_device_tree as generator


ROOT = Path(__file__).resolve().parents[1]
METADATA_ROW = (
    "/dev/block/by-name/metadata /metadata f2fs noatime,nosuid,nodev,discard "
    "wait,check,formattable,first_stage_mount"
)
DATA_ROW = (
    "/dev/block/bootdevice/by-name/userdata /data f2fs "
    "noatime,nosuid,nodev,discard,inlinecrypt,atgc "
    "latemount,wait,check,fileencryption=aes-256-xts:aes-256-cts:v2+wrappedkey_v0,"
    "keydirectory=/metadata/vold/metadata_encryption,"
    "metadata_encryption=aes-256-xts:wrappedkey_v0,checkpoint=fs"
)
INVALID_VARIANTS = (
    "", " ", "eng", "production", "User", "user userdebug", "user eng",
    "userdebug userdebug", "user\tuserdebug", "user\neng", " user", "user ",
    None, True, 1, ["user"],
)
DENIED_FRAMEWORK_GOALS = (
    "evolution", "droid", "droid_targets", "droidcore", "droidcore-unbundled",
    "dist_files", "checkbuild", "target-files-package", "target-files-dir",
    "otapackage", "otardppackage", "partialotapackage", "updatepackage", "bacon",
    "superimage", "superimage_dist", "superimage-nodeps", "supernod",
    "superimage_empty", "super_empty",
)


class GenerateDeviceTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_records = {}
        cls.source_identities = {}
        for name in generator.RECORD_NAMES:
            raw = (ROOT / "research" / (name + ".json")).read_bytes()
            cls.source_records[name] = json.loads(raw)
            cls.source_identities[name] = {
                "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)
            }

    def setUp(self):
        self.records = copy.deepcopy(self.source_records)
        self.identities = copy.deepcopy(self.source_identities)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def plan(self, records=None, **options):
        return generator.derive_plan(records or self.records, self.identities, **options)

    def fstab(self, physical=None):
        boot = self.records["boot-contract"]
        rows = [
            " ".join(entry[key] for key in (
                "source", "mount_point", "filesystem", "mount_flags", "fs_mgr_flags"
            ))
            for entry in boot["first_stage_fstab"]["logical_mounts"]
        ]
        rows += [
            "/mnt/vendor/mi_ext /mi_ext erofs ro,bind wait,nofail",
            "overlay /system/framework overlay ro,lowerdir=/mi_ext/framework:/system/framework check,nofail",
        ]
        rows += [METADATA_ROW, DATA_ROW] if physical is None else physical
        raw = ("# Synthetic mount contract\n" + "\n".join(rows) + "\n").encode()
        path = self.root / "fstab.qcom"
        path.write_bytes(raw)
        boot["first_stage_fstab"]["sha256"] = hashlib.sha256(raw).hexdigest()
        return path

    def candidate(self, **options):
        plan = self.plan(**options)
        payloads = {
            (generator.DEVICE_PATH / name).as_posix(): b"# Synthetic candidate template\n"
            for name in generator.TEMPLATE_FILES
        }
        for name, data in {
            "BoardConfigCandidate.mk": b"BOARD_AVB_ENABLE := true\n",
            "device-candidate.mk": b"PRODUCT_ENFORCE_VINTF_MANIFEST := true\n",
            "fstab.qcom": b"# Synthetic candidate fstab\n",
        }.items():
            payloads[(generator.DEVICE_PATH / "generated" / name).as_posix()] = data
        payloads[generator.SECURITY_PATCH.as_posix()] = b"# Synthetic security patch\n"
        payloads[generator.SECURITY_RECORD.as_posix()] = b'{"schema_version": 1}\n'
        plan["files"] = []
        for name, data in sorted(payloads.items()):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            plan["files"].append({
                "path": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)
            })
        self.save_admission(plan)
        return plan

    def save_admission(self, plan):
        (self.root / "admission.json").write_text(json.dumps(plan), encoding="utf-8")

    def generation_inputs(self):
        """Small synthetic private artifacts, retaining only public record shape."""
        boot = self.records["boot-contract"]
        layout = self.records["firmware-layout"]
        boot["provenance"]["package_sha256"] = "2" * 64
        layout["package"]["sha256"] = "3" * 64
        kernel_root, vendor_root = self.root / "kernel", self.root / "vendor"
        kernel_root.mkdir()
        vendor_root.mkdir()

        def write(root, name, data):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {"path": name, "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "readback_verified": True}

        source = self.fstab()
        files = [write(kernel_root, "kernel/Image", b"synthetic kernel"),
                 write(kernel_root, "config/fstab.qcom", source.read_bytes())]
        boot["kernel"]["sha256"] = files[0]["sha256"]
        module_sets = {}
        for name, recorded in boot["dlkm_followup"]["sets"].items():
            recorded["file_count"] = 1
            path = f"modules/{name}/fixture.ko"
            files.append(write(kernel_root, path, b"synthetic module " + name.encode()))
            module_sets[name] = {"module_count": 1, "modules": [path]}
        kernel = {
            "schema_version": 1, "device": "nezha",
            "provenance": {"parent_package_sha256": "2" * 64, "origin_verified": False},
            "kernel": {"release": boot["kernel"]["release"], "page_size_bytes": 4096,
                       "boot_security_patch": "2026-02-01"},
            "files": files, "module_sets": module_sets, "roles": {"fstab": "config/fstab.qcom"},
            "validation": {"input_avb_status": "failed"},
        }
        kernel_path = kernel_root / "receipt.json"
        kernel_path.write_text(json.dumps(kernel))

        images = {}
        for name in ("vendor", "odm"):
            image = write(vendor_root, f"proprietary/images/{name}.img", name.encode() * 1024)
            image["source_partition"] = name + "_a"
            images[name] = image
            partition = next(part for part in layout["partitions"] if part["name"] == name + "_a")
            partition["size_bytes"] = image["size_bytes"]
            partition["extraction"]["sha256"] = image["sha256"]
        generated = [write(vendor_root, name, b"# synthetic bundle makefile\n")
                     for name in ("BoardConfigVendor.mk", "nezha-vendor.mk")]

        header = b"\n".join([
            b"vendor boot image header version: 4", b"page size: 0x00001000",
            b"kernel load address: 0x00008000", b"ramdisk load address: 0x01000000",
            b"kernel tags load address: 0x00000100", b"dtb address: 0x0000000001f00000",
            b"vendor command line args: video=vfb:640x400,bpp=32 erofs.reserved_pages=64 swinfo.fingerprint=fixture bootconfig",
            b"",
        ])
        evidence = self.root / "artifacts/boot-evidence"
        info = write(evidence, "logs/unpack-vendor_boot.stdout.txt", header)
        info["kind"] = "regular"
        receipt = {"schema_version": 1, "parent_package_sha256": "2" * 64, "artifacts": [info]}
        raw = json.dumps(receipt).encode()
        (evidence / "final-receipt.json").write_bytes(raw)
        boot["evidence"] = {"private_directory": "artifacts/boot-evidence",
                            "final_receipt_sha256": hashlib.sha256(raw).hexdigest()}

        record_paths = {}
        for name, record in self.records.items():
            path = self.root / "research" / (name + ".json")
            write(self.root, str(path.relative_to(self.root)), json.dumps(record).encode())
            record_paths[name] = path
        vendor = {
            "schema_version": 1, "device": "nezha", "images": images,
            "extras": [], "generated_files": generated,
            "source": {"package_sha256": "3" * 64, "input_avb_status": "failed",
                       "source_record_sha256": hashlib.sha256(record_paths["firmware-layout"].read_bytes()).hexdigest()},
        }
        vendor_path = vendor_root / "vendor-inputs.json"
        vendor_path.write_text(json.dumps(vendor))
        return {"record_paths": record_paths, "kernel_receipt": kernel_path,
                "vendor_receipt": vendor_path, "workspace_root": self.root}

    def recovery_template_inputs(self):
        inputs = self.generation_inputs()
        templates = self.root / "recovery-templates"
        for name in generator.TEMPLATE_FILES:
            path = templates / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = f"# Synthetic public template: {name}\n"
            if name == "BoardConfig.mk":
                data += "include $(NEZHA_DEVICE_PATH)/recovery-prebuilt.mk\n"
            path.write_text(data)
        return {**inputs, "template_root": templates}

    def test_recovery_template_is_copied_and_hashed_without_promoting_admission(self):
        inputs = self.recovery_template_inputs()
        relative = (generator.DEVICE_PATH / "recovery-prebuilt.mk").as_posix()
        expected = (inputs["template_root"] / "recovery-prebuilt.mk").read_bytes()
        self.assertEqual(generator.TEMPLATE_FILES.count("recovery-prebuilt.mk"), 1)
        for variant in generator.BUILD_VARIANTS:
            with self.subTest(variant=variant):
                output = self.root / "artifacts" / variant
                plan = generator.generate(output, variant=variant, **inputs)
                self.assertEqual((output / relative).read_bytes(), expected)
                entry = next(row for row in plan["files"] if row["path"] == relative)
                self.assertEqual(entry, {"path": relative, "size_bytes": len(expected),
                                         "sha256": hashlib.sha256(expected).hexdigest()})
                self.assertEqual(plan["admission"], self.plan(variant=variant)["admission"])
                self.assertEqual(plan["profile"], "framework-checks")
                self.assertEqual(generator.validate(output), plan)
                for purpose in ("target-files", "flash"):
                    with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                        generator.validate(output, purpose=purpose)

    def test_generation_requires_the_public_recovery_template(self):
        inputs = self.recovery_template_inputs()
        (inputs["template_root"] / "recovery-prebuilt.mk").unlink()
        output = self.root / "artifacts/missing-recovery-template"
        with self.assertRaisesRegex(generator.CandidateError, "input does not exist"):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())

    def test_validation_rejects_missing_or_changed_recovery_template(self):
        self.candidate()
        template = self.root / generator.DEVICE_PATH / "recovery-prebuilt.mk"
        original = template.read_bytes()
        for mutation in ("changed", "missing"):
            with self.subTest(mutation=mutation):
                if mutation == "changed":
                    template.write_bytes(original + b"# unexpected change\n")
                else:
                    template.unlink()
                with self.assertRaises(generator.CandidateError):
                    generator.validate(self.root)
                template.write_bytes(original)

    def test_generation_never_reads_or_copies_private_recovery_stage_files(self):
        inputs = self.recovery_template_inputs()
        stage = self.root / "vendor/xiaomi/nezha-recovery"
        stage.mkdir(parents=True)
        private_files = []
        for directory in (stage, inputs["template_root"]):
            for name in ("recovery.img", "receipt.json", "recovery-inputs.mk"):
                path = directory / name
                path.write_bytes(b"synthetic private recovery input\n")
                private_files.append(path)
        read_file = generator._read_file

        def public_or_existing_bundle_read(path, **options):
            self.assertNotIn(Path(path), private_files)
            return read_file(path, **options)

        output = self.root / "artifacts/public-recovery-template"
        with mock.patch.object(generator, "_read_file", side_effect=public_or_existing_bundle_read):
            plan = generator.generate(output, **inputs)
            self.assertEqual(generator.validate(output), plan)
        names = {row["path"] for row in plan["files"]}
        self.assertFalse(any(name.startswith("vendor/") for name in names))
        self.assertFalse(any(Path(name).name in {"recovery.img", "receipt.json", "recovery-inputs.mk"}
                             for name in names))
        self.assertFalse((output / "vendor").exists())

    def test_validation_refuses_private_recovery_files_even_when_listed(self):
        plan = self.candidate()
        for name in ("recovery.img", "receipt.json", "recovery-inputs.mk"):
            with self.subTest(name=name):
                relative = "vendor/xiaomi/nezha-recovery/" + name
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                data = b"synthetic private recovery input\n"
                path.write_bytes(data)
                plan["files"].append({"path": relative, "size_bytes": len(data),
                                      "sha256": hashlib.sha256(data).hexdigest()})
                self.save_admission(plan)
                with self.assertRaisesRegex(generator.CandidateError, "generated file set"):
                    generator.validate(self.root)
                plan["files"].pop()
                path.unlink()
        self.save_admission(plan)
        self.assertEqual(generator.validate(self.root), plan)

    def test_generation_is_deterministic_with_synthetic_bundles(self):
        inputs = self.generation_inputs()
        first, second = self.root / "artifacts/first", self.root / "artifacts/second"
        plan = generator.generate(first, **inputs)
        other = generator.generate(second, **inputs)
        self.assertEqual(plan, other)
        for path in ["admission.json", *(entry["path"] for entry in plan["files"])]:
            self.assertEqual((first / path).read_bytes(), (second / path).read_bytes(), path)
        self.assertTrue(plan["mixed_package_sources"])
        self.assertEqual(plan["source_packages"], {"kernel": "2" * 64, "vendor": "3" * 64})
        self.assertIs(plan["admission"]["flash_allowed"], False)
        board = (first / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        self.assertIn("BOARD_KERNEL_BASE := 0x00000000", board)
        self.assertIn("--dtb_offset 0x1f00000", board)
        self.assertIn("--ramdisk_offset 0x1000000", board)
        self.assertIn("NEZHA_EXPECTED_KERNEL_PACKAGE_SHA256 := " + "2" * 64, board)
        self.assertNotIn("swinfo.fingerprint", board)
        self.assertIn("BOOT_SECURITY_PATCH := 2026-02-01", board)
        self.assertIn("BOARD_AVB_ROLLBACK_INDEX := " + str(plan["avb_root_rollback_index"]), board)
        self.assertEqual((first / generator.SECURITY_PATCH).read_bytes(),
                         (ROOT / generator.SECURITY_PATCH).read_bytes())
        self.assertFalse(plan["required_source_adjustments"][0]["applied_by_generator"])
        self.assertEqual(generator.validate(first), plan)

    def factory_inputs(self):
        """Tiny invented payloads with complete receipt links, never private firmware."""
        inputs = self.generation_inputs()
        kernel = json.loads(inputs["kernel_receipt"].read_text())
        kernel["roles"].update(kernel="kernel/Image", dtb="dtb/vendor.dtb",
                               dtbo="dtbo/dtbo.img", bootconfig="reference/vendor.bootconfig")
        for role in ("dtb", "dtbo", "bootconfig"):
            data = ("synthetic " + role).encode()
            path = inputs["kernel_receipt"].parent / kernel["roles"][role]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            kernel["files"].append({"path": kernel["roles"][role], "size_bytes": len(data),
                                    "sha256": hashlib.sha256(data).hexdigest(), "readback_verified": True})
        inputs["kernel_receipt"].write_text(json.dumps(kernel))
        plan = self.plan()
        rows = []
        for name, filesystem in plan["logical_filesystems"].items():
            mount = "/mnt/vendor/mi_ext" if name == "mi_ext" else "/" + name
            flags = "wait,slotselect,avb=" + plan["avb_descriptor_owners"][name] + ",logical,first_stage_mount"
            if name == "mi_ext":
                flags += ",nofail"
            if name == "system":
                flags += ",avb_keys=/avb/test-only-fixture.avbpubkey"
            rows.append(f"{name} {mount} {filesystem} ro {flags}")
        rows += [f"/dev/block/by-name/{name} /{name} emmc defaults slotselect,avb=vbmeta,first_stage_mount"
                 for name in plan["image_budgets"]]
        rows += [METADATA_ROW, DATA_ROW, "overlay /system/framework overlay ro,lowerdir=/fixture check,nofail",
                 "/devices/platform/test-usb/*.controller /storage/test vfat nosuid,nodev wait,voldmanaged=fixture:auto"]
        raw = ("# Synthetic license notice retained\n" + "\n".join(rows) + "\n").encode()
        fstab = self.root / "factory.fstab"
        fstab.write_bytes(raw)
        data_rows = []
        for row in (METADATA_ROW, DATA_ROW):
            source, mount, filesystem, options, flags = row.split()
            data_rows.append({"source": source, "mount_point": mount, "filesystem": filesystem,
                              "mount_options": options.split(","), "fs_mgr_flags": flags.split(",")})
        contract = {"factory_sha256": hashlib.sha256(raw).hexdigest(), "factory_size_bytes": len(raw),
                    "rows_in_each": len(rows), "normal_data_rows": data_rows}
        package = {"sha256": "3" * 64, "source_kind": "user-provided", "source_url": None,
                   "origin_verified": False}
        files = {item["path"]: item for item in kernel["files"]}
        components = []
        for role, path in (("kernel", "unpacked/boot/kernel"), ("dtb", "unpacked/vendor_boot/dtb"),
                           ("bootconfig", "unpacked/vendor_boot/bootconfig")):
            item = files[kernel["roles"][role]]
            components.append({"path": path, "size_bytes": item["size_bytes"],
                               "factory_sha256": item["sha256"], "xiaomi_eu_sha256": item["sha256"],
                               "bytes_match_eu": True})

        def reference(name, record):
            path = self.root / "artifacts/factory-reference" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (json.dumps(dict(schema_version=1, **record)) + "\n").encode()
            path.write_bytes(raw)
            return {"path": path.relative_to(self.root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
                    "size_bytes": len(raw)}

        header = reference("headers.json", {"factory_package_sha256": "3" * 64,
                           "xiaomi_eu_package_sha256": "2" * 64, "components": components})
        ramdisk = reference("ramdisk.json", {"factory_package_sha256": "3" * 64,
                            "inputs_identity_and_hash_rechecked": True,
                            "artifacts": [{"path": "text-members/vendor_boot-0001.txt",
                                           "sha256": contract["factory_sha256"], "size_bytes": len(raw)}]})
        sizes, luns = [], []
        for name in (*plan["image_budgets"], "super"):
            extent = plan["super"]["bytes"] if name == "super" else plan["image_budgets"][name]["bytes"]
            if name == "dtbo":
                extent = 32 * 1024 ** 2
            labels = ["super"] if name == "super" else [name + "_a", name + "_b"]
            entries = [{"label": label, "type_guid_zero": False, "first_lba": 16 + i * extent // 4096,
                        "last_lba": 15 + (i + 1) * extent // 4096, "size_bytes": extent}
                       for i, label in enumerate(labels)]
            gpt = {"header_crc32_verified": True, "entry_array_crc32_verified": True, "entries": entries}
            lun = len(luns)
            luns.append({"lun": lun, "primary_backup_entry_arrays_identical": True, "sector_size_bytes": 4096,
                         "gpt": {"main": {"headers": [gpt]}, "backup": {"headers": [copy.deepcopy(gpt)]}}})
            item = {"name": name, "labels": labels, "lun": lun, "package_extent_bytes": extent,
                    "stored_image_bytes": extent, "stored_image_sha256": "a" * 64}
            if name == "dtbo":
                item.update(stored_image_bytes=files[kernel["roles"]["dtbo"]]["size_bytes"],
                            stored_image_sha256=files[kernel["roles"]["dtbo"]]["sha256"])
            sizes.append(item)
        image_rows = []
        for item in sizes:
            copy_record = {"size_bytes": item["stored_image_bytes"], "sha256": item["stored_image_sha256"],
                           "regular_nonsymlink": True, "identity_stable": True, "matches_expected_sha256": True}
            image_rows.append({"path": item["name"] + ".img", "expected_size_bytes": item["stored_image_bytes"],
                               "expected_sha256": item["stored_image_sha256"], "both_match_verified_archive": True,
                               "archive_image": copy_record, "user_extracted_image": copy.deepcopy(copy_record)})
        image_receipt = reference("images.json", {"package_sha256": "3" * 64, "source_kind": "user-provided",
                                  "source_url": None, "origin_verified": False, "images": image_rows,
                                  "image_count": len(image_rows), "all_images_match": True})
        analysis = reference("gpt-analysis.json", {"sector_size_bytes": 4096, "luns": luns,
                             "physical_phone_geometry_verified": False, "flashable_gpt_admitted": False})
        receipt = reference("gpt-receipt.json", {"parent_package_sha256": "3" * 64,
                            "input_hashes_and_identity_rechecked": True,
                            "output": {**analysis, "readback_verified": True}})
        factory = {"schema_version": 1, "device": {"codename": "nezha", "hardware_region": "CN"},
                   "packages": {"factory": package, "xiaomi_eu": {"sha256": "2" * 64}},
                   "image_readback": {"receipt": image_receipt},
                   "header_component_readback": {"receipt": header, "components": components},
                   "ramdisk_comparison": {"receipt": ramdisk}, "normal_vendor_fstab": contract,
                   "vendor_bootconfig": {"declarations": plan["bootconfig"]}}
        partitions = {"schema_version": 1, "device": factory["device"], "package": package,
                      "inspection": {"receipt": receipt, "analysis": analysis}, "build_relevant_sizes": sizes}
        factory_path, partition_path = self.root / "factory.json", self.root / "partitions.json"
        factory_path.write_text(json.dumps(factory))
        partition_path.write_text(json.dumps(partitions))
        return dict(inputs, factory_boot_contract=factory_path, partition_metadata=partition_path, fstab_source=fstab)

    def mi_ext_inputs(self, inputs=None):
        """Mock private-bundle verification; retain the real native Make renderer."""
        from scripts import mi_ext_inputs as mi
        inputs = inputs or self.factory_inputs()
        config = json.loads((ROOT / mi.CONTRACT_PATH).read_bytes())
        source = json.loads((ROOT / mi.SOURCE_CONTRACT_PATH).read_bytes())
        self.enterContext(mock.patch.object(mi, "EXPECTED_PACKAGE", "3" * 64))
        self.enterContext(mock.patch.object(mi, "_controls", return_value=(config, source, {})))
        path = inputs["record_paths"]["firmware-layout"]
        layout = json.loads(path.read_text())
        row = next(row for row in layout["partitions"] if row["name"] == "mi_ext_a")
        row["size_bytes"] = mi.EXPECTED_IMAGE["size_bytes"]
        row["extraction"]["sha256"] = mi.EXPECTED_IMAGE["sha256"]
        self.save_mi_ext_layout(inputs, layout)
        receipt = self.root / "mi-ext-bundle" / mi.RECEIPT_NAME
        receipt.parent.mkdir()
        raw = b'{"schema_version":1,"synthetic_private_receipt":true}\n'
        receipt.write_bytes(raw)
        inputs["mi_ext_inputs_receipt"] = receipt
        binding = {
            "bundle": mi.BUNDLE_PATH, "factory_package_sha256": "3" * 64,
            "image": copy.deepcopy(mi.EXPECTED_IMAGE),
            "receipt": {"path": receipt.name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "native_source": {"project_commit": mi.BUILD_COMMIT, "files": mi._source_files(source)},
            "dynamic_layout": copy.deepcopy(config["dynamic_layout"]), "scope": copy.deepcopy(mi.SCOPE),
        }
        return inputs, binding

    def save_mi_ext_layout(self, inputs, layout):
        path = inputs["record_paths"]["firmware-layout"]
        path.write_text(json.dumps(layout))
        vendor = json.loads(inputs["vendor_receipt"].read_text())
        vendor["source"]["source_record_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        inputs["vendor_receipt"].write_text(json.dumps(vendor))

    def test_mi_ext_requires_explicit_factory_profile_before_reading_inputs(self):
        with mock.patch.object(generator, "_load_records") as load, \
                self.assertRaisesRegex(generator.CandidateError, "mi_ext inputs require the explicit factory"):
            generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none",
                               vendor_receipt="none", mi_ext_inputs_receipt="none")
        load.assert_not_called()

    def test_mi_ext_is_not_enabled_or_inspected_by_default(self):
        inputs = self.factory_inputs()
        with mock.patch.object(generator, "_verify_mi_ext_inputs", side_effect=AssertionError("implicit bundle read")), \
                mock.patch.object(generator, "_render_mi_ext_include", side_effect=AssertionError("implicit native binding")):
            first = generator.generate(self.root / "artifacts/default-mi-ext", **inputs)
            second = generator.generate(self.root / "artifacts/explicit-none-mi-ext", mi_ext_inputs_receipt=None, **inputs)
        self.assertEqual(first, second)
        self.assertNotIn("mi_ext_inputs", first)
        self.assertEqual(first["required_unpacked_partitions"], ["mi_ext"])
        self.assertNotIn(generator.MI_EXT_BOARD_INCLUDE.as_posix(), {row["path"] for row in first["files"]})

    def test_mi_ext_generation_is_deterministic_preserves_root_avb_and_refuses_packaging(self):
        inputs, binding = self.mi_ext_inputs()
        first = self.root / "artifacts/mi-ext-first"
        second = self.root / "artifacts/mi-ext-second"
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding) as verify:
            plan = generator.generate(first, variant="user", **inputs)
            self.assertEqual(generator.generate(second, variant="user", **inputs), plan)
        self.assertEqual(verify.call_args_list, [mock.call(inputs["mi_ext_inputs_receipt"], expected_package_sha256="3" * 64)] * 2)
        self.assertEqual(generator.validate(first), plan)
        self.assertEqual(plan["mi_ext_inputs"], binding)
        self.assertEqual(plan["packaged_logical_partitions"], [*generator.FRAMEWORK_PARTITIONS, "mi_ext"])
        self.assertEqual(plan["required_unpacked_partitions"], [])
        self.assertTrue(any(note.startswith("The factory mi_ext input is selected;") for note in plan["limitations"]))
        self.assertEqual(plan["avb_descriptor_owners"]["mi_ext"], "vbmeta")
        self.assertEqual(set(plan["avb_chains"]), {"boot", "recovery", "vbmeta_system"})
        board = (first / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        product = (first / generator.DEVICE_PATH / "generated/device-candidate.mk").read_text()
        include = (first / generator.MI_EXT_BOARD_INCLUDE).read_text()
        group_line = next(line for line in board.splitlines() if line.startswith("BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST :="))
        ab_line = next(line for line in product.splitlines() if line.startswith("AB_OTA_PARTITIONS +="))
        self.assertEqual(group_line.split()[2:], [*generator.FRAMEWORK_PARTITIONS, "mi_ext"])
        self.assertEqual(ab_line.split().count("mi_ext"), 1)
        self.assertIn("BOARD_AVB_VBMETA_SYSTEM := system system_ext product\n", board)
        self.assertEqual(board.count("include $(NEZHA_DEVICE_PATH)/generated/mi-ext-prebuilt.mk\n"), 1)
        self.assertIn("BOARD_AVB_CUSTOMIMAGES_DIRECT_PARTITION_LIST := mi_ext\n", include)
        self.assertIn("BOARD_MI_EXT_IMAGE_LIST := vendor/xiaomi/nezha-mi-ext/mi_ext.img\n", include)
        self.assertIn(binding["image"]["sha256"], include)
        self.assertIn(binding["receipt"]["sha256"], include)
        for row in binding["native_source"]["files"]:
            self.assertIn(row["sha256"], include)
        self.assertFalse(plan["fstab"]["stock_overlay_mounts_adopted"])
        self.assertFalse(any(row["path"].startswith("vendor/") or row["path"].endswith(".img") for row in plan["files"]))
        for key, value in plan["admission"].items():
            self.assertIs(value, key == "configuration_allowed", key)
        for purpose in ("target-files", "flash"):
            with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(first, purpose=purpose)

    def test_mi_ext_coexists_with_oem_helper_and_dsp_without_changing_their_admissions(self):
        inputs, policy = self.oem_inputs()
        inputs, binding = self.mi_ext_inputs(inputs)
        base_inputs = {key: value for key, value in inputs.items() if key != "mi_ext_inputs_receipt"}
        before, after = self.root / "artifacts/oem-before-mi-ext", self.root / "artifacts/oem-with-mi-ext"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy), \
                mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding):
            baseline = generator.generate(before, **base_inputs)
            plan = generator.generate(after, **inputs)
        for key in ("init_helper_capability", "dsp_policy", "oem_policy", "policy_inputs", "admission", "avb_policy", "avb_chains"):
            self.assertEqual(plan[key], baseline[key], key)
        board = (after / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        self.assertTrue(board.endswith("\n" + "\n".join(generator._dsp_wiring_lines()) + "\n"))
        self.assertIn("\n" + "\n".join(generator._init_helper_wiring_lines()) + "\n", board)
        for name in ("BoardConfig.mk", "init-helper-capability.mk", *generator.DSP_POLICY_FILES, *generator.OEM_POLICY_FILES):
            self.assertEqual((before / generator.DEVICE_PATH / name).read_bytes(),
                             (after / generator.DEVICE_PATH / name).read_bytes(), name)
        self.assertEqual(generator.validate(after), plan)

    def test_mi_ext_selected_image_hash_length_and_b_slot_must_match_the_bundle(self):
        inputs, binding = self.mi_ext_inputs()
        baseline = json.loads(inputs["record_paths"]["firmware-layout"].read_text())
        mutations = [lambda a, b: a["extraction"].update(sha256="0" * 64),
                     lambda a, b: a.update(size_bytes=a["size_bytes"] - 4096),
                     lambda a, b: a["extraction"].update(readback_verified=False),
                     lambda a, b: b.update(size_bytes=False),
                     lambda a, b: b.update(extents=False),
                     lambda a, b: b.update(extents=[{"unreviewed": True}])]
        for mutate in mutations:
            changed = copy.deepcopy(baseline)
            a = next(row for row in changed["partitions"] if row["name"] == "mi_ext_a")
            b = next(row for row in changed["partitions"] if row["name"] == "mi_ext_b")
            mutate(a, b)
            self.save_mi_ext_layout(inputs, changed)
            with self.subTest(mutate=mutate), mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding), \
                    self.assertRaisesRegex(generator.CandidateError, "selected factory logical image"):
                generator.generate(self.root / "artifacts/refused", **inputs)
            self.assertFalse((self.root / "artifacts/refused").exists())

    def test_mi_ext_receipt_replacement_noncanonical_name_and_symlink_are_refused(self):
        inputs, binding = self.mi_ext_inputs()
        path = inputs["mi_ext_inputs_receipt"]
        wrong = path.parent / "other.json"
        wrong.write_bytes(path.read_bytes())
        link = path.parent / "linked.json"
        link.symlink_to(path.name)
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding) as verify:
            for candidate in (wrong, link):
                with self.subTest(candidate=candidate), self.assertRaises(generator.CandidateError):
                    generator.generate(self.root / "artifacts/refused", **dict(inputs, mi_ext_inputs_receipt=candidate))
            verify.assert_not_called()
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(generator.CandidateError, "receipt changed"):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_mi_ext_bundle_failure_does_not_publish_or_fall_back(self):
        inputs = self.factory_inputs()
        path = self.root / generator.MI_EXT_INPUTS_RECEIPT
        path.write_text("{}")
        from scripts import mi_ext_inputs as mi
        with mock.patch.object(mi, "validate_admission", side_effect=mi.MiExtInputsError("changed private image")), \
                self.assertRaisesRegex(generator.CandidateError, "changed private image"):
            generator.generate(self.root / "artifacts/refused", mi_ext_inputs_receipt=path, **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_mi_ext_validation_rejects_layout_source_and_scope_promotion(self):
        inputs, binding = self.mi_ext_inputs()
        output = self.root / "artifacts/mi-ext-binding"
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding):
            original = generator.generate(output, **inputs)
        changes = [lambda p: p["mi_ext_inputs"].update(factory_package_sha256="0" * 64),
                   lambda p: p["mi_ext_inputs"]["native_source"].update(project_commit="0" * 40),
                   lambda p: p["mi_ext_inputs"]["native_source"]["files"][0].update(sha256="0" * 64),
                   lambda p: p["mi_ext_inputs"]["scope"].update(complete_rom_admitted=True),
                   lambda p: p["mi_ext_inputs"]["scope"].update(factory_overlays_activated=True),
                   lambda p: p["mi_ext_inputs"]["scope"].update(hardware_tested=True),
                   lambda p: p["mi_ext_inputs"]["dynamic_layout"].update(group_name="other"),
                   lambda p: p["super"].update(group_bytes=p["super"]["group_bytes"] - 4096),
                   lambda p: p["logical_filesystems"].update(mi_ext="ext4"),
                   lambda p: p["avb_descriptor_owners"].update(mi_ext="vbmeta_system"),
                   lambda p: p["avb_chains"].update(mi_ext={"location": 7, "rollback_index": 1}),
                   lambda p: p["required_unpacked_partitions"].append("mi_ext"),
                   lambda p: p["packaged_logical_partitions"].append("mi_ext"),
                   lambda p: p["admission"].update(physical_partition_fit_verified=True)]
        for change in changes:
            plan = copy.deepcopy(original)
            change(plan)
            (output / "admission.json").write_text(json.dumps(plan))
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_mi_ext_validation_rejects_resealed_board_product_guard_and_fstab_changes(self):
        inputs, binding = self.mi_ext_inputs()
        output = self.root / "artifacts/mi-ext-wiring"
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding):
            plan = generator.generate(output, **inputs)
        mutations = {
            "generated/BoardConfigCandidate.mk": lambda raw: raw.replace(b" system_dlkm mi_ext\n", b" system_dlkm\n"),
            "generated/device-candidate.mk": lambda raw: raw.replace(b" system_dlkm mi_ext\n", b" system_dlkm\n"),
            "generated/mi-ext-prebuilt.mk": lambda raw: raw.replace(b"BOARD_MI_EXT_IMAGE_LIST :=", b"BOARD_MI_EXT_IMAGE_LIST ?="),
            "generated/fstab.qcom": lambda raw: raw.replace(b"mi_ext /mnt/vendor/mi_ext erofs ro wait,slotselect,avb=vbmeta,",
                                                              b"mi_ext /mi_ext erofs ro wait,slotselect,avb=vbmeta_system,"),
        }
        for relative, mutate in mutations.items():
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            raw = mutate(original)
            self.assertNotEqual(raw, original, name)
            self.reseal_candidate_file(output, plan, name, raw)
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)
        self.assertEqual(generator.validate(output), plan)

    def test_mi_ext_validation_refuses_other_makefile_assignment_even_after_inventory_reseal(self):
        inputs, binding = self.mi_ext_inputs()
        output = self.root / "artifacts/mi-ext-extra-wiring"
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding):
            plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "device.mk").as_posix()
        raw = (output / name).read_bytes() + b"\nBOARD_AVB_MI_EXT_KEY_PATH := unreviewed.pem\n"
        self.reseal_candidate_file(output, plan, name, raw)
        with self.assertRaisesRegex(generator.CandidateError, "may only use the reviewed generated include"):
            generator.validate(output)

    def test_mi_ext_validation_preserves_exact_factory_mount_flags_and_rejects_alternate_sources(self):
        inputs, binding = self.mi_ext_inputs()
        output = self.root / "artifacts/mi-ext-fstab"
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding):
            plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "generated/fstab.qcom").as_posix()
        original = (output / name).read_bytes()
        row = b"mi_ext /mnt/vendor/mi_ext erofs ro wait,slotselect,avb=vbmeta,logical,first_stage_mount,nofail"
        changes = [original + row.replace(b"mi_ext /", b"other /") + b"\n",
                   original.replace(row, row.replace(b"mi_ext /", b"other /")),
                   original.replace(row, row.replace(b",nofail", b"")),
                   original.replace(row, row + b",avb_keys=/unreviewed.avbpubkey"),
                   original.replace(row, row + b",formattable"),
                   original.replace(row, row + b",logical"),
                   original + b"overlay /system/framework overlay ro,lowerdir=/mi_ext/framework:/system/framework check,nofail\n"]
        for raw in changes:
            self.assertNotEqual(raw, original)
            self.reseal_candidate_file(output, plan, name, raw)
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaises(generator.CandidateError):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, name, original)
        self.assertEqual(generator.validate(output), plan)

    def test_mi_ext_partition_selection_cannot_move_to_other_makefiles_without_capability(self):
        inputs = self.factory_inputs()
        output = self.root / "artifacts/mi-ext-alternate-lists"
        plan = generator.generate(output, **inputs)
        for relative, assignment in (("device.mk", b"AB_OTA_PARTITIONS += mi_ext\n"),
                                     ("BoardConfig.mk", b"AB_OTA_PARTITIONS += mi_ext\n"),
                                     ("device.mk", b"BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST += mi_ext\n"),
                                     ("BoardConfig.mk", b"BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST += mi_ext\n"),
                                     ("generated/device-candidate.mk", b"BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST += mi_ext\n")):
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, original + assignment)
            with self.subTest(relative=relative, assignment=assignment), self.assertRaisesRegex(generator.CandidateError, "selection may only use|explicit verified bundle"):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)

    def test_mi_ext_validation_cannot_add_partition_or_wiring_without_capability(self):
        inputs = self.factory_inputs()
        output = self.root / "artifacts/no-mi-ext"
        plan = generator.generate(output, **inputs)
        for relative, content in (("generated/BoardConfigCandidate.mk", b"include $(NEZHA_DEVICE_PATH)/generated/mi-ext-prebuilt.mk\n"),
                                  ("generated/device-candidate.mk", b"AB_OTA_PARTITIONS += mi_ext\n")):
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, original + content)
            with self.subTest(relative=relative), self.assertRaisesRegex(generator.CandidateError, "explicit verified bundle"):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)
        forged = copy.deepcopy(plan)
        forged["packaged_logical_partitions"].append("mi_ext")
        forged["required_unpacked_partitions"] = []
        (output / "admission.json").write_text(json.dumps(forged))
        with self.assertRaisesRegex(generator.CandidateError, "matching explicit input capability"):
            generator.validate(output)

    def test_mi_ext_validation_never_reopens_private_bundle_or_guest_source(self):
        inputs, binding = self.mi_ext_inputs()
        output = self.root / "artifacts/mi-ext-offline"
        with mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding):
            plan = generator.generate(output, **inputs)
        inputs["mi_ext_inputs_receipt"].unlink()
        with mock.patch.object(generator, "_verify_mi_ext_inputs", side_effect=AssertionError("private bundle read")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("native process started")):
            self.assertEqual(generator.validate(output), plan)
        self.assertFalse(plan["mi_ext_inputs"]["scope"]["complete_avb_chain_verified"])

    def test_cli_passes_optional_mi_ext_receipt_without_enabling_it_by_default(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--mi-ext-inputs-receipt", "mi-ext-inputs.json"], Path("mi-ext-inputs.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["mi_ext_inputs_receipt"], expected)

    def metadata_inputs(self, *, source_contract=None, inputs=None):
        """Tiny private metadata fixture; use real public controls and Make renderers."""
        from scripts import mi_ext_inputs as mi
        metadata = generator._metadata_module(source_contract=source_contract)
        inputs, mi_binding = self.mi_ext_inputs(inputs)
        legacy_public = generator._metadata_public_binding()
        public = legacy_public if source_contract is None else generator._metadata_public_binding(source_contract=source_contract)
        vendor = json.loads(inputs["vendor_receipt"].read_bytes())
        for record in (legacy_public, public):
            record["factory_package_sha256"] = "3" * 64
            record["images"] = {name: {key: row[key] for key in ("sha256", "size_bytes")}
                                for name, row in vendor["images"].items()}
        config, legacy, controls = mi._controls.return_value
        composed = copy.deepcopy(legacy)
        composed.update(composition=public["native_source"], composition_identity=public["composition_identity"])
        old_metadata = copy.deepcopy(legacy)
        old_metadata.update(composition=legacy_public["native_source"], composition_identity=legacy_public["composition_identity"])
        def mi_controls(reader, composed_source_contract=None):
            source = legacy if composed_source_contract is None else composed
            if source_contract is not None and composed_source_contract == ROOT / generator.TARGET_FILES_METADATA_CONTRACT:
                source = old_metadata
            return config, source, controls
        mi._controls.side_effect = mi_controls
        mi_binding["native_source"] = mi._native_source(composed)
        self.enterContext(mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=mi_binding))
        def public_binding(**options):
            if options:
                self.assertEqual(set(options), {"source_contract"})
                self.assertIsNotNone(options["source_contract"])
                return copy.deepcopy(public)
            return copy.deepcopy(legacy_public)
        self.enterContext(mock.patch.object(generator, "_metadata_public_binding", side_effect=public_binding))
        rows = [{"target_path": f"VENDOR/etc/vintf/fixture-{index}.xml"}
                for index in range(public["metadata_file_count"])]
        receipt = {"schema_version": 1, "profile": public["profile"], "images": public["images"],
                   "source_composition": public["native_source"], "scope": public["scope"],
                   "files": rows, "bundle_files": copy.deepcopy(public["control_files"])}
        path = self.root / "artifacts/metadata-inputs" / generator.TARGET_FILES_METADATA_RECEIPT
        path.parent.mkdir(parents=True)
        runtime = {"tools/target_files_metadata.py": (ROOT / "scripts/target_files_metadata.py").read_bytes()}
        if source_contract is not None:
            _, _, selected_controls = metadata._controls(ROOT, metadata.Reader(), source_contract=source_contract)
            runtime = metadata.runtime_tool_payloads(selected_controls)
        for row in receipt["bundle_files"]:
            relative = row["path"]
            target = path.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative.removeprefix("controls/")).read_bytes()
                               if relative.startswith("controls/") else runtime[relative])
        path.write_bytes(metadata.encoded(receipt))
        inputs.update(target_files_metadata_receipt=path,
                      target_files_metadata_receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        if source_contract is not None:
            inputs["target_files_source_contract"] = source_contract
            mi_receipt = inputs["mi_ext_inputs_receipt"]
            mi_receipt.parent.chmod(0o700)
            mi_receipt.chmod(0o600)
            for member in (mi.IMAGE_MEMBER, mi.LOGICAL_RECEIPT_MEMBER):
                target = mi_receipt.parent / member
                target.write_bytes(b"synthetic mi_ext input")
                target.chmod(0o600)
        files = {row["target_path"]: (row, b"synthetic content") for row in rows}
        verifier = self.enterContext(mock.patch.object(metadata, "verify_bundle", return_value=(receipt, files, mock.Mock())))
        return inputs, public, receipt, verifier

    def test_metadata_is_not_selected_or_inspected_by_default(self):
        inputs = self.generation_inputs()
        with mock.patch.object(generator, "_metadata_public_binding", side_effect=AssertionError("implicit controls")), \
                mock.patch.object(generator, "_verify_target_files_metadata", side_effect=AssertionError("implicit bundle")):
            first = generator.generate(self.root / "artifacts/default-metadata", **inputs)
            second = generator.generate(self.root / "artifacts/explicit-none-metadata",
                                        target_files_metadata_receipt=None,
                                        target_files_metadata_receipt_sha256=None, **inputs)
        self.assertEqual(first, second)
        self.assertNotIn("target_files_metadata", first)
        self.assertFalse(any(row["path"] == generator.TARGET_FILES_METADATA_INCLUDE.as_posix() for row in first["files"]))

    def test_metadata_requires_paired_external_digest_factory_and_mi_ext_before_reads(self):
        base = {"record_paths": {}, "kernel_receipt": "none", "vendor_receipt": "none"}
        mutations = [
            {"target_files_metadata_receipt": "none"},
            {"target_files_metadata_receipt_sha256": "1" * 64},
            {"target_files_metadata_receipt": "none", "target_files_metadata_receipt_sha256": "1" * 64},
            {"target_files_metadata_receipt": "none", "target_files_metadata_receipt_sha256": "1" * 64,
             "factory_boot_contract": "none", "partition_metadata": "none", "fstab_source": "none"},
        ]
        for options in mutations:
            with self.subTest(options=options), mock.patch.object(generator, "_load_records") as load, \
                    self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused-metadata", **base, **options)
            load.assert_not_called()
        for digest in ("", "x" * 64, "1" * 63, "1" * 65, "$(shell false)", True, 1):
            with self.subTest(digest=digest), mock.patch.object(generator, "_load_records") as load, \
                    self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused-metadata", **base,
                                   target_files_metadata_receipt="none", target_files_metadata_receipt_sha256=digest)
            load.assert_not_called()

    def test_metadata_generation_binds_current_sources_without_promoting_packaging(self):
        inputs, public, receipt, verifier = self.metadata_inputs()
        first = self.root / "artifacts/metadata-first"
        second = self.root / "artifacts/metadata-second"
        original_recovery = (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        plan = generator.generate(first, **inputs)
        self.assertEqual(generator.generate(second, **inputs), plan)
        self.assertEqual(verifier.call_count, 4)
        for call in verifier.call_args_list:
            self.assertEqual(call, mock.call(inputs["target_files_metadata_receipt"].parent,
                                            expected_receipt=inputs["target_files_metadata_receipt_sha256"]))
        for call in generator._verify_mi_ext_inputs.call_args_list:
            self.assertEqual(call.kwargs["composed_source_contract"], ROOT / generator.TARGET_FILES_METADATA_CONTRACT)
        capability = plan["target_files_metadata"]
        self.assertEqual(capability["metadata_file_count"], 205)
        self.assertEqual(capability["native_source"], public["native_source"])
        self.assertFalse(capability["native_source"]["patches_applied_by_this_tool"])
        self.assertFalse(capability["native_source"]["whole_source_tree_verified"])
        self.assertEqual(capability["images"], public["images"])
        self.assertEqual(capability["scope"], receipt["scope"])
        include = (first / generator.TARGET_FILES_METADATA_INCLUDE).read_text()
        self.assertEqual(include.count(" := "), 3)
        self.assertNotIn(".KATI_READONLY", include)
        self.assertIn("BOARD_NEZHA_PREBUILT_METADATA_RECEIPT_SHA256 := " + inputs["target_files_metadata_receipt_sha256"], include)
        self.assertIn("BOARD_NEZHA_PREBUILT_METADATA_TOOL_SHA256 := " +
                      next(row["sha256"] for row in public["control_files"] if row["path"] == "tools/target_files_metadata.py"), include)
        recovery = (first / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        self.assertNotEqual(recovery, original_recovery)
        self.assertEqual(recovery, generator._metadata_recovery_include(original_recovery))
        self.assertEqual((ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes(), original_recovery)
        for row in public["native_source"]["final_source_files"]:
            self.assertIn(row["sha256"].encode(), recovery)
        self.assertFalse(any(row["path"].startswith("vendor/") for row in plan["files"]))
        self.assertTrue(plan["admission"]["configuration_allowed"])
        self.assertTrue(all(value is False for key, value in plan["admission"].items() if key != "configuration_allowed"))
        self.assertEqual(generator.validate(first), plan)
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(first, purpose=purpose)

    def test_metadata_receipt_identity_and_filename_are_checked_before_bundle_verification(self):
        inputs, _, _, verifier = self.metadata_inputs()
        path = inputs["target_files_metadata_receipt"]
        alias = path.with_name("other.json")
        alias.write_bytes(path.read_bytes())
        symlink = path.with_name("link.json")
        symlink.symlink_to(path)
        for options in ({"target_files_metadata_receipt_sha256": "0" * 64},
                        {"target_files_metadata_receipt": alias}, {"target_files_metadata_receipt": symlink}):
            with self.subTest(options=options), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused-metadata", **dict(inputs, **options))
        verifier.assert_not_called()

    def test_metadata_receipt_rejects_special_files_and_hardlinks_before_opening(self):
        inputs, _, _, verifier = self.metadata_inputs()
        original = inputs["target_files_metadata_receipt"]
        for kind in ("directory", "fifo", "hardlink"):
            parent = self.root / kind
            parent.mkdir()
            path = parent / generator.TARGET_FILES_METADATA_RECEIPT
            if kind == "directory":
                path.mkdir()
            elif kind == "fifo":
                os.mkfifo(path)
            else:
                path.hardlink_to(original)
            with self.subTest(kind=kind), self.assertRaisesRegex(generator.CandidateError, "metadata receipt refused"):
                generator._verify_target_files_metadata(path,
                    expected_receipt_sha256=inputs["target_files_metadata_receipt_sha256"])
            if kind == "hardlink":
                path.unlink()
        verifier.assert_not_called()

    def test_metadata_rejects_self_consistent_noncurrent_copied_public_controls(self):
        inputs, _, receipt, verifier = self.metadata_inputs()
        mutations = [
            lambda row: row["profile"].update(sha256="0" * 64),
            lambda row: row["source_composition"]["project"].update(commit="0" * 40),
            lambda row: row["source_composition"]["final_source_files"][0].update(sha256="0" * 64),
            lambda row: row["source_composition"]["contracts"][0].update(sha256="0" * 64),
            lambda row: row["scope"].update(metadata_only=1),
            lambda row: row["scope"].update(complete_rom_admitted=0),
            lambda row: row["files"].pop(),
        ]
        mutations.extend(lambda row, path=entry["path"]: next(item for item in row["bundle_files"]
                                                            if item["path"] == path).update(sha256="0" * 64)
                         for entry in receipt["bundle_files"])
        mutations.append(lambda row: row["bundle_files"].append({"path": "tools/unreviewed.py", "sha256": "0" * 64, "size_bytes": 1}))
        original_files, reader = verifier.return_value[1:]
        for mutate in mutations:
            changed = copy.deepcopy(receipt)
            mutate(changed)
            verifier.return_value = changed, original_files, reader
            with self.subTest(mutate=mutate), self.assertRaisesRegex(generator.CandidateError, "current public"):
                generator.generate(self.root / "artifacts/refused-metadata", **inputs)
        self.assertFalse((self.root / "artifacts/refused-metadata").exists())

    def test_metadata_requires_original_factory_images_and_same_vendor_bundle(self):
        inputs, public, _, _ = self.metadata_inputs()
        verify = generator._verify_target_files_metadata
        for partition in ("vendor", "odm"):
            changed = copy.deepcopy(public)
            changed["images"][partition]["sha256"] = "0" * 64
            raw = inputs["target_files_metadata_receipt"].read_bytes()
            changed["receipt"] = {"path": generator.TARGET_FILES_METADATA_RECEIPT,
                                  "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
            with self.subTest(partition=partition), mock.patch.object(generator, "_verify_target_files_metadata", return_value=changed), \
                    self.assertRaisesRegex(generator.CandidateError, "exact original factory vendor/ODM"):
                generator.generate(self.root / "artifacts/refused-metadata", **inputs)

        def changed_vendor(*args, **kwargs):
            result = verify(*args, **kwargs)
            path = inputs["vendor_receipt"]
            path.write_bytes(path.read_bytes() + b"\n")
            return result

        with mock.patch.object(generator, "_verify_target_files_metadata", side_effect=changed_vendor), \
                self.assertRaisesRegex(generator.CandidateError, "vendor inputs changed"):
            generator.generate(self.root / "artifacts/refused-metadata", **inputs)

    def test_metadata_rejects_legacy_mi_ext_and_recovery_source_compositions(self):
        inputs, _, _, _ = self.metadata_inputs()
        binding = generator._verify_mi_ext_inputs.return_value
        binding["native_source"].pop("composition")
        binding["native_source"].pop("composition_identity")
        with self.assertRaises(generator.CandidateError):
            generator.generate(self.root / "artifacts/refused-legacy-mi", **inputs)
        # The exact renderer refuses an altered legacy template before it can
        # be turned into a new composition-specific guard.
        original = (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        with self.assertRaisesRegex(generator.CandidateError, "recovery source binding refused"):
            generator._metadata_recovery_include(original + b"# unreviewed selector\n")

    def test_metadata_validation_rejects_resealed_source_scope_and_bundle_claims(self):
        inputs, _, _, _ = self.metadata_inputs()
        output = self.root / "artifacts/metadata-scope"
        original = generator.generate(output, **inputs)
        mutations = [
            lambda p: p["target_files_metadata"].update(bundle="vendor/xiaomi/other"),
            lambda p: p["target_files_metadata"].update(factory_package_sha256="0" * 64),
            lambda p: p["target_files_metadata"].update(metadata_file_count=204),
            lambda p: p["target_files_metadata"]["scope"].update(vintf_verified=True),
            lambda p: p["target_files_metadata"]["scope"].update(ota_verified=0),
            lambda p: p["target_files_metadata"]["native_source"]["final_source_files"][0].update(sha256="0" * 64),
            lambda p: p["target_files_metadata"]["control_files"][0].update(sha256="0" * 64),
            lambda p: p["target_files_metadata"]["vendor_bundle"].update(sha256="0" * 64),
            lambda p: (p["target_files_metadata"].update(vendor_bundle={"sha256": "invalid", "size_bytes": True}),
                       p["bundles"]["vendor"].update(sha256="invalid", size_bytes=True)),
            lambda p: p["target_files_metadata"]["receipt"].update(size_bytes=True),
            lambda p: p["target_files_metadata"]["receipt"].update(path="other.json"),
            lambda p: p["mi_ext_inputs"]["native_source"].pop("composition"),
            lambda p: p.update(release_config="other"),
            lambda p: p["admission"].update(full_rom_build_allowed=True),
        ]
        for mutate in mutations:
            plan = copy.deepcopy(original)
            mutate(plan)
            (output / "admission.json").write_text(json.dumps(plan))
            with self.subTest(mutate=mutate), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_metadata_validation_rejects_resealed_selectors_and_legacy_recovery(self):
        inputs, _, _, _ = self.metadata_inputs()
        output = self.root / "artifacts/metadata-wiring"
        plan = generator.generate(output, **inputs)
        changes = {
            "generated/target-files-metadata.mk": lambda raw: raw.replace(b" := ", b" ?= "),
            "generated/BoardConfigCandidate.mk": lambda raw: raw.replace(b"include $(NEZHA_DEVICE_PATH)/generated/target-files-metadata.mk\n", b""),
            "recovery-prebuilt.mk": lambda _: (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes(),
        }
        for relative, mutate in changes.items():
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, mutate(original))
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)
        self.assertEqual(generator.validate(output), plan)

    def test_metadata_selectors_cannot_move_to_other_make_or_blueprint_files(self):
        inputs, _, _, _ = self.metadata_inputs()
        output = self.root / "artifacts/metadata-duplicate-selector"
        plan = generator.generate(output, **inputs)
        lines = [b"BOARD_NEZHA_PREBUILT_METADATA := false\n",
                 b"BOARD_NEZHA_PREBUILT_METADATA_RECEIPT_SHA256 := 0\n",
                 b"BOARD_NEZHA_PREBUILT_METADATA_TOOL_SHA256 := 0\n",
                 b"NEZHA_PREBUILT_METADATA_ROOT := elsewhere\n",
                 b"include vendor/xiaomi/nezha-target-files-metadata/selection.mk\n",
                 b"include $(NEZHA_DEVICE_PATH)/generated/target-files-metadata.mk\n",
                 b"EXTRA_TOOL := target_files_metadata.py\n"]
        for relative in ("device.mk", "BoardConfig.mk", "Android.bp", "generated/device-candidate.mk"):
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            for line in lines:
                self.reseal_candidate_file(output, plan, name, original + line)
                with self.subTest(name=name, line=line), self.assertRaises(generator.CandidateError):
                    generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)
        self.assertEqual(generator.validate(output), plan)

    def test_metadata_cannot_be_enabled_without_its_explicit_capability(self):
        inputs = self.generation_inputs()
        output = self.root / "artifacts/metadata-unselected"
        plan = generator.generate(output, **inputs)
        for relative, line in (("generated/BoardConfigCandidate.mk", b"BOARD_NEZHA_PREBUILT_METADATA := true\n"),
                               ("device.mk", b"include $(NEZHA_DEVICE_PATH)/generated/target-files-metadata.mk\n"),
                               ("Android.bp", b"// vendor/xiaomi/nezha-target-files-metadata\n")):
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, original + line)
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)
        unexpected = output / generator.TARGET_FILES_METADATA_INCLUDE
        unexpected.write_text("BOARD_NEZHA_PREBUILT_METADATA := true\n")
        with self.assertRaisesRegex(generator.CandidateError, "unexpected candidate file|unlisted or missing candidate file"):
            generator.validate(output)

    def test_metadata_validation_does_not_reopen_private_inputs(self):
        inputs, _, _, _ = self.metadata_inputs()
        output = self.root / "artifacts/portable-metadata"
        plan = generator.generate(output, **inputs)
        inputs["target_files_metadata_receipt"].unlink()
        with mock.patch.object(generator, "_verify_target_files_metadata", side_effect=AssertionError("private input read")):
            self.assertEqual(generator.validate(output), plan)

    def test_metadata_external_verification_failure_or_late_change_cannot_publish(self):
        from scripts import target_files_metadata as metadata
        inputs, _, _, verifier = self.metadata_inputs()
        verified = verifier.return_value
        for calls in ([metadata.TargetFilesMetadataError("unlisted file")],
                      [verified, metadata.TargetFilesMetadataError("late unlisted empty directory")]):
            verifier.side_effect = calls
            with self.subTest(calls=calls), self.assertRaisesRegex(generator.CandidateError, "metadata bundle refused"):
                generator.generate(self.root / "artifacts/refused-metadata", **inputs)
            self.assertFalse((self.root / "artifacts/refused-metadata").exists())

    def test_metadata_rechecks_final_inventory_after_the_verifier_recheck(self):
        inputs, _, _, verifier = self.metadata_inputs()
        reader = verifier.return_value[2]
        bundle = inputs["target_files_metadata_receipt"].parent
        for kind in ("file", "empty-directory"):
            late = bundle / ("late-" + kind)
            def add_late():
                if kind == "file":
                    late.write_bytes(b"unexpected")
                else:
                    late.mkdir()
            # The first wrapper succeeds. Mutate during the last bound-reader
            # pass of the second wrapper immediately before publication.
            def recheck():
                if reader.recheck.call_count == 2:
                    add_late()
            reader.recheck.side_effect = recheck
            with self.subTest(kind=kind), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused-metadata", **inputs)
            self.assertFalse((self.root / "artifacts/refused-metadata").exists())
            late.rmdir() if kind == "empty-directory" else late.unlink()
            reader.recheck.reset_mock()

    def test_metadata_rechecks_vendor_receipt_before_candidate_publication(self):
        inputs, _, _, _ = self.metadata_inputs()
        validate = generator.validate
        def change_after_validation(*args, **kwargs):
            result = validate(*args, **kwargs)
            path = inputs["vendor_receipt"]
            path.write_bytes(path.read_bytes() + b"\n")
            return result
        with mock.patch.object(generator, "validate", side_effect=change_after_validation), \
                self.assertRaisesRegex(generator.CandidateError, "vendor inputs changed"):
            generator.generate(self.root / "artifacts/refused-metadata", **inputs)
        self.assertFalse((self.root / "artifacts/refused-metadata").exists())

    def test_metadata_output_cannot_be_nested_inside_the_private_bundle(self):
        inputs, _, _, _ = self.metadata_inputs()
        output = inputs["target_files_metadata_receipt"].parent / "new-candidate"
        with self.assertRaisesRegex(generator.CandidateError, "nested inside a target-files metadata bundle"):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())

    def test_cli_preserves_explicit_metadata_receipt_and_external_digest(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        cases = [([], None, None),
                 (["--target-files-metadata-receipt", "metadata.json", "--target-files-metadata-receipt-sha256", "1" * 64],
                  Path("metadata.json"), "1" * 64)]
        for options, path, digest in cases:
            with self.subTest(options=options), mock.patch.object(generator, "generate", return_value={}) as generate, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + options), 0)
            self.assertEqual(generate.call_args.kwargs["target_files_metadata_receipt"], path)
            self.assertEqual(generate.call_args.kwargs["target_files_metadata_receipt_sha256"], digest)

    def readonly_inputs(self, inputs=None):
        """Mock only private image verification; retain the real source composers."""
        from scripts import mi_ext_inputs as mi
        inputs, binding = self.mi_ext_inputs(inputs)
        selected = ROOT / generator.DIRECT_AVB_READONLY_CONTRACT
        public = generator._direct_avb_readonly_public(selected)
        config, legacy, controls = mi._controls.return_value
        source = copy.deepcopy(legacy)
        source.update(composition=public["native_source"], composition_identity=public["composition_identity"])
        mi._controls.side_effect = lambda reader, composed_source_contract=None: (
            config, legacy if composed_source_contract is None else source, controls)
        binding["native_source"] = mi._native_source(source)
        receipt = inputs["mi_ext_inputs_receipt"]
        receipt.parent.chmod(0o700)
        receipt.chmod(0o600)
        for member in (mi.IMAGE_MEMBER, mi.LOGICAL_RECEIPT_MEMBER):
            path = receipt.parent / member
            path.write_bytes(b"synthetic private input")
            path.chmod(0o600)
        inputs["direct_avb_readonly_contract"] = selected
        verifier = self.enterContext(mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=binding))
        return inputs, public, binding, verifier

    def test_readonly_is_not_selected_or_read_by_default_or_metadata(self):
        inputs = self.generation_inputs()
        with mock.patch.object(generator, "_direct_avb_readonly_public", side_effect=AssertionError("implicit 0010 selection")), \
                mock.patch.object(generator, "_readonly_recovery_include", side_effect=AssertionError("implicit recovery selection")):
            first = generator.generate(self.root / "artifacts/readonly-default", **inputs)
            second = generator.generate(self.root / "artifacts/readonly-explicit-none", direct_avb_readonly_contract=None, **inputs)
        self.assertEqual(first, second)
        self.assertNotIn("direct_avb_readonly", first)
        original = (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        self.assertEqual((self.root / "artifacts/readonly-default" / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes(), original)

    def test_readonly_does_not_change_the_existing_metadata_rendering(self):
        inputs, _, _, _ = self.metadata_inputs()
        with mock.patch.object(generator, "_direct_avb_readonly_public", side_effect=AssertionError("implicit 0010 selection")):
            first = generator.generate(self.root / "artifacts/metadata-before-readonly", **inputs)
            second = generator.generate(self.root / "artifacts/metadata-explicit-no-readonly", direct_avb_readonly_contract=None, **inputs)
        self.assertEqual(first, second)
        self.assertNotIn("direct_avb_readonly", first)
        recovery = (self.root / "artifacts/metadata-before-readonly" / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        self.assertEqual(hashlib.sha256(recovery).hexdigest(), "09241772ac54621a68fb7ed742d5f86d15ad975831d8ee9d97b122202706162f")

    def test_readonly_requires_factory_and_mi_ext_and_rejects_metadata_before_reads(self):
        base = {"record_paths": {}, "kernel_receipt": "none", "vendor_receipt": "none",
                "direct_avb_readonly_contract": "none"}
        factory = {"factory_boot_contract": "none", "partition_metadata": "none", "fstab_source": "none"}
        options = [{}, factory, {**factory, "mi_ext_inputs_receipt": "none", "target_files_metadata_receipt": "none"},
                   {**factory, "mi_ext_inputs_receipt": "none", "target_files_metadata_receipt_sha256": "1" * 64},
                   {**factory, "mi_ext_inputs_receipt": "none", "target_files_metadata_receipt": "none",
                    "target_files_metadata_receipt_sha256": "1" * 64}]
        for extra in options:
            with self.subTest(options=extra), mock.patch.object(generator, "_load_records") as load, \
                    self.assertRaisesRegex(generator.CandidateError, "direct AVB read-only"):
                generator.generate(self.root / "artifacts/refused-readonly", **base, **extra)
            load.assert_not_called()

    def test_readonly_generation_binds_eight_source_files_and_retains_readiness(self):
        inputs, public, binding, verifier = self.readonly_inputs()
        first, second = self.root / "artifacts/readonly-first", self.root / "artifacts/readonly-repeat"
        plan = generator.generate(first, **inputs)
        self.assertEqual(generator.generate(second, **inputs), plan)
        self.assertEqual(verifier.call_count, 4)
        for call in verifier.call_args_list:
            self.assertEqual(call, mock.call(inputs["mi_ext_inputs_receipt"], expected_package_sha256="3" * 64,
                                            composed_source_contract=ROOT / generator.DIRECT_AVB_READONLY_CONTRACT))
        self.assertEqual(plan["direct_avb_readonly"], public)
        self.assertEqual(plan["mi_ext_inputs"], binding)
        self.assertNotIn("target_files_metadata", plan)
        composition = public["native_source"]
        self.assertEqual(len(composition["contracts"]), 4)
        self.assertEqual(len(composition["ordered_patches"]), 4)
        self.assertEqual(len(composition["core_transitions"]), 3)
        self.assertEqual(len(composition["final_source_files"]), 8)
        self.assertIn("build/make/core/product.mk", {row["path"] for row in composition["final_source_files"]})
        self.assertEqual(composition["contracts"][-1]["path"], generator.DIRECT_AVB_READONLY_CONTRACT)
        self.assertEqual(public["scope"], generator.DIRECT_AVB_READONLY_SCOPE)
        self.assertTrue(plan["admission"]["configuration_allowed"])
        self.assertTrue(all(value is False for key, value in plan["admission"].items() if key != "configuration_allowed"))
        recovery = (first / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        legacy = (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        self.assertEqual(recovery, generator._readonly_recovery_include(legacy))
        self.assertNotEqual(recovery, legacy)
        mi_include = (first / generator.MI_EXT_BOARD_INCLUDE).read_bytes()
        for row in composition["final_source_files"]:
            self.assertIn(row["sha256"].encode(), recovery)
            self.assertIn(row["sha256"].encode(), mi_include)
        self.assertNotIn(b"BOARD_NEZHA_PREBUILT_METADATA", (first / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_bytes())
        self.assertEqual(generator.validate(first), plan)
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(first, purpose=purpose)

    def test_readonly_coexists_with_property_sources_without_selecting_providers(self):
        inputs, policy = self.property_inputs()
        inputs, public, _, _ = self.readonly_inputs(inputs)
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy):
            plan = generator.generate(self.root / "artifacts/readonly-properties", **inputs)
        self.assertEqual(plan["direct_avb_readonly"], public)
        self.assertIn("oem_properties", plan)
        self.assertIn("oem_policy", plan)
        self.assertIn("init_helper_capability", plan)
        self.assertNotIn("framework_providers", plan)
        self.assertNotIn("target_files_metadata", plan)

    def test_readonly_rejects_unreviewed_contract_before_verifying_private_mi_ext(self):
        inputs, _, _, verifier = self.readonly_inputs()
        selected = self.root / "selected-readonly.json"
        original = (ROOT / generator.DIRECT_AVB_READONLY_CONTRACT).read_bytes()
        for raw in (original + b"\n", (ROOT / generator.TARGET_FILES_METADATA_CONTRACT).read_bytes(),
                    original.replace(generator.DIRECT_AVB_READONLY_CONTRACT_ID.encode(), b"unknown-contract")):
            selected.write_bytes(raw)
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused-readonly", **dict(inputs, direct_avb_readonly_contract=selected))
        verifier.assert_not_called()
        selected.unlink()
        selected.symlink_to(ROOT / generator.DIRECT_AVB_READONLY_CONTRACT)
        with self.assertRaisesRegex(generator.CandidateError, "symlink refused"):
            generator.generate(self.root / "artifacts/refused-readonly", **dict(inputs, direct_avb_readonly_contract=selected))
        verifier.assert_not_called()

    def test_readonly_selected_contract_rejects_special_files_and_hardlinks(self):
        selected = self.root / "readonly.json"
        original = self.root / "original-readonly.json"
        original.write_bytes((ROOT / generator.DIRECT_AVB_READONLY_CONTRACT).read_bytes())
        for kind in ("directory", "fifo", "hardlink"):
            if kind == "directory":
                selected.mkdir()
            elif kind == "fifo":
                os.mkfifo(selected)
            else:
                selected.hardlink_to(original)
            with self.subTest(kind=kind), self.assertRaisesRegex(generator.CandidateError, "contract input refused"):
                generator._direct_avb_readonly_public(selected)
            selected.rmdir() if kind == "directory" else selected.unlink()

    def test_readonly_validation_rejects_resealed_composition_scope_and_readiness(self):
        inputs, _, _, _ = self.readonly_inputs()
        output = self.root / "artifacts/readonly-provenance"
        original = generator.generate(output, **inputs)
        mutations = [
            lambda p: p["direct_avb_readonly"].update(contract_id="other"),
            lambda p: p["direct_avb_readonly"]["contract_record"].update(sha256="0" * 64),
            lambda p: p["direct_avb_readonly"]["scope"].update(native_kati_verified=True),
            lambda p: p["direct_avb_readonly"]["scope"].update(source_patch_applied=0),
            lambda p: p["direct_avb_readonly"]["composition_identity"].update(sha256="0" * 64),
            lambda p: p["direct_avb_readonly"]["native_source"]["core_transitions"].pop(),
            lambda p: p["direct_avb_readonly"]["native_source"]["final_source_files"][0].update(sha256="0" * 64),
            lambda p: p["direct_avb_readonly"]["native_source"].update(schema_version=True),
            lambda p: p["mi_ext_inputs"]["native_source"]["composition"].update(whole_source_tree_verified=0),
            lambda p: p["mi_ext_inputs"]["native_source"].pop("composition_identity"),
            lambda p: p.update(target_files_metadata={}),
            lambda p: p.pop("direct_avb_readonly"),
            lambda p: p.update(release_config="other"),
            lambda p: p["factory_profile"].update(origin_verified=True),
            lambda p: p["admission"].update(full_rom_build_allowed=True),
        ]
        for mutate in mutations:
            plan = copy.deepcopy(original)
            mutate(plan)
            (output / "admission.json").write_text(json.dumps(plan))
            with self.subTest(mutate=mutate), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_readonly_validation_rejects_legacy_and_metadata_recovery_guards(self):
        inputs, _, _, _ = self.readonly_inputs()
        output = self.root / "artifacts/readonly-recovery-mismatch"
        plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "recovery-prebuilt.mk").as_posix()
        original = (output / name).read_bytes()
        legacy = (ROOT / name).read_bytes()
        for raw in (legacy, generator._metadata_recovery_include(legacy), original + b"# changed guard\n"):
            self.reseal_candidate_file(output, plan, name, raw)
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaisesRegex(generator.CandidateError, "matching recovery source guard"):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, name, original)
        self.assertEqual(generator.validate(output), plan)

    def test_readonly_rechecks_selected_contract_before_publication(self):
        inputs, _, _, _ = self.readonly_inputs()
        selected = self.root / "readonly-selection.json"
        selected.write_bytes((ROOT / generator.DIRECT_AVB_READONLY_CONTRACT).read_bytes())
        inputs["direct_avb_readonly_contract"] = selected
        validate = generator.validate
        def change_selected(*args, **kwargs):
            result = validate(*args, **kwargs)
            selected.write_bytes(selected.read_bytes() + b"\n")
            return result
        with mock.patch.object(generator, "validate", side_effect=change_selected), self.assertRaises(generator.CandidateError):
            generator.generate(self.root / "artifacts/refused-readonly", **inputs)
        self.assertFalse((self.root / "artifacts/refused-readonly").exists())

    def test_readonly_rechecks_mi_ext_inputs_and_inventory_before_publication(self):
        inputs, _, binding, verifier = self.readonly_inputs()
        changed = copy.deepcopy(binding)
        changed["receipt"]["sha256"] = "0" * 64
        verifier.side_effect = [binding, changed]
        with self.assertRaisesRegex(generator.CandidateError, "mi_ext inputs changed before"):
            generator.generate(self.root / "artifacts/refused-readonly", **inputs)
        self.assertFalse((self.root / "artifacts/refused-readonly").exists())
        bundle = inputs["mi_ext_inputs_receipt"].parent
        verifier.side_effect = None
        verifier.reset_mock()
        def add_after_final_verifier(*args, **kwargs):
            if verifier.call_count == 2:
                (bundle / "unexpected-directory").mkdir()
            return binding
        verifier.side_effect = add_after_final_verifier
        with self.assertRaisesRegex(generator.CandidateError, "mi_ext inventory refused"):
            generator.generate(self.root / "artifacts/refused-readonly", **inputs)
        self.assertFalse((self.root / "artifacts/refused-readonly").exists())

    def test_readonly_candidate_cannot_be_nested_inside_its_mi_ext_bundle(self):
        inputs, _, _, _ = self.readonly_inputs()
        # Place the existing synthetic bundle under artifacts so this exercises
        # the specific preserved-input check rather than the output-root guard.
        old = inputs["mi_ext_inputs_receipt"].parent
        new = self.root / "artifacts/readonly-mi-ext"
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        inputs["mi_ext_inputs_receipt"] = new / inputs["mi_ext_inputs_receipt"].name
        output = new / "new-candidate"
        with self.assertRaisesRegex(generator.CandidateError, "nested inside its mi_ext bundle"):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())

    def test_readonly_candidate_validation_never_reopens_private_mi_ext_bundle(self):
        inputs, _, _, _ = self.readonly_inputs()
        output = self.root / "artifacts/portable-readonly"
        plan = generator.generate(output, **inputs)
        inputs["mi_ext_inputs_receipt"].unlink()
        with mock.patch.object(generator, "_verify_mi_ext_inputs", side_effect=AssertionError("private bundle reopened")):
            self.assertEqual(generator.validate(output), plan)

    def test_readonly_cli_argument_is_optional_and_explicit(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--direct-avb-readonly-contract", "readonly.json"], Path("readonly.json"))):
            with self.subTest(args=args), mock.patch.object(generator, "generate", return_value={}) as generate, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["direct_avb_readonly_contract"], expected)

    def test_combined_source_requires_paired_metadata_and_rejects_standalone_readonly(self):
        base = {"record_paths": {}, "kernel_receipt": "none", "vendor_receipt": "none",
                "target_files_source_contract": "none"}
        factory = {"factory_boot_contract": "none", "partition_metadata": "none", "fstab_source": "none"}
        metadata = {"target_files_metadata_receipt": "none", "target_files_metadata_receipt_sha256": "1" * 64}
        cases = [{}, {"target_files_metadata_receipt": "none"},
                 {"target_files_metadata_receipt_sha256": "1" * 64}, metadata, {**metadata, **factory},
                 {**metadata, **factory, "mi_ext_inputs_receipt": "none", "direct_avb_readonly_contract": "none"}]
        for options in cases:
            with self.subTest(options=options), mock.patch.object(generator, "_load_records") as load, \
                    self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused-combined", **base, **options)
            load.assert_not_called()

    def test_combined_source_is_not_selected_by_original_metadata_or_default(self):
        inputs, _, _, _ = self.metadata_inputs()
        with mock.patch.object(generator, "_target_files_source_reference", side_effect=AssertionError("implicit combined selection")):
            first = generator.generate(self.root / "artifacts/old-metadata-no-combined", **inputs)
            second = generator.generate(self.root / "artifacts/old-metadata-explicit-none", target_files_source_contract=None, **inputs)
        self.assertEqual(first, second)
        self.assertNotIn("source_contract", first["target_files_metadata"])
        self.assertEqual(first["target_files_metadata"]["composition_identity"]["sha256"],
                         "6cc3a2bc48603a8eb8b15082252350dc550c0dfc669af24d96e6b4e1a317ad0f")

    def test_combined_source_generation_binds_ten_sources_and_standalone_runtime(self):
        selected = ROOT / generator.TARGET_FILES_SOURCE_CONTRACT
        inputs, public, _, verifier = self.metadata_inputs(source_contract=selected)
        first, second = self.root / "artifacts/combined-first", self.root / "artifacts/combined-repeat"
        plan = generator.generate(first, **inputs)
        self.assertEqual(generator.generate(second, **inputs), plan)
        self.assertEqual(verifier.call_count, 4)
        for call in verifier.call_args_list:
            self.assertEqual(call, mock.call(inputs["target_files_metadata_receipt"].parent,
                                            expected_receipt=inputs["target_files_metadata_receipt_sha256"],
                                            source_contract=selected))
        self.assertEqual(generator._verify_mi_ext_inputs.call_count, 4)
        for call in generator._verify_mi_ext_inputs.call_args_list:
            self.assertEqual(call.kwargs["composed_source_contract"], selected)
        binding = plan["target_files_metadata"]
        self.assertEqual(binding["source_contract"], generator._target_files_source_reference(selected))
        self.assertEqual(binding["native_source"], public["native_source"])
        self.assertEqual(len(binding["native_source"]["ordered_patches"]), 7)
        self.assertEqual(len(binding["native_source"]["contracts"]), 8)
        self.assertEqual(len(binding["native_source"]["final_source_files"]), 10)
        sources = {row["path"]: row for row in binding["native_source"]["final_source_files"]}
        self.assertEqual(sources["build/make/core/Makefile"]["sha256"],
                         "bf6e0668ff571f3858fc09d5cefa039ff6a8fdebf5b9ecfdc690794f25889ba7")
        self.assertEqual(sources["build/make/tools/releasetools/check_target_files_vintf.py"]["sha256"],
                         "8ada3c9809c7b6e5e07dd02a361a1dcb8a28b615bc37f62f46e156ac06159a93")
        self.assertIn("build/make/core/product.mk", sources)
        self.assertEqual(binding["metadata_file_count"], 205)
        self.assertNotIn("direct_avb_readonly", plan)
        self.assertTrue(all(value is False for key, value in plan["admission"].items() if key != "configuration_allowed"))
        runtime = next(row for row in binding["control_files"] if row["path"] == "tools/target_files_metadata.py")
        self.assertNotEqual(runtime["sha256"], hashlib.sha256((ROOT / "scripts/target_files_metadata.py").read_bytes()).hexdigest())
        self.assertEqual([row["path"] for row in binding["control_files"] if row["path"].startswith("tools/")],
                         ["tools/target_files_metadata.py"])
        include = (first / generator.TARGET_FILES_METADATA_INCLUDE).read_bytes()
        self.assertIn(runtime["sha256"].encode(), include)
        recovery = (first / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        legacy = (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        self.assertEqual(recovery, generator._metadata_recovery_include(legacy, source_contract=selected))
        for row in sources.values():
            self.assertIn(row["sha256"].encode(), recovery)
            self.assertIn(row["sha256"].encode(), (first / generator.MI_EXT_BOARD_INCLUDE).read_bytes())
        self.assertEqual(generator.validate(first), plan)
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(first, purpose=purpose)

    def test_combined_source_coexists_with_property_only_profile(self):
        inputs, policy = self.property_inputs()
        inputs, _, _, _ = self.metadata_inputs(inputs=inputs, source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy):
            plan = generator.generate(self.root / "artifacts/combined-properties", **inputs)
        self.assertIn("oem_properties", plan)
        self.assertIn("init_helper_capability", plan)
        self.assertIn("source_contract", plan["target_files_metadata"])
        self.assertNotIn("framework_providers", plan)
        self.assertNotIn("direct_avb_readonly", plan)

    def test_combined_source_reference_rejects_forged_special_and_linked_inputs(self):
        canonical = ROOT / generator.TARGET_FILES_SOURCE_CONTRACT
        selected = self.root / "source-selection.json"
        for raw in (canonical.read_bytes() + b"\n", (ROOT / generator.DIRECT_AVB_READONLY_CONTRACT).read_bytes(),
                    (ROOT / generator.TARGET_FILES_METADATA_CONTRACT).read_bytes()):
            selected.write_bytes(raw)
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaises(generator.CandidateError):
                generator._target_files_source_reference(selected)
        selected.unlink()
        original = self.root / "source-original.json"
        original.write_bytes(canonical.read_bytes())
        for kind in ("directory", "fifo", "hardlink", "symlink"):
            if kind == "directory":
                selected.mkdir()
            elif kind == "fifo":
                os.mkfifo(selected)
            elif kind == "hardlink":
                selected.hardlink_to(original)
            else:
                selected.symlink_to(original)
            with self.subTest(kind=kind), self.assertRaises(generator.CandidateError):
                generator._target_files_source_reference(selected)
            selected.rmdir() if kind == "directory" else selected.unlink()

    def test_checksum_source_public_binding_preserves_policy_and_metadata_inputs(self):
        from scripts import target_files_metadata_checksum as checksum
        image = ROOT / generator.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT
        before = generator._metadata_public_binding(
            source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT, image_contract=image)
        after = generator._metadata_public_binding(
            source_contract=ROOT / generator.TARGET_FILES_CHECKSUM_SOURCE_CONTRACT, image_contract=image)
        changed = {"source_contract", "control_files", "native_source", "composition_identity"}
        self.assertEqual({key: value for key, value in before.items() if key not in changed},
                         {key: value for key, value in after.items() if key not in changed})
        old_sources = {row["path"]: row for row in before["native_source"]["final_source_files"]}
        new_sources = {row["path"]: row for row in after["native_source"]["final_source_files"]}
        self.assertEqual(new_sources, {**old_sources, checksum.CORE: {"path": checksum.CORE, **checksum.CORE_AFTER}})
        self.assertEqual(after["native_source"], checksum._derive_composition(before["native_source"]))
        runtime = next(row for row in after["control_files"] if row["path"] == "tools/target_files_metadata.py")
        include = generator._render_metadata_include({**after, "receipt": {"sha256": "1" * 64}})
        self.assertIn(runtime["sha256"], include)
        self.assertEqual(generator._metadata_options(after), {
            "source_contract": ROOT / generator.TARGET_FILES_CHECKSUM_SOURCE_CONTRACT,
            "image_contract": image,
        })

    def test_checksum_source_module_requires_explicit_matching_policy3_images(self):
        from scripts import target_files_metadata_checksum as checksum
        from scripts import target_files_metadata_combined as combined
        source = ROOT / generator.TARGET_FILES_CHECKSUM_SOURCE_CONTRACT
        self.assertIs(generator._metadata_module(
            source_contract=source, image_contract=ROOT / generator.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT), checksum)
        self.assertIs(generator._metadata_module(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT), combined)
        for image in (None, ROOT / generator.POLICY_IMAGE_DELIVERY_CONTRACT,
                      ROOT / generator.POLICY_IMAGE_DELIVERY_4K_CONTRACT):
            with self.subTest(image=image), self.assertRaisesRegex(generator.CandidateError, "policy3"):
                generator._metadata_module(source_contract=source, image_contract=image)

    def test_checksum_source_reference_and_binding_reject_forgery(self):
        source = ROOT / generator.TARGET_FILES_CHECKSUM_SOURCE_CONTRACT
        selected = self.root / "checksum-source.json"
        raw = source.read_bytes()
        selected.write_bytes(raw)
        reference = generator._target_files_source_reference(source)
        self.assertEqual(generator._target_files_source_reference(selected), reference)
        for changed in (raw + b"\n", b"not JSON", b"[]", b"\xff", b'{"contract_id":"unreviewed"}'):
            selected.write_bytes(changed)
            with self.subTest(changed=changed[:32]), self.assertRaises(generator.CandidateError):
                generator._target_files_source_reference(selected)
        for key, value in (("contract_id", generator.TARGET_FILES_SOURCE_CONTRACT_ID),
                           ("path", generator.TARGET_FILES_SOURCE_CONTRACT),
                           ("sha256", "0" * 64), ("size_bytes", True)):
            forged = {**reference, key: value}
            with self.subTest(key=key), self.assertRaises(generator.CandidateError):
                generator._metadata_source_selection({"source_contract": forged})
        selected.unlink()
        selected.symlink_to(source)
        with self.assertRaises(generator.CandidateError):
            generator._target_files_source_reference(selected)

    def test_checksum_recovery_renderer_uses_complete_new_source_guard(self):
        from scripts import target_files_metadata_checksum as checksum
        template = (ROOT / generator.DEVICE_PATH / "recovery-prebuilt.mk").read_bytes()
        selected = ROOT / generator.TARGET_FILES_CHECKSUM_SOURCE_CONTRACT
        rendered = generator._metadata_recovery_include(template, source_contract=selected)
        composition = checksum.compose_sources(ROOT, source_contract=selected)
        self.assertIn(checksum.identity(checksum.encoded(composition))["sha256"].encode(), rendered)
        self.assertNotIn(checksum.CORE_BEFORE["sha256"].encode(), rendered)
        for row in composition["final_source_files"]:
            self.assertIn(row["sha256"].encode(), rendered, row["path"])

    def test_combined_source_validation_rejects_removed_forged_or_mixed_selection(self):
        inputs, _, _, _ = self.metadata_inputs(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        output = self.root / "artifacts/combined-provenance"
        original = generator.generate(output, **inputs)
        changes = [
            lambda p: p["target_files_metadata"].pop("source_contract"),
            lambda p: p["target_files_metadata"]["source_contract"].update(contract_id="other"),
            lambda p: p["target_files_metadata"]["source_contract"].update(path=generator.DIRECT_AVB_READONLY_CONTRACT),
            lambda p: p["target_files_metadata"]["source_contract"].update(sha256="0" * 64),
            lambda p: p["target_files_metadata"]["source_contract"].update(size_bytes=True),
            lambda p: p["target_files_metadata"]["native_source"]["final_source_files"].pop(),
            lambda p: p["target_files_metadata"]["native_source"]["contracts"].pop(),
            lambda p: p["target_files_metadata"]["native_source"].update(whole_source_tree_verified=0),
            lambda p: p["target_files_metadata"]["scope"].update(target_files_verified=True),
            lambda p: p["mi_ext_inputs"]["native_source"]["composition"].update(schema_version=True),
            lambda p: p.update(direct_avb_readonly={}),
            lambda p: p["factory_profile"].update(origin_verified=True),
        ]
        for change in changes:
            plan = copy.deepcopy(original)
            change(plan)
            (output / "admission.json").write_text(json.dumps(plan))
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_combined_source_validation_rejects_older_recovery_variants(self):
        inputs, _, _, _ = self.metadata_inputs(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        output = self.root / "artifacts/combined-recovery"
        plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "recovery-prebuilt.mk").as_posix()
        original = (output / name).read_bytes()
        legacy = (ROOT / name).read_bytes()
        for raw in (legacy, generator._metadata_recovery_include(legacy), generator._readonly_recovery_include(legacy)):
            self.reseal_candidate_file(output, plan, name, raw)
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaisesRegex(generator.CandidateError, "matching recovery source guard"):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, name, original)
        self.assertEqual(generator.validate(output), plan)

    def test_combined_source_rejects_noncurrent_adapter_runtime_and_control_copies(self):
        inputs, _, receipt, verifier = self.metadata_inputs(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        targets = [row["path"] for row in receipt["bundle_files"] if row["path"].startswith(("tools/", "controls/scripts/"))]
        for path in targets:
            changed = copy.deepcopy(receipt)
            next(row for row in changed["bundle_files"] if row["path"] == path)["sha256"] = "0" * 64
            verifier.return_value = changed, verifier.return_value[1], verifier.return_value[2]
            with self.subTest(path=path), self.assertRaisesRegex(generator.CandidateError, "current public inputs"):
                generator.generate(self.root / "artifacts/refused-combined", **inputs)
        self.assertFalse((self.root / "artifacts/refused-combined").exists())

    def test_combined_source_rechecks_selected_contract_and_both_bundle_inventories(self):
        inputs, _, _, verifier = self.metadata_inputs(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        selected = self.root / "selected-source.json"
        raw = (ROOT / generator.TARGET_FILES_SOURCE_CONTRACT).read_bytes()
        selected.write_bytes(raw)
        inputs["target_files_source_contract"] = selected
        validate = generator.validate
        def change_selected(*args, **kwargs):
            result = validate(*args, **kwargs)
            selected.write_bytes(raw + b"\n")
            return result
        with mock.patch.object(generator, "validate", side_effect=change_selected), self.assertRaises(generator.CandidateError):
            generator.generate(self.root / "artifacts/refused-combined", **inputs)
        self.assertFalse((self.root / "artifacts/refused-combined").exists())
        selected.write_bytes(raw)
        reader = verifier.return_value[2]
        reader.recheck.reset_mock()
        late_metadata = inputs["target_files_metadata_receipt"].parent / "unexpected-file"
        def add_metadata():
            if reader.recheck.call_count == 2:
                late_metadata.write_bytes(b"unlisted")
        reader.recheck.side_effect = add_metadata
        with self.assertRaises(generator.CandidateError):
            generator.generate(self.root / "artifacts/refused-combined", **inputs)
        late_metadata.unlink()
        reader.recheck.side_effect = None
        mi_verifier = generator._verify_mi_ext_inputs
        mi_verifier.reset_mock()
        binding = mi_verifier.return_value
        def add_mi(*args, **kwargs):
            if mi_verifier.call_count == 2:
                (inputs["mi_ext_inputs_receipt"].parent / "unexpected-directory").mkdir()
            return binding
        mi_verifier.side_effect = add_mi
        with self.assertRaisesRegex(generator.CandidateError, "mi_ext inventory refused"):
            generator.generate(self.root / "artifacts/refused-combined", **inputs)
        self.assertFalse((self.root / "artifacts/refused-combined").exists())

    def test_combined_source_candidate_cannot_be_nested_in_either_private_bundle(self):
        inputs, _, _, _ = self.metadata_inputs(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        for key in ("target_files_metadata_receipt", "mi_ext_inputs_receipt"):
            path = inputs[key]
            if not path.is_relative_to(self.root / "artifacts"):
                new = self.root / "artifacts/combined-mi-ext"
                path.parent.rename(new)
                inputs[key] = new / path.name
            output = inputs[key].parent / "nested-candidate"
            with self.subTest(bundle=key), self.assertRaisesRegex(generator.CandidateError, "nested inside"):
                generator.generate(output, **inputs)
            self.assertFalse(output.exists())

    def test_combined_source_portable_validation_does_not_reopen_private_bundles(self):
        inputs, _, _, _ = self.metadata_inputs(source_contract=ROOT / generator.TARGET_FILES_SOURCE_CONTRACT)
        output = self.root / "artifacts/portable-combined"
        plan = generator.generate(output, **inputs)
        inputs["target_files_metadata_receipt"].unlink()
        inputs["mi_ext_inputs_receipt"].unlink()
        with mock.patch.object(generator, "_verify_target_files_metadata", side_effect=AssertionError("private metadata read")), \
                mock.patch.object(generator, "_verify_mi_ext_inputs", side_effect=AssertionError("private image read")):
            self.assertEqual(generator.validate(output), plan)

    def test_combined_source_cli_argument_is_optional_and_explicit(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--target-files-source-contract", "source.json"], Path("source.json"))):
            with self.subTest(args=args), mock.patch.object(generator, "generate", return_value={}) as generate, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["target_files_source_contract"], expected)

    def test_factory_generation_binds_geometry_and_preserves_flags_and_provenance(self):
        inputs = self.factory_inputs()
        output = self.root / "artifacts/factory-candidate"
        plan = generator.generate(output, variant="user", **inputs)
        self.assertEqual(generator.validate(output), plan)
        self.assertEqual(plan["image_budgets"]["dtbo"]["bytes"], 33554432)
        self.assertIn("GPT", plan["image_budgets"]["dtbo"]["basis"])
        self.assertTrue(plan["factory_profile"]["kernel_dtb_dtbo_bootconfig_bytes_match"])
        self.assertFalse(plan["factory_profile"]["kernel_bundle_provenance_relabelled"])
        self.assertTrue(plan["mixed_package_sources"])
        self.assertFalse(plan["admission"]["physical_partition_fit_verified"])
        self.assertFalse(plan["admission"]["flash_allowed"])
        self.assertFalse(plan["avb_policy"]["source_image_set_verified"])
        fstab = (output / generator.DEVICE_PATH / "generated/fstab.qcom").read_text()
        self.assertIn("# Synthetic license notice retained", fstab)
        self.assertIn("avb_keys=/avb/test-only-fixture.avbpubkey", fstab)
        self.assertIn(DATA_ROW, fstab)
        self.assertIn(METADATA_ROW, fstab)
        self.assertNotIn("lowerdir=", fstab)
        self.assertEqual(len(plan["fstab"]["factory_boot_verification_rows"]), 5)
        self.assertTrue(plan["fstab"]["factory_logical_flags_preserved"])
        self.assertIn("/devices/platform/test-usb/*.controller /storage/test", fstab)
        self.assertEqual(plan["fstab"]["device_node_globs_preserved"], 1)
        self.assertFalse(plan["fstab"]["device_node_globs_expanded"])
        board = (output / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        self.assertIn("BOARD_DTBOIMG_PARTITION_SIZE := 33554432", board)
        with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
            generator.validate(output, purpose="target-files")

    def test_factory_generation_requires_all_three_explicit_inputs(self):
        inputs = self.factory_inputs()
        for missing in ("factory_boot_contract", "partition_metadata", "fstab_source"):
            with self.subTest(missing=missing):
                invalid = dict(inputs, **{missing: None})
                with self.assertRaisesRegex(generator.CandidateError, "requires boot contract"):
                    generator.generate(self.root / "artifacts/refused", **invalid)

    def test_factory_rejects_other_package_origin_or_component_claims(self):
        inputs = self.factory_inputs()
        path = inputs["factory_boot_contract"]
        original = json.loads(path.read_text())
        mutations = [
            lambda r: r["device"].update(codename="popsicle"),
            lambda r: r["device"].update(hardware_region="GLOBAL"),
            lambda r: r["packages"]["factory"].update(sha256="4" * 64),
            lambda r: r["packages"]["factory"].update(origin_verified=True),
            lambda r: r["packages"]["xiaomi_eu"].update(sha256="5" * 64),
            lambda r: r["header_component_readback"]["components"][0].update(factory_sha256="6" * 64),
            lambda r: r["vendor_bootconfig"]["declarations"].update(**{"androidboot.hardware": "other"}),
            lambda r: r["normal_vendor_fstab"].update(factory_sha256="7" * 64),
        ]
        for index, change in enumerate(mutations):
            with self.subTest(index=index):
                record = copy.deepcopy(original)
                change(record)
                path.write_text(json.dumps(record))
                with self.assertRaises(generator.CandidateError):
                    generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_factory_rejects_budget_changes_not_present_in_gpt(self):
        inputs = self.factory_inputs()
        path = inputs["partition_metadata"]
        original = json.loads(path.read_text())
        for change in (
            lambda r: r["build_relevant_sizes"][0].update(package_extent_bytes=4096),
            lambda r: r["build_relevant_sizes"][0].update(labels=["boot_b", "boot_a"]),
            lambda r: r["build_relevant_sizes"][0].update(stored_image_bytes=2 ** 40),
            lambda r: r["build_relevant_sizes"][0].update(stored_image_bytes=True),
            lambda r: r["build_relevant_sizes"].append(copy.deepcopy(r["build_relevant_sizes"][0])),
        ):
            record = copy.deepcopy(original)
            change(record)
            path.write_text(json.dumps(record))
            with self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_factory_receipt_tampering_is_rejected_before_publication(self):
        inputs = self.factory_inputs()
        record = json.loads(inputs["partition_metadata"].read_text())
        path = self.root / record["inspection"]["analysis"]["path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(generator.CandidateError, "reference hash/size mismatch"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_factory_stored_length_must_match_the_bound_image_readback(self):
        inputs = self.factory_inputs()
        path = inputs["partition_metadata"]
        record = json.loads(path.read_text())
        record["build_relevant_sizes"][0]["stored_image_bytes"] = 1
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(generator.CandidateError, "stored-image summary differs"):
            generator.generate(self.root / "artifacts/refused", **inputs)

    def test_factory_dtbo_cannot_be_substituted_through_bundle_and_summary(self):
        inputs = self.factory_inputs()
        path = inputs["kernel_receipt"]
        kernel = json.loads(path.read_text())
        data = b"another synthetic overlay"
        (path.parent / kernel["roles"]["dtbo"]).write_bytes(data)
        item = next(f for f in kernel["files"] if f["path"] == kernel["roles"]["dtbo"])
        item.update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
        path.write_text(json.dumps(kernel))
        path = inputs["partition_metadata"]
        record = json.loads(path.read_text())
        budget = next(b for b in record["build_relevant_sizes"] if b["name"] == "dtbo")
        budget.update(stored_image_sha256=item["sha256"], stored_image_bytes=len(data))
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(generator.CandidateError, "stored-image summary differs"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_factory_image_readback_must_agree_in_both_copies(self):
        inputs = self.factory_inputs()
        factory_path = inputs["factory_boot_contract"]
        factory = json.loads(factory_path.read_text())
        ref = factory["image_readback"]["receipt"]
        path = self.root / ref["path"]
        record = json.loads(path.read_bytes())
        record["images"][0]["user_extracted_image"]["sha256"] = "b" * 64
        raw = json.dumps(record).encode()
        path.write_bytes(raw)
        ref.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        factory_path.write_text(json.dumps(factory))
        with self.assertRaisesRegex(generator.CandidateError, "image copy hash/size/identity mismatch"):
            generator.generate(self.root / "artifacts/refused", **inputs)

    def test_factory_fstab_keeps_all_original_flags_or_refuses_the_input(self):
        inputs = self.factory_inputs()
        contract = json.loads(inputs["factory_boot_contract"].read_text())["normal_vendor_fstab"]
        path = inputs["fstab_source"]
        original = path.read_text()
        for changed in (
            original.replace("avb=vbmeta_system,", "", 1),
            original.replace("avb=vbmeta_system", "avb=vbmeta", 1),
            original.replace("avb=vbmeta_system", "avb=vbmeta_system,avb=other", 1),
            original.replace("slotselect,avb=vbmeta,first_stage_mount", "slotselect,first_stage_mount", 1),
            original.replace("aes-256-xts:wrappedkey_v0", "aes-256-xts", 1),
            original.replace(DATA_ROW, DATA_ROW + "\n" + DATA_ROW),
            original.replace("/devices/platform/test-usb/*.controller", "/dev/block/*.controller"),
            original.replace("voldmanaged=fixture:auto", "notmanaged=fixture:auto"),
            original.replace("/devices/platform/test-usb/*.controller", "/devices/$(touch-other)"),
        ):
            raw = changed.encode()
            path.write_bytes(raw)
            expected = dict(contract, factory_sha256=hashlib.sha256(raw).hexdigest(), factory_size_bytes=len(raw))
            with self.assertRaises(generator.CandidateError):
                generator.render_factory_fstab(self.plan(), expected, path)

    def test_factory_fstab_requires_its_exact_hash(self):
        inputs = self.factory_inputs()
        contract = json.loads(inputs["factory_boot_contract"].read_text())["normal_vendor_fstab"]
        inputs["fstab_source"].write_text("# not the admitted file\n")
        with self.assertRaisesRegex(generator.CandidateError, "fstab hash/size mismatch"):
            generator.render_factory_fstab(self.plan(), contract, inputs["fstab_source"])

    def trust_synthetic_dsp_contract(self, inputs, record):
        """A test-only trust root; the CLI cannot override the reviewed digest."""
        raw = (json.dumps(record, sort_keys=True) + "\n").encode()
        inputs["dsp_policy_contract"].write_bytes(raw)
        patcher = mock.patch.object(generator, "DSP_POLICY_CONTRACT_SHA256", hashlib.sha256(raw).hexdigest())
        patcher.start()
        self.addCleanup(patcher.stop)

    def dsp_inputs(self):
        """Tiny synthetic receipt graph, not firmware or a compiler result."""
        inputs = self.factory_inputs()
        record = json.loads((ROOT / generator.DSP_POLICY_RECORD).read_text())
        contract = record["generator_contract"]
        contract["factory_package_sha256"] = "3" * 64
        layout = json.loads(inputs["record_paths"]["firmware-layout"].read_text())
        partitions = {part["name"]: part for part in layout["partitions"]}
        contract["vendor_images"] = {
            name: {"sha256": partitions[name + "_a"]["extraction"]["sha256"],
                   "size_bytes": partitions[name + "_a"]["size_bytes"]}
            for name in ("vendor", "odm")
        }
        fixture_root = self.root / "artifacts/dsp-fixture"

        def write(name, data):
            path = fixture_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {"path": path.relative_to(self.root).as_posix(),
                    "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

        def reference(name, value):
            return write(name, (json.dumps(dict(schema_version=1, **value)) + "\n").encode())

        contract["policy_inputs"] = [
            {"runtime_path": row["runtime_path"],
             **write(f"policy/{i}.cil", f"; synthetic policy data {i}\n".encode())}
            for i, row in enumerate(contract["policy_inputs"])
        ]
        contract["policy_capture_receipt"] = reference("policy-capture.json", {
            "parent_package_sha256": "3" * 64, "origin_verified": False,
            "input_order": copy.deepcopy(contract["policy_inputs"]),
        })
        contract["source_ownership_receipt"] = reference("ownership.json", {"fixture_only": True})
        fixture = {
            "proof_completed": True, "errors": [], "guard_errors": [],
            "complete_assertion_multiset_equal": True, "complete_assertion_count": 6366,
            "corresponding_dsp_failure_removed": True, "all_four_other_diagnostics_preserved": True,
            "baseline_diagnostics": [{"synthetic": True}] * 5,
            "candidate_diagnostics": [{"synthetic": True}] * 4,
        }
        fixture.update({key: False for key in (
            "neverallow_checks_disabled", "original_assertions_removed", "new_allow_statements_added",
            "fresh_soong_or_m4_build_performed", "strict_compilation_passed", "android_source_or_out_written",
            "user_out_accessed", "phone_accessed", "firmware_executed",
        )})
        contract["fixture_receipt"] = reference("fixture.json", fixture)
        outputs = []
        for i in range(77):
            row = write(f"readback/{i:03d}", f"synthetic output {i}\n".encode())
            row["host_path"] = row.pop("path")
            outputs.append(row)
        contract["readback_receipt"] = reference("readback.json", {
            "receipt_sha256": contract["fixture_receipt"]["sha256"], "guest_writes": False,
            "files": outputs, "total_bytes": sum(row["size_bytes"] for row in outputs),
        })
        templates = self.root / "dsp-templates"
        for name in (*generator.TEMPLATE_FILES, *generator.DSP_POLICY_FILES):
            path = templates / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / generator.DEVICE_PATH / name).read_bytes())
        inputs.update(template_root=templates, dsp_policy_contract=self.root / "dsp-contract.json")
        self.trust_synthetic_dsp_contract(inputs, record)
        return inputs

    def change_dsp_bound_record(self, inputs, key, change):
        contract = json.loads(inputs["dsp_policy_contract"].read_text())
        reference = contract["generator_contract"][key]
        path = self.root / reference["path"]
        record = json.loads(path.read_text())
        change(record)
        raw = (json.dumps(record) + "\n").encode()
        path.write_bytes(raw)
        reference.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        self.trust_synthetic_dsp_contract(inputs, contract)

    def test_dsp_source_integration_is_explicit_and_deterministic_for_both_variants(self):
        inputs = self.dsp_inputs()
        for variant in ("user", "userdebug"):
            with self.subTest(variant=variant):
                first, second = [self.root / f"artifacts/dsp-{variant}-{number}" for number in (1, 2)]
                plan = generator.generate(first, variant=variant, **inputs)
                self.assertEqual(generator.generate(second, variant=variant, **inputs), plan)
                self.assertEqual(generator.validate(first), plan)
                expected = {(generator.DEVICE_PATH / name).as_posix() for name in generator.DSP_POLICY_FILES}
                expected.add(generator.DSP_POLICY_RECORD.as_posix())
                self.assertTrue(expected <= {row["path"] for row in plan["files"]})
                self.assertEqual(len(plan["files"]), len(generator.TEMPLATE_FILES) + 8)
                for key, value in (("factory_policy_inputs_rehashed", 3), ("fixture_readback_files_rehashed", 77),
                                   ("fixture_original_assertions_retained", 6366)):
                    self.assertEqual(plan["dsp_policy"][key], value)
                self.assertFalse(plan["dsp_policy"]["fresh_soong_or_m4_build_performed"])
                self.assertFalse(plan["dsp_policy"]["strict_full_policy_compiled"])
                self.assertFalse(plan["admission"]["flash_allowed"])
                board = (first / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
                for key, path in generator.DSP_POLICY_WIRING.items():
                    self.assertEqual(board.count(f"{key} += {path}\n"), 1)
                for purpose in ("target-files", "flash"):
                    with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                        generator.validate(first, purpose=purpose)

    def test_dsp_legacy_generation_never_requires_or_includes_the_new_contract(self):
        inputs = self.generation_inputs()
        with mock.patch.object(generator, "_bind_dsp_policy", side_effect=AssertionError("unexpected DSP opt-in")):
            output = self.root / "artifacts/legacy"
            plan = generator.generate(output, **inputs)
        self.assertNotIn("dsp_policy", plan)
        self.assertEqual(len(plan["files"]), len(generator.TEMPLATE_FILES) + 5)
        for name in generator.DSP_POLICY_FILES:
            self.assertNotIn(name, generator.TEMPLATE_FILES)
        with mock.patch.object(generator, "_dsp_contract", side_effect=AssertionError("legacy validator read DSP data")):
            self.assertEqual(generator.validate(output), plan)
        board = (output / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        for key in generator.DSP_POLICY_WIRING:
            self.assertNotIn(key, board)

    def test_dsp_opt_in_does_not_change_the_existing_factory_profile(self):
        inputs = self.dsp_inputs()
        legacy_inputs = {key: value for key, value in inputs.items() if key != "dsp_policy_contract"}
        legacy_path, new_path = self.root / "artifacts/v8-shape", self.root / "artifacts/dsp-enabled"
        legacy = generator.generate(legacy_path, **legacy_inputs)
        new = generator.generate(new_path, **inputs)
        self.assertEqual({k: v for k, v in legacy.items() if k != "files"},
                         {k: v for k, v in new.items() if k not in {"files", "dsp_policy"}})
        for row in legacy["files"]:
            if not row["path"].endswith("generated/BoardConfigCandidate.mk"):
                self.assertEqual((legacy_path / row["path"]).read_bytes(), (new_path / row["path"]).read_bytes())
        self.assertEqual(generator.validate(legacy_path), legacy)

    def test_dsp_requires_factory_profile_before_any_record_reads(self):
        with mock.patch.object(generator, "_load_records") as load:
            with self.assertRaisesRegex(generator.CandidateError, "explicit factory profile"):
                generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none",
                                   vendor_receipt="none", dsp_policy_contract="none")
            load.assert_not_called()

    def test_dsp_rejects_unknown_modified_or_symlink_contracts(self):
        inputs = self.dsp_inputs()
        path, original = inputs["dsp_policy_contract"], inputs["dsp_policy_contract"].read_bytes()
        for value in (original + b"\n", original.replace(b'nezha-dsp-membership-v1', b'nezha-dsp-membership-v2')):
            path.write_bytes(value)
            with self.assertRaisesRegex(generator.CandidateError, "unknown or changed DSP"):
                generator.generate(self.root / "artifacts/refused", **inputs)
        path.write_bytes(original)
        link = self.root / "dsp-link.json"
        link.symlink_to(path)
        with self.assertRaisesRegex(generator.CandidateError, "symlink refused"):
            generator.generate(self.root / "artifacts/refused", **dict(inputs, dsp_policy_contract=link))
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_dsp_contract_cannot_redirect_sources_wiring_package_or_images(self):
        inputs = self.dsp_inputs()
        baseline = json.loads(inputs["dsp_policy_contract"].read_text())
        changes = (
            lambda c: c.update(contract_id="unknown"),
            lambda c: c.update(profile="flash"),
            lambda c: c.update(factory_origin_verified=True),
            lambda c: c["source_files"][0].update(path="device/xiaomi/other/sepolicy/attributes"),
            lambda c: c["source_files"].append(copy.deepcopy(c["source_files"][0])),
            lambda c: c["wiring"].update(SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS="$(shell false)"),
            lambda c: c.update(factory_package_sha256="4" * 64),
            lambda c: c["vendor_images"]["vendor"].update(sha256="4" * 64),
            lambda c: c["vendor_images"]["odm"].update(size_bytes=1),
        )
        for change in changes:
            record = copy.deepcopy(baseline)
            change(record["generator_contract"])
            self.trust_synthetic_dsp_contract(inputs, record)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_dsp_rehashes_all_three_factory_policy_inputs(self):
        inputs = self.dsp_inputs()
        record = json.loads(inputs["dsp_policy_contract"].read_text())
        for row in record["generator_contract"]["policy_inputs"]:
            path = self.root / row["path"]
            original = path.read_bytes()
            path.write_bytes(original + b"; changed\n")
            with self.subTest(path=row["runtime_path"]), self.assertRaisesRegex(generator.CandidateError, "policy input hash/size mismatch"):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)

    def test_dsp_rehashes_first_and_last_readback_outputs(self):
        inputs = self.dsp_inputs()
        contract = json.loads(inputs["dsp_policy_contract"].read_text())["generator_contract"]
        readback = json.loads((self.root / contract["readback_receipt"]["path"]).read_text())
        for index in (0, 76):
            row = readback["files"][index]
            path = self.root / row["host_path"]
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(index=index), self.assertRaisesRegex(generator.CandidateError, "bundle file hash/size mismatch"):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)

    def test_dsp_never_accepts_changed_assertion_or_scope_results(self):
        inputs = self.dsp_inputs()
        baseline = json.loads(inputs["dsp_policy_contract"].read_text())
        reference = baseline["generator_contract"]["fixture_receipt"]
        original = (self.root / reference["path"]).read_bytes()
        changes = [lambda r: r.update(complete_assertion_count=6365),
                   lambda r: r.update(candidate_diagnostics=[{}] * 3),
                   lambda r: r.update(guard_errors=["changed input"])]
        changes.extend(lambda r, key=key: r.update({key: True}) for key in (
            "neverallow_checks_disabled", "original_assertions_removed", "new_allow_statements_added",
            "fresh_soong_or_m4_build_performed", "strict_compilation_passed", "android_source_or_out_written",
            "user_out_accessed", "phone_accessed", "firmware_executed",
        ))
        for change in changes:
            (self.root / reference["path"]).write_bytes(original)
            self.trust_synthetic_dsp_contract(inputs, baseline)
            self.change_dsp_bound_record(inputs, "fixture_receipt", change)
            with self.subTest(change=change), self.assertRaisesRegex(generator.CandidateError, "DSP.*fixture"):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_dsp_rejects_readback_count_total_or_receipt_substitution(self):
        inputs = self.dsp_inputs()
        baseline = json.loads(inputs["dsp_policy_contract"].read_text())
        reference = baseline["generator_contract"]["readback_receipt"]
        original = (self.root / reference["path"]).read_bytes()
        changes = (lambda r: r.update(receipt_sha256="4" * 64),
                   lambda r: r.update(guest_writes=True),
                   lambda r: r["files"].pop(),
                   lambda r: r.update(total_bytes=r["total_bytes"] + 1),
                   lambda r: r["files"].__setitem__(76, copy.deepcopy(r["files"][0])))
        for change in changes:
            (self.root / reference["path"]).write_bytes(original)
            self.trust_synthetic_dsp_contract(inputs, baseline)
            self.change_dsp_bound_record(inputs, "readback_receipt", change)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_dsp_source_tampering_is_rejected_before_publication(self):
        inputs = self.dsp_inputs()
        for name in generator.DSP_POLICY_FILES:
            path = inputs["template_root"] / name
            original = path.read_bytes()
            path.write_bytes(original + b"allow domain domain:process signal;\n")
            with self.subTest(name=name), self.assertRaisesRegex(generator.CandidateError, "DSP policy source file hash/size mismatch"):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_dsp_validation_uses_only_the_self_contained_candidate(self):
        inputs = self.dsp_inputs()
        output = self.root / "artifacts/dsp-standalone"
        plan = generator.generate(output, **inputs)
        with mock.patch.object(generator, "_bound_reference", side_effect=AssertionError("private evidence accessed")):
            self.assertEqual(generator.validate(output), plan)

    def trust_synthetic_helper_contract(self, inputs, contract):
        raw = (json.dumps(contract, sort_keys=True) + "\n").encode()
        inputs["init_helper_capability_contract"].write_bytes(raw)
        patcher = mock.patch.object(generator, "INIT_HELPER_CONTRACT_SHA256", hashlib.sha256(raw).hexdigest())
        patcher.start()
        self.addCleanup(patcher.stop)

    def helper_inputs(self):
        """Tiny private-input substitutes; never read real captured firmware."""
        inputs = self.dsp_inputs()
        contract = json.loads((ROOT / generator.INIT_HELPER_RECORD).read_text())
        dsp = json.loads(inputs["dsp_policy_contract"].read_text())["generator_contract"]
        contract["factory_package_sha256"] = dsp["factory_package_sha256"]
        contract["vendor_images"] = dsp["vendor_images"]

        def write(name, data):
            path = self.root / "artifacts/helper-fixture" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {"path": path.relative_to(self.root).as_posix(),
                    "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

        for index, row in enumerate(contract["source_captures"]):
            row.update(write(f"source/{index}", f"synthetic source {index}\n".encode()))
        scan = {"schema_version": 1, "factory_package_sha256": dsp["factory_package_sha256"],
                "factory_origin_authenticated": False, "partitions": []}
        for name in ("vendor", "odm"):
            files = []
            for index in range(2):
                row = write(f"{name}/{index}", f"# selected {name} source {index}\n".encode())
                row["host_path"] = row.pop("path")
                row["image_path"] = f"/etc/init/fixture{index}.rc"
                files.append(row)
            scan["partitions"].append({"partition": name, "files": files, "file_count": len(files),
                                       "total_bytes": sum(row["size_bytes"] for row in files),
                                       "image_sha256": dsp["vendor_images"][name]["sha256"]})
        contract["static_input_scan"] = write("scan.json", (json.dumps(scan) + "\n").encode())
        contract["static_input_file_count"] = 4
        contract["static_input_total_bytes"] = sum(row["total_bytes"] for row in scan["partitions"])
        audit = {
            "schema_version": 1,
            "source_pins": contract["required_source_revisions"],
            "selected_factory_evidence": {"factory_package_sha256": dsp["factory_package_sha256"]},
            "selected_init_rc": {"upstream_optional_service_preserved": True},
            "validation": {"final_init_hook_bytes_and_text_identity_passed": True,
                           "selected_init_rc_identity_passed": True},
            "proposed_capability": {"complete_rom_admission": False},
        }
        raw = (json.dumps(audit) + "\n").encode()
        (self.root / generator.INIT_HELPER_AUDIT).write_bytes(raw)
        contract["prior_component_audit"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        inputs["init_helper_capability_contract"] = self.root / "helper-contract.json"
        self.trust_synthetic_helper_contract(inputs, contract)
        return inputs

    def reseal_candidate_file(self, output, plan, name, raw):
        (output / name).write_bytes(raw)
        updated = copy.deepcopy(plan)
        next(row for row in updated["files"] if row["path"] == name).update(
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        (output / "admission.json").write_text(json.dumps(updated))

    def test_helper_public_contract_and_guard_files_have_the_pinned_identity(self):
        contract, identity = generator._init_helper_contract(ROOT / generator.INIT_HELPER_RECORD)
        self.assertEqual(identity["sha256"], generator.INIT_HELPER_CONTRACT_SHA256)
        for row in [*contract["device_guards"], contract["source_patch"], contract["patch_metadata"],
                    contract["prior_component_audit"]]:
            raw = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
            self.assertEqual(len(raw), row["size_bytes"])
        self.assertFalse(contract["limits"]["runtime_helper_absence_verified"])

    def test_helper_source_option_is_explicit_and_deterministic_for_both_variants(self):
        inputs = self.helper_inputs()
        for variant in generator.BUILD_VARIANTS:
            output = self.root / "artifacts" / ("helper-" + variant)
            plan = generator.generate(output, variant=variant, **inputs)
            repeat = generator.generate(self.root / "artifacts" / ("helper-repeat-" + variant),
                                        variant=variant, **inputs)
            self.assertEqual(plan, repeat)
            self.assertEqual(generator.validate(output), plan)
            self.assertEqual(plan["init_helper_capability"]["capability"], generator.INIT_HELPER_CAPABILITY)
            self.assertEqual(plan["init_helper_capability"]["static_factory_files_rehashed"], 4)
            self.assertFalse(plan["init_helper_capability"]["fresh_soong_or_m4_build_performed"])
            self.assertFalse(plan["init_helper_capability"]["strict_full_policy_compiled"])
            self.assertEqual(len(plan["files"]), len(generator.TEMPLATE_FILES) + 12)
            board = (output / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
            self.assertEqual(board.count("BOARD_SEPOLICY_M4DEFS += target_init_dev_config_property_writes=false\n"), 1)
            for purpose in ("target-files", "flash"):
                with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                    generator.validate(output, purpose=purpose)

    def test_helper_legacy_profile_leaves_upstream_value_undefined(self):
        inputs = self.dsp_inputs()
        with mock.patch.object(generator, "_init_helper_contract", side_effect=AssertionError("implicit helper opt-in")):
            output = self.root / "artifacts/helper-undefined"
            plan = generator.generate(output, **inputs)
            self.assertEqual(generator.validate(output), plan)
        self.assertNotIn("init_helper_capability", plan)
        board = (output / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        self.assertNotIn(generator.INIT_HELPER_SYMBOL, board)

    def test_helper_option_requires_factory_and_dsp_before_any_record_reads(self):
        with mock.patch.object(generator, "_load_records") as records:
            with self.assertRaisesRegex(generator.CandidateError, "explicit factory and DSP"):
                generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none",
                                   vendor_receipt="none", init_helper_capability_contract="none")
            records.assert_not_called()

    def test_helper_contract_refuses_changed_values_inputs_scope_and_guards(self):
        inputs = self.helper_inputs()
        original = json.loads(inputs["init_helper_capability_contract"].read_text())
        changes = (
            lambda c: c["capability"].update(value="true"),
            lambda c: c["capability"].update(value=False),
            lambda c: c["capability"].update(api_version_inference_used=True),
            lambda c: c.update(provider_contract={"path": "/vendor/bin/unreviewed"}),
            lambda c: c["limits"].update(complete_installed_input_closure_verified=True),
            lambda c: c.update(factory_package_sha256="4" * 64),
            lambda c: c.update(factory_origin_verified=True),
            lambda c: c["vendor_images"]["vendor"].update(sha256="4" * 64),
            lambda c: c["required_source_revisions"].update({"system/sepolicy": "4" * 40}),
            lambda c: c["required_patched_source"].update(sha256="4" * 64),
            lambda c: c["device_guards"].append(copy.deepcopy(c["device_guards"][0])),
        )
        for change in changes:
            contract = copy.deepcopy(original)
            change(contract)
            self.trust_synthetic_helper_contract(inputs, contract)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_helper_contract_requires_exact_bytes_and_no_symlinks(self):
        inputs = self.helper_inputs()
        path = inputs["init_helper_capability_contract"]
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with self.assertRaisesRegex(generator.CandidateError, "unknown or changed init-helper"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        path.write_bytes(original)
        link = self.root / "helper-link.json"
        link.symlink_to(path)
        with self.assertRaisesRegex(generator.CandidateError, "symlink"):
            generator.generate(self.root / "artifacts/refused", **dict(inputs, init_helper_capability_contract=link))

    def test_helper_rehashes_factory_files_and_captured_sources(self):
        inputs = self.helper_inputs()
        contract = json.loads(inputs["init_helper_capability_contract"].read_text())
        scan = json.loads((self.root / contract["static_input_scan"]["path"]).read_text())
        names = [row["path"] for row in contract["source_captures"]]
        names += [row["host_path"] for part in scan["partitions"] for row in part["files"]]
        for name in names:
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b"# changed\n")
            with self.subTest(name=name), self.assertRaisesRegex(generator.CandidateError, "hash/size mismatch"):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)

    def test_helper_static_scan_rejects_new_provider_labels_and_invocations_even_if_resealed(self):
        inputs = self.helper_inputs()
        original = json.loads(inputs["init_helper_capability_contract"].read_text())
        scan_path = self.root / original["static_input_scan"]["path"]
        baseline_scan = json.loads(scan_path.read_text())
        for text in ("ro.vendor.init_dev_config.path=/vendor/bin/helper\n",
                     "ro.vendor.init_dev_config.path=${unresolved.selector}\n",
                     "/vendor/bin/helper u:object_r:init_dev_config_exec:s0\n",
                     "exec_start init_dev_config\n", "ro.boot.init_rc=/vendor/etc/alternate.rc\n"):
            scan = copy.deepcopy(baseline_scan)
            row = scan["partitions"][0]["files"][0]
            raw = text.encode()
            (self.root / row["host_path"]).write_bytes(raw)
            old_size = row["size_bytes"]
            row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
            scan["partitions"][0]["total_bytes"] += len(raw) - old_size
            scan_raw = (json.dumps(scan) + "\n").encode()
            scan_path.write_bytes(scan_raw)
            contract = copy.deepcopy(original)
            contract["static_input_scan"].update(sha256=hashlib.sha256(scan_raw).hexdigest(), size_bytes=len(scan_raw))
            contract["static_input_total_bytes"] += len(raw) - old_size
            self.trust_synthetic_helper_contract(inputs, contract)
            with self.subTest(text=text), self.assertRaisesRegex(generator.CandidateError, "uncontracted init-helper"):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_helper_device_sources_reject_providers_and_guard_changes(self):
        inputs = self.helper_inputs()
        for name, addition in (("device.mk", b"PRODUCT_VENDOR_PROPERTIES += ro.vendor.init_dev_config.path=/vendor/bin/helper\n"),
                               ("recovery/root/init.recovery.qcom.rc", b"exec_start init_dev_config\n"),
                               ("init-helper-capability.mk", b"BOARD_SEPOLICY_M4DEFS += target_init_dev_config_property_writes=true\n")):
            path = inputs["template_root"] / name
            original = path.read_bytes()
            path.write_bytes(original + addition)
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)

    def test_helper_vendor_soong_provider_is_rejected_even_with_resealed_bundle(self):
        inputs = self.helper_inputs()
        receipt = inputs["vendor_receipt"]
        vendor = json.loads(receipt.read_text())
        raw = b'cc_prebuilt_binary { name: "init_dev_config", srcs: ["helper"] }\n'
        (receipt.parent / "Android.bp").write_bytes(raw)
        vendor["generated_files"].append({"path": "Android.bp", "size_bytes": len(raw),
                                          "sha256": hashlib.sha256(raw).hexdigest(), "readback_verified": True})
        receipt.write_text(json.dumps(vendor))
        with self.assertRaisesRegex(generator.CandidateError, "uncontracted init-helper"):
            generator.generate(self.root / "artifacts/refused", **inputs)

    def test_helper_validation_rejects_duplicate_or_commented_wiring_after_inventory_rehash(self):
        inputs = self.helper_inputs()
        output = self.root / "artifacts/helper-wiring"
        plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix()
        original = (output / name).read_bytes()
        directive = b"BOARD_SEPOLICY_M4DEFS += target_init_dev_config_property_writes=false\n"
        changes = (original.replace(directive, b"# " + directive),
                   original.replace(directive, directive + directive),
                   original.replace(directive, directive.replace(b"=false", b"=true")),
                   original.replace(directive, directive + b"# " + generator.INIT_HELPER_SYMBOL.encode() + b"\n"),
                   original.replace(generator._init_helper_wiring_lines()[0].encode() + b"\n",
                                    generator._init_helper_wiring_lines()[0].encode() + b" \\\n"))
        for raw in changes:
            self.reseal_candidate_file(output, plan, name, raw)
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaisesRegex(generator.CandidateError, "init-helper board wiring"):
                generator.validate(output)

    def test_helper_validation_rejects_public_guard_and_receipt_promotion(self):
        inputs = self.helper_inputs()
        output = self.root / "artifacts/helper-guards"
        plan = generator.generate(output, **inputs)
        for name in ("BoardConfig.mk", "init-helper-capability.mk"):
            relative = (generator.DEVICE_PATH / name).as_posix()
            original = (output / relative).read_bytes()
            self.reseal_candidate_file(output, plan, relative, original + b"# unreviewed guard changes\n")
            with self.assertRaisesRegex(generator.CandidateError, "init-helper public input"):
                generator.validate(output)
            (output / relative).write_bytes(original)
        updated = copy.deepcopy(plan)
        updated["init_helper_capability"]["strict_full_policy_compiled"] = True
        (output / "admission.json").write_text(json.dumps(updated))
        with self.assertRaisesRegex(generator.CandidateError, "init-helper admission"):
            generator.validate(output)

    def test_helper_validation_never_reads_private_evidence_or_reports_new_builds(self):
        inputs = self.helper_inputs()
        output = self.root / "artifacts/helper-self-contained"
        plan = generator.generate(output, **inputs)
        with mock.patch.object(generator, "_bound_reference", side_effect=AssertionError("private input read")):
            self.assertEqual(generator.validate(output), plan)
        self.assertFalse(plan["init_helper_capability"]["source_checkout_inspected"])

    def test_cli_passes_optional_helper_contract_without_enabling_it_by_default(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--init-helper-capability-contract", "helper.json"], Path("helper.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["init_helper_capability_contract"], expected)

    def policy_bundle_inputs(self):
        """Mock only the separate bundle verifier; its real tests own that trust boundary."""
        from scripts import policy_inputs
        inputs = self.helper_inputs()
        receipt = self.root / "policy-bundle" / generator.POLICY_INPUTS_RECEIPT
        receipt.parent.mkdir()
        raw = b'{"schema_version":1,"synthetic":true}\n'
        receipt.write_bytes(raw)
        inputs["policy_inputs_receipt"] = receipt
        verification = {
            "schema_version": 1, "operation": "verify-nezha-policy-inputs", "status": "verified",
            "device": "nezha", "bundle": generator.POLICY_INPUTS_PATH,
            "factory_package_sha256": "3" * 64,
            "files": [{"path": "Android.bp", "sha256": "4" * 64, "size_bytes": 10}],
            "receipt": {"path": receipt.name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "scope": copy.deepcopy(policy_inputs.SCOPE),
        }
        return inputs, verification

    def test_policy_bundle_export_is_separate_explicit_and_generation_verified(self):
        inputs, verification = self.policy_bundle_inputs()
        output = self.root / "artifacts/helper-native"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification) as verify:
            plan = generator.generate(output, **inputs)
        verify.assert_called_once_with(inputs["policy_inputs_receipt"])
        self.assertEqual(plan["policy_inputs"], verification)
        self.assertFalse(plan["policy_inputs"]["scope"]["policy_compiled"])
        self.assertFalse(plan["admission"]["complete_target_files_allowed"])
        product = (output / generator.DEVICE_PATH / "generated/device-candidate.mk").read_text()
        self.assertEqual(product.count("PRODUCT_SOONG_NAMESPACES += vendor/xiaomi/nezha-policy\n"), 1)
        with mock.patch.object(generator, "_verify_policy_input_bundle", side_effect=AssertionError("external bundle rehashed")):
            self.assertEqual(generator.validate(output), plan)
        default = generator.generate(self.root / "artifacts/helper-no-native",
                                     **{key: value for key, value in inputs.items() if key != "policy_inputs_receipt"})
        self.assertNotIn("policy_inputs", default)
        product = (self.root / "artifacts/helper-no-native" / generator.DEVICE_PATH / "generated/device-candidate.mk").read_text()
        self.assertNotIn(generator.POLICY_INPUTS_PATH, product)

    def test_policy_bundle_requires_helper_and_dsp_before_reading_inputs(self):
        with mock.patch.object(generator, "_load_records") as records:
            with self.assertRaisesRegex(generator.CandidateError, "explicit helper and DSP"):
                generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none",
                                   vendor_receipt="none", policy_inputs_receipt="none")
            records.assert_not_called()

    def test_policy_bundle_refuses_wrong_package_scope_namespace_or_receipt(self):
        inputs, original = self.policy_bundle_inputs()
        for change in (
            lambda r: r.update(factory_package_sha256="4" * 64),
            lambda r: r.update(bundle="vendor/xiaomi/other-policy"),
            lambda r: r.update(status="not-verified"),
            lambda r: r["scope"].update(policy_compiled=True),
            lambda r: r["scope"].update(complete_rom_admitted=True),
            lambda r: r["receipt"].update(sha256="4" * 64),
            lambda r: r["files"].append(copy.deepcopy(r["files"][0])),
        ):
            verification = copy.deepcopy(original)
            change(verification)
            with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification), \
                    self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_policy_bundle_cannot_export_namespace_without_receipt_or_change_it_after_generation(self):
        inputs, verification = self.policy_bundle_inputs()
        output = self.root / "artifacts/native-namespace"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "generated/device-candidate.mk").as_posix()
        original = (output / name).read_bytes()
        self.reseal_candidate_file(output, plan, name, original + b"PRODUCT_SOONG_NAMESPACES += vendor/xiaomi/nezha-policy\n")
        with self.assertRaisesRegex(generator.CandidateError, "namespace export changed"):
            generator.validate(output)
        (output / name).write_bytes(original)
        updated = copy.deepcopy(plan)
        del updated["policy_inputs"]
        (output / "admission.json").write_text(json.dumps(updated))
        with self.assertRaisesRegex(generator.CandidateError, "explicit verified bundle"):
            generator.validate(output)

    def test_cli_passes_policy_bundle_receipt_without_implicit_adoption(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--policy-inputs-receipt", "policy-inputs.json"], Path("policy-inputs.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["policy_inputs_receipt"], expected)

    def test_cli_passes_oem_source_contract_without_implicit_adoption(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--oem-policy-contract", "oem-policy.json"], Path("oem-policy.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["oem_policy_contract"], expected)

    def test_cli_passes_evolution_base_contract_without_implicit_adoption(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                "--output", "artifacts/out"]
        for args, expected in (([], None), (["--evolution-policy-base-contract", "evolution-base.json"], Path("evolution-base.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["evolution_policy_base_contract"], expected)

    def test_evolution_base_requires_user_and_complete_explicit_sources_before_reads(self):
        names = ("policy_inputs_receipt", "oem_policy_contract", "oem_property_contract",
                 "framework_provider_policy_contract", "framework_provider_inputs_receipt")
        selected = {name: "unused" for name in names}
        cases = [{**selected, "variant": "userdebug"}]
        cases.extend({**selected, "variant": "user", name: None} for name in names)
        for options in cases:
            with self.subTest(options=options), mock.patch.object(generator, "_load_records") as load, \
                    self.assertRaisesRegex(generator.CandidateError, "Evolution policy base requires explicit"):
                generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="unused",
                                   vendor_receipt="unused", evolution_policy_base_contract="unused", **options)
            load.assert_not_called()

    def test_oem_policy_requires_all_other_explicit_inputs_before_record_reads(self):
        with mock.patch.object(generator, "_load_records") as records:
            with self.assertRaisesRegex(generator.CandidateError, "OEM policy requires explicit"):
                generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none",
                                   vendor_receipt="none", oem_policy_contract="none")
            records.assert_not_called()
        inputs, _ = self.policy_bundle_inputs()
        del inputs["policy_inputs_receipt"]
        with mock.patch.object(generator, "_load_records") as records:
            with self.assertRaisesRegex(generator.CandidateError, "OEM policy requires explicit"):
                generator.generate(self.root / "artifacts/refused", oem_policy_contract="none", **inputs)
            records.assert_not_called()

    def test_legacy_helper_policy_generation_never_reads_or_includes_oem_sources(self):
        inputs, verification = self.policy_bundle_inputs()
        output = self.root / "artifacts/native-without-oem"
        with mock.patch.object(generator, "_oem_policy_contract", side_effect=AssertionError("implicit OEM policy")), \
                mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
            self.assertEqual(generator.validate(output), plan)
        self.assertNotIn("oem_policy", plan)
        self.assertNotIn(generator.OEM_POLICY_RECORD.as_posix(), {row["path"] for row in plan["files"]})
        board = (output / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        for path in generator.OEM_POLICY_WIRING.values():
            self.assertNotIn(path, board)
        for name in generator.OEM_POLICY_FILES:
            self.assertFalse((output / generator.DEVICE_PATH / name).exists())

    def test_oem_native_bundle_cannot_be_adopted_without_oem_source_capability(self):
        inputs, verification = self.policy_bundle_inputs()
        verification["oem_policy_contract"] = {
            "path": generator.OEM_POLICY_RECORD.as_posix(), "sha256": "4" * 64, "size_bytes": 100,
        }
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            with self.assertRaisesRegex(generator.CandidateError, "same reviewed contract"):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def trust_synthetic_oem_contract(self, inputs, contract, verification=None):
        raw = (json.dumps(contract, sort_keys=True) + "\n").encode()
        inputs["oem_policy_contract"].write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        patcher = mock.patch.object(generator, "OEM_POLICY_CONTRACT_SHA256", digest)
        patcher.start()
        self.addCleanup(patcher.stop)
        if verification is not None:
            verification["oem_policy_contract"] = {
                "path": generator.OEM_POLICY_RECORD.as_posix(), "sha256": digest, "size_bytes": len(raw),
            }

    def oem_inputs(self):
        """Synthetic private evidence, with only the authored public TE sources real."""
        inputs, verification = self.policy_bundle_inputs()
        contract = json.loads((ROOT / generator.OEM_POLICY_RECORD).read_text())
        dsp_record = json.loads(inputs["dsp_policy_contract"].read_text())
        dsp = dsp_record["generator_contract"]
        contract["factory_package_sha256"] = dsp["factory_package_sha256"]
        contract["unchanged_factory_inputs"] = [
            {key: row[key] for key in ("runtime_path", "sha256", "size_bytes")} for row in dsp["policy_inputs"]
        ]
        capture_path = self.root / dsp["policy_capture_receipt"]["path"]
        capture = json.loads(capture_path.read_text())
        for index, row in enumerate(contract["evidence"]["source_rows"]):
            path = self.root / "artifacts/oem-fixture" / (str(index) + ".cil")
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = f"; synthetic original factory framework input {index}\n".encode()
            path.write_bytes(raw)
            row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
            capture["input_order"].append({
                "path": path.relative_to(self.root).as_posix(),
                **{key: row[key] for key in ("runtime_path", "sha256", "size_bytes")},
            })
        raw = (json.dumps(capture) + "\n").encode()
        capture_path.write_bytes(raw)
        dsp["policy_capture_receipt"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        self.trust_synthetic_dsp_contract(inputs, dsp_record)
        triage_path = self.root / contract["evidence"]["triage"]["path"]
        triage_path.parent.mkdir(parents=True, exist_ok=True)
        triage_raw = (json.dumps({"schema_version": 1, "all_inputs_rehashed_unchanged": True,
                                 "compiler_invoked": False, "oem_te_source_recovered": False,
                                 "source_or_guest_mutated": False}) + "\n").encode()
        triage_path.write_bytes(triage_raw)
        contract["evidence"]["triage"].update(sha256=hashlib.sha256(triage_raw).hexdigest(), size_bytes=len(triage_raw))
        contract["required_capability_contract"]["sha256"] = hashlib.sha256(
            inputs["init_helper_capability_contract"].read_bytes()).hexdigest()
        for name in generator.OEM_POLICY_FILES:
            path = inputs["template_root"] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / generator.DEVICE_PATH / name).read_bytes())
        inputs["oem_policy_contract"] = self.root / "oem-policy-contract.json"
        self.trust_synthetic_oem_contract(inputs, contract, verification)
        return inputs, verification

    def test_oem_public_contract_pins_exact_authored_sources_and_ownership(self):
        contract, identity = generator._oem_policy_contract(ROOT / generator.OEM_POLICY_RECORD)
        self.assertEqual(identity["sha256"], generator.OEM_POLICY_CONTRACT_SHA256)
        self.assertEqual(contract["types"], generator.OEM_POLICY_TYPES)
        for row in contract["source_files"]:
            raw = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
            self.assertEqual(len(raw), row["size_bytes"])
        self.assertEqual(contract["types"]["offlinelog_file"]["mapping_members"], [])
        self.assertIsNone(contract["types"]["offlinelog_file"]["versioned_attribute"])

    def trust_synthetic_property_contract(self, inputs, contract, verification=None):
        raw = (json.dumps(contract, sort_keys=True) + "\n").encode()
        inputs["oem_property_contract"].write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        self.enterContext(mock.patch.object(generator, "OEM_PROPERTY_CONTRACT_SHA256", digest))
        if verification is not None:
            verification["oem_property_contract"] = {
                "path": generator.OEM_PROPERTY_RECORD.as_posix(), "sha256": digest, "size_bytes": len(raw),
            }

    def property_inputs(self):
        """Inert evidence receipts; real authored property source bytes and grammar."""
        inputs, verification = self.oem_inputs()
        base = json.loads(inputs["oem_policy_contract"].read_text())
        contract = json.loads((ROOT / generator.OEM_PROPERTY_RECORD).read_text())
        contract["base_oem_contract"] = copy.deepcopy(verification["oem_policy_contract"])
        for key in ("factory_package_sha256", "required_capability_contract", "unchanged_factory_inputs"):
            contract[key] = copy.deepcopy(base[key])
        for key in ("factory_system_ext_cil", "factory_system_ext_mapping"):
            row = next(row for row in base["evidence"]["source_rows"]
                       if row["runtime_path"] == contract["evidence"][key]["runtime_path"])
            contract["evidence"][key] = copy.deepcopy(row)
        dsp_record = json.loads(inputs["dsp_policy_contract"].read_text())
        capture_path = self.root / dsp_record["generator_contract"]["policy_capture_receipt"]["path"]
        capture = json.loads(capture_path.read_text())
        contexts = self.root / "artifacts/property-fixture/factory-property-contexts"
        contexts.parent.mkdir(parents=True)
        raw = b"# Synthetic original factory property-context evidence\n"
        contexts.write_bytes(raw)
        contract["evidence"]["factory_system_ext_property_contexts"].update(
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        capture.setdefault("files", []).append({
            "path": contexts.relative_to(self.root).as_posix(),
            **contract["evidence"]["factory_system_ext_property_contexts"],
        })
        raw = (json.dumps(capture) + "\n").encode()
        capture_path.write_bytes(raw)
        dsp_record["generator_contract"]["policy_capture_receipt"].update(
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        self.trust_synthetic_dsp_contract(inputs, dsp_record)

        def evidence(key, record):
            row = contract["evidence"][key]
            path = self.root / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (json.dumps({"schema_version": 1, **record}) + "\n").encode()
            path.write_bytes(raw)
            row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

        evidence("finite_impact_audit", {
            "all_inputs_rehashed_unchanged": True, "assertions": contract["finite_impact"]["assertions"],
            "native_compiler_invoked": False, "native_m4_invoked": False, "source_or_input_files_modified": False,
            "guest_accessed": False, "phone_accessed": False, "permissive_declarations_in_model": 0,
            "per_property": {name: {"effective_all_ordinary_allow_edges_after": budget}
                             for name, budget in contract["native_effective_ordinary_allow_edges"].items()},
        })
        evidence("finite_impact_readback", {
            "report": contract["evidence"]["finite_impact_audit"], "all_direct_inputs_unchanged": True,
            "all_ordinary_delta_group_encodings_and_digests_verified": True,
            "per_property_full_allow_sets_reproduced_from_global_additions": True,
            "guest_accessed": False, "native_compiler_invoked": False, "phone_accessed": False,
        })
        evidence("independent_finite_impact_review", {
            "reviewed_report": contract["evidence"]["finite_impact_audit"], "current_correctness_findings": [],
            "compiler_executed": False, "guest_accessed": False, "phone_accessed": False,
            "parent_files_modified": False, "tracked_files_modified": False,
        })
        for name in generator.OEM_PROPERTY_FILES:
            path = inputs["template_root"] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / generator.DEVICE_PATH / name).read_bytes())
        inputs["oem_property_contract"] = self.root / "property-contract.json"
        self.trust_synthetic_property_contract(inputs, contract, verification)
        return inputs, verification

    def test_property_public_contract_pins_four_sources_types_contexts_and_allow_budget(self):
        contract, identity = generator._oem_property_contract(ROOT / generator.OEM_PROPERTY_RECORD)
        self.assertEqual(identity["sha256"], generator.OEM_PROPERTY_CONTRACT_SHA256)
        self.assertEqual(contract["types"], generator.OEM_PROPERTY_TYPES)
        self.assertEqual(contract["native_effective_ordinary_allow_edges"], generator.OEM_PROPERTY_ALLOW_BUDGET)
        contents = {row["path"]: (ROOT / row["path"]).read_bytes() for row in contract["source_files"]}
        generator._verify_oem_property_sources(contents, contract)
        self.assertEqual(len(contents), 4)
        self.assertEqual(len(contract["property_contexts"]), 8)
        self.assertEqual(len(contract["read_clauses"]), 2)
        self.assertFalse(contract["limits"]["denial_logging_unchanged"])

    def test_property_contract_requires_explicit_oem_source_and_native_inputs_before_record_reads(self):
        with mock.patch.object(generator, "_load_records") as load, self.assertRaisesRegex(generator.CandidateError, "OEM properties require"):
            generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none", vendor_receipt="none",
                               oem_property_contract="none")
        load.assert_not_called()

    def test_property_sources_and_private_evidence_are_not_read_by_default(self):
        inputs, verification = self.oem_inputs()
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification), \
                mock.patch.object(generator, "_oem_property_contract", side_effect=AssertionError("implicit property read")):
            first = generator.generate(self.root / "artifacts/no-properties", **inputs)
            second = generator.generate(self.root / "artifacts/properties-none", oem_property_contract=None, **inputs)
        self.assertEqual(first, second)
        self.assertNotIn("oem_properties", first)
        self.assertTrue(all("oem_properties" not in row["path"] for row in first["files"]))

    def test_property_bundle_is_rejected_without_matching_explicit_source_capability(self):
        inputs, verification = self.oem_inputs()
        verification["oem_property_contract"] = {"path": generator.OEM_PROPERTY_RECORD.as_posix(),
                                                  "sha256": generator.OEM_PROPERTY_CONTRACT_SHA256, "size_bytes": 65716}
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification), \
                self.assertRaisesRegex(generator.CandidateError, "OEM property source capability"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_property_generation_is_deterministic_and_preserves_v11_device_sources_and_readiness(self):
        inputs, verification = self.property_inputs()
        first, second = self.root / "artifacts/property-first", self.root / "artifacts/property-repeat"
        for variant in generator.BUILD_VARIANTS:
            first_variant, second_variant = first / variant, second / variant
            with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
                plan = generator.generate(first_variant, variant=variant, **inputs)
                self.assertEqual(generator.generate(second_variant, variant=variant, **inputs), plan)
            self.assertEqual(generator.validate(first_variant), plan)
            self.assertEqual(len(plan["files"]), len(generator.TEMPLATE_FILES) + 20)
            self.assertEqual(plan["oem_properties"]["expected_native_effective_ordinary_allow_edges"], generator.OEM_PROPERTY_ALLOW_BUDGET)
            for key in ("source_checkout_inspected", "fresh_soong_or_m4_build_performed", "native_effective_allow_budget_verified",
                        "strict_full_policy_compiled", "complete_context_or_treble_checks_passed", "image_integration_verified", "hardware_tested"):
                self.assertIs(plan["oem_properties"][key], False, key)
            self.assertTrue(plan["oem_properties"]["inherited_denial_logging_effects"]["existing_dontaudit_semantics_do_change_for_restored_types"])
            board = (first_variant / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
            self.assertEqual(board.count("SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS"), 3)
            self.assertEqual(board.count("SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS"), 2)
            self.assertTrue(board.endswith("\n" + "\n".join(generator._dsp_wiring_lines()) + "\n"))
            for key, path in generator.OEM_PROPERTY_WIRING.items():
                self.assertEqual(board.count(f"{key} += {path}\n"), 1)
            for name in ("BoardConfig.mk", "init-helper-capability.mk", *generator.DSP_POLICY_FILES, *generator.OEM_POLICY_FILES):
                self.assertEqual((first_variant / generator.DEVICE_PATH / name).read_bytes(), (ROOT / generator.DEVICE_PATH / name).read_bytes())
            for purpose in ("target-files", "flash"):
                with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                    generator.validate(first_variant, purpose=purpose)

    def test_property_profile_combines_with_mi_ext_without_changing_its_binding(self):
        inputs, verification = self.property_inputs()
        inputs, mi_ext = self.mi_ext_inputs(inputs)
        output = self.root / "artifacts/property-mi-ext"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification), \
                mock.patch.object(generator, "_verify_mi_ext_inputs", return_value=mi_ext):
            plan = generator.generate(output, variant="user", **inputs)
        self.assertEqual(plan["mi_ext_inputs"], mi_ext)
        self.assertEqual(plan["required_unpacked_partitions"], [])
        self.assertEqual(generator.validate(output), plan)
        self.assertFalse(plan["admission"]["complete_target_files_allowed"])

    def test_property_contract_rejects_unknown_hash_or_symlink(self):
        inputs, verification = self.property_inputs()
        path = inputs["oem_property_contract"]
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with self.assertRaisesRegex(generator.CandidateError, "unknown or changed OEM property"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        path.write_bytes(original)
        link = self.root / "property-link.json"
        link.symlink_to(path.name)
        with self.assertRaisesRegex(generator.CandidateError, "symlink"):
            generator.generate(self.root / "artifacts/refused", **dict(inputs, oem_property_contract=link))

    def test_property_contract_rejects_membership_reader_prefix_and_scope_widening(self):
        inputs, verification = self.property_inputs()
        original = json.loads(inputs["oem_property_contract"].read_text())
        changes = [lambda c: c["types"]["vendor_mm_parser_prop"]["attributes"].append("coredomain"),
                   lambda c: c["types"]["vendor_mm_parser_prop"]["mapping_members"].append("unreviewed_prop"),
                   lambda c: c["read_clauses"][0]["permissions"].append("write"),
                   lambda c: c["property_contexts"][0].update(match="exact"),
                   lambda c: c["property_contexts"][0].update(property_pattern="persist.vendor."),
                   lambda c: c["native_effective_ordinary_allow_edges"]["vendor_wlc_public_prop"].update(count=27),
                   lambda c: c["source_files"][0].update(scope="vendor"),
                   lambda c: c["limits"].update(denial_logging_unchanged=True),
                   lambda c: c["finite_impact"]["assertions"].update(ordinary_semantic_restriction_edges_removed=1)]
        for change in changes:
            contract = copy.deepcopy(original)
            change(contract)
            self.trust_synthetic_property_contract(inputs, contract, verification)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_property_binding_rejects_other_base_helper_factory_input_or_source_revision(self):
        inputs, verification = self.property_inputs()
        original = json.loads(inputs["oem_property_contract"].read_text())
        changes = [lambda c: c["base_oem_contract"].update(sha256="0" * 64),
                   lambda c: c["required_capability_contract"].update(value="true"),
                   lambda c: c["unchanged_factory_inputs"][0].update(sha256="0" * 64),
                   lambda c: c["existing_vendor_derivation"].update(sha256="0" * 64),
                   lambda c: c["required_source_revisions"].update(**{"system/core": "0" * 40}),
                   lambda c: c["evidence"]["factory_system_ext_mapping"].update(sha256="0" * 64)]
        for change in changes:
            contract = copy.deepcopy(original)
            change(contract)
            self.trust_synthetic_property_contract(inputs, contract, verification)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_property_source_requires_matching_native_bundle_contract_both_ways(self):
        inputs, verification = self.property_inputs()
        original = copy.deepcopy(verification)
        for value in (None, {**original["oem_property_contract"], "sha256": "0" * 64},
                      {**original["oem_property_contract"], "size_bytes": 1}):
            verification = copy.deepcopy(original)
            verification["oem_property_contract"] = value
            with self.subTest(value=value), mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification), \
                    self.assertRaisesRegex(generator.CandidateError, "OEM property source capability"):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def test_property_generation_refuses_modified_evidence_and_unlisted_source_files(self):
        inputs, verification = self.property_inputs()
        contract = json.loads(inputs["oem_property_contract"].read_text())
        for key in generator.OEM_PROPERTY_EVIDENCE:
            path = self.root / contract["evidence"][key]["path"]
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.subTest(key=key), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)
        extra = inputs["template_root"] / "sepolicy/system_ext/oem_properties/private/unreviewed.te"
        extra.write_text("allow mediaextractor vendor_mm_parser_prop:file write;\n")
        with self.assertRaisesRegex(generator.CandidateError, "unreviewed file or directory"):
            generator.generate(self.root / "artifacts/refused", **inputs)

    def test_property_source_grammar_rejects_duplicate_macros_after_source_and_contract_reseal(self):
        inputs, verification = self.property_inputs()
        contract = json.loads(inputs["oem_property_contract"].read_text())
        row = contract["source_files"][0]
        path = inputs["template_root"] / Path(row["path"]).relative_to(generator.DEVICE_PATH)
        raw = path.read_bytes() + b"system_public_prop(vendor_mm_parser_prop)\n"
        path.write_bytes(raw)
        row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        self.trust_synthetic_property_contract(inputs, contract, verification)
        with self.assertRaisesRegex(generator.CandidateError, "missing, duplicated, or unreviewed"):
            generator.generate(self.root / "artifacts/refused", **inputs)

    def test_property_validation_rejects_resealed_sources_wiring_and_permission_budget(self):
        inputs, verification = self.property_inputs()
        output = self.root / "artifacts/property-reseal"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        for relative, addition in ((generator.OEM_PROPERTY_FILES[1], b"get_prop(mediaextractor, vendor_wlc_public_prop)\n"),
                                   ("generated/BoardConfigCandidate.mk", b"SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += device/xiaomi/nezha/sepolicy/system_ext/oem_properties/public\n"),
                                   ("device.mk", b"SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += device/xiaomi/nezha/sepolicy/system_ext/oem_properties/private\n")):
            name = (generator.DEVICE_PATH / relative).as_posix()
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, original + addition)
            with self.subTest(relative=relative), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)
        for change in (lambda p: p["oem_properties"].update(native_effective_allow_budget_verified=True),
                       lambda p: p["oem_properties"]["expected_native_effective_ordinary_allow_edges"]["vendor_sys_video_prop"].update(count=27),
                       lambda p: p["policy_inputs"].pop("oem_property_contract")):
            changed = copy.deepcopy(plan)
            change(changed)
            (output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_property_validation_cannot_enable_sources_without_explicit_contract(self):
        inputs, verification = self.oem_inputs()
        output = self.root / "artifacts/property-unselected"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "device.mk").as_posix()
        original = (output / name).read_bytes()
        for addition in (b"SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += device/xiaomi/nezha/sepolicy/system_ext/oem_properties/private\n",
                         b"SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/sepolicy/system_ext/oem_properties/private\n",
                         b"SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/sepolicy/system_ext/oem_properties/public\n"):
            self.reseal_candidate_file(output, plan, name, original + addition)
            with self.subTest(addition=addition), self.assertRaisesRegex(generator.CandidateError, "property source selection may only"):
                generator.validate(output)

    def test_property_validation_never_reopens_private_evidence_or_claims_a_native_build(self):
        inputs, verification = self.property_inputs()
        output = self.root / "artifacts/property-offline"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        with mock.patch.object(generator, "_bound_reference", side_effect=AssertionError("private evidence read")), \
                mock.patch.object(generator, "_verify_policy_input_bundle", side_effect=AssertionError("private policy bundle read")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("native process")):
            self.assertEqual(generator.validate(output), plan)
        self.assertFalse(plan["oem_properties"]["native_effective_allow_budget_verified"])

    def test_property_slice_refuses_provider_bundles_without_separate_source_capability(self):
        inputs, verification = self.property_inputs()
        for key in ("framework_provider_policy_contract", "framework_provider_inputs"):
            changed = copy.deepcopy(verification)
            changed[key] = {"unselected": True}
            with self.subTest(key=key), mock.patch.object(generator, "_verify_policy_input_bundle", return_value=changed), \
                    self.assertRaisesRegex(generator.CandidateError, "separately supported source capability"):
                generator.generate(self.root / "artifacts/refused", **inputs)

    def provider_inputs(self, *, properties=False):
        """Real public sources/renderer, mocked private bundle verification boundary."""
        from scripts import framework_provider_inputs as provider_inputs
        inputs, policy_verification = self.property_inputs() if properties else self.oem_inputs()
        profile = json.loads((ROOT / generator.FRAMEWORK_PROVIDER_INPUT_RECORD).read_text())
        profile["factory_package_sha256"] = "3" * 64
        profile_path = self.root / generator.FRAMEWORK_PROVIDER_INPUT_RECORD
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_raw = (json.dumps(profile, sort_keys=True) + "\n").encode()
        profile_path.write_bytes(profile_raw)
        profile_identity = {"sha256": hashlib.sha256(profile_raw).hexdigest(), "size_bytes": len(profile_raw)}
        patcher = mock.patch.object(generator, "FRAMEWORK_PROVIDER_INPUT_SHA256", profile_identity["sha256"])
        patcher.start()
        self.addCleanup(patcher.stop)
        contract = json.loads((ROOT / generator.FRAMEWORK_PROVIDER_RECORD).read_text())
        contract["factory_package_sha256"] = "3" * 64
        contract["required_contracts"] = {
            "oem_policy": {key: policy_verification["oem_policy_contract"][key] for key in ("path", "sha256")},
            "init_helper": {"path": generator.INIT_HELPER_RECORD.as_posix(),
                            "sha256": hashlib.sha256(inputs["init_helper_capability_contract"].read_bytes()).hexdigest()},
            "provider_inputs": {"path": generator.FRAMEWORK_PROVIDER_INPUT_RECORD.as_posix(),
                                "sha256": profile_identity["sha256"]},
        }
        contract_path = self.root / generator.FRAMEWORK_PROVIDER_RECORD
        contract_raw = (json.dumps(contract, sort_keys=True) + "\n").encode()
        contract_path.write_bytes(contract_raw)
        patcher = mock.patch.object(generator, "FRAMEWORK_PROVIDER_CONTRACT_SHA256", hashlib.sha256(contract_raw).hexdigest())
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in generator.FRAMEWORK_PROVIDER_FILES:
            path = inputs["template_root"] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / generator.DEVICE_PATH / name).read_bytes())
        for row, destination in [(profile["source_lock"], self.root),
                                 *((item["evidence"], self.root) for item in profile["payload_derivations"]),
                                 *((row, inputs.get("patch_source_root", ROOT)) for row in profile["required_source_patches"])]:
            path = destination / row["path"]
            if destination != ROOT:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / row["path"]).read_bytes())
        bundle = self.root / "providers"
        bundle.mkdir()
        blueprint = provider_inputs._module_bp(profile)
        product = generator._framework_provider_product(profile)
        files = {"proprietary" + row["runtime_path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                 for row in profile["files"]}
        files.update({"provenance/captures/" + name + ".json": {key: row[key] for key in ("sha256", "size_bytes")}
                      for name, row in profile["captures"].items()})
        files["provenance/nezha-framework-providers.json"] = profile_identity
        files["framework-providers.Android.bp"] = {"sha256": hashlib.sha256(blueprint).hexdigest(), "size_bytes": len(blueprint)}
        controls = generator._framework_provider_native_controls(profile, files)
        files.update({name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)} for name, raw in controls.items()})
        files["framework-providers.mk"] = {"sha256": hashlib.sha256(product).hexdigest(), "size_bytes": len(product)}
        for name in files:
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blueprint if name == "framework-providers.Android.bp" else b"inert private-input placeholder\n")
        receipt = bundle / generator.FRAMEWORK_PROVIDER_INPUTS_RECEIPT
        receipt.write_bytes(b'{"schema_version":1,"synthetic":true}\n')
        verification = {
            "schema_version": 1, "operation": "stage-framework-provider-inputs", "status": "verified", "device": "nezha",
            "bundle": generator.FRAMEWORK_PROVIDER_INPUTS_PATH, "module_package": generator.FRAMEWORK_PROVIDER_MODULE_PACKAGE,
            "contract": profile_identity, "factory_package_sha256": "3" * 64,
            "factory_image": profile["factory_image"], "source_lock": profile["source_lock"],
            "native_check_target": provider_inputs.CHECK, "native_output_recipe": profile["native_output_recipe"],
            "payload_derivations": copy.deepcopy(profile["payload_derivations"]),
            "packages": [row["module"] for row in profile["files"] if "module" in row], "providers": profile["providers"],
            "scope": profile["scope"], "readback_verified": True,
            "module_blueprint": {"path": "framework-providers.Android.bp", **files["framework-providers.Android.bp"]},
            "receipt": {"path": receipt.name, "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(), "size_bytes": receipt.stat().st_size},
            "files": [{"path": name, **value} for name, value in sorted(files.items())],
        }
        receipt.write_bytes(provider_inputs.encoded({key: value for key, value in verification.items() if key not in ("status", "receipt")}))
        verification["receipt"].update(sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(), size_bytes=receipt.stat().st_size)
        policy_verification["framework_provider_policy_contract"] = {
            "path": generator.FRAMEWORK_PROVIDER_RECORD.as_posix(), "sha256": hashlib.sha256(contract_raw).hexdigest(),
            "size_bytes": len(contract_raw),
        }
        policy_verification["framework_provider_inputs"] = copy.deepcopy(verification)
        inputs.update(framework_provider_policy_contract=contract_path, framework_provider_inputs_receipt=receipt)
        return inputs, verification, policy_verification

    def generate_provider(self, output, inputs, verification, policy_verification):
        with mock.patch.object(generator, "_verify_framework_provider_bundle", return_value=verification), \
                mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy_verification):
            return generator.generate(output, **inputs)

    def evolution_base_inputs(self):
        """Use exact public source selectors with synthetic private admissions."""
        inputs, providers, native = self.provider_inputs(properties=True)
        inputs["variant"] = "user"
        contract = json.loads((ROOT / generator.EVOLUTION_POLICY_BASE_RECORD).read_bytes())
        contract["required_contracts"] = {
            "oem_policy": native["oem_policy_contract"],
            "oem_properties": native["oem_property_contract"],
            "framework_provider_policy": native["framework_provider_policy_contract"],
        }
        path = self.root / generator.EVOLUTION_POLICY_BASE_RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(contract, indent=2, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        identity = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}

        def trusted_synthetic_contract(selected):
            self.assertEqual(Path(selected).read_bytes(), raw)
            return copy.deepcopy(contract), identity, raw

        # This isolates generator coupling. The policy-input suite exercises the
        # real public contract loader and byte verifier, without this boundary.
        self.enterContext(mock.patch.object(generator, "_evolution_policy_base_contract",
                                            side_effect=trusted_synthetic_contract))
        native["evolution_policy_base_contract"] = {
            "path": generator.EVOLUTION_POLICY_BASE_RECORD.as_posix(), **identity}
        inputs["evolution_policy_base_contract"] = path
        return inputs, providers, native

    def test_evolution_base_generation_is_explicit_repeatable_and_preserves_existing_sources(self):
        inputs, providers, native = self.evolution_base_inputs()
        first, repeat = self.root / "artifacts/evolution-base", self.root / "artifacts/evolution-base-repeat"
        plan = self.generate_provider(first, inputs, providers, native)
        self.assertEqual(self.generate_provider(repeat, inputs, providers, native), plan)
        self.assertEqual(generator.validate(first), plan)
        legacy_inputs = {key: value for key, value in inputs.items() if key != "evolution_policy_base_contract"}
        legacy_native = {key: value for key, value in native.items() if key != "evolution_policy_base_contract"}
        legacy = self.root / "artifacts/evolution-base-absent"
        baseline = self.generate_provider(legacy, legacy_inputs, providers, legacy_native)
        self.assertNotIn("evolution_policy_base", baseline)
        old_files = {row["path"]: row for row in baseline["files"]}
        new_files = {row["path"]: row for row in plan["files"]}
        self.assertEqual(set(new_files) - set(old_files), {
            generator.EVOLUTION_POLICY_BASE_RECORD.as_posix(), generator.EVOLUTION_POLICY_BASE_GROUPS.as_posix()})
        for name, row in old_files.items():
            self.assertEqual(new_files[name], row)
            self.assertEqual((first / name).read_bytes(), (legacy / name).read_bytes())
        self.assertFalse(plan["admission"]["flash_allowed"])
        self.assertFalse(plan["admission"]["complete_target_files_allowed"])
        self.assertFalse(plan["evolution_policy_base"]["fresh_soong_or_m4_build_performed"])
        self.assertFalse(plan["evolution_policy_base"]["image_integration_verified"])

    def test_evolution_base_source_and_native_bundle_must_be_selected_together(self):
        inputs, providers, native = self.evolution_base_inputs()
        without_source = {key: value for key, value in inputs.items() if key != "evolution_policy_base_contract"}
        without_native = {key: value for key, value in native.items() if key != "evolution_policy_base_contract"}
        for name, selected, verification in (("source-missing", without_source, native),
                                               ("native-missing", inputs, without_native)):
            output = self.root / "artifacts" / name
            with self.subTest(name=name), self.assertRaisesRegex(generator.CandidateError, "same explicit contract"):
                self.generate_provider(output, selected, providers, verification)
            self.assertFalse(output.exists())

    def test_evolution_base_resealed_blueprint_or_profile_removal_is_rejected(self):
        inputs, providers, native = self.evolution_base_inputs()
        output = self.root / "artifacts/evolution-base-tampering"
        plan = self.generate_provider(output, inputs, providers, native)
        name = generator.EVOLUTION_POLICY_BASE_GROUPS.as_posix()
        original = (output / name).read_bytes()
        changed = original.replace(b'"system_ext/public/attributes"', b'"system_ext/public/*"')
        self.assertNotEqual(changed, original)
        self.reseal_candidate_file(output, plan, name, changed)
        with self.assertRaisesRegex(generator.CandidateError, "source filegroups differ"):
            generator.validate(output)
        self.reseal_candidate_file(output, plan, name, original)
        removed = copy.deepcopy(plan)
        del removed["evolution_policy_base"]
        (output / "admission.json").write_text(json.dumps(removed))
        with self.assertRaises(generator.CandidateError):
            generator.validate(output)

    def test_evolution_base_owned_group_render_cannot_be_applied_twice(self):
        from scripts import policy_inputs
        inputs, providers, native = self.evolution_base_inputs()
        output = self.root / "artifacts/evolution-base-duplicate"
        plan = self.generate_provider(output, inputs, providers, native)
        with self.assertRaisesRegex(generator.CandidateError, "selected or rendered twice"):
            generator._bind_evolution_policy_base(plan, inputs["evolution_policy_base_contract"], {})
        without_binding = {key: value for key, value in plan.items() if key != "evolution_policy_base"}
        with self.assertRaisesRegex(generator.CandidateError, "selected or rendered twice"):
            generator._bind_evolution_policy_base(without_binding, inputs["evolution_policy_base_contract"],
                {generator.EVOLUTION_POLICY_BASE_GROUPS.as_posix(): policy_inputs.render_evolution_owned_groups()})

    def camera_property_inputs(self):
        inputs, providers, native = self.evolution_base_inputs()
        path = ROOT / generator.CAMERA_PROPERTY_RECORD
        raw = path.read_bytes()
        native["camera_property_capability_contract"] = {
            "path": generator.CAMERA_PROPERTY_RECORD.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        inputs["camera_property_capability_contract"] = path
        return inputs, providers, native

    def test_camera_property_generation_is_explicit_repeatable_and_preserves_other_sources(self):
        from scripts import policy_inputs
        inputs, providers, native = self.camera_property_inputs()
        first, repeat = self.root / "artifacts/camera", self.root / "artifacts/camera-repeat"
        plan = self.generate_provider(first, inputs, providers, native)
        self.assertEqual(self.generate_provider(repeat, inputs, providers, native), plan)
        self.assertEqual(generator.validate(first), plan)
        legacy = self.root / "artifacts/camera-absent"
        old_inputs = {key: value for key, value in inputs.items() if key != "camera_property_capability_contract"}
        old_native = {key: value for key, value in native.items() if key != "camera_property_capability_contract"}
        baseline = self.generate_provider(legacy, old_inputs, providers, old_native)
        self.assertNotIn("camera_property_capability", baseline)
        before = {row["path"]: row for row in baseline["files"]}
        after = {row["path"]: row for row in plan["files"]}
        camera = plan["camera_property_capability"]
        self.assertEqual(set(after) - set(before), {
            generator.CAMERA_PROPERTY_RECORD.as_posix(), generator.CAMERA_PROPERTY_GUARD.as_posix(),
            camera["source_patch"]["path"]})
        self.assertEqual({name for name in before if before[name] != after[name]}, {
            "device/xiaomi/nezha/BoardConfig.mk", "device/xiaomi/nezha/generated/BoardConfigCandidate.mk"})
        old_board = (legacy / "device/xiaomi/nezha/BoardConfig.mk").read_bytes()
        new_board = (first / "device/xiaomi/nezha/BoardConfig.mk").read_bytes()
        self.assertEqual(new_board, policy_inputs.camera_property_board(old_board))
        self.assertEqual((first / generator.CAMERA_PROPERTY_GUARD).read_bytes(), policy_inputs.render_camera_property_guard())
        generated = (first / "device/xiaomi/nezha/generated/BoardConfigCandidate.mk").read_text()
        self.assertEqual(generated.count("BOARD_SEPOLICY_M4DEFS += " + policy_inputs.CAMERA_PROPERTY_SYMBOL + "=false\n"), 1)
        self.assertFalse(camera["fresh_soong_or_m4_build_performed"])
        self.assertFalse(camera["strict_full_policy_compiled"])
        self.assertFalse(plan["admission"]["flash_allowed"])

    def test_camera_property_source_and_native_bundle_require_same_explicit_profile(self):
        inputs, providers, native = self.camera_property_inputs()
        no_source = {key: value for key, value in inputs.items() if key != "camera_property_capability_contract"}
        no_native = {key: value for key, value in native.items() if key != "camera_property_capability_contract"}
        for label, selected, verified in (("source", no_source, native), ("bundle", inputs, no_native)):
            with self.subTest(label=label), self.assertRaisesRegex(generator.CandidateError, "same explicit contract"):
                self.generate_provider(self.root / "artifacts" / label, selected, providers, verified)
        with mock.patch.object(generator, "_load_records") as read:
            with self.assertRaisesRegex(generator.CandidateError, "explicit Evolution"):
                generator.generate(self.root / "artifacts/refused-camera", record_paths={},
                    kernel_receipt="unused", vendor_receipt="unused", camera_property_capability_contract="unused")
            read.assert_not_called()

    def test_camera_property_resealed_duplicate_conflicting_and_other_file_definitions_fail(self):
        from scripts import policy_inputs
        inputs, providers, native = self.camera_property_inputs()
        output = self.root / "artifacts/camera-tampering"
        plan = self.generate_provider(output, inputs, providers, native)
        generated = "device/xiaomi/nezha/generated/BoardConfigCandidate.mk"
        original = (output / generated).read_bytes()
        definition = ("BOARD_SEPOLICY_M4DEFS += " + policy_inputs.CAMERA_PROPERTY_SYMBOL + "=false\n").encode()
        for change in (original + definition, original.replace(definition, definition.replace(b"=false", b"=true")),
                       original.replace(definition, b""), original + b"BOARD_SEPOLICY_M4DEFS += $(LATE_CAMERA_FLAGS)\n"):
            self.reseal_candidate_file(output, plan, generated, change)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, generated, original)
        for name in ("device/xiaomi/nezha/device.mk", "device/xiaomi/nezha/Android.bp",
                     generator.CAMERA_PROPERTY_GUARD.as_posix()):
            data = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, data + definition)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, data)
        self.assertEqual(generator.validate(output), plan)

    def test_camera_final_guard_and_board_include_cannot_be_removed_or_doubled(self):
        from scripts import policy_inputs
        inputs, providers, native = self.camera_property_inputs()
        output = self.root / "artifacts/camera-final-guard"
        plan = self.generate_provider(output, inputs, providers, native)
        name = "device/xiaomi/nezha/BoardConfig.mk"
        raw = (output / name).read_bytes()
        token = b"include $(NEZHA_DEVICE_PATH)/generated/camera-property-capability.mk\n"
        for changed in (raw.replace(token, b""), raw + token):
            self.reseal_candidate_file(output, plan, name, changed)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, name, raw)
        with self.assertRaisesRegex(policy_inputs.PolicyInputsError, "exactly one"):
            policy_inputs.camera_property_board(raw)
        with self.assertRaisesRegex(generator.CandidateError, "selected or rendered twice"):
            generator._bind_camera_property(plan, inputs["camera_property_capability_contract"], ROOT, {})

    def test_camera_cli_does_not_implicitly_select_other_profiles(self):
        for extra, expected in (([], None), (["--camera-property-capability-contract", "camera.json"], Path("camera.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(["generate", "--output", "artifacts/unused",
                    "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json", *extra]), 0)
            self.assertEqual(generate.call_args.kwargs["camera_property_capability_contract"], expected)
            self.assertIsNone(generate.call_args.kwargs["evolution_policy_base_contract"])

    def factory_contexts_inputs(self):
        inputs, providers, native = self.camera_property_inputs()
        path = ROOT / generator.FACTORY_CONTEXTS_RECORD
        raw = path.read_bytes()
        native["factory_property_contexts_capability_contract"] = {
            "path": generator.FACTORY_CONTEXTS_RECORD.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        inputs["factory_property_contexts_capability_contract"] = path
        return inputs, providers, native

    def test_factory_contexts_generation_pairs_two_distinct_capabilities_and_preserves_other_bytes(self):
        from scripts import policy_inputs
        inputs, providers, native = self.factory_contexts_inputs()
        output, repeat = self.root / "artifacts/contexts", self.root / "artifacts/contexts-repeat"
        plan = self.generate_provider(output, inputs, providers, native)
        self.assertEqual(self.generate_provider(repeat, inputs, providers, native), plan)
        self.assertEqual(generator.validate(output), plan)
        old_inputs = {key: value for key, value in inputs.items() if key != "factory_property_contexts_capability_contract"}
        old_native = {key: value for key, value in native.items() if key != "factory_property_contexts_capability_contract"}
        old = self.root / "artifacts/contexts-absent"
        baseline = self.generate_provider(old, old_inputs, providers, old_native)
        before = {row["path"]: row for row in baseline["files"]}
        after = {row["path"]: row for row in plan["files"]}
        contexts = plan["factory_property_contexts_capability"]
        self.assertEqual(set(after) - set(before), {generator.FACTORY_CONTEXTS_RECORD.as_posix(),
            generator.FACTORY_CONTEXTS_GUARD.as_posix(), contexts["source_patch"]["path"]})
        self.assertEqual({name for name in before if before[name] != after[name]}, {
            "device/xiaomi/nezha/BoardConfig.mk", "device/xiaomi/nezha/generated/BoardConfigCandidate.mk"})
        self.assertEqual((output / "device/xiaomi/nezha/BoardConfig.mk").read_bytes(),
            policy_inputs.factory_property_contexts_board((old / "device/xiaomi/nezha/BoardConfig.mk").read_bytes()))
        self.assertEqual((output / generator.FACTORY_CONTEXTS_GUARD).read_bytes(), policy_inputs.render_factory_property_contexts_guard())
        board = (output / "device/xiaomi/nezha/generated/BoardConfigCandidate.mk").read_text()
        self.assertEqual(board.count("BOARD_SEPOLICY_M4DEFS += " + policy_inputs.CAMERA_PROPERTY_SYMBOL + "=false\n"), 1)
        self.assertEqual(board.count("BOARD_SEPOLICY_M4DEFS += " + policy_inputs.FACTORY_CONTEXTS_SYMBOL + "=true\n"), 1)
        self.assertEqual(plan["camera_property_capability"], baseline["camera_property_capability"])
        self.assertFalse(contexts["fresh_soong_or_m4_build_performed"])
        self.assertFalse(contexts["image_integration_verified"])

    def test_factory_contexts_generation_requires_explicit_camera_and_matching_native_profile(self):
        inputs, providers, native = self.factory_contexts_inputs()
        missing_source = {key: value for key, value in inputs.items() if key != "factory_property_contexts_capability_contract"}
        missing_native = {key: value for key, value in native.items() if key != "factory_property_contexts_capability_contract"}
        for name, options, verified in (("source", missing_source, native), ("native", inputs, missing_native)):
            with self.subTest(name=name), self.assertRaisesRegex(generator.CandidateError, "same explicit contract"):
                self.generate_provider(self.root / "artifacts" / name, options, providers, verified)
        with mock.patch.object(generator, "_load_records") as load:
            with self.assertRaisesRegex(generator.CandidateError, "explicit camera"):
                generator.generate(self.root / "artifacts/missing-camera", record_paths={},
                    kernel_receipt="unused", vendor_receipt="unused", factory_property_contexts_capability_contract="unused")
            load.assert_not_called()

    def test_factory_contexts_resealed_duplicate_false_removed_or_relocated_definitions_fail(self):
        from scripts import policy_inputs
        inputs, providers, native = self.factory_contexts_inputs()
        output = self.root / "artifacts/contexts-tampering"
        plan = self.generate_provider(output, inputs, providers, native)
        generated = "device/xiaomi/nezha/generated/BoardConfigCandidate.mk"
        original = (output / generated).read_bytes()
        definition = ("BOARD_SEPOLICY_M4DEFS += " + policy_inputs.FACTORY_CONTEXTS_SYMBOL + "=true\n").encode()
        for changed in (original + definition, original.replace(definition, definition.replace(b"=true", b"=false")),
                        original.replace(definition, b""), original + b"BOARD_SEPOLICY_M4DEFS += $(LATE_CONTEXT_FLAGS)\n"):
            self.reseal_candidate_file(output, plan, generated, changed)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, generated, original)
        for name in ("device/xiaomi/nezha/device.mk", generator.FACTORY_CONTEXTS_GUARD.as_posix()):
            raw = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, raw + definition)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, raw)
        board = "device/xiaomi/nezha/BoardConfig.mk"
        raw = (output / board).read_bytes()
        token = b"include $(NEZHA_DEVICE_PATH)/generated/factory-property-contexts-capability.mk\n"
        for changed in (raw.replace(token, b""), raw + token):
            self.reseal_candidate_file(output, plan, board, changed)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
        self.reseal_candidate_file(output, plan, board, raw)
        self.assertEqual(generator.validate(output), plan)

    def test_factory_contexts_cli_does_not_select_camera_implicitly(self):
        for extra, expected in (([], None), (["--factory-property-contexts-capability-contract", "contexts.json"], Path("contexts.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(["generate", "--output", "artifacts/unused",
                    "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json", *extra]), 0)
            self.assertEqual(generate.call_args.kwargs["factory_property_contexts_capability_contract"], expected)
            self.assertIsNone(generate.call_args.kwargs["camera_property_capability_contract"])

    def test_provider_public_contracts_and_source_statements_are_pinned(self):
        contract, identity = generator._framework_provider_contract(ROOT / generator.FRAMEWORK_PROVIDER_RECORD)
        profile, profile_identity = generator._framework_provider_input_contract(ROOT / generator.FRAMEWORK_PROVIDER_INPUT_RECORD)
        self.assertEqual(identity["sha256"], generator.FRAMEWORK_PROVIDER_CONTRACT_SHA256)
        self.assertEqual(profile_identity["sha256"], contract["required_contracts"]["provider_inputs"]["sha256"])
        generator._verify_framework_provider_sources({row["path"]: (ROOT / row["path"]).read_bytes()
                                                    for row in contract["source_files"]}, contract)
        blueprint = generator._framework_provider_blueprint(profile).decode()
        self.assertEqual(blueprint.count("check_elf_files: true"), 26)
        self.assertEqual(blueprint.count("allow_undefined_symbols: false"), 26)
        self.assertNotIn("proprietary/", blueprint)
        self.assertEqual(len(profile["payload_derivations"]), 1)
        derivation = profile["payload_derivations"][0]
        original = next(row for row in profile["files"] if row["runtime_path"] == derivation["runtime_path"])
        self.assertEqual({key: original[key] for key in ("sha256", "size_bytes")}, derivation["recipe"]["original"])
        self.assertIn(derivation["recipe"]["old"], original["needed"])
        module = blueprint.split('name: "' + original["module"] + '",', 1)[1].split("\n}", 1)[0]
        self.assertIn('"android.media.audio.common.types-V4-cpp"', module)
        self.assertNotIn('"android.media.audio.common.types-V2-cpp"', module)

    def test_provider_requires_explicit_source_inputs_oem_and_native_policy_before_reads(self):
        for values in ({"framework_provider_policy_contract": "none"},
                       {"framework_provider_inputs_receipt": "none"},
                       {"framework_provider_policy_contract": "none", "framework_provider_inputs_receipt": "none"}):
            with self.subTest(values=values), mock.patch.object(generator, "_load_records") as records, \
                    self.assertRaisesRegex(generator.CandidateError, "explicit paired provider"):
                generator.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none", vendor_receipt="none", **values)
            records.assert_not_called()

    def test_provider_only_generation_preserves_native_dependencies_and_readiness(self):
        inputs, verification, policy = self.provider_inputs()
        first, second = self.root / "artifacts/providers", self.root / "artifacts/providers-repeat"
        with mock.patch.object(generator, "_verify_framework_provider_bundle", return_value=verification) as verify, \
                mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy) as native:
            plan = generator.generate(first, **inputs)
            self.assertEqual(verify.call_count, 2)
            native.assert_called_once_with(inputs["policy_inputs_receipt"],
                                           framework_provider_inputs_receipt=inputs["framework_provider_inputs_receipt"])
        self.assertEqual(self.generate_provider(second, inputs, verification, policy), plan)
        self.assertNotIn("oem_properties", plan)
        self.assertEqual(plan["framework_providers"]["inputs"], policy["framework_provider_inputs"])
        self.assertEqual(len(plan["framework_providers"]["inputs"]["payload_derivations"]), 1)
        evidence = plan["framework_providers"]["inputs"]["payload_derivations"][0]["evidence"]
        self.assertEqual((first / evidence["path"]).read_bytes(), (self.root / evidence["path"]).read_bytes())
        self.assertEqual((first / generator.FRAMEWORK_PROVIDER_BLUEPRINT).read_bytes(),
                         (inputs["framework_provider_inputs_receipt"].parent / "framework-providers.Android.bp").read_bytes())
        product = (first / generator.DEVICE_PATH / "generated/device-candidate.mk").read_text()
        self.assertEqual(product.count("$(call inherit-product, vendor/xiaomi/nezha-framework-providers/framework-providers.mk)"), 1)
        self.assertNotIn("PRODUCT_PACKAGES", product)
        board = (first / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        self.assertEqual(board.count("SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS"), 2)
        self.assertEqual(board.count(next(iter(generator.FRAMEWORK_PROVIDER_WIRING.values()))), 1)
        for key in ("source_checkout_inspected", "source_patches_applied", "fresh_soong_or_m4_build_performed",
                    "strict_native_elf_checks_passed", "strict_full_policy_compiled", "complete_context_or_treble_checks_passed",
                    "image_integration_verified", "hardware_tested"):
            self.assertIs(plan["framework_providers"][key], False)
        for purpose in ("target-files", "flash"):
            with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(first, purpose=purpose)

    def test_provider_and_property_profiles_compose_without_public_provider_mappings(self):
        inputs, verification, policy = self.provider_inputs(properties=True)
        output = self.root / "artifacts/providers-properties"
        plan = self.generate_provider(output, inputs, verification, policy)
        self.assertIn("oem_properties", plan)
        self.assertEqual(plan["oem_properties"]["expected_native_effective_ordinary_allow_edges"], generator.OEM_PROPERTY_ALLOW_BUDGET)
        board = (output / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
        self.assertEqual(board.count("SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS"), 3)
        self.assertEqual(board.count("SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS"), 3)
        self.assertTrue(all(row["scope"] == "system_ext_private" and row["versioned_attribute"] is None
                            for row in plan["framework_providers"]["types"].values()))

    def test_provider_off_profile_never_reads_external_bundle_or_sources(self):
        inputs, policy = self.oem_inputs()
        with mock.patch.object(generator, "_verify_framework_provider_bundle", side_effect=AssertionError("implicit external input")), \
                mock.patch.object(generator, "_framework_provider_contract", side_effect=AssertionError("implicit source")), \
                mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy):
            plan = generator.generate(self.root / "artifacts/no-providers", **inputs)
        self.assertNotIn("framework_providers", plan)
        self.assertTrue(all("framework_providers" not in row["path"] and "framework-providers" not in row["path"] for row in plan["files"]))

    def test_provider_native_policy_requires_identical_full_bundle_and_source_binding(self):
        inputs, verification, original = self.provider_inputs()
        for change in (lambda p: p.pop("framework_provider_inputs"), lambda p: p.pop("framework_provider_policy_contract"),
                       lambda p: p["framework_provider_inputs"]["files"][0].update(sha256="f" * 64),
                       lambda p: p["framework_provider_policy_contract"].update(size_bytes=1)):
            policy = copy.deepcopy(original)
            change(policy)
            with self.subTest(change=change), self.assertRaisesRegex(generator.CandidateError, "same separately supported source"):
                self.generate_provider(self.root / "artifacts/refused", inputs, verification, policy)

    def test_provider_rejects_input_namespace_recipe_scope_and_package_tampering(self):
        inputs, original, policy = self.provider_inputs()
        for change in (lambda p: p.update(bundle="vendor/other"), lambda p: p.update(module_package="vendor/other"),
                       lambda p: p["native_output_recipe"].update(consumer_inputs="raw_inputs"),
                       lambda p: p["scope"].update(elf_checks_disabled=True), lambda p: p["packages"].pop(),
                       lambda p: p["module_blueprint"].update(sha256="f" * 64), lambda p: p["receipt"].update(sha256="f" * 64),
                       lambda p: p["files"].append(copy.deepcopy(p["files"][0])),
                       lambda p: p["files"].__setitem__(0, {**p["files"][0], "path": "../../bad"})):
            verification = copy.deepcopy(original)
            change(verification)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                self.generate_provider(self.root / "artifacts/refused", inputs, verification, policy)

    def test_provider_rejects_changed_contracts_sources_blueprint_and_source_patch(self):
        inputs, verification, policy = self.provider_inputs()
        paths = [inputs["framework_provider_policy_contract"], self.root / generator.FRAMEWORK_PROVIDER_INPUT_RECORD,
                 inputs["template_root"] / generator.FRAMEWORK_PROVIDER_FILES[2],
                 inputs["framework_provider_inputs_receipt"].parent / "framework-providers.Android.bp",
                 self.root / "config/evolution-source-lock.json"]
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(path=path), self.assertRaises(generator.CandidateError):
                self.generate_provider(self.root / "artifacts/refused", inputs, verification, policy)
            path.write_bytes(original)

    def test_provider_rejects_symlinked_and_extra_source_and_bundle_entries(self):
        inputs, verification, policy = self.provider_inputs()
        for directory in (inputs["template_root"] / Path(generator.FRAMEWORK_PROVIDER_FILES[0]).parent,
                          inputs["framework_provider_inputs_receipt"].parent):
            for kind in ("file", "directory", "symlink"):
                extra = directory / "unreviewed"
                if kind == "file": extra.write_bytes(b"unreviewed")
                elif kind == "directory": extra.mkdir()
                else: extra.symlink_to(inputs["framework_provider_policy_contract"])
                with self.subTest(directory=directory, kind=kind), self.assertRaises(generator.CandidateError):
                    self.generate_provider(self.root / "artifacts/refused", inputs, verification, policy)
                if kind == "directory": extra.rmdir()
                else: extra.unlink()

    def test_provider_rechecks_external_inventory_after_final_verifier(self):
        inputs, verification, policy = self.provider_inputs()
        calls = 0
        def mutate_after_verification(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                (inputs["framework_provider_inputs_receipt"].parent / "late-directory").mkdir()
            return verification
        with mock.patch.object(generator, "_verify_framework_provider_bundle", side_effect=mutate_after_verification), \
                mock.patch.object(generator, "_verify_policy_input_bundle", return_value=policy), \
                self.assertRaisesRegex(generator.CandidateError, "unexpected directory"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_provider_rejects_output_inside_preserved_inputs_before_creating_directories(self):
        inputs, verification, policy = self.provider_inputs()
        for key in ("framework_provider_inputs_receipt", "policy_inputs_receipt"):
            old = inputs[key]
            bundle = self.root / "artifacts" / ("protected-" + key)
            old.parent.rename(bundle)
            inputs[key] = bundle / old.name
        for key in ("framework_provider_inputs_receipt", "policy_inputs_receipt"):
            output = inputs[key].parent / "unreviewed-parent/candidate"
            with self.subTest(key=key), self.assertRaisesRegex(generator.CandidateError, "must not be nested"):
                self.generate_provider(output, inputs, verification, policy)
            self.assertFalse(output.parent.exists())

    def test_provider_validation_rejects_resealed_blueprint_sources_and_duplicate_wiring(self):
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-resealed"
        plan = self.generate_provider(output, inputs, verification, policy)
        cases = [(generator.FRAMEWORK_PROVIDER_BLUEPRINT, b"cc_prebuilt_binary { name: \"unreviewed\" }\n"),
                 ((generator.DEVICE_PATH / generator.FRAMEWORK_PROVIDER_FILES[2]).as_posix(), b"permissive vendor_qccsyshal_qti;\n"),
                 ((generator.DEVICE_PATH / "generated/device-candidate.mk").as_posix(),
                  b"$(call inherit-product, vendor/xiaomi/nezha-framework-providers/framework-providers.mk)\n"),
                 ((generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix(),
                  b"SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += device/xiaomi/nezha/sepolicy/system_ext/framework_providers/private\n"),
                 ((generator.DEVICE_PATH / "device.mk").as_posix(), b"PRODUCT_PACKAGES += nezha_framework_qccsyshal_aidl_service\n"),
                 ((generator.DEVICE_PATH / "Android.bp").as_posix(), b"soong_namespace { imports: [\"vendor/xiaomi/nezha-framework-providers\"] }\n")]
        for name, extra in cases:
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, original + extra)
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            self.reseal_candidate_file(output, plan, name, original)

    def test_provider_validation_rejects_receipt_promotion_and_missing_policy_binding(self):
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-limits"
        plan = self.generate_provider(output, inputs, verification, policy)
        for change in (lambda p: p["framework_providers"].update(strict_native_elf_checks_passed=True),
                       lambda p: p["framework_providers"].update(image_integration_verified=True),
                       lambda p: p["framework_providers"]["inputs"]["native_output_recipe"].update(consumer_inputs="raw_inputs"),
                       lambda p: p["policy_inputs"].pop("framework_provider_inputs"), lambda p: p.pop("framework_providers")):
            changed = copy.deepcopy(plan)
            change(changed)
            (output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_provider_validation_is_portable_and_does_not_reopen_private_evidence(self):
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-portable"
        plan = self.generate_provider(output, inputs, verification, policy)
        with mock.patch.object(generator, "_bound_reference", side_effect=AssertionError("private evidence read")), \
                mock.patch.object(generator, "_verify_policy_input_bundle", side_effect=AssertionError("private policy read")), \
                mock.patch.object(generator, "_verify_framework_provider_bundle", side_effect=AssertionError("private provider read")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("native process")):
            self.assertEqual(generator.validate(output), plan)

    def test_provider_validation_rejects_jointly_resealed_native_control_identities(self):
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-controls"
        plan = self.generate_provider(output, inputs, verification, policy)
        for path in ("Android.bp", "tools/verify_framework_provider_inputs.py", "framework-providers.mk"):
            changed = copy.deepcopy(plan)
            for record in (changed["framework_providers"]["inputs"], changed["policy_inputs"]["framework_provider_inputs"]):
                next(row for row in record["files"] if row["path"] == path)["sha256"] = "f" * 64
            (output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(path=path), self.assertRaisesRegex(generator.CandidateError, "input inventory differs"):
                generator.validate(output)

    def test_provider_validation_rejects_jointly_resealed_receipt_identity(self):
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-receipt"
        plan = self.generate_provider(output, inputs, verification, policy)
        for field, value in (("sha256", "f" * 64), ("size_bytes", 1)):
            changed = copy.deepcopy(plan)
            for record in (changed["framework_providers"]["inputs"], changed["policy_inputs"]["framework_provider_inputs"]):
                record["receipt"][field] = value
            (output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaisesRegex(generator.CandidateError, "exact canonical manifest"):
                generator.validate(output)

    def test_provider_validation_rejects_jointly_resealed_derivation_metadata(self):
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-derivation-metadata"
        plan = self.generate_provider(output, inputs, verification, policy)
        mutations = (
            lambda value: value.pop("payload_derivations"),
            lambda value: value.update(payload_derivations=[]),
            lambda value: value["payload_derivations"].append(copy.deepcopy(value["payload_derivations"][0])),
            lambda value: value["payload_derivations"][0]["recipe"].update(changed_byte_file_offset=1),
            lambda value: value["payload_derivations"][0]["recipe"]["original"].update(sha256="f" * 64),
            lambda value: value["payload_derivations"][0]["recipe"]["derived"].update(sha256="f" * 64),
            lambda value: value["payload_derivations"][0]["recipe"].update(new="unreviewed.so"),
            lambda value: value["payload_derivations"][0]["evidence"].update(sha256="f" * 64),
            lambda value: value["native_output_recipe"].pop("payload_transformations"),
            lambda value: value["native_output_recipe"].update(payload_transformations="arbitrary_elf_rewrite"),
        )
        for number, mutate in enumerate(mutations):
            changed = copy.deepcopy(plan)
            for record in (changed["framework_providers"]["inputs"], changed["policy_inputs"]["framework_provider_inputs"]):
                mutate(record)
                record["receipt"].update(generator._framework_provider_receipt_identity(record))
            (output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(number=number), self.assertRaisesRegex(generator.CandidateError, "reviewed source admission"):
                generator.validate(output)

    def test_provider_validation_rejects_native_checker_that_omits_the_byte_derivation(self):
        from scripts import framework_provider_inputs as provider_inputs
        inputs, verification, policy = self.provider_inputs()
        output = self.root / "artifacts/providers-raw-checker"
        plan = self.generate_provider(output, inputs, verification, policy)
        profile = json.loads((self.root / generator.FRAMEWORK_PROVIDER_INPUT_RECORD).read_bytes())
        checker_path = "tools/verify_framework_provider_inputs.py"
        native_files = {row["path"]: {key: row[key] for key in ("sha256", "size_bytes")}
                        for row in verification["files"]
                        if row["path"] not in {"Android.bp", "framework-providers.mk", checker_path}}
        forged = provider_inputs._native_checker(dict(sorted(native_files.items())),
                                                 provider_inputs._native_outputs(profile), [])
        for record in (plan["framework_providers"]["inputs"], plan["policy_inputs"]["framework_provider_inputs"]):
            next(row for row in record["files"] if row["path"] == checker_path).update(
                sha256=hashlib.sha256(forged).hexdigest(), size_bytes=len(forged))
            record["receipt"].update(generator._framework_provider_receipt_identity(record))
        (output / "admission.json").write_text(json.dumps(plan))
        with self.assertRaisesRegex(generator.CandidateError, "input inventory differs"):
            generator.validate(output)

    def test_provider_derivation_evidence_is_required_before_staging_and_after_relocation(self):
        inputs, verification, policy = self.provider_inputs()
        reference = verification["payload_derivations"][0]["evidence"]
        evidence = self.root / reference["path"]
        original = evidence.read_bytes()
        for kind in ("missing", "changed", "symlink"):
            evidence.unlink()
            if kind == "changed":
                evidence.write_bytes(original + b"unreviewed")
            elif kind == "symlink":
                evidence.symlink_to(inputs["framework_provider_policy_contract"])
            output = self.root / "artifacts" / ("refused-evidence-" + kind)
            with self.subTest(kind=kind), self.assertRaises((generator.CandidateError, OSError)):
                self.generate_provider(output, inputs, verification, policy)
            self.assertFalse(output.exists())
            if evidence.exists() or evidence.is_symlink():
                evidence.unlink()
            evidence.write_bytes(original)
        output = self.root / "artifacts/providers-evidence"
        plan = self.generate_provider(output, inputs, verification, policy)
        self.reseal_candidate_file(output, plan, reference["path"], original + b"unreviewed")
        with self.assertRaisesRegex(generator.CandidateError, "derivation evidence"):
            generator.validate(output)

    def test_provider_cli_arguments_are_explicit_and_default_to_none(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json", "--output", "artifacts/out"]
        for option in ("framework-provider-policy-contract", "framework-provider-inputs-receipt"):
            for arguments, expected in (([], None), (["--" + option, "provider.json"], Path("provider.json"))):
                with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                    self.assertEqual(generator.main(base + arguments), 0)
                self.assertEqual(generate.call_args.kwargs[option.replace("-", "_")], expected)

    def test_cli_passes_optional_property_contract_without_enabling_it_by_default(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json", "--output", "artifacts/out"]
        for args, expected in (([], None), (["--oem-property-contract", "property.json"], Path("property.json"))):
            with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(base + args), 0)
            self.assertEqual(generate.call_args.kwargs["oem_property_contract"], expected)

    def test_oem_source_generation_is_explicit_deterministic_and_keeps_all_existing_guards(self):
        inputs, verification = self.oem_inputs()
        for variant in generator.BUILD_VARIANTS:
            first = self.root / "artifacts" / ("oem-" + variant)
            second = self.root / "artifacts" / ("oem-repeat-" + variant)
            with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
                plan = generator.generate(first, variant=variant, **inputs)
                self.assertEqual(generator.generate(second, variant=variant, **inputs), plan)
            self.assertEqual(generator.validate(first), plan)
            self.assertEqual(len(plan["files"]), len(generator.TEMPLATE_FILES) + 15)
            self.assertEqual(plan["oem_policy"]["factory_framework_evidence_files_rehashed"], 3)
            self.assertFalse(plan["oem_policy"]["fresh_soong_or_m4_build_performed"])
            self.assertFalse(plan["oem_policy"]["strict_full_policy_compiled"])
            self.assertFalse(plan["oem_policy"]["complete_context_or_treble_checks_passed"])
            board = (first / generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").read_text()
            self.assertTrue(board.endswith("\n" + "\n".join(generator._dsp_wiring_lines()) + "\n"))
            self.assertIn("\n" + "\n".join(generator._init_helper_wiring_lines()) + "\n", board)
            for name, path in generator.OEM_POLICY_WIRING.items():
                self.assertEqual(board.count(f"{name} += {path}\n"), 1)
            self.assertEqual(board.count("SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS"), 2)
            self.assertEqual(board.count("SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS"), 1)
            self.assertEqual((first / generator.DEVICE_PATH / "BoardConfig.mk").read_bytes(),
                             (ROOT / generator.DEVICE_PATH / "BoardConfig.mk").read_bytes())
            for purpose in ("target-files", "flash"):
                with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                    generator.validate(first, purpose=purpose)

    def test_oem_contract_requires_exact_bytes_and_refuses_symlinks(self):
        inputs, verification = self.oem_inputs()
        path = inputs["oem_policy_contract"]
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with self.assertRaisesRegex(generator.CandidateError, "unknown or changed OEM"):
            generator.generate(self.root / "artifacts/refused", **inputs)
        path.write_bytes(original)
        link = self.root / "oem-policy-link.json"
        link.symlink_to(path)
        with self.assertRaisesRegex(generator.CandidateError, "symlink"):
            generator.generate(self.root / "artifacts/refused", **dict(inputs, oem_policy_contract=link))

    def test_oem_contract_cannot_change_ownership_mappings_platform_or_existing_inputs(self):
        inputs, verification = self.oem_inputs()
        baseline = json.loads(inputs["oem_policy_contract"].read_text())
        changes = (
            lambda c: c["platform"].update(branch="cnb"),
            lambda c: c["platform"].update(board_api="202604"),
            lambda c: c["source_files"][0].update(scope="system_ext_private"),
            lambda c: c["source_files"][0].update(path="device/xiaomi/nezha/sepolicy/generated.cil"),
            lambda c: c["source_files"].append(copy.deepcopy(c["source_files"][0])),
            lambda c: c["wiring"].update(SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS="device/xiaomi/other"),
            lambda c: c.update(factory_origin_verified=True),
            lambda c: c.update(factory_package_sha256="4" * 64),
            lambda c: c["required_capability_contract"].update(value="true"),
            lambda c: c["required_capability_contract"].update(sha256="4" * 64),
            lambda c: c["required_source_revisions"].update({"build/soong": "4" * 40}),
            lambda c: c["unchanged_factory_inputs"][0].update(sha256="4" * 64),
            lambda c: c["types"]["vendor_hal_atfwd_hwservice"]["attributes"].append("domain"),
            lambda c: c["types"]["vendor_hal_systemhelper_aidl_service"].update(role="unreviewed_r"),
            lambda c: c["types"]["offlinelog_file"].update(versioned_attribute="offlinelog_file_202504"),
            lambda c: c["types"]["vendor_hal_atfwd_hwservice"]["mapping_members"].append("domain"),
            lambda c: c["limits"].update(new_allow_statements_added=True),
            lambda c: c["limits"].update(complete_rom_admitted=True),
        )
        for change in changes:
            contract = copy.deepcopy(baseline)
            change(contract)
            self.trust_synthetic_oem_contract(inputs, contract, verification)
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)
        self.assertFalse((self.root / "artifacts/refused").exists())

    def test_oem_rehashes_factory_framework_evidence_and_authored_sources(self):
        inputs, verification = self.oem_inputs()
        contract = json.loads(inputs["oem_policy_contract"].read_text())
        dsp = json.loads(inputs["dsp_policy_contract"].read_text())["generator_contract"]
        capture = json.loads((self.root / dsp["policy_capture_receipt"]["path"]).read_text())
        selected = {row["runtime_path"] for row in contract["evidence"]["source_rows"]}
        paths = [self.root / row["path"] for row in capture["input_order"] if row["runtime_path"] in selected]
        paths += [inputs["template_root"] / name for name in generator.OEM_POLICY_FILES]
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(original + b"; changed\n")
            with self.subTest(path=path), self.assertRaisesRegex(generator.CandidateError, "hash/size mismatch"):
                generator.generate(self.root / "artifacts/refused", **inputs)
            path.write_bytes(original)

    def test_oem_capture_cannot_substitute_framework_evidence_or_promote_triage(self):
        inputs, verification = self.oem_inputs()
        baseline = json.loads(inputs["oem_policy_contract"].read_text())
        for change in (
            lambda c: c["evidence"]["source_rows"][0].update(sha256="4" * 64),
            lambda c: c["evidence"]["source_rows"].append(copy.deepcopy(c["evidence"]["source_rows"][0])),
        ):
            contract = copy.deepcopy(baseline)
            change(contract)
            self.trust_synthetic_oem_contract(inputs, contract, verification)
            with self.assertRaises(generator.CandidateError):
                generator.generate(self.root / "artifacts/refused", **inputs)
        contract = copy.deepcopy(baseline)
        path = self.root / contract["evidence"]["triage"]["path"]
        triage = json.loads(path.read_text())
        triage["oem_te_source_recovered"] = True
        raw = (json.dumps(triage) + "\n").encode()
        path.write_bytes(raw)
        contract["evidence"]["triage"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        self.trust_synthetic_oem_contract(inputs, contract, verification)
        with self.assertRaisesRegex(generator.CandidateError, "bounded generated-CIL observation"):
            generator.generate(self.root / "artifacts/refused", **inputs)

    def test_oem_source_capability_requires_matching_native_bundle_identity(self):
        inputs, original = self.oem_inputs()
        for value in (None, {**original["oem_policy_contract"], "sha256": "4" * 64},
                      {**original["oem_policy_contract"], "size_bytes": 1}):
            verification = copy.deepcopy(original)
            verification["oem_policy_contract"] = value
            with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
                with self.assertRaisesRegex(generator.CandidateError, "same reviewed contract"):
                    generator.generate(self.root / "artifacts/refused", **inputs)

    def test_oem_validation_rejects_resealed_sources_contract_and_admission_claims(self):
        inputs, verification = self.oem_inputs()
        output = self.root / "artifacts/oem-source-guards"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        names = [(generator.DEVICE_PATH / name).as_posix() for name in generator.OEM_POLICY_FILES]
        names.append(generator.OEM_POLICY_RECORD.as_posix())
        for name in names:
            original = (output / name).read_bytes()
            self.reseal_candidate_file(output, plan, name, original + b"\n")
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            (output / name).write_bytes(original)
        updated = copy.deepcopy(plan)
        updated["oem_policy"]["strict_full_policy_compiled"] = True
        (output / "admission.json").write_text(json.dumps(updated))
        with self.assertRaisesRegex(generator.CandidateError, "OEM policy admission"):
            generator.validate(output)

    def test_oem_validation_keeps_exact_board_and_native_bundle_guards(self):
        inputs, verification = self.oem_inputs()
        output = self.root / "artifacts/oem-wiring-guards"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix()
        original = (output / name).read_bytes()
        first = next(iter(generator.OEM_POLICY_WIRING.items()))
        directive = f"{first[0]} += {first[1]}\n".encode()
        for raw in (original.replace(directive, b"# " + directive),
                    original.replace(directive, directive + directive),
                    original.replace(directive, directive.replace(b"/oem/public", b"/unreviewed")),
                    original.replace(directive, b"ifeq (false,true)\n" + directive + b"endif\n")):
            self.reseal_candidate_file(output, plan, name, raw)
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)
        (output / name).write_bytes(original)
        for change in (lambda p: p.pop("policy_inputs"),
                       lambda p: p["policy_inputs"].pop("oem_policy_contract"),
                       lambda p: p.pop("oem_policy")):
            updated = copy.deepcopy(plan)
            change(updated)
            (output / "admission.json").write_text(json.dumps(updated))
            with self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_oem_candidate_validation_does_not_rehash_unmounted_private_evidence(self):
        inputs, verification = self.oem_inputs()
        output = self.root / "artifacts/oem-self-contained"
        with mock.patch.object(generator, "_verify_policy_input_bundle", return_value=verification):
            plan = generator.generate(output, **inputs)
        with mock.patch.object(generator, "_bound_reference", side_effect=AssertionError("private evidence accessed")):
            self.assertEqual(generator.validate(output), plan)

    def test_dsp_validation_rejects_source_tampering_even_if_inventory_is_rehashed(self):
        inputs = self.dsp_inputs()
        output = self.root / "artifacts/dsp-source-guard"
        plan = generator.generate(output, **inputs)
        for name in generator.DSP_POLICY_FILES:
            relative = (generator.DEVICE_PATH / name).as_posix()
            path = output / relative
            original = path.read_bytes()
            changed = original + b"allow domain domain:process signal;\n"
            path.write_bytes(changed)
            updated = copy.deepcopy(plan)
            next(row for row in updated["files"] if row["path"] == relative).update(
                sha256=hashlib.sha256(changed).hexdigest(), size_bytes=len(changed))
            (output / "admission.json").write_text(json.dumps(updated))
            with self.subTest(name=name), self.assertRaisesRegex(generator.CandidateError, "source file differs from the reviewed"):
                generator.validate(output)
            path.write_bytes(original)
        (output / "admission.json").write_text(json.dumps(plan))
        self.assertEqual(generator.validate(output), plan)

    def test_dsp_validation_rejects_contract_or_wiring_tampering_with_rehashed_inventory(self):
        inputs = self.dsp_inputs()
        output = self.root / "artifacts/dsp-contract-guard"
        plan = generator.generate(output, **inputs)
        names = (generator.DSP_POLICY_RECORD.as_posix(),
                 (generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix())
        for name in names:
            path = output / name
            original = path.read_bytes()
            changed = (original + b"\n" if name == generator.DSP_POLICY_RECORD.as_posix() else
                       original.replace(b"PRODUCT_PRIVATE_SEPOLICY_DIRS += device/xiaomi/nezha/",
                                        b"PRODUCT_PRIVATE_SEPOLICY_DIRS += device/xiaomi/unreviewed/"))
            path.write_bytes(changed)
            updated = copy.deepcopy(plan)
            next(row for row in updated["files"] if row["path"] == name).update(
                sha256=hashlib.sha256(changed).hexdigest(), size_bytes=len(changed))
            (output / "admission.json").write_text(json.dumps(updated))
            with self.subTest(path=name), self.assertRaises(generator.CandidateError):
                generator.validate(output)
            path.write_bytes(original)

    def test_dsp_wiring_cannot_be_commented_out_or_continued_after_inventory_rehash(self):
        inputs = self.dsp_inputs()
        output = self.root / "artifacts/dsp-wiring-lines"
        plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix()
        path = output / name
        original = path.read_bytes()
        first = b"SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += "
        second = b"PRODUCT_PRIVATE_SEPOLICY_DIRS += "
        comment = generator._dsp_wiring_lines()[0].encode()
        changes = (
            original.replace(first, b"# " + first),
            original.replace(second, b"# " + second),
            original.replace(comment + b"\n", comment + b" \\\n"),
            original.replace(first, b"unreviewed_prefix" + first),
            original + b"# unreviewed trailing section\n",
        )
        # Python text line splitting recognizes separators that Make does not.
        # The generated section requires its original ASCII LF boundaries.
        changes += tuple(original.replace(comment + b"\n", comment + separator)
                         for separator in (b"\x0b", b"\x0c", b"\r", b"\r\n", b"\xc2\x85", b"\xe2\x80\xa8"))
        for changed in changes:
            path.write_bytes(changed)
            updated = copy.deepcopy(plan)
            next(row for row in updated["files"] if row["path"] == name).update(
                sha256=hashlib.sha256(changed).hexdigest(), size_bytes=len(changed))
            (output / "admission.json").write_text(json.dumps(updated))
            with self.subTest(changed=hashlib.sha256(changed).hexdigest()), \
                    self.assertRaisesRegex(generator.CandidateError, "DSP board wiring changed"):
                generator.validate(output)

    def test_dsp_validation_rejects_self_promoted_receipts_and_package_changes(self):
        inputs = self.dsp_inputs()
        output = self.root / "artifacts/dsp-admission-guard"
        plan = generator.generate(output, **inputs)
        changes = (
            lambda p: p.update(dsp_policy=None),
            lambda p: p["dsp_policy"].update(contract_id="unknown"),
            lambda p: p["dsp_policy"].update(strict_full_policy_compiled=True),
            lambda p: p["dsp_policy"].update(fresh_soong_or_m4_build_performed=True),
            lambda p: p["dsp_policy"].update(factory_policy_inputs_rehashed=0),
            lambda p: p["source_packages"].update(vendor="4" * 64),
            lambda p: p["factory_profile"].update(package_sha256="4" * 64),
            lambda p: p["factory_profile"].update(origin_verified=True),
        )
        for change in changes:
            updated = copy.deepcopy(plan)
            change(updated)
            (output / "admission.json").write_text(json.dumps(updated))
            with self.subTest(change=change), self.assertRaises(generator.CandidateError):
                generator.validate(output)

    def test_dsp_extra_sources_are_not_admitted_by_legacy_file_lists(self):
        plan = self.candidate()
        path = self.root / generator.DEVICE_PATH / generator.DSP_POLICY_FILES[0]
        path.parent.mkdir(parents=True)
        data = b"attribute vendor_hal_dspmanager_client;\n"
        path.write_bytes(data)
        plan["files"].append({"path": path.relative_to(self.root).as_posix(),
                              "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
        self.save_admission(plan)
        with self.assertRaisesRegex(generator.CandidateError, "file set is incomplete or unexpected"):
            generator.validate(self.root)

    def test_dsp_wiring_without_opt_in_is_refused_even_with_legacy_file_inventory(self):
        plan = self.candidate()
        relative = (generator.DEVICE_PATH / "generated/BoardConfigCandidate.mk").as_posix()
        path = self.root / relative
        data = path.read_bytes() + ("\n".join(generator._dsp_wiring_lines()) + "\n").encode()
        path.write_bytes(data)
        next(row for row in plan["files"] if row["path"] == relative).update(
            sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
        self.save_admission(plan)
        with self.assertRaisesRegex(generator.CandidateError, "wiring requires an explicit reviewed contract"):
            generator.validate(self.root)

    def test_cli_dsp_policy_contract_defaults_to_none_and_passes_explicit_path(self):
        for arguments, expected in (([], None), (["--dsp-policy-contract", "reviewed.json"], Path("reviewed.json"))):
            with self.subTest(arguments=arguments), mock.patch.object(generator, "generate", return_value={}) as generate:
                with redirect_stdout(io.StringIO()):
                    result = generator.main(["generate", "--kernel-receipt", "kernel.json",
                                             "--vendor-receipt", "vendor.json", "--output", "artifacts/cli-dsp",
                                             *arguments])
                self.assertEqual(result, 0)
                self.assertEqual(generate.call_args.kwargs["dsp_policy_contract"], expected)

    def test_default_variant_remains_userdebug_and_explicit_user_changes_only_variant(self):
        default = self.plan()
        self.assertEqual(default["variant"], "userdebug")
        self.assertEqual(default, self.plan(variant="userdebug"))
        user = self.plan(variant="user")
        self.assertEqual(user, {**default, "variant": "user"})
        self.assertEqual(user["admission"], default["admission"])
        self.assertEqual(user["avb_policy"], default["avb_policy"])

    def test_plan_rejects_eng_empty_multiple_and_nonstring_variants(self):
        for variant in INVALID_VARIANTS:
            with self.subTest(variant=variant), self.assertRaisesRegex(generator.CandidateError, "variant"):
                self.plan(variant=variant)

    def test_user_generation_validates_without_changing_security_or_packaging_gates(self):
        inputs = self.generation_inputs()
        default_path, user_path = self.root / "artifacts/default", self.root / "artifacts/user"
        default = generator.generate(default_path, **inputs)
        user = generator.generate(user_path, variant="user", **inputs)
        self.assertEqual(default["variant"], "userdebug")
        self.assertEqual(user, {**default, "variant": "user"})
        self.assertEqual(generator.validate(user_path), user)
        self.assertEqual(default["files"], user["files"])
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(user_path, purpose=purpose)
        for flag in ("flash_allowed", "complete_target_files_allowed"):
            changed = copy.deepcopy(user)
            changed["admission"][flag] = True
            (user_path / "admission.json").write_text(json.dumps(changed))
            with self.subTest(flag=flag), self.assertRaisesRegex(generator.CandidateError, "cannot promote"):
                generator.validate(user_path)
        changed = copy.deepcopy(user)
        changed["avb_policy"]["disabled_flags"] = ["--flags 3"]
        (user_path / "admission.json").write_text(json.dumps(changed))
        with self.assertRaisesRegex(generator.CandidateError, "AVB policy was weakened"):
            generator.validate(user_path)

    def test_generate_rejects_invalid_variants_before_reading_inputs_or_creating_output(self):
        output = self.root / "artifacts/rejected-variant"
        with mock.patch.object(generator, "_load_records") as load:
            for variant in INVALID_VARIANTS:
                with self.subTest(variant=variant), self.assertRaisesRegex(generator.CandidateError, "variant"):
                    generator.generate(output, record_paths={}, kernel_receipt=None,
                                       vendor_receipt=None, variant=variant)
                self.assertFalse(output.exists())
            load.assert_not_called()

    def test_validation_rejects_missing_and_invalid_variant_in_admission(self):
        plan = self.candidate()
        for variant in INVALID_VARIANTS:
            self.save_admission({**plan, "variant": variant})
            with self.subTest(variant=variant), self.assertRaisesRegex(generator.CandidateError, "variant"):
                generator.validate(self.root)
        plan.pop("variant")
        self.save_admission(plan)
        with self.assertRaisesRegex(generator.CandidateError, "variant"):
            generator.validate(self.root)

    def test_cli_plan_defaults_to_userdebug_and_records_explicit_variant(self):
        for arguments, expected in (([], "userdebug"), (["--variant", "userdebug"], "userdebug"),
                                    (["--variant", "user"], "user")):
            stdout = io.StringIO()
            with self.subTest(arguments=arguments), redirect_stdout(stdout):
                self.assertEqual(generator.main(["plan", *arguments]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["variant"], expected)

    def test_cli_generate_propagates_default_and_explicit_variant(self):
        for arguments, expected in (([], "userdebug"), (["--variant", "userdebug"], "userdebug"),
                                    (["--variant", "user"], "user")):
            with self.subTest(arguments=arguments), mock.patch.object(generator, "generate", return_value={}) as generate:
                with redirect_stdout(io.StringIO()):
                    result = generator.main([
                        "generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                        "--output", "artifacts/cli-user", *arguments,
                    ])
                self.assertEqual(result, 0)
                self.assertEqual(generate.call_args.kwargs["variant"], expected)

    def test_cli_plan_and_generate_reject_invalid_variants_before_work(self):
        for command in ("plan", "generate"):
            required = (["--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                         "--output", "artifacts/cli-user"] if command == "generate" else [])
            for variant in (value for value in INVALID_VARIANTS if isinstance(value, str)):
                with self.subTest(command=command, variant=variant), \
                        mock.patch.object(generator, "_load_records") as load, \
                        mock.patch.object(generator, "generate") as generate:
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        generator.main([command, *required, "--variant", variant])
                    self.assertEqual(error.exception.code, 2)
                    load.assert_not_called()
                    generate.assert_not_called()

    def test_generation_refuses_overwrite_and_paths_outside_artifacts(self):
        inputs = self.generation_inputs()
        output = self.root / "artifacts/target"
        generator.generate(output, **inputs)
        sentinel = (output / "admission.json").read_bytes()
        with self.assertRaisesRegex(generator.CandidateError, "already exists"):
            generator.generate(output, **inputs)
        self.assertEqual((output / "admission.json").read_bytes(), sentinel)
        with self.assertRaisesRegex(generator.CandidateError, "artifacts subdirectory"):
            generator.generate(self.root / "tracked", **inputs)

    def test_generation_rejects_changed_bundle_and_missing_module_coverage(self):
        inputs = self.generation_inputs()
        image = inputs["kernel_receipt"].parent / "kernel/Image"
        original = image.read_bytes()
        image.write_bytes(b"changed kernel")
        with self.assertRaisesRegex(generator.CandidateError, "hash/size mismatch"):
            generator.generate(self.root / "artifacts/rejected", **inputs)
        image.write_bytes(original)
        receipt = json.loads(inputs["kernel_receipt"].read_text())
        stage = next(iter(receipt["module_sets"].values()))
        stage["modules"] = ["modules/missing.ko"]
        inputs["kernel_receipt"].write_text(json.dumps(receipt))
        with self.assertRaisesRegex(generator.CandidateError, "not covered"):
            generator.generate(self.root / "artifacts/rejected", **inputs)
        self.assertFalse((self.root / "artifacts/rejected").exists())

    def test_generation_rejects_unbound_header_and_symlink_parent(self):
        inputs = self.generation_inputs()
        report = self.root / "artifacts/boot-evidence/logs/unpack-vendor_boot.stdout.txt"
        original = report.read_bytes()
        report.write_bytes(original.replace(b"0x00008000", b"0x00009000"))
        with self.assertRaisesRegex(generator.CandidateError, "report hash mismatch"):
            generator.generate(self.root / "artifacts/rejected", **inputs)
        report.write_bytes(original)
        alias = self.root / "artifacts/alias"
        alias.symlink_to(self.root / "artifacts", target_is_directory=True)
        with self.assertRaisesRegex(generator.CandidateError, "symlink"):
            generator.generate(alias / "rejected", **inputs)

    def test_validation_refuses_unlisted_source_and_symlinks(self):
        self.candidate()
        extra = self.root / generator.DEVICE_PATH / "Android.mk"
        extra.write_text("# Unlisted source must not reach Kati\n")
        with self.assertRaisesRegex(generator.CandidateError, "unexpected candidate file"):
            generator.validate(self.root)
        extra.unlink()
        extra.symlink_to(self.root / "admission.json")
        with self.assertRaisesRegex(generator.CandidateError, "symlink"):
            generator.validate(self.root)

    def test_makefile_injection_paths_and_dates_are_rejected(self):
        for path in (".", "..", "../escape", "file$(id)", "/tmp/escape", "a//b", "a/./b"):
            with self.subTest(path=path), self.assertRaises(generator.CandidateError):
                generator._relative(path)
        for value in ("2026-02-30", "2026-02-01\n$(shell id)", "2026-2-1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                generator._patch_date(value)

    def test_recorded_budgets_do_not_claim_measured_capacity_or_flash_admission(self):
        plan = self.plan()
        self.assertEqual(plan["super"]["bytes"], 15300820992)
        self.assertIn("physical capacity unverified", plan["super"]["basis"])
        for name, budget in plan["image_budgets"].items():
            image = next(item for item in self.records["boot-contract"]["image_files"]
                         if item["path"] == name + ".img")
            self.assertEqual(budget["bytes"], image["size_bytes"])
            self.assertIn("physical capacity unverified", budget["basis"])
        self.assertTrue(plan["admission"]["configuration_allowed"])
        for key in ("complete_target_files_allowed", "flash_allowed",
                    "physical_partition_fit_verified", "bootloader_state_verified",
                    "kernel_abi_verified", "native_features_tested"):
            self.assertIs(plan["admission"][key], False, key)
        self.assertIs(plan["avb_policy"]["source_image_set_verified"], False)
        self.assertIs(plan["avb_policy"]["oem_authentication"], False)

    def test_geometry_and_image_budgets_follow_supplied_records(self):
        metadata = self.records["firmware-layout"]["logical_metadata"]
        metadata["physical_devices"][0]["size_bytes"] += 16 * 1024 ** 2
        group = next(item for item in metadata["groups"] if item["index"] == 1)
        group["maximum_size"] += 8 * 1024 ** 2
        group["name"] = "nezha_fixture_a"
        boot_image = next(item for item in self.records["boot-contract"]["image_files"]
                          if item["path"] == "boot.img")
        boot_image["size_bytes"] += 4096
        plan = self.plan()
        self.assertEqual(plan["super"]["bytes"], metadata["physical_devices"][0]["size_bytes"])
        self.assertEqual(plan["super"]["group_bytes"], group["maximum_size"])
        self.assertEqual(plan["super"]["group_name"], "nezha_fixture")
        self.assertEqual(plan["image_budgets"]["boot"]["bytes"], boot_image["size_bytes"])

    def test_wrong_identity_is_rejected_for_every_record_and_cn_baseline(self):
        for name in generator.RECORD_NAMES:
            records = copy.deepcopy(self.records)
            device = records[name]["device"]
            if isinstance(device, dict):
                device["codename"] = "another_device"
            else:
                records[name]["device"] = "another_device"
            with self.subTest(record=name), self.assertRaises(generator.CandidateError):
                self.plan(records)
        for key, value in (("reported_hwc", "GLOBAL"), ("soc", "SM8750"),
                           ("board_platform", "another_board"), ("abi", "x86_64")):
            records = copy.deepcopy(self.records)
            records["device-baseline"]["device"][key] = value
            with self.subTest(field=key), self.assertRaises(generator.CandidateError):
                self.plan(records)

    def test_wrong_slots_layout_and_filesystem_are_rejected(self):
        mutations = {
            "populated B slot": lambda layout: layout["partitions"][0].update(name="odm_b"),
            "multiple physical devices": lambda layout: layout["logical_metadata"]["physical_devices"].append(
                copy.deepcopy(layout["logical_metadata"]["physical_devices"][0])),
            "wrong super name": lambda layout: layout["logical_metadata"]["physical_devices"][0].update(
                partition_name="not_super"),
            "group exceeds super": lambda layout: layout["logical_metadata"]["groups"][1].update(
                maximum_size=layout["logical_metadata"]["physical_devices"][0]["size_bytes"]),
            "overcommitted group": lambda layout: layout["logical_metadata"]["groups"][1].update(
                maximum_size=4096),
            "wrong filesystem": lambda layout: layout["partitions"][0]["filesystem"].update(format="F2FS"),
        }
        for label, mutate in mutations.items():
            records = copy.deepcopy(self.records)
            mutate(records["firmware-layout"])
            with self.subTest(case=label), self.assertRaises(generator.CandidateError):
                self.plan(records)

    def test_required_kernel_configuration_and_page_size_are_enforced(self):
        for option in ("CONFIG_ARM64_4K_PAGES", "CONFIG_MODULES", "CONFIG_MODVERSIONS",
                       "CONFIG_DM_VERITY", "CONFIG_SECURITY_SELINUX"):
            records = copy.deepcopy(self.records)
            records["boot-contract"]["kernel"]["selected_config"][option] = "n"
            with self.subTest(option=option), self.assertRaises(generator.CandidateError):
                self.plan(records)
        for key, value in (("runtime_page_size_bytes", 16384), ("architecture", "x86_64")):
            records = copy.deepcopy(self.records)
            records["boot-contract"]["kernel"][key] = value
            with self.subTest(field=key), self.assertRaises(generator.CandidateError):
                self.plan(records)

    def test_recorded_avb_owners_and_mi_ext_requirement_are_retained(self):
        plan = self.plan()
        self.assertEqual(plan["avb_descriptor_owners"]["system_dlkm"], "vbmeta")
        for name in ("system", "system_ext", "product"):
            self.assertEqual(plan["avb_descriptor_owners"][name], "vbmeta_system")
        self.assertEqual(plan["avb_descriptor_owners"]["mi_ext"], "vbmeta")
        self.assertIn("mi_ext", plan["logical_filesystems"])
        self.assertEqual(plan["required_unpacked_partitions"], ["mi_ext"])
        self.assertNotIn("mi_ext", plan["packaged_logical_partitions"])
        self.assertEqual({name: chain["location"] for name, chain in plan["avb_chains"].items()},
                         {"boot": 3, "recovery": 1, "vbmeta_system": 2})
        self.assertEqual([name for name in plan["packaged_logical_partitions"]
                          if plan["avb_descriptor_owners"][name] == "vbmeta_system"],
                         ["system", "system_ext", "product"])
        root_image = next(item for item in self.records["boot-contract"]["image_files"]
                          if item["path"] == "vbmeta.img")
        root_image["avb"]["rollback_index"] = 900
        self.assertEqual(self.plan()["avb_root_rollback_index"], 900)

    def test_missing_conflicting_avb_owners_and_colliding_chains_are_rejected(self):
        for label in ("missing", "conflicting", "colliding"):
            records = copy.deepcopy(self.records)
            avb = records["boot-contract"]["avb"]
            if label == "missing":
                avb["logical_partition_checks"] = [item for item in avb["logical_partition_checks"]
                                                   if item["partition"] != "mi_ext"]
            elif label == "conflicting":
                avb["logical_partition_checks"].append({
                    "partition": "system_dlkm", "descriptor_source": "vbmeta_system"
                })
            else:
                avb["chain_key_checks"][1]["rollback_index_location"] = avb["chain_key_checks"][0]["rollback_index_location"]
            with self.subTest(case=label), self.assertRaises(generator.CandidateError):
                self.plan(records)

    def test_fstab_adds_avb_preserves_crypto_and_discards_stock_overlays(self):
        source = self.fstab()
        plan = self.plan()
        result = generator.render_fstab(plan, self.records["boot-contract"], source)
        rows = [line.split() for line in result.splitlines() if line and not line.startswith("#")]
        logical = {row[0]: row for row in rows if row[0] in plan["logical_filesystems"]}
        self.assertEqual(len(logical), 8)
        for name, row in logical.items():
            self.assertEqual(row[2:4], ["erofs", "ro"])
            self.assertIn("avb=" + plan["avb_descriptor_owners"][name], row[4].split(","))
            self.assertNotIn("nofail", row[4].split(","))
        self.assertEqual(logical["mi_ext"][1], "/mnt/vendor/mi_ext")
        self.assertIn(METADATA_ROW + "\n", result)
        self.assertIn(DATA_ROW + "\n", result)
        self.assertNotIn("ro,bind", result)
        self.assertNotIn("lowerdir=", result)
        self.assertIs(plan["fstab"]["logical_avb_enabled"], True)
        self.assertIs(plan["fstab"]["stock_overlay_mounts_adopted"], False)
        self.assertIs(plan["fstab"]["vendor_image_replacement_applied"], False)

    def test_fstab_rejects_hash_mutation_and_symlink_source(self):
        source = self.fstab()
        source.write_bytes(source.read_bytes() + b"# changed\n")
        with self.assertRaisesRegex(generator.CandidateError, "hash mismatch"):
            generator.render_fstab(self.plan(), self.records["boot-contract"], source)
        source = self.fstab()
        link = self.root / "linked.fstab"
        link.symlink_to(source)
        with self.assertRaisesRegex(generator.CandidateError, "symlink"):
            generator.render_fstab(self.plan(), self.records["boot-contract"], link)

    def test_fstab_rejects_missing_mounts_unencrypted_data_and_malformed_rows(self):
        cases = {
            "missing metadata": [DATA_ROW],
            "missing userdata": [METADATA_ROW],
            "missing encryption": [METADATA_ROW, "/dev/block/by-name/userdata /data f2fs defaults wait"],
            "malformed": [METADATA_ROW, DATA_ROW, "invalid row"],
            "unsafe field": [METADATA_ROW, DATA_ROW.replace("/data f2fs", "/data;unsafe f2fs")],
        }
        for label, rows in cases.items():
            source = self.fstab(rows)
            with self.subTest(case=label), self.assertRaises(generator.CandidateError):
                generator.render_fstab(self.plan(), self.records["boot-contract"], source)

    def test_validation_only_admits_configuration(self):
        plan = self.candidate()
        self.assertEqual(generator.validate(self.root)["product"], plan["product"])
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(self.root, purpose=purpose)

    def test_validation_rejects_receipt_promotion_weakened_avb_and_changed_files(self):
        plan = self.candidate()
        for flag in ("flash_allowed", "complete_target_files_allowed"):
            changed = copy.deepcopy(plan)
            changed["admission"][flag] = True
            self.save_admission(changed)
            with self.subTest(flag=flag), self.assertRaisesRegex(generator.CandidateError, "cannot promote"):
                generator.validate(self.root)
        changed = copy.deepcopy(plan)
        changed["avb_policy"]["disabled_flags"] = ["--flags 3"]
        self.save_admission(changed)
        with self.assertRaisesRegex(generator.CandidateError, "AVB policy was weakened"):
            generator.validate(self.root)
        self.save_admission(plan)
        (self.root / plan["files"][0]["path"]).write_bytes(b"modified\n")
        with self.assertRaisesRegex(generator.CandidateError, "hash/size mismatch"):
            generator.validate(self.root)

    def allocator_inputs(self, inputs=None):
        inputs = inputs or self.generation_inputs()
        contract = json.loads((ROOT / generator.FRAMEWORK_ALLOCATOR_RECORD).read_bytes())
        for row in (contract["source_lock"], contract["source_snapshot"]):
            path = self.root / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / row["path"]).read_bytes())
        return dict(inputs, framework_allocator_contract=ROOT / generator.FRAMEWORK_ALLOCATOR_RECORD)

    def reseal_allocator_candidate(self, output, plan, name, raw):
        path = output / name
        path.write_bytes(raw)
        row = next(row for row in plan["files"] if row["path"] == name)
        row.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        (output / "admission.json").write_text(json.dumps(plan))

    def test_allocator_contract_pins_real_service_and_separate_native_obligations(self):
        contract, identity = generator._framework_allocator_contract(ROOT / generator.FRAMEWORK_ALLOCATOR_RECORD)
        self.assertEqual(identity["sha256"], generator.FRAMEWORK_ALLOCATOR_CONTRACT_SHA256)
        self.assertEqual(contract["partition"], "system_ext")
        self.assertEqual(contract["vintf"]["max_level"], 8)
        self.assertTrue(contract["vintf"]["register_only_when_transport_hwbinder"])
        self.assertEqual(contract["init"]["executable"],
                         "/system/system_ext/bin/hw/android.hidl.allocator@1.0-service")
        self.assertEqual(contract["source_patches"], [])
        self.assertEqual(contract["additional_policy"], [])
        self.assertEqual({row["role"] for row in contract["installed_outputs"]},
                         {"binary", "init", "vintf_fragment"})
        self.assertEqual(len(contract["source_preconditions"]), 24)
        self.assertEqual(contract["required_source_revisions"]["system/libhidl"],
                         "d063c3a2bf981d8dab2ca60ea471f940d71167a6")
        self.assertIn("Build the actual android.hidl.allocator@1.0-service component",
                      "\n".join(contract["required_native_checks"]))

    def test_allocator_opt_in_selects_binary_owner_once_without_copying_a_fragment(self):
        inputs = self.allocator_inputs()
        first, second = self.root / "artifacts/allocator", self.root / "artifacts/allocator-repeat"
        plan = generator.generate(first, **inputs)
        self.assertEqual(generator.generate(second, **inputs), plan)
        product = (first / generator.DEVICE_PATH / "generated/device-candidate.mk").read_text()
        self.assertEqual(product.count("PRODUCT_PACKAGES += android.hidl.allocator@1.0-service\n"), 1)
        self.assertNotIn("PRODUCT_COPY_FILES", product)
        self.assertFalse(any(row["path"].startswith("system/libhidl/") or
                             row["path"].endswith(("-service.rc", "-service.xml")) for row in plan["files"]))
        self.assertEqual(plan["framework_allocator"]["scope"], generator.FRAMEWORK_ALLOCATOR_SCOPE)
        self.assertNotIn("page_size_profile", plan)
        self.assertNotIn("framework_providers", plan)
        self.assertEqual(generator.validate(first), plan)
        for purpose in ("target-files", "flash"):
            with self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(first, purpose=purpose)

    def test_allocator_omission_preserves_existing_product_and_does_not_read_capability(self):
        inputs = self.generation_inputs()
        with mock.patch.object(generator, "_framework_allocator_contract", side_effect=AssertionError("implicit allocator")):
            before = generator.generate(self.root / "artifacts/before", **inputs)
            explicit_none = generator.generate(self.root / "artifacts/none", framework_allocator_contract=None, **inputs)
        self.assertEqual(before, explicit_none)
        self.assertNotIn("framework_allocator", before)
        self.assertNotIn("PRODUCT_PACKAGES", generator._render_product(before))
        self.assertNotIn(generator.FRAMEWORK_ALLOCATOR_RECORD.as_posix(), {row["path"] for row in before["files"]})

    def test_allocator_composes_with_current_provider_profile_without_policy_or_alignment_changes(self):
        inputs, verification, policy = self.provider_inputs(properties=True)
        before = self.generate_provider(self.root / "artifacts/provider-before", inputs, verification, policy)
        inputs = self.allocator_inputs(inputs)
        after = self.generate_provider(self.root / "artifacts/provider-allocator", inputs, verification, policy)
        self.assertEqual(before["framework_providers"], after["framework_providers"])
        self.assertEqual(before["policy_inputs"], after["policy_inputs"])
        self.assertEqual(before["oem_properties"], after["oem_properties"])
        self.assertEqual(generator._render_board(before), generator._render_board(after))
        self.assertNotIn("page_size_profile", after)
        self.assertNotIn("PRODUCT_MAX_PAGE_SIZE_SUPPORTED", generator._render_product(after))
        self.assertEqual(after["admission"], before["admission"])

    def test_allocator_changed_contract_fails_before_candidate_publication(self):
        inputs = self.allocator_inputs()
        path = self.root / "changed-allocator.json"
        contract = json.loads(inputs["framework_allocator_contract"].read_bytes())
        contract["vintf"]["max_level"] = 202504
        path.write_text(json.dumps(contract))
        inputs["framework_allocator_contract"] = path
        output = self.root / "artifacts/refused"
        with self.assertRaisesRegex(generator.CandidateError, "changed framework allocator contract"):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())

    def test_allocator_missing_or_changed_source_lock_is_not_accepted(self):
        inputs = self.allocator_inputs()
        contract = json.loads(inputs["framework_allocator_contract"].read_bytes())
        for key in ("source_lock", "source_snapshot"):
            path = self.root / contract[key]["path"]
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(key=key), self.assertRaisesRegex(generator.CandidateError, "source lock or snapshot differs"):
                generator.generate(self.root / ("artifacts/refused-" + key), **inputs)
            path.write_bytes(original)
        (self.root / contract["source_snapshot"]["path"]).unlink()
        with self.assertRaises((generator.CandidateError, OSError)):
            generator.generate(self.root / "artifacts/missing", **inputs)

    def test_allocator_rechecks_source_inputs_before_publication(self):
        inputs = self.allocator_inputs()
        contract = json.loads(inputs["framework_allocator_contract"].read_bytes())
        snapshot = self.root / contract["source_snapshot"]["path"]
        real_validate = generator.validate
        def mutate_after_validation(*args, **kwargs):
            result = real_validate(*args, **kwargs)
            snapshot.write_bytes(snapshot.read_bytes() + b"\n")
            return result
        output = self.root / "artifacts/refused"
        with mock.patch.object(generator, "validate", side_effect=mutate_after_validation), \
                self.assertRaisesRegex(generator.CandidateError, "source lock or snapshot differs"):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())

    def test_allocator_resealed_native_success_or_partition_change_is_rejected(self):
        inputs = self.allocator_inputs()
        output = self.root / "artifacts/allocator"
        original = generator.generate(output, **inputs)
        for change in (lambda row: row["scope"].update(native_service_binary_built=True),
                       lambda row: row["scope"].update(full_vintf_compatibility_verified=True),
                       lambda row: row.update(partition="system"),
                       lambda row: row["vintf"].update(max_level=202504),
                       lambda row: row.update(source_preconditions=[]),
                       lambda row: row["installed_outputs"].pop()):
            plan = copy.deepcopy(original)
            change(plan["framework_allocator"])
            (output / "admission.json").write_text(json.dumps(plan))
            with self.assertRaisesRegex(generator.CandidateError, "allocator admission differs"):
                generator.validate(output)

    def test_allocator_resealed_product_cannot_select_fragment_alone_or_disable_checks(self):
        inputs = self.allocator_inputs()
        output = self.root / "artifacts/allocator"
        original = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "generated/device-candidate.mk").as_posix()
        raw = (output / name).read_bytes()
        for changed in (raw.replace(b"-service\n", b"-service.xml\n"),
                        raw + b"PRODUCT_PACKAGES += android.hidl.allocator@1.0-service\n",
                        raw.replace(b"PRODUCT_ENFORCE_VINTF_MANIFEST := true", b"PRODUCT_ENFORCE_VINTF_MANIFEST := false")):
            plan = copy.deepcopy(original)
            self.reseal_allocator_candidate(output, plan, name, changed)
            with self.assertRaisesRegex(generator.CandidateError, "allocator generated product"):
                generator.validate(output)

    def test_allocator_unselected_service_cannot_be_injected_into_a_resealed_candidate(self):
        inputs = self.generation_inputs()
        output = self.root / "artifacts/no-allocator"
        plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / "device.mk").as_posix()
        self.reseal_allocator_candidate(output, plan, name,
            (output / name).read_bytes() + b"\nPRODUCT_PACKAGES += android.hidl.allocator@1.0-service\n")
        with self.assertRaisesRegex(generator.CandidateError, "only use the reviewed upstream module"):
            generator.validate(output)

    def test_allocator_duplicate_init_manifest_policy_and_module_ownership_is_rejected(self):
        plan = self.plan()
        payloads = {
            "device.mk": b"PRODUCT_PACKAGES += android.hidl.allocator@1.0-service\n",
            "lineage_nezha.mk": b"NEZHA_ALLOCATOR_INTERFACE := android.hidl.allocator@1.0\nPRODUCT_PACKAGES += $(NEZHA_ALLOCATOR_INTERFACE)-service\n",
            "Android.bp": b'cc_binary { name: "android.hidl.allocator@1.0-service", }\n',
            "init.rc": b"service hidl_memory /different/service\n",
            "init-tab.rc": b"service\thidl_memory\t/different/service\n",
            "init-spaces.rc": b"service  hidl_memory  /different/service\n",
            "manifest.xml": b"<hal><name>android.hidl.allocator</name></hal>\n",
            "allocator.te": b"type hal_allocator_default, domain;\n",
            "hwservice.te": b"type hidl_allocator_hwservice, hwservice_manager_type;\n",
            "property.te": b"type hidl_memory_prop, property_type;\n",
            "file_contexts": b"/system_ext/bin/hw/android\\.hidl\\.allocator@1\\.0-service u:object_r:wrong:s0\n",
            "property_contexts": b"hidl_memory.disabled u:object_r:wrong:s0\n",
        }
        for name, raw in payloads.items():
            with self.subTest(name=name), self.assertRaisesRegex(generator.CandidateError, "only use the reviewed upstream module"):
                generator._framework_allocator_source_guards(plan, {(generator.DEVICE_PATH / name).as_posix(): raw})

    def test_allocator_public_interface_library_clients_remain_allowed(self):
        generator._framework_allocator_source_guards(self.plan(), {
            (generator.DEVICE_PATH / "framework-providers/Android.bp").as_posix():
                b'cc_prebuilt_library_shared { name: "client", shared_libs: ["android.hidl.allocator@1.0"], }\n',
            (generator.DEVICE_PATH / "client.te").as_posix():
                b'allow client hidl_allocator_hwservice:hwservice_manager find;\n'})

    def test_allocator_resealed_source_snapshot_is_rejected(self):
        inputs = self.allocator_inputs()
        output = self.root / "artifacts/allocator"
        plan = generator.generate(output, **inputs)
        name = plan["framework_allocator"]["source_snapshot"]["path"]
        self.reseal_allocator_candidate(output, plan, name, (output / name).read_bytes() + b"\n")
        with self.assertRaisesRegex(generator.CandidateError, "source lock or snapshot changed"):
            generator.validate(output)

    def test_allocator_cli_forwards_only_the_explicit_capability(self):
        with mock.patch.object(generator, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
            result = generator.main(["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                                     "--framework-allocator-contract", "allocator.json", "--output", "candidate"])
        self.assertEqual(result, 0)
        self.assertEqual(generate.call_args.kwargs["framework_allocator_contract"], Path("allocator.json"))


    def qti_namespace_inputs(self, inputs=None):
        inputs = inputs or self.generation_inputs()
        source = ROOT / generator.QTI_AIDL_NAMESPACE_RECORD
        raw = source.read_bytes()
        contract = json.loads(raw)
        for field in ('source_lock', 'source_snapshot', 'preserved_framework_provider_contract'):
            row = contract[field]
            destination = self.root / row['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / row['path']).read_bytes())
        destination = self.root / generator.QTI_AIDL_NAMESPACE_RECORD
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        return dict(inputs, qti_aidl_namespace_contract=destination)


    def test_qti_contract_pins_exact_roots_and_preserves_source_only_scope(self):
        inputs = self.qti_namespace_inputs()
        contract, identity = generator._qti_aidl_namespace_contract(inputs['qti_aidl_namespace_contract'])
        self.assertEqual(identity['sha256'], generator.QTI_AIDL_NAMESPACE_CONTRACT_SHA256)
        self.assertEqual(contract['contract_id'], generator.QTI_AIDL_NAMESPACE_CONTRACT_ID)
        self.assertEqual(contract['namespaces'], [
            'hardware/qcom-caf/sm8750', 'vendor/qcom/opensource/commonsys-intf/display'])
        self.assertEqual(contract['prior_evaluated_exports'], [
            'vendor/xiaomi/nezha-policy', 'vendor/xiaomi/nezha-framework-providers',
            'device/xiaomi/nezha/framework-providers', 'vendor/xiaomi/nezha',
            'device/xiaomi/nezha', 'vendor/xiaomi/nezha', 'vendor/lineage/prebuilts', 'vendor/bcr'])
        self.assertEqual(len(contract['required_interfaces']), 7)
        self.assertEqual(len(contract['source_preconditions']), 666)
        provider_raw = (ROOT / generator.FRAMEWORK_PROVIDER_INPUT_RECORD).read_bytes()
        self.assertEqual(contract['preserved_framework_provider_contract'], {
            'path': generator.FRAMEWORK_PROVIDER_INPUT_RECORD.as_posix(),
            'sha256': '7e514674abbf7739efb2e7520d79e7c1f302de773a3e49c0d683aba7c51fc8a7',
            'size_bytes': 30596})
        self.assertEqual(hashlib.sha256(provider_raw).hexdigest(),
                         contract['preserved_framework_provider_contract']['sha256'])
        self.assertEqual(len(provider_raw), contract['preserved_framework_provider_contract']['size_bytes'])
        generator._verify_qti_aidl_wfd_dependency(json.loads(provider_raw), contract)
        for key in ('source_patches', 'product_packages', 'runtime_services'):
            self.assertEqual(contract[key], [])
        self.assertEqual(contract['scope'], generator.QTI_AIDL_NAMESPACE_SCOPE)
        self.assertTrue(all(value is False for key, value in contract['scope'].items()
                            if key != 'phone_operations'))
        self.assertIs(type(contract['scope']['phone_operations']), list)
        self.assertEqual(contract['scope']['phone_operations'], [])


    def test_qti_omission_preserves_baseline_bytes_without_contract_reads(self):
        inputs = self.generation_inputs()
        baseline = generator
        before_dir = self.root / 'artifacts/qti-before'
        before = baseline.generate(before_dir, **inputs)
        default_dir, none_dir = self.root / 'artifacts/qti-default', self.root / 'artifacts/qti-none'
        with mock.patch.object(generator, '_qti_aidl_namespace_contract',
                               side_effect=AssertionError('implicit namespace contract read')):
            default = generator.generate(default_dir, **inputs)
            explicit_none = generator.generate(none_dir, qti_aidl_namespace_contract=None, **inputs)
        self.assertEqual(before, default)
        self.assertEqual(default, explicit_none)
        self.assertNotIn('qti_aidl_namespaces', default)
        self.assertNotIn(generator.QTI_AIDL_NAMESPACE_RECORD.as_posix(), {row['path'] for row in default['files']})
        for row in before['files']:
            self.assertEqual((before_dir / row['path']).read_bytes(), (default_dir / row['path']).read_bytes())
            self.assertEqual((before_dir / row['path']).read_bytes(), (none_dir / row['path']).read_bytes())


    def test_qti_explicit_render_adds_only_two_namespaces_once(self):
        inputs = self.generation_inputs()
        before_dir = self.root / 'artifacts/qti-base'
        before = generator.generate(before_dir, **inputs)
        inputs = self.qti_namespace_inputs(inputs)
        first_dir, second_dir = self.root / 'artifacts/qti-first', self.root / 'artifacts/qti-second'
        selected = generator.generate(first_dir, **inputs)
        self.assertEqual(generator.generate(second_dir, **inputs), selected)
        product_name = (generator.DEVICE_PATH / 'generated/device-candidate.mk').as_posix()
        before_product = (before_dir / product_name).read_text()
        after_product = (first_dir / product_name).read_text()
        expected = ('PRODUCT_SOONG_NAMESPACES += hardware/qcom-caf/sm8750 '
                    'vendor/qcom/opensource/commonsys-intf/display')
        extra = [line for line in after_product.splitlines() if line not in before_product.splitlines()
                 and line.strip() and not line.lstrip().startswith('#')]
        self.assertEqual(extra, [expected])
        self.assertEqual(after_product.splitlines().count(expected), 1)
        self.assertEqual([line for line in after_product.splitlines() if 'PRODUCT_PACKAGES' in line],
                         [line for line in before_product.splitlines() if 'PRODUCT_PACKAGES' in line])
        self.assertEqual(selected['admission'], before['admission'])
        for row in before['files']:
            if row['path'] != product_name:
                self.assertEqual((before_dir / row['path']).read_bytes(), (first_dir / row['path']).read_bytes())
        self.assertFalse(any(row['path'].startswith(('hardware/qcom-caf/', 'vendor/qcom/opensource/'))
                             for row in selected['files']))
        self.assertEqual(generator.validate(first_dir), selected)


    def test_qti_rendered_plan_composition_preserves_provider_packages_and_wfd_v5(self):
        # Load the real namespace contract before the existing fixture patches
        # provider pins to synthetic private receipts. This checks composition
        # at the rendered-plan boundary, not a real private bundle admission.
        source = ROOT / generator.QTI_AIDL_NAMESPACE_RECORD
        contract, identity = generator._qti_aidl_namespace_contract(source)
        inputs, verification, policy = self.provider_inputs(properties=True)
        before_dir = self.root / 'artifacts/qti-provider-before'
        before = self.generate_provider(before_dir, inputs, verification, policy)
        after = copy.deepcopy(before)
        after['qti_aidl_namespaces'] = generator._qti_aidl_namespace_admission(after, contract, identity)
        for key in ('framework_providers', 'policy_inputs', 'oem_properties', 'admission'):
            self.assertEqual(after[key], before[key])
        self.assertEqual(generator._render_board(after), generator._render_board(before))
        before_product, after_product = generator._render_product(before), generator._render_product(after)
        self.assertEqual([line for line in after_product.splitlines() if 'PRODUCT_PACKAGES' in line],
                         [line for line in before_product.splitlines() if 'PRODUCT_PACKAGES' in line])
        expected = ('PRODUCT_SOONG_NAMESPACES += hardware/qcom-caf/sm8750 '
                    'vendor/qcom/opensource/commonsys-intf/display')
        self.assertEqual([line for line in after_product.splitlines() if line not in before_product.splitlines()
                          and line.strip() and not line.lstrip().startswith('#')], [expected])
        blueprint = (before_dir / generator.FRAMEWORK_PROVIDER_BLUEPRINT).read_bytes()
        generator._qti_aidl_namespace_source_guards(after, {
            (generator.DEVICE_PATH / 'generated/device-candidate.mk').as_posix(): after_product.encode(),
            generator.FRAMEWORK_PROVIDER_BLUEPRINT: blueprint})
        profile = json.loads((self.root / generator.FRAMEWORK_PROVIDER_INPUT_RECORD).read_bytes())
        wfd = '//vendor/qcom/opensource/commonsys-intf/display:vendor.qti.hardware.display.config-V5-ndk'
        self.assertEqual(profile['source_dependencies']['vendor.qti.hardware.display.config-V5-ndk.so'], wfd)
        self.assertEqual(contract['preserved_wfd_dependency']['source_module'], wfd)
        self.assertIn(wfd.encode(), blueprint)
        self.assertEqual(generator._framework_provider_product(profile),
                         generator._framework_provider_product(json.loads((ROOT / generator.FRAMEWORK_PROVIDER_INPUT_RECORD).read_bytes())))


    def test_qti_source_guard_allows_existing_qualified_wfd_client_reference(self):
        generator._qti_aidl_namespace_source_guards(self.plan(), {
            generator.FRAMEWORK_PROVIDER_BLUEPRINT:
                b'cc_prebuilt_library_shared { name: "existing_client", shared_libs: ["//vendor/qcom/opensource/commonsys-intf/display:vendor.qti.hardware.display.config-V5-ndk"], }\n'})

    def test_qti_qualified_client_exception_cannot_be_used_as_namespace_export(self):
        name = (generator.DEVICE_PATH / 'device.mk').as_posix()
        qualified = b'//vendor/qcom/opensource/commonsys-intf/display:vendor.qti.hardware.display.config-V5-ndk'
        generator._qti_aidl_namespace_source_guards(self.plan(), {
            name: b'WFD_LIBRARY := ' + qualified + b'\n'})
        for separator in (b' ', b' \\\n    '):
            with self.subTest(separator=separator), self.assertRaisesRegex(
                    generator.CandidateError, 'only be exported by the reviewed generated product'):
                generator._qti_aidl_namespace_source_guards(self.plan(), {
                    name: b'PRODUCT_SOONG_NAMESPACES +=' + separator + qualified + b'\n'})


    def test_qti_changed_contract_is_rejected_before_publication(self):
        inputs = self.qti_namespace_inputs()
        path = inputs['qti_aidl_namespace_contract']
        original = json.loads(path.read_bytes())
        changes = [lambda x: x['namespaces'].append('unreviewed/namespace'),
                   lambda x: x['namespaces'].reverse(),
                   lambda x: x['namespaces'].append(x['namespaces'][0]),
                   lambda x: x['prior_evaluated_exports'].remove('vendor/xiaomi/nezha'),
                   lambda x: x['product_packages'].append('unreviewed-module'),
                   lambda x: x['source_patches'].append('unreviewed.patch')]
        for index, change in enumerate(changes):
            contract = copy.deepcopy(original)
            change(contract)
            path.write_text(json.dumps(contract))
            output = self.root / ('artifacts/qti-bad-contract-' + str(index))
            with self.subTest(index=index), self.assertRaises(generator.CandidateError):
                generator.generate(output, **inputs)
            self.assertFalse(output.exists())


    def test_qti_missing_public_metadata_dependency_is_rejected(self):
        inputs = self.qti_namespace_inputs()
        contract = json.loads(inputs['qti_aidl_namespace_contract'].read_bytes())
        for key in ('source_lock', 'source_snapshot', 'preserved_framework_provider_contract'):
            path = self.root / contract[key]['path']
            raw = path.read_bytes()
            path.unlink()
            output = self.root / ('artifacts/qti-missing-' + key)
            try:
                with self.subTest(key=key), self.assertRaises((generator.CandidateError, OSError)):
                    generator.generate(output, **inputs)
                self.assertFalse(output.exists())
            finally:
                path.write_bytes(raw)


    def test_qti_rechecks_metadata_before_publication(self):
        inputs = self.qti_namespace_inputs()
        contract = json.loads(inputs['qti_aidl_namespace_contract'].read_bytes())
        snapshot = self.root / contract['source_snapshot']['path']
        real_validate = generator.validate
        def mutate_after_validation(*args, **kwargs):
            result = real_validate(*args, **kwargs)
            snapshot.write_bytes(snapshot.read_bytes() + b'\n')
            return result
        output = self.root / 'artifacts/qti-late-input'
        with mock.patch.object(generator, 'validate', side_effect=mutate_after_validation), \
                self.assertRaises(generator.CandidateError):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())


    def test_qti_contract_symlink_is_rejected(self):
        inputs = self.qti_namespace_inputs()
        link = self.root / 'namespace-contract-link.json'
        link.symlink_to(inputs['qti_aidl_namespace_contract'])
        inputs['qti_aidl_namespace_contract'] = link
        output = self.root / 'artifacts/qti-symlink'
        with self.assertRaises(generator.CandidateError):
            generator.generate(output, **inputs)
        self.assertFalse(output.exists())


    def test_qti_resealed_plan_scope_or_namespace_change_is_rejected(self):
        inputs = self.qti_namespace_inputs()
        output = self.root / 'artifacts/qti-plan'
        original = generator.generate(output, **inputs)
        changes = [lambda p: p['qti_aidl_namespaces']['namespaces'].append('other/namespace'),
                   lambda p: p['qti_aidl_namespaces']['scope'].update(
                       {next(iter(p['qti_aidl_namespaces']['scope'])): True}),
                   lambda p: p['qti_aidl_namespaces']['contract_record'].update(sha256='0' * 64),
                   lambda p: p.pop('qti_aidl_namespaces')]
        for index, change in enumerate(changes):
            plan = copy.deepcopy(original)
            change(plan)
            (output / 'admission.json').write_text(json.dumps(plan))
            with self.subTest(index=index), self.assertRaises(generator.CandidateError):
                generator.validate(output)


    def test_qti_resealed_generated_export_change_is_rejected(self):
        inputs = self.qti_namespace_inputs()
        output = self.root / 'artifacts/qti-product'
        original = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / 'generated/device-candidate.mk').as_posix()
        raw = (output / name).read_bytes()
        line = (b'PRODUCT_SOONG_NAMESPACES += hardware/qcom-caf/sm8750 '
                b'vendor/qcom/opensource/commonsys-intf/display\n')
        changes = [raw + line, raw.replace(line, b''),
                   raw.replace(line, line.replace(b' += ', b' := ')),
                   raw + b'PRODUCT_PACKAGES += unreviewed-module\n']
        for index, changed in enumerate(changes):
            plan = copy.deepcopy(original)
            self.reseal_allocator_candidate(output, plan, name, changed)
            with self.subTest(index=index), self.assertRaises(generator.CandidateError):
                generator.validate(output)


    def test_qti_conflicting_export_in_other_device_file_is_rejected(self):
        inputs = self.qti_namespace_inputs()
        output = self.root / 'artifacts/qti-other-export'
        plan = generator.generate(output, **inputs)
        name = (generator.DEVICE_PATH / 'device.mk').as_posix()
        changed = (output / name).read_bytes() + b'\nPRODUCT_SOONG_NAMESPACES += hardware/qcom-caf/sm8750\n'
        self.reseal_allocator_candidate(output, plan, name, changed)
        with self.assertRaises(generator.CandidateError):
            generator.validate(output)


    def test_qti_unselected_export_cannot_be_injected(self):
        output = self.root / 'artifacts/qti-no-selection'
        plan = generator.generate(output, **self.generation_inputs())
        name = (generator.DEVICE_PATH / 'device.mk').as_posix()
        changed = (output / name).read_bytes() + b'\nPRODUCT_SOONG_NAMESPACES += vendor/qcom/opensource/commonsys-intf/display\n'
        self.reseal_allocator_candidate(output, plan, name, changed)
        with self.assertRaises(generator.CandidateError):
            generator.validate(output)


    def test_qti_source_admission_cannot_claim_native_or_flash_readiness(self):
        output = self.root / 'artifacts/qti-not-native'
        plan = generator.generate(output, **self.qti_namespace_inputs())
        scope = plan['qti_aidl_namespaces']['scope']
        self.assertEqual(scope, generator.QTI_AIDL_NAMESPACE_SCOPE)
        self.assertTrue(all(value is False for key, value in scope.items() if key != 'phone_operations'))
        self.assertIs(type(scope['phone_operations']), list)
        self.assertEqual(scope['phone_operations'], [])
        self.assertTrue(plan['admission']['configuration_allowed'])
        self.assertTrue(all(value is False for key, value in plan['admission'].items()
                            if key != 'configuration_allowed'))
        for purpose in ('target-files', 'flash'):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, 'admission refused'):
                generator.validate(output, purpose=purpose)


    def test_qti_cli_forwards_only_explicit_selection(self):
        for option, expected in (([], None), (['--qti-aidl-namespace-contract', 'namespace.json'], Path('namespace.json'))):
            with mock.patch.object(generator, 'generate', return_value={}) as generate, redirect_stdout(io.StringIO()):
                code = generator.main(['generate', '--kernel-receipt', 'kernel.json', '--vendor-receipt', 'vendor.json',
                                       '--output', 'candidate', *option])
            self.assertEqual(code, 0)
            self.assertEqual(generate.call_args.kwargs['qti_aidl_namespace_contract'], expected)




class NezhaBoardHookTests(unittest.TestCase):
    def test_recovery_prebuilt_hook_is_public_and_precedes_lineage_without_relocating_recovery(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        recovery = (generator.ROOT / "device/xiaomi/nezha/recovery-prebuilt.mk").read_text()
        hook = "include $(NEZHA_DEVICE_PATH)/recovery-prebuilt.mk"
        self.assertIn("recovery-prebuilt.mk", generator.TEMPLATE_FILES)
        self.assertEqual(board.count(hook), 1)
        self.assertGreater(board.index(hook), board.index("BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true"))
        self.assertLess(board.index(hook), board.index("include vendor/lineage/config/BoardConfigLineage.mk"))
        self.assertIn("TARGET_PREBUILT_RECOVERY :=", recovery)
        for forbidden in ("BOARD_USES_RECOVERY_AS_BOOT := true",
                          "BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT := true",
                          "BOARD_AVB_ENABLE := false", "androidboot.selinux=permissive"):
            self.assertNotIn(forbidden, board + recovery)

    def test_treble_labeling_is_strict_without_waivers_or_an_execution_claim(self):
        product = (generator.ROOT / "device/xiaomi/nezha/device.mk").read_text()
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        doc = (generator.ROOT / "device/xiaomi/nezha/README.md").read_text()
        self.assertIn("PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING := true", product)
        self.assertIn("ifneq ($(PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING),true)", board)
        self.assertIn("$(error Nezha requires Treble labeling violations to remain errors)", board)
        self.assertIn("ifneq ($(strip $(PRODUCT_SELINUX_TREBLE_LABELING_TRACKING_LIST_FILE)),)", board)
        self.assertIn("$(error Nezha does not admit unreviewed Treble labeling waivers)", board)
        self.assertNotIn("--treat_as_warnings", product + board)
        self.assertIn("this setting is not evidence of a passed labeling check", doc)
        self.assertIn("predates this stricter setting", doc)

    def test_board_allows_exactly_one_user_or_userdebug_variant_and_keeps_security_guards(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        guard = (
            "ifneq ($(TARGET_BUILD_VARIANT),user)\n"
            "ifneq ($(TARGET_BUILD_VARIANT),userdebug)\n"
            "$(error Nezha framework-checks product requires user or userdebug; eng weakens upstream AVB policy)\n"
            "endif\n"
            "endif"
        )
        self.assertIn(guard, board)
        self.assertNotIn("$(filter user userdebug,$(TARGET_BUILD_VARIANT))", board)
        for required in (
            "BOARD_AVB_ENABLE := true",
            "BUILD_BROKEN_SRC_DIR_IS_WRITABLE := false",
            "ifneq ($(filter true,$(SELINUX_IGNORE_NEVERALLOWS) $(BUILD_BROKEN_DUP_SYSPROP)),)",
            "$(error Nezha candidate does not permit SELinux or duplicate-property check bypasses)",
            "ifneq ($(strip $(filter " + " ".join(DENIED_FRAMEWORK_GOALS) + ",$(MAKECMDGOALS))),)",
            "$(error Nezha framework-checks profile does not admit complete target-files, OTA or super packaging; see generated admission.json)",
            "RELAX_USES_LIBRARY_CHECK := false",
            "ifneq ($(RELAX_USES_LIBRARY_CHECK),false)",
        ):
            self.assertIn(required, board)
        self.assertLess(board.index(guard), board.index("include vendor/lineage/config/BoardConfigLineage.mk"))

    def test_packaging_alias_guard_leaves_named_partial_targets_available(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        prefix, suffix = "ifneq ($(strip $(filter ", ",$(MAKECMDGOALS))),)"
        selectors = [line[len(prefix):-len(suffix)] for line in board.splitlines()
                     if line.startswith(prefix) and line.endswith(suffix)]
        self.assertEqual(selectors, [" ".join(DENIED_FRAMEWORK_GOALS)])
        denied = set(selectors[0].split())
        for alias in DENIED_FRAMEWORK_GOALS:
            with self.subTest(alias=alias):
                self.assertTrue(denied.intersection(("recoveryimage", alias)))
        for goals in (("recoveryimage",), ("bootimage",), ("recoveryimage", "bootimage"),
                      ("libc",), ("nothing",), ("all", "recoveryimage")):
            with self.subTest(goals=goals):
                self.assertFalse(denied.intersection(goals))

    def test_default_build_guard_blocks_empty_or_all_goals_only_during_build_configuration(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        guard = (
            "ifeq ($(WRITE_SOONG_VARIABLES),true)\n"
            "ifeq ($(strip $(filter-out all,$(MAKECMDGOALS))),)\n"
            "$(error Nezha framework-checks requires an explicit admitted build target; default droid packaging is not admitted)\n"
            "endif\n"
            "endif"
        )
        self.assertEqual(board.count(guard), 1)
        self.assertLess(board.index(guard), board.index("include $(NEZHA_DEVICE_PATH)/recovery-prebuilt.mk"))

        def default_is_denied(requested_goals, write_soong_variables):
            # Model these literal conditions, not a Make/Soong execution. The
            # pinned Soong path consumes dist before supplying MAKECMDGOALS.
            make_goals = [goal for goal in requested_goals.split() if goal != "dist"]
            return write_soong_variables == "true" and not any(goal != "all" for goal in make_goals)

        cases = (
            ("", "true", True), ("all", "true", True), ("dist", "true", True),
            ("all dist", "true", True), (" all all dist ", "true", True),
            ("", None, False), ("dumpvars", None, False), ("", "false", False),
            ("recoveryimage", "true", False), ("bootimage", "true", False),
            ("libc", "true", False), ("nothing", "true", False),
            ("all recoveryimage dist", "true", False),
        )
        for goals, write_soong_variables, expected in cases:
            with self.subTest(goals=goals, write_soong_variables=write_soong_variables):
                self.assertIs(default_is_denied(goals, write_soong_variables), expected)
        # Config-only/docs modes with WRITE_SOONG_VARIABLES=true and no named
        # goals are conservatively denied by the same empty-goal condition.
        self.assertTrue(default_is_denied("", "true"))

    def test_lunch_choices_include_user_and_userdebug_but_never_eng(self):
        products = (generator.ROOT / "device/xiaomi/nezha/AndroidProducts.mk").read_text()
        choices = products.split("COMMON_LUNCH_CHOICES :=", 1)[1].replace("\\", "").split()
        self.assertEqual(choices, ["lineage_nezha-bp4a-userdebug", "lineage_nezha-bp4a-user"])

    def test_stock_loader_gets_its_vendor_dlkm_selector_without_blocking_vendor_modules(self):
        product = (generator.ROOT / "device/xiaomi/nezha/device.mk").read_text()
        include = "include $(NEZHA_KERNEL_INPUTS)/kernel-inputs.mk"
        copy = "$(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE):$(TARGET_COPY_OUT_VENDOR_DLKM)/lib/modules/system_dlkm.modules.blocklist"
        self.assertEqual(product.count(include), 1)
        self.assertEqual(product.count(copy), 1)
        self.assertLess(product.index(include), product.index(copy))
        self.assertIn("ifeq ($(strip $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)),)", product)
        self.assertIn("$(error Nezha requires the captured system DLKM selection blocklist)", product)
        self.assertNotIn("BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)", product)
        wrapper = (generator.ROOT / "kernel/xiaomi/nezha/stock-prebuilt.mk").read_text()
        self.assertIn("BOARD_SYSTEM_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)", wrapper)
        self.assertIn("BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_VENDOR_MODULES_BLOCKLIST_FILE)", wrapper)

    def test_full_lineage_hook_follows_prebuilt_selector_and_board_values(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        hook = "include vendor/lineage/config/BoardConfigLineage.mk"
        self.assertEqual(board.count(hook), 1)
        self.assertNotIn("include vendor/lineage/config/BoardConfigKernel.mk", board)
        self.assertGreater(board.index(hook), board.index("include kernel/xiaomi/nezha/stock-prebuilt.mk"))
        self.assertGreater(board.index(hook), board.index("BOARD_AVB_ENABLE := true"))
        self.assertNotIn("BOARD_USES_QCOM_HARDWARE := true", board)

    def test_product_requires_read_only_source_for_ninja(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        setting = "BUILD_BROKEN_SRC_DIR_IS_WRITABLE := false"
        self.assertEqual(board.count(setting), 1)
        self.assertNotIn("BUILD_BROKEN_SRC_DIR_RW_ALLOWLIST", board)
        self.assertLess(board.index(setting), board.index("include vendor/lineage/config/BoardConfigLineage.mk"))

    def test_board_overrides_inherited_global_uses_library_relaxation(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        setting = "RELAX_USES_LIBRARY_CHECK := false"
        self.assertEqual(board.count(setting), 1)
        self.assertGreater(board.index(setting), board.index("include vendor/lineage/config/BoardConfigLineage.mk"))
        self.assertNotIn("RELAX_USES_LIBRARY_CHECK ?=", board)
        self.assertNotIn("RELAX_USES_LIBRARY_CHECK := true", board)

    def test_conflicting_uses_library_override_is_rejected(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        guard = "ifneq ($(RELAX_USES_LIBRARY_CHECK),false)\n$(error Nezha requires strict APK uses-library validation)\nendif"
        self.assertIn(guard, board)
        self.assertGreater(board.index(guard), board.index("RELAX_USES_LIBRARY_CHECK := false"))


if __name__ == "__main__":
    unittest.main()
