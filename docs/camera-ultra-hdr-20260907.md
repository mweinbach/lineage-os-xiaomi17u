# Ultra HDR initialization and rear/front capture, 2026-09-07

**Aperture saved rear and front Ultra HDR photos on the installed v8 build, and
both saved files passed real gain-map decoding.** The earlier JPEG_R configuration failure
had a startup-order dependency: the factory vendor wrapper checked a persistent
enable property before entering the EcoEngine stage that initializes it. An
ordinary JPEG configuration ran that initializer, allowing the later JPEG_R
session to configure and capture.

The authored `NEZHA_CAMERA_JPEGR_DEFAULT` integration supplies the same enabled
value as a build-property default. It is off by default and requires
`NEZHA_CAMERA_FRAMEWORK=true`. It is **not device-admitted**: generated-property,
source-installation, build and first-camera-session boot validation are still
required. The successful v8 capture used the existing factory initializer; it
does not prove the new fragment was installed.

## Measured initialization dependency

The factory `odm/etc/camera/xiaomi/ecoMetaExtensionExt.json` contains the
`MiviThirdJpegr` rule. Its source accepts the empty string or literal `0` for
`persist.vendor.camera.sdk.third.jpegr.enable`, and its target writes `1`.
The rule has no app or camera-ID restriction. Its file SHA256 is
`a4ee1a473b12fe4e6d75a5d423922cf4e139bda8e288f75c003c35de2ad57def`.

The vendor AIDL wrapper detects JPEG_R dataspace `0x1005`, then reads this
property with default `0`. It only continues into EcoEngine when the value is
nonzero or the session includes a CameraX extension connection. Ordinary JPEG
does not encounter that JPEG_R-specific gate. The factory configuration rule
can write the property only after a session enters the EcoEngine Config stage.

The retained v8 logs distinguish those stages:

- The early rear and front JPEG_R attempts opened EcoEngine but skipped its
  configuration stage, then failed vendor graph construction.
- The rear ordinary JPEG configuration at 17:47:59 showed the `MiviThirdJpegr`
  rule matching an empty property and completing. A later front ordinary JPEG
  configuration did not match the rule again.
- The later JPEG_R retry recorded property value `1` before opening camera 0,
  entered EcoEngine's third-party JPEG_R mode and completed configuration.
- A manual shutter capture reported a saved image at 18:37:35.677. The saved
  bytes supplied the separate HDR evidence below.

The exact wrapper, rule-loader and property-writer disassembly, log lines and
input hashes remain in the ignored
`reports/camera-completion-20260907/ultra-hdr/` analysis reports. No separate
factory init.rc or build.prop assignment was found in the bounded retained
text/config search. Establishing the default earlier is an explicit port
integration based on the measured factory rule, rather than a copied factory
boot-property assignment.

## Verified saved image

| Measurement | Result |
| --- | --- |
| Installed source/build | v8 `nezha.f2e3feac321f56f92d2ad7ea` |
| Application/camera | Aperture, rear camera 0, Ultra HDR enabled |
| Saved JPEG size | 2,372,274 bytes |
| Saved image dimensions | 3072 × 4096 |
| Saved JPEG SHA256 | `fcea377aeae783df79d82b8f6814b8575870d382caf51f4a4057619b5b64cee7` |
| Decoder | `libultrahdr v1.4.0`, `ultrahdr_app` |
| Decode result | Exit 0 |
| Gain map maximum content boost | 1.48872; HDR capacity maximum also 1.48872 |
| Decoded RGBA F16 output | 100,663,296 bytes, equal to 3072 × 4096 × 8 |

The front camera 1 independently saved a 7,072,821-byte, 3072 × 4096 JPEG
with SHA256 `a159549356a29bc2194d3028887acc69c91c106216057fdbd3a85310cc9713c3`.
Its gain map has maximum content boost and HDR capacity maximum `2.26206`.
The same decoder completed with exit 0 and produced 100,663,296 RGBA F16 bytes.
Both captures used the existing factory-initialized property value `1` on v8.

The private image and decoder evidence are retained under
`reports/camera-completion-20260907/aperture-tests/ultrahdr-verified/`.
This establishes a nontrivial gain map and successful HDR decoding, beyond the
app's save callback or its ordinary JPEG container-format label. The scene was
dark and close to the camera, so this is capture/format proof rather than an
image-quality assessment. Other lenses, CameraX extension modes, high-resolution
capture and Xiaomi Camera acceptance remain separate device results.

## Selected-source candidate

The [new fragment](../device/xiaomi/nezha/camera-jpegr-default.mk) is described by
the [source contract](../config/nezha-camera-jpegr-default.json). When selected,
it appends exactly this value to `PRODUCT_SYSTEM_PROPERTIES`:

```make
persist.vendor.camera.sdk.third.jpegr.enable=1
```

Using the system property output follows the existing camera-framework port
and keeps the factory vendor/odm images intact. The fragment has no runtime
property writer and does not alter camera capabilities, metadata, stream
formats, encoders, task profiles or scheduling state.

This is a default for a fresh persistent-property store. Android still loads
any existing persisted value over its build default. A stored `0` therefore
remains `0` until the existing factory rule changes it during an admitted
configuration. This integration does not add a migration or overwrite a
persisted value. A selected build must verify the final property output and a
first-session JPEG_R capture before this default can be called boot-validated.

The focused offline tests exercise actual Make selection and dependency
handling, verify the exact property output, preserve unrelated build variables
and recompute the contract's fragment hash. They do not need a phone and cannot
establish persistent-property behavior on a booted device.
