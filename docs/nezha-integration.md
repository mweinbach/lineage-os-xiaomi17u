# Nezha integration plan and activation gates

This plan applies to the user's **China-hardware Xiaomi 17 Ultra (`nezha`,
SM8850 / `canoe`)** and Evolution X **Android 16 QPR2 `bka`**. An authored
`framework-checks` product is now registered, passes Soong/Kati and has built
Android ARM64 `libbase.so` and the x86-64 host VINTF checker. It is
recorded under `device.development_target` in `config/sources.json`; the
complete-ROM fields remain `build_ready=false` and `lunch_target=null`.
See [current build progress](build-progress.md). Missing hardware/flash
prerequisites do not prevent safe local source generation and module checks.

The supplied Xiaomi.eu package is useful for identifying the actual hardware
and software dependencies. It is **not a valid signed image set**: the retained
AVB metadata disagrees with vendor_boot and the logical images. Local archive,
sparse, LP and EROFS checks passing does not override those failures. Keep it
as a modified research input, separate from the full-size but still-unverified
official-named China download.

The [later community release](community-bringup.md) makes a substantial Nezha
Camera port a concrete research lead. Its private device tree and official
`.307` firmware base do not supply reproducible Evolution X inputs for our
modified `.309` snapshot. The [public MiCode branch review](micode-popsicle-review.md)
establishes shared kernel/KMI/compiler-family evidence while preserving the
unresolved exact Nezha board and module requirements.
The subsequent [configuration audit](../kernel/xiaomi/nezha/config-audit/README.md)
finds all 812 explicit ACK base-defconfig requests in the captured GKI with
matching values. It keeps the vendor DDK dictionaries separate and generates
20 stock-derived preservation assertions. This advances the source baseline
without pretending those literal comparisons resolve the complete kernel build.

## Evidence to use, and what it does not establish

| Input | Verified observation | Remaining gate |
| --- | --- | --- |
| Live modified installation | Xiaomi/Nezha identity and CN hardware-country readback; Android 16; enforcing SELinux; 4 KiB pages | Physical variant details must not be inferred from the global-looking modified model string. Actual bootloader state remains unresolved. |
| Reconstructed package | Independent sparse implementations produce the same 15,300,820,992-byte super; all metadata copies agree; independent LP extraction hashes agree; all eight EROFS checks pass | These are local integrity and format results, not OEM authentication or a flash-safety result. |
| Dynamic layout | Eight logical partitions per slot, including mi_ext and both DLKM partitions; only A partitions have data in this package | Retain this exact evidence; do not adopt another phone's partition groups or use empty B records to remove A/B support. |
| Physical boot chain | Current by-name links include A/B boot, init_boot, vendor_boot, recovery, DTBO, vbmeta and vbmeta_system | All 30 follow-up sysfs size/start reads were denied. Image file sizes are not proof of physical partition capacity or offsets. |
| Kernel | Extracted boot kernel release matches the running 6.12.23 Android 16 GKI release | Module ABI, symbol CRCs, signatures, DT selection and source/licensing requirements are separate checks. A different vendor module release suffix alone does not prove incompatibility. |
| Camera APK | Package copy is byte-for-byte identical to the earlier live Camera APK | No Camera or Leica feature has been tested on Evolution X. |
| Vendor compatibility | Target-level and board API are `202504`; ODM first API is `36`. The built validator loads/merges vendor/ODM plus the observed active vendor APEX fragments successfully. | Full compatibility with the assembled Evolution framework, kernel and policy remains unverified. Static acceptance does not prove working services. |
| Vendor patch level | Supplied vendor build reports `2026-02-01`; system reports `2026-07-01` | Do not rewrite vendor security metadata to the system date. |

The [device baseline](device-baseline.md), [provided package](provided-firmware.md),
[source audit](device-research.md), [VINTF contract](vintf-contract.md),
[boot/DLKM contract](boot-contract.md), and [camera baseline](camera-baseline.md)
keep acquisition facts separate from integration hypotheses.
The later [actual VINTF validation](vintf-validation.md) and
[vendor APEX inspection](apex-dependencies.md) record the checks performed on
those inputs without replacing the original captures.

## Intended source boundaries

The authored device tree, stock-kernel wrapper and generated vendor/kernel
inputs are installed for framework checks. The table also identifies later
integration work; its remaining requirements do not prohibit that profile.

| Component | Responsibility | Complete integration requirements |
| --- | --- | --- |
| `device/xiaomi/nezha` | Exact product identity, physical layout, device overlays, init, recovery and device policy | Verified CN variant/partition contract, complete product makefile and pinned dependencies. Do not rename the public popsicle makefile and assume the remaining tree works. |
| `device/xiaomi/sm8850-common` | Only hardware/services demonstrably shared by the supported SM8850 devices | Review components individually against Nezha. The Myron reference's board geometry and AVB test settings are not acceptable defaults. |
| `kernel/xiaomi/nezha` with private `vendor/xiaomi/nezha-kernel` inputs | Kernel, DTB/DTBO, vendor ramdisk modules, vendor_dlkm and system_dlkm inputs | Exact hashes and provenance; module ABI and load-order checks; confirmed source and redistribution obligations. The private DTS roundtrip is a source-adaptation basis; it does not prove a rebuilt kernel boots. |
| `vendor/xiaomi/nezha` | Generated proprietary files and makefiles from a reviewed Nezha extraction list | Resolve every listed file to an exact source image/hash; preserve its partition and architecture; review ELF dependencies, VINTF, init, permissions and licenses. Do not copy another vendor tree or calibration data. |
| Separate Nezha Camera package | Xiaomi Camera, narrowly required framework/JNI/service dependencies and feature configuration | Basic Camera2/HAL operation first; permission/signature and linker-namespace review; distinct feature tests for Leica processing, lenses, video and accessories. |
| `vendor/lineage` | Evolution X product configuration from the selected manifest | The manifest uses this path for `Evolution-X/vendor_evolution`; do not inherit a guessed `vendor/evolution` product path. |

Do not add a local manifest until these dependencies have real reviewed
revisions. The workspace intentionally refuses unreviewed local manifests.
Changing that guard and activating a complete product must be a deliberate
change with tests, not a way to silence missing-product errors.

## Boot and kernel work before a complete ROM or device test

1. Obtain a complete matching unmodified China package and verify its internal
   AVB consistency. Record the actual source and signing evidence; embedded-key
   signature checks alone do not establish an OEM trust root. Preserve the
   modified package and its failed checks for comparison.
2. Establish physical partition capacities and the recovery/boot arrangement
   without inferring them from image lengths. The existing Android read-only
   interfaces denied the needed reads. Do not escalate privileges or reboot
   merely to fill this gap without a separate user instruction.
3. Reconcile boot/init_boot/vendor_boot/recovery headers, DT selection and
   rollback locations with that verified package. The supplied vendor ramdisk
   fstab lacks `avb`/`verify` mount flags; it is not an enforcing template to
   transplant into the new ROM.
4. Preserve the separation of vendor ramdisk, vendor_dlkm and system_dlkm module
   sets and their load/dependency/block lists. Validate each required module,
   its architecture, KMI/symbol CRCs and signature policy against the chosen
   kernel. The supplied sets contain distinct zram/zsmalloc variants and one
   shared imported-symbol CRC disagreement; preserve their selection and
   blocklist policy for review. Matching imported CRCs do not prove agreement
   with kernel exports. Do not turn off module/signature checks to fit inputs.
5. Preserve verified boot, rollback constraints, encrypted storage and enforcing
   SELinux in the new design. Vendor security policy and framework policy need
   compatible mappings; permissive policy and test AVB flags are not bring-up
   fixes.

No opaque installer or binary from the firmware is an extraction dependency.
Raw proprietary inputs, public-key inspection artifacts, private logs and
generated vendor files remain in ignored local storage until redistribution
rights and provenance are settled.

## Native-feature integration sequence

Start with storage, display/input, encrypted credentials, thermals/charging
protection, networking, audio and telephony. Each service needs its own exact
vendor/ODM binary, init declaration, VINTF interface, native library closure,
configuration and SELinux labels. VINTF and successful library parsing are
static checks; future hardware tests must separately establish behavior.

For Camera, the supplied files already establish several real boundaries:
algorithm libraries occur in **ODM**, compute/DSP dependencies in **vendor**,
and Camera framework/JNI components in **system_ext**. The app alone cannot
provide this stack. Resolve the complete `DT_NEEDED` closure and any dynamic
loads without flattening those partition boundaries. Check Java library
mappings against actual file locations, and review each privileged permission
and signing requirement. Optional `uses-native-library` declarations, including
MediaTek-named adapters in the shared APK, must not automatically become Nezha
vendor dependencies.

The [APK import review](camera-apk-integration.md) now supplies concrete signing,
4 KiB layout and manifest checks. The remaining build work includes a real
DEX class-loader provider and an explicit signing/privilege/packaging contract.
Neither a module-name alias nor a global relaxed library check supplies those
requirements. Keep the existing signature and raw captures unchanged while
reviewing any new derived input.

Keep IMS separate from basic modem/data operation, and fingerprint/trusted
services separate from ordinary touch/display operation. Preserve target-specific
charging protection, panel data and camera tuning. Do not collect device keys,
substitute another unit's calibration, change identity/attestation, or promise
payment/DRM eligibility.

The [native-feature matrix](native-features.md) specifies the eventual device
tests. It remains entirely untested on Evolution X. The first physical ROM
experiment requires a separate explicit authorization and recovery/data
preservation plan; completing this repository's tooling does not authorize it.

## Progressive validation

The platform checkpoint now has a successful Repo result, unchanged manifest/
Repo pins, 1,179 verified clean project checkouts, a resolved manifest with full
commit IDs, and verified content hashes for all 99 LFS files. The
[source record](../research/source-sync.json) documents that checkpoint.
Rosetta's standalone host-tool proofs, Nezha product configuration and the
successful first Android module build each have separate receipts. A source
kernel and complete ROM have not yet been built. [Build progress](build-progress.md)
records the current Camera compilation and actual read-only Ninja sandbox.

After dependency admission, check product inheritance, artifact paths, VINTF,
ELF dependencies, kernel module compatibility, SELinux and AVB before attempting
an image build. Record the exact manifest, product/kernel/vendor commits,
firmware and tool hashes with every result. Keep a compilation result separate
from boot, functional hardware and native-feature results.

The offline workspace suite remains `make test`. It uses no phone or network
and does not substitute for the later Android build, CTS/VTS, camera or device
acceptance tests.
