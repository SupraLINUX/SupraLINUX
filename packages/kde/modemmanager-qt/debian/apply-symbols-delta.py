#!/usr/bin/python3
from __future__ import annotations
import hashlib
from pathlib import Path

PATH = Path('debian/libkf6modemmanagerqt6.symbols')
BASE_SHA256 = '70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2'
RESULT_SHA256 = 'b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f'
ANCHOR = ' _ZTIN12ModemManager10ModemVoiceE@Base 6.0.0'
NEW_SYMBOL = ' (optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f'unexpected ModemManagerQt symbols baseline: {digest(raw)}')

lines = raw.decode().splitlines()
if NEW_SYMBOL in lines or any('_ZSt19piecewise_construct@Base' in line for line in lines):
    raise SystemExit('ModemManagerQt symbols baseline unexpectedly already contains piecewise_construct')
try:
    index = lines.index(ANCHOR)
except ValueError as exc:
    raise SystemExit('ModemManagerQt 6.28 symbols anchor did not match expected baseline') from exc
lines.insert(index, NEW_SYMBOL)
result = ('\n'.join(lines) + '\n').encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f'unexpected reviewed ModemManagerQt symbols result: {digest(result)}')
PATH.write_bytes(result)
