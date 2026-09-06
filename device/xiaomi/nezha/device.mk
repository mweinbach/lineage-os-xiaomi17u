# SPDX-License-Identifier: Apache-2.0

NEZHA_DEVICE_PATH := device/xiaomi/nezha
NEZHA_VENDOR_PATH ?= vendor/xiaomi/nezha
NEZHA_KERNEL_INPUTS ?= vendor/xiaomi/nezha-kernel

# Exact Nezha factory geometry; device overlays take priority over common ones.
DEVICE_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/overlay

# Exact-panel normal-brightness candidate, with explicit private-input gating.
include $(NEZHA_DEVICE_PATH)/display-panel.mk

# Optional framework controls; preserve factory vendor haptic calibration.
include $(NEZHA_DEVICE_PATH)/haptics.mk

# Manual Dolby controls only; do not replace the factory vendor backend.
include $(NEZHA_DEVICE_PATH)/dolby.mk

# The opt-in successor uses the original signed factory Camera and a narrow
# same-partition privilege policy. A selected but missing packet must fail.
ifeq ($(NEZHA_XIAOMI_CAMERA),true)
$(call inherit-product, vendor/xiaomi/nezha-camera/camera-product.mk)
endif

$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch.mk)
$(call inherit-product, $(NEZHA_DEVICE_PATH)/generated/device-candidate.mk)
$(call inherit-product, $(NEZHA_VENDOR_PATH)/nezha-vendor.mk)

# Treat Treble labeling violations as errors when its dedicated check runs.
# At platform policy 202504, merely setting this does not schedule that check.
PRODUCT_ENFORCE_SELINUX_TREBLE_LABELING := true

PRODUCT_SOONG_NAMESPACES += \
    $(NEZHA_DEVICE_PATH) \
    $(NEZHA_VENDOR_PATH)

# The retained vendor loader reads this selector from vendor_dlkm before
# loading system modules. BoardConfig separately installs the same bytes as
# system_dlkm's own modules.blocklist; that does not create this vendor path.
# Read the verified generated bundle at product scope so the source path is
# available before BoardConfig runs. Never add these names to vendor's general
# blocklist, which would suppress the intended vendor ZRAM/allocator pair.
include $(NEZHA_KERNEL_INPUTS)/kernel-inputs.mk
ifeq ($(strip $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)),)
$(error Nezha requires the captured system DLKM selection blocklist)
endif
PRODUCT_COPY_FILES += \
    $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE):$(TARGET_COPY_OUT_VENDOR_DLKM)/lib/modules/system_dlkm.modules.blocklist

# The preserved vendor image owns its own init/import chain. Do not pretend
# that copying a file into vendor staging changes that prebuilt image.
PRODUCT_COPY_FILES += \
    $(NEZHA_DEVICE_PATH)/generated/fstab.qcom:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.qcom
