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

## Source fixes before the next image set

1. **FamilySpace lacks two product privileged-permission declarations.** Its
   unflagged requests for `GET_ACCOUNTS_PRIVILEGED` and `WRITE_SECURE_SETTINGS`
   are subject to the current enforce-mode startup check. The reviewed
   [source patch](familyspace-privapp-permissions.md) adds only those entries
   for `com.google.android.apps.pixel.familyspace`. It is not installed yet.
2. **TurboAdapter has unaligned stored DEX/resources.** Its signed
   `classes.dex` starts at byte 65 and `resources.arsc` at 314,249; both violate
   four-byte ZIP alignment. This is not a 16 KiB page-size requirement.
   Current SignApk clones access/creation timestamps, and Java later emits
   a 13-byte extra field outside the signer's alignment calculation. A real
   no-key JDK fixture reproduces that displacement and verifies the proposed
   fresh-entry correction. The ordinary signer/app pipeline must be rebuilt,
   retaining the same platform certificate and original APK payload contents.

Neither issue justifies disabling permission enforcement, skipping alignment
checks, changing certificates, or editing generated target-files XML/APKs.

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
