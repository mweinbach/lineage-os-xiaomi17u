# Performance and battery worktree handoff — September 5, 2026

This follow-up implements the five requested tracks as guarded source changes,
an exact private-input candidate and read-only measurement tooling. It does not
claim measured performance or battery improvements. The installed Package7 and
the separately active main-branch build are unchanged.

| Track | Delivered here | Still required |
| --- | --- | --- |
| 1. Camera scheduling | Opt-in `CAMERA_CAPTURE_SCHED` compatibility profile at the actual preserved vendor loader's system-ext path; two real joins to standard camera groups | Native delivery, loaded-library/file access and actual thread membership; compare capture latency and energy |
| 2. Refresh policy | Opt-in 120 Hz normal/peak defaults, source verification and saved-display-state analysis | Effective overlay/policy checks and measured transitions; no forced 24/30 Hz or invented flicker thresholds |
| 3. Screen-off drain | Bounded before/after snapshot collection and verified suspend, idle and wake-count deltas | Controlled unplugged intervals on an authorized installed device; identify any actual suspend blocker |
| 4. Power hints/classifier | Power/hint/thermal/property observations and a reproducible exact-byte disabled classifier bundle | Classifier signing/domain, native/class/JNI ownership, permissions and sender-boundary closure; effective hint and energy tests |
| 5. Memory pressure | PSI/reclaim/swap/ZRAM/read-ahead and LMKD observations, with offline comparisons and reset handling | Repeatable app-switch workloads and joint latency/retention/energy evaluation before changing memory policy |

## Source selection

For a separately reviewed successor, set these at product scope before inheriting
the Nezha device product:

```make
NEZHA_CAMERA_TASK_PROFILES := true
NEZHA_REFRESH_POLICY := true
```

Unset/false adds neither candidate. Invalid selectors fail. The camera guard
also requires the exact reviewed platform cgroup/init/profile source hashes and
exact candidate actions. Its independently authored profile selects supported
`camera-daemon` parent groups; it does not reproduce Xiaomi's unavailable
`limit-level6`/`limit-level2` children. If a thread already belongs to the parents,
successful resolution need not change placement or speed.

The refresh candidate corrects the generic peak default of 240 to the panel's
advertised 120 Hz maximum, keeping the normal default at 120. It does not
overwrite saved settings. The pinned Evolution code itself defaults a missing
minimum setting to 60 Hz: the saved 60 Hz vote is not proof of a user's choice.
Factory content detection and touch-timer properties are already present. No
unmeasured low-rate policy or battery-saving claim is introduced.

`NEZHA_WORKLOAD_CLASSIFIER := true` **fails with explicit blockers**. That is
intentional: producing exact files does not make their signer, permissions,
native dependencies or component boundaries compatible with Evolution. The
Android intent-security review also requires resolution of the custom receiver
sender boundary. No patched/resigned factory APK or permissive policy is used.

All public device files are in the generator's template inventory. The private
classifier packet remains separate and contains no active `Android.bp` or
automatic source installation step. Kernel, vendor/ODM images, thermal limits,
voltage/frequency tables, ZRAM size/compressor and memory sysctls are unchanged.

## Offline checks and future measurement

These commands access no phone and create no snapshot:

```sh
make performance-plan
make refresh-policy-verify
```

For actual collection, follow the [measurement workflow](nezha-performance-measurement-20260905.md).
It requires an explicitly identified authorized device and separate output
directories. The operator performs screen, USB and workload actions manually;
the collector does not change those states or poll throughout idle.

Snapshots retain exact build/kernel/boot identity, command outcomes, bounded
private output and hashes. Comparison rejects incompatible identities, bad time
ordering and counter resets. Permission-denied data remains unavailable. The
analyzer separates endpoint declarations from full-interval proof, cumulative
counters from gauges, and charge-counter drop from energy. A two-snapshot fuel
gauge change is not a demonstrated battery-life improvement.

For each installed candidate, compare controlled repeated workloads at matched
brightness, refresh policy, radios, temperature and background load. Measure
camera latency, frame consistency, app reloads, thermal behavior and energy
together. A passing source verifier, disappeared error message or registered
power service is insufficient by itself.

## Evidence and focused documentation

- [Camera scheduling](nezha-camera-scheduling-20260905.md): five exact private
  inputs, vendor constructor control flow and pinned platform admission checks.
- [Refresh policy](nezha-refresh-policy-20260905.md): source revisions, existing
  vendor properties, resource syntax and qualified saved-dump interpretation.
- [Workload classifier](nezha-workload-classifier-20260905.md): three original
  inputs totaling 197,970 bytes, verified producer output and activation gates.
- [Performance measurement](nezha-performance-measurement-20260905.md): collection
  limits, operator workflow, counter semantics and offline tests.

Native ROM/component delivery and physical outcomes remain separate from the
offline validation recorded for this branch. No phone, source VM, main branch,
original workspace files or existing private stock artifacts were modified.

## Final offline validation

The full suite passed **4,803 tests in 217.109 seconds**, including all 78 new
camera, refresh, classifier and measurement tests. Its retained private log is
`reports/feature-fixes-worktree-20260905/performance-all-tests.log`.
The generated-device-tree suite separately passed 252 tests. Both new Make
preview/verification targets ran without device access or snapshot creation.

The exact five-file camera capture and three-file classifier packet passed
fresh root-level verification. The camera source guard passed on the three
real pinned public source files; positive Make selection and duplicate-output
rejection were also checked. Refresh resources passed local `aapt2` syntax
compilation. The performance tests include a mocked complete preflight,
collection, receipt verification and comparison flow; no real device sample
or energy comparison was substituted for that fixture.

Independent source and measurement reviews found no remaining blocking code
issues after the camera path-variable correction and collector partial-read
handling improvements. These results do not establish native image delivery,
camera acceleration, adaptive low-refresh behavior or improved battery life.
