# The factory EcoEngine config enables third-party JPEG_R after an ordinary
# configuration. Seed that same value for a fresh persistent-property store so
# the first JPEG_R session can reach EcoEngine. Existing persisted values retain
# Android's normal precedence. The factory vendor/odm images are unchanged.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_JPEGR_DEFAULT))),)
$(error NEZHA_CAMERA_JPEGR_DEFAULT must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_JPEGR_DEFAULT))),)
$(error NEZHA_CAMERA_JPEGR_DEFAULT must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_JPEGR_DEFAULT)),true)
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERA_JPEGR_DEFAULT requires NEZHA_CAMERA_FRAMEWORK=true)
endif
PRODUCT_SYSTEM_PROPERTIES += persist.vendor.camera.sdk.third.jpegr.enable=1
endif
