# eSIM follow-up after removing the screen lock, September 12, 2026

The subsequent [interface investigation](esim-interface-20260912.md) measures
the alternate pin functions, identifies the card OS/configuration and records
the final version-7 diagnostic. The results below retain the earlier capture.

**The user is now unlocked and the diagnostic app's wake channel works again.
eSIM remains unavailable.** This follows the
[application-LPA boot experiment](esim-boot-20260912.md) on the same Nezha v25
build. The follow-up distinguishes the remaining card-startup failure from the
separate missing Android profile-management service.

## Measured on the phone

The user reports removing the password. Android reports `RUNNING_UNLOCKED` and
`deviceLocked=0`; these observations establish current accessibility, without
examining credentials or changing lock settings.

The original diagnostic app again opens the stock ISD logical channel, reaches
`READY_FOR_SWITCH`, and closes its channel and session after STOP. Its directory
query again succeeds with 38 application entries, including the exact eUICC
ISD-R AID. ISD-R selection on `eSE1` still fails with both P2 values 00 and 04.
This closes the app-launch obstacle from the preceding boot, but does not repeat
the combination of a held channel and reboot-loaded application-LPA settings.
The modem is currently on its restored configuration.

Version 4 of the owned diagnostic app adds strict reader selection for inspect
and discovery. It accepts only `eSE1`, `SIM1`, or `SIM2`, rejects reader options
for hold/registry, and does not substitute another reader. An absent reader
stops discovery before opening a session or attempting SELECT.

| Final APK check | Observed result |
| --- | --- |
| Inspect `eSE1` | Present |
| Inspect `SIM1` and `SIM2` | Both absent |
| Discover ISD-R on `eSE1` | SELECT attempted; `NoSuchElementException` |
| Discover on `SIM1` or `SIM2` | Reader absent; no session or SELECT attempted |
| Request `SIM3` or pass a reader to registry | Rejected before binding |
| Hold with its default reader | `eSE1` channel opens; STOP closes resources |
| Registry with its default reader | 38 entries; resources close |

The SIM-reader results are scoped to the restored physical-SIM selection, not
a new eSIM-selected experiment. Android's telephony dump reports two slots,
neither identified as an eUICC. The feature declarations for eUICC and MEP are
present, but `econtroller` reports `UnavailableState` and
`mSelectedComponent=null`: there is no selected LPA service.

## Modem startup capture

A read-only query through a local Qualcomm diagnostic client connected but
received no modem-mask response. A second query exposed an incompatible stock
router-state printer; its implausible fields were rejected. A bounded raw query
and producer-matched decoder established the relevant routing arrays instead.

The existing USB configuration already exposes a separate DIAG interface. A
host collector verified the selected phone's serial and interface descriptors,
claimed only that interface, and used its existing HDLC framing. It did not
reset USB, change configuration, detach a driver, or create a router logging
session. The first fixed mask query returned a CRC-valid reply.

The live router's range table establishes that UIM SSID 21 is word 21 in the
returned 0..158 range. The complete original response was saved. Only that
word changed from 0 to `0x0f`; the other 158 words remained identical. The test
held the app's ISD channel, selected eSIM, power-cycled slot 2, measured the
failure, then restored physical SIM selection and closed the hold. The final
mask reply exactly matches the complete original 640 bytes. This verifies mask
values, not every internal router bookkeeping field.

The 16.93-second capture contains 4,813 CRC-valid frames, with no dropped frames:
4,807 QSR4 records and six mask responses. Of the QSR4 records, 4,404 resolve to
modem SSID 21 using the retained QDB; 403 from another token group remain
unmatched. This firmware's argument-width/count nibbles differ from the public
reference decoder. Exact captured lengths and QDB argument counts establish
the corrected interpretation. The packets do not independently authenticate
the QDB's full image GUID.

Four other message IDs have 91 records with one extra argument relative to
their QDB text. None of the records supporting the power, level-shifter,
RX BREAK or ATR conclusions has an argument-count mismatch; unmatched or
inconsistent messages do not supply those conclusions.

Five eSIM startup attempts show:

- Three nonzero eSIM PM handles.
- Voltage modification allowed, a 1200 mV request, and the eSIM enable vote.
- The level-shifter PM driver enable call returns `pm_err=0`.
- RX BREAK, no received ATR, and native ERROR / NO_ATR card status.

The later physical-SIM restoration has separate 1800/2928 mV requests. Neither
phase obtained an EID. The repeated eSIM selector returned expected `NoEffect`
when already selected; the actual power requests returned success.

## Power and signal-routing interpretation

Further tracing of the retained, device-matched modem executable identifies a
limitation in earlier power tests. At `0x3861633c..0x38616348`, missing
eSIM enable/voltage handles skip the voltage and enable votes. The function can
still reach successful completion at `0x386164a8`. This proves a possible code
path. The new runtime capture rules out missing handles or a skipped enable
branch in this experiment. It still does not measure physical rail voltage.

The modem DTB maps `/pm/uim_esim/*` to the `L2F_E0` resource. It is separate from
the AP-side eSE GPIO46 checked earlier. Handle initialization creates the eSIM
resources for instance 1, with no product, region, current-SIM or LPA condition
in the examined chain. No additional regional initializer was identified.

The previously unchecked voltage policy is
`/nv/item_files/modem/uim/uimdrv/uim_hw_ldo_config_efs`. Its five-byte readback is
`0000000000` in both subscription contexts. The traced decoder treats that as
default policy; it does not request a custom voltage class that suppresses the
1200 mV vote. No change to this record is supported by the evidence.

The level-shifter override also matches the retained hardware configuration:
value 10 becomes index 9. It applies in the common power-on tail; the PM driver
call returns `pm_err=0` in both eSIM and physical-SIM phases. The electrical
output is unmeasured. No replacement value is justified.

The timeout logs show reset/clock/data values of 0/0/0 during the eSIM attempts,
but the native logger reads the ordinary `_mira` SIM pins. The eSIM branch uses
different `_mird` pin handles. Those zeros therefore do **not** establish that
the active eSIM pins were low. The remaining useful measurements are the
alternate signal routing/reset/clock/data path and physical eSIM supply, while
preserving card-OS/interface policy as another unresolved possibility.

The examined root-domain firmware sections did not yield a plaintext mapping
from those alternate pin names to physical GPIO numbers. The OEM executable
identifies the runtime descriptor block, but the retained code does not
establish a usable diagnostic memory-read handler and its routing. No modem
memory read or speculative GPIO/NV write was attempted.

A fixed read-only router inventory identifies the modem root and OEM domains
as DIAG IDs 7 and 8. The first receive contained 61 queued QSR records whose
timestamps immediately follow the restoration capture. A receive-only drain
retrieved the inventory reply, followed by 2.19 seconds without another bulk
packet. No duplicate request was sent. This establishes a bounded idle
observation and endpoint names; it does not supply a supported RAM-read handler
or a measurement of the active pins.

## What our own SIM app needs

The directory establishes an installed application entry. It does not reveal
selectable lifecycle, completed personalization, or permissions on each chip
interface. The prior native status 6999 therefore remains a selection refusal,
with its underlying chip condition unresolved. The standard LPA activation
command follows successful ISD-R selection; it is not a preselection enable
command. See [GSMA SGP.22 section 5.7.1](https://www.gsma.com/newsroom/wp-content/uploads/SGP.22_v2.2.pdf)
and [Java Card runtime section 4.6.2](https://docs.oracle.com/en/java/javacard/3.2/jc-re-spec/F74157_03.pdf).

The CN binding path was also traced beyond its UI. `BindEsimService` handles
card-originated CAT commands and delegates challenge/response processing to
Xiaomi's vendor binding service. Its card-ready path requires a PRESENT eUICC,
including the zero-profile case. The automatic post-enable binding check can
power off a mismatched bound card; it does not initiate pairing. The visible
code supplies no pre-ATR activation command. Vendor crypto/card-OS internals
remain unverified, and binding may still matter after card startup succeeds.

The application requirements are concrete: a privileged `EuiccService`, a card
transport that can select ISD-R and retrieve EID, and the profile-download and
management protocol. `EuiccCardManager` supplies card operations for the selected
LPA; the application still owns download/session orchestration.
[AOSP's implementation guide](https://source.android.com/docs/core/connect/esim-overview)
describes this division.

A maintained open-source starting point was checked and pinned:

- [OpenEUICC](https://gitea.angry.im/PeterCxy/OpenEUICC/src/commit/9a537a25163c5159899260fb6191a5da35a692bd):
  `9a537a25163c5159899260fb6191a5da35a692bd`.
- Its [libeuicc backend](https://github.com/estkme-group/lpac/tree/d214738fa0bdb23faf5833d3d798963079a00468/euicc):
  `d214738fa0bdb23faf5833d3d798963079a00468`.

That backend already implements the protocol and JNI interface. An original
service/UI can use it with a narrow Nezha QTI selector, preserving the selected
components' licenses and notices. Its Android service integration is partial,
including carrier-app and metadata/OTA callbacks; this is a source reference,
not a delivered LPA or a claim of complete carrier compatibility. No upstream
app was built or installed during this follow-up.

The first implementation milestone is measured EID, eUICC information and a
profile list through the selected service. A registration-only service would
change `mSelectedComponent` without resolving card access.

## Validation and final state

The final version-4 APK was built, signature/alignment checked, installed and
exercised through the reader, rejected-input, hold/STOP and registry cases.
`make test-current` passed 1,124 tests, `make test` passed 5,101 tests, the probe
builder passed six tests, and the Java registry parser harness passed. The
private diagnostic decoders passed five mask tests and 19 synthetic QSR checks;
capture framing and the complete mask restoration were independently recomputed.
These host checks validate tools and evidence, not working eSIM service.

The original LPA record, physical-SIM selection, absent terminal-capability
record and extended slot mapping were verified after the capture. The phone
remains on the same v25 boot with SELinux Enforcing. The diagnostic app remains
installed at version 4 and is stopped; its channels are closed and temporary
native probes are removed. This follow-up performed no reboot, firmware flash
or profile operation. ADB was returned to shell UID 2000 and verified after
cleanup; the boot ID remained unchanged.

Raw device logs, decompilation, upstream checkouts and generated APKs remain in
ignored `reports/esim-followup-20260912/` and `artifacts/`. The sanitized
[receipt](../research/esim-followup-20260912.json) records provenance, final state
and validation separately from the unresolved eSIM result.
