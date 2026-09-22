#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier3-support-build-level1.json")
a=load("manifests/kde-tier3-support-build-level1-attempts.json")
l0=load("manifests/kde-tier3-support-build-level0.json")
mat=load("manifests/kde-tier3-support-materialization.json")
deps=load("manifests/kde-frameworks-tier3-dependencies.json")
tier3=load("manifests/kde-frameworks-tier3.json")
t1=load("manifests/kde-frameworks-tier1.json")
t2=load("manifests/kde-frameworks-tier2.json")
dag=load("manifests/kde-dag.json")

req(c.get("schema")==1 and c.get("authority")=="kde-upstream","support level1 schema/authority")
req(c.get("role")=="support-binary-build-level1","support level1 role")
req(c.get("frameworks_series")=="6.30.0","support level1 series")
req(c.get("state") in {"pending-ci","PASS"},"support level1 lifecycle")
req(c.get("selected_nodes")==["kded"],"support level1 node set")
req(c.get("materialization_manifest")=="manifests/kde-tier3-support-materialization.json","support level1 materialization link")
req(c.get("level0_manifest")=="manifests/kde-tier3-support-build-level0.json","support level1 level0 link")
req(l0.get("state")=="PASS","support level1 requires level0 PASS")
req(l0.get("nodes",{}).get("kdoctools",{}).get("state")=="PASS","support level1 requires KDocTools PASS")
req(l0.get("nodes",{}).get("kdoctools",{}).get("pass_evidence",{}).get("artifact_id")==10682066198,"KDocTools predecessor artifact pin")
req(mat.get("state")=="PASS" and mat.get("nodes",{}).get("kded",{}).get("state")=="materialized","KDED materialization PASS")

ecm=c.get("shared_predecessors",{}).get("extra_cmake_modules",{})
canon_ecm=dag.get("nodes",{}).get("extra-cmake-modules",{})
req(canon_ecm.get("state")=="PASS" and ecm.get("version")==canon_ecm.get("package_version"),"ECM canonical PASS/version")
req(any(e.get("result")=="PASS" and e.get("artifact_id")==ecm.get("artifact_id") and e.get("artifact_sha256")==ecm.get("artifact_sha256") for e in canon_ecm.get("evidence",[])),"ECM PASS artifact pin")

canon={}
for n in t1.get("nodes",[]): canon[n["id"]]=n
for n in t2.get("nodes",[]): canon[n["id"]]=n
for pred in ("kconfig","kcoreaddons","kcrash","kdbusaddons","kservice"):
    cfg=c.get("retained_predecessors",{}).get(pred,{})
    n=canon.get(pred,{})
    req(n.get("state")=="PASS" and n.get("packaging",{}).get("downstream_eligible") is True,f"{pred}: canonical downstream PASS")
    req(cfg.get("version")==n.get("packaging",{}).get("package_version"),f"{pred}: version pin")
    req(any(e.get("result")=="PASS" and e.get("artifact_id")==cfg.get("artifact_id") and e.get("artifact_sha256")==cfg.get("artifact_sha256") for e in n.get("packaging",{}).get("evidence",[])),f"{pred}: artifact pin")
    req(cfg.get("dev_package") in cfg.get("debs",{}),f"{pred}: dev package")
kdoc=c.get("retained_predecessors",{}).get("kdoctools",{})
req(kdoc.get("version")=="6.30.0-0supralinux1" and kdoc.get("artifact_id")==10682066198,"KDocTools retained PASS pin")
req(kdoc.get("dev_package")=="libkf6doctools-dev" and kdoc.get("dev_package") in kdoc.get("debs",{}),"KDocTools dev package pin")
for pred in ("karchive","ki18n"):
    cfg=c.get("package_dependency_closure",{}).get(pred,{})
    n=canon.get(pred,{})
    req(n.get("state")=="PASS" and n.get("packaging",{}).get("downstream_eligible") is True,f"{pred}: closure canonical PASS")
    req(cfg.get("version")==n.get("packaging",{}).get("package_version"),f"{pred}: closure version pin")
    req(any(e.get("result")=="PASS" and e.get("artifact_id")==cfg.get("artifact_id") and e.get("artifact_sha256")==cfg.get("artifact_sha256") for e in n.get("packaging",{}).get("evidence",[])),f"{pred}: closure artifact pin")

n=c.get("nodes",{}).get("kded",{})
req(n.get("state") in {"prepared-pending-build","remediation-pending-build","PASS"},"KDED level1 state")
req(n.get("source_package")=="kf6-kded" and n.get("package_version")=="6.30.0-0supralinux1","KDED package identity")
req(n.get("expected_binary_packages")==["kded6","kded6-dev"],"KDED binary package contract")
req(n.get("direct_predecessors")==["kconfig","kcoreaddons","kcrash","kdbusaddons","kservice","kdoctools"],"KDED direct predecessor set")
req(n.get("package_dependency_closure")==["karchive","ki18n"],"KDED package closure")
req(n.get("cmake_package")=="KF6KDED" and n.get("cmake_variable")=="KDED_DBUS_INTERFACE","KDED CMake consumer contract")
m=n.get("materialization",{})
req(m.get("workflow_run")==35698463205 and m.get("artifact_id")==10680629132,"KDED materialization artifact")
for key in ("artifact_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
    req(len(m.get(key,""))==64,f"KDED materialization {key}")
support=deps.get("support_components",{}).get("kded",{})
req(support.get("state") in {"pending","PASS"} and support.get("readiness") in {"build-level1-ready","PASS"},"canonical KDED lifecycle")
if n.get("state")=="PASS":
    ev=n.get("pass_evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_attempted") is True and ev.get("downstream_eligible") is True,"KDED PASS evidence semantics")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"KDED PASS run/job")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"KDED PASS artifact")
    req(ev.get("executable_contract")=="PASS" and ev.get("cmake_consumer")=="PASS","KDED executable/CMake gates")

req(a.get("schema")==1 and a.get("batch")=="tier3-support-build-level1","level1 attempt ledger")
req(set(a.get("nodes",{}))=={"kded"},"level1 attempt ledger nodes")
attempts=a.get("nodes",{}).get("kded",[])
for i,attempt in enumerate(attempts,1):
    req(attempt.get("attempt")==i,f"KDED attempt sequence {i}")
    req(attempt.get("result") in {"PASS","FAIL"},f"KDED attempt {i} result")
    req(attempt.get("package_version")=="6.30.0-0supralinux1",f"KDED attempt {i} package version")
    req(isinstance(attempt.get("workflow_run"),int) and isinstance(attempt.get("job_id"),int),f"KDED attempt {i} run/job")
    req(isinstance(attempt.get("artifact_id"),int) and len(attempt.get("artifact_sha256",""))==64,f"KDED attempt {i} artifact evidence")
if c.get("state")=="PASS":
    req(len(attempts)>=1 and attempts[-1].get("result")=="PASS","KDED terminal PASS attempt")
    req(sum(1 for x in attempts if x.get("result")=="PASS")==1,"KDED exactly one PASS attempt")
req(tier3.get("support_components",{}).get("next_gate") in {"support-build-level1","tier3-provider-audit","tier3-package-contracts","tier3-build"},"canonical level1 gate")
req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

for path in (
 "scripts/plan-kde-tier3-support-build-level1.py",
 "scripts/validate-kde-tier3-support-level1-retained-inputs.py",
 "scripts/run-kde-tier3-support-build-level1.sh",
 "scripts/kde-tier3-support-build-level1-needed.sh",
 "scripts/test-kde-tier3-support-build-level1-scope.sh",
 ".github/workflows/kde-tier3-support-build-level1.yml",
 "docs/kde-tier3-support-build-level1.md",
):
    req((ROOT/path).exists(),f"missing support level1 component: {path}")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 support build level 1 definition: PASS")
print("state="+c["state"])
