# Framework allocator service selection

The actual `vintf-v13h-2` build reached 3,108 of 3,109 Ninja actions and then
failed `vintffm`: `android.hidl.allocator` is mandatory in the frozen framework
manifest check at device level 5, but the selected product did not include it.
The result and full log are preserved under
`artifacts/build-validation/nezha-vintf-v13h-2/`; their SHA256 values are
`88e4200261601edc7b941249b275bc2a2f47ff7cd0c2c3dc872b5d0d7c159f4f`
and `8237f827172672ccaef4a1b406aa2c617dc2915a3b77b4a198a64963e06167e0`.
This was a real check failure, not a timeout or a passed compatibility result.

The explicit [allocator contract](../config/nezha-framework-allocator.json)
selects the existing upstream `android.hidl.allocator@1.0-service` module. The
generator adds only its `PRODUCT_PACKAGES` selection to the generated product.
It does not create another service, copy a standalone manifest, modify a frozen
matrix, or add policy. Previous profiles produce their previous output when
the option is omitted.

## Pinned source and behavior

The contract binds 24 source files, totaling 329,015 bytes, captured from the
existing checkout on August 30, 2026. Their three project revisions match the
recorded Evolution `bka` / `bp4a` source snapshot:

| Project | Revision |
| --- | --- |
| `system/libhidl` | `d063c3a2bf981d8dab2ca60ea471f940d71167a6` |
| `build/make` | `a438ca40c6ed779042f806142b1165ba1360a7b2` |
| `system/sepolicy` | `e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27` |

The libhidl project was clean. The other two projects retained only their
previously reviewed local patches; these captures did not modify source.
The exact file identities and capture receipts are in the contract. They are
preconditions for the separate native source transaction, not a claim that the
portable generator inspected the Linux checkout.

The upstream Blueprint owns all three installed outputs:

| Role | Expected installed path |
| --- | --- |
| Binary | `system_ext/bin/hw/android.hidl.allocator@1.0-service` |
| Init | `system_ext/etc/init/android.hidl.allocator@1.0-service.rc` |
| VINTF fragment | `system_ext/etc/vintf/manifest/android.hidl.allocator@1.0-service.xml` |

Both the binary and `vintf_fragment` module are `system_ext_specific`. The
binary uses `vintf_fragment_modules` to require its fragment. Init starts
`hidl_memory` in class `hal`, with user and group `system`, through the upstream
`/system/system_ext/bin/hw/` path. The existing platform file context covers
both `/system_ext/` and `/system/system_ext/` spellings.

The source fragment declares HIDL `android.hidl.allocator@1.0`, interface
`IAllocator`, instance `ashmem`, with **`max-level="8"`**. Keep that maximum.
The implementation registers only when the service manager reports the
`HWBINDER` transport. Otherwise it sets `hidl_memory.disabled=true` and exits;
the upstream init action stops it. Satisfying the frozen level-5 check therefore
does not establish that registration is expected or tested at Nezha's newer
vendor level.

Existing platform policy provides `hal_allocator_default`, its executable
type, the init transition, `hidl_allocator_hwservice`, and the
`hidl_memory_prop` declaration, context and write permission. No additional
Nezha domain, permission, permissive mode or neverallow exception is selected.

## Reproducible candidate capability

Add this option to the existing, verified candidate-generation invocation:

```sh
--framework-allocator-contract config/nezha-framework-allocator.json
```

This option has no dependency on the separate OEM, proprietary-provider or
held 4 KiB capabilities. It is limited to the existing Nezha `framework-checks`
product, `bp4a`, and shipping API 36. The original source lock and source
snapshot are copied into the portable admission record and rechecked before
publication. The service contract is immutable by SHA256; changing its module,
source preconditions, output roles or native-success flags cannot be made valid
by merely updating the generated file inventory.

The candidate-local ownership guard rejects another service selection,
declaration, allocator manifest or owned policy definition. Device Make files
reserve the allocator name for the generated selection; native client libraries
may still link `android.hidl.allocator@1.0` from their Blueprints, and existing
policy clients may reference the allocator hwservice type. This is a bounded
source scan, not arbitrary Make evaluation or proof of uniqueness throughout
the Android checkout. Normal Soong/Ninja duplicate checks and the native
producer review remain mandatory.

## Required native evidence

The next source transaction must preserve current v13ha/provider-v7 and all
original private inputs, verify the contract's source preconditions, and change
only the generated product selection. Its build must request the **actual
service component**, not just `check-vintf-all`: a fragment alone can satisfy
a manifest check without proving the executable was built.

The native review must resolve the binary, init file and VINTF fragment back to
the pinned upstream module, reject competing owners and duplicate installed
destinations, and inspect the complete binary dependency closure. Preserve the
original init and source-fragment bytes. Bind the installed XML to its actual
`vintf_fragment` producer and semantic content; do not assume that a generated
XML is byte-identical to its source before inspecting the build rule.

Run normal enforcing-policy, init/context/Treble and frozen framework checks
without suppressions. Then recapture the complete selected framework, vendor,
kernel and APEX inputs and run full VINTF compatibility. The previous 21-XML
capture is a predecessor; it cannot silently stand in for a graph that now
includes the allocator fragment.

Offline generator tests and a reproducible candidate are source-admission
evidence only. Actual service compilation, full compatibility, image inclusion,
runtime registration and hardware behavior remain separate gates. This change
does not authorize a phone operation or promote complete-ROM readiness.
