"""Offline host-signing tests using inert fixtures and mocked native operations.

No real key, signature, image, guest or device is used. The fixture private-key
file is deliberately invalid, and Python is forbidden from opening it after
setup. Native operations are simulated; real structural and image-set guards
remain active so these tests exercise the preparation/signing handoff.
"""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import avb_signing as signing

try:
    from . import test_avb_image_set as fixture
except ImportError:
    import test_avb_image_set as fixture


avb = signing.avb


def metadata_blob(raw):
    """Independent fixture decoder; no filesystem or native work."""
    if raw[-64:-60] == b"AVBf":
        _, _, _, _, offset, size, _ = struct.unpack_from(">4sIIQQQ28s", raw, len(raw) - 64)
    else:
        auth, aux = struct.unpack_from(">QQ", raw, 12)
        offset, size = 0, 256 + auth + aux
    return raw[offset:offset + size]


def raw_descriptors(raw):
    blob = metadata_blob(raw)
    auth = struct.unpack_from(">Q", blob, 12)[0]
    offset, length = struct.unpack_from(">QQ", blob, 96)
    data = blob[256 + auth + offset:256 + auth + offset + length]
    result, cursor = [], 0
    while cursor < len(data):
        _, following = struct.unpack_from(">QQ", data, cursor)
        result.append(data[cursor:cursor + 16 + following])
        cursor += 16 + following
    return result


def repeated_arguments(args, flag):
    return [args[index + 1] for index, word in enumerate(args) if word == flag]


class SigningTests(fixture.NoNativeTests):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="avb-signing-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "scripts").mkdir(mode=0o700)
        (self.root / "scripts/avb_signing.py").write_bytes(b"# INERT workflow identity fixture\n")
        source = self.root / "inputs"
        source.mkdir(mode=0o700)
        self.fx = fixture.SyntheticSet(source)
        self.new_key = self.fx.keys["recovery"]
        self.new_pem = self.fx.pems["recovery"]
        self.properties = [(b"com.android.build.boot.z", b"value:with colon\nand newline"),
                           (b"com.android.build.boot.a", b"\xff\x80binary property"),
                           (b"com.android.build.boot.empty", b"")]
        self.source_boot_salt = b"B" * 64
        self.set_boot_source()
        self.profile = deepcopy(self.fx.profile)
        self.profile["image_budgets"]["boot"] = 131072  # Keep synthetic signing copies small.
        self.profile["tools"]["avbtool"].update(fixture.identity((source / "tools/avbtool.py").read_bytes()))
        openssl = source / "tools/openssl"
        self.profile["tools"]["openssl"]["binaries"] = [
            {"platform": "darwin-arm64", "version": "synthetic", "build_allowed": True,
             **fixture.identity(openssl.read_bytes())}]
        self.profile_sha = fixture.identity(json.dumps(self.profile, sort_keys=True).encode())["sha256"]
        self.contract = json.loads(signing.CONTRACT.read_text())
        self.contract["verifier_profile"]["sha256"] = self.profile_sha
        self.contract["public_key"] = fixture.identity(self.new_pem)
        self.contract["avb_public_key_sha256"] = fixture.identity(self.new_key)["sha256"]
        self.contract["accepted_input_boot_keys"] = [fixture.identity(self.fx.keys["boot"])["sha256"],
                                                     fixture.identity(self.new_key)["sha256"]]
        self.contract["raw_descriptor_sources"] = {
            name: {"image": fixture.identity(self.fx.images[name]),
                   "descriptor": avb._descriptor(self.fx.descriptors[name])}
            for name in ("countrycode", "pvmfw")}
        self.contract_sha = fixture.identity(json.dumps(self.contract, sort_keys=True).encode())["sha256"]
        provenance = source / "provenance.json"
        provenance.write_text('{"fixture":"inert","hardware_tested":false}\n')
        self.input = {"schema_version": 1, "contract_id": signing.CONTRACT_ID,
                      "contract_sha256": self.contract_sha, "artifact_set_id": "synthetic-not-flashable",
                      "images": {name: deepcopy(row) for name, row in self.fx.manifest["images"].items()
                                 if name in signing.INPUTS},
                      "source_records": [{"path": provenance.name, **fixture.identity(provenance.read_bytes())}]}
        self.input_path = source / "signing-input.json"
        self.private_path = self.root / "never-open-host-key.pem"
        self.private_path.write_bytes(b"INERT fixture marker; not a real private key\n")
        self.private_path.chmod(0o600)
        self.public_path = source / "public/expected-recovery.pem"
        self.local_path = self.root / "local-recovery.json"
        self.local = {"key": str(self.private_path), "public_key": str(self.public_path),
                      "openssl": str(openssl)}
        self.local_path.write_text(json.dumps(self.local))
        self.avbtool = source / "tools/avbtool.py"
        self.calls, self.hook, self.verify_hook, self.verify_override = [], None, None, None
        self.fail_label, self.different_second_pass, self.counter = None, False, 0
        self.forbid_private_stat = False
        self.enterContext(mock.patch.object(signing, "ROOT", self.root))
        self.enterContext(mock.patch.object(signing, "load_contract", side_effect=self.contract_state))
        self.enterContext(mock.patch.object(avb, "load_profile", side_effect=lambda: (deepcopy(self.profile), self.profile_sha)))
        self.enterContext(mock.patch.object(signing.platform, "system", return_value="Darwin"))
        self.enterContext(mock.patch.object(signing.platform, "machine", return_value="arm64"))
        self.enterContext(mock.patch.object(signing.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)))
        self.prepare_tools = self.enterContext(mock.patch.object(signing.io, "_prepare_tools", side_effect=self.tools))
        self.runner = self.enterContext(mock.patch.object(signing.io, "_run", side_effect=self.native_step))
        self.real_verifier = avb.verify
        self.verifier = self.enterContext(mock.patch.object(avb, "verify", side_effect=self.independent_verifier))
        self.guard_private_path()

    def guard_private_path(self):
        def is_private(path):
            return isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).name == self.private_path.name
        for module, name in ((builtins, "open"), (io, "open"), (os, "open")):
            original = getattr(module, name)
            def guarded(path, *args, original=original, **kwargs):
                if is_private(path):
                    raise AssertionError("Python must never open the synthetic private key")
                return original(path, *args, **kwargs)
            self.enterContext(mock.patch.object(module, name, side_effect=guarded))
        for name in ("stat", "lstat"):
            original = getattr(os, name)
            def guarded(path, *args, original=original, **kwargs):
                if self.forbid_private_stat and is_private(path):
                    raise AssertionError("public-only work must not stat the private key")
                return original(path, *args, **kwargs)
            self.enterContext(mock.patch.object(os, name, side_effect=guarded))

    def contract_state(self):
        return deepcopy(self.contract), self.contract_sha, deepcopy(self.profile), self.profile_sha

    def set_boot_source(self, *, unsigned=False):
        descriptor = fixture.hash_descriptor("boot", self.fx.payloads["boot"], salt=self.source_boot_salt)
        self.fx.descriptors["boot"] = descriptor
        descriptors = [descriptor] + [fixture.property_descriptor(key, value) for key, value in self.properties]
        raw = fixture.with_footer(self.fx.payloads["boot"], fixture.vbmeta(
            descriptors, key=b"" if unsigned else self.fx.keys["boot"], rollback=0 if unsigned else 1769904000))
        self.fx.write_image("boot", raw)
        if hasattr(self, "input"):
            self.input["images"]["boot"] = deepcopy(self.fx.manifest["images"]["boot"])

    def tools(self, profile, work, **selected):
        (work / "tools").mkdir(mode=0o700)
        copied = work / "tools/avbtool.py"
        copied.write_bytes(Path(selected["avbtool"]).read_bytes())
        copied.chmod(0o600)
        paths = {"avbtool": copied, "openssl": Path(selected["openssl"])}
        identities = {name: fixture.identity(Path(path).read_bytes()) for name, path in selected.items()}
        originals = {Path(path): identities[name] for name, path in selected.items()}
        return paths, identities, originals, {"PATH": "/nonexistent", "LC_ALL": "C"}

    def native_step(self, label, args, env, work, records, **kwargs):
        self.calls.append((label, list(args), work))
        if label == self.fail_label:
            raise signing.io.TwrpWorkingError(label + " failed (mock native failure)")
        if "extract_public_key" in args:
            selected = Path(args[args.index("--key") + 1])
            self.assertEqual(selected.read_bytes(), self.new_pem)
            output = Path(args[args.index("--output") + 1])
            output.write_bytes(self.new_key)
        elif "pkey" in args:
            self.assertEqual(args[args.index("-in") + 1], self.private_path)
            self.assertIn("-pubout", args)
            output = Path(args[args.index("-out") + 1])
            output.write_bytes(self.new_pem)  # Never open the inert private-key file.
        elif "add_hash_footer" in args:
            image = Path(args[args.index("--image") + 1])
            payload = image.read_bytes()
            self.assertNotEqual(payload[-64:-60], b"AVBf", "signer must start from a payload-only copy")
            name = args[args.index("--partition_name") + 1]
            salt = bytes.fromhex(args[args.index("--salt") + 1])
            descriptors = [fixture.hash_descriptor(name, payload, salt=salt)]
            for item in repeated_arguments(args, "--prop_from_file"):
                key, path = item.split(":", 1)
                descriptors.append(fixture.property_descriptor(key.encode(), Path(path).read_bytes()))
            algorithm = args[args.index("--algorithm") + 1]
            key = b"" if algorithm == "NONE" else self.new_key
            metadata = fixture.vbmeta(descriptors, key=key,
                                      rollback=int(args[args.index("--rollback_index") + 1]),
                                      location=int(args[args.index("--rollback_index_location") + 1]))
            if "--do_not_append_vbmeta_image" in args:
                self.assertEqual(algorithm, "NONE")
                output = Path(args[args.index("--output_vbmeta_image") + 1])
                output.write_bytes(metadata)
                self.assertEqual(image.read_bytes(), payload)
            else:
                self.assertEqual(args[args.index("--key") + 1], self.private_path)
                compact = fixture.with_footer(payload, metadata)
                budget = int(args[args.index("--partition_size") + 1])
                self.assertGreaterEqual(budget, len(compact))
                image.write_bytes(compact[:-64] + bytes(budget - len(compact)) + compact[-64:])
        elif "make_vbmeta_image" in args:
            self.assertEqual(args[args.index("--key") + 1], self.private_path)
            descriptors = []
            for item in repeated_arguments(args, "--chain_partition"):
                name, location, path = item.split(":", 2)
                descriptors.append(fixture.chain_descriptor(name, int(location), Path(path).read_bytes()))
            for source in repeated_arguments(args, "--include_descriptors_from_image"):
                descriptors.extend(raw_descriptors(Path(source).read_bytes()))
            metadata = fixture.vbmeta(descriptors, key=self.new_key,
                                      rollback=int(args[args.index("--rollback_index") + 1]))
            if self.different_second_pass and label == "sign-vbmeta-2":
                changed = bytearray(metadata)
                changed[288] ^= 1
                metadata = bytes(changed)
            output = Path(args[args.index("--output") + 1])
            output.write_bytes(fixture.padded(metadata))
        elif "verify_image" in args:
            self.assertNotIn("--follow_chain_partitions", args)
            self.assertNotIn("--accept_zeroed_hashtree", args)
            self.check_mock_image(Path(args[args.index("--image") + 1]))
        else:
            raise AssertionError("unrecognized mocked native operation: " + label)
        record = {"step": label, "returncode": 0,
                  "stdout": fixture.identity(b"mocked native result"), "stderr": fixture.identity(b"")}
        records.append(record)
        signing.io._save(work / f"native-{len(records):02d}-{label}.json", record)
        if self.hook is not None:
            self.hook(label, args, work)

    def check_mock_image(self, path):
        blob = metadata_blob(path.read_bytes())
        if struct.unpack_from(">I", blob, 28)[0] == 2:
            if blob[288:800] != b"S" * 512:
                raise signing.io.TwrpWorkingError("mock native rejected the dummy signature")
        for raw in raw_descriptors(path.read_bytes()):
            if struct.unpack_from(">Q", raw)[0] != 2:
                continue
            _, _, size, _, nl, sl, dl, _, _ = struct.unpack_from(">QQQ32sIIII60s", raw)
            name = raw[132:132 + nl].decode()
            salt = raw[132 + nl:132 + nl + sl]
            digest = raw[132 + nl + sl:132 + nl + sl + dl]
            source = path.parent / (name + ".img")
            if hashlib.sha256(salt + source.read_bytes()[:size]).digest() != digest:
                raise signing.io.TwrpWorkingError("mock native rejected payload digest")

    def independent_verifier(self, path, expected_sha, **kwargs):
        if self.verify_override is not None:
            return deepcopy(self.verify_override)
        result = self.real_verifier(path, expected_sha, **kwargs)
        if self.verify_hook is not None:
            replacement = self.verify_hook(path, result)
            if replacement is not None:
                return replacement
        return result

    def save_input(self):
        raw = (json.dumps(self.input, sort_keys=True) + "\n").encode()
        self.input_path.write_bytes(raw)
        return fixture.identity(raw)["sha256"]

    def output(self, label):
        self.counter += 1
        return self.root / self.contract["output_root"] / f"{label}-{self.counter}"

    def prepare(self, output=None):
        out = output or self.output("prepare")
        result = signing.prepare(self.input_path, self.save_input(), local_config=self.local_path,
                                 output_dir=out, avbtool=self.avbtool)
        return out, result

    def sign(self, prepared=None, output=None):
        prepared = prepared or self.prepare()
        path = prepared[0] / "preparation.json"
        out = output or self.output("sign")
        result = signing.sign(path, fixture.identity(path.read_bytes())["sha256"], local_config=self.local_path,
                              output_dir=out, avbtool=self.avbtool)
        return out, result

    def test_plan_reads_no_local_configuration_images_keys_or_native_tools(self):
        self.forbid_private_stat = True
        for row in self.input["images"].values():
            (self.fx.root / row["path"]).unlink()
        self.local_path.unlink()
        with mock.patch.object(signing, "_local", side_effect=AssertionError("plan opened local config")), \
             mock.patch.object(signing, "_key_state", side_effect=AssertionError("plan stat'ed key")):
            result = signing.plan(self.input_path, self.save_input())
        self.assertEqual(result["status"], "ready_for_public_preparation")
        for field in ("native_commands_run", "private_key_accessed", "signing_performed", "complete_chain_verified"):
            self.assertFalse(result[field])
        self.runner.assert_not_called()
        self.prepare_tools.assert_not_called()

    def test_plan_reports_missing_inputs_and_provenance_without_promotion(self):
        self.input["images"].pop("vendor")
        self.input["source_records"] = []
        result = signing.plan(self.input_path, self.save_input())
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["missing_partitions"], ["vendor"])
        self.assertEqual(result["provenance_records_supplied"], 0)
        self.assertFalse(result["complete_rom_ready"])
        with self.assertRaises(signing.AvbSigningError):
            self.prepare()
        self.runner.assert_not_called()

    def test_public_preparation_never_resolves_stats_or_opens_private_key(self):
        self.forbid_private_stat = True
        with mock.patch.object(signing, "_key_state", side_effect=AssertionError("prepare stat'ed private key")):
            out, result = self.prepare()
        self.assertEqual(result["status"], "prepared_public_only")
        self.assertFalse(result["private_key_accessed"])
        self.assertFalse(result["signing_performed"])
        self.assertFalse(result["complete_chain_verified"])
        self.assertEqual(len(result["preparation"]["inputs"]), 15)
        self.assertFalse(any(str(self.private_path) in str(arg) for _, args, _ in self.calls for arg in args))
        self.assertNotIn(self.private_path.name, json.dumps(result))
        self.assertNotIn(self.private_path.name, (out / "input-manifest.json").read_text())
        self.assertFalse(list(out.rglob("*.img")))

    def test_boot_recipe_preserves_64_byte_salt_binary_empty_values_and_property_order(self):
        _, result = self.prepare()
        recipe = result["preparation"]["boot_recipe"]
        self.assertEqual(recipe["salt_hex"], self.source_boot_salt.hex())
        self.assertEqual(recipe["payload"], fixture.identity(self.fx.payloads["boot"]))
        self.assertEqual([p["name"] for p in recipe["properties"]], [k.decode() for k, _ in self.properties])
        self.assertEqual([{k: p[k] for k in ("sha256", "size_bytes")} for p in recipe["properties"]],
                         [fixture.identity(value) for _, value in self.properties])
        self.assertEqual([p["encoded_descriptor_sha256"] for p in recipe["properties"]],
                         [fixture.identity(fixture.property_descriptor(k, v))["sha256"] for k, v in self.properties])

    def test_complete_mock_sign_flow_reproduces_and_independently_checks_all_17_images(self):
        private_before = signing._key_state(self.private_path)
        out, result = self.sign()
        self.assertEqual(result["status"], "signed_and_verified")
        self.assertTrue(result["signing_performed"])
        self.assertTrue(result["complete_chain_verified"])
        self.assertTrue(result["two_pass_reproduction_verified"])
        self.assertEqual(result["signed_derivative_passes"][0], result["signed_derivative_passes"][1])
        self.assertEqual(set(result["verification"]["images"]), avb.PARTITIONS)
        self.assertEqual(result["unchanged_leaf_count"], 14)
        self.assertTrue(result["working76_preserved"])
        self.assertEqual((out / "boot.img").read_bytes()[:len(self.fx.payloads["boot"])], self.fx.payloads["boot"])
        self.assertEqual((out / "recovery.img").read_bytes(), self.fx.images["recovery"])
        for name in signing.INPUTS:
            row = self.input["images"][name]
            self.assertEqual((self.fx.root / row["path"]).read_bytes(), self.fx.images[name])
            if name != "boot":
                self.assertEqual((out / (name + ".img")).read_bytes(), self.fx.images[name])
        for name in ("vbmeta", "vbmeta_system"):
            self.assertEqual((out / (name + ".img")).stat().st_size, self.contract["vbmeta_output_size"])
        for field in ("private_key_copied", "private_key_payload_read_by_python", "keys_generated", "guest_accessed",
                      "complete_rom_ready", "oem_trust_established", "apk_apex_ota_signing_performed"):
            self.assertFalse(result[field], field)
        self.assertEqual(signing._key_state(self.private_path), private_before)
        self.assertEqual(stat.S_IMODE((out / "signing-receipt.json").stat().st_mode), 0o600)
        self.assertNotIn(str(self.private_path), json.dumps(result))
        self.assertNotIn(self.private_path.name, json.dumps(result))
        self.assertEqual(sum(signing.SECRET_LABEL in row["argv"] for row in result["native_results"]), 7)
        for path in out.rglob("*.json"):
            self.assertNotIn(self.private_path.name, path.read_text())

    def test_signing_commands_use_exact_imports_and_never_inherit_old_boot_or_root_metadata(self):
        out, _ = self.sign()
        signing_calls = [(label, args) for label, args, _ in self.calls if label.startswith("sign-")]
        self.assertEqual(len(signing_calls), 6)
        for label, args in signing_calls:
            self.assertEqual(args[args.index("--algorithm") + 1], "SHA256_RSA4096")
            self.assertEqual(args[args.index("--flags") + 1], "0")
            self.assertEqual(args[args.index("--rollback_index_location") + 1], "0")
            if label.startswith("sign-boot-"):
                self.assertEqual(repeated_arguments(args, "--include_descriptors_from_image"), [])
                self.assertEqual(args[args.index("--salt") + 1], self.source_boot_salt.hex())
                self.assertEqual(args[args.index("--rollback_index") + 1], "1769904000")
                self.assertEqual([item.split(":", 1)[0] for item in repeated_arguments(args, "--prop_from_file")],
                                 [key.decode() for key, _ in self.properties])
            else:
                imports = repeated_arguments(args, "--include_descriptors_from_image")
                names = [Path(path).stem for path in imports]
                expected = (self.contract["system_import_order"] if label.startswith("sign-vbmeta-system-")
                            else self.contract["root_direct_import_order"])
                self.assertEqual(names, expected)
                self.assertFalse({"boot", "recovery", "vbmeta", "vbmeta_system"} & set(names))
                self.assertEqual(args[args.index("--padding_size") + 1], "4096")
                if label.startswith("sign-vbmeta-system-"):
                    self.assertEqual(repeated_arguments(args, "--chain_partition"), [])
                    self.assertEqual(args[args.index("--rollback_index") + 1], "1769904000")
                else:
                    self.assertEqual(repeated_arguments(args, "--chain_partition"),
                                     [f"{name}:{location}:{out / 'public.avbpubkey'}"
                                      for name, location in (("boot", 3), ("recovery", 1), ("vbmeta_system", 2))])
                    self.assertEqual(args[args.index("--rollback_index") + 1], "0")

    def test_unsigned_boot_source_is_accepted_only_as_an_input_and_signed_in_output(self):
        self.set_boot_source(unsigned=True)
        out, result = self.sign()
        self.assertEqual(result["verification"]["images"]["boot"]["metadata"]["algorithm"], "SHA256_RSA4096")
        self.assertEqual((out / "boot.img").read_bytes()[:len(self.fx.payloads["boot"])], self.fx.payloads["boot"])

    def test_old_vbmeta_unknown_roles_booleans_and_changed_retained_identities_are_rejected(self):
        original = deepcopy(self.input)
        mutations = [lambda x: x.update(schema_version=True),
                     lambda x: x["images"].update(vbmeta=deepcopy(self.fx.manifest["images"]["vbmeta"])),
                     lambda x: x["images"].update(boot_a=deepcopy(x["images"]["boot"])),
                     lambda x: x["images"]["boot"].update(size_bytes=True)]
        mutations += [lambda x, name=name: x["images"][name].update(sha256="0" * 64)
                      for name in ("recovery", "countrycode", "pvmfw")]
        for index, mutate in enumerate(mutations):
            self.input = deepcopy(original)
            mutate(self.input)
            with self.subTest(index=index), self.assertRaises((signing.AvbSigningError, avb.AvbImageSetError)):
                self.prepare()
        self.runner.assert_not_called()

    def test_input_digest_and_bounded_json_provenance_are_required(self):
        digest = self.save_input()
        with self.assertRaisesRegex(signing.AvbSigningError, "manifest digest"):
            signing.plan(self.input_path, "0" * 64)
        for records in ([{"path": "key.pem", "size_bytes": 32, "sha256": "0" * 64}], True):
            self.input["source_records"] = records
            with self.subTest(records=records), self.assertRaises((signing.AvbSigningError, avb.AvbImageSetError)):
                self.prepare()
        self.runner.assert_not_called()

    def test_non_mac_or_wrong_architecture_refuses_before_local_or_private_access(self):
        for system, machine in (("Linux", "aarch64"), ("Darwin", "x86_64")):
            with self.subTest(system=system, machine=machine), \
                 mock.patch.object(signing.platform, "system", return_value=system), \
                 mock.patch.object(signing.platform, "machine", return_value=machine), \
                 mock.patch.object(signing, "_local", side_effect=AssertionError("non-Mac opened local config")), \
                 mock.patch.object(signing, "_key_state", side_effect=AssertionError("non-Mac accessed key")):
                with self.assertRaisesRegex(signing.AvbSigningError, "ARM64 Mac"):
                    signing.sign(self.root / "absent.json", "0" * 64, local_config=self.local_path,
                                 output_dir=self.output("forbidden"), avbtool=self.avbtool)
        self.runner.assert_not_called()

    def test_two_signing_passes_must_match_before_independent_verification(self):
        self.different_second_pass = True
        out = self.output("mismatch")
        with self.assertRaisesRegex(signing.AvbSigningError, "two signing passes"):
            self.sign(output=out)
        self.assertFalse((out / "signing-receipt.json").exists())
        self.verifier.assert_not_called()

    def test_independent_verifier_boolean_alone_cannot_publish_success(self):
        self.verify_override = {"complete_chain_verified": True}
        prepared = self.prepare()
        path = prepared[0] / "preparation.json"
        out = self.output("inadequate-verification")
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            code = signing.main(["sign", "--input", str(path), "--expected-sha256",
                                 fixture.identity(path.read_bytes())["sha256"],
                                 "--local-config", str(self.local_path), "--avbtool", str(self.avbtool),
                                 "--output-dir", str(out)])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(stderr.getvalue())["complete_chain_verified"])
        self.assertFalse((out / "signing-receipt.json").exists())

    def test_verified_output_cannot_change_after_the_reproduction_comparison(self):
        def hook(path, result):
            # Removing only zero padding can leave a valid vbmeta signature;
            # it must still fail the previously compared full-image identity.
            with (path.parent / "vbmeta.img").open("r+b") as stream:
                stream.truncate(4096)
        self.verify_hook = hook
        out = self.output("post-verify-change")
        with self.assertRaises((signing.AvbSigningError, avb.AvbImageSetError)):
            self.sign(output=out)
        self.assertFalse((out / "signing-receipt.json").exists())

    def test_verifier_receipt_must_bind_the_same_images_profile_and_manifest(self):
        changes = [lambda result: result["images"]["boot"]["identity"].update(sha256="0" * 64),
                   lambda result: result.update(manifest_sha256="0" * 64),
                   lambda result: result.update(profile_sha256="0" * 64),
                   lambda result: result.update(native_commands_run=False),
                   lambda result: result.update(inputs_unchanged=False),
                   lambda result: result.update(status="artifacts-inspected")]
        for index, change in enumerate(changes):
            def hook(path, result):
                change(result)
                return result
            self.verify_hook = hook
            out = self.output("wrong-verifier-evidence")
            with self.subTest(index=index), self.assertRaises(signing.AvbSigningError):
                self.sign(output=out)
            self.assertFalse((out / "signing-receipt.json").exists())

    def test_native_boot_signer_cannot_change_salt_or_property_order(self):
        for change_salt in (False, True):
            def hook(label, args, work):
                if label != "sign-boot-1":
                    return
                image = Path(args[args.index("--image") + 1])
                descriptors = raw_descriptors(image.read_bytes())
                if change_salt:
                    descriptors[0] = fixture.hash_descriptor("boot", self.fx.payloads["boot"], salt=b"x" * 32)
                else:
                    descriptors[1:] = reversed(descriptors[1:])
                compact = fixture.with_footer(self.fx.payloads["boot"], fixture.vbmeta(
                    descriptors, key=self.new_key, rollback=1769904000))
                budget = self.profile["image_budgets"]["boot"]
                image.write_bytes(compact[:-64] + bytes(budget - len(compact)) + compact[-64:])
            self.hook = hook
            out = self.output("changed-signed-boot")
            with self.subTest(salt=change_salt), self.assertRaisesRegex(signing.AvbSigningError, "descriptor or property"):
                self.sign(output=out)
            self.assertFalse((out / "signing-receipt.json").exists())
        self.verifier.assert_not_called()

    def test_raw_descriptor_carrier_must_match_the_retained_factory_descriptor(self):
        def hook(label, args, work):
            if label == "raw-countrycode":
                output = Path(args[args.index("--output_vbmeta_image") + 1])
                output.write_bytes(fixture.vbmeta([fixture.hash_descriptor(
                    "countrycode", self.fx.payloads["countrycode"], digest=b"X" * 32)]))
        self.hook = hook
        out = self.output("wrong-raw-carrier")
        with self.assertRaisesRegex(signing.AvbSigningError, "exact reviewed descriptor"):
            self.prepare(out)
        self.assertFalse((out / "preparation.json").exists())

    def test_duplicate_properties_across_imported_leaves_are_rejected_before_signing(self):
        for name in ("system", "product"):
            metadata = fixture.vbmeta([self.fx.descriptors[name],
                                      fixture.property_descriptor(b"com.android.build.duplicate", name.encode())])
            raw = fixture.with_footer(self.fx.payloads[name], metadata,
                                      tree_and_fec=b"T" * 4096 + b"F" * 8192)
            self.fx.write_image(name, raw)
            self.input["images"][name] = deepcopy(self.fx.manifest["images"][name])
        out = self.output("duplicate-imported-properties")
        with self.assertRaisesRegex(signing.AvbSigningError, "duplicate properties"):
            self.prepare(out)
        self.assertFalse((out / "preparation.json").exists())
        self.assertFalse(any(label.startswith("sign-") for label, _, _ in self.calls))

    def test_preparation_rechecks_source_images_and_workflow_before_publishing(self):
        for workflow in (False, True):
            selected = (self.root / "scripts/avb_signing.py" if workflow else
                        self.fx.root / self.input["images"]["boot"]["path"])
            original = selected.read_bytes()
            def hook(label, args, work):
                if label == "verify-input-vendor-dlkm":
                    selected.write_bytes(original + b"changed")
            self.hook = hook
            out = self.output("changed-preparation-source")
            with self.subTest(workflow=workflow), self.assertRaises((signing.AvbSigningError, avb.AvbImageSetError)):
                self.prepare(out)
            self.assertFalse((out / "preparation.json").exists())
            selected.write_bytes(original)

    def test_sign_rejects_preparation_from_different_workflow_bytes_before_key_access(self):
        prepared = self.prepare()
        workflow = self.root / "scripts/avb_signing.py"
        workflow.write_bytes(workflow.read_bytes() + b"changed")
        with mock.patch.object(signing, "_key_state", side_effect=AssertionError("changed workflow accessed key")):
            with self.assertRaisesRegex(signing.AvbSigningError, "public-only workflow"):
                self.sign(prepared=prepared)

    def test_unapproved_openssl_cannot_reach_private_key_derivation(self):
        self.profile["tools"]["openssl"]["binaries"][0]["build_allowed"] = False
        out = self.output("verify-only-openssl")
        with self.assertRaisesRegex(signing.AvbSigningError, "OpenSSL is not approved"):
            self.sign(output=out)
        self.assertFalse(any(label == "derive-signing-public" for label, _, _ in self.calls))
        self.assertFalse((out / "signing-receipt.json").exists())

    def test_private_key_metadata_requires_owner_only_regular_single_link_file(self):
        self.private_path.chmod(0o644)
        with self.assertRaises(signing.AvbSigningError):
            signing._key_state(self.private_path)
        self.private_path.chmod(0o600)
        with mock.patch.object(signing.os, "geteuid", return_value=os.geteuid() + 1):
            with self.assertRaises(signing.AvbSigningError):
                signing._key_state(self.private_path)
        alias = self.root / "key-hardlink"
        os.link(self.private_path, alias)
        with self.assertRaises(signing.AvbSigningError):
            signing._key_state(self.private_path)
        alias.unlink()
        link = self.root / "key-symlink"
        link.symlink_to(self.private_path)
        with self.assertRaises(signing.AvbSigningError):
            signing._key_state(link)

    def test_private_key_metadata_mutation_during_native_operation_is_rejected(self):
        def hook(label, args, work):
            if label == "derive-signing-public":
                self.private_path.chmod(0o400)
        self.hook = hook
        out = self.output("key-mode-changed")
        with self.assertRaisesRegex(signing.AvbSigningError, "private key metadata changed"):
            self.sign(output=out)
        self.assertFalse((out / "signing-receipt.json").exists())

    def test_copied_native_tool_mutation_is_rejected(self):
        def hook(label, args, work):
            if label == "sign-boot-1":
                tool = work / "tools/avbtool.py"
                tool.write_bytes(tool.read_bytes() + b"changed")
        self.hook = hook
        out = self.output("tool-changed")
        with self.assertRaises(avb.AvbImageSetError):
            self.sign(output=out)
        self.assertFalse((out / "signing-receipt.json").exists())

    def test_native_failure_and_private_key_errors_publish_no_success_or_path(self):
        prepared = self.prepare()
        path = prepared[0] / "preparation.json"
        digest = fixture.identity(path.read_bytes())["sha256"]
        self.fail_label = "sign-boot-1"
        out = self.output("native-failure")
        arguments = ["sign", "--input", str(path), "--expected-sha256", digest,
                     "--local-config", str(self.local_path), "--avbtool", str(self.avbtool), "--output-dir", str(out)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(signing.main(arguments), 2)
        self.assertFalse((out / "signing-receipt.json").exists())
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(self.private_path.name, stderr.getvalue())
        self.assertFalse(json.loads(stderr.getvalue())["complete_chain_verified"])
        self.fail_label = None
        self.private_path.unlink()
        arguments[-1] = str(self.output("missing-private-key"))
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            self.assertEqual(signing.main(arguments), 2)
        self.assertNotIn(self.private_path.name, stderr.getvalue())
        self.assertEqual(json.loads(stderr.getvalue())["status"], "failed")

    def test_fresh_output_refuses_reuse_escape_or_symlink_without_overwrite(self):
        out, _ = self.prepare()
        original = (out / "preparation.json").read_bytes()
        with self.assertRaises(signing.io.TwrpWorkingError):
            self.prepare(out)
        self.assertEqual((out / "preparation.json").read_bytes(), original)
        with self.assertRaisesRegex(signing.AvbSigningError, "new ignored"):
            self.prepare(self.root / "outside-output-root")
        alias = self.root / self.contract["output_root"] / "alias"
        alias.symlink_to(out, target_is_directory=True)
        with self.assertRaises((signing.io.TwrpWorkingError, avb.envelope.ImageInspectionError, OSError)):
            self.prepare(alias / "nested")
        self.assertFalse((out / "nested").exists())

    def test_prepared_configuration_and_input_changes_cannot_be_silently_reused(self):
        prepared = self.prepare()
        self.local["key"] = "different-unopened-key.pem"
        self.local_path.write_text(json.dumps(self.local))
        with self.assertRaisesRegex(signing.AvbSigningError, "local configuration changed"):
            self.sign(prepared=prepared)
        self.assertFalse(any(label == "derive-signing-public" for label, _, _ in self.calls))

    def test_private_selector_cannot_be_selected_as_tool_public_key_or_image(self):
        self.forbid_private_stat = True
        original_tool = self.avbtool
        for role in ("avbtool", "public_key", "openssl", "boot"):
            with self.subTest(role=role):
                local = deepcopy(self.local)
                if role == "avbtool":
                    self.avbtool = self.private_path
                elif role == "boot":
                    self.input["images"]["boot"]["path"] = str(self.private_path)
                else:
                    local[role] = str(self.private_path)
                self.local_path.write_text(json.dumps(local))
                with self.assertRaisesRegex(signing.AvbSigningError, "private signing selector"):
                    self.prepare()
                self.avbtool = original_tool
                self.input["images"]["boot"] = deepcopy(self.fx.manifest["images"]["boot"])
                self.local_path.write_text(json.dumps(self.local))
        self.runner.assert_not_called()

    def test_tool_symlink_and_hardlink_to_private_file_are_rejected_before_read(self):
        self.forbid_private_stat = True
        symbolic = self.root / "tool-symbolic-alias.py"
        symbolic.symlink_to(self.private_path)
        self.avbtool = symbolic
        with self.assertRaisesRegex(signing.AvbSigningError, "private signing selector"):
            self.prepare()
        hard = self.root / "tool-hard-alias.py"
        os.link(self.private_path, hard)
        self.avbtool = hard
        try:
            with self.assertRaisesRegex(signing.AvbSigningError, "singly linked"):
                self.prepare()
        finally:
            hard.unlink()
        self.runner.assert_not_called()

    def test_legitimate_tool_alias_is_resolved_without_inspecting_private_key(self):
        self.forbid_private_stat = True
        alias = self.root / "selected-tool.py"
        alias.symlink_to(self.avbtool)
        self.avbtool = alias
        _, result = self.prepare()
        self.assertEqual(result["status"], "prepared_public_only")
        self.assertFalse(result["private_key_accessed"])

    def test_original_images_and_provenance_stay_bound_through_final_verification(self):
        for relative in (self.input["images"]["boot"]["path"], self.input["source_records"][0]["path"]):
            target = self.input_path.parent / relative
            original = target.read_bytes()
            def hook(path, result):
                target.write_bytes(original + b"changed after independent verification")
            self.verify_hook = hook
            out = self.output("changed-source-after-verification")
            try:
                with self.subTest(source=relative), self.assertRaises((signing.AvbSigningError, avb.AvbImageSetError)):
                    self.sign(output=out)
                self.assertFalse((out / "signing-receipt.json").exists())
            finally:
                target.write_bytes(original)
                self.verify_hook = None


class PublicSigningContractTests(fixture.NoNativeTests):
    def test_json_selector_rejects_pem_header_before_reading_any_payload(self):
        stream = mock.Mock()
        stream.read.return_value = b"-"
        context = mock.MagicMock()
        context.__enter__.return_value = (stream, SimpleNamespace(st_size=2048))
        with mock.patch.object(avb, "_input", return_value=context):
            with self.assertRaisesRegex(signing.AvbSigningError, "expected a JSON object"):
                signing._json_file(Path("unused-private-fixture.pem"), 4096)
        stream.read.assert_called_once_with(1)

    def test_public_contract_locks_existing_key_and_keeps_device_and_rom_gates_false(self):
        contract, digest, profile, profile_sha = signing.load_contract()
        self.assertEqual(len(contract["input_partitions"]), 15)
        self.assertEqual(contract["key_roles"], {name: "existing-working76-development-key" for name in avb.SIGNED})
        self.assertFalse(contract["new_avb_key_required"])
        self.assertEqual(contract["avb_public_key_sha256"], profile["working76"]["avb_public_key_sha256"])
        self.assertEqual(contract["reproduction"]["passes"], 2)
        self.assertFalse(contract["limits"]["complete_rom_ready"])
        self.assertFalse(contract["limits"]["device_operations"])
        self.assertEqual(len(digest), len(profile_sha))

    def reject_contract_mutations(self, mutations):
        original = json.loads(signing.CONTRACT.read_text())
        real_json = signing._json_file
        for label, mutate in mutations:
            changed = deepcopy(original)
            mutate(changed)
            raw = json.dumps(changed, sort_keys=True).encode()
            def read(path, maximum, expected=None):
                if Path(path) == signing.CONTRACT:
                    return raw
                return real_json(path, maximum, expected)
            with self.subTest(mutation=label), mock.patch.object(signing, "_json_file", side_effect=read):
                with self.assertRaises((signing.AvbSigningError, avb.AvbImageSetError)):
                    signing.load_contract()

    def test_contract_cannot_drop_or_duplicate_required_implementation_and_evidence_pins(self):
        self.reject_contract_mutations([
            ("removed implementation", lambda c: c["implementation_dependencies"].pop()),
            ("duplicate implementation", lambda c: c["implementation_dependencies"].append(
                deepcopy(c["implementation_dependencies"][0]))),
            ("removed evidence", lambda c: c["source_evidence"].pop()),
            ("changed dependency identity", lambda c: c["implementation_dependencies"][0].update(sha256="0" * 64)),
        ])

    def test_contract_cannot_broaden_accepted_boot_keys_or_repin_retained_factory_inputs(self):
        self.reject_contract_mutations([
            ("broader input key", lambda c: c["accepted_input_boot_keys"].append("0" * 64)),
            ("different raw image", lambda c: c["raw_descriptor_sources"]["pvmfw"]["image"].update(sha256="0" * 64)),
            ("different factory root", lambda c: c["factory_vbmeta_identity"].update(sha256="0" * 64)),
            ("replacement working public key", lambda c: c["public_key"].update(sha256="0" * 64)),
        ])

    def test_contract_cannot_promote_readiness_guest_key_access_or_other_signing_scope(self):
        self.reject_contract_mutations([
            ("ROM readiness", lambda c: c["limits"].update(complete_rom_ready=True)),
            ("guest private keys", lambda c: c["limits"].update(private_keys_in_guest=True)),
            ("OTA signing", lambda c: c["limits"].update(apk_apex_ota_signing=True)),
            ("key generation", lambda c: c.update(new_avb_key_required=True)),
            ("unknown scope field", lambda c: c.update(skip_verification=True)),
        ])


if __name__ == "__main__":
    unittest.main()
