"""Public source contracts for an ADB request, not USB readiness or a phone test.

Only tracked RC, stock metadata, series and public patches are read. The small
event matcher checks the literal guard, not Android init execution. Transport
checks reuse the existing full-patch parser and conditional source projection.
"""

import hashlib
import itertools
import json
from pathlib import Path
import unittest

from test_twrp_usb_transport import (
    MAIN_NETWORK_TOKENS, RECOVERY_DEFINES, WIFI_NETWORK_TOKENS,
    full_sources, projection,
)


ROOT = Path(__file__).resolve().parents[1]
RC = ROOT / "recovery/twrp/device/xiaomi/nezha/recovery/root/init.recovery.qcom.rc"
OLD_RC_BYTES = 406
OLD_RC_SHA256 = "a5754b16c6aacddf7ce46b136425be6b1d2cbb24518f8da99229da9411abfcfa"
CONTROLLER = "a600000.dwc3"
GUARD = (
    "on post-fs && property:ro.debuggable=0 && property:ro.secure=1 && "
    "property:ro.adb.secure=1 && property:sys.usb.configfs=1 && "
    "property:ro.boot.usbcontroller=" + CONTROLLER
)
ACTIVE_LINES = (
    "on init", "setprop sys.usb.configfs 1",
    "on property:ro.boot.usbcontroller=*",
    "setprop sys.usb.controller ${ro.boot.usbcontroller}",
    GUARD, "setprop sys.usb.controller ${ro.boot.usbcontroller}",
    "setprop sys.usb.config adb",
)


def validate_request_rc(content):
    """Accept this reviewed three-action RC; this is not a general RC parser."""
    if hashlib.sha256(content[:OLD_RC_BYTES]).hexdigest() != OLD_RC_SHA256:
        raise ValueError("Original qcom RC prefix changed")
    lines = tuple(line.strip() for line in content.decode().splitlines()
                  if line.strip() and not line.lstrip().startswith("#"))
    if lines != ACTIVE_LINES:
        raise ValueError("Only the reviewed secure-user request may be appended")
    return lines


def request_matches(trigger, event, properties):
    """Evaluate the reviewed event plus exact property predicates only."""
    if trigger != GUARD:
        raise ValueError("Unexpected request guard")
    parts = trigger.removeprefix("on ").split(" && ")
    expected = dict(part.removeprefix("property:").split("=", 1) for part in parts[1:])
    return event == parts[0] and all(properties.get(name) == value for name, value in expected.items())


class TwrpUsbStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc = RC.read_bytes()
        cls.lines = validate_request_rc(cls.rc)
        cls.stock = json.loads((ROOT / "research/twrp-stock-contract.json").read_text())["usb_and_adb"]
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_text())["patches"]
        cls.rows = {row["id"]: row for row in cls.series}
        cls.usb = cls.rows["0024-recovery-usb-only-adb"]
        cls.auth = cls.rows["0004-require-recovery-adb-auth"]
        cls.payload = (ROOT / cls.usb["patch"]).read_bytes()
        cls.sources = full_sources(cls.payload)
        cls.main = projection(cls.sources["daemon/main.cpp"]["after"].decode(), RECOVERY_DEFINES)
        cls.properties = {"ro.debuggable": "0", "ro.secure": "1", "ro.adb.secure": "1",
                          "sys.usb.configfs": "1", "ro.boot.usbcontroller": CONTROLLER}

    def test_existing_configfs_and_controller_actions_are_preserved(self):
        self.assertEqual(self.lines, ACTIVE_LINES)
        self.assertEqual(self.lines[:4], ACTIVE_LINES[:4])
        self.assertNotIn("PROPOSAL ONLY", self.rc.decode())

    def test_exact_controller_matches_public_stock_contract(self):
        self.assertEqual(self.stock["usb_controller_from_vendor_bootconfig"], CONTROLLER)
        self.assertEqual(self.stock["controller_property_forwarding"], "ro.boot.usbcontroller -> sys.usb.controller")
        self.assertTrue(self.stock["configfs_enabled_by_qcom_recovery_init"])
        self.assertEqual(self.stock["stock_security_properties"]["ro.debuggable"], "0")

    def test_all_five_properties_must_match_when_post_fs_is_processed(self):
        for present in itertools.product((False, True), repeat=5):
            properties = {name: value for (name, value), keep in zip(self.properties.items(), present) if keep}
            with self.subTest(present=present):
                self.assertEqual(request_matches(self.lines[4], "post-fs", properties), all(present))
        for name in self.properties:
            for bad in ("", "unknown", "*", "1" if self.properties[name] == "0" else "0"):
                self.assertFalse(request_matches(self.lines[4], "post-fs", {**self.properties, name: bad}))

    def test_late_property_change_is_not_the_post_fs_event(self):
        for event in ("init", "fs", "boot", "charger", "property:ro.boot.usbcontroller", ""):
            self.assertFalse(request_matches(self.lines[4], event, self.properties))
        self.assertTrue(request_matches(self.lines[4], "post-fs", self.properties))

    def test_existing_userdebug_event_is_not_replaced(self):
        self.assertFalse(request_matches(self.lines[4], "post-fs", {**self.properties, "ro.debuggable": "1"}))
        affected = [row["id"] for row in self.series if row["project"] == "bootable/recovery"
                    and any(item["path"] == "etc/init.rc" for item in row["files"])]
        self.assertEqual(affected, ["0002-do-not-force-adb-root"])
        row = self.rows[affected[0]]
        payload = (ROOT / row["patch"]).read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), row["patch_sha256"])
        self.assertIn(b"\n on fs && property:ro.debuggable=1\n", payload)
        self.assertNotIn("on fs", "\n".join(self.lines))
        # This preserves the startup event; patch24 intentionally changes transport.

    def test_failed_setup_does_not_suppress_a_matching_request(self):
        for mount_ok, bind_ok in itertools.product((False, True), repeat=2):
            properties = {**self.properties, "test.mount_ok": str(mount_ok), "test.bind_ok": str(bind_ok)}
            self.assertTrue(request_matches(self.lines[4], "post-fs", properties))
        self.assertEqual(self.lines[-2:], ACTIVE_LINES[-2:])
        # No real mount or init command runs here; these flags are injected inputs.

    def test_transport_patch_is_bound_to_auth_predecessor_and_exact_postimage(self):
        self.assertEqual(self.usb["base_commit"], "ce023afef190b0cea7f8939e9dd5ee3ee79b137b")
        self.assertEqual(hashlib.sha256(self.payload).hexdigest(),
                         "e472bfde972d168fdc8dd1190298a2891d165a083ce3e02898dcd88e8882d792")
        item = self.usb["files"][0]
        self.assertEqual(item["predecessor_patch_id"], self.auth["id"])
        self.assertEqual(item["before_sha256"], self.auth["files"][0]["after_sha256"])
        for phase in ("before", "after"):
            self.assertEqual(hashlib.sha256(self.sources["daemon/main.cpp"][phase]).hexdigest(), item[phase + "_sha256"])

    def test_missing_functionfs_endpoint_exits_without_socket_fallback(self):
        failure = ('if (access(USB_FFS_ADB_EP0, F_OK) != 0) {\n'
                   '        PLOG(ERROR) << "Recovery ADB requires a USB FunctionFS endpoint";\n'
                   '        return 1;\n    }\n    usb_init();')
        self.assertIn(failure, self.main)
        self.assertLess(self.main.index(failure), self.main.index("fdevent_loop();"))
        for token in MAIN_NETWORK_TOKENS:
            self.assertNotIn(token, self.main)
        wifi = projection(self.sources["daemon/adb_wifi.cpp"]["after"].decode(), RECOVERY_DEFINES)
        for token in WIFI_NETWORK_TOKENS:
            self.assertNotIn(token, wifi)

    def test_authentication_and_shell_privilege_drop_remain_required(self):
        self.assertIn("auth_required = true;", self.main)
        self.assertNotIn("auth_required = false", self.main)
        self.assertIn("adbd_auth_init();", self.main)
        self.assertIn("minijail_change_uid(jail.get(), AID_SHELL);", self.main)
        self.assertIn("if (ro_debuggable && adb_root)", self.main)
        self.assertTrue(self.stock["target_requires_explicit_host_authorization"])
        self.assertFalse(self.stock["stock_key_contents_captured_or_adopted"])
        # No real host signature verification or authorizer UI is exercised.

    def test_no_key_mode_wait_persist_or_root_commands_are_added(self):
        for forbidden in ("exec ", "service ", "mount ", "wait ", "write ", "chmod ",
                          "chown ", "copy ", "adb_keys", "persist.", "service.adb.root", "setenforce"):
            self.assertNotIn(forbidden, "\n".join(self.lines))
        comments = self.rc.decode()
        self.assertIn("not readiness proof", comments)
        self.assertIn("unknown host must remain unauthorized", comments)
        self.assertIn("Init continues after mount/write failure", comments)

    def test_mutations_cannot_widen_guard_or_add_commands(self):
        mutations = [
            self.rc.replace(b"property:ro.boot.usbcontroller=a600000.dwc3", b"property:ro.boot.usbcontroller=*"),
            self.rc.replace(b"on post-fs && ", b"on "),
            self.rc.replace(b"property:ro.debuggable=0", b"property:ro.debuggable=1"),
            self.rc.replace(b"&& property:ro.adb.secure=1 ", b""),
            self.rc + b"\n    setprop service.adb.root 1\n",
            self.rc + b"\n    setprop persist.adb.tcp.port 5555\n",
            self.rc + b"\n    wait /dev/usb-ffs/adb/ep0\n",
            self.rc + b"\n    write /sys/example/mode peripheral\n",
            self.rc + b"\n    copy /data/example /adb_keys\n",
            self.rc.replace(b"setprop sys.usb.config adb", b"setprop sys.usb.config mtp,adb"),
        ]
        for mutated in mutations:
            with self.subTest(content=hashlib.sha256(mutated).hexdigest()), self.assertRaises(ValueError):
                validate_request_rc(mutated)


if __name__ == "__main__":
    unittest.main()
