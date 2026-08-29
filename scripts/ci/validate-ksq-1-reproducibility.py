#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

DEDICATED_ORDERS = {29, 68, 81, 99, 100, 101}
EXPECTED_ORDERS = set(range(1, 102))


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_REPRO_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path: Path, expected: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != expected:
            fail(f"{path}: unexpected header {reader.fieldnames}")
        return list(reader)


def read_binary_index(root: Path) -> dict[int, list[dict[str, str]]]:
    header = ["order", "source_package", "binary_package", "filename", "version", "architecture"]
    paths = sorted(root.rglob("binary-packages.tsv"))
    if not paths:
        fail(f"no binary package indexes under {root}")

    by_order: dict[int, list[dict[str, str]]] = {}
    filenames: set[str] = set()
    packages: set[str] = set()
    for path in paths:
        for row in read_tsv(path, header):
            order = int(row["order"])
            filename = row["filename"]
            package = row["binary_package"]
            if filename in filenames:
                fail(f"{root}: duplicate binary filename {filename}")
            if package in packages:
                fail(f"{root}: duplicate binary package {package}")
            filenames.add(filename)
            packages.add(package)
            by_order.setdefault(order, []).append(row)

    for rows in by_order.values():
        rows.sort(key=lambda row: row["binary_package"])
    return by_order


def source_evidence_dirs(root: Path) -> dict[int, Path]:
    dirs: dict[int, Path] = {}
    for status in sorted(root.rglob("build-status.env")):
        values: dict[str, str] = {}
        for line in status.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        if values.get("AURORA_KSQ_1_BUILD_RESULT") != "PASS":
            continue
        try:
            order = int(values["AURORA_KSQ_1_BUILD_ORDER"])
        except (KeyError, ValueError):
            fail(f"{status}: missing/invalid build order")
        if order in dirs:
            fail(f"{root}: duplicate source evidence for order {order}")
        dirs[order] = status.parent
    return dirs


def prepared_identity(directory: Path) -> dict[str, str]:
    required = ["debian-control", "debian-changelog"]
    result: dict[str, str] = {}
    for name in required:
        path = directory / name
        if not path.is_file():
            fail(f"{directory}: missing {name}")
        result[name] = sha256(path)

    dscs = sorted(directory.glob("*.dsc"))
    if len(dscs) != 1:
        fail(f"{directory}: expected one prepared dsc, got {len(dscs)}")
    result[dscs[0].name] = sha256(dscs[0])

    deltas = sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and "~supra26.04.1" in path.name
        and not path.name.endswith(".dsc")
        and not path.name.endswith(".buildinfo")
        and not path.name.endswith(".changes")
        and not path.name.endswith(".build")
    )
    if not deltas:
        fail(f"{directory}: prepared source delta was not retained")
    for path in deltas:
        result[path.name] = sha256(path)
    return result


def normalized_rows(rows: list[dict[str, str]]) -> list[tuple[str, str, str, str, str]]:
    return [
        (
            row["source_package"],
            row["binary_package"],
            row["filename"],
            row["version"],
            row["architecture"],
        )
        for row in rows
    ]


def read_dedicated_proofs(paths: list[Path]) -> dict[int, list[dict[str, str]]]:
    header = ["order", "source_package", "binary_package", "filename", "version", "architecture", "sha256"]
    proofs: dict[int, list[dict[str, str]]] = {}
    seen_files: set[str] = set()
    for path in paths:
        for row in read_tsv(path, header):
            order = int(row["order"])
            if order not in DEDICATED_ORDERS:
                fail(f"{path}: dedicated proof unexpectedly covers order {order}")
            filename = row["filename"]
            if filename in seen_files:
                fail(f"dedicated proof duplicates {filename}")
            seen_files.add(filename)
            proofs.setdefault(order, []).append(row)
    for rows in proofs.values():
        rows.sort(key=lambda row: row["binary_package"])
    return proofs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-debs", required=True, type=Path)
    parser.add_argument("--reference-evidence", required=True, type=Path)
    parser.add_argument("--candidate-debs", required=True, type=Path)
    parser.add_argument("--candidate-evidence", required=True, type=Path)
    parser.add_argument("--dedicated-proof", action="append", default=[], type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    reference_debs = args.reference_debs.resolve()
    candidate_debs = args.candidate_debs.resolve()
    reference_index = read_binary_index(args.reference_evidence.resolve())
    candidate_index = read_binary_index(args.candidate_evidence.resolve())
    reference_sources = source_evidence_dirs(args.reference_evidence.resolve())
    candidate_sources = source_evidence_dirs(args.candidate_evidence.resolve())
    dedicated = read_dedicated_proofs(args.dedicated_proof)

    if set(candidate_index) != EXPECTED_ORDERS:
        fail(f"candidate binary index orders are not exactly 1..101: {sorted(set(candidate_index) ^ EXPECTED_ORDERS)}")
    if set(candidate_sources) != EXPECTED_ORDERS:
        fail(f"candidate source evidence orders are not exactly 1..101: {sorted(set(candidate_sources) ^ EXPECTED_ORDERS)}")
    if set(dedicated) != DEDICATED_ORDERS:
        fail(f"dedicated proof orders {sorted(dedicated)} != required {sorted(DEDICATED_ORDERS)}")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "reproducibility-manifest.tsv"
    rows_out: list[list[str]] = []

    for order in range(1, 102):
        candidate_rows = candidate_index[order]
        source = candidate_rows[0]["source_package"]
        if any(row["source_package"] != source for row in candidate_rows):
            fail(f"candidate order {order}: multiple source names")

        if order in DEDICATED_ORDERS:
            proof_rows = dedicated[order]
            proof_shape = [
                (
                    row["source_package"],
                    row["binary_package"],
                    row["filename"],
                    row["version"],
                    row["architecture"],
                )
                for row in proof_rows
            ]
            if normalized_rows(candidate_rows) != proof_shape:
                fail(f"order {order} {source}: candidate binary shape differs from dedicated proof")
            for candidate_row, proof_row in zip(candidate_rows, proof_rows, strict=True):
                deb = candidate_debs / candidate_row["filename"]
                if not deb.is_file():
                    fail(f"candidate DEB missing: {deb}")
                actual = sha256(deb)
                if actual != proof_row["sha256"]:
                    fail(f"order {order} {candidate_row['filename']}: candidate differs from dedicated rebuild proof")
            mode = "dedicated-independent-rebuild"
        else:
            if order not in reference_index or order not in reference_sources:
                fail(f"reference evidence missing unaffected order {order}")
            reference_rows = reference_index[order]
            if normalized_rows(candidate_rows) != normalized_rows(reference_rows):
                fail(f"order {order} {source}: candidate/reference binary shape differs")

            candidate_identity = prepared_identity(candidate_sources[order])
            reference_identity = prepared_identity(reference_sources[order])
            if candidate_identity != reference_identity:
                missing = sorted(set(candidate_identity) ^ set(reference_identity))
                changed = sorted(
                    name
                    for name in set(candidate_identity) & set(reference_identity)
                    if candidate_identity[name] != reference_identity[name]
                )
                fail(f"order {order} {source}: prepared source identity differs; file-set={missing} changed={changed}")

            for candidate_row in candidate_rows:
                filename = candidate_row["filename"]
                candidate_deb = candidate_debs / filename
                reference_deb = reference_debs / filename
                if not candidate_deb.is_file() or not reference_deb.is_file():
                    fail(f"order {order} {source}: missing candidate/reference DEB {filename}")
                if sha256(candidate_deb) != sha256(reference_deb):
                    fail(f"order {order} {filename}: independent rebuilds are not byte-identical")
            mode = "independent-full-dag-rebuild"

        rows_out.append([str(order), source, mode, str(len(candidate_rows)), "PASS"])

    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["order", "source_package", "proof_mode", "binary_count", "result"])
        writer.writerows(rows_out)

    total_binaries = sum(int(row[3]) for row in rows_out)
    status = output / "reproducibility-status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_REPRODUCIBILITY_STATUS=PASS",
                "AURORA_KSQ_1_REPRODUCIBILITY_SOURCES=101",
                f"AURORA_KSQ_1_REPRODUCIBILITY_BINARIES={total_binaries}",
                f"AURORA_KSQ_1_REPRODUCIBILITY_REFERENCE_SOURCES={101 - len(DEDICATED_ORDERS)}",
                f"AURORA_KSQ_1_REPRODUCIBILITY_DEDICATED_SOURCES={len(DEDICATED_ORDERS)}",
                "AURORA_KSQ_1_REPRODUCIBILITY_BYTE_IDENTICAL=yes",
                "AURORA_KSQ_1_FULL_CERTIFIED=no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run([sys.executable, "-m", "py_compile", str(Path(__file__).resolve())], check=True)
    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_REPRO_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
