# Now Playing music trigger — backing Google's model with the Qualcomm DSP, September 11, 2026

**Not device-admitted.** This page describes a reviewed source change and its
offline checks. Nothing here has run on the phone.

## The problem this solves

On the installed v21 the two Pixel `music_detector` files are in
`/product/etc/firmware` at their pinned hashes, so Android System Intelligence
enables its Now Playing switch. Turning it on then fails in the sound-trigger
HAL, and the failure is expensive:

```
LOAD_MODEL ("9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15") -> ServiceSpecificException: INTERNAL_ERROR (code 5)
SoundTriggerHalEnforcer: Exception caught from HAL, rebooting HAL
AS.AudioService: AudioService.onAudioServerDied
```

PAL refuses the model because the device's resource-manager XML has no
sound-model entry for that vendor UUID, and the Pixel entry it would need names
a Google ADSP module (`execution_type="ADSP"`, `library="none"`) that is part of
Pixel firmware rather than of any configuration file. The measurement and the
full vendor log are in the [v21 install record](v21-install-validation-20260911.md).

Because the framework reads a load failure as a HAL fault, ASI's five-second
retry loop restarted the whole audio stack every five seconds. Any fix has to
stop that first.

## The change

One new class and a one-line edit, both inside the sound-trigger middleware:
[`patches/evolution/nezha-now-playing-trigger.patch`](../patches/evolution/nezha-now-playing-trigger.patch),
contract [`config/nezha-now-playing-trigger.json`](../config/nezha-now-playing-trigger.json),
authored source `templates/now-playing-trigger/NezhaMusicTriggerHal.java`.

`SoundTriggerModule.attachToHal` builds its HAL chain as
`SoundTriggerHalEnforcer(SoundTriggerHalWatchdog(SoundTriggerDuplicateModelHandler(hal)))`.
The patch inserts `NezhaMusicTriggerHal.wrap(...)` around the innermost HAL, so
the shim sits **below** the enforcer. That placement is the point: an exception
the shim raises passes through `SoundTriggerHalEnforcer.handleException`, which
returns a `RecoverableException` to the caller instead of rebooting the HAL.

The shim claims three UUIDs — the music detector `9f6ad62a…`, its TFLite variant
`6ac81359…` and the music-break model `12caddb1…` — and passes every other model,
including the assistant hotword, straight through untouched. It adds no
permission, no SELinux rule, no vendor change and no new HAL.

## The three modes

`persist.sys.nezha.nowplaying.mode`, readable and settable on a running device:

| Mode | What it does |
| --- | --- |
| `off` (default) | Refuses the music model with a recoverable `OPERATION_NOT_SUPPORTED`. Now Playing still cannot run, but turning it on no longer reboots the audio HAL. |
| `acd` | Loads Qualcomm's own Acoustic Context Detection stream in place of the Google model and translates its context events into the `music` / `neg_music` events ASI expects. |
| `periodic` | Needs no vendor support: raises a `music` event on a timer while recognition is armed, so ASI runs its own on-device matcher. |

An unrecognized value falls back to `off`. Timings (`interval_s`,
`first_delay_s`, `retrigger_s`, `min_gap_s`, `debounce_ms`) and the ACD
`acd_threshold` / `acd_step` are properties too, so one build can test both live
modes without reflashing.

## Why Acoustic Context Detection is the right Qualcomm feature

The device already ships a music detector that runs on this DSP. The resource
manager declares a `QC_ACD` stream config for vendor UUID
`4e93281b-296e-4d73-9833-2710c3c7c1db`, and `/vendor/etc/models/acd/` holds
`music.eai` under `ACD_SOUND_MODEL_ID_MUSIC` with the context `AMBIENCE_MUSIC`
(`0x08001336`). The Qualcomm STHAL routes any model whose vendor UUID is that
one to `PAL_STREAM_ACD`, and `CoreUtils::isValidSoundModel` deliberately exempts
ACD streams from the "model data must be non-empty" rule, because for ACD the
contexts, not a model blob, select what is detected.

So in `acd` mode the shim loads a model with ASI's own UUID but the ACD vendor
UUID, and sends a recognition config carrying one context — AMBIENCE_MUSIC —
with a threshold and step size. The payload layout comes from the published PAL
sources (`SoundTriggerUtils.h`, `StreamACD.cpp`), all packed little-endian:

```
st_param_header          { key_id = 5 (CONTEXT_RECOGNITION_INFO), payload_size }
acd_recognition_cfg      { version, num_contexts }
acd_per_context_cfg[]    { context_id, threshold, step_size }
```

and events come back the same way with `key_id = 6`:

```
st_param_header              { key_id = 6 (CONTEXT_EVENT_INFO), payload_size }
acd_context_event            { version, detection_ts, num_contexts }
acd_per_context_event_info[] { context_id, event_type, confidence_score, detection_ts }
```

`event_type` is `STOPPED` / `STARTED` / `DETECTED`; the shim reports music on
`STARTED`, on `DETECTED` above the threshold, and silence on `STOPPED`, then
emits the ASCII `music` or `neg_music` payload ASI's `AmbientMusicDetector`
parses. `tests/test_now_playing_trigger.py` recomputes both payloads from the
constants in the Java source and compares them with the vectors pinned in the
contract, so a constant that drifts from the reviewed layout fails offline.

## Event bookkeeping

The middleware is strict about one thing: `recognitionStillActive` may only be
set when the status is `SUCCESS` or `FORCED`, or `SoundTriggerHalEnforcer` logs
a `wtf` and reboots the HAL. The shim therefore sets it only on the `FORCED`
event it synthesizes for `forceRecognitionEvent`, which is how ASI polls model
state when the screen turns on and which the Qualcomm HAL does not implement at
all (`SoundTriggerHw::forceRecognitionEvent` returns "unsupported API"). Ordinary
`SUCCESS` triggers leave recognition inactive, exactly as a real one-shot DSP
trigger would, and ASI re-arms.

## Offline checks

`tests/test_now_playing_trigger.py` recomputes the patch and template hashes,
reconstructs the whole new class from the patch and compares it byte for byte
with the authored template, asserts that the only edit to `SoundTriggerModule`
is the one-line factory wrap, checks the mode names and property name against
the contract, and pins both ACD wire payloads. The change also compiles: a
throwaway guest build of the `services` goal with the shim staged in passed
`//frameworks/base/services/voiceinteraction:services.soundtrigger_middleware
javac`, after which the guest tree was restored and re-verified byte for byte.

## What this page does not prove

That any mode works on the phone. Specifically unproven: that QC ACD accepts a
recognition config from a generic sound-trigger client on this unit and reports
AMBIENCE_MUSIC; that the `HOTWORD` `AudioRecord` ASI opens after a trigger
returns usable audio when the trigger did not come from a Google DSP model; and
that the on-device matcher identifies a real song. Those are device results for
the install page of the set that carries this patch.
