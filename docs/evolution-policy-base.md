# Explicit Evolution policy base

The ordinary Evolution product includes the pinned Lineage/Evolution SELinux
directories when `LINEAGE_BUILD=nezha` is selected. The earlier framework-check
builds did not contain those contributions in their recorded Soong configuration.
The successful ordinary `nothing` action exposed that difference; it did not
regenerate or validate policy. The old policy outputs remain dated evidence.

`config/evolution-policy-base.json` is an explicit, user-build-only contract for
Android 16 QPR2 `bka`, `bp4a`, board policy API `202504`. It does not select another
platform branch, change the prebuilt-vendor mode, or remove an Evolution directory.
The generator and private policy bundle accept it only with the existing OEM,
property, and framework-provider contracts. Omitting it preserves the previous
device plan, Blueprint rendering, and native checker behavior.

## Native reference and owned additions

The optional device source filegroups name the eight owned policy files and
three owned context files exactly. Comparison modules subtract those filegroups
from the native `se_build_files` system_ext tags. The remaining base comprises
six public policy files, 37 private policy files, and one each of property, file,
and service contexts. Their 46 source selectors, ordering, lengths, and hashes
are required. The backuptool input must be the reviewed 171-byte postimage from
`patches/evolution/0015-backuptool-permissive-only-recovery.patch`; its unchanged
152-byte upstream input remains separately recorded. The patch keeps normal
Android enforcing and limits that permissive declaration to recovery.

The reference uses Android's normal M4/checkpolicy CIL and current-version mapping
producers, including their platform filtering and native validation flags. Its
public exporter is incomplete policy, like the upstream public exporter; it is
not presented as an independently compilable policy binary. The comparison CIL,
configuration, and mapping modules are noninstallable. Native context module
types declare install rules, so their three unique comparison names must stay
out of product package and direct build-goal selections. A native admission must
confirm that these comparison context files were not installed.

`scripts/evolution_policy_base.py` compares the complete actual ten-input policy
corpus with an independent reference assembled in memory from the native base,
the eight unchanged inputs, and the reviewed owned contracts. It never emits or
edits generated CIL. It checks type and role ownership, declaration counts,
named and inherited anonymous attribute memberships, new anonymous definitions,
expansion flags, all access/audit/assertion forms, transitions and other forms,
public type inventory, exact mappings, and full base-plus-owned context rows.
The only additional base/factory duplicate type is the pinned
`vendor_persist_camera_prop`; its source owners, object role, and singleton
`202504` mapping are checked explicitly.

The eight unchanged inputs preserve all 6,366 original assertions byte for byte.
The existing provider contract retains its four registration assertions; the
Evolution base can add further assertions. The checker retains the disabled
init-helper property-write checks and rejects permissive CIL declarations.
Actual strict compilation and unfiltered binary analysis remain separate gates.

The optional base replaces the old platform-only source-membership reference
with the independently produced Evolution base. The existing OEM and provider
ownership, role, mapping, permission, and context checks still inspect the full
actual corpus. The four owned properties' effective ordinary permission budget
is computed from the independent base plus owned contracts, rather than treating
the historical 105-edge result as unchanged. The default profile retains its
original finite budget.

## Native evidence still required

No new native policy or image success follows from the offline implementation
tests. The next ordinary policy phase must bind the actual source history,
configured directories, user variant, helper M4 definition, all new producer
commands and source dependencies, complete contexts, and the strict factory-aware
combined input list. Compiler assertions must not be removed or bypassed.

The planned 32-goal phase includes ordinary `selinux_policy`. At the selected
configuration its dependency closure, together with the two explicit comparison
goals, yields 12 distinct normal policy binaries: source precompiled policy,
platform precompiled policy, the neverallow test binary, seven compatibility
test binaries, framework-only precompiled policy, and the factory-aware combined
binary. Each needs an unfiltered `sepolicy-analyze <binary> permissive` result
with zero exit and empty native output. Upstream compatibility producers retain
their existing neverallow-disabled diagnostic behavior; they are neither strict
neverallow passes nor shipping-policy candidates. Recovery policy remains a
separate approved exception. Fresh execution, reused output, and skipped checks
must be reported separately.

Complete context accounting does not mean unchanged label selection. The pinned
system_ext additions specialize seven factory property prefixes: three camera
package-list entries, three Dolby entries, and one USB UVC payload-size entry.
Actual merged-context label selection and permission effects require a separate
review before image adoption. The owned four-property check does not cover those
new base prefixes. All original factory context and proprietary inputs remain
unchanged.

The newly selected vendor/dynamic policy directories are also preserved in the
ordinary source build. Their contribution has not been delivered into the
retained opaque vendor or ODM images by this reference mechanism. Source-vendor
integration, target-files and image delivery, complete Treble application
labeling, freeze-test freshness, AVB/partition fit, and device behavior remain
independent gates. This contract does not authorize or claim any phone action,
boot, OTA, or complete-ROM readiness.
