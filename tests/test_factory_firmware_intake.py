"""Offline invariants for the factory-named TGZ intake, without private files."""

import json
from pathlib import Path, PurePosixPath
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
XIAOMI_EU = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
PREFIX = "nezha_images_OS3.0.309.0.WPACNXM_16.0/images/"


class FactoryFirmwareIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/factory-firmware-intake.json").read_text())
        cls.images = {row["path"]: row for row in cls.record["images"]}

    def test_local_integrity_does_not_invent_download_origin(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        package = self.record["package"]
        self.assertEqual(package["sha256"], PACKAGE)
        self.assertEqual(package["size_bytes"], 12778943953)
        self.assertEqual(package["schema_version"], 2)
        self.assertEqual(package["source_kind"], "user-provided")
        self.assertIsNone(package["source_url"])
        self.assertIsNone(package["independently_published_sha256"])
        for key in ("origin_verified", "oem_key_authenticated", "declared_identity_verified_from_embedded_properties"):
            self.assertIs(package[key], False)
        url = urlsplit(package["reference_url"])
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.hostname, "bigota.d.miui.com")
        self.assertEqual(PurePosixPath(url.path).name, package["filename"])
        self.assertEqual(package["reference_head_size_bytes"], package["size_bytes"])
        self.assertIn("not evidence", package["reference_url_role"])

    def test_original_preservation_and_separate_copy_are_explicit(self):
        package = self.record["package"]
        for key in ("original_regular_nonsymlink", "original_identity_stable_through_intake_and_extraction",
                    "original_retained", "separate_intake_copy_readback_verified",
                    "original_rehashed_after_extraction", "original_and_intake_copy_sha256_match"):
            self.assertIs(package[key], True)
        self.assertEqual(package["source_path"], "sources/" + package["filename"])
        self.assertEqual(package["intake_path"], "artifacts/firmware/" + PACKAGE)
        intake = self.record["intake"]
        self.assertEqual(intake["exit_code"], 0)
        self.assertGreater(intake["disk_free_before_bytes"], package["size_bytes"])
        self.assertFalse(intake["source_url_invented"])
        command = intake["command"]
        self.assertEqual(command[command.index("--source-kind") + 1], "user-provided")
        self.assertNotIn("--source-url", command)

    def test_complete_stream_and_image_totals_are_consistent(self):
        extraction = self.record["extraction"]
        self.assertEqual(extraction["exit_code"], 0)
        self.assertEqual(extraction["archive_format"], "tar-gzip")
        self.assertEqual(extraction["member_count"], 127)
        self.assertEqual(extraction["member_count"], extraction["regular_member_count"] + extraction["directory_member_count"])
        self.assertEqual(extraction["decompressed_archive_bytes"], 15325941760)
        self.assertEqual(extraction["image_count"], len(self.images))
        self.assertEqual(len(self.images), 19)
        self.assertEqual(extraction["total_image_bytes"], 14852407336)
        self.assertEqual(extraction["total_image_bytes"], sum(row["size_bytes"] for row in self.images.values()))
        for key in ("gzip_stream_crc_verified", "tar_header_checksums_verified", "entire_gzip_stream_drained",
                    "tar_zero_trailer_checked", "only_regular_image_members_extracted", "all_image_hashes_readback_verified"):
            self.assertIs(extraction[key], True)
        self.assertEqual(extraction["limits"], {"image_bytes": 64 * 1024**3,
                                              "archive_decompressed_bytes": 128 * 1024**3,
                                              "trailer_bytes": 1024**2, "catalog_members": 20000})

    def test_all_image_members_are_relative_regular_image_records(self):
        seen = set()
        for name, row in self.images.items():
            self.assertRegex(name, r"^[A-Za-z0-9][A-Za-z0-9_-]*\.img$")
            self.assertNotIn(name.casefold(), seen)
            seen.add(name.casefold())
            self.assertEqual(row["archive_member"], PREFIX + name)
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(row["size_bytes"], 0)
            self.assertIs(row["readback_verified"], True)
        required = {"boot.img", "init_boot.img", "vendor_boot.img", "dtbo.img", "recovery.img",
                    "vbmeta.img", "vbmeta_system.img", "super.img"}
        self.assertTrue(required.issubset(self.images))

    def test_independent_readback_binds_original_and_all_published_images(self):
        readback = self.record["postpublication_readback"]
        self.assertEqual(readback["original_package_sha256"], PACKAGE)
        self.assertEqual(readback["image_count"], self.record["extraction"]["image_count"])
        for key in ("original_and_all_images_verified", "all_identities_stable", "all_hashes_match"):
            self.assertIs(readback[key], True)
        self.assertEqual(readback["block_size_bytes"], 4 * 1024**2)
        self.assertGreater(readback["started_at_utc"], self.record["extraction"]["finished_at_utc"])

    def test_sparse_header_is_not_promoted_to_chunk_or_partition_validation(self):
        image = self.images["super.img"]
        self.assertEqual(image["size_bytes"], 12438543008)
        self.assertEqual(image["sha256"], "fe2c6b4abe4a36c871be184350132dfed1aa1b32ada0b051923a19835affa8f5")
        self.assertEqual(image["header_kind"], "android-sparse")
        header = image["sparse_header"]
        self.assertEqual((header["major_version"], header["minor_version"]), (1, 0))
        self.assertEqual((header["file_header_size"], header["chunk_header_size"]), (28, 12))
        self.assertEqual(header["total_chunks"], 220)
        self.assertEqual(header["block_size_bytes"], 4096)
        self.assertEqual(header["expanded_size_bytes"], 15300820992)
        self.assertEqual(header["expanded_size_bytes"], header["total_blocks"] * header["block_size_bytes"])
        self.assertEqual(header["image_checksum"], 0)
        self.assertIn("header only", header["scope"])
        self.assertFalse(self.record["verification_boundaries"]["sparse_chunks_or_logical_metadata_checked_by_intake"])

    def test_xiaomi_eu_byte_comparison_preserves_distinct_package_provenance(self):
        comparison = self.record["xiaomi_eu_byte_comparison"]
        self.assertEqual(comparison["package_sha256"], XIAOMI_EU)
        self.assertNotEqual(comparison["package_sha256"], PACKAGE)
        self.assertIn("modified", comparison["description"])
        self.assertIn("Sparse-versus-raw", comparison["scope"])
        self.assertEqual(comparison["same_basename_sha256_differences"], ["vendor_boot.img", "vm-bootsys.img"])
        matches = comparison["same_basename_exact_sha256_matches"]
        self.assertEqual(len(matches), 8)
        for row in self.images.values():
            old = row["xiaomi_eu_same_basename"]
            if old is None:
                self.assertIn(row["path"], comparison["same_basename_absent_from_xiaomi_eu"])
                continue
            self.assertEqual(old["sha256_matches"], old["sha256"] == row["sha256"])
            self.assertEqual(old["size_matches"], old["size_bytes"] == row["size_bytes"])
            self.assertEqual(row["path"] in matches, old["sha256_matches"])
        vendor = self.images["vendor_boot.img"]
        self.assertEqual(vendor["sha256"], "c98aebae56e098eee6e758b8ac387ffd6dd5ec2cf051b389e97ae77d7a3404d3")
        self.assertTrue(vendor["xiaomi_eu_same_basename"]["size_matches"])
        self.assertFalse(vendor["xiaomi_eu_same_basename"]["sha256_matches"])

    def test_geometry_catalog_is_exact_and_not_claimed_as_phone_measurement(self):
        catalog = self.record["geometry_metadata_catalog"]
        expected = {f"gpt_{kind}{lun}.bin" for kind in ("main", "backup", "both", "empty") for lun in range(6)}
        expected |= {f"{kind}{lun}.xml" for kind in ("rawprogram", "patch") for lun in range(6)}
        expected.add("partition_ext_p1.xml")
        self.assertEqual(catalog["candidate_count"], 37)
        self.assertEqual({row["name"].removeprefix(PREFIX) for row in catalog["candidates"]}, expected)
        for row in catalog["candidates"]:
            self.assertTrue(row["name"].startswith(PREFIX))
            self.assertEqual(row["kind"], "file")
            self.assertGreater(row["size_bytes"], 0)
            self.assertLess(row["size_bytes"], 1024**2)
        self.assertEqual([row["name"] for row in catalog["other_xml"]], [PREFIX + "qsahara_device_programmer.xml"])
        self.assertFalse(catalog["package_geometry_parsed_by_intake"])
        self.assertFalse(catalog["physical_phone_geometry_verified"])
        self.assertFalse(catalog["device_programmer_extracted_or_executed"])

    def test_receipts_and_tools_have_hashes_without_private_machine_paths(self):
        receipts = [self.record["intake"]["receipt"], self.record["extraction"]["receipt"],
                    self.record["extraction"]["run_receipt"], self.record["postpublication_readback"]["receipt"],
                    self.record["header_observations_receipt"]]
        for row in receipts:
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(row["size_bytes"], 0)
            self.assertFalse(PurePosixPath(row["path"]).is_absolute())
            self.assertIn(PurePosixPath(row["path"]).parts[0], ("reports", "artifacts"))
            self.assertNotIn("..", PurePosixPath(row["path"]).parts)
        self.assertEqual({row["path"] for row in self.record["tools"]},
                         {"scripts/firmware.py", "scripts/firmware_tar.py", "scripts/firmware_images.py", "scripts/artifact_files.py"})
        for row in self.record["tools"]:
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(self.record["extractor_last_changed_commit"], r"^[a-f0-9]{40}$")

    def test_no_build_phone_or_authenticity_promotion_is_implied(self):
        boundaries = self.record["verification_boundaries"]
        self.assertEqual(boundaries["publisher_authenticity"], "unverified")
        for key, value in boundaries.items():
            if key != "publisher_authenticity":
                self.assertIs(value, False, key)
        for key in ("existing_outputs_overwritten", "installers_extracted_or_executed", "links_or_special_files_created"):
            self.assertIs(self.record["extraction"][key], False)

    def test_public_summary_contains_no_raw_firmware_or_private_identifiers(self):
        text = (ROOT / "research/factory-firmware-intake.json").read_text()
        self.assertNotIn("/Users/", text)
        self.assertNotIn("BEGIN PRIVATE KEY", text)
        self.assertNotRegex(text, r'"(?:serial|serialno|imei|imsi|meid|email|phone_number|blob|base64|inode|ctime_ns)"\s*:')
        doc = (ROOT / "docs/factory-firmware-intake.md").read_text()
        for phrase in (PACKAGE, "Factory-named", "source_url: null", "not an authenticity conclusion", "127 members", "19 files"):
            self.assertIn(phrase, doc)


if __name__ == "__main__":
    unittest.main()
