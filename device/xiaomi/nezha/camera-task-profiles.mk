# SPDX-License-Identifier: Apache-2.0
# Exact preserved vendor libprocessgroup consumes this system_ext filename.
# This is a compatibility candidate, not the OEM limit-level policy.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CAMERA_TASK_PROFILES))),)
$(error NEZHA_CAMERA_TASK_PROFILES must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CAMERA_TASK_PROFILES))),)
$(error NEZHA_CAMERA_TASK_PROFILES must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CAMERA_TASK_PROFILES)),true)
_nezha_camera_task_profile_check := $(shell python3 $(NEZHA_DEVICE_PATH)/camera-task-profiles/verify.py --source-root . 2>&1)
ifneq ($(_nezha_camera_task_profile_check),verified-camera-task-profiles)
$(error Camera task-profile admission failed: $(_nezha_camera_task_profile_check))
endif
ifneq ($(filter %:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/task_profiles_cameraopt.json,$(PRODUCT_COPY_FILES)),)
$(error Another input already owns the camera task-profile destination)
endif
PRODUCT_COPY_FILES += \
    $(NEZHA_DEVICE_PATH)/camera-task-profiles/task_profiles_cameraopt.json:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/task_profiles_cameraopt.json
endif
