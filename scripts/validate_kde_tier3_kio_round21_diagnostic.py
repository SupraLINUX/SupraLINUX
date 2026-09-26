#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round21-diagnostic.json")
R20=load("manifests/kde-tier3-kio-round20-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round21-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round21-diagnostic.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round21-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==21,"Round21 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round21 upstream identity")
req(M.get("status")=="diagnostic-PASS" and M.get("execution_authorized") is False,"Round21 closed lifecycle")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none" and M.get("package_revision_allocation") is False,"Round21 package safety")
req(M.get("canonical_source_modified") is False and M.get("test_suppression") is False,"Round21 canonical source safety")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round21 historical snapshot")
ev=M.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36248969228 and ev.get("job_id")==108423337171 and ev.get("branch_commit")=="9c18c9e811d31f8ec296d22180fdda7ed70545d9","Round21 run evidence")
req(ev.get("artifact_id")==10908497619 and ev.get("artifact_sha256")=="31f4fddc17bf13b2058773c9c506a54f625ebe100d884418ef27fe45fd9ec4e0","Round21 artifact evidence")
req(ev.get("result")=="DIAG_COMPLETE","Round21 diagnostic result")
r=M.get("result",{})
req(r.get("environment_valid") is True,"Round21 environment validity")
req((r.get("baseline_runs"),r.get("baseline_failures"),r.get("baseline_attempt8_signature_failures"))==(30,0,0),"Round21 baseline result")
req((r.get("delayed_runs"),r.get("delayed_failures"),r.get("delayed_attempt8_signature_failures"))==(30,0,0),"Round21 delayed result")
req(r.get("capture_all_entries")==15 and r.get("capture_all_duplicate_modified_groups")==0,"Round21 capture-all result")
req(r.get("conclusion")=="krecentdocument-attempt8-failure-not-reproduced","Round21 conclusion")
req(R20.get("status")=="diagnostic-PASS","Round20 predecessor retained")
req(M.get("next_gate")=="tier3-round22-kio-krecent-ctest-home-matrix-diagnostic-definition","Round21 historical handoff")
req("workflow_call" in W and "run-kde-tier3-kio-round21-diagnostic.sh" in W,"Round21 workflow retained")
req("SUPRALINUX_PRESERVE_XBEL" in RUNNER and "capture_all_duplicate_modified_groups" in RUNNER,"Round21 runner retained")
req("Round 21" in DOC and M.get("stable_promotion_requires_explicit_user_approval") is True,"Round21 docs/stable policy")
print("KDE Tier 3 KIO Round 21 historical diagnostic evidence: PASS")
print("baseline=30/30 PASS; delayed=30/30 PASS; duplicate_modified_groups=0")
print("historical_next_gate=tier3-round22-kio-krecent-ctest-home-matrix-diagnostic-definition")
