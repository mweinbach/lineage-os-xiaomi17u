**Historical checkpoint — August 28, 2026.** This page records the v9 DSP
source build and its four remaining assertion failures with unchanged factory
policy. The later native user source/M4/vendor-policy build passed; see the
[current policy integration](policy-source-integration.md) and its
[result record](../research/policy-source-integration.json). That later pass
does not establish complete context/Treble validation, image adoption or
hardware support. The original v9 results remain unchanged below.

The Nezha **user v9 policy build passed**, and the complete factory-policy
check now fails **four assertions instead of five**. The missing DSP client
membership is resolved through actual Soong source integration. Both generated
source-policy outputs have zero permissive domains under unfiltered analysis.
The complete factory combination still produces no binary, so this is not a
factory-policy compatibility pass or a boot result.

The [public result record](../research/dsp-policy-build.json) binds the build,
installation, sealed inputs, diagnostics and source audit to separate receipts.
It does not rewrite the earlier [source experiment](dsp-policy-integration.md)
or [v8 results](user-security-build.md). The experiment used preprocessed
fixtures; v9 evaluates the two authored source files through Soong and its
normal policy pipeline.

The optional `--dsp-policy-contract` input produced a fresh v9 candidate with
three additional files and one changed generated Board configuration. The
other eleven candidate files were identical to v8. Installation atomically
exchanged only the device directory and preserved its previous version. All
63 output guards and the existing vendor/kernel receipts remained unchanged;
installation wrote no build output. The policy declaration belongs in
`SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS`, and the isolated-compute membership belongs
in `PRODUCT_PRIVATE_SEPOLICY_DIRS`. No new allow rule or platform API mapping
was introduced. The membership extends existing vendor Binder and file
descriptor grants to include `isolated_compute_app`.

The build completed at `2026-08-28T01:26:15.353358Z` after **201 Ninja actions**.
Its **16 targets** cover source policy, seven framework CIL/mapping outputs,
host policy tools and source-policy tests. It reused the existing user OUT
without a sync, clean build or output reset. It requested no image or ROM
packaging target. Thirty-three previous user files were preserved before reuse;
the eleven earlier userdebug artifacts, sealed v8 snapshot and twelve retained
v8 boot artifacts remained unchanged. These preservation sets overlap and are
not a count of newly built images.

Actual configuration is `lineage_nezha-bp4a-user`, with `Debuggable=false`,
`Eng=false`, `SelinuxIgnoreNeverallows=false`,
`EnforceSELinuxTrebleLabeling=true` and an empty labeling waiver path. Soong
reports both intended source directories, and its two CIL fragments exactly
match the prior experiment. The policy API remains `202504`. The labeling
flag is configuration evidence; it does not establish a completed Treble
labeling test under the [documented dependency gates](selinux-user-integration.md).

| Separately checked output | Result |
| --- | --- |
| Source `precompiled_sepolicy`, 721,536 bytes | Analyzer exit 0; empty output; zero permissive domains |
| Source `sepolicy_neverallows` binary, 775,162 bytes | Analyzer exit 0; empty output; zero permissive domains |
| Seven v9 framework CIL files plus three unchanged factory files | Compiler exit 255; four assertion sites; no binary |

The first two analyses directly ran `sepolicy-analyze … permissive` without
the upstream target's permissive allowlists or output filtering. The source
precompiled binary has the same hash as v8; the neverallows binary differs and
is 56 bytes larger. Both were read from the completed v9 build. The precompiled
output under `odm/etc/selinux` does not replace the policy inside the retained
factory ODM image, and neither analysis establishes enforcement on the phone.

The full ten-file assembly contains **5,361,292 bytes**. It was checked with
`secilc -m -M true -G -c 30`, retaining every input and assertion. Compared with
v8, five framework files and all three factory files are byte-identical. Only
the system_ext declaration and product membership changed: their new fragments
are 46 and 73 bytes, replacing one newline each. The complete assertion forms
remain identical: **5,976 `neverallow` plus 390 `neverallowx`, totaling 6,366**.
This was checked by parsing the saved inputs, not just by counting compiler
diagnostics.

The failure at factory `vendor_sepolicy.cil:6044` is absent. Its assertion
remains present; the added client membership resolves the conflict. The four
remaining diagnostics match v8 exactly after normalizing snapshot paths:

| Remaining group | Assertion locations |
| --- | --- |
| Init helper property setters | Factory `plat_pub_versioned.cil:5931` and `:5746`; displayed framework allows come from `init_dev_config.te:10` and `:9` |
| Binder service-object labels used as process domains | Framework `plat_sepolicy.cil:24641` and `:24636`, from `private/domain.te:2224` and `:2223` |

The compiler displays ten allow locations. That is not the complete Binder
conflict inventory. No assertion was removed, init API mapping broadened,
factory CIL edited or check disabled to reach this result. There is no combined
binary on which to run a permissive-domain analysis yet. Correct integration
of these remaining groups, complete policy/context and VINTF checks, and the
rest of the ROM image set remain work before a device build can be admitted.

The actual build had separate mount, network, PID and user namespaces, with
source read-only and output writable; no sandbox fallback occurred. The three
later policy checks used only sealed inputs, with source, both OUT directories
and all sealed inputs/tools/provenance read-only. Their sole writable backing
directory was fresh validation storage, including the namespace's `/tmp`.
All 29 file guards remained unchanged. Host readback verified 28 input/tool/
provenance files totaling 14,838,838 bytes and nine diagnostic/observation files
totaling 8,180 bytes.

A separate audit after the strict check matched all **1,179 project HEADs and
remotes** to the resolved manifest. Exactly 1,176 projects were clean, with only
the three expected patched projects accepted. The three patches affect four
files; their hashes are unchanged from v8. This audit did not repeat LFS
payload verification or cover ignored and authored directories outside Repo.
The device sources have their own installation/build hash guards.

The factory package remains user-provided with unknown URL and unauthenticated
origin; internal AVB validation does not authenticate its source. The retained
kernel input bundle still has Xiaomi.eu provenance. Raw policy, binaries and
logs remain ignored. No firmware executable ran, no phone was accessed, and
DSP/native-feature behavior, a complete ROM and device boot remain unverified.
