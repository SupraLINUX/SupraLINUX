#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)
M=load("manifests/kde-tier3-kio-round20-diagnostic.json")
R19=load("manifests/kde-tier3-kio-round19-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round20-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round20-diagnostic.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round20-diagnostic.md").read_text()
req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==20,"Round20 identity")
req(M.get("status")=="diagnostic-PASS" and M.get("execution_authorized") is False,"Round20 closed lifecycle")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round20 non-packaging")
req(M.get("canonical_source_modified") is False and M.get("package_revision_allocation") is False,"Round20 source safety")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round20 historical snapshot")
ev=M.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36244913604 and ev.get("job_id")==108412266582 and ev.get("branch_commit")=="b86b84dacf00a2c374f79a89766fd68c643897d2","Round20 run evidence")
req(ev.get("artifact_id")==10906434669 and ev.get("artifact_sha256")=="2071034608c31411399b656fb4e963cd066bded08e8c52566beea6c186d77fbc","Round20 artifact")
res=M.get("result",{}); kdir=res.get("kdirmodel",{}); recent=res.get("krecentdocument",{})
req(res.get("overall")=="partial-causal-resolution","Round20 result")
req(kdir.get("conclusion")=="hidden-home-component-controls-kdirmodel-showroot-failure","Round20 KDir cause")
req(kdir.get("hidden_initial",{}).get("show_root_fail") is True and kdir.get("visible",{}).get("show_root_fail") is False and kdir.get("hidden_repeat",{}).get("show_root_fail") is True,"Round20 KDir A/B/A")
req(kdir.get("visible_path_hidden_components")==[],"Round20 visible path audit")
req(recent.get("conclusion")=="DIAG_INVALID-hidden-working-directory-and-post-test-cleanup" and len(recent.get("defects",[]))==3,"Round20 KRecent invalidity")
req(R19.get("status")=="diagnostic-PASS","Round19 predecessor")
req(M.get("next_gate")=="tier3-round21-kio-krecent-visible-cwd-diagnostic-definition","Round20 handoff")
req("workflow_call" in W and "run-kde-tier3-kio-round20-diagnostic.sh" in W,"Round20 workflow retained")
req(".work/kde-tier3-kio-round20-diagnostic" in RUNNER and "recent-capture-all" in RUNNER,"Round20 runner retained")
req("Round 20" in DOC and M.get("stable_promotion_requires_explicit_user_approval") is True,"Round20 docs/policy")
print("KDE Tier 3 KIO Round 20 historical diagnostic evidence: PASS")
