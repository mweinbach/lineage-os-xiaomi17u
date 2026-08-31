"""Offline adversarial checks of the explicitly selected Evolution base.

The native corpus below is synthetic. It exercises composition and ownership;
it is neither Android compiler output nor evidence that any image can boot.
"""

from collections import Counter, defaultdict
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import evolution_policy_base as eb
from scripts import framework_provider_policy as fp
from scripts import oem_policy as op
from scripts import vendor_policy as vp
from tests.test_oem_policy import native_fixture as legacy_fixture


ROOT = Path(__file__).resolve().parents[1]
PLATFORM = op.INPUT_FLAGS["platform_cil"]
FACTORY = op.INPUT_FLAGS["factory_pub"]
CAMERA = "vendor_persist_camera_prop"
APP = "evolution_test_app"
EXEC = "evolution_test_app_exec"
SERVICE = "evolution_test_service"
BASE_TYPES = {CAMERA, APP, EXEC, SERVICE}
INHERITED = "base_typeattr_7"
BASE_LOCAL = "base_typeattr_50"
FULL_LOCAL = "base_typeattr_1050"


def cil(expressions):
    return ("\n".join(vp.render(expr) for expr in expressions) + "\n").encode()


def context_bytes(rows):
    return ("\n".join(" ".join(str(value) for value in row if value is not None)
                      for row in rows) + "\n").encode()


def rename(expression, before, after):
    if isinstance(expression, str):
        return after if expression == before else expression
    return tuple(rename(item, before, after) for item in expression)


def combined_named_assignments(expressions):
    """Model checkpolicy's single union assignment for each named attribute."""
    kept, members = [], defaultdict(set)
    for expression in expressions:
        if expression[0] == "typeattributeset" and not expression[1].startswith("base_typeattr_"):
            members[expression[1]].update(expression[2])
        else:
            kept.append(expression)
    return kept + [("typeattributeset", name, tuple(sorted(values)))
                   for name, values in sorted(members.items())]


def composition_fixture():
    """Keep the public budgets, rebinding only copied immutable CIL anchors."""
    oem = copy.deepcopy(op.load_contract())
    properties = copy.deepcopy(op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH))
    provider = copy.deepcopy(fp.load_contract())
    owned = op._compose_contract(oem, properties)
    contract = copy.deepcopy(eb.load_contract())
    specifications = {**owned["types"], **provider["types"]}
    domains = ("init", "servicemanager", "audioserver", "surfaceflinger", "atrace", "shell",
               "system_app", "traceur_app", "untrusted_app", "su", "mediaextractor", "mediaserver")
    objects = ("audioserver_service", "surfaceflinger_service")
    attributes = {attr for spec in specifications.values() for attr in spec["attributes"]}
    platform = [("role", "r"), ("role", "object_r")]
    for name in domains + objects:
        platform.extend((("type", name), ("roletype", "object_r", name)))
    platform += [("typeattribute", attr) for attr in sorted(attributes)]
    platform += [
        ("typeattributeset", "domain", domains),
        ("typeattributeset", "coredomain", ("init", "audioserver", "surfaceflinger", "mediaextractor", "mediaserver")),
        ("roletype", "r", "domain"),
        ("typeattribute", INHERITED),
        ("typeattributeset", INHERITED, ("init",)),
        ("neverallow", "shell", "audioserver_service", ("service_manager", ("add",))),
        ("neverallowx", "init", "self", ("ioctl", "file", ("range", "0x0", "0xff"))),
    ]
    factory = [("type", CAMERA), ("roletype", "object_r", CAMERA)]
    factory += [("type", name) for name in owned["types"] if owned["types"][name]["versioned_attribute"]]

    owned_forms = [("typeattribute", name) for name in contract["owned_attribute_declarations"]]
    mapping, public = [], []
    for name, spec in specifications.items():
        owned_forms += [("type", name), ("roletype", "object_r", name)]
        owned_forms += [("typeattributeset", attribute, (name,)) for attribute in spec["attributes"]]
        if spec["versioned_attribute"] is not None:
            version = spec["versioned_attribute"]
            mapping += [("typeattribute", version), ("typeattributeset", version, (name,)),
                        ("expandtypeattribute", (version,), "true")]
            public.append(("type", name))
    for row in properties["read_clauses"]:
        owned_forms.append(("allow", row["source_type"], row["target_type"],
                            (row["class"], tuple(row["permissions"]))))
    # The provider guard's existing budget is independent of the new base
    # composition helper; no expected forms are obtained from that helper.
    for expression, count in fp.expected_native_forms(provider).items():
        owned_forms.extend([expression] * count)
    for index, row in enumerate(provider["native_policy_budget"]["registration_assertions"]):
        attribute = "base_typeattr_" + str(9000 + index)
        owned_forms += [
            ("typeattribute", attribute),
            ("typeattributeset", attribute, ("and", ("domain",), ("not", tuple(row["exclude_domains"])))),
            ("neverallow", attribute, row["service"], ("service_manager", (row["permission"],))),
        ]
    base_forms = []
    for name in sorted(BASE_TYPES):
        base_forms.extend((("type", name), ("roletype", "object_r", name)))
    base_forms += [
        ("typeattributeset", "domain", (APP,)),
        ("typeattributeset", "coredomain", (APP,)),
        ("typeattributeset", "file_type", (EXEC,)),
        ("typeattributeset", "exec_type", (EXEC,)),
        ("typeattributeset", "service_manager_type", (SERVICE,)),
        ("typeattributeset", "property_type", (CAMERA,)),
        ("typeattributeset", "system_property_type", (CAMERA,)),
        ("typeattributeset", "system_public_property_type", (CAMERA,)),
        ("typeattribute", "evolution_test_scope"),
        ("typeattributeset", "evolution_test_scope", (APP,)),
        ("typeattributeset", INHERITED, (APP,)),
        ("typeattribute", BASE_LOCAL),
        ("typeattributeset", BASE_LOCAL, ("and", ("domain",), ("not", ("init", "shell")))),
        ("expandtypeattribute", (BASE_LOCAL,), "false"),
        ("allow", APP, CAMERA, ("file", ("getattr", "read"))),
        ("dontaudit", APP, EXEC, ("file", ("getattr",))),
        ("typetransition", "init", EXEC, "process", APP),
        ("neverallow", BASE_LOCAL, SERVICE, ("service_manager", ("add",))),
    ]
    version = CAMERA + "_202504"
    base_mapping = [("typeattribute", version), ("typeattributeset", version, (CAMERA,)),
                    ("expandtypeattribute", (version,), "true")]
    base = {
        "system_ext_cil": cil(base_forms), "system_ext_mapping": cil(base_mapping),
        "public_cil": cil([("type", CAMERA)]),
        "property_contexts": f"persist.evolution.test u:object_r:{CAMERA}:s0 exact bool\n".encode(),
        "file_contexts": f"/system_ext/bin/evolution_test u:object_r:{EXEC}:s0\n".encode(),
        "service_contexts": f"evolution.test u:object_r:{SERVICE}:s0\n".encode(),
    }
    contexts = {
        "property_contexts": base["property_contexts"] + context_bytes([
            tuple(row[key] for key in ("property_pattern", "context", "match", "value_type"))
            for row in properties["property_contexts"]]),
        **{kind: base[kind] + context_bytes(provider["context_entries"][kind])
           for kind in ("file_contexts", "service_contexts")},
    }
    corpus = {runtime: b"\n" for runtime in op.INPUT_FLAGS.values()}
    corpus[PLATFORM] = cil(platform)
    corpus[FACTORY] = cil(factory)
    corpus[eb.EXT] = cil(combined_named_assignments(
        [rename(expression, BASE_LOCAL, FULL_LOCAL) for expression in base_forms] + owned_forms))
    corpus[eb.MAPPING] = cil(base_mapping + mapping)
    for row in contract["unchanged_cil_inputs"]:
        raw = corpus[row["runtime_path"]]
        forms = vp.parse(raw)
        row.update(sha256=vp.sha(raw), size_bytes=len(raw),
                   neverallow=sum(form.expr[0] == "neverallow" for form in forms),
                   neverallowx=sum(form.expr[0] == "neverallowx" for form in forms))
    contract["original_assertions"].update(immutable_input_neverallows=1, immutable_input_neverallowx=1)
    return dict(corpus=corpus, owned_contract=owned, properties=properties, provider=provider,
                base=base, contract=contract, full_contexts=contexts,
                full_public=base["public_cil"] + cil(public))


def check_fixture(fixture):
    arguments = dict(fixture)
    parsed = {runtime: vp.parse(raw, runtime) for runtime, raw in fixture["corpus"].items()}
    policy = vp.Policy([form for forms in parsed.values() for form in forms])
    return eb.check_composition(parsed=parsed, actual=policy, **arguments)


def rebind_fixture_inputs(fixture):
    """Bind synthetic immutable inputs, never a firmware or Android artifact."""
    counts = Counter()
    for row in fixture["contract"]["unchanged_cil_inputs"]:
        raw = fixture["corpus"][row["runtime_path"]]
        forms = vp.parse(raw)
        row.update(sha256=vp.sha(raw), size_bytes=len(raw),
                   neverallow=sum(form.expr[0] == "neverallow" for form in forms),
                   neverallowx=sum(form.expr[0] == "neverallowx" for form in forms))
        counts.update({head: row[head] for head in ("neverallow", "neverallowx")})
    fixture["contract"]["original_assertions"].update(
        immutable_input_neverallows=counts["neverallow"], immutable_input_neverallowx=counts["neverallowx"])


def camera_composition_fixture():
    fixture = composition_fixture()
    fixture["camera_contract"] = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
    fixture["corpus"][PLATFORM] += cil([
        ("type", "vendor_init"), ("roletype", "object_r", "vendor_init"),
        ("typeattributeset", "domain", ("vendor_init",)),
        ("type", "property_socket"), ("roletype", "object_r", "property_socket"),
        ("typeattribute", "system_restricted_property_type"),
    ])
    version = CAMERA + "_202504"
    fixture["corpus"][FACTORY] = fixture["corpus"][FACTORY].replace(
        cil([("roletype", "object_r", CAMERA)]), cil([("roletype", "object_r", version)]))
    fixture["corpus"][FACTORY] += cil([
        ("typeattribute", version),
        *(("typeattributeset", attribute, (version,)) for attribute in
          ("property_type", "system_property_type", "system_restricted_property_type")),
        ("typeattribute", "base_typeattr_232_202504"),
        ("typeattributeset", "base_typeattr_232_202504", ("and", ("domain",), ("not", ("coredomain",)))),
        ("neverallow", "base_typeattr_232_202504", version, ("property_service", ("set",))),
    ])
    source = [
        ("allow", "vendor_init", "property_socket", ("sock_file", ("write",))),
        ("allow", "vendor_init", "init", ("unix_stream_socket", ("connectto",))),
        ("allow", "vendor_init", CAMERA, ("file", ("getattr", "open", "read", "map"))),
        ("typeattribute", "base_typeattr_51"),
        ("typeattributeset", "base_typeattr_51", ("and", ("domain",), ("not", ("init", "vendor_init")))),
        ("neverallow", "base_typeattr_51", CAMERA, ("property_service", ("set",))),
    ]
    fixture["base"]["system_ext_cil"] += cil(source)
    fixture["corpus"][eb.EXT] += cil([rename(expr, "base_typeattr_51", "base_typeattr_1051") for expr in source])
    rebind_fixture_inputs(fixture)
    return fixture


def change_camera_source(fixture, before, after):
    """Apply an adversarial change to both independent synthetic producers."""
    for container, key in ((fixture["base"], "system_ext_cil"), (fixture["corpus"], eb.EXT)):
        old, new = before, after
        if key == eb.EXT:
            old = old.replace(b"base_typeattr_51", b"base_typeattr_1051")
            new = new.replace(b"base_typeattr_51", b"base_typeattr_1051")
        if old:
            if old not in container[key]:
                raise AssertionError("synthetic camera source mutation target is absent")
            container[key] = container[key].replace(old, new)
        else:
            container[key] += new


class ContractAndSourceTests(unittest.TestCase):
    def test_contract_is_pinned_even_when_copied(self):
        contract = eb.load_contract()
        self.assertEqual(contract["build_variant"], "user")
        self.assertEqual(len(eb.source_rows(contract)), 46)
        self.assertEqual(len({row["path"] for row in eb.source_rows(contract)}), 46)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / "contract.json"
            raw = (ROOT / eb.CONTRACT_PATH).read_bytes()
            target.write_bytes(raw)
            self.assertEqual(eb.load_contract(target), contract)
            target.write_bytes(raw + b"\n")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                eb.load_contract(target)

    def make_sources(self, root):
        contract = copy.deepcopy(eb.load_contract())
        paths = []
        for index, row in enumerate(eb.source_rows(contract)):
            path = root / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = f"synthetic source {index}\n".encode()
            path.write_bytes(raw)
            row.update(sha256=vp.sha(raw), size_bytes=len(raw))
            paths.append(path)
        return contract, paths

    def test_exact_ordered_source_list_is_rehashed_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            contract, paths = self.make_sources(Path(directory).resolve())
            before = [path.read_bytes() for path in paths]
            result = eb.verify_source_files(paths, contract)
            self.assertEqual([row["selected_path"] for row in result], list(map(str, paths)))
            self.assertEqual(before, [path.read_bytes() for path in paths])

    def test_missing_extra_duplicate_reordered_and_wrong_selector_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            contract, paths = self.make_sources(Path(directory).resolve())
            changes = {
                "missing": paths[:-1], "extra": paths + paths[:1],
                "duplicate": [paths[1], *paths[1:]],
                "reordered": [paths[1], paths[0], *paths[2:]],
                "selector": [paths[0].with_name("unreviewed.te"), *paths[1:]],
            }
            for kind, changed in changes.items():
                with self.subTest(kind=kind), self.assertRaises(eb.EvolutionBaseError):
                    eb.verify_source_files(changed, contract)

    def test_source_hash_size_and_multiple_roots_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contract, paths = self.make_sources(root / "one")
            _, other = self.make_sources(root / "two")
            with self.assertRaisesRegex(eb.EvolutionBaseError, "multiple source roots"):
                eb.verify_source_files([other[0], *paths[1:]], contract)
            changed = copy.deepcopy(contract)
            eb.source_rows(changed)[0]["size_bytes"] += 1
            with self.assertRaisesRegex(eb.EvolutionBaseError, "size"):
                eb.verify_source_files(paths, changed)
            paths[0].write_bytes(paths[0].read_bytes() + b"changed\n")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                eb.verify_source_files(paths, contract)

    def test_source_symlink_and_readback_mutation_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            contract, paths = self.make_sources(Path(directory).resolve())
            first = paths[0]
            original = first.read_bytes()
            backing = first.with_name("saved-source")
            backing.write_bytes(original)
            first.unlink()
            first.symlink_to(backing.name)
            with self.assertRaisesRegex(vp.VendorPolicyError, "regular file"):
                eb.verify_source_files(paths, contract)
            first.unlink()
            first.write_bytes(original)

            class MutatingReader(vp.Reader):
                def recheck(self):
                    first.write_bytes(original + b"drift\n")
                    super().recheck()

            with self.assertRaises(vp.VendorPolicyError):
                eb.verify_source_files(paths, contract, MutatingReader())

    def test_legacy_default_is_still_narrow_and_has_no_base_admission(self):
        fixture = legacy_fixture()
        with patch.object(op, "_evolution_base_module", side_effect=AssertionError("optional helper was imported")):
            result = op.check_native_contents(*fixture)
        self.assertEqual(len(result["type_ownership"]), 3)
        self.assertFalse(any(key.startswith("evolution_") for key in result))
        fixture[0][eb.EXT] += b"(type unexpected_evolution_type)\n"
        with self.assertRaises(op.OemPolicyError):
            op.check_native_contents(*fixture)


class ExplicitSelectionTests(unittest.TestCase):
    def test_pure_oem_check_rejects_every_partial_base_selection(self):
        options = {"evolution_base_contract": eb.load_contract(),
                   "evolution_base_inputs": {}, "system_ext_public_cil": b"\n"}
        names = list(options)
        for mask in range(1, 2**len(names) - 1):
            selected = {name: options[name] for index, name in enumerate(names) if mask & (1 << index)}
            with self.subTest(selected=list(selected)), self.assertRaisesRegex(op.OemPolicyError, "selected together"):
                op.check_native_contents(*legacy_fixture(), **selected)

    def test_file_oem_check_requires_all_base_provenance_inputs_together(self):
        options = {"evolution_base_contract_path": ROOT / eb.CONTRACT_PATH,
                   "evolution_base_inputs": {}, "system_ext_public_cil_path": Path("absent-exporter"),
                   "evolution_base_source_files": []}
        names = list(options)
        for mask in range(1, 2**len(names) - 1):
            selected = {name: options[name] for index, name in enumerate(names) if mask & (1 << index)}
            with self.subTest(selected=list(selected)), self.assertRaisesRegex(op.OemPolicyError, "selected together"):
                op.check_native({}, Path("absent-vendor"), Path("absent-capability"), **selected)

    def test_base_cannot_implicitly_enable_property_or_provider_profiles(self):
        options = {"evolution_base_contract": eb.load_contract(),
                   "evolution_base_inputs": {}, "system_ext_public_cil": b"\n"}
        with self.assertRaisesRegex(op.OemPolicyError, "explicit property and provider"):
            op.check_native_contents(*legacy_fixture(), **options)

    def test_base_must_bind_exact_owned_contracts_device_and_user_variant(self):
        changes = (
            lambda contract: contract.update(build_variant="userdebug"),
            lambda contract: contract["device"].update(codename="other_device"),
            lambda contract: contract["platform"].update(branch="different_branch"),
            lambda contract: contract["required_contracts"]["oem_policy"].update(sha256="0" * 64),
        )
        for change in changes:
            contract = copy.deepcopy(eb.load_contract())
            change(contract)
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "does not bind"):
                op.check_native_contents(
                    *legacy_fixture(), evolution_base_contract=contract, evolution_base_inputs={},
                    system_ext_public_cil=b"\n",
                    property_contract=op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH),
                    provider_contract=fp.load_contract())


class CameraCapabilityTests(unittest.TestCase):
    def test_optional_contract_is_pinned_and_cannot_be_rewritten_after_load(self):
        contract = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
        before = copy.deepcopy(contract)
        eb.validate_camera_contract(contract)
        self.assertEqual(contract, before)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "camera.json"
            raw = (ROOT / eb.CAMERA_CONTRACT_PATH).read_bytes()
            path.write_bytes(raw)
            self.assertEqual(eb.load_camera_contract(path), contract)
            path.write_bytes(raw + b"\n")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                eb.load_camera_contract(path)
        for change in (
                lambda value: value["selected_profile"].update(capability_value="true"),
                lambda value: value["files"][0].update(after_sha256="0" * 64),
                lambda value: value["factory_assertion"].update(expression="(neverallow init self (file (read)))")):
            changed = copy.deepcopy(contract)
            change(changed)
            with self.subTest(change=change), self.assertRaisesRegex(eb.EvolutionBaseError, "exact reviewed contract"):
                eb.validate_camera_contract(changed)

    def test_optional_source_identity_changes_only_one_row_without_mutation(self):
        contract = eb.load_contract()
        before = copy.deepcopy(contract)
        camera = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
        rows = eb.source_rows(contract, camera)
        original = eb.source_rows(contract)
        self.assertEqual(contract, before)
        self.assertEqual(len(rows), 46)
        changed = [(old, new) for old, new in zip(original, rows) if old != new]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0][0]["path"], "device/lineage/sepolicy/common/public/property.te")
        self.assertEqual(changed[0][1]["sha256"], camera["files"][0]["after_sha256"])
        self.assertEqual(changed[0][1]["size_bytes"], 925)
        self.assertEqual(vp.sha((ROOT / eb.CONTRACT_PATH).read_bytes()), eb.CONTRACT_SHA256)

    def test_optional_source_cannot_rebind_wrong_profile_or_preimage(self):
        camera = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
        changes = (
            lambda value: value["device"].update(codename="other"),
            lambda value: value["platform"].update(branch="newer"),
            lambda value: value.update(build_variant="userdebug"),
            lambda value: value["upstream"].update(commit="0" * 40),
            lambda value: value["base_policy_sources"]["system_ext_public"][3].update(sha256="0" * 64),
            lambda value: value["base_policy_sources"]["system_ext_public"].pop(3),
            lambda value: value["base_policy_sources"]["system_ext_public"].append(
                copy.deepcopy(value["base_policy_sources"]["system_ext_public"][3])),
        )
        for change in changes:
            contract = copy.deepcopy(eb.load_contract())
            change(contract)
            with self.subTest(change=change), self.assertRaises(eb.EvolutionBaseError):
                eb.source_rows(contract, camera)

    def test_source_check_requires_actual_patched_bytes_only_when_selected(self):
        camera = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
        patch_lines = (ROOT / camera["patch"]).read_text().splitlines(keepends=True)
        hunk = patch_lines[next(i for i, line in enumerate(patch_lines) if line.startswith("@@")) + 1:]
        patched = "".join(line[1:] for line in hunk if line.startswith((" ", "+"))).encode()
        original = """# Aux camera allow/excludelist prop
system_vendor_config_prop(vendor_persist_camera_prop)

# NFC
system_vendor_config_prop(vendor_persist_nfc_prop)

# USB
system_vendor_config_prop(usb_uvc_config_prop)

# xtra-daemon control
system_restricted_prop(xtra_control_prop)
""".encode()
        with tempfile.TemporaryDirectory() as directory:
            contract = copy.deepcopy(eb.load_contract())
            root, paths, selected = Path(directory).resolve(), [], None
            for index, row in enumerate(eb.source_rows(contract)):
                path = root / row["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                if row["path"].endswith("common/public/property.te"):
                    raw, selected = patched, path
                else:
                    raw = f"synthetic source {index}\n".encode()
                    row.update(sha256=vp.sha(raw), size_bytes=len(raw))
                path.write_bytes(raw)
                paths.append(path)
            result = eb.verify_source_files(paths, contract, camera_contract=camera)
            self.assertEqual(result[3]["sha256"], camera["files"][0]["after_sha256"])
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                eb.verify_source_files(paths, contract)
            selected.write_bytes(original)
            eb.verify_source_files(paths, contract)
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                eb.verify_source_files(paths, contract, camera_contract=camera)

    def test_camera_capability_cannot_enable_an_implicit_base(self):
        camera = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
        with self.assertRaisesRegex(op.OemPolicyError, "complete explicit Evolution"):
            op.check_native_contents(*legacy_fixture(), camera_property_contract=camera)
        with self.assertRaisesRegex(op.OemPolicyError, "complete explicit Evolution"):
            op.check_native({}, Path("absent-vendor"), Path("absent-helper"),
                            camera_property_contract_path=ROOT / eb.CAMERA_CONTRACT_PATH)

    def test_native_cli_passes_only_explicit_camera_selection(self):
        arguments = ["check-native", "--contract", "oem", "--capability-contract", "helper",
                     "--factory-vendor", "vendor"]
        for flag in op.INPUT_FLAGS:
            arguments.extend(["--" + flag.replace("_", "-"), flag])
        for selected in (False, True):
            command = arguments + (["--camera-property-capability-contract", "camera"] if selected else [])
            with self.subTest(selected=selected), patch.object(op, "check_native", return_value={}) as check, \
                    patch.object(op, "_write_result"):
                self.assertEqual(op.main(command), 0)
            self.assertEqual(check.call_args.kwargs["camera_property_contract_path"],
                             Path("camera") if selected else None)

    def test_optional_native_scope_is_verified_without_weakening_either_assertion(self):
        fixture = camera_composition_fixture()
        before = copy.deepcopy(fixture)
        result = check_fixture(fixture)["result"]
        self.assertEqual(fixture, before)
        report = result["camera_property_capability_verification"]
        self.assertEqual(report["capability_value"], "false")
        self.assertEqual(report["contract_sha256"], eb.CAMERA_CONTRACT_SHA256)
        self.assertFalse(report["binary_or_image_or_runtime_admitted"])
        self.assertFalse(report["source_or_generated_cil_modified_by_check"])
        self.assertEqual(set(report["native_policies"]), {"actual", "comparison"})
        for scope in report["native_policies"].values():
            self.assertEqual(scope["effective_vendor_init_property_set_grants"], 0)
            self.assertEqual(scope["source_assertions"], 1)
            self.assertEqual(scope["factory_assertions"], 1)
            self.assertTrue(scope["effective_socket_and_read_permissions_retained"])
            self.assertTrue(scope["source_public_and_factory_restricted_attributes_retained"])
        legacy = check_fixture(composition_fixture())["result"]
        self.assertNotIn("camera_property_capability_verification", legacy)

    def test_direct_attribute_alias_and_immutable_input_write_edges_all_fail(self):
        for variant in ("direct", "attribute", "alias", "immutable"):
            fixture = camera_composition_fixture()
            source, target = "vendor_init", CAMERA
            if variant == "attribute":
                fixture["corpus"][PLATFORM] += cil([
                    ("typeattribute", "test_camera_writers"),
                    ("typeattributeset", "test_camera_writers", ("vendor_init",)),
                    ("typeattribute", "test_camera_targets"),
                    ("typeattributeset", "test_camera_targets", (CAMERA,)),
                ])
                source, target = "test_camera_writers", "test_camera_targets"
            elif variant == "alias":
                fixture["corpus"][PLATFORM] += cil([
                    ("typealias", "test_camera_writer"), ("typealiasactual", "test_camera_writer", "vendor_init"),
                    ("typealias", "test_camera_target"), ("typealiasactual", "test_camera_target", CAMERA),
                ])
                source, target = "test_camera_writer", "test_camera_target"
            rule = cil([("allow", source, target, ("property_service", ("set",)))])
            if variant == "immutable":
                fixture["corpus"][PLATFORM] += rule
            else:
                change_camera_source(fixture, b"", rule)
            rebind_fixture_inputs(fixture)
            with self.subTest(variant=variant), self.assertRaisesRegex(eb.EvolutionBaseError, "property-write capability"):
                check_fixture(fixture)

    def test_renamed_anonymous_reference_membership_is_not_a_property_reclassification(self):
        fixture = camera_composition_fixture()
        change_camera_source(fixture, b"", cil([
            ("typeattribute", "base_typeattr_52"),
            ("typeattributeset", "base_typeattr_52", ("not", ("domain",))),
        ]))
        result = check_fixture(fixture)["result"]["camera_property_capability_verification"]
        self.assertEqual(result["status"], "verified")

    def test_source_assertion_cannot_be_removed_duplicated_or_weakened(self):
        assertion = cil([("neverallow", "base_typeattr_51", CAMERA, ("property_service", ("set",)))])
        for mutation in ("removed", "duplicated", "weakened"):
            fixture = camera_composition_fixture()
            if mutation == "weakened":
                change_camera_source(fixture, b"(not (init vendor_init))", b"(not (init vendor_init shell))")
            else:
                change_camera_source(fixture, assertion, b"" if mutation == "removed" else assertion * 2)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(eb.EvolutionBaseError, "source assertion"):
                check_fixture(fixture)

    def test_factory_assertion_and_definition_cannot_change(self):
        for mutation in ("removed", "duplicated", "definition"):
            fixture = camera_composition_fixture()
            factory = fixture["camera_contract"]["factory_assertion"]
            assertion = factory["expression"].encode() + b"\n"
            if mutation == "definition":
                fixture["corpus"][FACTORY] = fixture["corpus"][FACTORY].replace(
                    b"(not (coredomain))", b"(not (coredomain vendor_init))")
            else:
                fixture["corpus"][FACTORY] = fixture["corpus"][FACTORY].replace(
                    assertion, b"" if mutation == "removed" else assertion * 2)
            rebind_fixture_inputs(fixture)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(eb.EvolutionBaseError, "factory assertion"):
                check_fixture(fixture)

    def test_vendor_init_reclassification_cannot_make_factory_assertion_vacuous(self):
        fixture = camera_composition_fixture()
        fixture["corpus"][PLATFORM] += b"(typeattributeset coredomain (vendor_init))\n"
        rebind_fixture_inputs(fixture)
        with self.assertRaisesRegex(eb.EvolutionBaseError, "outside coredomain"):
            check_fixture(fixture)

    def test_preserved_read_and_socket_permissions_cannot_be_removed(self):
        for target, cls, permissions in (("property_socket", "sock_file", ("write",)),
                                         ("init", "unix_stream_socket", ("connectto",)),
                                         (CAMERA, "file", ("getattr", "open", "read", "map"))):
            fixture = camera_composition_fixture()
            statement = cil([("allow", "vendor_init", target, (cls, permissions))])
            change_camera_source(fixture, statement, b"")
            with self.subTest(cls=cls), self.assertRaisesRegex(eb.EvolutionBaseError, "socket or read"):
                check_fixture(fixture)

    def test_platform_filtered_socket_permissions_remain_effective(self):
        fixture = camera_composition_fixture()
        for target, cls, permission in (("property_socket", "sock_file", "write"),
                                        ("init", "unix_stream_socket", "connectto")):
            rule = cil([("allow", "vendor_init", target, (cls, (permission,)))])
            change_camera_source(fixture, rule, b"")
            fixture["corpus"][PLATFORM] += rule
        rebind_fixture_inputs(fixture)
        report = check_fixture(fixture)["result"]["camera_property_capability_verification"]
        for scope in report["native_policies"].values():
            self.assertTrue(scope["effective_socket_and_read_permissions_retained"])

    def test_self_rule_does_not_grant_vendor_init_a_connection_to_init(self):
        fixture = camera_composition_fixture()
        change_camera_source(fixture,
            cil([("allow", "vendor_init", "init", ("unix_stream_socket", ("connectto",)))]),
            cil([("allow", "domain", "self", ("unix_stream_socket", ("connectto",)))]))
        with self.assertRaisesRegex(eb.EvolutionBaseError, "socket or read"):
            check_fixture(fixture)

    def test_source_and_factory_classification_must_both_survive(self):
        for origin in ("source", "factory"):
            fixture = camera_composition_fixture()
            if origin == "source":
                for group, key in ((fixture["base"], "system_ext_cil"), (fixture["corpus"], eb.EXT)):
                    expressions = []
                    for form in vp.parse(group[key]):
                        expr = form.expr
                        if expr[:2] == ("typeattributeset", "system_public_property_type"):
                            members = tuple(member for member in expr[2] if member != CAMERA)
                            if members:
                                expressions.append((*expr[:2], members))
                        else:
                            expressions.append(expr)
                    expressions.append(("typeattributeset", "system_restricted_property_type", (CAMERA,)))
                    group[key] = cil(expressions)
            else:
                fixture["corpus"][FACTORY] = fixture["corpus"][FACTORY].replace(
                    b"system_restricted_property_type (vendor_persist_camera_prop_202504)",
                    b"system_public_property_type (vendor_persist_camera_prop_202504)")
                rebind_fixture_inputs(fixture)
            with self.subTest(origin=origin), self.assertRaisesRegex(eb.EvolutionBaseError, "property attributes"):
                check_fixture(fixture)

    def test_camera_public_export_and_exact_mapping_cannot_be_omitted_or_duplicated(self):
        for mutation in ("public_missing", "public_duplicate", "mapping_expansion", "mapping_duplicate"):
            fixture = camera_composition_fixture()
            if mutation.startswith("public"):
                before = cil([("type", CAMERA)])
                after = b"" if mutation == "public_missing" else before * 2
                fixture["base"]["public_cil"] = fixture["base"]["public_cil"].replace(before, after)
                fixture["full_public"] = fixture["full_public"].replace(before, after)
            else:
                before = cil([("expandtypeattribute", (CAMERA + "_202504",), "true")])
                after = b"" if mutation == "mapping_expansion" else before * 2
                for group, key in ((fixture["base"], "system_ext_mapping"), (fixture["corpus"], eb.MAPPING)):
                    group[key] = group[key].replace(before, after)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(eb.EvolutionBaseError, "camera public"):
                check_fixture(fixture)


class FactoryContextCapabilityTests(unittest.TestCase):
    def fixture(self):
        contract = eb.load_factory_contexts_contract(ROOT / eb.FACTORY_CONTEXTS_CONTRACT_PATH)
        properties = op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH)
        base = context_bytes(contract["selected_base_semantic_rows"])
        full = base + context_bytes([
            tuple(row[key] for key in ("property_pattern", "context", "match", "value_type"))
            for row in properties["property_contexts"]])
        inputs = {
            "platform": b"test.enum u:object_r:default_prop:s0 exact enum enabled disabled\n",
            "product": b"test.product u:object_r:default_prop:s0 exact bool\n",
            "vendor": (b"vendor.camera. u:object_r:vendor_camera_prop:s0\n"
                       b"ro.vendor.audio. u:object_r:vendor_audio_prop:s0\n"
                       b"vendor.usb. u:object_r:vendor_usb_prop:s0\n"),
            "odm": b"test.odm u:object_r:vendor_default_prop:s0 prefix string\n",
        }
        fixture = {"base_raw": base, "full_raw": full, "inputs": inputs,
                   "contract": copy.deepcopy(contract), "property_contract": properties}
        self.rebind_synthetic_inputs(fixture)
        return fixture

    def rebind_synthetic_inputs(self, fixture):
        # Test only the pure semantic engine with synthetic context inputs.
        # Production check_factory_contexts first pins the complete contract.
        for row in fixture["contract"]["preimage_context_closure"]["five_complete_context_inputs"]:
            role = next(role for role, runtime in eb.PROPERTY_CONTEXT_RUNTIMES.items()
                        if runtime == row["runtime_path"])
            if role != "system_ext":
                raw = fixture["inputs"][role]
                row.update(sha256=vp.sha(raw), size_bytes=len(raw))

    def check(self, fixture):
        return eb._check_factory_contexts_contents(**fixture)

    def test_contract_copies_are_pinned_and_in_memory_changes_are_rejected(self):
        path = ROOT / eb.FACTORY_CONTEXTS_CONTRACT_PATH
        contract = eb.load_factory_contexts_contract(path)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / "contexts.json"
            target.write_bytes(path.read_bytes())
            self.assertEqual(eb.load_factory_contexts_contract(target), contract)
            target.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                eb.load_factory_contexts_contract(target)
        contract["selected_profile"]["capability_value"] = "false"
        with self.assertRaisesRegex(eb.EvolutionBaseError, "exact reviewed contract"):
            eb.validate_factory_contexts_contract(contract)
        fixture = self.fixture()
        with self.assertRaisesRegex(eb.EvolutionBaseError, "exact reviewed contract"):
            eb.check_factory_contexts(**fixture)

    def test_source_overlay_preserves_0016_and_changes_only_the_context_identity(self):
        base = eb.load_contract()
        before = copy.deepcopy(base)
        camera = eb.load_camera_contract(ROOT / eb.CAMERA_CONTRACT_PATH)
        contexts = eb.load_factory_contexts_contract(ROOT / eb.FACTORY_CONTEXTS_CONTRACT_PATH)
        prior = eb.source_rows(base, camera)
        result = eb.source_rows(base, camera, contexts)
        self.assertEqual(base, before)
        changed = [(old, new) for old, new in zip(prior, result) if old != new]
        self.assertEqual(len(result), 46)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0][0]["path"], "device/lineage/sepolicy/common/private/property_contexts")
        self.assertEqual(changed[0][1]["sha256"], contexts["files"][0]["after_sha256"])
        self.assertEqual(changed[0][1]["size_bytes"], 3423)
        self.assertEqual(eb.source_rows(base, camera), prior)
        with self.assertRaisesRegex(eb.EvolutionBaseError, "explicit camera"):
            eb.source_rows(base, factory_contexts_contract=contexts)
        base["base_context_sources"]["property_contexts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(eb.EvolutionBaseError, "source preimage"):
            eb.source_rows(base, camera, contexts)

    def test_optional_contexts_require_all_inputs_and_explicit_camera(self):
        contexts = eb.load_factory_contexts_contract(ROOT / eb.FACTORY_CONTEXTS_CONTRACT_PATH)
        for contract, inputs in ((contexts, None), (None, {})):
            with self.subTest(contract=contract is not None), self.assertRaisesRegex(op.OemPolicyError, "selected together"):
                op.check_native_contents(*legacy_fixture(), factory_contexts_contract=contract,
                                         factory_property_contexts=inputs)
        with self.assertRaisesRegex(op.OemPolicyError, "explicit camera"):
            op.check_native_contents(*legacy_fixture(), factory_contexts_contract=contexts,
                                     factory_property_contexts={})
        with self.assertRaisesRegex(op.OemPolicyError, "explicit camera"):
            op.check_native({}, Path("absent-vendor"), Path("absent-helper"),
                            factory_contexts_contract_path=ROOT / eb.FACTORY_CONTEXTS_CONTRACT_PATH,
                            factory_property_context_paths={})
        for missing in eb.FACTORY_CONTEXT_FLAGS.values():
            fixture = self.fixture()
            del fixture["inputs"][missing]
            with self.subTest(missing=missing), self.assertRaisesRegex(eb.EvolutionBaseError, "all four"):
                self.check(fixture)

    def test_cli_forwards_all_four_context_inputs_and_explicit_contract(self):
        arguments = ["check-native", "--contract", "oem", "--capability-contract", "helper",
                     "--factory-vendor", "vendor", "--factory-property-contexts-capability-contract", "contexts"]
        for flag in op.INPUT_FLAGS:
            arguments.extend(["--" + flag.replace("_", "-"), flag])
        for flag in eb.FACTORY_CONTEXT_FLAGS:
            arguments.extend(["--" + flag.replace("_", "-"), flag])
        with patch.object(op, "check_native", return_value={}) as check, patch.object(op, "_write_result"):
            self.assertEqual(op.main(arguments), 0)
        self.assertEqual(check.call_args.kwargs["factory_contexts_contract_path"], Path("contexts"))
        self.assertEqual(check.call_args.kwargs["factory_property_context_paths"],
                         {flag: Path(flag) for flag in eb.FACTORY_CONTEXT_FLAGS})

    def test_exact_twenty_five_base_and_eight_owned_rows_preserve_all_seven_regions(self):
        fixture = self.fixture()
        before = copy.deepcopy(fixture)
        report = self.check(fixture)
        self.assertEqual(fixture, before)
        self.assertEqual(report["capability_value"], "true")
        self.assertEqual(report["native_contexts"]["comparison"]["source_rows"], 25)
        self.assertEqual(report["native_contexts"]["actual"]["source_rows"], 33)
        self.assertEqual(len(report["unchanged_complete_context_inputs"]), 4)
        self.assertTrue(report["all_other_twenty_five_base_and_eight_owned_rows_retained"])
        for scope in report["native_contexts"].values():
            self.assertEqual(len(scope["seven_prefix_regions"]), 7)
            self.assertTrue(all(row["whole_prefix_language_verified"] for row in scope["seven_prefix_regions"]))
            self.assertTrue(all(row["effective_value_type"] == "string" for row in scope["seven_prefix_regions"]))
        self.assertFalse(report["permission_or_image_or_runtime_admitted"])
        self.assertFalse(report["source_or_generated_contexts_modified_by_check"])

    def test_non_system_ext_inputs_cannot_drift(self):
        for role in eb.FACTORY_CONTEXT_FLAGS.values():
            fixture = self.fixture()
            fixture["inputs"][role] += b"# drift\n"
            with self.subTest(role=role), self.assertRaisesRegex(eb.EvolutionBaseError, "reviewed anchor"):
                self.check(fixture)

    def test_remaining_rows_and_owned_rows_cannot_change(self):
        for key, mutation in (("base_raw", "missing"), ("full_raw", "missing"),
                              ("base_raw", "duplicate"), ("full_raw", "label"),
                              ("base_raw", "suppressed")):
            fixture = self.fixture()
            rows = fixture[key].splitlines(keepends=True)
            if mutation == "missing":
                rows.pop()
            elif mutation == "duplicate":
                rows.append(rows[0])
            elif mutation == "label":
                rows[0] = rows[0].replace(b"odm_cast_prop", b"other_prop")
            else:
                rows.append(fixture["contract"]["suppressed_rows"][0]["raw_line"].encode())
            fixture[key] = b"".join(rows)
            with self.subTest(key=key, mutation=mutation), self.assertRaisesRegex(eb.EvolutionBaseError, "retained base plus owned"):
                self.check(fixture)

    def test_equal_and_deeper_exact_and_prefix_rules_are_rejected_for_entire_regions(self):
        for role in eb.FACTORY_CONTEXT_FLAGS.values():
            for suffix, match in (("", "exact"), (".child", "exact"), ("suffix", "prefix")):
                fixture = self.fixture()
                prefix = fixture["contract"]["suppressed_rows"][0]["selector"]
                fixture["inputs"][role] += f"{prefix}{suffix} u:object_r:vendor_camera_prop:s0 {match} string\n".encode()
                self.rebind_synthetic_inputs(fixture)
                with self.subTest(role=role, suffix=suffix, match=match), \
                        self.assertRaisesRegex(eb.EvolutionBaseError, "equal or deeper"):
                    self.check(fixture)

    def test_longer_ancestor_cannot_relabel_the_removed_prefix_region(self):
        fixture = self.fixture()
        fixture["inputs"]["platform"] += b"vendor.camera.aux. u:object_r:other_prop:s0 prefix\n"
        self.rebind_synthetic_inputs(fixture)
        with self.assertRaisesRegex(eb.EvolutionBaseError, "exact factory fallback"):
            self.check(fixture)

    def test_untyped_factory_fallback_cannot_hide_an_inherited_non_string_type(self):
        for value_type in ("bool", "enum enabled disabled"):
            fixture = self.fixture()
            fixture["inputs"]["platform"] += f"vendor. u:object_r:vendor_default_prop:s0 prefix {value_type}\n".encode()
            self.rebind_synthetic_inputs(fixture)
            with self.subTest(value_type=value_type), self.assertRaisesRegex(eb.EvolutionBaseError, "string value type"):
                self.check(fixture)
        fixture = self.fixture()
        fixture["inputs"]["platform"] += b"vendor. u:object_r:vendor_default_prop:s0 prefix string\n"
        self.rebind_synthetic_inputs(fixture)
        self.assertEqual(self.check(fixture)["status"], "verified")

    def test_missing_factory_fallback_and_cross_scope_duplicate_are_rejected(self):
        for mutation in ("missing", "duplicate"):
            fixture = self.fixture()
            row = b"vendor.camera. u:object_r:vendor_camera_prop:s0\n"
            if mutation == "missing":
                fixture["inputs"]["vendor"] = fixture["inputs"]["vendor"].replace(row, b"")
            else:
                fixture["inputs"]["product"] += row
            self.rebind_synthetic_inputs(fixture)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(eb.EvolutionBaseError, "fallback|duplicate"):
                self.check(fixture)

    def test_complete_parser_accepts_native_enum_and_rejects_invalid_or_ambiguous_syntax(self):
        rows = eb._complete_property_rows(
            b"old u:object_r:default_prop:s0\nchoice u:object_r:default_prop:s0 exact enum enabled disabled\n", "test")
        self.assertEqual(rows[0]["match_kind"], "prefix")
        self.assertIsNone(rows[0]["value_type"])
        self.assertEqual(rows[1]["value_type"], "enum enabled disabled")
        self.assertEqual(eb._complete_property_rows(
            b"ctl.vendor.port-bridge u:object_r:vendor_ctl_port-bridge_prop:s0\n", "test")[0]["context"],
            "u:object_r:vendor_ctl_port-bridge_prop:s0")
        for row in (b"x u:object_r:default_prop:s0 unknown\n", b"x u:object_r:default_prop:s0 exact enum\n",
                    b"x u:object_r:default_prop:s0 exact bool extra\n", b"x u:object_r:default_prop:s0 # inline\n",
                    b"x\x00 u:object_r:default_prop:s0\n"):
            with self.subTest(row=row), self.assertRaises(eb.EvolutionBaseError):
                eb._complete_property_rows(row, "test")


class CompositionTests(unittest.TestCase):
    def test_distinct_base_plus_owned_composition_passes_with_limits(self):
        fixture = composition_fixture()
        before = copy.deepcopy(fixture)
        result = check_fixture(fixture)
        self.assertEqual(fixture, before)
        self.assertEqual(result["base_types"], BASE_TYPES)
        report = result["result"]
        self.assertEqual(report["immutable_original_assertions"], 2)
        self.assertEqual(report["owned_provider_assertions"], 4)
        self.assertEqual(report["base_assertions"], 1)
        self.assertEqual(report["owned_type_count"], 15)
        self.assertEqual(report["base_factory_duplicate_types"], [CAMERA])
        self.assertFalse(report["binary_zero_permissive_check_performed"])
        self.assertFalse(report["vendor_source_delivery_into_factory_images_proven"])
        self.assertFalse(report["image_or_runtime_admitted"])
        self.assertTrue(report["native_recipe_and_source_action_provenance_requires_separate_evidence"])
        self.assertIn(APP, result["membership_budget"]["domain"])
        self.assertIn("vendor_sigmahal_qti", result["membership_budget"]["domain"])

    def test_reference_inputs_cannot_be_missing_or_extra(self):
        for change in ("missing", "extra"):
            fixture = composition_fixture()
            if change == "missing":
                del fixture["base"]["public_cil"]
            else:
                fixture["base"]["unreviewed"] = b"\n"
            with self.subTest(change=change), self.assertRaisesRegex(eb.EvolutionBaseError, "reference input"):
                check_fixture(fixture)

    def test_immutable_policy_and_assertions_cannot_be_replaced_or_removed(self):
        for change in ("append", "neverallow", "neverallowx"):
            fixture = composition_fixture()
            if change == "append":
                fixture["corpus"][PLATFORM] += b"(allow init self (capability (sys_admin)))\n"
            else:
                forms = vp.parse(fixture["corpus"][PLATFORM])
                fixture["corpus"][PLATFORM] = cil([f.expr for f in forms if f.expr[0] != change])
            with self.subTest(change=change), self.assertRaisesRegex(eb.EvolutionBaseError, "assertion anchor"):
                check_fixture(fixture)

    def test_each_immutable_assertion_counter_is_checked_even_with_same_bytes(self):
        for field in ("neverallow", "neverallowx"):
            fixture = composition_fixture()
            next(row for row in fixture["contract"]["unchanged_cil_inputs"]
                 if row["runtime_path"] == PLATFORM)[field] += 1
            with self.subTest(field=field), self.assertRaisesRegex(eb.EvolutionBaseError, "assertion count"):
                check_fixture(fixture)

    def test_new_partition_cannot_hide_a_rule_outside_the_source_budget(self):
        fixture = composition_fixture()
        fixture["corpus"]["/unreviewed/policy.cil"] = b"(allow init self (capability (sys_admin)))\n"
        with self.assertRaisesRegex(eb.EvolutionBaseError, "input set"):
            check_fixture(fixture)

    def test_owned_type_cannot_leak_into_independent_base_cil_or_mapping(self):
        for kind, statement in (
            ("system_ext_cil", "(allow init vendor_sigmahal_qti (binder (call)))"),
            ("system_ext_mapping", "(typeattributeset vendor_persist_camera_prop_202504 (vendor_mm_parser_prop))"),
        ):
            fixture = composition_fixture()
            fixture["base"][kind] += statement.encode()
            with self.subTest(kind=kind), self.assertRaisesRegex(eb.EvolutionBaseError, "device-owned types"):
                check_fixture(fixture)

    def test_named_and_inherited_anonymous_closures_cannot_broaden(self):
        for name in ("evolution_test_scope", INHERITED, "domain"):
            fixture = composition_fixture()
            fixture["corpus"][eb.EXT] += f"(typeattributeset {name} (audioserver_service))\n".encode()
            with self.subTest(name=name), self.assertRaisesRegex(eb.EvolutionBaseError, "attribute closure"):
                check_fixture(fixture)

    def test_fresh_anonymous_closure_and_expansion_flag_cannot_change(self):
        for change in ("closure", "expansion", "duplicate"):
            fixture = composition_fixture()
            raw = fixture["corpus"][eb.EXT]
            if change == "closure":
                raw = raw.replace(b"(not (init shell))", b"(not (init))")
            elif change == "expansion":
                raw = raw.replace(f"(expandtypeattribute ({FULL_LOCAL}) false)".encode(),
                                  f"(expandtypeattribute ({FULL_LOCAL}) true)".encode())
            else:
                raw += f"(typeattribute {FULL_LOCAL})\n".encode()
            fixture["corpus"][eb.EXT] = raw
            with self.subTest(change=change), self.assertRaisesRegex(eb.EvolutionBaseError, "anonymous"):
                check_fixture(fixture)

    def test_inherited_anonymous_definition_counts_cannot_be_duplicated(self):
        for statement in (f"(typeattribute {INHERITED})", f"(typeattributeset {INHERITED} ({APP}))"):
            fixture = composition_fixture()
            fixture["corpus"][eb.EXT] += statement.encode()
            with self.subTest(statement=statement), self.assertRaisesRegex(eb.EvolutionBaseError, "attribute definition multiplicity"):
                check_fixture(fixture)

    def test_named_declaration_and_alias_namespace_cannot_be_extended(self):
        for statement in ("(typeattribute evolution_test_scope)",
                          f"(typealias unreviewed_alias)(typealiasactual unreviewed_alias {APP})"):
            fixture = composition_fixture()
            fixture["corpus"][eb.EXT] += statement.encode()
            with self.subTest(statement=statement), self.assertRaisesRegex(eb.EvolutionBaseError, "declarations|alias namespace"):
                check_fixture(fixture)

    def test_anonymous_numbering_and_permission_order_do_not_affect_composition(self):
        fixture = composition_fixture()
        fixture["corpus"][eb.EXT] = fixture["corpus"][eb.EXT].replace(
            FULL_LOCAL.encode(), b"base_typeattr_100050").replace(b"(getattr read)", b"(read getattr)")
        self.assertEqual(check_fixture(fixture)["result"]["status"], "verified")

    def test_added_allow_dontaudit_auditallow_and_assertion_fail(self):
        for head in ("allow", "dontaudit", "auditallow", "neverallow"):
            fixture = composition_fixture()
            fixture["corpus"][eb.EXT] += f"({head} {APP} {CAMERA} (file (write)))\n".encode()
            with self.subTest(head=head), self.assertRaisesRegex(eb.EvolutionBaseError, "access, audit, or assertion"):
                check_fixture(fixture)

    def test_changed_removed_and_duplicated_base_rule_fail(self):
        row = f"(allow {APP} {CAMERA} (file (getattr read)))".encode()
        for replacement in (b"", row + row, row.replace(b"read", b"write")):
            fixture = composition_fixture()
            self.assertIn(row, fixture["corpus"][eb.EXT])
            fixture["corpus"][eb.EXT] = fixture["corpus"][eb.EXT].replace(row, replacement)
            with self.subTest(replacement=replacement), self.assertRaisesRegex(eb.EvolutionBaseError, "access, audit, or assertion"):
                check_fixture(fixture)

    def test_provider_registration_assertion_cannot_be_removed(self):
        fixture = composition_fixture()
        forms = vp.parse(fixture["corpus"][eb.EXT])
        fixture["corpus"][eb.EXT] = cil([f.expr for f in forms
            if not (f.expr[0] == "neverallow" and f.expr[1] == "base_typeattr_9000")])
        with self.assertRaisesRegex(eb.EvolutionBaseError, "access, audit, or assertion"):
            check_fixture(fixture)

    def test_added_or_changed_transition_fails(self):
        for change in ("extra", "target"):
            fixture = composition_fixture()
            if change == "extra":
                fixture["corpus"][eb.EXT] += f"(typetransition shell {EXEC} process {APP})\n".encode()
            else:
                fixture["corpus"][eb.EXT] = fixture["corpus"][eb.EXT].replace(
                    f"(typetransition init {EXEC} process {APP})".encode(),
                    f"(typetransition init {EXEC} process shell)".encode())
            with self.subTest(change=change), self.assertRaisesRegex(eb.EvolutionBaseError, "transition"):
                check_fixture(fixture)

    def test_duplicate_source_type_role_and_named_assignment_fail(self):
        for statement in (f"(type {APP})", f"(roletype object_r {CAMERA})",
                          f"(typeattributeset evolution_test_scope ({APP}))"):
            fixture = composition_fixture()
            fixture["corpus"][eb.EXT] += statement.encode()
            with self.subTest(statement=statement), self.assertRaisesRegex(eb.EvolutionBaseError, "multiplicity|duplicated"):
                check_fixture(fixture)

    def test_public_mapping_membership_multiplicity_and_expansion_are_exact(self):
        version = CAMERA + "_202504"
        for statement in (f"(typeattribute {version})", f"(typeattributeset {version} ({CAMERA}))",
                          f"(expandtypeattribute ({version}) true)", f"(expandtypeattribute ({version}) false)"):
            fixture = composition_fixture()
            fixture["corpus"][eb.MAPPING] += statement.encode()
            with self.subTest(statement=statement), self.assertRaisesRegex(eb.EvolutionBaseError, "mapping|expansion"):
                check_fixture(fixture)

    def test_factory_duplicate_contract_cannot_silently_admit_more_types(self):
        fixture = composition_fixture()
        fixture["contract"]["base_factory_duplicate_types"] = {}
        with self.assertRaisesRegex(eb.EvolutionBaseError, "duplicate type set"):
            check_fixture(fixture)

    def test_permissive_normal_policy_fails_in_actual_and_reference(self):
        for side in ("actual", "reference"):
            fixture = composition_fixture()
            statement = f"(typepermissive {APP})\n".encode()
            if side == "actual":
                fixture["corpus"][eb.EXT] += statement
            else:
                fixture["base"]["system_ext_cil"] += statement
            with self.subTest(side=side), self.assertRaisesRegex(eb.EvolutionBaseError, "permissive|other forms"):
                check_fixture(fixture)

    def test_full_public_exporter_cannot_leak_private_or_duplicate_public_types(self):
        for name in ("offlinelog_file", "vendor_sigmahal_qti", CAMERA, "vendor_mm_parser_prop"):
            fixture = composition_fixture()
            fixture["full_public"] += f"(type {name})\n".encode()
            with self.subTest(name=name), self.assertRaisesRegex(eb.EvolutionBaseError, "public exporter"):
                check_fixture(fixture)

    def test_independent_public_exporter_cannot_contain_owned_types(self):
        fixture = composition_fixture()
        fixture["base"]["public_cil"] += b"(type vendor_mm_parser_prop)\n"
        with self.assertRaisesRegex(eb.EvolutionBaseError, "base public exporter"):
            check_fixture(fixture)


class ContextClosureTests(unittest.TestCase):
    def check(self, fixture):
        return eb.check_contexts(fixture["base"], fixture["full_contexts"],
                                 fixture["properties"], fixture["provider"])

    def test_exact_base_and_owned_contexts_preserve_untyped_prefixes(self):
        fixture = composition_fixture()
        result = self.check(fixture)
        self.assertEqual(result["property_contexts"]["full_rows"], 9)
        self.assertEqual(result["file_contexts"]["full_rows"], 5)
        self.assertEqual(result["service_contexts"]["full_rows"], 3)
        # Old two-column syntax and an explicit untyped prefix mean the same
        # thing; neither is silently upgraded to a typed string property.
        fixture["full_contexts"]["property_contexts"] = fixture["full_contexts"]["property_contexts"].replace(
            b" prefix\n", b"\n")
        self.assertEqual(self.check(fixture), result)

    def test_context_order_comments_and_whitespace_are_semantically_irrelevant(self):
        fixture = composition_fixture()
        before = self.check(fixture)
        for kind, raw in fixture["full_contexts"].items():
            fixture["full_contexts"][kind] = b"# comment\n" + b"\n".join(
                b"  " + row + b" # retained\n" for row in reversed(raw.splitlines()))
        self.assertEqual(self.check(fixture), before)

    def test_missing_extra_duplicate_and_relabelled_rows_fail_for_every_kind(self):
        for kind in ("property_contexts", "file_contexts", "service_contexts"):
            for change in ("missing", "extra", "duplicate", "label"):
                fixture = composition_fixture()
                rows = fixture["full_contexts"][kind].splitlines(keepends=True)
                if change == "missing":
                    rows = rows[1:]
                elif change == "extra":
                    rows.append(b"unexpected u:object_r:unreviewed:s0\n")
                elif change == "duplicate":
                    rows.append(rows[0])
                else:
                    rows[0] = rows[0].replace(b":s0", b"_changed:s0")
                fixture["full_contexts"][kind] = b"".join(rows)
                with self.subTest(kind=kind, change=change), self.assertRaisesRegex(eb.EvolutionBaseError, "context rows"):
                    self.check(fixture)

    def test_property_prefix_exactness_and_value_type_cannot_change(self):
        changes = ((b"exact bool", b"prefix bool"), (b"exact bool", b"exact string"),
                   (b":s0 prefix\n", b":s0 prefix string\n"),
                   (b"persist.vendor.dpm.", b"persist.vendor.dpm"))
        for before, after in changes:
            fixture = composition_fixture()
            self.assertIn(before, fixture["full_contexts"]["property_contexts"])
            fixture["full_contexts"]["property_contexts"] = fixture["full_contexts"]["property_contexts"].replace(before, after)
            with self.subTest(before=before, after=after), self.assertRaisesRegex(eb.EvolutionBaseError, "context rows"):
                self.check(fixture)

    def test_base_owned_property_prefix_overlap_is_not_a_new_base_permission(self):
        for selector in ("persist.vendor.", "persist.vendor.dpm.child"):
            fixture = composition_fixture()
            row = f"{selector} u:object_r:{CAMERA}:s0 prefix bool\n".encode()
            fixture["base"]["property_contexts"] += row
            fixture["full_contexts"]["property_contexts"] += row
            with self.subTest(selector=selector), self.assertRaisesRegex(eb.EvolutionBaseError, "prefixes overlap"):
                self.check(fixture)

    def test_base_cannot_duplicate_an_owned_selector_or_its_own_selector(self):
        for collision in ("owned", "base"):
            fixture = composition_fixture()
            row = (fixture["base"]["service_contexts"] if collision == "base" else
                   context_bytes(fixture["provider"]["context_entries"]["service_contexts"][:1]))
            fixture["base"]["service_contexts"] += row
            fixture["full_contexts"]["service_contexts"] += row
            with self.subTest(collision=collision), self.assertRaisesRegex(eb.EvolutionBaseError, "context selector"):
                self.check(fixture)

    def test_nul_or_non_object_label_in_contexts_fails(self):
        for row in (b"extra\x00 u:object_r:test:s0\n", b"extra u:r:test:s0\n"):
            fixture = composition_fixture()
            fixture["full_contexts"]["service_contexts"] += row
            with self.subTest(row=row), self.assertRaisesRegex(eb.EvolutionBaseError, "context bytes|object label"):
                self.check(fixture)


class FullOemIntegrationTests(unittest.TestCase):
    def native_arguments(self, camera=False):
        fixture = camera_composition_fixture() if camera else composition_fixture()
        corpus = fixture["corpus"]
        original = copy.deepcopy(op.load_contract())
        corpus[PLATFORM] += (
            b"(type init_dev_config)(type apexd_select_prop)(type media_variant_prop)\n"
            b"(typeattributeset domain (init_dev_config))\n")
        corpus[FACTORY] += b"(type mediaextractor)(type mediaserver)\n"
        vendor = b"(type offlinelog_file)(roletype object_r offlinelog_file)\n"
        corpus[op.INPUT_FLAGS["derived_vendor"]] = vendor
        for row in original["unchanged_factory_inputs"]:
            raw = corpus[row["runtime_path"]]
            row.update(sha256=vp.sha(raw), size_bytes=len(raw))
        original["existing_vendor_derivation"].update(sha256=vp.sha(vendor), size_bytes=len(vendor))
        for row in fixture["contract"]["unchanged_cil_inputs"]:
            raw = corpus[row["runtime_path"]]
            row.update(sha256=vp.sha(raw), size_bytes=len(raw))
        result = [corpus, vendor, original, (ROOT / "config/nezha-init-helper-capability.json").read_bytes(),
                  fixture["properties"], fixture["full_contexts"]["property_contexts"], fixture["provider"],
                  fixture["full_contexts"]["file_contexts"], fixture["full_contexts"]["service_contexts"],
                  fixture["contract"], fixture["base"], fixture["full_public"]]
        return result + [fixture["camera_contract"]] if camera else result

    def test_optional_camera_profile_keeps_full_oem_provider_and_helper_checks(self):
        arguments = self.native_arguments(camera=True)
        before = copy.deepcopy(arguments)
        result = op.check_native_contents(*arguments)
        self.assertEqual(arguments, before)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["helper_effective_property_set_grants"], 0)
        self.assertEqual(result["permissive_cil_declarations"], 0)
        self.assertEqual(result["evolution_policy_base_verification"]["camera_property_capability_verification"]
                         ["native_policies"]["actual"]["effective_vendor_init_property_set_grants"], 0)
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_enabled_base_keeps_full_oem_provider_and_helper_checks(self):
        arguments = self.native_arguments()
        original = copy.deepcopy(arguments)
        result = op.check_native_contents(*arguments)
        self.assertEqual(arguments, original)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["helper_effective_property_set_grants"], 0)
        self.assertEqual(result["permissive_cil_declarations"], 0)
        self.assertEqual(len(result["type_ownership"]), 7)
        self.assertEqual(len(result["provider_policy_verification"]["type_ownership"]), 8)
        self.assertEqual(result["evolution_policy_base_verification"]["base_type_count"], 4)
        self.assertEqual(result["property_effective_edge_budget_basis"],
                         "independent-native-evolution-base-plus-owned-contracts")
        self.assertFalse(result["legacy_property_edge_budget_reused_as_current"])
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_base_profile_never_relaxes_original_vendor_or_disabled_helper_guards(self):
        for change in ("original_vendor", "derived_vendor", "helper_set", "permissive"):
            arguments = self.native_arguments()
            if change == "original_vendor":
                arguments[1] += b"; changed\n"
            elif change == "derived_vendor":
                arguments[0][op.INPUT_FLAGS["derived_vendor"]] += b"; changed\n"
            elif change == "helper_set":
                arguments[0][PLATFORM] += b"(allow init_dev_config apexd_select_prop (property_service (set)))\n"
            else:
                arguments[0][eb.EXT] += b"(typepermissive evolution_test_app)\n"
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                op.check_native_contents(*arguments)


if __name__ == "__main__":
    unittest.main()
