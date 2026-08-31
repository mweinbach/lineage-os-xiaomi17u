# Exact Nezha device framework matrix

The first complete 4 KiB VINTF comparison materialized all **39 selected APEX
packages** and passed the separate framework and vendor/ODM consistency
commands. The full `--check-compat` command then returned **65**, identifying
**155 AIDL interface/version/instance tuples** absent from the selected framework
matrices at FCM **202504**. The original failure is preserved under
`artifacts/build-validation/nezha-full-vintf-v13ja-4k-capture-v1/results/`.
Its 10,599-byte stderr has SHA256
`c6185d0ea2d9d5859b6dc114800190af34a13ca8513e3ad4a6fc038583e6fa5c`.
This is the pinned checker's `checkUnusedHals` failure, not evidence that the
services failed to start.

The [matrix contract](../config/nezha-framework-matrix.json) and
[projection helper](../scripts/framework_compatibility_matrix.py) provide the
missing source integration through the existing Android device-FCM producer.
They do not change any numbered platform matrix, add a service implementation,
alter SELinux or suppress a check. Complete-ROM, runtime and hardware readiness
remain false.

## Original evidence and narrow derivation

All 155 tuples have an exact declaration in the current original vendor/ODM
inputs and matching original factory framework-matrix coverage. The admitted
factory package remains
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`;
its user-provided origin is not independently authenticated.

| Original framework matrix | Unique selected tuples | SHA256 |
| --- | ---: | --- |
| `/system/etc/vintf/compatibility_matrix.device.xml` | 152 | `378f41d642384e0896b88ad9d08791e3202f6ce897fba70f10600cd32b0fdd26` |
| `/product/etc/vintf/compatibility_matrix.xml` | 2: Dolby DVS and Xiaomi ToF | `e3d9b04cbebe3af5b3c8f07396a2de4f50850ddc73125a66ce0c0d1d60d6f58a` |
| `/product/etc/vintf/touch_framework_compatibility_matrix.xml` | 1: Xiaomi touchfeature | `6f0ce5932bb6db336bd25735f1b657455f498165098a098d1c48f9f41c6fc9cc` |

The stock system matrix includes duplicate displayfeature, micharge and mimd2
elements. The projection records their original positions and emits each exact
tuple once. It preserves the three product declarations' provenance while
deliberately consolidating these static declarations into the single Nezha
system device FCM. No runtime service or proprietary file moves partitions.
Pinned libvintf combines system, system-ext and product framework matrices for
the unused-HAL comparison. A separate product matrix would also need its own
explicit native goal: the pinned aggregate framework-matrix alias does not
select the product module.

The generated source contains **130 AIDL packages and 155 exact tuples**. It
does not import the stock matrix's other legacy declarations, duplicate
elements, wildcard instances or version ranges. An omitted original AIDL
version is recorded separately and emitted explicitly as version 1, consistent
with the actual native manifest diagnostic. No `optional` attribute is added.
This omission is not described as runtime presence enforcement: the pinned
`HalManifest::checkCompatibility` implementation does not compare HAL presence.

Generation reopens **119 original XML files**: 116 device manifests and the
three framework matrices. Full hashes, regular capture members, readback
status, inode identities, inventory links and exact tuple support are checked.
The 22 evidence records and 15 captured source preconditions are also rehashed.
Original XML, dumps and logs remain in ignored paths; only authored XML and a
public provenance contract enter the portable candidate. Image identities are
recorded provenance; this helper does not reread the full stock images.

The independent host mapping is retained in
`reports/oem-policy-integration-20260829/framework-matrix-integration-v1/semantic-review/`.
Its mapping SHA256 is
`71625900bc7b4fab345176e2d71c95a0488a2ace01076d1672bfd6c894c33c22`.
All 209 original VINTF XML files were rehashed during that review. That broader
inventory review is distinct from the generator's 119-file selected closure.

## Non-vendor prefixes and framework support

`android.se.omapi.ISecureElementService/default` is a real original vendor
VINTF declaration, distinct from `android.hardware.secure_element`. The pinned
framework provides the VINTF-stable `android.se.omapi` interface with a frozen
version-1 API snapshot. Its current interface definition may still develop;
the Blueprint's `frozen` field is false. The pinned `SecureElement` app contains
the exact stable-service registration, conditional on the system user and
`secure_element_vintf_enabled=true`. It separately registers its ordinary
framework binder with system stability. Selected resources, package inclusion
and actual runtime registration are not established by this matrix change.

OZO audio, FPC fingerprint and Dolby DMS/DVS are distinct original extensions.
Their package prefixes do not make them equivalent to platform audio,
fingerprint or Codec2 interfaces. They are acknowledged exactly as captured;
client ABI, library closure, process startup and feature behavior remain
separate bring-up work.

## Generator and native build path

Add the explicit option to the existing verified factory candidate invocation:

```sh
--framework-matrix-contract config/nezha-framework-matrix.json
```

Omitting the option preserves previous output. Selection requires the exact
factory profile, `lineage_nezha`, `bp4a` and shipping API 36. The source lock and
all existing recovery, provider, page-size, partition and policy bindings stay
in place. The generator refuses another contract hash, changed originals,
duplicate or broadened tuples, conflicting matrix selectors and altered
portable output, including changes accompanied by a resealed file inventory.
It reopens inputs before publishing a new candidate.

The source delta is confined to:

- `device/xiaomi/nezha/generated/BoardConfigCandidate.mk`: select and freeze the
  exact singleton `DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE`, reject prior
  or command-line/environment overrides, and keep the product selector empty.
- `device/xiaomi/nezha/generated/framework-compatibility-matrix.xml`: the new
  no-level framework matrix, schema version 9.0.

The portable candidate also includes the contract. The product fragment,
package list, namespaces, 4096 settings, policy sources and provider binaries
do not change. Existing candidates and prior native evidence must not be
overwritten.

The existing `framework_compatibility_matrix.device.xml` module consumes the
standard selector. Preserve its normal check-manifest generation,
`assemble_vintf`, XML schema validation and generated SELinux/AVB requirements.
Do not substitute an edited installed XML or create an external `device_fcm`
module. Recheck the live source preconditions before installing the source
candidate. Build the actual matrix module and `check-vintf-all`, then inspect
the exported Soong selector, the actual Ninja input and the installed matrix.
The installed XML adds normal build-generated fields and is not expected to
match the authored source byte for byte.

After that component build, recapture the selected graph, all framework XML,
original vendor/ODM metadata, kernel release/configuration and all 39 APEX
packages. Repeat the same framework consistency, vendor/ODM consistency and
full `--check-compat` commands. Preserve the existing no-level matrix-definition
skip and other pinned checker limitations explicitly. A successful unused-HAL
check is not a proprietary interface-definition check, a service test or proof
that Evolution X boots. Native adoption and the retry are separate from this
host source-admission milestone.

## Host source verification

Two independently generated source-only successors under
`artifacts/device-candidates/nezha-factory-framework-user-v13j-4k-matrix-v1`
and its `-repeat` directory have identical bytes: 46 payload files plus the
admission record. Both admission records have SHA256
`3fa9b1e20d10bce5d05834ce1a10808b6e09c2f3b8f808acdbff53b13c823058`.
The old v13ja candidate and all 183 predecessor controls remain unchanged.
The new 185-file control snapshot is recorded by
`candidate-controls-freeze-v1.json`, SHA256
`4e69430e2e67dfab3a34ba6369624959f0277734862dc8cae43ba71ca2059aec`,
under the ignored matrix integration report directory. The generator still
rejects both target-files and flash admission.

The independent implementation review passes **27 focused tests and 214
existing generator tests**, with zero skips. It reopens the actual selected
original inputs, checks all 155 tuples and 158 original matrix-element
references, and confirms unchanged output for four unselected generic/factory
user/userdebug cases. The review is
`source-review/implementation-review-v1.json`, SHA256
`9fe1eb7ecb6e3e5dd04450c65156f7ceacf22efbc75643aa8c7c39a2ff06cfc5`.
These are host source/projection results, not a native compatibility pass.
