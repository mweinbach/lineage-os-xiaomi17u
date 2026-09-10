# Current Nezha workspace status

**Installed phone: v15 userdebug (`nezha.81c1b93277a1fa371a3efbb3`, source
revision 13, 702 rows), slot A, boot completed in 25.4 s with SELinux Enforcing.**
The separately approved eight-image installation completed without a wipe, slot
change or data clear. V15 adds the exact-stock IMS provider, which runs in its
restored `vendor_qtelephony` domain and is bound by the telephony process (no
SIM is inserted, so no registration), and corrects the display dim level from
0 to 0.05, measured on the keyguard as panel value 314 instead of the minimum.
See the [v15 installation record](v15-install-validation-20260909.md) and the
[tier 1 source record](tier1-ims-dim-20260909.md). V14
(`nezha.98d08f70d20e5a87a2777f81`) remains the recorded predecessor: its
[installation record](wallpaper-v14-install-validation-20260908.md) holds the
wallpaper fix and the camera subset, and its bundle was removed after v15 was
installed.

The [v13 runtime record](camera-v13-install-validation-20260908.md) holds the
full camera matrix: UltraRAW DNG and embedded preview decode, audio policy
initializes, a short Xiaomi video has fully decoded HEVC and AAC tracks, and
ordinary rear/front photos, main/telephoto 50 MP, telephoto 200 MP, Pro RAW,
three physical RAW sensors and all ten warm Aperture Ultra HDR effects pass.
V14's seven camera/audio components are byte-identical to v13.

Source revision 10 is `nezha.2c510f47f6d99b93f0c3ee11`, with 671 recorded rows.
Its component/full build, signed archive and eight-image bundle pass their
checks, recorded in the [v13 package](camera-v13-package-20260908.md).
The source adds the measured [compressed Bayer and factory audio paths](camera-bayer-audio-compat-20260908.md).
Useful image/effect quality, sensor-native detail and sustained behavior remain
unverified; **full camera acceptance remains incomplete.**

The [v12 runtime record](camera-v12-install-validation-20260908.md) preserves
source revision 9 and its measured Bayer/audio failures, now resolved in the
v13 capture matrix. The retained source also includes
[save/audio compatibility](camera-save-audio-compat-20260908.md),
[stream sizing](camera-stream-sizing-20260908.md),
[vendor-key discovery](camera-vendor-key-discovery-20260908.md) and the
[CameraX cache backport](camerax-extension-cache-20260908.md).
[V11r1](camera-v11-install-validation-20260908.md) and
[v10](camera-v10-install-validation-20260908.md) remain preserved predecessor records.

V9 (`nezha.393aae12fba9ebe8627cdc38`), v8
(`nezha.f2e3feac321f56f92d2ad7ea`) and v7
(`nezha.c6ad60080698a987390afc40`) remain recorded predecessors. Their bundles,
signed archives and transfer copies were removed from the host in the
[September 9 retention pass](artifact-retention-20260909.md), which keeps only
the installed v14 set; every removed set is still identified by hash in its
dated record.
The [f9e installation](package7-f9e-install-20260906.md),
[a6d installation](package7-feature-successor-install-20260905.md) and
[original Package7 first boot](package7-first-boot-20260905.md) remain historical
device evidence. The [status archive](workspace-status-history-20260905.md)
preserves earlier checkpoints; its pending gates are not current selections.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Installed build identity | `nezha.81c1b93277a1fa371a3efbb3` (userdebug, delivery set v15) |
| Prepared successor (not installed) | v16 `nezha.434625bd9b5cd7a8a7eabd84`, source revision 15 (708 rows), bundle manifest SHA256 `5c57a12ff14d98349742ce59e6214d2ab2377c0c5e18edc2265b9b27b7188c3d`; needs a separate installation approval; see the [CameraOpt record](cameraopt-four-methods-20260909.md) |
| Installed source receipt | 702 rows; `reports/tier1-20260909/source-revision-13/source-installed.json`, SHA256 `f5236e241c60c0e61d17e21e006477d23723cfd089da6d3be144b3f78035917f` |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v15/` (the only delivery set retained on the host; see the [retention record](artifact-retention-20260909.md)) |
| Bundle manifest SHA256 | `64e5741d37eabcee872d6a64553e4ba7e99442465396fe2190431172bc22f4ed` |
| Reconciled signed target-files SHA256 | `ae3f0be8887e38fd35faf6792e60d11f344546a342875f8e69e760f58c53b953` |
| Signing/reconciliation result | Passed signing, reconciliation, 18 host gates and eight-payload verification; receipts in the [tier 1 record](tier1-ims-dim-20260909.md) |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe, slot change or data clear; normal boot completed in 25.4 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; IMS provider persistent in `vendor_qtelephony` and bound by telephony; no denials for the domain; dim policy lands at panel value 314 |
| Camera acceptance observed | On v14: rear/front photo, UltraRAW DNG/preview, one Aperture effect and a short HEVC/AAC video pass. On v13 (byte-identical camera components): five Xiaomi Ultra HDR photos including main/telephoto 50 MP and telephoto 200 MP, Pro RAW, three physical RAW sensors and all ten warm Aperture Ultra HDR effects pass |
| App data | V14: all 28 CE and five DE wallpaper picker members unchanged before first launch. V13: all 513 CE and five DE camera members unchanged; no claim about all userdata |
| Recovery | TWRP `working76`; preserve its `fix22ZJ-touchfix18` runtime/hardware setup, permissive recovery policy and zero-vibration defaults |
| Normal Android policy | Enforcing source/build baseline; measured current state is recorded above |

The private eight-image bundles and target-files ZIPs are not OTA or TWRP
installers. Preserve the installed v14 set, the working76 rescue recovery,
the stock return inputs, the signing key and the private build inputs.
Superseded delivery sets are removed once their successor is installed and
recorded; a removed set survives only as the hashes in its dated record. Artifact
checks, installation results and feature validation are separate evidence.

## Resume development

The selected camera-completion source extends the
[merged feature source](feature-candidates-build-merge-20260906.md),
[explicit userdebug opt-in](build-variant-opt-in-20260906.md),
[QTI camera XML selection fix](camera-xml-selection-20260907.md) and
[HyperOS camera-framework port](camera-framework-port-20260907.md).
`user` remains the default build variant. Userdebug requires its explicit
invocation opt-in, and normal Android SELinux must remain enforcing.

The [native camera hook record](camera-native-hook-20260907.md) preserves the
v8 implementation and installed baseline. The new [completion record](camera-completion-20260907.md)
adds measured v8 capture results and the selected CameraOpt source candidate.
Its original factory verifier and native boot hook remain unchanged. V10
resolves the measured vendor-key discovery failure and saves ordinary Xiaomi
photos. CameraOpt's four app-reachable methods, including `reclaimMemoryForCamera`,
are ported in source revision 14 ([record](cameraopt-four-methods-20260909.md));
eighteen methods without a known app call path stay explicitly unported.
The retained v11r1 sizing repair resolves the measured telephoto output
truncation and Pro RAW configuration failure. V12 adds the save APIs. V13 adds
the measured Bayer container path, now verified by full DNG and embedded preview
decoding.

The [v14 runtime record](wallpaper-v14-install-validation-20260908.md) is the
current phone evidence for the wallpaper fix and the camera subset; the
[v13 runtime record](camera-v13-install-validation-20260908.md) remains the full
camera matrix evidence. The [source behavior record](camera-bayer-audio-compat-20260908.md)
and [v13 package record](camera-v13-package-20260908.md) retain the host/build
checks and their offline test results. Artifact, installation and capture
verification remain separate evidence. The Linux checkout held source
revision 13 (`nezha.81c1b93277a1fa371a3efbb3`) for the installed v15 and now
holds revision 15 (`nezha.434625bd9b5cd7a8a7eabd84`) for the prepared v16, which
adds the four CameraOpt methods and the [factory camcorder profile selection](camera-video-profiles-20260909.md). After the v14 installation record
was added, `make test-current` passed 939 tests and `make test` passed 4,916
tests plus shell checks. After the September 9 retention pass and checker
update, `make test-current` passes 946 tests in 27.566 seconds and `make test`
passes 4,923 tests in 187.054 seconds plus shell checks.

1. Read [source-lock handling](source-lock.md),
   [device integration](../device/xiaomi/nezha/README.md) and the
   [build host guide](apple-container.md). Run `make apple-status` before resuming
   the existing `twrp-nezha-upstream74-20260829` VM and persistent
   `evolution-nezha-work` ext4 volume. Only one VM may write that volume. Recheck
   disk, OS, architecture, filesystem case sensitivity, manifest and source state
   before a sync or build; do not reset local source selections.
2. Continue from `/work/evolution` and the preserved
   `/work/out/nezha-feature-fixes-20260905-v1` output when preflight passes. Adopt
   a fresh identity and source/artifact records for each change, retain
   intermediates, and let Ninja invalidate changed edges. Use the
   [build/cache lessons](feature-successor-build-lessons-20260905.md); do not
   prune source volumes or delete protected source, output or rollback inputs.
3. Make a focused change supported by the reported behavior. Run
   `make test-current` while iterating, affected module tests when outside that
   selection, and `make test` before completion. Offline tests must not need a
   phone. Record build, package and device evidence separately.
4. Record each observed device result in a focused issue note and update this
   selection when the evidence warrants it. Phone collection and changes need
   the authorized device and scope. The explicit v14 approval ("ok can you
   install") covered its installation, reboot, wallpaper/clock tests, a camera
   subset and root diagnostics without a wipe or slot change. It does not
   authorize flashing any next bundle.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md). This
reproduces the pinned working76 prebuilt derivative, not a fresh runtime source
compilation. TWRP remains the required default recovery; missing or mismatched
inputs must fail. Recovery success with stock companions does not prove the
successor ROM boot chain or OTA behavior.

## Tier 0 hardware ledger on v14 (September 9)

The [tier 0 session](hardware-ledger-v14-20260909.md) ran the hardware ledger
against the installed v14 over root ADB without a reboot, flash or wipe and
restored every setting it touched. Five checks pass (`display.manual_curve`,
`power.thermal`, `wifi.connectivity`, `camera.xiaomi.startup`, `mi_ext.mounts`),
none fail, twenty-five need a person, a SIM, an accessory, open sky or unplugged
time. Findings to act on: the modem reports no SIM in either slot, the dim
brightness configuration is zero so the lock screen goes nearly black after
its ten-second timeout, `vendor_qmipriod` is denied every five seconds on the
enforcing build, kernel suspend never happened in 3.3 hours on USB, and the
keyguard carrier text shows a fading edge on static text. Retained userdata is
present (one account, 22 third-party packages, 151 media files); no fingerprint
template is enrolled.

## Remaining feature work

- **Camera:** V13 passes the requested capture matrix: ordinary rear/front
  Xiaomi Ultra HDR photos, main/telephoto 50 MP, telephoto 200 MP, Pro RAW,
  UltraRAW DNG and preview, three physical RAW sensors and all ten warm
  Aperture Ultra HDR effects. Useful effect quality, focus, stabilization,
  sensor-native detail and sustained behavior remain unverified. Preserve the
  [v13 runtime record](camera-v13-install-validation-20260908.md).
- **Video and audio:** Audio policy initializes with primary output handle 13
  at all three later boot checkpoints. A 10.079-second 1080p HEVC video and
  48 kHz mono AAC audio fully decode with a measured nonzero audio signal.
  On v15 the app offers no other resolution or frame rate because the platform
  loads the generic camcorder profile table; the stock `media.settings.xml`
  key is restored in the prepared v16. An unattended eight-minute 1080p
  recording on v15 ran at a steady 24 fps (low-light auto frame rate) with no
  dropped frame and a 2.6 °C board rise ([measurements](tier2-camera-v15-measurements-20260909.md)).
  4K, 8K, 60 fps, slow motion, microphone response and playback quality remain
  unverified.
- **Wallpaper process:** Resolved on the installed v14. The measured cause was
  the stale `SystemUIClocks-Flex` prebuilt (pre-QPR2 plugin package with a
  bundled interface copy); v14 drops that product selection while SystemUI's
  default provider keeps the Flex clock. On the phone, Wallpaper & style opens
  from both routes, the clock chooser offers eight faces, a plugin clock applies
  and the default restores, with no plugin rejection or crash. Wallpaper
  changes, theme packs and the other six plugin clocks were not applied. See the
  [v14 runtime record](wallpaper-v14-install-validation-20260908.md).

- **Retained userdata, UDFPS and shade:** The tier 0 session found the user's account, third-party apps and media present on v14, no fingerprint template enrolled, and a fading edge on the keyguard carrier text; enrollment, unlock and shade acceptance by eye remain unverified.
  The user confirmed fingerprint enrollment on a6d; f9e loaded the measured
  pixel-pitch correction and shade configuration. Their
  [source/build measurements](package7-ui-camera-followup-20260905.md) and
  [installation results](package7-f9e-install-20260906.md) remain preserved.
  Those results do not establish current rendering, authentication or userdata
  behavior. Preserve the approved normal status-bar geometry when refining shade.
- **IMS and telephony:** the exact-stock Android IMS provider is installed with
  v15, runs in its restored `vendor_qtelephony` domain and is bound by the
  telephony process. No SIM is inserted, so registration, data, SMS and voice
  are untested. VoLTE, VoWiFi and emergency calling remain unverified. The workload classifier also
  remains disabled; selected display, Dolby, haptics, camera-scheduling and
  refresh candidates still need their own measured device results.
- **Other hardware and lifecycle:** track networking, display/touch, audio,
  fingerprint, sensors, storage/encryption, charging and thermals separately.
  OTA/update behavior and stock restoration remain untested. The
  [roadmap](roadmap-20260906.md) retains the private audience, eventual both-slot
  coverage and source-kernel design goal with the prebuilt kernel selectable.

Use [native features](native-features.md), the [documentation index](README.md)
and [build history](build-progress.md) for the underlying research and dated
experiments. The [cleanup record](workspace-cleanup-20260905.md) identifies
retired duplicate expansions; historical replay must rematerialize them from
their retained archives before following an old path.
