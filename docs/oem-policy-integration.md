# Native OEM policy declarations and factory checks

The **v11b** Nezha user policy build passed at **2026-08-29 20:47:06 UTC**.
The strict combined-policy compiler, the new OEM ownership guard and all nine
factory context/structural checks executed successfully in the actual Android
graph. This resolves the three failures recorded after the
[v10 helper/Binder source integration](policy-source-integration.md).
The [result record](../research/oem-policy-integration.json) preserves both
v11 attempts and their exact inputs. Independent v11 semantic comparison and
unfiltered permissive-domain analysis passed at **20:54:46 UTC**. Image adoption,
complete Treble labeling and an Evolution boot are not established.

The selected source remains Evolution X Android 16 QPR2 `bka`, release `bp4a`,
for `lineage_nezha-bp4a-user`. No upstream branch, ROM readiness flag or normal
Android SELinux mode changed. The same existing source volume and user output
were used; no source sync, new VM or phone operation occurred.

## Source ownership and admission

The [three-type contract](../config/nezha-oem-policy.json) binds exact factory
system_ext/product CIL evidence. The original Xiaomi `.te` sources were not
recovered: these are authored declarations reproducing the reviewed ownership
and classifications, not a claim to possess the original source tree.

| Type | Authored owner and attributes | Generated result |
| --- | --- | --- |
| `vendor_hal_atfwd_hwservice` | system_ext public; `hwservice_manager_type`, `protected_hwservice`, `coredomain_hwservice` | `object_r`; singleton `vendor_hal_atfwd_hwservice_202504` mapping |
| `vendor_hal_systemhelper_aidl_service` | system_ext public; `service_manager_type`, `protected_service`, `hal_service_type` | `object_r`; singleton `vendor_hal_systemhelper_aidl_service_202504` mapping |
| `offlinelog_file` | system_ext private; `file_type`, `data_file_type`, `core_data_file_type` | `object_r`; no public mapping |

The two source files add no `allow`, process-domain or permissive declaration.
`coredomain_hwservice` classifies a service object; it does not make that object
a process domain. Android M4 and the standard policy producers generate CIL,
roles and mappings. No generated CIL is hand-edited for this integration.

The device generator and private policy stager both require explicit
`--oem-policy-contract` admission, the factory inputs, the DSP profile and the
existing helper capability. The native guard checks exact declarations,
source ownership, named memberships, object roles, two singleton public
mappings and the unchanged DSP boundary. It rejects added allows, unexpected
domains, helper property SET access and unreviewed definitions. The unchanged
factory vendor input contains identical bare type declarations; the existing
compiler `-m` behavior is retained only with those expected duplicate names
checked. Factory CIL and original images are preserved.

The first v11 build compiled the combined policy and passed the nine factory
checks, but **the phase failed** its new guard. Android's filtered system_ext
output retains a full inherited platform membership set when a new member is
added. The first guard incorrectly expected only the new member. The isolated
correction in commit `551c2a3` accepts exactly the current platform membership
plus the reviewed additions, while still rejecting unrelated additions. It
does not loosen the policy or suppress a failed check.

The v11b replacement changed the private checker bundle and candidate receipt;
the installed device tree and upstream source files remained unchanged. Ten
previous validation outputs were archived before rerunning the compiler and
all nine checks. The successful retry completed 31 Ninja actions. Both phases
have observed source-read-only/output-writable nsjail mounts and unchanged
input hashes; the first failure remains evidence, not a pass.

## Reproduce the selected slice

Start with `make apple-status`, inspect live `active_volume_users`, and check
disk, architecture, case sensitivity, the selected manifest and existing
processes. Use only the existing sole volume owner. Follow the
[source-lock](source-lock.md) and [Container](apple-container.md) rules; do not
reset local patches or replace the checkout. The exact installed v11b tools
are frozen in the result record. Later workspace tool revisions need fresh
bundle and candidate receipts rather than being relabelled as the tested bytes.

Stage into a fresh ignored directory, with the same original classification
corpus and factory capture used by v10:

```sh
factory_analysis=artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b
policy_bundle=artifacts/policy-inputs/nezha-factory-oem-NEW
mkdir -p artifacts/policy-inputs &&
python3 scripts/policy_inputs.py stage \
  --corpus-root artifacts/build-validation/nezha-dsp-policy-v9-1/files/inputs/combined \
  --factory-policy-receipt "$factory_analysis/erofs-contract-v1/policy-receipt.json" \
  --oem-policy-contract config/nezha-oem-policy.json \
  --output "$policy_bundle" &&
python3 scripts/policy_inputs.py verify --bundle "$policy_bundle"
```

Use that receipt in the [device generation command](build-progress.md), which
also explicitly selects `config/nezha-oem-policy.json`. Default generation does
not opt into this slice. Neither command applies patches, changes a source
checkout or admits target-files/flash. Preserve previous candidates and bundles
when installing; independently verify transferred controls and destination
bytes from the owning guest. The bundle's own manifest is not its authority.

The native combined binary still consumes the ten inputs documented in the
[v10 workflow](policy-source-integration.md): current Android framework CIL and
mappings, the original vendor public mapping and ODM CIL, the genrule-derived
vendor CIL, and the current genfs compatibility CIL. The old framework corpus
is only derivation provenance. Include the required
`nezha_factory_oem_policy_check` target with the strict combined build and all
nine factory checks; the complete executed argument list is in the result
record. Preserve `ignore_neverallow: false`, no permissive-domain allowance,
read-only source mounts and all existing artifact-path checks.

## Native results and verification limits

| Native target | v11b result |
| --- | --- |
| `nezha_factory_oem_policy_check` | Passed; exact ownership/membership/mapping receipt emitted |
| `nezha_factory_precompiled_sepolicy` | Strict compilation passed; remains non-installable |
| `nezha_factory_file_contexts_test` | Passed |
| `nezha_factory_property_contexts_test` | Passed |
| `nezha_factory_hwservice_contexts_test` | Passed; previous atfwd classification failure resolved |
| `nezha_factory_service_contexts_test` | Passed; previous systemhelper classification failure resolved |
| `nezha_factory_vndservice_contexts_test` | Passed |
| `nezha_factory_seapp_contexts_checked` | Passed with vendor-only restrictions retained |
| `nezha_factory_platform_seapp_contexts_checked` | Passed without incorrectly applying vendor-only restrictions |
| `nezha_factory_sepolicy_test` | Passed; previous offlinelog classification failure resolved |
| `nezha_factory_dev_type_test` | Passed |

The service check retains two warnings for identical duplicate specifications;
they were neither deleted nor suppressed. The pass refers to executed check
actions in the successful full phase log, not phony targets, installation rows,
stale stamps or the API-202504 compatibility no-op.

The separate independent analysis binds all ten actual compiler inputs, strict
flags, binary hashes, source/M4 inputs, roles, public exports and mappings.
All **5,976 neverallow and 390 neverallowx statements** remain, with concrete
coverage matching the reviewed projection. Existing named and anonymous
attribute closures, expansion flags and inherited non-access-vector statements
also match. Restoring classifications intentionally changes some coverage;
this is not a claim that every old expanded assertion set stays identical.

The actual generated inputs produce exactly the predicted permission delta:
five added lookup permissions and 47 removed `vendor_init` file-access
permissions. The added lookups are the existing framework service lookups by
`atrace`, `shell`, `system_app` and `traceur_app` for systemhelper, plus
`vendor_atfwd` finding its hardware service. There are no extra extended allow
changes. These are comparisons of complete generated policy inputs, not a
claim that the corresponding services have run.

All three real, unfiltered `sepolicy-analyze ... permissive` invocations exited
zero with empty output under observed read-only input mounts. They find zero
permissive domains in the combined binary, source precompiled binary and source
neverallow binary. The factory-aware combined output is **1,515,022 bytes**,
SHA256 `c5df9b0f97fa32da33dfe2f83c3266280286153efccd65de3fe1976585da5456`.
The independent receipt also verifies the nine fresh native actions against
their real Ninja commands and sandbox input/output maps. It did not replay the
compiler or modify Android source/output. Its 195,805-byte receipt has SHA256
`6fe08672416a7752875da29da5a8c2da350fcb6842f0e9492aaa80047b75cfd0`;
the sealed local capture preserves the raw evidence privately.

Complete Treble labeling needs real complete Evolution APK inventories.
Vendor keystore2-key and TEE-service contexts are outside these nine checks.
Actual service registration and native-feature behavior remain untested.

The combined factory-aware binary is not the default source-only
`precompiled_sepolicy` under the output ODM directory. Never adopt that
source-only binary into the retained factory images. The eventual image
derivation needs exactly the corrected vendor CIL, the combined ODM policy and
three matching framework digests, with complete metadata/payload preservation
proved independently. The authored [EROFS metadata tool](../tools/erofs-metadata/README.md)
does not itself supply a writer, a validated round trip or signed images.

The optional [four-property policy](../config/nezha-oem-properties.json),
[provider policy](../config/nezha-framework-provider-policy.json),
[Sigma/QCC inputs](framework-providers.md), [Camera runtime inputs](camera-runtime-inputs.md),
[mi_ext path](mi-ext-inputs.md) and [A/B recovery correction](recovery-packaging.md)
are separate authored integrations. They are not installed or native-validated
by this v11b result. Their future source receipts, builds and device tests must
remain distinct. Working76 and its separate stock-companion device evidence
remain unchanged; private keys stay outside the VM and no device operation is
authorized by a policy or packaging pass.
