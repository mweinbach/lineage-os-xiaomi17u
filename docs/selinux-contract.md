# SELinux inputs and strict stock-policy check

On **2026-08-27**, 60 exact SELinux files were captured from the supplied
modified Xiaomi.eu images, and native Linux ARM64 policy tools were built from
the pinned Android sources. The strict compilation of ten captured CIL inputs
**failed with seven neverallow diagnostics**, exiting 255 at **20:10:04 UTC**.
No policy binary was produced, so permissive-domain analysis did not run.

This result concerns the captured modified package under the recorded compiler
configuration. It does not establish that the connected phone is permissive,
that a native feature is broken, or that Evolution framework policy is
incompatible. The phone was not accessed. The later check with actual Soong
x86-64 host tools is separate and was not performed by this experiment.

The [sanitized contract](../research/selinux-contract.json) records every input
path/hash, compiler and source pin, failed attempt, diagnostic location and
remaining check. Raw CIL, contexts, precompiled policy and detailed logs remain
ignored under the supplied package's `selinux-analysis/` artifact directory.
The [boot contract](boot-contract.md) retains the package's AVB failures and
unverified modified origin; SELinux inspection does not change that provenance.

| Partition | Captured files | Bytes | Selected content |
| --- | ---: | ---: | --- |
| vendor | 14 | 2,361,353 | Vendor CIL, versioned public CIL, policy/genfs versions, contexts and denial metadata |
| ODM | 11 | 1,750,633 | ODM CIL and contexts, precompiled policy, three framework hash files |
| system | 13 | 2,814,626 | Platform CIL, `202504` mapping, two genfs snippets, contexts and hash metadata |
| system-ext | 11 | 713,632 | System-ext CIL, `202504` mapping, contexts and hash metadata |
| product | 11 | 81,752 | Product CIL, `202504` mapping, contexts and hash metadata |
| Total | 60 | 7,721,996 | All captured files rehashed against their receipts |

The guarded EROFS tool used the existing complete inventories and exact logical
image hashes. It captured all regular vendor/ODM SELinux files and the listed
framework inputs into new directories. Older compatibility mappings, `bug_map`
and the separate userdebug platform CIL were not selected. Nothing was mounted,
no firmware executable was run, and no existing capture was replaced. See the
[VINTF contract](vintf-contract.md) for the shared capture tool's safety rules.

Both `/vendor/etc/selinux/plat_sepolicy_vers.txt` and
`genfs_labels_version.txt` contain `202504` followed by a newline. The precompiled
ODM policy header declares binary policy version **30**, MLS and the Android
netlink flags. Only its bounded header and SHA-256 were inspected; the stored
binary was not loaded, installed or supplied to the compiler.

These values agree with the pinned build's policy format version 30 and the
observed product configuration: platform/vendor policy API and genfs version
`202504`, with `SelinuxIgnoreNeverallows=false`. API version and binary policy
format version are different fields. Agreement does not establish compatibility
with every policy rule or with a running kernel.

All three stored hash pairs agree: each framework partition's
`*_sepolicy_and_mapping.sha256` has the same bytes as the corresponding
`/odm/etc/selinux/precompiled_sepolicy.*.sha256` file. However, **none matches a
fresh SHA-256 of its captured CIL followed by its captured `202504` mapping**,
using the pinned build rule's concatenation order. The JSON retains all three
declared and recomputed values.

Each pinned hash genrule has exactly two ordered inputs: its partition's CIL
module, then its current mapping module. **Genfs CIL is not included in these
hash recipes.** The record binds the module names, file paths, source lines and
source-file hash. This reproduces bka's recipe on the captured files; Xiaomi's
original hash recipe and build input ordering have not been verified.

The pinned init implementation compares the stored metadata files before
selecting a precompiled policy; it does not recompute those CIL digests at that
point. Stored-pair agreement therefore does not authenticate the present CIL or
prove it reproduces the precompiled binary. The cause of these discrepancies
was not established, and no hash, CIL or binary was repaired.
[Build hash rules](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/Android.bp),
[init selection](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/init/selinux.cpp)

The native tools use `external/selinux` at
`085c131ad1b984bfa8ffdafee7a976e9d89f403c` and Evolution's `system/sepolicy` at
`e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27`. The final experiment copied 183
tracked regular public source files, totaling 2,228,086 bytes, to
`/work/validation/nezha-selinux-stock-v3`. Original and copied source bytes and
the ten private CIL inputs were rehashed afterward; both source projects stayed
at their pinned commits with clean worktrees.

The installed native GCC 13.3.0, Make 4.3, Flex 2.6.4 and binutils 2.42 built
`libsepol.a`, `secilc` and `sepolicy-analyze`. Tool binaries, compiler backend,
versions, commands and hashes are recorded. The two executables are ELF64
**AArch64**, distinct from Soong's x86-64 Android host tools under Rosetta.

| Attempt | Preserved result |
| --- | --- |
| v1 | Native libsepol compilation stopped on GCC's unused-function error for `cil_attrib_roletype`; no policy compilation |
| v2 | Library and analyzer built, but `secilc` selected installed-header layout without Android's host definition; no policy compilation |
| v3 | Library and both tools built; strict stock CIL compilation reached the seven neverallow failures |

The final native build preserves the Makefile's default flags and adds only
the approved `-Wno-error=unused-function` exception, keeping that warning
visible, plus the pinned Soong `-DANDROID` definition. The exception concerns a
C compiler warning; SELinux rules and checks were not changed. `-DANDROID`
selects the source tree's declared CIL header layout. No substitute header tree
or source patch was created.
[Pinned host definition](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/cc/config/global.go),
[CIL compiler source](https://android.googlesource.com/platform/external/selinux/+/085c131ad1b984bfa8ffdafee7a976e9d89f403c/secilc/secilc.c)

Every command ran through the existing `nsjail`, with Android source and Android
OUT read-only. Only the new validation directory and `/tmp` were writable; the
stock CIL input directory had an additional read-only bind. Native Make used
two jobs, and the strict compiler had a 90-second limit. The preset's writable
proc, unchanged cgroup namespace setting and outer-UID/GID warning remain
recorded. No Soong/Ninja build, package installation or network download was
part of this isolated experiment.

The strict invocation used `-m -M true -G -c 30` and explicit new policy/context
output paths. **It did not use `-N` or `--disable-neverallow`.** This differs
deliberately from init's runtime recompilation arguments: a development check
must retain the neverallow assertions. The ten inputs, totaling 5,403,225 bytes,
were supplied in this order:

| Order | Exact runtime path |
| ---: | --- |
| 1 | `/system/etc/selinux/plat_sepolicy.cil` |
| 2 | `/system/etc/selinux/mapping/202504.cil` |
| 3 | `/system_ext/etc/selinux/system_ext_sepolicy.cil` |
| 4 | `/system_ext/etc/selinux/mapping/202504.cil` |
| 5 | `/product/etc/selinux/product_sepolicy.cil` |
| 6 | `/product/etc/selinux/mapping/202504.cil` |
| 7 | `/vendor/etc/selinux/plat_pub_versioned.cil` |
| 8 | `/vendor/etc/selinux/vendor_sepolicy.cil` |
| 9 | `/odm/etc/selinux/odm_sepolicy.cil` |
| 10 | `/system/etc/selinux/plat_sepolicy_genfs_202504.cil` |

Each path is rooted under the immutable guest `v3/inputs` directory for this
experiment. The captured `202604` genfs snippet has identical bytes but was not
substituted for the selected `202504` input. No `202504.compat.cil` exists in
the inspected stock inventories. The stored precompiled policy was not an input.

| Failed assertion location | Conflicting access reported by the compiler |
| --- | --- |
| Vendor CIL line 9892 | CameraMind and miuibooster finding `vendor_hal_perf2_service` |
| Product CIL line 67 | `vendor_qvirtmgr` adding `vendor_qvirtmgr_service` |
| System-ext CIL line 7093 | `virtual_keyboard` adding `virtual_keyboard_service` |
| Platform CIL line 29504 | `system_server` executing dalvik-cache and APEX ART data files |
| Platform CIL line 15445 | The same two execute grants against a second assertion |
| Platform CIL line 9872 | Updater writes to recovery-cache symlinks |
| Platform CIL line 9871 | Updater writes to cache symlinks |

The seven diagnostics contain ten conflicting allow references. The record
keeps their exact input locations and available original source line markers.
No assertion or grant was filtered to obtain a successful result. The captured
CIL text contains 6,081 top-level neverallow forms and zero `typepermissive`
forms; that inventory is not a substitute for analyzing a compiled policy.
Because the compiler produced no binary or contexts output, the planned
`sepolicy-analyze NEW_POLICY permissive` did not run and has no passing result.

The immutable native v3 receipt is
`selinux-analysis/native-stock-check-v3/receipt.json`, SHA-256
`4170c9a452fc6bf9ab13968be3efb662c649b0346ca4f4ec94ae95b539bb0e73`.
The matching guest receipt is
`/work/validation/nezha-selinux-stock-v3/receipt.json`. Exact input order,
absolute arguments, sandbox arguments and log hashes are preserved there and
in the public record. The ignored `reports/run-selinux-stock-v3.py` records the
guarded one-off procedure; its output directory must be new. v1 and v2 remain
available rather than being overwritten.

The next corroboration is to build actual Soong `secilc` and `sepolicy-analyze`
targets, then repeat the same ten-input strict check with their x86-64 binaries
and a new result directory. That comparison remains separate from this native
record, including if a different compiler produces a different result.

For the first actual Evolution policy compatibility check, build
`plat_sepolicy.cil`, `plat_mapping_file`, `plat_sepolicy_genfs_202504.cil`,
`system_ext_sepolicy.cil`, `system_ext_mapping_file`, `product_sepolicy.cil` and
`product_mapping_file`. Use those seven generated framework inputs together
with the three exact vendor/ODM CIL inputs above, keeping every failure visible.
The current product observation has empty vendor, ODM and system-ext policy
source directories: a successful normal product policy target alone would not
cover the captured Nezha inputs.

Keep `sepolicy_neverallows`, `sepolicy_test` and `sepolicy_dev_type_test` in the
source-policy checks, but label their actual input coverage. After a combined
policy compiles, validate exact file contexts with `checkfc`, properties with
`property_info_checker`, Binder/HwBinder/vndbinder service contexts with the
matching `checkfc` mode, and app selectors with `checkseapp -p`. The record gives
the argument order and additional host targets. Captured contexts have not yet
passed these checks against a new policy.

Run explicit permissive-domain analysis even for userdebug: the pinned build
only performs its automatic permissive-domain rejection on user builds, with
an upstream allowance list. Do not filter a nonempty result into a pass. Kernel
policy loading, enforcing behavior, labeling and native service operation need
separate later tests; none is authorized by this static experiment.
[Pinned policy build checks](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/build/soong/policy.go)
