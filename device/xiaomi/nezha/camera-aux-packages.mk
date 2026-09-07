# Expose auxiliary IDs to the two bundled camera apps through AOSP's package
# allowlist. Camera permission and provider access checks still apply.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_AUX_PACKAGES))),)
$(error NEZHA_CAMERA_AUX_PACKAGES must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_AUX_PACKAGES))),)
$(error NEZHA_CAMERA_AUX_PACKAGES must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_AUX_PACKAGES)),true)
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERA_AUX_PACKAGES requires NEZHA_CAMERA_FRAMEWORK=true)
endif
# Require the measured predecessor so an unrelated product override cannot be
# silently replaced. The original factory fragment remains independently usable.
ifneq ($(filter vendor.camera.aux.packagelist=%,$(PRODUCT_SYSTEM_PROPERTIES)),vendor.camera.aux.packagelist=com.xiaomi.runin,com.xiaomi.cameratest,com.xiaomi.factory.mmi,org.codeaurora.snapcam)
$(error NEZHA_CAMERA_AUX_PACKAGES requires the single reviewed factory camera allowlist)
endif
PRODUCT_SYSTEM_PROPERTIES := $(filter-out vendor.camera.aux.packagelist=%,$(PRODUCT_SYSTEM_PROPERTIES))
PRODUCT_SYSTEM_PROPERTIES += vendor.camera.aux.packagelist=com.android.camera,org.lineageos.aperture
endif
