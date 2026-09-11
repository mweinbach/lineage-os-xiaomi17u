# The camera's extra modes: the download works, the load does not, September 11, 2026

**Cause measured on the installed v23. The fix is a reviewed source change and has
not run on the phone.**

## What was reported

The Xiaomi camera's extra modes cannot be downloaded.

## What is actually happening

The extra modes are [Qigsaw](https://github.com/iqiyi/Qigsaw) dynamic feature
splits, not code inside the APK. `assets/qigsaw_5.0.0.0_2.0.json` inside
`MiuiCamera.apk` lists seven, each with a public CDN URL:

| Module | Version | Bytes |
| --- | --- | --- |
| mimojifu2 | 1.3.4@250115 | 179,087,959 |
| movielens | 44.0.0@44 | 127,382,399 |
| clone | 38.0@38 | 74,931,730 |
| vlog2 | 3.13@15 | 27,606,596 |
| panorama | 8.4.1@17 | 18,247,013 |
| milive | 0106@230106 | 10,251,664 |
| ambilight | v1.3.7@20250115 | 2,912,883 |

Every module directory on the phone exists and is empty, which looks exactly
like a download that never happens. It is not. Selecting Panorama produced this,
in order:

```
D nativeloader: Load /data/user/0/com.android.camera/app_qigsaw/5.0.0.0/panorama/8.4.1@17/nativeLib/arm64-v8a/libmorpho_sensor_fusion.so
              ... dlopen failed: couldn't map ".../libmorpho_sensor_fusion.so" segment 2: Permission denied
W MCAM_MorphoSensorFusion: can't loadLibrary morpho_sensor_fusion
D MCAM_Split.FileUtil: Succeed to delete file: .../panorama/8.4.1@17/panorama.apk
D MCAM_Split.FileUtil: Succeed to delete file: .../panorama/8.4.1@17/nativeLib/arm64-v8a/libmorpho_sensor_fusion.so
D MCAM_Split.FileUtil: Succeed to delete file: .../5.0.0.0/panorama
```

The split downloaded, unpacked, and its dex loaded — the failure is inside the
static initializer of a class that came *out of the split*. Qigsaw reads the
failed `dlopen` as a bad install and deletes the module, which is why the
directories are empty afterwards.

The download really is fine. Fetching the panorama split by hand gives
18,247,013 bytes with md5 `3891f5ead83911e32d24b14c7ba7554b`, exactly what the
manifest declares, and the CDN answers the phone in 17 ms.

## Why the library will not map

The camera is signed with the platform key, so it runs as `platform_app` and its
data is labelled `app_data_file`. Asking the kernel what that pair may do:

```
/sys/fs/selinux/access
  u:r:platform_app:s0:c512,c768  u:object_r:app_data_file:s0:c512,c768  class file
  -> allowed 0x1142e7f
```

Decoded, that is `append create getattr ioctl lock map open read rename setattr
unlink watch watch_reads write` — everything the app needs except **execute**.
Mapping a library's executable segment needs it, so the `mmap` returns `EACCES`
and the linker reports "couldn't map segment 2". No `avc: denied` appears in the
log, because the platform policy carries a `dontaudit` for this exact access;
the linker message is the only evidence.

This is W^X working as designed — and as Android relaxes it for the cases that
need it. Stock HyperOS allows it: the retained `/data` on this phone still
carries a package-manager record of `.../app_qigsaw/5.0.0.0/panorama/8.4.1@17/panorama.apk`
from before the ROM was installed.

## The fix

One rule, in the already-wired product policy directory
`device/xiaomi/nezha/sepolicy/product/private/platform_app.te`:

```
allow platform_app app_data_file:file execute;
```

Pinned by [`config/nezha-camera-split-modules.json`](../config/nezha-camera-split-modules.json).

`execmod` and `execute_no_trans` are deliberately withheld. None of the nine
libraries in the panorama split declares `DT_TEXTREL` or the `TEXTREL` flag, so
mapping them needs `execute` alone, and nothing here calls `execve`.

No AOSP neverallow covers this. The app-data execute neverallows in
`private/app_neverallows.te` name `all_untrusted_apps`, and the sensitive-domain
list in `private/app.te` (`bluetooth`, `isolated_app_all`, `nfc`, `radio`,
`shared_relro`, `sdk_sandbox_all`, `system_app`) does not include
`platform_app`. Both types are public, so product-private policy may add the
rule.

## What it costs

The grant is not camera-specific. Every platform-key-signed app gains the
ability to run native code it wrote into its own data directory. On the
installed v23 that domain holds five processes, all signed with the same key as
the rest of the image:

```
com.android.camera            com.android.systemui
com.google.android.packageinstaller
com.android.bluetooth.bthelper   com.google.android.flipendo
```

Two narrower designs were rejected:

- **A private data type for the camera alone** (`type=` in `seapp_contexts`)
  would scope the grant to one app, but a large number of platform rules name
  `app_data_file` literally instead of the `app_data_file_type` attribute, so the
  camera would silently lose access it has today.
- **A private domain for the camera** would have to re-derive everything
  `platform_app` grants it, with a camera that fails to start as the failure mode.

## What this page does not prove

That a mode installs and runs. That is a device result for the delivery set that
carries the rule. Only Panorama was exercised; the other six modules were never
observed downloading, and whether any of them needs a permission beyond
`execute` once its libraries load is unknown.

Sanitized record:
[`research/camera-split-modules-20260911.json`](../research/camera-split-modules-20260911.json).
