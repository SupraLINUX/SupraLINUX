#!/usr/bin/env python3
"""Plan Debian versions from verified sources; never execute a package build."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def compare(left, operation, right):
    result = subprocess.run(["dpkg", "--compare-versions", left, operation, right])
    if result.returncode not in {0, 1}:
        raise ValueError("invalid Debian version comparison")
    return result.returncode == 0


def candidate_version(upstream, reference, available):
    epoch, separator, body = reference.partition(":")
    if not separator:
        epoch, body = "", reference
    prefix = epoch + ":" if epoch else ""
    candidate = prefix + upstream + "-0supralinux1"
    references = set(available) | {reference}
    for version in references:
        if compare(candidate, "gt", version):
            continue
        ref_epoch, separator, ref_body = version.partition(":")
        if not separator:
            ref_epoch, ref_body = "", version
        ref_upstream = ref_body.rsplit("-", 1)[0]
        if ref_epoch != epoch or ref_upstream != upstream:
            raise ValueError(f"selected upstream {upstream} cannot supersede Ubuntu {version} without a transition review")
        proposed = version + "+supralinux1"
        if compare(proposed, "gt", candidate):
            candidate = proposed
    if not all(compare(candidate, "gt", version) for version in references):
        raise ValueError("candidate does not supersede all captured Ubuntu references")
    subprocess.run(["dpkg", "--validate-version", candidate], check=True)
    return candidate


def assign(level, result, result_sha256):
    selected = level["selected_nodes"]
    records = result["nodes"]
    by_node = {node["node"]: node for node in records}
    if (result.get("state") != "PASS" or len(by_node) != len(records)
            or set(by_node) != set(selected) or not selected):
        raise ValueError("materialization must contain exactly the selected PASS nodes")
    items = []
    for name in selected:
        node, record = level["nodes"][name], by_node[name]
        source, reference = record["upstream"], record["ubuntu_reference"]
        if (record["state"] != "PASS" or source["sha256"] != node["upstream_source_sha256"]
                or source["version"] != node["upstream_version"]
                or source.get("signature_verification") != "PASS"
                or reference["source_package"] != node["packaging_reference"]["source_package"]):
            raise ValueError(f"{name}: source/reference evidence identity mismatch")
        version = candidate_version(source["version"], reference["source_version"], reference["apt_source_versions"])
        items.append({"node": name, "source_package": reference["source_package"],
                      "upstream_version": source["version"], "ubuntu_reference_version": reference["source_version"],
                      "captured_ubuntu_versions": reference["apt_source_versions"],
                      "candidate_package_version": version, "epoch_preserved": True,
                      "greater_than_all_captured_ubuntu_versions": True})
    return {"schema": 1, "state": "PASS", "run_kind": "candidate-version-assignment",
            "materialization_result_sha256": result_sha256, "selected_node_count": len(items), "nodes": items,
            "package_execution_started": False, "consumes_package_attempt": False,
            "canonical_package_state_effect": "none", "next_gate": "plasma-level0-packaging-preparation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level-manifest", type=Path, required=True)
    parser.add_argument("--materialization-result", type=Path, required=True)
    parser.add_argument("--result-sha256", required=True)
    args = parser.parse_args()
    payload = args.materialization_result.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != args.result_sha256:
        parser.error("materialization result digest mismatch")
    plan = assign(json.loads(args.level_manifest.read_text()), json.loads(payload), digest)
    print(json.dumps(plan, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
