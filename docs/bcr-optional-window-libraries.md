# BCR optional Window libraries

At this September 1, 2026 preparation checkpoint, patch
[0021](../patches/evolution/0021-bcr-optional-window-libraries.patch) corrects
BCR's optional-library declaration. It has passed host checks but has not been
adopted into the active Android source or verified by an ordinary Android build.
The [contract](../patches/evolution/bcr-optional-window-libraries.json) binds the
source transition, original failure and host evidence. Complete-ROM readiness
remains false.

The second target-files attempt stopped at BCR's
`enforce_uses_libraries.status` producer, with native exit 1. Its complete log
records no required libraries and two optional libraries in the APK manifest,
in this order: `androidx.window.extensions`, then `androidx.window.sidecar`.
The generated command supplied empty required, optional and missing-library
lists. It also had no `--dexpreopt-config` operands. This is a source declaration
mismatch; the failed result is preserved rather than reclassified as success.

The declaration is the nested
`vendor/extras/bcr/prebuilts/product/priv-app/com.chiller3.bcr/Android.mk`,
at the pinned `vendor/extras` revision
`c401d732c0475b7010c205a2e9bfb0fd6888d0be` on `bka`. Neither
`bcr/Android.mk` nor `bcr/Android.bp` exists at this checkpoint. The early native
capture includes all five tracked BCR Makefiles, with stable project HEAD,
index and clean status; their complete bodies match their Git blobs.

Patch 0021 adds this one assignment immediately before `BUILD_PREBUILT`:

```make
LOCAL_OPTIONAL_USES_LIBRARIES := androidx.window.extensions androidx.window.sidecar
```

The original file has 11 CRLF lines and 310 bytes. The corrected file has 12
CRLF lines and 395 bytes. All original bytes and mode `100644` are preserved,
including the `PRESIGNED` certificate, `APPS` class, source APK, privileged flag
and product placement. The unified diff uses LF headers and CRLF source lines;
replay must use bytes without newline normalization. It changes no APK,
required-library declaration, provider registration, signing tool or enforcement
setting. The pre-existing `RELAX_USES_LIBRARY_CHECK` assignment in `bcr/bcr.mk`
is untouched and does not establish the selected product's effective setting:
the actual failing command was strict.

Verification is deliberately separated:

- Eleven offline standard-library tests recover the complete source pair from
  the public patch, verify the pinned manifest and original settings, and reject
  duplicate application, drift, malformed hunks, path/mode changes and newline
  normalization. They need no ignored inputs, source checkout, process or phone.
- Full captured-source replay reproduces the exact 395-byte postimage and
  reverses to the original 310 bytes with no fuzz or offsets. Twelve negative
  cases are rejected. The captured inputs and historical 0018–0020 patch,
  contract and document triplets remain unchanged. The receipt is
  `reports/bcr-uses-library-20260901/patch-preparation-v1/replay-receipt.json`.
- The unchanged pinned `manifest_check.py` and helper pass one corrected case
  and reject four strict negative cases: the old empty lists, reversed order,
  missing sidecar and optional libraries incorrectly declared required. The
  positive status file is empty; negative checks return 255 and create no status
  file. All five cases ran, with no skips. These are host CLI checks on synthetic
  XML generated from the retained native diagnostic, not actual APK or Android
  graph execution. The receipt is
  `reports/bcr-uses-library-20260901/patch-preparation-v1/strict-checker-fixtures-v1/receipt.json`.

The early source capture does not replace the full combined intake required
before adoption. At this authoring checkpoint, the original APK's raw SHA256
and fresh badging are pending; the observed Git index blob is not a substitute
for its raw identity. That intake must reauthenticate the original APK, selected
declarations, actual tools and all existing source/input/output guards. The
separate source transaction must preserve the original APK and other reviewed
patches and derive its source inventory and build identity from the actual
union.

After adoption, regenerate the ordinary `bka`/`bp4a` user graph, inspect BCR's
exact ordered optional flags with no relaxation, and require a fresh successful
ordinary status action. Check the real module, dexpreopt dependency inputs and
class-loader contexts before retrying target-files packaging. Host checks do
not establish signing, package completion, boot or hardware behavior. Preserve
normal Android SELinux enforcement, the 4 KiB baseline and working76 recovery;
phone mutations still require fresh user authorization.
