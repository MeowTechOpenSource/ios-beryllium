#!/usr/bin/env python3
"""Package the diagnostic with this Poco's boot-v1 layout and captured live FDT.

Creates a local candidate only. Does not run fastboot or write a device.
Inputs and output contain private device metadata and must stay out of git.
"""
import argparse
import gzip
import hashlib
from pathlib import Path
import struct


def pack(stock, image, dtb):
    if len(stock) < 4096 or stock[:8] != b'ANDROID!':
        raise ValueError('Invalid stock boot image')
    page, version = struct.unpack_from('<II', stock, 36)
    if page != 4096 or version != 1:
        raise ValueError('Only the verified Poco boot-v1/4096 layout is supported')
    if struct.unpack_from('<I', stock, 12)[0] != 0x8000:
        raise ValueError('Unexpected kernel load offset')
    if image[56:60] != b'ARM\x64' or len(image) < 64:
        raise ValueError('Not an ARM64 Linux Image')
    if struct.unpack_from('<Q', image, 16)[0] != len(image):
        raise ValueError('Linux image_size does not match input size')
    if len(dtb) < 40 or dtb[:4] != b'\xd0\x0d\xfe\xed':
        raise ValueError('Invalid live FDT')
    total, = struct.unpack_from('>I', dtb, 4)
    if total != len(dtb):
        raise ValueError('FDT length mismatch')
    if len(image) % 8:
        raise ValueError('Image must be 8-byte aligned before appended DTB')
    kernel = image + dtb
    # Empty newc cpio archive. ABL receives a valid nonempty ramdisk, but this
    # diagnostic never reads or executes it.
    fields = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0]
    archive = b'070701' + b''.join(f'{x:08x}'.encode() for x in fields) + b'TRAILER!!!\0'
    archive += bytes(-len(archive) % 512)
    ramdisk = gzip.compress(archive, mtime=0)
    header = bytearray(stock[:page])
    struct.pack_into('<I', header, 8, len(kernel))
    struct.pack_into('<I', header, 16, len(ramdisk))
    struct.pack_into('<II', header, 24, 0, 0)  # no second stage
    struct.pack_into('<IQI', header, 1632, 0, 0, 1648)  # no recovery DTBO
    digest = hashlib.sha1()
    for payload in [kernel, ramdisk, b'', b'']:
        digest.update(payload)
        digest.update(struct.pack('<I', len(payload)))
    header[576:608] = digest.digest() + bytes(12)
    align = lambda data: data + bytes(-len(data) % page)
    return bytes(header) + align(kernel) + align(ramdisk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock-boot', type=Path, required=True)
    parser.add_argument('--live-dtb', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = pack(args.stock_boot.read_bytes(), args.image.read_bytes(), args.live_dtb.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(result)
    args.out.chmod(0o600)
    print('Packaged temporary diagnostic candidate:', len(result), 'bytes')
    print('SHA256:', hashlib.sha256(result).hexdigest())


if __name__ == '__main__':
    main()
