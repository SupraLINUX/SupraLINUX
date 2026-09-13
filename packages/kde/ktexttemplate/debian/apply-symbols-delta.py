#!/usr/bin/python3
from __future__ import annotations

import hashlib
from pathlib import Path

PATH = Path("debian/libkf6texttemplate6.symbols")
BASE_SHA256 = "552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273"
RESULT_SHA256 = "2ff2111ce15f910328557c3295008fa21588518a0156626425df3c7b9f1b0e19"
REMOVE = {
    "_ZGVZN9QMetaType21registerConverterImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPKvPvEES_S_E10unregister@Base",
    "_ZGVZN9QMetaType23registerMutableViewImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPvS9_EES_S_E10unregister@Base",
    "_ZN13QMetaSequence12MetaSequenceI5QListIP7QObjectEE5valueE@Base",
    "_ZTIZN9QMetaType17registerConverterI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate33QSequentialIterableConvertFunctorIS4_EEEEbT1_EUlPKvPvE_@Base",
    "_ZTIZN9QMetaType19registerMutableViewI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate37QSequentialIterableMutableViewFunctorIS4_EEEEbT1_EUlPvSC_E_@Base",
    "_ZTSZN9QMetaType17registerConverterI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate33QSequentialIterableConvertFunctorIS4_EEEEbT1_EUlPKvPvE_@Base",
    "_ZTSZN9QMetaType19registerMutableViewI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate37QSequentialIterableMutableViewFunctorIS4_EEEEbT1_EUlPvSC_E_@Base",
    "(optional=templinst)_ZZN9QMetaType21registerConverterImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPKvPvEES_S_E10unregister@Base",
    "(optional=templinst)_ZZN9QMetaType23registerMutableViewImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPvS9_EES_S_E10unregister@Base",
    "qt_plugin_instance@Base",
    "qt_plugin_query_metadata_v2@Base",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = PATH.read_bytes()
if digest(raw) != BASE_SHA256:
    raise SystemExit(f"unexpected KTextTemplate symbols baseline: {digest(raw)}")

out: list[str] = []
ctor_anchor = False
context_anchor = False
exception_vtable = False
for line in raw.decode().splitlines():
    symbol = line.lstrip().split(" ", 1)[0]
    if symbol in REMOVE:
        continue
    if symbol == "_ZTVN13KTextTemplate9ExceptionE@Base":
        out.append(" (optional=inline)_ZTVN13KTextTemplate9ExceptionE@Base 6.0.0")
        exception_vtable = True
        continue
    out.append(line)
    if symbol == "_ZN13KTextTemplate6Filter9setStreamEPNS_12OutputStreamE@Base":
        out += [
            " _ZN13KTextTemplate6FilterC1Ev@Base 6.30.0",
            " _ZN13KTextTemplate6FilterC2Ev@Base 6.30.0",
        ]
        ctor_anchor = True
    elif symbol == "_ZNK13KTextTemplate6Filter6isSafeEv@Base":
        out.append(" _ZNK13KTextTemplate6Filter7contextEv@Base 6.30.0")
        context_anchor = True

if not (ctor_anchor and context_anchor and exception_vtable):
    raise SystemExit("KTextTemplate 6.28 symbols anchors did not match expected baseline")

result = ("\n".join(out) + "\n").encode()
if digest(result) != RESULT_SHA256:
    raise SystemExit(f"unexpected reviewed KTextTemplate symbols result: {digest(result)}")
PATH.write_bytes(result)
