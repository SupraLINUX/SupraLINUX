#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round26-remediation.json")
R25=load("manifests/kde-tier3-kio-round25-remediation.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round26-remediation.yml").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round26-remediation.md").read_text()

req(M.get("schema")==1 and M.get("round")==26 and M.get("node")=="kio","Round26 identity")
req(M.get("status")=="remediation-PASS" and M.get("execution_authorized") is False,"Round26 historical closure")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round26 package safety")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round26 historical snapshot")

ri=R25.get("interpretation",{})
req(R25.get("status")=="remediation-FAIL-contract","Round25 historical contract retained")
req(ri.get("historical_contract_result")=="FAIL" and ri.get("target_krecent_remediation")=="PASS","Round25 predecessor interpretation")

ev=M.get("historical_evidence",{})
req(ev.get("workflow_run")==36366972800 and ev.get("job_id")==108755265236,"Round26 run/job")
req(ev.get("branch_commit")=="d8ad9719307bcc115380440f008e9b862b5e6388","Round26 branch commit")
req(ev.get("artifact_id")==10948970106 and ev.get("artifact_sha256")=="7c8b91266fd9ecd79638c8c4bfc5419dadac937b911517522b083900e9bc9f98","Round26 artifact")
req(ev.get("result")=="REMEDIATION_PASS","Round26 result")

r=M.get("result",{})
req(r.get("environment_valid") is True and r.get("diagnostic_build_path_invoked") is True,"Round26 historical path")
req(r.get("source_restored") is True and r.get("rules_restored") is True,"Round26 restoration")
req(r.get("historical_candidate_patch_reused") is True,"Round26 exact KRecent candidate reuse")
req(r.get("candidate_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Round26 candidate patch")
hidden=r.get("kdirmodel_matrix",{}).get("hidden-home",{})
visible=r.get("kdirmodel_matrix",{}).get("visible-home",{})
req((hidden.get("runs"),hidden.get("nonzero_rc_runs"),hidden.get("exact_historical_signature_runs"))==(10,10,10),"Round26 hidden HOME causality")
req((visible.get("runs"),visible.get("nonzero_rc_runs"),visible.get("exact_historical_signature_runs"))==(20,0,0),"Round26 visible HOME remediation")
full=r.get("full_suite_visible",{})
req(full.get("rc")==0 and full.get("all_69_tests_pass") is True,"Round26 full suite")
req(full.get("kdirmodel_pass") is True and full.get("krecent_pass") is True,"Round26 target tests")
req(full.get("krecent_final_order")==["temp File 12","temp File 13","temp File 14"] and full.get("krecent_final_order_ok") is True,"Round26 KRecent order")
req(r.get("hidden_home_causality_reproduced") is True and r.get("visible_home_remediation_pass") is True and r.get("combined_suite_pass") is True,"Round26 combined proof")
req(r.get("conclusion")=="hidden-home-causality-and-combined-kio-remediation-PASS","Round26 conclusion")

i=M.get("interpretation",{})
req(i.get("hidden_home_path_causality")=="confirmed","Round26 causal interpretation")
req(i.get("combined_kio_suite")=="69/69 PASS","Round26 combined suite interpretation")
req(i.get("attempt9_authorized") is False,"Round26 does not authorize Attempt9")
req(M.get("next_gate")=="tier3-attempt9-kio-remediation-definition","Round26 historical next gate")

req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round26 workflow reusable/manual")
req("69/69 PASS" in DOC and "Attempt 9" in DOC and "not executed" in DOC,"Round26 closed docs")

print("KDE Tier 3 KIO Round 26 historical remediation evidence: PASS")
print("hidden_home=10/10 historical signature")
print("visible_home=20/20 PASS")
print("combined_suite=69/69 PASS")
print("Attempt9=NOT-AUTHORIZED")
