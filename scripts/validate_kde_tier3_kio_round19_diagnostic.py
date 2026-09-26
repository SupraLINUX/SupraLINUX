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
W=(ROOT/".github/workflows/kde-tier3-kio-round19-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round19-diagnostic.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round19-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==19,"Round19 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round19 upstream identity")
req(M.get("non_promoting") is True and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round19 non-promoting semantics")
req(M.get("canonical_source_modified") is False and M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round19 source/package safety")
req(M.get("status")=="diagnostic-PASS" and M.get("execution_authorized") is False,"Round19 closed lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round19 historical canonical snapshot")
pred=M.get("predecessor",{})
req(pred.get("attempt")==8 and pred.get("workflow_run")==36238357510 and pred.get("commit")=="77129c31006ac746d0d5d1d249ed7d1aaf6cf530","Round19 Attempt8 predecessor")
req(pred.get("kio",{}).get("job_id")==108394325161 and pred.get("kio",{}).get("artifact_id")==10905267300,"Round19 Attempt8 KIO evidence")
req(pred.get("kio",{}).get("tests")=={"total":69,"pass":67,"fail":2},"Round19 Attempt8 KIO test totals")
sm=M.get("source_materialization",{})
req(sm.get("artifact_id")==10898999142 and sm.get("artifact_sha256")=="c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d","Round19 source materialization")
ev=M.get("diagnostic_evidence",{})
req(ev.get("result")=="DIAG_COMPLETE" and ev.get("workflow_run")==36243076879 and ev.get("job_id")==108407192850,"Round19 execution identity")
req(ev.get("branch_commit")=="0df59eee29ee3c0024d2331a0bc78e503975f72f","Round19 branch commit")
req(ev.get("referenced_workflow_sha")=="ca433e58636ae43ffc744f1098eed805e11d1e01","Round19 PR merge workflow SHA")
req(ev.get("artifact_id")==10906951441 and ev.get("artifact_sha256")=="3395536506ea205ce722a4a9be8962b0f0b3fb7597dbee708a6b7e0dc8ef2611","Round19 artifact identity")
req(ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round19 evidence semantics")
dr=M.get("diagnostic_results",{})
req(dr.get("overall_conclusion")=="inconclusive-methodology-defects-require-environment-corrected-followup","Round19 overall conclusion")
recent=dr.get("krecentdocument",{})
req(recent.get("baseline_runs")==30 and recent.get("baseline_failures")==30 and recent.get("delayed_runs")==30 and recent.get("delayed_failures")==30,"Round19 recent observed counts")
req(recent.get("capture_all_entries")==0 and recent.get("conclusion")=="invalid-targeted-environment","Round19 recent invalidity classification")
req(".qttest/share" in recent.get("validity_defect","") and "recentUrls.length()==0" in recent.get("validity_defect",""),"Round19 recent validity defect")
kdir=dr.get("kdirmodel",{})
req(kdir.get("hidden_initial")=="historical-showroot-signature-FAIL" and kdir.get("hidden_repeat")=="historical-showroot-signature-FAIL","Round19 KDir hidden reproductions")
req(kdir.get("visible_control")=="historical-showroot-signature-FAIL" and kdir.get("trailing_slash")=="PASS" and kdir.get("test_icon")=="PASS","Round19 KDir observations")
req(kdir.get("conclusion")=="control-path-invalid-for-hidden-component-hypothesis" and ".work" in kdir.get("validity_defect",""),"Round19 KDir control invalidity")
req(M.get("next_gate")=="tier3-round20-kio-environment-corrected-diagnostic-definition","Round19 historical handoff")
for token in ("workflow_call","run-kde-tier3-kio-round19-diagnostic.sh","KIO Round 19 residual test root cause"):
    req(token in W,f"Round19 workflow token {token}")
for token in ("recent-capture-all","QTest::qWait(5)","hidden-initial","visible","hidden-repeat"):
    req(token in RUNNER,f"Round19 runner token {token}")
req("Attempt 8 residual failures" in DOC,"Round19 documentation")
print("KDE Tier 3 KIO Round 19 historical diagnostic evidence: PASS")
print("result=inconclusive-methodology-defects")
print("next_gate="+M["next_gate"])
