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
# vendor/xiaomi/nezha-aicore bundle; this fragment admits them by hash and selects the Soong
# module that installs them.
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
# The APK is a signed prebuilt, so it is a Soong android_app_import in the bundle rather than a
# PRODUCT_COPY_FILES entry, and it pulls in the two prebuilt_etc modules it requires. Make refuses
# a prebuilt apk in PRODUCT_COPY_FILES outright.
ifneq ($(filter AiCore,$(PRODUCT_PACKAGES)),)
$(error Another input already provides the AICore application module)
endif
# The bundle's blueprint declares its own Soong namespace, so the directory has to be registered
# or the module is invisible and PRODUCT_PACKAGES reports it as non-existent.
PRODUCT_SOONG_NAMESPACES += vendor/xiaomi/nezha-aicore
PRODUCT_PACKAGES += AiCore
endif
