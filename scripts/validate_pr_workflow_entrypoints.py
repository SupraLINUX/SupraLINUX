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
req(re.search(r"pull_request:\s*\n\s+types:\s*\[opened, synchronize, reopened\]", router) is not None,
    "PR router must handle opened/synchronize/reopened")

special = {
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

policy = blocks.get("repository-policy.yml", "")
req("  workflow_call:" in policy, "Repository Policy must be reusable from PR router")
req("  workflow_dispatch:" in policy, "Repository Policy must remain manually runnable")
req("  pull_request:" not in policy, "Repository Policy must not listen to PR directly")
req("  push:" in policy, "Repository Policy must retain main push validation")

router_text = (WF / "pr-ci-router.yml").read_text()
req("uses: ./.github/workflows/repository-policy.yml" in router_text,
    "PR router must invoke Repository Policy on every normal PR")

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
