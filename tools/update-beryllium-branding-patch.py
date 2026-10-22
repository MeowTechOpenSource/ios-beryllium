#!/usr/bin/env python3
"""Regenerate target diagnostic labels from the audited local 0081 source tree.

Apply 0082–0084 first in a disposable tree, then change diagnostic literals only.
Historical patches and internal compatibility identifiers remain unchanged.
"""
from pathlib import Path
import difflib
import re
import shutil
import subprocess
import tempfile
r=Path(__file__).resolve().parents[1]
files=['iokit/Kernel/arm/'+n for n in ['SweetCPU.cpp','SweetPlatformExpert.cpp','SweetFramebuffer.cpp','SweetWatchdog.cpp','SweetKeyStore.cpp','SweetSurface.cpp','SweetBattery.cpp','hid/SweetHID.cpp']]
files += ['pexpert/arm/pe_fiq.c','bsd/netinet/in.c','bsd/net/rtsock.c','osfmk/arm64/sweet_early.c','osfmk/prng/prng_random.c','iokit/bsddev/IOKitBSDInit.cpp','bsd/kern/bsd_init.c','bsd/kern/sweet_amfi.c','bsd/kern/kern_trustcache.c','bsd/pthread/sweet_pthread_init.c','bsd/sweet_hfs/sweet_hfs_iokit.c','bsd/sweet_hfs/core/hfs_vfsutils.c','bsd/dev/sweet_ufs.c']
with tempfile.TemporaryDirectory(prefix='beryllium-brand-') as d:
 t=Path(d)
 for f in files:
  dst=t/f;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/'research/upstream-0081/xnu'/f,dst)
 # Existing overlays also touch files beyond the branding set.
 for patch in sorted((r/'ports/beryllium/xnu').glob('008[234]-*.patch')):
  names=re.findall(r'^\+\+\+ b/(.+)$',patch.read_text(),re.M)
  for f in names:
   dst=t/f; src=r/'research/upstream-0081/xnu'/f
   if not dst.exists() and src.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  subprocess.run(['git','apply','--unsafe-paths',str(patch)],cwd=t,check=True)
 out=[];count=0
 for f in files:
  old=(t/f).read_text()
  # Only diagnostic string contents; not preprocessor flags, symbols, filenames,
  # device-tree matches, boot arguments or on-disk formats.
  new=re.sub(r'"(?:[^"\\]|\\.)*"',lambda m: m[0].replace('SWEET','BERYLLIUM') if re.search(r'SWEET(?: |:)',m[0]) else m[0],old)
  # Independently assert that only SWEET text in string literals changed.
  literal = r'"(?:[^"\\]|\\.)*"'
  assert re.sub(literal, '""', old) == re.sub(literal, '""', new), f
  assert new.replace('BERYLLIUM', 'SWEET') == old.replace('BERYLLIUM', 'SWEET'), f
  if new!=old:
   count+=old.count('SWEET')-new.count('SWEET')
   out.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+f,tofile='b/'+f))
 patch=r/'ports/beryllium/xnu/0085-beryllium-diagnostic-branding.patch';patch.write_text(''.join(out))
 subprocess.run(['git','apply','--check',str(patch)],cwd=t,check=True)
 subprocess.run(['git','apply',str(patch)],cwd=t,check=True)
 print('Branding replacements:',count,'files:',len(files))
