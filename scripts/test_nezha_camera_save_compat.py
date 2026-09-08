#!/usr/bin/env python3
"""Run the authored DNG parser and neutral gainmap helper with synthetic inputs.

Requires a local C++ compiler and JDK. No phone, network or proprietary source.
Android ABI builds and independent decoding of captures remain separate checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def lossless_tile():
    """Encode a 16x16, three-channel, 16-bit SOF3 tile with constant samples."""
    def segment(marker, body):
        return b'\xff' + bytes([marker]) + struct.pack('>H', len(body) + 2) + body
    frame = bytes([16]) + struct.pack('>HHB', 16, 16, 3) + bytes([1, 0x11, 0, 2, 0x11, 0, 3, 0x11, 0])
    huffman = bytes([0, 1]) + bytes(15) + bytes([0])
    scan = bytes([3, 1, 0, 2, 0, 3, 0, 1, 0, 0])
    return (b'\xff\xd8' + segment(0xc3, frame) + segment(0xc4, huffman)
            + segment(0xda, scan) + bytes(16 * 16 * 3 // 8) + b'\xff\xd9')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--javac', default='javac')
    parser.add_argument('--java', default='java')
    args = parser.parse_args()
    for tool in (args.cxx, args.javac, args.java):
        if shutil.which(tool) is None:
            parser.error('Compiler/runtime not available: ' + tool)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    templates = ROOT / 'templates/camera-save-compat'
    fixtures = ROOT / 'tests/fixtures/camera-save-compat'
    rows = []
    def run(name, command):
        result = subprocess.run(list(map(str, command)), capture_output=True, timeout=90)
        (out / (name + '.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(name + ' failed: ' + result.stderr.decode(errors='replace'))
        rows.append({'name': name, 'command': list(map(str, command)), 'exit_code': result.returncode,
                     'stdout': result.stdout.decode(errors='replace')})
    (out / 'tile.jpg').write_bytes(lossless_tile())
    run('dng-compile', [args.cxx, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                       '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-I', templates,
                       fixtures / 'CompressedDngTest.cpp', '-o', out / 'dng-test'])
    run('dng-test', [out / 'dng-test', out / 'tile.jpg'])
    run('gainmap-compile', [args.javac, '-d', out, templates / 'NezhaNeutralGainmap.java',
                           fixtures / 'NeutralGainmapTest.java'])
    run('gainmap-test', [args.java, '-cp', out, 'NeutralGainmapTest'])
    inputs = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for directory in (templates, fixtures) for path in sorted(directory.iterdir())}
    record = {'passed': True, 'phone_accessed': False, 'inputs': inputs, 'commands': rows}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'passed': True, 'tests': [row['stdout'].strip() for row in rows
                                            if row['name'].endswith('-test')]}))


if __name__ == '__main__':
    main()
