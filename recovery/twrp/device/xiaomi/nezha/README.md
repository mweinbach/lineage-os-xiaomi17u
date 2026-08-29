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

The device product explicitly requests four original packages: `recovery`,
`adbd.recovery`, `cgroups.recovery.json`, and `task_profiles.json.recovery`.
The three additions repair a source-level packaging omission for the intended
authenticated ADB and log workflow. The minimal inheritance chain does not
include `base_vendor.mk`, which normally requests the daemon and recovery
cgroups profile. TWRP requests the task profiles only in its decryption branch,
which remains disabled here. Its enabled logd branch does not request either
JSON file, even though logd treats a failed background scheduling profile as
fatal. Explicit package requests avoid relying on incidental installation.

The pinned original providers retain these exact Soong and Make module names,
without a second `.recovery` suffix. Their expected paths and existing labels
inside the recovery ramdisk are:

| Package | Original provider | Expected path and SELinux type |
| --- | --- | --- |
| `adbd.recovery` | `packages/modules/adb/Android.bp`, `cc_binary`, `recovery: true`, stem `adbd` | `/system/bin/adbd`, `adbd_exec` |
| `cgroups.recovery.json` | `system/core/libprocessgroup/profiles/Android.bp`, `prebuilt_etc`, filename `cgroups.json` | `/system/etc/cgroups.json`, `cgroup_desc_file` |
| `task_profiles.json.recovery` | `bootable/recovery/etc/Android.bp`, `prebuilt_etc` using `:task_profiles.json`, filename `task_profiles.json` | `/system/etc/task_profiles.json`, `task_profiles_file` |

These files are expected under `recovery/root` in the product output; the
original `/etc` link to `/system/etc` supplies the profile lookup paths.
That link must already exist in the packaged ramdisk: cgroup setup runs before
`early-init` and `init`, so a later init-script symlink alone is insufficient.
The original providers, dependencies, contents, file-context rules, and product
inheritance are unchanged. All 182 source-selection rules and every other
non-package device assignment were unchanged by that package addition; later
source restorations append rules as documented below. Graph 47 verified a
generated product package list differing from the recorded eight roots only by
the three explicit additions. That list is not a transitive installed-file
inventory, and the graph still failed on an APEX availability check.

The default `user` build, secure ADB properties, authentication patches,
SELinux enforcement, signature and AVB checks remain in place. This change
does not alter decryption or network settings, allow root ADB or unauthenticated
sideload, add a host key, or modify the USB transport. Package selection does
not enforce USB-only behavior: the original daemon had a TCP/VSOCK fallback
when USB was unavailable. The separate transport review led to patch 0024,
which excludes network listener selection and Wi-Fi TLS discovery in recovery.
It preserves authentication and privilege dropping, requests the original USB
transport when the FunctionFS endpoint exists, and otherwise exits with status 1.
The ordinary Android branches remain unchanged. This does not prevent network
sockets opened by an authenticated shell or reverse-forwarding request. Package
inclusion is not proof of daemon startup, cgroup availability, USB transport,
authentication or log access. A successful strict build must still verify the
final ARM64 daemon, JSON contents, paths, labels, `/etc` link and logd
dependencies; device testing remains a separate step requiring authorization.

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
| `hardware/google/aemu/` | Original emulator exclusion; four shared provider files are restored below for the reviewed Crosvm closure |
| `packages/modules/AdServices/` | Advertising services and their test collectors |
| `device/google/cuttlefish/` | Cuttlefish device and host source, except the two reviewed signing and host-tool Blueprint files described below |
| `hardware/interfaces/virtualization/capabilities_service/vts/` | Virtualization capability VTS tests |

The initial `system/secretkeeper/` exclusion was later removed when restored
virtualization sources introduced real consumers, as described under Graph 6
below. Disabling recovery decryption does not make a consumed provider optional.

The source audit of retained Android Virtualization Framework consumers found
the original Crosvm providers `libfuse_rust`, `libdisk` and
`libcrosvm_control_static`. Their reviewed dependency closure also needs
gfxstream's existing AEMU libraries. Four exact positive source prefixes restore
`hardware/google/aemu/Android.bp`, `base/Android.bp`, `host-common/Android.bp`
and `snapshot/Android.bp` from the original AEMU checkout at
`caad0d2be91bde934e4ff299f9e1a78d8ca0ead2`. These files retain eight named
modules and four package declarations, including `aemu_common_headers`,
`gfxstream_base`, `gfxstream_host_common`, `gfxstream_snapshot`, their test
support and original license metadata. All 61 source-file references and seven
include-directory references exist. The remaining AEMU build files stay
excluded; raw include paths remain available independently of Blueprint
selection.

The ten original Android 16 r1 provider projects are pinned separately in
`config/twrp-dependencies.json`. They preserve Crosvm's GPU features, Mesa's
SwiftShader LLVM dependency and the genuine Wayland generator. The selected
Soong already permits that generator plugin; no validation exception is added.
This is a source dependency restoration, not an observed graph 24 failure or a
working virtualization or graphics feature. At that stage, `PRODUCT_PACKAGES` contained
only `recovery`. Compilation, linking and device behavior remain unverified.

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
for these leaves. Platform runner, collector and rule subtrees remained excluded
at that stage; the Graph 31 helper restoration is described below. The next
real build must still validate variants and generated artifacts.

Graph 22 found that the retained `tradefed-test-framework` needs the original
`test-composers` library. The positive
`platform_testing/libraries/health/composers/host/` prefix restores its two
Blueprint files from pinned project `7b48625b052b94b1ef24573ef5e8ffa5e2ea9783`.
All three original modules remain: `test-composers`, `test-composers-tests`
and `HostTestComposersTests`, together with their source, license and team
metadata. Their immediate providers already exist in the selected sources.
The parent health-test aggregate and the device-composer sibling remained
excluded at that stage; the required platform composer is restored below.
This restores build declarations; it does not claim those tests ran
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
`sdk_sandbox_exported_flags_lib`. Two narrow positive source prefixes initially restored
`packages/modules/AdServices/sdksandbox/Android.bp` and its `flags/` leaf from
the original project at `a6ee8245f54f1719a899809cc8727f7fcce9ca35`. The parent
file keeps the original package metadata, global Apache license,
`trendy_team_rubidium_sdk_runtime` team and `sdksandbox-java-defaults`; the
leaf keeps the flag declaration and both Java flag libraries. Its 10 original
flags, exported mode, visibility, API settings and container are unchanged.
Other AdServices runtime and test source files were excluded at that stage.
The original declarations are not replaced with device-local copies.

Graph 27 found that the retained framework API aggregates also need the
generated exportable stubs from `framework-adservices`, `framework-sdksandbox`
and `service-sdksandbox`. That selection restored sixteen exact Blueprint
files from the same pinned AdServices project. Their 65 named declarations
include the original API providers, package license, shared libraries, linter,
flags, Cobalt and protobuf generators, and the checked-in Cobalt registry
filegroup. The original SdkSandbox app definition shares a required provider
file and was retained unchanged; the AdServices APK and APEX build files and
the wider test trees remained excluded at that stage.

The Cobalt registry's bare filegroup has no package declaration of its own.
The earlier claim that it inherited AdServices root license metadata was
incorrect. In the pinned Soong implementation, `default_applicable_licenses`
comes from the module's own package directory and is not inherited from ancestor
directories. The root's Apache and BSD declarations, or the APK directory's
package defaults, do not assign those defaults to the Cobalt child. The original
declarations and license checks are unchanged; this does not establish
redistribution clearance.

This source selection does not add these services to `PRODUCT_PACKAGES`, which
at that stage contained only `recovery`. API checks and visibility
remain unchanged, as do the original module definitions and generator commands.
Shared external providers come from their existing pinned source projects.
This establishes a reviewed source dependency set, not successful compilation
or SDK sandbox behavior on Nezha; the strict graph and actual build still have
to validate it.

Graph 24 requires `sts-host-util` from the retained `CtsAppSecurityUtils`.
Two exact positive prefixes restore the original
`platform_testing/libraries/sts-common-util/host-side/Android.bp` and
`platform_testing/libraries/sts-common-util/util/Android.bp` at
`7b48625b052b94b1ef24573ef5e8ffa5e2ea9783`. The seven named declarations
keep the STS host library, Java resources, tombstone protobuf wrapper, docs,
native test defaults and shared utility providers together. Both files retain
their original global Apache package metadata. Their existing annotation
processors, protobuf generators, documentation template and compiler checks
are unchanged. The sibling host/device tests and rootcanal test product remain
outside the selected source scope. This restores the shared security-test
helper; it does not disable the CTS app-security consumers or certify a device.

Graph 24 also exposes `wakeup_client_protos` as a shared dependency of the
retained remote-access test servers. The exact positive prefix
`hardware/interfaces/automotive/remoteaccess/hal/default/proto/Android.bp`
restores the original two genrules and static protocol library from
`hardware/interfaces` at `3e2bcbf17426a5783f034c8b0bb0d26743b39892`.
The original `wakeup_client.proto`, protobuf include root, `aprotoc`, gRPC
generator and both linked libraries are present. The surrounding default HAL
implementation stays excluded. All three test servers and the remote-access
AIDL and VTS files remain selected. Their separate Car team metadata dependency
is supplied by the original provider described below; restoring this protocol
file alone does not resolve that dependency or establish a working automotive
service.

The remaining graph 24 Car host CTS error belongs to the closed
`cts/hostsidetests/car/` subtree: four Blueprint files define eight automotive
test, helper and defaults modules, with no outside named-module, source-path,
Make or Go consumers found in the reviewed source set. The negative prefix
excludes only that subtree. Its `cts/hostsidetests/car_builtin/` sibling, CTS security helpers and
remote-access AIDL/VTS files remain selected. The missing Car flag and two
protobuf providers reside in mixed runtime build files; they are not replaced
with local stubs or imported for this excluded automotive suite.

The separately retained remote-access tests need `trendy_team_aaos_power_triage`.
The original Android 16 r1 Car project is pinned at
`61256ae811853028effed5c2c7227aebc347dc5e`. Its initial admission used a negative
`packages/services/Car/` prefix and the sole exact positive
`packages/services/Car/teams/Android.bp`. That complete file preserves nine
original team declarations and the global Apache package license. The source
manifest keeps this historical admission reason unchanged. The current scope
also includes the shared API providers described below. The complete pinned tree has no
`Android.mk`, `AndroidProducts.mk` or `Makefile` module entrypoints; its original
root `CleanSpec.mk` still participates in normal build-output cleanup. This
metadata admission preserves the VTS consumers without inventing team aliases
or weakening dependency validation. It is not a successful graph or device test.

The subsequent source audit found retained consumers of `android.car-test-stubs`,
including the Car builtin helper at that stage and CTS media tests. This is an original Car
provider, not a generic SDK alias. Five exact positive Blueprint prefixes now
restore `car-lib/Android.bp`, `aconfig/Android.bp`, `car-builtin-lib/Android.bp`,
`libs/car-internal-dep-lib/Android.bp` and `prebuilts/Android.bp` beneath
`packages/services/Car/`. Their 41 named declarations preserve the original
API library, builtin/internal libraries, flags, API checks and documentation
generators. The original `car_sdk` prebuilt-API owner supplies the combined
latest API text modules. `metalava-manual` is an existing exported-directory
module, not a missing source folder. Original genrule tool resolution and
visibility checks remain unchanged.

At that stage, all other Car Blueprint files, including `service/Android.bp`
and the Car tests, remained excluded. The later APEX restoration below selects
the required service file. The earlier closed host CTS subtree stays excluded, while its
`cts/hostsidetests/car_builtin/` sibling and the other retained consumers remain selected. This
restoration is a source-audit projection, not a graph 25 failure or a working
Car feature. The original source records, flags, generator commands and API
validation remain intact; actual graph and compilation are still required.

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
profile. Exactly these six files were excluded at that stage; their parent
directories and other source files remained included. Graph 31 restores the two
consumed extension files, as described below. The existing patch for
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

Graph 31 reports missing `setupcompat` and `setupdesign`. The broader framework
source audit also identifies shared flags, generated sources and helper libraries
that retained framework and test consumers need. Eleven official Android 16 r1
projects are pinned in the supplemental source configuration. Their selected
scope contains 19 complete original Blueprint files and 108 named declarations.
The source audit accounts for their direct references, metadata and raw inputs;
it is not a successful build or a claim of complete transitive graph closure.
SystemUI and the shared platform test/Robolectric sources remain companion work.

At that stage, the five scoped projects used 17 source rules: one negative directory prefix for
each project and twelve exact positive Blueprint files. CellBroadcastService's
root retains its real stats generator and app definitions; CellBroadcastReceiver
provides the complete permissions filegroup file. Settings' flags require their
original license owner in the root file, which also retains `Settings-core` and
`Settings`. Launcher3's four files preserve its flags, shared library, checks and
`launcher-aosp-tapl`. Traceur's root keeps `TraceurCommon`, `Traceur-res` and the
inseparable app declaration. This does not install Settings, Launcher3, Traceur
or either CellBroadcast app in recovery: at that stage `PRODUCT_PACKAGES` was `recovery`.
Other Blueprint files in these five projects remained outside the profile at that stage.

The complete original SetupWizard, SetupDesign, SetupCompat and ZXing providers
need no additional scope rules. The subsampling image library and Dancing Script
font satisfy test-only dependencies in SilkFX and CorePerfTests; they are not
claimed as recovery runtime requirements or installed assets. Original license
metadata and the font's special licensing notice remain intact; source selection
does not establish redistribution clearance.

One additional exact positive rule restores the original `WifiTrackerLib` file
from `frameworks/opt/net/wifi` at
`1cab31f96d1f903e190708c1ce665520a4a89d10`. Its four definitions and eight external
references are independently closed against existing selected providers. This
preserves the library and resources required by SystemUI and Settings without
selecting sibling Wi-Fi build files or changing `TW_NO_NETWORK`.

Graph 31 also requires the original collector, Flicker and app-helper libraries.
The reviewed closure retains 51 original helper Blueprint files: the previously
restored WifiTrackerLib file plus fifty exact platform_testing files. Their
76 named declarations include the original performance-setup type registration;
no replacement helper, flattened test file or synthetic default is introduced.
Original package metadata, source lists and child library boundaries remain.
The platform_testing root aggregate and unselected sibling files stay excluded.

The shared runner requires the genuine `Robolectric_all-target` library chain.
Its two original extension files, initially excluded at Graph 14, are restored
by removing those negative rules. They retain `Robolectric-aosp-plugins`,
`ClearcutJunitListener`, their host tests and original team declaration. An exact
positive rule also restores `junitxml`. Equal-length positive/negative rule ties
are not used. The other four Graph 14 Onboarding/SettingsLib exclusions and all
historical patch entries remain unchanged.

The exact SystemUI `tracinglib/robolectric/Android.bp` file is excluded after a
complete pinned-owner and current-source incoming-reference audit. It contains
only `tracinglib-robo-test` and its `tracinglib-test-app`; no outside module or
literal build-path consumer was found. The mixed `animationlib/Android.bp` and
all production tracing files remain selected. Separate reviewed patches use
three named test guards for `animationlib_robo_tests`, `CtesqueRoboTests` and
`NativeGraphicsTests`, only under the typed native recovery setting. Shared
libraries and normal Android behavior remain intact; the existing disabled
Robolectric runtime helper is not enabled to mask those test dependencies.

That cohort produced 146 source rules. Whole original SystemUI and
Robolectric sources, the MIME data generator and the Turbine compiler-tool
provider are coordinated source requirements. The dependency and factory audits
are not proof of compilation, app functionality or a complete runtime closure.
The next strict graph still validates the selected modules and generated paths.
No app packages, networking, decryption, device writes or validation waivers
are enabled by these source selections.

Graph 32 requires `CtsSdkSandboxTestScenario` through a retained CTS WebKit test.
Eight exact positive rules restore eight complete original Blueprint files in
AdServices at `a6ee8245f54f1719a899809cc8727f7fcce9ca35`. Their 25 named declarations
retain the scenario rule, executor, device/host utilities, clients and shared
providers with original metadata. The upstream path is spelled `textexecutor`.
All direct references and six SDK-generated library providers were resolved
against the selected sources. These files add no Robolectric constructors and
need no additional Robolectric gate. The root test aggregates, unrelated
sibling files and SDK-sandbox test runner remained outside that Graph 32
selection; the runner is restored separately after the Graph 33 failure below.

`TvSettingsAPI` comes from the original TvSettings project at
`139dd3c1a8f626a57271baf4926180f8d1f3bade`. A negative project prefix and exactly two
positive files, `SettingsAPI/Android.bp` and `TwoPanelSettingsLib/Android.bp`,
retain five declarations including the required `TvSliceLib`. Both packages use
the existing global Apache license without requiring the TV app's root build
file. Their 47 direct references and one inherited library dependency resolve;
the original TV app, unbundled product and Robolectric tests stay excluded.
This does not install a TV product or change Nezha's device identity.

That Graph 32 selection had 157 source rules. These additions preserve security,
API, signature, variant and dependency validation. They describe source closure,
not successful CTS execution, Android compilation or recovery hardware support.

Graph 33 failed because the retained `WebViewSandboxTestSdk` requires
`CtsSdkSandboxTestRunner`. One exact positive rule now restores the original
`sdksandbox/tests/testutils/testscenario/testrunner/Android.bp` from the same
pinned AdServices project. Its single `java_library` keeps the original Java
source, Apache license, team and CTS visibility. The genuine `truth`,
`CtsSdkSandboxTestExecutor` and `compatibility-device-util-axt` dependencies
are already selected. Sibling test files remain excluded.

A separate source projection of that helper's `:sdksandbox-test` certificate
reference restores the original `sdksandbox/tests/keys/Android.bp`; this was
not the error reported by Graph 33. Its unchanged `android_app_certificate`
declaration keeps the original basename, license, team and inherited visibility.
In the pinned Soong source, this source-app certificate dependency is added
after the existing visibility pass; no exemption, visibility override or
validator change is introduced. No key or certificate contents were read,
copied or changed, and product signing configuration is unchanged.

A separate CTS lookahead found that `CtsSecurityBulletinHostTestCases` needs
the `MainlineModuleDetector` test artifact. One exact positive rule restores
`platform_testing/libraries/sts-common-util/apps/MainlineModuleDetector/Android.bp`
from `7b48625b052b94b1ef24573ef5e8ffa5e2ea9783`. Its original `android_test`,
`cts_defaults`, sources, manifest and test settings remain intact. The reviewed
direct and implicit providers are already selected; no factory or test settings
are changed. This is not a Graph 33 diagnostic, and the platform_testing root
aggregate and sibling apps remain excluded.

The Graph 33 cohort produced 160 source rules. These three restorations add no
package to `PRODUCT_PACKAGES` or test certificate to recovery trusted keys.
These are source checks, not cryptographic validation, and do not establish
that the next graph or any device test passes.

Graph 34 reports missing `libwifi-system` in the retained hostapd and supplicant
VTS helpers. One exact positive rule restores
`frameworks/opt/net/wifi/libwifi_system/Android.bp` from the existing owner at
`1cab31f96d1f903e190708c1ce665520a4a89d10`. Its three original declarations retain
`libwifi-system`, `libwifi-system-defaults` and `libwifi-system-test` together.
The four genuine external providers, global Apache license and all eight raw
files are present. The rule selects only this build file; sibling build files
remain excluded. The Wi-Fi restoration produced 161 source rules, with networking
still disabled and `PRODUCT_PACKAGES` then limited to recovery.

The original exported `mock_hal_tool.h` retains its stale
`wifi_system/hal_tool.h` include. A bounded scan of 185 C/C++ source and header
files in the Wi-Fi owner and Wi-Fi VTS tree found no source including that mock
header. This caveat is preserved, not patched around; the audit does not prove
complete C++ header compatibility, compilation or working Wi-Fi on Nezha.

A separate CTS source projection found that the retained `CtsSettingsTestCases`
needs `com_android_car_settings_flags_lib`. The original Car Settings project at
`64634c7bfc79be369f0cd251d6c61df995cdf8b1` supplies it through the complete
`packages/apps/Car/Settings/aconfig/Android.bp`. A negative project prefix and
that one exact positive file retain both `com_android_car_settings_flags` and
its Java flags library, including their original flag input and Apache metadata.
The other eleven app, test and generator declarations have no retained incoming
consumer in the bounded audit and stay excluded. `CtsSettingsTestCases` remains
selected; no substitute flags, factory changes or new test gates are introduced.
This is a source projection, not an actual Graph 34 diagnostic. That selection
had 163 source rules and does not install Car Settings or change
Nezha's identity. Compilation and device behavior remain unverified.

Graph 34 also reports `CtsCarBuiltinApiTestCases` requiring
`android.car.test.utils`. The complete `cts/tests/tests/car_builtin/` component
is excluded after review of its two Blueprint files, two named test modules
and 50 source blobs. This includes both the root test and
`apps/SimpleApp/Android.bp`, which defines `CtsCarBuiltinSimpleApp`.
Excluding the root build file alone was rejected because the retained child
would lose its inherited team, `trendy_team_aaos_framework`. Excluding the
complete component leaves no selected descendant without that metadata.

The bounded Blueprint, Make, Go and product review found no outside active
incoming consumer of this component. CTS suite membership is collected from
selected modules and does not impose a fixed dependency on these two tests.
The separate `cts/hostsidetests/car_builtin/` suite and its PM helper remain
selected, along with Settings CTS and the existing Car SDK, flags and team
providers. That selection had 164 source rules. This changes test
availability in the native recovery profile; it does not claim complete CTS
coverage, a successful graph or a working recovery. No source definitions,
test gates or validators are changed.

Graph 39 reports the missing `android.automotive.watchdog-V2-ndk` provider for
`android.hardware.automotive.vehicle@2.0-manager-lib` and
`android.hardware.automotive.vehicle@2.0-fake-user-hal-lib`. Both inherit that
dependency from `vhal_v2_0_target_defaults`. One exact positive rule restores
`packages/services/Car/cpp/watchdog/aidl/Android.bp` from the already present Car
revision `61256ae811853028effed5c2c7227aebc347dc5e`; no source fetch is needed.
The complete original file retains two AIDL interfaces: public watchdog
versions 2 and 3, and the internal interface importing public V3. Its original
`trendy_team_aaos_framework` team resolves through the already selected
`build/make/teams/Android.bp`; the global Apache license provider is also selected.

That selection had 165 source rules. The previous 164 rules retain
their order, and the broad Car exclusion remained in place: that step restored
no neighboring watchdog implementation, power, telemetry, service or test
Blueprint. `PRODUCT_PACKAGES` was then `recovery`; this source-provider repair
does not install a Car service or establish compilation or device behavior.
Source definitions, API declarations, feature flags and validators are unchanged.

Graph 42 reports that `platform-bootclasspath` cannot resolve
`com.android.adservices`. Four exact positive rules restore these complete
original files from the already present AdServices revision
`a6ee8245f54f1719a899809cc8727f7fcce9ca35`:

- `packages/modules/AdServices/apex/Android.bp`
- `packages/modules/AdServices/adservices/apk/Android.bp`
- `packages/modules/AdServices/adservices/service/Android.bp`
- `packages/modules/AdServices/apex/permissions/Android.bp`

The cohort preserves 19 original declarations, including 15 named modules,
and the original APEX, APK, service, permission, key and certificate providers.
Their required providers already exist in the selected source tree; no source
fetch is needed. Signing declarations are unchanged, and no key material was
read or changed. The restored APK package's license defaults apply to its own
directory, not to the Cobalt child described above.

That selection had 169 source rules, with the previous 165 rules in
their original order. The broad AdServices exclusion still protects unrelated
files and test subtrees. `PRODUCT_PACKAGES` was then `recovery`, and
`TW_EXCLUDE_APEX` remains true; this scope change does not enable installed-system
APEX discovery. Dependency, APEX, signature and license checks remain enabled.
This is source-graph repair, not proof of compilation, final image contents or
AdServices behavior in recovery.

Graph 43 reports 43 absent app and tool dependencies of the handwritten
`aosp_shared_system_image` declaration. Excluding its entire
`build/make/target/product/generic/Android.bp` file was rejected: the companion
`build/make/target/product/gsi/Android.bp` consumes its shared image defaults.
Excluding both files was also rejected because retained `vts_vndk_utils` in
`test/vts-testcase/vndk/Android.bp` needs the GSI file's `vndk_lib_lists` provider.
All three Blueprint files therefore remain selected.

Patch `0021-native-recovery-generic-system-image` instead adds an `enabled`
selector only to `aosp_shared_system_image`. The existing typed
`nezha_twrp.native_recovery_only` value disables that one image in this profile;
the default branch is true, preserving the original enabled behavior for false
or absent profile values. The generic and GSI defaults, custom module type,
variables, signing and file-context helpers, and VTS providers remain intact. Recovery's own image
generation, AVB, size, SELinux and VINTF checks are unchanged. This does not
establish a successful GSI build or passing GSI/VTS tests.

A separate source projection, not an actual Graph 43 diagnostic, requires two
original Cuttlefish Blueprint files at revision
`c6a8b05c38d88e8d19b83fd8d47f75c0686f2e69`. A negative
`device/google/cuttlefish/` prefix admits only these exact positive exceptions:

- `device/google/cuttlefish/apex/keys/Android.bp`
- `device/google/cuttlefish/host/commands/append_squashfs_overlay/Android.bp`

The first file preserves `com.google.cf.apex.key` and
`com.google.cf.apex.certificate` for retained HAL APEX declarations. The second
preserves the Rust host binary `append_squashfs_overlay` and its original
`append_squashfs_overlay.test` for retained OpenWrt image generators. Both files
have their own global Apache package metadata; their four named definitions
and two package declarations remain unchanged. The only ordinary external
module dependency is the existing host-capable `libclap`.

Blueprint filtering does not suppress Make autodiscovery. The full project has
no `Android.mk`, but its root `CleanSpec.mk` is discovered; the finder stops
descending there rather than independently importing the nested CleanSpec.
An initial read-only check found `clean_steps.mk` absent. That state must be
checked again immediately before Kati: absent state initializes the clean-step
record without running the steps, while existing state can run newly discovered
steps that remove product and recovery charger/health outputs. Original
CleanSpec and clean-state handling remain enabled; no clean state is fabricated
and no output is deleted to force absence.

A separate CTS packaging projection restores only
`platform_testing/scripts/Android.bp` at the existing revision
`7b48625b052b94b1ef24573ef5e8ffa5e2ea9783`. Its original `sh_binary_host`
`test-utils-script` has its own global Apache package and no ordinary module
dependencies. The retained `csuite_standalone_zip` action copies the utility
into its host ZIP; neither that action nor the host binary factory executes
or sources the script. Future test runtime behavior was not exercised. The
`platform_tests` aggregate and other script Blueprints remain excluded, while
the previously selected `perf-setup/Android.bp` remains selected.

That selection had 173 source rules, preserving the previous 169 rules
in their original order, followed by the three Cuttlefish rules and the exact
script-provider file. No Cuttlefish product, board, identity, kernel or
firmware is inherited. `PRODUCT_PACKAGES` was then `recovery`, and Nezha retains
its own AOSP engineering recovery key at
`external/avb/test/data/testkey_rsa4096.pem`. The scope audit did not read or copy
key payloads. This admits source providers, not Cuttlefish installation or
runtime support; signature, AVB, SELinux, VINTF and dependency checks remain
enabled, and compilation and final image contents remain unverified.

Graph 44 reaches Trusty test VM dependencies outside this recovery profile.
Four exact Blueprint exclusions are appended after the unchanged 173 rules:

- `packages/modules/Virtualization/guest/trusty/test_vm/Android.bp`
- `packages/modules/Virtualization/guest/trusty/test_vm/vm/Android.bp`
- `packages/modules/Virtualization/guest/trusty/test_vm_os/Android.bp`
- `packages/modules/Virtualization/guest/trusty/test_vm_os/vm/Android.bp`

These four files define 16 names at Virtualization revision
`c984fc337c11ca5edc03ccf02037b2455dd8fcaf`. A static scan of 12,120 Blueprint
files, 41,501 named declarations, 2,119 Make files and 13,584 Go files found
two retained tests consuming those providers: `libpvmfw_avb.integration_test`
and `vts_treble_vintf_trusted_hal_test`. The four exclusions are not closed
alone. They require the paired source patches that replace only those tests'
architecture-specific `enabled: true` values with the existing typed
`nezha_twrp.native_recovery_only` selector: true disables the test, while
`default: true` preserves its original architecture behavior outside this
profile. No test dependency, factory, visibility or license metadata is edited.

The mixed `packages/modules/Virtualization/guest/pvmfw/avb/Android.bp` remains
selected, preserving `libpvmfw_avb_nostd`, production `libpvmfw` consumers and
both AVB fuzzers. The mixed `test/vts-testcase/hal/treble/vintf/Android.bp`
at revision `9705f94b4d727578335a79e957bf839f273664b6` also remains selected,
preserving `vts_treble_vintf_test_defaults`, `libvintf_service_info_aidl`, and
the normal vendor, framework, no-HIDL and combined VINTF tests. The production
Trusty security VM, shared signing providers and neighboring Blueprint files
remain selected. That selection had 177 source rules; product packages,
security properties and every other device make assignment remain unchanged.

This is a bounded static closure review, not a successful graph, compilation,
passing Trusty or VINTF test, or runtime proof. Blueprint filtering does not
disable Make files or arbitrary Go factories. Signature, AVB, SELinux, VINTF
and strict dependency checks remain enabled; the next graph must still
validate the combined source patches and exclusions.

A separate provider projection appends five more rules for the original
Goldfish host utility and its namespace imports. Negative prefixes exclude
the rest of `device/generic/goldfish/` and `device/generic/goldfish-opengl/`,
with only these three complete Blueprint files restored:

- `device/generic/goldfish/Android.bp`
- `device/generic/goldfish/tools/Android.bp`
- `device/generic/goldfish-opengl/Android.bp`

Goldfish revision `40f1fffd800a519f942320f2c265bb7abfa5681f` supplies the
original `python_binary_host` named `mk_combined_img`. Its tools file explicitly
uses the root `device_generic_goldfish_license`; both preserve the original
Apache and BSD license kinds. The root also defines `gen-emulator-info` and
the namespace importing `device/generic/goldfish-opengl`. The imported root at
revision `ad6692caa5eeda26fb0dde1a6ca44494f07712d5` contains only its namespace,
package and license declaration. Its Apache, BSD, GPL-2.0 and MIT kinds,
`LICENSE`, and `BY_EXCEPTION_ONLY` metadata remain unchanged. This is not
licensing clearance. The selection retains two of 70 Goldfish Blueprint files
and one of 13 Goldfish OpenGL Blueprint files; no child graphics modules or
emulator product are selected by these rules.

The same projection restores the original `prebuilts/remoteexecution-client`
revision `6bcf0cc83afa9268ca79a442db0dc4b8e29a1266` without an additional
source rule. Its one root Blueprint defines `rewrapper` as a
`prebuilt_build_tool` using `live/rewrapper`. It supplies a retained ART build
input without enabling remote execution. The inspected generated configuration
has `UseRBE` and `UseGoma` false, with no `USE_RBE` or `RBE_server_address`
environment entry. The original ART script uses the remote wrapper only when
`RBE_server_address` is present. The profile adds no remote-execution setting.

Recursive source trees for these three projects contain no `Android.mk` or
`CleanSpec.mk`. Goldfish's `AndroidProducts.mk` registers 14 product paths;
the original product loader imports only the selected `twrp_nezha` product.
No Goldfish product, board, firmware, kernel or identity is inherited. The
selection at that stage had 182 source rules: the original 173, four Trusty file
exclusions and five Goldfish rules, in that order. All other device make
assignments, signature, AVB, SELinux, VINTF and dependency checks remain
unchanged. These provider and execution-path checks do not demonstrate a
successful graph, image build or remote-execution run.

Graph 47 rejects `com.android.cellbroadcast` in the original `apex_available`
list of `aconfig_settingstheme_exported_flags_java_lib`, at
`frameworks/base/AconfigFlags.bp:1918` in variant `android_common_apex30`.
The real APEX definition was filtered out. The target restores these three
complete files from the already pinned CellBroadcastReceiver revision
`b97c8a4ffa3946d7206808bf4810746678b44a5c`:

- `packages/apps/CellBroadcastReceiver/Android.bp`
- `packages/apps/CellBroadcastReceiver/apex/Android.bp`
- `packages/apps/CellBroadcastReceiver/flags/Android.bp`

The original APEX contains `CellBroadcastApp` and `CellBroadcastServiceModule`.
The receiver root supplies `CellBroadcastApp`, `CellBroadcastCommon`, its
shared proto library, and the platform alternative app. The flags file supplies
`cellbroadcastreceiver_flags_lib` needed by `CellBroadcastCommon`. The service
root remains selected at revision `1249b4c132181f66cbc5a36168570f12390b4b2d`,
as does the receiver's existing permissions Blueprint. The rest of both
projects stays filtered, including the receiver's legacy app, overlays and
test files.

The complete original APEX defaults, app certificates, APEX key declarations,
package and license metadata, visibility, manifests, resources, and generation
rules are preserved. The framework's `apex_available` list is unchanged; no
APEX name, dependency validator or signature check is bypassed. The selection
at that step had 185 rules: the unchanged 182-rule prefix followed by these three exact
file rules. All four recovery package requests and every other device make
assignment remain unchanged. `TW_EXCLUDE_APEX` stays true; this source
restoration does not enable installed-system APEX discovery or add a
CellBroadcast app or APEX to `PRODUCT_PACKAGES`.

This repairs source selection, not a demonstrated build, final image inventory,
CellBroadcast operation or recovery runtime feature. The next strict graph must
validate the restored original providers and their dependencies; SELinux, AVB,
VINTF, signature and license checks remain enabled. This restoration adds no
API waiver.

A separate source projection after Graph 47 found `com.android.car.framework`
also filtered from retained `apex_available` lists. This was a projected
dependency, not another observed Graph 47 diagnostic. Its original APEX,
`ScriptExecutor`, `android.car-module`, service, proto and support providers
require thirteen exact Blueprint exceptions from existing owners. Eleven are
from `packages/services/Car` at `61256ae811853028effed5c2c7227aebc347dc5e`;
two are VHAL property/configuration files from the frozen base
`hardware/interfaces` revision `3e2bcbf17426a5783f034c8b0bb0d26743b39892`.
The exact thirteen paths are listed in `device.mk`. The already selected
watchdog AIDL file is not added again, and the broad Car and VHAL exclusions
remain in place around the reviewed files.

The APEX's system-server classpath fragment also needs the original
`car-frameworks-service-module`. Its owner, `frameworks/opt/car/services`, is
pinned at `d1edb5049c9e9bcadc38fa1069e6dbb525bb4d43`. A new negative project
prefix is followed by exactly three complete file exceptions:

- `frameworks/opt/car/services/builtInServices/Android.bp`
- `frameworks/opt/car/services/builtInServices/proto/Android.bp`
- `frameworks/opt/car/services/updatableServices/Android.bp`

These retain the real `car-frameworks-service` SDK, `car-builtin-protos`,
`car-frameworks-updatable-service-sources` and module library. Its generated
`car-frameworks-service.stubs.module_lib` comes from the original SDK factory;
no synthetic stub or namespace is introduced. The same factory still creates
its implementation/XML modules and SDK registration. The original Java, API,
proto and jarjar inputs are retained. The project's JNI and test Blueprints
stay excluded, and it has no `Android.mk`, `AndroidProducts.mk` or `CleanSpec.mk`.

The original Car APEX still names `CarServiceUpdatable` and `ScriptExecutor`,
with `android.car-module` in its bootclasspath fragment. Complete signing,
file-context, package, license, team and visibility declarations are preserved,
as are the original shared test helpers in the selected files. No new test
gate or Car product inheritance is added. Both `android.car-module` and
`car-frameworks-service` keep upstream `api_lint.enabled: true` and
`unsafe_ignore_missing_latest_api: true`. The latter disables latest-API
comparisons and can suppress conditional API lint in the original factory.
It is not a new waiver, and this audit does not demonstrate API-lint execution
or identical API validation coverage. Original current/removed API files
remain required.

The combined selection has 202 rules: the unchanged 182-rule prefix, the three
CellBroadcast restorations, then these thirteen existing-owner file rules and
four framework-service rules. Only one source owner is added. All four recovery
package requests and every non-source device assignment remain unchanged;
`TW_EXCLUDE_APEX` stays true. No Car app or APEX is added to `PRODUCT_PACKAGES`;
no Car firmware, kernel, product or device identity is inherited. This is bounded
source closure, not a successful graph, compilation, image inventory or Car runtime
test. Generated variants and the actual recovery image still require strict
build validation.

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

The authored USB glue selects configfs and forwards the bootloader's
`ro.boot.usbcontroller`. It also requests ADB at `post-fs` only for the secure
user profile when configfs is selected and the boot controller is exactly the
stock-recorded `a600000.dwc3`. Missing, different or late controller values do
not trigger that request. The original QCOM RC prefix and upstream userdebug
startup event are preserved. It does not guess a controller, switch a hardware
mode, adopt stock keys or add a second module loader. Init may still request
adbd after failed USB setup; patch 0024 removes the missing-endpoint network
fallback but does not prove enumeration or policy access. The recovery properties
require `ro.secure=1` and `ro.adb.secure=1`. The pinned Soong
`build/soong/scripts/gen_build_prop.py` supplies both values for `user`, together
with `ro.debuggable=0`. Build 62 exposed identical duplicate entries when this
product also declared both secure properties. The target now omits those user
redefinitions and supplies only `ro.adb.secure=1` inside the exact `userdebug`
conditional, because that variant's generator already supplies `ro.secure=1`
but not the ADB-auth property. The original userdebug debugging behavior and
mandatory recovery authentication remain unchanged. This fixes the generation
inputs, not the compiled property file: no postbuild deduplication is used, and
the inspector still rejects even same-value duplicate assignments. A fresh
image must pass the unchanged secure-property checks before admission.

No ADB public key is bundled, so
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


The build62 artifact scan found 44 unresolved ELF interpreters: 42 binaries
request `/system/bin/linker64`, while `e2fsck` and `hwservicemanager` request
`/system/bin/bootstrap/linker64`. All 1,074 recorded library dependencies had
unique archive providers, but that did not establish interpreter availability,
namespace compatibility or runtime startup. Neither linker path was packaged.

The target now explicitly selects the original `linker.recovery` and
`ld.config.recovery.txt` modules that pinned `base_vendor.mk` normally selects.
At bionic `99926c766ef7f121950611f047dba4769a25226c`, a separate recovery linker
linked against static libraries is installed as `/system/bin/linker64`; the
ordinary core linker and its APEX redirects are not selected. At linkerconfig
`e6e748db0343684959fc49356f07e1793f96db85`, `generate_recovery_linker_config`
runs the original host `linkerconfig --recovery` generator and installs its
output as `/system/etc/ld.config.txt`. This uses the generated recovery section
and `/system/${LIB}` search path, not a hand-written or empty substitute.
The current generated Make declarations prove both module names and recovery
install paths; they do not prove the revised outputs have been built.

The target's `nezha_recovery_bootstrap_linker64` uses the standard Soong
`install_symlink` module with `recovery: true` and an explicit dependency on
`linker.recovery`. It packages `/system/bin/bootstrap/linker64` as an absolute
symlink to `/system/bin/linker64`, matching the existing upstream recovery
init command. It adds no second linker implementation, 32-bit alias, copied
prebuilt, runtime APEX or post-build file mutation. The original init command
remains unchanged: it will report `EEXIST` for the already present alias;
pinned init logs that command failure and continues to the next command.
This is not silent idempotence or evidence that init ran on the phone.

The original early `/linkerconfig/ld.config.txt` placeholder also remains
unchanged. Pinned bionic selects that existing empty file, fails to parse a
configuration, and uses its native default namespace until init copies the
newly packaged real `/system/etc/ld.config.txt` over the placeholder. It does
not retry the system config after that parse failure. This describes source
behavior, not runtime validation. The 202 source rules, existing 33 patches,
ADB authentication, SELinux enforcement, AVB, ELF checks, and disabled storage,
crypto and network features remain unchanged. A new normal build and archive
inspection must prove the linker, nonempty generated config and alias are
actually present; namespace, relocation and device startup tests remain
separate gates. This change authorizes no device operation.


The build64 ramdisk and staging tree lacked `/etc`. This is a packaging defect:
pinned `system/core/init/init.cpp` queues `SetupCgroupsAction` before `early-init`,
and `libprocessgroup/setup/cgroup_map_write.cpp` reads `/etc/cgroups.json`.
Recovery's later `init.rc` command cannot supply that initial lookup path.

Nezha uses the existing `BOARD_RECOVERY_IMAGE_PREPARE` hook to create
`/etc -> /system/etc` during the normal recovery build, before `mkbootfs`,
compression and AVB signing. The hook requires real staging, `system` and
`system/etc` directories. It accepts an existing exact alias, rejects every
other `/etc` file, directory or link, and creates a missing alias exclusively.
GNU `ln -sT` refuses to treat a conflicting directory as a link destination;
there is no force overwrite, manual output repair or activation of the wider
`init.environ.rc` root setup. The installed recovery modules remain normal
dependencies of the original ramdisk staging target.

The pinned Makefile invokes this hook after producing `ramdisk-files.txt` and
`ramdisk-files.sha256sum`. Therefore the hook reruns both original inventory
commands after establishing the alias. The name list includes `etc`; the
digest list does not follow symlinks, but it hashes the name list itself, so
refreshing only the names would leave a stale checksum. The original filters
remain unchanged. Bash error and pipeline failure handling stops packaging if
any guard or regeneration fails. No checksum exception or unvalidated name
append is used. The original repacker consumes these inventories, although
Nezha's repacking feature remains disabled.

This target change preserves the nine-file target layout, all 33 source
patches, seven selected packages, source rules, modes, authentication, SELinux,
AVB and disabled features. It does not chmod staging to match archive metadata:
the separately reviewed `mkbootfs` mode normalization remains intact. A new
normal build must establish the alias and coherent inventories in the actual
archive before the existing initial-profile lookup gate can pass. Source
review and offline fixtures do not establish cgroup mounts, daemon startup,
ADB access or permission to boot or flash a device.
