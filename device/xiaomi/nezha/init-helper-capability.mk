# SPDX-License-Identifier: Apache-2.0
# The generator admits this capability only for its exact reviewed inputs.
# Other products and legacy candidates leave the upstream default undefined.
ifneq ($(origin NEZHA_INIT_HELPER_CAPABILITY_CONTRACT),undefined)
ifneq ($(origin NEZHA_INIT_HELPER_CAPABILITY_CONTRACT),file)
$(error Nezha init-helper capability cannot be supplied by an override)
endif
ifneq ($(NEZHA_INIT_HELPER_CAPABILITY_CONTRACT),nezha-init-helper-no-property-writes-v1)
$(error Nezha init-helper capability requires its reviewed generator contract)
endif
ifneq ($(origin BOARD_SEPOLICY_M4DEFS),file)
$(error Nezha init-helper M4 definitions cannot be supplied by an override)
endif
# Freeze recursive references before checking the exact list Soong will see.
# Readonly on the outer variable alone cannot freeze later inner-variable edits.
BOARD_SEPOLICY_M4DEFS := $(strip $(BOARD_SEPOLICY_M4DEFS))
# Inspect every token containing the symbol, including malformed or quoted
# spellings. M4's last-definition-wins behavior must never admit duplicates.
ifneq ($(strip $(foreach _nezha_m4def,$(BOARD_SEPOLICY_M4DEFS),$(if $(findstring target_init_dev_config_property_writes,$(_nezha_m4def)),$(_nezha_m4def)))),target_init_dev_config_property_writes=false)
$(error Nezha requires exactly one admitted init-helper M4 definition with value false)
endif

# There is no reviewed helper provider or alternate root-script contract.
# Reject explicit selections, including empty and optional assignments; do
# not turn unresolved expressions into an assertion of provider absence.
ifneq ($(strip $(foreach _nezha_prop,$(PRODUCT_SYSTEM_PROPERTIES) $(PRODUCT_SYSTEM_EXT_PROPERTIES) $(PRODUCT_PRODUCT_PROPERTIES) $(PRODUCT_VENDOR_PROPERTIES) $(PRODUCT_ODM_PROPERTIES) $(PRODUCT_SYSTEM_DLKM_PROPERTIES) $(PRODUCT_VENDOR_DLKM_PROPERTIES) $(PRODUCT_ODM_DLKM_PROPERTIES) $(PRODUCT_PROPERTY_OVERRIDES) $(PRODUCT_DEFAULT_PROPERTY_OVERRIDES) $(PRODUCT_SYSTEM_DEFAULT_PROPERTIES) $(ADDITIONAL_SYSTEM_PROPERTIES) $(ADDITIONAL_VENDOR_PROPERTIES) $(ADDITIONAL_ODM_PROPERTIES),$(if $(or $(findstring ro.vendor.init_dev_config.path,$(_nezha_prop)),$(findstring ro.boot.init_rc,$(_nezha_prop))),$(_nezha_prop)))),)
$(error Nezha init-helper capability rejects uncontracted helper or alternate init-script properties)
endif
ifneq ($(strip $(TARGET_INIT_VENDOR_LIB) $(TARGET_INIT_VENDOR_LIB_V2) $(SOONG_CONFIG_libinit_vendor_init_lib)),)
$(error Nezha init-helper capability rejects an unreviewed vendor init hook)
endif

# The pinned Soong path only reads this list after BoardConfig. A later writer
# must fail in Kati instead of changing the value after the duplicate check.
.KATI_READONLY := NEZHA_INIT_HELPER_CAPABILITY_CONTRACT BOARD_SEPOLICY_M4DEFS
else
ifneq ($(strip $(foreach _nezha_m4def,$(BOARD_SEPOLICY_M4DEFS),$(if $(findstring target_init_dev_config_property_writes,$(_nezha_m4def)),$(_nezha_m4def)))),)
$(error Nezha init-helper M4 definition requires an explicit generator contract)
endif
endif
