# Factory input comparisons and host staging

A separate bundle of factory vendor/ODM images and nine selected Camera
dependency outputs is now **staged on the host**. The evidence supports carrying
forward specific byte-identical inputs and the observed API requirements. It
does not establish installation in the builder, a successful Android build,
device compatibility or permission to flash. Later adoption belongs in the
separate [build progress record](build-progress.md).

The factory-named package remains user-provided, with no verified origin URL:
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
The modified Xiaomi.eu package,
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`,
and its historical records remain unchanged. Passing local hashes and the
selected [external AVB checks](factory-firmware-validation.md) does not
authenticate a Xiaomi trust root or the connected phone's rollback state.

The [compact record](../research/factory-input-reuse.json) binds the detailed
private receipts, selected file hashes and host bundle. Full module inventories,
properties, images, JARs, JNI payloads and logs stay ignored. This publication
read metadata only; it did not access images, the guest or the phone.

All **nine complete build.prop files differ** between factory and Xiaomi.eu.
Nevertheless, all **69 selected critical property values** agree. The nine
paths cover eight logical images, including both vendor build.prop files.
These are values from captured files, not a new live property read.

| Requirement | Factory and Xiaomi.eu value |
| --- | --- |
| Shipping API, from ODM | 36 |
| System and vendor SDK | 36 |
| Board first/current API, from vendor | 202504 |
| Board API frozen | true |
| LLNDK API, from system | 202504 |
| System security patch | 2026-07-01 |
| Vendor security patch | 2026-02-01 |
| System build type / debuggable | user / 0 |
| System secure / ADB secure | 1 / 1 |

The first strict property analysis stopped at the bare line
`ro.vendor.mitee_support`, which has no equals sign. It occurs at factory ODM
line 480 and Xiaomi.eu ODM line 479. The next analysis preserves it as
**uninterpreted text**, not an empty assignment, while retaining the original
script, log and successful captures. Neither attempt applies properties.
Imports, precedence across files and effective VINTF behavior remain outside
this comparison. The [factory framework contract](factory-framework-contract.md)
records the separate XML and policy work.

The private normalized layout translates the already verified factory LP,
AVB and filesystem evidence into the existing input-tool schema. It has
**16 logical entries: eight populated A entries and eight empty B entries**,
with **12,477,939,712 allocated bytes**. The populated group declares a
15,290,335,232-byte maximum within a 15,300,820,992-byte super device. These
are package metadata declarations, not measurements of the phone.

The unchanged vendor tool accepted the base vendor/ODM plan. The device
derivation also accepted both user and userdebug schema checks using factory
layout/properties plus the historical Xiaomi.eu boot reference. Those checks
were explicitly mixed references and generated no target. The base plan
did not exercise the Camera extra-file inventory requirement; the later
staging operation did.

The normalizer records the existing selected external AVB result as
`passed`; the vendor tool's supported schema maps it to `verified`.
`source_trust_is_from_record_not_reauthenticated` remains true, and
`avb_checked_by_this_tool` remains false. This is a label translation tied to
the exact external receipt, not a new signature check or an origin upgrade.
No parser or verification check was weakened to accept the record.

The DLKM comparison covers every regular file under `/lib/modules` in its two
images. All **504 files** match the preserved Xiaomi.eu source and existing
kernel-input bundle, with no added, removed or changed paths.

| Location | .ko file instances | Metadata files | Compared bytes |
| --- | ---: | ---: | ---: |
| vendor_dlkm | 381 | 6 | 129,052,231 |
| system_dlkm | 103 | 14 | 14,227,225 |
| Total DLKM | 484 | 20 | 143,279,456 |

Together with the **430** matching vendor ramdisk modules in the
[factory boot contract](factory-boot-contract.md), this covers **914 .ko file
instances across three locations**. It is not a count of 914 unique modules
or loaded modules. Whole-file comparison preserves appended signature bytes
where present, but does not verify signature trust, ABI compatibility or which
duplicate provider should load. No stripping, signing, depmod or module loading
was performed by these comparisons.

The nine original Camera dependency sources also match Xiaomi.eu byte for byte:
four DEX JARs, one JNI library and four XML sources, totaling **544,623 bytes**.
Seven selected outputs are unchanged factory files. The two existing
[XML derivations](camera-inputs.md) reproduce the other outputs exactly:
CameraX selects one registration from platform-miui.xml; postproc maps its
registration from `/system/framework/` to the selected `/system_ext/framework/`
JAR. These two outputs are not labeled as original factory files. The selected
outputs total **542,236 bytes**.

The new private selection changes only the package SHA256; all paths, hashes,
module declarations and recipes retain their earlier values. The public
Xiaomi.eu selection is preserved. No Camera APK is in this bundle. Equality
does not establish Camera class loading, linker namespaces, signatures,
service behavior or Leica feature compatibility.

The first host staging attempt stopped before publication because the required
canonical EROFS inventory parent directory was absent. Two existing metadata
files were then copied into the expected location, with hashes and bytes
verified unchanged. Originals and receipt contents were retained; no links,
image rescan or guard changes were used. The failed attempt's empty result and
error log remain separate from the successful second attempt.

The completed host bundle is
`artifacts/vendor-inputs/nezha-factory-d2cf57fd-camera-v1/`.
It contains **two images, nine extras and five generated files**.
The image/extra total is **5,727,872,540 bytes**:
5,727,330,304 image bytes plus 542,236 selected-extra bytes.
Generated makefile/Blueprint/README metadata is counted separately. The
staging receipt confirms input hashes and output readback, while leaving
dependency closure, new AVB verification and device testing unproven.

| Evidence | SHA256 |
| --- | --- |
| Normalized factory layout | 8fa822ebe52e9ea1cfea2e6215af150623c6321d782291f9588ddb84636de1c0 |
| Factory property comparison | 349783a63894190afcecef489707800a0e03c851b58cac64375774021c08a901 |
| DLKM comparison receipt | 70e4471ba25fcce901c37aface8f88e4d22b067fc963d1a3f8b12227fb23b018 |
| Camera source/output comparison | 0994eddaa3a718e2edfd42d1ec125c1647757f02293f2210bf29437c2e384f63 |
| New factory Camera selection | c82cf07f512342d7e20cc155a6425bf89d272c6c1fb3fc258e89e50473f7a8d2 |
| Completed host vendor bundle | 811f7904adbec2fa99d933179b1247d0c2e30f80a2ba7e0b54c8a2e713917360 |
| Independent layout/property review | 04aa9f32ed114b9dfe7c59b7b336b47e68e09cf8016fc6fb40c6487360a7b716 |

An independent review found no material issues in the layout or property
bindings. A separate pass rehashed **88 metadata and selected-payload files,
3,360,249 bytes**, including the nine Camera source pairs and selected outputs.
These checks and the offline workspace tests do not constitute an Android
build or a hardware test.
