#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"
WORKFLOW = ROOT / ".github/workflows/host-authoritative-control.yml"
REQUEST = ROOT / "ops/host-authoritative/request.json"

broker = BROKER.read_text()
workflow = WORKFLOW.read_text()
request = json.loads(REQUEST.read_text())

required_broker = [
    'os.environ.get("SUDO_USER") != RUNNER_USER',
    '"mode", "gate", "runner_group_id", "cancel_run_id"',
    '"cancel_run_head_sha"',
    'request.get("mode") not in {"diagnose", "repair-host", "preflight", "rebuild-golden", "execute"}',
    'request.get("gate") != "plasma-package-build"',
    'request["mode"] in {"diagnose", "repair-host", "rebuild-golden", "execute"} and (',
    'run.get("status") == "queued"',
    'job.get("status") != "queued"',
    'make_demote(extra_groups=())',
    'privileged_groups = tuple(sorted({libvirt_group, kvm_group}))',
    '"persistent_group_membership_changed=no"',
    '"privilege_scope=child-process-only"',
    'if request["mode"] == "diagnose":',
    '"root-kvm-open"',
    '"operator-kvm-open-normal"',
    '"operator-kvm-open-scoped-groups"',
    '"runner-service-security"',
    '"operator-check-kvm-host"',
    '"operator-check-kvm-network-userspace"',
    '"host-default-routes"',
    '"host-{device}-features"',
    '"host-uptime-since"',
    '"libguestfs-runtime-dir"',
    '"libguestfs-runtime-cache"',
    '"libguestfs-runtime-provenance"',
    '"libguestfs-source-kernel-stat"',
    '"libguestfs-runtime-kernel-sha256"',
    '"libguestfs-modules-dep-sha256"',
    '"github_token_requested=no"',
    '"jit_invoked=no"',
    '"package_attempt_effect=none"',
    '/actions/runs/{cancel_run_id}/cancel',
    '/labels/ci%3Aplasma-package-build',
    'package_build_label_present = any(',
    'label.get("name") == "ci:plasma-package-build"',
    'if package_build_label_present:',
    'refs/pull/{PR_NUMBER}/head',
    '"status", "--porcelain", "--untracked-files=normal"',
    '["scripts/check-kvm-host.sh"]',
    '["scripts/with-libguestfs-runtime.sh", "true"]',
    '"scripts/check-golden-image-provenance.sh"',
    '["scripts/run-kvm-jit-gate.sh", request["gate"]]',
    '"SUPRALINUX_GITHUB_TOKEN": token',
    '"package_attempt_effect=none-before-execute"',
    'if request["mode"] == "rebuild-golden":',
    '"SUPRALINUX_REPLACE_GOLDEN_IMAGE": "1"',
    '["scripts/build-authoritative-runner-image.sh"]',
    '"HOST_AUTHORITATIVE_GOLDEN_REBUILD=PASS"',
    '"golden-rebuild-admission.txt"',
    '"package_attempt_effect=none"',
    'KVM_RUNTIME_PROBE = r"""',
    '"kvm-runtime-admission.json"',
    'kvm_runtime_result.get("open_ok") is True',
    'kvm_runtime_result.get("kvm_api_version") == 12',
    'if request["mode"] == "repair-host":',
    '"/usr/local/libexec/supralinux-restore-kvm-host-network-safety"',
    '"HOST_NETWORK_SAFETY_REPAIR=PASS"',
    '"github_token_requested=no"',
    '"github_api_mutation=no"',
]
for token in required_broker:
    if token not in broker:
        raise SystemExit(f"missing authoritative host broker contract: {token}")

for forbidden in (
    "eval(",
    "shell=True",
    'request["script"]',
    "chmod 0777",
    'run_as_operator(["test", "-r", "/dev/kvm"]',
    'run_as_operator(["test", "-w", "/dev/kvm"]',
):
    if forbidden in broker:
        raise SystemExit(f"forbidden authoritative host broker construct: {forbidden}")

required_workflow = [
    "workflow_call:",
    "supralinux-host-orchestrator",
    "Checkout exact PR head",
    "Refresh authoritative host broker",
    "Validate authoritative control request",
    "Execute fixed authoritative host control",
    "/usr/local/libexec/supralinux-authoritative-host-broker",
    "Upload authoritative control result",
]
for token in required_workflow:
    if token not in workflow:
        raise SystemExit(f"missing authoritative host workflow contract: {token}")

expected_request = {
    "schema": 1,
    "mode": "rebuild-golden",
    "gate": "plasma-package-build",
    "runner_group_id": 3,
}
if request != expected_request:
    raise SystemExit(f"unexpected initial authoritative host request: {request!r}")

print("Host authoritative control contract: PASS")
