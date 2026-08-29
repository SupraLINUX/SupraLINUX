#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests/kde-stack"
STATE = ROOT / "build/ksq-1/full"
DEBS = STATE / "debs"
EVIDENCE = STATE / "evidence-artifacts"
KWALLET = STATE / "kwallet-validation"
CLOSURE = ROOT / "build/ksq-0/build-order.tsv"
ADAPTATIONS = TESTS / "ksq-1-packaging-adaptations.tsv"
SUFFIX = "~supra26.04.1"

KWALLET_ADAPTATION = "kwallet-pam-compat13-relationship-substvars"
SYNTAX_ADAPTATION = "kf6-syntax-highlighting-deterministic-jinja-order"
EXPECTED_ADAPTATION_IDS = {KWALLET_ADAPTATION, SYNTAX_ADAPTATION}


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_FULL_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, expected: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != expected:
            fail(f"{path}: unexpected header {reader.fieldnames}")
        return list(reader)


def field(deb: Path, name: str) -> str:
    return subprocess.run(
        ["dpkg-deb", "-f", str(deb), name],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


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


def parse_ids(value: str) -> list[str]:
    if value == "-":
        return []
    ids = value.split(",")
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        fail(f"invalid adaptation id list {value!r}")
    return sorted(ids)


def main() -> int:
    if not CLOSURE.is_file():
        fail("KSQ-0 build order missing")
    if not ADAPTATIONS.is_file():
        fail("KSQ-1 packaging adaptation manifest missing")
    if not DEBS.is_dir():
        fail("merged DEB directory missing")
    if not EVIDENCE.is_dir():
        fail("evidence artifact directory missing")

    closure = read_tsv(
        CLOSURE,
        ["order", "source_package", "packaging_version", "candidate_family", "decision"],
    )
    if len(closure) != 101:
        fail(f"closure contains {len(closure)} rows, expected 101")
    closure_by_order = {int(row["order"]): row for row in closure}
    if sorted(closure_by_order) != list(range(1, 102)):
        fail("closure order is not exactly 1..101")
    closure_by_source = {row["source_package"]: row for row in closure}
    if len(closure_by_source) != 101:
        fail("closure source package names are not unique")

    adaptation_rows = read_tsv(
        ADAPTATIONS,
        ["source_package", "source_version", "adaptation_id", "kind", "implementation_ref", "reason"],
    )
    ids = [row["adaptation_id"] for row in adaptation_rows]
    if len(ids) != len(set(ids)):
        fail("packaging adaptation manifest contains duplicate adaptation IDs")
    if set(ids) != EXPECTED_ADAPTATION_IDS:
        fail(f"packaging adaptation boundary changed: {sorted(ids)}")

    expected_adaptations: dict[str, list[str]] = {source: [] for source in closure_by_source}
    for row in adaptation_rows:
        source = row["source_package"]
        expected = closure_by_source.get(source)
        if expected is None:
            fail(f"adaptation {row['adaptation_id']} references source outside closure: {source}")
        if row["source_version"] != expected["packaging_version"]:
            fail(
                f"adaptation {row['adaptation_id']} version {row['source_version']} "
                f"!= closure packaging version {expected['packaging_version']}"
            )
        expected_adaptations[source].append(row["adaptation_id"])

        if row["adaptation_id"] == SYNTAX_ADAPTATION:
            expected_ref = "packaging/ksq-1/patches/kf6-syntax-highlighting/supralinux-deterministic-jinja-order.patch"
            if row["kind"] != "quilt-source-patch" or row["implementation_ref"] != expected_ref:
                fail("syntax-highlighting adaptation implementation metadata drifted")
            if not (ROOT / expected_ref).is_file():
                fail("syntax-highlighting declared patch file is missing")
        elif row["adaptation_id"] == KWALLET_ADAPTATION:
            expected_ref = "scripts/ci/prepare-ksq-1-source.py#restore_kwallet_compat13_substvars"
            if row["kind"] != "control-relationship-restoration" or row["implementation_ref"] != expected_ref:
                fail("kwallet-pam adaptation implementation metadata drifted")

    manifest_paths = sorted(EVIDENCE.rglob("build-manifest.tsv"))
    binary_paths = sorted(EVIDENCE.rglob("binary-packages.tsv"))
    status_paths = sorted(EVIDENCE.rglob("range-status.env"))
    hash_paths = sorted(EVIDENCE.rglob("new-debs.sha256"))
    prepared_paths = sorted(EVIDENCE.rglob("prepared-source.env"))
    if not (len(manifest_paths) == len(binary_paths) == len(status_paths) == len(hash_paths) == 5):
        fail(
            "expected five range evidence sets, got "
            f"manifests={len(manifest_paths)} binaries={len(binary_paths)} "
            f"status={len(status_paths)} hashes={len(hash_paths)}"
        )
    if len(prepared_paths) != 101:
        fail(f"expected 101 prepared-source evidence files, got {len(prepared_paths)}")

    prepared_seen: set[str] = set()
    for path in prepared_paths:
        env = read_env(path)
        source = env.get("AURORA_KSQ_1_SOURCE", "")
        if source not in closure_by_source:
            fail(f"{path}: unexpected prepared source {source!r}")
        if source in prepared_seen:
            fail(f"prepared source evidence duplicated for {source}")
        prepared_seen.add(source)
        expected = closure_by_source[source]
        base = env.get("AURORA_KSQ_1_PACKAGING_BASE")
        if base != expected["packaging_version"]:
            fail(f"{path}: packaging base {base!r} != {expected['packaging_version']!r}")
        expected_version = expected["packaging_version"] + SUFFIX
        if env.get("AURORA_KSQ_1_VERSION") != expected_version:
            fail(f"{path}: prepared version mismatch")

        actual_ids = parse_ids(env.get("AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS", ""))
        wanted_ids = sorted(expected_adaptations[source])
        if actual_ids != wanted_ids:
            fail(f"{path}: adaptations {actual_ids} != declared {wanted_ids}")
        if int(env.get("AURORA_KSQ_1_PACKAGING_ADAPTATIONS_APPLIED", "-1")) != len(wanted_ids):
            fail(f"{path}: packaging adaptation count mismatch")

        expected_override_count = 1 if source == "kwallet-pam" else 0
        if int(env.get("AURORA_KSQ_1_OVERRIDES_APPLIED", "-1")) != expected_override_count:
            fail(f"{path}: certified Build-Depends override count mismatch")
        expected_substvars = 3 if source == "kwallet-pam" else 0
        if int(env.get("AURORA_KSQ_1_COMPAT13_SUBSTVARS_RESTORED", "-1")) != expected_substvars:
            fail(f"{path}: compat13 substvar restoration count mismatch")

    if prepared_seen != set(closure_by_source):
        fail("prepared source evidence does not cover exact 101-source closure")

    manifest_header = [
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
    binary_header = [
        "order",
        "source_package",
        "binary_package",
        "filename",
        "version",
        "architecture",
    ]

    manifests: list[dict[str, str]] = []
    binaries: list[dict[str, str]] = []
    for path in manifest_paths:
        manifests.extend(read_tsv(path, manifest_header))
    for path in binary_paths:
        binaries.extend(read_tsv(path, binary_header))

    if len(manifests) != 101:
        fail(f"combined build manifest contains {len(manifests)} sources, expected 101")
    manifest_by_order: dict[int, dict[str, str]] = {}
    for row in manifests:
        order = int(row["order"])
        if order in manifest_by_order:
            fail(f"duplicate source order {order}")
        manifest_by_order[order] = row
        expected = closure_by_order.get(order)
        if expected is None:
            fail(f"manifest contains unexpected order {order}")
        checks = {
            "source_package": expected["source_package"],
            "packaging_base": expected["packaging_version"],
            "candidate_family": expected["candidate_family"],
            "decision": expected["decision"],
        }
        for key, value in checks.items():
            if row[key] != value:
                fail(f"order {order} {key}={row[key]!r}, expected {value!r}")
        expected_version = expected["packaging_version"] + SUFFIX
        if row["supra_version"] != expected_version:
            fail(f"order {order} version {row['supra_version']} != {expected_version}")
        if row["result"] != "PASS":
            fail(f"order {order} result is {row['result']}")
        if int(row["deb_count"]) < 1 or int(row["buildinfo_count"]) < 1 or int(row["changes_count"]) < 1:
            fail(f"order {order} has incomplete build artifacts")

    if sorted(manifest_by_order) != list(range(1, 102)):
        fail("combined manifest order is not exactly 1..101")

    package_seen: dict[str, str] = {}
    filename_seen: dict[str, str] = {}
    binary_count_by_order = {order: 0 for order in range(1, 102)}
    for row in binaries:
        order = int(row["order"])
        manifest = manifest_by_order.get(order)
        if manifest is None:
            fail(f"binary row references unknown source order {order}")
        if row["source_package"] != manifest["source_package"]:
            fail(f"binary {row['binary_package']} source mismatch at order {order}")
        if row["version"] != manifest["supra_version"]:
            fail(f"binary {row['binary_package']} version mismatch at order {order}")

        package = row["binary_package"]
        filename = row["filename"]
        if package in package_seen:
            fail(f"binary package {package} produced twice: {package_seen[package]} and {filename}")
        if filename in filename_seen:
            fail(f"binary filename {filename} recorded twice")
        package_seen[package] = filename
        filename_seen[filename] = package
        binary_count_by_order[order] += 1

        deb = DEBS / filename
        if not deb.is_file():
            fail(f"recorded DEB missing: {filename}")
        if field(deb, "Package") != package:
            fail(f"{filename}: Package field mismatch")
        if field(deb, "Version") != row["version"]:
            fail(f"{filename}: Version field mismatch")
        if field(deb, "Architecture") != row["architecture"]:
            fail(f"{filename}: Architecture field mismatch")

    for order, count in binary_count_by_order.items():
        if count < 1:
            fail(f"source order {order} has no recorded binary packages")

    actual_debs = {path.name for path in DEBS.glob("*.deb")}
    recorded_debs = set(filename_seen)
    if actual_debs != recorded_debs:
        missing = sorted(recorded_debs - actual_debs)
        extra = sorted(actual_debs - recorded_debs)
        fail(f"merged DEB set differs from evidence; missing={missing} extra={extra}")

    hashed: dict[str, str] = {}
    for path in hash_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                fail(f"{path}: malformed checksum line {line!r}")
            digest, filename = parts
            filename = filename.lstrip("*")
            if "/" in filename:
                fail(f"{path}: checksum is not relocatable: {filename}")
            if filename in hashed:
                fail(f"checksum recorded twice for {filename}")
            deb = DEBS / filename
            if not deb.is_file():
                fail(f"{path}: checksum target missing {filename}")
            actual = sha256(deb)
            if actual != digest:
                fail(f"{filename}: SHA-256 mismatch")
            hashed[filename] = digest
    if set(hashed) != actual_debs:
        fail("range checksum union does not exactly cover merged DEB set")

    expected_ranges = {(1, 20), (21, 40), (41, 60), (61, 80), (81, 101)}
    observed_ranges: set[tuple[int, int]] = set()
    for path in status_paths:
        env = read_env(path)
        if env.get("AURORA_KSQ_1_RANGE_STATUS") != "PASS":
            fail(f"{path}: range did not PASS")
        first = int(env["AURORA_KSQ_1_RANGE_FIRST_ORDER"])
        last = int(env["AURORA_KSQ_1_RANGE_LAST_ORDER"])
        observed_ranges.add((first, last))
        if env.get("AURORA_KSQ_1_RANGE_FULL_CERTIFIED") != "no":
            fail(f"{path}: premature full certification marker")
    if observed_ranges != expected_ranges:
        fail(f"unexpected checkpoint coverage {sorted(observed_ranges)}")

    kwallet_status = KWALLET / "status.env"
    if not kwallet_status.is_file():
        fail("KWallet validation status missing")
    kwallet = read_env(kwallet_status)
    required_kwallet = {
        "AURORA_KSQ_1_KWALLET_VERSION": "4:6.7.4-0ubuntu3~supra26.04.1",
        "AURORA_KSQ_1_KWALLET_COMPAT": "13",
        "AURORA_KSQ_1_KWALLET_SUBSTVARS_RESTORED": "misc+qml6+shlibs",
        "AURORA_KSQ_1_KWALLET_BINARY_RUNTIME_DEPS": "PASS",
        "AURORA_KSQ_1_KWALLET_PAM_INSTALLATION": "PASS",
        "AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED": "no",
    }
    for key, value in required_kwallet.items():
        if kwallet.get(key) != value:
            fail(f"KWallet {key}={kwallet.get(key)!r}, expected {value!r}")

    full_manifest = STATE / "full-build-manifest.tsv"
    with full_manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=manifest_header, lineterminator="\n")
        writer.writeheader()
        for order in range(1, 102):
            writer.writerow(manifest_by_order[order])

    full_binaries = STATE / "full-binary-packages.tsv"
    with full_binaries.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=binary_header, lineterminator="\n")
        writer.writeheader()
        for row in sorted(binaries, key=lambda item: (int(item["order"]), item["binary_package"])):
            writer.writerow(row)

    with (STATE / "full-debs.sha256").open("w", encoding="utf-8") as handle:
        for filename in sorted(actual_debs):
            handle.write(f"{sha256(DEBS / filename)}  {filename}\n")

    status = STATE / "full-build-status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_FULL_BUILD_STATUS=PASS",
                "AURORA_KSQ_1_FULL_BUILD_SOURCES=101",
                f"AURORA_KSQ_1_FULL_BUILD_BINARIES={len(actual_debs)}",
                "AURORA_KSQ_1_FULL_BUILD_CHECKPOINTS=5",
                f"AURORA_KSQ_1_FULL_BUILD_PACKAGING_ADAPTATIONS={len(adaptation_rows)}",
                "AURORA_KSQ_1_FULL_BUILD_KWALLET_PAM=PASS",
                "AURORA_KSQ_1_FULL_BUILD_REPRODUCIBILITY_CERTIFIED=no",
                "AURORA_KSQ_1_FULL_CERTIFIED=no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_FULL_BUILD_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
