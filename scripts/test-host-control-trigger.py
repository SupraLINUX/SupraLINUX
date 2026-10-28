#!/usr/bin/env python3
"""Contract tests for the scoped automatic host-control trigger planner."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "scripts/plan-host-control-trigger.py"
spec = importlib.util.spec_from_file_location("host_control_trigger", PLANNER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

expected_auto = {
    ("supralinux-proposed", "repair-frameworks-retained-artifacts"),
    ("supralinux-proposed", "repair-proposed-retained-artifacts"),
    ("supralinux-proposed", "certify-proposed-content"),
    ("supralinux-proposed", "certify-proposed-signing"),
    ("supralinux-proposed-integration", "preflight"),
    ("supralinux-proposed-integration", "execute"),
}
if module.AUTO_SYNCHRONIZE_CONTROLS != expected_auto:
    raise SystemExit("automatic host-control scope drifted")

with tempfile.TemporaryDirectory() as directory:
    repo = Path(directory)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
    (repo / "ops/host-authoritative").mkdir(parents=True)
    (repo / "ops/host-workspace").mkdir(parents=True)
    selector = repo / "ops/host-workspace/request.json"
    request = repo / "ops/host-authoritative/request.json"

    selector.write_text(json.dumps({"schema": 1, "target": "authoritative"}) + "\n")
    request.write_text(
        json.dumps(
            {
                "schema": 1,
                "mode": "diagnose",
                "gate": "plasma-package-build",
                "runner_group_id": 3,
            }
        )
        + "\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
    base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    request.write_text(
        json.dumps(
            {
                "schema": 1,
                "mode": "repair-proposed-retained-artifacts",
                "gate": "supralinux-proposed",
                "runner_group_id": 3,
            }
        )
        + "\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "proposed repair"], check=True)
    repair = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    automatic = module.plan(
        repo=repo,
        event_action="synchronize",
        before=base,
        after=repair,
        selector_path=selector,
        authoritative_request_path=request,
    )
    if not (
        automatic["requested"] is True
        and automatic["automatic"] is True
        and automatic["trigger"] == "automatic-reviewed-proposed-maintenance"
    ):
        raise SystemExit("reviewed proposed maintenance did not auto-trigger")

    (repo / "docs").mkdir()
    (repo / "docs/note.md").write_text("no request change\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "docs"], check=True)
    docs = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    no_request_change = module.plan(
        repo=repo,
        event_action="synchronize",
        before=repair,
        after=docs,
        selector_path=selector,
        authoritative_request_path=request,
    )
    if no_request_change["requested"] is not False:
        raise SystemExit("non-request synchronize delta auto-triggered host control")

    request.write_text(
        json.dumps(
            {
                "schema": 1,
                "mode": "execute",
                "gate": "plasma-package-build",
                "runner_group_id": 3,
            }
        )
        + "\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "package execute request"], check=True)
    package = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    package_attempt = module.plan(
        repo=repo,
        event_action="synchronize",
        before=docs,
        after=package,
        selector_path=selector,
        authoritative_request_path=request,
    )
    if package_attempt["requested"] is not False:
        raise SystemExit("package execution request was auto-triggered")

    request.write_text(
        json.dumps(
            {
                "schema": 1,
                "mode": "preflight",
                "gate": "supralinux-proposed-integration",
                "runner_group_id": 3,
            }
        )
        + "\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "proposed integration preflight"], check=True)
    integration_preflight = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    integration_preflight_plan = module.plan(
        repo=repo,
        event_action="synchronize",
        before=package,
        after=integration_preflight,
        selector_path=selector,
        authoritative_request_path=request,
    )
    if not (
        integration_preflight_plan["requested"] is True
        and integration_preflight_plan["automatic"] is True
        and integration_preflight_plan["gate"] == "supralinux-proposed-integration"
        and integration_preflight_plan["mode"] == "preflight"
    ):
        raise SystemExit("reviewed proposed integration preflight did not auto-trigger")

    request.write_text(
        json.dumps(
            {
                "schema": 1,
                "mode": "execute",
                "gate": "supralinux-proposed-integration",
                "runner_group_id": 3,
            }
        )
        + "\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "proposed integration execute"], check=True)
    integration = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    integration_attempt = module.plan(
        repo=repo,
        event_action="synchronize",
        before=integration_preflight,
        after=integration,
        selector_path=selector,
        authoritative_request_path=request,
    )
    if not (
        integration_attempt["requested"] is True
        and integration_attempt["automatic"] is True
        and integration_attempt["gate"] == "supralinux-proposed-integration"
        and integration_attempt["mode"] == "execute"
    ):
        raise SystemExit("reviewed proposed integration request did not auto-trigger")

    selector.write_text(json.dumps({"schema": 1, "target": "workspace"}) + "\n")
    explicit = module.plan(
        repo=repo,
        event_action="labeled",
        before="",
        after="",
        selector_path=selector,
        authoritative_request_path=request,
    )
    if not (
        explicit["requested"] is True
        and explicit["automatic"] is False
        and explicit["target"] == "workspace"
    ):
        raise SystemExit("explicit ci:host-workspace label semantics changed")

print("Scoped automatic host-control trigger contract: PASS")
