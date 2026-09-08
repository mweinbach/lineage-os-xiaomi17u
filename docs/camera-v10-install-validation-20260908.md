# V10 installation and camera validation

V10 (`nezha.0c10ad024d3033691a2825cc`) is installed on slot A and booted
with SELinux Enforcing. **Ordinary Xiaomi Camera photos now save, and Aperture
can switch through all five effects on both cameras in one running process.**
Telephoto high resolution, Xiaomi RAW/Ultra RAW and video still fail.

The [machine-readable record](../research/camera-v10-install-validation-20260908.json)
pins the ignored device receipts, captures, independent decodes and failure logs.
The [package record](camera-v10-package-20260908.md) preserves the preceding
build, signing and bundle checks; its original approval-pending state describes
the checkpoint before this installation.

## Installation and retained app data

The user explicitly approved the verified v10 bundle, reboot, camera tests and
root diagnostics without wiping or changing slots. Shared Super and the seven
slot-A companion writes were acknowledged; the manifest remained
`739acc4ffad8d5eaf3828af4ead90d9387bc646251f5f9f3a74468877ca886f9`.
Android completed boot in 25.5 seconds. The installed source has 659 recorded
rows. The original v9, v8 and v7 bundles remain preserved.

Before the first Camera launch, all 508 credential-encrypted and five
device-encrypted Xiaomi Camera data members retained their bytes, ownership,
mode and modification time. Its active APK and platform signer were unchanged.
This comparison covers Camera's app data, not all personal userdata.
The original CameraOpt verifier returns true during successful captures.

## Measured results

| Test | Observed result |
| --- | --- |
| Xiaomi Photo, rear 1×, rear 0.6×, rear 3.2× UI selection, and front | Four saved 3072×4096 JPEGs; full JPEG and Ultra HDR decodes pass |
| Xiaomi Photo, rear 1× at 50 MP | Saved 6144×8192 JPEG; full JPEG and Ultra HDR decodes pass |
| Aperture Bokeh, HDR, Night, Face Retouch and Auto, rear and front | All ten saved 3072×4096 JPEGs and fully decoded Ultra HDR; same Aperture process throughout |
| Aperture effect transitions | Rear and front None → Bokeh and the subsequent Bokeh → HDR → Night → Face Retouch → Auto transitions pass without a cold restart |
| Physical RAW through the retained capture probe | Wide and ultrawide DNGs decode at 4096×3072; telephoto DNG decodes at 4080×3072; matching physical capture results retained |
| Xiaomi Photo, telephoto 50 MP | Saved malformed JPEG; both JPEG and Ultra HDR decoders fail |
| Xiaomi Pro, telephoto 200 MP | Factory UI exposes 200 MP; saved file has a 16320×12288 header but is truncated and fails full decode |
| Xiaomi Pro RAW, telephoto | No saved image; mock camera 7 rejects the RAW16 output dimensions before HAL configuration |
| Xiaomi Pro Ultra RAW, telephoto | No saved image; provider crashes in the vendor lossless-JPEG/DNG encoding path and restarts automatically |
| Xiaomi default video | 1080p30 Dolby Vision recording fails to initialize AudioRecord; only an empty pending MP4 is created |

All ten Aperture captures retained the same app process and stable service
identities during each capture; their crash buffers were unchanged. The whole
session was not crash-free: the Xiaomi Ultra RAW test restarted the provider.
An earlier Photo test also saw an unrelated wallpaper plugin crash entry.

The scene was dark and static. These results establish saved and decodable
outputs, not useful effect quality, focus, stabilization or sensor-native
resolution. The normal Photo 3.2× UI selection does not by itself establish
physical telephoto selection. A 200 MP header in a truncated file is a failure,
not an admitted 200 MP capture.

## Remaining failures and next repair

The telephoto 50 MP JPEG/R assembler needed 2,824,513 + 5,181,335 bytes in a
4,388,802-byte buffer. The 200 MP attempt needed 2,228,035 + 15,555,619 bytes
in the same buffer size. A later read of the first file was byte-identical,
excluding an early read during saving as the cause.

The retained stock camera service has three sizing decisions absent from the
current port: `isMockCamera`, `getCustomBestSize` and
`raiseDimensionsforCustomImageQuality`. Its mock-camera path retains requested
dimensions; its JPEG sizing path also permits size-based extrapolation. The
current service rounds mock-camera outputs using the public size table and
can clamp the JPEG buffer. The stock library exports and Qcom vtable entries
for these methods are verified in the retained binary analysis. These findings
support a focused source repair; no such repair is installed in v10.

The vendor client-list property currently contains only Snapcam. That is an
additional observation, not a complete fix for the missing factory hooks.
No runtime property override was performed.

The video error is separate. Audio HAL services are registered, but the audio
policy manager is null and AudioFlinger has no hardware threads. The retained
log records AudioRecord creation failing with `-19`. The original audio startup
log is no longer present; collect it from boot during the next approved install
before deciding on an audio source change.

Camera settings were returned to rear Photo at 1× and 12.5 MP, with Pro output
back to JPEG. Aperture was returned to rear, None, Ultra HDR enabled and RAW
disabled. The camera apps and capture probe were stopped. USB stay-awake was
not changed. Cleanup and final build/slot/policy observations are pinned in the
machine-readable record.

The previous full offline suite passed 4,881 tests plus shell checks, and
`make test-current` passed 939 tests for the installed source and delivery
contracts. The device measurements above are additional evidence, not an
extension of those offline test counts. Future source repairs need their own
tests, build and separately approved device validation.
