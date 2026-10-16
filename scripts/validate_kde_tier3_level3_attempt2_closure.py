#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

a=load("manifests/kde-tier3-build-level3-attempts.json")
m=load("manifests/kde-tier3-build-level3.json")
t=load("manifests/kde-frameworks-tier3.json")

RUN=36639418961
COMMIT="9fd5041053a176fdafcb3939e57a0ff2dd26d91e"
SNAP="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
ROOTFS={"job_id":109648205853,"artifact_id":11066320451,"artifact_sha256":"d6ec90546a42d24d6561e49c9684ca03716b9c0ce4b98d7d95415571e3f4bb85"}
ART={"ktexteditor":{"job_id":109648411937,"artifact_id":11066168089,"artifact_sha256":"74fd2819b9110d7a8ce35ca2a2c8a89fb1a9b31548e32e05de2cb0e9426234e6","package_version":"6.30.0-0supralinux2","tests":"76/77 PASS","failure_substage":"ctest-katedocument-testAboutToSave-relative-source-path","observation":"Encoding race remediation passed; only katedocument_test::testAboutToSave failed because the test tried to open relative __FILE__ from the reproducible build working directory."},"purpose":{"job_id":109648412196,"artifact_id":11066102772,"artifact_sha256":"adf13dd09a0ebd4b001f51c83cfe2b19360fa482b6c73c1a1ab579e7914e0a19","package_version":"6.30.0-0supralinux2","tests":"1/3 PASS","failure_substage":"ctest-purpose-external-http-under-network-disabled-sbuild","observation":"KIO file workers and the offscreen Qt platform were resolved; alternativesmodeltest and menutest still used http://kde.org and failed under the intentionally network-disabled sbuild environment."}}

hist=[x for x in a.get("campaign_history",[]) if x.get("attempt")==2]
req(len(hist)==1,"Level3 Attempt2 immutable campaign record")
h=hist[0] if hist else {}
req(h.get("workflow_run")==RUN and h.get("commit")==COMMIT and h.get("result")=="FAIL","Level3 Attempt2 identity/result")
req(h.get("package_attempted") is True and h.get("rootfs")==ROOTFS,"Level3 Attempt2 valid package execution/rootfs")
req(h.get("workflow_jobs")=={"success":0,"fail":2},"Level3 Attempt2 job counts")
req(h.get("primary_classification")=={"PASS":[],"FAIL":["ktexteditor","purpose"],"INFRA_INVALID":[]},"Level3 Attempt2 classification")
req(h.get("canonical_failures")==2 and h.get("canonical_promotions")==0 and h.get("next_attempt")==3,"Level3 Attempt2 canonical effect")

for node,exp in ART.items():
    rows=[x for x in a.get("nodes",{}).get(node,[]) if x.get("attempt")==2]
    req(len(rows)==1,node+": Attempt2 immutable node record")
    x=rows[0] if rows else {}
    req(x.get("workflow_run")==RUN and x.get("commit")==COMMIT and x.get("job_id")==exp["job_id"],node+": Attempt2 run/job")
    req(x.get("artifact_id")==exp["artifact_id"] and x.get("artifact_sha256")==exp["artifact_sha256"],node+": Attempt2 artifact")
    req(x.get("result")=="FAIL" and x.get("stage")=="sbuild" and x.get("exit_code")==2 and x.get("package_attempted") is True,node+": real sbuild FAIL")
    req(x.get("failure_substage")==exp["failure_substage"] and x.get("package_version")==exp["package_version"] and x.get("tests")==exp["tests"],node+": failure identity/version/tests")
    req(x.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and x.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],node+": rootfs proof")
    req(x.get("observation")==exp["observation"],node+": retained observation")

def validate_summary(s,label):
    req(s.get("workflow_run")==RUN and s.get("commit")==COMMIT and s.get("result")=="FAIL",label+": identity/result")
    req(s.get("package_attempted") is True and s.get("package_state_effect")==f"2 FAIL; canonical {SNAP}",label+": package state effect")
    req(s.get("rootfs")==ROOTFS and s.get("workflow_jobs")=={"success":0,"fail":2},label+": rootfs/jobs")
    req(s.get("primary_classification")=={"PASS":[],"FAIL":["ktexteditor","purpose"],"INFRA_INVALID":[]},label+": classification")
    req(s.get("canonical_promotions")==0 and s.get("canonical_failures")==2 and s.get("next_attempt")==3,label+": canonical effect")
    req(s.get("next_gate")=="tier3-build-level3-attempt2-remediation-definition",label+": historical next gate")
    ne=s.get("node_evidence",{})
    for node,exp in ART.items():
        x=ne.get(node,{})
        req(x.get("job_id")==exp["job_id"] and x.get("artifact_id")==exp["artifact_id"] and x.get("artifact_sha256")==exp["artifact_sha256"],label+": "+node+" artifact")
        req(x.get("package_version")==exp["package_version"] and x.get("stage")=="sbuild" and x.get("exit_code")==2 and x.get("package_attempted") is True,label+": "+node+" execution/version")
        req(x.get("failure_substage")==exp["failure_substage"] and x.get("tests")==exp["tests"] and x.get("observation")==exp["observation"],label+": "+node+" failure evidence")

validate_summary(m.get("attempt2_summary",{}),"Level3 manifest Attempt2 summary")
validate_summary(t.get("build_level3",{}).get("attempt2_evidence",{}),"Tier3 canonical Attempt2 evidence")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 3 Attempt 2 historical closure: PASS")
print("workflow_run=36639418961 result=FAIL canonical_failures=2")
print("snapshot=18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED")
