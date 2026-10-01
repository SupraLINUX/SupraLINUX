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
if runner.get("status")=="INFRA_INVALID":
    hold=runner.get("infrastructure_hold",{})
    req(runner.get("execution_authorized") is False,"INFRA_INVALID runner-contract must be execution-frozen")
    req(hold.get("mechanism")=="github-jit-runner-api","runner-contract INFRA_INVALID mechanism")
    req(isinstance(hold.get("consecutive_infra_invalid"),int) and hold["consecutive_infra_invalid"]>=2,"runner-contract INFRA_INVALID retry cutoff")
    req(hold.get("resume_requires")=="scripts/check-jit-runner-api-lifecycle.sh:PASS","runner-contract resume requires synthetic JIT API PASS")

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
