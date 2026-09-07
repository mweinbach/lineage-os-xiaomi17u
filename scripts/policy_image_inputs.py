#!/usr/bin/env python3
"""Prepare the exact five Nezha policy replacements as two complete TAR sets.

This host command does not extract a filesystem or run a native image writer.
It requires reviewed native evidence, complete metadata exports and all regular
file bytes, then preserves their metadata through the pinned full-TAR helper.
Raw EROFS construction, metadata comparison, FEC, AVB and adoption remain gates.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import types
import uuid

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
CONTRACT = ROOT / "config/nezha-policy-images-successor.json"
CONTRACT_ID = "nezha-five-file-policy-image-inputs-v1"
HISTORICAL_PROFILE = "historical-v12"
EXPORT4_PROFILE = "v12-export4"
EXPORT4_CONTRACT_ID = "nezha-five-file-policy-image-inputs-v12-export4-v1"
PROVIDER_PROFILE = "v13h-policy-only"
PROVIDER_CONTRACT_ID = "nezha-five-file-policy-image-inputs-v13h-v1"
POLICY3_PROFILE = "policy3-evolution"
POLICY3_CONTRACT_ID = "nezha-five-file-policy-image-inputs-policy3-evolution-v1"
PROFILE_CONTRACT_IDS = {HISTORICAL_PROFILE: CONTRACT_ID, EXPORT4_PROFILE: EXPORT4_CONTRACT_ID,
                        PROVIDER_PROFILE: PROVIDER_CONTRACT_ID, POLICY3_PROFILE: POLICY3_CONTRACT_ID}
PROFILE_CONTRACT_SHA256 = {
    HISTORICAL_PROFILE: "f49e2b37497d72ad39ffd25dde56c89f0d6f062d63ff0d83dd4130e928e6b461",
    EXPORT4_PROFILE: "273cc45a033bbac606077b7ca47eb391c7ecb99ab3734070457d113e43c06236",
    PROVIDER_PROFILE: "dfbfcaee979af9a5593d12820df9d19ac61c42f3648e0513e2e31d75ca545c4b",
    POLICY3_PROFILE: "f355811b248fe19d4dfc8b4b6561efa6b5dbbad07c20c3ee98c8d4952f66d215",
}
TEXT = 8 << 20
PROVIDER_EVIDENCE = 16 << 20
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
EXPORT4_RECORD_ROLES = RECORD_ROLES | {"erofs_fsize_probe", "erofs_fsize_orchestration",
    "sidecar_source_capture", "sidecar_native_validation", "sidecar_orchestration", "sidecar_sandbox"} | {
    "erofs_" + partition + "_noop" + suffix
    for partition in PARTITIONS for suffix in ("", "_orchestration", "_sandbox", "_capture")}
PROVIDER_RECORD_ROLES = EXPORT4_RECORD_ROLES | {"provider_complete_effect_review"}
POLICY3_REVIEW_ROLES = frozenset(("policy_capture_mapping", "policy_oem_replay", "policy_native_log_review",
    "policy_m4_source_review", "policy_freeze_selectors", "policy_wrapper_review", "policy_property_freeze",
    "policy_property_effects", "policy_property_summary", "policy_property_bindings"))
POLICY3_RECORD_ROLES = (EXPORT4_RECORD_ROLES - {
    "policy_build_log", "policy_source_manifest", "policy_build_sandbox", "sidecar_source_capture",
    "sidecar_native_validation", "sidecar_orchestration", "sidecar_sandbox"}) | POLICY3_REVIEW_ROLES | {
    "policy_review_freeze", "policy_retained_capture", "policy_binary_validation", "policy_binary_review", "policy_freeze_review",
    "policy_sidecar_capture", "policy_sidecar_validation"}
POLICY3_REVIEW_SECTIONS = frozenset(("m4_recipe", "native_completion", "native_context_checks",
    "producer_provenance_limits", "scope", "seven_prefix_effects", "source_and_oem_composition", "strict_factory_compile"))
POLICY3_BINARY_MODULES = (
    ("precompiled_sepolicy", False), ("plat_precompiled_sepolicy", False), ("sepolicy_neverallows", False),
    ("29.0_compat_test", True), ("30.0_compat_test", True), ("31.0_compat_test", True),
    ("32.0_compat_test", True), ("33.0_compat_test", True), ("34.0_compat_test", True),
    ("202404_compat_test", True), ("precompiled_sepolicy_without_vendor", False),
    ("nezha_factory_precompiled_sepolicy", None))
PROVIDER_PROOF_SECTIONS = frozenset(("selection", "source_history_proof", "provider_policy_contract_crosspin",
    "provider_policy_tool_crosspin", "portable_provider_provenance", "native_policy_output_preservation",
    "protected_existing_component_outputs", "configuration", "m4", "native_202504_mapping_producers",
    "public_exporters", "provider_input_action", "application_policy_exports", "semantics",
    "native_oem_check", "native_context_checks"))
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


def read_json(path, expected=None, *, limit=TEXT):
    # Do not buffer an accidentally selected PEM payload as a JSON input.
    with avb._input(path, limit) as (stream, st):
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


def record_roles(contract):
    require(contract["contract_id"] in PROFILE_CONTRACT_IDS.values(), "unknown policy snapshot profile")
    if contract["contract_id"] == POLICY3_CONTRACT_ID:
        return POLICY3_RECORD_ROLES
    if contract["contract_id"] == PROVIDER_CONTRACT_ID:
        return PROVIDER_RECORD_ROLES
    return EXPORT4_RECORD_ROLES if contract["contract_id"] == EXPORT4_CONTRACT_ID else RECORD_ROLES


def derived_sidecars(contract):
    return contract["contract_id"] in (EXPORT4_CONTRACT_ID, PROVIDER_CONTRACT_ID)


def complete_noops_required(contract):
    return derived_sidecars(contract) or contract["contract_id"] == POLICY3_CONTRACT_ID


def record_json_limit(control, role):
    # Only explicitly selected, measured record roles exceed the original
    # 8 MiB bound. The private control cannot choose an arbitrary reader limit.
    if control["contract_id"] == PROVIDER_CONTRACT_ID and role in ("policy_analysis", "provider_complete_effect_review"):
        return PROVIDER_EVIDENCE
    if control["contract_id"] == POLICY3_CONTRACT_ID and role == "policy_build":
        return 16 << 20
    return TEXT


def load_contract(selected_profile=HISTORICAL_PROFILE):
    document, _ = read_json(CONTRACT)
    avb._keys(document, ("schema_version", "profiles"), "policy-image profile catalog")
    require(type(document["schema_version"]) is int and document["schema_version"] == 2
            and type(document["profiles"]) is dict and set(document["profiles"]) == set(PROFILE_CONTRACT_IDS)
            and selected_profile in PROFILE_CONTRACT_IDS, "unknown or incomplete policy-image profile catalog")
    c = document["profiles"][selected_profile]
    raw = json_bytes(c)
    expected = PROFILE_CONTRACT_SHA256[selected_profile]
    require(expected is None or avb._sha(raw) == expected, "selected reviewed contract bytes changed")
    fields = {"schema_version", "contract_id", "device", "platform", "factory_package_sha256", "originals",
        "dependencies", "erofs_revision", "exporter_source", "native_driver_sha256", "shared_driver_sha256",
        "writer_driver_sha256", "native_records", "native_tools", "production_execution_profile", "admitted_metadata",
        "output_root", "independent_tar_passes", "limits"}
    if selected_profile in (EXPORT4_PROFILE, PROVIDER_PROFILE):
        fields.add("sidecar_derivation")
    if selected_profile == PROVIDER_PROFILE:
        fields.add("provider_policy")
    if selected_profile == POLICY3_PROFILE:
        fields.add("evolution_policy")
    avb._keys(c, fields, "policy-image contract")
    require(c["schema_version"] == 1 and type(c["schema_version"]) is int
            and c["contract_id"] == PROFILE_CONTRACT_IDS[selected_profile] and c["device"] == "nezha"
            and c["platform"] == {"branch": "bka", "release_config": "bp4a", "board_api": "202504"},
            "unsupported policy-image contract")
    require(set(c["originals"]) == PARTITIONS and set(c["native_records"]) == record_roles(c)
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
    if selected_profile == PROVIDER_PROFILE:
        required |= {"config/nezha-framework-provider-policy.json", "config/nezha-framework-providers.json",
                     "scripts/framework_provider_policy.py"}
    if selected_profile == POLICY3_PROFILE:
        required |= {"config/evolution-policy-base.json", "config/nezha-framework-provider-policy.json"}
    require(paths == required, "implementation source pins are incomplete")
    profile, profile_sha = avb.load_profile()
    require(profile_sha == "f5160e1f2d9e901d3fb9e3fe1a3ef11e085336f91d0511eaac4442b8399191a1",
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
    if selected_profile in (EXPORT4_PROFILE, PROVIDER_PROFILE):
        sidecar = c["sidecar_derivation"]
        avb._keys(sidecar, ("source_revision", "source", "recipe", "contract", "driver", "launcher", "collector"),
                  "source-bound sidecar derivation")
        require(sidecar["source_revision"] == "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27"
                and sidecar["source"] == {"sha256": "17171fec6b4e253db277c351f817670077c6fd235ca07ac33be509c8faa4d2f8",
                    "size_bytes": 43467} and sidecar["recipe"] == "cat $(in) | sha256sum | cut -d' ' -f1 > $(out)",
                "source-bound sidecar algorithm changed")
        for name in ("source", "contract", "driver", "launcher", "collector"):
            avb._identity_spec(sidecar[name])
    if selected_profile == PROVIDER_PROFILE:
        provider = c["provider_policy"]
        avb._keys(provider, ("analysis_operation", "build_phase", "provider_phase", "baseline", "baseline_corpus_sha256",
            "native_contract", "input_contract", "native_policy_tool", "semantic_contract", "complete_review_canonical_sha256",
            "proof_sections"), "provider policy snapshot")
        require(provider["analysis_operation"] == "verify-native-provider-policy-only-v13h"
                and provider["build_phase"] == "policy-only-v13h-1"
                and provider["provider_phase"] == "v13h-provider-policy-only-runtime-exports-v1"
                and set(provider["proof_sections"]) == PROVIDER_PROOF_SECTIONS,
                "provider policy source/action proof coverage differs")
        for name in ("baseline", "native_contract", "input_contract", "native_policy_tool", "semantic_contract"):
            avb._identity_spec(provider[name])
        for name in ("baseline_corpus_sha256", "complete_review_canonical_sha256"):
            avb._digest(provider[name])
        for row in provider["proof_sections"].values():
            avb._identity_spec(row)
    if selected_profile == POLICY3_PROFILE:
        evolution = c["evolution_policy"]
        avb._keys(evolution, ("build_phase", "build_operation", "review_operation", "review_status", "review_evidence",
            "compiler_inputs", "combined", "review_sections", "oem_semantics", "source_commit", "sidecar_source"),
            "policy3 Evolution snapshot")
        require(evolution["build_phase"] == "first-target-files-policy-3"
                and evolution["build_operation"] == "first-ordinary-target-files-construction"
                and evolution["review_operation"] == "review-actual-policy3-selected-factory-baseline"
                and evolution["review_status"] == "verified-native-completion-and-scoped-semantic-source-context-review"
                and set(evolution["review_evidence"]) == POLICY3_REVIEW_ROLES
                and set(evolution["review_sections"]) == POLICY3_REVIEW_SECTIONS
                and [row["runtime_path"] for row in evolution["compiler_inputs"]] == list(RUNTIME_INPUTS),
                "policy3 source or ordered evidence selection differs")
        for row in evolution["review_evidence"].values():
            avb._identity_spec(row, path=True)
        for row in evolution["review_sections"].values():
            avb._identity_spec(row)
        for name in ("oem_semantics", "source_commit", "sidecar_source"):
            avb._identity_spec(evolution[name])
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


def plan(selected_profile=HISTORICAL_PROFILE):
    c, digest, _, _ = load_contract(selected_profile)
    return {"schema_version": 1, "operation": "plan-nezha-policy-image-inputs", "contract_sha256": digest,
        "profile": selected_profile, "contract_id": c["contract_id"],
        "status": "blocked" if (PROFILE_CONTRACT_SHA256[selected_profile] is None
            or any(row is None for row in c["native_records"].values())) else "ready_for_evidence_validation",
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
    export4 = derived_sidecars(contract)
    fields = {"schema_version", "contract_id", "contract_sha256", "artifact_set_id", "records", "partitions", "policy_files"}
    if complete_noops_required(contract):
        fields.add("noop_manifests")
    avb._keys(value, fields, "policy image inputs")
    require(value["schema_version"] == 1 and type(value["schema_version"]) is int
            and value["contract_id"] == contract["contract_id"] and value["contract_sha256"] == contract_sha
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value["artifact_set_id"]), "input contract differs")
    require(type(value["records"]) is dict and type(value["partitions"]) is dict
            and set(value["records"]) == record_roles(contract) and set(value["partitions"]) == PARTITIONS,
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
    expected_roles = {*RUNTIME_INPUTS, "combined"}
    if not export4:
        expected_roles |= {"plat_sha256", "system_ext_sha256", "product_sha256"}
    require(type(value["policy_files"]) is dict and set(value["policy_files"]) == expected_roles,
            "policy/compiler/hash-file coverage differs")
    for row in value["policy_files"].values():
        selected(row, True)
        require(row["size_bytes"] <= POLICY, "policy artifact exceeds bound")
    if complete_noops_required(contract):
        require(type(value["noop_manifests"]) is dict and set(value["noop_manifests"]) == PARTITIONS,
                "complete vendor/ODM no-op manifest coverage required")
        for rows in value["noop_manifests"].values():
            require(type(rows) is list and len(rows) == 2, "both no-op manifest passes are required")
            for row in rows:
                selected(row)
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
            result[name] = read_json(row["path"], row, limit=record_json_limit(control, name))[0]
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
    result = {"tools": lock["tools"], "reviewed_failed_checks_retained": {
        "synthetic": synthetic_failures, "writer_upstream_xattrs": writer_failures},
        "nonzero_nanoseconds_admitted": False, "empty_xattr_values_admitted": False,
        "native_reexecuted_by_this_command": False, "production_writer_admitted": False}
    if complete_noops_required(contract):
        result["complete_original_noop_qualification"] = qualify_noops(records, contract, control)
    return result


def _noop_equal(before, after):
    physical = {"root_nid", "primary_blocks", "total_blocks", "meta_blkaddr", "xattr_blkaddr"}
    require(set(before.entries) == set(after.entries) and before.hardlinks == after.hardlinks,
            "no-op namespace or hardlink topology changed")
    require(all({k: v for k, v in before.entries[path].items() if k != "nid"}
                == {k: v for k, v in after.entries[path].items() if k != "nid"} for path in before.entries),
            "no-op inode metadata or content changed")
    require({k: v for k, v in before.header["superblock"].items() if k not in physical}
            == {k: v for k, v in after.header["superblock"].items() if k not in physical},
            "no-op semantic superblock changed")
    return {"entries_compared": len(before.entries),
            "regular_contents_compared": sum(row["type"] == "regular" for row in before.entries.values()),
            "metadata_exclusions": ["inode.nid"], "superblock_physical_exclusions": sorted(physical),
            "content_replacements": [], "all_semantic_fields_equal": True}


def _noop_sandbox(sandbox):
    require(sandbox["source_out_and_inputs_readonly"] is True
            and type(sandbox["uid"]) is int and sandbox["uid"] == 65534
            and type(sandbox["gid"]) is int and sandbox["gid"] == 65534,
            "no-op sandbox identity or read-only source proof differs")
    require(set(sandbox["capabilities"]) == {"CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"}
            and all(int(value, 16) == 0 for value in sandbox["capabilities"].values()), "no-op capabilities are not empty")
    require(set(sandbox["namespaces"]) == set(sandbox["parent_namespaces"]) == {"mnt", "net", "pid", "user"}
            and all(sandbox["namespaces"][name] != sandbox["parent_namespaces"][name]
                    for name in sandbox["namespaces"]), "no-op namespace isolation differs")
    for field in ("uid_map", "gid_map"):
        require([list(map(int, line.split())) for line in sandbox["identity_maps"][field].splitlines()]
                == [[65534, 0, 1]], "no-op identity mapping differs")
    require(sandbox["readonly_flag"] == 1 and all(sandbox["effective_mount_flags"][name] & 1
            for name in ("/", "/work", "/work/evolution", "/work/out")), "no-op protected mounts are writable")
    avb._digest(sandbox["mountinfo_sha256"])


def qualify_noops(records, contract, control):
    """Rebind measured original-image proofs; never admit changed policy images."""
    probe, probe_outer = records["erofs_fsize_probe"], records["erofs_fsize_orchestration"]
    require(probe["operation"] == "native-production-fsize-sparse-log-profile-proof"
            and probe["passed"] is True and type(probe["skipped"]) is int and probe["skipped"] == 0
            and probe_outer["passed"] is True and probe_outer["bound_input_bytes_preserved"] is True
            and identity(probe_outer["native_probe_receipt"]) == identity(control["records"]["erofs_fsize_probe"]),
            "native finite-file primitive proof is incomplete")
    expected_checks = {"limit-2gib", "limit-6gib", "log-overflow-group-kill", "bound-inputs-unchanged"}
    checks = {row["name"]: row for row in probe["checks"]}
    require(len(probe["checks"]) == len(checks) == 4 and set(checks) == expected_checks
            and all(row["status"] == "passed" for row in checks.values()), "native primitive checks differ")
    for gib in (2, 6):
        row = checks["limit-" + str(gib) + "gib"]["native_result"]
        require(row["passed"] is True and row["architecture"] == "x86_64" and row["off_t_bytes"] == 8
                and row["limit_bytes"] == row["rlimit_soft_bytes"] == row["rlimit_hard_bytes"] == gib << 30
                and row["sigxfsz"] == "SIG_IGN" and row["sigpipe"] == "SIG_DFL"
                and row["filesystem_magic"] == 0xEF53
                and set(row["checks"]) == {"inherited_signal_profile", "finite_limits", "ext4_alignment",
                    "truncate_2tib_rejected", "truncate_over_limit_rejected", "write_at_limit_rejected",
                    "sparse_boundary_write", "sparse_allocation_bounded", "sparse_readback",
                    "truncated_back_to_zero", "cleanup_completed"}
                and all(value is True for value in row["checks"].values()), "native finite-file ABI/limit proof differs")
    require(probe["scope"]["mkfs_executed"] is False
            and probe["scope"]["mkfs_production_execution_qualified"] is False,
            "primitive falsely claims image-writer qualification")
    results = {}
    for partition, revision in (("vendor", 2), ("odm", 1)):
        role = "erofs_" + partition + "_noop"
        native, outer, sandbox, capture = (records[role + suffix]
            for suffix in ("", "_orchestration", "_sandbox", "_capture"))
        require(native["operation"] == f"full-original-{partition}-noop-erofs-roundtrip-v{revision}"
                and native["passed"] is True and type(native["skipped"]) is int and native["skipped"] == 0
                and native["replacements"] == [] and native["bound_inputs_preserved"] is True,
                "complete original no-op proof differs")
        expected = {"fresh-original-full-export", "original-structure-data-xattrs",
                    "independent-tar-image-manifest-reproducibility", "original-tools-runtime-inputs-and-stage-preserved"}
        expected |= {f"{partition}-noop-{n}-{suffix}" for n in (1, 2)
                     for suffix in ("structure-data-xattrs", "all-bytes-and-metadata")}
        checks = {row["name"]: row for row in native["checks"]}
        require(len(native["checks"]) == len(checks) == 8 and set(checks) == expected
                and all(row["status"] == "passed" for row in checks.values()), "complete no-op checks are absent, failed or duplicated")
        require(outer["operation"] == f"root-full-{partition}-noop-orchestration-v{revision}"
                and outer["passed"] is True and outer["native_result"] == native
                and identity(outer["native_receipt"]) == identity(control["records"][role])
                and outer["bound_selected_inputs_unchanged"] is True
                and outer["global_android_output_unchanged_claimed"] is False
                and outer["global_build_idle_required"] is False, "no-op outer/native linkage differs")
        require(identity(native["sandbox_observation"]) == identity(outer["sandbox_observation"])
                == identity(control["records"][role + "_sandbox"]), "no-op sandbox receipt identity differs")
        _noop_sandbox(sandbox)
        require(identity(outer["exporter_source"]) == identity(contract["exporter_source"])
                and set(native["tools"]) == {"mkfs", "fsck", "exporter"}
                and all(identity(row) == contract["native_tools"][name] for name, row in native["tools"].items()),
                "no-op source or copied native tool bytes differ")
        scope = native["scope"]
        require(scope["raw_" + partition + "_noop_roundtrip_qualified"] is True
                and all(scope[key] is False for key in ("policy_adopted", "original_images_written",
                    "source_or_android_output_writes", "global_android_output_unchanged_claimed",
                    "complete_rom_admitted", "avb_verified", "partition_fit_verified",
                    "retained_kernel_mount_or_boot_verified", "production_policy_writer_admitted", "phone_accessed")),
                "no-op scope claims unproved adoption or runtime support")
        require(native["prior_synthetic_evidence"] == {"passed": 11, "failed": 6, "skipped": 0,
                "all_checks_passed": False, "known_empty_xattr_fsck_failures_retained": True},
                "no-op proof lost the historical synthetic failures")
        resources = native["resources"]
        require(len(resources["effective_cpus"]) == 1
                and set(resources["effective_cpus"]) <= set(resources["inherited_allowed_cpus"])
                and resources["nice"] == 19 and resources["whole_job_wall_seconds"] == 7200
                and resources["initial_headroom"]["available_disk_bytes"] >= 48 << 30
                and resources["initial_headroom"]["mem_available_bytes"] >= 8 << 30,
                "no-op bounded resource profile differs")
        captured = {row["path"]: row for row in capture["files"]}
        require(len(captured) == len(capture["files"]) == 63
                and all(Path(name).name == name for name in captured)
                and sum(row["size_bytes"] for row in captured.values()) == capture["total_bytes"],
                "no-op capture inventory is incomplete or unsafe")
        require(identity(captured["receipt.json"]) == identity(control["records"][role])
                and identity(captured["orchestration.json"]) == identity(control["records"][role + "_orchestration"])
                and identity(captured["sandbox.json"]) == identity(control["records"][role + "_sandbox"]),
                "no-op capture/record linkage differs")
        before_row = control["partitions"][partition]["manifest"]
        before = metadata.read_manifest(before_row["path"], expected_manifest_sha256=before_row["sha256"],
            expected_image_sha256=contract["originals"][partition]["image"]["sha256"])
        require(identity(captured["original-export.stdout"]) == before.identity
                == checks["fresh-original-full-export"]["manifest"], "no-op original manifest selection differs")
        require(native["stock_profile"]["entry_count"] == len(before.entries)
                and native["stock_profile"]["superblock"] == before.header["superblock"]
                and all(native["stock_profile"][key] == 0 for key in
                    ("hardlink_groups", "empty_xattrs", "nonzero_nanoseconds", "set_id_inodes", "special_inodes")),
                "no-op original profile differs")
        require(len(native["artifacts"]) == len(native["final_artifact_identities"])
                == len(control["noop_manifests"][partition]) == 2,
                "two independently rehashed no-op artifact sets are required")
        for number, (artifact, selected) in enumerate(zip(native["artifacts"], control["noop_manifests"][partition]), 1):
            require({key: artifact[key] for key in ("tar", "image", "manifest")}
                    == native["final_artifact_identities"][number - 1]
                    and identity(artifact["manifest"]) == identity(selected)
                    == identity(captured[f"{partition}-noop-{number}-export.stdout"]),
                    "no-op final artifact or selected manifest identity changed")
            after = metadata.read_manifest(selected["path"], expected_manifest_sha256=selected["sha256"],
                expected_image_sha256=artifact["image"]["sha256"])
            comparison = _noop_equal(before, after)
            sb = after.header["superblock"]
            require(artifact["comparison"] == comparison
                    == checks[f"{partition}-noop-{number}-all-bytes-and-metadata"]["comparison"]
                    and artifact["superblock"] == sb
                    and artifact["image"]["size_bytes"] == after.header["image_size_bytes"]
                    == sb["primary_blocks"] * sb["block_size"] and sb["total_blocks"] == sb["primary_blocks"],
                    "no-op semantic proof or raw filesystem boundary differs")
        require(all(identity(native["artifacts"][0][kind]) == identity(native["artifacts"][1][kind])
                    for kind in ("tar", "image", "manifest")), "no-op independent derivations differ")
        commands = native["commands"]
        require(len(commands) == 24, "no-op command coverage differs")
        mkfs = []
        for command in commands:
            require(type(command["exit_code"]) is int and command["exit_code"] == 0
                    and command["kill_reason"] is None and command["whole_process_group_killed"] is False
                    and command["all_pipes_eof"] is True, "no-op command did not complete successfully")
            limits = command["limits"]
            is_mkfs = "--tar=f" in command["argv"]
            require(limits["file_size_soft_and_hard_bytes"] == PRODUCTION_PROFILE["mkfs_fsize_soft_and_hard_bytes"][partition]
                    and limits["log_cap_each_bytes"] == 16 << 20 and limits["sampled_rss_ceiling_bytes"] == 2 << 30
                    and limits["rss_is_kernel_hard_limit"] is False and limits["cpu_soft_seconds"] == 1800
                    and limits["cpu_hard_seconds"] == 1801 and limits["wall_seconds"] == 1800
                    and limits["sigxfsz"] == ("SIG_IGN" if is_mkfs else "SIG_DFL")
                    and limits["restore_signals"] is False, "no-op native limits or signal profile changed")
            for row in command["logs"].values():
                require(identity(row) == identity(captured[Path(row["path"]).name]) and row["size_bytes"] <= 16 << 20,
                        "no-op native log capture differs")
            if is_mkfs:
                mkfs.append(command)
                require(command["argv"][0] == native["tools"]["mkfs"]["path"]
                        and command["observed_unlinked_private_spools"]
                        and any(row["size_bytes"] > 0 and row["target"].startswith(command["private_tmpdir"] + "/tmp.")
                                and row["target"].endswith(" (deleted)") for row in command["observed_unlinked_private_spools"]),
                        "actual private no-op diskbuf fallback was not observed")
        require(len(mkfs) == 2, "two actual no-op mkfs commands required")
        sb = before.header["superblock"]
        options = ["--tar=f", "--clean=data", "--mkfs-time", "--preserve-mtime", "-T", str(sb["build_time_sec"]),
                   "-U", str(uuid.UUID(hex=sb["uuid_hex"])), "-L", bytes.fromhex(sb["volume_name_hex"]).split(b"\0", 1)[0].decode("ascii"),
                   "-b4096", "-zlz4hc,level=9", "-C4096", "--uid-offset=0", "--workers=0", "--ovlfs-strip=0"]
        if not sb["feature_compat"] & 4:
            options += ["-E", "^xattr-name-filter"]
        for number, command in enumerate(mkfs):
            args = command["argv"]
            require(re.fullmatch(r"/proc/self/fd/[0-9]+", args[-1]) and args == [native["tools"]["mkfs"]["path"],
                    *options, native["artifacts"][number]["image"]["path"], args[-1]], "no-op compression/UUID/time/worker recipe differs")
        retained = {row["path"]: identity(row) for row in capture["guest_only_large_artifacts"]}
        expected_retained = {Path(row[kind]["path"]).name: identity(row[kind])
                             for row in native["artifacts"] for kind in ("tar", "image")}
        require(len(capture["guest_only_large_artifacts"]) == 4 and retained == expected_retained,
                "root-retained large no-op artifact identities differ")
        require(native["staging_before"] == native["staging_after"]
                and native["staging_after"]["all_paths_checked_without_following_symlinks"] == len(before.entries)
                and native["staging_after"]["host_metadata_used_as_authority"] is False
                and native["staging_after"]["staging_content_executed"] is False, "no-op regular-byte staging preservation differs")
        results[partition] = {"native_checks_passed": 8, "skipped": 0, "complete_metadata_manifests_rechecked": 2,
            "original_entry_count": len(before.entries), "scope": "original-noop-only",
            "policy_replacement_images_qualified": False, "original_images_reopened_by_this_qualifier": False}
    return {"partitions": results, "finite_file_primitive_verified": True,
            "native_processes_reexecuted": False, "policy_replacement_images_qualified": False}


def qualify_sidecar_derivation(records, control, held, contract):
    """Verify the recorded shell recipe without inventing installed outputs."""
    provider = contract["contract_id"] == PROVIDER_CONTRACT_ID
    native_operation = "derive-v13h-policy-sidecars-native-v1" if provider else "derive-export4-policy-sidecars-native-v1"
    outer_operation = "root-policy-sidecar-v13h-native-orchestration-v1" if provider else "root-policy-sidecar-native-orchestration-v1"
    baseline_operation = "verify-native-provider-policy-only-v13h" if provider else "verify-native-oem-properties-v12f-export4"
    native, outer, sandbox, source = (records[role] for role in
        ("sidecar_native_validation", "sidecar_orchestration", "sidecar_sandbox", "sidecar_source_capture"))
    pins = contract["sidecar_derivation"]
    require(source["schema_version"] == 1 and source["guest_writes"] is False and source["phone_accessed"] is False
            and source["files"] == [{"path": "system/sepolicy/Android.bp", **pins["source"]}]
            and source["total_bytes"] == pins["source"]["size_bytes"]
            and source["projects"] == {"system/sepolicy": {"head": pins["source_revision"],
                "status": "M private/init_dev_config.te\n M private/su.te"}}, "sidecar source capture differs")
    require(type(native["schema_version"]) is int and native["schema_version"] == 1
            and native["operation"] == native_operation and native["passed"] is True
            and type(native["skipped"]) is int and native["skipped"] == 0
            and native["input_bytes_preserved"] is True and native["tool_and_runtime_bytes_preserved"] is True,
            "native derived-sidecar validation is incomplete")
    require(native["scope"] == {"native_recipe_executed": True, "derived_sidecars_verified": True,
                "installed_sidecars_captured": False, "native_android_genrules_executed": False,
                "source_or_android_output_writes": False, "images_accessed_or_written": False,
                "policy_adopted": False, "complete_rom_ready": False, "phone_accessed": False},
            "derived sidecars falsely claim installed outputs or image adoption")
    require(identity(native["contract"]) == pins["contract"] and identity(native["driver"]) == pins["driver"]
            and identity(native["collector"]) == pins["collector"]
            and identity(native["source_capture"]) == identity(control["records"]["sidecar_source_capture"])
            and identity(native["recipe_source"]) == pins["source"]
            and native["recipe_source"]["project_revision"] == pins["source_revision"]
            and native["recipe_source"]["native_path"] == "/work/evolution/system/sepolicy/Android.bp"
            and identity(native["baseline"]) == identity(control["records"]["policy_analysis"])
            and native["baseline"]["operation"] == baseline_operation,
            "native sidecar source, tool or selected policy binding differs")
    require(outer["operation"] == outer_operation and outer["passed"] is True
            and outer["native_result"] == native
            and identity(outer["native_receipt"]) == identity(control["records"]["sidecar_native_validation"])
            and identity(outer["launcher"]) == pins["launcher"]
            and identity(outer["collector"]) == pins["collector"]
            and identity(outer["live_recipe_source"]) == pins["source"]
            and outer["bound_selected_inputs_unchanged"] is True
            and all(outer[key] is False for key in ("global_build_idle_required", "global_android_output_unchanged_claimed",
                "source_or_android_output_writes", "images_accessed_or_written", "phone_accessed")),
            "sidecar root orchestration linkage or preservation differs")
    require(identity(native["sandbox"]) == identity(outer["sandbox_observation"])
            == identity(control["records"]["sidecar_sandbox"]), "sidecar sandbox binding differs")
    _noop_sandbox(sandbox)
    base = outer["guest_base"]
    namespace = "policy-sidecar-v13h-native-v" if provider else "policy-sidecar-native-v"
    require(type(base) is str and re.fullmatch(
            r"/work/validation/nezha-oem-policy-integration-20260829/" + namespace + r"[1-9][0-9]*", base),
            "sidecar native work directory differs")
    for prefix in (base, base + "/inputs"):
        require(sandbox["effective_mount_flags"][prefix] & 1, "sidecar sealed inputs were writable")
    require(sandbox["argv"] == ["/usr/bin/python3", "-I", "-B", base + "/inputs/driver.py", "--base", base]
            and native["driver"]["path"] == base + "/inputs/driver.py"
            and native["collector"]["path"] == base + "/inputs/bound_util.py"
            and outer["collector"]["path"] == base + "/inputs/bound_util.py"
            and outer["launcher"]["path"] == base + "/inputs/run.py"
            and identity(native["staging_manifest"]) == identity(outer["staging_manifest"]),
            "sidecar isolated invocation differs")
    require(native["limits"] == {"command_cpu_hard_seconds": 11, "command_cpu_soft_seconds": 10,
            "command_wall_seconds": 20, "file_size_soft_and_hard_bytes": 16 << 20,
            "initial_free_bytes": 256 << 20, "log_cap_each_bytes": 16 << 20, "whole_job_wall_seconds": 180}
            and native["environment"] == {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "TMPDIR": "/tmp"},
            "native sidecar execution limits or environment differ")

    def successful(command, supervisor=False):
        require(type(command["exit_code"]) is int and command["exit_code"] == 0
                and command["timed_out"] is False and command["log_overflow"] is False
                and command["whole_process_group_killed"] is False and command["all_pipes_eof"] is True
                and command["log_cap_each_bytes"] == 16 << 20 and command["supervisor_log_separated"] is supervisor
                and set(command["logs"]) == ({"stdout", "stderr", "supervisor"} if supervisor else {"stdout", "stderr"})
                and identity(command["logs"]["stderr"]) == avb._identity(b""), "native sidecar command did not complete cleanly")
        for row in command["logs"].values():
            avb._digest(row["sha256"])
            require(type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= 16 << 20
                    and (row["size_bytes"] != 0 or row["sha256"] == avb._sha(b""))
                    and row["path"].startswith(base + "/results/"),
                    "native sidecar log bound or destination differs")

    commands = native["commands"]
    require(len(commands) == 14 and len(outer["commands"]) == 3, "native sidecar command coverage differs")
    for command in commands:
        successful(command)
    for index, command in enumerate(outer["commands"]):
        successful(command, index == 1)
        if index != 1:
            require(command["argv"] == ["/usr/bin/git", "--no-optional-locks", "-C",
                "/work/evolution/system/sepolicy", "rev-parse", "HEAD"]
                and identity(command["logs"]["stdout"]) == avb._identity((pins["source_revision"] + "\n").encode()),
                "sidecar live source revision was not preserved")
    require(outer["nsjail"]["sha256"] == "3f97556c3cf8a83d3f5ae854e6dfc2f345355ead547dd661d07a369b6c2ba280"
            and outer["commands"][1]["argv"][0] == outer["nsjail"]["path"], "sidecar native jail changed")
    require(set(native["tools"]) == {"bash", "cat", "sha256sum", "cut"}, "native sidecar tool coverage differs")
    for index, name in enumerate(("bash", "cat", "sha256sum", "cut")):
        tool = native["tools"][name]
        machine = tool["abi"]["elf_machine"]
        loader = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        require(machine in (62, 183) and tool["abi"]["interpreter"] == loader
                and tool["identity"]["selected_path"] == "/usr/bin/" + name
                and tool["loader"]["selected_path"] == loader and tool["runtime"]
                and tool["runtime_command_index"] == 2 * index and tool["version_command_index"] == 2 * index + 1
                and commands[2 * index]["argv"] == [loader, "--list", "/usr/bin/" + name]
                and commands[2 * index + 1]["argv"] == ["/usr/bin/" + name, "--version"]
                and commands[2 * index]["logs"]["stdout"]["size_bytes"] > 0
                and commands[2 * index + 1]["logs"]["stdout"]["size_bytes"] > 0,
                "native sidecar tool/runtime selection differs")
        for row in [tool["identity"], tool["loader"], *tool["runtime"]]:
            avb._identity_spec(identity(row["canonical"]))
            require(row["canonical"]["size_bytes"] > 0 and type(row["symlink_chain"]) is list,
                    "native sidecar binary or runtime identity is absent")
        parsed = tool["loader_output_parse"]
        avb._keys(parsed, ("adapter", "abi", "original_stdout", "named_records_stdout", "initial_address_only_record",
            "named_file_paths", "named_records_checked_by_unchanged_frozen_parser", "unnamed_record_file_origin_claimed"),
            "native sidecar loader-output proof")
        require(parsed["adapter"] == "initial-aarch64-address-only-record-v1" and parsed["abi"] == tool["abi"]
                and identity(parsed["original_stdout"]) == identity(commands[2 * index]["logs"]["stdout"])
                and parsed["named_file_paths"] == sorted(row["selected_path"] for row in tool["runtime"])
                and len(set(parsed["named_file_paths"])) == len(parsed["named_file_paths"])
                and parsed["named_records_checked_by_unchanged_frozen_parser"] is True
                and parsed["unnamed_record_file_origin_claimed"] is False, "native sidecar named runtime proof differs")
        avb._identity_spec(identity(parsed["named_records_stdout"]))
        unnamed = parsed["initial_address_only_record"]
        if unnamed is None:
            require(identity(parsed["named_records_stdout"]) == identity(parsed["original_stdout"]),
                    "native sidecar loader output was altered without a recorded initial line")
        else:
            avb._keys(unnamed, ("line_index", "raw_line", "file_path", "file_identity_verified", "mapping_kind_identified"),
                      "unnamed native loader record")
            require(machine == 183 and type(unnamed["line_index"]) is int and unnamed["line_index"] == 0
                    and re.fullmatch(r"\t \(0x[0-9a-f]{16}\)\n", unnamed["raw_line"])
                    and unnamed["file_path"] is None and unnamed["file_identity_verified"] is False
                    and unnamed["mapping_kind_identified"] is False
                    and parsed["original_stdout"]["size_bytes"] == parsed["named_records_stdout"]["size_bytes"]
                        + len(unnamed["raw_line"].encode()), "unqualified or misattributed unnamed loader record")

    roles = [name + "-" + suffix for name in ("plat", "system_ext", "product") for suffix in ("cil", "mapping")]
    require([row["role"] for row in native["inputs"]] == roles
            and [row["runtime_path"] for row in native["inputs"]] == list(RUNTIME_INPUTS[:6]),
            "sidecar compiler input coverage or ordering differs")
    for row, runtime in zip(native["inputs"], RUNTIME_INPUTS):
        selected = control["policy_files"][runtime]
        require(identity(row) == identity(selected) == avb._identity(held[runtime])
                and row["native_compiler_input"] == selected["native_path"]
                and row["filename"] == row["role"] + ".cil"
                and row["derived_input_path"] == base + "/inputs/" + row["filename"],
                "sidecar input is not the sealed actual compiler file")
    require(len(native["recipes"]) == len(native["outputs"]) == 3, "three source recipes and native outputs required")
    pipeline = '/usr/bin/cat "$1" "$2" | /usr/bin/sha256sum | /usr/bin/cut -d\' \' -f1 > "$3"'
    def arguments(left, right, destination):
        return ["/usr/bin/bash", "--noprofile", "--norc", "-euo", "pipefail", "-c", pipeline,
                "sidecar-recipe", left, right, destination]
    known = {}
    for index, name in enumerate(("plat", "system_ext", "product")):
        pair_roles = roles[2 * index:2 * index + 2]
        recipe, output = native["recipes"][index], native["outputs"][index]
        expected = hashlib.sha256(held[RUNTIME_INPUTS[2 * index]] + held[RUNTIME_INPUTS[2 * index + 1]]).hexdigest().encode() + b"\n"
        known[name] = expected
        require(recipe == {"module": name + "_sepolicy_and_mapping.sha256_gen",
            "source_modules": [":" + name + "_sepolicy.cil", ":" + name + "_mapping_file"],
            "ordered_input_roles": pair_roles, "command": pins["recipe"],
            "line_start": (514, 531, 549)[index], "line_end": (522, 539, 557)[index]},
            "pinned Android source recipe order differs")
        destination = base + "/results/derived/" + name + "_sepolicy_and_mapping.sha256"
        require(output["name"] == name and output["ordered_input_roles"] == pair_roles
                and output["command_index"] == 8 + index and output["native_installed_path"] is None
                and output["provenance"] == ("derived-from-sealed-v13h-inputs" if provider else "derived-from-sealed-export4-inputs")
                and output["output"]["path"] == destination and output["ascii_content"].encode() == expected
                and identity(output["output"]) == avb._identity(expected)
                and commands[8 + index]["argv"] == arguments(*[base + "/inputs/" + r + ".cil" for r in pair_roles], destination),
                "native sidecar is not the exact ordered CIL/mapping digest plus LF")
    checks = {row["name"]: row for row in native["checks"]}
    require(len(native["checks"]) == len(checks) == 6 and set(checks) == {"plat-known-answer", "system_ext-known-answer",
            "product-known-answer", "reversed-order", "changed-input", "missing-final-lf"}
            and all(row["status"] == "passed" for row in checks.values()), "native sidecar negative cases are absent or failed")
    first, second = held[RUNTIME_INPUTS[0]], held[RUNTIME_INPUTS[1]]
    changed = bytes([first[0] ^ 1]) + first[1:]
    mutations = {"reversed-order": hashlib.sha256(second + first).hexdigest().encode() + b"\n",
                 "changed-input": hashlib.sha256(changed + second).hexdigest().encode() + b"\n",
                 "missing-final-lf": known["plat"][:-1]}
    for index, (name, expected) in enumerate(mutations.items(), 11):
        require(checks[name]["command_index"] == index and checks[name]["rejected_by_exact_output_check"] is True
                and identity(checks[name]["output"]) == avb._identity(expected) and expected != known["plat"]
                and checks[name]["output"]["path"] == base + "/results/" + name + ".sha256",
                "native sidecar negative output was not independently rejected")
    left, right = [base + "/inputs/plat-" + suffix + ".cil" for suffix in ("cil", "mapping")]
    expected_negative_commands = [arguments(right, left, base + "/results/reversed-order.sha256"),
        arguments(base + "/results/changed-plat.cil", right, base + "/results/changed-input.sha256"),
        ["/usr/bin/bash", "--noprofile", "--norc", "-euo", "pipefail", "-c",
         'printf \'%s\' "$1" > "$2"', "negative-lf", known["plat"].decode().rstrip("\n"),
         base + "/results/missing-final-lf.sha256"]]
    require([row["argv"] for row in commands[11:]] == expected_negative_commands
            and all(identity(row["logs"]["stdout"]) == avb._identity(b"") for row in commands[8:]),
            "native sidecar negative invocation or redirected output differs")
    require(native["changed_input"] == {"original_role": "plat-cil", "mutation": "first-byte-xor-1",
        "output": {"path": base + "/results/changed-plat.cil", **avb._identity(changed)}}, "native sidecar negative input differs")
    return {"source_recipe_bound": True, "native_known_answers": 3, "native_negative_cases": 3, "skipped": 0,
        "native_installed_sidecars_captured": False, "android_genrule_execution_claimed": False,
        "derivation_kind": "sealed-v13h-CIL-and-mapping" if provider else "sealed-v12-export4-CIL-and-mapping",
        "native_reexecuted_by_this_command": False}


def qualify_provider_policy(records, control, contract):
    """Admit one reviewed native provider snapshot, never a projected policy.

    The complete source, action and effect inventories remain exact pinned
    sections of the native receipt. Their canonical hashes preserve every
    nested fact without recreating the native CIL comparator or relabeling its
    deliberately limited inner scope. Independent byte and producer bindings
    below connect that proof to the files actually selected for replacement.
    """
    build, analysis = records["policy_build"], records["policy_analysis"]
    pins = contract["provider_policy"]
    _build(build)
    require(analysis["schema_version"] == 1 and type(analysis["schema_version"]) is int
            and analysis["operation"] == pins["analysis_operation"] and analysis["status"] == "verified"
            and analysis["build_phase"] == build["phase"] == pins["build_phase"]
            and analysis["provider_phase"] == build["provider_phase"] == pins["provider_phase"]
            and analysis["provider_profile_selected"] is True and analysis["policy_only"] is True
            and analysis["strict_compiler_flags_verified"] is True
            and analysis["compiler_temporary_to_analyzed_final_copy_verified"] is True
            and analysis["all_guarded_inputs_unchanged"] is True, "v13h native policy analysis is incomplete")
    for key in ("full_treble_apk_labeling_pass", "policy_compiler_replayed", "source_or_android_output_modified",
                "images_changed", "phone_accessed", "provider_runtime_built", "provider_runtime_installation_verified",
                "strict_elf_actions_verified", "provider_elf_compatibility_verified", "complete_rom_or_runtime_support_proven"):
        require(analysis[key] is False, "v13h policy analysis claims unsupported scope: " + key)
    require(build["policy_only"] is True and build["preservation_verified"] is True
            and build["protected_runtime_outputs_unchanged"] is True and build["remaining_build_processes"] == []
            and build["preservation_error"] is None and build["protected_runtime_outputs_error"] is None
            and build["post_build_error"] is None, "v13h build preservation or completion differs")
    for key in ("provider_runtime_requested", "provider_runtime_built", "strict_elf_actions_verified", "images_requested",
                "complete_rom_built", "phone_accessed", "forced_kill_after_timeout"):
        require(build[key] is False, "v13h build claims unsupported scope: " + key)
    for field, role in (("build_result_sha256", "policy_build"), ("build_log_sha256", "policy_build_log"),
                        ("build_source_manifest_sha256", "policy_source_manifest"), ("build_sandbox_sha256", "policy_build_sandbox")):
        require(analysis[field] == control["records"][role]["sha256"], "v13h analysis build linkage differs")
    require(identity(build["source_manifest"]) == identity(control["records"]["policy_source_manifest"])
            and identity(build["log"]) == identity(control["records"]["policy_build_log"])
            and records["policy_build_sandbox"] == build["sandbox"], "v13h build capture or sandbox differs")
    require(set(pins["proof_sections"]) == PROVIDER_PROOF_SECTIONS, "v13h complete proof coverage differs")
    for name in sorted(PROVIDER_PROOF_SECTIONS):
        require(avb._identity(json_bytes(analysis[name])) == pins["proof_sections"][name],
                "reviewed complete v13h proof changed: " + name)
    selection = analysis["selection"]
    require(selection["schema_version"] == 1 and selection["operation"] == "admit-actual-v13h-policy-only-analysis"
            and selection["source_and_history_verification_required"] is True
            and selection["build_record_identity"] == identity(control["records"]["policy_build"])
            and selection["phase"] == build["phase"] and selection["provider_phase"] == build["provider_phase"]
            and selection["argv"] == build["argv"]
            and build["argv"][:3] == ["build/soong/soong_ui.bash", "--make-mode", "-j8"] and len(build["argv"]) == 34,
            "v13h exact native invocation or selection differs")
    commit = build["provider_fixup_commit"]
    require(analysis["provider_fixup_manifest_identity"] == selection["provider_fixup_manifest_identity"]
            == build["provider_fixup_manifest_identity"]
            and analysis["provider_fixup_commit_identity"] == selection["provider_fixup_commit_identity"]
            == avb._identity(json_bytes(commit))
            and commit["manifest_sha256"] == analysis["provider_fixup_manifest_identity"]["sha256"]
            and commit["verified"] is True and commit["last_event"]["sequence"] == 8
            and commit["last_event"]["operation_count"] == 3
            and commit["last_event"]["event"] == "commit_verified", "v13h three-operation installation differs")
    source = analysis["source_history_proof"]
    require(source == build["source_history_proof"] == build["post_build_source_verification"]
            and source["operation"] == "verify-v13h-policy-input-sources-after-build" and source["verified"] is True
            and source["actual_commit"] == commit and source["manifest_identity"] == analysis["provider_fixup_manifest_identity"]
            and source["operation_count"] == 3 and source["journal_events"] == 9
            and source["component_trees_checked"] == 3 and source["unchanged_component_trees_checked"] == 4
            and source["normal_android_enforcing_required"] is True and source["live_outputs_checked"] is False,
            "v13h source/history proof differs")
    cross, tool_cross = analysis["provider_policy_contract_crosspin"], analysis["provider_policy_tool_crosspin"]
    require(analysis["provider_contract_sha256"] == pins["native_contract"]["sha256"]
            and cross["verified"] is True and cross["actual_native_contract"] == pins["native_contract"]
            and cross["actual_input_profile"] == pins["input_contract"]
            and cross["preserved_semantic_contract"] == pins["semantic_contract"]
            and cross["only_changed_json_path"] == ["required_contracts", "provider_inputs", "sha256"]
            and cross["all_other_contract_values_exact"] is True and cross["semantic_contract_bytes_replaced"] is False
            and cross["source_or_cil_modified"] is False
            and tool_cross["verified"] is True and tool_cross["actual_native_policy_tool"] == pins["native_policy_tool"]
            and tool_cross["new_policy_contract"] == pins["native_contract"]
            and tool_cross["old_policy_contract"] == pins["semantic_contract"]
            and tool_cross["all_other_tool_bytes_exact"] is True and tool_cross["source_files_modified"] is False,
            "v13h semantic/native contract crosspin differs")
    for path, name in (("config/nezha-framework-provider-policy.json", "native_contract"),
                       ("config/nezha-framework-providers.json", "input_contract"),
                       ("scripts/framework_provider_policy.py", "native_policy_tool")):
        avb._small(ROOT / path, TEXT, pins[name])
    native, files = analysis["actual_compiler_inputs"], control["policy_files"]
    require([row["runtime_path"] for row in native] == list(RUNTIME_INPUTS), "actual ten compiler inputs/order differ")
    require(files["combined"]["native_path"].endswith(COMBINED_SUFFIX),
            "ODM replacement must be the actual factory-combined binary, not the source-only installed policy")
    native_out = files["combined"]["native_path"].removesuffix(COMBINED_SUFFIX)
    require(native_out and native_out != "/", "invalid physical native OUT root")
    for row in native:
        selected = files[row["runtime_path"]]
        require(identity(row) == identity(selected) and row["resolved_path"] == selected["native_path"],
                "selected CIL is not the actual compiler input")
    semantics = analysis["semantics"]
    review = records["provider_complete_effect_review"]
    review_digest = avb._sha(json.dumps(review, sort_keys=True, separators=(",", ":")).encode())
    require(analysis["complete_effect_review"] == selection["complete_effect_review"]
            == identity(control["records"]["provider_complete_effect_review"])
            and review_digest == pins["complete_review_canonical_sha256"]
            and review["complete_effect_inventory_reviewed"] is True
            and review["baseline_receipt_sha256"] == analysis["baseline_receipt_sha256"] == pins["baseline"]["sha256"]
            and selection["baseline_receipt"] == pins["baseline"]
            and review["baseline_corpus_identity_sha256"] == pins["baseline_corpus_sha256"]
            and review["provider_contract_sha256"] == pins["semantic_contract"]["sha256"],
            "complete provider effect review or actual baseline differs")
    require(semantics["status"] == "verified" and semantics["operation"] == "actual-v12f-to-v13f-provider-semantic-delta"
            and semantics["provider_contract_sha256"] == pins["semantic_contract"]["sha256"]
            and semantics["actual_v12f_baseline_receipt_sha256"] == pins["baseline"]["sha256"]
            and semantics["candidate_input_identities"] == [{"runtime_path": row["runtime_path"], **identity(row)} for row in native]
            and semantics["native_provenance_verified_by_this_module"] is False
            and semantics["native_actions_contexts_images_or_hardware_verified_by_this_module"] is False,
            "v13h reviewed semantic comparison differs")
    before = semantics["actual_baseline_input_identities"]
    require([row["runtime_path"] for row in before] == list(RUNTIME_INPUTS)
            and avb._sha(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()) == pins["baseline_corpus_sha256"],
            "provider baseline compiler corpus differs")
    for old, new in zip(before, native):
        if old["runtime_path"] != RUNTIME_INPUTS[2]:
            require(identity(old) == identity(new), "provider policy changed a non-system_ext compiler input")
    impact = semantics["effect_inventory"]
    require(impact["status"] == "review-required" and impact["operation"] == "provider-semantic-effect-inventory"
            and impact["native_capture_authenticated"] is False and impact["complete_effect_review_admitted"] is False
            and impact["contract_projection_matches_candidate_semantics"] is True
            and impact["original_assertions_retained"] == 6366 and impact["assertions_after"] == 6370
            and impact["new_assertions"] == 4 and impact["new_source_dontaudit_statements"] == 2
            and impact["source_additions"] == {"allow": 26, "dontaudit": 2, "typetransition": 2, "neverallow": 4}
            and impact["all_six_oem_public_mappings_unchanged"] is True
            and impact["helper_effective_property_set_permissions"] == 0 and impact["denial_logging_unchanged"] is False,
            "provider assertions, permissions or inner evidence scope differs")
    properties, properties_raw = read_json(ROOT / "config/nezha-oem-properties.json")
    _, oem_raw = read_json(ROOT / "config/nezha-oem-policy.json")
    expected_properties = properties["native_effective_ordinary_allow_edges"]
    require(analysis["oem_property_contract_sha256"] == avb._sha(properties_raw)
            and analysis["oem_contract_sha256"] == avb._sha(oem_raw), "native OEM contracts differ")
    for observed in (impact["oem_property_ordinary_allow_totals"], analysis["native_oem_check"]["property_effective_ordinary_allow_edges"]):
        require(set(observed) == set(expected_properties), "provider property effect coverage differs")
        for name, expected in expected_properties.items():
            require({k: observed[name][k] for k in ("count", "sha256_sorted_compact_json_rows")} == expected,
                    "provider changed the retained OEM property effects")
    binaries = {row["name"]: row for row in analysis["analyses"]}
    require(len(binaries) == len(analysis["analyses"]) == 3 and set(binaries) == {
        "combined", "source-precompiled", "source-neverallows"}, "native permissive analysis coverage differs")
    paths = {"combined": files["combined"]["native_path"],
        "source-precompiled": native_out + "/target/product/nezha/odm/etc/selinux/precompiled_sepolicy",
        "source-neverallows": native_out + "/soong/.intermediates/system/sepolicy/sepolicy_neverallows/android_common/policy"}
    for name, row in binaries.items():
        require(type(row["exit_code"]) is int and row["exit_code"] == 0
                and type(row["stdout_bytes"]) is int and row["stdout_bytes"] == 0
                and row["stdout_sha256"] == avb._sha(b"") and row["unfiltered"] is True
                and row["zero_permissive_domains"] is True and row["sandbox_observed"] is True
                and row["build_path"] == paths[name], "native provider policy permissive analysis differs")
        bindings = [r for r in analysis["input_bindings"] if r["path"] == paths[name]]
        require(len(bindings) == 1 and identity(bindings[0]) == identity(row), "analyzed native binary identity differs")
        avb._digest(row["sandbox_receipt_sha256"]); avb._digest(row["mountinfo_sha256"])
    require(identity(binaries["combined"]) == identity(files["combined"]), "selected factory-combined policy differs")
    contexts, oem, producer = analysis["native_context_checks"], analysis["native_oem_check"], analysis["provider_input_action"]
    require(len(contexts) == 9 and {row["target"] for row in contexts} == CONTEXT_TARGETS,
            "required factory context checks are incomplete")
    for row in contexts + [oem, producer]:
        require(row["status"] == "executed_and_passed" and row["fresh_execution_observed"] is True
                and row["build_phase"] == analysis["build_phase"] and row["build_log_sha256"] == analysis["build_log_sha256"]
                and row["mtime_used_to_infer_execution"] is False and bool(row["ninja_success_records"])
                and type(row["action_log_line"]) is int and row["action_log_line"] > 0
                and type(row["action_log_text"]) is str and bool(row["action_log_text"]), "stale native provider policy check")
    for row in contexts:
        matches = [r for r in row["inputs"] if r["resolved_path"] == files["combined"]["native_path"]]
        require(row["empty_stamp_alone_used_as_evidence"] is False and len(matches) == 1
                and identity(matches[0]) == identity(files["combined"]), "context check used a different combined binary")
    require(producer["operation"] == "verify-policy-only-provider-inputs"
            and producer["target"] == "nezha_framework_provider_inputs_check"
            and producer["provider_phase"] == pins["provider_phase"] and producer["original_input_count"] == 42
            and producer["current_reviewed_input_count"] == 42 and producer["verified_payload_count"] == 31
            and producer["unchanged_payload_count"] == 30 and producer["derived_payload_count"] == 1
            and producer["declared_output_count"] == 32 and len(producer["inputs"]) == 42
            and len(producer["payload_outputs"]) == 31 and producer["native_receipt_exact_bytes_verified"] is True
            and producer["payload_outputs_exact_bytes_verified"] is True and producer["all_copy_mappings_verified"] is True
            and producer["original_inputs_rehashed"] is True and producer["original_proprietary_inputs_preserved"] is True
            and producer["transitive_oem_dependency"]["content_dependency_verified"] is True
            and producer["transitive_oem_dependency"]["order_only_dependency_used_as_evidence"] is False
            and producer["scope"] and all(value is False for value in producer["scope"].values()),
            "fresh provider producer or its retained-input scope differs")
    assertions = {"neverallow": 5980, "neverallowx": 390}
    require(oem["target"] == "nezha_factory_oem_policy_check" and oem["guard_json_alone_used_as_evidence"] is False
            and oem["actual_strict_compiler_input_count"] == 10 and oem["input_binding_proof"]["count"] == 22
            and len(oem["inputs"]) == 23 and oem["input_binding_proof"]["exact_paths_hashes_sizes_verified"] is True
            and oem["full_guard_result_independently_rebound"] is True and oem["executed_tool_runtime_files_rehashed"] is True
            and oem["all_copy_mappings_verified"] is True and oem["provider_profile_present"] is True
            and oem["assertion_statement_counts"] == assertions
            and identity(oem["output"]) == identity(control["records"]["native_oem_guard"]),
            "native provider OEM guard binding differs")
    for row in native:
        matches = [r for r in oem["inputs"] if r["path"] == row["compiler_input"]]
        require(len(matches) == 1 and identity(matches[0]) == identity(row)
                and matches[0]["resolved_path"] == row["resolved_path"], "OEM guard did not consume the actual compiler inputs")
    raw_guard = records["native_oem_guard"]
    require(raw_guard["schema_version"] == 1 and raw_guard["operation"] == "check-nezha-oem-native-policy-inputs"
            and raw_guard["status"] == "verified" and raw_guard["contract_sha256"] == analysis["oem_contract_sha256"]
            and raw_guard["property_contract_sha256"] == analysis["oem_property_contract_sha256"]
            and raw_guard["provider_contract_sha256"] == pins["native_contract"]["sha256"]
            and raw_guard["helper_effective_property_set_grants"] == 0 and raw_guard["permissive_cil_declarations"] == 0
            and raw_guard["original_factory_inputs_preserved"] is True and raw_guard["existing_binder_derivation_preserved"] is True
            and raw_guard["all_inputs_rehashed_unchanged"] is True and raw_guard["assertion_statement_counts"] == assertions
            and raw_guard["property_effective_ordinary_allow_edges"] == expected_properties
            and raw_guard["tool_sources_sha256"] == oem["source_tool_sha256"], "raw native provider OEM result differs")
    derivation = records["vendor_derivation"]
    correction, correction_raw = read_json(ROOT / "config/vendor-policy-correction.json")
    require(derivation["operation"] == "nezha-factory-binder-correction-v1"
            and derivation["contract_sha256"] == avb._sha(correction_raw)
            and derivation["factory_package_sha256"] == contract["factory_package_sha256"]
            and derivation["output"] == correction["output"] and derivation["measured"] == correction["expected"]
            and derivation["inputs"] == correction["inputs"]
            and [{k: row[k] for k in ("runtime_path", "sha256", "size_bytes")} for row in derivation["input_manifest"]] == correction["inputs"]
            and derivation["preservation"] == {k: True for k in ("all_unselected_bytes_and_line_positions", "all_assertions",
                "type_role_alias_attribute_and_mapping_declarations", "valid_process_binder_grants", "fd_and_service_manager_grants")}
            and derivation["output_readback_verified"] is True and derivation["all_inputs_rehashed_unchanged"] is True
            and derivation["tool_sha256"] == oem["source_tool_sha256"]["vendor_policy.py"]
            and derivation["publisher_sha256"] == oem["source_tool_sha256"]["artifact_files.py"], "vendor correction receipt differs")
    require(files[RUNTIME_INPUTS[7]]["native_path"] == native_out + VENDOR_SUFFIX
            and identity(files[RUNTIME_INPUTS[7]]) == identity(correction["output"]), "vendor correction output changed")
    receipt_path = files[RUNTIME_INPUTS[7]]["native_path"].removesuffix("vendor_sepolicy.cil") + "receipt.json"
    matches = [r for r in analysis["input_bindings"] if r["path"] == receipt_path]
    require(len(matches) == 1 and identity(matches[0]) == identity(control["records"]["vendor_derivation"]),
            "vendor derivation is not bound by the current native analysis")
    held = {name: avb._small(row["path"], POLICY, row) for name, row in files.items()}
    replacements = {"vendor": {"/etc/selinux/vendor_sepolicy.cil": files[RUNTIME_INPUTS[7]]},
                    "odm": {"/etc/selinux/precompiled_sepolicy": files["combined"]}}
    for index, name in ((0, "plat"), (2, "system_ext"), (4, "product")):
        value = hashlib.sha256(held[RUNTIME_INPUTS[index]] + held[RUNTIME_INPUTS[index + 1]]).hexdigest().encode() + b"\n"
        replacements["odm"]["/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"] = {
            **avb._identity(value), "derived_bytes": value, "sidecar_name": name,
            "source_kind": "derived-from-sealed-native-cil-and-mapping",
            "ordered_input_roles": [RUNTIME_INPUTS[index], RUNTIME_INPUTS[index + 1]]}
    sidecars = qualify_sidecar_derivation(records, control, held, contract)
    return replacements, {"current_factory_combined_binary_bound": True, "sidecars_recomputed_and_matched": True,
        "assertion_statements_retained": 6366, "assertion_statements_added": 4, "assertion_statements_total": 6370,
        "normal_android_permissive_domains": 0, "full_treble_apk_labeling_proven": False,
        "native_policy_reexecuted": False, "sidecar_derivation": sidecars, "native_policy_snapshot": pins["build_phase"],
        "current_active_source_compatibility_proven": False, "sidecars_observed_at_native_install_paths": False,
        "provider_profile_selected": True, "provider_runtime_support_proven": False,
        "complete_native_provider_proof_sections_bound": True, "complete_effect_review_bound": True}


def qualify_policy3_basis(records, control, contract):
    """Bind the scoped actual Evolution source review, without promoting its limits.

    Binary permissive, freeze-comparator and installed-sidecar checks are
    separate requirements. This helper alone cannot admit a preparation.
    """
    pins = contract["evolution_policy"]
    build, review = records["policy_build"], records["policy_analysis"]
    build_id = identity(control["records"]["policy_build"])
    require(build["schema_version"] == 1 and type(build["schema_version"]) is int
            and build["operation"] == pins["build_operation"] and build["phase"] == pins["build_phase"]
            and build["profile"] == "policy" and build["profile_completed"] is True
            and build["native_invocation_executed"] is True and build["native_process_succeeded"] is True
            and build["preflight_completed"] is True and build["profile_validation_verified"] is True
            and build["preflight_error"] is None and build["postcheck_errors"] == []
            and build["argv"] == build["soong_argv"]
            and build["argv"] == ["build/soong/soong_ui.bash", "--make-mode", "-j8", *build["goals"]]
            and len(build["goals"]) == 32 and build["goals"][-1] == "selinux_policy",
            "actual policy3 ordinary build did not complete")
    for key in ("source_mutation_requested", "capture_only", "complete_rom_ready", "signed_flashable_rom_verified",
                "fresh_action_claims_from_matching_bytes", "image_reproducibility_verified"):
        require(build[key] is False, "policy3 build claims unsupported scope: " + key)
    env = build["fixed_environment"]
    require({key: env[key] for key in ("TARGET_PRODUCT", "TARGET_RELEASE", "TARGET_BUILD_VARIANT", "LINEAGE_BUILD")}
            == {"TARGET_PRODUCT": "lineage_nezha", "TARGET_RELEASE": "bp4a", "TARGET_BUILD_VARIANT": "user", "LINEAGE_BUILD": "nezha"},
            "policy3 is not the selected Evolution user product")
    native = build["invocation"]
    require(type(native["exit_code"]) is int and native["exit_code"] == 0
            and all(native[key] is True for key in ("process_reaped", "streams_complete", "ninja_observed",
                "ninja_argv_verified", "ninja_limits_verified", "sandbox_checks_passed"))
            and all(native[key] is False for key in ("timed_out", "forced_kill", "output_overflow", "sandbox_fallback", "disk_floor_breached")),
            "policy3 native invocation was incomplete or relaxed")
    guards = build["source_and_input_admission_before"]
    require(guards == build["source_and_input_admission_after"] and set(guards) == {
        "verify_immutable_archive", "verify_protected_inputs", "verify_selected_inputs", "verify_source_history",
        "verify_source_lock", "verify_strict_settings"}, "policy3 six source/input guard groups differ")
    settings = {"framework_matrix_source": "device/xiaomi/nezha/generated/framework-compatibility-matrix.xml",
                "maximum": 4096, "no_bionic_page_size_macro": True, "prebuilt_alignment_check": True, "strict_elf_checks": True}
    require(guards["verify_strict_settings"] == settings
            and all({key: build["source_observations_" + when]["strict_settings"][key] for key in settings} == settings
                    for when in ("before", "after")), "policy3 strict 4 KiB settings differ")
    require(review["schema_version"] == 1 and review["operation"] == pins["review_operation"]
            and review["status"] == pins["review_status"] and identity(review["actual_result"]) == build_id,
            "policy3 scoped review is not for the actual completed build")
    require(set(pins["review_sections"]) == POLICY3_REVIEW_SECTIONS, "policy3 complete scoped-review coverage differs")
    for name in sorted(POLICY3_REVIEW_SECTIONS):
        require(avb._identity(json_bytes(review[name])) == pins["review_sections"][name],
                "reviewed complete policy3 section changed: " + name)
    evidence = pins["review_evidence"]
    require(len(review["evidence"]) == len(evidence) == 10
            and {row["path"]: identity(row) for row in review["evidence"]}
                == {row["path"]: identity(row) for row in evidence.values()}, "policy3 review evidence coverage differs")
    for role, row in evidence.items():
        require(identity(control["records"][role]) == identity(row), "policy3 selected review evidence differs: " + role)
    frozen = records["policy_review_freeze"]
    require(frozen["operation"] == "freeze-scoped-actual-policy3-review" and frozen["schema_version"] == 1
            and frozen["final_recheck"] == {"all_equal": True, "evidence_pins": 10, "own_members": 6, "retained_host_bodies": 89}
            and frozen["scope"] == review["scope"]
            and identity(frozen["dependencies"]["actual_result"]) == build_id
            and identity(frozen["dependencies"]["actual_decoded_capture"]) == identity(control["records"]["policy_retained_capture"]),
            "policy3 scoped review freeze differs")
    expected_members = {identity(control["records"][role])["sha256"]: identity(control["records"][role]) for role in (
        "policy_analysis", "policy_capture_mapping", "policy_oem_replay", "policy_freeze_selectors",
        "policy_native_log_review", "policy_m4_source_review")}
    require(len(frozen["files"]) == 6 and {row["sha256"]: identity(row) for row in frozen["files"]} == expected_members,
            "policy3 review freeze does not bind its six complete members")
    require(review["scope"]["host_cil_semantic_replay_verified"] is True
            and review["scope"]["preserved_property_label_effects_verified"] is True
            and review["scope"]["source_m4_and_native_command_forms_reviewed"] is True
            and all(review["scope"][key] is False for key in ("all12_binary_zero_permissive_verified",
                "complete_se_freeze_admission_verified", "complete_treble_apk_labeling_verified",
                "full_recursive_producer_provenance_verified", "new_image_basis_admitted", "hardware_or_runtime_verified", "complete_rom_ready")),
            "policy3 scoped review has been promoted into an unperformed check")
    completion = review["native_completion"]
    require(completion["ordinary_goals"] == 32 and completion["current_source_rows"] == 539
            and completion["source_projects"] == 13 and completion["guard_groups_rechecked_equal"] == 6
            and completion["native_exit_code"] == completion["wrapper_exit_code"] == 0
            and completion["complete_stdout_stderr_and_reaped"] is True,
            "policy3 source inventory or native completion differs")
    mapping = records["policy_capture_mapping"]
    require(identity(mapping["build_result"]) == build_id and len(mapping["files"]) == 89
            and all(mapping[key] is True for key in ("all89_base64_and_host_bodies_exact", "all89_guest_final_rechecks",
                "all89_host_final_rechecks", "all89_request_and_decoded_rows_exact", "gzip_decompression_equals_retained_plain",
                "invocation_equals_actual_result")), "policy3 retained input capture is incomplete")
    def captured(role):
        rows = [row for row in mapping["files"] if role in row["roles"]]
        require(len(rows) == 1, "missing or duplicate actual policy3 input role: " + role)
        row = rows[0]
        require(identity(row["host"]) == identity(row["original_native"]) == identity(row["retained_native"]),
                "policy3 retained and live input identities differ")
        return row
    files = control["policy_files"]
    for expected in pins["compiler_inputs"]:
        role = expected["runtime_path"]
        row = captured("factory_compiler_input:" + role)
        require(identity(files[role]) == identity(expected) == identity(row["original_native"])
                and files[role]["native_path"] == expected["native_path"] == row["original_native"]["path"],
                "selected policy3 CIL is not the exact actual compiler input")
    combined = captured("normal_binary:nezha_factory_precompiled_sepolicy")
    require(combined == review["strict_factory_compile"]["factory_binary"]
            and identity(files["combined"]) == identity(pins["combined"]) == identity(combined["original_native"])
            and files["combined"]["native_path"] == pins["combined"]["native_path"] == combined["original_native"]["path"]
            and files["combined"]["native_path"].endswith(COMBINED_SUFFIX),
            "policy3 replacement must be the actual factory-combined binary, not a source-only policy")
    require(review["strict_factory_compile"]["ten_compiler_inputs_in_exact_required_order"] is True
            and review["strict_factory_compile"]["ignore_neverallow_flag_present"] is False
            and review["strict_factory_compile"]["secilc_flags"] == ["-v", "-m", "-M", "true", "-G", "-c", "30"],
            "policy3 strict compiler recipe differs")
    replay, raw_oem = records["policy_oem_replay"], records["native_oem_guard"]
    require(replay["operation"] == "replay-actual-policy3-frozen-oem-composition" and identity(replay["build_result"]) == build_id
            and identity(replay["capture_mapping"]) == identity(control["records"]["policy_capture_mapping"])
            and avb._identity(json_bytes(replay["source_commit"])) == pins["source_commit"]
            and all(replay[key] is True for key in ("all_source_and_captured_inputs_rehashed_unchanged",
                "bundle62_payloads_rehashed_before_after", "source46_equal_to_actual539_before_after_inventory",
                "source46_exactly_equal_to_capability_composed_contract"))
            and replay["input_bindings_replayed_count"] == 83, "policy3 OEM source/input replay differs")
    semantic = replay["semantic_result"]
    require(avb._identity(json_bytes(semantic)) == pins["oem_semantics"]
            and set(replay["semantic_fields_equal_to_native_report"]) == set(semantic)
            and all(raw_oem[key] == value for key, value in semantic.items())
            and replay["native_report"] == captured("native_oem_output")
            and identity(replay["native_report"]["host"]) == identity(control["records"]["native_oem_guard"]),
            "complete policy3 semantic replay does not equal the captured native OEM output")
    base = semantic["evolution_policy_base_verification"]
    require(semantic["status"] == "verified" and semantic["helper_effective_property_set_grants"] == 0
            and semantic["permissive_cil_declarations"] == 0
            and semantic["assertion_statement_counts"] == {"neverallow": 6009, "neverallowx": 390}
            and semantic["legacy_property_edge_budget_reused_as_current"] is False
            and semantic["property_effective_edge_budget_basis"] == "independent-native-evolution-base-plus-owned-contracts"
            and base["immutable_original_assertions"] == 6366 and base["owned_provider_assertions"] == 4
            and base["base_assertions"] == 29 and base["all_source_access_audit_assertion_transition_forms_accounted_for"] is True
            and base["full_named_and_inherited_anonymous_closures_match_independent_reference"] is True
            and base["base_factory_duplicate_types"] == ["vendor_persist_camera_prop"]
            and base["vendor_source_delivery_into_factory_images_proven"] is False
            and base["binary_zero_permissive_check_performed"] is False and base["image_or_runtime_admitted"] is False,
            "policy3 exact Evolution/owned assertion and capability composition differs")
    _, base_raw = read_json(ROOT / "config/evolution-policy-base.json")
    require(base["contract_sha256"] == avb._sha(base_raw), "policy3 Evolution base contract differs")
    composition = review["source_and_oem_composition"]
    require(composition["assertions"] == {"original_contract": 6366, "provider": 4, "evolution_base": 29,
                "neverallow": 6009, "neverallowx": 390, "total": 6399}
            and composition["helper_effective_property_set_grants"] == composition["camera_vendor_init_set_grants"] == 0
            and composition["permissive_cil_declarations"] == 0 and composition["immutable_cil_inputs_preserved"] == 8,
            "policy3 assertion membership or disabled write capability differs")
    require(review["m4_recipe"]["all_three_capabilities_exactly_once"] == {
        "target_init_dev_config_property_writes": "false", "target_nezha_preserve_factory_property_labels": "true",
        "target_vendor_persist_camera_prop_vendor_init_writes": "false"}, "policy3 M4 capability guards differ")
    effects = review["seven_prefix_effects"]
    require(effects["complete_prefix_languages"] == 7 and effects["original_factory_labels_and_string_types_preserved"] is True
            and effects["camera_added_policy_reader_domains"] == ["mediashell_app", "mosey_app", "updater_app"]
            and effects["camera_writer_domains"] == ["hal_camera_default", "init"]
            and effects["camera_writer_changes"] == 0 and effects["camera_readers_lost"] == []
            and effects["context_relabel_only_edge_deltas"] == effects["audio_and_usb_ordinary_edge_deltas"] == 0,
            "policy3 seven-prefix property effects differ")
    contexts = review["native_context_checks"]
    require(contexts["nine_factory_context_and_structural_commands_observed"] is True
            and contexts["file_hwservice_service_aggregates_equal_ordered_five_inputs"] is True
            and contexts["system_ext_rows"]["property"] == {"base": 25, "owned": 8, "full": 33}
            and contexts["warnings_not_counted_as_passes_or_suppressed"] is True,
            "policy3 context composition or warning accounting differs")
    derivation = records["vendor_derivation"]
    correction, correction_raw = read_json(ROOT / "config/vendor-policy-correction.json")
    require(identity(control["records"]["vendor_derivation"]) == identity(captured("factory_vendor_derivation_receipt")["host"])
            and derivation["operation"] == "nezha-factory-binder-correction-v1"
            and derivation["contract_sha256"] == avb._sha(correction_raw)
            and derivation["factory_package_sha256"] == contract["factory_package_sha256"]
            and derivation["inputs"] == correction["inputs"] and derivation["output"] == correction["output"]
            and derivation["measured"] == correction["expected"]
            and derivation["preservation"] == {k: True for k in ("all_unselected_bytes_and_line_positions", "all_assertions",
                "type_role_alias_attribute_and_mapping_declarations", "valid_process_binder_grants", "fd_and_service_manager_grants")}
            and derivation["output_readback_verified"] is True and derivation["all_inputs_rehashed_unchanged"] is True
            and derivation["tool_sha256"] == raw_oem["tool_sources_sha256"]["vendor_policy.py"]
            and derivation["publisher_sha256"] == raw_oem["tool_sources_sha256"]["artifact_files.py"]
            and identity(files[RUNTIME_INPUTS[7]]) == identity(correction["output"]), "policy3 Binder derivation changed")
    held = {name: avb._small(files[name]["path"], POLICY, files[name]) for name in (*RUNTIME_INPUTS, "combined")}
    return held, {"scoped_current_source_basis_bound": True, "complete_policy3_oem_semantics_bound": True,
        "max_page_size_supported": 4096,
        "assertion_statements_retained": 6366, "provider_assertion_statements": 4, "evolution_assertion_statements": 29,
        "assertion_statements_total": 6399, "helper_property_write_grants": 0, "camera_vendor_init_property_write_grants": 0,
        "permissive_cil_declarations": 0, "full_recursive_producer_provenance_verified": False,
        "complete_treble_apk_labeling_proven": False, "vendor_source_delivery_into_factory_images_proven": False,
        "native_binary_zero_permissive_verified_by_basis": False, "native_freeze_verified_by_basis": False,
        "native_sidecars_verified_by_basis": False, "image_admission_enabled_by_basis": False}


def qualify_policy3_binaries(records, control, contract):
    """Require the twelve actual, unfiltered analyses of the selected binaries."""
    result = records["policy_binary_validation"]
    require(result["schema_version"] == 1 and type(result["schema_version"]) is int
            and result["operation"] == "policy3-twelve-unfiltered-permissive-checks-v1"
            and result["passed"] is True and result["zero_permissive_binaries_verified"] is True
            and result["errors"] == [] and result["unreached_binary_modules"] == []
            and identity(result["build_result"]) == identity(control["records"]["policy_build"])
            and identity(result["capture"]) == identity(control["records"]["policy_retained_capture"]),
            "policy3 unfiltered binary checks are incomplete or use another build")
    for key in ("complete_rom_ready", "full_treble_apk_labeling_verified", "host_unprivileged_execution_claimed",
                "images_modified", "new_image_basis_verified", "phone_accessed", "policy_compiled_here",
                "policy_semantics_or_full_provenance_verified", "source_or_android_output_modified"):
        require(result[key] is False, "policy3 binary analysis has unsupported scope: " + key)
    require(len(result["checks"]) == 2 and [row["name"] for row in result["checks"]] == ["source-after", "inputs-after"]
            and all(row["verified"] is True for row in result["checks"]), "policy3 final binary input/source rechecks differ")
    before, after = result["source_before"], result["checks"][0]["value"]
    require(before["verified"] is True and after["verified"] is True
            and all(identity(before[key]) == identity(after[key]) for key in ("configuration", "source_proof")),
            "policy3 binary source changed")
    inputs = result["inputs_before"]
    require(len(inputs) == 39 and len({row["path"] for row in inputs}) == 39,
            "policy3 binary/tool input coverage differs")
    freezes = result["freeze_inputs"]
    require(result["freeze_capture_complete"] is True and len(freezes) == 4
            and [row["role"] for row in freezes] == ["sepolicy_freeze_test_tool", "current_platform_public_freeze_cil",
                "api_202504_platform_public_freeze_cil", "se_freeze_test_stamp"]
            and all(row["comparison_execution_claimed_by_capture"] is False
                    and identity(row["original"]) == identity(row["retained"]) for row in freezes)
            and result["checks"][1]["value"] == inputs + [row[name] for row in freezes for name in ("original", "retained")]
            and len({row["path"] for row in result["checks"][1]["value"]}) == 47,
            "policy3 final binary inputs or four separate freeze captures differ")
    native_out = control["policy_files"]["combined"]["native_path"].removesuffix(COMBINED_SUFFIX)
    analyzer_path = native_out + "/host/linux-x86/bin/sepolicy-analyze"
    analyzer = [row for row in inputs if row["path"] == analyzer_path]
    require(len(analyzer) == 1 and identity(analyzer[0]) == {
        "sha256": "a271e82042286276651db28a34928bd149c745ccb6ba7cacf18b51258b909669", "size_bytes": 543160},
        "policy3 permissive analyzer identity differs")
    commands = result["commands"]
    require(len(commands) == 12 and [row["module"] for row in commands] == [name for name, _ in POLICY3_BINARY_MODULES],
            "policy3 binary analysis coverage or order differs")
    empty = avb._identity(b"")
    profile = {"core_bytes": 0, "cpu_hard_seconds": 181, "cpu_soft_seconds": 180, "fsize_bytes": 64 << 20,
        "jail_cpu_soft_and_hard_seconds": 180, "log_cap_each_bytes": 16 << 20, "minimum_disk_bytes": 20 << 30,
        "minimum_mem_available_bytes": 12 << 30, "nofile": 1024, "outer_drain_margin_seconds": 30,
        "sampled_rss_ceiling_bytes": 8 << 30, "wall_seconds": 180}
    for index, (row, (module, ignore)) in enumerate(zip(commands, POLICY3_BINARY_MODULES)):
        matches = [entry for entry in records["policy_capture_mapping"]["files"]
                   if "normal_binary:" + module in entry["roles"]]
        require(len(matches) == 1 and row["upstream_compile_ignores_neverallows"] is ignore,
                "policy3 binary selection or diagnostic compile scope differs")
        bound = matches[0]
        for name, capture_name in (("live", "original_native"), ("retained", "retained_native")):
            require(identity(row[name]) == identity(bound[capture_name])
                    and row[name]["path"] == bound[capture_name]["path"]
                    and len([item for item in inputs if item == row[name]]) == 1,
                    "policy3 binary is not the current captured native output")
        native = row["native"]
        require(native["name"] == f"permissive-{index:02d}"
                and native["argv"] == [analyzer_path, row["live"]["path"], "permissive"]
                and native["passed"] is True and native["complete_native_exit"] is True
                and type(native["exit_code"]) is int and native["exit_code"] == 0
                and type(native["supervisor_exit_code"]) is int and native["supervisor_exit_code"] == 0
                and native["errors"] == [] and native["resource_profile"] == profile,
                "policy3 binary command was filtered, failed or used different limits")
        attempt = native["bounded_attempt"]
        require(attempt["operation"] == "bounded-native-command" and attempt["status"] == "completed"
                and type(attempt["returncode"]) is int and attempt["returncode"] == 0
                and type(attempt["exit_code"]) is int and attempt["exit_code"] == 0
                and attempt["exit_code_scope"] == "nsjail-supervisor" and attempt["native_exit_code_claimed"] is False
                and all(attempt[key] is True for key in ("all_pipes_eof", "diagnostics_persisted", "launch_attempted",
                    "launched", "no_live_descendants_observed_before_exit", "process_reaped", "process_started", "supervisor_log_separated"))
                and attempt["kill_reason"] is None and attempt["reasons"] == [],
                "policy3 native command did not finish with separate bounded streams")
        for stream in ("stdout", "stderr"):
            log = attempt["logs"][stream]
            require(identity(native[stream]) == identity(log) == empty
                    and native[stream]["path"] == log["path"]
                    and type(log["observed_bytes"]) is int and log["observed_bytes"] == 0
                    and log["truncated"] is False, "policy3 unfiltered permissive output is nonempty or truncated")
        supervisor = attempt["logs"]["supervisor"]
        require(identity(native["supervisor"]) == identity(supervisor)
                and native["supervisor"]["path"] == supervisor["path"]
                and supervisor["observed_bytes"] == supervisor["size_bytes"] <= profile["log_cap_each_bytes"]
                and supervisor["truncated"] is False, "policy3 supervisor diagnostics are incomplete or mixed with native output")
        for key in ("bounded_attempt_record", "mountinfo", "native_exit_observation", "resource_observation", "sandbox"):
            avb._identity_spec(identity(native[key]))
    review = records["policy_binary_review"]
    require(review["schema_version"] == 1 and review["operation"] == "review-actual-policy3-twelve-native-permissive-result-v1"
            and review["status"] == "verified-within-recorded-scope" and review["findings"] == []
            and identity(review["actual_result"]) == identity(control["records"]["policy_binary_validation"])
            and identity(review["canonical_guest_receipt"]) == identity(review["actual_result"])
            and review["canonical_guest_receipt_hash_only_rechecked"] is True
            and review["binary_results"] == [{**{key: row[key] for key in ("live", "module", "retained",
                    "upstream_compile_ignores_neverallows")}, "zero_permissive_domains": True} for row in commands],
            "policy3 independent binary review does not bind the twelve actual commands")
    source = review["source"]
    require(source["files"] == source["modes"] == 539 and source["projects"] == 13
            and source["full_source_proof_reconstructed_from_actual_policy3_after_state"] is True
            and source["source_and_configuration_after_guards_passed"] is True
            and source["fresh_metadata_six_file_check_performed_by_this_analysis"] is False
            and avb._identity(json_bytes(source["actual_commit"])) == contract["evolution_policy"]["source_commit"]
            and identity(source["actual_generated_configuration"]) == identity(
                records["policy_build"]["source_observations_after"]["strict_settings"]["file"])
            and source["full_configuration_observation_before_and_after"] == identity(before["configuration"])
            and source["source_proof_before_and_after"] == identity(before["source_proof"]),
            "policy3 native binary review is not bound to the actual source539 and complete configuration")
    observed = review["native"]
    require(observed["exact_module_order"] == [name for name, _ in POLICY3_BINARY_MODULES]
            and all(observed[key] == 12 for key in ("command_count", "empty_unfiltered_native_stderr",
                "empty_unfiltered_native_stdout", "native_exit_zero", "supervisor_exit_zero", "supervisor_streams_separate_and_retained"))
            and observed["all_complete_nontruncated_reaped_eof_without_kill_or_reason"] is True
            and observed["bound_native_caller_verified_actual_namespace_mount_capability_resource_records"] is True
            and observed["canonical_json_ledgers_reconstructed"] == 17 and observed["canonical_record_reconstructions"] == 60
            and observed["raw_sandbox_mountinfo_and_supervisor_bodies_replayed_on_host"] is False,
            "policy3 independent native command reconstruction or scope differs")
    require(review["scope"]["zero_permissive_domains_verified_for_exact_twelve_binaries"] is True
            and all(value is False for key, value in review["scope"].items()
                    if key != "zero_permissive_domains_verified_for_exact_twelve_binaries")
            and review["freeze_inputs"]["capture_complete"] is True
            and review["freeze_inputs"]["comparator_success_claimed_by_capture"] is False,
            "policy3 binary review promotes incomplete freeze, strict compatibility or runtime proof")
    return {"native_unfiltered_binary_count": 12, "native_unfiltered_permissive_domains": 0,
        "diagnostic_compatibility_binaries_count": 7, "diagnostic_compatibility_compiles_used_as_strict_assertion_proof": False,
        "native_permissive_analysis_reexecuted_by_preparation": False}


def qualify_policy3_freeze(records, control, contract):
    """Bind the public-name comparator and its actual ordinary-build action."""
    result = records["policy_freeze_review"]
    require(result["schema_version"] == 1 and type(result["schema_version"]) is int
            and result["operation"] == "review-actual-policy3-public-freeze"
            and result["status"] == "verified-policy3-platform-public-api-freeze"
            and result["public_freeze_comparison_verified"] is True
            and result["fresh_logged_comparator_action_verified"] is True
            and identity(result["actual_build_result"]) == identity(control["records"]["policy_build"])
            and identity(result["actual_native_readback"]) == identity(control["records"]["policy_binary_validation"])
            and result["native_comparator_rerun_performed"] is False
            and result["native_comparator_rerun_required"] is False
            and result["recursive_graph_replay_required_for_this_scope"] is False,
            "policy3 public freeze has no matching comparison and fresh native action")
    captured = result["freeze_inputs"]
    native = records["policy_binary_validation"]["freeze_inputs"]
    require(len(captured) == len(native) == 4
            and [{key: row[key] for key in ("role", "original", "retained", "comparison_execution_claimed_by_capture")}
                 for row in captured] == native,
            "policy3 freeze review does not select the actual four captured inputs")
    for key, row in zip(("tool", "current_cil", "api_cil", "stamp"), captured):
        require(result[key] == row["original"]
                and identity(row["host"]) == identity(row["original"]) == identity(row["retained"])
                and row["comparison_execution_claimed_by_capture"] is False,
                "policy3 freeze body identity or capture-only scope differs")
    mapping = records["policy_capture_mapping"]["files"]
    exporter = [row for row in mapping if "public_exporter:plat_pub_policy.cil" in row["roles"]]
    verbose = [row for row in mapping if "native-verbose-plain" in row["roles"]]
    require(len(exporter) == len(verbose) == 1
            and identity(result["current_cil"]) == identity(exporter[0]["original_native"]),
            "policy3 public freeze is not the selected current platform public exporter")
    source = result["source_and_recipe_witnesses"]
    require(avb._identity(json_bytes(source["actual_policy3_source_checkpoint"])) == contract["evolution_policy"]["source_commit"]
            and source["board_api"] == "202504" and source["build_variant"] == "user"
            and source["captured_source_project"] == {"head": "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27",
                "status": "M private/init_dev_config.te\n M private/su.te"},
            "policy3 public freeze source, selected API or product differs")
    logged = result["logged_native_comparison"]
    native_out = control["policy_files"]["combined"]["native_path"].removesuffix(COMBINED_SUFFIX)
    def alias(row):
        require(row["path"].startswith(native_out + "/"), "policy3 freeze path is outside the selected native OUT")
        return "out-" + Path(native_out).name + row["path"].removeprefix(native_out)
    require(logged["tokens"] == [alias(result["tool"]), "-c", alias(result["current_cil"]),
                "-p", alias(result["api_cil"]), "&&", "touch", alias(result["stamp"])]
            and logged["line"] == 654 and logged["main_ninja_action"] == 371
            and identity(logged["verbose"]) == identity(verbose[0]["host"])
            and logged["actual_native_build_exit_code"] == logged["actual_wrapper_exit_code"] == 0
            and logged["se_freeze_test_was_an_ordinary_goal"] is True
            and logged["comparator_precedes_success_conditional_stamp_touch"] is True
            and logged["standalone_stamp_or_timestamp_used_as_pass"] is False
            and logged["per_process_historical_tool_hash_at_action_launch_independently_sampled"] is False,
            "policy3 freeze action is missing, stale or inferred from its stamp")
    packaged = result["packaged_tool_source_binding"]
    require(packaged["complete_tool_hash_bound"] is True
            and packaged["two_complete_pyc_members_reproduced_from_exact_captured_sources"] is True
            and packaged["entrypoint"] == "sepolicy_freeze_test"
            and packaged["entrypoint_bootstrap"]["single_expected_entrypoint"] is True
            and packaged["native_android_compiler_identity_assumed"] is False
            and packaged["source_hash_headers_alone_used_as_proof"] is False
            and packaged["stdlib_and_native_launcher_audit_claimed"] is False
            and [row["packaged_member"] for row in packaged["comparisons"]] == ["sepolicy_freeze_test.pyc", "mini_parser.pyc"],
            "policy3 freeze packaged checker/parser source binding differs")
    for row in packaged["comparisons"]:
        require(row["whole_bytes_equal"] is True and row["packaged_sha256"] == row["regenerated_sha256"]
                and row["packaged_size_bytes"] == row["regenerated_size_bytes"]
                and row["pyc_flags"] == 3 and row["pyc_magic"] == "f30d0d0a",
                "policy3 freeze source reproduction is incomplete")
        avb._digest(row["packaged_sha256"])
    comparison = result["public_comparison"]
    require(comparison["captured_upstream_do_main_returned_normally"] is True
            and comparison["current_cil_equals_already_bound_current_platform_public_exporter"] is True
            and comparison["current_declared_type_count"] == comparison["api_declared_type_count"] == 1419
            and comparison["current_compared_attribute_count"] == comparison["api_compared_attribute_count"] == 353
            and comparison["current_excluded_generated_attribute_count"] == comparison["api_excluded_generated_attribute_count"] == 234
            and all(comparison[name] == [] for name in ("added_attributes", "added_types", "removed_attributes", "removed_types"))
            and comparison["host_stdout_bytes"] == comparison["host_stderr_bytes"] == 0
            and comparison["full_cil_byte_equality"] is False,
            "policy3 actual public type/attribute comparison differs")
    require(result["scope"]["platform_public_freeze_for_actual_policy3_verified"] is True
            and all(value is False for key, value in result["scope"].items()
                    if key != "platform_public_freeze_for_actual_policy3_verified")
            and result["validation"]["actual_source_comparator_replay_passed"] is True
            and result["validation"]["four_bodies_and_sources_rehashed_after"] is True
            and result["validation"]["complete_pyc_member_matches"] == 2
            and result["validation"]["failures"] == result["validation"]["skips"] == 0,
            "policy3 freeze review overstates its scope or omits a final input check")
    return {"public_freeze_comparison_verified": True, "fresh_logged_comparator_action_verified": True,
        "public_type_and_attribute_names_only": True, "freeze_native_comparator_reexecuted_by_preparation": False,
        "full_policy_permission_equivalence_claimed_by_freeze": False}


def qualify_policy3_sidecars(records, control, contract, held):
    """Select actual ordinary-build outputs, independently recomputing their bytes."""
    capture, result = records["policy_sidecar_capture"], records["policy_sidecar_validation"]
    require(result["schema_version"] == 1 and type(result["schema_version"]) is int
            and result["operation"] == "qualify-existing-policy3-sidecar-producers-readonly-v1"
            and result["status"] == "verified" and result["sidecar_success_verified"] is True
            and identity(result["evidence"]["read_only_capture"]) == identity(control["records"]["policy_sidecar_capture"])
            and identity(result["evidence"]["policy3_result"]) == identity(control["records"]["policy_build"])
            and result["actual_outputs_checked"] == result["actual_ordered_inputs_checked"] == 6
            and result["actual_sbox_manifests_checked"] == result["exact_dependency_chains_checked"] == 3
            and result["read_only_ninja_queries"] == 2 and result["scope"]["normal_android_enforcing_required"] is True
            and all(value is False for key, value in result["scope"].items() if key != "normal_android_enforcing_required"),
            "policy3 installed sidecar producer validation is incomplete or has unsupported scope")
    require(capture["schema_version"] == 1 and capture["operation"] == "capture-policy3-sidecar-producer-evidence-readonly-v1"
            and capture["status"] == "captured" and capture["read_only_capture_verified"] is True
            and capture["guard_errors"] == [] and "error" not in capture
            and all(capture[key] is False for key in ("source_or_output_written", "native_build_or_checker_executed",
                "new_native_genrules_executed", "producer_actions_admitted", "sidecar_success_verified", "complete_rom_ready", "phone_accessed"))
            and all(capture[key + "_before"] == capture[key + "_after"] for key in ("source", "native_result", "ninja", "sandbox"))
            and capture["sandbox_before"]["checks_passed"] is True and capture["sandbox_before"]["all_work_readonly"] is True
            and identity(capture["native_result_before"]) == identity(control["records"]["policy_build"]),
            "policy3 sidecar capture is incomplete, changed inputs or claims producer success by itself")
    root_source, source = result["source_context"], capture["source_before"]
    build_source = records["policy_build"]["source_observations_after"]
    require(root_source["operation"] == "verify-current539-in-original-root-context"
            and root_source["verified"] is True and root_source["source_files_checked"] == 539
            and root_source["source_projects_checked"] == 13
            and type(root_source["uid"]) is int and root_source["uid"] == 0
            and type(root_source["gid"]) is int and root_source["gid"] == 0
            and root_source["source_proof"] == avb._identity(json_bytes(build_source["source_history"]))
            and root_source["configuration"] == avb._identity(json_bytes(build_source["configuration"]))
            and root_source["policy3_result"] == identity(control["records"]["policy_build"])
            and root_source["private_view_owner_mode_guards_unchanged"] is True
            and root_source["source_or_output_modified"] is False,
            "policy3 complete source proof is not bound to its original root context")
    require(source["source_files_checked"] == 0 and source["source_projects_checked"] == 0
            and source["root_current539_guard_required"] is True
            and avb._identity(json_bytes(source["actual_commit"])) == contract["evolution_policy"]["source_commit"]
            and source["historical_source_history_reverified"] is False and source["source_or_output_modified"] is False
            and identity(source["configuration"]) == identity(records["policy_build"]["source_observations_after"]["strict_settings"]["file"])
            and source["strict_settings"] == records["policy_build"]["source_observations_after"]["strict_settings"]
            and result["recipe_source"]["path"] == "/work/evolution/system/sepolicy/Android.bp"
            and identity(result["recipe_source"]) == contract["evolution_policy"]["sidecar_source"]
            and result["recipe_project_head"] == "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27",
            "policy3 native sidecar source/configuration/recipe differs")
    observations = capture["observations_before"]
    require(len(observations) == 19 and observations == capture["observations_after"]
            and [row["selection_index"] for row in observations] == list(range(19))
            and len({row["observation"]["path"] for row in observations}) == 19,
            "policy3 sidecar capture does not cover the nineteen unchanged observations")
    modules = result["modules"]
    names = ("plat", "system_ext", "product")
    require(len(modules) == 3 and [row["module"] for row in modules] == [name + "_sepolicy_and_mapping.sha256" for name in names],
            "policy3 ordinary sidecar module coverage or order differs")
    files, selected, installed = control["policy_files"], {}, []
    native_out = files["combined"]["native_path"].removesuffix(COMBINED_SUFFIX)
    alias = "out-" + Path(native_out).name
    commands, intermediate_commands, success_selectors = [], [], []
    for index, (name, row) in enumerate(zip(names, modules)):
        module, partition = name + "_sepolicy_and_mapping.sha256", ("system" if name == "plat" else name)
        roles = RUNTIME_INPUTS[index * 2:index * 2 + 2]
        inputs = [{"path": files[role]["native_path"], **identity(files[role])} for role in roles]
        require(row["partition"] == partition and row["ordered_inputs"] == inputs,
                "policy3 sidecar producer uses another ordered compiler pair")
        value = hashlib.sha256(held[roles[0]] + held[roles[1]]).hexdigest().encode() + b"\n"
        directory = "/soong/.intermediates/system/sepolicy/" + module + "_gen/android_common/"
        generated = alias + directory + "gen/" + module
        intermediate = alias + "/soong/.intermediates/system/sepolicy/" + module + "/android_arm64_armv8-a/" + module
        installed_selector = alias + "/target/product/nezha/" + partition + "/etc/selinux/" + module
        require(row["dependency_chain"] == {"module": module, "generated_selector": generated,
            "prebuilt_intermediate_selector": intermediate, "installed_selector": installed_selector,
            "installed_copy_reads_prebuilt_intermediate": True}, "policy3 genrule/prebuilt/installed dependency chain differs")
        paths = {"generated": native_out + directory + "gen/" + module,
                 "installed": native_out + installed_selector.removeprefix(alias),
                 "sbox_manifest": native_out + directory + "genrule.sbox.textproto"}
        for offset, kind in enumerate(("generated", "installed", "sbox_manifest")):
            body = row[kind]
            captured = observations[index * 5 + offset]
            observed = captured["observation"]
            require(captured["role"] == kind and captured["module"] == module
                    and body["path"] == paths[kind] == observed["path"]
                    and identity(body) == identity(observed) and body["stat"] == observed["stat"]
                    and observed["present"] is True
                    and body["body_origin"] == "actual-readonly-native-file-capture"
                    and body["capture_body_selector"] == f"observations_before[{index * 5 + offset}].body_base64"
                    and body["body_base64"] == captured["body_base64"],
                    "policy3 sidecar body is not the selected actual capture")
            raw = base64.b64decode(body["body_base64"], validate=True)
            require(avb._identity(raw) == identity(body) and stat.S_ISREG(body["stat"]["st_mode"])
                    and body["stat"]["st_nlink"] == 1 and body["stat"]["st_size"] == len(raw),
                    "policy3 captured sidecar bytes or inode differ")
            if kind != "sbox_manifest":
                require(raw == value and len(raw) == 65 and stat.S_IMODE(body["stat"]["st_mode"]) == 0o644,
                        "actual policy3 sidecar is not SHA256(CIL || mapping) plus LF")
        for offset, expected in enumerate(inputs):
            observed = observations[index * 5 + 3 + offset]
            require(observed["role"] == "ordered_input_" + str(offset) and observed["module"] == module
                    and observed["body_base64"] is None and observed["observation"]["present"] is True
                    and {key: observed["observation"][key] for key in ("path", "sha256", "size_bytes")} == expected,
                    "policy3 sidecar capture is not joined to the actual compiler input")
        recipe = row["sbox_recipe"]
        operand_paths = ["__SBOX_SANDBOX_DIR__/out" + item["path"].removeprefix(native_out) for item in inputs]
        expected_command = "cat " + " ".join(operand_paths) + " | sha256sum | cut -d' ' -f1 > __SBOX_SANDBOX_DIR__/out/" + module
        require(recipe["module"] == module and recipe["ordered_inputs"] == inputs
                and recipe["manifest"] == identity(row["sbox_manifest"]) and recipe["command"] == expected_command
                and recipe["opaque_input_hash_not_used_as_content_digest"] is True
                and recipe["native_command_executed_by_verifier"] is False,
                "policy3 actual sbox recipe or ordered operands differ")
        avb._digest(recipe["opaque_soong_input_hash"])
        selected[name] = files[name + "_sha256"]
        require(selected[name]["native_path"] == paths["installed"]
                and identity(selected[name]) == identity(row["installed"])
                and avb._small(selected[name]["path"], 65, selected[name]) == value,
                "policy3 replacement sidecar is not the captured native installed output")
        installed.append({"name": name, "native_path": paths["installed"], **identity(selected[name])})
        commands.append(alias + "/host/linux-x86/bin/sbox --sandbox-path " + alias + "/soong/.temp --output-dir "
            + generated.rsplit("/", 1)[0] + " --manifest " + alias + directory + "genrule.sbox.textproto")
        intermediate_commands.append("rm -f " + intermediate + " && cp -d  " + generated + " " + intermediate)
        success_selectors.append((generated, installed_selector))
    commands += ['/bin/bash -c "rm -f ' + row[1] + " && cp -f -d " + modules[index]["dependency_chain"]["prebuilt_intermediate_selector"]
                 + " " + row[1] + '"' for index, row in enumerate(success_selectors)]
    production = result["production"]
    require(production["policy3_result"] == identity(control["records"]["policy_build"])
            and production["prior_native_command_count"] == 6 and production["prior_genrule_commands"] == 3
            and production["prior_installed_copy_commands"] == 3 and production["supporting_intermediate_copy_count"] == 3
            and production["fresh_native_actions"] == 0 and production["command_hash_prediction_claimed"] is False
            and [row["command"] for row in production["prior_native_commands"]] == commands == capture["ordered_leaf_commands"]
            and [row["command"] for row in production["supporting_prior_intermediate_copy_commands"]] == intermediate_commands,
            "policy3 ordinary sidecar producer/copy evidence is incomplete or claims new execution")
    actions = production["prior_native_commands"] + production["supporting_prior_intermediate_copy_commands"]
    require(len({row["action"] for row in actions}) == 9
            and all(type(row["line"]) is int and row["line"] > 0 and row["total"] == 556 for row in actions)
            and all(production["prior_native_commands"][index]["action"]
                < production["supporting_prior_intermediate_copy_commands"][index]["action"]
                < production["prior_native_commands"][index + 3]["action"] for index in range(3)),
            "policy3 native sidecar actions do not prove the complete ordered copy chain")
    require([row["selector"] for row in production["ninja_success_rows"]]
            == [row[0] for row in success_selectors] + [row[1] for row in success_selectors],
            "policy3 current producer success row coverage differs")
    return selected, {"source_kind": "captured-ordinary-android-installed-sidecars",
        "native_installed_outputs": installed, "ordered_input_count": 6, "prior_native_genrule_commands": 3,
        "prior_native_installed_copy_commands": 3, "supporting_prior_intermediate_copy_commands": 3,
        "fresh_native_actions": 0, "native_captured_sidecars_read_and_recomputed": True,
        "native_genrules_reexecuted_by_preparation": False, "full_recursive_producer_provenance_verified": False}


def qualify_policy3_policy(records, control, contract):
    held, basis = qualify_policy3_basis(records, control, contract)
    binaries = qualify_policy3_binaries(records, control, contract)
    freeze = qualify_policy3_freeze(records, control, contract)
    sidecars, sidecar_proof = qualify_policy3_sidecars(records, control, contract, held)
    files = control["policy_files"]
    replacements = {"vendor": {"/etc/selinux/vendor_sepolicy.cil": files[RUNTIME_INPUTS[7]]},
                    "odm": {"/etc/selinux/precompiled_sepolicy": files["combined"]}}
    for name, row in sidecars.items():
        replacements["odm"]["/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"] = row
    return replacements, {"current_factory_combined_binary_bound": True, "sidecars_recomputed_and_matched": True,
        "assertion_statements_retained": 6366, "assertion_statements_added": 33, "assertion_statements_total": 6399,
        "normal_android_permissive_domains": 0, "full_treble_apk_labeling_proven": False,
        "native_policy_reexecuted": False, "native_policy_snapshot": contract["evolution_policy"]["build_phase"],
        "current_active_source_compatibility_proven": False, "sidecars_observed_at_native_install_paths": True,
        "provider_profile_selected": True, "provider_runtime_support_proven": False,
        "source_basis": basis, "binary_checks": binaries, "public_freeze": freeze,
        "sidecar_native_production": sidecar_proof}


def qualify_policy(records, control, contract):
    if contract["contract_id"] == POLICY3_CONTRACT_ID:
        return qualify_policy3_policy(records, control, contract)
    if contract["contract_id"] == PROVIDER_CONTRACT_ID:
        return qualify_provider_policy(records, control, contract)
    build, analysis = records["policy_build"], records["policy_analysis"]
    export4 = contract["contract_id"] == EXPORT4_CONTRACT_ID
    operation = "verify-native-oem-properties-v12f-export4" if export4 else "verify-native-oem-properties-v12f"
    _build(build)
    require(type(analysis["schema_version"]) is int and analysis["schema_version"] == 1
            and analysis["operation"] == operation and analysis["status"] == "verified"
            and analysis["build_phase"] == build["phase"] and analysis["provider_profile_selected"] is False
            and analysis["strict_compiler_flags_verified"] is True
            and analysis["compiler_temporary_to_analyzed_final_copy_verified"] is True
            and analysis["all_guarded_inputs_unchanged"] is True, "current factory policy analysis is incomplete")
    if export4:
        require(analysis["build_phase"] == "policy-v12f-export-1"
                and analysis["export_phase"] == "v12f-runtime-policy-exports-v1"
                and analysis["installed_fixup_manifest_sha256"] == "8907f7705cd1a767a037531c63ee9b4c4454def1ec8bfbd623862f4df879ce14"
                and analysis["installed_integration_manifest_sha256"] == "084e740e4888bdded20c2ca3b44ce3400652c5ac8ab242a8c17dc99d56a04820"
                and all(analysis[key] is False for key in ("full_treble_apk_labeling_pass", "policy_compiler_replayed",
                    "source_or_android_output_modified", "images_changed", "phone_accessed", "complete_rom_or_runtime_support_proven")),
                "export4 snapshot, installation linkage or evidence boundary differs")
        source = analysis["source_fixup_provenance"]
        require(source["operation"] == "verify-v12f-fixed-addendum-chain" and source["status"] == "verified"
                and source["normal_android_enforcing_required"] is True
                and source["unchanged_policy_component_retained"] is True
                and source["unchanged_vendor_component_retained"] is True
                and source["native_build_binding"]["phase"] == analysis["build_phase"]
                and source["native_build_binding"]["packaged_commit_equal_to_build_record"] is True
                and source["source_capture"]["all_effective_source_guards_bound"] is True,
                "export4 captured source/fixup provenance is incomplete")
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
        if export4:
            row = {**avb._identity(expected), "derived_bytes": expected, "sidecar_name": name,
                   "source_kind": "derived-from-sealed-native-cil-and-mapping",
                   "ordered_input_roles": [RUNTIME_INPUTS[index], RUNTIME_INPUTS[index + 1]]}
        else:
            row = files[name + "_sha256"]
            partition = "system" if name == "plat" else name
            suffix = "/target/product/nezha/" + partition + "/etc/selinux/" + name + "_sepolicy_and_mapping.sha256"
            require(row["native_path"] == native_out + suffix and held[name + "_sha256"] == expected,
                    "framework sidecar does not equal SHA256(CIL || mapping/202504.cil) plus LF")
        replacements["odm"]["/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"] = row
    proof = {"current_factory_combined_binary_bound": True, "sidecars_recomputed_and_matched": True,
        "assertion_statements_retained": 6366, "normal_android_permissive_domains": 0,
        "full_treble_apk_labeling_proven": False, "native_policy_reexecuted": False}
    if export4:
        proof["sidecar_derivation"] = qualify_sidecar_derivation(records, control, held, contract)
        proof.update(native_policy_snapshot="policy-v12f-export-1", current_active_source_compatibility_proven=False,
                     sidecars_observed_at_native_install_paths=False, provider_profile_selected=False)
    return replacements, proof


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


def prepare(input_path, expected_sha, *, output_dir, selected_profile=HISTORICAL_PROFILE):
    contract, contract_sha, profile, helper = load_contract(selected_profile)
    workflow = avb._identity(avb._small(ROOT / "scripts/policy_image_inputs.py", TEXT))
    require(PROFILE_CONTRACT_SHA256[selected_profile] is not None
            and all(row is not None for row in contract["native_records"].values()),
            "actual native evidence pins are not ready; preparation remains blocked")
    control, original_control = load_control(input_path, expected_sha, contract, contract_sha)
    records = read_records(control)
    erofs_proof = qualify_erofs(records, contract, control)
    selected, policy_proof = qualify_policy(records, control, contract)
    out = avb.envelope._absolute_path(output_dir)
    allowed = ROOT / contract["output_root"]
    require(out != allowed and out.is_relative_to(allowed), "output must be a fresh ignored policy-images/nezha child")
    require(all(not out.is_relative_to(row["staging_root"]) for row in control["partitions"].values()),
            "output must be outside every read-only regular-byte staging tree")
    derived = []
    for rows in selected.values():
        for row in rows.values():
            if "derived_bytes" in row:
                require(derived_sidecars(contract) and "native_path" not in row, "derived sidecar cannot claim a native installation path")
                row["path"] = out / "derived-sidecars" / (row["sidecar_name"] + "_sepolicy_and_mapping.sha256")
                derived.append(row)
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
    with io._private_creation():
        io._fresh_output(out)
        require(shutil.disk_usage(out).free >= 2 * sum(sizes.values()) + RESERVE, "insufficient space for two complete TAR sets")
        if derived:
            require(len(derived) == 3, "three derived sidecars required")
            io._mkdir(out / "derived-sidecars")
            for row in derived:
                with avb.envelope._parent_directory(row["path"]) as parent:
                    fd = os.open(row["path"].name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(row["derived_bytes"])
                    stream.flush()
                    os.fsync(stream.fileno())
                avb._rehash(row["path"], row)
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
        for row in derived:
            avb._rehash(row["path"], row)
        for rows in control.get("noop_manifests", {}).values():
            for row in rows:
                avb._rehash(row["path"], row)
        read_records(control)
        require(read_json(input_path)[1] == original_control and load_contract(selected_profile)[1] == contract_sha
                and avb._identity(avb._small(ROOT / "scripts/policy_image_inputs.py", TEXT)) == workflow,
                "input selection or source contract changed")
        report = {"schema_version": 1, "operation": "prepare-nezha-five-file-policy-image-inputs",
            "status": "complete-tar-inputs-prepared", "artifact_set_id": control["artifact_set_id"],
            "profile": selected_profile, "contract_id": contract["contract_id"],
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
            "derived_sidecars": [{"path": str(row["path"].relative_to(out)), **identity(row),
                "source_kind": row["source_kind"], "ordered_input_roles": row["ordered_input_roles"],
                "ordered_inputs": [{"runtime_path": role, "native_path": control["policy_files"][role]["native_path"],
                                    **identity(control["policy_files"][role])} for role in row["ordered_input_roles"]],
                "native_installed_output_claimed": False} for row in derived],
            "remaining_gates": [
                ("Apply the qualified finite limits in fresh isolated work and build both policy-substituted images twice."
                 if complete_noops_required(contract) else
                 "Qualify the recorded finite production limits, scratch filesystem and bounded log executor, then run two native builds."),
                "Complete native metadata exports and exact-five-file semantic comparison for both new images.",
                "Regenerate hashtrees/FEC/AVB footers; verify final identities, partition fit and signed parent chain."],
            **BOUNDARIES}
        io._save(out / "preparation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    planned = sub.add_parser("plan")
    selected = sub.add_parser("prepare")
    selected.add_argument("--input", required=True, type=Path)
    selected.add_argument("--expected-sha256", required=True)
    selected.add_argument("--output-dir", required=True, type=Path)
    for command in (planned, selected):
        command.add_argument("--profile", choices=tuple(PROFILE_CONTRACT_IDS), default=HISTORICAL_PROFILE)
    args = parser.parse_args(argv)
    try:
        result = plan(args.profile) if args.operation == "plan" else prepare(args.input, args.expected_sha256,
            output_dir=args.output_dir, selected_profile=args.profile)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2 if result["status"] == "blocked" else 0
    except (PolicyImageError, avb.AvbImageSetError, metadata.MetadataError, io.TwrpWorkingError,
            OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "failed", "error_class": type(exc).__name__,
                          "error": "policy-image preparation prerequisites failed", **BOUNDARIES}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
