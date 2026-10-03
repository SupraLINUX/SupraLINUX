#!/usr/bin/python3
from __future__ import annotations
import hashlib
from pathlib import Path

PATH = Path("debian/libkf6configgui6.symbols")
BASE_SHA256 = "c131c44659cce576fbc0754a2a55fd470aa9c065f3efc7d92b49c0042dc758ea"
RESULT_SHA256 = "8a8220263cd60e88208e68138cb0f7288a4d99d3a99c0349e62be314d9d1fd04"
ANCHOR = " _ZN16KStandardActions19shortcutForActionIdENS_14StandardActionE@Base 6.3.0"
NEW_SYMBOL = " _ZN16KStandardActions16staticMetaObjectE@Base 6.29.0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f"unexpected KConfig ConfigGui symbols baseline: {digest(raw)}")

lines = raw.decode().splitlines()
if NEW_SYMBOL in lines or any("_ZN16KStandardActions16staticMetaObjectE@Base" in line for line in lines):
    raise SystemExit("KConfig ConfigGui baseline unexpectedly already contains KStandardActions::staticMetaObject")
try:
    index = lines.index(ANCHOR)
except ValueError as exc:
    raise SystemExit("KConfig 6.28 ConfigGui symbols anchor did not match expected baseline") from exc
lines.insert(index, NEW_SYMBOL)
result = ("\n".join(lines) + "\n").encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f"unexpected reviewed KConfig ConfigGui symbols result: {digest(result)}")
PATH.write_bytes(result)
