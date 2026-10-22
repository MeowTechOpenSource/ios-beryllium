#!/usr/bin/env python3
"""Stream an exact raw image into Android sparse RAW/FILL chunks; never flash.

DONT_CARE is deliberately not emitted: every source byte, including zeroes,
has a defined write value. Each chunk stays small for old bootloaders.
Format: AOSP system/core/libsparse sparse_format.h (v1.0).
"""
import argparse
import hashlib
from pathlib import Path
import struct

MAGIC, RAW, FILL = 0xed26ff3a, 0xcac1, 0xcac2
BLOCK, RAW_LIMIT = 4096, 4 * 1024 * 1024

def encode(source, target):
    """Return (raw bytes, chunks, SHA256) with <=4MiB RAW buffering."""
    target.write(bytes(28))
    chunks = blocks = 0
    digest = hashlib.sha256()
    kind, count, body = None, 0, bytearray()
    def flush():
        nonlocal chunks, kind, count, body
        if not count: return
        target.write(struct.pack('<HHII',kind,0,count,12+len(body)))
        target.write(body)
        chunks += 1
        kind, count, body = None, 0, bytearray()
    while True:
        block = source.read(BLOCK)
        if not block: break
        if len(block) != BLOCK: raise ValueError('raw image is not block-aligned')
        digest.update(block)
        blocks += 1
        if blocks > 0xffffffff: raise ValueError('too many sparse blocks')
        word = block[:4]
        fill = block == word * (BLOCK//4)
        next_kind = FILL if fill else RAW
        if count and (kind != next_kind or (fill and body != word) or
                      (not fill and len(body) >= RAW_LIMIT)):
            flush()
        kind = next_kind
        count += 1
        if fill: body[:] = word
        else: body.extend(block)
    flush()
    if not blocks: raise ValueError('empty raw image')
    target.seek(0)
    target.write(struct.pack('<IHHHHIIII',MAGIC,1,0,28,12,BLOCK,blocks,chunks,0))
    return blocks*BLOCK, chunks, digest.hexdigest()

def verify(source):
    """Hash the expanded RAW/FILL stream without materializing it."""
    header = source.read(28)
    if len(header)!=28: raise ValueError('short sparse header')
    magic,major,minor,fhs,chs,block,total,chunks,crc=struct.unpack('<IHHHHIIII',header)
    if (magic,major,minor,fhs,chs,block,crc)!=(MAGIC,1,0,28,12,BLOCK,0):
        raise ValueError('unsupported sparse header')
    digest=hashlib.sha256();done=0
    for _ in range(chunks):
        raw=source.read(12)
        if len(raw)!=12: raise ValueError('short chunk header')
        kind,reserved,n,size=struct.unpack('<HHII',raw)
        if reserved or not n or n>total-done: raise ValueError('invalid chunk span')
        length=n*BLOCK
        if kind==RAW:
            if size!=12+length: raise ValueError('wrong RAW size')
            while length:
                b=source.read(min(length,1024*1024))
                if not b: raise ValueError('short RAW data')
                digest.update(b);length-=len(b)
        elif kind==FILL:
            word=source.read(4)
            if size!=16 or len(word)!=4: raise ValueError('wrong FILL size')
            unit=word*(min(length,1024*1024)//4)
            while length:
                part=unit[:min(length,len(unit))];digest.update(part);length-=len(part)
        else: raise ValueError('unverifiable chunk type')
        done+=n
    if done!=total or source.read(1): raise ValueError('sparse total or trailing data mismatch')
    return done*BLOCK,digest.hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--expected-sha256',required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('refusing to overwrite existing output')
    part=a.output.with_name(a.output.name+'.part')
    if part.exists(): p.error('partial output already exists')
    try:
        with a.raw.open('rb') as src, part.open('w+b') as dst:
            size,chunks,digest=encode(src,dst)
            if digest!=a.expected_sha256: raise ValueError('source SHA256 mismatch')
            dst.flush();dst.seek(0)
            if verify(dst)!=(size,digest): raise ValueError('expanded sparse verification failed')
        part.rename(a.output)
        print(f'Exact sparse image verified: {size} raw bytes, {chunks} chunks, SHA256 {digest}')
    except BaseException:
        part.unlink(missing_ok=True)
        raise
