#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def req(v,m):
    if not v: errors.append(m)
a=json.loads((ROOT/"manifests/kde-tier3-build-level2-attempts.json").read_text())
RUN=36473379324
COMMIT="35ee2761b4f6c196e9ab95e7c8eff66c6cffcce3"
ROOTFS={"job_id":109100990204,"artifact_id":10992682557,"artifact_sha256":"0dad0fc0a61d5d39bb0cc12c62d43956927657d13e67a79f9cfb6274ef690d54"}
ART={
 "baloo":{"job_id":109101309616,"artifact_id":10993001091,"artifact_sha256":"6cc70756a50990874ec7342194a0d59e85b0c5f47b4a894c721c1cc9684b5ff4","result":"PASS","version":"6.30.0-0supralinux1","tests":"38/38 PASS"},
 "kcmutils":{"job_id":109101309445,"artifact_id":10992718121,"artifact_sha256":"674a760f2075e9000e713b910cebd281d120aedf0bfdbfe3833a9950b3a7a999","result":"FAIL","version":"6.30.0-0supralinux2","tests":"6/6 PASS"},
 "knotifyconfig":{"job_id":109101309465,"artifact_id":10992533517,"artifact_sha256":"243ef6fe3e99e9dfa1132cdcf9c47dbe528b28bfefa048f2bbe179f98470ff39","result":"PASS","version":"6.30.0-0supralinux1","tests":"1/1 PASS"},
 "kparts":{"job_id":109101309656,"artifact_id":10992408883,"artifact_sha256":"be548d17290dc7f5adaa9b518574c04bd9e29348b292e5db2795609bce355935","result":"PASS","version":"6.30.0-0supralinux2","tests":"3/3 PASS"},
}
hist=[x for x in a.get("campaign_history",[]) if x.get("attempt")==4]
req(len(hist)==1,"Attempt4 immutable campaign record")
h=hist[0] if hist else {}
req(h.get("workflow_run")==RUN and h.get("commit")==COMMIT and h.get("result")=="MIXED","Attempt4 identity/result")
req(h.get("package_attempted") is True and h.get("rootfs")==ROOTFS,"Attempt4 valid package execution/rootfs")
req(h.get("workflow_jobs")=={"success":3,"fail":1},"Attempt4 job result counts")
req(h.get("primary_classification")=={"PASS":["baloo","knotifyconfig","kparts"],"FAIL":["kcmutils"],"INFRA_INVALID":[]},"Attempt4 package classification")
req(h.get("canonical_promotions")==3 and h.get("canonical_failures")==1,"Attempt4 canonical effect")
for node,exp in ART.items():
    rows=[x for x in a.get("nodes",{}).get(node,[]) if x.get("attempt")==4]
    req(len(rows)==1,node+": Attempt4 immutable node record")
    x=rows[0] if rows else {}
    req(x.get("workflow_run")==RUN and x.get("commit")==COMMIT and x.get("job_id")==exp["job_id"],node+": Attempt4 run/job")
    req(x.get("artifact_id")==exp["artifact_id"] and x.get("artifact_sha256")==exp["artifact_sha256"],node+": Attempt4 artifact")
    req(x.get("result")==exp["result"] and x.get("package_version")==exp["version"] and x.get("tests")==exp["tests"],node+": Attempt4 result/version/tests")
    req(x.get("package_attempted") is True and x.get("rootfs_artifact_id")==ROOTFS["artifact_id"] and x.get("rootfs_artifact_sha256")==ROOTFS["artifact_sha256"],node+": Attempt4 package/rootfs proof")
k=[x for x in a.get("nodes",{}).get("kcmutils",[]) if x.get("attempt")==4]
if k:
    x=k[0]
    req(x.get("stage")=="sbuild" and x.get("failure_substage")=="dpkg-gensymbols-missing-toolchain-template-typeinfo" and x.get("exit_code")==2,"KCMUtils Attempt4 real sbuild FAIL")
    req(x.get("symbol")=="_ZTISt23_Sp_counted_ptr_inplaceI10QQmlEngineSaIvELN9__gnu_cxx12_Lock_policyE2EE@Base","KCMUtils Attempt4 missing typeinfo identity")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 Attempt 4 historical closure: PASS")
print("workflow_run=36473379324 result=MIXED promotions=3 fail=1")
