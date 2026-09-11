# Volume does nothing: the engine has no volume curves, September 11, 2026

**Cause measured on the installed v23. The first fix shipped as v24 and boot-looped
the phone; the corrected fix below is a reviewed source change that has not run on
the phone.**

## What was reported

Media volume reads 0 and the speaker plays at full scale. Moving the slider
changes nothing.

## What the phone says

`dumpsys audio` agrees with the slider and disagrees with the speaker:

```
- STREAM_MUSIC:
   Muted: true
   Min: 0   Max: 150
   streamVolume:0
   Current: 2 (speaker): 0, 40000000 (default): 100
```

`dumpsys media.audio_policy` shows why the index does not matter. It prints
every volume group with its streams, attributes and index range, and **not one
curve point**:

```
    -AUDIO_STREAM_MUSIC (id: 9)
      Volume Curves Streams/Attributes, Curve points Streams for device category (index, attenuation in millibel)
       Streams: AUDIO_STREAM_MUSIC(3)
       Attributes: { ... }
        Can be muted  Index Min  Index Max  Index Cur [device : index]...
        true          00         150        0002 : 00, 40000000 : 00,
```

`VolumeCurves::volIndexToDb()` answers `0.0f` — no attenuation — when it holds
no curve for the device category, and logs `Invalid device category %d`. That
line is in the log continuously:

```
E APM::VolumeCurve: Invalid device category 1 for Volume Curve
```

Device category 1 is the speaker. **AudioService mutes a stream by setting index
0**, so with no curve, 0 is not silence, it is the loudest setting the slider can
reach. Every stream is affected; media is just the one that gets noticed.

## Why the curves are missing

Restarting `audioserver` reproduced the whole sequence in one second of log.

The HAL reads its engine configuration and is happy with it:

```
D AHAL_Config: getEngineConfig: number of strategies parsed: 8, default strategy: 5, number of volume groups parsed: 12
```

The framework then throws all of it away:

```
E APM::AudioPolicyEngine/Config: Function: aidl2legacy_AudioHalVolumeCurve_VolumeCurve Line: 143 Failed result (BAD_VALUE)
E APM::AudioPolicyEngine/Config: Function: aidl2legacy_AudioHalVolumeGroup_VolumeGroup Line: 156 Failed result (BAD_VALUE)
E APM::AudioPolicyEngine/Base: loadAudioPolicyEngineConfig: There was an error parsing AIDL data
W APM::AudioPolicyEngine/Base: processParsingResult: No configuration of AUDIO_STREAM_MUSIC found, using default volume configuration
```

Line 143 is the device-category conversion. The engine configuration the HAL
serves is Xiaomi's, `/odm/etc/audio_policy_engine_stream_volumes_mi.xml`, and it
declares eight device categories AOSP does not define — 33 curves beside the 60
standard ones:

| Category | Curves in the file |
| --- | --- |
| `DEVICE_CATEGORY_A2DP` | 12 |
| `DEVICE_CATEGORY_USB` | 12 |
| `DEVICE_CATEGORY_A2DP_CE` | 2 |
| `DEVICE_CATEGORY_HEADSET_CE` | 2 |
| `DEVICE_CATEGORY_USB_CE` | 2 |
| `DEVICE_CATEGORY_A2DP_SPATIALIZER_CE` | 1 |
| `DEVICE_CATEGORY_HEADSET_SPATIALIZER_CE` | 1 |
| `DEVICE_CATEGORY_USB_SPATIALIZER_CE` | 1 |

The xsdc parser maps an unknown enumeration to `UNKNOWN`,
`aidl2legacy_DeviceCategory` refuses that value, and because the AIDL path
converts a group's curves with `convertContainer()`, **one unrepresentable curve
fails the entire engine configuration**. `EngineBase` then falls back to
`gDefaultEngineConfig`, whose `volumeGroups` list is empty, so
`processParsingResult()` builds one volume group per default strategy out of a
default-constructed configuration that has no curve points at all. The live dump
confirms that is what happened: the strategies and group names are the AOSP
defaults (`STRATEGY_MEDIA`, `AUDIO_STREAM_MUSIC`), not the vendor's lowercase
names (`music`, `ring`).

Note what is *not* wrong. The vendor files are fine, the HAL is fine, and
`ro.config.media_vol_steps=150` is irrelevant. The XML path in `EngineBase`
already has a fallback for this shape of failure — `parseLegacyVolumes()` — and
the AIDL path simply does not use it.

## The fix

[`patches/evolution/nezha-audio-volume-curves.patch`](../patches/evolution/nezha-audio-volume-curves.patch),
one file, pinned by
[`nezha-audio-volume-curves.json`](../patches/evolution/nezha-audio-volume-curves.json):

`EngineBase.cpp` — if a converted configuration has no volume groups at all, fill
them from the legacy volume tables before the engine is built, which is exactly
what the XML path already does when it finds no engine configuration.

The AIDL conversion itself is left upstream. It still fails on the first
unrepresentable device category, so the framework keeps the AOSP default product
strategies it has always used here. **That is deliberate, and it is the whole
lesson of the first attempt** (below).

The names line up by construction. `parseLegacyVolumes()` builds one group per
stream type found in `/vendor/etc/audio_policy_volumes.xml`, named by
`audio_stream_type_to_string` — `AUDIO_STREAM_MUSIC`, `AUDIO_STREAM_RING` and so
on — and those are precisely the names the default strategies ask for. Fourteen
of the fifteen match; only `AUDIO_STREAM_CALL_ASSISTANT` has no legacy entry and
keeps the curveless full-scale behaviour it has today, and it carries no audio on
this phone.

What is lost is Xiaomi's per-category tuning. The curves now come from the AOSP
legacy tables, so absolute levels will not match stock exactly. They attenuate,
which is the thing that was broken.

## The first attempt, and why it boot-looped

The first version of this fix also patched `EngineConfig.cpp` so that a curve
whose device category cannot be represented is skipped instead of failing the
whole conversion. That looked better — it kept Xiaomi's twelve volume groups and
their real curves — and it shipped as **v24**
(`nezha.d2ff2fe2133ee17a0fb46d7f`). The install was clean: eight images written
and reverified to slot A, no wipe. The phone then never finished booting.

```
FATAL EXCEPTION IN SYSTEM PROCESS: main
java.lang.RuntimeException: Failed to create service com.android.server.audio.AudioService$Lifecycle
Caused by: java.lang.IllegalArgumentException: Invalid usage 19
    at android.media.AudioAttributes$Builder.setUsage(AudioAttributes.java:948)
    at android.media.audiopolicy.AudioProductStrategy.native_list_audio_product_strategies(Native Method)
    at com.android.server.audio.AudioSystemAdapter.getAllProductStrategies
    at com.android.server.audio.AudioDeviceBroker.<init>
    at com.android.server.audio.AudioService.<init>
```

The volume groups and the product strategies arrive in the **same** payload.
Accepting the configuration adopted the strategies too, and those come from
Xiaomi's `/odm/etc/audio_policy_engine_product_strategies_mi.xml`, which declares
four usages the vendor's own file does not:

```
AUDIO_USAGE_BLUETOOTH_SCO
AUDIO_USAGE_NOTIFICATION_COMMUNICATION_REQUEST
AUDIO_USAGE_NOTIFICATION_COMMUNICATION_INSTANT
AUDIO_USAGE_NOTIFICATION_COMMUNICATION_DELAYED
```

`AudioAttributes.Builder.setUsage()` refuses them, so the first thing
`AudioService` does with the strategy list throws, and `system_server` restarts
forever.

Only the volume groups are safe to take from this HAL. The corrected patch takes
neither — it does not touch the conversion at all — and gets its curves from the
legacy tables instead.

## What this page does not prove

That the phone attenuates. That is a device result for the delivery set that
carries the patch. Also unproven: which Xiaomi category the HAL sends first (the
AIDL payload is not readable from the device, so the category list comes from
the ODM XML), and whether any Xiaomi-only category carries tuning the five AOSP
categories do not already cover.

There is no runtime workaround. The curves are built once when audioserver
starts the audio policy manager.

## Method note

The only change made to the phone for this page was restarting `audioserver`
once to capture the boot-time engine log. Sanitized record:
[`research/audio-volume-curves-20260911.json`](../research/audio-volume-curves-20260911.json).
