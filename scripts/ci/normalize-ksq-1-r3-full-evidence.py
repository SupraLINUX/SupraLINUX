#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path
from typing import NoReturn

RAW_RANGES = [(1, 20), (21, 40), (41, 43), (44, 60), (61, 65), (66, 80), (81, 90), (91, 101)]
NORMALIZED_RANGES = [
    ((1, 20),),
    ((21, 40),),
    ((41, 43), (44, 60)),
    ((61, 65), (66, 80)),
    ((81, 90), (91, 101)),
]
MANIFEST_HEADER = [
    "order", "source_package", "packaging_base", "supra_version",
    "candidate_family", "decision", "deb_count", "buildinfo_count",
    "changes_count", "result",
]
BINARY_HEADER = [
    "order", "source_package", "binary_package", "filename", "version", "architecture",
]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"AURORA_KSQ_R3_EVIDENCE_NORMALIZE_FAILURE: {message}")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"{path}: malformed env line {line!r}")
        key, value = line.split("=", 1)
        if key in values:
            fail(f"{path}: duplicate env key {key}")
        values[key] = value
    return values


def read_tsv(path: Path, header: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != header:
            fail(f"{path}: unexpected header {reader.fieldnames}")
        return list(reader)


def write_tsv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def range_name(first: int, last: int) -> str:
    return f"range-{first:03d}-{last:03d}"


def validate_raw(root: Path, first: int, last: int) -> dict[str, object]:
    directory = root / range_name(first, last)
    if not directory.is_dir():
        fail(f"missing raw evidence directory {directory}")

    required = [
        directory / "range-status.env",
        directory / "build-manifest.tsv",
        directory / "binary-packages.tsv",
        directory / "new-debs.sha256",
    ]
    for path in required:
        if not path.is_file():
            fail(f"{directory}: missing {path.name}")

    status = read_env(directory / "range-status.env")
    expected = {
        "AURORA_KSQ_1_RANGE_STATUS": "PASS",
        "AURORA_KSQ_1_RANGE_FIRST_ORDER": str(first),
        "AURORA_KSQ_1_RANGE_LAST_ORDER": str(last),
        "AURORA_KSQ_1_RANGE_SOURCES": str(last - first + 1),
    }
    for key, value in expected.items():
        if status.get(key) != value:
            fail(f"{directory}: {key}={status.get(key)!r}, expected {value}")

    manifests = read_tsv(directory / "build-manifest.tsv", MANIFEST_HEADER)
    orders = [int(row["order"]) for row in manifests]
    if orders != list(range(first, last + 1)):
        fail(f"{directory}: manifest orders {orders} do not match range")
    if any(row["result"] != "PASS" for row in manifests):
        fail(f"{directory}: non-PASS manifest row")

    binaries = read_tsv(directory / "binary-packages.tsv", BINARY_HEADER)
    if set(int(row["order"]) for row in binaries) != set(range(first, last + 1)):
        fail(f"{directory}: binary index does not cover every order")

    source_dirs: list[Path] = []
    for row in manifests:
        source_dir = directory / f"{int(row['order'])}-{row['source_package']}"
        if not source_dir.is_dir() or not (source_dir / "prepared-source.env").is_file():
            fail(f"{directory}: missing source evidence {source_dir.name}")
        source_dirs.append(source_dir)

    hashes: list[tuple[str, str]] = []
    names: set[str] = set()
    for line in (directory / "new-debs.sha256").read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f"{directory}: malformed checksum {line!r}")
        digest, name = parts
        name = name.lstrip("*")
        if "/" in name or name in names:
            fail(f"{directory}: invalid/duplicate checksum target {name}")
        names.add(name)
        hashes.append((digest, name))

    new_debs = int(status.get("AURORA_KSQ_1_RANGE_NEW_DEBS", str(len(hashes))))
    if new_debs != len(hashes):
        fail(f"{directory}: NEW_DEBS={new_debs}, checksum rows={len(hashes)}")
    accumulated = int(status.get("AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS", "-1"))
    if accumulated < new_debs:
        fail(f"{directory}: invalid accumulated DEB count {accumulated}")

    return {
        "dir": directory,
        "status": status,
        "manifests": manifests,
        "binaries": binaries,
        "source_dirs": source_dirs,
        "hashes": hashes,
        "new": new_debs,
        "accumulated": accumulated,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    raw_root = args.raw_root.resolve()
    output_root = args.output_root.resolve()
    raw_data = {(first, last): validate_raw(raw_root, first, last) for first, last in RAW_RANGES}

    shutil.rmtree(output_root, ignore_errors=True)
    output_root.mkdir(parents=True)

    all_sources: set[str] = set()
    all_packages: set[str] = set()
    all_files: set[str] = set()
    expected_first = 1
    normalized_rows: list[tuple[int, int, int, int, int, int, int]] = []

    for parts in NORMALIZED_RANGES:
        first = parts[0][0]
        last = parts[-1][1]
        if first != expected_first:
            fail(f"normalized chain discontinuity at {first}")

        destination = output_root / f"aurora-ksq-1-evidence-{first:03d}-{last:03d}"
        destination.mkdir()
        manifests: list[dict[str, str]] = []
        binaries: list[dict[str, str]] = []
        hashes: list[tuple[str, str]] = []
        new_debs = 0
        accumulated = -1

        for part in parts:
            info = raw_data[part]
            manifests.extend(info["manifests"])
            binaries.extend(info["binaries"])
            hashes.extend(info["hashes"])
            new_debs += int(info["new"])
            accumulated = int(info["accumulated"])
            for source_dir in info["source_dirs"]:
                target = destination / source_dir.name
                if target.exists():
                    fail(f"duplicate source evidence {source_dir.name}")
                shutil.copytree(source_dir, target, symlinks=True)

        orders = [int(row["order"]) for row in manifests]
        if orders != list(range(first, last + 1)):
            fail(f"normalized {first}-{last}: source order mismatch")

        for row in manifests:
            source = row["source_package"]
            if source in all_sources:
                fail(f"source duplicated across normalized ranges: {source}")
            all_sources.add(source)

        for row in binaries:
            package = row["binary_package"]
            filename = row["filename"]
            if package in all_packages:
                fail(f"binary package duplicated across normalized ranges: {package}")
            if filename in all_files:
                fail(f"binary filename duplicated across normalized ranges: {filename}")
            all_packages.add(package)
            all_files.add(filename)

        hash_names = [name for _, name in hashes]
        if len(hash_names) != len(set(hash_names)):
            fail(f"normalized {first}-{last}: duplicate checksum filename")

        write_tsv(destination / "build-manifest.tsv", MANIFEST_HEADER, manifests)
        write_tsv(destination / "binary-packages.tsv", BINARY_HEADER, binaries)
        with (destination / "new-debs.sha256").open("w", encoding="utf-8") as handle:
            for digest, name in hashes:
                handle.write(f"{digest}  {name}\n")

        (destination / "range-status.env").write_text(
            "\n".join(
                [
                    "AURORA_KSQ_1_RANGE_STATUS=PASS",
                    f"AURORA_KSQ_1_RANGE_FIRST_ORDER={first}",
                    f"AURORA_KSQ_1_RANGE_LAST_ORDER={last}",
                    f"AURORA_KSQ_1_RANGE_SOURCES={last - first + 1}",
                    f"AURORA_KSQ_1_RANGE_NEW_DEBS={new_debs}",
                    f"AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS={accumulated}",
                    "AURORA_KSQ_1_RANGE_FULL_CERTIFIED=no",
                    "AURORA_KSQ_R3_NORMALIZED_VALIDATION_VIEW=yes",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        normalized_rows.append(
            (first, last, len(manifests), len(binaries), len(hashes), new_debs, accumulated)
        )
        expected_first = last + 1

    if expected_first != 102 or len(all_sources) != 101:
        fail(f"normalized evidence does not cover exact 101 sources ({len(all_sources)})")

    with (output_root / "r3-normalization.tsv").open("w", encoding="utf-8") as handle:
        handle.write(
            "first_order\tlast_order\tsources\tbinary_rows\tchecksum_rows\tnew_debs\taccumulated_debs\n"
        )
        for row in normalized_rows:
            handle.write("\t".join(map(str, row)) + "\n")

    (output_root / "r3-normalization-status.env").write_text(
        "AURORA_KSQ_R3_EVIDENCE_NORMALIZATION=PASS\n"
        "AURORA_KSQ_R3_RAW_CHECKPOINTS=8\n"
        "AURORA_KSQ_R3_NORMALIZED_VALIDATION_CHECKPOINTS=5\n"
        "AURORA_KSQ_R3_SOURCES=101\n",
        encoding="utf-8",
    )
    print("AURORA_KSQ_R3_EVIDENCE_NORMALIZATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
