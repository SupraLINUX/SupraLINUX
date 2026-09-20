#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

contracts=load("manifests/kde-tier2-package-contracts.json")
tier2=load("manifests/kde-frameworks-tier2.json")
deps=load("manifests/kde-frameworks-tier2-dependencies.json")

expected=["kcrash","knotifications","kstatusnotifieritem","kunitconversion","syndication"]
req(contracts.get("schema")==1,"contract schema")
req(contracts.get("state") in {"reference-capture-pending","reference-capture-pass","materialized"},"contract state")
if contracts.get("state") in {"reference-capture-pass","materialized"}:
    ev=contracts.get("reference_evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","reference capture PASS evidence")
    req(isinstance(ev.get("workflow_run"),int) and ev.get("workflow_run")>0,"reference capture workflow identity")
    req(isinstance(ev.get("job_id"),int) and ev.get("job_id")>0,"reference capture job identity")
    req(isinstance(ev.get("artifact_id"),int) and ev.get("artifact_id")>0,"reference capture artifact identity")
    req(len(ev.get("artifact_sha256",""))==64,"reference artifact digest")
    req(ev.get("snapshot_sha256")=="5bfdf1238cedc31ccda2a3f3c93459911709b3e7650eb40c129354f42d0286e9","reference snapshot digest")
    req(ev.get("versions_sha256")=="adc9d4eda684acaaa77a05a4089fa975ca3e894acdd9bd18190d41cbdb062d74","reference versions digest")
    req(ev.get("result_json_sha256")=="5fd85f5d9365a658497bd104007f666304c3f88da2366d32b2bf5b629bf6b14f","reference result digest")
req(contracts.get("source_authority")=="kde-upstream" and contracts.get("packaging_authority")=="supralinux","authority split")
req(contracts.get("frameworks_series")=="6.30.0","Frameworks series")
req(contracts.get("selected_nodes")==expected,"selected contract node order")
req(contracts.get("compatibility_reference",{}).get("ubuntu",{}).get("role")=="technical-reference-only","Ubuntu reference role")
req(contracts.get("compatibility_reference",{}).get("debian",{}).get("role")=="technical-reference-only","Debian reference role")
adapt=contracts.get("provider_adaptations",{}).get("ubuntu-resolute",{}).get("debhelper_compat",{})
req(adapt.get("technical_reference_level")==14,"Debian technical-reference debhelper compat level")
req(adapt.get("selected_level")==13,"Resolute provider debhelper compat level")
req(adapt.get("kde_feature_effect")=="none","debhelper adaptation must not change KDE feature profile")
provider=contracts.get("provider_adaptations",{}).get("ubuntu-resolute",{})
changelog=provider.get("changelog_distribution",{})
req(changelog.get("selected")=="resolute","Resolute changelog distribution")
req(changelog.get("kde_feature_effect")=="none","changelog integration must not change KDE feature profile")
shiboken=provider.get("shiboken_clang_discovery",{})
req(shiboken.get("provider_packages")==["llvm-dev","libclang-common-21-dev"],"Shiboken LLVM/Clang provider closure")
req(shiboken.get("tool_path")=="/usr/bin/llvm-config","Shiboken llvm-config provider path")
req(shiboken.get("resource_header")=="/usr/lib/llvm-21/lib/clang/21/include/stddef.h","Shiboken builtin Clang resource header")
req(shiboken.get("llvm_major")==21,"Shiboken LLVM major")
req(shiboken.get("applies_to")==["knotifications","kstatusnotifieritem","kunitconversion"],"Shiboken provider scope")
req(shiboken.get("kde_feature_effect")=="none","Shiboken provider must not change KDE feature profile")
if contracts.get("state") == "materialized":
    mat=contracts.get("materialization",{})
    req(mat.get("status")=="PASS" and mat.get("result")=="PASS","materialization PASS state")
    req(isinstance(mat.get("workflow_run"),int) and mat.get("workflow_run")>0,"materialization workflow identity")
    req(len(mat.get("evidence",{}))==5,"materialization evidence node set")
    for node_id, evidence in mat.get("evidence",{}).items():
        req(evidence.get("result")=="PASS" and evidence.get("package_attempted") is False and evidence.get("package_state_effect")=="none",f"{node_id}: materialization semantics")
        req(isinstance(evidence.get("artifact_id"),int) and evidence.get("artifact_id")>0,f"{node_id}: materialization evidence artifact")
        for key in ("artifact_sha256","tree_sha256","debian_tree_sha256","debian_tar_sha256","dsc_sha256","orig_tar_sha256"):
            req(len(evidence.get(key,""))==64,f"{node_id}: {key}")

canonical={n["id"]:n for n in tier2["nodes"]}
dep_nodes=deps["nodes"]
for node_id in expected:
    c=contracts["nodes"].get(node_id,{})
    n=canonical[node_id]
    if n.get("state")=="PASS":
        req(n.get("packaging",{}).get("state")=="PASS" and n.get("packaging",{}).get("downstream_eligible") is True,f"{node_id}: retained package PASS")
        req(n.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: retained-pass readiness")
    else:
        req(n.get("state")=="pending",f"{node_id}: pending before package PASS")
        req(n.get("planning",{}).get("readiness") in {"package-contract-ready","build-ready"},f"{node_id}: valid package readiness")
        req(n.get("planning",{}).get("package_contract") in {"not-materialized","materialized"},f"{node_id}: valid package-contract state")
    req(c.get("upstream_version")=="6.30.0",f"{node_id}: version")
    req(c.get("source_sha256")==n.get("source_sha256"),f"{node_id}: source SHA")
    req(c.get("source_package")==f"kf6-{node_id}",f"{node_id}: Ubuntu-compatible source package")
    req(c.get("package_version_candidate")=="6.30.0-0supralinux1",f"{node_id}: first candidate revision")
    req(c.get("cmake_target","").startswith("KF6::"),f"{node_id}: CMake target")
    req(c.get("soname","").endswith(".so.6"),f"{node_id}: SONAME")
    provider_state=dep_nodes[node_id].get("provider_audit")
    if provider_state=="pending-ci":
        audit=deps.get("provider_audit",{})
        req(audit.get("mode")=="remediation-revalidation" and node_id in audit.get("nodes",[]),f"{node_id}: supplemental provider revalidation")
    else:
        req(provider_state=="PASS",f"{node_id}: provider audit PASS")
    req(c.get("compatibility_binary_packages"),f"{node_id}: compatibility binary package set")
    if contracts.get("state") in {"reference-capture-pass","materialized"}:
        refs=c.get("technical_references",{})
        req(refs.get("ubuntu",{}).get("version")=="6.24.0-0ubuntu1",f"{node_id}: pinned Ubuntu reference")
        req(refs.get("debian",{}).get("version")=="6.30.0-1",f"{node_id}: pinned Debian reference")
        req(len(refs.get("ubuntu",{}).get("debian_tar_sha256",""))==64,f"{node_id}: Ubuntu debian.tar SHA")
        req(len(refs.get("debian",{}).get("debian_tar_sha256",""))==64,f"{node_id}: Debian debian.tar SHA")

for node_id,module,pkg in (
    ("knotifications","KNotifications","python3-kf6notifications"),
    ("kstatusnotifieritem","KStatusNotifierItem","python3-kf6statusnotifieritem"),
    ("kunitconversion","KUnitConversion","python3-kf6unitconversion"),
):
    c=contracts["nodes"][node_id]
    req(c.get("python_module")==module,f"{node_id}: upstream Python module")
    req(c.get("selected_profile",{}).get("BUILD_PYTHON_BINDINGS") is True,f"{node_id}: Python bindings selected")
    req(pkg in c.get("supralinux_additional_binary_packages",[]),f"{node_id}: Python binary split")

req(contracts["nodes"]["knotifications"]["selected_profile"].get("BUILD_QML_IF_PROVIDER_AVAILABLE") is True,"KNotifications QML capability preserved")
if contracts.get("state") in {"reference-capture-pass","materialized"}:
    for node_id in ("kcrash","knotifications","kstatusnotifieritem","kunitconversion"):
        req(contracts["nodes"][node_id]["technical_references"]["debian"].get("orig_matches_kde_authority") is True,f"{node_id}: Debian 6.30 orig matches KDE authority")
    synd=contracts["nodes"]["syndication"]["technical_references"]["debian"]
    req(synd.get("orig_matches_kde_authority") is False,"Syndication Debian orig mismatch retained")
    req(synd.get("authority_source_sha256")==contracts["nodes"]["syndication"]["source_sha256"],"Syndication KDE authority source retained")
    req(synd.get("policy")=="verified-files-excluded-repack-required","Syndication mismatch/repack policy")
    dist=contracts["nodes"]["syndication"].get("source_distribution",{})
    req(dist.get("mode")=="verified-files-excluded-repack" and dist.get("authority")=="kde-upstream","Syndication source authority/repack split")
    req(dist.get("repack_orig_sha256")==synd.get("orig_tar_sha256"),"Syndication repack orig pin")

doc=(ROOT/"docs/kde-tier2-package-contracts.md").read_text()
for token in ("technical reference","python3-kf6notifications","python3-kf6statusnotifieritem","python3-kf6unitconversion","not a package PASS"):
    req(token in doc,f"contract docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 package-contract draft: PASS")
print(f"nodes=5; reference state={contracts.get('state')}; package state unchanged")
