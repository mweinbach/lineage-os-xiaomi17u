# Nezha TWRP stage 0

This is an **experimental, compile-only recovery target**, not an installable
release or a demonstrated rescue path. Its first purpose is to compile and
inspect a separate recovery ramdisk while keeping the Evolution X source and
output intact. No phone command, boot, flash, format, unlock or slot change is
authorized by this target.

Copy this directory to `device/xiaomi/nezha` only inside the isolated TWRP
source tree. The product is `twrp_nezha`; its registered lunch choices are
`twrp_nezha-bp2a-userdebug` and `twrp_nezha-bp2a-user`. The build target is
`recoveryimage`. The workspace runner must check the host, disk, filesystem,
resolved manifest and source patch receipts first. Do not repurpose the
existing Evolution product or use `recoveryimage-nodeps`.

The pinned GUI source reads `OUT` from the build environment to place its
theme under the selected product's `recovery/root/twres`. The runner must
provide the same absolute product-output directory that `lunch` exports as
`OUT` and `ANDROID_PRODUCT_OUT`; setting `OUT_DIR` alone is insufficient. No
checkout-specific output path or `/recovery` directory belongs in this target.

The first graph exposed orphan subsystem consumers whose parent definitions
are omitted by the minimal manifest. This recovery product uses the supported
`PRODUCT_SOURCE_ROOT_DIRS` control to exclude these bounded source scopes:

| Excluded scope | Why it is outside this initial product |
| --- | --- |
| `tools/loganalysis/`, `tools/tradefederation/contrib/`, `test/suite_harness/` | Host test and log-analysis tooling without the omitted Tradefed definitions |
| `hardware/google/aemu/` | Emulator graphics host tooling without its gfxstream defaults |
| `packages/modules/AdServices/` | Advertising services and their test collectors |
| `system/secretkeeper/` | Secretkeeper consumers; this recovery does not enable decryption |
| `hardware/interfaces/neuralnetworks/utils/` | Neural-network adapters outside recovery functionality |
| `hardware/interfaces/virtualization/capabilities_service/vts/` | Virtualization capability VTS tests |

The second graph reached a further set of absent defaults. Its additional
exclusions are limited to the following consumers, after checking their
declared module names against recovery/core/ADB/vold and the protected build,
SELinux, VINTF and AVB roots:

| Additional excluded scope | Missing parent and scope limit |
| --- | --- |
| Seven individual `cts/hostsidetests/securitybulletin/securityPatch/CVE-*/` directories | `CVE-2019-1988`, `CVE-2023-21085`, `CVE-2023-40114`, `CVE-2023-4863`, `CVE-2024-43091`, `CVE-2024-43097`, `CVE-2024-43767`; their Skia/STS test defaults are absent. Other security-bulletin tests remain included. |
| `cts/tests/tests/car/`, `cts/tests/tests/car_permission_tests/` | Automotive framework CTS tests requiring the omitted car framework; other CTS tests remain included. |
| `hardware/interfaces/automotive/remoteaccess/hal/default/` | Default automotive remote-access service, helper library and its tests requiring vehicle-HAL client defaults; the AIDL interface is retained. |
| `hardware/interfaces/security/see/hwcrypto/aidl/vts/functional/` | HWCrypto functional VTS tests requiring omitted Rust test defaults; the production security AIDL interface is retained. |
| `system/chre/` | Context Hub Runtime Environment, its HAL/client libraries and tests requiring Pigweed RPC support. This is an excluded runtime subsystem, not merely a test-generator removal. |

Graph 2 also excluded `packages/modules/Connectivity/tests/common/` because
its coverage test required the absent `libnetworkstackutilsjni_deps` provider.
Graph 3 reported 19 missing-default errors because this same `Android.bp`
defines shared defaults used by retained consumers, including BPF tests.
That exclusion is now removed,
leaving 20 source scopes excluded. File-prefix selection cannot remove only
the coverage test while preserving defaults in the same file.

The corresponding source restoration uses the genuine Android 16 r1
NetworkStack project at `f9da1fc7154ea007aa835f88e8070c6ac46d54e9`, including
`tests/unit/Android.bp`, where `libnetworkstackutilsjni_deps` is defined. It
uses no substitute defaults, copied module stubs, or missing-dependency
allowlists. Source-sync and subsequent graph receipts must establish the
restoration and its dependencies; these target changes alone are not proof
of a successful graph or image. Runtime networking remains disabled.

These are build-graph scope checks, not executions or passing results for the
excluded tests. The bounded reference scan found no direct recovery consumer
of the excluded module names; it is not proof of complete transitive closure.
If retained modules need one of these providers, the next graph must fail and
the appropriate source must be restored rather than hiding that dependency.

This includes non-test code and is a product-scope decision, not a general
claim that all removed modules are optional for Android. Unrelated Android
platform and test modules are excluded; the table identifies the test scopes.
Blueprint
`dcb14f2e146f40cf1f212efb220e9aa1f3cfc280` applies literal prefix matching,
with the longest matching prefix first and unmatched paths allowed. Each
negative path ends in `/` so it does not hide similarly named siblings.
Dependencies on skipped modules still fail; if recovery requires one of these
modules, restore its reviewed parent sources and revise the scope rather than
suppressing the error. Recovery, fs_mgr, SELinux policy and tests, AVB, storage,
VINTF and device assertions remain in the graph. Connectivity's BPF headers
are retained because recovery's `libsysutils` needs `bpf_headers`; missing BPF
providers must be restored from the pinned Android source, not hidden by a cut.
The top-level product also calls `enforce-product-packages-exist` without an
allowlist. Required-module bypass flags and ASAN's implicit exemption from
that check are rejected by the board config.

The source contract is the experimental
[TWRP-Test Android 16 manifest](https://github.com/TWRP-Test/platform_manifest_twrp_aosp/tree/d2188a9345857fb078c391e8cb3e259a21e941e5),
not a claim of official TeamWin device support. The directly inspected source
pins for the target's build controls are:

| Source | Commit | Relevant files |
| --- | --- | --- |
| `TWRP-Test/android_bootable_recovery` | `b70f8e998b302381ecefc6e7f46df1614bd61afc` | `Android.bp`, `twrp_recovery_defaults.go`, `partitionmanager.cpp`, `etc/init.rc` |
| `TWRP-Test/android_build` | `3b5b2b43b8e2200ef92b7b814a84c8dde8b74121` | `core/board_config.mk`, `core/Makefile`, `target/product/generic_ramdisk.mk` |
| `TWRP-Test/android_vendor_twrp` | `b53296dfc420ce65fffe712de380d5abf6c4c2f1` | `config/BoardConfigSoong.mk`, `config/common.mk` |
| `TWRP-Test/android_system_core` | `9292e0ddea6c1e8ff95abc8d3fedd6dd0c722f31` | `init/first_stage_init.cpp` |

The controller must resolve and record the full transitive manifest and apply
its reviewed source patch queue. A product makefile alone cannot repair the
upstream recovery's authentication and permissive-policy defaults. The final
compiled policy must be examined without filtering permissive domains, and
the built properties and adbd must retain authentication. This target refuses
`eng`, neverallow bypasses, missing dependencies, duplicate rules/properties,
ELF-copy bypasses and unreviewed plugin exceptions. The local policy adds a
neverallow for the recovery domain changing SELinux enforcement. Source-tree
writes are explicitly disabled; a conflicting command-line override fails.
This source-write sandbox is separate from device SELinux enforcement.

The pinned init source compiles `ALLOW_PERMISSIVE_SELINUX=0` for `user`, while
debuggable builds change it to 1 and can accept `androidboot.selinux=permissive`
from kernel command line or bootconfig. There is no reviewed device make flag
here that overrides this init behavior. The target does not inject a fake
enforcement property or claim that selecting `userdebug` compels enforcement;
its compile-only status and runtime admission checks still apply.

The separate recovery layout comes from the supplied Nezha China package
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`:
boot header v4, no kernel or DTB in recovery, an empty recovery-header command
line, and a legacy LZ4 ramdisk. Both recovery slots occupy 104,857,600 bytes in
the checked package GPT. That package limit is enforced during assembly;
physical phone geometry remains unverified. `PRODUCT_BUILD_RECOVERY_IMAGE`
is explicitly true because the build system otherwise suppresses recovery
when `TARGET_NO_KERNEL` is true. Other image products are disabled.

AVB artifact creation and image-size checks stay enabled. The image uses the
public AOSP test key under `external/avb/test/data/`, with recovery rollback
location 1 and index 1 retained from the package. **A valid signature under
that public test key is not authorization to boot it, OEM authentication, or
protection from rollback-counter changes.** No signing key is stored here, no
phone trust root is changed, and no bootloader acceptance path has been tested.
The source's actual Android version and patch level are kept; OEM fingerprints
and future security dates are not fabricated.

The matched `boot`, `init_boot`, `vendor_boot` and bootloader remain external
runtime dependencies. The stock recovery contains no `.ko` files. Its vendor
ramdisk provides 430 modules under `/lib/modules`, with 435 ordered recovery
load-list rows and 424 unique names; the reviewed hard closure contains 426
modules. The pinned first-stage init selects `modules.load.recovery` in
recovery mode and falls back to `modules.load` only when the recovery list
cannot be stat'ed. This target does not duplicate that loader or ship a kernel,
module, stock executable or firmware. Module signatures, successful loading
and the actual bootloader ramdisk composition still require validation.

Display and touch are separate unresolved milestones. The captured stock
kernel enables DRM without framebuffer emulation. Nezha panel and touch DTBO
entries include 1200 by 2608 geometry, but this target only selects the generic
portrait theme; it does not assert a working renderer, pixel format or touch
mapping. The Synaptics and Xiaomi touch modules are in `vendor_dlkm`, outside
the vendor-ramdisk module set, and need matching `/odm` firmware. Those inputs
are deliberately absent from this first compile. Do not count a successful
build as a working display or touch test.

The only authored USB glue selects configfs and forwards the bootloader's
`ro.boot.usbcontroller`. It does not guess a controller, switch a hardware
mode, adopt stock keys or add a second module loader. The recovery properties
require `ro.secure=1` and `ro.adb.secure=1`. No ADB public key is bundled, so
failure to authenticate must remain a failure; a separately reviewed private
public-key input and runtime test are needed before relying on ADB. Logd and
logcat are requested for diagnostics, but collecting those logs is not yet a
verified device capability.

`recovery.fstab` has no active rows. Additional vendor-fstab discovery, APEX
loading, crypto, MTP, USB mass storage, fastbootd, partition tools and recovery
repacking are not enabled by this target. The pinned build's default
`AB_OTA_UPDATER=true` is retained for Nezha's actual A/B slot/update model;
its presence does not establish safe slot or snapshot behavior. Stock normal
userdata is F2FS with
`wrappedkey_v0` for file and metadata encryption; neither the older ext4/ICE
recovery fstab nor an invented decryption configuration is used here.

**An empty fstab does not make TWRP read-only.** The pinned recovery still has
startup paths that clear bootloader messages, run scripts and pending
OpenRecoveryScript commands, write settings/logs and disable stock recovery
replacement. Its source also includes installer, sideload and formatting
code. The flags above do not remove or prove safe all those paths. Before any
separately authorized boot test, review and constrain startup/actions, inspect
the ramdisk and compiled policy, verify authentication and the boot chain, and
establish a stock-return procedure. Data decryption, metadata access, backups,
restores, snapshots and slot control are not implemented or validated here.

The workspace's standard-library tests inspect the actual target files and
their separation, image layout, policy, authentication and storage invariants.
They do not run Android make/Soong, compile SELinux, load a module, or substitute
for the separate recovery build and authorized hardware tests.
