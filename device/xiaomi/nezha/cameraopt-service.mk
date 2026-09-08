# Authored CameraOpt service, selected explicitly for the signed camera variant.
# The unchanged factory JAR supplies Binder protocol and the complete verifier.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERAOPT_SERVICE))),)
$(error NEZHA_CAMERAOPT_SERVICE must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERAOPT_SERVICE))),)
$(error NEZHA_CAMERAOPT_SERVICE must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERAOPT_SERVICE)),true)
# TARGET_DEVICE is assigned after product inheritance during early dumpvars.
# TARGET_PRODUCT already identifies the selected product in both phases.
ifneq ($(strip $(TARGET_PRODUCT)),lineage_nezha)
$(error NEZHA_CAMERAOPT_SERVICE requires TARGET_PRODUCT=lineage_nezha)
endif
ifneq ($(strip $(TARGET_DEVICE)),)
ifneq ($(strip $(TARGET_DEVICE)),nezha)
$(error NEZHA_CAMERAOPT_SERVICE requires TARGET_DEVICE=nezha)
endif
endif
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERAOPT_SERVICE requires NEZHA_CAMERA_FRAMEWORK=true)
endif
ifneq ($(strip $(NEZHA_CAMERAOPT_NATIVE_COMPAT)),true)
$(error NEZHA_CAMERAOPT_SERVICE requires NEZHA_CAMERAOPT_NATIVE_COMPAT=true)
endif
ifneq ($(strip $(NEZHA_CAMERA_PLATFORM_SIGNED)),true)
$(error NEZHA_CAMERAOPT_SERVICE requires NEZHA_CAMERA_PLATFORM_SIGNED=true)
endif
ifneq ($(strip $(NEZHA_CAMERA_AUX_PACKAGES)),true)
$(error NEZHA_CAMERAOPT_SERVICE requires NEZHA_CAMERA_AUX_PACKAGES=true)
endif
ifneq ($(filter miui-cameraopt nezha-cameraopt-service platform:miui-cameraopt platform:nezha-cameraopt-service system_ext:miui-cameraopt system_ext:nezha-cameraopt-service,$(PRODUCT_SYSTEM_SERVER_JARS)),)
$(error NEZHA_CAMERAOPT_SERVICE requires exclusive ownership of its system-server classpath entries)
endif
PRODUCT_PACKAGES += miui-cameraopt nezha-cameraopt-service
# Explicit partition qualifiers also set the runtime and dexpreopt locations.
PRODUCT_SYSTEM_SERVER_JARS += system_ext:miui-cameraopt system_ext:nezha-cameraopt-service
PRODUCT_SYSTEM_PROPERTIES += ro.nezha.cameraopt.service=true
PRODUCT_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/cameraopt-service/overlay
SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/cameraopt-service/sepolicy/public
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(NEZHA_DEVICE_PATH)/cameraopt-service/sepolicy/private
endif
