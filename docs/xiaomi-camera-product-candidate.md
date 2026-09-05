# Original Xiaomi Camera product candidate (September 5)

The user requested native Xiaomi Camera integration after Package7 booted.
`scripts/camera_product_inputs.py` now derives a separate, opt-in product
namespace from the unchanged verified factory Camera packet. The earlier
build-only packet and its contracts remain historical inputs; this new workflow
provides the product integration instead of changing their scope flags.

The real staged candidate is
`artifacts/camera-apk-inputs/product-candidate-20260905`. Its source namespace is
`vendor/xiaomi/nezha-camera`; the product fragment is `camera-product.mk` and the
app module is `NezhaXiaomiCamera`. The filename remains `MiuiCamera.apk`.
The integration requires the existing nine-file Camera runtime bundle and
patched Soong DEX provider already used by the Package7 source tree. Copy only
the candidate's `source/` inventory to the exact namespace, check the recorded
file hashes, then explicitly inherit its product fragment. No installer,
phone command, source copy or native build runs from the host staging script.
The parent's build coordinator owns actual source adoption and compilation.

The APK retains its original 204,365,218 bytes, SHA256
`7bce1fb140802511bb3d6527f6fcc25ef7558f278d24229755413d3a9b42199e`,
and verified OEM signing identity. Preprocessed, presigned privileged product
packaging, all three exact optional Java libraries and strict library checking
remain enabled. The content-verifying producer now also covers the product
fragment and narrow permission XML before publishing the APK. No APK re-sign,
DEX transformation, missing-library exemption or preopt disablement is added.
The two platform Window modules are explicitly selected; `miui-cameraopt` and
its registration continue to come from the required existing runtime bundle.

The same-partition privilege policy selects the eleven possible platform
privileged requests from the hash-bound factory inspection, including
`SYSTEM_CAMERA` and the feature-dependent keyguard subscription permission.
It excludes the unrelated MediaTek entry, dangerous `READ_PHONE_STATE`, and all
pure signature requests. Android must continue to deny the three unsupported
pure signature permissions (`CONTROL_DEVICE_STATE`,
`CONTROL_DISPLAY_BRIGHTNESS`, `INJECT_EVENTS`) without a qualifying signing
relationship; a SELinux platform label is not that relationship.

Read-only guest inspection found all three Java providers in the existing
user-policy output. It captured the six generated framework MAC/seapp files
and combined them with the four hash-verified retained vendor/ODM captures.
That composition has eight distinct signer certificate sets. The existing
retained vendor mapping selects `seinfo=platform` for the original Camera
certificate, and the generic platform seapp rule predicts `platform_app`.
There is no competing Camera-specific rule and no new mapping is needed.
This is static composition evidence, not execution of Android's resolver or
observation of a running Camera process. Generated vendor/ODM output files
were explicitly excluded because the delivered images retain their own files.
The private report `reports/xiaomi-camera-product-20260905/composed-mac.json`
records the ten actual input hashes and the distinction.

All forty actual embedded AArch64 libraries were re-parsed for ELF dependencies.
The private `jni-elf.json` report records their twenty external dependency
names. OEM dependencies include retained vendor/ODM `libOpenCL`, `libcdsprpc`,
`libmialgo_ai_vision`, `libmialgo_utils`, `libmiocr`, and
`libxmi_slow_motion_mein`. File retention does not establish app linker-namespace
visibility, symbol compatibility or dynamic loads from proprietary Java code.
The selected system-ext algorithm JNI wrapper also depends on private platform
interfaces, as documented in the earlier dependency inspection.

The existing built framework manifest still contains both conditional
permission-definition branches. AAPT inspection alone therefore does not
identify their runtime-effective protection levels. The eleven-entry
allowlist covers either privileged branch; it does not imply signature grants.

Reproduction uses fresh ignored directories:

```sh
python3 scripts/camera_apk_inputs.py stage --output artifacts/camera-apk-inputs/ORIGINAL_NEW
python3 scripts/camera_product_inputs.py stage \
  --input-packet artifacts/camera-apk-inputs/ORIGINAL_NEW \
  --output artifacts/camera-apk-inputs/PRODUCT_NEW
python3 scripts/camera_product_inputs.py verify \
  --input-packet artifacts/camera-apk-inputs/ORIGINAL_NEW \
  --output artifacts/camera-apk-inputs/PRODUCT_NEW
python3 -m unittest discover -s tests -p 'test_camera_product_inputs.py' -v
```

The native build must verify the original packaged APK hash, packaging check,
strict manifest-library status, real dexpreopt outputs and installed permission
XML. Camera startup, preview, capture, lens switching, video, Leica modes,
Android permission grants and native linking remain device validation work.
