#!/usr/bin/env python3
"""Plan or collect bounded read-only Nezha first-flash observations.

Never reboots, roots, mounts, flashes, wipes, changes slots, runs snapshotctl,
or grants flash readiness. Device collection requires an explicit USB serial,
mode, and fresh private output. Unsupported observations remain unknown.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import sys
import time

if __package__:
    from . import avb_signing
    from .collect_recovery import bounded_run, selected_transport
    from .collect_stock import CollectionError, secure_write, utc_now
else:
    import avb_signing
    from collect_recovery import bounded_run, selected_transport
    from collect_stock import CollectionError, secure_write, utc_now

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_ROLES = ('boot', 'dtbo', 'init_boot', 'recovery', 'vbmeta', 'vbmeta_system', 'vendor_boot')
RETAINED = ('countrycode', 'pvmfw')
PARTITIONS = tuple(f'{role}_{slot}' for role in PHYSICAL_ROLES + RETAINED for slot in ('a', 'b')) + ('super',)
IDENTITY_PROPERTIES = ('ro.product.manufacturer', 'ro.product.device', 'ro.kernel.qemu', 'ro.board.platform')
MODE_PROPERTIES = ('ro.bootmode', 'ro.boot.mode', 'init.svc.recovery', 'ro.twrp.version',
                   'sys.boot_completed', 'init.svc.zygote', 'init.svc.zygote_secondary', 'init.svc.surfaceflinger')
PROPERTIES = IDENTITY_PROPERTIES + MODE_PROPERTIES + (
    'ro.boot.hardware', 'ro.soc.model', 'ro.boot.hwc', 'ro.boot.slot_suffix',
    'ro.boot.flash.locked', 'ro.boot.vbmeta.device_state', 'ro.boot.verifiedbootstate',
    'ro.build.version.incremental', 'ro.vendor.build.version.incremental',
    'ro.build.fingerprint', 'ro.vendor.build.fingerprint', 'ro.crypto.state', 'ro.crypto.type',
)
FASTBOOT_VARS = (
    'product', 'is-userspace', 'version', 'version-bootloader', 'version-baseband',
    'unlocked', 'current-slot', 'slot-count', 'max-download-size', 'snapshot-update-status',
) + tuple(f'{key}:{slot}' for key in ('slot-successful', 'slot-unbootable', 'slot-retry-count')
          for slot in ('a', 'b')) + tuple(f'partition-size:{p}' for p in PARTITIONS) + tuple(
              f'has-slot:{p}' for p in PHYSICAL_ROLES + RETAINED + ('super',))
BOOTCTL_READS = (
    ('bootctl', 'hal-info'), ('bootctl', 'get-number-slots'), ('bootctl', 'get-current-slot'),
    ('bootctl', 'get-active-boot-slot'), ('bootctl', 'get-snapshot-merge-status'),
) + tuple(('bootctl', operation, slot) for operation in (
    'get-suffix', 'is-slot-bootable', 'is-slot-marked-successful') for slot in ('0', '1'))
RECOVERY_DEVICE_TREE = {
    '/proc/device-tree/model': b'Qualcomm Technologies, Inc. Nezha based on SM8850\0',
    '/proc/device-tree/compatible': b'qcom,canoe-mtp\0qcom,canoe\0qcom,canoep-mtp\0qcom,canoep\0qcom,mtp\0',
}
MAX_SESSION_BYTES = 16 * 1024 * 1024
MAX_BLOCK_READ = 1024 * 1024


def valid_serial(serial):
    return (isinstance(serial, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,256}', serial) is not None
            and not serial.startswith('emulator-') and '_adb-tls-' not in serial)


def selected_usb_transport(inventory, serial):
    selected = selected_transport(inventory, serial)
    rows = [line.split() for line in inventory.splitlines() if line.split() and line.split()[0] == serial]
    usb = [field for field in rows[0][2:] if field.startswith('usb:')]
    if len(usb) != 1 or not usb[0][4:]:
        raise CollectionError('An explicit local USB transport marker is required; network transports are refused.')
    return selected


def read_allowlist(target_slot):
    """Finite remote reads; target slot comes from the reviewed delivery route."""
    if target_slot not in ('a', 'b'):
        raise ValueError('An explicit target slot a or b is required')
    reads = [('getprop', p) for p in PROPERTIES]
    reads += [('id', '-u'), ('getconf', 'PAGESIZE'), ('getenforce',),
              ('cat', '/proc/self/mountinfo'), ('cat', '/proc/bootconfig'), ('pidof', 'recovery')]
    reads += [('cat', path) for path in RECOVERY_DEVICE_TREE]
    reads += list(BOOTCTL_READS)
    for partition in PARTITIONS:
        path = '/dev/block/by-name/' + partition
        reads += [('readlink', '-f', path), ('stat', '-L', '-c', '%F:%t:%T', path),
                  ('blockdev', '--getsize64', path)]
    reads += [('dd', 'if=/dev/block/by-name/super', 'bs=4096', 'count=256')]
    reads += [('dd', f'if=/dev/block/by-name/{role}_{target_slot}', 'bs=4096', 'count=256')
              for role in RETAINED]
    return tuple(reads)


def validate_read(tokens, target_slot):
    if not isinstance(tokens, (list, tuple)) or any(not isinstance(t, str) for t in tokens):
        raise CollectionError('Read tokens must be literal strings')
    if tuple(tokens) not in read_allowlist(target_slot):
        raise CollectionError('Command is outside the fixed read-only allowlist')
    return tuple(tokens)


def parse_fastboot_value(variable, stdout, stderr, exit_code, *, truncated=False):
    """Retain one exact-key value; unsupported and malformed replies stay unknown."""
    if variable not in FASTBOOT_VARS:
        raise ValueError('Unknown variable')
    unknown = {'status': 'unknown', 'value': None}
    if truncated or type(exit_code) is not int or exit_code != 0:
        return {**unknown, 'reason': 'incomplete-or-unsuccessful-command'}
    if any(not isinstance(x, bytes) for x in (stdout, stderr)):
        raise ValueError('Raw command streams required')
    if len(stdout) > 65536 or len(stderr) > 65536:
        return {**unknown, 'reason': 'output-limit'}
    try:
        lines = (stdout + b'\n' + stderr).decode('utf-8', 'strict').splitlines()
    except UnicodeDecodeError:
        return {**unknown, 'reason': 'invalid-text'}
    values = []
    for raw in lines:
        line = raw.strip()
        if line.startswith('(bootloader) '):
            line = line[len('(bootloader) '):]
        if re.search(r'(?i)(FAILED|unknown variable|not supported|not implemented|permission denied|remote:.*error)', line):
            return {**unknown, 'reason': 'remote-error'}
        if line.startswith(variable + ':'):
            values.append(line[len(variable) + 1:].strip())
    if len(values) != 1 or not values[0]:
        return {**unknown, 'reason': 'missing-duplicate-or-empty-value'}
    value = values[0]
    allowed = None
    if variable in ('is-userspace', 'unlocked') or variable.startswith(('has-slot:', 'slot-successful:', 'slot-unbootable:')):
        allowed = {'yes', 'no'}
    elif variable == 'current-slot':
        allowed = {'a', 'b'}
    elif variable == 'slot-count':
        allowed = {'2'}
    elif variable == 'snapshot-update-status':
        allowed = {'none', 'snapshotted', 'merging'}
    elif variable.startswith('slot-retry-count:'):
        allowed = {str(i) for i in range(8)}
    if (allowed is not None and value not in allowed) or (variable.startswith('partition-size:') or variable == 'max-download-size') and parse_capacity(value) is None:
        return {**unknown, 'reason': 'unsupported-or-malformed-value', 'reported_text': value}
    return {'status': 'observed', 'value': value, 'reason': None}


def parse_capacity(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:0x[0-9a-fA-F]+|[0-9]+)', value):
        return None
    number = int(value, 16 if value.startswith('0x') else 10)
    return number if 0 < number <= 2**63 - 1 else None


def compare_retained_firmware(body, reference):
    """Compare saved bytes with the maintained factory descriptor, entirely on host."""
    image, descriptor = reference['image'], reference['descriptor']
    if len(body) != image['size_bytes']:
        return {'status': 'unknown', 'authenticated_region_matches': None,
                'full_file_matches': None, 'reason': 'incomplete-or-extra-capture'}
    full = hashlib.sha256(body).hexdigest()
    digest = hashlib.sha256(bytes.fromhex(descriptor['salt_hex']) + body[:descriptor['image_size']]).hexdigest()
    matches = digest == descriptor['digest_hex']
    return {'status': 'match' if matches else 'mismatch', 'authenticated_region_matches': matches,
            'full_file_matches': full == image['sha256'], 'full_sha256': full,
            'authenticated_digest_hex': digest, 'authenticated_size': descriptor['image_size'],
            'complete_firmware_trust_or_bootloader_acceptance_proven': False}


def interpret_bootctl(result, operation=None):
    """A false getter is not a HAL error; retain every raw result separately."""
    text = result['stdout'].decode('utf-8', 'replace').strip()
    if result['truncated_streams']:
        return {'status': 'unknown', 'value': None}
    if result['exit_code'] == 0 and result['status'] == 'ok':
        allowed = {
            'get-snapshot-merge-status': {'none', 'snapshotted', 'merging', 'cancelled'},
            'get-current-slot': {'0', '1'}, 'get-active-boot-slot': {'0', '1'},
            'get-number-slots': {'2'}, 'get-suffix': {'_a', '_b'},
            'is-slot-bootable': {'1'}, 'is-slot-marked-successful': {'1'},
        }.get(operation)
        if not text or (allowed is not None and text not in allowed):
            return {'status': 'unknown', 'value': None, 'reported_text': text}
        return {'status': 'observed', 'value': text}
    if operation in ('is-slot-bootable', 'is-slot-marked-successful') and result['exit_code'] == 70 and text == '0' and not result['stderr'].strip():
        return {'status': 'observed', 'value': '0'}
    return {'status': 'unknown', 'value': None}


def fresh_output(path):
    """Private fresh directory; no symlink or traversal ancestors."""
    output = path.expanduser().absolute()
    evidence = ROOT / 'evidence'
    try:
        relative = output.relative_to(evidence)
    except ValueError as exc:
        raise CollectionError('Output must be a fresh subdirectory of ignored evidence/.') from exc
    if not relative.parts or any(part in ('.', '..') for part in relative.parts):
        raise CollectionError('Output must be a fresh evidence subdirectory without traversal.')
    current = ROOT
    for part in ('evidence', *relative.parts[:-1]):
        current /= part
        if current.is_symlink():
            raise CollectionError('Output ancestors must not be symlinks.')
        current.mkdir(mode=0o700, exist_ok=True)
        if not current.is_dir():
            raise CollectionError('Output ancestors must be directories.')
    output.mkdir(mode=0o700)
    (output / 'commands').mkdir(mode=0o700)
    secure_write(output / '.gitignore', b'*\n!.gitignore\n')
    return output


class Collector:
    def __init__(self, args):
        self.args = args
        self.output = fresh_output(args.output)
        self.deadline = time.monotonic() + args.total_timeout
        self.bytes_read = 0
        self.transport = None
        self.verified = False
        self.contract, contract_sha, self.profile, profile_sha = avb_signing.load_contract()
        self.report = {
            'schema_version': 1, 'collection_kind': 'read-only-device-flash-preflight-observations',
            'started_at': utc_now(), 'status': 'collecting', 'serial': args.serial, 'mode': args.mode,
            'target_slot': args.target_slot, 'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dependencies': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                             for name in ('collect_recovery.py', 'collect_stock.py', 'avb_signing.py')},
            'signing_contract_sha256': contract_sha, 'avb_profile_sha256': profile_sha,
            'commands': [], 'properties': {}, 'fastboot': {}, 'bootctl': {}, 'capacities': {},
            'firmware': {}, 'errors': [], 'unknowns': [], 'secure_rollback_indices': None,
            'secure_rollback_reason': 'No standard secure stored-index getter is assumed. Image indices and libavb_user stub zeros are not storage evidence.',
            'flash_ready': False, 'device_preflight_admitted': False, 'phone_mutations_requested': False,
            'backup_verified': False, 'data_wipe_authorized': False, 'snapshot_idle_verified': False,
            'limits': {'per_command_seconds': args.timeout, 'session_seconds': args.total_timeout,
                       'session_output_bytes': MAX_SESSION_BYTES, 'raw_block_read_bytes': MAX_BLOCK_READ},
            'options': {name: getattr(args, name) for name in ('include_boot_control', 'include_firmware', 'include_super_metadata')},
        }

    def execute(self, label, command, limit=65536):
        remaining = self.deadline - time.monotonic()
        limit = min(limit, (MAX_SESSION_BYTES - self.bytes_read) // 2)
        if remaining <= 0 or limit <= 0:
            raise CollectionError('Collection time or output budget exhausted; remaining facts are unknown.')
        result = bounded_run(command, timeout=min(self.args.timeout, remaining), max_bytes=limit)
        record = {key: value for key, value in result.items() if key not in ('stdout', 'stderr')}
        record.update(label=label, argv=command, max_bytes_per_stream=limit)
        for stream in ('stdout', 'stderr'):
            body = result[stream]
            self.bytes_read += len(body)
            path = self.output / 'commands' / f'{len(self.report["commands"]):03d}-{label}.{stream}.bin'
            secure_write(path, body)
            record[stream] = {'path': str(path.relative_to(self.output)), 'size_bytes': len(body),
                              'sha256': hashlib.sha256(body).hexdigest()}
        self.report['commands'].append(record)
        if result['status'] == 'interrupted':
            raise KeyboardInterrupt
        return result

    def direct_adb(self, label, tokens):
        if tokens in (('version',), ('devices', '-l')):
            command = [self.args.adb, *tokens]
        elif tokens in (('get-state',), ('features',)) and self.transport:
            command = [self.args.adb, '-t', self.transport, *tokens]
        else:
            raise CollectionError('Unapproved direct ADB command.')
        return self.execute(label, command)

    def shell(self, label, tokens, limit=65536):
        tokens = validate_read(tokens, self.args.target_slot)
        if not self.transport:
            raise CollectionError('A selected transport is required.')
        if not self.verified and not (tokens[0] == 'getprop' or tokens == ('pidof', 'recovery')
                or self.args.mode == 'adb-recovery' and tokens in tuple(('cat', path) for path in RECOVERY_DEVICE_TREE)):
            raise CollectionError('Device identity and mode must be verified before reads.')
        return self.execute(label, [self.args.adb, '-t', self.transport, 'shell', '-T', shlex.join(tokens)], limit)

    @staticmethod
    def text(result):
        if result['status'] != 'ok' or result['exit_code'] != 0 or result['truncated_streams']:
            return None
        return result['stdout'].decode('utf-8', 'replace').strip()

    def property(self, name, prefix='property'):
        value = self.text(self.shell(prefix + '-' + name, ('getprop', name), 4096))
        if prefix == 'property':
            self.report['properties'][name] = value
        return value

    def adb_preflight(self):
        if self.text(self.direct_adb('adb-version', ('version',))) is None:
            raise CollectionError('ADB version could not be read.')
        inventory = self.text(self.direct_adb('adb-devices', ('devices', '-l')))
        if inventory is None:
            raise CollectionError('A complete ADB inventory is required.')
        state, self.transport = selected_usb_transport(inventory, self.args.serial)
        self.report['transport_id'] = self.transport
        self.adb_state = state
        if self.text(self.direct_adb('adb-state', ('get-state',))) != state:
            raise CollectionError('ADB transport state changed.')
        features = self.text(self.direct_adb('adb-features', ('features',)))
        if features is None or 'shell_v2' not in re.split(r'[,\s]+', features):
            raise CollectionError('ADB shell_v2 exit-status support is required.')
        for name in IDENTITY_PROPERTIES + MODE_PROPERTIES:
            self.property(name)
        p = self.report['properties']
        if (p['ro.product.manufacturer'] or '').casefold() != 'xiaomi' or p['ro.product.device'] != 'nezha' or p['ro.kernel.qemu'] not in ('', '0'):
            raise CollectionError('Exact physical Xiaomi/nezha/canoe identity was not observed.')
        modes = {p['ro.bootmode'], p['ro.boot.mode']}
        if self.args.mode == 'adb-recovery':
            if p['ro.board.platform'] not in ('canoe', 'xiaomi_sm8750'):
                raise CollectionError('Unreviewed recovery board property.')
            self.recovery_device_tree('initial')
            if p['init.svc.recovery'] != 'running' or (state != 'recovery' and 'recovery' not in modes) or any(m not in ('', 'unknown', 'recovery') for m in modes) or ('unknown' in modes and state != 'recovery'):
                raise CollectionError('Already-running recovery mode was not observed.')
            if any(p[n] not in ('', 'stopped') for n in ('init.svc.zygote', 'init.svc.zygote_secondary', 'init.svc.surfaceflinger')):
                raise CollectionError('Android framework markers conflict with recovery mode.')
            pid = self.text(self.shell('recovery-pid', ('pidof', 'recovery'), 256))
            self.recovery_pid = pid
            if pid is None or re.fullmatch(r'[1-9][0-9]{0,9}', pid) is None:
                raise CollectionError('One running recovery process is required.')
        elif p['ro.board.platform'] != 'canoe' or any(m not in ('', 'normal') for m in modes) or state != 'device' or p['sys.boot_completed'] != '1' or 'recovery' in modes or p['init.svc.recovery'] not in ('', 'stopped'):
            raise CollectionError('Already-running Android mode was not observed.')
        self.verified = True

    def recovery_device_tree(self, stage):
        observed = {}
        for path, expected in RECOVERY_DEVICE_TREE.items():
            result = self.shell('device-tree-' + stage + '-' + path.rsplit('/', 1)[1], ('cat', path), 4096)
            if (result['status'] != 'ok' or result['exit_code'] != 0 or result['truncated_streams']
                    or result['stdout'] != expected):
                raise CollectionError('Exact live Nezha SM8850/canoe recovery device tree was not observed.')
            observed[path] = result['stdout'].decode('ascii')
        self.report['recovery_device_tree'] = observed

    def recheck_adb(self, stage):
        if self.args.mode == 'adb-recovery':
            self.recovery_device_tree(stage)
        for name in IDENTITY_PROPERTIES + MODE_PROPERTIES + ('ro.boot.slot_suffix',):
            if self.property(name, stage) != self.report['properties'][name]:
                raise CollectionError('Device identity, mode or running slot changed during collection.')
        if self.args.mode == 'adb-recovery' and self.text(self.shell('recovery-pid-' + stage, ('pidof', 'recovery'), 256)) != self.recovery_pid:
            raise CollectionError('Recovery process changed or disappeared during collection.')
        inventory = self.text(self.direct_adb('adb-devices-' + stage, ('devices', '-l')))
        if inventory is None or selected_usb_transport(inventory, self.args.serial) != (self.adb_state, self.transport):
            raise CollectionError('Selected ADB transport or state changed during collection.')
        if self.text(self.direct_adb('adb-state-' + stage, ('get-state',))) != self.adb_state:
            raise CollectionError('Selected ADB state changed during collection.')

    def capacity(self, partition, value):
        observed = parse_capacity(value)
        role = partition[:-2] if partition.endswith(('_a', '_b')) else partition
        expected = 15300820992 if role == 'super' else self.profile['image_budgets'][role]
        self.report['capacities'][partition] = {
            'observed_bytes': observed, 'recorded_package_budget_bytes': expected,
            'meets_recorded_budget': None if observed is None else observed >= expected,
            'matches_recorded_package_capacity': None if observed is None else observed == expected,
            'candidate_artifact_fit_or_flash_admission': False,
        }

    def adb_collect(self):
        self.adb_preflight()
        for name in PROPERTIES:
            if name not in self.report['properties']:
                self.property(name)
        uid = self.text(self.shell('uid', ('id', '-u'), 256))
        self.report['existing_uid'] = uid
        for label, tokens in (('page-size', ('getconf', 'PAGESIZE')), ('selinux', ('getenforce',)),
                              ('mountinfo', ('cat', '/proc/self/mountinfo')), ('bootconfig', ('cat', '/proc/bootconfig'))):
            self.shell(label, tokens, 262144)
        identities = {}
        for partition in PARTITIONS:
            path = '/dev/block/by-name/' + partition
            resolved = self.text(self.shell('resolve-' + partition, ('readlink', '-f', path), 4096))
            kind = self.text(self.shell('type-' + partition, ('stat', '-L', '-c', '%F:%t:%T', path), 4096))
            size = self.text(self.shell('size-' + partition, ('blockdev', '--getsize64', path), 4096))
            identities[partition] = (resolved, kind, size)
            self.capacity(partition, size)
        self.report['partition_nodes'] = identities
        if self.args.include_boot_control:
            first = self.shell('bootctl-hal-info', BOOTCTL_READS[0], 4096)
            self.report['bootctl']['hal-info'] = interpret_bootctl(first, 'hal-info')
            if self.text(first) is not None:
                for tokens in BOOTCTL_READS[1:]:
                    result = self.shell('-'.join(tokens), tokens, 4096)
                    interpreted = interpret_bootctl(result, tokens[1])
                    self.report['bootctl'][' '.join(tokens[1:])] = interpreted
                    if interpreted.get('value') == '0' and result['exit_code'] == 70:
                        self.report['commands'][-1]['observed_false_getter'] = True
            else:
                self.report['unknowns'].append('Boot-control HAL query unavailable; no service is started or repaired explicitly.')
        if self.args.include_firmware or self.args.include_super_metadata:
            self.recheck_adb('before-raw')
            if uid != '0' or self.args.mode != 'adb-recovery':
                raise CollectionError('Block capture requires already-running recovery with existing uid 0; no root escalation is attempted.')
            selected = ([f'{role}_{self.args.target_slot}' for role in RETAINED] if self.args.include_firmware else [])
            selected += ['super'] if self.args.include_super_metadata else []
            for partition in selected:
                resolved, kind, _ = identities[partition]
                if (not resolved or re.fullmatch(r'/dev/block/sd[a-z]+[1-9][0-9]*', resolved) is None
                        or sum(row[0] == resolved for row in identities.values()) != 1
                        or not kind or sum(row[1] == kind for row in identities.values()) != 1):
                    raise CollectionError('Raw capture requires distinct physical UFS partition nodes, not dm/mapper or aliased nodes.')
            for partition in selected:
                resolved, kind, size = identities[partition]
                if not resolved or re.fullmatch(r'/dev/block/[A-Za-z0-9_./-]+', resolved) is None or not kind or re.fullmatch(r'(?:block special file|block device):[0-9a-fA-F]+:[0-9a-fA-F]+', kind) is None or parse_capacity(size) is None or parse_capacity(size) < MAX_BLOCK_READ:
                    raise CollectionError('A fixed block node and its readable capacity are required before raw capture.')
                path = '/dev/block/by-name/' + partition
                result = self.shell('raw-' + partition, ('dd', 'if=' + path, 'bs=4096', 'count=256'), MAX_BLOCK_READ)
                after = (self.text(self.shell('resolve-after-' + partition, ('readlink', '-f', path), 4096)),
                         self.text(self.shell('type-after-' + partition, ('stat', '-L', '-c', '%F:%t:%T', path), 4096)),
                         self.text(self.shell('size-after-' + partition, ('blockdev', '--getsize64', path), 4096)))
                complete = result['status'] == 'ok' and result['exit_code'] == 0 and not result['truncated_streams'] and len(result['stdout']) == MAX_BLOCK_READ and after == identities[partition]
                if not complete:
                    raise CollectionError('First raw capture failed or block identity changed; no repeat read attempted.')
                repeat = self.shell('raw-recheck-' + partition, ('dd', 'if=' + path, 'bs=4096', 'count=256'), MAX_BLOCK_READ)
                final_identity = (self.text(self.shell('resolve-final-' + partition, ('readlink', '-f', path), 4096)),
                                  self.text(self.shell('type-final-' + partition, ('stat', '-L', '-c', '%F:%t:%T', path), 4096)),
                                  self.text(self.shell('size-final-' + partition, ('blockdev', '--getsize64', path), 4096)))
                complete = (complete and final_identity == identities[partition] and repeat['status'] == 'ok' and repeat['exit_code'] == 0
                            and not repeat['truncated_streams'] and repeat['stdout'] == result['stdout'])
                if not complete:
                    raise CollectionError('Paired raw block reads were incomplete, differed, or block identity changed; comparison refused.')
                if partition != 'super':
                    role = partition[:-2]
                    self.report['firmware'][partition] = compare_retained_firmware(result['stdout'], self.contract['raw_descriptor_sources'][role])
                else:
                    self.report['super_metadata_capture'] = {'prefix_bytes': MAX_BLOCK_READ,
                        'sha256': hashlib.sha256(result['stdout']).hexdigest(),
                        'full_super_or_logical_payload_hash': False, 'host_lp_parse_pending': True,
                        'paired_prefix_reads_match': True}
        self.recheck_adb('final')
        self.report['bootloader_unlocked_confirmed'] = None
        self.report['lock_scope'] = 'Android/recovery properties are reported observations, not independent bootloader lock evidence.'

    def fastboot_query(self, variable, suffix=''):
        if variable not in FASTBOOT_VARS:
            raise CollectionError('Unapproved fastboot variable.')
        result = self.execute('getvar-' + variable.replace(':', '-') + suffix,
                              [self.args.fastboot, '-s', self.args.serial, 'getvar', variable])
        parsed = parse_fastboot_value(variable, result['stdout'], result['stderr'], result['exit_code'],
                                      truncated=bool(result['truncated_streams']) or result['status'] != 'ok')
        if not suffix:
            self.report['fastboot'][variable] = parsed
        return parsed['value']

    def fastboot_collect(self):
        if self.fastboot_query('is-userspace') != 'no':
            raise CollectionError('Independent bootloader mode is unverified; fastbootd and unsupported mode probes are refused.')
        if self.fastboot_query('product') != 'nezha':
            raise CollectionError('Fastboot product must be exactly nezha; no alternate device is selected.')
        for variable in FASTBOOT_VARS:
            if variable not in self.report['fastboot']:
                value = self.fastboot_query(variable)
                if variable.startswith('partition-size:'):
                    self.capacity(variable.split(':', 1)[1], value)
        before = {name: self.report['fastboot'][name]['value'] for name in ('is-userspace', 'product', 'current-slot')}
        for name, value in before.items():
            if self.fastboot_query(name, '-recheck') != value:
                raise CollectionError('Bootloader mode, product or next-boot slot changed during collection.')
        unlocked = self.report['fastboot']['unlocked']['value']
        self.report['bootloader_unlocked_confirmed'] = {'yes': True, 'no': False}.get(unlocked)
        self.report['board_identity'] = None
        self.report['identity_scope'] = 'Bootloader product is nezha; exact canoe/region identity needs a same-device authorized ADB or prior independently reviewed identity join.'
        self.report['slot_scope'] = 'Bootloader current-slot selects next boot; ADB ro.boot.slot_suffix describes the running boot.'

    def collect(self):
        status = 0
        try:
            if self.args.mode.startswith('adb-'):
                self.adb_collect()
            else:
                self.fastboot_collect()
            unknown = ([f'fastboot:{name}' for name, value in self.report['fastboot'].items() if value['status'] == 'unknown']
                       + [f'bootctl:{name}' for name, value in self.report['bootctl'].items() if value['status'] == 'unknown']
                       + [f'property:{name}' for name, value in self.report['properties'].items() if value is None]
                       + [f'capacity:{name}' for name, value in self.report['capacities'].items() if value['observed_bytes'] is None])
            self.report['unknowns'].extend(unknown)
            incomplete = bool(self.report['unknowns']) or any((c['status'] != 'ok' and not c.get('observed_false_getter', False)) or c['truncated_streams'] for c in self.report['commands'])
            self.report['status'] = 'partial-observations' if incomplete else 'requested-observations-complete-not-device-admission'
            status = 3 if incomplete else 0
        except KeyboardInterrupt:
            self.report['status'] = 'interrupted'
            status = 130
        except (CollectionError, OSError, ValueError) as exc:
            self.report['errors'].append(str(exc).replace(self.args.serial, '<selected-device>'))
            self.report['status'] = 'blocked-or-incomplete'
            status = 2
        finally:
            self.report['completed_at'] = utc_now()
            self.report['captured_output_bytes'] = self.bytes_read
            secure_write(self.output / 'manifest.json', (json.dumps(self.report, indent=2) + '\n').encode())
        return status


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument('--collect', action='store_true', help='Explicitly execute only the fixed reads after separate user authorization.')
    result.add_argument('--serial', help='Explicit authorized physical USB identifier, never auto-selected.')
    result.add_argument('--mode', choices=('adb-android', 'adb-recovery', 'fastboot-bootloader'))
    result.add_argument('--target-slot', choices=('a', 'b'), help='Explicit reviewed delivery target; not automatically the inactive slot.')
    result.add_argument('--output', type=Path, help='Fresh ignored evidence/ subdirectory, required for collection.')
    result.add_argument('--adb', default='adb')
    result.add_argument('--fastboot', default='fastboot')
    result.add_argument('--include-boot-control', action='store_true', help='Query available boot-control getters; HAL lookup may activate a lazy service.')
    result.add_argument('--include-firmware', action='store_true', help='Read exactly 1 MiB from each target-slot countrycode/pvmfw block node in existing root recovery.')
    result.add_argument('--include-super-metadata', action='store_true', help='Read only the first 1 MiB of Super in existing root recovery, for later host LP inspection.')
    result.add_argument('--timeout', type=float, default=20)
    result.add_argument('--total-timeout', type=float, default=600)
    return result


def main(argv=None):
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if args.serial is not None and not valid_serial(args.serial):
        command_parser.error('Serial must be a physical USB identifier without shell or network syntax.')
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60 or not math.isfinite(args.total_timeout) or not 0 < args.total_timeout <= 900:
        command_parser.error('Timeouts must be finite: 0 < per-command <= 60 and 0 < total <= 900 seconds.')
    if args.collect and any(getattr(args, name) is None for name in ('serial', 'mode', 'target_slot', 'output')):
        command_parser.error('Collection requires explicit --serial, --mode, --target-slot and --output.')
    if args.mode == 'fastboot-bootloader' and any((args.include_boot_control, args.include_firmware, args.include_super_metadata)):
        command_parser.error('ADB optional scopes cannot be used in bootloader fastboot mode.')
    if args.mode == 'adb-android' and (args.include_firmware or args.include_super_metadata):
        command_parser.error('Raw block captures require already-running root recovery; normal Android is refused.')
    if args.collect and args.mode.startswith('adb-') and any(os.environ.get(name) for name in ('ADB_SERVER_SOCKET', 'ANDROID_ADB_SERVER_ADDRESS', 'ANDROID_ADB_SERVER_PORT')):
        command_parser.error('Nondefault ADB server environment is refused for explicit local USB collection.')
    if not args.collect:
        print('Plan only: no commands executed, no device selected, no files created.')
        print('Choose explicit authorized USB serial, mode, target slot and fresh evidence output before --collect.')
        print('Recovery raw reads and boot-control HAL queries are separate opt-in scopes. No snapshotctl, avbctl, getvar all or arbitrary commands.')
        print('Unknown rollback/identity/snapshot fields stay unknown; this helper never grants flash readiness.')
        return 0
    try:
        collector = Collector(args)
        status = collector.collect()
    except (CollectionError, OSError, ValueError) as exc:
        print(('Preflight stopped: ' + str(exc)).replace(args.serial, '<selected-device>'), file=sys.stderr)
        return 2
    print('Observation status: ' + collector.report['status'] + '. Flash readiness remains false.')
    return status


if __name__ == '__main__':
    raise SystemExit(main())
