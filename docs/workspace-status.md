# Current Nezha workspace status

**Package7 boots on the Xiaomi 17 Ultra and is the working baseline for fixes.**
On September 5, 2026, the user confirmed that the build is “booted and working.”
The preceding recorded clean-data boot reached Android setup. The earlier
retained-data Package Manager failure and the successful retry remain in the
[first-boot record](package7-first-boot-20260905.md).

This page selects the baseline for ongoing development. The previous 3,124-line
status is preserved unchanged in the [dated status archive](workspace-status-history-20260905.md).
Historical pending gates in that archive describe their original checkpoints.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Build identity | `nezha.128c96ed5e626cdd0d213542` |
| Source record | 549 selected source files; 1,179 project revisions/origins verified during Package7 build, plus reviewed local patches and private inputs |
| Private installed bundle | `artifacts/flash/nezha/package7-20260904-v1/` |
| Bundle manifest SHA256 | `004650a587064b6b9a8438cc69c9ce168f89c2769544498fac51797ad0389308` |
| Signed target-files SHA256 | `ba01cc71fa8122cea665454c194fea540b0a4b6b56a205d7aabc949790704da6` |
| Recovery | TWRP `working76`; preserve its runtime, hardware setup, permissive recovery policy and zero-vibration defaults |
| Normal Android policy | Enforcing source/build baseline; do not change normal Android to permissive |
| Installation observed | Eight Package7 image writes to shared Super and the A boot chain, followed by an explicitly authorized clean-data reset and boot |

The [bundle record](package7-experimental-bundle.md) holds exact image identities
and off-device checks. Its pre-install language is a historical artifact-preparation
checkpoint; the later first-boot record and user confirmation above establish
that the build has since booted. Neither the bundle nor target-files ZIP is an
OTA or TWRP installer.

## Resume development

1. Start from the existing source checkout and Package7 input state. Read
   [source-lock handling](source-lock.md), [device integration](../device/xiaomi/nezha/README.md)
   and [the build host guide](apple-container.md). Inspect `make apple-status`
   before resuming the persistent `evolution-nezha-work` volume; only one VM may
   write it. Recheck disk, host, filesystem and source state before a build.
2. Pick the reported issue, capture its actual behavior when device collection
   is authorized, and make a focused source change. Preserve the booted Package7
   bundle, stock return inputs, working76 rescue, signing key and private build
   inputs as the recovery/reproduction baseline.
3. Run `make test-current` for focused Package7 tooling checks while iterating and
   `python3 -m unittest discover -s tests -v` before completing a change.
   Build a successor into separate outputs with source and artifact identities.
   A tooling test run does not establish a device fix.
4. Record the fix and its observed device result here or in a linked focused
   issue note. Future phone changes still require an explicit user request.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md).
The older full-source TWRP experiments remain historical references.

## Remaining feature work

The user confirmation establishes a working boot baseline. It does not identify
which individual hardware features have been tested. The recorded clean-boot ADB
shell was closed, so that attempt has no machine-read `sys.boot_completed` result.
Capture fresh diagnostics when needed for the next issue instead of treating
older bootloader/setup observations as the phone's current state.

Camera currently selects Aperture; Xiaomi/Leica integration remains separate.
The Android IMS provider stack is not integrated, and VoLTE, VoWiFi and emergency
calling remain unverified. Track device results for networking, display/touch,
audio, fingerprint, sensors, storage/encryption, charging and thermals as work
proceeds. OTA/update behavior and stock restoration remain untested. See
[native features](native-features.md) for the underlying feature research.

Detailed experiments, failures and proof records remain accessible through the
[documentation index](README.md) and [build history](build-progress.md).

The [September 5 cleanup record](workspace-cleanup-20260905.md) lists retired
duplicate expansions and retained originals. Historical replay that names a
retired expansion must first rematerialize it from its retained archive.
