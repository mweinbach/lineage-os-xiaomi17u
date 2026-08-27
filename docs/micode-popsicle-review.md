# MiCode popsicle source review for Nezha

Read-only review on **2026-08-27** confirms that the user-linked
`popsicle-w-oss` branch is relevant to Nezha's **Canoe platform and
6.12-android16-5 KMI family**. It does **not** establish a complete, reproducible
kernel source release or board configuration for this China Xiaomi 17 Ultra.
No kernel or ROM was built, no source executable was run, and no phone or
container operation was performed for this review.

The sanitized findings and individual source-file hashes are in
[`research/micode-popsicle-review.json`](../research/micode-popsicle-review.json).
The [community ROM author](community-bringup.md) cites this MiCode branch as
kernel source, but separately states that the device tree is private. That
reference is useful evidence of the author's source choice, not a public
reproducible ROM dependency manifest or a device test performed here.

Fresh remote checks and local Git object verification established these pins:

| Component | Inspected commit | Scope |
| --- | --- | --- |
| [MiCode kernel branch](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/45705be1220b4cfa8100516ad86711656c0b634e) | `45705be1220b4cfa8100516ad86711656c0b634e` | 2,370 tracked files; SoC/vendor code and build definitions. |
| [MiCode device-tree branch](https://github.com/MiCode/kernel_devicetree/tree/667482462e15458b602a2688a94efd47a5010141) | `667482462e15458b602a2688a94efd47a5010141` | 5,837 tracked files; includes Canoe and named sibling-device overlays. |
| [MiCode release index](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/62444eb540a7468f7e329a1bb417dd95c07ac8ab/README.md#L236) | `62444eb540a7468f7e329a1bb417dd95c07ac8ab` | Lists Xiaomi 17, 17 Pro and 17 Pro Max, with base label `release-w-qcom-sm8850`; does not list Nezha. |

Both `popsicle-w-oss` commits are dated March 9, 2026 and explicitly describe
the three sibling models. Case-insensitive searches found **zero Nezha path
matches and zero Nezha text matches in both pinned trees**. The text search was
`git grep -n -I -i nezha HEAD`; it excludes binary files. This is a bounded
finding about these revisions, not proof that shared code cannot support Nezha
or that no Nezha source exists in any other repository.

The references are preserved as clean, detached, ignored checkouts at
`upstream/micode-popsicle-review` and
`upstream/micode-popsicle-devicetree-review`. All reachable Git objects are
present, and `git fsck --full --no-dangling` passed in both. No existing
platform checkout or reference was changed.

The source's [ACK pointer](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/android/ACK_SHA)
names `f1bdb13583da85a47fcf1632a78ef52d6e6da651` and
`android16-6.12-2025-06_r8`. The
[official Android tag](https://android.googlesource.com/kernel/common/+/refs/tags/android16-6.12-2025-06_r8)
independently resolves to that commit. Its
[Makefile](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/Makefile)
declares Linux **6.12.23**, and its
[build constants](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/build.config.constants)
declare `BRANCH=android16-6.12`, `KMI_GENERATION=5`, and
`CLANG_VERSION=r536225`.

That agrees with the captured kernel's version/KMI family and compiler family.
The package and live baseline release is
`6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`; its recovered IKCONFIG
reports Clang 19.0.1 based on `r536225` and enables 4 KiB pages. The exact
captured GKI revision, build inputs and binary equivalence are still unverified.
A single lookup of the abbreviated `75e9b1c7ae7c` commit in `kernel/common`
returned HTTP 404; this does not establish absence from all public sources.
Android's [KMI versioning rules](https://source.android.com/docs/core/architecture/kernel/gki-versioning)
explain the family identifier; matching a label does not perform the required
symbol, configuration or signature checks on these modified-package inputs.

This branch is not a standalone GKI tree. Its
[Kleaf definitions](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/kleaf-scripts/android_build.bzl)
set `KERNEL_DIR=common` and `SOC_DIR=soc-repo`; performance variants use the
[default `//common:kernel_aarch64` label](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/BUILD.bazel#L278).
They require external Kleaf/build rules, the GKI tree, device trees, boot-image
inputs and [many external module targets](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/kleaf-scripts/techpack_modules.bzl),
including camera, display, audio, WLAN and Xiaomi module repositories. Those
references are not a verified complete dependency set or a release of the
closed userspace HALs and camera processing stack.

The local `Makefile` happens to declare 6.11.0. That is **not evidence that the
effective GKI is 6.11**: the inspected DT build explicitly selects
[`//common:Makefile`](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/kleaf-scripts/dtbs.bzl#L68),
and the ACK pointer above identifies the separate base. Local `Kconfig`,
`arch/arm64/configs/gki_defconfig`, `Module.symvers`, and the declared
`android/abi_gki_aarch64_qcom` export are absent from this pinned tree. Resolve
the intended source composition before treating these declarations as a build.

The named configurations are
[Popsicle, Pudding and Pandora on Canoe](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/target_variants.bzl).
The [Popsicle target](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/kleaf-scripts/targets/popsicle.bzl)
merges common Canoe and device fragments; it is not a Nezha defconfig. Its
early-console address and the Canoe image config's base address are reference
settings, not approved Nezha values. Likewise, the image-packing `PAGE_SIZE=4096`
does not independently prove the built kernel's page configuration or any
physical partition size.

The supplied package's DTBO root was independently read from the already
extracted, hash-verified FDT bytes. It contains the same generic Qualcomm
compatible strings and the same set of MSM ID pairs as the three published
overlays, but their Xiaomi board identities differ:

| DTBO source | Root model suffix | `qcom,board-id` | `xiaomi,miboard-id` |
| --- | --- | --- | --- |
| Supplied Nezha package | Nezha based on SM8850 | `<8 0>` | **`<5 0>`** |
| [Published Popsicle overlay](https://github.com/MiCode/kernel_devicetree/blob/667482462e15458b602a2688a94efd47a5010141/qcom/popsicle-sm8850-overlay.dtso) | Popsicle based on SM8850 | `<8 0>` | `<1 0>` |
| [Published Pudding overlay](https://github.com/MiCode/kernel_devicetree/blob/667482462e15458b602a2688a94efd47a5010141/qcom/pudding-sm8850-overlay.dtso) | Pudding based on SM8850 | `<8 0>` | `<2 0>` |
| [Published Pandora overlay](https://github.com/MiCode/kernel_devicetree/blob/667482462e15458b602a2688a94efd47a5010141/qcom/pandora-sm8850-overlay.dtso) | Pandora based on SM8850 | `<8 0>` | `<3 0>` |

The Nezha FDT SHA256 is
`4bb4b31bca5de3e354a565304d1ea277ac6d9b70e2760a40147d9f151a691f99`.
These are static package/source properties, not a live bootloader-selection
test. Shared `qcom,canoe` compatibility or board ID 8 cannot establish exact
panel, touch, camera, charging or China-variant configuration. Do not substitute
a sibling overlay or copy its hardware addresses into an active device tree.

The [boot and module contract](boot-contract.md) remains the controlling local
evidence: **914 module instances, 637 distinct payloads and 635 normalized
module names**, split across vendor ramdisk, vendor_dlkm and system_dlkm.
Vendor and GKI releases differ in their build suffixes. Their imported
`module_layout` CRC agrees, but vendor and system zram expect different
`zs_malloc` CRCs. Kernel/provider exports, cryptographic module signatures and
runtime loading have not been verified.

The branch includes
[vendor zram](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/drivers/block/zram/modules.bzl)
and [zsmalloc definitions](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/mm/modules.bzl),
which are relevant leads for this split. Their equivalence to the captured
binaries is unproven. All three sibling `modules.systemdlkm_blocklist` files
are empty, whereas the supplied Nezha package blocks the system `zram` and
`zsmalloc` copies. Do not replace the captured stage-specific policy with those
empty reference files.

A Canoe `kernel_abi` target exists, but was not run. The
[consolidate/debug target](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/kleaf-scripts/consolidate.bzl)
explicitly relaxes KMI trimming/strictness and includes a module-signing-disabled
fragment. Those settings have **not** been adopted. A debug build that omits
these checks would not establish a suitable production kernel for this work.

The [kernel COPYING file](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/COPYING)
declares GPL-2.0 with the Linux syscall exception; the three reviewed overlay
files declare BSD-3-Clause. Preserve the applicable source notices. Before
distributing GPL-covered kernel/module binaries, satisfy the corresponding
source requirements, including applicable modifications and build scripts;
an unrelated or incomplete reference link does not establish this. See the
[GPLv2 terms](https://raw.githubusercontent.com/torvalds/linux/master/LICENSES/preferred/GPL-2.0)
and [Linux licensing rules](https://docs.kernel.org/process/license-rules.html).
This review does not determine another publisher's license compliance or grant
redistribution rights for proprietary userspace, APKs, firmware or blobs.

The next source gate is the exact Nezha board definition plus a pinned complete
GKI/module/build dependency graph or an explicitly reviewed prebuilt strategy.
Compare its resulting configuration, DTs, symbols, CRCs, signatures and module
load policy with authenticated China firmware. The existing AVB failures,
physical geometry gaps, VINTF/SELinux requirements, bootloader-state question
and separately authorized hardware tests remain unresolved. No lunch target
or native-feature compatibility has been asserted by this review.

The ignored evidence directory is
`reports/micode-popsicle-review-20260827/`; it contains 29 hash-checked selected
public source files, the retrieved release index and ACK files, search results,
and bounded private-input hash/property checks. Receipt SHA256:
`9a094677d2164004565a6794a678994a4b47804da29719513e62e27d38086abe`.
The earlier community-page receipt remains separate. No raw firmware or module
contents are included in Git. The offline record tests require neither the
reference checkouts nor a phone or network.
