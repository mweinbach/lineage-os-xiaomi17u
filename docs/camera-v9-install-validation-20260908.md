# V9 installation and camera validation, 2026-09-08

**The authorized v9 installation completed and booted on slot A with SELinux
Enforcing. Xiaomi Camera now passes its original verifier, but its first rear
Photo still failed to save.** Camera acceptance remains incomplete.

The installed build is `nezha.393aae12fba9ebe8627cdc38`. All eight writes were
acknowledged: shared Super, then seven A-chain images. Boot completed in 25.3
seconds. There was no wipe or slot change. The retained bundle manifest is
`9db1e3e3e07411f9d884a7c25817e3a164f8e89ddfcf8ad7d2f43dd13c3da958`.
The [structured record](../research/camera-v9-install-validation-20260908.json)
pins approval, execution, boot, package transition and capture evidence.

The active Camera APK matches the final signed archive and platform signer.
It retains app ID 10422. Its measured process domain is `u:r:platform_app:s0:c512,c768`. Before its
first launch, all 501 credential-encrypted
and five device-encrypted data archive members were unchanged; both complete
archives were byte-identical to the preflash copies. This measures the Camera
package transition, not all personal userdata or general device acceptance.

CameraOpt's boot callback completed without native initialization failure.
The real Camera app subsequently received `last_original_verifier_result=true`
from the unchanged verifier. Its first rear Photo request called `adjBoost`,
`sendCameraEvent`, `getSystemStatusJson` and `getVerifyResult`. It also called
the explicitly unported `reclaimMemoryForCamera` once.

The 1× rear Photo shutter produced a preview thumbnail but no saved full image.
The app omitted `xiaomi.snapshot.imageName`; the processing pipeline reported a
missing shot name, returned a different callback name, and the app timed out.
The [vendor-key diagnosis](camera-vendor-key-discovery-20260908.md) records the
APK branch and the actual advertised metadata. The selected source candidate
restores the factory discovery behavior only for this device and Camera app.
A successful installed capture is still needed to determine whether that
correction closes the complete processing path.

V9 regression captures independently saved and decoded rear Bokeh JPEG_R and
telephoto RAW. Aperture's five rear effects—Auto, Face retouch, Bokeh, HDR and
Night—each saved a 3072×4096 Ultra HDR image with full JPEG and gain-map decoding.
All five front effects also saved and fully decoded Ultra HDR photos at
3072×4096. All ten app-level cases are pinned in the structured record. The earlier [v8 matrix](camera-completion-20260907.md)
preserves 20 platform extension captures and three physical rear RAW captures.

Rear effect transitions closed the activity without a fatal process crash.
A cold launch saved a valid HDR image. A later logged None-to-Bokeh transition
identified a 1440×1080 preview rejected by the extension. The
[CameraX cache diagnosis](camerax-extension-cache-20260908.md) identifies an
upstream cache-key bug and records its prepared source backport. Camera service/provider process identities
and crash-buffer bytes stayed unchanged during the admitted capture windows.
Wallpaper `ClockProviderPlugin` crashes exist outside those windows; a clean
whole-device crash buffer is not claimed. These images establish capture and
pixel decoding, not useful effect quality in a representative scene.

The combined successor source is `nezha.0c10ad024d3033691a2825cc`, with 659
verified inventory rows. The vendor-key framework build passed on predecessor
`nezha.8fb05f49f5a7e31a6a3a498b`; the combined Aperture and full target-files builds passed with all 659 source
rows unchanged. See the [v10 package record](camera-v10-package-20260908.md)
for final artifact and delivery verification.
The host checks comprise 35 vendor-key Java assertions, 24 CameraX cache
assertions and 4,881 passing offline tests. Those host checks are separate from the completed Android build. The
successor has not been installed. The next bundle needs its own explicit
flash/reboot approval. Xiaomi 50/200 MP, processed Ultra RAW and full camera
acceptance remain unverified.

Final cleanup restored rear camera, effect None, RAW off, Ultra HDR on and
USB stay-awake off. Xiaomi Camera, Aperture and the test probe are stopped.

Original photos, raw logs, proprietary inputs and device identifiers remain in
ignored private storage. V9 and prior v8/v7 bundles remain preserved.
