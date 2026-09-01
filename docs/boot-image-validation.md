# Boot-image validation

The public macOS runtime for the prepared Nezha boot-content checker passed its
live input recheck on **2026-09-01 at 14:56:33 UTC**, with outer exit **0**.
This verifies the selected runtime and its declared inputs. Final Evolution
boot images have not been admitted by this check.

The selection remains Evolution X Android 16 QPR2 **`bka` / `bp4a`**, with
**543 source files across fourteen projects** and build number
**`nezha.3c24f46cf801e6abd6d5361c`**. The **4 KiB** baseline and **working76**
recovery derivative remain unchanged. Recovery testing used stock companion
components. Normal Android SELinux enforcement is unchanged. The active build
blocker remains in [current status](workspace-status.md).

Six public-tool observations, three record emissions, independent reviews and
the final runtime API result are separate evidence. The live check rehashed
**195 runtime files** and completed the full recheck of **237 nonempty guarded
inputs and 5 empty inputs**. Three of those empty inputs are Python package
sources; the other two are diagnostics. These counts do not describe ROM images
or hardware tests. Exact milestone, stdout, completion and runtime-selector pins
are in [the sanitized record](../research/boot-image-validation.json).

The earlier **raw-v6 capture remains on HOLD**: it omitted `base64`, imported
later by a source-proof helper. A reviewed observer initialized the four pinned
helpers before enumeration. Fresh **raw-v7** added the actual `base64` source and
cache; prior evidence was preserved. The current projector rejects raw-v6 even
with matching controller pins.

Qualification binds the selected Python/LZ4 runtime, pinned AOSP unpack/DTBO
sources and observed imports and loader dependencies. It does **not** prove
complete dynamic or hermetic runtime closure. System shared-cache dependencies
explicitly rely on observed macOS build **26A5425a**. Independent review checked
retained records; process execution and resource-limit enforcement remain
root-recorded evidence.

Keep the interfaces separate: [target-files materialization](target-files-materialization.md)
copies thirteen ZIP images and two retained inputs into a signing-input bundle;
[AVB image-set verification](avb-image-set.md) checks its separate complete
image/public-key manifest. The runtime selector binds observations and review,
not either image manifest. The [supplied-package boot contract](boot-contract.md)
and [factory boot contract](factory-boot-contract.md) retain their historical
input boundaries.

Successful package2, verified ZIP transfer, materialization, fresh boot-source
and producer evidence, and all **six native boot-image inspections** remain
pending. Complete signed AVB/rollback/partition-fit checks, full VINTF and an
authorized physical Evolution boot are also still required. No phone operation
is authorized by this milestone.
