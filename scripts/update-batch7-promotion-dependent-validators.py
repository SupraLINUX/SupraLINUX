#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: update-batch7-promotion-dependent-validators.py <canonical-checkout>")
root = Path(sys.argv[1]).resolve()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one target, found {count}")
    return text.replace(old, new, 1)

# Packaging-reference snapshot remains non-authoritative; its policy validator simply
# needs to recognize the three additional real package PASS nodes.
p = root / "scripts/validate_kde_tier1_packaging_reference.py"
s = p.read_text()
marker = "}\nerrors: list[str] = []"
add = '''    "kcalendarcore": ("6.30.0-0supralinux5", 35130213945, 10461386548, "6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6"),\n    "kcoreaddons": ("6.30.0-0supralinux4", 35122522242, 10457958023, "c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64"),\n    "kwidgetsaddons": ("6.30.0-0supralinux7", 35145607543, 10467164025, "f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e"),\n'''
if '"kcalendarcore": ("6.30.0-0supralinux5"' in s:
    raise SystemExit("packaging-reference validator already contains Batch 7 promotion")
s = replace_once(s, marker, add + marker, "packaging-reference PASS_NODES")
s = replace_once(s,
    'require(sum(1 for node in source_nodes if node.get("state") == "PASS") == 18, "Reference validator expects 18 actual package PASS nodes")',
    'require(sum(1 for node in source_nodes if node.get("state") == "PASS") == 21, "Reference validator expects 21 actual package PASS nodes")',
    "packaging-reference PASS count")
s = replace_once(s,
    'require(sum(1 for node in source_nodes if node.get("state") == "pending") == 11, "Reference validator expects 11 pending nodes")',
    'require(sum(1 for node in source_nodes if node.get("state") == "pending") == 8, "Reference validator expects 8 pending nodes")',
    "packaging-reference pending count")
s = replace_once(s,
    'print("Actual package states: 18 PASS; 11 pending")',
    'print("Actual package states: 21 PASS; 8 pending")',
    "packaging-reference summary")
p.write_text(s)

# Packaging-tree evidence remains the exact historical 29-node/58-tree snapshot.
# Only the later canonical package-state expectations advance from 18/11 to 21/8.
p = root / "scripts/validate_kde_tier1_packaging_tree.py"
s = p.read_text()
old_set_tail = '''    "kidletime", "modemmanager-qt", "networkmanager-qt", "kwindowsystem", "solid",\n}'''
new_set_tail = '''    "kidletime", "modemmanager-qt", "networkmanager-qt", "kwindowsystem", "solid",\n    "kcalendarcore", "kcoreaddons", "kwidgetsaddons",\n}'''
s = replace_once(s, old_set_tail, new_set_tail, "packaging-tree PASS_NODES")
s = replace_once(s,
    'require(sum(1 for node in nodes if node.get("state") == "PASS") == 18, "Packaging-tree validator expects 18 actual package PASS nodes")',
    'require(sum(1 for node in nodes if node.get("state") == "PASS") == 21, "Packaging-tree validator expects 21 actual package PASS nodes")',
    "packaging-tree PASS count")
s = replace_once(s,
    'require(sum(1 for node in nodes if node.get("state") == "pending") == 11, "Packaging-tree validator expects 11 pending nodes")',
    'require(sum(1 for node in nodes if node.get("state") == "pending") == 8, "Packaging-tree validator expects 8 pending nodes")',
    "packaging-tree pending count")
s = replace_once(s,
    'print("Reference work has no state authority; current real package state is 18 PASS / 11 pending")',
    'print("Reference work has no state authority; current real package state is 21 PASS / 8 pending")',
    "packaging-tree summary")
p.write_text(s)

# Batch 1: preserve its historical closure (7/22) but advance only its assertions
# about the current canonical frontier.
p = root / "scripts/validate_kde_tier1_package_batch1.py"
s = p.read_text()
s = replace_once(s,
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "PASS") == 18, "Canonical Tier 1 PASS count must be 18 after Batch 6 closure")',
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "PASS") == 21, "Canonical Tier 1 PASS count must be 21 after Batch 7 closure")',
    "Batch1 current PASS count")
s = replace_once(s,
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "pending") == 11, "Canonical Tier 1 pending count must be 11 after Batch 6 closure")',
    'require(sum(1 for item in tier_nodes.values() if item.get("state") == "pending") == 8, "Canonical Tier 1 pending count must be 8 after Batch 7 closure")',
    "Batch1 current pending count")
s = replace_once(s,
    'print("Canonical Tier 1 now: 18 PASS, 11 pending, 0 FAIL, 0 BLOCKED; Batch 1 historical closure remains 7/22")',
    'print("Canonical Tier 1 now: 21 PASS, 8 pending, 0 FAIL, 0 BLOCKED; Batch 1 historical closure remains 7/22")',
    "Batch1 summary")
p.write_text(s)

# Batch 4: preserve its 13/16 closure snapshot and historical docs; update only
# present-day canonical assertions and the current dependency-document count.
p = root / "scripts/validate_kde_tier1_package_batch4.py"
s = p.read_text()
s = replace_once(s,
    'req(sum(1 for n in tier1.values() if n.get("state") == "PASS") == 18, "Current Tier 1 PASS count must be 18 after Batch 6 closure")',
    'req(sum(1 for n in tier1.values() if n.get("state") == "PASS") == 21, "Current Tier 1 PASS count must be 21 after Batch 7 closure")',
    "Batch4 current PASS count")
s = replace_once(s,
    'req(sum(1 for n in tier1.values() if n.get("state") == "pending") == 11, "Current Tier 1 pending count must be 11 after Batch 6 closure")',
    'req(sum(1 for n in tier1.values() if n.get("state") == "pending") == 8, "Current Tier 1 pending count must be 8 after Batch 7 closure")',
    "Batch4 current pending count")
s = replace_once(s,
    'req("18 PASS / 11 pending" in depdoc, "dependency documentation current canonical count")',
    'req("21 PASS / 8 pending" in depdoc, "dependency documentation current canonical count")',
    "Batch4 dependency doc current count")
s = replace_once(s,
    'print("Current canonical Tier 1: 18 PASS / 11 pending / 0 FAIL / 0 BLOCKED; Batch 4 historical closure remains 13/16")',
    'print("Current canonical Tier 1: 21 PASS / 8 pending / 0 FAIL / 0 BLOCKED; Batch 4 historical closure remains 13/16")',
    "Batch4 summary")
p.write_text(s)

# Batch 5: the 2026-09-15 status file is historical and must remain 18/11. Only
# current Tier1 state and living DAG/dependency docs advance to 21/8.
p = root / "scripts/validate_kde_tier1_package_batch5.py"
s = p.read_text()
s = replace_once(s,
    'req(sum(1 for n in tier.values() if n.get("state") == "PASS") == 18, "Tier1 current PASS count must be 18")',
    'req(sum(1 for n in tier.values() if n.get("state") == "PASS") == 21, "Tier1 current PASS count must be 21")',
    "Batch5 current PASS count")
s = replace_once(s,
    'req(sum(1 for n in tier.values() if n.get("state") == "pending") == 11, "Tier1 current pending count must be 11")',
    'req(sum(1 for n in tier.values() if n.get("state") == "pending") == 8, "Tier1 current pending count must be 8")',
    "Batch5 current pending count")
old_docs = '''for path in (CURRENT_STATUS, DAG_DOC, DEPENDENCY_DOC):\n    t = text(path)\n    req("18 PASS" in t and "11 pending" in t, f"{path.name}: current canonical count")'''
new_docs = '''t = text(CURRENT_STATUS)\nreq("18 PASS" in t and "11 pending" in t, f"{CURRENT_STATUS.name}: historical 2026-09-15 canonical count")\nfor path in (DAG_DOC, DEPENDENCY_DOC):\n    t = text(path)\n    req("21 PASS" in t and "8 pending" in t, f"{path.name}: current canonical count")'''
s = replace_once(s, old_docs, new_docs, "Batch5 current/historical docs split")
s = replace_once(s,
    'print("Canonical Tier 1: 18 PASS / 11 pending / 0 FAIL / 0 BLOCKED")',
    'print("Canonical Tier 1: 21 PASS / 8 pending / 0 FAIL / 0 BLOCKED")',
    "Batch5 summary")
p.write_text(s)

# Batch 6: keep the campaign closure snapshot and every BATCH6-CANONICAL-CLOSURE
# historical marker at 18/11. Only the current Tier1 count and current summary advance.
p = root / "scripts/validate_kde_tier1_package_batch6.py"
s = p.read_text()
s = replace_once(s,
    "counts={s:sum(x.get('state')==s for x in t['nodes']) for s in ('PASS','pending','FAIL','BLOCKED')}; req(counts=={'PASS':18,'pending':11,'FAIL':0,'BLOCKED':0},f'Tier1 counts {counts}')",
    "counts={s:sum(x.get('state')==s for x in t['nodes']) for s in ('PASS','pending','FAIL','BLOCKED')}; req(counts=={'PASS':21,'pending':8,'FAIL':0,'BLOCKED':0},f'Tier1 current counts {counts}')",
    "Batch6 current counts")
s = replace_once(s,
    "print('Canonical Tier 1: 18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED')",
    "print('Canonical Tier 1 current state: 21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED; Batch 6 historical closure remains 18/11')",
    "Batch6 summary")
p.write_text(s)

print("Promotion-dependent validators: PASS; historical batch closure snapshots preserved")
