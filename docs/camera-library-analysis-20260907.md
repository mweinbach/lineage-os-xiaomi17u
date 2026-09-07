# Camera library analysis (2026-09-07)

**The four Xiaomi “sensor probe fail” verdicts are logical-camera lookup
failures, not direct hardware-probe results.** Retained logs contain generated
camera entries, but their XML IDs do not match the IDs Xiaomi expects.
Qualcomm GSI configuration selection is now the strongest lead.

This was **off-device**, read-only analysis of retained libraries and logs.
No phone was accessed, restarted or changed. No camera fix is device-admitted.
The sanitized [record](../research/camera-library-analysis-20260907.json)
pins the inputs. Proprietary files, logs and disassembly remain ignored.

## Corrections to the earlier experiment

The [root experiment](camera-root-experiment-20260907.md) still establishes
that clearing persisted camera state did not restore cameras. Two causal
interpretations in that historical record are superseded:

- `retryTimes: 5 / expectSensorNumbers: 4` reports the initial retry budget
  **before** the per-module pass. It does not establish five failed attempts
  or an exhausted retry budget.
- CHI's damage routine searches `ExtensionModule`'s **logical-camera array**.
  It does not read CamX's raw per-sensor probe status. Proximity of strings
  or symbols in a stripped binary does not establish that relationship.

In the retained 09:18 provider-start log, the retry message appears at
09:18:37.211, EEPROM successes at 09:18:38.323, immune probe-success history
updates at 09:18:38.333, and generated camera entries at 09:18:38.998 onward.
The same capture contains sensor-mode data. None of this proves streaming
works, but it rules out treating the damage verdict alone as evidence that
no usable sensor records were produced.

## What the damage check actually tests

Addresses below are ELF virtual addresses, not ASLR-adjusted process addresses.
They apply only to the pinned binaries.

In `com.qti.chi.override.so`:

- `CameraIdXiaomi::addDamagePyhCameraRoleIds` starts at `0x632ea0`.
  Its call at `0x632f84` obtains a logical-camera record. Instructions at
  `0x632f8c–0x632f94` compare record field `+0x2d50` with the expected XML ID.
- `ExtensionModule::GetCameraInfo(unsigned)` at `0x54b430` bounds the
  requested index against logical count `+0x490` and indexes array `+0x498`
  with stride `0x2d68`.
- The retained damage verdicts expect XML IDs 1, 2, 3 and 4 for front, wide,
  ultrawide and tele, respectively, with Xiaomi roles 1, 0, 21 and 20.

The preceding generated records instead include:

| Logical index | Entry | Sensor ID | XML ID |
| --- | --- | --- | --- |
| 0 | UltrawidePhysicalCam | 1 | 252706820 (`0x0f100004`) |
| 1 | WidePhysicalCam | 2 | 252706817 (`0x0f100001`) |
| 2 | RearAONCam | 3 | 252706819 (`0x0f100003`) |
| 3 | TelePhysicalCam | 3 | 252706821 (`0x0f100005`) |
| 4 | Three-physical-camera logical entry | 1, 2, 3 | 0 |

Framework IDs are a separate field, not interchangeable with XML IDs.
The missing front entry and later stream failures still need explanation.
The downstream `sensorffrlist` is consistent with the failed logical lookup;
clearing it does not repair the table that regenerates it.

## A concrete path that can override `nezha.xml`

The factory ODM override file and the retained settings dump both contain
`multiCameraLogicalXMLFile=nezha.xml`. That dump displays the raw override
store, not the final selector.

The CHI dataflow is:

1. `ModifySettings()` gets the static-settings object. At
   `0x4f8c8c` it sets offset `0xf1d8`; at `0x4f8d4c–0x4f8d54` it copies
   that string into an auxiliary object at `ExtensionModule+0x480`,
   string offset `+0xd8`.
2. `GetDevicesSettings()` calls `ModifySettings()` at `0x4e55fc`, then
   applies SoC/framework-dependent replacements. Its jump table at
   `0x11279b`, indexed by SoC ID minus `0x241`, sends IDs `0x294` and
   `0x295` to `0x4e5750`, among other entries.
3. At `0x4e5754–0x4e576c`, if
   `isRunningWithVendorEnhancedFramework()` is false **and**
   `ChxUtils::IsGSIVersion()` is false, the replacement is
   `kaanapali_gsi.xml`. Assignment to the same string is at
   `0x4e56e0–0x4e56e8`.
4. `FillHwDeviceInformation()` reads that string at `0x4f7084–0x4f7098`
   and passes it to the XML picker at `0x4f70cc` (target `0x37c6c0`).
   The picker supports explicit filenames and automatic matching for an
   empty string or `_`.

The predicates are concrete, despite the confusing GSI naming:

- In factory `libqti_vndfwk_detect.so`, exported entry `0x5058` branches
  to `0x403c`. It returns the boolean
  `ro.vendor.qti.va_aosp.support`, with a false default.
- `ChxUtils::IsGSIVersion()` at `0x68d330` caches whether
  `ro.build.product` equals `generic_arm64`, case-insensitively.
- Factory `/system/build.prop` sets `ro.vendor.qti.va_aosp.support=1`
  and `ro.build.product=missi`. Vendor/ODM parity does not preserve a
  property supplied by the replaced system image.

This is a **conditional binary path**, not a measured current property value
or proof that this branch executed on the phone.

## Why the GSI lead is stronger than a filename guess

The compiled `kaanapali` registry pairs filename vector `0x750208` with
logical-definition-vector pointers at `0x750300`. Index 2 is
`kaanapali_gsi.xml`, pointing to `0x7ad900`; index 19 is `nezha.xml`,
pointing to `0x7ad7b0`. Registration copies those parallel arrays beginning
at `0x42196c` and `0x4219d4`.

The GSI vector constructor at `0x418104–0x418120` constructs eight entries.
Its wide, rear-AON, ultrawide and tele implementation IDs are assigned at
`0x417f20`, `0x41801c`, `0x41806c` and `0x4180d0`. They match all four
large XML IDs above. The Nezha vector constructor at `0x4148f4–0x41492c`
constructs thirteen entries; its tele implementation ID is 4
(`0x4147fc`, stored at `0x414830`), not `0x0f100005`.

This is a matching configuration signature, not proof of uniqueness across
every compiled XML or a recovered runtime selector.

## Next discriminating check

Under separately authorized device collection, capture the provider-visible
framework flag, `ro.build.product`, SoC ID, static string at `+0xf1d8`,
effective selector at auxiliary `+0xd8`, and selected XML name/handle.
If the selector becomes `kaanapali_gsi.xml`, test a narrowly scoped correction
to framework detection, then verify XML IDs 1–4, camera count, front/rear
capture and stream configuration. Do not patch away the damage verdict.

No such test ran here. Missing properties, failed static-setting propagation,
automatic matching and other XML selection paths remain distinguishable
possibilities. Stock VFE/SFE/ICP behavior also remains unverified; a stock
boot comparison is not authorized by this analysis.
