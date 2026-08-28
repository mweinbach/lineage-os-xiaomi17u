# Android 16 ARM64 cluster: bounded validation runbook

Companion to the [feasibility report](android16-arm64-cluster-report.md),
researched 27–28 August 2026. **This is a proposed runbook, not a claim that
all these commands were executed.** Actual observations are in
[probe-results.json](../research/arm64-cluster/probe-results.json). In
particular, no backend, remote action, full platform graph or full image was
run in this investigation.

A subsequent [tool-substitution follow-up](android16-arm64-tool-swaps.md)
tested official native Rust, native Java compilation and an external native
LLVM package. It supplies candidates for the later stages below, but has not
completed a full Soong action or a remote build.

Run Linux commands in **Bash inside a dedicated ARM64 Linux guest**. Keep
source, output, logs and caches on its local ext4 disk. Use new directories;
do not reuse a production `out/`, modify the active Evolution X tree, attach
its volume to another VM, or access a phone. No experiment needs unlocking,
flashing, keys, credentials or a mounted Mac home directory.

## Experiment 1 — Verify an ARM64 Ubuntu VM before downloading source

The already tested guest is Ubuntu 24.04 on Apple Container 1.0.0. Prefer
reusing its existing owning VM for a small isolated probe after checking for
other work. For an independent new VM, the following is a **local-image
example**, not a public image to pull. First inspect the image and host:

```bash
# macOS host
sw_vers
uname -m
sysctl hw.memsize hw.logicalcpu
df -h .
container --version
container list
container volume list
container image inspect evolution-nezha-builder:ubuntu24.04-v1
```

The inspected image digest was
`sha256:82960bf5b04070ffa323bb37eaa4e77d1b189f7bdcd0c31204d5d8ac092d36ca`.
If this local image is absent, first prepare a reviewed ARM64 Ubuntu guest
with the build prerequisites. Do not substitute an unverified image silently.
Only after checking actual host capacity and choosing resources that leave
macOS sufficient RAM, create a **new** volume and VM; these names must not
already exist:

```bash
# macOS host; example resource allocation, not automatic sizing
export CLUSTER_IMAGE_TAG=evolution-nezha-builder:ubuntu24.04-v1
export CLUSTER_IMAGE_DIGEST=sha256:82960bf5b04070ffa323bb37eaa4e77d1b189f7bdcd0c31204d5d8ac092d36ca
python3 - <<'PY'
import json, os, subprocess
result = subprocess.run(['container', 'image', 'inspect', os.environ['CLUSTER_IMAGE_TAG']],
                        check=True, capture_output=True, text=True)
images = json.loads(result.stdout)
assert len(images) == 1
assert images[0]['configuration']['descriptor']['digest'] == os.environ['CLUSTER_IMAGE_DIGEST']
assert any(v['platform'] == {'architecture': 'arm64', 'os': 'linux'} for v in images[0]['variants'])
print('Local image identity verified; do not retag it during this experiment')
PY
test "$?" = 0 || exit 1
container volume create -s 800G aosp16-cluster-lab-work || exit 1
container run --name aosp16-cluster-lab --arch arm64 --rosetta \
  --cpus 16 --memory 96G --workdir /work \
  --mount type=volume,source=aosp16-cluster-lab-work,target=/work \
  -it "$CLUSTER_IMAGE_TAG" bash
```

The installed CLI resolves this locally built image by its registered tag;
digest-only and `repository@digest` inspection did not resolve it. The check
above therefore enforces its expected identity before launching the local
tag, which must not be changed concurrently. For a registry-distributed
image, use a verified immutable digest reference supported by that runtime.
An existing volume name is a hard stop, not an invitation to reuse it.

An 800G sparse volume does not reserve 800G of physical storage. Recheck host
free space during sync/build. A persistent VZ Ubuntu VM managed by Lima, Tart
or UTM is an alternative; the remaining commands are Linux commands and do
not depend on Apple Container.

```bash
# Linux guest; use this shell for subsequent experiments
set -o pipefail
uname -a
dpkg --print-architecture
cat /etc/os-release
findmnt -T /work -o TARGET,SOURCE,FSTYPE,OPTIONS
df -h /work
free -h
nproc
getconf PAGESIZE
ulimit -n
ulimit -u
python3 - <<'PY'
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory(prefix='aosp-case-', dir='/work') as root:
    root = Path(root)
    (root / 'Case').write_text('upper')
    (root / 'case').write_text('lower')
    assert (root / 'Case').read_text() == 'upper', 'not case sensitive'
    print('case-sensitive filesystem verified')
PY
export CLUSTER_LAB=/work/aosp16-cluster-lab
mkdir "$CLUSTER_LAB" || exit 1
mkdir "$CLUSTER_LAB/evidence" || exit 1
unset GOARCH GOOS GOROOT GOFLAGS GOEXPERIMENT GOAMD64 GOARM GOARM64 GODEBUG
unset GOPATH GO111MODULE CGO_ENABLED CGO_CFLAGS CGO_CPPFLAGS CGO_CXXFLAGS CGO_LDFLAGS
export GOENV=off GOTOOLCHAIN=local
```

**Expected:** Linux/aarch64, arm64 Ubuntu, case-sensitive ext4, ample real
disk/RAM, and RBE limits at least 16,000 files and 2,500 processes. The observed
guest exceeded those limits. **Failure means:** fix the VM/storage allocation
before investigating AOSP. Do not turn a case-insensitive host share into the
source directory. **Capture:** the above output, image/VM/kernel versions,
resource allocation and free space; omit personal paths and serials from
published evidence.

## Experiment 2 — Pin the release; choose a cheap replay or a full sync

For the fastest answer, inspect the already recorded native probes first.
Inside their existing owning VM, these commands read the isolated result:

```bash
python3 -m json.tool \
  /work/arm64-cluster-probes/20260828-stock-r4/result.json
git -C /work/arm64-cluster-probes/20260828-stock-r4/src/build/soong rev-parse HEAD
git -C /work/arm64-cluster-probes/20260828-stock-r4/src/build/make diff
```

That directory is a bootstrap/configuration subset with borrowed support
paths, **not a full stock checkout**. Do not extrapolate a complete build from
it. For independent full-tree validation, perform the following optional
sync only after Experiment 1. Budget at least the official 400GB baseline,
additional outputs/caches, and physical host headroom. This download was not
performed by this investigation.

```bash
git clone https://gerrit.googlesource.com/git-repo "$CLUSTER_LAB/repo-tool" || exit 1
git -C "$CLUSTER_LAB/repo-tool" checkout --detach \
  b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77 || exit 1
export REPO_LAUNCHER="$CLUSTER_LAB/repo-tool/repo"
export AOSP_TOP="$CLUSTER_LAB/src"
mkdir "$AOSP_TOP" || exit 1
cd "$AOSP_TOP" || exit 1
python3 "$REPO_LAUNCHER" init \
  --manifest-url https://android.googlesource.com/platform/manifest \
  --manifest-branch 15128c9e27cfa599c48d294babd39286ee8f1426 \
  --manifest-name default.xml --no-clone-bundle --current-branch \
  --repo-url https://gerrit.googlesource.com/git-repo \
  --repo-rev b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77 || exit 1
python3 "$REPO_LAUNCHER" sync --current-branch --jobs=8 \
  --no-clone-bundle --no-tags --no-manifest-update --fail-fast \
  2>&1 | tee "$CLUSTER_LAB/evidence/repo-sync.log" || exit 1
python3 "$REPO_LAUNCHER" manifest -r \
  -o "$CLUSTER_LAB/evidence/resolved-manifest.xml"
git -C build/soong rev-parse HEAD
git -C build/make rev-parse HEAD
cat prebuilts/go/linux-x86/VERSION
```

**Expected:** stock r4 Soong `f389fa2a2a768a93bc99957e2288f3fbee032bff`, Make
`b815dded1eafbf06191a6ae306956bb6ed6fb415`, Go 1.24.1. Keep Repo signature
verification enabled; a failed verification stops this stage. **Failure
means:** network, manifest, disk or checkout setup, not an ARM64 build failure.
**Capture:** resolved manifest and tool commit, sync exit status, clean source
status. Never use `--force-sync` to overwrite other work.

## Experiment 3 — Reproduce the first native architecture failure

```bash
cd "$AOSP_TOP"
env -u GOROOT -u GOOS -u GOARCH \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin GOCACHE="$CLUSTER_LAB/go-cache-native" \
  OUT_DIR="$CLUSTER_LAB/out-native" \
  build/soong/soong_ui.bash --dumpvar-mode OUT_DIR \
  >"$CLUSTER_LAB/evidence/native-01.log" 2>&1
native_status=$?
printf 'exit=%s\n' "$native_status"
cat "$CLUSTER_LAB/evidence/native-01.log"
```

**Expected:** missing `prebuilts/go/linux-arm64/bin/go`, not rejection of
`runtime.GOARCH=arm64`. This was observed against the original Android16 tree.
**Failure means:** distinguish a missing distribution from a missing Soong
architecture implementation. **Capture:** exact command, exit status, selected
path, `scripts/microfactory.bash` and source hashes. Do not patch Soong yet.

## Experiment 4 — Supply only matching ARM64 Go, then its stdlib archives

These commands are for **r4's Go 1.24.1 only**. r1 uses another version.

```bash
cd "$CLUSTER_LAB"
curl --fail --location --output go1.24.1.linux-arm64.tar.gz \
  https://go.dev/dl/go1.24.1.linux-arm64.tar.gz
printf '%s  %s\n' \
  8df5750ffc0281017fb6070fba450f5d22b600a02081dceef47966ffaf36a3af \
  go1.24.1.linux-arm64.tar.gz | sha256sum --check || exit 1
mkdir toolchains || exit 1
tar -xzf go1.24.1.linux-arm64.tar.gz -C toolchains || exit 1
test ! -e "$AOSP_TOP/prebuilts/go/linux-arm64" || exit 1
ln -s "$CLUSTER_LAB/toolchains/go" "$AOSP_TOP/prebuilts/go/linux-arm64" || exit 1
cd "$AOSP_TOP"
env -u GOROOT -u GOOS -u GOARCH PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  GOCACHE="$CLUSTER_LAB/go-cache-native" \
  OUT_DIR="$CLUSTER_LAB/out-native" \
  build/soong/soong_ui.bash --dumpvar-mode OUT_DIR \
  >"$CLUSTER_LAB/evidence/native-02.log" 2>&1
printf 'exit=%s\n' "$?"
cat "$CLUSTER_LAB/evidence/native-02.log"
```

**Expected:** the direct Blueprint compiler cannot find installed standard
library `.a` files in the upstream Go archive. This was observed. Add only the
branch's established archive-install behavior:

```bash
env GODEBUG=installgoroot=all CGO_ENABLED=0 \
  GOENV=off GOTOOLCHAIN=local GOCACHE="$CLUSTER_LAB/go-cache-stdlib" \
  GOROOT="$CLUSTER_LAB/toolchains/go" \
  "$CLUSTER_LAB/toolchains/go/bin/go" install std
cd "$AOSP_TOP"
env -u GOROOT -u GOOS -u GOARCH PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  GOCACHE="$CLUSTER_LAB/go-cache-native" \
  OUT_DIR="$CLUSTER_LAB/out-native" \
  build/soong/soong_ui.bash --dumpvar-mode OUT_DIR \
  2>&1 | tee "$CLUSTER_LAB/evidence/native-03.log"
file "$CLUSTER_LAB/out-native/soong_ui" \
  "$CLUSTER_LAB/out-native/microfactory_Linux"
sha256sum "$CLUSTER_LAB/out-native/soong_ui"
```

**Expected:** native AArch64 Soong UI; `OUT_DIR` query succeeds. The pinned
bootstrap subset passed without any Soong source edit. **Failure means:**
record the next actual source/package dependency; do not leap to a compiler
upgrade. **Capture:** Go archive SHA, installed version, complete bootstrap
log, ELF architecture and hashes. This fast query does not generate the full
platform graph.

## Experiment 5 — Make/Kati host detection, one edit at a time

```bash
cd "$AOSP_TOP"
env -u GOROOT -u GOOS -u GOARCH PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  GOCACHE="$CLUSTER_LAB/go-cache-native" \
  TARGET_PRODUCT=aosp_arm64 TARGET_RELEASE=bp4a TARGET_BUILD_VARIANT=userdebug \
  OUT_DIR="$CLUSTER_LAB/out-native" \
  build/soong/soong_ui.bash --dumpvars-mode \
  '--vars=HOST_ARCH HOST_PREBUILT_TAG HOST_OUT ANDROID_JAVA_HOME' \
  >"$CLUSTER_LAB/evidence/kati-01.log" 2>&1
printf 'exit=%s\n' "$?"
cat "$CLUSTER_LAB/evidence/kati-01.log"
```

**Expected:** `.KATI_READONLY: unknown variable: HOST_ARCH` in stock r4
`build/make/core/envsetup.mk`. Add only the first tested change, in this
isolated checkout:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('build/make/core/envsetup.mk')
old = '''  HOST_IS_64_BIT := true
else
ifneq (,$(findstring i686,$(UNAME))$(findstring x86,$(UNAME)))'''
new = '''  HOST_IS_64_BIT := true
else ifneq (,$(findstring aarch64,$(UNAME)))
  HOST_ARCH := arm64
  HOST_2ND_ARCH :=
  HOST_IS_64_BIT := true
else
ifneq (,$(findstring i686,$(UNAME))$(findstring x86,$(UNAME)))'''
text = p.read_text()
assert text.count(old) == 1, 'unexpected source; inspect rather than guessing'
p.write_text(text.replace(old, new))
PY
git -C build/make diff --check
git -C build/make diff >"$CLUSTER_LAB/evidence/make-host-only.patch"
```

Repeat the same query into `kati-02.log`. **Expected:** `HOST_ARCH=arm64` but
`HOST_PREBUILT_TAG=linux-x86` and x86 host output paths. This was observed once
the subset's unrelated missing support paths were supplied. Next make only
the independent tag correction:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('build/make/core/envsetup.mk')
old = 'HOST_PREBUILT_ARCH := x86\n'
new = '''ifeq ($(HOST_ARCH),arm64)
HOST_PREBUILT_ARCH := arm64
else
HOST_PREBUILT_ARCH := x86
endif
'''
text = p.read_text()
assert text.count(old) == 1, 'unexpected source; stop'
p.write_text(text.replace(old, new))
PY
git -C build/make diff --check
git -C build/make diff >"$CLUSTER_LAB/evidence/make-host-and-tag.patch"
```

Repeat into `kati-03.log`. **Expected:** `linux-arm64` tag and JDK path, not a
working full build. **Failure means:** inspect the first new error. Missing
files in a partial checkout are fixture failures, not automatically ARM64
blockers. **Capture:** each separate patch/query/log and output-path agreement.
Do not commit this patch to the active product tree as a completed port.

## Experiment 6 — Stop and enumerate compiler/runtime gaps

```bash
cd "$AOSP_TOP"
python3 - <<'PY'
from pathlib import Path
paths = [
    'prebuilts/jdk/jdk21/linux-arm64/bin/java',
    'prebuilts/clang/host/linux-arm64/clang-r563880c/bin/clang',
    'prebuilts/rust/linux-arm64/1.88.0/bin/rustc',
]
for name in paths:
    p = Path(name)
    print('present' if p.exists() else 'MISSING', name)
PY
rg -n 'linux-musl-x86|linux-x86|UseHostMusl|HostPrebuiltTag' \
  build/soong/rust/config/global.go build/soong/rust/bindgen.go \
  prebuilts/jdk/jdk21/Android.bp
rg -n 'LinuxMusl|runtime.GOARCH|linux_musl' \
  build/soong/android/arch.go build/soong/android/paths.go
```

**Expected:** selected native JDK, Clang and Rust are missing, and source shows
remaining host-path/libc coupling. Those three missing paths were recorded;
their compilers were not invoked by the fast query. **Failure means:** a
different branch or effective compiler override must be pinned and audited.
**Capture:** effective versions, ELF class/machine, interpreter, NEEDED/RPATH
for every replacement, and which process loads each library. Do not treat an
x86 `.so` as usable by an ARM64 process. This is the two-hour stop point: the
bootstrap is small; the remaining work is several toolchain closures.

## Experiment 7 — Establish an unchanged x86-profile Rosetta control

Use a **separate clean stock checkout** for this branch of the experiment.
Do not reuse the Make-patched checkout or its native bootstrap outputs.
Set `AOSP_X86_TOP` to that clean r4 checkout. The existing Evolution X tree
can provide an explicitly labeled module smoke test, not a stock control.

```bash
: "${AOSP_X86_TOP:?set this to a separate clean r4 checkout}"
cd "$AOSP_X86_TOP"
git -C build/soong status --short
git -C build/make status --short
prebuilts/build-tools/linux-arm64/bin/toybox uname -m
prebuilts/build-tools/linux-x86/bin/toybox uname -m
file prebuilts/go/linux-x86/bin/go
readelf -l prebuilts/jdk/jdk21/linux-x86/bin/java
test -e /lib64/ld-linux-x86-64.so.2
env -u GOROOT -u GOOS -u GOARCH \
  PATH="$PWD/prebuilts/build-tools/path/linux-x86:/usr/sbin:/usr/bin:/sbin:/bin" \
  GOCACHE="$CLUSTER_LAB/go-cache-rosetta" \
  OUT_DIR="$CLUSTER_LAB/out-rosetta" \
  build/soong/soong_ui.bash --dumpvar-mode OUT_DIR \
  2>&1 | tee "$CLUSTER_LAB/evidence/rosetta-bootstrap.log"
file "$CLUSTER_LAB/out-rosetta/soong_ui"
```

**Expected:** native Toybox reports aarch64, translated Toybox x86_64, and
Soong UI is an x86-64 ELF. The x86 PATH is command-scoped; it does not change
the VM's kernel architecture. **Failure means:** fix translator/runtime
visibility or the selected x86 Go path before discussing RBE. **Capture:**
ELF/interpreter, errors, version and output architecture. Do not install an
x86 VM, replace `/usr/bin/uname`, or disable security checks.

A minimal mixed-process reproduction, independent of a full image:

```bash
export STOCK_CLANG="$AOSP_X86_TOP/prebuilts/clang/host/linux-x86/clang-r563880c"
export STOCK_JDK="$AOSP_X86_TOP/prebuilts/jdk/jdk21/linux-x86"
mkdir "$CLUSTER_LAB/hybrid" || exit 1
cd "$CLUSTER_LAB/hybrid" || exit 1
printf 'int value(void) { return 42; }\n' >value.c
cat >Hello.java <<'JAVA'
class Hello {
  public static void main(String[] args) {
    System.out.println("hybrid-jvm:" + System.getProperty("os.arch"));
  }
}
JAVA
"$STOCK_CLANG/bin/clang" --target=aarch64-linux-android36 -c value.c -o android.o
"$STOCK_JDK/bin/javac" Hello.java
"$STOCK_JDK/bin/java" -cp . Hello
file android.o "$STOCK_CLANG/bin/clang" "$STOCK_JDK/bin/java"
```

**Expected:** AArch64 object and `hybrid-jvm:amd64`. The recorded probe also
used native Ninja to schedule translated Clang/LLD/JDK, then ran an x86
executable successfully. Small programs do not test large heaps, LTO or ART.

## Experiment 8 — Test one matched native compiler before a full port

**Prerequisite not supplied by this runbook:** a reviewed native execution
package built from Android16's *effective* Clang revision/configuration. The
modern LLVM22/23 package is not an acceptable substitute for this gate.
Building that package is explicit engineering work described in the report;
there is no validated one-command Android16 native compiler recipe here.

Keep original x86 tools intact. `NATIVE_CLANG_ROOT` must refer to the new
package, with native implementation libraries and matching target resources.

```bash
: "${NATIVE_CLANG_ROOT:?a verified matched native Clang package is required}"
"$STOCK_CLANG/bin/clang" --version
"$NATIVE_CLANG_ROOT/bin/clang" --version
file "$NATIVE_CLANG_ROOT/bin/clang"
cd "$CLUSTER_LAB/hybrid"
for target in aarch64-linux-android36 x86_64-unknown-linux-gnu; do
  "$STOCK_CLANG/bin/clang" --target="$target" -MMD -MF result.d \
    -MT result.o -c value.c -o result.o
  cp result.o "$target.stock.o"
  cp result.d "$target.stock.d"
  "$NATIVE_CLANG_ROOT/bin/clang" --target="$target" -MMD -MF result.d \
    -MT result.o -c value.c -o result.o
  cmp "$target.stock.o" result.o
  cmp "$target.stock.d" result.d
  file result.o
done
```

**Expected:** matching simple objects/dependencies for both targets, including
x86 host outputs from native Clang. **Failure means:** stop substituting that
compiler; investigate revision/configuration/resource differences first.
**Capture:** compiler source/build configuration, package hashes, `-###`
command traces, resource directories and dependency differences. Then replay
actual saved Soong C/C++ commands at the **same working directory and output
path**. Include headers, response files and diagnostics; a trivial matching
object is only the first gate. Do not use `eval` to replay untrusted commands.

Before treating the C++ test as representative, replay ordinary 64-bit device
ThinLTO compiles and links with their original flags and MLGO settings. R4
defaults to ThinLTO for that class, so it is not an obscure edge case. Inspect
LLVM bitcode target triples when a `.o` is not ELF, and compare the final linked
outputs. A native compiler must remain compatible with the retained stock LLD
and Rust LLVM inputs. Do not disable LTO/MLGO globally to manufacture parity.

## Experiment 9 — Start one self-hosted backend in an isolated lab

Buildfarm is the first compatibility candidate because it has a public AOSP
guide. Its example requires its documented container/runtime prerequisites.
Use ordinary Linux containers inside the persistent VM, not separate Apple
Container VMs sharing a writable source volume.

The pinned example still uses `:latest` images, host networking and a
privileged worker. **Do not run that default on an exposed or shared host.**
First adapt a local copy to reviewed image digests and the isolated test
network; record its patch. Privilege inside a dedicated worker VM does not
establish that the action sandbox is correct. Validate that separately.

```bash
cd "$CLUSTER_LAB"
git clone https://github.com/buildfarm/buildfarm.git buildfarm
git -C buildfarm checkout --detach 05f13afb95aee3d5fac2f60f9527f7358315d389
cd buildfarm
cat contrib/aosp/README.md
sed -n '1,220p' examples/bf-run
# Only after adapting/reviewing the example's images, ports and isolation:
git diff -- examples/bf-run examples/config.minimal.yml
examples/bf-run start
```

**Expected:** one execution server, CAS/action cache and a worker. This command
is from the pinned upstream guide; it was **not run here** and is not proof
that the example automatically chooses the intended ARM64 images. Inspect
resolved image manifests/ELF architecture and configure an ARM64 worker
platform explicitly. Treat an x86 image running through translation as such.

**Failure means:** backend/runtime/packaging setup, separate from AOSP host
support. **Capture:** source commit, image digests/architectures, service
configuration, capabilities, worker platform and logs. Bind insecure example
services only on an isolated lab network; use authenticated TLS for persistent
LAN deployment. Do not upload signing keys or private source to an unknown
endpoint.

## Experiment 10 — Prove a remote action, with no cache or local fallback

For the isolated no-auth lab only, set `RBE_LAB_ENDPOINT` to the service you
just verified. The worker must already have a declared, sandboxed ARM64
runner environment whose platform matches `OSFamily=linux,ISA=arm-a64`.

```bash
: "${RBE_LAB_ENDPOINT:?set the verified private lab host:port}"
export RBE_service="$RBE_LAB_ENDPOINT"
export RBE_instance=main
export RBE_use_rpc_credentials=false
export RBE_service_no_auth=true
export RBE_service_no_security=true
export RBE_server_address="unix://$CLUSTER_LAB/reproxy.sock"
export RBE_log_dir="$CLUSTER_LAB/evidence/reproxy"
export RBE_proxy_log_dir="$RBE_log_dir"
export RBE_output_dir="$RBE_log_dir"
export RBE_cache_dir="$CLUSTER_LAB/reclient-cache"
export RBE_DIR="$AOSP_X86_TOP/prebuilts/remoteexecution-client/live"
mkdir -p "$RBE_log_dir" "$RBE_cache_dir"
mkdir "$CLUSTER_LAB/remote-action" || exit 1
cd "$CLUSTER_LAB/remote-action" || exit 1
"$RBE_DIR/bootstrap" --re_proxy="$RBE_DIR/reproxy" || exit 1
"$RBE_DIR/rewrapper" --exec_root="$PWD" --labels=type=tool \
  --exec_strategy=remote --remote_accept_cache=false --remote_update_cache=false \
  --platform=OSFamily=linux,ISA=arm-a64 \
  --output_files=machine.txt \
  -- /bin/sh -c 'uname -m > machine.txt'
action_status=$?
"$RBE_DIR/bootstrap" --shutdown
shutdown_status=$?
test "$action_status" = 0 || exit "$action_status"
test "$shutdown_status" = 0 || exit "$shutdown_status"
cat machine.txt
```

The shell/uname here are **declared worker-image tools**, not a hermetic AOSP
compile. This isolates transport/platform/execution proof. The platform must
uniquely identify that pinned runner configuration; add its immutable image
property if required by your backend. **Expected:** actual remote execution
and a worker identity in the logs, not merely aarch64 output. **Failure means:**
fix endpoint/auth/platform/CAS/sandbox before touching Soong. **Capture:**
action digest, executor identity, uncached execution status, platform and
stdout/output; never count a fallback or cache hit as execution.

Next prove a translated Clang action in the worker's **actual sandbox**, with
complete toolchain inputs, x86 libraries and Rosetta interpreter visibility.
Repeat with a reviewed native execution dispatcher only after Experiment 8.
The following is a precise invocation template; **the dispatcher/native
package and their input lists are prerequisites, not implemented artifacts**:

```bash
: "${ACTION_ROOT:?isolated input root with original compiler and test source}"
: "${REL_STOCK_CLANG:?original compiler path relative to ACTION_ROOT}"
: "${REL_NATIVE_CLANG:?matched native compiler path relative to ACTION_ROOT}"
: "${REL_DISPATCHER:?reviewed allowlisted execution wrapper path}"
: "${RUNNER_PLATFORM:?exact immutable configured ARM64 runner platform}"
cd "$ACTION_ROOT" || exit 1
test ! -e value.o && test ! -e value.d || exit 1
"$RBE_DIR/bootstrap" --re_proxy="$RBE_DIR/reproxy" || exit 1
"$RBE_DIR/rewrapper" --exec_root="$PWD" \
  --labels=type=compile,lang=cpp,compiler=clang \
  --exec_strategy=remote --remote_accept_cache=false --remote_update_cache=false \
  --platform="$RUNNER_PLATFORM" \
  --remote_wrapper="$REL_DISPATCHER" \
  --toolchain_inputs="$REL_NATIVE_CLANG,$REL_DISPATCHER" \
  --inputs=value.c --output_files=value.o,value.d \
  -- "$REL_STOCK_CLANG" --target=aarch64-linux-android36 \
  -MMD -MF value.d -MT value.o -c value.c -o value.o
action_status=$?
"$RBE_DIR/bootstrap" --shutdown
shutdown_status=$?
test "$action_status" = 0 || exit "$action_status"
test "$shutdown_status" = 0 || exit "$shutdown_status"
```

The dispatcher accepts only an allowlisted original compiler and arguments,
selects the matching native executable, and is itself part of the action
digest. Its executable-specific `*_remote_toolchain_inputs` lists must include
all native libraries/resources. The original compiler/scanner inputs must
also remain complete. Do not silently substitute a different binary behind
an unchanged path/cache key. First omit `--remote_wrapper` and native inputs
to test the complete translated package; use a distinct declared platform.

**Expected:** the native action output/dependency list matches the baseline,
and worker evidence shows native Clang. **Failure means:** distinguish local
input processing from remote execution, missing CAS input, dynamic loader,
sandbox or compiler mismatch. Stop after a bounded failure investigation;
do not weaken sandbox, signature or image compatibility checks.

## Experiment 11 — One real Soong module, then more action classes

**Prerequisite:** adapt the Google platform defaults at the inspected Soong
and Make generation sites, and, for native compilation, explicitly integrate
the verified execution dispatcher. `RBE_platform` alone does not reliably
override generated command-line values. Inspect emitted rewrapper commands
before starting a module build. Keep signing, links and JVM/Rust remote gates
unset at first.

```bash
cd "$AOSP_X86_TOP"
export PATH="$PWD/prebuilts/build-tools/path/linux-x86:/usr/sbin:/usr/bin:/sbin:/bin"
export OUT_DIR=out-arm64-cluster-rbe-module
export GOCACHE="$CLUSTER_LAB/go-cache-rbe"
export USE_RBE=1 NO_ABFS=1 NINJA_REMOTE_NUM_JOBS=8
export RBE_CXX_EXEC_STRATEGY=remote
export RBE_remote_accept_cache=false RBE_remote_update_cache=false
unset RBE_CXX_LINKS RBE_RUST RBE_JAVAC RBE_TURBINE RBE_D8 RBE_R8
unset RBE_SIGNAPK RBE_ZIP RBE_ABI_DUMPER RBE_ABI_LINKER RBE_CLANG_TIDY
unset NOSTART_RBE
source build/envsetup.sh
lunch aosp_arm64-bp4a-userdebug
m -j8 libbase 2>&1 | tee "$CLUSTER_LAB/evidence/rbe-libbase.log"
```

Keep the endpoint/auth variables from the verified lab configuration, or
replace them with the persistent authenticated TLS configuration. Soong
manages reproxy here; do not leave a manually started instance on its socket.
Do not set remote flags to `0` as a substitute for unsetting them: some Make
conditions check presence.

**Expected:** at least one real uncached C++ action on the intended worker,
matching artifacts and no fallback. Local graph, generators and links remain.
**Failure means:** classify the exact action and retain its inputs/command;
it is not yet evidence that the whole backend or all AOSP actions fail.
**Capture:** generated Ninja rule, original/remote argv, depfiles, action
digest, worker identity, effective platform, scanner log and output hashes.
Inspect client logs to ensure cache disabling survived environment filtering.

Keep these distinct RBE outputs **inside the source execution root**. Reclient
uses that root to translate inputs/outputs; sibling output directories can
produce `..` paths that its input processing rejects. The earlier external
bootstrap-only output directories do not establish remote-build support for
that layout.

Then separately validate javac, Turbine, D8/R8, Rust and optional links with
their exact source gates and execution strategies. Do not enable all flags
at once. Native Java means native JNI; native Rust proc macros require native
rustc/libc. The x86-profile design deliberately keeps those process groups
translated until tested.

## Experiment 12 — Scale to four machines and test a complete image

Give each worker a separate SSD-backed cache/action directory and declared
platform. Do not give workers a shared `out/`. They should succeed after the
coordinator checkout is made inaccessible to them except through CAS. Reserve
coordinator CPU/RAM for hashing, scanning and local build stages.

Measure the actual VM network path before a speedup claim:

```bash
# Worker VM; bind to the reviewed private interface, not the public Internet
iperf3 -s -1 -B "$WORKER_PRIVATE_IP"
# Coordinator VM, while that server is listening
iperf3 -c "$WORKER_PRIVATE_IP" -P 4 -t 30 -J \
  >"$CLUSTER_LAB/evidence/network-forward.json"
# Start another one-shot server before repeating with reverse direction
iperf3 -c "$WORKER_PRIVATE_IP" -P 4 -t 30 -R -J \
  >"$CLUSTER_LAB/evidence/network-reverse.json"
```

**Expected:** measured bandwidth/CPU, not an assumed 10GbE line rate. **Failure
means:** VM routing/NAT/MTU/host networking may bound scaling. **Capture:**
network configuration, iperf JSON, CPU use, and cold/warm CAS transfer volume.

Only after a small module, sandbox isolation and tool correctness pass, and
after rechecking disk/RAM/filesystem/manifest, attempt a full generic image:

```bash
cd "$AOSP_X86_TOP"
df -h "$AOSP_X86_TOP" "$CLUSTER_LAB"
free -h
python3 "$REPO_LAUNCHER" manifest -r \
  -o "$CLUSTER_LAB/evidence/pre-build-manifest.xml"
export OUT_DIR=out-arm64-cluster-rbe-full
export NINJA_REMOTE_NUM_JOBS=24
source build/envsetup.sh
lunch aosp_arm64-bp4a-userdebug
/usr/bin/time -v bash -c 'build/soong/soong_ui.bash --make-mode -j8 droid' \
  2>&1 | tee "$CLUSTER_LAB/evidence/full-rbe.log"
```

The job counts are conservative test settings, not sizing recommendations.
Use separate output directories for local, translated and cluster controls.
Repeat against an actual x86 Linux control with the same manifest and effective
tool versions. Measure both clean and incremental workloads, cache hit rates,
critical path, worker busy time, coordinator CPU, peak RSS, OOMs and total CAS
bytes. Compare outputs accounting explicitly for timestamps/build IDs; a hash
difference is a reason to investigate, not automatically a compiler defect.

**Expected:** a complete image with normal security/compatibility checks and
validated ART/dexpreopt/image generators. **Failure means:** preserve the
first error and surrounding logs, classify it, and keep the last known-good
configuration. **Capture:** full manifest, patches, environment allowlist,
tool/image hashes, action logs, image validation and timing. A generic image
does not establish Xiaomi device compatibility, and no flashing is included.

## Decision gates and failure record

After roughly two hours of an already provisioned checkout, expect enough
evidence to classify bootstrap and host selection. If the next step is a
missing compiler/JDK/Rust distribution, call it toolchain integration work;
do not keep describing it as one architecture check. Time-box the matched
native compiler and one real remote action before a multiweek port.

Use one record per failure; preserve fixture failures separately:

```text
Observed time and experiment:
Failure / exact exit status:
Root cause (confirmed or hypothesis):
Repository and immutable commit:
Relevant source file and line:
Exact command / execution ISA / output ISA:
Fix attempted (one change):
Result and artifact/log hashes:
Upstream equivalent commit, or none identified:
Next gate and stop condition:
```

Go forward only if remote execution is real, compiler inputs/outputs are
correct, security checks remain enabled and measured build time improves.
Otherwise retain Rosetta for the difficult processes or use x86 Linux workers.
No part of this runbook authorizes weakening SELinux, verified boot, rollback
checks, signatures, source isolation or device-compatibility checks.

Primary command references: [AOSP host requirements](https://source.android.com/docs/setup/start/requirements),
[pinned Soong bootstrap](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/scripts/microfactory.bash),
[pinned build-tools recipe](https://android.googlesource.com/platform/prebuilts/build-tools/+/412724a805835d89234d67c363f7ada7f5f8a67f/build-prebuilts.sh),
[Go release archives](https://go.dev/dl/),
[Buildfarm AOSP guide](https://github.com/buildfarm/buildfarm/blob/05f13afb95aee3d5fac2f60f9527f7358315d389/contrib/aosp/README.md),
[Buildfarm example launcher](https://github.com/buildfarm/buildfarm/blob/05f13afb95aee3d5fac2f60f9527f7358315d389/examples/bf-run),
[rewrapper flags](https://github.com/bazelbuild/reclient/blob/dbabdc03691e4a293f0b8b6656cdc27f892c4e54/cmd/rewrapper/main.go),
[Soong RBE lifecycle](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/ui/build/rbe.go).
