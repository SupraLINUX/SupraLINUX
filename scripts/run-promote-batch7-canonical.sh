#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 <canonical-checkout>" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SCRIPT_DIR}/promote-batch7-canonical.py"
TMP="$(mktemp)"
trap 'rm -f "${TMP}"' EXIT
cp "${SOURCE}" "${TMP}"

python3 - "${TMP}" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()

# Correct the one-shot historical guard without changing canonical documentation.
old_guard = 'Batch 6 closure is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**'
new_guard = 'Canonical Tier 1 at the Batch 6 closure is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**'
if s.count(old_guard) != 1:
    raise SystemExit(f"expected exactly one historical-guard typo, found {s.count(old_guard)}")
s = s.replace(old_guard, new_guard, 1)

# The canonical DAG contains promoted nodes, not every Tier 1 pending node. Materialize
# Batch 7 nodes from their already-validated Tier 1 source metadata when absent.
old_dag = '''        node = dag["nodes"][node_id]\n        if node.get("state") != "pending":\n            die(f"{node_id}: DAG pre-promotion state drifted")\n        node.update({'''
new_dag = '''        node = dag["nodes"].get(node_id)\n        if node is None:\n            source_node = by_id[node_id]\n            node = {\n                "tier": 1,\n                "upstream_version": source_node["upstream_version"],\n                "source_url": source_node["source_url"],\n                "source_sha256": source_node["source_sha256"],\n                "source_evidence": tier["release_reference"],\n                "source_authority": "kde-upstream",\n                "depends_on": ["extra-cmake-modules"],\n            }\n            dag["nodes"][node_id] = node\n        elif node.get("state") != "pending":\n            die(f"{node_id}: DAG pre-promotion state drifted")\n        node.update({'''
if s.count(old_dag) != 1:
    raise SystemExit(f"expected exactly one DAG materialization target, found {s.count(old_dag)}")
s = s.replace(old_dag, new_dag, 1)

p.write_text(s)
PY

python3 "${TMP}" "$1"
