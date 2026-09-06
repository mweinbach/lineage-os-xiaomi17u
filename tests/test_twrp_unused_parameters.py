"""Offline source contract for the21 build54 unused-parameter repairs.

Reads only the public patch and series. Outer-conditional projection preserves
nested source text; it is not C++ compilation or runtime validation.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest

from support import canonical_json_sha256 as canonical, sha256_bytes as digest

ROOT = Path(__file__).resolve().parents[1]

PATCH_ID = '0029-explicit-unused-recovery-parameters'

PATCH_SHA256 = 'b5d127b1d70231dc4edd1f5fbb5c5ce065abd2d022e5a58785ce1d0078f70f38'

ENTRY_SHA256 = '8f2cf040cd15bee5460bd9799a68ea2dfbe17092cd636438eaa0901a726285c6'

REVISION = 'b70f8e998b302381ecefc6e7f46df1614bd61afc'

PRIOR28_SERIALIZED_SHA256 = 'a3087166dd6178b0d3608b12d84995ac8de1ff873ec1c79464082eb60334a9d1'

FILES = [{'path': 'twrpTar.cpp',
  'mode': '100755',
  'before_size_bytes': 48284,
  'after_size_bytes': 48299,
  'before_sha256': '7749d979cc9511d69aa62aded025c6499c39ee3b50defe3c8453bcb733931466',
  'after_sha256': '546bb1226d2330da1455486e24d5f58d48fec4e93850142863d9b7633924769b',
  'before_git_blob': '6794edc7d5758379effdf663860b461a7b309661',
  'after_git_blob': 'b1cc7990f475568a1240d55fce39c22b04ed73ab',
  'before_lines': 1559,
  'after_lines': 1560},
 {'path': 'twrp.cpp',
  'mode': '100644',
  'before_size_bytes': 16158,
  'after_size_bytes': 16173,
  'before_sha256': 'c6f522167f616155913d3e580380474bcf9b6655abecccc8073bcb9f4102232e',
  'after_sha256': '9fa6045c34bd73d3b0523d172c42807fa95d758a076cb386c22d9df37e4d8f1a',
  'before_git_blob': '456c774ccb0e488500b8af9aa7e80de114e37a21',
  'after_git_blob': '2f3bec56a3ad939f88c53c02a33deecd11c484d9',
  'before_lines': 493,
  'after_lines': 494},
 {'path': 'data.cpp',
  'mode': '100644',
  'before_size_bytes': 29478,
  'after_size_bytes': 29500,
  'before_sha256': '40892d3b543ef1178404e929da07a5b046f8ded49e31cd305321a1134c3613d7',
  'after_sha256': 'a4b6b7e95dc5fa2f52dd5aa391d9a848e50593478a4a28a62634c5a41889fdca',
  'before_git_blob': 'c69574a6b180c9f6abe3649ffec3891027d11bb7',
  'after_git_blob': '3c2395442cad7a56b47999ddebf414850877dc3a',
  'before_lines': 998,
  'after_lines': 1000},
 {'path': 'partition.cpp',
  'mode': '100755',
  'before_size_bytes': 114338,
  'after_size_bytes': 114426,
  'before_sha256': 'a7c8c9bdf2a4f845a4555721072934ca183bca86e97b0f4c0c45f22ff6a4825d',
  'after_sha256': '4eca74029d5a289388b71634d1930245c4c1f93d7e10131eddf728d0e6ee400b',
  'before_git_blob': '2531496b293c21c8e908afb3583e2713f3f3eafc',
  'after_git_blob': 'c3fa3df2e245afe1e9d2b76c3f5da5bca618317e',
  'before_lines': 3656,
  'after_lines': 3660},
 {'path': 'twrp-functions.cpp',
  'mode': '100644',
  'before_size_bytes': 43762,
  'after_size_bytes': 43866,
  'before_sha256': 'ac1440e4e4ca9971d6c63b5fbf3bc6b5be2dcef9f65a7be57c9fd15441c30b20',
  'after_sha256': 'feb1dd540e7ebf8db1ed1dc85844c26e6afaba80c3b6eea0ac304ebc1761e203',
  'before_git_blob': 'c310f425afff3dbbf8303931052816d1350a53a6',
  'after_git_blob': '7f0a864433e14b89057ca7471bd0029dc3efd43b',
  'before_lines': 1516,
  'after_lines': 1522},
 {'path': 'partitionmanager.cpp',
  'mode': '100755',
  'before_size_bytes': 130688,
  'after_size_bytes': 130878,
  'before_sha256': '9a7ee5bc9eef5d27112a36425fe5dd0bf37bd1bb627d355bd8989b8031a01ffb',
  'after_sha256': '073cbd2c2af845ec958ba62add709bb7b1fa2f77a8aadc013cad2176e389371a',
  'before_git_blob': '42b848df32ad29d7c7942da4d3d9bd53abbe63a6',
  'after_git_blob': 'dfe12c5a9fea010590dc4440ca60d1510e304cfe',
  'before_lines': 3905,
  'after_lines': 3919}]

CONTRACTS = [{'path': 'twrpTar.cpp',
  'source_line': 113,
  'signature': 'void twrpTar::Signal_Kill(int signum) {',
  'parameters': ['signum'],
  'placement': 'entry',
  'outer_conditional': None,
  'adds_else': False,
  'cast_lines': '\t(void)signum;\n',
  'before_function_sha256': '8a837ce3945f84c2bf4d18d340155126946bf71e7e29357d15349d66802b8ed9',
  'after_function_sha256': '2db74c614ceabe632ccb9b9daf93749d0d9fe8a88eee5b9efc98aae68f7ac450'},
 {'path': 'twrp.cpp',
  'source_line': 80,
  'signature': 'static void Print_Prop(const char *key, const char *name, void *cookie) {',
  'parameters': ['cookie'],
  'placement': 'entry',
  'outer_conditional': None,
  'adds_else': False,
  'cast_lines': '\t(void)cookie;\n',
  'before_function_sha256': 'c63d506fa6c85549d27348484a20815dc453b0bc6828ea1158ac790a62963259',
  'after_function_sha256': '4ad3bac191a7b63c58f3285b456c8d0250d82bec652421c0fc0fe40184d9fbc0'},
 {'path': 'data.cpp',
  'source_line': 982,
  'signature': 'void DataManager::Vibrate(const string& varName)',
  'parameters': ['varName'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifndef TW_NO_HAPTICS',
  'adds_else': True,
  'cast_lines': '\t(void)varName;\n',
  'before_function_sha256': '1179aa64fe1f68daa3ea24894561fe6824b30fdd4cd81a48a606ecd22cbd042b',
  'after_function_sha256': '7da55a4c8ac476f8601772203dc542682becafd8a5a031013caacdad60819e9c'},
 {'path': 'partition.cpp',
  'source_line': 674,
  'signature': 'void TWPartition::Setup_Data_Partition(bool Display_Error) {',
  'parameters': ['Display_Error'],
  'placement': 'entry',
  'outer_conditional': None,
  'adds_else': False,
  'cast_lines': '\t(void)Display_Error;\n',
  'before_function_sha256': '712dc94ed92197bcd25cdfc3430eb60038054099997833c4f00fda104c47def7',
  'after_function_sha256': '8b7e4834591dd840eb7ff1ffc0f02a6ad2e5e4a6265948e7361c428fd2b0a7eb'},
 {'path': 'partition.cpp',
  'source_line': 1327,
  'signature': 'void TWPartition::Find_Real_Block_Device(string& Block, bool Display_Error) {',
  'parameters': ['Display_Error'],
  'placement': 'entry',
  'outer_conditional': None,
  'adds_else': False,
  'cast_lines': '\t(void)Display_Error;\n',
  'before_function_sha256': '1a9c9c439f9ea468c58915ff8f08c5aaea09fc599bf1b22ca6ec6396e8bc462e',
  'after_function_sha256': 'c6977ad85acfba1da26e6b63c595e36367e945f23204ef8477b7f9125ba37bce'},
 {'path': 'partition.cpp',
  'source_line': 1614,
  'signature': 'bool TWPartition::Bind_Mount(bool Display_Error) {',
  'parameters': ['Display_Error'],
  'placement': 'entry',
  'outer_conditional': None,
  'adds_else': False,
  'cast_lines': '\t(void)Display_Error;\n',
  'before_function_sha256': '8f37015fb767c1ebbcf8f46f7a4091b6469aed57e41bc2dfdacb04eaf66a0325',
  'after_function_sha256': '83abd689193932c62cb2fa0da453cc78ca6606e220dee201dae69e34754c4e23'},
 {'path': 'partition.cpp',
  'source_line': 2038,
  'signature': 'string TWPartition::Get_Restore_File_System(PartitionSettings *part_settings) {',
  'parameters': ['part_settings'],
  'placement': 'entry',
  'outer_conditional': None,
  'adds_else': False,
  'cast_lines': '\t(void)part_settings;\n',
  'before_function_sha256': '8595bd2d4ce65686aed6673cdc16d3fbcb1c39beb9bba7f0ffa59b62cb1bd6b0',
  'after_function_sha256': 'e7dc471cae2283509e67dda238871f33779ba0b3add670d4313fbdc2eaa04297'},
 {'path': 'twrp-functions.cpp',
  'source_line': 889,
  'signature': 'void TWFunc::Fixup_Time_On_Boot(const string& time_paths /* = "" */)',
  'parameters': ['time_paths'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef QCOM_RTC_FIX',
  'adds_else': True,
  'cast_lines': '\t(void)time_paths;\n',
  'before_function_sha256': 'dbaf6d480cb88da9c7707ccfa3a67a89eb95f51e7af5ea8ded8461f6e51b5d32',
  'after_function_sha256': '5b2f470453817ef16971079594aaf99b699fde2063426486b46126ae78ea368d'},
 {'path': 'twrp-functions.cpp',
  'source_line': 1088,
  'signature': 'bool TWFunc::Toggle_MTP(bool enable) {',
  'parameters': ['enable'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_HAS_MTP',
  'adds_else': False,
  'cast_lines': '\t(void)enable;\n',
  'before_function_sha256': '19ebbadc7b27fb17f8ceec687fa024c8affa7b557adeabe2035525a40c2fbd24',
  'after_function_sha256': '6c29f959b7250e06821fe9d62e893870ed043b2bb954f24e0d1d4c68aa1935db'},
 {'path': 'twrp-functions.cpp',
  'source_line': 1250,
  'signature': 'int TWFunc::Property_Override(string Prop_Name, string Prop_Value) {',
  'parameters': ['Prop_Name', 'Prop_Value'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_INCLUDE_LIBRESETPROP',
  'adds_else': False,
  'cast_lines': '    (void)Prop_Name;\n    (void)Prop_Value;\n',
  'before_function_sha256': '84f31e96837c49e1bb34e441f6cb213bc6d2405214ac48aa649de184f08c5f15',
  'after_function_sha256': '7723bd32534cc08bf9a72036a5b3b1e5f7500dc747388832d8f3b7b809dd2c8b'},
 {'path': 'twrp-functions.cpp',
  'source_line': 1258,
  'signature': 'int TWFunc::Delete_Property(string Prop_Name) {',
  'parameters': ['Prop_Name'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_INCLUDE_LIBRESETPROP',
  'adds_else': False,
  'cast_lines': '    (void)Prop_Name;\n',
  'before_function_sha256': '783b45feaee9d21646439e4f6382eacb88d25d08a3cbd45306a2ddaf8d0cbbfc',
  'after_function_sha256': 'aec47b03f720fea1a06994f3373e8bfc21772368529f52af9664c20cb50ab17a'},
 {'path': 'partitionmanager.cpp',
  'source_line': 2140,
  'signature': 'void TWPartitionManager::Mark_User_Decrypted(int userID) {',
  'parameters': ['userID'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_INCLUDE_FBE',
  'adds_else': True,
  'cast_lines': '\t(void)userID;\n',
  'before_function_sha256': 'adebd4cb2decbf4d02a57a5ff5d0c4410de269a8e835805b4ce32855f34d4210',
  'after_function_sha256': '44c1949e971e870e8c1a684649e2d45d251e740e6f7771ee1e12511d3c7b559b'},
 {'path': 'partitionmanager.cpp',
  'source_line': 2205,
  'signature': 'int TWPartitionManager::Decrypt_Device(string Password, int user_id) {',
  'parameters': ['Password', 'user_id'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_INCLUDE_CRYPTO',
  'adds_else': False,
  'cast_lines': '\t(void)Password;\n\t(void)user_id;\n',
  'before_function_sha256': 'cfbd852f7df207ebe1128315c03113f6c2dfe48b9d41fc13402932b4df1e8e1c',
  'after_function_sha256': '87587e2daa07e32139a3db6ddb3ec0760fcdbdb3f02a13f4032d59abd6ed9ba7'},
 {'path': 'partitionmanager.cpp',
  'source_line': 2973,
  'signature': 'bool TWPartitionManager::Add_Remove_MTP_Storage(TWPartition* Part, int '
               'message_type) {',
  'parameters': ['Part', 'message_type'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_HAS_MTP',
  'adds_else': False,
  'cast_lines': '\t(void)Part;\n\t(void)message_type;\n',
  'before_function_sha256': 'b5a0a7dad42e4c4da3d8a3d17e7ad49aa8519bdcfacb1f427b9bcffa785c8dd5',
  'after_function_sha256': '4ff191a63a83c330c8e78e547282eb2f0fca1a275ca9c08a5067b95c9353d87b'},
 {'path': 'partitionmanager.cpp',
  'source_line': 3037,
  'signature': 'bool TWPartitionManager::Add_MTP_Storage(string Mount_Point) {',
  'parameters': ['Mount_Point'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_HAS_MTP',
  'adds_else': True,
  'cast_lines': '\t(void)Mount_Point;\n',
  'before_function_sha256': 'c08202ee74f91654e2bc9901187a132f12e9f85d7dc6b454e75a14a46c3fb736',
  'after_function_sha256': 'cfa5eb1b03c10540c3da74af60ba10e2e251b5ee2c4c1a7e099c4e5a39396fbe'},
 {'path': 'partitionmanager.cpp',
  'source_line': 3049,
  'signature': 'bool TWPartitionManager::Add_MTP_Storage(unsigned int Storage_ID) {',
  'parameters': ['Storage_ID'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_HAS_MTP',
  'adds_else': True,
  'cast_lines': '\t(void)Storage_ID;\n',
  'before_function_sha256': '46af8b7d2a27bdc712d8e95fcf00bd4e1b4a965f003e113e28ed16775aca27ed',
  'after_function_sha256': '38aa7667b630dff17f294ac8c24e17c1da42958fe663f70d1d9f65f1919ccd57'},
 {'path': 'partitionmanager.cpp',
  'source_line': 3061,
  'signature': 'bool TWPartitionManager::Remove_MTP_Storage(string Mount_Point) {',
  'parameters': ['Mount_Point'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_HAS_MTP',
  'adds_else': True,
  'cast_lines': '\t(void)Mount_Point;\n',
  'before_function_sha256': '1d4036d5150fb199754271bd25a00531f1ec0edcd9c78e06738e48cc9d786df8',
  'after_function_sha256': 'fff37a40ec4adb5bc6b5aaf17db910f7261f2964077671ae19342d6b8abfb0b8'},
 {'path': 'partitionmanager.cpp',
  'source_line': 3073,
  'signature': 'bool TWPartitionManager::Remove_MTP_Storage(unsigned int Storage_ID) {',
  'parameters': ['Storage_ID'],
  'placement': 'disabled_branch',
  'outer_conditional': '#ifdef TW_HAS_MTP',
  'adds_else': True,
  'cast_lines': '\t(void)Storage_ID;\n',
  'before_function_sha256': '275b01df084e21ecdf0e056a982157ffe77a524f1818a367d9c66f5dc7d6b958',
  'after_function_sha256': '7c1c17900b73112a23966134063b38e815a1fa9029f14e2fd6190592c8f37f23'}]

DIAGNOSTICS = [('twrpTar.cpp', 113, 'signum'),
 ('twrp.cpp', 80, 'cookie'),
 ('data.cpp', 982, 'varName'),
 ('partition.cpp', 674, 'Display_Error'),
 ('partition.cpp', 1327, 'Display_Error'),
 ('partition.cpp', 1614, 'Display_Error'),
 ('partition.cpp', 2038, 'part_settings'),
 ('twrp-functions.cpp', 889, 'time_paths'),
 ('twrp-functions.cpp', 1088, 'enable'),
 ('twrp-functions.cpp', 1250, 'Prop_Name'),
 ('twrp-functions.cpp', 1250, 'Prop_Value'),
 ('twrp-functions.cpp', 1258, 'Prop_Name'),
 ('partitionmanager.cpp', 2140, 'userID'),
 ('partitionmanager.cpp', 2205, 'Password'),
 ('partitionmanager.cpp', 2205, 'user_id'),
 ('partitionmanager.cpp', 2973, 'Part'),
 ('partitionmanager.cpp', 2973, 'message_type'),
 ('partitionmanager.cpp', 3037, 'Mount_Point'),
 ('partitionmanager.cpp', 3049, 'Storage_ID'),
 ('partitionmanager.cpp', 3061, 'Mount_Point'),
 ('partitionmanager.cpp', 3073, 'Storage_ID')]


def serialized_records(text):
    decoder = json.JSONDecoder()
    match = re.search(r'"patches"\s*:\s*\[', text)
    if not match:
        raise ValueError("Missing patch array")
    position = match.end()
    records = []
    while True:
        while text[position].isspace() or text[position] == ",":
            position += 1
        if text[position] == "]":
            return records
        value, end = decoder.raw_decode(text, position)
        if not isinstance(value, dict):
            raise ValueError("Expected patch object")
        records.append(text[position:end])
        position = end


def function(text, signature):
    anchor = signature + "\n"
    if text.count(anchor) != 1:
        raise ValueError("Missing or duplicate reviewed function")
    start = text.index(anchor)
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def outer_conditional(lines):
    depth = 0
    start = alternate = end = None
    for index, line in enumerate(lines):
        token = line.strip()
        if token.startswith(("#ifdef ", "#ifndef ", "#if ")):
            if depth == 0:
                if start is not None:
                    raise ValueError("Only one outer feature conditional is reviewed")
                start = index
            depth += 1
        elif token == "#else" and depth == 1:
            if alternate is not None:
                raise ValueError("Duplicate outer else")
            alternate = index
        elif token == "#endif":
            if depth <= 0:
                raise ValueError("Orphan endif")
            if depth == 1:
                end = index
            depth -= 1
        elif token.startswith(("#elif", "#define", "#undef")):
            raise ValueError("Unreviewed conditional or feature definition")
    if depth or start is None or end is None:
        raise ValueError("Unbalanced or absent feature conditional")
    return start, alternate, end


def transformed_function(before, contract):
    lines = before.splitlines(keepends=True)
    casts = contract["cast_lines"]
    if contract["placement"] == "entry":
        if not lines[0].rstrip().endswith("{"):
            raise ValueError("Unexpected function entry")
        return lines[0] + casts + "".join(lines[1:])
    start, alternate, end = outer_conditional(lines)
    if lines[start].strip() != contract["outer_conditional"]:
        raise ValueError("Feature conditional changed")
    if (alternate is None) != contract["adds_else"]:
        raise ValueError("Existing disabled branch changed")
    if alternate is None:
        return "".join(lines[:end]) + "#else\n" + casts + "".join(lines[end:])
    return "".join(lines[:alternate + 1]) + casts + "".join(lines[alternate + 1:])


def project_outer(text, primary_branch):
    """Select only the outer branch, retaining every nested directive byte."""
    lines = text.splitlines(keepends=True)
    start, alternate, end = outer_conditional(lines)
    selected = lines[start + 1:alternate if alternate is not None else end] if primary_branch else (
        lines[alternate + 1:end] if alternate is not None else [])
    return "".join(lines[:start] + selected + lines[end + 1:])


def validate_patch(raw):
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF text patch")
    text = raw.decode("utf-8")
    offsets = [match.start() for match in re.finditer(r"^diff --git ", text, re.M)]
    if len(offsets) != len(FILES) or offsets[0] != 0:
        raise ValueError("Unexpected file inventory")
    offsets.append(len(text))
    result = {}
    for index, metadata in enumerate(FILES):
        path = metadata["path"]
        section = text[offsets[index]:offsets[index + 1]]
        header = (f"diff --git a/{path} b/{path}\n"
                  f"index {metadata['before_git_blob']}..{metadata['after_git_blob']} {metadata['mode']}\n"
                  f"--- a/{path}\n+++ b/{path}\n"
                  f"@@ -1,{metadata['before_lines']} +1,{metadata['after_lines']} @@\n")
        if not section.startswith(header):
            raise ValueError("Unreviewed path, mode, blobs or complete-file hunk")
        body = section[len(header):].splitlines(keepends=True)
        if (any(line[:1] not in (" ", "+") for line in body)
                or sum(line.startswith(" ") for line in body) != metadata["before_lines"]
                or len(body) != metadata["after_lines"]):
            raise ValueError("Only the reviewed insertions are allowed")
        before = "".join(line[1:] for line in body if line.startswith(" "))
        after = "".join(line[1:] for line in body)
        for stage, source in [("before", before), ("after", after)]:
            data = source.encode()
            if len(data) != metadata[stage + "_size_bytes"] or digest(data) != metadata[stage + "_sha256"]:
                raise ValueError("Complete source bytes changed")
        expected = before
        for contract in [row for row in CONTRACTS if row["path"] == path]:
            original = function(expected, contract["signature"])
            expected = expected.replace(original, transformed_function(original, contract), 1)
        if after != expected:
            raise ValueError("Unreviewed source change outside exact void casts")
        result[path] = (before, after)
    return result


class TwrpUnusedParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue_text = (ROOT / "patches/twrp/series.json").read_text()
        cls.queue = json.loads(cls.queue_text)
        rows = [row for row in cls.queue["patches"] if row["id"] == PATCH_ID]
        if len(rows) != 1:
            raise ValueError("Expected one unused-parameter patch selected by ID")
        cls.entry = rows[0]
        cls.patch = (ROOT / "patches/twrp" / (PATCH_ID + ".patch")).read_bytes()
        cls.sources = validate_patch(cls.patch)

    def test_payload_entry_and_source_file_identities(self):
        self.assertEqual((len(self.patch), digest(self.patch)), (396500, PATCH_SHA256))
        self.assertEqual(canonical(self.entry), ENTRY_SHA256)
        self.assertEqual(self.entry["base_commit"], REVISION)
        self.assertEqual(len(self.entry["files"]), 6)
        for metadata, recorded in zip(FILES, self.entry["files"]):
            self.assertEqual({key: recorded[key] for key in metadata}, metadata)
            self.assertNotIn("predecessor_patch_id", recorded)
            self.assertIn(REVISION, recorded["source_url"])
            for stage, source in zip(("before", "after"), self.sources[metadata["path"]]):
                raw = source.encode()
                blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
                self.assertEqual(blob, metadata[stage + "_git_blob"])

    def test_serialized_prior28_survives_future_appends(self):
        records = serialized_records(self.queue_text)
        self.assertGreaterEqual(len(records), 29)
        self.assertEqual(digest("\n".join(records[:28]).encode()), PRIOR28_SERIALIZED_SHA256)
        rows = self.queue["patches"]
        index = next(i for i, row in enumerate(rows) if row["id"] == PATCH_ID)
        earlier = {(row["project"], f["path"]) for row in rows[:index] for f in row["files"]}
        for metadata in FILES:
            self.assertNotIn(("bootable/recovery", metadata["path"]), earlier)

    def test_exact_twenty_one_diagnostics_in_eighteen_functions(self):
        covered = [(row["path"], row["source_line"], param)
                   for row in CONTRACTS for param in row["parameters"]]
        self.assertEqual(covered, DIAGNOSTICS)
        self.assertEqual((len(CONTRACTS), len(covered), len(set(covered))), (18, 21, 21))
        self.assertEqual(sum(len(row["parameters"]) for row in CONTRACTS if row["placement"] == "entry"), 6)
        for row in CONTRACTS:
            before, after = self.sources[row["path"]]
            self.assertEqual(before.splitlines()[row["source_line"] - 1], row["signature"])
            original = function(before, row["signature"])
            changed = function(after, row["signature"])
            self.assertEqual(digest(original.encode()), row["before_function_sha256"])
            self.assertEqual(digest(changed.encode()), row["after_function_sha256"])
            for param in row["parameters"]:
                self.assertRegex(row["signature"], r"\b" + re.escape(param) + r"\b")

    def test_only_void_casts_and_seven_disabled_else_directives_are_added(self):
        added = [line[1:] for line in self.patch.decode().splitlines()
                 if line.startswith("+") and not line.startswith("+++")]
        self.assertEqual(len(added), 28)
        self.assertEqual(added.count("#else"), 7)
        casts = [line for line in added if line != "#else"]
        self.assertEqual(len(casts), 21)
        self.assertTrue(all(re.fullmatch(r"\s+\(void\)[A-Za-z_][A-Za-z_0-9]*;", line) for line in casts))
        self.assertFalse(any(line.startswith("-") and not line.startswith("---")
                             for line in self.patch.decode().splitlines()))

    def test_enabled_conditional_branches_are_byte_identical(self):
        for row in CONTRACTS:
            if row["placement"] != "disabled_branch":
                continue
            with self.subTest(function=row["signature"]):
                before, after = self.sources[row["path"]]
                original = function(before, row["signature"])
                changed = function(after, row["signature"])
                self.assertEqual(project_outer(original, True), project_outer(changed, True))

    def test_disabled_branches_only_consume_the_expected_parameters(self):
        for row in CONTRACTS:
            if row["placement"] != "disabled_branch":
                continue
            with self.subTest(function=row["signature"]):
                before, after = self.sources[row["path"]]
                original = project_outer(function(before, row["signature"]), False)
                changed = project_outer(function(after, row["signature"]), False)
                self.assertEqual(changed.count(row["cast_lines"]), 1)
                self.assertEqual(changed.replace(row["cast_lines"], "", 1), original)

    def test_always_unused_parameters_preserve_all_existing_body_bytes(self):
        for row in CONTRACTS:
            if row["placement"] != "entry":
                continue
            with self.subTest(function=row["signature"]):
                before, after = self.sources[row["path"]]
                original = function(before, row["signature"])
                changed = function(after, row["signature"])
                self.assertEqual(changed.replace(row["cast_lines"], "", 1), original)
                for param in row["parameters"]:
                    self.assertEqual(len(re.findall(r"\b" + re.escape(param) + r"\b", original)), 1)

    def test_all_other_source_returns_licenses_and_signatures_are_unchanged(self):
        for path, (before, after) in self.sources.items():
            restored = after
            for row in [row for row in CONTRACTS if row["path"] == path]:
                restored = restored.replace(function(restored, row["signature"]),
                                            function(before, row["signature"]), 1)
            self.assertEqual(restored, before)
            self.assertEqual(re.findall(r"\breturn[^;]*;", before), re.findall(r"\breturn[^;]*;", after))
            self.assertTrue(before.endswith("\n") and after.endswith("\n"))

    def test_version_macro_source_is_unchanged_and_not_hidden(self):
        before, after = self.sources["twrp-functions.cpp"]
        first = next(row["signature"] for row in CONTRACTS if row["path"] == "twrp-functions.cpp")
        self.assertEqual(before.split(first, 1)[0], after.split(first, 1)[0])
        self.assertIn("return std::string(TW_VERSION_STR);", after)
        self.assertIs(self.entry["scope"]["version_macro_changed"], False)

    def test_no_warning_policy_changes_or_optional_feature_enablement(self):
        added = "\n".join(line[1:] for line in self.patch.decode().splitlines()
                          if line.startswith("+") and not line.startswith("+++"))
        for forbidden in ("#define", "#undef", "#pragma", "-Wno", "-Werror", "ALLOW_MISSING", "BUILD_BROKEN",
                          "TW_INCLUDE", "TW_HAS_MTP", "QCOM_RTC_FIX", "setenforce", "Exec_Cmd", "return"):
            self.assertNotIn(forbidden, added)
        for key in ("warning_policy_changed", "features_enabled", "function_signatures_changed"):
            self.assertIs(self.entry["scope"][key], False)
        self.assertIn("crypto-enabled/FBE-disabled", " ".join(self.entry["limits"]))
        self.assertIn("not an Android compilation result", " ".join(self.entry["limits"]))

    def test_missing_extra_or_behavior_changing_edits_are_rejected(self):
        raw = self.patch
        mutations = {
            "mode": raw.replace(b" 100755\n", b" 100644\n", 1),
            "short_blob": raw.replace(FILES[0]["before_git_blob"].encode(), FILES[0]["before_git_blob"][:12].encode(), 1),
            "missing_parameter": raw.replace(b"+\t(void)signum;\n", b"", 1),
            "wrong_parameter": raw.replace(b"+\t(void)signum;", b"+\t(void)cookie;", 1),
            "extra_call": raw.replace(b"+\t(void)signum;", b"+\tsignum++;", 1),
            "warning_waiver": raw.replace(b"+\t(void)signum;", b'+#pragma clang diagnostic ignored "-Wunused-parameter"', 1),
            "return_success": raw.replace(b"+\t(void)signum;", b"+\treturn;", 1),
            "duplicate_cast": raw.replace(b"+\t(void)signum;\n", b"+\t(void)signum;\n+\t(void)signum;\n", 1),
            "enabled_branch": raw.replace(b"+#else\n", b"+#if 1\n", 1),
            "feature_enable": raw.replace(b"+#else\n", b"+#define TW_INCLUDE_CRYPTO\n", 1),
            "changed_return": raw.replace(b" return NOT_AVAILABLE;", b" return 0;", 1),
            "changed_version": raw.replace(b"std::string(TW_VERSION_STR)", b'std::string("test")', 1),
            "extra_file": raw + raw,
            "truncated": raw[:-1],
            "binary_trailer": raw + b"GIT binary patch\n",
        }
        # Match the unchanged four-space property fallback line exactly.
        mutations["changed_return"] = raw.replace(b"     return NOT_AVAILABLE;", b"     return 0;", 1)
        for name, changed in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)


if __name__ == "__main__":
    unittest.main()
