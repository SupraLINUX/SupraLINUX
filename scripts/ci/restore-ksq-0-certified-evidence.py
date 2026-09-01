#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

SNAPSHOT = "20260829T022000Z"
KSQ0_ARTIFACT_ID = "9708738867"
KSQ0_ZIP_SHA256 = "5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50"
BUILD_ORDER_SHA256 = "9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88"
CLOSURE_STATUS_SHA256 = "f391d261aa4230ee77dc2534e40937de1d090fd4f5d0807665ac072669f1be05"


def fail(message: str) -> None:
    print(f"AURORA_KSQ_0_RESTORE_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_member(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(p.parts) and not p.is_absolute() and ".." not in p.parts


def verify_selected_source_hashes(root: Path) -> None:
    manifest = root / "build/ksq-0/source-audit/selected-source-files.sha256"
    downloads = root / "build/ksq-0/source-audit/downloads"
    if not manifest.is_file() or not downloads.is_dir():
        fail("restored source-audit evidence is incomplete")
    seen: set[str] = set()
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            fail(f"malformed selected-source hash row: {raw}")
        expected, original_path = parts
        name = Path(original_path.strip()).name
        if name in seen:
            fail(f"duplicate selected-source basename: {name}")
        seen.add(name)
        target = downloads / name
        if not target.is_file():
            fail(f"selected-source object missing after restore: {name}")
        actual = sha256(target)
        if actual != expected:
            fail(f"selected-source hash mismatch: {name}")
    if not seen:
        fail("selected-source hash manifest restored zero objects")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice-root", type=Path, default=Path(f"/opt/supralinux/archive/{SNAPSHOT}"))
    parser.add_argument("--workspace", type=Path, default=Path("/workspace"))
    args = parser.parse_args()

    slice_root = args.slice_root.resolve()
    workspace = args.workspace.resolve()
    artifact = slice_root / f"provenance/github-artifact-{KSQ0_ARTIFACT_ID}.zip"
    if not artifact.is_file():
        fail(f"embedded canonical artifact missing: {artifact}")
    if sha256(artifact) != KSQ0_ZIP_SHA256:
        fail("embedded canonical KSQ-0 ZIP digest mismatch")

    build_root = workspace / "build/ksq-0"
    canonical_root = build_root / "canonical"
    source_audit_root = build_root / "source-audit"
    shutil.rmtree(canonical_root, ignore_errors=True)
    shutil.rmtree(source_audit_root, ignore_errors=True)
    canonical_root.mkdir(parents=True, exist_ok=True)

    wanted_exact = {
        "build/ksq-0/build-order.tsv",
        "build/ksq-0/closure-status.env",
        "build/ksq-0/build-dependency-edges.tsv",
        "build/ksq-0/build-dep-overrides-applied.tsv",
        "build/ksq-0/root-source-owners.tsv",
        "build/ksq-0/selected-source-records.txt",
    }
    wanted_prefix = "build/ksq-0/source-audit/"

    with zipfile.ZipFile(artifact) as archive:
        for info in archive.infolist():
            if not safe_member(info.filename):
                fail(f"unsafe canonical artifact member: {info.filename}")
            if info.is_dir():
                continue
            if info.filename in wanted_exact:
                dest = canonical_root / Path(info.filename).name
            elif info.filename.startswith(wanted_prefix):
                rel = PurePosixPath(info.filename).relative_to(PurePosixPath(wanted_prefix))
                dest = source_audit_root / Path(*rel.parts)
            else:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)

    build_order = canonical_root / "build-order.tsv"
    closure = canonical_root / "closure-status.env"
    if not build_order.is_file() or sha256(build_order) != BUILD_ORDER_SHA256:
        fail("canonical build-order.tsv identity mismatch")
    if not closure.is_file() or sha256(closure) != CLOSURE_STATUS_SHA256:
        fail("canonical closure-status.env identity mismatch")

    closure_text = closure.read_text(encoding="utf-8")
    required = (
        "AURORA_KSQ_0_APT_SNAPSHOT=20260829T022000Z",
        "AURORA_KSQ_0_CLOSURE_STATUS=COMPLETE",
        "AURORA_KSQ_0_CLOSURE_SOURCES=101",
        "AURORA_KSQ_0_CLOSURE_UNRESOLVED=0",
        "AURORA_KSQ_0_CLOSURE_BUILD_ORDERED=101",
    )
    for line in required:
        if line not in closure_text.splitlines():
            fail(f"canonical closure invariant missing: {line}")

    verify_selected_source_hashes(workspace)

    print(f"AURORA_KSQ_0_RESTORE_ARTIFACT={KSQ0_ARTIFACT_ID}")
    print(f"AURORA_KSQ_0_RESTORE_BUILD_ORDER_SHA256={BUILD_ORDER_SHA256}")
    print("AURORA_KSQ_0_CERTIFIED_EVIDENCE_RESTORED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
