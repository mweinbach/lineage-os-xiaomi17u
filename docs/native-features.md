# Retaining Xiaomi 17 Ultra stock features

Research date: **2026-08-27**. Every Evolution X feature below is **untested on
the target phone**. A working camera preview, a successful ROM build, or an APK
that installs is not evidence of stock feature parity. The dependency and test
columns are engineering hypotheses to verify against the exact stock build;
they are not claims that particular blobs or workarounds already work.

The user reports China-edition hardware currently running xiaomi.eu; read-only
Android collection corroborates `nezha`, HWC CN and the modified xiaomi.eu
product. See [device-baseline.md](device-baseline.md). Preserve that current
installation as a separate feature baseline in the research records, and
identify the matching official China vendor/firmware source. Do
not label xiaomi.eu output as an unmodified factory-stock test. The global
product specifications below are a feature inventory, not proof of this
China variant's capacity, radio bands, eSIM availability or firmware.

The practical approach is to establish the phone's stock hardware/vendor
contract first, get ordinary Android functions working with enforcing SELinux,
then add Xiaomi-specific services and apps in isolated changes. Keep a stock
baseline for every proposed feature. Do not overwrite a working vendor stack
with another phone's files or make SELinux permissive to hide missing policy.

The supplied-package follow-up has now located and hashed 13 external Camera
dependencies and confirmed that its Camera APK matches the live snapshot.
See the [camera findings](camera-baseline.md) and the concrete
[Nezha integration plan](nezha-integration.md). These are static dependency
results only. The package's retained AVB metadata does not match its modified
images, so its fstab and images must not become an unreviewed boot/security
template for the port. Every hardware acceptance test below remains unrun.

## Dependency and acceptance matrix

The public global hardware baseline is documented in
[Xiaomi's global specifications](https://www.mi.com/global/product/xiaomi-17-ultra/specs/).
Regional availability is not assumed. Tests below describe future, explicitly
authorized device validation, not actions performed by setup scripts.

| Feature to preserve | Dependency investigation | Reproducible acceptance test | Status |
| --- | --- | --- | --- |
| Basic cameras and physical lens controls | Exact sensor/actuator drivers, camera provider HAL, ISP/DSP firmware, tuning/calibration, vendor tags, logical/physical camera IDs, media profiles. Preserve calibration; never substitute another unit's data. | On stock and ROM, enumerate IDs/modes, capture rear/front stills and videos, check focus, stabilization, lens transitions and 75–100 mm optical zoom. Check output files, not just UI labels. | Untested; baseline needed. |
| Leica processing and advanced capture | Stock Camera APK, JNI libraries, Xiaomi postprocessing services, framework/shared-library dependencies, signing/privileged permissions, feature configuration and model-specific tuning. | Fixed lighting and target: compare Leica styles, HDR/LOFIC behavior, portrait, night, macro, RAW and high-resolution modes. Check color, metadata, processing completion and repeatability. | Untested; highest dependency uncertainty. |
| Advanced video and HDR playback | Camera pipeline plus encoder/decoder capabilities, color management, codec configuration, Dolby components and licensing where applicable. | Record the modes actually available on this stock variant; inspect codec, bit depth, frame rate, HDR metadata, audio sync and dropped frames. Play on a known compatible display and test sustained recording. | Untested; mode names alone are insufficient. |
| Calls, data, SMS and IMS | Matching modem firmware, RIL/radio HAL, IMS service/APKs and libraries, carrier overlays, provisioning and carrier entitlement. eSIM additionally needs the appropriate eUICC/LPA support where present. | With a known supported carrier: incoming/outgoing calls, SMS, mobile data, IMS registration, VoLTE/VoWiFi, Wi-Fi/cellular handover and dual-SIM behavior. Emergency behavior only through a carrier-approved test procedure; never place unsolicited emergency calls. | Untested; registration/data do not prove voice or IMS. |
| Fingerprint, lock screen and encryption | Ultrasonic fingerprint HAL, vendor service, display/touch coordination, trusted firmware, KeyMint/Gatekeeper/Weaver/StrongBox as actually present. Recovery decryption patches are not a security design for Android. | Authorized enrollment/removal, rejection of an unregistered finger, screen-off unlock, lockout and credential fallback, plus encryption and app biometric authentication. Record the actual biometric strength. | Untested; do not weaken authentication or trust storage. |
| Charging, battery reporting and thermals | Exact charging drivers, battery/health and power HALs, Xiaomi charge/thermal services, power hints, limits and unit-specific calibration. Inspect wired, wireless and reverse power paths separately. | With certified accessories and controlled ambient temperature/state of charge, compare negotiated power and temperature curves, charge limits, current reporting, idle drain and throttling. Stop on abnormal heat or charging behavior; do not defeat protection. | Untested; no maximum-power guarantee. |
| Display, refresh, brightness, touch and AOD | Panel-specific driver/DTS, composer and display HALs, Xiaomi display service, brightness/calibration tables, overlays, touch service and doze behavior. | Verify real mode transitions, low-brightness rendering, automatic brightness, HDR presentation, touch while charging, suspend/wake and AOD drain. Distinguish a selected refresh setting from measured presentation. | Untested; use the target panel's data. |
| Audio and haptics | Audio HAL, DSP firmware, mixer/audio policy, effects libraries, microphone routing, vibrator HAL and waveform configuration. | Earpiece/speaker, every microphone route, calls, recordings, USB/Bluetooth audio, channel balance, volume limits and synchronized haptic patterns. Test vendor audio effects separately from basic sound. | Untested. |
| Wi-Fi, Bluetooth and GNSS | Matching wireless firmware/modules, HALs, coexistence configuration, regulatory data, codec support and location services. | Supported bands and APs, reconnect/suspend, hotspot, Bluetooth calls/audio and codec negotiation, GNSS fix and navigation. Do not change regulatory limits to make a test pass. | Untested. |
| NFC and IR | NFC HAL, secure-element/OMAPI integration where present, vendor permissions, Consumer IR HAL and transmitter configuration. | Read/write an owned test NFC tag, test permitted secure-element use, and send a known IR command to an owned appliance. Payment certification is a separate result, not implied by tag reading. | Untested. |
| Photography Kit, standard model | Xiaomi's stock Camera integration and Bluetooth accessory protocol, button events, battery reporting and settings integration. Identify the actual accessory first. | Pair/reconnect, half/full shutter press, video button, camera launch, battery status and idle disconnect. Separate generic button support from stock Camera feature support. | Untested; standard kit is Bluetooth. |
| Photography Kit Pro | USB-C accessory/control path, charge coordination, stock Camera/grip service and settings; shutter, zoom and dial mapping. | Connect/disconnect, half/full shutter press, zoom/dial, video and launch behavior, charging transition and battery reporting. Verify each function independently. | Untested; distinct from the Bluetooth kit. |
| Physical Leica Camera Ring | Only in scope if the identified phone actually has the ring. Requires the matching input/service path and camera integration. | Check detected input, assigned zoom/exposure behavior, camera-mode changes and grip coexistence. | Conditional; do not assume standard Ultra hardware includes it. |
| HyperOS apps, cloud/AI and cross-device features | Xiaomi framework APIs, privileged permissions/signatures, account services, server eligibility, region and licensing. Inventory the user's actual must-have workflows first. | Run each named workflow against a stock baseline, including offline/error behavior. Preserve privacy and do not request account credentials in the repository. | Not promised; a separate application/service port. |
| DRM, payment and app integrity | Hardware-backed trust, boot state, licensed provisioning, app/service policies and signing. | Check legitimate service eligibility and playback/payment behavior without modifying attestations or device identity. Do not collect keys. | Not promised; custom-ROM feature parity is not sufficient. |

The standard grip and Pro grip are real, distinct accessories. Xiaomi's
[standard kit FAQ](https://www.mi.com/global/support/faq/details/KA-667482/)
describes Bluetooth and says third-party camera apps are unsupported. Its
[Pro product page](https://www.mi.com/ae-en/product/xiaomi-17-ultra-photography-kit-pro/)
describes USB-C, a 2000 mAh battery and grip controls. Therefore, a working
Bluetooth/USB link is only the first test, not evidence that a stock grip feature
has survived the ROM change. Leica's
[Leitzphone specifications](https://leica-camera.com/en-US/mobile/leitzphone-powered-by-xiaomi/technical-specification)
identify the separate Camera Ring feature.

## Camera integration is more than an APK

Android's camera HAL connects application APIs to the device pipeline. The
standard framework does not itself supply Xiaomi's image tuning or Leica
processing. First identify the actual provider interface from stock VINTF;
do not assume its AIDL/HIDL version from an older phone or tutorial.
[AOSP camera architecture](https://source.android.com/docs/core/camera),
[AOSP VINTF](https://source.android.com/docs/core/architecture/vintf)

Evolution X already has a useful **packaging example for a different device**:
`Evolution-X-Devices/device_xiaomi_peridot-miuicamera`, branch `bka`, commit
`5f2bdfecdbd12c5deaf9ccf94b365e1fc4596426` (2026-03-05). Its product file adds
permission configuration and an overlay; its proprietary list includes the
Camera APK, JNI libraries, a Xiaomi GUI library and postprocessing interfaces.
This demonstrates the categories to inventory, not compatibility with Nezha.
[Pinned product configuration](https://github.com/Evolution-X-Devices/device_xiaomi_peridot-miuicamera/blob/5f2bdfecdbd12c5deaf9ccf94b365e1fc4596426/device.mk),
[Pinned proprietary list](https://github.com/Evolution-X-Devices/device_xiaomi_peridot-miuicamera/blob/5f2bdfecdbd12c5deaf9ccf94b365e1fc4596426/proprietary-files.txt)

For Nezha, collect the matching stock package and examine app manifests,
required shared libraries, native ELF dependencies, referenced Binder/HAL
services, permissions and configuration. Record SHA-256 and provenance for
each private artifact. Preserve original licenses and signing requirements;
do not distribute extracted apps or blobs merely because a different port
publishes a file list. Keep the eventual camera package and its narrow policy
changes separate from the baseline device tree so failures can be isolated.

Similarly, IMS is an explicit telephony integration, not an automatic result
of loading modem firmware. Android documents an IMS service and carrier
configuration contract that must be satisfied for supported calling features.
[AOSP IMS implementation](https://source.android.com/docs/core/connect/ims)

## Test records and promotion gates

For every result, record the exact device variant (without serial/IMEI), whether
the baseline is official stock or xiaomi.eu, system build and vendor fingerprint,
ROM commit and manifest revision, kernel/module
versions, firmware hashes, relevant app versions, accessories/carrier,
environment, steps, expected output, actual output and artifact hashes. Keep
private logs and photos in ignored storage; public notes should contain only
sanitized conclusions. An unavailable mode is `not available on this stock
baseline`, not a ROM regression. An unrun test is `untested`, not `working`.

1. Establish the authorized stock baseline and the exact hardware/firmware
   contract before modifying a phone.
2. Validate boot, encrypted storage, input, ordinary display, networking, audio,
   charging protections and enforcing SELinux on the eventual development ROM.
3. Validate all physical cameras through a basic Camera2 client, then add stock
   processing and accessory integration in separate commits with their own
   tests and an explicit list of unresolved dependencies.
4. Run the relevant Android CTS/VTS and camera tests on the built target as well
   as manual comparisons. A workspace unit test cannot validate a hardware HAL.
5. Do not describe the ROM as ready for daily use while telephony, encryption,
   charging safety, updates, recovery or data preservation remain unverified.

The local tooling tests remain offline and phone-free:

```sh
python3 -m unittest discover -s tests -v
```

Passing that command validates this workspace's tooling only. It does not
build Android, test a phone, unlock a bootloader, or demonstrate native-feature
support.
