"""Offline checks for the Apple Container image; never start a container."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import stat
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "containers" / "apple"
RECIPE = (CONTEXT / "Containerfile").read_text()
SPEC = importlib.util.spec_from_file_location("apple_image_verifier", CONTEXT / "verify-image.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def instructions():
    result = []
    current = ""
    for raw in RECIPE.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        current += line.removesuffix("\\").strip() + " "
        if not line.endswith("\\"):
            result.append(current.strip())
            current = ""
    if current:
        raise AssertionError("unterminated Containerfile instruction")
    return result


def source_stanzas(filename):
    blocks = (CONTEXT / filename).read_text().strip().split("\n\n")
    return [dict(line.split(": ", 1) for line in block.splitlines()) for block in blocks]


def elf_header(machine=62):
    header = bytearray(64)
    header[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<H", header, 18, machine)
    return bytes(header)


class ContainerRecipeTests(unittest.TestCase):
    def test_official_arm64_base_is_pinned_to_recorded_manifest(self):
        record = json.loads((CONTEXT / "base-image.json").read_text())
        self.assertEqual(record["registry"], "docker.io/library/ubuntu")
        self.assertEqual(record["tag_used_for_discovery"], "24.04")
        self.assertEqual(record["platform"], "linux/arm64/v8")
        for field in ("index_digest", "arm64_manifest_digest", "config_digest"):
            self.assertRegex(record[field], r"^sha256:[0-9a-f]{64}$")
        self.assertIn("ARG UBUNTU_IMAGE=" + record["registry"] + "@" + record["arm64_manifest_digest"], instructions())
        self.assertIn("FROM --platform=linux/arm64 ${UBUNTU_IMAGE}", instructions())

    def test_native_architecture_and_ca_bootstrap_precede_multiarch(self):
        self.assertIn('test "$(dpkg --print-architecture)" = arm64', RECIPE)
        bootstrap = RECIPE.index("apt-get install -y --no-install-recommends ca-certificates")
        replacement = RECIPE.index("COPY ubuntu-arm64.sources")
        multiarch = RECIPE.index("dpkg --add-architecture amd64")
        self.assertLess(bootstrap, replacement)
        self.assertLess(replacement, multiarch)

    def test_arm64_uses_only_ports_with_explicit_architecture(self):
        stanzas = source_stanzas("ubuntu-arm64.sources")
        self.assertEqual(len(stanzas), 1)
        self.assertEqual(stanzas[0]["URIs"], "https://ports.ubuntu.com/ubuntu-ports")
        self.assertEqual(stanzas[0]["Architectures"], "arm64")
        self.assertEqual(set(stanzas[0]["Suites"].split()), {"noble", "noble-updates", "noble-backports", "noble-security"})

    def test_amd64_has_separate_archive_and_security_stanzas(self):
        stanzas = source_stanzas("ubuntu-amd64.sources")
        self.assertEqual(len(stanzas), 2)
        by_uri = {entry["URIs"]: entry for entry in stanzas}
        archive = by_uri["https://archive.ubuntu.com/ubuntu"]
        security = by_uri["https://security.ubuntu.com/ubuntu"]
        self.assertEqual(set(archive["Suites"].split()), {"noble", "noble-updates", "noble-backports"})
        self.assertEqual(security["Suites"], "noble-security")
        self.assertTrue(all(entry["Architectures"] == "amd64" for entry in stanzas))

    def test_all_final_apt_sources_use_https_and_ubuntu_signature_key(self):
        for entry in source_stanzas("ubuntu-arm64.sources") + source_stanzas("ubuntu-amd64.sources"):
            self.assertTrue(entry["URIs"].startswith("https://"))
            self.assertEqual(entry["Types"], "deb")
            self.assertEqual(entry["Signed-By"], "/usr/share/keyrings/ubuntu-archive-keyring.gpg")
            self.assertEqual(set(entry), {"Types", "URIs", "Suites", "Components", "Architectures", "Signed-By"})

    def test_native_tools_and_amd64_runtime_packages_are_explicit(self):
        install = next(line for line in instructions() if line.startswith("RUN dpkg --add-architecture"))
        after_install = install.split("apt-get install -y --no-install-recommends", 1)[1].split("&&", 1)[0]
        packages = set(shlex.split(after_install))
        self.assertTrue({
            "git", "git-lfs", "gnupg", "python3", "build-essential", "ca-certificates",
            "gcc-x86-64-linux-gnu", "libc6-dev-amd64-cross", "binutils-x86-64-linux-gnu",
            "libc6:amd64", "libgcc-s1:amd64", "libstdc++6:amd64", "zlib1g:amd64",
        }.issubset(packages))
        self.assertNotIn("git:amd64", packages)
        self.assertNotIn("python3:amd64", packages)
        self.assertNotIn("build-essential:amd64", packages)

    def test_build_commands_do_not_execute_foreign_probe_or_loader(self):
        allowed_commands = {
            "test", "apt-get", "rm", "dpkg", "install", "x86_64-linux-gnu-gcc",
            "chown", "chmod", "python3", "dpkg-query",
        }
        for instruction in instructions():
            if not instruction.startswith("RUN "):
                continue
            for command in instruction[4:].split("&&"):
                tokens = shlex.split(command.strip())
                self.assertIn(tokens[0], allowed_commands)
                if tokens[0] == "python3":
                    self.assertEqual(tokens[1:], ["/opt/evolution/image/verify-image.py"])
                if tokens[0] == "rm":
                    self.assertEqual(tokens[1:], ["-rf", "/var/lib/apt/lists/*"])
        self.assertIn("x86_64-linux-gnu-gcc -O2", RECIPE)
        self.assertIn("-Wl,--dynamic-linker=/lib64/ld-linux-x86-64.so.2", RECIPE)

    def test_no_authentication_bypass_or_ignored_install_failure(self):
        for forbidden in ("trusted=yes", "--allow-unauthenticated", "Verify-Peer=false", "Verify-Host=false", "|| true", "|| echo"):
            self.assertNotIn(forbidden, RECIPE)
        self.assertIn('SHELL ["/bin/bash", "-euo", "pipefail", "-c"]', instructions())

    def test_runtime_has_no_entrypoint_or_source_mutation(self):
        self.assertFalse(any(line.startswith("ENTRYPOINT") for line in instructions()))
        self.assertIn('CMD ["/bin/bash"]', instructions())
        for forbidden in ("--cap-add", "BUILD_BROKEN_ARTIFACT_PATH_REQUIREMENT", "artifact_path_requirements.mk", "finder.go", "AndroidProducts.mk"):
            self.assertNotIn(forbidden, RECIPE)

    def test_work_paths_are_inside_the_named_volume_mount(self):
        self.assertIn("WORKDIR /work/evolution", instructions())
        self.assertIn("OUT_DIR=/work/out/evolution", RECIPE)
        self.assertIn("CCACHE_DIR=/work/cache/ccache", RECIPE)

    def test_marker_and_probe_have_the_host_gate_contract(self):
        self.assertEqual((CONTEXT / "builder-marker").read_bytes(), b"evolution-apple-container-builder-v1\n")
        self.assertIn("chmod 0644 /opt/evolution/apple-container-builder", RECIPE)
        self.assertIn("chmod 0755 /opt/evolution/bin/rosetta-probe", RECIPE)
        self.assertIn("chown 0:0 /opt/evolution/apple-container-builder /opt/evolution/bin/rosetta-probe", RECIPE)
        probe = (CONTEXT / "rosetta-probe.c").read_text()
        self.assertIn('puts("evolution-x86_64-probe-ok")', probe)
        self.assertIn("!defined(__x86_64__)", probe)
        self.assertIn("defined(__ILP32__)", probe)
        self.assertIn("sizeof(void *) == 8", probe)

    def test_build_context_contains_no_source_or_evidence_copy(self):
        allowed = {
            "Containerfile", "ubuntu-arm64.sources", "ubuntu-amd64.sources", "builder-marker",
            "rosetta-probe.c", "verify-image.py", "base-image.json",
        }
        ignore_lines = (CONTEXT / ".dockerignore").read_text().splitlines()
        self.assertEqual(ignore_lines[0], "*")
        self.assertEqual({line.removeprefix("!") for line in ignore_lines[1:]}, allowed)
        for instruction in instructions():
            self.assertFalse(instruction.startswith("ADD "))
            if instruction.startswith("COPY "):
                for source in shlex.split(instruction)[1:-1]:
                    self.assertIn(source, allowed)
                    self.assertTrue((CONTEXT / source).is_file())

    def test_installed_package_versions_are_recorded(self):
        self.assertIn("dpkg-query -W", RECIPE)
        self.assertIn("/opt/evolution/installed-packages.tsv", RECIPE)


class ImageVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "elf"
        self.path.write_bytes(elf_header())

    def details(self, mode=0o755, uid=0, kind=stat.S_IFREG):
        return SimpleNamespace(st_mode=kind | mode, st_uid=uid)

    def test_machine_reader_accepts_x86_64_and_arm64(self):
        self.assertEqual(verifier.elf_machine(elf_header(62)), 62)
        self.assertEqual(verifier.elf_machine(elf_header(183)), 183)

    def test_machine_reader_rejects_wrong_format_and_short_headers(self):
        for offset, replacement in ((0, 0), (4, 1), (5, 2), (6, 0)):
            data = bytearray(elf_header())
            data[offset] = replacement
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                verifier.elf_machine(bytes(data))
        with self.assertRaises(ValueError):
            verifier.elf_machine(elf_header()[:63])

    def test_root_owned_expected_elf_is_accepted_without_execution(self):
        with mock.patch.object(Path, "stat", return_value=self.details()):
            verifier.check_elf(self.path, 62, executable=True)

    def test_wrong_architecture_is_rejected(self):
        with mock.patch.object(Path, "stat", return_value=self.details()):
            with self.assertRaisesRegex(ValueError, "architecture"):
                verifier.check_elf(self.path, 183)

    def test_non_root_writable_and_nonregular_elfs_are_rejected(self):
        for details in (self.details(uid=1000), self.details(mode=0o775), self.details(mode=0o757), self.details(kind=stat.S_IFDIR)):
            with self.subTest(details=details), mock.patch.object(Path, "stat", return_value=details):
                with self.assertRaisesRegex(ValueError, "root-owned"):
                    verifier.check_elf(self.path, 62)

    def test_required_executable_permission_is_checked(self):
        with mock.patch.object(Path, "stat", return_value=self.details(mode=0o644)):
            with self.assertRaisesRegex(ValueError, "executable"):
                verifier.check_elf(self.path, 62, executable=True)

    def test_marker_requires_exact_bytes_and_mode(self):
        marker = self.root / "marker"
        marker.write_bytes(verifier.MARKER)
        for mode in (0o444, 0o644):
            with mock.patch.object(Path, "lstat", return_value=self.details(mode=mode)):
                verifier.check_marker(marker)
        for details in (self.details(mode=0o664), self.details(mode=0o644, uid=1000), self.details(mode=0o644, kind=stat.S_IFLNK)):
            with self.subTest(details=details), mock.patch.object(Path, "lstat", return_value=details):
                with self.assertRaises(ValueError):
                    verifier.check_marker(marker)
        marker.write_bytes(verifier.MARKER.rstrip())
        with mock.patch.object(Path, "lstat", return_value=self.details(mode=0o644)):
            with self.assertRaises(ValueError):
                verifier.check_marker(marker)

    def test_main_checks_native_compiler_and_amd64_runtime_but_does_not_claim_execution(self):
        output = io.StringIO()
        with mock.patch.object(verifier, "check_marker") as marker, mock.patch.object(verifier, "check_elf") as elf:
            with contextlib.redirect_stdout(output):
                verifier.main()
        marker.assert_called_once_with(Path("/opt/evolution/apple-container-builder"))
        elf.assert_any_call(Path("/usr/bin/x86_64-linux-gnu-gcc"), 183, executable=True)
        elf.assert_any_call(Path("/lib64/ld-linux-x86-64.so.2"), 62)
        elf.assert_any_call(Path("/opt/evolution/bin/rosetta-probe"), 62, executable=True)
        self.assertEqual(elf.call_count, 8)
        self.assertIn("Rosetta execution still required", output.getvalue())
        self.assertNotIn("evolution-x86_64-probe-ok", output.getvalue())


if __name__ == "__main__":
    unittest.main()
