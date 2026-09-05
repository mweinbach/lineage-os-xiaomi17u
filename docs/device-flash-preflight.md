# Read-only device preflight for an experimental Nezha install

`scripts/device_flash_preflight.py` collects bounded observations from one
explicitly authorized USB device. It **never grants flash readiness** and never
changes a slot, reboots, roots, mounts, formats, flashes, cancels a snapshot or
changes a bootloader setting. Host image preparation is separate. A request to
prepare images does not authorize running this collector on a connected phone.

The default is a plan only. No serial, device command or output directory is
needed:

```sh
python3 scripts/device_flash_preflight.py
```

Collection requires all four arguments: `--serial`, `--mode`, `--target-slot`
and a fresh `--output` under this checkout's ignored `evidence/` directory.
`--collect` is an explicit execution switch, not a substitute for the user's
fresh authorization to collect from that particular phone. The target slot is
chosen by the reviewed image delivery plan, never automatically from the active
or inactive slot. The current factory-style Super populates A and empties B;
see [the image-bundle limits](experimental-flash-bundle.md).

## Modes and exact read scope

| Mode | Required existing state | Observation scope |
| --- | --- | --- |
| `adb-android` | Authorized Android ADB, completed Android boot, Xiaomi / `nezha` / `canoe`, no recovery marker | Selected properties, existing UID, page size, SELinux, mountinfo, bootconfig, physical block-node identities and capacities |
| `adb-recovery` | Already-running authorized recovery ADB, Xiaomi / `nezha` / `canoe`, recovery service/PID, no running Android framework markers | Same reads; optional bounded firmware and Super-prefix reads require existing UID 0 |
| `fastboot-bootloader` | Already-entered bootloader, `is-userspace=no`, `product=nezha` | Only fixed `getvar` queries, including independent bootloader lock state, next-boot slot, slot health and physical capacities |

No mode transition is included. A missing tool, permission denial or unsupported
query remains missing evidence. There is no `adb root`, `su`, remount, automatic
service repair, reboot to recovery, reboot to bootloader or fastbootd fallback.
Android/recovery ADB uses the existing collector's `selected_transport` and
`bounded_run` primitives. Every remote shell call uses the pinned transport and
shell-v2 exit status; tokens are checked against a finite allowlist and quoted.
An explicit `usb:` inventory marker is required, and nondefault ADB server
environment overrides are refused. Device identity, all mode markers, recovery
PID, running slot and transport state are checked again before optional raw
reads and at the end.

The exact common shell reads are exported by `read_allowlist(target_slot)` in
the script: selected `getprop` names, `id -u`, `getconf PAGESIZE`, `getenforce`,
`cat /proc/self/mountinfo`, `cat /proc/bootconfig`, and `pidof recovery` for
recovery identification. For each physical partition, the collector reads
`readlink -f`, `stat -L -c %F:%t:%T` and `blockdev --getsize64`. It does not run
an unrestricted command or pull a directory.

Installed working76 recovery reports a donor `ro.board.platform=xiaomi_sm8750`
and `ro.bootmode=unknown`. Recovery collection therefore additionally requires
exact live `/proc/device-tree/model` and `/proc/device-tree/compatible` bytes
for Nezha SM8850/canoe. These reads are repeated before raw capture and at the
end. Only `canoe` and the observed recovery donor property are accepted; this
does not change normal Android's `canoe` requirement. An unknown recovery boot
mode requires an ADB `recovery` transport, a running recovery service/PID and
no Android framework services. Block-node validation accepts both GNU's
`block special file` and Toybox's `block device` labels with hexadecimal
major/minor numbers; character devices and ordinary files remain refused.

Physical names are both suffixes of `boot`, `dtbo`, `init_boot`, `recovery`,
`vbmeta`, `vbmeta_system`, `vendor_boot`, `countrycode` and `pvmfw`, plus shared
unsuffixed `super`. There are no logical-partition getvars or `getvar all`.
Observed bytes are compared with recorded package budgets. That comparison is
not a hash check of a proposed image, source provenance or final flash admission.

Bootloader queries are `product`, `is-userspace`, `version`,
`version-bootloader`, `version-baseband`, `unlocked`, `current-slot`, `slot-count`,
`max-download-size`, `snapshot-update-status`; `slot-successful`,
`slot-unbootable` and `slot-retry-count` for `a` and `b`; `has-slot` for each base
name; and `partition-size` for the 19 physical names. Malformed, duplicate,
empty and unsupported replies stay unknown even if the process exits zero.
`current-slot` in bootloader denotes the next boot slot; it is not automatically
the same fact as the running Android `ro.boot.slot_suffix`.

Bootloader `product=nezha` alone does not supply board or hardware-region proof.
The bootloader receipt leaves board identity unknown for a separate, same-device
join to authorized ADB/physical identity evidence. Do not choose global firmware
from a modified-ROM model name. The earlier phone baseline reported China
hardware with globally branded xiaomi.eu model strings.

## Optional scopes

`--include-boot-control` permits only getter operations: `hal-info`,
`get-number-slots`, `get-current-slot`, `get-active-boot-slot`,
`get-snapshot-merge-status`, `get-suffix 0/1`, `is-slot-bootable 0/1` and
`is-slot-marked-successful 0/1`. No setters are allowed. HAL lookup can activate
a lazy service; opt in only when that observation scope is authorized and the
existing HAL is appropriate. A failed initial HAL query stops further HAL
queries, without installing or explicitly starting a service. False boolean
getters use their documented exit 70 / stdout `0` convention; HAL failures and
unrecognized values remain distinct.

`--include-firmware` in root recovery reads exactly 1 MiB from each selected-slot
`countrycode` and `pvmfw` block node, twice. `--include-super-metadata` reads the
first 1 MiB of the physical Super, twice. The only raw command form is `dd`
with a fixed `if=...`, `bs=4096`, `count=256`; there is no `of=`, device-side
redirection, pipeline or arbitrary input path. Raw sources must resolve to distinct physical UFS partition nodes; device-mapper
paths and aliased major/minor identities are refused. Readlink, device type/major/minor
and capacity must remain stable, both full read bodies must match, and any
short read, extra output, process failure or byte limit prevents acceptance.
A failed first read does not trigger the second.

Firmware comparison runs entirely on the host against the maintained
[signing contract](../config/nezha-avb-signing.json), loaded through its existing
strict validator. It computes SHA256 of the recorded salt followed by the
AVB-authenticated region: 32 bytes for countrycode and 778,240 for pvmfw. It also
compares the full 1 MiB reference-image extent. A padding/footer difference can
therefore be reported separately from a payload mismatch. This is not a claim
about unrelated firmware or secure bootloader trust, and it never adds firmware
to a write list. A later signed root must still use these same reviewed
firmware descriptors.

The Super prefix is only captured and hashed here. Host LP parsing remains
explicitly pending; it must verify the geometry, all metadata copies and
physical bounds using the measured full Super size. A prefix cannot prove the
hashes of all logical contents, current snapshot idleness or a fallback slot.
No sparse image, filesystem or device-mapper mapping is created on the phone.

## Snapshot and rollback limits

Do not substitute `snapshotctl dump`. In the pinned
[`system/core` snapshot sources](https://github.com/Evolution-X/system_core/tree/241488ea392c01079941d86ddc458b8a0c9ae6e1/fs_mgr/libsnapshot),
constructing `DeviceInfo` can map and mount scratch OTA metadata. Dumping a
merging state can also start snapuserd. These side effects are outside this
collector's scope. Do not mount `/metadata` to make a status read succeed.

A snapshot status of `snapshotted` or `merging` blocks direct image installation.
An unsupported status, `unknown`, or incomplete evidence is not idle. Even
`none` remains a scoped observation; this helper leaves `snapshot_idle_verified`
false for review alongside LP state, active updates and any already-mounted
metadata evidence. No snapshot cancellation or merge is included.

Fastbootd is deliberately refused in the independent bootloader mode. The
[pinned fastbootd source](https://github.com/Evolution-X/system_core/tree/241488ea392c01079941d86ddc458b8a0c9ae6e1/fastboot/device)
derives its lock answer from Android verified-boot properties, can map logical
partitions for capacity queries, and has mode-specific slot-success rendering.
It is not interchangeable with the proprietary bootloader's independent state.
The standard query protocol is documented in the
[pinned fastboot README](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/fastboot/README.md);
getter semantics come from
[pinned bootctl](https://github.com/LineageOS/android_system_extras/blob/52c6bff46ba509eae3ae016e6cd7724d377d5da1/bootctl/bootctl.cpp).

There is no invented `getvar rollback-index` or Xiaomi OEM `anti` query. No
standard getter for secure stored per-location AVB indices is assumed. The
local libavb_user implementation returns a stub zero for rollback reads, and
`avbtool` reports image indices, not secure device storage. An image currently
accepted on this phone can inform a later device-specific risk review, but is
not relabeled as secure-counter attestation. Unsupported counters stay unknown;
this limitation requires an honest review, not fabrication of a zero or an
unattainable attestation requirement that prevents all useful preparation.

## Evidence handling and next decisions

The collector stores both raw streams, exit/timeout/truncation status, command
arguments, byte hashes, timings and interpreted values under private output.
It defaults to 20 seconds per command and 600 seconds total, with maxima of
60/900 seconds and 16 MiB total output. It uses the existing bounded process
runner and stops only its local client on timeout. No device-side kill is sent.
An interrupted/partial collection keeps a manifest with false readiness flags.
Unknown parser results are counted separately from successful process exits.

Before any later mutation, the user still needs a concrete backed-up data and
stock-return plan, an explicit decision on keeping versus wiping encrypted
userdata, the exact device/slot/partition write set, and fresh authorization.
This tool does not verify backup coverage or decryption and cannot authorize a
wipe, slot switch, reboot, rollback bypass or relock. Never relock with the
development key.

Offline tests run without a phone and mock every device/process operation:

```sh
python3 -m unittest discover -s tests -p test_device_flash_preflight.py -v
```
