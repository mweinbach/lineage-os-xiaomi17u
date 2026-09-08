# Factory Camera vendor-key discovery compatibility. Off unless selected.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_VENDOR_KEYS))),)
$(error NEZHA_CAMERA_VENDOR_KEYS must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_VENDOR_KEYS))),)
$(error NEZHA_CAMERA_VENDOR_KEYS must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_VENDOR_KEYS)),true)
ifneq ($(strip $(TARGET_PRODUCT)),lineage_nezha)
$(error NEZHA_CAMERA_VENDOR_KEYS requires TARGET_PRODUCT=lineage_nezha)
endif
ifneq ($(strip $(TARGET_DEVICE)),)
ifneq ($(strip $(TARGET_DEVICE)),nezha)
$(error NEZHA_CAMERA_VENDOR_KEYS requires TARGET_DEVICE=nezha when assigned)
endif
endif
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERA_VENDOR_KEYS requires NEZHA_CAMERA_FRAMEWORK=true)
endif
ifneq ($(strip $(NEZHA_XIAOMI_CAMERA)),true)
$(error NEZHA_CAMERA_VENDOR_KEYS requires NEZHA_XIAOMI_CAMERA=true)
endif
ifneq ($(strip $(NEZHA_CAMERA_PLATFORM_SIGNED)),true)
$(error NEZHA_CAMERA_VENDOR_KEYS requires NEZHA_CAMERA_PLATFORM_SIGNED=true)
endif
PRODUCT_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/camera-vendor-keys/overlay
endif
