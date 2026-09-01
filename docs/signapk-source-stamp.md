# SignApk source-stamp construction correction

The first ordinary four-module GMS build exits successfully, but its component
postcheck fails on the installed `CrossDeviceAccessServicePrimary` APK.
`apksigner verify --verbose --print-certs -Werr` verifies one platform signer
and the v3 signature, then exits 1 with `WARNING: No SourceStamp signature`.
The overall result remains failed. This is a source-construction defect, not
an approved warning exception.

Read-only ZIP inspection explains the warning. The unchanged original APK
contains a 32-byte `stamp-cert-sha256` entry and a source-stamp v2 block
(`0x6dff800d`). The built and installed APKs retain the same digest entry but
lack that block. Pinned SignApk already disables preservation of other signers
and passes `null` for the input APK signing block. Its normal APK-copy call
nevertheless copies the obsolete digest entry.

The [0020 patch](../patches/evolution/0020-signapk-remove-stale-source-stamp.patch)
changes two files in `build/make` at
`a438ca40c6ed779042f806142b1165ba1360a7b2` on the selected `bka` base:

| Source | Correction |
| --- | --- |
| `tools/signapk/src/com/android/signapk/SignApk.java` | Pass an exact, quoted `ApkUtils.SOURCE_STAMP_CERTIFICATE_HASH_ZIP_ENTRY_NAME` pattern to the normal APK-copy call. |
| `core/app_prebuilt_internal.mk` | Add `$(SIGNAPK_JAR)` as a normal prerequisite of ordinary non-PRESIGNED prebuilt APKs, before the existing common recipe. |

`copyFiles` already tests that pattern with whole-name `Matcher.matches`
before either entry-copy path. The exact constant resolves to
`stamp-cert-sha256` in the pinned apksig source. No filename prefix, wildcard
or unrelated ZIP entry is selected. This applies to APK re-signing through
SignApk generally, not just this GMS module.

The dependency correction matters because the existing rule lists SignApk
only as an order-only prerequisite. A rebuilt signing tool must cause the
ordinary signed APK to be rebuilt through its normal producer. The new rule
is conditional on `LOCAL_CERTIFICATE` being different from `PRESIGNED`; the
existing common recipe, ordinary PRESIGNED recipe and split-APK recipe remain
unchanged. Actual regenerated Ninja dependencies and fresh producer execution
still require native verification. Deleting outputs, touching dependencies
or forcing actions is not a substitute.

The patch leaves whole-file OTA signing and its `STRIP_PATTERN`, signing
algorithms, keys, certificate selection and verification flags unchanged.
Original proprietary APKs are preserved. Normal verification already has
`--verify-source-stamp false` as its default; switching that option to true
would select stamp-only verification and would not fix this construction
problem. `-Werr` and all strict uses-library checks remain required.

The [source contract](../patches/evolution/signapk-source-stamp.json) records
both complete preimages and postimages, their modes and Git object IDs, the
patch hash, the pinned Make/apksig sources and the original failed evidence.
Two in-memory forward/reverse replays per complete captured file reproduce
the exact postimages and restore the originals. Sixteen negative cases reject
source drift, mode or revision drift, changed patches, duplicate application
and invalid reverse inputs, with no offsets or fuzz. Twelve offline workspace
tests check the partial public hunks, their file scope and the source contract.
Their surrounding text is inert; they do not compile Java or verify APKs.
The earlier one-file draft is retained only in ignored preparation evidence.

This record is **host preparation, not source adoption or a corrected native
build**. Adoption must preserve unrelated reviewed changes, install both
source files together and recalculate the source inventory and build identity.
Then build SignApk, verify the regenerated dependency, and require fresh
ordinary APK production with the obsolete entry absent. Repeat the complete
four-module postcheck using the original strict verifier and expected signer
identities before proceeding to current image and package validation.

Normal Android remains enforcing, with the selected 4 KiB baseline and
working76 recovery unchanged. This patch establishes no target-files package,
signed image chain, ROM boot, OTA or hardware result. ROM readiness remains
false, and no phone operation is authorized by this preparation.
