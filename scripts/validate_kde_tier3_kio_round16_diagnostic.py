#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round16-diagnostic.json")
D15=load("manifests/kde-tier3-kio-round15-diagnostic.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round16-diagnostic.yml").read_text()
D=(ROOT/"docs/kde-tier3-kio-round16-diagnostic.md").read_text()
runner_paths=[
 "scripts/run-kde-tier3-kio-round16-diagnostic.sh",
 "scripts/run-kde-tier3-kio-round16-probe-build.sh",
 "scripts/run-kde-tier3-kio-round16-probe-matrix.sh",
 "scripts/run-kde-tier3-kio-round16-classify.sh",
]
R="\n".join((ROOT/p).read_text() for p in runner_paths)

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==16,"Round16 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round16 upstream identity")
req(M.get("claim")=="non-promoting-kiconthemes-startup-kio-library-linkage-diagnostic" and M.get("non_promoting") is True,"Round16 claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round16 package state")
req(M.get("dag_state_changes_allowed") is False and M.get("downstream_eligibility_changes_allowed") is False,"Round16 DAG safety")
req(M.get("execution_authorized") is False and M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round16 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round16 snapshot")

nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux7","KIO -7 remains FAIL")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO downstream eligibility")
req(L.get("state")=="attempt7-closed-mixed" and L.get("execution_authorized") is False,"Level1 closed")
req(L.get("current_attempt")==7 and L.get("next_attempt")==8,"Attempt counters")

req(D15.get("status")=="diagnostic-PASS" and D15.get("next_gate")=="tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-definition","Round15 handoff")
e15=M.get("round15_evidence",{})
req(e15.get("workflow_run")==36208311383 and e15.get("job_id")==108309466429 and e15.get("artifact_id")==10894857677,"Round15 evidence identity")
req(e15.get("artifact_sha256")=="58413dce8261e276f08b450ac6fbab494a0d691018dd0472a997b570b5e2e136","Round15 evidence digest")
req(e15.get("conclusion")=="breeze-init-state-does-not-reproduce-kio-icon-name-loss","Round15 conclusion")

e13=M.get("round13_build_tree_evidence",{})
req(e13.get("workflow_run")==36146880757 and e13.get("artifact_id")==10869413386,"Round13 evidence")
req(e13.get("artifact_sha256")=="f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7","Round13 digest")
sm=M.get("source_materialization",{})
req(sm.get("artifact_id")==10839162922 and sm.get("artifact_sha256")=="ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c","Round16 source materialization")
req(sm.get("package_version")=="6.30.0-0supralinux7" and sm.get("upstream_source_sha256")=="c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2","Round16 source identity")

lc=M.get("source_link_contract",{})
req("KF6::KIOWidgets" in lc.get("kdirmodeltest",[]) and "KF6::KIOCore" in lc.get("kdirmodeltest",[]),"kdirmodel linkage")
req("KF6::KIOFileWidgets" in lc.get("knewfilemenutest",[]) and "KF6::KIOWidgets" in lc.get("knewfilemenutest",[]),"knewfilemenu linkage")
req("KF6::IconThemes" in lc.get("kiowidgets_private_includes",[]),"KIOWidgets IconThemes linkage")
req("KF6::KIOWidgets" in lc.get("kiofilewidgets_public_includes",[]),"KIOFileWidgets linkage")

scope=M.get("diagnostic_scope",{})
req(scope.get("sequences")==["normal","kdirmodel-testmode","knewfilemenu-sequence"],"Round16 sequences")
req(scope.get("modes")==["qt-baseline","kiconthemes-only","kiocore-only","kiconthemes-plus-kiocore","kiowidgets-closure","kiofilewidgets-closure"],"Round16 modes")
req(scope.get("icons")==["unknown","inode-directory","folder-red"],"Round16 icon set")
req(all(scope.get(x) is False for x in ("package_build","source_modification","package_revision_allocation","test_suppression")),"Round16 safety scope")

for token in ("KDE Frameworks Tier 3 KIO Round 16 diagnostic","ubuntu-26.04","run-kde-tier3-kio-round16-diagnostic.sh"):
    req(token in W,f"workflow token {token}")
for token in ("10839162922","--no-as-needed","libKF6IconThemes.so.6","libKF6KIOCore.so.6","libKF6KIOWidgets.so.6","libKF6KIOFileWidgets.so.6","kiconthemes-plus-kiocore","QT_PLUGIN_PATH"):
    req(token in R,f"runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in R,f"Round16 must not package: {forbidden}")
req("which loaded library closure first changes QIcon identity" in D and "No KIO source remediation" in D,"Round16 documentation")

if M.get("status")=="definition-pending-diagnostic":
    req(L.get("next_gate")=="tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-definition","Round16 live definition gate")
    req(M.get("next_gate")=="tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-evidence","Round16 evidence gate")
else:
    req(M.get("next_gate")=="tier3-round17-kio-object-path-state-transition-diagnostic-definition","Round16 closed handoff")
    req(L.get("next_gate")==M.get("next_gate"),"Round16 closed live gate")
    dv=M.get("definition_validation",{})
    req(dv.get("commit")=="5bea0781bf90ed97c53fdddc761566d4a984f5a7" and dv.get("repository_policy_workflow_run")==36209833503 and dv.get("result")=="PASS","Round16 definition validation")
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36209833629 and ev.get("job_id")==108313880904 and ev.get("commit")=="5bea0781bf90ed97c53fdddc761566d4a984f5a7","Round16 workflow identity")
    req(ev.get("artifact_id")==10894374901 and ev.get("artifact_sha256")=="8cda50173446df052b21e5ca4fe89129af65e1c1e1ff13ac137953b5a9508cf6","Round16 artifact identity")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round16 closure evidence")
    dr=M.get("diagnostic_results",{})
    req(dr.get("baseline_valid") is True and dr.get("kiconthemes_startup_observed") is True,"Round16 valid baseline/startup")
    req(dr.get("conclusion")=="library-preload-alone-does-not-reproduce-kio-icon-name-loss","Round16 closure conclusion")
    req(dr.get("next_diagnostic_scope")=="actual-kio-object-path-state-transition","Round16 next scope")
    for mode in ("qt-baseline","kiconthemes-only","kiocore-only","kiconthemes-plus-kiocore","kiowidgets-closure","kiofilewidgets-closure"):
        req(dr.get("modes",{}).get(mode,{}).get("primary_empty_any") is False,f"Round16 {mode} preserves primary icon names")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval")
print("KDE Tier 3 KIO Round 16 diagnostic definition: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
