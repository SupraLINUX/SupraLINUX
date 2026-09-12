#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "desktop-stack.json"
WORKFLOWS = ROOT / ".github" / "workflows"
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read_required(path: Path) -> str:
    if not path.exists():
        errors.append(f"required file missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(data.get("schema") == 1, "manifest schema must be 1")
platform = data.get("platform", {})
require(platform.get("authority") == "ubuntu", "platform authority must be ubuntu")
require(platform.get("version") == "26.04 LTS", "platform version must be Ubuntu 26.04 LTS")
require(platform.get("series") == "resolute", "Ubuntu 26.04 series must be resolute")

desktop = data.get("desktop", {})
require(desktop.get("authority") == "kde-upstream", "desktop authority must be kde-upstream")
for component in ("plasma", "frameworks", "gear"):
    item = desktop.get(component, {})
    require(bool(item.get("version")), f"{component} version is required")
    require(str(item.get("evidence", "")).startswith("https://kde.org/"), f"{component} must cite KDE evidence")

qt = data.get("qt", {})
require(qt.get("requirement_authority") == "kde-upstream", "Qt requirement authority must be kde-upstream")
require(qt.get("source_authority") == "qt-project", "Qt source authority must be qt-project")
require(bool(qt.get("required_series")), "Qt required_series is required")
provider = qt.get("provider", {})
require(provider.get("name") in {"ubuntu", "supralinux"}, "Qt provider must be ubuntu or supralinux")
if provider.get("name") == "ubuntu":
    require(provider.get("series") == "resolute", "Ubuntu Qt provider must use resolute")
cert = qt.get("certification", {})
require(cert.get("status") in {"pending", "certified", "rejected"}, "Qt certification status is invalid")
if cert.get("status") == "certified":
    require(bool(cert.get("evidence")), "certified Qt requires evidence")

ci = data.get("ci", {})
hosted = ci.get("hosted_runner", {})
require(hosted.get("label") == "ubuntu-26.04", "hosted runner must be explicitly ubuntu-26.04")
require(hosted.get("role") == "non-authoritative-preflight", "hosted runner must be non-authoritative preflight")
authoritative = ci.get("authoritative_runner", {})
require(authoritative.get("platform") == "ubuntu-26.04", "authoritative runner platform must be ubuntu-26.04")
require(authoritative.get("virtualization") == "kvm", "authoritative runner virtualization must be kvm")
require(authoritative.get("lifecycle") == "ephemeral-vm", "authoritative runner must use ephemeral VMs")
require(authoritative.get("build_isolation") == "sbuild-unshare", "authoritative package build must use sbuild-unshare")
require(authoritative.get("system_test") == "autopkgtest-qemu", "authoritative package system test must use autopkgtest-qemu")
require(authoritative.get("nested_kvm_required") is True, "authoritative package testing requires nested KVM")

workflow_texts: dict[str, str] = {}
for path in sorted(WORKFLOWS.glob("*.y*ml")):
    text = path.read_text(encoding="utf-8")
    workflow_texts[path.name] = text
    require("ubuntu-latest" not in text, f"{path.relative_to(ROOT)} must not use ubuntu-latest")
    require("pull_request_target" not in text, f"{path.relative_to(ROOT)} must not use pull_request_target")

repository_policy = workflow_texts.get("repository-policy.yml", "")
runner_contract = workflow_texts.get("runner-contract.yml", "")
authoritative_workflow = workflow_texts.get("authoritative-package-proof.yml", "")
hosted_proof = workflow_texts.get("package-build-proof.yml", "")
require("bash -n scripts/*.sh" in repository_policy, "repository policy must syntax-check all shell scripts")

for filename, text, gate_label in (
    ("runner-contract.yml", runner_contract, "ci:runner-contract"),
    ("authoritative-package-proof.yml", authoritative_workflow, "ci:authoritative-package-proof"),
):
    require(bool(text), f"missing authoritative workflow: .github/workflows/{filename}")
    require("types: [labeled]" in text, f"{filename} must use a PR labeled trigger")
    require(gate_label in text, f"{filename} must require controlled label {gate_label}")
    require("github.event.pull_request.head.repo.full_name == github.repository" in text, f"{filename} must refuse fork PRs")
    for label in ("self-hosted", "linux", "x64", "supralinux", "ubuntu-26.04", "kvm", "ephemeral"):
        require(label in text, f"{filename} must target authoritative runner label {label}")

require("scripts/check-nested-kvm-runtime.sh" in runner_contract, "runner contract must execute a real nested-KVM runtime probe")
require("types: [opened, synchronize, reopened]" in hosted_proof, "hosted package preflight must declare explicit PR lifecycle events")
require("github.event.before" in hosted_proof and "github.event.after" in hosted_proof, "hosted preflight must compare synchronize before/after SHAs")
require("scripts/package-preflight-needed.sh" in hosted_proof, "hosted preflight must gate expensive builds on event delta")
require("fetch-depth: 0" in hosted_proof, "hosted preflight must fetch comparison history")

required_files = [
    "docs/architecture/overview.md",
    "docs/architecture/build-ci.md",
    "docs/status/2026-09-11.md",
    "docs/decisions/ADR-0001-authority-provider.md",
    "docs/runners/ubuntu-26.04.md",
    "docs/runners/provisioning.md",
    "docs/runners/host-kvm.md",
    "scripts/check-kvm-host.sh",
    "scripts/check-nested-kvm-runtime.sh",
    "scripts/provision-kvm-host.sh",
    "scripts/package-preflight-needed.sh",
    "scripts/fetch-ubuntu-26.04-cloud-image.sh",
    "scripts/build-authoritative-runner-image.sh",
    "scripts/install-actions-runner.sh",
    "scripts/provision-authoritative-runner-guest.sh",
    "scripts/prepare-autopkgtest-qemu-image.sh",
    "scripts/seal-authoritative-runner-image.sh",
    "scripts/qemu-kvm-required.sh",
    "scripts/run-kvm-jit-gate.sh",
    "scripts/run-authoritative-package-proof.sh",
]
for relative in required_files:
    require((ROOT / relative).exists(), f"required architecture/runner file missing: {relative}")

package_delta = read_required(ROOT / "scripts/package-preflight-needed.sh")
for tracked in ("packages/supralinux-build-test/*", "scripts/run-package-build-proof.sh", ".github/workflows/package-build-proof.yml"):
    require(tracked in package_delta, f"package preflight delta detector must track {tracked}")

host_provisioner = read_required(ROOT / "scripts/provision-kvm-host.sh")
for package in ("libvirt-daemon-system", "qemu-system-x86", "virt-install", "libguestfs-tools"):
    require(package in host_provisioner, f"host provisioning must install {package}")
require("does NOT change BIOS" in host_provisioner, "host provisioning must explicitly avoid automatic BIOS/KVM-module changes")
require("/var/lib/supralinux/golden-builds" in host_provisioner, "host provisioning must create golden-build state")

host_checker = read_required(ROOT / "scripts/check-kvm-host.sh")
for token in ("/dev/kvm", "parameters/nested", "qemu:///system", "virt-sysprep", "virt-cat", "virt-copy-out", "flock"):
    require(token in host_checker, f"host preflight missing required check: {token}")

nested_probe = read_required(ROOT / "scripts/check-nested-kvm-runtime.sh")
require("-accel kvm" in nested_probe, "nested KVM runtime probe must force KVM")
require("-cpu host" in nested_probe, "nested KVM runtime probe must exercise host CPU")
require("probe_exit_code" in nested_probe and "nested_kvm_runtime=PASS" in nested_probe, "nested KVM probe must retain explicit result evidence")

cloud_fetcher = read_required(ROOT / "scripts/fetch-ubuntu-26.04-cloud-image.sh")
require("SHA256SUMS.gpg" in cloud_fetcher and "gpgv" in cloud_fetcher, "Ubuntu source image must use signed checksum verification")
require("/var/lib/supralinux/images/source/resolute" in cloud_fetcher, "Ubuntu source image must default to stable host storage")

golden_builder = read_required(ROOT / "scripts/build-authoritative-runner-image.sh")
for token, message in (
    ("scripts/check-kvm-host.sh", "golden builder must require host preflight"),
    (".provenance.txt", "golden builder must require source provenance"),
    ("--cpu host-passthrough", "golden builder must expose host CPU virtualization"),
    ("scripts/provision-authoritative-runner-guest.sh", "golden builder must provision guest"),
    ("scripts/prepare-autopkgtest-qemu-image.sh", "golden builder must prepare nested test image"),
    ("scripts/seal-authoritative-runner-image.sh", "golden builder must seal guest state"),
    ("virt-sysprep", "golden builder must perform offline clone cleanup"),
    ("qemu-img convert", "golden builder must flatten overlay"),
    ("qemu-img check", "golden builder must validate final qcow2"),
    ("SUPRALINUX_REPLACE_GOLDEN_IMAGE", "golden replacement must require opt-in"),
    ("source_checkout_removed=yes", "golden builder must prove temporary checkout removal"),
):
    require(token in golden_builder, message)
require("machine-id" in golden_builder and "ssh-hostkeys" in golden_builder, "golden builder must reset machine/SSH identity")

installer = read_required(ROOT / "scripts/install-actions-runner.sh")
require(".digest" in installer and "sha256sum --check --strict" in installer, "Actions runner archive must use GitHub-published SHA-256 verification")

host_orchestrator = read_required(ROOT / "scripts/run-kvm-jit-gate.sh")
for token, message in (
    ("generate-jitconfig", "host orchestrator must use GitHub JIT config"),
    ("/run/supralinux-jit-config", "JIT config must live in guest tmpfs"),
    ("Authoritative self-hosted gates refuse fork PRs", "host orchestrator must refuse fork PRs"),
    ("flock -n", "host orchestrator must serialize local authoritative jobs"),
    ("workflow-baseline-ids.json", "host orchestrator must snapshot run IDs before trigger"),
    ("head_sha=${PR_HEAD_SHA}", "host orchestrator must query exact PR head SHA"),
    ("actions/runs/${WORKFLOW_RUN_ID}", "host orchestrator must bind exact workflow run ID"),
    ("guest-exec-status", "host orchestrator must detect premature runner exit"),
    ("PROVENANCE_SHA256", "host orchestrator must verify golden SHA against provenance"),
    ("source_checkout_removed=yes", "host orchestrator must require source-clean golden provenance"),
    ("su --login --shell /bin/bash --command", "guest runner must start non-root with explicit login shell"),
):
    require(token in host_orchestrator, message)

authoritative_proof = read_required(ROOT / "scripts/run-authoritative-package-proof.sh")
require("scripts/check-nested-kvm-runtime.sh" in authoritative_proof, "authoritative proof must run nested-KVM runtime probe")
require("--qemu-command=\"${KVM_QEMU_WRAPPER}\"" in authoritative_proof, "authoritative autopkgtest must use the KVM-required QEMU wrapper")
require("--qemu-architecture=x86_64" in authoritative_proof, "authoritative autopkgtest must pin QEMU architecture")
require("qemu-kvm-wrapper-sha256.txt" in authoritative_proof, "authoritative evidence must hash the QEMU wrapper")
require('"system_test_acceleration": "kvm-required"' in authoritative_proof, "authoritative result must record KVM-required acceleration")

qemu_wrapper = read_required(ROOT / "scripts/qemu-kvm-required.sh")
require('exec "${QEMU}" -accel kvm "$@"' in qemu_wrapper, "QEMU wrapper must select KVM only")
require("tcg" not in qemu_wrapper.lower(), "KVM-required QEMU wrapper must not contain a TCG fallback")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository policy validation: PASS")
print(f"Platform: {platform['version']} ({platform['series']})")
print("Desktop: Plasma {plasma}, Frameworks {frameworks}, Gear {gear}".format(
    plasma=desktop["plasma"]["version"], frameworks=desktop["frameworks"]["version"], gear=desktop["gear"]["version"]))
print(f"Qt: required {qt['required_series']}, provider={provider['name']}, candidate={provider.get('candidate_version', 'n/a')}, certification={cert['status']}")
print("CI: hosted={hosted}; authoritative={platform}/{virt}/{lifecycle}; build={build}; test={test}; KVM-runtime=required; deterministic-qemu-wrapper=required; JIT=required; exact-run-binding=required; shell-syntax=required".format(
    hosted=hosted["role"], platform=authoritative["platform"], virt=authoritative["virtualization"], lifecycle=authoritative["lifecycle"], build=authoritative["build_isolation"], test=authoritative["system_test"]))
