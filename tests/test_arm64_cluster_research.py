"""Offline integrity checks for the ARM64 cluster research evidence.

These tests validate the record, not an Android build or a remote worker.
"""

import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "arm64-cluster"


class Arm64ClusterResearchTests(unittest.TestCase):
    def setUp(self):
        self.pins = json.loads((RESEARCH / "source-pins.json").read_text())

    def test_source_pins_have_immutable_provenance(self):
        self.assertEqual(self.pins["schema_version"], 1)
        seen = set()
        for source in self.pins["sources"]:
            key = (source["repository"], source["requested_ref"])
            with self.subTest(key=key):
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertIn(source["status"], {"resolved", "unavailable_ref"})
                if source["status"] == "resolved":
                    self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
                    self.assertRegex(source["metadata_response_sha256"], r"^[0-9a-f]{64}$")
                    self.assertTrue(source["immutable_url"].endswith(source["commit"]))
                    self.assertTrue(source["author_time"])
                    self.assertTrue(source["committer_time"])
                    self.assertIsInstance(source["tree_entries"], list)
                else:
                    self.assertIn("error", source)
                    self.assertNotIn("commit", source)

    def test_inventory_does_not_claim_a_full_build(self):
        self.assertIs(self.pins["full_platform_build_verified"], False)
        self.assertIn("not proof", self.pins["scope"])

    def test_public_arm64_go_and_clang_roots_are_recorded_as_empty(self):
        by_key = {(s["repository"], s["requested_ref"]): s for s in self.pins["sources"]}
        for repository in ("platform/prebuilts/go/linux-arm64",
                           "platform/prebuilts/clang/host/linux-arm64"):
            with self.subTest(repository=repository):
                self.assertEqual(by_key[repository, "main"]["tree_entries"], [])
                self.assertEqual(by_key[repository, "android-16.0.0_r4"]["status"],
                                 "unavailable_ref")

    def test_release_and_main_are_separate_baselines(self):
        refs = {s["requested_ref"] for s in self.pins["sources"]}
        self.assertTrue({"main", "android-16.0.0_r1", "android-16.0.0_r4",
                         "android-17.0.0_r1"}.issubset(refs))

    def test_modern_clang_mirror_is_not_conflated_with_empty_main(self):
        matches = [s for s in self.pins["sources"]
                   if s["repository"] == "platform/prebuilts/clang/host/linux-arm64"
                   and "mirror-goog" in s["requested_ref"]]
        self.assertTrue(matches)
        for source in matches:
            self.assertIn("clang-r584948b", source["tree_entries"])
            self.assertNotIn("clang-r563880c", source["tree_entries"])

    def test_probe_limits_keep_bootstrap_separate_from_platform_and_rbe(self):
        record = json.loads((RESEARCH / "probe-results.json").read_text())
        self.assertEqual(record["schema_version"], 1)
        for key, value in record["boundaries"].items():
            with self.subTest(key=key):
                self.assertIs(value, key == "patches_only_in_isolated_probe_copy")
        self.assertEqual(record["environment"]["native_machine"], "aarch64")
        self.assertEqual(record["environment"]["filesystem"], "ext4")
        self.assertTrue(record["environment"]["case_sensitive"])
        for dependency in record["original_dependency_state"].values():
            self.assertEqual(dependency["status"], [])

    def test_native_bootstrap_outputs_and_make_mismatch_are_explicit(self):
        record = json.loads((RESEARCH / "probe-results.json").read_text())
        probes = {p["id"]: p for p in record["probes"]}
        self.assertEqual(probes["P03"]["exit_code"], 0)
        self.assertEqual(len(probes["P03"]["outputs"]), 5)
        for output in probes["P03"]["outputs"]:
            self.assertEqual(output["elf_machine"], 183)
            self.assertRegex(output["sha256"], r"^[a-f0-9]{64}$")
        self.assertNotEqual(probes["P04"]["exit_code"], 0)
        self.assertIn("unknown variable: HOST_ARCH", probes["P04"]["failure"])
        self.assertEqual(probes["P05"]["result"]["HOST_PREBUILT_TAG"], "linux-x86")
        self.assertEqual(probes["P06"]["result"]["HOST_PREBUILT_TAG"], "linux-arm64")
        self.assertEqual(len(probes["P06"]["missing_selected_tools"]), 3)

    def test_hybrid_probe_records_both_execution_architectures(self):
        record = json.loads((RESEARCH / "probe-results.json").read_text())
        probe = next(p for p in record["probes"] if p["id"] == "P07")
        by_name = {Path(p["path"]).name: p for p in probe["files"]}
        self.assertEqual(probe["exit_code"], 0)
        for name in ("ninja", "android.o"):
            self.assertEqual(by_name[name]["elf_machine"], 183)
        for name in ("clang", "ld.lld", "java", "exit-x86"):
            self.assertEqual(by_name[name]["elf_machine"], 62)

    def test_probe_patch_is_narrow_and_not_a_security_bypass(self):
        patch = (RESEARCH / "probe-host-detection.patch").read_text()
        self.assertEqual(patch.count("diff --git"), 1)
        self.assertIn("a/core/envsetup.mk b/core/envsetup.mk", patch)
        for forbidden in ("SELINUX", "ALLOW_MISSING", "DISABLE_SANDBOX", "BUILD_BROKEN"):
            self.assertNotIn(forbidden, patch)

    def test_commit_history_has_full_hashes_and_dates(self):
        record = json.loads((RESEARCH / "upstream-commits.json").read_text())
        seen = set()
        for commit in record["commits"]:
            key = (commit["repository"], commit["commit"])
            with self.subTest(key=key):
                self.assertNotIn("error", commit)
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertRegex(commit["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(commit["author_time"])
                self.assertTrue(commit["committer_time"])
                self.assertTrue(commit["url"].endswith(commit["commit"]))

    def test_report_has_all_deliverables_and_resolved_reference_links(self):
        report = (ROOT / "docs/android16-arm64-cluster-report.md").read_text()
        sections = [int(n) for n in re.findall(r"^## (\d+)\.", report, re.M)]
        self.assertEqual(sections, list(range(1, 15)))
        definitions = re.findall(r"^\[([^\]]+)\]: (https://\S+)\s*$", report, re.M)
        names = [name for name, _ in definitions]
        self.assertEqual(len(names), len(set(names)))
        used = set(re.findall(r"\[[^\]\n]+\]\[([^\]\n]+)\]", report))
        self.assertFalse(used - set(names), f"Missing references: {used - set(names)}")
        for verdict in ("Confirmed working", "Should work", "Experimental",
                        "Major engineering required", "Not viable"):
            self.assertIn(verdict, report)

    def test_research_documents_link_to_existing_local_artifacts(self):
        for name in ("android16-arm64-cluster-report.md",
                     "android16-arm64-cluster-experiments.md"):
            document = ROOT / "docs" / name
            links = re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", document.read_text())
            for target in links:
                if target.startswith(("https://", "http://", "#")):
                    continue
                path = (document.parent / unquote(target.split("#")[0])).resolve()
                with self.subTest(document=name, target=target):
                    self.assertTrue(path.is_relative_to(ROOT))
                    self.assertTrue(path.is_file())

    def test_claims_reference_sources_probes_and_record_unvalidated_gaps(self):
        ledger = json.loads((RESEARCH / "claims-and-sources.json").read_text())
        probes = json.loads((RESEARCH / "probe-results.json").read_text())
        self.assertEqual(ledger["schema_version"], 1)
        sources = {source["id"] for source in ledger["sources"]}
        self.assertEqual(len(sources), len(ledger["sources"]))
        probe_ids = {probe["id"] for probe in probes["probes"]}
        for claim in ledger["claims"]:
            with self.subTest(claim=claim["id"]):
                self.assertIn(claim["evidence_class"],
                              {"observed", "pinned_source", "engineering_inference"})
                self.assertTrue(claim["limitation"])
                self.assertTrue(set(claim["source_ids"]).issubset(sources))
                self.assertTrue(set(claim["probe_ids"]).issubset(probe_ids))
                if claim["evidence_class"] == "observed":
                    self.assertTrue(claim["probe_ids"])
        self.assertGreaterEqual(len(ledger["open_gaps"]), 8)
        for gap in ledger["open_gaps"]:
            self.assertEqual(gap["status"], "not_validated")
            self.assertTrue(gap["runbook_experiments"])
        for name in ledger["evidence_files"] + [ledger["report"], ledger["runbook"]]:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_runbook_separates_proposed_experiments_from_observed_results(self):
        runbook = (ROOT / "docs/android16-arm64-cluster-experiments.md").read_text()
        experiments = [int(n) for n in re.findall(r"^## Experiment (\d+) ", runbook, re.M)]
        self.assertEqual(experiments, list(range(1, 13)))
        self.assertIn("proposed runbook", runbook)
        self.assertIn("not implemented artifacts", runbook)
        self.assertIn("--remote_accept_cache=false", runbook)
        self.assertIn("--remote_update_cache=false", runbook)
        self.assertIn("ThinLTO", runbook)
        self.assertIn("no backend, remote action, full platform graph or full image", runbook)

    def test_tool_swap_probes_preserve_scope_and_download_identity(self):
        record = json.loads((RESEARCH / "tool-swap-probes.json").read_text())
        self.assertEqual(record["schema_version"], 1)
        self.assertTrue(all(value is False for value in record["boundaries"].values()))
        triples = {item["triple"] for item in record["rust"]["downloads"]}
        self.assertEqual(triples, {"aarch64-unknown-linux-gnu", "aarch64-unknown-linux-musl"})
        for download in record["rust"]["downloads"] + [record["llvm"]["archive"]]:
            self.assertTrue(download["url"].startswith("https://"))
            self.assertRegex(download["sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(record["rust"]["runtime_signature_followup"]["verified"])

    def test_native_rust_success_does_not_hide_metadata_or_libc_failures(self):
        rust = json.loads((RESEARCH / "tool-swap-probes.json").read_text())["rust"]
        probes = {p["id"]: p for p in rust["probes"]}
        for name in ("gnu-explicit-sysroot-soong-flags", "gnu-macro-run",
                     "musl-runtime-version", "musl-runtime-soong-flags",
                     "musl-coherent-proc-consumer", "musl-coherent-proc-run"):
            self.assertEqual(probes[name]["exit_code"], 0, name)
        self.assertIn("E0514", probes["gnu-stock-stdlib-cross-metadata"]["stderr"])
        self.assertNotEqual(probes["gnu-soong-flags-stable"]["exit_code"], 0)
        self.assertIn("libc_musl.so", rust["coherent_musl_macro_needed"])
        self.assertNotIn("libc.so.6", rust["coherent_musl_macro_needed"])
        self.assertTrue(rust["fixture_corrections"])
        self.assertIn("PAC/BTI compiler-patch equivalence", rust["not_established"])

    def test_java_byte_comparisons_include_a_real_jni_counterexample(self):
        java = json.loads((RESEARCH / "tool-swap-probes.json").read_text())["java"]
        self.assertTrue(java["inputs_unchanged"])
        self.assertEqual(java["inputs_before"], java["inputs_after"])
        self.assertTrue(all(p["exit_code"] == 0 for p in java["probes"]))
        for comparison in java["comparisons"].values():
            self.assertTrue(comparison.get("equal", comparison.get("equal_bytes")))
        jni = {p["id"]: p for p in java["jni"]["probes"]}
        self.assertEqual(jni["stock"]["exit_code"], 0)
        self.assertNotEqual(jni["native"]["exit_code"], 0)
        self.assertIn("UnsatisfiedLinkError", jni["native"]["stderr"])
        self.assertTrue(java["jni"]["inputs_unchanged"])

    def test_native_llvm_receipt_keeps_mlgo_and_libclang_limits(self):
        llvm = json.loads((RESEARCH / "tool-swap-probes.json").read_text())["llvm"]
        failures = [p for p in llvm["probes"] if p["exit_code"] != 0]
        self.assertEqual(len(failures), 1)
        self.assertIn("mlgo", failures[0]["id"])
        self.assertIn("regalloc eviction advisor", failures[0]["stderr"])
        self.assertEqual(llvm["nonruntime_libclang_entries"], [])
        for name in ("ar-output", "ar-bitcode-output", "objcopy-output", "readobj-output",
                     "generated-text", "generated-object-without-comment"):
            self.assertTrue(llvm["byte_equal"][name], name)
        self.assertFalse(llvm["byte_equal"]["generated-object"])
        self.assertIn("Community", llvm["source_status"])


if __name__ == "__main__":
    unittest.main()
