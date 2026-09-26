#!/usr/bin/python3
from __future__ import annotations
import hashlib
from pathlib import Path

PATH = Path("debian/libkf6sonnetcore6.symbols")
BASE_SHA256 = "da300d1551304beac95a201ecd5c27fbf1286fe1e2ef7ab893b959e5e656f2b6"
RESULT_SHA256 = "e75af49fd74700ef8a2c21ce55decaf96439479223770c63654410f3c3f956bb"
ANCHOR = " _ZN6Sonnet8Settings22skipRunTogetherChangedEv@Base 6.0.0"
NEW_SYMBOL = " _ZN6Sonnet8Settings22defaultSkipRunTogetherEv@Base 6.30.0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f"unexpected SonnetCore symbols baseline: {digest(raw)}")

lines = raw.decode().splitlines()
if NEW_SYMBOL in lines or any("_ZN6Sonnet8Settings22defaultSkipRunTogetherEv@Base" in line for line in lines):
    raise SystemExit("SonnetCore baseline unexpectedly already contains Settings::defaultSkipRunTogether")
try:
    index = lines.index(ANCHOR)
except ValueError as exc:
    raise SystemExit("Sonnet 6.28 SonnetCore symbols anchor did not match expected baseline") from exc
lines.insert(index, NEW_SYMBOL)
result = ("\n".join(lines) + "\n").encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f"unexpected reviewed SonnetCore symbols result: {digest(result)}")
PATH.write_bytes(result)
