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
CONTRACT = ROOT / "config/nezha-policy-images.json"
CONTRACT_ID = "nezha-five-file-policy-image-inputs-v1"
HISTORICAL_PROFILE = "historical-v12"
EXPORT4_PROFILE = "v12-export4"
EXPORT4_CONTRACT_ID = "nezha-five-file-policy-image-inputs-v12-export4-v1"
PROFILE_CONTRACT_IDS = {HISTORICAL_PROFILE: CONTRACT_ID, EXPORT4_PROFILE: EXPORT4_CONTRACT_ID}
PROFILE_CONTRACT_SHA256 = {
    HISTORICAL_PROFILE: "0a549e0374f17fcd24e25dba668bbe745750968bc1336c7c142583fac1816cc4",
    EXPORT4_PROFILE: "5c7e020cbf2101bc6ed5af412f1e667d41e75e3259547c0700090d2d1f10ffb4",
}
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
EXPORT4_RECORD_ROLES = RECORD_ROLES | {"erofs_fsize_probe", "erofs_fsize_orchestration",
    "sidecar_source_capture", "sidecar_native_validation", "sidecar_orchestration", "sidecar_sandbox"} | {
    "erofs_" + partition + "_noop" + suffix
    for partition in PARTITIONS for suffix in ("", "_orchestration", "_sandbox", "_capture")}
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


def record_roles(contract):
    require(contract["contract_id"] in PROFILE_CONTRACT_IDS.values(), "unknown policy snapshot profile")
    return EXPORT4_RECORD_ROLES if contract["contract_id"] == EXPORT4_CONTRACT_ID else RECORD_ROLES


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
    if selected_profile == EXPORT4_PROFILE:
        fields.add("sidecar_derivation")
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
    if selected_profile == EXPORT4_PROFILE:
        sidecar = c["sidecar_derivation"]
        avb._keys(sidecar, ("source_revision", "source", "recipe", "contract", "driver", "launcher", "collector"),
                  "source-bound sidecar derivation")
        require(sidecar["source_revision"] == "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27"
                and sidecar["source"] == {"sha256": "17171fec6b4e253db277c351f817670077c6fd235ca07ac33be509c8faa4d2f8",
                    "size_bytes": 43467} and sidecar["recipe"] == "cat $(in) | sha256sum | cut -d' ' -f1 > $(out)",
                "source-bound sidecar algorithm changed")
        for name in ("source", "contract", "driver", "launcher", "collector"):
            avb._identity_spec(sidecar[name])
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
    export4 = contract["contract_id"] == EXPORT4_CONTRACT_ID
    fields = {"schema_version", "contract_id", "contract_sha256", "artifact_set_id", "records", "partitions", "policy_files"}
    if export4:
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
    if export4:
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
    result = {"tools": lock["tools"], "reviewed_failed_checks_retained": {
        "synthetic": synthetic_failures, "writer_upstream_xattrs": writer_failures},
        "nonzero_nanoseconds_admitted": False, "empty_xattr_values_admitted": False,
        "native_reexecuted_by_this_command": False, "production_writer_admitted": False}
    if contract["contract_id"] == EXPORT4_CONTRACT_ID:
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
    native, outer, sandbox, source = (records[role] for role in
        ("sidecar_native_validation", "sidecar_orchestration", "sidecar_sandbox", "sidecar_source_capture"))
    pins = contract["sidecar_derivation"]
    require(source["schema_version"] == 1 and source["guest_writes"] is False and source["phone_accessed"] is False
            and source["files"] == [{"path": "system/sepolicy/Android.bp", **pins["source"]}]
            and source["total_bytes"] == pins["source"]["size_bytes"]
            and source["projects"] == {"system/sepolicy": {"head": pins["source_revision"],
                "status": "M private/init_dev_config.te\n M private/su.te"}}, "sidecar source capture differs")
    require(type(native["schema_version"]) is int and native["schema_version"] == 1
            and native["operation"] == "derive-export4-policy-sidecars-native-v1" and native["passed"] is True
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
            and native["baseline"]["operation"] == "verify-native-oem-properties-v12f-export4",
            "native sidecar source, tool or export4 binding differs")
    require(outer["operation"] == "root-policy-sidecar-native-orchestration-v1" and outer["passed"] is True
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
    require(type(base) is str and re.fullmatch(
            r"/work/validation/nezha-oem-policy-integration-20260829/policy-sidecar-native-v[1-9][0-9]*", base),
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
                and output["provenance"] == "derived-from-sealed-export4-inputs"
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
        "derivation_kind": "sealed-v12-export4-CIL-and-mapping", "native_reexecuted_by_this_command": False}


def qualify_policy(records, control, contract):
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
                require(selected_profile == EXPORT4_PROFILE and "native_path" not in row, "derived sidecar cannot claim a native installation path")
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
                 if selected_profile == EXPORT4_PROFILE else
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
