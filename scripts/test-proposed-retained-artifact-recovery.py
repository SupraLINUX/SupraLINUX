#!/usr/bin/env python3
"""Contract tests for exact SupraLINUX-proposed retained-artifact recovery."""
from __future__ import annotations

import hashlib
import importlib.util
import os
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
