"""Offline safety and format tests; no phone, mounted image or installed tool."""

import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

from scripts import apex_inputs as apex
from scripts import erofs_inventory


def varint(number):
    result = bytearray()
    while number > 127:
        result.append((number & 127) | 128)
        number >>= 7
    return bytes(result + bytes([number]))


def string_field(number, text):
    data = text.encode()
    return varint(number * 8 + 2) + varint(len(data)) + data


def manifest(name='com.example.vendor', version=1):
    return string_field(1, name) + b'\x10' + varint(version)


def zip_bytes(extra=(), *, payload=b'payload', manifest_bytes=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, content in [('apex_payload.img', payload), ('apex_manifest.pb', manifest_bytes or manifest()),
                              ('apex_pubkey', b'public-key'), ('AndroidManifest.xml', b'opaque-axml'), *extra]:
            archive.writestr(name, content)
    return output.getvalue()


def elf_fixture(bits=64, endian='<'):
    header_size, phsize, dynsize = (64, 56, 16) if bits == 64 else (52, 32, 8)
    data = bytearray(512)
    data[:16] = b'\x7fELF' + bytes([2 if bits == 64 else 1, 1 if endian == '<' else 2, 1]) + bytes(9)
    struct.pack_into(endian + ('HHIQQQIHHHHHH' if bits == 64 else 'HHIIIIIHHHHHH'), data, 16,
                     3, 183 if bits == 64 else 40, 1, 0, header_size, 0, 0,
                     header_size, phsize, 2, 0, 0, 0)
    if bits == 64:
        struct.pack_into(endian + 'IIQQQQQQ', data, header_size, 1, 4, 0, 0x1000, 0, 512, 512, 4096)
        struct.pack_into(endian + 'IIQQQQQQ', data, header_size + phsize, 2, 4, 192, 0x10c0, 0, 6 * dynsize, 6 * dynsize, 8)
    else:
        struct.pack_into(endian + 'IIIIIIII', data, header_size, 1, 0, 0x1000, 0, 512, 512, 4, 4096)
        struct.pack_into(endian + 'IIIIIIII', data, header_size + phsize, 2, 192, 0x10c0, 0, 6 * dynsize, 6 * dynsize, 4, 4)
    strings = b'\0libc.so\0libvendor.so\0$ORIGIN/../lib64\0'
    data[320:320 + len(strings)] = strings
    dynamic = [(5, 0x1140), (10, len(strings)), (1, 1), (14, 9), (29, 22), (0, 0)]
    for index, item in enumerate(dynamic):
        struct.pack_into(endian + ('qQ' if bits == 64 else 'iI'), data, 192 + index * dynsize, *item)
    return bytes(data)


class ManifestTests(unittest.TestCase):
    def test_records_exact_fields_and_repeated_order(self):
        data = manifest() + string_field(8, 'libz.so') + string_field(8, 'liba.so') + b'\x30\x00'
        result = apex.parse_manifest(data)
        self.assertEqual(result['declared_fields'], {'name': 'com.example.vendor', 'version': 1,
                                                    'requireNativeLibs': ['libz.so', 'liba.so'], 'noCode': False})
        self.assertNotIn('bootstrap', result['declared_fields'])

    def test_unknown_fields_preserved_without_interpretation(self):
        result = apex.parse_manifest(manifest() + b'\xf0\x01\x02' + b'\xf9\x01abcdefgh')
        self.assertEqual(result['unknown_fields'], [{'number': 30, 'wire': 0, 'value': 2},
                                                   {'number': 31, 'wire': 1, 'value': b'abcdefgh'.hex()}])

    def test_rejects_malformed_or_ambiguous_manifests(self):
        values = [b'', manifest() + b'\x80', manifest() + b'\x80' * 11,
                  manifest() + b'\xf0\x01' + b'\xff' * 9 + b'\x02',
                  manifest() + string_field(1, 'com.other'), manifest() + b'\x10\x01',
                  manifest() + b'\x0b', manifest() + b'\x00', manifest() + b'\x30\x02',
                  manifest() + b'\x32\x01a', manifest() + b'\x42\xff\x7f',
                  manifest('../escape'), manifest('no-dot'), manifest(version=0),
                  string_field(1, 'com.example'), manifest(version=2**63),
                  manifest() + string_field(8, 'lib\0.so')]
        for value in values:
            with self.subTest(value=value), self.assertRaises((apex.ApexError, UnicodeError)):
                apex.parse_manifest(value)


class Ext4ParserTests(unittest.TestCase):
    def listing(self, extra=''):
        return '/2/040755/0/0/.//\n/2/040755/0/0/..//\n' + extra

    def test_regular_directory_and_symlink_are_distinguished(self):
        result = apex.parse_ext4_listing(self.listing('/12/100644/0/0/manifest.xml/42/\n'
                                                      '/13/040755/0/0/etc//\n'
                                                      '/14/120777/0/0/alias/5/\n'), inode=2, parent=2)
        self.assertEqual([x['type'] for x in result], ['regular', 'directory', 'symlink'])
        self.assertEqual(result[0]['size_bytes'], 42)

    def test_debugfs_terminal_blank_line_is_accepted_but_not_interior_blank(self):
        self.assertEqual(apex.parse_ext4_listing(self.listing() + '\n', inode=2, parent=2), [])
        with self.assertRaises(apex.ApexError):
            apex.parse_ext4_listing(self.listing() + '\n\n', inode=2, parent=2)

    def test_exact_unused_directory_slots_are_ignored_without_following_them(self):
        self.assertEqual(apex.parse_ext4_listing(self.listing('/0/000000/0/0//0/\n' * 3) + '\n', inode=2, parent=2), [])
        for record in ('/0/000000/0/0/named/0/\n', '/0/100644/0/0//0/\n', '/0/000000/0/0//1/\n'):
            with self.subTest(record=record), self.assertRaises(apex.ApexError):
                apex.parse_ext4_listing(self.listing(record), inode=2, parent=2)

    def test_rejects_bad_directory_records(self):
        values = [self.listing('/12/100644/0/0/bad name/42/\n'), self.listing('/12/100644/0/0/file//\n'),
                  self.listing('/12/020644/0/0/device/42/\n'), self.listing('/0/100644/0/0/file/42/\n'),
                  self.listing('/12/100644/0/0/file/42/\n/13/100644/0/0/file/42/\n'),
                  self.listing().replace('/2/040755/0/0/..', '/3/040755/0/0/..'),
                  '/2/040755/0/0/.//\n', self.listing() + 'unexpected output\n']
        for value in values:
            with self.subTest(value=value), self.assertRaises(apex.ApexError):
                apex.parse_ext4_listing(value, inode=2, parent=2)

    def test_rechecks_regular_file_inode_metadata(self):
        expected = {'inode': 12, 'mode': '100644', 'uid': 0, 'gid': 0, 'size_bytes': 42}
        text = 'Inode: 12   Type: regular    Mode:  0644   Flags: 0x80000\nUser: 0   Group: 0   Size: 42\n'
        apex.parse_ext4_stat(text, expected)
        for old, new in [('Inode: 12', 'Inode: 13'), ('regular', 'symlink'), ('0644', '0755'),
                         ('User: 0', 'User: 1'), ('Size: 42', 'Size: 41')]:
            with self.subTest(old=old), self.assertRaises(apex.ApexError):
                apex.parse_ext4_stat(text.replace(old, new), expected)


class ElfTests(unittest.TestCase):
    def test_extracts_32_and_64_bit_dependencies_in_both_byte_orders(self):
        for bits in (32, 64):
            for endian in ('<', '>'):
                with self.subTest(bits=bits, endian=endian):
                    result = apex.elf_dynamic(elf_fixture(bits, endian))
                    self.assertEqual(result['class_bits'], bits)
                    self.assertEqual(result['needed'], ['libc.so'])
                    self.assertEqual(result['soname'], 'libvendor.so')
                    self.assertEqual(result['search_paths'], [{'tag': 29, 'value': '$ORIGIN/../lib64'}])

    def test_non_elf_is_not_executed_or_parsed(self):
        self.assertIsNone(apex.elf_dynamic(b'#!/bin/sh\nanything'))

    def test_rejects_truncated_elf(self):
        for size in (4, 15, 63, 120, 200, 400):
            with self.subTest(size=size), self.assertRaises(apex.ApexError):
                apex.elf_dynamic(elf_fixture()[:size])

    def test_rejects_bad_string_table_and_dynamic_offsets(self):
        for offset, value in [(192 + 8, 0xfffffff), (208 + 8, 999999), (224 + 8, 2000)]:
            data = bytearray(elf_fixture())
            struct.pack_into('<Q', data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(apex.ApexError):
                apex.elf_dynamic(bytes(data))


class StaticDependencyTests(unittest.TestCase):
    def test_xml_preserves_omitted_version_and_does_not_claim_effective_merge(self):
        data = b'<manifest version="9.0" type="device"><hal format="aidl"><name>android.hardware.cas</name><fqname>IMediaCasService/default</fqname></hal></manifest>'
        result = apex.vintf_declarations(data)
        self.assertEqual(result['hals'][0]['declared_versions'], [])
        self.assertEqual(result['hals'][0]['fqnames'], ['IMediaCasService/default'])
        self.assertFalse(result['effective_manifest_verified'])

    def test_xml_dtd_and_entity_declarations_are_refused(self):
        for data in (b'<!DOCTYPE a><manifest type="device"/>', b'<!ENTITY a "b"><manifest type="device"/>',
                     b'<manifest/>', b'<compatibility-matrix type="framework"/>'):
            with self.subTest(data=data), self.assertRaises(apex.ApexError):
                apex.vintf_declarations(data)

    def test_init_records_missing_executable_without_running_or_repairing_it(self):
        data = b'on property:apex.all.ready=true\n    mkdir /data/vendor/example\nservice vendor.example /apex/com.example/bin/server\n    user media\nservice vendor.other /apex/com.example/bin/missing\n    disabled\n'
        result = apex.init_declarations(data, 'com.example', {'/bin/server'})
        self.assertEqual([s['executable_present_as_regular'] for s in result['services']], [True, False])
        self.assertEqual(result['observed_action_triggers'], ['property:apex.all.ready=true'])
        self.assertFalse(result['executed'])


class ApexWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.patch = mock.patch.object(erofs_inventory, 'WORKSPACE_ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.base = self.root / 'artifacts'
        self.base.mkdir()
        self.capture = self.base / 'capture'
        self.capture.mkdir()
        (self.capture / 'files').mkdir()
        self.tool = self.root / 'debugfs'
        self.tool.write_bytes(b'fixture tool; never executed')
        self.tool.chmod(0o700)
        self.tool_hash = hashlib.sha256(self.tool.read_bytes()).hexdigest()

    def setup_capture(self, data=None):
        data = zip_bytes() if data is None else data
        (self.capture / 'files/0001').write_bytes(data)
        receipt = {'schema_version': 1, 'operation': 'erofs-capture', 'image_mounted': False, 'firmware_executed': False,
                   'symlinks_followed': False, 'origin_verified': False,
                   'image': {'sha256': 'a' * 64, 'size_bytes': 1024},
                   'files': [{'path': '/apex/com.example.apex', 'output_path': 'files/0001',
                              'type': 'regular', 'sha256': hashlib.sha256(data).hexdigest(),
                              'size_bytes': len(data), 'readback_verified': True}]}
        path = self.capture / 'receipt.json'
        path.write_text(json.dumps(receipt))
        return {'capture_receipt': path, 'expected_receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'source_path': '/apex/com.example.apex', 'package_sha256': 'b' * 64,
                'output_dir': self.base / 'result', 'debugfs': self.tool,
                'expected_debugfs_sha256': self.tool_hash, 'zip_only': True}

    def test_zip_capture_is_flat_hashed_and_does_not_upgrade_trust(self):
        args = self.setup_capture(zip_bytes(extra=[('etc/not/a/real/path', b'inert')]))
        with mock.patch.object(apex.subprocess, 'Popen') as process:
            result = apex.inspect_apex(**args)
        process.assert_not_called()
        self.assertEqual(result['status'], 'zip-only')
        self.assertEqual(len(result['zip_members']), 5)
        self.assertFalse((self.base / 'result/etc').exists())
        for field in ('origin_verified', 'signature_authenticated', 'payload_avb_verified', 'active_state_verified',
                      'image_mounted', 'package_activated', 'firmware_executed', 'compatibility_verified'):
            self.assertIs(result[field], False)
        for item in result['zip_members']:
            self.assertTrue(item['crc_verified'])
            self.assertTrue(item['readback_verified'])
            self.assertEqual(hashlib.sha256((args['output_dir'] / item['output_path']).read_bytes()).hexdigest(), item['sha256'])

    def test_existing_outputs_are_not_replaced(self):
        args = self.setup_capture()
        args['output_dir'].mkdir()
        sentinel = args['output_dir'] / 'keep'
        sentinel.write_text('untouched')
        with self.assertRaises(ValueError):
            apex.inspect_apex(**args)
        self.assertEqual(sentinel.read_text(), 'untouched')

    def test_failed_inspection_preserves_its_receipt(self):
        args = self.setup_capture(zip_bytes(manifest_bytes=manifest('bad/name')))
        with self.assertRaises(apex.ApexError):
            apex.inspect_apex(**args)
        receipt = json.loads((args['output_dir'] / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'failed')
        self.assertIn('unsafe APEX module name', receipt['error'])
        self.assertTrue((args['output_dir'] / 'zip/0000').exists())

    def test_output_cannot_be_public_or_a_symlink(self):
        args = self.setup_capture()
        args['output_dir'] = self.root / 'public-output'
        with self.assertRaises(ValueError):
            apex.inspect_apex(**args)
        args['output_dir'] = self.base / 'alias'
        args['output_dir'].symlink_to(self.capture, target_is_directory=True)
        with self.assertRaises(ValueError):
            apex.inspect_apex(**args)

    def test_receipt_and_input_and_tool_hashes_are_required(self):
        for option in ('expected_receipt_sha256', 'expected_debugfs_sha256'):
            args = self.setup_capture()
            args[option] = 'c' * 64
            with self.subTest(option=option), self.assertRaises(ValueError):
                apex.inspect_apex(**args)
        args = self.setup_capture()
        (self.capture / 'files/0001').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            apex.inspect_apex(**args)

    def test_unsafe_zip_paths_special_files_and_duplicates_are_refused(self):
        symlink = zipfile.ZipInfo('link')
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        directory = zipfile.ZipInfo('directory/')
        for index, entry in enumerate([('../escape', b'x'), ('/absolute', b'x'), ('a//b', b'x'),
                                       ('a\\b', b'x'), (symlink, b'target'), (directory, b''),
                                       ('apex_pubkey', b'duplicate')]):
            with self.subTest(entry=entry):
                with warnings.catch_warnings(record=True) as emitted:
                    warnings.simplefilter('always')
                    args = self.setup_capture(zip_bytes(extra=[entry]))
                if entry[0] == 'apex_pubkey':
                    self.assertEqual(len(emitted), 1)
                    self.assertIn('Duplicate name', str(emitted[0].message))
                else:
                    self.assertFalse(emitted)
                args['output_dir'] = self.base / f'bad-{index}'
                with self.assertRaises(apex.ApexError):
                    apex.inspect_apex(**args)

    def test_zip_crc_failure_is_not_ignored(self):
        data = bytearray(zip_bytes())
        location = data.index(b'payload')
        # The first match is in the filename; change actual stored member data.
        location = data.index(b'payload', location + 7)
        data[location] ^= 1
        args = self.setup_capture(bytes(data))
        with self.assertRaises(zipfile.BadZipFile):
            apex.inspect_apex(**args)
        self.assertEqual(json.loads((args['output_dir'] / 'receipt.json').read_text())['status'], 'failed')

    def test_zip_size_limit_is_enforced(self):
        args = self.setup_capture()
        with mock.patch.object(apex, 'MAX_FILE_BYTES', 2), self.assertRaises(apex.ApexError):
            apex.inspect_apex(**args)

    def test_capture_symlink_is_rejected(self):
        args = self.setup_capture()
        source = self.capture / 'files/0001'
        renamed = self.capture / 'files/real'
        source.rename(renamed)
        source.symlink_to(renamed)
        with self.assertRaises(ValueError):
            apex.inspect_apex(**args)

    def test_debugfs_command_language_is_restricted_before_process_creation(self):
        with mock.patch.object(apex.subprocess, 'Popen') as process:
            for command in ('cat /etc/passwd', 'write file /bad', 'ls -p <2>; quit', 'cat <0>',
                            'cat <12>\nwrite bad', '-w', 'rdump / output', 'cat <-1>'):
                with self.subTest(command=command), self.assertRaises(apex.ApexError):
                    apex._run_debugfs({}, {}, command, self.base, [])
        process.assert_not_called()

    def test_debugfs_uses_read_only_descriptor_and_preserves_logs(self):
        output = self.base / 'commands-output'
        output.mkdir()
        (output / 'commands').mkdir()
        image_path = self.base / 'image'
        image_path.write_bytes(b'fixture image')
        processes = []

        def process(argv, **kwargs):
            reader, writer = os.pipe()
            os.write(writer, b'listing\n')
            os.close(writer)
            err_reader, err_writer = os.pipe()
            os.write(err_writer, (apex.DEBUGFS_VERSION + '\n').encode())
            os.close(err_writer)
            child = mock.Mock(stdout=os.fdopen(reader, 'rb'), stderr=os.fdopen(err_reader, 'rb'))
            child.wait.return_value = 0
            child.poll.return_value = 0
            processes.append((argv, kwargs))
            return child

        commands = []
        with apex._checked_file(self.tool) as tool, apex._checked_file(image_path) as image:
            with mock.patch.object(apex.subprocess, 'Popen', side_effect=process):
                result = apex._run_debugfs(tool, image, 'ls -p <2>', output, commands)
            self.assertEqual(processes[0][0], [str(self.tool), '-R', 'ls -p <2>', f"/dev/fd/{image['stream'].fileno()}"])
            self.assertEqual(processes[0][1]['pass_fds'], (image['stream'].fileno(),))
            self.assertNotIn('shell', processes[0][1])
        self.assertEqual(result.read_bytes(), b'listing\n')
        self.assertEqual(commands[0]['exit_code'], 0)
        self.assertTrue(commands[0]['stderr']['readback_verified'])

    def test_debugfs_diagnostics_fail_even_when_process_returns_zero(self):
        output = self.base / 'diagnostics-output'
        output.mkdir()
        (output / 'commands').mkdir()
        image_path = self.base / 'image'
        image_path.write_bytes(b'fixture image')

        def process(*args, **kwargs):
            pipes = []
            for data in (b'', (apex.DEBUGFS_VERSION + '\nchecksum failed\n').encode()):
                reader, writer = os.pipe()
                os.write(writer, data)
                os.close(writer)
                pipes.append(os.fdopen(reader, 'rb'))
            child = mock.Mock(stdout=pipes[0], stderr=pipes[1])
            child.wait.return_value = 0
            child.poll.return_value = 0
            return child

        commands = []
        with apex._checked_file(self.tool) as tool, apex._checked_file(image_path) as image:
            with mock.patch.object(apex.subprocess, 'Popen', side_effect=process), self.assertRaises(apex.ApexError):
                apex._run_debugfs(tool, image, 'stats', output, commands)
        self.assertIn(b'checksum failed', (output / commands[0]['stderr']['output_path']).read_bytes())
        self.assertEqual(commands[0]['exit_code'], 0)

    def test_ext4_symlinks_are_inventoried_but_never_read(self):
        image_path = self.base / 'ext4-image'
        image_path.write_bytes(bytes(1080) + b'\x53\xef')
        output = self.base / 'ext4-output'
        output.mkdir()
        calls = []

        def call(tool, image, request, out, commands, **kwargs):
            calls.append(request)
            data = {'stats': b'filesystem metadata',
                    'ls -p <2>': b'/2/040755/0/0/.//\n/2/040755/0/0/..//\n/12/120777/0/0/link/20/\n\n'}[request]
            p = output / f'{len(calls)}.stdout'
            p.write_bytes(data)
            return p

        with apex._checked_file(image_path) as image, mock.patch.object(apex, '_run_debugfs', side_effect=call):
            result = apex.inspect_ext4(image, {}, output, [])
        self.assertEqual(calls, ['stats', 'ls -p <2>'])
        self.assertEqual(result['inventory'][0]['type'], 'symlink')
        self.assertEqual(result['files'], [])

    def test_ext4_directory_cycles_are_refused(self):
        image_path = self.base / 'ext4-image'
        image_path.write_bytes(bytes(1080) + b'\x53\xef')
        output = self.base / 'cycle-output'
        output.mkdir()
        listing = output / 'fixture'
        listing.write_text('/2/040755/0/0/.//\n/2/040755/0/0/..//\n/2/040755/0/0/cycle//\n\n')
        with apex._checked_file(image_path) as image, mock.patch.object(apex, '_run_debugfs', return_value=listing):
            with self.assertRaisesRegex(apex.ApexError, 'cycle or alias'):
                apex.inspect_ext4(image, {}, output, [])


class PublicRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.record = json.loads((cls.root / 'research/apex-dependencies.json').read_text())

    def test_exact_three_packages_and_two_vintf_contributions(self):
        modules = self.record['modules']
        self.assertEqual([m['module_name'] for m in modules],
                         ['com.android.hardware.cas', 'com.google.android.widevine', 'com.xiaomi.wifi'])
        self.assertEqual([m['regular_files'] for m in modules], [4, 10, 2])
        self.assertEqual([m['elf_files'] for m in modules], [1, 7, 0])
        self.assertEqual([len(m['vintf']) for m in modules], [1, 1, 0])
        self.assertNotIn('nonupdatable', modules[1]['vintf'][0]['runtime_path'])
        self.assertTrue(all(not f['hals'][0]['declared_versions'] for m in modules for f in m['vintf']))

    def test_stock_matches_do_not_hide_denials_or_become_evolution_proof(self):
        observed = self.record['stock_observations']
        self.assertEqual(observed['active_total_entries'], 39)
        self.assertEqual(observed['active_vendor_count'], 3)
        self.assertEqual(observed['active_odm_count'], 0)
        self.assertEqual(len(observed['matched']), 5)
        self.assertEqual(len(observed['unavailable']), 3)
        self.assertFalse(observed['raw_all_matched_value'])
        self.assertTrue(all(x['transport_status'] == 'ok' and x['payload_read_status'] == 'unavailable'
                            for x in observed['unavailable']))
        limits = self.record['validation_boundaries']
        for field in ('apex_payload_avb_verification_attempted', 'apex_container_signature_verification_attempted',
                      'evolution_activation_verified', 'oem_origin_authenticated', 'feature_behavior_verified',
                      'effective_vintf_compatibility_established_by_this_record', 'elf_dependency_closure_verified'):
            self.assertIs(limits[field], False)

    def test_actual_inspection_and_independent_counts_agree(self):
        inspection = self.record['inspection']
        self.assertEqual(inspection['zip_entries_crc_verified'], 29)
        self.assertEqual(inspection['debugfs_commands_passed'], 51)
        self.assertEqual(inspection['captured_regular_files'], 16)
        self.assertEqual(inspection['captured_regular_bytes'], 5656378)
        self.assertEqual(self.record['independent_elf_check']['files_verified'], 10)
        self.assertEqual(sum(m['captured_regular_bytes'] for m in self.record['modules']), inspection['captured_regular_bytes'])
        self.assertEqual(sum(m['package_bytes'] for m in self.record['modules']), 6348800)

    def test_requirements_and_missing_service_are_not_silently_repaired(self):
        cas, widevine, wifi = self.record['modules']
        self.assertIn(':mediacas', cas['required_native_libs_declared_order'])
        self.assertIn('liboemcrypto.so', widevine['required_native_libs_declared_order'])
        self.assertEqual([s['executable_present_as_regular'] for s in widevine['init_services']], [True, False])
        self.assertTrue(widevine['init_services'][1]['executable'].endswith('-rikers'))
        self.assertEqual(wifi['wifi_compat']['declared_os_versions_count'], 0)
        self.assertFalse(wifi['wifi_compat']['runtime_semantics_verified'])

    def test_provenance_and_documentation_remain_explicit(self):
        self.assertFalse(self.record['provenance']['origin_verified'])
        self.assertIsNone(self.record['provenance']['source_url'])
        self.assertTrue(self.record['provenance']['raw_proprietary_files_git_ignored'])
        doc = (self.root / 'docs/apex-dependencies.md').read_text()
        for text in ('all_matched=false', 'permission-denied', 'without activation', 'not proof', 'new'):
            self.assertIn(text, doc)


if __name__ == '__main__':
    unittest.main()
