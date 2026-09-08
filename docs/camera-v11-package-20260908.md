# Camera v11 package, 2026-09-08

**The corrected v11r1 package, `nezha.130611bac9232625e0066968`, passes its
full build, signed archive checks and eight-image bundle verification.** It is
not installed. [V10 remains the measured phone baseline](camera-v10-install-validation-20260908.md);
new flash/reboot approval and a fresh device preflight are required.

The [factory stream-sizing change](camera-stream-sizing-20260908.md) restores
three measured factory decisions: preserve requested mock-camera dimensions,
select and adjust custom sizes, and permit mock-camera JPEG allocation beyond
the public table maximum. V10's telephoto JPEG/R outputs exceed the allocated
buffer, and Pro RAW fails public-table rounding before HAL configuration.
This candidate addresses those measured sizing paths. It does not establish
that the separate Ultra RAW provider crash or video audio initialization is fixed.

## Build and package verification

The source inventory contains 661 verified rows. The native component build
completed 152 actions, the full target-files build completed 35 actions, and
the corrected packaging build completed three actions, all with exit code zero.
These are incremental builds using the preserved source/output/cache. The
before/after source inventories match, and the pinned manifest and sole writer
VM remain selected.

The delivered `cameraserver` is 4,026,968 bytes, SHA256
`5dd3bc8a8105877dbff507afaf9d2a420cce53a1f3a9397f2b869aadd603c938`.
It statically links the modified camera service, retains `__cfi_check`, and
contains all three factory lookup names. Its bytes match the inspected native
component in both unsigned and signed archives. The framework JAR, framework
resources and Aperture APK retain the verified v10 component bytes.

An explicit component build also installed an unselected shared
`libcameraservice.so` variant. The corrected package excludes that variant;
both the archive member list and actual filesystem images verify its absence.
The initial unsigned attempt and correction receipt remain preserved. Future
component builds should request `cameraserver` alone when validating this
statically linked delivery path.

The unsigned target-files ZIP is 11,322,896,122 bytes, SHA256
`b1d6bb078ec797ffbc6e73af3050ee6094ddf026705eefd272c1928591c84675`.
The transferred sparse Super image is 9,476,728,944 bytes, SHA256
`3a6ca060a28c5ecd8d76db047a0a39e2c11f844202d0e82c28f591d4dc4216e9`.
Guest and host measurements match. The measured `system_ext` image is
792,690,688 bytes, SHA256
`938d37bd18aae9f01640a28fc8e5d7bd9869e8ef51aea458adfbe95e406e60da`;
its admission updates the signing contract without increasing the image budget.

Camera artifact gates, native dependency bindings and filesystem configuration
checks pass on the unsigned and signed archives. The signing checks preserve
the original factory verifier, APK payload and required signing relationships.
All 272 selected filesystem configuration files and 98 policy inputs match
between the verified unsigned and signed images.

Normal-init policy compilation passes, with only the existing userdebug `su`
domain permissive. The separate strict neverallow compile retains the same
16 existing conflicts as v9, with no new conflicts; it does not pass. V10's
measured Enforcing state does not prove v11 runtime policy loading.

After the measured image admission and signing-contract update,
`make test-current` passed 939 tests in 29.001 seconds; `make test` passed
4,885 tests in 194.538 seconds plus shell checks. The separate C++ source
harness passed 43 selector-disabled and 46 selector-enabled assertions with
the undefined-behavior sanitizer. These checks do not require a phone.

## Signed delivery

The signed target-files archive is 11,145,217,133 bytes, SHA256
`dbdfefb26e4acdbd2081175412de3935527b5a07dab6b4da312913fdb88c1c02`. Signing, reconciliation and the
published AVB inventory pass. The private bundle is
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v11r1/`.
Its manifest SHA256 is
`b6966d7e2071e23de371d74e1e295d4e7c8277465ae8f50f3ee5ac96a5b64d80`.

All eight payload identities pass verification: shared Super and seven slot-A
chain images (DTBO, init_boot, vendor_boot, recovery, boot, vbmeta_system and
vbmeta). The [structured delivery record](../research/camera-v11-package-20260908.json)
binds the source, native component, full builds, tests, package correction,
archive, policy, signing and bundle receipts. No phone action was performed
while preparing this candidate. It remains not device-admitted.

## Next device validation

After explicit approval, install the corrected bundle through the existing
shared-Super/slot-A route without a wipe or slot change. Capture the earliest
available audio startup log and audio service snapshots before enabling root
ADB for the remaining diagnostics. The prepared collector checks the exact
approved manifest and acknowledged writes; it does not issue a reboot or
restart audio services.

Confirm build identity, slot A, Enforcing policy, installed cameraserver bytes,
Camera APK/signer and app-data retention before the first camera launch. Repeat
ordinary Xiaomi Ultra HDR and main-camera 50 MP captures, then require complete
image decodes for telephoto 50 MP and 200 MP. Test Pro RAW and one bounded Ultra
RAW attempt; independently decode any DNG and stop that path if the provider
crashes again. Recheck all three physical RAW sensors and the five Aperture
effects on rear/front cameras in one running app process.

The audio startup record must identify the video initialization failure before
selecting an audio repair. Useful effect quality, native sensor resolution,
stabilization and full camera acceptance remain unverified. Saved files and
complete decodes are required; mode labels and advertised dimensions alone
do not prove capture support.

V10 and earlier rollback bundles, working76 recovery, stock return inputs and
signing material remain preserved. This private eight-image bundle is not an
OTA or TWRP installer. Proprietary inputs, build archives and device evidence
remain in ignored directories.
