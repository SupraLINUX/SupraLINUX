#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

closure=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level3_attempt1_closure.py")])
if closure.returncode:
    raise SystemExit(closure.returncode)

c=load("manifests/kde-tier3-package-contracts.json")
m=load("manifests/kde-tier3-materialization.json")
t=load("manifests/kde-frameworks-tier3.json")
l3=load("manifests/kde-tier3-build-level3.json")
a=load("manifests/kde-tier3-build-level3-attempts.json")
support=load("manifests/kde-tier3-support-build-level1.json")

T=["ktexteditor","purpose"]
VERS={"ktexteditor":"6.30.0-0supralinux2","purpose":"6.30.0-0supralinux2"}
SNAP="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
TRIGGER={"attempt":1,"workflow_run":36607647059,"commit":"2692489bdb861520181df486c524efb9cdf47d60","failed_nodes":T,"rootfs_artifact_id":11051807633,"rootfs_artifact_sha256":"08eb26b3d264c79e26dd0f5e1cb6fe543a16e1f2be0f713bab5fee45cabdbd83"}

for obj,name in ((c.get("level3_remediation",{}),"contracts"),(m.get("level3_remediation",{}),"materialization"),(t.get("level3_remediation",{}),"canonical"),(l3.get("level3_remediation",{}),"level3")):
    req(obj.get("status")=="materialization-pending-ci",name+": Level3 remediation status")
    req(obj.get("trigger")==TRIGGER,name+": Level3 remediation trigger")
    req(obj.get("candidate_package_versions")==VERS,name+": candidate versions")
    req(obj.get("package_attempted") in {None,False},name+": no package attempt")

req(c["level3_remediation"].get("materialization_authorized") is True and c["level3_remediation"].get("package_build_authorized") is False,"contract materialization/package authorization")
req(m.get("state")=="remediation-pending-ci" and m.get("remediation_queue")==["ktexteditor"],"Level3 remediation materialization queue")
req(m.get("package_attempted") is False and m.get("package_state_effect")=="none","materialization has no package state effect")
req(m["level3_remediation"].get("materialization_authorized") is True and m["level3_remediation"].get("package_execution_authorized") is False,"materialization execution boundary")
req(t.get("discovery_policy",{}).get("phase")=="build-level3-remediation-planning","canonical remediation phase")
req(t.get("discovery_policy",{}).get("package_builds")=="tier3-level3-remediation-pending-materialization","canonical materialization gate")
req(t.get("discovery_policy",{}).get("remediation")=="level3-attempt1-remediation-materialization","canonical remediation marker")
req(t.get("build_level3",{}).get("status")=="attempt1-closed-FAIL" and t.get("build_level3",{}).get("execution_authorized") is False,"binary Level3 remains closed")
req(t["level3_remediation"].get("materialization_authorized") is True and t["level3_remediation"].get("package_execution_authorized") is False,"canonical source-only authorization")
req(t["level3_remediation"].get("canonical_snapshot")==SNAP and t["level3_remediation"].get("current_attempt")==1 and t["level3_remediation"].get("next_attempt")==2,"canonical snapshot/attempt markers")
req(l3.get("state")=="FAIL" and l3.get("execution_authorized") is False and l3.get("current_attempt")==1 and l3.get("next_attempt")==2,"Level3 package execution remains paused")
req(l3.get("canonical_snapshot")==SNAP and l3.get("next_gate")=="tier3-level3-remediation-materialization-evidence","Level3 remediation next gate")
req(len(a.get("campaign_history",[]))==1 and all(len(a.get("nodes",{}).get(x,[]))==1 for x in T),"Attempt2 has not consumed package execution")

progress=m.get("level3_remediation",{}).get("materialization_progress",{})
req(progress.get("workflow_run")==36614234522 and progress.get("result")=="PARTIAL","Level3 partial materialization evidence")
req(progress.get("PASS")==["purpose"] and progress.get("INFRA_INVALID")==["ktexteditor"] and progress.get("package_attempted") is False,"Level3 partial materialization classification")
inc=progress.get("infrastructure_incident",{})
req(inc.get("classification")=="INFRA_INVALID" and inc.get("node")=="ktexteditor" and inc.get("job_id")==109563580419 and inc.get("artifact_id")==11055071212 and inc.get("package_attempted") is False,"KTextEditor materialization infrastructure incident")

ktm=m["nodes"]["ktexteditor"]
req(ktm.get("state")=="remediation-pending" and ktm.get("candidate_package_version")==VERS["ktexteditor"],"KTextEditor materialization remains pending")
req(ktm.get("retained_previous_evidence",{}).get("result")=="PASS" and ktm.get("materialization_incident",{}).get("classification")=="INFRA_INVALID","KTextEditor retained source/incident")

pum=m["nodes"]["purpose"]; pev=pum.get("evidence",{})
req(pum.get("state")=="materialized" and pum.get("package_version")==VERS["purpose"] and pum.get("candidate_package_version")==VERS["purpose"],"Purpose remediation materialized")
req(pev.get("workflow_run")==36614234522 and pev.get("job_id")==109563580375 and pev.get("artifact_id")==11054941469 and pev.get("artifact_sha256")=="b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7","Purpose materialization artifact")
req(pev.get("result")=="PASS" and pev.get("package_attempted") is False and pev.get("package_state_effect")=="none","Purpose source-only materialization PASS")
req(pev.get("package_version")==VERS["purpose"] and pev.get("materialized_tree_sha256")=="b320bfaaba55b2a76adbfd2b4f5354b4315de6926672eafcf239d4ad348020bc","Purpose materialized version/tree")
req(pum.get("retained_previous_evidence",{}).get("result")=="PASS","Purpose previous materialization retained")
    node=next(n for n in t["nodes"] if n["id"]==x)
    req(node.get("state")=="FAIL" and node.get("packaging",{}).get("state")=="FAIL" and node.get("packaging",{}).get("downstream_eligible") is False,x+": canonical FAIL retained")

kt=c["nodes"]["ktexteditor"]
req(kt.get("package_version_candidate")==VERS["ktexteditor"],"KTextEditor revision")
rr=kt.get("rules_text_replacements",[])
req(any(x.get("old")=="\tdh_auto_test" and x.get("new")=="\tdh_auto_test --no-parallel" and x.get("expected_count")==1 for x in rr),"KTextEditor serialized full test suite")
sp=kt.get("supralinux_source_patches",[])
req(len([x for x in sp if x.get("name")=="supralinux-test-abouttosave-writable-copy.patch"])==1,"KTextEditor writable-save test patch")
kp=next((x for x in sp if x.get("name")=="supralinux-test-abouttosave-writable-copy.patch"),{})
req(kp.get("target")=="autotests/src/katedocument_test.cpp","KTextEditor test-only patch target")
req(kp.get("expected_patch_sha256")=="4ea0fea28a883661eb59bf6cf516e88cf7f623341218821dc2c6460206c07443","KTextEditor patch digest")
req(kp.get("expected_source_sha256")=="2d09ae4a05f7c0934a9a181998ff7be151eec0b78642103ddb617c56bc3bf538","KTextEditor patched source digest")

pu=c["nodes"]["purpose"]
req(pu.get("package_version_candidate")==VERS["purpose"],"Purpose revision")
rels=pu.get("source_build_relation_overrides",[])
req(any(x.get("action")=="ensure" and x.get("relation")=="kio6 (>= 6.30.0~) <!nocheck>" for x in rels),"Purpose KIO worker runtime provider")
prr=pu.get("rules_text_replacements",[])
req(any(x.get("old")=="\tdh_auto_test" and x.get("new")=="\tQT_QPA_PLATFORM=offscreen dh_auto_test" and x.get("expected_count")==1 for x in prr),"Purpose headless Qt test environment")

kded=support.get("nodes",{}).get("kded",{})
pev=kded.get("pass_evidence",{})
expected_kded={"version":"6.30.0-0supralinux1","workflow_run":35721085911,"artifact_id":10691372157,"artifact_sha256":"ff8756cf6efb4746568fa032cfb17cdf5c6b47bc31f532130936536aecb7c5c9","expected_binary_packages":["kded6","kded6-dev"],"dev_package":"kded6-dev","provenance":"tier3-support-level1-pass"}
req(kded.get("state")=="PASS" and kded.get("downstream_eligible") is True,"KDED support PASS")
req(pev.get("workflow_run")==35721085911 and pev.get("artifact_id")==10691372157 and pev.get("artifact_sha256")==expected_kded["artifact_sha256"],"KDED support evidence")
req(l3.get("support_predecessors",{}).get("kded")==expected_kded,"Level3 exact KDED support pin")
for x in T:
    req(l3["nodes"][x].get("support_input_ids")==["breeze-icons","kdoctools","kded"],x+": complete support solver closure")

req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval contract")
req(m.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval materialization")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 3 remediation definition: PASS")
print("source-rematerialization=ktexteditor,purpose; candidate=6.30.0-0supralinux2")
print("package-execution-authorized=false")
