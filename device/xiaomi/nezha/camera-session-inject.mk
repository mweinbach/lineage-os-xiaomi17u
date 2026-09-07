# Native Xiaomi camera session hook. Off by default; the ported camera
# framework supplies the library that the enabled hook loads at runtime.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_SESSION_INJECT))),)
$(error NEZHA_CAMERA_SESSION_INJECT must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_SESSION_INJECT))),)
$(error NEZHA_CAMERA_SESSION_INJECT must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_SESSION_INJECT)),true)
ifneq ($(strip $(NEZHA_CAMERA_FRAMEWORK)),true)
$(error NEZHA_CAMERA_SESSION_INJECT requires NEZHA_CAMERA_FRAMEWORK=true)
endif
$(call soong_config_set_bool,nezha_camera_session,enabled,true)
endif
