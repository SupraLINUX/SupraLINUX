#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
dag = json.loads((ROOT / "manifests/kde-dag.json").read_text())
errors = []
items = []

if dag.get("frameworks_series") != "6.30.0":
    errors.append("unexpected Frameworks series")

for node_id, node in sorted(dag.get("nodes", {}).items()):
    if node.get("state") != "PASS":
        continue
    version = node.get("package_version")
    evidence = [
        item for item in node.get("evidence", [])
        if isinstance(item, dict) and item.get("result") == "PASS"
    ]
    exact = [
        item for item in evidence
        if item.get("attempted_package_version") in (None, version)
    ]
    chosen = (exact or evidence)[-1] if (exact or evidence) else None
    if not chosen:
        errors.append(f"{node_id}: missing retained PASS evidence")
        continue
    run_id = chosen.get("workflow_run") or chosen.get("run_id")
    artifact_id = chosen.get("artifact_id")
    digest = chosen.get("artifact_sha256")
    if not isinstance(run_id, int):
        errors.append(f"{node_id}: PASS evidence lacks workflow run")
    if not isinstance(artifact_id, int):
        errors.append(f"{node_id}: PASS evidence lacks artifact id")
    if not isinstance(digest, str) or len(digest) != 64:
        errors.append(f"{node_id}: PASS evidence lacks artifact SHA-256")
    if chosen.get("downstream_eligible") is False:
        errors.append(f"{node_id}: PASS artifact explicitly not downstream eligible")
    items.append({
        "node": node_id,
        "tier": node.get("tier"),
        "package_version": version,
        "workflow_run_id": run_id,
        "artifact_id": artifact_id,
        "artifact_sha256": digest,
        "commit": chosen.get("commit"),
    })

if len(items) != 65:
    errors.append(f"expected 65 current Frameworks PASS nodes, got {len(items)}")
if len({item["artifact_id"] for item in items if isinstance(item.get("artifact_id"), int)}) != len(items):
    errors.append("Frameworks milestone plan contains duplicate artifact ids")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

out = {
    "schema": 1,
    "kind": "frameworks-6.30-milestone-cache-plan",
    "frameworks_series": "6.30.0",
    "source_manifest": "manifests/kde-dag.json",
    "pass_node_count": len(items),
    "artifact_count": len(items),
    "items": items,
}
print(json.dumps(out, indent=2, sort_keys=True))
