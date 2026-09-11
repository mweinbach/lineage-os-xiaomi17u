# Gemini Nano on nezha — the gate is a feature declaration, September 11, 2026

**Corrected.** This page first concluded that Gemini Nano could never run here.
That was wrong. The blocker is that **this build never declares it supports
AICore**: the global SKU of this same phone declares
`com.google.android.feature.AICORE_QC_SM8850`, and this build declares no AICore
feature at all, so Play has nothing to match and refuses the application. That
feature name is Google's own, and it names this exact SoC — so Gemini Nano *is*
built for this NPU. The correction and what was wrong about the original
reasoning are recorded in the
[availability JSON](../research/gemini-nano-20260911.json); the fix is in
[the AICore record](aicore-global-20260911.md).

The framework on the installed v22 is already wired for Gemini Nano and the
hardware is more than capable. What follows is the measurement trail, including
the two arguments that first led to the wrong answer, kept with what is actually
wrong about them.

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

Three measurements were taken. The first two were over-read at the time; the
third is what actually matters, and its answer changes once the feature is
declared.

### 1. The flag list names other silicon — but it is not the model catalogue

**This argument does not hold.** The list below is a binary-transparency
verification set, not the complete set of model groups, and the global firmware
declares `AICORE_QC_SM8850` regardless. It is kept because the measurement is
real and the client list is informative.

`AicModels__file_group_binary_transparency_allowlist`, read off this device,
lists the model file groups AICore knows about:

```
llm_it_xxs_edgetpu   llm_mmit_xs_edgetpu   llm_mmit_xs_edgetpu_baseonly   ← Tensor
llm_sm8635_xxs_it    llm_sm8650_xxs_it                                    ← Snapdragon
llm_slsi_npu_xxs_it                                                       ← Exynos
llm_mt6897_xxs_it    llm_mt6989_xxs_it                                    ← MediaTek
```

AICore is genuinely cross-vendor — its client quota list on this device includes
vivo, Sharp, Lenovo and Sony applications. The Snapdragon groups here name
SM8635 and SM8650 and no SM8850, but that absence proves nothing: the list
governs transparency verification, and the global firmware for this phone
declares `AICORE_QC_SM8850` anyway.

### 2. The models are per-NPU binaries (true, and not a blocker)

This part stands as a fact and explains why no *other* device's weights could be
copied in. It does not show that Google lacks an HTP v81 build — and
`AICORE_QC_SM8850` shows it has one.

These are not portable weight files. A Gemini Nano file group is a QNN context
binary compiled for one Hexagon HTP version: SM8635 is HTP v73 and SM8650 is
HTP v75, while this phone is **v81**. QNN graphs do not load across HTP
versions. The phone's own vendor models follow the identical rule — Xiaomi ships
`vendor/data/model/seg_quantized.serialized.**8850**.aimet.pertensor_512_cls3.minn`,
named for this exact SoC.

This is the same shape of problem as the Now Playing model, one level harder.
There the blocker was a Google module inside the Pixel ADSP image; here it is a
multi-gigabyte graph that has never been compiled for this NPU.

### 3. The shipped APK is a stub, and Play refuses the real one (on this build)

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

The gap is a declaration this build does not make. Pulled from the official
`nezha_eea_global` OS3.0.336.0.XPAEUXM OTA — the global SKU of this same phone,
Android 17, product partition SHA256 `35521909…` — the global firmware carries
exactly three AICore pieces:

| File | What it is |
| --- | --- |
| `/product/etc/sysconfig/google_aicore.xml` | declares `com.google.android.feature.AICORE_QC_SM8850` and `…AICORE_QC` |
| `/product/etc/permissions/privapp-permissions-aicore-product.xml` | twelve privileged permissions for `com.google.android.aicore` |
| `/product/priv-app/AiCore/AiCore.apk` | 21,019 bytes, `versionName 0.stub.oem.stub_aicore_…` — an OEM stub reserving the package for a Play update |

So the global phone does not ship a working AICore either; it ships the
*declaration* that lets Play deliver one. This build declares 24 other
`com.google.android.feature.*` entries and zero AICore ones.

Shipping those three files is therefore the whole fix on the build side, and it
is the device's own firmware rather than another phone's. That work is
[the AICore fragment](aicore-global-20260911.md).

## What this page does not prove

Whether Play serves the functional AICore once the feature is declared; whether
it runs on this build, given three permissions the global allowlist names do not
exist here (`ACCESS_NPU_MODEL_MANAGER_API`, `MANAGE_AISEAL_VIRTUAL_MACHINE`,
`ATTRIBUTE_WORK_TO_OTHER_APPS`, all Qualcomm/Xiaomi framework additions); and
whether this build's Pixel fingerprint (`google/mustang_beta/mustang`)
interferes. Those are device results for the set that carries the fragment.

## Device changes

None. Every step was read-only apart from opening a Play Store listing, which
was closed again. No install, flash, reboot or setting change.
