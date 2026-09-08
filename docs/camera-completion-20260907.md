# Camera capture progress and successor candidate, 2026-09-07

**Installed v8 now has measured Aperture Ultra HDR and RAW capture, standard
RAW from all three rear physical sensors, and 20 successful platform extension
captures. Full camera acceptance remains incomplete.** Xiaomi Camera still
needs its normal service integration and a successful capture; 50 MP, 200 MP,
processed Ultra RAW and the proposed successor's runtime behavior are unverified.

These captures ran on `nezha.f2e3feac321f56f92d2ad7ea`, slot A, with SELinux
Enforcing. They extend the earlier [native-hook checkpoint](camera-native-hook-20260907.md).
The new CameraOpt, platform-signing, auxiliary-package and JPEG_R-default
sources are a separate candidate. The [structured record](../research/camera-completion-20260907.json)
pins retained measurements and source contracts. Original images, raw logs,
proprietary inputs and device identifiers remain in ignored storage.

| Measured surface on v8 | Result | Scope limit |
| --- | --- | --- |
| Aperture rear 0 and front 1 Ultra HDR | Both saved JPEG_R files pass base-image and gain-map decoding; encoded size 3072×4096 | Existing factory property initialization had already run; the new boot default is untested |
| Aperture rear 0 RAW + JPEG | Saved 4096×3072 DNG and companion JPEG; DNG independently decoded | Standard resolution |
| Aperture front 1 RAW | Saved 4096×3072 DNG; independent pixel decode passed | Companion front JPEG is outside the retained verification |
| Rear physical 2, 3 and 4 RAW | Three explicit physical selections saved and decoded DNGs | Default pixel mode, approximately 12.6 MP |
| Platform extensions | All 20 combinations of five modes, two public cameras and two formats captured and decoded | One still after eight preview callbacks per case; image quality and sustained preview are separate |
| Aperture rear Bokeh + Ultra HDR | UI selection, CameraX extension session, save and independent decoding verified | One app-level Bokeh result; other Aperture effects remain unverified |

The [Ultra HDR record](camera-ultra-hdr-20260907.md) explains the startup-order
dependency. An ordinary JPEG configuration ran the existing factory Eco rule
that initialized `persist.vendor.camera.sdk.third.jpegr.enable=1`. Later rear
and front JPEG_R captures succeeded. Their retained files contain 2,372,274 and
7,072,821 bytes; libultrahdr 1.4.0 produced 100,663,296 bytes of RGBA F16 output
from each, with maximum content boosts 1.48872 and 2.26206. The proposed default
applies to a fresh persistent-property store; an existing persisted value still
takes precedence. First-session behavior on a successor boot is unverified.

The physical RAW probe opened logical camera 0 and explicitly selected each
physical output. Each receipt reports the requested active physical ID,
matching image/result timestamps, eight preview results and one still capture.
Kernel sensor-start evidence independently identifies the sensor. All three
DNGs decoded at the captured dimensions.

| Physical ID | Rear role and sensor | DNG dimensions |
| --- | --- | --- |
| 2 | Wide, OVX10500U | 4096×3072 |
| 3 | Ultrawide, S5KJN5 | 4096×3072 |
| 4 | Telephoto, S5KHPE | 4080×3072 |

The platform `CameraExtensionSession` matrix covers public rear 0 and front 1.
Every saved image is 4096×3072. Each cell below represents one captured file
with a complete base-image decode; JPEG_R cells also passed fresh gain-map
decoding. All 20 files and reports were independently rehashed, and all ten
JPEG_R decodes reproduced the retained HDR pixels and gain-map configuration.

| Extension mode | Rear JPEG | Rear JPEG_R | Front JPEG | Front JPEG_R |
| --- | --- | --- | --- | --- |
| Auto | Pass | Pass | Pass | Pass |
| Face retouch | Pass | Pass | Pass | Pass |
| Bokeh | Pass | Pass | Pass | Pass |
| HDR | Pass | Pass | Pass | Pass |
| Night | Pass | Pass | Pass | Pass |

Camera service/provider process IDs and crash-buffer bytes stayed unchanged
within these retained test windows. Probe-reported callbacks and timestamps
were checked for consistency; host validation independently establishes the
saved artifacts. The extension matrix does not isolate rear lenses. Its rear
samples are very dark: rear Auto, Face retouch and HDR have all-zero gain maps,
while rear Bokeh and Night gain maps range only from 0 to 3. These samples
establish capture and format decoding; useful HDR improvement and effect
appearance remain unverified.

Aperture's Photo → Pro settings panel exposed the effect button. Selecting
Bokeh produced a CameraX extension session with a 4096×3072 JPEG_R output and
a saved image after 4.471 seconds. The retained log audit and later artifact
verification agree on the 4,671,264-byte file hash. Its encoded portrait size
is 3072×4096; independent JPEG and libultrahdr decoding passed, with maximum
content boost 3. The early file-list snapshot preceded completion of the save.
The evidence records both configured stream size and encoded orientation.

The source candidate comprises five explicit, default-disabled selections:

| Contract | Intended behavior | Remaining proof |
| --- | --- | --- |
| [JPEG_R default](../config/nezha-camera-jpegr-default.json) | Initialize the measured factory enable value earlier | Generated property and first-session boot result |
| [Auxiliary packages](../config/nezha-camera-aux-packages.json) | Expose auxiliary IDs to the bundled Xiaomi and Aperture apps | Combined build list and app captures |
| [Platform camera input](../config/nezha-camera-platform-signed.json) | Normal Android platform-signing path using unchanged factory APK inputs | Final signature/content, package-data transition, installed grants and labels |
| [CameraOpt native compatibility](../config/nezha-cameraopt-native-compat.json) | Supply the measured query-only `get_cpuset_policy` import | Final artifact checks, JNI loading and initialization |
| [CameraOpt service](../config/nezha-cameraopt-service.json) | Publish the original Binder interface with the complete original verifier and bounded authored services | Final classpath/API retention checks, Enforcing startup, native verification and actual Xiaomi use |

The CameraOpt candidate retains the original platform-signature check, native
cached result and boot-completed callback. Its implemented request surfaces
cover verification, real available status, a temporary camera process OOM cap,
selected camera events and postprocessing completion; the factory's immediate
return for memory-pressure reporting is preserved. **Twenty-two Binder methods
remain unported.** Four have concrete app call paths: `boostCameraByThreshold`,
`reclaimMemoryForCamera`, `notifyCameraPerformanceTime` and `updateCloudData`.
Unsupported one-way calls produce server-side diagnostics, not a client failure
acknowledgment. Genuine prelaunch sampling still lacks an integrated producer.
The original verifier's runtime result is not established by these source checks.

Host validation includes 13 service tests, 35 process-helper harness assertions,
88 native-query harness cases, sampler compilation and exact patch replay.
The service patch also preserves its public helper API under the selected
services.jar shrinker. The first combined suite ran 4,862 tests and failed with
8 failures and 116 errors after the generic generator rejected the reviewed
CameraOpt policy fragment. The corrected generator admits the exact reviewed
fragment while retaining other policy restrictions. A later retained generator
run passed 258 tests. The corrected combined suite then passed 4,865 tests in
189.946 seconds and its shell checks. That suite preceded the additional early
selector and classpath corrections below. The current revision passed 268
affected service/generator tests in 31.654 seconds and `make test-current`
passed 939 tests in 29.119 seconds. The source revision `make test` rerun passed
4,866 tests in 197.413 seconds. After admitting the actual v9 image and updating
the signing contracts, the final rerun passed **4,866 tests in 205.601 seconds**
and its shell checks.

The selected successor source is revision 3,
**`nezha.393aae12fba9ebe8627cdc38`**, with 652 inventory rows. Its source
transaction changed one file from revision 2. The retained source/build sequence
is:

| Source revision | Result |
| --- | --- |
| 1: `nezha.af6d7a77320c30b10d63afd4` | Installed 652 rows, 41 changed files. Build stopped during early dumpvars because `TARGET_DEVICE` was unset. |
| 2: `nezha.cbf3d0c25dde0df6305c66d4` | Corrected the early product/device guard. Kati then rejected inconsistent system-server preopt paths. |
| 3: `nezha.393aae12fba9ebe8627cdc38` | Corrected the two system-server JAR qualifiers; all 498 affected-component build actions passed. |

The [classpath diagnosis](../reports/camera-completion-20260907/classpath-layout-diagnosis/receipt.json)
records that the two modules scheduled installation under `system_ext/framework`,
while unqualified `PRODUCT_SYSTEM_SERVER_JARS` entries advertised
`system/framework` to preopt checking and classpath generation. Revision 3 uses
the supported `system_ext:miui-cameraopt` and
`system_ext:nezha-cameraopt-service` entries in their existing order. Normal
classpath loading, module partitions and strict preopt checks remain enabled.

The [component-build receipt](../reports/camera-completion-20260907/component-build-receipts/receipt.json)
records exit 0 for `libprocessgroup`, `services`, `nezha-cameraopt-service`,
`NezhaXiaomiCameraPlatform` and `framework-res` in run
`20260908T001748-userdebug`. The source inventories before and after the build
are byte-identical at 652 rows. The [full target-files build](../reports/camera-completion-20260907/full-target-files-build-receipts/receipt.json)
passed all 3,339 actions as `20260908T003851-userdebug`, again preserving the
exact 652-row source inventory. Its archive and Super were transferred with
matching guest/host hashes. The unsigned archive passed the Camera APK, JAR/API,
classpath, native dependency and packaged configuration checks. Effective
split-policy compilation passed. Signed images are verified; final archive and
bundle verification remain pending. The installed phone
remains v8; no successor installation or Xiaomi capture is established.

A separate [compiled-component audit](../reports/camera-completion-20260907/component-artifacts-revision-3/component-verification.json)
verified ten stable outputs. The Camera APK uses the same platform signer as
framework-res and preserves all 9,491 original non-signature entries. Built
services.jar retains the public helper constructor and five methods; the
adapter implements all 28 original Binder signatures, and the original factory
JAR remains byte-identical. The compiled service resource and native query
export also passed. These checks will be repeated against the final archive.

The [read-only pre-flash preservation record](../reports/camera-completion-20260907/xiaomi-app/preflash-transition-v9/backup-manifest.json)
retains Camera's two private data directories and file metadata. Both archive
streams were read twice with identical bytes, while Camera was stopped. The
package remains the bundled system app with ID 10422. This provides comparison
and recovery evidence; the signer/data transition remains unverified, and no
data restoration, clearing or uninstall is authorized by the record.

The [packaged SELinux gate](../reports/camera-completion-20260907/config-artifacts-revision-3/policy-gate-v9-final.json)
confirms that the stale vendor policy cache selects normal split compilation.
The exact init options compile the packaged policy and retain all 17 required
CameraOpt type-enforcement accesses. Only the existing userdebug `su` domain is
permissive; the camera domains enforce. The separate strict neverallow compile
fails the same 16 complete rule pairs as v8, with no new conflict and no added
policy exception. Runtime labels, constraints, service access and global kernel
enforcement still require the successor device test.

The [high-resolution source investigation](../reports/camera-completion-20260907/raw-highres/highres-mode-plan.md)
identifies current Pixel/AlgoUp session mode `0x9004`; `0x80f3` is the legacy
route. Mode-specific tables offer 8192×6144 wide/ultrawide and 8160×6144 telephoto
outputs. General/QCFA telephoto tables advertise 16320×12288, but the selected
mode-specific table stops at 8160×6144. The actual factory 200 MP configuration
must resolve that discrepancy. No measured result here establishes 50 MP or
200 MP capture, native 200 MP readout, RAW + 200 MP or processed Ultra RAW.

The ignored evidence is indexed through the structured record, including the
physical RAW matrix, both extension matrices, independent artifact/gain-map
audits, Aperture verification receipts, Bokeh log proof and candidate source
handoff. Preserve the installed v8 and retained v7 rollback evidence while
the remaining build and device gates are completed. The final app cleanup
records effect None, RAW off, Ultra HDR on, USB stay-awake off and camera
stopped, with v8, slot A and Enforcing reconfirmed.
