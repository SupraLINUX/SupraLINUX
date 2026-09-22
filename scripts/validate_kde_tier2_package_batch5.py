#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier2-package-campaign-batch5.json")
a=load("manifests/kde-tier2-package-batch5-attempts.json")
plan=load("manifests/kde-tier2-campaign-plan.json")
tier2=load("manifests/kde-frameworks-tier2.json")
contracts=load("manifests/kde-tier2-package-contracts.json")
tier1=load("manifests/kde-frameworks-tier1.json")
RUNNABLE={"prepared-pending-build","remediation-pending-build"}

req(c.get("schema")==1 and c.get("batch")=="tier2-batch-5","Batch5 identity")
req(c.get("selected_nodes")==["kmime"],"Batch5 KMime-only scope")
req(c.get("activation",{}).get("status") in {"armed","rematerialization-required"},"Batch5 activation")
req(c.get("activation",{}).get("package_state_effect")=="none","Batch5 activation state semantics")
req(c.get("frameworks_series")=="6.30.0","Batch5 Frameworks series")
req(c.get("scheduling",{}).get("fail_fast") is False,"Batch5 fail-fast policy")
sem=c.get("semantics",{})
req(sem.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
req(sem.get("package_attempt_begins")=="immediately-before-sbuild","attempt boundary")
req(sem.get("fail_requires")=="node-owned-root-cause","FAIL ownership")
req({"legacy-runtime-coinstallation","no-fake-legacy-abi-metadata"} <= set(sem.get("pass_requires",[])),"KMime compatibility PASS gates")

canon={n["id"]:n for n in tier2["nodes"]}
t1={n["id"]:n for n in tier1["nodes"]}
n=c["nodes"]["kmime"]; cn=canon["kmime"]; pc=contracts["nodes"]["kmime"]
runnable=n.get("state") in RUNNABLE
rematerialization=n.get("state")=="rematerialization-pending"
req(set(plan.get("build_queue",[])).intersection({"kmime"})==({"kmime"} if runnable else set()),"Batch5 scoped global build queue")
req(set(plan.get("package_contract_ready",[])).intersection({"kmime"})==({"kmime"} if rematerialization else set()),"Batch5 scoped rematerialization queue")
req(n.get("source_package")=="kf6-kmime"==pc.get("source_package"),"KMime source identity")
req(n.get("source_sha256")==cn.get("source_sha256")==pc.get("source_sha256"),"KMime source SHA")
req(n.get("package_version")==cn.get("package_identity",{}).get("package_version_candidate")==pc.get("package_version_candidate"),"KMime package version")
req(n.get("expected_binary_packages")==pc.get("target_binary_packages"),"KMime Framework binary contract")
req(n.get("runtime_package")=="libkf6mime6" and n.get("dev_package")=="libkf6mime-dev","KMime runtime/dev packages")
req(n.get("soname")=="libKF6Mime.so.6" and n.get("cmake_package")=="KF6Mime" and n.get("cmake_target")=="KF6::Mime","KMime development/ABI contract")
req(n.get("predecessors")==["kcodecs"] and n.get("package_dependency_closure")==[],"KMime predecessor contract")
req(cn.get("state")=="pending","KMime canonical pending")
m=n.get("materialization",{})
if runnable:
    req(cn.get("planning",{}).get("readiness")=="build-ready","KMime canonical build-ready")
    req(cn.get("planning",{}).get("package_contract")=="materialized","KMime canonical materialized")
    cm=cn.get("planning",{}).get("materialization_evidence",{})
    for key in ("workflow_run","job_id","artifact_id","artifact_sha256","tree_sha256","debian_tree_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
        req(m.get(key)==cm.get(key),f"KMime materialization {key}")
elif rematerialization:
    req(cn.get("planning",{}).get("readiness")=="package-contract-ready","KMime rematerialization canonical readiness")
    req(cn.get("planning",{}).get("package_contract")=="not-materialized","KMime rematerialization contract state")
    history=cn.get("planning",{}).get("materialization_history",[])
    req(any(x and x.get("artifact_id")==m.get("artifact_id") for x in history),"KMime previous materialization retained historically")
else:
    req(n.get("state")=="PASS","KMime Batch5 state vocabulary")

compat=n.get("compatibility",{})
req(compat.get("legacy_runtime_package")=="libkpim6mime6","legacy runtime package")
req(compat.get("legacy_data_package")=="libkmime-data","legacy data package")
req(compat.get("legacy_runtime_soname")=="libKPim6Mime.so.6","legacy runtime SONAME")
req(compat.get("runtime_coinstallation_required") is True and compat.get("fake_abi_metadata_forbidden") is True,"legacy coexistence policy")
pcc=pc.get("compatibility_contract",{})
req(pcc.get("runtime_abi_equivalent") is False and pcc.get("fake_provides_replaces_for_runtime") is False,"package-contract ABI non-equivalence")
req(pcc.get("legacy_install_policy")=="on-demand-only","legacy install policy")

pool=c.get("retained_predecessors",{})
req(set(pool)=={"kcodecs"},"Batch5 retained predecessor pool")
kc=pool["kcodecs"]; kt=t1["kcodecs"]
req(kt.get("state")=="PASS","KCodecs Tier1 PASS")
req(kt.get("packaging",{}).get("package_version")==kc.get("version"),"KCodecs retained version")
req(kc.get("dev_package")=="libkf6codecs-dev" and kc.get("dev_package") in kc.get("debs",{}),"KCodecs dev package retained")
for pkg,digest in kc.get("debs",{}).items():
    req(re.fullmatch(r"[0-9a-f]{64}",digest or "") is not None,f"KCodecs {pkg} digest")
ecm=c.get("shared_predecessors",{}).get("extra_cmake_modules",{})
req(ecm.get("version")=="6.30.0-0supralinux3","ECM version")
req(ecm.get("debs",{}).get("extra-cmake-modules")=="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f","ECM digest")

req(a.get("schema")==1 and a.get("batch")=="tier2-batch-5","attempt ledger identity")
req(isinstance(a.get("real_attempts",{}).get("kmime"),list),"KMime real-attempt ledger")
req(isinstance(a.get("blocked_events",{}).get("kmime"),list),"KMime blocked ledger")
req(isinstance(a.get("infrastructure_incidents"),list),"Batch5 infrastructure ledger")

for path in (
 "scripts/plan-kde-tier2-package-batch5.py",
 "scripts/kde-tier2-package-batch5-needed.sh",
 "scripts/validate-kde-tier2-batch5-retained-inputs.py",
 "scripts/run-kde-tier2-package-batch5.sh",
 "scripts/test-kde-tier2-package-batch5-scope.sh",
 ".github/workflows/kde-tier2-package-batch5.yml",
):
    req((ROOT/path).exists(),f"missing Batch5 component: {path}")
doc=(ROOT/"docs/kde-tier2-package-batch5.md").read_text()
for token in ("KMime","KF6Mime","KPim6Mime","co-install","stable"):
    req(token.casefold() in doc.casefold(),f"Batch5 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 5 preparation: PASS")
print(f"runnable={runnable} node=kmime")
