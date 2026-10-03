#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round23-diagnostic.json")
R22=load("manifests/kde-tier3-kio-round22-diagnostic.json")
P=load("manifests/diagnostic-infrastructure-preflight.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round23-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round23-diagnostic.sh").read_text()
HOOK=(ROOT/"scripts/run-kde-tier3-kio-round23-hook.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round23-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("round")==23 and M.get("node")=="kio","Round23 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0","Round23 upstream")
req(M.get("status")=="diagnostic-PASS" and M.get("execution_authorized") is False,"Round23 closed")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round23 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round23 no package/test mutation")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round23 historical snapshot")
req(R22.get("status")=="diagnostic-PASS","Round22 retained")

attempts=M.get("diagnostic_attempts",[])
req(len(attempts)==7 and [x.get("ordinal") for x in attempts]==list(range(1,8)),"Round23 invalid-attempt ledger")
req(all(x.get("status")=="INFRA_INVALID" and x.get("package_attempted") is False and x.get("canonical_state_effect")=="none" for x in attempts),"Round23 infra-invalid history")
review=M.get("methodology_review",{})
req(review.get("triggered") is True and review.get("infra_invalid_cutoff")==2 and review.get("observed_infra_invalid")==7,"Round23 methodology cutoff")

req(P.get("status")=="PASS" and P.get("execution_authorized") is False,"preflight closed PASS")
pev=P.get("evidence",{})
req(pev.get("workflow_run")==36286096599 and pev.get("job_id")==108527097646 and pev.get("artifact_id")==10920194622,"preflight evidence identity")
req(pev.get("artifact_sha256")=="ee6adecf77aa5110db735220bca0ebecd2a4a41b4a2b8dacc6692816866c1d39","preflight artifact digest")

ev=M.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36288655361 and ev.get("job_id")==108534328079,"Round23 run/job")
req(ev.get("branch_commit")=="f31c5620697dfaecb69b870287a180574b3bc92d","Round23 branch commit")
req(ev.get("artifact_id")==10921272952 and ev.get("artifact_sha256")=="1638ac8ea01881a78e4ec32761eb473836258653d3c08f1f116af6ac93829e69","Round23 artifact")
req(ev.get("result")=="DIAG_COMPLETE","Round23 diagnostic completion")

r=M.get("result",{})
req(r.get("environment_valid") is True and r.get("diagnostic_build_path_invoked") is True,"Round23 valid historical build path")
req(r.get("source_restored") is True and r.get("rules_restored") is True,"Round23 worktree restored")
req(r.get("package_attempted") is False and r.get("package_state_effect")=="none","Round23 result package safety")
req(r.get("historical_build_path")=="sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary -> override_dh_auto_test","Round23 historical path")
expected={
 "isolated-krecent":(100,100,100,58,51),
 "prefix-through-krecent":(30,30,30,14,13),
 "full-suite":(3,3,3,3,1),
}
for lane,want in expected.items():
    x=r.get("matrix",{}).get(lane,{})
    got=(x.get("runs"),x.get("expected_runs"),x.get("valid_captures"),x.get("krecent_failed_runs"),x.get("attempt8_signature_failures"))
    req(got==want,f"Round23 {lane} matrix")
req(r.get("conclusion")=="krecentdocument-attempt8-signature-reproduced-isolated-in-historical-build-path","Round23 conclusion")

interp=M.get("interpretation",{})
req(interp.get("classification")=="isolated-nondeterministic-krecent-ordering-reproduced","Round23 classification")
req(interp.get("preceding_ctest_prefix_required") is False and interp.get("exact_attempt8_signature_reproduced") is True,"Round23 isolated reproduction")
req(interp.get("timestamp_tie_hypothesis")=="strengthened-but-not-yet-proven-causal","Round23 timestamp hypothesis discipline")

req(M.get("next_gate")=="tier3-round24-kio-krecent-timestamp-tie-causality-diagnostic-definition","Round23 historical next gate")

req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round23 workflow reusable/manual only")
req("# shellcheck disable=SC2329" in RUNNER,"Round23 EXIT-trap ShellCheck annotation")
for token in ("Command: dpkg-buildpackage --sanitize-env -us -uc -b","debian/rules binary","SUPRALINUX_ROUND23_EVIDENCE_BASE64_BEGIN"):
    req(token in RUNNER,"Round23 retained runner token "+token)
for forbidden in ("debian/rules clean","override_dh_auto_configure","override_dh_auto_build"):
    req(forbidden not in HOOK,"Round23 hook does not reconstruct "+forbidden)
req("51 / 100" in DOC and "Attempt 9 = NOT AUTHORIZED" in DOC and "timestamp" in DOC.lower(),"Round23 closed docs")

print("KDE Tier 3 KIO Round 23 historical diagnostic evidence: PASS")
print("isolated=58/100 failures; exact_attempt8=51/100")
print("prefix=14/30 failures; exact_attempt8=13/30")
print("full_suite=3/3 failures; exact_attempt8=1/3")
print("Attempt9=NOT-AUTHORIZED")
