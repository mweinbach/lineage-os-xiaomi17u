# SPDX-License-Identifier: Apache-2.0
# Expose existing Android controls while preserving the factory vendor tuning.
# Native delivery and the perceptible low/medium/high range still need testing.
ifneq ($(filter-out 0 1,$(words $(NEZHA_HAPTICS_CONTROLS))),)
$(error NEZHA_HAPTICS_CONTROLS must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_HAPTICS_CONTROLS))),)
$(error NEZHA_HAPTICS_CONTROLS must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_HAPTICS_CONTROLS)),true)
DEVICE_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/haptics-overlay
endif
