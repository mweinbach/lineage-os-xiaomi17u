# CLAUDE.md

Bring-up workspace for a private Evolution X (Android 16 QPR2, `bka` / `bp4a`)
build for one Xiaomi 17 Ultra (`nezha`, SM8850 / `canoe`, 4 KiB pages). The
installed build is the v15 userdebug delivery set, which boots with enforcing
SELinux and root ADB for diagnostics. Most of this repository is tooling,
contracts and evidence records, not Android source.

## Read first

1. `AGENTS.md` holds the working rules and the definition of a meaningful
   test. Follow it; this file only adds orientation.
2. `docs/workspace-status.md` selects the current baseline, identities, hashes
   and next development steps.
3. `docs/software-plan-20260909.md` is the prioritized plan for the ROM
   itself. `docs/roadmap-20260906.md` holds the tooling, update and kernel
   workstreams and the decisions already taken (both physical slots written,
   Super single-copy with A/B updates, private audience, source kernel as the
   design goal with prebuilt kept selectable).
4. `docs/README.md` indexes every dated record. Old pages describe their own
   checkpoint; do not read a historical gate as a current one.
5. Other sessions land work between your turns. Re-read `git log`, the status
   page and `make apple-status` before resuming anything, and look for build
   processes inside the VM before any guest step.

## Rules that bite

- Never unlock, relock, wipe, reboot, flash, sideload or change slots on the
  phone without an explicit request for that operation. Collectors are
  read-only and take an explicitly identified serial.
- Nothing proprietary, no serials, logs, keys or raw dumps in Git. They live
  under ignored `artifacts/`, `evidence/`, `reports/`, `sources/`, `upstream/`,
  `.tools/` and the ignored `vendor/xiaomi/nezha-*` bundles. Record hashes and
  provenance instead.
- Normal Android stays enforcing. Only recovery may be permissive, and only
  because the user authorized it for bring-up.
- Do not borrow another phone's partition layout, kernel, firmware or identity.
- One writer per Linux source volume. Check `make apple-status` before
  resuming a build; never prune volumes or reset the checkout.
- Keep verified facts separate from unresolved work in every doc and record.
  A passing test, a compile or a receipt never closes a device result.
- A delivery set costs about 57 GB on the host. Only the installed set is
  retained; remove a superseded set once its successor is installed and
  recorded, and never delete stock return inputs, the working76 rescue
  recovery, the signing key or private build inputs.

## Layout

| Path | Role |
| --- | --- |
| `config/*.json` | Reviewed contracts: source lock, AVB profiles, construction descriptors, feature inputs. Scripts pin a contract's SHA256; editing a contract means updating the pin and recording why. |
| `scripts/*.py` | Stdlib-only Python tools. Most expose `plan` / `check` / `verify` / `build` subcommands and a `--dry-run`. `plan` reads public inputs only. |
| `tests/` | Offline unittest suite, stdlib only, phones and networks mocked. `support.py` holds shared walkers; discovery does not collect it. |
| `device/xiaomi/nezha/` | Authored product and board source, including the guarded camera, CameraOpt, audio and clock selections. The tracked `BoardConfig.mk` is a restricted template; `generate_device_tree.py` writes the buildable derivative into an ignored staging root. |
| `kernel/xiaomi/nezha/` | Prebuilt kernel bundle consumer (provenance kind `prebuilt` or `source`), kernel input contract and the ACK/MiCode config audit. |
| `patches/evolution/`, `patches/twrp/` | Numbered upstream patches, each with a JSON contract holding its hash. 0029 to 0039 are the camera, audio and clock-plugin work. |
| `policy/nezha/` | Blueprint entry for the SELinux source integration; the policy inputs themselves are contracts under `config/` and ignored bundles. |
| `recovery/twrp-working/` | The selected `working76` recovery repack workflow. `recovery/twrp-upstream/` and `recovery/twrp/` are preserved source experiments. |
| `research/*.json` | Sanitized public records behind the docs. Tests recompute hashes, links and totals from them. |
| `docs/` | Current status, runbooks and dated evidence pages named `topic-YYYYMMDD.md`. |
| `containers/apple/` | Apple Container + Rosetta builder image for the Linux build volume. |
| `tools/` | Small native probes built in the Android tree: camera metadata and capture probes, EROFS metadata reader, VINTF definition audit. |
| `templates/` | Source templates for the guarded IMS, workload-classifier and camera integrations. |
| `manifests/` | Deliberately empty. No local device manifest exists yet; the platform comes from the source lock and its snapshot under `research/source-snapshots/`. |

## How a build is delivered today

The pipeline that produced every installed set since v1 lives in the ignored
`reports/variant-opt-in-20260906/` directory: `deliver_userdebug.py` with
stages package, transfer, sign, bundle, preflight, install and observe, plus
`admit_package.py`, `admit_cascade.py` and `make_retained_manifest.py`, all
keyed by the `NEZHA_DELIVERY_SET` environment variable. Each set also gets
prepare, verify, finish and record scripts under `reports/<topic>/`. None of
that is in Git; absorbing it into `scripts/` is roadmap workstream A.
`scripts/release_workflow.py check` recognizes its receipts, and
`scripts/release_signing.py`, `ota_package.py` and `delivery_route.py` are the
tracked pieces waiting to replace parts of it.

## Commands

```sh
make help                 # every target with a one-line purpose
make test-current         # focused suite, under a minute
make test                 # full offline suite, about three minutes, run once before finishing
python3 -m unittest discover -s tests -p 'test_NAME.py' -v   # one module, from repo root
make apple-status         # who owns the Linux source volume
make release-plan BUILD_NUMBER=nezha.<hash> ARTIFACT_SET=<set>   # runbook stages for one identity
python3 -B scripts/release_workflow.py check --build-number nezha.<hash> --artifact-set <set>
make recovery-plan        # working76 build and ROM recovery input contract
python3 -B scripts/rom_construction.py plan --phase target-files
```

Run test commands from the repository root. Shell working directory persists
between Bash calls, so return to the root after any `cd`. The zsh shell globs
`--include=*.md`, so quote such arguments or use `grep -r` with `--include`
quoted.

## Conventions

- New evidence gets a dated page under `docs/`, a sanitized JSON record under
  `research/` when there is structured data, and a row in `docs/README.md`.
  Relative links in `README.md` and `docs/*.md` are tested, so never link into
  a directory that a retention pass may remove; name the path in code instead.
- Update `docs/workspace-status.md` when the selected baseline, identity or
  next step changes. Preserve superseded text in the dated archive rather than
  deleting history.
- A record states what was checked, what was not, and what it does not prove.
  Use words like "unverified", "not device-admitted" and "off-device" exactly.
- Every build gets a fresh source/build identity (`nezha.<hash>`) and a new
  delivery set number. The predecessor survives as hashes in its record, not as
  bytes on the host.
- Tests earn their place by exercising a script with synthetic input,
  recomputing a hash, link or total from an artifact, or pinning a measured
  value that carries a build decision. Do not write tests that restate a
  record they just read.
- Commit small, descriptive changes as work completes. Do not sweep unrelated
  uncommitted files into a commit.
- Plain language, main point first, no stock phrases or closing summaries.

## Where things stand

- Installed: v15, `nezha.81c1b93277a1fa371a3efbb3`, userdebug, slot A,
  Enforcing, bundle under
  `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v15/`.
- Prepared, not installed: v16, `nezha.434625bd9b5cd7a8a7eabd84` (source
  revision 15), bundle manifest SHA256 `5c57a12ff14d98349742ce59e6214d2ab2377c0c5e18edc2265b9b27b7188c3d`.
  It carries the four ported CameraOpt methods and the factory camcorder
  profile selection (`docs/cameraopt-four-methods-20260909.md`,
  `docs/camera-video-profiles-20260909.md`). Flashing it needs a fresh explicit
  request; once it is installed and recorded, remove the v15 set.
- Source: revision 15 in the Linux checkout (revision 13 is the installed v15). It carries the merged feature
  candidates (display brightness, Dolby, haptics, camera scheduling, refresh
  policy), the explicit userdebug opt-in, the QTI camera XML selection fix,
  the HyperOS camera framework port, native camera session hooks, vendor-key
  discovery, stream sizing, compressed Bayer DNG, Xiaomi audio descriptors and
  the stale Flex clock removal. `user` is still the default variant; userdebug
  needs its explicit opt-in. The workload classifier stays disabled.
- V15 adds the exact-stock IMS provider (running in its restored
  `vendor_qtelephony` domain, no SIM yet) and the display dim level 0.05; see
  `docs/tier1-ims-dim-20260909.md` and `docs/v15-install-validation-20260909.md`.
- Camera: the requested capture matrix passes on v13 and the v14 subset:
  rear and front Ultra HDR, main and telephoto 50 MP, telephoto 200 MP, Pro
  RAW, UltraRAW DNG, three physical RAW sensors, all ten Aperture effects and
  a short HEVC/AAC video. On v15 the Xiaomi app offers only 1080p because the
  platform loads the generic camcorder profile table (fixed in v16). An
  unattended eight-minute 1080p recording ran at a steady 24 fps with no
  drops. Image quality, focus, stabilization, 4K/60 fps/slow motion and the
  microphone response are unverified (`docs/tier2-camera-v15-measurements-20260909.md`).
- Open on device: retained userdata, UDFPS, shade visuals, IMS and VoLTE,
  panel brightness and HBM policy, Dolby, haptics, refresh policy, workload
  classifier, and the hardware ledger (radio, sensors, GNSS, NFC, Wi-Fi,
  Bluetooth, suspend, charging, thermals).
- Not yet built: OTA packages, the both-slot delivery route, a source kernel,
  release keys. The tracked tools for those exist but have not run on a real
  identity.
