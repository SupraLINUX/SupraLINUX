#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path
from typing import NoReturn

SNAPSHOT = "20260829T022000Z"
EXTENSION_ID = "20260829T022000Z-kwallet-runtime-r1"
EXPECTED_ACQUISITIONS = 375
EXPECTED_MISSING = {
    ("lsb-base", "11.6build1", "all", "pool/main/l/lsb/lsb-base_11.6build1_all.deb"),
    ("libwrap0", "7.6.q-36build2", "amd64", "pool/main/t/tcp-wrappers/libwrap0_7.6.q-36build2_amd64.deb"),
    ("socat", "1.8.1.1-1ubuntu0.1", "amd64", "pool/main/s/socat/socat_1.8.1.1-1ubuntu0.1_amd64.deb"),
}

ACQUIRE_RE = re.compile(r"^(Get|Err|Ign):(\d+)\s+(.+)$")
ERR_RE = re.compile(
    r"^file:\S+\s+(?P<suite>\S+)\s+(?P<index_arch>\S+)\s+"
    r"(?P<package>\S+)\s+(?P<package_arch>\S+)\s+(?P<version>\S+)$"
)
PATH_VERSION_RE = re.compile(r"^(?P<prefix>.+)_(?P<version>[^_]+)_(?P<arch>[^_]+)\.deb$")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_FAILURE: {message}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_r2_objects(path: Path) -> set[str]:
    objects: set[str] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        fields = raw.split("\t")
        if len(fields) != 2 or not fields[1].isdigit():
            fail(f"invalid r2 object row at line {line_no}: {raw!r}")
        if fields[0] in objects:
            fail(f"duplicate r2 object path: {fields[0]}")
        objects.add(fields[0])
    if len(objects) != 1783:
        fail(f"expected 1783 r2 binary objects, got {len(objects)}")
    return objects


def infer_pool_path(package: str, version: str, arch: str, error_detail: str) -> str:
    marker = "File not found - "
    if marker not in error_detail:
        fail(f"missing file path detail for {package}")
    absolute = error_detail.split(marker, 1)[1].split(" (", 1)[0]
    needle = "/ubuntu/"
    if needle not in absolute:
        fail(f"unexpected missing object path for {package}: {absolute}")
    pool_path = absolute.split(needle, 1)[1]
    basename = Path(pool_path).name
    m = PATH_VERSION_RE.match(basename)
    if not m or m.group("version") != version or m.group("arch") != arch:
        fail(f"missing object filename does not match {package}={version}:{arch}: {basename}")
    return pool_path


def analyze(args: argparse.Namespace) -> None:
    solver_log = Path(args.solver_log)
    r2_objects_path = Path(args.r2_binary_objects)
    out = Path(args.out_dir)
    if not solver_log.is_file() or not r2_objects_path.is_file():
        fail("analysis inputs missing")
    out.mkdir(parents=True, exist_ok=True)

    lines = solver_log.read_text(encoding="utf-8", errors="replace").splitlines()
    by_index: dict[int, list[tuple[str, str, str | None]]] = {}
    for pos, line in enumerate(lines):
        m = ACQUIRE_RE.match(line)
        if not m:
            continue
        kind, index_text, rest = m.groups()
        index = int(index_text)
        detail = None
        if kind == "Err" and pos + 1 < len(lines) and lines[pos + 1].startswith("  "):
            detail = lines[pos + 1].strip()
        by_index.setdefault(index, []).append((kind, rest, detail))

    expected_indices = set(range(1, EXPECTED_ACQUISITIONS + 1))
    actual_indices = set(by_index)
    if actual_indices != expected_indices:
        missing = sorted(expected_indices - actual_indices)
        extra = sorted(actual_indices - expected_indices)
        fail(f"acquisition index coverage mismatch missing={missing} extra={extra}")

    final_get = 0
    final_err: list[tuple[str, str, str, str, str, str]] = []
    for index in range(1, EXPECTED_ACQUISITIONS + 1):
        records = by_index[index]
        if any(kind == "Err" for kind, _, _ in records):
            err_records = [(rest, detail) for kind, rest, detail in records if kind == "Err"]
            if len(err_records) != 1:
                fail(f"acquisition {index} has {len(err_records)} Err records")
            rest, detail = err_records[0]
            m = ERR_RE.match(rest)
            if not m or detail is None:
                fail(f"cannot parse Err acquisition {index}: {rest}")
            package = m.group("package")
            version = m.group("version")
            package_arch = m.group("package_arch")
            pool_path = infer_pool_path(package, version, package_arch, detail)
            final_err.append((package, version, package_arch, pool_path, m.group("suite"), str(index)))
        elif any(kind == "Get" for kind, _, _ in records):
            final_get += 1
        else:
            fail(f"acquisition {index} ended without Get or Err")

    if final_get != EXPECTED_ACQUISITIONS - len(EXPECTED_MISSING):
        fail(f"expected 372 successful acquisitions, got {final_get}")
    actual_missing = {(p, v, a, path) for p, v, a, path, _, _ in final_err}
    if actual_missing != EXPECTED_MISSING:
        fail(f"runtime gap mismatch: {sorted(actual_missing)!r}")

    r2_objects = parse_r2_objects(r2_objects_path)
    for package, version, arch, pool_path, _, _ in final_err:
        if pool_path in r2_objects:
            fail(f"reported missing object is present in r2 manifest: {pool_path}")

    gap_tsv = out / "runtime-gap.tsv"
    with gap_tsv.open("w", encoding="utf-8") as f:
        f.write("package\tversion\tarchitecture\tpool_path\tsuite\tacquisition_index\tr2_present\n")
        for row in sorted(final_err):
            package, version, arch, pool_path, suite, index = row
            f.write(f"{package}\t{version}\t{arch}\t{pool_path}\t{suite}\t{index}\tno\n")

    status = out / "gap-status.env"
    status.write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_KWALLET_RUNTIME_GAP_STATUS=PROVEN",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_GAP_SNAPSHOT={SNAPSHOT}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID={EXTENSION_ID}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS={EXPECTED_ACQUISITIONS}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS_PRESENT={final_get}",
                f"AURORA_KSQ_1_KWALLET_RUNTIME_ACQUISITIONS_MISSING={len(final_err)}",
                "AURORA_KSQ_1_KWALLET_RUNTIME_R2_BINARY_OBJECTS=1783",
                "AURORA_KSQ_1_KWALLET_RUNTIME_GAP_PACKAGES=lsb-base,libwrap0,socat",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(status.read_text(encoding="utf-8"), end="")
    print("AURORA_KSQ_1_KWALLET_RUNTIME_GAP_ANALYSIS_SUCCESS")


def dpkg_field(deb: Path, field: str) -> str:
    cp = subprocess.run(
        ["dpkg-deb", "-f", str(deb), field],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cp.stdout.strip()


def validate(args: argparse.Namespace) -> None:
    root = Path(args.root)
    packages_dir = root / "packages"
    gap_tsv = root / "runtime-gap.tsv"
    status = root / "gap-status.env"
    sha_manifest = root / "packages.sha256"
    provenance = root / "provenance.env"
    for path in (packages_dir, gap_tsv, status, sha_manifest, provenance):
        if not path.exists():
            fail(f"extension member missing: {path.name}")

    debs = sorted(packages_dir.glob("*.deb"))
    if len(debs) != 3:
        fail(f"expected exactly 3 extension DEBs, got {len(debs)}")

    actual: set[tuple[str, str, str]] = set()
    for deb in debs:
        package = dpkg_field(deb, "Package")
        version = dpkg_field(deb, "Version")
        arch = dpkg_field(deb, "Architecture")
        actual.add((package, version, arch))
    expected = {(p, v, a) for p, v, a, _ in EXPECTED_MISSING}
    if actual != expected:
        fail(f"extension package identities mismatch: {sorted(actual)!r}")

    expected_hashes: dict[str, str] = {}
    for line_no, raw in enumerate(sha_manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        fields = raw.split(None, 1)
        if len(fields) != 2:
            fail(f"invalid packages.sha256 row {line_no}")
        digest, rel = fields
        rel = rel.lstrip("* ")
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            fail(f"unsafe hash manifest path: {rel}")
        expected_hashes[rel] = digest
    if set(expected_hashes) != {f"packages/{d.name}" for d in debs}:
        fail("packages.sha256 membership mismatch")
    for rel, digest in expected_hashes.items():
        if sha256_file(root / rel) != digest:
            fail(f"SHA-256 mismatch for {rel}")

    provenance_text = provenance.read_text(encoding="utf-8")
    required = {
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STATUS=IMMUTABLE",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID={EXTENSION_ID}",
        f"AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT={SNAPSHOT}",
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES=3",
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ARCH=amd64+all",
        "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_SOURCE=ubuntu-snapshot-service",
    }
    lines = set(provenance_text.splitlines())
    missing_required = sorted(required - lines)
    if missing_required:
        fail(f"provenance contract missing: {missing_required}")

    print("AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_VALID")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--solver-log", required=True)
    p.add_argument("--r2-binary-objects", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=analyze)
    p = sub.add_parser("validate")
    p.add_argument("--root", required=True)
    p.set_defaults(func=validate)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
