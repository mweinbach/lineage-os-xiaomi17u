# SPDX-License-Identifier: Apache-2.0
# Mark the framework as QTI value-add capable, as the factory system image does
# ("#System Enable QCOM enhanced feature"). libqti_vndfwk_detect derives
# isRunningWithVendorEnhancedFramework() from this single boolean. With it unset,
# the camera CHI override on SoC 660 replaces the Nezha logical-camera XML with
# kaanapali_gsi.xml, whose implementation IDs never match Xiaomi's expected XML
# IDs 1-4, so the front, wide, ultrawide and tele roles are reported damaged.
# The property is read by every vendor consumer of the detection library, not
# only the camera stack; see config/nezha-qti-value-add-framework.json.
ifneq ($(filter-out 0 1,$(words $(NEZHA_QTI_VALUE_ADD_FRAMEWORK))),)
$(error NEZHA_QTI_VALUE_ADD_FRAMEWORK must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_QTI_VALUE_ADD_FRAMEWORK))),)
$(error NEZHA_QTI_VALUE_ADD_FRAMEWORK must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_QTI_VALUE_ADD_FRAMEWORK)),true)
PRODUCT_SYSTEM_PROPERTIES += \
    ro.vendor.qti.va_aosp.support=1
endif
