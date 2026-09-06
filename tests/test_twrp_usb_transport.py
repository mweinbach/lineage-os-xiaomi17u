"""Offline source checks for ordinary recovery adbd transport admission.

The public full-file patch supplies every tested source byte. These tests do
not read source captures, start processes, contact a phone, or run Soong/C++.
Conditional projection checks only the reviewed guards, not an Android binary.
Authenticated forwarding and shell network access are outside this restriction.
"""

import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts import twrp_patch_state as state
from support import canonical_json_sha256 as canonical


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0024-recovery-usb-only-adb"
AUTH_ID = "0004-require-recovery-adb-auth"
OWNER = "packages/modules/adb"
REVISION = "ce023afef190b0cea7f8939e9dd5ee3ee79b137b"
REPOSITORY = "https://android.googlesource.com/platform/" + OWNER
PATCH_SHA256 = "e472bfde972d168fdc8dd1190298a2891d165a083ce3e02898dcd88e8882d792"
REVIEWED_CANDIDATE_SHA256 = "8ecb76333df2f0a21323ad929204a9cd78bbf1f650c218fe98ce25740fcc8d4d"
OLD_SERIES_SHA256 = "cc2fa6b5edf39619be5166d4888ecb8abf108bab6428d3a812df026df18fdd33"
OLD_PREFIX_SHA256 = "8f70a8034f55d4646beac906a3edf9ede454fd9fac512a1c471c90786900d8ed"
NONPATCH_SHA256 = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
SNAPSHOT = ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
SNAPSHOT_SHA256 = "e967ec0392a3438f4706278e9e77b0810c4401a36f0e64c211a1e5c6e5bfb051"
PATHS = ("daemon/main.cpp", "daemon/adb_wifi.cpp")
# SHA-256, Git blob ID, byte count, line count; not inferred from mutable metadata.
IDENTITIES = {
    PATHS[0]: {
        "before": ("87934aa1c82e8cb8b728230467b75643fe8462a58a13d60e11f035741e6a157e",
                   "9073e34fdaa81bc3c7a7c72235b8909d3a40359e", 13123, 371),
        "after": ("8a9aec32ad19c081349aa3fd908e9c406e78b31c2a34ca7651d728e6b576d2b3",
                  "4a5983abe6931cc41ad40ba2ed195eb8697cb092", 13521, 383),
    },
    PATHS[1]: {
        "before": ("d77f683e7c4349d7ea4e742d97482d16ccd2f1fec086a124512a43d4bc5105fb",
                   "a62db3a0d7069727e244d7aeadf0e799a65edcf1", 6676, 224),
        "after": ("29d449caab9a0d859f5a8a1d5d308430042494fdcd786425497789c0ac32cd6a",
                  "1ca53f672ed0b8449bdfc9ceec33e4185e71b8af", 6832, 224),
    },
}
PRISTINE_MAIN = ("8b9ea62b9ec742a6f3fe15b3c2612b929dbdc2d57aa86f3609ad54744ddba8ca",
                 "931b170211a4aab20069920cdbdc18fc325ee95e", 13274, 371)
RECOVERY_DEFINES = {"__ANDROID__", "__ANDROID_RECOVERY__"}
NORMAL_DEFINES = (set(), {"__ANDROID__"}, {"__BIONIC__"}, {"__ANDROID__", "__BIONIC__"})
WIFI_GUARD = "#if defined(__ANDROID__) && !defined(__ANDROID_RECOVERY__)"
USB_BRANCH = (
    "#if defined(__ANDROID_RECOVERY__)\n"
    "    // Recovery ADB must never substitute a network transport for missing USB.\n"
    "    if (access(USB_FFS_ADB_EP0, F_OK) != 0) {\n"
    '        PLOG(ERROR) << "Recovery ADB requires a USB FunctionFS endpoint";\n'
    "        return 1;\n"
    "    }\n"
    "    usb_init();\n"
    "#else\n"
)
MAIN_NETWORK_TOKENS = (
    "service.adb.listen_addrs", "service.adb.tcp.port", "persist.adb.tcp.port",
    "ADBD_PORT", "static void setup_adb", "init_transport_socket_server(",
    "setup_mdns(", '"tcp:%d"', '"vsock:%d"',
)
WIFI_NETWORK_TOKENS = (
    "class TlsServer", "start_wifi_enabled_observer", "WaitForProperty(",
    "enable_wifi_debugging", "network_inaddr_any_server(",
    "persist.adb.tls_server.enable", "service.adb.tls.port", "register_socket_transport(",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    return sha256(data), blob, len(data), len(data.splitlines())


def full_sources(payload):
    """Reconstruct both complete files; accept only two full-file text hunks."""
    if not payload.endswith(b"\n") or b"\r" in payload or b"\0" in payload:
        raise ValueError("Expected complete LF-terminated source text")
    sections = payload.decode().split("diff --git ")
    if sections[0] or len(sections) != len(PATHS) + 1:
        raise ValueError("Expected exactly the two reviewed source sections")
    result = {}
    for relative, section in zip(PATHS, sections[1:]):
        lines = section.splitlines(keepends=True)
        if len(lines) < 6 or lines[0] != f"a/{relative} b/{relative}\n":
            raise ValueError("Unexpected source path or section order")
        index = re.fullmatch(r"index ([0-9a-f]{40})\.\.([0-9a-f]{40}) 100644\n", lines[1])
        if not index or lines[2:4] != [f"--- a/{relative}\n", f"+++ b/{relative}\n"]:
            raise ValueError("Expected complete Git identities and unchanged regular-file mode")
        hunk = re.fullmatch(r"@@ -1,(\d+) \+1,(\d+) @@\n", lines[4])
        body = lines[5:]
        if not hunk or any(line[:1] not in (" ", "+", "-") for line in body):
            raise ValueError("Expected one full-file hunk without extra directives")
        before = "".join(line[1:] for line in body if line.startswith((" ", "-"))).encode()
        after = "".join(line[1:] for line in body if line.startswith((" ", "+"))).encode()
        if (len(before.splitlines()) != int(hunk[1])
                or len(after.splitlines()) != int(hunk[2])):
            raise ValueError("Full-file hunk count differs from reconstructed source")
        if identity(before)[1] != index[1] or identity(after)[1] != index[2]:
            raise ValueError("Full Git index does not bind reconstructed source")
        result[relative] = {"before": before, "after": after}
    return result


def verify_identities(sources, metadata):
    if tuple(sources) != PATHS or tuple(item["path"] for item in metadata) != PATHS:
        raise ValueError("Source closure changed")
    for item in metadata:
        for phase in ("before", "after"):
            expected = IDENTITIES[item["path"]][phase]
            declared = (item[phase + "_sha256"], item[phase + "_git_blob"],
                        item[phase + "_size_bytes"])
            if identity(sources[item["path"]][phase]) != expected or declared != expected[:3]:
                raise ValueError("Reviewed whole-file identity changed")
        if item.get("mode") != "100644":
            raise ValueError("Reviewed source mode changed")


def reverse_auth_patch(after, payload):
    """Undo the public patch4 hunks in memory, checking both coordinate sets."""
    text = payload.decode()
    expected_header = (
        "diff --git a/daemon/main.cpp b/daemon/main.cpp\n"
        f"index {PRISTINE_MAIN[1]}..{IDENTITIES[PATHS[0]]['before'][1]} 100644\n"
        "--- a/daemon/main.cpp\n+++ b/daemon/main.cpp\n"
    )
    if not text.startswith(expected_header):
        raise ValueError("Authentication predecessor header changed")
    pattern = r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n"
    matches = list(re.finditer(pattern, text, re.M))
    if len(matches) != 2 or matches[0].start() != len(expected_header):
        raise ValueError("Authentication predecessor hunk inventory changed")
    source, result, cursor = after.decode().splitlines(keepends=True), [], 0
    for number, match in enumerate(matches):
        end = matches[number + 1].start() if number + 1 < len(matches) else len(text)
        body = text[match.end():end].splitlines(keepends=True)
        if any(line[:1] not in (" ", "+", "-") for line in body):
            raise ValueError("Unexpected authentication patch directive")
        old = [line[1:] for line in body if line.startswith((" ", "-"))]
        new = [line[1:] for line in body if line.startswith((" ", "+"))]
        old_start, old_count, new_start, new_count = map(int, match.groups())
        start = new_start - 1
        if (start < cursor or len(old) != old_count or len(new) != new_count
                or source[start:start + new_count] != new):
            raise ValueError("Authentication predecessor context does not match")
        result.extend(source[cursor:start])
        if len(result) != old_start - 1:
            raise ValueError("Authentication predecessor source coordinates differ")
        result.extend(old)
        cursor = start + new_count
    return "".join(result + source[cursor:]).encode()


def condition(expression, defines):
    """Evaluate only defined(), boolean literals, !, && and ||; never eval()."""
    expression = re.sub(r"defined\s*\(\s*(\w+)\s*\)",
                        lambda match: str(match[1] in defines), expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = re.sub(r"!(?!=)", " not ", expression)
    try:
        node = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as error:
        raise ValueError("Unsupported source conditional") from error

    def evaluate(value):
        if isinstance(value, ast.Expression):
            return evaluate(value.body)
        if isinstance(value, ast.Constant) and type(value.value) in (bool, int):
            return bool(value.value)
        if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Not):
            return not evaluate(value.operand)
        if isinstance(value, ast.BoolOp) and isinstance(value.op, (ast.And, ast.Or)):
            values = [evaluate(item) for item in value.values]
            return all(values) if isinstance(value.op, ast.And) else any(values)
        raise ValueError("Unsupported source conditional")

    return evaluate(node)


def projection(source, defines):
    """Select reviewed source guards; this is deliberately not a C preprocessor."""
    stack, active, output = [], True, []
    for line in source.splitlines():
        match = re.match(r"^\s*#\s*(\w+)(.*)$", line)
        if not match:
            if active and line.strip():
                output.append(line)
            continue
        directive, expression = match.groups()
        expression = expression.split("//", 1)[0].strip()
        if directive in ("if", "ifdef", "ifndef"):
            if directive != "if" and not re.fullmatch(r"\w+", expression):
                raise ValueError("Unsupported macro name")
            selected = condition(expression, defines) if directive == "if" else expression in defines
            if directive == "ifndef":
                selected = not selected
            stack.append([active, selected, False])
            active = active and selected
        elif directive in ("else", "elif"):
            if not stack or stack[-1][2] or (directive == "else" and expression):
                raise ValueError("Unexpected source conditional branch")
            parent, previous, _ = stack[-1]
            selected = True if directive == "else" else condition(expression, defines)
            active = parent and not previous and selected
            stack[-1] = [parent, previous or selected, directive == "else"]
        elif directive == "endif":
            if not stack or expression:
                raise ValueError("Unexpected conditional terminator")
            active = stack.pop()[0]
        elif directive not in ("include", "define", "pragma"):
            raise ValueError("Unsupported source directive")
    if stack:
        raise ValueError("Unclosed source conditional")
    return "\n".join(output) + "\n"


def function(source, name):
    """Extract a reviewed function whose body has balanced literal braces."""
    match = re.search(r"\b" + re.escape(name) + r"\([^;]*?\)\s*\{", source)
    if not match:
        raise ValueError("Missing reviewed function: " + name)
    depth = 0
    for index in range(source.index("{", match.start()), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise ValueError("Unclosed reviewed function")


def reviewed_postimage(relative, before):
    """Derive the approved minimal source edit independently of patch hashes."""
    if relative == PATHS[0]:
        start = "static void setup_adb("
        end = "}\n\nint adbd_main() {"
        if before.count(start) != 1 or before.count(end) != 1:
            raise ValueError("Network setup boundaries changed")
        expected = before.replace(start, "#if !defined(__ANDROID_RECOVERY__)\n" + start, 1)
        expected = expected.replace(end, "}\n#endif  // !defined(__ANDROID_RECOVERY__)\n\nint adbd_main() {", 1)
        start = "    bool is_usb = false;\n"
        end = '    LOG(INFO) << "adbd started";'
        if expected.count(start) != 1 or expected.count(end) != 1:
            raise ValueError("Transport selection boundaries changed")
        begin, finish = expected.index(start), expected.index(end)
        return (expected[:begin] + USB_BRANCH + expected[begin:finish]
                + "#endif  // defined(__ANDROID_RECOVERY__)\n\n" + expected[finish:])
    if relative == PATHS[1]:
        if before.count("#if defined(__ANDROID__)\n") != 2 or before.count("#endif  //__ANDROID__") != 2:
            raise ValueError("Wi-Fi implementation and startup guards changed")
        return before.replace("#if defined(__ANDROID__)\n", WIFI_GUARD + "\n").replace(
            "#endif  //__ANDROID__", "#endif  // defined(__ANDROID__) && !defined(__ANDROID_RECOVERY__)")
    raise ValueError("Unreviewed source path")


def validate_source_edit(relative, before, after):
    if reviewed_postimage(relative, before) != after:
        raise ValueError("Source differs from the reviewed USB-only edit")


def usb_file(records, relative):
    """Target the reviewed USB file even when unrelated patches follow it."""
    entries = [entry for entry in records if entry["id"] == PATCH_ID]
    if len(entries) != 1:
        raise ValueError("Expected exactly one reviewed USB patch")
    files = [item for item in entries[0]["files"] if item["path"] == relative]
    if len(files) != 1:
        raise ValueError("Expected exactly one reviewed USB source file")
    return files[0]


class TwrpUsbTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.entries = {item["id"]: item for item in cls.record["patches"]}
        cls.entry = cls.entries[PATCH_ID]
        cls.payload = (ROOT / cls.entry["patch"]).read_bytes()
        cls.sources = full_sources(cls.payload)
        cls.before = {path: value["before"].decode() for path, value in cls.sources.items()}
        cls.after = {path: value["after"].decode() for path, value in cls.sources.items()}
        cls.auth_payload = (ROOT / cls.entries[AUTH_ID]["patch"]).read_bytes()
        cls.pristine = reverse_auth_patch(cls.sources[PATHS[0]]["before"], cls.auth_payload)

    def test_full_file_payload_and_reviewed_candidate_mapping_are_pinned(self):
        self.assertEqual(self.entry["patch"], "patches/twrp/" + PATCH_ID + ".patch")
        self.assertEqual(self.entry["patch_sha256"], PATCH_SHA256)
        self.assertEqual(sha256(self.payload), PATCH_SHA256)
        self.assertEqual(len(self.payload), 21488)
        self.assertEqual(self.entry["reviewed_candidate_sha256"], REVIEWED_CANDIDATE_SHA256)
        self.assertNotEqual(PATCH_SHA256, REVIEWED_CANDIDATE_SHA256)
        verify_identities(self.sources, self.entry["files"])

    def test_frozen_manifest_binds_adb_and_soong_source_revisions(self):
        raw = SNAPSHOT.read_bytes()
        self.assertEqual(sha256(raw), SNAPSHOT_SHA256)
        frozen = {item.get("path", item.get("name")): item.attrib
                  for item in ET.fromstring(raw).findall("project")}
        self.assertEqual(frozen[OWNER]["revision"], REVISION)
        self.assertEqual(frozen["build/soong"]["revision"], "91bdc79cffb29d35b2d46a33204c061c3e7ed4f7")
        self.assertEqual(self.entry["project"], OWNER)
        self.assertEqual(self.entry["repository"], REPOSITORY)
        self.assertEqual(self.entry["base_commit"], REVISION)
        for item in self.entry["files"]:
            self.assertEqual(item["source_url"], REPOSITORY + "/+/" + REVISION + "/" + item["path"] + "?format=TEXT")

    def test_old_twenty_three_records_payloads_and_nonpatch_metadata_are_unchanged(self):
        self.assertGreaterEqual(len(self.record["patches"]), 24)
        self.assertEqual(self.record["patches"][23]["id"], PATCH_ID)
        self.assertEqual(canonical(self.record["patches"][:23]), OLD_PREFIX_SHA256)
        self.assertEqual(canonical({key: value for key, value in self.record.items() if key != "patches"}), NONPATCH_SHA256)
        for entry in self.record["patches"][:23]:
            with self.subTest(patch=entry["id"]):
                self.assertEqual(sha256((ROOT / entry["patch"]).read_bytes()), entry["patch_sha256"])

    def test_source_attribution_is_preserved_in_both_complete_files(self):
        for relative, year in zip(PATHS, (2015, 2019)):
            with self.subTest(path=relative):
                before, after = self.before[relative], self.after[relative]
                self.assertTrue(before.startswith(f"/*\n * Copyright (C) {year} The Android Open Source Project\n"))
                license_text = before.split(" */", 1)[0] + " */\n"
                self.assertIn("Licensed under the Apache License, Version 2.0", license_text)
                self.assertTrue(after.startswith(license_text))

    def test_source_closure_has_only_main_and_wifi_without_android_build_or_policy_changes(self):
        self.assertEqual(tuple(self.sources), PATHS)
        self.assertEqual(tuple(item["path"] for item in self.entry["files"]), PATHS)
        additions = "\n".join(line[1:] for line in self.payload.decode().splitlines()
                              if line.startswith("+") and not line.startswith("+++"))
        for token in ("auth_required", "ro.secure", "ro.adb.secure", "service.adb.root",
                      "minijail", "selinux", "permissive", "minadbd", "/adb_keys"):
            with self.subTest(token=token):
                self.assertNotIn(token, additions)

    def test_predecessor_reconstructs_original_upstream_main_from_public_patch4(self):
        self.assertEqual(identity(self.pristine), PRISTINE_MAIN)
        predecessor = self.entries[AUTH_ID]["files"][0]
        self.assertEqual(identity(self.pristine)[:3], (predecessor["before_sha256"],
                         predecessor["before_git_blob"], predecessor["before_size_bytes"]))
        for field in ("sha256", "git_blob", "size_bytes"):
            self.assertEqual(self.entry["files"][0]["before_" + field], predecessor["after_" + field])
        self.assertNotEqual(self.pristine, self.sources[PATHS[0]]["before"])

    def test_reverse_auth_patch_rejects_changed_context_or_coordinates(self):
        mutations = (
            self.auth_payload.replace(b"+163,14", b"+162,14", 1),
            self.auth_payload.replace(b"-163,12", b"-162,12", 1),
            self.auth_payload.replace(b"+    auth_required = true;", b"+    auth_required = false;", 1),
            self.auth_payload.replace(b"+#endif\n", b"+#else\n", 1),
        )
        for mutated in mutations:
            with self.subTest(payload=sha256(mutated)), self.assertRaises(ValueError):
                reverse_auth_patch(self.sources[PATHS[0]]["before"], mutated)

    def test_exact_minimal_edits_reproduce_both_reviewed_postimages(self):
        for relative in PATHS:
            with self.subTest(path=relative):
                validate_source_edit(relative, self.before[relative], self.after[relative])

    def test_complete_authentication_privilege_drop_and_selinux_prefix_is_unchanged(self):
        before, after = self.before[PATHS[0]], self.after[PATHS[0]]
        self.assertEqual(before.split("static void setup_adb(", 1)[0],
                         after.split("#if !defined(__ANDROID_RECOVERY__)\nstatic void setup_adb(", 1)[0])
        for name in ("should_drop_privileges", "drop_privileges"):
            self.assertEqual(function(before, name), function(after, name))
        start = "int adbd_main() {"
        self.assertEqual(before.split(start, 1)[1].split("    bool is_usb = false;", 1)[0],
                         after.split(start, 1)[1].split(USB_BRANCH, 1)[0])

    def test_recovery_keeps_auth_root_drop_local_auth_socket_and_selinux_transitions(self):
        source = projection(self.after[PATHS[0]], RECOVERY_DEFINES)
        for required in ("auth_required = true;", "adbd_cloexec_auth_socket();", "drop_privileges();",
                         "adbd_auth_init();", "minijail_change_uid(jail.get(), AID_SHELL);",
                         "minijail_change_gid(jail.get(), AID_SHELL);", "selinux_android_setcon(root_seclabel)",
                         'GetBoolProperty("ro.secure", true)', "CAP_EFFECTIVE", "CAP_PERMITTED"):
            with self.subTest(required=required):
                self.assertIn(required, source)
        for forbidden in ("auth_required = false", "enter_tradeinmode(", "is_in_tradein_evaluation_mode("):
            self.assertNotIn(forbidden, source)

    def test_event_loop_cli_and_security_order_are_preserved(self):
        anchor = '    LOG(INFO) << "adbd started";'
        self.assertEqual(self.before[PATHS[0]].split(anchor, 1)[1], self.after[PATHS[0]].split(anchor, 1)[1])
        main = function(projection(self.after[PATHS[0]], RECOVERY_DEFINES), "adbd_main")
        ordered = ["auth_required = true;", "drop_privileges();", "adbd_auth_init();",
                   "access(USB_FFS_ADB_EP0, F_OK)", "usb_init();", "fdevent_loop();"]
        positions = [main.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_all_normal_android_and_host_source_projections_are_unchanged(self):
        for relative in PATHS:
            for defines in NORMAL_DEFINES:
                with self.subTest(path=relative, defines=sorted(defines)):
                    self.assertEqual(projection(self.before[relative], defines), projection(self.after[relative], defines))

    def test_normal_main_projection_remains_identical_even_before_auth_patch4(self):
        for defines in NORMAL_DEFINES:
            with self.subTest(defines=sorted(defines)):
                self.assertEqual(projection(self.pristine.decode(), defines), projection(self.after[PATHS[0]], defines))

    def test_original_recovery_has_default_tcp_vsock_fallback_and_explicit_addresses(self):
        main = projection(self.before[PATHS[0]], RECOVERY_DEFINES)
        self.assertIn("else if (!is_usb)", main)
        self.assertIn('"tcp:%d", DEFAULT_ADB_LOCAL_TRANSPORT_PORT', main)
        self.assertIn('"vsock:%d", DEFAULT_ADB_LOCAL_TRANSPORT_PORT', main)
        self.assertIn('GetProperty("service.adb.listen_addrs", "")', main)
        self.assertIn("init_transport_socket_server(addr);", main)
        wifi = projection(self.before[PATHS[1]], RECOVERY_DEFINES)
        self.assertIn("class TlsServer", wifi)
        self.assertIn("start_wifi_enabled_observer();", wifi)

    def test_recovery_has_no_default_or_property_selected_host_socket_listener(self):
        for defines in (RECOVERY_DEFINES, RECOVERY_DEFINES | {"__BIONIC__"}):
            source = projection(self.after[PATHS[0]], defines)
            for token in MAIN_NETWORK_TOKENS:
                with self.subTest(defines=sorted(defines), token=token):
                    self.assertNotIn(token, source)

    def test_missing_functionfs_endpoint_returns_error_before_usb_or_event_loop(self):
        main = function(projection(self.after[PATHS[0]], RECOVERY_DEFINES), "adbd_main")
        expected = (
            "if (access(USB_FFS_ADB_EP0, F_OK) != 0) {\n"
            '        PLOG(ERROR) << "Recovery ADB requires a USB FunctionFS endpoint";\n'
            "        return 1;\n"
            "    }\n"
            "    usb_init();"
        )
        self.assertIn(expected, main)
        self.assertEqual(main.count("usb_init();"), 1)
        self.assertLess(main.index(expected), main.index("fdevent_loop();"))
        # This checks initial endpoint admission; later USB open/retry is not modeled.
        self.assertNotIn("setup_adb(", main)

    def test_recovery_has_neither_wifi_listener_implementation_nor_observer_start(self):
        for defines in (RECOVERY_DEFINES, RECOVERY_DEFINES | {"__BIONIC__"}):
            source = projection(self.after[PATHS[1]], defines)
            for token in WIFI_NETWORK_TOKENS:
                with self.subTest(defines=sorted(defines), token=token):
                    self.assertNotIn(token, source)
            self.assertEqual(function(source, "adbd_wifi_init"),
                             "adbd_wifi_init(AdbdAuthContext* ctx) {\n    auth_ctx = ctx;\n}")

    def test_existing_wifi_auth_context_and_connection_callbacks_are_unchanged(self):
        for name in ("adb_disconnected", "adbd_wifi_secure_connect"):
            self.assertEqual(function(self.before[PATHS[1]], name), function(self.after[PATHS[1]], name))
        normal = projection(self.after[PATHS[1]], {"__ANDROID__"})
        self.assertIn("auth_ctx = ctx;", function(normal, "adbd_wifi_init"))
        self.assertIn("start_wifi_enabled_observer();", function(normal, "adbd_wifi_init"))

    def test_normal_android_and_host_network_selection_remains_available(self):
        android = projection(self.after[PATHS[0]], {"__ANDROID__"})
        for token in MAIN_NETWORK_TOKENS:
            if token != "ADBD_PORT":
                self.assertIn(token, android)
        host = projection(self.after[PATHS[0]], set())
        self.assertIn('getenv("ADBD_PORT")', host)
        self.assertIn("init_transport_socket_server(addr);", host)
        self.assertIn("class TlsServer", projection(self.after[PATHS[1]], {"__ANDROID__"}))
        self.assertNotIn("class TlsServer", projection(self.after[PATHS[1]], set()))

    def test_guard_and_fail_closed_mutations_are_rejected_independently_of_hashes(self):
        source = self.after[PATHS[0]]
        mutations = {
            "disable recovery branch": source.replace(USB_BRANCH, USB_BRANCH.replace("#if defined(__ANDROID_RECOVERY__)", "#if 0"), 1),
            "invert recovery branch": source.replace(USB_BRANCH, USB_BRANCH.replace("#if defined(__ANDROID_RECOVERY__)", "#if !defined(__ANDROID_RECOVERY__)"), 1),
            "successful missing endpoint": source.replace(USB_BRANCH, USB_BRANCH.replace("return 1;", "return 0;"), 1),
            "missing endpoint check": source.replace(USB_BRANCH, "#if defined(__ANDROID_RECOVERY__)\n    usb_init();\n#else\n", 1),
            "USB before endpoint check": source.replace(USB_BRANCH, USB_BRANCH.replace("    if (access", "    usb_init();\n    if (access"), 1),
            "compile setup in recovery": source.replace("#if !defined(__ANDROID_RECOVERY__)\nstatic void setup_adb", "#if 1\nstatic void setup_adb", 1),
            "explicit recovery listener": source.replace(USB_BRANCH, USB_BRANCH.replace("    usb_init();", '    init_transport_socket_server("tcp:5555");\n    usb_init();'), 1),
            "auth weakened": source.replace("    auth_required = true;", "    auth_required = false;", 1),
            "root drop removed": source.replace("    drop_privileges();\n", "", 1),
            "ordinary listener changed": source.replace('"service.adb.listen_addrs"', '"service.adb.changed_listen_addrs"', 1),
        }
        for label, mutated in mutations.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                validate_source_edit(PATHS[0], self.before[PATHS[0]], mutated)

    def test_each_wifi_guard_is_required_for_recovery_listener_closure(self):
        source = self.after[PATHS[1]]
        first = source.replace(WIFI_GUARD, "#if defined(__ANDROID__)", 1)
        last = "#if defined(__ANDROID__)".join(source.rsplit(WIFI_GUARD, 1))
        self.assertIn("class TlsServer", projection(first, RECOVERY_DEFINES))
        self.assertIn("network_inaddr_any_server(", projection(first, RECOVERY_DEFINES))
        self.assertIn("start_wifi_enabled_observer();", projection(last, RECOVERY_DEFINES))
        for mutated in (first, last, source.replace("&& !defined(__ANDROID_RECOVERY__)", "|| defined(__ANDROID_RECOVERY__)"),
                        source.replace("    auth_ctx = ctx;\n", "")):
            with self.subTest(source=sha256(mutated.encode())), self.assertRaises(ValueError):
                validate_source_edit(PATHS[1], self.before[PATHS[1]], mutated)

    def test_main_guard_removal_exposes_the_old_recovery_network_path(self):
        source = self.after[PATHS[0]].replace(USB_BRANCH, USB_BRANCH.replace("#if defined(__ANDROID_RECOVERY__)", "#if 0"), 1)
        selected = projection(source, RECOVERY_DEFINES)
        self.assertIn("service.adb.listen_addrs", selected)
        self.assertIn('"vsock:%d", DEFAULT_ADB_LOCAL_TRANSPORT_PORT', selected)

    def test_full_file_parser_rejects_truncation_extra_files_modes_and_partial_hunks(self):
        mutations = {
            "truncated newline": self.payload[:-1],
            "truncated source": self.payload.rsplit(b"\n", 2)[0] + b"\n",
            "extra file": self.payload + self.payload,
            "partial hunk": self.payload.replace(b"@@ -1,371 +1,383 @@", b"@@ -2,371 +2,383 @@", 1),
            "wrong counts": self.payload.replace(b"@@ -1,371 +1,383 @@", b"@@ -1,370 +1,383 @@", 1),
            "executable mode": self.payload.replace(b" 100644\n", b" 100755\n", 1),
            "short Git index": self.payload.replace(IDENTITIES[PATHS[0]]["before"][1].encode(), b"9073e34", 1),
            "interior source mutation": self.payload.replace(b" minijail_change_uid", b" minijail_changed_uid", 1),
            "wrong file closure": self.payload.replace(b"daemon/adb_wifi.cpp", b"daemon/auth.cpp"),
            "EOF directive": self.payload + b"\\ No newline at end of file\n",
            "binary payload": self.payload + b"\0\n",
        }
        for label, mutated in mutations.items():
            self.assertNotEqual(mutated, self.payload, label)
            with self.subTest(case=label), self.assertRaises(ValueError):
                full_sources(mutated)

    def test_reviewed_identity_constants_reject_metadata_rewrites(self):
        for field, value in (("before_sha256", "0" * 64), ("after_git_blob", "0" * 40),
                             ("after_size_bytes", 1), ("mode", "100755")):
            metadata = copy.deepcopy(self.entry["files"])
            metadata[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_identities(self.sources, metadata)

    def test_projection_rejects_unsupported_or_unbalanced_constructs(self):
        for expression in ("UNKNOWN", "unknown()", "defined(X) == 1", "True or unknown()", "1 + 1"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                condition(expression, set())
        for source in ("#if defined(X)\nbody\n", "#else\n", "#endif\n", "#error failure\n",
                       "#if 1\n#else\n#else\n#endif\n", "#if 1\n#else\n#elif 1\n#endif\n"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                projection(source, set())

    def test_actual_public_inventory_accepts_append_without_any_process_calls(self):
        denied = AssertionError("Offline source tests must not start a process")
        with patch("subprocess.run", side_effect=denied) as run, patch("subprocess.Popen", side_effect=denied) as popen:
            reviewed = state.patch_inventory({"manifest": self.record["manifest"]}, ROOT)
            previous = {"series_sha256": OLD_SERIES_SHA256, "patches": self.record["patches"][:23]}
            extension = state.validate_patch_extension(previous, reviewed)
            self.assertEqual(reviewed["patches"], self.record["patches"])
            self.assertEqual(extension["patches"], self.record["patches"][23:])
            self.assertEqual(extension["patches"][0], self.entry)
            self.assertEqual(extension["complete_patches"], self.record["patches"])
            self.assertEqual(extension["previous_patch_count"], 23)
            run.assert_not_called()
            popen.assert_not_called()

    def test_actual_plan_contains_only_one_explicit_chain_and_one_fresh_wifi_file(self):
        # These exact counts describe the historical USB admission cohort.
        cohort = {"patches": self.record["patches"][:24]}
        plan = state.patch_plan(cohort)
        chains = [(owner, path, item) for owner, project in plan["projects"].items()
                  for path, item in project["files"].items() if len(item["steps"]) > 1]
        self.assertTrue(plan["has_chains"])
        self.assertEqual(plan["patch_count"], 24)
        self.assertEqual([(owner, path) for owner, path, _ in chains], [(OWNER, PATHS[0])])
        main = chains[0][2]
        self.assertEqual([step["patch_id"] for step in main["steps"]], [AUTH_ID, PATCH_ID])
        self.assertEqual([step["index"] for step in main["steps"]], [3, 23])
        self.assertEqual(main["root"], self.entries[AUTH_ID]["files"][0])
        wifi = plan["projects"][OWNER]["files"][PATHS[1]]
        self.assertEqual([step["patch_id"] for step in wifi["steps"]], [PATCH_ID])
        self.assertNotIn("predecessor_patch_id", wifi["root"])
        self.assertEqual(sum(len(project["files"]) for project in plan["projects"].values()), 39)
        self.assertEqual(sum(len(entry["files"]) for entry in cohort["patches"]), 40)

        # Still validate the entire current queue and every declared path/touch.
        full = state.patch_plan(self.record)
        self.assertEqual(full["patch_count"], len(self.record["patches"]))
        expected_paths = {(entry["project"], item["path"])
                          for entry in self.record["patches"] for item in entry["files"]}
        actual_files = {(owner, path): chain for owner, project in full["projects"].items()
                        for path, chain in project["files"].items()}
        self.assertEqual(set(actual_files), expected_paths)
        self.assertEqual(sum(len(chain["steps"]) for chain in actual_files.values()),
                         sum(len(entry["files"]) for entry in self.record["patches"]))
        for owner, project in plan["projects"].items():
            for path, chain in project["files"].items():
                actual = actual_files[(owner, path)]
                self.assertEqual(actual["root"], chain["root"])
                self.assertEqual(actual["steps"][:len(chain["steps"])], chain["steps"])

    def test_successor_alone_or_implicit_overlap_is_not_an_authorized_queue(self):
        with self.assertRaisesRegex(ValueError, "First patch touch"):
            state.patch_plan({"patches": [self.entry]})
        for value in (None, "", "missing", PATCH_ID, "0002-do-not-force-adb-root"):
            records = copy.deepcopy(self.record["patches"])
            usb_file(records, PATHS[0])["predecessor_patch_id"] = value
            with self.subTest(predecessor=value), self.assertRaisesRegex(ValueError, "immediate predecessor"):
                state.patch_plan({"patches": records})
        records = copy.deepcopy(self.record["patches"])
        del usb_file(records, PATHS[0])["predecessor_patch_id"]
        with self.assertRaisesRegex(ValueError, "immediate predecessor"):
            state.patch_plan({"patches": records})

    def test_chain_identity_discontinuities_and_fresh_file_predecessor_are_rejected(self):
        for field, value in (("before_sha256", "0" * 64), ("before_git_blob", "0" * 40), ("before_size_bytes", 1)):
            records = copy.deepcopy(self.record["patches"])
            usb_file(records, PATHS[0])[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "discontinuous"):
                state.patch_plan({"patches": records})
        records = copy.deepcopy(self.record["patches"])
        usb_file(records, PATHS[1])["predecessor_patch_id"] = AUTH_ID
        with self.assertRaisesRegex(ValueError, "First patch touch"):
            state.patch_plan({"patches": records})

    def test_extension_cannot_rewrite_authentication_predecessor(self):
        previous = {"patches": self.record["patches"][:23], "series_sha256": OLD_SERIES_SHA256}
        changed = copy.deepcopy(self.record)
        next(entry for entry in changed["patches"] if entry["id"] == AUTH_ID)["reason"] += " changed"
        with self.assertRaisesRegex(ValueError, "exact unchanged prefix"):
            state.validate_patch_extension(previous, changed)

    def test_future_unrelated_append_preserves_usb_checks_and_full_queue_validation(self):
        # A fresh synthetic metadata record needs no payload or source checkout.
        extra = {"id": "fixture-unrelated-after-usb", "project": "fixtures/unrelated",
                 "base_commit": "e" * 40, "files": [{"path": "source.cpp",
                 "before_sha256": "a" * 64, "after_sha256": "b" * 64,
                 "before_size_bytes": 1, "after_size_bytes": 2}]}
        record = copy.deepcopy(self.record)
        record["patches"].append(extra)
        unchanged = copy.deepcopy(record)
        probe = type(self)("test_actual_plan_contains_only_one_explicit_chain_and_one_fresh_wifi_file")
        probe.record = record
        probe.test_old_twenty_three_records_payloads_and_nonpatch_metadata_are_unchanged()
        probe.test_actual_plan_contains_only_one_explicit_chain_and_one_fresh_wifi_file()
        probe.test_successor_alone_or_implicit_overlap_is_not_an_authorized_queue()
        probe.test_chain_identity_discontinuities_and_fresh_file_predecessor_are_rejected()
        self.assertEqual(record, unchanged)
        previous = {"series_sha256": OLD_SERIES_SHA256, "patches": record["patches"][:23]}
        extension = state.validate_patch_extension(previous, record)
        self.assertEqual(extension["patches"], record["patches"][23:])
        self.assertEqual(extension["complete_patches"], record["patches"])
        self.assertEqual(extension["previous_patch_count"], 23)
        # A malformed unrelated append must still reach the full-queue planner.
        invalid = copy.deepcopy(extra)
        invalid["base_commit"] = "invalid"
        probe.record = {**self.record, "patches": self.record["patches"] + [invalid]}
        with self.assertRaisesRegex(ValueError, "full pinned base revision"):
            probe.test_actual_plan_contains_only_one_explicit_chain_and_one_fresh_wifi_file()

    def test_chain_uses_full_matching_indexes_in_both_old_and_new_payloads(self):
        predecessor = self.entries[AUTH_ID]["files"][0]
        state.chain_patch_index(self.auth_payload, PATHS[0], predecessor, mode=0o644)
        for item in self.entry["files"]:
            state.chain_patch_index(self.payload, item["path"], item, mode=0o644)
        item = self.entry["files"][0]
        for mutated in (
                self.payload.replace(item["before_git_blob"].encode(), b"9073e34", 1),
                self.payload.replace(item["after_git_blob"].encode(), b"0" * 40, 1),
                self.payload.replace(b" 100644\n", b" 100755\n", 1)):
            with self.subTest(payload=sha256(mutated)), self.assertRaisesRegex(ValueError, "full matching Git index"):
                state.chain_patch_index(mutated, PATHS[0], item, mode=0o644)


if __name__ == "__main__":
    unittest.main()
