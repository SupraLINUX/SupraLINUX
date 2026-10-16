#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/"manifests/kde-tier3-build-level3-attempts.json").read_text())
errors=[]
def req(v,m):
    if not v: errors.append(m)

RUN=36645760261
COMMIT="a9bb6b507cdf98bbf81f61524ed594a4f1e5e000"
ROOTFS={"job_id":109668495106,"artifact_id":11068855519,"artifact_sha256":"f3a25f7c68905b206281d023530031f01648228d6ca4974d6c478e0746cdc132"}
K={"job_id":109668677528,"artifact_id":11068519665,"artifact_sha256":"96361a7771ea352dd01ffb9a032e37ed66399cb538f98137948c595ff043a69e"}
P={"job_id":109668677478,"artifact_id":11068364147,"artifact_sha256":"b76383545d2bd8eb7d64cf1fd27e57d081eb05b385f88529ad50069c1e0c49f3"}

hist=[x for x in a.get("campaign_history",[]) if x.get("attempt")==3]
req(len(hist)==1,"Level3 Attempt3 immutable campaign record")
h=hist[0] if hist else {}
req(h.get("workflow_run")==RUN and h.get("commit")==COMMIT and h.get("result")=="PARTIAL","Level3 Attempt3 identity/result")
req(h.get("package_attempted") is True and h.get("rootfs")==ROOTFS,"Level3 Attempt3 valid package execution/rootfs")
req(h.get("workflow_jobs")=={"success":1,"fail":1},"Level3 Attempt3 job counts")
req(h.get("primary_classification")=={"PASS":["ktexteditor"],"FAIL":[],"INFRA_INVALID":["purpose"]},"Level3 Attempt3 classification")
req(h.get("canonical_promotions")==1 and h.get("canonical_failures")==0 and h.get("canonical_failures_retained")==1,"Level3 Attempt3 canonical effects")
req(h.get("next_attempt")==4 and h.get("next_gate")=="tier3-build-level3-attempt4-planning-validation","Level3 Attempt3 next gate")

kr=[x for x in a.get("nodes",{}).get("ktexteditor",[]) if x.get("attempt")==3]
req(len(kr)==1,"KTextEditor Attempt3 immutable record")
k=kr[0] if kr else {}
req(k.get("workflow_run")==RUN and k.get("commit")==COMMIT and k.get("job_id")==K["job_id"],"KTextEditor Attempt3 identity")
req(k.get("artifact_id")==K["artifact_id"] and k.get("artifact_sha256")==K["artifact_sha256"],"KTextEditor Attempt3 artifact")
req(k.get("result")=="PASS" and k.get("build_result")=="PASS" and k.get("stage")=="complete" and k.get("exit_code")==0,"KTextEditor Attempt3 PASS")
req(k.get("package_attempted") is True and k.get("package_state_effect")=="PASS" and k.get("canonical_state_effect")=="PASS","KTextEditor Attempt3 state effect")
req(k.get("package_version")=="6.30.0-0supralinux3" and k.get("tests")=="77/77 PASS","KTextEditor Attempt3 version/tests")
req(k.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and k.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],"KTextEditor Attempt3 rootfs")

pr=[x for x in a.get("nodes",{}).get("purpose",[]) if x.get("attempt")==3]
req(len(pr)==1,"Purpose Attempt3 immutable record")
p=pr[0] if pr else {}
req(p.get("workflow_run")==RUN and p.get("commit")==COMMIT and p.get("job_id")==P["job_id"],"Purpose Attempt3 identity")
req(p.get("artifact_id")==P["artifact_id"] and p.get("artifact_sha256")==P["artifact_sha256"],"Purpose Attempt3 artifact")
req(p.get("result")=="INFRA_INVALID" and p.get("raw_result")=="FAIL" and p.get("build_result")=="PASS","Purpose Attempt3 validation classification")
req(p.get("stage")=="buildinfo-predecessor-proof" and p.get("exit_code")==1 and p.get("package_attempted") is True,"Purpose Attempt3 post-build stage")
req(p.get("package_state_effect")=="none" and p.get("canonical_state_effect")=="retain-attempt2-FAIL","Purpose Attempt3 no canonical failure")
req(p.get("package_version")=="6.30.0-0supralinux3" and p.get("tests")=="3/3 PASS" and p.get("sbuild_status")=="successful","Purpose Attempt3 successful build/tests")
req(p.get("validation_result")=="INFRA_INVALID" and p.get("validation_mechanism")=="buildinfo-predecessor-proof-contract","Purpose Attempt3 validation incident")
req(p.get("incorrect_expected_package")=="libkf6prison-dev" and p.get("actual_declared_build_dependency")=="qml6-module-org-kde-prison" and p.get("actual_proven_version")=="6.30.0-0supralinux1","Purpose Attempt3 proof mismatch")
req(p.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and p.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],"Purpose Attempt3 rootfs")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 3 Attempt 3 historical closure: PASS")
print("classification=KTextEditor:PASS Purpose:INFRA_INVALID")
print("canonical=19 PASS / 0 pending / 1 current FAIL / 0 BLOCKED")
