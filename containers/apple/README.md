# Apple Container builder image

This image provides Ubuntu 24.04 **ARM64** tools and **amd64** runtime libraries
for the workspace's explicit Apple Container + Rosetta experiment. It is not a
native Linux x86-64 host, an Android source checkout, or proof that Evolution X
Android 16 can complete a build for `nezha`.

The build context is **`containers/apple/`**, with **`Containerfile`** as its
recipe. Do not use the repository root as the context. The local `.dockerignore`
allows only the seven image input files; it excludes firmware, device evidence,
source checkouts, credentials, and other workspace material.

## Base image and package sources

The default `UBUNTU_IMAGE` argument pins the official Ubuntu 24.04 Linux ARM64
manifest:

```text
docker.io/library/ubuntu@sha256:95fa486768020359141f1318720f43e7982ef926c792891d984aef9aaf05e7ea
```

[`base-image.json`](base-image.json) records the corresponding multi-platform
index and configuration digests. These were resolved from Docker's official
registry on 2026-08-27; both returned manifest bodies were independently
SHA256-hashed. The parent workflow also confirmed the same digests through its
live Apple Container image inspection. Refresh that record deliberately when
changing the base rather than depending on a moving tag.

Minimal Ubuntu lacks the HTTPS CA bundle. The first native ARM64 layer installs
`ca-certificates` through the pinned base image's original Ubuntu APT
configuration, retaining normal archive signature verification. That initial
configuration may use HTTP. Before adding the foreign architecture, the recipe
replaces it with explicit **HTTPS** deb822 sources:

| Architecture | Repository | Suites |
| --- | --- | --- |
| `arm64` | `ports.ubuntu.com/ubuntu-ports` | `noble`, updates, backports, security |
| `amd64` | `archive.ubuntu.com/ubuntu` | `noble`, updates, backports |
| `amd64` | `security.ubuntu.com/ubuntu` | `noble-security` |

Each stanza sets `Architectures` and `Signed-By` explicitly. This keeps APT from
asking the ports repository for amd64 indexes. Ubuntu documents these fields in
[`sources.list(5)`](https://manpages.ubuntu.com/manpages/noble/man5/sources.list.5.html)
and the architecture registration operation in
[`dpkg(1)`](https://manpages.ubuntu.com/manpages/noble/man1/dpkg.1.html).

APT must verify every repository and package. The recipe has no `trusted=yes`,
authentication bypass, TLS verification bypass, ignored install errors, or
runtime package-install fallback. Package versions follow Ubuntu's current
security/update repositories; this is **not a byte-for-byte reproducible APT
snapshot**. Each finished image records all installed package versions in
`/opt/evolution/installed-packages.tsv`. Retain that receipt and the resulting
image digest with build evidence.

## Native tools and translated runtime

Git, Git LFS, GPG, Python, the standard build utilities, and the cross compiler
run natively as ARM64. The optional native JDK is available without overriding
`JAVA_HOME`; Android's pinned source configuration remains responsible for its
chosen prebuilts. The Repo launcher is supplied separately by the parent
workflow from the workspace's verified pin, not downloaded by this image.

The Ubuntu
[`gcc-x86-64-linux-gnu` cross compiler](https://packages.ubuntu.com/noble/gcc-x86-64-linux-gnu)
builds [`rosetta-probe.c`](rosetta-probe.c) into a dynamically linked x86-64 Linux
ELF. The build never executes the foreign probe or loader. Native Python checks
the ELF headers and ownership instead. Rosetta execution must be tested later
on the actual Mac's container runtime.

The runtime gate has this exact interface:

| Path | Required identity |
| --- | --- |
| `/opt/evolution/apple-container-builder` | Root-owned regular file, mode `0644`, exact bytes `evolution-apple-container-builder-v1\n` |
| `/opt/evolution/bin/rosetta-probe` | Root-owned executable, mode `0755`, ELF64 little-endian machine 62 |
| `/lib64/ld-linux-x86-64.so.2` | Resolves to Ubuntu's root-owned x86-64 ELF loader from `libc6:amd64` |
| `/usr/lib/x86_64-linux-gnu/libc.so.6` | amd64 C runtime |
| `/usr/lib/x86_64-linux-gnu/libstdc++.so.6` | amd64 C++ runtime |
| `/usr/lib/x86_64-linux-gnu/libz.so.1` | amd64 zlib runtime |

Executing the probe with Rosetta enabled must exit zero and print exactly:

```text
evolution-x86_64-probe-ok
```

The line ends with one newline. Merely finding the marker, checking ELF headers,
or booting Ubuntu does not meet this runtime check. A successful probe verifies
this small dynamic executable only; it does not establish compatibility with
every Android prebuilt or prove a complete ROM build.

## Filesystem and command contract

There is **no entrypoint**. The default command is `/bin/bash`; a command supplied
by the parent workflow replaces it unchanged. Starting the image does not copy
files, run package installation, edit sources, source `envsetup.sh`, or start a
sync/build.

| Setting | Default |
| --- | --- |
| Working directory | `/work/evolution` |
| `OUT_DIR` | `/work/out/evolution` |
| `CCACHE_DIR` | `/work/cache/ccache` |

The parent workflow mounts a named ext4 volume at `/work` and initializes these
directories there. The image's precreated directories are hidden by a new volume
mount, so the first initialization must use an existing working directory such
as `/work`. Source, output, and cache live on that Linux filesystem. The ccache
directory is configured, but this does not force Android to enable ccache.

Only a narrow, read-only control bundle should be shared from macOS. Do not mount
the entire home directory or private device-evidence tree. Changes inside the
named volume persist. Do not assume a writable virtiofs bind mount provides a
temporary copy or protects host files. Apple's
[command reference](https://github.com/apple/container/blob/main/docs/command-reference.md)
documents the separate read-only mount and Rosetta options; use the reference
matching the installed release when running the parent orchestration.

The image requires no `--cap-add ALL`, Android source patches, disabled artifact
path checks, or removed product definitions. Extra capabilities are not a
substitute for diagnosing a failing build. Preserve normal manifest pins,
filesystem checks, SELinux design, and device-specific bring-up prerequisites.

## Reference and validation limits

The requested
[AOSP module-build article](https://personaldevblog.web.app/en/blog/running-aosp-builds-on-mac-with-apple-container-en)
reports an Android 14 experiment. Its native ARM64 tools plus amd64 libraries
approach informs this image; its performance estimates and complete-build
claims are not verification for this Android 16 workspace.

The article's
[reference Containerfile at commit `8466fe2ff573160e8f199a5a1b2bafbe64703313`](https://github.com/wangchauyan/aosp-container/blob/8466fe2ff573160e8f199a5a1b2bafbe64703313/Containerfile)
was inspected as firsthand implementation evidence. This recipe does not adopt
its trusted-repository override, ignored installation failures, startup source
patches, or asserted default virtiofs copy-on-write behavior.

Run the workspace's offline suite from its root:

```sh
python3 -m unittest discover -s tests -v
```

The image tests check the pinned base, architecture-separated repositories,
signature settings, build-context boundary, native-only build commands, runtime
contract, and malformed ELF/marker rejection. They use the Python standard
library and do not start containers, install host tools, contact a phone, or
access the network. The parent workflow owns the actual image build, Rosetta
execution, ext4/case-sensitivity checks, and any later Android compilation.
