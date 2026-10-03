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
req(cp.get("state") in {"build-required", "PASS"}, "Frameworks milestone state")
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

passes = [n for n in dag.get("nodes", {}).values() if n.get("state") == "PASS"]
req(dag.get("frameworks_series") == "6.30.0", "Frameworks canonical series")
req(len(passes) == 65, "Frameworks canonical PASS count")

l0cp = level0.get("execution_checkpoint", {})
req(l0cp.get("checkpoint_id") == "frameworks-6.30-pass", "Level 0 checkpoint binding")
req(l0cp.get("required_before_package_execution") is True, "Level 0 checkpoint execution requirement")
req(l0cp.get("cache_only") is True, "Level 0 checkpoint cache-only role")
req(level0.get("package_execution_authorized") is False, "Level 0 package execution must remain locked")

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
print("frameworks-6.30-pass: build-required cache; 65 retained PASS artifacts")
print("Plasma Level 0 package execution remains locked until checkpoint admission")
