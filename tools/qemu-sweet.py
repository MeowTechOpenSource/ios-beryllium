#!/usr/bin/env python3
"""Compatibility entry point for the original Redmi QEMU profile."""
import runpy
import sys
from pathlib import Path
if __name__ == '__main__':
    if not any(arg == '--profile' or arg.startswith('--profile=') for arg in sys.argv[1:]):
        sys.argv.extend(['--profile', 'sweet'])
    runpy.run_path(str(Path(__file__).with_name('qemu-beryllium.py')), run_name='__main__')
