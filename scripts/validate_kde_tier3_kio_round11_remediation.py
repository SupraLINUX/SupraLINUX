#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/"manifests/kde-tier3-kio-round11-remediation.json").read_text())
T=json.loads((ROOT/"manifests/kde-frameworks-tier3.json").read_text())
L=json.loads((ROOT/"manifests/kde-tier3-build-level1.json").read_text())
C=json.loads((ROOT/"manifests/kde-tier3-package-contracts.json").read_text())
M=json.loads((ROOT/"manifests/kde-tier3-materialization.json").read_text())
G=json.loads((ROOT/"manifests/kde-dag.json").read_text())
Q=json.loads((ROOT/"manifests/kde-tier3-kio-round11-diagnostic.json").read_text())
errors=[]
def req(v,m):
    if not v: errors.append(m)

req(D.get("schema")==1 and D.get("node")=="kio" and D.get("round")==11,"Round11 definition identity")
req(D.get("status")=="definition-pending-validation" and D.get("claim")=="non-executable-remediation-definition","Round11 definition lifecycle")
req(D.get("canonical_state_effect")=="none" and D.get("execution_authorized") is False and D.get("source_materialization_authorized") is False,"Round11 definition must be non-executable")

policy=T.get("discovery_policy",{})
req(policy.get("package_builds")=="tier3-level1-attempt6-closed","canonical execution gate must remain Attempt6 closed")
req(policy.get("phase")=="build-level1","canonical phase must remain closed Level1")
nodes={x["id"]:x for x in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux6","KIO canonical FAIL/-6 retained")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO remains non-eligible")
req(nodes["kxmlgui"].get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux5","KXMLGui canonical PASS/-5 retained")
req(nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"KXMLGui remains downstream eligible")
req("kio" not in G.get("nodes",{}),"KIO FAIL remains absent from canonical DAG")
req(G.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","KXMLGui remains canonical DAG PASS")

req(L.get("state")=="attempt6-closed-mixed" and L.get("execution_authorized") is False,"Level1 remains Attempt6 closed")
req(L.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","canonical snapshot unchanged")
req(L.get("current_attempt")==6 and L.get("next_gate")=="tier3-round11-kio-remediation-definition","canonical next gate remains definition until validation")

ev=D.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36071103806 and ev.get("job_id")==107872008601,"diagnostic run/job")
req(ev.get("artifact_id")==10837734340 and ev.get("artifact_sha256")=="d4d944ac656d755ebd8c828d1e84c1b735e076c26a17adc66da42f0464a8cedc","diagnostic artifact")
req(ev.get("closure_commit")=="5f057d6abcdd767f97856d83ce7d7fb0caa0bca0","diagnostic closure commit")
req(ev.get("closure_repository_policy_run")==36071666308 and ev.get("closure_diagnostic_run")==36071666343,"diagnostic closure validation runs")
req(Q.get("status")=="diagnostic-PASS","diagnostic manifest must be closed PASS")
qr=Q.get("diagnostic_results",{})
req(qr.get("cmake_environment_modification",{}).get("result")=="PASS","ENVIRONMENT_MODIFICATION proof")
req(qr.get("qt_breeze_icon_resolution",{}).get("result")=="PASS","Qt/Breeze proof")
req(qr.get("krecentdocument",{}).get("result")=="UNRESOLVED-HYPOTHESIS","KRecentDocument remains unresolved")

plan=D.get("attempt7_plan",{})
req(plan.get("source_changed_nodes")==["kio"],"Attempt7 source-changed scope")
req(plan.get("retained_revalidation_nodes")==["kxmlgui"],"Attempt7 retained revalidation scope")
req(plan.get("source_materialization_nodes")==["kio"],"Attempt7 KIO-only materialization")
req(plan.get("full_level1_rerun_nodes")==["kio","kxmlgui"],"Attempt7 complete Level1 rerun scope")
req(plan.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux7","kxmlgui":"6.30.0-0supralinux5"},"Attempt7 versions")
req(plan.get("package_revision_bump_required") is True and plan.get("rematerialize_only_changed_nodes") is True and plan.get("full_level1_rerun_required") is True,"Attempt7 policy")

delta=D.get("planned_contract_delta",{})
req(delta.get("upstream_source_changed") is False and delta.get("packaging_source_changed") is True and delta.get("test_suppression") is False,"Round11 delta classification")
frm=delta.get("from",{}); to=delta.get("to",{})
req(frm.get("cmake_property")=="ENVIRONMENT" and frm.get("operation")=="set_tests_properties","Round10 destructive mechanism identity")
req(to.get("cmake_property")=="ENVIRONMENT_MODIFICATION","Round11 non-destructive mechanism")
req(to.get("affected_tests")==["kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"],"Round11 targeted test scope")
req(to.get("modifications")==["QT_QPA_PLATFORM=set:xcb","QT_QPA_SYSTEM_ICON_THEME=set:breeze"],"Round11 exact environment modifications")
req("QT_PLUGIN_PATH" in to.get("preserves",[]),"Round11 preserves QT_PLUGIN_PATH")

# Executable contract/materialization must remain the validated -6 baseline until activation.
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")=="6.30.0-0supralinux6","executable KIO contract must remain -6 before definition PASS")
rr=kc.get("rules_text_replacements",[])
req(any("set_tests_properties(kiowidgets-kdirmodeltest PROPERTIES ENVIRONMENT" in x.get("new","") for x in rr),"Round10 executable test adaptation retained until activation")
req(not any("ENVIRONMENT_MODIFICATION" in x.get("new","") for x in rr),"Round11 delta must not be executable before validation")
req(M.get("state")=="PASS","materialization baseline remains PASS")
req("remediation_queue" not in M,"no executable materialization queue before definition validation")
req(M.get("nodes",{}).get("kio",{}).get("package_version")=="6.30.0-0supralinux6","materialized KIO baseline remains -6")

kr=D.get("krecentdocument_policy",{})
req(kr.get("source_patch_authorized") is False and kr.get("suppression_authorized") is False and kr.get("exclusion_authorized") is False,"KRecentDocument conservative policy")
req(kr.get("next_attempt_behavior")=="remain-fatal","KRecentDocument remains fatal")

ap=D.get("activation_policy",{})
req(ap.get("prerequisite")=="Repository Policy PASS for this definition","activation prerequisite")
req(D.get("next_gate")=="tier3-round11-definition-validation","definition next gate")
req(D.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Round 11 remediation definition: PASS")
print("definition-only; canonical/executable manifests unchanged")
print("candidate KIO=6.30.0-0supralinux7; retained KXMLGui=6.30.0-0supralinux5")
