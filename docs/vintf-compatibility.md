# Native VINTF inputs and complete comparison

At the **August 29, 2026 20:00 UTC checkpoint**, the existing Nezha `bp4a-user`
build produced the platform framework matrices, framework base manifests,
host tools and exact stock kernel metadata. This is a prerequisite build,
**not a complete framework/vendor compatibility pass**. The
[new record](../research/vintf-compatibility.json) retains the native build,
actual selected graph, source pins, artifact hashes and current factory APEX
provenance. The earlier [vendor-only check](vintf-validation.md) remains a
separate dated result.

The corrected native phase completed **2,475 Ninja actions**, exit 0, between
19:49:23 and 19:53:56 UTC. Its running Ninja process had separate mount,
network, PID and user namespaces, read-only source and writable user output.
Source inputs remained unchanged. No image or phone operation was requested.

## What the native graph actually includes

The guarded [graph auditor](../scripts/vintf_compatibility.py) read the complete
1,343,190,940-byte generated Kati graph and inspected its selected input files
without writing to the guest. It found:

| Native input or check | Observed result |
| --- | --- |
| Selected system/system-ext VINTF XML | 19 files: nine present, ten manifest fragments not yet built |
| Selected framework APEX packages | 36 packages, all unbuilt at this checkpoint |
| `check-vintf-all` dependencies | `check_vintf_system.log` and `vintffm.log` only |
| Vendor consistency and full compatibility logs | Neither target exists in this product graph |
| Full kernel release and configuration targets | Both built; exact release and IKCONFIG match captured stock bytes |

The current product uses opaque factory vendor/ODM images. Pinned build-core
rules conditionally omit the full comparison when installed vendor VINTF
metadata is absent. Consequently, a successful `check-vintf-all` would not
establish compatibility with those factory images. Its name is not a substitute
for inspecting its generated dependencies or recording the checks that ran.

The nine installed XML files are the system matrices for FCM **5, 6, 7, 8,
202404 and 202504**, the device-specific framework matrix, and the system and
system-ext base manifests. FCM 202504 uses the pinned `kernel_config_b_6.12`
requirements. Older selected matrices remain intact. The system-ext manifest
includes the platform HIDL manager/token declarations from
`system/hwservicemanager/hwservicemanager.xml`; it contains neither Qualcomm
framework provider discussed below.

Two native module conditions matter when reproducing this build:

- `product_manifest.xml` has no build action or Ninja target when
  `PRODUCT_MANIFEST_FILES` is empty. The first attempted goal list failed
  before VINTF actions for exactly this reason. That failure is retained; no
  replacement manifest was fabricated.
- `product_compatibility_matrix.xml` is a valid phony target with no output
  when `DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE` is empty. Its successful
  goal is not evidence that a product matrix was generated. At this pin, the
  `framework_compatibility_matrix.xml` alias selects the system list; any
  configured product matrix must also be selected explicitly.

The exact kernel release is
`6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`. Native
`kernel_configs.txt` has SHA256
`73fa878baa4c748b2139e7acb4ed396d2056ca8ed71b565ded6f96b3558a98cd`, matching
the 220,352-byte stock IKCONFIG. Producing these files does not compare them
against framework requirements; the eventual invocation must actually supply
them through `--kernel`.

## Factory APEX provenance

All 209 partition VINTF XML files match the earlier Xiaomi.eu capture, as
recorded in the [factory framework comparison](factory-framework-contract.md).
That equality did not establish the identities of the factory APEX packages.
A new guarded read-only capture from the admitted factory vendor image now
accounts for all three package files in its complete inventory. The complete
ODM inventory contains no APEX package. No image was mounted or changed.

| Factory vendor package | Comparison and VINTF scope |
| --- | --- |
| `com.android.hardware.cas` | Package bytes match the historical complete inspection; one CAS VINTF fragment |
| `com.google.android.widevine` | Package bytes match the historical complete inspection; one DRM VINTF fragment |
| `com.xiaomi.wifi` | Package differs; independently inspected factory payload still has two regular files and no VINTF directory |

The three captured packages total **6,348,800 bytes**. Factory Wi-Fi has SHA256
`b76fe0135990383d5e635d4d53ac19ea172e0024ff5e72b0b70ba990a5ecbc2d`.
Its manifest and `wifi_compat.json` payload files match the older inspection,
but the package contains an additional outer `compat.json` and different
public-key, signature and payload-container bytes. These differences remain
recorded; the factory package is not relabeled as the Xiaomi.eu package.
Payload AVB, container signatures, OEM origin and activation remain separate
unverified claims in this slice.

The old phone `apex-info-list.xml` describes its Xiaomi.eu installation. It
cannot stand in for Evolution's selected framework packages. Once all native
packages exist, use the pinned `apexd_host` with a complete isolated set of
framework and original factory vendor/ODM inputs. Verify package/module
identities, duplicate module names, extraction outputs and the emitted list.
That tool produces static host metadata; it does not prove on-device activation.

## What the checker does and does not establish

The exact pinned `libvintf` source matters. At commit
`69c456ea4aa2f503a2904cfbc11f279a3b2efb09`, `HalManifest::checkCompatibility`
does **not compare HAL presence**. Its framework/device-matrix branch checks
vendor-NDK and system-SDK declarations; the opposite branch checks sepolicy
and applicable kernel requirements. The full command additionally performs
deprecation and unused-device-HAL checks. The record binds this observation
to the exact `HalManifest.cpp` bytes, which match the live Git HEAD.

The factory device matrix declares `android.frameworks.sensorservice`,
`vendor.qti.hardware.sigma_miracast_aidl`, `vendor.qti.qccsyshal_aidl` and
system SDK 36. These declarations are useful integration evidence. They do
not by themselves establish a validator failure or prove the providers run.
Factory system-ext contains real sigma-Miracast and QCC provider candidates,
which need their client, ELF, linker, init, VINTF and policy requirements
reviewed before import. Adding only their manifest declarations would not
implement the services.

Other upstream limits remain visible: `--check-one` returns before kernel
handling; `--check-compat` without `--kernel` disables runtime-info checks;
the host APEX loader accepts a missing info list; default flags exclude the
AVB-version comparison; and the static runtime provider reports `SIZE_MAX`
for kernel SELinux policy capability. Do not use these behaviors to turn
missing inputs into a compatibility claim.

## Reproduction and next checks

Recheck `make apple-status`, sole volume ownership, source pins and idle build
state first. From this workspace, stream the auditor into the verified owning
guest using the real physical OUT path. Replace the dated VM name only with
the currently verified sole owner; the source-root alias remains the graph's
literal prefix:

```sh
container exec -i twrp-nezha-upstream74-20260829 python3 -B - \
  --build-ninja /work/out/nezha-user-policy-20260827T2220Z/build-lineage_nezha.ninja \
  --product-out out-nezha-user-policy-20260827T2220Z/target/product/nezha \
  --output-root /work/out/nezha-user-policy-20260827T2220Z \
  < scripts/vintf_compatibility.py
```

This uses the existing Container exec connection, as the recorded run did,
with no guest file writes. Exit 0 means the inventory completed;
`compatibility_verified` remains false.
Selected graph variables or unsupported syntax fail closed. The auditor
checks duplicate outputs, input links, bounded reads, and changes to the graph
or inspected artifacts. Its 32 offline tests and independent native Ninja
grammar probes are tooling evidence, not an Android compatibility test.

Build the complete selected framework XML and APEX closure, then assemble all
five partition maps plus the actual host-materialized APEX map. Keep original
factory vendor/ODM metadata, the `canoe`/`nezha` selection properties, API
values and full kernel release/configuration. Record distinct framework and
device consistency checks followed by an explicit full `--check-compat`, with
every failure retained. Full image adoption, signed boot-chain validation,
native provider behavior and any authorized first Evolution boot remain
separate gates in [current workspace status](workspace-status.md).
