# Gemini Nano on nezha — measured unavailable, September 11, 2026

**Gemini Nano cannot run on this device, and the reason is not something this
workspace can fix.** Google's distribution refuses the application to this phone,
the only publicly shipped AICore binary is a stub, and no published Gemini Nano
model is compiled for this phone's NPU. The structured record is the
[availability JSON](../research/gemini-nano-20260911.json).

This page exists because the answer is counter-intuitive: the framework on the
installed v22 is already wired for Gemini Nano, and the hardware is more than
capable. Everything is ready except the one part only Google can supply.

## What is already in place

The build's GMS package set ships `PixelConfigOverlayCommon.apk`, which points
the platform's on-device intelligence service at AICore. AOSP leaves both of
these strings empty; on this device they read:

```
OnDeviceIntelligenceService:        com.google.android.aicore/…AiCoreIntelligenceService
OnDeviceSandboxedInferenceService:  com.google.android.aicore/…AiCoreIsolatedService
config_defaultOnDeviceIntelligenceDeviceConfigNamespace: aicore
```

`dumpsys on_device_intelligence` confirms the service manager is running with
that configuration. The hardware underneath is not the blocker either:

| Input | Value |
| --- | --- |
| SoC | SM8850 (`canoe`) |
| NPU | Hexagon HTP **v81** (`libQnnHtpV81Skel.so` is the only skeleton on the DSP) |
| On-NPU LLM runtime | `libQnnGenAiTransformer.so` and friends, present in `/vendor/lib64` |
| RAM | 11.3 GB |
| Free user storage | 458 GB |

Google also pushes 148 `aicore` DeviceConfig flags to this phone, so it is
within reach of the configuration service.

## What is missing

`com.google.android.aicore` is not installed, and it is not in the source tree
at all — the GMS package set ships ASI, Astrea, SettingsIntelligence and
AiIcons, but no AICore. Gemini Nano runs inside AICore, so nothing can work
without it.

Three independent measurements say that gap cannot be closed here.

### 1. Google's own flags name the target silicon, and this chip is not among them

`AicModels__file_group_binary_transparency_allowlist`, read off this device,
lists the model file groups AICore knows about:

```
llm_it_xxs_edgetpu   llm_mmit_xs_edgetpu   llm_mmit_xs_edgetpu_baseonly   ← Tensor
llm_sm8635_xxs_it    llm_sm8650_xxs_it                                    ← Snapdragon
llm_slsi_npu_xxs_it                                                       ← Exynos
llm_mt6897_xxs_it    llm_mt6989_xxs_it                                    ← MediaTek
```

AICore is genuinely cross-vendor — its client quota list on this device includes
vivo, Sharp, Lenovo and Sony applications — but the Snapdragon groups target
**SM8635** and **SM8650**. There is no SM8850 group.

### 2. The models are per-NPU binaries, so another chip's weights cannot be borrowed

These are not portable weight files. A Gemini Nano file group is a QNN context
binary compiled for one Hexagon HTP version: SM8635 is HTP v73 and SM8650 is
HTP v75, while this phone is **v81**. QNN graphs do not load across HTP
versions. The phone's own vendor models follow the identical rule — Xiaomi ships
`vendor/data/model/seg_quantized.serialized.**8850**.aimet.pertensor_512_cls3.minn`,
named for this exact SoC.

This is the same shape of problem as the Now Playing model, one level harder.
There the blocker was a Google module inside the Pixel ADSP image; here it is a
multi-gigabyte graph that has never been compiled for this NPU.

### 3. The shipped APK is a stub, and Play refuses the real one

`product.img` was range-fetched out of the official Google factory image
`mustang-cp2a.260805.005.a1` (published SHA256 `0eeb93e8…`; only the 2.78 GB
`product.img` member of the 9.61 GB archive was downloaded). AICore is there:

```
priv-app/AICorePrebuilt-aicore_20260302.01_RC00/…​.apk   1,447,374 bytes
versionName = 0.stub.stub_aicore_20260302.01_RC00.877448964
```

**1.4 MB, no native libraries, no model assets, and "stub" in its own version
name.** Even a Pixel does not carry a working AICore in its system image; the
functional application arrives as a Play Store update to eligible devices.

Asked directly on this phone, Play gives the verdict:

> **Android AICore (Beta)** — Google LLC
> **"Your device isn't compatible with this version."**

(The signed-in account is even enrolled as a beta tester for the app, and the
answer is still no.)

## Conclusion

Nothing short of Google publishing an SM8850 build of AICore and an HTP v81
model would change this. Sideloading the stub would add a Google-signed package
with no runtime behind it; sideloading a functional AICore from another vendor's
firmware would still find no model group for this SoC.

The device's own on-NPU LLM runtime is idle and usable, so on-device generative
AI is achievable here through stacks that publish weights for this silicon —
that is a separate piece of work, and it would not be Gemini Nano.

## What this page does not prove

Whether an SM8850 model group exists privately behind the opaque
`AicDataRelease__build_id_*` entries, and whether a functional AICore taken from
a non-Pixel Snapdragon firmware would behave differently. Both were left
untested: the first is not observable from here, and the second means running an
unverifiable binary with system privileges.

## Device changes

None. Every step was read-only apart from opening a Play Store listing, which
was closed again. No install, flash, reboot or setting change.
