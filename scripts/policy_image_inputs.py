#!/usr/bin/env python3
"""Prepare the exact five Nezha policy replacements as two complete TAR sets.

This host command does not extract a filesystem or run a native image writer.
It requires reviewed native evidence, complete metadata exports and all regular
file bytes, then preserves their metadata through the pinned full-TAR helper.
Raw EROFS construction, metadata comparison, FEC, AVB and adoption remain gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import types

sys.dont_write_bytecode = True
if __package__:
    from . import avb_image_set as avb
    from . import erofs_metadata as metadata
    from . import twrp_working as io
else:
    import avb_image_set as avb
    import erofs_metadata as metadata
    import twrp_working as io

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-policy-images.json"
CONTRACT_ID = "nezha-five-file-policy-image-inputs-v1"
TEXT = 8 << 20
POLICY = 64 << 20
RESERVE = 2 << 30
PRODUCTION_PROFILE = {
    "schema_version": 1, "native_execution_qualified": False,
    "mkfs_fsize_soft_and_hard_bytes": {"vendor": 2 << 30, "odm": 6 << 30},
    "scratch_alignment_max_bytes": 65536, "construction_allowance_bytes": 128 << 20,
    "minimum_additional_free_bytes": 48 << 30, "reserve_bytes": RESERVE,
    "regular_capture_max_file_bytes": 512 << 20, "regular_capture_max_batch_bytes": 2 << 30,
    "log_limit_per_stream_bytes": 16 << 20, "metadata_output_limit_bytes": 128 << 20,
    "sequential_native_processes": True, "private_persistent_ext4_tmpdir_required": True,
    "fsize_signal_offset_and_log_overflow_probes_required": True,
    "bounded_parent_pipe_capture_required": True, "original_image_copies_required": False,
}
PARTITIONS = frozenset(("vendor", "odm"))
RECORD_ROLES = frozenset(("erofs_build", "erofs_source_manifest", "erofs_tools", "erofs_shared",
    "erofs_synthetic", "erofs_stock", "erofs_writer", "erofs_writer_orchestration", "policy_build",
    "policy_analysis", "vendor_derivation", "policy_build_log", "policy_source_manifest", "policy_build_sandbox",
    "native_oem_guard"))
RUNTIME_INPUTS = (
    "/system/etc/selinux/plat_sepolicy.cil", "/system/etc/selinux/mapping/202504.cil",
    "/system_ext/etc/selinux/system_ext_sepolicy.cil", "/system_ext/etc/selinux/mapping/202504.cil",
    "/product/etc/selinux/product_sepolicy.cil", "/product/etc/selinux/mapping/202504.cil",
    "/vendor/etc/selinux/plat_pub_versioned.cil", "/vendor/etc/selinux/vendor_sepolicy.cil",
    "/odm/etc/selinux/odm_sepolicy.cil", "/system/etc/selinux/plat_sepolicy_genfs_202504.cil")
COMBINED_SUFFIX = "/soong/.intermediates/vendor/xiaomi/nezha-policy/nezha_factory_precompiled_sepolicy/android_common/nezha_factory_precompiled_sepolicy"
VENDOR_SUFFIX = "/soong/.intermediates/vendor/xiaomi/nezha-policy/nezha_factory_vendor_policy/gen/derived/vendor_sepolicy.cil"
CONTEXT_TARGETS = frozenset("nezha_factory_" + name for name in (
    "file_contexts_test", "property_contexts_test", "hwservice_contexts_test", "service_contexts_test",
    "vndservice_contexts_test", "seapp_contexts_checked", "platform_seapp_contexts_checked",
    "sepolicy_test", "dev_type_test"))
BOUNDARIES = {"native_tools_executed": False, "filesystem_extracted": False, "raw_erofs_built": False,
    "hashtree_or_fec_regenerated": False, "avb_signed": False, "source_or_vendor_inputs_adopted": False,
    "complete_rom_ready": False, "phone_accessed": False, "guest_accessed": False}


class PolicyImageError(ValueError):
    """A required evidence, identity or scope guard was not satisfied."""


def require(ok, message):
    if not ok:
        raise PolicyImageError(message)


def identity(value):
    return {key: value[key] for key in ("sha256", "size_bytes")}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def read_json(path, expected=None):
    # Do not buffer an accidentally selected PEM payload as a JSON input.
    with avb._input(path, TEXT) as (stream, st):
        prefix = bytearray()
        while len(prefix) < min(st.st_size, 4096):
            byte = stream.read(1)
            prefix.extend(byte)
            if byte not in (b" ", b"\r", b"\n", b"\t"):
                break
        require(prefix[-1:] in (b"{", b"["), "expected JSON evidence")
        raw = bytes(prefix) + stream.read(st.st_size + 1)
        require(len(raw) == st.st_size, "JSON input changed length")
    if expected is not None:
        require(avb._identity(raw) == identity(expected), "JSON evidence identity differs")
    return avb._json(raw), raw


def load_contract():
    c, raw = read_json(CONTRACT)
    avb._keys(c, ("schema_version", "contract_id", "device", "platform", "factory_package_sha256", "originals",
        "dependencies", "erofs_revision", "exporter_source", "native_driver_sha256", "shared_driver_sha256",
        "writer_driver_sha256", "native_records", "native_tools", "production_execution_profile", "admitted_metadata",
        "output_root", "independent_tar_passes", "limits"), "policy-image contract")
    require(c["schema_version"] == 1 and type(c["schema_version"]) is int
            and c["contract_id"] == CONTRACT_ID and c["device"] == "nezha"
            and c["platform"] == {"branch": "bka", "release_config": "bp4a", "board_api": "202504"},
            "unsupported policy-image contract")
    require(set(c["originals"]) == PARTITIONS and set(c["native_records"]) == RECORD_ROLES
            and c["independent_tar_passes"] == 2 and type(c["independent_tar_passes"]) is int
            and c["output_root"] == "artifacts/policy-images/nezha" and json_bytes(c["limits"]) == json_bytes(BOUNDARIES),
            "policy-image scope or evidence coverage changed")
    require(c["admitted_metadata"] == {"superblock_nanoseconds": 0, "inode_nanoseconds": 0,
            "compatible_features": [3, 7], "incompatible_features": 1, "compression_algorithms": 1,
            "empty_xattr_values": False}, "unqualified metadata capability")
    require(json_bytes(c["production_execution_profile"]) == json_bytes(PRODUCTION_PROFILE),
            "production construction limits changed without a new reviewed profile")
    require(c["erofs_revision"] == "2c190a73fceb29f00da0558e44bb88ce19ec5bf4"
            and c["exporter_source"]["sha256"] == "89d60827a44c1c808b8c9bb6f180b28aeaa0e440ff7180856e9c16180cab06b3",
            "EROFS source selection changed")
    paths = set()
    for row in c["dependencies"] + [c["exporter_source"]]:
        avb._identity_spec(row, path=True)
        require(row["path"] not in paths and not Path(row["path"]).is_absolute()
                and ".." not in Path(row["path"]).parts, "duplicate or unsafe source dependency")
        paths.add(row["path"])
        avb._small(ROOT / row["path"], TEXT, row)
    required = {"tools/erofs-metadata/full_tar.py", "scripts/erofs_metadata.py", "scripts/avb_image_set.py",
                "scripts/twrp_working.py", "scripts/inspect_twrp_image.py", "config/nezha-avb-image-set.json",
                "config/vendor-policy-correction.json", "tools/erofs-metadata/erofs_metadata.c",
                "research/factory-framework-contract.json", "config/nezha-oem-policy.json", "config/nezha-oem-properties.json"}
    require(paths == required, "implementation source pins are incomplete")
    profile, profile_sha = avb.load_profile()
    require(profile_sha == "14f58671ecd15a1913ba5e1dd7767d0ebf163fd02d30f7fb4130e734790f3567",
            "immutable AVB image-set profile changed")
    factory, _ = read_json(ROOT / "research/factory-firmware-validation.json")
    require(c["factory_package_sha256"] == factory["package"]["sha256"], "factory package selection differs")
    factory_images = {row["partition"].removesuffix("_a"): identity(row)
                      for row in factory["logical_partitions"]["outputs"]}
    factory_policy, _ = read_json(ROOT / "research/factory-framework-contract.json")
    old_members = {row["runtime_path"]: {"sha256": row["factory_sha256"], "size_bytes": row["factory_size_bytes"]}
                   for row in factory_policy["factory_policy"]["comparison"]["files"]}
    correction, _ = read_json(ROOT / "config/vendor-policy-correction.json")
    old_members.update({row["runtime_path"]: identity(row) for row in correction["inputs"] if row["runtime_path"].startswith("/vendor/")})
    for name in PARTITIONS:
        row = c["originals"][name]
        avb._identity_spec(row["image"])
        require(row["image"] == factory_images[name], "factory image provenance differs")
        require(row["image"]["size_bytes"] == profile["image_budgets"][name], "partition package budget differs")
        require(set(row["replacements"]) == metadata.REPLACEMENT_PATHS[name], "five replacement paths changed")
        for path, member in row["replacements"].items():
            avb._identity_spec(member)
            require(member == old_members["/" + name + path], "factory policy preimage provenance differs")
    for row in c["native_records"].values():
        if row is not None:
            avb._identity_spec(row)
    require(set(c["native_tools"]) == {"mkfs", "fsck", "exporter", "metadata_checker"}, "native tool role pins differ")
    for row in c["native_tools"].values():
        avb._identity_spec(row)
    helper_row = next(row for row in c["dependencies"] if row["path"] == "tools/erofs-metadata/full_tar.py")
    require(helper_row["sha256"] == "ec487d93ea158fab7022f427793839211978790f01dbcfc9361a63b02b681daa",
            "full-TAR helper is not the byte-identical qualified candidate")
    helper_raw = avb._small(ROOT / helper_row["path"], TEXT, helper_row)
    helper = types.ModuleType("nezha_bound_full_tar")
    helper.__file__ = str(ROOT / helper_row["path"])
    exec(compile(helper_raw, helper.__file__, "exec"), helper.__dict__)
    return c, avb._sha(raw), profile, helper


def plan():
    c, digest, _, _ = load_contract()
    return {"schema_version": 1, "operation": "plan-nezha-policy-image-inputs", "contract_sha256": digest,
        "status": "blocked" if any(row is None for row in c["native_records"].values()) else "ready_for_evidence_validation",
        "missing_reviewed_native_record_pins": sorted(name for name, row in c["native_records"].items() if row is None),
        "required_replacements": {name: sorted(metadata.REPLACEMENT_PATHS[name]) for name in sorted(PARTITIONS)},
        "two_complete_tar_passes_required": True, "production_writer_admitted": False,
        "missing_production_execution_profile": c["production_execution_profile"] is None,
        "images_or_policy_inputs_opened": False, **BOUNDARIES}


def load_control(path, expected_sha, contract, contract_sha):
    avb._digest(expected_sha)
    path = avb.envelope._absolute_path(path)
    value, raw = read_json(path)
    require(avb._sha(raw) == expected_sha, "input control digest differs")
    avb._keys(value, ("schema_version", "contract_id", "contract_sha256", "artifact_set_id",
                      "records", "partitions", "policy_files"), "policy image inputs")
    require(value["schema_version"] == 1 and type(value["schema_version"]) is int
            and value["contract_id"] == CONTRACT_ID and value["contract_sha256"] == contract_sha
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value["artifact_set_id"]), "input contract differs")
    require(type(value["records"]) is dict and type(value["partitions"]) is dict
            and set(value["records"]) == RECORD_ROLES and set(value["partitions"]) == PARTITIONS,
            "missing or extra native evidence/partition")
    def selected(row, native=False):
        if native:
            avb._keys(row, ("path", "sha256", "size_bytes", "native_path"), "policy artifact")
            require(type(row["native_path"]) is str and row["native_path"].startswith("/")
                    and row["native_path"] == os.path.normpath(row["native_path"]), "noncanonical native producer")
            avb._identity_spec({key: row[key] for key in ("path", "sha256", "size_bytes")}, path=True)
        else:
            avb._identity_spec(row, path=True)
        row["path"] = avb.envelope._absolute_path(path.parent / row["path"])
    for name, row in value["records"].items():
        selected(row)
        require(contract["native_records"][name] is not None
                and identity(row) == contract["native_records"][name], "native record is not reviewed and pinned: " + name)
    expected_roles = {*RUNTIME_INPUTS, "combined", "plat_sha256", "system_ext_sha256", "product_sha256"}
    require(type(value["policy_files"]) is dict and set(value["policy_files"]) == expected_roles,
            "policy/compiler/hash-file coverage differs")
    for row in value["policy_files"].values():
        selected(row, True)
        require(row["size_bytes"] <= POLICY, "policy artifact exceeds bound")
    for name, row in value["partitions"].items():
        avb._keys(row, ("image", "manifest", "staging_root"), "partition input")
        selected(row["image"]); selected(row["manifest"])
        require(identity(row["image"]) == contract["originals"][name]["image"], "original factory image differs")
        require(type(row["staging_root"]) is str, "invalid regular-byte staging root")
        row["staging_root"] = avb.envelope._absolute_path(path.parent / row["staging_root"])
    roots = [value["partitions"][name]["staging_root"] for name in sorted(PARTITIONS)]
    require(not roots[0].is_relative_to(roots[1]) and not roots[1].is_relative_to(roots[0]),
            "partition regular-byte staging roots must be separate, not shared or nested")
    return value, raw


def read_records(control):
    result = {}
    for name, row in control["records"].items():
        if name == "policy_build_log":
            avb._small(row["path"], 256 << 20, row)
        else:
            result[name] = read_json(row["path"], row)[0]
    return result


def _build(record):
    require(record["build_passed"] is True and record["native_sandbox_verified"] is True
            and record["source_inputs_unchanged"] is True and record["exit_code"] == 0
            and type(record["exit_code"]) is int and record["timed_out"] is False
            and record["sandbox_fallback"] is False and record["actual_ninja_sandbox_observed"] is True
            and record["target_product"] == "lineage_nezha" and record["target_release"] == "bp4a"
            and record["variant"] == "user", "native source build did not satisfy the enforcing user gate")


def _checks(record, operation, required, *, allowed_failures=()):
    require(record["operation"] == operation and record["skipped"] == 0 and type(record["skipped"]) is int
            and record["boundaries"]["native_processes_executed"] is True,
            "native qualification was skipped or is the wrong operation")
    rows = record["checks"]
    require(type(rows) is list and all(type(row) is dict for row in rows)
            and len({row["name"] for row in rows}) == len(rows), "duplicate native check names")
    by_name = {row["name"]: row for row in rows}
    require(set(required) <= set(by_name) and all(by_name[n]["status"] == "passed" for n in required),
            "required native qualification check is absent or failed")
    failures = {row["name"] for row in rows if row["status"] == "failed"}
    require(all(row["status"] in {"passed", "failed"} for row in rows)
            and failures <= set(allowed_failures)
            and type(record["failed"]) is int and type(record["passed"]) is int
            and record["failed"] == len(failures) and record["passed"] == len(rows) - len(failures)
            and record["all_checks_passed"] is (not failures), "native failures are unreviewed or miscounted")
    return by_name, sorted(failures)


def qualify_erofs(records, contract, control):
    _build(records["erofs_build"])
    require(identity(records["erofs_build"]["source_manifest"]) == identity(control["records"]["erofs_source_manifest"]),
            "EROFS build source capture differs")
    sources = records["erofs_source_manifest"]
    require(type(sources) is list, "native EROFS source capture must enumerate actual files")
    exporter_sources = [r for r in sources if r["path"].endswith("/tools/nezha-erofs-metadata/erofs_metadata.c")]
    require(len(exporter_sources) == 1 and identity(exporter_sources[0]) == identity(contract["exporter_source"])
            and "nezha_erofs_metadata" in records["erofs_build"]["argv"], "native exporter source/build linkage differs")
    lock = records["erofs_tools"]
    require(lock["schema_version"] == 1 and lock["expected_erofs_utils_revision"] == contract["erofs_revision"]
            and lock["expected_exporter_source_sha256"] == contract["exporter_source"]["sha256"]
            and lock["build_provenance_verified_by_this_capture"] is False
            and set(lock["tools"]) == {"mkfs", "fsck", "exporter", "metadata_checker"}, "native tools lock differs")
    require({name: identity(row) for name, row in lock["tools"].items()} == contract["native_tools"],
            "native binary identities differ from the reviewed build/qualification pins")
    helper_pin = next(row for row in contract["dependencies"] if row["path"] == "scripts/erofs_metadata.py")
    require(identity(lock["tools"]["metadata_checker"]) == identity(helper_pin), "native metadata checker differs")
    for role in ("erofs_shared", "erofs_synthetic", "erofs_stock", "erofs_writer"):
        record = records[role]
        other = record["tools"]
        require({k: v for k, v in other.items() if k != "tools"} == {k: v for k, v in lock.items() if k != "tools"}
                and set(other["tools"]) == set(lock["tools"])
                and all(identity(other["tools"][n]) == identity(lock["tools"][n]) for n in lock["tools"])
                and record["driver"]["sha256"] == contract["native_driver_sha256"],
                "qualification used different tools or native driver")
        require(record["exporter_checks_passed"] is True, "native exporter qualification failed")
    shared = {"native-versions", "literal-shared-base-zero", "shared-id-at-eof", "shared-entry-crosses-eof",
              "shared-reserved-byte", "shared-shared-count-over-body", "original-fixture-preserved", "tools-stable"}
    _checks(records["erofs_shared"], "synthetic-block-zero-shared-xattr-qualification", shared)
    require(records["erofs_shared"]["controls"]["qualification_driver"]["sha256"] == contract["shared_driver_sha256"],
            "shared-xattr qualification source differs")
    _, synthetic_failures = _checks(records["erofs_synthetic"], "synthetic-native-validation",
        {"native-versions", "deterministic-flat-rebuild", "exporter-reads-nanoseconds-independently",
         "detect-capability-change", "detect-selinux-nul-change", "detect-unselected-content-change", "tools-stable"},
        allowed_failures={"writer-preserves-nanoseconds", "upstream-fsck-empty-xattr-compatibility"})
    stock, _ = _checks(records["erofs_stock"], "read-only-stock-metadata-validation",
        {"native-versions", "stock-vendor", "stock-odm", "stock-vendor-fsck-xattrs", "stock-odm-fsck-xattrs", "tools-stable"})
    required_writer = {"native-versions", "vendor-seed-qualification", "odm-seed-qualification",
        "vendor-writer-1-roundtrip", "vendor-writer-2-roundtrip", "odm-writer-1-roundtrip", "odm-writer-2-roundtrip",
        "required-native-export-qualification", "both-partitions-reproducible-exact-five-changes",
        "all-bound-inputs-unchanged", "tools-stable"}
    writer, writer_failures = _checks(records["erofs_writer"], "synthetic-manifest-policy-writer-roundtrip-v3",
        required_writer, allowed_failures={p + "-writer-" + str(n) + "-upstream-xattrs" for p in PARTITIONS for n in (1, 2)}
        | {p + "-seed-upstream-xattrs" for p in PARTITIONS})
    controls = records["erofs_writer"]["controls"]
    require(controls["writer_roundtrip_checks_passed"] is True
            and controls["wrapper_driver"]["sha256"] == contract["writer_driver_sha256"]
            and controls["known_limitations"]["nonzero_nanoseconds_admitted"] is False,
            "native full-TAR qualification is incomplete")
    detail = writer["both-partitions-reproducible-exact-five-changes"]["detail"]
    require(detail["independent_derivations_per_partition"] == 2 and detail["unique_literal_policy_replacements"] == 5
            and detail["tar_image_manifest_bytes_reproducible"] is True, "native repeat proof differs")
    outer = records["erofs_writer_orchestration"]
    require(outer["operation"] == "native-erofs-manifest-writer-roundtrip"
            and outer["input_bytes_preserved"] is True and outer["source_and_android_outputs_unchanged"] is True
            and outer["original_images_modified"] is False and outer["phone_accessed"] is False
            and outer["complete_rom_readiness"] is False and outer["qualified_checker_path_preserved"] is True,
            "writer isolation or input preservation proof is absent")
    for field, role in (("native_build", "erofs_build"), ("source_manifest", "erofs_source_manifest"),
                        ("qualified_tools_lock", "erofs_tools")):
        require(identity(outer[field]) == identity(control["records"][role]), "writer source/build/lock linkage differs")
    prior = outer["prior_qualification"]
    require(len(prior) == 2, "writer prior qualification coverage differs")
    for row, role in zip(prior, ("erofs_shared", "erofs_synthetic")):
        old = records[role]
        require(identity(row) == identity(control["records"][role])
                and all(row[key] == old[key] for key in ("passed", "failed", "all_checks_passed"))
                and row["failed_checks"] == [r for r in old["checks"] if r["status"] == "failed"],
                "writer prior qualification result differs")
    require(identity(outer["contract"]) == identity(controls["contract"])
            and identity(controls["input_contract"]["tools_lock"]) == identity(control["records"]["erofs_tools"])
            and identity(outer["fresh_checker_copy"]) == identity(helper_pin), "writer input contract/checker differs")
    sources = controls["input_contract"]["sources"]
    full_tar = next(r for r in contract["dependencies"] if r["path"] == "tools/erofs-metadata/full_tar.py")
    require(identity(sources["writer"]) == identity(full_tar)
            and identity(sources["exporter_source"]) == identity(contract["exporter_source"])
            and identity(sources["metadata_checker"]) == identity(helper_pin)
            and sources["native_runner"]["sha256"] == contract["native_driver_sha256"],
            "native writer helper/source identities differ")
    staged = outer["staged_inputs"]
    require(len({r["path"] for r in staged}) == len(staged), "duplicate writer staged input")
    for row in [*sources.values(), outer["contract"], controls["wrapper_driver"], controls["input_contract"]["fixture_bundle"]]:
        # The checker intentionally retained its earlier qualified guest path;
        # its fresh copy has the same bytes. All other staged inputs keep paths.
        matches = [r for r in staged if identity(r) == identity(row)
                   and (r["path"] == row["path"] or row is sources["metadata_checker"])]
        require(len(matches) == 1, "writer source was not bound to one preserved staged input")
    result, phase = outer["result"], outer["phase"]
    require(result["receipt_present"] is True
            and identity(result["receipt"]) == identity(control["records"]["erofs_writer"])
            and result["writer_roundtrip_checks_passed"] is True and result["exporter_checks_passed"] is True
            and result["tools_stable"] is True and result["nonzero_nanoseconds_admitted"] is False
            and result["empty_xattr_failures_retained"] is True
            and all(result[k] == records["erofs_writer"][k] for k in ("passed", "failed", "skipped", "all_checks_passed"))
            and result["failed_checks"] == [r for r in records["erofs_writer"]["checks"] if r["status"] == "failed"]
            and all(r["group"] == "upstream-fsck" for r in result["failed_checks"])
            and phase["sandbox_verified"] is True and type(phase["exit_code"]) is int
            and phase["exit_code"] == (1 if writer_failures else 0), "outer writer receipt/sandbox results differ")
    for field in ("sandbox_observation", "stdout", "stderr"):
        avb._identity_spec(identity(phase[field]))
    for name in PARTITIONS:
        info = stock["stock-" + name]["detail"]
        require(info["all_inode_nanoseconds_zero"] is True
                and identity(info["manifest"]) == identity(control["partitions"][name]["manifest"])
                and info["image_hash_reported_by_native_exporter"] == contract["originals"][name]["image"]["sha256"]
                and info["entry_count"] == contract["originals"][name]["entry_count"], "stock metadata capture differs")
    return {"tools": lock["tools"], "reviewed_failed_checks_retained": {
        "synthetic": synthetic_failures, "writer_upstream_xattrs": writer_failures},
        "nonzero_nanoseconds_admitted": False, "empty_xattr_values_admitted": False,
        "native_reexecuted_by_this_command": False, "production_writer_admitted": False}


def qualify_policy(records, control, contract):
    build, analysis = records["policy_build"], records["policy_analysis"]
    _build(build)
    require(type(analysis["schema_version"]) is int and analysis["schema_version"] == 1
            and analysis["operation"] == "verify-native-oem-properties-v12f" and analysis["status"] == "verified"
            and analysis["build_phase"] == build["phase"] and analysis["provider_profile_selected"] is False
            and analysis["strict_compiler_flags_verified"] is True
            and analysis["compiler_temporary_to_analyzed_final_copy_verified"] is True
            and analysis["all_guarded_inputs_unchanged"] is True, "current factory policy analysis is incomplete")
    for field, role in (("build_result_sha256", "policy_build"), ("build_log_sha256", "policy_build_log"),
                        ("build_source_manifest_sha256", "policy_source_manifest"), ("build_sandbox_sha256", "policy_build_sandbox")):
        require(analysis[field] == control["records"][role]["sha256"], "policy analysis build linkage differs")
    require(identity(build["source_manifest"]) == identity(control["records"]["policy_source_manifest"])
            and identity(build["log"]) == identity(control["records"]["policy_build_log"])
            and records["policy_build_sandbox"] == build["sandbox"], "policy build capture or sandbox differs")
    native = analysis["actual_compiler_inputs"]
    require([row["runtime_path"] for row in native] == list(RUNTIME_INPUTS), "actual ten compiler inputs/order differ")
    files = control["policy_files"]
    require(files["combined"]["native_path"].endswith(COMBINED_SUFFIX),
            "ODM replacement must be the actual factory-combined binary, not the source-only installed policy")
    native_out = files["combined"]["native_path"].removesuffix(COMBINED_SUFFIX)
    require(native_out and native_out != "/", "invalid physical native OUT root")
    for field in ("compiler_command_sha256", "driver_manifest_sha256", "analyzer_tool_sha256", "nsjail_sha256"):
        avb._digest(analysis[field])
    for row in native:
        selected = files[row["runtime_path"]]
        require(identity(row) == identity(selected) and row["resolved_path"] == selected["native_path"],
                "selected CIL is not the actual compiler input")
    binaries = {row["name"]: row for row in analysis["analyses"]}
    require(len(binaries) == len(analysis["analyses"]) == 3 and set(binaries) == {
        "combined", "source-precompiled", "source-neverallows"}, "native permissive analysis coverage differs")
    binary_paths = {"combined": files["combined"]["native_path"],
        "source-precompiled": native_out + "/target/product/nezha/odm/etc/selinux/precompiled_sepolicy",
        "source-neverallows": native_out + "/soong/.intermediates/system/sepolicy/sepolicy_neverallows/android_common/policy"}
    for name, row in binaries.items():
        require(type(row["exit_code"]) is int and row["exit_code"] == 0
                and type(row["stdout_bytes"]) is int and row["stdout_bytes"] == 0
                and row["stdout_sha256"] == avb._sha(b"") and row["unfiltered"] is True
                and row["zero_permissive_domains"] is True and row["sandbox_observed"] is True,
                "native policy has permissive domains or incomplete analysis")
        require(row["build_path"] == binary_paths[name], "native permissive-analysis producer differs")
        bindings = [r for r in analysis["input_bindings"] if r["path"] == binary_paths[name]]
        require(len(bindings) == 1 and identity(bindings[0]) == identity(row), "native analyzed binary identity differs")
        avb._digest(row["sandbox_receipt_sha256"]); avb._digest(row["mountinfo_sha256"])
    require(binaries["combined"]["build_path"] == files["combined"]["native_path"]
            and identity(binaries["combined"]) == identity(files["combined"]),
            "ODM replacement must be the actual factory-combined binary, not the source-only installed policy")
    require(files[RUNTIME_INPUTS[7]]["native_path"] == native_out + VENDOR_SUFFIX,
            "vendor CIL is not the same native build's correction output")
    semantics = analysis["semantics"]
    properties, properties_raw = read_json(ROOT / "config/nezha-oem-properties.json")
    _, oem_raw = read_json(ROOT / "config/nezha-oem-policy.json")
    require(analysis["oem_property_contract_sha256"] == semantics["review_contract_file_sha256"] == avb._sha(properties_raw)
            and analysis["oem_contract_sha256"] == avb._sha(oem_raw)
            and analysis["reviewed_property_impact_sha256"] == semantics["review_impact_file_sha256"]
            and analysis["baseline_receipt_sha256"] == semantics["actual_v11_baseline_receipt_sha256"],
            "policy review contract, impact or native baseline linkage differs")
    require(semantics["candidate_input_identities"] == [
        {"runtime_path": row["runtime_path"], **identity(row)} for row in native], "semantic proof used another compiler corpus")
    require(semantics["status"] == "verified"
            and semantics["operation"] == "actual-native-v11-to-v12-four-property-semantic-delta"
            and semantics["original_assertion_statement_count"] == 6366
            and semantics["original_assertion_statements_identical"] is True
            and semantics["assertion_concrete_coverage_compared_to_projection"] is True
            and semantics["reviewed_policy_delta_and_property_allow_endpoint_sets_matched"] is True
            and semantics["helper_property_write_capability_disabled"] is True
            and semantics["helper_effective_property_set_permissions"] == 0, "policy assertion or capability proof differs")
    require(semantics["inherited_semantics"]["all_referenced_symbol_closures_unchanged"] is True,
            "inherited symbol closures changed")
    def measured(value, expected):
        require(type(value) is dict and type(value.get("count")) is int
                and {k: value[k] for k in ("count", "sha256_sorted_compact_json_rows")} == expected,
                "finite native policy effect differs from the reviewed contract")
    expected_deltas = properties["finite_impact"]["ordinary_rule_deltas"]
    require(set(semantics["ordinary_rule_deltas"]) == set(expected_deltas), "ordinary policy effect coverage differs")
    for head, directions in expected_deltas.items():
        require(set(semantics["ordinary_rule_deltas"][head]) == set(directions), "ordinary effect directions differ")
        for direction, expected in directions.items():
            measured(semantics["ordinary_rule_deltas"][head][direction], expected)
    expected_properties = properties["native_effective_ordinary_allow_edges"]
    for observed in (semantics["property_ordinary_totals"], analysis["native_oem_check"]["property_effective_ordinary_allow_edges"]):
        require(set(observed) == set(expected_properties), "property effect coverage differs")
        for name, expected in expected_properties.items():
            measured(observed[name], expected)
    for name, count in (("neverallow", 5976), ("neverallowx", 390)):
        row = semantics["rule_semantics"][name]
        require(row["before_occurrences"] == row["after_occurrences"] == count
                and row["matches_projection"] is True and row["statements_unchanged"] is True,
                "policy assertions were dropped or changed")
    contexts = analysis["native_context_checks"]
    require(len(contexts) == 9 and {row["target"] for row in contexts} == CONTEXT_TARGETS,
            "required factory context checks are incomplete")
    for row in contexts + [analysis["native_oem_check"]]:
        require(row["status"] == "executed_and_passed" and row["fresh_execution_observed"] is True
                and row["build_phase"] == analysis["build_phase"] and row["build_log_sha256"] == analysis["build_log_sha256"]
                and row["mtime_used_to_infer_execution"] is False
                and type(row["ninja_success_records"]) is list and bool(row["ninja_success_records"])
                and type(row["action_log_line"]) is int and row["action_log_line"] > 0
                and type(row["action_log_text"]) is str and bool(row["action_log_text"]), "stale native policy check")
    for row in contexts:
        require(row["empty_stamp_alone_used_as_evidence"] is False, "context check relies on an empty stamp")
        bindings = [r for r in row["inputs"] if r["resolved_path"] == files["combined"]["native_path"]]
        require(len(bindings) == 1 and identity(bindings[0]) == identity(files["combined"]),
                "native context check used a different combined binary")
    oem = analysis["native_oem_check"]
    require(oem["target"] == "nezha_factory_oem_policy_check" and oem["guard_json_alone_used_as_evidence"] is False
            and oem["actual_strict_compiler_input_count"] == 10 and oem["input_binding_proof"]["count"] == 18
            and oem["input_binding_proof"]["exact_paths_hashes_sizes_verified"] is True
            and oem["full_guard_result_independently_rebound"] is True
            and oem["executed_tool_runtime_files_rehashed"] is True and oem["all_copy_mappings_verified"] is True
            and oem["provider_profile_present"] is False
            and oem["assertion_statement_counts"] == {"neverallow": 5976, "neverallowx": 390},
            "native OEM guard source/input proof differs")
    for row in native:
        bindings = [r for r in oem["inputs"] if r["path"] == row["compiler_input"]]
        require(len(bindings) == 1 and identity(bindings[0]) == identity(row)
                and bindings[0]["resolved_path"] == row["resolved_path"], "OEM guard did not use the actual compiler inputs")
    require(identity(oem["output"]) == identity(control["records"]["native_oem_guard"]),
            "captured OEM guard result differs from independently checked native output")
    raw_guard = records["native_oem_guard"]
    require(raw_guard["schema_version"] == 1 and type(raw_guard["schema_version"]) is int
            and raw_guard["operation"] == "check-nezha-oem-native-policy-inputs" and raw_guard["status"] == "verified"
            and raw_guard["contract_sha256"] == analysis["oem_contract_sha256"]
            and raw_guard["property_contract_sha256"] == analysis["oem_property_contract_sha256"]
            and raw_guard["helper_effective_property_set_grants"] == 0 and raw_guard["permissive_cil_declarations"] == 0
            and raw_guard["original_factory_inputs_preserved"] is True
            and raw_guard["existing_binder_derivation_preserved"] is True
            and raw_guard["all_inputs_rehashed_unchanged"] is True
            and raw_guard["assertion_statement_counts"] == {"neverallow": 5976, "neverallowx": 390}
            and raw_guard["property_effective_ordinary_allow_edges"] == expected_properties
            and raw_guard["tool_sources_sha256"] == oem["source_tool_sha256"],
            "raw native OEM result does not match its independently rebound proof")
    derivation = records["vendor_derivation"]
    correction, correction_raw = read_json(ROOT / "config/vendor-policy-correction.json")
    require(derivation["operation"] == "nezha-factory-binder-correction-v1"
            and derivation["contract_sha256"] == avb._sha(correction_raw)
            and derivation["factory_package_sha256"] == contract["factory_package_sha256"]
            and derivation["output"] == correction["output"] and derivation["measured"] == correction["expected"]
            and derivation["inputs"] == correction["inputs"]
            and [{k: row[k] for k in ("runtime_path", "sha256", "size_bytes")} for row in derivation["input_manifest"]]
                == correction["inputs"]
            and derivation["preservation"] == {k: True for k in (
                "all_unselected_bytes_and_line_positions", "all_assertions", "type_role_alias_attribute_and_mapping_declarations",
                "valid_process_binder_grants", "fd_and_service_manager_grants")}
            and derivation["output_readback_verified"] is True and derivation["all_inputs_rehashed_unchanged"] is True,
            "vendor correction receipt differs")
    require(identity(files[RUNTIME_INPUTS[7]]) == identity(correction["output"]), "vendor correction output changed")
    require(derivation["tool_sha256"] == oem["source_tool_sha256"]["vendor_policy.py"]
            and derivation["publisher_sha256"] == oem["source_tool_sha256"]["artifact_files.py"],
            "vendor derivation used different installed tools")
    receipt_native_path = files[RUNTIME_INPUTS[7]]["native_path"].removesuffix("vendor_sepolicy.cil") + "receipt.json"
    bindings = [r for r in analysis["input_bindings"] if r["path"] == receipt_native_path]
    require(len(bindings) == 1 and identity(bindings[0]) == identity(control["records"]["vendor_derivation"]),
            "derivation receipt is not the one bound by current native analysis")
    held = {name: avb._small(row["path"], POLICY, row) for name, row in files.items()}
    replacements = {"vendor": {"/etc/selinux/vendor_sepolicy.cil": files[RUNTIME_INPUTS[7]]},
                    "odm": {"/etc/selinux/precompiled_sepolicy": files["combined"]}}
    for index, name in ((0, "plat"), (2, "system_ext"), (4, "product")):
        expected = hashlib.sha256(held[RUNTIME_INPUTS[index]] + held[RUNTIME_INPUTS[index + 1]]).hexdigest().encode() + b"\n"
        row = files[name + "_sha256"]
        partition = "system" if name == "plat" else name
        suffix = "/target/product/nezha/" + partition + "/etc/selinux/" + name + "_sepolicy_and_mapping.sha256"
        require(row["native_path"] == native_out + suffix and held[name + "_sha256"] == expected,
                "framework sidecar does not equal SHA256(CIL || mapping/202504.cil) plus LF")
        replacements["odm"]["/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"] = row
    return replacements, {"current_factory_combined_binary_bound": True, "sidecars_recomputed_and_matched": True,
        "assertion_statements_retained": 6366, "normal_android_permissive_domains": 0,
        "full_treble_apk_labeling_proven": False, "native_policy_reexecuted": False}


class Counter:
    def write(self, data):
        return len(data)


def tar_size(helper, manifest, replacements):
    out = helper.TarOutput(Counter())
    aliases = {p: group[0] for group in manifest.hardlinks for p in group[1:]}
    for path, row in manifest.entries.items():
        link, hard = None, path in aliases
        size = replacements[path]["size_bytes"] if path in replacements else row["size_bytes"]
        if hard:
            link, size = aliases[path][1:], 0
        elif row["type"] == "symlink":
            link, size = bytes.fromhex(row["symlink_target_hex"]), 0
        elif row["type"] != "regular":
            size = 0
        helper.entry_headers(out, path, row, size=size, link=link, hardlink=hard)
        out.size += size + (-size % 512)
    return out.size + 1024


def production_budget(manifests, plans, tar_sizes, contract):
    """Bound future sequential native work without admitting or executing it.

    The 64 KiB rounded spool sum bounds the pinned diskbuf alignment only after
    the production executor measures a power-of-two alignment no larger than
    64 KiB. The fixed construction allowance is conservative, not a proof of
    compression size or fit. Actual native image/export checks remain required.
    """
    profile = contract["production_execution_profile"]
    require(json_bytes(profile) == json_bytes(PRODUCTION_PROFILE), "unreviewed production construction profile")
    require(set(manifests) == set(plans) == set(tar_sizes) == PARTITIONS, "production budget coverage differs")
    rounded = lambda size, alignment: ((size + alignment - 1) // alignment) * alignment
    partitions, replacement_allocation = {}, 0
    for name in sorted(PARTITIONS):
        manifest = manifests[name]
        replacements = {row["path"].encode(): row["after"]["size_bytes"] for row in plans[name]["replacements"]}
        aliases = {path for group in manifest.hardlinks for path in group[1:]}
        originals = {path: row["size_bytes"] for path, row in manifest.entries.items()
                     if row["type"] == "regular" and path not in aliases}
        require(set(replacements) <= set(originals), "replacement has no original regular inode")
        after = {path: replacements.get(path, size) for path, size in originals.items()}
        require(all(type(size) is int and 0 <= size <= POLICY for size in replacements.values()),
                "replacement exceeds the admitted bound")
        require(max(originals.values(), default=0) <= profile["regular_capture_max_file_bytes"],
                "original file exceeds the bounded regular-byte capture profile")
        spool = sum(rounded(size, profile["scratch_alignment_max_bytes"]) for size in after.values())
        limit = profile["mkfs_fsize_soft_and_hard_bytes"][name]
        required = rounded(max(spool, tar_sizes[name]) + profile["construction_allowance_bytes"], 1 << 30)
        require(required <= limit < (2 << 40) and spool < limit and tar_sizes[name] < limit,
                "production payload exceeds the reviewed finite construction cap")
        allocation = sum(rounded(size, 4096) for size in originals.values())
        replacement_allocation += sum(rounded(size, 4096) for size in replacements.values())
        partitions[name] = {"original_unique_regular_bytes": sum(originals.values()),
            "original_staging_allocation_bound_bytes": allocation,
            "replacement_unique_regular_bytes": sum(after.values()),
            "scratch_spool_bound_bytes": spool, "exact_tar_bytes": tar_sizes[name],
            "tar_assembler_fsize_bytes": rounded(tar_sizes[name], 4096) + 4096,
            "mkfs_fsize_soft_and_hard_bytes": limit, "minimum_calculated_mkfs_cap_bytes": required,
            "max_original_regular_file_bytes": max(originals.values(), default=0),
            "minimum_regular_capture_batches": (sum(originals.values()) + profile["regular_capture_max_batch_bytes"] - 1)
                // profile["regular_capture_max_batch_bytes"],
            "partition_fit_verified": False}
    peak = sum(row["original_staging_allocation_bound_bytes"] + 2 * row["exact_tar_bytes"]
               + 2 * row["mkfs_fsize_soft_and_hard_bytes"] for row in partitions.values())
    peak += max(row["mkfs_fsize_soft_and_hard_bytes"] for row in partitions.values()) + RESERVE + replacement_allocation
    return {"partitions": partitions, "additional_free_bytes_required": max(peak, profile["minimum_additional_free_bytes"]),
        "calculated_additional_peak_bytes": peak, "replacement_source_allocation_bytes": replacement_allocation,
        "original_images_already_present_and_not_copied": True, "both_staging_trees_and_two_tar_image_pairs_retained": True,
        "scratch_filesystem_alignment_and_capacity_recheck_required": True,
        "native_execution_qualified": False, "profile": profile}


def prepare(input_path, expected_sha, *, output_dir):
    contract, contract_sha, profile, helper = load_contract()
    workflow = avb._identity(avb._small(ROOT / "scripts/policy_image_inputs.py", TEXT))
    require(all(row is not None for row in contract["native_records"].values()),
            "actual native evidence pins are not ready; preparation remains blocked")
    control, original_control = load_control(input_path, expected_sha, contract, contract_sha)
    records = read_records(control)
    erofs_proof = qualify_erofs(records, contract, control)
    selected, policy_proof = qualify_policy(records, control, contract)
    manifests, plans, sizes, avb_sources = {}, {}, {}, {}
    for name in sorted(PARTITIONS):
        row = control["partitions"][name]
        avb._rehash(row["image"]["path"], row["image"])
        image = avb.read_image_metadata(row["image"]["path"], name, profile["image_budgets"][name])
        avb.validate_metadata({name: image}, profile, {})
        avb_sources[name] = avb._safe_report(image)
        manifest = metadata.read_manifest(row["manifest"]["path"], expected_image_sha256=row["image"]["sha256"],
            expected_manifest_sha256=row["manifest"]["sha256"])
        require(manifest.identity == identity(row["manifest"])
                and manifest.header["image_size_bytes"] == row["image"]["size_bytes"]
                and len(manifest.entries) == contract["originals"][name]["entry_count"], "complete metadata capture differs")
        helper.admit(manifest)
        require(not any(attr["value_hex"] == "" for entry in manifest.entries.values() for attr in entry["xattrs"]),
                "empty xattr values require a separately qualified writer profile")
        plan_rows = []
        for path in sorted(metadata.REPLACEMENT_PATHS[name]):
            new = selected[name][path]
            plan_rows.append({"path": path, "before": contract["originals"][name]["replacements"][path],
                              "after": {**identity(new), "source": str(new["path"])}})
        plans[name] = {"schema_version": 1, "partition": name, "replacements": plan_rows}
        replacements = helper.replacement_plan(metadata, manifest, plans[name])
        sizes[name] = tar_size(helper, manifest, replacements)
        manifests[name] = manifest
    budget = production_budget(manifests, plans, sizes, contract)
    out = avb.envelope._absolute_path(output_dir)
    allowed = ROOT / contract["output_root"]
    require(out != allowed and out.is_relative_to(allowed), "output must be a fresh ignored policy-images/nezha child")
    require(all(not out.is_relative_to(row["staging_root"]) for row in control["partitions"].values()),
            "output must be outside every read-only regular-byte staging tree")
    with io._private_creation():
        io._fresh_output(out)
        require(shutil.disk_usage(out).free >= 2 * sum(sizes.values()) + RESERVE, "insufficient space for two complete TAR sets")
        results = []
        for repetition in (1, 2):
            directory = out / f"pass-{repetition}"
            io._mkdir(directory)
            current = {}
            for name in sorted(PARTITIONS):
                path = directory / (name + ".tar")
                manifest = manifests[name]
                replacements = helper.replacement_plan(metadata, manifest, plans[name])
                with avb.envelope._parent_directory(path) as parent:
                    fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                with os.fdopen(fd, "wb") as stream:
                    output = helper.TarOutput(stream)
                    counts = helper.assemble(manifest, control["partitions"][name]["staging_root"], replacements, output)
                    stream.flush(); os.fsync(stream.fileno())
                require(output.size == sizes[name] and counts["regular_paths_verified"] ==
                    sum(row["type"] == "regular" for row in manifest.entries.values()), "TAR coverage or byte count differs")
                tar_identity = {"sha256": output.digest.hexdigest(), "size_bytes": output.size}
                avb._rehash(path, tar_identity)
                command = helper.mkfs_command(manifest.header["superblock"], helper.admit(manifest), str(path))
                current[name] = {"tar": tar_identity, "regular_paths_verified": counts["regular_paths_verified"],
                    "recipe": {"tool_role": "mkfs", "unset_environment": ["SOURCE_DATE_EPOCH"],
                        "arguments": command[4:-2] + [f"pass-{repetition}/{name}.erofs", f"pass-{repetition}/{name}.tar"],
                        "native_execution_admitted": False, "production_execution_profile_required": True}}
            results.append(current)
        require(all(results[0][name]["tar"] == results[1][name]["tar"] for name in PARTITIONS),
                "two independent complete TAR derivations differ")
        for repetition, current in enumerate(results, 1):
            for name in sorted(PARTITIONS):
                avb._rehash(out / f"pass-{repetition}" / (name + ".tar"), current[name]["tar"])
        for name, row in control["partitions"].items():
            avb._rehash(row["image"]["path"], row["image"])
            avb._rehash(row["manifest"]["path"], row["manifest"])
            io._save(out / (name + "-replacement-plan.json"), plans[name])
        for row in control["policy_files"].values():
            avb._rehash(row["path"], row)
        read_records(control)
        require(read_json(input_path)[1] == original_control and load_contract()[1] == contract_sha
                and avb._identity(avb._small(ROOT / "scripts/policy_image_inputs.py", TEXT)) == workflow,
                "input selection or source contract changed")
        report = {"schema_version": 1, "operation": "prepare-nezha-five-file-policy-image-inputs",
            "status": "complete-tar-inputs-prepared", "artifact_set_id": control["artifact_set_id"],
            "contract_sha256": contract_sha, "input_control_sha256": expected_sha,
            "workflow": workflow,
            "original_images": {name: identity(row["image"]) for name, row in control["partitions"].items()},
            "native_manifests": {name: identity(row["manifest"]) for name, row in control["partitions"].items()},
            "native_evidence": {name: identity(row) for name, row in control["records"].items()},
            "original_avb_metadata": avb_sources, "policy_proof": policy_proof, "erofs_proof": erofs_proof,
            "replacements": {name: plans[name]["replacements"] for name in sorted(PARTITIONS)},
            "passes": results, "two_complete_tar_derivations_identical": True,
            "production_execution_budget": budget,
            "original_images_unchanged": True, "metadata_from_staging_tree": False,
            "qualified_helper_promotion_byte_identical": True, "production_writer_admitted": False,
            "comparison_contract_generated": False, "old_avb_tail_copied": False,
            "remaining_gates": ["Qualify the recorded finite production limits, scratch filesystem and bounded log executor, then run two native builds.",
                "Complete native metadata exports and exact-five-file semantic comparison for both new images.",
                "Regenerate hashtrees/FEC/AVB footers; verify final identities, partition fit and signed parent chain."],
            **BOUNDARIES}
        io._save(out / "preparation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("plan")
    selected = sub.add_parser("prepare")
    selected.add_argument("--input", required=True, type=Path)
    selected.add_argument("--expected-sha256", required=True)
    selected.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = plan() if args.operation == "plan" else prepare(args.input, args.expected_sha256, output_dir=args.output_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2 if result["status"] == "blocked" else 0
    except (PolicyImageError, avb.AvbImageSetError, metadata.MetadataError, io.TwrpWorkingError,
            OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "failed", "error_class": type(exc).__name__,
                          "error": "policy-image preparation prerequisites failed", **BOUNDARIES}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
