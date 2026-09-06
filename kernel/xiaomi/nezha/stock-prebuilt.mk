# SPDX-License-Identifier: Apache-2.0
# Nezha candidate inputs only. Include before Evolution's BoardConfigKernel.mk.
# See README.md for the pinned build semantics and unresolved compatibility gates.

ifndef _NEZHA_STOCK_PREBUILT_INCLUDED
_NEZHA_STOCK_PREBUILT_INCLUDED := true

NEZHA_KERNEL_INPUTS ?= vendor/xiaomi/nezha-kernel
ifneq ($(words $(NEZHA_KERNEL_INPUTS)),1)
$(error NEZHA_KERNEL_INPUTS must name one verified kernel-input bundle directory)
endif

# Overrides require a separately reviewed contract and a hash-verified receipt.
# These expected values are comparison inputs, not authentication or boot proof.
# The bundle's provenance kind selects which checks apply: `prebuilt` bundles
# come from a captured package; `source` bundles come from a recorded ACK and
# vendor build. Both kinds share every module, DTB, DTBO and boot setting below.
NEZHA_EXPECTED_KERNEL_PROVENANCE_KIND ?= prebuilt
NEZHA_EXPECTED_KERNEL_PACKAGE_SHA256 ?= b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69
NEZHA_EXPECTED_KERNEL_RELEASE ?= 6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k
NEZHA_EXPECTED_KERNEL_AVB_STATUS ?= failed
NEZHA_EXPECTED_KERNEL_ORIGIN_VERIFIED ?= false
NEZHA_EXPECTED_KERNEL_SOURCE_ACK_COMMIT ?= f1bdb13583da85a47fcf1632a78ef52d6e6da651
NEZHA_EXPECTED_KERNEL_SOURCE_VENDOR_COMMIT ?= 45705be1220b4cfa8100516ad86711656c0b634e
NEZHA_EXPECTED_KERNEL_SOURCE_DEFCONFIG_SHA256 ?=

# Bundles generated before the provenance kind existed are prebuilt bundles.
NEZHA_KERNEL_PROVENANCE_KIND := prebuilt

# A missing bundle is an error, not permission to omit the kernel or modules.
include $(NEZHA_KERNEL_INPUTS)/kernel-inputs.mk

ifneq ($(NEZHA_STOCK_INPUTS_SCHEMA_VERSION),1)
$(error Unsupported Nezha kernel-input schema; regenerate and verify the bundle)
endif
ifneq ($(NEZHA_KERNEL_PROVENANCE_KIND),$(NEZHA_EXPECTED_KERNEL_PROVENANCE_KIND))
$(error Kernel-input provenance kind $(NEZHA_KERNEL_PROVENANCE_KIND) differs from the expected $(NEZHA_EXPECTED_KERNEL_PROVENANCE_KIND))
endif
ifneq ($(NEZHA_STOCK_KERNEL_RELEASE),$(NEZHA_EXPECTED_KERNEL_RELEASE))
$(error Kernel-input release does not match the reviewed Nezha 4 KiB kernel)
endif
ifeq ($(NEZHA_KERNEL_PROVENANCE_KIND),prebuilt)
ifneq ($(NEZHA_STOCK_INPUTS_PACKAGE_SHA256),$(NEZHA_EXPECTED_KERNEL_PACKAGE_SHA256))
$(error Kernel-input bundle does not match the reviewed Nezha package)
endif
ifneq ($(NEZHA_STOCK_INPUT_AVB_STATUS),$(NEZHA_EXPECTED_KERNEL_AVB_STATUS))
$(error Kernel-input AVB status differs from the reviewed package; review new evidence first)
endif
ifneq ($(NEZHA_STOCK_INPUT_ORIGIN_VERIFIED),$(NEZHA_EXPECTED_KERNEL_ORIGIN_VERIFIED))
$(error Kernel-input origin status differs from the reviewed package; review new evidence first)
endif
else ifeq ($(NEZHA_KERNEL_PROVENANCE_KIND),source)
ifneq ($(NEZHA_KERNEL_SOURCE_ACK_COMMIT),$(NEZHA_EXPECTED_KERNEL_SOURCE_ACK_COMMIT))
$(error Source kernel bundle was built from ACK $(NEZHA_KERNEL_SOURCE_ACK_COMMIT), not the reviewed commit)
endif
ifneq ($(NEZHA_KERNEL_SOURCE_VENDOR_COMMIT),$(NEZHA_EXPECTED_KERNEL_SOURCE_VENDOR_COMMIT))
$(error Source kernel bundle was built from vendor commit $(NEZHA_KERNEL_SOURCE_VENDOR_COMMIT), not the reviewed commit)
endif
ifeq ($(strip $(NEZHA_EXPECTED_KERNEL_SOURCE_DEFCONFIG_SHA256)),)
$(error Set NEZHA_EXPECTED_KERNEL_SOURCE_DEFCONFIG_SHA256 to the reviewed defconfig hash before selecting a source kernel)
endif
ifneq ($(NEZHA_KERNEL_SOURCE_DEFCONFIG_SHA256),$(NEZHA_EXPECTED_KERNEL_SOURCE_DEFCONFIG_SHA256))
$(error Source kernel bundle defconfig differs from the reviewed defconfig)
endif
else
$(error Unsupported Nezha kernel provenance kind: $(NEZHA_KERNEL_PROVENANCE_KIND))
endif

# The core installer flattens .ko paths. Check inventory collisions without
# sorting or deduplicating the independent ordered load lists.
define _nezha_check_module_stage
$(if $(strip $(NEZHA_STOCK_$(1)_MODULES)),,$(error Missing Nezha $(2) module inventory))
$(if $(filter-out $(NEZHA_KERNEL_INPUTS)/modules/$(2)/%,$(NEZHA_STOCK_$(1)_MODULES)),$(error Nezha $(2) module is outside its bundle stage))
$(if $(filter-out %.ko,$(NEZHA_STOCK_$(1)_MODULES)),$(error Nezha $(2) module inventory contains a non-KO input))
$(if $(filter $(words $(NEZHA_STOCK_$(1)_MODULES)),$(words $(sort $(notdir $(NEZHA_STOCK_$(1)_MODULES))))),,$(error Nezha $(2) module basenames collide after installation))
endef
$(eval $(call _nezha_check_module_stage,VENDOR_RAMDISK,vendor_ramdisk))
$(eval $(call _nezha_check_module_stage,VENDOR,vendor_dlkm))
$(eval $(call _nezha_check_module_stage,SYSTEM,system_dlkm))

_nezha_stock_required_files := \
    $(NEZHA_KERNEL_INPUTS)/receipt.json \
    $(NEZHA_KERNEL_INPUTS)/kernel/Image \
    $(NEZHA_KERNEL_INPUTS)/dtb/vendor.dtb \
    $(NEZHA_KERNEL_INPUTS)/dtbo/dtbo.img \
    $(NEZHA_STOCK_VENDOR_RAMDISK_MODULES) \
    $(NEZHA_STOCK_VENDOR_MODULES) \
    $(NEZHA_STOCK_SYSTEM_MODULES) \
    $(NEZHA_STOCK_VENDOR_RAMDISK_MODULES_BLOCKLIST_FILE) \
    $(NEZHA_STOCK_VENDOR_MODULES_BLOCKLIST_FILE) \
    $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)
$(foreach _nezha_file,$(_nezha_stock_required_files),$(if $(wildcard $(_nezha_file)),,$(error Missing Nezha kernel input: $(_nezha_file))))
ifneq ($(wildcard $(NEZHA_KERNEL_INPUTS)/dtb/*.dtb),$(NEZHA_KERNEL_INPUTS)/dtb/vendor.dtb)
$(error Nezha DTB directory must contain only the exact concatenated vendor.dtb)
endif

# This directory is a wrapper, not kernel source. Evolution tests directory
# existence when selecting a source build; a defined empty value blocks ?=.
TARGET_KERNEL_SOURCE :=
TARGET_KERNEL_ARCH := arm64
TARGET_KERNEL_VERSION := $(word 1,$(subst ., ,$(NEZHA_STOCK_KERNEL_RELEASE))).$(word 2,$(subst ., ,$(NEZHA_STOCK_KERNEL_RELEASE)))
TARGET_PREBUILT_KERNEL := $(NEZHA_KERNEL_INPUTS)/kernel/Image
BOARD_KERNEL_VERSION := $(NEZHA_STOCK_KERNEL_RELEASE)

# Image-format observations, not physical partition sizes or a kernel rebuild.
BOARD_BOOT_HEADER_VERSION := 4
BOARD_KERNEL_PAGESIZE := 4096
BOARD_RAMDISK_USE_LZ4 := true
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_PREBUILT_DTBIMAGE_DIR := $(NEZHA_KERNEL_INPUTS)/dtb
BOARD_PREBUILT_DTBOIMAGE := $(NEZHA_KERNEL_INPUTS)/dtbo/dtbo.img

# Keep existing module bytes and signatures. SYSTEM is already copied without
# a strip staging directory by the pinned build core; no extra flag is needed.
BOARD_DO_NOT_STRIP_VENDOR_RAMDISK_MODULES := true
BOARD_DO_NOT_STRIP_VENDOR_MODULES := true
BOARD_VENDOR_RAMDISK_KERNEL_MODULES := $(NEZHA_STOCK_VENDOR_RAMDISK_MODULES)
BOARD_VENDOR_KERNEL_MODULES := $(NEZHA_STOCK_VENDOR_MODULES)
BOARD_SYSTEM_KERNEL_MODULES := $(NEZHA_STOCK_SYSTEM_MODULES)

# Empty vendor LOAD lists normally mean "load all" in build core; SYSTEM already
# defaults to false. Explicit false keeps empty lists empty in all three stages.
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD := $(if $(strip $(NEZHA_STOCK_VENDOR_RAMDISK_MODULES_LOAD)),$(NEZHA_STOCK_VENDOR_RAMDISK_MODULES_LOAD),false)
BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD := $(NEZHA_STOCK_VENDOR_RAMDISK_RECOVERY_MODULES_LOAD)
BOARD_VENDOR_KERNEL_MODULES_LOAD := $(if $(strip $(NEZHA_STOCK_VENDOR_MODULES_LOAD)),$(NEZHA_STOCK_VENDOR_MODULES_LOAD),false)
BOARD_SYSTEM_KERNEL_MODULES_LOAD := $(if $(strip $(NEZHA_STOCK_SYSTEM_MODULES_LOAD)),$(NEZHA_STOCK_SYSTEM_MODULES_LOAD),false)
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_VENDOR_RAMDISK_MODULES_BLOCKLIST_FILE)
BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_VENDOR_MODULES_BLOCKLIST_FILE)
BOARD_SYSTEM_KERNEL_MODULES_BLOCKLIST_FILE := $(NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE)

# No stock ramdisk is activated. The product owns fresh ramdisks, separate
# init_boot/recovery, DLKM filesystems/mounts, geometry, AVB and enforcing policy.
$(warning Nezha candidate kernel inputs report AVB=$(NEZHA_STOCK_INPUT_AVB_STATUS) and origin_verified=$(NEZHA_STOCK_INPUT_ORIGIN_VERIFIED); kernel/module compatibility and device boot are unverified)

_nezha_stock_required_files :=
_nezha_check_module_stage :=
endif
