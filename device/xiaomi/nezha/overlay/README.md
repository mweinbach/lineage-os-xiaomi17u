# Nezha display geometry

These authored overlays reproduce only the framework and SystemUI geometry
values in the retained exact-device factory product image. They address the
September 5 Package7 report that status-bar icons sit incorrectly against the
physical corners. They do not change display density or launcher spacing.

Factory product image SHA256:
`67e6c683c1091abc0a548c27e4681bbe26471529129d15453b95c8d69417795f`.

| Factory source | APK SHA256 | Selected values |
| --- | --- | --- |
| `/product/overlay/DevicesAndroidOverlay.apk` | `a73f3829f4cb59f78310d40f35ccc027e3faa08712739d038273c50cb94034f0` | All three corner radii 170px; default and portrait status bar 144px; cutout `M 0,0 H -34 V 144 H 34 V 0 H 0 Z` |
| `/product/overlay/DevicesOverlay.apk` | `b46b8e61a6287232832445e5a74f0012b148c1928bed0916b2aa0b0f1aeb1c74` | Rounded-corner content padding 100px; status-bar top padding 38px |

The factory manifests target `android` and `com.android.systemui`, respectively.
Readback-verified extraction receipts and `aapt2 dump resources` output are kept
privately under `artifacts/display-stock-20260905/devices-overlays/`. Extraction
used the hash-bound stock EROFS inventory without mounting or executing firmware.
Resource decoding used the installed Android SDK 37.0.0 `aapt2`.

Package7 diagnostics reported native 1200 x 2608, density 480 with no override,
an empty framework cutout, 20dp corner radius (60px), and a 28dp status bar
(84px). Density already matches factory. The cutout is the factory's rectangular
safe-area approximation, not a newly measured camera-hole contour.

Keep these dimensions in pixels, as in the factory resource table. Do not copy
unrelated stock animations, biometrics, doze components, colors, or its display
shape resource. The latter describes a 1080 x 2400 contour and has not been
validated against this panel. No landscape status-bar value is inferred.
The stock 20px `status_bar_padding_bottom` is also omitted: the pinned Evolution
SystemUI has no matching resource. All eight selected names exist in Evolution
`frameworks/base` revision `8140698cc12983deecdbd434220affb5f931bfc6`, checked
against its framework `config.xml`/`dimens.xml` and SystemUI `dimens.xml`.

`DEVICE_PACKAGE_OVERLAYS` selects these resources ahead of common product
overlays. The device generator copies and hashes each selected overlay file.
Source/resource validation is separate from a successor image build and the
required visual check on the phone; this change has not yet been device-tested.
