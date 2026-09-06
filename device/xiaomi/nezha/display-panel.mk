# SPDX-License-Identifier: Apache-2.0
# Native/device qualification is pending; only select with a generated packet.
ifneq ($(filter-out 0 1,$(words $(NEZHA_CALIBRATED_DISPLAY))),)
$(error NEZHA_CALIBRATED_DISPLAY must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_CALIBRATED_DISPLAY))),)
$(error NEZHA_CALIBRATED_DISPLAY must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_CALIBRATED_DISPLAY)),true)
$(call inherit-product, vendor/xiaomi/nezha-display/display-product.mk)
endif
