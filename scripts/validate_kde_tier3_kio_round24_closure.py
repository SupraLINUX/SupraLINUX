#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)
M=load("manifests/kde-tier3-kio-round24-diagnostic.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
next_gate="tier3-round25-kio-krecent-ordering-remediation-definition"
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="diagnostic" and policy.get("package_builds")=="tier3-round24-diagnostic-closed","Round24 current closed gate")
req(policy.get("remediation")=="round24-krecent-timestamp-tie-causality-confirmed-pending-round25-remediation-definition","Round24 current remediation")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="round24-diagnostic-PASS-pending-round25-remediation-definition",name+" Round24 closure")
    req(obj.get("next_gate")==next_gate,name+" Round24 handoff")
    req(obj.get("execution_authorized") is False,name+" package execution blocked")
    e=obj.get("round24_diagnostic",{})
    req(e.get("status")=="diagnostic-PASS" and e.get("workflow_run")==36295265079 and e.get("job_id")==108552864340,name+" Round24 evidence")
    req(e.get("artifact_id")==10922979916 and e.get("artifact_sha256")=="3fac75e577fbe9d33ec671ef6bc4fa9fca86f6324285fa04f7fb9a4147cfa4a3",name+" Round24 artifact")
    req(e.get("conclusion")=="timestamp-tie-causality-confirmed" and e.get("package_attempted") is False and e.get("package_state_effect")=="none",name+" Round24 result")
kp=T.get("active_remediation",{}).get("krecentdocument_policy",{})
req(kp.get("classification")=="timestamp-tie-causality-confirmed","KRecent classification")
req(kp.get("action")=="define-minimal-upstream-compatible-ordering-remediation-no-test-suppression","KRecent action")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("next_attempt")==9,"Attempt9 remains unauthorized")
req(C.get("active_remediation",{}).get("level1_execution_authorized") is False,"Level1 remains blocked")
req(MAT.get("active_remediation",{}).get("package_attempted") is False and MAT.get("active_remediation",{}).get("package_state_effect")=="none","materialization unchanged")
req(M.get("status")=="diagnostic-PASS" and M.get("next_gate")==next_gate,"Round24 historical handoff")
print("KDE Tier 3 KIO Round 24 current lifecycle closure: PASS")
print("next_gate="+next_gate)
print("Attempt9=NOT-AUTHORIZED")
