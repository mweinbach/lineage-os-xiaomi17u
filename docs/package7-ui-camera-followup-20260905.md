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
`nezha.f9e30611efe01b882f9ed0cb`; its native SystemUI component build is still
running.

None of these changes has been packaged, signed or installed. The completed
`376a` component result does not prove Aperture preview/capture, vendor
camera-provider repair, or corrected UDFPS rendering on the phone. The `f9e`
shade source has no completed native component result yet.

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

## Current `f9e` shade source and pending build

The shade source transaction was applied on top of the preserved 572-row
`376a` inventory. The current source inventory contains 574 rows and has SHA256
`abaa6c525a6b2e628c7ac48d0a4015e43d43d331b3244b8282103d02a6cd27fc`.
All 572 prior paths remain present. The transaction adds the framework default
resource and patched `NotificationsQSContainerController.kt`, and updates the
Nezha overlay to opt in. The resulting build number is
`nezha.f9e30611efe01b882f9ed0cb`.

Patch 0028 leaves `rounded_corner_content_padding=100px` and
`status_bar_padding_top=38px` unchanged. The framework resource defaults the
new behavior to false, while Nezha opts in. In portrait on the normal single
shade, the controller anchors the header to the parent with a derived 49px top
inset. Landscape, split shade and large-screen header modes retain a zero
inset. The existing fixed header height and its internal constraints are
preserved.

The native SystemUI build is running against the preserved output. Until it
returns successfully and its artifact is admitted, `f9e` is source evidence
only. There is no new SystemUI APK identity, target-files package, signing,
Super assembly, bundle or installation result from this transaction.

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

First finish and admit the current SystemUI component build. Before
installation, build a fresh target-files package for
`nezha.f9e30611efe01b882f9ed0cb` or its explicit successor, then repeat archive
admission, AVB signing/reconciliation, Super assembly/readback, qualification
and bundle verification. Any install requires its own authorization. Device
validation must separately test the normal status bar, shade header, lockscreen
icon, Aperture process survival, camera open, preview, capture and Xiaomi
Camera.
