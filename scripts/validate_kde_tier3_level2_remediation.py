#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
t=load("manifests/kde-frameworks-tier3.json"); c=load("manifests/kde-tier3-package-contracts.json"); m=load("manifests/kde-tier3-materialization.json"); l=load("manifests/kde-tier3-build-level2.json"); a=load("manifests/kde-tier3-build-level2-attempts.json"); p=load("manifests/kde-tier3-build-campaign.json")
RUN=36466461781; COMMIT="a0ee684e97f834e39a760eab401ba29e2c172a5d"; NEXT="tier3-build-level2-attempt4-activation-validation"; STATUS="materialization-PASS-pending-attempt4-activation-validation"
ART={
 "kcmutils":{"job_id":109078164555,"artifact_id":10989229464,"artifact_sha256":"ec9fb73d8c03f7c972ab2e878ffaa56a3a51f7edad56e276464a09842a88fe5b","package_version":"6.30.0-0supralinux2"},
 "kparts":{"job_id":109078164738,"artifact_id":10989828107,"artifact_sha256":"52183686781a2fd30a0d6b8c0b0c40fce6e5da55ac2f8680df7fcc2eae120112","package_version":"6.30.0-0supralinux2"},
}
r=t.get("level2_remediation",{})
req(r.get("status")==STATUS,"Level2 remediation status")
req(r.get("trigger")=={"attempt":3,"workflow_run":36461187872,"commit":"76bbe36b1d036b31bc95840dbba26dbf8e9b0bb1","result":"MIXED"},"Attempt3 trigger")
req(r.get("source_materialization_nodes")==["kcmutils","kparts"] and r.get("retained_source_nodes")==["baloo","knotifyconfig"],"Level2 remediation scope")
req(r.get("candidate_package_versions")=={"kcmutils":"6.30.0-0supralinux2","kparts":"6.30.0-0supralinux2"},"Level2 remediation revisions")
req(r.get("execution_authorized") is False and r.get("canonical_state_effect")=="none","Level2 execution pause")
req(r.get("source_materialization_complete") is True and r.get("materialization_workflow_run")==RUN and r.get("materialization_commit")==COMMIT,"Level2 materialization identity")
req(r.get("materialization_artifacts")==ART and r.get("next_gate")==NEXT,"Level2 materialization artifacts/gate")
req(t.get("discovery_policy",{}).get("phase")=="build-level2-remediation-planning","Level2 live phase")
req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level2-attempt4-remediation-materialized-pending-activation","Level2 package-build gate")
live=t.get("level2_execution",{})
req(live.get("status")=="attempt3-closed-MIXED-attempt4-materialization-PASS-pending-activation" and live.get("execution_authorized") is False,"Level2 live pause")
req(live.get("current_attempt")==3 and live.get("next_attempt")==4 and live.get("next_gate")==NEXT,"Attempt4 activation handoff")
req(live.get("canonical_snapshot")=="13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED","canonical snapshot")
nodes={x["id"]:x for x in t.get("nodes",[])}
for x in ("baloo","kcmutils","knotifyconfig","kparts"): req(nodes[x].get("state")=="FAIL" and nodes[x].get("packaging",{}).get("state")=="FAIL",x+": canonical FAIL retained")
req(nodes["knewstuff"].get("state")=="BLOCKED" and nodes["knewstuff"].get("packaging",{}).get("blocked_by")==["kcmutils"],"KNewStuff BLOCKED")
req(nodes["ktexteditor"].get("state")=="BLOCKED" and nodes["ktexteditor"].get("packaging",{}).get("blocked_by")==["kparts"],"KTextEditor BLOCKED")
req(nodes["purpose"].get("state")=="BLOCKED" and nodes["purpose"].get("packaging",{}).get("blocked_by")==["kcmutils"],"Purpose BLOCKED")
req(l.get("state")=="remediation-materialized-pending-activation" and l.get("execution_authorized") is False,"Level2 build remains paused")
req(l.get("current_attempt")==3 and l.get("next_attempt")==4 and l.get("next_gate")==NEXT,"Level2 Attempt4 activation gate")
s=l.get("attempt3_summary",{})
req(s.get("workflow_run")==36461187872 and s.get("result")=="MIXED" and s.get("primary_classification")=={"FAIL":["kcmutils"],"INFRA_INVALID":["baloo","knotifyconfig","kparts"]},"Attempt3 closure retained")
hist=a.get("campaign_history",[])
req(len(hist)==3 and hist[-1].get("attempt")==3 and hist[-1].get("result")=="MIXED","Attempt3 immutable campaign ledger")
req(m.get("state")=="PASS" and m.get("remediation_queue")==[],"materialization promoted PASS")
mr=m.get("level2_remediation",{})
req(mr.get("status")==STATUS and mr.get("materialization_workflow_run")==RUN and mr.get("materialization_commit")==COMMIT,"materialization remediation evidence")
req(mr.get("materialization_evidence",{}).get("artifacts")==ART and mr.get("next_gate")==NEXT,"materialization artifacts/gate")
for x in ("kcmutils","kparts"):
    ev=m["nodes"][x].get("evidence",{})
    req(m["nodes"][x].get("state")=="materialized" and m["nodes"][x].get("package_version")==ART[x]["package_version"],x+": promoted materialization")
    req(ev.get("workflow_run")==RUN and ev.get("job_id")==ART[x]["job_id"] and ev.get("artifact_id")==ART[x]["artifact_id"] and ev.get("artifact_sha256")==ART[x]["artifact_sha256"] and ev.get("result")=="PASS",x+": exact materialization evidence")
    req(l["nodes"][x].get("package_version")==ART[x]["package_version"] and l["nodes"][x].get("materialization")=={"workflow_run":RUN,"job_id":ART[x]["job_id"],"artifact_id":ART[x]["artifact_id"],"artifact_sha256":ART[x]["artifact_sha256"]},x+": Level2 materialization handoff")
    req(p["nodes"][x].get("package_version")==ART[x]["package_version"] and p["nodes"][x].get("materialization")=={"workflow_run":RUN,"job_id":ART[x]["job_id"],"artifact_id":ART[x]["artifact_id"],"artifact_sha256":ART[x]["artifact_sha256"]},x+": campaign materialization handoff")
cr=c.get("level2_remediation",{})
req(cr.get("status")==STATUS and cr.get("materialization_authorized") is False and cr.get("package_build_authorized") is False,"contract post-materialization gate")
req(cr.get("source_materialization_complete") is True and cr.get("materialization_evidence",{}).get("artifacts")==ART and cr.get("next_gate")==NEXT,"contract materialization evidence")
kov=c["nodes"]["kcmutils"].get("symbol_template_overrides",[])
req(len(kov)==1 and kov[0].get("package")=="libkf6kcmutilsquick6" and kov[0].get("preserve_tags")==["arch=!riscv64"] and kov[0].get("add_tags")==["optional"],"KCMUtils symbols remediation")
adds=c["nodes"]["kparts"].get("symbol_template_additions",[])
req(len(adds)==1 and adds[0].get("package")=="libkf6parts6" and adds[0].get("symbol")=="_ZSt19piecewise_construct@Base" and adds[0].get("minimal_version")=="6.30.0" and adds[0].get("tags")==["optional"],"KParts symbols remediation")
runner=(ROOT/"scripts/run-kde-tier3-build-level2.sh").read_text()
req("support-closure.json" in runner and '"support_input_ids"' in runner,"support closure proof")
req('if x["kind"]=="support" and x.get("dev_package")' not in runner,"no synthetic support dev buildinfo edge")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 Attempt 4 remediation materialization: PASS")
print("kcmutils=6.30.0-0supralinux2 kparts=6.30.0-0supralinux2")
print("canonical=13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED")
print("next_gate="+NEXT)
