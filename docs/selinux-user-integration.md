The actual Evolution `user` framework policy still fails strict combination
with the three exact factory vendor/ODM CIL files: **five assertion sites in
three groups**, with no binary produced. This is a separate, preserved result
from the earlier `userdebug` check. Its 16 debug-specific failures are absent;
the five remaining failures require source integration work. The compact
[record](../research/selinux-user-integration.json) binds the inputs, compiler,
configuration, diagnostics and subsequent static audits.

This page preserves the user v7 snapshot. The later
[hardened v8 source build](user-security-build.md) has zero permissive domains
in both independently checked source-policy binaries, while its complete
factory combination still fails the same five assertion sites. The
[DSP source integration](dsp-policy-integration.md) is a separate, explicit
device-tree option; its compiler fixture is not a fresh Soong build.

The input set also contains one top-level permissive declaration, for `su`.
That is a source/CIL observation, not a successful permissive-domain analysis
of a binary and not evidence about enforcement on the connected phone. Both
the failed result and its original inputs remain preserved.

| Experiment | Assertion sites | Displayed allow locations | Binary produced |
| --- | ---: | ---: | --- |
| Earlier exact factory policy | 1 | 2 | No |
| Earlier Evolution `userdebug` + factory | 21 | 27 | No |
| Actual Evolution `user` v7 + factory | 5 | 11 | No |

The first two results remain in the
[factory framework contract](factory-framework-contract.md). The new check
completed at `2026-08-27T23:02:40.905496+00:00`, using the successful v7
framework/tool build receipt
`5dff46fcbbbe5ffd0d8a8a046ac93c070b61ebf2c63dc70c2ae3dd573df25fc8`.
It used `lineage_nezha`, release `bp4a`, variant `user`, and the fresh OUT
directory `/work/out/nezha-user-policy-20260827T2220Z`. A successful framework
target is not a complete ROM build.

The ten ordered inputs total **5,361,195 bytes**: seven generated framework
files and the same three factory vendor/ODM files used in the earlier check.
Only the platform CIL hash changed among the seven framework files; the four
system-ext/product CIL and mapping files still contain one newline each.
Their inclusion does not establish that device policy has been integrated.

The factory inputs come from the user-provided China fastboot TGZ with SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Its download URL and origin are unverified. The documented internal AVB
checks do not authenticate an OEM trust root or download origin. Original
firmware, CIL, context files, full configuration and compiler logs stay in
ignored storage.

The output configuration was read back and hashed, rather than inferred from
the requested build variant. Its SHA256 is
`e00daa42d329e0c8495079854554dd1f6fe38c348da1a22bc2dfc4381545f3f7`.

| Observed v7 configuration | Value |
| --- | --- |
| `Debuggable`, `Eng` | Both `false` |
| `SelinuxIgnoreNeverallows` | `false` |
| Platform SDK | `36` |
| Platform and board SELinux versions | Both `202504` |
| `EnforceSELinuxTrebleLabeling` | `false` |
| Treble labeling tracking list | Empty |
| Vendor/ODM and system-ext/product policy source directories | Empty lists |

These are historical v7 values. Later hardening must be validated against its
own generated configuration; it does not change this receipt.

The actual Soong-built x86-64 compiler ran under Rosetta in the existing
container. It received `-m -M true -G -c 30`, all ten inputs, and fresh output
paths. No `-N`, omitted input, modified rule, removed assertion or precompiled
fallback was used. It returned **255**, produced no binary or file-context
output, and therefore did not run `sepolicy-analyze`.

The check observed the sandbox's mount flags from inside the namespace before
compiling. Source, both OUT directories, staged inputs and provenance were
read-only. Its only writable backing directory was the fresh
`/work/validation/nezha-selinux-evolution-user-factory-v2`; namespace `/tmp`
was backed by that directory's `tmp` child. Before/after guards covered ten
inputs, seven original framework outputs, four tools, three provenance files
and eleven historical artifacts. All remained unchanged; guard errors were
empty. No new build, VM, firmware executable or phone operation was performed
by this check.

| Remaining group | Assertion location | Conflicting grant or scope |
| --- | --- | --- |
| Isolated compute DSP lookup | Vendor CIL line 6044 | Platform CIL line 43169, from `isolated_compute_app.te:17` |
| Init helper media property | Vendor public versioned CIL line 5931 | Platform CIL line 41740, from `init_dev_config.te:10` |
| Init helper APEX property | Vendor public versioned CIL line 5746 | Platform CIL line 41720, from `init_dev_config.te:9` |
| Binder target is not a process domain | Platform CIL line 24642, from `domain.te:2224` | Compiler displays four of 35 vendor matches |
| Binder source is not a process domain | Platform CIL line 24637, from `domain.te:2223` | Compiler displays four of 32 vendor matches |

The **11 displayed locations are not the full conflict inventory**. An
independent static Binder audit enumerated all 67 matching vendor locations
and reproduced the compiler's 35 + 32 counts without altering any input.
Those locations represent 65 normalized statements, 39 concrete directed
edges and 70 distinct directed permission tuples. These counts describe
different things and must not be substituted for one another.

The Binder endpoints in question are four service-manager labels and one
hardware-service-manager label. All five belong to `object_r`, fall outside
the 596 `domain` members and role-`r` types, and have no process transition,
process allowance or entrypoint match in the inspected assembly. The audit
also checked 34 captured factory context files. These rules cannot authorize
communication between the normally labeled process domains represented by
this policy; that does not prove all possible runtime states or authorize a
live change.

| Service-object label | Statically eligible provider domain |
| --- | --- |
| `connectivity_native_service` | `system_server` |
| `hal_mediaeventgatherservice_service` | `hal_mediaeventgatherservice_default` |
| `hal_mipowerhalservice_service` | `hal_mipowerservice_default` |
| `hal_visdisplaysrv_service` | `hal_visdisplaysrv_default` |
| `vendor_hal_display_config_hwservice` | Four eligible composer-server domains; actual provider unverified |

Correct process-to-process Binder grants already cover the four cases with a
single eligible provider. The display-config case cannot be resolved by
choosing a provider from its name: `rild` has existing matching grants only
for `hal_graphics_composer_default` among the four candidates. The source
direction is to correct the mistaken Binder macro arguments, preserve service
lookup/registration rules and existing process grants, and review the 32
related FD rules. The original vendor macro source is unavailable; its shape
is inferred from CIL expansions. Marking service-object labels as domains or
granting access to every possible provider would not be a justified fix.

The isolated-compute conflict has a separate cause. Factory product CIL line
15 assigns `isolated_compute_app` to `vendor_hal_dspmanager_client`;
Evolution's newline-only product policy does not. Both assemblies already
place the service in `isolated_compute_allowed_service`, and their historical
type mapping agrees. A static experiment restored only the missing client
membership in memory, leaving every input and assertion intact. It changed
two attribute sets and made seven existing vendor rules applicable.

That membership would add Binder `call`/`transfer` and FD `use` in both
directions between `isolated_compute_app` and `vendor_dspservice`. Service
lookup was already allowed, so it adds no `find` permission. All five audited
class/direction edges match the factory assembly and show no assertion
intersection on those edges. This is **not a complete policy compilation**.
Correct product/vendor source ownership, the full policy check and runtime
privacy/native-feature behavior still need validation before adoption.

The proposed historical-init mapping shortcut is unsupported. Factory,
Evolution and pinned compatibility source all map `init_202504` only to
`init`. The `202504.ignore.cil` source explicitly classifies
`init_dev_config` and its executable type as new, with no historical analogue.
The two complete mapping files differ only in three factory
`sysfs_therm_202504` forms, not in init membership.

Adding the helper to that historical attribute would affect 17 attribute
sets, including `mlstrustedsubject`, and 1,414 allow forms. It would also alter
108 assertion sets, excluding the helper from 100 of them, plus 331 transition
forms and 96 MLS-constraint forms. These are affected source forms, not a
count of unique effective permissions. The predicted access includes
filesystem mount/unmount/relabel and executable/transition permissions; it
is much broader than the two property writes under investigation. Preserve
the identity mapping and both assertions.

Pinned `system/core` source supplies an early `exec_start init_dev_config`
before APEX bootstrap. Its service obtains the executable from
`ro.vendor.init_dev_config.path` and uses the helper's process label. The
source comment requires a vendor-supplied bootstrap-Bionic executable. This
does not establish which executable is installed for Nezha or whether both
property writes are needed. Capability-specific source restrictions require
that evidence, not an API-version guess.
[Invocation and service definition](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/rootdir/init.rc#L1349)

The permissive `su` declaration comes from pinned
`system/sepolicy/private/su.te:137`, after the debug macro closes at line 134.
The source file SHA256 is
`aa90a463c2e7a98f749c474f08c864be65467bca8118481de0388e8ce85e924f`.
It appears at platform CIL line 4231 in this failed `user` assembly. The
subsequent [narrow source patch](../patches/evolution/0002-remove-permissive-su.patch)
removes that declaration; it was not part of v7 and does not retroactively
make this check pass.
[Pinned declaration](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/private/su.te#L137)

An ordinary upstream target passing would not establish zero permissive
domains. Its binary rule checks only non-debuggable, non-recovery builds and
filters module-specific allowlists: the precompiled target permits
`backuptool` and `su`, and the base-platform target permits `su`. The
compatibility generator also has its own neverallow-disabled/allowlisted
test path; that was not used by our strict compiler. After a strict combined
binary exists, independently run an **unfiltered** permissive-domain check
and require an empty result for both authorized Nezha variants.
[Binary rule](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/build/soong/policy.go#L542),
[Target allowlists](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/Android.bp#L718)

The observed Treble-labeling flag has a different purpose from the strict
compiler's neverallow check. Kati's `core/Makefile:3542` and Soong's
`filesystem/android_device.go:1950` append `--treat_as_warnings` unless the
product flag is true. The labeling test then downgrades ordinary violations
and omits their failure exit. A nonempty `treble_labeling_violators` attribute
on a user build remains a separate hard error even in warning mode.
[Kati consumer](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/Makefile#L3542),
[Soong consumer](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/filesystem/android_device.go#L1950),
[Test behavior](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/tests/treble_labeling_tests.py#L519)

Explicitly enabling the product flag is appropriate hardening, but it does not
prove the test runs. Both automatic build dependencies require platform
SELinux version `202604` or later; this output reports `202504`. Both consumers
can also write a skipped-test timestamp when required inputs are missing,
even with the flag enabled. The needed inputs include platform/vendor app
lists, app contexts, vendor file contexts, combined and framework-only policy
binaries, and `aapt2`. Require an actual non-skipped check with complete inputs,
the real API values and no waiver list. No Treble-labeling test was executed
or passed by the v7 compiler experiment.

The strict user receipt is
`artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/selinux-evolution-user-check-v2/receipt.json`,
SHA256 `e544850869664a710bdf3ab1eb34975fe309723055a35a2bbe5e53b4139ed98e`.
The public record binds the complete private source, static-analysis and
readback receipts without redistributing their inventories or proprietary
rules. Workspace tests verify this metadata; they are separate from a full
image build, VINTF/context checks, policy loading and separately authorized
device tests of boot, enforcement and native features.
