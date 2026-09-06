# SPDX-License-Identifier: Apache-2.0
# Bound the framework defaults to this panel's advertised maximum. This does
# not change saved user settings or enable unqualified low-brightness modes.
ifneq ($(filter-out 0 1,$(words $(NEZHA_REFRESH_POLICY))),)
$(error NEZHA_REFRESH_POLICY must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_REFRESH_POLICY))),)
$(error NEZHA_REFRESH_POLICY must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_REFRESH_POLICY)),true)
ifeq ($(wildcard $(NEZHA_DEVICE_PATH)/refresh-overlay/frameworks/base/core/res/res/values/config.xml),)
$(error NEZHA_REFRESH_POLICY requires its framework resource overlay)
endif
DEVICE_PACKAGE_OVERLAYS += $(NEZHA_DEVICE_PATH)/refresh-overlay
endif
