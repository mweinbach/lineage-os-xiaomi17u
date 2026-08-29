# Current Nezha workspace status

The selected target is **Evolution X Android 16 QPR2 `bka` for Xiaomi 17 Ultra
(`nezha`, SM8850 / `canoe`)**, with **TWRP `working76` as the default recovery**.
The ROM remains a `framework-checks` product, not a complete or flashable ROM.
The recovery has a separate successful device test using the installed stock
companion boot, kernel and vendor stack; it does not establish that it works
with newly built Evolution components or that Evolution X boots. This page
consolidates recorded evidence through August 29,
2026. It does not assert that a historical builder VM is still running.

The observed phone reports `nezha` and CN hardware-country information. Its
physical sales region is not independently established. During the authorized
August 29 tests, the bootloader positively reported `unlocked: yes`,
`secure: yes`, slot `a`, and 100 MiB recovery slots, despite Android properties
reporting a locked state. Use the [bootloader observations](../research/twrp-boot-attempts.json)
for that checkpoint; older unresolved-bootloader statements are historical.
Recheck the selected device before a future authorized operation.

## Build baseline and provenance

| Input | Selected baseline and evidence |
| --- | --- |
| Platform | Evolution `bka`, manifest `cc4ebb8db9750afba6049825127304b09327f7c1`, release configuration `bp4a`; [source selection](../config/sources.json) |
| Project revisions | [Resolved 1,179-project snapshot](../research/source-snapshots/evolution-bka-20260827.xml), SHA256 `a7b9b5aec7f07a4d351771dbb834f4c4561c26564c7292930409f3f5968edeac`; [source verification](../research/source-sync.json) |
| Product | Authored `device/xiaomi/nezha`, `lineage_nezha-bp4a-user` and `userdebug`; ARM64, 4 KiB kernel pages, shipping API 36, board API `202504`; [generation contract](../device/xiaomi/nezha/README.md) |
| Kernel and modules | Exact stock-prebuilt Nezha bundle, with its original Xiaomi.eu provenance retained; [kernel wrapper](../kernel/xiaomi/nezha/README.md), [factory comparison](../research/factory-input-reuse.json) |
| Vendor/ODM | Reviewed factory-named `OS3.0.309.0.WPACNXM` archive, SHA256 `d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`; [factory intake and validation](factory-firmware-validation.md) |
| Recovery | `working76`, SHA256 `a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e`; [working-image contract](../research/twrp-working-defaults.json), [build and handling instructions](../recovery/twrp-working/README.md) |

The manifest commit alone does not lock every project: its upstream entries
include branches. The [reviewed source-lock workflow](source-lock.md) now uses
the exact resolved snapshot for fresh initialization and sync. It never
converts an existing selector or resets local changes. `make source-check`
audits existing HEADs, remotes and worktree state against that lock. The earlier
August 28 audit matched all 1,179 HEADs/remotes, with 1,176 clean projects and
three expected patched projects; see [build progress](../research/build-progress.json).
The [August 29 integration audit](../research/workspace-integration.json) again
matched all 1,179 HEADs/remotes, with 1,175 clean projects. The fourth patched
project is now `build/make`, for the verified prebuilt-recovery consumer. The
audit deliberately returns status `2` for those local changes; it does not
reset them or describe the checkout as pristine. A source lock does not
include the remaining build inputs below.

Those local changes are part of the build inputs: the
[Evolution property patch](../patches/evolution/security-properties.json),
[SELinux enforcement patch](../patches/evolution/selinux-enforcement.json), and
[init property patch](../patches/evolution/init-boot-properties.json), together
with the [prebuilt-recovery consumer](../patches/evolution/prebuilt-recovery.json),
the [scoped helper capability](policy-source-integration.md), authored
device/kernel sources and hash-bound private vendor bundles. The helper patch
is now applied in the existing `system/sepolicy` project; it does not add a
fifth modified upstream project. The
snapshot alone does not include these changes. Factory archive origin and OEM
trust remain unauthenticated; passing internal AVB checks does not authenticate
the archive. Matching factory bytes do not relabel the older kernel bundle.

The verified local host route is Apple Container ARM64 plus Rosetta, with
`/work/evolution` on the persistent ext4 volume `evolution-nezha-work`.
Native Linux x86-64 is also supported by the workspace preflight. Recheck host,
disk, architecture, case sensitivity, source pins and volume ownership before
work; never attach the same volume to concurrent writer VMs. Preserve source,
output and cache. The [build-host guide](build-host.md) and
[container workflow](apple-container.md) distinguish component-build evidence
from a full build and require destination hash verification after transfers.

## What has actually passed

| Validation level | Result | Primary record |
| --- | --- | --- |
| Native source configuration and modules | User/userdebug product checks; ARM64 `libbase.so`; nine selected Camera dependencies, including four JARs with ODEX/VDEX; host VINTF and policy tools | [Build progress](../research/build-progress.json) |
| Native component builds and inspection | Boot, DTBO and both DLKM images in the recorded userdebug snapshot; factory-based user v8 init_boot, vendor_boot and DTBO preserve admitted DT/module/fstab inputs | [Boot/DLKM](../research/boot-dlkm-build.json), [factory boot](../research/factory-boot-build.json) |
| Native user v9 source policy | DSP membership integrated through Soong; both source-policy binaries have zero permissive domains | [DSP source build](../research/dsp-policy-build.json) |
| Strict policy prototype | Derived Binder correction plus two helper-permission removals compile as combined CIL with zero permissive domains; all 6,366 assertions retained | [Helper projection](../research/helper-policy-projection.json) |
| Native user v10 source and factory policy | The reviewed helper patch now runs through Android M4; a native genrule reproduces the Binder correction and the strict combined policy target builds successfully, including its user permissive-domain guard | [Source integration](../research/policy-source-integration.json) |
| Independent v10 analysis | Native combined binary matches the earlier prototype exactly; all 6,366 assertion statements remain, with only the intended 69 allow removals; three binaries have zero permissive domains | [Source integration](../research/policy-source-integration.json) |
| Static vendor VINTF | Vendor/ODM manifest load and merge, including captured active vendor APEX fragments | [VINTF validation](../research/vintf-validation.json) |
| Recovery device test | `working76` installed to recovery_a; matching readback; visible UI and fast touch confirmed by the user; root ADB, logs and automatic defaults verified | [Working recovery](../research/twrp-working-defaults.json) |
| Recovery reproduction and ROM build target | Two fresh Mac rebuilds match working76 byte for byte; Linux public-key staging/verification and two actual `recoveryimage` target runs pass with unchanged output bytes | [Workspace integration](../research/workspace-integration.json) |

TWRP preserves the working `fix22ZJ-touchfix18` executables, libraries, drivers,
firmware and policy. Exactly two text files change: early recovery startup sets
SELinux permissive, and theme vibration defaults are zero. Its AVB footer is
signed with the local development key, flags zero, recovery rollback index 1
and location 1. This is a verified repack of a prebuilt runtime, not a proven
source compilation or OEM signature. The exception is recovery-only; normal
Android enforcement and denial checks remain required. Saved TWRP settings can
override theme defaults. No Magisk integration is included.

## Gates before a complete ROM

- **Policy:** the v10 source/vendor-input path now passes the actual Android
  combined-policy build and independent analysis. Six of nine factory context
  and structural checks pass. The remaining failures are the missing manager
  classifications for `vendor_hal_atfwd_hwservice` and
  `vendor_hal_systemhelper_aidl_service`, plus missing `core_data_file_type`
  membership for `offlinelog_file` at `/data/local/log`. Restore the evidenced
  Xiaomi system_ext public declarations, roles and generated API mappings,
  together with the framework-owned offlinelog classification; review the
  effective permission changes before adopting them. Preserve the original
  system_ext/product ownership evidence instead of adding broad attributes.
  Full labeling needs the actual complete Evolution APK inventory; a missing
  artifact skip or API-202504 touch-only target is not a pass. The corrected
  policy is a non-installable validation output: retained vendor/ODM images
  still contain their original policy and need a reviewed image derivation.
- **Complete partition and OTA packaging:** retain `mi_ext`, both DLKM sets,
  the dedicated A/B recovery layout, factory encryption/AVB fstab declarations
  and measured Nezha budgets. `mi_ext` is not yet packaged. Target-files, OTA,
  super-image and flash admission remain false. Selecting TWRP does not prove
  an OTA contains, preserves or restores it correctly on either slot. The
  pinned target-files tool still requires a separately validated
  `recovery-two-step.img`, which the current prebuilt integration does not
  provide.
- **Signing and boot chain:** the inspected v8 generated boot components have
  AVB algorithm `NONE`, despite AVB being enabled in configuration. A complete
  signed chain, key availability, rollback compatibility and partition fit
  still need validation. The recovery bundle supplies its matching public key
  instead of using the generic engineering test key for that chain descriptor;
  this configuration is not proof of a completed, trusted vbmeta chain.
  Working recovery's development signature does not sign the ROM or authorize
  relocking. Its kernel-free image depends on the intact device boot chain and
  is not protection against bootloader damage.
- **Framework/vendor compatibility:** assemble Evolution framework matrices,
  device matrices, kernel requirements and active APEX inputs for full VINTF
  checks. The existing device-manifest pass and retained stock framework
  definition failures are not that complete comparison.
- **Runtime and stock features:** no Evolution boot or native feature is
  verified. Module stage loading/signature behavior, storage, telephony, audio,
  thermals, sensors, camera/Leica and accessories require separate tests. The
  Camera APK itself is not packaged; strict signing and uses-library integration
  remain open despite its nine dependencies building.
- **Recovery completeness:** encrypted `/data`, backup/restore coverage,
  additional reboot/Android round trips, A/B and OTA behavior, ADB host
  authentication and restoring recovery SELinux enforcement remain unverified.

Keep `SELINUX_IGNORE_NEVERALLOWS`, relaxed uses-library validation, VINTF
bypasses, AVB bypass flags and writable-source exceptions out of the ROM
workflow. A permissive recovery or successful component build does not waive
these gates. [Integration sequencing](nezha-integration.md) records the next
source work; [recovery handling](recovery-plan.md) records recovery boundaries.

## Current entry points and historical evidence

| Use now | Keep for diagnosis; do not treat as the current default |
| --- | --- |
| This status page and [Nezha integration](nezha-integration.md) | Detailed dated checkpoints in `docs/build-progress.md` and the individual component-build records |
| [Working TWRP instructions](../recovery/twrp-working/README.md) and [current recovery guide](twrp-bringup.md) | [Recovery history](twrp-bringup-history.md): earlier minimal builds, RAM-boot attempts and `provided75` before persistent defaults |
| [Native source-policy integration](policy-source-integration.md) and its [current record](../research/policy-source-integration.json) | v7/v8/v9 policy builds and the copied-CIL prototypes remain dated evidence; their original results are preserved |
| Current factory vendor/ODM input receipts | Modified Xiaomi.eu package, earlier candidates, outputs and failed AVB results with their original provenance |

Run `make test` before completing workspace changes. Generate into new ignored
candidate directories, validate configuration admission, preserve separate
user/userdebug output directories, and bind each build to its source snapshot,
patches, input receipts, tool hashes and artifact hashes. Offline tests neither
compile Android nor test a phone. Cleanup and local builds do not authorize
device changes; any future flash, reboot or restore needs its own explicit
user instruction and selected-device preflight.

The v10 native build completed at **2026-08-29 18:43:51 UTC**, with 255 Ninja
actions and observed read-only source / writable user output mounts. Independent
analysis completed at 19:02:14 UTC; the context phase completed at 19:04:29 UTC
with its three failures retained. The final audit again matched all 1,179
project revisions/origins, the same four intentionally patched projects, both
original factory images and working76 recovery. A temporary Container transport
stall was resolved without restarting the Nezha VM or shared service. No new
source sync, image adoption or device operation occurred.
