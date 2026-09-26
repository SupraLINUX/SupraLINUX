#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
M=load("manifests/kde-tier3-materialization.json")
A=load("manifests/kde-tier3-build-level1-attempts.json")
R=load("manifests/kde-tier3-kio-round18-remediation.json")
D=load("manifests/kde-dag.json")

RUN=36238357510
COMMIT="77129c31006ac746d0d5d1d249ed7d1aaf6cf530"
ROOTFS_ID=10904512642
ROOTFS_SHA="d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe"
KIO_JOB=108394325161
KIO_ART=10905267300
KIO_SHA="9f95e2b8e3330ee4f1b275eb059736b87fa57d7752602aa598cb313659cae53f"
KXML_JOB=108394325149
KXML_ART=10905212105
KXML_SHA="297d8d91e52f82cd6713c30072a8f2deff80d73647b9c93c1b89263e5f21d441"
NEXT="tier3-round19-kio-diagnostic-definition"
BLOCKED={"baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"}
PASS={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}

p=T.get("discovery_policy",{})
req(p.get("phase")=="build-level1-planning","Attempt8 closure phase")
req(p.get("package_builds")=="tier3-level1-attempt8-closed","Attempt8 closure package gate")
req(p.get("remediation")=="round19-kio-diagnostic-definition-pending","Attempt8 closure marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS,"canonical PASS set")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"canonical pending set")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"canonical FAIL set")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==BLOCKED,"canonical BLOCKED set")
req(nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux8","canonical KIO FAIL/-8")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO ineligible")
req(nodes["kxmlgui"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux5" and nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"KXMLGui retained PASS")
req("kio" not in D.get("nodes",{}),"KIO absent from PASS DAG")

ar=T.get("active_remediation",{})
req(ar.get("status")=="attempt8-complete-mixed" and ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical Attempt8 closed")
req(ar.get("current_attempt")==8 and ar.get("next_attempt")==9 and ar.get("next_gate")==NEXT,"canonical Attempt9 handoff")
req(ar.get("validation_workflow_run")==RUN and ar.get("validation_commit")==COMMIT,"canonical Attempt8 evidence")
ev=ar.get("attempt8_evidence",{})
req(ev.get("rootfs",{}).get("artifact_id")==ROOTFS_ID and ev.get("rootfs",{}).get("artifact_sha256")==ROOTFS_SHA,"canonical rootfs")
req(ev.get("kio",{}).get("job_id")==KIO_JOB and ev.get("kio",{}).get("artifact_id")==KIO_ART and ev.get("kio",{}).get("artifact_sha256")==KIO_SHA,"canonical KIO artifact")
req(ev.get("kxmlgui",{}).get("job_id")==KXML_JOB and ev.get("kxmlgui",{}).get("artifact_id")==KXML_ART and ev.get("kxmlgui",{}).get("artifact_sha256")==KXML_SHA,"canonical KXMLGui artifact")

req(L.get("state")=="attempt8-closed-mixed" and L.get("execution_authorized") is False,"Level1 Attempt8 closed")
req(L.get("current_attempt")==8 and L.get("next_attempt")==9 and L.get("next_gate")==NEXT,"Level1 Attempt9 handoff")
req(L.get("attempt8_summary",{}).get("kio_tests")=={"total":69,"pass":67,"fail":2},"KIO 67/69")
req(L.get("attempt8_summary",{}).get("kxmlgui_tests")=={"total":7,"pass":7,"fail":0},"KXMLGui 7/7")
req(L.get("attempt8_summary",{}).get("kxmlgui_python_import")=="PASS","KXMLGui Python import")
req(L.get("nodes",{}).get("kio",{}).get("last_attempt",{}).get("attempt")==8 and L.get("nodes",{}).get("kio",{}).get("last_attempt",{}).get("result")=="FAIL","KIO Attempt8 result")
req(L.get("nodes",{}).get("kxmlgui",{}).get("last_attempt",{}).get("attempt")==8 and L.get("nodes",{}).get("kxmlgui",{}).get("last_attempt",{}).get("result")=="PASS","KXMLGui Attempt8 result")

cr=C.get("active_remediation",{})
req(cr.get("status")=="attempt8-complete-mixed" and cr.get("execution_authorized") is False and cr.get("level1_execution_authorized") is False,"contracts Attempt8 closed")
req(cr.get("current_attempt")==8 and cr.get("next_attempt")==9 and cr.get("next_gate")==NEXT,"contracts Attempt9 handoff")
kc=C.get("nodes",{}).get("kio",{})
rels=[(x.get("action"),x.get("package") or x.get("relation"),x.get("classification")) for x in kc.get("source_build_relation_overrides",[])]
req(("ensure","qt6-svg-plugins <!nocheck>","upstream-test-environment-provider") in rels,"SVG provider retained")
req(kc.get("test_policy",{}).get("failures_fatal") is True,"upstream tests remain fatal")

req(M.get("state")=="PASS","source materialization stays PASS")
req(M.get("nodes",{}).get("kio",{}).get("package_version")=="6.30.0-0supralinux8","KIO -8 materialization retained")
req(M.get("active_remediation",{}).get("next_gate")==NEXT,"materialization handoff")

hist=A.get("campaign_history",[])
req(hist and hist[-1].get("attempt")==8 and hist[-1].get("workflow_run")==RUN and hist[-1].get("result")=="MIXED","Attempt8 ledger campaign")
req(hist[-1].get("workflow_jobs")=={"success":1,"fail":1} and hist[-1].get("canonical_promotions")==0,"Attempt8 mixed/no promotion")
ki=A.get("nodes",{}).get("kio",[])
kx=A.get("nodes",{}).get("kxmlgui",[])
req(ki and ki[-1].get("attempt")==8 and ki[-1].get("result")=="FAIL" and ki[-1].get("artifact_id")==KIO_ART,"KIO ledger Attempt8")
req(ki[-1].get("tests")=={"total":69,"pass":67,"fail":2},"KIO ledger tests")
req(kx and kx[-1].get("attempt")==8 and kx[-1].get("result")=="PASS" and kx[-1].get("artifact_id")==KXML_ART,"KXMLGui ledger Attempt8")
req(kx[-1].get("tests")=={"total":7,"pass":7,"fail":0} and kx[-1].get("python_import")=="PASS","KXMLGui ledger tests/import")

req(R.get("status")=="attempt8-closed-mixed" and R.get("execution_authorized") is False,"Round18 Attempt8 closed")
rr=R.get("attempt8_result",{})
req(rr.get("workflow_run")==RUN and rr.get("commit")==COMMIT and rr.get("result")=="MIXED","Round18 result identity")
req(rr.get("kio",{}).get("tests")=={"total":69,"pass":67,"fail":2},"Round18 KIO tests")
req(rr.get("kio",{}).get("remaining_failures",{}).get("krecentdocument"),"KRecentDocument failure retained")
req(rr.get("kio",{}).get("remaining_failures",{}).get("kdirmodel"),"KDirModel failure retained")
req(rr.get("kxmlgui",{}).get("tests")=={"total":7,"pass":7,"fail":0},"Round18 KXMLGui tests")
req(R.get("next_gate")==NEXT,"Round19 handoff")
for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round18 remediation")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 8 closure: PASS")
print("12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux8 67/69; KXMLGui=PASS 6.30.0-0supralinux5 7/7")
print("next_gate="+NEXT)
