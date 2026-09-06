# Current Nezha workspace status

**The Package7 UI, camera and shade successor (`f9e`) is the installed
development baseline.** On September 6, 2026, it reached completed Android boot
with enforcing SELinux and the intended UI resources loaded. Post-unlock
retained-userdata access, UDFPS and shade visuals, and camera behavior remain
unverified for this installation. See the
[installation record](package7-f9e-install-20260906.md).
The earlier [feature-successor installation](package7-feature-successor-install-20260905.md)
and [original Package7 first boot](package7-first-boot-20260905.md) remain
preserved evidence.

This page selects the baseline for ongoing development. The previous 3,124-line
status is preserved unchanged in the [dated status archive](workspace-status-history-20260905.md).
Historical pending gates in that archive describe their original checkpoints.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Installed build identity | `nezha.f9e30611efe01b882f9ed0cb` |
| Installed build source evidence | [Preserved f9e source and build record](package7-ui-camera-followup-20260905.md); 574-row inventory, SHA256 `abaa6c525a6b2e628c7ac48d0a4015e43d43d331b3244b8282103d02a6cd27fc` |
| Development source selection | `nezha.bc6311b1a714e310eaf1af56`; see the [source-merge record](feature-candidates-build-merge-20260906.md), separate from the installed build |
| Private installed bundle | `artifacts/flash/nezha/package7-ui-camera-shade-20260906-v1/` |
| Bundle manifest SHA256 | `78693f3eb040b61dd7972bf4e432ab9d8f9000e7c6d1b433373f41a1711e4c85` |
| Reconciled target-files SHA256 | `4cd1374be9370a81b505b72eadd79fcceecd777b3fed1618e725742802f76bd8` |
| Recovery | TWRP `working76`; preserve its runtime, hardware setup, permissive recovery policy and zero-vibration defaults |
| Normal Android policy | Enforcing source/build baseline; do not change normal Android to permissive |
| Installation observed | Shared Super and seven A-chain writes acknowledged; normal reboot, no wipe or slot change; completed boot with Zygote/SurfaceFlinger running; post-unlock retained-userdata access not yet established |

The [preserved build record](package7-ui-camera-followup-20260905.md) holds the
off-device checks and the [installation record](package7-f9e-install-20260906.md)
holds the authorized write scope and first device results. The original
Package7 and a6d bundles remain predecessor/rollback evidence. These private
bundles and target-files ZIPs are not OTA or TWRP installers.

## Resume development

The [roadmap](roadmap-20260906.md) orders the remaining work and records the
September 6 decisions: populate both slots, private audience, source kernel as
the design goal with the prebuilt kernel kept selectable.

**September 6 build-variant opt-in:** the construction guard now admits
`userdebug` only through an explicit invocation opt-in; `user` stays the default.
See the [build-variant opt-in record](build-variant-opt-in-20260906.md). It is a
source and runner change, not a build or installation.

**September 6 source update:** the feature branch is now merged into main and
the existing Linux checkout under identity `nezha.bc6311b1a714e310eaf1af56`, with
603 hash-verified source inputs. Display, Dolby, haptics, camera scheduling and
refresh candidates are selected; the IMS provider and workload classifier stay
disabled. No native build or installation was performed by this merge. Use the
[source-merge record and new runner](feature-candidates-build-merge-20260906.md)
for the next build. The f9e source/build records below are preserved predecessor
evidence, not the current source selection.

The existing source checkout and preserved output produced the
[a6d feature successor](package7-feature-successor-20260905.md) and the later
installed baseline selected above. On a6d, fingerprint enrollment worked,
both camera applications failed and the UDFPS icon was visually wrong. The
latest installation has not yet established post-unlock feature results. Use
the [build/cache lessons](feature-successor-build-lessons-20260905.md) for
incremental work: adopt a fresh source/build identity, retain intermediates,
and let Ninja invalidate changed edges. Preserve the original Package7, a6d
and current installed bundles, working76 and stock return inputs.

The source checkout is ahead of the installed phone. The preserved
[UI and Aperture follow-up](package7-ui-camera-followup-20260905.md) at source
identity `nezha.376a73a742ddc9da2bdedab3` contains the Aperture initialization
guard and measured UDFPS pixel pitch. Its cached 45-edge component build passed
and produced pinned SystemUI and Aperture APKs. Commit `0784f4d` subsequently
added the Nezha portrait shade-header alignment source. The f9e 574-row
source inventory has SHA256
`abaa6c525a6b2e628c7ac48d0a4015e43d43d331b3244b8282103d02a6cd27fc`
and build identity `nezha.f9e30611efe01b882f9ed0cb`. The installed-source and
native pre-build and post-build inventories are byte-identical at those 574
rows. Its native SystemUI build completed successfully in 51 Ninja edges and
produced a host-matched APK. Its fresh full target-files package, verified
signing chain, Super assembly/readback and host qualification have now completed
off-device. The private eight-image bundle passed assembly and verification;
those historical receipts deliberately stop short of device admission. The
subsequent [authorized installation](package7-f9e-install-20260906.md) establishes
the current installed baseline and completed first boot, separately from those
off-device checks.

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

On the a6d predecessor, the user confirmed fingerprint enrollment worked at
21:23 local time on September 5; framework evidence also recorded one enrolled
print, two successful authentications and no fingerprint HAL death since boot.
That build's invalid `pixel_pitch=-1` fallback produced roughly 3,074 px of
internal padding inside the 148 px lockscreen icon. The current installation
loads the corrected `pixel_pitch=60.583`, derived from the device's 419.25723 dpi
display, along with the intended shade configuration. Post-unlock UDFPS and
shade visual checks remain pending; loaded resources do not establish rendering
correctness or fingerprint behavior.

The Aperture and UDFPS source corrections first passed a component build under
the preserved `nezha.376a73a742ddc9da2bdedab3` identity and were included in the
installed successor. The `nezha.f9e30611efe01b882f9ed0cb` source also adds a
Nezha-only portrait shade-header inset. It preserves the approved normal status
bar's 100px horizontal content padding and 38px top padding, and leaves the new
behavior disabled by default outside the Nezha overlay. Its SystemUI build is
complete: native run
`/work/validation/feature-fixes-builds-20260905/20260906T022159` returned exit 0
after 51 Ninja edges, and the native and host SystemUI APKs independently match
at 51,257,403 bytes with SHA256
`7572a603498a18ff0bcf418e1819eb49f86d51ce718dbd9c8054d06dd3902ecf`.
The unchanged Aperture APK remains 8,311,019 bytes with SHA256
`a80bbe6322cfb2aa2b7cbd0bd683ecc07c18039b07144fba617359968f0667cd`.
Host `aapt2` resolves the compiled opt-in to true alongside
`pixel_pitch=60.583`, 100px rounded-corner content padding and 38px status-bar
top padding.

The fresh full `f9e` target-files build completed with exit 0 in native session
2162 after its passing preflight for the same persistent VM, output and manifest
head `cc4ebb8db9750afba6049825127304b09327f7c1`. The admitted native archive is
11,277,109,433 bytes with SHA256
`cc8304be1bd04670de6505a938bdcc3f0f16e4c472f68b4f6a73df63e2803057`.
The reconciled signed archive is 11,100,598,098 bytes with SHA256
`4cd1374be9370a81b505b72eadd79fcceecd777b3fed1618e725742802f76bd8`,
and its signing receipt reports a fully verified chain. Its packaged SystemUI
and Aperture members exactly match the focused component artifacts.

Super assembly and LP eight-image readback passed with logical and physical fit.
The compressed sparse Super is 9,446,504,548 bytes, expands to 15,300,820,992
bytes and has SHA256
`fd6fcfe734ffbc2b172049d0c34d61fc3df5bcfdeba740407fe708e358bd0551`.
The second host transfer completed with matching native final hash, complete
host stream and host readback. Its predecessor remains a preserved failed
partial transfer whose full-ancestor guard fired without recording the exact
changed ancestor or field. This remains off-device artifact evidence: the LP
readback receipt does not claim functional Super verification. FEC qualification
subsequently closed through a
read-only recovery collector without rerunning native parity: all eight native
checks and 42 finite readbacks passed with source574 unchanged, final idle state
and the sole VM owner. Its completion receipt has SHA256
`e1a7484fcd22e984b01cbb33ce17c21c0810796468c4f0d9c4d724540111d8aa` and
the semantic admission has SHA256
`2ba3f467561fe7c1b53bed430d9c564ee79ea539a456e718a09cda343fd71a37`.
The initial collector failure remains preserved; its transport did not pass.
Host APK, boot, delivery and classpath qualification then completed with the
documented APK findings retained. The aggregate admission binds the unchanged
574-row source cohort, 15 native target-files roles and 17 signed roles; exact
working76 preservation, the four focused delivery bytes, 456 API 36 signature
and 4 KiB APK alignment checks, and 70 resolved classpath JARs all passed.
The preserved off-device admission leaves complete-ROM readiness false. The
later installation establishes first boot and loaded UI resources, not full
readiness: post-unlock userdata access, SystemUI shade geometry and visual
behavior, runtime app loading and permission grants, camera operation and
fingerprint icon geometry still need measured validation.

The final private bundle is
`artifacts/flash/nezha/package7-ui-camera-shade-20260906-v1/`. Its assembly and
independent verification receipts passed with exactly eight payloads. The
8,240-byte manifest has SHA256
`78693f3eb040b61dd7972bf4e432ab9d8f9000e7c6d1b433373f41a1711e4c85`.
Its historical assembly status remains
`byte-identities-verified-not-device-admitted-not-flash-ready`; do not rewrite
that receipt to imply it performed device admission. The separately authorized
[installation record](package7-f9e-install-20260906.md) supplies the later write,
reboot and first-boot evidence. Future phone changes still require explicit
authorization. The joined off-device qualification summary is
`reports/feature-fixes-20260905/shade-followup/qualification-summary.json`,
5,918 bytes with SHA256
`94020ef08a74c10c5924d9358e5023ef2a8edc364e72b9c8ae379146c683d0bd`.

The recorded full offline suite, including the exact f9e `system_ext` admission
contracts from commit `954bac6`, passed all 4,647 tests in 195.747 seconds. This
is tooling and source-contract evidence, not an on-phone result.

The predecessor's Aperture and original Xiaomi Camera tests failed for
separately established reasons. Camera behavior has not been revalidated after
the current installation. One Aperture process hit the mode-selector/configuration
initialization race that throws on a null configuration. In the later unlocked
foreground attempt, the persistent Aperture process successfully opens public
Camera0, then Xiaomi's vendor stack fails the normal preview-plus-JPEG stream
configuration while constructing the internal logical camera 4 multicamera
graph. That post-open failure includes an empty camera-role set, physical-to-role
mapping failures and a missing `MCXSuperFG` sink port; the Aperture null guard
does not resolve it. Xiaomi Camera separately reaches a vendor session-policy
abort for operation mode `0x9005` and role 64. Preview, capture, lenses and OEM
features remain unverified. See the
[predecessor installation record](package7-feature-successor-install-20260905.md)
and its linked follow-up for the exact point-in-time camera evidence.

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
