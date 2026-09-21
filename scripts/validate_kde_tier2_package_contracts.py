#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

contracts=load("manifests/kde-tier2-package-contracts.json")
tier2=load("manifests/kde-frameworks-tier2.json")
deps=load("manifests/kde-frameworks-tier2-dependencies.json")
plan=load("manifests/kde-tier2-campaign-plan.json")

states={"reference-capture-pending","reference-capture-pass","materialized"}
req(contracts.get("schema")==1,"contract schema")
req(contracts.get("state") in states,"contract state")
req(contracts.get("source_authority")=="kde-upstream" and contracts.get("packaging_authority")=="supralinux","authority split")
req(contracts.get("frameworks_series")=="6.30.0","Frameworks series")
req(contracts.get("compatibility_reference",{}).get("ubuntu",{}).get("role")=="technical-reference-only","Ubuntu reference role")
req(contracts.get("compatibility_reference",{}).get("debian",{}).get("role")=="technical-reference-only","Debian reference role")

selected=contracts.get("selected_nodes",[])
req(0 < len(selected) <= 5 and len(selected)==len(set(selected)),"selected contract batch size/uniqueness")
canonical={n["id"]:n for n in tier2["nodes"]}
dep_nodes=deps.get("nodes",{})
req(set(selected) <= set(canonical),"selected nodes must exist canonically")
req(set(selected) <= set(plan.get("package_contract_ready",[])) | set(plan.get("build_queue",[])) | set(plan.get("retained_pass",[])),"selected nodes must be contract/build/PASS ready")

provider=contracts.get("provider_adaptations",{}).get("ubuntu-resolute",{})
adapt=provider.get("debhelper_compat",{})
req(adapt.get("selected_level")==13 and adapt.get("kde_feature_effect")=="none","Resolute debhelper adaptation")
req(provider.get("changelog_distribution",{}).get("selected")=="resolute","Resolute changelog distribution")

for node_id in selected:
    c=contracts.get("nodes",{}).get(node_id,{})
    n=canonical[node_id]
    req(n.get("state") in {"pending","PASS"},f"{node_id}: contract batch package-state vocabulary")
    req(n.get("planning",{}).get("provider_audit")=="complete",f"{node_id}: provider audit complete")
    if n.get("state")=="PASS":
        req(n.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: retained PASS readiness")
    else:
        req(n.get("planning",{}).get("readiness") in {"package-contract-ready","build-ready"},f"{node_id}: valid package readiness")
    req(c.get("upstream_version")=="6.30.0",f"{node_id}: upstream version")
    req(c.get("source_sha256")==n.get("source_sha256"),f"{node_id}: source authority SHA")
    req(c.get("source_package")==n.get("package_identity",{}).get("source_package"),f"{node_id}: source package identity")
    req(c.get("package_version_candidate")==n.get("package_identity",{}).get("package_version_candidate"),f"{node_id}: package version identity")
    req(c.get("package_version_candidate","").startswith("6.30.0-0supralinux"),f"{node_id}: SupraLINUX package revision")
    req(bool(c.get("compatibility_binary_packages")),f"{node_id}: compatibility binary package set")
    req(c.get("cmake_target","").startswith("KF6::"),f"{node_id}: CMake target")
    req(c.get("soname","").startswith("libKF6") and ".so." in c.get("soname",""),f"{node_id}: SONAME")
    req(dep_nodes.get(node_id,{}).get("provider_audit")=="PASS",f"{node_id}: provider audit PASS")

if contracts.get("state")=="reference-capture-pending":
    ev=contracts.get("reference_evidence",{})
    req(ev.get("result")=="pending" and ev.get("package_state_effect")=="none","pending reference semantics")
    req(contracts.get("materialization",{}).get("status")=="blocked-reference-capture","materialization blocked before reference capture")
else:
    ev=contracts.get("reference_evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","reference capture PASS evidence")
    for key in ("workflow_run","job_id","artifact_id"):
        req(isinstance(ev.get(key),int) and ev.get(key)>0,f"reference evidence {key}")
    req(len(ev.get("artifact_sha256",""))==64,"reference artifact digest")
    for node_id in selected:
        refs=contracts["nodes"][node_id].get("technical_references",{})
        for provider_name in ("ubuntu","debian"):
            r=refs.get(provider_name,{})
            req(bool(r.get("version")),f"{node_id}: {provider_name} reference version")
            req(len(r.get("debian_tar_sha256",""))==64,f"{node_id}: {provider_name} debian.tar SHA")
        req(contracts["nodes"][node_id]["technical_references"]["ubuntu"].get("version")=="6.24.0-0ubuntu1",f"{node_id}: Resolute KDE reference")
        req(contracts["nodes"][node_id]["technical_references"]["debian"].get("version")=="6.30.0-1",f"{node_id}: Debian KDE 6.30 reference")

if "kcontacts" in selected:
    kc=contracts["nodes"]["kcontacts"]
    req(kc.get("build_depends_remove")==["libkf6coreaddons-dev"],"KContacts reference-only KCoreAddons Build-Depends removal")
    req(kc.get("binary_depends_remove",{}).get("libkf6contacts-dev")==["libkf6coreaddons-dev"],"KContacts dev Depends overconstraint removal")
    req(bool(kc.get("rules_auto_test_command")),"KContacts reference-disabled tests restored")
    req(kc.get("provider_adaptation",{}).get("classification")=="technical-reference-overconstraint-removal","KContacts overconstraint classification")

if "kpackage" in selected:
    kp=contracts["nodes"]["kpackage"]
    req(kp.get("build_depends_remove")==["libkf6doctools-dev"],"KPackage technical-reference DocTools Build-Depends removal")
    req(kp.get("selected_profile",{}).get("CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools") is True,"KPackage optional DocTools disabled without matching SupraLINUX provider")
    req(kp.get("install_entries_remove",{}).get("kpackagetool6.install")==["usr/share/man/*/man1/kpackagetool6.1","usr/share/man/man1/kpackagetool6.1"],"KPackage stale DocTools manpage install entries removed")
    cmd=kp.get("rules_auto_test_command","")
    req(cmd.startswith("AS_VALIDATE_NONET=1 xvfb-run "), "KPackage AppStream offline validation scoped to restored tests")
    req("dh_auto_test" in cmd and "--no-parallel" in cmd,"KPackage upstream test invocation remains enabled")
    tea=kp.get("test_environment_adaptation",{})
    req(tea.get("classification")=="provider-validator-network-isolation","KPackage AppStream test-environment classification")
    req(tea.get("tool")=="appstreamcli" and tea.get("observed_provider_version")=="1.1.2-1","KPackage AppStream provider identity")
    req(tea.get("setting")=="AS_VALIDATE_NONET=1" and tea.get("scope")=="dh_auto_test-only","KPackage AppStream offline scope")
    req(tea.get("kde_feature_effect")=="none","KPackage AppStream adaptation KDE feature effect")
    req("v1.1.2" in tea.get("upstream_tool_reference",""),"KPackage AppStream upstream reference")
    req(kp.get("provider_adaptation",{}).get("classification")=="technical-reference-overconstraint-removal","KPackage reference-overconstraint classification")

history=contracts.get("history",[])
req(any(h.get("batch")=="tier2-package-contract-1" for h in history),"historical Batch 1 contract evidence retained")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 package-contract definition: PASS")
print(f"batch={contracts.get('batch')} state={contracts.get('state')} nodes={selected}")
