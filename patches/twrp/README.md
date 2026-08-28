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
The separate `minadbd`/sideload implementation is not covered by this daemon
patch and is not admitted for use in the first compile experiment.

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
