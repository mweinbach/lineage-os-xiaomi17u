# Verified storage cleanup — September 2, 2026

These dated checkpoints record explicitly scoped host and guest cleanup.
They do not authorize deleting source checkouts, the active build volume,
current build inputs or historical evidence generally. No phone command ran.
The first two operations were host-only; subsequent guest actions and their
verification limits are recorded separately below.

## Completed cleanup result — 17:45:04 UTC

The cleanup removed **51 obsolete files**: one detached volume snapshot, ten
duplicate crosscheck images and 40 guest scratch bodies. After the separately
approved free-block trim, host availability is **293,727,363,072 bytes
(273.56 GiB)**. The three operation-local host-free increases total
**246,185,762,816 bytes (229.28 GiB)**. The guest's 99.18 GiB scratch deletion is
not an additional host-free delta and must not be counted twice.

The same builder was restored with its original configuration, the temporary
maintenance container was removed, and the active raw volume remains 1 TiB.
The unchanged 100 GiB host reserve is exceeded at this checkpoint; fresh build
admission and the full follow-on budget remain separate. Cleanup establishes no
new Nothing11, ROM, signing or boot result.

The later [Nothing11 validation](build-progress.md#nothing11-passes-after-storage-cleanup--2026-09-02)
closes successfully at **17:56:39 UTC**. That separate result verifies the
resumed frontend/metadata check; it does not change the scope of this cleanup
checkpoint or establish fresh image production or boot success.

## Host copies and measured space — 17:16:46 UTC

| Completed UTC | Removed | Logical bytes | Allocated bytes before removal | Observed host-free increase |
| --- | --- | ---: | ---: | ---: |
| 17:13:17 | Detached pre-expansion 800 GiB volume peer | 858,993,459,200 | 732,420,161,536 | 34,511,769,600 |
| 17:16:46 | Ten byte-identical firmware crosscheck image bodies | 41,650,827,264 | 34,586,898,432 | 34,585,952,256 |

The two operation-local free-space increases total **69,097,721,856 bytes
(64.35 GiB)**. Host availability went from **53,546,377,216 bytes** before the
first operation to **122,636,726,272 bytes (114.21 GiB)** after the second.
The net change is slightly smaller than the summed deltas because availability
also changed between measurements. These are observed filesystem-free values,
not exclusive APFS block accounting. In particular, an APFS clone's allocated
size does not predict the space its deletion will recover.

At this checkpoint availability exceeds the unchanged **100 GiB host reserve**.
That clears only the measured reserve threshold, not the full continuation
budget or any build/readiness gate. **Nothing11 has not executed.** Fresh space,
input and ownership checks remain necessary before native work; the remaining
component, image, packaging, signing, AVB/VINTF, super, OTA and boot gates remain
open. The ROM is not flashable.

## Detached volume peer

Only this superseded raw image was removed:

```text
reports/oem-policy-integration-20260829/root-volume-maintenance-preparation-v1/offline-v1/volume-peer.img
```

It was the old 800 GiB image retained during the September 1 expansion to
1,024 GiB, not the current managed volume. The user explicitly approved losing
rollback to this old snapshot after that consequence was explained. The
preflight found no open handles or configured container mount for the peer.
Its historical full SHA-256 remains recorded; cleanup did not claim a fresh
full read of the 800 GiB image.

The current external `evolution-nezha-work/volume.img` remained **1,099,511,627,776
bytes**, with inode **1234891033** and all nine recorded stat fields unchanged.
Before/after host inventory still selected that managed volume and the same
builder. The removed path was confirmed absent; **193 small maintenance files**
and **409 protected files** were unchanged. The clone/swap receipts and metadata
remain as historical evidence, but their old raw snapshot is no longer available.

## Duplicate firmware crosscheck bodies

All ten removed bodies passed fresh, complete byte comparison and full SHA-256
checks on both sides against distinct regular canonical files. The copies were:

- `d2cf57fd…/upstream-super-crosscheck/super.raw.img`, with its canonical
  `reconstructed/super.raw.img` preserved.
- `b29afecc…/upstream-crosscheck/super.raw.img`, with its canonical
  `reconstructed/super.raw.img` preserved.
- Eight `b29afecc…/lp-upstream-crosscheck/` images: `odm_a`, `product_a`,
  `system_a`, `system_dlkm_a`, `system_ext_a`, `vendor_a`, `vendor_dlkm_a` and
  `mi_ext_a`, with all eight `logical-partitions/` counterparts preserved.

These paths are under `artifacts/firmware-analysis/`; the verification receipt
below contains every full path, hash and before/after identity. Only these ten
files were unlinked. All three crosscheck directories and their receipts remain.
Postchecks confirmed the ten removed paths absent, ten survivors unchanged,
three receipts unchanged and all **409 protected files** unchanged.

Both original firmware archives, canonical extracted images, `working76`,
`.tools`, source checkouts, the active user-policy output, current source
candidate, Package5 archive and materialized images were preserved. The
Nothing11 protection review verified its **180 frozen inputs**. These host
operations do not establish current guest output integrity or bootability.
No old guest compiler output was deleted.

## Earlier unprivileged trim failure — 17:27:36 UTC

The attempt to trim already-free ext4 blocks through the original builder
failed with native exit **1**: `FITRIM ioctl failed: Operation not permitted`.
The original failed receipt remains failed. It deleted no files, wrote no
source/output files and reduced the backing image's allocated size by **zero
bytes**. Guest free space remained **286,256,033,792 bytes**; host availability
did not increase. Three selected source/recovery/configuration sentinel files
passed before/after full-hash and stat checks, not an all-files integrity audit.

## Guest scratch retirement — 17:42:18 UTC

A separate finite deletion removed **40 exact regular files** under
`/work/validation/nezha-oem-policy-integration-20260829/`:

- 16 obsolete policy-image TAR or redundant export4 EROFS bodies.
- Eight EROFS no-op experiment image/TAR bodies.
- 16 footer-test `protected-prefix.bin` and `regenerated.fec` scratch bodies.

The exact target inventory and native deletion journal are pinned below. Target
body hashes in the inventory are historical, not fresh full reads. No parent
directory or final footer-bearing image was removed. The operation preserved
metadata for **236 sibling entries**: 154 small regular files also checked by
full hash, 16 large files checked by metadata only, and 66 directories. All
**16 parent directories** remained, along with full hashes/stat identities for
three selected source/recovery/configuration sentinels. These checks do not
establish complete source or output integrity. Before/after
ownership checks found the same sole builder on the existing 1,024 GiB volume.

The targets occupied **106,498,433,024 allocated bytes (99.18 GiB)**. Guest
available space increased by exactly that amount, from **286,256,033,792** to
**392,754,466,816 bytes**. This was **not additional host reclamation**: the
outer completion recorded **116,699,738,112 bytes (108.68 GiB)** host free, down
831,488 bytes across the operation. Ext4-free bytes must not be added to the
earlier APFS host-free increases. Current source checkouts, active output,
working76, stock inputs, keys, Package5 and final footer images remain outside
this deletion set. Nothing11 had not executed at this scratch-cleanup checkpoint.

## Approved free-block trim and restoration — 17:45:04 UTC

The user explicitly approved briefly stopping the idle builder, attaching the
existing volume to a temporary maintenance container with **`CAP_SYS_ADMIN`**,
then restoring the original builder. The controller confirmed detachment before
each handoff; the source volume was not attached to concurrent writer VMs.
This did not grant the normal builder a new capability or change its configuration.

The maintenance command returned **exit 0** at **17:45:02 UTC**. The controller
completed successfully at **17:45:04 UTC**, with no execution or restoration
error, the original builder restored, and the temporary container removed.
The active backing still has inode **1234891033** and logical size
**1,099,511,627,776 bytes**. Its allocation and timestamps changed as expected;
the earlier host-only nine-stat equality does not apply across this trim.

| Measurement | Before | After | Observed change |
| --- | ---: | ---: | ---: |
| Host available bytes | 116,639,322,112 | 293,727,363,072 | +177,088,040,960 |
| Raw backing allocated bytes | 871,685,799,936 | 694,572,396,544 | −177,113,403,392 |
| Guest available bytes | 392,754,466,816 | 392,754,466,816 | 0 |

The **164.93 GiB observed host-free increase** is neither the backing-allocation
reduction nor the trim command's **392,771,244,032-byte** discard report. These
measurements describe different layers. Host availability also changed between
operations; the first-to-last net increase is **240,180,985,856 bytes**, not the
sum of operation-local deltas.

Trim deleted no live files and wrote no source/output files. Full hashes and all
nine stat fields of the three selected source/recovery/configuration sentinels
were unchanged through restoration. The original builder configuration hash
also matched. These are bounded preservation checks, not a complete filesystem,
source, output, recovery-runtime or hardware integrity audit. The earlier
unprivileged failure remains failed; the successful maintenance is a separate
authorized operation. No phone operation occurred.

## Exact local evidence

All paths below are relative to `reports/cleanup-20260902/`. These ignored local
receipts retain the complete inventories and operation checks; historical
evidence JSON was not rewritten to describe a different original result.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `protection-v1/protection.json` | `e8c5d0f952cdf827f4b5305f211bd5fb13360df2a6c78e73755eac5ae115b22a` | 413,065 |
| `protection-v2/protection.json` | `e5ce392d474c189671871d8d34c04503500c24a8b1cb45687e64b10eb6e1beb3` | 23,632 |
| `root-volume-peer-v1/preflight.json` | `7ffb8b03acc125df0f3095da7e48b3e2581ae9891cf4bc0765ed18a10c08950c` | 295,217 |
| `root-volume-peer-v1/completion.json` | `2e162522bafe7120327fb01f370ed938ebd2241c46dd4f889a24d743c6ab7252` | 6,420 |
| `duplicate-images-v1/verification.json` | `b29db0df8bd131b1fb032af7f8504ed9712b6ec0c436d2a4cd333befe70887be` | 12,692 |
| `duplicate-images-v1/removal-preflight.json` | `108fe240b09d89b60f0df6c39a9c28890919d6683231a9eee612b44125ff2202` | 14,368 |
| `duplicate-images-v1/removal-completion.json` | `3a194b3f41912ef48f5d111e4a758767201f88988d132713d15c9386a4cb41a3` | 2,347 |
| `vm-trim-v1/actual-v1/stdout.json` | `77f5318838716a6f02def8afc514b7148ce4408b2bc14ca6c829ea2643b6d530` | 2,238 |
| `vm-trim-v1/actual-v1/completion.json` | `6690237e99e454e6bdeaca245fa8aa28b3c6e21e547d8a13dfa7e1fa153478a7` | 1,417 |
| `vm-scratch-retirement-v1/targets.json` | `28f8aa6d912a14d2695f343e76e580139f580730305388c2fcaa6257326884d1` | 13,889 |
| `vm-scratch-retirement-v1/inspect-v1/stdout.jsonl` | `0cef833302ec3a0f99d02ada8dadcf8b8c9dec26816e9b0d94d6f3ac07fa7da7` | 113,596 |
| `vm-scratch-retirement-v1/delete-v1/stdout.jsonl` | `8b73ea8adc5ec25417fa3a72c04e7749bce3e99d31057a3e85ce35a7528c2d9d` | 11,434 |
| `vm-scratch-retirement-v1/delete-v1/completion.json` | `ac1100884e7bd6c5829be5c152ef479c8e7faf95cf7ba4ec54eec9ae88fa2c70` | 1,161 |
| `vm-admin-trim-v1/actual-v1/authorization-and-plan.json` | `508fb9c314090ea154f492344919ce7fec159f1f05764ff5fde3d4f9b6dbcedb` | 984 |
| `vm-admin-trim-v1/actual-v1/09-maintenance.stdout` | `0b227df4ddf441d4a60552307f3587b5e469519a871f952838ee3d2c87980230` | 2,145 |
| `vm-admin-trim-v1/actual-v1/16-original-read-check.stdout` | `15e4808d529e31291995e1bd31095fd6b7fe9d1d0b58639f7472eef221b041ec` | 1,282 |
| `vm-admin-trim-v1/actual-v1/completion.json` | `cf75a7b6da0e1a1016b6c13f58285cefdb76791966e9584874b58c9b5847ca65` | 1,209 |

See [current workspace status](workspace-status.md) for subsequent work and
[Apple Container](apple-container.md) for the preserved expansion checkpoint
and active-volume boundaries.
