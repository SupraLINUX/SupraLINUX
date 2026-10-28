#!/usr/bin/env python3
"""Contract tests for exact SupraLINUX-proposed retained-artifact recovery."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import zipfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/restore-proposed-retained-artifacts.py"

spec = importlib.util.spec_from_file_location("proposed_recovery", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

source = SCRIPT.read_text()
for token in (
    'remove_header("Authorization")',
    'exc.code in {404, 410}',
    '"scripts/retain-package-artifacts.py"',
    '"--dag", str(dag_path)',
    'source_package != candidate.get("source_package")',
    '"sealed-host-package-export"',
    '"restored-sealed-host"',
    '"restored_from_sealed_host"',
    '"archive_index_sha256"',
    '"package_attempt_consumed": False',
    '"canonical_package_state_effect": "none"',
    '"stable_publication_authorized": False',
    '"BLOCKED"',
):
    if token not in source:
        raise SystemExit(f"missing proposed recovery contract: {token}")

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    persistent = base / "persistent"
    legacy = base / "legacy"
    persistent.mkdir()
    legacy.mkdir()

    archive_root = ".artifacts/plasma-6.7.5/example-attempt1"
    payload = b"exact-historical-artifact"
    digest = hashlib.sha256(payload).hexdigest()
    legacy_path = (
        legacy
        / "plasma-6.7.5"
        / "example-attempt1"
        / "sha256"
        / f"{digest}.zip"
    )
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes(payload)

    found = module.find_legacy_artifact([legacy], archive_root, digest)
    if found != legacy_path:
        raise SystemExit("exact legacy artifact was not found")

    target = module.artifact_target(persistent, archive_root, digest)
    module.atomic_install(found, target, digest)
    if module.sha256(target) != digest:
        raise SystemExit("atomic retained artifact installation changed bytes")

    module.atomic_install(found, target, digest)
    if module.sha256(target) != digest:
        raise SystemExit("idempotent retained artifact reuse changed bytes")

    wrong = base / "wrong.zip"
    wrong.write_bytes(b"wrong")
    try:
        module.atomic_install(wrong, target, hashlib.sha256(b"wrong").hexdigest())
    except SystemExit:
        pass
    else:
        raise SystemExit("conflicting retained artifact target was overwritten")

    for invalid in (
        "/absolute/archive",
        ".artifacts",
        ".artifacts/../escape",
    ):
        try:
            module.logical_parts(invalid)
        except SystemExit:
            pass
        else:
            raise SystemExit(f"unsafe logical archive root accepted: {invalid}")

    dag_path = base / "plasma-dag.json"
    module.write_plasma_identity_dag(
        dag_path,
        "example-node",
        {"source_package": "example-source"},
        {"source_package": "example-source"},
    )
    if module.json.loads(dag_path.read_text()) != {
        "schema": 1,
        "nodes": {"example-node": {"source_package": "example-source"}},
    }:
        raise SystemExit("synthetic Plasma identity DAG is not exact")

    try:
        module.write_plasma_identity_dag(
            dag_path,
            "example-node",
            {"source_package": "expected-source"},
            {"source_package": "wrong-source"},
        )
    except SystemExit:
        pass
    else:
        raise SystemExit("mismatched Plasma source identity was accepted")

    host_root = base / "host-evidence-root"
    host_dir = host_root / "sealed-run"
    payload_dir = (
        host_dir
        / "guest-files"
        / "workspace"
        / "evidence"
        / "authoritative-plasma-package"
    )
    payload_dir.mkdir(parents=True)
    package_file = payload_dir / "packages" / "example.deb"
    package_file.parent.mkdir()
    package_file.write_bytes(b"sealed-package-bytes")
    package_digest = module.sha256(package_file)
    result = {
        "node": "example-node",
        "version": "1.0-0supralinux1",
        "state": "PASS",
        "exit_code": 0,
        "source_commit": "1" * 40,
        "workflow_run_id": "123",
        "package_attempt_consumed": True,
        "files_sha256": {
            "packages/example.deb": package_digest,
        },
    }
    (payload_dir / "result.json").write_text(
        module.json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    seal_lines = []
    for sealed_file in sorted(
        path for path in host_dir.rglob("*")
        if path.is_file()
    ):
        seal_lines.append(
            f"{module.sha256(sealed_file)}  ./{sealed_file.relative_to(host_dir)}"
        )
    manifest = host_dir / "evidence-sha256.txt"
    manifest.write_text("\n".join(seal_lines) + "\n")

    reference_zip = base / "reference-sealed-export.zip"
    with zipfile.ZipFile(
        reference_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        strict_timestamps=False,
    ) as archive:
        for path in sorted(payload_dir.rglob("*")):
            if path.is_file():
                archive.write(path, str(path.relative_to(payload_dir)))
    reference_digest = module.sha256(reference_zip)
    rebuilt_zip = base / "rebuilt-sealed-export.zip"
    sealed_record = {
        "evidence": {
            "artifact_origin": "sealed-host-package-export",
            "actions_export_complete": False,
            "host_evidence_dir": str(host_dir),
            "host_evidence_manifest_sha256": module.sha256(manifest),
            "source_commit": "1" * 40,
            "workflow_run_id": 123,
        }
    }
    sealed_candidate = {
        "version": "1.0-0supralinux1",
        "artifact_sha256": reference_digest,
    }
    if module.rebuild_sealed_host_export(
        [host_root],
        "example-node",
        sealed_candidate,
        sealed_record,
        rebuilt_zip,
    ) != "restored":
        raise SystemExit("exact sealed host export was not rebuilt")
    if module.sha256(rebuilt_zip) != reference_digest:
        raise SystemExit("rebuilt sealed host export changed archive bytes")

    wrong_candidate = dict(sealed_candidate)
    wrong_candidate["artifact_sha256"] = "0" * 64
    if module.rebuild_sealed_host_export(
        [host_root],
        "example-node",
        wrong_candidate,
        sealed_record,
        rebuilt_zip,
    ) != "digest-mismatch":
        raise SystemExit("non-reproducible sealed host export was accepted")

    if hasattr(os, "symlink"):
        symlink_root = base / "symlink-root"
        real = base / "real-root"
        real.mkdir()
        symlink_root.symlink_to(real, target_is_directory=True)
        try:
            module.real_root(symlink_root)
        except SystemExit:
            pass
        else:
            raise SystemExit("symlink artifact root was accepted")

print("SupraLINUX-proposed retained artifact recovery contract: PASS")
