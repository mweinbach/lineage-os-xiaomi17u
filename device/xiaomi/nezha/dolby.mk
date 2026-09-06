# SPDX-License-Identifier: Apache-2.0
# Manual control candidate for this phone's preserved factory Dolby backend.
ifneq ($(filter-out 0 1,$(words $(NEZHA_DOLBY_CONTROLLER))),)
$(error NEZHA_DOLBY_CONTROLLER must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_DOLBY_CONTROLLER))),)
$(error NEZHA_DOLBY_CONTROLLER must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_DOLBY_CONTROLLER)),true)
PRODUCT_PACKAGES += NezhaDolbyController
endif
