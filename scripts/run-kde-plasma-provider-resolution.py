#!/usr/bin/env python3
import hashlib
import json
import re
import sys
from pathlib import Path

from kde_plasma_provider_index import apt_source_many, build_dep_packages, apt_policy_many

if len(sys.argv) != 3:
    raise SystemExit("usage: run-kde-plasma-provider-resolution.py <provider-inventory.json> <dependencies.json>")

inventory_path=Path(sys.argv[1])
deps_path=Path(sys.argv[2])
raw=inventory_path.read_bytes()
expected="885bcf1da1521b5f3c78a7e252a81ee4a64b537eda1f9922bec6654bbe415b5c"
actual=hashlib.sha256(raw).hexdigest()
if actual!=expected:
    raise SystemExit(f"provider inventory SHA-256 mismatch: {actual}")

inv=json.loads(raw)
deps=json.loads(deps_path.read_text())
if deps.get("parser_revision")!=4 or len(deps.get("nodes",{}))!=75:
    raise SystemExit("unexpected dependency discovery contract")

out=Path("evidence/kde-plasma-provider-resolution")
out.mkdir(parents=True,exist_ok=True)

source_ids = ["aurorae","bluedevil","breeze","breeze-grub","breeze-gtk","breeze-plymouth","discover","drkonqi","flatpak-kcm","kactivitymanagerd","kde-cli-tools","kde-gtk-config","kdecoration","kdeplasma-addons","kgamma","kglobalacceld","kinfocenter","kmenuedit","knighttime","kpipewire","krdp","kscreen","kscreenlocker","ksshaskpass","ksystemstats","kwallet-pam","kwayland","kwayland-integration","kwin","kwin-x11","kwrited","layer-shell-qt","libkscreen","libksysguard","libplasma","milou","ocean-sound-theme","oxygen","oxygen-sounds","plasma-activities","plasma-activities-stats","plasma-bigscreen","plasma-browser-integration","plasma-desktop","plasma-dialer","plasma-disks","plasma-firewall","plasma-integration","plasma-keyboard","plasma-login-manager","plasma-mobile","plasma-nano","plasma-nm","plasma-pa","plasma-sdk","plasma-setup","plasma-systemmonitor","plasma-thunderbolt","plasma-vault","plasma-welcome","plasma-workspace","plasma-workspace-wallpapers","plasma5support","plymouth-kcm","polkit-kde-agent-1","powerdevil","print-manager","qqc2-breeze-style","sddm-kcm","spacebar","spectacle","systemsettings","union","wacomtablet","xdg-desktop-portal-kde"]
ubuntu_sources=apt_source_many(source_ids)

all_build_deps=set()
source_build_deps={}
for name,data in ubuntu_sources.items():
    pkgs=build_dep_packages(data)
    source_build_deps[name]=pkgs
    all_build_deps.update(pkgs)

policy=apt_policy_many(sorted(all_build_deps))
source_provider_summary={}
for name in source_ids:
    pkgs=source_build_deps[name]
    available=[p for p in pkgs if policy.get(p)]
    missing=[p for p in pkgs if not policy.get(p)]
    source_provider_summary[name]={
        "ubuntu_source_reference_available":ubuntu_sources[name]["available"],
        "build_dep_package_count":len(pkgs),
        "available_build_dep_candidates":available,
        "missing_build_dep_candidates":missing,
        "provider_reference_status":
            "ubuntu-source-reference-complete" if ubuntu_sources[name]["available"] and not missing else
            "ubuntu-source-reference-partial" if ubuntu_sources[name]["available"] else
            "ubuntu-source-reference-missing"
    }

known={}
for req in inv["cmake_requirements"]:
    if req in inv["cmake_categories"].get("kf6-namespace",[]):
        known[req]={"decision":"supralinux-frameworks","provider":"Frameworks 6.30.0"}
    elif req in inv["cmake_categories"].get("qt6-namespace",[]):
        known[req]={"decision":"ubuntu-qt6","provider":"Qt 6.10.2"}
    elif req in inv["cmake_categories"].get("legacy-qt5-kf5",[]):
        known[req]={"decision":"legacy-reference-review","provider":None}
    elif req=="Qt${QT_MAJOR_VERSION}":
        known[req]={"decision":"ubuntu-qt6","provider":"Qt 6.10.2"}
    elif req=="KF${QT_MAJOR_VERSION}ConfigWidgets":
        known[req]={"decision":"supralinux-frameworks","provider":"KF6ConfigWidgets / Frameworks 6.30.0"}
    elif req=="KF${QT_MAJOR_VERSION}KirigamiAddons":
        known[req]={"decision":"kde-extra-review","provider":"KirigamiAddons Qt6 branch"}
    elif req=="${GENMODULE}":
        known[req]={"decision":"dynamic-source-context-review","provider":None}
    else:
        known[req]={"decision":"source-build-dep-reference","provider":None}

qml={}
for module in inv["qml_requirements"]:
    if module.startswith("Qt") or module.startswith("QtQuick"):
        qml[module]={"decision":"ubuntu-qt6-qml","provider":"Qt 6.10.2"}
    elif module.startswith("org.kde.plasma.") or module in {"org.kde.milou","org.kde.pipewire"}:
        qml[module]={"decision":"plasma-internal","provider":"Plasma 6.7.5 DAG"}
    elif module.startswith("org.kde."):
        qml[module]={"decision":"kde-framework-or-extra-review","provider":None}
    else:
        qml[module]={"decision":"review-required","provider":None}

pkg={}
for raw_req in inv["pkg_config_requirements"]:
    module=re.split(r"[<>=]",raw_req,maxsplit=1)[0].strip()
    pkg[raw_req]={"module":module,"decision":"source-build-dep-reference","provider":None}

node_resolution={}
for node_id,node in deps["nodes"].items():
    src=source_provider_summary[node_id]
    node_resolution[node_id]={
        "internal_candidate_dependencies":node.get("internal_candidate_dependencies",[]),
        "cmake_requirements":node.get("external_requirements",[]),
        "qml_requirements":node.get("external_qml_modules",[]),
        "pkg_config_requirements":node.get("pkg_config_modules",[]),
        "ubuntu_source_reference":src,
    }

(out/"ubuntu-source-reference.json").write_text(json.dumps(ubuntu_sources,indent=2,sort_keys=True)+"\n")
(out/"ubuntu-build-dep-providers.json").write_text(json.dumps({
    "package_candidates":policy,
    "per_source":source_provider_summary,
},indent=2,sort_keys=True)+"\n")
(out/"cmake-resolution.json").write_text(json.dumps(known,indent=2,sort_keys=True)+"\n")
(out/"pkg-config-resolution.json").write_text(json.dumps(pkg,indent=2,sort_keys=True)+"\n")
(out/"qml-resolution.json").write_text(json.dumps(qml,indent=2,sort_keys=True)+"\n")
(out/"node-resolution.json").write_text(json.dumps(node_resolution,indent=2,sort_keys=True)+"\n")

result={
    "schema":1,
    "node":"plasma-provider-resolution",
    "state":"PASS",
    "run_kind":"planning-provider-resolution",
    "authoritative":False,
    "package_execution_started":False,
    "consumes_package_attempt":False,
    "canonical_package_state_effect":"none",
    "plasma_version":"6.7.5",
    "provider_inventory_sha256":actual,
    "ubuntu_source_references_available":sum(1 for x in ubuntu_sources.values() if x["available"]),
    "ubuntu_source_references_missing":sum(1 for x in ubuntu_sources.values() if not x["available"]),
    "ubuntu_build_dep_packages":len(all_build_deps),
    "ubuntu_build_dep_candidates_available":sum(1 for x in policy.values() if x),
    "ubuntu_build_dep_candidates_missing":sum(1 for x in policy.values() if not x),
    "known_cmake_direct_decisions":sum(1 for x in known.values() if x["decision"]!="source-build-dep-reference"),
    "cmake_source_reference_reviews":sum(1 for x in known.values() if x["decision"]=="source-build-dep-reference"),
    "qml_direct_decisions":sum(1 for x in qml.values() if x["provider"] is not None),
    "review_required":True,
    "next_gate":"plasma-provider-resolution-review",
}
(out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2))
