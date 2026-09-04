# SignApk STORED-entry timestamp correction

Package6's platform-signed TurboAdapter has an unaligned `resources.arsc`:
its data offset is 314,249, which is one byte past a four-byte boundary. The
first `classes.dex` entry begins at 65 instead of the signer's calculated 52.
The APK targets SDK 31, so this resource-table alignment is relevant to Android's
package parsing checks. This finding does not establish an observed device
parse failure or an unconditional system-server boot failure.

The pinned signer clones each STORED `JarEntry`. Java retains parsed access and
creation `FileTime` fields in that clone even after `setTime(timestamp)` and
`setExtra(null)`. When writing the entry, the JDK adds a 13-byte extended timestamp
field that the signer's alignment calculation did not count. The actual source
APK carries those times in an NTFS extra field; the normal `zip2zip` producer
converts `classes.dex` to STORED before signing.

[Patch 0025](../patches/evolution/0025-signapk-stored-entry-timestamps.patch)
starts a fresh STORED entry and explicitly preserves its name, compression
method, size, compressed size and CRC. It keeps the existing normalized
timestamp, comment/extra-field removal, alignment calculation, signing callbacks,
compressed-entry path, certificate choices and [0020 source-stamp correction](signapk-source-stamp.md).
No proprietary APK is edited.

A fresh entry also normalizes hidden central-directory creator OS and external
Unix attributes to zero, matching the existing compressed-entry path. Public
`JarEntry` APIs have no setters for those fields. The patch uses no reflection.
This behavior is recorded explicitly: the change is not whole-archive byte
equivalence, and its fixture does not qualify arbitrary ZIP consumers that use
Unix mode bits.

| Source | Identity |
| --- | --- |
| Base `build/make` | `Evolution-X/build`, commit `a438ca40c6ed779042f806142b1165ba1360a7b2`, `bka` |
| Before, including 0020 | SHA256 `a1ef3eaac711108c867c1834c475a84a4425d0fb29d07364b3fd20ed71f260f9`, 61,172 bytes |
| After 0025 | SHA256 `e36126abbaa95f6762fb652139100a27032f2fe5ee4621f2be7debf4c9639111`, 61,517 bytes |
| File | `tools/signapk/src/com/android/signapk/SignApk.java`, `100644`, LF |

The [contract](../patches/evolution/signapk-stored-entry-timestamps.json)
records full Git blob IDs, captured source and actual APK evidence. The
[pure byte helper](../scripts/signapk_stored_entry_timestamps.py) requires the
exact 0020 postimage and supports exact reversal. Thirteen
[offline tests](../tests/test_signapk_stored_entry_timestamps.py) cover the
partial patch, source chain, metadata scope, duplicate/drift rejection and
unchanged surrounding source without Java, proprietary inputs, keys or a phone.

The separate [no-key Java fixture](../tests/fixtures/SignApkStoredEntryTimestampRepro.java)
ran ten cases against the host JDK: absent times, access only, creation only,
both times, and NTFS metadata, each at four-byte and 4 KiB alignment. All 20
output ZIPs passed payload/size/CRC and normalized metadata checks. All corrected
outputs align; eight timestamp-bearing clone controls reproduce misalignment.
The original overly strict whole-ZIP comparison failure is preserved separately;
the corrected fixture explicitly checks central-attribute normalization while
retaining payload, local-byte and flag comparisons.

This remains **source preparation**, not an Android signer build, actual APK
signing result, or rebuilt-image qualification. Adoption must rebuild the native
SignApk and ordinary TurboAdapter producer, verify every non-signing member
payload without blanket `META-INF` exclusions, check the expected platform
certificate and strict signatures, and pass `zipalign` with `-P 4`. Successor
images and target-files need their own checks. Flash readiness remains false.

## Native source adoption — September 4, 2026

The combined two-file source transaction completed at **14:36:30 UTC** and
passed full readback and independent review. Both original source inodes and
independent originals remain retained. Current source is the 549-file
`nezha.128c96ed5e626cdd0d213542` state; previous source-preparation records keep
their historical scope. This does not yet establish a rebuilt signer, APK or
image. Follow [current flash-readiness work](flash-readiness.md#current-source-state).

## Actual ordinary build and APK verification — September 4, 2026

The source549 ordinary `signapk TurboAdapter` command exits zero with observed
Ninja, sandbox and resource checks. The rebuilt APK independently passes both
strict signature modes, manifest parsing and four-byte/4 KiB alignment; all
four protected payloads and the platform certificate are unchanged. See the
[current artifact result](flash-readiness.md#signerapk-rebuild-and-independent-verification)
for hashes and the separately preserved wrapper failure caused by its original
stamp-inventory assumption. Corrected postcheck replay now passes without
rewriting the original failure or rerunning compilation. Final image delivery
remains a separate gate. This does not qualify a boot or authorize flashing.
