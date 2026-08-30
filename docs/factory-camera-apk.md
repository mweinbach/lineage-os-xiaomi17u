# Original factory Camera APK inspection

The Camera APK captured from the selected factory package passes the pinned
**preprocessed, privileged APK packaging check without any transformation or
check bypass**. Its eight DEX files are already uncompressed. This removes the
compression blocker for this input, while the earlier Xiaomi.eu/live APK keeps
its recorded failure. Neither APK has been selected in the Evolution product.

The [inspection record](../research/factory-camera-apk.json) binds the original
capture, pinned tools, validator commands, permission review and SELinux
metadata. Checks completed August 30 UTC, August 29 local time. They are host
checks on real proprietary input, not an Android APK build or device test.

## Input identity and packaging

The original `/product/priv-app/MiuiCamera/MiuiCamera.apk` came from
`product_a.img`, SHA256
`67e6c683c1091abc0a548c27e4681bbe26471529129d15453b95c8d69417795f`,
inside the selected package `d2cf57fd…7820cd8b`. The guarded capture checked the
inventory, inode and byte readback without mounting or modifying the image.
That proves the captured relationship; it does not authenticate an OEM trust
root or the user-provided package's origin.

| Attribute | Factory input | Earlier Xiaomi.eu/live input |
| --- | --- | --- |
| APK SHA256 | `7bce1fb140802511bb3d6527f6fcc25ef7558f278d24229755413d3a9b42199e` | `cadf2c07cb6fd25c06f7fe6f37dc227df204bed3a873b3025aff93d53d72da79` |
| Bytes | 204,365,218 | 170,279,563 |
| Version | `6.3.007010.0` / `630070100` | Same |
| Eight DEX entries | Stored, four-byte aligned | Compressed |
| Privileged preprocessed packaging | Pass | Fail: compressed DEX |
| Verified v3 signer certificate | `c9009d01…2149025` | `f87bd41b…45e869` |

Both declare package `com.android.camera`, SDK minimum 29/target 35, no shared
UID and `extractNativeLibs=false`. Their binary manifests are identical. Their
eight DEX payloads all differ, so the earlier
[guarded-call inspection](camera-apk-inputs.md) cannot establish this input's
code behavior.

The factory signature verifies with one RSA-2048 signer. All 9,494 ZIP entries
pass CRC checks. Both 4 KiB and 16 KiB ZIP-alignment checks pass. All forty
AArch64 JNI payloads are byte-identical to the earlier APK and uncompressed;
all satisfy 4 KiB ELF load-layout checks, while the same three libraries retain
the documented 16 KiB exceptions. ZIP alignment does not prove native linking.

The pinned strict manifest checker accepts exactly the ordered optional names
`miui-cameraopt`, `androidx.window.extensions`, `androidx.window.sidecar`, with
no required libraries or relaxation flag. A wrong-module-name control fails.
All [nine runtime dependency inputs](camera-runtime-inputs.md) were rehashed
unchanged. This establishes matching declarations, not complete dependency
closure or the actual APK's generated class-loader context.

## Privileged permissions and SELinux are separate gates

The manifest requests 70 unique permissions. The pinned platform defines 46;
three others are declared by this APK itself, and 21 external definers remain
outside this review. Two platform definitions have opposite feature-flag
branches: `DEVICE_POWER` and `SUBSCRIBE_TO_KEYGUARD_LOCKED_STATE`. Their effective
installed branches remain unverified; the record preserves both.

The pinned flag definitions confirm that `system` is the deprecated alias of
`privileged` (`0x10`), so `SYSTEM_CAMERA` must be included. Ten requested platform
permissions always contain that bit; `SUBSCRIBE_TO_KEYGUARD_LOCKED_STATE`
contains it in one branch. The existing
factory `/product/etc/permissions/privapp-permissions-product.xml` contains one
Camera block with thirteen allows and no denies, covering all eleven possible
privileged requests. Its other entries are `READ_PHONE_STATE` (dangerous) and
`mediatek.permission.ACCESS_APU_SYS` (not defined in the pinned platform
manifest); those two entries do not establish privileged grants.
The three pure signature requests remain `CONTROL_DEVICE_STATE`,
`CONTROL_DISPLAY_BRIGHTNESS` and `INJECT_EVENTS`. A privapp XML alone does not
resolve their Android signing requirements.

This is provenance for a future narrowly derived Camera allow/deny file on the
same partition as the app. No factory XML or permission grant was added to
Evolution. Static coverage does not prove that boot-time permission enforcement
passes; the effective installed definitions and grant logic still need review.

The factory certificate also matches **global `seinfo=platform` signer entries
in both factory platform and retained vendor MAC permission files**. All five
factory seapp files lack a Camera-specific rule. Factory platform seapp has a
generic `seinfo=platform` rule for `platform_app`, separate from its generic
privileged-app fallback. Evolution's different Android platform certificate
therefore does not by itself establish this APK's future SELinux label.

The captured pinned `SELinuxMMAC.java` confirms that existing vendor MAC files
participate in loading. Package-specific mappings precede global mappings;
matching certificate sets, or supported certificate history, can supply the
base seinfo. The comparator marks compared global entries with equal signer
sets as duplicates regardless of seinfo value, and loading rejects detected
duplicates. It does not perform a separate all-pairs scan, so inspection alone
does not prove the complete factory combination will fail. Validate the actual
composed set; copying another global signer mapping is not justified. No such
copy or signer mapping was added.

The actual composed MAC files and installed seapp contexts must establish the
effective label before APK admission. This SELinux mapping neither grants
Android signature permissions nor proves that the APK will run.

## Next bounded admission check

The record lists the six expected installed framework MAC/seapp outputs and
four retained vendor/ODM image paths. Their current guest existence and
completeness have not been checked by this host review. `SELinuxMMAC`, `Policy`
and `PolicyComparator` are together in the captured Java source; libselinux's
native Android resolver remains a source-capture candidate. Source-only
generated vendor/ODM contexts must not substitute for the metadata actually
retained inside those images. Resolve the conditional permission definitions
against the built framework as part of the permission admission check.

After that check, a separate reviewed input contract can bind the original
APK, its signer, narrowly derived same-partition permission policy and actual
label expectations. Then build the real APK with strict library checks and
inspect its outputs before any authorized device test. No signing, compression,
permission or SELinux exception is proposed, and no boot-readiness flag changed.
