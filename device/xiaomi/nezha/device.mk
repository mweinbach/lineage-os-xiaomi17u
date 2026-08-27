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

# The preserved vendor image owns its own init/import chain. Do not pretend
# that copying a file into vendor staging changes that prebuilt image.
PRODUCT_COPY_FILES += \
    $(NEZHA_DEVICE_PATH)/generated/fstab.qcom:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.qcom
