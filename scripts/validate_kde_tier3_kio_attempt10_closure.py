#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
# Historical validator: validate frozen Attempt 10 evidence only, never current Level 2 live state.
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
T=load("manifests/kde-frameworks-tier3.json"); D=load("manifests/kde-dag.json")
L=load("manifests/kde-tier3-build-level1.json"); A=load("manifests/kde-tier3-build-level1-attempts.json")
C=load("manifests/kde-tier3-package-contracts.json"); M=load("manifests/kde-tier3-materialization.json")
R=load("manifests/kde-tier3-kio-attempt10-remediation.json")
RUN=36425867815; COMMIT="dc7cedb37689eb6eb27b6034b58584c33985a5b0"; NEXT="tier3-build-level2-planning"
ROOTFS={"artifact_id":10971154003,"artifact_sha256":"963ca24b1ef3e5b97cb0a52d767ae22696f21d16921315690b08266756ee1103"}
KIO_JOB=108939890139; KIO_ART=10972557457; KIO_SHA="700a7abebfaca99ae76e36cfb8f54798694732f248b0002224025cfc80d94056"; KIO_VERSION="6.30.0-0supralinux10"
KXML_JOB=108939889724; KXML_ART=10971509790; KXML_SHA="a4a5bac1ca996792cc9d44e20d68d451ac61ea0a30811781260299bf87a04c00"; KXML_VERSION="6.30.0-0supralinux5"
nodes={n["id"]:n for n in T.get("nodes",[])}
k=nodes["kio"]; x=nodes["kxmlgui"]
req(k.get("state")=="PASS" and k.get("packaging",{}).get("state")=="PASS" and k.get("packaging",{}).get("package_version")==KIO_VERSION and k.get("packaging",{}).get("downstream_eligible") is True,"canonical KIO PASS/-10")
kp=[e for e in k.get("packaging",{}).get("evidence",[]) if e.get("result")=="PASS" and e.get("package_state_effect")=="PASS"]
req(len(kp)==1 and kp[0].get("workflow_run")==RUN and kp[0].get("job_id")==KIO_JOB and kp[0].get("artifact_id")==KIO_ART and kp[0].get("artifact_sha256")==KIO_SHA,"canonical KIO promotion evidence")
req(kp[0].get("tests")=="69/69 PASS" and kp[0].get("lintian")=="PASS-errors" and kp[0].get("apt_check")=="PASS" and kp[0].get("abi_contract")=="PASS" and kp[0].get("cmake_consumer")=="PASS","canonical KIO package gates")
req(kp[0].get("provider_closure_artifact_validation")=="PASS" and kp[0].get("declared_runtime_input_proof")=="PASS" and kp[0].get("buildinfo_predecessor_proof")=="PASS","canonical KIO closure/provenance gates")
req(x.get("state")=="PASS" and x.get("packaging",{}).get("package_version")==KXML_VERSION and x.get("packaging",{}).get("downstream_eligible") is True,"canonical KXMLGui PASS/-5")
xr=[e for e in x.get("packaging",{}).get("evidence",[]) if e.get("workflow_run")==RUN]
req(len(xr)==1 and xr[0].get("package_state_effect")=="PASS-revalidation" and xr[0].get("artifact_id")==KXML_ART and xr[0].get("artifact_sha256")==KXML_SHA,"KXMLGui Attempt10 revalidation evidence")
req(xr[0].get("tests")=="7/7 PASS" and xr[0].get("python_import")=="PASS","KXMLGui Attempt10 tests/import")
snap=T.get("level1_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(13,7,0,0),"canonical 13/7/0/0 snapshot")
req(snap.get("runtime_pending")==["knewstuff"] and snap.get("workflow_run")==RUN and snap.get("commit")==COMMIT,"canonical closure snapshot evidence")
dk=D.get("nodes",{}).get("kio",{})
req(dk.get("state")=="PASS" and dk.get("downstream_eligible") is True and dk.get("package_version")==KIO_VERSION,"DAG KIO PASS")
req(dk.get("attempt_ledger")=="manifests/kde-tier3-build-level1-attempts.json","DAG KIO ledger")
dp=dk.get("evidence",[])
req(len(dp)==1 and dp[0].get("workflow_run")==RUN and dp[0].get("artifact_id")==KIO_ART and dp[0].get("tests")=="69/69 PASS","DAG KIO evidence")
req(L.get("state")=="PASS" and L.get("execution_authorized") is False and L.get("current_attempt")==10 and L.get("next_gate")==NEXT,"Level1 closure")
req(L.get("nodes",{}).get("kio",{}).get("state")=="PASS" and L.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","Level1 node PASS states")
hist=[e for e in A.get("campaign_history",[]) if e.get("attempt")==10]
req(len(hist)==1 and hist[0].get("workflow_run")==RUN and hist[0].get("result")=="PASS" and hist[0].get("workflow_jobs")=={"success":2,"fail":0} and hist[0].get("canonical_promotions")==1,"Attempt10 campaign ledger")
ki=[e for e in A.get("nodes",{}).get("kio",[]) if e.get("attempt")==10]
kx=[e for e in A.get("nodes",{}).get("kxmlgui",[]) if e.get("attempt")==10]
req(len(ki)==1 and ki[0].get("result")=="PASS" and ki[0].get("tests")=="69/69 PASS" and ki[0].get("artifact_id")==KIO_ART,"Attempt10 KIO ledger")
req(len(kx)==1 and kx[0].get("result")=="PASS" and kx[0].get("tests")=="7/7 PASS" and kx[0].get("python_import")=="PASS" and kx[0].get("package_state_effect")=="PASS-revalidation","Attempt10 KXMLGui ledger")
rr=R.get("attempt10_result",{})
req(R.get("status")=="attempt10-closed-PASS" and R.get("execution_authorized") is False and R.get("package_execution_authorized") is False,"Attempt10 historical closure")
req(rr.get("workflow_run")==RUN and rr.get("commit")==COMMIT and rr.get("result")=="PASS" and rr.get("rootfs")==ROOTFS,"Attempt10 result identity")
req(rr.get("kio",{}).get("artifact_id")==KIO_ART and rr.get("kio",{}).get("tests")=="69/69 PASS" and rr.get("kio",{}).get("lintian")=="PASS-errors","Attempt10 KIO result")
req(rr.get("kxmlgui",{}).get("artifact_id")==KXML_ART and rr.get("kxmlgui",{}).get("tests")=="7/7 PASS" and rr.get("kxmlgui",{}).get("python_import")=="PASS","Attempt10 KXMLGui result")
req(C.get("active_remediation",{}).get("status")=="attempt10-complete-PASS" and C.get("active_remediation",{}).get("execution_authorized") is False,"contracts closure")
req(M.get("state")=="PASS" and M.get("active_remediation",{}).get("status")=="attempt10-complete-PASS","materialization closure")
for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Attempt10")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 10 closure: PASS")
print("KIO 6.30.0-0supralinux10 = PASS; 69/69 tests; package gates PASS")
print("KXMLGui 6.30.0-0supralinux5 = PASS revalidation")
print("canonical=13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED")
print("next_gate="+NEXT)
