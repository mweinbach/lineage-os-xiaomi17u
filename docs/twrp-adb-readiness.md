# ADB readiness for Nezha recovery

The default `user` target is not ready for authorized ADB log collection. No
trusted host key is bundled, and no recovery authentication or log-access test
has passed. Successful compilation or USB enumeration would not establish
authorized access. This document records source evidence and a proposal, not
implemented provisioning.

The pinned authentication path is:

- `packages/modules/adb@ce023afef190b0cea7f8939e9dd5ee3ee79b137b`,
  `daemon/main.cpp`, with
  `patches/twrp/0004-require-recovery-adb-auth.patch`, requires authentication
  even when unlocked or debuggable. `daemon/auth.cpp:156` verifies a host's
  signature against trusted public keys; `adb.cpp:472` then authorizes it.
- `frameworks/native@2827a4a16b0340ecd07c2d5a6c89991799b362bb`,
  `libs/adbd_auth/adbd_auth.cpp:393`, reads `/adb_keys` with symlink following
  and `/data/misc/adb/adb_keys` without symlink following. Unknown keys trigger
  a `PK` request through init's `adbd` socket; a framework client must answer
  `OK` or `NO`. A valid previously provisioned key does not need that client.
- `bootable/recovery@b70f8e998b302381ecefc6e7f46df1614bd61afc`,
  `Android.bp:425`, selects `twrp.cpp`. The commented-out AOSP binary using
  `recovery_main.cpp` does not supply its userdata-key-copy routine. The
  inspected TWRP source has no identified authorization-dialog client;
  `gui/action.cpp:2030` only changes USB configuration.

The target deliberately has no userdata mount or decryption integration, so
stock `/data` authorization cannot be assumed available. The patched init
automatically requests ADB only for `ro.debuggable=1`; the default user target
still needs an explicitly reviewed startup path.

The subsequent startup review confirms that the existing recovery init script
is reached through `init_second_stage.recovery` and `init_recovery.rc`, at
`/system/etc/init/hw/init.rc`. It does not need a new package request. Ordinary
adbd remains a disabled service until requested; the excluded MTP startup path
does not supply that request, and the GUI's explicit ADB action is not an
authentication dialog. Logd already receives an explicit `on init` start.

The source packaging review identified three original providers missing from
the inspected product's eight explicit requests: `adbd.recovery`,
`cgroups.recovery.json`, and `task_profiles.json.recovery`. The ADB API phony
supplies libraries rather than the daemon, and the upstream task-profile request
is inside the disabled crypto branch. The target now explicitly requests all
three original modules alongside `recovery`, without enabling crypto or
inheriting the broad vendor product. This is a source change, not a finding from
a completed installation graph or ramdisk.

The next generated product configuration must contain the previous eight roots
plus exactly these three additions. Final packaging must verify the original
ARM64 daemon at `/system/bin/adbd`, both JSON files in `/system/etc`, their
existing SELinux labels and the `/etc` link. That link must already exist in
the ramdisk because cgroup setup precedes the normal `early-init` and `init`
actions. The [target notes](../recovery/twrp/device/xiaomi/nezha/README.md)
record the exact provider names, expected paths and remaining artifact checks.

Automatic startup also needs a separate transport restriction. The pinned
`daemon/main.cpp` falls back to TCP/VSOCK listeners on port 5555 if the FunctionFS
endpoint `/dev/usb-ffs/adb/ep0` is absent. Explicit listener properties can
select networking as well. `TW_NO_NETWORK` controls TWRP feature selection;
it does not remove those adbd paths. A guarded init-event prototype still
requests the daemon after a failed FunctionFS mount, so that prototype is not
admitted on its own. Prevent the networking fallback before describing future
startup as USB-only; retain host authentication and the existing privilege drop.

The ignored source receipt `reports/twrp-user-adbd-startup44/handoff.json`,
SHA256 `953b6c4fb2fe1eaad882df40341950d4aea7d8f98818e8a99d8a830e7e3e7412`,
binds 25 startup and 19 independent packaging checks. Those checks validate
source contracts and controlled init-event expectations, not device behavior.
The [community comparison](twrp-community-references.md) corroborates the stock
USB controller paths but supplies no authenticated startup or log-access test
for this profile.

Setting `PRODUCT_ADB_KEYS` alone is insufficient. In
`build/soong@91bdc79cffb29d35b2d46a33204c061c3e7ed4f7`,
`etc/adb_keys.go:50` skips installation unless the product is debuggable and
has a key input. `build/make@3b5b2b43b8e2200ef92b7b814a84c8dde8b74121`,
`core/product_config.mk:471`, also conditionally clears that variable.

A proposed personal-build option would accept one explicitly authorized,
user-designated **public ADB key file**. It must never discover host keys or
read private keys. Validate Android's public-key encoding, reject private-key
and unrelated formats, and keep the input and personalized artifact ignored
and undistributed. Record a digest rather than identifying key comments.

Stage a regular, root-owned `0644` `/adb_keys` before packaging and signing;
verify its exact bytes and effective SELinux label before starting adbd.
`system/sepolicy@f0270686ee017f4de42e1032aca7527031bcc484`,
`private/file_contexts:27`, labels this path `system_file`; `private/adbd.te`
permits reading that type. Actual labeling and policy still require validation.
Keep `user`, `ro.secure=1`, `ro.adb.secure=1`, enforcing SELinux, patch `0004`,
and `patches/twrp/0014-native-recovery-disable-minadbd.patch`. Do not enable
root or sideload to avoid authentication.

Artifact inspection must establish key identity, permissions, labeling,
authenticated-adbd selection, startup and logging inputs. Only a separately
authorized device test can prove that the intended host connects, an unrelated
host remains unauthorized, intended shell privileges remain intact, and bounded
reads of `/tmp/recovery.log` and logcat work. No phone action or key read is
authorized by this proposal.

The ignored receipt
`reports/twrp-adb-readiness-source-audit-20260828T122741Z.json` records 15
exact pinned source hashes and two verified prepared patch postimages.

Authorized ADB does not by itself grant access to every diagnostic. The current
`user` profile drops the shell to UID 2000 and runs commands in the SELinux
`shell` domain. A subsequent source review found these distinct limits:

| Diagnostic | Source-based expectation before a device test |
| --- | --- |
| `/tmp/recovery.log` | A fresh log is root-owned mode `0666`, but recovery mounts tmpfs over `/tmp`; the reviewed policy does not grant shell access to that tmpfs file. Reopening an existing file preserves its mode. |
| Logcat | Shell retains the log group, has `read_logd` policy access, and is exempt from framework log-consent prompts. Logd startup and its task-profile inputs still need artifact and runtime verification. |
| Plain `dmesg` | Shell lacks the required kernel-log capability and policy access. A userdebug build does not remove the shell-domain restriction. |
| Pstore | Shell can search the directory and read permitted known files, but lacks the directory open/read access used by the collector's initial listing. Device file modes remain unverified. |

The collector's mandatory `readlink /proc/<recovery-pid>/exe` check is another
possible blocker. Normal Linux cross-UID ptrace-read credential checks are
expected to reject shell reading a root process's executable link without
`CAP_SYS_PTRACE`; membership in the readproc group does not establish that
permission. This is a source-based inference, not a measured result from the
phone's kernel. The collector currently stops if the check fails. Do not
silently skip it, enable root ADB, or weaken SELinux to make collection pass.

These findings require a separately reviewed logging design in addition to
public-key provisioning and adbd startup. Logcat alone is not a substitute for
the kernel ring buffer or the TWRP recovery log. Required applets, installed
paths, library dependencies, effective labels and logd's background scheduling
profile must also be verified in the actual artifact.

The ignored receipt
`reports/twrp-nonroot-log-readiness-20260828T134206Z-v2.json`, SHA256
`d669d693e9fae306a2a29838ed4619ac796c225c0e9f13d80e3ae2922239986d`,
binds 37 reviewed source files and the 16-patch queue. No key, phone, permission
or collector behavior was changed by this review.
