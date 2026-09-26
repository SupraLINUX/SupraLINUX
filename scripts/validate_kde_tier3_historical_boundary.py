#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
HISTORICAL=[
    "scripts/validate_kde_tier3_kio_round12_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round13_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round14_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round15_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round16_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round17_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round18_provider_contract.py",
    "scripts/validate_kde_tier3_kio_round19_diagnostic.py",
]
LIVE_READS=[
    'ROOT/"manifests/kde-frameworks-tier3.json"',
    'ROOT/"manifests/kde-tier3-build-level1.json"',
    'ROOT/"manifests/kde-tier3-package-contracts.json"',
    'ROOT/"manifests/kde-tier3-materialization.json"',
    'ROOT/"manifests/kde-tier3-build-campaign.json"',
    'ROOT/"manifests/kde-dag.json"',
    'load("manifests/kde-frameworks-tier3.json")',
    'load("manifests/kde-tier3-build-level1.json")',
    'load("manifests/kde-tier3-package-contracts.json")',
    'load("manifests/kde-tier3-materialization.json")',
    'load("manifests/kde-tier3-build-campaign.json")',
    'load("manifests/kde-dag.json")',
]
errors=[]
for rel in HISTORICAL:
    text=(ROOT/rel).read_text()
    for token in LIVE_READS:
        if token in text:
            errors.append(f"{rel}: historical validator reads live state via {token}")
if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 historical evidence/live-state boundary: PASS")
print(f"historical_validators={len(HISTORICAL)}")
