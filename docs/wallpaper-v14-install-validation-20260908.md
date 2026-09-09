# Wallpaper & style v14 installation and validation, 2026-09-08

**V14 is installed and booted on slot A with normal Android SELinux Enforcing,
and Wallpaper & style no longer crashes.** The picker opens from the launcher
long press and from Settings, its clock chooser offers the default clock and
all seven kept Pixel plugin clocks, a plugin clock applies and renders on the
real lock screen, and the default clock was restored. Fresh crash and SystemUI
buffers hold no plugin rejection and no fatal exception. A five-capture camera
subset passes on the preserved v13 camera baseline. This page records the
device side of the [prepared v14 fix](wallpaper-clock-plugin-20260908.md).

## Installation

The user approved the install in reply to the prepared v14 recap, and the
approval was bound to the bundle manifest
`b36a0482e3b28be2c16d609f6cc6252b6c8b68ee25d0f87d624472df5b678ce0` before any
phone write. The read-only Android preflight confirmed the expected v13
predecessor on slot A, unlocked; the bootloader review confirmed slot A and
no pending snapshot; the bundle was reverified. All eight A-chain writes over
the shared Super were acknowledged in the fixed order (super, dtbo, init_boot,
vendor_boot, recovery, boot, vbmeta_system, vbmeta) with every payload
rehashed identical afterwards. Android completed boot in 25.5 seconds as
`nezha.98d08f70d20e5a87a2777f81`, userdebug, slot `_a`, Enforcing. No wipe,
slot change or data clear was performed. Root ADB was re-established for
diagnostics only.

Before the flash, the v13 phone still listed the Flex clock package and its
crash buffer still held the four saved wallpaper crashes; the lock-screen clock
setting was unset. The wallpaper picker's app data (28 CE and 5 DE members)
was backed up after force-stopping the picker.

## Post-boot observation, before any UI action

| Check | Observed |
| --- | --- |
| `SystemUIClocks-Flex` directory and package | Absent |
| Kept clock packages | BigNum, Calligraphy, Growth, Inflate, Metro, NumOverlap, Weather present |
| Installed clock and wallpaper picker APKs | All eight hash-identical to the contract's kept plugins and host |
| Seven v13 camera and audio payloads | Byte-identical to the v13 component run |
| SystemUI "Disabling plugin" / "Clock Id conflict" / InvalidVersionException lines | None (the v13 boot logged eleven and one) |
| Crash buffer | No fatal exception |
| Wallpaper picker CE and DE app data | All 33 members unchanged before first launch |

## Wallpaper & style validation

The lock screen rendered the default clock before the test. Wallpaper & style
was opened from the launcher long-press menu and, later, from the Settings
entry; both landed in the same customization activity, and one wallpaper
process served the whole session without restarting. Tapping the lock-screen
preview opened the wallpaper preview activity. The lock-screen sheet listed
Theme pack, Clock, Shortcuts, Notifications on lock screen and More lock screen
settings.

The Clock chooser offered eight faces in this order: Digital default, Digital
overlapping numerals, Digital transit clock, Analog bold font, Digital
calligraphy, Digital inflated, Digital with weather and Digital stenciling.
That is the native default plus the seven kept plugin clocks. Digital
calligraphy was selected and applied; the secure setting changed to
`DIGITAL_CLOCK_CALLIGRAPHY`, and after sleep and wake the real lock screen
rendered the calligraphy digits. The chooser was reopened and Digital default
applied, which the setting recorded as `DEFAULT` with the default font axes,
and the lock screen rendered the default clock again. Because the pre-test
value was unset rather than an explicit default, the setting was then deleted
so the phone holds exactly its pre-test value; the theme overlay setting was
unchanged throughout.

One mis-tap opened the Shortcuts editor; it was left with Navigate up and the
Shortcuts entry still reads "Flashlight, Camera". The home-screen preview inside
the picker showed a launcher widget "Something went wrong / Try again" card; it
belongs to the previewed widget, not to plugin loading, and is unverified
further.

After the session the crash buffer holds no fatal exception and the main and
system buffers hold no plugin rejection line.

## Camera subset on the preserved baseline

| Case | Observed |
| --- | --- |
| Xiaomi rear Photo 1x | 3072×4096 JPEG decodes |
| Xiaomi front Photo | 3072×4096 JPEG decodes |
| Xiaomi Pro UltraRAW | 4080×3072 JPEG plus compressed Bayer DNG; all 64 tiles, CFA metadata, embedded preview and full LibRaw decode pass |
| Aperture rear Bokeh | 3072×4096 JPEG decodes |
| Xiaomi rear video | 10.08-second 1920×1080 HEVC with mono AAC; both tracks fully decode |

Pro format was returned to JPEG, the camera to rear Photo 1x, and Aperture's
effect to NONE with its panel closed; all three test apps were stopped and the
stay-awake setting restored to 0.

## What this does not prove

One session on one phone. Wallpaper changes, theme packs and the other six
plugin clocks were not applied; sustained picker use is unmeasured. The camera
subset is five captures, not the full v13 matrix. The
[research record](../research/wallpaper-v14-install-validation-20260908.json)
binds the authorization, preflight, execution, boot, post-boot, UI-session,
capture and cleanup receipts by hash; screenshots, UI dumps, media, logs and
app-data archives stay under ignored directories.
