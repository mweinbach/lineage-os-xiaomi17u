# Camera scheduling compatibility candidate — September 5, 2026

The opt-in `NEZHA_CAMERA_TASK_PROFILES := true` candidate supplies the missing
`CAMERA_CAPTURE_SCHED` name to the **existing vendor loader**. It performs two
real `JoinCgroup` actions: cpuset `camera-daemon`, then cpu `camera-daemon`.
It does not claim to reproduce Xiaomi's more specific capture scheduling policy,
and camera speed, smoothness and energy use remain unmeasured.

## Why this is an integration change

The retained Package7 hardware log at lines 3457–3466 has five missing-profile
messages paired with `CameraOpt_Native` thread-group assignment failures. They
occur during the retained camera diagnostic interval; these are not controlled
shutter-latency measurements.

The exact factory system-ext profile defines that name as an aggregate joining
cpuset `camera-daemon/limit-level6` and cpu `camera-daemon/limit-level2`. The pinned
Evolution platform init creates the standard `camera-daemon` parents, not these
OEM child groups. Installing the complete OEM file without its initialization
and policy dependencies would exchange a missing-name failure for missing-group
failures. This candidate supplies only the observed caller's requested name and
uses the standard camera groups, without CPU masks, utilization floors, priority
boosts, new groups, permissions, SELinux changes or thermal modifications.

The **parent groups are a compatibility choice, not equivalent OEM levels**.
If a thread is already in these parent groups, a successful action need not
change its placement. The objective is a supported scheduling operation, not
an unmeasured performance claim.

## Actual consumer, not a file in an unused vendor staging tree

Vendor is delivered as a preserved prebuilt image. Therefore the candidate is
installed in built **system_ext/etc/task_profiles_cameraopt.json**, not written
to a vendor staging path that would be discarded.

The exact preserved `/vendor/lib64/libprocessgroup.so` was captured read-only
and inspected as AArch64 ELF; it is not replaced or executed. Its
`TaskProfiles` constructor at VA `0x329f4` loads system/API/vendor profiles first,
then constructs the string at VA `0x10621`,
`/system_ext/etc/task_profiles_cameraopt.json`. An access check at `0x32c50` is
followed, when present, by a `TaskProfiles::Load` call at `0x32c98` using that
filename. This is disassembled control-flow evidence, not just a string match.
The exact vendor `libcameraopt.so` imports `SetTaskProfiles`, depends on
`libprocessgroup.so`, and contains the requested profile name and matching log
tag. Runtime namespace resolution and file access still require device proof.

Upstream Evolution `system/core` branch `bka` was checked with `git ls-remote`;
its observed head and the reviewed source-lock revision were both
`241488ea392c01079941d86ddc458b8a0c9ae6e1`. Its own platform loader does not load
the OEM supplemental filename. This candidate deliberately serves the preserved
vendor caller; it does not claim to expose this name to every platform process.
The standard parent-group configuration and two standard camera profiles are
present in that revision's init and libprocessgroup configuration.

## Source selection and fail-closed checks

`camera-task-profiles.mk` accepts only unset, `false`, or one `true`. Only `true`
adds the file. Before admission, the bundled offline verifier requires exact
reviewed SHA256 hashes of platform `task_profiles.json`, `cgroups.json`, and
`rootdir/init.rc`, and exactly the two reviewed candidate actions. It rejects
missing or drifted inputs, duplicate JSON keys, symlinks and oversized files.
A source update or legitimate init modification must be reviewed before updating
these pins; the check must not be bypassed. Existing ownership of the destination
in `PRODUCT_COPY_FILES` is rejected at inclusion time. Android's normal duplicate
output checks remain enabled for later additions.

This relies on the existing preserved-vendor image identity gate; a replacement
vendor loader needs a new audit. No factory library, profile body or private raw
evidence is redistributed. The tracked contract records identities and interface
facts only. The shipped JSON is the small independently authored compatibility
configuration above, not a factory-file transplant.

## Validation and remaining device gates

Five private input files were recaptured with the maintained non-mounting EROFS
collector from exact pinned stock images into ignored
`artifacts/camera-scheduling-20260905/`. The verifier successfully rehashed all
five captured files, validated capture metadata, and checked the OEM-to-candidate
mapping. Run it with:

```sh
python3 scripts/camera_task_profiles.py --capture-root artifacts/camera-scheduling-20260905
```

Three pinned public source files were separately captured into ignored
`artifacts/camera-scheduling-20260905/public-source/`. Running the same native
admission verifier on those real bytes returned `verified-camera-task-profiles`.
This checks the source guard, **not a native Android build**. Offline tests cover
the exact mapping, empty/no-op and unsupported actions, source drift, malformed
inputs, unsafe file types and Make selector rejection.

Before accepting a built successor:

1. Verify the built system-ext file bytes and the unchanged preserved vendor
   loader hash, plus the actual effective system cgroups/init configuration.
2. In an explicitly authorized runtime test, identify the camera process's loaded
   library path and verify the supplemental file's access/SELinux result.
3. Reproduce the caller operation and check both disappearance of missing-profile
   errors and actual thread membership in the two standard camera groups.
4. Check for cgroup assignment errors or AVCs; do not widen policy to hide them.
   Confirm camera closure/work completion releases any unrelated active boosts.
5. Compare repeated camera open/capture latency, frame consistency and energy
   under matched temperature and workload. Record regressions as well as gains.

No phone, active source VM, installed images or original workspace files were
changed by this work. Disabling the selector omits the candidate on a subsequent
build; changing an installed device still needs separate authorization.
