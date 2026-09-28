#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

rc=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level2_attempt4_closure.py")]).returncode
if rc:
    raise SystemExit(rc)

t=load("manifests/kde-frameworks-tier3.json")
c=load("manifests/kde-tier3-package-contracts.json")
m=load("manifests/kde-tier3-materialization.json")
l=load("manifests/kde-tier3-build-level2.json")
a=load("manifests/kde-tier3-build-level2-attempts.json")
hist=a.get("campaign_history",[])
req(bool(hist),"Level2 attempt history")
latest=hist[-1] if hist else {}
cur=latest.get("attempt")
nxt=(cur+1) if isinstance(cur,int) else None
trigger={"attempt":cur,"workflow_run":latest.get("workflow_run"),"commit":latest.get("commit"),"result":latest.get("result")}
SNAP="16 PASS / 1 pending / 1 current FAIL / 2 BLOCKED"
GATE="tier3-level2-remediation-materialization-evidence"

req(latest.get("result")=="MIXED" and latest.get("package_attempted") is True,"latest valid package attempt closure")
r=t.get("level2_remediation",{})
req(r.get("status")=="materialization-pending-ci","Level2 remediation status")
req(r.get("trigger")==trigger,"Level2 remediation trigger follows latest closed attempt")
req(r.get("source_materialization_nodes")==["kcmutils"],"Level2 source remediation scope")
req(r.get("retained_source_nodes")==["baloo","knotifyconfig","kparts"],"Level2 retained PASS scope")
req(r.get("candidate_package_versions")=={"kcmutils":"6.30.0-0supralinux3"},"Level2 candidate revision")
req(r.get("execution_authorized") is False and r.get("next_gate")==GATE,"Level2 remediation execution pause")
pol=t.get("discovery_policy",{})
req(pol.get("phase")=="build-level2-remediation-planning","Level2 remediation phase")
req(pol.get("package_builds")=="tier3-level2-remediation-pending-materialization","Level2 remediation package gate")

lx=t.get("level2_execution",{})
req(lx.get("execution_authorized") is False and lx.get("current_attempt")==cur and lx.get("next_attempt")==nxt,"Level2 current/next package attempt")
req(lx.get("canonical_snapshot")==SNAP and lx.get("next_gate")==GATE,"Level2 canonical remediation handoff")
nodes={x["id"]:x for x in t.get("nodes",[])}
for x in ("baloo","knotifyconfig","kparts"):
    req(nodes[x].get("state")=="PASS" and nodes[x].get("packaging",{}).get("state")=="PASS" and nodes[x].get("packaging",{}).get("downstream_eligible") is True,x+": Attempt closure PASS")
req(nodes["kcmutils"].get("state")=="FAIL" and nodes["kcmutils"].get("packaging",{}).get("state")=="FAIL","KCMUtils current FAIL")
req(nodes["ktexteditor"].get("state")=="pending" and nodes["ktexteditor"].get("packaging",{}).get("state")=="pending","KTextEditor unblocked to pending")
for x in ("knewstuff","purpose"):
    req(nodes[x].get("state")=="BLOCKED" and nodes[x].get("packaging",{}).get("blocked_by")==["kcmutils"],x+": remains KCMUtils-blocked")
snap=t.get("level2_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(16,1,1,2),"canonical snapshot counts")

req(l.get("state")=="remediation-pending-materialization" and l.get("execution_authorized") is False,"Level2 binary execution paused")
req(l.get("current_attempt")==cur and l.get("next_attempt")==nxt and l.get("next_gate")==GATE,"Level2 package-attempt markers")
req(l.get("canonical_snapshot")==SNAP,"Level2 manifest canonical snapshot")
for x in ("baloo","knotifyconfig","kparts"):
    req(l["nodes"][x].get("state")=="PASS" and l["nodes"][x].get("pass_evidence",{}).get("result")=="PASS",x+": Level2 PASS evidence")
req(l["nodes"]["kcmutils"].get("state")=="rematerialization-pending" and l["nodes"]["kcmutils"].get("candidate_package_version")=="6.30.0-0supralinux3","KCMUtils Level2 rematerialization state")

req(m.get("state")=="remediation-pending-ci" and m.get("remediation_queue")==["kcmutils"],"materialization queue")
for x in m.get("selected_nodes",[]):
    expected="remediation-pending" if x=="kcmutils" else "materialized"
    req(m["nodes"][x].get("state")==expected,x+": materialization state")
req(m["nodes"]["kcmutils"].get("package_version")=="6.30.0-0supralinux2" and m["nodes"]["kcmutils"].get("candidate_package_version")=="6.30.0-0supralinux3","KCMUtils current/candidate source revisions")

cr=c.get("level2_remediation",{})
req(cr.get("trigger")==trigger and cr.get("materialization_authorized") is True and cr.get("package_build_authorized") is False,"contract materialization gate")
req(cr.get("candidate_package_versions")=={"kcmutils":"6.30.0-0supralinux3"} and cr.get("next_gate")==GATE,"contract remediation revision/gate")
req(c["nodes"]["kcmutils"].get("package_version_candidate")=="6.30.0-0supralinux3","KCMUtils contract candidate")
over=c["nodes"]["kcmutils"].get("symbol_template_overrides",[])
by_symbol={x.get("symbol"):x for x in over}
for sym,klass in (
    ("_ZTVSt23_Sp_counted_ptr_inplaceI10QQmlEngineSaIvELN9__gnu_cxx12_Lock_policyE2EE@Base","toolchain-generated-template-vtable"),
    ("_ZTISt23_Sp_counted_ptr_inplaceI10QQmlEngineSaIvELN9__gnu_cxx12_Lock_policyE2EE@Base","toolchain-generated-template-typeinfo"),
):
    x=by_symbol.get(sym,{})
    req(x.get("package")=="libkf6kcmutilsquick6" and x.get("preserve_tags")==["arch=!riscv64"] and x.get("add_tags")==["optional"] and x.get("classification")==klass,"KCMUtils optional toolchain symbol: "+sym)

runner=(ROOT/"scripts/run-kde-tier3-build-level2.sh").read_text()
req("support-closure.json" in runner and '"support_input_ids"' in runner,"support closure evidence")
req('if x["kind"]=="support" and x.get("dev_package")' not in runner,"no synthetic support dev buildinfo edge")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 live remediation: PASS")
print("current_package_attempt="+str(cur))
print("next_package_attempt="+str(nxt))
print("canonical="+SNAP)
print("materialization_queue=kcmutils")
