# Optional partition properties in target-files

The pinned Evolution `bka` `build/make` commit
`a438ca40c6ed779042f806142b1165ba1360a7b2` has a property-reader defect that
affects opaque prebuilt partition packaging. `LoadInfoDict` iterates every
property-capable partition, including optional partitions, but
`_ReadPartitionPropFile` indexes a map containing only existing directories.
An absent directory raises `KeyError` before the function can return its
documented empty result. The directory mapper also cannot handle ZIP paths or
open `ZipFile` objects, although the surrounding reader accepts both.

[Patch 0008](../patches/evolution/0008-optional-partition-build-props.patch) adds
the missing optional-directory check and supports all three input forms. Its
[separate contract](../patches/evolution/optional-partition-build-props.json)
binds the original and resulting complete `common.py`, the patch, and its
limited verification scope:

| Input | SHA256 | Bytes |
| --- | --- | ---: |
| Original `common.py` | `78b74437cb9916eda2b25ac4c8afd13b50847648f10c2e4fd66df0e02ab90bc2` | 156263 |
| Corrected `common.py` | `66c76097fafb6d4422e617b232babc1fc9f5da3d5e8f0d52d925c8841104792d` | 157203 |

The patch retains the ordered canonical and nested partition paths and the
priority of `etc/build.prop` over root-level `build.prop`. An existing preferred
partition directory without properties does not fall through to a different
partition directory. An empty preferred property file stays empty. ZIP lookup
recognizes implicit directories and explicit empty directory entries, requires
a trailing-slash boundary, and does not close a caller-owned ZIP. Property
parsing, imports, signing, AVB and image construction remain unchanged.

Missing optional properties remain missing and produce a warning. This must
not become an excuse to omit required vendor/ODM metadata. Nezha's actual
factory vendor image contains `vendor/odm_dlkm/etc/build.prop`, despite having
no separate `odm_dlkm` logical partition. Preserve that real nested path; do not
invent a top-level `ODM_DLKM` tree or a property value.

## Verification

The offline test module has **19 passing tests**. It executes the changed
function bodies from the public patch against real synthetic directories and
ZIPs, demonstrates the original missing-directory and ZIP failures, exercises
canonical/nested lookup and property precedence, and checks contract/source
failure handling. These tests require no checkout, device or proprietary files.

The [source-bound verifier](../scripts/partition_build_props.py) separately reads
the complete hash-bound corrected file. With the original source supplied, it
also replays both patch hunks exactly in memory. Its **24 Python probe cases**
execute only the actual property reader, mapper and original byte-reading
helpers. They use disposable synthetic inputs and do not import the Android
checkout or invoke external tools.

```sh
python3 -m unittest discover -s tests -p test_partition_build_props.py -v
python3 scripts/partition_build_props.py \
  --source-tree /path/to/prepared/patched/source \
  --before-source-tree /path/to/verified/original/source \
  --probe
```

The August 29 host run reproduced the exact corrected bytes and passed all 24
cases. The ignored result is
`reports/oem-policy-integration-20260829/partition-build-props/source-probe-v1.json`.
This is a Python behavior result, not a native target-files build, VINTF pass,
complete AVB verification, OTA validation or device test.

## Separate integration prerequisites

The existing recovery and `mi_ext` contracts still require the **original**
`common.py`. Patch 0008 is a separate authored follow-up; it has not been added
to those contracts or installed into the active source by this change. A new
explicit reviewed source composition is required before native adoption.
Historical patch contracts must remain unchanged.

Opaque vendor/ODM packaging also needs an image-bound metadata projection
through a native input and target dependency path. The current core copies
prebuilt images into `IMAGES/` but does not populate their `VENDOR/` and `ODM/`
metadata trees. Properties, VINTF XML, complete original APEX packages and their
real directories must match the selected images. This patch supplies none of
those inputs. Complete APK/context inventories are additional requirements for
Treble labeling and signing checks, not implied by a property-reader result.

Local artifact construction can be admitted once its input closure and strict
recipes are reviewed; completed-artifact validation comes afterward. Keep
construction permission distinct from verified target-files, installable OTA,
hardware-tested and flash admission. No existing readiness flags change here.
