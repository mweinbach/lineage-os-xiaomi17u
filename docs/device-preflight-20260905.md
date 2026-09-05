# Authorized device preflight — September 5, 2026

The user confirmed the connected Nezha in direct response to the request for a
read-only USB preflight. One matching USB ADB device was identified and its
serial/transport pinned in private evidence. **No flashing, wiping, rooting,
rebooting, unlocking or slot change was requested or performed.** No VM or
signing operation was needed.

The phone is running Android, not recovery or bootloader mode. The base
collector finished with `partial-observations`, exit 3, and no collection
errors. Unsupported reads were not counted as passed checks.

| Observation | Current evidence |
| --- | --- |
| Device | Xiaomi / `nezha` / `canoe`, SM8850, reported `CN` hardware |
| Running slot | A |
| Android state | Boot complete; zygote and SurfaceFlinger running |
| Existing ADB privilege | UID 2000; no elevation attempted |
| Page size / SELinux | 4,096 bytes / Enforcing |
| Framework and vendor version | Both report `OS3.0.309.0.WPACNXM` |
| Data | File-based encryption reported; `/data` and `/metadata` mounted |
| Battery | Reports 54%, charging; no stopped-updates marker |
| Android lock properties | `locked`, flash lock `1`, verified-boot state `green` |

The Android lock values **do not independently establish bootloader state**.
They must not be treated as proof that this development-key bundle can be
flashed. Matching version strings likewise do not prove retained firmware
payload identity or that an unmodified factory ROM is running.

## What this mode could not supply

All 19 direct physical-capacity reads and `/proc/bootconfig` were denied to the
existing Android shell. The partition symlinks and block-device major/minor
tuples were readable; the denials do not mean partitions are absent or too small.

A separate bounded supplement attempted only the ten relevant A/retained/Super
sysfs `dev`, `size` and `partition` attributes, twice. It tied decimal device
numbers to the already observed hexadecimal stat tuples and rechecked device,
mode, region, slot, USB transport and physical-node identity. All 60 sysfs reads
were denied. **Every capacity therefore remains unknown.** No raw block bytes
were read and no alternative privileged access was attempted. The supplement
uses Linux's read-only [partition attributes](https://github.com/torvalds/linux/blob/v6.12/block/partitions/core.c);
it does not modify the base collector or suppress its unknowns.

The base collector records 106 commands / 212 streams. The supplement records
131 commands / 262 streams, including 71 successful commands and 60 denied
sysfs reads. Independent review rehashed every saved stream, with no mismatch
or truncation. This is real device observation, distinct from the earlier
4,602-test offline tooling run; no unrelated test suite was rerun for this
read-only collection and documentation change.

Private evidence, containing serials and raw logs, remains ignored:

- `evidence/device-preflight-20260905T031715Z-android-a/manifest.json`:
  `49b19887a58313c3daf4e794c1548871999ff8ba6e9f06966f3adea00b800819`
  (90,216 bytes).
- `evidence/device-sysfs-preflight-20260905T032149Z/manifest.json`:
  `84f139965da75431ba6f5a09a5280efc567b674e5b2095cd888f0288f52994d4`
  (106,868 bytes).

## Gate after the Android collection (historical)

An explicitly authorized reboot into the proprietary bootloader is needed to
read its independent unlock state, next-boot slot, capacities and supported
snapshot status. No mode transition has been authorized by the read-only
collection request. Bootloader entry would not authorize flashing, wiping,
unlocking, slot changes or recovery transitions.

Retained firmware payloads, LP/snapshot state, secure rollback uncertainty,
bootloader return behavior, backups and data handling remain separate gates.
An already mounted `/metadata` does not prove snapshot idleness. Package7's
verified bundle is unchanged; `flash_ready` and `complete_rom_ready` remain false.

## Authorized bootloader follow-up

The user subsequently explicitly authorized the bootloader reboot. Before the
single `adb reboot bootloader`, the same private serial was matched to a USB
Android connection and `nezha` / `canoe` identity was freshly checked. The same
serial then appeared in fastboot. No flash, wipe, unlock, slot change, recovery
transition or return reboot was performed; the phone was left in bootloader mode.
The transition receipt is private in
`evidence/bootloader-entry-20260905T1432Z/transition.json`.

The bounded collector independently observed `is-userspace: no`, `product:
nezha`, **`unlocked: yes`**, and next-boot slot **A**. This resolves the earlier
Android-property uncertainty in favor of an unlocked bootloader. Both slots
report not unbootable; A reports successful, B does not. Retry counts are 6/7.
`snapshot-update-status` reports `none`; this is a bootloader observation, not
verification of LP metadata or retained firmware payloads. Maximum download
size reports 805,306,368 bytes.

All 19 physical-capacity observations match the recorded package capacities:
boot/vendor_boot 96 MiB each, dtbo 32 MiB, init_boot 8 MiB, recovery 100 MiB,
vbmeta/vbmeta_system 128 KiB each, countrycode/pvmfw 1 MiB each (both slots),
and Super 15,300,820,992 bytes. This does not independently validate candidate
image contents, expanded sparse-image fit, or flash admission.

Version fields and nine `has-slot` queries remain unsupported or empty. The
collector therefore correctly returns `partial-observations`, exit 3, with no
collection errors. Product, bootloader mode and next-boot slot were rechecked.
All 96 saved streams from 48 commands were rehashed with no mismatch.

Private manifest: `evidence/device-preflight-20260905T1433Z-bootloader-a/manifest.json`
(SHA-256 `fcc840b3f0d6e18f5aa1c430b36f9c5002e12e5cc582884e8659697556bb3c13`).

The next unresolved gates remain retained firmware/LP evidence, secure rollback
uncertainty, backups/data handling and bootloader return behavior. Any further
phone transition or flashing requires explicit authorization for that action.
Package7 is unchanged; `flash_ready` and `complete_rom_ready` remain false.

## Pre-flash verification follow-up

The user accepts losing all phone data and asked to verify the remaining risks.
This resolves backup preservation as a user requirement; no wipe was performed
or selected as an automatic action. No further mode transition was performed.

Fresh bootloader collection at 14:36 UTC again reports unlocked, target A and
snapshot status `none`. All 96 saved streams rehash correctly. The exact
Package7 manifest and all eight payloads pass the portable verifier. Comparing
actual image lengths (expanded sparse length for Super) with these live
capacities confirms all eight candidates fit. Super expands to exactly
15,300,820,992 bytes. This is a capacity check, not live LP admission.
Private comparison: `reports/flash-ready-20260905/bundle-device-fit-review.json`.

A separate host review freshly rehashed 11 stock/rescue files totaling
12,883,155,616 bytes: the eight original China return images, two firmware
references and working76. All match their recorded hashes; the original TGZ
was not rehashed. Fresh stock/candidate AVB headers have identical rollback
indices (root 0, boot/system 1769904000, recovery 1) and flags zero. Recovery
header locations differ (stock 0, candidate 1); the previously reviewed parent
chains use effective location 1. These facts reduce index-change risk but do
not establish stored secure counters or actual full-chain boot acceptance.
Stock return still requires original recovery with original vbmeta, and actual
stock restoration has not been exercised.
Private receipt: `reports/flash-ready-20260905/stock-return/rehash.json`, SHA-256
`0b5acc60d2d0a023f0181f3e6c96612e2b8b2ef81779c46c4cdf9d60ada7dcc2`.

The remaining direct evidence requires entering installed recovery: read the
selected-slot countrycode/pvmfw authenticated contents and current Super LP
metadata using the bounded collector, then review LP/snapshot state on the
host. This specific transition remains an explicit-authorization gate under
AGENTS.md. Do not flash a replacement recovery just to collect it. Unsupported
secure-counter reads remain an explicit risk-review limit, not an invented
zero or a promise of attainable attestation. Flash readiness remains false.

## Authorized recovery read and bootloader return

The user explicitly approved entering the installed recovery, bounded reads and
returning to bootloader. Both transitions succeeded on the same selected serial.
No flash, wipe, slot switch, privilege elevation or manual mount was performed.

Two failed collectors are preserved: the initial one rejected TWRP's donor board
property and unknown bootmode; the second rejected Toybox's block-device label.
Neither reached raw capture. The corrected collector uses exact live Nezha
SM8850/canoe device-tree bytes and recovery process/transport checks, with
identity rechecks, while accepting both documented block-device labels. The
successful collection has 154 commands / 308 hash-verified streams, exit zero,
and no unknowns or errors within its requested scope.

Both target-A firmware references match: countrycode's 32-byte authenticated
region and pvmfw's 778,240-byte authenticated region, plus their complete 1 MiB
reference-image hashes. Each read was repeated with identical bytes and stable
physical-node identities. The same paired read captured the first 1 MiB of Super.

Host LP parsing verifies both geometry copies and all six metadata copies,
including SHA256 checksums, partition/group/extents and measured physical bounds.
All primary/backup pairs match. Geometry uses 65,536-byte metadata slots, three
slots and 4 KiB logical blocks; the entire metadata region ends at byte 405,504,
inside the captured prefix. All copies describe eight populated A partitions
and empty B entries. Flags contain only the virtual-A/B-device bit, with no
active-overlay or unknown header flags. Logical payload contents were not read
or hashed. This is consistent with the bootloader's `none` snapshot observation;
it is not a secure-storage or full snapshot-service attestation.

On return, the proprietary bootloader again reports Nezha, unlocked, slot A and
snapshot status `none`. The phone was left there. Secure rollback counters,
first Evolution boot and physical-button reentry remain unverified; stock
return files are verified off-device but restoration has not been executed.

Private evidence:

- `evidence/recovery-verification-20260905T144120Z/`: transition and diagnostic receipts.
- `evidence/device-preflight-20260905T1441Z-recovery-a/`: first stopped collection.
- `evidence/device-preflight-20260905T1447Z-recovery-a/`: second stopped collection.
- `evidence/device-preflight-20260905T1449Z-recovery-a/manifest.json`: successful read receipt.
- `evidence/device-preflight-20260905T1449Z-recovery-a/lp-prefix-review.json`: scoped host LP review.

The bundle remains unchanged. An exact install/clean-data/stop/return plan is
still separate from this authorization for recovery verification.

Verification of the final collector revision: **4,610 offline tests passed**
with zero skips, including **43 focused preflight tests**. The tests mock phone
commands; the live firmware/LP results above are separate hardware evidence.
