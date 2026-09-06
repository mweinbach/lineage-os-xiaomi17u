# Workload-classifier restoration candidate — September 5, 2026

The exact factory classifier now has a reproducible, original-byte private-input
packet and review-only build declarations. **Activation remains blocked.** This
is a useful dependency and integration checkpoint, not a completed power HAL fix
or a demonstrated battery improvement. No package, permission, property, SELinux
rule, CPU policy, thermal limit, or phone state is changed by the default product.

## What was verified locally

The audit starts at workspace commit
`e4993feb94e5ff513eed4d1f433f21ae339da8f2`, using retained factory system-ext
image SHA256 `53dd447bf8453f07b9df24e91a9429c2a15b5589b31406747cc62f0fc79cab5e`.
No new upstream source is selected or depended upon. Original image captures
remain private under ignored artifacts; the tracked
[`config/nezha-workload-classifier.json`](../config/nezha-workload-classifier.json)
pins the APK, model, JNI library, audit facts and template identities. Its three
input identities agree with the pre-existing
[`power-input evidence`](../config/nezha-power-evidence.json).

The 78,238-byte factory APK is `com.qualcomm.qti.workloadclassifier`, version
code 36 / version name 16. SDK 37 `apksigner verify --print-certs` validates its
original signature with certificate SHA256
`c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025`.
It does **not** declare `android.uid.system` or another shared UID. This differs
from PowerKeeper and means shared-UID rejection is not the reason for this gate.
The factory app-domain selection nevertheless specifically requires
`seinfo=platform`; preserving the MIUI APK signer does not make it an
Evolution-platform-signed package.

The manifest requests boot completion, all-package visibility and usage stats.
It marks a boot receiver direct-boot-aware; the service has no explicit
direct-boot-aware declaration. Its unusual API 36 minimum versus API 35
target/maximum metadata is recorded unchanged and needs actual successor package
parsing/startup verification. Nothing patches or re-signs these declarations.

Static Java/Dex inspection shows that this is an APK workload classifier, not
wireless charging support or a general power-manager replacement. It scans APK
metadata/features, runs a model, and feeds workload-type/heaviness and launcher
information to Qualcomm's performance interface. It can rescan when the boot
image timestamp changes and records that timestamp in
`persist.vendor.build.date.utc`. It waits for `vendor.mpctl.init.complete` and
uses a configurable exit timeout. These are concrete integration contracts;
they do not prove that enabling the app saves energy. Scanning itself costs
work, and workload-dependent perf hints can increase as well as decrease power.

The APK includes `com.qualcomm.qti.Performance` and `IPerfManager` classes. The
classifier constructs the no-context Performance variant and calls native perf
methods. A matching selected boot/framework class, JNI registration and linker
namespace must be established; an embedded Java declaration does not prove
native resolution. The `LocalPM` path additionally uses hidden PackageManager
reflection and Binder interfaces. No general hidden-API exemption is emitted.

The 27,672-byte JNI is AArch64 ELF64. NDK 28.2 `llvm-readelf` confirms these
`DT_NEEDED` entries:

| Dependency group | Libraries |
| --- | --- |
| Model runtime | `libtflite.so` |
| Android platform | `libnativehelper.so`, `libcutils.so`, `liblog.so`, `libutils.so`, `libbase.so` |
| C/C++ runtime | `libc++.so`, `libc.so`, `libm.so`, `libdl.so` |

It imports TensorFlow Lite **C++** model/interpreter symbols, so a library with
the right filename alone is not sufficient ABI proof. Its model path is exactly
`/system_ext/etc/perf/wlc_model.tflite` (92,060 bytes). The bounded factory
system-ext inventory does not contain `libtflite.so`; that is not a claim that
the full factory image set lacks it. The candidate therefore declares and
checks this dependency rather than skipping ELF checks or copying a guessed
runtime. Runtime native affinity behavior also needs measurement; it is not a
justification to apply global scheduler changes.

## Admission gates

1. Preserve the original signature and reconstruct narrowly scoped
   package-specific signer/domain policy. Do not give the MIUI signer general
   platform identity, bypass signatures, or silently re-sign the APK.
2. Restore the required enforcing app policy and exact private-property
   relationship. Existing `vendor_wlc_public_prop` / mpctl mapping is not the
   missing `vendor_wlc_app` and `vendor_wlc_prop` integration.
3. Resolve the selected hidden-API/perf Java/JNI chain, native namespaces,
   `libtflite` C++ ABI and transitive symbols in a built successor.
4. Verify actual usage-stat permission/app-op, package visibility, package
   parsing, boot and direct-boot service behavior. No blanket privileged grant
   or default app-op mutation is emitted.
5. Complete a defensive review of the custom-broadcast sender boundary. The
   factory receiver is exported without a manifest permission; system events
   use protected broadcasts, but custom control entry points need a supported
   original-signer-compatible boundary. This is a static admission finding, not
   an exploit demonstration or a confirmed runtime vulnerability.
6. Pass native component/image checks, then explicitly authorized installed
   tests of classifier lifecycle, hint delivery/release, denial logs, suspend,
   responsiveness and energy use under matching conditions.

The Android intent-security skill informed gate 5. It caused us to keep the
original component inactive rather than change its signed manifest or presume
that factory provenance establishes safe exposure. No application hardening
patch was applied and no receiver was invoked.

## Reproduce the private packet

From this worktree, run:

```sh
python3 scripts/workload_classifier_inputs.py prepare \
  --capture-root artifacts/power-stock-20260905/wlc \
  --output artifacts/wlc-candidate-20260905-v1
python3 scripts/workload_classifier_inputs.py verify \
  --packet artifacts/wlc-candidate-20260905-v1
python3 scripts/workload_classifier_inputs.py assert-ready \
  --packet artifacts/wlc-candidate-20260905-v1
```

The shown packet already exists: repeat `verify` on it, or use a new output
directory for a second preparation. Existing destinations are never overwritten.
Preparation and verification passed for **three inputs / 197,970 bytes**.
`assert-ready` intentionally exits **2**, reporting the remaining admission gates.
`activation_allowed` and `android_build_verified` remain false even though
`private_bytes_verified` is true. Receipts cannot override admission.

The packet contains:

- Private unmodified bytes under `vendor/xiaomi/nezha-workload-classifier/`.
- A Soong producer that verifies every exact hash/size before emitting inputs;
  each app/model/JNI filegroup consumes that producer's verified output.
- Review-only `Android.bp.in` declarations under
  `device/xiaomi/nezha/workload-classifier/`, with modules disabled and original
  APK preservation, uses-library checks, ELF/symbol checks and no stripping.
- An explicit failing admission include and a deterministic inventory receipt.

It intentionally emits **no `Android.bp`**, active package list, permission XML
or permissive policy. The public
[`workload-classifier.mk`](../device/xiaomi/nezha/workload-classifier.mk)
defaults `NEZHA_WORKLOAD_CLASSIFIER` to false and adds nothing. Setting it true
fails with the actual closure blockers; malformed values fail too. This flag is
not a switch that makes the component ready.

## Measurement handoff

The read-only performance/suspend collector should observe the exact properties
listed in the contract, `vendor.perfservice` and the power/performance service
inventory, the classifier's package state and its usage-stats app-op when
present. Keep unavailable/permission-denied observations distinct from false
values. Do not reset BatteryStats, set properties, grant app-ops, start the app,
send custom broadcasts, or force wake/sleep as part of passive collection.
Correlate real workload durations, boost release, temperature, suspend residency
and energy over matched intervals before attributing gains to this component.

Validation: **28 offline tests passed** for exact capture selection, byte and
template drift, original-byte round trips, disabled admission, path/symlink and
receipt rejection, verified build-producer inputs and product-flag behavior.
Factory `prepare`/`verify` also passed; `assert-ready` failed as designed. This
does not substitute for a native source build, an installed run or a battery
comparison. Main was not changed, and the source VM and connected phone were
not accessed or modified. Retained factory evidence in the original workspace
was read without changing it.
