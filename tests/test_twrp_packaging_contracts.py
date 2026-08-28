"""Offline contract for the recovery packaging repairs observed by graph49.

These tests reconstruct all three public source files from full-context patch
hunks. They require only Python's standard library and the tracked controls;
they do not invoke a process, read ignored evidence, compile Android, or claim
that generated installation rules represent built ELF files.
"""
import hashlib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = '0026-repair-recovery-packaging-contracts'
PROJECT = 'bootable/recovery'
REVISION = 'b70f8e998b302381ecefc6e7f46df1614bd61afc'
SOURCE_SNAPSHOT = 'e967ec0392a3438f4706278e9e77b0810c4401a36f0e64c211a1e5c6e5bfb051'
BINDING = {'entry_file_sha256': 'c5e972a5f7f612908df07eb636ad9c71e069590362bf88abe4e5b64676cc5489', 'entry_sha256': '81cf96034c973a44908262b0636c98ca935072c4e2cdfe33bd1cb083119ee069', 'files': [{'after_git_blob': '8bf22f8d021465d425558be0b8e51f4a41cbb624', 'after_sha256': '5738f3924cd2e2cf023069892c61031ab749830e49a8f5f36005be3fa22a2dd2', 'after_size_bytes': 20673, 'before_git_blob': '87c1a57f513bdc1e1fcc7bca980886739c4ca047', 'before_sha256': '1049726f463a715bd9e3d4714599de9e2be7185dbec1ceb19d1bbf99d8bd2cbf', 'before_size_bytes': 20703, 'mode': '100644', 'path': 'Android.bp', 'predecessor_patch_id': '0020-restore-common-mdpi-recovery-resources', 'source_url': 'https://raw.githubusercontent.com/TWRP-Test/android_bootable_recovery/b70f8e998b302381ecefc6e7f46df1614bd61afc/Android.bp'}, {'after_git_blob': '15995f7ad81edb39e5087eb3f5960435dfd961e4', 'after_sha256': 'b36ce58dd712793c67985136a3d07fafc517d7525b06234e4128d87718c3874e', 'after_size_bytes': 38823, 'before_git_blob': '8a07a5f1ff3c5811e267ad04d6e7cdc7f2d53e89', 'before_sha256': '683d6256f3b5d17b6c03087b0ea27cd710911ebb1a91d1b357ada24e3bfd1cc7', 'before_size_bytes': 29919, 'mode': '100644', 'path': 'prebuilt/Android.mk', 'source_url': 'https://raw.githubusercontent.com/TWRP-Test/android_bootable_recovery/b70f8e998b302381ecefc6e7f46df1614bd61afc/prebuilt/Android.mk'}, {'after_git_blob': '91b876b692a3fa07756391b0eecb814beae4b987', 'after_sha256': '36b93ad83ae03432e2115f2120f1ca66378b079c5892c2ea9c4eb3f98bf2ae3b', 'after_size_bytes': 4612, 'before_git_blob': '59171146f8db58c09aadf54d541e8be8df2bdb04', 'before_sha256': '21cdc935ff21e7047fb6c9e2e5ba0dd6c6d882c31302fb5ccdcdab21ad767010', 'before_size_bytes': 332, 'mode': '100755', 'path': 'prebuilt/relink.sh', 'source_url': 'https://raw.githubusercontent.com/TWRP-Test/android_bootable_recovery/b70f8e998b302381ecefc6e7f46df1614bd61afc/prebuilt/relink.sh'}], 'old_metadata': 'bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22', 'old_queue_sha256': '21c092dcb3476be531223f25cce07128102ac834c782b26cf9a13a8e78ff5d71', 'old_twenty_five': '247dcc0acd1defecee6febd47a0f423fac4f9ecb022a483a51fe759846086b95', 'patch_sha256': '3ad173dccf01b9b45e6c6b8d8af02dfe360441fd12b5b2b0e77a6a3ac07b220c', 'source_generated_installs_sha256': 'dfd6436bde452fb1b41a00279f7bbf5c40067a6dc5b693d1954904735ecf34cf', 'source_generated_make_sha256': '391ec16fd405ef20fabbb9c6e2dac0df05a0061a873c1691fb4da773ae6319ba', 'source_graph_log_sha256': '103888c42bf7a9040921a8b602eab4461ed9099de15375285eb9e2e9ebf72b75'}
FILES = BINDING['files']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def reconstruct(raw):
    """Validate complete source identities independently of the payload digest."""
    if not isinstance(raw, bytes) or not raw.endswith(b'\n') or b'\0' in raw or b'\r' in raw:
        raise ValueError('Expected complete LF text')
    text = raw.decode()
    sections = re.split(r'(?m)(?=^diff --git )', text)
    if sections[0] != '' or len(sections) != 4:
        raise ValueError('Expected exactly three same-path file edits')
    result = {}
    for section, f in zip(sections[1:], FILES):
        lines = section.splitlines(keepends=True)
        expected = [f"diff --git a/{f['path']} b/{f['path']}\n",
                    f"index {f['before_git_blob']}..{f['after_git_blob']} {f['mode']}\n",
                    f"--- a/{f['path']}\n", f"+++ b/{f['path']}\n"]
        if lines[:4] != expected:
            raise ValueError('Wrong path, full Git index, or file mode')
        match = re.fullmatch(r'@@ -1,(\d+) \+1,(\d+) @@(?: [^\n]*)?\n', lines[4])
        if not match or any(line[:1] not in (' ', '+', '-') for line in lines[5:]):
            raise ValueError('Expected one complete ordinary hunk per file')
        stages = {}
        for stage, prefixes, count in [('before', (' ', '-'), int(match[1])),
                                        ('after', (' ', '+'), int(match[2]))]:
            selected = [line[1:] for line in lines[5:] if line.startswith(prefixes)]
            value = ''.join(selected).encode()
            blob = hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()
            if (len(selected) != count or len(value) != f[stage+'_size_bytes']
                    or digest(value) != f[stage+'_sha256'] or blob != f[stage+'_git_blob']):
                raise ValueError('Complete source identity changed')
            stages[stage] = value.decode()
        result[f['path']] = stages
    return result


class RecoveryPackagingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT/'patches/twrp/series.json').read_bytes())
        cls.rows = cls.series['patches']
        cls.entry = cls.rows[25]
        cls.raw = (ROOT/'patches/twrp'/f'{PATCH_ID}.patch').read_bytes()
        cls.sources = reconstruct(cls.raw)

    def test_previous_twenty_five_and_metadata_are_unchanged(self):
        self.assertGreaterEqual(len(self.rows), 26)
        self.assertEqual(canonical(self.rows[:25]), BINDING['old_twenty_five'])
        self.assertEqual(canonical({k:v for k,v in self.series.items() if k!='patches'}), BINDING['old_metadata'])
        for row in self.rows[:25]:
            self.assertEqual(digest((ROOT/row['patch']).read_bytes()), row['patch_sha256'])

    def test_exact_new_entry_payload_and_three_files(self):
        self.assertEqual(self.entry['id'], PATCH_ID)
        self.assertEqual(canonical(self.entry), BINDING['entry_sha256'])
        self.assertEqual(digest(self.raw), BINDING['patch_sha256'])
        self.assertEqual(self.entry['patch_sha256'], BINDING['patch_sha256'])
        self.assertEqual(self.entry['files'], FILES)
        self.assertEqual(list(self.sources), ['Android.bp','prebuilt/Android.mk','prebuilt/relink.sh'])

    def test_pinned_recovery_source_owner(self):
        source = (ROOT/'research/source-snapshots/twrp-16.0-linux-20260828.xml').read_bytes()
        self.assertEqual(digest(source), SOURCE_SNAPSHOT)
        projects=[p for p in ET.fromstring(source).iter('project') if p.get('path',p.get('name'))==PROJECT]
        self.assertEqual(len(projects),1)
        self.assertEqual(projects[0].get('revision'),REVISION)
        self.assertEqual((self.entry['project'],self.entry['base_commit']),(PROJECT,REVISION))

    def test_mdpi_predecessor_is_immediate_and_other_files_are_fresh(self):
        self.assertEqual(FILES[0]['predecessor_patch_id'],'0020-restore-common-mdpi-recovery-resources')
        prior=[r for r in self.rows[:25] if r['id']==FILES[0]['predecessor_patch_id']][0]
        for key in ('sha256','size_bytes','git_blob'):
            self.assertEqual(FILES[0]['before_'+key],prior['files'][0]['after_'+key])
        for f in FILES[1:]:
            self.assertNotIn('predecessor_patch_id',f)
            self.assertNotIn((PROJECT,f['path']),{(r['project'],old['path']) for r in self.rows[:25] for old in r['files']})

    def test_existing_usb_chain_and_safety_files_are_preserved(self):
        chains=[(r['id'],f['path'],f['predecessor_patch_id']) for r in self.rows[:26] for f in r['files'] if 'predecessor_patch_id' in f]
        self.assertEqual(chains,[('0024-recovery-usb-only-adb','daemon/main.cpp','0004-require-recovery-adb-auth'),
                                 (PATCH_ID,'Android.bp','0020-restore-common-mdpi-recovery-resources')])
        touched={(PROJECT,f['path']) for f in FILES}
        for row in self.rows[:25]:
            if row['id'].startswith(('0001-','0002-','0004-','0014-','0024-')):
                self.assertFalse(touched & {(row['project'],f['path']) for f in row['files']})

    def test_full_mdpi_module_bytes_are_retained(self):
        modules=[]
        for stage in ('before','after'):
            text=self.sources['Android.bp'][stage]
            found=re.findall(r'^prebuilt_res \{\n    name: "recovery-resources-common-mdpi",.*?^\}\n',text,re.M|re.S)
            self.assertEqual(len(found),1)
            self.assertEqual(digest(found[0].encode()),'30fb4bfd79ddc99c5d3c6463730cb80e91a1b9bffff7f927605f0ecc552cc216')
            modules.append(found[0])
        self.assertEqual(*modules)

    def test_root_blueprint_only_repairs_three_required_names(self):
        before=self.sources['Android.bp']['before']
        expected=before.replace('        "teamwin",\n','').replace('        "twrp",\n','')
        expected=expected.replace('            "event-log-tags"','            "twrp_event_log_tags"')
        self.assertEqual(self.sources['Android.bp']['after'],expected)
        self.assertIn('        "orscmd",',expected)

    def test_make_keeps_provider_names_separate_from_stems_and_symlinks(self):
        text=self.sources['prebuilt/Android.mk']['after']
        for module,stem in [('orscmd','twrp'),('ziptool.recovery','unzip'),('init_second_stage.recovery','ueventd'),('twrpbu','bu')]:
            self.assertIn('$(call twrp-register-binary,'+module+',$(TARGET_RECOVERY_ROOT_OUT)/system/bin/'+stem+')',text)
        self.assertIn('$(call twrp-register-library,libclang_rt.ubsan_standalone.recovery,',text)
        self.assertIn('RECOVERY_BINARY_REQUIRED_MODULES += android.hardware.health@2.1-service.recovery',text)
        self.assertNotIn('LOCAL_MODULE := teamwin',text)

    def test_generated_event_tags_have_an_actual_etc_prebuilt(self):
        text=self.sources['prebuilt/Android.mk']['after']
        expected=('LOCAL_MODULE := twrp_event_log_tags\nLOCAL_MODULE_TAGS := optional\nLOCAL_MODULE_CLASS := ETC\n')
        self.assertIn(expected,text)
        self.assertIn('LOCAL_MODULE_STEM := event-log-tags',text)
        self.assertIn('LOCAL_PREBUILT_MODULE_FILE := $(TARGET_OUT)/etc/event-log-tags',text)
        self.assertIn('LOCAL_MODULE_PATH := $(TARGET_RECOVERY_ROOT_OUT)/system/etc',text)
        self.assertIn('include $(BUILD_PREBUILT)',text[text.index('LOCAL_MODULE := twrp_event_log_tags'):])

    def test_system_ext_paths_follow_make_output_variables(self):
        text=self.sources['prebuilt/Android.mk']['after']
        self.assertIn('$(call twrp-register-binary,bash,$(TARGET_OUT_SYSTEM_EXT_EXECUTABLES)/bash)',text)
        self.assertIn('$(call twrp-register-library,libncurses,$(TARGET_OUT_SYSTEM_EXT_SHARED_LIBRARIES)/libncurses.so)',text)
        self.assertNotIn('out-twrp/target/product/nezha/',text)

    def test_required_inputs_and_copy_failures_cannot_be_silently_ignored(self):
        text=self.sources['prebuilt/relink.sh']['after']
        self.assertIn('set -euo pipefail',text)
        self.assertIn('die "required input is missing or not a file: $src"',text)
        self.assertIn('die "conflicting required inputs for ${src##*/}: $src and $other"',text)
        self.assertIn('cp -pP -- "$src" "$work_dir/file"',text)
        self.assertIn('mv -f -- "$work_dir/file" "$dst"',text)
        self.assertNotIn('|| true',text)
        self.assertNotIn('2>/dev/null',text)

    def test_native_files_and_symlink_safety_remain_checked(self):
        text=self.sources['prebuilt/relink.sh']['after']
        for token in ['symlink escapes recovery','symlink cycle or excessive chain','destination directory is a symlink',
                      'destination contains a parent traversal','refusing to replace a destination symlink',
                      'verify_staged_file "$dest/${src##*/}"']:
            self.assertIn(token,text)
        self.assertIn('if [[ $src == "$dest_arg/$name" || $src == "$dst" ]]',text)
        self.assertEqual(FILES[2]['mode'],'100755')

    def test_structural_and_source_mutations_fail_without_payload_hash_gate(self):
        raw=self.raw
        mutations={
            'path':raw.replace(b'a/prebuilt/relink.sh',b'a/prebuilt/other.sh',1),
            'mode':raw.replace(b'100755\n',b'100644\n',1),
            'blob':raw.replace(FILES[0]['before_git_blob'].encode(),b'0'*40,1),
            'partial_hunk':raw.replace(b'@@ -1,',b'@@ -2,',1),
            'source_module':raw.replace(b' name: "recovery-resources-common-mdpi",',b' name: "recovery-resources-common-hdpi",',1),
            'provider':raw.replace(b'+$(eval $(call twrp-register-binary,orscmd,',b'+$(eval $(call twrp-register-binary,twrp,',1),
            'copy_failure':raw.replace(b'+set -euo pipefail',b'+set +e',1),
            'copy_mode':raw.replace(b'+    cp -pP --',b'+    cp -pL --',1),
            'missing_failure':raw.replace(b'+    [[ -f $src || -L $src ]] || die',b'+    [[ -f $src || -L $src ]] || true #',1),
            'extra_path':raw+b'diff --git a/extra b/extra\n',
            'truncated':raw[:-1], 'nul':raw+b'\0\n', 'crlf':raw.replace(b'\n',b'\r\n'),
        }
        for label,value in mutations.items():
            with self.subTest(mutation=label):
                self.assertNotEqual(value,raw)
                with self.assertRaises((ValueError,IndexError)):
                    reconstruct(value)


if __name__ == '__main__':
    unittest.main()
