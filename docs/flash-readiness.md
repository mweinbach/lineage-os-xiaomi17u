# Experimental first-boot readiness

The requested milestone is a reviewed image set for an **authorized first
Evolution X boot**, not a release, a working OTA, or verified hardware support.
The platform stays Android 16 QPR2 `bka` / `bp4a`, with 4 KiB pages, normal
Android enforcing, and working76 recovery. No phone operation is authorized by
this preparation.

**Do not flash the current Package6 image set.** The complete APK audit found
two integration defects that need source fixes and rebuilt images. The earlier
VINTF and boot-content passes remain valid within their recorded scope; they
did not detect these APK issues.

## Current source state

The two-file transaction completed at **14:36:30 UTC**, with complete native
readback and independent verification. It changes the existing signer row and
adds the permission XML to the tracked source inventory: **549 files across 15
selected projects**, with all 1,179 pinned HEADs/origins matching. The other 547
existing source rows remain unchanged. Both original inodes and independent
copies are retained; Package6's existing input/artifact bytes are unchanged.

The source identity is `128c96ed5e626cdd0d21354231daed97f878057def27af1def13051befe26d4d`,
with `BUILD_NUMBER=nezha.128c96ed5e626cdd0d213542`. Only the source descriptor
changes; private/generated/tool/public-signing descriptor hashes remain the
same. Configuration queries and the new graph are verified. The ordinary signer/APK
build and independent artifact checks now pass as described below; image and
target-files results remain pending. Source installation is not rebuilt-image
or flash readiness. The full workspace suite passes **4,602 tests**, zero skips.

## Source fixes before the next image set

1. **FamilySpace lacks two product privileged-permission declarations.** Its
   unflagged requests for `GET_ACCOUNTS_PRIVILEGED` and `WRITE_SECURE_SETTINGS`
   are subject to the current enforce-mode startup check. The reviewed
   [source patch](familyspace-privapp-permissions.md) adds only those entries
   for `com.google.android.apps.pixel.familyspace`. The source is installed;
   its ordinary product copy and images still need rebuilding.
2. **TurboAdapter has unaligned stored DEX/resources.** Its signed
   `classes.dex` starts at byte 65 and `resources.arsc` at 314,249; both violate
   four-byte ZIP alignment. This is not a 16 KiB page-size requirement.
   Current SignApk clones access/creation timestamps, and Java later emits
   a 13-byte extra field outside the signer's alignment calculation. A real
   no-key JDK fixture reproduces that displacement and verifies the proposed
   [fresh-entry correction](signapk-stored-entry-timestamps.md). Its source is
   installed. Its ordinary signer/app rebuild now produces a strictly verified,
   aligned APK with the same platform certificate and protected payloads;
   final image delivery remains pending.

Neither issue justifies disabling permission enforcement, skipping alignment
checks, changing certificates, or editing generated target-files XML/APKs.

## Signer/APK rebuild and independent verification

The ordinary `signapk TurboAdapter` build finished at **15:26:21 UTC**, native
exit zero, with the required Ninja arguments, sandbox and limits observed.
All six source/input callback maps remain identical before and after. The
installed SignApk JAR is `da15c6c87386ac7c16fa019ecbaf2c5d3594f1aace11a5f4764562b88528cf40`
(3,321,606 bytes). The installed TurboAdapter APK is
`968f10081ddcb9fe1f9e6d0703a5d14f8d94eef19a9cb4184946f055279aae6a`
(324,086 bytes).

Independent native host checks pass strict signatures for API 36 and the full
supported range, `zipalign -c -P 4 -v 4`, and manifest parsing. The platform
certificate and all four non-signing payloads, sizes, CRCs and compression
methods remain unchanged. DEX/resources offsets move from 65/314,249 to
52/314,236, removing the incorrect timestamp-extra displacement.

The original component wrapper remains a recorded failure: its postcheck
incorrectly treated the original `stamp-cert-sha256` member as a payload that
must survive, although patch 0020 already removes this obsolete signing stamp.
The source APK's exact eight entries and the output's exact seven entries are
captured. Corrected structural/metadata replay now passes, including an
independent full replay by the coordinating agent. Its separate receipt binds
the exact original failure, complete corrected result and SDK verification;
the original completion flag stays false. No native compilation was rerun and
no source APK was changed to satisfy the check. The ordinary recovery/vendor/
ODM/mi_ext/policy-hash rebuild also passes, with all seven fresh producer
actions and three recomputed policy sidecars checked. Source/input callbacks
remain unchanged; working76 and retained proprietary image bytes are preserved.
This does not verify the final signed parent chain or runtime. Platform images
and the successor target-files package are still pending.

The shared app/graph capture now completes with no capture or guard errors.
Its first attempt stopped at an outdated 128 MiB per-log limit: the intact
Ninja dependency database is 171,935,084 bytes. The retry admits only that
exact measured file, retains the ordinary 128 MiB default and 256 MiB total
log cap, and verifies all graph-derived log paths. No database was removed,
truncated or reset.

The first GMS3 launcher attempt subsequently stopped during verification-helper
initialization, before the native phase directory or Android build was created.
A host-only recovery helper assumed a filesystem module path. Its authenticated
pure pairing API fixes that boundary without an Android source change or new
capture. The retry now passes the full native/profile checks and independent
semantic replay of all 91 retained evidence files. Two CrossDevice APK actions
are fresh; six APK outputs and four strict statuses use verified reuse evidence.
There are **zero fresh strict-status actions** in this phase. Sixteen native APK
signature/manifest commands pass, and all six source callback maps match. The
earlier component1 SignApk production stays separate from GMS3 tool reuse.
The original failed run remains unchanged. Platform images and the final
package still need building. The full offline suite passes again: 4,602 tests,
zero skips, in 201.844 seconds.

The native Package6 ZIP is also retained as an independent, fully rehashed
11,006,603,036-byte copy before Package7 can replace the ordinary output path.
The original archive remains in place at this checkpoint; no complete expanded
tree backup is claimed.

Selected-app preparation now has admitted **19 fresh query calls** against
16 graph files (6,862,614,527 bytes), while preserving the original singleton
query evidence separately. A failed first comparison treated containing-directory
timestamps as cross-build absence identity. The corrected comparison retains
path and directory identity checks and all current before/after stability checks;
only the two timestamps differed in the actual failure, and the file remained
absent throughout.

All five original file-reader families and 26 current app/status observations
also pass complete host replay, including source checks before and after.
No old physical observations were reused, and this collection did not modify
source or output files. The subsequent Selected5 attempt stopped in preflight:
its staging map omitted six existing capture-proof aliases. It did not prepare
or invalidate outputs and did not invoke Android. All six original proof files
are now staged with their recorded hashes; the failed attempt remains intact.
A separate Selected6 attempt uses the complete input map and a new phase
record. It preserves all 26 old outputs as copies and retained originals, then
completes all **35 ordinary Ninja actions** at **19:50:13 UTC** with exit zero.
Ninja arguments, limits and sandbox checks pass. The complete native profile and
postchecks now also pass, including 26 fresh required actions, eight fresh
strict statuses, ten live verification passes and five verified intervals.
All six before/after source callback maps match. Flex's prior read-only check
remains separate and is not counted as a fresh status.

All 193 retained evidence files (127,408,623 bytes) are exported with matching
hashes and stable native descriptors. Independent review accepts the original
process-success predicate and actual profile bindings. Full independent
semantic replay now passes over all 300 proof files (337,629,321 bytes),
including the 36 artifact commands, contexts, source guards, retention and
separate historical Flex evidence. Platform images and Package7 remain unbuilt.
The exact original request is retained after completion, explicitly recording
that the native invocation consumed stdin rather than that later file.

The full proof exceeds the old inline transport's file-count and compressed-
size limits. Package7 needs an explicit external-file transport while retaining
the original checks and complete bytes. This is separate from the successful
native app stage and independent semantic replay; neither requires a rebuild.

## Completed checks

The first-stage init refresh completed at **2026-09-04 14:09:10 UTC** through
the existing Android Ninja graph. It rebuilt 13 direct source objects, linked,
stripped and installed init: **all 16 outputs reproduce byte-for-byte**,
including the 2,701,184-byte installed binary with SHA-256
`40e909efe66f1e94b445bb6c71ade94be994470981606dcbede6c975bfbcff94`.
All 59 selected source/tool/reused-link inputs remain unchanged. Fresh compiler
depfiles record 1,405 dependency identities; this is not a rebuild of every
linked library. Originals remain retained. The first attempt stopped before
retention because the harness looked for Ninja's no-work message on stdout;
the corrected harness validates the two complete streams and keeps the failed
attempt intact.

The Package6 package audit checks target-files members and verified APEX
payloads, separately from the earlier image-content checks:

| Check | Result |
| --- | --- |
| APK signatures for exact API 36 | 455/455 pass, including 28 APKs inside APEXes |
| Full supported-API-range strict signing checks | 515/520 pass; five Google APK legacy JAR-warning failures are preserved |
| APEX payload AVB, key and manifest checks | 39/39 pass |
| Compressed APEX pair consistency | All 26 pairs match certificate, public key and verified inner root digest |
| APK ZIP/native-library alignment | 454/455 pass; TurboAdapter is the failure |
| Permission/required-library inventory | FamilySpace is the unconditional allowlist gap; no unresolved required library declaration names |
| Shell's flagged permission | Absent from all packaged default flag stores; parser skips its definition. Existing device overrides are outside this check. |
| Input preservation | Full published ZIP and all 520 copied APK/container inputs rehash unchanged |

A subsequent image inventory found **three compressed full APK payloads**
behind Chrome, WebView and Trichrome stubs. Their bounded expansions and all
three stubs pass strict signature and alignment checks. Package names, versions
and signing identities match; Chrome/WebView's Trichrome version 699,813,532
and required certificate match the expanded library. The earlier incomplete
host-readback attempt is preserved separately from the completed retry. These
are additional Package6 artifact checks, not proof of on-device expansion or
successor-image delivery. Effective manifest analysis substitutes the expanded
APK for its stub instead of counting two installed packages.

The original [three VINTF commands and boot-image checks](package6-static-validation.md)
also pass, retaining their two definition skips and two framework-only warnings.
These do not prove service registration or hardware behavior.

## Vendor and ODM application coverage

Fresh EROFS scans and captures separately cover all **19 APKs in the current
vendor/ODM images**: ten apps and nine overlays. All pass actual manifest,
four-byte ZIP / 4 KiB native-library alignment, and strict signature checks for
API 36 and their full supported range. The Adreno APK needs a separately pinned
BouncyCastle provider for the SDK verifier's RSA-PSS operation; the original
host-provider failure is preserved. Eighteen APKs retain Xiaomi signatures and
one retains Qualcomm's. No platform/phone shared-UID certificate conflict was
found. These checks supplement the 455 APKs found in target-files and APEXes.

Eight requested `signature|privileged` grants remain unavailable to CneApp,
TxPwrAdmin and the Goodix factory test app under the new platform signer. They
are nonprivileged `app` packages, so this is separate from FamilySpace's fatal
privileged-allowlist gap. Cne's restricted-network requests and Tx's startup
precise-telephony registration catch the relevant exceptions. Later keepalive
and permission-observer operations may still fail without a local handler.
The reviewed DEX establishes no unconditional whole-Android startup failure;
it does not prove radio or power behavior works. Preserve OEM signers and
validate these functions on device before making a targeted integration change.
Factory test applications receive no extra permissions.

## Delivery and device gates

The current Super layout is **A-only**: all eight A logical partitions are
populated and all B entries are empty. Super is shared, so writing it removes
the existing logical rollback slot. Keeping B boot images does not preserve a
bootable stock B system. Two complete copies of the current logical images
would exceed physical Super by 3,341,697,024 bytes, before extra overhead.

The [offline bundle tool](experimental-flash-bundle.md) can assemble exact
verified bytes into a fresh private directory, but no final bundle has been
assembled while the source fixes are pending. The candidate route has Super
plus seven physical images. `countrycode` and `pvmfw` are verification
references, not automatic writes; their selected-slot authenticated contents
must match the signed root descriptors.

Before any device action, require a freshly identified and explicitly
authorized device, matching variant/firmware, capacities, slot state, idle
snapshot/merge state, unlocked-bootloader policy, rollback acceptance, reliable
USB/power, an off-device data backup, and a concrete stock-return/recovery plan.
Stock userdata/encryption migration is not verified. Wiping userdata or metadata
requires a separate explicit decision and authorization; neither is automatic.
Never relock on the development key.

A [bounded read-only preflight helper](device-flash-preflight.md) is prepared
for separately authorized collection. Its default is plan-only. It preserves
unknown device observations, rejects fastbootd as independent bootloader
evidence, and cannot authorize installation or modify the phone. It has not
been run against a device.

The original **China OS3.0.309.0.WPACNXM (Android 16)** package provides an
off-device Android return set: original Super and seven boot/AVB companions,
with countrycode/pvmfw references and the original TGZ retained. Fresh hashes
cover 25,662,099,569 bytes including the separate working76 rescue image; fresh
sparse parsing finds no DONT_CARE inside the eight populated logical extents or
LP metadata. The retired reconstructed raw Super is not a missing input: its
original sparse image remains present.

An unchanged factory AVB chain requires its **original recovery**, whose key
differs from working76. Keep TWRP separately as the tested rescue artifact.
This material supports returning to that original China package; it does not
establish restoration of the prior xiaomi.eu installation, personal-data backup,
current firmware/variant compatibility, or authorization to write any phone.
Exact private paths and the reviewed plan are indexed in the research record.

OTA is a separate milestone. This target-files ZIP is not a sideload or
fastboot-update installer; OTA key references are blank and two retained vendor
APEXes lack re-signing metadata rows. These do not invalidate their verified
built-in signatures, but do prevent an OTA-readiness claim.

The current candidate includes Aperture. The factory Xiaomi Camera/Leica APK is
not selected, and native camera feature support remains intended, not tested.
Two duplicate overlay package names are also recorded for later feature
validation. Neither a generic camera package nor preserved vendor hardware
inputs proves camera, radio, encryption, thermals, or other hardware works.

The compact evidence index is [flash-readiness.json](../research/flash-readiness.json).
Complete-ROM and flash-admission flags remain false until their actual gates
are satisfied.
