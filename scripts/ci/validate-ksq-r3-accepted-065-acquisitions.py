#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_LOGS = 65
EXPECTED_EVENTS = 28215
EXPECTED_UNIQUE = 1052
EXPECTED_GAP = 3
GET_RE = re.compile(
    r"^Get:\d+\s+file:\S+/ubuntu\s+(\S+)/(\S+)\s+(amd64|all)\s+"
    r"(\S+)\s+(amd64|all)\s+(\S+)\s+\["
)


def fail(msg: str) -> None:
    print(f"AURORA_KSQ_R3_ACCEPTED_065_ACQUISITION_FAILURE: {msg}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"missing TSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def env(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"missing env: {path}")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            fail(f"malformed env row in {path}: {raw}")
        k, v = raw.split("=", 1)
        out[k] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r3-root", type=Path, required=True)
    ap.add_argument("--checkpoint-root", type=Path, action="append", required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    r3 = args.r3_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    prov = env(r3 / "provenance.env")
    expected_prov = {
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS": "COMPLETE",
        "AURORA_KSQ_SNAPSHOT_SLICE_ID": "20260829T022000Z-r3",
        "AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SNAPSHOT": "20260829T022000Z",
        "AURORA_KSQ_SNAPSHOT_SLICE_INSTALL_RECOMMENDS": "default",
        "AURORA_KSQ_SNAPSHOT_SLICE_BINARY_OBJECTS": "1786",
        "AURORA_KSQ_SNAPSHOT_R3_BASE_BINARY_OBJECTS": "1783",
        "AURORA_KSQ_SNAPSHOT_R3_GAP_OBJECTS": "3",
        "AURORA_KSQ_SNAPSHOT_R3_GAP_BYTES": "547318",
        "AURORA_KSQ_SNAPSHOT_R3_WITNESS_STATUS": "PROVEN",
        "AURORA_KSQ_SNAPSHOT_R3_MANUAL_PACKAGE_ADDITIONS": "0",
    }
    for k, v in expected_prov.items():
        if prov.get(k) != v:
            fail(f"r3 provenance mismatch {k}={prov.get(k)!r}, expected {v!r}")

    binary_rows = read_tsv(r3 / "manifests/binary.tsv")
    gap_rows = read_tsv(r3 / "manifests/r3-gap.tsv")
    if len(binary_rows) != 1786:
        fail(f"r3 binary manifest count {len(binary_rows)} != 1786")
    if len(gap_rows) != EXPECTED_GAP:
        fail(f"r3 gap count {len(gap_rows)} != {EXPECTED_GAP}")

    by_identity: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in binary_rows:
        by_identity[(row["package"], row["version"], row["architecture"])].append(row)

    logs: list[Path] = []
    for root in args.checkpoint_root:
        root = root.resolve()
        if not root.is_dir():
            fail(f"checkpoint root missing: {root}")
        logs.extend(sorted(root.rglob("*.build")))
    logs = sorted(set(logs))
    if len(logs) != EXPECTED_LOGS:
        fail(f"accepted build log count {len(logs)} != {EXPECTED_LOGS}")
    if len({p.name for p in logs}) != EXPECTED_LOGS:
        fail("accepted build log basenames are not unique")

    events: list[tuple[str, str, str, str, str, str, str]] = []
    per_log = Counter()
    for log in logs:
        text = log.read_text(encoding="utf-8", errors="replace")
        if "Status: successful" not in text:
            fail(f"accepted log is not successful: {log}")
        for line in text.splitlines():
            m = GET_RE.match(line)
            if not m:
                continue
            suite, component, index_arch, package, arch, version = m.groups()
            events.append((log.name, suite, component, index_arch, package, arch, version))
            per_log[log.name] += 1
        if per_log[log.name] == 0:
            fail(f"no Ubuntu package acquisitions parsed from accepted log: {log}")

    if len(events) != EXPECTED_EVENTS:
        fail(f"accepted Ubuntu acquisition events {len(events)} != {EXPECTED_EVENTS}")

    identities = sorted({(e[4], e[5], e[6]) for e in events})
    if len(identities) != EXPECTED_UNIQUE:
        fail(f"accepted unique package identities {len(identities)} != {EXPECTED_UNIQUE}")

    gap_ids = {(r["package"], r["architecture"], r["version"]) for r in gap_rows}
    gap_names = {r["package"] for r in gap_rows}
    observed_ids = set(identities)
    observed_names = {p for p, _, _ in identities}
    exact_intersection = sorted(observed_ids & gap_ids)
    name_intersection = sorted(observed_names & gap_names)
    if exact_intersection:
        fail(f"accepted acquisitions intersect r3 gap identities: {exact_intersection}")
    if name_intersection:
        fail(f"accepted acquisitions intersect r3 gap package names: {name_intersection}")

    verified_payloads = 0
    manifest_rows_used = 0
    corpus_rows: list[tuple[str, str, str, str, str, str]] = []
    for package, arch, version in identities:
        matches = by_identity.get((package, version, arch), [])
        if len(matches) != 1:
            fail(
                f"r3 physical manifest identity {package}={version}/{arch} has {len(matches)} matches"
            )
        row = matches[0]
        payload = r3 / row["path"]
        if not payload.is_file():
            fail(f"r3 payload missing for accepted identity: {row['path']}")
        if payload.stat().st_size != int(row["size"]):
            fail(f"r3 payload size mismatch: {row['path']}")
        if sha256(payload) != row["sha256"]:
            fail(f"r3 payload SHA256 mismatch: {row['path']}")
        verified_payloads += 1
        manifest_rows_used += 1
        corpus_rows.append((package, version, arch, row["path"], row["size"], row["sha256"]))

    with (out / "accepted-065-ubuntu-acquisitions.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(("package", "version", "architecture", "r3_path", "size", "sha256"))
        w.writerows(corpus_rows)

    with (out / "accepted-065-acquisition-events.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(("build_log", "suite", "component", "index_arch", "package", "architecture", "version"))
        w.writerows(events)

    with (out / "r3-gap-package-names.txt").open("w", encoding="utf-8") as f:
        for name in sorted(gap_names):
            f.write(name + "\n")

    status = {
        "AURORA_KSQ_R3_ACCEPTED_065_ACQUISITION_REGRESSION": "PASS",
        "AURORA_KSQ_R3_ACCEPTED_065_BUILD_LOGS": str(len(logs)),
        "AURORA_KSQ_R3_ACCEPTED_065_UBUNTU_ACQUISITION_EVENTS": str(len(events)),
        "AURORA_KSQ_R3_ACCEPTED_065_UNIQUE_UBUNTU_IDENTITIES": str(len(identities)),
        "AURORA_KSQ_R3_ACCEPTED_065_R3_PAYLOADS_VERIFIED": str(verified_payloads),
        "AURORA_KSQ_R3_ACCEPTED_065_GAP_OBJECTS": str(len(gap_rows)),
        "AURORA_KSQ_R3_ACCEPTED_065_GAP_IDENTITY_INTERSECTION": "0",
        "AURORA_KSQ_R3_ACCEPTED_065_GAP_PACKAGE_NAME_INTERSECTION": "0",
        "AURORA_KSQ_R3_ACCEPTED_065_SIGNED_METADATA_IDENTITY_REQUIRED": "yes",
        "AURORA_KSQ_R3_ACCEPTED_065_FULL_SOURCE_REBUILD_REQUIRED_BY_THIS_DELTA": "no",
    }
    with (out / "acquisition-regression.env").open("w", encoding="utf-8") as f:
        for k, v in status.items():
            f.write(f"{k}={v}\n")

    print("AURORA_KSQ_R3_ACCEPTED_065_ACQUISITION_REGRESSION=PASS")
    print(f"AURORA_KSQ_R3_ACCEPTED_065_BUILD_LOGS={len(logs)}")
    print(f"AURORA_KSQ_R3_ACCEPTED_065_UBUNTU_ACQUISITION_EVENTS={len(events)}")
    print(f"AURORA_KSQ_R3_ACCEPTED_065_UNIQUE_UBUNTU_IDENTITIES={len(identities)}")
    print("AURORA_KSQ_R3_ACCEPTED_065_GAP_INTERSECTION=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
