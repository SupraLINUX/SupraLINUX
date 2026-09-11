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
if WORKFLOWS.exists():
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        workflow_texts[path.name] = text
        require("ubuntu-latest" not in text, f"{path.relative_to(ROOT)} must not use ubuntu-latest")
        require("pull_request_target" not in text, f"{path.relative_to(ROOT)} must not use pull_request_target")

runner_contract = workflow_texts.get("runner-contract.yml", "")
authoritative_proof = workflow_texts.get("authoritative-package-proof.yml", "")
hosted_proof = workflow_texts.get("package-build-proof.yml", "")
for filename, text, gate_label in (
    ("runner-contract.yml", runner_contract, "ci:runner-contract"),
    ("authoritative-package-proof.yml", authoritative_proof, "ci:authoritative-package-proof"),
):
    require(bool(text), f"missing authoritative workflow: .github/workflows/{filename}")
    require("types: [labeled]" in text, f"{filename} must use an explicit PR labeled trigger for pre-merge certification")
    require(gate_label in text, f"{filename} must require controlled label {gate_label}")
    require(
        "github.event.pull_request.head.repo.full_name == github.repository" in text,
        f"{filename} must refuse fork PRs on self-hosted runners",
    )
    for label in ("self-hosted", "linux", "x64", "supralinux", "ubuntu-26.04", "kvm", "ephemeral"):
        require(label in text, f"{filename} must target authoritative runner label {label}")

require("types: [opened, synchronize, reopened]" in hosted_proof, "hosted package preflight must declare explicit PR lifecycle events")
require("github.event.before" in hosted_proof, "hosted package preflight must use synchronize before SHA")
require("github.event.after" in hosted_proof, "hosted package preflight must use synchronize after SHA")
require("scripts/package-preflight-needed.sh" in hosted_proof, "hosted package preflight must gate expensive builds on event-delta changes")
require("fetch-depth: 0" in hosted_proof, "hosted package preflight must fetch comparison history")

required_files = [
    ROOT / "docs" / "architecture" / "overview.md",
    ROOT / "docs" / "architecture" / "build-ci.md",
    ROOT / "docs" / "status" / "2026-09-11.md",
    ROOT / "docs" / "decisions" / "ADR-0001-authority-provider.md",
    ROOT / "docs" / "runners" / "ubuntu-26.04.md",
    ROOT / "docs" / "runners" / "provisioning.md",
    ROOT / "docs" / "runners" / "host-kvm.md",
    ROOT / "scripts" / "check-kvm-host.sh",
    ROOT / "scripts" / "provision-kvm-host.sh",
    ROOT / "scripts" / "package-preflight-needed.sh",
    ROOT / "scripts" / "fetch-ubuntu-26.04-cloud-image.sh",
    ROOT / "scripts" / "build-authoritative-runner-image.sh",
    ROOT / "scripts" / "install-actions-runner.sh",
    ROOT / "scripts" / "provision-authoritative-runner-guest.sh",
    ROOT / "scripts" / "prepare-autopkgtest-qemu-image.sh",
    ROOT / "scripts" / "seal-authoritative-runner-image.sh",
    ROOT / "scripts" / "run-kvm-jit-gate.sh",
    ROOT / "scripts" / "run-authoritative-package-proof.sh",
]
for path in required_files:
    require(path.exists(), f"required architecture/runner file missing: {path.relative_to(ROOT)}")

package_delta = read_required(ROOT / "scripts" / "package-preflight-needed.sh")
for tracked in (
    "packages/supralinux-build-test/*",
    "scripts/run-package-build-proof.sh",
    ".github/workflows/package-build-proof.yml",
):
    require(tracked in package_delta, f"package preflight delta detector must track {tracked}")

host_provisioner = read_required(ROOT / "scripts" / "provision-kvm-host.sh")
for package in ("libvirt-daemon-system", "qemu-system-x86", "virt-install", "libguestfs-tools"):
    require(package in host_provisioner, f"host provisioning must install {package}")
require("does NOT change BIOS" in host_provisioner, "host provisioning must explicitly avoid automatic BIOS/KVM-module changes")

host_checker = read_required(ROOT / "scripts" / "check-kvm-host.sh")
require("/dev/kvm" in host_checker, "host preflight must validate /dev/kvm")
require("parameters/nested" in host_checker, "host preflight must validate nested KVM state")
require("qemu:///system" in host_checker, "host preflight must validate system libvirt connection")
for command in ("virt-sysprep", "virt-cat", "virt-copy-out"):
    require(command in host_checker, f"host preflight must validate {command}")

cloud_fetcher = read_required(ROOT / "scripts" / "fetch-ubuntu-26.04-cloud-image.sh")
require("SHA256SUMS.gpg" in cloud_fetcher, "Ubuntu cloud image fetcher must verify signed checksum metadata")
require("gpgv" in cloud_fetcher, "Ubuntu cloud image fetcher must perform signature verification")

golden_builder = read_required(ROOT / "scripts" / "build-authoritative-runner-image.sh")
require("scripts/check-kvm-host.sh" in golden_builder, "golden image builder must require host preflight")
require(".provenance.txt" in golden_builder, "golden image builder must require verified source-image provenance")
require("--cpu host-passthrough" in golden_builder, "golden image builder must expose host CPU virtualization capabilities")
require("scripts/provision-authoritative-runner-guest.sh" in golden_builder, "golden image builder must provision the runner guest")
require("scripts/prepare-autopkgtest-qemu-image.sh" in golden_builder, "golden image builder must prepare the nested QEMU test image")
require("scripts/seal-authoritative-runner-image.sh" in golden_builder, "golden image builder must seal guest-side runner state")
require("virt-sysprep" in golden_builder, "golden image builder must perform offline clone-safety cleanup")
require("machine-id" in golden_builder and "ssh-hostkeys" in golden_builder, "golden image builder must reset machine and SSH host identity")
require("qemu-img convert" in golden_builder, "golden image builder must flatten the preparation overlay")
require("qemu-img check" in golden_builder, "golden image builder must validate the final qcow2")
require("SUPRALINUX_REPLACE_GOLDEN_IMAGE" in golden_builder, "golden image replacement must require explicit opt-in")
require("golden-image-sha256.txt" in golden_builder, "golden image builder must retain final image SHA-256 evidence")

installer = read_required(ROOT / "scripts" / "install-actions-runner.sh")
require(".digest" in installer, "Actions runner installer must consume GitHub-published asset digest")
require("sha256sum --check --strict" in installer, "Actions runner installer must verify the downloaded archive")

host_orchestrator = read_required(ROOT / "scripts" / "run-kvm-jit-gate.sh")
require("generate-jitconfig" in host_orchestrator, "host orchestrator must use GitHub JIT runner configuration")
require("/run/supralinux-jit-config" in host_orchestrator, "JIT configuration must be injected into guest tmpfs")
require("virt-copy-out" in host_orchestrator, "host orchestrator must export guest diagnostics before deleting the overlay")
require("Authoritative self-hosted gates refuse fork PRs" in host_orchestrator, "host orchestrator must refuse fork PRs")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository policy validation: PASS")
print(f"Platform: {platform['version']} ({platform['series']})")
print(
    "Desktop: Plasma {plasma}, Frameworks {frameworks}, Gear {gear}".format(
        plasma=desktop["plasma"]["version"],
        frameworks=desktop["frameworks"]["version"],
        gear=desktop["gear"]["version"],
    )
)
print(
    f"Qt: required {qt['required_series']}, provider={provider['name']}, "
    f"candidate={provider.get('candidate_version', 'n/a')}, certification={cert['status']}"
)
print(
    "CI: hosted={hosted}; authoritative={platform}/{virt}/{lifecycle}; build={build}; test={test}; "
    "JIT=required; host-preflight=required; golden-builder=required; hosted-delta-gate=required".format(
        hosted=hosted["role"],
        platform=authoritative["platform"],
        virt=authoritative["virtualization"],
        lifecycle=authoritative["lifecycle"],
        build=authoritative["build_isolation"],
        test=authoritative["system_test"],
    )
)
