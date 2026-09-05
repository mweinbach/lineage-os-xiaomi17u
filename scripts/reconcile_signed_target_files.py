#!/usr/bin/env python3
"""Reconcile an already signed Nezha image set into a fresh target-files ZIP.

Actual inputs are mandatory. This never signs or selects private key material,
rebuilds a filesystem, invokes broad releasetools packaging, or accesses a VM.
It repeats the maintained public-only complete AVB verification before copying.
The output is an image-reconciled archive, not OTA, super or device admission.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys
import uuid
import zipfile
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

if __package__:
    from . import target_files_avb_inventory as inventory
    from .artifact_files import publish_new_directory
    from .target_files_archive_copy import inspect_dtbo_alias, rewrite_archive
else:
    import target_files_avb_inventory as inventory
    from artifact_files import publish_new_directory
    from target_files_archive_copy import inspect_dtbo_alias, rewrite_archive

signing, avb = inventory.signing, inventory.avb
OPERATION = 'reconcile-nezha-signed-target-files-v1'
CHANGED_ROLES = frozenset(('boot', 'vbmeta', 'vbmeta_system'))
DTBO_ALIAS_MEMBER = 'PREBUILT_IMAGES/dtbo.img'
RAW_ROLES = frozenset(('countrycode', 'pvmfw'))
DATA_ROLES = frozenset(signing.INPUTS) - RAW_ROLES
RECORD_FIELDS = frozenset(('target_files', 'inventory', 'retained_input_manifest',
                          'signing_preparation', 'signing_receipt', 'verification_manifest'))
PUBLIC_PINS = {
    'scripts/target_files_avb_inventory.py': ('893778a88df0badb6f27db0f88be5aff9885cb8f3111f06e062e5d7f0d7f89e4', 28614),
    'scripts/avb_signing.py': ('e0afd0d9f86560306117aa43a5487e036751c2824e24b17080da2bb1b30cddb8', 46523),
    'scripts/avb_image_set.py': ('f70c6f44b1c0cf02803a199f00331154fd51ab15351f368f38850d358a4d1bea', 43864),
    'scripts/artifact_files.py': ('ddc784d1c378510c66621d95af267790ab7fb1965ac5951926b471e897bd6343', 1586),
}
FALSE_SCOPE = {name: False for name in (
    'complete_rom_ready', 'ota_package_ready', 'super_verified',
    'fec_payload_verified', 'source_provenance_semantics_verified',
    'target_files_compatibility_verified', 'physical_partition_fit_verified',
    'device_rollback_compatibility_verified', 'hardware_verified',
    'apk_apex_or_payload_signing_performed', 'private_key_or_local_config_accessed',
    'guest_accessed', 'phone_accessed', 'original_source_or_android_output_modified',
    'signing_metadata_reconciled', 'generic_resigning_supported')}


class ReconciliationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReconciliationError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def same(actual, expected, message):
    require(encoded(actual) == encoded(expected), message)


def selected(row):
    return {name: row[name] for name in ('sha256', 'size_bytes')}


def controls():
    result = signing.load_contract()
    require(result[1] == '8749a855328acac6c63d62b45e989e3e1d354aaaf86b754940dfe00caa257c3c'
            and result[3] == 'c5dbd4055c904422581ad511d34ba143672683a54aea3390c0581a4af321ba37',
            'only the reviewed signing and seventeen-image contracts are supported')
    return result


def write_new(path, raw):
    with avb.envelope._parent_directory(path) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return avb._identity(raw)


class Guards:
    def __init__(self):
        self.files = {}

    def remember(self, path, identity, maximum, *, signature=None):
        path = avb.envelope._absolute_path(path)
        pin = selected(identity)
        avb._identity_spec(pin)
        require(pin['size_bytes'] <= maximum, 'selected input exceeds its bound')
        current = avb._file_signature(path, maximum)
        require(signature is None or signature == current, 'input changed after its header check')
        signature = current
        avb._rehash(path, pin, signature)
        if path in self.files:
            same(self.files[path][:2], (pin, signature), 'same path selects different input state')
        self.files[path] = (pin, signature, maximum)
        return path

    def json(self, path, identity):
        path = avb.envelope._absolute_path(path)
        signature = avb._file_signature(path, signing.MAX_TEXT)
        # Keep the maintained one-byte JSON opener check ahead of hashing.
        # A PEM selected by mistake must never have its body read as a record.
        raw = signing._json_file(path, signing.MAX_TEXT, identity)
        value = avb._json(raw)
        require(type(value) is dict, 'selected JSON must contain an object')
        self.remember(path, identity, signing.MAX_TEXT, signature=signature)
        return value, raw

    def archive(self, path, identity):
        path = avb.envelope._absolute_path(path)
        with avb._input(path, inventory.MAX_ARCHIVE) as (stream, info):
            signature = avb._signature(info)
            require(stream.read(4) == b'PK\x03\x04', 'expected a native target-files ZIP header')
        return self.remember(path, identity, inventory.MAX_ARCHIVE, signature=signature)

    def public_key(self, path, identity):
        path = avb.envelope._absolute_path(path)
        signature = avb._file_signature(path, avb.MAX_PUBLIC_KEY)
        avb._public_pem(path, identity)
        return self.remember(path, identity, avb.MAX_PUBLIC_KEY, signature=signature)

    def recheck(self):
        for path, (pin, signature, _) in self.files.items():
            avb._rehash(path, pin, signature)

    def signatures(self):
        for path, (pin, signature, _) in self.files.items():
            require(avb._file_signature(path, pin['size_bytes']) == signature,
                    'input replaced after its final content check')


def _verified_record(value, manifest, manifest_sha, profile_sha, contract):
    require(value['operation'] == 'verify-image-set' and value['status'] == 'verified'
            and value['complete_chain_verified'] is True and value['native_commands_run'] is True
            and value['inputs_unchanged'] is True and value['missing_partitions'] == []
            and value['artifacts_without_native_payload_verification'] == []
            and set(value['verified_artifacts']) == avb.SIGNED
            and len(value['verified_artifacts']) == len(avb.SIGNED)
            and value['manifest_sha256'] == manifest_sha
            and value['profile_sha256'] == profile_sha
            and value['artifact_set_id'] == manifest['artifact_set_id']
            and set(value['images']) == avb.PARTITIONS,
            'a complete verification of the selected image set is required')
    same({name: row['identity'] for name, row in value['images'].items()},
         {name: selected(row) for name, row in manifest['images'].items()},
         'verified image identities differ from the selected manifest')
    same(value['public_keys'], {
        name: {**contract['public_key'], 'avb_sha256': contract['avb_public_key_sha256']}
        for name in avb.SIGNED}, 'verified public keys differ from the approved signing roles')
    for field in ('complete_rom_ready', 'oem_trust_established',
                  'device_rollback_compatibility_verified', 'physical_partition_fit_verified',
                  'fec_payload_verified', 'phone_accessed', 'signing_performed'):
        require(value[field] is False, 'verification receipt overclaims its scope')


def _blob(raw):
    require(len(raw) >= 256 and raw[:4] == b'AVB0', 'standalone AVB header is required')
    auth, aux = struct.unpack_from('>QQ', raw, 12)
    end = 256 + auth + aux
    require(256 <= end <= avb.MAX_VBMETA and end <= len(raw)
            and not any(raw[end:]), 'standalone AVB extent or padding differs')
    value = raw[:end]
    avb.parse_vbmeta(value)
    return value


def image_blob(path, role, budget):
    metadata = avb.read_image_metadata(path, role, budget)
    with avb._input(path, budget) as (stream, info):
        if metadata['footer']:
            footer = metadata['footer']
            stream.seek(footer['vbmeta_offset'])
            raw = stream.read(footer['vbmeta_size'])
            require(len(raw) == footer['vbmeta_size'], 'truncated AVB child metadata')
            avb.parse_vbmeta(raw)
            return raw
        require(info.st_size <= 131072, 'standalone AVB image exceeds its bound')
        return _blob(stream.read(info.st_size))


def digest_from_blobs(blobs):
    """Independent bounded equivalent of the pinned tool's immediate-child order."""
    require(set(blobs) == avb.SIGNED, 'exact four signed metadata roles required')
    root = avb.parse_vbmeta(blobs['vbmeta'])
    children = [row['partition'] for row in root['descriptors'] if row['kind'] == 'chain']
    require(len(children) == 3 and set(children) == avb.SIGNED - {'vbmeta'},
            'root AVB chain topology differs')
    h = hashlib.sha256(blobs['vbmeta'])
    for role in children:
        child = avb.parse_vbmeta(blobs[role])
        require(not any(row['kind'] == 'chain' for row in child['descriptors']),
                'nested AVB chains are outside the selected profile')
        h.update(blobs[role])
    return h.hexdigest().encode() + b'\n'


def native_digest(work, manifest, profile, expected):
    """Use existing bounded native runner and public tools, without a key selector."""
    native = signing.Native(work, profile, manifest['tools']['avbtool'], manifest['tools']['openssl'])
    destination = work / 'vbmeta_digest.txt'
    native.call('calculate-vbmeta-digest', native.avb(
        'calculate_vbmeta_digest', '--image', manifest['images']['vbmeta']['path'],
        '--hash_algorithm', 'sha256', '--format', 'hex', '--output', destination))
    raw = avb._small(destination, 65)
    require(re.fullmatch(rb'[0-9a-f]{64}\n', raw) is not None and raw == expected,
            'native vbmeta digest differs from independent metadata calculation')
    require(native.records[-1]['returncode'] == 0
            and native.records[-1]['stdout'] == avb._identity(b'')
            and native.records[-1]['stderr'] == avb._identity(b''),
            'unexpected native digest output or diagnostic')
    native.check()
    return raw, {'tools': native.identities, 'native_results': native.records,
                 'digest': avb._identity(raw)}, native


def admit_misc_info(raw):
    """Admit only the captured ordinary A/B image flow; preserve its recipe."""
    consumed = {'ab_update', 'allow_non_ab', 'boot_images', 'avb_enable',
                'avb_building_vbmeta_image'}
    values = {}
    for line in inventory._text(raw).splitlines():
        line = line.strip(' \t')
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        require(separator and re.fullmatch(r'[a-zA-Z0-9_.-]+', key), 'invalid build metadata key')
        if key in consumed:
            require(key not in values, 'duplicate consumed build metadata key')
            values[key] = value.strip(' \t')
    require(all(values.get(key) == 'true' for key in
                ('ab_update', 'avb_enable', 'avb_building_vbmeta_image')),
            'ordinary A/B full-root AVB metadata is required')
    require('allow_non_ab' not in values or values['allow_non_ab'] == 'false',
            'non-A/B delivery is outside this adapter')
    require('boot_images' not in values or values['boot_images'].split() == ['boot.img'],
            'only the canonical single boot image is supported')
    return values


def _zip_old_digest(target_files, archive_pin, original, profile):
    with avb._input(target_files, inventory.MAX_ARCHIVE) as (stream, info):
        same(inventory._stream_identity(stream, info.st_size), archive_pin, 'original archive changed')
        bounds = inventory._zip_bounds(stream, info.st_size)
        with zipfile.ZipFile(stream) as archive:
            members = inventory._members(archive, bounds, DATA_ROLES | {'vbmeta', 'vbmeta_system'})
            _, misc = inventory._member_identity(archive, members['META/misc_info.txt'],
                                                  inventory.MAX_METADATA, collect=True)
            admit_misc_info(misc)
            blobs = {}
            for role in ('vbmeta', 'vbmeta_system'):
                _, raw = inventory._member_identity(archive, members['IMAGES/' + role + '.img'],
                                                     avb.image_budget(profile, role), collect=True)
                blobs[role] = _blob(raw)
            for role in ('boot', 'recovery'):
                blobs[role] = image_blob(original['images'][role]['path'], role, avb.image_budget(profile, role))
            _, before = inventory._member_identity(archive, members['META/vbmeta_digest.txt'], 65, collect=True)
            require(re.fullmatch(rb'[0-9a-f]{64}\n', before) is not None
                    and before == digest_from_blobs(blobs), 'original target-files vbmeta digest is stale or malformed')
            return before


def _topology(directory):
    result = {'.': avb._signature(directory.lstat())}
    for path in directory.rglob('*'):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'output topology contains a link or nonregular object')
        result[path.relative_to(directory).as_posix()] = avb._signature(info)
    return result


def parent_identity(path):
    value = path.lstat()
    require(stat.S_ISDIR(value.st_mode), 'output parent is no longer a directory')
    return value.st_dev, value.st_ino, value.st_mode


def preflight_output(value, contract, archive_size, profile):
    output = avb.envelope._absolute_path(value)
    allowed = signing.ROOT / contract['output_root']
    require(output.is_relative_to(allowed) and output != allowed and not os.path.lexists(output),
            'fresh ignored artifacts/avb/nezha output directory required')
    require(all(stat.S_ISDIR(path.lstat().st_mode) for path in output.parents),
            'output parent must exist without symlinks')
    # This is an early floor before public verification. The streamed copier
    # separately admits a conservative bound for every recompressed member.
    require(shutil.disk_usage(output.parent).free >= archive_size
            + 3 * profile['image_budgets']['boot'] + avb.RESERVE_BYTES,
            'insufficient space for fresh archive')
    return output, parent_identity(output.parent)


def reconcile(request_path, expected_sha256, output_dir):
    """No default or inferred archive, image, key, signing or receipt selectors."""
    contract, contract_sha, profile, profile_sha = controls()
    guards = Guards()
    request_path = avb.envelope._absolute_path(request_path)
    raw = signing._json_file(request_path, signing.MAX_TEXT)
    avb._digest(expected_sha256)
    require(avb._sha(raw) == expected_sha256, 'request digest differs')
    request, _ = guards.json(request_path, avb._identity(raw))
    avb._keys(request, RECORD_FIELDS | {'schema_version', 'operation'}, 'reconciliation request')
    require(type(request['schema_version']) is int and request['schema_version'] == 1
            and request['operation'] == OPERATION, 'unsupported reconciliation request')
    avb._identity_spec(request['target_files'], path=True)
    output_dir, parent_signature = preflight_output(output_dir, contract,
        request['target_files']['size_bytes'], profile)
    paths = {}
    for name in RECORD_FIELDS:
        avb._identity_spec(request[name], path=True)
        paths[name] = avb.envelope._absolute_path(request_path.parent / request[name]['path'])
        if name == 'target_files':
            guards.archive(paths[name], request[name])
        else:
            guards.json(paths[name], request[name])
    implementation = {}
    for name, (sha, size) in PUBLIC_PINS.items():
        pin = {'sha256': sha, 'size_bytes': size}
        guards.remember(ROOT / name, pin, signing.MAX_TEXT)
        implementation[name] = pin
    for path in (Path(__file__), HERE / 'target_files_archive_copy.py'):
        pin = signing._identity(path, signing.MAX_TEXT)
        guards.remember(path, pin, signing.MAX_TEXT)
        implementation[path.name] = pin
    supplied, _ = guards.json(paths['inventory'], request['inventory'])
    observed = inventory.inspect_target_files(paths['target_files'], selected(request['target_files']),
        retained_input_manifest=paths['retained_input_manifest'],
        expected_retained_manifest_sha256=request['retained_input_manifest']['sha256'])
    require(observed['status'] == 'complete' and observed['complete_input_inventory'] is True,
            'complete source archive and retained-input inventory required')
    same(observed, supplied, 'actual archive inventory differs from the externally selected record')
    retained, _ = signing.load_input(paths['retained_input_manifest'],
        request['retained_input_manifest']['sha256'], contract, contract_sha, profile)
    require(set(retained['images']) == RAW_ROLES, 'retained manifest selects an unexpected role')
    prepared, _ = guards.json(paths['signing_preparation'], request['signing_preparation'])
    signed, _ = guards.json(paths['signing_receipt'], request['signing_receipt'])
    workflow = signing._identity(signing.ROOT / 'scripts/avb_signing.py', signing.MAX_TEXT)
    require(prepared['operation'] == 'prepare' and prepared['status'] == 'prepared_public_only'
            and prepared['signing_performed'] is False and prepared['complete_chain_verified'] is False
            and prepared['source_inputs_unchanged'] is True, 'selected public preparation record is required')
    for record in (prepared, signed):
        require(record['contract_sha256'] == contract_sha and record['verifier_profile_sha256'] == profile_sha,
                'signing record uses different contracts')
        same(record['workflow'], workflow, 'signing workflow changed')
    require(signed['operation'] == 'sign' and signed['status'] == 'signed_and_verified'
            and signed['signing_performed'] is True and signed['complete_chain_verified'] is True
            and signed['two_pass_reproduction_verified'] is True and signed['working76_preserved'] is True
            and type(signed['unchanged_leaf_count']) is int and signed['unchanged_leaf_count'] == 14
            and signed['source_inputs_unchanged'] is True
            and signed['provenance_semantics_verified'] is False
            and signed['preparation_sha256'] == request['signing_preparation']['sha256'],
            'complete signing and reproduction evidence must bind this preparation')
    same(signed['key_roles'], contract['key_roles'], 'signing key roles differ')
    same(signed['public_key'], contract['public_key'], 'signing public key differs')
    original_path = paths['signing_preparation'].parent / 'input-manifest.json'
    guards.json(original_path, prepared['input_manifest'])
    original, _ = signing.load_input(original_path, prepared['input_manifest']['sha256'], contract, contract_sha, profile)
    require(set(original['images']) == signing.INPUTS and original['source_records'], 'fifteen prepared input roles required')
    same(prepared['preparation']['inputs'], {n: selected(r) for n, r in original['images'].items()},
         'preparation image identities differ')
    same(signed['provenance'], [selected(r) for r in original['source_records']], 'signing provenance differs')
    same(signed['verification_manifest'], selected(request['verification_manifest']), 'signed verification manifest differs')
    manifest, _ = avb.load_manifest(paths['verification_manifest'], request['verification_manifest']['sha256'], profile, profile_sha)
    require(set(manifest['images']) == avb.PARTITIONS
            and paths['verification_manifest'].parent == paths['signing_receipt'].parent,
            'complete canonical signed output directory required')
    require(manifest['artifact_set_id'] == original['artifact_set_id'] == signed['artifact_set_id'] == prepared['artifact_set_id'],
            'artifact set identity differs across signing records')
    for role, row in manifest['images'].items():
        require(row['path'] == paths['verification_manifest'].parent / (role + '.img'),
                'signed image is not its canonical sibling')
    same(signed['signed_derivative_passes'], [
        {name: selected(manifest['images'][name]) for name in contract['reproduction']['compare_images']}]*2,
        'two signing passes do not bind the final three image identities')
    for role in DATA_ROLES:
        same(selected(original['images'][role]), selected(observed['final_images'][role]),
             'prepared image did not come from the selected target-files archive')
    for role in signing.INPUTS - {'boot'}:
        same(selected(manifest['images'][role]), selected(original['images'][role]),
             'signing altered one of the fourteen retained input images')
    for role in RAW_ROLES:
        same(selected(original['images'][role]), selected(retained['images'][role]), 'retained firmware changed')
    dtbo_alias_proof = None
    for name, alias in observed['aliases'].items():
        if alias['image_role'] not in CHANGED_ROLES:
            final_image = selected(manifest['images'][alias['image_role']])
            if selected(alias) == final_image:
                continue
            require(name == DTBO_ALIAS_MEMBER and alias['image_role'] == 'dtbo',
                    'an unchanged image alias differs from the admitted final image')
            # AddDtbo can regenerate the copied prebuilt's AVB footer. Admit
            # only its proven salt/fingerprint metadata change, never a new
            # canonical DTBO or an exemption for another unchanged alias.
            dtbo_alias_proof = inspect_dtbo_alias(paths['target_files'],
                selected(request['target_files']), profile=profile)
            same(dtbo_alias_proof['source_archive'], selected(request['target_files']),
                 'DTBO alias proof selects another archive')
            same(dtbo_alias_proof['before'], selected(alias), 'DTBO alias proof selects another prebuilt')
            same(dtbo_alias_proof['after'], final_image, 'DTBO alias proof selects another canonical image')
    for record in original['source_records'] + retained['source_records']:
        guards.json(record['path'], record)
    for group in (original['images'], retained['images'], manifest['images']):
        for role, row in group.items():
            guards.remember(row['path'], row, avb.image_budget(profile, role))
    for row in manifest['public_keys'].values():
        same({k: row[k] for k in ('sha256', 'size_bytes', 'avb_sha256')},
             {**contract['public_key'], 'avb_sha256': contract['avb_public_key_sha256']}, 'unexpected intended public key')
        guards.public_key(row['path'], row)
    _verified_record(signed['verification'], manifest, request['verification_manifest']['sha256'], profile_sha, contract)
    before_digest = _zip_old_digest(paths['target_files'], selected(request['target_files']), original, profile)
    guards.recheck()
    repeated_verification = avb.verify(paths['verification_manifest'], request['verification_manifest']['sha256'])
    _verified_record(repeated_verification, manifest, request['verification_manifest']['sha256'], profile_sha, contract)
    same(repeated_verification['tools'], signed['verification']['tools'], 'public verification tool identities differ')
    require(parent_identity(output_dir.parent) == parent_signature and not os.path.lexists(output_dir),
            'output selection changed during input verification')
    staging = output_dir.parent / ('.' + output_dir.name + '.incomplete-' + uuid.uuid4().hex)
    with signing.io._private_creation():
        signing.io._mkdir(staging)
        signing.io._mkdir(staging / 'digest')
        expected_digest = digest_from_blobs({role: image_blob(manifest['images'][role]['path'], role,
            avb.image_budget(profile, role)) for role in avb.SIGNED})
        after_digest, digest_record, native = native_digest(staging / 'digest', manifest, profile, expected_digest)
        replacements = {'IMAGES/' + role + '.img': manifest['images'][role] for role in CHANGED_ROLES}
        replacements.update({name: manifest['images'][alias['image_role']] for name, alias in observed['aliases'].items()
                             if alias['image_role'] in CHANGED_ROLES})
        alias_normalizations, copy_options = {}, {}
        if dtbo_alias_proof is not None:
            replacements[DTBO_ALIAS_MEMBER] = manifest['images']['dtbo']
            alias_normalizations[DTBO_ALIAS_MEMBER] = dtbo_alias_proof
            copy_options['dtbo_alias_proof'] = dtbo_alias_proof
        replacements['META/vbmeta_digest.txt'] = {'data': after_digest}
        copy_report = rewrite_archive(paths['target_files'], selected(request['target_files']),
                                      staging / 'target-files.zip', replacements, profile=profile, **copy_options)
        if dtbo_alias_proof is not None:
            same(copy_report['dtbo_alias_proof'], dtbo_alias_proof, 'copied DTBO alias proof differs')
        archive_identity = signing._identity(staging / 'target-files.zip', inventory.MAX_ARCHIVE)
        final_inventory = inventory.inspect_target_files(staging / 'target-files.zip', archive_identity,
            retained_input_manifest=paths['retained_input_manifest'],
            expected_retained_manifest_sha256=request['retained_input_manifest']['sha256'])
        require(final_inventory['status'] == 'complete' and final_inventory['complete_input_inventory'] is True,
                'reconciled archive inventory failed')
        for role in DATA_ROLES | {'vbmeta', 'vbmeta_system'}:
            row = final_inventory['final_images'].get(role, final_inventory['generated_vbmeta_images'].get(role))
            same(selected(row), selected(manifest['images'][role]), 'reconciled final image differs')
        require(all(row['matches_final_image'] is True for row in final_inventory['aliases'].values()),
                'a reconciled image alias differs from its final image')
        same(selected(final_inventory['metadata']['META/vbmeta_digest.txt']), avb._identity(after_digest),
             'reconciled digest metadata differs')
        pins = {}
        for name, value in [('public-verification.json', repeated_verification), ('archive-copy.json', copy_report),
                            ('inventory-staging-path.json', final_inventory), ('native-digest.json', digest_record)]:
            pins[name] = write_new(staging / name, encoded(value))
        pins['request.json'] = write_new(staging / 'request.json', raw)
        report = {'schema_version': 1, 'operation': OPERATION, 'status': 'signed-image-archive-reconciled-only',
            'artifact_set_id': manifest['artifact_set_id'], 'contracts': observed['contracts'],
            'implementation': implementation, 'request': avb._identity(raw),
            'original_archive': selected(request['target_files']),
            'archive': {'path': 'target-files.zip', **archive_identity},
            'signed_verification_manifest': selected(request['verification_manifest']),
            'signing_receipt': selected(request['signing_receipt']),
            'public_complete_avb_verification_repeated': True,
            'vbmeta_digest_before': avb._identity(before_digest), 'vbmeta_digest_after': avb._identity(after_digest),
            'fourteen_signer_inputs_preserved': True, 'working76_preserved': True,
            'original_build_metadata_preserved': True,
            'alias_normalizations': alias_normalizations,
            'archive_runtime': {'python_implementation': sys.implementation.name,
                'python_version': sys.version, 'zlib_compile_version': zlib.ZLIB_VERSION,
                'zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION, 'deflate_level': 6,
                'cross_runtime_byte_reproduction_verified': False},
            'archive_copy': copy_report, 'evidence_files': pins, 'inputs_unchanged': True,
            'inventory_path_scope': 'The inventory names the immutable pre-publication staging path; replay at the published path for later consumers.',
            'limits': FALSE_SCOPE}
        receipt_pin = write_new(staging / 'receipt.json', encoded(report))
        output_guards = Guards()
        expected_files = {**pins, 'receipt.json': receipt_pin, 'target-files.zip': archive_identity,
                          'digest/vbmeta_digest.txt': avb._identity(after_digest)}
        for path in staging.rglob('*'):
            if path.is_file():
                relative = path.relative_to(staging).as_posix()
                maximum = inventory.MAX_ARCHIVE if relative == 'target-files.zip' else signing.io.MAX_TOOL
                pin = expected_files.get(relative)
                if pin is None:
                    pin = signing._identity(path, maximum)
                output_guards.remember(path, pin, maximum)
        topology = _topology(staging)
        guards.recheck()
        native.check()
        output_guards.recheck()
        _, final_contract_sha, _, final_profile_sha = controls()
        require((final_contract_sha, final_profile_sha) == (contract_sha, profile_sha),
                'public signing or image-set contract changed')
        guards.signatures()
        output_guards.signatures()
        require(parent_identity(output_dir.parent) == parent_signature, 'output parent changed')
        same(_topology(staging), topology, 'staging topology changed before exclusive publication')
        publish_new_directory(staging, output_dir)
    return {'status': report['status'], 'output_directory': str(output_dir),
            'archive': {'path': str(output_dir / 'target-files.zip'), **archive_identity},
            'receipt': {'path': str(output_dir / 'receipt.json'), **receipt_pin},
            'alias_normalizations': alias_normalizations, 'limits': FALSE_SCOPE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.request, args.expected_sha256, args.output_dir)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, zipfile.BadZipFile,
            struct.error, EOFError, zlib.error) as error:
        print(json.dumps({'status': 'blocked', 'error_type': type(error).__name__, 'limits': FALSE_SCOPE}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
