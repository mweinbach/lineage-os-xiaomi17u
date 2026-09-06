"""Offline checks for the both-physical-slot route derived from a version-1 plan."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import delivery_route as route
from scripts import experimental_flash_bundle as bundle


def hashed(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def synthetic_plan():
    plan = {
        "schema_version": 1, "device": dict(bundle.DEVICE), "platform": dict(bundle.PLATFORM),
        "artifact_set_id": "example-route-20260906-v1", "build_number": "nezha." + "5" * 24,
        **{key: False for key in bundle.FALSE_FLAGS},
        "fresh_experimental_flash_authorization": None, "source_archive_is_flashable_installer": False,
        "device_preflight": {**{key: None for key in bundle.PREFLIGHT_FIELDS}, "device_preflight_admitted": False},
        "delivery_modes": {"current_super_factory_style": {
            **bundle.LAYOUT, "warning": bundle.WARNING, "payloads": list(bundle.PAYLOADS)}},
        "avb_contract": {"algorithm": "SHA256_RSA4096", "flags": 0,
                         "disable_verification_or_verity_allowed": False, "relock_allowed": False,
                         "rollback_bypass_allowed": False, "public_key_sha256": "b" * 64},
        "retained_firmware_avb_requirements": {"countrycode": {"note": "match"}, "pvmfw": {"note": "match"}},
        "super": {**hashed(b"inert super"), "expanded_size_bytes": 15300820992},
        "artifacts": [], "evidence": {},
    }
    for role in (*bundle.PHYSICAL, *bundle.LOGICAL, *bundle.REFERENCES):
        raw = ("inert image fixture for " + role).encode()
        delivery_role = ("required-physical-slot-image" if role in bundle.PHYSICAL else
                         "verification-reference-only-retain-existing-device-firmware" if role in bundle.REFERENCES else
                         "embedded-in-current-super-or-separate-logical-image-for-a-different-reviewed-route")
        target = (role + "_a-for-current-super-route" if role in bundle.PHYSICAL else
                  role + "_<selected-slot>" if role in bundle.REFERENCES else role + "_a")
        plan["artifacts"].append({"role": role, "path": role + ".img", "delivery_role": delivery_role,
                                  "target": target, **hashed(raw)})
    return plan


class DeliveryRouteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.plan = synthetic_plan()
        self.plan_sha = "c" * 64
        self.enterContext(mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")))

    def test_route_writes_super_once_then_b_then_a_from_the_same_bytes(self):
        result = route.validate(route.derive(self.plan, self.plan_sha))
        self.assertEqual(result["write_count"], 15)
        writes = result["writes"]
        self.assertEqual(writes[0]["target"], "super")
        self.assertEqual(writes[0]["sparse_chunk_limit"], "512M")
        self.assertEqual([w["target"] for w in writes[1:8]],
                         ["dtbo_b", "init_boot_b", "vendor_boot_b", "recovery_b", "boot_b", "vbmeta_system_b", "vbmeta_b"])
        self.assertEqual([w["target"] for w in writes[8:]],
                         ["dtbo_a", "init_boot_a", "vendor_boot_a", "recovery_a", "boot_a", "vbmeta_system_a", "vbmeta_a"])
        self.assertEqual([w["order"] for w in writes], list(range(1, 16)))
        by_role = {}
        for row in writes[1:]:
            by_role.setdefault(row["role"], set()).add((row["sha256"], row["size_bytes"]))
        self.assertTrue(all(len(identities) == 1 for identities in by_role.values()))
        expected_boot = next(r for r in self.plan["artifacts"] if r["role"] == "boot")
        self.assertEqual(by_role["boot"], {(expected_boot["sha256"], expected_boot["size_bytes"])})
        self.assertEqual(result["retained_firmware_readback"]["pvmfw"]["targets"], ["pvmfw_a", "pvmfw_b"])
        self.assertTrue(result["layout"]["logical_single_copy_by_virtual_ab_design"])
        self.assertFalse(result["layout"]["slot_change_requested"])
        self.assertFalse(result["flash_ready"])
        self.assertEqual(result["build_number"], self.plan["build_number"])
        self.assertNotIn("logical_b_populated", json.dumps(result))

    def test_invalid_plans_are_rejected_before_derivation(self):
        self.plan["flash_ready"] = True
        with self.assertRaisesRegex(route.RouteError, "delivery plan rejected"):
            route.derive(self.plan, self.plan_sha)
        plan = synthetic_plan()
        plan["artifacts"] = [row for row in plan["artifacts"] if row["role"] != "vbmeta"]
        with self.assertRaises(route.RouteError):
            route.derive(plan, self.plan_sha)

    def test_validate_rejects_reordered_missing_or_altered_writes(self):
        good = route.derive(self.plan, self.plan_sha)
        reordered = deepcopy(good)
        reordered["writes"][1], reordered["writes"][8] = reordered["writes"][8], reordered["writes"][1]
        with self.assertRaisesRegex(route.RouteError, "out of order"):
            route.validate(reordered)
        missing = deepcopy(good)
        missing["writes"] = missing["writes"][:-1]
        missing["write_count"] = 14
        with self.assertRaisesRegex(route.RouteError, "exactly 15"):
            route.validate(missing)
        altered = deepcopy(good)
        altered["writes"][8]["sha256"] = "d" * 64
        with self.assertRaisesRegex(route.RouteError, "different bytes"):
            route.validate(altered)
        promoted = deepcopy(good)
        promoted["flash_ready"] = True
        with self.assertRaisesRegex(route.RouteError, "promotes"):
            route.validate(promoted)
        one_slot = deepcopy(good)
        one_slot["retained_firmware_readback"]["pvmfw"]["targets"] = ["pvmfw_a"]
        with self.assertRaisesRegex(route.RouteError, "both slots"):
            route.validate(one_slot)

    def test_cli_derives_exclusively_and_validates(self):
        plan_path = self.root / "plan.json"
        raw = bundle.json_bytes(self.plan)
        plan_path.write_bytes(raw)
        output = self.root / "route.json"
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(route.main(["derive", "--plan", str(plan_path), "--expected-plan-sha256", digest,
                                     "--output", str(output)]), 0)
        self.assertEqual(route.main(["derive", "--plan", str(plan_path), "--expected-plan-sha256", digest,
                                     "--output", str(output)]), 2)
        self.assertEqual(route.main(["derive", "--plan", str(plan_path), "--expected-plan-sha256", "0" * 64,
                                     "--output", str(self.root / "other.json")]), 1)
        self.assertEqual(route.main(["validate", "--route", str(output)]), 0)
        document = json.loads(output.read_bytes())
        document["writes"][0]["sparse_chunk_limit"] = "64M"
        output.write_bytes(bundle.json_bytes(document))
        self.assertEqual(route.main(["validate", "--route", str(output)]), 1)


if __name__ == "__main__":
    unittest.main()
