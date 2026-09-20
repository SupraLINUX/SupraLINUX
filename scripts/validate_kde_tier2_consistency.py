#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []


def req(value, message):
    if not value:
        errors.append(message)


def load(path):
    return json.loads((ROOT / path).read_text())


canonical = load("manifests/kde-frameworks-tier2.json")
dependencies = load("manifests/kde-frameworks-tier2-dependencies.json")
discovery = load("manifests/kde-tier2-global-discovery.json")

nodes = {node["id"]: node for node in canonical.get("nodes", [])}
dep_nodes = dependencies.get("nodes", {})
metadata = dependencies.get("metadata", {})
active = discovery.get("nodes", {})
completed = discovery.get("completed_nodes", {})

req(set(dep_nodes) == set(nodes), "dependency view must cover exactly the canonical Tier 2 node set")

for node_id, node in sorted(nodes.items()):
    framework_meta = node.get("kde_framework_dependencies", {})
    expected_required = framework_meta.get("required", [])
    expected_conditional = framework_meta.get("conditional", [])
    expected_selected = framework_meta.get("selected_profile", [])

    dep = dep_nodes.get(node_id, {})
    dep_frameworks = dep.get("frameworks", {})
    req(dep_frameworks.get("required", []) == expected_required, f"{node_id}: required dependency drift")
    req(dep_frameworks.get("conditional", []) == expected_conditional, f"{node_id}: conditional dependency drift")
    req(dep_frameworks.get("provider_selected", []) == expected_selected, f"{node_id}: selected-profile dependency drift")

    md = metadata.get(node_id, {})
    req(md.get("ref") == node.get("upstream_ref"), f"{node_id}: upstream ref drift")
    req(md.get("commit") == node.get("upstream_commit"), f"{node_id}: upstream commit drift")
    req(md.get("root_cmake_blob") == node.get("root_cmake_blob"), f"{node_id}: root CMake blob drift")

    planning = node.get("planning", {})
    if node.get("state") == "PASS":
        done = completed.get(node_id, {})
        req(planning.get("readiness") == "retained-pass", f"{node_id}: PASS planning readiness")
        req(done.get("state") == "PASS", f"{node_id}: PASS node missing completed discovery record")
    else:
        view = active.get(node_id, {})
        req(view, f"{node_id}: pending node missing active discovery record")
        req(view.get("readiness") == planning.get("readiness"), f"{node_id}: discovery readiness drift")
        expected_predecessors = set(expected_required + expected_selected)
        req(set(view.get("tier1_predecessors", [])) == expected_predecessors, f"{node_id}: discovery predecessor drift")

        if planning.get("provider_audit") == "required-before-materialization":
            req(
                dep.get("provider_audit") == "pending-package-profile-audit",
                f"{node_id}: provider audit state drift",
            )

snapshot = discovery.get("promoted_snapshot", {})
expected_snapshot = {
    "pass": sum(node.get("state") == "PASS" for node in nodes.values()),
    "pending": sum(node.get("state") == "pending" for node in nodes.values()),
    "current_fail": sum(node.get("state") == "FAIL" for node in nodes.values()),
    "blocked": sum(node.get("state") == "BLOCKED" for node in nodes.values()),
}
req(snapshot == expected_snapshot, "global discovery snapshot drift from canonical Tier 2 state")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 2 canonical/derived consistency: PASS")
print(f"nodes={len(nodes)} snapshot={expected_snapshot}")
