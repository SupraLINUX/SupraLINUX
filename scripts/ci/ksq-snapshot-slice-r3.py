#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import lzma
import os
import shutil
import stat
import sys
from pathlib import Path

UPSTREAM_SNAPSHOT = "20260829T022000Z"
BASE_SLICE_ID = "20260829T022000Z-r2"
SLICE_ID = "20260829T022000Z-r3"
STAGE_ID = f".staging-{SLICE_ID}"
BASE_URL = f"https://snapshot.ubuntu.com/ubuntu/{UPSTREAM_SNAPSHOT}"

BASE_RELEASE_ID = "381836501"
BASE_RELEASE_ASSET_ID = "542414026"
BASE_RELEASE_ASSET_SHA256 = "23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b"
BASE_RELEASE_ASSET_BYTES = "1054177280"
BASE_RELEASE_MANIFEST_ASSET_ID = "542414028"
BASE_RELEASE_MANIFEST_SHA256 = "6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481"
BASE_BINARY_OBJECTS = 1783
BASE_BINARY_BYTES = 785219274

BINARY_FIELDS = ["path", "size", "sha256", "package", "version", "architecture", "suite", "component"]
GAP_FIELDS = ["filename", "size", "sha256", "package", "version", "architecture", "witness_orders"]


def load_engine():
    path = Path(__file__).with_name("ksq-snapshot-slice.py")
    spec = importlib.util.spec_from_file_location("supralinux_ksq_snapshot_slice_r3_engine", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load slice engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


m = load_engine()


def fail(message: str) -> None:
    raise SystemExit(f"AURORA_KSQ_SNAPSHOT_R3_FAILURE: {message}")


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"required env file missing: {path}")
    return m.read_results_env(path)


def read_tsv_exact(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"required TSV missing: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames != fields:
            fail(f"unexpected TSV header in {path}: {reader.fieldnames!r}")
        return list(reader)


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_witness_analysis(analysis: Path) -> tuple[list[dict[str, str]], dict[str, str], dict[str, str]]:
    status = read_env(analysis / "result/status.env")
    expected = {
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_STATUS": "PROVEN",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SNAPSHOT": UPSTREAM_SNAPSHOT,
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_FIRST_ORDER": "66",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_LAST_ORDER": "101",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SOURCES": "36",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_LOGS": "36",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_R2_OBJECTS": str(BASE_BINARY_OBJECTS),
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_REMOTE_POLICY": "fixed-snapshot-only",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_SIGNED_METADATA": "apt-verified-snapshot-packages",
        "AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_MANUAL_PACKAGE_ADDITIONS": "0",
    }
    for key, value in expected.items():
        if status.get(key) != value:
            fail(f"witness analysis mismatch: {key} expected={value!r} got={status.get(key)!r}")

    acceptance = read_env(analysis / "acceptance.env")
    if acceptance.get("AURORA_KSQ_1_WITNESS_INDEPENDENT_ANALYSIS") != "PASS":
        fail("independent witness analysis is not PASS")
    for key, value in expected.items():
        if acceptance.get(key) != value:
            fail(f"witness acceptance mismatch: {key}")

    origin = read_env(analysis / "analysis-artifact.env")
    for key in (
        "AURORA_KSQ_1_WITNESS_ANALYSIS_RUN_ID",
        "AURORA_KSQ_1_WITNESS_ANALYSIS_HEAD_SHA",
        "AURORA_KSQ_1_WITNESS_ANALYSIS_ARTIFACT_ID",
        "AURORA_KSQ_1_WITNESS_ANALYSIS_ARTIFACT_DIGEST",
    ):
        if not origin.get(key):
            fail(f"witness artifact origin missing: {key}")

    gap = read_tsv_exact(analysis / "result/gap-objects.tsv", GAP_FIELDS)
    expected_count = int(status.get("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_GAP_OBJECTS", "-1"))
    expected_bytes = int(status.get("AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_GAP_BYTES", "-1"))
    if expected_count <= 0:
        fail("r3 requested but complete witness gap is empty")
    if len(gap) != expected_count or sum(int(row["size"]) for row in gap) != expected_bytes:
        fail("witness gap count/byte total mismatch")

    seen: set[str] = set()
    for row in gap:
        filename = row["filename"]
        if filename in seen:
            fail(f"duplicate witness gap filename: {filename}")
        seen.add(filename)
        if not filename.startswith("pool/") or not filename.endswith(".deb"):
            fail(f"invalid witness gap payload path: {filename}")
        digest = row["sha256"].lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            fail(f"invalid witness gap SHA256: {filename}")
        if row["architecture"] not in {"amd64", "all"}:
            fail(f"unexpected witness gap architecture: {filename}")
        if not row["witness_orders"]:
            fail(f"missing witness provenance for gap object: {filename}")
    return gap, status, origin


def validate_base_identity(base: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    if not base.is_dir() or base.name != BASE_SLICE_ID:
        fail(f"base r2 slice identity mismatch: {base}")
    if any(path.is_symlink() for path in [base, *base.rglob("*")]):
        fail("base r2 contains symlink")
    provenance = read_env(base / "provenance.env")
    expected = {
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS": "COMPLETE",
        "AURORA_KSQ_SNAPSHOT_SLICE_ID": BASE_SLICE_ID,
        "AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SNAPSHOT": UPSTREAM_SNAPSHOT,
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH": "amd64",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH_VARIANTS": "disabled",
        "AURORA_KSQ_SNAPSHOT_SLICE_INSTALL_RECOMMENDS": "default",
        "AURORA_KSQ_SNAPSHOT_SLICE_BINARY_OBJECTS": str(BASE_BINARY_OBJECTS),
        "AURORA_KSQ_SNAPSHOT_SLICE_BINARY_BYTES": str(BASE_BINARY_BYTES),
        "AURORA_KSQ_SNAPSHOT_SLICE_REMOTE_FALLBACK": "forbidden",
    }
    for key, value in expected.items():
        if provenance.get(key) != value:
            fail(f"base r2 provenance mismatch: {key} expected={value!r} got={provenance.get(key)!r}")
    rows = read_tsv_exact(base / "manifests/binary.tsv", BINARY_FIELDS)
    if len(rows) != BASE_BINARY_OBJECTS or sum(int(row["size"]) for row in rows) != BASE_BINARY_BYTES:
        fail("base r2 binary manifest count/byte total mismatch")
    return rows, provenance


def signed_package_index(base: Path) -> dict[tuple[str, str, str, str], dict[str, str]]:
    result: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for suite in m.RESOLUTE_SUITES:
        for component in m.COMPONENTS:
            index = base / "ubuntu/dists" / suite / component / "binary-amd64/Packages.xz"
            if not index.is_file():
                fail(f"signed Packages index missing from base r2: {index}")
            with lzma.open(index, "rt", encoding="utf-8", errors="strict") as f:
                records = m.parse_deb822_records(f.read())
            for record in records:
                required = ("Package", "Version", "Architecture", "Filename", "Size", "SHA256")
                if any(field not in record for field in required):
                    continue
                key = (record["Package"], record["Version"], record["Architecture"], record["Filename"])
                row = {
                    "package": record["Package"],
                    "version": record["Version"],
                    "architecture": record["Architecture"],
                    "filename": record["Filename"],
                    "size": record["Size"],
                    "sha256": record["SHA256"].lower(),
                    "suite": suite,
                    "component": component,
                }
                previous = result.get(key)
                if previous is not None:
                    if previous["size"] != row["size"] or previous["sha256"] != row["sha256"]:
                        fail(f"conflicting signed package identity for {key}")
                    continue
                result[key] = row
    if not result:
        fail("base r2 signed Packages corpus is empty")
    return result


def resolve_gap(base: Path, gap: list[dict[str, str]]) -> list[dict[str, str]]:
    signed = signed_package_index(base)
    resolved: list[dict[str, str]] = []
    for row in gap:
        key = (row["package"], row["version"], row["architecture"], row["filename"])
        record = signed.get(key)
        if record is None:
            fail(f"witness gap object absent from inherited signed metadata: {row['filename']}")
        if record["size"] != row["size"] or record["sha256"] != row["sha256"].lower():
            fail(f"witness gap identity differs from signed metadata: {row['filename']}")
        resolved.append(record)
    return resolved


def copy_tree_preserve_hardlinks(source: Path, dest: Path) -> None:
    if dest.exists():
        fail(f"staging directory already exists; refusing implicit reuse: {dest}")
    dest.mkdir(parents=True)
    seen: dict[tuple[int, int], Path] = {}
    for root, dirs, files in os.walk(source):
        src_root = Path(root)
        dst_root = dest / src_root.relative_to(source)
        dst_root.mkdir(parents=True, exist_ok=True)
        os.chmod(dst_root, 0o755)
        for name in dirs:
            src = src_root / name
            if src.is_symlink():
                fail(f"symlink forbidden while copying base r2: {src}")
            dst = dst_root / name
            dst.mkdir(exist_ok=True)
            os.chmod(dst, 0o755)
        for name in files:
            src = src_root / name
            if src.is_symlink():
                fail(f"symlink forbidden while copying base r2: {src}")
            st = src.stat()
            if not stat.S_ISREG(st.st_mode):
                fail(f"non-regular file forbidden in base r2: {src}")
            dst = dst_root / name
            inode = (st.st_dev, st.st_ino)
            previous = seen.get(inode)
            if previous is not None and st.st_nlink > 1:
                os.link(previous, dst)
            else:
                shutil.copy2(src, dst)
                if st.st_nlink > 1:
                    seen[inode] = dst
            os.chmod(dst, 0o644)


def write_local_sources(stage: Path, final: Path) -> None:
    text = f"""Types: deb deb-src
URIs: file:{final}/ubuntu
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no

Types: deb-src
URIs: file:{final}/ubuntu
Suites: stonking
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no
"""
    (stage / "aurora-local.sources").write_text(text, encoding="utf-8")


def preserve_provenance(stage: Path, analysis: Path, base: Path, origin: dict[str, str]) -> None:
    out = stage / "provenance/r3"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base / "provenance.env", out / "base-r2-provenance.env")
    shutil.copy2(base / "manifests/binary.tsv", out / "base-r2-binary.tsv")
    for rel in (
        "acceptance.env",
        "trigger.env",
        "analysis-artifact.env",
        "result/status.env",
        "result/gap-objects.tsv",
        "result/observed-objects.tsv",
        "historical-oracle-comparison.tsv",
        "snapshot-packages-amd64.txt.sha256",
        "apt-metadata.sha256",
        "r2-binary-objects.sha256",
    ):
        src = analysis / rel
        if src.is_file():
            shutil.copy2(src, out / rel.replace("/", "-"))
    (out / "base-release.env").write_text("\n".join([
        f"AURORA_KSQ_R3_BASE_SLICE_ID={BASE_SLICE_ID}",
        f"AURORA_KSQ_R3_BASE_RELEASE_ID={BASE_RELEASE_ID}",
        f"AURORA_KSQ_R3_BASE_RELEASE_ASSET_ID={BASE_RELEASE_ASSET_ID}",
        f"AURORA_KSQ_R3_BASE_RELEASE_ASSET_SHA256={BASE_RELEASE_ASSET_SHA256}",
        f"AURORA_KSQ_R3_BASE_RELEASE_ASSET_BYTES={BASE_RELEASE_ASSET_BYTES}",
        f"AURORA_KSQ_R3_BASE_RELEASE_MANIFEST_ASSET_ID={BASE_RELEASE_MANIFEST_ASSET_ID}",
        f"AURORA_KSQ_R3_BASE_RELEASE_MANIFEST_SHA256={BASE_RELEASE_MANIFEST_SHA256}",
        f"AURORA_KSQ_R3_WITNESS_ANALYSIS_RUN_ID={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_RUN_ID']}",
        f"AURORA_KSQ_R3_WITNESS_ANALYSIS_HEAD_SHA={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_HEAD_SHA']}",
        f"AURORA_KSQ_R3_WITNESS_ANALYSIS_ARTIFACT_ID={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_ARTIFACT_ID']}",
        f"AURORA_KSQ_R3_WITNESS_ANALYSIS_ARTIFACT_DIGEST={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_ARTIFACT_DIGEST']}",
        "",
    ]), encoding="utf-8")


def write_provenance(stage: Path, base: dict[str, str], witness: dict[str, str], origin: dict[str, str], gap_count: int, gap_bytes: int) -> None:
    binary_objects = BASE_BINARY_OBJECTS + gap_count
    binary_bytes = BASE_BINARY_BYTES + gap_bytes
    values = [
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS=COMPLETE",
        f"AURORA_KSQ_SNAPSHOT_SLICE_ID={SLICE_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SNAPSHOT={UPSTREAM_SNAPSHOT}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SNAPSHOT={UPSTREAM_SNAPSHOT}",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH=amd64",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH_VARIANTS=disabled",
        "AURORA_KSQ_SNAPSHOT_SLICE_GENERATOR_HOST=ubuntu-26.04",
        "AURORA_KSQ_SNAPSHOT_SLICE_INSTALL_RECOMMENDS=default",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BINARY_OBJECTS={binary_objects}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BINARY_BYTES={binary_bytes}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_OBJECTS={base['AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_OBJECTS']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_BYTES={base['AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_BYTES']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_OBJECTS={base['AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_OBJECTS']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_BYTES={base['AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_BYTES']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_OBJECTS={base['AURORA_KSQ_SNAPSHOT_SLICE_METADATA_OBJECTS']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BYTES={base['AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BYTES']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_HASH_POLICY={base['AURORA_KSQ_SNAPSHOT_SLICE_METADATA_HASH_POLICY']}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BY_HASH_ALGORITHMS={base['AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BY_HASH_ALGORITHMS']}",
        "AURORA_KSQ_SNAPSHOT_SLICE_REMOTE_FALLBACK=forbidden",
        "AURORA_KSQ_SNAPSHOT_SLICE_APT_SNAPSHOT_MODE=disabled-local-copy",
        f"AURORA_KSQ_SNAPSHOT_R3_BASE_SLICE_ID={BASE_SLICE_ID}",
        f"AURORA_KSQ_SNAPSHOT_R3_BASE_RELEASE_ASSET_SHA256={BASE_RELEASE_ASSET_SHA256}",
        f"AURORA_KSQ_SNAPSHOT_R3_BASE_BINARY_OBJECTS={BASE_BINARY_OBJECTS}",
        f"AURORA_KSQ_SNAPSHOT_R3_BASE_BINARY_BYTES={BASE_BINARY_BYTES}",
        f"AURORA_KSQ_SNAPSHOT_R3_GAP_OBJECTS={gap_count}",
        f"AURORA_KSQ_SNAPSHOT_R3_GAP_BYTES={gap_bytes}",
        "AURORA_KSQ_SNAPSHOT_R3_GAP_DERIVATION=per-build-context-witness-066-101",
        f"AURORA_KSQ_SNAPSHOT_R3_WITNESS_STATUS={witness['AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_STATUS']}",
        f"AURORA_KSQ_SNAPSHOT_R3_WITNESS_ANALYSIS_RUN_ID={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_RUN_ID']}",
        f"AURORA_KSQ_SNAPSHOT_R3_WITNESS_ANALYSIS_HEAD_SHA={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_HEAD_SHA']}",
        f"AURORA_KSQ_SNAPSHOT_R3_WITNESS_ANALYSIS_ARTIFACT_ID={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_ARTIFACT_ID']}",
        f"AURORA_KSQ_SNAPSHOT_R3_WITNESS_ANALYSIS_ARTIFACT_DIGEST={origin['AURORA_KSQ_1_WITNESS_ANALYSIS_ARTIFACT_DIGEST']}",
        "AURORA_KSQ_SNAPSHOT_R3_MANUAL_PACKAGE_ADDITIONS=0",
        "",
    ]
    (stage / "provenance.env").write_text("\n".join(values), encoding="utf-8")


def validate_inherited_objects(final: Path) -> set[str]:
    expected_pool: set[str] = set()
    for row in m.read_tsv(final / "manifests/ubuntu-source.tsv"):
        obj = final / row["path"]
        expected_pool.add(row["path"])
        if not obj.is_file() or obj.stat().st_size != int(row["size"]) or m.sha(obj, "sha512") != row["sha512"]:
            fail(f"Ubuntu source object validation failed: {row['path']}")
    for row in m.read_tsv(final / "manifests/debian-source.tsv"):
        obj = final / row["path"]
        if not obj.is_file() or obj.stat().st_size != int(row["size"]) or m.sha(obj) != row["sha256"]:
            fail(f"Debian source object validation failed: {row['path']}")

    metadata = m.read_tsv(final / "manifests/metadata.tsv")
    inrelease_maps: dict[str, tuple[str, str, dict[str, tuple[int, str]]]] = {}
    expected_metadata: set[str] = set()
    expected_by_hash: set[str] = set()
    for row in metadata:
        obj = final / row["path"]
        expected_metadata.add(row["path"])
        if not obj.is_file() or obj.stat().st_size != int(row["size"]) or m.sha(obj) != row["sha256"]:
            fail(f"metadata object validation failed: {row['path']}")
        if obj.name in {"Packages.xz", "Sources.xz"}:
            parts = Path(row["path"]).parts
            suite = parts[2]
            rel_index = "/".join(parts[3:])
            if suite not in inrelease_maps:
                inrelease_maps[suite] = m.inrelease_strongest_map(final / "ubuntu/dists" / suite / "InRelease")
            section, algorithm, signed_entries = inrelease_maps[suite]
            signed = signed_entries.get(rel_index)
            if signed is None:
                fail(f"metadata absent from strongest signed InRelease section: {suite}/{rel_index}")
            size, digest = signed
            if size != int(row["size"]) or row.get("signed_hash_algorithm") != section or row.get("signed_hash") != digest:
                fail(f"signed metadata identity mismatch: {row['path']}")
            if m.sha(obj, algorithm) != digest:
                fail(f"signed metadata digest mismatch: {row['path']}")
            by_hash = obj.parent / "by-hash" / section / digest
            expected_by_hash.add(by_hash.relative_to(final).as_posix())
            if not by_hash.is_file() or not os.path.samefile(obj, by_hash):
                fail(f"metadata by-hash hardlink mismatch: {by_hash}")
    actual_metadata = {p.relative_to(final).as_posix() for p in (final / "ubuntu/dists").rglob("*") if p.is_file()}
    if actual_metadata != expected_metadata | expected_by_hash:
        fail("metadata whitelist mismatch")
    for suite in list(m.RESOLUTE_SUITES) + ["stonking"]:
        m.verify_inrelease(final / "ubuntu/dists" / suite / "InRelease")
    return expected_pool


def validate_r3(final: Path, analysis: Path | None = None, *, check_read_only: bool = True) -> None:
    if not final.is_dir():
        fail(f"r3 slice missing: {final}")
    if any(path.is_symlink() for path in [final, *final.rglob("*")]):
        fail("r3 slice contains symlink")
    provenance = read_env(final / "provenance.env")
    required = {
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS": "COMPLETE",
        "AURORA_KSQ_SNAPSHOT_SLICE_ID": SLICE_ID,
        "AURORA_KSQ_SNAPSHOT_SLICE_SNAPSHOT": UPSTREAM_SNAPSHOT,
        "AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SNAPSHOT": UPSTREAM_SNAPSHOT,
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH": "amd64",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH_VARIANTS": "disabled",
        "AURORA_KSQ_SNAPSHOT_SLICE_INSTALL_RECOMMENDS": "default",
        "AURORA_KSQ_SNAPSHOT_SLICE_REMOTE_FALLBACK": "forbidden",
        "AURORA_KSQ_SNAPSHOT_R3_BASE_SLICE_ID": BASE_SLICE_ID,
        "AURORA_KSQ_SNAPSHOT_R3_BASE_RELEASE_ASSET_SHA256": BASE_RELEASE_ASSET_SHA256,
        "AURORA_KSQ_SNAPSHOT_R3_BASE_BINARY_OBJECTS": str(BASE_BINARY_OBJECTS),
        "AURORA_KSQ_SNAPSHOT_R3_BASE_BINARY_BYTES": str(BASE_BINARY_BYTES),
        "AURORA_KSQ_SNAPSHOT_R3_GAP_DERIVATION": "per-build-context-witness-066-101",
        "AURORA_KSQ_SNAPSHOT_R3_WITNESS_STATUS": "PROVEN",
        "AURORA_KSQ_SNAPSHOT_R3_MANUAL_PACKAGE_ADDITIONS": "0",
    }
    for key, value in required.items():
        if provenance.get(key) != value:
            fail(f"r3 provenance mismatch: {key} expected={value!r} got={provenance.get(key)!r}")

    gap = read_tsv_exact(final / "manifests/r3-gap.tsv", GAP_FIELDS)
    gap_count = int(provenance["AURORA_KSQ_SNAPSHOT_R3_GAP_OBJECTS"])
    gap_bytes = int(provenance["AURORA_KSQ_SNAPSHOT_R3_GAP_BYTES"])
    if gap_count <= 0 or len(gap) != gap_count or sum(int(row["size"]) for row in gap) != gap_bytes:
        fail("r3 gap manifest count/byte total mismatch")

    binary = read_tsv_exact(final / "manifests/binary.tsv", BINARY_FIELDS)
    expected_count = BASE_BINARY_OBJECTS + gap_count
    expected_bytes = BASE_BINARY_BYTES + gap_bytes
    if len(binary) != expected_count or sum(int(row["size"]) for row in binary) != expected_bytes:
        fail("r3 binary manifest count/byte total mismatch")
    if provenance.get("AURORA_KSQ_SNAPSHOT_SLICE_BINARY_OBJECTS") != str(expected_count):
        fail("r3 provenance binary object count mismatch")
    if provenance.get("AURORA_KSQ_SNAPSHOT_SLICE_BINARY_BYTES") != str(expected_bytes):
        fail("r3 provenance binary byte total mismatch")

    expected_pool: set[str] = set()
    seen: set[str] = set()
    manifest_map: dict[str, dict[str, str]] = {}
    for row in binary:
        if row["path"] in seen:
            fail(f"duplicate r3 binary manifest path: {row['path']}")
        seen.add(row["path"])
        manifest_map[row["path"]] = row
        expected_pool.add(row["path"])
        obj = final / row["path"]
        if not obj.is_file() or obj.stat().st_size != int(row["size"]) or m.sha(obj) != row["sha256"]:
            fail(f"r3 binary object validation failed: {row['path']}")

    expected_pool |= validate_inherited_objects(final)
    actual_pool = {p.relative_to(final).as_posix() for p in (final / "ubuntu/pool").rglob("*") if p.is_file()}
    if actual_pool != expected_pool:
        extra = sorted(actual_pool - expected_pool)[:10]
        missing = sorted(expected_pool - actual_pool)[:10]
        fail(f"r3 pool whitelist mismatch; extra={extra} missing={missing}")

    sources = (final / "aurora-local.sources").read_text(encoding="utf-8")
    apt_root = final.parent / SLICE_ID if final.name == STAGE_ID else final
    expected_uri = f"URIs: file:{apt_root}/ubuntu"
    if sources.count(expected_uri) != 2 or "Snapshot: no" not in sources or "http://" in sources or "https://" in sources:
        fail("r3 local APT source is not strictly local/fail-closed")

    resolved = resolve_gap(final, gap)
    for record in resolved:
        path = f"ubuntu/{record['filename']}"
        row = manifest_map.get(path)
        if row is None or row["size"] != record["size"] or row["sha256"] != record["sha256"]:
            fail(f"r3 gap object differs from inherited signed metadata: {path}")

    if analysis is not None:
        source_gap, _, source_origin = validate_witness_analysis(analysis)
        if source_gap != gap:
            fail("embedded r3 gap differs from supplied independent witness analysis")
        if provenance.get("AURORA_KSQ_SNAPSHOT_R3_WITNESS_ANALYSIS_RUN_ID") != source_origin["AURORA_KSQ_1_WITNESS_ANALYSIS_RUN_ID"]:
            fail("r3 witness analysis run identity mismatch")

    if check_read_only:
        writable = [path for path in [final, *final.rglob("*")] if path.exists() and (path.stat().st_mode & 0o222)]
        if writable:
            fail(f"r3 slice contains writable path: {writable[0]}")
    print("AURORA_KSQ_SNAPSHOT_R3_VALID")


def materialize(args: argparse.Namespace) -> None:
    root = args.archive_root.resolve()
    base = args.base_slice_root.resolve()
    analysis = args.witness_analysis_dir.resolve()
    final = root / SLICE_ID
    stage = root / STAGE_ID
    if final.exists():
        validate_r3(final, analysis)
        print("AURORA_KSQ_SNAPSHOT_R3_ALREADY_COMPLETE")
        return

    base_rows, base_provenance = validate_base_identity(base)
    gap, witness_status, origin = validate_witness_analysis(analysis)
    resolved_gap = resolve_gap(base, gap)
    base_paths = {row["path"] for row in base_rows}
    for record in resolved_gap:
        if f"ubuntu/{record['filename']}" in base_paths:
            fail(f"witness gap object already exists in base r2 manifest: {record['filename']}")

    root.mkdir(parents=True, exist_ok=True)
    copy_tree_preserve_hardlinks(base, stage)
    (stage / "COMPLETE").unlink(missing_ok=True)
    preserve_provenance(stage, analysis, base, origin)

    jobs: list[tuple[str, Path, int, str, str]] = []
    added: list[dict[str, str]] = []
    for record in resolved_gap:
        rel = record["filename"]
        jobs.append((f"{BASE_URL}/{rel}", stage / "ubuntu" / rel, int(record["size"]), record["sha256"], "sha256"))
        added.append({
            "path": f"ubuntu/{rel}",
            "size": record["size"],
            "sha256": record["sha256"],
            "package": record["package"],
            "version": record["version"],
            "architecture": record["architecture"],
            "suite": record["suite"],
            "component": record["component"],
        })
    m.download_many(jobs, args.workers)

    write_tsv(stage / "manifests/binary.tsv", BINARY_FIELDS, sorted([*base_rows, *added], key=lambda row: row["path"]))
    write_tsv(stage / "manifests/r3-gap.tsv", GAP_FIELDS, gap)
    write_tsv(stage / "manifests/r3-added-binary.tsv", BINARY_FIELDS, sorted(added, key=lambda row: row["path"]))
    write_local_sources(stage, final)
    write_provenance(stage, base_provenance, witness_status, origin, len(gap), sum(int(row["size"]) for row in gap))
    (stage / "COMPLETE").write_text("AURORA_KSQ_SNAPSHOT_R3_COMPLETE\n", encoding="utf-8")

    validate_r3(stage, analysis, check_read_only=False)
    m.harden_read_only(stage)
    os.replace(stage, final)
    validate_r3(final, analysis)
    print(f"AURORA_KSQ_SNAPSHOT_R3_PATH={final}")
    print("AURORA_KSQ_SNAPSHOT_R3_MATERIALIZED")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    materialize_parser = sub.add_parser("materialize")
    materialize_parser.add_argument("--archive-root", type=Path, required=True)
    materialize_parser.add_argument("--base-slice-root", type=Path, required=True)
    materialize_parser.add_argument("--witness-analysis-dir", type=Path, required=True)
    materialize_parser.add_argument("--workers", type=int, default=6)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--slice-root", type=Path, required=True)
    validate_parser.add_argument("--witness-analysis-dir", type=Path)
    args = parser.parse_args()
    if args.command == "materialize":
        materialize(args)
    else:
        validate_r3(args.slice_root.resolve(), args.witness_analysis_dir.resolve() if args.witness_analysis_dir else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
