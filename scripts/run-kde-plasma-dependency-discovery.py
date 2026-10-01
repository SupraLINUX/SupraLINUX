#!/usr/bin/env python3
import hashlib
import io
import json
import re
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/kde-plasma.json"
OUT = ROOT / "evidence/kde-plasma-dependency-discovery"
OUT.mkdir(parents=True, exist_ok=True)

manifest = json.loads(MANIFEST.read_text())
sources = manifest["sources"]
source_ids = {item["id"] for item in sources}

aliases = {
    "KWin": "kwin",
    "KWinEffects": "kwin",
    "KWinDBusInterface": "kwin",
    "KDecoration2": "kdecoration",
    "KGlobalAccelD": "kglobalacceld",
    "KScreenLocker": "kscreenlocker",
    "KF6Screen": "libkscreen",
    "KScreen": "libkscreen",
    "KPipeWire": "kpipewire",
    "Plasma": "libplasma",
    "PlasmaQuick": "libplasma",
    "Plasma5Support": "plasma5support",
    "KWayland": "kwayland",
    "KWaylandClient": "kwayland",
    "LayerShellQt": "layer-shell-qt",
    "KSysGuard": "libksysguard",
    "KActivities": "plasma-activities",
    "KActivitiesStats": "plasma-activities-stats",
    "LibKWorkspace": "plasma-workspace",
    "PlasmaWorkspace": "plasma-workspace",
}

def compact(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())

source_by_compact = {compact(item["id"]): item["id"] for item in sources}
find_re = re.compile(r"\b(?:find_package|find_dependency)\s*\(\s*([A-Za-z0-9_.+:-]+)", re.IGNORECASE)
qml_re = re.compile(r"\becm_find_qmlmodule\s*\(\s*([^\s\)]+)", re.IGNORECASE)
pkg_re = re.compile(r"\bpkg_check_modules\s*\(\s*[^\s\)]+\s+(?:REQUIRED\s+)?([^\s\)]+)", re.IGNORECASE)

errors = []
nodes = {}
verified = 0

for index, item in enumerate(sources, 1):
    source_id = item["id"]
    url = item["source_url"]
    expected = item["source_sha256"]
    print(f"[{index}/{len(sources)}] {source_id}", flush=True)

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SupraLINUX-Plasma-Dependency-Discovery/1"})
        with urllib.request.urlopen(request, timeout=120) as response:
            blob = response.read()
    except Exception as exc:
        errors.append(f"{source_id}: download failed: {exc}")
        nodes[source_id] = {"state": "download-failed"}
        continue

    actual = hashlib.sha256(blob).hexdigest()
    if actual != expected:
        errors.append(f"{source_id}: SHA-256 mismatch: expected {expected}, got {actual}")
        nodes[source_id] = {"state": "hash-mismatch", "actual_sha256": actual}
        continue

    verified += 1
    cmake_chunks = []
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:xz") as archive:
            for member in archive.getmembers():
                if not member.isfile() or member.size > 2 * 1024 * 1024:
                    continue
                name = member.name
                if not (name.endswith("/CMakeLists.txt") or name.endswith(".cmake")):
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                cmake_chunks.append(handle.read().decode("utf-8", errors="ignore"))
    except Exception as exc:
        errors.append(f"{source_id}: CMake extraction failed: {exc}")
        nodes[source_id] = {"state": "cmake-extraction-failed", "source_sha256": actual}
        continue

    cmake = "\n".join(cmake_chunks)
    packages = sorted(set(find_re.findall(cmake)))
    qml_modules = sorted(set(qml_re.findall(cmake)))
    pkg_modules = sorted(set(pkg_re.findall(cmake)))

    internal = set()
    external = set()
    for package in packages:
        target = aliases.get(package)
        if target is None:
            target = source_by_compact.get(compact(package))
        if target in source_ids and target != source_id:
            internal.add(target)
        else:
            external.add(package)

    nodes[source_id] = {
        "state": "source-verified-cmake-scanned",
        "source_sha256": actual,
        "cmake_files_scanned": len(cmake_chunks),
        "find_packages": packages,
        "internal_candidate_dependencies": sorted(internal),
        "external_requirements": sorted(external),
        "qml_modules": qml_modules,
        "pkg_config_modules": pkg_modules,
    }

result = {
    "schema": 1,
    "node": "plasma-dependency-discovery",
    "state": "PASS" if not errors and verified == len(sources) else "FAIL",
    "run_kind": "planning-source-dependency-discovery",
    "authoritative": False,
    "package_execution_started": False,
    "consumes_package_attempt": False,
    "canonical_package_state_effect": "none",
    "plasma_version": manifest["release"]["version"],
    "source_count": len(sources),
    "source_sha256_verified": verified,
    "dependency_edge_status": "candidate-review-required",
    "signature_verification": manifest["release"]["source_signature_verification"],
    "errors": errors,
}

(OUT / "dependencies.json").write_text(json.dumps({
    "schema": 1,
    "plasma_version": manifest["release"]["version"],
    "authority": "kde-upstream-source-cmake",
    "candidate_only": True,
    "nodes": nodes,
}, indent=2) + "\n")
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")

print(json.dumps(result, indent=2))
sys.exit(0 if result["state"] == "PASS" else 1)
