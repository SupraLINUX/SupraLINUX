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
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round24-diagnostic.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round24-diagnostic.sh").read_text()
HOOK=(ROOT/"scripts/run-kde-tier3-kio-round24-hook.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round24-diagnostic.md").read_text()
R11=(ROOT/"scripts/validate_kde_tier3_round11.py").read_text()

req(M.get("schema")==1 and M.get("round")==24 and M.get("node")=="kio","Round24 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round24 upstream identity")
req(M.get("claim")=="non-promoting-krecent-timestamp-tie-causality-diagnostic","Round24 claim")
req(M.get("status")=="definition-pending-ci" and M.get("execution_authorized") is True,"Round24 diagnostic authorization")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round24 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round24 no package/test mutation")
req(M.get("canonical_source_modified") is False and M.get("diagnostic_worktree_modified") is True and M.get("controlled_perturbation") is True,"Round24 controlled worktree perturbation")

r=R23.get("result",{})
req(R23.get("status")=="diagnostic-PASS","Round23 predecessor closed PASS")
ev=R23.get("diagnostic_evidence",{})
req(ev.get("workflow_run")==36288655361 and ev.get("artifact_id")==10921272952 and ev.get("artifact_sha256")=="1638ac8ea01881a78e4ec32761eb473836258653d3c08f1f116af6ac93829e69","Round23 predecessor evidence")
req(r.get("matrix",{}).get("isolated-krecent",{}).get("runs")==100 and r.get("matrix",{}).get("isolated-krecent",{}).get("krecent_failed_runs")==58,"Round23 isolated evidence")
req(r.get("matrix",{}).get("isolated-krecent",{}).get("attempt8_signature_failures")==51,"Round23 exact signature evidence")

hyp=M.get("hypothesis",{})
req(hyp.get("classification")=="timestamp-tie-causality-candidate","Round24 hypothesis classification")
facts=" ".join(hyp.get("source_facts",[]))
for token in ("ISODateWithMs","QMultiMap<QDateTime,QDomNode>","recentUrls"):
    req(token in facts,"Round24 source fact "+token)
req(hyp.get("production_change_authorized") is False,"Round24 no production change")

infra=M.get("infrastructure_basis",{})
req(infra.get("new_infrastructure_mechanism") is False,"Round24 must reuse certified infrastructure")
pre=infra.get("certified_preflight",{})
req(pre.get("status")=="PASS" and pre.get("workflow_run")==36286096599 and pre.get("artifact_id")==10920194622,"Round24 preflight basis")
transport=infra.get("certified_target_transport",{})
req(transport.get("round")==23 and transport.get("status")=="diagnostic-PASS" and transport.get("workflow_run")==36288655361,"Round24 transport basis")

a=M.get("attempt8_reference",{})
req(a.get("rootfs_artifact_id")==10904512642 and a.get("rootfs_tar_sha256")=="790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e","Round24 exact rootfs")
req(a.get("materialization_artifact_id")==10898999142 and a.get("materialization_artifact_sha256")=="c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d","Round24 exact source materialization")

matrix=M.get("diagnostic_matrix",[])
req([(x.get("id"),x.get("repetitions"),x.get("timestamp_mode")) for x in matrix]==[("native",40,"native"),("monotonic",40,"monotonic"),("fixed",20,"fixed")],"Round24 causal matrix")
ctrl=M.get("timestamp_controls",{})
req(ctrl.get("monotonic",{}).get("expected_final_timestamp_cardinality")==3,"Round24 monotonic control")
req(ctrl.get("fixed",{}).get("expected_final_timestamp_cardinality")==1,"Round24 fixed control")
v=M.get("validity_contract",{})
for key in ("exact_attempt8_rootfs","exact_attempt8_source_materialization","exact_attempt8_predecessor_artifacts","exact_sbuild_unshare_mode","historical_dpkg_buildpackage_required","diagnostic_runs_from_override_dh_auto_test","native_lane_preserves_original_timestamp_expression","monotonic_lane_requires_three_distinct_final_timestamps","fixed_lane_requires_one_final_timestamp","test_and_core_sources_restored_before_exit","canonical_source_artifact_unchanged","no_candidate_package_artifacts"):
    req(v.get(key) is True,"Round24 validity "+key)

next_gate="tier3-round24-kio-krecent-timestamp-tie-causality-diagnostic-evidence"
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="diagnostic" and policy.get("package_builds")=="tier3-round24-diagnostic-pending","Round24 live diagnostic gate")
req(policy.get("remediation")=="round24-krecent-timestamp-tie-causality-diagnostic-pending-ci","Round24 live remediation")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="round24-diagnostic-pending-ci",name+" Round24 status")
    req(obj.get("next_gate")==next_gate,name+" Round24 next gate")
    req(obj.get("execution_authorized") is False,name+" package execution blocked")
    d=obj.get("round24_definition",{})
    req(d.get("status")=="definition-pending-ci" and d.get("matrix")=={"native":40,"monotonic":40,"fixed":20},name+" Round24 definition")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("next_attempt")==9,"Attempt9 remains unauthorized")
req(MAT.get("active_remediation",{}).get("package_attempted") is False and MAT.get("active_remediation",{}).get("package_state_effect")=="none","materialization remains source-only")
req(M.get("next_gate")==next_gate,"Round24 next gate")

req('gate=="tier3-round24-diagnostic-pending"' in R11 and "validate_kde_tier3_kio_round24_diagnostic.py" in R11,"Round11 routes Round24")
req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round24 workflow reusable/manual only")
for token in ("10904512642","10898999142","0.91.2ubuntu3","Command: dpkg-buildpackage --sanitize-env -us -uc -b","debian/rules binary","SUPRALINUX_ROUND24_EVIDENCE_BASE64_BEGIN",'expected={"native":40,"monotonic":40,"fixed":20}',"timestamp-tie-causality-confirmed"):
    req(token in RUNNER,"Round24 runner token "+token)
for token in ('SUPRALINUX_KRECENT_TIMESTAMP_MODE="${timestamp_mode}"',"run_lane native 40 native","run_lane monotonic 40 monotonic","run_lane fixed 20 fixed",'QStringLiteral("monotonic")','QStringLiteral("fixed")',"krecentdocument.cpp.original"):
    req(token in HOOK,"Round24 hook token "+token)
for forbidden in ("debian/rules clean","override_dh_auto_configure","override_dh_auto_build"):
    req(forbidden not in HOOK,"Round24 hook must not reconstruct "+forbidden)
req("Attempt 9 = NOT AUTHORIZED" in DOC and "40" in DOC and "monotonic" in DOC and "fixed" in DOC,"Round24 docs")
print("KDE Tier 3 KIO Round 24 timestamp-tie causality definition: PASS")
print("Round24=AUTHORIZED-DIAGNOSTIC-ONLY")
print("Attempt9=NOT-AUTHORIZED")
