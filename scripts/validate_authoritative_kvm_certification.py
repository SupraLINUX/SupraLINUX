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
if runner.get("status")=="PASS":
    evidence=runner.get("evidence",[])
    req(len(evidence)==2,"runner-contract PASS evidence set")
    github_evidence=next((x for x in evidence if x.get("kind")=="github-actions-run"),{})
    host_evidence=next((x for x in evidence if x.get("kind")=="host-local-runner-contract-bundle"),{})
    req(github_evidence.get("workflow_run_id")==36814843490,"runner-contract PASS workflow run")
    req(github_evidence.get("workflow_head_sha")=="31b28aa91ec8430159ecaf249dee14121bdb4fde","runner-contract PASS workflow head")
    req(github_evidence.get("job_id")==110217559631,"runner-contract PASS job")
    req(github_evidence.get("conclusion")=="success","runner-contract PASS workflow conclusion")
    artifact=github_evidence.get("artifact",{})
    req(artifact.get("id")==11141310599,"runner-contract PASS artifact ID")
    req(artifact.get("digest")=="sha256:1e227aa48517efb3f8c90075781213dd49b1dfbc7418af43a75dee868d6fbbb7","runner-contract PASS artifact digest")
    req(host_evidence.get("host")=="chmodmasx-h370mds3h","runner-contract PASS host")
    req(host_evidence.get("result")=="PASS","runner-contract host bundle PASS")
    req(host_evidence.get("workflow_run_id")==36814843490,"runner-contract host bundle workflow binding")
    req(host_evidence.get("evidence_manifest_sha256")=="89fa380bc9706e43e9544339cc4372651f3db6884b0de39e158c15119a7cba50","runner-contract host bundle manifest hash")
    host_artifacts=host_evidence.get("artifacts",{})
    expected_host_artifacts={
        "guest-copy-out.txt",
        "host-environment.txt",
        "host-result.json",
        "runner-busy.json",
        "runner-online.json",
        "workflow-run-created.json",
        "workflow-run.json",
    }
    req(set(host_artifacts)==expected_host_artifacts,"runner-contract host bundle artifact set")
    req(all(re.fullmatch(r"[0-9a-f]{64}",str(value)) is not None for value in host_artifacts.values()),"runner-contract host bundle artifact hashes")

if runner.get("status")=="INFRA_INVALID":
    hold=runner.get("infrastructure_hold",{})
    req(runner.get("execution_authorized") is False,"INFRA_INVALID runner-contract must be execution-frozen")
    mechanism=hold.get("mechanism")
    req(mechanism in {"github-jit-runner-api","guest-actions-runner-startup","runner-contract-evidence-capture"},"runner-contract INFRA_INVALID mechanism")
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
    elif mechanism=="runner-contract-evidence-capture":
        req(isinstance(hold.get("consecutive_infra_invalid"),int) and hold["consecutive_infra_invalid"]>=1,"runner-contract evidence-capture incident count")
        req(hold.get("resume_requires")=="repository-policy:PASS-after-runner-contract-evidence-capture-remediation","runner-contract evidence-capture recovery contract")
        incident=hold.get("incident_evidence",{})
        req(incident.get("workflow_run_id")==36813959540,"runner-contract evidence-capture workflow run")
        req(incident.get("job_id")==110214858616,"runner-contract evidence-capture job")
        req(incident.get("failing_step")=="Capture runner contract evidence","runner-contract evidence-capture failing step")
        req("unrecognized arguments: --version" in str(incident.get("failure","")),"runner-contract evidence-capture failure")
        req(incident.get("failure_exit_code")==20,"runner-contract evidence-capture exit code")
        req(incident.get("repository_invariants_ran") is False,"runner-contract evidence-capture must record skipped repository invariants")
        req(incident.get("package_attempt_consumed") is False,"runner-contract evidence-capture must not consume a package attempt")
        artifact=incident.get("partial_artifact",{})
        req(artifact.get("id")==11140222717,"runner-contract evidence-capture artifact ID")
        req(re.fullmatch(r"sha256:[0-9a-f]{64}",str(artifact.get("digest",""))) is not None,"runner-contract evidence-capture artifact digest")

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

closed_evidence_capture=runner.get("closed_evidence_capture_hold",{})
if closed_evidence_capture:
    req(closed_evidence_capture.get("mechanism")=="runner-contract-evidence-capture","closed runner-contract evidence-capture mechanism")
    req(closed_evidence_capture.get("consecutive_infra_invalid")==1,"closed runner-contract evidence-capture incident count")
    req(closed_evidence_capture.get("resume_requires")=="repository-policy:PASS-after-runner-contract-evidence-capture-remediation","closed runner-contract evidence-capture recovery contract")
    req(closed_evidence_capture.get("closed_by")=="repository-policy:PASS-after-runner-contract-evidence-capture-remediation","closed runner-contract evidence-capture closure")
    req(closed_evidence_capture.get("repository_policy_run")==36814180227,"closed runner-contract evidence-capture policy run")
    req(closed_evidence_capture.get("remediation_commit")=="c280d83fcb1c170c15fb6b712e3e3161587c9b56","closed runner-contract evidence-capture remediation commit")
    req(closed_evidence_capture.get("recovery_state")=="runner-contract-pending","closed runner-contract evidence-capture recovery state")
    incident=closed_evidence_capture.get("incident_evidence",{})
    req(incident.get("workflow_run_id")==36813959540,"closed runner-contract evidence-capture workflow run")
    req(incident.get("job_id")==110214858616,"closed runner-contract evidence-capture job")
    req(incident.get("package_attempt_consumed") is False,"closed runner-contract evidence-capture must not consume a package attempt")
    artifact=incident.get("partial_artifact",{})
    req(artifact.get("id")==11140222717,"closed runner-contract evidence-capture artifact ID")
    req(artifact.get("digest")=="sha256:4e7d2f6cf6e2f7743d02f0a3f76dbbc879e610444628d89e947076bb35e35699","closed runner-contract evidence-capture artifact digest")

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
if pkg.get("status")=="INFRA_INVALID":
    hold=pkg.get("infrastructure_hold",{})
    req(pkg.get("execution_authorized") is False,"INFRA_INVALID package proof must be execution-frozen")
    mechanism=hold.get("mechanism")
    if mechanism=="autopkgtest-qemu-acceleration-argv":
        req(isinstance(hold.get("consecutive_infra_invalid"),int) and hold.get("consecutive_infra_invalid")>=2,"package proof repeated infrastructure incident count")
        req(hold.get("resume_requires")=="scripts/check-autopkgtest-qemu-argv-lifecycle.sh:PASS-and-repository-policy:PASS","package proof repeated infrastructure recovery contract")
        diagnosis=hold.get("diagnosis",{})
        req(diagnosis.get("provider")=="autopkgtest 5.55","package proof provider diagnosis")
        req("-enable-kvm" in str(diagnosis.get("provider_behavior","")),"package proof provider -enable-kvm diagnosis")
        req("-enable-kvm" in str(diagnosis.get("first_remediation_gap","")),"package proof first-remediation gap")
        req("-enable-kvm" in str(diagnosis.get("cause","")) and "-accel kvm" in str(diagnosis.get("cause","")),"package proof repeated accelerator cause")
        history=hold.get("incident_history",[])
        req(len(history)==2,"package proof repeated infrastructure history length")
        expected_history=[
            (1,36815641827,"f6de7272b507cb2b9cacc7cb3b4f5fb96c28acc7",110219976560,11141147657,"sha256:cbe9e3bbc6983a72ff94f70d66004cce75af18fa0f9cdfed789bc024f484638d"),
            (2,36817238333,"7b952961c6939a18b855e3814c43479cb6b7b4b7",110224861819,11141369927,"sha256:eac3c15aa99dae57de683862b8758b6f47dca776bfdbd8e3dc88a79e261617be"),
        ]
        for incident,expected in zip(history,expected_history):
            sequence,run_id,head_sha,job_id,artifact_id,artifact_digest=expected
            req(incident.get("sequence")==sequence,f"package proof infrastructure history {sequence} sequence")
            req(incident.get("workflow_run_id")==run_id,f"package proof infrastructure history {sequence} run")
            req(incident.get("workflow_head_sha")==head_sha,f"package proof infrastructure history {sequence} head")
            req(incident.get("job_id")==job_id,f"package proof infrastructure history {sequence} job")
            req(incident.get("stage")=="autopkgtest-qemu",f"package proof infrastructure history {sequence} stage")
            req(incident.get("autopkgtest_exit_code")==16,f"package proof infrastructure history {sequence} autopkgtest exit")
            attempt=incident.get("package_attempt",{})
            req(attempt.get("kind")=="synthetic-certification-package-attempt",f"package proof infrastructure history {sequence} attempt kind")
            req(attempt.get("package")=="supralinux-build-test" and attempt.get("version")=="0.1.0",f"package proof infrastructure history {sequence} package")
            req(attempt.get("execution_started") is True,f"package proof infrastructure history {sequence} execution")
            req(attempt.get("sbuild_result")=="PASS",f"package proof infrastructure history {sequence} sbuild PASS")
            req(attempt.get("canonical_kde_package_state_effect")=="none",f"package proof infrastructure history {sequence} canonical package state")
            artifact=incident.get("artifact",{})
            req(artifact.get("id")==artifact_id,f"package proof infrastructure history {sequence} artifact ID")
            req(artifact.get("digest")==artifact_digest,f"package proof infrastructure history {sequence} artifact digest")
        second=history[1] if len(history)==2 else {}
        req(second.get("qemu_wrapper_sha256")=="f27de04824122ba9b2fa80244c68cabde942a84d3dc1eec8e1e734e24ab7ff32","package proof second incident wrapper hash")
        result=second.get("result_semantics",{})
        req(result.get("state")=="INFRA_INVALID","package proof second incident result state")
        req(result.get("sbuild_result")=="PASS","package proof second incident result sbuild")
        req(result.get("autopkgtest_result")=="testbed-failure","package proof second incident result autopkgtest")
        req(result.get("package_attempt_consumed") is True,"package proof second incident result package attempt")
        req(result.get("canonical_kde_package_state_effect")=="none","package proof second incident result canonical state")
        latest=hold.get("latest_incident",{})
        req(latest.get("workflow_run_id")==36817238333,"package proof latest infrastructure run")
        req(latest.get("job_id")==110224861819,"package proof latest infrastructure job")
        req(latest.get("autopkgtest_exit_code")==16,"package proof latest infrastructure autopkgtest exit")
        req(latest.get("canonical_adjudication")=="INFRA_INVALID","package proof latest infrastructure adjudication")
        req(latest.get("artifact_id")==11141369927,"package proof latest infrastructure artifact ID")
        req(latest.get("artifact_digest")=="sha256:eac3c15aa99dae57de683862b8758b6f47dca776bfdbd8e3dc88a79e261617be","package proof latest infrastructure artifact digest")
    elif mechanism=="autopkgtest-superficial-only-proof":
        req(hold.get("consecutive_infra_invalid")==1,"superficial-only package proof incident count")
        req(hold.get("resume_requires")=="repository-policy:PASS-after-substantive-autopkgtest-remediation","superficial-only package proof recovery contract")
        incident=hold.get("incident_evidence",{})
        req(incident.get("workflow_run_id")==36820141760,"superficial-only package proof workflow run")
        req(incident.get("workflow_head_sha")=="d2fb30b01bec76548ef1bced75d52d7f030c8020","superficial-only package proof workflow head")
        req(incident.get("job_id")==110233743928,"superficial-only package proof job")
        req(incident.get("stage")=="autopkgtest-qemu","superficial-only package proof stage")
        attempt=incident.get("package_attempt",{})
        req(attempt.get("kind")=="synthetic-certification-package-attempt","superficial-only package proof attempt kind")
        req(attempt.get("package")=="supralinux-build-test" and attempt.get("version")=="0.1.0","superficial-only package proof package")
        req(attempt.get("execution_started") is True,"superficial-only package proof execution")
        req(attempt.get("sbuild_result")=="PASS","superficial-only package proof sbuild PASS")
        req(attempt.get("canonical_kde_package_state_effect")=="none","superficial-only package proof canonical package state")
        testbed=incident.get("qemu_kvm_testbed",{})
        req(testbed.get("booted") is True,"superficial-only package proof QEMU testbed boot")
        req(testbed.get("architecture")=="amd64" and testbed.get("release")=="resolute","superficial-only package proof testbed identity")
        autopkg=incident.get("autopkgtest",{})
        req(autopkg.get("version")=="5.55","superficial-only package proof autopkgtest version")
        req(autopkg.get("exit_code")==8,"superficial-only package proof autopkgtest exit")
        req(autopkg.get("smoke_result")=="PASS (superficial)","superficial-only package proof smoke result")
        req(autopkg.get("canonical_adjudication")=="INFRA_INVALID","superficial-only package proof adjudication")
        req(incident.get("raw_result_state_before_semantic_fix")=="FAIL","superficial-only package proof historical raw result")
        artifact=incident.get("artifact",{})
        req(artifact.get("id")==11142903389,"superficial-only package proof artifact ID")
        req(artifact.get("digest")=="sha256:7e23b9b797eb2e99749cf1352ecb869e69fe9dccd529b6890e658a9d081aa61c","superficial-only package proof artifact digest")
        req(artifact.get("result_json_sha256")=="58c6507e18dceea51904d8bc192f50db2718c94e365237effc8d04df71319d0c","superficial-only package proof result hash")
        req(artifact.get("autopkgtest_log_sha256")=="ad340af027a0c713ab9f462b72129630604f4a759f6c9d6edabec7dd8122d03c","superficial-only package proof autopkgtest log hash")
        req(artifact.get("qemu_wrapper_sha256")=="1e74eafbbd4712b9eeb69b6c2e105232ae5f11e635d9fd4b75d117a67e3fb60d","superficial-only package proof wrapper hash")
    else:
        req(False,"unknown active package proof infrastructure mechanism")

closed_pkg_hold=pkg.get("closed_infrastructure_hold",{})
if closed_pkg_hold:
    req(closed_pkg_hold.get("mechanism")=="autopkgtest-qemu-acceleration-argv","closed package proof infrastructure mechanism")
    req(closed_pkg_hold.get("consecutive_infra_invalid")==1,"closed package proof infrastructure incident count")
    req(closed_pkg_hold.get("resume_requires")=="repository-policy:PASS-after-autopkgtest-qemu-acceleration-remediation","closed package proof infrastructure recovery contract")
    req(closed_pkg_hold.get("closed_by")=="repository-policy:PASS-after-autopkgtest-qemu-acceleration-remediation","closed package proof infrastructure closure")
    req(closed_pkg_hold.get("repository_policy_run")==36816437830,"closed package proof infrastructure policy run")
    req(closed_pkg_hold.get("remediation_commit")=="35fc1ce488f2f51a8dc940d55b51866d4a0b7a2b","closed package proof infrastructure remediation commit")
    validation=closed_pkg_hold.get("synthetic_validation",{})
    req(validation.get("qemu_wrapper_test")=="PASS","closed package proof QEMU wrapper synthetic PASS")
    req(validation.get("repository_invariants")=="PASS","closed package proof repository invariants PASS")
    req(validation.get("authoritative_kvm_state_validator")=="PASS","closed package proof KVM state validator PASS")
    req(closed_pkg_hold.get("recovery_state")=="authoritative-package-proof-pending","closed package proof recovery state")
    incident=closed_pkg_hold.get("incident_evidence",{})
    req(incident.get("workflow_run_id")==36815641827,"closed package proof infrastructure workflow run")
    req(incident.get("job_id")==110219976560,"closed package proof infrastructure job")
    attempt=incident.get("package_attempt",{})
    req(attempt.get("execution_started") is True,"closed package proof synthetic attempt execution")
    req(attempt.get("sbuild_result")=="PASS","closed package proof synthetic attempt sbuild PASS")
    req(attempt.get("canonical_kde_package_state_effect")=="none","closed package proof incident must not alter canonical KDE package state")
    artifact=incident.get("artifact",{})
    req(artifact.get("id")==11141147657,"closed package proof infrastructure artifact ID")
    req(artifact.get("digest")=="sha256:cbe9e3bbc6983a72ff94f70d66004cce75af18fa0f9cdfed789bc024f484638d","closed package proof infrastructure artifact digest")

closed_repeated_pkg_hold=pkg.get("closed_repeated_infrastructure_hold",{})
if closed_repeated_pkg_hold:
    req(closed_repeated_pkg_hold.get("mechanism")=="autopkgtest-qemu-acceleration-argv","closed repeated package proof mechanism")
    req(closed_repeated_pkg_hold.get("consecutive_infra_invalid")==2,"closed repeated package proof incident count")
    req(closed_repeated_pkg_hold.get("resume_requires")=="scripts/check-autopkgtest-qemu-argv-lifecycle.sh:PASS-and-repository-policy:PASS","closed repeated package proof recovery contract")
    req(closed_repeated_pkg_hold.get("closed_by")=="synthetic-autopkgtest-qemu-argv-preflight-and-repository-policy:PASS","closed repeated package proof closure")
    req(closed_repeated_pkg_hold.get("repository_policy_run")==36819196488,"closed repeated package proof policy run")
    req(closed_repeated_pkg_hold.get("repository_policy_job")==110230862901,"closed repeated package proof policy job")
    req(closed_repeated_pkg_hold.get("recovery_head_sha")=="3cba7dc932ab062bc78dbe61a138c46bb341ef95","closed repeated package proof recovery head")
    remediation_commits=closed_repeated_pkg_hold.get("remediation_commits",[])
    req(remediation_commits[-1:] == ["3cba7dc932ab062bc78dbe61a138c46bb341ef95"],"closed repeated package proof remediation head")
    recovery=closed_repeated_pkg_hold.get("synthetic_recovery_evidence",{})
    req(recovery.get("shellcheck")=="PASS","closed repeated package proof shellcheck PASS")
    req(recovery.get("qemu_wrapper_functional_test")=="PASS","closed repeated package proof wrapper PASS")
    req(recovery.get("autopkgtest_qemu_argv_lifecycle")=="PASS","closed repeated package proof argv lifecycle PASS")
    req(recovery.get("autopkgtest_version")=="5.55","closed repeated package proof autopkgtest version")
    req(recovery.get("provider_contract")=="-enable-kvm","closed repeated package proof provider contract")
    req(recovery.get("normalized_acceleration")=="-accel kvm","closed repeated package proof normalized acceleration")
    req(recovery.get("repository_invariants")=="PASS","closed repeated package proof repository invariants PASS")
    req(recovery.get("authoritative_kvm_state_validator")=="PASS","closed repeated package proof KVM state validator PASS")
    req(closed_repeated_pkg_hold.get("recovery_state")=="authoritative-package-proof-pending","closed repeated package proof recovery state")
    req(closed_repeated_pkg_hold.get("retry_authorized") is True,"closed repeated package proof retry authorization")
    history=closed_repeated_pkg_hold.get("incident_history",[])
    req(len(history)==2,"closed repeated package proof incident history")
    req([x.get("workflow_run_id") for x in history]==[36815641827,36817238333],"closed repeated package proof incident runs")
    req(all(x.get("package_attempt",{}).get("sbuild_result")=="PASS" for x in history),"closed repeated package proof sbuild history")
    req(all(x.get("package_attempt",{}).get("canonical_kde_package_state_effect")=="none" for x in history),"closed repeated package proof canonical package state")

closed_superficial_pkg_hold=pkg.get("closed_superficial_only_infrastructure_hold",{})
if closed_superficial_pkg_hold:
    req(closed_superficial_pkg_hold.get("mechanism")=="autopkgtest-superficial-only-proof","closed superficial-only package proof mechanism")
    req(closed_superficial_pkg_hold.get("consecutive_infra_invalid")==1,"closed superficial-only package proof incident count")
    req(closed_superficial_pkg_hold.get("resume_requires")=="repository-policy:PASS-after-substantive-autopkgtest-remediation","closed superficial-only package proof recovery contract")
    req(closed_superficial_pkg_hold.get("closed_by")=="repository-policy:PASS-after-substantive-autopkgtest-remediation","closed superficial-only package proof closure")
    req(closed_superficial_pkg_hold.get("repository_policy_run")==36820787722,"closed superficial-only package proof policy run")
    req(closed_superficial_pkg_hold.get("repository_policy_job")==110235765685,"closed superficial-only package proof policy job")
    req(closed_superficial_pkg_hold.get("remediation_head_sha")=="361d4ceb2d4ee3a06cbb6e218340b5cf2f4299ae","closed superficial-only package proof remediation head")
    validation=closed_superficial_pkg_hold.get("synthetic_validation",{})
    req(validation.get("shellcheck")=="PASS","closed superficial-only shellcheck PASS")
    req(validation.get("qemu_wrapper_functional_test")=="PASS","closed superficial-only QEMU wrapper PASS")
    req(validation.get("autopkgtest_qemu_argv_lifecycle")=="PASS","closed superficial-only QEMU argv lifecycle PASS")
    req(validation.get("repository_invariants")=="PASS","closed superficial-only repository invariants PASS")
    req(validation.get("authoritative_kvm_state_validator")=="PASS","closed superficial-only KVM state validator PASS")
    req(validation.get("smoke_test_superficial_restriction_absent") is True,"closed superficial-only smoke test must be substantive")
    req(validation.get("autopkgtest_exit_8_classification")=="INFRA_INVALID","closed superficial-only exit 8 classification")
    req(closed_superficial_pkg_hold.get("recovery_state")=="authoritative-package-proof-pending","closed superficial-only recovery state")
    req(closed_superficial_pkg_hold.get("retry_authorized") is True,"closed superficial-only retry authorization")
    incident=closed_superficial_pkg_hold.get("incident_evidence",{})
    req(incident.get("workflow_run_id")==36820141760,"closed superficial-only incident run")
    req(incident.get("job_id")==110233743928,"closed superficial-only incident job")
    attempt=incident.get("package_attempt",{})
    req(attempt.get("sbuild_result")=="PASS","closed superficial-only incident sbuild PASS")
    req(attempt.get("canonical_kde_package_state_effect")=="none","closed superficial-only incident canonical package state")
    autopkg=incident.get("autopkgtest",{})
    req(autopkg.get("exit_code")==8,"closed superficial-only incident autopkgtest exit")
    req(autopkg.get("smoke_result")=="PASS (superficial)","closed superficial-only incident smoke result")
    artifact=incident.get("artifact",{})
    req(artifact.get("id")==11142903389,"closed superficial-only incident artifact ID")
    req(artifact.get("digest")=="sha256:7e23b9b797eb2e99749cf1352ecb869e69fe9dccd529b6890e658a9d081aa61c","closed superficial-only incident artifact digest")

if pkg.get("status")=="PASS":
    req(pkg.get("execution_authorized") is False,"package proof PASS must close package-proof execution authorization")
    evidence=pkg.get("evidence",[])
    req(len(evidence)==3,"package proof PASS evidence set")
    github=next((x for x in evidence if x.get("kind")=="github-actions-authoritative-package-proof-pass"),{})
    req(github.get("workflow_run_id")==36821470840,"package proof PASS workflow run")
    req(github.get("workflow_head_sha")=="985bb09eadb9c8ebd5d48d58f84aeedf55831e14","package proof PASS workflow head")
    req(github.get("workflow_checkout_merge_sha")=="a859f3b13ea2549993c90825ab13a4c4cef9b03a","package proof PASS checkout merge")
    req(github.get("job_id")==110237761112 and github.get("conclusion")=="success","package proof PASS job")
    result=github.get("result",{})
    req(result.get("state")=="PASS" and result.get("exit_code")==0 and result.get("stage")=="complete","package proof PASS result")
    req(result.get("authoritative") is True and result.get("package_attempt_consumed") is True,"package proof PASS authoritative attempt")
    req(result.get("canonical_kde_package_state_effect")=="none","package proof PASS canonical KDE state")
    req(result.get("sbuild_result")=="PASS" and result.get("autopkgtest_result")=="PASS" and result.get("autopkgtest_exit_code")==0,"package proof PASS build/system test")
    artifact=github.get("artifact",{})
    req(artifact.get("id")==11143842131,"package proof PASS artifact ID")
    req(artifact.get("digest")=="sha256:3a67e29341afa78c29cae1d29e1849659aa47825b160c6ce1fe84dc12f17ba02","package proof PASS artifact digest")
    req(artifact.get("files",{}).get("result.json")=="a4d15540ebe223efea74650b27cd2aa9ee70a95d7f2c47c54ff3d5c6c161c7b0","package proof PASS result hash")
    host_bundle=next((x for x in evidence if x.get("kind")=="host-local-package-proof-bundle"),{})
    req(host_bundle.get("workflow_run_id")==36821470840 and host_bundle.get("host_result_exit_code")==0,"package proof PASS host bundle")
    req(host_bundle.get("evidence_manifest_sha256")=="4311ddf6967d746c44adced1ff39d840197a267566f25a125d6027549ced60a2","package proof PASS host bundle seal")
    req(host_bundle.get("workspace_evidence_exported") is False,"package proof historical host bundle must preserve workspace export gap")
    supplemental=next((x for x in evidence if x.get("kind")=="host-local-supplemental-package-proof-archive"),{})
    req(supplemental.get("workflow_run_id")==36821470840 and supplemental.get("artifact_id")==11143842131,"package proof PASS supplemental archive binding")
    req(supplemental.get("result_json_sha256")=="a4d15540ebe223efea74650b27cd2aa9ee70a95d7f2c47c54ff3d5c6c161c7b0","package proof PASS supplemental result hash")
    req(supplemental.get("evidence_manifest_sha256")=="6e87286d11f08fc00b0f9f011e37869f97613dbaad20deb67195084c3964191f","package proof PASS supplemental archive seal")
    if sample.get("status")=="pending":
        req(sample.get("execution_authorized") is True,"package proof PASS must authorize pending Frameworks sample")
    elif sample.get("status")=="PASS":
        req(sample.get("execution_authorized") is False,"completed Frameworks sample must close execution authorization")
    else:
        req(False,"package proof PASS requires Frameworks sample pending or PASS")

if pkg.get("execution_authorized"):
    req(runner.get("status")=="PASS" and pkg.get("status")=="pending","package proof authorization requires runner-contract PASS")
    req(not pkg.get("infrastructure_hold"),"execution-authorized package proof cannot retain an active infrastructure hold")
    if closed_repeated_pkg_hold:
        req(closed_repeated_pkg_hold.get("retry_authorized") is True,"package proof retry requires certified repeated-infra recovery")
    if closed_superficial_pkg_hold:
        req(closed_superficial_pkg_hold.get("retry_authorized") is True,"package proof retry requires certified substantive-test recovery")
if sample.get("execution_authorized"):
    req(pkg.get("status")=="PASS" and sample.get("status")=="pending","Frameworks sample authorization requires package proof PASS")

host_orchestrator=(ROOT / "scripts/run-kvm-jit-gate-core.sh").read_text()
req('REPOSITORY_NAME="${REPOSITORY##*/}"' in host_orchestrator,"host orchestrator must derive repository name for workspace evidence export")
req('/opt/actions-runner/_work/${REPOSITORY_NAME}/${REPOSITORY_NAME}/evidence' in host_orchestrator,"host orchestrator must export workflow workspace evidence")
req('guest-files/workspace' in host_orchestrator,"host orchestrator must isolate workspace evidence from golden-image evidence")

s=sample.get("sample",{})
req(s.get("framework")=="karchive","Frameworks certification sample")
req(s.get("package_version")=="6.30.0-0supralinux4","KArchive sample package version")
req(s.get("ecm_predecessor")=="6.30.0-0supralinux3","KArchive sample ECM predecessor")
req(s.get("package_state_effect")=="none","Frameworks sample must not alter canonical package state")

if sample.get("status")=="PASS":
    req(sample.get("execution_authorized") is False,"Frameworks sample PASS must close execution authorization")
    evidence=sample.get("evidence",[])
    req(len(evidence)==2,"Frameworks sample PASS evidence set")
    github=next((x for x in evidence if x.get("kind")=="github-actions-authoritative-frameworks-sample-pass"),{})
    req(github.get("workflow_run_id")==36823362745,"Frameworks sample PASS workflow run")
    req(github.get("workflow_head_sha")=="7125f11efee46e478a37b010d89d4896ed5e61bf","Frameworks sample PASS workflow head")
    req(github.get("workflow_checkout_merge_sha")=="eb5adde4b605afa4d32c7029c1ff43f387ddcb28","Frameworks sample PASS checkout merge")
    req(github.get("job_id")==110243543920 and github.get("conclusion")=="success","Frameworks sample PASS job")
    result=github.get("result",{})
    req(result.get("node")=="karchive" and result.get("state")=="PASS" and result.get("exit_code")==0,"Frameworks sample PASS result")
    req(result.get("stage")=="complete" and result.get("authoritative") is True,"Frameworks sample PASS authoritative completion")
    req(result.get("run_kind")=="authoritative-certification-sample","Frameworks sample PASS run kind")
    req(result.get("package_execution_started") is True and result.get("package_state_effect")=="none","Frameworks sample PASS package semantics")
    req(result.get("canonical_package_version")=="6.30.0-0supralinux4","Frameworks sample PASS package version")
    retained=github.get("retained_inputs",{})
    req(retained.get("ecm_run")==34694951158 and retained.get("ecm_artifact")==10298635300,"Frameworks sample retained ECM evidence")
    req(retained.get("ecm_version")=="6.30.0-0supralinux3","Frameworks sample retained ECM version")
    req(retained.get("ecm_deb_sha256")=="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f","Frameworks sample retained ECM hash")
    req(retained.get("karchive_run")==34884764702 and retained.get("karchive_artifact")==10364726750,"Frameworks sample retained KArchive evidence")
    validation=github.get("validation",{})
    req(validation.get("upstream_ctest")=="5/5 PASS","Frameworks sample upstream tests")
    req(validation.get("lintian")=="completed-with-warnings","Frameworks sample Lintian result")
    req(validation.get("consumer_configure")=="PASS" and validation.get("consumer_build")=="PASS","Frameworks sample consumer proof")
    artifact=github.get("artifact",{})
    req(artifact.get("id")==11143244708,"Frameworks sample PASS artifact ID")
    req(artifact.get("digest")=="sha256:2419e353f66856bb398cf1d72e50b7d4d12a282ff675d8fb3b42afd595729e76","Frameworks sample PASS artifact digest")
    req(artifact.get("files",{}).get("result.json")=="44b8ae4d1fcd94ab8453941ca7fc5d55956068ed41852b9f036acebfb793dd00","Frameworks sample PASS result hash")
    host=next((x for x in evidence if x.get("kind")=="host-local-frameworks-sample-bundle"),{})
    req(host.get("workflow_run_id")==36823362745 and host.get("host_result_exit_code")==0,"Frameworks sample host bundle binding")
    req(host.get("workspace_evidence_exported") is True,"Frameworks sample workspace evidence export")
    req(host.get("workspace_result_json_sha256")=="44b8ae4d1fcd94ab8453941ca7fc5d55956068ed41852b9f036acebfb793dd00","Frameworks sample host result hash")
    req(host.get("evidence_manifest_sha256")=="293e4847e6460dec41ff8c798ab9222b2fa3d4100457121ce6b28a8a8e59a903","Frameworks sample host bundle seal")

release=state.get("release_relevant_desktop",{})
final_pass=sample.get("status")=="PASS"
if final_pass:
    req(release.get("status")=="unlocked","final sample PASS must unlock release-relevant desktop state")
    req(release.get("plasma_authorized") is True,"Plasma release-relevant work unlocked")
    req(release.get("kwin_authorized") is True,"KWin release-relevant work unlocked")
    req(release.get("session_authorized") is True,"session release-relevant work unlocked")
    req(release.get("unlocked_by")=="frameworks-sample-proof:PASS","desktop unlock provenance")
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

if final_pass:
    req(ci.get("status")=="certified","desktop stack must record completed authoritative certification")
else:
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
