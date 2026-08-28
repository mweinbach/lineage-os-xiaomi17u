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
| `hardware/google/aemu/` | Emulator graphics host tooling without its gfxstream defaults |
| `packages/modules/AdServices/` | Advertising services and their test collectors |
| `hardware/interfaces/virtualization/capabilities_service/vts/` | Virtualization capability VTS tests |

The initial `system/secretkeeper/` exclusion was later removed when restored
virtualization sources introduced real consumers, as described under Graph 6
below. Disabling recovery decryption does not make a consumed provider optional.

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
| `system/chre/` (initially excluded, now restored) | Context Hub Runtime Environment, its HAL/client libraries and tests originally lacked Pigweed RPC support. Graph 22 proved its shared flags have a retained framework consumer; the full original source scope is restored with genuine dependencies. |

Graph 2 also excluded `packages/modules/Connectivity/tests/common/` because
its coverage test required the absent `libnetworkstackutilsjni_deps` provider.
Graph 3 reported 19 missing-default errors because this same `Android.bp`
defines shared defaults used by retained consumers, including BPF tests.
That exclusion was removed, leaving 20 source scopes at that stage.
File-prefix selection cannot remove only
the coverage test while preserving defaults in the same file.

The corresponding source restoration uses the genuine Android 16 r1
NetworkStack project at `f9da1fc7154ea007aa835f88e8070c6ac46d54e9`, including
`tests/unit/Android.bp`, where `libnetworkstackutilsjni_deps` is defined. It
uses no substitute defaults, copied module stubs, or missing-dependency
allowlists. Source-sync and subsequent graph receipts must establish the
restoration and its dependencies; these target changes alone are not proof
of a successful graph or image. Runtime networking remains disabled.

Graph 4 adds five bounded exclusions for further consumers outside recovery:

| Additional excluded scope | Scope limit |
| --- | --- |
| `hardware/interfaces/automotive/vehicle/vts/` | Automotive vehicle VTS tests requiring the omitted vehicle-HAL client. |
| `hardware/interfaces/automotive/audiocontrol/aidl/default/` | The automotive audio-control example service and helpers requiring car power-policy support. |
| `hardware/interfaces/automotive/vehicle/aidl/impl/3/`, `hardware/interfaces/automotive/vehicle/aidl/impl/current/` | Vehicle HAL implementations requiring automotive large-parcelable defaults; the production AIDL interfaces remain included. |
| `hardware/interfaces/security/secretkeeper/aidl/vts/` | Secretkeeper VTS tests, test support and diagnostic CLI requiring omitted Rust test defaults; the production Secretkeeper AIDL interface remains included. |

No declared module from these five scopes was directly referenced in the
bounded recovery/core/ADB/vold and protected validation source scan. This
does not establish transitive closure; a dependency that the next graph finds
must still be restored.

The initial neural-network review found that restoring only the project's
root and `common/types` files could not supply a coherent provider set.
`neuralnetworks_types_cl` needs defaults in `common/Android.bp`, which also
introduces runtime, shim and external ML dependencies. The original temporary
utility exclusions avoided those absent providers without substituting empty
defaults. The complete dependency sources are now required by the shared
text-classifier hash provider reached through graph 18's Bluetooth protobuf
restoration, so those utility exclusions are removed.

Removing six negative prefixes restores nine original Blueprint files at
frozen hardware-interface commit `3e2bcbf17426a5783f034c8b0bb0d26743b39892`:
the five `hardware/interfaces/neuralnetworks/{1.0,1.1,1.2,1.3,aidl}/utils/`
files and the canonical `utils/{common,service,adapter/aidl,adapter/hidl}/`
files. They retain eighteen modules, including their original utility tests,
defaults and metadata. Real `neuralnetworks_types` and utility defaults come
from the complete pinned NeuralNetworks project, with its external dependencies.
This source restoration does not install or validate NNAPI execution in
recovery. HIDL/AIDL interface definitions remain included; the unrelated
`hardware/interfaces/neuralnetworks/aidl/vts/functional/` test leaf remains
excluded and has no new incoming dependency in the reviewed NN declarations.

Graph 17 failed at `CtsNNAPITestCases` because `CtsNNAPITests_static` and
`libneuralnetworks` were absent at that point. The recovery profile still
excludes only `cts/tests/tests/neuralnetworks/`: its five original Blueprint
files define four tests and one JNI test library. They retain their original
source bytes and global Apache package metadata in the checkout. A complete
text scan across 10,907 BP, 1,701 Make and 13,441 Go files found no outside
references to those five module names; the single Java-to-JNI edge stays
within the omitted leaf. The child benchmark, Java and TensorFlow delegate
tests are projected follow-ups from that source review, not additional
observed graph failures. Other CTS tests, NNAPI HIDL/AIDL interfaces and the
SELinux service-fuzzer registry remain selected and unchanged. This scope
does not validate NNAPI support or substitute historical VNDK libraries for
the missing runtime.

Tradefed takes the provider-restoration path. Its first-graph exclusions for
`tools/loganalysis/`, `tools/tradefederation/contrib/` and `test/suite_harness/`
are removed. The original `platform_testing/libraries/tradefed-error-prone/`
subtree supplies both required quality-check defaults. A negative
`platform_testing/` prefix and the longer positive provider prefix retain
that subtree while excluding the unrelated platform-test aggregate in the
root `Android.bp`. The provider has its own package declaration using the
global Apache license; no copied defaults or source edits are needed.
Native-bridge support remains included as a complete original source project
because the retained binary-translation modules consume its defaults and
filegroups. Its bytes and revision remain the source runner's responsibility.

The subsequent defaults scan found one unrelated scene-transition test needing
`MotionTestDefaults`. The file-prefix exclusion
`-frameworks/base/packages/SystemUI/compose/scene/tests/Android.bp` omits only
the file declaring `PlatformComposeSceneTransitionLayoutTests`, which has no
external module references in the bounded scan. The directory is not excluded:
`tests/utils/Android.bp` supplies a helper consumed by retained SystemUI,
SettingsLib and screenshot tests. Those consumers and their dependency checks
remain included. The actual Skia, HWUI and RenderEngine sources are not cut to
work around missing graphics providers.

Graph 5 reached one remaining vehicle-default consumer in
`hardware/interfaces/automotive/vehicle/aidl/aidl_test/`. That scope declares
only the AIDL/HIDL compatibility test and the C++ and Java property-annotation
tests. Their implementation providers were already outside the recovery
product, and the bounded scan found no external consumers or shared helper
modules in this scope. The test directory is excluded; the production vehicle
AIDL definitions and API data remain included.

A static follow-up checked the remaining references to the recently excluded
module names. The only further active reference found was the vehicle header
`IVehicleHardware`, used by `DefaultBroadcastRadioHalTestCase` in
`hardware/interfaces/broadcastradio/aidl/default/test/`. That directory declares
only this test and has no external consumers or shared helper modules in the
bounded scan. It is excluded while the production radio service and AIDL
interface remain included. No additional broad source exclusions were added.

Graph 6 passed the literal-default resolution stage and reached the SELinux
service-fuzzer binding validator. The missing fuzzer providers are restored
from their genuine source projects; the validator and registry remain intact.
The wificond provider needs `libwifi-system-iface` and its test-support library.
The original Wi-Fi project at `1cab31f96d1f903e190708c1ce665520a4a89d10` supplies
both in the self-contained `frameworks/opt/net/wifi/libwifi_system_iface/`
subtree. The negative project prefix and longer positive provider prefix retain
that subtree, including its test support, while leaving unrelated Wi-Fi tracker
and framework code outside this product. The leaf has its own package using the
global Apache license. This selection does not enable TWRP networking.

The complete AVF project at `c984fc337c11ca5edc03ccf02037b2455dd8fcaf` supplies
the missing virtualization fuzzer and `avf_build_flags_rust`. Its
`guest/microdroid_manager/Android.bp` also consumes `libsecretkeeper_client`
and `libsecretkeeper_comm_nostd`; the client needs the original Secretkeeper
core library as well. The former `system/secretkeeper/` exclusion is therefore
removed to retain those real providers. The separately scoped Secretkeeper
hardware VTS exclusion is unchanged. The retained Secretkeeper tests also need
`rdroidtest.defaults`, so the original `platform_testing/libraries/rdroidtest/`
provider subtree is re-included, with its libraries and tests unchanged. Its
original module and licensing declarations are retained; no substitute Rust
defaults are created. Further Rust dependencies must resolve through the actual
graph; none is stubbed or silently ignored. These source
restorations do not add recovery packages, enable TWRP decryption, or establish
a working virtual machine or encrypted-data path on the phone.

Graph 7 exposed an upstream configuration type mismatch: the vendor exporter
registers `include_se_omapi` unconditionally but marks it as a boolean only
when crypto is enabled. With crypto off, recovery's boolean `select` branches
receive an untyped string. This target calls the original
`soong_config_set_bool` helper with `false` after the vendor exporter, keeping
OMAPI disabled while supplying the required boolean type. No source branch
or type check is removed, and no crypto feature is enabled to avoid the error.

Graph 9 reached `prebuilt_core-lambda-stubs` through SDK distribution packaging
in `development/build/Android.bp`. The only Blueprint file in that directory
defines five SDK archive/helper modules: `build-tools`, `platform-tools`,
`build-tools_renderscript_includes`, `build-tools_core-lambda-stubs-device` and
`build-tools_core-lambda-stubs`. An independent scan of 10,657 discovered
Blueprint files found no external references to those five modules. This
recovery-only profile excludes `development/build/`; it does not package SDK
distributions. The actual ADB, fastboot, mkbootimg and apksigner providers remain
included, along with AVB, SELinux, fuzzer-binding and VINTF validation. Missing
libraries consumed by retained tools still require their genuine providers.

The source batch prepared for Graph 10 restores `system/media` at the genuine
Android 16 r1 commit `f01e84b958fb6a887dc0e74e4b5ebd159f03860a`. Its
`system/media/audio_utils/tests/Android.bp` adds audio tests requiring the
absent TensorFlow and NNAPI runtimes. That single file declares 39 tests,
one local test default and six test tools, with no shared-library providers.
The bounded scan found no references to those 46 module names from 10,657
existing Blueprint files or the other 21 media Blueprint files. Only this
test file is excluded; production audio and vibrator code, benchmarks,
fuzzers, other test files and security validators remain included. Required
production dependencies still need genuine providers, not substitutes.

Graph 11 identified retained consumers of `compatibility-common-util-lib` and
`platform-test-annotations`. The original
`platform_testing/libraries/compatibility-common-util/` and
`platform_testing/libraries/annotations/` subtrees are re-included from the
pinned Android 16 r1 project at `7b48625b052b94b1ef24573ef5e8ffa5e2ea9783`.
Their three Blueprint files retain the seven original library, wrapper and
test modules, including compatibility's child test. Each file declares the
global Apache license, and the referenced Java libraries, test defaults and
team metadata have real providers in included source paths. The large
`platform_testing/Android.bp` test aggregate remains excluded. No module,
license declaration or dependency check is replaced.

The Nezha native recovery profile explicitly sets the boolean
`nezha_twrp.native_recovery_only` after the vendor configuration. The original
source patches gate 19 specific Robolectric test and helper
modules through their `enabled` selections, with `true: false` and
`default: unset`. Other products leave the switch unset and retain their
original enabled behavior. Production SystemUI and Bluetooth modules, package
metadata, defaults and helpers needed by retained consumers remain in the
source graph. SELinux policy and fuzzer checks, signature verification, ELF
checks and dependency validation remain enabled. This native profile does not
run those JVM UI tests and is not a full Android test profile.

The source projection after Graph 13 found retained consumers of `flag-junit`,
`flag-junit-host` and `libflagtest`. It did not identify an observed Graph 13
error. The original `platform_testing/libraries/flag-helpers/junit/` and
`platform_testing/libraries/flag-helpers/libflagtest/` leaves are re-included.
Their three Blueprint files retain all 12 module definitions, including local
tests, native flag declarations and defaults, with their original license and
team metadata. The bounded check found existing selected dependency providers,
including the genuine SDK generator for
`framework-configinfrastructure.stubs.module_lib`; no new project is needed
for these leaves. Platform runner, collector and rule subtrees remain excluded.
The next real build must still validate variants and generated artifacts.

Graph 22 found that the retained `tradefed-test-framework` needs the original
`test-composers` library. The positive
`platform_testing/libraries/health/composers/host/` prefix restores its two
Blueprint files from pinned project `7b48625b052b94b1ef24573ef5e8ffa5e2ea9783`.
All three original modules remain: `test-composers`, `test-composers-tests`
and `HostTestComposersTests`, together with their source, license and team
metadata. Their immediate providers already exist in the selected sources.
The parent health-test aggregate and the device-composer sibling remain
excluded. This restores build declarations; it does not claim those tests ran
or that a recovery image compiled.

Graph 22 also found that the retained framework's
`android.chre.flags-aconfig-java` needs `chre_flags`. The original CHRE source
at `39be9f48eebb530d56972d967c5ee4d99b2ac3a5` is restored in full: 22 Blueprint files
and 99 named modules, including its runtime libraries, tests, generators and
metadata. The 18 original flags remain in `system/chre/chre_flags.aconfig`,
with their original package and system container. No flag definitions are
copied into the device tree or substituted with a new provider.

Pinned Pigweed and Emboss projects provide the original RPC and code-generation
dependencies. Their complete build definitions remain selected. Existing AIDL
interfaces generate the required versioned bindings; historical VNDK name
matches are not used as substitutes. This restores a shared build dependency,
not Context Hub support or an installed recovery service. Compilation and
generated-output checks remain for the next actual build.

Graph 23 identified the retained framework dependency on
`sdk_sandbox_exported_flags_lib`. Two narrow positive source prefixes restore
`packages/modules/AdServices/sdksandbox/Android.bp` and its `flags/` leaf from
the original project at `a6ee8245f54f1719a899809cc8727f7fcce9ca35`. The parent
file keeps the original package metadata, global Apache license,
`trendy_team_rubidium_sdk_runtime` team and `sdksandbox-java-defaults`; the
leaf keeps the flag declaration and both Java flag libraries. Its 10 original
flags, exported mode, visibility, API settings and container are unchanged.
Other AdServices runtime and test source files remain excluded. This changes
source selection only, without adding an SDK sandbox service to recovery or
replacing original declarations with device-local copies.

The native source projection also found three retained Wi-Fi service modules
and one test consuming `libwifi-hal`. The positive
`frameworks/opt/net/wifi/libwifi_hal/` prefix restores one original Blueprint
and its nine named declarations from pinned project
`1cab31f96d1f903e190708c1ce665520a4a89d10`. All eight external dependencies
selected by the current empty Wi-Fi configuration have existing providers.
No chipset, driver path or vendor HAL is selected by this target. The unchanged
upstream configuration uses `libwifi-hal-fallback`; this is source dependency
restoration, not a Xiaomi Wi-Fi implementation or a hardware-support claim.
The broader Wi-Fi source filter and the interface-library leaf remain in place,
and recovery networking stays disabled. This finding was not a graph 22 error;
the next evaluated graph must still validate the restored declarations.

Graph 14 reported seven missing dependencies in the two
`test/robolectric-extensions` Blueprint files. The follow-up projection found
four more files containing only related test support: Onboarding's
`contracts/testing/Android.bp` and `testing/Android.bp`, plus SettingsLib's
`tests/robotests/Android.bp` and `tests/robotests/fragment/Android.bp`.
The combined review checked module, shell, manifest, generator and local team
references across Blueprint properties and 14,901 Make/Go files. Every
consumer was within the reviewed test scope or already disabled by this
profile. Exactly these six files are excluded; their parent directories and
other source files remain included. The existing patch for
`SettingsLibRoboTests` remains unchanged, even though its Blueprint file is
now outside the source selection.

Three further projected helpers share files with production code:
`SettingsLibIpc-testutils`, `car-ui-lib-testing-support` and
`car-ui-lib-testing-support-source`. Separate reviewed source patches gate
only those helpers with the same typed profile switch and `default: unset`;
the IPC and car SDK Blueprint files remain included. These three gates extend
the original 19 source declarations; the counts do not describe executed
tests or enabled build targets. They were found by projection, not the seven
reported Graph 14 errors. Production code, licenses, defaults and validation
checks are retained.

The `hwtrust` restoration is a separate source-projection finding, not an
attribution of the observed Graph 16 failure. Retained production code in
`libkeymint_remote_prov_support` unconditionally needs `libhwtrust_cxx`.
The genuine `tools/security` project at Android 16 r1 commit
`8d8a8332751c3b20a87f38dd7cb4039eeea489b5` supplies that provider. The negative
`tools/security/` prefix and positive `tools/security/remote_provisioning/hwtrust/`
prefix select its two Blueprint files and all 12 module definitions, including
the Rust library, CXX bridge, binaries, tests, fixtures and original license
metadata. The full project remains unchanged, and all 16 external dependency
providers already exist in selected source paths.

The other 32 Blueprint files declare 43 modules outside this product, including
three unrelated fuzzers with missing libraries. None of those module names is
referenced by the service-fuzzer registry, whose 45 unique named fuzzers and
validator remain intact. KeyMint production code, API checks, SELinux,
signature and dependency validation are not excluded or patched to bypass the
missing provider. This selection does not enable recovery decryption or prove
that `hwtrust` is packaged in the recovery image; variants and linking still
require the next strict build.

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
directory exclusion ends in `/` so it does not hide similarly named siblings.
The scene, audio and reviewed Robolectric support exclusions name individual
`Android.bp` files, preserving other files and child directories, including the consumed scene
test helper in `utils`. The documented positive provider prefixes are explicit exceptions
inside otherwise excluded projects, evaluated by the same longest-prefix rule.
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
replacement. Its source also includes installer and formatting code. The
separate minadbd/sideload guard rejects that transport before changing USB
state; it does not disable or prove safe the other write paths. Before any
separately authorized boot test, review and constrain startup/actions, inspect
the ramdisk and compiled policy, verify authentication and the boot chain, and
establish a stock-return procedure. Data decryption, metadata access, backups,
restores, snapshots and slot control are not implemented or validated here.

The workspace's standard-library tests inspect the actual target files and
their separation, image layout, policy, authentication and storage invariants.
They do not run Android make/Soong, compile SELinux, load a module, or substitute
for the separate recovery build and authorized hardware tests.
