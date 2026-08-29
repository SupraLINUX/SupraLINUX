#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "build/ksq-1/full"
DEBS = STATE / "debs"
EVIDENCE = STATE / "evidence-artifacts"
KWALLET = STATE / "kwallet-validation"
CLOSURE = ROOT / "build/ksq-0/build-order.tsv"
SUFFIX = "~supra26.04.1"


def fail(message: str) -> "NoReturn":
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


def main() -> int:
    if not CLOSURE.is_file():
        fail("KSQ-0 build order missing")
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

    manifest_paths = sorted(EVIDENCE.rglob("build-manifest.tsv"))
    binary_paths = sorted(EVIDENCE.rglob("binary-packages.tsv"))
    status_paths = sorted(EVIDENCE.rglob("range-status.env"))
    hash_paths = sorted(EVIDENCE.rglob("new-debs.sha256"))
    if not (len(manifest_paths) == len(binary_paths) == len(status_paths) == len(hash_paths) == 5):
        fail(
            "expected five range evidence sets, got "
            f"manifests={len(manifest_paths)} binaries={len(binary_paths)} "
            f"status={len(status_paths)} hashes={len(hash_paths)}"
        )

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
