# Current-provider 4 KiB source integration

The user explicitly approved a 4 KiB bring-up baseline after the initial
16 KiB provider checks failed. The new optional
`config/nezha-page-size-profile-v2.json` binds the admitted stock kernel and
provider-v7 inputs. It does not change the default 16 KiB profile or rewrite
the earlier held v1 descriptor and v13g candidate.

The corrected **v13ja source transaction committed at 2026-08-31 00:07:36 UTC**,
and its normal **37-goal `pagesize-v13j-1` build passed at 00:43:11 UTC**
(August 30 in New York). The captured settings differ in exactly one of 254
fields: the maximum changes from 16384 to 4096. Strict prebuilt and ELF checks
remain enabled. The build logs contain 4,890 Ninja action descriptions after
163 frontend steps; these are not counts of tests.

All 204 guarded source inputs match the admitted configuration. The thirteen
protected policy identities and eleven runtime identities are unchanged,
allowing reuse of the existing strict policy analysis without claiming a new
assertion recount. The rebuilt allocator has four 4096-aligned load segments.
The partial VINTF alias explicitly skips the matrix-definition subcheck for a
matrix with no level. Fresh provider ELF checks, full framework/vendor/kernel/
APEX compatibility, packaging and boot remain open. The
[native integration record](native-rom-integration.md) binds the actual result,
54 captured file bodies, 36 APEX metadata records and scoped reviews. The first
failed inactive v13j stage and all earlier 16 KiB evidence remain preserved.

Select this successor with the existing `--page-size-profile` argument. The
generator admits only the two reviewed profile IDs, exact descriptor hashes
and canonical candidate paths. Without that argument, neither profile is read
or inferred from the provider receipt. The standard product settings are:

```make
PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096
PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE := true
PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO := true
```

The pinned build uses that maximum for both newly linked platform binaries and
prebuilt alignment checks. ELF dependency, symbol and alignment checks remain
enabled. No module ignore flag, fake API level, low-RAM setting, test exclusion,
kernel boot-mode claim or normal Android SELinux change is introduced. The
known 22 provider alignment gaps against the 16 KiB/VTS requirement remain
recorded as unresolved; the new selection is a narrower bring-up baseline.

All 26 original provider identities remain separately bound. The existing
provider-v7 Miracast dependency correction is admitted through its complete
reviewed derivation, including evidence, original and derived hashes, and byte
offset. A single effective-file override records that derived output; its
module, runtime path and load alignments must match the original row. The
generator does not alter or relabel proprietary inputs.

The first candidate extends the current v13i source configuration only. It adds
the v2 descriptor, changes only `generated/device-candidate.mk`, and records the
new page-size binding in admission. Allocator, policy, provider, kernel,
recovery, mi_ext, factory inputs and pinned upstream composition remain the
same. Portable validation checks the approved profile ID/path pair before
opening the descriptor and rejects crossed profiles or arbitrary paths.

The maintained policy-image delivery capability from `e304faa` cannot yet be
combined with either page profile. Its current-policy/source evidence belongs
to the earlier 16 KiB configuration. That rejection stays in generation and
portable validation; fresh native policy equality and a reviewed paired
delivery admission are required before combining them. No existing metadata,
image or source receipt is rewritten to imply that validation occurred.

Offline tests cover the explicit successor, unchanged default rendering,
canonical path enforcement, stale provider bindings, changed derivation or
effective layout, original-versus-derived identity confusion, and delivery
rejection. Host generation and repeated candidate equality remain different
evidence from normal Android policy/ELF/component builds. Source installation,
native checks, full VINTF, image packaging, signed AVB, OTA, partition fit and
physical-device testing remain separate steps. Complete-ROM readiness and
hardware-tested flags stay false.
