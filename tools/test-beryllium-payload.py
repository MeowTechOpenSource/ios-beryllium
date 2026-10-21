#!/usr/bin/env python3
"""Exercise the C pre-copy bounds guard using generated and malformed payloads."""
import ctypes
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VIRT = 0xfffffff006000000
PHYS = 0x140000000
MEM = 0xff00000
HEADER = 0x2a8


def payload(two=False):
    count = 2 if two else 1
    table = HEADER + count * 32
    body = (table + 15) & ~15
    data = bytearray(body + 64)
    struct.pack_into('<8sII7Q', data, 0, b'SWEETXNU', 1, count,
                     VIRT, VIRT + 0x1000, body + 32, 16, VIRT + 0x4000,
                     PHYS, MEM)
    struct.pack_into('<4Q', data, HEADER, VIRT, 0x4000, body, 16)
    if two:
        struct.pack_into('<4Q', data, HEADER + 32, VIRT + 0x8000, 0x4000, body + 16, 16)
        struct.pack_into('<Q', data, 0x30, VIRT + 0xc000)
    # Put entry in file-backed bytes, not BSS.
    struct.pack_into('<Q', data, 0x18, VIRT)
    return data


class BoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        lib = Path(cls.temp.name) / 'bounds.dylib'
        subprocess.run(['clang', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=undefined', str(ROOT / 'shim/beryllium_payload.c'),
                        '-o', str(lib)], check=True)
        cls.lib = ctypes.CDLL(str(lib))
        cls.lib.beryllium_payload_check.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
        cls.lib.beryllium_payload_check.restype = ctypes.c_char_p

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check(self, data, start=0x90000000):
        blob = ctypes.create_string_buffer(bytes(data))
        return self.lib.beryllium_payload_check(blob, len(data), start)

    def test_valid_one_and_two_segments(self):
        self.assertIsNone(self.check(payload()))
        self.assertIsNone(self.check(payload(True)))

    def test_wrong_window_and_virtual_overflow(self):
        for offset, value in [(0x38, 0x100000000), (0x40, MEM + 0x1000),
                              (0x10, 0xffffffffff000000), (0x30, VIRT + MEM + 0x4000)]:
            data = payload()
            struct.pack_into('<Q', data, offset, value)
            self.assertIsNotNone(self.check(data))

    def test_entry_must_be_loaded(self):
        data = payload()
        struct.pack_into('<Q', data, 0x18, VIRT + 0x1000)
        self.assertIn(b'entry', self.check(data))

    def test_initrd_must_not_overlap_or_wrap(self):
        self.assertIsNotNone(self.check(payload(), PHYS))
        self.assertIsNotNone(self.check(payload(), 0xfffffffffffffff8))
        self.assertIsNotNone(self.check(payload(), 0x90000001))

    def test_segments_must_not_overlap(self):
        data = payload(True)
        struct.pack_into('<Q', data, HEADER + 32, VIRT)
        self.assertIn(b'overlapping', self.check(data))

    def test_truncated_table_and_out_of_range_data(self):
        data = payload()
        self.assertIsNotNone(self.check(data[:HEADER + 16]))
        struct.pack_into('<Q', data, HEADER + 16, len(data) + 8)
        self.assertIsNotNone(self.check(data))

    def test_command_line_must_terminate(self):
        data = payload()
        data[0x48:HEADER] = b'x' * 608
        self.assertIn(b'command line', self.check(data))


if __name__ == '__main__':
    unittest.main()
