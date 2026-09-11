# SPDX-License-Identifier: Apache-2.0
# Declare this device's Google AICore support the way its own global firmware does.
#
# AICore hosts Gemini Nano. Its distribution is gated on a declared system feature, not on
# silicon: the global SKU of this same phone (nezha_eea_global, OS3.0.336.0.XPAEUXM) ships
# /product/etc/sysconfig/google_aicore.xml declaring com.google.android.feature.AICORE_QC_SM8850
# and com.google.android.feature.AICORE_QC. Without them Play answers "Your device isn't
# compatible with this version" and the package can never arrive. AICORE_QC_SM8850 names this
# exact SoC, so Google does build Gemini Nano for this NPU.
#
# The platform side is already wired: the GMS PixelConfigOverlayCommon overlay points
# config_defaultOnDeviceIntelligenceService at com.google.android.aicore.
#
# Three files come from that global image and nowhere else: the 21 KB Google-signed OEM stub
# APK that reserves the package for a Play update, its privileged-permission allowlist, and the
# feature declaration. They are proprietary and live only in the ignored
# vendor/xiaomi/nezha-aicore bundle; this fragment admits them by hash and copies them.
# Whether Play then serves the functional AICore, and whether it runs on this build, is a device
# result, not a build result. See config/nezha-aicore.json.
ifneq ($(filter-out 0 1,$(words $(NEZHA_AICORE))),)
$(error NEZHA_AICORE must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_AICORE))),)
$(error NEZHA_AICORE must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_AICORE)),true)
NEZHA_AICORE_BUNDLE ?= vendor/xiaomi/nezha-aicore/proprietary
NEZHA_AICORE_CONTRACT ?= $(NEZHA_DEVICE_PATH)/aicore/contract.json
_nezha_aicore_check := $(shell python3 $(NEZHA_DEVICE_PATH)/aicore/verify.py --bundle $(NEZHA_AICORE_BUNDLE) --contract $(NEZHA_AICORE_CONTRACT) 2>&1)
ifneq ($(_nezha_aicore_check),verified-aicore-global)
$(error AICore admission failed: $(_nezha_aicore_check))
endif
ifneq ($(filter %:$(TARGET_COPY_OUT_PRODUCT)/priv-app/AiCore/AiCore.apk,$(PRODUCT_COPY_FILES)),)
$(error Another input already owns the AICore application destination)
endif
ifneq ($(filter %:$(TARGET_COPY_OUT_PRODUCT)/etc/sysconfig/google_aicore.xml,$(PRODUCT_COPY_FILES)),)
$(error Another input already owns the AICore feature declaration destination)
endif
ifneq ($(filter %:$(TARGET_COPY_OUT_PRODUCT)/etc/permissions/privapp-permissions-aicore-product.xml,$(PRODUCT_COPY_FILES)),)
$(error Another input already owns the AICore privileged-permission destination)
endif
# The bundle is flat: the verifier admits bare names, the destinations are set here.
PRODUCT_COPY_FILES += \
    $(NEZHA_AICORE_BUNDLE)/AiCore.apk:$(TARGET_COPY_OUT_PRODUCT)/priv-app/AiCore/AiCore.apk \
    $(NEZHA_AICORE_BUNDLE)/google_aicore.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/sysconfig/google_aicore.xml \
    $(NEZHA_AICORE_BUNDLE)/privapp-permissions-aicore-product.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/permissions/privapp-permissions-aicore-product.xml
endif
