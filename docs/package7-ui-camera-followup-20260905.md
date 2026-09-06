# Installed-successor UI and Aperture follow-up — September 5, 2026

The installed device remains build `nezha.a6d3109ae93158c498bb30b0`. Two narrow
source corrections were admitted and compiled as components under the later
`nezha.376a73a742ddc9da2bdedab3` source identity:

- commit `3bed419` changes Aperture's shared configuration updater to return
  without mutation when camera configuration has not initialized, closing the
  captured mode-selector/null-configuration race;
- commit `074183c` supplies the measured Nezha display pixel pitch used by the
  lockscreen fingerprint icon, replacing the installed build's invalid `-1`
  fallback.

Commit `0784f4d` now adds a third source correction: a Nezha-only opt-in that
centers the portrait shade header on the cutout-aware status-bar content while
preserving the approved normal status bar's 100px horizontal content padding
and 38px top padding. It is staged under source identity
`nezha.f9e30611efe01b882f9ed0cb`; its native SystemUI component build has now
completed successfully.

None of these changes has been installed. The completed `376a` and `f9e`
component results do not prove Aperture preview/capture, vendor camera-provider
repair, corrected UDFPS rendering or shade alignment on the phone. The fresh
`f9e` full target-files build, signing chain, Super assembly/readback and host
qualification have completed off-device. The final private eight-image bundle
also passed assembly and verification, but it is explicitly not device-admitted
or flash-ready and there is no `f9e` installation result.

## Preserved `376a` source and component result

The changes were installed into the existing source checkout as a new 572-file
source cohort. Its before and after native inventories are byte-identical,
SHA256 `06b3f2a6b761539d33ffce23a7cc2fef2d4784a1666351b145d656ab554a63ca`.
The build used identity `nezha.376a73a742ddc9da2bdedab3` and the preserved
physical output `/work/out/nezha-feature-fixes-20260905-v1`. Native execution
completed with exit 0 under
`/work/validation/feature-fixes-builds-20260905/20260906T013502`.

Incremental reuse worked as intended: Ninja scheduled 45 edges for Aperture and
SystemUI while retaining the existing Soong, host-tool and unrelated product
outputs. No clean, source sync, output replacement, new cache launcher or full
package build was used. This is concrete evidence that an admitted source
identity plus Ninja invalidation can safely reuse the preserved output for a
focused successor component build.

The final APK identities, independently matched between native output and the
host exports, are:

| Component | Bytes | SHA256 |
| --- | ---: | --- |
| SystemUI | 51,257,403 | `f2bba8e8e956d95e25344983716767909f5364c007da3a6c6b07b769dfb48816` |
| Aperture | 8,311,019 | `a80bbe6322cfb2aa2b7cbd0bd683ecc07c18039b07144fba617359968f0667cd` |

`aapt2` inspection of the exported SystemUI APK independently resolves
`dimen/pixel_pitch` to `60.583`. The receipt is
`reports/feature-fixes-20260905/ui-camera-followup/systemui-pixel-pitch-resource.txt`.
Exact component paths and hashes are in the adjacent
`component-artifacts.json`.

Focused source checks passed nine Aperture tests, three UDFPS tests and a host
`aapt2` compile. The final full offline suite passed all 4,643 tests in 202.601
seconds. These checks validate source contracts and the compiled components;
they do not replace a device test.

After the f9e package, signing, Super and qualification tooling was added, the
current full offline suite passed all 4,647 tests in 195.747 seconds; the log is
`reports/feature-fixes-20260905/shade-followup/full-unittest.log`. This includes
the source contracts for commit `954bac6` and still does not establish runtime
behavior on the phone.

## Current `f9e` shade source and component result

The shade source transaction was applied on top of the preserved 572-row
`376a` inventory. The current source inventory contains 574 rows and has SHA256
`abaa6c525a6b2e628c7ac48d0a4015e43d43d331b3244b8282103d02a6cd27fc`.
All 572 prior paths remain present. The transaction adds the framework default
resource and patched `NotificationsQSContainerController.kt`, and updates the
Nezha overlay to opt in. The resulting build number is
`nezha.f9e30611efe01b882f9ed0cb`.

The installed-source receipt and the native pre-build and post-build source
inventories are byte-identical at 574 rows with that same SHA256. Native
execution completed with exit 0 under
`/work/validation/feature-fixes-builds-20260905/20260906T022159` and reused the
preserved physical output `/work/out/nezha-feature-fixes-20260905-v1`. Ninja
completed 51 edges for the SystemUI component.

The final component identities independently match between native output and
the host exports:

| Component | Bytes | SHA256 |
| --- | ---: | --- |
| SystemUI | 51,257,403 | `7572a603498a18ff0bcf418e1819eb49f86d51ce718dbd9c8054d06dd3902ecf` |
| Aperture | 8,311,019 | `a80bbe6322cfb2aa2b7cbd0bd683ecc07c18039b07144fba617359968f0667cd` |

The Aperture artifact is unchanged from the `376a` component result. The
SystemUI artifact changes because it includes the shade alignment source.

Patch 0028 leaves `rounded_corner_content_padding=100px` and
`status_bar_padding_top=38px` unchanged. The framework resource defaults the
new behavior to false, while Nezha opts in. In portrait on the normal single
shade, the controller anchors the header to the parent with a derived 49px top
inset. Landscape, split shade and large-screen header modes retain a zero
inset. The existing fixed header height and its internal constraints are
preserved.

Host `aapt2` inspection of the exported SystemUI APK resolves
`config_alignShadeHeaderWithStatusBar=true`, `pixel_pitch=60.583`,
`rounded_corner_content_padding=100px`, and
`status_bar_padding_top=38px`. This confirms the compiled resource values; it
does not establish visual behavior on the phone.

## Current boundaries and next gate

The Aperture change fixes the proven app-side null-state race. A later unlocked
foreground attempt provides a separate result: the persistent installed
Aperture process opens public Camera0 successfully, then Xiaomi's vendor stack
fails to configure its normal 1600x1200 preview plus 4096x3072 JPEG_R session.
The log reports an empty camera-role set, repeated physical-to-role mapping
failures and a missing `MCXSuperFG` sink port while creating internal logical
camera 4's multicamera graph. The null guard does not resolve that post-open
vendor failure, and no provider fix is claimed. Xiaomi Camera's `0x9005` /
role-64 abort remains a third, separately captured failure.

The fresh full target-files build for `nezha.f9e30611efe01b882f9ed0cb`
completed with exit 0 in native session 2162, using the same persistent VM,
manifest head `cc4ebb8db9750afba6049825127304b09327f7c1`, case-sensitive ext filesystem
and preserved output. The admitted native archive is 11,277,109,433 bytes with
SHA256 `cc8304be1bd04670de6505a938bdcc3f0f16e4c472f68b4f6a73df63e2803057`.
Its packaged SystemUI and Aperture members exactly match the earlier component
artifacts.

The fresh AVB sequence completed inventory, materialization, preparation,
signing, reconciliation and publication. The reconciled target-files archive is
11,100,598,098 bytes with SHA256
`4cd1374be9370a81b505b72eadd79fcceecd777b3fed1618e725742802f76bd8`;
the signing receipt reports `signed_and_verified` with the complete chain
verified. Super assembly and LP eight-image readback also passed, including
logical and physical fit. The resulting compressed sparse Super is
9,446,504,548 bytes, expands to 15,300,820,992 bytes and has SHA256
`fd6fcfe734ffbc2b172049d0c34d61fc3df5bcfdeba740407fe708e358bd0551`.
Its second host transfer completed with the native final hash, full host stream
and host readback matching that identity. The first transfer remains a preserved
failure after its full-ancestor guard rejected the partial run; the exact
changed ancestor and field were not recorded. These are off-device artifact
results. Functional Super qualification remains false in the LP readback
receipt. The later FEC qualification closed through a
read-only recovery collector: all eight native image checks and all 42 finite
readbacks passed with the 574-row source cohort unchanged, final idle state and
the sole VM owner re-established. Its completion receipt is 5,342 bytes with
SHA256 `e1a7484fcd22e984b01cbb33ce17c21c0810796468c4f0d9c4d724540111d8aa`;
the 18,509-byte semantic admission has SHA256
`2ba3f467561fe7c1b53bed430d9c564ee79ea539a456e718a09cda343fd71a37`.
The original collector failure remains preserved and is not reported as a
successful transport.

Host APK, boot, delivery and classpath qualification also completed. It checked
456 APKs for API 36 signatures and 4 KiB alignment, preserved exact working76,
matched the four focused delivery bytes, and resolved 70 classpath JARs from 45
fragments. The aggregate admission covers the unchanged 574-row source cohort,
15 native target-files roles and 17 signed roles. The host summary retains the
documented APK findings and reports
`completed_with_retained_apk_findings`; the aggregate status is `admitted`.
Neither claims complete-ROM readiness.

The private bundle is
`artifacts/flash/nezha/package7-ui-camera-shade-20260906-v1/`. Assembly and
independent verification both completed with exactly eight payloads. Its
8,240-byte manifest has SHA256
`78693f3eb040b61dd7972bf4e432ab9d8f9000e7c6d1b433373f41a1711e4c85`.
Both receipts retain `flash_ready=false` and status
`byte-identities-verified-not-device-admitted-not-flash-ready`. This completes
the off-device build and qualification chain without establishing any live
feature result. The 5,918-byte joined qualification summary at
`reports/feature-fixes-20260905/shade-followup/qualification-summary.json` has
SHA256 `94020ef08a74c10c5924d9358e5023ef2a8edc364e72b9c8ae379146c683d0bd`.

No `f9e` image has been installed. Any installation requires its own
authorization. Device validation must separately test the normal status bar,
shade header, lockscreen icon, Aperture process survival, camera open, preview,
capture and Xiaomi Camera.
