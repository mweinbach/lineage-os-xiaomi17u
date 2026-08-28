"""Offline invariants for the real TWRP target, not a device boot test."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "recovery/twrp/device/xiaomi/nezha"


def logical_lines(text):
    """Read the simple continued assignments used by this authored target."""
    pending = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        if pending or line:
            yield pending + line
        pending = ""
    if pending:
        raise ValueError("unterminated make continuation")


def assignments(text):
    """Return literal make values; intentionally do not execute make or shells."""
    values = {}
    pattern = re.compile(r"^([A-Z][A-Z0-9_]*)\s*(:=|\+=|\?=|=)\s*(.*)$")
    for line in logical_lines(text):
        match = pattern.match(line)
        if not match:
            continue
        name, operation, value = match.groups()
        if operation == "+=":
            values[name] = " ".join(filter(None, (values.get(name, ""), value)))
        elif operation != "?=" or name not in values:
            values[name] = value
    return values


class TwrpDeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board_text = (DEVICE / "BoardConfig.mk").read_text()
        cls.product_text = (DEVICE / "twrp_nezha.mk").read_text()
        cls.device_text = (DEVICE / "device.mk").read_text()
        cls.board = assignments(cls.board_text)
        cls.product = assignments(cls.product_text)
        cls.device = assignments(cls.device_text)
        cls.stock = json.loads((ROOT / "research/recovery-plan.json").read_text())["stock"]
        cls.baseline = json.loads((ROOT / "research/device-baseline.json").read_text())

    def test_target_has_its_own_product_and_restricted_lunch_choices(self):
        products = assignments((DEVICE / "AndroidProducts.mk").read_text())
        self.assertEqual(products["PRODUCT_MAKEFILES"], "$(LOCAL_DIR)/twrp_nezha.mk")
        self.assertEqual(products["COMMON_LUNCH_CHOICES"].split(), [
            "twrp_nezha-bp2a-userdebug", "twrp_nezha-bp2a-user"])
        self.assertEqual(self.product["PRODUCT_NAME"], "twrp_nezha")
        self.assertIn("lineage_nezha.mk", (ROOT / "device/xiaomi/nezha/AndroidProducts.mk").read_text())

    def test_product_inherits_only_reviewed_source_ramdisk_and_own_device(self):
        inherits = re.findall(r"\$\(call inherit-product,\s*(.*?)\)", self.product_text)
        # The nested SRC_TARGET_DIR expansion is checked as a complete line.
        self.assertEqual(len(inherits), 3)
        self.assertEqual([line for line in logical_lines(self.product_text)
                          if line.startswith("$(call inherit-product,")], [
            "$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)",
            "$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)",
            "$(call inherit-product, device/xiaomi/nezha/device.mk)"])
        active = "\n".join(logical_lines(self.product_text + self.device_text + self.board_text))
        for unadmitted in ("vendor/lineage/", "vendor/evolution/", "vendor/xiaomi/",
                           "vendor/twrp/config/common.mk", "generated/", "stock-prebuilt.mk"):
            self.assertNotIn(unadmitted, active)

    def test_identity_matches_nezha_without_another_soc_or_rom_fingerprint(self):
        observed = self.baseline["device"]
        self.assertEqual(self.product["PRODUCT_DEVICE"], observed["codename"])
        self.assertEqual(self.product["PRODUCT_MANUFACTURER"], observed["manufacturer"])
        self.assertEqual(self.board["TARGET_BOARD_PLATFORM"], observed["board_platform"])
        self.assertEqual(self.board["TARGET_BOOTLOADER_BOARD_NAME"], "canoe")
        self.assertEqual(self.board["TARGET_ARCH"], "arm64")
        self.assertEqual(self.board["TARGET_CPU_ABI"], observed["abi"])
        self.assertEqual(self.board["TARGET_CPU_VARIANT"], "generic")
        self.assertEqual(self.product["PRODUCT_SHIPPING_API_LEVEL"], "36")
        for forbidden in ("BUILD_FINGERPRINT", "PRODUCT_BUILD_PROP_OVERRIDES",
                          "PLATFORM_VERSION", "PLATFORM_VERSION_LAST_STABLE",
                          "PLATFORM_SECURITY_PATCH", "VENDOR_SECURITY_PATCH", "BOOT_SECURITY_PATCH"):
            self.assertNotIn(forbidden, self.board | self.product | self.device)
        self.assertNotIn("2099", self.board_text)

    def test_only_dedicated_recovery_image_is_selected(self):
        enabled = {key for key, value in self.device.items()
                   if key.startswith("PRODUCT_BUILD_") and value == "true"}
        self.assertEqual(enabled, {"PRODUCT_BUILD_RECOVERY_IMAGE"})
        for image in ("BOOT", "INIT_BOOT", "VENDOR_BOOT", "SYSTEM", "SYSTEM_EXT", "PRODUCT",
                      "VENDOR", "ODM", "USERDATA", "CACHE", "VBMETA"):
            self.assertEqual(self.device[f"PRODUCT_BUILD_{image}_IMAGE"], "false", image)
        self.assertEqual(self.board["TARGET_NO_KERNEL"], "true")
        self.assertEqual(self.board["TARGET_NO_RECOVERY"], "false")
        self.assertEqual(self.board["BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE"], "true")
        for setting in ("BOARD_USES_RECOVERY_AS_BOOT", "BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT",
                        "BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT"):
            self.assertEqual(self.board[setting], "false", setting)

    def test_header_ramdisk_and_capacity_match_the_factory_contract(self):
        header = self.stock["headers"]["recovery"]
        limit = self.stock["package_gpt_contract"]["partition_size_bytes_per_slot"]["recovery"]
        self.assertEqual(int(self.board["BOARD_BOOT_HEADER_VERSION"]), header["header_version"])
        self.assertNotIn("BOARD_BOOTIMG_HEADER_VERSION", self.board)
        self.assertEqual(self.board["BOARD_RECOVERY_MKBOOTIMG_ARGS"], "--header_version 4")
        self.assertEqual(self.board["BOARD_RAMDISK_USE_LZ4"], "true")
        self.assertEqual(int(self.board["BOARD_RECOVERYIMAGE_PARTITION_SIZE"]), limit)
        self.assertEqual(header["kernel_size_bytes"], 0)
        for setting in ("TARGET_PREBUILT_KERNEL", "BOARD_PREBUILT_DTBIMAGE_DIR",
                        "BOARD_PREBUILT_DTBOIMAGE", "BOARD_INCLUDE_DTB_IN_BOOTIMG",
                        "BOARD_KERNEL_BASE", "BOARD_KERNEL_CMDLINE"):
            self.assertNotIn(setting, self.board)

    def test_avb_keeps_explicit_test_signing_and_recovery_rollback_roles(self):
        self.assertEqual(self.board["BOARD_AVB_ENABLE"], "true")
        self.assertEqual(self.board["BOARD_AVB_RECOVERY_KEY_PATH"],
                         "external/avb/test/data/testkey_rsa4096.pem")
        self.assertEqual(self.board["BOARD_AVB_RECOVERY_ALGORITHM"], "SHA256_RSA4096")
        chain = self.stock["recovery_chain"]
        self.assertEqual(int(self.board["BOARD_AVB_RECOVERY_ROLLBACK_INDEX"]), chain["rollback_index"])
        self.assertEqual(int(self.board["BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION"]),
                         chain["rollback_index_location"])
        self.assertNotIn("BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION", self.board)
        for forbidden in ("--disable-verity", "--disable-verification", "--flags 2", "--flags 3"):
            self.assertNotIn(forbidden, self.board_text)

    def test_fstab_exposes_no_writable_or_raw_partition(self):
        fstab = (DEVICE / "recovery.fstab").read_text()
        self.assertEqual(list(logical_lines(fstab)), [])
        self.assertEqual(self.board["TARGET_RECOVERY_FSTAB"],
                         "$(NEZHA_TWRP_DEVICE_PATH)/recovery.fstab")
        self.assertEqual(self.board["TW_SKIP_ADDITIONAL_FSTAB"], "true")
        self.assertIn("F2FS", fstab)
        self.assertIn("metadata_encryption=aes-256-xts:wrappedkey_v0", fstab)
        for path in DEVICE.rglob("*fstab*"):
            self.assertEqual(path.name, "recovery.fstab")

    def test_unvalidated_storage_crypto_and_mutation_features_are_not_enabled(self):
        for setting in ("TW_INCLUDE_CRYPTO", "TW_INCLUDE_CRYPTO_FBE", "TW_INCLUDE_LIBRESETPROP",
                        "TW_INCLUDE_RESETPROP", "TW_INCLUDE_REPACKTOOLS", "TW_INCLUDE_FASTBOOTD",
                        "TW_INCLUDE_LPTOOLS", "TW_INCLUDE_LPDUMP", "TW_USE_DMCTL", "TW_ENABLE_BLKDISCARD"):
            self.assertEqual(self.board[setting], "false", setting)
        for setting in ("TW_EXCLUDE_APEX", "TW_EXCLUDE_MTP", "TW_NO_USB_STORAGE",
                        "TW_NO_FLASH_CURRENT_TWRP"):
            self.assertEqual(self.board[setting], "true", setting)
        for setting in ("AB_OTA_UPDATER", "PRODUCT_USE_DYNAMIC_PARTITIONS", "PRODUCT_VIRTUAL_AB_OTA",
                        "TW_OVERRIDE_SYSTEM_PROPS", "TW_PREPARE_DATA_MEDIA_EARLY"):
            self.assertNotEqual((self.board | self.device).get(setting), "true", setting)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")

    def test_adb_security_is_explicit_and_no_host_or_stock_keys_are_bundled(self):
        properties = dict(value.split("=", 1) for value in
                          self.device["PRODUCT_SYSTEM_DEFAULT_PROPERTIES"].split())
        self.assertEqual(properties, {"ro.secure": "1", "ro.adb.secure": "1"})
        active = "\n".join(logical_lines(self.product_text + self.device_text + self.board_text))
        self.assertNotIn("PRODUCT_ADB_KEYS", active)
        self.assertNotIn("service.adb.root", active)
        self.assertNotIn("persist.sys.disable_rescue", active)
        self.assertFalse(any(path.name == "adb_keys" for path in DEVICE.rglob("*")))

    def test_authored_init_only_forwards_verified_controller_contract(self):
        rc = (DEVICE / "recovery/root/init.recovery.qcom.rc").read_text()
        self.assertEqual(list(logical_lines(rc)), [
            "on init", "setprop sys.usb.configfs 1",
            "on property:ro.boot.usbcontroller=*",
            "setprop sys.usb.controller ${ro.boot.usbcontroller}"])
        self.assertEqual(self.board["TW_EXCLUDE_DEFAULT_USB_INIT"], "true")
        self.assertIn("recovery/root/init.recovery.qcom.rc", self.device["PRODUCT_COPY_FILES"])

    def test_runtime_loader_inputs_are_not_duplicated_or_replaced(self):
        active = "\n".join(logical_lines(self.board_text + self.device_text))
        for item in ("BOARD_RECOVERY_KERNEL_MODULES", "TW_LOAD_VENDOR_MODULES", "modprobe", "insmod"):
            self.assertNotIn(item, active)
        for path in DEVICE.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix, {".ko", ".img", ".bin", ".apk", ".apex", ".pem", ".pk8", ".key"})
                self.assertNotEqual(path.read_bytes()[:4], b"\x7fELF")

    def test_source_policy_forbids_recovery_disabling_selinux(self):
        policy = (DEVICE / "sepolicy/recovery.te").read_text()
        active = "\n".join(logical_lines(policy))
        self.assertIn("neverallow recovery kernel:security setenforce;", active)
        self.assertNotRegex(active, r"\bpermissive\s+\w+\s*;")
        self.assertEqual(self.board["BOARD_SEPOLICY_DIRS"], "$(NEZHA_TWRP_DEVICE_PATH)/sepolicy")
        self.assertEqual(self.device["PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING"], "true")

    def test_board_guards_keep_validation_and_correct_image_layout(self):
        self.assertIn("$(filter $(TARGET_BUILD_VARIANT),user userdebug)", self.board_text)
        self.assertIn("ifeq ($(strip $(TARGET_BUILD_VARIANT)),)", self.board_text)
        for flag in ("ALLOW_MISSING_DEPENDENCIES", "SELINUX_IGNORE_NEVERALLOWS",
                     "BUILD_BROKEN_DUP_RULES", "BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES",
                     "BUILD_BROKEN_DUP_SYSPROP", "BUILD_BROKEN_PLUGIN_VALIDATION"):
            self.assertIn(f"$({flag})", self.board_text)
            self.assertNotEqual(self.board.get(flag), "true", flag)
        self.assertIn("ifneq ($(BOARD_AVB_ENABLE),true)", self.board_text)
        self.assertIn("ifneq ($(BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE),true)", self.board_text)
        self.assertIn("recoveryimage-nodeps bootimage vendorbootimage initbootimage", self.board_text)

    def test_hardware_defaults_do_not_invent_paths_or_readiness(self):
        self.assertEqual(self.board["TW_THEME"], "portrait_hdpi")
        for setting in ("TW_CUSTOM_TOUCH_DEVICE", "TW_BRIGHTNESS_PATH", "TW_MAX_BRIGHTNESS",
                        "TARGET_SCREEN_WIDTH", "TARGET_SCREEN_HEIGHT", "TARGET_RECOVERY_PIXEL_FORMAT",
                        "TW_ROTATION", "RECOVERY_GRAPHICS_FORCE_USE_LINELENGTH"):
            self.assertNotIn(setting, self.board)
        self.assertEqual(self.board["TARGET_USES_LOGD"], "true")
        self.assertEqual(self.board["TWRP_INCLUDE_LOGCAT"], "true")
        readme = (DEVICE / "README.md").read_text()
        self.assertIn("experimental, compile-only recovery target", readme)
        self.assertIn("An empty fstab does not make TWRP read-only", readme)
        self.assertIn("not authorization to boot it", readme)
        self.assertIn("No ADB public key is bundled", readme)
        self.assertIn("does not assert a working renderer", readme)

    def test_source_write_sandbox_is_explicit_and_conflicting_override_is_rejected(self):
        self.assertEqual(self.board["BUILD_BROKEN_SRC_DIR_IS_WRITABLE"], "false")
        active = list(logical_lines(self.board_text))
        start = active.index("ifneq ($(BUILD_BROKEN_SRC_DIR_IS_WRITABLE),false)")
        self.assertEqual(active[start + 1],
                         "$(error Nezha TWRP requires the source-write sandbox; "
                         "BUILD_BROKEN_SRC_DIR_IS_WRITABLE must remain false)")
        self.assertEqual(active[start + 2], "endif")
        # This literal ifneq rejects true, an empty override, and any value
        # other than false. Do not replace it with a truthy-only filter.
        self.assertNotIn("$(filter true,$(BUILD_BROKEN_SRC_DIR_IS_WRITABLE))", active)


if __name__ == "__main__":
    unittest.main()
