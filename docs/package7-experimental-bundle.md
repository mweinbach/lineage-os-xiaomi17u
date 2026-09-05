# Verified experimental Package7 bundle

The off-device bundle was assembled and independently verified on **September
5, 2026 at 02:55 UTC**. This finished about ten minutes after the working
five-hour target. It is ready for review and a separately authorized device
preflight, not an assertion that Evolution X boots on the phone.

The platform remains Evolution X Android 16 QPR2 `bka` / `bp4a`, Xiaomi 17 Ultra
`nezha` / `canoe` / SM8850, 4 KiB pages and normal Android SELinux enforcing.
Source identity is `nezha.128c96ed5e626cdd0d213542`, with 549 selected source files
and all 1,179 locked project revisions/origins verified during the build.

## Artifacts

Private bundle: `artifacts/flash/nezha/package7-20260904-v1/`.

- Eight images, totaling **9,639,995,468 bytes**: `super`, `boot`, `init_boot`,
  `vendor_boot`, `dtbo`, `recovery`, `vbmeta`, and `vbmeta_system`.
- Bundle manifest SHA256:
  `004650a587064b6b9a8438cc69c9ce168f89c2769544498fac51797ad0389308`.
- Signed target-files archive SHA256:
  `ba01cc71fa8122cea665454c194fea540b0a4b6b56a205d7aabc949790704da6`,
  **10,834,328,127 bytes**.
- Sparse Super SHA256:
  `0795239c0e842744974284ad91e0f93662c3eedbf198225b51912d38981302f0`,
  **9,291,737,164 bytes**, expanded size **15,300,820,992 bytes**.

Keep the manifest digest independently from the bundle. Verify a copy with:

```sh
python3 -B scripts/experimental_flash_bundle.py verify \
  --bundle /Users/mweinbach/Projects/lineage-os-xiaomi17u/artifacts/flash/nezha/package7-20260904-v1 \
  --expected-manifest-sha256 004650a587064b6b9a8438cc69c9ce168f89c2769544498fac51797ad0389308
```

Neither the bundle nor target-files ZIP is an OTA or TWRP installer. Proprietary
images and signing material remain private and ignored by Git.

## Verification completed

- Native attempt8 completed the ordinary target-files build and its postchecks;
  source/input callbacks match before and after. Failed attempt7 is preserved.
- The existing Mac development key signs a verified 17-role AVB set. Two-pass
  signing reproduction passes; 14 input leaves and working76 are preserved.
  No private key entered the Linux VM.
- All 455 APKs pass API-36 signature and 4 KiB alignment checks. All 39 APEX
  payloads and 26 CAPEX pairs pass. Three compressed apps and their stubs pass
  the corresponding checks. Five legacy full-range signature failures, known
  overlay duplicates and conditional Shell findings remain recorded.
- Actual signed filesystem exports verify 427 APKs, three compressed APKs,
  36 APEX containers, FamilySpace's two required grants and required Java
  library delivery. These original-ZIP checks are carried to the published ZIP
  by the reconciler's complete member-equality proof, not relabeled as reruns.
- Final boot checks verify five images, 16 ZIP member joins, exact init,
  fstab, 430 ramdisk modules, six metadata files, the 4 KiB kernel, eight DTBs,
  DTBO and working76. Separate DLKM scans verify 484 modules and 11 metadata
  files. These are not module-insertion or boot tests.
- All three original native VINTF commands pass, including the full
  framework/vendor/kernel/APEX command with 39 current APEX packages. Two
  definition-check skips and two warnings remain explicit, not passed checks.
- Classpath validation covers 45 fragments and 70 unique JARs, preserving
  runtime ordering and SDK selection. Original APEX ext4 permissions and
  root-reader access to build properties replace incorrect extraction-directory
  assumptions; both diagnostic failures remain preserved. Runtime class loading,
  APEX activation and SELinux access are untested.
- Super assembly, full readback and transfer pass. All eight embedded image
  hashes and six metadata copies match; logical B is empty. Populated extents
  contain neither DONT_CARE nor LP ZERO coverage. Bundle assembly and separate
  portable verification both pass against the independently derived digest.
- Latest complete workspace tooling run: **4,602 tests passed, zero skips**.
  Focused runner tests, native execution and physical-device tests are separate
  evidence categories.

## Required before any phone changes

The subsequent [authorized device preflights](device-preflight-20260905.md)
confirm the same device, unlocked proprietary bootloader, slot A, matching
physical capacities and bootloader snapshot status `none`. Fresh verification
confirms all eight image lengths fit, including expanded Super. The stock return
images and rescue recovery were rehashed. The user accepts loss of phone data.
The authorized recovery round trip now verifies retained target-A firmware
contents and all six live LP metadata copies. The phone is back in bootloader
mode. Secure rollback counters and actual stock restoration remain unknown.

**No phone was accessed or changed for this milestone.** `flash_ready` and
`complete_rom_ready` remain false because device admission and boot are pending.
An explicitly identified, authorized device is required even for collection;
flashing, wiping, rebooting and slot changes require a fresh explicit request.

Confirm exact variant, current slot, unlocked state, target-A capacities,
snapshot/update state, retained firmware, USB/bootloader reentry, power and
off-device backups. Decide whether a first install preserves data or uses an
explicitly authorized clean install. Neither option proves existing encrypted
data will survive a first boot.

**Shared Super replaces the logical fallback, including B.** Leaving B's
physical boot images untouched does not preserve a bootable stock B system.
The bundle contains A candidates only; no write order or device is selected.
`countrycode` and `pvmfw` remain retained-device references, not bundle writes.
Never relock on the development key or disable verification to make a test run.

The original China return set remains separately verified and preserved. Stock
return requires its original recovery/vbmeta pairing; working76 is a separate
rescue image. This does not restore the exact prior xiaomi.eu state or userdata.

Camera uses Aperture; factory Xiaomi/Leica APK integration is not selected.
The Android IMS provider stack is not integrated; VoLTE, VoWiFi and emergency
calling are unverified. Storage/encryption, display/touch, radio, networking,
audio, sensors, fingerprint, camera, charging, thermals and accessories still
need actual device testing. Working76 UI/touch/root-ADB testing used stock
companions and does not prove the new Evolution boot chain.

Machine-readable current evidence is in `research/flash-readiness.json`.
Detailed records remain under the ignored `reports/flash-ready-20260904/` tree.
