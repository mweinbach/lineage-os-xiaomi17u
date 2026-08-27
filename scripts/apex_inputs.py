#!/usr/bin/env python3
"""Inspect captured vendor APEX files without mounting or activating a package.

ZIP members and EXT4 regular files are stored under flat private filenames.
debugfs is invoked read-only, with numeric inode requests, no shell, no repair
flags and no image paths interpolated into its command language. Its native
installed binary must match the caller's expected SHA256. This is static
evidence, not APEX signature authentication or an active-apex-info-list.
"""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

if __package__:
    from .erofs_inventory import (_checked_file, _destination, _image_record,
                                  _read_json, _real_parents, _unchanged, _write_json)
    from .firmware import _directory
else:
    from erofs_inventory import (_checked_file, _destination, _image_record,
                                 _read_json, _real_parents, _unchanged, _write_json)
    from firmware import _directory


MAX_APEX_BYTES = 128 * 1024**2
MAX_FILE_BYTES = 64 * 1024**2
MAX_TOTAL_BYTES = 256 * 1024**2
MAX_ENTRIES = 4096
MAX_DEPTH = 32
MAX_METADATA_BYTES = 4 * 1024**2
BUFFER_SIZE = 64 * 1024
DEFAULT_DEBUGFS = Path('/opt/homebrew/opt/e2fsprogs/sbin/debugfs')
DEBUGFS_VERSION = 'debugfs 1.47.4 (6-Mar-2025)'
SHA256 = re.compile(r'[0-9a-f]{64}')
SAFE_NAME = re.compile(r'[A-Za-z0-9_+.@,-]+')


class ApexError(ValueError):
    """A package, receipt or inspector output failed a bounded safety check."""


def checksum(value):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ApexError('a lowercase SHA256 is required')
    return value


def relative_path(value):
    if (not isinstance(value, str) or not value or len(value) > 4096
            or any(part in ('', '.', '..') or not SAFE_NAME.fullmatch(part)
                   for part in value.split('/'))):
        raise ApexError('noncanonical or unsafe archive/capture path')
    return value


def _artifact(path, output):
    with _checked_file(path) as record:
        return {'output_path': str(path.relative_to(output)), 'sha256': record['sha256'],
                'size_bytes': record['size_bytes'], 'readback_verified': True}


def _write_bytes(path, data, output):
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    result = _artifact(path, output)
    if result['sha256'] != hashlib.sha256(data).hexdigest():
        raise ApexError('artifact SHA256 readback failed')
    return result


def _varint(data, offset):
    value = 0
    for index in range(10):
        if offset >= len(data):
            raise ApexError('truncated protobuf varint')
        byte = data[offset]
        offset += 1
        if index == 9 and byte > 1:
            raise ApexError('protobuf varint exceeds uint64')
        value |= (byte & 127) << (7 * index)
        if byte < 128:
            return value, offset
    raise ApexError('protobuf varint is too long')


def parse_manifest(data):
    """Decode only the pinned AOSP ApexManifest fields; preserve unknown fields.

    Schema: platform/system/apex@97548ed51112062a4d1762a7dffa0cadcc09bda9,
    proto/apex_manifest.proto. Missing fields stay absent, not observations.
    """
    if not 0 < len(data) <= MAX_METADATA_BYTES:
        raise ApexError('APEX manifest has an invalid size')
    names = {1: 'name', 2: 'version', 3: 'preInstallHook', 4: 'postInstallHook',
             5: 'versionName', 6: 'noCode', 7: 'provideNativeLibs', 8: 'requireNativeLibs',
             9: 'jniLibs', 10: 'requireSharedApexLibs', 11: 'provideSharedApexLibs',
             13: 'supportsRebootlessUpdate', 14: 'vndkVersion', 15: 'vendorBootstrap',
             16: 'bootstrap'}
    repeated, integers = {7, 8, 9, 10}, {2, 6, 11, 13, 15, 16}
    result, unknown, offset, field_count = {}, [], 0, 0
    while offset < len(data):
        field_count += 1
        if field_count > MAX_ENTRIES:
            raise ApexError('too many protobuf fields')
        tag, offset = _varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if not 1 <= number < 2**29 or wire not in (0, 1, 2, 5):
            raise ApexError('unsupported or invalid protobuf field')
        if wire == 0:
            value, offset = _varint(data, offset)
        else:
            size = {1: 8, 5: 4}.get(wire)
            if wire == 2:
                size, offset = _varint(data, offset)
            if size > len(data) - offset:
                raise ApexError('truncated protobuf field')
            value, offset = data[offset:offset + size], offset + size
        if number not in names:
            unknown.append({'number': number, 'wire': wire,
                            'value': value if isinstance(value, int) else value.hex()})
            continue
        name = names[number]
        if wire != (0 if number in integers else 2):
            raise ApexError('APEX manifest field has the wrong wire type')
        if number in integers:
            if number == 2:
                if not 0 < value < 2**63:
                    raise ApexError('APEX version must be a positive int64')
            else:
                if value not in (0, 1):
                    raise ApexError('APEX boolean field is not zero or one')
                value = bool(value)
        else:
            value = value.decode('utf-8', errors='strict')
            if '\0' in value or len(value) > 4096:
                raise ApexError('unsafe or oversized APEX manifest string')
        if number in repeated:
            result.setdefault(name, []).append(value)
        elif name in result:
            raise ApexError('duplicate singular APEX manifest field')
        else:
            result[name] = value
    if not re.fullmatch(r'[A-Za-z0-9_]+(?:[.][A-Za-z0-9_-]+)+', result.get('name', '')):
        raise ApexError('missing or unsafe APEX module name')
    if 'version' not in result:
        raise ApexError('missing APEX version')
    return {'declared_fields': result, 'unknown_fields': unknown}


def unpack_zip(source, output):
    """Read every member through CRC validation; never materialize ZIP paths."""
    source['stream'].seek(0)
    records, total, names = [], 0, set()
    (output / 'zip').mkdir(mode=0o700)
    with zipfile.ZipFile(source['stream']) as archive:
        members = archive.infolist()
        if not 1 <= len(members) <= MAX_ENTRIES:
            raise ApexError('APEX ZIP entry count exceeds its bound')
        for member in members:
            name = relative_path(member.filename)
            mode = member.external_attr >> 16
            if (name in names or member.orig_filename != member.filename
                    or member.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or member.flag_bits & 1
                    or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ApexError('duplicate, special, encrypted or unsupported ZIP member')
            names.add(name)
            total += member.file_size
            if not 0 <= member.file_size <= MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ApexError('APEX ZIP uncompressed size exceeds its bound')
        if not {'apex_payload.img', 'apex_manifest.pb', 'apex_pubkey', 'AndroidManifest.xml'} <= names:
            raise ApexError('a non-compressed APEX with payload, manifest and public key is required')
        if shutil.disk_usage(output).free < total + 64 * 1024**2:
            raise ApexError('insufficient free space for bounded APEX extraction')
        for index, member in enumerate(members):
            target = output / 'zip' / f'{index:04d}'
            size, digest = 0, hashlib.sha256()
            with archive.open(member) as incoming, target.open('xb') as outgoing:
                os.chmod(target, 0o600)
                while data := incoming.read(BUFFER_SIZE):
                    size += len(data)
                    if size > member.file_size:
                        raise ApexError('ZIP member exceeded its declared size')
                    digest.update(data)
                    outgoing.write(data)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            record = _artifact(target, output)
            if size != member.file_size or record['sha256'] != digest.hexdigest():
                raise ApexError('ZIP extraction size or SHA256 readback failed')
            records.append({'member': member.filename, 'crc32': f'{member.CRC:08x}',
                            'crc_verified': True, **record})
    _unchanged(source)
    return records


def _run_debugfs(tool, image, request, output, commands, *, limit=MAX_METADATA_BYTES):
    if request != 'stats' and not re.fullmatch(r'(?:ls -p|stat|cat) <[1-9][0-9]{0,9}>', request):
        raise ApexError('debugfs request is not an allowed numeric-inode read')
    if not 0 <= limit <= MAX_FILE_BYTES:
        raise ApexError('debugfs output limit is invalid')
    _unchanged(tool)
    _unchanged(image)
    number = len(commands)
    stdout_path, stderr_path = output / 'commands' / f'{number:04d}.stdout', output / 'commands' / f'{number:04d}.stderr'
    fd = image['stream'].fileno()
    argv = [str(tool['path']), '-R', request, f'/dev/fd/{fd}']
    record = {'request': request, 'argv': argv}
    commands.append(record)
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, pass_fds=(fd,),
                               env={'LC_ALL': 'C', 'LANG': 'C', 'TZ': 'UTC', 'PATH': '/usr/bin:/bin'})
    deadline, sizes = time.monotonic() + 30, {'stdout': 0, 'stderr': 0}
    try:
        with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
            os.chmod(stdout_path, 0o600)
            os.chmod(stderr_path, 0o600)
            outputs = {'stdout': stdout, 'stderr': stderr}
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
                selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        raise ApexError('debugfs command timed out')
                    for key, _ in selector.select(min(1, deadline - time.monotonic())):
                        data = os.read(key.fileobj.fileno(), BUFFER_SIZE)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        sizes[key.data] += len(data)
                        if sizes[key.data] > (limit if key.data == 'stdout' else MAX_METADATA_BYTES):
                            raise ApexError('debugfs command output exceeds its bound')
                        outputs[key.data].write(data)
            record['exit_code'] = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            stdout.flush()
            stderr.flush()
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
        if stdout_path.exists():
            record['stdout'] = _artifact(stdout_path, output)
        if stderr_path.exists():
            record['stderr'] = _artifact(stderr_path, output)
    diagnostic = stderr_path.read_text(errors='strict').strip()
    if record.get('exit_code') != 0 or diagnostic != DEBUGFS_VERSION:
        raise ApexError('debugfs reported diagnostics; see preserved command logs')
    _unchanged(tool)
    _unchanged(image)
    return stdout_path


def parse_ext4_listing(text, *, inode, parent):
    entries, names, dots = [], set(), {}
    lines = text.splitlines()
    # debugfs 1.47.4 terminates its table with one additional blank line.
    if lines and lines[-1] == '':
        lines.pop()
    if len(lines) > MAX_ENTRIES + 2:
        raise ApexError('EXT4 directory record limit exceeded')
    for line in lines:
        # debugfs ls includes empty directory slots (DIRENT_FLAG_INCLUDE_EMPTY).
        # Only this exact unnamed zero-inode record is inert; named inode zero
        # entries and all other malformed records remain errors.
        if line == '/0/000000/0/0//0/':
            continue
        match = re.fullmatch(r'/([0-9]+)/([0-7]+)/([0-9]+)/([0-9]+)/([^/]+)/([0-9]*)/', line)
        if not match:
            raise ApexError('unexpected debugfs ls -p record')
        ino, mode, uid, gid, name, size = match.groups()
        ino, mode = int(ino), int(mode, 8)
        if not 0 < ino < 2**32 or name in names:
            raise ApexError('duplicate EXT4 name or invalid inode')
        names.add(name)
        if name in ('.', '..'):
            if not stat.S_ISDIR(mode):
                raise ApexError('EXT4 dot entry is not a directory')
            dots[name] = ino
            continue
        relative_path(name)
        kind = {stat.S_IFREG: 'regular', stat.S_IFDIR: 'directory', stat.S_IFLNK: 'symlink'}.get(stat.S_IFMT(mode))
        if kind is None:
            raise ApexError('special EXT4 inode type is not accepted')
        if kind == 'regular' and not size:
            raise ApexError('regular EXT4 entry lacks a size')
        entries.append({'inode': ino, 'name': name, 'type': kind, 'mode': f'{mode:06o}',
                        'uid': int(uid), 'gid': int(gid), 'size_bytes': int(size) if size else None})
        if len(entries) > MAX_ENTRIES:
            raise ApexError('EXT4 directory entry limit exceeded')
    if dots != {'.': inode, '..': parent}:
        raise ApexError('EXT4 dot entries do not match the visited directory')
    return entries


def parse_ext4_stat(text, expected):
    first = re.search(r'^Inode: ([0-9]+)\s+Type: (\S+)\s+Mode: +([0-7]+)', text, re.M)
    details = re.search(r'^User: +([0-9]+)\s+Group: +([0-9]+)\s+.*?Size: +([0-9]+)', text, re.M)
    if (not first or not details or int(first[1]) != expected['inode']
            or first[2] != 'regular' or int(first[3], 8) != int(expected['mode'], 8) & 0o7777
            or int(details[1]) != expected['uid'] or int(details[2]) != expected['gid']
            or int(details[3]) != expected['size_bytes']):
        raise ApexError('EXT4 inode metadata does not match the directory entry')


def elf_dynamic(data):
    """Read bounded ELF program/dynamic headers, without invoking the binary."""
    if data[:4] != b'\x7fELF':
        return None
    if len(data) < 64 or data[4] not in (1, 2) or data[5] not in (1, 2) or data[6] != 1:
        raise ApexError('unsupported or truncated ELF header')
    bits, endian = (64 if data[4] == 2 else 32), ('<' if data[5] == 1 else '>')
    header = struct.unpack_from(endian + ('HHIQQQIHHHHHH' if bits == 64 else 'HHIIIIIHHHHHH'), data, 16)
    phoff, phsize, phcount = header[4], header[8], header[9]
    expected_size = 56 if bits == 64 else 32
    if phsize != expected_size or not 0 < phcount <= MAX_ENTRIES or phoff + phsize * phcount > len(data):
        raise ApexError('invalid ELF program header table')
    loads, dynamic = [], []
    for index in range(phcount):
        fields = struct.unpack_from(endian + ('IIQQQQQQ' if bits == 64 else 'IIIIIIII'), data, phoff + phsize * index)
        if bits == 64:
            kind, _, offset, address, _, size, _, _ = fields
        else:
            kind, offset, address, _, size, _, _, _ = fields
        if offset + size > len(data):
            raise ApexError('ELF segment exceeds file size')
        if kind == 1:
            loads.append((address, offset, size))
        if kind == 2:
            dynamic.append((offset, size))
    if len(dynamic) > 1:
        raise ApexError('ambiguous ELF dynamic segment')
    needed, table, table_size, soname, search_paths = [], None, None, None, []
    width = 16 if bits == 64 else 8
    if dynamic:
        offset, size = dynamic[0]
        if size % width:
            raise ApexError('misaligned ELF dynamic segment')
        terminated = False
        for position in range(offset, offset + size, width):
            tag, value = struct.unpack_from(endian + ('qQ' if bits == 64 else 'iI'), data, position)
            if tag == 0:
                terminated = True
                break
            if tag == 1:
                needed.append(value)
            elif tag == 5:
                if table is not None:
                    raise ApexError('duplicate ELF string table')
                table = value
            elif tag == 10:
                if table_size is not None:
                    raise ApexError('duplicate ELF string table size')
                table_size = value
            elif tag == 14:
                if soname is not None:
                    raise ApexError('duplicate ELF SONAME')
                soname = value
            elif tag in (15, 29):
                search_paths.append((tag, value))
        if not terminated:
            raise ApexError('unterminated ELF dynamic segment')
    strings = b''
    if needed or soname is not None or search_paths:
        if table is None or table_size is None or table_size > MAX_FILE_BYTES:
            raise ApexError('ELF dynamic strings lack their bounded table')
        offsets = [offset + table - address for address, offset, size in loads
                   if address <= table and table + table_size <= address + size]
        if len(offsets) != 1:
            raise ApexError('ELF string table is not in exactly one load segment')
        strings = data[offsets[0]:offsets[0] + table_size]

    def string(index):
        if index >= len(strings) or (end := strings.find(b'\0', index)) < 0 or end - index > 4096:
            raise ApexError('invalid ELF dynamic string offset or termination')
        return strings[index:end].decode('utf-8', errors='strict')

    return {'class_bits': bits, 'endianness': 'little' if endian == '<' else 'big',
            'machine': header[1], 'needed': [string(i) for i in needed],
            'soname': string(soname) if soname is not None else None,
            'search_paths': [{'tag': tag, 'value': string(index)} for tag, index in search_paths]}


def vintf_declarations(data):
    if (not 0 < len(data) <= MAX_METADATA_BYTES
            or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper()):
        raise ApexError('VINTF XML is oversized or contains DTD/entity declarations')
    root = ET.fromstring(data)
    if root.tag != 'manifest' or root.get('type') not in ('device', 'framework'):
        raise ApexError('APEX VINTF file is not a typed manifest')
    hals = []
    for hal in root.findall('hal'):
        hals.append({'format': hal.get('format'), 'attributes': dict(hal.attrib),
                     'name': hal.findtext('name'),
                     'declared_versions': [e.text for e in hal.findall('version')],
                     'fqnames': [e.text for e in hal.findall('fqname')],
                     'interfaces': [{'name': interface.findtext('name'),
                                     'instances': [e.text for e in interface.findall('instance')]}
                                    for interface in hal.findall('interface')]})
    return {'root_attributes': dict(root.attrib), 'hals': hals,
            'effective_manifest_verified': False}


def init_declarations(data, module_name, regular_paths):
    """Record service stanzas, not the effects or full semantics of init code."""
    if len(data) > MAX_METADATA_BYTES:
        raise ApexError('init fragment exceeds its size bound')
    services, triggers, current = [], [], None
    for line in data.decode('utf-8', errors='strict').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        words = line.split()
        if not line[0].isspace():
            current = None
            if words[0] == 'service':
                if len(words) < 3:
                    raise ApexError('truncated init service declaration')
                prefix = '/apex/' + module_name + '/'
                relative = '/' + words[2][len(prefix):] if words[2].startswith(prefix) else None
                current = {'name': words[1], 'executable': words[2], 'arguments': words[3:],
                           'payload_path': relative,
                           'executable_present_as_regular': relative in regular_paths,
                           'options': {}}
                services.append(current)
            elif words[0] == 'on':
                triggers.append(' '.join(words[1:]))
        elif current is not None:
            current['options'].setdefault(words[0], []).append(words[1:])
    return {'services': services, 'observed_action_triggers': triggers, 'executed': False,
            'scope': 'service stanza observations; not a complete init parser or runtime test'}


def describe_payload(record, output):
    module = record['manifest']['declared_fields']['name']
    files = record['payload']['files']
    regular_paths = {f['path'] for f in files}
    result = {'vintf_files': [], 'init_files': [], 'json_files': [],
              'elf_files': [], 'active_state_inferred': False}
    for file in files:
        path = file['path']
        source = {'payload_path': path, 'runtime_path': '/apex/' + module + path,
                  'output_path': file['output_path'], 'sha256': file['sha256']}
        with _checked_file(output / file['output_path'], file['sha256']) as checked:
            checked['stream'].seek(0)
            if path.startswith('/etc/vintf/'):
                result['vintf_files'].append({**source, 'immediate_vintf_child': path.count('/') == 3,
                                             **vintf_declarations(checked['stream'].read(MAX_METADATA_BYTES + 1))})
            elif path.startswith('/etc/') and path.endswith('.rc'):
                result['init_files'].append({**source, **init_declarations(
                    checked['stream'].read(MAX_METADATA_BYTES + 1), module, regular_paths)})
            elif path.startswith('/etc/') and path.endswith('.json'):
                data = checked['stream'].read(MAX_METADATA_BYTES + 1)
                if len(data) > MAX_METADATA_BYTES:
                    raise ApexError('JSON configuration exceeds its size bound')
                result['json_files'].append({**source, 'data': json.loads(data),
                                             'runtime_semantics_verified': False})
        if file['elf'] is not None:
            result['elf_files'].append({**source, **file['elf']})
    provided = {f['soname'] for f in result['elf_files'] if f['soname'] is not None}
    needed = {name for f in result['elf_files'] for name in f['needed']}
    result['bundled_sonames'] = sorted(provided)
    result['dt_needed_union'] = sorted(needed)
    result['dt_needed_not_bundled_by_soname'] = sorted(needed - provided)
    result['namespace_resolution_verified'] = False
    return result


def inspect_ext4(image, tool, output, commands):
    image['stream'].seek(1080)
    if image['stream'].read(2) != b'\x53\xef':
        raise ApexError('only EXT4 payloads are supported by this inspector')
    superblock = _run_debugfs(tool, image, 'stats', output, commands)
    inventory, files, seen_dirs, inode_types = [], [], {2}, {2: 'directory'}
    queue, unique_files, total = deque([('/', 2, 2, 0)]), {}, 0
    deadline = time.monotonic() + 600
    while queue:
        if time.monotonic() > deadline:
            raise ApexError('EXT4 inspection exceeded its batch timeout')
        path, inode, parent, depth = queue.popleft()
        listing = _run_debugfs(tool, image, f'ls -p <{inode}>', output, commands)
        for entry in parse_ext4_listing(listing.read_text(), inode=inode, parent=parent):
            entry['path'] = path.rstrip('/') + '/' + entry.pop('name')
            if len(inventory) >= MAX_ENTRIES or depth + 1 > MAX_DEPTH:
                raise ApexError('EXT4 inventory exceeds its entry or depth limit')
            inventory.append(entry)
            if inode_types.setdefault(entry['inode'], entry['type']) != entry['type']:
                raise ApexError('EXT4 inode types are inconsistent')
            if entry['type'] == 'directory':
                if entry['inode'] in seen_dirs:
                    raise ApexError('EXT4 directory cycle or alias detected')
                seen_dirs.add(entry['inode'])
                queue.append((entry['path'], entry['inode'], inode, depth + 1))
            elif entry['type'] == 'regular':
                size = entry['size_bytes']
                if not 0 <= size <= MAX_FILE_BYTES:
                    raise ApexError('EXT4 file exceeds its size limit')
                metadata = _run_debugfs(tool, image, f"stat <{entry['inode']}>", output, commands)
                parse_ext4_stat(metadata.read_text(), entry)
                if entry['inode'] not in unique_files:
                    total += size
                    if total > MAX_TOTAL_BYTES:
                        raise ApexError('EXT4 regular files exceed the batch size limit')
                    if shutil.disk_usage(output).free < size + 64 * 1024**2:
                        raise ApexError('insufficient free space for bounded EXT4 capture')
                    captured = _run_debugfs(tool, image, f"cat <{entry['inode']}>", output, commands, limit=size)
                    record = _artifact(captured, output)
                    if record['size_bytes'] != size:
                        raise ApexError('captured EXT4 file size differs from its inode')
                    record['elf'] = elf_dynamic(captured.read_bytes())
                    unique_files[entry['inode']] = record
                record = unique_files[entry['inode']]
                if record['size_bytes'] != size:
                    raise ApexError('EXT4 hardlink aliases disagree about file size')
                files.append({**entry, **record})
    return {'filesystem': 'ext4', 'superblock': _artifact(superblock, output),
            'inventory': inventory, 'files': files, 'unique_regular_inodes': len(unique_files),
            'captured_bytes': total}


def inspect_apex(*, capture_receipt, expected_receipt_sha256, source_path,
                 package_sha256, output_dir, debugfs=DEFAULT_DEBUGFS,
                 expected_debugfs_sha256, zip_only=False):
    checksum(package_sha256)
    receipt_path = Path(os.path.abspath(capture_receipt))
    capture, capture_hash = _read_json(receipt_path, MAX_METADATA_BYTES, checksum(expected_receipt_sha256))
    if (capture.get('schema_version') != 1 or capture.get('operation') != 'erofs-capture'
            or capture.get('image_mounted') is not False
            or capture.get('firmware_executed') is not False or capture.get('symlinks_followed') is not False):
        raise ApexError('a guarded EROFS capture receipt is required')
    if (not isinstance(capture.get('files'), list) or not 1 <= len(capture['files']) <= MAX_ENTRIES
            or any(not isinstance(f, dict) for f in capture['files'])
            or not isinstance(capture.get('image'), dict)
            or type(capture['image'].get('size_bytes')) is not int or capture['image']['size_bytes'] <= 0):
        raise ApexError('invalid EROFS capture files or parent image')
    checksum(capture['image'].get('sha256'))
    matches = [f for f in capture.get('files', []) if f.get('path') == source_path]
    if len(matches) != 1 or matches[0].get('type') != 'regular' or matches[0].get('readback_verified') is not True:
        raise ApexError('APEX selection must match exactly one captured regular file')
    selected = matches[0]
    source = receipt_path.parent / relative_path(selected['output_path'])
    destination = _destination(output_dir)
    tool_path = Path(debugfs).resolve(strict=True)
    if tool_path.name != 'debugfs' or not os.access(tool_path, os.X_OK):
        raise ApexError('an installed executable debugfs is required')
    with _checked_file(source, checksum(selected['sha256'])) as apex, \
            _checked_file(tool_path, checksum(expected_debugfs_sha256)) as tool:
        if not 0 < apex['size_bytes'] <= MAX_APEX_BYTES or apex['size_bytes'] != selected['size_bytes']:
            raise ApexError('captured APEX size is invalid or does not match its receipt')
        _directory(destination.parent)
        destination.mkdir(mode=0o700)
        (destination / 'commands').mkdir(mode=0o700)
        record = {'schema_version': 1, 'operation': 'inert-vendor-apex-inspection',
                  'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
                  'source': {'package_sha256': package_sha256, 'package_sha256_binding': 'caller-supplied parent provenance',
                             'capture_receipt': str(receipt_path), 'capture_receipt_sha256': capture_hash,
                             'vendor_image': capture['image'], 'image_path': source_path,
                             'apex': _image_record(apex)},
                  'tool': {**_image_record(tool), 'expected_version_banner': DEBUGFS_VERSION},
                  'inspector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'commands': [], 'origin_verified': False, 'signature_authenticated': False,
                  'payload_avb_verified': False, 'active_state_verified': False,
                  'image_mounted': False, 'package_activated': False, 'firmware_executed': False,
                  'symlinks_followed': False, 'compatibility_verified': False}
        try:
            record['zip_members'] = unpack_zip(apex, destination)
            by_name = {f['member']: f for f in record['zip_members']}
            manifest = destination / by_name['apex_manifest.pb']['output_path']
            record['manifest'] = parse_manifest(manifest.read_bytes())
            payload = destination / by_name['apex_payload.img']['output_path']
            if not zip_only:
                with _checked_file(payload, by_name['apex_payload.img']['sha256']) as image:
                    record['payload'] = inspect_ext4(image, tool, destination, record['commands'])
                payload_manifests = [f for f in record['payload']['files'] if f['path'] == '/apex_manifest.pb']
                if len(payload_manifests) != 1:
                    raise ApexError('EXT4 payload must contain one regular apex_manifest.pb')
                inner = destination / payload_manifests[0]['output_path']
                if inner.read_bytes() != manifest.read_bytes():
                    raise ApexError('outer and EXT4 APEX manifests are not byte-identical')
                record['outer_inner_manifest_match'] = True
                record['static_dependencies'] = describe_payload(record, destination)
            _unchanged(apex)
            _unchanged(tool)
            _real_parents(destination)
            record['status'] = 'zip-only' if zip_only else 'complete'
        except Exception as exc:
            record['status'] = 'failed'
            record['error'] = f'{type(exc).__name__}: {exc}'
            _write_json(destination / 'receipt.json', record)
            raise
        _write_json(destination / 'receipt.json', record)
        return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-receipt', required=True, type=Path)
    parser.add_argument('--expected-receipt-sha256', required=True)
    parser.add_argument('--source-path', required=True)
    parser.add_argument('--package-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--debugfs', type=Path, default=DEFAULT_DEBUGFS)
    parser.add_argument('--expected-debugfs-sha256', required=True)
    parser.add_argument('--zip-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        receipt = inspect_apex(capture_receipt=args.capture_receipt,
                               expected_receipt_sha256=args.expected_receipt_sha256,
                               source_path=args.source_path, package_sha256=args.package_sha256,
                               output_dir=args.output, debugfs=args.debugfs,
                               expected_debugfs_sha256=args.expected_debugfs_sha256,
                               zip_only=args.zip_only)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f'APEX evidence: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({'output': str(args.output), 'status': receipt['status'],
                      'manifest': receipt['manifest'], 'commands': len(receipt['commands'])}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
