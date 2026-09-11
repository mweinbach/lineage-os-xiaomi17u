# CLAUDE.md

Bring-up workspace for a private Evolution X (Android 16 QPR2, `bka` / `bp4a`)
build for one Xiaomi 17 Ultra (`nezha`, SM8850 / `canoe`, 4 KiB pages). The
installed build is the v20 userdebug delivery set, which boots with enforcing
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

- Installed: v20, `nezha.d5894f355e27f7d2f503f519`, userdebug, slot A,
  Enforcing, bundle under
  `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v20/`. It is v17 plus
  a three-part MPEG4Writer fix so the Xiaomi recorder's 8K/4K120/long-4K60 modes
  write a decodable HEVC track, and it still carries the always-on Leica Essential
  selection, the four ported CameraOpt methods and the factory camcorder profile
  selection; see `docs/v20-install-validation-20260910.md`,
  `docs/leica-essential-20260910.md` and `docs/tier2-camera-v16-20260910.md`.
- Predecessor (removed from host): v19, `nezha.613930978f6706c35296cd90` (v18/v19
  were the first two parts of the recorder fix; v17 `nezha.11b0a26475073bca18f34c39`
  baked in Leica Essential). V16 `nezha.434625bd9b5cd7a8a7eabd84` survives in
  `docs/v16-install-validation-20260910.md` and V15
  (`nezha.81c1b93277a1fa371a3efbb3`) in `docs/v15-install-validation-20260909.md`.
- Source: revision 19 in the Linux checkout, now installed as v20. It carries the merged feature
  candidates (display brightness, Dolby, haptics, camera scheduling, refresh
  policy), the explicit userdebug opt-in, the QTI camera XML selection fix,
  the HyperOS camera framework port, native camera session hooks, vendor-key
  discovery, stream sizing, compressed Bayer DNG, Xiaomi audio descriptors and
  the stale Flex clock removal. `user` is still the default variant; userdebug
  needs its explicit opt-in. The workload classifier stays disabled.
- V15 carried the exact-stock IMS provider in its restored
  `vendor_qtelephony` domain (no SIM) and the display dim level 0.05; those
  remain in v20. See `docs/tier1-ims-dim-20260909.md`.
- Camera: on v20 the Xiaomi app exposes the full video matrix (720p to 8K,
  30/60/120 fps). 4K60 Dolby Vision and 1080p record and play with a live
  microphone; 8K, 4K120 and long/sustained 4K60 now also record a decodable HEVC
  track (8K30 7680×4320, 4K120 a true 120 fps, 45 s 4K60 with audio), fixed by
  three guarded MPEG4Writer patches that handle the vendor encoder's
  length-prefixed NAL and codec-config framing (`vendor.qti-ext-enc-nal-length-bs`);
  see `docs/v20-install-validation-20260910.md` and
  `patches/evolution/nezha-hevc-*`. The 8K/4K60 container frame rate and sustained
  thermals still want a lit scene and longer runs. The four CameraOpt methods run
  on real 4K events, killing only cached apps above the adj floor. The cloud Leica
  color filters are enabled.
  The Leica M3/M9 Essential looks (module 256) are baked on (from v17) by two
  properties, `ro.theme_customize=LCC` and `camera.debug.safe.check.disable=true`:
  the gate was the camera's native anti-tamper check (fails on an unlocked
  bootloader), not a hardware attestation, and the device keeps its real
  identity. The guarded fragment `device/xiaomi/nezha/leica-essential.mk`
  (`NEZHA_LEICA_ESSENTIAL := true`) writes both into `build.prop`, so the mode is
  present at boot with no runtime resetprop and no Magisk; on the installed v17
  both properties read from the image after a clean reboot and the mode selector
  lists `Leica Essential` (256) without the app self-closing
  (`docs/leica-essential-20260910.md`, `docs/v17-install-validation-20260910.md`).
  Image quality, focus, stabilization and the M9-vs-M3 look still need a lit scene
  (`docs/tier2-camera-v16-20260910.md`).
- Open on device: retained userdata, UDFPS, shade visuals, IMS and VoLTE,
  panel brightness and HBM policy, Dolby, haptics, refresh policy, workload
  classifier, and the hardware ledger (radio, sensors, GNSS, NFC, Wi-Fi,
  Bluetooth, suspend, charging, thermals).
- Not yet built: OTA packages, the both-slot delivery route, a source kernel,
  release keys. The tracked tools for those exist but have not run on a real
  identity.
