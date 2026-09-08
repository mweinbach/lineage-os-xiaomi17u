"""Offline checks for the clock plugin audit and the Flex removal contract.

Synthetic APKs are ZIP files carrying only the DEX descriptor strings and the
manifest action string the audit reads. No Android tool, APK or phone is used.
"""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import systemui_clock_plugin_audit as audit


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/systemui-clocks-flex-removal.json"
PATCH = ROOT / "patches/evolution/0039-remove-stale-systemui-clocks-flex.patch"
NEW = "Lcom/android/systemui/plugins/keyguard/ui/clocks/ClockProviderPlugin;"
OLD = "Lcom/android/systemui/plugins/clocks/ClockProviderPlugin;"
# Identities measured from the vendor/extras checkout at c401d732 and the
# generated patch; a changed byte in either file changes the build identity.
BEFORE_SHA = "247015dc34d77625e9fba96def23c07a79722c4d711a876cc6eafc7969e133fb"
AFTER_SHA = "00cec0caeff933975b06fc5cd4a53b6b0b39cf7557bfd0ef497aeea44b692ec5"
PATCH_SHA = "dd332a12b5672b0cf0248d30a0c028d8f2b6788c065ef29f2bc5d1d612912052"
KEPT_CLOCKS = ("BigNum", "Calligraphy", "Growth", "Inflate", "Metro", "NumOverlap", "Weather")


def apk(descriptors=(), action=False, utf16=True, manifest=True, extra_dex=b""):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        dex = b"dex\n035\0" + b"\0".join(d.encode() for d in descriptors) + extra_dex
        archive.writestr("classes.dex", dex)
        archive.writestr("classes2.dex", b"dex\n035\0")
        if manifest:
            text = audit.ACTION if action else "android.intent.action.MAIN"
            body = text.encode("utf-16-le") if utf16 else text.encode()
            archive.writestr("AndroidManifest.xml", b"\x03\x00\x08\x00" + body)
        archive.writestr("resources.arsc", b"\x02\x00")
    return buffer.getvalue()


HOST = apk([NEW, audit.PROVIDES_INTERFACE.decode(), audit.VERSION_INFO.decode(), audit.REQUIRES.decode()])
GOOD_PLUGIN = apk([NEW, audit.REQUIRES.decode()], action=True)
STALE_PLUGIN = apk([OLD, audit.PROVIDES_INTERFACE.decode(), audit.REQUIRES.decode()], action=True, utf16=False)


class ClassificationTests(unittest.TestCase):
    def test_host_plugin_and_bystander_roles(self):
        host = audit.classify("host.apk", HOST)
        plugin = audit.classify("plugin.apk", GOOD_PLUGIN)
        other = audit.classify("other.apk", apk([NEW, audit.PROVIDES_INTERFACE.decode()]))
        self.assertEqual((host["role"], plugin["role"], other["role"]), ("host", "plugin", "other"))
        self.assertEqual(host["clock_provider_interfaces"], [NEW])
        self.assertFalse(host["bundles_plugin_interface_copy"])
        self.assertTrue(plugin["declares_clock_provider_action"])
        self.assertTrue(other["bundles_plugin_interface_copy"])
        self.assertEqual(host["sha256"], hashlib.sha256(HOST).hexdigest())

    def test_action_is_found_in_both_manifest_encodings(self):
        self.assertTrue(audit.classify("a", apk([NEW], action=True, utf16=True))["declares_clock_provider_action"])
        self.assertTrue(audit.classify("b", apk([NEW], action=True, utf16=False))["declares_clock_provider_action"])
        self.assertFalse(audit.classify("c", apk([NEW]))["declares_clock_provider_action"])

    def test_descriptor_variants_are_not_confused_with_the_interface(self):
        row = audit.classify("p", apk([NEW.replace(";", "$Companion;"), NEW.replace(";", "Protector;"),
                                       NEW.replace("ClockProviderPlugin", "ClockProviderPluginKt")], action=True))
        self.assertEqual(row["clock_provider_interfaces"], [])

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.classify("x", b"not a zip")
        with self.assertRaises(audit.AuditError):
            audit.classify("x", apk([NEW], manifest=False))
        with self.assertRaises(audit.AuditError):
            audit.read_apk(bytearray(HOST))


class CheckTests(unittest.TestCase):
    def test_matching_host_and_plugins_pass(self):
        report = audit.check([audit.classify("host", HOST), audit.classify("a", GOOD_PLUGIN),
                              audit.classify("b", GOOD_PLUGIN)])
        self.assertTrue(report["passed"])
        self.assertEqual((report["host_count"], report["plugin_count"], report["host_interfaces"]), (2 - 1, 2, [NEW]))

    def test_stale_plugin_fails_for_both_reasons(self):
        report = audit.check([audit.classify("host", HOST), audit.classify("flex", STALE_PLUGIN)])
        self.assertFalse(report["passed"])
        self.assertEqual([f["kind"] for f in report["failures"]],
                         ["plugin_interface_not_provided_by_host", "plugin_bundles_interface_copy"])
        self.assertEqual(report["failures"][0]["foreign_interfaces"], [OLD])
        self.assertEqual(report["failures"][0]["host_interfaces"], [NEW])

    def test_missing_host_plugin_without_interface_and_host_disagreement(self):
        no_host = audit.check([audit.classify("a", GOOD_PLUGIN)])
        self.assertEqual([f["kind"] for f in no_host["failures"]], ["no_host"])
        self.assertFalse(no_host["passed"])
        empty = audit.check([audit.classify("host", HOST), audit.classify("p", apk([audit.REQUIRES.decode()], action=True))])
        self.assertEqual([f["kind"] for f in empty["failures"]], ["plugin_without_interface"])
        old_host = apk([OLD, audit.VERSION_INFO.decode()])
        split = audit.check([audit.classify("h1", HOST), audit.classify("h2", old_host), audit.classify("a", GOOD_PLUGIN)])
        kinds = [f["kind"] for f in split["failures"]]
        self.assertIn("host_interface_disagreement", kinds)
        self.assertIn("plugin_interface_not_provided_by_host", kinds)


class ArchiveTests(unittest.TestCase):
    def _archive(self, path, include_flex):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("SYSTEM_EXT/priv-app/SystemUI/SystemUI.apk", HOST)
            archive.writestr("SYSTEM_EXT/priv-app/SystemUIClocks-BigNum/SystemUIClocks-BigNum.apk", GOOD_PLUGIN)
            archive.writestr("PRODUCT/app/Bystander/Bystander.apk", apk(["Lfoo/Bar;"]))
            archive.writestr("VENDOR/app/Ignored/Ignored.apk", STALE_PLUGIN)
            archive.writestr("SYSTEM/build.prop", "ro.build.type=userdebug\n")
            if include_flex:
                archive.writestr("SYSTEM_EXT/priv-app/SystemUIClocks-Flex/SystemUIClocks-Flex.apk", STALE_PLUGIN)

    def test_archive_scan_expectations_and_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "good.zip"), Path(tmp, "bad.zip")
            self._archive(good, include_flex=False)
            self._archive(bad, include_flex=True)
            out = Path(tmp, "report.json")
            quiet = contextlib.redirect_stdout(io.StringIO())
            with quiet:
                code = audit.main(["check", "--target-files", str(good), "--expect-absent", "SystemUIClocks-Flex",
                               "--expect-present", "SystemUIClocks-BigNum", "--output", str(out)])
            report = json.loads(out.read_text())
            self.assertEqual(code, 0)
            self.assertTrue(report["passed"])
            self.assertEqual(report["packaged_modules_scanned"], 3)
            self.assertEqual([row["name"].split("/")[-1] for row in report["rows"]], ["SystemUI.apk", "SystemUIClocks-BigNum.apk"])
            with quiet:
                code = audit.main(["check", "--target-files", str(bad), "--expect-absent", "SystemUIClocks-Flex",
                                   "--expect-present", "SystemUIClocks-Weather"])
            self.assertEqual(code, 1)
            with quiet:
                code = audit.main(["inspect", "--target-files", str(bad), "--expect-absent", "SystemUIClocks-Flex"])
            self.assertEqual(code, 1)
            with quiet:
                code = audit.main(["inspect", "--target-files", str(good), "--expect-absent", "SystemUIClocks-Flex"])
            self.assertEqual(code, 0)

    def test_apk_arguments_are_required(self):
        with self.assertRaises(audit.AuditError):
            audit.main(["check"])


class ContractTests(unittest.TestCase):
    def test_contract_pin_matches_file(self):
        self.assertEqual(hashlib.sha256(CONTRACT.read_bytes()).hexdigest(), audit.CONTRACT_SHA256)

    def test_patch_reproduces_pinned_source_identities(self):
        report = audit.contract_report()
        self.assertEqual(hashlib.sha256(PATCH.read_bytes()).hexdigest(), PATCH_SHA)
        self.assertEqual((report["before"]["sha256"], report["after"]["sha256"]), (BEFORE_SHA, AFTER_SHA))
        self.assertEqual(report["file"], "evolution.mk")
        self.assertEqual(report["project"], "vendor/extras")
        self.assertEqual(report["removed_lines"], ["    SystemUIClocks-Flex \\\n"])
        self.assertTrue(all(line.startswith("#") for line in report["added_lines"]))

    def test_only_flex_leaves_the_package_list(self):
        report = audit.contract_report()
        for name in KEPT_CLOCKS:
            self.assertIn("    SystemUIClocks-%s" % name, report["before_text"])
            self.assertIn("    SystemUIClocks-%s" % name, report["after_text"])
        self.assertIn("    SystemUIClocks-Flex \\\n", report["before_text"])
        self.assertNotIn("SystemUIClocks-Flex \\", report["after_text"])
        self.assertEqual(report["after_text"].count("SystemUIClocks-Flex"), 1)
        # The Flex import block is not the change; only its product selection is.
        self.assertEqual(report["before_text"].replace("    SystemUIClocks-Flex \\\n", "").count("\n") + 4,
                         report["after_text"].count("\n"))

    def test_contract_rejects_tampered_patch(self):
        contract = json.loads(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "patches/evolution").mkdir(parents=True)
            patched = PATCH.read_bytes().replace(b"-    SystemUIClocks-Flex \\\n", b"-    SystemUIClocks-Weather \\\n")
            (root / contract["patch"]).write_bytes(patched)
            contract["patch_sha256"] = hashlib.sha256(patched).hexdigest()
            raw = json.dumps(contract).encode()
            (root / "config/contract.json").write_bytes(raw)
            with self.assertRaises(audit.AuditError):
                audit.contract_report(root / "config/contract.json", hashlib.sha256(raw).hexdigest())
            with self.assertRaises(audit.AuditError):
                audit.contract_report(CONTRACT, "0" * 64)


if __name__ == "__main__":
    unittest.main()


class RecordTests(unittest.TestCase):
    """Tie the sanitized v14 record to the contract and patch it claims."""
    RECORD = ROOT / "research/wallpaper-clock-plugin-20260908.json"

    def test_record_pins_recompute_from_tracked_files(self):
        record = json.loads(self.RECORD.read_text())
        contract = json.loads(CONTRACT.read_text())
        for pin in (record["source_change"]["contract"], record["source_change"]["patch"]):
            raw = (ROOT / pin["path"]).read_bytes()
            self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)), (pin["sha256"], pin["size_bytes"]), pin["path"])
        self.assertEqual(record["source_change"]["before_sha256"], contract["files"]["evolution.mk"]["before_sha256"])
        self.assertEqual(record["source_change"]["after_sha256"], contract["files"]["evolution.mk"]["after_sha256"])
        self.assertEqual(record["diagnosis"]["host_interface_descriptor"], "L" + NEW[1:])
        self.assertEqual(record["diagnosis"]["flex_interface_descriptor"], OLD)
        self.assertEqual(record["diagnosis"]["retained_flex_apk"], contract["retained_flex_apk"])

    def test_record_keeps_device_gates_open_and_only_flex_removed(self):
        record = json.loads(self.RECORD.read_text())
        self.assertFalse(record["installed"] or record["flash_authorized"] or record["phone_accessed"]
                         or record["wallpaper_fix_verified_on_device"])
        self.assertRegex(record["build_number"], r"^nezha\.[0-9a-f]{24}$")
        self.assertNotEqual(record["build_number"], record["installed_predecessor"])
        for phase in ("unsigned", "signed"):
            summary = record["verification"]["archive_diff_summary"][phase]
            self.assertEqual(summary["removed"], ["SYSTEM_EXT/priv-app/SystemUIClocks-Flex/",
                                                  "SYSTEM_EXT/priv-app/SystemUIClocks-Flex/SystemUIClocks-Flex.apk"])
            self.assertEqual(summary["added"], [])
            self.assertEqual(summary["previous_members"] - summary["members"], 2)
            self.assertEqual(summary["identical"] + summary["changed"] + 2, summary["previous_members"])
            audit_summary = record["verification"]["clock_plugin_audit_summary"][phase]
            self.assertTrue(audit_summary["passed"])
            self.assertEqual((audit_summary["plugins"], audit_summary["host_interfaces"]), (7, ["L" + NEW[1:]]))
        self.assertEqual(sorted(record["diagnosis"]["kept_clock_plugins"]), sorted(KEPT_CLOCKS))
        self.assertEqual(record["source_change"]["source_rows"], record["source_change"]["preserved_predecessor_rows"] + 1)
