#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
a=json.loads((ROOT/"manifests/kde-tier3-build-level3-attempts.json").read_text())
m=json.loads((ROOT/"manifests/kde-tier3-build-level3.json").read_text())
t=json.loads((ROOT/"manifests/kde-frameworks-tier3.json").read_text())
RUN=36607647059
COMMIT="2692489bdb861520181df486c524efb9cdf47d60"
ROOTFS={"job_id":109541198352,"artifact_id":11051807633,"artifact_sha256":"08eb26b3d264c79e26dd0f5e1cb6fe543a16e1f2be0f713bab5fee45cabdbd83"}
ART={
 "ktexteditor":{"job_id":109541487937,"artifact_id":11052302105,"artifact_sha256":"d66ad916ef3f4e38e2ab3dc436fba3ac7dcb6f1e59603399c5debaebfa6a5458","version":"6.30.0-0supralinux1","tests":"64/77 PASS","failure_substage":"ctest-encoding-diffs-and-katedocument-save-timeout"},
 "purpose":{"job_id":109541487871,"artifact_id":11052225512,"artifact_sha256":"cff8b75aac023985ba5f4c3c4d429665b268cd65865d65969724408ec2cc5122","version":"6.30.0-0supralinux1","tests":"1/3 PASS","failure_substage":"ctest-kio-file-protocol-and-xcb-display"},
}
hist=[x for x in a.get("campaign_history",[]) if x.get("attempt")==1]
req(len(hist)==1,"Level3 Attempt1 immutable campaign record")
h=hist[0] if hist else {}
req(h.get("workflow_run")==RUN and h.get("commit")==COMMIT and h.get("result")=="FAIL","Level3 Attempt1 identity/result")
req(h.get("package_attempted") is True and h.get("rootfs")==ROOTFS,"Level3 Attempt1 valid package execution/rootfs")
req(h.get("workflow_jobs")=={"success":0,"fail":2},"Level3 Attempt1 job counts")
req(h.get("primary_classification")=={"PASS":[],"FAIL":["ktexteditor","purpose"],"INFRA_INVALID":[]},"Level3 Attempt1 classification")
req(h.get("canonical_failures")==2 and h.get("canonical_promotions")==0 and h.get("next_attempt")==2,"Level3 Attempt1 canonical effect")
for node,exp in ART.items():
    rows=[x for x in a.get("nodes",{}).get(node,[]) if x.get("attempt")==1]
    req(len(rows)==1,node+": Attempt1 immutable node record")
    x=rows[0] if rows else {}
    req(x.get("workflow_run")==RUN and x.get("commit")==COMMIT and x.get("job_id")==exp["job_id"],node+": Attempt1 run/job")
    req(x.get("artifact_id")==exp["artifact_id"] and x.get("artifact_sha256")==exp["artifact_sha256"],node+": Attempt1 artifact")
    req(x.get("result")=="FAIL" and x.get("stage")=="sbuild" and x.get("exit_code")==2 and x.get("package_attempted") is True,node+": real sbuild FAIL")
    req(x.get("failure_substage")==exp["failure_substage"] and x.get("package_version")==exp["version"] and x.get("tests")==exp["tests"],node+": failure identity/version/tests")
    req(x.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and x.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],node+": rootfs proof")
req(m.get("state")=="FAIL" and m.get("execution_authorized") is False and m.get("current_attempt")==1 and m.get("next_attempt")==2,"Level3 Attempt1 closed manifest state")
req(m.get("canonical_snapshot")=="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED" and m.get("next_gate")=="tier3-build-level3-attempt1-remediation-definition","Level3 Attempt1 closed snapshot/gate")
req(t.get("build_level3",{}).get("status")=="attempt1-closed-FAIL" and t.get("build_level3",{}).get("execution_authorized") is False,"Tier3 live Level3 closure")
req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level3-attempt1-closed-FAIL","Tier3 live closure gate")
nodes={x["id"]:x for x in t.get("nodes",[])}
for node in ART:
    req(nodes.get(node,{}).get("state")=="FAIL" and nodes.get(node,{}).get("packaging",{}).get("state")=="FAIL",node+": canonical FAIL")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 3 Attempt 1 historical closure: PASS")
print("workflow_run=36607647059 result=FAIL canonical_failures=2")
print("snapshot=18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED")
