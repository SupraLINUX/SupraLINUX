#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round19-diagnostic.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
R18=load("manifests/kde-tier3-kio-round18-remediation.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round19-diagnostic.yml").read_text()
ROUTER=(ROOT/".github/workflows/pr-ci-router.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round19-diagnostic.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round19-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==19,"Round19 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round19 upstream identity")
req(M.get("claim")=="non-promoting-kio-residual-test-root-cause-diagnostic" and M.get("non_promoting") is True,"Round19 claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round19 package state")
req(M.get("canonical_source_modified") is False and M.get("diagnostic_worktree_modified") is True,"Round19 source safety")
req(M.get("dag_state_changes_allowed") is False and M.get("downstream_eligibility_changes_allowed") is False,"Round19 DAG safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round19 no revision/suppression")
req(M.get("execution_authorized") is True and M.get("package_execution_authorized") is False,"Round19 diagnostic-only authorization")
req(M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round19 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round19 snapshot")

pred=M.get("predecessor",{})
req(pred.get("attempt")==8 and pred.get("workflow_run")==36238357510 and pred.get("commit")=="77129c31006ac746d0d5d1d249ed7d1aaf6cf530","Attempt8 predecessor")
req(pred.get("kio",{}).get("job_id")==108394325161 and pred.get("kio",{}).get("artifact_id")==10905267300,"Attempt8 KIO evidence")
req(pred.get("kio",{}).get("tests")=={"total":69,"pass":67,"fail":2},"Attempt8 KIO tests")
req(pred.get("kxmlgui",{}).get("tests")=={"total":7,"pass":7,"fail":0} and pred.get("kxmlgui",{}).get("python_import")=="PASS","Attempt8 KXMLGui result")
req(pred.get("remaining_failures",{}).get("krecentdocument") and pred.get("remaining_failures",{}).get("kdirmodel"),"Round19 residual failures")

sm=M.get("source_materialization",{})
req(sm.get("artifact_id")==10898999142 and sm.get("artifact_sha256")=="c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d","Round19 source artifact")
req(sm.get("package_version")=="6.30.0-0supralinux8" and sm.get("upstream_source_sha256")=="c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2","Round19 source identity")

obs=M.get("upstream_source_observations",{})
req(obs.get("krecentdocument",{}).get("test_file_git_blob")=="ee4652d040a5cb52e1af5c5339a24ddcb2bd11a0","KRecentDocument exact upstream test")
req(obs.get("krecentdocument",{}).get("implementation_git_blob")=="a2e96a8f4b9a695f866cdc100aab5b24665e07e7","KRecentDocument exact implementation")
req(obs.get("kdirmodel",{}).get("test_file_git_blob")=="1d9d47f086a2605f76ceb31581111000a83bfba4","KDirModel exact upstream test")
req(".supralinux-test-home" in obs.get("kdirmodel",{}).get("attempt8_home",""),"KDirModel hidden HOME hypothesis")

scope=M.get("diagnostic_scope",{})
req(scope.get("build_targets")==["kio_file","kioworker","krecentdocumenttest","kdirmodeltest"],"Round19 targets")
req(scope.get("krecentdocument",{}).get("baseline_repetitions")==30 and scope.get("krecentdocument",{}).get("delayed_repetitions")==30,"KRecentDocument repetitions")
req(scope.get("kdirmodel",{}).get("sequence")==["hidden-home-initial","visible-home","hidden-home-repeat"],"KDirModel A/B/A")
req(all(scope.get(x) is not None for x in ("krecentdocument","kdirmodel","invariants")),"Round19 scope")

p=T.get("discovery_policy",{})
req(p.get("phase")=="diagnostic" and p.get("package_builds")=="tier3-round19-diagnostic-pending","Round19 current phase")
req(p.get("remediation")=="round19-kio-residual-tests-definition-pending-ci","Round19 current marker")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"Level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("next_gate")=="tier3-round19-kio-residual-test-diagnostic-evidence",name+" Round19 evidence gate")
req(T.get("active_remediation",{}).get("execution_authorized") is False,"canonical package execution paused")
req(L.get("execution_authorized") is False and L.get("state")=="attempt8-closed-mixed","Level1 remains Attempt8 closed")
req(R18.get("status")=="attempt8-closed-mixed" and R18.get("next_gate")=="tier3-round19-kio-diagnostic-definition","Round18 historical handoff preserved")

for token in ("workflow_call","run-kde-tier3-kio-round19-diagnostic.sh","KIO Round 19 residual test root cause"):
    req(token in W,f"Round19 workflow token {token}")
req("pull_request:" not in W,"Round19 must not subscribe directly to PR")
for token in ("run_round19","kde-tier3-kio-round19-diagnostic.yml","tier3-round19-diagnostic-pending"):
    req(token in ROUTER,f"router token {token}")
for token in ("10898999142","recent-capture-all","QTest::qWait(5)","hidden-initial","visible","hidden-repeat",".supralinux-test-home","supralinux-test-home"):
    req(token in RUNNER,f"runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in RUNNER,f"Round19 must not package: {forbidden}")
req("Attempt 8 residual failures" in DOC and "hidden HOME component" in DOC and "timestamp" in DOC,"Round19 documentation")

if M.get("status")=="definition-pending-diagnostic":
    req(M.get("next_gate")=="tier3-round19-kio-residual-test-diagnostic-evidence","Round19 evidence gate")
else:
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round19 closure evidence")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval")
print("KDE Tier 3 KIO Round 19 diagnostic definition: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux8")
print("next_gate="+M["next_gate"])
