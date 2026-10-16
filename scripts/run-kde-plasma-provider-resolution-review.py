#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2:
    raise SystemExit("usage: run-kde-plasma-provider-resolution-review.py <provider-resolution-evidence-dir>")

artifact_dir = Path(sys.argv[1])
definition_path = ROOT / "manifests/kde-plasma-provider-resolution-review.json"
definition_raw = definition_path.read_bytes()
definition = json.loads(definition_raw)
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

expected_files = definition["input"]["files"]
loaded = {}
for name, expected_sha in expected_files.items():
    path = artifact_dir / name
    req(path.is_file(), f"missing provider-resolution evidence file: {name}")
    if not path.is_file():
        continue
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    req(actual_sha == expected_sha, f"{name}: SHA-256 mismatch: {actual_sha}")
    loaded[name] = json.loads(path.read_text())

required = set(expected_files)
req(set(loaded) == required, "provider-resolution evidence file set")

if set(loaded) == required:
    result = loaded["result.json"]
    providers = loaded["ubuntu-build-dep-providers.json"]
    qml = loaded["qml-resolution.json"]
    cmake = loaded["cmake-resolution.json"]
    nodes = loaded["node-resolution.json"]

    req(result.get("state") == "PASS", "provider resolution must be PASS")
    req(result.get("run_kind") == "planning-provider-resolution", "provider resolution run kind")
    req(result.get("authoritative") is False, "provider resolution must remain non-authoritative")
    req(result.get("package_execution_started") is False, "provider resolution package execution boundary")
    req(result.get("consumes_package_attempt") is False, "provider resolution package Attempt boundary")
    req(result.get("canonical_package_state_effect") == "none", "provider resolution canonical package effect")
    req(result.get("review_required") is True, "provider resolution must require this review")

    expected = definition["expected_sets"]
    missing_sources = {name for name, data in providers["per_source"].items() if not data["ubuntu_source_reference_available"]}
    missing_build_deps = {name for name, candidate in providers["package_candidates"].items() if candidate is None}
    pending_qml = {name for name, data in qml.items() if data.get("provider") is None}
    legacy = {name for name, data in cmake.items() if data.get("decision") == "legacy-reference-review"}
    dynamic = {name for name, data in cmake.items() if data.get("decision") == "dynamic-source-context-review"}
    kde_extra = {name for name, data in cmake.items() if data.get("decision") == "kde-extra-review"}
    source_reference = {name for name, data in cmake.items() if data.get("decision") == "source-build-dep-reference"}

    req(missing_sources == set(expected["missing_ubuntu_source_references"]), "five missing Ubuntu source references changed")
    req(missing_build_deps == set(expected["missing_build_dep_candidates"]), "seven special Build-Depends changed")
    req(pending_qml == set(expected["pending_qml_modules"]), "pending QML review set changed")
    req(legacy == set(expected["legacy_cmake_references"]), "legacy CMake review set changed")
    req(dynamic == set(expected["dynamic_cmake_references"]), "dynamic CMake review set changed")
    req(kde_extra == set(expected["kde_extra_cmake_references"]), "KDE-extra CMake review set changed")
    req(len(source_reference) == definition["cmake_source_reference_policy"]["expected_review_count"] == 117, "CMake source-reference review cardinality")

    source_decisions = definition["source_reference_decisions"]
    build_dep_decisions = definition["missing_build_dep_decisions"]
    qml_decisions = definition["qml_provider_decisions"]
    req(set(source_decisions) == missing_sources, "source-reference decision coverage")
    req(set(build_dep_decisions) == missing_build_deps, "special Build-Depends decision coverage")
    req(set(qml_decisions) == pending_qml, "QML provider decision coverage")
    req(all(v.get("status") == "resolved" for v in source_decisions.values()), "source-reference decisions must be resolved")
    req(all(v.get("status") == "resolved" and v.get("provider") for v in build_dep_decisions.values()), "Build-Depends decisions must name providers")
    req(all(v.get("status") == "resolved" and v.get("provider") for v in qml_decisions.values()), "QML decisions must name providers")

    uncovered = []
    for requirement in sorted(source_reference):
        referencing_nodes = [
            node_id for node_id, node in nodes.items()
            if requirement in node.get("cmake_requirements", [])
        ]
        if not referencing_nodes:
            uncovered.append(f"{requirement}: no referring Plasma node")
            continue
        for node_id in referencing_nodes:
            source = nodes[node_id]["ubuntu_source_reference"]
            if not source.get("ubuntu_source_reference_available") and node_id not in source_decisions:
                uncovered.append(f"{requirement}: {node_id} lacks source context")
    req(not uncovered, "CMake source-reference context coverage: " + "; ".join(uncovered[:8]))

    actual_legacy_nodes = {
        node_id for node_id, node in nodes.items()
        if any(req_name in legacy for req_name in node.get("cmake_requirements", []))
    }
    req(actual_legacy_nodes == set(definition["legacy_compatibility"]["nodes"]), "legacy compatibility node set")
    req(definition["legacy_compatibility"].get("status") == "resolved", "legacy compatibility decision")
    req(set(definition["legacy_compatibility"].get("references", [])) == legacy, "legacy compatibility reference coverage")

    req(set(definition["dynamic_cmake_decisions"]) == dynamic, "dynamic CMake decision coverage")
    req(all(v.get("status") == "resolved" for v in definition["dynamic_cmake_decisions"].values()), "dynamic CMake decisions")
    req(set(definition["kde_extra_cmake_decisions"]) == kde_extra, "KDE-extra CMake decision coverage")
    req(all(v.get("status") == "resolved" and v.get("provider") for v in definition["kde_extra_cmake_decisions"].values()), "KDE-extra CMake decisions")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

out = ROOT / "evidence/kde-plasma-provider-resolution-review"
out.mkdir(parents=True, exist_ok=True)
snapshot = {
    "schema": 1,
    "plasma_version": definition["plasma_version"],
    "provider_resolution_evidence": definition["input"],
    "source_reference_decisions": definition["source_reference_decisions"],
    "missing_build_dep_decisions": definition["missing_build_dep_decisions"],
    "qml_provider_decisions": definition["qml_provider_decisions"],
    "cmake_source_reference_policy": definition["cmake_source_reference_policy"],
    "legacy_compatibility": definition["legacy_compatibility"],
    "dynamic_cmake_decisions": definition["dynamic_cmake_decisions"],
    "kde_extra_cmake_decisions": definition["kde_extra_cmake_decisions"],
}
(out / "review.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
result_out = {
    "schema": 1,
    "node": "plasma-provider-resolution-review",
    "state": "PASS",
    "run_kind": "planning-provider-resolution-review",
    "authoritative": False,
    "package_execution_started": False,
    "consumes_package_attempt": False,
    "canonical_package_state_effect": "none",
    "plasma_version": "6.7.5",
    "source_reference_reviews": 5,
    "source_reference_resolved": 5,
    "missing_build_dep_reviews": 7,
    "missing_build_dep_resolved": 7,
    "qml_reviews": 12,
    "qml_resolved": 12,
    "cmake_source_reference_reviews": 117,
    "cmake_source_reference_resolved": 117,
    "legacy_cmake_reviews": 11,
    "legacy_cmake_resolved": 11,
    "dynamic_cmake_reviews": 1,
    "dynamic_cmake_resolved": 1,
    "kde_extra_cmake_reviews": 1,
    "kde_extra_cmake_resolved": 1,
    "review_required": False,
    "next_gate": "plasma-dag-executable-promotion",
    "definition_sha256": hashlib.sha256(definition_raw).hexdigest(),
}
(out / "result.json").write_text(json.dumps(result_out, indent=2, sort_keys=True) + "\n")
print(json.dumps(result_out, indent=2))
