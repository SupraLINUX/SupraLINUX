#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
a=json.loads((ROOT/"manifests/kde-tier3-build-level2-attempts.json").read_text())
RUN=36503684811
COMMIT="fdc9d93fcc6ec9065f173d5d47b2bca928bf6f06"
ROOTFS={"job_id":109200172739,"artifact_id":11006221515,"artifact_sha256":"4676e81943a42a265b0649e87a5da668f27975d768bf62eedee99af9b79f0d84"}
ART={"job_id":109200408066,"artifact_id":11006467074,"artifact_sha256":"4dc1045a571b0cb05e61e25600a56fbdc59e5a80cde071cc3ad6af78f7b884a7","version":"6.30.0-0supralinux3"}
hist=[x for x in a.get("campaign_history",[]) if x.get("attempt")==5]
req(len(hist)==1,"Attempt5 immutable campaign record")
h=hist[0] if hist else {}
req(h.get("workflow_run")==RUN and h.get("commit")==COMMIT and h.get("result")=="PASS","Attempt5 identity/result")
req(h.get("package_attempted") is True and h.get("rootfs")==ROOTFS,"Attempt5 valid package execution/rootfs")
req(h.get("workflow_jobs")=={"success":1,"fail":0},"Attempt5 job result counts")
req(h.get("primary_classification")=={"PASS":["kcmutils"],"FAIL":[],"INFRA_INVALID":[]},"Attempt5 package classification")
req(h.get("canonical_promotions")==1 and h.get("canonical_failures")==0,"Attempt5 canonical effect")
req(h.get("next_gate")=="tier3-knewstuff-runtime-validation-planning","Attempt5 historical next gate")
rows=[x for x in a.get("nodes",{}).get("kcmutils",[]) if x.get("attempt")==5]
req(len(rows)==1,"KCMUtils Attempt5 immutable node record")
x=rows[0] if rows else {}
req(x.get("workflow_run")==RUN and x.get("commit")==COMMIT and x.get("job_id")==ART["job_id"],"KCMUtils Attempt5 run/job")
req(x.get("artifact_id")==ART["artifact_id"] and x.get("artifact_sha256")==ART["artifact_sha256"],"KCMUtils Attempt5 artifact")
req(x.get("result")=="PASS" and x.get("build_result")=="PASS" and x.get("package_version")==ART["version"],"KCMUtils Attempt5 result/version")
req(x.get("stage")=="complete" and x.get("exit_code")==0 and x.get("package_attempted") is True and x.get("package_state_effect")=="PASS","KCMUtils Attempt5 valid package PASS")
req(x.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and x.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],"KCMUtils Attempt5 rootfs proof")
for key,val in {
 "tests":"6/6 PASS","lintian":"PASS-errors","apt_check":"PASS","abi_contract":"PASS",
 "cmake_consumer":"PASS","buildinfo_predecessor_proof":"PASS",
 "provider_closure_artifact_validation":"PASS","declared_runtime_input_proof":"PASS",
 "selected_profile_proof":"PASS","python_import":"not-applicable","qml_payload":"PASS"
}.items():
    req(x.get(key)==val,"KCMUtils Attempt5 "+key)
req(x.get("downstream_eligible") is True and x.get("claim")=="hosted-clean-package-preflight" and x.get("authoritative") is False,"KCMUtils Attempt5 hosted preflight classification")
req(x.get("artifacts",{}).get("kf6-kcmutils_6.30.0-0supralinux3_amd64.buildinfo")=="1f05be8d5ebb4e0a4c68a80c8047b19f266dba351d01e891ef40ca34ac99127f","KCMUtils Attempt5 buildinfo hash")
req(x.get("artifacts",{}).get("libkf6kcmutilsquick6_6.30.0-0supralinux3_amd64.deb")=="f52c71956240d29bdabdbffba7f01bea342845f776802687fb469b0195d7c315","KCMUtils Attempt5 quick library hash")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 Attempt 5 historical closure: PASS")
print("workflow_run=36503684811 result=PASS promotions=1")
print("historical_snapshot=17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED")
print("historical_next_gate=tier3-knewstuff-runtime-validation-planning")
