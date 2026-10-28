#!/usr/bin/python3
from __future__ import annotations

import hashlib
from pathlib import Path

PATH = Path("debian/libquickcharts1.symbols")
BASE_SHA256 = "ed06cd19136bc5a1bfb10fb7e5c93070fdb4f76ca81f8536243666297e8193e6"
RESULT_SHA256 = "f1ba9c4d179d7dc3638f82fe5879c6ecea43455f520eff686aad508c4e32702e"

REPLACEMENTS = {
    " (arch=!riscv64)_ZTISt15_Sp_counted_ptrIP10QQuickItemLN9__gnu_cxx12_Lock_policyE2EE@Base 6.0.0":
    " (optional=templinst|arch=!riscv64)_ZTISt15_Sp_counted_ptrIP10QQuickItemLN9__gnu_cxx12_Lock_policyE2EE@Base 6.0.0",
    " (arch=!riscv64)_ZTVSt15_Sp_counted_ptrIP10QQuickItemLN9__gnu_cxx12_Lock_policyE2EE@Base 6.0.0":
    " (optional=templinst|arch=!riscv64)_ZTVSt15_Sp_counted_ptrIP10QQuickItemLN9__gnu_cxx12_Lock_policyE2EE@Base 6.0.0",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = PATH.read_bytes()
observed = digest(raw)
if observed != BASE_SHA256:
    raise SystemExit(f"unexpected KQuickCharts symbols baseline: {observed}")

text = raw.decode()
for old, new in REPLACEMENTS.items():
    if text.count(old) != 1:
        raise SystemExit(f"KQuickCharts baseline does not contain exactly one reviewed template symbol: {old}")
    if new in text:
        raise SystemExit(f"KQuickCharts baseline unexpectedly already contains transformed template symbol: {new}")
    text = text.replace(old, new)

result = text.encode()
observed_result = digest(result)
if observed_result != RESULT_SHA256:
    raise SystemExit(f"unexpected reviewed KQuickCharts symbols result: {observed_result}")
PATH.write_bytes(result)
