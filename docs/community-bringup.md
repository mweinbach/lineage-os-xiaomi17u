# Community Nezha work found through the supplied XDA thread

Reviewed on **2026-08-27**. The user's
[April bring-up thread](https://xdaforums.com/t/dev-xiaomi-17-ultra-nezha-lineageos-bring-up-started.4785557/)
leads to a newer, separate
[unofficial Nezha LineageOS 23.2 release](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/)
by **JohnTheFarm3r**. The original developer, kevte89!,
[confirmed on June 25](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/#post-90639594)
that he had stopped his separate effort. Do not treat the April announcement
as the latest state or assume these are the same source tree.

## Useful leads, with explicit limits

The release author reports a substantial Xiaomi/Leica Camera port, including
high-resolution capture and advanced video, while warning about remaining
differences and no commitment to further stock-Camera fixes. The author also
identifies brightness, audio and haptics differences. These are **maintainer
reports about another ROM**, not results reproduced on this phone or Evolution
X. The observed download page names
`LineageOS-Xiaomi17U_nezha-fastboot-20260811.zip`; only the public page was opened.
No release archive or attached modem was downloaded, verified or executed.
[Release notes and download link](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/#post-90638370)

The required baseline in that release is official China
**`OS3.0.307.0.WPACNXM`**. Our observed installation and supplied package are
modified Xiaomi.eu **`OS3.0.309.0.WPACNXM`**. The author
[explicitly distinguishes Xiaomi.eu from the official input](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/#post-90641234).
This is not evidence that the builds, modem or rollback requirements are
interchangeable. The release's extra modem attachment is explicitly for global
hardware; it is not an input for this China device. Nothing was flashed,
downgraded or changed to match the other ROM.

The strongest source-availability statement is the author's
[August 10 reply](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/page-3#post-90691410):
**the device tree is private**. The release links MiCode's
[`popsicle-w-oss`](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/popsicle-w-oss)
as its kernel-source reference. That citation does not supply the private
device tree, vendor-generation rules, exact kernel configuration, full source
manifest or camera patches. The branch's actual content must still be matched
to the [captured boot/module contract](boot-contract.md).

## Changes to the integration investigation

The following are leads for review, not configurations copied from the forum:

| Lead | What to establish before using it |
| --- | --- |
| Stock Camera on an AOSP framework | Compare the actual JNI, framework, service, permission, signing and linker dependencies. The existing 13-file seed inventory is not a complete port. |
| Camera Session Manager and an init/service bridge | July posts describe vendor-session controls for third-party apps and later MotionCam integration. Obtain reviewable implementation and assess permissions, Binder/service boundaries and SELinux rather than recreate a privileged bridge from a feature description. |
| Nezha power-profile overlay | A July 20 change reports adding the missing device overlay. Independently derive our overlay from recorded Nezha input and validate power accounting, thermals and charging protection. |
| Lens protection, high-rate RAW and accessory controls | Later posts describe limits and differing observations. Add separate sustained-capture, actuator/protection and accessory tests; do not infer behavior from a preview or one user's report. |
| Country-specific hardware | Keep CN modem and regional capabilities separate. Global eSIM statements do not establish eSIM hardware or service eligibility on this unit. |

The camera/service and power-profile leads come from the maintainer's
[July development updates](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/page-2).
The [later replies](https://xdaforums.com/t/rom-unofficial-nezha-xiaomi-17-ultra-lineageos-23-android-16-2026-08-11.4792785/page-3)
contain the private-tree statement and regional/actuator qualifications.
Unrelated rooting and integrity-hiding discussions are not adopted.

The practical consequence is narrower uncertainty about whether a substantial
camera port is feasible, **not a ready source base for this Evolution X build**.
The [integration gates](nezha-integration.md) still require reviewable sources,
exact physical geometry, a consistent firmware/AVB baseline, kernel/module
compatibility, VINTF and enforcing policy. No contact message was sent to a
maintainer and no private access was attempted.

Sanitized facts and source links are in
[`research/community-bringup.json`](../research/community-bringup.json).
Selected public-post captures are kept in ignored
`reports/community-review-20260827/`; receipt SHA256 is
`618502342022a3e59cdc3aca936d15c661845d44ccd93dd6af6b2f37765d3a36`.
The public record contains no archive bytes, identifiers from other users'
device logs, or executable installation instructions.
