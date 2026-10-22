#!/usr/bin/env python3
"""Poco display/CPU-driver profile on QEMU virt; not a Poco SoC emulator."""
import argparse
from pathlib import Path
import adt
import mkadt
from mkberylliumadt import BASE, WINDOW, PANIC, prop

def build():
    tree = mkadt.build(qemu=True)
    chosen = next(c for c in tree.children if c.name == 'chosen')
    prop(chosen, 'dram-base', mkadt.u64(BASE))
    prop(chosen, 'dram-size', mkadt.u64(WINDOW - PANIC))
    cpus = next(c for c in tree.children if c.name == 'cpus')
    prop(cpus.children[0], 'compatible', mkadt.cstr('qcom,kryo385') + mkadt.cstr('ARM,v8'))
    fb = next(c for c in tree.children if c.name == 'sweet-fbcon')
    prop(fb, 'reg', mkadt.u64(0x9d400000, 0x944000))
    prop(fb, 'height', mkadt.u32(2246))
    pram = next(c for c in tree.children if c.name == 'pram')
    prop(pram, 'reg', mkadt.u64(BASE + WINDOW - PANIC, PANIC))
    tree.children = [c for c in tree.children if c.name != 'sweet-ufs']
    return tree

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(adt.serialize(build()))
