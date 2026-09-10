# Camcorder profiles: why the Xiaomi camera offers only 1080p30, September 9, 2026

**On v15 the platform loads the generic `media_profiles_V1_0.xml`, whose
highest quality is 1080p30, because the factory system property
`media.settings.xml` is missing from our system image. The stock system
build.prop sets it, and the QTI-patched profile loader then upgrades to
`/vendor/etc/media_profiles_canoe_v2.xml`, which carries the 4K, 8K, DCI and
high-speed profiles.** The guarded fragment
`device/xiaomi/nezha/camera-video-profiles.mk` restores the property; its
contract is `config/nezha-camera-video-profiles.json`. This is a source
finding; the corrected build is packaged as delivery set v16 (identity
`nezha.434625bd9b5cd7a8a7eabd84`, bundle manifest SHA256
`5c57a12ff14d98349742ce59e6214d2ab2377c0c5e18edc2265b9b27b7188c3d`, see the
[CameraOpt record](cameraopt-four-methods-20260909.md) for the gates) and is
not yet installed.

## How it was found

The tier 2 video matrix started from the Xiaomi app's Video mode on v15. The
Resolution (1080P) and Frame rate (30FPS) controls accept no tap, with Dolby
Vision on or off; a long press opens only the control-rearrange panel, so the
touches do reach the bar. A read-only reflection helper run from a root shell
then asked `CamcorderProfile` what the platform exposes: cameras 0 and 1 list
qualities 0 to 7 and the time-lapse qualities only, highest 1920×1080 at 30 fps,
with no 2160p, 8K or high-speed quality at all. The camera HAL is not the
limit: every rear device advertises 60 fps target ranges and 120/240 fps
high-speed configurations in `dumpsys media.camera`.

`frameworks/av/media/libmedia/MediaProfiles.cpp` explains the table choice.
With `media.settings.xml` unset it searches product, odm, vendor and system for
`media_profiles<ro.media.xml_variant.profiles>.xml`, and that variant property
is also unset, so the default `_V1_0` file wins. With `media.settings.xml`
naming a `/vendor/etc` path, the QTI branch substitutes
`/vendor/etc/media_profiles<ro.media.xml_variant.codecs>.xml` when it exists.
The codec variant is `_canoe_v2` on this phone, copied by
`init.qti.media.rc` from the vendor target variant, and the file exists.

| Table | Camera 0 profiles | Highest camera 0 | High-speed profiles |
| --- | --- | --- | --- |
| `media_profiles_V1_0.xml` (loaded on v15) | 13 | 1920×1080@30 | none |
| `media_profiles_canoe_v2.xml` (stock selection) | 24 | 7680×4320@30, 4096×2160@24, 3840×2160@30 | 1080p@120 and 720p@240 on camera 2, 1080p@120 on camera 3 |

The stock system build.prop line 100 reads
`media.settings.xml=/vendor/etc/media_profiles_vendor.xml`. That file does not
exist on the vendor image either; the key only needs to name a `/vendor/etc`
path for the loader to take the codec-variant route.

## What changed in source

The fragment sets exactly the stock line through `PRODUCT_SYSTEM_PROPERTIES`
when `NEZHA_CAMERA_VIDEO_PROFILES := true`, refuses a second owner of the key,
and is included from `device.mk`. Tests cover the selector states, the
exclusive-ownership guard, the generator's template list and the stock
build.prop pin when the factory extract is present. The audio descriptor
contract was rebound to the new `device.mk` bytes with a history note.

## What this does not prove

The Xiaomi application's resolution and frame-rate lists after the property
lands, 4K, 8K and high-speed sessions on this framework, Dolby Vision,
stabilization and the microphone at those resolutions, and other
`MediaRecorder` clients such as Aperture are all unverified until the next
delivery set is installed and the video matrix is run.
