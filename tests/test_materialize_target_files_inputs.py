"""Inert temp ZIPs and mocked factory identities; no ROM/native/device evidence."""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import unittest
from unittest import mock
import zipfile

from tests import test_target_files_avb_inventory as fixtures
from scripts import materialize_target_files_inputs as materializer


class MaterializerTests(unittest.TestCase):
    # Reuse only fixture methods, not the maintained module's 42-test suite.
    load_contract = fixtures.TargetFilesAvbInventoryTests.load_contract
    save_retained = fixtures.TargetFilesAvbInventoryTests.save_retained
    write_zip = fixtures.TargetFilesAvbInventoryTests.write_zip
    inspect = fixtures.TargetFilesAvbInventoryTests.inspect

    def setUp(self):
        fixtures.TargetFilesAvbInventoryTests.setUp(self)
        self.contract['output_root'] = 'artifacts/avb/nezha'
        self.enterContext(mock.patch.object(materializer, 'contracts', side_effect=self.load_contract))
        self.enterContext(mock.patch.object(materializer.signing, 'ROOT', self.root))
        self.output_parent = self.root / 'artifacts/avb/nezha'
        self.output_parent.mkdir(parents=True)
        self.output = self.output_parent / 'materialized-v1'
        self.record = self.root / 'inventory.json'
        self.archive_identity = self.write_zip()
        self.save_inventory()

    def save_inventory(self):
        self.inventory_value = self.inspect(retained=True)
        self.record.write_bytes(materializer.encoded(self.inventory_value))
        self.inventory_sha = fixtures.identity(self.record.read_bytes())['sha256']

    def run_materialize(self, **changes):
        args = dict(target_files=self.archive, expected_archive=self.archive_identity,
                    inventory_record=self.record, expected_inventory_sha256=self.inventory_sha,
                    retained_manifest=self.retained,
                    expected_retained_sha256=fixtures.identity(self.retained.read_bytes())['sha256'],
                    output_dir=self.output, artifact_set_id='synthetic-not-a-rom')
        args.update(changes)
        return materializer.materialize(**args)

    def fails(self, **changes):
        with self.assertRaises((ValueError, OSError, RuntimeError, KeyError, zipfile.BadZipFile)):
            self.run_materialize(**changes)
        if not self.output.exists():
            self.assertFalse(os.path.lexists(self.output))

    def assert_success(self, result):
        self.assertEqual('materialized-inputs-only', result['status'])
        self.assertTrue(all(result['scope'][key] is False for key in materializer.FALSE_SCOPE))
        self.assertTrue(result['scope']['image_bytes_materialized'])
        self.assertTrue(result['scope']['signer_input_schema_verified'])
        path = self.output / 'input-manifest.json'
        manifest, unused = materializer.signing.load_input(path, result['input_manifest']['sha256'],
                                                         self.contract, self.contract_sha, self.profile)
        self.assertEqual(fixtures.FINAL_ROLES | fixtures.RAW_ROLES, set(manifest['images']))
        self.assertEqual({role + '.img' for role in manifest['images']}, {p.name for p in (self.output / 'images').iterdir()})
        for role, row in manifest['images'].items():
            self.assertEqual(self.images[role], row['path'].read_bytes())
            self.assertEqual(1, row['path'].stat().st_nlink)
            self.assertEqual(0o600, stat.S_IMODE(row['path'].stat().st_mode))
        receipt = json.loads((self.output / 'receipt.json').read_text())
        self.assertEqual((15, 13, 2), tuple(receipt[key] for key in ('image_count', 'extracted_image_count', 'retained_image_count')))
        self.assertTrue(receipt['inputs_unchanged'])
        self.assertTrue(receipt['output_bytes_independently_rehashed'])
        self.assertFalse((self.output / 'images/vbmeta.img').exists())
        self.assertFalse((self.output / 'images/vbmeta_system.img').exists())
        self.assertEqual(self.archive_identity, fixtures.identity(self.archive.read_bytes()))

    def test_stored_inputs_become_exact_fifteen_files_and_existing_signer_manifest(self):
        self.assert_success(self.run_materialize())

    def test_deflate_inputs_use_existing_end_of_stream_validator(self):
        self.archive_identity = self.write_zip(compression=zipfile.ZIP_DEFLATED)
        self.save_inventory()
        with mock.patch.object(materializer.inventory, '_deflate_complete', wraps=materializer.inventory._deflate_complete) as check:
            self.assert_success(self.run_materialize())
        self.assertGreaterEqual(check.call_count, 28)  # 15 inventory entries plus 13 extracted entries.

    def test_two_destinations_reproduce_all_manifest_and_image_bytes(self):
        first = self.run_materialize()
        second = self.run_materialize(output_dir=self.output_parent / 'materialized-v2')
        self.assertEqual(first['input_manifest']['sha256'], second['input_manifest']['sha256'])
        self.assertEqual(first['receipt']['sha256'], second['receipt']['sha256'])
        for path in self.output.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (self.output_parent / 'materialized-v2' / path.relative_to(self.output)).read_bytes())

    def test_missing_actual_inventory_does_not_create_output(self):
        self.fails(inventory_record=self.root / 'absent.json')
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_resealed_inventory_cannot_invent_success_or_extra_fields(self):
        self.inventory_value['invented_native_pass'] = True
        self.record.write_bytes(materializer.encoded(self.inventory_value))
        self.fails(expected_inventory_sha256=fixtures.identity(self.record.read_bytes())['sha256'])
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_wrong_archive_inventory_or_retained_manifest_pins_fail(self):
        for changes in ({'expected_archive': {**self.archive_identity, 'sha256': '0' * 64}},
                        {'expected_inventory_sha256': '0' * 64}, {'expected_retained_sha256': '0' * 64}):
            with self.subTest(changes=changes):
                self.fails(**changes)
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_missing_final_image_cannot_use_bootable_alias(self):
        del self.members['IMAGES/boot.img']
        self.members['BOOTABLE_IMAGES/boot.img'] = self.images['boot']
        self.archive_identity = self.write_zip()
        self.save_inventory()
        self.fails()

    def test_alias_payload_never_replaces_exact_final_entry(self):
        self.members['BOOTABLE_IMAGES/boot.img'] = b'A' * 4096
        self.archive_identity = self.write_zip()
        self.save_inventory()
        self.assert_success(self.run_materialize())

    def test_duplicate_traversal_and_selected_symlink_members_fail(self):
        cases = [dict(extra=[('IMAGES/boot.img', self.images['boot'])]),
                 dict(extra=[('../outside', b'no')]),
                 dict(modes={'IMAGES/boot.img': stat.S_IFLNK | 0o777})]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                self.archive_identity = self.write_zip(**kwargs)
                self.save_inventory()
                self.fails()

    def test_corrupted_zip_crc_is_not_materialized(self):
        data = bytearray(self.archive.read_bytes())
        with zipfile.ZipFile(self.archive) as archive:
            info = archive.getinfo('IMAGES/boot.img')
            offset = info.header_offset + 30 + len(info.filename.encode())
        data[offset] ^= 1
        self.archive.write_bytes(data)
        self.archive_identity = fixtures.identity(bytes(data))
        self.save_inventory()
        self.fails()

    def test_wrong_recovery_or_retained_firmware_is_rejected(self):
        self.members['IMAGES/recovery.img'] = b'R' * 4096
        self.archive_identity = self.write_zip()
        self.save_inventory()
        self.fails()
        self.members['IMAGES/recovery.img'] = self.images['recovery']
        self.archive_identity = self.write_zip()
        (self.root / 'countrycode.raw').write_bytes(b'C' * 4096)
        self.save_inventory()
        self.fails()

    def test_existing_output_or_symlink_is_never_replaced(self):
        self.output.mkdir()
        sentinel = self.output / 'sentinel'
        sentinel.write_bytes(b'keep')
        self.fails()
        self.assertEqual(b'keep', sentinel.read_bytes())
        link = self.output_parent / 'alias'
        link.symlink_to(self.output, target_is_directory=True)
        self.fails(output_dir=link)
        self.assertTrue(link.is_symlink())

    def test_symlinked_output_parent_is_rejected(self):
        link = self.output_parent / 'alias-parent'
        link.symlink_to(self.root, target_is_directory=True)
        self.fails(output_dir=link / 'new')
        self.assertFalse((self.root / 'new').exists())

    def test_archive_same_bytes_inode_replacement_during_copy_fails(self):
        original = materializer._copy_member
        replaced = False
        def replace(*args, **kwargs):
            nonlocal replaced
            original(*args, **kwargs)
            if not replaced:
                replacement = self.root / 'replacement.zip'
                replacement.write_bytes(self.archive.read_bytes())
                replacement.replace(self.archive)
                replaced = True
        with mock.patch.object(materializer, '_copy_member', side_effect=replace):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_retained_same_bytes_inode_replacement_after_inventory_fails(self):
        original = materializer._copy_member
        replaced = False
        def replace(*args, **kwargs):
            nonlocal replaced
            original(*args, **kwargs)
            if not replaced:
                replacement = self.root / 'replacement.raw'
                replacement.write_bytes(self.images['countrycode'])
                replacement.replace(self.root / 'countrycode.raw')
                replaced = True
        with mock.patch.object(materializer, '_copy_member', side_effect=replace):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_late_image_or_manifest_corruption_prevents_atomic_publication(self):
        original = materializer._verify_files
        for relative in ('images/boot.img', 'input-manifest.json'):
            with self.subTest(relative=relative):
                count = 0
                def corrupt(directory, *args):
                    nonlocal count
                    original(directory, *args)
                    count += 1
                    if count == 1:
                        path = directory / relative
                        raw = path.read_bytes()
                        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                with mock.patch.object(materializer, '_verify_files', side_effect=corrupt):
                    self.fails()
                self.assertFalse(self.output.exists())

    def test_destination_race_fails_without_replacing_existing_bytes(self):
        original = materializer.publish_new_directory
        def raced(staging, output):
            output.mkdir()
            (output / 'sentinel').write_bytes(b'keep')
            original(staging, output)
        with mock.patch.object(materializer, 'publish_new_directory', side_effect=raced):
            self.fails()
        self.assertEqual(b'keep', (self.output / 'sentinel').read_bytes())
        self.assertFalse((self.output / 'input-manifest.json').exists())

    def test_low_space_refuses_before_staging(self):
        with mock.patch.object(materializer.shutil, 'disk_usage', return_value=type('Usage', (), {'free': 0})()):
            self.fails()
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_additional_source_json_is_copied_and_hash_bound(self):
        path = self.root / 'synthetic-build-review.json'
        path.write_bytes(b'{"synthetic_only":true,"native_build_claimed":false}\n')
        row = {'path': str(path), **fixtures.identity(path.read_bytes())}
        result = self.run_materialize(source_records=[row])
        self.assert_success(result)
        self.assertEqual(path.read_bytes(), (self.output / 'provenance/source-001.json').read_bytes())

    def test_malformed_or_duplicate_field_provenance_json_is_rejected(self):
        path = self.root / 'synthetic-bad-review.json'
        for raw in (b'{not-json', b'{"same":1,"same":2}'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                self.fails(source_records=[{'path': str(path), **fixtures.identity(raw)}])
                self.assertEqual([], list(self.output_parent.iterdir()))

    def test_output_change_during_last_archive_hash_is_rejected(self):
        original_hash = materializer.avb._rehash
        original_verify = materializer._verify_files
        state = {'ready': False, 'directory': None}
        def verify(directory, *args):
            result = original_verify(directory, *args)
            if (directory / 'receipt.json').exists():
                state.update(ready=True, directory=directory)
            return result
        def changed(path, *args, **kwargs):
            result = original_hash(path, *args, **kwargs)
            if path == self.archive and state['ready']:
                target = state['directory'] / 'images/boot.img'
                raw = target.read_bytes()
                target.write_bytes(b'X' + raw[1:])
                state['ready'] = False
            return result
        with mock.patch.object(materializer, '_verify_files', side_effect=verify), mock.patch.object(materializer.avb, '_rehash', side_effect=changed):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_same_byte_staging_root_replacement_is_rejected(self):
        original_hash = materializer.avb._rehash
        original_verify = materializer._verify_files
        state = {'ready': False, 'directory': None}
        def verify(directory, *args):
            result = original_verify(directory, *args)
            if (directory / 'receipt.json').exists():
                state.update(ready=True, directory=directory)
            return result
        def changed(path, *args, **kwargs):
            result = original_hash(path, *args, **kwargs)
            if path == self.archive and state['ready']:
                directory = state['directory']
                backup = directory.with_name(directory.name + '-original')
                directory.rename(backup)
                shutil.copytree(backup, directory)
                state['ready'] = False
            return result
        with mock.patch.object(materializer, '_verify_files', side_effect=verify), mock.patch.object(materializer.avb, '_rehash', side_effect=changed):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_earlier_source_replacement_during_later_source_hash_is_rejected(self):
        original_hash = materializer.avb._rehash
        original_verify = materializer._verify_files
        state = {'ready': False}
        def verify(directory, *args):
            result = original_verify(directory, *args)
            if (directory / 'receipt.json').exists():
                state['ready'] = True
            return result
        def changed(path, *args, **kwargs):
            result = original_hash(path, *args, **kwargs)
            if path == self.root / 'pvmfw.raw' and state['ready']:
                replacement = self.root / 'archive-new-inode.zip'
                replacement.write_bytes(self.archive.read_bytes())
                replacement.replace(self.archive)
                state['ready'] = False
            return result
        with mock.patch.object(materializer, '_verify_files', side_effect=verify), mock.patch.object(materializer.avb, '_rehash', side_effect=changed):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_extra_raw_vbmeta_or_key_record_is_rejected(self):
        for role in ('vbmeta', 'boot'):
            with self.subTest(role=role):
                altered = copy.deepcopy(self.retained_value)
                altered['images'][role] = altered['images']['countrycode']
                self.retained.write_bytes(materializer.encoded(altered))
                self.fails()
        self.save_retained()
        self.fails(source_records=[{'path': str(self.root / 'never-read.pem'), 'sha256': 'a' * 64, 'size_bytes': 10}])

    def test_public_source_identity_change_is_not_accepted(self):
        altered = dict(materializer.PUBLIC_PINS)
        name = next(iter(altered))
        altered[name] = ('0' * 64, altered[name][1])
        with mock.patch.object(materializer, 'PUBLIC_PINS', altered):
            self.fails()

    @contextmanager
    def selected_reads(self, selected):
        """Observe byte reads of one inert input without buffering its body."""
        original = materializer.avb._input
        reads = []

        class Observed:
            def __init__(self, stream):
                self.stream = stream

            def read(self, count=-1):
                reads.append((self.stream.tell(), count))
                return self.stream.read(count)

            def __getattr__(self, name):
                return getattr(self.stream, name)

        @contextmanager
        def observe(path, maximum):
            with original(path, maximum) as (stream, info):
                yield (Observed(stream) if Path(path) == selected else stream), info

        with mock.patch.object(materializer.avb, '_input', side_effect=observe):
            yield reads

    def test_private_pem_selected_as_zip_stops_at_existing_four_byte_header(self):
        path = self.root / 'inert-private-marker.zip'
        raw = b'-----BEGIN PRIVATE KEY-----\nSYNTHETIC FIXTURE, NOT A KEY\n' + b'X' * 4096
        path.write_bytes(raw)
        with self.selected_reads(path) as reads:
            self.fails(target_files=path, expected_archive=fixtures.identity(raw))
        self.assertEqual([(0, 4)], reads)
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_private_pem_selected_as_json_never_reads_its_body(self):
        path = self.root / 'inert-private-marker.json'
        raw = b'-----BEGIN PRIVATE KEY-----\nSYNTHETIC FIXTURE, NOT A KEY\n'
        path.write_bytes(raw)
        pin = fixtures.identity(raw)
        for changes in (
            {'inventory_record': path, 'expected_inventory_sha256': pin['sha256']},
            {'retained_manifest': path, 'expected_retained_sha256': pin['sha256']},
            {'source_records': [{'path': str(path), **pin}]},
        ):
            with self.subTest(changes=tuple(changes)), self.selected_reads(path) as reads:
                self.fails(**changes)
                self.assertEqual([(0, 1)], reads)
        self.assertEqual([], list(self.output_parent.iterdir()))

    def swap_after_json_read(self, selected):
        original = materializer.signing._json_file
        changed = False

        def replace(path, *args, **kwargs):
            nonlocal changed
            result = original(path, *args, **kwargs)
            if Path(path) == selected and not changed:
                replacement = selected.with_name(selected.name + '.new-inode')
                replacement.write_bytes(result)
                replacement.replace(selected)
                changed = True
            return result

        return mock.patch.object(materializer.signing, '_json_file', side_effect=replace)

    def test_inventory_inode_replacement_after_json_read_blocks_publication(self):
        with self.swap_after_json_read(self.record):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_retained_manifest_inode_replacement_during_inventory_blocks_publication(self):
        with self.swap_after_json_read(self.retained):
            self.fails()
        self.assertFalse(self.output.exists())

    def test_nonprivate_output_modes_cannot_be_published(self):
        original = materializer._copy_member
        for selection in ('file', 'images', 'provenance', 'root'):
            with self.subTest(selection=selection):
                destination = self.output_parent / ('mode-' + selection)

                def changed(archive, info, output, *args):
                    result = original(archive, info, output, *args)
                    target = {'file': output, 'images': output.parent,
                              'provenance': output.parent.parent / 'provenance',
                              'root': output.parent.parent}[selection]
                    target.chmod(0o644 if selection == 'file' else 0o755)
                    return result

                with mock.patch.object(materializer, '_copy_member', side_effect=changed):
                    self.fails(output_dir=destination)
                self.assertFalse(destination.exists())

    def test_materialized_manifest_survives_existing_signer_normalization(self):
        result = self.run_materialize()
        manifest, unused = materializer.signing.load_input(
            self.output / 'input-manifest.json', result['input_manifest']['sha256'],
            self.contract, self.contract_sha, self.profile)
        prepared_directory = self.root / 'synthetic-normalized-manifest'
        prepared_directory.mkdir(mode=0o700)
        prepared_path = prepared_directory / 'input-manifest.json'
        prepared_pin = materializer.signing._input_file(manifest, prepared_path)
        prepared, unused = materializer.signing.load_input(
            prepared_path, prepared_pin['sha256'], self.contract, self.contract_sha, self.profile)
        self.assertNotEqual(result['input_manifest']['sha256'], prepared_pin['sha256'])
        self.assertEqual(manifest, prepared)
        self.assertEqual(15, len(prepared['images']))
        self.assertEqual(['materialization.json', 'inventory.json', 'factory-extraction.json'],
                         [row['path'].name for row in prepared['source_records']])
        for row in prepared['source_records']:
            self.assertTrue(row['path'].is_absolute())
            materializer.signing._json_file(row['path'], materializer.signing.MAX_TEXT, row)

    def test_maximum_additional_provenance_fits_existing_signer_limit(self):
        records = []
        for index in range(61):
            path = self.root / ('synthetic-source-' + str(index) + '.json')
            raw = materializer.encoded({'inert_source': index})
            path.write_bytes(raw)
            records.append({'path': str(path), **fixtures.identity(raw)})
        result = self.run_materialize(source_records=records)
        manifest, unused = materializer.signing.load_input(
            self.output / 'input-manifest.json', result['input_manifest']['sha256'],
            self.contract, self.contract_sha, self.profile)
        self.assertEqual(64, len(manifest['source_records']))
        self.assertEqual(records[-1]['sha256'], manifest['source_records'][-1]['sha256'])
        self.assertEqual('source-061.json', manifest['source_records'][-1]['path'].name)

    def test_source_record_count_and_size_limits_reject_before_body_read(self):
        path = self.root / 'unread-inert-record.json'
        path.write_bytes(b'{"inert":true}\n')
        row = {'path': str(path), **fixtures.identity(path.read_bytes())}
        for records in ([row] * 62, [{**row, 'size_bytes': materializer.signing.MAX_TEXT + 1}]):
            with self.subTest(count=len(records)), self.selected_reads(path) as reads:
                self.fails(source_records=records)
                self.assertEqual([], reads)
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_hardlinked_original_archive_is_rejected_without_staging(self):
        alias = self.root / 'archive-hardlink.zip'
        os.link(self.archive, alias)
        self.fails()
        self.assertEqual(self.archive_identity, fixtures.identity(alias.read_bytes()))
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_flush_failure_preserves_originals_and_does_not_publish(self):
        with mock.patch.object(materializer.os, 'fsync', side_effect=OSError('inert flush failure')):
            self.fails()
        self.assertFalse(self.output.exists())
        self.assertTrue(list(self.output_parent.glob('.materialized-v1.incomplete-*')))
        self.assertEqual(self.archive_identity, fixtures.identity(self.archive.read_bytes()))

    def cli_arguments(self):
        return ['--target-files', str(self.archive), '--expected-sha256', self.archive_identity['sha256'],
                '--expected-size-bytes', str(self.archive_identity['size_bytes']),
                '--inventory', str(self.record), '--expected-inventory-sha256', self.inventory_sha,
                '--retained-input-manifest', str(self.retained),
                '--expected-retained-manifest-sha256', fixtures.identity(self.retained.read_bytes())['sha256'],
                '--artifact-set-id', 'synthetic-not-a-rom', '--output-dir', str(self.output)]

    def test_cli_emits_only_materialization_result_on_success(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = materializer.main(self.cli_arguments())
        self.assertEqual(0, code)
        self.assertEqual('', stderr.getvalue())
        self.assert_success(json.loads(stdout.getvalue()))

    def test_cli_invalid_source_size_is_blocked_without_exposing_input_selectors(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        arguments = self.cli_arguments() + ['--source-record', str(self.root / 'private-selector.json'), 'a' * 64, 'invalid-size']
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = materializer.main(arguments)
        self.assertEqual(2, code)
        self.assertEqual('', stdout.getvalue())
        result = json.loads(stderr.getvalue())
        self.assertEqual('blocked', result['status'])
        self.assertEqual('ValueError', result['error_type'])
        self.assertEqual(materializer.FALSE_SCOPE, result['scope'])
        self.assertNotIn('private-selector', stderr.getvalue())
        self.assertEqual([], list(self.output_parent.iterdir()))

    def test_late_mode_change_cannot_become_the_final_verified_baseline(self):
        original = materializer.avb._file_signature
        changed = False

        def signature(path, maximum):
            nonlocal changed
            path = Path(path)
            if (path.name == 'boot.img' and path.parent.name == 'images'
                    and (path.parent.parent / 'receipt.json').exists() and not changed):
                path.chmod(0o644)
                changed = True
            return original(path, maximum)

        with mock.patch.object(materializer.avb, '_file_signature', side_effect=signature):
            self.fails()
        self.assertTrue(changed)
        self.assertFalse(self.output.exists())

    def test_midstream_space_drop_blocks_before_image_copy_finishes(self):
        observed_partial = []

        def available(descriptor):
            info = os.fstat(descriptor)
            if stat.S_ISREG(info.st_mode) and info.st_size == 1024:
                observed_partial.append(info.st_size)
                return 0
            return 1 << 40

        with mock.patch.object(materializer.avb, 'CHUNK', 512), \
                mock.patch.object(materializer, 'SPACE_CHECK_BYTES', 1024), \
                mock.patch.object(materializer.archive_copy, '_available', side_effect=available):
            self.fails()
        self.assertEqual([1024], observed_partial)
        stages = list(self.output_parent.glob('.materialized-v1.incomplete-*'))
        self.assertEqual(1, len(stages))
        self.assertEqual(1024, (stages[0] / 'images/boot.img').stat().st_size)
        self.assertLess(1024, len(self.images['boot']))
        self.assertFalse(self.output.exists())

    def test_metadata_write_rechecks_space_after_flush(self):
        original = materializer._write
        writing_metadata = False
        checked_metadata = False

        def write(path, raw, budget):
            nonlocal writing_metadata
            writing_metadata = path.name == 'inventory.json'
            return original(path, raw, budget)

        def available(descriptor):
            nonlocal checked_metadata
            info = os.fstat(descriptor)
            if writing_metadata and stat.S_ISREG(info.st_mode) and info.st_size:
                checked_metadata = True
                return 0
            return 1 << 40

        with mock.patch.object(materializer, '_write', side_effect=write), \
                mock.patch.object(materializer.archive_copy, '_available', side_effect=available):
            self.fails()
        self.assertTrue(checked_metadata)
        self.assertFalse(self.output.exists())

    def test_every_output_file_and_publication_directory_is_synced(self):
        original = materializer.os.fsync
        calls = []

        def synced(descriptor):
            info = os.fstat(descriptor)
            calls.append((info.st_dev, info.st_ino))
            return original(descriptor)

        with mock.patch.object(materializer.os, 'fsync', side_effect=synced):
            result = self.run_materialize()
        self.assert_success(result)
        for path in (self.output, self.output / 'images', self.output / 'provenance',
                     self.output.parent, *self.output.rglob('*')):
            info = path.stat()
            self.assertIn((info.st_dev, info.st_ino), calls, str(path))
        root = self.output.stat()
        self.assertEqual(2, calls.count((root.st_dev, root.st_ino)))
        for role in ('countrycode', 'pvmfw'):
            image = (self.output / 'images' / (role + '.img')).stat()
            self.assertEqual(1, calls.count((image.st_dev, image.st_ino)))
        self.assertTrue(all(result['publication'].values()))
        checkpoint = json.loads((self.output / 'receipt.json').read_text())
        self.assertEqual('verified-before-publication', checkpoint['status'])
        self.assertEqual('prepublication-byte-verification', checkpoint['receipt_scope'])
        self.assertFalse(checkpoint['publication_durability_claimed'])
        self.assertTrue(checkpoint['successful_publication_requires_returned_result'])

    def test_directory_sync_failures_never_return_success_or_delete_outputs(self):
        original = materializer._sync_directory
        for selected in ('images', 'provenance', 'staging-root', 'published-root', 'parent'):
            with self.subTest(selected=selected):
                destination = self.output_parent / ('sync-failure-' + selected)
                called = False

                def sync(path, identity):
                    nonlocal called
                    matches = (path == destination if selected == 'published-root'
                               else path == destination.parent if selected == 'parent'
                               else path.name.startswith('.' + destination.name + '.incomplete-')
                               if selected == 'staging-root' else path.name == selected)
                    if matches:
                        called = True
                        raise OSError('inert directory sync failure')
                    return original(path, identity)

                with mock.patch.object(materializer, '_sync_directory', side_effect=sync):
                    with self.assertRaises(OSError):
                        self.run_materialize(output_dir=destination)
                self.assertTrue(called)
                if selected in ('published-root', 'parent'):
                    self.assertTrue(destination.is_dir())
                    checkpoint = json.loads((destination / 'receipt.json').read_text())
                    self.assertFalse(checkpoint['publication_durability_claimed'])
                    self.assertEqual('verified-before-publication', checkpoint['status'])
                else:
                    self.assertFalse(destination.exists())
                    self.assertTrue(list(self.output_parent.glob('.' + destination.name + '.incomplete-*')))
                self.assertEqual(self.archive_identity, fixtures.identity(self.archive.read_bytes()))

    def test_cli_postrename_sync_failure_preserves_checkpoint_and_reports_blocked(self):
        original = materializer._sync_directory

        def sync(path, identity):
            if path == self.output.parent:
                raise OSError('inert postrename parent sync failure')
            return original(path, identity)

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(materializer, '_sync_directory', side_effect=sync), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            code = materializer.main(self.cli_arguments())
        self.assertEqual(2, code)
        self.assertEqual('', stdout.getvalue())
        self.assertEqual('blocked', json.loads(stderr.getvalue())['status'])
        self.assertTrue(self.output.is_dir())
        checkpoint = json.loads((self.output / 'receipt.json').read_text())
        self.assertFalse(checkpoint['publication_durability_claimed'])
        self.assertEqual('verified-before-publication', checkpoint['status'])

    def test_budget_rejects_short_or_excessive_writes(self):
        class Short(io.BytesIO):
            def write(self, raw):
                return super().write(raw[:-1])

        budget = materializer._OutputBudget(8)
        with self.assertRaises(materializer.MaterializationError):
            budget.write(Short(), b'abcd')
        self.assertEqual(8, budget.remaining)
        stream = io.BytesIO()
        with self.assertRaises(materializer.MaterializationError):
            budget.write(stream, b'ninebytes')
        self.assertEqual(b'', stream.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
