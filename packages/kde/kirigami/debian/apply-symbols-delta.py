#!/usr/bin/python3
from __future__ import annotations

import hashlib
from pathlib import Path

QOBJECT_TEMPLATE_SYMBOLS = [
    "_ZGVZN9QMetaType21registerConverterImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPKvPvEES_S_E10unregister@Base",
    "_ZGVZN9QMetaType23registerMutableViewImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPvS9_EES_S_E10unregister@Base",
    "_ZN13QMetaSequence12MetaSequenceI5QListIP7QObjectEE5valueE@Base",
    "_ZTIZN9QMetaType17registerConverterI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate33QSequentialIterableConvertFunctorIS4_EEEEbT1_EUlPKvPvE_@Base",
    "_ZTIZN9QMetaType19registerMutableViewI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate37QSequentialIterableMutableViewFunctorIS4_EEEEbT1_EUlPvSC_E_@Base",
    "_ZTSZN9QMetaType17registerConverterI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate33QSequentialIterableConvertFunctorIS4_EEEEbT1_EUlPKvPvE_@Base",
    "_ZTSZN9QMetaType19registerMutableViewI5QListIP7QObjectE9QIterableI13QMetaSequenceEN9QtPrivate37QSequentialIterableMutableViewFunctorIS4_EEEEbT1_EUlPvSC_E_@Base",
    "_ZZN9QMetaType21registerConverterImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPKvPvEES_S_E10unregister@Base",
    "_ZZN9QMetaType23registerMutableViewImplI5QListIP7QObjectE9QIterableI13QMetaSequenceEEEbSt8functionIFbPvS9_EES_S_E10unregister@Base",
]

RBTREE_TEMPLATE_SYMBOLS = [
    "_ZNSt8_Rb_treeI7QStringSt4pairIKS0_8QVariantESt10_Select1stIS4_ESt4lessIS0_ESaIS4_EE24_M_get_insert_unique_posERS2_@Base",
    "_ZNSt8_Rb_treeI7QStringSt4pairIKS0_8QVariantESt10_Select1stIS4_ESt4lessIS0_ESaIS4_EE29_M_get_insert_hint_unique_posESt23_Rb_tree_const_iteratorIS4_ERS2_@Base",
]

SPECS = [
    {
        "path": "debian/libkirigamicontrols6.symbols",
        "base_sha256": "18a292f5b614aecb1f71d1f2335989dc6b7217e25dccf511e11b38c1d3206849",
        "result_sha256": "71cc0b7a2622f7b9b98c9d87dfa5e7824743025ff8960fdb5ef28da9ffe67f38",
        "anchor": " _Z44qml_register_types_org_kde_kirigami_controlsv@Base 6.26.0",
        "symbols": [(symbol, "6.30.0") for symbol in QOBJECT_TEMPLATE_SYMBOLS],
    },
    {
        "path": "debian/libkirigamidelegates6.symbols",
        "base_sha256": "b58d788f8cae861b02fdc5a681d84a23adda77d65461b84da0e1368256bfee2f",
        "result_sha256": "7b2f50807ea409c91094e36605a37cf8190910e0be23f8e472a051d9bcbb9954",
        "anchor": " _Z45qml_register_types_org_kde_kirigami_delegatesv@Base 6.0.0",
        "symbols": [(symbol, "6.23.0") for symbol in QOBJECT_TEMPLATE_SYMBOLS],
    },
    {
        "path": "debian/libkirigamiformsprivatecards6.symbols",
        "base_sha256": "080732bf5305417218086c8849c77b08508a7315acfaca5e4e130161c3951614",
        "result_sha256": "4483ccb4b6cc376bb28e5ac408147b8cf3f190b9a394f1b38326d7500671925f",
        "anchor": " _Z55qml_register_types_org_kde_kirigami_forms_private_cardsv@Base 6.26.0",
        "symbols": [(symbol, "6.30.0") for symbol in QOBJECT_TEMPLATE_SYMBOLS],
    },
    {
        "path": "debian/libkirigamiformsprivateflat6.symbols",
        "base_sha256": "6b501c473adb47811bb556bfd3376e5300bfc9af678b09531a375ddd1870089b",
        "result_sha256": "75c25d52c7415502d200b57f4dea7d9a8405aa3df20a2d5ea03349d5812fcc61",
        "anchor": " _Z54qml_register_types_org_kde_kirigami_forms_private_flatv@Base 6.26.0",
        "symbols": [(symbol, "6.30.0") for symbol in QOBJECT_TEMPLATE_SYMBOLS],
    },
    {
        "path": "debian/libkirigamitemplates6.symbols",
        "base_sha256": "c58094969b409f527c6fdcfc5af14ca42da6c604637cfd4b72bcc1f2c03f51e1",
        "result_sha256": "b60af9408ad63c919775ce099d040a5207069dd972e5daee98c974336e038582",
        "anchor": " _Z45qml_register_types_org_kde_kirigami_templatesv@Base 6.18.0",
        "symbols": [(symbol, "6.30.0") for symbol in RBTREE_TEMPLATE_SYMBOLS],
    },
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


for spec in SPECS:
    path = Path(spec["path"])
    raw = path.read_bytes()
    observed = digest(raw)
    if observed != spec["base_sha256"]:
        raise SystemExit(f"unexpected Kirigami symbols baseline for {path.name}: {observed}")

    lines = raw.decode().splitlines()
    additions = [f" (optional=templinst){symbol} {version}" for symbol, version in spec["symbols"]]
    for symbol, _version in spec["symbols"]:
        if any(symbol in line for line in lines):
            raise SystemExit(f"Kirigami baseline unexpectedly already contains reviewed template symbol {symbol} in {path.name}")

    try:
        index = lines.index(spec["anchor"]) + 1
    except ValueError as exc:
        raise SystemExit(f"Kirigami symbols anchor did not match expected baseline for {path.name}") from exc

    lines[index:index] = additions
    result = ("\n".join(lines) + "\n").encode()
    observed_result = digest(result)
    if observed_result != spec["result_sha256"]:
        raise SystemExit(f"unexpected reviewed Kirigami symbols result for {path.name}: {observed_result}")
    path.write_bytes(result)
