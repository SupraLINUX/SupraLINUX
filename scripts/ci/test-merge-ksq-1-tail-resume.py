#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MERGER = ROOT / "scripts/ci/merge-ksq-1-tail-resume.py"
CLOSURE = ROOT / "build/ksq-0/build-order.tsv"
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


def write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def build_deb(output: Path, package: str, version: str) -> None:
    with tempfile.TemporaryDirectory(prefix="ksq-tail-deb-") as tmp:
        root = Path(tmp)
        control = root / "DEBIAN/control"
        control.parent.mkdir(parents=True)
        control.write_text(
            "\n".join(
                [
                    f"Package: {package}",
                    f"Version: {version}",
                    "Architecture: amd64",
                    "Maintainer: SupraLINUX CI <ci@example.invalid>",
                    "Description: synthetic KSQ tail merge fixture",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(output)], check=True, stdout=subprocess.DEVNULL)


def fixture_rows(first: int, last: int, deb_dir: Path, evidence: Path) -> tuple[list[list[str]], list[list[str]]]:
    manifests: list[list[str]] = []
    binaries: list[list[str]] = []
    deb_dir.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    for order in range(first, last + 1):
        source = f"source-{order}"
        base = f"1.0-{order}"
        version = f"{base}~supra26.04.1"
        package = f"pkg-{order}"
        filename = f"{package}_{version}_amd64.deb"
        build_deb(deb_dir / filename, package, version)
        source_evidence = evidence / f"{order}-{source}"
        source_evidence.mkdir(parents=True)
        (source_evidence / "build-status.env").write_text(
            "\n".join(
                [
                    "AURORA_KSQ_1_BUILD_RESULT=PASS",
                    f"AURORA_KSQ_1_BUILD_ORDER={order}",
                    f"AURORA_KSQ_1_BUILD_SOURCE={source}",
                    f"AURORA_KSQ_1_BUILD_VERSION={version}",
                    "AURORA_KSQ_1_BUILD_RESOLVE_ALTERNATIVES=yes",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (source_evidence / "fixture.txt").write_text(f"fixture {order}\n", encoding="utf-8")
        manifests.append([str(order), source, base, version, "test", "candidate", "1", "1", "1", "PASS"])
        binaries.append([str(order), source, package, filename, version, "amd64"])
    write_tsv(evidence / "build-manifest.tsv", MANIFEST_HEADER, manifests)
    write_tsv(evidence / "binary-packages.tsv", BINARY_HEADER, binaries)
    return manifests, binaries


def invoke(work: Path, partial_evidence: Path, partial_debs: Path, completion_evidence: Path, completion_debs: Path, expected_success: bool) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [
            sys.executable,
            str(MERGER),
            "--partial-last",
            "98",
            "--partial-evidence",
            str(partial_evidence),
            "--partial-debs",
            str(partial_debs),
            "--completion-evidence",
            str(completion_evidence),
            "--completion-debs",
            str(completion_debs),
            "--prior-debs",
            str(work / "prior"),
            "--output-evidence",
            str(work / "out-evidence"),
            "--output-debs",
            str(work / "out-debs"),
            "--base-run-id",
            "111111",
            "--base-head-sha",
            "a" * 40,
            "--resume-run-id",
            "222222",
            "--resume-head-sha",
            "b" * 40,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if expected_success and result.returncode != 0:
        raise SystemExit(f"expected merger PASS, got rc={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    if not expected_success and result.returncode == 0:
        raise SystemExit("expected merger rejection but it returned success")
    return result


def main() -> int:
    CLOSURE.parent.mkdir(parents=True, exist_ok=True)
    original_closure = CLOSURE.read_bytes() if CLOSURE.exists() else None
    try:
        closure_rows = [
            [str(order), f"source-{order}", f"1.0-{order}", "test", "candidate"]
            for order in range(1, 102)
        ]
        write_tsv(
            CLOSURE,
            ["order", "source_package", "packaging_version", "candidate_family", "decision"],
            closure_rows,
        )

        with tempfile.TemporaryDirectory(prefix="ksq-tail-merge-") as tmp:
            work = Path(tmp)
            partial_evidence = work / "partial-evidence"
            partial_debs = work / "partial-debs"
            completion_evidence = work / "completion-evidence"
            completion_debs = work / "completion-debs"
            prior = work / "prior"
            prior.mkdir()
            build_deb(prior / "prior_1.0_amd64.deb", "prior", "1.0")

            fixture_rows(81, 98, partial_debs, partial_evidence)
            fixture_rows(99, 101, completion_debs, completion_evidence)

            # Reproduce the timed-out base shape: prepared evidence for order 99
            # exists, but it has no PASS build-status and is absent from the
            # partial manifest/binary index.
            interrupted = partial_evidence / "99-source-99"
            interrupted.mkdir()
            (interrupted / "prepared-source.env").write_text("AURORA_KSQ_1_SOURCE=source-99\n", encoding="utf-8")

            result = invoke(work, partial_evidence, partial_debs, completion_evidence, completion_debs, True)
            if "AURORA_KSQ_1_TAIL_MERGE_SUCCESS" not in result.stdout:
                raise SystemExit("successful merge did not emit success marker")

            out_evidence = work / "out-evidence"
            out_debs = work / "out-debs"
            merged_manifest = read_tsv(out_evidence / "build-manifest.tsv")
            if [int(row[0]) for row in merged_manifest[1:]] != list(range(81, 102)):
                raise SystemExit("canonical manifest is not exact order 81..101")
            if len(list(out_debs.glob("*.deb"))) != 21:
                raise SystemExit("canonical tail does not contain 21 synthetic DEBs")
            status = (out_evidence / "range-status.env").read_text(encoding="utf-8")
            if "AURORA_KSQ_1_RANGE_STATUS=PASS" not in status or "AURORA_KSQ_1_RANGE_SOURCES=21" not in status:
                raise SystemExit("canonical range status is incomplete")

            # Negative test: remove order 98 from the partial manifest. The
            # merger must reject a non-contiguous reusable prefix.
            bad = work / "bad-partial"
            shutil.copytree(partial_evidence, bad)
            rows = read_tsv(bad / "build-manifest.tsv")
            write_tsv(bad / "build-manifest.tsv", rows[0], rows[1:-1])
            invoke(work, bad, partial_debs, completion_evidence, completion_debs, False)

        print("AURORA_KSQ_1_TAIL_MERGER_TEST_PASS")
        return 0
    finally:
        if original_closure is None:
            CLOSURE.unlink(missing_ok=True)
        else:
            CLOSURE.write_bytes(original_closure)


def read_tsv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle, delimiter="\t"))


if __name__ == "__main__":
    raise SystemExit(main())
