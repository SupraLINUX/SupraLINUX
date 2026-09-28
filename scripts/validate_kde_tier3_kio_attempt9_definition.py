#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr); raise SystemExit(1)

M=load("manifests/kde-tier3-kio-attempt9-remediation.json")
R26=load("manifests/kde-tier3-kio-round26-remediation.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
DOC=(ROOT/"docs/kde-tier3-kio-attempt9-remediation.md").read_text()

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("attempt")==9,"Attempt9 identity")
req(M.get("status")=="definition-pending-ci","Attempt9 definition status")
req(M.get("candidate_package_version")=="6.30.0-0supralinux9" and M.get("previous_package_version")=="6.30.0-0supralinux8","Attempt9 version identity")
req(subprocess.run(["dpkg","--compare-versions","6.30.0-0supralinux9","gt","6.30.0-0supralinux8"]).returncode==0,"Attempt9 Debian version must increase")
req(M.get("package_revision_bump_required") is True and M.get("source_rematerialization_required") is True,"Attempt9 source/revision policy")
req(M.get("materialization_authorized") is True,"Attempt9 materialization authorization")
req(M.get("package_execution_authorized") is False and M.get("level1_execution_authorized") is False,"Attempt9 binary execution blocked")
req(M.get("canonical_kio_state")=="FAIL" and M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Attempt9 canonical state unchanged")

req(R26.get("status")=="remediation-PASS","Round26 predecessor status")
r26=R26.get("result",{})
req(r26.get("combined_suite_pass") is True and r26.get("conclusion")=="hidden-home-causality-and-combined-kio-remediation-PASS","Round26 combined proof")
req(r26.get("candidate_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Round26 exact candidate patch")
req(r26.get("candidate_source_sha256")=="57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b","Round26 exact candidate source")

src=M.get("source_remediation",{})
req(src.get("patch_name")=="supralinux-krecent-deterministic-ordering.patch","Attempt9 patch name")
req(src.get("exact_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","Attempt9 patch digest")
req(src.get("exact_patched_source_sha256")=="57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b","Attempt9 patched source digest")
req(src.get("public_api_change") is False and src.get("abi_change") is False and src.get("xbel_schema_change") is False and src.get("timestamp_format_change") is False,"Attempt9 source compatibility shape")

env=M.get("test_environment_remediation",{})
req(env.get("previous_home")=="debian/.supralinux-test-home/sbuild","Attempt9 historical hidden HOME")
req(env.get("selected_home")=="debian/supralinux-test-home/sbuild","Attempt9 visible HOME")
req(env.get("test_environment_only") is True and env.get("package_runtime_effect") is False,"Attempt9 HOME scope")
req(env.get("upstream_tests_filtered") is False and env.get("failures_fatal") is True,"Attempt9 test policy")

k=C["nodes"]["kio"]
req(k.get("package_version_candidate")=="6.30.0-0supralinux9","KIO contract candidate -9")
patches=k.get("supralinux_source_patches",[])
req(len(patches)==1,"KIO exact source patch count")
p=patches[0]
req(p.get("name")==src.get("patch_name") and p.get("expected_patch_sha256")==src.get("exact_patch_sha256"),"KIO patch contract identity")
req(p.get("expected_source_sha256")==src.get("exact_patched_source_sha256"),"KIO patched source identity")
rules=k.get("rules_text_replacements",[])
test_rule=next((x for x in rules if x.get("classification")=="upstream-test-environment-correction"),None)
req(test_rule is not None and "debian/supralinux-test-home/sbuild" in test_rule.get("new",""),"KIO visible test HOME materialized")
req("debian/.supralinux-test-home/sbuild" not in test_rule.get("new",""),"KIO hidden test HOME removed from new rules")
req(k.get("test_environment_contract",{}).get("home_policy")=="writable-visible-path-debian/supralinux-test-home/sbuild-ending-in-sbuild-to-match-build-user","KIO HOME contract")

policy=T.get("discovery_policy",{})
req(policy.get("phase")=="build-level1-planning","Attempt9 definition phase")
req(policy.get("package_builds")=="tier3-level1-remediation-pending-materialization","Attempt9 materialization gate")
req(policy.get("remediation")=="attempt9-kio-proven-remediation-pending-materialization","Attempt9 remediation marker")

for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("status")=="attempt9-remediation-defined-pending-materialization",name+" Attempt9 definition")
    req(obj.get("candidate_package_versions",{}).get("kio")=="6.30.0-0supralinux9",name+" Attempt9 candidate")
    req(obj.get("execution_authorized") is False,name+" execution blocked")
    req(obj.get("next_gate")=="tier3-attempt9-kio-remediation-materialization-evidence",name+" materialization handoff")

req(L.get("execution_authorized") is False and L.get("current_attempt")==8 and L.get("next_attempt")==9,"Level1 Attempt9 remains unauthorized")
req(L.get("active_remediation",{}).get("source_rematerialization_required") is True,"Attempt9 source rematerialization required")
req(MAT.get("state")=="remediation-pending-ci" and MAT.get("remediation_queue")==["kio"],"Attempt9 materialization queue")
req(MAT["nodes"]["kio"].get("state")=="remediation-pending" and MAT["nodes"]["kio"].get("package_version")=="6.30.0-0supralinux9","Attempt9 KIO materialization node")
req(MAT["nodes"]["kxmlgui"].get("state")=="materialized","KXMLGui retained materialization")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Attempt9 definition non-attempt")
req("Attempt 9 = NOT AUTHORIZED" in DOC and "6.30.0-0supralinux9" in DOC and "source materialization only" in DOC,"Attempt9 docs")

print("KDE Tier 3 KIO Attempt 9 remediation definition: PASS")
print("candidate=6.30.0-0supralinux9")
print("materialization=AUTHORIZED")
print("Attempt9=NOT-AUTHORIZED")
