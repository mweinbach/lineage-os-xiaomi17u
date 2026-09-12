# eSIM interface and card configuration investigation, September 12, 2026

**The modem reaches the expected alternate pin functions, but still receives no
ATR. eSIM remains unavailable.** The secure element reports Thales Connected eSE
5.3.4 v1.1 OS identifiers and configuration class `C1146657-A`. Its installed
ISD-R application refuses selection through both tested SPI channel types.
These observations narrow the failure without establishing its card-side or
electrical cause.

This continues the [unlocked-user follow-up](esim-followup-20260912.md) on the
same v25 boot, build `nezha.b2c99443fe9e90a4a7954eac`, slot A. No reboot occurred.
The [receipt](../research/esim-interface-20260912.json) records the measured
values, validation and hashes of ignored evidence.

## Alternate pins now measured

The retained Canoe pinctrl module's function arrays map alternate eSIM DATA,
CLK and RESET to GPIO 70, 71 and 72, function 2. The ordinary SIM functions use
GPIO 130, 131 and 132, function 1. The live device tree identifies
`qcom,canoe-tlmm`; none of these six pins is in its reserved-pin list.

A temporarily mounted, read-only debugfs exposed the driver's existing GPIO
register readback. The reviewed path skips invalid GPIO lines and reads control
and IO registers without exporting, requesting or programming a pin. A first
138-sample host capture caught DATA and CLK in function 2. Its roughly 129 ms
spacing could not resolve the short RESET transition.

An authored native sampler then read a fixed 5,120-byte prefix of the same file,
covering the six pins while stopping before the next GPIO controller. It ran
for 20 seconds with independent time and output bounds. Seven host parser
acceptance/rejection cases passed, and all 138 retained full snapshots verified
that the prefix contains the target lines within the first controller record.

| Fast capture measurement | Result |
| --- | --- |
| Samples | 7,204 |
| Median sample interval | 2.747 ms |
| Median file-read window | 2.230 ms |
| DATA / CLK / RESET samples in function 2 | 52 / 49 / 1 |
| Sample 744 | All three alternate pins read as function 2; ordinary pins read as function 0 |
| Sample 744 read window | 0.865 ms |
| Current eSIM startup attempts | Five; each still reaches RX BREAK and NO_ATR |
| Reset-function restoration to RX BREAK | 0.312–0.539 ms |

The six pins are read serially. One sample is not an atomic waveform
measurement. The output-level field is a GPIO output latch, not a physical
voltage measurement when the peripheral owns the pin. The fast capture retains
parsed pin records; the earlier full snapshots and reviewed parser provide its
input-format validation.

Correlated modem messages show the nonzero PM handles, 1,200 mV request, enable
vote and reset-function restoration already reached in the preceding capture.
RESET release hands the pin to the UART peripheral; a GPIO-latch-high write is
not part of that sequence. The fast sample rules out an entirely omitted mux
transition in this experiment. It does not verify board routing, the supply at
the chip or the actual clock/reset/data waveforms.

The capture contains 4,786 CRC-valid frames: 4,781 QSR4 and five mask replies,
with no collector drops. Of 4,378 records matched to the retained modem QDB,
230 precede the enable acknowledgement and belong to queued prior restoration;
they are excluded from the current experiment. Another 403 records use a
different token group and remain unmatched to the modem QDB. Both captures
restored physical SIM selection, the complete original 640-byte mask response,
the held channel and their temporary mounts/files.

The AP regulator metadata maps `L2F_E0` to `pmh0110_f_l2`. Its sysfs values report
cached AP requests and do not measure the shared physical rail. The
[ST54L data brief](https://www.st.com/resource/en/data_brief/st54l.pdf) separates
its 2.4–5.1 V battery supply from 1.2/1.8 V IO supply. The board connection of
the modem's named rail remains unverified; these values do not justify a voltage
override.

## Card identity and SPI selection

The original diagnostic app was extended to version 7 and installed using the
existing development certificate and Android permission policy. Its fixed
queries add no arbitrary AID/APDU input, authentication, activation, profile or
network operation. The [app documentation](../tools/esim-probe/README.md)
records each command and cleanup requirement.

| Final version-7 device check | Result |
| --- | --- |
| Known ISD on basic channel, then ISD-R SELECT | Opening `9000`, target `6999` |
| Explicit default restoration and Java-close default SELECT | Both `9000`; final FCI matches the opening FCI |
| Logical ISD-R SELECT, P2 00 | Refused; native `6999` |
| Logical ECASD SELECT, P2 00 and 04 | Both refused; native `6999` |
| OS tags FE and FD on the working ISD | Valid responses; patch value `00000000` |
| Configuration tag FC on fixed ISD `A000000030FF555001` | Valid response; class `C1146657-A` |
| Registry / hold and STOP | 38 directory entries / channel opens and closes |
| Discovery on absent SIM2 under physical-SIM selection | Stops before session or SELECT |
| Five invalid target/reader/P2 combinations | Rejected before a diagnostic run starts |
| Native channels after every case | Empty; basic-case Java and native dumps match their baselines |

Version 5's first basic-channel experiment is invalid as a channel comparison:
an extra default SELECT closed the installed HAL's native basic channel before
the target command, producing a transport error without a target status word.
Versions 6 and 7 use the saved opening response. Their actual ISD-R status is
`6999`, and correlated default-SELECT replies plus both channel inventories
verify restoration. An app-side close return alone would not establish this.

FE reports platform counter `D0026A15E0` and internal release `0102`; FD reports
zero patch bytes. These match **Connected eSE 5.3.4 v1.1, TOE revision 1.0** in
the [Thales platform target, page 11](https://messervices.cyber.gouv.fr/visas/ANSSI-CC-2024-33-cible.pdf).
The internal release 1.2 is not the separate product named v1.2. This is software
identification, not cryptographic attestation of the hardware or its configured
modules.

The [Thales eSA target, pages 10 and 26](https://trustcb.com/download/?wpdmdl=3979)
distinguishes optional card-platform module activation from applet installation.
ISD-R, ECASD and the eUICC plug need not all be enabled on every combo product;
GemActivate represents manufacturer-authorized platform administration. Thus
directory entries and OS identity do not establish an active eUICC plug. An
inactive module is a supported possibility, not a diagnosed cause.

The fixed FC query was derived from inspected Thales-client command handling.
Its ten-byte result is a configuration/customer class, not an EID or module
status. It matches none of the reference client's 102 configuration entries or
the scoped Xiaomi inventory: 2,435 files and 13,612 inspected units. The small
reference APK was used only for host analysis, with signature and provenance
limitations recorded privately; it was not installed or treated as firmware
for this device.

No supported module-status command was found. A concrete missing reference is
Thales **D1611592 v1.2, PLATFORM_IdentificationConfigurability for Connected eSE
5.3.4 V1.1**. Its applicable query definition or Xiaomi's configuration definition
for `C1146657-A` would allow a justified next card-status check.

## Xiaomi services and the remaining boot combination

The exact retained CN MITSMClient callers and Nfc_st implementations do not
supply the suspected activation step: Nfc_st's `activateSeInterface` and
`deactivateSeInterface` return `-1`; its inspected RESET_ESE receiver only checks
a flag and sleeps. The inspected deprecated ST settings methods for connectivity,
EnableSE and status are stubs. Complete retained vendor/odm/system_ext inventories
did not reveal a missing native IEsimService implementation. The inspected GPQeSE
recovery caller invokes coordinated NFC/SE reset after repeated TEE errors; no
measured evidence makes it an eSIM-enable prerequisite.

One experimental combination remains unmeasured:

| Boot-loaded LPA mode | Working ISD channel held during startup | Result |
| --- | --- | --- |
| Original modem-LPA mode | Yes | NO_ATR; expected mux/power requests now observed |
| Prior application-LPA candidate | No successful hold after that boot's locked-user state | NO_ATR |
| Application-LPA candidate | Yes | Not yet tested |

Native consumers of the candidate settings select profile ownership, APDU
security lists, network transport, callbacks and terminal-capability APDUs.
Some enclosing state machines can switch slots, but the inspected mode branches
do not select a new voltage, reset, mux or eSE-hold operation. There is therefore
little evidence that the missing combination will fix the initial ATR failure.
Testing it would close a specific interaction gap rather than exercise a newly
discovered initializer.

The prepared experiment repeats only the previous exact candidate: LPA record
`00000100000000000000000000000000`, terminal capability `060083010700`, and SIM
types `[1,3]`. Fresh device/build and record checks precede any changes. After a
candidate reboot, require `RUNNING_UNLOCKED` and `READY_FOR_SWITCH` before a
bounded slot-2 cycle and ATR capture. Evaluate card communication first; the
modem's EID API can be unsupported by design in application-LPA mode.

The rollback restores the freshly saved original LPA record, removes only the
test-created terminal record after an exact-content check, and restores `[1,1]`.
A second reboot restores the persistent mode cache. Both reboots need new
explicit authorization: the earlier authorized candidate/rollback pair was
already completed. No new candidate records were written in this investigation.

If that combination also fails, useful next evidence is the matching card
configuration guide or physical ISO-interface measurements on this board.
Android still needs a selected LPA service once transport works. Our app can
be extended into a profile manager after a usable eUICC channel is established;
the present diagnostic does not supply that missing transport.

## Validation and final state

Source commit `65b6568` adds the fixed diagnostics. The signed version-7 APK
was pulled back from the phone and exactly matches the host build, SHA-256
`1ac4c58a7092cf678b97328e99ca50372f12e20f7805946709c7d8edb4bced65`.
`make test-current` passes 1,124 tests; `make test` passes 5,101; the six builder
tests and Java registry parser harness also pass. These host checks are separate
from the device cases above.

Final readback verifies original LPA bytes, absent terminal record, original
70-byte mapping, both default voltage-policy records, and physical SIM types
`[1,1]`. Android reports two slots and zero eUICCs; `econtroller` remains
`UnavailableState`. The app is stopped, native channels are empty, temporary
probes are removed and debugfs is unmounted. ADB is back at shell UID 2000.
The build, slot, boot ID and enforcing SELinux state are unchanged. No profiles,
firmware, credentials or Android security policy were changed.
