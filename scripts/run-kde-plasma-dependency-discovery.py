#!/usr/bin/env python3
import hashlib
import io
import json
import re
import shlex
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/kde-plasma.json"
OUT = ROOT / "evidence/kde-plasma-dependency-discovery"
OUT.mkdir(parents=True, exist_ok=True)

manifest = json.loads(MANIFEST.read_text())
sources = manifest["sources"]
source_ids = {item["id"] for item in sources}

# Fallbacks only. The primary internal-provider authority in this validation
# run is the package config/QML metadata actually present in each verified
# upstream source tarball.
fallback_aliases = {
    "KWin": "kwin",
    "KWinEffects": "kwin",
    "KWinDBusInterface": "kwin",
    "KDecoration2": "kdecoration",
    "KDecoration3": "kdecoration",
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
    "LibTaskManager": "plasma-workspace",
    "LibNotificationManager": "plasma-workspace",
    "LibKLookAndFeel": "plasma-workspace",
    "KSMServerDBusInterface": "plasma-workspace",
    "KRunnerAppDBusInterface": "plasma-workspace",
    "ScreenSaverDBusInterface": "kscreenlocker",
}

def compact(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())

source_by_compact = {compact(item["id"]): item["id"] for item in sources}
find_re = re.compile(r"\b(?:find_package|find_dependency)\s*\(\s*([A-Za-z0-9_.+:-]+)", re.IGNORECASE)
qml_re = re.compile(r"\becm_find_qmlmodule\s*\(\s*([^\s\)]+)", re.IGNORECASE)
pkg_call_re = re.compile(r"\bpkg_check_modules\s*\(\s*([^\)]+)\)", re.IGNORECASE | re.DOTALL)
config_name_re = re.compile(r"^(.+?)Config\.cmake(?:\.in)?$", re.IGNORECASE)
pkg_keywords = {
    "REQUIRED", "QUIET", "IMPORTED_TARGET", "GLOBAL", "NO_CMAKE_PATH",
    "NO_CMAKE_ENVIRONMENT_PATH", "NO_SYSTEM_ENVIRONMENT_PATH",
}

errors = []
raw_nodes = {}
cmake_provider_candidates = {}
qml_provider_candidates = {}
verified = 0

for index, item in enumerate(sources, 1):
    source_id = item["id"]
    url = item["source_url"]
    expected = item["source_sha256"]
    print(f"[{index}/{len(sources)}] {source_id}", flush=True)

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SupraLINUX-Plasma-Dependency-Discovery/2"})
        with urllib.request.urlopen(request, timeout=120) as response:
            blob = response.read()
    except Exception as exc:
        errors.append(f"{source_id}: download failed: {exc}")
        raw_nodes[source_id] = {"state": "download-failed"}
        continue

    actual = hashlib.sha256(blob).hexdigest()
    if actual != expected:
        errors.append(f"{source_id}: SHA-256 mismatch: expected {expected}, got {actual}")
        raw_nodes[source_id] = {"state": "hash-mismatch", "actual_sha256": actual}
        continue

    verified += 1
    cmake_chunks = []
    provided_cmake = set()
    provided_qml = set()

    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:xz") as archive:
            for member in archive.getmembers():
                if not member.isfile() or member.size > 2 * 1024 * 1024:
                    continue

                basename = Path(member.name).name
                config_match = config_name_re.match(basename)
                if config_match and not config_match.group(1).lower().endswith("version"):
                    package_name = config_match.group(1)
                    if package_name and package_name.lower() not in {"config", "package"}:
                        provided_cmake.add(package_name)

                handle = None
                if basename == "qmldir":
                    handle = archive.extractfile(member)
                    if handle is not None:
                        qml_text = handle.read().decode("utf-8", errors="ignore")
                        for line in qml_text.splitlines():
                            line = line.strip()
                            if line.startswith("module "):
                                module = line.split(None, 1)[1].strip()
                                if module:
                                    provided_qml.add(module)
                    continue

                if not (member.name.endswith("/CMakeLists.txt") or member.name.endswith(".cmake")):
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                cmake_chunks.append(handle.read().decode("utf-8", errors="ignore"))
    except Exception as exc:
        errors.append(f"{source_id}: metadata extraction failed: {exc}")
        raw_nodes[source_id] = {"state": "metadata-extraction-failed", "source_sha256": actual}
        continue

    cmake = "\n".join(cmake_chunks)
    packages = sorted(set(find_re.findall(cmake)))
    qml_modules = sorted(set(qml_re.findall(cmake)))

    pkg_modules = set()
    for call in pkg_call_re.findall(cmake):
        try:
            tokens = shlex.split(call.replace("\n", " "))
        except ValueError:
            tokens = call.replace("\n", " ").split()
        # First token is the CMake variable prefix.
        for token in tokens[1:]:
            if token.upper() in pkg_keywords:
                continue
            if token.startswith("$") or token.startswith("${"):
                continue
            if re.search(r"[A-Za-z0-9]", token):
                pkg_modules.add(token)

    raw_nodes[source_id] = {
        "state": "source-verified-metadata-scanned",
        "source_sha256": actual,
        "cmake_files_scanned": len(cmake_chunks),
        "find_packages": packages,
        "qml_modules": qml_modules,
        "pkg_config_modules": sorted(pkg_modules),
        "provided_cmake_packages": sorted(provided_cmake),
        "provided_qml_modules": sorted(provided_qml),
    }

    for package_name in provided_cmake:
        cmake_provider_candidates.setdefault(compact(package_name), set()).add(source_id)
    for module_name in provided_qml:
        qml_provider_candidates.setdefault(module_name, set()).add(source_id)

nodes = {}
internal_edge_count = 0
internal_qml_edge_count = 0
ambiguous_provider_refs = 0

for source_id, raw in raw_nodes.items():
    if raw.get("state") != "source-verified-metadata-scanned":
        nodes[source_id] = raw
        continue

    internal = set()
    external = set()
    self_requirements = set()
    ambiguous = {}

    for package in raw["find_packages"]:
        candidates = set(cmake_provider_candidates.get(compact(package), set()))
        fallback = fallback_aliases.get(package)
        if fallback:
            candidates.add(fallback)
        direct = source_by_compact.get(compact(package))
        if direct:
            candidates.add(direct)

        if source_id in candidates and len(candidates) == 1:
            self_requirements.add(package)
            continue

        candidates.discard(source_id)
        if len(candidates) == 1:
            internal.add(next(iter(candidates)))
        elif len(candidates) > 1:
            ambiguous[package] = sorted(candidates)
            ambiguous_provider_refs += 1
        else:
            external.add(package)

    internal_qml = set()
    external_qml = set()
    ambiguous_qml = {}
    for module in raw["qml_modules"]:
        candidates = set(qml_provider_candidates.get(module, set()))
        candidates.discard(source_id)
        if len(candidates) == 1:
            internal_qml.add(next(iter(candidates)))
        elif len(candidates) > 1:
            ambiguous_qml[module] = sorted(candidates)
            ambiguous_provider_refs += 1
        elif module not in raw["provided_qml_modules"]:
            external_qml.add(module)

    internal.update(internal_qml)
    internal_edge_count += len(internal)
    internal_qml_edge_count += len(internal_qml)

    nodes[source_id] = {
        **raw,
        "internal_candidate_dependencies": sorted(internal),
        "internal_qml_candidate_dependencies": sorted(internal_qml),
        "external_requirements": sorted(external),
        "external_qml_modules": sorted(external_qml),
        "self_package_requirements": sorted(self_requirements),
        "ambiguous_internal_requirements": ambiguous,
        "ambiguous_qml_requirements": ambiguous_qml,
    }

provider_index = {
    "cmake": {
        key: sorted(value)
        for key, value in sorted(cmake_provider_candidates.items())
    },
    "qml": {
        key: sorted(value)
        for key, value in sorted(qml_provider_candidates.items())
    },
}

result = {
    "schema": 1,
    "node": "plasma-dependency-discovery",
    "parser_revision": 2,
    "state": "PASS" if not errors and verified == len(sources) else "FAIL",
    "run_kind": "planning-source-dependency-discovery",
    "authoritative": False,
    "package_execution_started": False,
    "consumes_package_attempt": False,
    "canonical_package_state_effect": "none",
    "plasma_version": manifest["release"]["version"],
    "source_count": len(sources),
    "source_sha256_verified": verified,
    "cmake_provider_names": sum(len(v["provided_cmake_packages"]) for v in nodes.values() if isinstance(v, dict) and "provided_cmake_packages" in v),
    "qml_provider_modules": sum(len(v["provided_qml_modules"]) for v in nodes.values() if isinstance(v, dict) and "provided_qml_modules" in v),
    "internal_candidate_edge_count": internal_edge_count,
    "internal_qml_edge_count": internal_qml_edge_count,
    "ambiguous_provider_references": ambiguous_provider_refs,
    "dependency_edge_status": "candidate-review-required",
    "signature_verification": manifest["release"]["source_signature_verification"],
    "errors": errors,
}

(OUT / "dependencies.json").write_text(json.dumps({
    "schema": 1,
    "plasma_version": manifest["release"]["version"],
    "authority": "kde-upstream-source-metadata",
    "candidate_only": True,
    "parser_revision": 2,
    "provider_index": provider_index,
    "nodes": nodes,
}, indent=2) + "\n")
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")

print(json.dumps(result, indent=2))
sys.exit(0 if result["state"] == "PASS" else 1)
