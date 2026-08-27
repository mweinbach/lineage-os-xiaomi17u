# SPDX-License-Identifier: Apache-2.0

$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, device/xiaomi/nezha/device.mk)
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

PRODUCT_NAME := lineage_nezha
PRODUCT_DEVICE := nezha
PRODUCT_BRAND := Xiaomi
PRODUCT_MANUFACTURER := Xiaomi
# Use the public product name, not the modified installation's global model ID.
PRODUCT_MODEL := Xiaomi 17 Ultra

# These are mandatory device policy. See the generated admission record for
# the two inherited Evolution defaults that must become optional assignments.
# Never enable duplicate-property compatibility mode to hide a conflict.
PRODUCT_PRODUCT_PROPERTIES += \
    ro.ota.allow_downgrade=false \
    ro.control_privapp_permissions=enforce

PRODUCT_ENFORCE_VINTF_MANIFEST := true
