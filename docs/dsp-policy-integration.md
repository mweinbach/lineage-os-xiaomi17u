In a sealed compiler fixture, the authored Nezha DSP policy extension removes one specific conflict:
the strict assembly goes from five failing assertion sites to four while
retaining all **6,366 assertions**. Both compilations still exit 255 and produce
no policy binary. This is a source integration result, not a complete policy,
Treble, ROM build or native-feature pass.

The compact [integration record](../research/dsp-policy-integration.json) binds
the source files, factory inputs, compiler experiment and private receipts.
It extends the preserved [user policy investigation](selinux-user-integration.md);
it does not rewrite that earlier five-site result.

Factory product policy assigns `isolated_compute_app` to
`vendor_hal_dspmanager_client`. The generated Evolution product policy had no
such assignment, even though the retained vendor policy already placed its DSP
service in the set available to isolated compute apps. The lookup therefore
conflicted with the vendor assertion restricting DSP service lookup to clients
and other named exemptions.

The authored files reproduce only the missing interface and membership:

| Authored source | Purpose | Build variable |
| --- | --- | --- |
| [system-ext public attributes](../device/xiaomi/nezha/sepolicy/system_ext/public/attributes) | Declare the existing named DSP client attribute | `SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS` |
| [product-private membership](../device/xiaomi/nezha/sepolicy/product/private/isolated_compute_app.te) | Assign only `isolated_compute_app` to that attribute | `PRODUCT_PRIVATE_SEPOLICY_DIRS` |

The factory declaration appears in system-ext CIL and its vendor-facing public
export; the membership appears in product CIL. The pinned Android build rules
make system-ext public policy visible to both product and vendor compilation.
Named public attributes are not versioned, so this change needs no new
`202504` mapping, core platform public API edit or expansion directive.
The original Xiaomi source filename is unknown; these are authored source
files based on the verified compiled policy and the pinned build interfaces.

The source ownership audit is bound by receipt
`40c54145c834ceaf8257f3252705e2b6524529b56a6ef455739bd7e4716089f4`.
Its source references include
[Android policy layering](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/Android.bp)
and [source-directory selection](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/build/soong/build_files.go).
The reviewed file bytes are copied exactly into this workspace.

The compiler experiment used plain TE insertions at pinned file-order
boundaries in **sealed older userdebug preprocessed source**. It did not run
fresh Soong or m4 evaluation. Trusted `checkpolicy`, the pinned standard
`build_sepolicy filter_out` implementation and `version_policy` produced the
extension fragments. Unchanged-source controls reproduced the original
newline-only system-ext and product outputs before the extension was added.
No handwritten CIL was appended to the original inputs.

The final comparisons each used the complete ten-input assembly: the seven
preserved **user-v7** framework inputs and the three exact factory public,
vendor and ODM CIL inputs. The candidate replaced only the two empty extension
fragments with the compiler-produced results:

| Runtime input | Baseline | Candidate |
| --- | ---: | ---: |
| `system_ext_sepolicy.cil` | 1 byte | 46 bytes: one attribute declaration |
| `product_sepolicy.cil` | 1 byte | 73 bytes: one membership assignment |
| Other eight inputs | Preserved hashes | Byte-identical |

The complete public mapping and both empty extension mappings also remained
byte-identical. The candidate total is 5,361,312 bytes, up from 5,361,195 bytes.
The original ten files remain sealed separately.

Both final compiler commands kept `-m -M true -G -c 30`, with no `-N`, omitted
input, removed assertion or precompiled fallback. Only the DSP lookup failure
disappeared. The two init-property failures and two Binder object-label
failures remain unchanged, including the diagnostic abbreviations showing
four of 35 and four of 32 matching Binder rules. The full assertion multiset
was checked, not just the displayed failures.

The completed second attempt is bound by receipt
`3b60d9a6a45da4bfb843af4bce4c565c5818469eeaf2b934f8eb58a0e4082f6d`;
the immutable preparation plan is
`707802baf20229f97e6696e4727b5c1902f6d7b4144e00e8103916dce1872f50`.
The first loader failure and its outputs were preserved. The second attempt's
77 readback files, totaling 21,042,592 bytes, were rehashed before publication.
Raw CIL, images, logs and the full readback inventory stay private.

No new allow statement is authored, but the membership makes seven existing
vendor rules applicable. Their effective static permission changes are:

| Communication | Added permissions |
| --- | --- |
| `isolated_compute_app` to `vendor_dspservice` | Binder `call`/`transfer`, FD `use` |
| `vendor_dspservice` to `isolated_compute_app` | Binder `call`/`transfer`, FD `use` |
| Isolated compute lookup of the DSP service | None; `find` was already allowed |

These are six new directed permissions across five audited edges, matching
the factory static allow sets. They do not prove native DSP access on
Evolution, camera or voice functionality, or the privacy of isolated compute
data flows. Those require device tests.

The generator exposes this extension only through the explicit
`--dsp-policy-contract research/dsp-policy-integration.json` option on the
existing **factory** `framework-checks` profile. It requires the approved
record hash, pinned source revisions, exact vendor/ODM image identities, the
three captured factory policy inputs and the two reviewed source hashes.
The source revisions are recorded requirements; the host generator does not
inspect the Android checkout or verify that its local patches are applied.
The factory package is user-provided and its origin remains unverified;
neither these hashes nor its internally consistent AVB chain authenticate
the download's origin.

With the option, the generated payload adds the two authored source files,
the approved public record and the corresponding directory wiring.
Without it, the existing twelve-file payload remains unchanged. Standalone
bundle validation checks the copied approved record and authored sources;
it does not reopen private firmware or rerun the policy compiler. No
proprietary policy input is copied into the generated source payload.

The next integration check is a fresh build of an explicitly generated
factory-profile bundle, followed by the complete strict policy check.
The remaining source-level assertion failures, unfiltered permissive-domain
analysis after a binary exists, and complete enforced Treble labeling checks
are still separate requirements. This option does not authorize complete
ROM packaging, flashing or any phone modification.
