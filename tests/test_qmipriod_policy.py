"""Offline derivation and rejection checks; no phone or policy compiler."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts import qmipriod_policy as qp, vendor_policy as vp


class QmipriodPolicyTests(unittest.TestCase):
    def setUp(self):
        self.contract = qp.load_contract()
        self.base = b"; synthetic immutable policy\n(type vendor_qmipriod)\n"
        self.fixture = copy.deepcopy(self.contract)
        self.fixture["base"] = {"sha256": vp.sha(self.base), "size_bytes": len(self.base)}
        output = self.base + self.fixture["suffix"].encode()
        self.fixture["output"] = {"sha256": vp.sha(output), "size_bytes": len(output)}

    def test_extension_preserves_base_bytes_and_can_be_factored_for_native_check(self):
        result = qp.extend(self.base, self.fixture)
        self.assertEqual(result[:len(self.base)], self.base)
        self.assertEqual(qp.verify_extended(result, self.fixture), self.base)

    def test_changed_input_duplicate_extension_and_extra_rule_are_rejected(self):
        result = qp.extend(self.base, self.fixture)
        for raw in (b" " + self.base, result):
            with self.assertRaises(vp.VendorPolicyError):
                qp.extend(raw, self.fixture)
        for raw in (result + b"\n", result.replace(b"write", b"read", 1),
                    result + b"(allow vendor_qmipriod self (capability (sys_admin)))\n"):
            with self.assertRaises(vp.VendorPolicyError):
                qp.verify_extended(raw, self.fixture)

    def test_changed_contract_is_not_a_production_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(self.fixture))
            with self.assertRaises(vp.VendorPolicyError):
                qp.load_contract(path)

    def test_permission_budget_is_only_log_creation_and_writing(self):
        # Security boundary justified by the measured fopen(log.txt, "w"):
        # no execution, relabeling, network access, transitions or broad types.
        forms = [f.expr for f in vp.parse(self.contract["suffix"].encode())]
        self.assertEqual(forms, [
            ("allow", "vendor_qmipriod", "vendor_qmipriod_data_file",
             ("dir", ("search", "write", "add_name"))),
            ("allow", "vendor_qmipriod", "vendor_qmipriod_data_file",
             ("file", ("create", "open", "write", "getattr"))),
        ])
        self.assertEqual(self.contract["base"], vp.load_contract()["output"])


if __name__ == "__main__":
    unittest.main()
