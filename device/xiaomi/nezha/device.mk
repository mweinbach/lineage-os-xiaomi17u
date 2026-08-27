# SPDX-License-Identifier: Apache-2.0

NEZHA_DEVICE_PATH := device/xiaomi/nezha
NEZHA_VENDOR_PATH ?= vendor/xiaomi/nezha
NEZHA_KERNEL_INPUTS ?= vendor/xiaomi/nezha-kernel

$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch.mk)
$(call inherit-product, $(NEZHA_DEVICE_PATH)/generated/device-candidate.mk)
$(call inherit-product, $(NEZHA_VENDOR_PATH)/nezha-vendor.mk)

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
