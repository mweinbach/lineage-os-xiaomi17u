# Feature-successor build lessons and cache reuse — September 5, 2026

This record captures what made build `nezha.a6d3109ae93158c498bb30b0`
succeed, what failed on the way, and which outputs can accelerate the next
Nezha build. It complements the [candidate qualification record](package7-feature-successor-20260905.md).
Package7 and its working76 recovery remain the preserved rollback baseline.
The successor was built in the existing single-writer named ext4 environment;
none of these notes authorize deleting an older output, attaching the source
volume to a second writer, or reusing bytes whose recorded inputs no longer
match.

## Successful build identity

- VM: `twrp-nezha-upstream74-20260829`; source: `/work/evolution`.
- Physical output: `/work/out/nezha-feature-fixes-20260905-v1`, reached from the
  source checkout through `/work/evolution/out-nezha-feature-fixes-20260905-v1`.
  Preserve that exact alias and physical directory; do not replace the target.
  The Go build cache is `/work/cache/nezha-framework-go`. Read-only verification
  confirmed these paths, Soong intermediates, host tools and product objects on
  the same persistent ext4 filesystem; the private observation is
  `reports/feature-fixes-20260905/cache-native-paths.json`.
- Source inventory: `reports/feature-fixes-20260905/source-installed.json`,
  SHA256 `20778fdee3c36fa1e42fe53c7c14f8eede047f40531d434e8bc42c5e63892e5b`.
- Admitted unsigned target-files ZIP: SHA256
  `a93f8816068564052da34e72b9e6bb8ff8bb2e0238a7ff1fbe537f0129adb6ba`,
  11,277,109,570 bytes. The admission and transfer receipts are retained under
  `artifacts/build-validation/feature-successor-package-admit-v3/` and
  `feature-successor-package-transfer-v2/`.
- Reconciled target-files ZIP: SHA256
  `26ae30eddfd3716212b08f4c77b9d6674db26c64c8d798e0038208f24331bc9a`,
  11,100,598,089 bytes. The signed images, signing receipt, verification
  manifest and published inventory are under
  `artifacts/avb/nezha/package7-feature-fixes-20260905-v1/`.
- Final eight-image bundle: `artifacts/flash/nezha/package7-feature-fixes-20260905-v1/`,
  manifest SHA256 `8550182663180841592a47cc0a33efa5bb7a76f5d70a197faa4d662f47040c1f`.

These identities are a reusable checkpoint. They do not make a future source
tree, output directory, target-files ZIP, signed image, or device state
equivalent to current.

## Lessons from the build

### Put the original Camera packet in `system_ext`

The first integration placed the presigned Xiaomi Camera under `product`. Its
bundled native libraries depend on the namespace available to bundled system
apps, so the corrected transaction moved the APK, libraries and the matching
permission XML together to `system_ext`. The final APK is at
`system_ext/priv-app/NezhaXiaomiCamera/MiuiCamera.apk`; its permission XML is at
`system_ext/etc/permissions/privapp-permissions-nezha-camera.xml`. Keep those
files on the same partition, retain the original APK bytes, and reject a stale
product copy. The final build passed strict uses-library verification and
dexpreopt with this layout.

### Resume transient host-tool failures from the same output

The full package took three ordinary build attempts. The first stopped in Go
`merge_zips`; the exact Glide merge was rerun in isolation and produced the
317,570-byte, 232-member output recorded in
`reports/feature-fixes-20260905/glide-merge-retry.json`. The second stopped in
the Java VM while R8 processed CrashRecovery; its JVM crash record is retained.
The third completed from the same output without changing sources, compiler
settings or the product configuration.

For the same pinned source identity, preserve completed Soong/Ninja outputs,
verify source and idle state, then resume. A host-process crash alone is not a
reason to clean the output. Do not promote a failed run's partial ZIP or call an
isolated command retry a package success; only the later exit-0 package record
is authoritative.

### Keep AVB capacity changes explicit and propagate their pins

Moving Camera into `system_ext` increased that logical image beyond the frozen
Package7 limit. The successful route added a measured successor logical-budget
profile while retaining physical Super and group capacities. Every consumer in
inventory, materialization, signing, reconciliation and policy-image selection
had to use the same successor profile. Early signing attempts failed when
inventory and materialization still carried old dependency or budget pins.

Do not edit a frozen Package7 catalog to make a successor fit. The frozen
catalog remains in `config/nezha-policy-images.json`; successor consumers use
`config/nezha-policy-images-successor.json`. When tooling changes, refresh all
dependent SHA256 pins as one reviewed cohort and rerun the public contract tests.
A larger logical allowance does not authorize a larger physical partition or
dynamic-partition group.

### Treat idle checks as ownership checks, including zombies

Before a build, admission, Super operation, or large readback, check the sole
VM/volume owner, active build processes and output writers. A defunct process
can remain visible after a crash; classify zombies by process state and parent
ownership rather than treating any matching PID as live work. Recheck idle and
ownership after the operation. Never attach the named ext4 source volume to a
second writer to work around a stale process.

### Separate publication metadata from payload integrity

The first target-files transfer and the final FEC wrapper exposed the same
class of guard failure: a tool wrote its result beneath an ancestor whose stat
metadata was included in the protected snapshot, then rejected the timestamp
change caused by its own publication. The FEC comparisons themselves had
completed successfully. Their failed outer transport was preserved, and a new
read-only collector rehashed the staged controls and completed receipts before
admitting all 42 finite readbacks through the unchanged semantic checks.

Future wrappers should publish outside protected input ancestors or exclude a
new result directory from the ancestor-stat cohort before execution. Never
rewrite a failure as success. Recovery is valid only when it reads completed
receipts without rerunning or modifying the native work and independently
binds the exact inputs, outputs, source cohort, idle state and sole owner.

### Admit only measured byte differences

The reconciler found a prebuilt DTBO alias whose canonical payload matched and
whose difference was limited to reviewed AVB footer representation. The
exception is specific to that DTBO alias and requires recomputed proof; it does
not permit padding, header, payload, source-identity or other alias changes.

Boot qualification likewise rejected the first-stage `init` exact hash until
comparison showed that only its 16-byte GNU build ID descriptor changed. All
other ELF bytes and runtime CPIO owner/mode data matched. Record this as
`initBuildID`-only drift, not as blanket permission to accept rebuilt boot
content.

## Cache and artifact reuse policy

The ignored machine-readable inventory is
`reports/feature-fixes-20260905/cache-reuse-inventory.json`. The useful caches
fall into four groups:

1. **Build cache:** the physical `/work/out/nezha-feature-fixes-20260905-v1`
   tree contains host tools, Soong intermediates, object files, dexpreopt/R8
   products, final images and target-files intermediates. Exact-run resumption
   requires the same source inventory, product, variant, build number, selectors,
   toolchain and output alias. For the next reviewed fix, retain intermediates,
   adopt the new source transaction/build identity, and let Ninja rebuild changed
   dependencies; old final-image qualification does not carry across that change.
2. **Source transaction cache:** the three
   `/work/validation/feature-fixes-source-20260905-v*` records preserve
   preimages and exact installed bytes. Use them to audit or roll back their own
   scoped writes. They are not a substitute for checking the current checkout.
3. **Host qualification cache:** the admitted ZIP, signed/reconciled set, Super
   transfer/readback, FEC recovery and final bundle are immutable evidence for
   this build identity. Reuse their tools and receipts as pinned inputs; do not
   reuse their conclusions for a different archive.
4. **Private retained inputs:** signing keys, Camera packet, stock images and
   retained firmware stay in ignored/private locations. Reuse requires the
   recorded size and SHA256, expected device/firmware provenance, exact public
   key derivation and the current contract pins. Never copy private keys into
   the VM, logs, source tree or repository.

For a subsequent source fix, choose deliberate incremental reuse of this working
output after source/configuration admission; a clean output is not the default
response to a source change or host-tool crash. Product/toolchain changes may
require a separate output after review. Before reusing mutable intermediates,
retain the prior admitted target-files, signed set, bundle and receipts as
immutable host artifacts. Always produce new admission, signing, reconciliation
and qualification receipts for the next image identity. Historical native output
paths are point-in-time evidence and must reject later changed bytes. Keep the
original Package7 output and rescue artifacts intact.

The existing runner already uses this output and persistent Go cache. After the
normal source, sole-writer and capacity preflight, resume only the needed goals
with `python3 reports/feature-fixes-20260905/build_successor.py <goals>`; for
packaging, select `target-files-package` by itself. Do not run `clean`, remove
Soong intermediates, prune the named volume, or enable a new compiler-cache
launcher as an incidental speed tweak. No new build was launched merely to
create these cache records.


## Installation preflight lesson

The booted Package7 phone reports `ro.bootmode=unknown`, so the first Android
collector rejected it despite completed boot and running framework services.
The failed capture remains under
`evidence/feature-successor-install-20260905-v1/android-before/`. The maintained
collector now accepts that exact case only with physical Xiaomi/Nezha/canoe
identity, USB ADB `device` state, completed boot, running primary Zygote and
SurfaceFlinger, and absent recovery/TWRP markers. Incomplete or conflicting
states still fail. Commit `f87015b` adds the positive and rejection regressions;
the subsequent complete offline suite passed all 4,638 tests.

The [installation record](package7-feature-successor-install-20260905.md)
captures the resulting writes and boot. Its first flash wrapper compared raw
`os.stat_result` values around the Super write and stopped after fastboot exit 0.
That comparison includes access time, but its before fields were not serialized;
the exact changed field is therefore unproven. A fresh full hash matched the
pinned Super image, the remaining companions were written, and Super was not
repeated. Future device-write wrappers must serialize the complete before cohort
and distinguish stable input identity from read-sensitive metadata.
