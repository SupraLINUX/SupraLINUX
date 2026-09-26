#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round17-diagnostic.json")
D16=load("manifests/kde-tier3-kio-round16-diagnostic.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round17-diagnostic.yml").read_text()
D=(ROOT/"docs/kde-tier3-kio-round17-diagnostic.md").read_text()
R="\n".join((ROOT/p).read_text() for p in (
 "scripts/run-kde-tier3-kio-round17-diagnostic.sh",
 "scripts/run-kde-tier3-kio-round17-instrument.sh",
 "scripts/run-kde-tier3-kio-round17-classify.sh",
))

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==17,"Round17 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round17 upstream identity")
req(M.get("claim")=="non-promoting-actual-kio-object-path-state-transition-diagnostic" and M.get("non_promoting") is True,"Round17 claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round17 package state")
req(M.get("canonical_source_modified") is False and M.get("diagnostic_instrumentation") is True,"Round17 instrumentation contract")
req(M.get("dag_state_changes_allowed") is False and M.get("downstream_eligibility_changes_allowed") is False,"Round17 DAG safety")
req(M.get("execution_authorized") is False and M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round17 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round17 snapshot")

nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux7","KIO -7 FAIL")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO ineligible")
req(L.get("state")=="attempt7-closed-mixed" and L.get("execution_authorized") is False,"Level1 closed")
req(L.get("current_attempt")==7 and L.get("next_attempt")==8,"Attempt counters")

req(D16.get("status")=="diagnostic-PASS" and D16.get("next_gate")=="tier3-round17-kio-object-path-state-transition-diagnostic-definition","Round16 handoff")
e16=M.get("round16_evidence",{})
req(e16.get("workflow_run")==36209833629 and e16.get("job_id")==108313880904 and e16.get("artifact_id")==10894374901,"Round16 evidence identity")
req(e16.get("artifact_sha256")=="8cda50173446df052b21e5ca4fe89129af65e1c1e1ff13ac137953b5a9508cf6","Round16 evidence digest")
req(e16.get("conclusion")=="library-preload-alone-does-not-reproduce-kio-icon-name-loss","Round16 conclusion")
sm=M.get("source_materialization",{})
req(sm.get("artifact_id")==10839162922 and sm.get("artifact_sha256")=="ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c","Round17 source materialization")
req(sm.get("package_version")=="6.30.0-0supralinux7" and sm.get("upstream_source_sha256")=="c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2","Round17 source identity")

invalid=M.get("invalid_attempts",[])
req(len(invalid)==1,"Round17 invalid attempt ledger")
a=invalid[0]
req(a.get("attempt")==1 and a.get("workflow_run")==36213295538 and a.get("job_id")==108324143779,"Round17 invalid Attempt1 workflow")
req(a.get("artifact_id")==10896761982 and a.get("artifact_sha256")=="5247d6b2f9f80c15cb04c63c4687d37b707421e3a1f91f0e8f9e2d3360c01084","Round17 invalid Attempt1 artifact")
req(a.get("result")=="DIAG_INVALID" and a.get("conclusion")=="instrumentation-perturbed-original-failure" and a.get("canonical_effect")=="none","Round17 invalid Attempt1 classification")

scope=M.get("diagnostic_scope",{})
req(scope.get("transient_instrumented_files")==["src/widgets/kdirmodel.cpp","src/filewidgets/knewfilemenu.cpp"],"Round17 instrumented files")
req(scope.get("exact_test_cases",{}).get("kdirmodeltest")=="testIcon","Round17 KDir test")
req(scope.get("exact_test_cases",{}).get("knewfilemenutest")=="testFolderIconCollection:default","Round17 KNew test")
req(scope.get("instrumentation_strategy")=="conditional-single-QIcon-name-read-perturbation","Round17 corrected strategy")
req(scope.get("kdirmodel_touch_variants")==["baseline-no-touch","KDIR_FALLBACK","KDIR_ABSOLUTE","KDIR_FROMTHEME","KDIR_BEFORE_OVERLAYS","KDIR_AFTER_OVERLAYS"],"Round17 KDir touch matrix")
req(scope.get("knewfilemenu_touch_variants")==["baseline-no-touch","KNEW_CONSTRUCTOR","KNEW_CHECK_ENTRY","KNEW_CHECK_EXIT","KNEW_SHOW_ENTRY","KNEW_AFTER_INIT","KNEW_DEFAULT_CREATED","KNEW_SETICON_INPUT"],"Round17 KNew touch matrix")
req(all(scope.get(x) is False for x in ("package_build","canonical_source_modification","package_revision_allocation","test_suppression")),"Round17 safety scope")

for token in ("KDE Frameworks Tier 3 KIO Round 17 diagnostic","ubuntu-26.04","run-kde-tier3-kio-round17-diagnostic.sh"):
    req(token in W,f"workflow token {token}")
for token in ("10839162922","SUPRALINUX_R17_TOUCH","KDIR_FROMTHEME","KDIR_AFTER_OVERLAYS","KNEW_CONSTRUCTOR","KNEW_SETICON_INPUT","testFolderIconCollection:default","instrumentation.patch"):
    req(token in R,f"runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in R,f"Round17 must not package: {forbidden}")
req("transient diagnostic-only instrumentation patch" in D and "must still reproduce both original failures" in D and "Corrected Attempt 2 strategy" in D,"Round17 documentation")

if M.get("status")=="definition-pending-diagnostic":
    req(L.get("next_gate")=="tier3-round17-kio-object-path-state-transition-diagnostic-definition","Round17 live definition gate")
    req(M.get("next_gate")=="tier3-round17-kio-object-path-state-transition-diagnostic-evidence","Round17 evidence gate")
else:
    req(M.get("next_gate","").startswith("tier3-round18-"),"Round17 closed handoff")
    req(L.get("next_gate")==M.get("next_gate"),"Round17 closed live gate")
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round17 closure evidence")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval")
print("KDE Tier 3 KIO Round 17 diagnostic definition: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
