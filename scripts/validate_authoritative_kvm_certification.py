#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

ROOT=Path(__file__).resolve().parents[1]
state=json.loads((ROOT/"manifests/authoritative-kvm-certification.json").read_text())
desktop=json.loads((ROOT/"manifests/desktop-stack.json").read_text())
errors=[]

def req(v,m):
    if not v:
        errors.append(m)

req(state.get("schema")==1,"authoritative KVM certification schema")
req(state.get("authority")=="supralinux","authoritative KVM certification authority")
req(state.get("role")=="live-authoritative-kvm-certification-state","authoritative KVM live-state role")

pre=state.get("hosted_frameworks_precondition",{})
req(pre.get("status")=="PASS","hosted Frameworks precondition must be PASS")
req(pre.get("canonical_snapshot")=="20 PASS / 0 pending / 0 current FAIL / 0 BLOCKED","hosted Frameworks canonical snapshot")
req(pre.get("manifest")=="manifests/kde-frameworks-tier3.json","hosted Frameworks manifest binding")
req(re.fullmatch(r"[0-9a-f]{40}",str(pre.get("closure_commit",""))) is not None,"hosted Frameworks closure commit")
req(isinstance(pre.get("repository_policy_run"),int) and pre["repository_policy_run"]>0,"hosted Frameworks policy evidence")

host=state.get("host_kvm_preflight",{})
gold=state.get("golden_image",{})
req(host.get("status") in {"pending-real-evidence","PASS"},"host KVM preflight status")
req(gold.get("status") in {"pending-real-evidence","PASS"},"golden image status")
req(gold.get("input_fingerprint_schema")==1,"golden image input fingerprint schema")
if host.get("status")=="PASS":
    req(bool(host.get("evidence")),"host KVM PASS requires evidence")
if gold.get("status")=="PASS":
    req(host.get("status")=="PASS","golden image PASS requires host KVM PASS")
    req(bool(gold.get("evidence")),"golden image PASS requires evidence")
    req(re.fullmatch(r"[0-9a-f]{64}",str(gold.get("image_sha256",""))) is not None,"golden image PASS requires SHA-256")
    req(re.fullmatch(r"[0-9a-f]{40}",str(gold.get("source_commit",""))) is not None,"golden image PASS requires source commit")
    req(re.fullmatch(r"[0-9a-f]{64}",str(gold.get("input_digest",""))) is not None,"golden image PASS requires golden-input digest")
    req(gold.get("source_checkout_removed") is True,"golden image PASS requires source checkout removal")

gates=state.get("gates",[])
req([x.get("id") for x in gates]==["runner-contract","authoritative-package-proof","frameworks-sample-proof"],"authoritative gate order")
byid={x.get("id"):x for x in gates}
allowed={"pending","PASS","FAIL","INFRA_INVALID"}
for gate in gates:
    gid=gate.get("id")
    req(gate.get("status") in allowed,f"{gid}: status")
    req(isinstance(gate.get("execution_authorized"),bool),f"{gid}: execution_authorized boolean")
    req((ROOT/gate.get("workflow","")).is_file(),f"{gid}: workflow exists")
    text=(ROOT/gate["workflow"]).read_text()
    req(gate.get("trigger_label") in text,f"{gid}: workflow label binding")
    req("self-hosted" in text and "ubuntu-26.04" in text and "kvm" in text and "ephemeral" in text,f"{gid}: authoritative runner labels")
    if gate.get("status")=="PASS":
        req(bool(gate.get("evidence")),f"{gid}: PASS requires evidence")
        req(gate.get("execution_authorized") is False,f"{gid}: closed PASS cannot remain execution-authorized")

runner=byid.get("runner-contract",{})
pkg=byid.get("authoritative-package-proof",{})
sample=byid.get("frameworks-sample-proof",{})

runner_ready=host.get("status")=="PASS" and gold.get("status")=="PASS"
if runner.get("execution_authorized"):
    req(runner_ready and runner.get("status")=="pending","runner-contract authorization requires host+golden PASS")
    req(not runner.get("infrastructure_hold"),"execution-authorized runner-contract cannot retain an active infrastructure hold")
if runner.get("status")=="INFRA_INVALID":
    hold=runner.get("infrastructure_hold",{})
    req(runner.get("execution_authorized") is False,"INFRA_INVALID runner-contract must be execution-frozen")
    mechanism=hold.get("mechanism")
    req(mechanism in {"github-jit-runner-api","guest-actions-runner-startup"},"runner-contract INFRA_INVALID mechanism")
    if mechanism=="github-jit-runner-api":
        req(isinstance(hold.get("consecutive_infra_invalid"),int) and hold["consecutive_infra_invalid"]>=2,"runner-contract JIT API retry cutoff")
        req(hold.get("resume_requires")=="scripts/check-jit-runner-api-lifecycle.sh:PASS","runner-contract resume requires synthetic JIT API PASS")
    elif mechanism=="guest-actions-runner-startup":
        req(isinstance(hold.get("consecutive_infra_invalid"),int) and hold["consecutive_infra_invalid"]>=2,"runner-contract guest startup retry cutoff")
        req(hold.get("resume_requires")=="scripts/check-jit-runner-startup-lifecycle.sh:PASS","runner-contract resume requires synthetic guest startup PASS")
        incident=hold.get("incident_evidence",{})
        req(incident.get("runner_id")==155,"runner-contract guest startup incident runner ID")
        req(incident.get("guest_exit_code")==1,"runner-contract guest startup incident exit code")
        req(incident.get("workflow_run_id")=="","runner-contract guest startup incident must precede workflow creation")
        req(incident.get("package_attempt_consumed") is False,"runner-contract guest startup incident must not consume a package attempt")
        diagnosis=hold.get("diagnosis",{})
        req("/run" in str(diagnosis.get("cause","")),"runner-contract startup diagnosis must identify the /run ownership boundary")
        req("delete only" in str(diagnosis.get("remediation","")),"runner-contract startup diagnosis must preserve the minimal remediation")
        history=hold.get("diagnostic_history",[])
        req(len(history)>=3,"runner-contract guest startup diagnostic history")
        if history:
            req(all(x.get("workflow_created") is False for x in history),"runner-contract startup diagnostics must precede workflow creation")
            req(all(x.get("package_attempt_consumed") is False for x in history),"runner-contract startup diagnostics must not consume package attempts")
            failures=[x.get("observed_failure") for x in history]
            req("rm /run/supralinux-jit-config: Permission denied" in failures,"runner-contract direct-/run startup failure evidence")
            req("rmdir /run/supralinux-jit: Permission denied" in failures,"runner-contract private-directory startup failure evidence")
            write_runs=[x for x in history if x.get("jit_config_expected_bytes")==4144]
            req(any(x.get("jit_config_written_bytes")==4144 and x.get("jit_config_flush")=="PASS" for x in write_runs),"runner-contract JIT config byte/flush evidence")
        candidate=hold.get("recovery_candidate",{})
        if candidate:
            req(candidate.get("runner_id")==158,"runner-contract recovery candidate runner ID")
            req(candidate.get("runner_status")=="online","runner-contract recovery candidate online state")
            req(candidate.get("runner_busy") is False,"runner-contract recovery candidate idle state")
            req(candidate.get("runner_version")=="2.337.0","runner-contract recovery candidate runner version")
            req(candidate.get("workflow_run_id")=="","runner-contract recovery candidate must precede workflow creation")
            req(candidate.get("package_attempt_consumed") is False,"runner-contract recovery candidate must not consume a package attempt")
            req(candidate.get("cleanup")=="PASS","runner-contract recovery candidate cleanup")
            req(candidate.get("validation_run_verdict")=="INFRA_INVALID","runner-contract recovery candidate validator incident classification")
            req(candidate.get("canonical_recovery_state")=="awaiting-evidence-hashes","runner-contract recovery candidate hash gate")

closed_guest_startup=runner.get("closed_guest_startup_hold",{})
if closed_guest_startup:
    req(closed_guest_startup.get("mechanism")=="guest-actions-runner-startup","closed guest startup hold mechanism")
    req(isinstance(closed_guest_startup.get("consecutive_infra_invalid"),int) and closed_guest_startup["consecutive_infra_invalid"]>=3,"closed guest startup hold incident count")
    req(closed_guest_startup.get("resume_requires")=="scripts/check-jit-runner-startup-lifecycle.sh:PASS","closed guest startup hold recovery contract")
    req(closed_guest_startup.get("closed_by")=="host-local-evidence-adjudication:PASS","closed guest startup hold adjudication")
    req(closed_guest_startup.get("closed_after_repository_policy_run")==36813130825,"closed guest startup hold policy run")
    history=closed_guest_startup.get("diagnostic_history",[])
    req(len(history)>=3,"closed guest startup diagnostic history")
    if history:
        req(all(x.get("workflow_created") is False for x in history),"closed guest startup incidents must precede workflow creation")
        req(all(x.get("package_attempt_consumed") is False for x in history),"closed guest startup incidents must not consume package attempts")
    recovery=closed_guest_startup.get("recovery_evidence",{})
    req(recovery.get("kind")=="host-local-jit-startup-validation-run","guest startup recovery evidence kind")
    req(recovery.get("infrastructure_result")=="PASS","guest startup recovery infrastructure PASS")
    req(recovery.get("validation_run_result")=="INFRA_INVALID","guest startup recovery preserves validator incident")
    req(recovery.get("runner_id")==158,"guest startup recovery runner ID")
    req(recovery.get("runner_status")=="online","guest startup recovery online state")
    req(recovery.get("runner_busy") is False,"guest startup recovery idle state")
    req(recovery.get("runner_version")=="2.337.0","guest startup recovery runner version")
    req(recovery.get("workflow_run_id")=="","guest startup recovery must precede workflow creation")
    req(recovery.get("package_attempt_consumed") is False,"guest startup recovery must not consume a package attempt")
    req(recovery.get("cleanup")=="PASS","guest startup recovery cleanup")
    req(re.fullmatch(r"[0-9a-f]{64}",str(recovery.get("evidence_manifest_sha256",""))) is not None,"guest startup recovery evidence manifest hash")
    artifacts=recovery.get("artifacts",{})
    expected_artifacts={
        "guest-copy-out.txt",
        "guest-files/_diag/Runner_20261001-035533-utc.log",
        "guest-files/supralinux-actions-runner-console.log",
        "host-result.json",
        "jit-config-flush.json",
        "jit-config-write.json",
        "runner-online.json",
    }
    req(set(artifacts)==expected_artifacts,"guest startup recovery artifact set")
    req(all(re.fullmatch(r"[0-9a-f]{64}",str(value)) is not None for value in artifacts.values()),"guest startup recovery artifact hashes")

closed_hold=runner.get("closed_infrastructure_hold",{})
if closed_hold:
    req(closed_hold.get("mechanism")=="github-jit-runner-api","closed runner-contract infrastructure hold mechanism")
    req(isinstance(closed_hold.get("consecutive_infra_invalid"),int) and closed_hold["consecutive_infra_invalid"]>=2,"closed runner-contract infrastructure hold incident count")
    req(closed_hold.get("resume_requires")=="scripts/check-jit-runner-api-lifecycle.sh:PASS","closed runner-contract hold recovery contract")
    req(closed_hold.get("closed_by")=="scripts/check-jit-runner-api-lifecycle.sh:PASS","closed runner-contract hold closure evidence")
    recovery=closed_hold.get("recovery_evidence",{})
    req(recovery.get("kind")=="host-local-jit-api-preflight","runner-contract recovery evidence kind")
    req(recovery.get("result")=="PASS","runner-contract recovery evidence PASS")
    req(recovery.get("runner_group_id")==3,"runner-contract recovery runner group")
    req(recovery.get("http_status")==201,"runner-contract recovery HTTP status")
    req(recovery.get("cleanup")=="PASS","runner-contract recovery cleanup")
    artifacts=recovery.get("artifacts",{})
    req(re.fullmatch(r"[0-9a-f]{64}",str(artifacts.get("result.txt",""))) is not None,"runner-contract recovery result hash")
    req(re.fullmatch(r"[0-9a-f]{64}",str(artifacts.get("transport.txt",""))) is not None,"runner-contract recovery transport hash")
if pkg.get("execution_authorized"):
    req(runner.get("status")=="PASS" and pkg.get("status")=="pending","package proof authorization requires runner-contract PASS")
if sample.get("execution_authorized"):
    req(pkg.get("status")=="PASS" and sample.get("status")=="pending","Frameworks sample authorization requires package proof PASS")

s=sample.get("sample",{})
req(s.get("framework")=="karchive","Frameworks certification sample")
req(s.get("package_version")=="6.30.0-0supralinux4","KArchive sample package version")
req(s.get("ecm_predecessor")=="6.30.0-0supralinux3","KArchive sample ECM predecessor")
req(s.get("package_state_effect")=="none","Frameworks sample must not alter canonical package state")

release=state.get("release_relevant_desktop",{})
final_pass=sample.get("status")=="PASS"
if final_pass:
    req(release.get("status") in {"ready","unlocked"},"final sample PASS must unlock release-relevant desktop state")
else:
    req(release.get("status")=="locked","desktop must remain locked before Frameworks sample PASS")
    req(release.get("plasma_authorized") is False,"Plasma release-relevant work locked")
    req(release.get("kwin_authorized") is False,"KWin release-relevant work locked")
    req(release.get("session_authorized") is False,"session release-relevant work locked")

ci=desktop.get("ci",{}).get("authoritative_runner",{})
req(ci.get("certification_manifest")=="manifests/authoritative-kvm-certification.json","desktop stack binds authoritative certification manifest")
req(ci.get("desktop_release_relevant_authorized") is final_pass,"desktop stack authorization mirrors final Frameworks gate")

if not runner_ready:
    expected_next_gate="host-kvm-preflight-and-golden-image"
elif runner.get("status")!="PASS":
    expected_next_gate="runner-contract"
elif pkg.get("status")!="PASS":
    expected_next_gate="authoritative-package-proof"
elif sample.get("status")!="PASS":
    expected_next_gate="frameworks-sample-proof"
else:
    expected_next_gate="certification-complete"

req(state.get("next_gate")==expected_next_gate,"authoritative KVM live-state next gate")
req(ci.get("next_gate")==expected_next_gate,"desktop stack next gate mirrors authoritative KVM lifecycle")

if not final_pass:
    req(ci.get("status")=="pending-certification","desktop stack remains pending certification")
req(state.get("stable_publication_authorized") is False,"KVM certification must never auto-authorize stable publication")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("Authoritative KVM certification live state: PASS")
print("host_kvm="+host.get("status","missing"))
print("golden_image="+gold.get("status","missing"))
print("runner_contract="+runner.get("status","missing"))
print("authoritative_package_proof="+pkg.get("status","missing"))
print("frameworks_sample_proof="+sample.get("status","missing"))
print("desktop_release_relevant_authorized="+str(final_pass).lower())
