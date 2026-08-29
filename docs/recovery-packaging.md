# Dedicated TWRP recovery in A/B target-files

Nezha must carry the exact working76 image as its **dedicated A/B recovery
payload**. It must not invent a `recovery-two-step.img` by copying that image.
The pinned non-A/B updater writes the two-step image into **boot** before
updating recovery. Working76 is kernel-free and 100 MiB; Nezha's measured boot
budget is 96 MiB. It is not a substitute boot image.

The [0006 follow-up patch](../patches/evolution/0006-ab-only-recovery-packaging.patch)
fixes an inappropriate packaging requirement in the selected `bka` source. It
constructs the two-step image only when non-A/B updates are supported. A/B-only
products retain the required ordinary recovery image without requesting the
unused non-A/B artifact. The original assertions remain active for non-A/B and
hybrid products. Missing ordinary recovery still fails in every applicable
mode.

This is a source integration change, not an OTA or boot result. The
[source contract](../patches/evolution/ab-only-recovery-packaging.json) preserves
the distinction. Complete target-files, OTA, super and flash admission remain
false until their other gates pass. Follow [current workspace status](workspace-status.md)
for actual source adoption and native build results.

## Pinned source semantics

The reviewed build project is Evolution `bka` commit
`a438ca40c6ed779042f806142b1165ba1360a7b2`. A read-only August 29 capture matched
its existing reviewed 0005 recovery consumer and the unchanged releasetools
sources. The follow-up changes only
`build/make/tools/releasetools/add_img_to_target_files.py`.

| Consumer | Relevant behavior |
| --- | --- |
| `non_ab_ota.py`, `_WriteRecoveryImageToBoot`, line 680 | Chooses the two-step recovery and writes it to `/boot`; its fallback is also inappropriate for Nezha. |
| `common.py`, `_FindAndLoadRecoveryFstab`, line 1261 | Already omits recovery-fstab loading when `ab_update=true` and `allow_non_ab` is not `true`. |
| `common.py`, `GetBootableImage`, line 1961 | Returns `BOOTABLE_IMAGES/recovery.img` unchanged before considering a generated or re-signed image. |
| `ota_from_target_files.py`, line 1446 | Rejects forced non-A/B generation unless `allow_non_ab=true`; chooses the A/B generator otherwise. |
| `add_img_to_target_files.py`, original line 1031 | Previously attempted two-step construction whenever a new dedicated recovery image was added, including A/B-only products. |

The patch uses the same A/B-only distinction as the pinned fstab loader. It
does not set `no_recovery`, remove recovery from the payload list, provide a
fake `RECOVERY/RAMDISK`, alter AVB signing, or relax checks. The ordinary
recovery partition entry, required-image assertion, output copy and ZIP entry
remain unchanged. It also preserves upstream behavior for an already present
`IMAGES/recovery.img`; this narrow patch does not redesign incremental
target-files repair.

| Input/update mode | Ordinary recovery | Two-step recovery |
| --- | --- | --- |
| A/B-only, new image | Required, exact prebuilt copied to `IMAGES/recovery.img` | Not requested or emitted |
| Non-A/B, new image | Required | Still required; missing input or failed construction raises the original assertion |
| Hybrid A/B with non-A/B allowed | Required | Still required |
| No recovery configured | No recovery operation | No two-step operation |

The ordinary image's destination remains a dedicated recovery slot. The
100 MiB size, SHA256, header-v4 format, signature, rollback index/location and
public-key checks remain the responsibility of the existing
[working recovery workflow](../recovery/twrp-working/README.md) and
[recovery input consumer](../device/xiaomi/nezha/recovery-prebuilt.mk).
No private key is needed by this follow-up or its probe.

## Reproduce the source and Python checks

Preserve the existing checkout, local patches and working76 input. Apply the
reviewed follow-up to the exact pinned build project after checking its
before identity; do not initialize or sync a replacement source tree. The
original 0005 patch stays separate because it changes `core/Makefile`, while
0006 changes only the releasetools Python file.

| `add_img_to_target_files.py` state | Bytes | SHA256 |
| --- | ---: | --- |
| Pinned upstream | 48,004 | `9ace653e00cc3635ae476d15e03b44b7bf6c70898497c343bf41f6ce521dbd98` |
| With 0006 | 48,289 | `ef2e4014238ad323e8157a3bf80190d1795f01b6dd0c087b5e8c2cc167a43c51` |

From the workspace or a hash-verified control bundle, run:

```sh
python3 scripts/recovery_packaging.py check-source --source-tree /work/evolution
python3 scripts/recovery_packaging.py probe --source-tree /work/evolution
python3 -m unittest discover -s tests -p 'test_recovery_packaging.py' -v
```

The source checker verifies the patch contract, the changed Python file and
the four pinned semantic files. It is read-only and does not replace the
1179-project source audit.

The optional [0007 direct-custom-image contract](../patches/evolution/direct-avb-custom-images.json)
changes the already patched build core. It does not replace the original 0005
contract. Select this source composition explicitly when that follow-up is
installed:

```sh
python3 scripts/recovery_packaging.py check-source \
  --source-tree /work/evolution \
  --composed-source-contract patches/evolution/direct-avb-custom-images.json
python3 scripts/recovery_packaging.py probe \
  --source-tree /work/evolution \
  --composed-source-contract patches/evolution/direct-avb-custom-images.json
python3 scripts/recovery_inputs.py plan \
  --composed-source-contract patches/evolution/direct-avb-custom-images.json
```

The shared composition checker binds the same pinned project, the ordered
0005/0006/0007 patches, both complete build-core transitions, and all seven
final source files. It refuses a mismatched intermediate core, changed
releasetools semantics, an unreviewed control copy, or conflicting identities.
Neither source checker applies patches or verifies the whole checkout's HEAD;
the separate source audit supplies that evidence.

Use the same explicit option with `recovery_inputs.py stage` and `verify` for
a **new** private recovery bundle. Its receipt records the composition and its
Make include binds the composed core identity. The image and public PEM remain
byte-identical. Do not overwrite the previous bundle or change the original
0005-only record to describe the composed source. Omitting the option retains
the original behavior and fails against a different core; it does not infer a
new source selection from whichever files happen to be installed. Stage and
verification use only the public key, never the signing key.

The `make recovery-plan`, `recovery-stage` and `recovery-inputs-verify` wrappers
accept the optional `RECOVERY_COMPOSED_SOURCE_CONTRACT` variable and forward it
to the same commands. Its default is empty. `recovery-build` and
`recovery-verify` remain the unchanged working76 image workflow.

The probe first verifies those complete source bytes, then executes only the
actual recovery branch, `GetBootableImage`, and the bounded OTA-mode/fstab
decisions. Its temporary files contain inert synthetic bytes. Native image
builders and signers are not run. The 12 recovery cases cover ZIP and directory
output, existing and missing ordinary recovery, non-A/B and hybrid failures,
distinct non-A/B two-step input, and unknown mode values. Separate decisions
confirm the forced non-A/B rejection and the A/B-only fstab behavior.

On the captured source with 0006 applied locally, all 12 cases passed. The
17 focused offline packaging tests also passed. The recovery-input tests cover
the explicit composition, retention of the old bundle and failure on changed
sources or control records. Their synthetic inputs and
expected failures are test cases, not skipped build checks. These checks do
not build Android target-files, validate AVB image content, sign an OTA, test
recovery installation, or access a phone. The actual target-files build remains
a separate gated milestone.

## Remaining packaging requirements

Removing this inapplicable requirement does not fill other missing images.
`mi_ext`, full VINTF and policy labeling, signing keys and complete AVB
descriptors, exact partition budgets, snapshot/slot behavior and payload
trust still need their own integration and validation.

In particular, a successful pinned packaging command is insufficient evidence:

- `build_super_image.py` can return without producing a super image when
  required input images are missing, while its CLI does not propagate that
  return value as an error. Its direct-info path can also construct a zero-size
  partition from a missing image setting. Require the output, inspect its LP
  metadata and compare each extracted image against the admitted inputs.
- The pinned `validate_target_files.py` file-consistency check covers selected
  sparse system/vendor images and skips non-sparse images. Its OTA-key
  reconciliation is explicitly unfinished. Independently check the actual
  recovery bytes, metadata, signatures, image inventory and update trust.
- Packaging the factory `mi_ext` does not activate its OEM framework overlays.
  Restoring those without a dependency, privilege and capability review could
  introduce new Android inputs unrelated to the bounded policy admission.

No packaging check authorizes a phone change. Follow the
[recovery handling rules](recovery-plan.md), preserve stock companion and return
paths, and obtain a fresh explicit request before reboot, flash, slot changes,
wipe, unlock or relock. Never relock on the development signing key.
