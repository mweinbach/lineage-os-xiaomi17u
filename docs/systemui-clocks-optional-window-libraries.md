# SystemUI Clock optional Window libraries

At this September 1, 2026 preparation checkpoint,
[patch 0022](../patches/evolution/0022-systemui-clocks-optional-window-libraries.patch)
corrects seven Clock imports without changing Flex. The
[contract](../patches/evolution/systemui-clocks-optional-window-libraries.json)
pins the complete source transition and all eight original Clock APK identities.
Host verification passes; source adoption, regenerated Android rules and actual
module builds remain separate work. Complete-ROM readiness remains false.

The completed read-only audit checked BCR and eight Clock APKs. BCR and Flex
passed; **seven Clocks failed** strict uses-library checks: BigNum, Calligraphy,
Growth, Inflate, Metro, NumOverlap and Weather. All nine native badging commands
passed and all original APK hashes, modes and stat identities remained stable.
The audit still exits 1. Its successful input guards do not change that result,
and removing the status-output argument for read-only probes does not establish
ordinary status-file production.

Each failing Clock manifest declares optional `androidx.window.extensions`
followed by `androidx.window.sidecar`; its build declaration supplies neither.
Required-library lists are empty. Flex has no uses-library tags and already
matches its empty build lists. Adding the pair to Flex would introduce a new
mismatch.

The pinned `vendor/extras` source at
`c401d732c0475b7010c205a2e9bfb0fd6888d0be` has eight separate imports in
`themes/SystemUIClocks/Android.bp`, with no shared defaults. Patch 0022 adds an
explicit ordered `optional_uses_libs` array to each of the seven failing imports.
It leaves Flex's entire block unchanged and preserves every original source
byte, including platform signing, APK paths, owner, privileges, system_ext
placement and the pre-existing `dex_preopt.enabled: false` settings. Those
settings are not a new workaround; strict uses-library checking remains enabled.

The source keeps mode `100755`, tabs and CRLF endings. It grows from 2,046 bytes
and 95 lines to 2,690 bytes and 123 lines, with only seven four-line arrays added.
The complete body comes from the earlier 543-file intake's verified flat decode;
the later audit reauthenticates the same Clock source under the current
544-file/fifteen-project guard context. That inventory does not yet contain the
Clock Blueprint. The separate adoption must derive its new inventory and build
identity from the actual union and preserve the existing BCR integration.

Ten offline standard-library tests verify the source pair, selective changes,
all eight APK bindings and strict scope. Full captured-source replay produces
the exact postimage and restores the original bytes, with no fuzz or offsets;
twelve malformed, drift or duplicate cases are rejected. The unchanged pinned
checker also ran thirteen host CLI cases on synthetic XML derived from actual
badging: seven corrected Clocks and unchanged Flex pass; five negative cases
fail, including an incorrect Window declaration on Flex. Positive status files
are empty, negative files are absent, and no cases are skipped. These fixtures
do not open APKs or execute Soong. Their retained receipt is
`reports/bcr-uses-library-20260901/clock-patch-preparation-v1/host-verification.json`.

After guarded adoption, inspect all eight regenerated checker rules and collect
fresh successful ordinary status-action evidence for the seven corrected
imports, alongside strict selected-prebuilt, module and signature evidence.
An approved targeted build or packaging itself may supply the ordinary producer
evidence; no separate nine-module build is prescribed here. Preserve existing
dexpreopt choices and inspect the dependency inputs that the real graph
produces. Target-files packaging, VINTF, AVB, rollback, partition fit and device
boot still need their own evidence. Normal Android SELinux enforcement, the
4 KiB baseline and working76 recovery remain unchanged; phone mutations require
fresh user authorization.
