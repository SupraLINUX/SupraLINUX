#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
REFERENCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1-packaging-reference.json"
RUNNER = ROOT / "scripts" / "run-kde-tier1-packaging-tree-snapshot.sh"
SCOPE = ROOT / "scripts" / "kde-tier1-packaging-tree-needed.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-packaging-tree.yml"
DOC = ROOT / "docs" / "kde-tier1-packaging-trees.md"

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        print(f"ERROR: {path.relative_to(ROOT)} must contain an object", file=sys.stderr)
        raise SystemExit(1)
    return value


source = load(SOURCE_MANIFEST)
reference = load(REFERENCE_MANIFEST)
runner = read(RUNNER)
scope = read(SCOPE)
workflow = read(WORKFLOW)
doc = read(DOC)

nodes = source.get("nodes", [])
require(source.get("frameworks_series") == "6.30.0", "Packaging-tree lane must follow Frameworks 6.30.0")
require(isinstance(nodes, list) and len(nodes) == 29, "Packaging-tree lane requires exactly 29 Tier 1 nodes")
node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
require(len(node_ids) == 29 and None not in node_ids, "Tier 1 node IDs are incomplete")

require(reference.get("authority") is False, "Packaging references must remain non-authoritative")
require(reference.get("role") == "packaging-reference-only", "Packaging-reference manifest role changed unexpectedly")
require(reference.get("selected_kde") == "6.30.0", "Packaging-reference manifest must follow selected KDE 6.30.0")
reference_nodes = reference.get("nodes", {})
require(set(reference_nodes) == node_ids, "Packaging-tree source-package mapping must cover the exact Tier 1 set")
for node_id in sorted(node_ids):
    require(reference_nodes.get(node_id) == {"source_package": f"kf6-{node_id}"}, f"{node_id}: source-package mapping changed unexpectedly")

for token in (
    'role": "packaging-reference-trees-only"',
    '"authoritative": False',
    '"framework_package_build_certification": "unchanged"',
    "ubuntu-archive-keyring.gpg",
    "debian-archive-keyring.gpg",
    "Checksums-Sha256",
    ".debian.tar.",
    "Expected exactly one .debian.tar.*",
    "sha256sum --check --strict",
    "packaging_trees=58",
    "source_index_signature=APT-verified",
    "No Framework package or DAG state was promoted",
):
    require(token in runner, f"Packaging-tree runner missing invariant: {token}")

require("https://archive.ubuntu.com/ubuntu" in runner, "Packaging-tree runner must use Ubuntu archive HTTPS provider")
require("https://deb.debian.org/debian" in runner, "Packaging-tree runner must use Debian archive HTTPS provider")
require("resolute main universe" in runner and "resolute-updates main universe" in runner and "resolute-security main universe" in runner, "Ubuntu source indices must cover Resolute release/updates/security")
require("sid main" in runner, "Debian source index must be sid main")
require("Reference" in runner and "newer than selected KDE" in runner, "Packaging-tree lane must stop for a reference newer than selected KDE")
require("tree-files.sha256" in runner and "tree-hashes.tsv" in runner, "Packaging-tree lane must retain extracted-tree hashes")
require("download-plan.tsv" in runner and "snapshot.json" in runner and "versions.tsv" in runner, "Packaging-tree lane must retain normalized provenance records")

for token in (
    "manifests/kde-frameworks-tier1.json",
    "manifests/kde-frameworks-tier1-packaging-reference.json",
    "scripts/run-kde-tier1-packaging-tree-snapshot.sh",
    "scripts/kde-tier1-packaging-tree-needed.sh",
    ".github/workflows/kde-tier1-packaging-tree.yml",
):
    require(token in scope, f"Packaging-tree scope must track input {token}")
require("docs/" not in scope, "Packaging-tree capture must not rerun for documentation-only changes")
require("validate_kde_tier1_packaging_tree.py" not in scope, "Packaging-tree capture must not rerun for validator-only changes")
require('git diff --name-only "${BEFORE}" "${AFTER}" --' in scope, "Packaging-tree scope must compare the exact event delta")

for token in (
    "runs-on: ubuntu-26.04",
    "fetch-depth: 0",
    "github.event.before",
    "github.event.after",
    "github.event.pull_request.base.sha",
    "github.event.pull_request.head.sha",
    "bash scripts/kde-tier1-packaging-tree-needed.sh",
    "bash scripts/run-kde-tier1-packaging-tree-snapshot.sh",
    "steps.scope.outputs.run == 'true'",
    "steps.scope.outputs.run == 'false'",
    "retention-days: 90",
):
    require(token in workflow, f"Packaging-tree workflow missing invariant: {token}")
require("paths:" not in workflow, "Packaging-tree workflow must not use PR-wide paths filtering")
require("workflow_dispatch" in workflow, "Packaging-tree workflow must support explicit manual refresh")

require("KDE upstream" in doc and "authority" in doc.lower(), "Packaging-tree documentation must preserve KDE authority")
require("58" in doc and "29" in doc, "Packaging-tree documentation must state expected tree/node counts")
require("Checksums-Sha256" in doc, "Packaging-tree documentation must describe signed-index checksum provenance")
require("no package" in doc.lower() and "PASS" in doc, "Packaging-tree documentation must distinguish reference PASS from package PASS")

for node in nodes:
    if not isinstance(node, dict):
        continue
    node_id = node.get("id")
    if node_id == "attica":
        require(node.get("state") == "PASS", "Attica package PASS must remain intact")
    else:
        require(node.get("state") == "pending", f"{node_id}: reference-tree work must not promote package state")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 packaging-tree policy validation: PASS")
print("Expected capture: 29 nodes x 2 distro references = 58 hash-verified debian/ trees")
print("Authority: KDE upstream; Ubuntu/Debian trees are compatibility references only")
print("Package state remains independent of reference-tree capture")
