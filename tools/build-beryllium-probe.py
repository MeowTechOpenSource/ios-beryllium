#!/usr/bin/env python3
"""Build an ELF and Linux Image for the storage-free Poco diagnostic.

Requires the ziglang Python package in this interpreter. No boot image is
packaged: the actual phone's stock boot header/DTB must be obtained first.
This script never invokes adb/fastboot or accesses a device.
"""
import os
import argparse
from pathlib import Path
import struct
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--early-marker', action='store_true', help='Use the framebuffer reservation verified on this specific Poco before FDT validation')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = root / ('shim/out/beryllium-probe-early' if args.early_marker else 'shim/out/beryllium-probe')
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(out / 'zig-cache'))
    command = [sys.executable, '-m', 'ziglang']
    flags = ['-target', 'aarch64-freestanding-none', '-O2', '-ffreestanding',
             '-fno-builtin', '-nostdlib', '-fno-pic', '-fno-stack-protector',
             '-mgeneral-regs-only', '-mstrict-align', '-Wall', '-Wextra', '-Werror',
             '-DBERYLLIUM_DIAGNOSTIC']
    if args.early_marker:
        flags.append('-DBERYLLIUM_EARLY_MARKER')
    sources = ['start.S', 'console.c', 'beryllium_fdt.c', 'beryllium_probe.c']
    objects = []
    for source in sources:
        obj = out / (Path(source).stem + '.o')
        subprocess.run(command + ['cc'] + flags + ['-c', str(root / 'shim' / source),
                       '-o', str(obj)], check=True, env=env)
        objects.append(str(obj))
    elf = out / 'probe.elf'
    subprocess.run(command + ['cc'] + flags + objects +
                   ['-Wl,-T,' + str(root / 'shim/shim.ld'), '-Wl,--build-id=none',
                    '-Wl,-e,_head', '-Wl,--no-gc-sections', '-o', str(elf)], check=True, env=env)
    image = out / 'Image'
    subprocess.run(command + ['objcopy', '-O', 'binary', str(elf), str(image)],
                   check=True, env=env)
    raw = image.read_bytes()
    if len(raw) < 64 or raw[56:60] != b'ARM\x64':
        raise SystemExit('Invalid arm64 Linux Image header')
    size, = struct.unpack_from('<Q', raw, 16)
    if size < len(raw) or size > 1024 * 1024:
        raise SystemExit(f'Invalid image_size {size}')
    # Match upstream: reserve zeroed BSS and stacks in the loaded image.
    image.write_bytes(raw + bytes(size - len(raw)))
    print(f'Built {image} ({size} bytes). Not packaged or boot-tested.')


if __name__ == '__main__':
    main()
