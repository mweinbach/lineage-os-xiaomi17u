# Tier 0 hardware ledger session on v14, September 9, 2026

**Five of the thirty ledger checks pass on the installed v14 build, none fail,
and twenty-five need a person, a SIM, an accessory, open sky or unplugged time.**
The session ran over root ADB with the phone found asleep on USB and left
asleep with every changed setting restored. Nothing was rebooted, flashed,
installed or wiped. The ledger validated with the maintained analyzer, and the
sanitized record is
[`research/hardware-ledger-v14-20260909.json`](../research/hardware-ledger-v14-20260909.json).
Raw dumps, screenshots and per-command receipts stay under the ignored
`evidence/hardware-ledger-v14-20260909/` directory.

## What ran

| Phase | Method | Phone state changed |
| --- | --- | --- |
| Passive | 94 read-only ADB reads (properties, dumpsys, sysfs, mounts, logs) plus the maintained collector with feature diagnostics | none; one five-packet ping |
| Active | manual brightness sweep, low-brightness screen off/on, automatic-brightness samples, Wi-Fi disable/enable, four haptic effects, shade and quick-settings screenshots | three settings changed and restored, Wi-Fi toggled, keyguard (swipe-only) dismissed |
| Load | four hash threads for 45 s with thermal sampling every 5 s and a 70 °C abort guard | temporary processes only |

## Ledger result

| Status | Checks |
| --- | --- |
| Pass | `display.manual_curve`, `power.thermal`, `wifi.connectivity`, `camera.xiaomi.startup`, `mi_ext.mounts` |
| Fail | none |
| Not run | the other 25; each has partial observations in the private session notes |

Passes mean the procedure was completed without a person at the phone. They
do not qualify calls, audio, sensors, drain, GNSS, NFC, Bluetooth or camera
capture, and the Wi-Fi pass covers one band only.

## Measured

| Item | Value |
| --- | --- |
| Brightness sweep, settings 1 to 255 | panel value 7 to 6142 of 16383, strictly monotonic, normal range capped at 600 nits, HBM off |
| Automatic brightness at about 12 lux | 0.18 of range, panel value 1110 |
| CPU load peak / recovery after 45 s | 52.1 °C / 30.5 °C, no throttling, clocks 2.75 and 2.88 GHz |
| Wi-Fi 6 GHz, 802.11be, WPA3-SAE | reconnect 2.2 s after disable/enable, ping 5/5 |
| Haptic effects | CLICK, DOUBLE_CLICK, HEAVY_CLICK, 300 ms one-shot all reported finished by the HAL |
| `mi_ext` | mounted as EROFS at first stage; 13 of the 22 vendor fstab overlay entries mounted |
| Retained userdata | 1 account, 22 third-party packages, 151 media files present |
| Fingerprint | sensor 5 present, 0 templates enrolled, keyguard swipe-only |

## Findings to act on

1. **No SIM detected.** The modem reported both card slots absent at boot,
   there are no subscriptions, and the status bar says "Emergency calls only".
   Confirm whether a SIM is inserted before reading this as a detection fault.
   All three radio checks wait on it.
2. **Dim brightness is zero.** The build's float dim configuration is 0.0, so
   the display's dim policy drives the panel to its minimum. The keyguard's
   ten-second user-activity timeout reaches that policy even while the phone is
   kept awake, so the lock screen goes nearly black. A first sweep taken on the
   lock screen read the minimum throughout and is kept as evidence. A nonzero
   dim value is a small overlay change.
3. **Recurring SELinux denial.** `vendor_qmipriod` is denied `search` on its
   own data directory every five seconds, 49 times in the retained buffer, on
   the enforcing build. One `vendor_location_xtra_daemon` denial on a system
   file appeared once. Both are policy work.
4. **Suspend never happened.** Suspend statistics show zero successes over 3.3
   hours of uptime with USB attached and a third-party job holding a partial
   wake lock at sampling time. The unplugged interval in the procedure is the
   only way to separate USB from a real problem.
5. **Keyguard carrier text fades at both ends.** The status bar text view
   applies its horizontal fading edge to a static string. Cosmetic; screenshot
   retained.
6. **Stale thermal cache.** `dumpsys thermalservice` cached CPU temperatures
   of 80 to 92 °C while the live HAL readings and every sysfs zone were 25 to
   28 °C. Not a live misreport; the load test confirmed the HAL tracks the
   zones.
7. **Idle load average near 10** comes from nine vendor kernel threads in
   uninterruptible sleep with the CPUs 93 % idle. Cosmetic.
8. A camera capture probe app from an earlier session is still installed under
   `/data/app`.

## What needs hands

In the order the ledger guide suggests: a SIM, then ordinary data, SMS and a
call with a consenting peer; a speaker and earpiece clip and a microphone
recording; USB and Bluetooth audio accessories; rotating the phone and covering
the light and proximity sensors; feeling the haptic effects; an unplugged
screen-off interval and a wired and wireless charge from below full; GNSS
outdoors; an owned NFC tag; fingerprint enrollment and unlock; Aperture front
and rear video and Xiaomi front video with lens transitions. Nothing in that
list needs a new build.

## What this does not prove

Receipts and hashes bind the evidence, not its interpretation. The five passes
were judged from readbacks and logs, not by eye or ear. No luminance meter,
no throughput test, no second band, no true suspend and no ambient meter were
available. The camera startup pass reuses the previous day's captures on the
same installed build rather than a fresh launch.
