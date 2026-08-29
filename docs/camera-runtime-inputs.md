# Camera runtime dependency inputs

The [runtime contract](../config/nezha-camera-runtime.json) adds an explicit
class-loader input profile for the four existing Camera DEX JARs. It keeps all
nine selected file paths and hashes from the factory dependency bundle. It
changes only their four Soong module names and adds their declared required
dependencies. No Camera APK, permission grant or new framework implementation
is included. The [APK packaging and signing gates](camera-apk-integration.md)
remain separate from a first platform image.

The fresh host bundle is
`artifacts/vendor-inputs/nezha-factory-camera-runtime-20260829-v1/`.
Its `vendor-inputs.json` SHA256 is
`061cf33a7f062cda6de73a64ebd3d494c04093308b511b4eb42cd4de8f3c865d`.
Staging rehashed both original factory images, the nine selected extras and
generated outputs. All four actual registration XMLs match their declared
names, installed paths and empty required-dependency lists. This is a host
input milestone; it does not establish that the new profile or Soong patch is
installed in the guest or that a native build has passed. Later build evidence
must record those results separately.

The [host evidence record](../research/camera-runtime-inputs.json) binds the
source patch, tools, prepared selection, bundle and independent 32-file
readback. All 97 focused Camera/vendor/provider workspace tests passed with no
skips. That count is separate from the required complete workspace suite.

| Exact module and runtime name | Installed JAR under `/system_ext/framework/` |
| --- | --- |
| `camerax-vendor-extensions.jar` | `camerax-vendor-extensions.jar` |
| `com.xiaomi.hardware.camera.companion-V1` | `com.xiaomi.hardware.camera.companion-V1.jar` |
| `miui-cameraopt` | `miui-cameraopt.jar` |
| `vendor.xiaomi.hardware.postprocservice-V1-java` | `vendor.xiaomi.hardware.postprocservice-V1-java.jar` |

The CameraX runtime name intentionally includes `.jar`, as observed in stock.
The Camera APK directly declares only `miui-cameraopt` plus the two platform
window libraries, all optional. The other three selected JARs must not become
direct APK `uses-library` entries simply because they are packaged. Nor does
an empty XML dependency list prove that proprietary code has no additional
reflection, linking or runtime service requirements.

## Guards and preserved inputs

`vendor_inputs.py` accepts a DEX-only `runtime_library` object with `name`,
`registration` and ordered `uses_libs`. Every name must be exact and unique;
every registration must be a separately selected system-ext XML. Required
dependencies must themselves be selected registered DEX imports. Unknown
dependencies, cycles, duplicate names, namespace aliases, missing XMLs and
extra properties fail before publishing a bundle.

Staging reads the actual hash-verified XML bytes. A registration must contain
one direct library element with the exact name, JAR path and ordered
`dependency` attribute. Hidden dependencies, extra registration policy,
unrelated permission grants, aliases, duplicates, DTDs and namespace ambiguity
are rejected. All selected XMLs are searched for duplicate registrations of a
selected runtime name or JAR path. Required dependency order is preserved in
the emitted Soong `uses_libs` list.

An explicit `uses_libs: []` is emitted even for these four dependency-free
registrations. The unpatched `dex_import` does not accept that property, so it
cannot silently build this profile without its runtime provider. The existing
Soong patch retains strict manifest checks and dexpreopt; it does not invent
class files, permit aliases or add missing-library exceptions. The original
unnamed Camera selection still generates exactly its historical module
definitions, and the older factory/Xiaomi.eu bundles remain unchanged.

The CameraX and postproc XMLs retain the two already-reviewed derivations from
[the original Camera input workflow](camera-inputs.md). No new XML permission
or path transformation is introduced. Vendor/ODM images remain whole original
images in this profile; deriving their SELinux policy is a separate operation.

## Reproduction and native checks

From the workspace, prepare a new selection using the preserved factory
selection and hash-bound source records:

```sh
python3 scripts/camera_runtime_inputs.py prepare \
  --output artifacts/vendor-inputs/nezha-camera-runtime-preparation-NEW

camera_analysis=artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b
python3 scripts/vendor_inputs.py stage \
  --analysis "$camera_analysis" \
  --source-record "$camera_analysis/normalized-layout-v1/firmware-layout.json" \
  --expected-package-sha256 d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b \
  --selection artifacts/vendor-inputs/nezha-camera-runtime-preparation-NEW/camera-runtime-selection.json \
  --capture-receipt "$camera_analysis/camera-comparison-v1/binary-capture/receipt.json" \
  --capture-receipt "$camera_analysis/erofs-contract-v1/xml/system_ext/receipt.json" \
  --output artifacts/vendor-inputs/nezha-factory-camera-runtime-NEW
```

Preparation produces metadata only and explicitly reports that XML/blob hashes
have not yet been checked. The second command performs those checks. Existing
destinations and symlinked ancestors are rejected. The new full bundle replaces
the old bundle only through the ordinary reviewed device admission and transfer
workflow; never install both sets of module definitions into the source tree.

The [provider patch](../patches/evolution/dex-import-uses-library.patch) is
SHA256 `30358a2e304f6a1ad536c4b2ad0a4ad114ab7ddbc649266dd42b89944eb7e708`
against `build/soong` revision
`cbcbea9e65503ca15b363a0b06dda88fdbcb0154`. Preserve any other local changes.
Before applying it, verify its two original file hashes and that the new test
file is absent; afterwards verify all three resulting hashes. The contract
records both sets. In a verified control workspace with its referenced small
metadata files available, use the read-only helper:

```sh
python3 scripts/camera_runtime_inputs.py verify-source \
  --soong-root /work/evolution/build/soong --state base

python3 scripts/camera_runtime_inputs.py verify-source \
  --soong-root /work/evolution/build/soong --state patched
```

These commands inspect the actual Git root/HEAD and patch file bytes. They do
not apply the patch, run a build or replace the complete source audit. Guest
application and builds remain owned by the existing sole VM's coordinator.

After verified installation, the concrete native targets are the four exact
module names in the table, the unchanged JNI target
`nezha_system_ext_lib64_libcamera_algoup_jni_xiaomi_so`, and the four XML module
names in the generated `nezha-vendor.mk`. Build with the existing `user` output
and strict release configuration. Run the added `TestDexImportUsesLibrary*`
Go fixtures with the pinned guest toolchain, then inspect actual product package
membership, generated dexpreopt contexts, installed JAR paths and ODEX/VDEX
outputs. The [earlier host fixture results](dex-import-uses-library.md) are not
native build evidence; their preserved full-suite failures and skips remain.

For a future APK import, verify the actual manifest-check command omits
`--enforce-uses-libraries-relax` and bind the real APK's class-loader context to
the installed library names. The original v3 signature and compressed DEX still
conflict with the selected privileged preprocessed packaging policy. Three
requested platform permissions are signature-only. This dependency work does
not resolve those gates, authorize a signing change or demonstrate Camera/Leica
runtime behavior.

Offline checks use only synthetic inputs and need no phone or network:

```sh
python3 -m unittest discover -s tests -p 'test_camera_runtime_inputs.py' -v
python3 -m unittest discover -s tests -p 'test_vendor_inputs.py' -v
```
