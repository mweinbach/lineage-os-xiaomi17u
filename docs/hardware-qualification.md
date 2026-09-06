# Nezha hardware qualification ledger

The [remaining-feature audit](package7-remaining-feature-audit-20260905.md)
identifies registered hardware that still needs behavioral tests. The source-owned
[check plan](../config/nezha-hardware-qualification.json) and
[offline validator](../scripts/hardware_qualification.py) provide a repeatable
way to record those results against the actual installed build. They never
invoke ADB, change the phone, start a VM or build sources.

Every check begins `not-run`. Only an operator's explicit measurement can become
`pass` or `fail`; a supplied service dump cannot promote a check. Pass and fail
both require an observation, timezone-aware measurement time and nonempty saved
evidence files with matching SHA-256 hashes. This verifies record integrity, not
whether the operator interpreted a recording correctly. Review evidence before
using a result to close an issue.

## Prepare an acceptance session

Print the concrete checks and an empty ledger with the CLI:

```sh
python3 scripts/hardware_qualification.py plan
python3 scripts/hardware_qualification.py template --build-identity nezha.ACTUAL_INSTALLED_ID
```

Save the template as `results.json` inside a new ignored `evidence/` directory.
Use the installed incremental identity from a saved, authorized capture, not the
identity of an uninstalled source successor. Keep each installed build/session in
a separate directory. Raw call details, SIM identifiers, locations, photos and
logs must remain private. Do not commit generated ledgers containing those data.

The [stock collector](stock-evidence.md) supports `--feature-diagnostics` for
read-only context including service state, telephony, audio, camera, sensors,
power, location, networking and selected `mi_ext`/overlay values. Preview its
command plan with `--dry-run`; actual collection requires an explicitly
identified, authorized device. These dumps support observations, but do not
perform the behavioral procedures or establish a pass. A future installation,
phone state changes and communications with test peers need their own authority.

The smallest useful order is ordinary data/SMS/non-emergency calls, audio routes,
sensors/haptics, suspend/charging/thermal observation, GNSS, owned NFC tags,
Wi-Fi/Bluetooth, then the separate camera paths. Each check's `procedure` lists
the expected measurement. Retain output files for audio/camera and interval data
for power; a screenshot of a service list is insufficient. Do not place emergency
calls as part of this matrix.

For an installed opt-in display-calibration packet, separately record normal
manual brightness response, automatic-brightness transitions, minimum-brightness
rendering and suspend/resume. Capture which display configuration actually loaded.
HBM is excluded until a compatible thermal/timer policy is selected; the retained
stock file alone does not authorize enabling or exercising it.

## Record and validate a result

Replace an attempted check with a record of this form; values below are
illustrative, and the placeholder hash is intentionally invalid:

```json
{
  "id": "camera.aperture.front",
  "status": "fail",
  "observed_at": "2026-09-05T15:00:00Z",
  "observation": "Attempted front selection in the recorded app version; no front selector was exposed. Rear preview worked. See the saved operator note and screen recording.",
  "evidence": [
    {"path": "camera/front-selection-notes.txt", "sha256": "REPLACE_WITH_ACTUAL_SHA256"},
    {"path": "camera/front-selection.mp4", "sha256": "REPLACE_WITH_ACTUAL_SHA256"}
  ]
}
```

Use `shasum -a 256` on each saved file to obtain its hash. Evidence paths must
stay inside the selected directory, including after symlink resolution. All
unattempted checks stay `not-run`; missing check entries also remain `not-run`.
Unknown/duplicate IDs, missing/changed/empty files, unsupported status values,
mixed build identities and incomplete measured records are rejected.

```sh
python3 scripts/hardware_qualification.py analyze \
  --evidence-dir evidence/YOUR_SESSION \
  --build-identity nezha.ACTUAL_INSTALLED_ID
```

The JSON report preserves each operator verdict and identifies excluded claims.
Exit code `0` means all **scoped** checks have recorded passes; `1` means the
ledger is valid but includes failures or unrun checks; `2` means invalid input.
The report intentionally has no overall stock-parity or certification verdict.
Output may include private observations; keep it in ignored evidence/reports.

## Follow the measured failure

Camera gates remain separate: logical/physical mapping, Aperture rear capture,
Aperture front capture, Xiaomi startup, Xiaomi normal capture and OEM modes.
Aperture admission does not create a front selector under logical camera 0.
For Xiaomi startup failures, capture the first actual linker/JNI/service or
permission error, preserve model-specific tuning, and resolve it before testing
mode behavior. A mode aggregate can pass only after every mode named in its
procedure has evidence; narrower results belong in its observation without
promoting the aggregate. Hashes of real still/video output and its metadata are
stronger evidence than preview alone.

For `mi_ext`, record effective mounts/init outcomes and exact property/resource
values separately. Retained vendor fstab may attempt conditional overlays while
the generated first-stage fstab excludes them; neither fact establishes an
unconditional startup failure. Test the actual trigger and resulting mount,
idmap and resource state before restoring any source slice. For CNE/TxPwr, pair
effective grants with an exercised operation and its actual exception/AVC/outcome.
For optional/lazy services, pair the known client trigger with before/after
registration and behavior; absence at one instant is not a missing-HAL finding.

The matrix does not qualify IMS registration, emergency calling, payments,
secure-element app eligibility, DSDS/handover, reverse charging, OEM charge limits
or stock parity. Those require separate scoped procedures. `vendor_wlc` is a
workload-classifier contract; its name is not evidence about wireless charging.

Run offline tooling tests with
`python3 -m unittest discover -s tests -p 'test_hardware_qualification.py' -v`.
Synthetic test fixtures validate ledger handling only; they do not validate
hardware.
