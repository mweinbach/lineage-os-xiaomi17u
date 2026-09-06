"""Synthetic reconciliation failures, never real cryptographic or ROM evidence.

Reuse the maintained inert image/signing fixture with every native invocation
mocked. It prohibits shell, sockets, and native execution and opening its fake
private key. Reconciliation additionally forbids even stat'ing that key and
loading local signing configuration. ZIP streaming and receipt joins are real.
"""
from contextlib import contextmanager, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

from scripts import reconcile_signed_target_files as subject
from tests import test_avb_signing as fixtures

identity = fixtures.fixture.identity


def fixture_digest(images):
    """Binary fixture decoder independent of adapter's descriptor parser."""
    root = fixtures.metadata_blob(images['vbmeta'])
    children = []
    for descriptor in fixtures.raw_descriptors(images['vbmeta']):
        if struct.unpack_from('>Q', descriptor)[0] != 4:
            continue
        length = struct.unpack_from('>I', descriptor, 20)[0]
        children.append(descriptor[92:92 + length].decode())
    digest = hashlib.sha256(root)
    for role in children:
        digest.update(fixtures.metadata_blob(images[role]))
    return digest.hexdigest().encode() + b'\n'


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.SigningTests('test_plan_reads_no_local_configuration_images_keys_or_native_tools')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        # The ordinary DTBO producer carries its build fingerprint. Keep its
        # original payload/hash descriptor while making that real layout part
        # of the existing end-to-end signing/reconciliation fixture.
        dtbo = fixtures.fixture.with_footer(self.f.fx.payloads['dtbo'], fixtures.fixture.vbmeta([
            self.f.fx.descriptors['dtbo'], fixtures.fixture.property_descriptor(
                b'com.android.build.dtbo.fingerprint', b'canonical-fixture-fingerprint')]))
        self.f.fx.write_image('dtbo', dtbo)
        self.f.input['images']['dtbo'] = deepcopy(self.f.fx.manifest['images']['dtbo'])
        self.root = self.f.root
        self.prepared = self.f.prepare()
        self.signed = self.f.sign(self.prepared)
        self.f.calls.clear()
        self.f.forbid_private_stat = True
        self.enterContext(mock.patch.object(subject.signing, '_local', side_effect=AssertionError('local config forbidden')))
        self.enterContext(mock.patch.object(subject.signing, '_key_state', side_effect=AssertionError('private key stat forbidden')))
        self.enterContext(mock.patch.object(subject, 'controls', side_effect=self.f.contract_state))
        self.enterContext(mock.patch.object(subject, 'PUBLIC_PINS', {}))
        self.f.runner.side_effect = self.native
        self.fail_digest = self.malformed_digest = self.mismatch_digest = False
        self.archive = self.root / 'actual-only-inert-fixture.zip'
        self.retained = self.root / 'retained.json'
        provenance = self.f.fx.root / 'provenance.json'
        record = {'path': str(provenance), **identity(provenance.read_bytes())}
        self.retained_value = {
            'schema_version': 1, 'contract_id': subject.signing.CONTRACT_ID,
            'contract_sha256': self.f.contract_sha, 'artifact_set_id': 'synthetic-retained-inputs',
            'images': {name: {'path': str(self.f.fx.root / row['path']), **subject.selected(row)}
                       for name, row in self.f.input['images'].items() if name in subject.RAW_ROLES},
            'source_records': [record]}
        self.retained.write_bytes(subject.encoded(self.retained_value))
        self.enterContext(mock.patch.object(subject.inventory, '_factory_record', return_value=subject.selected(record)))
        dynamic = ' '.join(sorted(subject.avb.LOGICAL))
        self.members = {'IMAGES/' + name + '.img': raw for name, raw in self.f.fx.images.items()
                        if name not in subject.RAW_ROLES}
        self.members.update({
            'META/misc_info.txt': ('ab_update=true\navb_enable=true\navb_building_vbmeta_image=true\n'
                'use_dynamic_partitions=true\ndynamic_partition_list=' + dynamic + '\n'
                'avb_vbmeta_key_path=original-private-signing-recipe-not-opened\n'
                'avb_vbmeta_rollback_index=0\n').encode(),
            'META/dynamic_partitions_info.txt': ('use_dynamic_partitions=true\ndynamic_partition_list=' + dynamic + '\n').encode(),
            'META/ab_partitions.txt': ('\n'.join(sorted(subject.avb.PARTITIONS - subject.RAW_ROLES)) + '\n').encode(),
            'META/vbmeta_digest.txt': fixture_digest(self.f.fx.images),
            'META/apkcerts.txt': b'INERT original OEM APK signing metadata\n',
            'META/apexkeys.txt': b'INERT original APEX signing metadata\n',
            'META/care_map.pb': b'\x01\x00\xffopaque original care map\n',
            'SYSTEM/priv-app/Camera/Camera.apk': b'INERT NOT A REAL APK\0\xff',
            'SYSTEM/bin/sh': b'toybox',
            'SYSTEM/bin/empty': b'',
        })
        self.inventory_path = self.root / 'inventory.json'
        self.request_path = self.root / 'request.json'
        self.output = self.f.output('reconciled')
        self.refresh_archive()

    def native(self, label, args, env, work, records, **kwargs):
        if label != 'calculate-vbmeta-digest':
            return self.f.native_step(label, args, env, work, records, **kwargs)
        self.f.calls.append((label, list(args), work))
        self.assertNotIn('--key', args)
        self.assertNotIn('--follow_chain_partitions', args)
        self.assertNotIn('--accept_zeroed_hashtree', args)
        self.assertEqual('sha256', args[args.index('--hash_algorithm') + 1])
        self.assertEqual('hex', args[args.index('--format') + 1])
        if self.fail_digest:
            raise ValueError('mock digest execution failed')
        root = Path(args[args.index('--image') + 1]).parent
        raw = fixture_digest({role: (root / (role + '.img')).read_bytes() for role in subject.avb.SIGNED})
        if self.malformed_digest:
            raw = raw.rstrip(b'\n')
        if self.mismatch_digest:
            raw = b'0' * 64 + b'\n'
        destination = Path(args[args.index('--output') + 1])
        subject.write_new(destination, raw)
        record = {'step': label, 'returncode': 0, 'stdout': identity(b''), 'stderr': identity(b'')}
        records.append(record)
        subject.signing.io._save(work / f'native-{len(records):02d}-{label}.json', record)

    def refresh_archive(self, compression=zipfile.ZIP_STORED):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.comment = b'ORIGINAL INERT ARCHIVE COMMENT\x00'
            for name, raw in self.members.items():
                member = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                member.create_system = 3
                mode = stat.S_IFLNK | 0o777 if name == 'SYSTEM/bin/sh' else stat.S_IFREG | 0o644
                member.external_attr = mode << 16
                member.compress_type = compression
                member.comment = b'original member comment'
                archive.writestr(member, raw)
        pin = identity(self.archive.read_bytes())
        self.inventory_value = subject.inventory.inspect_target_files(self.archive, pin,
            retained_input_manifest=self.retained,
            expected_retained_manifest_sha256=identity(self.retained.read_bytes())['sha256'])
        self.inventory_path.write_bytes(subject.encoded(self.inventory_value))
        paths = {'target_files': self.archive, 'inventory': self.inventory_path,
                 'retained_input_manifest': self.retained,
                 'signing_preparation': self.prepared[0] / 'preparation.json',
                 'signing_receipt': self.signed[0] / 'signing-receipt.json',
                 'verification_manifest': self.signed[0] / 'verification-manifest.json'}
        self.request = {'schema_version': 1, 'operation': subject.OPERATION,
                        **{key: {'path': str(path), **identity(path.read_bytes())} for key, path in paths.items()}}
        self.save_request()

    def save_request(self):
        self.request_path.write_bytes(subject.encoded(self.request))
        self.request_sha = identity(self.request_path.read_bytes())['sha256']

    def rewrite_record(self, name, change):
        path = Path(self.request[name]['path'])
        value = json.loads(path.read_text())
        change(value)
        path.write_bytes(subject.encoded(value))
        self.request[name] = {'path': str(path), **identity(path.read_bytes())}
        self.save_request()

    def run_reconcile(self, **changes):
        values = dict(request_path=self.request_path, expected_sha256=self.request_sha, output_dir=self.output)
        values.update(changes)
        return subject.reconcile(**values)

    def fails(self, **changes):
        with self.assertRaises((ValueError, OSError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile)):
            self.run_reconcile(**changes)
        self.assertFalse(self.output.exists())

    def assert_success(self, result, *, normalized_aliases=()):
        self.assertEqual('signed-image-archive-reconciled-only', result['status'])
        self.assertTrue(all(value is False for value in result['limits'].values()))
        report = json.loads((self.output / 'receipt.json').read_text())
        self.assertTrue(report['original_build_metadata_preserved'])
        self.assertTrue(report['fourteen_signer_inputs_preserved'])
        self.assertTrue(report['working76_preserved'])
        self.assertEqual(set(normalized_aliases), set(report['alias_normalizations']))
        self.assertEqual(report['alias_normalizations'], result['alias_normalizations'])
        self.assertFalse(report['archive_runtime']['cross_runtime_byte_reproduction_verified'])
        self.assertEqual(6, report['archive_runtime']['deflate_level'])
        self.assertTrue(report['archive_runtime']['python_version'])
        self.assertTrue(report['archive_runtime']['zlib_runtime_version'])
        final = self.output / 'target-files.zip'
        self.assertEqual(identity(final.read_bytes()), subject.selected(result['archive']))
        self.assertEqual(0o600, stat.S_IMODE(final.stat().st_mode))
        with zipfile.ZipFile(final) as out, zipfile.ZipFile(self.archive) as original:
            self.assertEqual(original.namelist(), out.namelist())
            self.assertEqual(original.comment, out.comment)
            for name in original.namelist():
                role = Path(name).stem
                if name.startswith(('IMAGES/', 'BOOTABLE_IMAGES/', 'PREBUILT_IMAGES/')) and role in subject.CHANGED_ROLES:
                    self.assertEqual((self.signed[0] / (role + '.img')).read_bytes(), out.read(name))
                elif name in normalized_aliases:
                    self.assertEqual(original.read('IMAGES/dtbo.img'), out.read(name))
                elif name == 'META/vbmeta_digest.txt':
                    self.assertEqual(fixture_digest({r: (self.signed[0] / (r + '.img')).read_bytes()
                                                    for r in subject.avb.SIGNED}), out.read(name))
                else:
                    self.assertEqual(original.read(name), out.read(name), name)
            for name in ('SYSTEM/bin/sh', 'SYSTEM/bin/empty'):
                self.assertEqual(original.getinfo(name).external_attr, out.getinfo(name).external_attr)
        labels = [row[0] for row in self.f.calls]
        self.assertIn('calculate-vbmeta-digest', labels)
        self.assertTrue(any('verify' in label for label in labels))
        self.assertFalse(any(label.startswith('sign-') for label in labels))

    def test_real_streaming_keeps_all_other_members_metadata_and_no_private_access(self):
        self.assert_success(self.run_reconcile())

    def test_deflated_archive_and_all_existing_aliases_are_reconciled(self):
        for prefix in ('BOOTABLE_IMAGES', 'PREBUILT_IMAGES'):
            for role in ('boot', 'vbmeta', 'vbmeta_system'):
                self.members[f'{prefix}/{role}.img'] = b'OLD DISTINCT ALIAS NOT A FALLBACK'
        self.members['BOOTABLE_IMAGES/recovery.img'] = self.f.fx.images['recovery']
        self.refresh_archive(zipfile.ZIP_DEFLATED)
        self.assert_success(self.run_reconcile())

    def test_already_identical_replacement_alias_is_valid(self):
        self.members['BOOTABLE_IMAGES/boot.img'] = (self.signed[0] / 'boot.img').read_bytes()
        self.refresh_archive()
        self.assert_success(self.run_reconcile())

    def dtbo_alias(self, *, payload=None, digest=None, properties=None, rollback=0, flags=0):
        payload = self.f.fx.payloads['dtbo'] if payload is None else payload
        if properties is None:
            properties = [fixtures.fixture.property_descriptor(
                b'com.android.build.dtbo.fingerprint', b'prebuilt-fixture-fingerprint')]
        metadata = fixtures.fixture.vbmeta([
            fixtures.fixture.hash_descriptor('dtbo', payload, salt=b'A' * 64, digest=digest),
            *properties], rollback=rollback, flags=flags)
        return fixtures.fixture.with_footer(payload, metadata)

    def test_proven_dtbo_prebuilt_alias_is_normalized_without_changing_canonical_image(self):
        alias = self.dtbo_alias()
        self.members[subject.DTBO_ALIAS_MEMBER] = alias
        self.refresh_archive(zipfile.ZIP_DEFLATED)
        original_archive = self.archive.read_bytes()
        result = self.run_reconcile()
        self.assert_success(result, normalized_aliases=(subject.DTBO_ALIAS_MEMBER,))
        proof = result['alias_normalizations'][subject.DTBO_ALIAS_MEMBER]
        self.assertEqual(identity(alias), proof['before'])
        self.assertEqual(identity(self.members['IMAGES/dtbo.img']), proof['after'])
        self.assertEqual(identity(original_archive), proof['source_archive'])
        self.assertEqual(original_archive, self.archive.read_bytes())
        report = json.loads((self.output / 'receipt.json').read_text())
        copied = report['archive_copy']
        self.assertEqual(proof, copied['dtbo_alias_proof'])
        replacement_names = {row['member'] for row in copied['replacement_members']}
        self.assertIn(subject.DTBO_ALIAS_MEMBER, replacement_names)
        self.assertNotIn('IMAGES/dtbo.img', replacement_names)

    def test_identical_dtbo_alias_is_preserved_without_normalization_proof(self):
        self.members[subject.DTBO_ALIAS_MEMBER] = self.members['IMAGES/dtbo.img']
        self.refresh_archive()
        with mock.patch.object(subject, 'inspect_dtbo_alias', side_effect=AssertionError('unneeded DTBO proof')):
            self.assert_success(self.run_reconcile())

    def test_absent_dtbo_alias_is_not_created_or_selected(self):
        with mock.patch.object(subject, 'inspect_dtbo_alias', side_effect=AssertionError('absent DTBO alias')):
            result = self.run_reconcile()
        with zipfile.ZipFile(result['archive']['path']) as archive:
            self.assertNotIn(subject.DTBO_ALIAS_MEMBER, archive.namelist())
        self.assertEqual({}, result['alias_normalizations'])

    def test_dtbo_exception_does_not_admit_other_alias_names(self):
        for name in ('BOOTABLE_IMAGES/dtbo.img', 'PREBUILT_IMAGES/vendor.img'):
            with self.subTest(name=name):
                self.members[name] = self.dtbo_alias()
                self.refresh_archive()
                with mock.patch.object(subject, 'inspect_dtbo_alias', side_effect=AssertionError('wrong alias name')):
                    self.fails()
                self.assertEqual([], self.f.calls)
                del self.members[name]

    def test_dtbo_alias_changed_payload_or_unreviewed_metadata_fails_before_native(self):
        payload = bytearray(self.f.fx.payloads['dtbo'])
        payload[-1] ^= 1
        property_descriptor = fixtures.fixture.property_descriptor
        cases = {
            'changed payload with a valid new hash': self.dtbo_alias(payload=bytes(payload)),
            'incorrect payload digest': self.dtbo_alias(digest=b'D' * 32),
            'changed flags': self.dtbo_alias(flags=1),
            'changed rollback': self.dtbo_alias(rollback=1),
            'missing fingerprint': self.dtbo_alias(properties=[]),
            'renamed property': self.dtbo_alias(properties=[property_descriptor(b'com.android.build.other', b'other')]),
            'extra property': self.dtbo_alias(properties=[
                property_descriptor(b'com.android.build.dtbo.fingerprint', b'prebuilt'),
                property_descriptor(b'com.android.build.extra', b'unreviewed')]),
        }
        for label, raw in cases.items():
            with self.subTest(label=label):
                self.members[subject.DTBO_ALIAS_MEMBER] = raw
                self.refresh_archive()
                self.fails()
                self.assertEqual([], self.f.calls)

    def test_dtbo_alias_nonzero_padding_and_unparsed_header_changes_fail_before_native(self):
        alias = self.dtbo_alias()
        metadata_at = struct.unpack_from('>Q', alias, len(alias) - 44)[0]
        offsets = {
            'payload padding': len(self.f.fx.payloads['dtbo']),
            'metadata padding': len(alias) - 65,
            'release string': metadata_at + 128,
            'AVB header reserved': metadata_at + 176,
            'footer reserved': len(alias) - 1,
        }
        for label, offset in offsets.items():
            with self.subTest(label=label):
                raw = bytearray(alias)
                raw[offset] ^= 1
                self.members[subject.DTBO_ALIAS_MEMBER] = bytes(raw)
                self.refresh_archive()
                self.fails()
                self.assertEqual([], self.f.calls)

    def test_dtbo_alias_proof_must_select_same_source_and_canonical_identities(self):
        self.members[subject.DTBO_ALIAS_MEMBER] = self.dtbo_alias()
        self.refresh_archive()
        real = subject.inspect_dtbo_alias
        for field in ('source_archive', 'before', 'after'):
            def substitute(*args, **kwargs):
                proof = real(*args, **kwargs)
                proof[field]['sha256'] = '0' * 64
                return proof
            with self.subTest(field=field), mock.patch.object(subject, 'inspect_dtbo_alias', side_effect=substitute):
                self.fails()
                self.assertEqual([], self.f.calls)

    def test_dtbo_alias_source_mutation_after_proof_fails(self):
        self.members[subject.DTBO_ALIAS_MEMBER] = self.dtbo_alias()
        self.refresh_archive()
        real = subject.inspect_dtbo_alias
        def mutate(*args, **kwargs):
            proof = real(*args, **kwargs)
            original = self.archive.read_bytes()
            self.archive.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            return proof
        with mock.patch.object(subject, 'inspect_dtbo_alias', side_effect=mutate):
            self.fails()
        self.assertEqual([], self.f.calls)

    def test_dtbo_alias_copier_must_return_the_same_recomputed_proof(self):
        self.members[subject.DTBO_ALIAS_MEMBER] = self.dtbo_alias()
        self.refresh_archive()
        real = subject.rewrite_archive
        def substitute(*args, **kwargs):
            report = real(*args, **kwargs)
            report['dtbo_alias_proof'] = deepcopy(report['dtbo_alias_proof'])
            report['dtbo_alias_proof']['before']['sha256'] = '0' * 64
            return report
        with mock.patch.object(subject, 'rewrite_archive', side_effect=substitute):
            self.fails()

    def test_unknown_request_field_and_boolean_schema_fail_before_native(self):
        for key, value in (('schema_version', True), ('invented_bypass', True)):
            with self.subTest(key=key):
                old = deepcopy(self.request)
                self.request[key] = value
                self.save_request()
                self.fails()
                self.assertEqual([], self.f.calls)
                self.request = old

    def test_wrong_request_hash_and_selected_input_pin_fail(self):
        self.fails(expected_sha256='0' * 64)
        self.request['target_files']['sha256'] = '0' * 64
        self.save_request()
        self.fails()
        self.assertEqual([], self.f.calls)

    def observe_reads(self, selected_path):
        """Trace only an inert sentinel, using the real unbuffered safe opener."""
        original = subject.avb._input
        reads = []
        class Traced:
            def __init__(self, stream):
                self.stream = stream
            def read(self, *args):
                value = self.stream.read(*args)
                reads.append(value)
                return value
            def readline(self, *args):
                value = self.stream.readline(*args)
                reads.append(value)
                return value
            def __getattr__(self, name):
                return getattr(self.stream, name)
        @contextmanager
        def trace(path, maximum):
            with original(path, maximum) as (stream, info):
                yield (Traced(stream) if Path(path) == selected_path else stream), info
        return reads, mock.patch.object(subject.avb, '_input', side_effect=trace)

    def test_mistaken_pem_json_selector_is_rejected_before_body_hashing(self):
        path = self.root / 'inert-wrong-record.pem'
        raw = b'-----BEGIN PRIVATE KEY-----\nINERT SENTINEL NOT A KEY\n-----END PRIVATE KEY-----\n'
        path.write_bytes(raw)
        self.request['inventory'] = {'path': str(path), **identity(raw)}
        self.save_request()
        reads, patcher = self.observe_reads(path)
        with patcher:
            self.fails()
        self.assertEqual(b'-', b''.join(reads))
        self.assertEqual([], self.f.calls)

    def test_mistaken_pem_archive_selector_is_rejected_at_zip_header(self):
        path = self.root / 'inert-wrong-archive.pem'
        raw = b'-----BEGIN PRIVATE KEY-----\nINERT SENTINEL NOT A KEY\n-----END PRIVATE KEY-----\n'
        path.write_bytes(raw)
        self.request['target_files'] = {'path': str(path), **identity(raw)}
        self.save_request()
        reads, patcher = self.observe_reads(path)
        with patcher:
            self.fails()
        self.assertEqual(b'----', b''.join(reads))
        self.assertEqual([], self.f.calls)

    def test_mistaken_pem_source_record_is_rejected_before_body_hashing(self):
        path = self.root / 'inert-wrong-source.pem'
        raw = b'-----BEGIN PRIVATE KEY-----\nINERT SENTINEL NOT A KEY\n-----END PRIVATE KEY-----\n'
        path.write_bytes(raw)
        reads, patcher = self.observe_reads(path)
        with patcher, self.assertRaises(ValueError):
            subject.Guards().json(path, identity(raw))
        self.assertEqual(b'-', b''.join(reads))

    def test_private_pem_selected_as_public_key_is_rejected_at_header(self):
        path = self.root / 'inert-wrong-public.pem'
        header = b'-----BEGIN PRIVATE KEY-----\n'
        raw = header + b'INERT SENTINEL NOT A KEY\n-----END PRIVATE KEY-----\n'
        path.write_bytes(raw)
        reads, patcher = self.observe_reads(path)
        with patcher, self.assertRaises(ValueError):
            subject.Guards().public_key(path, identity(raw))
        self.assertEqual(header, b''.join(reads))

    def test_record_inode_replacement_after_json_header_check_fails(self):
        path = self.root / 'inert-replaced-record.json'
        raw = b'{"inert":true}\n'
        path.write_bytes(raw)
        original = subject.signing._json_file
        def replace(*args, **kwargs):
            value = original(*args, **kwargs)
            alternate = path.with_suffix('.new')
            alternate.write_bytes(raw)
            alternate.replace(path)
            return value
        with mock.patch.object(subject.signing, '_json_file', side_effect=replace), self.assertRaises(ValueError):
            subject.Guards().json(path, identity(raw))

    def test_unknown_inventory_claim_is_rejected_even_with_updated_pin(self):
        self.rewrite_record('inventory', lambda value: value.update(hardware_verified=True))
        self.fails()
        self.assertEqual([], self.f.calls)

    def test_incomplete_preparation_record_fails(self):
        self.rewrite_record('signing_preparation', lambda value: value.update(source_inputs_unchanged=False))
        self.fails()
        self.assertEqual([], self.f.calls)

    def test_signing_receipt_cannot_claim_another_preparation(self):
        self.rewrite_record('signing_receipt', lambda value: value.update(preparation_sha256='0' * 64))
        self.fails()

    def test_artifact_set_identity_must_match_all_records(self):
        self.rewrite_record('signing_receipt', lambda value: value.update(artifact_set_id='another-inert-set'))
        self.fails()

    def test_missing_reproduction_or_changed_leaf_admission_fails(self):
        self.rewrite_record('signing_receipt', lambda value: value.update(two_pass_reproduction_verified=False))
        self.fails()

    def test_changed_recovery_input_is_rejected_by_actual_inventory(self):
        self.members['IMAGES/recovery.img'] = b'UNAPPROVED RECOVERY'
        self.refresh_archive()
        self.fails()

    def test_changed_prepared_leaf_is_not_the_selected_archive(self):
        self.members['IMAGES/vendor.img'] = b'CHANGED VENDOR BYTES'
        self.refresh_archive()
        self.fails()

    def test_unchanged_alias_may_not_disagree_with_admitted_image(self):
        self.members['BOOTABLE_IMAGES/recovery.img'] = b'UNAPPROVED RECOVERY ALIAS'
        self.refresh_archive()
        self.fails()

    def test_stale_original_digest_fails_before_any_native_call(self):
        self.members['META/vbmeta_digest.txt'] = b'0' * 64 + b'\n'
        self.refresh_archive()
        self.fails()
        self.assertEqual([], self.f.calls)

    def test_original_digest_requires_exact_native_newline_format(self):
        self.members['META/vbmeta_digest.txt'] = self.members['META/vbmeta_digest.txt'].rstrip(b'\n')
        self.refresh_archive()
        self.fails()

    def test_public_verification_failure_prevents_new_archive(self):
        def incomplete(path, value):
            value['complete_chain_verified'] = False
            return value
        self.f.verify_hook = incomplete
        self.fails()
        self.assertFalse(any('incomplete-' in p.name for p in self.output.parent.iterdir()))

    def test_native_digest_failure_retains_partial_without_published_output(self):
        self.fail_digest = True
        self.fails()
        self.assertTrue(any('incomplete-' in p.name for p in self.output.parent.iterdir()))

    def test_native_digest_malformed_or_mismatched_result_fails(self):
        for field in ('malformed_digest', 'mismatch_digest'):
            with self.subTest(field=field):
                setattr(self, field, True)
                self.fails()
                setattr(self, field, False)

    def test_existing_output_is_refused_before_native(self):
        self.output.mkdir()
        sentinel = self.output / 'sentinel'
        sentinel.write_bytes(b'KEEP EXISTING')
        with self.assertRaises(ValueError):
            self.run_reconcile()
        self.assertEqual(b'KEEP EXISTING', sentinel.read_bytes())
        self.assertEqual([], self.f.calls)

    def test_symlink_output_parent_and_low_space_fail_before_native(self):
        alias = self.output.parent / 'alias-parent'
        alias.symlink_to(self.root, target_is_directory=True)
        self.fails(output_dir=alias / 'new')
        with mock.patch.object(subject.shutil, 'disk_usage', return_value=SimpleNamespace(free=0)):
            self.fails()
        self.assertEqual([], self.f.calls)

    def test_source_same_bytes_inode_replacement_during_copy_fails(self):
        original = subject.rewrite_archive
        def replace(*args, **kwargs):
            value = original(*args, **kwargs)
            path = self.root / 'source-replaced.zip'
            path.write_bytes(self.archive.read_bytes())
            path.replace(self.archive)
            return value
        with mock.patch.object(subject, 'rewrite_archive', side_effect=replace):
            self.fails()

    def test_signed_leaf_mutation_during_copy_fails(self):
        original = subject.rewrite_archive
        def replace(*args, **kwargs):
            value = original(*args, **kwargs)
            path = self.signed[0] / 'vendor.img'
            path.write_bytes(path.read_bytes()[:-1] + b'!')
            return value
        with mock.patch.object(subject, 'rewrite_archive', side_effect=replace):
            self.fails()

    def test_same_byte_output_replacement_after_final_content_check_fails(self):
        original = subject.Guards.recheck
        replaced = False
        def replace(guards):
            nonlocal replaced
            original(guards)
            for path in guards.files:
                if path.name == 'target-files.zip' and not replaced:
                    replacement = path.with_name('replacement.zip')
                    replacement.write_bytes(path.read_bytes())
                    replacement.replace(path)
                    replaced = True
        with mock.patch.object(subject.Guards, 'recheck', new=replace):
            self.fails()
        self.assertTrue(replaced)

    def test_output_payload_corruption_before_final_recheck_fails(self):
        original = subject._topology
        invoked = False
        def corrupt(path):
            nonlocal invoked
            value = original(path)
            if not invoked:
                archive = path / 'target-files.zip'
                raw = archive.read_bytes()
                archive.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
                invoked = True
            return value
        with mock.patch.object(subject, '_topology', side_effect=corrupt):
            self.fails()

    def test_exclusive_publication_race_never_overwrites_new_destination(self):
        original = subject.publish_new_directory
        def raced(staging, output):
            output.mkdir()
            (output / 'sentinel').write_bytes(b'KEEP RACING OWNER')
            original(staging, output)
        with mock.patch.object(subject, 'publish_new_directory', side_effect=raced):
            with self.assertRaises(OSError):
                self.run_reconcile()
        self.assertEqual(b'KEEP RACING OWNER', (self.output / 'sentinel').read_bytes())
        self.assertFalse((self.output / 'target-files.zip').exists())

    def test_cli_returns_only_blocked_scope_without_private_paths(self):
        with redirect_stderr(io.StringIO()) as stream:
            result = subject.main(['--request', str(self.request_path), '--expected-sha256', '0' * 64,
                                   '--output-dir', str(self.output)])
        self.assertEqual(2, result)
        value = json.loads(stream.getvalue())
        self.assertEqual('blocked', value['status'])
        self.assertTrue(all(v is False for v in value['limits'].values()))
        self.assertNotIn(str(self.f.private_path), stream.getvalue())


class MetadataAdmissionTests(unittest.TestCase):
    BASE = b'ab_update=true\navb_enable=true\navb_building_vbmeta_image=true\n'

    def test_native_omitted_defaults_and_original_key_recipe_are_accepted(self):
        raw = self.BASE + b'avb_vbmeta_key_path=original-signing-recipe\nother=1\nother=2\n'
        self.assertEqual({'ab_update': 'true', 'avb_enable': 'true', 'avb_building_vbmeta_image': 'true'},
                         subject.admit_misc_info(raw))

    def test_explicit_false_nonab_and_single_boot_are_accepted(self):
        subject.admit_misc_info(self.BASE + b'allow_non_ab=false\nboot_images=boot.img\n')

    def test_changed_or_duplicate_consumed_values_fail(self):
        cases = [self.BASE.replace(b'ab_update=true\n', b''),
                 self.BASE.replace(b'avb_building_vbmeta_image=true', b'avb_building_vbmeta_image=false'),
                 self.BASE + b'ab_update=true\n', self.BASE + b'allow_non_ab=true\n',
                 self.BASE + b'allow_non_ab=\n', self.BASE + b'boot_images=\n',
                 self.BASE + b'boot_images=renamed.img\n',
                 self.BASE + b'boot_images=boot.img other.img\n',
                 self.BASE + b'boot_images=boot.img\nboot_images=boot.img\n']
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    subject.admit_misc_info(raw)


if __name__ == '__main__':
    unittest.main()


class CurrentPublicContractTests(unittest.TestCase):
    def test_current_public_contracts_load_without_mocks(self):
        value = subject.controls()
        self.assertEqual(value[1], hashlib.sha256(Path(subject.signing.ROOT / "config/nezha-avb-signing.json").read_bytes()).hexdigest())
        self.assertEqual(value[3], hashlib.sha256(Path(subject.signing.ROOT / "config/nezha-avb-image-set.json").read_bytes()).hexdigest())
