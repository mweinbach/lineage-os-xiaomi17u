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
        self.contract = json.loads(policy.CONTRACT.read_text())["profiles"][policy.HISTORICAL_PROFILE]
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
    def test_historical_contract_has_fifteen_records_and_blocks_seven_unreviewed_policy_records(self):
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

    def test_catalog_preserves_historical_canonical_bytes_and_requires_explicit_current_selection(self):
        catalog = json.loads(policy.CONTRACT.read_bytes())
        historical = catalog["profiles"][policy.HISTORICAL_PROFILE]
        self.assertEqual("0a549e0374f17fcd24e25dba668bbe745750968bc1336c7c142583fac1816cc4",
                         identity(policy.json_bytes(historical))["sha256"])
        self.assertEqual(policy.HISTORICAL_PROFILE, policy.plan()["profile"])
        current = policy.plan(policy.EXPORT4_PROFILE)
        self.assertEqual(policy.EXPORT4_CONTRACT_ID, current["contract_id"])
        self.assertEqual("ready_for_evidence_validation", current["status"])
        self.assertEqual([], current["missing_reviewed_native_record_pins"])
        self.assertEqual(policy.PROFILE_CONTRACT_SHA256[policy.EXPORT4_PROFILE], current["contract_sha256"])
        self.assert_boundaries(current)
        self.assertFalse(current["production_writer_admitted"])

    def test_unknown_or_mutated_profile_fails_before_private_input_reads(self):
        with self.assertRaisesRegex(ValueError, "unknown or incomplete"):
            policy.load_contract("v13-prototype")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "contract.json"
            original = json.loads(policy.CONTRACT.read_bytes())
            for change in (lambda c: c["profiles"][policy.HISTORICAL_PROFILE].update(device="other"),
                           lambda c: c["profiles"].update({"v13-prototype": {}})):
                value = copy.deepcopy(original)
                change(value)
                path.write_bytes(policy.json_bytes(value))
                with mock.patch.object(policy, "CONTRACT", path):
                    with self.assertRaisesRegex(ValueError, "reviewed contract bytes|unknown or incomplete"):
                        policy.load_contract()
            value = copy.deepcopy(original)
            value["profiles"][policy.EXPORT4_PROFILE]["native_records"]["sidecar_native_validation"]["sha256"] = "f" * 64
            path.write_bytes(policy.json_bytes(value))
            with mock.patch.object(policy, "CONTRACT", path):
                with self.assertRaisesRegex(ValueError, "reviewed contract bytes"):
                    policy.load_contract(policy.EXPORT4_PROFILE)


class FixtureTests(OfflineTests):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="policy-input-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fx = SyntheticInputs(self.root)


def select_export4(fx):
    """Select the new schema using only inert local evidence identities."""
    fx.contract["contract_id"] = policy.EXPORT4_CONTRACT_ID
    fx.contract["sidecar_derivation"] = copy.deepcopy(json.loads(policy.CONTRACT.read_text())["profiles"]
                                                     [policy.EXPORT4_PROFILE]["sidecar_derivation"])
    fx.control["contract_id"] = policy.EXPORT4_CONTRACT_ID
    for role in sorted(policy.EXPORT4_RECORD_ROLES - EXPECTED_RECORDS):
        row = fx.write("records/" + role + ".json", policy.json_bytes({"inert_record": role}))
        fx.control["records"][role] = row
        fx.contract["native_records"][role] = policy.identity(row)
    for name in ("plat", "system_ext", "product"):
        fx.control["policy_files"].pop(name + "_sha256")
    fx.control["noop_manifests"] = {name: [copy.deepcopy(fx.control["partitions"][name]["manifest"]) for unused in range(2)]
                                    for name in ("vendor", "odm")}
    fx.save()


def sidecar_evidence(fx, control):
    """Literal recipe/output evidence shape; no command is executed."""
    pins = fx.contract["sidecar_derivation"]
    base = "/work/validation/nezha-oem-policy-integration-20260829/policy-sidecar-native-v1"
    row = lambda name, raw=b"inert": {"path": base + "/" + name, **identity(raw)}
    sandbox = {"source_out_and_inputs_readonly": True, "uid": 65534, "gid": 65534,
        "capabilities": {name: "0" * 16 for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")},
        "namespaces": {name: name + ":[2]" for name in ("mnt", "net", "pid", "user")},
        "parent_namespaces": {name: name + ":[1]" for name in ("mnt", "net", "pid", "user")},
        "identity_maps": {name: "65534 0 1\n" for name in ("uid_map", "gid_map")}, "readonly_flag": 1,
        "effective_mount_flags": {name: 1 for name in ("/", "/work", "/work/evolution", "/work/out", base, base + "/inputs")},
        "mountinfo_sha256": identity(b"inert mountinfo")["sha256"],
        "argv": ["/usr/bin/python3", "-I", "-B", base + "/inputs/driver.py", "--base", base]}
    source = {"schema_version": 1, "guest_writes": False, "phone_accessed": False,
        "files": [{"path": "system/sepolicy/Android.bp", **pins["source"]}], "total_bytes": pins["source"]["size_bytes"],
        "projects": {"system/sepolicy": {"head": pins["source_revision"], "status": "M private/init_dev_config.te\n M private/su.te"}}}
    held = {runtime: fx.policy_bytes[runtime] for runtime in policy.RUNTIME_INPUTS[:6]}
    native = {"schema_version": 1, "operation": "derive-export4-policy-sidecars-native-v1", "passed": True,
        "skipped": 0, "input_bytes_preserved": True, "tool_and_runtime_bytes_preserved": True,
        "scope": {"native_recipe_executed": True, "derived_sidecars_verified": True,
            "installed_sidecars_captured": False, "native_android_genrules_executed": False,
            "source_or_android_output_writes": False, "images_accessed_or_written": False,
            "policy_adopted": False, "complete_rom_ready": False, "phone_accessed": False},
        "contract": row("inputs/contract.json"),
        "driver": {"path": base + "/inputs/driver.py", **pins["driver"]},
        "collector": {"path": base + "/inputs/bound_util.py", **pins["collector"]},
        "source_capture": policy.identity(control["records"]["sidecar_source_capture"]),
        "recipe_source": {**pins["source"], "project_revision": pins["source_revision"], "native_path": "/work/evolution/system/sepolicy/Android.bp"},
        "baseline": {**policy.identity(control["records"]["policy_analysis"]), "operation": "verify-native-oem-properties-v12f-export4"},
        "sandbox": policy.identity(control["records"]["sidecar_sandbox"]), "staging_manifest": row("inputs/staging.json"),
        "limits": {"command_cpu_hard_seconds": 11, "command_cpu_soft_seconds": 10, "command_wall_seconds": 20,
            "file_size_soft_and_hard_bytes": 16 << 20, "initial_free_bytes": 256 << 20,
            "log_cap_each_bytes": 16 << 20, "whole_job_wall_seconds": 180},
        "environment": {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "TMPDIR": "/tmp"},
        "commands": [], "tools": {}, "inputs": [], "recipes": [], "outputs": [], "checks": []}
    native["contract"].update(pins["contract"])

    def command(argv, stdout=b"", supervisor=False):
        return {"argv": argv, "exit_code": 0, "timed_out": False, "log_overflow": False,
            "whole_process_group_killed": False, "all_pipes_eof": True, "log_cap_each_bytes": 16 << 20,
            "supervisor_log_separated": supervisor,
            "logs": {name: row("results/command." + name, stdout if name == "stdout" else b"")
                     for name in (("stdout", "stderr", "supervisor") if supervisor else ("stdout", "stderr"))}}

    def linked(path):
        return {"selected_path": path, "canonical": {"path": path, **identity(b"inert ELF fixture")}, "symlink_chain": []}

    for index, name in enumerate(("bash", "cat", "sha256sum", "cut")):
        loader = "/lib/ld-linux-aarch64.so.1"
        native["tools"][name] = {"abi": {"elf_machine": 183, "interpreter": loader},
            "identity": linked("/usr/bin/" + name), "loader": linked(loader), "runtime": [linked("/lib/libc.so.6")],
            "runtime_command_index": 2 * index, "version_command_index": 2 * index + 1}
        native["commands"] += [command([loader, "--list", "/usr/bin/" + name], b"inert loader output"),
                               command(["/usr/bin/" + name, "--version"], b"inert version output")]
        native["tools"][name]["loader_output_parse"] = {
            "adapter": "initial-aarch64-address-only-record-v1", "abi": copy.deepcopy(native["tools"][name]["abi"]),
            "original_stdout": identity(b"inert loader output"), "named_records_stdout": identity(b"inert loader output"),
            "initial_address_only_record": None, "named_file_paths": ["/lib/libc.so.6"],
            "named_records_checked_by_unchanged_frozen_parser": True, "unnamed_record_file_origin_claimed": False}
    roles = [name + "-" + suffix for name in ("plat", "system_ext", "product") for suffix in ("cil", "mapping")]
    for runtime, role in zip(policy.RUNTIME_INPUTS, roles):
        native["inputs"].append({"role": role, "runtime_path": runtime, **identity(held[runtime]),
            "native_compiler_input": control["policy_files"][runtime]["native_path"], "filename": role + ".cil",
            "derived_input_path": base + "/inputs/" + role + ".cil"})
    pipeline = '/usr/bin/cat "$1" "$2" | /usr/bin/sha256sum | /usr/bin/cut -d\' \' -f1 > "$3"'
    arguments = lambda left, right, dest: ["/usr/bin/bash", "--noprofile", "--norc", "-euo", "pipefail", "-c",
        pipeline, "sidecar-recipe", left, right, dest]
    for index, name in enumerate(("plat", "system_ext", "product")):
        pair = roles[2 * index:2 * index + 2]
        content = hashlib.sha256(held[policy.RUNTIME_INPUTS[2 * index]] + held[policy.RUNTIME_INPUTS[2 * index + 1]]).hexdigest().encode() + b"\n"
        destination = base + "/results/derived/" + name + "_sepolicy_and_mapping.sha256"
        native["recipes"].append({"module": name + "_sepolicy_and_mapping.sha256_gen",
            "source_modules": [":" + name + "_sepolicy.cil", ":" + name + "_mapping_file"],
            "ordered_input_roles": pair, "command": pins["recipe"],
            "line_start": (514, 531, 549)[index], "line_end": (522, 539, 557)[index]})
        native["outputs"].append({"name": name, "ordered_input_roles": pair, "command_index": 8 + index,
            "native_installed_path": None, "provenance": "derived-from-sealed-export4-inputs",
            "output": {"path": destination, **identity(content)}, "ascii_content": content.decode()})
        native["commands"].append(command(arguments(*[base + "/inputs/" + r + ".cil" for r in pair], destination)))
        native["checks"].append({"name": name + "-known-answer", "status": "passed"})
    first, second = held[policy.RUNTIME_INPUTS[0]], held[policy.RUNTIME_INPUTS[1]]
    changed = bytes([first[0] ^ 1]) + first[1:]
    mutations = {"reversed-order": hashlib.sha256(second + first).hexdigest().encode() + b"\n",
        "changed-input": hashlib.sha256(changed + second).hexdigest().encode() + b"\n",
        "missing-final-lf": native["outputs"][0]["ascii_content"].encode()[:-1]}
    left, right = [base + "/inputs/plat-" + suffix + ".cil" for suffix in ("cil", "mapping")]
    mutation_commands = [arguments(right, left, base + "/results/reversed-order.sha256"),
        arguments(base + "/results/changed-plat.cil", right, base + "/results/changed-input.sha256"),
        ["/usr/bin/bash", "--noprofile", "--norc", "-euo", "pipefail", "-c", 'printf \'%s\' "$1" > "$2"',
         "negative-lf", native["outputs"][0]["ascii_content"].rstrip("\n"), base + "/results/missing-final-lf.sha256"]]
    for index, (name, content) in enumerate(mutations.items(), 11):
        native["commands"].append(command(mutation_commands[index - 11]))
        native["checks"].append({"name": name, "status": "passed", "command_index": index,
            "output": row("results/" + name + ".sha256", content), "rejected_by_exact_output_check": True})
    native["changed_input"] = {"original_role": "plat-cil", "mutation": "first-byte-xor-1",
        "output": row("results/changed-plat.cil", changed)}
    outer = {"operation": "root-policy-sidecar-native-orchestration-v1", "passed": True,
        "native_result": native, "native_receipt": policy.identity(control["records"]["sidecar_native_validation"]),
        "launcher": {"path": base + "/inputs/run.py", **pins["launcher"]},
        "collector": {"path": base + "/inputs/bound_util.py", **pins["collector"]},
        "live_recipe_source": pins["source"], "bound_selected_inputs_unchanged": True,
        "global_build_idle_required": False, "global_android_output_unchanged_claimed": False,
        "source_or_android_output_writes": False, "images_accessed_or_written": False, "phone_accessed": False,
        "sandbox_observation": native["sandbox"], "guest_base": base, "staging_manifest": native["staging_manifest"],
        "nsjail": {"path": "/work/evolution/prebuilts/build-tools/linux-x86/bin/nsjail",
            "sha256": "3f97556c3cf8a83d3f5ae854e6dfc2f345355ead547dd661d07a369b6c2ba280", "size_bytes": 1},
        "commands": [command(["/usr/bin/git", "--no-optional-locks", "-C", "/work/evolution/system/sepolicy", "rev-parse", "HEAD"],
                             (pins["source_revision"] + "\n").encode())]}
    outer["commands"] += [command([outer["nsjail"]["path"]], supervisor=True), copy.deepcopy(outer["commands"][0])]
    return {"sidecar_native_validation": native, "sidecar_orchestration": outer,
            "sidecar_sandbox": sandbox, "sidecar_source_capture": source}, held


class Export4InputTests(FixtureTests):
    def setUp(self):
        super().setUp()
        select_export4(self.fx)

    def test_current_selection_has_only_eleven_real_policy_artifacts_and_four_noop_manifests(self):
        control = self.fx.loaded()
        self.assertEqual({*policy.RUNTIME_INPUTS, "combined"}, set(control["policy_files"]))
        self.assertEqual(29, len(control["records"]))
        self.assertEqual({"vendor": 2, "odm": 2}, {p: len(rows) for p, rows in control["noop_manifests"].items()})

    def test_absent_installed_sidecars_cannot_be_fabricated_as_selectors(self):
        self.fx.control["policy_files"]["plat_sha256"] = copy.deepcopy(self.fx.control["policy_files"]["combined"])
        self.fx.save()
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            self.fx.loaded()

    def test_missing_complete_noop_pass_and_extra_profile_field_are_rejected(self):
        original = copy.deepcopy(self.fx.control)
        for change in (lambda: self.fx.control["noop_manifests"]["vendor"].pop(),
                       lambda: self.fx.control.update(profile="v12-export4")):
            self.fx.control = copy.deepcopy(original)
            change(); self.fx.save()
            with self.assertRaises(ValueError):
                self.fx.loaded()

    def test_historical_control_cannot_select_current_contract(self):
        self.fx.control["contract_id"] = policy.CONTRACT_ID
        self.fx.save()
        with self.assertRaisesRegex(ValueError, "contract differs"):
            self.fx.loaded()


class SidecarQualificationTests(FixtureTests):
    def setUp(self):
        super().setUp()
        select_export4(self.fx)
        self.control = self.fx.loaded()
        self.records, self.held = sidecar_evidence(self.fx, self.control)

    def qualify(self):
        return policy.qualify_sidecar_derivation(self.records, self.control, self.held, self.fx.contract)

    def test_ordered_known_answers_and_three_negatives_admit_only_derived_outputs(self):
        proof = self.qualify()
        self.assertEqual((3, 3, 0), (proof["native_known_answers"], proof["native_negative_cases"], proof["skipped"]))
        self.assertIs(proof["native_installed_sidecars_captured"], False)
        self.assertIs(proof["android_genrule_execution_claimed"], False)

    def test_derivation_cannot_be_relabelled_as_installed_android_output(self):
        native = self.records["sidecar_native_validation"]
        for key in ("installed_sidecars_captured", "native_android_genrules_executed", "policy_adopted", "complete_rom_ready"):
            with self.subTest(key=key):
                native["scope"][key] = True
                with self.assertRaisesRegex(ValueError, "falsely claim"):
                    self.qualify()
                native["scope"][key] = False
        native["outputs"][0]["native_installed_path"] = "/work/out/target/product/nezha/system/etc/selinux/plat_sepolicy_and_mapping.sha256"
        with self.assertRaisesRegex(ValueError, "exact ordered"):
            self.qualify()

    def test_reversed_recipe_order_even_with_valid_input_identities_is_rejected(self):
        self.records["sidecar_native_validation"]["recipes"][0]["source_modules"].reverse()
        with self.assertRaisesRegex(ValueError, "recipe order"):
            self.qualify()

    def test_output_content_and_recorded_identity_must_both_match_recomputed_digest(self):
        native = self.records["sidecar_native_validation"]
        for content in ("0" * 64 + "\n", native["outputs"][0]["ascii_content"][:-1]):
            with self.subTest(content=content):
                original = copy.deepcopy(native["outputs"][0])
                native["outputs"][0]["ascii_content"] = content
                native["outputs"][0]["output"].update(identity(content.encode()))
                with self.assertRaisesRegex(ValueError, "digest plus LF"):
                    self.qualify()
                native["outputs"][0] = original

    def test_different_native_compiler_source_and_swapped_pair_are_rejected(self):
        native = self.records["sidecar_native_validation"]
        native["inputs"][0]["native_compiler_input"] = "/work/out/unrelated.cil"
        with self.assertRaisesRegex(ValueError, "actual compiler file"):
            self.qualify()
        native["inputs"][0]["native_compiler_input"] = self.control["policy_files"][policy.RUNTIME_INPUTS[0]]["native_path"]
        native["inputs"][0], native["inputs"][1] = native["inputs"][1], native["inputs"][0]
        with self.assertRaisesRegex(ValueError, "input coverage"):
            self.qualify()

    def test_missing_or_forged_negative_check_cannot_count_as_pass(self):
        native = self.records["sidecar_native_validation"]
        native["checks"].pop()
        with self.assertRaisesRegex(ValueError, "negative cases"):
            self.qualify()
        self.records, self.held = sidecar_evidence(self.fx, self.control)
        native = self.records["sidecar_native_validation"]
        native["checks"][3]["output"].update(policy.identity(native["outputs"][0]["output"]))
        with self.assertRaisesRegex(ValueError, "negative output"):
            self.qualify()

    def test_writable_sealed_inputs_changed_driver_and_nonzero_capabilities_reject(self):
        for change in (lambda: self.records["sidecar_sandbox"]["effective_mount_flags"].update({self.records["sidecar_orchestration"]["guest_base"] + "/inputs": 0}),
                       lambda: self.records["sidecar_native_validation"]["driver"].update(sha256="f" * 64),
                       lambda: self.records["sidecar_sandbox"]["capabilities"].update(CapEff="1")):
            self.records, self.held = sidecar_evidence(self.fx, self.control)
            change()
            with self.assertRaises(ValueError):
                self.qualify()

    def test_failed_or_truncated_native_pipeline_is_not_a_pass(self):
        for key, value in (("exit_code", 1), ("log_overflow", True), ("all_pipes_eof", False)):
            self.records, self.held = sidecar_evidence(self.fx, self.control)
            self.records["sidecar_native_validation"]["commands"][8][key] = value
            with self.assertRaisesRegex(ValueError, "complete cleanly"):
                self.qualify()

    def test_actual_abi_address_only_line_is_recorded_without_assigning_file_or_mapping_origin(self):
        native = self.records["sidecar_native_validation"]
        parsed = native["tools"]["bash"]["loader_output_parse"]
        raw = "\t (0x0000ffff88890000)\n"
        parsed["initial_address_only_record"] = {"line_index": 0, "raw_line": raw, "file_path": None,
            "file_identity_verified": False, "mapping_kind_identified": False}
        parsed["original_stdout"] = identity(raw.encode() + b"inert loader output")
        native["commands"][0]["logs"]["stdout"].update(parsed["original_stdout"])
        self.qualify()
        for key, value in (("line_index", 1), ("raw_line", "unrecognized line\n"),
                           ("file_identity_verified", True), ("mapping_kind_identified", True)):
            original = parsed["initial_address_only_record"][key]
            parsed["initial_address_only_record"][key] = value
            with self.assertRaisesRegex(ValueError, "unnamed loader record"):
                self.qualify()
            parsed["initial_address_only_record"][key] = original

    def test_loader_adapter_cannot_drop_named_files_or_claim_unnamed_file_origin(self):
        parsed = self.records["sidecar_native_validation"]["tools"]["bash"]["loader_output_parse"]
        for key, value in (("named_file_paths", []), ("unnamed_record_file_origin_claimed", True),
                           ("named_records_checked_by_unchanged_frozen_parser", False)):
            original = parsed[key]
            parsed[key] = value
            with self.assertRaisesRegex(ValueError, "named runtime proof"):
                self.qualify()
            parsed[key] = original


def export4_policy_evidence(fx):
    records, unused = fx.policy_evidence()
    select_export4(fx)
    control = fx.loaded()
    analysis = records["policy_analysis"]
    phase = "policy-v12f-export-1"
    records["policy_build"]["phase"] = phase
    analysis.update(operation="verify-native-oem-properties-v12f-export4", build_phase=phase,
        export_phase="v12f-runtime-policy-exports-v1",
        installed_fixup_manifest_sha256="8907f7705cd1a767a037531c63ee9b4c4454def1ec8bfbd623862f4df879ce14",
        installed_integration_manifest_sha256="084e740e4888bdded20c2ca3b44ce3400652c5ac8ab242a8c17dc99d56a04820",
        **{key: False for key in ("full_treble_apk_labeling_pass", "policy_compiler_replayed",
            "source_or_android_output_modified", "images_changed", "phone_accessed", "complete_rom_or_runtime_support_proven")})
    analysis["source_fixup_provenance"] = {"operation": "verify-v12f-fixed-addendum-chain", "status": "verified",
        "normal_android_enforcing_required": True, "unchanged_policy_component_retained": True,
        "unchanged_vendor_component_retained": True,
        "native_build_binding": {"phase": phase, "packaged_commit_equal_to_build_record": True},
        "source_capture": {"all_effective_source_guards_bound": True}}
    for row in [*analysis["native_context_checks"], analysis["native_oem_check"]]:
        row["build_phase"] = phase
    sidecars, unused = sidecar_evidence(fx, control)
    records.update(sidecars)
    return records, control


class Export4PolicyTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.records, self.control = export4_policy_evidence(self.fx)
        self.enterContext(mock.patch.object(policy, "ROOT", self.root))

    def qualify(self):
        return policy.qualify_policy(self.records, self.control, self.fx.contract)

    def test_actual_v12_shape_retains_strict_policy_guards_and_derives_three_uninstalled_files(self):
        replacements, proof = self.qualify()
        self.assertEqual(policy.metadata.REPLACEMENT_PATHS, {name: set(rows) for name, rows in replacements.items()})
        self.assertEqual(6366, proof["assertion_statements_retained"])
        self.assertEqual(0, proof["normal_android_permissive_domains"])
        self.assertFalse(proof["current_active_source_compatibility_proven"])
        self.assertFalse(proof["sidecars_observed_at_native_install_paths"])
        for path, row in replacements["odm"].items():
            if path.endswith(".sha256"):
                self.assertEqual(65, len(row["derived_bytes"]))
                self.assertNotIn("native_path", row)
                self.assertNotIn("path", row)

    def test_old_operation_or_provider_profile_cannot_be_admitted_as_export4(self):
        analysis = self.records["policy_analysis"]
        for key, wrong in (("operation", "verify-native-oem-properties-v12f"), ("provider_profile_selected", True)):
            old = analysis[key]
            analysis[key] = wrong
            with self.assertRaisesRegex(ValueError, "policy analysis is incomplete"):
                self.qualify()
            analysis[key] = old

    def test_current_snapshot_still_rejects_source_only_odm_and_missing_assertions(self):
        old = self.control["policy_files"]["combined"]["native_path"]
        self.control["policy_files"]["combined"]["native_path"] = "/work/out/target/product/nezha/odm/etc/selinux/precompiled_sepolicy"
        with self.assertRaisesRegex(ValueError, "factory-combined"):
            self.qualify()
        self.control["policy_files"]["combined"]["native_path"] = old
        self.records["policy_analysis"]["semantics"]["original_assertion_statement_count"] = 6365
        with self.assertRaisesRegex(ValueError, "assertion or capability"):
            self.qualify()


class Export4PreparationTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.records, unused = export4_policy_evidence(self.fx)
        self.enterContext(mock.patch.object(policy, "ROOT", self.root))
        self.enterContext(mock.patch.object(policy, "load_contract", return_value=(
            self.fx.contract, self.fx.contract_sha, self.fx.profile, self.fx.helper)))
        self.enterContext(mock.patch.dict(policy.PROFILE_CONTRACT_SHA256, {policy.EXPORT4_PROFILE: self.fx.contract_sha}))
        self.enterContext(mock.patch.object(policy, "qualify_erofs", return_value={"synthetic_native_evidence_mock": True}))
        qualify = policy.qualify_policy
        self.enterContext(mock.patch.object(policy, "qualify_policy", side_effect=lambda unused, control, contract:
                                            qualify(self.records, control, contract)))
        self.enterContext(mock.patch.object(policy.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(1 << 40, 0, 1 << 40)))

    def prepare(self):
        return policy.prepare(self.fx.path, self.fx.sha, output_dir=self.fx.output, selected_profile=policy.EXPORT4_PROFILE)

    def test_derived_sidecars_have_own_provenance_and_complete_repeated_tar_contents(self):
        report = self.prepare()
        self.assert_boundaries(report)
        self.assertEqual(policy.EXPORT4_PROFILE, report["profile"])
        self.assertEqual(3, len(report["derived_sidecars"]))
        self.assertFalse(report["policy_proof"]["sidecars_observed_at_native_install_paths"])
        for row in report["derived_sidecars"]:
            path = self.fx.output / row["path"]
            raw = path.read_bytes()
            self.assertEqual(identity(raw), policy.identity(row))
            self.assertEqual(65, len(raw))
            self.assertFalse(row["native_installed_output_claimed"])
            self.assertEqual(2, len(row["ordered_inputs"]))
            self.assertEqual(row["ordered_input_roles"], [r["runtime_path"] for r in row["ordered_inputs"]])
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
            member = "etc/selinux/precompiled_sepolicy." + path.name
            for repetition in (1, 2):
                with tarfile.open(self.fx.output / f"pass-{repetition}/odm.tar", "r:") as archive:
                    self.assertEqual(raw, archive.extractfile(member).read())
        self.assertEqual((self.fx.output / "pass-1/odm.tar").read_bytes(), (self.fx.output / "pass-2/odm.tar").read_bytes())

    def test_changed_derived_sidecar_after_assembly_prevents_success_receipt(self):
        assemble = self.fx.helper.assemble
        calls = 0
        def mutate_after_last(*args):
            nonlocal calls
            result = assemble(*args)
            calls += 1
            if calls == 4:
                (self.fx.output / "derived-sidecars/plat_sepolicy_and_mapping.sha256").write_bytes(b"0" * 64 + b"\n")
            return result
        with mock.patch.object(self.fx.helper, "assemble", side_effect=mutate_after_last):
            with self.assertRaisesRegex(ValueError, "input changed"):
                self.prepare()
        self.assertFalse((self.fx.output / "preparation.json").exists())

    def test_changed_complete_noop_manifest_after_assembly_prevents_success_receipt(self):
        assemble = self.fx.helper.assemble
        calls = 0
        def mutate_after_last(*args):
            nonlocal calls
            result = assemble(*args)
            calls += 1
            if calls == 4:
                path = self.root / self.fx.control["noop_manifests"]["vendor"][0]["path"]
                path.write_bytes(b"changed evidence\n")
            return result
        with mock.patch.object(self.fx.helper, "assemble", side_effect=mutate_after_last):
            with self.assertRaisesRegex(ValueError, "input changed"):
                self.prepare()
        self.assertFalse((self.fx.output / "preparation.json").exists())


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

    def contract(self, selected_profile=policy.HISTORICAL_PROFILE):
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


class SyntheticNoopEvidence:
    """Two original inodes, two complete after captures, and full receipt links."""

    def __init__(self, root):
        self.root = root
        root.mkdir(parents=True)
        self.records, self.rows = {}, {}
        self.control = {"records": {}, "partitions": {}, "noop_manifests": {}}
        self.contract = {
            "contract_id": policy.EXPORT4_CONTRACT_ID, "originals": {},
            "exporter_source": identity(b"synthetic exporter source"),
            "native_tools": {name: identity(("synthetic " + name).encode())
                             for name in ("mkfs", "fsck", "exporter")},
        }
        primitive_names = (
            "inherited_signal_profile", "finite_limits", "ext4_alignment",
            "truncate_2tib_rejected", "truncate_over_limit_rejected", "write_at_limit_rejected",
            "sparse_boundary_write", "sparse_allocation_bounded", "sparse_readback",
            "truncated_back_to_zero", "cleanup_completed",
        )
        self.records["erofs_fsize_probe"] = {
            "operation": "native-production-fsize-sparse-log-profile-proof", "passed": True, "skipped": 0,
            "scope": {"mkfs_executed": False, "mkfs_production_execution_qualified": False},
            "checks": [{"name": f"limit-{gib}gib", "status": "passed", "native_result": {
                "passed": True, "architecture": "x86_64", "off_t_bytes": 8,
                "limit_bytes": gib << 30, "rlimit_soft_bytes": gib << 30, "rlimit_hard_bytes": gib << 30,
                "sigxfsz": "SIG_IGN", "sigpipe": "SIG_DFL", "filesystem_magic": 0xEF53,
                "checks": {name: True for name in primitive_names},
            }} for gib in (2, 6)] + [
                {"name": "log-overflow-group-kill", "status": "passed"},
                {"name": "bound-inputs-unchanged", "status": "passed"},
            ],
        }
        self.records["erofs_fsize_orchestration"] = {"passed": True, "bound_input_bytes_preserved": True}
        for partition, revision in (("vendor", 2), ("odm", 1)):
            self._partition(partition, revision)
        self.rebind()

    def _manifest(self, partition, label, rows):
        raw = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in rows)
        path = self.root / f"{partition}-{label}.jsonl"
        path.write_bytes(raw)
        return {"path": str(path), **identity(raw)}

    def _partition(self, partition, revision):
        role = "erofs_" + partition + "_noop"
        original_hash = identity((partition + " original image identity only").encode())["sha256"]
        rows = metadata_fixture(partition, original_hash)
        rows = [rows[0], by_path(rows, b"/"), by_path(rows, b"/unchanged"), rows[-1]]
        rows[0]["superblock"].update(inode_count=2, feature_compat=7 if partition == "vendor" else 3)
        rows[1].update(nid=1, nlink=2, size_bytes=48, mtime_nsec=0)
        rows[2].update(nid=2, nlink=1, mtime_nsec=0)
        rows[2]["xattrs"].append({"name_hex": b"user.binary".hex(), "value_hex": b"\x00\xff\n=\x80".hex()})
        rows[-1]["entry_count"] = 2
        before = self._manifest(partition, "original", rows)
        self.control["partitions"][partition] = {"manifest": before}
        self.contract["originals"][partition] = {"image": {"sha256": original_hash}}
        image_hash = identity((partition + " raw image identity only").encode())["sha256"]
        after = copy.deepcopy(rows)
        after[0].update(image_size_bytes=16384, image_sha256=image_hash)
        after[0]["superblock"]["root_nid"] = 101
        after[1]["nid"], after[2]["nid"] = 101, 102
        after[-1]["image_sha256"] = image_hash
        self.rows[partition] = {"before": rows, "after": after}
        self.control["noop_manifests"][partition] = [self._manifest(partition, str(n), after) for n in (1, 2)]
        comparison = {
            "entries_compared": 2, "regular_contents_compared": 1, "metadata_exclusions": ["inode.nid"],
            "superblock_physical_exclusions": ["meta_blkaddr", "primary_blocks", "root_nid", "total_blocks", "xattr_blkaddr"],
            "content_replacements": [], "all_semantic_fields_equal": True,
        }
        artifacts = [{
            "image": {"path": f"/synthetic/{partition}-noop-{n}.erofs", "sha256": image_hash, "size_bytes": 16384},
            "tar": {"path": f"/synthetic/{partition}-noop-{n}.tar", **identity(b"synthetic complete TAR identity")},
            "manifest": {"path": f"/synthetic/{partition}-noop-{n}-export.stdout", **policy.identity(selected)},
            "superblock": copy.deepcopy(after[0]["superblock"]), "comparison": copy.deepcopy(comparison),
        } for n, selected in enumerate(self.control["noop_manifests"][partition], 1)]
        checks = [
            {"name": "fresh-original-full-export", "status": "passed", "manifest": policy.identity(before)},
            {"name": "original-structure-data-xattrs", "status": "passed"},
            {"name": "independent-tar-image-manifest-reproducibility", "status": "passed"},
            {"name": "original-tools-runtime-inputs-and-stage-preserved", "status": "passed"},
        ] + [{"name": f"{partition}-noop-{n}-{suffix}", "status": "passed", "comparison": copy.deepcopy(comparison)}
             for n in (1, 2) for suffix in ("structure-data-xattrs", "all-bytes-and-metadata")]
        staging = {"all_paths_checked_without_following_symlinks": 2,
                   "host_metadata_used_as_authority": False, "staging_content_executed": False}
        tools = {name: {"path": "/synthetic/tools/" + name, **pin} for name, pin in self.contract["native_tools"].items()}
        scope = {key: False for key in (
            "policy_adopted", "original_images_written", "source_or_android_output_writes",
            "global_android_output_unchanged_claimed", "complete_rom_admitted", "avb_verified",
            "partition_fit_verified", "retained_kernel_mount_or_boot_verified", "production_policy_writer_admitted", "phone_accessed")}
        scope["raw_" + partition + "_noop_roundtrip_qualified"] = True
        native = self.records[role] = {
            "operation": f"full-original-{partition}-noop-erofs-roundtrip-v{revision}",
            "passed": True, "skipped": 0, "replacements": [], "bound_inputs_preserved": True,
            "checks": checks, "scope": scope, "tools": tools, "artifacts": artifacts,
            "stock_profile": {"entry_count": 2, "superblock": copy.deepcopy(rows[0]["superblock"]),
                **{name: 0 for name in ("hardlink_groups", "empty_xattrs", "nonzero_nanoseconds", "set_id_inodes", "special_inodes")}},
            "prior_synthetic_evidence": {"passed": 11, "failed": 6, "skipped": 0,
                "all_checks_passed": False, "known_empty_xattr_fsck_failures_retained": True},
            "resources": {"effective_cpus": [0], "inherited_allowed_cpus": [0, 1], "nice": 19,
                "whole_job_wall_seconds": 7200, "initial_headroom": {"available_disk_bytes": 48 << 30, "mem_available_bytes": 8 << 30}},
            "staging_before": staging, "staging_after": copy.deepcopy(staging), "commands": [],
        }
        captured = [{"path": "original-export.stdout", **policy.identity(before)}]
        captured += [{"path": f"{partition}-noop-{n}-export.stdout", **policy.identity(row)}
                     for n, row in enumerate(self.control["noop_manifests"][partition], 1)]
        options = ["--tar=f", "--clean=data", "--mkfs-time", "--preserve-mtime", "-T", "1230768000",
                   "-U", "01234567-89ab-cdef-0123-456789abcdef", "-L", "", "-b4096", "-zlz4hc,level=9",
                   "-C4096", "--uid-offset=0", "--workers=0", "--ovlfs-strip=0"]
        if partition == "odm":
            options += ["-E", "^xattr-name-filter"]
        for number in range(24):
            is_mkfs = number >= 22
            logs = {kind: {"path": f"/synthetic/command-{number}.{kind}", **identity(b"")}
                    for kind in ("stdout", "stderr")}
            captured += [{"path": Path(row["path"]).name, **policy.identity(row)} for row in logs.values()]
            native["commands"].append({
                "argv": ([tools["mkfs"]["path"], *options, artifacts[number - 22]["image"]["path"], "/proc/self/fd/4"]
                         if is_mkfs else [tools["fsck"]["path"], "--synthetic-record-only"]),
                "exit_code": 0, "kill_reason": None, "whole_process_group_killed": False, "all_pipes_eof": True,
                "logs": logs, "private_tmpdir": "/synthetic/private-tmp",
                "observed_unlinked_private_spools": [{"size_bytes": 4096, "target": "/synthetic/private-tmp/tmp.1 (deleted)"}],
                "limits": {"file_size_soft_and_hard_bytes": (2 if partition == "vendor" else 6) << 30,
                    "log_cap_each_bytes": 16 << 20, "sampled_rss_ceiling_bytes": 2 << 30, "rss_is_kernel_hard_limit": False,
                    "cpu_soft_seconds": 1800, "cpu_hard_seconds": 1801, "wall_seconds": 1800,
                    "sigxfsz": "SIG_IGN" if is_mkfs else "SIG_DFL", "restore_signals": False},
            })
        self.records[role + "_sandbox"] = {
            "source_out_and_inputs_readonly": True, "uid": 65534, "gid": 65534,
            "capabilities": {name: "0000000000000000" for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")},
            "namespaces": {name: "child:" + name for name in ("mnt", "net", "pid", "user")},
            "parent_namespaces": {name: "parent:" + name for name in ("mnt", "net", "pid", "user")},
            "identity_maps": {name: "65534 0 1\n" for name in ("uid_map", "gid_map")}, "readonly_flag": 1,
            "effective_mount_flags": {name: 1 for name in ("/", "/work", "/work/evolution", "/work/out")},
            "mountinfo_sha256": identity(b"synthetic mount observation")["sha256"],
        }
        self.records[role + "_orchestration"] = {
            "operation": f"root-full-{partition}-noop-orchestration-v{revision}", "passed": True,
            "bound_selected_inputs_unchanged": True, "global_android_output_unchanged_claimed": False,
            "global_build_idle_required": False, "exporter_source": self.contract["exporter_source"],
        }
        self.records[role + "_capture"] = {"files": captured + [
            {"path": f"supervisor-{n}.stdout", **identity(b"inert supervisor record")}
            for n in range(9)]}

    def _record_selector(self, role):
        selected = {"path": str(self.root / (role + ".json")), **identity(policy.json_bytes(self.records[role]))}
        self.control["records"][role] = selected
        return selected

    def rebind(self):
        """Refresh all receipt identities without repairing any semantic claim."""
        probe = self._record_selector("erofs_fsize_probe")
        self.records["erofs_fsize_orchestration"]["native_probe_receipt"] = copy.deepcopy(probe)
        self._record_selector("erofs_fsize_orchestration")
        for partition in ("vendor", "odm"):
            role = "erofs_" + partition + "_noop"
            native, outer, capture = (self.records[role + suffix] for suffix in ("", "_orchestration", "_capture"))
            sandbox = self._record_selector(role + "_sandbox")
            native["sandbox_observation"] = copy.deepcopy(sandbox)
            native["final_artifact_identities"] = [{key: copy.deepcopy(row[key]) for key in ("tar", "image", "manifest")}
                                                    for row in native["artifacts"]]
            outer.update(native_result=copy.deepcopy(native), native_receipt=self._record_selector(role),
                         sandbox_observation=copy.deepcopy(sandbox))
            self._record_selector(role + "_orchestration")
            retained = {row["path"]: row for row in capture["files"]}
            for suffix, name in (("", "receipt.json"), ("_orchestration", "orchestration.json"), ("_sandbox", "sandbox.json")):
                retained[name] = {"path": name, **policy.identity(self.control["records"][role + suffix])}
            capture["files"] = list(retained.values())
            capture["total_bytes"] = sum(row["size_bytes"] for row in capture["files"])
            capture["guest_only_large_artifacts"] = [{"path": Path(row[kind]["path"]).name, **policy.identity(row[kind])}
                                                    for row in native["artifacts"] for kind in ("tar", "image")]
            self._record_selector(role + "_capture")

    def rewrite_after(self, partition, mutation):
        rows = self.rows[partition]["after"]
        mutation(rows)
        role = "erofs_" + partition + "_noop"
        capture = {row["path"]: row for row in self.records[role + "_capture"]["files"]}
        for number in (1, 2):
            selected = self._manifest(partition, str(number), rows)
            self.control["noop_manifests"][partition][number - 1] = selected
            self.records[role]["artifacts"][number - 1]["manifest"].update(policy.identity(selected))
            capture[f"{partition}-noop-{number}-export.stdout"].update(policy.identity(selected))

    def mkfs(self, partition="vendor"):
        return self.records["erofs_" + partition + "_noop"]["commands"][22]

    def qualify(self):
        self.rebind()
        return policy.qualify_noops(self.records, self.contract, self.control)


class NoopQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.counter = 0
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native execution forbidden")))
        self.enterContext(mock.patch("subprocess.run", side_effect=AssertionError("native execution forbidden")))

    def fresh(self):
        self.counter += 1
        return SyntheticNoopEvidence(self.root / str(self.counter))

    def test_full_synthetic_graph_rechecks_four_complete_manifests(self):
        evidence = self.fresh()
        result = evidence.qualify()
        self.assertTrue(result["finite_file_primitive_verified"])
        self.assertFalse(result["native_processes_reexecuted"])
        self.assertFalse(result["policy_replacement_images_qualified"])
        for row in result["partitions"].values():
            self.assertEqual((row["native_checks_passed"], row["skipped"], row["complete_metadata_manifests_rechecked"]), (8, 0, 2))
            self.assertEqual(row["original_entry_count"], 2)
        self.assertEqual(len(list(evidence.root.iterdir())), 6)
        self.assertTrue(all(path.suffix == ".jsonl" for path in evidence.root.iterdir()))

    def test_missing_or_extra_selected_manifest_never_claims_two_rechecks(self):
        for partition in ("vendor", "odm"):
            for count in (0, 1, 3):
                with self.subTest(partition=partition, count=count):
                    evidence = self.fresh()
                    evidence.control["noop_manifests"][partition] = evidence.control["noop_manifests"][partition][:1] * count
                    with self.assertRaisesRegex(policy.PolicyImageError, "two independently rehashed"):
                        evidence.qualify()

    def test_native_primitive_requires_all_eleven_named_checks(self):
        for change in ("empty", "missing", "extra", "false"):
            with self.subTest(change=change):
                evidence = self.fresh()
                checks = evidence.records["erofs_fsize_probe"]["checks"][0]["native_result"]["checks"]
                if change == "empty": checks.clear()
                elif change == "missing": checks.pop("sparse_readback")
                elif change == "extra": checks["unreviewed"] = True
                else: checks["truncate_2tib_rejected"] = False
                with self.assertRaisesRegex(policy.PolicyImageError, "finite-file ABI/limit"):
                    evidence.qualify()

    def test_rehashed_content_xattr_and_mode_changes_still_fail(self):
        mutations = {
            "content": lambda rows: rows[2].update(content_sha256=identity(b"changed!!")["sha256"]),
            "xattr": lambda rows: rows[2]["xattrs"][1].update(value_hex=b"different".hex()),
            "mode": lambda rows: rows[2].update(mode=rows[2]["mode"] ^ 1),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                evidence = self.fresh()
                evidence.rewrite_after("vendor", mutation)
                with self.assertRaisesRegex(policy.PolicyImageError, "inode metadata or content changed"):
                    evidence.qualify()

    def test_rehashed_filesystem_feature_change_is_not_a_physical_exclusion(self):
        evidence = self.fresh()
        evidence.rewrite_after("odm", lambda rows: rows[0]["superblock"].update(feature_compat=7))
        with self.assertRaisesRegex(policy.PolicyImageError, "semantic superblock changed"):
            evidence.qualify()

    def test_repeated_tar_identity_must_match_even_when_all_links_are_rebound(self):
        evidence = self.fresh()
        evidence.records["erofs_vendor_noop"]["artifacts"][1]["tar"]["sha256"] = identity(b"different TAR")["sha256"]
        with self.assertRaisesRegex(policy.PolicyImageError, "independent derivations differ"):
            evidence.qualify()

    def test_scope_cannot_claim_policy_or_boot_admission(self):
        for name in ("policy_adopted", "production_policy_writer_admitted", "retained_kernel_mount_or_boot_verified"):
            with self.subTest(name=name):
                evidence = self.fresh()
                evidence.records["erofs_vendor_noop"]["scope"][name] = True
                with self.assertRaisesRegex(policy.PolicyImageError, "unproved adoption or runtime"):
                    evidence.qualify()

    def test_capability_identity_and_readonly_guards_are_not_receipt_decoration(self):
        mutations = {
            "capability": lambda s: s["capabilities"].update(CapEff="0000000000000001"),
            "missing-cap-set": lambda s: s["capabilities"].pop("CapBnd"),
            "mapping": lambda s: s["identity_maps"].update(uid_map="65534 1000 1\n"),
            "source-writable": lambda s: s["effective_mount_flags"].update({"/work/evolution": 0}),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                evidence = self.fresh()
                mutation(evidence.records["erofs_vendor_noop_sandbox"])
                with self.assertRaisesRegex(policy.PolicyImageError, "capabilities|mapping|protected mounts"):
                    evidence.qualify()

    def test_worker_uuid_and_overlay_recipe_are_exact(self):
        for option, replacement in (("--workers=0", "--workers=1"),
                                    ("01234567-89ab-cdef-0123-456789abcdef", "00000000-0000-0000-0000-000000000000"),
                                    ("--ovlfs-strip=0", "--ovlfs-strip=1")):
            with self.subTest(option=option):
                evidence = self.fresh()
                args = evidence.mkfs()["argv"]
                args[args.index(option)] = replacement
                with self.assertRaisesRegex(policy.PolicyImageError, "recipe differs"):
                    evidence.qualify()

    def test_mkfs_only_ignored_sigxfsz_and_fixed_limits(self):
        for index, key, value in ((22, "sigxfsz", "SIG_DFL"), (0, "sigxfsz", "SIG_IGN"),
                                  (22, "restore_signals", True), (22, "file_size_soft_and_hard_bytes", 3 << 30),
                                  (22, "log_cap_each_bytes", 17 << 20), (22, "sampled_rss_ceiling_bytes", 3 << 30)):
            with self.subTest(index=index, key=key):
                evidence = self.fresh()
                evidence.records["erofs_vendor_noop"]["commands"][index]["limits"][key] = value
                with self.assertRaisesRegex(policy.PolicyImageError, "limits or signal profile changed"):
                    evidence.qualify()

    def test_private_nonempty_unlinked_spool_must_be_observed(self):
        for change in ("absent", "empty", "outside", "linked"):
            with self.subTest(change=change):
                evidence = self.fresh()
                rows = evidence.mkfs()["observed_unlinked_private_spools"]
                if change == "absent": rows.clear()
                elif change == "empty": rows[0]["size_bytes"] = 0
                elif change == "outside": rows[0]["target"] = "/elsewhere/tmp.1 (deleted)"
                else: rows[0]["target"] = "/synthetic/private-tmp/tmp.1"
                with self.assertRaisesRegex(policy.PolicyImageError, "fallback was not observed"):
                    evidence.qualify()



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


def select_provider(fx):
    """Add the provider selection without changing either frozen v12 fixture."""
    published = json.loads(policy.CONTRACT.read_bytes())["profiles"][policy.PROVIDER_PROFILE]
    fx.contract["contract_id"] = fx.control["contract_id"] = policy.PROVIDER_CONTRACT_ID
    for name in ("provider_policy", "sidecar_derivation"):
        fx.contract[name] = copy.deepcopy(published[name])
    existing_paths = {row["path"] for row in fx.contract["dependencies"]}
    for row in published["dependencies"]:
        if row["path"] not in existing_paths:
            fx.contract["dependencies"].append(copy.deepcopy(row))
            fx.write(row["path"], (REAL_ROOT / row["path"]).read_bytes())
    for role in sorted(policy.PROVIDER_RECORD_ROLES - EXPECTED_RECORDS):
        row = fx.write("records/" + role + ".json", policy.json_bytes({"synthetic_record_role": role}))
        fx.control["records"][role] = row
        fx.contract["native_records"][role] = policy.identity(row)
    for name in ("plat", "system_ext", "product"):
        fx.control["policy_files"].pop(name + "_sha256")
    fx.control["noop_manifests"] = {
        name: [copy.deepcopy(fx.control["partitions"][name]["manifest"]) for unused in range(2)]
        for name in ("vendor", "odm")}
    fx.save()


def provider_record(fx, records, role, *, padded_size=None):
    raw = policy.json_bytes(records[role])
    if padded_size is not None:
        assert len(raw) < padded_size
        raw += b" " * (padded_size - len(raw))
    row = fx.write("records/" + role + ".json", raw)
    fx.control["records"][role] = row
    fx.contract["native_records"][role] = policy.identity(row)
    return policy.identity(row)


def bind_provider_sections(fx, records, *names):
    analysis = records["policy_analysis"]
    for name in names or policy.PROVIDER_PROOF_SECTIONS:
        fx.contract["provider_policy"]["proof_sections"][name] = identity(policy.json_bytes(analysis[name]))


def provider_policy_evidence(fx, *, review_size=None):
    """A wholly synthetic v13h graph, including actual bounded record reads.

    Opaque source/action sections contain inert records. Their exact canonical
    identities are still checked; this fixture never claims native execution.
    """
    records, unused = fx.policy_evidence()
    select_provider(fx)
    control = fx.loaded()
    build, analysis = records["policy_build"], records["policy_analysis"]
    pins = fx.contract["provider_policy"]
    pins["baseline"] = identity(b"synthetic reviewed v12 baseline")
    for path, role in (("config/nezha-framework-provider-policy.json", "native_contract"),
                       ("config/nezha-framework-providers.json", "input_contract"),
                       ("scripts/framework_provider_policy.py", "native_policy_tool")):
        pins[role] = identity((fx.root / path).read_bytes())
    build.update(phase="policy-only-v13h-1", provider_phase="v13h-provider-policy-only-runtime-exports-v1",
                 policy_only=True, preservation_verified=True, protected_runtime_outputs_unchanged=True,
                 remaining_build_processes=[], preservation_error=None, protected_runtime_outputs_error=None,
                 post_build_error=None,
                 argv=["build/soong/soong_ui.bash", "--make-mode", "-j8"] + ["synthetic-goal-" + str(i) for i in range(31)])
    for key in ("provider_runtime_requested", "provider_runtime_built", "strict_elf_actions_verified", "images_requested",
                "complete_rom_built", "phone_accessed", "forced_kill_after_timeout"):
        build[key] = False
    analysis.update(operation="verify-native-provider-policy-only-v13h", build_phase=build["phase"],
                    provider_phase=build["provider_phase"], provider_profile_selected=True, policy_only=True,
                    provider_contract_sha256=pins["native_contract"]["sha256"],
                    baseline_receipt_sha256=pins["baseline"]["sha256"])
    for key in ("full_treble_apk_labeling_pass", "policy_compiler_replayed", "source_or_android_output_modified",
                "images_changed", "phone_accessed", "provider_runtime_built", "provider_runtime_installation_verified",
                "strict_elf_actions_verified", "provider_elf_compatibility_verified", "complete_rom_or_runtime_support_proven"):
        analysis[key] = False
    manifest_identity = identity(b"synthetic three-operation fixup manifest")
    commit = {"manifest_sha256": manifest_identity["sha256"], "verified": True,
              "last_event": {"sequence": 8, "operation_count": 3, "event": "commit_verified"}}
    source = {"operation": "verify-v13h-policy-input-sources-after-build", "verified": True,
              "actual_commit": copy.deepcopy(commit), "manifest_identity": manifest_identity,
              "operation_count": 3, "journal_events": 9, "component_trees_checked": 3,
              "unchanged_component_trees_checked": 4, "normal_android_enforcing_required": True,
              "live_outputs_checked": False}
    build.update(provider_fixup_manifest_identity=copy.deepcopy(manifest_identity),
                 provider_fixup_commit=copy.deepcopy(commit), source_history_proof=copy.deepcopy(source),
                 post_build_source_verification=copy.deepcopy(source))
    analysis.update(provider_fixup_manifest_identity=copy.deepcopy(manifest_identity),
                    provider_fixup_commit_identity=identity(policy.json_bytes(commit)),
                    source_history_proof=copy.deepcopy(source))
    analysis["provider_policy_contract_crosspin"] = {
        "verified": True, "actual_native_contract": pins["native_contract"], "actual_input_profile": pins["input_contract"],
        "preserved_semantic_contract": pins["semantic_contract"],
        "only_changed_json_path": ["required_contracts", "provider_inputs", "sha256"],
        "all_other_contract_values_exact": True, "semantic_contract_bytes_replaced": False, "source_or_cil_modified": False}
    analysis["provider_policy_tool_crosspin"] = {
        "verified": True, "actual_native_policy_tool": pins["native_policy_tool"],
        "new_policy_contract": pins["native_contract"], "old_policy_contract": pins["semantic_contract"],
        "all_other_tool_bytes_exact": True, "source_files_modified": False}
    native = analysis["actual_compiler_inputs"]
    before = [{"runtime_path": row["runtime_path"], **policy.identity(row)} for row in native]
    before[2].update(identity(b"synthetic previous system_ext CIL"))
    pins["baseline_corpus_sha256"] = identity(json.dumps(before, sort_keys=True, separators=(",", ":")).encode())["sha256"]
    expected_properties = json.loads((fx.root / "config/nezha-oem-properties.json").read_bytes())["native_effective_ordinary_allow_edges"]
    analysis["semantics"] = {
        "status": "verified", "operation": "actual-v12f-to-v13f-provider-semantic-delta",
        "provider_contract_sha256": pins["semantic_contract"]["sha256"],
        "actual_v12f_baseline_receipt_sha256": pins["baseline"]["sha256"],
        "candidate_input_identities": [{"runtime_path": row["runtime_path"], **policy.identity(row)} for row in native],
        "actual_baseline_input_identities": before, "native_provenance_verified_by_this_module": False,
        "native_actions_contexts_images_or_hardware_verified_by_this_module": False,
        "effect_inventory": {
            "status": "review-required", "operation": "provider-semantic-effect-inventory",
            "native_capture_authenticated": False, "complete_effect_review_admitted": False,
            "contract_projection_matches_candidate_semantics": True, "original_assertions_retained": 6366,
            "assertions_after": 6370, "new_assertions": 4, "new_source_dontaudit_statements": 2,
            "source_additions": {"allow": 26, "dontaudit": 2, "typetransition": 2, "neverallow": 4},
            "all_six_oem_public_mappings_unchanged": True, "helper_effective_property_set_permissions": 0,
            "denial_logging_unchanged": False, "oem_property_ordinary_allow_totals": copy.deepcopy(expected_properties)}}
    records["provider_complete_effect_review"] = {
        "complete_effect_inventory_reviewed": True, "baseline_receipt_sha256": pins["baseline"]["sha256"],
        "baseline_corpus_identity_sha256": pins["baseline_corpus_sha256"],
        "provider_contract_sha256": pins["semantic_contract"]["sha256"],
        "synthetic_complete_inventory": [{"change": "four assertion additions", "count": 4}]}
    review_identity = provider_record(fx, records, "provider_complete_effect_review", padded_size=review_size)
    pins["complete_review_canonical_sha256"] = identity(json.dumps(
        records["provider_complete_effect_review"], sort_keys=True, separators=(",", ":")).encode())["sha256"]
    analysis["complete_effect_review"] = review_identity
    for row in analysis["native_context_checks"] + [analysis["native_oem_check"]]:
        row["build_phase"] = build["phase"]
    oem = analysis["native_oem_check"]
    oem.update(provider_profile_present=True, assertion_statement_counts={"neverallow": 5980, "neverallowx": 390})
    oem["input_binding_proof"]["count"] = 22
    oem["inputs"].extend({"path": "synthetic-provider-input-" + str(i), "resolved_path": "/work/provider/input-" + str(i),
                          **identity(("provider-input-" + str(i)).encode())} for i in range(13))
    producer = {key: copy.deepcopy(oem[key]) for key in (
        "status", "fresh_execution_observed", "build_phase", "build_log_sha256", "mtime_used_to_infer_execution",
        "ninja_success_records", "action_log_line", "action_log_text")}
    producer.update(operation="verify-policy-only-provider-inputs", target="nezha_framework_provider_inputs_check",
                    provider_phase=build["provider_phase"], original_input_count=42, current_reviewed_input_count=42,
                    verified_payload_count=31, unchanged_payload_count=30, derived_payload_count=1, declared_output_count=32,
                    inputs=[{"synthetic_input": i} for i in range(42)],
                    payload_outputs=[{"synthetic_output": i} for i in range(31)], native_receipt_exact_bytes_verified=True,
                    payload_outputs_exact_bytes_verified=True, all_copy_mappings_verified=True, original_inputs_rehashed=True,
                    original_proprietary_inputs_preserved=True,
                    transitive_oem_dependency={"content_dependency_verified": True, "order_only_dependency_used_as_evidence": False},
                    scope={"provider_runtime_built": False, "policy_adopted": False})
    analysis["provider_input_action"] = producer
    records["native_oem_guard"].update(provider_contract_sha256=pins["native_contract"]["sha256"],
                                       assertion_statement_counts={"neverallow": 5980, "neverallowx": 390})
    for role in ("policy_source_manifest", "policy_build_sandbox", "native_oem_guard", "vendor_derivation"):
        provider_record(fx, records, role)
    build["source_manifest"] = policy.identity(fx.control["records"]["policy_source_manifest"])
    oem["output"] = policy.identity(fx.control["records"]["native_oem_guard"])
    receipt_path = control["policy_files"][policy.RUNTIME_INPUTS[7]]["native_path"].removesuffix("vendor_sepolicy.cil") + "receipt.json"
    next(row for row in analysis["input_bindings"] if row["path"] == receipt_path).update(
        policy.identity(fx.control["records"]["vendor_derivation"]))
    provider_record(fx, records, "policy_build")
    for field, role in (("build_result_sha256", "policy_build"), ("build_log_sha256", "policy_build_log"),
                        ("build_source_manifest_sha256", "policy_source_manifest"), ("build_sandbox_sha256", "policy_build_sandbox")):
        analysis[field] = fx.control["records"][role]["sha256"]
    analysis["selection"] = {
        "schema_version": 1, "operation": "admit-actual-v13h-policy-only-analysis",
        "source_and_history_verification_required": True, "build_record_identity": policy.identity(fx.control["records"]["policy_build"]),
        "phase": build["phase"], "provider_phase": build["provider_phase"], "argv": copy.deepcopy(build["argv"]),
        "provider_fixup_manifest_identity": copy.deepcopy(manifest_identity),
        "provider_fixup_commit_identity": identity(policy.json_bytes(commit)), "complete_effect_review": copy.deepcopy(review_identity),
        "baseline_receipt": copy.deepcopy(pins["baseline"])}
    for name in policy.PROVIDER_PROOF_SECTIONS:
        analysis.setdefault(name, {"synthetic_pinned_section": name})
    bind_provider_sections(fx, records)
    provider_record(fx, records, "policy_analysis")
    fx.save()
    control = fx.loaded()
    sidecars, unused = sidecar_evidence(fx, control)

    def current(value):
        if isinstance(value, dict):
            return {current(key): current(child) for key, child in value.items()}
        if isinstance(value, list):
            return [current(child) for child in value]
        if isinstance(value, str):
            return (value.replace("policy-sidecar-native-v", "policy-sidecar-v13h-native-v")
                    .replace("derive-export4-policy-sidecars-native-v1", "derive-v13h-policy-sidecars-native-v1")
                    .replace("root-policy-sidecar-native-orchestration-v1", "root-policy-sidecar-v13h-native-orchestration-v1")
                    .replace("verify-native-oem-properties-v12f-export4", "verify-native-provider-policy-only-v13h")
                    .replace("derived-from-sealed-export4-inputs", "derived-from-sealed-v13h-inputs"))
        return value

    records.update(current(sidecars))
    native_sidecar, outer = records["sidecar_native_validation"], records["sidecar_orchestration"]
    provider_record(fx, records, "sidecar_source_capture")
    provider_record(fx, records, "sidecar_sandbox")
    native_sidecar["source_capture"] = policy.identity(fx.control["records"]["sidecar_source_capture"])
    native_sidecar["sandbox"] = policy.identity(fx.control["records"]["sidecar_sandbox"])
    outer["sandbox_observation"] = copy.deepcopy(native_sidecar["sandbox"])
    outer["native_result"] = native_sidecar
    provider_record(fx, records, "sidecar_native_validation")
    outer["native_receipt"] = policy.identity(fx.control["records"]["sidecar_native_validation"])
    provider_record(fx, records, "sidecar_orchestration")
    fx.save()
    return records, fx.loaded()


class ProviderContractTests(OfflineTests):
    def test_additive_provider_catalog_preserves_both_prior_canonical_contracts(self):
        catalog = json.loads(policy.CONTRACT.read_bytes())
        self.assertEqual({policy.HISTORICAL_PROFILE, policy.EXPORT4_PROFILE, policy.PROVIDER_PROFILE}, set(catalog["profiles"]))
        for name, expected in ((policy.HISTORICAL_PROFILE, "0a549e0374f17fcd24e25dba668bbe745750968bc1336c7c142583fac1816cc4"),
                               (policy.EXPORT4_PROFILE, "5c7e020cbf2101bc6ed5af412f1e667d41e75e3259547c0700090d2d1f10ffb4")):
            self.assertEqual(expected, identity(policy.json_bytes(catalog["profiles"][name]))["sha256"])
        self.assertEqual(policy.HISTORICAL_PROFILE, policy.plan()["profile"])
        current = policy.plan(policy.PROVIDER_PROFILE)
        self.assertEqual(policy.PROVIDER_CONTRACT_ID, current["contract_id"])
        self.assertEqual(policy.PROVIDER_PROFILE, current["profile"])
        self.assertFalse(current["images_or_policy_inputs_opened"])
        self.assert_boundaries(current)
        blocked = bool(current["missing_reviewed_native_record_pins"]) or policy.PROFILE_CONTRACT_SHA256[policy.PROVIDER_PROFILE] is None
        self.assertEqual("blocked" if blocked else "ready_for_evidence_validation", current["status"])

    def test_missing_provider_native_pin_stops_before_control_reads(self):
        contract, digest, profile, helper = policy.load_contract(policy.PROVIDER_PROFILE)
        contract["native_records"]["sidecar_native_validation"] = None
        with mock.patch.object(policy, "load_contract", return_value=(contract, digest, profile, helper)):
            with mock.patch.object(policy, "load_control", side_effect=AssertionError("private selection must stay unopened")) as selected:
                with self.assertRaisesRegex(ValueError, "native evidence pins"):
                    policy.prepare(Path("/nonexistent/provider-control"), "a" * 64,
                                   output_dir=Path("/nonexistent/output"), selected_profile=policy.PROVIDER_PROFILE)
        selected.assert_not_called()


class ProviderRecordLimitTests(OfflineTests):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="provider-record-limit-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def record(self, size):
        raw = b'{"synthetic":true}\n'
        raw += b" " * (size - len(raw))
        path = self.root / "bounded-evidence.json"
        path.write_bytes(raw)
        return {"path": path, **identity(raw)}

    def test_only_two_provider_roles_receive_the_larger_json_limit(self):
        self.assertEqual(8 << 20, policy.TEXT)
        for profile in (policy.CONTRACT_ID, policy.EXPORT4_CONTRACT_ID, policy.PROVIDER_CONTRACT_ID):
            for role in policy.PROVIDER_RECORD_ROLES:
                with self.subTest(profile=profile, role=role):
                    large = profile == policy.PROVIDER_CONTRACT_ID and role in {"policy_analysis", "provider_complete_effect_review"}
                    self.assertEqual(16 << 20 if large else 8 << 20, policy.record_json_limit({"contract_id": profile}, role))

    def test_named_roles_accept_valid_json_through_16mib_but_reject_one_more_byte(self):
        for size in ((8 << 20) + 1, 16 << 20, (16 << 20) + 1):
            row = self.record(size)
            for role in ("policy_analysis", "provider_complete_effect_review"):
                with self.subTest(size=size, role=role):
                    control = {"contract_id": policy.PROVIDER_CONTRACT_ID, "records": {role: row}}
                    if size <= 16 << 20:
                        self.assertEqual({role: {"synthetic": True}}, policy.read_records(control))
                    else:
                        with self.assertRaises(ValueError):
                            policy.read_records(control)

    def test_ordinary_records_and_default_control_reader_keep_the_original_8mib_cap(self):
        row = self.record(8 << 20)
        self.assertEqual({"synthetic": True}, policy.read_json(row["path"])[0])
        row = self.record((8 << 20) + 1)
        for contract_id, role in ((policy.CONTRACT_ID, "policy_analysis"), (policy.EXPORT4_CONTRACT_ID, "policy_analysis"),
                                 (policy.PROVIDER_CONTRACT_ID, "native_oem_guard"), (policy.PROVIDER_CONTRACT_ID, "sidecar_native_validation")):
            with self.subTest(contract_id=contract_id, role=role):
                with self.assertRaises(ValueError):
                    policy.read_records({"contract_id": contract_id, "records": {role: row}})
        with self.assertRaises(ValueError):
            policy.read_json(row["path"])
        with self.assertRaises(ValueError):
            policy.load_control(row["path"], row["sha256"], {}, "b" * 64)


class ProviderPolicyTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.records, self.control = provider_policy_evidence(self.fx)
        self.enterContext(mock.patch.object(policy, "ROOT", self.root))

    def qualify(self):
        return policy.qualify_policy(self.records, self.control, self.fx.contract)

    def test_provider_selection_has_thirty_records_eleven_artifacts_and_full_proof(self):
        self.assertEqual(30, len(self.control["records"]))
        self.assertEqual({*policy.RUNTIME_INPUTS, "combined"}, set(self.control["policy_files"]))
        replacements, proof = self.qualify()
        self.assertEqual((6366, 4, 6370), tuple(proof[key] for key in
                         ("assertion_statements_retained", "assertion_statements_added", "assertion_statements_total")))
        self.assertTrue(proof["provider_profile_selected"])
        self.assertTrue(proof["complete_native_provider_proof_sections_bound"])
        self.assertTrue(proof["complete_effect_review_bound"])
        self.assertEqual(policy.metadata.REPLACEMENT_PATHS, {name: set(rows) for name, rows in replacements.items()})
        self.assertEqual("sealed-v13h-CIL-and-mapping", proof["sidecar_derivation"]["derivation_kind"])
        for key in ("native_policy_reexecuted", "provider_runtime_support_proven", "full_treble_apk_labeling_proven",
                    "sidecars_observed_at_native_install_paths", "current_active_source_compatibility_proven"):
            self.assertFalse(proof[key], key)

    def test_missing_review_or_old_control_cannot_select_provider_profile(self):
        original = copy.deepcopy(self.fx.control)
        for change in (lambda: self.fx.control["records"].pop("provider_complete_effect_review"),
                       lambda: self.fx.control.update(contract_id=policy.EXPORT4_CONTRACT_ID),
                       lambda: self.fx.control["policy_files"].update(plat_sha256=copy.deepcopy(self.fx.control["policy_files"]["combined"]))):
            self.fx.control = copy.deepcopy(original)
            change()
            self.fx.save()
            with self.assertRaises(ValueError):
                self.fx.loaded()

    def test_provider_flag_policy_only_and_runtime_boundaries_are_enforced(self):
        analysis = self.records["policy_analysis"]
        for key, value in (("provider_profile_selected", False), ("policy_only", False),
                           ("provider_runtime_built", True), ("images_changed", True), ("strict_elf_actions_verified", True)):
            with self.subTest(key=key):
                old = analysis[key]
                analysis[key] = value
                with self.assertRaisesRegex(ValueError, "analysis is incomplete|unsupported scope"):
                    self.qualify()
                analysis[key] = old

    def test_same_total_cannot_hide_changed_retained_or_added_assertions(self):
        impact = self.records["policy_analysis"]["semantics"]["effect_inventory"]
        impact.update(original_assertions_retained=6365, new_assertions=5)
        self.assertEqual(6370, impact["assertions_after"])
        with self.assertRaisesRegex(ValueError, "complete v13h proof changed: semantics"):
            self.qualify()
        bind_provider_sections(self.fx, self.records, "semantics")
        with self.assertRaisesRegex(ValueError, "provider assertions"):
            self.qualify()

    def test_rehashed_source_history_must_still_match_the_selected_installation(self):
        analysis = self.records["policy_analysis"]
        source = analysis["source_history_proof"]
        source["manifest_identity"] = identity(b"another internally consistent installation")
        build = self.records["policy_build"]
        build["source_history_proof"] = copy.deepcopy(source)
        build["post_build_source_verification"] = copy.deepcopy(source)
        bind_provider_sections(self.fx, self.records, "source_history_proof")
        with self.assertRaisesRegex(ValueError, "source/history proof differs"):
            self.qualify()

    def test_rehashed_contract_crosspin_cannot_replace_the_preserved_semantic_contract(self):
        cross = self.records["policy_analysis"]["provider_policy_contract_crosspin"]
        cross["preserved_semantic_contract"] = identity(b"unreviewed semantic contract")
        bind_provider_sections(self.fx, self.records, "provider_policy_contract_crosspin")
        with self.assertRaisesRegex(ValueError, "contract crosspin differs"):
            self.qualify()

    def test_internally_rehashed_complete_review_cannot_claim_another_baseline(self):
        review = self.records["provider_complete_effect_review"]
        review["baseline_receipt_sha256"] = "a" * 64
        selected = provider_record(self.fx, self.records, "provider_complete_effect_review")
        self.control["records"]["provider_complete_effect_review"].update(selected)
        self.records["policy_analysis"]["complete_effect_review"] = selected
        self.records["policy_analysis"]["selection"]["complete_effect_review"] = copy.deepcopy(selected)
        self.fx.contract["provider_policy"]["complete_review_canonical_sha256"] = identity(
            json.dumps(review, sort_keys=True, separators=(",", ":")).encode())["sha256"]
        bind_provider_sections(self.fx, self.records, "selection")
        with self.assertRaisesRegex(ValueError, "complete provider effect review"):
            self.qualify()

    def test_rehashed_producer_section_requires_all_retained_inputs_and_payloads(self):
        producer = self.records["policy_analysis"]["provider_input_action"]
        producer["payload_outputs"].pop()
        bind_provider_sections(self.fx, self.records, "provider_input_action")
        with self.assertRaisesRegex(ValueError, "fresh provider producer"):
            self.qualify()

    def test_rehashed_context_proof_cannot_use_another_combined_binary(self):
        check = self.records["policy_analysis"]["native_context_checks"][0]
        check["inputs"][0]["sha256"] = "b" * 64
        bind_provider_sections(self.fx, self.records, "native_context_checks")
        with self.assertRaisesRegex(ValueError, "context check used a different combined"):
            self.qualify()

    def test_valid_export4_sidecar_bytes_do_not_substitute_for_fresh_provider_evidence(self):
        native = self.records["sidecar_native_validation"]
        native["operation"] = "derive-export4-policy-sidecars-native-v1"
        with self.assertRaisesRegex(ValueError, "derived-sidecar validation is incomplete"):
            self.qualify()
        native["operation"] = "derive-v13h-policy-sidecars-native-v1"
        native["baseline"]["operation"] = "verify-native-oem-properties-v12f-export4"
        with self.assertRaisesRegex(ValueError, "selected policy binding differs"):
            self.qualify()


class ProviderPreparationTests(FixtureTests):
    def setUp(self):
        super().setUp()
        self.records, unused = provider_policy_evidence(self.fx, review_size=(8 << 20) + 1)
        self.enterContext(mock.patch.object(policy, "ROOT", self.root))
        self.enterContext(mock.patch.object(policy, "load_contract", return_value=(
            self.fx.contract, self.fx.contract_sha, self.fx.profile, self.fx.helper)))
        self.enterContext(mock.patch.dict(policy.PROFILE_CONTRACT_SHA256, {policy.PROVIDER_PROFILE: self.fx.contract_sha}))
        self.enterContext(mock.patch.object(policy, "qualify_erofs", return_value={"synthetic_native_evidence_mock": True}))
        self.enterContext(mock.patch.object(policy.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(1 << 40, 0, 1 << 40)))

    def prepare(self):
        return policy.prepare(self.fx.path, self.fx.sha, output_dir=self.fx.output, selected_profile=policy.PROVIDER_PROFILE)

    def test_large_review_prepares_with_real_record_reads_and_provider_qualifier(self):
        report = self.prepare()
        self.assertEqual(policy.PROVIDER_PROFILE, report["profile"])
        self.assertEqual(6370, report["policy_proof"]["assertion_statements_total"])
        self.assertEqual((8 << 20) + 1, report["native_evidence"]["provider_complete_effect_review"]["size_bytes"])
        self.assert_boundaries(report)
        self.assertEqual(3, len(report["derived_sidecars"]))
        for row in report["derived_sidecars"]:
            self.assertFalse(row["native_installed_output_claimed"])
            self.assertEqual(65, (self.fx.output / row["path"]).stat().st_size)

    def test_same_size_large_review_mutation_after_fourth_assembly_blocks_success(self):
        assemble = self.fx.helper.assemble
        calls = 0
        mutated = False

        def mutate_after_last(*args):
            nonlocal calls, mutated
            result = assemble(*args)
            calls += 1
            if calls == 4:
                path = self.root / self.fx.control["records"]["provider_complete_effect_review"]["path"]
                raw = path.read_bytes()
                self.assertEqual((8 << 20) + 1, len(raw))
                path.write_bytes(raw[:-1] + b"\n")
                mutated = True
            return result

        with mock.patch.object(self.fx.helper, "assemble", side_effect=mutate_after_last):
            with self.assertRaisesRegex(ValueError, "JSON evidence identity differs"):
                self.prepare()
        self.assertEqual(4, calls)
        self.assertTrue(mutated)
        self.assertFalse((self.fx.output / "preparation.json").exists())


if __name__ == "__main__":
    unittest.main()
