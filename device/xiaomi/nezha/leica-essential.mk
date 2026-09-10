# SPDX-License-Identifier: Apache-2.0
# Enable the Xiaomi Leica Essential camera mode (the Leica M3 Monopan and Leica
# M9 film looks, module id 256) on this standard-edition unit.
#
# The stock MiuiCamera application already ships the Leica Essential module, its
# LegendaryModule capture path and the on-device style-transfer models
# (/odm/etc/camera/styletrans/styletrans_{low,high,colorfix}.minn, the
# com.xiaomi.plugin.legendST plugin and libmialgo_styletrans.so). Two gates keep
# it off a standard unit; both are properties, verified against the app bytecode
# and measured on v16 (see config/nezha-leica-essential.json and
# docs/leica-essential-20260910.md):
#
#   1. LegendaryEnter.support() requires the app to run as the Leica edition,
#      which G7.b.O() decides from ro.theme_customize == "LCC". The standard
#      unit leaves this empty because its per-hardware ODM prop file is absent;
#      the Leica Edition ODM sets ro.theme_customize=LCC.
#   2. On resume the app runs a native anti-tamper check
#      (com.camera.LSsdQFvLalapDwvA.RitIeKoenwCSqcPf in libHawk); when it fails,
#      which it does on an unlocked bring-up bootloader, the app posts the
#      "APK version error" exit dialog and closes after three seconds. The check
#      is skipped when F6.d.X is set, which reads camera.debug.safe.check.disable.
#
# Setting both properties makes the standard MiuiCamera present and run Leica
# Essential without altering the device model, market name or attestation
# identity. camera.debug.safe.check.disable disables only the camera
# application's own integrity self-check; it does not touch platform verified
# boot or SELinux.
ifneq ($(filter-out 0 1,$(words $(NEZHA_LEICA_ESSENTIAL))),)
$(error NEZHA_LEICA_ESSENTIAL must contain at most one value)
endif
ifneq ($(filter-out true false,$(strip $(NEZHA_LEICA_ESSENTIAL))),)
$(error NEZHA_LEICA_ESSENTIAL must be true, false or unset)
endif
ifeq ($(strip $(NEZHA_LEICA_ESSENTIAL)),true)
ifneq ($(filter ro.theme_customize=%,$(PRODUCT_SYSTEM_PROPERTIES)),)
$(error NEZHA_LEICA_ESSENTIAL requires exclusive ownership of ro.theme_customize)
endif
ifneq ($(filter camera.debug.safe.check.disable=%,$(PRODUCT_SYSTEM_PROPERTIES)),)
$(error NEZHA_LEICA_ESSENTIAL requires exclusive ownership of camera.debug.safe.check.disable)
endif
PRODUCT_SYSTEM_PROPERTIES += \
    ro.theme_customize=LCC \
    camera.debug.safe.check.disable=true
endif
