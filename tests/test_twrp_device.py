"""Offline invariants for the real TWRP target, not a device boot test."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "recovery/twrp/device/xiaomi/nezha"
MOTION_TEST_BLUEPRINT = "frameworks/base/packages/SystemUI/compose/scene/tests/Android.bp"
AUDIO_TEST_BLUEPRINT = "system/media/audio_utils/tests/Android.bp"
GRAPH14_TEST_BLUEPRINTS = (
    "test/robolectric-extensions/Android.bp",
    "test/robolectric-extensions/clearcut-junit-listener/Android.bp",
    "external/android_onboarding/java/com/android/onboarding/contracts/testing/Android.bp",
    "external/android_onboarding/java/com/android/onboarding/testing/Android.bp",
    "frameworks/base/packages/SettingsLib/tests/robotests/Android.bp",
    "frameworks/base/packages/SettingsLib/tests/robotests/fragment/Android.bp",
)
SOURCE_FILE_EXCLUSIONS = {MOTION_TEST_BLUEPRINT, AUDIO_TEST_BLUEPRINT, *GRAPH14_TEST_BLUEPRINTS}
SOURCE_EXCLUSIONS = [
    "-hardware/google/aemu/",
    "-packages/modules/AdServices/",
    "-hardware/interfaces/neuralnetworks/utils/",
    "-hardware/interfaces/virtualization/capabilities_service/vts/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2019-1988/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-21085/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-40114/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-4863/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43091/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43097/",
    "-cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43767/",
    "-cts/tests/tests/car/",
    "-cts/tests/tests/car_permission_tests/",
    "-hardware/interfaces/automotive/remoteaccess/hal/default/",
    "-hardware/interfaces/security/see/hwcrypto/aidl/vts/functional/",
    "-system/chre/",
    "-hardware/interfaces/automotive/vehicle/vts/",
    "-hardware/interfaces/automotive/audiocontrol/aidl/default/",
    "-hardware/interfaces/automotive/vehicle/aidl/impl/3/",
    "-hardware/interfaces/automotive/vehicle/aidl/impl/current/",
    "-hardware/interfaces/security/secretkeeper/aidl/vts/",
    "-hardware/interfaces/neuralnetworks/1.0/utils/",
    "-hardware/interfaces/neuralnetworks/1.1/utils/",
    "-hardware/interfaces/neuralnetworks/1.2/utils/",
    "-hardware/interfaces/neuralnetworks/1.3/utils/",
    "-hardware/interfaces/neuralnetworks/aidl/utils/",
    "-hardware/interfaces/neuralnetworks/aidl/vts/functional/",
    "-" + MOTION_TEST_BLUEPRINT,
    "-hardware/interfaces/automotive/vehicle/aidl/aidl_test/",
    "-hardware/interfaces/broadcastradio/aidl/default/test/",
    "-platform_testing/",
    "-frameworks/opt/net/wifi/",
    "-development/build/",
    "-" + AUDIO_TEST_BLUEPRINT,
    "-tools/security/",
] + ["-" + path for path in GRAPH14_TEST_BLUEPRINTS]
SOURCE_REINCLUSIONS = [
    "platform_testing/libraries/tradefed-error-prone/",
    "frameworks/opt/net/wifi/libwifi_system_iface/",
    "platform_testing/libraries/rdroidtest/",
    "platform_testing/libraries/compatibility-common-util/",
    "platform_testing/libraries/annotations/",
    "platform_testing/libraries/flag-helpers/junit/",
    "platform_testing/libraries/flag-helpers/libflagtest/",
    "tools/security/remote_provisioning/hwtrust/",
]


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


def source_path_allowed(path, source_roots):
    """Model Blueprint dcb14f2e context.go:202-223, not its dependency checker."""
    for entry in sorted(source_roots, key=len, reverse=True):
        excluded = entry.startswith("-")
        prefix = entry[1:] if excluded else entry
        if path.startswith(prefix):
            return not excluded
    return True


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
        # Pinned board_config.mk defaults the A/B updater to true. Preserve
        # Nezha's actual slot/update model; absence is not an updater disable.
        self.assertNotIn("AB_OTA_UPDATER", self.board | self.device | self.product)
        for setting in ("PRODUCT_USE_DYNAMIC_PARTITIONS", "PRODUCT_VIRTUAL_AB_OTA",
                        "TW_OVERRIDE_SYSTEM_PROPS", "TW_PREPARE_DATA_MEDIA_EARLY"):
            self.assertNotEqual((self.board | self.device).get(setting), "true", setting)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")

    def test_disabled_omapi_is_exported_as_boolean_after_vendor_configuration(self):
        lines = list(logical_lines(self.board_text))
        vendor_include = "include vendor/twrp/config/BoardConfigSoong.mk"
        typed_disable = "$(call soong_config_set_bool, twrpGlobalVars, include_se_omapi, false)"
        self.assertEqual(lines.count(vendor_include), 1)
        self.assertEqual(lines.count(typed_disable), 1)
        self.assertLess(lines.index(vendor_include), lines.index(typed_disable))
        # The real make helper supplies VendorVarTypes=bool; a plain string
        # assignment, even "false", cannot satisfy the upstream boolean select.
        omapi_lines = [line for line in lines if "include_se_omapi" in line]
        self.assertEqual(omapi_lines, [typed_disable])
        for setting in ("TW_INCLUDE_CRYPTO", "TW_INCLUDE_CRYPTO_FBE", "TW_INCLUDE_LIBRESETPROP"):
            self.assertEqual(self.board[setting], "false", setting)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")

    def test_native_recovery_profile_is_typed_and_local_to_this_product(self):
        lines = list(logical_lines(self.board_text))
        vendor_include = "include vendor/twrp/config/BoardConfigSoong.mk"
        profile_enable = "$(call soong_config_set_bool, nezha_twrp, native_recovery_only, true)"
        self.assertEqual(lines.count(profile_enable), 1)
        self.assertLess(lines.index(vendor_include), lines.index(profile_enable))
        self.assertEqual([line for line in lines if "native_recovery_only" in line], [profile_enable])
        self.assertNotIn("native_recovery_only", self.product_text + self.device_text)
        self.assertNotIn("native_recovery_only", (ROOT / "device/xiaomi/nezha/BoardConfig.mk").read_text())
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")

    def test_native_recovery_profile_keeps_production_and_validation_sources(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for source in ("frameworks/base/packages/SystemUI/Android.bp",
                       "frameworks/base/packages/SystemUI/compose/scene/tests/utils/Android.bp",
                       "packages/modules/Bluetooth/service/Android.bp",
                       "system/sepolicy/Android.bp", "system/sepolicy/tests/Android.bp",
                       "system/sepolicy/contexts/Android.bp", "external/avb/Android.bp",
                       "tools/apksig/Android.bp", "system/libvintf/Android.bp",
                       "build/soong/Android.bp", "bootable/recovery/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.board["BOARD_AVB_ENABLE"], "true")
        self.assertEqual(self.device["PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING"], "true")
        for setting in ("ALLOW_MISSING_DEPENDENCIES", "BUILD_BROKEN_MISSING_REQUIRED_MODULES",
                        "SELINUX_IGNORE_NEVERALLOWS", "BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES"):
            self.assertNotEqual(self.board.get(setting), "true", setting)
            self.assertIn("$(" + setting + ")", self.board_text)
        readme = (DEVICE / "README.md").read_text()
        self.assertIn("native_recovery_only", readme)
        self.assertIn("default: unset", readme)
        self.assertIn("not a full Android test profile", readme)

    def test_theme_output_is_not_faked_in_device_configuration(self):
        # The upstream theme hook reads the runner's OUT environment variable,
        # normally populated by lunch from absolute PRODUCT_OUT. Device config
        # must not compensate with /recovery or a path to a particular checkout.
        active = "\n".join(logical_lines(self.board_text + self.device_text + self.product_text))
        for name in ("OUT", "OUT_DIR", "ANDROID_PRODUCT_OUT", "PRODUCT_OUT"):
            self.assertNotIn(name, self.board | self.device | self.product)
        self.assertNotIn("/work/", active)
        self.assertNotIn("/Users/", active)
        self.assertNotIn("mkdir", active)

    def test_source_graph_exclusions_match_the_reviewed_bounded_scopes(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        # Blueprint sorts by prefix length; independent provider pairs may be
        # grouped together in the product without changing the selected graph.
        self.assertCountEqual(scopes, SOURCE_EXCLUSIONS + SOURCE_REINCLUSIONS)
        self.assertEqual(len(scopes), len(set(scopes)))
        for scope in scopes:
            if not scope.endswith("/"):
                self.assertIn(scope, {"-" + path for path in SOURCE_FILE_EXCLUSIONS})
            path = scope[1:] if scope.startswith("-") else scope
            self.assertNotIn("..", Path(path).parts)
            self.assertFalse(Path(path).is_absolute())
        self.assertNotIn("-", scopes)

    def test_source_graph_negative_prefixes_preserve_parents_and_siblings(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for scope in (rule for rule in scopes if rule.startswith("-")):
            prefix = scope[1:]
            with self.subTest(scope=scope):
                if not prefix.endswith("/"):
                    self.assertIn(prefix, SOURCE_FILE_EXCLUSIONS)
                    self.assertFalse(source_path_allowed(prefix, scopes))
                    self.assertTrue(source_path_allowed(str(Path(prefix).parent / "utils/Android.bp"), scopes))
                    self.assertTrue(source_path_allowed(str(Path(prefix).parent / "other.bp"), scopes))
                    continue
                self.assertFalse(source_path_allowed(prefix + "Android.bp", scopes))
                self.assertFalse(source_path_allowed(prefix + "nested/Android.bp", scopes))
                self.assertTrue(source_path_allowed(prefix.rstrip("/") + "_sibling/Android.bp", scopes))
                self.assertTrue(source_path_allowed(str(Path(prefix).parent / "Android.bp"), scopes))

    def test_source_graph_keeps_recovery_security_and_storage_checks(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for source in (
                "Android.bp", "bootable/recovery/Android.bp", "bootable/recovery/gui/Android.bp",
                "system/core/fs_mgr/Android.bp", "system/sepolicy/Android.bp",
                "system/sepolicy/tests/Android.bp", "external/avb/Android.bp",
                "external/f2fs-tools/Android.bp", "system/vold/Android.bp",
                "hardware/interfaces/boot/Android.bp", "hardware/interfaces/security/keymint/Android.bp",
                "hardware/interfaces/security/see/hwcrypto/aidl/Android.bp",
                "hardware/interfaces/security/secretkeeper/aidl/Android.bp",
                "hardware/interfaces/security/secureclock/aidl/vts/functional/Android.bp",
                "system/libvintf/Android.bp", "build/soong/Android.bp",
                "external/skia/Android.bp", "frameworks/base/libs/hwui/Android.bp",
                "frameworks/native/libs/renderengine/Android.bp",
                "packages/modules/Connectivity/bpf/headers/Android.bp", "system/bpf/Android.bp",
                "packages/modules/Connectivity/tests/common/Android.bp",
                "device/xiaomi/nezha/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.board["BOARD_AVB_ENABLE"], "true")
        self.assertEqual(self.device["PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING"], "true")
        self.assertNotEqual(self.board.get("ALLOW_MISSING_DEPENDENCIES"), "true")
        self.assertNotEqual(self.board.get("SELINUX_IGNORE_NEVERALLOWS"), "true")
        self.assertIn("$(ALLOW_MISSING_DEPENDENCIES)", self.board_text)
        self.assertIn("$(SELINUX_IGNORE_NEVERALLOWS)", self.board_text)

    def test_third_graph_keeps_shared_connectivity_defaults_and_real_provider(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertNotIn("-packages/modules/Connectivity/tests/common/", scopes)
        for source in ("packages/modules/Connectivity/tests/common/Android.bp",
                       "packages/modules/Connectivity/thread/tests/integration/Android.bp",
                       "packages/modules/Connectivity/bpf/tests/mts/Android.bp",
                       "packages/modules/NetworkStack/Android.bp",
                       "packages/modules/NetworkStack/tests/unit/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        # Restoring source graph providers does not enable runtime networking.
        self.assertEqual(self.board["TW_NO_NETWORK"], "true")
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        readme = (DEVICE / "README.md").read_text()
        self.assertIn("Graph 3", readme)
        self.assertIn("f9da1fc7154ea007aa835f88e8070c6ac46d54e9", readme)
        self.assertIn("no substitute defaults", readme)

    def test_fourth_graph_scope_keeps_production_security_and_automotive_interfaces(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for prefix in ("-hardware/interfaces/automotive/", "-hardware/interfaces/automotive/vehicle/",
                       "-hardware/interfaces/automotive/vehicle/aidl/",
                       "-hardware/interfaces/automotive/vehicle/aidl/impl/",
                       "-hardware/interfaces/security/secretkeeper/aidl/"):
            self.assertNotIn(prefix, scopes)
        for source in ("hardware/interfaces/automotive/vehicle/aidl/Android.bp",
                       "hardware/interfaces/automotive/vehicle/aidl/impl/2/Android.bp",
                       "hardware/interfaces/automotive/audiocontrol/aidl/Android.bp",
                       "hardware/interfaces/security/secretkeeper/aidl/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)

    def test_fourth_graph_keeps_nnapi_interfaces_outside_unselected_utilities(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertNotIn("-hardware/interfaces/neuralnetworks/", scopes)
        for version in ("1.0", "1.1", "1.2", "1.3", "aidl"):
            interface = f"hardware/interfaces/neuralnetworks/{version}/"
            self.assertTrue(source_path_allowed(interface + "Android.bp", scopes))
            self.assertFalse(source_path_allowed(interface + "utils/Android.bp", scopes))
        self.assertTrue(source_path_allowed("hardware/interfaces/neuralnetworks/aidl/aidl_api/Android.bp", scopes))
        self.assertFalse(source_path_allowed("hardware/interfaces/neuralnetworks/aidl/vts/functional/Android.bp", scopes))

    def test_original_tradefed_provider_is_reincluded_without_platform_test_aggregate(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        provider = "platform_testing/libraries/tradefed-error-prone/"
        self.assertTrue(source_path_allowed(provider + "Android.bp", scopes))
        self.assertTrue(source_path_allowed(provider + "nested/Android.bp", scopes))
        for source in ("platform_testing/Android.bp", "platform_testing/build/Android.bp",
                       "platform_testing/tests/Android.bp", "platform_testing/libraries/other/Android.bp",
                       "platform_testing/libraries/tradefed-error-prone_sibling/Android.bp"):
            self.assertFalse(source_path_allowed(source, scopes), source)
        for source in ("tools/tradefederation/core/Android.bp", "tools/tradefederation/contrib/Android.bp",
                       "tools/loganalysis/Android.bp", "test/suite_harness/common/host-side/tradefed/Android.bp",
                       "frameworks/libs/native_bridge_support/Android.bp",
                       "frameworks/libs/native_bridge_support/android_api/libc/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)

    def test_sixth_graph_selects_real_wifi_interface_and_test_support(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        provider = "frameworks/opt/net/wifi/libwifi_system_iface/"
        self.assertTrue(source_path_allowed(provider + "Android.bp", scopes))
        self.assertTrue(source_path_allowed(provider + "testlib/Android.bp", scopes))
        for source in ("frameworks/opt/net/wifi/Android.bp",
                       "frameworks/opt/net/wifi/libs/WifiTrackerLib/Android.bp",
                       "frameworks/opt/net/wifi/libwifi_hal/Android.bp",
                       "frameworks/opt/net/wifi/libwifi_system/Android.bp",
                       "frameworks/opt/net/wifi/libwifi_system_iface_sibling/Android.bp"):
            self.assertFalse(source_path_allowed(source, scopes), source)
        for source in ("system/connectivity/wificond/Android.bp",
                       "system/sepolicy/tests/Android.bp",
                       "frameworks/opt/net/wifi_sibling/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.board["TW_NO_NETWORK"], "true")
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")

    def test_sixth_graph_restores_consumed_secretkeeper_without_enabling_crypto(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertNotIn("-system/secretkeeper/", scopes)
        for source in ("system/secretkeeper/Android.bp",
                       "system/secretkeeper/client/Android.bp",
                       "system/secretkeeper/comm/Android.bp",
                       "system/secretkeeper/core/Android.bp",
                       "system/secretkeeper/dice_policy/Android.bp",
                       "system/secretkeeper/hal/Android.bp",
                       "packages/modules/Virtualization/build/Android.bp",
                       "packages/modules/Virtualization/guest/microdroid_manager/Android.bp",
                       "packages/modules/Virtualization/android/virtmgr/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertFalse(source_path_allowed(
            "hardware/interfaces/security/secretkeeper/aidl/vts/Android.bp", scopes))
        for setting in ("TW_INCLUDE_CRYPTO", "TW_INCLUDE_CRYPTO_FBE", "TW_INCLUDE_LIBRESETPROP"):
            self.assertEqual(self.board[setting], "false", setting)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        readme = (DEVICE / "README.md").read_text()
        for fact in ("Graph 6", "microdroid_manager", "libsecretkeeper_client",
                     "libsecretkeeper_comm_nostd"):
            self.assertIn(fact, readme)

    def test_original_rust_test_provider_keeps_secretkeeper_test_definitions(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        provider = "platform_testing/libraries/rdroidtest/"
        self.assertTrue(source_path_allowed(provider + "Android.bp", scopes))
        self.assertTrue(source_path_allowed(provider + "tests/Android.bp", scopes))
        for source in ("platform_testing/Android.bp",
                       "platform_testing/libraries/rdroidtest_sibling/Android.bp",
                       "platform_testing/libraries/other/Android.bp"):
            self.assertFalse(source_path_allowed(source, scopes), source)
        for source in ("system/secretkeeper/client/Android.bp",
                       "system/secretkeeper/comm/Android.bp",
                       "system/secretkeeper/dice_policy/tests/Android.bp",
                       "system/logging/rust/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        readme = (DEVICE / "README.md").read_text()
        self.assertIn("platform_testing/libraries/rdroidtest/", readme)
        self.assertIn("rdroidtest.defaults", readme)

    def test_graph11_restores_compatibility_and_annotations_without_test_aggregate(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for provider in ("platform_testing/libraries/compatibility-common-util/",
                         "platform_testing/libraries/annotations/"):
            self.assertTrue(source_path_allowed(provider + "Android.bp", scopes))
            self.assertTrue(source_path_allowed(provider + "tests/Android.bp", scopes))
            self.assertFalse(source_path_allowed(provider.rstrip("/") + "_sibling/Android.bp", scopes))
        for source in ("platform_testing/Android.bp", "platform_testing/libraries/Android.bp",
                       "platform_testing/libraries/other/Android.bp", "platform_testing/tests/Android.bp"):
            self.assertFalse(source_path_allowed(source, scopes), source)
        for source in ("test/suite_harness/common/util/Android.bp",
                       "frameworks/base/tools/locked_region_code_injection/Android.bp",
                       "cts/Android.bp", "external/junit/Android.bp", "external/guava/Android.bp",
                       "external/error_prone/Android.bp", "prebuilts/misc/common/json/Android.bp",
                       "prebuilts/misc/common/kxml2/Android.bp", "tools/tradefederation/core/Android.bp",
                       "build/soong/licenses/Android.bp", "build/make/teams/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        readme = (DEVICE / "README.md").read_text()
        for fact in ("Graph 11", "compatibility-common-util-lib", "platform-test-annotations",
                     "7b48625b052b94b1ef24573ef5e8ffa5e2ea9783"):
            self.assertIn(fact, readme)

    def test_sdk_distribution_scope_preserves_actual_tools_and_validators(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertFalse(source_path_allowed("development/build/Android.bp", scopes))
        self.assertNotIn("-development/", scopes)
        for source in ("development/Android.bp", "development/build_sibling/Android.bp",
                       "development/tools/Android.bp", "packages/modules/adb/Android.bp",
                       "system/core/fastboot/Android.bp", "system/tools/mkbootimg/Android.bp",
                       "tools/apksig/Android.bp", "external/avb/Android.bp",
                       "system/sepolicy/contexts/Android.bp", "system/sepolicy/tests/Android.bp",
                       "system/libvintf/Android.bp", "build/make/tools/apicheck/Android.bp",
                       "prebuilts/build-tools/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        self.assertEqual(self.board["BOARD_AVB_ENABLE"], "true")
        readme = (DEVICE / "README.md").read_text()
        self.assertIn("Graph 9", readme)
        self.assertIn("development/build/", readme)
        self.assertIn("SDK distribution", readme)

    def test_projected_flag_helpers_keep_tests_and_existing_dependency_providers(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        parent = "platform_testing/libraries/flag-helpers/"
        self.assertNotIn(parent, scopes)
        for leaf in ("junit/", "libflagtest/"):
            self.assertTrue(source_path_allowed(parent + leaf + "Android.bp", scopes))
            self.assertFalse(source_path_allowed(parent + leaf.rstrip("/") + "_sibling/Android.bp", scopes))
        self.assertTrue(source_path_allowed(parent + "junit/test/Android.bp", scopes))
        for source in ("platform_testing/Android.bp", parent + "Android.bp",
                       "platform_testing/libraries/runner/Android.bp",
                       "platform_testing/libraries/device-collectors/Android.bp",
                       "platform_testing/libraries/collectors-helper/Android.bp",
                       "platform_testing/libraries/junit-rules/Android.bp"):
            self.assertFalse(source_path_allowed(source, scopes), source)
        for source in ("external/auto/value/Android.bp", "external/jsr305/Android.bp",
                       "external/guava/Android.bp", "external/junit/Android.bp",
                       "external/mockito/Android.bp", "external/objenesis/Android.bp",
                       "platform_testing/libraries/annotations/Android.bp",
                       "prebuilts/misc/common/androidx-test/Android.bp",
                       "packages/modules/ConfigInfrastructure/framework/Android.bp",
                       "packages/modules/common/sdk/Android.bp",
                       "prebuilts/module_sdk/ConfigInfrastructure/current/Android.bp",
                       "build/make/tools/aconfig/aconfig_device_paths/Android.bp",
                       "build/make/tools/aconfig/aconfig_protos/Android.bp",
                       "build/make/tools/aconfig/aconfig_storage_read_api/Android.bp",
                       "system/server_configurable_flags/libflags/Android.bp",
                       "external/googletest/googletest/Android.bp", "system/libbase/Android.bp",
                       "system/logging/liblog/Android.bp", "tools/tradefederation/core/Android.bp",
                       "build/make/teams/Android.bp", "build/soong/licenses/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        readme = (DEVICE / "README.md").read_text()
        for fact in ("source projection after Graph 13", "flag-junit-host", "libflagtest",
                     "framework-configinfrastructure.stubs.module_lib"):
            self.assertIn(fact, readme)

    def test_motion_exclusion_preserves_consumed_test_helper_and_graphics(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertFalse(source_path_allowed(MOTION_TEST_BLUEPRINT, scopes))
        self.assertNotIn("-" + str(Path(MOTION_TEST_BLUEPRINT).parent) + "/", scopes)
        for source in (
                "frameworks/base/packages/SystemUI/compose/scene/Android.bp",
                "frameworks/base/packages/SystemUI/compose/scene/tests/utils/Android.bp",
                "frameworks/base/packages/SystemUI/Android.bp",
                "frameworks/base/packages/SettingsLib/Spa/screenshot/robotests/Android.bp",
                "frameworks/base/tests/InputScreenshotTest/robotests/Android.bp",
                "external/skia/Android.bp", "frameworks/base/libs/hwui/Android.bp",
                "frameworks/native/libs/renderengine/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)

    def test_audio_test_file_scope_preserves_production_fuzzers_and_other_tests(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertFalse(source_path_allowed(AUDIO_TEST_BLUEPRINT, scopes))
        for prefix in ("-system/media/", "-system/media/audio_utils/",
                       "-system/media/audio_utils/tests/"):
            self.assertNotIn(prefix, scopes)
        for source in ("system/media/Android.bp", "system/media/audio/Android.bp",
                       "system/media/alsa_utils/Android.bp", "system/media/audio_effects/Android.bp",
                       "system/media/audio_route/Android.bp", "system/media/audio_utils/Android.bp",
                       "system/media/audio_utils/benchmarks/Android.bp",
                       "system/media/audio_utils/fuzz/Android.bp",
                       "system/media/audio_utils/fuzz/format_fuzzer/Android.bp",
                       "system/media/audio_utils/tests/child/Android.bp",
                       "system/media/camera/tests/Android.bp", "system/media/tests/Android.bp",
                       "hardware/interfaces/vibrator/aidl/default/Android.bp",
                       "external/tinyalsa/Android.bp", "external/tinyalsa_new/Android.bp",
                       "external/speex/Android.bp", "system/sepolicy/contexts/Android.bp",
                       "system/sepolicy/tests/Android.bp", "external/avb/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        readme = (DEVICE / "README.md").read_text()
        self.assertIn(AUDIO_TEST_BLUEPRINT, readme)
        self.assertIn("f01e84b958fb6a887dc0e74e4b5ebd159f03860a", readme)

    def test_graph14_file_cuts_preserve_production_ipc_sdk_and_other_source_files(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for source in GRAPH14_TEST_BLUEPRINTS:
            self.assertFalse(source_path_allowed(source, scopes), source)
            self.assertNotIn("-" + str(Path(source).parent) + "/", scopes)
        for source in ("test/Android.bp", "test/robolectric-extensions/plugins/Android.bp",
                       "external/android_onboarding/Android.bp",
                       "external/android_onboarding/java/com/android/onboarding/contracts/Android.bp",
                       "external/android_onboarding/java/com/android/onboarding/testing/child/Android.bp",
                       "frameworks/base/Android.bp", "frameworks/base/packages/SettingsLib/Android.bp",
                       "frameworks/base/packages/SettingsLib/Ipc/Android.bp",
                       "frameworks/base/packages/SettingsLib/tests/Android.bp",
                       "frameworks/base/packages/SettingsLib/tests/robotests/fragment/child/Android.bp",
                       "prebuilts/sdk/current/aaos-libs/Android.bp",
                       "system/sepolicy/contexts/Android.bp", "system/sepolicy/tests/Android.bp",
                       "external/avb/Android.bp", "system/libvintf/Android.bp",
                       "bootable/recovery/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        readme = (DEVICE / "README.md").read_text()
        self.assertIn("Graph 14 reported seven missing dependencies", readme)
        self.assertIn("follow-up projection", readme)
        self.assertIn("SettingsLibIpc-testutils", readme)
        self.assertIn("car-ui-lib-testing-support", readme)

    def test_projected_hwtrust_provider_keeps_keymint_and_security_validators(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        provider = "tools/security/remote_provisioning/hwtrust/"
        for source in (provider + "Android.bp", provider + "cxxbridge/Android.bp",
                       provider + "tests/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        for source in ("tools/security/Android.bp", "tools/security/remote_provisioning/Android.bp",
                       "tools/security/remote_provisioning/hwtrust_sibling/Android.bp",
                       "tools/security/other/Android.bp"):
            self.assertFalse(source_path_allowed(source, scopes), source)
        for source in ("tools/security_sibling/Android.bp",
                       "hardware/interfaces/security/keymint/Android.bp",
                       "hardware/interfaces/security/keymint/support/Android.bp",
                       "hardware/interfaces/security/keymint/aidl/vts/functional/Android.bp",
                       "system/security/provisioner/Android.bp", "system/sepolicy/contexts/Android.bp",
                       "system/sepolicy/tests/Android.bp", "external/avb/Android.bp",
                       "system/libvintf/Android.bp", "build/soong/Android.bp",
                       "external/rust/cxx/gen/cmd/Android.bp", "external/rust/cxx/Android.bp",
                       "external/rust/crates/openssl/Android.bp", "external/boringssl/Android.bp",
                       "system/libbase/Android.bp", "build/soong/licenses/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)
        self.assertNotIn("-hardware/interfaces/security/", scopes)
        self.assertNotIn("-system/security/", scopes)
        self.assertEqual(self.device["PRODUCT_PACKAGES"], "recovery")
        self.assertEqual(self.board["BOARD_AVB_ENABLE"], "true")
        self.assertEqual(self.board["TW_INCLUDE_CRYPTO"], "false")
        readme = (DEVICE / "README.md").read_text()
        for fact in ("8d8a8332751c3b20a87f38dd7cb4039eeea489b5", "libkeymint_remote_prov_support",
                     "libhwtrust_cxx", "source-projection finding", "service-fuzzer registry"):
            self.assertIn(fact, readme)

    def test_vehicle_compatibility_test_scope_keeps_production_aidl(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertFalse(source_path_allowed(
            "hardware/interfaces/automotive/vehicle/aidl/aidl_test/Android.bp", scopes))
        for source in ("hardware/interfaces/automotive/vehicle/aidl/Android.bp",
                       "hardware/interfaces/automotive/vehicle/aidl/aidl_api/Android.bp",
                       "hardware/interfaces/automotive/vehicle/aidl/aidl_test_sibling/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)

    def test_broadcast_radio_test_scope_keeps_service_and_interface(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertFalse(source_path_allowed(
            "hardware/interfaces/broadcastradio/aidl/default/test/Android.bp", scopes))
        for source in ("hardware/interfaces/broadcastradio/aidl/Android.bp",
                       "hardware/interfaces/broadcastradio/aidl/default/Android.bp",
                       "hardware/interfaces/broadcastradio/aidl/default/test_sibling/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)

    def test_second_graph_scope_does_not_hide_entire_cts_or_hardware_interfaces(self):
        scopes = self.device["PRODUCT_SOURCE_ROOT_DIRS"].split()
        for prefix in ("-cts/", "-cts/hostsidetests/securitybulletin/",
                       "-cts/hostsidetests/securitybulletin/securityPatch/",
                       "-hardware/interfaces/", "-hardware/interfaces/security/",
                       "-hardware/interfaces/security/see/hwcrypto/aidl/",
                       "-packages/modules/Connectivity/", "-packages/modules/Connectivity/bpf/"):
            self.assertNotIn(prefix, scopes)
        for source in ("cts/Android.bp", "cts/hostsidetests/securitybulletin/Android.bp",
                       "cts/hostsidetests/securitybulletin/securityPatch/includes/Android.bp",
                       "cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-21084/Android.bp",
                       "cts/tests/tests/security/Android.bp", "cts/tests/tests/carrierapi/Android.bp",
                       "packages/modules/Connectivity/tests/unit/Android.bp",
                       "hardware/interfaces/automotive/remoteaccess/aidl/Android.bp"):
            self.assertTrue(source_path_allowed(source, scopes), source)

    def test_missing_final_product_packages_are_errors_without_an_allowlist(self):
        active = list(logical_lines(self.product_text))
        calls = [line for line in active if "enforce-product-packages-exist" in line]
        self.assertEqual(calls, ["$(call enforce-product-packages-exist)"])
        self.assertGreater(active.index(calls[0]), active.index(
            "$(call inherit-product, device/xiaomi/nezha/device.mk)"))
        for text in (self.board_text, self.device_text, self.product_text):
            self.assertNotIn("PRODUCT_ENFORCE_PACKAGES_EXIST_ALLOW_LIST", "\n".join(logical_lines(text)))

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
        for flag in ("ALLOW_MISSING_DEPENDENCIES", "BUILD_BROKEN_MISSING_REQUIRED_MODULES",
                     "SELINUX_IGNORE_NEVERALLOWS",
                     "BUILD_BROKEN_DUP_RULES", "BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES",
                     "BUILD_BROKEN_DUP_SYSPROP", "BUILD_BROKEN_PLUGIN_VALIDATION"):
            self.assertIn(f"$({flag})", self.board_text)
            self.assertNotEqual(self.board.get(flag), "true", flag)
        self.assertIn("ifneq ($(BOARD_AVB_ENABLE),true)", self.board_text)
        self.assertIn("ifneq ($(BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE),true)", self.board_text)
        self.assertIn("recoveryimage-nodeps bootimage vendorbootimage initbootimage", self.board_text)
        self.assertIn("ifneq ($(filter address,$(SANITIZE_TARGET)),)", self.board_text)
        self.assertNotIn("SANITIZE_TARGET", self.board | self.device | self.product)

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
