# SPDX-License-Identifier: Apache-2.0

NEZHA_DEVICE_PATH := device/xiaomi/nezha
NEZHA_VENDOR_PATH ?= vendor/xiaomi/nezha
NEZHA_KERNEL_INPUTS ?= vendor/xiaomi/nezha-kernel

# Conservative compiler target for the observed arm64-v8a ABI. This is not a
# claim about the exact Oryon microarchitecture or its performance tuning.
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic

TARGET_BOARD_PLATFORM := canoe
TARGET_BOOTLOADER_BOARD_NAME := canoe
TARGET_NO_BOOTLOADER := true

include $(NEZHA_DEVICE_PATH)/generated/BoardConfigCandidate.mk
include kernel/xiaomi/nezha/stock-prebuilt.mk
include $(NEZHA_VENDOR_PATH)/BoardConfigVendor.mk

BOARD_USES_GENERIC_KERNEL_IMAGE := true
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
BOARD_RAMDISK_USE_LZ4 := true
BOARD_USES_METADATA_PARTITION := true
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_RECOVERY_FSTAB := $(NEZHA_DEVICE_PATH)/generated/fstab.qcom

# Engineering artifacts still use signature and compatibility checks. The
# generated admission record never authorizes flashing or key enrollment.
BOARD_AVB_ENABLE := true

# bka's release defaults permit source writes inside the Ninja sandbox. Require
# build actions to write into OUT_DIR instead; this strengthens that default.
BUILD_BROKEN_SRC_DIR_IS_WRITABLE := false

ifneq ($(TARGET_BUILD_VARIANT),user)
ifneq ($(TARGET_BUILD_VARIANT),userdebug)
$(error Nezha framework-checks product requires user or userdebug; eng weakens upstream AVB policy)
endif
endif
ifneq ($(filter true,$(SELINUX_IGNORE_NEVERALLOWS) $(BUILD_BROKEN_DUP_SYSPROP)),)
$(error Nezha candidate does not permit SELinux or duplicate-property check bypasses)
endif
ifneq ($(strip $(filter target-files-package otapackage updatepackage bacon superimage super_empty,$(MAKECMDGOALS))),)
$(error Nezha framework-checks profile does not admit complete target-files, OTA or super packaging; see generated admission.json)
endif

# The full hook also exports kernel variables to Lineage's Soong generators.
# Include it after the explicit prebuilt selector and all local board values.
include vendor/lineage/config/BoardConfigLineage.mk

# The inherited BCR product sets this global relaxation before BoardConfig is
# read. Require exact APK uses-library checks before dexpreopt locks the value.
# A conflicting command-line override must fail instead of weakening checks.
RELAX_USES_LIBRARY_CHECK := false
ifneq ($(RELAX_USES_LIBRARY_CHECK),false)
$(error Nezha requires strict APK uses-library validation)
endif
