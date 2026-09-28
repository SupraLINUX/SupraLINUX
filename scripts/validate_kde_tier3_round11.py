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
    elif marker=="attempt9-kio-proven-remediation-pending-materialization":
        target="validate_kde_tier3_kio_attempt9_definition.py"
    elif marker=="attempt10-kio-symbol-metadata-remediation-pending-materialization":
        target="validate_kde_tier3_kio_attempt10_definition.py"
    else:
        target="validate_kde_tier3_round11_materialization.py"
elif gate=="tier3-level1-source-PASS-pending-planning-validation":
    marker=t.get("discovery_policy",{}).get("remediation")
    if marker=="round18-kio-svg-test-provider-source-PASS-pending-planning-validation":
        target="validate_kde_tier3_round18_planning.py"
    elif marker=="attempt9-kio-remediation-source-PASS-pending-planning-validation":
        target="validate_kde_tier3_kio_attempt9_planning.py"
    else:
        target="validate_kde_tier3_round11_planning.py"
elif gate=="tier3-level1-authorized":
    marker=t.get("discovery_policy",{}).get("remediation")
    if marker=="round18-kio-svg-test-provider-attempt8-active":
        target="validate_kde_tier3_round18_attempt8.py"
    elif marker=="attempt9-kio-proven-remediation-attempt9-active":
        target="validate_kde_tier3_kio_attempt9.py"
    else:
        target="validate_kde_tier3_round11_attempt7.py"
elif gate=="tier3-level1-attempt7-closed":
    target="validate_kde_tier3_round11_attempt7_closure.py"
elif gate=="tier3-level1-attempt8-closed":
    target="validate_kde_tier3_round18_attempt8_closure.py"
elif gate=="tier3-round19-diagnostic-pending":
    target="validate_kde_tier3_kio_round19_diagnostic.py"
elif gate=="tier3-round20-diagnostic-pending":
    target="validate_kde_tier3_kio_round20_diagnostic.py"
elif gate=="tier3-round21-diagnostic-pending":
    target="validate_kde_tier3_kio_round21_diagnostic.py"
elif gate=="tier3-round22-diagnostic-pending":
    target="validate_kde_tier3_kio_round22_diagnostic.py"
elif gate=="diagnostic-infrastructure-preflight-pending":
    target="validate_diagnostic_infrastructure_preflight.py"
elif gate in {"tier3-round23-diagnostic-pending","tier3-round23-diagnostic-closed"}:
    target="validate_kde_tier3_kio_round23_diagnostic.py"
elif gate=="tier3-round24-diagnostic-pending":
    target="validate_kde_tier3_kio_round24_diagnostic.py"
elif gate=="tier3-round24-diagnostic-closed":
    target="validate_kde_tier3_kio_round24_closure.py"
elif gate=="tier3-round25-remediation-pending":
    target="validate_kde_tier3_kio_round25_remediation.py"
elif gate=="tier3-round26-remediation-pending":
    target="validate_kde_tier3_kio_round26_remediation.py"
elif gate=="tier3-round26-remediation-closed":
    target="validate_kde_tier3_kio_round26_closure.py"
else:
    raise SystemExit(f"unsupported Round 11 lifecycle gate: {gate!r}")

raise SystemExit(subprocess.run([sys.executable,str(ROOT/"scripts"/target)]).returncode)
