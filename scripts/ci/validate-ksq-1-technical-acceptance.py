#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
FULL = ROOT / "build/ksq-1/full"
REPRO = ROOT / "build/ksq-1/repro/acceptance"
ORIGINAL = ROOT / "build/ksq-1/original-full-validation"
KSQ0 = ROOT / "build/ksq-1/ksq0-normalized"
RUNS = ROOT / "tests/kde-stack/ksq-1-acceptance-runs.env"
OUT = ROOT / "build/ksq-1/technical-acceptance"


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"missing env file: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"{path}: malformed line {line!r}")
        key, value = line.split("=", 1)
        if key in values:
            fail(f"{path}: duplicate key {key}")
        values[key] = value
    return values


def require(values: dict[str, str], expected: dict[str, str], label: str) -> None:
    for key, value in expected.items():
        if values.get(key) != value:
            fail(f"{label}: {key}={values.get(key)!r}, expected {value!r}")


def require_same_file(left: Path, right: Path, label: str) -> None:
    if not left.is_file() or not right.is_file():
        fail(f"{label}: missing file(s) {left} / {right}")
    if left.read_bytes() != right.read_bytes():
        fail(f"{label}: files differ")


def main() -> int:
    runs = read_env(RUNS)
    require(runs, {"AURORA_KSQ_1_ACCEPTANCE_RUNS_STATUS": "ACTIVE"}, "run selection")
    for key in (
        "AURORA_KSQ_1_CANDIDATE_RUN_ID",
        "AURORA_KSQ_1_REFERENCE_RUN_ID",
        "AURORA_KSQ_1_REPRO_RUN_ID",
        "AURORA_KSQ_1_KSQ0_CLOSURE_RUN_ID",
        "AURORA_KSQ_1_KSQ0_INVENTORY_RUN_ID",
    ):
        value = runs.get(key, "")
        if not value.isdigit():
            fail(f"run selection: {key} is not numeric: {value!r}")
    if runs["AURORA_KSQ_1_CANDIDATE_RUN_ID"] == runs["AURORA_KSQ_1_REFERENCE_RUN_ID"]:
        fail("candidate and reference run IDs must differ")

    repro_runs = read_env(REPRO / "repro-runs.env")
    require(
        repro_runs,
        {
            "AURORA_KSQ_1_REPRO_RUNS_STATUS": "ACTIVE",
            "AURORA_KSQ_1_CANDIDATE_RUN_ID": runs["AURORA_KSQ_1_CANDIDATE_RUN_ID"],
            "AURORA_KSQ_1_REFERENCE_RUN_ID": runs["AURORA_KSQ_1_REFERENCE_RUN_ID"],
        },
        "reproducibility provenance",
    )

    closure = read_env(KSQ0 / "closure-status.env")
    require(
        closure,
        {
            "AURORA_KSQ_0_CLOSURE_STATUS": "COMPLETE",
            "AURORA_KSQ_0_CLOSURE_UNRESOLVED": "0",
            "AURORA_KSQ_0_CLOSURE_SOURCES": "101",
            "AURORA_KSQ_0_CLOSURE_BUILD_ORDERED": "101",
        },
        "KSQ-0 closure regression",
    )
    if (KSQ0 / "unresolved.tsv").read_text(encoding="utf-8").count("\n") != 1:
        fail("KSQ-0 regression unresolved.tsv is not header-only")
    if (KSQ0 / "source-selections-applied.tsv").read_text(encoding="utf-8").count("\n") != 4:
        fail("KSQ-0 regression did not record exactly three source selections")
    if (KSQ0 / "build-dep-overrides-applied.tsv").read_text(encoding="utf-8").count("\n") != 2:
        fail("KSQ-0 regression did not record exactly one Build-Depends override")

    for name in (
        "release-sets.tsv",
        "plasma-6.7.4-sources.tsv",
        "frameworks-6.29.0-sources.tsv",
        "aurora-package-roots.tsv",
    ):
        require_same_file(ROOT / "tests/kde-stack" / name, KSQ0 / "inventory" / name, f"KSQ-0 inventory {name}")
    urls = KSQ0 / "inventory/validated-source-urls.tsv"
    if not urls.is_file() or len(urls.read_text(encoding="utf-8").splitlines()) < 2:
        fail("KSQ-0 inventory validated source URLs missing/empty")

    full = read_env(FULL / "full-build-status.env")
    require(
        full,
        {
            "AURORA_KSQ_1_FULL_BUILD_STATUS": "PASS",
            "AURORA_KSQ_1_FULL_BUILD_SOURCES": "101",
            "AURORA_KSQ_1_FULL_BUILD_CHECKPOINTS": "5",
            "AURORA_KSQ_1_FULL_BUILD_KWALLET_PAM": "PASS",
            "AURORA_KSQ_1_FULL_BUILD_REPRODUCIBILITY_CERTIFIED": "no",
            "AURORA_KSQ_1_FULL_CERTIFIED": "no",
        },
        "full build",
    )
    try:
        if int(full["AURORA_KSQ_1_FULL_BUILD_BINARIES"]) < 101:
            fail("full build reports fewer binary packages than source packages")
    except (KeyError, ValueError):
        fail("full build binary count missing/invalid")

    kwallet = read_env(FULL / "kwallet-validation/status.env")
    require(
        kwallet,
        {
            "AURORA_KSQ_1_KWALLET_BINARY_RUNTIME_DEPS": "PASS",
            "AURORA_KSQ_1_KWALLET_PAM_INSTALLATION": "PASS",
            "AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED": "no",
        },
        "KWallet package gate",
    )

    repro = read_env(REPRO / "reproducibility-status.env")
    require(
        repro,
        {
            "AURORA_KSQ_1_REPRODUCIBILITY_STATUS": "PASS",
            "AURORA_KSQ_1_REPRODUCIBILITY_SOURCES": "101",
            "AURORA_KSQ_1_REPRODUCIBILITY_REFERENCE_SOURCES": "95",
            "AURORA_KSQ_1_REPRODUCIBILITY_DEDICATED_SOURCES": "6",
            "AURORA_KSQ_1_REPRODUCIBILITY_BYTE_IDENTICAL": "yes",
            "AURORA_KSQ_1_FULL_CERTIFIED": "no",
        },
        "reproducibility",
    )
    if repro.get("AURORA_KSQ_1_REPRODUCIBILITY_BINARIES") != full.get("AURORA_KSQ_1_FULL_BUILD_BINARIES"):
        fail("full-build and reproducibility binary counts differ")

    for name in (
        "full-build-manifest.tsv",
        "full-binary-packages.tsv",
        "full-debs.sha256",
    ):
        require_same_file(FULL / name, ORIGINAL / name, f"authoritative candidate {name}")

    repro_manifest = REPRO / "reproducibility-manifest.tsv"
    if not repro_manifest.is_file():
        fail("reproducibility manifest missing")
    lines = repro_manifest.read_text(encoding="utf-8").splitlines()
    if len(lines) != 102:
        fail(f"reproducibility manifest has {len(lines) - 1} data rows, expected 101")
    if any(not line.endswith("\tPASS") for line in lines[1:]):
        fail("reproducibility manifest contains a non-PASS source")

    OUT.mkdir(parents=True, exist_ok=True)
    status = OUT / "technical-acceptance-status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_TECHNICAL_ACCEPTANCE=PASS",
                "AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_SOURCES=101",
                f"AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_BINARIES={full['AURORA_KSQ_1_FULL_BUILD_BINARIES']}",
                "AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_KWALLET=PASS",
                "AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_REPRODUCIBILITY=PASS",
                "AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_KSQ0_REGRESSION=PASS",
                "AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_PROVENANCE=PASS",
                "AURORA_KSQ_1_CERTIFIED=no",
                "AURORA_KSQ_2_UNBLOCKED=no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_TECHNICAL_ACCEPTANCE_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
