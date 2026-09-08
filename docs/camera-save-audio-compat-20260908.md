# Camera save and audio compatibility candidate, 2026-09-08

The successor source candidate addresses three failures measured on
[v11r1](camera-v11-install-validation-20260908.md): the missing Xiaomi Ultra RAW
save methods, a neutral gain map that fails independent HDR decoding, and two
rejected audio enum conversions during startup. **The phone still runs v11r1;
this candidate has not been installed or validated on the phone.**

## Compressed DNG save

The [DNG source contract](../config/nezha-compressed-dng.json) and
[framework patch](../patches/evolution/0036-nezha-compressed-dng.patch) add the
hidden `DngCreator.writeJpeg(int, int, ByteBuffer)` and
`writeLossLessJpeg(OutputStream, ByteBuffer)` methods used by the factory camera.
The implementation is enabled by the existing Nezha camera-session selection.
Other products reject the new operation, and ordinary RAW entry points retain
their existing defaults.

The retained factory runtime and `libcameradngimpl.so` establish the vendor
metadata layout: a 604-byte `com.xiaomi.dng.compressedParameters` value, RGB
format 15, 16-bit samples, and either one lossless JPEG strip or an 8-by-8 tile
grid. The candidate checks metadata type and size, dimensions, buffer capacity,
tile byte counts, SOF3 frame dimensions and complete JPEG boundaries before it
writes. Unknown formats and layouts produce explicit exceptions.

The writer uses AOSP's TIFF serializer and camera metadata path. It adds tile
tag definitions to this writer alone, computes offsets after all metadata and
preview entries exist, and preserves encoded image and preview bytes. RGB output
uses LinearRaw tags and omits Bayer-specific correction opcodes. Preview state
belongs to each `DngCreator` instance. Dynamic white level and the factory RGB
black-level convention are preserved for the compressed path.

Measured host checks:

- The full JNI candidate compiled with the Android toolchain in both disabled
  and enabled configurations. The final component build remains a separate gate.
- The portable parser passed 1,065 assertions with address and undefined-behavior
  sanitizers, including truncated buffers, bad sizes, unsupported formats and
  tile-count inconsistencies.
- The actual production tag, offset and serialization block ran against AOSP
  `libimg_utils` in the Linux build guest. Four synthetic 128-by-128 DNGs cover
  a single JPEG strip and 64 JPEG tiles, each with and without a preview and with
  a GPS metadata sub-IFD. LibRaw fully decoded all four. The encoded lossless
  segments and preview bytes match their inputs exactly, and decoded pixels are
  constant across tile boundaries.

The native fixture supplies synthetic camera metadata and output plumbing.
It does not establish that the camera's compressed buffer uses the admitted
SOF layout or that JNI metadata setup succeeds on the phone. Those are explicit
successor runtime checks. Private evidence is in
`reports/camera-completion-20260907/v12-dng/`.

## Neutral gain map

The [Aperture contract](../config/aperture-neutral-gainmap.json) and
[save patch](../patches/evolution/0037-aperture-neutral-gainmap.patch) address the
front HDR capture whose gain and capacity endpoints are all neutral. The saved
file includes both XMP and ISO 21496-1 metadata. Google libultrahdr 1.4.0 rejects
the equal capacity minimum and maximum, even though its ordinary JPEG decodes.
Android's gain-map API permits display ratios of 1; decoder interoperability
therefore needs explicit handling. [Android Gainmap API](https://developer.android.com/reference/android/graphics/Gainmap)

Aperture recognizes the measured neutral metadata on Nezha and changes the
full-HDR display capacity from 1 to 2 in both representations before notifying
listeners that the capture is saved. Both content-gain endpoints remain 1,
with zero offsets and gamma 1, so the operation adds no luminance boost. It
changes two bytes in the retained failing capture and preserves its file size,
JPEG payload, compressed gain map, EXIF and MPF offsets. Other metadata values
are left untouched. The same check handles the single-capture memory stream;
file work runs off the main thread.

The retained failing capture fully decodes to 100,663,296 bytes of RGBA F16 after
that repair. The nine previously valid effect captures are unchanged. The helper
passes 685 assertions using synthetic marker streams; a separate 35-assertion
run includes the ten real captures. Parser tests and full-image decoding are
separate evidence. Records are in
`reports/camera-completion-20260907/v12-hdr/`.

## Audio conversion

The [audio contract](../config/nezha-audio-vendor-enums.json) and
[conversion patch](../patches/evolution/0035-nezha-audio-vendor-enums.patch) admit
the two values measured in the retained Xiaomi audio configuration and factory
converter:

| Meaning | AIDL value | Legacy value |
| --- | --- | --- |
| Virtual deep-buffer output flag | Bit index 19 | `0x40000000` |
| Bluetooth SCO usage | 19 | 19 |

The Nezha product selects these conversions in the shared C++/NDK conversion
defaults. Existing named AOSP enum conversions retain their semantics, including
in-call music. Other unknown values continue to fail conversion.

A host harness compiled the six patched conversion functions and the actual
bitmask helper. It passed 1,099 assertions with the selection disabled and 1,657
with it enabled, using the undefined-behavior sanitizer. This proves conversion
behavior; it does not prove audio-policy initialization, playback, microphone
capture or video. Records are in
`reports/camera-completion-20260907/v12-audio/`.

## Reproduction and remaining gates

Run the portable save-helper checks without a phone or proprietary files:

```sh
python3 scripts/test_nezha_camera_save_compat.py --output reports/save-helper-check
```

A C++ compiler and JDK must be available; `--cxx`, `--javac` and `--java` can
select explicit installations. The ordinary offline suite checks the patch and
template bytes, inherited Aperture preimage and the measured factory ABI pins.
The focused seven-test contract suite passes. `make test-current` passed 939
tests in 27.607 seconds; `make test` passed 4,892 tests in 192.314 seconds plus
shell checks. The focused contract checks also passed after correcting the
build descriptor.

The installed source revision 8 is `nezha.efda11d09f81d7685c018d03`, with
668 source rows. Its receipt is
`reports/camera-completion-20260907/source-revision-8/source-installed.json`,
SHA256 `d4ff6f7e7726d7366bdbffdb92bab116e7101ceee106fcaf9668b64794101b4b`.
The initial component build rejected a duplicate Soong `defaults` property.
Revision 8 merges the new default into the existing list and preserves the
other 667 source rows. The failed revision 7, its log and the correction
preimage remain recorded. Revision 8 passed source, manifest, filesystem,
architecture, disk and one-writer preflight. The component/full ROM build and
signed bundle remain separate pending gates before the next phone installation.

The previous phone approval covered v11r1 only. A successor flash and reboot
require separate explicit authorization under [AGENTS.md](../AGENTS.md). The
next device validation must check Ultra RAW full decoding and its preview, the
neutral HDR case, audio-policy startup and video recording, then repeat the
working photo cases. Existing rollback bundles and the working recovery remain
preserved.
