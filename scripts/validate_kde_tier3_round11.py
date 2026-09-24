#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
t=json.loads((ROOT/"manifests/kde-frameworks-tier3.json").read_text())
ar=t.get("active_remediation",{})
gate=t.get("discovery_policy",{}).get("package_builds")

if ar.get("round")!=11:
    raise SystemExit("Round 11 lifecycle validator invoked outside Round 11")

if gate=="tier3-level1-remediation-pending-materialization":
    target="validate_kde_tier3_round11_materialization.py"
elif gate=="tier3-level1-source-PASS-pending-planning-validation":
    target="validate_kde_tier3_round11_planning.py"
else:
    raise SystemExit(f"unsupported Round 11 lifecycle gate: {gate!r}")

raise SystemExit(subprocess.run([sys.executable,str(ROOT/"scripts"/target)]).returncode)
