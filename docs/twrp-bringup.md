# TWRP for Nezha

TWRP is an active, separate bring-up target for the China Xiaomi 17 Ultra
(`nezha`). It is intended to shorten the eventual recovery/test/logging cycle
without requiring a complete Evolution X ROM first. A compiled recovery is
not yet a tested rescue environment, and this work authorizes no phone change.

**Normal build 64 produced a rebuilt engineering-key-signed recovery image.**
Its 100 MiB size and kernel-free v4 layout passed structural inspection, and
the build verified its AOSP test-key AVB signature. The rebuilt archive has
unique secure properties, resolves all 44 executable interpreter paths, and
contains the generated loader configuration. Detailed artifact verification
is still incomplete: the inventory checker needs to distinguish Android's
intentional linker/ABI-stub SONAME pair from an ambiguous library collision.
No image has been booted or flashed, and no working logging environment is
claimed.

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
This is a limitation of the inventory classification; it does not prove
runtime symbol compatibility. The original failed run is retained, and a
reviewed inspector correction plus another complete artifact run are still
required. The policy analyzer and compiled ADB checks were not reached by
this run.

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
