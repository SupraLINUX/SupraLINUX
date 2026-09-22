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
selected=contracts.get("selected_nodes",[])
mat=contracts.get("materialization",{})
state=contracts.get("state")
canonical={n["id"]:n for n in tier2["nodes"]}

req(mat.get("method")=="kde-authority-source-plus-pinned-debian-tree","materialization method")
req(mat.get("package_state_effect")=="none" and mat.get("package_attempted") is False,"materialization package-state semantics")
req(mat.get("maintainer_during_ci")=="SupraLINUX Build System <build@supralinux.invalid>","CI maintainer marker")
req(mat.get("publication_blocker")=="replace-ci-maintainer-with-approved-project-contact","publication blocker")

if state=="reference-capture-pending":
    req(mat.get("status")=="blocked-reference-capture","pending references must block materialization")
    req(set(mat.get("targets",[]))==set(selected),"blocked target set")
else:
    req(state in {"reference-capture-pass","materialized"},"materializable contract state")
    req(mat.get("status") in {"pending-ci","PASS"},"materialization status")
    req(set(mat.get("targets",[])) <= set(selected),"materialization targets selected")
    for node_id in selected:
        c=contracts["nodes"][node_id]
        refs=c.get("technical_references",{})
        req(refs.get("debian",{}).get("version")=="6.30.0-1",f"{node_id}: Debian 6.30 reference")
        req(len(refs.get("debian",{}).get("debian_tar_sha256",""))==64,f"{node_id}: pinned Debian tree digest")
    if mat.get("status")=="PASS":
        req(mat.get("result")=="PASS","materialization result")
        req(set(mat.get("evidence",{})) <= set(selected),"materialization evidence selected")

if "kcontacts" in selected:
    kc=contracts["nodes"]["kcontacts"]
    req(kc.get("build_depends_remove")==["libkf6coreaddons-dev"],"KContacts KCoreAddons Build-Depends overconstraint removal")
    req(kc.get("binary_depends_remove",{}).get("libkf6contacts-dev")==["libkf6coreaddons-dev"],"KContacts binary Depends overconstraint removal")
    req(bool(kc.get("rules_auto_test_command")),"KContacts tests restored")

if "kpackage" in selected:
    kp=contracts["nodes"]["kpackage"]
    req(kp.get("build_depends_remove")==["libkf6doctools-dev"],"KPackage DocTools Build-Depends removal")
    req(kp.get("selected_profile",{}).get("CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools") is True,"KPackage DocTools CMake disable")
    req(bool(kp.get("install_entries_remove",{}).get("kpackagetool6.install")),"KPackage DocTools-only install entries removed")
    cmd=kp.get("rules_auto_test_command","")
    req(cmd.startswith("AS_VALIDATE_NONET=1 xvfb-run ") and "dh_auto_test" in cmd,"KPackage tests restored with offline AppStream validation")
    tea=kp.get("test_environment_adaptation",{})
    req(tea.get("tool")=="appstreamcli" and tea.get("observed_provider_version")=="1.1.2-1","KPackage AppStream provider pin")
    req(tea.get("setting")=="AS_VALIDATE_NONET=1" and tea.get("scope")=="dh_auto_test-only","KPackage AppStream offline materialization scope")
    req(tea.get("kde_feature_effect")=="none","KPackage AppStream adaptation feature neutrality")

if "kdeclarative" in selected:
    kd=contracts["nodes"]["kdeclarative"]
    splits=kd.get("binary_package_splits",[])
    req(len(splits)==1 and splits[0].get("package")=="libkquickcontrolsprivate0","KDeclarative Ubuntu binary split")
    req(splits[0].get("source_match_substrings")==["libkquickcontrolsprivate.so.0","libkquickcontrolsprivate.so.6."],"KDeclarative complete private-library payload split")
    req(kd.get("provider_adaptation",{}).get("payload_contract")==["libkquickcontrolsprivate.so.0","libkquickcontrolsprivate.so.6.30.0"],"KDeclarative private-library payload contract")
    req(kd.get("provider_adaptation",{}).get("kde_feature_effect")=="none","KDeclarative split feature neutrality")

if "kservice" in selected:
    ks=contracts["nodes"]["kservice"]
    req(ks.get("build_depends_remove")==["libkf6doctools-dev"],"KService optional DocTools Build-Depends removal")
    req(ks.get("binary_depends_remove",{}).get("libkf6service-dev")==["libkf6doctools-dev"],"KService optional DocTools dev Depends removal")
    req(bool(ks.get("install_entries_remove",{}).get("libkf6service-bin.install")),"KService DocTools-only manpage entries removed")
    req(ks.get("symbols_adjustments")==[{"file":"libkf6service6.symbols","symbol":"_ZSt19piecewise_construct@Base","version":"6.30.0","tag":"optional=toolchain"}],"KService toolchain-dependent symbol baseline")

targets=set(mat.get("targets",[]))
for node_id in selected:
    n=canonical[node_id]
    req(n.get("state") in {"pending","PASS"},f"{node_id}: materialization/package state vocabulary")
    if n.get("state")=="PASS":
        req(n.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: retained PASS readiness")
    elif node_id in targets:
        req(n.get("planning",{}).get("readiness")=="package-contract-ready",f"{node_id}: rematerialization readiness")
        req(n.get("planning",{}).get("package_contract")=="not-materialized",f"{node_id}: rematerialization contract state")
    else:
        req(n.get("planning",{}).get("readiness") in {"package-contract-ready","build-ready"},f"{node_id}: readiness")

for path in (
  "scripts/materialize_kde_tier2_package.py",
  "scripts/run-kde-tier2-package-materialization.sh",
  "scripts/kde-tier2-materialization-needed.sh",
  "scripts/plan-kde-tier2-materialization.py",
  ".github/workflows/kde-tier2-package-materialization.yml",
):
    req((ROOT/path).exists(),f"missing materialization component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 package-materialization definition: PASS")
print(f"state={state} status={mat.get('status')} nodes={selected}")
