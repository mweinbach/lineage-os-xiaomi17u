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
  --output artifacts/esim-probe-local-v4 \
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
| `discovery` | On the requested reader, defaulting to `eSE1`, select ISD-R `A0000005591010FFFFFFFF8900000100`; P2 is `04` by default, or explicitly `00`. Log ATR/select-response lengths and SHA-256 hashes. |
| `registry` | On `eSE1`, select the ISD above, read the GP registry, and try the optional application directory if the registry query does not complete. |

The optional `seconds` integer is bounded to 2–90. `discovery` also accepts
`--ei p2 0` or `--ei p2 4`. Only `inspect` and `discovery` accept an explicit
`--es reader eSE1`, `--es reader SIM1`, or `--es reader SIM2`. Other names,
empty values, and a reader extra supplied to `hold` or `registry` are rejected.
A missing requested reader fails without choosing a different reader. A listed
reader may report absent; discovery then stops before opening a session.

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
