#!/usr/bin/env python3
"""Exercise the actual C parser before allowing framebuffer writes on hardware."""
import ctypes
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
U32 = lambda x: struct.pack('>I', x)
U64 = lambda x: struct.pack('>Q', x)


def fixture(device='xiaomi,beryllium', height=2246, base=0x9d400000,
            fmt='a8r8g8b8', region=True, status='okay', duplicate=False):
    strings = bytearray()
    tokens = bytearray()

    def begin(name):
        tokens.extend(U32(1) + name.encode() + b'\0')
        tokens.extend(bytes(-len(tokens) % 4))

    def end():
        tokens.extend(U32(2))

    def prop(name, value):
        offset = len(strings)
        strings.extend(name.encode() + b'\0')
        tokens.extend(U32(3) + U32(len(value)) + U32(offset) + value)
        tokens.extend(bytes(-len(tokens) % 4))

    begin('')
    prop('compatible', device.encode() + b'\0')
    prop('#address-cells', U32(2))
    prop('#size-cells', U32(2))
    begin('chosen')
    prop('#address-cells', U32(2))
    prop('#size-cells', U32(2))
    for i in range(2 if duplicate else 1):
        begin('framebuffer' + str(i))
        prop('compatible', b'simple-framebuffer\0')
        prop('format', fmt.encode() + b'\0')
        prop('width', U32(1080))
        prop('height', U32(height))
        prop('stride', U32(4320))
        prop('status', status.encode() + b'\0')
        prop('memory-region', U32(42)) if region else prop('reg', U64(base) + U64(0x2400000))
        end()
    end()
    if region:
        begin('reserved-memory')
        prop('#address-cells', U32(2))
        prop('#size-cells', U32(2))
        prop('ranges', b'')
        begin('framebuffer@9d400000')
        prop('phandle', U32(42))
        prop('reg', U64(base) + U64(0x2400000))
        end()
        end()
    end()
    tokens.extend(U32(9))
    structure_offset = 56  # header + terminating reserve-map entry
    string_offset = structure_offset + len(tokens)
    total = string_offset + len(strings)
    header = struct.pack('>10I', 0xd00dfeed, total, structure_offset,
                         string_offset, 40, 17, 16, 0, len(strings), len(tokens))
    return header + bytes(16) + tokens + strings


class Framebuffer(ctypes.Structure):
    _fields_ = [('base', ctypes.c_uint64), ('size', ctypes.c_uint64)]


class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        library = Path(cls.temp.name) / 'parser.dylib'
        subprocess.run(['clang', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=undefined', str(ROOT / 'shim/beryllium_fdt.c'),
                        '-o', str(library)], check=True)
        cls.lib = ctypes.CDLL(str(library))
        cls.lib.beryllium_framebuffer.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                                 ctypes.POINTER(Framebuffer)]
        cls.lib.beryllium_framebuffer.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def parse(self, data):
        blob = ctypes.create_string_buffer(bytes(data))
        fb = Framebuffer(0xdead, 0xbeef)
        result = self.lib.beryllium_framebuffer(blob, len(data), ctypes.byref(fb))
        if not result:
            self.assertEqual((fb.base, fb.size), (0xdead, 0xbeef))
        return result, fb

    def test_memory_region_resolved_after_chosen(self):
        result, fb = self.parse(fixture())
        self.assertEqual(result, 1)
        self.assertEqual((fb.base, fb.size), (0x9d400000, 0x2400000))

    def test_direct_reg(self):
        self.assertEqual(self.parse(fixture(region=False))[0], 1)

    def test_wrong_hardware_or_geometry_rejected(self):
        for args in [dict(device='xiaomi,sweet'), dict(height=2400),
                     dict(base=0x9c000000), dict(fmt='r5g6b5'),
                     dict(status='disabled'), dict(duplicate=True)]:
            with self.subTest(args=args):
                self.assertEqual(self.parse(fixture(**args))[0], 0)

    def test_all_truncations_rejected(self):
        data = fixture()
        for size in range(len(data)):
            with self.subTest(size=size):
                self.assertEqual(self.parse(data[:size])[0], 0)

    def test_bad_header_ranges(self):
        for offset, value in [(0, 0), (4, 0xffffffff), (8, 0xfffffffc),
                              (12, 0xffffffff), (32, 0xffffffff), (36, 0xffffffff)]:
            data = bytearray(fixture())
            struct.pack_into('>I', data, offset, value)
            self.assertEqual(self.parse(data)[0], 0)


if __name__ == '__main__':
    unittest.main()
