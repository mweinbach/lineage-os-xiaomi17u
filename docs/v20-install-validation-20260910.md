# V20 install validation — 8K / 4K120 / long 4K60 recording fixed, September 10, 2026

**V20 (`nezha.d5894f355e27f7d2f503f519`, source revision 19) is installed on
slot A. It is v17 plus a three-part fix to `MPEG4Writer` so the Xiaomi recorder's
8K, 4K120 and long/sustained 4K60 modes now write a decodable HEVC track. Before
this, 8K wrote a non-decodable track and 4K120 and long 4K60 crashed the recorder
(a FORTIFY write overflow, SIGABRT, no file).** The device keeps its real
identity and the always-on Leica Essential selection. You asked to make these
modes work ("ok do 8K/120fps/long-4K60 video now"); the approval was bound to
bundle manifest `1f0c5e0c974b103a74bf1ce66a92544ac4cb996e575cde2299919c41fbd53769`
before any phone write. The eight-image shared-Super slot-A write acknowledged
every payload rehashed identical, with no wipe and no slot change; userdata was
retained. The structured record is the
[install validation JSON](../research/v20-install-validation-20260910.json).

## The cause and the fix

The Xiaomi recorder enables `vendor.qti-ext-enc-nal-length-bs`, so the vendor
HEVC encoder emits **length-prefixed** NAL units (a 4-byte length before each NAL)
and length-prefixed codec-specific data, instead of Annex-B start codes. This
Evolution `frameworks/av` has no length-prefixed handling, so `MPEG4Writer`
misparsed the vendor output in three separate ways, fixed by three guarded
patches under `patches/evolution/`:

1. **`nezha-hevc-length-prefixed-nal.patch`** — the sample path scanned for
   `00 00 00 01` start codes; a NAL length in 256–511 is `00 00 01 xx`, which it
   read as a start code, underflowing a NAL size to `(size_t)-1` and aborting the
   writer with `FORTIFY: write: count 18446744073709551615`. The fix converts a
   validated length-prefixed access unit to Annex-B before that path.
2. **`nezha-hevc-recorder-csd-duplicate.patch`** — the encoder's output format
   already carried the codec config, then the encoder sent it again as a
   codec-config buffer before the first frame; the writer re-parsed it and failed
   with "Already have codec specific data", marking the track malformed and
   dropping its sample table. The fix lets a pre-frame codec-config buffer replace
   the format config instead of erroring.
3. **`nezha-hevc-recorder-csd-annexb.patch`** — the codec-specific data was
   length-prefixed too, so it was stored verbatim as a malformed `hvcC`. The fix
   converts it to Annex-B before building the `hvcC`, so the decoder config
   matches the length-prefixed samples.

## Measured on device

Recorded through the Xiaomi app on the installed v20, each clip pulled and
decoded off-device with ffprobe/ffmpeg:

| Mode | Before | After (v20) |
| --- | --- | --- |
| 8K30 | non-decodable track | HEVC 7680×4320, 362 frames, decodes, 0 gaps > 100 ms |
| 4K120 | FORTIFY crash, no file | HEVC 3840×2160, 1786 frames at 120.2 fps, 0 gaps > 100 ms |
| 4K60, 45 s | crash ~3 s in, no file | HEVC 3840×2160, 1337 frames over 44.5 s, live AAC audio |

No FORTIFY crash, track error or codec-config error in any case. The device
booted `nezha.d5894f355e27f7d2f503f519` in 25.5 seconds, SELinux Enforcing, with
root ADB; no fatal crashes.

## What this does not prove

Sustained thermal behavior at 8K and 4K120, and the exact encoder frame rate for
the 8K and 4K60 modes: the 8K clip decodes at about 25 fps and 4K60 at about
30 fps in the container (the Xiaomi mode timing and low-light auto frame rate in
a dark room), while 4K120 decodes at a true 120 fps. Rendered image quality still
needs a lit scene. Media and logs stay under the ignored evidence directory.
