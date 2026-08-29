"""Offline candidate derivation and admission tests; no private inputs required."""

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
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
