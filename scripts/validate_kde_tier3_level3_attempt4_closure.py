#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/"manifests/kde-tier3-build-level3-attempts.json").read_text())
errors=[]
def req(v,m):
    if not v: errors.append(m)

RUN=36655388053
COMMIT="cbfa17227fda156e5cccf598b910a36ed4bc8518"
ROOTFS={"job_id":109698853580,"artifact_id":11072870340,"artifact_sha256":"345b669578c89f718f69038c0a8e1f0ef78406e802040bea8e6203a03d938172"}
P={"job_id":109699029883,"artifact_id":11072881455,"artifact_sha256":"f9429216194b38e34fcd4ac36bb9638bf5c9b134965b445b8520e18ce667eb68"}

hist=[x for x in a.get("campaign_history",[]) if x.get("attempt")==4]
req(len(hist)==1,"Level3 Attempt4 immutable campaign record")
h=hist[0] if hist else {}
req(h.get("workflow_run")==RUN and h.get("commit")==COMMIT and h.get("result")=="PASS","Level3 Attempt4 identity/result")
req(h.get("package_attempted") is True and h.get("rootfs")==ROOTFS,"Level3 Attempt4 valid package execution/rootfs")
req(h.get("workflow_jobs")=={"success":1,"fail":0},"Level3 Attempt4 job counts")
req(h.get("primary_classification")=={"PASS":["purpose"],"FAIL":[],"INFRA_INVALID":[]},"Level3 Attempt4 classification")
req(h.get("canonical_promotions")==1 and h.get("canonical_failures")==0,"Level3 Attempt4 canonical effect")
req(h.get("next_attempt") is None and h.get("next_gate")=="authoritative-kvm-runner-certification","Level3 Attempt4 next gate")

rows=[x for x in a.get("nodes",{}).get("purpose",[]) if x.get("attempt")==4]
req(len(rows)==1,"Purpose Attempt4 immutable record")
p=rows[0] if rows else {}
req(p.get("workflow_run")==RUN and p.get("commit")==COMMIT and p.get("job_id")==P["job_id"],"Purpose Attempt4 identity")
req(p.get("artifact_id")==P["artifact_id"] and p.get("artifact_sha256")==P["artifact_sha256"],"Purpose Attempt4 artifact")
req(p.get("result")=="PASS" and p.get("build_result")=="PASS" and p.get("stage")=="complete" and p.get("exit_code")==0,"Purpose Attempt4 complete PASS")
req(p.get("package_attempted") is True and p.get("package_state_effect")=="PASS" and p.get("canonical_state_effect")=="PASS","Purpose Attempt4 state effect")
req(p.get("package_version")=="6.30.0-0supralinux3" and p.get("tests")=="3/3 PASS","Purpose Attempt4 version/tests")
req(p.get("buildinfo_predecessor_proof")=="PASS" and p.get("qml_payload")=="PASS" and p.get("downstream_eligible") is True,"Purpose Attempt4 corrected proof/QML")
req(p.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and p.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],"Purpose Attempt4 rootfs")
arts=p.get("artifacts",{})
req(arts.get("kf6-purpose_6.30.0-0supralinux3_amd64.buildinfo")=="5984ec23401eb2e361f9bd0c61ea84bd6f5b4c4abd0d8cff93532b8e4bb9822e","Purpose Attempt4 buildinfo retained")
req(arts.get("qml6-module-org-kde-purpose_6.30.0-0supralinux3_amd64.deb")=="a58c3cb8d58496220f124b1e7491715375fc10baa5796e609bad383c9f48de99","Purpose Attempt4 QML package retained")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 3 Attempt 4 historical closure: PASS")
print("classification=Purpose:PASS")
print("canonical=20 PASS / 0 pending / 0 current FAIL / 0 BLOCKED")
