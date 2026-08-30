# Factory Camera build-only input packet

`camera_apk_inputs.py` prepares a separate source packet for a future Android
Camera component build. It preserves the original factory APK and leaves
product packages, Make namespace exports, permission admission, SELinux signer
mapping and image adoption closed. It does not install sources or run a guest
build. The [factory inspection](factory-camera-apk.md) remains the authority for
what has actually passed on this APK.

The [contract](../config/nezha-camera-apk.json) pins the 204,365,218-byte APK,
its capture and image identities, the reviewed v3 signer evidence, the existing
nine-file runtime bundle, the source lock and the DEX-provider source state.
There is no signing operation or key input. Soong's preprocessed packaging
stamp is a ZIP/layout check, not cryptographic signature verification; the
exact APK hash binds the independently verified signature.

## Packet and source installation boundary

The packet has `source/`, `source-install.json` and `camera-apk-inputs.json`.
The only source destination is the new namespace
`vendor/xiaomi/nezha-camera-apk-check`. Its Blueprint imports the existing
`vendor/xiaomi/nezha` namespace for `miui-cameraopt`; the two Window providers
remain the pinned platform modules. No existing bundle is modified.

The uniquely named `nezha_factory_camera_build_check` import retains
`preprocessed: true`, `presigned: true`, `privileged: true`,
`product_specific: true` and strict library checks. Its optional declarations
are exactly `miui-cameraopt`, `androidx.window.extensions` and
`androidx.window.sidecar`, in order, with no required declarations. Defaults
for dexpreopt remain unchanged. No signing, alias, override, strip, compress,
missing-library or check-skipping property is generated.

The APK source is a tagged output of the content-verifying producer, not a raw
prebuilt guarded only by a separate stamp. The producer checks every declared
control and payload before publishing the verified APK and then its success
receipt. It retains the checked bytes through publication, rejects input/output
overlap and reused outputs, and removes only its own published files after a
failure. All copying preserves APK bytes.

The producer verifies its declared inputs only. Its receipt does not prove that
the whole namespace, the verifier itself or the surrounding build graph stayed
unchanged. Host/source readback establishes the exact namespace; the future
runner must freeze and reverify it, including the verifier tool, before graph
creation and execution.

Host verification reconstructs the Blueprint, producer, source inventory and
receipts from the pinned contract. It rejects changed or resealed controls,
extra files/directories, symlinks, incomplete copies and output paths inside
preserved inputs. `verify-installed` reads back the exact new namespace, checks
the required Soong project/revision/file hashes, and checks the existing nine
runtime inputs plus their Blueprint. It does not infer product membership,
graph correctness or permission/MAC admission from that readback.

The current device generator does not yet admit this packet. Its coordinator
must add a separate explicit source-install binding before copying any files
into the guest. Do not append these modules to the existing runtime bundle,
add `PRODUCT_PACKAGES`, or export this namespace to Make.

## Host reproduction

Use fresh ignored destinations; existing outputs are never replaced:

```sh
mkdir -p artifacts/camera-apk-inputs
python3 scripts/camera_apk_inputs.py stage \
  --output artifacts/camera-apk-inputs/NEW
python3 scripts/camera_apk_inputs.py verify \
  --bundle artifacts/camera-apk-inputs/NEW
```

After separately reviewed source installation, the coordinator can run
`verify-installed --bundle PACKET --source-root ANDROID_SOURCE` from a control
workspace. This command is read-only and does not perform the installation.
Offline tests use synthetic unsigned bytes and mocked Git results; they do not
need the private APK, SDK tools, a phone, network access or a Linux VM:

```sh
python3 -m unittest discover -s tests -p 'test_camera_apk_inputs.py' -v
```

## Native execution remains a separate admission

The packet records requirements for the future runner, **not permission to
execute a module target**. The pinned importer and dexpreopt request installation.
Core suppresses full-install and Kati copy rules for this unexported namespace,
while retaining packaging specifications and checkbuild inputs. Installation
hooks run before that gate, so graph generation still needs the enclosing
read-only partition protection. Absence from `PRODUCT_PACKAGES` alone does not
protect partition staging.

Resolve the current graph's exact intermediate APK, packaging validation stamp,
strict library status, dexpreopt configuration and real ODEX/VDEX outputs.
The default APK-copy output does not depend on the strict library-status rule;
request and inspect that rule separately. A configuration file alone does not
prove dex2oat ran. Require enabled normal preopt, no ART-only preopt, no relaxed
library checks, all three real providers and the expected class-loader paths.

Before execution, bind the actual graph, sources, configurations and providers.
Inspect the complete selected dependency closure and reject installation or
packaging writes. Permit only reviewed intermediate/tool output roots; expose
installed partition trees and image destinations read-only through every alias.
Reject stale Camera installation artifacts rather than deleting or ignoring
them, and verify installed inventories remain unchanged afterward. Never run
module, phony, wildcard, checkbuild, ROM, image, target-files or OTA targets as
part of this build-only check. Dependencies needing legitimate installation
writes require a separate reviewed phase.

Only a successful real component build can establish the APK graph and its
outputs. Permission enforcement, actual MAC/seapp resolution, image selection
and authorized Camera/Leica device tests remain later gates.
