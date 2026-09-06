# Current Nezha workspace status

**The Package7 feature successor boots on the Xiaomi 17 Ultra and is the
installed development baseline.** On September 5, 2026, it reached completed
Android with retained user data, and the user confirmed fingerprint enrollment
works. Camera remains broken and the on-screen fingerprint icon is malformed.
See the [installation record](package7-feature-successor-install-20260905.md).
The original Package7 first boot remains preserved in its
[dated record](package7-first-boot-20260905.md).

This page selects the baseline for ongoing development. The previous 3,124-line
status is preserved unchanged in the [dated status archive](workspace-status-history-20260905.md).
Historical pending gates in that archive describe their original checkpoints.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Build identity | `nezha.a6d3109ae93158c498bb30b0` |
| Source record | `reports/feature-fixes-20260905/source-installed.json`, SHA256 `20778fdee3c36fa1e42fe53c7c14f8eede047f40531d434e8bc42c5e63892e5b`; original source lock still matches 1,179 upstream revisions |
| Private installed bundle | `artifacts/flash/nezha/package7-feature-fixes-20260905-v1/` |
| Bundle manifest SHA256 | `8550182663180841592a47cc0a33efa5bb7a76f5d70a197faa4d662f47040c1f` |
| Reconciled target-files SHA256 | `26ae30eddfd3716212b08f4c77b9d6674db26c64c8d798e0038208f24331bc9a` |
| Recovery | TWRP `working76`; preserve its runtime, hardware setup, permissive recovery policy and zero-vibration defaults |
| Normal Android policy | Enforcing source/build baseline; do not change normal Android to permissive |
| Installation observed | Shared Super and seven A-chain companion writes; no wipe or slot change; completed boot with Zygote/SurfaceFlinger running and retained user data |

The [feature-successor record](package7-feature-successor-20260905.md) holds its
off-device checks and the [installation record](package7-feature-successor-install-20260905.md)
holds exact written image identities and first device results. The original
Package7 bundle remains rollback evidence. Neither target-files ZIP is an OTA
or TWRP installer.

## Resume development

The existing source checkout and preserved output produced the installed
[feature successor](package7-feature-successor-20260905.md). Its fingerprint,
Aperture and display patches and Xiaomi Camera system-ext candidate are now on
the phone. Fingerprint enrollment works; both camera applications fail and the
UDFPS icon remains visually wrong. Use the [build/cache lessons](feature-successor-build-lessons-20260905.md)
for incremental work: adopt a fresh source/build identity, retain intermediates,
and let Ninja invalidate changed edges. Preserve the original Package7 bundle,
this installed successor bundle, working76 and stock return inputs.

The source checkout is now one step ahead of the installed phone. The
[UI and Aperture follow-up](package7-ui-camera-followup-20260905.md) at source
identity `nezha.376a73a742ddc9da2bdedab3` contains the Aperture initialization
guard and measured UDFPS pixel pitch. A cached 45-edge component build passed
and produced pinned SystemUI and Aperture APKs. No new target-files package,
signing, Super, bundle or installation has been completed, so installed build
`nezha.a6d3109ae93158c498bb30b0` remains the device baseline.

1. Start from the existing source checkout and preserved Package7 input state. Read
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
   Build the next identity with fresh source and artifact records; deliberate
   incremental reuse of the preserved output is the default when its preflight
   passes.
   A tooling test run does not establish a device fix.
4. Record the fix and its observed device result here or in a linked focused
   issue note. Future phone changes still require an explicit user request.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md).
The older full-source TWRP experiments remain historical references.

## Remaining feature work

The successor reached `sys.boot_completed=1` with enforcing SELinux. The user
confirmed fingerprint enrollment works at 21:23 local time on September 5;
framework evidence also records one enrolled print, two successful
authentications and no fingerprint HAL death since boot. The installed
SystemUI's invalid `pixel_pitch=-1` fallback produces roughly 3,074 px of
internal padding inside the 148 px lockscreen icon. A source correction derived
from the device's 419.25723 dpi display (60.58 micrometre pixel pitch) is
absent from the installed build; its separate component result follows below.

The two source corrections now have a successful component build under the new
`nezha.376a73a742ddc9da2bdedab3` identity. They are still absent from the phone;
full packaging, signing, bundle qualification and separately authorized
installation remain required before either runtime result can change.

Aperture and the installed original Xiaomi Camera both still fail for separately
established reasons. Aperture has a mode-selector/configuration initialization
race that throws on a null configuration. Xiaomi Camera reaches a vendor
session-policy abort for operation mode `0x9005` and role 64. Similar provider
aborts appear in the Aperture-era buffer, but the captured evidence does not map
them to an exact Aperture action and they do not cause its earlier Kotlin
exception. Preview, capture, lenses and OEM features remain unverified. See the
installation record above for the exact point-in-time evidence.

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
