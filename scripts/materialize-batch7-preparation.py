#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import io
import lzma
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNK_DIR = ROOT / "tooling/batch7-payload"
EXPECTED = "14cbb49cb87a01b0f847ba7c2452d7a69ef81a5f47fedd3a350c3bf643e4c5e0"

chunks = sorted(CHUNK_DIR.glob("chunk-*.txt"))
if len(chunks) != 4:
    raise SystemExit(f"expected 4 payload chunks, got {len(chunks)}")
encoded = "".join(p.read_text().strip() for p in chunks)
blob = base64.b64decode(encoded, validate=True)
actual = hashlib.sha256(blob).hexdigest()
if actual != EXPECTED:
    raise SystemExit(f"payload SHA-256 mismatch: {actual} != {EXPECTED}")

raw = lzma.decompress(blob)
with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
    tf.extractall(ROOT, filter="data")

policy = ROOT / ".github/workflows/repository-policy.yml"
s = policy.read_text()
scope_anchor = (
    "      - name: Test KDE Tier 1 dependency preflight semantic scope\n"
    "        shell: bash\n"
    "        run: scripts/test-kde-tier1-dependency-preflight-scope.sh\n"
)
scope_block = scope_anchor + (
    "\n      - name: Test KDE Tier 1 Batch 7 package scope\n"
    "        shell: bash\n"
    "        run: scripts/test-kde-tier1-package-batch7-scope.sh\n"
)
if "Test KDE Tier 1 Batch 7 package scope" not in s:
    if scope_anchor not in s:
        raise SystemExit("Repository Policy scope anchor not found")
    s = s.replace(scope_anchor, scope_block, 1)

validator_anchor = (
    "      - name: Validate KDE Tier 1 batch 6 preparation\n"
    "        run: python3 scripts/validate_kde_tier1_package_batch6.py\n"
)
validator_block = validator_anchor + (
    "\n      - name: Validate KDE Tier 1 batch 7 preparation\n"
    "        run: python3 scripts/validate_kde_tier1_package_batch7.py\n"
)
if "Validate KDE Tier 1 batch 7 preparation" not in s:
    if validator_anchor not in s:
        raise SystemExit("Repository Policy Batch 6 anchor not found")
    s = s.replace(validator_anchor, validator_block, 1)
policy.write_text(s)

for path in (
    ROOT / "docs/status/2026-09-16-batch7-preparation-plan.md",
    ROOT / ".github/workflows/materialize-batch7-package-preparation.yml",
):
    if path.exists():
        path.unlink()

shutil.rmtree(CHUNK_DIR)
try:
    CHUNK_DIR.parent.rmdir()
except OSError:
    pass

self_path = Path(__file__).resolve()
self_path.unlink()
print(f"Batch 7 preparation payload materialized and tooling removed: sha256={actual}")
