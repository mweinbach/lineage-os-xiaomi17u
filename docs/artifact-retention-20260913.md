# Artifact retention pass, September 13, 2026

**Only the installed v26 delivery set remains on the host.** The user asked to
reclaim the superseded sets. Nine payload directories belonging to v23, v24 and
v25 were removed, 180,095,924 KiB (about 171.7 GiB), and host free space rose
from 732 GiB to 904 GiB. Each removed set is still identified by build number,
bundle manifest hash, reconciled archive hash and all eight payload hashes in
[`research/artifact-retention-20260913.json`](../research/artifact-retention-20260913.json),
which `tests/test_artifact_retention_v26.py` recomputes. Only the bytes are
gone; no build, record or device result changed.

This pass follows the rule the
[September 9 pass](artifact-retention-20260909.md) established: keep the
installed set, the working76 rescue recovery, the stock return inputs, the
signing key and the private build inputs; remove a superseded set once its
successor is installed and recorded. V26 is installed and recorded in the
[v26 installation record](v26-install-validation-20260912.md), so v23, v24 and
v25 became removable.

## Verified before removal

Each set was checked against its own recorded manifest before its bytes were
deleted, and all three passed:

| Set | Build | Bundle manifest SHA-256 | Verify result |
| --- | --- | --- | --- |
| v23 | `nezha.2fa2ea3549a2fc869a4c79df` | `6b75fe32…` | 8 payloads, byte identities verified |
| v24 | `nezha.d2ff2fe2133ee17a0fb46d7f` | `d775b47a…` | 8 payloads, byte identities verified |
| v25 | `nezha.b2c99443fe9e90a4a7954eac` | `c7435c90…` | 8 payloads, byte identities verified |

The reconciled signed archives hashed to `a26ce4f9…` (v23), `dbac73df…` (v24)
and `3c7dd392…` (v25). V24 is the attempt that boot-looped on `Invalid usage 19`
during the first audio volume-curve fix, so its bytes were never a rollback
target; the corrected fix shipped in v25 and remains in v26.

## Verified after removal

The installed set was rechecked once the deletions completed. `experimental_flash_bundle.py verify`
returned the expected manifest `883ead80…` with eight payloads,
`shasum -a 256 -c SHA256SUMS` reported OK for all eight images, and the
reconciled archive still hashes to `cc1a6349…`, the status-page value. All 5,118
offline tests pass, including the seven added with this record.

## Removed

| Group | Directories | Size |
| --- | --- | --- |
| Signing sets `artifacts/avb/nezha/<set>` | v23, v24, v25 | 3 directories, 90,363,676 KiB |
| Bundles `artifacts/flash/nezha/<set>` | v23, v24, v25 | 3 directories, 28,787,752 KiB |
| Transfer copies `artifacts/build-validation/<set>-transfer` | v23, v24, v25 | 3 directories, 60,944,496 KiB |

The deletion ran through
`reports/artifact-retention-20260913/retain_installed_set.py`, which re-checked
every path immediately before removing it: it had to sit directly under one of
the three delivery parents at the expected depth, name a superseded set, not
name the kept v26 set, not be a symlink, be a real directory, and be at least
1 GiB. The script refused nothing and defaults to a dry run. Its result is
`reports/artifact-retention-20260913/removal-result.json`.

## Kept

| Item | Location |
| --- | --- |
| v26 bundle, signing set, admission and transfer receipts | the four `variant-opt-in-userdebug-20260906-v26` directories |
| Every `<set>-admit/admission.json`, including v23 to v25 | `artifacts/build-validation/` — 8 KiB each, pinned by hash in `config/nezha-avb-image-set.json` |
| Per-set delivery, signing and install receipts and logs | `reports/variant-opt-in-20260906/`, `reports/tier2-camera-20260909/`, `reports/telephony-fixes-20260912/` and `evidence/` |
| Stock return inputs, firmware analysis, TWRP and recovery inputs, vendor, kernel, policy and camera inputs | the other `artifacts/` trees; not delivery sets, untouched |

The four small receipt-only directories under `artifacts/avb/nezha`
(`package5-20260902-v1` and the three
`package7-feature-fixes-20260905-v1-failed-*` directories) stayed, as in the
previous pass: they are below the removal threshold.

## Not removed

The VM was not touched. The `evolution-nezha-work` volume stayed attached to the
idle `twrp-nezha-upstream74-20260829` container, which held only `sleep infinity`
at a load average of 0.06, and the one-writer rule applies to that volume. Its
842 GiB of 1008 GiB remains in use, including the four large guest trees the
September 9 pass listed as later candidates.

## What this does not prove

Removal changes no build, record or device result. A historical replay of a
removed set must rebuild it or restore it from a copy that matches the payload
hashes in the research record. Host free space is measured at the time of the
pass; each new delivery set costs about 57 GB until its predecessor is removed.
