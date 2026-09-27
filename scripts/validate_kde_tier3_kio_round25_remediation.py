#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round25-remediation.json")
R24=load("manifests/kde-tier3-kio-round24-diagnostic.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round25-remediation.yml").read_text()
RUNNER=(ROOT/"scripts/run-kde-tier3-kio-round25-diagnostic.sh").read_text()
HOOK=(ROOT/"scripts/run-kde-tier3-kio-round25-hook.sh").read_text()
DOC=(ROOT/"docs/kde-tier3-kio-round25-remediation.md").read_text()
R11=(ROOT/"scripts/validate_kde_tier3_round11.py").read_text()

req(M.get("schema")==1 and M.get("round")==25 and M.get("node")=="kio","Round25 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round25 upstream")
req(M.get("status")=="definition-pending-ci" and M.get("execution_authorized") is True,"Round25 proof authorization")
req(M.get("package_execution_authorized") is False and M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round25 package safety")
req(M.get("package_revision_allocation") is False and M.get("test_suppression") is False,"Round25 no package/test mutation")
req(M.get("canonical_source_modified") is False and M.get("diagnostic_worktree_modified") is True,"Round25 worktree-only candidate")

req(R24.get("status")=="diagnostic-PASS","Round24 predecessor PASS")
r24=R24.get("result",{})
req(r24.get("conclusion")=="timestamp-tie-causality-confirmed","Round24 causal result")
req(r24.get("matrix",{}).get("native",{}).get("failed_runs")==14,"Round24 native evidence")
req(r24.get("matrix",{}).get("monotonic",{}).get("failed_runs")==0,"Round24 monotonic evidence")
req(r24.get("matrix",{}).get("fixed",{}).get("failed_runs")==20,"Round24 fixed evidence")

up=M.get("upstream_check",{})
req(up.get("repository")=="KDE/kio" and up.get("master_commit")=="970cbbbc5f80e56b71c9f32b1d333abac24a7770","Round25 upstream check")
req(up.get("relevant_logic_still_unfixed") is True,"Round25 upstream remediation check")

cand=M.get("candidate_remediation",{})
req(cand.get("source_file")=="src/core/krecentdocument.cpp","Round25 candidate source")
req(cand.get("public_api_change") is False and cand.get("abi_change") is False and cand.get("timestamp_format_change") is False and cand.get("xbel_schema_change") is False,"Round25 compatibility shape")
req(cand.get("eviction_order",{}).get("tie_breaker")=="XBEL document order ascending","Round25 eviction tie breaker")
req(cand.get("recent_urls_order",{}).get("tie_breaker")=="XBEL document order ascending","Round25 recentUrls tie breaker")
req(cand.get("production_patch_selected") is False,"Round25 candidate not production-selected")

matrix=M.get("diagnostic_matrix",[])
req([(x.get("id"),x.get("repetitions"),x.get("timestamp_mode")) for x in matrix]==[
    ("native",100,"native"),("fixed",100,"fixed"),("monotonic",20,"monotonic"),("full-suite",1,"native")
],"Round25 matrix")

v=M.get("validity_contract",{})
for key in ("exact_attempt8_rootfs","exact_attempt8_source_materialization","exact_attempt8_predecessor_artifacts","exact_sbuild_unshare_mode","historical_dpkg_buildpackage_required","remediation_runs_from_override_dh_auto_test","fixed_lane_requires_one_final_timestamp","monotonic_lane_requires_three_distinct_final_timestamps","all_lanes_require_final_order_12_13_14","candidate_patch_retained_in_evidence","candidate_source_hash_retained","test_and_core_sources_restored_before_exit","canonical_source_artifact_unchanged","no_candidate_package_artifacts"):
    req(v.get(key) is True,"Round25 validity "+key)

next_gate="tier3-round25-kio-krecent-ordering-remediation-evidence"
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="diagnostic" and policy.get("package_builds")=="tier3-round25-remediation-pending","Round25 live gate")
req(policy.get("remediation")=="round25-krecent-deterministic-ordering-remediation-pending-ci","Round25 live remediation")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="round25-remediation-pending-ci",name+" Round25 status")
    req(obj.get("next_gate")==next_gate,name+" Round25 next gate")
    req(obj.get("execution_authorized") is False,name+" package execution blocked")
    d=obj.get("round25_definition",{})
    req(d.get("status")=="definition-pending-ci" and d.get("matrix")=={"native":100,"fixed":100,"monotonic":20,"full-suite":1},name+" Round25 definition")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("next_attempt")==9,"Attempt9 remains unauthorized")
req(MAT.get("active_remediation",{}).get("package_attempted") is False and MAT.get("active_remediation",{}).get("package_state_effect")=="none","materialization unchanged")
req(M.get("next_gate")==next_gate,"Round25 next gate")

req('gate=="tier3-round25-remediation-pending"' in R11 and "validate_kde_tier3_kio_round25_remediation.py" in R11,"Round11 routes Round25")
req("workflow_call:" in W and "workflow_dispatch:" in W and "\n  pull_request:\n" not in W,"Round25 workflow reusable/manual only")
for token in ("10904512642","10898999142","0.91.2ubuntu3","Command: dpkg-buildpackage --sanitize-env -us -uc -b","debian/rules binary","SUPRALINUX_ROUND25_EVIDENCE_BASE64_BEGIN",'expected={"native":100,"fixed":100,"monotonic":20,"full-suite":1}',"deterministic-xbel-ordering-remediation-PASS"):
    req(token in RUNNER,"Round25 runner token "+token)
for token in ("struct BookmarkEntry","struct RecentDocumentEntry","candidate-remediation.patch","run_lane native 100 native","run_lane fixed 100 fixed","run_lane monotonic 20 monotonic","run_lane full-suite 1 native","SUPRALINUX_ROUND25_PREPARED"):
    req(token in HOOK,"Round25 hook token "+token)
for forbidden in ("debian/rules clean","override_dh_auto_configure","override_dh_auto_build"):
    req(forbidden not in HOOK,"Round25 hook must not reconstruct "+forbidden)
req("Attempt 9 = NOT AUTHORIZED" in DOC and "100" in DOC and "XBEL document order" in DOC,"Round25 docs")

print("KDE Tier 3 KIO Round 25 deterministic ordering remediation definition: PASS")
print("Round25=AUTHORIZED-REMEDIATION-PROOF-ONLY")
print("Attempt9=NOT-AUTHORIZED")
