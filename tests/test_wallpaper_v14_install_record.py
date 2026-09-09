"""Recompute the v14 installation and Wallpaper & style validation record from the public artifacts it binds."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/wallpaper-v14-install-validation-20260908.json"
PREPARED = ROOT / "research/wallpaper-clock-plugin-20260908.json"
CONTRACT = ROOT / "config/systemui-clocks-flex-removal.json"
BUILD = "nezha.98d08f70d20e5a87a2777f81"
PREDECESSOR = "nezha.2c510f47f6d99b93f0c3ee11"
MANIFEST_SHA = "b36a0482e3b28be2c16d609f6cc6252b6c8b68ee25d0f87d624472df5b678ce0"
KEPT = ["BigNum", "Calligraphy", "Growth", "Inflate", "Metro", "NumOverlap", "Weather"]
FACES = ["Digital default", "Digital overlapping numerals", "Digital transit clock", "Analog bold font",
         "Digital calligraphy", "Digital inflated", "Digital with weather", "Digital stenciling"]


class RecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.prepared = json.loads(PREPARED.read_text())
        cls.contract = json.loads(CONTRACT.read_text())

    def test_identity_and_flags(self):
        r = self.record
        self.assertEqual(r["build_number"], BUILD)
        self.assertEqual(r["installed_predecessor"], PREDECESSOR)
        self.assertTrue(r["installed"] and r["phone_accessed"] and r["wallpaper_fix_verified_on_device"])
        self.assertEqual(r["delivery_set"], "v14")
        self.assertEqual((ROOT / r["document"]).suffix, ".md")
        self.assertTrue((ROOT / r["document"]).is_file())

    def test_binds_prepared_record_and_manifest(self):
        r = self.record
        self.assertEqual(r["prepared_record_sha256"], hashlib.sha256(PREPARED.read_bytes()).hexdigest())
        self.assertEqual(self.prepared["build_number"], BUILD)
        self.assertEqual(self.prepared["package"]["bundle_manifest_sha256"], MANIFEST_SHA)
        self.assertEqual(r["installation"]["manifest_sha256"], MANIFEST_SHA)
        self.assertFalse(self.prepared["installed"])

    def test_installation_route(self):
        i = self.record["installation"]
        self.assertEqual(i["acknowledged_images"], 8)
        self.assertEqual(i["write_order"], ["super", "dtbo", "init_boot", "vendor_boot", "recovery", "boot", "vbmeta_system", "vbmeta"])
        self.assertEqual((i["slot"], i["selinux"], i["build_type"]), ("a", "Enforcing", "userdebug"))
        self.assertFalse(i["wipe_performed"] or i["slot_changed"] or i["data_cleared"])
        self.assertLess(i["boot_seconds"], 120)
        self.assertGreater(i["super_write_seconds"], 60)
        self.assertEqual(i["user_response"], "ok can you install")

    def test_flex_removed_and_kept_apks_match_contract(self):
        post = self.record["post_boot_observation"]
        self.assertTrue(post["flex_absent"])
        self.assertNotIn("com.android.systemui.clocks.flex", post["clock_packages"])
        for name in KEPT:
            self.assertIn("com.android.systemui.clocks." + name.lower(), post["clock_packages"])
        installed = post["installed_plugin_and_host_apks_match_contract"]
        for name in KEPT:
            self.assertEqual(installed[name], self.contract["kept_clock_plugins"][name]["sha256"])
        self.assertEqual(installed["WallpaperPickerGoogleRelease"], self.contract["hosts"]["WallpaperPickerGoogleRelease"]["sha256"])
        self.assertEqual(post["plugin_rejection_lines"], 0)
        self.assertEqual(post["crash_fatal_lines"], 0)
        self.assertTrue(post["wallpaper_app_data_unchanged_before_first_launch"])

    def test_pre_install_observation_matches_saved_failure(self):
        pre = self.record["pre_install_observation"]
        self.assertEqual(pre["build"], PREDECESSOR)
        self.assertTrue(pre["flex_installed"])
        self.assertEqual(pre["saved_wallpaper_crash_lines"], self.prepared["failure"]["crash_count_in_saved_trace"])
        self.assertEqual(pre["clock_face_setting"], "null")

    def test_wallpaper_validation(self):
        w = self.record["wallpaper_validation"]
        picker = "com.google.android.apps.wallpaper/com.android.wallpaper.picker.customization.ui.CustomizationPickerActivity2"
        self.assertEqual(w["entry_routes"], {"launcher_long_press": picker, "settings": picker})
        self.assertEqual(w["clock_faces_offered"], FACES)
        self.assertEqual(w["clock_face_count"], 1 + len(KEPT))
        self.assertEqual(w["applied_plugin_clock"]["clock_id"], "DIGITAL_CLOCK_CALLIGRAPHY")
        self.assertEqual(w["restored_default_clock"]["clock_id"], "DEFAULT")
        self.assertEqual(w["setting_restored_to_pre_install_value"], self.record["pre_install_observation"]["clock_face_setting"])
        self.assertEqual(w["crash_fatal_lines_after_session"], 0)
        self.assertEqual(w["plugin_rejection_lines_after_session"], 0)
        self.assertTrue(w["wallpaper_process_pid_constant_across_session"])
        self.assertIn("Clock", w["lock_screen_options_seen"])
        self.assertGreater(w["adb_commands"], 100)

    def test_camera_subset(self):
        c = self.record["camera_subset"]
        for key in ("xiaomi_rear_photo", "xiaomi_front_photo", "aperture_rear_bokeh"):
            media = c[key]["media"]
            self.assertEqual(len(media), 1)
            self.assertTrue(media[0]["decoded"])
            self.assertEqual(media[0]["dimensions"], [3072, 4096])
        ultra = c["xiaomi_ultra_raw"]["media"]
        self.assertEqual(sorted(m["size_bytes"] > 1_000_000 for m in ultra), [True, True])
        self.assertTrue(any(m.get("format") == "JPEG" and m["dimensions"] == [4080, 3072] for m in ultra))
        video = c["xiaomi_rear_video"]
        self.assertEqual((video["video_codec"], video["audio_codec"], video["width"], video["height"]), ("hevc", "aac", 1920, 1080))
        self.assertTrue(5 <= video["duration_seconds"] <= 20)

    def test_cleanup(self):
        cl = self.record["cleanup"]
        self.assertEqual(cl["xiaomi_final_mode"], "rear Photo 1.0X")
        self.assertEqual(cl["xiaomi_pro_format"], "JPEG")
        self.assertEqual(cl["aperture_final_effect"], "NONE")
        self.assertEqual(cl["usb_stay_awake"], "0")
        self.assertTrue(self.record["limits"] and self.record["privacy"])

    def test_pins_are_relative_and_well_formed(self):
        def walk(value):
            if isinstance(value, dict):
                if set(value) == {"path", "sha256", "size_bytes"}:
                    self.assertFalse(Path(value["path"]).is_absolute())
                    self.assertTrue(value["path"].startswith(("reports/", "evidence/")))
                    self.assertRegex(value["sha256"], r"^[0-9a-f]{64}$")
                    self.assertGreater(value["size_bytes"], 0)
                    return
                for v in value.values():
                    walk(v)
            elif isinstance(value, list):
                for v in value:
                    walk(v)
        walk(self.record)


if __name__ == "__main__":
    unittest.main()
