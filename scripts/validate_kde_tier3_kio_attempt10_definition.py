#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
M=load("manifests/kde-tier3-kio-attempt10-remediation.json")
A9=load("manifests/kde-tier3-kio-attempt9-remediation.json")
C=load("manifests/kde-tier3-package-contracts.json")
OLD="6.30.0-0supralinux9"; NEW="6.30.0-0supralinux10"
req(M.get("schema")==1 and M.get("node")=="kio" and M.get("attempt")==10,"Attempt10 identity")
req(M.get("candidate_package_version")==NEW and M.get("previous_package_version")==OLD,"Attempt10 version identity")
req(subprocess.run(["dpkg","--compare-versions",NEW,"gt",OLD]).returncode==0,"Attempt10 Debian version increment")
d=M.get("definition_contract",{})
req(d.get("status")=="PASS","Attempt10 definition contract PASS")
req(d.get("definition_commit")=="0a36afe3c2841dd4d00f783fc9b898a29580497c","Attempt10 definition commit")
req(d.get("validation_commit")=="a77f6e1f247792ccb486720010d969e2cbc41680" and d.get("repository_policy_workflow_run")==36424068693,"Attempt10 definition validation evidence")
req(d.get("candidate_package_version")==NEW and d.get("materialization_authorized_at_definition") is True and d.get("package_execution_authorized_at_definition") is False,"Attempt10 original authorization boundary")
req(d.get("symbol_count")==34 and d.get("minimal_version")=="6.30.0" and d.get("optional_only") is True and d.get("functional_source_unchanged") is True,"Attempt10 frozen remediation contract")
p=M.get("predecessor_attempt9",{})
req(p.get("workflow_run")==36416891314 and p.get("commit")=="e7dfc689bf18aea5ed194df03f31e9c74627ead0" and p.get("result")=="MIXED" and p.get("kio_tests")=="69/69 PASS","Attempt9 predecessor")
req(A9.get("status")=="attempt9-closed-mixed" and A9.get("attempt9_result",{}).get("functional_remediation_result")=="PASS","Attempt9 historical closure")
func=M.get("retained_functional_remediation",{})
req(func.get("krecent_patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602","KRecent patch retained")
req(func.get("patched_source_sha256")=="57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b","patched source retained")
req(func.get("test_home")=="debian/supralinux-test-home/sbuild" and func.get("source_code_change_from_attempt9") is False,"functional source unchanged")
sm=M.get("symbol_metadata_remediation",{})
req(sm.get("total_symbols")==34 and sm.get("minimal_version")=="6.30.0" and sm.get("tags")==["optional"],"Attempt10 symbol policy")
req(sm.get("public_abi_promotion") is False and sm.get("lintian_suppression") is False,"Attempt10 ABI/Lintian policy")
adds=C.get("nodes",{}).get("kio",{}).get("symbol_template_additions",[])
req(len(adds)==34 and sum(1 for x in adds if x.get("package")=="libkf6kiocore6")==1 and sum(1 for x in adds if x.get("package")=="libkf6kiogui6")==33,"Attempt10 symbol counts")
for x in adds:
    req(x.get("minimal_version")=="6.30.0" and x.get("tags")==["optional"],"optional upstream symbol baseline: "+str(x.get("symbol")))
req(M.get("stable_promotion_requires_explicit_user_approval") is True,"stable policy")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Attempt 10 historical definition contract: PASS")
print("candidate="+NEW+"; symbols=34 optional @ 6.30.0")
