# SPDX-License-Identifier: Apache-2.0
# Experimental compile-only target. See README.md before interpreting artifacts.

NEZHA_TWRP_DEVICE_PATH := device/xiaomi/nezha

# ARM64 ABI and canoe/SM8850 identity are captured Nezha facts. The generic
# compiler variant is conservative, not a claim about Oryon CPU tuning.
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_BOARD_PLATFORM := canoe
TARGET_BOOTLOADER_BOARD_NAME := canoe
TARGET_NO_BOOTLOADER := true
TARGET_NO_KERNEL := true
TARGET_NO_RECOVERY := false

# Dedicated recovery ramdisk: the matching boot partition supplies the kernel,
# init_boot supplies generic first-stage init, and vendor_boot supplies DTBs
# and /lib/modules. No kernel, DTB, module or firmware is copied into this tree.
BOARD_BOOT_HEADER_VERSION := 4
BOARD_RECOVERY_MKBOOTIMG_ARGS := --header_version 4
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
BOARD_USES_RECOVERY_AS_BOOT := false
BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT := false
BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT := false
BOARD_RAMDISK_USE_LZ4 := true

# Both stock-package recovery slot extents are 100 MiB. This is not a live
# measurement of the phone or permission to write either recovery slot.
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 104857600
TARGET_RECOVERY_FSTAB := $(NEZHA_TWRP_DEVICE_PATH)/recovery.fstab

# Retain AVB generation and size checking. This public AOSP TEST key provides
# engineering-artifact integrity only; it is not trusted by the stock phone.
# The captured recovery chain uses rollback location 1/index 1. The phone's
# stored counters and any acceptable custom-key boot path remain unverified.
BOARD_AVB_ENABLE := true
BOARD_AVB_RECOVERY_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_RECOVERY_ALGORITHM := SHA256_RSA4096
BOARD_AVB_RECOVERY_ROLLBACK_INDEX := 1
BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION := 1

# This first compile has no storage integration. The normal stock userdata
# format is F2FS with wrappedkey_v0; do not substitute a legacy ext4 fstab.
# Disabling extra-fstab discovery also prevents importing vendor /data and
# /metadata entries behind the deliberately empty recovery fstab.
TW_SKIP_ADDITIONAL_FSTAB := true
TW_EXCLUDE_APEX := true
TW_EXCLUDE_MTP := true
TW_NO_USB_STORAGE := true
TW_NO_FLASH_CURRENT_TWRP := true
TW_INCLUDE_CRYPTO := false
TW_INCLUDE_CRYPTO_FBE := false
TW_INCLUDE_LIBRESETPROP := false
TW_INCLUDE_RESETPROP := false
TW_INCLUDE_REPACKTOOLS := false
TW_INCLUDE_FASTBOOTD := false
TW_INCLUDE_LPTOOLS := false
TW_INCLUDE_LPDUMP := false
TW_USE_DMCTL := false
TW_ENABLE_BLKDISCARD := false

# Generic theme selection is experimental. No touch device, panel brightness,
# pixel format, rotation, framebuffer stride, or timing is guessed here.
# The stock kernel has DRM but no framebuffer emulation; test the source DRM
# renderer before claiming a working display. Touch also needs separate
# vendor_dlkm modules and /odm firmware absent from this compile-only target.
TW_THEME := portrait_hdpi
TW_NO_HAPTICS := true
TW_NO_NETWORK := true
TW_EXCLUDE_DEFAULT_USB_INIT := true

# Preserve diagnostic logs in the ramdisk. Extraction still needs a separately
# validated, authenticated ADB connection; no host public key is bundled.
TARGET_USES_LOGD := true
TWRP_INCLUDE_LOGCAT := true

BOARD_SEPOLICY_DIRS += $(NEZHA_TWRP_DEVICE_PATH)/sepolicy

# Build actions must write under OUT_DIR, never into the checked source tree.
# A conflicting command-line assignment survives this assignment in make, so
# the guard below must reject it rather than silently weakening the sandbox.
BUILD_BROKEN_SRC_DIR_IS_WRITABLE := false

# Source plugins read these exported values. The kernel-build wrapper is not
# needed for a target that intentionally builds no kernel.
include vendor/twrp/config/BoardConfigSoong.mk

# Upstream registers OMAPI even with crypto off, but types it only in the
# crypto-enabled branch. Declare this target's disabled value through the
# supported helper so recovery's boolean selects retain their type checks.
$(call soong_config_set_bool, twrpGlobalVars, include_se_omapi, false)

ifneq ($(filter $(TARGET_BUILD_VARIANT),user userdebug),$(TARGET_BUILD_VARIANT))
$(error Nezha TWRP accepts only user or userdebug builds)
endif
ifeq ($(strip $(TARGET_BUILD_VARIANT)),)
$(error Nezha TWRP requires an explicit user or userdebug build variant)
endif
ifneq ($(filter true,$(ALLOW_MISSING_DEPENDENCIES) $(BUILD_BROKEN_MISSING_REQUIRED_MODULES) $(SELINUX_IGNORE_NEVERALLOWS) $(BUILD_BROKEN_DUP_RULES) $(BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES) $(BUILD_BROKEN_DUP_SYSPROP)),)
$(error Nezha TWRP does not admit dependency, SELinux, duplicate-rule, ELF or property-check bypasses)
endif
# The pinned build skips required-module validation in an ASAN target build.
# A sanitizer profile needs separate review, not a hidden dependency bypass.
ifneq ($(filter address,$(SANITIZE_TARGET)),)
$(error Nezha TWRP stage 0 does not admit an ASAN profile that skips required-module checks)
endif
ifneq ($(strip $(BUILD_BROKEN_PLUGIN_VALIDATION)),)
$(error Nezha TWRP does not admit unreviewed plugin-validation exceptions)
endif
ifneq ($(BUILD_BROKEN_SRC_DIR_IS_WRITABLE),false)
$(error Nezha TWRP requires the source-write sandbox; BUILD_BROKEN_SRC_DIR_IS_WRITABLE must remain false)
endif
ifneq ($(BOARD_AVB_ENABLE),true)
$(error Nezha TWRP requires AVB artifact generation)
endif
ifneq ($(BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE),true)
$(error Nezha TWRP must retain the stock dedicated kernel-free recovery layout)
endif
ifneq ($(filter true,$(BOARD_USES_RECOVERY_AS_BOOT) $(BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT) $(BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT)),)
$(error Nezha TWRP must not replace boot or vendor_boot)
endif
ifneq ($(strip $(filter recoveryimage-nodeps bootimage vendorbootimage initbootimage target-files-package otapackage updatepackage superimage super_empty,$(MAKECMDGOALS))),)
$(error Nezha TWRP stage 0 admits only dependency-checked recovery compilation; no other image or OTA packaging)
endif
