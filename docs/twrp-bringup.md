# TWRP for Nezha

TWRP is an active, separate bring-up target for the China Xiaomi 17 Ultra
(`nezha`). It is intended to shorten the eventual recovery/test/logging cycle
without requiring a complete Evolution X ROM first. A compiled recovery is
not yet a tested rescue environment, and this work authorizes no phone change.

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
definitions use their real JNI dependencies. The current set contains 15
additional projects, including native bridge support, selected platform test
helpers, Skia and its missing codec/font providers. NFC, Wi-Fi and AVF source
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

For an already prepared checkout, run the following from the **new versioned
control bundle** instead of repeating `prepare`. Set `TWRP_PREVIOUS_CONTROL_ROOT`
to the absolute path of the exact previous bundle matching the prepared receipt;
an arbitrary older bundle or a mutable `latest` alias is not interchangeable.

```sh
python3 scripts/twrp_dependencies.py fetch --host-mode apple-rosetta
python3 scripts/twrp_build.py revise --host-mode apple-rosetta \
  --previous-control-root "${TWRP_PREVIOUS_CONTROL_ROOT:?set the exact previous control bundle path}"
```

`revise` verifies the existing target and patch queue before accepting reviewed
target changes and supplementary additions. It archives the previous receipt
and changed target files under the report directory's `build-revisions`, while
preserving the base snapshot, output and caches. Existing outputs retain their
earlier provenance; the new receipt marks the revision as not yet built or
validated. Then run the separate `graph` and `build` commands above. Changing
the patch queue, source configuration or target file set requires separate
review; unrelated local edits are not adopted.

The default build variant is `user`, which retains init's compile-time
enforcement behavior. Explicit `userdebug` builds remain diagnostic experiments;
their init can accept a permissive bootconfig. Neither build variant should
be described as enforcing on the phone before a device test.

The [patch queue](../patches/twrp/README.md) removes permissive debug `su`,
automatic root ADB and a source-file truncation during environment setup. It
also requires host authentication in recovery adbd, including on unlocked or
debuggable devices. The ordinary Android adbd behavior is unchanged. A trusted
host key and its recovery handling must still be provided and validated; no
host private key or stock key is bundled.

The [log collector](recovery-logs.md) and
[image inspector](../scripts/inspect_twrp_image.py) run separately. The inspector
also passed a read-only check against the hash-verified factory recovery image;
its structural result does not authenticate that input or validate TWRP.

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
