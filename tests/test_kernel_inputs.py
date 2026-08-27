"""Offline kernel-input staging tests using synthetic bytes and private tempdirs."""

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock

from scripts import kernel_inputs


RELEASE = "6.12.23-android16-5-fixture-4k"
PACKAGE_SHA256 = hashlib.sha256(b"synthetic user-provided package").hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_module(name, source="fixture"):
    """A relocatable ARM64 ELF with a bounded section table and .modinfo."""
    names = b"\0.shstrtab\0.modinfo\0"
    info = (f"name={name}\0vermagic={RELEASE} SMP preempt mod_unload modversions aarch64\0"
            f"fixture_source={source}\0").encode()
    data = bytearray(64)
    data[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    data.extend(names)
    info_at = len(data)
    data.extend(info)
    data.extend(b"\0" * (-len(data) % 8))
    section_at = len(data)
    data.extend(bytes(64))
    data.extend(struct.pack("<IIQQQQIIQQ", 1, 3, 0, 0, 64, len(names), 0, 0, 1, 0))
    data.extend(struct.pack("<IIQQQQIIQQ", 11, 1, 2, 0, info_at, len(info), 0, 0, 1, 0))
    struct.pack_into("<HHIQQQIHHHHHH", data, 16,
                     1, 183, 1, 0, 0, section_at, 0, 64, 0, 0, 64, 3, 1)
    return bytes(data)


def synthetic_fdt(*, model="Nezha SM8850 synthetic fixture", compatible="qcom,canoe",
                  board=(8, 0), miboard=(5, 0)):
    """One valid root node; no device-tree compiler or firmware tool is run."""
    properties = {
        "model": model.encode() + b"\0",
        "compatible": compatible.encode() + b"\0",
        "qcom,board-id": struct.pack(">2I", *board),
        "xiaomi,miboard-id": struct.pack(">2I", *miboard),
    }
    strings = bytearray()
    structure = bytearray(struct.pack(">I", 1) + b"\0" * 4)
    for name, value in properties.items():
        name_at = len(strings)
        strings.extend(name.encode() + b"\0")
        structure.extend(struct.pack(">3I", 3, len(value), name_at))
        structure.extend(value)
        structure.extend(b"\0" * (-len(structure) % 4))
    structure.extend(struct.pack(">2I", 2, 9))
    structure_at = 56
    strings_at = structure_at + len(structure)
    total = strings_at + len(strings)
    header = struct.pack(">10I", 0xd00dfeed, total, structure_at, strings_at,
                         40, 17, 16, 0, len(strings), len(structure))
    return header + bytes(16) + structure + strings


def synthetic_dtbo(fdt=None):
    payload = synthetic_fdt() if fdt is None else fdt
    header = struct.pack(">8I", 0xd7b7ab1e, 64 + len(payload), 32, 32, 1, 32, 4096, 0)
    entry = struct.pack(">8I", len(payload), 64, 0, 0, 0, 0, 0, 0)
    return header + entry + payload


def synthetic_kernel(*, release=RELEASE, flags=2):
    image = bytearray(64)
    image[56:60] = b"ARM\x64"
    image.extend(f"Linux version {release} fixture@offline\n".encode())
    struct.pack_into("<QQQ", image, 8, 0x80000, len(image), flags)
    return bytes(image)


def synthetic_cpio(members):
    """Build newc and its inventory together, recording exact content offsets."""
    data = bytearray()
    entries = []
    for inode, (name, content) in enumerate([*members, ("TRAILER!!!", b"")], 1):
        encoded_name = name.encode() + b"\0"
        fields = (inode, stat.S_IFREG | 0o644, 0, 0, 1, 0, len(content),
                  0, 0, 0, 0, len(encoded_name), 0)
        data.extend(b"070701" + b"".join(f"{field:08x}".encode() for field in fields))
        data.extend(encoded_name)
        data.extend(b"\0" * (-len(data) % 4))
        offset = len(data)
        data.extend(content)
        data.extend(b"\0" * (-len(data) % 4))
        if name != "TRAILER!!!":
            entries.append({"name": name, "kind": stat.S_IFREG, "nlink": 1,
                            "size_bytes": len(content), "content_offset": offset,
                            "sha256": sha256(content)})
    return bytes(data), {"cpio_sha256": sha256(data), "entries": entries}


class KernelInputsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        (self.root / "artifacts").mkdir()
        self.output = self.root / "artifacts" / "kernel-inputs"
        self.contract_path = self.root / "contract.json"
        self.receipts = {}
        self.contract = {
            "schema_version": 1,
            "device": {"codename": "nezha", "hardware_region": "CN", "soc": "SM8850"},
            "provenance": {"parent_package_sha256": PACKAGE_SHA256,
                           "source_kind": "user-provided", "source_url": None,
                           "origin_verified": False, "package_kind": "xiaomi.eu-hybrid"},
            "kernel": {"release": RELEASE, "architecture": "arm64", "page_size_bytes": 4096,
                       "boot_header_version": 4, "dtb_count": 1, "dtbo_count": 1,
                       "dtbo_board_id": [8, 0], "dtbo_miboard_id": [5, 0]},
            "validation": {"input_avb_status": "failed", "kernel_abi_verified": False,
                           "module_signatures_verified": False, "device_tested": False},
            "receipts": {}, "files": [],
            "module_sets": {
                "vendor_ramdisk": {"source": "cpio-inventory", "receipt": "boot",
                                   "cpio_member": "ramdisks/vendor_boot.cpio",
                                   "inventory_member": "ramdisks/vendor_boot-inventory.json"},
                "vendor_dlkm": {"source": "erofs-capture", "receipt": "vendor"},
                "system_dlkm": {"source": "erofs-capture", "receipt": "system"},
            },
            "expected_module_counts": {"vendor_ramdisk": 2, "vendor_dlkm": 2, "system_dlkm": 2},
            "system_dlkm_blocklist": {"module_set": "vendor_dlkm", "path": "system_dlkm.modules.blocklist"},
            "required_system_blocklist_modules": ["zram", "zsmalloc"],
        }
        self.boot_members = {
            "unpacked/boot/kernel": synthetic_kernel(),
            "unpacked/vendor_boot/dtb": synthetic_fdt(),
            "kernel.config": ("CONFIG_ARM64=y\nCONFIG_ARM64_4K_PAGES=y\nCONFIG_MODULES=y\n"
                              "CONFIG_MODVERSIONS=y\nCONFIG_MODULE_SIG=y\nCONFIG_DM_VERITY=y\n"
                              "CONFIG_SECURITY_SELINUX=y\n").encode(),
            "unpacked/vendor_boot/vendor_ramdisk00": bytes.fromhex("02214c18") + b"vendor fixture",
            "unpacked/init_boot/ramdisk": bytes.fromhex("02214c18") + b"init fixture",
            "unpacked/recovery/ramdisk": bytes.fromhex("02214c18") + b"recovery fixture",
            "unpacked/vendor_boot/bootconfig": b"androidboot.hardware=qcom\n",
            "reference/fstab.qcom": b"Never activate this synthetic source fstab.\n",
        }
        self.cpio_members = [
            ("lib/modules/ram_a.ko", synthetic_module("ram_a")),
            ("lib/modules/ram_b.ko", synthetic_module("ram_b")),
            ("lib/modules/modules.load", b"ram_b.ko\nram_a.ko\nram_b.ko\n"),
            ("lib/modules/modules.load.recovery", b"ram_a.ko\n"),
        ]
        self.update_cpio()
        for role, receipt, member, output in (
            ("kernel", "boot", "unpacked/boot/kernel", "kernel/Image"),
            ("dtb", "boot", "unpacked/vendor_boot/dtb", "dtb/vendor.dtb"),
            ("dtbo", "archive", "dtbo.img", "dtbo/dtbo.img"),
            ("kernel_config", "boot", "kernel.config", "reference/kernel.config"),
            ("vendor_ramdisk", "boot", "unpacked/vendor_boot/vendor_ramdisk00", "reference/ramdisks/vendor_boot.lz4"),
            ("init_ramdisk", "boot", "unpacked/init_boot/ramdisk", "reference/ramdisks/init_boot.lz4"),
            ("recovery_ramdisk", "boot", "unpacked/recovery/ramdisk", "reference/ramdisks/recovery.lz4"),
            ("bootconfig", "boot", "unpacked/vendor_boot/bootconfig", "reference/vendor.bootconfig"),
        ):
            self.contract["files"].append({"receipt": receipt, "member": member, "output": output, "role": role})
        self.write_boot()
        archive = {"schema_version": 1, "parent_package_sha256": PACKAGE_SHA256,
                   "intake_provenance": {"sha256": PACKAGE_SHA256, "device": "nezha", "region": "CN",
                                         "source_kind": "user-provided", "origin_verified": False},
                   "images": []}
        payload = synthetic_dtbo()
        self.write_member("archive", "dtbo.img", payload)
        archive["images"].append({"path": "dtbo.img", "size_bytes": len(payload),
                                   "sha256": sha256(payload), "crc_verified": True})
        self.write_receipt("archive", "archive-images", archive)
        self.vendor_members = {
            "/lib/modules/zram.ko": synthetic_module("zram", "vendor"),
            "/lib/modules/zsmalloc.ko": synthetic_module("zsmalloc", "vendor"),
            "/lib/modules/modules.load": b"zsmalloc.ko\nzram.ko\nzram.ko\n",
            "/lib/modules/system_dlkm.modules.blocklist": b"blocklist zram\nblocklist zsmalloc\n",
        }
        prefix = f"/lib/modules/{RELEASE}"
        self.system_members = {
            f"{prefix}/kernel/mm/zsmalloc.ko": synthetic_module("zsmalloc", "system"),
            f"{prefix}/kernel/drivers/block/zram/zram.ko": synthetic_module("zram", "system"),
            f"{prefix}/modules.load": b"kernel/mm/zsmalloc.ko\nkernel/drivers/block/zram/zram.ko\nkernel/mm/zsmalloc.ko\n",
        }
        self.write_erofs("vendor", self.vendor_members)
        self.write_erofs("system", self.system_members)
        self.write_contract()
        self.process = self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("No firmware or subprocess execution")))
        self.shell = self.enterContext(mock.patch("os.system", side_effect=AssertionError("No shell execution")))

    def write_member(self, receipt_id, member, data):
        path = self.source / receipt_id / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_receipt(self, receipt_id, kind, receipt):
        path = self.source / receipt_id / "receipt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(receipt, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        self.receipts[receipt_id] = receipt
        self.contract["receipts"][receipt_id] = {
            "path": f"{receipt_id}/receipt.json", "sha256": sha256(raw), "type": kind,
        }

    def update_cpio(self):
        cpio, inventory = synthetic_cpio(self.cpio_members)
        self.boot_members["ramdisks/vendor_boot.cpio"] = cpio
        self.boot_members["ramdisks/vendor_boot-inventory.json"] = json.dumps(inventory).encode()

    def write_boot(self):
        receipt = {"schema_version": 1, "parent_package_sha256": PACKAGE_SHA256, "artifacts": []}
        for member, data in self.boot_members.items():
            self.write_member("boot", member, data)
            receipt["artifacts"].append({"path": member, "kind": "regular",
                                         "size_bytes": len(data), "sha256": sha256(data)})
        self.write_receipt("boot", "boot-analysis", receipt)

    def write_erofs(self, receipt_id, members):
        receipt = {"schema_version": 1, "operation": "erofs-capture", "origin_verified": False,
                   "image": {"sha256": sha256(receipt_id.encode()), "size_bytes": 4096},
                   "files": [], "firmware_executed": False, "image_mounted": False,
                   "symlinks_followed": False}
        for index, (path, data) in enumerate(members.items(), 1):
            output_path = f"files/{index:04d}"
            self.write_member(receipt_id, output_path, data)
            receipt["files"].append({"path": path, "output_path": output_path, "size_bytes": len(data),
                                       "sha256": sha256(data), "type": "regular", "readback_verified": True})
        self.write_receipt(receipt_id, "erofs-capture", receipt)

    def write_contract(self):
        self.contract_path.write_text(json.dumps(self.contract))

    def package(self, **options):
        self.write_contract()
        return kernel_inputs.package_inputs(self.contract_path, self.source, self.output,
                                            workspace_root=self.root, **options)

    def assert_rejected(self, **options):
        before = set(self.output.parent.iterdir())
        with self.assertRaises(kernel_inputs.KernelInputsError):
            self.package(**options)
        self.assertFalse(os.path.lexists(self.output))
        self.assertEqual(set(self.output.parent.iterdir()), before)

    def test_research_package_preserves_hashes_paths_order_and_failed_trust(self):
        before = {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        receipt = self.package()
        self.assertEqual(json.loads((self.output / "receipt.json").read_bytes()), receipt)
        self.assertEqual(receipt["validation"]["input_avb_status"], "failed")
        for key in ("kernel_abi_verified", "module_signatures_verified", "device_tested"):
            self.assertFalse(receipt["validation"][key])
        for record in receipt["files"]:
            path = self.output / record["path"]
            self.assertEqual(path.stat().st_size, record["size_bytes"])
            self.assertEqual(sha256(path.read_bytes()), record["sha256"])
            self.assertFalse(path.is_symlink())
            if record["path"] == "kernel-inputs.mk":
                self.assertIsNone(record["source_receipt_sha256"])
                self.assertIsNone(record["source_member"])
            else:
                self.assertIn(record["source_receipt_sha256"], {r["sha256"] for r in self.contract["receipts"].values()})
        for group in ("vendor_ramdisk", "vendor_dlkm", "system_dlkm"):
            self.assertEqual(receipt["module_sets"][group]["module_count"], 2)
        ramdisk = receipt["module_sets"]["vendor_ramdisk"]
        self.assertEqual(ramdisk["load_list"]["entries"], ["ram_b.ko", "ram_a.ko", "ram_b.ko"])
        self.assertEqual(ramdisk["recovery_load_list"]["entries"], ["ram_a.ko"])
        self.assertEqual((self.output / ramdisk["load_list"]["path"]).read_bytes(), self.cpio_members[2][1])
        vendor = receipt["module_sets"]["vendor_dlkm"]
        self.assertEqual(vendor["load_list"]["entries"], ["zsmalloc.ko", "zram.ko", "zram.ko"])
        self.assertEqual(vendor["modules"], ["modules/vendor_dlkm/zram.ko", "modules/vendor_dlkm/zsmalloc.ko"])
        system = receipt["module_sets"]["system_dlkm"]
        self.assertEqual(system["load_list"]["entries"], ["zsmalloc.ko", "zram.ko", "zsmalloc.ko"])
        self.assertIn(f"modules/system_dlkm/{RELEASE}/kernel/mm/zsmalloc.ko", system["modules"])
        vendor_zram = (self.output / "modules/vendor_dlkm/zram.ko").read_bytes()
        system_zram = (self.output / f"modules/system_dlkm/{RELEASE}/kernel/drivers/block/zram/zram.ko").read_bytes()
        self.assertEqual(vendor_zram, self.vendor_members["/lib/modules/zram.ko"])
        self.assertEqual(system_zram, self.system_members[f"/lib/modules/{RELEASE}/kernel/drivers/block/zram/zram.ko"])
        self.assertNotEqual(vendor_zram, system_zram)
        makefile = (self.output / "kernel-inputs.mk").read_text()
        self.assertIn("NEZHA_STOCK_VENDOR_RAMDISK_MODULES_LOAD := ram_b.ko ram_a.ko ram_b.ko", makefile)
        self.assertIn("NEZHA_STOCK_VENDOR_MODULES_LOAD := zsmalloc.ko zram.ko zram.ko", makefile)
        self.assertIn("NEZHA_STOCK_SYSTEM_MODULES_LOAD := zsmalloc.ko zram.ko zsmalloc.ko", makefile)
        self.assertEqual(before, {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()})
        self.process.assert_not_called()
        self.shell.assert_not_called()

    def test_build_candidate_preserves_failed_avb_and_all_unverified_flags(self):
        receipt = self.package(purpose="build-candidate")
        self.assertEqual(receipt["purpose"], "build-candidate")
        self.assertEqual(receipt["validation"]["input_avb_status"], "failed")
        self.assertFalse(receipt["provenance"]["origin_verified"])
        for key in ("kernel_abi_verified", "module_signatures_verified", "device_tested",
                    "input_avb_reverified_by_packager", "publisher_authenticated_by_packager",
                    "build_verified", "phone_accessed", "firmware_executed"):
            self.assertIs(receipt["validation"][key], False)
        self.assertIn("NEZHA_STOCK_INPUT_AVB_STATUS := failed", (self.output / "kernel-inputs.mk").read_text())

    def test_external_avb_success_requires_a_complete_trusted_key_receipt(self):
        self.contract["validation"]["input_avb_status"] = "verified-external"
        self.assert_rejected()
        self.write_receipt("avb", "avb-verification", {
            "schema_version": 1, "parent_package_sha256": PACKAGE_SHA256,
            "verification_bypass_flags_used": False, "images_padded_or_patched": False,
            "full_avb_verification_passed": True, "trusted_oem_key_supplied": False,
            "inputs_unchanged": True,
        })
        self.assert_rejected()
        self.receipts["avb"]["trusted_oem_key_supplied"] = True
        self.write_receipt("avb", "avb-verification", self.receipts["avb"])
        receipt = self.package()
        self.assertEqual(receipt["validation"]["input_avb_status"], "verified-external")
        self.assertFalse(receipt["validation"]["input_avb_reverified_by_packager"])

    def test_absent_recovery_list_is_unset_without_inventing_a_load_target(self):
        self.cpio_members = [item for item in self.cpio_members
                             if item[0] != "lib/modules/modules.load.recovery"]
        self.update_cpio()
        self.write_boot()
        receipt = self.package()
        self.assertIsNone(receipt["module_sets"]["vendor_ramdisk"]["recovery_load_list"])
        makefile = (self.output / "kernel-inputs.mk").read_text()
        self.assertIn("NEZHA_STOCK_VENDOR_RAMDISK_RECOVERY_MODULES_LOAD := \n", makefile)

    def test_complete_bundle_is_published_only_after_receipt_and_payloads_are_ready(self):
        real_publish = kernel_inputs.publish_new_directory

        def publish(staging, destination):
            self.assertEqual(destination, self.output)
            self.assertFalse(destination.exists())
            receipt = json.loads((staging / "receipt.json").read_bytes())
            for record in receipt["files"]:
                self.assertEqual(sha256((staging / record["path"]).read_bytes()), record["sha256"])
            real_publish(staging, destination)

        with mock.patch.object(kernel_inputs, "publish_new_directory", side_effect=publish) as publisher:
            self.package()
        publisher.assert_called_once()
        self.assertEqual(set(self.output.parent.iterdir()), {self.output})

    def test_publication_failure_cleans_staging_and_lock_without_partial_bundle(self):
        with mock.patch.object(kernel_inputs, "publish_new_directory", side_effect=OSError("publication fixture failure")):
            with self.assertRaises((kernel_inputs.KernelInputsError, OSError)):
                self.package()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])

    def test_destination_created_at_publication_is_not_overwritten(self):
        real_publish = kernel_inputs.publish_new_directory

        def publish(staging, destination):
            destination.mkdir()
            (destination / "preserve.txt").write_text("created by another writer")
            real_publish(staging, destination)

        with mock.patch.object(kernel_inputs, "publish_new_directory", side_effect=publish):
            with self.assertRaises((kernel_inputs.KernelInputsError, OSError)):
                self.package()
        self.assertEqual((self.output / "preserve.txt").read_text(), "created by another writer")
        self.assertEqual({p.name for p in self.output.iterdir()}, {"preserve.txt"})
        self.assertEqual(set(self.output.parent.iterdir()), {self.output})

    def test_make_fragment_is_opt_in_and_does_not_activate_stock_fstab_or_disable_checks(self):
        self.package()
        makefile = (self.output / "kernel-inputs.mk").read_text()
        active_lines = "\n".join(line for line in makefile.splitlines() if not line.lstrip().startswith("#"))
        for variable in ("NEZHA_STOCK_VENDOR_RAMDISK_MODULES", "NEZHA_STOCK_VENDOR_MODULES",
                         "NEZHA_STOCK_SYSTEM_MODULES", "NEZHA_STOCK_VENDOR_RAMDISK_MODULES_LOAD",
                         "NEZHA_STOCK_VENDOR_RAMDISK_RECOVERY_MODULES_LOAD"):
            self.assertIn(variable, makefile)
        self.assertNotIn("fstab", active_lines.lower())
        self.assertNotIn("BOARD_AVB_ENABLE := false", active_lines)
        self.assertNotIn("SELINUX_IGNORE_NEVERALLOWS := true", active_lines)
        self.assertNotIn("androidboot.selinux=permissive", active_lines)
        self.assertEqual(list(self.output.rglob("*fstab*")), [])
        blocklist = self.output / "modules/vendor_dlkm/system_dlkm.modules.blocklist"
        self.assertEqual(blocklist.read_bytes(), b"blocklist zram\nblocklist zsmalloc\n")

    def test_optional_fstab_remains_an_inert_hash_bound_reference(self):
        self.contract["files"].append({"receipt": "boot", "member": "reference/fstab.qcom",
                                       "output": "config/fstab.qcom", "role": "fstab"})
        receipt = self.package()
        self.assertEqual((self.output / "config/fstab.qcom").read_bytes(), self.boot_members["reference/fstab.qcom"])
        self.assertTrue(receipt["ramdisks_and_config_are_reference_only"])
        makefile = (self.output / "kernel-inputs.mk").read_text()
        active_lines = "\n".join(line for line in makefile.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotIn("PRODUCT_COPY_FILES", active_lines)
        self.assertNotIn("TARGET_RECOVERY_FSTAB", active_lines)
        self.assertNotIn("BOARD_VENDOR_RAMDISK_FRAGMENTS", active_lines)

    def test_wrong_device_kernel_identity_and_contract_versions_are_rejected(self):
        changes = [("schema_version", 2), ("device.codename", "other"), ("device.hardware_region", "Global"),
                   ("device.soc", "SM8750"), ("kernel.architecture", "x86_64"),
                   ("kernel.page_size_bytes", 16384), ("kernel.boot_header_version", 3)]
        original = copy.deepcopy(self.contract)
        for key, value in changes:
            with self.subTest(key=key):
                self.contract = copy.deepcopy(original)
                parts = key.split(".")
                target = self.contract if len(parts) == 1 else self.contract[parts[0]]
                target[parts[-1]] = value
                self.assert_rejected()

    def test_receipt_hash_and_selected_payload_hash_tampering_are_rejected(self):
        receipt_path = self.source / "boot/receipt.json"
        original = receipt_path.read_bytes()
        receipt_path.write_bytes(original + b" ")
        self.assert_rejected()
        receipt_path.write_bytes(original)
        self.write_member("boot", "unpacked/boot/kernel", b"tampered")
        self.assert_rejected()

    def test_source_receipt_provenance_mismatch_is_rejected(self):
        original = copy.deepcopy(self.receipts["archive"])
        for field, value in (("device", "other"), ("region", "Global"), ("sha256", "0" * 64)):
            with self.subTest(field=field):
                receipt = copy.deepcopy(original)
                receipt["intake_provenance"][field] = value
                self.write_receipt("archive", "archive-images", receipt)
                self.assert_rejected()

    def test_receipt_member_and_bundle_path_traversal_are_rejected(self):
        original = copy.deepcopy(self.contract)
        for field in ("member", "output"):
            for value in ("../escape", "/absolute", "a/../../escape", "a\\escape", "a/./escape", "a//escape"):
                with self.subTest(field=field, value=value):
                    self.contract = copy.deepcopy(original)
                    self.contract["files"][0][field] = value
                    self.assert_rejected()
        self.contract = copy.deepcopy(original)
        self.contract["receipts"]["boot"]["path"] = "../escape/receipt.json"
        self.assert_rejected()

    def test_duplicate_bundle_outputs_and_unregistered_members_are_rejected(self):
        original = copy.deepcopy(self.contract)
        self.contract["files"][1]["output"] = self.contract["files"][0]["output"]
        self.assert_rejected()
        self.contract = original
        self.contract["files"][0]["member"] = "unregistered.bin"
        self.write_member("boot", "unregistered.bin", synthetic_kernel())
        self.assert_rejected()

    def test_make_expressions_and_control_characters_cannot_enter_bundle_paths(self):
        for value in ("kernel/$(shell touch escaped)", "kernel/x;touch-escaped", "kernel/x\ny",
                      "kernel/with space", "kernel/x:y", "kernel/x#y"):
            with self.subTest(value=value):
                self.contract["files"][0]["output"] = value
                self.assert_rejected()
        self.assertFalse((self.root / "escaped").exists())

    def test_packaging_cannot_assert_abi_signature_or_runtime_validation(self):
        original = copy.deepcopy(self.contract["validation"])
        for key in ("kernel_abi_verified", "module_signatures_verified", "device_tested"):
            with self.subTest(key=key):
                self.contract["validation"] = {**original, key: True}
                self.assert_rejected()

    def test_source_file_and_parent_symlinks_are_rejected(self):
        path = self.source / "boot/unpacked/boot/kernel"
        data = path.read_bytes()
        target = self.root / "kernel-target"
        target.write_bytes(data)
        path.unlink()
        path.symlink_to(target)
        self.assert_rejected()
        path.unlink()
        path.write_bytes(data)
        parent = self.source / "boot/unpacked/boot"
        moved = self.source / "moved-boot"
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        self.assert_rejected()

    def test_nonregular_source_file_is_rejected_without_opening_fifo(self):
        path = self.source / "boot/unpacked/boot/kernel"
        path.unlink()
        os.mkfifo(path)
        self.assert_rejected()

    def test_hardlinked_payload_is_rejected(self):
        path = self.source / "boot/unpacked/boot/kernel"
        os.link(path, self.root / "kernel-hardlink")
        self.assert_rejected()

    def test_output_must_be_new_private_and_outside_source(self):
        self.output.mkdir()
        marker = self.output / "preserve.txt"
        marker.write_text("unchanged")
        with self.assertRaises(kernel_inputs.KernelInputsError):
            self.package()
        self.assertEqual(marker.read_text(), "unchanged")
        self.output = self.root / "public-bundle"
        self.assert_rejected()
        self.output = self.source / "nested-bundle"
        self.assert_rejected()

    def test_output_symlink_and_symlink_parent_are_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.output.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(kernel_inputs.KernelInputsError):
            self.package()
        self.assertEqual(list(outside.iterdir()), [])
        self.output.unlink()
        alias = self.root / "artifacts/alias"
        alias.symlink_to(outside, target_is_directory=True)
        self.output = alias / "bundle"
        self.assert_rejected()

    def test_kernel_magic_release_and_4k_flag_are_required(self):
        for data in (b"not an Image", synthetic_kernel(release="6.12.23-other"), synthetic_kernel(flags=4)):
            with self.subTest(data=data):
                self.boot_members["unpacked/boot/kernel"] = data
                self.write_boot()
                self.assert_rejected()

    def test_required_kernel_security_config_cannot_be_disabled(self):
        original = self.boot_members["kernel.config"]
        for option in ("CONFIG_ARM64_4K_PAGES", "CONFIG_MODULES", "CONFIG_MODVERSIONS",
                       "CONFIG_MODULE_SIG", "CONFIG_DM_VERITY", "CONFIG_SECURITY_SELINUX"):
            with self.subTest(option=option):
                self.boot_members["kernel.config"] = original.replace(f"{option}=y".encode(), f"# {option} is not set".encode())
                self.write_boot()
                self.assert_rejected()

    def test_dtb_compatibility_and_count_are_validated(self):
        for data in (b"wrong magic", synthetic_fdt(compatible="qcom,other"),
                     synthetic_fdt() + synthetic_fdt()):
            with self.subTest(payload_sha256=sha256(data)):
                self.boot_members["unpacked/vendor_boot/dtb"] = data
                self.write_boot()
                self.assert_rejected()

    def test_dtbo_board_ids_and_table_bounds_are_validated(self):
        for data in (b"wrong magic", synthetic_dtbo(synthetic_fdt(board=(7, 0))),
                     synthetic_dtbo(synthetic_fdt(miboard=(4, 0))), synthetic_dtbo()[:-1],
                     synthetic_dtbo(synthetic_fdt(model="Other SM8850")),
                     synthetic_dtbo(synthetic_fdt(model="Nezha SM8750"))):
            with self.subTest(payload_sha256=sha256(data)):
                self.write_member("archive", "dtbo.img", data)
                receipt = self.receipts["archive"]
                receipt["images"][0].update({"size_bytes": len(data), "sha256": sha256(data)})
                self.write_receipt("archive", "archive-images", receipt)
                self.assert_rejected()

    def test_module_hashes_and_architecture_are_validated(self):
        path = self.source / "vendor/files/0001"
        path.write_bytes(path.read_bytes() + b"tampering")
        self.assert_rejected()
        self.write_erofs("vendor", self.vendor_members)
        for offset, value in ((4, 1), (5, 2), (16, 2), (18, 62)):
            with self.subTest(offset=offset):
                module = bytearray(synthetic_module("zram"))
                module[offset] = value
                self.vendor_members["/lib/modules/zram.ko"] = bytes(module)
                self.write_erofs("vendor", self.vendor_members)
                self.assert_rejected()

    def test_cpio_offsets_hashes_types_and_hardlinks_are_validated(self):
        original = self.boot_members["ramdisks/vendor_boot-inventory.json"]
        changes = [("content_offset", -1), ("content_offset", 1 << 40),
                   ("size_bytes", 1 << 40), ("sha256", "0" * 64),
                   ("kind", stat.S_IFLNK), ("nlink", 2), ("name", "../../escape.ko")]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                inventory = json.loads(original)
                inventory["entries"][0][key] = value
                self.boot_members["ramdisks/vendor_boot-inventory.json"] = json.dumps(inventory).encode()
                self.write_boot()
                self.assert_rejected()

    def test_cpio_full_archive_hash_is_checked(self):
        self.boot_members["ramdisks/vendor_boot.cpio"] += b"changed but boot receipt updated"
        self.write_boot()
        self.assert_rejected()

    def test_erofs_paths_types_and_readback_flags_are_validated(self):
        original = copy.deepcopy(self.receipts["vendor"])
        for key, value in (("path", "/lib/modules/../../escape.ko"), ("output_path", "../outside"),
                           ("type", "symlink"), ("readback_verified", False)):
            with self.subTest(key=key):
                receipt = copy.deepcopy(original)
                receipt["files"][0][key] = value
                self.write_receipt("vendor", "erofs-capture", receipt)
                self.assert_rejected()

    def test_same_set_basename_collision_is_rejected_but_cross_set_names_are_preserved(self):
        self.vendor_members["/lib/modules/nested/zram.ko"] = synthetic_module("zram", "collision")
        self.contract["expected_module_counts"]["vendor_dlkm"] = 3
        self.write_erofs("vendor", self.vendor_members)
        self.assert_rejected()

    def test_missing_module_load_target_is_rejected(self):
        self.vendor_members["/lib/modules/modules.load"] += b"missing.ko\n"
        self.write_erofs("vendor", self.vendor_members)
        self.assert_rejected()

    def test_missing_module_load_file_is_rejected(self):
        del self.vendor_members["/lib/modules/modules.load"]
        self.write_erofs("vendor", self.vendor_members)
        self.assert_rejected()

    def test_missing_recovery_module_load_target_is_rejected(self):
        self.cpio_members[-1] = ("lib/modules/modules.load.recovery", b"missing.ko\n")
        self.update_cpio()
        self.write_boot()
        self.assert_rejected()

    def test_expected_module_count_is_enforced(self):
        self.contract["expected_module_counts"]["vendor_ramdisk"] = 3
        self.assert_rejected()

    def test_required_system_blocklist_entries_cannot_be_removed(self):
        for data in (b"blocklist zram\n", b"blocklist zsmalloc\n", b"# blocklist zram\n# blocklist zsmalloc\n"):
            with self.subTest(data=data):
                self.vendor_members["/lib/modules/system_dlkm.modules.blocklist"] = data
                self.write_erofs("vendor", self.vendor_members)
                self.assert_rejected()

    def test_missing_required_blocklist_file_is_rejected(self):
        del self.vendor_members["/lib/modules/system_dlkm.modules.blocklist"]
        self.write_erofs("vendor", self.vendor_members)
        self.assert_rejected()

    def test_unknown_purpose_and_trust_status_are_rejected(self):
        self.assert_rejected(purpose="flash-now")
        self.contract["validation"]["input_avb_status"] = "verification-disabled"
        self.assert_rejected()


if __name__ == "__main__":
    unittest.main()
