# Direct mi_ext care-map source integration

The separately authored [0013 patch](../patches/evolution/0013-direct-mi-ext-care-map.patch)
adds an explicit `mi_ext` care-map path to the pinned
`add_img_to_target_files.py`. Its new
[0014 successor](../patches/evolution/0014-direct-mi-ext-care-map-imports.patch)
admits the exact captured ODM property imports under separately declared boot
selectors. **Neither patch is selected in an active product or source
composition.** The original patch and selector retain their behavior; the
common partition/property lists remain unchanged.

The successor now verifies the content of all 22 authentic ODM property files,
including their two imports and the bare property name that native init
ignores. This removes the source parser's blanket rejection without inventing
a runtime selector tuple. Existing indexed evidence supplies only a historical
hardware SKU; the country code and hardware version remain unbound. The final
Evolution SYSTEM property file still needs artifact-bound qualification.
These source changes do not establish complete target-files, OTA or runtime
success and do not hold the separate compatibility or image work.

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

The [import successor contract](../patches/evolution/direct-mi-ext-care-map-imports.json)
pins a second transition from the exact 0013 output. It changes only that same
Python source file. It does not amend the active 0005–0011 composition, emit a
product selector, stage inputs in the guest or change any image.

## Explicit selection and checks

A future reviewed source/product capability must supply this exact
`META/misc_info.txt` pair:

```text
nezha_direct_mi_ext_care_map=factory-system-fingerprint-v1
```

Absence selects the original behavior. An unknown or empty value fails. No
existing generator emits this field; manually adding it to an otherwise
unqualified package is not an admission procedure.

The import successor accepts a separate value:

```text
nezha_direct_mi_ext_care_map=factory-system-fingerprint-odm-imports-v2
```

It also requires exactly these three selector declaration fields, with no
default values:

| Metadata field | Native global property |
| --- | --- |
| `nezha_care_map_odm_import_sku` | `ro.boot.product.hardware.sku` |
| `nezha_care_map_odm_import_country` | `ro.boot.ptcountrycode` |
| `nezha_care_map_odm_import_hwversion` | `ro.boot.hwversion` |

These fields declare the inputs being checked. They do not prove the bootloader
or property service will supply those values. No current tuple is populated by
this work. The historical August 27 SKU observation in
[the VINTF record](vintf-contract.md) is `nezha`; no indexed collection record
was found for the other two properties. The baseline's `reported_hwc` is a
different property and is not substituted.

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

## Property boundary and preserved first profile

Pinned init explicitly loads `/system/build.prop`, while the packaging reader
prefers `SYSTEM/etc/build.prop`. Init later loads other partition properties,
supports recursive imports and permits readonly overrides during its vendor
hook. The common packaging parser does not model all of that behavior.

The first constructor checks ordinary canonical files for SYSTEM,
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
file. No runtime-proof flag can override that rejection. The 0013 selector
continues to reject this file.

The 0014 selector separately checks the exact original importer and all 21
candidate files against their content hashes. The table comes from the full
3,059-entry original ODM inventory; every `.prop` member is one of those 22
regular files directly under `/etc`. All 22 must remain present, even if the
declared selectors choose only two of them. Missing or changed files, extra
`.prop` entries, symlinked paths, hardlink aliases, nested imports, filtered
imports and any SYSTEM fingerprint assignment fail. The entire closure and
selector declarations are rechecked before the SYSTEM marker is accepted.

Pinned `ExpandProps` reads global properties, not the accumulating property
file map. It appends their values verbatim, without recursive expansion.
Consequently the successor requires SKU `nezha` and nonempty ASCII selectors
that form single filename components: a letter or digit first, then letters,
digits, underscore, dot or hyphen, with at most 92 characters. Empty, `unknown`,
path-valued, whitespace-bearing and dollar-bearing declarations fail. No
assignment in a captured `.prop` file is used to supply these values.

For a selected basename in the original table, the helper records
`captured-file`. A safe basename outside that complete table is accepted only
when the actual property directory still matches the table and the selected
path is absent; it records `inventory-proven-absent`. This models native init's
missing-file outcome explicitly and does not call it a successful load. A
missing expected captured file always fails. Actual runtime values outside
the admitted component syntax are not covered by this static qualification.

The native loader also ignores lines without `=`. The original importer has
one such line, `ro.vendor.mitee_support` at line 480. The successor admits only
that exact statement in the hash-bound original importer; it does not relax
the original selector or ignore arbitrary malformed property files. Parsing
uses literal LF and ASCII space/tab boundaries, without Unicode line splitting.

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

The first implementation run passed **46 focused tests with zero skips**. The
existing mi_ext input suite separately passed **66 tests with zero skips**.
Independent review reproduced and resolved one property-parser discrepancy:
the new check now uses init's literal LF boundary and does not normalize
Unicode separators into an apparently matching fingerprint. The coordinator
owns the full workspace test run before committing this slice.

The successor adds **38 offline tests with zero skips**:

```sh
python3 -B -m unittest discover -s tests -p 'test_mi_ext_care_map_imports.py' -v
```

These tests execute the actual patch with explicitly synthetic property-content
fixtures. A separate host replay uses all 22 unmodified captured files (30,300
bytes) and the complete original inventory. All 54 combinations of the three
captured country filenames and eighteen hardware filenames resolve to two
captured files. Those combinations are declared test inputs, not observed
device values. The replay also checks explicit absent-file behavior and
refuses both an undeclared tuple and a missing final `SYSTEM/build.prop`.
It neither creates a final SYSTEM fingerprint nor opens an image.

The new ignored evidence and finite native-check preparation live under
`reports/oem-policy-integration-20260829/mi-ext-care-map-imports-v2/`.
The native plan retains missing tool/producer bindings as required inputs.
Its proposed codec fixtures are synthetic and cannot qualify final image
coverage. No native init, protobuf command or ordinary target-files build is
counted as executed by this source work.

The ignored implementation record is
`reports/oem-policy-integration-20260829/mi-ext-care-map-implementation-v1/`.
It contains strict replay against the complete captured source, the unchanged
upstream test identity, independent review, and a source probe using the real
pinned AVB parser and RangeSet. That probe rehashes the original `mi_ext` and
small factory root-vbmeta images read-only, checks their identical direct
descriptor, derives the exact data-only range and demonstrates refusal of
the authentic ODM imports. Its positive property case is explicitly
synthetic. None of these results is native care-map/protobuf or boot evidence.

Before either source transition can be selected, bind the declared boot
selector tuple and its provenance, qualify the final Evolution SYSTEM input
and selected init configuration, compose the additional source hashes
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
