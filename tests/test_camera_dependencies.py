"""Validate the sanitized, non-buildable camera dependency seed record."""

import json
from pathlib import Path, PurePosixPath
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CameraDependencyTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "research/camera-dependencies.json").read_text())

    def test_static_results_do_not_claim_trust_or_feature_compatibility(self):
        self.assertEqual(self.record["device"], "nezha")
        self.assertEqual(self.record["hardware_region"], "CN")
        self.assertFalse(self.record["provenance"]["origin_verified"])
        self.assertFalse(self.record["provenance"]["package_avb_consistent"])
        self.assertFalse(self.record["complete_transitive_closure"])
        self.assertFalse(self.record["evolution_x_hardware_tested"])
        self.assertTrue(self.record["camera_apk"]["matches_live_camera"])

    def test_dependency_paths_and_hashes_are_safe_and_partition_specific(self):
        artifacts = self.record["artifacts"]
        self.assertEqual(len(artifacts), 13)
        self.assertEqual(len({a["runtime_path"] for a in artifacts}), len(artifacts))
        for artifact in artifacts:
            path = PurePosixPath(artifact["runtime_path"])
            self.assertTrue(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertIn(path.parts[1], {"odm", "vendor", "system_ext"})
            self.assertGreater(artifact["size_bytes"], 0)
            for field in ("sha256", "image_sha256"):
                self.assertRegex(artifact[field], r"^[a-f0-9]{64}$")

    def test_native_seeds_retain_independent_linkage_evidence(self):
        libraries = [a for a in self.record["artifacts"] if "needed" in a]
        self.assertEqual(len(libraries), 8)
        for library in libraries:
            self.assertEqual(library["elf_bits"], 64)
            self.assertEqual(library["elf_machine"], 183)
            self.assertTrue(library["readelf_crosscheck"])
            self.assertTrue(library["needed"])
            self.assertEqual(library["needed"], sorted(set(library["needed"])))

    def test_record_has_no_host_identity_or_private_device_fields(self):
        forbidden = {"serial", "serialno", "imei", "imsi", "email", "account", "phone_number"}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertNotIn("/Users/", value)

        check(self.record)


if __name__ == "__main__":
    unittest.main()
