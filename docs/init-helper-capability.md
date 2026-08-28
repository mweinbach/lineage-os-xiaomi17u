The optional init-helper property capability now has a tested source patch.
It is **not installed in the Android source checkout or enabled by the device
generator**. The patch gives a product an explicit way to omit two permissions
from a new helper without weakening the factory assertions or expanding its
access through the historical init mapping. Its
[metadata](../patches/evolution/init-helper-property-writes.json) records the
exact source, macro tests and remaining adoption requirements.

The pinned framework defines the `init_dev_config` service and process domain
for an optional vendor executable. Its path is selected by
`ro.vendor.init_dev_config.path`, with `exec_start` scheduled before APEX
bootstrap. Its policy grants SET access to `apexd_select_prop` and
`media_variant_prop`. Those grants
conflict with two unchanged factory assertions. An absent or empty selector
conditionally causes a logged failure before execution; a later start can
retry. This is not evidence that the helper can never run on Nezha.

The [patch](../patches/evolution/0004-gate-init-dev-config-property-writes.patch)
adds the explicit `target_init_dev_config_property_writes` M4 value. Undefined
or `true` preserves the original two `set_prop` calls. `false` preserves their
property-file reads and socket permissions while omitting only the two SET
grants. Other values fail with an M4 error. The existing type, transition and
bootstrap-library source prefix is byte-identical; the service invocation,
old `init` and `vendor_init` permissions, assertions and API mappings are not
changed. The choice is not inferred from an Android or board API version.

The captured Make and Soong sources show the supported path from
`BOARD_SEPOLICY_M4DEFS` through the generated `BoardSepolicyM4Defs` list to the
policy M4 command. No current build contains this new definition. Admission
still needs to reject duplicate definitions; relying on M4's final definition
would not provide that guard.

An isolated host-M4 test expanded only the three captured property macros and
the helper's changed suffix. Original, undefined and `true` each produced the
same eight ordered grant occurrences. `false` produced six, with exactly the
two SET occurrences removed and no new grants. Both copies of the socket
permissions were retained. An independent permission-tuple model agreed.
All eleven tested invalid values exited with an error before emitting grants,
and 35 synthetic tests passed with process calls mocked.

This proof used the hash-verified macOS GNU M4 1.4.6, **not Android's build M4**.
It did not expand the unchanged prefix, compile full CIL, link init, modify an
image or run a device. Matching this macro fixture is not a complete policy or
runtime compatibility result. A separate isolated Git application check also
produced the exact expected 1,001-byte source file; the Android checkout was
not used for that test.

The factory input review gives a concrete existing media path to preserve.
Across 253 selected regular vendor/ODM init scripts, property files and SELinux
context files, there were no literal `init_dev_config` references. Four script
statements set the codec and codec-performance selectors from
`vendor.media.target_variant`: two under a property trigger in `init.qcom.rc`
and two under `post-fs-data` in `init.qti.media.rc`. The actual v9 framework CIL
also grants `vendor_init` SET access to `media_variant_prop`. The patch leaves
that authority unchanged. The source property's value and producer, trigger
execution and media behavior have not been verified.

That scan covers 716,487 bytes and does not establish provider absence. Two
selected BoringSSL script symlinks were not followed. Other file names,
partitions, APEX contents, ramdisks, generated properties, init hooks and
runtime boot inputs need their own checks. Earlier property/CIL lookups have
separate, partly overlapping scopes. None proves permanent helper nonuse.

Before source adoption, bind an explicit Nezha capability declaration to the
selected inputs and reject contradictory properties, executable labels or
invocations. Check the final init-hook linkage and alternate boot-script
selection. An unexpected provider must retain visible permission failures;
do not substitute another domain, expand permissions or suppress diagnostics.
A provider contract cannot waive a factory assertion.

The next validation is the Android M4 path and complete policy composition,
with every assertion retained and an unfiltered permissive-domain analysis.
APEX selection, hardware codecs and native camera behavior need separately
authorized device tests. Restricting a permission can expose an unsupported
feature dependency even when policy compilation succeeds. No phone access,
firmware execution or active source/output change occurred in this prototype.
