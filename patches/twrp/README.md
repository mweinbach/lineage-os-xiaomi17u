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

Patches 5 through 11 add only an `enabled` property to the nineteen named
modules recorded in `series.json`. They apply only when the typed Soong Boolean
`nezha_twrp.native_recovery_only` is true. Their `default: unset` branch leaves
the previous property behavior and inherited defaults intact for other
products. The Nezha device configuration sets this Boolean through the pinned
`soong_config_set_bool` Make helper. This native recovery profile deliberately
excludes eighteen JVM UI tests and their runtime helper; it does not claim to
run those tests or to provide the Android framework/automotive test runtime.

The recorded source audit examined 10,836 Blueprint files, including secondary
files. It found eighteen selected Robolectric test constructors, three already
outside the selected source roots, and no configurable aliases or explicit
references to the nineteen gated names. The runtime dependencies created
implicitly by Soong are covered by gating all eighteen selected constructors
alongside the helper. Recheck this inventory if the source selection changes.
Do not exclude the entire SystemUI or Bluetooth Blueprint files: they contain
production modules, shared defaults, compatibility configuration and licenses
used by retained modules. The patches preserve those bytes exactly.

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
`minadbd/minadbd.cpp` sets `auth_required = false` before `usb_init()`, and
neither `ro.adb.secure=1` nor the normal adbd patch changes that behavior. The
GUI's sideload action and OpenRecoveryScript's `sideload` command call
`twrp_sideload()`, which launches `/system/bin/minadbd` and selects the USB
sideload configuration. These entrypoints remain present; this is not a
build-time exclusion.

That sideload transport is not admitted for runtime use. This compile-only
experiment authorizes no boot or device command, and no authentication or
safety claim extends to minadbd. Before any diagnostic boot, separately disable
these entrypoints with a reviewed fail-closed gate or implement and verify
minadbd host authentication. Changing a packaging list or an ADB property alone
is insufficient.

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
  persistent writes. The image also retains manual formatting, install,
  sideload, shell, restore and other write-capable operations.
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
