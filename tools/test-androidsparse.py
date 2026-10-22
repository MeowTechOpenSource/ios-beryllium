#!/usr/bin/env python3
import io
import hashlib
import struct
import unittest
from mkandroidsparse import encode,verify,BLOCK,RAW_LIMIT
class SparseTests(unittest.TestCase):
    def test_exact_mixed_zero_fill_raw_and_chunk_split(self):
        data=bytes(BLOCK*2)+b'ABCD'*(BLOCK//4)+bytes(range(256))*(RAW_LIMIT//256+32)+bytes(BLOCK)
        sparse=io.BytesIO();size,chunks,digest=encode(io.BytesIO(data),sparse)
        self.assertGreater(chunks,4)
        self.assertEqual(digest,hashlib.sha256(data).hexdigest())
        sparse.seek(0);self.assertEqual(verify(sparse),(len(data),digest))
    def test_unaligned_and_empty_refused(self):
        for b in [b'',b'x',bytes(BLOCK+1)]:
            with self.assertRaises(ValueError):encode(io.BytesIO(b),io.BytesIO())
    def test_truncated_corrupt_and_unspecified_chunks_refused(self):
        out=io.BytesIO();encode(io.BytesIO(bytes(BLOCK)),out);b=out.getvalue()
        for n in range(len(b)):
            with self.assertRaises(ValueError):verify(io.BytesIO(b[:n]))
        for offset,fmt,value in [(0,'I',0),(16,'I',0),(28,'H',0xcac3),(32,'I',2),(36,'I',12)]:
            bad=bytearray(b);struct.pack_into('<'+fmt,bad,offset,value)
            with self.assertRaises(ValueError):verify(io.BytesIO(bad))
        with self.assertRaises(ValueError):verify(io.BytesIO(b+b'x'))
if __name__=='__main__':unittest.main()
