# Private recovery diagnostics

`scripts/collect_recovery.py` collects bounded observations from an explicitly
selected Xiaomi 17 Ultra (`nezha`) already running recovery. It does not start,
install, boot or test TWRP. No phone access is needed to inspect the plan:

```sh
python3 scripts/collect_recovery.py
python3 scripts/collect_recovery.py --dry-run --include-pstore
```

Both commands run no ADB commands and create no files. Passing a serial without
`--collect` also leaves the tool in plan mode. A future, authorized collection
uses this interface, after recovery has been entered through a separately
reviewed and authorized procedure:

```sh
python3 scripts/collect_recovery.py --collect \
  --serial '<explicit-authorized-device>' --expected-device nezha
```

The placeholder is not a device selector. Use the exact independently verified
physical device serial, and do not publish it in shared logs or issue reports.
The tool rejects emulator and network endpoint serial syntax; it never connects
or reconnects ADB transports. It selects only that serial from the existing ADB
inventory and pins its `transport_id`. Within the same ADB server lifetime, a
disconnected transport is not replaced by another phone or a later connection
with the same serial. Do not restart the ADB server or switch platform-tools
versions during collection: transport IDs can be reused after a server restart,
which invalidates this session. Stop and start a new explicitly selected
collection if the server changes. Current Android
platform-tools with transport IDs are required. The selected transport must
advertise `shell_v2` in `adb features`; without that negotiated support, a legacy
ADB shell can conceal a failed remote command behind a successful client exit.

Preflight requires an authorized online ADB state (`device` or `recovery`),
matching Xiaomi manufacturer and exact `nezha` device properties, no emulator
marker, a recovery boot-mode or transport-state marker, and a running recovery
init service. It also requires one live `recovery` PID whose executable resolves
to `/system/bin/recovery` or `/sbin/recovery`. A completed normal Android boot,
conflicting mode properties, missing identity or process evidence, and failed
preflight reads stop collection before diagnostic logs are read. These are
consistency checks against a device that the operator already trusts; they do
not authenticate firmware or prove the bootloader or recovery is secure.

The default read scope is deliberately small:

| Observation | Bound and scope |
| --- | --- |
| `/tmp/recovery.log` | Last at most 1 MiB from a regular file; symlinks are refused |
| `dmesg` | Read without clearing the ring buffer; first at most 1 MiB of output |
| `logcat` | Snapshot with `-d -t 1000`; only selected recovery/service tags from main, system and crash buffers; at most 1 MiB of output |
| SELinux state | `getenforce` only; non-enforcing results create a warning, never a setting change |
| Mount and partition inventory | `/proc/self/mounts` and `/proc/partitions`; no mount operation or file enumeration under user data |
| Kernel and properties | Kernel release and an explicit property allowlist for recovery version, build, boot/slot, verification and encryption state |

The property allowlist does not include serial-number or credential properties.
There is no unrestricted `getprop`, bugreport, dumpsys, app listing, screenshot,
user-data read, recursive pull or arbitrary remote command option. Logcat's
default tag silence excludes unrelated app logs, radio and event buffers. Logs
can still contain personal data, secrets, addresses or identifiers emitted by
recovery, kernel and security services. Treat every artifact as sensitive; the
collector does not claim to sanitize it.

`--include-pstore` additionally lists `/sys/fs/pstore` and reads at most eight
regular files with `console-ramoops`, `console-ramoops-N` or `dmesg-ramoops-N`
basenames. Each read is limited to the last `--max-bytes` bytes. No symlinks,
traversal, unrecognized names, pmsg entries or directories are read. Unknown
entries are counted as policy exclusions. More than eight eligible files makes
the collection partial. Pstore can retain sensitive records from an earlier
Android boot, which is why it is disabled by default. Nothing clears or deletes
pstore, recovery logs or log buffers.

The collector never invokes `adb root`, `su`, `remount`, mount/unmount, reboot,
flash, unlock/relock, decrypt, format, sideload, install, push, delete, slot
changes, snapshot operations or TWRP control commands. It does not issue
network downloads or start an external service. ADB may start its normal local
host daemon when asked for its device inventory. Only bounded read commands are
sent to the already selected transport. Closing a local ADB client at a limit
does not issue a device-side stop command.

Per-command limits default to 15 seconds and 1 MiB for each of stdout and stderr.
Identity/property reads use smaller caps. `--timeout` may be set up to 60 seconds,
`--total-timeout` defaults to 180 seconds and may be set up to 900, and
`--max-bytes` accepts 4 KiB through 4 MiB. A fixed 32 MiB cap covers all captured
stdout and stderr in a session. Both pipes are drained incrementally, so a noisy
or stuck command cannot allocate an unlimited output buffer. The client is
stopped when either stream exceeds its cap or a timeout expires; cleanup waits
at most one additional second. Interrupted, capped and timed-out output is
retained with its actual status and hashes, not presented as a complete log.

Output defaults to a new `evidence/recovery-UTC` directory in this checkout.
`--output` may choose a new subdirectory inside that ignored evidence tree;
existing directories and symlink ancestors are refused. New evidence directories
use mode `0700`, files use `0600`, and an additional local `.gitignore` protects
contents if the folder is later moved. No existing evidence is overwritten.

The private `manifest.json` records the explicit serial, pinned ADB transport,
tool/helper hashes, command arguments, selected properties, timestamps, limits,
statuses, exit codes, stderr paths, warnings and SHA-256/length receipts for every
successfully saved stream. Terminal output redacts the selected serial. Permission denials,
missing files, absent executables and partial output remain visible in the
manifest; the collector never retries them with higher privileges.
A local evidence-write failure can leave files without final receipts; an
in-progress manifest or unlisted output must be treated as incomplete.

| Exit code | Meaning |
| --- | --- |
| `0` | Plan printed, or every requested read finished; this does not establish TWRP correctness or complete log coverage |
| `2` | Invalid arguments, failed safety preflight, or a local evidence-write failure |
| `3` | Diagnostics were collected partially: a read failed, reached a limit or could not finish |
| `130` | Collection interrupted; saved output is incomplete |

The tooling tests are entirely offline and mock processes; they are separate
from a phone test or an Android recovery build:

```sh
python3 -m unittest discover -s tests -p 'test_collect_recovery.py' -v
python3 -m unittest discover -s tests -v
```

Before a separately authorized phone test, retain the exact recovery image hash,
source/build receipt and compatible stock boot-chain hashes beside this private
collection. A successful read, a recovery log, or a readable partition inventory
does not prove display/touch support, decryption, backup coverage, restore safety
or correct slot/OTA behavior. See [the recovery plan](recovery-plan.md) for those
distinct test gates.
