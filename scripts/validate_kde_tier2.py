#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

tier2=load("manifests/kde-frameworks-tier2.json")
deps=load("manifests/kde-frameworks-tier2-dependencies.json")
discovery=load("manifests/kde-tier2-global-discovery.json")
tier1=load("manifests/kde-frameworks-tier1.json")
dag=load("manifests/kde-dag.json")

expected_ids={
 "kauth","kcolorscheme","kcompletion","kcontacts","kcrash","kdeclarative",
 "kfilemetadata","knotifications","kpackage","kpty","kservice",
 "kstatusnotifieritem","kunitconversion","syndication","kmime"
}
source_sha={
 "kauth":"60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9",
 "kcolorscheme":"a4128e82e47cd474c777754c4dd8af28a00a57ecf388da1a62f8173d898890d0",
 "kcompletion":"96ad9c429ca53b830359c45614ca4c32ed6b759f3023f1b3db1650ba1c19bd58",
 "kcontacts":"170b51a41ac132968ea03d5f1ce8c585777155bbdc57e819a0562b1f8d03b7a5",
 "kcrash":"b17f8242309e1502119c48b1ef5059a396a3068596a84fb79fdef6d9e2cd4f49",
 "kdeclarative":"7ec3583a2cf2cd7143e39936ffb39e22d20563f4c87a8462e0e9d12c59ea89a6",
 "kfilemetadata":"5e14cd8e395e927042cb3eb7cff47e0effda5e8bf2520cf18d1082a9403b2e62",
 "knotifications":"09ad50570b26aada0408bb9ccfaabf629c56ec89a9972c8b0e155ab780f577cf",
 "kpackage":"58939af0c553f24963652e10d248e2f8f2b2ca2b87dc26d3220675ed0cf33019",
 "kpty":"ad66149c20470de29d483f0ccdcb057d42ccf778f3f8cc8e68aefca5380bace7",
 "kservice":"e63062504ede4ebfda4c93e3484a63817731e1157cdcac6e33fb47fe6abc1657",
 "kstatusnotifieritem":"373fb23fe6a5c0c5c755c473e7cf272796ea59891c05157c3a7e9607a4c4af4f",
 "kunitconversion":"3dcaa45875bab5a2dcadc34cf57cf06689b8d86ff40e20fee01ca2b18987175f",
 "syndication":"2d44e45b05766d342d3fe19e92d2b039c916a7a83f9e4dff0f9fa15860e140ee",
 "kmime":"2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc",
}
required={
 "kauth":["kcoreaddons"],
 "kcolorscheme":["kconfig","kguiaddons","ki18n"],
 "kcompletion":["kcodecs","kconfig","kwidgetsaddons"],
 "kcontacts":["ki18n","kconfig","kcodecs"],
 "kcrash":["kcoreaddons"],
 "kdeclarative":["ki18n","kconfig","kguiaddons"],
 "kfilemetadata":["ki18n"],
 "knotifications":["kconfig"],
 "kpackage":["karchive","ki18n","kcoreaddons"],
 "kpty":["kcoreaddons","ki18n"],
 "kservice":["kconfig","kcoreaddons","ki18n"],
 "kstatusnotifieritem":["kwindowsystem"],
 "kunitconversion":["ki18n"],
 "syndication":["kcodecs"],
 "kmime":["kcodecs"],
}
conditional={
 "kdeclarative":["kglobalaccel","kwidgetsaddons"],
 "kfilemetadata":["karchive","kcoreaddons","kconfig","kcodecs"],
}
selected={
 "kauth":["kwindowsystem"],
}

req(tier2.get("schema")==1 and tier2.get("authority")=="kde-upstream","Tier2 identity/authority")
req(tier2.get("frameworks_series")=="6.30.0" and tier2.get("tier")==2,"Tier2 series/tier")
nodes={n.get("id"):n for n in tier2.get("nodes",[])}
req(set(nodes)==expected_ids,"Tier2 node set must match KDE upstream 15-node inventory")
for node in sorted(expected_ids):
    n=nodes.get(node,{})
    req(n.get("upstream_version")=="6.30.0",f"{node}: upstream version")
    req(n.get("source_sha256")==source_sha[node],f"{node}: source SHA")
    req(n.get("upstream_ref")=="v6.30.0" and n.get("upstream_commit"),f"{node}: upstream tag/commit")
    req(n.get("root_cmake_blob"),f"{node}: root CMake blob")
    req(n.get("depends_on")==["extra-cmake-modules",*required[node],*selected.get(node,[])],f"{node}: selected DAG predecessors")
    kd=n.get("kde_framework_dependencies",{})
    req(kd.get("required")==required[node],f"{node}: required Framework dependency metadata")
    req(kd.get("conditional",[])==conditional.get(node,[]),f"{node}: conditional Framework dependency metadata")
    req(kd.get("selected_profile",[])==selected.get(node,[]),f"{node}: selected Framework dependency metadata")

k=nodes["kauth"]; m=nodes["kmime"]
req(k.get("state")=="PASS","KAuth canonical PASS")
kp=k.get("packaging",{})
req(kp.get("state")=="PASS" and kp.get("package_version")=="6.30.0-0supralinux3" and kp.get("downstream_eligible") is True,"KAuth packaging PASS")
req(k["package_identity"].get("package_version_candidate")==kp.get("package_version"),"KAuth package identity/current revision")
kev=[x for x in kp.get("evidence",[]) if x.get("result")=="PASS"]
req(len(kev)==1,"KAuth exactly one retained PASS")
if kev:
    e=kev[0]
    req(e.get("workflow_run")==35497461178 and e.get("job_id")==106043001431 and e.get("artifact_id")==10601382235,"KAuth PASS run/job/artifact")
    req(e.get("artifact_sha256")=="443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b","KAuth PASS artifact digest")
    req(e.get("rootfs_sha256")=="15113b108b939e2575758c6696fc34808dfa925fa2dd3cc5e6c13e65e7be4668","KAuth rootfs")
    req(e.get("tests")=="6/6 PASS" and e.get("lintian")=="PASS-errors" and e.get("abi_soname")=="libKF6AuthCore.so.6" and e.get("abi_export_count")==118,"KAuth tests/Lintian/ABI")
    req(e.get("consumer_smoke")=="PASS" and e.get("apt_check")=="PASS" and e.get("development_contract")=="PASS","KAuth runtime/development gates")

pending_ids=expected_ids-{"kauth"}
for node in sorted(pending_ids):
    n=nodes[node]
    req(n.get("state")=="pending" and n.get("packaging",{}).get("state")=="pending",f"{node}: must remain pending before real package PASS")
    req(n.get("package_identity",{}).get("package_version_candidate") is None,f"{node}: package version must remain unmaterialized/undecided")
req(m.get("packaging",{}).get("reason")=="compatibility-transition-decision-required","KMime compatibility transition gate")

dep_nodes=deps.get("nodes",{})
req(set(dep_nodes)==expected_ids,"Tier2 dependency manifest node set")
for node in sorted(expected_ids):
    dn=dep_nodes.get(node,{})
    req(dn.get("frameworks",{}).get("required")==required[node],f"{node}: dependency manifest required edges")
    req(dn.get("frameworks",{}).get("conditional",[])==conditional.get(node,[]),f"{node}: dependency manifest conditional edges")
    req(dn.get("frameworks",{}).get("provider_selected",[])==selected.get(node,[]),f"{node}: dependency manifest selected edges")
meta=deps.get("metadata",{})
for node in sorted(expected_ids):
    md=meta.get(node,{})
    req(md.get("ref")=="v6.30.0" and md.get("commit") and md.get("root_cmake_blob"),f"{node}: source metadata")
p=deps.get("external_requirements",{}).get("polkitqt6-1",{})
req(p.get("provider_version")=="0.200.0-4ubuntu1","Polkit provider")
req(sum(n.get("state")=="PASS" for n in tier1.get("nodes",[]))==29 and not any(n.get("state")!="PASS" for n in tier1.get("nodes",[])),"Tier1 precondition")

active=discovery.get("nodes",{})
req(set(active)==pending_ids,"Tier2 active discovery must contain all 14 pending nodes")
for node in sorted(pending_ids-{"kmime"}):
    canonical_readiness=nodes[node].get("planning",{}).get("readiness")
    req(active[node].get("readiness")==canonical_readiness,f"{node}: discovery readiness must match canonical planning state")
req(active["kmime"].get("readiness")=="compatibility-decision-required" and active["kmime"].get("blocker")=="ADR-0002","KMime decision gate")
snap=discovery.get("promoted_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(1,14,0,0),"Tier2 promoted snapshot")
done=discovery.get("completed_nodes",{}).get("kauth",{})
req(done.get("state")=="PASS" and done.get("package_version")=="6.30.0-0supralinux3" and done.get("artifact_id")==10601382235 and done.get("downstream_eligible") is True,"KAuth completed discovery record")

kd=dag.get("nodes",{}).get("kauth",{})
req(kd.get("tier")==2 and kd.get("state")=="PASS" and kd.get("package_version")=="6.30.0-0supralinux3" and kd.get("downstream_eligible") is True,"KAuth canonical DAG promotion")

cmp=subprocess.run(["dpkg","--compare-versions","6.30.0-0supralinux1","lt","25.12.3-0ubuntu1"])
req(cmp.returncode==0,"KMime naive Frameworks version ordering fact")
adr=(ROOT/"docs/decisions/ADR-0002-kmime-frameworks-transition.md").read_text()
for token in ("decision required","KPim6::Mime","KF6::Mime","libKPim6Mime.so.6","libKF6Mime.so.6","Pending human approval"):
    req(token in adr,f"KMime ADR missing {token}")
doc=(ROOT/"docs/kde-tier2.md").read_text()
for token in ("15","KAuth","KMime","1 PASS / 14 pending","POLKITQT6-1","compatibility-decision-required"):
    req(token in doc,f"Tier2 doc missing {token}")
policy=(ROOT/".github/workflows/repository-policy.yml").read_text()
req("python3 scripts/validate_kde_tier2.py" in policy,"Repository Policy Tier2 gate")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Frameworks 6.30 Tier 2 discovery validation: PASS")
print("Canonical Tier 2: 1 PASS / 14 pending / 0 FAIL / 0 BLOCKED")
ready=sum(active[n].get("readiness")=="package-contract-ready" for n in pending_ids-{"kmime"})
audit_pending=sum(active[n].get("readiness")=="package-lane-pending" for n in pending_ids-{"kmime"})
print(f"KAuth PASS/downstream-eligible; {ready} package-contract-ready; {audit_pending} provider-audit pending; KMime compatibility-decision-required")
