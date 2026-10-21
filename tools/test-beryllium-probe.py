#!/usr/bin/env python3
"""Execute the built ARM64 diagnostic with Unicorn, not simulated Python logic.

Requires unicorn in the current interpreter. The image runs at two nonzero
load addresses, with no mapped MMIO except the expected display reservation.
This checks relocation, FDT handling, rendering, and a wrong-device halt.
It does not emulate the Poco bootloader, display controller, or XNU.
"""
import importlib.util
from pathlib import Path
import struct
import unittest

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_X0

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fdt_fixtures', ROOT / 'tools/test-beryllium-fdt.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
FB = 0x9d400000
FB_SIZE = 0x2400000
DTB = 0x85000000


def result_offset():
    data = (ROOT / 'shim/out/beryllium-probe/probe.elf').read_bytes()
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, header[6] + i * header[11])
                for i in range(header[12])]
    for section in sections:
        if section[1] != 2:
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for pos in range(section[4], section[4] + section[5], section[9]):
            name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', data, pos)
            if names[name:].split(b'\0')[0] == b'beryllium_probe_result':
                return value
    raise AssertionError('Diagnostic result symbol absent')


def execute(load, device, blob=None):
    image = (ROOT / 'shim/out/beryllium-probe/Image').read_bytes()
    if image[56:60] != b'ARM\x64' or struct.unpack_from('<Q', image, 16)[0] != len(image):
        raise AssertionError('Build a valid diagnostic Image first')
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(load, (len(image) + 4095) & ~4095)
    uc.mem_write(load, image)
    blob = blob if blob is not None else fixtures.fixture(device=device)
    uc.mem_map(DTB, (len(blob) + 4095) & ~4095)
    uc.mem_write(DTB, blob)
    uc.mem_map(FB, FB_SIZE)
    uc.reg_write(UC_ARM64_REG_X0, DTB)
    reached_halt = []

    def step(engine, address, size, unused):
        if bytes(engine.mem_read(address, 4)) == b'\x5f\x20\x03\xd5':  # WFE
            reached_halt.append(address)
            engine.emu_stop()

    uc.hook_add(UC_HOOK_CODE, step)
    uc.emu_start(load, load + len(image), timeout=30000000, count=60000000)
    if not reached_halt:
        raise AssertionError(f'Did not reach halt, PC={uc.reg_read(UC_ARM64_REG_PC):#x}')
    # Main memory outside the CPU image, FDT and framebuffer was never mapped;
    # unintended storage, PMIC or interrupt-controller access would fault.
    outcome, = struct.unpack('<I', bytes(uc.mem_read(load + result_offset(), 4)))
    expected = 1 if device == 'xiaomi,beryllium' else 0
    if outcome != expected:
        raise AssertionError(f'Diagnostic outcome {outcome}, expected {expected}')
    return bytes(uc.mem_read(FB, 4320 * 2246))


class DiagnosticTests(unittest.TestCase):
    def test_valid_device_draws_blue_screen_at_two_load_addresses(self):
        for load in [0x80080000, 0x88000000]:
            with self.subTest(load=hex(load)):
                screen = execute(load, 'xiaomi,beryllium')
                self.assertEqual(screen[:4], struct.pack('<I', 0xff0000a0))
                self.assertIn(struct.pack('<I', 0xffffffff), screen)
                self.assertIn(struct.pack('<I', 0xffffff00), screen)
                self.assertEqual(screen[-4:], struct.pack('<I', 0xff0000a0))

    def test_downstream_tuple_reaches_completion(self):
        execute(0x80080000, 'xiaomi,beryllium', fixtures.fixture(downstream=True))

    @unittest.skipUnless((ROOT / 'dtb/poco-f1/live.dtb').exists(), 'No local hardware dump')
    def test_local_hardware_tree_reaches_completion(self):
        execute(0x80080000, 'xiaomi,beryllium', (ROOT / 'dtb/poco-f1/live.dtb').read_bytes())

    def test_wrong_device_halts_without_writing_framebuffer(self):
        screen = execute(0x80080000, 'xiaomi,sweet')
        self.assertEqual(screen, bytes(len(screen)))


if __name__ == '__main__':
    unittest.main()
