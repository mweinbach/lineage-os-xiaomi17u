# Explicit framework-provider source admission

The device generator can select the reviewed Sigma and QCC framework providers
through an explicit source capability. This is an offline configuration step;
it does not prove a native ELF check, policy compilation, image adoption,
service startup or hardware feature. The `framework-checks` target-files and
flash restrictions remain unchanged.

Pass both `--framework-provider-policy-contract` and
`--framework-provider-inputs-receipt` to
[`generate_device_tree.py`](../scripts/generate_device_tree.py), alongside the
existing factory, DSP, init-helper, OEM policy and native policy input arguments.
The four-property OEM profile is optional. The native policy bundle must have
been staged with the same provider policy contract and the same actual external
provider receipt; a copied provenance record cannot substitute for that bundle.

For the reviewed inputs, the additional arguments are:

```sh
--framework-provider-policy-contract config/nezha-framework-provider-policy.json \
--framework-provider-inputs-receipt artifacts/framework-providers-20260829/bundle-v6/framework-provider-inputs.json
```

Generation verifies the complete private provider bundle, then passes its actual
receipt to the native policy bundle verifier. Both returned provider records
must match in full. It checks the selected executable, init and VINTF identities
against the policy contract, and preserves the helper, factory, platform and
source-revision bindings. See the [provider input boundary](framework-providers.md)
and [private policy contract](../config/nezha-framework-provider-policy.json).

The generated device changes are limited to:

- The unchanged verified module Blueprint at
  `device/xiaomi/nezha/framework-providers/Android.bp`.
- The four reviewed private policy files in
  `sepolicy/system_ext/framework_providers/private`: two TE sources,
  `file_contexts` and `service_contexts`.
- One private policy directory selection in generated Board configuration and
  one product inheritance of the verified bundle's `framework-providers.mk`.

That inherited makefile owns both namespaces and its 27 installable modules
plus the native input checker. The generator does not recreate these lists or
redirect native consumers to raw proprietary files. The module Blueprint keeps
strict ELF validation, undefined-symbol rejection, original installation names
and tagged verified producer outputs. The eight provider types remain private;
there are no new public API mappings. The source lock and narrow mDNS visibility
patch are copied as public inputs, but generation does not apply the patch.

Portable candidate validation reconstructs every provider file identity that
can be derived from the pinned profile, including the native producer,
verification program, module Blueprint and product makefile. It also checks the
canonical provider receipt digest. This prevents jointly edited portable
provider and policy records from changing those controls. It rechecks source
statements, exact file sets and sole ownership of module and policy wiring,
without claiming to reopen private bundles unavailable at the destination.
The destination must still verify the actual private inputs before building.

During generation, private bundles are reverified before publication, including
their exact file and directory inventories. Output nested in either provider
or native policy input bundle is refused before any directories are created.
Inputs are never replaced or hard-linked into the generated candidate.

## August 29 host checkpoint

The v13 candidate and a separate repeat were generated at **21:44:10 UTC** from
the preserved v12 inputs, provider bundle-v6 and the composed native policy
bundle. Both admission files are 96,907 bytes with SHA256
`2a3f5f1f12ed9a4c26fac456007e11e2899474b7bdda2fb3187baa2237ab0e29`.
The provider receipt remains
`8847765ce31f0ce2cdca5f4973153a95a0336363783e4d80c8f0c9d685de2b28`;
the composed policy receipt is
`950daa1f1e39e8c95748d7b29ba0cdc251fa2dbd2e5c67f8efa7be827e96645a`.

Compared with v12, only the two generated Board/product files changed. Five
device source files and five public contract/lock/patch files were added; no
previous file was removed. Recovery, camera, mi_ext, kernel and original vendor
inputs remained unchanged. The ignored reproduction driver and receipt are
under `reports/oem-policy-integration-20260829/provider-source-admission-v1/`;
the candidates are under `artifacts/device-candidates/`.

All 153 generator tests passed offline with no skips, including provider-only
and property/provider composition, altered receipts, changed controls, duplicate
wiring, late file/directory additions and preservation of input bundles.
This checkpoint did not access the guest or phone. Native source installation,
ELF checks, provider policy compilation, complete labeling and service behavior
must be recorded separately before any stronger support claim.
