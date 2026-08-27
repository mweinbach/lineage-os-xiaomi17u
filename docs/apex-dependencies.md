# Nezha vendor APEX dependencies

The three supplied vendor APEX packages have been inspected without activation
or mounts. **All three installed package files and both active VINTF fragments
match the extracted Xiaomi.eu inputs byte for byte.** The phone's real APEX list
also identifies these three modules as active vendor packages. These are facts
about the current Xiaomi.eu installation, not proof that Evolution X can load
their services or retain DRM, CAS or Wi-Fi behavior.

The [machine-readable record](../research/apex-dependencies.json) binds the
package, payload, XML, tool and evidence hashes. Its parent is the user-provided,
modified Xiaomi.eu ZIP with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
The download origin remains unknown and unauthenticated. APEX `isFactory=true`
means the running system identifies a package as preinstalled; it does not
authenticate untouched Xiaomi factory firmware or resolve the parent images'
[AVB failures](boot-contract.md).

| Package under `/vendor/apex/` | Declared module name / version | Regular payload files / ELF files | VINTF contribution |
| --- | --- | ---: | --- |
| `com.android.hardware.cas.apex` | `com.android.hardware.cas` / `1` | 4 / 1 | AIDL `android.hardware.cas`, `IMediaCasService/default` |
| `com.google.android.widevine.nonupdatable.apex` | `com.google.android.widevine` / `190250226` | 10 / 7 | AIDL `android.hardware.drm`, `IDrmFactory/widevine` |
| `com.xiaomi.wifi.apex` | `com.xiaomi.wifi` / `1` | 2 / 0 | None in the complete payload inventory |

Both XML fragments declare schema `9.0`, type `device`, and omit the HAL version
element. The record preserves that omission rather than presenting a queried
service version. Their runtime paths are:

- `/apex/com.android.hardware.cas/etc/vintf/android.hardware.cas-service.xml`
- `/apex/com.google.android.widevine/etc/vintf/com.google.android.widevine.xml`

Widevine's runtime directory uses its **declared module name**, without the
filename's `.nonupdatable` suffix. The pinned libvintf implementation reads the
actual APEX information list, filters active entries by vendor/ODM partition,
and constructs each VINTF directory from `moduleName`. A filename-derived
directory or an invented empty APEX list would omit real inputs.
[Pinned APEX lookup](https://android.googlesource.com/platform/system/libvintf/+/69c456ea4aa2f503a2904cfbc11f279a3b2efb09/Apex.cpp)

The real `/apex/apex-info-list.xml` has 39 entries: three active `VENDOR` entries
and no active `ODM` entries. The three package paths, module names and versions
agree with the extracted inputs. Its SHA256 is
`77c8b054a58d64c9568c30d150bb36465b89107eac48cb8545600fdc75a1f02b`.
The read-only collection used the existing explicitly authorized Nezha identity
and matching baseline fingerprint. It did not change the phone.

The later content comparison has **five positive hash matches and three
unavailable reads**. All 6,348,800 package bytes and both XML fragments, 373 and
349 bytes, matched. Direct reads of the three active `apex_manifest.pb` paths
returned permission-denied text even though ADB reported transport success.
Those 72/75/63-byte responses are diagnostics, not different manifests. The
original comparison's `all_matched=false` is preserved. There was no privilege
escalation or retry with changed access controls. Separately, each extracted
ZIP manifest matches the manifest inside its own EXT4 payload byte for byte.

CAS declares the five common external libraries `libbinder_ndk.so`, `libc.so`,
`libdl.so`, `liblog.so` and `libm.so`, plus `:mediacas`. The colon entry denotes
the vendor mediacas namespace, not a library filename. The pinned linkerconfig
source maps it to the vendor mediacas directory. The exact vendor image also
contains a captured `lib64/mediacas/libclearkeycasplugin.so`; its direct ELF
dependencies include both protobuf 21.12 libraries, stagefright foundation,
crypto and the usual vendor runtime libraries. Their namespace and symbol
resolution still require validation.
[Pinned mediacas namespace](https://android.googlesource.com/platform/system/linkerconfig/+/12743643593c9f13784ed30424db2ea09a7bc65f/contents/namespace/vendordefault.cc)

Widevine bundles six shared libraries alongside its service. Its manifest also
requires `liboemcrypto.so`, which is present at `/vendor/lib64/liboemcrypto.so`
and was captured separately. That library's direct dependencies include
`libQSEEComAPI.so`, `libcpion.so`, `libminkdescriptor.so`,
`libtrustedapploader.so` and `vendor.qti.hardware.display.config-V7-ndk.so`.
Names and hashes establish inputs; they do not prove trusted-app access,
provisioning, a DRM security level, playback or compatibility with replacement
framework libraries.

The Widevine init fragment declares two service executables. The main Widevine
binary is present; `android.hardware.drm-service.widevine-rikers` is absent from
the complete payload inventory. This is a recorded unresolved declaration, not
proof that the current Widevine service fails, and no replacement binary or
init edit was invented. The Wi-Fi APEX contains only its manifest and
`etc/wifi_compat.json`: the latter declares a vendor flag and an empty
`os_versions` list. No HAL, init fragment or ELF exists in that payload. The
empty list's runtime meaning and Wi-Fi behavior have not been tested here.

The guarded [inspector](../scripts/apex_inputs.py) verified all 29 ZIP entries
through streaming CRC checks and SHA256 readback. It then inventoried 29 EXT4
entries, excluding the three roots, and captured all 16 regular files totaling
5,656,378 bytes. Its 51 successful `debugfs` requests were limited to filesystem
metadata, numeric-inode listings/stat calls and regular-file reads. Images stayed
open read-only, symbolic links were not followed, output files used flat names,
and neither firmware executables nor init fragments were executed. The installed
Homebrew `debugfs` 1.47.4 binary and source references are hash-recorded. No
write, force, checksum-disable, activation, mount or repair option was used.

Two initial parser attempts stopped on normal listing details: a trailing blank
line, then exact unused zero-inode slots in `lost+found`. Their failed receipts,
logs and producer scripts remain intact. Narrow handling was checked against
the [pinned debugfs listing implementation](https://github.com/tytso/e2fsprogs/blob/7ee1d505ef3b37831215f490411f346fe57e9053/debugfs/ls.c)
and covered by regression tests; malformed named entries and tool diagnostics
still fail. The completed receipts are `cas-v4`, `widevine-v2` and `wifi-v2`
under ignored `artifacts/firmware-analysis/<package-sha256>/apex-analysis/`.

An independent installed NDK `llvm-readobj` check matched all eight payload ELF
files and the two captured vendor libraries: ARM64/ELF64 little endian, ordered
`DT_NEEDED` entries, SONAME and absence of runtime search-path tags. It did not
load them, resolve their symbols or validate linker namespace access. Public
key and signature members were captured as inert bytes; APEX payload AVB and
container-signature verification were not attempted in this slice.

The existing captures need no repetition. To inspect the same captured package
into a **new** private directory, preserving prior evidence:

```sh
apex_analysis=artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69
python3 scripts/apex_inputs.py \
  --capture-receipt "$apex_analysis/erofs/vendor-apex-capture-v1/receipt.json" \
  --expected-receipt-sha256 11b81a5a735d6ce22a94052fb71491277c210b3730c2a08c20605f2b07ccd55e \
  --source-path /apex/com.android.hardware.cas.apex \
  --package-sha256 b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69 \
  --expected-debugfs-sha256 aacdaf85fab9aab4a555f7ebebba169aff981744f297030d9a2e5813f65b3483 \
  --output "$apex_analysis/apex-analysis/cas-review-new"
```

The package hash argument records the caller's parent provenance; it does not
authenticate the original ZIP. The capture receipt and captured APEX bytes are
independently hash-checked. Offline tests require no phone or native filesystem
tool. Full VINTF checks must consume the observed active list and exact fragments
alongside the [vendor/ODM and framework contracts](vintf-contract.md); their
results remain separate from APEX activation, enforcing policy, proprietary
dependency closure and authorized device feature tests.
