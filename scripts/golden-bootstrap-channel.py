#!/usr/bin/env python3
"""Run the golden bootstrap network guard inside the disposable guest."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

MAC = "52:54:00:53:55:01"
PORT = Path("/dev/virtio-ports/org.supralinux.bootstrap.0")
HELPER = Path("/usr/local/libexec/supralinux-configure-golden-bootstrap-network.py")
EVIDENCE = Path("/var/lib/supralinux/evidence")
CLEANUP_PATHS = (
    Path("/etc/systemd/system/sysinit.target.wants/supralinux-golden-bootstrap-guard.service"),
    Path("/etc/systemd/system/multi-user.target.wants/supralinux-golden-bootstrap-verify.service"),
    Path("/etc/systemd/system/supralinux-golden-bootstrap-guard.service"),
    Path("/etc/systemd/system/supralinux-golden-bootstrap-verify.service"),
    HELPER,
    Path("/usr/local/libexec/supralinux-golden-bootstrap-channel.py"),
)


def wait_for_interface(timeout):
    deadline = time.monotonic() + timeout
    while True:
        matches = []
        for entry in Path("/sys/class/net").iterdir():
            try:
                if (entry / "address").read_text().strip().lower() == MAC:
                    matches.append(entry.name)
            except OSError:
                continue
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RuntimeError(f"multiple interfaces expose the golden MAC: {matches!r}")
        if time.monotonic() >= deadline:
            raise TimeoutError("timed out waiting for the controlled golden guest interface")
        time.sleep(0.5)


def run_helper(verify, timeout):
    args = ["/usr/bin/python3", str(HELPER), "--bootstrap"]
    if verify:
        args.append("--verify-network")
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "golden guest network helper failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}")
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("golden guest network helper returned invalid JSON") from exc
    return payload, completed.stderr


def write_evidence(name, payload):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    text_value = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (EVIDENCE / name).write_text(text_value)
    return hashlib.sha256(text_value.encode()).hexdigest()


def open_port(timeout):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return os.open(PORT, os.O_WRONLY | os.O_CLOEXEC | os.O_NONBLOCK)
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for bootstrap virtio channel: {PORT}")
            time.sleep(0.5)


def send(kind, payload, timeout=30):
    data = (
        kind
        + " "
        + json.dumps(payload, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()
    deadline = time.monotonic() + timeout
    while True:
        fd = open_port(max(1, int(deadline - time.monotonic())))
        try:
            written = os.write(fd, data)
            if written != len(data):
                raise RuntimeError(f"short bootstrap channel write: {written}/{len(data)}")
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)
        finally:
            os.close(fd)


def cleanup_bootstrap():
    failures = []
    for path in CLEANUP_PATHS:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            failures.append(f"{path}: {exc}")
    if failures:
        raise RuntimeError("bootstrap cleanup failed: " + "; ".join(failures))


def guard_phase():
    interface = wait_for_interface(60)
    payload, stderr = run_helper(False, 90)
    if not (
        payload.get("state") == "PASS"
        and payload.get("host_network_modified") is False
        and payload.get("private_ipv4_and_external_ipv6_blocked") is True
        and payload.get("bootstrap_mode") is True
    ):
        raise RuntimeError(f"golden guest isolation did not pass: {payload!r}")
    digest = write_evidence("golden-bootstrap-guard.json", payload)
    send(
        "READY",
        {
            "state": "PASS",
            "phase": "guard",
            "interface": interface,
            "host_network_modified": False,
            "private_ipv4_and_external_ipv6_blocked": True,
            "policy_sha256": digest,
            "stderr_empty": not bool(stderr.strip()),
        },
    )


def verify_phase():
    payload, stderr = run_helper(True, 120)
    if not (
        payload.get("state") == "PASS"
        and payload.get("host_network_modified") is False
        and payload.get("private_reject_counter_delta", 0) >= 2
        and payload.get("internet_status") == 200
    ):
        raise RuntimeError(f"golden guest connectivity/isolation probe failed: {payload!r}")
    digest = write_evidence("golden-bootstrap-connectivity.json", payload)
    cleanup_bootstrap()
    send(
        "VERIFIED",
        {
            "state": "PASS",
            "phase": "verify",
            "host_network_modified": False,
            "private_reject_counter_delta": payload["private_reject_counter_delta"],
            "internet_status": payload["internet_status"],
            "connectivity_sha256": digest,
            "bootstrap_cleanup": "PASS",
            "stderr_empty": not bool(stderr.strip()),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("guard", "verify"), required=True)
    args = parser.parse_args()
    try:
        if args.phase == "guard":
            guard_phase()
        else:
            verify_phase()
    except Exception as exc:
        try:
            send(
                "ERROR",
                {
                    "state": "FAIL",
                    "phase": args.phase,
                    "error": str(exc)[:2000],
                },
                timeout=5,
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
