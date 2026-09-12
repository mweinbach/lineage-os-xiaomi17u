# eSIM startup with root GPIO and power logs, September 12, 2026

**eSIM still ends in NO_ATR. The modem now directly records all five attempts
configuring the three alternate interface pins, and the root power manager
records requests for the eSIM resource.** This adds driver evidence but does
not measure the physical signals or identify the secure element's module state.

The single completed experiment follows the [NFC/UART and root-log
investigation](esim-nfc-uart-20260912.md). It uses the same v25 build,
`nezha.b2c99443fe9e90a4a7954eac`, slot A, original modem-LPA records, verified
ISD channel hold and acknowledged NFC eSE power/link request. No reboot or
flash occurred. The NFC request, SIM selection, owned channel, diagnostic mask,
temporary helper, diagnostic-app process and ADB privilege state were restored.

## Instrumentation and limits

The previously verified root ULog protocol supplies four exact logger names:
`GPIO`, `PMIC Log`, `PMIC PRM Log` and `Spmi Log`. This capture confirms each
name with a fresh CONNECT before the candidate, then uses the returned token
throughout. This avoids relying on an unchanged Android boot ID to exclude a
modem-only restart. Four baseline READs validate the named sessions before SIM
dispatch. No connections are repeated during or after the candidate.

Root reads share the collector's single USB transport and run between polls of
the QMI helper. Each request has a 0.75-second deadline; a timeout or ambiguous
response disables further root reads. The aggregate limit is 128 READ pages.
No logger enable, reset, attribute or transport-setting command is issued.
The ordinary shared log-reader cursor and session bookkeeping do change.

The actual capture contains 91 root READ pages over 20 started live rounds and
two subsequent rounds, including one partially completed live round. It also
retains the existing OEM raw UART read. The saved DIAG stream has 4,499 frames,
123,371 payload bytes, zero recorded CRC errors/drops and no trailing partial
frame. The serial USB parser validates CRC while receiving; the saved payloads
do not retain the original HDLC checksum bytes for later recomputation.

| Root logger | READ pages | Rendered text bytes |
| --- | ---: | ---: |
| GPIO | 23 | 7,708 |
| PMIC Log | 23 | 0 |
| PMIC PRM Log | 23 | 13,896 |
| Spmi Log | 22 | 0 |

Zero-count formatted replies can hide read/overwrite errors. They do not prove
that a logger was empty, that no PMIC operation occurred, or that no error
occurred. Likewise, a page arriving late at the host may contain older retained
records. The capture is a bounded sample, not a complete power-operation audit.

## New startup evidence

The GPIO text contains five complete six-record groups:

1. DATA GPIO70, CLK GPIO71 and RESET GPIO72 select function 2, in that order.
2. RESET GPIO72, CLK GPIO71 and DATA GPIO70 return to function 0, in that order.

All 30 target records report pull 0 and raw drive value 200. The recorded drive
value is not interpreted as a measured drive current. These are modem driver
configuration records; they do not prove the pad's electrical level, external
connection, reset waveform or successful eSE response. The other GPIO text
records routine configuration of pin 141.

The root power-manager slice contains five entries for client `uim1_esim` and
resource `/pm/uim_esim`: enable state 1, then voltage-request state 0, enable
state 0, mode state 4 and mode state 5. Its last target timestamp precedes the
last GPIO group even though the page was received late in the capture. Missing
1200 mV or additional enable records in this partial slice cannot establish
that those requests were absent. The preceding native UART/QSR investigation
already recorded the modem's 1200 mV requests; neither log measures rail voltage.

The records establish that the root drivers receive alternate-pin and eSIM
power-resource operations during the failing test. They still do not map the
level-shifter's controller argument 1 to a physical PMIC/SID. No measured
configuration difference or documented card-activation command follows from
this result. The electrical path and the Thales module's activation state
remain unresolved, and Android still has no working eUICC/EID.

Both retained QSR dictionaries resolve all 4,391 compressed-message records:
3,988 OEM and 403 root records. The 138 critical argument records have no
arity errors. The candidate again makes five 1200 mV requests, five eSIM enable
requests and five RX BREAK events, each with reset-reason fields `[2,0,1,0,0]`.
Four attempts explicitly log ATR-received 0; the third instead records an
external-command timeout, with the same RX BREAK and reset-reason evidence.
Critical values match the preceding capture apart from opaque allocated
handles. This supplies no new cause-specific voltage, clock or pin setting.

The raw UART read independently decodes to 113 complete 36-byte records. Every
ordered instance/register/action/value tuple matches the preceding raw2 capture,
including interrupt status `0x4`, UART status `0x36c` and the subsequent
receive-reset command `0x10`. The ring includes an overrun marker, so this is a
retained window rather than the entire startup history. No new clock or
interface-setting difference appears in that window.

## Restoration and verification

The candidate QMI result selects `[1,3]` and reports NO_ATR. Cleanup verifies
physical selection `[1,1]`, original modem records, exact 640-byte mask
restoration, owned-channel release with other clients' entries preserved, and
temporary-probe removal. The diagnostic app is force-stopped only after its
owned channel is proven released; its process is then absent.

The coordinator requires a fresh complete process listing with no helper or
dispatch shell, and a terminal collector receipt showing completed physical
restoration, before lowering NFC eSE power or restarting adbd. The actual guard
passes. The NFC controller acknowledges both power/link 3 and its restoration
to 0. NFC remains on, always-on returns off, the original boot/build/slot and
Enforcing SELinux state verify, and ADB returns to shell UID 2000. Both journals
finish without cleanup errors.

The new collector passed ten independent mocked cases, its token helper passed
six cases plus four independent cases, and the coordinator passed 26 cases.
An independent audit correlates all 96 root responses to unique request windows,
reconstructs every page and text file, and verifies the held channel, QMI
selection and cleanup against their raw evidence. Three mutation checks reject
an incorrect token, altered phase text and an extra raw response. A separate
QSR audit reproduces the preceding capture's selected scalar event order after
normalizing only identified pointer fields, preserving zero/nonzero state.
The prior workspace checks in this continuation passed `make test-current`
(1,124 tests) and `make test` (5,101 tests). These host checks verify tooling;
the unsuccessful startup and restoration above are separate device evidence.

The machine-readable record is
[the root-power receipt](../research/esim-root-power-20260912.json). Raw captures,
device identifiers, source-derived proprietary details and temporary diagnostic
sources remain in ignored `reports/esim-continuation-20260912/root-ulog-cycle/`.
