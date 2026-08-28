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
