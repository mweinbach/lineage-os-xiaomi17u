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

# Do not inherit vendor/twrp/config/common.mk: it adds a rescue-disable
# property, a broad package bundle, and an unrelated recovery installer key.
PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING := true
PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \
    ro.secure=1 \
    ro.adb.secure=1

PRODUCT_COPY_FILES += \
    $(NEZHA_TWRP_DEVICE_PATH)/recovery/root/init.recovery.qcom.rc:recovery/root/init.recovery.qcom.rc
