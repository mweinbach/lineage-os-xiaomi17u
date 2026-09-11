# AICore from this phone's global firmware, September 11, 2026

**Not device-admitted.** This page describes a reviewed source change and its
offline checks. Nothing here has run on the phone.

## The gate

Gemini Nano runs inside Google AICore. On the installed v22, AICore is absent and
Play refuses it — *"Your device isn't compatible with this version."* The reason
is not the silicon:

```xml
<!-- /product/etc/sysconfig/google_aicore.xml, nezha_eea_global OS3.0.336.0.XPAEUXM -->
<config>
    <feature name="com.google.android.feature.AICORE_QC_SM8850" />
    <feature name="com.google.android.feature.AICORE_QC" />
</config>
```

The global SKU of this same phone declares a system feature that **names this
exact SoC**. AICore's distribution is matched against declared features, and this
build declares 24 other `com.google.android.feature.*` entries and **zero**
AICore ones, so there is nothing for Play to match. See the
[availability record](gemini-nano-20260911.md) for the full measurement trail,
including the reasoning this finding corrects.

## Where the files come from

The official Xiaomi recovery OTA for the global SKU of this phone —
`nezha_eea_global`, `OS3.0.336.0.XPAEUXM`, Android 17, published MD5
`7a537f7858df429601d84f489c37726d`. Only the `product` partition was fetched, by
parsing the A/B payload manifest and downloading that partition's operation
ranges: **3.01 GB of a 9.58 GB archive**, reconstructed to a 3,907,145,728-byte
EROFS image, SHA256 `35521909f5f4ae9bdab5a70301fb00695477052d7ad99c0293c0550e023e5220`.
The tools are `reports/tier2-camera-20260909/ota_payload_index.py` and
`ota_extract_partition.py`.

This is the device's own firmware in another region, not another phone. No
identity, layout, kernel or firmware is borrowed.

| File | Bytes | Role |
| --- | --- | --- |
| `AiCore.apk` | 21,019 | Google-signed OEM stub, `versionName 0.stub.oem.stub_aicore_20260302.01_RC00…`, versionCode 395591. Reserves the package so Play can update it. |
| `google_aicore.xml` | 185 | The two feature declarations — the actual gate. |
| `privapp-permissions-aicore-product.xml` | 976 | Twelve privileged permissions for `com.google.android.aicore`. |

Note what is *not* there: no runtime, no model weights. The global phone does not
ship a working AICore either — it ships the declaration that lets Play deliver
one. That is the same arrangement as a Pixel, whose own preinstalled AICore is a
1.4 MB stub.

## The guarded fragment

`device/xiaomi/nezha/aicore.mk`, selector `NEZHA_AICORE`, admits the bundle by
size and SHA-256 through `aicore/verify.py` against
[`config/nezha-aicore.json`](../config/nezha-aicore.json) and copies the three
files into `/product`. It refuses a drifted or missing file, refuses a second
owner of any of the three destinations, and changes nothing else: no HAL, SELinux
or identity change. The bundle is flat and lives only in the ignored
`vendor/xiaomi/nezha-aicore` directory; the destinations are set in the fragment.

The platform half is already done — the GMS `PixelConfigOverlayCommon` overlay
points `config_defaultOnDeviceIntelligenceService` at
`com.google.android.aicore`, and `dumpsys on_device_intelligence` shows that
configuration live.

`tests/test_aicore.py` exercises the selector, the admission and the copies with
synthetic bundles, checks every contract destination has a copy line and an
ownership guard, and asserts the contract records the feature name as the gate.

## Known risks

Three permissions the global allowlist names **do not exist in this build**:
`ACCESS_NPU_MODEL_MANAGER_API`, `MANAGE_AISEAL_VIRTUAL_MACHINE` and
`ATTRIBUTE_WORK_TO_OTHER_APPS`. They are Qualcomm/Xiaomi framework additions.
Unknown names in a privileged-permission allowlist are ignored, so this is not a
boot hazard, but an AICore path that needs the vendor NPU model manager may not
work here.

This build also reports a Pixel fingerprint,
`google/mustang_beta/mustang:CANARY/…`. Declaring a Qualcomm AICore feature
alongside a Pixel fingerprint is inconsistent, and Play may key on more than the
feature alone.

## What this page does not prove

That Gemini Nano works. Specifically unproven: that Play serves the functional
AICore once the feature is declared; that AICore, once installed, judges this
device supported and downloads a model built for Hexagon HTP v81; and that any
feature actually runs. Those are device results for the set that carries this
fragment.
