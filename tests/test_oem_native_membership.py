"""Android retains inherited platform members in changed system_ext attributes."""

import unittest

from scripts import oem_policy as op
from scripts import vendor_policy as vp
from tests.test_oem_policy import native_fixture


HW = "vendor_hal_atfwd_hwservice"
ATTR = "hwservice_manager_type"


def inherited_fixture():
    corpus, vendor, contract, capability = native_fixture()
    corpus[op.INPUT_FLAGS["platform_cil"]] += (
        b"(type inherited_hwservice)(roletype object_r inherited_hwservice)\n"
        b"(type unrelated_platform_type)(roletype object_r unrelated_platform_type)\n"
        b"(typeattributeset hwservice_manager_type (inherited_hwservice))\n"
    )
    ext = op.INPUT_FLAGS["system_ext_cil"]
    corpus[ext] = corpus[ext].replace(f"(typeattributeset {ATTR} ({HW}))".encode(),
                                    f"(typeattributeset {ATTR} (inherited_hwservice {HW}))".encode())
    return corpus, vendor, contract, capability


class NativeInheritedMembershipTests(unittest.TestCase):
    def check(self, fixture):
        return op.check_native_contents(*fixture)

    def test_exact_platform_plus_oem_membership_passes(self):
        result = self.check(inherited_fixture())
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["type_ownership"][HW]["roles"], ["object_r"])
        self.assertEqual(result["type_ownership"][HW]["versioned_mapping"], [HW])
        self.assertEqual(result["helper_effective_property_set_grants"], 0)

    def test_missing_inherited_or_oem_member_fails_even_if_combined_closure_has_it(self):
        for member in ("inherited_hwservice", HW):
            fixture = list(inherited_fixture())
            ext = op.INPUT_FLAGS["system_ext_cil"]
            full = f"(typeattributeset {ATTR} (inherited_hwservice {HW}))".encode()
            remaining = HW if member == "inherited_hwservice" else "inherited_hwservice"
            fixture[0][ext] = fixture[0][ext].replace(full, f"(typeattributeset {ATTR} ({remaining}))".encode())
            with self.subTest(member=member), self.assertRaisesRegex(op.OemPolicyError, "source-owned"):
                self.check(fixture)

    def test_unrelated_platform_type_is_not_an_inherited_attribute_member(self):
        fixture = list(inherited_fixture())
        ext = op.INPUT_FLAGS["system_ext_cil"]
        fixture[0][ext] = fixture[0][ext].replace(f"inherited_hwservice {HW}".encode(),
                                               f"inherited_hwservice unrelated_platform_type {HW}".encode())
        with self.assertRaisesRegex(op.OemPolicyError, "unreviewed source-owned"):
            self.check(fixture)

    def test_vendor_only_membership_cannot_be_laundered_through_combined_closure(self):
        fixture = list(inherited_fixture())
        corpus, contract = fixture[0], fixture[2]
        public, ext = op.INPUT_FLAGS["factory_pub"], op.INPUT_FLAGS["system_ext_cil"]
        corpus[public] += (
            b"(type vendor_only_hwservice)(roletype object_r vendor_only_hwservice)\n"
            b"(typeattributeset hwservice_manager_type (vendor_only_hwservice))\n"
        )
        for row in contract["unchanged_factory_inputs"]:
            if row["runtime_path"] == public:
                row.update(sha256=vp.sha(corpus[public]), size_bytes=len(corpus[public]))
        corpus[ext] = corpus[ext].replace(f"inherited_hwservice {HW}".encode(),
                                         f"inherited_hwservice vendor_only_hwservice {HW}".encode())
        with self.assertRaisesRegex(op.OemPolicyError, "unreviewed source-owned"):
            self.check(fixture)

    def test_duplicate_source_assignment_and_permission_are_still_rejected(self):
        for addition in (f"(typeattributeset {ATTR} (inherited_hwservice {HW}))".encode(),
                         f"(allow init_dev_config {HW} (hwservice_manager (find)))".encode()):
            fixture = list(inherited_fixture())
            fixture[0][op.INPUT_FLAGS["system_ext_cil"]] += addition
            with self.subTest(addition=addition), self.assertRaises(op.OemPolicyError):
                self.check(fixture)


if __name__ == "__main__":
    unittest.main()
