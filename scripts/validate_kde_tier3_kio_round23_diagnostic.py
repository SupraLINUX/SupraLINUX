#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT/path).read_text())

def req(value,message):
    if not value:
        print("ERROR:",message,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round23-diagnostic.json")
R22=load("manifests/kde-tier3-kio-round22-diagnostic.json")
P=load("manifests/diagnostic-infrastructure-preflight.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round23-diagnostic.yml").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round23-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("round")==23 and M.get("node")=="kio","Round23 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0","Round23 upstream")
req(M.get("claim")=="non-promoting-krecent-attempt8-rootfs-diagnostic","Round23 claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round23 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round23 no package/test mutation")
req(M.get("status")=="BLOCKED-pending-diagnostic-infrastructure-preflight","Round23 blocked status")
req(M.get("execution_authorized") is False and M.get("package_execution_authorized") is False,"Round23 blocked authorization")

attempts=M.get("diagnostic_attempts",[])
req(len(attempts)==7,"Round23 invalid-attempt ledger length")
req([x.get("ordinal") for x in attempts]==list(range(1,8)),"Round23 attempt ordinals")
req(all(x.get("status")=="INFRA_INVALID" for x in attempts),"Round23 attempts must remain infrastructure-invalid")
req(all(x.get("package_attempted") is False for x in attempts),"Round23 invalid attempts must not be package attempts")
req(all(x.get("canonical_state_effect")=="none" for x in attempts),"Round23 invalid attempts must have no canonical effect")
req(all(x.get("usable_for_kio_diagnostic_conclusion") is False for x in attempts),"Round23 invalid attempts cannot support KIO conclusions")
last=attempts[-1]
req(last.get("workflow_run")==36282766027 and last.get("job_id")==108517688179,"Round23 attempt7 run/job")
req(last.get("artifact_id")==10919472201 and last.get("artifact_sha256")=="c70ec7003ab48c6bdca8f99adc86fe2464abfa7c61b7a48eba61d32525754780","Round23 attempt7 artifact")
req(last.get("failed_stage")=="run-starting-build-commands","Round23 attempt7 stage")

review=M.get("methodology_review",{})
req(review.get("triggered") is True and review.get("infra_invalid_cutoff")==2,"Round23 methodology-review cutoff")
req(review.get("observed_infra_invalid")==7,"Round23 methodology-review count")
req(review.get("required_preflight")=="manifests/diagnostic-infrastructure-preflight.json","Round23 required preflight")
req(review.get("redesign_after_preflight_pass") is True,"Round23 redesign requirement")
req(review.get("preserve_historical_build_path") is True,"Round23 parity requirement")

req(R22.get("status")=="diagnostic-PASS","Round22 remains closed PASS")
a=M.get("attempt8_reference",{})
req(a.get("rootfs_artifact_id")==10904512642 and a.get("rootfs_artifact_sha256")=="d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe","Round23 Attempt8 rootfs")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round23 canonical snapshot")

gate="diagnostic-infrastructure-preflight-evidence"
req(P.get("status")=="definition-pending-ci" and P.get("execution_authorized") is True,"preflight is the runnable gate")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("next_gate")==gate,name+" preflight gate")
req(T.get("active_remediation",{}).get("execution_authorized") is False,"canonical package execution blocked")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8,"Attempt9 remains unauthorized")
req(M.get("next_gate")==gate,"Round23 hands off to infrastructure preflight")

req("workflow_call" in W and "pull_request:" not in W,"Round23 workflow remains reusable-only")
req("BLOCKED pending diagnostic infrastructure preflight" in DOC,"Round23 docs blocked state")
req("Attempt 9" in DOC,"Round23 docs preserve Attempt9 state")
print("KDE Tier 3 KIO Round 23 blocked lifecycle: PASS")
print("infra_invalid_attempts=7")
print("next_gate=diagnostic-infrastructure-preflight-evidence")
