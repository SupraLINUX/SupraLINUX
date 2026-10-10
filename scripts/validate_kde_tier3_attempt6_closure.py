#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def req(value, message):
    if not value:
        errors.append(message)

def load(path):
    return json.loads((ROOT/path).read_text())

tier3=load("manifests/kde-frameworks-tier3.json")
level1=load("manifests/kde-tier3-build-level1.json")
ledger=load("manifests/kde-tier3-build-level1-attempts.json")
dag=load("manifests/kde-dag.json")
contracts=load("manifests/kde-tier3-package-contracts.json")
materialization=load("manifests/kde-tier3-materialization.json")

WORKFLOW=36035351270
COMMIT="f6d47684e4c69cf0765e2d24e8bb93807be04791"
NEXT_GATE="tier3-round11-kio-remediation-definition"
SNAPSHOT="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED"
BLOCKED=["baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"]
PASS_SET={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}

policy=tier3.get("discovery_policy",{})
req(policy.get("phase")=="build-level1","Attempt6 closure phase")
req(policy.get("package_builds")=="tier3-level1-attempt6-closed","Attempt6 closure build gate")
req(policy.get("provider_audit")=="PASS" and policy.get("package_contracts")=="PASS","Attempt6 closure prerequisite gates")

nodes={n.get("id"):n for n in tier3.get("nodes",[])}
req(len(nodes)==20,"Attempt6 closure Tier3 node count")
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS_SET,"Attempt6 closure PASS set")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"Attempt6 closure pending set")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"Attempt6 closure current FAIL set")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==set(BLOCKED),"Attempt6 closure BLOCKED set")

kio=nodes.get("kio",{})
kxml=nodes.get("kxmlgui",{})
req(kio.get("packaging",{}).get("state")=="FAIL" and kio.get("packaging",{}).get("package_version")=="6.30.0-0supralinux6","KIO canonical FAIL/version")
req(kio.get("packaging",{}).get("downstream_eligible") is False,"KIO not downstream eligible")
kev=(kio.get("packaging",{}).get("evidence") or [{}])[-1]
req(kev.get("workflow_run")==WORKFLOW and kev.get("job_id")==107754320435,"KIO Attempt6 workflow/job")
req(kev.get("artifact_id")==10824413911 and kev.get("artifact_sha256")=="61f2c1ad261fcc4fae4cd8064d71606af42542f5ab735a672e6ff77f6b2f5861","KIO Attempt6 evidence artifact")
req(kev.get("tests")=="66/69 PASS" and set(kev.get("failed_tests",[]))=={"kiocore-krecentdocumenttest","kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"},"KIO Attempt6 test result")

req(kxml.get("packaging",{}).get("state")=="PASS" and kxml.get("packaging",{}).get("package_version")=="6.30.0-0supralinux5","KXMLGui canonical PASS/version")
req(kxml.get("packaging",{}).get("downstream_eligible") is True,"KXMLGui downstream eligible")
xev=(kxml.get("packaging",{}).get("evidence") or [{}])[-1]
req(xev.get("workflow_run")==WORKFLOW and xev.get("job_id")==107754320420,"KXMLGui Attempt6 workflow/job")
req(xev.get("artifact_id")==10824512023 and xev.get("artifact_sha256")=="da271b820ffe62c1bd4bf4e59874582ff482eb89b9e42d6bf6ae28c8cccc74e6","KXMLGui Attempt6 artifact")
req(xev.get("tests")=="7/7 PASS" and xev.get("python_import")=="PASS","KXMLGui Attempt6 tests/import")

for node_id in BLOCKED:
    p=nodes[node_id].get("packaging",{})
    req(p.get("state")=="BLOCKED" and p.get("downstream_eligible") is False,f"{node_id}: BLOCKED packaging state")
    req(p.get("blocked_by")==["kio"],f"{node_id}: blocked by KIO current FAIL")

snap=tier3.get("level1_snapshot",{})
req(snap.get("pass")==12 and snap.get("pending")==1 and snap.get("current_fail")==1 and snap.get("blocked")==6,"Tier3 Attempt6 snapshot counts")
req(snap.get("runtime_pending")==["knewstuff"] and snap.get("current_fail_nodes")==["kio"],"Tier3 Attempt6 pending/FAIL snapshot")
req(snap.get("blocked_nodes")==BLOCKED and snap.get("workflow_run")==WORKFLOW and snap.get("commit")==COMMIT,"Tier3 Attempt6 snapshot evidence")

ar=tier3.get("active_remediation",{})
req(ar.get("round")==10 and ar.get("status")=="attempt6-complete-mixed","Tier3 Attempt6 closed remediation state")
req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 Attempt6 execution closed")
req(ar.get("current_attempt")==6 and ar.get("validation_workflow_run")==WORKFLOW and ar.get("validation_commit")==COMMIT,"Tier3 Attempt6 closure evidence")
req(ar.get("remaining_failed_nodes")==["kio"] and ar.get("blocked_nodes")==BLOCKED and ar.get("canonical_promotions")==1,"Tier3 Attempt6 transition semantics")
req(ar.get("next_gate")==NEXT_GATE,"Tier3 Attempt6 next gate")

req(level1.get("state")=="attempt6-closed-mixed" and level1.get("execution_authorized") is False,"Level1 Attempt6 closed state")
req(level1.get("canonical_snapshot")==SNAPSHOT and level1.get("next_gate")==NEXT_GATE and level1.get("current_attempt")==6,"Level1 Attempt6 closed snapshot/gate")
req(level1.get("activation",{}).get("status")=="CLOSED-MIXED" and level1.get("activation",{}).get("workflow_run")==WORKFLOW,"Level1 Attempt6 activation closed")
req(level1.get("nodes",{}).get("kio",{}).get("state")=="FAIL","Level1 KIO FAIL")
req(level1.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","Level1 KXMLGui PASS")

summary=level1.get("attempt6_summary",{})
req(summary.get("workflow_run")==WORKFLOW and summary.get("commit")==COMMIT and summary.get("result")=="MIXED","Level1 Attempt6 summary identity")
req(summary.get("workflow_jobs")=={"success":1,"fail":1} and summary.get("pass_nodes")==["kxmlgui"] and summary.get("failed_nodes")==["kio"],"Level1 Attempt6 job result")
req(summary.get("blocked_nodes")==BLOCKED and summary.get("canonical_promotions")==1 and summary.get("next_gate")==NEXT_GATE,"Level1 Attempt6 summary transition")
req(summary.get("rootfs",{}).get("artifact_id")==10824730747 and summary.get("rootfs",{}).get("artifact_sha256")=="3ece315a28ecd5070a1e2139db45af8483126aebbe8f99bce1cf25999e218234","Level1 Attempt6 rootfs artifact")

hist=ledger.get("campaign_history",[])
req(len(hist)>=6,"Attempt6 ledger campaign length")
if len(hist)>=6:
    h=hist[-1]
    req(h.get("attempt")==6 and h.get("workflow_run")==WORKFLOW and h.get("commit")==COMMIT and h.get("result")=="MIXED","Attempt6 ledger campaign identity")
    req(h.get("workflow_jobs")=={"success":1,"fail":1} and h.get("pass_nodes")==["kxmlgui"] and h.get("failed_nodes")==["kio"],"Attempt6 ledger mixed result")
    req(h.get("blocked_nodes")==BLOCKED and h.get("canonical_promotions")==1 and h.get("next_gate")==NEXT_GATE,"Attempt6 ledger transition")

for node_id, result, job, artifact, digest, version in (
    ("kio","FAIL",107754320435,10824413911,"61f2c1ad261fcc4fae4cd8064d71606af42542f5ab735a672e6ff77f6b2f5861","6.30.0-0supralinux6"),
    ("kxmlgui","PASS",107754320420,10824512023,"da271b820ffe62c1bd4bf4e59874582ff482eb89b9e42d6bf6ae28c8cccc74e6","6.30.0-0supralinux5"),
):
    attempts=ledger.get("nodes",{}).get(node_id,[])
    req(len(attempts)>=6,f"{node_id}: Attempt6 ledger entry")
    if len(attempts)>=6:
        x=attempts[-1]
        req(x.get("attempt")==6 and x.get("result")==result and x.get("workflow_run")==WORKFLOW and x.get("job_id")==job,f"{node_id}: Attempt6 ledger identity")
        req(x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest and x.get("package_version")==version,f"{node_id}: Attempt6 ledger artifact/version")

dxml=dag.get("nodes",{}).get("kxmlgui",{})
req(dxml.get("tier")==3 and dxml.get("state")=="PASS" and dxml.get("downstream_eligible") is True,"KXMLGui canonical DAG promotion")
req(dxml.get("package_version")=="6.30.0-0supralinux5" and dxml.get("artifact_id")==10824512023 and dxml.get("artifact_sha256")=="da271b820ffe62c1bd4bf4e59874582ff482eb89b9e42d6bf6ae28c8cccc74e6","KXMLGui DAG evidence")
req("kio" not in dag.get("nodes",{}),"KIO FAIL must not enter canonical DAG")

ac=contracts.get("active_remediation",{})
req(ac.get("round")==10 and ac.get("status")=="attempt6-complete-mixed","contract Attempt6 closed state")
req(ac.get("execution_authorized") is False and ac.get("next_gate")==NEXT_GATE,"contract Attempt6 closed gate")
req(ac.get("validation_workflow_run")==WORKFLOW and ac.get("validation_commit")==COMMIT,"contract Attempt6 closure evidence")

am=materialization.get("active_remediation",{})
req(am.get("round")==10 and am.get("status")=="PASS","Round10 source materialization remains PASS")
req(am.get("workflow_run")==36002910277 and am.get("promoted_nodes")==["kio","kxmlgui"],"Round10 materialization retained evidence")
req(am.get("next_gate")==NEXT_GATE,"materialization closure handoff")
req(materialization.get("evidence_summary",{}).get("next_gate")==NEXT_GATE,"materialization summary closure handoff")

req(tier3.get("support_components",{}).get("next_gate")=="tier3-build-level1","support sub-DAG remains closed/PASS")
req(level1.get("stable_promotion_requires_explicit_user_approval") is True,"Level1 stable approval policy")
req(materialization.get("stable_promotion_requires_explicit_user_approval") is True,"materialization stable approval policy")
req(contracts.get("stable_promotion_requires_explicit_user_approval") is True,"contract stable approval policy")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 Level 1 Attempt 6 closure: PASS")
print(SNAPSHOT)
print("next_gate="+NEXT_GATE)
