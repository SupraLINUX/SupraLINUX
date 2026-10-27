#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "scripts/autopkgtest-backend-policy.py"
CERTIFIER = ROOT / "scripts/certify-autopkgtest-unshare-backend.sh"
RUNNER_WORKFLOW = ROOT / ".github/workflows/runner-contract.yml"
MANIFEST = ROOT / "manifests/autopkgtest-backend-certification.json"

spec = importlib.util.spec_from_file_location("autopkgtest_backend_policy", POLICY)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    normal = root / "normal.control"
    normal.write_text(
        "Tests: payload\n"
        "Depends: @, python3\n"
        "Restrictions: needs-root, allow-stderr\n"
    )
    result = module.classify(normal)
    assert result["backend"] == "unshare"
    assert not result["qemu_required_restrictions"]
    assert not result["unknown_restrictions"]

    machine = root / "machine.control"
    machine.write_text(
        "Tests: reboot\n"
        "Depends: @\n"
        "Restrictions: isolation-machine\n"
    )
    result = module.classify(machine)
    assert result["backend"] == "qemu"
    assert result["qemu_required_restrictions"] == ["isolation-machine"]

    unknown = root / "unknown.control"
    unknown.write_text(
        "Tests: future\n"
        "Depends: @\n"
        "Restrictions: future-restriction\n"
    )
    result = module.classify(unknown)
    assert result["backend"] == "qemu"
    assert result["unknown_restrictions"] == ["future-restriction"]

controls = sorted(ROOT.glob("packages/plasma/*/debian/tests/control"))
assert len(controls) >= 27, "expected the reviewed Plasma autopkgtest corpus"
unshare_candidates = 0
for control in controls:
    result = module.classify(control)
    assert result["state"] == "PASS"
    assert not result["unknown_restrictions"], f"unknown restriction in {control}"
    if result["backend"] == "unshare":
        unshare_candidates += 1
assert unshare_candidates >= 27, "reviewed Plasma corpus unexpectedly lost unshare eligibility"

certifier = CERTIFIER.read_text()
for token in (
    'run_backend qemu',
    'run_backend unshare',
    'unshare --arch amd64 --tarball',
    '"normalized_results_equal": True',
    '"package_attempt_consumed": False',
    '"sbuild_invoked": False',
    '"production_backend_changed": False',
    'one-real-package-canary-before-default-rollout',
):
    assert token in certifier, f"missing certification contract: {token}"
for forbidden in (
    "run-authoritative-plasma-package.sh",
    "sbuild --",
    "execute-and-publish-pass",
):
    assert forbidden not in certifier, f"certifier crosses package boundary: {forbidden}"

workflow = RUNNER_WORKFLOW.read_text()
for token in (
    "autopkgtest-virt-unshare",
    "scripts/certify-autopkgtest-unshare-backend.sh",
    "Certify autopkgtest unshare backend equivalence",
):
    assert token in workflow, f"runner contract misses certification hook: {token}"

manifest = json.loads(MANIFEST.read_text())
assert manifest["state"] == "pending"
assert manifest["current_backend"] == "autopkgtest-qemu"
assert manifest["candidate_backend"] == "autopkgtest-unshare"
assert manifest["package_attempt_effect"] == "none"
assert manifest["rollout"]["production_default_changed"] is False
assert manifest["rollout"]["next_step"] == "authoritative-a-b-certification"

print(
    "Autopkgtest backend certification policy: PASS; "
    f"reviewed_controls={len(controls)} unshare_candidates={unshare_candidates}"
)
