#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)
M=load("manifests/kde-tier3-kio-round22-diagnostic.json")
R21=load("manifests/kde-tier3-kio-round21-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round22-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round22-diagnostic.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round22-diagnostic.md").read_text()
req(M.get("schema")==1 and M.get("round")==22 and M.get("node")=="kio","Round22 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0","Round22 upstream")
req(M.get("status")=="diagnostic-PASS" and M.get("execution_authorized") is False,"Round22 closed")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none" and M.get("package_revision_allocation") is False,"Round22 package safety")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round22 historical snapshot")
ev=M.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36278019755 and ev.get("job_id")==108504444054 and ev.get("branch_commit")=="07282c338c1c6d3b1341e4ba8d4d1c82c9b3b658","Round22 run evidence")
req(ev.get("artifact_id")==10917842068 and ev.get("artifact_sha256")=="0554aeb1a38aa78de4b9316e85058fbfd6b24cc8ff62c7978cfa286f6ea34f8e","Round22 artifact evidence")
r=M.get("result",{})
req(r.get("environment_valid") is True,"Round22 valid environment")
for lane in ("direct-visible","direct-hidden","ctest-visible","ctest-hidden"):
    x=r.get("matrix",{}).get(lane,{})
    req((x.get("runs"),x.get("failures"),x.get("attempt8_signature_failures"),x.get("valid_captures"),x.get("duplicate_modified_runs"))==(30,0,0,30,0),f"Round22 {lane}")
req(r.get("conclusion")=="krecentdocument-attempt8-failure-not-reproduced-outside-sbuild","Round22 conclusion")
req(R21.get("status")=="diagnostic-PASS","Round21 retained")
req(M.get("next_gate")=="tier3-round23-kio-krecent-attempt8-rootfs-diagnostic-definition","Round22 handoff")
req("workflow_call" in W and "run-kde-tier3-kio-round22-diagnostic.sh" in W,"Round22 workflow retained")
req("SUPRALINUX_CAPTURE_XBEL" in RUNNER and "ctest-hidden" in RUNNER,"Round22 runner retained")
req("Round 22" in DOC and M.get("stable_promotion_requires_explicit_user_approval") is True,"Round22 docs/stable")
print("KDE Tier 3 KIO Round 22 historical diagnostic evidence: PASS")
print("matrix=4 lanes x 30; failures=0; Attempt8 signatures=0")
print("historical_next_gate=tier3-round23-kio-krecent-attempt8-rootfs-diagnostic-definition")
