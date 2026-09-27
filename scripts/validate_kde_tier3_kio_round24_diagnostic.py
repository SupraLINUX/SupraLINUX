#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round24-diagnostic.json")
R23=load("manifests/kde-tier3-kio-round23-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round24-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round24-diagnostic.sh").read_text()
HOOK=(ROOT/"scripts/run-kde-tier3-kio-round24-hook.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round24-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("round")==24 and M.get("node")=="kio","Round24 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round24 upstream identity")
req(M.get("claim")=="non-promoting-krecent-timestamp-tie-causality-diagnostic","Round24 claim")
req(M.get("status")=="diagnostic-PASS" and M.get("execution_authorized") is False,"Round24 closed")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round24 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round24 no package/test mutation")
req(M.get("canonical_source_modified") is False and M.get("controlled_perturbation") is True,"Round24 controlled perturbation")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round24 historical snapshot")

r23=R23.get("result",{})
req(R23.get("status")=="diagnostic-PASS","Round23 predecessor PASS")
req(r23.get("matrix",{}).get("isolated-krecent",{}).get("krecent_failed_runs")==58,"Round23 isolated evidence")
req(r23.get("matrix",{}).get("isolated-krecent",{}).get("attempt8_signature_failures")==51,"Round23 exact signature evidence")

ev=M.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36295265079 and ev.get("job_id")==108552864340,"Round24 run/job")
req(ev.get("branch_commit")=="6fa1facb7afb562bf0cae8e1f4edaa067ab4c297","Round24 branch commit")
req(ev.get("artifact_id")==10922979916 and ev.get("artifact_sha256")=="3fac75e577fbe9d33ec671ef6bc4fa9fca86f6324285fa04f7fb9a4147cfa4a3","Round24 artifact")
req(ev.get("result")=="DIAG_COMPLETE","Round24 diagnostic completion")

r=M.get("result",{})
req(r.get("environment_valid") is True and r.get("diagnostic_build_path_invoked") is True,"Round24 historical path")
req(r.get("source_restored") is True and r.get("rules_restored") is True,"Round24 worktree restored")
req(r.get("controlled_timestamp_modes_verified") is True,"Round24 timestamp controls")
req(r.get("historical_build_path")=="sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary -> override_dh_auto_test","Round24 historical path text")
expected={
 "native":(40,40,40,14,14,{"2":31,"3":9}),
 "monotonic":(40,40,40,0,0,{"3":40}),
 "fixed":(20,20,20,20,0,{"1":20}),
}
for lane,want in expected.items():
    x=r.get("matrix",{}).get(lane,{})
    got=(x.get("runs"),x.get("expected_runs"),x.get("valid_captures"),x.get("failed_runs"),x.get("attempt8_signature_failures"),x.get("timestamp_cardinality_counts"))
    req(got==want,f"Round24 {lane} matrix")
req(r.get("matrix",{}).get("native",{}).get("observed_orders")=={"temp File 11 | temp File 13 | temp File 14":14,"temp File 12 | temp File 13 | temp File 14":26},"Round24 native orders")
req(r.get("matrix",{}).get("monotonic",{}).get("observed_orders")=={"temp File 12 | temp File 13 | temp File 14":40},"Round24 monotonic order")
req(r.get("matrix",{}).get("fixed",{}).get("observed_orders")=={"temp File 0 | temp File 1 | temp File 2":20},"Round24 fixed order")
req(r.get("conclusion")=="timestamp-tie-causality-confirmed","Round24 conclusion")

interp=M.get("interpretation",{})
req(interp.get("classification")=="timestamp-ties-causally-confirmed-for-krecent-max-entry-flake","Round24 classification")
req(interp.get("native_reproduced") is True and interp.get("no_tie_control_eliminated_failures") is True and interp.get("forced_tie_control_reproduced_failures") is True,"Round24 causal controls")
req(interp.get("production_fix_selected") is False and interp.get("test_suppression_authorized") is False and interp.get("attempt9_authorized") is False,"Round24 no remediation authorization")
req(M.get("next_gate")=="tier3-round25-kio-krecent-ordering-remediation-definition","Round24 historical next gate")

req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round24 workflow reusable/manual only")
for forbidden in ("debian/rules clean","override_dh_auto_configure","override_dh_auto_build"):
    req(forbidden not in HOOK,"Round24 hook does not reconstruct "+forbidden)
req("timestamp-tie-causality-confirmed" in DOC and "Attempt 9 = NOT AUTHORIZED" in DOC,"Round24 closed docs")
print("KDE Tier 3 KIO Round 24 historical diagnostic evidence: PASS")
print("native=14/40 FAIL; monotonic=0/40 FAIL; fixed=20/20 FAIL")
print("conclusion=timestamp-tie-causality-confirmed")
print("Attempt9=NOT-AUTHORIZED")
