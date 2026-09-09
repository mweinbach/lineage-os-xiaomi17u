"""Offline checks for the IMS selection fragment, activated modules and restored policy."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "device/xiaomi/nezha"
TEMPLATE = ROOT / "templates/ims/Android.bp.in"
ACTIVATED = DEVICE / "ims/Android.bp"
STOCK_SELECTOR = ("user=_app seinfo=platform name=org.codeaurora.ims isPrivApp=true "
                  "domain=vendor_qtelephony type=app_data_file levelFrom=all")


def make(value, extra=""):
    include = DEVICE / "ims.mk"
    text = (f"NEZHA_DEVICE_PATH := {DEVICE}\nTARGET_PRODUCT := lineage_nezha\n{extra}"
            f"NEZHA_IMS := {value}\ninclude {include}\nall:\n\t@true\n")
    with tempfile.TemporaryDirectory() as directory:
        return subprocess.run(["make", "-f", "-", "all"], input=text, cwd=directory, text=True, capture_output=True)


class ImsFragmentTests(unittest.TestCase):
    def test_unset_and_false_select_nothing(self):
        for value in ("", "false"):
            self.assertEqual(make(value).returncode, 0, value)

    def test_true_requires_the_private_bundle(self):
        result = make("true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("vendor/xiaomi/nezha-ims", result.stderr)

    def test_invalid_values_and_wrong_product_fail(self):
        for value in ("tru", "true false", "true true"):
            result = make(value)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("NEZHA_IMS", result.stderr)
        result = make("true", extra="TARGET_PRODUCT := other\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lineage_nezha", result.stderr)

    def test_fragment_selects_exactly_the_reviewed_packages_and_policy(self):
        text = (DEVICE / "ims.mk").read_text()
        packages = re.search(r"PRODUCT_PACKAGES \+= \\\n((?:    .*\\\n)*    .*\n)", text).group(1)
        names = [line.strip().rstrip("\\").strip() for line in packages.splitlines()]
        self.assertEqual(names, ["ims", "qti-telephony-hidl-wrapper", "qti-telephony-utils", "ims-ext-common",
                                 "nezha_ims_libdiagatbparser_system"])
        for line in ("SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/ims/sepolicy/public",
                     "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/ims/sepolicy/private",
                     "PRODUCT_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/ims/overlay",
                     "PRODUCT_SOONG_NAMESPACES += $(NEZHA_DEVICE_PATH)/ims vendor/xiaomi/nezha-ims"):
            self.assertIn(line, text)
        self.assertNotIn("rcs", text.lower().replace("no rcs", ""))
        self.assertIn("include $(NEZHA_DEVICE_PATH)/ims.mk", (DEVICE / "device.mk").read_text())


class ActivatedModuleTests(unittest.TestCase):
    def test_activated_definitions_are_the_template_minus_enabled_false(self):
        template = TEMPLATE.read_text()
        activated = ACTIVATED.read_text()
        code = [l for l in activated.splitlines() if not l.startswith("//")]
        self.assertFalse(any("enabled" in l for l in code))
        strip = lambda text: [l for l in text.splitlines() if not l.startswith("//") and "enabled: false" not in l]
        self.assertEqual(strip(activated), strip(template))
        names = re.findall(r'^    name: "([^"]+)"', activated, re.M)
        self.assertEqual(len(names), 24)
        self.assertEqual(len(set(names)), 24)
        for name in ("ims", "qti-telephony-hidl-wrapper", "qti-telephony-utils", "ims-ext-common",
                     "nezha_ims_libimscamera_jni_app_link", "nezha_ims_libimsmedia_jni_app_link"):
            self.assertIn(name, names)
        self.assertIn('presigned: true', activated)
        self.assertIn('enforce_uses_libs: true', activated)
        self.assertNotIn("optional_uses_libs: [\"", activated)

    def test_permission_and_overlay_files_match_the_reviewed_templates(self):
        contract = json.loads((ROOT / "config/nezha-ims.json").read_text())
        pinned = {row["path"]: row["sha256"] for row in contract["templates"] if row["path"] != "Android.bp.in"}
        self.assertEqual(len(pinned), 3)
        for rel, digest in pinned.items():
            raw = (DEVICE / "ims" / rel).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest, rel)
            self.assertEqual(raw, (ROOT / "templates/ims" / rel).read_bytes())


class RestoredPolicyTests(unittest.TestCase):
    def test_public_type_private_rules_and_stock_selector(self):
        public = (DEVICE / "ims/sepolicy/public/vendor_qtelephony.te").read_text()
        private = (DEVICE / "ims/sepolicy/private/vendor_qtelephony.te").read_text()
        seapp = (DEVICE / "ims/sepolicy/private/seapp_contexts").read_text()
        self.assertIn("type vendor_qtelephony, domain;", public)
        self.assertNotIn("permissive", public + private)
        for macro in ("app_domain(vendor_qtelephony)", "net_domain(vendor_qtelephony)",
                      "hal_client_domain(vendor_qtelephony, hal_telephony)", "binder_use(vendor_qtelephony)",
                      "hwbinder_use(vendor_qtelephony)", "typeattribute vendor_qtelephony coredomain;"):
            self.assertIn(macro, private)
        finds = re.search(r"allow vendor_qtelephony \{([^}]*)\}:service_manager find;", private).group(1).split()
        self.assertEqual(sorted(finds), sorted(["app_api_service", "system_api_service", "radio_service", "audioserver_service",
                                                "cameraserver_service", "drmserver_service", "mediaserver_service",
                                                "mediametrics_service", "mediaextractor_service"]))
        lines = [l for l in seapp.splitlines() if l and not l.startswith("#")]
        self.assertEqual(lines, [STOCK_SELECTOR])
        # No vendor-only names that the shipped vendor policy does not declare.
        rules = "\n".join(l for l in private.splitlines() if not l.startswith("#"))
        for absent in ("vendor_dpmd", "vendor_dpmtcm_socket", "vendor_hal_atfwd_client", "vendor_hal_imsvthal_client"):
            self.assertNotIn(absent, rules)

    def test_generator_lists_every_ims_file(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from scripts import generate_device_tree as generator
        # The fragment may name system_ext policy directories only while its bytes match the pin.
        self.assertEqual(generator.IMS_FRAGMENT_SHA256,
                         hashlib.sha256((DEVICE / "ims.mk").read_bytes()).hexdigest())
        listed = {name for name in generator.TEMPLATE_FILES if name == "ims.mk" or name.startswith("ims/")}
        on_disk = {"ims.mk"} | {p.relative_to(DEVICE).as_posix() for p in (DEVICE / "ims").rglob("*") if p.is_file()}
        self.assertEqual(listed, on_disk)


if __name__ == "__main__":
    unittest.main()
