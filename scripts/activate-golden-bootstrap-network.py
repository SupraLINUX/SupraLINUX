#!/usr/bin/env python3
"""Install the golden guest network guard through QGA before enabling SLIRP."""
import argparse
import base64
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAC = "52:54:00:53:55:01"


def run(command, *, check=True):
    return subprocess.run(command, check=check, capture_output=True, text=True)


def virsh(uri, *args, check=True):
    return run(["virsh", "--connect", uri, *args], check=check)


def qga(uri, vm, payload):
    result = virsh(uri, "qemu-agent-command", vm, json.dumps(payload))
    return json.loads(result.stdout)


def wait_qga(uri, vm, timeout):
    deadline = time.monotonic() + timeout
    while True:
        try:
            qga(uri, vm, {"execute": "guest-ping"})
            return
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            if time.monotonic() >= deadline:
                raise SystemExit("Timed out waiting for qemu-guest-agent before network activation.")
            time.sleep(2)


def guest_python(uri, vm, source, argv, timeout):
    encoded = base64.b64encode(source.read_bytes()).decode()
    code = (
        "import base64,sys;"
        f"sys.argv={argv!r};"
        f"exec(compile(base64.b64decode({encoded!r}),'golden-network','exec'))"
    )
    launched = qga(
        uri,
        vm,
        {
            "execute": "guest-exec",
            "arguments": {
                "path": "/usr/bin/python3",
                "arg": ["-c", code],
                "capture-output": True,
            },
        },
    )
    pid = launched.get("return", {}).get("pid")
    if type(pid) is not int or pid <= 0:
        raise SystemExit("qemu-guest-agent did not return a valid helper PID.")
    deadline = time.monotonic() + timeout
    while True:
        status = qga(
            uri,
            vm,
            {"execute": "guest-exec-status", "arguments": {"pid": pid}},
        ).get("return", {})
        if status.get("exited") is True:
            stdout = base64.b64decode(status.get("out-data", "")).decode(errors="replace")
            stderr = base64.b64decode(status.get("err-data", "")).decode(errors="replace")
            if status.get("exitcode", 1) != 0:
                raise SystemExit(
                    "Golden guest network helper failed before/after link activation: "
                    + stderr.strip()
                )
            return status, stdout, stderr
        if time.monotonic() >= deadline:
            raise SystemExit("Timed out waiting for golden guest network helper.")
        time.sleep(1)


def check_domain(uri, vm, evidence, expected_link):
    domain_path = evidence / (
        "network-live-domain.xml"
        if expected_link == "down"
        else "network-live-domain-enabled.xml"
    )
    domain_path.write_text(virsh(uri, "dumpxml", vm).stdout)
    check = run(
        [
            "python3",
            str(ROOT / "scripts/check-kvm-network.py"),
            "--userspace",
            "--domain-xml",
            str(domain_path),
        ]
    )
    report = json.loads(check.stdout)
    if report.get("state") != "PASS" or report.get("guest_link") != expected_link:
        raise SystemExit(f"Unexpected golden guest link admission: {report!r}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vm-name", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--libvirt-uri", default="qemu:///system")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if not (
        args.vm_name.startswith("supralinux-golden-")
        or args.vm_name.startswith("supralinux-golden-network-")
    ):
        raise SystemExit("Refusing to control a VM outside the golden namespaces.")
    if args.timeout < 30 or args.timeout > 900:
        raise SystemExit("Golden network activation timeout must be 30..900 seconds.")

    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    helper = ROOT / "scripts/configure-golden-bootstrap-network.py"

    before = check_domain(args.libvirt_uri, args.vm_name, evidence, "down")
    wait_qga(args.libvirt_uri, args.vm_name, args.timeout)

    status, stdout, stderr = guest_python(
        args.libvirt_uri,
        args.vm_name,
        helper,
        ["golden-network", "--bootstrap"],
        90,
    )
    (evidence / "network-guest-policy-execution.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n"
    )
    (evidence / "network-guest-policy.stderr").write_text(stderr)
    policy = json.loads(stdout)
    (evidence / "network-guest-safety.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n"
    )
    if not (
        policy.get("state") == "PASS"
        and policy.get("host_network_modified") is False
        and policy.get("private_ipv4_and_external_ipv6_blocked") is True
        and policy.get("bootstrap_mode") is True
    ):
        raise SystemExit(f"Golden guest isolation did not pass: {policy!r}")

    virsh(args.libvirt_uri, "domif-setlink", args.vm_name, MAC, "up")
    after = check_domain(args.libvirt_uri, args.vm_name, evidence, "up")

    status, stdout, stderr = guest_python(
        args.libvirt_uri,
        args.vm_name,
        helper,
        ["golden-network", "--bootstrap", "--verify-network"],
        120,
    )
    (evidence / "network-guest-connectivity-execution.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n"
    )
    (evidence / "network-guest-connectivity.stderr").write_text(stderr)
    connectivity = json.loads(stdout)
    (evidence / "network-guest-connectivity.json").write_text(
        json.dumps(connectivity, indent=2, sort_keys=True) + "\n"
    )
    if not (
        connectivity.get("state") == "PASS"
        and connectivity.get("host_network_modified") is False
        and connectivity.get("private_reject_counter_delta", 0) >= 2
        and connectivity.get("internet_status") == 200
    ):
        raise SystemExit(f"Golden guest connectivity/isolation probe failed: {connectivity!r}")

    print(
        json.dumps(
            {
                "state": "PASS",
                "scope": "golden-bootstrap-network-activation",
                "guest_link_before": before["guest_link"],
                "guest_link_after": after["guest_link"],
                "host_network_modified": False,
                "private_reject_counter_delta": connectivity["private_reject_counter_delta"],
                "internet_status": connectivity["internet_status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
