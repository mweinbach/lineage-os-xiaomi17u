# V22 install validation — Now Playing identifies a song on this phone, September 11, 2026

**V22 (`nezha.b68e83ef070c648895e3881e`, source revision 22) is installed on
slot A. Now Playing works: with the music-trigger shim in `periodic` mode the
phone identified a track playing in the room and wrote it to Now Playing's own
history — "Never Gonna Give You Up, Rick Astley, 4:46 AM" — on a device whose
DSP cannot run Google's music model at all.** The set also stops the audio-HAL
reboot loop v21 exposed, arms Qualcomm's own on-DSP music context detector, and
carries the 8 mm lock-screen UDFPS icon. The approval was bound to bundle
manifest `f626deb90ed9e28a834deeea3d8bb44dc63d204e949e601420369110d3848b98`
before any phone write. The eight-image shared-Super slot-A write acknowledged
every payload rehashed identical, with no wipe and no slot change; userdata was
retained, and the device booted in 25.6 s with SELinux Enforcing, root ADB and
no fatal crashes. The structured record is the
[install validation JSON](../research/v22-install-validation-20260911.json).

## What the set changes

Two things, both reviewed:

- `NezhaMusicTriggerHal`, a sound-trigger middleware shim
  ([design](now-playing-trigger-20260911.md),
  [contract](../config/nezha-now-playing-trigger.json)). It claims the three
  Google music UUIDs and passes every other model, including the assistant
  hotword, through untouched.
- The device SystemUI overlay gains `udfps_icon_size` at 8000 µm, so the
  lock-screen fingerprint icon is drawn 132 px wide inside the 148 px sensor
  square instead of upstream's 99 px.

The v21 model files, the v20 recorder fix, Leica Essential, the CameraOpt
methods and the camcorder profile selection are all carried forward unchanged.

## Measured on device

| Mode | Verdict | What was observed |
| --- | --- | --- |
| `off` (default) | `refused_without_hal_reboot` | `LOAD_MODEL → ServiceSpecificException: Now Playing music trigger is off (code 2)`. **0 HAL reboots, 0 `onAudioServerDied`, audio HAL pid unchanged.** |
| `periodic` | **`song_recognized`** | Shim raised the trigger; ASI logged `Received music trigger: 'RecognitionEvent{data=music, captureSession=305, …rate=16000, status=0}'`, then `Running on-device song recognition`, then `Pipeline run finished`. Now Playing history showed the track and artist. |
| `acd` | `acd_armed_no_music_event_yet` | `QC ACD music context loaded → QC ACD music detection started (threshold 50, step 20)`, 0 HAL reboots. No context event, because the room was silent. |

The `off` result is the fix for the v21 regression: on v21 every load attempt
produced `INTERNAL_ERROR (code 5)` and `SoundTriggerHalEnforcer: Exception
caught from HAL, rebooting HAL`, restarting `audioserver` and the QTI audio HAL
on ASI's five-second retry. Here the same retry loop produces a recoverable
`OPERATION_NOT_SUPPORTED` and the audio stack is untouched.

The `periodic` result is the feature working end to end. The synthesized event
carries a real capture session and the 16 kHz mono PCM16 format, so ASI opens
its `HOTWORD` `AudioRecord`, reads live audio and runs its own matcher against
the ambient-music shard database that was already downloaded on the phone. The
track was played through the phone's own speaker at media volume 6 of 150 —
inaudible across a room, ample for a microphone centimetres from the speaker —
with `NowPlaying__capture_own_speaker_allowed` set for the test and reverted
afterwards.

The `acd` result proves the substitution is accepted by the vendor stack: the
Qualcomm HAL took a model carrying ASI's UUID with the ACD vendor UUID
`4e93281b…`, PAL opened an ACD stream, took the packed recognition config naming
context `AMBIENCE_MUSIC` (`0x08001336`), and started detection. Whether it
reports music on real audio is still unmeasured.

## Selecting a mode

`persist.sys.nezha.nowplaying.mode`, read at model load, surviving reboot:

```sh
adb shell su 0 setprop persist.sys.nezha.nowplaying.mode periodic   # proven to identify songs
adb shell su 0 setprop persist.sys.nezha.nowplaying.mode acd        # DSP-driven, detection unproven
adb shell su 0 setprop persist.sys.nezha.nowplaying.mode off        # safe default
```

The device was left in `acd` with Now Playing on, because that is the mode that
costs no periodic CPU wake-up if it works. `periodic` is the mode that is proven
to identify songs, at the cost of waking to listen on a timer.

## The UDFPS icon is built but not yet visible

The built SystemUI carries `udfps_icon_size` 8000 where the previous build
carried upstream's 6000, confirmed by dumping the resource out of the built
`SystemUI.apk`. **The drawn icon could not be measured, because no fingerprint
is enrolled on this phone**: `dumpsys fingerprint` reports `"count":0` and no
UDFPS window exists, so SystemUI draws no affordance on the lock screen. To
confirm the visible change, enrol a fingerprint, lock the screen and run
`reports/tier2-camera-20260909/measure_udfps_icon.py` against a fresh
`screencap`; the icon should measure about 132 px across inside the 148 px
sensor square.

## What this page does not prove

Whether Qualcomm's ACD reports music on real audio on this unit; the battery
cost of either live mode; recognition accuracy beyond the one track; and
anything about the fingerprint icon as drawn. Logs, screenshots and media stay
under the ignored evidence directory.
