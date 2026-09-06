# Feature candidates merged into the build environment — September 6, 2026

The user requested merging `codex/nezha-feature-fixes` into the build environment.
Git merge `1c58422` combines feature head `6a4fcc9` with main `3076a4c`, retaining
main's newer camera, UI, packaging and qualification work. The existing Linux
checkout now selects these candidates under source identity
**`nezha.bc6311b1a714e310eaf1af56`**. No native build or phone operation was run.

## Selected source

The same sole-writer VM, `twrp-nezha-upstream74-20260829`, retains
`/work/evolution` on the case-sensitive ext4 `evolution-nezha-work` volume.
Preflight found no live Soong/Ninja/Kati build; the two old Ninja zombies were
not active writers. At that checkpoint the guest had approximately 208 GiB
free and the host 207 GiB free. These are not reserved build capacity.

Five flags are explicitly true in the source product before device inheritance:

- `NEZHA_CALIBRATED_DISPLAY`: exact-panel normal/automatic brightness packet;
  HBM remains withheld and saved-slider interpretation changes.
- `NEZHA_DOLBY_CONTROLLER`: manual controls for the preserved vendor effect;
  no replacement backend or automatic state restoration.
- `NEZHA_HAPTICS_CONTROLS`: framework intensity controls and keyboard toggle;
  factory calibration, default intensities and waveforms remain unchanged.
- `NEZHA_CAMERA_TASK_PROFILES`: the two reviewed camera cgroup joins, not
  Xiaomi's unavailable proprietary scheduling policy.
- `NEZHA_REFRESH_POLICY`: 120 Hz normal/peak defaults without saved-setting writes.

The exact add-only `TelephonyBaseUtilsStub.isMiuiRom()` API is also installed in
framework source. **The IMS provider is not enabled.** Its disabled templates
and the radio, power and memory measurement tooling are merged into the host
workspace. `NEZHA_WORKLOAD_CLASSIFIER` is explicitly false; its unresolved
signing, native/JNI, permission and component-boundary gates remain intact.
No memory, voltage/frequency, thermal or charging policy was fabricated.

## Transaction and preservation

The reviewed rollback-capable source transaction was reused with a new request
and result namespace, rather than its old host receipt writer. It held the
existing exclusive build lock, checked every baseline byte/size/mode, rejected
unreviewed existing destinations and symlinks, retained preimages and verified
the complete final inventory.

There are 25 selected additions/replacements and 603 final inventory rows.
All 574 previous paths remain; only the old `device.mk` and `lineage_nezha.mk`
entries changed. Six existing platform prerequisite files were additionally
hash-bound. The other changes are new candidate files and the private display
packet. Camera, fingerprint, shade, generated/private inputs, recovery, AVB,
SELinux and 4 KiB policies from the preceding source remain preserved.

Private records:

- Host: `reports/feature-merge-20260906/`, containing the preparation script,
  source request, original source snapshot, transaction and installed receipt.
- Guest: `/work/validation/feature-candidates-source-20260906-v1/`, containing
  preimages, `before.json` and `after.json`.
- New host `source-installed.json` SHA256:
  `c4a7d55d6c3ea3c5fe7d51450a354bc15c358a616bbee2f3ab0f1ae0aa2731f9`.
- Old `reports/feature-fixes-20260905/source-installed.json` remains unchanged,
  SHA256 `abaa6c525a6b2e628c7ac48d0a4015e43d43d331b3244b8282103d02a6cd27fc`.
  It remains f9e evidence, not the current source selection.

The uncommitted installation note/index change and concurrent `AGENTS.md`
changes were preserved and not included in this integration's commits. No
source sync, cleanup, output replacement, signing or device access occurred.

## Next build and validation

Use the new private runner, not the f9e runner:

```sh
python3 reports/feature-merge-20260906/build_successor.py nothing
```

This is a future command, **not an executed result**. The adapter reads the new
603-row receipt, uses a new native run namespace, and intentionally retains the
existing output alias and Go cache according to the
[incremental-build policy](feature-successor-build-lessons-20260905.md).
It preserves source checks, the exclusive lock and the 200 GiB guest reserve.
Recheck host capacity, sole writer, source and output state before invoking it;
the small margin above the guest reserve is not a full-package capacity proof.
The next actual build may update mutable intermediates, but this merge did not.

The complete merged offline suite passed **4,820 tests in 254.378 seconds**;
the log is `reports/feature-merge-20260906/all-tests.log`. A standalone Make
admission check inside the VM passed the display hash checks, actual camera
source guards, three overlay selections and Dolby package selection. It did
not execute Soong or compile an Android component. The new runner and its
embedded guest passed Python syntax parsing; they have not been executed.

An independent read-only review rehashed all 603 guest source files, recomputed
the build identity, checked five flag selections, verified the exact IMS API
and confirmed preservation of the predecessor receipt and unrelated sources.
Native compilation, final-image delivery and hardware/performance results are
still required. Historical f9e qualification does not qualify this successor.
