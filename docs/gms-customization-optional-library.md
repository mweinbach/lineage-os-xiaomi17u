# GMS customization optional library

The first ordinary `target-files-package` attempt fails the strict uses-library
check for `CustomizationBundlePrebuiltFullVersion`. The original APK declares
optional `wear-sdk`; the module's Make stanza declares neither required nor
optional libraries. The original native failure log is retained and bound in
the [patch record](../patches/evolution/gms-customization-optional-library.json).
This is a source preparation checkpoint, not a successful package or ROM.

The [one-line patch](../patches/evolution/0018-gms-customization-optional-wear-sdk.patch)
adds `LOCAL_OPTIONAL_USES_LIBRARIES := wear-sdk` immediately before
`include $(BUILD_PREBUILT)` in that module. It retains every original source
byte, the original APK, `PRESIGNED`, product placement and privileged status.
It changes no required-library, dexpreopt or enforcement setting. No provider,
JAR, library registration, global exception or APK rewrite is introduced.

The source is pinned to `vendor/gms` revision
`89c3940a77298c204c55a21efded92ddafb59fe9`, on the reviewed `bka` source
snapshot. The named remote is `evo` at
`https://github.com/Evolution-X/vendor_gms`. The source lock is unchanged;
this local patch must be admitted separately.

| Bound input | Bytes | SHA-256 |
| --- | ---: | --- |
| Original `Android.mk`, mode `0644` | 983 | `a8e2f012e4e44cbb3b555a1d67827d59d192c049839cfe799dc863cdadd6fa5c` |
| Patched `Android.mk`, mode `0644` | 1,025 | `915d1fdc2ed7cd843edff8399216584d3306b67d763243758829041c9dd34b45` |
| Original APK, mode `0644` | 12,967,838 | `3c91e4cc1fa60228ad5e1747aebd63f71e196b99529c56976ebe0a8904f7f8fc` |

The coordinator's native `aapt2 dump badging` succeeds against that exact APK
and reports only `uses-library-not-required:'wear-sdk'`. The APK is package
`com.google.android.apps.pixel.customizationbundle`, version code
`10003735`, version `1.0.813706241.release`. This readback is not a new APK
signature validation. No proprietary APK is included in the workspace patch.

The earlier source capture records clean GMS status. The later read-only
metadata capture verifies the HEAD and named remote, but its separate status
query fails with exit 128 because Git LFS attempts a temporary clean-filter
write on read-only source. That failure is retained; it is not another
clean-status result.

The pinned Make rule at `build/make`
`a438ca40c6ed779042f806142b1165ba1360a7b2` passes the full declared optional
list to the strict checker, excluding bootclasspath libraries. Separately, it
filters optional dexpreopt dependencies by `PRODUCT_PACKAGES`. The actual
captured package list contains the consumer and no exact `wear-sdk` entry.
Declaring the optional name therefore does not require adding a speculative
provider. The early Make filter can miss indirectly installed libraries, so
the final module context, installed packages and library registrations still
need native review before claiming complete provider absence. Make's rule
does not use Soong's missing-optional marker.

Two isolated host copies apply the exact patch, reject duplicate application
and reverse to the original bytes and mode. A separate admission check rejects
preimage, mode, project revision and patch drift before replay. The unchanged
pinned manifest checker passes 22 upstream unit tests plus nine synthetic XML
and nine synthetic badging scenarios. Two additional minimal Make-style cases
show the exact optional declaration passing with an empty status file and its
omission failing with exit 255. These are host semantic fixtures, not the
proprietary APK's generated build action. Fourteen existing workspace tests
also pass with zero failures, errors or skips; they cover the earlier DEX
provider path and the retained global enforcement guards.

Native admission remains separate. Recheck the exact source and original APK,
admit the single changed Makefile through the reviewed source projection, and
recompute source and build identities. Regenerate the ordinary `bka` /
`bp4a` user graph; verify that the real status rule has exactly one
`--optional-uses-library wear-sdk`, retains enforcement and has no relaxation.
Require a freshly executed successful status action and an empty status file,
then inspect the actual module's dexpreopt context and dependencies. A
hand-edited checker invocation does not establish native integration.

The previous 537-file/thirteen-project source and `8643` build identity remain
the prior checkpoint until a separate adoption record supersedes them.
Normal Android enforcement, the 4 KiB baseline, working76 recovery, strict
APK checks, VINTF, AVB and rollback constraints are unchanged. Target-files
completion, signed-image admission, customization behavior, ROM boot and OTA
validation remain unverified by this preparation.
