#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round26-remediation.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")

next_gate="tier3-attempt9-kio-remediation-definition"
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="remediation","Round26 closed phase")
req(policy.get("package_builds")=="tier3-round26-remediation-closed","Round26 current closed gate")
req(policy.get("remediation")=="round26-combined-kio-remediation-PASS-pending-attempt9-definition","Round26 current remediation")

for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="round26-remediation-PASS-pending-attempt9-definition",name+" Round26 closure")
    req(obj.get("next_gate")==next_gate,name+" Attempt9 definition handoff")
    req(obj.get("execution_authorized") is False,name+" package execution blocked")
    e=obj.get("round26_remediation",{})
    req(e.get("status")=="remediation-PASS" and e.get("workflow_run")==36366972800 and e.get("job_id")==108755265236,name+" Round26 evidence")
    req(e.get("artifact_id")==10948970106 and e.get("artifact_sha256")=="7c8b91266fd9ecd79638c8c4bfc5419dadac937b911517522b083900e9bc9f98",name+" Round26 artifact")
    req(e.get("conclusion")=="hidden-home-causality-and-combined-kio-remediation-PASS",name+" Round26 conclusion")
    req(e.get("package_attempted") is False and e.get("package_state_effect")=="none",name+" Round26 package safety")

req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("next_attempt")==9,"Attempt9 remains unauthorized")
req(C.get("active_remediation",{}).get("level1_execution_authorized") is False,"Level1 remains blocked")
req(MAT.get("active_remediation",{}).get("package_attempted") is False and MAT.get("active_remediation",{}).get("package_state_effect")=="none","materialization unchanged")
req(M.get("status")=="remediation-PASS" and M.get("next_gate")==next_gate,"Round26 historical handoff")

print("KDE Tier 3 KIO Round 26 current lifecycle closure: PASS")
print("next_gate="+next_gate)
print("Attempt9=NOT-AUTHORIZED")
