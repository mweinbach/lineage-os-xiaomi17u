# Missing notification cards on v25, September 12, 2026

**The notification shade is retaining a lockscreen count after unlock.** The
user reported missing download/progress notifications in several apps and
supplied a screenshot showing the Silent section and only the small icon shelf.
A read-only capture with the shade open reproduces that appearance. Notification
content reaches both NotificationManager and SystemUI, but the stack remains
restricted to one notification even though the shade requests an unlimited count.

The [source candidate](../patches/evolution/nezha-shade-notification-limit.patch)
allows the unlimited count to be emitted while gesture tracking remains active.
It preserves the existing rule that lockscreen space recalculation waits for
gestures to finish. The candidate is **not installed or adopted into the Linux
source checkout**. The event that left interaction state active is unresolved.

## Measured state

The phone remains v25 (`nezha.b2c99443fe9e90a4a7954eac`), slot A, boot completed,
shell UID 2000 and SELinux Enforcing. The inspected source remains based on
`frameworks/base` commit `8140698cc12983deecdbd434220affb5f931bfc6` with its existing
local changes preserved. Upstream `bka` was checked at
`7857aa02c9a06e1b5a5f94673798062b6c34da63`; its affected flow method is unchanged.

| Open-shade observation | Value |
| --- | --- |
| Panel expansion fraction | 1.0, fully open |
| On lockscreen | false |
| Show unlimited notifications | true |
| Reported user interaction | true |
| Panel and quick-settings touch tracking | both false |
| Applied maximum notification count | 1; unrestricted would be -1 |
| Stack end height | 342 px |
| Show-shelf-only override | false |

`SharedNotificationContainerViewModel.getMaxNotifications` puts both lockscreen
recalculation and emission of the unlimited value behind `!isUserInteracting`.
The captured combination therefore leaves the old lockscreen limit in place.
This is a source-supported explanation of the retained limit and collapsed
stack. It does not identify which gesture or interaction source became stale.
The icon strip in the screenshot is the notification shelf, rather than a
notification whose text failed to inflate.

The retained SystemUI buffers place the interaction's transition to true at
phone time 19:41:16.488, exactly when a lockscreen drag begins. A brief
Glanceable Hub transition overlaps, followed by unlock. The buffer contains no
later false interaction event. This narrows the trigger to that gesture sequence,
but the specific missing cleanup path remains unproven.

At the final open-shade capture, the remaining notifications are the USB system
group. Earlier captures also contain ordinary app notifications. No actual
download was active during collection, so download-specific acceptance remains
pending. The main/system/crash buffers contain no matched notification-inflation
exception or fatal Java exception during this capture.

## Physical SIM observation

The newly inserted physical SIM loads as Google Fi. Telephony reports LTE
registration in service and a connected default cellular data context with no
failure cause. Wi-Fi is also connected. These are registration observations,
not a successful cellular download, call or SMS test. IMS/MMTEL and RCS are
unregistered in the captured telephony dump.

The already recorded `vendor.qmipriod` directory-search denial and restart loop
continues; see the [earlier diagnosis](tier1-ims-dim-20260909.md). It predates SIM
insertion. No causal connection between the SIM and the shade fault is established.

## Validation and next device step

Validation results and hashes are recorded in the
[candidate metadata](../patches/evolution/nezha-shade-notification-limit.json).
The patch includes two Android multivalent regressions for unlocking and opening
the shade while interaction remains active. Those Android tests have not run;
the separate coroutine harness exercises the exact production method with small
flow fixtures and does not constitute a SystemUI APK build or device test.

The original method reproduces the retained one-notification limit on unlock;
the candidate passes all six coroutine scenarios. Patch application reproduces
both recorded postimage hashes. `make test-current` passes 1,127 tests and
`make test` passes 5,104 tests, including the private evidence hash checks.

All raw dumps, screenshots, source snapshots and harness outputs remain under
ignored `reports/sim-progress-notifications-20260912/`. No phone setting, package,
file, root mode or modem configuration was changed, and no reboot or flash was
performed. The existing Apple Container service and sole source VM were resumed
for source reads; no source sync or Android build was started.

A separately authorized SystemUI restart can test whether clearing its transient
state restores the current notifications. It would not install the source fix
or prove that the fault cannot recur. Permanent delivery still needs source
adoption, a SystemUI/ROM build and separately authorized installation.
