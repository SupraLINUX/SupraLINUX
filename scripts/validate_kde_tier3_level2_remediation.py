#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

for script in ("validate_kde_tier3_level2_attempt4_closure.py","validate_kde_tier3_level2_attempt5_closure.py"):
    rc=subprocess.run([sys.executable,str(ROOT/"scripts"/script)]).returncode
    if rc: raise SystemExit(rc)

t=load("manifests/kde-frameworks-tier3.json")
c=load("manifests/kde-tier3-package-contracts.json")
m=load("manifests/kde-tier3-materialization.json")
l=load("manifests/kde-tier3-build-level2.json")
a=load("manifests/kde-tier3-build-level2-attempts.json")
hist=a.get("campaign_history",[])
latest=hist[-1] if hist else {}
attempt=latest.get("attempt")
SNAP="17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED"
NEXT="tier3-knewstuff-runtime-validation-planning"

req(latest.get("result")=="PASS" and latest.get("package_attempted") is True,"latest Level2 package attempt PASS")
req(attempt==5,"Level2 closed attempt identity")
req(latest.get("next_gate")==NEXT,"Level2 historical/live handoff")

# Historical Level 2 closure is immutable. Do not couple this validator to the
# current runtime-validation phase, current Tier 3 node states, or the current DAG.
# Later lifecycle transitions must not invalidate a closed package attempt.
r=t.get("level2_remediation",{})
req(r.get("status")=="package-attempt-PASS-closed" and r.get("current_attempt")==attempt and r.get("next_attempt") is None,"historical Level2 closure")
req(r.get("execution_authorized") is False and r.get("package_build_authorized") is False and r.get("next_gate")==NEXT,"historical Level2 execution closed")

lx=t.get("level2_execution",{})
req(lx.get("status")=="package-attempt-PASS-closed" and lx.get("current_attempt")==attempt and lx.get("execution_authorized") is False,"historical Level2 execution closure")
req(lx.get("canonical_snapshot")==SNAP and lx.get("next_gate")==NEXT,"historical Level2 snapshot/handoff")

snap=t.get("level2_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(17,3,0,0),"historical Level2 snapshot counts")
req(snap.get("runtime_pending")==["knewstuff"] and snap.get("workflow_run")==36503684811 and snap.get("commit")=="fdc9d93fcc6ec9065f173d5d47b2bca928bf6f06","historical Level2 snapshot evidence")

req(l.get("state")=="PASS" and l.get("execution_authorized") is False and l.get("current_attempt")==attempt and l.get("next_attempt") is None,"Level2 manifest closed PASS")
req(l.get("canonical_snapshot")==SNAP and l.get("next_gate")==NEXT,"Level2 manifest handoff")
for x in ("baloo","kcmutils","knotifyconfig","kparts"):
    req(l["nodes"][x].get("state")=="PASS" and l["nodes"][x].get("pass_evidence",{}).get("result")=="PASS",x+": Level2 retained PASS")
req(l["nodes"]["kcmutils"].get("pass_evidence",{}).get("artifact_id")==11006467074,"KCMUtils Level2 PASS artifact")

cr=c.get("level2_remediation",{})
req(cr.get("status")=="package-attempt-PASS-closed" and cr.get("package_build_authorized") is False and cr.get("current_attempt")==attempt and cr.get("next_gate")==NEXT,"contract Level2 closure")

me=m.get("nodes",{}).get("kcmutils",{}).get("evidence",{})
req(me.get("result")=="PASS" and me.get("package_attempted") is False,"KCMUtils source materialization remains source-only PASS")
req(me.get("package_version")=="6.30.0-0supralinux3","KCMUtils materialization version retained")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 historical closure: PASS")
print("closed_package_attempt="+str(attempt))
print("canonical="+SNAP)
print("next_gate="+NEXT)
