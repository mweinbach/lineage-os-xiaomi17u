# Detailed plans for the next steps — September 6, 2026

Researched plans for the four steps the [roadmap](roadmap-20260906.md) put
next, plus one prerequisite the research surfaced. Each plan states the facts
it rests on with their source, the design, the concrete work items, the tests,
the gate, and what can start while the build VM is busy. Nothing here was
executed on the phone or in the VM; every fact below comes from committed
records, the retained archive metadata, or the pinned upstream trees.

## Correction: what "both slots" can mean on this device

The roadmap's slot decision needs one correction before the plans below.

- The eight logical images total 9,476,509,696 bytes; the single dynamic
  partition group allows 15,290,335,232 bytes. Two complete copies exceed the
  physical Super by 3,341,697,024 bytes, as the
  [flash-readiness review](flash-readiness.md#delivery-and-device-gates) already
  recorded.
- Stock behaves the same way. The captured factory Super metadata lists
  `system_b` at zero bytes in group `qti_dynamic_partitions_b`
  ([partition metadata record](../research/firmware-layout.json)). Under
  Virtual A/B, Super holds one copy; an update creates the other slot's logical
  partitions through snapshots on userdata and merges after a successful boot.
- Therefore the current Super layout (logical A populated, logical B empty) is
  the correct Virtual A/B layout, not a defect of the route.

What "both slots" can still mean, and what it buys:

| Slot content | Can be pre-populated? | Why it matters |
| --- | --- | --- |
| Logical partitions in Super | No, one copy only | The first OTA into B populates logical B itself. |
| Seven physical images per slot (`boot`, `dtbo`, `init_boot`, `vendor_boot`, `recovery`, `vbmeta`, `vbmeta_system`) | Yes, 14 small writes | Removes the stock boot chain from slot B, gives `working76` on both recovery slots, and keeps `vbmeta_b` consistent with our key. The OTA also writes these from its payload, so this is hygiene and rescue consistency, not a requirement for updates. |

The updates-without-wipe goal is met by the OTA path (plan 2), not by
pre-populating B. Plan 1 is therefore small: extend the fastboot route to write
the physical chain to both slots in the same authorized session as the next
full install.

## Plan 1: both-physical-slot delivery route (C.1)

Facts, from the [bootloader preflight](device-preflight-20260905.md) and the
[f9e installation](package7-f9e-install-20260906.md):

| Observation | Value |
| --- | --- |
| `unlocked` / `slot-count` / `current-slot` | yes / 2 / a |
| `slot-successful:a` / `slot-successful:b` | yes / no |
| `slot-unbootable:a` / `slot-unbootable:b` | no / no |
| `snapshot-update-status` | none |
| `max-download-size` | 805,306,368 bytes; the install used `-S 512M` for Super |
| `has-slot` | yes for boot, dtbo, init_boot, recovery, vbmeta, vbmeta_system, vendor_boot, countrycode, pvmfw; Super unslotted |
| f9e write order | super, dtbo_a, init_boot_a, vendor_boot_a, recovery_a, boot_a, vbmeta_system_a, vbmeta_a; no wipe, no slot change |

Design:

- A version-2 delivery plan and bundle manifest. The assembler in
  `scripts/experimental_flash_bundle.py` hardcodes the A-only `LAYOUT` and the
  `<role>_a` targets; version 2 adds `physical_slots: ["a", "b"]`, a target
  list of 14 physical writes plus Super, and keeps the same eight payload files
  (each physical image is written twice, not stored twice).
- Write order: Super, then the complete B chain, then the complete A chain,
  each in the f9e order. Slot A is written last so the active slot's `vbmeta`
  is the final write. No `--set-active`; slot switching stays a separate
  authorization.
- Retained firmware: `countrycode` and `pvmfw` are read back for both slots
  and compared with the plan's references. The current preflight compares only
  the selected slot.
- Preflight additions: `slot-retry-count:b`, `slot-unbootable:b` and
  `slot-successful:b` recorded before and after; both remain read-only.

Work items:

1. `experimental_flash_bundle.py`: accept `schema_version: 2` plans with the
   both-slot layout; keep version 1 validation byte-identical for the f9e
   bundle receipts. Manifest `images` rows gain `targets: ["boot_a", "boot_b"]`.
2. Delivery-plan builder: promote `f9e-plan-prep/build_plan.py` into
   `scripts/delivery_plan.py` with the identity and layout as parameters, and
   emit version 2 plans.
3. `device_flash_preflight.py`: add the B-slot variables and the B-slot
   retained-firmware readback to the fastboot allowlist.
4. Install runner template: a reviewed per-session script with the 15-write
   order, current-slot recheck before every write, and per-write receipts, as
   `install_f9e_authorized.py` does today.
5. Tests: version 1 plans still validate; version 2 plans reject a missing
   slot, a Super target other than `super`, or a physical image without both
   targets; the write order is asserted.

Gate: an assembled version-2 bundle with passing `verify`, plus a preflight
showing slot A active and snapshot status `none`. Installation still needs an
explicit request.

Can start now: items 1, 2, 3 and 5 touch host tooling only. Item 1 waits until
the other thread's userdebug bundle is assembled, since it uses the same script.

## Plan 2: full A/B OTA package off-device (C.4)

Facts, from the [update mechanism record](update-mechanism-20260906.md) and the
f9e archive:

- `ab_update=true`, `virtual_ab=true`, `virtual_ab_cow_version=3`, no
  compression flag; `META/ab_partitions.txt` lists 15 partitions;
  `META/care_map.pb` and `META/update_engine_config.txt` (payload 2.9) exist;
  no `META/postinstall_config.txt`; `META/otakeys.txt` is empty and
  `SYSTEM/etc/security/otacerts.zip` contains only `testkey.x509.pem`.
- `tool_extensions=device/xiaomi/nezha/../common` names a directory absent
  from the 603-row source inventory, and the archive has no
  `META/releasetools.py`, so no device-specific OTA extension runs.
- The f9e package build produced `care_map_generator`, `avbtool` and `lpmake`
  under `host/linux-x86/bin`; `delta_generator` was not observed. The
  `otatools` goal builds it.
- The Evolution Updater at the pinned commit `146a599` has a local-update
  import path (`local_update_import`) and the A/B background-install dialog
  (`apply_update_dialog_message_ab`).
- The reconciled signed archive replaces only three image roles and
  `vbmeta_digest`; `META/` and the other `IMAGES/` members are unchanged, so
  it is a valid `ota_from_target_files` input.
- Checked offline on September 6 against the `working76` ramdisk kept by the
  reproduction build (4,210 members, SHA256 `fe554c9d…`, image equal to the
  recorded `a130ba75…`): it carries `system/bin/update_engine_sideload`
  (3,082,000 bytes), `minadbd`, `snapuserd` with its init file and
  `libfusesideload.so`, and its init scripts wire the `sideload` USB
  configuration. Its `otacerts.zip` trusts three certificates: a `lineage`
  certificate, a third-party `releasekey` certificate of unknown origin, and
  the AOSP test key whose digest `a40da80a…` equals the ROM's only trusted
  certificate. A test-key-signed package therefore passes both trust lists;
  the third-party release key is a trust boundary to remove when recovery is
  rebuilt from source. Sideload behavior itself remains untested.

Design:

1. Guest, after the VM is free and the sole-writer check passes: build
   `otatools` in the existing OUT with the same runner pattern, record the
   tool hashes.
2. Guest: run `ota_from_target_files --path <OUT>/host/linux-x86 -k
   build/make/target/product/security/testkey -v <reconciled.zip> <ota.zip>`.
   The package key must match `otacerts.zip`, which today means the AOSP test
   key (see plan 3). Expect `payload.bin`, `payload_properties.txt`,
   `care_map.pb`, `apex_info.pb` and `META-INF/com/android/metadata`.
3. Host verification before any device step:
   - package signature with the pinned `check_ota_package_signature.py` and
     the test-key certificate;
   - payload manifest with the `update_payload` library from
     `system/update_engine/scripts` (`paycheck.py --check`), recording each
     partition's `new_partition_info` hash;
   - equality of those hashes with the 15 admitted signed image identities in
     `published-inventory.json`. This binds the OTA to the same bytes the
     bundle carries.
4. Transfer the package to `artifacts/ota/nezha/<set>/` with the existing
   archive-copy pattern and a transfer receipt.
5. Device qualification, each step separately authorized:
   - recovery path first: `adb sideload` through `working76`, which carries
     `update_engine_sideload` (checked above) but has never applied an A/B
     package on this device;
   - in-ROM path: Updater local import, background install, reboot into B,
     `slot-successful:b` observed, retained userdata confirmed;
   - rollback: only possible until the merge completes, because the merge
     consumes the previous slot's logical partitions. Record the merge state
     after boot; a post-merge rollback is a reinstall from the preserved
     bundle, not a slot switch.
6. Later: incremental packages with `-i <previous reconciled.zip>`.

Tests: an offline `scripts/ota_package.py inspect` that opens the package,
parses `metadata`, `payload_properties.txt` and the payload header, and
compares partition hashes with a published inventory, with synthetic fixtures.
No test runs `ota_from_target_files`.

Gate: a package whose signature verifies, whose payload hashes match the
published inventory, and a recorded sideload or in-ROM install.

Can start now: the host inspector and its tests, the transfer receipt schema,
and the `working76` ramdisk check for `update_engine_sideload`.

## Plan 3: release keys (new prerequisite)

Finding: the archive's `META/apkcerts.txt` signs 3,782 APKs with the AOSP
`testkey`, the platform certificate is the AOSP `platform` test key, and
`otacerts.zip` trusts only `testkey`. The build fingerprint's `test-keys` tag
has been noted in past records; the consequence for updates has not. Anyone
holding the public AOSP keys can sign an APK that receives platform-signature
permissions on this device, or an OTA the Updater would accept. Images are
already signed with a private AVB development key; APKs and OTA packages are
not.

Options:

| Option | How | Trade-off |
| --- | --- | --- |
| A. Build-time release keys | Generate private keys on the Mac with `make_key`; point `PRODUCT_DEFAULT_DEV_CERTIFICATE` at a key directory the guest can read (the LineageOS `vendor/lineage-priv/keys` pattern). APKs, APEXes and `otacerts.zip` are right at build time; no post-build re-signing. | Private keys must be readable inside the build VM, which the working rules currently forbid for the AVB key. Mitigation: a separate read-only key volume attached only for builds, never the source volume. |
| B. Post-build re-signing | Run `sign_target_files_apks` in a dedicated signing container with keys mounted read-only, then `add_img_to_target_files -a` to regenerate `IMAGES/`. | Keeps keys out of the build VM, but regenerates every image through releasetools, which the [reconciliation record](signed-target-files-reconciliation.md) deliberately avoided; the Mac AVB signer and every downstream receipt would consume regenerated images. |

Recommendation: prove the OTA mechanism first with the test key (plan 2), then
adopt option A with a dedicated key volume before the build that becomes the
daily driver. Changing the platform key requires a userdata wipe; post-unlock
userdata is not yet established, so the cost is lowest now. This is a user
decision because it touches the key-handling rule.

Work items once decided: key generation and public-certificate record under
`config/`; a source patch or product change selecting the certificate; a test
that the built `apkcerts.txt` no longer names `testkey`; an OTA package signed
with the new release key; a wipe-and-install session.

## Plan 4: kernel bundle provenance kind (D.1)

Facts, from `scripts/kernel_inputs.py`, `kernel/xiaomi/nezha/stock-prebuilt.mk`
and the pinned trees:

- The contract requires `provenance.parent_package_sha256`, `source_kind`,
  `package_kind`, `source_url` and `origin_verified`, and a `validation` block
  that must state `kernel_abi_verified`, `module_signatures_verified` and
  `device_tested` as false.
- The receipt copies `provenance` and `kernel` from the contract; the emitted
  `kernel-inputs.mk` carries `NEZHA_STOCK_INPUTS_PACKAGE_SHA256`,
  `NEZHA_STOCK_KERNEL_RELEASE`, `NEZHA_STOCK_INPUT_AVB_STATUS` and
  `NEZHA_STOCK_INPUT_ORIGIN_VERIFIED`, which `stock-prebuilt.mk` compares with
  `NEZHA_EXPECTED_*` values.
- Two prebuilt bundles exist (`nezha-xiaomi-eu-candidate-v1`, `-v2`, 950
  files each) and must keep validating unchanged.
- The pinned MiCode tree carries `build.config.msm.canoe`, maps `popsicle`,
  `pandora` and `pudding` to `canoe` in `target_variants.bzl`, has
  `configs/canoe_perf.bzl`, `canoe_consolidate.bzl` and `canoe_tuivm.bzl`, and
  Kleaf module lists naming Canoe drivers. Its `android/ACK_SHA` is
  `f1bdb135…`, tag `android16-6.12-2025-06_r8`, Clang `r536225`. The device
  tree repository has `qcom/canoe-*.dtsi` and `.dtso` overlays and
  `platform_map.bzl`.

Design, additive and backward compatible:

1. Contract and receipt: `provenance.kind` with values `prebuilt` or `source`.
   Absent means `prebuilt`, so existing contracts and receipts stay valid. For
   `source`, a required `source_build` block: ACK url, commit and tag; vendor
   url, commit and branch; device-tree url and commit; defconfig path and
   SHA256; build config name and Kleaf target; toolchain identity; and the
   builder host record. `parent_package_sha256` for a source bundle is the
   SHA256 of the canonical `source_build` block, so the existing digest
   checks keep one meaning: identity of the input set.
2. Makefile emitter: add `NEZHA_KERNEL_PROVENANCE_KIND` and, for source
   bundles, `NEZHA_KERNEL_SOURCE_ACK_COMMIT`, `NEZHA_KERNEL_SOURCE_VENDOR_COMMIT`
   and `NEZHA_KERNEL_SOURCE_DEFCONFIG_SHA256`.
3. Consumer: `stock-prebuilt.mk` gains `NEZHA_EXPECTED_KERNEL_PROVENANCE_KIND
   ?= prebuilt`. The existing package checks run only for `prebuilt`; a
   `source` bundle is checked against expected ACK and vendor commits and the
   defconfig hash. Everything below the provenance checks is shared, so
   module stages, DTB, DTBO and boot-header settings are identical for both
   kinds. Rename to `kernel-inputs.mk` consumer later; keep the file name now.
4. Producer for source bundles, a later increment: `scripts/kernel_source_bundle.py`
   that takes a Kleaf distribution directory (Image, `vendor.dtb`, `dtbo.img`,
   staged modules) and the module selection lists from the prebuilt bundle,
   and emits the same layout and receipt with `kind: source`. Load lists and
   blocklists come from the captured stock lists until measured otherwise.
5. Parity checks before any source bundle is selected: the two export/CRC
   readers from the [kernel export contract](kernel-export-contract.md) on the
   built Image, `kernel_config_audit.py` on its IKCONFIG, and the module
   provider audit on the built modules.

Tests: contracts without `kind` still validate; `kind: source` without
`source_build` is rejected; the emitted makefile lines for both kinds; the
existing receipt fixtures unchanged; a synthetic source bundle round trip.

Gate: the two existing prebuilt bundles verify byte-for-byte with the new
tool, and a synthetic source bundle produces a makefile the consumer accepts
under `NEZHA_EXPECTED_KERNEL_PROVENANCE_KIND=source`.

Can start now: items 1 to 3 and the tests. The GKI and vendor module builds
need a Linux x86-64 Bazel host; under Rosetta on the existing volume they
compete with ROM builds for space and the sole-writer lock, so they wait.

## Plan 5: promote the signing orchestrator (A.2)

Facts, from `run_f9e_successor_signing.py`:

- Constants: artifact set, build number, the source record pin, the retained
  input manifest and its hash, the local configuration path, and the
  per-build operation names `admit-feature-successor-f9e-package-v1` and
  `transfer-admitted-nezha-f9e-image-v1`.
- Six stages call maintained scripts in order; each writes
  `<stage>.stdout.json`, `<stage>.stderr` and `<stage>.exit.json` with
  `returncode`; the base directory is created exclusively; Python runs with
  `-B` and optimization disabled; the host must be Darwin arm64.

Design: `scripts/release_signing.py` with the same six stages, where every
constant becomes a field of a selection JSON pinned by `--expected-sha256`:
identity, source record pin with entry count, total bytes and transaction,
target-files pin, package admission and transfer pins with their expected
operation names, retained input manifest pin, and the local configuration
path. `plan` prints the stage commands and validates the selection without
running anything; `run --execute-host-signing` performs the sequence and
writes the same stage logs, so `release_workflow.py check` keeps working.

Work items:

1. Move `validate_selection` into the new module with the operation names and
   pins as inputs; keep every existing assertion.
2. Stage table shared with `release_workflow.py` so the runbook, the checker
   and the orchestrator agree on names.
3. Tests with `subprocess.run` mocked to write the stage stdout JSON: happy
   path, a failing stage preserving logs and stopping, an existing base
   directory refused, a selection hash mismatch refused, and a `plan` that
   opens no private files beyond the selection.
4. Make target `release-sign SELECTION=... SELECTION_SHA256=...`.
5. Leave the f9e orchestrator untouched as evidence.

Gate: `plan` on the f9e selection reproduces the six commands recorded in the
f9e stage logs, argument for argument.

Can start now: all of it.

## Order of work while the VM is busy

1. Plan 5 (orchestrator) and plan 4 items 1 to 3 (kernel provenance): pure
   host tooling with tests.
2. Plan 1 items 2, 3 and 5 (delivery plan builder, preflight, tests); item 1
   after the other thread's bundle is assembled.
3. Plan 2 host inspector (done) and the `working76` sideload-binary check (done).
4. Plan 3 decision from the user; key generation on the Mac can follow
   immediately.
5. When the VM is free: `otatools`, the OTA package, and its host verification.
