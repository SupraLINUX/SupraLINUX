#!/usr/bin/env python3
from pathlib import Path


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        return
    if new not in text:
        raise SystemExit(f"{path}: replacement anchor missing: {old}")


# Packaging-tree reference capture remains immutable/non-authoritative;
# only the validator's view of later real package promotions changes.
p = Path("scripts/validate_kde_tier1_packaging_tree.py")
replace_required(
    p,
    '    "kidletime", "modemmanager-qt", "networkmanager-qt",\n}',
    '    "kidletime", "modemmanager-qt", "networkmanager-qt", "kwindowsystem", "solid",\n}',
)
replace_required(
    p,
    'require(sum(1 for node in nodes if node.get("state") == "PASS") == 16, "Packaging-tree validator expects 16 actual package PASS nodes")',
    'require(sum(1 for node in nodes if node.get("state") == "PASS") == 18, "Packaging-tree validator expects 18 actual package PASS nodes")',
)
replace_required(
    p,
    'require(sum(1 for node in nodes if node.get("state") == "pending") == 13, "Packaging-tree validator expects 13 pending nodes")',
    'require(sum(1 for node in nodes if node.get("state") == "pending") == 11, "Packaging-tree validator expects 11 pending nodes")',
)
replace_required(
    p,
    'print("Reference work has no state authority; current real package state is 16 PASS / 13 pending")',
    'print("Reference work has no state authority; current real package state is 18 PASS / 11 pending")',
)

# Batch 1 historical closure remains 7/22; only the later canonical state advances.
p = Path("scripts/validate_kde_tier1_package_batch1.py")
replace_required(
    p,
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "PASS") == 16, "Canonical Tier 1 PASS count must be 16 after later batch promotions")',
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "PASS") == 18, "Canonical Tier 1 PASS count must be 18 after Batch 6 closure")',
)
replace_required(
    p,
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "pending") == 13, "Canonical Tier 1 pending count must be 13 after later batch promotions")',
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "pending") == 11, "Canonical Tier 1 pending count must be 11 after Batch 6 closure")',
)
replace_required(
    p,
    'print("Canonical Tier 1 now: 16 PASS, 13 pending, 0 FAIL, 0 BLOCKED; Batch 1 historical closure remains 7/22")',
    'print("Canonical Tier 1 now: 18 PASS, 11 pending, 0 FAIL, 0 BLOCKED; Batch 1 historical closure remains 7/22")',
)

# Batch 4 historical closure remains 13/16; only current canonical checks advance.
p = Path("scripts/validate_kde_tier1_package_batch4.py")
replace_required(
    p,
    'req(sum(1 for n in tier1.values() if n.get("state") == "PASS") == 16, "Current Tier 1 PASS count must be 16 after Batch 5 closure")',
    'req(sum(1 for n in tier1.values() if n.get("state") == "PASS") == 18, "Current Tier 1 PASS count must be 18 after Batch 6 closure")',
)
replace_required(
    p,
    'req(sum(1 for n in tier1.values() if n.get("state") == "pending") == 13, "Current Tier 1 pending count must be 13 after Batch 5 closure")',
    'req(sum(1 for n in tier1.values() if n.get("state") == "pending") == 11, "Current Tier 1 pending count must be 11 after Batch 6 closure")',
)
replace_required(
    p,
    'req("16 PASS / 13 pending" in depdoc, "dependency documentation current canonical count")',
    'req("18 PASS / 11 pending" in depdoc, "dependency documentation current canonical count")',
)
replace_required(
    p,
    'print("Current canonical Tier 1: 16 PASS / 13 pending / 0 FAIL / 0 BLOCKED; Batch 4 historical closure remains 13/16")',
    'print("Current canonical Tier 1: 18 PASS / 11 pending / 0 FAIL / 0 BLOCKED; Batch 4 historical closure remains 13/16")',
)

# Batch 5's campaign/doc snapshot remains historical 16/13. Current cross-project docs are 18/11.
p = Path("scripts/validate_kde_tier1_package_batch5.py")
replace_required(
    p,
    'req(sum(1 for n in tier.values() if n.get("state") == "PASS") == 16, "Tier1 current PASS count must be 16")',
    'req(sum(1 for n in tier.values() if n.get("state") == "PASS") == 18, "Tier1 current PASS count must be 18")',
)
replace_required(
    p,
    'req(sum(1 for n in tier.values() if n.get("state") == "pending") == 13, "Tier1 current pending count must be 13")',
    'req(sum(1 for n in tier.values() if n.get("state") == "pending") == 11, "Tier1 current pending count must be 11")',
)
replace_required(
    p,
    '''for path in (DOC, STATUS, CURRENT_STATUS, DAG_DOC, DEPENDENCY_DOC):
    t = text(path)
    req("16 PASS" in t and "13 pending" in t, f"{path.name}: current canonical count")''',
    '''for path in (DOC, STATUS):
    t = text(path)
    req("16 PASS" in t and "13 pending" in t, f"{path.name}: historical Batch 5 closure count")
for path in (CURRENT_STATUS, DAG_DOC, DEPENDENCY_DOC):
    t = text(path)
    req("18 PASS" in t and "11 pending" in t, f"{path.name}: current canonical count")''',
)
replace_required(
    p,
    'print("Canonical Tier 1: 16 PASS / 13 pending / 0 FAIL / 0 BLOCKED")',
    'print("Canonical Tier 1: 18 PASS / 11 pending / 0 FAIL / 0 BLOCKED")',
)

# Document the implementation/validator change without rewriting historical batch closures.
doc = Path("docs/status/2026-09-15-batch6.md")
d = doc.read_text(encoding="utf-8")
marker = "### Remaining policy-validator audit"
if marker not in d:
    d += (
        "\n\n" + marker + "\n\n"
        "- After the Tier 1 and packaging-reference fixes, a complete audit of the remaining Repository Policy validators found stale current-state assumptions in the packaging-tree, Batch 1, Batch 4, and Batch 5 validators. "
        "Their historical closure snapshots remain unchanged (Batch 1 `7/22`, Batch 4 `13/16`, Batch 5 `16/13`); only checks describing the current canonical state are aligned to Batch 6 `18 PASS / 11 pending / 0 FAIL / 0 BLOCKED`. "
        "Batch 2 and Batch 3 require no change. No package, source, reference snapshot, runner, ABI, or build-input change is introduced.\n"
    )
    doc.write_text(d, encoding="utf-8")
