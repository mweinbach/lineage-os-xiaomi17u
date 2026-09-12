# Nezha eSIM diagnostic

This authored diagnostic app observes the Android secure-element service and
performs a small, fixed set of read operations. It is intended for a developer
who has explicitly authorized diagnostics on a selected phone. It is not a
profile manager and cannot install, enable, disable, or delete an eSIM profile.

The app uses its own UID and requests only
`android.permission.SECURE_ELEMENT_PRIVILEGED_OPERATION`. Android must grant
that permission through its normal signing or privileged-app policy. Both
exported components require the caller's `android.permission.DUMP`; no launcher,
network, shared UID, boot receiver, or background service is declared.

## Build

Use an existing development platform key and its public certificate explicitly.
The certificate must be appropriate for the authorized target ROM. The builder
checks the APK against the supplied certificate; it does not inspect a phone.

```sh
python3 scripts/build_esim_probe.py \
  --sdk /path/to/Android/sdk \
  --java-home /path/to/jdk \
  --output artifacts/esim-probe-local-v7 \
  --platform-key /private/path/platform.pk8 \
  --platform-cert /path/to/platform.x509.pem
```

The SDK defaults are platform 36 and build tools 37.0.0. The output must be a new,
Git-ignored directory under `artifacts/`. The builder verifies the final APK's
signature, supplied public certificate, and ZIP alignment, then writes a build
receipt containing public input hashes. It passes the existing key directly to
the signer; it never copies or hashes the key or records its path in the receipt.
Building does not install or run the APK.

## Diagnostic modes

After an authorized installation, a shell with `DUMP` permission can invoke the
explicit activity. Replace `AUTHORIZED_SERIAL` with the already authorized
device's identifier. These are example commands, not an automatic device script.

```sh
adb -s AUTHORIZED_SERIAL shell am start -W \
  -n org.evolution.nezha.esimprobe/.HoldActivity \
  --es mode registry --ei seconds 90
```

| Mode | Operation |
| --- | --- |
| `inspect` | List readers and check the requested reader's presence; default to the first eSE reader. Open no session. |
| `hold` | On `eSE1`, select ISD `A000000151000000` with P2 `00`; hold the channel until stop/deadline. |
| `discovery` | On the requested reader, defaulting to `eSE1`, select ISD-R `A0000005591010FFFFFFFF8900000100`, or the fixed ECASD target described below, on a logical channel. P2 is `04` by default, or explicitly `00`. Log ATR/select-response lengths and SHA-256 hashes. |
| `basic-discovery` | On fixed `eSE1`, open the known ISD on the basic channel, verify its saved SELECT response, try the exact ISD-R SELECT with P2 `00`, and explicitly restore default selection before normal close. Send no command to the selected ISD-R after SELECT. |
| `registry` | On `eSE1`, select the ISD above, read the GP registry, and try the optional application directory if the registry query does not complete. |
| `identity` | On `eSE1`, select the ISD above and query the two fixed Thales OS-identification tags `FE` and `FD`. Log validated OS-version OIDs and patch bytes; query no card serial. |
| `configuration` | On `eSE1`, select fixed ISD `A000000030FF555001` on a logical channel and query only configuration tag `FC`. Require exact short-form TLV, `9000`, and 1–64 printable ASCII bytes. |

The optional `seconds` integer is bounded to 2–90. `discovery` also accepts
`--ei p2 0` or `--ei p2 4`. Only `inspect` and `discovery` accept an explicit
`--es reader eSE1`, `--es reader SIM1`, or `--es reader SIM2`. Other names,
empty values, and a reader extra supplied to other modes are rejected.
A missing requested reader fails without choosing a different reader. A listed
reader may report absent; discovery then stops before opening a session.

Only logical `discovery` accepts `--es target isd-r` or `--es target ecasd`.
Its default is `isd-r`; `ecasd` selects the fixed, previously enumerated AID
`A0000005591010FFFFFFFF8900000200`. Arbitrary AIDs, empty targets, and a target
extra in another mode are rejected before binding. `basic-discovery` and
`configuration` also reject a `p2` extra because they always use `00`.

For example, a SELECT-only check of the second modem/UICC reader is:

```sh
adb -s AUTHORIZED_SERIAL shell am start -W \
  -n org.evolution.nezha.esimprobe/.HoldActivity \
  --es mode discovery --es reader SIM2 --ei p2 0 --ei seconds 30
```

The app logs both the requested and selected reader. Reader presence alone does
not prove that the eUICC is usable. No reader choice changes the modem's SIM type
or performs a card reset.

A second start while a run is active is rejected;
after `DONE`, the same activity accepts another explicit start. To stop early:

```sh
adb -s AUTHORIZED_SERIAL shell am broadcast \
  -n org.evolution.nezha.esimprobe/.StopReceiver
```

Results appear in the activity and logcat tag `NezhaEsimProbe`. Keep collected
device logs in ignored storage. The app logs discovered AIDs and lifecycle bytes,
but no raw ATR/select-response payloads. A single I/O executor serializes all
secure-element work and cleanup. An independent watchdog kills this app's own
process at the deadline if a service call or cleanup hangs. `DONE` is emitted
only after resources close and the active-run ownership is released.

## Fixed protocol and interpretation

The registry mode uses the reviewed
[GlobalPlatform Card Specification 2.3.1](https://globalplatform.org/wp-content/uploads/2018/05/GPC_CardSpecification_v2.3.1_PublicRelease_CC.pdf),
sections 11.3 and 11.4:

1. Send GET STATUS `80F24002024F0000`. Continue only after status `6310`, using
   `80F24003024F0000`, for at most 16 pages. Status `9000` completes the query;
   any other status stops it and reports an incomplete result. Parse repeated
   `E3` templates with a direct `4F` AID, mandatory one-byte `9F70` lifecycle
   and mandatory three-byte `C5` privileges fields.
2. If GET STATUS does not complete, send the optional GET DATA application
   directory query `80CA2F00025C0000` once. The `5C00` tag-list data is required.
   A nonempty `9000` response contains repeated `61` templates with direct `4F`
   AIDs, with no outer `2F00` wrapper. Empty, unsupported, or denied replies are
   inconclusive.

All response bytes, including status words, share a 64 KiB cap. Parsing permits
at most 256 entries, validates enclosing BER lengths, rejects indefinite or
truncated lengths, and skips unknown direct child fields within their declared
lengths. OMAPI handles transport-level response chaining and logical-channel
addressing. The app adds no authentication, command substitution, or arbitrary
APDU input. Malformed responses stop the run with an incomplete result.

A completed list is scoped to what the selected security domain may reveal;
missing AIDs do not prove card-wide absence. A failed ISD-R SELECT, including
status `6999`, does not establish whether the applet exists. A successful eSE
session or registry read does not establish that modem-side eUICC transport,
EID retrieval, or eSIM profile management works.

The basic-channel comparison needs additional cleanup evidence. It first calls
`openBasicChannel(A000000151000000, 00)` and requires a returned basic-channel
handle. It reads the saved SELECT response and proceeds only after `9000`, then sends
the fixed ISD-R SELECT `00A4040010A0000005591010FFFFFFFF890000010000` once.
A `finally` block sends `00A4040000` again even when the target SELECT fails or
STOP has arrived. This restoration response has its own 64 KiB size bound so
the normal diagnostic byte cap cannot prevent the restoration attempt.
Only status `9000` emits `BASIC_DEFAULT_RESTORED`; other responses or exceptions
emit `BASIC_RESTORATION_FAILED`. Session/channel close follows in either case.

This operation uses the installed service's existing privileged SELECT support.
It preserves permission checks and exposes no general APDU input. A basic-channel
success would distinguish channel behavior; it would not verify the logical
channel needed by the standard LPA transport. ECASD selection is likewise only
a comparison of applet selectability, with no certificate or authentication
commands sent.

The installed HAL treats an exact transmitted `00A4040000` as basic-channel
close: it clears native channel ownership and may close its TEE connection.
Therefore the baseline must use the saved opening response. Opening with a null
AID cannot provide that response through this installed Java service. Version 5
sent an extra default SELECT before the target and consequently closed the
native channel early; that test produced a transport failure without a target
status word and was not a valid basic-channel comparison.

The explicit restoration SELECT may release native channel ownership itself.
Normal Java close then selects default again, and the subsequent native close
may report that the channel is already closed. Public close methods can suppress
errors, and the HAL's transmitted-default special case does not check `9000`
before clearing ownership. Consequently `DONE` or an app-side close return alone
does not prove final default selection or native release. Capture correlated
default-SELECT replies and compare both Java and native open-channel listings
before and after the experiment. Require a final observed default SELECT `9000`
and no newly owned channels; an already-closed native channel is consistent with
this sequence. A watchdog exit explicitly marks restoration unverified; inspect
native cleanup before another diagnostic. Do not reset the reader or close
another client's session as cleanup.

The identity mode follows the identification fields in the
[Thales Connected eSE 5.3.4 security target, page 11](https://messervices.cyber.gouv.fr/visas/ANSSI-CC-2024-33-cible.pdf).
It sends `80CA00FE00` and `80CA00FD00` only. A successful response must end in
`9000`, contain at most 256 bytes, and have one exact short-form outer TLV with
the requested tag. `FE` permits only contained OID values; `FD` requires exactly
four patch bytes. Unsupported, extended, malformed, or denied forms remain
inconclusive. The published example is a format reference; it does not establish
the installed card OS or activate any platform module. No CPLC serial,
certificate, authentication, activation, or profile command is included.

Configuration mode requires the saved ISD SELECT response to end in `9000`,
then sends exactly `80CA00FC00`. It accepts only one `FC` TLV whose declared
short length consumes the entire response body and whose 1–64 value bytes are
printable ASCII. Other formats or status words remain inconclusive. Reviewed
Thales-client references use this value as a configuration/customer class
shared by card configurations. The text does not establish enabled modules or
eUICC availability. This mode has no fallback, configurable AID/tag, or activation
command, and leaves the existing FE/FD identity queries on their original ISD.

## Host checks

The Python builder tests use only the standard library and mocked subprocesses:

```sh
python3 -m unittest discover -s tools/esim-probe/tests -p test_builder.py -v
```

The pure Java parser harness additionally checks valid registry/directory data,
unknown fields, long lengths, and malformed or excessive inputs. Compile and
run it with a local JDK into a private temporary directory:

```sh
mkdir -p artifacts/esim-parser-check
javac -d artifacts/esim-parser-check \
  tools/esim-probe/src/org/evolution/nezha/esimprobe/RegistryParser.java \
  tools/esim-probe/tests/RegistryParserCheck.java
java -cp artifacts/esim-parser-check org.evolution.nezha.esimprobe.RegistryParserCheck
```

These checks and a signed APK build are host evidence. Device permission,
session lifetime, and returned registry values require a separate device test.
