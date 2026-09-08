# Camera v10 package, 2026-09-08

**V10, `nezha.0c10ad024d3033691a2825cc`, passed its full Android build and
signed archive checks. Its eight-image bundle passed byte-identity verification.**
The phone remains on installed v9, `nezha.393aae12fba9ebe8627cdc38`. V10 has
not been installed or tested on the phone, and needs its own flash approval.

This candidate combines two measured fixes:

- [Vendor-key discovery](camera-vendor-key-discovery-20260908.md): Xiaomi
  Camera's available-request-key list omits registered vendor keys used by its
  request builder. The guarded Nezha/Camera-package framework path merges those
  registered keys. The built framework DEX contains the guarded entrypoint and
  helper, and the corresponding framework resource is enabled.
- [CameraX extension cache](camerax-extension-cache-20260908.md): the bundled
  library reuses metadata from the first effect queried on a camera. The
  upstream backport keys the cache by camera and effect. Its compiled classes
  pass the JVM behavior harness; the optimized Aperture DEX retains the nested
  lookup and population in its active, inlined synchronous path.

The source transaction verified 659 inventory rows before and after the
combined Aperture component build and full target-files build. The latter
completed 4,363 actions with exit code zero. The build retained the pinned
manifest and source selections, the existing output/cache, and the sole writer
VM on the case-sensitive ext4 volume. No source sync or reset was performed.

## Artifact verification

The transferred target-files ZIP has SHA256
`8cbf2a684261aa259ac520b54f5b32bd7e5253a2431261e094ba6fe85909aec7`
and is 11,322,900,726 bytes. The sparse Super image is 9,476,720,752 bytes,
SHA256 `6926c1a2e5fe18d5bf3a43ca7ed0637beecc8dd47e9dbf22d999d257cf63cea4`.
The host readback matches both guest measurements.

The archive's `framework.jar`, `framework-res.apk`, and `Aperture.apk` are
byte-identical to the inspected component artifacts. The camera artifact
checks passed for the original factory verifier/Binder ABI, service classpaths,
platform signing, preserved proprietary APK payload, helper API, and native
exports. The separate native-library audit binds the retained ELF analysis to
the final archive's libraries, APEX containers and library-name resolution.
These checks do not establish runtime linker behavior or a successful capture.

The actual filesystem images passed configuration checks for the build
properties, CameraOpt service/property contexts and reviewed privileged
permissions. All 98 policy input files are byte-identical to v9. A fresh native
compile using the modeled normal-init flags produced the same policy binary,
SHA256 `3cdb97b4fda06f3be46cc34a24ac944eb330ae42bcc395136b25a4a18869b2a7`.
Only the existing userdebug `su` domain is permissive in that compiled policy.

The separate strict neverallow compile still reports the 16 existing v9/v8
conflicts. Its full stderr matches v9 after normalizing only temporary file
descriptor numbers; there are no new conflicts. This is a qualified baseline
comparison, not a claim that the strict compile passes. V10's runtime policy
and kernel load remain untested.

The measured `system_ext` image is 792,690,688 bytes, SHA256
`0af4035baaea12652952ef4977857da7b8ce0c241311a1dc33d8c857e1229f01`.
Its archive/guest admission record has been added to the host signing contract,
and the dependent contract hashes were regenerated. The 939 current tests
passed in 29.886 seconds. The full offline suite passed 4,881 tests in
197.202 seconds, plus shell checks, after that admission update.

## Signed delivery

The signed target-files archive is 11,145,218,862 bytes, SHA256
`8963528914383eeed5769af44e7b6c091d76974b66e0bcef066b73803912fa21`. The complete
signing sequence, archive reconciliation and final AVB inventory passed.
The signed camera, native-library and component-identity gates passed again.
All 272 selected filesystem configuration files and 98 policy input files
match the verified unsigned package.

The private bundle is
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v10/`.
Its manifest SHA256 is
`739acc4ffad8d5eaf3828af4ead90d9387bc646251f5f9f3a74468877ca886f9`.
All eight payload byte identities passed verification: shared Super and seven
slot-A chain images (DTBO, init_boot, vendor_boot, recovery, boot, vbmeta_system
and vbmeta). It remains **not device-admitted and not flash-ready** until the
separate explicit approval and fresh device preflight. The
[structured delivery record](../research/camera-v10-package-20260908.json)
binds the source, tests, build, archive, signing and bundle receipts.

## Device status and next validation

On [installed v9](camera-v9-install-validation-20260908.md), the original
CameraOpt verifier succeeds, but Xiaomi Camera's first rear Photo capture did
not save. All ten Aperture effect captures saved fully decoded Ultra HDR
photos. Bokeh Ultra HDR and telephoto RAW regression captures also passed.
The recorded effect-switch failure remains reproducible on v9.

After an approved v10 installation, first verify the build, slot and enforcing
policy, then test Xiaomi Photo saving and same-process Aperture effect
switching. Repeat ordinary Ultra HDR/RAW regressions before progressing to the
factory 50 MP, telephoto 200 MP and processed Ultra RAW modes. Retain the actual
saved files, decoded dimensions, camera/session and sensor evidence for each.
High-resolution support, useful effect quality, video and full camera acceptance
remain unverified. A UI mode or advertised size is insufficient evidence.

V9, v8/v7 rollback bundles, working76 recovery, stock-return inputs and signing
material remain preserved. This private eight-image route is not an OTA or
TWRP installer. No wipe or slot change is part of the proposed next validation.

Private build/artifact receipts are under
`reports/camera-completion-20260907/` (`v10-full-run/`, `v10-unsigned-*`,
`native-artifacts-revision-5/`, `config-artifacts-revision-5/`) and
`reports/variant-opt-in-20260906/v10-*`. Proprietary inputs and phone evidence
remain ignored.
