The hardened Nezha **user v8 build passed**, and both generated source-policy
binaries have **zero permissive domains** under an independent, unfiltered
analysis. The separate combination with the exact factory vendor/ODM policy
still fails five assertions. These are different results: the source-policy
pass does not establish factory compatibility or enforcement on the phone.
The [public record](../research/user-security-build.json) binds each result to
its own inputs and receipts.

The build completed at `2026-08-28T00:17:18.209127Z` after 6,551 Ninja actions.
It used `lineage_nezha-bp4a-user`, the factory v8 admission, and the existing
user OUT directory. Targets included `init_boot`, `vendor_boot`, DTBO, both
init stages, framework policy, host policy tools and source-policy tests.
Eleven earlier userdebug artifacts remained unchanged; seventeen earlier
user policy/tool/configuration files were copied and verified before reuse.
No source sync, clean build, output reset or phone operation was performed.
Image-content validation is a separate result from this build receipt.

Three narrow source patches were present: Nezha's security property defaults,
removal of the unconditional `permissive su` declaration, and disabling the
known inherited init property-masking helpers while protecting existing
`ro.boot.*` values. A full post-build audit matched all **1,179 project HEADs
and remotes** to the resolved manifest. Exactly 1,176 projects were clean and
the three patched projects had only their recorded changes. This audit did
not repeat the earlier LFS payload verification or inspect ignored files and
authored directories outside Repo.

The actual Ninja process had separate mount, network, PID and user namespaces,
with source mounted read-only and output read-write. No sandbox fallback was
observed. Generated configuration reports `Debuggable=false`, `Eng=false`,
`SelinuxIgnoreNeverallows=false`, `EnforceSELinuxTrebleLabeling=true` and an
empty labeling waiver path. The last two values establish configuration, not
a completed Treble-labeling test; the automatic test dependencies have the
[previously documented API and input gates](selinux-user-integration.md).

| Independently checked policy | Result |
| --- | --- |
| Generated source `precompiled_sepolicy`, 721,536 bytes | Analyzer exit 0; empty output; zero permissive domains |
| Generated `sepolicy_neverallows` binary, 775,106 bytes | Analyzer exit 0; empty output; zero permissive domains |
| Seven new framework CIL files plus three unchanged factory files | Compiler exit 255; five assertion sites; no binary |

The first two checks invoked `sepolicy-analyze … permissive` directly, without
the upstream target's `su`/`backuptool` allowlists or output filtering. Both
stderr streams contain only nsjail's global-root UID/GID warnings, not analyzer
errors. The source precompiled binary is staged under
`odm/etc/selinux/precompiled_sepolicy`; this does **not** replace the policy
inside the retained factory ODM image.

The new platform CIL differs from the preserved user v7 output by exactly
20 bytes: removal of `(typepermissive su)` and its newline. Every other byte
is identical. The other six framework CIL files and all three factory files
also retain their previous hashes. This verifies the narrow compiled effect
of the source patch without changing the historical
[v7 result](selinux-user-integration.md).

The complete ten-file combination contains 5,361,175 bytes. It was compiled
with `secilc -m -M true -G -c 30`, keeping every input and neverallow assertion.
Its five remaining assertion sites cover the missing isolated-compute DSP
client membership, two init-helper property setters, and two Binder rules
that use service-object labels as process domains. The compiler displays
eleven allow locations; this is not the complete Binder conflict inventory.
No combined binary exists, so a permissive-domain check of that combination
cannot pass yet.

All three policy checks used private validation output while source, both
build OUT directories, inputs, tools and provenance remained read-only.
All 22 bound files and source guards were unchanged afterward. The host
readback verified 33 files totaling 14,840,854 bytes; raw policies, logs and
receipts remain ignored. No firmware executable ran and the phone was not
accessed. A complete image set, factory policy/context integration, normal AVB
chain, live bootloader state and native-feature tests remain separate work.
