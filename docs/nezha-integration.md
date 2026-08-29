# Nezha integration plan and activation gates

This plan applies to the user's **Xiaomi 17 Ultra (`nezha`, SM8850 / `canoe`)**
and Evolution X **Android 16 QPR2 `bka`**. CN hardware-country information is
recorded, but the physical sales region is not independently established.
The [workspace status](workspace-status.md) is the current cross-project entry
point; dated build and device records remain evidence of their own checkpoints.
An authored `framework-checks` product is now registered in both `user` and `userdebug`
variants. Recorded builds include ARM64 `libbase.so`, all nine selected Camera
dependencies, host validation tools, boot/DTBO and both DLKM images. It is
recorded under `device.development_target` in `config/sources.json`; the
complete-ROM fields remain `build_ready=false` and `lunch_target=null`.
See [current build progress](build-progress.md). Missing hardware/flash
prerequisites do not prevent safe local source generation and module checks.

**TWRP `working76` is the selected default recovery.** Its installed image,
visible UI, responsive touch, root ADB and automatic recovery-only permissive
and zero-vibration defaults are verified in the
[working recovery record](../research/twrp-working-defaults.json). Follow the
[working-image build contract](../recovery/twrp-working/README.md) and
[recovery guide](twrp-bringup.md). This is a prebuilt-derived runtime; no new
TWRP runtime source compilation or complete ROM/OTA integration is implied.
The device test used the installed stock companion boot, kernel and vendor
stack, not newly built Evolution components. Normal Android keeps enforcing
SELinux and all existing admission gates.

The immediate milestone is a reproducible Evolution build that boots and
works on this device. Keep the pinned Evolution base, exact device/vendor
integration, and future platform features separate. Framework, system-service,
API, permission and SystemUI changes belong in a later explicit feature layer
once this baseline is established; public fork naming and branding remain
separate decisions.

The supplied Xiaomi.eu package is useful for identifying the actual hardware
and software dependencies. It is **not a valid signed image set**: the retained
AVB metadata disagrees with vendor_boot and the logical images. Local archive,
sparse, LP and EROFS checks passing does not override those failures. Keep it
as a modified research input. The separately supplied factory-named China TGZ
now passes [intake, selected AVB-chain and filesystem checks](factory-firmware-validation.md).
Its origin is still unverified. The current candidate explicitly uses its
vendor/ODM images, API facts, GPT budgets and enforcing fstab declarations,
while preserving the older input and build identities.

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
| Live modified installation | Xiaomi/Nezha identity and CN hardware-country readback; Android 16; enforcing SELinux in normal Android; 4 KiB pages | Physical variant details must not be inferred from the global-looking modified model string. August 29 bootloader checks positively reported unlocked and secure; recheck before a future authorized device operation. |
| Reconstructed package | Independent sparse implementations produce the same 15,300,820,992-byte super; all metadata copies agree; independent LP extraction hashes agree; all eight EROFS checks pass | These are local integrity and format results, not OEM authentication or a flash-safety result. |
| Dynamic layout | Eight logical partitions per slot, including mi_ext and both DLKM partitions; only A partitions have data in this package | Retain this exact evidence; do not adopt another phone's partition groups or use empty B records to remove A/B support. |
| Physical boot chain | Captured by-name links include A/B boot, init_boot, vendor_boot, recovery, DTBO, vbmeta and vbmeta_system. Later fastboot checks report 100 MiB recovery slots and a 96 MiB boot slot budget. | The earlier 30 Android sysfs reads were denied. Later measurements do not establish every partition's capacity or offset; image lengths and package GPT extents are not substitutes for live fit checks. |
| Kernel | Extracted boot kernel release matches the running 6.12.23 Android 16 GKI release; all 36,963 recorded distinct-module CRC expectations have matching captured providers | The global provider pool does not prove availability at each loading stage, provider selection, signatures, full ABI compatibility or source/licensing compliance. |
| Camera APK | Package copy is byte-for-byte identical to the earlier live Camera APK | No Camera or Leica feature has been tested on Evolution X. |
| Vendor compatibility | Target-level and board API are `202504`; ODM first API is `36`. The built validator loads/merges vendor/ODM plus the observed active vendor APEX fragments successfully. | Full compatibility with the assembled Evolution framework, kernel and policy remains unverified. Static acceptance does not prove working services. |
| Vendor patch level | Supplied vendor build reports `2026-02-01`; system reports `2026-07-01` | Do not rewrite vendor security metadata to the system date. |

The [device baseline](device-baseline.md), [provided package](provided-firmware.md),
[source audit](device-research.md), [VINTF contract](vintf-contract.md),
[boot/DLKM contract](boot-contract.md), and [camera baseline](camera-baseline.md)
keep acquisition facts separate from integration hypotheses.
The [factory boot contract](factory-boot-contract.md),
[factory input comparison](factory-input-reuse.md) and
[module provider audit](module-provider-audit.md) extend those observations
without rewriting the original receipts.
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
| Future platform feature patches | Deliberate changes to Android framework, services, APIs, permissions and SystemUI | Separate reviewed commits and upstream pins after the device baseline; no speculative feature or rebranding is admitted by bring-up. |

Do not add a local manifest until these dependencies have real reviewed
revisions. The workspace intentionally refuses unreviewed local manifests.
Changing that guard and activating a complete product must be a deliberate
change with tests, not a way to silence missing-product errors.

## Boot and kernel work before a complete ROM or device test

1. Preserve the complete factory input and its passing selected AVB chain,
   while resolving source authentication separately. Embedded-key signature
   checks alone do not establish an OEM trust root. Keep the modified package
   and its failed checks for comparison.
2. Use the [later bootloader observations](../research/twrp-boot-attempts.json)
   and working recovery test for the verified recovery/boot arrangement.
   Revalidate the selected phone and relevant partition capacities before any
   future authorized flash; do not infer missing capacities or offsets from
   image lengths. The earlier Android sysfs denials remain historical evidence,
   not a reason to discard the successful fastboot measurements. Do not reboot
   or escalate privileges merely to fill remaining gaps without instruction.
3. Validate built boot/init_boot/vendor_boot components against the captured
   headers, DT selection, rollback locations and package GPT extents. The
   Xiaomi.eu ramdisk fstab lacks verification flags; the current generated
   factory profile instead retains all observed logical/boot AVB declarations,
   GSI key references and encryption fields. Referenced-key availability and
   complete signed-image integration remain separate requirements.
4. Preserve the separation of vendor ramdisk, vendor_dlkm and system_dlkm module
   sets and their load/dependency/block lists. Validate each required module,
   its architecture, KMI/symbol CRCs and signature policy against the chosen
   kernel. The supplied sets contain distinct zram/zsmalloc variants and one
   shared imported-symbol CRC disagreement; preserve their selection and
   blocklist policy for review. The later export audit now supplies matching
   CRC candidates, but stage availability and actual loading remain unresolved.
   Do not turn off module/signature checks to fit inputs.
5. Preserve verified boot, rollback constraints, encrypted storage and enforcing
   SELinux for normal Android. Recovery-only permissive mode is the explicitly
   authorized bring-up exception, with enforcement a later recovery milestone.
   The [native v10 policy integration](policy-source-integration.md) applies
   the helper correction through Android M4 and derives the vendor Binder
   correction in the actual build graph. Strict combined compilation and
   independent analysis pass; all 6,366 assertion statements remain and three
   binaries have zero permissive domains at that checkpoint. The later
   [v11b source integration](oem-policy-integration.md) restores the two Xiaomi
   system_ext service declarations, roles and generated 202504 mappings, plus
   the framework-owned offlinelog classification. Its native ownership guard,
   strict compiler and all nine factory checks pass. Independent v11 analysis
   verifies all 6,366 assertions and their reviewed concrete coverage, exactly
   five added and 47 removed permissions, and zero permissive domains in three
   binaries. These checks include roles, named/anonymous attribute closures,
   public exports and generated mappings, not assertion text alone.
   Complete Treble labeling also remains unverified. The derived policy is
   still a non-installable validation target; original vendor/ODM images are
   intact. Complete metadata evidence and an exact five-file derivation are
   required before adopting policy into those images.
   Keep their eventual image derivation separate from the preserved
   [earlier copied-CIL prototype](helper-policy-projection.md).

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
4 KiB layout and manifest checks. A tested [DEX class-loader provider patch](dex-import-uses-library.md)
is available, but its guest and Make-app consumer integration remain pending,
along with an explicit signing/privilege/packaging contract.
The [runtime-input follow-up](camera-runtime-inputs.md) now stages the exact
four JAR names and XML registrations without a module-name alias; its actual
guest provider patch and native rebuild remain separate work.
Neither a module-name alias nor a global relaxed library check supplies those
requirements. Keep the existing signature and raw captures unchanged while
reviewing any new derived input.

The [selected Sigma/QCC provider bundle](framework-providers.md) and its
[bounded policy contract](../config/nezha-framework-provider-policy.json) are
authored inputs awaiting native adoption. Preserve their original init and
VINTF declarations, require real ELF/linker closure, and do not infer runtime
availability from the factory matrix or a compatibility CLI pass. Likewise,
the optional [four-property policy](../config/nezha-oem-properties.json) has
its own source/context and permission budget; it is not included in the v11b
three-type result or evidence that all OEM services work.

The [mi_ext prebuilt path](mi-ext-inputs.md) and
[A/B-only recovery correction](recovery-packaging.md) are now reviewed source
work with host checks. They have not yet been adopted into the v11b guest
source or proven by native target-files/super/OTA artifacts. Keep working76
unchanged and do not turn it into a fake non-A/B boot recovery. The
[AVB verifier](avb-image-set.md) checks separate public keys for each signed
role; it does not supply the missing signed artifacts or device rollback facts.

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

The recorded platform checkpoint has a successful Repo result, unchanged manifest/
Repo pins, 1,179 verified clean project checkouts, a resolved manifest with full
commit IDs, and verified content hashes for all 99 LFS files. The
[source record](../research/source-sync.json) documents that checkpoint.
Rosetta's standalone host-tool proofs, Nezha product configuration and the
successful first Android module build each have separate receipts. A source
kernel and complete ROM have not yet been built. [Build progress](build-progress.md)
records the completed Camera dependency compilation and actual read-only Ninja
sandbox. Its later source audit binds all 1,179 project revisions while allowing
only the three recorded source-patch projects; it does not reclassify historical
checkouts as unmodified or establish current VM state.

The [August 29 workspace integration](../research/workspace-integration.json)
adds the fourth reviewed patch project, `build/make`, for TWRP. All 1,179 base
revisions and remotes still match. The selected recovery bundle carries the
matching public chain key, while its private signing key remains outside the
VM. These changes do not admit a full target-files/OTA build or alter the
earlier component-build and policy results.

The [later v11 preflight and build](../research/oem-policy-integration.json)
again preserve those 1,179 upstream revisions and four patched projects.
Authored follow-up patches require their own installed-source audit. Its native
policy retry and independent analysis establish the restored three-type slice
and all nine context checks. Full Treble labeling, framework image/APEX closure,
policy-image adoption, target-files and the signed boot chain remain separate
milestones. No phone was accessed for this integration.

Continue checking product inheritance, artifact paths, VINTF, ELF dependencies,
kernel modules, SELinux and AVB as the partial image builds expand. Record the
exact manifest, product/kernel/vendor commits,
firmware and tool hashes with every result. Keep a compilation result separate
from boot, functional hardware and native-feature results.

The offline workspace suite remains `make test`. It uses no phone or network
and does not substitute for the later Android build, CTS/VTS, camera or device
acceptance tests.
