#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round25-remediation.json")
R24=load("manifests/kde-tier3-kio-round24-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round25-remediation.yml").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round25-remediation.md").read_text()

req(M.get("schema")==1 and M.get("round")==25 and M.get("node")=="kio","Round25 identity")
req(M.get("status")=="remediation-FAIL-contract" and M.get("execution_authorized") is False,"Round25 historical closure")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round25 package safety")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round25 historical snapshot")
req(R24.get("status")=="diagnostic-PASS" and R24.get("result",{}).get("conclusion")=="timestamp-tie-causality-confirmed","Round24 predecessor")

ev=M.get("historical_evidence",{})
req(ev.get("workflow_run")==36359842892 and ev.get("job_id")==108734756942,"Round25 run/job")
req(ev.get("branch_commit")=="5d8b72cf6d468550aa520d0a09c169ff9c1bf05f","Round25 commit")
req(ev.get("artifact_id")==10945592004 and ev.get("artifact_sha256")=="0ac55c97c3efb725bd46500d9f899fcc0222368f8b60973b574356975b2dd1ce","Round25 artifact")
req(ev.get("result")=="REMEDIATION_FAIL","Round25 declared historical result")

r=M.get("result",{})
req(r.get("environment_valid") is True and r.get("diagnostic_build_path_invoked") is True,"Round25 valid historical path")
req(r.get("source_restored") is True and r.get("rules_restored") is True,"Round25 restoration")
req(r.get("candidate_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Round25 candidate patch")
req(r.get("candidate_source_sha256")=="57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b","Round25 candidate source")
req(r.get("all_orders_correct") is True,"Round25 deterministic order")

expected={
 "native":(100,0,0,100),
 "fixed":(100,0,0,100),
 "monotonic":(20,0,0,20),
 "full-suite":(1,1,1,1),
}
for lane,want in expected.items():
    x=r.get("matrix",{}).get(lane,{})
    got=(x.get("runs"),x.get("failed_runs"),x.get("nonzero_rc_runs"),x.get("valid_captures"))
    req(got==want,f"Round25 {lane} matrix")
req(r.get("conclusion")=="deterministic-xbel-ordering-remediation-FAIL","Round25 contract result")

i=M.get("interpretation",{})
req(i.get("historical_contract_result")=="FAIL" and i.get("target_krecent_remediation")=="PASS","Round25 target/contract distinction")
te=i.get("target_evidence",{})
req(te.get("isolated_runs")==220 and te.get("isolated_failures")==0 and te.get("full_suite_krecent")=="PASS","Round25 KRecent target proof")
ib=i.get("independent_blocker",{})
req(ib.get("test")=="kiowidgets-kdirmodeltest" and ib.get("historical_in_attempt8") is True and ib.get("reproduced_in_round25") is True,"Round25 independent blocker")
hh=i.get("hidden_home_hypothesis",{})
req(hh.get("classification")=="strong-causal-candidate-not-yet-proven","Round25 hidden HOME hypothesis discipline")
req(M.get("next_gate")=="tier3-round26-kio-kdirmodel-hidden-home-causality-definition","Round25 historical next gate")
req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round25 workflow reusable/manual")
req("target KRecent remediation: **PASS**" in DOC and "historical Round 25 contract: **FAIL**" in DOC,"Round25 closed docs")

print("KDE Tier 3 KIO Round 25 historical evidence: PASS")
print("historical_contract=FAIL")
print("target_krecent_remediation=PASS")
print("independent_blocker=kiowidgets-kdirmodeltest")
print("Attempt9=NOT-AUTHORIZED")
