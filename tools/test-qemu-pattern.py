#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct
import unittest
spec=importlib.util.spec_from_file_location('qemu_beryllium',Path(__file__).with_name('qemu-beryllium.py'))
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class PatternTests(unittest.TestCase):
    def setUp(self):
        self.saved=q.FB_W,q.FB_H,q.FB_STRIDE
        q.FB_W,q.FB_H,q.FB_STRIDE=8,3,32
        border=[0xffffffff]*8
        middle=[0xffffffff,0xffffff00,0xff00ffff,0xff00ff00,0xffff00ff,0xffff0000,0xff0000ff,0xffffffff]
        self.frame=bytearray(struct.pack('<24I',*(border+middle+border)))
    def tearDown(self):q.FB_W,q.FB_H,q.FB_STRIDE=self.saved
    def test_clean_and_single_pixel_overlay(self):
        self.assertEqual(q.pattern_difference(self.frame),0)
        struct.pack_into('<I',self.frame,4*(8+3),0xff000000)
        self.assertEqual(q.pattern_difference(self.frame),1)
    def test_both_target_panic_labels(self):
        for label in ('SWEET EARLY PANIC:', 'BERYLLIUM EARLY PANIC:', 'panic(cpu 0'):
            self.assertEqual(q.screen_result(label, 0)['status'], 'panic')
    def test_border_and_short_frame(self):
        struct.pack_into('<I',self.frame,0,0)
        self.assertEqual(q.pattern_difference(self.frame),1)
        with self.assertRaises(ValueError):q.pattern_difference(self.frame[:-1])
if __name__=='__main__':unittest.main()
