# Feature-successor installation and first device results — September 5, 2026

The user authorized installation of the previously qualified Package7 feature
successor. The eight-image bundle was installed to the existing A route without
a wipe or slot change. Android booted with the retained user data, and build
`nezha.a6d3109ae93158c498bb30b0` is now the installed development baseline.
The original Package7 bundle, working76 recovery and stock return inputs remain
preserved as rollback and rescue material.

This is a point-in-time installation and first-test record. The captured
evidence is under
`evidence/feature-successor-install-20260905-v1/`. Later builds or device tests
need their own records.

## Installed artifact set

The selected private bundle is
`artifacts/flash/nezha/package7-feature-fixes-20260905-v1/`. Its manifest SHA256
is `8550182663180841592a47cc0a33efa5bb7a76f5d70a197faa4d662f47040c1f`.
The source build identity and exact payloads are:

| Target | Bytes | SHA256 |
| --- | ---: | --- |
| `super` | 9,446,512,740 | `ba18cecb36f53ca9eee6d524ce94534e7c3d1ae52b36b5540a3c8d3ea23bd6da` |
| `dtbo_a` | 33,554,432 | `d70a4da0958c09d84201132efeff778417de8e568d2b2ed9cdcf13c42f916f1d` |
| `init_boot_a` | 8,388,608 | `e167b96d1db18149a5574060e48ac849dfc770856810b3f0309ae41f9ddf045b` |
| `vendor_boot_a` | 100,663,296 | `0c4a164598c8af9b667a1dd8d47c9f2aaa5d1f568aada39179d2537ce71e3006` |
| `recovery_a` | 104,857,600 | `a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e` |
| `boot_a` | 100,663,296 | `cbd6b6b2fee214e9d2f97fd0bd38f1539c8971cef15d620bdef8ed2c2dd7cfb3` |
| `vbmeta_system_a` | 65,536 | `2d40424b8c8c2b48f2c2a5c7c4518d7ffb53b729d55fc66b7cf67924a12dee30` |
| `vbmeta_a` | 65,536 | `71b83481e64f43ed7616db086a9e9418afa4cd67c65db21dd655a00734a459aa` |

The reconciled target-files ZIP remains SHA256
`26ae30eddfd3716212b08f4c77b9d6674db26c64c8d798e0038208f24331bc9a`
(11,100,598,089 bytes). The complete pre-install signing and qualification
scope is in the [successor record](package7-feature-successor-20260905.md).

## Installation result

The preflight selected the physical Xiaomi `nezha` / `canoe` device, an
unlocked bootloader, slot A, no snapshot update, and exact partition capacities.
The operation retained the selected slot, did not format user data, did not
disable AVB verification or verity, and did not relock the bootloader.

Fastboot returned exit 0 after writing sparse `super`. The first wrapper then
stopped because its raw `os.stat_result` comparison reported changed input
metadata. That comparison includes read-sensitive access time, but the wrapper
did not serialize the before fields, so the exact changed field cannot now be
proved. The record does not claim that access time was the observed cause.
Fresh content verification reproduced the original Super SHA256 and size after
the acknowledged write. The continuation therefore wrote the remaining seven
companions and did not send Super a second time. All seven fastboot writes were
acknowledged, their source bytes were rehashed, and their serialized before and
after identity fields matched. The initial guard failure remains preserved in
`execution.json`; the bounded continuation is in `continuation.json` and the
consolidated result is in `installation.json`.

After the authorized reboot, the first observation already had
`sys.boot_completed=1`, Zygote and SurfaceFlinger running, boot animation
stopped, and incremental build `nezha.a6d3109ae93158c498bb30b0`. A later check
recorded PID 3389 for `system_server`. Normal Android reported SELinux
`Enforcing`. Existing encrypted user data was retained; no wipe was performed.

## First feature results

- At 21:23 local time on September 5, 2026, the user confirmed fingerprint
  enrollment works. The captured framework state reports sensor 5 with one
  enrolled print, successful authentications and no HAL deaths since boot.
- The current lockscreen screenshot shows a malformed on-screen fingerprint
  icon. The installed SystemUI falls back to `pixel_pitch=-1`; that value drives
  roughly 3,074 px of internal padding inside a 148 px icon. The device reports
  419.25723 dpi, which derives a 60.58 micrometre physical pixel pitch for the
  source correction. That correction is separate work and is not present in
  this installed build, so fingerprint enrollment success does not close the
  UDFPS rendering issue.
- Aperture still fails with `IllegalStateException: Camera configuration is
  null`. The captured click path exposes a separate initialization race between
  the mode selector and its nullable configuration state. A later Aperture
  process constructs Camera0 use cases and reaches CameraService, but no
  successful open, preview or capture is established.
- Xiaomi Camera still fails through the vendor-provider stream configuration
  path. The fully captured abort records
  `get InternalStreamConfigInfo failed` for operation mode `0x9005` and role 64.
  Similar provider aborts exist in the Aperture-era crash buffer, but their
  timing does not cause the earlier Kotlin exception and the evidence does not
  map `0x9005` to an exact Aperture mode or stream. Neither camera has a
  successful preview or capture result.

Fingerprint enrollment is the first confirmed hardware improvement from this
successor. Boot completion and enforcing SELinux are also confirmed on the
installed bytes. Camera remains unresolved, the diagnosed UDFPS source
correction still needs build and installation, and the other fingerprint lifecycle, status-bar, camera lens,
photo/video, charging, telephony and OTA checks remain separate device work.

## Operational lesson

Input guards around a mutating command must serialize every compared field
before execution. If reads may update access time, compare the stable identity
cohort that proves immutability and rehash content after the command. When a
guard fails after a device write, preserve the failure, establish what the
device tool acknowledged, and reverify the exact source bytes before deciding
whether to continue. Do not repeat a large shared-partition write merely to make
a wrapper record look successful.
