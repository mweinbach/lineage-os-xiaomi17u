# Direct mi_ext care-map source integration

The separately authored [0013 patch](../patches/evolution/0013-direct-mi-ext-care-map.patch)
adds a narrow, explicit `mi_ext` care-map path to the pinned
`add_img_to_target_files.py`. It is **not selected in an active product or
source composition**. Existing profiles retain their behavior and the common
partition/property lists stay unchanged.

The current factory property inputs deliberately cannot pass the new path:
the actual ODM property file contains two unqualified boot-selected imports.
The final Evolution SYSTEM property file also still needs artifact-bound
qualification. This patch supplies the guarded packaging behavior; it does
not establish complete target-files, OTA or runtime success and does not hold
the separate allocator or vendor/ODM footer work.

## Why a separate path is needed

The retained `mi_ext` is an A/B logical partition and already appears in the
AVB custom-image map. The pinned packaging code nevertheless omits it because
it is absent from `PARTITIONS_WITH_CARE_MAP`. Adding it to that shared list
would also expand `PARTITIONS_WITH_BUILD_PROP`, then encounter missing
fingerprint metadata. The authentic `mi_ext/etc/build.prop` has no fingerprint;
an AVB descriptor property is not a runtime `ro.mi_ext.*` property.

The [source contract](../patches/evolution/direct-mi-ext-care-map.json) pins the
single source transition after 0006 and records its dependency on the existing
0005–0011 source composition. The upstream build/make revision remains
`a438ca40c6ed779042f806142b1165ba1360a7b2`, Evolution `bka`. No old contract,
source selector, private receipt or generated product is rewritten. Pinned
`GetCareMap`, the standard partition lists, the existing upstream tests and
the recovery/AVB behavior outside this branch are unchanged.

## Explicit selection and checks

A future reviewed source/product capability must supply this exact
`META/misc_info.txt` pair:

```text
nezha_direct_mi_ext_care_map=factory-system-fingerprint-v1
```

Absence selects the original behavior. An unknown or empty value fails. No
existing generator emits this field; manually adding it to an otherwise
unqualified package is not an admission procedure.

When selected, the branch requires:

- The complete, unique eight-partition Nezha A/B logical set: `system`,
  `system_ext`, `product`, `vendor`, `odm`, `vendor_dlkm`, `system_dlkm` and
  `mi_ext`. It does not invent an `odm_dlkm` logical partition from the real
  nested vendor property directory.
- A/B-only AVB configuration and the existing direct-custom registration for
  exactly `mi_ext.img`. Child signing, chain ownership, synthetic hashtree
  enablement and a fabricated verity-device property are rejected.
- The ordinary, nonsparse retained image, exactly 111,198,208 bytes, SHA256
  `60f791178bed4694870be74190b4487d9371af575e18ffbc950fb91fdb97e196`.
  The image is streamed through SHA256 and parsed read-only with the pinned
  AVB parser. Symlinked paths, changed files and mismatches fail.
- The original sole hashtree descriptor, encoded SHA256
  `c7251f78926feb64f83671a61b4a164f9851948cf12291f1106069f8fac35269`,
  and matching original footer geometry. The current root `vbmeta.img` must
  contain that exact descriptor directly, once, with verification enabled.
  This is a descriptor check, not a claim that the root signature or complete
  parent chain has been verified.
- The 109,445,120 data bytes, or 26,720 blocks of 4,096 bytes, produce exactly
  `2,0,26720`: the half-open range `[0, 26720)`. Tree and FEC bytes are outside
  that range. Android memory page size does not change the consumer's block
  unit. This does not validate FEC parity.
- A genuine `ro.system.build.fingerprint` pair from the canonical runtime
  input `SYSTEM/build.prop`. It must match `system.build.prop.GetProp()` and
  the generated SYSTEM care-map entry. An optional preferred
  `SYSTEM/etc/build.prop` must contain the same pair. Missing, empty,
  `unknown`, duplicate or conflicting definitions fail; no thumbprint,
  computed global fingerprint or invented mi_ext property is substituted.
- All eight resulting entries must be unique, nonempty and have usable
  markers and nonempty canonical ranges. The ordinary native generator is
  then invoked, and its `--parse_proto` result must reproduce every original
  field before the protobuf is copied into target-files. Native command
  failures and incomplete results are not ignored.

The SYSTEM pair is a **freshness marker for the selected artifact set**. It is
not a cryptographic identity for `mi_ext`. The image hash, descriptor, complete
AVB chain, signed target-files and OTA signatures retain their separate roles.

## Conservative property boundary

Pinned init explicitly loads `/system/build.prop`, while the packaging reader
prefers `SYSTEM/etc/build.prop`. Init later loads other partition properties,
supports recursive imports and permits readonly overrides during its vendor
hook. The common packaging parser does not model all of that behavior.

This first constructor checks ordinary canonical files for SYSTEM,
SYSTEM_EXT, SYSTEM_DLKM, VENDOR, VENDOR_DLKM, the real nested vendor ODM_DLKM,
ODM and PRODUCT, plus their standard `build.prop`, `etc/build.prop` and
`default.prop` alternatives when present. It rejects imports and conflicting
SYSTEM fingerprint definitions in those files, rather than implementing a
new native-property interpreter. Named debug-ramdisk property inputs are also
outside this normal-user constructor.

The authentic `ODM/etc/build.prop` contains two imports using boot property
selectors. The preserved capture includes 21 candidate imported files; an
observation that they contain no SYSTEM fingerprint assignment is not yet a
qualified selector/import closure. The actual patched helper rejects this
file. No runtime-proof flag can override that rejection. A later, separately
reviewed source capability may admit the exact captured closure without
changing these original input bytes or weakening the old profile.

The located SYSTEM property capture is stock firmware. It cannot substitute
for the final Evolution SYSTEM file and its image-to-target-files binding.
Even a successful static constructor cannot prove arbitrary vendor hook
behavior or the final runtime value. The selected final init configuration and
eventual authorized runtime test remain independent gates.

## Validation and remaining work

The focused offline suite executes the actual public patch bodies and checks
legacy behavior against the actual prepatch function. Its image-parser,
RangeSet and protobuf process seams are explicitly synthetic. It does not
need a private image, source checkout, native executable, network or phone:

```sh
python3 -B -m unittest discover -s tests -p 'test_mi_ext_care_map.py' -v
```

The implementation run passed **46 focused tests with zero skips**. The
existing mi_ext input suite separately passed **66 tests with zero skips**.
Independent review reproduced and resolved one property-parser discrepancy:
the new check now uses init's literal LF boundary and does not normalize
Unicode separators into an apparently matching fingerprint. The coordinator
owns the full workspace test run before committing this slice.

The ignored implementation record is
`reports/oem-policy-integration-20260829/mi-ext-care-map-implementation-v1/`.
It contains strict replay against the complete captured source, the unchanged
upstream test identity, independent review, and a source probe using the real
pinned AVB parser and RangeSet. That probe rehashes the original `mi_ext` and
small factory root-vbmeta images read-only, checks their identical direct
descriptor, derives the exact data-only range and demonstrates refusal of
the authentic ODM imports. Its positive property case is explicitly
synthetic. None of these results is native care-map/protobuf or boot evidence.

Before this source transition can be selected, qualify the authentic import
closure and final Evolution SYSTEM input, compose the additional source hash
explicitly, and regenerate the source-bound recovery, mi_ext and metadata
receipts while preserving their immutable payloads. Do not edit old expected
hashes or treat current original-image metadata profiles as admitting new
vendor/ODM derivatives.

Then run the pinned upstream tests with their required native tools and no
skipped cases, build the ordinary complete target-files path, independently
parse the actual protobuf and require all eight unique entries. Recheck the
image, SYSTEM marker and protobuf after signing. Verify that the full OTA
contains that exact stored `care_map.pb`; the upstream warning for a missing
file and partial-OTA filtering cannot satisfy complete coverage.

An authorized device test must distinguish actual dm-verity block reads,
snapshot verification and skipped entries. A missing `mi_ext` dm-verity
mapping can fail verification; a mismatched property can skip an entry while
other entries succeed. Process success or `MarkBootSuccessful` alone does not
prove complete coverage. No device action is performed or authorized by this
source work.
