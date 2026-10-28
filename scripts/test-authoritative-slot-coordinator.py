#!/usr/bin/env python3
import os
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COORDINATOR = ROOT / "scripts/authoritative-slot-coordinator.sh"


def run(mode, command, env, check=False):
    return subprocess.run(
        [str(COORDINATOR), mode, "--", *command],
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    env = os.environ.copy()
    env["SUPRALINUX_AUTHORITATIVE_LOCK_ROOT"] = str(root / "locks")
    env["SUPRALINUX_AUTHORITATIVE_SLOTS"] = "2"
    env["SUPRALINUX_REPOSITORY"] = "SupraLINUX/SupraLINUX"

    markers = [root / "slot-a", root / "slot-b"]
    workers = []
    for marker in markers:
        script = (
            f'printf "%s\\n" "$SUPRALINUX_AUTHORITATIVE_SLOT" > {marker}; '
            'sleep 1'
        )
        workers.append(
            subprocess.Popen(
                [str(COORDINATOR), "worker", "--", "bash", "-c", script],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not all(marker.exists() for marker in markers):
        time.sleep(0.05)
    assert all(marker.exists() for marker in markers), "two worker slots were not acquired"

    slots = sorted(marker.read_text().strip() for marker in markers)
    assert slots == ["1", "2"], f"expected distinct slots 1/2, got {slots}"

    third = run("worker", ["true"], env)
    assert third.returncode == 75
    assert "No authoritative execution slot is available" in third.stderr

    maintenance = run("maintenance", ["true"], env)
    assert maintenance.returncode == 75
    assert "blocked by active workers" in maintenance.stderr

    for worker in workers:
        assert worker.wait(timeout=5) == 0, worker.stderr.read()

    maintenance = run(
        "maintenance",
        ["bash", "-c", 'test "$SUPRALINUX_AUTHORITATIVE_SLOT" = maintenance'],
        env,
    )
    assert maintenance.returncode == 0, maintenance.stderr

    env["SUPRALINUX_AUTHORITATIVE_SLOTS"] = "1"
    first = subprocess.Popen(
        [str(COORDINATOR), "worker", "--", "bash", "-c", "sleep 1"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.2)
    second = run("worker", ["true"], env)
    assert second.returncode == 75
    assert first.wait(timeout=5) == 0, first.stderr.read()

    bad = env.copy()
    bad["SUPRALINUX_AUTHORITATIVE_SLOTS"] = "0"
    assert run("worker", ["true"], bad).returncode == 64
    bad["SUPRALINUX_AUTHORITATIVE_SLOTS"] = "9"
    assert run("worker", ["true"], bad).returncode == 64

print("Authoritative slot coordinator contract: PASS")
