# CameraOpt's retained JNI imports the factory cpuset query ABI. This opt-in
# restores the query in the platform library without replacing libprocessgroup.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERAOPT_NATIVE_COMPAT))),)
$(error NEZHA_CAMERAOPT_NATIVE_COMPAT must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERAOPT_NATIVE_COMPAT))),)
$(error NEZHA_CAMERAOPT_NATIVE_COMPAT must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERAOPT_NATIVE_COMPAT)),true)
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERAOPT_NATIVE_COMPAT requires NEZHA_CAMERA_FRAMEWORK=true)
endif
$(call soong_config_set_bool,nezha_cameraopt,native_compat,true)
endif
