#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

SNAPSHOT = "20260829T022000Z"
GET_RE = re.compile(
    rf"^Get:\d+\s+https://snapshot\.ubuntu\.com/ubuntu/{SNAPSHOT}\s+"
    r"(?P<suite>resolute(?:-(?:updates|security|backports))?)/(?P<component>main|universe|restricted|multiverse)\s+"
    r"(?P<index_arch>amd64)\s+(?P<package>\S+)\s+(?P<arch>amd64|all)\s+(?P<version>\S+)\s+\["
)


@dataclass(frozen=True, order=True)
class PackageKey:
    package: str
    version: str
    architecture: str


@dataclass(frozen=True)
class PackageRecord:
    filename: str
    size: int
    sha256: str


def fail(msg: str) -> None:
    raise SystemExit(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_FAILURE: {msg}")


def parse_deb822(path: Path) -> dict[PackageKey, PackageRecord]:
    records: dict[PackageKey, PackageRecord] = {}
    current: dict[str, str] = {}

    def flush() -> None:
        nonlocal current
        if not current:
            return
        required = ("Package", "Version", "Architecture", "Filename", "Size", "SHA256")
        if all(k in current for k in required):
            key = PackageKey(current["Package"], current["Version"], current["Architecture"])
            rec = PackageRecord(current["Filename"], int(current["Size"]), current["SHA256"])
            old = records.get(key)
            if old is not None and old != rec:
                fail(f"conflicting signed package records for {key}: {old} != {rec}")
            records[key] = rec
        current = {}

    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if not raw:
            flush()
            continue
        if raw[0].isspace():
            continue
        if ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        current[k] = v.strip()
    flush()
    return records


def parse_r2_objects(path: Path) -> dict[str, int]:
    rows: dict[str, int] = {}
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            fail(f"invalid r2 object row at {path}:{lineno}: {raw!r}")
        rel, size_text = parts
        size = int(size_text)
        old = rows.get(rel)
        if old is not None and old != size:
            fail(f"conflicting r2 size for {rel}")
        rows[rel] = size
    if len(rows) != 1783:
        fail(f"expected 1783 r2 binary objects, got {len(rows)}")
    return rows


def parse_range_status(evidence: Path, first: int, last: int) -> None:
    status = evidence / "range-status.env"
    if not status.is_file():
        fail(f"range status missing: {status}")
    values: dict[str, str] = {}
    for raw in status.read_text().splitlines():
        if "=" in raw:
            k, v = raw.split("=", 1)
            values[k] = v
    expected = {
        "AURORA_KSQ_1_RANGE_STATUS": "PASS",
        "AURORA_KSQ_1_RANGE_FIRST_ORDER": str(first),
        "AURORA_KSQ_1_RANGE_LAST_ORDER": str(last),
        "AURORA_KSQ_1_RANGE_SOURCES": str(last - first + 1),
    }
    for k, v in expected.items():
        if values.get(k) != v:
            fail(f"{status}: {k} expected {v!r}, got {values.get(k)!r}")

    dirs = []
    for order in range(first, last + 1):
        matches = sorted(evidence.glob(f"{order}-*"))
        if len(matches) != 1:
            fail(f"expected one evidence directory for order {order}, got {len(matches)}")
        build_status = matches[0] / "build-status.env"
        if not build_status.is_file():
            fail(f"missing build status for order {order}")
        text = build_status.read_text()
        if "AURORA_KSQ_1_BUILD_RESULT=PASS\n" not in text:
            fail(f"order {order} is not PASS")
        dirs.append(matches[0])


def collect_observed(evidence_roots: list[tuple[Path, int, int]]) -> tuple[dict[PackageKey, set[str]], int]:
    observed: dict[PackageKey, set[str]] = {}
    log_count = 0
    for evidence, first, last in evidence_roots:
        parse_range_status(evidence, first, last)
        for order in range(first, last + 1):
            src_dir = next(iter(sorted(evidence.glob(f"{order}-*"))))
            logs = sorted(src_dir.glob("*.build"))
            if len(logs) != 1:
                fail(f"order {order}: expected exactly one .build log, got {len(logs)}")
            log_count += 1
            log = logs[0]
            source = src_dir.name.split("-", 1)[1]
            for raw in log.read_text(encoding="utf-8", errors="replace").splitlines():
                m = GET_RE.match(raw)
                if not m:
                    continue
                key = PackageKey(m.group("package"), m.group("version"), m.group("arch"))
                observed.setdefault(key, set()).add(f"{order}:{source}")
    expected_logs = sum(last - first + 1 for _, first, last in evidence_roots)
    if log_count != expected_logs:
        fail(f"expected {expected_logs} witness logs, got {log_count}")
    if not observed:
        fail("no timestamped snapshot package acquisitions observed")
    return observed, log_count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-packages", type=Path, required=True)
    ap.add_argument("--r2-objects", type=Path, required=True)
    ap.add_argument("--evidence-066-080", type=Path, required=True)
    ap.add_argument("--evidence-081-090", type=Path, required=True)
    ap.add_argument("--evidence-091-101", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    signed = parse_deb822(args.snapshot_packages)
    if not signed:
        fail("signed snapshot Packages corpus is empty")
    r2 = parse_r2_objects(args.r2_objects)
    evidence = [
        (args.evidence_066_080, 66, 80),
        (args.evidence_081_090, 81, 90),
        (args.evidence_091_101, 91, 101),
    ]
    observed, log_count = collect_observed(evidence)

    resolved: dict[PackageKey, PackageRecord] = {}
    missing_metadata: list[PackageKey] = []
    for key in sorted(observed):
        rec = signed.get(key)
        if rec is None:
            missing_metadata.append(key)
        else:
            resolved[key] = rec
    if missing_metadata:
        fail("observed package selections absent from signed snapshot metadata: " + ", ".join(map(str, missing_metadata[:20])))

    # One exact payload object may satisfy only one exact package/version/arch record here.
    objects: dict[str, tuple[PackageKey, PackageRecord, set[str]]] = {}
    for key, rec in resolved.items():
        old = objects.get(rec.filename)
        if old is not None and (old[0] != key or old[1] != rec):
            fail(f"payload identity collision at {rec.filename}")
        objects[rec.filename] = (key, rec, observed[key])

    gap = {path: item for path, item in objects.items() if path not in r2}
    for path, (_, rec, _) in objects.items():
        if path in r2 and r2[path] != rec.size:
            fail(f"r2 size mismatch for signed object {path}: {r2[path]} != {rec.size}")

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "observed-packages.tsv").open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["package", "version", "architecture", "filename", "size", "sha256", "witness_orders"])
        for key in sorted(resolved):
            rec = resolved[key]
            w.writerow([key.package, key.version, key.architecture, rec.filename, rec.size, rec.sha256, ",".join(sorted(observed[key]))])

    with (args.out / "observed-objects.tsv").open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["filename", "size", "sha256", "package", "version", "architecture", "witness_orders"])
        for path in sorted(objects):
            key, rec, where = objects[path]
            w.writerow([path, rec.size, rec.sha256, key.package, key.version, key.architecture, ",".join(sorted(where))])

    with (args.out / "gap-objects.tsv").open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["filename", "size", "sha256", "package", "version", "architecture", "witness_orders"])
        for path in sorted(gap):
            key, rec, where = gap[path]
            w.writerow([path, rec.size, rec.sha256, key.package, key.version, key.architecture, ",".join(sorted(where))])

    observed_bytes = sum(item[1].size for item in objects.values())
    gap_bytes = sum(item[1].size for item in gap.values())
    with (args.out / "status.env").open("w") as f:
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_STATUS=PROVEN\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SNAPSHOT={SNAPSHOT}\n")
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_FIRST_ORDER=66\n")
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_LAST_ORDER=101\n")
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SOURCES=36\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_LOGS={log_count}\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_PACKAGES={len(resolved)}\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_OBJECTS={len(objects)}\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_OBJECT_BYTES={observed_bytes}\n")
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_R2_OBJECTS=1783\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_GAP_OBJECTS={len(gap)}\n")
        f.write(f"AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_GAP_BYTES={gap_bytes}\n")
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SIGNED_METADATA=apt-verified-snapshot-packages\n")
        f.write("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_MANUAL_PACKAGE_ADDITIONS=0\n")

    print((args.out / "status.env").read_text(), end="")
    print("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SUCCESS")


if __name__ == "__main__":
    main()
