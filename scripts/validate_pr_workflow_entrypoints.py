#!/usr/bin/env python3
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
errors = []

def req(value, message):
    if not value:
        errors.append(message)

def on_block(text):
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line == "on:"), None)
    if start is None:
        return ""
    out = [lines[start]]
    for line in lines[start + 1:]:
        if line and not line.startswith((" ", "\t")):
            break
        out.append(line)
    return "\n".join(out)

files = sorted(list(WF.glob("*.yml")) + list(WF.glob("*.yaml")))
blocks = {p.name: on_block(p.read_text()) for p in files}

router = blocks.get("pr-ci-router.yml", "")
req("  pull_request:" in router, "PR router must be the normal pull_request entrypoint")
req(re.search(r"pull_request:\s*\n\s+types:\s*\[opened, synchronize, reopened, labeled\]", router) is not None,
    "PR router must handle opened/synchronize/reopened plus controlled labeled gates")

special = {
    "hosted-kvm-probe.yml",
    "hosted-ubuntu-guest-probe.yml",
    "hosted-sbuild-userns-diagnostic.yml",
    "authoritative-package-revalidation.yml",
    "authoritative-plasma-package-build.yml",
    "authoritative-frameworks-sample-proof.yml",
    "authoritative-package-proof.yml",
    "runner-contract.yml",
}

normal_direct = []
for name, block in blocks.items():
    if "  pull_request:" not in block:
        continue
    if name == "pr-ci-router.yml":
        continue
    if name in special:
        req(re.search(r"pull_request:\s*\n\s+types:\s*\[labeled\]", block) is not None,
            f"{name}: special PR entrypoint must remain labeled-only")
        continue
    normal_direct.append(name)

req(not normal_direct,
    "normal PR workflows must enter only through pr-ci-router.yml; direct listeners: " + ", ".join(normal_direct))

guest_workflow = (WF / "hosted-sbuild-userns-diagnostic.yml").read_text()
req("github.event.label.name == 'ci:hosted-sbuild-guest'" in guest_workflow,
    "hosted-sbuild-userns-diagnostic.yml must require its exact opt-in label")
req("github.event.pull_request.head.repo.full_name == github.repository" in guest_workflow,
    "hosted-sbuild-userns-diagnostic.yml must require same-repository PR head")
req("github.event_name == 'pull_request'" in guest_workflow,
    "hosted-sbuild-userns-diagnostic.yml must require PR event for guest KVM lane")
req("github.event_name != 'pull_request'" in guest_workflow,
    "hosted-sbuild-userns-diagnostic.yml must keep cheap host probe off labeled PR events")

policy = blocks.get("repository-policy.yml", "")
req("  workflow_call:" in policy, "Repository Policy must be reusable from PR router")
req("  workflow_dispatch:" in policy, "Repository Policy must remain manually runnable")
req("  pull_request:" not in policy, "Repository Policy must not listen to PR directly")
req("  push:" in policy, "Repository Policy must retain main push validation")

router_text = (WF / "pr-ci-router.yml").read_text()
req("uses: ./.github/workflows/repository-policy.yml" in router_text,
    "PR router must invoke Repository Policy on ordinary PR lifecycle events")
req(router_text.count("if: github.event.action != 'labeled'") >= 2,
    "labeled host workspace events must skip the full plan/repository-policy path")

host_workspace = blocks.get("host-workspace.yml", "")
req("  workflow_call:" in host_workspace,
    "Host workspace must be reusable from the PR router")
req("  pull_request:" not in host_workspace,
    "Host workspace must not listen to PR directly")
req("uses: ./.github/workflows/host-workspace.yml" in router_text,
    "PR router must own the host workspace entrypoint")
req("github.event.label.name == 'ci:host-workspace'" in router_text,
    "PR router must require the exact host-control opt-in label")
req("host-workspace-admission:" in router_text,
    "PR router must expose a cheap hosted admission gate for host control")
req("scripts/plan-host-control-trigger.py" in router_text,
    "PR router must use the reviewed host-control trigger planner")
req("needs: [repository-policy]" in router_text and
    "needs.repository-policy.result == 'success'" in router_text and
    "needs.repository-policy.result == 'skipped'" in router_text,
    "automatic host maintenance must be gated by repository policy while explicit labels remain usable")
req("needs.host-workspace-admission.outputs.requested == 'true'" in router_text,
    "host execution must require an affirmative reviewed trigger plan")
req("runs-on: ubuntu-26.04" in router_text,
    "host control admission must run on explicit hosted Ubuntu 26.04")
req("scripts/test-host-orchestrator-service.sh" in router_text and
    "scripts/test-host-workspace-libvirt-permissions.sh" in router_text,
    "workspace target must validate orchestrator and libvirt contracts")
req("needs: [host-workspace-admission]" in router_text,
    "host workspace must depend on successful hosted admission")
req("needs.host-workspace-admission.outputs.target == 'workspace'" in router_text,
    "host workspace must require the workspace selector")

host_authoritative = blocks.get("host-authoritative-control.yml", "")
req("  workflow_call:" in host_authoritative,
    "Host authoritative control must be reusable from the PR router")
req("  pull_request:" not in host_authoritative,
    "Host authoritative control must not listen to PR directly")
req("uses: ./.github/workflows/host-authoritative-control.yml" in router_text,
    "PR router must own the authoritative host control entrypoint")
req("python3 scripts/test-host-authoritative-control.py" in router_text,
    "authoritative target must validate its fixed-control contract")
req("needs.host-workspace-admission.outputs.target == 'authoritative'" in router_text,
    "authoritative host control must require the authoritative selector")
req('request.get("target", "workspace")' in router_text,
    "host admission must select workspace versus authoritative control from versioned input")
mode_match = re.search(r'request\.get\("mode"\) in \{([^}]*)\}', router_text)
expected_authoritative_modes = {
    "diagnose",
    "repair-host",
    "repair-libguestfs-runtime",
    "preflight",
    "rebuild-golden",
    "execute",
    "execute-and-publish-pass",
    "close-evidence-check",
    "close-evidence",
    "publish-evidence-check",
    "publish-evidence",
    "repair-frameworks-retained-artifacts",
    "repair-proposed-retained-artifacts",
    "certify-proposed-content",
    "certify-proposed-signing",
}
admitted_authoritative_modes = (
    set(re.findall(r'"([^"]+)"', mode_match.group(1)))
    if mode_match is not None else set()
)
req(admitted_authoritative_modes == expected_authoritative_modes,
    "host authoritative admission must expose exactly the reviewed fixed-control modes")

historical = [
    p.name for p in files
    if re.match(r"kde-tier3-kio-round(?:1[1-9]|2[0-6])-(?:diagnostic|provider-contract|remediation)\.yml$", p.name)
]
for name in historical:
    block = blocks[name]
    req("  workflow_call:" in block, f"{name}: historical workflow must remain reusable")
    req("  workflow_dispatch:" in block, f"{name}: historical workflow must remain manually runnable")
    req("  pull_request:" not in block, f"{name}: historical workflow must not listen to PR")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("PR workflow entrypoint architecture: PASS")
print("normal_pr_entrypoint=pr-ci-router.yml")
print("repository_policy=reusable-via-router")
print("special_labeled_entrypoints=" + ",".join(sorted(special)))
print("historical_kio_workflows=" + str(len(historical)))
