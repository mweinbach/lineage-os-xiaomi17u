# eSIM NFC power and UART investigation, September 12, 2026

**eSIM still fails before ATR, but the modem's raw UART log now establishes a
receive-break condition before error cleanup.** Two completed tests added the
active NFC service's supported eSE power/link request to the verified ISD hold.
Both requests were acknowledged by the NFC controller, and both tests restored
the original phone state. The new condition did not make the card respond.

This follows the [combined application-LPA test](esim-combined-20260912.md) on
the same Nezha v25 build, `nezha.b2c99443fe9e90a4a7954eac`, slot A, with SELinux
Enforcing. Neither new test rebooted or flashed the phone. The
[receipt](../research/esim-nfc-uart-20260912.json) records hashes of private
evidence and separates native analysis, host checks and device observations.

## Supported NFC power request

The installed `NfcNciApex.apk` and its native library were pulled and hashed.
Their inspected always-on path, with NFC already on, calls the NFC controller's
eSE power/link operation without reinitializing NFC. The effective configuration
selects NFCEE `0x86` and enable value `0x03`.

| Operation | Captured outgoing NCI packet | Required response |
| --- | --- | --- |
| Enable always-on mode 1 | `22 03 02 86 03` | `42 03 01 00` |
| Restore always-on mode 0 | `22 03 02 86 00` | `42 03 01 00` |

The upper native callback discards the controller response status. Accordingly,
shell success and the Java always-on flag were insufficient: the controller
required a fresh matching command/response pair from the NFC snoop before the
slot cycle, and again before declaring restoration. All four exchanges passed.

Both tests retained the original modem-LPA records and used the already
validated diagnostic app's ISD hold. The same app PID, owned logical channel,
opening AID and successful native SELECT were checked at the cycle endpoints.
This records a held SPI channel and an accepted NFC power/link request. Neither
observation measures the ISO7816 supply or establishes card-module activation.

## Two captures, the same failed startup

| Measurement | First capture | Second capture |
| --- | ---: | ---: |
| QSR4 records | 4,660 | 4,361 |
| Records matched to the retained modem QDB | 4,257 | 3,958 |
| Other-token records | 403 | 403 |
| eSIM startup attempts | 5 | 5 |
| Attempts with RX BREAK and reset reason `[2,0,1,0,0]` | 5 | 5 |
| Explicit generic timeouts reporting no ATR received | 4 | 4 |
| Critical records independently audited | 138 | 138 |
| Critical argument mismatches / decoder errors / reported drops | 0 / 0 / 0 | 0 / 0 / 0 |
| Candidate QMI cycle duration | 5.250 s | 5.443 s |

Every candidate attempt requests 1,200 mV, enables its eSIM power vote, encounters
RX BREAK and disables the vote. The third attempt lacks the particular generic
timeout message emitted by the other four; its positive RX BREAK/reset evidence
remains present. QMI independently reports NO_ATR. Four later starts in each
capture belong to physical-SIM restoration and are excluded from candidate
counts. Changes in allocated nonzero handle values do not change this result.

## Recovering the UART register log

The exact OEM modem executable initializes a 4 KiB named `UIM_UARTDM_ULOG`.
Its registered DIAG handler supports version, named connection and bounded
format-1 reads. The authored collector uses only those operations and the
server-returned token; it does not use raw-address reads, log reset or enable
commands. Reading advances the log's reader cursor.

The first candidate read returned format 3 with four bytes of metadata. Native
analysis showed that this is an overrun-recovery response which can rebase the
reader before returning any records. It is not an end-of-log indication. The
second capture changed only collection handling: it continued supported reads
within the fixed budget after that response, before releasing the held channel
or restoring physical selection.

Seven replies then yielded 4,068 bytes containing 113 validated register records.
The first reply again reported overrun recovery; the remaining replies supplied
the retained tail. The capture is therefore not a complete startup history.
An independent raw-byte decoder confirms the critical sequence:

| Capture order | Operation | Value | Supported observation |
| --- | --- | --- | --- |
| 54 | Read UART SR | `0x20c` | Break and shared parity/framing bits clear |
| 56 | Read UART ISR | `0x21` | Break-change interrupt bit clear |
| 57 | Read UART MISR | `0x4` | Break-change interrupt selected |
| 58 | Read UART SR | `0x36c` | Break and shared parity/framing bits set before cleanup |
| 59 | Write UART CR | `0x10` | Receiver-reset command |
| 61 | Read UART SR | `0x0c` | Break/error bits clear after reset |

The stock reset path had already cleared the receiver and bracketed its RESET
handoff with the normal interrupt mask. This weakens the hypothesis that an
unchanged stale break simply survived that reset. It also resolves the earlier
ambiguity in the QDB message, whose handler synthesizes the printed `0x40`:
the raw receiver status independently has that bit set before cleanup.

These are UART observations. They do not measure voltage, prove the card-side
data level, locate the exact electrical onset, or identify whether routing,
power, configuration or the card caused the condition. The matching public
[UARTDM register definitions](https://fuchsia.googlesource.com/zircon/+/13ee3dc5e4c46bf127977ad28645c47442ec517d/kernel/dev/uart/msm/uart.cpp)
corroborate register naming but are from another hardware implementation.

Candidate and physical-restoration tails contain the same SIM_CFG values
`0x309`/`0x389`, CSR values `0x44`/`0x55`, and interrupt masks `0`/`0x1000c`.
Native analysis identifies SIM_CFG bit `0x80` as clock lifecycle control,
separate from the convention mask `0x6`. No MR1/MR2 access remains in these
tails, so complete live initialization-mode equivalence is not established.
The vendor's alternate clock retry was already exercised in the earlier
combined capture; repeating that clock choice supplies no new candidate.

## Lineage switcher applicability

The user-provided [Lineage controller](https://github.com/LineageOS/android_hardware_xiaomi/blob/e0b0fa0cf9b5a5c5f174a1c3a6e8d63cc361c1d1/packages/EsimSwitcher/src/com/xiaomi/mtb/EsimController.kt)
was pinned at hardware-xiaomi `e0b0fa0cf9b5a5c5f174a1c3a6e8d63cc361c1d1`.
It uses legacy OEM85 power-down, OEM84 GPIO selection, and OEM85 power-up.
The power messages match the tested QMI operations. The GPIO helper has no
Nezha product-401 entry and falls back to descriptor `0x4000`; even its getter
configures that GPIO. Stock Nezha uses the modern QTI SIM-type selector already
tested here. The legacy helper is not a verified Nezha enable path.

The [linked garnet commit](https://github.com/LineageOS/android_device_xiaomi_garnet/commit/0c2a8e865bc3c7f64d8f13153cda3f92071c2a59)
integrates the switcher, hook and policy. It supplies no chip initializer or
profile-download backend, and its variant declarations exclude CN/IN eUICC.
It can inform future settings integration once transport works.

## Restoration and continuing investigation

Each transaction verified original LPA bytes, absent terminal-capability record,
unchanged slot mapping, physical selection `[1,1]`, the complete original
640-byte diagnostic mask, native NFC default-power acknowledgment, unchanged
boot/build/slot and Enforcing SELinux. Owned channels were released, temporary
native probes were removed, and ADB returned to UID 2000. The app's STOP action
released its hold but left an idle process; a subsequent owned-app force-stop
removed that process, with identical Java channel dumps before and after. Native
dump requests after unroot produced no usable data; the root collector's earlier
native channel readbacks supply the native cleanup proof.

No firmware, profile, credentials, direct NV/EFS-file writes or Android security
policy changed. QTI selector operations changed and restored their own selector
record. NFC remains on with always-on off. Android still has no usable eUICC
or selected LPA backend.

`make test-current` passes 1,124 tests and `make test` passes 5,101. The NFC
transaction has 12 mocked host regressions, and the UART decoder has 16 host
fixtures. All 44 private artifact hashes in the initial receipt were recomputed
successfully. These are host/evidence checks, separate from the failed card
startup measurements; no ROM or diagnostic APK was rebuilt.

## Further firmware and card-reference comparisons

The previously retained configuration comparison left executable-code and AP
overlay gaps. Those have now been investigated using the retained CN, WW and
official EEA modem images. Nineteen bounded UART function groups, covering
1,264 instruction lines per image, match after explicit relocation mapping.
Eighteen power/level-shifter groups also match. The comparison preserves reset
order, mode/mask constants, clock choices, eSIM checks, votes and GPIO/QDI
operations. Ten complete UART tables are byte-identical. Unexamined external
callees remain outside this comparison; it does not prove whole-firmware
equivalence or interchangeability.

The EEA336 AP DTBO was reconstructed from 11 verified OTA operations, and its
complete 23,068,672-byte hash matches the OTA manifest. Its second overlay has
the same board selectors as CN309. Across 384 focused nodes and 1,375
properties, the compared ST54/NFC, PMIC and satellite SIM declarations have no
differences after resolving phandle references. The extra EEA overlay supplies
different platform selectors and has 22 PMIC differences; its compared ST/NFC,
satellite and SD-card settings match.

The Tiantong satellite driver does have runtime SIM-route controls. Its GPIO
getters request and free ownership, so they were not used as passive queries.
Reanalysis of all 138 earlier full GPIO snapshots found unchanged printed
PMH0101 GPIO8/10 output-low values, but the exact PMIC driver's debug output
uses cached fields for output level, direction and function. It rereads enable
control and conditionally input status. Those output-low strings therefore do
not establish the modem's actual level-shifter state. The numerical match
between the AP's GPIO10 and the modem's zero-based GPIO9 does not yet identify
the same PMIC controller or prove an eSIM connection.

Five small public-mirror artifacts, totaling 476,689 bytes, yielded ten Thales
maintenance scripts. The eUICC-update APEX duplicates three of the loose
catalogs. All scripts start by selecting a patch security domain; their only
unwrapped identity queries are FE, FD and FC, already measured here. There is
no AuditScript, matching `C1146657-A` definition, or documented pre-SELECT SPI
initializer. The target identifiers differ from the measured card OS platform
identifier.
Git blob identities and the APEX outer signature/source stamp verify, but
official factory membership was not established and six optional embedded
manifest hashes do not match decoded script bytes. No patch was executed.
The client uses a card-bound cryptographic session for its Thales provisioning
URL; that client path is not a shared-catalog read and was not contacted.

## Actual NFC controller configuration

An original temporary DEX helper invokes the active NFC service's typed Binder
API for two fixed ST GET_CONFIG commands. It registers no vendor callback,
changes no configuration and sends no card APDU. The active APK, JNI, HAL and
configuration file are hash-gated before dispatch. Fifteen mocked host tests
cover fresh response correlation, ambiguous/extra replies and cleanup failures.

| Record | Captured request | Observed value | Comparison with the freshly pulled shipped file |
| --- | --- | ---: | --- |
| Hardware | `2f02050300020100` | 48 bytes | Byte-identical |
| Secure element | `2f020503000b0100` | 30 bytes | Byte-identical |

Both controller responses have status zero, exact NCI/value lengths and raw
prefix bytes `0100`. The prefix's field meanings are not assumed. Each response
is correlated with its own fresh outgoing command, without another ST command
or response in that query window. The response timestamps follow the requests
by 9,759 and 6,944 microseconds respectively; these are log intervals, not chip
startup measurements. An independent decoder rechecked both responses against
the raw snoop and freshly pulled configuration file.

These records are therefore present and match the shipped configuration. Their
opaque fields supply no verified ISO7816-enable bit or card-module status.
No eSIM cycle was performed for these reads. The temporary helper was removed,
ADB returned to UID 2000, and boot/build/slot, Enforcing SELinux, NFC on and
always-on off were verified unchanged.

The official EEA336 `/odm/etc/st54l_conf.txt` was subsequently extracted from
the existing OTA with 1,382,007 additional compressed bytes. The whole 6,750-byte
file matches the freshly pulled phone file, so both measured controller records
also match the EEA shipped records. The new data operation was checked against
the retained manifest, reused reconstructed operations were rehashed, and all
required inode/directory/data extents were covered. This is a verified partial
extraction; no complete ODM-partition hash or new OTA-signature verification is
claimed.

The comparisons supply no supported global-firmware configuration change or
new card-activation command. TrustZone's separate eSE GPIO configuration and
the modem's downstream PMIC-controller mapping remain under host review.
The public [ST54L description](https://www.st.com/en/secure-mcus/st54l.html)
supports the chip family's eSIM capability; it does not identify this board's
connections or personalization. No measured result yet justifies changing
voltage, polarity, legacy GPIO descriptors or card activation state.
