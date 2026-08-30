#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "build/ksq-0/build-order.tsv"
SUFFIX = "~supra26.04.1"
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
BINARY_HEADER = [
    "order",
    "source_package",
    "binary_package",
    "filename",
    "version",
    "architecture",
]


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_TAIL_MERGE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_tsv(path: Path, expected: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"missing TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != expected:
            fail(f"{path}: unexpected header {reader.fieldnames}")
        return list(reader)


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deb_field(path: Path, field: str) -> str:
    return subprocess.run(
        ["dpkg-deb", "-f", str(path), field],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def write_hash_tree(root: Path, output: Path) -> None:
    rows: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        rows.append(f"{sha256(path)}  {rel}")
    output.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def source_dir(evidence: Path, order: int, source: str) -> Path:
    matches = [path for path in evidence.glob(f"{order}-*") if path.is_dir()]
    exact = [path for path in matches if path.name == f"{order}-{source}"]
    if len(exact) != 1:
        fail(f"{evidence}: expected one source directory {order}-{source}, got {len(exact)}")
    return exact[0]


def validate_source_status(directory: Path, order: int, source: str, version: str) -> None:
    status = read_env(directory / "build-status.env")
    expected = {
        "AURORA_KSQ_1_BUILD_RESULT": "PASS",
        "AURORA_KSQ_1_BUILD_ORDER": str(order),
        "AURORA_KSQ_1_BUILD_SOURCE": source,
        "AURORA_KSQ_1_BUILD_VERSION": version,
        "AURORA_KSQ_1_BUILD_RESOLVE_ALTERNATIVES": "yes",
    }
    for key, value in expected.items():
        if status.get(key) != value:
            fail(f"{directory}: {key}={status.get(key)!r}, expected {value!r}")


def validate_manifest_rows(
    rows: list[dict[str, str]],
    expected_orders: list[int],
    closure: dict[int, dict[str, str]],
    label: str,
) -> None:
    orders = [int(row["order"]) for row in rows]
    if orders != expected_orders:
        fail(f"{label}: orders {orders} != expected {expected_orders}")
    for row in rows:
        order = int(row["order"])
        expected = closure[order]
        comparisons = {
            "source_package": expected["source_package"],
            "packaging_base": expected["packaging_version"],
            "candidate_family": expected["candidate_family"],
            "decision": expected["decision"],
            "supra_version": expected["packaging_version"] + SUFFIX,
            "result": "PASS",
        }
        for key, value in comparisons.items():
            if row[key] != value:
                fail(f"{label} order {order}: {key}={row[key]!r}, expected {value!r}")
        if min(int(row["deb_count"]), int(row["buildinfo_count"]), int(row["changes_count"])) < 1:
            fail(f"{label} order {order}: incomplete build artifact counts")


def validate_binary_rows(
    rows: list[dict[str, str]],
    manifest: dict[int, dict[str, str]],
    allowed_orders: set[int],
    label: str,
) -> None:
    seen_package: set[str] = set()
    seen_filename: set[str] = set()
    counts = {order: 0 for order in allowed_orders}
    for row in rows:
        order = int(row["order"])
        if order not in allowed_orders:
            fail(f"{label}: binary row outside expected orders: {order}")
        source = manifest[order]
        if row["source_package"] != source["source_package"]:
            fail(f"{label}: binary source mismatch at order {order}")
        if row["version"] != source["supra_version"]:
            fail(f"{label}: binary version mismatch at order {order}")
        package = row["binary_package"]
        filename = row["filename"]
        if package in seen_package or filename in seen_filename:
            fail(f"{label}: duplicate binary {package}/{filename}")
        seen_package.add(package)
        seen_filename.add(filename)
        counts[order] += 1
    missing = [order for order, count in sorted(counts.items()) if count < 1]
    if missing:
        fail(f"{label}: source orders without binaries: {missing}")


def validate_deb_set(
    directory: Path,
    rows: list[dict[str, str]],
    label: str,
) -> None:
    expected = {row["filename"]: row for row in rows}
    actual = {path.name: path for path in directory.glob("*.deb")}
    if set(actual) != set(expected):
        fail(
            f"{label}: DEB set differs; missing={sorted(set(expected)-set(actual))} "
            f"extra={sorted(set(actual)-set(expected))}"
        )
    for filename, row in expected.items():
        deb = actual[filename]
        metadata = (
            deb_field(deb, "Package"),
            deb_field(deb, "Version"),
            deb_field(deb, "Architecture"),
        )
        wanted = (row["binary_package"], row["version"], row["architecture"])
        if metadata != wanted:
            fail(f"{label}: metadata mismatch for {filename}: {metadata} != {wanted}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial-last", required=True, type=int)
    parser.add_argument("--partial-evidence", required=True, type=Path)
    parser.add_argument("--partial-debs", required=True, type=Path)
    parser.add_argument("--completion-evidence", required=True, type=Path)
    parser.add_argument("--completion-debs", required=True, type=Path)
    parser.add_argument("--prior-debs", required=True, type=Path)
    parser.add_argument("--output-evidence", required=True, type=Path)
    parser.add_argument("--output-debs", required=True, type=Path)
    parser.add_argument("--base-run-id", required=True)
    parser.add_argument("--base-head-sha", required=True)
    parser.add_argument("--resume-run-id", required=True)
    parser.add_argument("--resume-head-sha", required=True)
    args = parser.parse_args()

    if not 81 <= args.partial_last <= 100:
        fail(f"partial-last {args.partial_last} is outside 81..100")
    resume_start = args.partial_last + 1
    if not args.base_run_id.isdigit() or not args.resume_run_id.isdigit():
        fail("run IDs must be numeric")
    for label, sha in (("base", args.base_head_sha), ("resume", args.resume_head_sha)):
        if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha.lower()):
            fail(f"{label} head SHA is invalid: {sha!r}")

    for path in (
        args.partial_evidence,
        args.partial_debs,
        args.completion_evidence,
        args.completion_debs,
        args.prior_debs,
    ):
        if not path.is_dir():
            fail(f"input directory missing: {path}")
    if not CLOSURE.is_file():
        fail("KSQ-0 build order missing")

    closure_rows = read_tsv(
        CLOSURE,
        ["order", "source_package", "packaging_version", "candidate_family", "decision"],
    )
    closure = {int(row["order"]): row for row in closure_rows}
    if sorted(closure) != list(range(1, 102)):
        fail("KSQ-0 closure is not exactly orders 1..101")

    partial_rows = read_tsv(args.partial_evidence / "build-manifest.tsv", MANIFEST_HEADER)
    completion_rows = read_tsv(args.completion_evidence / "build-manifest.tsv", MANIFEST_HEADER)
    partial_orders = list(range(81, args.partial_last + 1))
    completion_orders = list(range(resume_start, 102))
    validate_manifest_rows(partial_rows, partial_orders, closure, "partial evidence")
    validate_manifest_rows(completion_rows, completion_orders, closure, "completion evidence")

    partial_manifest = {int(row["order"]): row for row in partial_rows}
    completion_manifest = {int(row["order"]): row for row in completion_rows}
    merged_manifest = {**partial_manifest, **completion_manifest}
    if sorted(merged_manifest) != list(range(81, 102)):
        fail("merged tail manifest is not exactly 81..101")

    partial_binary = read_tsv(args.partial_evidence / "binary-packages.tsv", BINARY_HEADER)
    completion_binary = read_tsv(args.completion_evidence / "binary-packages.tsv", BINARY_HEADER)
    validate_binary_rows(partial_binary, partial_manifest, set(partial_orders), "partial evidence")
    validate_binary_rows(completion_binary, completion_manifest, set(completion_orders), "completion evidence")

    all_binary = partial_binary + completion_binary
    packages = [row["binary_package"] for row in all_binary]
    filenames = [row["filename"] for row in all_binary]
    if len(packages) != len(set(packages)):
        fail("merged tail contains duplicate binary package names")
    if len(filenames) != len(set(filenames)):
        fail("merged tail contains duplicate binary filenames")

    validate_deb_set(args.partial_debs, partial_binary, "partial DEBs")
    validate_deb_set(args.completion_debs, completion_binary, "completion DEBs")

    # A timed-out base range may retain a prepared source directory for the
    # interrupted order. Only PASS source directories are eligible for merge.
    pass_orders_in_partial: set[int] = set()
    for status in args.partial_evidence.glob("*-*/build-status.env"):
        env = read_env(status)
        if env.get("AURORA_KSQ_1_BUILD_RESULT") == "PASS":
            pass_orders_in_partial.add(int(env["AURORA_KSQ_1_BUILD_ORDER"]))
    if pass_orders_in_partial != set(partial_orders):
        fail(
            f"partial PASS source set {sorted(pass_orders_in_partial)} "
            f"!= expected {partial_orders}"
        )

    pass_orders_in_completion: set[int] = set()
    for status in args.completion_evidence.glob("*-*/build-status.env"):
        env = read_env(status)
        if env.get("AURORA_KSQ_1_BUILD_RESULT") == "PASS":
            pass_orders_in_completion.add(int(env["AURORA_KSQ_1_BUILD_ORDER"]))
    if pass_orders_in_completion != set(completion_orders):
        fail(
            f"completion PASS source set {sorted(pass_orders_in_completion)} "
            f"!= expected {completion_orders}"
        )

    out_evidence = args.output_evidence.resolve()
    out_debs = args.output_debs.resolve()
    if out_evidence.exists():
        shutil.rmtree(out_evidence)
    if out_debs.exists():
        shutil.rmtree(out_debs)
    out_evidence.mkdir(parents=True)
    out_debs.mkdir(parents=True)

    for order in range(81, 102):
        row = merged_manifest[order]
        version = row["supra_version"]
        source = row["source_package"]
        src_root = args.partial_evidence if order <= args.partial_last else args.completion_evidence
        src_dir = source_dir(src_root, order, source)
        validate_source_status(src_dir, order, source, version)
        shutil.copytree(src_dir, out_evidence / src_dir.name)

    binary_by_filename = {row["filename"]: row for row in all_binary}
    for filename in sorted(binary_by_filename):
        src_root = args.partial_debs if filename in {row["filename"] for row in partial_binary} else args.completion_debs
        shutil.copy2(src_root / filename, out_debs / filename)

    with (out_evidence / "build-manifest.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for order in range(81, 102):
            writer.writerow(merged_manifest[order])

    with (out_evidence / "binary-packages.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BINARY_HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in sorted(all_binary, key=lambda item: (int(item["order"]), item["binary_package"])):
            writer.writerow(row)

    tail_hashes = [f"{sha256(path)}  {path.name}" for path in sorted(out_debs.glob("*.deb"))]
    (out_evidence / "new-debs.sha256").write_text("\n".join(tail_hashes) + "\n", encoding="utf-8")

    prior_files = {path.name: path for path in args.prior_debs.glob("*.deb")}
    tail_files = {path.name: path for path in out_debs.glob("*.deb")}
    overlap = set(prior_files) & set(tail_files)
    if overlap:
        fail(f"prior/tail DEB filename overlap: {sorted(overlap)}")
    accumulated = {**prior_files, **tail_files}
    accumulated_hashes = [
        f"{sha256(path)}  {name}" for name, path in sorted(accumulated.items())
    ]
    (out_evidence / "accumulated-debs.sha256").write_text(
        "\n".join(accumulated_hashes) + "\n", encoding="utf-8"
    )

    (out_evidence / "range-status.env").write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_RANGE_STATUS=PASS",
                "AURORA_KSQ_1_RANGE_FIRST_ORDER=81",
                "AURORA_KSQ_1_RANGE_LAST_ORDER=101",
                "AURORA_KSQ_1_RANGE_SOURCES=21",
                f"AURORA_KSQ_1_RANGE_NEW_DEBS={len(tail_files)}",
                f"AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS={len(accumulated)}",
                "AURORA_KSQ_1_RANGE_RESOLVE_ALTERNATIVES=yes",
                "AURORA_KSQ_1_RANGE_FULL_CERTIFIED=no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    provenance = out_evidence / "tail-resume-provenance.env"
    provenance.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_TAIL_RESUME_STATUS=PASS",
                f"AURORA_KSQ_1_TAIL_BASE_RUN_ID={args.base_run_id}",
                f"AURORA_KSQ_1_TAIL_BASE_HEAD_SHA={args.base_head_sha}",
                "AURORA_KSQ_1_TAIL_PARTIAL_FIRST=81",
                f"AURORA_KSQ_1_TAIL_PARTIAL_LAST={args.partial_last}",
                f"AURORA_KSQ_1_TAIL_RESUME_FIRST={resume_start}",
                "AURORA_KSQ_1_TAIL_RESUME_LAST=101",
                f"AURORA_KSQ_1_TAIL_RESUME_RUN_ID={args.resume_run_id}",
                f"AURORA_KSQ_1_TAIL_RESUME_HEAD_SHA={args.resume_head_sha}",
                "AURORA_KSQ_1_TAIL_CANONICAL_RANGE=81-101",
                "AURORA_KSQ_1_TAIL_FULL_CERTIFIED=no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    write_hash_tree(args.partial_evidence, out_evidence / "resume-partial-evidence-input.sha256")
    write_hash_tree(args.partial_debs, out_evidence / "resume-partial-debs-input.sha256")
    write_hash_tree(args.completion_evidence, out_evidence / "resume-completion-evidence-input.sha256")
    write_hash_tree(args.completion_debs, out_evidence / "resume-completion-debs-input.sha256")

    # Verify the canonical output we just created before returning PASS.
    validate_deb_set(out_debs, all_binary, "canonical tail DEBs")
    if len(read_tsv(out_evidence / "build-manifest.tsv", MANIFEST_HEADER)) != 21:
        fail("canonical tail manifest does not contain 21 sources")

    print(provenance.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_TAIL_MERGE_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
