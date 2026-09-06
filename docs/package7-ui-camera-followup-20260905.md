# Installed-successor UI and Aperture follow-up — September 5, 2026

The installed device remains build `nezha.a6d3109ae93158c498bb30b0`. Two narrow
source corrections have since been admitted and compiled as components:

- commit `3bed419` changes Aperture's shared configuration updater to return
  without mutation when camera configuration has not initialized, closing the
  captured mode-selector/null-configuration race;
- commit `074183c` supplies the measured Nezha display pixel pitch used by the
  lockscreen fingerprint icon, replacing the installed build's invalid `-1`
  fallback.

These changes have not been packaged, signed or installed. Their component
success does not prove Aperture preview/capture, vendor camera-provider repair,
or corrected UDFPS rendering on the phone.

## Source and component result

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

## Current boundaries and next gate

The Aperture change fixes the proven app-side null-state race. The separate
vendor `0x9005` / role-64 stream-configuration abort remains unresolved and the
current captures do not map it to an Aperture stream. The provider's camera-list
entry point copies an already populated private-ID vector, so the unresolved
mismatch is earlier in that private-ID population path. No provider fix is
claimed.

Before installation, build a fresh target-files package for
`nezha.376a73a742ddc9da2bdedab3` or its explicit successor, then repeat archive
admission, AVB signing/reconciliation, Super assembly/readback, qualification
and bundle verification. Any install requires its own authorization. Device
validation must separately test the lockscreen icon, Aperture process survival,
camera open, preview, capture and Xiaomi Camera.
