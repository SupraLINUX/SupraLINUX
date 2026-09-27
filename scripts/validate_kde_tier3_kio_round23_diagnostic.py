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
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round23-diagnostic.sh").read_text()
HOOK=(ROOT/"scripts/run-kde-tier3-kio-round23-hook.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round23-diagnostic.md").read_text()

req(M.get("schema")==1 and M.get("round")==23 and M.get("node")=="kio","Round23 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0","Round23 upstream")
req(M.get("claim")=="non-promoting-krecent-attempt8-rootfs-diagnostic","Round23 claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round23 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round23 no package/test suppression")
req(M.get("status")=="definition-pending-ci","Round23 runnable diagnostic status")
req(M.get("execution_authorized") is True and M.get("package_execution_authorized") is False,"Round23 diagnostic-only authorization")
req(M.get("diagnostic_build_path_invocation_required") is True,"Round23 historical build-path invocation")
req(M.get("candidate_package_artifacts_forbidden") is True,"Round23 package artifacts forbidden")

attempts=M.get("diagnostic_attempts",[])
req(len(attempts)==7,"Round23 invalid-attempt ledger length")
req([x.get("ordinal") for x in attempts]==list(range(1,8)),"Round23 attempt ordinals")
req(all(x.get("status")=="INFRA_INVALID" for x in attempts),"Round23 attempts remain infrastructure-invalid")
req(all(x.get("package_attempted") is False for x in attempts),"Round23 invalid attempts are not package attempts")
req(all(x.get("canonical_state_effect")=="none" for x in attempts),"Round23 invalid attempts have no canonical effect")
req(all(x.get("usable_for_kio_diagnostic_conclusion") is False for x in attempts),"Round23 invalid attempts cannot support KIO conclusions")
last=attempts[-1]
req(last.get("workflow_run")==36282766027 and last.get("job_id")==108517688179,"Round23 attempt7 run/job")
req(last.get("artifact_id")==10919472201 and last.get("artifact_sha256")=="c70ec7003ab48c6bdca8f99adc86fe2464abfa7c61b7a48eba61d32525754780","Round23 attempt7 artifact")
req(last.get("failed_stage")=="run-starting-build-commands","Round23 attempt7 stage")

review=M.get("methodology_review",{})
req(review.get("triggered") is True and review.get("infra_invalid_cutoff")==2,"Round23 methodology-review cutoff")
req(review.get("observed_infra_invalid")==7,"Round23 methodology-review count")
req(review.get("required_preflight")=="manifests/diagnostic-infrastructure-preflight.json","Round23 required preflight")
req(review.get("redesign_after_preflight_pass") is True and review.get("preserve_historical_build_path") is True,"Round23 redesign requirement")

req(P.get("status")=="PASS" and P.get("execution_authorized") is False,"preflight must be closed PASS")
pev=P.get("evidence",{})
req(pev.get("workflow_run")==36286096599 and pev.get("job_id")==108527097646,"preflight PASS run/job")
req(pev.get("artifact_id")==10920194622 and pev.get("artifact_sha256")=="ee6adecf77aa5110db735220bca0ebecd2a4a41b4a2b8dacc6692816866c1d39","preflight PASS artifact")
req(pev.get("rootfs_tar_sha256")=="790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e","preflight exact rootfs tar")

req(R22.get("status")=="diagnostic-PASS","Round22 remains closed PASS")
a=M.get("attempt8_reference",{})
req(a.get("workflow_run")==36238357510 and a.get("job_id")==108394325161,"Round23 Attempt8 run/job")
req(a.get("rootfs_artifact_id")==10904512642 and a.get("rootfs_artifact_sha256")=="d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe","Round23 Attempt8 rootfs")
req(a.get("rootfs_tar_sha256")=="790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e","Round23 Attempt8 rootfs tar")
req(a.get("materialization_artifact_id")==10898999142 and a.get("materialization_artifact_sha256")=="c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d","Round23 Attempt8 materialization")
req(a.get("kio_artifact_id")==10905267300 and a.get("kio_artifact_sha256")=="9f95e2b8e3330ee4f1b275eb059736b87fa57d7752602aa598cb313659cae53f","Round23 Attempt8 KIO evidence")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round23 canonical snapshot")

hist=M.get("historical_build_path_contract",{})
req(hist.get("sbuild_version")=="0.91.2ubuntu3" and hist.get("chroot_mode")=="unshare","Round23 historical sbuild")
req(hist.get("dpkg_buildpackage_command")=="dpkg-buildpackage --sanitize-env -us -uc -b","Round23 dpkg-buildpackage parity")
req(hist.get("debian_entrypoint")=="debian/rules binary","Round23 Debian entrypoint")
req(hist.get("diagnostic_injection_point")=="override_dh_auto_test","Round23 diagnostic injection point")
req(hist.get("manual_configure_or_build_from_hook_forbidden") is True,"Round23 no reconstructed configure/build")
req(hist.get("worktree_source_restored_before_exit") is True,"Round23 worktree restore contract")
req(hist.get("candidate_package_artifacts_forbidden") is True,"Round23 artifact prevention contract")

v=M.get("validity_contract",{})
for key in ("exact_attempt8_rootfs","exact_attempt8_source_materialization","exact_attempt8_predecessor_artifacts",
            "exact_sbuild_unshare_mode","historical_dpkg_buildpackage_required","diagnostic_runs_from_override_dh_auto_test",
            "canonical_source_artifact_unchanged","no_candidate_package_artifacts"):
    req(v.get(key) is True,"Round23 validity contract "+key)
req(v.get("matrix")=={"isolated-krecent":100,"prefix-through-krecent":30,"full-suite":3},"Round23 matrix contract")

next_gate="tier3-round23-krecent-attempt8-full-build-path-diagnostic-evidence"
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="diagnostic","Round23 live phase")
req(policy.get("package_builds")=="tier3-round23-diagnostic-pending","Round23 live package gate")
req(policy.get("remediation")=="round23-krecent-attempt8-full-build-path-diagnostic-pending-ci","Round23 live remediation marker")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="round23-diagnostic-pending-ci-after-infrastructure-PASS",name+" Round23 state")
    req(obj.get("next_gate")==next_gate,name+" Round23 gate")
req(T.get("active_remediation",{}).get("execution_authorized") is False,"canonical package execution remains blocked")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("active_remediation",{}).get("next_attempt")==9,"Attempt9 remains unauthorized")
req(C.get("active_remediation",{}).get("execution_authorized") is False and C.get("active_remediation",{}).get("level1_execution_authorized") is False,"contracts keep Level1 blocked")
req(MAT.get("active_remediation",{}).get("package_attempted") is False and MAT.get("active_remediation",{}).get("package_state_effect")=="none","materialization unchanged")
req(M.get("next_gate")==next_gate,"Round23 next gate")

req("workflow_call" in W and "pull_request:" not in W,"Round23 workflow remains reusable-only")
for token in ("10904512642","10898999142","0.91.2ubuntu3","--chroot-mode=unshare","--enable-network",
              "Command: dpkg-buildpackage --sanitize-env -us -uc -b","debian/rules binary",
              "SUPRALINUX_ROUND23_EVIDENCE_BASE64_BEGIN","candidate package artifacts were produced"):
    req(token in RUNNER,"Round23 runner token "+token)
for forbidden in ("debian/rules clean","override_dh_auto_configure","override_dh_auto_build"):
    req(forbidden not in HOOK,"Round23 hook must not reconstruct build step: "+forbidden)
for token in ("override_dh_auto_test","SUPRALINUX_CAPTURE_XBEL","preparation-complete","source-restored"):
    req(token in HOOK,"Round23 hook token "+token)
req("Infrastructure preflight: **PASS**" in DOC and "Attempt 9 = NOT AUTHORIZED" in DOC,"Round23 docs current state")

print("KDE Tier 3 KIO Round 23 historical-build-path diagnostic definition: PASS")
print("preflight=PASS")
print("Round23=AUTHORIZED-DIAGNOSTIC-ONLY")
print("Attempt9=NOT-AUTHORIZED")
