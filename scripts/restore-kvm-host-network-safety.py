#!/usr/bin/env python3
"""Restore the documented non-persistent e1000e KVM host offload safety state."""
import json
import os
import re
import subprocess
from pathlib import Path

CHECKER = Path("/usr/local/libexec/supralinux-check-kvm-network.py")
OFFLOAD_ARGS = ("tso", "off", "gso", "off")


def run(args, *, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def load_json(args):
    return json.loads(run(args).stdout)


def parse_driver(text):
    values = [
        line.split(":", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith("driver:")
    ]
    if len(values) != 1:
        raise SystemExit("Could not resolve exactly one NIC driver.")
    return values[0]


def feature_states(text):
    wanted = {}
    names = {
        "tcp-segmentation-offload": "tso",
        "generic-segmentation-offload": "gso",
    }
    for line in text.splitlines():
        for prefix, short in names.items():
            if line.startswith(prefix + ":"):
                value = line.split(":", 1)[1].strip().split()[0]
                if value not in {"on", "off"}:
                    raise SystemExit(f"Unexpected {short} state: {value!r}")
                wanted[short] = value
    if set(wanted) != {"tso", "gso"}:
        raise SystemExit("Could not read both TSO and GSO state.")
    return wanted


def normalize_default_routes(rows):
    keys = ("dst", "gateway", "dev", "prefsrc", "metric", "table", "protocol")
    return sorted(
        [{key: row.get(key) for key in keys if row.get(key) is not None} for row in rows],
        key=lambda row: json.dumps(row, sort_keys=True),
    )


def normalize_addresses(rows):
    normalized = []
    for row in rows:
        normalized.append(
            {
                "ifname": row.get("ifname"),
                "address": row.get("address"),
                "mtu": row.get("mtu"),
                "addr_info": sorted(
                    [
                        {
                            key: item.get(key)
                            for key in ("family", "local", "prefixlen", "scope", "label")
                            if item.get(key) is not None
                        }
                        for item in row.get("addr_info", [])
                    ],
                    key=lambda item: json.dumps(item, sort_keys=True),
                ),
            }
        )
    return sorted(normalized, key=lambda row: json.dumps(row, sort_keys=True))


def main():
    if os.geteuid() != 0:
        raise SystemExit("Host network safety repair must run as root.")
    if not CHECKER.is_file():
        raise SystemExit(f"Installed network checker is missing: {CHECKER}")

    default_before_raw = load_json(["ip", "-json", "route", "show", "default"])
    devices = sorted({row.get("dev") for row in default_before_raw if row.get("dev")})
    if len(devices) != 1:
        raise SystemExit(f"Expected exactly one default-route interface; got {devices!r}")
    device = devices[0]
    if re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", device) is None:
        raise SystemExit(f"Unsafe interface name: {device!r}")

    driver = parse_driver(run(["ethtool", "-i", device]).stdout)
    if driver != "e1000e":
        raise SystemExit(f"Refusing offload repair on non-e1000e interface: {device} uses {driver}")

    carrier_path = Path("/sys/class/net") / device / "carrier"
    carrier_before = carrier_path.read_text().strip()
    if carrier_before != "1":
        raise SystemExit(f"Default interface has no carrier before repair: {device}")

    addresses_before = normalize_addresses(
        load_json(["ip", "-json", "address", "show", "dev", device])
    )
    default_before = normalize_default_routes(default_before_raw)
    features_before = feature_states(run(["ethtool", "-k", device]).stdout)

    changed = any(features_before[name] != "off" for name in ("tso", "gso"))
    if changed:
        run(["ethtool", "-K", device, *OFFLOAD_ARGS])

    features_after = feature_states(run(["ethtool", "-k", device]).stdout)
    if features_after != {"tso": "off", "gso": "off"}:
        raise SystemExit(f"Required offload state was not applied: {features_after!r}")

    carrier_after = carrier_path.read_text().strip()
    if carrier_after != "1":
        raise SystemExit(f"Carrier changed during offload repair: {device}")

    addresses_after = normalize_addresses(
        load_json(["ip", "-json", "address", "show", "dev", device])
    )
    default_after = normalize_default_routes(
        load_json(["ip", "-json", "route", "show", "default"])
    )
    if addresses_after != addresses_before:
        raise SystemExit("Interface addresses changed during offload repair.")
    if default_after != default_before:
        raise SystemExit("Default route changed during offload repair.")

    admitted = json.loads(run(["python3", str(CHECKER), "--userspace"]).stdout)
    if admitted.get("state") != "PASS" or admitted.get("host_network_modified") is not False:
        raise SystemExit(f"Bridge-free network admission did not pass: {admitted!r}")

    print(
        json.dumps(
            {
                "state": "PASS",
                "scope": "e1000e-runtime-offload-safety-restore",
                "interface": device,
                "driver": driver,
                "changed": changed,
                "features_before": features_before,
                "features_after": features_after,
                "carrier_before": carrier_before,
                "carrier_after": carrier_after,
                "addresses_preserved": True,
                "default_route_preserved": True,
                "userspace_network_admission": "PASS",
                "persistent_change": False,
                "host_firewall_modified": False,
                "host_packages_installed": False,
                "host_routes_modified": False,
                "host_bridges_modified": False,
                "docker_modified": False,
                "vm_created": False,
                "jit_invoked": False,
                "package_attempt_effect": "none",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
