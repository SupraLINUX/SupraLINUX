#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

INPUT_RANGES = [(1, 20), (21, 40), (41, 43), (44, 60), (61, 65), (66, 80), (81, 90), (91, 101)]
OUTPUT_RANGES = [
    ((1, 20), [(1, 20)]),
    ((21, 40), [(21, 40)]),
    ((41, 60), [(41, 43), (44, 60)]),
    ((61, 80), [(61, 65), (66, 80)]),
    ((81, 101), [(81, 90), (91, 101)]),
]
MANIFEST_HEADER = [
    "order",
    "source_package",
    "packaging_base",
    "supra_version",
    "candidate_family",
    "decision",
    "deb_count",
    "buildinfo_count",
    "changes_count",
    "result",
]
BINARY_HEADER = ["order", "source_package", "binary_package", "filename", "version", "architecture"]


def fail(message: str) -> None:
    raise SystemExit(f"AURORA_KSQ_REPRO_INPUT_FAILURE: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"{path}: malformed env line {line!r}")
        key, value = line.split("=", 1)
        values[key] = value
    return values


def read_tsv(path: Path, header: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != header:
            fail(f"{path}: unexpected header {reader.fieldnames}")
        return list(reader)


def locate_chunk(root: Path, first: int, last: int) -> Path:
    name = f"chunk-{first:03d}-{last:03d}"
    found = []
    for path in [root / "ksq-1/full" / name, root / "build/ksq-1/full" / name]:
        if path.is_dir():
            found.append(path)
    if len(found) != 1:
        fail(f"{root}: expected one {name}, got {len(found)}")
    return found[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk", action="append", default=[], metavar="FIRST-LAST=ROOT")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    roots: dict[tuple[int, int], Path] = {}
    for spec in args.chunk:
        try:
            span, raw = spec.split("=", 1)
            first, last = map(int, span.split("-", 1))
        except Exception:
            fail(f"invalid --chunk {spec!r}")
        key = (first, last)
        if key in roots:
            fail(f"duplicate input range {key}")
        roots[key] = Path(raw).resolve()
    if set(roots) != set(INPUT_RANGES):
        fail(f"input ranges differ: {sorted(set(roots) ^ set(INPUT_RANGES))}")

    inputs: dict[tuple[int, int], dict[str, object]] = {}
    all_orders: set[int] = set()
    all_deb_names: set[str] = set()
    all_pkg_names: set[str] = set()
    total_debs = 0

    for first, last in INPUT_RANGES:
        chunk = locate_chunk(roots[(first, last)], first, last)
        evidence = chunk / "evidence"
        new_debs = chunk / "new-debs"
        status = read_env(evidence / "range-status.env")
        expected = {
            "AURORA_KSQ_1_RANGE_STATUS": "PASS",
            "AURORA_KSQ_1_RANGE_FIRST_ORDER": str(first),
            "AURORA_KSQ_1_RANGE_LAST_ORDER": str(last),
            "AURORA_KSQ_1_RANGE_SOURCES": str(last - first + 1),
            "AURORA_KSQ_1_RANGE_RESOLVE_ALTERNATIVES": "yes",
            "AURORA_KSQ_1_RANGE_FULL_CERTIFIED": "no",
        }
        for key, value in expected.items():
            if status.get(key) != value:
                fail(f"{evidence / 'range-status.env'}: {key}={status.get(key)!r}, expected {value!r}")

        manifest = read_tsv(evidence / "build-manifest.tsv", MANIFEST_HEADER)
        binaries = read_tsv(evidence / "binary-packages.tsv", BINARY_HEADER)
        if len(manifest) != last - first + 1:
            fail(f"{chunk}: manifest source count {len(manifest)}")
        orders = [int(row["order"]) for row in manifest]
        if orders != list(range(first, last + 1)):
            fail(f"{chunk}: manifest order drift")
        if any(row["result"] != "PASS" for row in manifest):
            fail(f"{chunk}: non-PASS build row")

        recorded = {row["filename"] for row in binaries}
        actual = {path.name for path in new_debs.glob("*.deb")}
        if recorded != actual:
            fail(f"{chunk}: binary index/new-deb set mismatch")
        if int(status["AURORA_KSQ_1_RANGE_NEW_DEBS"]) != len(actual):
            fail(f"{chunk}: new DEB count drift")

        hashes: dict[str, str] = {}
        for line in (evidence / "new-debs.sha256").read_text(encoding="utf-8").splitlines():
            digest, name = line.split(None, 1)
            name = name.lstrip("*")
            if "/" in name:
                fail(f"{chunk}: non-relocatable hash target {name}")
            hashes[name] = digest
        if set(hashes) != actual:
            fail(f"{chunk}: new-debs.sha256 coverage mismatch")
        for name, digest in hashes.items():
            if sha256(new_debs / name) != digest:
                fail(f"{chunk}: hash mismatch {name}")

        source_dirs: list[Path] = []
        for order in range(first, last + 1):
            matches = sorted(path for path in evidence.iterdir() if path.is_dir() and path.name.startswith(f"{order}-"))
            if len(matches) != 1:
                fail(f"{chunk}: expected one source evidence dir for order {order}")
            build_status = read_env(matches[0] / "build-status.env")
            if build_status.get("AURORA_KSQ_1_BUILD_RESULT") != "PASS":
                fail(f"{matches[0]}: build result not PASS")
            if int(build_status.get("AURORA_KSQ_1_BUILD_ORDER", "-1")) != order:
                fail(f"{matches[0]}: build order mismatch")
            if not (matches[0] / "prepared-source.env").is_file():
                fail(f"{matches[0]}: prepared-source.env missing")
            source_dirs.append(matches[0])

        for row in binaries:
            filename = row["filename"]
            package = row["binary_package"]
            if filename in all_deb_names:
                fail(f"duplicate DEB filename {filename}")
            if package in all_pkg_names:
                fail(f"duplicate binary package {package}")
            all_deb_names.add(filename)
            all_pkg_names.add(package)

        all_orders.update(orders)
        total_debs += len(actual)
        inputs[(first, last)] = {
            "chunk": chunk,
            "evidence": evidence,
            "new_debs": new_debs,
            "manifest": manifest,
            "binaries": binaries,
            "source_dirs": source_dirs,
        }

    if all_orders != set(range(1, 102)):
        fail("input source coverage is not exactly 1..101")
    if total_debs != 424:
        fail(f"input DEB count {total_debs} != 424")

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    (output / "chunks").mkdir(parents=True)
    merged_debs = output / "debs"
    merged_debs.mkdir()
    accumulated = 0
    provenance: list[list[str]] = []

    for (out_first, out_last), parts in OUTPUT_RANGES:
        destination = output / "chunks" / f"chunk-{out_first:03d}-{out_last:03d}"
        destination_evidence = destination / "evidence"
        destination_debs = destination / "new-debs"
        destination_evidence.mkdir(parents=True)
        destination_debs.mkdir()
        manifests: list[dict[str, str]] = []
        binaries: list[dict[str, str]] = []

        for part in parts:
            source = inputs[part]
            source_chunk = source["chunk"]
            source_dirs = source["source_dirs"]
            source_debs = source["new_debs"]
            source_manifest = source["manifest"]
            source_binaries = source["binaries"]
            assert isinstance(source_chunk, Path)
            assert isinstance(source_dirs, list)
            assert isinstance(source_debs, Path)
            assert isinstance(source_manifest, list)
            assert isinstance(source_binaries, list)

            provenance.append(
                [
                    f"{out_first:03d}-{out_last:03d}",
                    f"{part[0]:03d}-{part[1]:03d}",
                    str(source_chunk),
                ]
            )
            manifests.extend(source_manifest)
            binaries.extend(source_binaries)

            for source_dir in source_dirs:
                target = destination_evidence / source_dir.name
                if target.exists():
                    fail(f"output duplicate source evidence {target.name}")
                shutil.copytree(source_dir, target, symlinks=True)

            for deb in sorted(source_debs.glob("*.deb")):
                target = destination_debs / deb.name
                if target.exists():
                    fail(f"output duplicate DEB {deb.name}")
                shutil.copy2(deb, target)
                merged_target = merged_debs / deb.name
                if merged_target.exists():
                    fail(f"merged output duplicate DEB {deb.name}")
                shutil.copy2(deb, merged_target)

        manifests.sort(key=lambda row: int(row["order"]))
        binaries.sort(key=lambda row: (int(row["order"]), row["binary_package"]))
        with (destination_evidence / "build-manifest.tsv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_HEADER, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(manifests)
        with (destination_evidence / "binary-packages.tsv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=BINARY_HEADER, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(binaries)

        hashes = [f"{sha256(deb)}  {deb.name}\n" for deb in sorted(destination_debs.glob("*.deb"))]
        (destination_evidence / "new-debs.sha256").write_text("".join(hashes), encoding="utf-8")
        accumulated += len(hashes)
        (destination_evidence / "range-status.env").write_text(
            "\n".join(
                [
                    "AURORA_KSQ_1_RANGE_STATUS=PASS",
                    f"AURORA_KSQ_1_RANGE_FIRST_ORDER={out_first}",
                    f"AURORA_KSQ_1_RANGE_LAST_ORDER={out_last}",
                    f"AURORA_KSQ_1_RANGE_SOURCES={out_last - out_first + 1}",
                    f"AURORA_KSQ_1_RANGE_NEW_DEBS={len(hashes)}",
                    f"AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS={accumulated}",
                    "AURORA_KSQ_1_RANGE_RESOLVE_ALTERNATIVES=yes",
                    "AURORA_KSQ_1_RANGE_FULL_CERTIFIED=no",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if len(list(merged_debs.glob("*.deb"))) != 424:
        fail("normalized merged DEB count != 424")
    if len(list((output / "chunks").rglob("prepared-source.env"))) != 101:
        fail("normalized prepared-source count != 101")
    if len(list((output / "chunks").rglob("build-status.env"))) != 101:
        fail("normalized build-status count != 101")

    with (output / "checkpoint-provenance.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["canonical_range", "input_range", "input_chunk"])
        writer.writerows(provenance)

    (output / "checkpoint-status.env").write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_REPRO_INPUT_STATUS=PASS",
                "AURORA_KSQ_1_REPRO_INPUT_SOURCES=101",
                "AURORA_KSQ_1_REPRO_INPUT_DEBS=424",
                "AURORA_KSQ_1_REPRO_INPUT_INPUT_RANGES=8",
                "AURORA_KSQ_1_REPRO_INPUT_CANONICAL_RANGES=5",
                "AURORA_KSQ_1_REPRO_INPUT_FULL_CERTIFIED=no",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "evidence.sha256"):
        lines.append(f"{sha256(path)}  {path.relative_to(output).as_posix()}\n")
    (output / "evidence.sha256").write_text("".join(lines), encoding="utf-8")

    print((output / "checkpoint-status.env").read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_REPRO_INPUT_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
