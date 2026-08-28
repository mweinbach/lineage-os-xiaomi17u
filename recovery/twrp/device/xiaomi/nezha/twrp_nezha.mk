# SPDX-License-Identifier: Apache-2.0
# Install this directory at device/xiaomi/nezha in the isolated TWRP source.

$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)
$(call inherit-product, device/xiaomi/nezha/device.mk)

PRODUCT_NAME := twrp_nezha
PRODUCT_DEVICE := nezha
PRODUCT_BRAND := Xiaomi
PRODUCT_MANUFACTURER := Xiaomi
PRODUCT_MODEL := Xiaomi 17 Ultra
PRODUCT_SHIPPING_API_LEVEL := 36

# The compiled recovery identifies itself, never an OEM-signed HyperOS build.
# Keep the source tree's actual Android version and security patch level.
