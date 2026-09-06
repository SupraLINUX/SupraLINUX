#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_REPRO_RANGE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class RangedRoot:
    first: int
    last: int
    root: Path


def parse_ranged_root(spec: str, label: str) -> RangedRoot:
    range_part, sep, path_part = spec.partition("=")
    match = re.fullmatch(r"([1-9][0-9]*)-([1-9][0-9]*)", range_part)
    if not sep or match is None or not path_part:
        fail(f"invalid {label} range declaration {spec!r}; expected FIRST-LAST=PATH")
    first, last = map(int, match.groups())
    if first < 1 or last > 101 or first > last:
        fail(f"invalid {label} range {first}-{last}")
    root = Path(path_part).resolve()
    if not root.is_dir():
        fail(f"{label} root does not exist: {root}")
    return RangedRoot(first, last, root)


def authoritative_root(ranges: list[RangedRoot], order: int, label: str) -> Path:
    matches = [entry.root for entry in ranges if entry.first <= order <= entry.last]
    if len(matches) != 1:
        fail(f"{label}: order {order} authoritative root cardinality {len(matches)}")
    return matches[0]


def rows_from(roots: list[Path], name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[Path] = set()
    for root in roots:
        for path in root.rglob(name):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            with path.open(newline="", encoding="utf-8") as handle:
                rows.extend(csv.DictReader(handle, delimiter="\t"))
    return rows


def rows_from_ranged_roots(
    ranges: list[RangedRoot], name: str, orders: set[int], label: str
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[Path] = set()
    for entry in ranges:
        scoped_orders = {order for order in orders if entry.first <= order <= entry.last}
        if not scoped_orders:
            continue
        for path in entry.root.rglob(name):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    try:
                        order = int(row["order"])
                    except (KeyError, TypeError, ValueError):
                        fail(f"{label}: malformed order in {path}")
                    if order in scoped_orders:
                        rows.append(row)
    return rows


def source_dir(roots: list[Path], order: int, source: str) -> Path:
    name = f"{order}-{source}"
    found: dict[Path, Path] = {}
    for root in roots:
        for path in root.rglob(name):
            if path.is_dir() and (path / "prepared-source.env").is_file():
                found[path.resolve()] = path
    if len(found) != 1:
        fail(f"{name}: source evidence cardinality {len(found)}")
    return next(iter(found.values()))


def ranged_source_dir(ranges: list[RangedRoot], order: int, source: str, label: str) -> Path:
    root = authoritative_root(ranges, order, label)
    name = f"{order}-{source}"
    found: dict[Path, Path] = {}
    for path in root.rglob(name):
        if path.is_dir() and (path / "prepared-source.env").is_file():
            found[path.resolve()] = path
    if len(found) != 1:
        fail(f"{name}: source evidence cardinality {len(found)} inside authoritative root {root}")
    return next(iter(found.values()))


def find_deb(roots: list[Path], filename: str) -> Path:
    found: dict[Path, Path] = {}
    for root in roots:
        for path in root.rglob(filename):
            if path.is_file() and path.suffix == ".deb":
                found[path.resolve()] = path
    if len(found) != 1:
        fail(f"{filename}: DEB cardinality {len(found)}")
    return next(iter(found.values()))


def ranged_find_deb(
    ranges: list[RangedRoot], order: int, filename: str, label: str
) -> Path:
    root = authoritative_root(ranges, order, label)
    found: dict[Path, Path] = {}
    for path in root.rglob(filename):
        if path.is_file() and path.suffix == ".deb":
            found[path.resolve()] = path
    if len(found) != 1:
        fail(f"{filename}: DEB cardinality {len(found)} inside authoritative root {root}")
    return next(iter(found.values()))


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def manifest_by_order(rows: list[dict[str, str]], orders: set[int], label: str) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        order = int(row["order"])
        if order not in orders:
            continue
        if order in result:
            fail(f"{label}: duplicate manifest order {order}")
        result[order] = row
    if set(result) != orders:
        fail(f"{label}: manifest coverage {sorted(result)} != {sorted(orders)}")
    return result


def candidate_ranges_from_args(args: argparse.Namespace, orders: set[int]) -> list[RangedRoot]:
    if args.candidate_root_range and args.candidate_root:
        fail("do not mix --candidate-root-range with --candidate-root")
    if args.candidate_root_range:
        ranges = [
            parse_ranged_root(spec, "candidate") for spec in args.candidate_root_range
        ]
    else:
        roots = [path.resolve() for path in (args.candidate_root or [])]
        if len(roots) != 1:
            fail("multiple candidate roots require explicit --candidate-root-range FIRST-LAST=PATH")
        if not roots[0].is_dir():
            fail(f"candidate root does not exist: {roots[0]}")
        ranges = [RangedRoot(min(orders), max(orders), roots[0])]
    for order in sorted(orders):
        authoritative_root(ranges, order, "candidate")
    return ranges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=int, required=True)
    parser.add_argument("--last", type=int, required=True)
    parser.add_argument("--candidate-root", type=Path, action="append")
    parser.add_argument(
        "--candidate-root-range",
        action="append",
        metavar="FIRST-LAST=PATH",
        help="bind each candidate checkpoint root to the exact source-order range it authoritatively represents",
    )
    parser.add_argument("--rebuilt-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.first < 1 or args.last > 101 or args.first > args.last:
        fail("invalid order range")
    orders = set(range(args.first, args.last + 1))
    candidate_ranges = candidate_ranges_from_args(args, orders)
    rebuilt_roots = [path.resolve() for path in args.rebuilt_root]
    if not all(path.is_dir() for path in rebuilt_roots):
        fail("one or more rebuilt roots do not exist")

    candidate_manifest = manifest_by_order(
        rows_from_ranged_roots(candidate_ranges, "build-manifest.tsv", orders, "candidate"),
        orders,
        "candidate",
    )
    rebuilt_manifest = manifest_by_order(
        rows_from(rebuilt_roots, "build-manifest.tsv"), orders, "rebuilt"
    )
    manifest_keys = [
        "source_package",
        "packaging_base",
        "supra_version",
        "candidate_family",
        "decision",
        "deb_count",
        "result",
    ]
    for order in sorted(orders):
        for key in manifest_keys:
            left = candidate_manifest[order].get(key)
            right = rebuilt_manifest[order].get(key)
            if left != right:
                fail(f"order {order} manifest {key} differs: {left!r} != {right!r}")
        if candidate_manifest[order].get("result") != "PASS":
            fail(f"order {order} candidate result is not PASS")

    candidate_binaries = rows_from_ranged_roots(
        candidate_ranges, "binary-packages.tsv", orders, "candidate"
    )
    rebuilt_binaries = [
        row for row in rows_from(rebuilt_roots, "binary-packages.tsv") if int(row["order"]) in orders
    ]

    def binary_key(row: dict[str, str]) -> tuple[object, ...]:
        return (
            int(row["order"]),
            row["source_package"],
            row["binary_package"],
            row["filename"],
            row["version"],
            row["architecture"],
        )

    if sorted(map(binary_key, candidate_binaries)) != sorted(map(binary_key, rebuilt_binaries)):
        fail("candidate/rebuilt binary package shape differs")

    env_keys = [
        "AURORA_KSQ_1_SOURCE",
        "AURORA_KSQ_1_PACKAGING_BASE",
        "AURORA_KSQ_1_VERSION",
        "AURORA_KSQ_1_OVERRIDES_APPLIED",
        "AURORA_KSQ_1_PACKAGING_ADAPTATIONS_APPLIED",
        "AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS",
        "AURORA_KSQ_1_COMPAT13_SUBSTVARS_RESTORED",
    ]

    source_rows: list[list[str]] = []
    for order in sorted(orders):
        source = candidate_manifest[order]["source_package"]
        candidate_dir = ranged_source_dir(candidate_ranges, order, source, "candidate")
        rebuilt_dir = source_dir(rebuilt_roots, order, source)
        candidate_env = read_env(candidate_dir / "prepared-source.env")
        rebuilt_env = read_env(rebuilt_dir / "prepared-source.env")
        for key in env_keys:
            if candidate_env.get(key) != rebuilt_env.get(key):
                fail(
                    f"order {order} {key} differs: "
                    f"{candidate_env.get(key)!r} != {rebuilt_env.get(key)!r}"
                )

        for filename in ("debian-control", "debian-changelog"):
            if sha256(candidate_dir / filename) != sha256(rebuilt_dir / filename):
                fail(f"order {order} {filename} differs")

        candidate_dsc = list(candidate_dir.glob("*.dsc"))
        rebuilt_dsc = list(rebuilt_dir.glob("*.dsc"))
        if len(candidate_dsc) != 1 or len(rebuilt_dsc) != 1:
            fail(
                f"order {order} dsc cardinality "
                f"candidate={len(candidate_dsc)} rebuilt={len(rebuilt_dsc)}"
            )
        if candidate_dsc[0].name != rebuilt_dsc[0].name:
            fail(f"order {order} prepared dsc filename differs")
        candidate_dsc_sha = sha256(candidate_dsc[0])
        rebuilt_dsc_sha = sha256(rebuilt_dsc[0])
        if candidate_dsc_sha != rebuilt_dsc_sha:
            fail(f"order {order} prepared dsc differs")

        candidate_delta = {
            path.name: sha256(path) for path in candidate_dir.glob("*~supra*.debian.tar.*")
        }
        rebuilt_delta = {
            path.name: sha256(path) for path in rebuilt_dir.glob("*~supra*.debian.tar.*")
        }
        if not candidate_delta or candidate_delta != rebuilt_delta:
            fail(f"order {order} prepared Debian source delta differs")

        logs = list(rebuilt_dir.glob("*.build"))
        if len(logs) != 1:
            fail(f"order {order} rebuilt .build cardinality {len(logs)}")
        text = logs[0].read_text(errors="replace")
        required_markers = [
            "AURORA_NATIVE_BUILD_NETWORK_WRAPPER=START",
            "AURORA_NATIVE_BUILD_NETNS_DIFFERENT=PASS",
            "AURORA_NATIVE_BUILD_PROC_NETIFS_ONLY_LO=PASS",
            "AURORA_NATIVE_BUILD_IPV4_ROUTE_ISOLATION=PASS",
            "AURORA_NATIVE_BUILD_NETWORK=isolated",
            "Status: successful",
        ]
        for marker in required_markers:
            if marker not in text:
                fail(f"order {order} rebuilt log missing {marker}")
        if re.search(r"^(Get|Hit|Ign|Err):.*https?://", text, re.MULTILINE):
            fail(f"order {order} rebuilt log used remote APT transport")

        source_rows.append(
            [
                str(order),
                source,
                candidate_dsc[0].name,
                candidate_dsc_sha,
                next(iter(candidate_delta.values())),
                candidate_env["AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS"],
            ]
        )

    binary_rows: list[list[str]] = []
    for row in sorted(candidate_binaries, key=binary_key):
        order = int(row["order"])
        candidate_deb = ranged_find_deb(candidate_ranges, order, row["filename"], "candidate")
        rebuilt_deb = find_deb(rebuilt_roots, row["filename"])
        candidate_sha = sha256(candidate_deb)
        rebuilt_sha = sha256(rebuilt_deb)
        if candidate_sha != rebuilt_sha:
            fail(f"order {row['order']} non-reproducible DEB {row['filename']}")
        binary_rows.append(
            [
                row["order"],
                row["source_package"],
                row["binary_package"],
                row["filename"],
                candidate_sha,
            ]
        )

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "source-proof.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            ["order", "source_package", "dsc", "dsc_sha256", "debian_delta_sha256", "adaptation_ids"]
        )
        writer.writerows(source_rows)
    with (args.output / "binary-proof.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["order", "source_package", "binary_package", "filename", "sha256"])
        writer.writerows(binary_rows)

    status = args.output / "status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_REPRO_RANGE_STATUS=PASS",
                f"AURORA_KSQ_1_REPRO_RANGE_FIRST_ORDER={args.first}",
                f"AURORA_KSQ_1_REPRO_RANGE_LAST_ORDER={args.last}",
                f"AURORA_KSQ_1_REPRO_RANGE_SOURCES={len(orders)}",
                f"AURORA_KSQ_1_REPRO_RANGE_BINARIES={len(binary_rows)}",
                "AURORA_KSQ_1_REPRO_CANDIDATE_RANGE_BINDING=PASS",
                "AURORA_KSQ_1_REPRO_RANGE_SOURCE_IDENTITY=PASS",
                "AURORA_KSQ_1_REPRO_RANGE_BINARY_IDENTITY=PASS",
                "AURORA_KSQ_1_FULL_CERTIFIED=no",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_REPRO_RANGE_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
