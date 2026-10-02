#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_SHA = "a6b2d066ced63231dd3de6adb6248dbbd7eba01cf0d776d49c6d2b091c0f82ef"
EXPECTED_CATEGORIES = {
    "dynamic-cmake": 4,
    "kf6-namespace": 38,
    "legacy-qt5-kf5": 11,
    "other-cmake": 117,
    "qt6-namespace": 22,
}

if len(sys.argv) != 2:
    raise SystemExit("usage: run-kde-plasma-provider-audit.py <dependencies.json>")

src = Path(sys.argv[1])
raw = src.read_bytes()
actual_sha = hashlib.sha256(raw).hexdigest()
if actual_sha != EXPECTED_SHA:
    raise SystemExit(f"dependency snapshot SHA-256 mismatch: {actual_sha}")

data = json.loads(raw)
if data.get("parser_revision") != 4:
    raise SystemExit("unexpected Plasma dependency parser revision")
nodes = data.get("nodes", {})
if len(nodes) != 75:
    raise SystemExit(f"unexpected Plasma node count: {len(nodes)}")

cmake = sorted({x for node in nodes.values() for x in node.get("external_requirements", [])})
qml = sorted({x for node in nodes.values() for x in node.get("external_qml_modules", [])})
pkg = sorted({x for node in nodes.values() for x in node.get("pkg_config_modules", [])})

def cmake_category(req):
    if "${" in req:
        return "dynamic-cmake"
    if req == "ECM" or req.startswith("KF6"):
        return "kf6-namespace"
    if req.startswith("Qt6") or req == "QtWaylandScanner":
        return "qt6-namespace"
    if req.startswith("KF5") or req.startswith("Qt5"):
        return "legacy-qt5-kf5"
    return "other-cmake"

groups = {}
for req in cmake:
    groups.setdefault(cmake_category(req), []).append(req)
counts = {name: len(values) for name, values in sorted(groups.items())}

if len(cmake) != 192:
    raise SystemExit(f"unexpected unique CMake requirement count: {len(cmake)}")
if len(qml) != 24:
    raise SystemExit(f"unexpected unique QML requirement count: {len(qml)}")
if len(pkg) != 62:
    raise SystemExit(f"unexpected unique pkg-config requirement count: {len(pkg)}")
if counts != EXPECTED_CATEGORIES:
    raise SystemExit(f"unexpected CMake category counts: {counts}")

out = Path("evidence/kde-plasma-provider-audit")
out.mkdir(parents=True, exist_ok=True)

inventory = {
    "schema": 1,
    "plasma_version": "6.7.5",
    "source_dependencies_sha256": actual_sha,
    "classification": "syntactic-provider-inventory-only",
    "provider_resolution_status": "review-required",
    "cmake_requirements": cmake,
    "cmake_categories": groups,
    "qml_requirements": qml,
    "pkg_config_requirements": pkg,
    "counts": {
        "cmake": len(cmake),
        "qml": len(qml),
        "pkg_config": len(pkg),
        "cmake_categories": counts,
    },
    "dynamic_cmake_references": groups.get("dynamic-cmake", []),
    "legacy_qt5_kf5_references": groups.get("legacy-qt5-kf5", []),
}
(out / "provider-inventory.json").write_text(
    json.dumps(inventory, indent=2, sort_keys=True) + "\n"
)

result = {
    "schema": 1,
    "node": "plasma-provider-inventory-audit",
    "state": "PASS",
    "run_kind": "planning-provider-inventory-audit",
    "authoritative": False,
    "package_execution_started": False,
    "consumes_package_attempt": False,
    "canonical_package_state_effect": "none",
    "plasma_version": "6.7.5",
    "dependencies_json_sha256": actual_sha,
    "unique_cmake_requirements": len(cmake),
    "unique_qml_requirements": len(qml),
    "unique_pkg_config_requirements": len(pkg),
    "cmake_category_counts": counts,
    "dynamic_cmake_references": len(groups.get("dynamic-cmake", [])),
    "legacy_qt5_kf5_references": len(groups.get("legacy-qt5-kf5", [])),
    "provider_resolution_status": "review-required",
    "next_gate": "plasma-provider-resolution",
}
(out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2))
