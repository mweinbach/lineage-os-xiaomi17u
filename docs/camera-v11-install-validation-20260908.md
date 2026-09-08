# Camera v11 installation and validation, 2026-09-08

**V11r1 (`nezha.130611bac9232625e0066968`) is installed and booted on slot A
with normal Android SELinux Enforcing. Xiaomi Camera now saves valid 200 MP
Ultra HDR photos, telephoto 50 MP photos and Pro RAW.** Ultra RAW still fails
at its final framework save call, and audio policy initialization blocks video.
Full camera acceptance remains incomplete.

The [package checkpoint](camera-v11-package-20260908.md) records the preceding
host build and signing phase. Its uninstalled state is historical. The user
subsequently approved this exact bundle, its reboot, camera tests and root
diagnostics. All eight writes were acknowledged; no wipe or slot change was
performed. Normal boot completed in 25.3 seconds. The installed `cameraserver`
bytes match the verified 4,026,968-byte component, SHA256
`5dd3bc8a8105877dbff507afaf9d2a420cce53a1f3a9397f2b869aadd603c938`.

## Captures and independent decodes

| Path | Saved output | Observed result |
| --- | --- | --- |
| Xiaomi rear Photo | 3072 × 4096 JPEG/R | Full JPEG and Ultra HDR decode pass |
| Xiaomi front Photo | 3072 × 4096 JPEG/R | Full JPEG and Ultra HDR decode pass |
| Xiaomi main 50 MP | 6144 × 8192 JPEG/R | Full JPEG and Ultra HDR decode pass |
| Xiaomi telephoto 50 MP | 6144 × 8160 JPEG/R | Full JPEG and Ultra HDR decode pass; v10 output was truncated |
| Xiaomi Pro telephoto 200 MP | 16320 × 12288 JPEG/R, 19,758,173 bytes | Full JPEG and Ultra HDR decode pass; v10 output was truncated |
| Xiaomi Pro RAW | 4080 × 3072 DNG plus companion JPEG | LibRaw fully decodes the DNG to RGB; orientation produces 3072 × 4080 TIFF |
| Physical wide / ultrawide / telephoto RAW | 4096 × 3072 / 4096 × 3072 / 4080 × 3072 DNG | All three fully decode to RGB |
| Aperture rear and front effects | Ten 3072 × 4096 JPEG/R files | All five modes save valid JPEGs on each side; nine Ultra HDR decodes pass, front HDR metadata is rejected |

The Aperture sequence switches all five effects on both cameras without
restarting the app. Its PID and process start time remain the same across
both sequences. Capture crash buffers and camera-provider, cameraserver and
system-server process identities remain unchanged in all ten cases. The
Xiaomi Photo and Pro RAW cases also retain their capture process identities.
These checks establish output validity and mode switching; the static, mostly
dark scene does not establish useful effect quality, focus, stabilization or
sensor-native resolving power.

The 200 MP file SHA256 is
`2b82fd862fd596b187e210897404aa64f5815f888ab9f6f84d90ab29e0bbd93c`.
The first host Ultra HDR decoder rejected its dimensions because that binary
limits either dimension to 8192. An isolated build of the same unmodified
libultrahdr 1.4.0 source, commit
`d52a0d13814ca399fc8a07e23de1d2c63f0e8404`, with
`UHDR_MAX_DIMENSION=16384` fully decoded the same file to 1,604,321,280 bytes
of RGBA F16 HDR data. The initial failure is retained as a decoder limit;
it is not a malformed-camera-output result. The existing host decoder was
not replaced.

The Pro RAW DNG is 25,097,580 bytes, SHA256
`4033e38c42692cebdfe8b9f1049bed38660d08c681036d2a400673eb5090a96a`.
The initial post-decode size assertion omitted LibRaw's orientation handling.
The retained decoder output and identify report establish the correct rotated
dimensions; the corrected verification does not require another capture.

## Remaining failures

Front HDR saves a complete JPEG, but libultrahdr rejects its gain-map metadata
because HDR capacity minimum and maximum are both 1.0. Nine other effect files
fully decode as Ultra HDR. This is a neutral-gainmap interoperability failure,
not a JPEG truncation or app restart. [Android's Gainmap setter](https://developer.android.com/reference/android/graphics/Gainmap#setDisplayRatioForFullHdr(float))
permits 1.0; that API contract alone does not establish cross-decoder compatibility.
The retained file needs a measured metadata-path repair before all ten Ultra
HDR cases can be admitted.

Ultra RAW delivers 76,368,352 bytes of lossless data to Xiaomi Camera and saves
its companion JPEG, but leaves an empty DNG. Its save code reflects
`DngCreator.writeLossLessJpeg(OutputStream, ByteBuffer)`, which is absent from
the current framework. The preceding embedded-JPEG method,
`writeJpeg(int, int, ByteBuffer)`, is also absent. The empty file remains empty through the bounded
follow-up. Unlike v10, this attempt does not restart the provider, camera app,
cameraserver or system server. Factory framework inspection confirms the Java
method, JNI signature and compressed-DNG metadata path. A correct container
writer still needs implementation and device validation.

Audio diagnostics started at the approved boot and completed before root ADB
was enabled. Audio HAL services register, but policy initialization rejects
an AIDL output flag while loading the module, then rejects an audio usage while
loading engine strategies. Later snapshots have a null policy manager.
The live module exposes `VIRTUAL_DEEP_BUFFER` at AIDL flag bit 19; the factory
converter maps it to legacy bit 30 (`0x40000000`). The factory framework and
native converter identify `BLUETOOTH_SCO` usage as 19. Live ODM and vendor
configuration files match the retained factory files. These measured conversion
gaps guide the next repair; no audio repair is installed, and video was not
retried against the known null policy manager.

A separate Wallpaper and style crash dialog appeared during UI inspection.
It disappeared before a guarded dismissal could run, so no dismissal tap was
sent. Full phone health is not claimed.

## Data, cleanup and evidence

Before the first camera launch, all 512 Xiaomi Camera CE members and five DE
members retain their bytes and metadata. The active Camera APK and platform
signer also match the predecessor. This is a Camera-app comparison and does
not verify all userdata.

Cleanup restores Xiaomi rear Photo at 1x and 12.5 MP, with Pro format JPEG,
and Aperture rear with no effect, Ultra HDR enabled and RAW disabled. The
three camera test apps are stopped. USB stay-awake remains its original value
of zero. Final checks reconfirm the installed build, slot A and Enforcing policy.

The [structured runtime record](../research/camera-v11-install-validation-20260908.json)
binds installation, authorization, app data, each capture, independent decoders,
process checks, startup diagnostics and cleanup. Raw logs, images, app data and
proprietary analysis remain in ignored local evidence. The predecessor bundles
and their historical records are preserved. A future bundle requires a fresh,
specific flash/reboot approval.

The completed runtime record passes all 61 evidence-pin checks. `make test-current`
passes 939 tests in 27.858 seconds; `make test` passes 4,885 tests in
192.417 seconds plus shell checks. The earlier run found the document
link before this record existed; the completed-record rerun passes.
