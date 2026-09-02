#!/usr/bin/env python3
"""Materialize exact inventoried IMAGES inputs for the existing Mac signer.

Only fresh private image copies and bounded JSON provenance are written.
This does not establish image validity or a bootable ROM. No signing, image reconstruction, native
tool, guest, key/config access, ZIP repack or phone operation is provided.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import uuid
import zipfile
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if __package__:
    from . import target_files_avb_inventory as inventory
    from . import target_files_archive_copy as archive_copy
    from .artifact_files import publish_new_directory
else:
    import target_files_avb_inventory as inventory
    import target_files_archive_copy as archive_copy
    from artifact_files import publish_new_directory

signing, avb = inventory.signing, inventory.avb
RAW_ROLES = frozenset(('countrycode', 'pvmfw'))
DATA_ROLES = frozenset(('boot', 'dtbo', 'init_boot', 'mi_ext', 'odm', 'product',
                       'recovery', 'system', 'system_dlkm', 'system_ext', 'vendor',
                       'vendor_boot', 'vendor_dlkm'))
PUBLIC_PINS = {
    'scripts/target_files_avb_inventory.py': ('160cf1c5c7abe8072956affc3cc6ebe3a55ce95705ca55c9c3c8cf9c4b82021b', 28544),
    'scripts/avb_signing.py': ('ed87a8aa0ba7bbcf5bcc066cb03206dd5604c8e64379dbbd176260a0825ba1c3', 46629),
    'scripts/avb_image_set.py': ('08dede641768c043e050e103b852503b2bc5af310aba3bef1d1f1824b7f9f80c', 41370),
    'scripts/artifact_files.py': ('ddc784d1c378510c66621d95af267790ab7fb1965ac5951926b471e897bd6343', 1586),
    'scripts/target_files_archive_copy.py': ('1ae8ba5c8721ddc44807c825a9044a7010a11abf8c8bedea51b5318e08469650', 40588),
}
SPACE_CHECK_BYTES = archive_copy.SPACE_CHECK_BYTES
FALSE_SCOPE = {name: False for name in (
    'image_format_verified', 'signatures_verified', 'complete_chain_verified',
    'fec_payload_verified', 'source_provenance_semantics_verified',
    'target_files_compatibility_verified', 'physical_partition_fit_verified',
    'runtime_verified', 'complete_rom_ready', 'native_commands_run',
    'private_key_or_local_config_accessed', 'guest_accessed', 'phone_accessed',
    'archive_repacked', 'source_or_android_output_modified')}


class MaterializationError(ValueError):
    pass


def require(value, message):
    if not value:
        raise MaterializationError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def same(actual, expected, message):
    require(encoded(actual) == encoded(expected), message)


def selected(row):
    return {key: row[key] for key in ('sha256', 'size_bytes')}


def contracts():
    value = signing.load_contract()
    require(value[1] == '8749a855328acac6c63d62b45e989e3e1d354aaaf86b754940dfe00caa257c3c'
            and value[3] == '14f58671ecd15a1913ba5e1dd7767d0ebf163fd02d30f7fb4130e734790f3567',
            'only the existing signing and verifier profiles are supported')
    return value


class _OutputBudget:
    """Account for this fixed bundle, retaining the existing copier's reserve."""
    def __init__(self, maximum):
        require(type(maximum) is int and 0 < maximum <= inventory.MAX_ARCHIVE,
                'materialized output budget exceeds its bound')
        self.remaining = maximum
        self.since_check = 0

    def check(self, descriptor):
        require(archive_copy._available(descriptor) >= self.remaining + avb.RESERVE_BYTES,
                'materialization free-space reserve was crossed')
        self.since_check = 0

    def consume(self, count):
        require(type(count) is int and 0 <= count <= self.remaining, 'materialization exceeds output budget')
        self.remaining -= count
        self.since_check += count

    def write(self, stream, raw):
        require(len(raw) <= self.remaining, 'materialization exceeds output budget')
        require(stream.write(raw) == len(raw), 'short materialization write')
        self.consume(len(raw))
        if self.since_check >= SPACE_CHECK_BYTES:
            stream.flush()
            self.check(stream.fileno())


def _write(path, raw, budget):
    require(0 < len(raw) <= avb.MAX_TEXT, 'generated materialization record exceeds bound')
    with avb.envelope._parent_directory(path) as parent:
        budget.check(parent)
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            budget.write(stream, raw)
            stream.flush()
            os.fsync(stream.fileno())
            budget.check(stream.fileno())
    return avb._identity(raw)


def _copy_member(archive, info, destination, expected, maximum, budget):
    """Use the inventory's strict envelope/DEFLATE guards, without buffering an image."""
    require(inventory._regular_member(info), 'selected member is not regular')
    require(not info.flag_bits & (1 | 64) and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'unsupported selected ZIP encoding')
    require(0 < info.file_size == expected['size_bytes'] <= maximum, 'member size differs')
    start = inventory._selected_span(archive, info)
    if info.compress_type == zipfile.ZIP_STORED:
        require(info.compress_size == info.file_size, 'stored member size differs')
    digest, count, crc = hashlib.sha256(), 0, 0
    with avb.envelope._parent_directory(destination) as parent:
        budget.check(parent)
        fd = os.open(destination.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as output, archive.open(info, 'r') as source:
            while part := source.read(min(avb.CHUNK, info.file_size - count + 1)):
                count += len(part)
                require(count <= info.file_size, 'selected image grew beyond bound')
                digest.update(part)
                crc = zlib.crc32(part, crc)
                budget.write(output, part)
            output.flush()
            os.fsync(output.fileno())
            budget.check(output.fileno())
    require(count == info.file_size and crc == info.CRC, 'selected size/CRC differs')
    if info.compress_type == zipfile.ZIP_DEFLATED:
        inventory._deflate_complete(archive.fp, start, info)
    same({'sha256': digest.hexdigest(), 'size_bytes': count}, selected(expected), 'extracted image differs from admitted inventory')
    avb._rehash(destination, expected)


def _sync_image(path, expected, budget):
    """The unchanged raw copier closes its output but does not fsync it."""
    with avb._input(path, expected['size_bytes']) as (stream, info):
        require(info.st_size == expected['size_bytes'] and stat.S_IMODE(info.st_mode) == 0o600,
                'raw output size or private mode differs')
        os.fsync(stream.fileno())
        budget.check(stream.fileno())


def _directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode)


def _sync_directory(path, expected_identity):
    """Sync a selected real directory; unsupported/failed syncs remain errors."""
    with avb.envelope._parent_directory(path) as parent:
        initial = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        require(stat.S_ISDIR(initial.st_mode) and _directory_identity(initial) == expected_identity,
                'directory changed before synchronization')
        descriptor = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            before = avb._signature(initial)
            require(avb._signature(os.fstat(descriptor)) == before, 'directory replaced before synchronization')
            os.fsync(descriptor)
            require(before == avb._signature(os.fstat(descriptor))
                    == avb._signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)),
                    'directory changed during synchronization')
        finally:
            os.close(descriptor)


def _verify_files(directory, manifest_raw, expected_manifest, expected_files, contract, contract_sha, profile):
    """Independent readback through the existing signer schema, plus every output byte."""
    root_info = directory.lstat()
    require(stat.S_ISDIR(root_info.st_mode) and stat.S_IMODE(root_info.st_mode) == 0o700,
            'materialization directory is not private')
    same(avb._identity(signing._json_file(directory / 'input-manifest.json', avb.MAX_TEXT)), avb._identity(manifest_raw), 'materialized manifest changed')
    manifest, unused = signing.load_input(directory / 'input-manifest.json', avb._sha(manifest_raw), contract, contract_sha, profile)
    require(set(manifest['images']) == DATA_ROLES | RAW_ROLES, 'signer needs exactly fifteen materialized images')
    same(avb._json(manifest_raw), expected_manifest, 'signer manifest shape differs')
    wanted = set(expected_files) | {'input-manifest.json'}
    actual = set()
    signatures = {'.': avb._signature(directory.lstat())}
    for path in directory.rglob('*'):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1), 'output alias or special file')
        if stat.S_ISDIR(info.st_mode):
            require(stat.S_IMODE(info.st_mode) == 0o700, 'output directory mode is not private')
            require(path.relative_to(directory).as_posix() in ('images', 'provenance'), 'unexpected output directory')
            signatures[path.relative_to(directory).as_posix()] = avb._signature(info)
        if stat.S_ISREG(info.st_mode):
            require(stat.S_IMODE(info.st_mode) == 0o600, 'output file mode is not private')
            actual.add(path.relative_to(directory).as_posix())
    same(sorted(actual), sorted(wanted), 'unexpected or absent materialized file')
    for relative, identity in {**expected_files, 'input-manifest.json': avb._identity(manifest_raw)}.items():
        signature = avb._file_signature(directory / relative, identity['size_bytes'])
        avb._rehash(directory / relative, identity, signature)
        signatures[relative] = signature
    for role, row in manifest['images'].items():
        require(row['path'] == directory / 'images' / (role + '.img'), 'signer image escapes exact output role')
        same(selected(row), expected_files['images/' + role + '.img'], 'signer image identity differs')
    for row in manifest['source_records']:
        require(row['path'].is_relative_to(directory), 'materialized provenance escapes output')
        require(type(avb._json(signing._json_file(row['path'], signing.MAX_TEXT, row))) is dict, 'provenance body is not a JSON object')
    return signatures


def _final_signatures(directory, output_signatures, source_guards):
    """Close the large source-rehash window without rereading image payloads."""
    require(all(stat.S_ISDIR(path.lstat().st_mode) for path in directory.parents), 'staging ancestor changed')
    root = directory.lstat()
    require(stat.S_ISDIR(root.st_mode) and stat.S_IMODE(root.st_mode) == 0o700,
            'staging root no longer has its private mode')
    actual = {'.': avb._signature(root)}
    for path in directory.rglob('*'):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1), 'staging topology changed')
        require(stat.S_IMODE(info.st_mode) == (0o700 if stat.S_ISDIR(info.st_mode) else 0o600),
                'staging entry no longer has its private mode')
        actual[path.relative_to(directory).as_posix()] = avb._signature(info)
    same(actual, output_signatures, 'verified staging file/directory identity changed')
    for path, (pin, signature, unused) in source_guards.items():
        require(avb._file_signature(path, pin['size_bytes']) == signature, 'source changed after final content rehash')


def materialize(target_files, expected_archive, inventory_record, expected_inventory_sha256,
                retained_manifest, expected_retained_sha256, output_dir, artifact_set_id,
                *, source_records=()):
    """No defaults for future inputs: all archive/inventory/raw selections are explicit."""
    contract, contract_sha, profile, profile_sha = contracts()
    require(set(contract['input_partitions']) == DATA_ROLES | RAW_ROLES and set(profile['raw_leaf_partitions']) == RAW_ROLES, 'role topology differs')
    avb._identity_spec(expected_archive)
    avb._digest(expected_inventory_sha256)
    avb._digest(expected_retained_sha256)
    require(type(artifact_set_id) is str and avb.re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', artifact_set_id), 'explicit artifact-set id required')
    require(type(source_records) in (list, tuple) and len(source_records) <= 61, 'too many additional source records')
    target_files, inventory_record, retained_manifest, output_dir = [avb.envelope._absolute_path(path) for path in (target_files, inventory_record, retained_manifest, output_dir)]
    allowed = signing.ROOT / contract['output_root']
    require(output_dir.is_relative_to(allowed) and output_dir != allowed and not os.path.lexists(output_dir), 'fresh ignored signer input directory required')
    require(all(stat.S_ISDIR(path.lstat().st_mode) for path in output_dir.parents), 'output parent must already exist without symlinks')
    parent_state = output_dir.parent.stat()
    guards = {}
    def remember(path, pin, maximum, *, signature=None):
        path = avb.envelope._absolute_path(path)
        avb._identity_spec(selected(pin))
        require(path not in guards, 'duplicate selected input path')
        current = avb._file_signature(path, maximum)
        require(signature is None or current == signature, 'input changed after its guarded read')
        guards[path] = (selected(pin), current, maximum)
        return path
    def recheck():
        for path, (pin, signature, unused) in guards.items():
            avb._rehash(path, pin, signature)
        same(contracts()[1::2], (contract_sha, profile_sha), 'public profiles changed')
        current = output_dir.parent.lstat()
        require(stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino, current.st_mode) == (parent_state.st_dev, parent_state.st_ino, parent_state.st_mode), 'output parent changed')
    implementation = {}
    for name, (sha, size) in PUBLIC_PINS.items():
        pin = {'sha256': sha, 'size_bytes': size}
        remember(ROOT / name, pin, avb.MAX_TEXT)
        avb._rehash(ROOT / name, pin)
        implementation[name] = pin
    own_pin = signing._identity(Path(__file__), avb.MAX_TEXT)
    remember(Path(__file__), own_pin, avb.MAX_TEXT)
    remember(target_files, expected_archive, inventory.MAX_ARCHIVE)
    inventory_signature = avb._file_signature(inventory_record, avb.MAX_TEXT)
    invraw = signing._json_file(inventory_record, avb.MAX_TEXT)
    require(avb._sha(invraw) == expected_inventory_sha256, 'inventory record digest differs')
    remember(inventory_record, avb._identity(invraw), avb.MAX_TEXT, signature=inventory_signature)
    supplied = avb._json(invraw)
    retained_signature = avb._file_signature(retained_manifest, avb.MAX_TEXT)
    observed = inventory.inspect_target_files(target_files, expected_archive,
        retained_input_manifest=retained_manifest, expected_retained_manifest_sha256=expected_retained_sha256)
    require(observed['status'] == 'complete' and observed['complete_input_inventory'] is True and observed['complete_zip_role_inventory'] is True and observed['inputs_unchanged'] is True and observed['errors'] == [], 'fully replayed inventory is required')
    same(supplied, observed, 'supplied inventory is not the actual current inventory')
    require(set(observed['final_images']) == DATA_ROLES and set(observed['retained_inputs']) == RAW_ROLES, 'inventory image role set differs')
    retained, retained_raw, unused, raw_signatures = inventory._retained(retained_manifest, expected_retained_sha256, contract, contract_sha, profile)
    remember(retained_manifest, avb._identity(retained_raw), avb.MAX_TEXT, signature=retained_signature)
    records = [retained['source_records'][0]]
    for source in source_records:
        avb._identity_spec(source, path=True)
        require(Path(source['path']).suffix == '.json' and source['size_bytes'] <= signing.MAX_TEXT, 'source record must be bounded JSON')
        records.append(source)
    record_bodies = []
    for record in records:
        path = remember(record['path'], record, avb.MAX_TEXT)
        body = signing._json_file(path, avb.MAX_TEXT, record)
        require(type(avb._json(body)) is dict, 'source record must parse as a strict JSON object')
        record_bodies.append(body)
    for role in RAW_ROLES:
        row = retained['images'][role]
        remember(row['path'], row, profile['image_budgets'][role])
        require(guards[row['path']][1] == raw_signatures[role], 'retained input replaced since inventory')
    recheck()
    size = sum(row['size_bytes'] for row in observed['final_images'].values()) + sum(row['size_bytes'] for row in retained['images'].values())
    # Actual copied JSON plus three individually bounded generated records.
    maximum = size + len(invraw) + len(retained_raw) + sum(map(len, record_bodies)) + 3 * avb.MAX_TEXT
    budget = _OutputBudget(maximum)
    require(shutil.disk_usage(output_dir.parent).free >= maximum + avb.RESERVE_BYTES, 'insufficient private materialization space')
    staging = output_dir.parent / ('.' + output_dir.name + '.incomplete-' + uuid.uuid4().hex)
    files = {}
    with signing.io._private_creation():
        signing.io._mkdir(staging)
        signing.io._mkdir(staging / 'images')
        signing.io._mkdir(staging / 'provenance')
        with avb._input(target_files, inventory.MAX_ARCHIVE) as (stream, info):
            require(avb._signature(info) == guards[target_files][1], 'archive replaced before extraction')
            same(inventory._stream_identity(stream, info.st_size), expected_archive, 'archive changed before extraction')
            bounds = inventory._zip_bounds(stream, info.st_size)
            with zipfile.ZipFile(stream, 'r') as archive:
                members = inventory._members(archive, bounds, DATA_ROLES | {'vbmeta', 'vbmeta_system'})
                for role in sorted(DATA_ROLES):
                    name = 'IMAGES/' + role + '.img'
                    require(name in members and observed['final_images'][role]['member'] == name, 'exact IMAGES entry required')
                    _copy_member(archive, members[name], staging / 'images' / (role + '.img'), observed['final_images'][role], profile['image_budgets'][role], budget)
                    files['images/' + role + '.img'] = selected(observed['final_images'][role])
            same(inventory._stream_identity(stream, info.st_size), expected_archive, 'archive changed during extraction')
        # The archive's held-FD/parent guard has completed before manifest creation.
        for role in sorted(RAW_ROLES):
            row = retained['images'][role]
            destination = staging / 'images' / (role + '.img')
            with avb.envelope._parent_directory(destination) as parent:
                budget.check(parent)
                avb._copy_image(row['path'], destination, row, profile['image_budgets'][role])
                budget.consume(row['size_bytes'])
                _sync_image(destination, row, budget)
            files['images/' + role + '.img'] = selected(row)
        for name, raw in [('inventory.json', invraw), ('retained-manifest.json', retained_raw),
                          *[(('factory-extraction.json' if i == 0 else f'source-{i:03}.json'), raw) for i, raw in enumerate(record_bodies)]]:
            files['provenance/' + name] = _write(staging / 'provenance' / name, raw, budget)
        derivation = {'schema_version': 1, 'operation': 'materialize-exact-nezha-signer-inputs-v1',
            'artifact_set_id': artifact_set_id, 'archive': {'path': str(target_files), **expected_archive},
            'inventory': {'path': str(inventory_record), **avb._identity(invraw)},
            'retained_manifest': {'path': str(retained_manifest), **avb._identity(retained_raw)},
            'contracts': observed['contracts'], 'implementation': implementation, 'workflow': own_pin,
            'extracted_members': {role: observed['final_images'][role] for role in sorted(DATA_ROLES)},
            'retained_inputs': observed['retained_inputs'], 'files': files.copy(),
            'scope': {**FALSE_SCOPE, 'image_bytes_materialized': True, 'signer_input_schema_verified': False},
            'source_records_are_hash_bound_not_semantically_verified': True}
        files['materialization.json'] = _write(staging / 'materialization.json', encoded(derivation), budget)
        sources = ['materialization.json', 'provenance/inventory.json', 'provenance/factory-extraction.json']
        sources += [f'provenance/source-{i:03}.json' for i in range(1, len(record_bodies))]
        manifest = {'schema_version': 1, 'contract_id': contract['contract_id'], 'contract_sha256': contract_sha,
            'artifact_set_id': artifact_set_id,
            'images': {role: {'path': 'images/' + role + '.img', **files['images/' + role + '.img']} for role in sorted(DATA_ROLES | RAW_ROLES)},
            'source_records': [{'path': name, **files[name]} for name in sources]}
        manifest_raw = encoded(manifest)
        _write(staging / 'input-manifest.json', manifest_raw, budget)
        _verify_files(staging, manifest_raw, manifest, files, contract, contract_sha, profile)
        recheck()
        result = {'schema_version': 1, 'operation': 'verify-materialized-nezha-signer-inputs-v1', 'status': 'verified-before-publication',
            'artifact_set_id': artifact_set_id, 'input_manifest': {'path': 'input-manifest.json', **avb._identity(manifest_raw)},
            'materialization': {'path': 'materialization.json', **files['materialization.json']},
            'image_count': 15, 'extracted_image_count': 13, 'retained_image_count': 2,
            'inputs_unchanged': True, 'output_bytes_independently_rehashed': True,
            'receipt_scope': 'prepublication-byte-verification', 'publication_durability_claimed': False,
            'successful_publication_requires_returned_result': True,
            'scope': {**FALSE_SCOPE, 'image_bytes_materialized': True, 'signer_input_schema_verified': True},
            'files': {**files, 'input-manifest.json': avb._identity(manifest_raw)}}
        receipt_raw = encoded(result)
        _write(staging / 'receipt.json', receipt_raw, budget)
        final_files = {**files, 'receipt.json': avb._identity(receipt_raw)}
        output_signatures = _verify_files(staging, manifest_raw, manifest, final_files, contract, contract_sha, profile)
        for relative in ('images', 'provenance', '.'):
            signature = output_signatures[relative]
            _sync_directory(staging if relative == '.' else staging / relative,
                            (signature[0], signature[1], signature[5]))
        recheck()
        _final_signatures(staging, output_signatures, guards)
        # Existing exclusive publisher: no replacement and no non-atomic fallback.
        publish_new_directory(staging, output_dir)
        root_signature = output_signatures['.']
        _sync_directory(output_dir, (root_signature[0], root_signature[1], root_signature[5]))
        _sync_directory(output_dir.parent, _directory_identity(parent_state))
        published_root = output_dir.lstat()
        require(_directory_identity(published_root) == (root_signature[0], root_signature[1], root_signature[5]),
                'published directory identity differs')
        # Rename may update the root directory's ctime; child identities must
        # remain exactly those independently read back before publication.
        published_signatures = {**output_signatures, '.': avb._signature(published_root)}
        _final_signatures(output_dir, published_signatures, guards)
    return {'output_directory': str(output_dir), 'receipt': {'path': str(output_dir / 'receipt.json'), **avb._identity(receipt_raw)},
            'input_manifest': {'path': str(output_dir / 'input-manifest.json'), **avb._identity(manifest_raw)},
            'status': 'materialized-inputs-only', 'scope': result['scope'],
            'publication': {'data_files_synced': True, 'directories_synced_before_and_after_rename': True,
                            'parent_directory_synced': True, 'final_file_states_rechecked': True}}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target-files', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--expected-size-bytes', type=int, required=True)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--expected-inventory-sha256', required=True)
    p.add_argument('--retained-input-manifest', type=Path, required=True)
    p.add_argument('--expected-retained-manifest-sha256', required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--artifact-set-id', required=True)
    p.add_argument('--source-record', nargs=3, action='append', metavar=('JSON_PATH', 'SHA256', 'BYTES'), default=[])
    a = p.parse_args(argv)
    try:
        value = materialize(a.target_files, {'sha256': a.expected_sha256, 'size_bytes': a.expected_size_bytes},
            a.inventory, a.expected_inventory_sha256, a.retained_input_manifest, a.expected_retained_manifest_sha256,
            a.output_dir, a.artifact_set_id, source_records=[{'path': path, 'sha256': sha, 'size_bytes': int(size)} for path, sha, size in a.source_record])
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile, zlib.error) as error:
        print(json.dumps({'status': 'blocked', 'error_type': type(error).__name__, 'scope': FALSE_SCOPE}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
