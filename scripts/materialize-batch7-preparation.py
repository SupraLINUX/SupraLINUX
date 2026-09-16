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

# The canonical package DAG contains promoted PASS nodes only. Pending/in-flight
# Tier 1 nodes remain in the Tier 1 manifest/campaign and must be absent here.
validator = ROOT / "scripts/validate_kde_tier1_package_batch7.py"
vs = validator.read_text()
old_selected = '    req(dag.get(n,{}).get("state")=="pending",f"{n} DAG must remain pending")'
new_selected = '    req(n not in dag,f"{n} must stay absent from promoted package DAG before PASS")'
old_deferred = 'req(tier["kguiaddons"].get("state")=="pending" and dag.get("kguiaddons",{}).get("state")=="pending","KGuiAddons must remain deferred/pending")'
new_deferred = 'req(tier["kguiaddons"].get("state")=="pending" and "kguiaddons" not in dag,"KGuiAddons must remain pending and absent from promoted package DAG")'
if old_selected not in vs or old_deferred not in vs:
    raise SystemExit("Batch 7 validator DAG-semantics anchors not found")
vs = vs.replace(old_selected, new_selected, 1).replace(old_deferred, new_deferred, 1)
validator.write_text(vs)

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

marker = ROOT / "docs/status/2026-09-16-batch7-preparation-plan.md"
if marker.exists():
    marker.unlink()

# Keep the currently executing tooling workflow in the staging branch so the
# Actions token does not need workflows:write. It is removed later through the
# authorized GitHub connector after the validated non-workflow tree is pushed.
shutil.rmtree(CHUNK_DIR)
try:
    CHUNK_DIR.parent.rmdir()
except OSError:
    pass

self_path = Path(__file__).resolve()
self_path.unlink()
print(f"Batch 7 preparation payload materialized; staging workflow retained: sha256={actual}")
