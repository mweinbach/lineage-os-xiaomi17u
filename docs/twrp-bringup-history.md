# TWRP bring-up history

This archive preserves the guide and recovery-review text that preceded the
current documentation cleanup. Use [TWRP for Nezha](twrp-bringup.md) for the
selected `working76` baseline and current local workflow, and the
[recovery plan](recovery-plan.md) for Evolution X integration and test gates.

The text below retains each experiment's facts, receipts, source pins and
relative links. Statements such as "not booted", "next" or "unverified" belong
to the checkpoint being discussed; they do not replace the later working76
hardware result. Historical commands are retained for debugging, not as the
current entry point. In particular, the source-build pipeline and its earlier
`make twrp-plan` meaning are distinct from the current prebuilt-adaptation plan.
No historical research record, patch, source checkout or image was changed by
moving this text.

## Original TWRP bring-up guide

TWRP is an active, separate bring-up target for the Xiaomi 17 Ultra (`nezha`),
using the recorded China firmware inputs. It is intended to shorten the recovery/test/logging cycle
without requiring a complete Evolution X ROM first. A compiled recovery is
not yet a tested rescue environment. Device actions require separate, explicit
user authorization.

**The working-image derivative now boots from `recovery_a` with its tested
defaults applied automatically.** The installed 100 MiB `working76/recovery.img`
has SHA256 `a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e`;
a readback of `recovery_a` matches. After reboot, without any runtime setting
commands, root ADB reports `3.7.1_16-Xiaomi_17_Ultra`, a running recovery service,
slot `a`, global `Permissive` SELinux, and zero for all three TWRP vibration
settings. Fresh recovery and kernel logs were collected successfully. The user
then confirmed that this fresh boot shows the UI and still feels fast. This is
qualitative touch feedback, not a timed latency benchmark. `working76` is now
the tested baseline for further recovery changes.

The [configuration patch](../recovery/twrp-working/README.md) changes only
`system/etc/init/hw/init.rc` and `twres/ui.xml`. All 4,208 remaining CPIO members
retain their payload and metadata, including the working executables,
libraries, touch setup, firmware and SELinux policy file. The kernel-free v4
header is unchanged except for the ramdisk size. A fresh local development-key
AVB footer passed signature and descriptor verification with flags zero,
recovery rollback index 1 and location 1; this does not establish OEM trust.
The [derived-image record](../research/twrp-working-defaults.json) separates
assembly checks from the successful device test. No other partition was
flashed, and no wipe or slot-change command was sent. Data decryption remains
unverified; Magisk has not been installed.

The baseline is the user-supplied `fix22ZJ-touchfix18` image, SHA256
`56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323`, preserved
unchanged alongside the derivative. It first booted after an authorized flash
to `recovery_a`, and the user confirmed its visible UI. Initial touch responses
took 5–10 seconds. Global permissive mode brought partial improvement;
disabling TWRP's action, button and keyboard vibration then made it much faster,
as confirmed by the user. Those two tested changes are now the recovery
defaults. Saved TWRP settings can override the vibration defaults; no saved
settings file existed before this test.

The supplied baseline had an unsigned AVB footer with a mismatched descriptor
hash, disclosed before its installation. Its initial policy reported global
`Enforcing` but contained eight permissive domains. The earlier
[installation record](../research/twrp-installed-recovery.json) preserves those
observations and both latency tests. This is an adaptation of supplied recovery
binaries, not a claim of a fresh source build or verified source provenance for
those binaries. Future changes should retain this device-tested baseline.

The preceding attempt used the complete Nezha tree from
[`antocorvo3000/twrp-xiaomi-17-series`](https://github.com/antocorvo3000/twrp-xiaomi-17-series/tree/4a35185d43782b4dd460a7f456d674c0976c0859/twrp_device_xiaomi_nezha),
pinned at `4a35185d43782b4dd460a7f456d674c0976c0859`. Its supplied kernel
matches the recorded stock kernel byte for byte, but temporarily booting its
assembled prebuilt root still produced a black screen with no selected USB
transport. That [trial](../research/twrp-upstream-bringup.json), the earlier
minimal recovery, and its unbooted timed diagnostic remain separate,
preserved experiments, not the selected baseline.

The user explicitly authorized **permissive SELinux for initial recovery
bring-up** on 2026-08-29. This keeps denial logging available while establishing
boot, display, touch, USB and recovery logs. Working enforcement is a later
milestone; do not disable SELinux in the kernel or change installed Android's
mode. The upstream policy's permissive domains are therefore an intentional
bring-up choice, not evidence of an enforcing recovery. Magisk is a possible
later step; it has not been installed or used to patch the phone. Existing
verified-boot, rollback, no-wipe and device-action authorization boundaries
still apply. The historical checks below describe earlier experiments, not the
installed working recovery.

**Normal build 66 produced a recovery image that passed the complete static
artifact sequence and the separate inventory check.** The 100 MiB image has
SHA256 `51478e22c6e99f7b604aa0ab1681d90adb84931f60d61b8e978e48a15ed1e791`.
Its kernel-free v4 layout and AOSP engineering-key AVB signature passed. The
actual archive contains the required `/etc` alias, unique secure properties,
and a policy with no permissive domains. All 44 executable interpreter paths,
1,074 library dependency edges and five recovery compiler-evidence roles passed
their checks. Both ramdisk inventories agree with the packaged contents.

The local candidate is `artifacts/twrp/nezha/build66/recovery.img`; that ignored
directory also contains its hashes and verification notes. The committed
[artifact verification record](../research/twrp-artifact-milestone.json) binds
the build, native inspection, compiler evidence and separate inventory reports.
This remains a static artifact milestone, not a tested rescue environment.
The user subsequently authorized rebooting the connected phone to its
bootloader and trying a temporary boot. The first upload succeeded, but the
bootloader rejected this kernel-free recovery with `Bad Buffer Size` before
TWRP execution was established. No partition was flashed. The separate
[hardware-attempt record](../research/twrp-boot-attempts.json) preserves that
failure and the private receipt identities; it does not rewrite the earlier
static verification record. Display, touch, boot-chain compatibility,
authenticated ADB and usable recovery-log access remain unverified.

The phone identifies as `nezha` / `2512BPNDAG`, running
`OS3.0.309.0.WPACNXM`. Its physical sales region has not been independently
established. Android reports locked boot properties, but the bootloader itself
positively reports `unlocked: yes`, `secure: yes`, slot `a`, and 100 MiB recovery
slots. The bootloader's unlocked result governed the authorized temporary boot.
Its error does not isolate which format, size or authentication check failed.
`fastboot boot` sends a supplied Android image unchanged; it does not supply
the missing stock kernel automatically. A separate wrapper containing the
matching stock kernel is therefore a testable format hypothesis, not a proven
boot method. Flashing, unlocking/relocking, wiping and slot changes remain
outside this authorization.

The second temporary trial combined the exact matching stock kernel with the
unchanged build-66 compressed ramdisk using pinned `mkbootimg`. The separate
96 MiB v4 wrapper has SHA256
`70c2d3ab2aee6c216a2c8d6a38d05ddeb76b1e3313a3602d3a2f1fdc1a155de2`.
A new local development key signed its fresh `boot` AVB descriptor; signature
and hash verification passed, flags remain zero, and the stock boot rollback
index `1769904000` and location zero were preserved. Its two AVB properties
retain the stock kernel's Android 16 / 2026-02-01 metadata, not a claim that the
custom userspace has that patch level. The stock Xiaomi fingerprint was not
copied. The original recovery and stock images remain unchanged.

The bootloader accepted that wrapper, but the phone reached stock Android:
`sys.boot_completed=1`, Zygote, SurfaceFlinger and system_server were present,
with no TWRP version property or recovery service. The authorized stock ADB
shell was UID 2000 and SELinux was enforcing. Those observations do not verify
recovery ADB or TWRP policy at runtime. A v4 bootloader can select the installed
`init_boot` ramdisk instead of the downloaded ramdisk; the exact Nezha loader
implementation is not established. The
[RAM-boot inspector](../scripts/inspect_twrp_ram_boot.py) checks the wrapper's
bytes and AVB digest offline but deliberately does not claim signature trust,
boot compatibility or runtime success. No flash command was sent; this does
not establish that the bootloader leaves all internal boot metadata unchanged.

The third trial used an explicitly inspected v3 wrapper, SHA256
`f8c2a3696036faea4401dacfabcde5ad092bb9b56adeffb9444f5d4adae52118`.
Public Qualcomm source at
[`9a7cebb3d43c569aeb70c86af5f1e91251923305`](https://github.com/CodeLinaro-mirror/la_abl_tianocore_edk2/blob/9a7cebb3d43c569aeb70c86af5f1e91251923305/QcomModulePkg/Library/BootLib/BootLinux.c#L1231-L1284)
supports selecting the downloaded ramdisk on that path while retaining the
installed vendor ramdisk and DTB. This is source evidence, not identification
of the proprietary Nezha loader. V3 omits the separate vendor bootconfig, so
the wrapper carries its eight exact stock declarations as a 269-byte command
line. Pinned init imports those `androidboot.*` parameters normally, but its
early parallel-module switch reads only bootconfig and can fall back to serial
loading. No security override or force-normal-boot marker was added.

The bootloader accepted v3, but Android returned afterward. Unlike the earlier
result, the latest `SYSTEM_LAST_KMSG` entry provides a concrete startup error:
first-stage init could not mount `/proc`, `/sys`, `/mnt`, `/debug_ramdisk` and
`/second_stage_resources` because the mount-point directories were absent. It
aborted at about 0.256 seconds and requested a bootloader reboot. The saved log
has some corrupted characters; its raw bytes remain private and hash-bound in
the attempt record. Direct pstore access was denied to the stock shell, but
the bounded Android DropBox read succeeded. This is access to a previous
kernel log, not proof of TWRP's own logging or authenticated recovery ADB.

The dedicated recovery archive omits generic initramfs directories normally
supplied by the companion `init_boot` ramdisk. The next RAM-only wrapper can
provide the canonical seven empty root directories: `debug_ramdisk`, `dev`,
`metadata`, `mnt`, `proc`, `second_stage_resources` and `sys`. Init creates
the mounted children itself. No stock executable, debug marker, policy,
property file or extra init script is needed for this measured failure.

The fourth trial supplied those directories in a deterministic 1,037-byte
legacy LZ4 member before the unchanged original compressed ramdisk. The
wrapper SHA256 is
`4da77ae4bd8e5a30d036b23ae2e8939fada75023a16588a6f4456fce8e866093`.
An independent native decompression matched the 1,024-byte directory archive
followed by the complete original build-66 CPIO. The prefix uses the Linux
generator's directory link-count convention of two, rather than TWRP
mkbootfs's one; the kernel does not apply its regular-file hardlink handling
to directories. The [prefix helper](../scripts/twrp_ram_boot_scaffold.py)
and inspector check the exact bytes and unchanged original suffix.

This fixed the measured first-stage failure. The saved kernel log shows vendor
modules loading, `/sepolicy` loading, SELinux entering enforcing mode, and
`init second stage started!` at about 18.496 seconds. Init then requested a
bootloader reboot. The phone remained on slot `a`; a diagnostic `fastboot
reboot` returned it to stock Android to collect the saved log. TWRP's UI and
authenticated recovery ADB were not verified at that checkpoint. The fatal
cause was not identified in this log: kernel messages explicitly report
hundreds of init lines suppressed by rate limiting.

The fifth trial added only `printk.devkmsg=on` to the header command line,
preserving the kernel and complete ramdisk bytes. Its SHA256 is
`74b1cbad15dfefcad96b0f77dbb340ae4df9461d70e28ad19a144308bb0c1bb1`.
This parameter removes the `/dev/kmsg` writer rate limit for already permitted
writers; it does not grant log access or change SELinux, ADB authentication,
AVB flags or rollback metadata. It can increase log volume. The fresh saved
kernel log shows 426 modules loaded, enforcing policy, second-stage init and
the TWRP build identity, then an `ENOENT` mounting tmpfs on `/apex` followed by
`InitFatalReboot: signal 6`. The canonical archive had no `/apex` directory.

BootReceiver published that trial's `SYSTEM_LAST_KMSG` entry after Android
reported `sys.boot_completed=1`. An initial read therefore captured the older
trial's log. Both receipts are retained, but only the entry at
`2026-08-29 00:22:41 America/New_York`, verified newer than the diagnostic stock
reboot, supports the fifth trial's diagnosis. Future collection must check
entry freshness instead of assuming the newest available entry is current.

The sixth trial adds only the empty `/apex` directory to the scaffold. Its
1,551-byte LZ4 prefix precedes the unchanged original compressed ramdisk;
native decompression, independent inspection and explicit-key AVB verification
passed. The 96 MiB image has SHA256
`8278aa15d2aa21e5553a332787580716e3d7b43b88ad505c73e8141e37dd9e7f`.
Inspection requires the explicit `--header-version 3 --scaffold --init-logging
--apex` variant. This verifies an empty directory, not working APEX packages.

The bootloader accepted the sixth trial. Twenty USB presence checks spanning
about 58 seconds found neither ADB nor fastboot, and a host USB descriptor
check found no Android device. This does not establish that TWRP started or
that it crashed. No further reboot was sent; the phone's screen state was
requested before deciding the next device action. The recorded current
runtime, display, touch and authenticated recovery ADB remain unresolved.

The user subsequently reported a black screen. Fresh checks still found
neither the selected ADB/fastboot transport nor a matching Android USB device.
This rules out a user-observed working UI at that time, but it does not identify
a kernel, coldboot, recovery-service or graphics failure, or prove that stock
Android cannot boot. With no USB transport, the next device action requires a
physical restart. Xiaomi documents Power + Volume Down for fastboot and
holding Power for more than ten seconds to force an unresponsive phone to
restart in its [support instructions](https://www.mi.com/uk/support/faq/details/KA-550626/).
Preserve any fresh saved kernel log before sending the next temporary image.

The user then returned the phone to Android and confirmed that no recovery UI
had appeared at any point. Authorized ADB verified the same stock build and
slot `a`, with `sys.boot_completed=1`. DropBox contained zero entries throughout
the bounded collection, so no previous-kernel log was available through that
route. BootReceiver logcat entries had a different wall-clock date from the
current phone clock; the cause of the missing capture was not established.
The raw observations were preserved without reusing an older trial's log.

The subsequent source audit identified another missing root mount point:
the packaged recovery RC mounts configfs on `/config` without creating the
directory. Neither the canonical archive nor the sixth trial's prefix contains
it. The audit covered all eight mount commands and their directory dependencies
in the main recovery RC and its present direct imports. Other mount points
have an existing archive entry or an earlier creator; for example, cgroup
setup creates `/acct`. Init can suppress the missing-directory error from an
RC mount command, so absence of a normal-severity error would not clear this
defect. ADB host authentication happens after USB enumeration and cannot by
itself explain the absence of a USB device.

A separate candidate adds only the empty `/config` directory. It is stored
locally at `artifacts/twrp/nezha/ramboot72-config/boot.img`, SHA256
`8cbc355d68750c32f1b3ba4dec1953732bd32a3924731553b16204a699ee730f`.
Its native decompression, independent inspection and explicit-key AVB
verification passed. The inspector requires `--header-version 3 --scaffold
--init-logging --apex --usb-config`; all earlier variants remain separate and
unchanged. The original **unbooted preparation checkpoint** remains a separate
historical record. It does not establish that this is the only runtime problem
or that the image's USB setup works.

The seventh trial subsequently uploaded and temporarily booted that image.
Fastboot accepted it, but twenty presence checks spanning about 58 seconds
again found neither ADB nor fastboot, and the USB descriptor scan found no
Android or Qualcomm device. Adding `/config` alone has not produced an
observable USB transport. TWRP UI, configfs mounting, authenticated recovery
ADB and the runtime cause remain unverified. The user was asked to return to
fastboot promptly if the screen remained black so another saved-log collection
could be attempted.

The user subsequently returned the phone to fastboot. Fresh checks positively
identified the selected `nezha`, slot `a`, `is-userspace: no`, `unlocked: yes`
and `secure: yes`. One authorized diagnostic `fastboot reboot` was accepted,
and authorized ADB returned on the same stock build and slot. The original
trial's absent-USB observation remains unchanged; this later stock return
does not establish which recovery stage ran or whether its UI or ADB started.

Read-only collection began at phone uptime 8.13 seconds without waiting for
boot completion or filtering candidates by date. Within a 90-second host
monotonic budget, 80 DropBox index observations through 84.929 seconds of
elapsed capture time found no `SYSTEM_LAST_KMSG` snapshot or candidate. A
normal `SYSTEM_BOOT` entry did publish, so this was not an entirely empty
DropBox. The phone clock corrected forward between observed uptimes of about
18.95 and 29.84 seconds. That correction does not establish why the kernel log
was missing, and no stale log was used to diagnose the recovery trial.
The final stock observation had `sys.boot_completed=1`, `sys.boot.reason=bootloader`
and uptime 94.05 seconds. No partition-write, flash, wipe, unlock/relock or
slot-change command was sent. Recovery-stage progress, UI, authenticated
recovery ADB and the failure cause remain unverified for this trial.

## Source and build isolation

The selected experimental source is
[TWRP-Test Android 16](https://github.com/TWRP-Test/platform_manifest_twrp_aosp/tree/d2188a9345857fb078c391e8cb3e259a21e941e5),
manifest commit `d2188a9345857fb078c391e8cb3e259a21e941e5`. This is not an
official TeamWin Nezha release. The manifest's default AOSP revision is
`android-16.0.0_r1`, with the fork's recovery, build and vendor projects.
Every fetched project must be recorded at its resolved commit before building.
Do not substitute a current branch tip for that recorded snapshot.

The initial sync has completed. All **391 Linux-selected projects** passed
HEAD, origin and clean-worktree checks, including the 36 independently pinned
GitHub overrides and 355 locally verified AOSP tag commits. The only excluded
project from the 392-project raw manifest is its Darwin-only Bazel prebuilt.
The [resolved source lock](../research/source-snapshots/twrp-16.0-linux-20260828.xml)
has SHA256 `e967ec0392a3438f4706278e9e77b0810c4401a36f0e64c211a1e5c6e5bfb051`.
The [source verification record](../research/twrp-source-sync.json) contains
the host, tool-version probes and receipt hashes. Source-sync success is
separate from recovery compilation and device testing.

The [supplementary source configuration](../config/twrp-dependencies.json)
separately pins AOSP `system/bpf` at
`4447acd742bf443f9088c300bd69f96ede8eaeb1` from `android-16.0.0_r1`, providing
the BPF defaults required by the selected Connectivity headers. It also pins
the matching NetworkStack, APF and libpcap projects so the retained Connectivity
definitions use their real JNI dependencies. Additional projects provide native
bridge support, selected platform test helpers, Skia and its missing codec/font
providers, Java signing tools and shared audio libraries. NFC, Wi-Fi and AVF source
provides the real modules required by the global SELinux service-fuzzer
registry. Registering those modules does not install their services in recovery
or establish support for the phone's NFC, Wi-Fi, virtualization or decryption.
The SELinux binding validator remains enabled and its registry is unchanged. The
[helper](../scripts/twrp_dependencies.py) preserves the immutable 391-project
Repo snapshot; these additions are not a replacement lock or proof of a complete
recovery dependency graph.

The [build-attempt ledger](../research/twrp-build-progress.json) records actual
outcomes and the exact source, control bundle and log hashes for each attempt.
Earlier failures remain in that record after a target revision. Generated
theme resources alone do not establish that a recovery image was built.

Graph 49 completed Blueprint generation and entered legacy Make processing,
which rejected missing required modules. That is a partial milestone, not a
successful full graph or compiled image. Its first Kati pass also created
`clean_steps.mk`; subsequent runs must preserve and verify that recorded state
and review newly introduced CleanSpec commands before allowing Kati to run.
Deleting the state to suppress clean steps is not part of this workflow.

Graph 51 is the first successful full graph: Soong, legacy Make, packaging-rule
generation and Ninja's `nothing` target completed with exit zero. The source
and prepared revision remained verified afterward, and no sandbox fallback was
reported. The exact combined, Soong, Make and packaging Ninja files are recorded
in the ledger. All 50 earlier failures remain recorded. This checkpoint does
not contain a compiled recovery image or establish any phone behavior.

The native recovery profile now omits four unrelated continuous CI archive
tasks, preserving their original bodies for other profiles and retaining the
strict missing-module checks. It does not claim those tests passed. The
post-graph cleanup check preserved all 1,248 existing clean-step IDs; all 325
preflight and 325 postflight checks passed without resetting the saved state.

Build 52 then entered actual recovery compilation and reached step 18,042 of
19,919 before stopping on one compiler error: the GUI's optional OZIP helper
referenced an unconfigured decryption-key macro. No recovery image was produced.
The source revision and all 325 cleanup-state checks remained valid afterward.
Patch 28 guards that unavailable feature and propagates failure through the
existing GUI status without changing ordinary ZIP installation or supplying a
key. A resumed compile must establish whether further failures remain.

Graph 53 passed after that fix, and build 54 reused the previous outputs with
1,880 remaining steps. It stopped at step 438 on 21 unused-parameter errors
across six recovery source files and one malformed default version macro.
Patches 29 and 30 address those two causes without disabling warning checks,
enabling optional features or changing existing recovery operations. No image
was produced by that attempt; the source and cleanup-state checks still passed.

Graph 55 passed with both fixes, and build 56 compiled the affected C++ files.
It then stopped on one unused descriptor parameter in `tarWrite.c`. Patch 31
marks that parameter intentionally unused without adding an I/O operation or
changing the deferred flush behavior. This fix still requires a new build;
build 56 produced no image and passed the subsequent source and cleanup checks.

Graph 57 passed, and diagnostic build 58 compiled `tarWrite.c` and linked both
the recovery executable and recovery ADB. It completed the runnable work at
step 1,444 of 1,450, stopping only because the compiled recovery policy declared
seven permissive domains: `adbd`, `fastbootd`, `init`, `logd`, `postinstall`,
`recovery` and `ueventd`. The existing user-build SELinux validator rejected
that policy. No recovery image was produced; the failed policy, unfiltered
domain list and exact input hashes are retained in the build ledger. The next
source change must correct those declarations, not disable the validator or
assume the resulting policy works on the phone.

Patch 32 passed graph 59. Normal build 60 then regenerated and installed a
recovery policy with no permissive declarations, passing the unchanged native
user-build check. Packaging stopped later because its recipe touched
`linkerconfig/ld.config.txt` without first creating the parent directory. This
attempt produced no recovery image. The recipe needs to handle a clean output
tree; manually creating a directory in this build's output would not fix that
requirement. The source and all 325 cleanup-state checks passed afterward.

Patch 33 creates that directory in the packaging recipe. Graph 61 and normal
build 62 then passed, producing `recovery.img` with SHA256
`65141f46297f7aeee41edd877ccc1ba4df4896b206fae69bd8719699cce346d3`.
The image is 104,857,600 bytes; its embedded compressed ramdisk matches the
separate build output. The first artifact run rejected Android's empty CPIO
trailer mode `0755`; the narrow inspector correction below preserves that
failed run and does not modify the image.

Inspection of the same decompressed archive then found two equal duplicate
assignments (`ro.secure=1` and `ro.adb.secure=1`). A separate ELF inventory
parsed 159 ELF files and 1,074 library dependency edges without missing or
ambiguous library candidates, but found 44 unresolved interpreter paths:
42 refer to `/system/bin/linker64` and two to
`/system/bin/bootstrap/linker64`. Neither loader is packaged. The archive also
lacks `/system/etc/ld.config.txt`; its `/linkerconfig/ld.config.txt` is only
the empty placeholder created by the recipe. These are incomplete packaging
results, not runtime success. The property and ELF checks remain unchanged;
source fixes and a new normal build must precede another full artifact check.

The target now uses the generated user-build secure properties, explicitly
packages `linker.recovery` and `ld.config.recovery.txt`, and installs the
bootstrap alias through a device `install_symlink` module. Graph 63 verified
the actual generated module and installation rules. Normal build 64 then
completed with image SHA256
`8b5a4dcead011b54c25c89f8f7e5c1b5f1b8c083606f91c9a69383c2a8d84aef`.
It is still 104,857,600 bytes. The source revision and all 325 cleanup-state
checks passed, and the earlier failed image and reports remain preserved.

The build-64 artifact run passed bounded decompression, CPIO structure and
secure-property checks. Its inventory parsed 160 ARM64 ELF files and 1,074
unique dependency candidates, with no missing dependency candidates and all
44 interpreter targets resolved. It stopped on one global SONAME collision
between `system/bin/linker64` and `system/lib64/ld-android.so`. Pinned bionic
`99926c766ef7f121950611f047dba4769a25226c` deliberately gives the linker this
SONAME, defines the separate link-time ABI stub, and registers the running
linker before resolving unqualified dependency names. Both files must remain.
This was a limitation of the inventory classification; it did not prove
runtime symbol compatibility. The original failed run is retained. The reviewed
successor recognizes only this exact loader/stub pair under the original path,
architecture, ELF-type, dependency and interpreter constraints. It preserves
the duplicate SONAME metadata and rejects ambiguous library resolution. The
policy analyzer and compiled ADB checks were not reached by that failed run.

The next build-64 artifact run passed the ELF inventory and stopped at a real
staging/archive mode difference for the pinned UI XML. Source review of
`mkbootfs` and `fs_config` established three exact packing rules: `twres/ui.xml`
changes from `0755` to `0644`, the authored `init.recovery.qcom.rc` from `0644`
to `0750`, and `system/bin/logd` from `0755` to `0550`. Their contents match.
The verifier now checks those exact mode policies; it does not chmod outputs
or pretend their staging and packed modes are equal. The original failed
report remains unchanged.

The same inspection found `/etc` absent from both staging and the archive.
The target change in commit `2ced55ff186e5d361172c8ef22b19fbeb9efbae4` uses the
existing `BOARD_RECOVERY_IMAGE_PREPARE` hook to establish
`/etc -> /system/etc` before packing and signing. It rejects conflicting paths
and refreshes both original inventories, including the name list's checksum.
Graph 65 verified the rendered recipe; normal build 66 completed all 25
incremental steps and the engineering-signature check. All 33 source patches,
272 supplementary projects and 202 source-selection rules remain unchanged.
All 325 cleanup-state checks passed before and after the graph and after the
build. No source checkout, saved clean state or prior image was deleted.

The complete artifact run used the actual build-66 receipt and image, with a
new immutable verifier bundle. Bounded decompression produced a 57,758,208-byte
CPIO archive with SHA256
`26e00b45e58c82abca9c58bed226248645c6ced543469ff4d56be9fee2089a9e`.
It contains 777 entries: 28 directories, 541 regular files and 208 symlinks.
The ELF inventory parsed 160 ARM64 files with no unresolved library or
interpreter paths. The native policy analyzer returned zero with unfiltered
empty stdout and stderr for the exact packaged policy. The bounded LLVM reader
and compile-command checks passed for `init`, `libtwrpinstall`, `minadbd`,
`adbd_main` and `adbd_wifi`; the persisted capture, image, object and installed
file bindings also passed. These checks do not attest compiler execution or
prove runtime authentication, labeling, relocation or daemon startup.

The separate inventory check compared every regular-file hash and symlink
target with a fresh staging capture. All 778 name-list entries and 537 checksum
entries match the original producer's census and exclusions. The name list
includes its observed `.` root; `mkbootfs` omits that header, so no synthetic
entry is added to the archive count. The verified `/etc` alias resolves both
original cgroup/profile JSON lookups before init actions. Runtime cgroup mounts
and logd behavior still require a device test.

The [community reference review](twrp-community-references.md) records the two
Nezha trees supplied during bring-up at exact commits. Their USB and touch
details are useful comparison inputs, but their reported hardware results are
not tests of this stock package. Neither tree is imported wholesale or used to
replace the pinned platform, stock layout, authentication or validation checks.

The existing Apple Container VM remains the sole writer of the ext4 volume.
TWRP source is separate at `/work/twrp-nezha`; its output belongs below
`/work/out/twrp-nezha`, with reports under `/work/validation/twrp-nezha`.
The existing `/work/evolution` source and output must remain untouched. No
home directory, credentials, phone evidence or stock archive is mounted into
the guest for this work.

The initial preflight verified Ubuntu 24.04 ARM64, case-sensitive ext4,
546.4 GiB free in the volume, 125.7 GiB guest RAM and the trusted Rosetta
execution probe. The host had about 1.1 TiB available. Repo was verified at
`b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77`, and initialization preserved its
signature checks. These are observations from this attempt, not permanent
capacity guarantees or proof that all TWRP host tools execute correctly.

## Local workflow

This section records the older source workflow. The preserved `make twrp-plan`
command below had its former meaning; use `make twrp-source-plan` for the
current source-plan entry. The remaining commands require their recorded pins
and environment checks and are not a working76 rebuild recipe.

Preview the workflow from this repository without contacting the phone or
starting a source operation:

```sh
make twrp-plan
python3 scripts/twrp_dependencies.py plan
make recovery-logs-plan
make test
```

Run real source/build operations only from a generated, versioned control
bundle in the existing verified Linux VM (or an independently verified native
Linux x86-64 host). The guest-side commands are:

```sh
python3 scripts/twrp_workspace.py freeze --host-mode apple-rosetta
python3 scripts/twrp_dependencies.py fetch --host-mode apple-rosetta
python3 scripts/twrp_build.py prepare --host-mode apple-rosetta
python3 scripts/twrp_build.py graph --host-mode apple-rosetta --variant user --jobs 16
python3 scripts/twrp_build.py build --host-mode apple-rosetta --variant user --jobs 16
```

`freeze` records an already completed sync; it does not fetch sources. `init`
and `sync` are for a new isolated checkout. After a snapshot exists, repeat
source operations verify it instead of following moving branches. `prepare`
stages the authored target and exact reviewed patches, and refuses unrelated
changes. The build uses `out-twrp` as a source-relative alias to the isolated
output directory; source, output and caches remain in ext4. No phone command
or automatic flashing step is part of these tools.

For a diagnostic compile, the `build` action accepts `--keep-going`. This adds
an explicit `-k0` to the recorded Soong command so Ninja can collect independent
failures in one run. Errors still fail the build; source, sandbox, image and
engineering-signature checks remain enabled. The flag does not allow blocked
dependencies or failed graph generation to proceed. After a successful
diagnostic run, repeat `build` without the flag to obtain the normal receipt
required by artifact verification. The default command remains unchanged.

For an already prepared checkout, run the following from the **new versioned
control bundle** instead of repeating `prepare`. Set `TWRP_PREVIOUS_CONTROL_ROOT`
to the absolute path of the exact previous bundle matching the prepared receipt;
an arbitrary older bundle or a mutable `latest` alias is not interchangeable.

```sh
python3 scripts/twrp_dependencies.py fetch --host-mode apple-rosetta \
  --previous-control-root "${TWRP_PREVIOUS_CONTROL_ROOT:?set the exact previous control bundle path}"
python3 scripts/twrp_build.py revise --host-mode apple-rosetta \
  --previous-control-root "${TWRP_PREVIOUS_CONTROL_ROOT:?set the exact previous control bundle path}"
```

`revise` verifies the existing target and patch queue before accepting reviewed
target changes, supplementary additions and appended source patches. Existing
patch entries must remain an exact unchanged prefix. A first touch must match
the frozen Git base; an explicitly linked successor must name the immediately
preceding patch and match its exact postimage. The
[linear patch-chain contract](twrp-linear-patch-chains.md) requires complete
forward and reverse scratch rehearsal and exact bytes, blobs and modes at every
boundary. All patch contexts are checked before any source or target change. The tool
archives the previous receipt, patch payloads, source preimages and changed
target files under the report directory's `build-revisions`, while preserving
the base snapshot, output and caches. A partial application retains its backups
and old receipt and blocks automatic retry. Existing outputs retain their
earlier provenance; the new receipt marks the revision as not yet built or
validated. Then run the separate `graph` and `build` commands above. Implicit
overlap, changed source pins and unapproved changes to the target file set are
rejected; unrelated local edits are not adopted. Supplementary source patches must match the exact active previous
bundle during `fetch`; fetching never applies a proposed patch. The
[supplement patching guide](twrp-supplement-patching.md) describes those checks.

Adding a reviewed file at the target root requires an explicit allowance on
`revise`; the default still requires the same file set. For the new bootstrap
link definition, run from the new control bundle with:

```sh
python3 scripts/twrp_build.py revise --host-mode apple-rosetta \
  --previous-control-root "${TWRP_PREVIOUS_CONTROL_ROOT:?set the exact previous control bundle path}" \
  --allow-target-addition Android.bp
```

Every added root filename must be named once, and the allowed names must
exactly match the new control inventory. Removals, nested additions, existing
files, directories and symlinks remain rejected. The helper archives the
verified prior absence and the controlled new bytes, then creates the file
exclusively without following directory links. It rechecks the complete
target before publishing the revised receipt. A failed creation or later
failure preserves partial files and the old receipt for inspection; it does
not delete, adopt or silently retry them. This allowance applies only to
source revision, not to graph, build, artifact or phone validation.

The default build variant is `user`, which retains init's compile-time
enforcement behavior. Explicit `userdebug` builds remain diagnostic experiments;
their init can accept a permissive bootconfig. Neither build variant should
be described as enforcing on the phone before a device test.

The [patch queue](../patches/twrp/README.md) removes permissive debug `su`,
automatic root ADB and a source-file truncation during environment setup. It
also requires host authentication in recovery adbd, including on unlocked or
debuggable devices. The ordinary Android adbd behavior is unchanged. A trusted
host key and its recovery handling must still be provided and validated; no
host private key or stock key is bundled. The [ADB readiness record](twrp-adb-readiness.md)
explains the authored secure-user startup request and USB transport restriction,
along with the remaining authorized public-key input and log-access design.
No compiled artifact or device test has established that those paths work.

The queue also disables the separate unauthenticated minadbd transport for
this profile. Both its standalone entrypoint and TWRP's sideload caller return
an error before starting the transport or changing USB state. The caller guard
prevents a disabled daemon from stranding ordinary adbd behind an indefinite
USB-readiness wait. This is a compile-time restriction, not authenticated
sideload support; the selected flags and compiled behavior still need checking.
Other startup, installer and persistent-write paths remain outside this gate.

The [log collector](recovery-logs.md) and
[image inspector](../scripts/inspect_twrp_image.py) run separately. The inspector
also passed a read-only check against the hash-verified factory recovery image;
its structural result does not authenticate that input or validate TWRP.

For a compiled `ramdisk-recovery.cpio`, the separate
[ramdisk inspector](../scripts/inspect_twrp_ramdisk.py) validates a single bounded
newc archive without extracting or executing it. It checks the packaged secure
property literals, critical file permissions and ARM64 init/adbd ELF headers,
and records the policy and executable hashes. It does not establish effective
runtime properties or resolve the complete ELF library graph. Bind that CPIO to
the compressed ramdisk in the inspected image, run the real policy analyzer,
and inspect every packaged ELF dependency before accepting a build candidate.

The archive inspector accepts the empty trailer with mode `0` or permission
bits `0755`. The pinned Android `mkbootfs` applies directory `fs_config` to its
zeroed trailer stat, producing the latter without file-type bits. This narrow
format correction retains the canonical trailer name, empty payload, ownership,
link, device, checksum, alignment and bounded trailing-zero checks. It does not
allow arbitrary trailer modes or concatenated archives. The
[Linux initramfs format](https://docs.kernel.org/driver-api/early-userspace/buffer-format.html)
requires an empty trailer payload but does not require its mode to be zero.

## First target and limits

The factory contract requires a dedicated A/B recovery image: Android boot
header v4, no kernel, an LZ4 ramdisk, and a 100 MiB package partition limit.
The kernel remains in `boot`; DTBs and the first-stage module collection
remain in the matching `vendor_boot`. The [earlier recovery review](recovery-plan.md)
and [factory boot contract](factory-boot-contract.md) record the measured
inputs and distinguish package geometry from this phone's unmeasured capacity.

The first target is a **compile-only experimental recovery**, initially focused
on display, USB/ADB and diagnostics. No decryption, touch, backup, restore,
installation or boot success is implied. In particular, the touchscreen
drivers also need the matching vendor DLKM and firmware; compiling the UI
does not establish that the touchscreen will work.

Do not import a community tree's permissive policy, missing-dependency flags,
fake future security patch levels, foreign board identity or vendor_boot
layout. Retain SELinux, signature, ELF and image-size checks. Recovery must
not reset Android's boot-state properties to hide the state of the device.

A restricted fstab is **not a write lock**. Upstream TWRP includes boot-control,
script, settings and other write paths outside ordinary filesystem mounts.
Those paths must be audited before any boot test. Neither the absence of data
decryption nor a successful image build makes it safe to use on personal data.

## Acceptance sequence

1. Pin and synchronize the independent platform, register the Nezha target and
   compile with all relevant build checks retained.
2. Inspect image layout, included services, authentication and compiled SELinux
   policy. Record the image hash and distinguish an engineering AVB signature
   from a key trusted by this phone.
3. Only after a separately authorized device test: validate display, touch,
   USB, authenticated ADB and bounded log capture, with a verified return path.
4. Add and test storage and installation support separately. Preserve the real
   F2FS/wrapped-key encryption and Virtual A/B state; do not upgrade persistent
   keys, format data or merge snapshots as a way to make a test pass.

The phone has not been rebooted, unlocked, flashed or otherwise changed by this
bring-up. An ordinary `fastboot boot recovery.img` is not an established test
method for Nezha's kernel-less dedicated recovery.

## Original recovery review

TWRP is now an independent bring-up track, at the user's request; it does not
wait for a complete Evolution X ROM. Follow the [active TWRP work](twrp-bringup.md)
for source, build and test status. The observations and machine-readable record
below preserve the earlier review checkpoint, before a TWRP target existed.

A tested recovery can help restore an unbootable Android system,
but **it cannot prevent bootloader corruption or start without a working boot
chain**. Nezha's recovery is not self-contained: the captured image has no
kernel. Keeping recovery intact therefore does not protect against damage to
the bootloader, required boot images, partition tables or hardware-backed
security state. This follows the [AOSP bootloader responsibilities](https://source.android.com/docs/core/architecture/bootloader)
and [dedicated A/B recovery design](https://source.android.com/docs/core/architecture/partitions/generic-boot).

This is an engineering plan, not a recovery release. At the review checkpoint,
no TWRP target had been registered and no recovery build or device test had
passed. No phone change is authorized by that review. The existing Evolution source and output
must stay intact. The [machine-readable record](../research/recovery-plan.json)
separates source observations, factory-package evidence and future tests.

The new China fastboot package has SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Its existing extraction, AOSP boot inspection and full selected AVB-chain
receipts were checked again for this review; no firmware was re-extracted or
executed. The selected chain and Qtvm check pass without verification bypasses.
The supplied archive's origin and an independent OEM trust root remain
unverified. That result is separate from the modified Xiaomi.eu package's
retained AVB failures.

| Image | Verified package contents | Recovery requirement |
| --- | --- | --- |
| `boot` | Header v4; 39,963,136-byte kernel; no ramdisk | Keep the matching kernel available through the boot chain |
| `init_boot` | Header v4; generic ramdisk; no kernel | Preserve the generic first-stage init dependency |
| `vendor_boot` | Header v4; 4 KiB page field; vendor ramdisk and DTBs | Preserve Nezha's DT selection and required module dependencies |
| `recovery` | Header v4; 30,407,261-byte compressed ramdisk; no kernel | Build a dedicated recovery ramdisk, not a replacement vendor_boot layout |

The recovery image is 104,857,600 bytes (100 MiB), with SHA256
`a6f2c77608026fcfe6221e5191c501b0ac880658f76c55231879ed198ce8a0f9`.
Image length is not a live partition measurement. The separately checked
package GPT, rawprogram and partition XML agree on 100 MiB for both recovery
slots, 96 MiB each for boot/vendor_boot, 8 MiB for init_boot, and 32 MiB for
DTBO. The DTBO file is only 22 MiB, demonstrating why file lengths cannot
substitute for partition extents. These are package-derived limits, not a
measurement of this phone. GPT growth placeholders remain unresolved; no
flashable GPT layout is admitted. The independent analysis receipts are
bound in the recovery record.
The recorded recovery chain has rollback location 1 and index 1;
`vbmeta_system` uses location 2. Keep those roles distinct from the values in
a generic recovery tree. The phone's stored rollback counters and actual
bootloader authorization remain unresolved.

The later [factory ramdisk comparison](factory-boot-contract.md) confirms that
the captured recovery ramdisk and its payloads match the earlier input. Its
two recovery fstabs still contain ext4 and legacy ICE/wrapped-key settings
that differ from the normal EROFS/FBE layout; they are evidence to reconcile,
not a ready-to-use TWRP decryption configuration. The
[module-provider audit](module-provider-audit.md) supplies matching captured
CRC candidates. The later [boot-stage audit](module-stage-closure.md) accounts
for the recovery list's 435 rows and 424 unique requested modules. Its hard
dependency closure contains 426 modules, adding `hdcp_qseecom_dlkm` and
`smmu_proxy_dlkm`; all 20,345 recorded CRC expectations have matching kernel
or local predecessor candidates, with no missing hard path or dependency
cycle. One soft dependency names the absent `phy-msm-snps-hs`; that alone does
not establish a required-import failure, and no substitute was invented.
This uses the captured inputs and pinned loader semantics. The stock loader's
source identity, successful loading, signature admission and TWRP behavior
remain unverified.

The recovery build should retain the separate A/B recovery arrangement,
header v4, LZ4 ramdisk format and exclusion of the kernel from recovery.
It needs a reviewed module closure for display, touch, storage, USB and
security services. Preserve the [ZRAM provider and loader contract](zram-module-plan.md):
vendor and GKI modules with the same basename are not interchangeable. Do not
assume a ramdisk-only recovery image supports temporary boot, or infer a
safe test procedure from another device's instructions.

Two first-hand community trees are useful, but neither is admitted wholesale:

| Reference | Pinned revision | What to retain as research |
| --- | --- | --- |
| [MissMyTime SM8850](https://github.com/MissMyTime/twrp_device_sm8850/tree/17525a886e43c26c350fb3db9b260c55e4360dc8) | `17525a886e43c26c350fb3db9b260c55e4360dc8` | Nezha-specific ramdisk layout, secure-element routing, manual decryption and USB work |
| [antocorvo3000 Xiaomi 17 series](https://github.com/antocorvo3000/twrp-xiaomi-17-series/tree/4a35185d43782b4dd460a7f456d674c0976c0859) | `4a35185d43782b4dd460a7f456d674c0976c0859` | Reported boot/touch results and a synthetic-password authentication fix to review independently |

MissMyTime's [Nezha BoardConfig](https://github.com/MissMyTime/twrp_device_sm8850/blob/17525a886e43c26c350fb3db9b260c55e4360dc8/device/xiaomi/nezha/BoardConfig.mk)
matches the dedicated recovery layout, but relaxes missing-dependency,
duplicate-rule, ELF-copy and plugin checks. Its included
[recovery policy](https://github.com/MissMyTime/twrp_device_sm8850/blob/17525a886e43c26c350fb3db9b260c55e4360dc8/device/xiaomi/nezha/sepolicy/recovery.te)
declares permissive recovery and vibrator domains. BoardConfig also uses a
fake platform version and security patch dates in 2099. These settings are
not acceptable inputs to this project. The device's
[vold work](https://github.com/MissMyTime/twrp_device_sm8850/blob/17525a886e43c26c350fb3db9b260c55e4360dc8/patches/nezha/README.md)
addresses installed-system KeyMint parameters and persistent key upgrades;
its safety and correctness need independent tests before any port. One build
guide sentence puts the kernel in vendor_boot, contradicting that tree's own
Nezha BoardConfig and the stock headers above; use the measured arrangement.

The other tree's [active board settings](https://github.com/antocorvo3000/twrp-xiaomi-17-series/blob/4a35185d43782b4dd460a7f456d674c0976c0859/twrp_device_xiaomi_nezha/BoardConfig.mk)
retain SM8750 identity, disable a separate recovery target, move recovery
resources into vendor_boot, and assign `vbmeta_system` rollback location 1.
Its init fstab labels metadata as ext4. Those are not Nezha defaults to copy.
The maintainer [reports boot and touch but unconfirmed decryption](https://github.com/antocorvo3000/twrp-xiaomi-17-series/blob/4a35185d43782b4dd460a7f456d674c0976c0859/twrp_device_xiaomi_nezha/README.md),
with StrongBox removed and Gatekeeper switched away from SPU operation.
Neither change establishes the correct security route for this phone. The
AES-GCM patch adds authentication-result checks; evaluate it against the
chosen source base with valid, truncated and corrupted synthetic fixtures,
without using a real user's keys or disabling authentication.

TeamWin's [compilation guide](https://twrp.me/faq/howtocompiletwrp.html) still
links its Android 12.1+ minimal manifest. That manifest is pinned here at
`6dc117d9cbd08430daa16db2013560e1c4017fa8`; official recovery source is
`5c3d206a5eeb3d446bcda8248a405a4b278bab5c` on `android-12.1`.
MissMyTime instead documents the experimental
[TWRP-Test Android 16 manifest](https://github.com/TWRP-Test/platform_manifest_twrp_aosp/tree/d2188a9345857fb078c391e8cb3e259a21e941e5),
pinned at `d2188a9345857fb078c391e8cb3e259a21e941e5`. These are different
source bases. Their full transitive project revisions have not been resolved
or synced here. Nezha was not listed in [TeamWin's Xiaomi device index](https://twrp.me/Devices/Xiaomi/)
when inspected on 2026-08-27; a community claim is not an official support or
local compatibility result.

Use the Nezha-specific layout as a reference for an isolated recovery product
and a small reviewed patch queue. Do not run either repository's setup,
patching or installer scripts in the Evolution checkout. Resolve the chosen
manifest completely before building, with its own source and output paths,
the existing host checks and no concurrent writer on the ext4 volume.

The work proceeds in these stages:

| Stage | Required result before proceeding |
| --- | --- |
| Independent local recovery integration | Factory-derived fstab and size constraints; exact boot/module inputs; strict build, ELF, VINTF, SELinux and AVB checks; inspected recovery output |
| Separately authorized boot test | Verified boot chain and return plan; display/touch and USB/ADB tests; no automatic data decrypt/format, slot changes or snapshot mutation |
| Separately authorized encrypted-storage test | Correct secure services, metadata and CE/DE access; credential failure stays a failure; no persistent key upgrade; Android remains able to access its data afterward |
| Separately authorized rescue validation | Proven backup/restore scope, internal-media coverage, slot/OTA behavior and stock-return procedure |

Encrypted data requires more than a working UI. Reconcile the new factory
fstab instead of importing the modified Xiaomi.eu fstab's missing verification
flags. Confirm the factory filesystem and encryption formats; the earlier
captured baseline uses F2FS and wrapped keys. Preserve the confirmed formats,
real OS/vendor/boot patch levels and the correct KeyMint, Gatekeeper, Weaver
and secure-element dependencies. Metadata decryption must precede filesystem
access; credential-encrypted data is a separate stage. Do not select a route
from an unrelated Xiaomi model or a masked Android property. See the
[AOSP FBE requirements](https://source.android.com/docs/security/features/encryption/file-based),
[metadata encryption requirements](https://source.android.com/docs/security/features/encryption/metadata)
and [hardware-wrapped key design](https://source.android.com/docs/security/features/encryption/hw-wrapped-keys).
TeamWin also explicitly treats [device-specific decryption](https://twrp.me/faq/encryptionsupport.html)
as separate integration work.

Virtual A/B does not provide two independent complete super images. Recovery
must understand the actual snapshot/merge state and boot-control interface;
an initial smoke test must not merge snapshots or alter slots automatically.
[AOSP describes the shared base and snapshot arrangement](https://source.android.com/docs/core/ota/virtual_ab).
Keep bootloader firmware, GPT and persistent-security partitions outside
initial write support. Recovery cannot undo every hardware-backed state change.

Backups must live off the phone and have verified coverage and hashes.
TeamWin's ordinary data backup [excludes internal media](https://twrp.me/faq/backupexclusions.html),
so photos and other `/data/media` content need separate coverage. A backup
file is not a demonstrated restore path, and a spare slot is not proven
bootable merely because it exists. Do not promise protection until the
appropriate restore tests are separately authorized and pass.

The private review receipt is
`artifacts/source-contracts/nezha-recovery-plan-v1/receipt.json`, SHA256
`f07607300c58473b9cb698e26c40859e23a785623f1f5ebdeb89a397defa33d9`.
It binds 45 text files from five pinned repositories, ten primary web pages
and the checked stock-header observations. All source-file Git blob hashes
and SHA256 hashes matched. This bounded review did not download or execute
the repositories' prebuilt binaries, review every source file, build TWRP,
or access the phone or guest.
