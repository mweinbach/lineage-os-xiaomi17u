# Ported HyperOS camera framework: native libraries, configs, the CameraMind
# app and the factory camera system properties. Selected per build, off by
# default. The proprietary blobs and their Soong modules live in the ignored
# vendor/xiaomi/nezha-camera-framework bundle; this fragment only selects them
# and sets the same system properties the factory system build.prop declares.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_FRAMEWORK))),)
$(error NEZHA_CAMERA_FRAMEWORK must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_FRAMEWORK))),)
$(error NEZHA_CAMERA_FRAMEWORK must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(call inherit-product-if-exists, vendor/xiaomi/nezha-camera-framework/camera-framework.packages.mk)
PRODUCT_SYSTEM_PROPERTIES += \
    vendor.camera.support.mivi=true \
    vendor.camera.aux.packagelist=com.xiaomi.runin,com.xiaomi.cameratest,com.xiaomi.factory.mmi,org.codeaurora.snapcam \
    vendor.camera.aux.packagelistext=com.xiaomi.factory.CameraTestItem,com.firefightcam1,com.phonetest.hwttss \
    persist.vendor.camera.privapp.list=org.codeaurora.snapcam \
    hypercamera.disable_app_default_config=true
endif
