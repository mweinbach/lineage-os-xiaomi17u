# Explicit current-policy image delivery

The generator has an optional delivery mode for the reviewed v13i vendor/ODM
leaves and their unchanged factory metadata. It is configuration admission,
not a complete ROM, image installation or hardware result. Existing factory
metadata modes and the standalone 0010 mode keep their previous output when
the new option is absent. The default `userdebug` framework-checks product
remains available; these particular derived leaves require explicit `user`.

Select `--policy-image-delivery-contract config/nezha-policy-image-delivery.json`
only together with the existing metadata receipt and its externally reviewed
SHA256, `--target-files-source-contract`, factory/mi_ext inputs, the exact
current policy and provider-v7 receipts, and the allocator capability. The
generator never selects delivery by reading an unexpected receipt schema.
It rejects a missing paired capability, a different product/device/release or
shipping API, a different policy/provider receipt, and the held 4 KiB profile.
The selected context remains `lineage_nezha-bp4a-user`, Nezha, shipping API 36.

The binding is recorded as `target_files_metadata.policy_image_delivery`.
Factory `images`, the vendor bundle and package provenance retain the original
hashes. `packaged_images` records the two reviewed derived leaves separately,
along with the maintained image contract, current-policy evidence, independent
selected-copy evidence and required source-input receipts. No derived image
body is copied or claimed read by this delivery binding; the existing original
kernel/vendor bundle verification is unchanged. Configuration validation can
verify the portable candidate without reopening a private image bundle.

The metadata consumer requires the four maintained source files documented in
[the delivery adapter](policy-image-delivery.md), all 22 copied controls and
the exact regenerated standalone checker. Copied controls cannot replace the
executing public controls. The original and combined metadata modules remain
unchanged; the delivery modules select a separate schema-3 receipt. The
existing seven-patch, ten-file source composition is unchanged. On the active
0005/0006/0007/0010 source, its remaining changes are exactly 0008, 0009 and
0011, after checking every preimage. No date, care-map or page-size capability
is selected by this integration.

## Generated source changes

Relative to the original-image combined-source candidate, delivery changes
only three device files:

1. `BoardConfig.mk` gains one include immediately after the unchanged
   proprietary `BoardConfigVendor.mk`. The complete existing target guards
   remain byte-for-byte intact. Validation checks the original BoardConfig
   against the unchanged init-helper contract before admitting only this exact
   one-include derivation.
2. `generated/target-files-metadata.mk` selects the exact receipt and checker
   using the same three variables already consumed by 0009. Build core still
   owns their finalization.
3. `generated/policy-image-delivery.mk` requires the original file-owned
   vendor/ODM selectors, AVB, regular nonsymlink input paths, the exact metadata
   receipt, image contract, copy receipt and both final image hashes. It then
   assigns the standard prebuilt variables to the separate image directory.
   It does not use `override` or freeze standard board variables before their
   normal pinned initialization path.

The separate source input directory is `vendor/xiaomi/nezha-policy-images`.
It must contain `images/vendor.img`, `images/odm.img`, `image-admission.json`
and `selected-delivery-evidence.json`, all matching the selected binding.
Creating this directory is a separate independently hashed copy transaction;
the generator does not create it. Preserve both original proprietary images,
their original `BoardConfigVendor.mk`, and the already reviewed validation
copies. A selected-copy receipt proves the earlier independent copies; it does
not prove that a new source directory has already been staged.

The image directory shares a textual prefix with `vendor/xiaomi/nezha-policy`.
The namespace guard permits that spelling only inside the exact generated
delivery include. It still rejects policy namespace exports or alternate image
selectors in any other authored or generated device file.

## Native validation before adoption

Offline generator and adapter tests are separate from the following native
checks. Root coordinates these checks on the sole source-volume writer, after
fresh source/history/OUT and available-disk checks:

- Exercise the exact new include with the pinned Kati, including valid original
  selectors and negative missing/changed files, linked paths, command-line or
  environment selectors, alternate incoming images, and disabled AVB. Confirm
  the ordinary board-config finalization and the existing three-variable hook
  through the actual product route.
- Install the reviewed source composition, refreshed recovery/mi_ext guards,
  metadata inputs and independently copied image inputs through a verified
  transaction. Keep the current allocator, providers, policy and strict 16 KiB
  settings unchanged. Recheck all original inputs and actual destination bytes.
- Run ordinary `nothing`, `recoveryimage`, `mi_extimage`, `vendorimage` and
  `odmimage` component checks under a fresh bounded wrapper. Inspect actual
  producer actions and output identities; an existing identical output is not
  evidence that its producer ran again.
- When complete packaging is separately admitted, exercise the ordinary 0009
  metadata install hook. It must check all ten actual source files, exact
  target-files `IMAGES/vendor.img` and `IMAGES/odm.img`, seven actual framework
  CIL/mapping/genfs inputs and three recomputed framework sidecars before
  publication. An inert target-files fixture cannot establish that native
  construction path.

The current framework-checks target restrictions remain active: target-files,
super, OTA, `bacon`, default `droid` and their blocked aliases are not admitted.
Do not bypass them with raw output paths or nodeps targets. Full allocator-aware
framework/vendor/kernel/39-APEX compatibility, complete images, signing and
root AVB/rollback/partition fit, snapshot/COW, OTA trust and device testing remain
separate gates. The derived leaf footers are keyless `NONE`; this capability
does not claim a signed parent chain.

Installed 0006 already removes the inapplicable two-step recovery requirement
for A/B-only Nezha while preserving the non-A/B/hybrid checks. Do not fabricate
`recovery-two-step.img` or place kernel-free working76 into a boot image.
Working76 recovery and the authentic `mi_ext` bytes remain unchanged. The
inactive care-map and deterministic-date work is not selected here.
