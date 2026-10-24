#!/usr/bin/env python3
"""Validate the narrow host offload repair mechanism without touching the host."""
import importlib.machinery
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/restore-kvm-host-network-safety.py"
MODULE = importlib.machinery.SourceFileLoader("host_network_repair", str(SCRIPT)).load_module()

features = """Features for eno1:
tcp-segmentation-offload: on
generic-segmentation-offload: off
"""
assert MODULE.feature_states(features) == {"tso": "on", "gso": "off"}
assert MODULE.OFFLOAD_ARGS == ("tso", "off", "gso", "off")
assert MODULE.parse_driver("driver: e1000e\nversion: fixture\n") == "e1000e"

route_a = [{"dst": "default", "gateway": "192.168.1.1", "dev": "eno1",
            "protocol": "dhcp", "prefsrc": "192.168.1.41", "metric": 100,
            "expires": 100}]
route_b = [{**route_a[0], "expires": 50}]
assert MODULE.normalize_default_routes(route_a) == MODULE.normalize_default_routes(route_b)

address_a = [{"ifname": "eno1", "address": "00:11:22:33:44:55", "mtu": 1500,
              "addr_info": [{"family": "inet", "local": "192.168.1.41",
                             "prefixlen": 24, "scope": "global",
                             "valid_life_time": 100}]}]
address_b = [{"ifname": "eno1", "address": "00:11:22:33:44:55", "mtu": 1500,
              "addr_info": [{"family": "inet", "local": "192.168.1.41",
                             "prefixlen": 24, "scope": "global",
                             "valid_life_time": 50}]}]
assert MODULE.normalize_addresses(address_a) == MODULE.normalize_addresses(address_b)

source = SCRIPT.read_text()
for required in (
    'driver != "e1000e"',
    'len(devices) != 1',
    'run(["ethtool", "-K", device, *OFFLOAD_ARGS])',
    'features_after != {"tso": "off", "gso": "off"}',
    '"Interface addresses changed during offload repair."',
    '"Default route changed during offload repair."',
    'run(["python3", str(CHECKER), "--userspace"])',
    '"persistent_change": False',
    '"host_firewall_modified": False',
    '"host_packages_installed": False',
    '"host_routes_modified": False',
    '"host_bridges_modified": False',
    '"docker_modified": False',
    '"package_attempt_effect": "none"',
):
    assert required in source, required

for forbidden in ("iptables", "nft ", "apt-get", "apt ", "nmcli", "docker ", "ip link set",
                  "ip route add", "ip route del", "systemctl enable"):
    assert forbidden not in source, forbidden

print("Host e1000e runtime repair contract: PASS")
