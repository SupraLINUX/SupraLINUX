#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
import shutil
from pathlib import Path

UPSTREAM_SNAPSHOT = "20260829T022000Z"
SLICE_ID = "20260829T022000Z-r2"
SIZE_ARTIFACT_ID = "9883249125"
SIZE_ARTIFACT_DIGEST = "2281ab4655dc8d33639d9a3bbfb75d60325829a6b0af19902c20e4406e0c945b"
KSQ0_ARTIFACT_ID = "9708738867"
KSQ0_ARTIFACT_DIGEST = "5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50"
RECOMMENDS_AB_RUN_ID = "33729123389"
RECOMMENDS_AB_ARTIFACT_ID = "9883165109"
RECOMMENDS_AB_ARTIFACT_DIGEST = "0b617d25f575efead1dbe904eb24cc1b31df94a3f07ce32a7dbd25fc1327c20d"
EXPECTED_BINARY_OBJECTS = 1783
EXPECTED_BINARY_BYTES = 785219274
EXPECTED_RAW_UPPER_BOUND = 1303273303


def load_engine():
    path = Path(__file__).with_name("ksq-snapshot-slice.py")
    spec = importlib.util.spec_from_file_location("supralinux_ksq_snapshot_slice_engine", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load materialization engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


m = load_engine()

# Keep the certified Ubuntu archive point immutable while giving the corrected
# Supra local slice its own immutable identity.
m.SNAPSHOT = UPSTREAM_SNAPSHOT
m.BASE_URL = f"https://snapshot.ubuntu.com/ubuntu/{UPSTREAM_SNAPSHOT}"
m.FINAL_BASENAME = SLICE_ID
m.STAGE_BASENAME = f".staging-{SLICE_ID}"
m.SIZE_ARTIFACT_ID = SIZE_ARTIFACT_ID
m.SIZE_ARTIFACT_DIGEST = SIZE_ARTIFACT_DIGEST
m.KSQ0_ARTIFACT_ID = KSQ0_ARTIFACT_ID
m.KSQ0_ARTIFACT_DIGEST = KSQ0_ARTIFACT_DIGEST
m.EXPECTED_BINARY_OBJECTS = EXPECTED_BINARY_OBJECTS
m.EXPECTED_BINARY_BYTES = EXPECTED_BINARY_BYTES
m.EXPECTED_RAW_UPPER_BOUND = EXPECTED_RAW_UPPER_BOUND


def validate_canonical_evidence(size_dir: Path, ksq0_dir: Path, size_zip: Path, ksq0_zip: Path) -> None:
    if m.sha(size_zip) != SIZE_ARTIFACT_DIGEST:
        m.fail("native closure artifact ZIP digest mismatch")
    if m.sha(ksq0_zip) != KSQ0_ARTIFACT_DIGEST:
        m.fail("KSQ-0 closure artifact ZIP digest mismatch")

    results = m.read_results_env(size_dir / "results.env")
    expected = {
        "AURORA_KSQ_SLICE_STATUS": "MEASURED_METADATA_ONLY",
        "AURORA_KSQ_SLICE_UBUNTU_SNAPSHOT": UPSTREAM_SNAPSHOT,
        "AURORA_KSQ_SLICE_ARCH": "amd64",
        "AURORA_KSQ_SLICE_ARCH_VARIANTS": "disabled",
        "AURORA_KSQ_SLICE_INSTALL_RECOMMENDS": "default",
        "AURORA_KSQ_SLICE_CERTIFIED_BINARY_SEEDS": str(m.EXPECTED_CERTIFIED_SEEDS),
        "AURORA_KSQ_SLICE_BINARY_OBJECTS": str(EXPECTED_BINARY_OBJECTS),
        "AURORA_KSQ_SLICE_BINARY_BYTES": str(EXPECTED_BINARY_BYTES),
        "AURORA_KSQ_SLICE_UBUNTU_SOURCE_OBJECTS": str(m.EXPECTED_UBUNTU_SOURCE_OBJECTS),
        "AURORA_KSQ_SLICE_UBUNTU_SOURCE_BYTES": str(m.EXPECTED_UBUNTU_SOURCE_BYTES),
        "AURORA_KSQ_SLICE_DEBIAN_SOURCE_OBJECTS": str(m.EXPECTED_DEBIAN_SOURCE_OBJECTS),
        "AURORA_KSQ_SLICE_DEBIAN_SOURCE_BYTES": str(m.EXPECTED_DEBIAN_SOURCE_BYTES),
        "AURORA_KSQ_SLICE_RAW_UPPER_BOUND_BYTES": str(EXPECTED_RAW_UPPER_BOUND),
        "AURORA_KSQ_SLICE_PAYLOADS_DOWNLOADED": "0",
    }
    for key, value in expected.items():
        if results.get(key) != value:
            m.fail(f"native closure evidence mismatch: {key} expected={value} got={results.get(key)!r}")

    generator = m.read_results_env(size_dir / "generator.env")
    generator_expected = {
        "AURORA_KSQ_SLICE_GENERATOR_HOST": "ubuntu-26.04",
        "AURORA_KSQ_SLICE_GENERATOR_ARCH": "amd64",
        "AURORA_KSQ_SLICE_GENERATOR_ARCH_VARIANTS": "disabled",
        "AURORA_KSQ_SLICE_GENERATOR_INSTALL_RECOMMENDS": "default",
    }
    for key, value in generator_expected.items():
        if generator.get(key) != value:
            m.fail(f"native generator provenance mismatch: {key}")

    apt_policy = (size_dir / "apt-policy.txt").read_text(encoding="utf-8")
    for required in (
        'APT::Architecture "amd64";',
        'APT::Architecture-Variants "";',
        'APT::Install-Recommends "1";',
    ):
        if required not in apt_policy:
            m.fail(f"APT policy evidence missing: {required}")

    binary_objects = size_dir / "binary-objects.tsv"
    if not binary_objects.is_file():
        m.fail("native binary object manifest missing")
    text = binary_objects.read_text(encoding="utf-8")
    if "_amd64v3.deb\t" in text:
        m.fail("architecture variant leaked into generic-amd64 closure")
    if "pool/main/d/dbus/dbus-user-session_1.16.2-2ubuntu4_amd64.deb\t" not in text:
        m.fail("default-Recommends closure is missing dbus-user-session")

    canonical = m.read_results_env(size_dir / "canonical-artifacts.txt")
    canonical_expected = {
        "KSQ0_ARTIFACT_ID": KSQ0_ARTIFACT_ID,
        "KSQ0_ARTIFACT_SHA256": KSQ0_ARTIFACT_DIGEST,
        "RECOMMENDS_AB_RUN_ID": RECOMMENDS_AB_RUN_ID,
        "RECOMMENDS_AB_ARTIFACT_ID": RECOMMENDS_AB_ARTIFACT_ID,
        "RECOMMENDS_AB_ARTIFACT_SHA256": RECOMMENDS_AB_ARTIFACT_DIGEST,
    }
    for key, value in canonical_expected.items():
        if canonical.get(key) != value:
            m.fail(f"causal A/B provenance mismatch: {key}")

    closure = m.read_results_env(ksq0_dir / "build/ksq-0/closure-status.env")
    if closure.get("AURORA_KSQ_0_APT_SNAPSHOT") != UPSTREAM_SNAPSHOT or closure.get("AURORA_KSQ_0_CLOSURE_STATUS") != "COMPLETE":
        m.fail("KSQ-0 closure evidence is not COMPLETE for certified Ubuntu snapshot")


m.validate_canonical_evidence = validate_canonical_evidence


def copy_provenance(stage: Path, size_zip: Path, ksq0_zip: Path, size_dir: Path, ksq0_dir: Path) -> None:
    out = stage / "provenance"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(size_zip, out / f"github-artifact-{SIZE_ARTIFACT_ID}.zip")
    shutil.copy2(ksq0_zip, out / f"github-artifact-{KSQ0_ARTIFACT_ID}.zip")
    for src, name in [
        (size_dir / "results.env", "native-closure-results.env"),
        (size_dir / "generator.env", "native-closure-generator.env"),
        (size_dir / "apt-policy.txt", "native-closure-apt-policy.txt"),
        (size_dir / "binary-objects.tsv", "native-closure-binary-objects.tsv"),
        (size_dir / "certified-binary-seeds.tsv", "certified-binary-seeds.tsv"),
        (size_dir / "canonical-artifacts.txt", "canonical-artifacts.txt"),
        (ksq0_dir / "build/ksq-0/closure-status.env", "ksq0-closure-status.env"),
        (ksq0_dir / "build/ksq-0/selected-source-records.txt", "selected-source-records.txt"),
        (ksq0_dir / "build/ksq-0/apt-metadata.sha256", "ksq0-apt-metadata.sha256"),
        (ksq0_dir / "build/ksq-0/source-audit/wayland-protocols-1.48.sha256", "wayland-protocols-1.48.sha256"),
    ]:
        if not src.is_file():
            m.fail(f"required provenance file missing: {src}")
        shutil.copy2(src, out / name)


m.copy_provenance = copy_provenance


def write_provenance_env(stage: Path, binary_rows, source_rows, debian_rows, metadata_rows) -> None:
    hash_algorithms = sorted({r["signed_hash_algorithm"] for r in metadata_rows if r.get("signed_hash_algorithm")})
    content = "\n".join([
        "AURORA_KSQ_SNAPSHOT_SLICE_STATUS=COMPLETE",
        f"AURORA_KSQ_SNAPSHOT_SLICE_ID={SLICE_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SNAPSHOT={UPSTREAM_SNAPSHOT}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SNAPSHOT={UPSTREAM_SNAPSHOT}",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH=amd64",
        "AURORA_KSQ_SNAPSHOT_SLICE_ARCH_VARIANTS=disabled",
        "AURORA_KSQ_SNAPSHOT_SLICE_GENERATOR_HOST=ubuntu-26.04",
        "AURORA_KSQ_SNAPSHOT_SLICE_INSTALL_RECOMMENDS=default",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SIZE_ARTIFACT_ID={SIZE_ARTIFACT_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_SIZE_ARTIFACT_SHA256={SIZE_ARTIFACT_DIGEST}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_RECOMMENDS_AB_RUN_ID={RECOMMENDS_AB_RUN_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_RECOMMENDS_AB_ARTIFACT_ID={RECOMMENDS_AB_ARTIFACT_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_RECOMMENDS_AB_ARTIFACT_SHA256={RECOMMENDS_AB_ARTIFACT_DIGEST}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_KSQ0_ARTIFACT_ID={KSQ0_ARTIFACT_ID}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_KSQ0_ARTIFACT_SHA256={KSQ0_ARTIFACT_DIGEST}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BINARY_OBJECTS={len(binary_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_BINARY_BYTES={sum(int(r['size']) for r in binary_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_OBJECTS={len(source_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_UBUNTU_SOURCE_BYTES={sum(int(r['size']) for r in source_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_OBJECTS={len(debian_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_DEBIAN_SOURCE_BYTES={sum(int(r['size']) for r in debian_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_OBJECTS={len(metadata_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BYTES={sum(int(r['size']) for r in metadata_rows)}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_HASH_POLICY={m.METADATA_HASH_POLICY}",
        f"AURORA_KSQ_SNAPSHOT_SLICE_METADATA_BY_HASH_ALGORITHMS={','.join(hash_algorithms)}",
        "AURORA_KSQ_SNAPSHOT_SLICE_REMOTE_FALLBACK=forbidden",
        "AURORA_KSQ_SNAPSHOT_SLICE_APT_SNAPSHOT_MODE=disabled-local-copy",
        "",
    ])
    (stage / "provenance.env").write_text(content, encoding="utf-8")


m.write_provenance_env = write_provenance_env


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_mat = sub.add_parser("materialize")
    p_mat.add_argument("--archive-root", type=Path, default=Path("/srv/supralinux/archive"))
    p_mat.add_argument("--size-artifact-dir", type=Path, required=True)
    p_mat.add_argument("--ksq0-artifact-dir", type=Path, required=True)
    p_mat.add_argument("--size-artifact-zip", type=Path, required=True)
    p_mat.add_argument("--ksq0-artifact-zip", type=Path, required=True)
    p_mat.add_argument("--workers", type=int, default=6)
    p_val = sub.add_parser("validate")
    p_val.add_argument("--slice-root", type=Path, default=Path(f"/srv/supralinux/archive/{SLICE_ID}"))
    args = parser.parse_args()
    if args.command == "materialize":
        m.materialize(args)
    else:
        m.validate_slice(args.slice_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
