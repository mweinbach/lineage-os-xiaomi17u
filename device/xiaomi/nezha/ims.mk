# SPDX-License-Identifier: Apache-2.0
# Exact-stock Android IMS provider (org.codeaurora.ims), selected explicitly.
# Requires the private verified-input bundle at vendor/xiaomi/nezha-ims and
# restores the factory system_ext vendor_qtelephony application domain with
# its stock selector. Carrier registration and calls remain a device gate;
# this fragment only selects the reviewed modules and policy.
ifneq ($(filter-out 0 1,$(words $(NEZHA_IMS))),)
$(error NEZHA_IMS must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_IMS))),)
$(error NEZHA_IMS must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_IMS)),true)
ifneq ($(strip $(TARGET_PRODUCT)),lineage_nezha)
$(error NEZHA_IMS requires TARGET_PRODUCT=lineage_nezha)
endif
ifeq ($(wildcard vendor/xiaomi/nezha-ims/Android.bp),)
$(error NEZHA_IMS requires the private verified-input bundle vendor/xiaomi/nezha-ims/Android.bp)
endif
ifeq ($(wildcard vendor/xiaomi/nezha-ims/tools/verify_inputs.py),)
$(error NEZHA_IMS requires the generated input verifier vendor/xiaomi/nezha-ims/tools/verify_inputs.py)
endif
ifeq ($(wildcard $(NEZHA_DEVICE_PATH)/ims/Android.bp),)
$(error NEZHA_IMS requires the public IMS module definitions at $(NEZHA_DEVICE_PATH)/ims/Android.bp)
endif
# Both namespaces are needed: the public modules import the private filegroups.
PRODUCT_SOONG_NAMESPACES += $(NEZHA_DEVICE_PATH)/ims vendor/xiaomi/nezha-ims
# The app pulls its permission files, JNI links and lib-imsvt through required;
# the three DEX libraries pull their registration XML the same way. The optional
# diagnostics parser is selected explicitly to preserve the full reviewed set.
PRODUCT_PACKAGES += \
    ims \
    qti-telephony-hidl-wrapper \
    qti-telephony-utils \
    ims-ext-common \
    nezha_ims_libdiagatbparser_system
# MMTEL provider selector only; no RCS or GBA provider is named.
PRODUCT_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/ims/overlay
SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/ims/sepolicy/public
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/ims/sepolicy/private
endif
