# Current Nezha workspace status

**Installed phone: v14 userdebug (`nezha.98d08f70d20e5a87a2777f81`, source
revision 11, 672 rows), slot A, boot completed with SELinux Enforcing.** The
separately approved eight-image installation completed without a wipe, slot
change or data clear. V14 removes only the stale `SystemUIClocks-Flex` product
selection whose pre-QPR2 plugin interface crashed Wallpaper & style; on the
phone the picker now opens from the launcher and Settings, offers the default
and seven Pixel plugin clocks, applies and restores a clock, and logs no plugin
rejection or crash. A five-capture camera subset passes on the preserved v13
camera baseline. See the
[v14 installation and validation record](wallpaper-v14-install-validation-20260908.md)
and the [wallpaper clock plugin record](wallpaper-clock-plugin-20260908.md).

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
| Installed build identity | `nezha.98d08f70d20e5a87a2777f81` (userdebug, delivery set v14) |
| Installed source receipt | 672 rows; `reports/wallpaper-clock-plugin-20260908/source-revision-11/source-installed.json`, SHA256 `2227c605583e78d261bb4019c8f0a19dc057cf806980a4352f2eb1330301c484` |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v14/` (the only delivery set retained on the host; see the [retention record](artifact-retention-20260909.md)) |
| Bundle manifest SHA256 | `b36a0482e3b28be2c16d609f6cc6252b6c8b68ee25d0f87d624472df5b678ce0` |
| Reconciled signed target-files SHA256 | `fee3f8e03fef7ca7c29faf63d492d28d99c72be47dc93ddc05eafd90e9bd390d` |
| Signing/reconciliation result | Passed signing, reconciliation and eight-payload verification; receipts in the [wallpaper clock plugin record](wallpaper-clock-plugin-20260908.md) |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe, slot change or data clear; normal boot completed in 25.5 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; Flex package absent, seven kept clocks present, no plugin rejection lines; final cleanup reconfirmed build, slot and policy |
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
photos. CameraOpt still has explicitly unported methods, including
`reclaimMemoryForCamera`, which is observed during successful captures too.
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
verification remain separate evidence. The Linux checkout now holds source
revision 11 (`nezha.98d08f70d20e5a87a2777f81`): revision 10 plus the
`vendor/extras/evolution.mk` Flex removal. After the v14 installation record
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
  Other video resolutions/rates/modes, microphone response, playback quality
  and sustained recording remain unverified.
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
- **IMS and telephony:** the Android IMS provider is not integrated, and on
  September 9 the modem reported no SIM in either slot, so data, SMS and voice
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
