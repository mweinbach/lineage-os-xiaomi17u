# Release runbook: source to bundle

This page records the sequence that produced the installed `f9e` build and
turns it into the single path a future identity follows. It is the first step
of the [roadmap's](roadmap-20260906.md) release workstream. Where a stage still
runs through a private per-build adapter under `reports/`, the runbook says so;
absorbing those adapters into maintained scripts is the next increment.

`scripts/release_workflow.py plan` prints this sequence with concrete commands
for a chosen identity, and `check` reports which stage receipts exist for it.
Neither dispatches a build, signs, or touches the phone.

## Preconditions

Every run starts by checking these; the wrapper refuses otherwise.

| Check | Command or record |
| --- | --- |
| Sole writer on the Linux source volume | `make apple-status`; exactly one `active_volume_users` entry and no live Soong, Ninja or Kati process |
| Host and guest capacity | 100 GiB host reserve and the runner's 200 GiB guest reserve, rechecked per stage |
| Upstream base unchanged | `python3 scripts/workspace.py check-source --source-dir /work/evolution --source-lock config/evolution-source-lock.json` inside the guest |
| Selected source inventory unchanged | The runner rehashes every row of the installed-source record before and after each native stage |
| Offline suite | `make test` passes on the host at the commit being released |
| Input closure | `python3 scripts/input_closure.py verify --manifest <closure.json>` matches the committed tree and present private receipts |

## Stages

Each stage names its owner, the maintained script or private adapter that ran
for `f9e`, its inputs, its output receipt, and the gate that admits the next
stage. Identity means the build number `nezha.<24 hex>` and the artifact set
ID `<name>-<date>-v<N>`.

### 1. Select source and record the inventory

- Owner: host, reviewed source transaction.
- Ran for f9e: the transaction under `reports/feature-fixes-20260905/` that
  installed the shade source and wrote `source-installed.json` with 574 rows;
  the current selection is the 603-row record under
  `reports/feature-merge-20260906/`.
- Output: `source-installed.json` with `build_number`, `transaction` and
  `source_inventory` rows of path, size, mode and SHA256.
- Gate: the record hashes cleanly and the build number is new. A build never
  reuses a predecessor identity.

### 2. Generate the device candidate

- Owner: host, `scripts/generate_device_tree.py generate` with the complete
  user / 4 KiB / matrix / policy-image-delivery recipe and
  `--rom-construction-source-contract config/nezha-rom-construction-source-v1.json`.
- Output: a new ignored `artifacts/device-candidates/<name>/` with
  `admission.json` and the generated `rom-construction.mk` guard.
- Gate: `generate_device_tree.py validate` passes and the guard bytes match the
  contract. The [variant opt-in](build-variant-opt-in-20260906.md) selects
  `userdebug` only through the explicit environment key.

### 3. Native preflight and target-files package

- Owner: guest, private runner. For f9e, `reports/feature-fixes-20260905/build_successor.py`;
  for the current source, `reports/feature-merge-20260906/build_successor.py`.
- Sequence: `nothing`, then `recoveryimage`, `mi_extimage`, `vendorimage`,
  `odmimage` and the three sepolicy digest modules, then the sole
  `target-files-package` goal.
- Output: a run directory under `/work/validation/<family>/<timestamp>` with
  `request.json`, `build.log`, `result.json` and source before/after records;
  the archive under
  `<OUT>/target/product/nezha/obj/PACKAGING/target_files_intermediates/`.
- Gate: exit 0, source unchanged, and a read-only package admission that binds
  the archive hash, the expanded tree and every `IMAGES/` role to the source
  record (`native_package_f9e.py` for f9e).

### 4. Transfer the archive to the host

- Owner: host, `scripts/target_files_archive_copy.py` through the per-build
  transfer adapter (`package_transfer_f9e.py`).
- Output: `artifacts/build-validation/<set>-package-transfer-v<N>/lineage_nezha-target_files.zip`
  and its transfer receipt with matching native and host hashes.
- Gate: full-archive hash equality and a complete host readback.

### 5. Inventory, materialize, sign, reconcile

- Owner: host. For f9e, `run_f9e_successor_signing.py`; for the next
  identity, `scripts/release_signing.py run` with a pinned selection (see the
  [release tooling record](release-tooling-20260906.md)). Both drive the same
  six maintained scripts. Stage logs live under
  `artifacts/avb/nezha/<set>/stage-logs/`.

| Log | Script | Purpose |
| --- | --- | --- |
| `01-inventory` | `target_files_avb_inventory.py inspect` | Hash the 13 data roles and two vbmeta roles in the ZIP; bind countrycode and pvmfw from the retained-input manifest |
| `02-materialize` | `materialize_target_files_inputs.py` | Write the exact inventoried images to `inputs-v1/` for the signer |
| `03-prepare` | `avb_signing.py prepare` | Derive the signing plan from `config/nezha-avb-signing.json` |
| `04-sign` | `avb_signing.py sign` | Sign with the development key from ignored local configuration |
| `05-reconcile` | `reconcile_signed_target_files.py` | Stream the signed images into a fresh reconciled ZIP, replacing only the permitted roles |
| `06-published-inventory` | `target_files_avb_inventory.py inspect` | Re-inventory the reconciled ZIP and publish `published-inventory.json` |

- Gate: all six exits are zero, the signing receipt reports a fully verified
  chain, and `published-inventory.json` lists all 17 roles.

### 6. Assemble Super and read it back

- Owner: guest for assembly, host for transfer. For f9e,
  `reports/feature-fixes-20260905/f9e-super-prep/run.py prepare-current`,
  then `assemble`, then readback through `scripts/logical_partitions.py`.
- Output: the sparse Super under `artifacts/build-validation/<set>-super-transfer-v<N>/`
  with `transfer.json`, and the LP readback completion receipt.
- Gate: every logical image fits its bound, the group total fits the
  15,290,335,232-byte maximum, and native, stream and host hashes agree.
- Note: this stage populates logical A only, which is the Virtual A/B layout
  stock also uses. The both-physical-slot route keeps this Super and adds the
  B-chain writes; see the [update mechanism record](update-mechanism-20260906.md)
  and `scripts/delivery_route.py`.

### 7. Qualify off-device

- Owner: host and guest adapters under
  `reports/feature-fixes-20260905/f9e-qualification-prep/`.
- Stages: host APK, boot, delivery and classpath checks; VINTF capture; the
  eight-logical FEC readbacks; and the joined `qualification-summary.json`.
- Gate: the summary's `validation` block reports the offline test count, exit
  zero for the native package, four host stages, VINTF completed and FEC
  completed. Findings the APK stage retains are recorded, not hidden.

### 8. Plan and assemble the bundle

- Owner: host. `f9e-plan-prep/build_plan.py` joins the five records into the
  delivery plan; `scripts/experimental_flash_bundle.py assemble` copies the
  eight payloads; `verify` rereads the bundle.
- Output: `artifacts/flash/nezha/<set>/` with `manifest.json`, `SHA256SUMS`
  and `README.md`.
- Gate: assembly and verification receipts pass with exactly eight payloads.
  The bundle status stays `not-device-admitted-not-flash-ready`; installation
  is a separate authorization.

### 9. Record

- Update `docs/workspace-status.md` with the identity, bundle path, manifest
  hash and reconciled archive hash. Add a dated page for anything measured.
- Keep the predecessor bundle, its signed archive and the stock return inputs.

## What the wrapper absorbs next

The stages above still depend on per-build copies under `reports/`. The next
increment moves each into `scripts/` with the identity as a parameter:

1. The native runner and its package admission (stage 3).
2. The transfer adapter (stage 4).
3. The signing orchestrator (stage 5): done as `scripts/release_signing.py`.
4. Super preparation and assembly (stage 6), rewritten for the both-slot
   route.
5. The qualification adapters and the joined summary (stage 7).
6. The delivery-plan builder (stage 8).

Each move keeps the identity pins as inputs instead of constants and leaves
the f9e copies untouched as evidence.
