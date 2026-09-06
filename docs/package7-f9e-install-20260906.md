# Package7 UI, camera and shade successor installation — September 6, 2026

The user explicitly authorized installing the exact successor bundle whose
manifest SHA-256 is
`78693f3eb040b61dd7972bf4e432ab9d8f9000e7c6d1b433373f41a1711e4c85` on
the selected physical Xiaomi Nezha device, followed by a normal reboot. The
authorized operation writes the shared physical Super and the seven slot-A
physical-chain images. It does not authorize a wipe, format, slot change,
bootloader lock change, firmware write, recovery detour or verification bypass.

## Reviewed installation scope

The reviewed order and destinations are:

1. `super` to the shared, unslotted `super` partition, using a 512 MiB sparse
   transfer limit
2. `dtbo` to `dtbo_a`
3. `init_boot` to `init_boot_a`
4. `vendor_boot` to `vendor_boot_a`
5. `recovery` to `recovery_a`
6. `boot` to `boot_a`
7. `vbmeta_system` to `vbmeta_system_a`
8. `vbmeta` to `vbmeta_a`

The shared Super contains populated slot-A logical partitions and empty slot-B
logical partitions. Writing it changes the logical layout for both slots and
removes the prior logical fallback. It does not change the active physical slot;
all seven slotted destinations remain explicitly on A.

Before the first write, the host-side installer requires the exact manifest,
all eight image hashes and sizes, the selected serial binding, fresh reviewed
Android and bootloader preflight records, unlocked state, slot A, and explicit
flash and reboot authorization. It refuses wipe or slot-change authorization,
an existing execution record, duplicate or unexpected roles, indirect payload
paths, changed payload content, or a destination outside the reviewed set. It
checks slot A immediately before each write and stops after a failed fastboot
exit, changed input identity or changed input file metadata. Reboot is a
separate guarded step after all eight writes are acknowledged.

No `erase`, `format`, `set_active`, relock, `--force`, `--disable-verity` or
`--disable-verification` operation is part of this installation.

## Execution status

All eight fastboot writes returned zero in the reviewed order. Every record
reports `acknowledged`, an unchanged input-file metadata signature and a fresh
post-write match to the manifest hash and size. Shared Super completed in
236.477 seconds; the other seven writes completed individually in 4.662 seconds
or less. These results are fastboot write acknowledgements with host-side input
reverification, not raw partition readbacks.

The bootloader reported slot A again after the eighth acknowledgement. The
separate `fastboot reboot` then returned zero. Its receipt records that all eight
writes had been acknowledged, slot A was observed, and no wipe or slot change
was performed.

## First boot and live configuration

The boot observer reached `sys.boot_completed=1` after 25.5 seconds and read the
exact installed incremental identity `nezha.f9e30611efe01b882f9ed0cb`. Zygote
and SurfaceFlinger were running and boot animation had stopped. The live device
reported slot A, file-based encryption and enforcing SELinux. This establishes
a completed first Android boot of the written successor; it does not establish
post-unlock retained-userdata access or individual feature behavior.

Live resources expose the intended UI configuration: pixel pitch `60.583`,
status-bar top padding `38.0px`, rounded-corner content padding `100.0px`, and
shade alignment enabled. These values show that the packaged resources loaded.
They do not prove the visual result. The captured boot screen shows the normal
PIN-required lock screen with the existing wallpaper; no fingerprint glyph is
expected there before the first unlock after boot. Post-unlock UDFPS and shade
visual checks remain pending.

Private serial-bearing receipts and fastboot streams are under
`evidence/f9e-install-20260906-v1/`, including `execution.json`, the sixteen
per-image streams, `reboot-android.json`, `boot-completed.json`,
`live-validation.json` and `boot-screen.png`. Fastboot write acknowledgement,
normal reboot, Android boot completion and user-visible behavior remain
distinct evidence stages.

The successor was built to address UDFPS icon geometry, Aperture initialization
and notification-shade spacing. Completed boot and loaded resource values do not
verify those behaviors. Camera behavior remains unresolved unless a post-unlock
device test demonstrates otherwise.
