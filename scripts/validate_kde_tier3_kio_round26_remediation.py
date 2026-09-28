#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round26-remediation.json")
R25=load("manifests/kde-tier3-kio-round25-remediation.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round26-remediation.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round26-diagnostic.sh").read_text()
HOOK=(ROOT/"scripts/run-kde-tier3-kio-round26-hook.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round26-remediation.md").read_text()
R11=(ROOT/"scripts/validate_kde_tier3_round11.py").read_text()

req(M.get("schema")==1 and M.get("round")==26 and M.get("node")=="kio","Round26 identity")
req(M.get("status")=="definition-pending-ci" and M.get("execution_authorized") is True,"Round26 execution")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round26 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round26 no promotion/suppression")
req(R25.get("status")=="remediation-FAIL-contract","Round25 historical contract retained")
ri=R25.get("interpretation",{})
req(ri.get("historical_contract_result")=="FAIL" and ri.get("target_krecent_remediation")=="PASS","Round25 target/contract distinction")

pred=M.get("predecessor_round25",{})
req(pred.get("workflow_run")==36359842892 and pred.get("job_id")==108734756942 and pred.get("artifact_id")==10945592004,"Round26 predecessor evidence")
req(pred.get("artifact_sha256")=="0ac55c97c3efb725bd46500d9f899fcc0222368f8b60973b574356975b2dd1ce","Round26 predecessor artifact")
req(pred.get("candidate_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Round26 exact KRecent candidate")

up=M.get("kdirmodel_upstream_check",{})
req(up.get("test_v630_sha")==up.get("test_master_sha")=="1d9d47f086a2605f76ceb31581111000a83bfba4","KDirModel test unchanged")
req(up.get("implementation_v630_sha")==up.get("implementation_master_sha")=="35afa32a7fc2284d05dbcc6d7edadbf7ed59d98c","KDirModel implementation unchanged")
req(up.get("default_show_hidden_files") is False,"KCoreDirLister hidden default")
req(up.get("kcoredirlister_v630_sha")=="b9f7c8ba925d4b72bb724d49e8eef16dc3b06b48","KCoreDirLister v6.30 source")

hyp=M.get("hypothesis",{})
req(hyp.get("classification")=="hidden-home-path-causality-candidate","Round26 hypothesis")
req("/debian/.supralinux-test-home/sbuild" in hyp.get("historical_home",""),"Round26 hidden HOME")
req("/debian/supralinux-test-home/sbuild" in hyp.get("visible_control_home",""),"Round26 visible HOME")
req(hyp.get("production_change_authorized") is False,"Round26 no production change")

comb=M.get("combined_remediation",{})
req(comb.get("krecent_candidate_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Round26 reused patch")
home=comb.get("packaging_home_change",{})
req(home.get("source_code_change") is False and home.get("package_runtime_change") is False and home.get("test_environment_only") is True,"Round26 HOME remediation scope")

matrix=M.get("diagnostic_matrix",[])
req([(x.get("id"),x.get("repetitions")) for x in matrix]==[("hidden-home",10),("visible-home",20),("full-suite-visible",1)],"Round26 matrix")
v=M.get("validity_contract",{})
for key in ("exact_attempt8_rootfs","exact_attempt8_source_materialization","exact_attempt8_predecessor_artifacts","exact_sbuild_unshare_mode","historical_dpkg_buildpackage_required","remediation_runs_from_override_dh_auto_test","exact_round25_krecent_candidate_patch_required","hidden_lane_requires_exact_historical_kdirmodel_signature","visible_lane_requires_zero_kdirmodel_failures","full_suite_visible_requires_69_of_69","full_suite_requires_krecent_and_kdirmodel_pass","full_suite_krecent_final_order_12_13_14","hidden_and_visible_test_homes_removed_before_exit","test_and_core_sources_restored_before_exit","canonical_source_artifact_unchanged","no_candidate_package_artifacts"):
    req(v.get(key) is True,"Round26 validity "+key)

next_gate="tier3-round26-kio-combined-remediation-evidence"
policy=T.get("discovery_policy",{})
req(policy.get("package_builds")=="tier3-round26-remediation-pending","Round26 live gate")
req(policy.get("remediation")=="round26-kdirmodel-hidden-home-causality-and-combined-remediation-pending-ci","Round26 live remediation")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="round26-remediation-pending-ci",name+" Round26 status")
    req(obj.get("next_gate")==next_gate,name+" Round26 gate")
    req(obj.get("execution_authorized") is False,name+" package execution blocked")
    d=obj.get("round26_definition",{})
    req(d.get("status")=="definition-pending-ci" and d.get("matrix")=={"hidden-home":10,"visible-home":20,"full-suite-visible":1},name+" Round26 definition")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("next_attempt")==9,"Attempt9 remains unauthorized")
req(M.get("next_gate")==next_gate,"Round26 next gate")
req('gate=="tier3-round26-remediation-pending"' in R11 and "validate_kde_tier3_kio_round26_remediation.py" in R11,"Round11 routes Round26")

req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round26 workflow reusable/manual")
for token in ("10904512642","10898999142","0.91.2ubuntu3","Command: dpkg-buildpackage --sanitize-env -us -uc -b","SUPRALINUX_ROUND26_EVIDENCE_BASE64_BEGIN","hidden-home-causality-and-combined-kio-remediation-PASS","8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602"):
    req(token in RUNNER,"Round26 runner token "+token)
for token in ('HIDDEN_HOME="${PKGDIR}/debian/.supralinux-test-home/sbuild"','VISIBLE_HOME="${PKGDIR}/debian/supralinux-test-home/sbuild"',"run_kdirmodel_lane hidden-home 10","run_kdirmodel_lane visible-home 20","full-suite-visible.log","candidate-remediation.patch","test-homes-cleaned"):
    req(token in HOOK,"Round26 hook token "+token)
for forbidden in ("debian/rules clean","override_dh_auto_configure","override_dh_auto_build"):
    req(forbidden not in HOOK,"Round26 hook must not reconstruct "+forbidden)
req("Attempt 9 = NOT AUTHORIZED" in DOC and "69/69" in DOC and ".supralinux-test-home" in DOC,"Round26 docs")

print("KDE Tier 3 KIO Round 26 combined remediation definition: PASS")
print("Round26=AUTHORIZED-NON-PROMOTING")
print("Attempt9=NOT-AUTHORIZED")
