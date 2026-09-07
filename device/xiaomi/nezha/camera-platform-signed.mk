# A separate source candidate for normal Soong platform signing of the original
# verified Camera APK. The caller must choose this include instead of the
# original presigned Camera product; never include both package definitions.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_PLATFORM_SIGNED))),)
$(error NEZHA_CAMERA_PLATFORM_SIGNED must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_PLATFORM_SIGNED))),)
$(error NEZHA_CAMERA_PLATFORM_SIGNED must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_PLATFORM_SIGNED)),true)
ifneq ($(strip $(NEZHA_XIAOMI_CAMERA)),true)
$(error NEZHA_CAMERA_PLATFORM_SIGNED requires NEZHA_XIAOMI_CAMERA=true)
endif
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERA_PLATFORM_SIGNED requires NEZHA_CAMERA_FRAMEWORK=true)
endif
$(call inherit-product, vendor/xiaomi/nezha-camera-platform/camera-platform-product.mk)
endif
