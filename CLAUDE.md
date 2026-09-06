# CLAUDE.md

Bring-up workspace for a private Evolution X (Android 16 QPR2, `bka` / `bp4a`)
build for one Xiaomi 17 Ultra (`nezha`, SM8850 / `canoe`, 4 KiB pages). The
Package7 `f9e` build is installed and boots with enforcing SELinux. Most of this
repository is tooling, contracts and evidence records, not Android source.

## Read first

1. `AGENTS.md` holds the working rules and the definition of a meaningful
   test. Follow it; this file only adds orientation.
2. `docs/workspace-status.md` selects the current baseline, identities, hashes
   and next development steps.
3. `docs/roadmap-20260906.md` holds the workstreams, sequencing and the
   decisions already taken (both slots populated, private audience, source
   kernel as the design goal with prebuilt kept selectable).
4. `docs/README.md` indexes every dated record. Old pages describe their own
   checkpoint; do not read a historical gate as a current one.

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

## Layout

| Path | Role |
| --- | --- |
| `config/*.json` | Reviewed contracts: source lock, AVB profiles, construction descriptors, feature inputs. Scripts pin a contract's SHA256; editing a contract means updating the pin and recording why. |
| `scripts/*.py` | Stdlib-only Python tools. Most expose `plan` / `check` / `verify` / `build` subcommands and a `--dry-run`. `plan` reads public inputs only. |
| `tests/` | Offline unittest suite, stdlib only, phones and networks mocked. `support.py` holds shared walkers; discovery does not collect it. |
| `device/xiaomi/nezha/` | Authored product and board source. The tracked `BoardConfig.mk` is a restricted template; `generate_device_tree.py` writes the buildable derivative into an ignored staging root. |
| `kernel/xiaomi/nezha/` | Prebuilt kernel bundle consumer, kernel input contract and the ACK/MiCode config audit. |
| `patches/evolution/`, `patches/twrp/` | Numbered upstream patches, each with a JSON contract holding its hash. |
| `policy/nezha/` | Blueprint entry for the SELinux source integration; the policy inputs themselves are contracts under `config/` and ignored bundles. |
| `recovery/twrp-working/` | The selected `working76` recovery repack workflow. `recovery/twrp-upstream/` and `recovery/twrp/` are preserved source experiments. |
| `research/*.json` | Sanitized public records behind the docs. Tests recompute hashes, links and totals from them. |
| `docs/` | Current status, runbooks and dated evidence pages named `topic-YYYYMMDD.md`. |
| `containers/apple/` | Apple Container + Rosetta builder image for the Linux build volume. |
| `tools/` | Small native probes built in the Android tree: camera metadata probe app, EROFS metadata reader, VINTF definition audit. |
| `templates/` | Source templates for the guarded IMS and workload-classifier integrations. |
| `manifests/` | Deliberately empty. No local device manifest exists yet; the platform comes from the source lock and its snapshot under `research/source-snapshots/`. |

## Commands

```sh
make help                 # every target with a one-line purpose
make test-current         # focused Package7 suite, under a minute
make test                 # full offline suite, about four minutes, run once before finishing
python3 -m unittest discover -s tests -p 'test_NAME.py' -v   # one module, from repo root
make apple-status         # who owns the Linux source volume
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
  Relative links in `README.md` and `docs/*.md` are tested.
- Update `docs/workspace-status.md` when the selected baseline, identity or
  next step changes. Preserve superseded text in the dated archive rather than
  deleting history.
- A record states what was checked, what was not, and what it does not prove.
  Use words like "unverified", "not device-admitted" and "off-device" exactly.
- Every build gets a fresh source/build identity (`nezha.<hash>`). Keep the
  predecessor bundle as rollback evidence.
- Tests earn their place by exercising a script with synthetic input,
  recomputing a hash, link or total from an artifact, or pinning a measured
  value that carries a build decision. Do not write tests that restate a
  record they just read.
- Commit small, descriptive changes as work completes. Do not sweep unrelated
  uncommitted files into a commit.
- Plain language, main point first, no stock phrases or closing summaries.

## Where things stand

- Installed: `nezha.f9e30611efe01b882f9ed0cb`, bundle under
  `artifacts/flash/nezha/package7-ui-camera-shade-20260906-v1/`.
- Development source: `nezha.bc6311b1a714e310eaf1af56` in the existing Linux
  checkout, with display, Dolby, haptics, camera scheduling and refresh
  candidates selected and IMS and workload classifier disabled.
- Open on device: post-unlock userdata, UDFPS icon, shade visuals, camera
  role mapping, IMS. Camera evidence and the persisted-property experiment are
  summarized in `docs/workspace-status.md`.
- Not yet built: OTA packages, a both-slot delivery route, a source kernel.
