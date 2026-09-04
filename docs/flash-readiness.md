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
ODM/mi_ext/policy-hash rebuild has started; final image/package qualification
remains pending.

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
