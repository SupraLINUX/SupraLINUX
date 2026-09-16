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

print("Promotion-dependent packaging reference/tree validators: PASS")
