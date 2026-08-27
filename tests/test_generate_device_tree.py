"""Offline candidate derivation and admission tests; no private inputs required."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

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

    def plan(self, records=None):
        return generator.derive_plan(records or self.records, self.identities)

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

    def candidate(self):
        plan = self.plan()
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
    def test_full_lineage_hook_follows_prebuilt_selector_and_board_values(self):
        board = (generator.ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text()
        hook = "include vendor/lineage/config/BoardConfigLineage.mk"
        self.assertEqual(board.count(hook), 1)
        self.assertNotIn("include vendor/lineage/config/BoardConfigKernel.mk", board)
        self.assertGreater(board.index(hook), board.index("include kernel/xiaomi/nezha/stock-prebuilt.mk"))
        self.assertGreater(board.index(hook), board.index("BOARD_AVB_ENABLE := true"))
        self.assertNotIn("BOARD_USES_QCOM_HARDWARE := true", board)


if __name__ == "__main__":
    unittest.main()
