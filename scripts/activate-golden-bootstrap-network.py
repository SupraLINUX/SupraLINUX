#!/usr/bin/env python3
"""Enable golden SLIRP only after a guest-side guard reports readiness."""
import argparse
import json
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAC = "52:54:00:53:55:01"
MAX_MESSAGE_BYTES = 16_384


def run(command, *, check=True):
    return subprocess.run(command, check=check, capture_output=True, text=True)


def virsh(uri, *args, check=True):
    return run(["virsh", "--connect", uri, *args], check=check)


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


def connect_channel(path, timeout):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.connect(str(path))
            return client
        except OSError as exc:
            last_error = exc
            client.close()
            time.sleep(0.5)
    raise SystemExit(f"Timed out connecting to golden bootstrap channel {path}: {last_error}")


def read_message(client, expected_kind, timeout):
    client.settimeout(timeout)
    data = bytearray()
    while True:
        try:
            chunk = client.recv(4096)
        except socket.timeout:
            raise SystemExit(
                f"Timed out waiting for {expected_kind} on the golden bootstrap channel."
            )
        if not chunk:
            raise SystemExit(
                f"Golden bootstrap channel closed before {expected_kind} was received."
            )
        data.extend(chunk)
        if len(data) > MAX_MESSAGE_BYTES:
            raise SystemExit("Golden bootstrap channel message exceeded the size limit.")
        if b"\n" in data:
            line, _, remainder = data.partition(b"\n")
            if remainder:
                raise SystemExit("Golden bootstrap channel emitted multiple messages at once.")
            break
    try:
        kind, raw = line.decode("utf-8").split(" ", 1)
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit("Golden bootstrap channel emitted an invalid message.") from exc
    if kind == "ERROR":
        raise SystemExit(f"Golden guest bootstrap reported an error: {payload!r}")
    if kind != expected_kind:
        raise SystemExit(
            f"Golden bootstrap channel expected {expected_kind}, received {kind}: {payload!r}"
        )
    if payload.get("state") != "PASS":
        raise SystemExit(f"Golden bootstrap {expected_kind} did not report PASS: {payload!r}")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vm-name", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--channel-socket", type=Path, required=True)
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
    socket_path = args.channel_socket.resolve()

    before = check_domain(args.libvirt_uri, args.vm_name, evidence, "down")
    client = connect_channel(socket_path, args.timeout)
    protocol = []
    try:
        ready = read_message(client, "READY", args.timeout)
        protocol.append({"kind": "READY", "payload": ready})
        if not (
            ready.get("phase") == "guard"
            and ready.get("host_network_modified") is False
            and ready.get("private_ipv4_and_external_ipv6_blocked") is True
        ):
            raise SystemExit(f"Golden guest guard readiness is incomplete: {ready!r}")

        still_down = check_domain(args.libvirt_uri, args.vm_name, evidence, "down")
        virsh(args.libvirt_uri, "domif-setlink", args.vm_name, MAC, "up")
        after = check_domain(args.libvirt_uri, args.vm_name, evidence, "up")

        verified = read_message(client, "VERIFIED", args.timeout)
        protocol.append({"kind": "VERIFIED", "payload": verified})
        if not (
            verified.get("phase") == "verify"
            and verified.get("host_network_modified") is False
            and verified.get("private_reject_counter_delta", 0) >= 2
            and verified.get("internet_status") == 200
            and verified.get("bootstrap_cleanup") == "PASS"
        ):
            raise SystemExit(f"Golden guest connectivity/isolation verification failed: {verified!r}")
    finally:
        client.close()
        (evidence / "bootstrap-channel-protocol.json").write_text(
            json.dumps(protocol, indent=2, sort_keys=True) + "\n"
        )
    print(
        json.dumps(
            {
                "state": "PASS",
                "scope": "golden-bootstrap-network-activation",
                "transport": "virtio-serial-unix-channel",
                "guest_link_before": before["guest_link"],
                "guest_link_before_activation": still_down["guest_link"],
                "guest_link_after": after["guest_link"],
                "host_network_modified": False,
                "private_reject_counter_delta": verified["private_reject_counter_delta"],
                "internet_status": verified["internet_status"],
                "bootstrap_cleanup": verified["bootstrap_cleanup"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
