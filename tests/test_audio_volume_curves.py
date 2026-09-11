"""The audio volume curve fix: why every index played at full scale, and what the patch changes.

The ports below follow frameworks/av at the pinned revision: VolumeCurve::volIndexToDb
(engine/common/src/VolumeCurve.cpp) and VolumeCurves::volIndexToDb
(engine/common/include/VolumeCurve.h). The first attempt at this fix also patched
EngineConfig.cpp so the HAL's engine configuration was accepted whole; that shipped as v24 and
boot-looped, and the regression tests below pin why.
"""

import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "patches/evolution/nezha-audio-volume-curves.json"
PATCH = ROOT / "patches/evolution/nezha-audio-volume-curves.patch"
RECORD = ROOT / "research/audio-volume-curves-20260911.json"
STAGED = ROOT / "artifacts/audio-volume-curves"
RECORD_DATA = json.loads(RECORD.read_text())

VOLUME_MIN_DB = -758.0
# The five categories android.media.audio.common.AudioHalVolumeCurve.DeviceCategory defines.
AOSP_CATEGORIES = {"DEVICE_CATEGORY_HEADSET", "DEVICE_CATEGORY_SPEAKER", "DEVICE_CATEGORY_EARPIECE",
                   "DEVICE_CATEGORY_EXT_MEDIA", "DEVICE_CATEGORY_HEARING_AID"}


def vol_index_to_db(points, index_in_ui, index_min, index_max):
    """Port of VolumeCurve::volIndexToDb. points is a list of (index, attenuation in millibel)."""
    if index_min < 0 or index_max < 0:
        return math.nan
    if index_in_ui < index_min:
        if index_in_ui == 0:
            return VOLUME_MIN_DB
        index_in_ui = index_min
    elif index_in_ui > index_max:
        index_in_ui = index_max
    if index_min == index_max:
        return float(index_min) if index_in_ui == index_min else math.nan
    steps = 1 + points[-1][0] - points[0][0]
    vol_idx = (steps * (index_in_ui - index_min)) // (index_max - index_min)
    # SortedVector::orderOf: the position this index would be inserted at.
    position = 0
    while position < len(points) and points[position][0] < vol_idx:
        position += 1
    if position >= len(points):
        return points[-1][1] / 100.0
    if position == 0:
        if vol_idx != points[0][0]:
            return VOLUME_MIN_DB
        return points[0][1] / 100.0
    lo_index, lo_mb = points[position - 1]
    hi_index, hi_mb = points[position]
    return (lo_mb / 100.0) + (vol_idx - lo_index) * (
        ((hi_mb / 100.0) - (lo_mb / 100.0)) / (hi_index - lo_index))


def group_vol_index_to_db(curves, category, index_in_ui, index_min, index_max):
    """Port of VolumeCurves::volIndexToDb: no curve for the category means no attenuation."""
    if category not in curves:
        return 0.0  # and logs "Invalid device category %d for Volume Curve"
    return vol_index_to_db(curves[category], index_in_ui, index_min, index_max)


def legacy_group_name(stream):
    """audio_stream_type_to_string: what parseLegacyVolumes names a group it builds."""
    return "AUDIO_STREAM_" + stream


def patch_line_counts(text):
    """Added and removed lines per file, straight out of the unified diff."""
    counts, current = {}, None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            current = line[len("+++ b/"):]
            counts[current] = {"added_lines": 0, "removed_lines": 0}
        elif current and line.startswith("+") and not line.startswith("+++"):
            counts[current]["added_lines"] += 1
        elif current and line.startswith("-") and not line.startswith("---"):
            counts[current]["removed_lines"] += 1
    return counts


class MeasuredBehaviourTests(unittest.TestCase):
    """What the phone did, recomputed from the curve the HAL actually serves."""

    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        group = cls.record["measured_music_volume_group"]
        cls.points = [tuple(p) for p in group["speaker_curve_points"]]
        cls.index_min, cls.index_max = group["framework_index_range"]
        cls.expected = group["speaker_volume_db"]

    def test_a_group_without_curves_plays_at_full_scale_at_every_index(self):
        # The measured fault: no curve for the speaker, so no index attenuates anything.
        for index in (0, 1, 6, 75, 149, 150):
            self.assertEqual(
                group_vol_index_to_db({}, "DEVICE_CATEGORY_SPEAKER", index, self.index_min, self.index_max),
                0.0, index)

    def test_the_vendor_curve_makes_index_zero_silent_and_the_top_full(self):
        for index, decibels in self.expected.items():
            got = group_vol_index_to_db({"DEVICE_CATEGORY_SPEAKER": self.points},
                                        "DEVICE_CATEGORY_SPEAKER", int(index), self.index_min, self.index_max)
            self.assertAlmostEqual(got, decibels, places=2, msg=index)
        # Index 0 is the mute position only because a curve exists to say so.
        self.assertEqual(self.expected["0"], VOLUME_MIN_DB)
        self.assertGreater(self.expected["150"], self.expected["75"])
        self.assertGreater(self.expected["75"], self.expected["1"])

    def test_the_curve_is_authored_on_this_phones_150_step_scale(self):
        self.assertEqual(self.points[0][0], 0)
        self.assertEqual(self.points[-1][0], 150)
        self.assertEqual([self.index_min, self.index_max], [0, 150])


class FallbackTests(unittest.TestCase):
    """The fix fills empty volume groups from the legacy tables, and those names line up."""

    def test_the_legacy_group_names_are_exactly_what_the_default_strategies_ask_for(self):
        # gDefaultEngineConfig's strategies reference their volume groups by stream name, and
        # parseLegacyVolumes builds one group per stream named the same way, so they match.
        wanted = RECORD_DATA["fallback"]["default_strategy_volume_group_names"]
        built = [legacy_group_name(s) for s in RECORD_DATA["fallback"]["legacy_table_streams"]]
        self.assertEqual(sorted(set(wanted) & set(built)), sorted(RECORD_DATA["fallback"]["matched_groups"]))
        self.assertIn("AUDIO_STREAM_MUSIC", RECORD_DATA["fallback"]["matched_groups"])
        # only the call-assistant group has no legacy entry; it carries no audio on this phone
        self.assertEqual(sorted(set(wanted) - set(built)), ["AUDIO_STREAM_CALL_ASSISTANT"])
        self.assertIn("AUDIO_STREAM_CALL_ASSISTANT", RECORD_DATA["fallback"]["unmatched_group"])

    def test_the_legacy_tables_are_reachable_on_this_device(self):
        source = RECORD_DATA["fallback"]["legacy_tables"]
        self.assertTrue(source["policy_file"].endswith("audio_policy_configuration.xml"))
        self.assertTrue(any(i.endswith("/audio_policy_volumes.xml") for i in source["included"]), source)
        self.assertTrue(any(i.endswith("/default_volume_tables.xml") for i in source["included"]), source)
        self.assertTrue(all(i.startswith("/vendor/") for i in source["included"]), source)


class RegressionTests(unittest.TestCase):
    """v24 boot-looped. These pin the cause so the wider change is not tried again by accident."""

    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text())
        self.superseded = self.contract["superseded_attempt"]

    def test_the_patch_no_longer_touches_the_conversion(self):
        self.assertEqual(list(self.contract["files"]),
                         ["frameworks/av/services/audiopolicy/engine/common/src/EngineBase.cpp"])
        self.assertNotIn("EngineConfig.cpp", PATCH.read_text())

    def test_the_boot_loop_and_its_cause_are_recorded(self):
        self.assertIn("Invalid usage 19", self.superseded["measured_failure"])
        self.assertIn("AudioService", self.superseded["measured_failure"])
        self.assertIn("product strategies", self.superseded["why_it_was_wrong"])
        self.assertIn("v24", self.superseded["shipped_as"])
        # the usages that cannot be exposed are named, not just alluded to
        self.assertIn("AUDIO_USAGE_BLUETOOTH_SCO", self.superseded["why_it_was_wrong"])

    def test_the_product_strategies_are_left_alone(self):
        self.assertIn("product strategies stay the AOSP defaults", self.contract["fix"]["mechanism"])
        self.assertIn("AOSP default strategies", self.contract["safety"]["product_strategies_unchanged"])


class PatchPinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text())
        cls.text = PATCH.read_text()

    def test_the_contract_pins_this_patch(self):
        self.assertEqual(hashlib.sha256(PATCH.read_bytes()).hexdigest(), self.contract["patch_sha256"])
        self.assertEqual(self.contract["patch"], "patches/evolution/nezha-audio-volume-curves.patch")
        self.assertEqual(self.contract["project"], "frameworks/av")

    def test_the_patch_touches_exactly_the_pinned_file_with_the_pinned_line_counts(self):
        counts = patch_line_counts(self.text)
        self.assertEqual(set(counts), set(self.contract["files"]))
        for path, pinned in self.contract["files"].items():
            self.assertEqual(counts[path]["added_lines"], pinned["added_lines"], path)
            self.assertEqual(counts[path]["removed_lines"], pinned["removed_lines"], path)

    def test_the_patch_body_matches_what_the_contract_says_it_does(self):
        # the fallback is the whole patch; nothing is removed
        self.assertIn("+        if (engineConfig::parseLegacyVolumes(result.parsedConfig->volumeGroups) != NO_ERROR) {",
                      self.text)
        self.assertNotIn("\n-", self.text.split("@@", 1)[1])
        self.assertIn("legacy volume tables", self.contract["fix"]["mechanism"])

    def test_the_staged_sources_reproduce_the_pinned_hashes(self):
        if not (STAGED / "src").is_dir():
            self.skipTest("upstream sources not staged locally")
        work = STAGED / "test-apply"
        subprocess.run(["rm", "-rf", str(work)], check=True)
        for path, pinned in self.contract["files"].items():
            source = STAGED / "src" / Path(path).name
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), pinned["before_sha256"], path)
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        applied = subprocess.run(["patch", "-p1", "-s"], cwd=work, input=self.text,
                                 capture_output=True, text=True)
        self.assertEqual(applied.returncode, 0, applied.stderr + applied.stdout)
        for path, pinned in self.contract["files"].items():
            data = (work / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), pinned["after_sha256"], path)
            self.assertEqual(len(data), pinned["after_bytes"], path)
        subprocess.run(["rm", "-rf", str(work)], check=True)


class RecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.contract = json.loads(CONTRACT.read_text())

    def test_the_category_census_agrees_between_contract_and_record(self):
        census = self.record["cause"]["xiaomi_only_device_categories"]
        self.assertEqual(census, self.contract["problem"]["xiaomi_only_device_categories"])
        self.assertEqual(sum(census.values()), 33)
        self.assertFalse(set(census) & AOSP_CATEGORIES)
        self.assertEqual(set(self.record["cause"]["aosp_device_categories"]), AOSP_CATEGORIES)

    def test_the_record_keeps_the_measured_log_lines_and_its_limits(self):
        evidence = self.record["evidence"]
        self.assertIn("number of volume groups parsed: 12", evidence["hal_parsed_its_xml"])
        self.assertTrue(any("Line: 143" in line for line in evidence["framework_refused_it"]))
        self.assertIn("There was an error parsing AIDL data", evidence["framework_refused_it"][-1])
        self.assertIn("Invalid device category 1", evidence["runtime_effect"])
        self.assertTrue(any("not run on the phone" in item or "device result" in item
                            for item in self.record["not_established"]))
        self.assertTrue(self.contract["not_device_admitted"])

    def test_the_page_exists_and_is_indexed(self):
        page = ROOT / self.record["document"]
        self.assertTrue(page.is_file())
        self.assertIn(page.name, (ROOT / "docs/README.md").read_text())
        body = page.read_text()
        self.assertIn("Invalid device category 1 for Volume Curve", body)
        self.assertIn("There is no runtime workaround", body)
        for name in self.record["cause"]["xiaomi_only_device_categories"]:
            self.assertIn(name, body, name)


if __name__ == "__main__":
    unittest.main()
