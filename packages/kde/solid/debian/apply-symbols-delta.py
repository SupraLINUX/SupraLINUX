#!/usr/bin/python3
from __future__ import annotations
import hashlib
from pathlib import Path

PATH = Path('debian/libkf6solid6.symbols')
BASE_SHA256 = '4928d196746e4f497733ab7052eea5bf1b219013fb58c6aa4c52284f6e0eb419'
RESULT_SHA256 = '8614c45e8a902f3c3011b8cec65680ab5152314c798a71ebec108fc50fb547d0'
ANCHOR = ' _ZTIN5Solid11OpticalDiscE@Base 6.0.0'
NEW_SYMBOL = ' (optional=toolchain|arch=!armhf !riscv64)_ZSt19piecewise_construct@Base 6.4.0'

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f'unexpected Solid symbols baseline: {digest(raw)}')
lines = raw.decode().splitlines()
if NEW_SYMBOL in lines or any('_ZSt19piecewise_construct@Base' in line for line in lines):
    raise SystemExit('Solid symbols baseline unexpectedly already contains piecewise_construct')
try:
    index = lines.index(ANCHOR)
except ValueError as exc:
    raise SystemExit('Solid 6.28 symbols anchor did not match expected baseline') from exc
lines.insert(index, NEW_SYMBOL)
result = ('\n'.join(lines) + '\n').encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f'unexpected reviewed Solid symbols result: {digest(result)}')
PATH.write_bytes(result)
