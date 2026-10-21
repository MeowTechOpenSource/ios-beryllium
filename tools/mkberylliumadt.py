#!/usr/bin/env python3
"""Create a single-CPU, storage-disabled XNU ADT from this Poco's live FDT.

This describes an initial kernel-entry test, not a functioning iOS platform.
Requires the previously verified MP v2.1 board, timer, GIC and memory layout.
Private FDT input stays local; the generated ADT uses a synthetic identity.
"""
import argparse
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adt
import mkadt

BASE = 0x140000000
WINDOW = 0x10000000
PANIC = 0x100000


def fdt_nodes(blob):
    if len(blob) < 40:
        raise ValueError('Short FDT')
    magic, total, start, strings, reserve, version, compatible, cpu, ns, size = struct.unpack_from('>10I', blob)
    if magic != 0xd00dfeed or total != len(blob) or total > 2 * 1024 * 1024:
        raise ValueError('Invalid FDT header')
    if start < 40 or start & 3 or start + size > total or strings < 40 or strings + ns > total:
        raise ValueError('Invalid FDT blocks')
    nodes, stack, pos, end = {}, [], start, start + size
    while pos + 4 <= end:
        token, = struct.unpack_from('>I', blob, pos)
        pos += 4
        if token == 1:
            stop = blob.find(b'\0', pos, end)
            if stop < 0 or len(stack) >= 64:
                raise ValueError('Invalid FDT node')
            stack.append(blob[pos:stop].decode('ascii'))
            path = '/'.join(stack) or '/'
            if path in nodes:
                raise ValueError('Duplicate FDT node')
            nodes[path] = {}
            pos = (stop + 4) & ~3
        elif token == 2:
            if not stack:
                raise ValueError('Unbalanced FDT')
            stack.pop()
        elif token == 3:
            if not stack or pos + 8 > end:
                raise ValueError('Invalid FDT property')
            length, nameoff = struct.unpack_from('>II', blob, pos)
            pos += 8
            if nameoff >= ns or pos + length > end:
                raise ValueError('Invalid FDT property range')
            stop = blob.find(b'\0', strings + nameoff, strings + ns)
            if stop < 0:
                raise ValueError('Unterminated FDT property')
            key = blob[strings + nameoff:stop].decode('ascii')
            props = nodes['/'.join(stack) or '/']
            if key in props:
                raise ValueError('Duplicate FDT property')
            props[key] = blob[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            if stack:
                raise ValueError('Unbalanced FDT end')
            return nodes
        else:
            raise ValueError('Unknown FDT token')
    raise ValueError('Missing FDT end')


def prop(node, key, value):
    node.props = [(k, f, value if k == key else v) for k, f, v in node.props]


def build(blob):
    nodes = fdt_nodes(blob)
    root = nodes['/']
    if root.get('model') != b'Xiaomi Technologies, Inc. Beryllium MP v2.1\0':
        raise ValueError('Wrong board model')
    if root.get('qcom,board-id') != struct.pack('>II', 69, 0) or root.get('qcom,msm-id') != struct.pack('>II', 321, 0x20001):
        raise ValueError('Wrong board or SoC revision')
    if nodes.get('/psci', {}).get('method') != b'smc\0':
        raise ValueError('Unexpected PSCI conduit')
    gic = nodes.get('/soc/interrupt-controller@17a00000', {})
    if gic.get('reg') != struct.pack('>4I', 0x17a00000, 0x10000, 0x17a60000, 0x100000):
        raise ValueError('Unexpected GIC map')
    timer = nodes.get('/soc/timer', {}).get('interrupts', b'')
    if len(timer) != 48 or struct.unpack_from('>II', timer, 24) != (1, 3):
        raise ValueError('Virtual timer PPI is not INTID 19')
    memory = nodes.get('/memory', {}).get('reg', b'')
    if len(memory) % 16:
        raise ValueError('Invalid memory banks')
    banks = [struct.unpack_from('>QQ', memory, i) for i in range(0, len(memory), 16)]
    if not any(base <= BASE and BASE + WINDOW <= base + size for base, size in banks):
        raise ValueError('Kernel window outside live RAM')
    # Fixed firmware reservations are authoritative. Dynamic reservations here
    # belong to the stopped Linux instance, not to a live allocator in XNU.
    for name, values in nodes.items():
        if not name.startswith('/reserved-memory/') or 'reg' not in values:
            continue
        registers = values['reg']
        if len(registers) % 16:
            raise ValueError('Unexpected reserved-memory cells')
        for i in range(0, len(registers), 16):
            base, size = struct.unpack_from('>QQ', registers, i)
            if base < BASE + WINDOW and BASE < base + size:
                raise ValueError(f'Kernel window intersects {name}')
    tree = mkadt.build(seed=bytes(range(64)))
    # Seed must be fresh for every real build, never the deterministic fixture.
    import os
    chosen = next(c for c in tree.children if c.name == 'chosen')
    prop(chosen, 'random-seed', os.urandom(64))
    prop(chosen, 'dram-base', mkadt.u64(BASE))
    prop(chosen, 'dram-size', mkadt.u64(WINDOW - PANIC))
    prop(chosen, 'firmware-version', mkadt.cstr('beryllium-shim'))
    prop(chosen, 'system-firmware-version', mkadt.cstr('beryllium-shim'))
    cpus = next(c for c in tree.children if c.name == 'cpus')
    cpus.children = cpus.children[:1]
    prop(cpus.children[0], 'compatible', mkadt.cstr('qcom,kryo385') + mkadt.cstr('ARM,v8'))
    fb = next(c for c in tree.children if c.name == 'sweet-fbcon')
    prop(fb, 'reg', mkadt.u64(0x9d400000, 0x2400000))
    prop(fb, 'height', mkadt.u32(2246))
    pram = next(c for c in tree.children if c.name == 'pram')
    prop(pram, 'reg', mkadt.u64(BASE + WINDOW - PANIC, PANIC))
    # The SWEET token selects reused generic platform code; it is not a claim
    # that this hardware is sweet. No storage node means no UFS takeover.
    prop(tree, 'compatible', mkadt.cstr('D22AP') + mkadt.cstr('iPhone10,3') +
         mkadt.cstr('xiaomi,beryllium') + mkadt.cstr('qcom,sdm845') +
         mkadt.cstr('xiaomi,sweet') + mkadt.cstr('AppleARM'))
    tree.children = [c for c in tree.children if c.name != 'sweet-ufs']
    return tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('live_fdt', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    tree = build(args.live_fdt.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(adt.serialize(tree))
    print(f'Poco initial ADT: one CPU, {WINDOW // (1024*1024)} MiB window at {BASE:#x}, no UFS node')
    print('Window is described RAM; runtime XPU accessibility still needs a hardware probe')


if __name__ == '__main__':
    main()
