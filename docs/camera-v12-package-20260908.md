# Camera v12 package, 2026-09-08

**V12 is built, signed and verified on the host. It has not been installed on
the phone.** The installed predecessor is still
[v11r1](camera-v11-install-validation-20260908.md). The new bundle targets its
remaining compressed-DNG save failure, neutral Aperture HDR metadata failure
and two audio conversion failures. It does not establish successor camera,
audio or video behavior.

## Source and compiled components

The source identity is `nezha.0a0b5c6187d711a32aa3e46e`, with 668 rows.
The source receipt is `reports/camera-completion-20260907/source-revision-9/source-installed.json`, SHA256
`ef5452f69c340ce714849f467c4cfe106e31769bc4c40d286d8e9cb0f4a26245`. The ordinary incremental component build and full
`target-files-package` build both passed with the explicit userdebug opt-in.
Before/after checks found all recorded source bytes and modes unchanged.

The [source and host behavior record](camera-save-audio-compat-20260908.md)
explains the DNG writer, exact neutral HDR repair and audio mappings. Two build
integration errors were caught and corrected before delivery: a duplicate
Soong `defaults` property and an omitted Java helper in Aperture's explicit
source list. Both failed revisions and their preimages remain preserved.
Revision 9 is the successful final source.

Actual component checks establish:

- `framework.jar` defines both synchronized DNG save entry points and their
  native declarations. `libandroid_runtime.so` contains the enabled writer.
- The optimized Aperture APK retains the neutral metadata parser. Its saved-image
  callback starts a ViewModel coroutine and dispatches the repair to I/O before
  existing save-success handling. The Nezha device gate, RAW exclusion, bounded
  read, paired capacity writes and rollback path remain in the compiled code.
- Both delivered audio conversion libraries map AIDL output index 19 to legacy
  `0x40000000` and back. Their usage-19 paths return 19 successfully. These
  results come from the delivered ELF instructions and lookup tables; they are
  separate from audio-policy or microphone execution on the phone.
- `cameraserver` remains byte-identical to the verified v11r1 sizing component
  and retains its CFI entry point. Both audio libraries retain CFI entry points.
  The source changes do not alter sanitizer policy.

Seven selected component files are bound by byte identity to both unsigned and
signed archives: the camera server, framework JAR/resources, Aperture APK,
native Android runtime and both audio conversion libraries. The unselected
shared `libcameraservice.so` is absent from the archive and actual system image;
the camera service remains statically linked into `cameraserver`.

## Archive, policy and signed images

The signed target-files archive is 11,145,243,473 bytes, SHA256
`113b87cd7466590580e3a359d50c065bca623b6bdff2e5ad201e916d6ae3abc2`. Signing, reconciliation and the published AVB inventory
passed. The private eight-image bundle is
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v12/`, with manifest
SHA256 `45e4b0b034807b5f4f21a138f7a04244332fb698d8c661c55dc20367eabd28c8`.

All eight payload hashes and sizes passed bundle verification: shared Super,
DTBO, init_boot, vendor_boot, recovery, boot, vbmeta_system and vbmeta. This is
not an OTA or TWRP installer. Installation still requires fresh device admission
and the user's explicit bundle-specific approval.

Camera payload, signer, framework ABI, native dependency and configuration
checks pass on both archives. The 98 policy inputs match the preserved v9
baseline. Normal policy compilation passes; strict neverallow checking still
reports the same 16 existing conflicts and no new ones. The signed image
configuration matches the unsigned configuration across
272 inspected files. These policy/build checks do not establish successor
SELinux runtime state; v11r1's measured normal Android state is Enforcing.

## Tests, resources and retained evidence

After measured image admission and signing-contract updates, `make test-current`
passed 939 tests in 28.950 seconds, and `make test` passed
4,892 tests in 196.162 seconds plus shell checks. The separate save-helper,
audio-conversion, four fully decoded synthetic DNG and retained HDR-image
checks are recorded in the source/host behavior document. They remain distinct
from the actual component, full-build and signed-artifact checks above.

The full build passed disk, OS, architecture, manifest, case-sensitivity and
one-writer preflight. To restore its 200 GiB disk threshold, the host retained
and rehashed two copies of an older f9e Super image before removing only its
generated duplicate from the guest validation directory. Source, build output,
cache and rollback bundles were preserved. The original Package7, predecessor
bundles, working76 recovery, stock return inputs and signing material remain
available.

The [delivery evidence record](../research/camera-v12-package-20260908.json)
binds the source, component, build, package, policy, signing and bundle receipts.
Private images, source checkouts, device captures and keys remain ignored.

## Pending phone validation

V11r1 already saves fully decoded ordinary Xiaomi rear/front photos, main and
telephoto 50 MP, telephoto 200 MP Ultra HDR, Xiaomi Pro RAW and all three
physical rear RAW sensors. It saves all ten warm Aperture effect cases; nine
fully decode as Ultra HDR. Its Ultra RAW DNG save and neutral front HDR case
remain the measured failures addressed by v12. Audio/video acceptance remains
incomplete.

After separate approval, install the reviewed eight-image set without a wipe
or slot change, reboot and capture early audio diagnostics before root ADB
interrupts transport. Validate actual Ultra RAW DNG and preview decoding,
neutral front HDR, audio-policy startup and video tracks, then repeat the
working photo/RAW/effect cases. Useful effect quality, sensor-native resolution
and sustained behavior still need measured evaluation. Full camera acceptance
remains incomplete until the relevant device checks pass.
