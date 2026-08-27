# Connected phone baseline

Read-only collection on **2026-08-27** confirmed the connected phone reports
`nezha`, Xiaomi, SM8850 / `canoe`, and hardware country `CN`. This corroborates
the user's China-edition description. The current installation is **xiaomi.eu**,
not pristine Xiaomi stock firmware. No phone settings, software, partitions,
boot state, or user data were changed. No reboot, root, unlock, or flash operation
was attempted.

The sanitized machine-readable record is
[`research/device-baseline.json`](../research/device-baseline.json). Raw
inventory, XML, APKs, command logs, and the serial stay in ignored private
`evidence/xiaomi-eu-20260827T1530Z/`. These files are research inputs, not a
backup or a set of flashable images.

| Field | Observed value |
| --- | --- |
| Device / SoC / platform | `nezha` / `SM8850` / `canoe` |
| Hardware region | User: China; `ro.boot.hwc=CN` |
| Modified product | `nezha_xiaomieu_global` |
| Reported system model | `2512BPNDAG`; do not use it to select global firmware |
| Reported vendor device/model | Generic `mivendor` / `Xiaomi for arm64` |
| Android | 16 / SDK 36 / `arm64-v8a` |
| System and vendor incremental | `OS3.0.309.0.WPACNXM` |
| System security patch | `2026-07-01` |
| Vendor security patch | `2026-02-01` |
| Kernel release | `6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k` |
| Page size | `4096` bytes, read with `getconf PAGESIZE` |
| SELinux | `Enforcing` |
| Current reported slot | `_a` |

Android reports `ro.boot.flash.locked=1`, `verifiedbootstate=green`, and
`vbmeta.device_state=locked`. Modified firmware can mask these properties, so
the actual bootloader state remains **unverified**. Reading `/proc/bootconfig`
was denied. No stronger bootloader-mode check was attempted because that would
require a separately authorized reboot. Do not treat either the ROM name or
these properties as proof that unlocking, flashing, or relocking is safe.

## What was captured and verified

The collector executed **71 bounded read/pull commands**, inventoried **363
system packages**, and produced **575 artifacts**, including **432 XML files**
and the current camera APK. Every artifact's size and SHA-256 was independently
recomputed after collection and matched its manifest receipt.

The final status is correctly `partial`: reads of `/proc/partitions`, the
device-tree `model`, and device-tree `compatible` returned permission denied.
These are evidence gaps, not a reason to root the phone. VINTF/permission pulls,
the camera APK pull, `lpdump`, and the other inventory commands succeeded.

The camera APK came from `/product/priv-app/MiuiCamera/MiuiCamera.apk`, is
170,279,563 bytes, and has SHA-256
`cadf2c07cb6fd25c06f7fe6f37dc227df204bed3a873b3025aff93d53d72da79`.
Its presence is not proof that it can run on Evolution X. Package inventory
also identifies Xiaomi CameraTools, CameraMind, Gallery, and MiuixEditor, plus
Qualcomm IMS packages. Their data and APKs were not copied by this collection.

## Observed layout and hardware contracts

`lpdump` reports Virtual A/B metadata version 10.2 with three metadata slots,
a 15,300,820,992-byte `super` device and groups
`qti_dynamic_partitions_a` / `_b`, each with a 15,290,335,232-byte limit. The
logical partition names are `odm`, `product`, `system`, `system_dlkm`,
`system_ext`, `vendor`, `vendor_dlkm`, and `mi_ext`, with A/B suffixes.
The current snapshot update state is `none`. These are observations from the
installed ROM, **not approved values for a new BoardConfig**. Confirm the
physical boot chain and matching official package before generating images.

The copied manifests declare, among others:

| Area | Declared interface |
| --- | --- |
| Camera | AIDL `android.hardware.camera.provider`, v3, `ICameraProvider/vendor_qti/0` |
| Xiaomi camera | `vendor.xiaomi.hardware.camera.mivimessage`, `quickcamera`, `camera.synthetic`, and ODM `vendor.xiaomi.sensor.camera` |
| Fingerprint | AIDL `android.hardware.biometrics.fingerprint`, v4, plus QTI/Xiaomi extension interfaces |
| IMS | AIDL `vendor.qti.hardware.radio.ims`, v20, with `imsradio0` and `imsradio1` |
| Display | Xiaomi `displayfeature_aidl` v2, QTI display services and Xiaomi HWC extension v2 |
| Audio | AIDL audio core/effect v3 and Xiaomi SeaAudio |
| Power / thermal | AIDL power v6, thermal v3, health v4, Xiaomi MiPowerHal |
| NFC / haptics | AIDL NFC v2 and vibrator v2 |

These are **static declarations**. They do not prove an interface is active,
used by every feature, portable, or compatible with the selected Evolution X
framework. Preserve the vendor/ODM boundary, framework requirements, matching
native libraries and SELinux service labels during bring-up. See the
[feature matrix](native-features.md) for the validation work.

## Consequences for setup

Evolution X Android 16 `bka` is a reasonable starting branch because the phone
currently runs Android 16. It is not a proven ABI match. The modified system's
global-looking model and US software region must not override the China hardware
and `WPACNXM` vendor baseline. Keep the current xiaomi.eu application snapshot
separate from the matching official China firmware used for vendor extraction.

Still required: verified complete device/common/vendor/kernel integration,
matching stock firmware and extraction rules, a supported Linux x86-64 build
host, and an explicitly authorized recovery/backup/testing plan before any
physical ROM experiment. No Evolution X hardware feature has been tested yet.
