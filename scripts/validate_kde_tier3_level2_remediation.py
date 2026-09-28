#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
t=load("manifests/kde-frameworks-tier3.json")
c=load("manifests/kde-tier3-package-contracts.json")
m=load("manifests/kde-tier3-materialization.json")
l=load("manifests/kde-tier3-build-level2.json")
a=load("manifests/kde-tier3-build-level2-attempts.json")
p=load("manifests/kde-tier3-build-campaign.json")
POLICY=36468037163; L2RUN=36468036937; COMMIT="8b38a250b86f33dbbab60b406b2724ac6b25498d"; NEXT="tier3-build-level2-attempt4"
ART={
 "kcmutils":{"job_id":109078164555,"artifact_id":10989229464,"artifact_sha256":"ec9fb73d8c03f7c972ab2e878ffaa56a3a51f7edad56e276464a09842a88fe5b","package_version":"6.30.0-0supralinux2"},
 "kparts":{"job_id":109078164738,"artifact_id":10989828107,"artifact_sha256":"52183686781a2fd30a0d6b8c0b0c40fce6e5da55ac2f8680df7fcc2eae120112","package_version":"6.30.0-0supralinux2"},
}
T=["baloo","kcmutils","knotifyconfig","kparts"]
req(t.get("discovery_policy",{}).get("phase")=="build-level2","Attempt4 live phase")
req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level2-attempt4-active","Attempt4 package-build gate")
req(t.get("discovery_policy",{}).get("remediation")=="level2-attempt4-proof-and-symbol-metadata-remediation","Attempt4 remediation marker")
r=t.get("level2_remediation",{})
req(r.get("status")=="attempt4-active" and r.get("execution_authorized") is True and r.get("package_build_authorized") is True,"Attempt4 remediation authorization")
req(r.get("source_materialization_nodes")==["kcmutils","kparts"] and r.get("retained_source_nodes")==["baloo","knotifyconfig"],"Attempt4 remediation source scope")
req(r.get("materialization_artifacts")==ART and r.get("source_materialization_complete") is True,"Attempt4 promoted materializations")
req(r.get("activation_policy_workflow_run")==POLICY and r.get("activation_level2_workflow_run")==L2RUN and r.get("activation_commit")==COMMIT and r.get("next_gate")==NEXT,"Attempt4 activation evidence")
live=t.get("level2_execution",{})
req(live.get("status")=="attempt4-active" and live.get("attempt")==4 and live.get("current_attempt")==4 and live.get("execution_authorized") is True,"canonical Attempt4 active")
req(live.get("next_attempt") is None and live.get("next_gate")==NEXT,"canonical Attempt4 gate")
req(live.get("canonical_prebuild_snapshot")=="13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED","Attempt4 canonical prebuild snapshot")
pv=live.get("planning_validation",{})
req(pv.get("repository_policy_workflow_run")==POLICY and pv.get("level2_workflow_run")==L2RUN and pv.get("commit")==COMMIT and pv.get("result")=="PASS","canonical Attempt4 planning validation")
nodes={x["id"]:x for x in t.get("nodes",[])}
for x in T:
    req(nodes[x].get("state")=="FAIL" and nodes[x].get("packaging",{}).get("state")=="FAIL",x+": canonical FAIL retained before Attempt4 evidence")
req(nodes["knewstuff"].get("state")=="BLOCKED" and nodes["knewstuff"].get("packaging",{}).get("blocked_by")==["kcmutils"],"KNewStuff remains BLOCKED")
req(nodes["ktexteditor"].get("state")=="BLOCKED" and nodes["ktexteditor"].get("packaging",{}).get("blocked_by")==["kparts"],"KTextEditor remains BLOCKED")
req(nodes["purpose"].get("state")=="BLOCKED" and nodes["purpose"].get("packaging",{}).get("blocked_by")==["kcmutils"],"Purpose remains BLOCKED")
req(l.get("state")=="active-pending-ci" and l.get("execution_authorized") is True and l.get("current_attempt")==4 and l.get("next_attempt") is None and l.get("next_gate")==NEXT,"Level2 Attempt4 active state")
act=l.get("activation",{}); lpv=l.get("planning_validation",{})
req(act.get("status")=="ACTIVE" and act.get("attempt")==4 and act.get("planning_policy_workflow_run")==POLICY and act.get("planning_level2_workflow_run")==L2RUN and act.get("planning_commit")==COMMIT,"Level2 Attempt4 activation")
req(lpv.get("repository_policy_workflow_run")==POLICY and lpv.get("level2_workflow_run")==L2RUN and lpv.get("commit")==COMMIT and lpv.get("result")=="PASS","Level2 Attempt4 planning evidence")
req(l.get("canonical_snapshot")=="13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED","Level2 canonical snapshot")
for x in T:
    req(l["nodes"][x].get("state")=="remediation-pending-build",x+": Attempt4 runnable state")
for x in ("kcmutils","kparts"):
    req(l["nodes"][x].get("package_version")==ART[x]["package_version"],x+": Attempt4 package revision")
    req(l["nodes"][x].get("materialization")=={"workflow_run":36466461781,"job_id":ART[x]["job_id"],"artifact_id":ART[x]["artifact_id"],"artifact_sha256":ART[x]["artifact_sha256"]},x+": Attempt4 materialization pin")
    req(p["nodes"][x].get("package_version")==ART[x]["package_version"],x+": campaign revision")
    req(m["nodes"][x].get("state")=="materialized" and m["nodes"][x].get("package_version")==ART[x]["package_version"],x+": materialization PASS retained")
req(l["nodes"]["baloo"].get("package_version")=="6.30.0-0supralinux1" and l["nodes"]["knotifyconfig"].get("package_version")=="6.30.0-0supralinux1","retained-source revisions")
cr=c.get("level2_remediation",{})
req(cr.get("status")=="attempt4-active" and cr.get("materialization_authorized") is False and cr.get("package_build_authorized") is True,"contract Attempt4 authorization")
req(cr.get("activation_policy_workflow_run")==POLICY and cr.get("activation_level2_workflow_run")==L2RUN and cr.get("activation_commit")==COMMIT and cr.get("next_gate")==NEXT,"contract Attempt4 activation evidence")
mr=m.get("level2_remediation",{})
req(m.get("state")=="PASS" and mr.get("status")=="materialization-PASS" and mr.get("package_build_authorized") is True and mr.get("next_gate")==NEXT,"materialization handoff to Attempt4")
hist=a.get("campaign_history",[])
req(len(hist)==3 and hist[-1].get("attempt")==3 and hist[-1].get("result")=="MIXED","Attempt3 immutable history before Attempt4")
runner=(ROOT/"scripts/run-kde-tier3-build-level2.sh").read_text()
req("support-closure.json" in runner and '"support_input_ids"' in runner,"support closure evidence")
req('if x["kind"]=="support" and x.get("dev_package")' not in runner,"no synthetic support dev buildinfo edge")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 Attempt 4 activation: PASS")
print("nodes=baloo,kcmutils,knotifyconfig,kparts")
print("versions=baloo:-1 kcmutils:-2 knotifyconfig:-1 kparts:-2")
print("canonical=13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED")
print("next_gate="+NEXT)
