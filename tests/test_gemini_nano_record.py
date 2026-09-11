"""Recompute the Gemini Nano availability record: the framework is wired for AICore, the hardware is
capable, and three independent measurements say the model cannot be supplied for this NPU."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = json.loads((ROOT / "research/gemini-nano-20260911.json").read_text())


class GeminiNanoRecordTests(unittest.TestCase):
    def test_the_answer_is_no_and_the_page_says_why(self):
        self.assertEqual(RECORD["answer"], "no")
        page = (ROOT / RECORD["document"]).read_text()
        self.assertIn("Your device isn't compatible with this version.", page)
        self.assertIn("SM8850", page)
        self.assertIn("v81", page)

    def test_the_framework_is_already_pointed_at_aicore(self):
        wiring = RECORD["framework_wiring"]
        for key in ("on_device_intelligence_service", "on_device_sandboxed_inference_service"):
            self.assertTrue(wiring[key].startswith("com.google.android.aicore/"), key)
        self.assertEqual(wiring["device_config_namespace"], "aicore")
        # The gap is the package, not the plumbing.
        self.assertFalse(RECORD["aicore_package_installed"])
        self.assertFalse(RECORD["aicore_in_source_tree"])

    def test_the_hardware_is_not_the_blocker(self):
        hw = RECORD["hardware"]
        self.assertEqual(hw["soc"], "SM8850")
        self.assertIn("v81", hw["npu"])
        self.assertTrue(any("GenAiTransformer" in lib for lib in hw["qnn_genai_runtime"]))
        self.assertGreater(hw["ram_kb"], 8 * 1024 * 1024)

    def test_no_shipped_model_group_targets_this_soc(self):
        groups = RECORD["server_config_on_this_device"]["llm_file_groups"]
        self.assertTrue(groups)
        # Snapdragon groups exist, so this is not "Pixel only" -- but none name this chip.
        self.assertTrue(any("sm86" in g for g in groups), groups)
        self.assertFalse(any("8850" in g or "sm8850" in g for g in groups), groups)
        socs = {m for g in groups for m in re.findall(r"sm\d{4}", g)}
        self.assertEqual(socs, {"sm8635", "sm8650"})

    def test_the_official_apk_is_a_stub(self):
        apk = RECORD["official_apk_probe"]
        self.assertIn("stub", apk["apk_version_name"])
        self.assertLess(apk["apk_bytes"], 2 * 1024 * 1024)
        self.assertFalse(apk["apk_contains_native_libs"])
        self.assertFalse(apk["apk_contains_models"])
        self.assertEqual(len(apk["apk_sha256"]), 64)
        self.assertEqual(len(apk["product_img_sha256"]), 64)
        self.assertTrue(apk["source"].startswith("https://dl.google.com/"))

    def test_play_refused_the_app_on_this_device(self):
        play = RECORD["play_store_verdict_on_this_device"]
        self.assertEqual(play["package"], "com.google.android.aicore")
        self.assertIn("isn't compatible", play["message"])

    def test_the_record_keeps_its_limits_explicit_and_touched_nothing(self):
        self.assertIn("not_established", RECORD)
        self.assertIn("AicDataRelease", RECORD["not_established"])
        self.assertIn("None", RECORD["device_changes"])
        self.assertIn("gemini-nano-20260911.md", (ROOT / "docs/README.md").read_text())


if __name__ == "__main__":
    unittest.main()
