# FamilySpace product privileged permissions

The Package6 signing and permission audit found two missing product allowlist
entries for `com.google.android.apps.pixel.familyspace`:

- `android.permission.GET_ACCOUNTS_PRIVILEGED`
- `android.permission.WRITE_SECURE_SETTINGS`

The selected `FamilySpacePrebuilt-v484` APK requests both permissions without
SDK caps or feature flags. Its module is product-privileged and `PRESIGNED`.
Its actual package has no shared UID or install constraints. The active pinned
Kotlin permission implementation checks the privileged allowlist before
signature eligibility and throws accumulated enforce-mode violations at
`systemReady`. This is a source-backed boot-failure candidate, not an observed
device failure.

[Patch 0024](../patches/evolution/0024-familyspace-product-privapp-permissions.patch)
adds one block to
`vendor/gms/product/blobs/etc/permissions/privapp-permissions-google-p.xml`.
It preserves all 74 existing package blocks and every original byte. The
distinct `com.google.android.gms.supervision` package is unchanged. The patch
does not alter the APK, signature, module selection, partition placement,
permission enforcement, SELinux, 4 KiB baseline, or working76 recovery.

| Input | Identity |
| --- | --- |
| Pinned `vendor/gms` revision | `89c3940a77298c204c55a21efded92ddafb59fe9` on `bka` |
| Original XML | SHA256 `1a923edbfaa765eccb40ee7a11cec65e627349cfe8f33a7a1ff433e089a6a7f5`, 65,108 bytes |
| Patched XML | SHA256 `79ec429edf7269c1bf5a084cffabba08860ed981134ba75c8f00bd3cc196db71`, 65,356 bytes |
| XML mode and endings | `100644`, LF |
| Exact change | One package block, two permissions, 248 inserted bytes |

The [source contract](../patches/evolution/familyspace-product-privapp-permissions.json)
records complete Git blob IDs, source capture, actual APK and native manifest
and signature evidence. Full XML and APK bodies remain in ignored locations.
The [pure helper](../scripts/familyspace_privapp_permissions.py) rejects any
unreviewed preimage or postimage; its reverse operation recovers the exact
original. The public patch contains only the small insertion hunk.

The 14 [offline tests](../tests/test_familyspace_privapp_permissions.py) use a
synthetic XML fixture and tracked contracts, without proprietary inputs or a
phone. They cover the exact permission scope, preservation of the distinct
supervision package, malformed XML, duplicates, and unpinned source rejection.
Separate full-source replay against the authenticated captured XML confirms
both forward patch application and byte-exact reversal. Neither proves an
Android component build or device boot.

This is a **prepared source patch, not installed or rebuilt-image evidence**.
Source adoption must record a successor build identity, rebuild the ordinary
product permission copy and affected images, and rerun the effective permission
audit and artifact checks. Editing generated XML or target-files is insufficient.
Normal enforcement remains required; this patch does not promote complete-ROM
or flash readiness.

## Native source adoption — September 4, 2026

The combined two-file source transaction completed at **14:36:30 UTC** and
passed full readback and independent review. Both original source inodes and
independent originals remain retained. Current source is the 549-file
`nezha.128c96ed5e626cdd0d213542` state; previous source-preparation records keep
their historical scope. This does not yet establish a rebuilt signer, APK or
image. Follow [current flash-readiness work](flash-readiness.md#current-source-state).
