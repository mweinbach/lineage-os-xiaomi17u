# Factory mi_ext inputs and native packaging

The Xiaomi 17 Ultra factory image set contains an A/B logical `mi_ext`
partition. The reviewed A image is **111,198,208 bytes**, SHA256
`60f791178bed4694870be74190b4487d9371af575e18ffbc950fb91fdb97e196`.
Its existing SHA256 hashtree descriptor belongs directly to root `vbmeta`.
It has no separate child signing key or rollback location in the recorded
factory chain. The empty B record in the factory package does not remove A/B
support. See the [factory validation](factory-firmware-validation.md) and
[input contract](../config/nezha-mi-ext.json).

The native source change is an explicit prebuilt custom-image path in pinned
Evolution `build/make` commit `a438ca40c6ed779042f806142b1165ba1360a7b2`.
[Patch 0007](../patches/evolution/0007-direct-avb-custom-images.patch) follows
the preserved 0005 recovery consumer on `core/Makefile`; its
[source contract](../patches/evolution/direct-avb-custom-images.json) records
each pre/post identity and the releasetools semantics, including the separate
[A/B-only recovery packaging change](recovery-packaging.md).

The direct custom-image selector requires one canonical image and its expected
SHA256, copies the image unchanged, checks both input and output digests, and
runs native `avbtool verify_image`. It exposes `INSTALLED_MI_EXTIMAGE_TARGET`
and a `mi_extimage` target. The native root `vbmeta` rule includes the image's
existing descriptor, and target-files metadata registers it as an AVB custom
image while omitting child-key fields entirely. Empty key metadata would
incorrectly select re-signing in the pinned packaging tool.

For this dynamic partition, the custom-image flash entry before userspace
fastboot is suppressed. The existing entry after `update-super` remains.
`BOARD_MI_EXT_IMAGE_NO_FLASHALL` must stay absent: the pinned build also uses
that setting to remove the image from the update ZIP. Suppressing only the
early duplicate preserves the required image entry.

## Private staging and admission

`scripts/mi_ext_inputs.py` uses the reviewed public controls and the exact
factory extraction receipt. It never modifies the source image, builds a new
filesystem, signs an image, runs firmware, or accesses a phone. Staging must
use a fresh ignored directory:

```sh
mkdir -p artifacts/mi-ext-inputs
python3 scripts/mi_ext_inputs.py stage \
  --image artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/logical-partitions/mi_ext_a.img \
  --logical-receipt artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/logical-partitions/receipt.json \
  --output artifacts/mi-ext-inputs/nezha-factory-new
python3 scripts/mi_ext_inputs.py verify \
  --bundle artifacts/mi-ext-inputs/nezha-factory-new
```

The bundle has three private members: `mi_ext.img`, `logical-receipt.json`,
and `mi-ext-inputs.json`. The generator's explicit `--mi-ext-inputs-receipt`
option binds that receipt to the selected factory vendor package and normalized
layout. Only that selection adds `mi_ext` to the existing logical group and
A/B payload list. It leaves the seven standard generated-filesystem settings
unchanged: `mi_ext` is an opaque prebuilt. Default candidates remain unchanged.

The generated `mi-ext-prebuilt.mk` checks the native source hashes and exact
private image/provenance bytes before selecting the build variables. Conflicting
image paths, duplicate selectors, signing settings, chained ownership and
image-ZIP exclusions fail instead of selecting another behavior. Full-ROM,
target-files, super, OTA and flash admission remain false.

Transfer only the prepared private bundle to
`vendor/xiaomi/nezha-mi-ext` in the existing Android checkout. Reverify its
destination bytes using a trusted copy of the workspace controls; do not use a
bundle-supplied receipt as its own authority. Supplying `--source-tree` also
checks the actual composed native consumer files:

```sh
python3 scripts/mi_ext_inputs.py verify \
  --bundle /work/evolution/vendor/xiaomi/nezha-mi-ext \
  --source-tree /work/evolution
```

This command belongs in the already authorized build environment. It does not
attach a source volume, apply patches, enable a blocked build target, or admit a
device operation. Preserve the sole-writer constraints in
[Apple Container](apple-container.md).

## Evidence and remaining checks

The staging tests use inert files and mocked process/network boundaries. The
source probes exercise the actual patched Make expressions with host GNU Make.
These differ from a native Android/Kati component build. A host run of pinned
`avbtool` against the copied factory image verified its footer and SHA256
hashtree with the original bytes unchanged. Its embedded footer algorithm is
`NONE`; root `vbmeta` supplies the signed descriptor in the final ROM chain.
This check does not authenticate an OEM key or cryptographically verify FEC.

Before native adoption, run the actual generated board include and composed
core consumer through Kati, including override/duplicate cases. Build
`mi_extimage` and inspect the executed copy and AVB commands, actual installed
image hash, and root-vbmeta descriptor arguments. Target-files, update-ZIP,
super and OTA checks remain separate, gated work requiring the complete image
set. The selected metadata/image checker is available for real artifacts:

```sh
python3 scripts/mi_ext_inputs.py check-packaging \
  --misc-info /path/to/extracted-target-files/META/misc_info.txt \
  --fastboot-info /path/to/extracted-target-files/META/fastboot-info.txt \
  --ab-partitions /path/to/extracted-target-files/META/ab_partitions.txt \
  --images /path/to/extracted-target-files/IMAGES
```

It checks exact registration, Nezha group budgets and logical inventory, A/B
membership, image bytes and one correctly ordered flash entry. It does not
validate the entire target-files package, signed AVB chain, update ZIP or super
image. The pinned super builder can return without producing an image when an
input is missing, so require an actual output, inspect all LP metadata copies,
and compare extracted logical-image hashes. An exit status alone is inadequate.

The generated fstab retains the required `mi_ext` first-stage mount at
`/mnt/vendor/mi_ext`, with `slotselect`, `logical` and `avb=vbmeta`. The factory
framework overlay rows remain omitted. Adding the partition does not activate
its nested Xiaomi libraries, apps, permissions or overlays, nor prove camera
or accessory compatibility. Those integrations need explicit dependency and
capability review. Current ROM gates remain in
[workspace status](workspace-status.md).
