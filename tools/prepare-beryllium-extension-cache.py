#!/usr/bin/env python3
"""Prepare one development-only Poco FeatureFlags plist; never writes a phone.

Usage: prepare-beryllium-extension-cache.py ORIGINAL.plist OUTPUT.plist
The source is retained unchanged. Install is a separate image-preparation step.
"""
import argparse
from pathlib import Path
import plistlib


def prepare(source):
    data = plistlib.loads(source)
    key = 'enforce_xpc_cache_code_signing'
    if not isinstance(data, dict) or not isinstance(data.get(key), dict):
        raise ValueError('Unexpected ExtensionKit FeatureFlags layout')
    if type(data[key].get('Enabled')) is not bool:
        raise ValueError('Expected a boolean Enabled field')
    data[key]['Enabled'] = False
    fmt = plistlib.FMT_BINARY if source.startswith(b'bplist') else plistlib.FMT_XML
    return plistlib.dumps(data, fmt=fmt, sort_keys=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = prepare(args.source.read_bytes())
    with args.output.open('xb') as out:
        out.write(result)
    print('Prepared ExtensionKit/enforce_xpc_cache_code_signing = false')
    print('Local candidate only; no installed image or phone was modified.')
