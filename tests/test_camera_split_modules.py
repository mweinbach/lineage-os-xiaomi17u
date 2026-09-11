"""The camera's Qigsaw modules: the one policy rule that lets their libraries load, and the
measurement behind it. Offline; the split APK is only checked when it is staged locally."""

import hashlib
import json
from pathlib import Path
import re
import struct
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "config/nezha-camera-split-modules.json").read_text())
RECORD = json.loads((ROOT / "research/camera-split-modules-20260911.json").read_text())
RULE_FILE = ROOT / "device/xiaomi/nezha/sepolicy/product/private/platform_app.te"
SPLIT = ROOT / "artifacts/camera-splits/panorama.apk"
EXPECTED_RULE = "allow platform_app app_data_file:file execute;"


def statements(text):
    """Every policy statement in a .te file, comments and blank lines dropped."""
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")]


def has_text_relocation(data):
    """True if the ELF declares DT_TEXTREL or the TEXTREL bit of DT_FLAGS/DT_FLAGS_1."""
    assert data[:4] == b"\x7fELF" and data[4] == 2, "expected ELF64"
    e_phoff, = struct.unpack_from("<Q", data, 0x20)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", data, off)
        if p_type != 2:  # PT_DYNAMIC
            continue
        p_offset, _, _, p_filesz = struct.unpack_from("<QQQQ", data, off + 8)
        for d in range(0, p_filesz, 16):
            tag, val = struct.unpack_from("<qQ", data, p_offset + d)
            if tag == 0:
                return False
            if tag == 22:  # DT_TEXTREL
                return True
            if tag in (30, 0x6FFFFFFB) and val & 0x4:  # DT_FLAGS / DT_FLAGS_1, TEXTREL
                return True
    return False


class RuleTests(unittest.TestCase):
    def test_the_contract_pins_this_rule_file(self):
        body = RULE_FILE.read_bytes()
        pinned = CONTRACT["rule_file"]
        self.assertEqual(hashlib.sha256(body).hexdigest(), pinned["sha256"])
        self.assertEqual(len(body), pinned["size_bytes"])
        self.assertEqual(Path(pinned["path"]), RULE_FILE.relative_to(ROOT))

    def test_the_file_carries_exactly_one_rule_and_no_extra_permission(self):
        lines = statements(RULE_FILE.read_text())
        self.assertEqual(lines, [EXPECTED_RULE])
        self.assertEqual(CONTRACT["rule_file"]["rule"], EXPECTED_RULE)
        # execmod and execute_no_trans are the two that would widen this beyond dlopen
        for withheld in CONTRACT["scope_and_cost"]["withheld"]:
            self.assertNotIn(withheld, EXPECTED_RULE)

    def test_the_rule_lands_in_a_policy_directory_the_board_already_compiles(self):
        self.assertTrue(RULE_FILE.parent.is_dir())
        # the directory has to be one the generated BoardConfig already adds, or the rule is inert
        self.assertEqual(CONTRACT["rule_file"]["policy_dir"], str(RULE_FILE.parent.relative_to(ROOT)))
        self.assertIn("PRODUCT_PRIVATE_SEPOLICY_DIRS", CONTRACT["rule_file"]["wired_by"])
        sibling = RULE_FILE.parent / "isolated_compute_app.te"
        self.assertTrue(sibling.is_file(), "the precedent file for this directory is gone")


class MeasurementTests(unittest.TestCase):
    def test_the_permission_census_is_recomputed_from_the_measured_mask(self):
        m = RECORD["policy_measurement"]
        allowed = int(m["allowed_mask"], 16)
        indices = m["file_class_permission_indices"]
        granted = sorted(n for n, i in indices.items() if allowed & (1 << (i - 1)))
        withheld = sorted(n for n, i in indices.items() if not allowed & (1 << (i - 1)))
        self.assertEqual(granted, sorted(m["granted"]))
        self.assertEqual(withheld, sorted(m["withheld"]))
        # the whole point: map is granted, execute is not
        self.assertIn("map", granted)
        self.assertIn("execute", withheld)
        self.assertEqual(len(indices), len(granted) + len(withheld))

    def test_the_download_is_exonerated_by_a_hash_the_manifest_declares(self):
        d = RECORD["download_verified"]
        self.assertEqual(d["expected_md5"], d["downloaded_md5"])
        self.assertEqual(d["host_http_status"], 200)
        self.assertEqual(d["downloaded_bytes"],
                         RECORD["modules_declared"]["splits"][d["split"]]["bytes"])
        self.assertFalse(RECORD["modules_declared"]["built_in"])

    def test_the_failure_is_the_load_and_the_rollback_explains_the_empty_directories(self):
        f = RECORD["failure"]
        self.assertIn("couldn't map", f["linker"])
        self.assertIn("Permission denied", f["linker"])
        self.assertIn("nativeLib/arm64-v8a", f["linker"])
        self.assertIn("delete", f["rollback"])
        self.assertFalse(f["avc_denial_logged"])

    def test_seven_modules_are_declared_and_none_ships_in_the_image(self):
        splits = RECORD["modules_declared"]["splits"]
        self.assertEqual(len(splits), 7)
        self.assertIn("panorama", splits)
        self.assertEqual(sum(s["bytes"] for s in splits.values()), 440420244)

    def test_the_staged_split_reproduces_the_hash_and_the_relocation_survey(self):
        if not SPLIT.is_file():
            self.skipTest("panorama split not staged locally")
        data = SPLIT.read_bytes()
        self.assertEqual(hashlib.md5(data).hexdigest(), RECORD["download_verified"]["expected_md5"])
        self.assertEqual(len(data), RECORD["download_verified"]["downloaded_bytes"])
        libs = [n for n in zipfile.ZipFile(SPLIT).namelist() if n.endswith(".so")]
        survey = RECORD["text_relocation_survey"]
        self.assertEqual(len(libs), survey["libraries"])
        z = zipfile.ZipFile(SPLIT)
        flagged = [n for n in libs if has_text_relocation(z.read(n))]
        self.assertEqual(len(flagged), survey["with_dt_textrel_or_textrel_flag"], flagged)
        # the library the linker actually refused is in there
        self.assertTrue(any(n.endswith("libmorpho_sensor_fusion.so") for n in libs))


class RecordTests(unittest.TestCase):
    def test_the_page_exists_is_indexed_and_states_what_the_rule_costs(self):
        page = ROOT / RECORD["document"]
        self.assertTrue(page.is_file())
        self.assertIn(page.name, (ROOT / "docs/README.md").read_text())
        body = page.read_text()
        self.assertIn(EXPECTED_RULE, body)
        self.assertIn("W^X", body)
        for process in RECORD["cost"]["processes_in_that_domain_on_this_build"]:
            self.assertIn(process, body)

    def test_the_limits_and_the_rejected_designs_are_written_down(self):
        self.assertTrue(CONTRACT["not_device_admitted"])
        self.assertTrue(any("device result" in item for item in RECORD["not_established"]))
        self.assertEqual(set(CONTRACT["rejected_alternatives"]),
                         {"private_data_type_for_the_camera", "private_domain_for_the_camera",
                          "ship_the_splits_in_the_image"})
        self.assertTrue(RECORD["fix"]["selinux_stays_enforcing"])

    def test_the_contract_and_record_agree_on_the_measurement(self):
        self.assertEqual(CONTRACT["scope_and_cost"]["platform_app_processes_on_this_build"],
                         RECORD["cost"]["processes_in_that_domain_on_this_build"])
        self.assertIn(RECORD["policy_measurement"]["allowed_mask"],
                      CONTRACT["problem"]["evidence"]["policy_query"])
        self.assertEqual(CONTRACT["download_is_not_the_problem"]["panorama_split_md5_downloaded"],
                         RECORD["download_verified"]["downloaded_md5"])


if __name__ == "__main__":
    unittest.main()
