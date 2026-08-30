"""Offline policy-input guards and complete metadata-authoritative TAR tests.

Only tiny synthetic unsigned AVB structures and regular-file bytes are used.
Preparation tests mock native evidence qualification, never filesystem/AVB
validation or TAR assembly. Separate policy qualifier cases exercise its real
evidence checks. No key, native process, network, guest or phone is involved.
"""

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import tarfile
import tempfile
import types
import unittest
from unittest import mock

from scripts import policy_image_inputs as policy
from tests.test_avb_image_set import erofs_payload, tree_descriptor, vbmeta, with_footer
from tests.test_erofs_metadata import by_path, fixture as metadata_fixture, recount


REAL_ROOT = policy.ROOT
EXPECTED_RECORDS = {
    "erofs_build", "erofs_source_manifest", "erofs_tools", "erofs_shared",
    "erofs_synthetic", "erofs_stock", "erofs_writer", "erofs_writer_orchestration",
    "policy_build", "policy_analysis", "vendor_derivation", "policy_build_log",
    "policy_source_manifest", "policy_build_sandbox", "native_oem_guard",
}
UNREVIEWED_POLICY_RECORDS = {"policy_build", "policy_analysis", "vendor_derivation", "policy_build_log",
                             "policy_source_manifest", "policy_build_sandbox", "native_oem_guard"}
EXPECTED_POLICY_FILES = {
    "/system/etc/selinux/plat_sepolicy.cil", "/system/etc/selinux/mapping/202504.cil",
    "/system_ext/etc/selinux/system_ext_sepolicy.cil", "/system_ext/etc/selinux/mapping/202504.cil",
    "/product/etc/selinux/product_sepolicy.cil", "/product/etc/selinux/mapping/202504.cil",
    "/vendor/etc/selinux/plat_pub_versioned.cil", "/vendor/etc/selinux/vendor_sepolicy.cil",
    "/odm/etc/selinux/odm_sepolicy.cil", "/system/etc/selinux/plat_sepolicy_genfs_202504.cil",
    "combined", "plat_sha256", "system_ext_sha256", "product_sha256",
}
FAILURES = (ValueError, OSError, KeyError)


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def load_helper():
    path = REAL_ROOT / "tools/erofs-metadata/full_tar.py"
    module = types.ModuleType("policy_test_full_tar")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


class SyntheticInputs:
    """A complete, deliberately non-flashable two-partition input selection."""

    def __init__(self, root):
        self.root = root
        self.contract = json.loads(policy.CONTRACT.read_text())
        self.contract["production_execution_profile"] = copy.deepcopy(policy.PRODUCTION_PROFILE)
        self.contract_sha = hashlib.sha256(b"synthetic policy-input contract").hexdigest()
        self.helper = load_helper()
        self.control = {
            "schema_version": 1, "contract_id": policy.CONTRACT_ID,
            "contract_sha256": self.contract_sha, "artifact_set_id": "synthetic-never-flash",
            "records": {}, "policy_files": {}, "partitions": {},
        }
        self.path = root / "inputs.json"
        self.output = root / self.contract["output_root"] / "prepared"
        self.rows, self.original_bytes, self.policy_bytes = {}, {}, {}
        for role in sorted(EXPECTED_RECORDS):
            raw = (b"INERT native build log\n" if role == "policy_build_log"
                   else policy.json_bytes({"synthetic_record_role": role}))
            row = self.write("records/" + role + ".json", raw)
            self.control["records"][role] = row
            self.contract["native_records"][role] = identity(raw)
        for index, runtime in enumerate(policy.RUNTIME_INPUTS):
            raw = ("; inert CIL input %d\n" % index).encode()
            native = "/work/out/target/product/nezha" + runtime
            if runtime == policy.RUNTIME_INPUTS[7]:
                native = "/work/out" + policy.VENDOR_SUFFIX
            self.policy_file(runtime, raw, native)
        self.policy_file("combined", b"INERT combined policy\0", "/work/out" + policy.COMBINED_SUFFIX)
        for index, name in ((0, "plat"), (2, "system_ext"), (4, "product")):
            raw = (hashlib.sha256(self.policy_bytes[policy.RUNTIME_INPUTS[index]]
                                 + self.policy_bytes[policy.RUNTIME_INPUTS[index + 1]])
                   .hexdigest().encode() + b"\n")
            partition = "system" if name == "plat" else name
            native = ("/work/out/target/product/nezha/" + partition
                      + "/etc/selinux/" + name + "_sepolicy_and_mapping.sha256")
            self.policy_file(name + "_sha256", raw, native)
        self.profile = {"image_budgets": {}}
        for name in ("vendor", "odm"):
            payload = bytearray(erofs_payload() + bytes(8192))
            struct.pack_into("<I", payload, 1060, 4)
            descriptor = tree_descriptor(name, size=16384, tree_at=16384, fec_at=20480)
            raw_image = with_footer(bytes(payload), vbmeta([descriptor]),
                                    tree_and_fec=b"T" * 4096 + b"F" * 8192)
            image_row = self.write(name + ".original", raw_image)
            self.profile["image_budgets"][name] = len(raw_image)
            rows = metadata_fixture(name, image_row["sha256"])
            rows[0]["image_size_bytes"] = len(raw_image)
            for row in rows[1:-1]:
                row.update(mtime_nsec=0, uid=1000, gid=2000)
                if row["path_hex"] == b"/raw-\xff".hex():
                    # Native byte paths are covered by the manifest parser;
                    # APFS cannot create every Linux byte-name fixture.
                    row["path_hex"] = b"/empty".hex()
                if row["type"] == "regular":
                    row["mode"] = stat.S_IFREG | 0o640
                row["xattrs"].insert(0, {"name_hex": b"security.capability".hex(),
                                         "value_hex": b"\x01\x00\xff\x80".hex()})
            self.rows[name] = rows
            staging = root / "staging" / name
            staging.mkdir(parents=True)
            sources = {}
            for row in rows[1:-1]:
                path = bytes.fromhex(row["path_hex"])
                if row["type"] != "regular":
                    continue
                data = (b"old policy" if path.decode("utf-8", "surrogateescape")
                        in policy.metadata.REPLACEMENT_PATHS[name]
                        else b"" if path == b"/empty" else b"preserved")
                destination = staging / os.fsdecode(path[1:])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                destination.chmod(0o600)
                os.utime(destination, (987654321, 987654321))
                sources[path] = data
            self.original_bytes[name] = sources
            self.control["partitions"][name] = {
                "image": image_row, "staging_root": str(staging.relative_to(root)),
                "manifest": self.write_manifest(name),
            }
            self.contract["originals"][name] = {
                "image": identity(raw_image), "entry_count": len(rows) - 2,
                "replacements": {path: identity(sources[path.encode()])
                                 for path in policy.metadata.REPLACEMENT_PATHS[name]},
            }
        # ROOT is relocated for output isolation; retain source bytes for the
        # workflow fingerprint and any final implementation rehashes.
        for row in self.contract["dependencies"] + [self.contract["exporter_source"]]:
            self.write(row["path"], (REAL_ROOT / row["path"]).read_bytes())
        self.write("scripts/policy_image_inputs.py", (REAL_ROOT / "scripts/policy_image_inputs.py").read_bytes())
        self.save()

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"path": str(path.relative_to(self.root)), **identity(raw)}

    def policy_file(self, role, raw, native):
        row = self.write("policy/" + str(len(self.policy_bytes)) + ".bin", raw)
        row["native_path"] = native
        self.control["policy_files"][role] = row
        self.policy_bytes[role] = raw

    def write_manifest(self, name):
        raw = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in self.rows[name])
        return self.write(name + ".jsonl", raw)

    def save_manifest(self, name):
        self.control["partitions"][name]["manifest"] = self.write_manifest(name)
        self.save()

    def save(self):
        raw = policy.json_bytes(self.control)
        self.path.write_bytes(raw)
        self.sha = identity(raw)["sha256"]
        return self.sha

    def selected(self, control):
        files = control["policy_files"]
        return {
            "vendor": {"/etc/selinux/vendor_sepolicy.cil": files[policy.RUNTIME_INPUTS[7]]},
            "odm": {
                "/etc/selinux/precompiled_sepolicy": files["combined"],
                **{"/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256": files[name + "_sha256"]
                   for name in ("plat", "system_ext", "product")},
            },
        }

    def loaded(self):
        return policy.load_control(self.path, self.sha, self.contract, self.contract_sha)[0]

    def replacement_plan(self, name):
        selected = self.selected(self.loaded())[name]
        return {"schema_version": 1, "partition": name, "replacements": [
            {"path": path, "before": self.contract["originals"][name]["replacements"][path],
             "after": {**policy.identity(row), "source": str(row["path"])}}
            for path, row in sorted(selected.items())]}

    def policy_evidence(self):
        """Public receipt structure; its CIL bytes are intentionally inert."""
        control = self.loaded()
        records = {name: {} for name in EXPECTED_RECORDS}
        build = {
            "build_passed": True, "native_sandbox_verified": True, "source_inputs_unchanged": True,
            "exit_code": 0, "timed_out": False, "sandbox_fallback": False,
            "actual_ninja_sandbox_observed": True, "target_product": "lineage_nezha",
            "target_release": "bp4a", "variant": "user", "phase": "synthetic-v12f",
            "sandbox": {"synthetic_read_only_source": True},
            "source_manifest": policy.identity(control["records"]["policy_source_manifest"]),
            "log": policy.identity(control["records"]["policy_build_log"]),
        }
        binary_paths = {
            "combined": control["policy_files"]["combined"]["native_path"],
            "source-precompiled": "/work/out/target/product/nezha/odm/etc/selinux/precompiled_sepolicy",
            "source-neverallows": "/work/out/soong/.intermediates/system/sepolicy/sepolicy_neverallows/android_common/policy",
        }
        analyses = [{"name": name, "exit_code": 0, "stdout_bytes": 0, "unfiltered": True,
                     "zero_permissive_domains": True, "sandbox_observed": True,
                     "stdout_sha256": identity(b"")["sha256"],
                     "sandbox_receipt_sha256": identity((name + " sandbox").encode())["sha256"],
                     "mountinfo_sha256": identity((name + " mounts").encode())["sha256"],
                     "build_path": binary_paths[name],
                     **policy.identity(control["policy_files"]["combined"])}
                    for name in ("combined", "source-precompiled", "source-neverallows")]
        check = {"status": "executed_and_passed", "fresh_execution_observed": True,
                 "build_phase": build["phase"], "build_log_sha256": control["records"]["policy_build_log"]["sha256"],
                 "mtime_used_to_infer_execution": False,
                 "ninja_success_records": [{"output": "synthetic-check"}],
                 "action_log_line": 1, "action_log_text": "synthetic context action"}
        analysis = {
            "schema_version": 1, "operation": "verify-native-oem-properties-v12f", "status": "verified",
            "build_phase": build["phase"], "provider_profile_selected": False,
            "strict_compiler_flags_verified": True,
            "compiler_temporary_to_analyzed_final_copy_verified": True,
            "all_guarded_inputs_unchanged": True,
            "build_result_sha256": control["records"]["policy_build"]["sha256"],
            "build_log_sha256": control["records"]["policy_build_log"]["sha256"],
            "build_source_manifest_sha256": control["records"]["policy_source_manifest"]["sha256"],
            "build_sandbox_sha256": control["records"]["policy_build_sandbox"]["sha256"],
            "actual_compiler_inputs": [
                {"runtime_path": runtime, "compiler_input": "compiled-input-" + str(index),
                 "resolved_path": control["policy_files"][runtime]["native_path"],
                 **policy.identity(control["policy_files"][runtime])} for index, runtime in enumerate(policy.RUNTIME_INPUTS)],
            "analyses": analyses,
            "semantics": {
                "status": "verified", "operation": "actual-native-v11-to-v12-four-property-semantic-delta",
                "original_assertion_statement_count": 6366, "original_assertion_statements_identical": True,
                "assertion_concrete_coverage_compared_to_projection": True,
                "reviewed_policy_delta_and_property_allow_endpoint_sets_matched": True,
                "helper_property_write_capability_disabled": True, "helper_effective_property_set_permissions": 0,
                "rule_semantics": {name: {"before_occurrences": count, "after_occurrences": count,
                                          "matches_projection": True, "statements_unchanged": True}
                                   for name, count in (("neverallow", 5976), ("neverallowx", 390))},
            },
            "native_context_checks": [{"target": name, **check} for name in sorted(policy.CONTEXT_TARGETS)],
            "native_oem_check": dict(check), "input_bindings": [],
        }
        for field in ("compiler_command_sha256", "driver_manifest_sha256", "analyzer_tool_sha256", "nsjail_sha256",
                      "reviewed_property_impact_sha256", "baseline_receipt_sha256"):
            analysis[field] = identity(field.encode())["sha256"]
        analysis["oem_contract_sha256"] = identity((self.root / "config/nezha-oem-policy.json").read_bytes())["sha256"]
        properties_raw = (self.root / "config/nezha-oem-properties.json").read_bytes()
        properties = json.loads(properties_raw)
        analysis["oem_property_contract_sha256"] = identity(properties_raw)["sha256"]
        semantics = analysis["semantics"]
        semantics.update({
            "review_contract_file_sha256": analysis["oem_property_contract_sha256"],
            "review_impact_file_sha256": analysis["reviewed_property_impact_sha256"],
            "actual_v11_baseline_receipt_sha256": analysis["baseline_receipt_sha256"],
            "candidate_input_identities": [{"runtime_path": row["runtime_path"], **policy.identity(row)}
                                           for row in analysis["actual_compiler_inputs"]],
            "inherited_semantics": {"all_referenced_symbol_closures_unchanged": True},
            "ordinary_rule_deltas": copy.deepcopy(properties["finite_impact"]["ordinary_rule_deltas"]),
            "property_ordinary_totals": copy.deepcopy(properties["native_effective_ordinary_allow_edges"]),
        })
        for row in analysis["native_context_checks"]:
            row.update(empty_stamp_alone_used_as_evidence=False, inputs=[{
                "resolved_path": control["policy_files"]["combined"]["native_path"],
                **policy.identity(control["policy_files"]["combined"])}])
        tool_sources = {name: identity(name.encode())["sha256"]
                        for name in ("vendor_policy.py", "artifact_files.py")}
        analysis["native_oem_check"].update({
            "target": "nezha_factory_oem_policy_check", "guard_json_alone_used_as_evidence": False,
            "actual_strict_compiler_input_count": 10,
            "input_binding_proof": {"count": 18, "exact_paths_hashes_sizes_verified": True},
            "full_guard_result_independently_rebound": True, "executed_tool_runtime_files_rehashed": True,
            "all_copy_mappings_verified": True, "provider_profile_present": False,
            "assertion_statement_counts": {"neverallow": 5976, "neverallowx": 390},
            "property_effective_ordinary_allow_edges": copy.deepcopy(properties["native_effective_ordinary_allow_edges"]),
            "source_tool_sha256": tool_sources,
            "inputs": [{"path": row["compiler_input"], "resolved_path": row["resolved_path"],
                        **policy.identity(row)} for row in analysis["actual_compiler_inputs"]],
            "output": policy.identity(control["records"]["native_oem_guard"]),
        })
        records["native_oem_guard"] = {
            "schema_version": 1, "operation": "check-nezha-oem-native-policy-inputs", "status": "verified",
            "contract_sha256": analysis["oem_contract_sha256"],
            "property_contract_sha256": analysis["oem_property_contract_sha256"],
            "helper_effective_property_set_grants": 0, "permissive_cil_declarations": 0,
            "original_factory_inputs_preserved": True, "existing_binder_derivation_preserved": True,
            "all_inputs_rehashed_unchanged": True,
            "assertion_statement_counts": {"neverallow": 5976, "neverallowx": 390},
            "property_effective_ordinary_allow_edges": copy.deepcopy(properties["native_effective_ordinary_allow_edges"]),
            "tool_sources_sha256": tool_sources,
        }
        analysis["input_bindings"].extend({"path": row["build_path"], **policy.identity(row)} for row in analyses)
        correction = json.loads((REAL_ROOT / "config/vendor-policy-correction.json").read_text())
        correction["output"].update(policy.identity(control["policy_files"][policy.RUNTIME_INPUTS[7]]))
        correction_raw = policy.json_bytes(correction)
        self.write("config/vendor-policy-correction.json", correction_raw)
        derivation = {
            "operation": "nezha-factory-binder-correction-v1",
            "contract_sha256": identity(correction_raw)["sha256"],
            "factory_package_sha256": self.contract["factory_package_sha256"],
            "output": correction["output"], "measured": correction["expected"],
            "inputs": copy.deepcopy(correction["inputs"]), "input_manifest": copy.deepcopy(correction["inputs"]),
            "tool_sha256": tool_sources["vendor_policy.py"], "publisher_sha256": tool_sources["artifact_files.py"],
            "preservation": {key: True for key in (
                "all_unselected_bytes_and_line_positions", "all_assertions",
                "type_role_alias_attribute_and_mapping_declarations", "valid_process_binder_grants",
                "fd_and_service_manager_grants")},
            "output_readback_verified": True, "all_inputs_rehashed_unchanged": True,
        }
        analysis["input_bindings"].append({
            "path": control["policy_files"][policy.RUNTIME_INPUTS[7]]["native_path"]
                    .removesuffix("vendor_sepolicy.cil") + "receipt.json",
            **policy.identity(control["records"]["vendor_derivation"]),
        })
        records.update(policy_build=build, policy_build_sandbox=copy.deepcopy(build["sandbox"]),
                       policy_analysis=analysis, vendor_derivation=derivation)
        return records, control

    def erofs_evidence(self):
        """Minimal native record graph; no native binary or source is opened."""
        control = self.loaded()
        contract = self.contract
        lock = {
            "schema_version": 1, "expected_erofs_utils_revision": contract["erofs_revision"],
            "expected_exporter_source_sha256": contract["exporter_source"]["sha256"],
            "build_provenance_verified_by_this_capture": False,
            "tools": {name: {"path": "/work/native/" + name, **row}
                      for name, row in contract["native_tools"].items()},
        }

        def checks(operation, names, failures=()):
            rows = [{"name": name, "status": "passed", "detail": {}} for name in names]
            rows.extend({"name": name, "status": "failed", "detail": {}, "group": "upstream-fsck"} for name in failures)
            return {"operation": operation, "skipped": 0, "checks": rows,
                    "passed": len(names), "failed": len(failures), "all_checks_passed": not failures,
                    "boundaries": {"native_processes_executed": True},
                    "tools": copy.deepcopy(lock), "driver": {"sha256": contract["native_driver_sha256"]},
                    "exporter_checks_passed": True}

        records = {
            "erofs_build": {
                "build_passed": True, "native_sandbox_verified": True, "source_inputs_unchanged": True,
                "exit_code": 0, "timed_out": False, "sandbox_fallback": False,
                "actual_ninja_sandbox_observed": True, "target_product": "lineage_nezha",
                "target_release": "bp4a", "variant": "user", "argv": ["nezha_erofs_metadata"],
                "source_manifest": policy.identity(control["records"]["erofs_source_manifest"]),
            },
            "erofs_source_manifest": [{"path": "/work/evolution/tools/nezha-erofs-metadata/erofs_metadata.c",
                                        **policy.identity(contract["exporter_source"])}],
            "erofs_tools": lock,
            "erofs_shared": checks("synthetic-block-zero-shared-xattr-qualification", (
                "native-versions", "literal-shared-base-zero", "shared-id-at-eof", "shared-entry-crosses-eof",
                "shared-reserved-byte", "shared-shared-count-over-body", "original-fixture-preserved", "tools-stable")),
            "erofs_synthetic": checks("synthetic-native-validation", (
                "native-versions", "deterministic-flat-rebuild", "exporter-reads-nanoseconds-independently",
                "detect-capability-change", "detect-selinux-nul-change", "detect-unselected-content-change", "tools-stable"),
                ("writer-preserves-nanoseconds", "upstream-fsck-empty-xattr-compatibility")),
            "erofs_stock": checks("read-only-stock-metadata-validation", (
                "native-versions", "stock-vendor", "stock-odm", "stock-vendor-fsck-xattrs", "stock-odm-fsck-xattrs", "tools-stable")),
            "erofs_writer": checks("synthetic-manifest-policy-writer-roundtrip-v3", (
                "native-versions", "vendor-seed-qualification", "odm-seed-qualification",
                "vendor-writer-1-roundtrip", "vendor-writer-2-roundtrip", "odm-writer-1-roundtrip", "odm-writer-2-roundtrip",
                "required-native-export-qualification", "both-partitions-reproducible-exact-five-changes",
                "all-bound-inputs-unchanged", "tools-stable"), ("vendor-writer-1-upstream-xattrs",)),
            "erofs_writer_orchestration": {"operation": "native-erofs-manifest-writer-roundtrip",
                                           "input_bytes_preserved": True, "source_and_android_outputs_unchanged": True},
        }
        records["erofs_shared"]["controls"] = {"qualification_driver": {"sha256": contract["shared_driver_sha256"]}}
        records["erofs_writer"]["controls"] = {
            "writer_roundtrip_checks_passed": True, "wrapper_driver": {"sha256": contract["writer_driver_sha256"]},
            "known_limitations": {"nonzero_nanoseconds_admitted": False},
        }
        controls = records["erofs_writer"]["controls"]
        controls["wrapper_driver"].update(path="/work/native/wrapper.py", size_bytes=123)
        input_contract = {"path": "/work/native/input-contract.json", **identity(b"synthetic writer input contract")}
        source_pins = {name: next(row for row in contract["dependencies"] if row["path"] == path)
                       for name, path in (("writer", "tools/erofs-metadata/full_tar.py"),
                                          ("metadata_checker", "scripts/erofs_metadata.py"))}
        source_pins.update(exporter_source=contract["exporter_source"],
                           native_runner={"sha256": contract["native_driver_sha256"], "size_bytes": 234})
        sources = {name: {"path": "/work/native/" + name, **policy.identity(row)} for name, row in source_pins.items()}
        controls.update(contract=input_contract, input_contract={
            "tools_lock": policy.identity(control["records"]["erofs_tools"]), "sources": sources,
            "fixture_bundle": {"path": "/work/native/fixture.tar", **identity(b"synthetic fixture tar")},
        })
        outer = records["erofs_writer_orchestration"]
        outer.update({
            "original_images_modified": False, "phone_accessed": False,
            "complete_rom_readiness": False, "qualified_checker_path_preserved": True,
            "native_build": policy.identity(control["records"]["erofs_build"]),
            "source_manifest": policy.identity(control["records"]["erofs_source_manifest"]),
            "qualified_tools_lock": policy.identity(control["records"]["erofs_tools"]),
            "prior_qualification": [{**policy.identity(control["records"][role]),
                                      **{key: records[role][key] for key in ("passed", "failed", "all_checks_passed")},
                                      "failed_checks": copy.deepcopy([row for row in records[role]["checks"] if row["status"] == "failed"])}
                                     for role in ("erofs_shared", "erofs_synthetic")],
            "contract": dict(input_contract), "fresh_checker_copy": policy.identity(source_pins["metadata_checker"]),
            "staged_inputs": copy.deepcopy([*sources.values(), input_contract, controls["wrapper_driver"],
                                             controls["input_contract"]["fixture_bundle"]]),
            "result": {
                "receipt_present": True, "receipt": policy.identity(control["records"]["erofs_writer"]),
                "writer_roundtrip_checks_passed": True, "exporter_checks_passed": True,
                "tools_stable": True, "nonzero_nanoseconds_admitted": False, "empty_xattr_failures_retained": True,
                **{key: records["erofs_writer"][key] for key in ("passed", "failed", "skipped", "all_checks_passed")},
                "failed_checks": copy.deepcopy([row for row in records["erofs_writer"]["checks"] if row["status"] == "failed"]),
            },
            "phase": {"sandbox_verified": True, "exit_code": 1,
                      **{key: identity(key.encode()) for key in ("sandbox_observation", "stdout", "stderr")}},
        })
        writer = {row["name"]: row for row in records["erofs_writer"]["checks"]}
        writer["both-partitions-reproducible-exact-five-changes"]["detail"] = {
            "independent_derivations_per_partition": 2, "unique_literal_policy_replacements": 5,
            "tar_image_manifest_bytes_reproducible": True,
        }
        stock = {row["name"]: row for row in records["erofs_stock"]["checks"]}
        for name in ("vendor", "odm"):
            stock["stock-" + name]["detail"] = {
                "all_inode_nanoseconds_zero": True,
                "manifest": policy.identity(control["partitions"][name]["manifest"]),
                "image_hash_reported_by_native_exporter": contract["originals"][name]["image"]["sha256"],
                "entry_count": contract["originals"][name]["entry_count"],
            }
        return records, control


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native processes forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("shell execution forbidden")))

    def assert_boundaries(self, result):
        for name in policy.BOUNDARIES:
            self.assertIs(result[name], False, name)
        self.assertIs(result["production_writer_admitted"], False)


class ContractTests(OfflineTests):
    def test_current_contract_has_fifteen_records_and_blocks_seven_unreviewed_policy_records(self):
        contract, digest, _, helper = policy.load_contract()
        result = policy.plan()
        self.assertEqual(EXPECTED_RECORDS, set(contract["native_records"]))
        self.assertEqual(15, len(EXPECTED_RECORDS))
        self.assertEqual(UNREVIEWED_POLICY_RECORDS,
                         {name for name, value in contract["native_records"].items() if value is None})
        self.assertEqual("blocked", result["status"])
        self.assertEqual(sorted(UNREVIEWED_POLICY_RECORDS), result["missing_reviewed_native_record_pins"])
        self.assertEqual(digest, result["contract_sha256"])
        self.assertTrue(callable(helper.assemble))
        self.assertEqual(1, len(result["required_replacements"]["vendor"]))
        self.assertEqual(4, len(result["required_replacements"]["odm"]))
        self.assertIs(result["images_or_policy_inputs_opened"], False)
        self.assertIs(result["missing_production_execution_profile"], False)
        self.assertIs(contract["production_execution_profile"]["native_execution_qualified"], False)
        self.assert_boundaries(result)

    def test_prepare_blocked_before_input_selection_or_output_creation(self):
        with mock.patch.object(policy, "load_control", side_effect=AssertionError("must not inspect inputs")) as control:
            with mock.patch.object(policy.io, "_fresh_output", side_effect=AssertionError("must not create output")) as output:
                with self.assertRaisesRegex(policy.PolicyImageError, "native evidence pins"):
                    policy.prepare(Path("/nonexistent/private-input.json"), "a" * 64,
                                   output_dir=Path("/nonexistent/output"))
        control.assert_not_called()
        output.assert_not_called()

    def test_blocked_cli_reports_false_execution_boundaries(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = policy.main(["plan"])
        self.assertEqual(2, result)
        self.assert_boundaries(json.loads(stdout.getvalue()))

    def test_blocked_prepare_cli_emits_sanitized_failure_and_no_success(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = policy.main(["prepare", "--input", "/nonexistent/private-control.json",
                                  "--expected-sha256", "a" * 64, "--output-dir", "/nonexistent/output"])
        self.assertEqual(2, result)
        self.assertEqual("", stdout.getvalue())
        failure = json.loads(stderr.getvalue())
        self.assertEqual("failed", failure["status"])
        self.assertNotIn("private-control", stderr.getvalue())
        for name in policy.BOUNDARIES:
            self.assertIs(failure[name], False, name)


class FixtureTests(OfflineTests):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="policy-input-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fx = SyntheticInputs(self.root)


class InputTests(FixtureTests):
    def test_exact_fifteen_records_and_fourteen_policy_files_are_required(self):
        self.assertEqual(EXPECTED_POLICY_FILES, set(self.fx.loaded()["policy_files"]))
        self.assertEqual(14, len(EXPECTED_POLICY_FILES))
        for field, key in (("records", "native_oem_guard"), ("records", "policy_build_sandbox"),
                           ("policy_files", "combined"), ("policy_files", "plat_sha256")):
            for operation in ("remove", "extra"):
                with self.subTest(field=field, key=key, operation=operation):
                    original = copy.deepcopy(self.fx.control)
                    if operation == "remove":
                        self.fx.control[field].pop(key)
                    else:
                        self.fx.control[field]["unexpected"] = copy.deepcopy(self.fx.control[field][key])
                    self.fx.save()
                    with self.assertRaises(policy.PolicyImageError):
                        self.fx.loaded()
                    self.fx.control = original
        self.fx.save()

    def test_control_digest_and_reviewed_record_pin_are_enforced(self):
        with self.assertRaisesRegex(policy.PolicyImageError, "control digest"):
            policy.load_control(self.fx.path, "f" * 64, self.fx.contract, self.fx.contract_sha)
        self.fx.contract["native_records"]["policy_analysis"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(policy.PolicyImageError, "reviewed and pinned"):
            self.fx.loaded()

    def test_modified_promoted_helper_fails_source_pin_before_import(self):
        path = self.root / "tools/erofs-metadata/full_tar.py"
        original = path.read_bytes()
        path.write_bytes(b"X" + original[1:])
        with mock.patch.object(policy, "ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "identity differs"):
                policy.load_contract()

    def test_noncanonical_native_producer_paths_are_rejected(self):
        row = self.fx.control["policy_files"]["combined"]
        for path in ("relative/policy", "/work/../work/policy", "/work//policy"):
            with self.subTest(path=path):
                row["native_path"] = path
                self.fx.save()
                with self.assertRaisesRegex(policy.PolicyImageError, "native producer"):
                    self.fx.loaded()

    def test_metadata_helper_checks_every_replacement_preimage(self):
        for name in ("vendor", "odm"):
            with self.subTest(partition=name):
                manifest = policy.metadata.read_manifest(self.root / (name + ".jsonl"))
                plan = self.fx.replacement_plan(name)
                plan["replacements"][0]["before"]["sha256"] = "a" * 64
                with self.assertRaisesRegex(ValueError, "original identity"):
                    self.fx.helper.replacement_plan(policy.metadata, manifest, plan)


class PreparationTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.object(policy, "ROOT", self.root))
        self.contract_loader = self.enterContext(mock.patch.object(policy, "load_contract", side_effect=self.contract))
        self.enterContext(mock.patch.object(policy, "qualify_erofs", return_value={"native_reexecuted_by_this_command": False}))
        self.enterContext(mock.patch.object(policy, "qualify_policy", side_effect=lambda records, control, contract:
                                            (self.fx.selected(control), {"native_policy_reexecuted": False})))
        self.enterContext(mock.patch.object(policy.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(1 << 40, 0, 1 << 40)))

    def contract(self):
        return self.fx.contract, self.fx.contract_sha, self.fx.profile, self.fx.helper

    def prepare(self, output=None):
        return policy.prepare(self.fx.path, self.fx.sha, output_dir=output or self.fx.output)

    def assert_no_success(self):
        self.assertFalse((self.fx.output / "preparation.json").exists())

    def test_two_complete_tars_preserve_metadata_links_xattrs_and_exact_five_contents(self):
        source_snapshots = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = self.prepare()
        self.assertEqual("complete-tar-inputs-prepared", result["status"])
        self.assertTrue(result["two_complete_tar_derivations_identical"])
        self.assertFalse(result["metadata_from_staging_tree"])
        self.assert_boundaries(result)
        selected = self.fx.selected(self.fx.loaded())
        for name in ("vendor", "odm"):
            first = self.fx.output / "pass-1" / (name + ".tar")
            second = self.fx.output / "pass-2" / (name + ".tar")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(identity(first.read_bytes()), result["passes"][0][name]["tar"])
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
            for repetition in (0, 1):
                current = result["passes"][repetition][name]
                self.assertEqual(len(self.fx.original_bytes[name]), current["regular_paths_verified"])
                self.assertIs(current["recipe"]["native_execution_admitted"], False)
                self.assertIs(current["recipe"]["production_execution_profile_required"], True)
                self.assertIn("--tar=f", current["recipe"]["arguments"])
            with tarfile.open(first, "r:", encoding="utf-8", errors="surrogateescape") as archive:
                entries = archive.getmembers()
                self.assertEqual(len(self.fx.rows[name]) - 2, len(entries))
                self.assertEqual({"." if row["path_hex"] == "2f" else os.fsdecode(bytes.fromhex(row["path_hex"])[1:])
                                  for row in self.fx.rows[name][1:-1]}, {entry.name for entry in entries})
                for row in self.fx.rows[name][1:-1]:
                    path = bytes.fromhex(row["path_hex"])
                    member = archive.getmember("." if path == b"/" else os.fsdecode(path[1:]))
                    self.assertEqual((row["uid"], row["gid"], stat.S_IMODE(row["mode"]), row["mtime_sec"]),
                                     (member.uid, member.gid, member.mode, member.mtime))
                    if path != b"/hard-b":
                        for attr in row["xattrs"]:
                            key = "SCHILY.xattr." + bytes.fromhex(attr["name_hex"]).decode()
                            self.assertEqual(bytes.fromhex(attr["value_hex"]),
                                             member.pax_headers[key].encode("utf-8", "surrogateescape"))
                    if row["type"] == "regular":
                        replacement = selected[name].get(os.fsdecode(path))
                        expected = replacement["path"].read_bytes() if replacement else self.fx.original_bytes[name][path]
                        self.assertEqual(expected, archive.extractfile(member).read())
                    elif row["type"] == "symlink":
                        self.assertTrue(member.issym())
                        self.assertEqual(bytes.fromhex(row["symlink_target_hex"]), os.fsencode(member.linkname))
                alias = archive.getmember("hard-b")
                self.assertTrue(alias.islnk())
                self.assertEqual("hard-a", alias.linkname)
            self.assertEqual(len(policy.metadata.REPLACEMENT_PATHS[name]), len(result["replacements"][name]))
        for path, raw in source_snapshots.items():
            self.assertEqual(raw, path.read_bytes(), str(path))
        self.assertEqual(result, json.loads((self.fx.output / "preparation.json").read_text()))

    def test_missing_selected_preimage_is_not_replaced_without_verification(self):
        (self.root / "staging/vendor/etc/selinux/vendor_sepolicy.cil").unlink()
        with self.assertRaises(FileNotFoundError):
            self.prepare()
        self.assert_no_success()

    def test_original_image_identity_cannot_be_substituted(self):
        path = self.root / self.fx.control["partitions"]["vendor"]["image"]["path"]
        raw = path.read_bytes()
        path.write_bytes(b"X" + raw[1:])
        with self.assertRaisesRegex(ValueError, "input changed"):
            self.prepare()
        self.assert_no_success()

    def test_changed_unselected_or_hardlink_alias_bytes_are_rejected(self):
        for path in ("unchanged", "hard-b", "etc/selinux/vendor_sepolicy.cil"):
            with self.subTest(path=path):
                target = self.root / "staging/vendor" / path
                original = target.read_bytes()
                target.write_bytes(b"X" * len(original))
                with self.assertRaisesRegex(ValueError, "content mismatch"):
                    self.prepare()
                self.assert_no_success()
                target.write_bytes(original)
                if self.fx.output.exists():
                    shutil.rmtree(self.fx.output)

    def test_nonzero_nanoseconds_and_empty_xattrs_are_not_admitted(self):
        for kind in ("superblock", "inode", "empty-xattr"):
            with self.subTest(kind=kind):
                original = copy.deepcopy(self.fx.rows["vendor"])
                if kind == "superblock":
                    self.fx.rows["vendor"][0]["superblock"]["build_time_nsec"] = 1
                elif kind == "inode":
                    by_path(self.fx.rows["vendor"], b"/unchanged")["mtime_nsec"] = 1
                else:
                    by_path(self.fx.rows["vendor"], b"/unchanged")["xattrs"][0]["value_hex"] = ""
                self.fx.save_manifest("vendor")
                with self.assertRaisesRegex(ValueError, "nanoseconds|fractional|empty xattr"):
                    self.prepare()
                self.assert_no_success()
                self.fx.rows["vendor"] = original
        self.fx.save_manifest("vendor")

    def test_metadata_drift_without_new_manifest_identity_is_rejected(self):
        by_path(self.fx.rows["vendor"], b"/unchanged")["uid"] = 2001
        self.fx.write_manifest("vendor")
        with self.assertRaisesRegex(ValueError, "SHA256 differs"):
            self.prepare()
        self.assert_no_success()

    def test_missing_replacement_metadata_is_rejected(self):
        rows = self.fx.rows["vendor"]
        rows.remove(by_path(rows, b"/etc/selinux/vendor_sepolicy.cil"))
        recount(rows)
        self.fx.contract["originals"]["vendor"]["entry_count"] = len(rows) - 2
        self.fx.save_manifest("vendor")
        with self.assertRaisesRegex(ValueError, "missing replacement"):
            self.prepare()
        self.assert_no_success()

    def test_fresh_output_and_containment_are_required(self):
        self.fx.output.mkdir(parents=True)
        sentinel = self.fx.output / "untouched"
        sentinel.write_bytes(b"do not overwrite")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare()
        self.assertEqual(b"do not overwrite", sentinel.read_bytes())
        self.assert_no_success()
        for output in (self.root / self.fx.contract["output_root"], self.root / "outside-output"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "fresh ignored"):
                    self.prepare(output)

    def test_symlinked_staging_sources_and_output_ancestors_are_rejected(self):
        staging = self.root / "staging/vendor"
        moved = self.root / "real-vendor-staging"
        staging.rename(moved)
        staging.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(FAILURES):
            self.prepare()
        self.assert_no_success()
        staging.unlink()
        moved.rename(staging)
        if self.fx.output.exists():
            shutil.rmtree(self.fx.output)
        staging_file = staging / "unchanged"
        staging_file.unlink()
        staging_file.symlink_to(staging / "hard-a")
        with self.assertRaisesRegex(ValueError, "not regular"):
            self.prepare()
        self.assert_no_success()
        shutil.rmtree(self.fx.output.parent)
        self.fx.output.parent.symlink_to(staging, target_is_directory=True)
        with self.assertRaises(FAILURES):
            self.prepare()
        self.assertFalse((staging / "prepared").exists())

    def test_output_inside_staging_is_rejected_before_creating_it(self):
        self.fx.control["partitions"]["vendor"]["staging_root"] = str(self.root / self.fx.contract["output_root"])
        self.fx.save()
        with self.assertRaisesRegex(ValueError, "outside.*staging"):
            self.prepare()
        self.assertFalse(self.fx.output.exists())

    def test_shared_or_nested_staging_roots_are_rejected_before_assembly(self):
        vendor = self.root / "staging/vendor"
        original_odm = self.root / "staging/odm"
        for common in (vendor, vendor / "nested-odm"):
            with self.subTest(staging=common):
                shutil.copytree(original_odm, common, dirs_exist_ok=True)
                self.fx.control["partitions"]["odm"]["staging_root"] = str(common)
                self.fx.save()
                with mock.patch.object(self.fx.helper, "assemble", side_effect=AssertionError("must reject shared staging first")):
                    with self.assertRaisesRegex(ValueError, "staging.*distinct|staging.*overlap|staging.*shared|separate.*staging"):
                        self.prepare()
                self.assertFalse(self.fx.output.exists())

    def test_changed_policy_file_after_assembly_cannot_publish_success(self):
        assemble = self.fx.helper.assemble
        calls = 0

        def mutate_after_last(*args):
            nonlocal calls
            result = assemble(*args)
            calls += 1
            if calls == 4:
                path = self.root / self.fx.control["policy_files"]["combined"]["path"]
                raw = path.read_bytes()
                path.write_bytes(b"X" * len(raw))
            return result

        with mock.patch.object(self.fx.helper, "assemble", side_effect=mutate_after_last):
            with self.assertRaisesRegex(ValueError, "input changed"):
                self.prepare()
        self.assert_no_success()

    def test_changed_native_record_after_assembly_cannot_publish_success(self):
        assemble = self.fx.helper.assemble
        calls = 0

        def mutate_after_last(*args):
            nonlocal calls
            result = assemble(*args)
            calls += 1
            if calls == 4:
                path = self.root / self.fx.control["records"]["policy_analysis"]["path"]
                path.write_bytes(policy.json_bytes({"synthetic_record_role": "another_analysis"}))
            return result

        with mock.patch.object(self.fx.helper, "assemble", side_effect=mutate_after_last):
            with self.assertRaisesRegex(ValueError, "evidence identity differs"):
                self.prepare()
        self.assert_no_success()

    def test_changed_contract_after_assembly_cannot_publish_success(self):
        self.contract_loader.side_effect = [self.contract(), (self.fx.contract, "f" * 64, self.fx.profile, self.fx.helper)]
        with self.assertRaisesRegex(ValueError, "source contract changed"):
            self.prepare()
        self.assert_no_success()

    def test_changed_workflow_source_after_assembly_cannot_publish_success(self):
        assemble = self.fx.helper.assemble
        calls = 0

        def mutate_after_last(*args):
            nonlocal calls
            result = assemble(*args)
            calls += 1
            if calls == 4:
                (self.root / "scripts/policy_image_inputs.py").write_bytes(b"# changed workflow source\n")
            return result

        with mock.patch.object(self.fx.helper, "assemble", side_effect=mutate_after_last):
            with self.assertRaisesRegex(ValueError, "source contract changed"):
                self.prepare()
        self.assert_no_success()

    def test_second_tar_metadata_cannot_disagree_with_first_pass(self):
        assemble = self.fx.helper.assemble
        calls = 0

        def corrupt_second_pass(manifest, staging, replacements, output):
            nonlocal calls
            calls += 1
            if calls == 3:
                # Change only valid metadata in pass two, leaving the complete
                # regular-file reads and byte-count checks otherwise intact.
                manifest = copy.deepcopy(manifest)
                manifest.entries[b"/unchanged"]["uid"] += 1
            return assemble(manifest, staging, replacements, output)

        with mock.patch.object(self.fx.helper, "assemble", side_effect=corrupt_second_pass):
            with self.assertRaisesRegex(ValueError, "independent.*TAR.*differ"):
                self.prepare()
        self.assert_no_success()

    def test_completed_tar_cannot_change_during_the_other_pass(self):
        assemble = self.fx.helper.assemble
        calls = 0

        def corrupt_previous_pass(*args):
            nonlocal calls
            result = assemble(*args)
            calls += 1
            if calls == 4:
                old_tar = self.fx.output / "pass-1/odm.tar"
                raw = old_tar.read_bytes()
                old_tar.write_bytes(bytes((raw[0] ^ 1,)) + raw[1:])
            return result

        with mock.patch.object(self.fx.helper, "assemble", side_effect=corrupt_previous_pass):
            with self.assertRaisesRegex(ValueError, "input changed|TAR.*changed|TAR.*differ"):
                self.prepare()
        self.assert_no_success()

    def test_low_disk_fails_before_any_tar_is_written(self):
        with mock.patch.object(policy.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(0, 0, 0)):
            with self.assertRaisesRegex(ValueError, "insufficient space"):
                self.prepare()
        self.assertFalse(list(self.fx.output.rglob("*.tar")))
        self.assert_no_success()


class PolicyQualificationTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.records, self.control = self.fx.policy_evidence()
        self.enterContext(mock.patch.object(policy, "ROOT", self.root))

    def qualify(self):
        return policy.qualify_policy(self.records, self.control, self.fx.contract)

    def test_combined_binary_and_three_cil_plus_mapping_digests_select_exact_five_paths(self):
        selected, proof = self.qualify()
        self.assertEqual({name: set(rows) for name, rows in selected.items()}, policy.metadata.REPLACEMENT_PATHS)
        self.assertTrue(proof["current_factory_combined_binary_bound"])
        self.assertTrue(proof["sidecars_recomputed_and_matched"])
        self.assertFalse(proof["native_policy_reexecuted"])
        self.assertEqual(6366, proof["assertion_statements_retained"])

    def test_source_only_odm_binary_is_rejected_even_if_analysis_hash_matches(self):
        wrong = "/work/out/target/product/nezha/odm/etc/selinux/precompiled_sepolicy"
        self.control["policy_files"]["combined"]["native_path"] = wrong
        self.records["policy_analysis"]["analyses"][0]["build_path"] = wrong
        with self.assertRaisesRegex(ValueError, "factory-combined"):
            self.qualify()

    def test_analyzed_combined_producer_path_and_identity_must_match(self):
        combined = self.records["policy_analysis"]["analyses"][0]
        for key, value in (("build_path", "/other" + policy.COMBINED_SUFFIX), ("sha256", "c" * 64)):
            with self.subTest(key=key):
                old = combined[key]
                combined[key] = value
                with self.assertRaisesRegex(ValueError, "producer differs|binary identity differs|factory-combined"):
                    self.qualify()
                combined[key] = old

    def test_actual_compiler_cil_identity_path_and_input_order_must_match(self):
        inputs = self.records["policy_analysis"]["actual_compiler_inputs"]
        for key, value in (("sha256", "f" * 64), ("resolved_path", "/another/runtime.cil")):
            with self.subTest(key=key):
                original = inputs[0][key]
                inputs[0][key] = value
                with self.assertRaisesRegex(ValueError, "actual compiler input"):
                    self.qualify()
                inputs[0][key] = original
        inputs[0], inputs[1] = inputs[1], inputs[0]
        with self.assertRaisesRegex(ValueError, "inputs/order"):
            self.qualify()

    def test_sidecar_hashes_cil_then_mapping_and_requires_exact_lf(self):
        row = self.control["policy_files"]["plat_sha256"]
        cil, mapping = (self.fx.policy_bytes[p] for p in policy.RUNTIME_INPUTS[:2])
        for raw in (hashlib.sha256(cil).hexdigest().encode() + b"\n",
                    hashlib.sha256(mapping + cil).hexdigest().encode() + b"\n",
                    hashlib.sha256(cil + mapping).hexdigest().encode(),
                    hashlib.sha256(cil + mapping).hexdigest().encode() + b"\r\n"):
            with self.subTest(raw=raw):
                row["path"].write_bytes(raw)
                row.update(identity(raw))
                with self.assertRaisesRegex(ValueError, "framework sidecar"):
                    self.qualify()

    def test_sidecar_from_another_native_producer_is_rejected(self):
        self.control["policy_files"]["product_sha256"]["native_path"] = "/work/out/source-only/product.sha256"
        with self.assertRaisesRegex(ValueError, "framework sidecar"):
            self.qualify()

    def test_current_build_log_and_phase_bindings_are_required(self):
        analysis = self.records["policy_analysis"]
        for key, value in (("build_log_sha256", "a" * 64), ("build_phase", "stale-build"),
                           ("build_sandbox_sha256", "b" * 64)):
            with self.subTest(key=key):
                original = analysis[key]
                analysis[key] = value
                with self.assertRaises(ValueError):
                    self.qualify()
                analysis[key] = original

    def test_required_context_checks_cannot_be_skipped_or_inferred_from_mtime(self):
        check = self.records["policy_analysis"]["native_context_checks"][0]
        for key, value in (("fresh_execution_observed", False), ("mtime_used_to_infer_execution", True),
                           ("status", "skipped")):
            with self.subTest(key=key):
                original = check[key]
                check[key] = value
                with self.assertRaisesRegex(ValueError, "stale native policy check"):
                    self.qualify()
                check[key] = original

    def test_permissive_domains_or_assertion_removal_fail_closed(self):
        combined = self.records["policy_analysis"]["analyses"][0]
        combined["stdout_bytes"] = 1
        with self.assertRaisesRegex(ValueError, "permissive domains"):
            self.qualify()
        combined["stdout_bytes"] = 0
        self.records["policy_analysis"]["semantics"]["rule_semantics"]["neverallow"]["after_occurrences"] -= 1
        with self.assertRaisesRegex(ValueError, "assertions were dropped"):
            self.qualify()

    def test_two_source_policy_analyses_cannot_reuse_the_combined_producer(self):
        analyses = self.records["policy_analysis"]["analyses"]
        for source in analyses[1:]:
            with self.subTest(name=source["name"]):
                original = source["build_path"]
                source["build_path"] = analyses[0]["build_path"]
                with self.assertRaisesRegex(ValueError, "analysis producer"):
                    self.qualify()
                source["build_path"] = original

    def test_raw_oem_guard_and_record_identity_must_match_independent_proof(self):
        raw = self.records["native_oem_guard"]
        raw["original_factory_inputs_preserved"] = False
        with self.assertRaisesRegex(ValueError, "raw native OEM result"):
            self.qualify()
        raw["original_factory_inputs_preserved"] = True
        self.records["policy_analysis"]["native_oem_check"]["output"]["sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "captured OEM guard result"):
            self.qualify()

    def test_empty_vendor_preservation_proof_is_rejected(self):
        self.records["vendor_derivation"]["preservation"] = {}
        with self.assertRaisesRegex(ValueError, "vendor correction receipt"):
            self.qualify()

    def test_semantic_property_delta_cannot_be_replaced_by_passing_booleans(self):
        observed = self.records["policy_analysis"]["semantics"]["property_ordinary_totals"]
        first = next(iter(observed.values()))
        first["count"] += 1
        with self.assertRaisesRegex(ValueError, "finite native policy effect"):
            self.qualify()


class ErofsQualificationTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.records, self.control = self.fx.erofs_evidence()

    def qualify(self):
        return policy.qualify_erofs(self.records, self.fx.contract, self.control)

    def test_native_qualification_retains_known_failures_without_admitting_production(self):
        proof = self.qualify()
        self.assertEqual(["upstream-fsck-empty-xattr-compatibility", "writer-preserves-nanoseconds"],
                         proof["reviewed_failed_checks_retained"]["synthetic"])
        self.assertEqual(["vendor-writer-1-upstream-xattrs"],
                         proof["reviewed_failed_checks_retained"]["writer_upstream_xattrs"])
        for name in ("nonzero_nanoseconds_admitted", "empty_xattr_values_admitted",
                     "native_reexecuted_by_this_command", "production_writer_admitted"):
            self.assertIs(proof[name], False, name)

    def test_source_capture_and_exporter_source_must_match_build(self):
        build_source = self.records["erofs_build"]["source_manifest"]
        original = dict(build_source)
        build_source["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "build source capture differs"):
            self.qualify()
        build_source.update(original)
        self.records["erofs_source_manifest"][0]["sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "source/build linkage differs"):
            self.qualify()

    def test_self_consistent_replacement_native_tools_cannot_override_reviewed_pins(self):
        for role in ("erofs_tools", "erofs_shared", "erofs_synthetic", "erofs_stock", "erofs_writer"):
            lock = self.records[role] if role == "erofs_tools" else self.records[role]["tools"]
            lock["tools"]["mkfs"]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "native binary identities differ"):
            self.qualify()

    def test_shared_xattr_driver_is_independently_pinned(self):
        self.records["erofs_shared"]["controls"]["qualification_driver"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "shared-xattr qualification source"):
            self.qualify()

    def test_stock_export_manifest_and_image_must_match_selected_partition(self):
        detail = next(row["detail"] for row in self.records["erofs_stock"]["checks"] if row["name"] == "stock-vendor")
        detail["manifest"]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "stock metadata capture differs"):
            self.qualify()

    def test_outer_writer_receipt_must_identify_the_qualified_inner_result(self):
        outer = self.records["erofs_writer_orchestration"]
        outer["result"]["receipt"]["sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "outer writer receipt"):
            self.qualify()

    def test_outer_writer_must_bind_each_staged_source_and_retained_failure(self):
        outer = self.records["erofs_writer_orchestration"]
        source = outer["staged_inputs"][0]
        original = source["sha256"]
        source["sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "preserved staged input"):
            self.qualify()
        source["sha256"] = original
        outer["prior_qualification"][1]["failed_checks"] = []
        with self.assertRaisesRegex(ValueError, "prior qualification result differs"):
            self.qualify()


class ProductionBudgetTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.manifests = {name: policy.metadata.read_manifest(self.root / (name + ".jsonl"))
                          for name in ("vendor", "odm")}
        self.plans = {name: self.fx.replacement_plan(name) for name in self.manifests}
        self.tar_sizes = {}
        for name, manifest in self.manifests.items():
            replacements = self.fx.helper.replacement_plan(policy.metadata, manifest, self.plans[name])
            output = self.fx.helper.TarOutput(io.BytesIO())
            self.fx.helper.assemble(manifest, self.root / "staging" / name, replacements, output)
            self.tar_sizes[name] = output.size
            self.assertEqual(output.size, policy.tar_size(self.fx.helper, manifest, replacements))

    def budget(self):
        return policy.production_budget(self.manifests, self.plans, self.tar_sizes, self.fx.contract)

    def test_exact_tars_and_unique_regular_inode_rounding_keep_finite_unqualified_limits(self):
        budget = self.budget()
        vendor, odm = budget["partitions"]["vendor"], budget["partitions"]["odm"]
        self.assertEqual(10 + 9 + 9, vendor["original_unique_regular_bytes"])
        self.assertEqual(4 * 10 + 9 + 9, odm["original_unique_regular_bytes"])
        self.assertEqual(3 * 65536, vendor["scratch_spool_bound_bytes"])
        self.assertEqual(6 * 65536, odm["scratch_spool_bound_bytes"])
        self.assertEqual(3 * 4096, vendor["original_staging_allocation_bound_bytes"])
        self.assertEqual(6 * 4096, odm["original_staging_allocation_bound_bytes"])
        self.assertEqual(5 * 4096, budget["replacement_source_allocation_bytes"])
        self.assertEqual(48 << 30, budget["additional_free_bytes_required"])
        self.assertLess(budget["calculated_additional_peak_bytes"], 48 << 30)
        self.assertIs(budget["native_execution_qualified"], False)
        self.assertTrue(budget["original_images_already_present_and_not_copied"])
        for name, limit in (("vendor", 2 << 30), ("odm", 6 << 30)):
            partition = budget["partitions"][name]
            self.assertEqual(self.tar_sizes[name], partition["exact_tar_bytes"])
            self.assertEqual(((self.tar_sizes[name] + 4095) // 4096 + 1) * 4096,
                             partition["tar_assembler_fsize_bytes"])
            self.assertEqual(limit, partition["mkfs_fsize_soft_and_hard_bytes"])
            self.assertEqual(1, partition["minimum_regular_capture_batches"])
            self.assertFalse(partition["partition_fit_verified"])

    def test_scratch_estimate_rounds_up_at_64k_and_does_not_double_count_hardlinks(self):
        self.manifests["vendor"].entries[b"/unchanged"]["size_bytes"] = 65537
        result = self.budget()["partitions"]["vendor"]
        self.assertEqual(4 * 65536, result["scratch_spool_bound_bytes"])
        self.assertEqual(65537 + 10 + 9, result["original_unique_regular_bytes"])
        self.assertEqual((17 + 1 + 1) * 4096, result["original_staging_allocation_bound_bytes"])

    def test_unreviewed_profile_oversize_capture_and_excessive_tar_fail_closed(self):
        self.fx.contract["production_execution_profile"]["native_execution_qualified"] = True
        with self.assertRaisesRegex(ValueError, "unreviewed production"):
            self.budget()
        self.fx.contract["production_execution_profile"]["native_execution_qualified"] = False
        row = self.manifests["vendor"].entries[b"/unchanged"]
        original = row["size_bytes"]
        row["size_bytes"] = (512 << 20) + 1
        with self.assertRaisesRegex(ValueError, "regular-byte capture"):
            self.budget()
        row["size_bytes"] = original
        self.tar_sizes["vendor"] = 2 << 30
        with self.assertRaisesRegex(ValueError, "finite construction cap"):
            self.budget()


class NativeCheckRecordTests(OfflineTests):
    def record(self):
        return {"operation": "synthetic-native-validation", "skipped": 0,
                "boundaries": {"native_processes_executed": True},
                "checks": [{"name": "required", "status": "passed"},
                           {"name": "known-limit", "status": "failed"}],
                "passed": 1, "failed": 1, "all_checks_passed": False}

    def check(self, record):
        return policy._checks(record, "synthetic-native-validation", {"required"},
                              allowed_failures={"known-limit"})

    def test_reviewed_failures_are_retained_without_claiming_all_checks_passed(self):
        rows, failures = self.check(self.record())
        self.assertEqual(["known-limit"], failures)
        self.assertEqual("passed", rows["required"]["status"])

    def test_skipped_unreviewed_or_miscounted_native_checks_are_rejected(self):
        for field, value in (("skipped", 1), ("passed", 2), ("failed", 0), ("all_checks_passed", True)):
            with self.subTest(field=field):
                record = self.record()
                record[field] = value
                with self.assertRaises(ValueError):
                    self.check(record)
        record = self.record()
        record["checks"][1]["name"] = "unreviewed-failure"
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            self.check(record)

    def test_duplicate_or_failed_required_native_check_is_rejected(self):
        record = self.record()
        record["checks"].append(copy.deepcopy(record["checks"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(record)
        record = self.record()
        record["checks"][0]["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "required native"):
            self.check(record)


if __name__ == "__main__":
    unittest.main()
