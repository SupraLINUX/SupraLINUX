#!/usr/bin/env python3
"""Conservative PR-only historical-validator selector for Repository Policy.

Full legacy validation remains mandatory for main, manual audits, unknown deltas,
missing SHA/diffs, and any changes outside a strictly reviewed live-only allowlist.
This changes *execution scope*, never archived evidence or the validator code.
"""
import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"^[0-9a-f]{40}$")

# Explicit safe set, not a blacklist: any unknown path forces the full suite.
LIVE_FILES = frozenset({
    "manifests/desktop-image-profile.json",
    "manifests/desktop-stack.json",
    "manifests/kde-plasma-level0.json",
    "manifests/kde-plasma-package-build.json",
    "docs/status/current.md",
    "docs/hosted-ubuntu-guest-probe.md",
    "docs/hosted-kvm-probe.md",
    ".github/workflows/hosted-kvm-probe.yml",
    ".github/workflows/hosted-ubuntu-guest-probe.yml",
    "scripts/hosted-ubuntu-guest-lane.sh",
    "scripts/hosted-ubuntu-guest-snapshot.py",
    "scripts/test-hosted-ubuntu-guest-snapshot.py",
    "scripts/probe-hosted-kvm.py",
    "scripts/test-hosted-kvm-probe.py",
    "scripts/plan-desktop-image.py",
    "scripts/test-desktop-image-planner.py",
    "scripts/validate_plasma_package_build.py",
    "scripts/test-plasma-package-inputs.py",
    "scripts/test-native-fixture-review.py",
    "scripts/plasma_lifecycle.py",
    "scripts/validate_repository.py",
})
LIVE_PREFIXES = ("packages/plasma/",)


def historical_required(paths):
    if not paths:
        return True  # deleted/renamed files and empty evidence are not safe
    return any(p not in LIVE_FILES and not any(p.startswith(prefix) for prefix in LIVE_PREFIXES)
               for p in paths)


def git_delta(before, after):
    if not (SHA.fullmatch(before) and SHA.fullmatch(after)) or before == after:
        return None
    try:
        changed = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", "--no-ext-diff",
             "--diff-filter=ACDMRTUXB", before, after, "--"],
            text=True, timeout=25, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return changed.splitlines()


def choose(event, action, before, after, base, head):
    if event != "pull_request":
        return True, "non-PR: full evidence policy"
    if action == "synchronize":
        paths = git_delta(before, after)
        # Missing exact event delta must not silently exclude historical tests.
        if paths is None:
            paths = git_delta(base, head)
    else:
        paths = git_delta(base, head)
    if paths is None:
        return True, "unknown/unavailable PR delta"
    if historical_required(paths):
        return True, f"historical/unknown source in {len(paths)} changed paths"
    return False, f"only {len(paths)} allowlisted current-product paths"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    do_full, reason = choose(
        os.getenv("POLICY_EVENT", ""),
        os.getenv("POLICY_ACTION", ""),
        os.getenv("POLICY_BEFORE", ""),
        os.getenv("POLICY_AFTER", ""),
        os.getenv("POLICY_BASE", ""),
        os.getenv("POLICY_HEAD", ""),
    )
    with args.github_output.open("a") as handle:
        handle.write("historical=" + ("true" if do_full else "false") + "\n")
    print("Historical policy scope:", "FULL" if do_full else "SKIPPED (reusable archived inputs)",
          ";", reason)


if __name__ == "__main__":
    main()
