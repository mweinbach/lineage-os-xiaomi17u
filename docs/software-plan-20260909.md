# Software plan, September 9, 2026

This is the plan for the ROM itself: what the phone does, in the order the
work should happen. Tooling, the update path and the kernel keep their own
[roadmap](roadmap-20260906.md); this page only borrows its last phase as the
graduation step. The starting point is the installed v14 userdebug build,
`nezha.98d08f70d20e5a87a2777f81`, on slot A with enforcing SELinux and root
ADB, described in [workspace status](workspace-status.md).

## Where the software stands

| Area | Verified on the phone | Not verified or missing |
| --- | --- | --- |
| Boot, policy, storage | Boots enforcing in about 25 s, userdata retained across fourteen A-only installs, no data clear | Retained personal data after a wipe-free update is assumed, not audited |
| Camera | Rear and front Ultra HDR, 50 and 200 MP, Pro RAW, UltraRAW DNG, three physical RAW sensors, ten Aperture effects, one HEVC/AAC video | Image quality, focus, stabilization, other video modes, microphone in video, sustained thermal behavior, four unported CameraOpt methods |
| Audio | Audio policy starts, decoded playback signal, 48 kHz mono AAC recording | Speaker, microphones, USB and Bluetooth audio, Dolby controls candidate |
| Display | Boots at 120 Hz default, factory density loaded | 600-nit normal-brightness curve, automatic brightness, low-brightness resume, HBM policy, refresh policy behavior |
| Fingerprint | Enrollment screen opened on a6d; user confirmed enrollment there | Enrollment acquisition, unlock, UDFPS icon geometry on the current build |
| Telephony | Radio registers for data (observed in earlier sessions) | IMS not integrated: no VoLTE, VoWiFi or IMS SMS; voice falls back to whatever the carrier still offers |
| Power | None | Suspend, wired and wireless charging, thermal throttling, workload classifier (blocked), power profile |
| Everything else | Wi-Fi connected during boot logs | GNSS, NFC, Bluetooth, sensors, haptics waveforms, `mi_ext` mounts and overlays, shade visuals |

## How each change ships

One focused source change per delivery set. Source revision N+1 gets a fresh
identity, the host gates run, the set is installed only on your separate
approval, the runtime result gets its own dated record, the status page moves,
and the predecessor set is deleted. Root on the userdebug build is the
diagnostic tool for every item below; measure first, change second. Normal
Android stays enforcing throughout.

## Tier 0: measure the baseline once

One authorized read-only session on v14 fills the 30-check
[hardware ledger](hardware-qualification.md) from
`config/nezha-hardware-qualification.json`: display curves, radio data, SMS
and voice, speaker, microphones and USB audio, motion and proximity sensors,
haptic waveforms, suspend, wired and wireless charging, thermal, GNSS fixes,
NFC tag read, Wi-Fi, Bluetooth audio, the camera rows, `mi_ext` mounts and
overlays, and the two vendor rows. Add retained userdata, UDFPS enrollment and
unlock, and shade visuals to the same session. Nothing is flashed. The ledger
decides how much of tiers 1 and 3 is real work and how much already passes.
Effort: one session, then a dated record.

Status: the host-drivable half ran on September 9 and is recorded in the
[tier 0 ledger session](hardware-ledger-v14-20260909.md): five checks pass,
twenty-five wait on a SIM, a person or an accessory. It also surfaced a zero
dim-brightness configuration, a recurring `vendor_qmipriod` denial and no kernel
suspend on USB, which feed tiers 1 and 3.

## Tier 1: daily-driver blockers, in order

Status, September 9: v15 is installed. The IMS provider runs in its restored
domain and is bound by telephony ([install record](v15-install-validation-20260909.md));
its carrier gate waits on a SIM. The dim fix is measured on the panel. The QMI
daemon loop stays as is until the ROM moves off the stock vendor policy images.


1. **IMS, so calls and texts work the way the carrier expects.** This is the
   largest missing feature. The [IMS inputs](ims-private-inputs.md) already hold
   the 24 exact-stock modules, a build-time producer and the reviewed framework
   API patch. What remains is engineering, not research: integrate the API
   patch into the source successor, write the IMS domains and mapping into the
   policy source so enforcing boot keeps its five known assertion sites and adds
   none, flip the guarded selector, and prove the build, policy closure and
   signed-image gates. Device gate: IMS registration, a VoLTE call each way, an
   IMS SMS, VoWiFi on the home network. Emergency calling is not tested. Effort:
   large, two or three delivery sets.
2. **Fingerprint.** The [lifecycle candidate](package7-fingerprint-lifecycle-20260905.md)
   compiled but no acquisition sample was ever observed. With root, capture the
   fingerprint HAL and sensor logs during one enrollment attempt, then fix the
   measured cause. Keep the stock center and radius. Device gate: enroll,
   unlock, and the UDFPS icon lands on the sensor. Effort: small to medium.
3. **Display brightness.** The [600-nit candidate](display-panel-normal-brightness-20260905.md)
   is built into the source but unmeasured. Device gate from the ledger: manual
   curve, automatic brightness, low-brightness resume, no flicker at the
   transition. Then decide HBM: the loader validates the transition durations,
   so admitting HBM needs replacement durations and a thermal rule; treat it
   as its own later change. Effort: small to validate, medium for HBM.
4. **Audio paths.** Speaker, both microphones, USB and Bluetooth audio from the
   ledger, then the [Dolby controls candidate](nezha-dolby-20260905.md) against
   the vendor backend. Microphone in video capture belongs here too. Effort:
   small to measure; unknown until measured.
5. **Power.** Suspend residency overnight, wired and wireless charging rates and
   the thermal envelope under a sustained camera or video load. The
   [workload classifier](nezha-workload-classifier-20260905.md) stays blocked
   until its admission gates close; do not activate it before the baseline
   numbers exist. Effort: measurement first; changes depend on results.

## Tier 2: finish the camera

The capture matrix passes, so this tier is quality and completeness.

- Port the four CameraOpt methods with real app call paths:
  `boostCameraByThreshold`, `reclaimMemoryForCamera`,
  `notifyCameraPerformanceTime` and `updateCloudData`, per the
  [completion record](camera-completion-20260907.md). `reclaimMemoryForCamera`
  fires during successful captures today, so it is the first one.
- Video: 4K and 60 fps modes, stabilization, slow motion, and the microphone
  track in each; decode every result off-device the way v13 did.
- Focus, exposure and stabilization behavior on each lens, then sustained use
  until thermal throttling, recording the temperature and frame-rate curve.
- Effect quality: compare each Aperture Ultra HDR effect with the Xiaomi app's
  output on the same scene; the decoder checks proved structure, not looks.

Effort: medium per item; each is a separate delivery set only when a source
change is needed.

Status, September 9: the four CameraOpt methods are ported in source revision 14
([record](cameraopt-four-methods-20260909.md)); the video matrix stalled on v15
because the platform loads the generic camcorder profile table, fixed in source
by the [camcorder profile fragment](camera-video-profiles-20260909.md). Both
wait for the next delivery set. The [v15 measurements](tier2-camera-v15-measurements-20260909.md) hold an
eight-minute 1080p recording (steady 24 fps low-light auto frame rate, no drops,
board +2.6 °C) and per-lens photos that all routed to the main sensor on the
dark desk, so focus and lens behaviour need a lit scene.

## Tier 3: polish

- Shade visuals and status-bar geometry on the current build; the approved
  normal geometry stays.
- [Refresh policy](nezha-refresh-policy-20260905.md): confirm 120 Hz default
  and peak, measure idle drops, decide whether any adaptive behavior is worth
  adding.
- [Haptics](nezha-haptics-20260905.md): confirm the three-level controls and the
  keyboard toggle drive the factory waveforms.
- `mi_ext` mounts and overlays from the ledger.
- The Google Weather widget's boot-time error card is a widget race, not ours;
  leave it.

## Tier 4: graduate to a daily driver

The userdebug build exists for diagnostics. When tier 1 is done:

1. Build the same source as `user` under a fresh identity and run the ledger
   again on it; root disappears, so tier 0 and tier 1 evidence must already be
   complete.
2. Decide the release-key option from the [detailed plans](next-steps-plan-20260906.md)
   (build-time keys on a read-only key volume, or post-build re-signing) and
   accept the one wipe it costs.
3. Build the first OTA package and take the update path from the roadmap:
   physical chain on both slots, then A/B updates with rollback, so every later
   change in this plan installs in the background instead of through fastboot.

## Order of work from here

1. Tier 0 ledger session on v14 (needs your authorization for a read-only
   device session).
2. IMS integration on the host while the ledger results settle.
3. Fingerprint measurement in the same or the next root session, fix in the
   following delivery set.
4. Display and audio validation from the ledger; source changes only where the
   numbers say so.
5. Camera tier 2 items interleaved as separate sets.
6. Tier 4 once calls, fingerprint and brightness pass.

## What this plan does not claim

Nothing here is a device result. Every "verified" cell above comes from the
dated records it names, on the build it names, and every device gate needs its
own authorized session. Effort labels are judgments, not measurements.
