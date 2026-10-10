#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

data = json.loads((ROOT / "manifests/execution-checkpoints.json").read_text())
dag = json.loads((ROOT / "manifests/kde-dag.json").read_text())
level0 = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())

req(data.get("policy") == "milestone-images-are-execution-cache-not-source-of-truth", "checkpoint cache policy")
cp = data.get("checkpoints", {}).get("frameworks-6.30-pass", {})
req(cp.get("state") == "PASS", "Frameworks milestone state")
req(cp.get("kind") == "qcow2-execution-milestone-cache", "Frameworks milestone kind")
req(cp.get("framework_series") == "6.30.0", "Frameworks milestone series")
req(cp.get("expected_pass_nodes") == 65, "Frameworks milestone PASS-node count")
req(cp.get("source_golden_sha256") == "a0b88447d9a9ecd9785087390cf499abaf9416291864fe1be4d63d9a334b2acd", "Frameworks milestone golden source")
req(cp.get("payload", {}).get("prewarmed_sbuild_rootfs") is True, "Frameworks milestone prewarmed rootfs")
req(cp.get("payload", {}).get("retained_pass_artifact_pool") is True, "Frameworks milestone retained artifact pool")
req(cp.get("payload", {}).get("framework_packages_preinstalled_in_sbuild_rootfs") is False, "Frameworks milestone must not mask undeclared Build-Depends")
req(cp.get("safety", {}).get("cache_only") is True, "Frameworks milestone cache-only safety")
req(cp.get("safety", {}).get("package_truth_from_artifacts") is True, "Frameworks milestone artifact authority")
req(cp.get("safety", {}).get("failed_checkpoint_build_consumes_package_attempt") is False, "Frameworks milestone Attempt boundary")
req(cp.get("required_before", {}).get("plasma_level0_package_execution") is True, "Frameworks milestone Level 0 requirement")
req(cp.get("image_sha256") == "ec38f99e306d5a13333d6b247a9433b3526ec4a6d1a272631242c68df56c3e97", "Frameworks milestone admitted image hash")
evidence = cp.get("evidence", {})
req(evidence.get("result") == "PASS", "Frameworks milestone evidence result")
req(evidence.get("builder_commit") == "92defdaf79e573897e0e9836a9365aa3f2c7eb2d", "Frameworks milestone builder commit")
req(evidence.get("retained_framework_pass_artifacts") == 65, "Frameworks milestone retained artifact count")
req(evidence.get("apt_index_binary_entries") == 336, "Frameworks milestone APT entry count")
req(evidence.get("qemu_img_check") == "PASS", "Frameworks milestone qemu-img validation")
req(evidence.get("package_execution_started") is False, "Frameworks milestone package execution boundary")
req(evidence.get("consumes_package_attempt") is False, "Frameworks milestone package Attempt boundary")
req(evidence.get("canonical_package_state_effect") == "none", "Frameworks milestone package state effect")

passes = [n for n in dag.get("nodes", {}).values() if n.get("state") == "PASS"]
req(dag.get("frameworks_series") == "6.30.0", "Frameworks canonical series")
req(len(passes) == 65, "Frameworks canonical PASS count")

l0cp = level0.get("execution_checkpoint", {})
req(l0cp.get("checkpoint_id") == "frameworks-6.30-pass", "Level 0 checkpoint binding")
req(l0cp.get("required_before_package_execution") is True, "Level 0 checkpoint execution requirement")
req(l0cp.get("cache_only") is True, "Level 0 checkpoint cache-only role")
if level0.get("package_execution_authorized") is True:
    req(cp.get("state") == "PASS" and l0cp.get("state") == "PASS", "package execution requires admitted checkpoint evidence")
    req(l0cp.get("image_sha256") == cp.get("image_sha256"), "package execution checkpoint identity")
    req(bool(level0.get("authorized_package_nodes")), "package execution requires explicit node scope")

for path in (
    ROOT / "scripts/plan-frameworks-milestone.py",
    ROOT / "scripts/build-frameworks-milestone-image.sh",
    ROOT / "scripts/check-frameworks-milestone-image.sh",
):
    req(path.is_file(), f"checkpoint implementation missing: {path.name}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Execution checkpoint policy validation: PASS")
print("frameworks-6.30-pass: PASS cache; 65 retained PASS artifacts; 336 binary entries")
print("Plasma Level 0 package execution requires admitted checkpoint evidence and explicit node scope")
