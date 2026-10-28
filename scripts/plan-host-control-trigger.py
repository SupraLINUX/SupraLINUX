#!/usr/bin/env python3
"""Plan explicit or narrowly-scoped automatic host control for the PR router."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

AUTO_SYNCHRONIZE_CONTROLS = {
    ("supralinux-proposed", "repair-frameworks-retained-artifacts"),
    ("supralinux-proposed", "repair-proposed-retained-artifacts"),
    ("supralinux-proposed", "certify-proposed-content"),
    ("supralinux-proposed", "certify-proposed-signing"),
    ("supralinux-proposed-integration", "preflight"),
    ("supralinux-proposed-integration", "execute"),
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def request_changed(repo: Path, before: str, after: str) -> bool:
    if not SHA_RE.fullmatch(before or "") or not SHA_RE.fullmatch(after or ""):
        raise SystemExit("synchronize host-control planning requires exact before/after SHAs")
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "diff",
            "--quiet",
            before,
            after,
            "--",
            "ops/host-authoritative/request.json",
        ]
    )
    if proc.returncode not in {0, 1}:
        raise SystemExit(f"git diff failed with exit code {proc.returncode}")
    return proc.returncode == 1


def plan(
    *,
    repo: Path,
    event_action: str,
    before: str,
    after: str,
    selector_path: Path,
    authoritative_request_path: Path,
) -> dict:
    selector = load_json(selector_path)
    target = selector.get("target", "workspace")
    if target not in {"workspace", "authoritative"}:
        raise SystemExit(f"unsupported host control target: {target!r}")

    if event_action == "labeled":
        return {
            "schema": 1,
            "requested": True,
            "target": target,
            "trigger": "explicit-ci-host-workspace-label",
            "automatic": False,
        }

    if event_action != "synchronize":
        raise SystemExit(f"unsupported host-control planning event: {event_action!r}")

    authoritative = load_json(authoritative_request_path)
    control = (authoritative.get("gate"), authoritative.get("mode"))
    changed = request_changed(repo, before, after)
    approved = (
        changed
        and target == "authoritative"
        and control in AUTO_SYNCHRONIZE_CONTROLS
    )
    return {
        "schema": 1,
        "requested": approved,
        "target": target,
        "trigger": "automatic-reviewed-proposed-maintenance" if approved else "none",
        "automatic": approved,
        "authoritative_request_changed": changed,
        "gate": authoritative.get("gate"),
        "mode": authoritative.get("mode"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--event-action", required=True)
    parser.add_argument("--before", default="")
    parser.add_argument("--after", default="")
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--authoritative-request", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve(strict=True)
    result = plan(
        repo=repo,
        event_action=args.event_action,
        before=args.before,
        after=args.after,
        selector_path=args.selector,
        authoritative_request_path=args.authoritative_request,
    )
    if args.github_output:
        with args.github_output.open("a") as output:
            output.write(f"target={result['target']}\n")
            output.write(f"requested={'true' if result['requested'] else 'false'}\n")
            output.write(f"trigger={result['trigger']}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
