#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_REFERENCE_RANGE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def manifest_rows(roots: list[Path], orders: set[int], label: str) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for root in roots:
        for path in sorted(root.rglob("build-manifest.tsv")):
            for row in read_tsv(path):
                try:
                    order = int(row["order"])
                except (KeyError, ValueError):
                    fail(f"{label}: malformed order in {path}")
                if order not in orders:
                    continue
                if order in result:
                    fail(f"{label}: duplicate manifest order {order}")
                result[order] = row
    if set(result) != orders:
        fail(f"{label}: manifest coverage {sorted(result)} != {sorted(orders)}")
    return result


def binary_rows(roots: list[Path], orders: set[int], label: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[int, str]] = set()
    for root in roots:
        for path in sorted(root.rglob("binary-packages.tsv")):
            for row in read_tsv(path):
                try:
                    order = int(row["order"])
                except (KeyError, ValueError):
                    fail(f"{label}: malformed binary order in {path}")
                if order not in orders:
                    continue
                key = (order, row.get("binary_package", ""))
                if key in seen:
                    fail(f"{label}: duplicate binary row {key}")
                seen.add(key)
                result.append(row)
    covered = {int(row["order"]) for row in result}
    if covered != orders:
        fail(f"{label}: binary source coverage {sorted(covered)} != {sorted(orders)}")
    return result


def source_dirs(roots: list[Path], orders: set[int], label: str) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for root in roots:
        for status in sorted(root.rglob("build-status.env")):
            env = read_env(status)
            if env.get("AURORA_KSQ_1_BUILD_RESULT") != "PASS":
                continue
            try:
                order = int(env["AURORA_KSQ_1_BUILD_ORDER"])
            except (KeyError, ValueError):
                fail(f"{label}: invalid build status {status}")
            if order not in orders:
                continue
            if order in result:
                fail(f"{label}: duplicate source evidence order {order}")
            result[order] = status.parent
    if set(result) != orders:
        fail(f"{label}: source evidence coverage {sorted(result)} != {sorted(orders)}")
    return result


def find_deb(roots: list[Path], filename: str, label: str) -> Path:
    found: dict[Path, Path] = {}
    for root in roots:
        direct = root / filename
        if direct.is_file():
            found[direct.resolve()] = direct
    if len(found) != 1:
        fail(f"{label}: {filename} DEB cardinality {len(found)}")
    return next(iter(found.values()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", required=True, type=int)
    parser.add_argument("--last", required=True, type=int)
    parser.add_argument("--candidate-evidence", required=True, type=Path)
    parser.add_argument("--candidate-debs", required=True, type=Path)
    parser.add_argument("--reference-evidence", action="append", required=True, type=Path)
    parser.add_argument("--reference-debs", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.first < 1 or args.last > 101 or args.first > args.last:
        fail("invalid range")
    orders = set(range(args.first, args.last + 1))
    candidate_evidence = args.candidate_evidence.resolve()
    candidate_debs = args.candidate_debs.resolve()
    reference_evidence = [path.resolve() for path in args.reference_evidence]
    reference_debs = [path.resolve() for path in args.reference_debs]
    for path in [candidate_evidence, candidate_debs, *reference_evidence, *reference_debs]:
        if not path.is_dir():
            fail(f"input directory missing: {path}")

    cm = manifest_rows([candidate_evidence], orders, "candidate")
    rm = manifest_rows(reference_evidence, orders, "reference")
    cs = source_dirs([candidate_evidence], orders, "candidate")
    rs = source_dirs(reference_evidence, orders, "reference")

    manifest_keys = [
        "source_package",
        "packaging_base",
        "supra_version",
        "candidate_family",
        "decision",
        "deb_count",
        "result",
    ]
    source_rows: list[list[str]] = []
    for order in sorted(orders):
        for key in manifest_keys:
            if cm[order].get(key) != rm[order].get(key):
                fail(f"order {order}: manifest {key} differs")
        if cm[order].get("result") != "PASS":
            fail(f"order {order}: candidate/reference result is not PASS")

        source = cm[order]["source_package"]
        version = cm[order]["supra_version"]
        cdir = cs[order]
        rdir = rs[order]
        for label, directory in (("candidate", cdir), ("reference", rdir)):
            env = read_env(directory / "build-status.env")
            expected = {
                "AURORA_KSQ_1_BUILD_RESULT": "PASS",
                "AURORA_KSQ_1_BUILD_ORDER": str(order),
                "AURORA_KSQ_1_BUILD_SOURCE": source,
                "AURORA_KSQ_1_BUILD_VERSION": version,
            }
            for key, wanted in expected.items():
                if env.get(key) != wanted:
                    fail(f"order {order}: {label} {key}={env.get(key)!r} != {wanted!r}")

        for name in ("debian-control", "debian-changelog"):
            if sha256(cdir / name) != sha256(rdir / name):
                fail(f"order {order}: {name} differs")

        cdsc = sorted(cdir.glob("*.dsc"))
        rdsc = sorted(rdir.glob("*.dsc"))
        if len(cdsc) != 1 or len(rdsc) != 1:
            fail(f"order {order}: prepared dsc cardinality differs")
        if cdsc[0].name != rdsc[0].name or sha256(cdsc[0]) != sha256(rdsc[0]):
            fail(f"order {order}: prepared dsc differs")

        cdel = {path.name: sha256(path) for path in cdir.glob("*~supra*.debian.tar.*")}
        rdel = {path.name: sha256(path) for path in rdir.glob("*~supra*.debian.tar.*")}
        if not cdel or cdel != rdel:
            fail(f"order {order}: prepared Debian source delta differs")
        if len(cdel) != 1:
            fail(f"order {order}: expected one prepared Debian source delta, got {len(cdel)}")

        for label, directory in (("candidate", cdir), ("reference", rdir)):
            logs = sorted(directory.glob("*.build"))
            if len(logs) != 1:
                fail(f"order {order}: {label} build log cardinality {len(logs)}")
            if "Status: successful" not in logs[0].read_text(errors="replace"):
                fail(f"order {order}: {label} build log is not successful")

        prepared = read_env(cdir / "prepared-source.env")
        adaptation_ids = prepared.get("AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS", "")
        if not adaptation_ids:
            fail(f"order {order}: candidate adaptation id field missing")
        source_rows.append(
            [
                str(order),
                source,
                cdsc[0].name,
                sha256(cdsc[0]),
                next(iter(cdel.values())),
                adaptation_ids,
            ]
        )

    cb = binary_rows([candidate_evidence], orders, "candidate")
    rb = binary_rows(reference_evidence, orders, "reference")

    def key(row: dict[str, str]) -> tuple[object, ...]:
        return (
            int(row["order"]),
            row["source_package"],
            row["binary_package"],
            row["filename"],
            row["version"],
            row["architecture"],
        )

    if sorted(map(key, cb)) != sorted(map(key, rb)):
        fail("candidate/reference binary package shape differs")

    binary_proof: list[list[str]] = []
    for row in sorted(cb, key=key):
        current = find_deb([candidate_debs], row["filename"], "candidate")
        reference = find_deb(reference_debs, row["filename"], "reference")
        digest = sha256(current)
        if digest != sha256(reference):
            fail(f"order {row['order']}: non-reproducible DEB {row['filename']}")
        binary_proof.append(
            [
                row["order"],
                row["source_package"],
                row["binary_package"],
                row["filename"],
                digest,
            ]
        )

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "source-proof.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["order", "source_package", "dsc", "dsc_sha256", "debian_delta_sha256", "adaptation_ids"])
        writer.writerows(source_rows)
    with (args.output / "binary-proof.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["order", "source_package", "binary_package", "filename", "sha256"])
        writer.writerows(binary_proof)

    (args.output / "status.env").write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_REPRO_RANGE_STATUS=PASS",
                f"AURORA_KSQ_1_REPRO_RANGE_FIRST_ORDER={args.first}",
                f"AURORA_KSQ_1_REPRO_RANGE_LAST_ORDER={args.last}",
                f"AURORA_KSQ_1_REPRO_RANGE_SOURCES={len(orders)}",
                f"AURORA_KSQ_1_REPRO_RANGE_BINARIES={len(binary_proof)}",
                "AURORA_KSQ_1_REPRO_CANDIDATE_RANGE_BINDING=PASS",
                "AURORA_KSQ_1_REPRO_RANGE_SOURCE_IDENTITY=PASS",
                "AURORA_KSQ_1_REPRO_RANGE_BINARY_IDENTITY=PASS",
                "AURORA_KSQ_1_REPRO_REFERENCE_KIND=historical-independent-build",
                "AURORA_KSQ_1_FULL_CERTIFIED=no",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print((args.output / "status.env").read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_REFERENCE_RANGE_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
