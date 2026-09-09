# Artifact retention pass, September 9, 2026

**Only the installed v14 delivery set remains on the host.** The user asked to
keep the most recent set and remove the rest. Forty-six payload directories
belonging to superseded sets were deleted, about 848 GiB, and host free space
rose from 412 GiB to 1.2 TiB. Every removed set is still identified by hash in
the dated record that introduced it, so nothing about the history changed; only
the bytes are gone. The sanitized record is
[`research/artifact-retention-20260909.json`](../research/artifact-retention-20260909.json)
and `tests/test_artifact_retention.py` recomputes its totals.

## Kept

| Item | Location | Check before removal |
| --- | --- | --- |
| v14 bundle, build `nezha.98d08f70d20e5a87a2777f81` | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v14/` | `experimental_flash_bundle.py verify` matched manifest `b36a0482…` and all eight payloads |
| v14 signing set with the reconciled archive | `artifacts/avb/nezha/variant-opt-in-userdebug-20260906-v14/` | `shasum -a 256` of `reconciled-v1/target-files.zip` gave `fee3f8e0…`, the status page value |
| v14 admission and transfer receipts | `artifacts/build-validation/variant-opt-in-userdebug-20260906-v14-{admit,transfer}/` | unchanged |
| Every `<set>-admit/admission.json` | `artifacts/build-validation/` | 8 KiB each; `config/nezha-avb-image-set.json` pins them by hash |
| Five receipt-only directories under 1 GiB | `artifacts/avb/nezha/package5-20260902-v1` and the three `package7-feature-fixes-…-failed-*` directories, plus the f9e failed-attempts directory | below the removal threshold |
| Stock firmware, firmware analysis, vendor, kernel, recovery, policy and camera inputs | the other `artifacts/` trees | not delivery sets; untouched |

## Removed

| Group | Directories | Size |
| --- | --- | --- |
| Signing sets `artifacts/avb/nezha/<set>` | package6, package7, package7-feature-fixes, package7-ui-camera-shade (f9e), userdebug v1 and v3 to v13 including v11r1 | 17 directories, 442 GiB |
| Bundles `artifacts/flash/nezha/<set>` | package7, package7-feature-fixes, package7-ui-camera-shade (f9e), userdebug v1 and v3 to v13 including v11r1 | 14 directories, 128 GiB |
| Transfer copies `artifacts/build-validation/<set>-transfer` | userdebug v1 to v13 including v11 and v11r1 | 14 directories, 269 GiB |
| Retained f9e Super | `artifacts/build-validation/feature-successor-f9e-super-retained-20260908` | 1 directory, 8.8 GiB |

The deletion ran through a script that re-checked every path: it had to sit
directly under one of the three delivery parents, not be a symlink, not name
the v14 set, and be at least 1 GiB. The f9e set was the last `user`-variant
build; it is gone with the rest and a non-debuggable build now needs a fresh
build under a new identity.

## What changed in the repository

- `docs/camera-completion-20260907.md` linked to the v9 bundle directory; the
  two links are plain text now, because the documentation test requires link
  targets to exist.
- `docs/workspace-status.md`, `docs/release-runbook.md` and `CLAUDE.md` no
  longer say that predecessor bundles are kept as rollback evidence. The rule
  is now: keep the installed set, the working76 rescue recovery, the stock
  return inputs, the signing key and the private build inputs; remove a
  superseded set once its successor is installed and recorded.

## Not removed

The VM was not touched. It had 200 GB free and the one-writer rule applies to
that volume. Four large guest trees are candidates for a later pass:

| Guest path | `du` | Note |
| --- | --- | --- |
| `/work/validation/nezha-oem-policy-integration-20260829` | 145G | August policy integration run |
| `/work/out/nezha-user-policy-20260827T2220Z` | 116G | August user-policy output tree |
| `/work/out/nezha-framework-20260827T1835Z` | 13G | August framework output tree |
| `/work/validation/variant-opt-in-super-20260906-v14/super.img` | 8.9G | guest duplicate of the verified v14 Super |

The live incremental output `/work/out/nezha-feature-fixes-20260905-v1` and
the source checkout stay as they are.

## What this does not prove

Removal changes no build, record or device result. A historical replay of a
removed set must rebuild it or restore it from a copy that matches the recorded
hashes. Host free space is measured at the time of the pass; each new delivery
set costs about 57 GB until the previous one is removed.
