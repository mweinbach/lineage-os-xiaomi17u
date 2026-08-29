# SPDX-License-Identifier: Apache-2.0
# Exact working76 TWRP on the dedicated recovery partition. Stage/verify with
# scripts/recovery_inputs.py after applying patches/evolution/0005. Missing
# inputs never fall back to generated recovery. Normal Android stays enforcing.

NEZHA_RECOVERY_INPUTS := vendor/xiaomi/nezha-recovery
ifneq ($(NEZHA_RECOVERY_INPUTS),vendor/xiaomi/nezha-recovery)
$(error Nezha recovery inputs must use the verified private vendor/xiaomi/nezha-recovery bundle)
endif

_nezha_recovery_required := $(addprefix $(NEZHA_RECOVERY_INPUTS)/,recovery.img recovery-public.pem receipt.json recovery-inputs.mk)
$(foreach _nezha_file,$(_nezha_recovery_required),$(if $(wildcard $(_nezha_file)),,$(error Missing working76 recovery input $(_nezha_file); run recovery_inputs.py stage)))
include $(NEZHA_RECOVERY_INPUTS)/recovery-inputs.mk

ifneq ($(NEZHA_RECOVERY_SCHEMA_VERSION),2)
$(error Nezha recovery-input schema2 requires the verified public PEM; restage old bundles)
endif
ifneq ($(NEZHA_RECOVERY_IMAGE_SHA256),a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e)
$(error Recovery input is not the verified working76 image)
endif
ifneq ($(NEZHA_RECOVERY_IMAGE_SIZE),104857600)
$(error Nezha recovery input must be exactly 100 MiB)
endif
ifneq ($(NEZHA_RECOVERY_PROFILE_SHA256),caeb78aaff981fc250a9fd0c94ac8d8270d3fa3ded2db75538daffb692ee60d1)
$(error Recovery input was not verified against the current working76 profile)
endif
ifneq ($(NEZHA_RECOVERY_CORE_SHA256),61a40da9741cae2119263ca0a92cd717874a88320e28fb0ee67505bed6829d31)
$(error Recovery input requires the reviewed Evolution prebuilt-recovery consumer)
endif
ifneq ($(NEZHA_RECOVERY_PUBLIC_KEY_SHA256),50784f7b5ccd4cfde172f5cbce06f54e33547d1081c7d28b55e494aa37ab0967)
$(error Recovery input must include the exact verified working76 public PEM)
endif
ifneq ($(NEZHA_RECOVERY_AVB_PUBLIC_KEY_SHA256),020d7559b8ddedf153e77cc4a02af26c666e3746408a230650ef8cd1e8f09b03)
$(error Recovery input public key must match the working76 AVB key)
endif

# The upstream tree has no prebuilt-recovery selector. Check the actual patched
# consumer and the releasetools branch that preserves BOOTABLE_IMAGES bytes.
ifneq ($(shell sha256sum < build/make/core/Makefile 2>/dev/null | cut -d ' ' -f 1),61a40da9741cae2119263ca0a92cd717874a88320e28fb0ee67505bed6829d31)
$(error Apply the exact reviewed 0005 prebuilt-recovery patch before building Nezha)
endif
ifneq ($(shell sha256sum < build/make/tools/releasetools/common.py 2>/dev/null | cut -d ' ' -f 1),78b74437cb9916eda2b25ac4c8afd13b50847648f10c2e4fd66df0e02ab90bc2)
$(error Recovery requires the pinned Evolution releasetools semantics)
endif
ifneq ($(shell test -f vendor/xiaomi/nezha-recovery/recovery.img && test ! -L vendor/xiaomi/nezha-recovery/recovery.img && echo regular),regular)
$(error Recovery input must remain a regular file; run recovery_inputs.py verify)
endif
ifneq ($(strip $(shell wc -c < vendor/xiaomi/nezha-recovery/recovery.img)),104857600)
$(error Recovery image size changed; run recovery_inputs.py verify)
endif
ifneq ($(shell sha256sum < vendor/xiaomi/nezha-recovery/recovery.img | cut -d ' ' -f 1),a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e)
$(error Recovery image bytes changed; run recovery_inputs.py verify)
endif
ifneq ($(shell sha256sum < vendor/xiaomi/nezha-recovery/receipt.json | cut -d ' ' -f 1),$(NEZHA_RECOVERY_RECEIPT_SHA256))
$(error Recovery verification receipt changed; run recovery_inputs.py verify)
endif
ifneq ($(shell test -f vendor/xiaomi/nezha-recovery/recovery-public.pem && test ! -L vendor/xiaomi/nezha-recovery/recovery-public.pem && echo regular),regular)
$(error Recovery public PEM must remain a regular file; run recovery_inputs.py verify)
endif
ifneq ($(shell sha256sum < vendor/xiaomi/nezha-recovery/recovery-public.pem | cut -d ' ' -f 1),50784f7b5ccd4cfde172f5cbce06f54e33547d1081c7d28b55e494aa37ab0967)
$(error Recovery public PEM changed; run recovery_inputs.py verify)
endif

ifneq ($(BOARD_RECOVERYIMAGE_PARTITION_SIZE),104857600)
$(error working76 requires the observed dedicated 100 MiB recovery partition)
endif
ifneq ($(BOARD_BOOT_HEADER_VERSION),4)
$(error working76 requires the dedicated header-v4 recovery layout)
endif
ifneq ($(BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE),true)
$(error working76 is a kernel-free recovery image)
endif
ifneq ($(BOARD_AVB_ENABLE),true)
$(error Nezha prebuilt recovery does not permit disabling AVB)
endif
ifneq ($(filter true,$(BOARD_USES_RECOVERY_AS_BOOT) $(BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT) $(BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT)),)
$(error working76 cannot replace boot or vendor_boot recovery resources)
endif
ifneq ($(strip $(BOARD_CUSTOM_BOOTIMG_MK) $(BOARD_CUSTOM_BOOTIMG)),)
$(error Nezha prebuilt recovery cannot use global custom boot-image rules)
endif

TARGET_PREBUILT_RECOVERY := $(NEZHA_RECOVERY_INPUTS)/recovery.img
TARGET_PREBUILT_RECOVERY_SHA256 := a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e
ifneq ($(TARGET_PREBUILT_RECOVERY),vendor/xiaomi/nezha-recovery/recovery.img)
$(error Nezha requires the staged working76 recovery selector)
endif
ifneq ($(TARGET_PREBUILT_RECOVERY_SHA256),a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e)
$(error Nezha requires the reviewed recovery digest)
endif

# The selected recovery image is never re-signed. Future vbmeta chain metadata
# must use its verified public key, not the generated engineering signing key.
# No private key is staged, and other Android partition signing is unchanged.
BOARD_AVB_RECOVERY_KEY_PATH := $(NEZHA_RECOVERY_INPUTS)/recovery-public.pem
ifneq ($(BOARD_AVB_RECOVERY_KEY_PATH),vendor/xiaomi/nezha-recovery/recovery-public.pem)
$(error Nezha recovery chain key must be the staged working76 public PEM)
endif
ifneq ($(BOARD_AVB_RECOVERY_ALGORITHM),SHA256_RSA4096)
$(error Nezha recovery must retain SHA256_RSA4096)
endif
ifneq ($(BOARD_AVB_RECOVERY_ROLLBACK_INDEX),1)
$(error Nezha recovery must retain rollback index 1)
endif
ifneq ($(BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION),1)
$(error Nezha recovery must retain rollback location 1)
endif

# This does not admit target-files/OTA/super packaging or establish compatibility
# with newly built boot/init_boot/vendor_boot. working76 used stock companions.
_nezha_recovery_required :=
