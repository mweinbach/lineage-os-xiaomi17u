# Package6 static validation — September 4, 2026

Fresh inspection of the current signed Package6 boot images passes. This adds
direct image-content evidence to the earlier packaging and AVB records; it does
not establish bootloader acceptance or a successful Evolution X boot. The
selected platform remains `bka` / `bp4a`, normal Android remains enforcing, and
the kernel baseline remains **4 KiB**. No source, image, key or phone was changed.

The inspected archive is the existing signed/reconciled target-files ZIP,
SHA-256 `fbb6cba4ee1a0872634494c9398857bd7a176abba9b3adceee7c6bcbcbc0adb4`,
10,834,328,619 bytes. It is distinct from the original native Package6 ZIP
(`e3b9aa2b…`). Both retain their original provenance.

## Original VINTF checker results

The three **unmodified current Android checker commands all exit 0**, with
matching native/supervisor exits and complete streams. Collection completes at
**13:21:48 UTC**, after 605.184 seconds including the before/after source and
input checks. Full compatibility stdout ends `COMPATIBLE`.

| Original command | Native / supervisor | Reported definition skips | Warnings |
| --- | --- | ---: | ---: |
| Framework `--check-one` | 0 / 0 | 2 | 2 |
| Vendor/ODM `--check-one` | 0 / 0 | 0 | 0 |
| Framework/vendor/kernel/APEX `--check-compat` | 0 / 0 | 0 | 0 |

The final comparison uses all five partition maps, the selected Canoe/Nezha
SKUs, vendor API 202504, shipping API 36, both static kernel metadata files and
39 retained APEX modules. Their materialization is reverified before and after;
no APEX is substituted or newly activated. All six original source callbacks
match, including 548 source files across 15 selected projects and all 1,179
locked project HEADs/origins. The nine intentionally patched projects are
preserved. Complete source-callback returns, input and APEX maps agree across the run.

The original framework-only mode still skips definition checks for the
unlevelled system device matrix and product Lineage matrix. It also emits the
retained device-manifest/target-FCM and kernel-FCM warnings: this CLI mode
requires one primary partition mapping. The full comparison has all five maps
and the explicit kernel inputs. Neither warning nor skip is silently removed,
counted as a passed subcheck, or claimed to be covered by the final command.

The host review verifies 24 exported evidence bodies (191,008 decoded bytes),
original argv, native exits, sandbox/limits, preservation and the original
coverage parser. Its first attempt incorrectly required every raw mountinfo row
to say `ro`, including the hidden writable `/work` mount beneath the read-only
bind. The correction follows the unchanged observer's effective `statvfs`
flags, retains raw mountinfo/hash equality and rejects an effectively writable
mount. The original failure is preserved; nine focused regression tests pass.
No native check was changed or rerun to obtain a different result.

These are original CLI results, separate from the earlier instrumented
experiment. They do not qualify that experiment's ODR/runtime equivalence,
proprietary AIDL definitions or method ABI, APEX activation/signatures, live
SELinux/kernel state, AVB trust, OTA or boot. Native start/seal files were checked
by the guest but not exported for independent host filesystem replay. Complete
VINTF and ROM readiness flags remain false.

## Current boot-image contents

The inspection completed at **13:11:52 UTC**. It rehashed the five standalone
boot-related images and the complete published ZIP, then compared 16 selected
ZIP member bodies with the images or their embedded sections. Three fresh
pinned AOSP unpack operations and two bounded LZ4 decodes passed. CPIO entries
were parsed without materializing their paths, links or device nodes.

| Check | Observed result |
| --- | --- |
| Kernel | Exact retained ARM64 4 KiB Image; no replacement kernel |
| Device trees | Exact eight Canoe DTBs and the retained Nezha DTBO overlay |
| Recovery | Exact hardware-tested working76 image, `a130ba75…`; no runtime changes |
| Vendor ramdisk | All 430 modules and six module metadata files retain the expected payloads and factory ownership/modes |
| Fstab | 29 selected factory rows, including 13 AVB rows and the wrapped-key F2FS encryption settings; packaged root `0644` |
| Boot configuration | Eight expected bootconfig values and the exact vendor command-line token order |
| First-stage init | AArch64, 2,701,184 bytes, root `0750`, SHA-256 `40e909efe66f1e94b445bb6c71ade94be994470981606dcbede6c975bfbcff94` |
| Image sizes | All five fit the recorded build budgets; this is not a fresh physical-device capacity measurement |

This inspection does not repeat cryptographic signing verification. Some leaf
images have unsigned local metadata and are authenticated by descriptors in the
signed parent; the existing 17-role AVB verification remains separate evidence.
It also does not reconstruct the historical producer actions or prove that the
current first-stage binary was compiled from each recorded source input.

## Alternative GSI keys and the ordinary AVB chain

All seven literal `/avb/*-gsi.avbpubkey` paths referenced by the `/system` fstab
entry are absent from both inspected ramdisks. That absence is retained; key
closure is not marked complete.

The pinned `system/core` source at
`241488ea392c01079941d86ddc458b8a0c9ae6e1` has an explicit conditional fallback:
`first_stage_mount.cpp:493–533` skips unreadable alternate keys, and
`:825–841` can use the ordinary AVB handle if standalone verification fails and
the fstab entry also selects `avb`. The current entry selects
`avb=vbmeta_system`. Fresh metadata inspection finds the matching system
hashtree and nonempty security-patch descriptors in the signed parent.

This is a source-control-flow and descriptor result. Opening the ordinary
handle, bootloader digest/slot verification, hashtree setup and device-mapper
initialization must still succeed. Unlocked-bootloader handling can also affect
the standalone path. None of this changes Android's SELinux mode. Missing
alternate GSI keys alone do not justify adding arbitrary keys, disabling
verification or replacing otherwise matching images. DSU/GSI support and actual
device behavior remain unverified.

## VINTF scope correction

The retained diagnostic combined matrix has 223 HAL rows. A package/format set
comparison finds 39 rows absent from its effective device manifest, including
automotive, TV and virtual-machine entries. **These are not 39 failed mandatory
provider checks.** Do not add unrelated services to this phone from that set
difference.

At pinned libvintf `69c456ea4aa2f503a2904cfbc11f279a3b2efb09`,
`MatrixHalConverter` does not parse or emit a HAL `optional` attribute, and
`HalManifest::checkCompatibility` has no all-HAL presence loop. The unused-HAL
check instead matches device-manifest instances against the combined matrix.
The earlier phrase “full combined-matrix requirements” must not be read as a
new universal provider-presence requirement.

The original checker results, proprietary AIDL metadata coverage, and runtime
interface/device-feature validation are separate gates. The 155 matching
authored declarations and the 127-name generated-metadata gap remain distinct.
The unlevelled matrix definition-check skip is still explicit. Host static
kernel inputs do not measure live kernel SELinux policy, and the checker's
default flags do not verify AVB image signatures or rollback safety.

## Evidence and limits

The compact public record is
[`research/package6-static-validation.json`](../research/package6-static-validation.json).
Original images, unpacked sections, full inventories and raw logs remain in
ignored locations. The boot parser regression suites passed **124 tests**;
the separate matrix source-review suite passed **7 tests**, with zero skips.
The complete workspace suite passed **4,512 tests** at this checkpoint.

The explicit VINTF coverage limits, first-stage reproduction, APK/APEX/OTA
signing and update behavior, live rollback/capacity, first boot and hardware stabilization
remain separate work. All complete-ROM and flash readiness flags stay false.
