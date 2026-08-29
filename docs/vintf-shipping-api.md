# Forward the genuine shipping API to VINTF

The pinned Evolution `bka` target-files VINTF wrapper reads
`ro.product.first_api_level` only from vendor properties. Nezha's admitted
factory vendor property file lacks that key; the original ODM property file
supplies `36`. The old helper therefore warns and returns no shipping-API
argument, even though the value is available in the loaded metadata.

[Patch 0011](../patches/evolution/0011-vintf-shipping-api-from-odm.patch) changes
only `GetArgsForShippingApiLevel`. The [separate contract](../patches/evolution/vintf-shipping-api.json)
binds the complete original and corrected wrapper to build/make commit
`a438ca40c6ed779042f806142b1165ba1360a7b2`. Kernel, SKU, APEX, Treble, property
parsing and compatibility-result handling remain byte-for-byte unchanged.

| Input | Behavior |
| --- | --- |
| Valid vendor value, ODM absent | Return the existing vendor argument unchanged. |
| Vendor absent, valid ODM value | Forward the original ODM value. |
| Both valid and equal | Return one property argument. |
| Both valid but different | Fail; do not infer runtime precedence. |
| Either present value invalid | Fail, including when the other value is valid. |
| Both absent | Fail instead of omitting the argument. |

Absence means `GetProp` returns `None`. An explicit empty string is invalid.
Accepted values are canonical positive ASCII decimal strings, at most 20
characters and at most `18446744073709551615`. Zero, leading zeros, signs,
whitespace, hexadecimal, Unicode digits, suffixes, non-string values and
overflow are rejected. The length is checked before integer conversion.

That maximum is the pinned `PropertyFetcher` interface's `UINT64_MAX`
representation bound. It is not a supported Android API range. The underlying
native parser accepts some additional forms and substitutes a default on
invalid input; the wrapper deliberately accepts a stricter canonical subset.
Nezha's actual value `36` comes from its separately pinned original bytes.

## Source and property evidence

`common.LoadInfoDict` normally creates both partition-property objects.
`PartitionBuildProps.GetProp` returns a stored value or `None`. Init's pinned
`PropertyLoadBootDefaults` loads ODM after vendor, so a property residing in ODM
is not missing merely because it has a vendor-owned property label. Conflicting
values still fail in this wrapper rather than choosing one by load order.

The original vendor property file is 15,320 bytes, SHA256
`2ea7fe521d0e7010bc3f068db034baf2056ae274023a964ff8a770ff726f4703`.
The original ODM file is 18,903 bytes, SHA256
`b4a5f8b818d0dbe8a3a400cba6890deaca5012737ff24baa903518027a94287b`;
its shipping API appears at line 285. The files are not edited. Board API
`202504`, runtime SDK properties, system properties and guessed device defaults
are not fallback sources.

The common reader has existing limits: direct duplicate property keys use the
last value, and its import handling permits only partition brand/name/device
overrides. This patch does not reconstruct duplicates lost during parsing or
change import behavior. The actual factory shipping API is a direct ODM entry;
no runtime selector is inferred.

The corrected wrapper SHA256 is
`8ada3c9809c7b6e5e07dd02a361a1dcb8a28b615bc37f62f46e156ac06159a93`
(12,713 bytes). The original is
`df247272684b97b77ae8d6d556c4a9e3df70e394d9738b907363bf5cb496424a`
(11,705 bytes). The verifier also requires the exact common reader after patch
0008, SHA256 `66c76097fafb6d4422e617b232babc1fc9f5da3d5e8f0d52d925c8841104792d`.

## Verification and adoption boundary

The [read-only verifier](../scripts/vintf_shipping_api.py) hashes full source
files and can replay the public patch in memory. With the original source
supplied, it verifies that every byte outside the named function is unchanged.
Its probe executes only that actual function and the actual common property
container classes, with no native checker, Android checkout imports or APEX
activation.

```sh
python3 -m unittest discover -s tests -p test_vintf_shipping_api.py -v
python3 scripts/vintf_shipping_api.py \
  --source-tree /path/to/prepared/source \
  --before-source-tree /path/to/original/source \
  --probe \
  --vendor-build-prop /private/original/vendor/build.prop \
  --odm-build-prop /private/original/odm/etc/build.prop
```

The focused offline suite passes **27 tests with zero skips**. The August 29
source-bound host probe passes **59 cases** and independently confirms that the
unchanged factory inputs produce exactly
`--property ro.product.first_api_level=36`. Its ignored evidence is
`reports/oem-policy-integration-20260829/vintf-shipping-api/source-probe-v1.json`.

This is argument-forwarding and input-validation evidence. The pinned main
libvintf source search does not establish a shipping-API consumer in a specific
compatibility check; the framework build already forwards the configured
shipping API. Do not describe this patch as proving that a previously skipped
native check now runs, or as a complete VINTF pass.

The current metadata and recovery/mi_ext compositions still pin the original
wrapper. Patch 0011 is an authored follow-up, not an active-source change or an
automatic composition extension. Native adoption requires a new explicit
transition and fresh dependent receipts, followed by complete framework,
vendor, kernel and APEX compatibility checks. Preserve all older contracts,
bundles and image inputs. No readiness flags or phone authorizations change.
