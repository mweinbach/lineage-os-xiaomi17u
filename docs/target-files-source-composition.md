# Explicit combined packaging source composition

The [new source descriptor](../patches/evolution/target-files-source-composition.json)
joins the reviewed recovery, partition-property, metadata, readonly-variable and
shipping-API changes without changing their historical contracts. Its explicit
selector is `nezha-target-files-source-composition-v1`. The platform remains
Evolution `bka` at build/make commit
`a438ca40c6ed779042f806142b1165ba1360a7b2`.

The canonical order is **0005, 0006, 0007, 0008, 0009, 0010, 0011**. The complete
source closure has ten files: the metadata composition's nine files, plus
`core/product.mk`. The final `common.py` is the exact 0008 output, and the VINTF
wrapper is the exact [0011 output](vintf-shipping-api.md). No source file is
accepted solely because a patch command succeeds.

| Core transition | Required complete preimage | Complete output |
| --- | --- | --- |
| Canonical 0010 after metadata 0009 | `af8af76a36d6d2303dba471545bc2e36e15347211d9c96a4145a1ea3c6351d8b`, 392,075 bytes | `bf6e0668ff571f3858fc09d5cefa039ff6a8fdebf5b9ecfdc690794f25889ba7`, 392,084 bytes |
| Metadata 0009 after the existing readonly base | `77e4a7aa8f2094d116de233b2c46b21103694df66bc8d426ce1f6e4b1043329b`, 388,718 bytes | The same 392,084-byte output |

The frozen 0010 contract describes its original 0005/6/7 preimage. The new
descriptor records the additional transition explicitly; it does not rewrite
that old contract. The recorded existing readonly base upgrades with **only
0008, 0009 and 0011**, after verifying its entire ten-file preimage. Existing
patches do not need to be reset or reapplied. The two additional unmodified
preimage files are the pinned APEX utility and original VINTF wrapper.

The descriptor also binds the complete 31,527-byte `core/product.mk` and its
110-byte `readonly-variables` definition, including `define`, `endef`, and the
terminal newline. It retains the incoming-setting guards and empty defaults
required by the [readonly correction](../patches/evolution/direct-avb-readonly.json).

## Preserve historical selections

These serialized compositions remain unchanged:

| Existing selection | Composition SHA256 | Bytes |
| --- | --- | ---: |
| 0005/6/7 | `fe4ac5f9c0db04df0d8af9e5867edf2090310b34f03d96f7856d105aa35c5abe` | 3,516 |
| Metadata 0005–0009 | `6cc3a2bc48603a8eb8b15082252350dc550c0dfc669af24d96e6b4e1a317ad0f` | 3,971 |
| Readonly 0005/6/7/0010 | `ee4946fd7c2da9814c1115b95108768844b53c5d293761493ab1f50ed67e5b9c` | 4,401 |

The original [metadata tool](../scripts/target_files_metadata.py), its profile,
the seven source contracts, the patches, and historical private receipts remain
unchanged. The combined path has its own descriptor and fresh receipts. It does
not infer a selection from whichever source hash happens to be present.

The [new metadata adapter](../scripts/target_files_metadata_combined.py) preserves
the original capture, image, kernel-metadata and publication checks. It derives
one self-contained native verifier from the exact frozen base tool and reviewed
adapter. The assembly checks the base hash, exact main boundary and counted
substitutions. Both public source inputs and the resulting native tool are bound
into the fresh bundle. The unchanged 0009 build hook verifies the selected
native tool SHA256 before `python3 -I -S -B`; the native tool does not import an
unverified workspace composer.

The original image profile still admits only the original factory vendor/ODM
pair and all **205 authentic metadata payloads**: 24 property files, 178 VINTF
files and three APEX files. The new descriptor adds source integration; it does
not change those payloads or allow policy-bearing image derivatives. Such images
need separate complete content and filesystem-metadata derivation evidence and
a separately reviewed admission path, rather than edited expected image hashes.

## Source verification and selection

The [host verifier](../scripts/target_files_source_composition.py) checks all ten
complete final files and the readonly macro. Optional replay applies each patch
only in memory, at its exact hunk positions, verifying every complete before
and after hash and every final byte. It does not write Android sources.

```sh
python3 scripts/target_files_source_composition.py \
  --source-tree /private/prepared/combined-source \
  --predecessor-source-tree /private/captured/original-source

python3 scripts/target_files_source_composition.py \
  --source-tree /private/prepared/combined-source \
  --predecessor-source-tree /private/captured/readonly-source \
  --predecessor readonly
```

Use the explicit new contract while staging and verifying the new metadata
bundle with `target_files_metadata_combined.py`:

```sh
python3 scripts/target_files_metadata_combined.py stage \
  --source-contract patches/evolution/target-files-source-composition.json \
  --inputs-root /private/original-captures \
  --output /private/new-combined-metadata-bundle \
  --vendor-image /private/original/vendor.img \
  --odm-image /private/original/odm.img
```

Recovery and mi_ext staging use their existing `--composed-source-contract`
option with this exact new descriptor. Device generation uses the new
`--target-files-source-contract` option together with the existing metadata
receipt and its external expected SHA256. It must not also select the separate
base `--direct-avb-readonly-contract` option. Fresh recovery and mi_ext receipts
must agree on the same combined source composition. Historical selectors retain
their original behavior.

The adapter requires explicit selection for host staging and verification.
During native installation, the unchanged hook supplies the external metadata
receipt digest; the verifier checks that admission before accepting the exact
known combined descriptor copied into the bundle. Unknown descriptors and
source-hash fallback are rejected.

## Evidence boundary

The August 29 host preparation reproduces both the seven-patch canonical chain
and the three-patch readonly upgrade with identical final ten-file contents.
The captured core already contained 0005: preparing the original preimage
reversed that exact patch, checked the historical full-file preimage hash, and
replayed it forward. Captured originals remain untouched. The preparation,
before/final source closures and replay records are under the ignored
`reports/oem-policy-integration-20260829/target-files-source-composition-v1/`.

The focused source-verifier suite passes **30 tests with zero skips**. A separate
independent replay is recorded in
`reports/oem-policy-integration-20260829/combined-source-admission/independent-replay-v1.json`.
The new adapter passes **33 focused tests**, and the unchanged legacy metadata
suite passes **45 tests**, all with zero skips. The fresh combined metadata
bundle and its repeat match across all 234 files including the receipt; all 205
metadata payloads, image bindings and property-import closure match the preserved
v4 bundle. Its receipt SHA256 is
`8c1c78d19d786fee2be6c92a3f93fd28677ab24500f74da3bb911f96e6de89df`
(197,440 bytes). The packaged 64,462-byte verifier, SHA256
`8f050bd146f1136a496ba9adf80281abab4dee4d31a579df7a7f3c0dc6ece59e`,
passes an actual host `python3 -I -S -B` verification with all ten source files
and both original image hashes. It was not run inside an Android build.
The positive isolated entrypoint runs used `verify` and `selection`. An
independent negative `install` probe with deliberately missing images stopped
before publication. No successful metadata installation, target-files
construction or live guest source upgrade ran for this checkpoint.
The complete workspace suite passes **3,452 tests with zero skips**.

These are host source and tooling results. Native component builds, complete
framework/vendor/kernel/APEX VINTF compatibility, target-files, AVB, super and
OTA validation, policy-image adoption and device boot remain separate gates.
No complete-ROM readiness flag or phone authorization changes.
