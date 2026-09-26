#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/kio-round18-provider-contract")
OUT.mkdir(parents=True, exist_ok=True)

def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)

def candidate(pkg):
    text = run(["apt-cache", "policy", pkg]).stdout
    for line in text.splitlines():
        if line.strip().startswith("Candidate:"):
            value = line.split(":", 1)[1].strip()
            if value and value != "(none)":
                return value
    raise RuntimeError(f"{pkg}: no APT candidate")

def stanza(pkg, version):
    text = run(["apt-cache", "show", f"{pkg}={version}"]).stdout
    blocks = [x for x in text.split("\n\n") if x.strip()]
    if not blocks:
        raise RuntimeError(f"{pkg}: no control stanza")
    fields = {}
    current = None
    for line in blocks[0].splitlines():
        if line[:1].isspace() and current:
            fields[current] += " " + line.strip()
        elif ":" in line:
            current, value = line.split(":", 1)
            fields[current] = value.strip()
    return fields, text

os_release = {}
for line in Path("/etc/os-release").read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os_release[key] = value.strip().strip('"')
if os_release.get("VERSION_ID") != "26.04":
    raise RuntimeError(f"expected Ubuntu 26.04, got {os_release.get('PRETTY_NAME')}")

subprocess.run(["sudo", "apt-get", "update"], check=True)

packages = [
    "qt6-svg-plugins",
    "qt6-svg-dev",
    "libqt6gui6",
    "libkf6iconthemes6",
    "kf6-breeze-icon-theme",
]
versions = {pkg: candidate(pkg) for pkg in packages}
metadata = {}
raw = []
for pkg in packages:
    fields, text = stanza(pkg, versions[pkg])
    metadata[pkg] = fields
    raw.append(f"===== {pkg} {versions[pkg]} =====\n{text}")

if versions["qt6-svg-plugins"] != "6.10.2-2":
    raise RuntimeError(f"unexpected qt6-svg-plugins version: {versions['qt6-svg-plugins']}")
if versions["qt6-svg-dev"] != "6.10.2-2":
    raise RuntimeError(f"unexpected qt6-svg-dev version: {versions['qt6-svg-dev']}")
if not versions["libqt6gui6"].startswith("6.10.2"):
    raise RuntimeError(f"unexpected libqt6gui6 series: {versions['libqt6gui6']}")

svg_dev_depends = metadata["qt6-svg-dev"].get("Depends", "")
gui_recommends = metadata["libqt6gui6"].get("Recommends", "")
kicon_depends = metadata["libkf6iconthemes6"].get("Depends", "")
breeze_depends = metadata["kf6-breeze-icon-theme"].get("Depends", "")

if "qt6-svg-plugins" in svg_dev_depends:
    raise RuntimeError("qt6-svg-dev unexpectedly hard-depends on qt6-svg-plugins")
if "qt6-svg-plugins" not in gui_recommends:
    raise RuntimeError("libqt6gui6 does not recommend qt6-svg-plugins")
if "libqt6svg6" not in kicon_depends:
    raise RuntimeError("libkf6iconthemes6 does not depend on libqt6svg6")
if "qt6-svg-plugins" in kicon_depends:
    raise RuntimeError("libkf6iconthemes6 unexpectedly hard-depends on qt6-svg-plugins")
if "qt6-svg-plugins" in breeze_depends:
    raise RuntimeError("kf6-breeze-icon-theme unexpectedly hard-depends on qt6-svg-plugins")

with tempfile.TemporaryDirectory() as td:
    subprocess.run(
        ["apt-get", "download", f"qt6-svg-plugins={versions['qt6-svg-plugins']}"],
        cwd=td,
        check=True,
        text=True,
    )
    debs = list(Path(td).glob("qt6-svg-plugins_*.deb"))
    if len(debs) != 1:
        raise RuntimeError(f"expected one qt6-svg-plugins deb, found {len(debs)}")
    deb = debs[0]
    payload = run(["dpkg-deb", "-c", str(deb)]).stdout
    required = [
        "/usr/lib/x86_64-linux-gnu/qt6/plugins/iconengines/libqsvgicon.so",
        "/usr/lib/x86_64-linux-gnu/qt6/plugins/imageformats/libqsvg.so",
    ]
    missing = [path for path in required if path not in payload]
    if missing:
        raise RuntimeError(f"qt6-svg-plugins payload missing: {missing}")
    deb_sha256 = hashlib.sha256(deb.read_bytes()).hexdigest()

(OUT / "apt-metadata.txt").write_text("\n".join(raw))
result = {
    "schema": 1,
    "result": "AUDIT_COMPLETE",
    "ubuntu_version": os_release["VERSION_ID"],
    "package_versions": versions,
    "contracts": {
        "qt6_svg_dev_depends_on_plugin": False,
        "libqt6gui6_recommends_plugin": True,
        "libkf6iconthemes6_depends_on_libqt6svg6": True,
        "libkf6iconthemes6_depends_on_plugin": False,
        "breeze_icon_theme_depends_on_plugin": False,
    },
    "qt6_svg_plugins_deb_sha256": deb_sha256,
    "plugin_files": required,
    "decision": {
        "owner": "kio-build-test-closure",
        "relation": "qt6-svg-plugins <!nocheck>",
        "runtime_binary_relation": "none",
    },
    "package_attempted": False,
    "package_state_effect": "none",
}
(OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
