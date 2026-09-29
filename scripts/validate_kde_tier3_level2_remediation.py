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
d=load("manifests/kde-dag.json")
hist=a.get("campaign_history",[])
latest=hist[-1] if hist else {}
attempt=latest.get("attempt")
SNAP="17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED"
NEXT="tier3-knewstuff-runtime-validation-planning"

req(latest.get("result")=="PASS" and latest.get("package_attempted") is True,"latest Level2 package attempt PASS")
req(attempt==5,"Level2 closed attempt identity")
req(latest.get("next_gate")==NEXT,"Level2 historical/live handoff")

r=t.get("level2_remediation",{})
req(r.get("status")=="package-attempt-PASS-closed" and r.get("current_attempt")==attempt and r.get("next_attempt") is None,"canonical Level2 closure")
req(r.get("execution_authorized") is False and r.get("package_build_authorized") is False and r.get("next_gate")==NEXT,"canonical Level2 execution closed")
pol=t.get("discovery_policy",{})
req(pol.get("phase")=="runtime-validation-planning" and pol.get("package_builds")=="tier3-level2-package-attempt-PASS-closed","canonical post-Level2 phase")
req(pol.get("runtime_validation")=="planning-pending-policy-validation","canonical KNewStuff runtime-validation planning marker")
rv=t.get("runtime_validation",{})
req(rv.get("manifest")=="manifests/kde-tier3-knewstuff-runtime-validation.json" and rv.get("node")=="knewstuff","canonical runtime-validation manifest linkage")
req(rv.get("status")=="planning-pending-policy-validation" and rv.get("execution_authorized") is False,"canonical runtime-validation planning state")
req(rv.get("validation_run_kind")=="runtime-only" and rv.get("consumes_package_attempt") is False,"canonical runtime-validation attempt boundary")
req(rv.get("canonical_state_effect")=="none-until-runtime-validation-PASS" and rv.get("next_gate")==NEXT,"canonical runtime-validation planning handoff")
lx=t.get("level2_execution",{})
req(lx.get("status")=="package-attempt-PASS-closed" and lx.get("current_attempt")==attempt and lx.get("execution_authorized") is False,"canonical Level2 execution closure")
req(lx.get("canonical_snapshot")==SNAP and lx.get("next_gate")==NEXT,"canonical Level2 snapshot/handoff")

nodes={x["id"]:x for x in t.get("nodes",[])}
for x in ("baloo","kcmutils","knotifyconfig","kparts"):
    req(nodes[x].get("state")=="PASS" and nodes[x].get("packaging",{}).get("state")=="PASS" and nodes[x].get("packaging",{}).get("downstream_eligible") is True,x+": canonical Level2 PASS")
req(nodes["kcmutils"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux3","KCMUtils canonical version")
kp=[x for x in nodes["kcmutils"].get("packaging",{}).get("evidence",[]) if x.get("result")=="PASS" and x.get("package_state_effect")=="PASS"]
req(len(kp)==1 and kp[0].get("workflow_run")==36503684811 and kp[0].get("artifact_id")==11006467074 and kp[0].get("artifact_sha256")=="4dc1045a571b0cb05e61e25600a56fbdc59e5a80cde071cc3ad6af78f7b884a7","KCMUtils canonical PASS evidence")
req(nodes["knewstuff"].get("state")=="pending" and nodes["knewstuff"].get("packaging",{}).get("state")=="runtime-validation-required","KNewStuff runtime validation enabled")
req(nodes["knewstuff"].get("packaging",{}).get("downstream_eligible") is False and "blocked_by" not in nodes["knewstuff"].get("packaging",{}),"KNewStuff not auto-promoted")
for x in ("ktexteditor","purpose"):
    req(nodes[x].get("state")=="pending" and nodes[x].get("packaging",{}).get("state")=="pending",x+": Level3 pending")
snap=t.get("level2_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(17,3,0,0),"canonical snapshot counts")
req(snap.get("runtime_pending")==["knewstuff"] and snap.get("workflow_run")==36503684811 and snap.get("commit")=="fdc9d93fcc6ec9065f173d5d47b2bca928bf6f06","canonical snapshot evidence")

req(l.get("state")=="PASS" and l.get("execution_authorized") is False and l.get("current_attempt")==attempt and l.get("next_attempt") is None,"Level2 manifest closed PASS")
req(l.get("canonical_snapshot")==SNAP and l.get("next_gate")==NEXT,"Level2 manifest handoff")
for x in ("baloo","kcmutils","knotifyconfig","kparts"):
    req(l["nodes"][x].get("state")=="PASS" and l["nodes"][x].get("pass_evidence",{}).get("result")=="PASS",x+": Level2 retained PASS")
req(l["nodes"]["kcmutils"].get("pass_evidence",{}).get("artifact_id")==11006467074,"KCMUtils Level2 PASS artifact")

cr=c.get("level2_remediation",{})
req(cr.get("status")=="package-attempt-PASS-closed" and cr.get("package_build_authorized") is False and cr.get("current_attempt")==attempt and cr.get("next_gate")==NEXT,"contract Level2 closure")

me=m.get("nodes",{}).get("kcmutils",{}).get("evidence",{})
req(m.get("state")=="PASS" and me.get("result")=="PASS" and me.get("package_attempted") is False,"KCMUtils source materialization remains source-only PASS")
req(me.get("package_version")=="6.30.0-0supralinux3","KCMUtils materialization version retained")

dn=d.get("nodes",{}).get("kcmutils",{})
req(dn.get("state")=="PASS" and dn.get("downstream_eligible") is True and dn.get("package_version")=="6.30.0-0supralinux3","KCMUtils DAG promotion")
req(dn.get("attempt_ledger")=="manifests/kde-tier3-build-level2-attempts.json","KCMUtils DAG ledger")
dp=[x for x in dn.get("evidence",[]) if x.get("result")=="PASS"]
req(len(dp)==1 and dp[0].get("artifact_id")==11006467074 and dp[0].get("artifact_sha256")=="4dc1045a571b0cb05e61e25600a56fbdc59e5a80cde071cc3ad6af78f7b884a7","KCMUtils DAG PASS evidence")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 live closure: PASS")
print("closed_package_attempt="+str(attempt))
print("canonical="+SNAP)
print("next_gate="+NEXT)
