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
    marker=t.get("discovery_policy",{}).get("remediation")
    if marker=="round18-kio-svg-test-provider-materialization-pending-ci":
        target="validate_kde_tier3_round18_remediation.py"
    else:
        target="validate_kde_tier3_round11_materialization.py"
elif gate=="tier3-level1-source-PASS-pending-planning-validation":
    marker=t.get("discovery_policy",{}).get("remediation")
    if marker=="round18-kio-svg-test-provider-source-PASS-pending-planning-validation":
        target="validate_kde_tier3_round18_planning.py"
    else:
        target="validate_kde_tier3_round11_planning.py"
elif gate=="tier3-level1-authorized":
    target="validate_kde_tier3_round11_attempt7.py"
elif gate=="tier3-level1-attempt7-closed":
    target="validate_kde_tier3_round11_attempt7_closure.py"
else:
    raise SystemExit(f"unsupported Round 11 lifecycle gate: {gate!r}")

raise SystemExit(subprocess.run([sys.executable,str(ROOT/"scripts"/target)]).returncode)
