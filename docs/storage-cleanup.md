# Verified host storage cleanup — September 2, 2026

This dated checkpoint records two completed, explicitly scoped host deletions.
It does not authorize deleting source checkouts, the active build volume,
current build inputs or historical evidence generally. No guest or phone
command ran; host container status and configuration were inspected read-only.

## Removed copies and measured space

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
Nothing11 protection review verified its **180 frozen inputs**. This cleanup
does not establish current guest output integrity or bootability, and records
no deletion of old guest compiler outputs.

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

See [current workspace status](workspace-status.md) for subsequent work and
[Apple Container](apple-container.md) for the preserved expansion checkpoint
and active-volume boundaries.
