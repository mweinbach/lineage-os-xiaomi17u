# Evolution backuptool enforcement

The pinned Evolution policy declares `backuptool` permissive unconditionally.
The [narrow source patch](../patches/evolution/0015-backuptool-permissive-only-recovery.patch)
wraps that declaration in the existing `recovery_only` macro. Normal Android
therefore no longer receives this permissive declaration; the approved
recovery-only exception remains. This is a prepared source change, not an
installed policy or a verified backup/OTA implementation.

The [source contract](../patches/evolution/backuptool-enforcing.json) pins
`device/lineage/sepolicy` at `37c13c9b74344c17eddd6067541e9fcba116a34e`
on `bka`. Its sole file is `common/private/backuptool.te`, mode `100644`:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| Original | 152 | `cff90d8a5c7c7dcd3332cf74c1200ebbd0e7feeb8a43dba4bb41f64fe5775ba2` |
| Guarded | 171 | `3a1cb8110f792bc8669e8604c86208f9b8e948486ef2617a64a2a1ef67827e54` |

Only two wrapper lines are added. Every original byte remains in order,
including the type declaration and the complete transition `neverallow`.
The patch does not add permissions, change allowlists or contexts, redefine
macros, or alter the existing `update_engine` transition to `backuptool`.
That normal OTA transition is why removing permissiveness must not be taken
as evidence that addon.d, backup, restore or OTA operations work.

Two isolated host copies reproduce the exact guarded bytes and mode with
`patch` at zero fuzz. A separate host GNU M4 1.4.6 fixture passes 24 exact
expansion cases using the captured platform `recovery_only` definition:

- Both original and guarded source under `user`, `userdebug` and `eng`, each
  with `target_recovery=false`, an absent selector, and literal `true`.
- Six additional non-true values against the guarded user source, none of
  which selects the permissive declaration.

Normal guarded cases contain no permissive statement. Recovery cases retain
every original statement. All cases preserve the type and `neverallow` tokens,
and all M4 stderr is empty. The host fixture expands only that one pinned macro
definition, not the complete platform macro file or Android policy. It neither
uses Android's M4 binary nor runs a policy compiler. The source and macro
captures remain unchanged; receipt and tool identities are in the contract.

A separate independent host check also passes all nine variant/selector pairs
with the complete captured platform macro file. Its 27 M4 commands cover the
macro-only baseline, original source and guarded source for each pair; all
stderr is empty. This corroborates the narrow expansion without using Android's
M4 tool or compiling the selected complete policy.

The twelve [offline tests](../tests/test_evolution_backuptool_enforcing_patch.py)
check exact patch reconstruction, source/mode drift rejection and finite selector
projections. They use only public files and Python's standard library, with no
processes, private inputs, guest or phone. They do not replay host M4 evidence.

Activation still requires a reviewed source composition, fresh Android M4 and
policy builds, strict combined vendor/ODM compilation, context and Treble
checks, and unfiltered permissive-domain analysis with empty output for normal
Android. Image adoption and authorized device tests remain separate. The
working76 recovery input is unchanged; this patch does not alter that tested
prebuilt runtime or claim that a newly built recovery works.
