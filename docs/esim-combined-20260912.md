# Combined application-LPA and held-channel test, September 12, 2026

**The complete combination still fails before ATR. eSIM remains unavailable.**
The user explicitly authorized the candidate/rollback reboot pair proposed in
the [interface investigation](esim-interface-20260912.md). Both reboots were
completed, the missing combination was exercised with a verified held channel,
and the original state was restored. This closes that experimental gap without
identifying the underlying card-interface or electrical cause.

The phone remains on Nezha v25, build `nezha.b2c99443fe9e90a4a7954eac`, slot A,
with SELinux Enforcing. The [receipt](../research/esim-combined-20260912.json)
separates candidate, capture, restoration and host evidence; raw logs, native
references and device identifiers remain in ignored storage.

## Exact candidate and boot verification

Fresh readbacks matched the preceding verified baseline. The live `mtb` hash
matched the previously inspected executable. The bounded QMI helper was hashed
locally, uploaded to a new temporary path, and hashed again on the phone. The
installed version-7 diagnostic APK still matched its tested build exactly.

| Record/state | Fresh baseline | Candidate |
| --- | --- | --- |
| 16-byte LPA record | `01010002010000000000000000000000` | `00000100000000000000000000000000` |
| Terminal capability | Absent | `060083010700` |
| QMI current SIM types | `[1,1]` | `[1,3]` |
| Selector EFS bytes | `0001010101` | `0001030101` |
| 70-byte slot mapping | Saved and hashed | Unchanged |

The fixed `mtb` interface received one decimal argument per data byte. Both
writes and the QMI selection were read back exactly before the candidate reboot.
A changed boot ID, completed boot, identical candidate records and
`RUNNING_UNLOCKED` were then verified. Modem EID queries returned `NotSupported`
(94), as expected for application-LPA mode; this was not used as an ATR-failure
criterion.

## Verified held-channel capture

Thales StrongBox opened a separate secure-element channel during boot. The
collector was adjusted to account for other clients without closing their
channels. That system channel subsequently closed independently; it was already
absent at the completed capture's baseline.

An initial collection stopped before any slot cycle because its parser expected
zero padding after the native dump's AID. The installed HAL copies each opening
AID into a fixed 16-byte buffer without clearing a previous longer AID's tail.
Its separate `Aid info` vector retains the actual opening-AID length. Native
disassembly confirmed this behavior; the parser now requires an exact
length-aware AID and matching raw-buffer prefix. The captured stale-tail case
was added to the host regression checks. The aborted collection released the
owned channel and restored its mask, and is excluded from the completed test.

During the completed collection, the same app PID and logical channel were
observed before and after the slot cycle. Both snapshots confirmed Java
ownership, the native channel's exact opening ISD AID, and a successful native
SELECT response. No extra APDU was sent during the hold. This establishes the
intended hold across the measured cycle endpoints.

The slot was already eSIM-selected, so one `--cycle-esim` operation performed
power-down, selection and power-up. The selector's `NoEffect` result was accepted
only alongside successful power operations and exact `[1,3]` readback. There
was no extra standalone selector transition in this capture.

| Current eSIM attempt | Power-enable request to RX BREAK | Reset-function restoration to RX BREAK |
| --- | --- | --- |
| 1 | 23.609 ms | 0.355 ms |
| 2 | 23.453 ms | 0.306 ms |
| 3 | 23.512 ms | 0.473 ms |

Each attempt uses nonzero handles, requests 1,200 mV, enables power and requests
reset assertion/restoration before RX BREAK. Final QMI card status independently
reports NO_ATR. No ATR progress or completion records appear. Two attempts also
emit explicit timeout flags showing no ATR received; the first takes a different
immediate error-reporting path. The result relies on positive error/status
evidence, separately from the expected unsupported EID API.

The capture contains 3,890 frames: 3,885 QSR4 and five mask replies, with zero
collector CRC errors, drops or decoder failures. All 3,602 matching-token records
resolve to the retained modem QDB; 283 other-token records remain unmatched to
that QDB. There are no queued QDB records before this capture's enable
acknowledgment. All 184 audited critical records have matching placeholder and
argument counts. Relative intervals come from modem timestamps, not USB receive
timing.

This run did not sample GPIOs or measure voltage. Its function/power messages
are software requests. The earlier separate fast capture supplies the observed
pin-mux evidence. The ordinary-bank timeout logger's changed data bit likewise
does not establish a response on the active eSIM interface.

## Restoration and validation

The app received STOP and its own Java/native channel release was verified
before physical-SIM cleanup. The collector then restored `[1,1]`, restored the
complete original diagnostic mask, released USB and removed its temporary
client. It reported no cleanup error or uncertain native process.

The controller restored the freshly backed-up LPA bytes, checked the terminal
record against this test's exact candidate before deleting it, and verified
absence. All four record observations then matched the fresh baseline. The
second authorized reboot restored the cached mode. Afterward, the complete
QMI results also matched baseline, including the EID API's original responses.
The initial, candidate and restored boot IDs were independently distinct.

Final checks verify the unchanged build/slot, Enforcing SELinux, unlocked user,
both default voltage-policy records, two Android slots and zero eUICCs. The
LPA controller remains `UnavailableState` with no selected service. The original
640-byte mask was queried again after rollback and matched exactly. The app is
stopped, no diagnostic-owned channel or probe process remains, temporary probe
files are removed, debugfs is unmounted and ADB is shell UID 2000. Other-client
channels were not closed by the test.

`make test-current` passes 1,124 tests and `make test` passes 5,101. Six collector
regressions cover the actual and malformed native formats and QMI/hold predicates.
Eleven isolated controller checks cover observation-only reboot resumption and
partial restoration, including an interrupted cycle whose selector has already
changed. These host checks use mocked operations and are separate from the
completed device experiment. No ROM image or diagnostic APK was rebuilt here.

## Remaining work

Both original modem-LPA mode and boot-loaded application-LPA mode now fail with
a verified ISD hold. The screen-lock/app-launch limitation no longer explains
the untested combination. Repeating these settings supplies no new discriminator.

The useful missing evidence remains the applicable card configuration definition
for `C1146657-A`, a supported module-status query from Thales guide D1611592 v1.2,
or actual ISO-interface/rail measurements on this board. The tests do not prove
that a card module is disabled or that the hardware lacks eUICC capability.
Android also needs a working LPA service once card transport works; an original
SIM app alone cannot supply the currently missing ATR or make the tested SPI
ISD-R selections succeed.
