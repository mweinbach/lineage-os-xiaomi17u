# Nezha stock-kernel candidate

`stock-prebuilt.mk` connects a locally generated, verified kernel-input bundle
to the pinned Evolution build. It does not contain a kernel, vendor modules,
firmware, or a complete device product. This file does not stage inputs. The
coordinating workflow owns source-volume staging and its host, receipt and
sole-writer checks.

The reviewed defaults use the supplied Xiaomi.eu package with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its origin is unverified and its retained AVB metadata fails against
`vendor_boot` and all eight logical images. Reusing extracted components does
not repair that chain or establish OEM trust. See the
[boot contract](../../../docs/boot-contract.md) for the recorded evidence and
unresolved kernel/module compatibility.

The intended BoardConfig include order is:

```make
NEZHA_KERNEL_INPUTS ?= vendor/xiaomi/nezha-kernel
include kernel/xiaomi/nezha/stock-prebuilt.mk
# Include Evolution's BoardConfigKernel.mk after this wrapper, through the
# product's normal vendor/lineage BoardConfig integration.
```

The generated bundle must contain `kernel-inputs.mk`, a hashed `receipt.json`
manifest, `kernel/Image`, the exact concatenated `dtb/vendor.dtb`,
`dtbo/dtbo.img`, and the three module stages. Original compressed ramdisks and
optional `config/fstab.qcom` are reference evidence only. The stock first-stage
fstab omits AVB flags; this wrapper neither installs it nor selects a prebuilt
ramdisk.

Prepare the reviewed default bundle from the repository root with:

```sh
python3 scripts/kernel_inputs.py \
  --contract kernel/xiaomi/nezha/inputs-xiaomi-eu-OS3.0.309.0.json \
  --source-root artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69 \
  --output artifacts/kernel-inputs/nezha-xiaomi-eu-candidate-v1 \
  --purpose build-candidate
```

This prepares a local ignored bundle. It does not stage into the Linux source
volume, flash a phone, or turn failed input AVB into a passing boot chain.

Bundle verification must check file hashes before use. The wrapper checks
metadata, required paths and module basename collisions; Make parsing is not
cryptographic receipt verification. A new baseline requires its own reviewed
contract and hash-verified receipt before changing the caller's expected values.
Changing an expectation alone proves neither provenance nor compatibility.

## Generated include contract

The packager emits schema version `1` and metadata compared with these caller
expectations. The `?=` defaults remain the reviewed Xiaomi.eu baseline:

| Generated metadata | Caller expectation | Reviewed default |
| --- | --- | --- |
| `NEZHA_STOCK_INPUTS_PACKAGE_SHA256` | `NEZHA_EXPECTED_KERNEL_PACKAGE_SHA256` | The package hash above |
| `NEZHA_STOCK_KERNEL_RELEASE` | `NEZHA_EXPECTED_KERNEL_RELEASE` | `6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k` |
| `NEZHA_STOCK_INPUT_AVB_STATUS` | `NEZHA_EXPECTED_KERNEL_AVB_STATUS` | `failed` |
| `NEZHA_STOCK_INPUT_ORIGIN_VERIFIED` | `NEZHA_EXPECTED_KERNEL_ORIGIN_VERIFIED` | `false` |

These fields preserve the known input limitations; they are not a build or
hardware-validation pass. The generated list variables map as follows:

| Generated variable | Android build variable |
| --- | --- |
| `NEZHA_STOCK_VENDOR_RAMDISK_MODULES` | `BOARD_VENDOR_RAMDISK_KERNEL_MODULES` |
| `NEZHA_STOCK_VENDOR_RAMDISK_MODULES_LOAD` | `BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD` |
| `NEZHA_STOCK_VENDOR_RAMDISK_RECOVERY_MODULES_LOAD` | `BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD` |
| `NEZHA_STOCK_VENDOR_MODULES` | `BOARD_VENDOR_KERNEL_MODULES` |
| `NEZHA_STOCK_VENDOR_MODULES_LOAD` | `BOARD_VENDOR_KERNEL_MODULES_LOAD` |
| `NEZHA_STOCK_SYSTEM_MODULES` | `BOARD_SYSTEM_KERNEL_MODULES` |
| `NEZHA_STOCK_SYSTEM_MODULES_LOAD` | `BOARD_SYSTEM_KERNEL_MODULES_LOAD` |
| `NEZHA_STOCK_VENDOR_RAMDISK_MODULES_BLOCKLIST_FILE` | `BOARD_VENDOR_RAMDISK_KERNEL_MODULES_BLOCKLIST_FILE` |
| `NEZHA_STOCK_VENDOR_MODULES_BLOCKLIST_FILE` | `BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE` |
| `NEZHA_STOCK_SYSTEM_MODULES_BLOCKLIST_FILE` | `BOARD_SYSTEM_KERNEL_MODULES_BLOCKLIST_FILE` |

Module inventory values are paths rooted at `$(NEZHA_KERNEL_INPUTS)` under
`modules/vendor_ramdisk/`, `modules/vendor_dlkm/`, or `modules/system_dlkm/`.
The bundle retains each source suffix after `lib/modules/`, including system
release/subdirectories. Installation flattens those paths to module basenames;
each stage must have unique basenames. Load lists preserve the observed order
and duplicate entries. They must not be synthesized by sorting the inventory.
The build regenerates dependency/alias/softdep metadata, while blocklists pass
through its syntax validator. Original metadata remains in the bundle for
comparison; generated filesystem bytes are not claimed to equal stock.

The recovery list above produces `modules.load.recovery` in the vendor ramdisk.
It does not populate a separate recovery image. Empty normal load lists map to
the build's literal `false` sentinel. This prevents implicit load-all on the
vendor paths and matches the existing system-module default. An absent recovery
list remains unset. The successful host Soong bootstrap did not exercise these
device rules in an Android build.

## Pinned build behavior

The wrapper targets Evolution build
[`a438ca40c6ed779042f806142b1165ba1360a7b2`](https://github.com/Evolution-X/build/tree/a438ca40c6ed779042f806142b1165ba1360a7b2)
and vendor integration
[`11d2966a3294a0a692fc958127c770cfe9c00a3c`](https://github.com/Evolution-X/vendor_evolution/tree/11d2966a3294a0a692fc958127c770cfe9c00a3c),
both recorded in the resolved platform manifest.

`TARGET_PREBUILT_KERNEL` receives `kernel/Image`, not a complete `boot.img`.
`TARGET_KERNEL_SOURCE` is explicitly empty before Evolution's defaults, because
the wrapper directory would otherwise be mistaken for kernel source and fail
the defconfig check. `TARGET_KERNEL_VERSION` uses the reviewed release's
major/minor components (`6.12` by default) without a source Makefile. Evolution
installs the kernel itself; no separate product include or `PRODUCT_COPY_FILES`
entry for `kernel` is required.
[Kernel defaults](https://github.com/Evolution-X/vendor_evolution/blob/11d2966a3294a0a692fc958127c770cfe9c00a3c/config/BoardConfigKernel.mk#L65-L82),
[prebuilt selection](https://github.com/Evolution-X/vendor_evolution/blob/11d2966a3294a0a692fc958127c770cfe9c00a3c/build/tasks/kernel.mk#L151-L242),
[installation](https://github.com/Evolution-X/vendor_evolution/blob/11d2966a3294a0a692fc958127c770cfe9c00a3c/build/tasks/kernel.mk#L783-L792)

Boot header v4 and 4,096-byte vendor-boot alignment are recorded format
constraints. `BOARD_MKBOOTIMG_ARGS` supplies `--header_version 4`;
`BOARD_KERNEL_PAGESIZE=4096` controls image packing, not kernel compilation.
The extracted kernel already has `CONFIG_ARM64_4K_PAGES=y`. Legacy LZ4 is used
for newly built ramdisks. No physical partition capacity is inferred from an
input image length. [Boot construction](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/Makefile#L1181-L1209),
[AOSP vendor boot format](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions)

`BOARD_PREBUILT_DTBIMAGE_DIR` contains exactly one already concatenated file;
the core concatenation rule therefore preserves its internal DTB order.
Despite its name, `BOARD_INCLUDE_DTB_IN_BOOTIMG` routes the DTB to `vendor_boot`
when that image is built, unless `vendor_kernel_boot` is enabled and takes
precedence. This wrapper does not configure that additional partition.
`BOARD_PREBUILT_DTBOIMAGE` supplies the DTBO input;
the normal AVB rule adds output hash metadata using the product's configured
signing arguments. The wrapper does not provide signing keys or change
verification policy.
[DTB and DTBO rules](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/Makefile#L953-L983)

Vendor and vendor-ramdisk modules set their supported `BOARD_DO_NOT_STRIP_*`
flags to preserve the supplied bytes and any signatures. The system-module
path already omits the strip stage; there is no invented system no-strip flag.
Preserving bytes is not a KMI, symbol CRC, signature-trust, or load-order test.
The boot kernel and vendor module vermagic have different release suffixes.
[Module copy/load rules](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/Makefile#L362-L676),
[AOSP kernel module support](https://source.android.com/docs/core/architecture/kernel/kernel-module-support)

## Product responsibilities

The caller must configure separate init_boot and recovery behavior, fresh
ramdisks and first-stage fstab, enforcing SELinux, AVB/signing/rollback policy,
verified physical partition geometry, and the vendor/system DLKM filesystem
and mount configuration. Core derives `BOARD_USES_VENDOR_DLKMIMAGE` and
`BOARD_USES_SYSTEM_DLKMIMAGE` from the corresponding filesystem/prebuilt-image
settings; setting those derived flags alone does not create the partitions.
Without DLKM configuration, module rules route into vendor/system instead.
[DLKM image selection](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/board_config.mk#L742-L864)

The wrapper does not select a product, register a lunch target, compile a
replacement kernel, append another device's DTB, or disable kernel, VINTF,
KMI, signing, AVB, or SELinux checks. `BOARD_KERNEL_VERSION` records the full
release; when OTA kernel requirements are enabled, the pinned core checks it
against the extracted kernel and still extracts IKCONFIG.
[Kernel-version/config verification](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/Makefile#L4982-L5023)

An official kernel-source strategy, complete module compatibility, a verified
boot chain and reproducible device tests remain unresolved. This input mapping
does not establish that the candidate boots or that any native feature works.

Nine synthetic GNU Make checks cover wrapper parsing, variable mapping and
ordered loads, empty-load behavior, repeated inclusion, missing inputs, extra
DTBs, flattened module-name collisions, stage boundaries, and default or
caller-selected metadata expectations. They use temporary text fixtures, not
firmware or an Android build. Repository packager tests remain separate.
