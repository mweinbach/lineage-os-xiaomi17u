# Exact Nezha stock contract for TWRP

The first TWRP target can be a **separate recovery ramdisk**, without rebuilding
the ROM or substituting its kernel. The factory package has dedicated
`recovery_a` and `recovery_b` partitions, each declared as **104,857,600 bytes
(100 MiB)** by matching GPT, rawprogram XML and partition XML. Its recovery
image contains no kernel, DTB or bootconfig. It still depends on an intact,
compatible `boot`, `vendor_boot`, DTBO and bootloader path; it is not an
independent rescue environment for boot-chain damage.

The [machine-readable contract](../research/twrp-stock-contract.json) records
fresh input hashes, actual image headers, recovery interfaces and unresolved
device tests. This is a static target contract, not a compiled or booted TWRP
release. No phone or guest VM was accessed, and no firmware executable, module,
init command or factory-reset action was run by this audit.

The source is the separately preserved factory-named China package
`OS3.0.309.0.WPACNXM_16.0`, archive SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
It remains user-provided with unverified publisher origin. The Xiaomi.eu
package is retained as distinct evidence. Raw images, ramdisks, modules,
policy, keys and logs remain ignored; only derived facts and hashes are tracked.

| Component | Exact stock contract | Initial TWRP implication |
| --- | --- | --- |
| `recovery` | Header v4, 1,584-byte header, 4,096-byte pages; no kernel; empty cmdline | Build a dedicated ramdisk-only recovery image |
| Recovery ramdisk | Legacy LZ4, magic `02214c18`; 30,407,261 compressed bytes | Retain the compression format, not the old ramdisk size or payload |
| Recovery image budget | 104,857,600 bytes per package slot | Bound the complete image including any AVB footer; live capacity is still separate |
| `boot` | Header v4; 39,963,136-byte kernel; no ramdisk | Keep the exact compatible slot kernel |
| `vendor_boot` | Header v4; 18,107,362-byte ramdisk; 4,496,880-byte DTB; 270-byte bootconfig | Keep the existing slot's hardware and first-stage module inputs |
| `init_boot` | Header v4; 2,916,992-byte generic ramdisk | Do not convert the recovery target into an init_boot replacement |

The stock recovery image SHA256 is
`a6f2c77608026fcfe6221e5191c501b0ac880658f76c55231879ed198ce8a0f9`;
its compressed ramdisk is
`21ed80d706206420f846315e7da86e6112189ef3a22a8e3b5f95f3dad8748af3`.
Fresh AOSP `unpack_bootimg` at
`954bc3ead5e679005fddf3484d247f2557b3c2c9` produced the same ramdisk.
Recovery, boot and init_boot all have empty header cmdlines and zero encoded
OS-version and boot-signature-size fields. A zero boot-signature-size field
does **not** mean AVB is disabled.

Only vendor_boot carries the observed hardware cmdline. Its
`video=vfb:640x400,bpp=32,memsize=3072000` declaration is a virtual framebuffer
setting, not proof of the panel resolution. Do not move that command line,
the DTB, or the bootconfig into the dedicated recovery image. The exact kernel,
DTB and bootconfig hashes remain bound in the JSON and the
[factory boot contract](factory-boot-contract.md).

The vendor ramdisk supplies **430 module payloads under `/lib/modules`**;
recovery itself supplies none. `modules.load.recovery` contains 435 requests,
424 unique names, and a 426-module hard closure after adding
`hdcp_qseecom_dlkm` and `smmu_proxy_dlkm`. Existing static analysis found no
missing hard paths or hard/pre cycles, but did not establish actual loading,
signature trust or full ABI compatibility. Preserve the package's dependency,
alias, blocklist and ordered load files together.

The chosen TWRP-Test `system_core` revision
`9292e0ddea6c1e8ff95abc8d3fedd6dd0c722f31` already loads modules in first-stage
init. Recovery mode selects `modules.load.recovery` and falls back to the normal
list only when the recovery list cannot be statted. An empty file is not a
fallback. Recovery detection checks that `/system/bin/recovery` exists and
that normal boot is not forced. Module loading occurs before second-stage
recovery RC processing, and normal first-stage mounts are skipped in recovery.
Do not add a second full vendor-ramdisk module load to the device RC.
[Pinned first-stage implementation](https://github.com/TWRP-Test/android_system_core/blob/9292e0ddea6c1e8ff95abc8d3fedd6dd0c722f31/init/first_stage_init.cpp),
[recovery marker check](https://github.com/TWRP-Test/android_system_core/blob/9292e0ddea6c1e8ff95abc8d3fedd6dd0c722f31/init/util.cpp)

The touch drivers are a separate dependency. Exact factory DTBO names
`synaptics,tcm-spi`, at 15 MHz, with Xiaomi's touch integration. Neither driver
is in vendor_boot:

| Factory vendor_dlkm module | Bytes | SHA256 |
| --- | ---: | --- |
| `synaptics_tcm2.ko` | 619,608 | `5bfa810e1d94791a99f97b171f0d72310ff9b58404184a3f2aeb7104ed58f973` |
| `xiaomi_touch.ko` | 227,872 | `526a50e096172bb154f7901a2cb305614d2a30d830f47740132cde229411de52` |

Their declared ELF dependency closure has 13 modules; the other 11 occur in
the factory vendor ramdisk. A fresh byte check of the two drivers' versioned
imports found **173/173** Synaptics and **116/116** Xiaomi-touch CRC matches
against the exact factory kernel or module providers. Those are static
matches, not a successful module load or probe. Later recovery integration
needs the two exact drivers, a reviewed load sequence and their firmware;
copying a different phone's touchscreen stack is unnecessary and unsupported.
Stock `/vendor/lib/modules` links to `/vendor_dlkm/lib/modules`; that namespace
is separate from the early `/lib/modules` loader.

The factory ODM inventory and DTBO identify
`synaptics_spi_nezha_00.img`, `synaptics_spi_nezha_01.img`,
`nezha_syna_thp_config.ini` and `nezha_test_limits_S3910P.csv` under
`/odm/firmware`. DDIC IDs 1 and 2 select the `_00` and `_01` firmware;
`_00` is the default. After the initial inventory, a separate bounded capture
preserved and independently rehashed all four files, **439,256 bytes total**,
using the existing EROFS capture tool and a full factory ODM image hash check.
The original reports remain unchanged; a separate follow-up receipt supplies
the content hashes and private staging paths. No firmware was executed or
published. Preserve the DTBO's trusted-touch configuration
(`tvm`, `vm_mode`); this audit does not authorize disabling it.

The factory kernel has `CONFIG_DRM=y`, `CONFIG_DRM_KMS_HELPER=y`,
`CONFIG_INPUT_EVDEV=y` and `CONFIG_INPUT_TOUCHSCREEN=y`.
`CONFIG_FB` and `CONFIG_DRM_FBDEV_EMULATION` are disabled. This makes DRM the
appropriate candidate renderer; a `/dev/graphics/fb0` path cannot be assumed.
All nine P1 panel variant nodes in the exact DTBO have **1200 × 2608** timings,
DSC and command-mode DSI. Synaptics maximum coordinates are also 1200/2608.
A separate `synaptics,panel-display-resolution` property says 1440 × 3200;
it must not override the panel timing evidence. Physical panel selection,
touch axes and orientation, and the userspace DRM pixel format still need a
device test. The panel's 30-bit declaration is not a proven DRM buffer format.

Stock recovery init refers to
`/sys/class/backlight/panel0-backlight/brightness` and writes an initial 200;
the P1 panel DT maximum is 16383. These are stock declarations, not permission
to write a connected phone. The stock ueventd rules name DRM and input device
directories and search firmware in `/etc/firmware`, `/odm/firmware`,
`/vendor/firmware` and `/firmware/image`. Firmware availability has to be
established before treating touch-module presence as sufficient.

USB is also concrete: vendor_boot declares `a600000.dwc3` as the controller.
Stock QCOM recovery init enables configfs, forwards `ro.boot.usbcontroller` to
`sys.usb.controller`, and selects peripheral mode at the path derived from
`ro.boot.usb.dwc3_msm`, with `a600000.ssusb` as its fallback. The gadget root is
`/config/usb_gadget/g1`, with FunctionFS paths `/dev/usb-ffs/adb` and
`/dev/usb-ffs/fastboot`. This supports an authored USB integration without
copying every stock init action or promising successful enumeration.

The stock recovery properties are `ro.secure=1`, `ro.adb.secure=1` and
`ro.debuggable=0`. Its `/adb_keys` entry is only a symlink to
`/product/etc/security/adb_keys`; that is not a suitable key-provisioning plan
for this target. Use explicitly authorized host keys and verify authentication
against the built recovery. Do not import the stock key file or relax
authentication to obtain logs. A static ELF inventory also finds that stock
recovery's `logd` names `libsysutils.so` and `libcap.so`, neither present by
basename in that CPIO. This is not proof of a runtime linker failure, but it
is another reason to build the logging stack from the chosen source rather
than copying the stock executable.

The stock recovery fstab is useful evidence, **not a ready TWRP fstab**. Its
logical rows are ext4-only, while the inspected factory logical images are
EROFS. It describes `/data` using legacy `fileencryption=ice` and `wrappedkey`,
whereas normal vendor fstab explicitly requires
`aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0`, metadata
encryption `aes-256-xts:wrappedkey_v0`, and
`/metadata/vold/metadata_encryption`. It also marks data and metadata
formattable, names `rescue` as `/cache`, and includes `misc` and boot entries.
Do not copy these write and reset paths into the first recovery target.
Later read-only logical mounts need correct EROFS handling, slot selection,
AVB and snapshot semantics. Data decryption and key handling are separate
validation work, not prerequisites for compiling a UI/ADB recovery image.

Recovery contains a **1,611,785-byte monolithic policy**, SHA256
`93ab47624be9fb53108ff4fe0be6599d66d9501b13a5694602c6dd2abea7252c`,
whose header declares binary policy version 30. It also carries its own file,
property and service contexts. That policy has not been adopted or proven to
authorize TWRP. Build and validate the policy for the actual target init,
services, device nodes and TWRP executable, retaining enforcing behavior and
neverallow checks. Neither a permissive kernel command line nor permissive
recovery domains are acceptable substitutes for this work.

The factory recovery AVB footer covers a 30,412,800-byte original image and
contains 2,240 bytes of vbmeta. The embedded signature is SHA256_RSA4096 with
flags zero and rollback index 1; the parent recovery chain uses rollback
location 1. The child vbmeta header's location field is zero, so these fields
must not be conflated. The prior strict factory signature check passed against
the embedded keys, not an independently authenticated Xiaomi trust root.
Changing the recovery ramdisk invalidates that stock signature. No OEM signing
key, verified custom-image trust path or phone rollback-counter read is claimed.

The original read-only phone inventory saw the partition names, but all 30
selected sysfs size/start reads were denied. Package capacities therefore
support the image budget, not installation approval. Temporary `fastboot boot`
support for this kernel-free recovery is also unproven. Any boot test requires
its own authorization, verified geometry and boot chain, actual bootloader
state and a return plan; this work performs none of those phone operations.

The fresh main audit rehashed 29 file inputs, reparsed and hashed all 1,500
entries across the three ramdisks, and inspected 94 recovery ELF payloads.
The input/display audit separately rehashed the exact factory components and
all 430 vendor ramdisk modules. The complete offline workspace suite passed
**1,369 tests**, and record/receipt checks independently rehashed the published
evidence pointers and four captured firmware files. These checks cover the
tooling and static observations;
hardware display, touch, authenticated ADB, pstore/log access, backup/restore,
fastbootd and decryption remain untested.

| Private receipt | SHA256 |
| --- | --- |
| Recovery/header/CPIO/ELF readback | `73139b1139b5638192470c43e9d4b6fa86c0c4e4ce4d7c54c35abbeffbae9c50` |
| Factory display/touch and CRC summary | `3e4a1fe284547498750351c753f3ed98b9496246d7cb7afe4a3d9f366b2ff2dd` |
| Pinned first-stage source readback | `eca88d63a18a4e1717e2e4ba3511fc14d22d30469a2bb97135bcf0122547620e` |
| Four-file factory touch-firmware capture | `8a7f97d8c6461db8910d8cc4602d0cee9815176c55bd0caae87adc465b0576d2` |
