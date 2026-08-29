"""Synthetic, offline wrapper tests: no stock bytes, signing, keys, or devices."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import inspect_twrp_ram_boot as inspector


def _pad(data, alignment=4096):
    return data + bytes((-len(data)) % alignment)


def _property(key, value):
    following = (16 + len(key) + 1 + len(value) + 1 + 7) // 8 * 8
    return _pad(struct.pack(">4Q", 0, following, len(key), len(value)) + key + b"\0" + value + b"\0", 8)


def _fixture(*, salt=b"s" * 32, properties=None, header_version=4, command_line=None,
             directory_scaffold=False, prefix=None, suffix=None):
    kernel = b"SYNTHETIC KERNEL" * 277  # Crosses one page; not executable code.
    block = b"\x50hello"
    if suffix is None:
        suffix = b"\x02\x21\x4c\x18" + struct.pack("<I", len(block)) + block
    if directory_scaffold:
        prefix = inspector.scaffold.build_scaffold_prefix() if prefix is None else prefix
        ramdisk = prefix + suffix
    else:
        ramdisk = suffix
    header = bytearray(4096)
    header_size = 1580 if header_version == 3 else 1584
    if command_line is None:
        command_line = inspector.V3_COMMAND_LINE if header_version == 3 else ""
    struct.pack_into("<8s9I", header, 0, b"ANDROID!", len(kernel), len(ramdisk), 0, header_size, 0, 0, 0, 0, header_version)
    header[44:44 + len(command_line)] = command_line.encode("ascii")
    unsigned = bytes(header) + _pad(kernel) + _pad(ramdisk)
    digest = hashlib.sha256(salt + unsigned).digest()
    hash_size = (132 + 4 + len(salt) + 32 + 7) // 8 * 8
    descriptor = inspector.HASH_DESCRIPTOR.pack(2, hash_size - 16, len(unsigned), b"sha256", 4, len(salt), 32, 0, bytes(60))
    descriptors = _pad(descriptor + b"boot" + salt + digest, 8)
    if properties is None:
        properties = list(inspector.EXPECTED_PROPERTIES.items())
    descriptors += b"".join(_property(k, v) for k, v in properties)
    key = struct.pack(">II", 4096, 0) + bytes(1024)  # Deliberately invalid RSA key.
    auxiliary = _pad(descriptors + key, 64)
    vbmeta_header = bytearray(256)
    struct.pack_into(">4sIIQQI", vbmeta_header, 0, b"AVB0", 1, 0, 576, len(auxiliary), 2)
    struct.pack_into(">10Q", vbmeta_header, 32, 0, 32, 32, 512, len(descriptors), len(key),
                     len(descriptors) + len(key), 0, 0, len(descriptors))
    struct.pack_into(">QII", vbmeta_header, 112, inspector.ROLLBACK_INDEX, 0, 0)
    vbmeta_header[128:143] = b"synthetic-test\0"
    # This hash is valid; the opaque 512-byte signature intentionally is not.
    auth = hashlib.sha256(bytes(vbmeta_header) + auxiliary).digest() + b"S" * 512 + bytes(32)
    vbmeta = bytes(vbmeta_header) + auth + auxiliary
    image_size = len(unsigned) + len(_pad(vbmeta)) + 4096
    footer = inspector.envelope.AVB_FOOTER.pack(b"AVBf", 1, 0, len(unsigned), len(unsigned), len(vbmeta), bytes(28))
    image = unsigned + vbmeta + bytes(image_size - len(unsigned) - len(vbmeta) - len(footer)) + footer
    contract = inspector.RamBootContract(image_size, len(kernel), hashlib.sha256(kernel).hexdigest(),
                                         len(ramdisk), hashlib.sha256(ramdisk).hexdigest(), header_version, command_line,
                                         directory_scaffold, len(suffix) if directory_scaffold else None,
                                         hashlib.sha256(suffix).hexdigest() if directory_scaffold else None)
    offsets = {"vbmeta": len(unsigned), "auth": len(unsigned) + 256, "aux": len(unsigned) + 832,
               "hash_size": hash_size, "desc_size": len(descriptors), "vbmeta_size": len(vbmeta),
               "kernel_end": 4096 + len(kernel), "ramdisk": 4096 + len(_pad(kernel)),
               "ramdisk_end": 4096 + len(_pad(kernel)) + len(ramdisk)}
    return image, contract, offsets


def _mutate(image, offset, value, fmt=None):
    changed = bytearray(image)
    if fmt:
        struct.pack_into(fmt, changed, offset, value)
    else:
        changed[offset:offset + len(value)] = value
    return bytes(changed)


def _rehash_auth(image, offsets):
    """Synthetic fixture helper, not a signature or artifact verification."""
    v, a = offsets["vbmeta"], offsets["aux"]
    digest = hashlib.sha256(image[v:v + 256] + image[a:v + offsets["vbmeta_size"]]).digest()
    return _mutate(image, offsets["auth"], digest)


class RamBootParserTests(unittest.TestCase):
    def setUp(self):
        self.image, self.contract, self.offsets = _fixture()

    def parse(self, image=None, contract=None):
        return inspector.inspect_bytes(self.image if image is None else image,
                                       contract=self.contract if contract is None else contract)

    def reject(self, image, pattern=None):
        if pattern:
            with self.assertRaisesRegex(inspector.RamBootInspectionError, pattern): self.parse(image)
        else:
            with self.assertRaises(inspector.RamBootInspectionError): self.parse(image)

    def test_exact_spans_hashes_and_boot_descriptor_are_reported(self):
        r = self.parse()
        self.assertEqual(r["image"], {"size_bytes": len(self.image), "sha256": hashlib.sha256(self.image).hexdigest()})
        self.assertEqual(r["kernel"]["offset_bytes"], 4096)
        self.assertEqual(r["kernel"]["end_offset_bytes"], self.offsets["kernel_end"])
        self.assertEqual(r["kernel"]["sha256"], self.contract.kernel_sha256)
        self.assertEqual(r["ramdisk"]["offset_bytes"], self.offsets["ramdisk"])
        self.assertEqual(r["ramdisk"]["end_offset_bytes"], self.offsets["ramdisk_end"])
        self.assertEqual(r["ramdisk"]["sha256"], self.contract.ramdisk_sha256)
        self.assertEqual(r["header"]["padded_payload_size_bytes"], self.offsets["vbmeta"])
        avb = r["avb"]
        self.assertEqual(avb["original_image_size_bytes"], self.offsets["vbmeta"])
        self.assertEqual(avb["hash_descriptor"]["image_size_bytes"], self.offsets["vbmeta"])
        self.assertEqual(avb["hash_descriptor"]["digest_hex"], hashlib.sha256(b"s" * 32 + self.image[:self.offsets["vbmeta"]]).hexdigest())
        self.assertEqual(avb["hash_descriptor"]["partition_name"], "boot")
        self.assertTrue(avb["hash_descriptor"]["digest_verified"])
        self.assertTrue(avb["vbmeta"]["authentication_hash_verified"])
        self.assertTrue(all(d["payload_semantics_parsed"] for d in avb["vbmeta"]["descriptor_headers"]))
        self.assertEqual(avb["properties"], {k.decode(): v.decode() for k, v in inspector.EXPECTED_PROPERTIES.items()})

    def test_synthetic_key_and_signature_do_not_establish_trust_or_runtime(self):
        r = self.parse()
        for field in ("signature_verified", "trusted_key_verified", "avb_trusted", "boot_tested", "authenticated_adb_verified",
                      "runtime_verified", "rollback_compatibility_verified", "device_compatibility_verified", "flash_admitted",
                      "phone_accessed", "image_mutated", "stock_kernel_build66_payloads_verified", "twrp_contents_verified"):
            self.assertIs(r["validation"][field], False, field)
        self.assertFalse(r["avb"]["signature_verified"])
        self.assertFalse(r["avb"]["public_key"]["trusted_key_verified"])
        altered_signature = _mutate(self.image, self.offsets["auth"] + 32, b"X")
        self.assertFalse(self.parse(altered_signature)["validation"]["signature_verified"])

    def test_actual_contract_pins_are_fixed_and_not_selected_by_synthetic_input(self):
        expected = inspector.EXPECTED_CONTRACT
        self.assertEqual(expected.image_size_bytes, 100663296)
        self.assertEqual(expected.kernel_size_bytes, 39963136)
        self.assertEqual(expected.kernel_sha256, "4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8")
        self.assertEqual(expected.ramdisk_size_bytes, 25192233)
        self.assertEqual(expected.ramdisk_sha256, "8713a11b399bec1704bec14f1d06869ec6e615bbaed851945a2ef0e4b74db333")
        with self.assertRaises(inspector.RamBootInspectionError): inspector.inspect_bytes(self.image)

    def test_pure_parser_cannot_read_files_or_call_process_network_or_time(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            a, b = self.parse(), self.parse()
        self.assertEqual(a, b)

    def test_bad_contracts_and_mutable_inputs_are_rejected(self):
        for contract in (None, {}, replace(self.contract, image_size_bytes=True), replace(self.contract, image_size_bytes=4096),
                         replace(self.contract, image_size_bytes=100663297), replace(self.contract, kernel_size_bytes=0),
                         replace(self.contract, kernel_sha256="A" * 64), replace(self.contract, ramdisk_sha256="bad")):
            with self.subTest(contract=contract), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(self.image, contract=contract)
        for data in (bytearray(self.image), memoryview(self.image), "image"):
            with self.subTest(type=type(data)), self.assertRaises(inspector.RamBootInspectionError):
                self.parse(data)

    def test_header_magic_versions_sizes_os_and_signature_are_exact(self):
        self.reject(_mutate(self.image, 0, b"VNDRBOOT"))
        for offset, value in ((8, 0), (8, 0xFFFFFFFF), (12, 0), (12, 0xFFFFFFFF), (16, 1), (20, 1580), (40, 3), (1580, 4096)):
            with self.subTest(offset=offset, value=value): self.reject(_mutate(self.image, offset, value, "<I"))
        for image in (self.image[:-1], self.image + b"\0", self.image + bytes(4096)):
            self.reject(image, "image size")

    def test_header_reserved_cmdline_and_payload_padding_must_be_zero(self):
        for offset in (24, 39, 44, 1579, 1584, 4095, self.offsets["kernel_end"], self.offsets["ramdisk_end"], len(self.image) - 65):
            with self.subTest(offset=offset): self.reject(_mutate(self.image, offset, b"x"), "nonzero")

    def test_each_payload_hash_is_checked(self):
        self.reject(_mutate(self.image, 4096, b"X"), "kernel SHA256")
        self.reject(_mutate(self.image, self.offsets["ramdisk"] + 9, b"X"), "ramdisk SHA256")
        for name in ("kernel_sha256", "ramdisk_sha256"):
            with self.subTest(name=name), self.assertRaises(inspector.RamBootInspectionError):
                self.parse(contract=replace(self.contract, **{name: "0" * 64}))

    def test_footer_version_reserved_and_exact_offsets_are_required(self):
        start = len(self.image) - 64
        self.reject(_mutate(self.image, start, b"NOPE"))
        for offset, value, fmt in ((4, 2, ">I"), (8, 1, ">I"), (12, self.offsets["vbmeta"] - 4096, ">Q"),
                                   (20, self.offsets["vbmeta"] - 4096, ">Q"), (28, 128, ">Q")):
            with self.subTest(offset=offset): self.reject(_mutate(self.image, start + offset, value, fmt))
        self.reject(_mutate(self.image, start + 36, b"x"), "footer")

    def test_avb_algorithm_flags_rollback_and_versions_are_exact(self):
        v = self.offsets["vbmeta"]
        for offset, value, fmt in ((4, 2, ">I"), (8, 1, ">I"), (28, 1, ">I"), (112, 0, ">Q"),
                                   (120, 1, ">I"), (124, 1, ">I")):
            with self.subTest(offset=offset): self.reject(_rehash_auth(_mutate(self.image, v + offset, value, fmt), self.offsets))

    def test_authentication_and_auxiliary_ranges_and_padding_are_checked(self):
        v, a = self.offsets["vbmeta"], self.offsets["aux"]
        for offset, value in ((32, 1), (40, 0), (56, 256), (64, 0), (72, 1031), (88, 1), (96, 8)):
            with self.subTest(offset=offset): self.reject(_rehash_auth(_mutate(self.image, v + offset, value, ">Q"), self.offsets))
        for offset in (v + 175, v + 176, self.offsets["auth"] + 544, v + self.offsets["vbmeta_size"] - 1):
            with self.subTest(padding=offset): self.reject(_rehash_auth(_mutate(self.image, offset, b"x"), self.offsets), "nonzero")
        self.reject(_rehash_auth(_mutate(self.image, a + self.offsets["desc_size"], 2048, ">I"), self.offsets), "bit count")
        self.reject(_mutate(self.image, self.offsets["auth"], b"x"), "authentication hash")

    def test_boot_hash_descriptor_algorithm_sizes_flags_and_reserved_are_checked(self):
        a = self.offsets["aux"]
        for offset, value, fmt in ((0, 1, ">Q"), (8, 8, ">Q"), (16, self.offsets["vbmeta"] - 1, ">Q"),
                                   (56, 3, ">I"), (60, 31, ">I"), (64, 0, ">I"), (68, 1, ">I")):
            with self.subTest(offset=offset): self.reject(_rehash_auth(_mutate(self.image, a + offset, value, fmt), self.offsets))
        for offset, value in ((24, b"sha512"), (72, b"x"), (132, b"evil")):
            with self.subTest(offset=offset): self.reject(_rehash_auth(_mutate(self.image, a + offset, value), self.offsets))
        self.reject(_rehash_auth(_mutate(self.image, a + 132 + 4 + 32, b"x"), self.offsets), "salted boot image digest")

    def test_salt_is_bounded_by_descriptor_and_hash_padding_is_zero(self):
        for salt in (b"", b"x", b"x" * 64):
            image, contract, offsets = _fixture(salt=salt)
            r = inspector.inspect_bytes(image, contract=contract)
            self.assertEqual(r["avb"]["hash_descriptor"]["salt_size_bytes"], len(salt))
            if len(salt) == 1:
                bad = _mutate(image, offsets["aux"] + offsets["hash_size"] - 1, b"x")
                with self.assertRaisesRegex(inspector.RamBootInspectionError, "padding"):
                    inspector.inspect_bytes(_rehash_auth(bad, offsets), contract=contract)

    def test_boot_properties_are_exact_terminated_and_unique(self):
        props = list(inspector.EXPECTED_PROPERTIES.items())
        cases = ([], props[:1], props + [(b"com.android.build.boot.fingerprint", b"invented")],
                 [props[0], props[0]], [(props[0][0], b"15"), props[1]])
        for properties in cases:
            image, contract, _ = _fixture(properties=properties)
            with self.subTest(properties=properties), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(image, contract=contract)
        first = self.offsets["aux"] + self.offsets["hash_size"]
        for offset in (first + 32 + len(props[0][0]), first + len(_property(*props[0])) - 1):
            self.reject(_rehash_auth(_mutate(self.image, offset, b"x"), self.offsets), "terminator|padding")
        self.reject(_rehash_auth(_mutate(self.image, first, 99, ">Q"), self.offsets))


class RamBootV3Tests(unittest.TestCase):
    def setUp(self):
        self.image, self.contract, self.offsets = _fixture(header_version=3)

    def test_v3_report_has_exact_command_line_and_no_absent_signature_field(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            report = inspector.inspect_bytes(self.image, contract=self.contract)
        header = report["header"]
        self.assertEqual((header["version"], header["size_bytes"], header["page_size_bytes"]), (3, 1580, 4096))
        self.assertEqual(header["command_line"], inspector.V3_COMMAND_LINE)
        self.assertEqual(header["command_line_size_bytes"], 269)
        self.assertFalse(header["command_line_empty"])
        self.assertEqual(header["command_line_sha256"], hashlib.sha256(inspector.V3_COMMAND_LINE.encode("ascii")).hexdigest())
        self.assertNotIn("boot_signature_size_bytes", header)
        self.assertTrue(report["avb"]["hash_descriptor"]["digest_verified"])
        for key in ("signature_verified", "trusted_key_verified", "avb_trusted", "boot_tested", "runtime_verified", "authenticated_adb_verified", "flash_admitted"):
            self.assertIs(report["validation"][key], False)

    def test_v3_and_default_v4_contracts_differ_only_in_header_and_command_line(self):
        v3, v4 = inspector.V3_EXPECTED_CONTRACT, inspector.EXPECTED_CONTRACT
        self.assertEqual(v4.header_version, 4)
        self.assertEqual(v4.command_line, "")
        self.assertEqual(replace(v3, header_version=4, command_line=""), v4)
        self.assertEqual(v3.command_line.split(" "), [
            "androidboot.hardware=qcom", "androidboot.memcg=1", "androidboot.usbcontroller=a600000.dwc3",
            "androidboot.load_modules_parallel=true", "androidboot.hypervisor.protected_vm.supported=true",
            "androidboot.hypervisor.version=gunyah", "androidboot.vendor.qspa=true", "androidboot.serialconsole=0",
        ])
        self.assertEqual(v3.command_line, v3.command_line.strip())
        self.assertEqual(len(v3.command_line.encode("ascii")), 269)

    def test_header_version_mismatch_never_auto_selects_another_contract(self):
        v4_image, v4_contract, _ = _fixture()
        for data, expected in ((self.image, v4_contract), (v4_image, self.contract)):
            with self.subTest(version=expected.header_version), self.assertRaisesRegex(inspector.RamBootInspectionError, "expected Android header"):
                inspector.inspect_bytes(data, contract=expected)
        with self.assertRaises(inspector.RamBootInspectionError):
            inspector.inspect_bytes(self.image)

    def test_v3_header_size_padding_os_and_reserved_bytes_remain_strict(self):
        for offset, value in ((20, 1584), (40, 4), (16, 1), (24, 1), (1580, 1), (4092, 1)):
            changed = _mutate(self.image, offset, value, "<I")
            with self.subTest(offset=offset), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(changed, contract=self.contract)

    def test_changed_missing_extra_and_unknown_security_flags_are_rejected(self):
        line = inspector.V3_COMMAND_LINE
        changes = ("", line + " ", " " + line, line.replace("memcg=1", "memcg=0"),
                   line.replace("serialconsole=0", "serialconsole=1"), line + " androidboot.selinux=permissive",
                   line + " androidboot.verifiedbootstate=orange", line + "\0hidden")
        for changed_line in changes:
            changed = _mutate(self.image, 44, changed_line.encode("ascii").ljust(1536, b"\0"))
            with self.subTest(command_line=changed_line), self.assertRaisesRegex(inspector.RamBootInspectionError, "command line"):
                inspector.inspect_bytes(changed, contract=self.contract)

    def test_explicit_test_contract_cannot_authorize_unreviewed_flags(self):
        for contract in (replace(self.contract, command_line=""),
                         replace(self.contract, command_line=inspector.V3_COMMAND_LINE + " androidboot.selinux=permissive"),
                         replace(self.contract, header_version=4), replace(self.contract, header_version=True),
                         replace(self.contract, header_version=2)):
            with self.subTest(contract=contract), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(self.image, contract=contract)

    def test_v3_does_not_relax_kernel_ramdisk_or_avb_checks(self):
        for changed in (_mutate(self.image, 4096, b"X"),
                        _mutate(self.image, self.offsets["ramdisk"] + 9, b"X"),
                        _rehash_auth(_mutate(self.image, self.offsets["vbmeta"] + 120, 1, ">I"), self.offsets)):
            with self.subTest(), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(changed, contract=self.contract)

    def test_cli_requires_explicit_v3_selection_and_keeps_v4_default(self):
        path = Path("synthetic-only.img")
        report = inspector.inspect_bytes(self.image, contract=self.contract)
        for args, expected in (([str(path)], inspector.EXPECTED_CONTRACT),
                               ([str(path), "--header-version", "4"], inspector.EXPECTED_CONTRACT),
                               ([str(path), "--header-version", "3"], inspector.V3_EXPECTED_CONTRACT)):
            with self.subTest(args=args), mock.patch.object(inspector, "inspect_image", return_value=report) as read, redirect_stdout(io.StringIO()):
                self.assertEqual(inspector.main(args), 0)
                read.assert_called_once_with(path, contract=expected)
        with mock.patch.object(inspector, "inspect_image") as read, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            inspector.main([str(path), "--header-version", "2"])
        self.assertEqual(caught.exception.code, 2)
        read.assert_not_called()


class RamBootScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.image, self.contract, self.offsets = _fixture(header_version=3, directory_scaffold=True)

    def test_explicit_scaffold_reports_exact_prefix_and_unmodified_suffix_separately(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            report = inspector.inspect_bytes(self.image, contract=self.contract)
        ramdisk = report["ramdisk"]
        self.assertEqual(ramdisk["compression"]["format"], "concatenated-lz4-legacy-archives")
        self.assertEqual(ramdisk["compression"]["archive_count"], 2)
        self.assertEqual(ramdisk["scaffold"]["prefix_size_bytes"], 1037)
        self.assertEqual(ramdisk["scaffold"]["prefix_sha256"], "b06e73b4444e3d31f6ea48e9a65c2a673cf3a58ee70a72f23a3665249d29f40d")
        self.assertEqual(ramdisk["canonical_suffix"]["size_bytes"], self.contract.ramdisk_suffix_size_bytes)
        self.assertEqual(ramdisk["canonical_suffix"]["sha256"], self.contract.ramdisk_suffix_sha256)
        self.assertEqual(ramdisk["canonical_suffix"]["image_offset_bytes"], self.offsets["ramdisk"] + 1037)
        self.assertEqual(ramdisk["canonical_suffix"]["compression"]["format"], "lz4-legacy")
        self.assertFalse(ramdisk["canonical_suffix"]["build66_bytes_verified"])
        self.assertTrue(report["validation"]["directory_scaffold_verified"])
        self.assertTrue(report["avb"]["hash_descriptor"]["digest_verified"])
        self.assertNotIn("boot_signature_size_bytes", report["header"])
        for key in ("full_kernel_decompression_verified", "ramdisk_decompressed", "twrp_contents_verified", "runtime_verified", "boot_tested", "flash_admitted"):
            self.assertIs(report["validation"][key], False)

    def test_production_scaffold_contract_keeps_kernel_header_commandline_and_canonical_suffix(self):
        contract = inspector.V3_SCAFFOLD_EXPECTED_CONTRACT
        self.assertTrue(contract.scaffold)
        self.assertEqual(contract.header_version, 3)
        self.assertEqual(contract.command_line, inspector.V3_COMMAND_LINE)
        self.assertEqual(contract.ramdisk_size_bytes, 25193270)
        self.assertEqual(contract.ramdisk_sha256, "1f1c61c9c8d473d1e9753cc971c13e0d71b23318e6080e5e9615bec7b5d196ff")
        self.assertEqual(contract.ramdisk_suffix_size_bytes, 25192233)
        self.assertEqual(contract.ramdisk_suffix_sha256, "8713a11b399bec1704bec14f1d06869ec6e615bbaed851945a2ef0e4b74db333")
        base = replace(contract, ramdisk_size_bytes=contract.ramdisk_suffix_size_bytes,
                       ramdisk_sha256=contract.ramdisk_suffix_sha256, scaffold=False,
                       ramdisk_suffix_size_bytes=None, ramdisk_suffix_sha256=None)
        self.assertEqual(base, inspector.V3_EXPECTED_CONTRACT)
        self.assertEqual(inspector.envelope._aligned(contract.ramdisk_size_bytes),
                         inspector.envelope._aligned(base.ramdisk_size_bytes))

    def test_prefix_mutations_fail_even_when_composite_contract_hash_is_updated(self):
        original = inspector.scaffold.build_scaffold_prefix()
        for offset in (0, 4, 8, 13 + 14, 13 + 110, 1036):
            prefix = _mutate(original, offset, bytes([original[offset] ^ 1]))
            image, contract, _ = _fixture(header_version=3, directory_scaffold=True, prefix=prefix)
            with self.subTest(offset=offset), self.assertRaisesRegex(inspector.RamBootInspectionError, "scaffold prefix"):
                inspector.inspect_bytes(image, contract=contract)

    def test_suffix_mutation_fails_even_when_composite_contract_hash_is_updated(self):
        changed = _mutate(self.image, self.offsets["ramdisk"] + 1037 + 9, b"X")
        combined = changed[self.offsets["ramdisk"]:self.offsets["ramdisk_end"]]
        contract = replace(self.contract, ramdisk_sha256=hashlib.sha256(combined).hexdigest())
        with self.assertRaisesRegex(inspector.RamBootInspectionError, "suffix differs"):
            inspector.inspect_bytes(changed, contract=contract)

    def test_suffix_envelope_is_still_checked_and_requires_legacy_lz4(self):
        for suffix in (b"070701" + bytes(20), b"\x02\x21\x4c\x18" + struct.pack("<I", 9999) + b"x"):
            image, contract, _ = _fixture(header_version=3, directory_scaffold=True, suffix=suffix)
            with self.subTest(suffix=suffix), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(image, contract=contract)

    def test_plain_v3_never_autodetects_concatenated_scaffold(self):
        plain = replace(self.contract, scaffold=False, ramdisk_suffix_size_bytes=None, ramdisk_suffix_sha256=None)
        with self.assertRaises(inspector.RamBootInspectionError):
            inspector.inspect_bytes(self.image, contract=plain)
        original, original_contract, _ = _fixture(header_version=3)
        wrong = replace(original_contract, scaffold=True, ramdisk_suffix_size_bytes=original_contract.ramdisk_size_bytes,
                        ramdisk_suffix_sha256=original_contract.ramdisk_sha256)
        with self.assertRaises(inspector.RamBootInspectionError):
            inspector.inspect_bytes(original, contract=wrong)

    def test_scaffold_contract_types_sizes_and_version_are_strict(self):
        for contract in (replace(self.contract, scaffold=1), replace(self.contract, header_version=4, command_line=""),
                         replace(self.contract, ramdisk_suffix_size_bytes=True), replace(self.contract, ramdisk_suffix_size_bytes=1),
                         replace(self.contract, ramdisk_suffix_sha256="bad"), replace(self.contract, scaffold=False)):
            with self.subTest(contract=contract), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(self.image, contract=contract)

    def test_scaffold_does_not_relax_header_or_avb_gates(self):
        for changed in (_mutate(self.image, 44, b"X"), _mutate(self.image, 4096, b"X"),
                        _rehash_auth(_mutate(self.image, self.offsets["vbmeta"] + 120, 1, ">I"), self.offsets)):
            with self.subTest(), self.assertRaises(inspector.RamBootInspectionError):
                inspector.inspect_bytes(changed, contract=self.contract)

    def test_cli_scaffold_is_an_explicit_v3_only_opt_in(self):
        path = Path("synthetic-only.img")
        report = inspector.inspect_bytes(self.image, contract=self.contract)
        with mock.patch.object(inspector, "inspect_image", return_value=report) as read, redirect_stdout(io.StringIO()):
            self.assertEqual(inspector.main([str(path), "--header-version", "3", "--scaffold"]), 0)
            read.assert_called_once_with(path, contract=inspector.V3_SCAFFOLD_EXPECTED_CONTRACT)
        for args in ([str(path), "--scaffold"], [str(path), "--header-version", "4", "--scaffold"]):
            with self.subTest(args=args), mock.patch.object(inspector, "inspect_image") as read, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                inspector.main(args)
            self.assertEqual(caught.exception.code, 2)
            read.assert_not_called()


class RamBootFileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.path = self.root / "synthetic.img"
        self.image, self.contract, _ = _fixture()
        self.path.write_bytes(self.image)

    def inspect(self, path=None):
        return inspector.inspect_image(self.path if path is None else path, contract=self.contract)

    def test_file_read_is_stable_and_does_not_mutate_input(self):
        r = self.inspect()
        self.assertTrue(r["validation"]["input_stable_during_read"])
        self.assertEqual(r["image"]["name"], "synthetic.img")
        self.assertEqual(self.path.read_bytes(), self.image)

    def test_file_and_parent_symlinks_and_directories_are_rejected(self):
        link = self.root / "link.img"; link.symlink_to(self.path)
        parent = self.root / "linked-parent"; parent.symlink_to(self.root, target_is_directory=True)
        for path in (link, parent / self.path.name, self.root):
            with self.subTest(path=path), self.assertRaises((inspector.RamBootInspectionError, OSError)):
                self.inspect(path)

    def test_fifo_is_rejected_without_opening_or_blocking(self):
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(inspector.RamBootInspectionError, "regular"):
            self.inspect(fifo)

    def test_wrong_size_is_rejected_before_reading(self):
        self.path.write_bytes(b"small")
        with mock.patch.object(os, "fdopen", side_effect=AssertionError("must not read")):
            with self.assertRaisesRegex(inspector.RamBootInspectionError, "image size"):
                self.inspect()

    def test_file_mutation_during_parse_is_rejected(self):
        parse = inspector.inspect_bytes
        def mutate(data, *, contract):
            result = parse(data, contract=contract)
            self.path.write_bytes(data[:-1])
            return result
        with mock.patch.object(inspector, "inspect_bytes", side_effect=mutate):
            with self.assertRaisesRegex(inspector.RamBootInspectionError, "changed while"):
                self.inspect()

    def test_cli_prints_metadata_and_creates_only_exclusive_json(self):
        output = self.root / "metadata.json"
        report = self.inspect()
        with mock.patch.object(inspector, "inspect_image", return_value=report), redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(inspector.main([str(self.path), "--output", str(output)]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), report)
        self.assertEqual(json.loads(output.read_bytes()), report)
        with mock.patch.object(inspector, "inspect_image", return_value=report), redirect_stderr(io.StringIO()):
            self.assertEqual(inspector.main([str(self.path), "--output", str(output)]), 2)
        self.assertEqual(self.path.read_bytes(), self.image)

    def test_cli_failure_emits_no_success_json(self):
        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
            self.assertEqual(inspector.main([str(self.path)]), 2)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
