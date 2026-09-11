# V21 install validation — the Now Playing gate is open, the Qualcomm DSP refuses Google's model, September 11, 2026

**V21 (`nezha.34aee22f376f606d9ed52909`, source revision 20) is installed on
slot A. It is v20 plus the two hash-admitted Pixel `music_detector` files in
`/product/etc/firmware`, which is the condition Android System Intelligence
checks before it lets you enable Now Playing.** That condition is now satisfied
on the device: the switch that was greyed out is enabled, it turns on, and the
setting reads `1`. **What does not work is the layer below it. The Qualcomm
sound-trigger HAL refuses to load Google's music model, and each refusal
rebooted the audio HAL, so the setting is turned back off on the installed
build.** You asked to get Now Playing working ("ok get it working! you may need
to do some more work on this but that's ok"); the approval was bound to bundle
manifest `13d9a34da39f4321a0bebe43b521730bc431f6bbeeffc42068b784e6c9fdb5fd`
before any phone write. The eight-image shared-Super slot-A write acknowledged
every payload rehashed identical, with no wipe and no slot change; userdata was
retained. The structured record is the
[install validation JSON](../research/v21-install-validation-20260911.json).

## What the set changes

One thing: `device/xiaomi/nezha/now-playing-dsp-model.mk` copies
`music_detector.sound_model` (34432 bytes, SHA256 `5472e735…`) and
`music_detector.descriptor` (1057 bytes, SHA256 `dadf2cbd…`) into
`/product/etc/firmware/`, admitted by hash against
[`config/nezha-now-playing-dsp-model.json`](../config/nezha-now-playing-dsp-model.json).
Both files read back from the installed image at exactly those hashes. Nothing
else moved: Leica Essential still reads from `build.prop` after a clean reboot,
the camcorder profile selection and the CameraOpt methods are unchanged, and the
recorder fix from v20 is carried forward. See
[the model page](now-playing-dsp-model-20260911.md) for where the files come from.

## Measured on device

| Check | Result |
| --- | --- |
| Boot | `nezha.34aee22f376f606d9ed52909`, 25.4 s to boot completed, Enforcing, root ADB, 0 fatal crashes |
| Model files | both present, both SHA256-identical to the contract pins |
| ASI switch | **enabled** (it was disabled on v20) and it turns on; `now_playing_enabled` reads `1` |
| DSP load | **fails**: `LOAD_MODEL ("9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15") -> ServiceSpecificException: INTERNAL_ERROR (code 5)`, then `startRecognition failed, error=-2147483648` |
| Side effect | `SoundTriggerHalEnforcer: Exception caught from HAL, rebooting HAL` → `AudioService.onAudioServerDied`, repeating on ASI's 5 s retry |
| Loaded models for ASI | none |

So the file gate this set was built to open is open, and the next gate down is
shut.

## Why the DSP refuses it

The vendor log says it plainly. The Qualcomm HAL hands the model to PAL, which
looks the vendor UUID up in the device's sound-model platform information:

```
STHAL: SoundTriggerSession: loadSoundModel_l: Enter handle 0, model SoundModel{type: GENERIC,
    uuid: 9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15, vendorUuid: 9f6ad62a-…, dataSize: 34432}
PAL: StreamSoundTrigger: ProcessEvent: 2158: Input vendor uuid : 9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15
PAL: StreamSoundTrigger: ProcessEvent: 2163: Failed to get sound model platform info
```

The resource-manager XML on this unit
(`/vendor/etc/audio/sku_canoe/resourcemanager_canoe_*.xml`) declares QC Voice UI
(`68ab2d40…`), the Google hotword engine (`7038ddc8…`), QC Acoustic Context
Detection (`4e93281b…`), sensor PCM and MMA. There is no Google Music Detection
entry. On the Snapdragon Pixels this model comes from, the platform file carries
one explicitly:

```xml
<!-- Google Music Detection -->
<sound_model_config>
    <param vendor_uuid="9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15" />
    <param execution_type="ADSP" />
    <param library="none" />
```

`library="none"` with `execution_type="ADSP"` means the model is executed by a
Google module compiled into the Pixel ADSP image. **That is firmware, not
configuration.** Adding a stream config for the UUID would route the model to a
module this SoC's DSP image does not contain. This is the honest end of the
"just ship the model files" approach: the files were necessary and they are not
sufficient.

The second result is the one that mattered on the day: the framework treats a
HAL load failure as a HAL fault and reboots it, which takes `audioserver` and
the QTI audio HAL down with it. ASI retries every five seconds, so the audio
stack was restarting every five seconds while the setting was on. Now Playing
was turned back off through ASI's own switch after the measurement, after which
the audio HAL was stable and no further load attempts were logged. No flash,
wipe, reboot or slot change was involved in that; it is a user setting.

## What comes next

The device does have real on-DSP music detection of its own: Qualcomm's Acoustic
Context Detection ships `music.eai` in `/vendor/etc/models/acd/` with the context
`AMBIENCE_MUSIC` (`0x08001336`), reachable through the `4e93281b…` stream config
that the platform file does declare. The follow-up work is a sound-trigger
middleware shim that claims the Google music UUIDs and backs them either with
that Qualcomm context detector or with a timer, and that refuses the model
harmlessly by default so the audio HAL is never rebooted over it. See
[the music-trigger page](now-playing-trigger-20260911.md).

## What this page does not prove

That Now Playing can identify a song on this phone. It proves the file gate is
satisfied, the app-level switch is enabled, and the DSP-level cause of the
failure. Recognition, the music database download and power behaviour are all
untested. Logs and dumps stay under the ignored evidence directory.
