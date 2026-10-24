#!/usr/bin/python3
from __future__ import annotations
import hashlib
from pathlib import Path

PATH = Path('debian/libkf6bluezqt6.symbols')
BASE_SHA256 = 'b72bea28842160da234b3bbab7975623616cd58f3e522b1e5d8705a279eef4f7'
RESULT_SHA256 = '0fd10c9d93b303fa48aa5cd66aaf4727fbc27f4b784926f5ce5f8d20606bf37a'
ANCHOR = ' _ZTI12QDBusContext@Base 6.0.0'
NEW_SYMBOL = ' (optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f'unexpected BluezQt symbols baseline: {digest(raw)}')

lines = raw.decode().splitlines()
if NEW_SYMBOL in lines or any('_ZSt19piecewise_construct@Base' in line for line in lines):
    raise SystemExit('BluezQt symbols baseline unexpectedly already contains piecewise_construct')
try:
    index = lines.index(ANCHOR)
except ValueError as exc:
    raise SystemExit('BluezQt 6.28 symbols anchor did not match expected baseline') from exc
lines.insert(index, NEW_SYMBOL)
result = ('\n'.join(lines) + '\n').encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f'unexpected reviewed BluezQt symbols result: {digest(result)}')
PATH.write_bytes(result)
