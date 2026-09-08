# Compressed Bayer DNG and audio descriptor compatibility — 2026-09-08

The installed [v12 validation](camera-v12-install-validation-20260908.md) identifies
two remaining compatibility failures: Xiaomi UltraRAW supplies compressed Bayer
format 32, and audio initialization rejects the factory multiroute descriptor.
This source candidate adds that Bayer container path and the measured audio
mappings. It has not been installed or validated on the phone.

## Compressed Bayer DNG

The v12 writer-entry capture contains 604 bytes of metadata with header
`[32, 4080, 3072, 13915666, 1, 8, 8]`. Its 64 tile counts sum to exactly
13,915,666 bytes. The captured JPEG header is SOF3, precision 16, dimensions
255 × 384 and two components. Each JPEG pixel carries a pair of Bayer samples,
so each DNG tile spans 510 × 384 sensor pixels. The factory runtime separately
selects its linear RGB handling for format 15.

The [DNG contract](../config/nezha-compressed-dng.json) and
[patch 0036](../patches/evolution/0036-nezha-compressed-dng.patch) now distinguish
compressed storage from linear RGB metadata. Format 32 uses one TIFF sample per
pixel, CFA photometric interpretation and the existing sensor color, black-level,
noise and opcode setup. Format 15 preserves its three-channel LinearRaw path.
Ordinary uncompressed DNG calls retain their existing setup. Unknown formats,
incorrect component counts, mismatched dimensions and invalid byte counts fail
before serialization.

The actual TIFF tag, offset and serialization block runs with AOSP `TiffWriter`
in an isolated directory in the Linux build guest. Twelve synthetic files fully
decode through LibRaw: Bayer and RGB at 128 × 128, plus Bayer at the measured
4080 × 3072 dimensions, each with strip/tile storage and with/without a JPEG
preview. The checks compare every embedded JPEG segment, preview bytes, TIFF
metadata and all decoded pixel values. This includes the measured 510-pixel tile
width. Host parser tests pass 1,228 assertions with address and undefined-behavior
sanitizers; the unchanged gainmap helper passes 685 assertions. JNI compilation
passes with the selector enabled and disabled.

These fixtures use synthetic camera metadata. Their decoding proves the new
container structure, not the phone's complete capture path. A successor build and
an actual UltraRAW capture remain necessary.

## Audio descriptors and validation

The retained factory converter maps `OUT_DEVICE` with connection `multiroute` to
`0x20000004`, and `DEFAULT` format with encoding `audio/vnd.mi.mihc` to
`0x40000000`. Multiroute is distinct from the existing proxy device value.
The [conversion contract](../config/nezha-audio-vendor-enums.json) and
[patch 0035](../patches/evolution/0035-nezha-audio-vendor-enums.patch) add these
bidirectional mappings under the existing Nezha selector. They preserve the
previously implemented output flag and usage extensions.

The [legacy header contract](../config/nezha-audio-device-format.json) and
[patch 0038](../patches/evolution/0038-nezha-audio-device-format.patch) add names for
those values. Multiroute enters the sorted array used by output-device validation;
it does not enter the Bluetooth LE device arrays. Format validation accepts the
exact MIHC value and rejects undefined MIHC subformats. The shared headers expose
the names and validators; the AIDL conversion entries remain product-selected.

The complete conversion source compiles and runs with the actual generated NDK
types against all 31 device descriptions, 33 formats, 18 flag combinations and 18 directional channel layouts
from the primary module's 54 advertised ports. The selector-disabled case passes
309 checks, including rejection of the vendor additions; the enabled case passes
314 checks. Both cover round trips, legacy validation, sorted output devices,
unknown-value rejection and the distinction between multiroute and Bluetooth LE.

The system/media input is Evolution X `bka` commit
`f49b447fd0f00152ecffbb9446403def0708a592`, matching the upstream branch checked on
2026-09-08. Existing source selections and the v12 output are preserved.
Audio policy initialization, physical audio input/output and video recording
remain unverified for this candidate.

The full offline suite passes 4,892 tests in 199.570 seconds plus shell checks.
`make test-current` passes 939 tests in 29.284 seconds. These are workspace checks;
they do not substitute for a ROM build or phone validation.

## Source adoption

The source change is committed as `3f9f9e8` and applied as revision 10,
`nezha.2c510f47f6d99b93f0c3ee11`. The guarded transaction changes eight files,
retains 663 predecessor rows byte-for-byte and adds three existing legacy header
preimages to the inventory, for 671 recorded rows. The
[source evidence record](../research/camera-bayer-audio-compat-20260908.json)
pins the transaction and host checks. Component/full build and delivery are
pending.

## Evidence and delivery boundary

Private inputs and generated checks remain under
`reports/camera-completion-20260907/v13-{investigation,dng,audio}/`.
The source contracts pin the relevant evidence. The installed v12 record remains
the authority for phone behavior. This work does not authorize a new flash,
reboot, wipe or slot change.
