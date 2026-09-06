"""Offline controller contracts; Java tests use a fake, never Android or a phone."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.generate_device_tree import TEMPLATE_FILES


ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "device/xiaomi/nezha"
APP = DEVICE / "dolby"
SOURCE = APP / "src/org/evolution/nezha/dolby"
ANDROID = "{http://schemas.android.com/apk/res/android}"


class DolbySourceContractTests(unittest.TestCase):
    def test_minimum_permissions_and_no_background_components(self):
        manifest = ET.parse(APP / "AndroidManifest.xml").getroot()
        sdk = manifest.find("uses-sdk")
        self.assertEqual(sdk.get(ANDROID + "minSdkVersion"), "35")
        self.assertEqual(sdk.get(ANDROID + "targetSdkVersion"), "36")
        self.assertEqual({node.get(ANDROID + "name") for node in manifest.findall("uses-permission")}, {
            "android.permission.MODIFY_AUDIO_SETTINGS",
            "android.permission.MODIFY_DEFAULT_AUDIO_EFFECTS",
        })
        application = manifest.find("application")
        self.assertEqual(application.get(ANDROID + "allowBackup"), "false")
        self.assertEqual([node.tag for node in application], ["activity"])
        self.assertIsNone(manifest.get(ANDROID + "sharedUserId"))

    def test_platform_source_build_and_template_coverage(self):
        bp = (APP / "Android.bp").read_text()
        for expected in ('name: "NezhaDolbyController"', "platform_apis: true",
                         'certificate: "platform"', "system_ext_specific: true"):
            self.assertIn(expected, bp)
        for forbidden in ("presigned", "skip_preprocessed", "privileged: true", "android_app_import"):
            self.assertNotIn(forbidden, bp)
        for path in APP.rglob("*"):
            if path.is_file():
                self.assertIn(path.relative_to(DEVICE).as_posix(), TEMPLATE_FILES)
        self.assertIn("dolby.mk", TEMPLATE_FILES)

    def test_activity_has_no_lifecycle_effect_calls_and_handles_insets(self):
        source = (SOURCE / "MainActivity.java").read_text()
        self.assertIn("WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout()", source)
        self.assertIn("if (!rendering) perform", source)
        self.assertIn("enabled.setSaveEnabled(false)", source)
        self.assertIn("profiles.setSaveEnabled(false)", source)
        self.assertIn("disconnect();", source)
        for line in source.splitlines():
            if "controller.inspect()" in line or "controller.set" in line:
                self.assertIn("perform(() ->", line)
        for forbidden in ("onResume(", "SharedPreferences", "BOOT_COMPLETED", "java.lang.reflect"):
            self.assertNotIn(forbidden, source)

    @unittest.skipUnless(shutil.which("make"), "make not installed")
    def test_make_flag_unset_true_false_and_malformed(self):
        makefile = f"include {DEVICE / 'dolby.mk'}\nall:\n\t@echo packages=$(PRODUCT_PACKAGES)\n"
        with tempfile.TemporaryDirectory() as temp:
            for value, expected in ((None, "packages="), ("false", "packages="),
                                    ("true", "packages=NezhaDolbyController")):
                args = ["make", "--no-print-directory", "-f", "-", "all"]
                if value is not None:
                    args.append("NEZHA_DOLBY_CONTROLLER=" + value)
                result = subprocess.run(args, input=makefile, text=True, capture_output=True, cwd=temp)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
            for value in ("yes", "TRUE", "1", "true false", "true true"):
                result = subprocess.run(
                    ["make", "--no-print-directory", "-f", "-", "all", "NEZHA_DOLBY_CONTROLLER=" + value],
                    input=makefile, text=True, capture_output=True, cwd=temp)
                self.assertNotEqual(result.returncode, 0, value)


FAKE_EFFECT = r'''
package android.media.audiofx;
import java.nio.*;
import java.util.UUID;
public class AudioEffect {
    public static int creations, releases, writes, reads, frameworkWrites;
    public static int enabled = 1, profile = 2, profiles = 9, responseSize = 4;
    public static int writeStatus, enableStatus;
    public static boolean control = true, frameworkEnabled = true, ignoreWrites, releaseFails;
    public AudioEffect(UUID type, UUID implementation, int priority, int session) {
        if (!type.toString().equals("ec7178ec-e5e1-4432-a3f4-4657e6795210") ||
            !implementation.toString().equals("9d4921da-8225-4f29-aefa-39537a04bcaa") ||
            priority != 0 || session != 0) throw new AssertionError("effect identity");
        creations++;
    }
    public boolean hasControl() { return control; }
    public boolean getEnabled() { return frameworkEnabled; }
    public int getParameter(int key, byte[] buffer) {
        if (buffer.length != 12) throw new AssertionError("query length");
        ByteBuffer bytes = ByteBuffer.wrap(buffer).order(ByteOrder.LITTLE_ENDIAN);
        int parameter = bytes.getInt();
        if (key != parameter + 5 || bytes.getInt() != 0 || bytes.getInt() != 0)
            throw new AssertionError("query layout");
        int value;
        if (parameter == 0) value = enabled;
        else if (parameter == 0x03000000) value = profiles;
        else if (parameter == 0x0a000000) value = profile;
        else throw new AssertionError("query parameter");
        bytes.putInt(0, value); reads++;
        return responseSize;
    }
    public int setParameter(int key, byte[] buffer) {
        if (key != 5 || buffer.length != 12) throw new AssertionError("write key/length");
        ByteBuffer bytes = ByteBuffer.wrap(buffer).order(ByteOrder.LITTLE_ENDIAN);
        int parameter = bytes.getInt();
        if (bytes.getInt() != 1) throw new AssertionError("write operation");
        int value = bytes.getInt(); writes++;
        if (writeStatus == 0 && !ignoreWrites) {
            if (parameter == 0) enabled = value;
            else if (parameter == 0x0a000000) profile = value;
            else throw new AssertionError("write parameter");
        }
        return writeStatus;
    }
    public int setEnabled(boolean value) {
        frameworkWrites++;
        if (enableStatus == 0 && !ignoreWrites) frameworkEnabled = value;
        return enableStatus;
    }
    public void release() {
        releases++;
        if (releaseFails) throw new IllegalStateException("fake release failure");
    }
}
'''

HARNESS = r'''
package org.evolution.nezha.dolby;
import android.media.audiofx.AudioEffect;
import java.util.Arrays;
public final class Harness {
    static void check(boolean value) { if (!value) throw new AssertionError(); }
    static void rejects(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("expected rejection");
    }
    public static void main(String[] args) {
        DolbyController controller = new DolbyController();
        check(AudioEffect.creations == 0);
        switch (args[0]) {
            case "protocol":
                check(Arrays.equals(DolbyProtocol.change(0x0a000000, 2),
                    new byte[]{0,0,0,10,1,0,0,0,2,0,0,0}));
                check(DolbyProtocol.decode(new byte[]{4,3,2,1}, 4) == 0x01020304);
                for (int size : new int[]{-5,0,1,2,3,13})
                    rejects(() -> DolbyProtocol.decode(new byte[12], size));
                rejects(() -> DolbyProtocol.change(DolbyProtocol.PROFILE_COUNT, 2));
                rejects(() -> DolbyProtocol.checkStatus("test", 1));
                check("Voice".equals(DolbyProtocol.knownProfileName(8)));
                check(DolbyProtocol.knownProfileName(9) == null);
                break;
            case "inspect":
                DolbyController.State initial = controller.inspect();
                check(initial.enabled && initial.frameworkEnabled);
                check(initial.currentProfile == 2 && initial.profileCount == 9);
                check(AudioEffect.writes == 0 && AudioEffect.frameworkWrites == 0);
                controller.close(); controller.close();
                check(AudioEffect.releases == 1);
                controller.inspect(); check(AudioEffect.creations == 2);
                break;
            case "write":
                check(!controller.setEnabled(false).enabled);
                check(AudioEffect.writes == 1 && AudioEffect.frameworkWrites == 1);
                check(controller.setProfile(8).currentProfile == 8);
                check(AudioEffect.writes == 2);
                rejects(() -> controller.setProfile(-1));
                rejects(() -> controller.setProfile(9));
                check(AudioEffect.writes == 2);
                break;
            case "control":
                AudioEffect.control = false;
                rejects(controller::inspect);
                rejects(() -> controller.setEnabled(false));
                check(AudioEffect.reads == 0 && AudioEffect.writes == 0);
                break;
            case "response":
                for (int size : new int[]{-4,0,3,13}) {
                    AudioEffect.responseSize = size;
                    rejects(controller::inspect);
                    rejects(() -> controller.setEnabled(false));
                }
                check(AudioEffect.writes == 0);
                break;
            case "state":
                AudioEffect.enabled = 2; rejects(controller::inspect);
                AudioEffect.enabled = 1;
                for (int count : new int[]{-1,0,33}) {
                    AudioEffect.profiles = count; rejects(controller::inspect);
                }
                AudioEffect.profiles = 9; AudioEffect.profile = 9;
                rejects(() -> controller.setEnabled(false));
                check(AudioEffect.writes == 0);
                break;
            case "status":
                AudioEffect.writeStatus = -5;
                rejects(() -> controller.setEnabled(false));
                check(AudioEffect.frameworkWrites == 0);
                AudioEffect.writeStatus = 0; AudioEffect.enableStatus = -5;
                rejects(() -> controller.setEnabled(false));
                check(AudioEffect.enabled == 0 && AudioEffect.frameworkEnabled);
                break;
            case "readback":
                AudioEffect.ignoreWrites = true;
                rejects(() -> controller.setEnabled(false));
                rejects(() -> controller.setProfile(8));
                break;
            case "release":
                controller.inspect(); AudioEffect.releaseFails = true;
                rejects(controller::close);
                AudioEffect.releaseFails = false;
                controller.inspect(); check(AudioEffect.creations == 2);
                break;
            default: throw new AssertionError("unknown case");
        }
        controller.close();
    }
}
'''


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK not installed")
class DolbyJavaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        fake = directory / "android/media/audiofx/AudioEffect.java"
        fake.parent.mkdir(parents=True)
        fake.write_text(FAKE_EFFECT)
        harness = directory / "Harness.java"
        harness.write_text(HARNESS)
        result = subprocess.run([
            "javac", "-d", str(directory), str(fake), str(SOURCE / "DolbyProtocol.java"),
            str(SOURCE / "DolbyController.java"), str(harness)],
            capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)

    def check_case(self, case):
        result = subprocess.run(["java", "-cp", self.temp.name,
                                 "org.evolution.nezha.dolby.Harness", case],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_packet_encoding_lengths_and_allowlist(self): self.check_case("protocol")
    def test_lazy_inspection_release_and_reconnect(self): self.check_case("inspect")
    def test_enable_and_profile_with_readback_and_bounds(self): self.check_case("write")
    def test_missing_control_blocks_queries_and_writes(self): self.check_case("control")
    def test_short_or_failed_responses_block_writes(self): self.check_case("response")
    def test_invalid_enable_or_profile_state_blocks_writes(self): self.check_case("state")
    def test_failed_write_and_partial_enable_are_rejected(self): self.check_case("status")
    def test_success_status_without_matching_readback_is_rejected(self): self.check_case("readback")
    def test_failed_release_does_not_reuse_stale_handle(self): self.check_case("release")


if __name__ == "__main__":
    unittest.main()
