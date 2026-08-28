# TWRP source patch queue

This queue belongs only to the isolated Android 16 TWRP source selected in
[`series.json`](series.json). It is not a patch set for the Evolution checkout
and does not make a recovery image ready to boot. Every changed file has an
exact project revision, input/output SHA256, size and Git blob ID. The patch
bytes have a separate SHA256. Hashes bind reviewed bytes; they do not establish
publisher trust or device compatibility.

The initial changes are deliberately small:

| Patch | Reason |
| --- | --- |
| `0001-remove-permissive-su` | Remove the active debug `su` permissive declaration without changing any allow or neverallow rule. |
| `0002-do-not-force-adb-root` | Stop recovery init from automatically requesting root ADB on every debug boot. Explicit debug root support is retained and still needs authenticated transport and enforcing policy. |
| `0003-preserve-source-on-envsetup` | Stop the vendor shell setup from truncating a VTS makefile when sourced. A build error must be repaired explicitly, not hidden by changing a source file. |
| `0004-require-recovery-adb-auth` | Require host authentication in the recovery adbd variant, including on unlocked/debuggable devices, and exclude recovery from trade-in/evaluation authentication bypasses. Normal Android adbd behavior is unchanged. |
| `0005-native-recovery-cts-robolectric` | Select out the one audited CTS Robolectric test for the Nezha native recovery product. |
| `0006-native-recovery-mobile-data-robolectric` | Select out the audited mobile-data-download Robolectric test. |
| `0007-native-recovery-framework-robolectric` | Select out twelve audited framework Robolectric tests across eleven files while retaining all shared production modules, defaults, licenses and other tests. |
| `0008-native-recovery-bluetooth-robolectric` | Select out the Bluetooth Robolectric test while preserving the Bluetooth service, build flags and shared libraries. |
| `0009-native-recovery-devicelock-robolectric` | Select out the two audited DeviceLock Robolectric tests. |
| `0010-native-recovery-healthfitness-robolectric` | Select out the audited HealthFitness Robolectric test while retaining its device tests and source groups. |
| `0011-native-recovery-robolectric-runtimes` | Select out the Robolectric runtime helper together with its eighteen implicit test consumers. |
| `0012-native-recovery-settings-ipc-testutils` | Select out only `SettingsLibIpc-testutils`, preserving the production IPC library and source group in the same file. |
| `0013-native-recovery-car-ui-test-support` | Select out the automotive Robolectric testing wrapper and its prebuilt source helper, preserving all production automotive SDK modules in the same file. |
| `0014-native-recovery-disable-minadbd` | Reject the standalone unauthenticated sideload/rescue transport and its TWRP caller before USB changes, only for the typed Nezha native recovery profile. |

Patches 5 through 11 add only an `enabled` property to the nineteen named
modules recorded in `series.json`. They apply only when the typed Soong Boolean
`nezha_twrp.native_recovery_only` is true. Their `default: unset` branch leaves
the previous property behavior and inherited defaults intact for other
products. The Nezha device configuration sets this Boolean through the pinned
`soong_config_set_bool` Make helper. This native recovery profile deliberately
excludes eighteen JVM UI tests and their runtime helper; it does not claim to
run those tests or to provide the Android framework/automotive test runtime.

The initial source audit examined 10,836 Blueprint files, including secondary
files. It found eighteen selected Robolectric test constructors, three already
outside the selected source roots, and no configurable aliases or explicit
references to the nineteen gated names. The runtime dependencies created
implicitly by Soong are covered by gating all eighteen selected constructors
alongside the helper. Recheck this inventory if the source selection changes.
Do not exclude the entire SystemUI or Bluetooth Blueprint files: they contain
production modules, shared defaults, compatibility configuration and licenses
used by retained modules. The patches preserve those bytes exactly.

Patches 12 and 13 extend the same typed Boolean gate to three test helpers in
two previously untouched base files. The wrapper
`car-ui-lib-testing-support` depends on `car-ui-lib-testing-support-source`,
so both receive the gate. Their source lists, dependencies, licenses and every
other property remain unchanged. Neither file is excluded: the production IPC
library and automotive SDK modules remain available.

The follow-up audit covered 10,855 Blueprint files and 14,901 Make/Go files.
It found no retained consumer outside the reviewed test closure after the
three gates and six companion Blueprint file exclusions in the device target.
Graph 14 reported Robolectric extension dependencies; the three helpers were
identified by the subsequent consumer audit, not by three additional observed
graph errors. This literal reference audit is not a complete evaluated Soong
graph, so the next strict graph must verify the combined selection.

The unchanged `native_recovery_profile` record describes the initial eighteen
tests and runtime helper. The separate `native_recovery_helper_profile` record
describes this extension and its companion exclusions. The queue now declares
twenty-two gates across twenty files. This is a historical declaration count:
one companion exclusion selects out the already-patched SettingsLib Robolectric
test file without modifying that patch or its receipt. No supplementary source
project is modified, and all eleven earlier patch records and payloads remain
unchanged.

The source-backed semantics and per-file module inventory are recorded in
`series.json`. `ModuleBase.Enabled` supports `select`, and Soong invokes a
module's dependency mutator only when that module is enabled. Ordinary
dependencies from retained modules to disabled modules still fail under the
existing strict validation. Existing special treatment of `required` tags is
unchanged. No missing-dependency allowance or validator bypass is introduced.
In the next graph attempt, check the generated `VendorVars` and `VendorVarTypes`
before treating this profile as verified. A successful recovery build remains
a separate gate; offline tests alone do not prove this selection was applied.

Apply the ordered queue only after resolving the complete selected manifest.
Require the recorded project HEAD, unmodified input paths and every input hash
before doing any mutation. Check all patch contexts first, apply with Git, and
verify every output hash afterward. A different source revision, dirty file,
missing dependency or failed check is a diagnostic result, not permission to
force an application, discard changes or weaken validation. Keep the original
resolved manifest and record the applied patches separately.

For an already prepared source tree, `twrp_build.py revise` accepts an appended
patch only when every old queue entry remains unchanged and the new file was
not previously patched. It verifies the exact frozen preimage and mode,
checks all patch contexts, and archives the previous receipt, source bytes and
patch payload before applying anything. It verifies the complete resulting
source state before advancing the receipt. A partial failure is preserved for
inspection; the tool does not reset sources or automatically adopt that state.

The normal AOSP init enforcement selection is retained. At the selected source
revision it permits a permissive boot property only for a debuggable build;
there is no unconditional TWRP `security_setenforce(0)` in the inspected init
source. The device target must keep enforcement selected, and the actual
recovery policy must pass an unfiltered `sepolicy-analyze ... permissive`
check with empty output. Removing one permissive declaration is not proof
that all compiled policy or runtime enforcement is correct.

Recovery ADB must retain `ro.secure=1` and `ro.adb.secure=1`. No authorized keys
are supplied by this queue. An image with no separately reviewed authorized
key should not become accessible to an arbitrary host. Authentication must be
verified in the actual selected adbd variant before a successful ADB/logging
claim; property text and removal of automatic root alone do not prove it.
The pinned AOSP daemon would otherwise force `auth_required=false` for recovery
on an unlocked or debuggable device, irrespective of `ro.adb.secure`. Patch 4
replaces that recovery-only branch with an unconditional authentication
requirement and prevents the later trade-in path from undoing it. The
non-recovery property-based selection and privilege-dropping behavior remain
unchanged. Confirm that `adbd_system_api_recovery` actually selects these
compiled sources and then test trusted, absent and unknown host keys.
The separate `minadbd` executable is already selected for building and packaging
by the pinned recovery. The packaging candidate preserves that dependency; it
does not add it. This executable does not enter the patched `adbd_main()`:
its original `minadbd/minadbd.cpp` sets `auth_required = false` before `usb_init()`,
and neither `ro.adb.secure=1` nor the normal adbd patch changes that behavior. The
GUI's sideload action and OpenRecoveryScript's `sideload` command call
`twrp_sideload()`, which would otherwise launch `/system/bin/minadbd` and select
the USB sideload configuration.

Patch 14 adds a reviewed fail-closed gate to both entrypoints. When
`nezha_twrp.native_recovery_only` is typed true, only `minadbd` and
`libtwrpinstall` receive `-DNEZHA_TWRP_DISABLE_MINADBD=1`. The daemon returns
`kMinadbdUnsupportedCommandError` (7) immediately after logging initialization,
before argument handling or transport startup. `twrp_sideload()` returns
`INSTALL_ERROR` before its first property read, USB change or fork. Gating
only the daemon would leave its caller waiting indefinitely for USB readiness;
the caller guard avoids stopping ordinary adbd in the first place. The normal
GUI path's MTP toggle is a compiled no-op under this target's existing
`TW_EXCLUDE_MTP=true`; the reviewed ORS sideload path does not stop adbd before
entering the guarded function. Other ORS commands and startup scripts remain
outside this gate.

The `default: unset` branches preserve other products' flags, including the
installer's existing `-DAB_OTA_UPDATER=1` and inherited defaults. Both real
modules, their libraries, tests and required packaging dependencies remain.
The previous thirteen patches are unchanged, and these four files were not
previously patched. This does not implement authenticated minadbd or add a host
key. That sideload transport is not admitted for runtime use. Before any
diagnostic boot, verify both selected compiler flags and the compiled early
returns, then test ordinary authenticated adbd separately. The source patch
and offline checks do not establish successful compilation or runtime safety.

Patch 17 restores the original Android 16 r1 image availability of
`libaconfig_storage_read_api_cc`. Graph 36 failed because TWRP added
`recovery_available: true` to this C++ wrapper without matching Rust recovery
variants. The source audit found no selected recovery consumer of the wrapper:
the relevant libraries, recursive defaults, generated factories and custom
configuration properties do not request that image variant. The sole Make
reference across the 640 configured projects copies the core shared library
and is inside the crypto/FBE branch, which this target leaves disabled.

Removing that one property makes the whole Blueprint byte-identical to the
[pinned AOSP Android 16 r1 file](https://android.googlesource.com/platform/build/+/874fa586c48ae230ebfcff0df1b9c1b004fa8f7c/tools/aconfig/aconfig_storage_read_api/Android.bp).
Host, core, vendor and product variants, the genuine Rust FFI bridge, generated
sources, release flags and runtime code remain unchanged. The remaining vendor
and product availability prevents an actual recovery request from silently
falling back to a sole core variant. A missed recovery consumer must still fail
the next strict graph; this source audit is not a graph or build success claim.
The alternative addition of 24 Rust/C++ recovery availability declarations was
reviewed but not applied. All sixteen earlier patch records remain unchanged.

Patch 18 supplies the recovery variant of the existing `aidl-analyzer-main`
static library. Graph 37 reached the generated SecureClock and Weaver analyzer
binaries, which inherit their interfaces' recovery availability and require
this library. Its two C++ inputs, exported header and genuine `libbase` and
`libbinder` shared dependencies are present; both dependencies already provide
recovery variants. Only one availability property is added to the helper.
The real C++/NDK interface libraries, analyzer generation, source selection,
product packages and service startup remain unchanged. These Binder analysis
tools are separate from the recovery log collector. The next strict graph and
build must verify the resulting variants; no installed-image or device result
is implied by the source checks.

Patch 19 supplies recovery availability for the genuine `android.se.omapi`
AIDL interface. Graph 38 failed because the existing `se_omapi` executable
requests a recovery variant even when this target leaves OMAPI disabled. Its
required NDK interface did not provide that variant. The single added property
reaches the generated C++ and NDK libraries and C++ analyzer; the pinned AIDL
generator does not pass it to Java or Rust. Their native dependencies already
declare recovery availability, including the analyzer helper from patch 18.

The entire original interface, version and import metadata, service source,
init rules and feature settings remain unchanged. The generated target keeps
OMAPI and crypto false as typed booleans, so its conditional OMAPI dependencies
and service requirement remain unselected. Availability does not enable the
feature or establish secure-element or decryption support. The next strict
graph and compilation must validate the new native variants.

Patch 20 restores the original `recovery-resources-common-mdpi` module in the
recovery Blueprint. Graph 39 reached Android's generated recovery-image
dependency on that module, which the TWRP fork had commented out. Removing
only the ten comment prefixes makes its declaration identical to the pinned
AOSP Android 16 r1 module. All 102 PNG inputs already exist and match the
official tree's file names, Git blobs and modes; the unrelated `dummyfile`
does not match the preserved PNG glob.

The recovery/root placement, `images` relative path and `no_full_install`
property are unchanged. The other four density modules remain commented out.
No density variable, generated-image dependency check, product package or
TWRP theme generation changes. This restores the real resource provider;
actual resource installation and final ramdisk contents still require a build.

Patch 21 limits the handwritten `aosp_shared_system_image` module to products
outside the typed Nezha native recovery profile. Graph 43 reached that unrelated
generic system image and its missing application dependencies. The patch adds
only an `enabled` selector: false for this profile and true otherwise, matching
the original Android image default. Shared image defaults, GSI and VNDK file
groups remain selected, as do the automatically generated system and recovery
image modules. The final recovery packaging route and all image checks are
unchanged.

Patches 22 and 23 exclude two Trusty virtual-machine tests from this recovery
profile: `libpvmfw_avb.integration_test` and
`vts_treble_vintf_trusted_hal_test`. Graph 44 reached two unsigned Trusty image
inputs whose original providers require a separate Trusty OS source build.
The device target also excludes the four original test-only Blueprint files
under `guest/trusty/test_vm` and `guest/trusty/test_vm_os`. Those four exclusions
are not sufficient alone: the two gated tests are their remaining selected
external consumers.

Only the existing architecture-specific `enabled: true` properties change.
The Rust AVB test receives the selector in ARM64 and x86-64; the Trusted HAL test
receives it only in ARM64. Each keeps its top-level `enabled: false`. Selecting
the typed recovery profile yields false; an absent or false profile yields the
original true architecture override. All other architectures retain their
original disabled state. The pinned Blueprint property merger replaces these
configurable architecture overrides, and both ordinary dependency mutation and
path-reference dependency mutation skip disabled modules.

Both mixed Blueprint files remain selected. Their complete source lists,
licenses, defaults, shared production AVB library, AVB test fixtures, normal
VINTF tests and AIDL sources are unchanged. No VINTF enforcement, service-fuzzer
registry, signature, rollback, SELinux or missing-dependency check is removed.
The global source review covered 12,120 Blueprint files, 2,119 Make files and
13,584 Go files and found no selected consumer of either gated test name. This
is a source review with explicit parser limits, not a completed graph or a run
of those tests. The two fresh source paths have separate project pins and
patch entries. All twenty-one earlier entries remain an unchanged prefix, and
the other queue metadata is unchanged. The next strict graph must validate the
combined selection.

The queue does not change signature verification, AVB/rollback checks, ELF or
artifact-path checks, dependency checks or SELinux assertions. The source
policy's allow rules and historical policy snapshots remain intact. Keep the
complete source diff and the generated ramdisk contents with any build receipt.
The removed envsetup operation is the confirmed immediate source mutation;
other shell helper functions remain in that file. This is not a general audit
or endorsement of executing every upstream helper.

## Compile-only boundary

The selected recovery source still has automatic persistent-state behavior:

- `startupArgs::parse` calls `args::get_args`, whose implementation in
  `twrpinstall/get_args.cpp` reads and rewrites the bootloader control block.
  `twrp.cpp` later calls `TWFunc::Clear_Bootloader_Message`.
- Startup converts pending install, wipe and backup arguments into
  OpenRecoveryScript commands. It can run pending scripts and shell startup
  hooks before the user reaches the main UI.
- Startup/settings/logging and `Disable_Stock_Recovery_Replace` contain
  persistent writes. The source also retains manual formatting, install,
  shell, restore and other write-capable operations. The separate sideload
  gate does not make those paths read-only.
- `TW_SKIP_ADDITIONAL_FSTAB=true` prevents the additional vendor fstab import;
  excluding crypto, APEX and userdata entries narrows the first experiment.
  None of those options is a write lock or proof of a safe boot.

A successful compile proves that the selected code and declared inputs can
produce an artifact. It does not prove display, touch, authenticated USB,
encrypted-storage access, snapshot safety, backup/restore or stock return.
Review and test those paths separately before any explicitly authorized phone
test. This queue authorizes no phone command, boot, flash, slot change or wipe.

Offline tests validate the patch records, exact edits and unified-diff framing.
They use Python's standard library and need no network, build tree or phone.
An actual source apply check and a recovery build remain separate gates.
