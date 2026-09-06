"""Offline checks for the OTA package inspector against synthetic A/B packages."""

import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import ota_package as ota


def varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def vint(number, value):
    return varint(number << 3) + varint(value)


def ld(number, data):
    return varint(number << 3 | 2) + varint(len(data)) + data


def partition_info(size, digest):
    return vint(1, size) + ld(2, digest)


def partition(name, size, digest, operations=(8, 8), old=None):
    body = ld(1, name.encode())
    if old is not None:
        body += ld(6, partition_info(*old))
    body += ld(7, partition_info(size, digest))
    for kind in operations:
        body += ld(8, vint(1, kind))
    body += ld(17, b"2")
    return ld(13, body)


def b64(hex_digest):
    return base64.b64encode(bytes.fromhex(hex_digest)).decode()


class PackageBuilder:
    def __init__(self, root):
        self.root = root
        self.images = {"boot": b"boot image bytes" * 64, "system": b"system image bytes" * 128,
                       "vbmeta": b"vbmeta bytes" * 8}
        self.digests = {name: hashlib.sha256(raw).hexdigest() for name, raw in self.images.items()}
        self.metadata = ("ota-type=AB\npost-build=Xiaomi/lineage_nezha/nezha:16/BP4A.251205.006/nezha.x:user/test-keys\n"
                         "post-timestamp=1788000000\npre-device=nezha\npost-security-patch-level=2026-02-01\n")
        self.comment = b"\x00" * 10 + struct.pack("<HHH", 16, 0xFFFF, 16)
        self.old = {}

    def manifest(self, names=("boot", "system", "vbmeta")):
        body = vint(3, 4096) + vint(12, 0)
        for name in names:
            body += partition(name, len(self.images[name]), bytes.fromhex(self.digests[name]), old=self.old.get(name))
        body += vint(14, 1788000000)
        group = ld(1, b"qti_dynamic_partitions") + vint(2, 15290335232) + ld(3, b"system")
        body += ld(15, ld(1, group) + vint(2, 1) + vint(3, 0) + vint(5, 3))
        body += ld(18, b"2026-02-01")
        return body

    def build(self, name="ota.zip", *, names=("boot", "system", "vbmeta"), magic=b"CrAU",
              file_hash=None, comment=None):
        manifest = self.manifest(names)
        payload = ota.HEADER.pack(magic, 2, len(manifest), 0) + manifest + b"payload data" * 1000
        metadata_size = ota.HEADER.size + len(manifest)
        properties = (f"FILE_HASH={file_hash or b64(hashlib.sha256(payload).hexdigest())}\n"
                      f"FILE_SIZE={len(payload)}\n"
                      f"METADATA_HASH={b64(hashlib.sha256(payload[:metadata_size]).hexdigest())}\n"
                      f"METADATA_SIZE={metadata_size}\n")
        path = self.root / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(ota.METADATA, self.metadata)
            archive.writestr(ota.PAYLOAD, payload)
            archive.writestr(ota.PROPERTIES, properties)
            archive.writestr("care_map.pb", b"\x00")
            archive.comment = self.comment if comment is None else comment
        return path

    def inventory(self, name="published-inventory.json", overrides=None):
        rows = {n: {"sha256": self.digests[n], "size_bytes": len(self.images[n])} for n in self.images}
        rows.update(overrides or {})
        record = {"final_images": {k: rows[k] for k in ("boot", "system")},
                  "generated_vbmeta_images": {"vbmeta": rows["vbmeta"]},
                  "partition_lists": {"ab_partitions": ["boot", "system", "vbmeta"]}}
        path = self.root / name
        path.write_text(json.dumps(record))
        return path


class OtaPackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.builder = PackageBuilder(self.root)
        self.enterContext(mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")))

    def test_full_package_parses_and_matches_the_published_inventory(self):
        package = self.builder.build()
        report = ota.inspect(package, self.builder.inventory())
        self.assertTrue(report["structurally_consistent"])
        self.assertTrue(report["matches_inventory"])
        self.assertTrue(report["manifest"]["is_full_update"])
        self.assertFalse(report["incremental"])
        dynamic = report["manifest"]["dynamic_partition_metadata"]
        self.assertEqual((dynamic["cow_version"], dynamic["snapshot_enabled"], dynamic["vabc_enabled"]), (3, True, False))
        self.assertEqual(dynamic["groups"][0]["partitions"], ["system"])
        boot = report["manifest"]["partitions"][0]
        self.assertEqual(boot["name"], "boot")
        self.assertEqual(boot["operation_types"], {"REPLACE_XZ": 2})
        self.assertEqual(boot["new"]["sha256"], self.builder.digests["boot"])
        self.assertEqual(report["manifest"]["security_patch_level"], "2026-02-01")
        self.assertTrue(report["whole_file_signature"]["present"])
        self.assertFalse(report["whole_file_signature"]["cryptographically_verified_here"])
        self.assertTrue(report["optional_members"]["care_map.pb"])
        self.assertFalse(any(report["scope"].values()))
        code = ota.main(["inspect", "--package", str(package), "--published-inventory",
                         str(self.root / "published-inventory.json"), "--output", str(self.root / "report.json")])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "report.json").is_file())
        self.assertEqual(ota.main(["inspect", "--package", str(package), "--output", str(self.root / "report.json")]), 2)

    def test_hash_mismatch_and_missing_partitions_are_reported(self):
        package = self.builder.build()
        inventory = self.builder.inventory(overrides={"system": {"sha256": "e" * 64, "size_bytes": 1}})
        report = ota.inspect(package, inventory)
        self.assertFalse(report["matches_inventory"])
        self.assertEqual([row["name"] for row in report["inventory_comparison"]["mismatched"]], ["system"])
        self.assertEqual(ota.main(["inspect", "--package", str(package), "--published-inventory", str(inventory)]), 1)
        partial = self.builder.build("partial.zip", names=("boot", "system"))
        report = ota.inspect(partial, self.builder.inventory())
        self.assertEqual(report["inventory_comparison"]["missing_from_payload"], ["vbmeta"])
        self.assertFalse(report["matches_inventory"])

    def test_property_hash_mismatch_and_bad_magic_are_detected(self):
        package = self.builder.build(file_hash=b64("a" * 64))
        report = ota.inspect(package)
        self.assertFalse(report["property_checks"]["file_hash_matches"])
        self.assertTrue(report["property_checks"]["metadata_hash_matches"])
        self.assertFalse(report["structurally_consistent"])
        self.assertIsNone(report["matches_inventory"])
        self.assertEqual(ota.main(["inspect", "--package", str(package)]), 1)
        bad = self.builder.build("bad.zip", magic=b"XXXX")
        with self.assertRaisesRegex(ota.OtaPackageError, "magic"):
            ota.inspect(bad)
        self.assertEqual(ota.main(["inspect", "--package", str(bad)]), 2)

    def test_non_ab_metadata_is_rejected_and_incrementals_are_flagged(self):
        self.builder.metadata = self.builder.metadata.replace("ota-type=AB", "ota-type=BLOCK")
        with self.assertRaisesRegex(ota.OtaPackageError, "not AB"):
            ota.inspect(self.builder.build())
        self.builder.metadata = self.builder.metadata.replace("ota-type=BLOCK", "ota-type=AB") + "pre-build=old\n"
        self.builder.old = {"system": (10, b"\x11" * 32)}
        report = ota.inspect(self.builder.build("incremental.zip"))
        self.assertTrue(report["incremental"])
        self.assertFalse(report["manifest"]["is_full_update"])
        system = next(row for row in report["manifest"]["partitions"] if row["name"] == "system")
        self.assertEqual(system["old"], {"size_bytes": 10, "sha256": "11" * 32})

    def test_unsigned_package_reports_no_footer(self):
        report = ota.inspect(self.builder.build(comment=b""))
        self.assertFalse(report["whole_file_signature"]["present"])
        report = ota.inspect(self.builder.build("marker.zip", comment=b"\x00" * 10 + struct.pack("<HHH", 16, 0x1234, 16)))
        self.assertFalse(report["whole_file_signature"]["present"])

    def test_protobuf_reader_rejects_truncation(self):
        with self.assertRaises(ota.OtaPackageError):
            list(ota.fields(bytes([0x0A, 0x05, 0x01])))
        with self.assertRaises(ota.OtaPackageError):
            list(ota.fields(bytes([0x08, 0x80])))


if __name__ == "__main__":
    unittest.main()
