# SPDX-License-Identifier: Apache-2.0

NEZHA_TWRP_DEVICE_PATH := device/xiaomi/nezha

# TARGET_NO_KERNEL suppresses the implicit recovery image rule. This explicit
# product switch builds the dedicated ramdisk image without a placeholder kernel.
PRODUCT_BUILD_RECOVERY_IMAGE := true
PRODUCT_BUILD_BOOT_IMAGE := false
PRODUCT_BUILD_INIT_BOOT_IMAGE := false
PRODUCT_BUILD_VENDOR_BOOT_IMAGE := false
PRODUCT_BUILD_SYSTEM_IMAGE := false
PRODUCT_BUILD_SYSTEM_EXT_IMAGE := false
PRODUCT_BUILD_PRODUCT_IMAGE := false
PRODUCT_BUILD_VENDOR_IMAGE := false
PRODUCT_BUILD_ODM_IMAGE := false
PRODUCT_BUILD_USERDATA_IMAGE := false
PRODUCT_BUILD_CACHE_IMAGE := false
PRODUCT_BUILD_VBMETA_IMAGE := false

PRODUCT_PACKAGES += recovery

# The minimal manifest retains these consumers without their parent defaults.
# Exclude only subsystems outside this no-network/no-crypto recovery product.
# Blueprint matches literal prefixes: the terminal slash prevents a similarly
# named sibling from being excluded. Unmatched paths stay enabled; dependencies
# on an excluded module remain errors and require a reviewed source restoration.
# Keep recovery, fs_mgr, SELinux, AVB, storage and device assertions in the graph.
PRODUCT_SOURCE_ROOT_DIRS += \
    -tools/loganalysis/ \
    -tools/tradefederation/contrib/ \
    -test/suite_harness/ \
    -hardware/google/aemu/ \
    -packages/modules/AdServices/ \
    -system/secretkeeper/ \
    -hardware/interfaces/neuralnetworks/utils/ \
    -hardware/interfaces/virtualization/capabilities_service/vts/

# The second graph exposed these specific CTS/VTS, automotive, connectivity
# test and context-hub consumers. Their missing parent defaults are unrelated
# to the first recovery product. CHRE includes a runtime subsystem, not just
# test generators. Preserve the rest of CTS and the security HAL interfaces.
PRODUCT_SOURCE_ROOT_DIRS += \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2019-1988/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-21085/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-40114/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2023-4863/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43091/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43097/ \
    -cts/hostsidetests/securitybulletin/securityPatch/CVE-2024-43767/ \
    -cts/tests/tests/car/ \
    -cts/tests/tests/car_permission_tests/ \
    -packages/modules/Connectivity/tests/common/ \
    -hardware/interfaces/automotive/remoteaccess/hal/default/ \
    -hardware/interfaces/security/see/hwcrypto/aidl/vts/functional/ \
    -system/chre/

# Do not inherit vendor/twrp/config/common.mk: it adds a rescue-disable
# property, a broad package bundle, and an unrelated recovery installer key.
PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING := true
PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \
    ro.secure=1 \
    ro.adb.secure=1

PRODUCT_COPY_FILES += \
    $(NEZHA_TWRP_DEVICE_PATH)/recovery/root/init.recovery.qcom.rc:recovery/root/init.recovery.qcom.rc
