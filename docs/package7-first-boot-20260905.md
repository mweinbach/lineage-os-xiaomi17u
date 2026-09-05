# Package7 first flash and failed first boot — September 5, 2026

The user explicitly requested the experimental first flash after reviewing the
recovery/firmware/LP results and accepting loss of phone data. The exact bundle
manifest remains `004650a587064b6b9a8438cc69c9ce168f89c2769544498fac51797ad0389308`.
A fresh portable verification and same-device bootloader preflight passed their
scoped checks before any write. Unsupported version/has-slot queries remained
unknown. No force, verification-disable, relock or firmware-write options were used.

## Installation result

All eight fastboot writes returned zero: shared Super, dtbo_a, init_boot_a,
vendor_boot_a, recovery_a, boot_a, vbmeta_system_a, then vbmeta_a. Super used a
512 MiB sparse transfer limit below the reported 768 MiB maximum download size;
all twenty chunks were written, total reported Super operation 232.986 seconds.
All sixteen saved write streams match their recorded hashes. This is fastboot
write acknowledgement, not a complete post-flash raw partition readback.

No slot change, userdata/metadata erase or format, bootloader firmware write,
relock, or stock restore was performed. The phone booted the candidate on A.
ADB reports Evolution X 16.0, build ID
`nezha.128c96ed5e626cdd0d213542`, and BP4A.251205.006 test-keys. Zygote,
SurfaceFlinger and boot animation ran. Android boot completion was not reached.
The reported Google Canary fingerprint is not independent build provenance;
the incremental identity and known written bundle are recorded separately.

## Observed failure

System server repeatedly aborts during PackageManagerService startup:

```text
java.lang.RuntimeException: There must be exactly one installer; found []
at com.android.server.pm.PackageManagerService.getRequiredInstallerLPr
```

GooglePackageInstaller is present under `/system/priv-app` and scanned live.
Its exact Package7 manifest declares an exported, direct-boot-aware installer
handling INSTALL_PACKAGE with DEFAULT/content/APK MIME, plus original-package
`com.android.packageinstaller`. Live Package Manager renames it to replace the
retained package and reports duplicate app ID 10095. This supports investigating
inherited package/user state, but does not prove which persisted setting causes
the resolver failure. Do not add another installer or weaken the framework check.

The failure was captured, then the phone was returned to bootloader to stop the
crash loop. Final queries confirm proprietary Nezha bootloader, unlocked, slot A,
snapshot status none. No working Android or complete-ROM success is claimed.

## Next controlled experiment

A separately approved clean-data boot would isolate inherited package state
from a clean-image installer/resolver defect. It must explicitly reset userdata
and its encryption metadata, preserve the eight installed images and firmware,
then attempt boot with stop-and-capture behavior. Data disposability is recorded;
this attempt deliberately performed no automatic erase/format. A clean-data
retry is not guaranteed to fix the observed failure.

Private serial-bearing commands and logs remain under
`evidence/package7-first-flash-20260905T145831Z/`: execution.json, write streams,
first-boot.json, first-adb-properties.json, crash.log, startup-expanded.log,
package-dirs.log and final-bootloader.json. The exact installer manifest is
`reports/flash-ready-20260904/signing-successor/archive-gzip/package7-original-v1/direct-and-apex/commands/0389/manifest.stdout`.

No tooling code changed in this flash attempt. Evidence hashes and documentation
were checked; the preceding 4,610-test tooling run is not relabeled as a device test.
