# Bounded performance, suspend and memory measurements

This is an offline-tested measurement workflow, not measured phone improvement.
It changes no governor, frequency, thermal limit, ZRAM size/compressor, swappiness,
read-ahead or page-cluster setting. It neither replaces the kernel nor grants
permission to contact a connected phone. No phone was contacted for this change.

## One snapshot, never a background idle poll

`scripts/collect_performance.py` captures a single explicitly selected, already
authorized physical Xiaomi `nezha`. It reuses the stock collector's identity
preflight and private output/receipt helpers, but implements its own bounded
subprocess reader: 256 KiB combined stdout/stderr per command, 120 commands,
180 seconds total, default five-second command timeout (maximum fifteen).
Timeouts, denied/missing interfaces and clipped output are unavailable, not zero.
Dynamic CPU-idle and block paths must match narrow numeric/name allowlists before
use. Unexpected discovery output skips that category with an unavailable reason;
safe endpoint collection continues and the text never becomes a command.
No `adb root`, root shell, broad pulls, unrestricted logs or shell writes exist.

The explicit serial is private, as are logs, app names, fingerprint, boot ID and
other evidence. Output is a fresh directory with private file modes and a local
ignore file. Do not publish snapshots. The receipt hashes retained command files;
it is an integrity record, not a signed proof of authentic device measurements.

The dry run has no ADB or filesystem side effects:

```sh
python3 scripts/collect_performance.py --serial EXPLICIT_AUTHORIZED_SERIAL --expected-device nezha --output evidence/performance-before --dry-run
```

After separately authorized device collection, remove `--dry-run` to take one
snapshot. For an idle experiment, add `--context screen-off-unplugged` only if the
operator actually established that context. The option records a declaration;
it does not change the screen, USB connection, settings or phone state. Repeat
with a new output directory for the second endpoint. The operator handles the
idle interval manually; do not poll ADB through it. USB disconnect/reconnect and
snapshot work can themselves wake the phone or charge it. Wireless ADB likewise
adds activity; this collector does not enable it.

```sh
python3 scripts/performance_analysis.py evidence/performance-before evidence/performance-after
```

The analyzer runs offline and prints JSON. It verifies every retained file's size
and SHA256, rejects traversal/symlink paths, unfinished manifests and mismatched
serial, exact build fingerprint/incremental, vendor fingerprint, kernel or boot
ID. Snapshot uptime must be positive/nonoverlapping and agree reasonably with
UTC elapsed time. The analyzer deliberately refuses across-build or across-reboot
cumulative counters: compare separately collected same-boot intervals per build.

## What is captured and what can be concluded

| Track | Retained measurements | Boundary |
| --- | --- | --- |
| Screen-off drain | Uptime/boot ID, battery plug state, power wakefulness, suspend successes/failures, CPU-idle time/usage, wake sources, suspend service, charge/current/voltage counters | Endpoint state does not prove the full interval; permission denial remains a missing measurement |
| Memory/retention | PSI totals, meminfo, selected cumulative vmstat counters, swaps, ZRAM mm/io/backing statistics and active compressor, LMKD dump and 200-line tagged log tail, read-ahead/page-cluster/swappiness | Memory/ZRAM values are gauges; log tails may rotate/overlap and are not a complete kill counter |
| Power hints | Power/performance_hint/thermal dumps, performance service states and workload-classifier properties/package | Registration is not proof a boost was delivered/released, and not an efficiency score |
| Refresh context | Effective display dump plus current system min/peak refresh setting reads | No preference is written and no frame-rate/battery benefit inferred |

Suspend, PSI and known cumulative vmstat/CPU-idle counters get nonnegative deltas.
A decreasing event counter is rejected as reset/wrap, never reported as a benefit.
CPU-idle time is per CPU/state in microseconds, not system suspend residency; do
not sum it into a single-device percentage. Known wake-source count columns also
get deltas; timing columns and suspend-service text remain manual observations
because vendor output formats/units are not guessed.

`/sys/class/power_supply/battery/charge_counter` follows the Linux power-supply
ABI's microampere-hour convention, but this vendor fuel gauge is not calibrated
by these scripts. Positive-to-positive net counter drop can yield an approximate
average net current over the midpoint uptime interval. Zero readings or increasing
counters are rejected. A fuel-gauge reset/recalibration to a lower nonzero value
cannot be distinguished from discharge by two snapshots. The report calls it a
net counter drop, not energy or a proven idle drain improvement. No mWh is computed
from instantaneous voltage, and power_profile.xml is not used as a measurement.

For useful battery comparisons, repeat controlled intervals with comparable
temperature, radios, brightness, apps and network conditions, and record the
operator's full interval context. For memory, record the repeated app-switch or
camera workload and correlate PSI/reclaim/LMKD evidence with observed retention
and latency. Actual interaction and optional future tracing require separate
device authority. A native build and installed-device measurement remain gates;
offline fixtures and successful dumps are not hardware qualification.

Policy and bounds: `config/nezha-performance-qualification.json`.
Offline tests: `tests/test_collect_performance.py` and
`tests/test_performance_analysis.py`; run the repository's standard-library test
suite before completing integration.
