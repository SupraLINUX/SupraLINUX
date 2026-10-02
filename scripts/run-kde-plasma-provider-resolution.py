#!/usr/bin/env python3
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from kde_plasma_provider_index import apt_file_search_many, apt_source_many

if len(sys.argv) != 2:
    raise SystemExit("usage: run-kde-plasma-provider-resolution.py <provider-inventory.json>")

src = Path(sys.argv[1])
raw = src.read_bytes()
expected = "885bcf1da1521b5f3c78a7e252a81ee4a64b537eda1f9922bec6654bbe415b5c"
actual = hashlib.sha256(raw).hexdigest()
if actual != expected:
    raise SystemExit(f"provider inventory SHA-256 mismatch: {actual}")

inv = json.loads(raw)
out = Path("evidence/kde-plasma-provider-resolution")
out.mkdir(parents=True, exist_ok=True)

cmake = {}
cmake_search_patterns = {}
for req in inv["cmake_requirements"]:
    if req in inv["cmake_categories"].get("kf6-namespace", []):
        cmake[req] = {"decision": "supralinux-frameworks", "provider": "Frameworks 6.30.0", "candidates": []}
        continue
    if req in inv["cmake_categories"].get("qt6-namespace", []):
        cmake[req] = {"decision": "ubuntu-qt6", "provider": "Qt 6.10.2", "candidates": []}
        continue
    if req in inv["cmake_categories"].get("legacy-qt5-kf5", []):
        cmake[req] = {"decision": "legacy-reference-review", "provider": None, "candidates": []}
        continue
    if req == "Qt${QT_MAJOR_VERSION}":
        cmake[req] = {"decision": "ubuntu-qt6", "provider": "Qt 6.10.2", "candidates": []}
        continue
    if req == "KF${QT_MAJOR_VERSION}ConfigWidgets":
        cmake[req] = {"decision": "supralinux-frameworks", "provider": "KF6ConfigWidgets / Frameworks 6.30.0", "candidates": []}
        continue
    if req == "KF${QT_MAJOR_VERSION}KirigamiAddons":
        cmake[req] = {"decision": "kde-extra-review", "provider": "KirigamiAddons Qt6 branch", "candidates": []}
        continue
    if req == "${GENMODULE}":
        cmake[req] = {"decision": "dynamic-source-context-review", "provider": None, "candidates": []}
        continue

    esc = re.escape(req)
    patterns = [
        rf"/{esc}Config\.cmake$",
        rf"/{re.escape(req.lower())}-config\.cmake$",
        rf"/{esc}-config\.cmake$",
        rf"/(?:s?bin)/{esc}$",
    ]
    cmake_search_patterns[req] = patterns

all_cmake_patterns = [p for patterns in cmake_search_patterns.values() for p in patterns]
cmake_hits = apt_file_search_many(all_cmake_patterns)

for req, patterns in cmake_search_patterns.items():
    config_candidates = sorted(set().union(*(set(cmake_hits[p]) for p in patterns[:3])))
    command_candidates = cmake_hits[patterns[3]]
    if config_candidates:
        cmake[req] = {
            "decision": "ubuntu-binary-candidate" if len(config_candidates) == 1 else "ubuntu-binary-ambiguous",
            "provider": config_candidates[0] if len(config_candidates) == 1 else None,
            "candidates": config_candidates,
        }
    else:
        cmake[req] = {
            "decision": "ubuntu-command-candidate" if len(command_candidates) == 1 else
                        "ubuntu-command-ambiguous" if len(command_candidates) > 1 else "unresolved",
            "provider": command_candidates[0] if len(command_candidates) == 1 else None,
            "candidates": command_candidates,
        }
pkg = {}
pkg_patterns = {}
for raw_req in inv["pkg_config_requirements"]:
    module = re.split(r"[<>=]", raw_req, 1)[0].strip()
    pattern = rf"/pkgconfig/{re.escape(module)}\.pc$"
    pkg_patterns[raw_req] = (module, pattern)

pkg_hits = apt_file_search_many([pattern for _, pattern in pkg_patterns.values()])
for raw_req, (module, pattern) in pkg_patterns.items():
    candidates = pkg_hits[pattern]
    pkg[raw_req] = {
        "module": module,
        "decision": "ubuntu-binary-candidate" if len(candidates) == 1 else
                    "ubuntu-binary-ambiguous" if len(candidates) > 1 else "unresolved",
        "provider": candidates[0] if len(candidates) == 1 else None,
        "candidates": candidates,
    }

qml = {}
qml_patterns = {
    module: rf"/qml/{re.escape(module.replace('.', '/'))}/qmldir$"
    for module in inv["qml_requirements"]
}
qml_hits = apt_file_search_many(qml_patterns.values())
for module in inv["qml_requirements"]:
    if module.startswith("Qt") or module.startswith("QtQuick"):
        provider_class = "ubuntu-qt6-qml"
    elif module.startswith("org.kde.plasma.") or module in {"org.kde.milou", "org.kde.pipewire"}:
        provider_class = "plasma-internal"
    elif module.startswith("org.kde."):
        provider_class = "kde-framework-or-extra"
    else:
        provider_class = "unknown"
    candidates = qml_hits[qml_patterns[module]]
    qml[module] = {
        "provider_class": provider_class,
        "decision": "ubuntu-binary-candidate" if len(candidates) == 1 else
                    "ubuntu-binary-ambiguous" if len(candidates) > 1 else "internal-or-unresolved",
        "provider": candidates[0] if len(candidates) == 1 else None,
        "candidates": candidates,
    }
source_ids = ["aurorae","bluedevil","breeze","breeze-grub","breeze-gtk","breeze-plymouth","discover","drkonqi","flatpak-kcm","kactivitymanagerd","kde-cli-tools","kde-gtk-config","kdecoration","kdeplasma-addons","kgamma","kglobalacceld","kinfocenter","kmenuedit","knighttime","kpipewire","krdp","kscreen","kscreenlocker","ksshaskpass","ksystemstats","kwallet-pam","kwayland","kwayland-integration","kwin","kwin-x11","kwrited","layer-shell-qt","libkscreen","libksysguard","libplasma","milou","ocean-sound-theme","oxygen","oxygen-sounds","plasma-activities","plasma-activities-stats","plasma-bigscreen","plasma-browser-integration","plasma-desktop","plasma-dialer","plasma-disks","plasma-firewall","plasma-integration","plasma-keyboard","plasma-login-manager","plasma-mobile","plasma-nano","plasma-nm","plasma-pa","plasma-sdk","plasma-setup","plasma-systemmonitor","plasma-thunderbolt","plasma-vault","plasma-welcome","plasma-workspace","plasma-workspace-wallpapers","plasma5support","plymouth-kcm","polkit-kde-agent-1","powerdevil","print-manager","qqc2-breeze-style","sddm-kcm","spacebar","spectacle","systemsettings","union","wacomtablet","xdg-desktop-portal-kde"]
ubuntu_sources = apt_source_many(source_ids)

(out / "cmake-resolution.json").write_text(json.dumps(cmake, indent=2, sort_keys=True) + "\n")
(out / "pkg-config-resolution.json").write_text(json.dumps(pkg, indent=2, sort_keys=True) + "\n")
(out / "qml-resolution.json").write_text(json.dumps(qml, indent=2, sort_keys=True) + "\n")
(out / "ubuntu-source-reference.json").write_text(json.dumps(ubuntu_sources, indent=2, sort_keys=True) + "\n")

def counts(mapping):
    result = {}
    for value in mapping.values():
        key = value.get("decision", "unknown")
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))

result = {
    "schema": 1,
    "node": "plasma-provider-resolution",
    "state": "PASS",
    "run_kind": "planning-provider-resolution",
    "authoritative": False,
    "package_execution_started": False,
    "consumes_package_attempt": False,
    "canonical_package_state_effect": "none",
    "plasma_version": "6.7.5",
    "provider_inventory_sha256": actual,
    "cmake_decisions": counts(cmake),
    "pkg_config_decisions": counts(pkg),
    "qml_decisions": counts(qml),
    "ubuntu_source_references_available": sum(1 for x in ubuntu_sources.values() if x["available"]),
    "ubuntu_source_references_missing": sum(1 for x in ubuntu_sources.values() if not x["available"]),
    "review_required": True,
    "next_gate": "plasma-provider-resolution-review",
}
(out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2))
