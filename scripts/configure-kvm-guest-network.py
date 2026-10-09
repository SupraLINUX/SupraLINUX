#!/usr/bin/env python3
"""Configure traffic and private-address guards inside one disposable guest only."""
import argparse
import errno
import hashlib
import ipaddress
import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from decimal import Decimal

MAC = '52:54:00:53:55:01'
PRIVATE = '0.0.0.0/8, 10.0.0.0/8, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 240.0.0.0/4'


def rates(download, upload):
    assert isinstance(download, int) and isinstance(upload, int)
    assert 0 < download <= 256 and 0 < upload <= 64, 'Unsafe guest traffic ceilings'
    return download * 1024, upload * 1024


def verify_police(filters, text, download_bytes):
    # iproute2 emits police rate only in its text formatter (PRINT_FP), unlike
    # TBF's JSON rate. IEC text preserves our integral KiB/s rates exactly.
    policers = [action for entry in filters for action in entry.get('options', {}).get('actions', []) if action.get('kind') == 'police']
    assert len(policers) == 1 and policers[0]['control_action']['type'] == 'drop', 'Expected one drop policer'
    values = re.findall(r'\bpolice\s+0x[0-9a-f]+\s+rate\s+(\d+(?:\.\d+)?)(bit|Kibit|Mibit|Gibit)\b', text)
    scale = {'bit': 1, 'Kibit': 1024, 'Mibit': 1024**2, 'Gibit': 1024**3}
    assert len(values) == 1 and Decimal(values[0][0]) * scale[values[0][1]] == download_bytes * 8, 'Actual download policer differs from the admitted rate'


def private_reject_packets(loaded):
    ruleset = [x['rule'] for x in loaded['nftables'] if 'rule' in x]
    assert len(ruleset) == 5 and 'reject' in ruleset[3]['expr'][-1]
    counters = [x['counter'] for x in ruleset[3]['expr'] if 'counter' in x]
    assert len(counters) == 1 and isinstance(counters[0], dict), 'Stateful guest counter required; never use nft stateless output'
    packets = counters[0]['packets']
    assert type(packets) is int and packets >= 0
    return packets


def rules(interface):
    assert interface.isalnum(), 'Unexpected guest interface name'
    guard = f'''oifname "lo" accept
        ip daddr 10.203.0.3 meta l4proto {{ tcp, udp }} th dport 53 accept
        ip daddr {{ 10.203.0.2, 10.203.0.255, 255.255.255.255 }} udp sport 68 udp dport 67 accept
        ip daddr {{ {PRIVATE} }} counter reject
        meta nfproto ipv6 counter reject'''
    return f'''table inet supralinux_guest {{
      chain output {{ type filter hook output priority -5; policy accept;
        {guard}
      }}
      chain forward {{ type filter hook forward priority -5; policy accept;
        ip daddr {{ {PRIVATE} }} counter reject
        meta nfproto ipv6 counter reject
      }}
    }}'''


def verify_network(device):
    deadline = time.monotonic() + 45
    while True:
        addresses = json.loads(subprocess.check_output(['ip', '-json', '-4', 'address', 'show', 'dev', device], text=True))
        ipv4 = [a for entry in addresses for a in entry.get('addr_info', []) if a['family'] == 'inet']
        if ipv4:
            break
        assert time.monotonic() < deadline, 'SLIRP DHCP did not assign a guest address'
        time.sleep(1)
    subnet = ipaddress.ip_network('10.203.0.0/24')
    assert all(ipaddress.ip_address(a['local']) in subnet and a['prefixlen'] == 24 for a in ipv4)
    routes = json.loads(subprocess.check_output(['ip', '-json', '-4', 'route', 'show', 'default'], text=True))
    assert len(routes) == 1 and routes[0]['dev'] == device and routes[0]['gateway'] == '10.203.0.2'

    def blocked_packets():
        loaded = json.loads(subprocess.check_output(['nft', '--json', 'list', 'chain', 'inet', 'supralinux_guest', 'output'], text=True))
        return private_reject_packets(loaded)

    before = blocked_packets()
    probes = []
    # Neither target is a service we need. The output counter proves these
    # packets were rejected inside the guest before reaching QEMU or the LAN.
    for target in ['10.203.0.2', '192.168.254.254']:
        probe_before = blocked_packets()
        try:
            with socket.create_connection((target, 443), timeout=2):
                raise AssertionError('Private-address connection escaped the guest guard')
        except OSError as error:
            assert error.errno == errno.ECONNREFUSED, 'Private probe was not locally rejected'
            probe_after = blocked_packets()
            assert probe_after > probe_before, 'Connection refusal lacks a guest-local rejection counter'
            probes.append({'address': target, 'port': 443, 'errno': error.errno,
                           'reject_packets_before': probe_before, 'reject_packets_after': probe_after})
    after = blocked_packets()
    assert after - before >= len(probes), 'Guest rejection counters did not account for both private probes'
    request = urllib.request.Request('https://api.github.com/zen', headers={'User-Agent': 'SupraLINUX-isolation-probe'})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read(1025)
        assert response.status == 200 and 0 < len(payload) <= 1024
    return {'state': 'PASS', 'scope': 'bounded real SLIRP Internet and guest-local private-address rejection',
            'host_network_modified': False, 'guest_ipv4': ipv4, 'guest_default_route': routes,
            'private_probes': probes, 'private_reject_counter_delta': after - before,
            'internet_url': request.full_url, 'internet_status': 200, 'internet_payload_bytes': len(payload)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--download-kib', type=int, required=True)
    p.add_argument('--upload-kib', type=int, required=True)
    p.add_argument('--verify-network', action='store_true', help='bounded connectivity check after enabling the controlled guest link')
    a = p.parse_args()
    down, up = rates(a.download_kib, a.upload_kib)
    assert os.geteuid() == 0, 'Only the guest agent may configure its own VM'
    virtual = subprocess.check_output(['systemd-detect-virt', '--vm'], text=True).strip()
    assert virtual in {'kvm', 'qemu'}, 'Never execute on a physical host'
    interfaces = [x for x in Path('/sys/class/net').iterdir() if (x/'address').read_text().strip() == MAC]
    assert len(interfaces) == 1 and Path('/opt/actions-runner/bin/Runner.Listener').is_file(), 'Wrong disposable build guest'
    device = interfaces[0].name
    if a.verify_network:
        print(json.dumps(verify_network(device)))
        return
    commands = [
        ['tc', 'qdisc', 'replace', 'dev', device, 'root', 'tbf', 'rate', str(up * 8), 'burst', '8192', 'latency', '100ms'],
        ['tc', 'qdisc', 'add', 'dev', device, 'handle', 'ffff:', 'ingress'],
        ['tc', 'filter', 'add', 'dev', device, 'parent', 'ffff:', 'protocol', 'all', 'prio', '1', 'matchall',
         'action', 'police', 'rate', str(down * 8), 'burst', '8192', 'conform-exceed', 'drop'],
    ]
    policy = rules(device)
    subprocess.run(['nft', '-f', '-'], input=policy, text=True, check=True)
    for command in commands:
        subprocess.run(command, check=True, capture_output=True, text=True)
    qdisc = json.loads(subprocess.check_output(['tc', '-json', 'qdisc', 'show', 'dev', device], text=True))
    root = next(x for x in qdisc if x.get('root') and x['kind'] == 'tbf')
    assert root['options']['rate'] == up, 'Actual upload shaper differs from the admitted rate'
    filters = json.loads(subprocess.check_output(['tc', '-json', 'filter', 'show', 'dev', device, 'ingress'], text=True))
    ingress_text = subprocess.check_output(['tc', '-iec', 'filter', 'show', 'dev', device, 'ingress'], text=True)
    verify_police(filters, ingress_text, down)
    actual_rules = subprocess.check_output(['nft', '--json', 'list', 'table', 'inet', 'supralinux_guest'], text=True)
    assert filters and len([x for x in json.loads(actual_rules)['nftables'] if 'rule' in x]) == 7
    print(json.dumps({'state': 'PASS', 'scope': 'guest-only SLIRP private-address firewall and traffic controls',
                      'interface': device, 'guest_mac': MAC, 'host_network_modified': False,
                      'private_ipv4_and_external_ipv6_blocked': True, 'guest_loopback_preserved': True,
                      'download_kib_per_second': a.download_kib, 'upload_kib_per_second': a.upload_kib,
                      'download_control': 'guest ingress policer; TCP retransmission/backpressure, no reserved host bandwidth',
                      'upload_control': 'guest egress TBF', 'qdisc': qdisc, 'ingress_filters': filters,
                      'ingress_filter_iec_text': ingress_text,
                      'firewall_loaded': json.loads(actual_rules),
                      'firewall_source_sha256': hashlib.sha256(policy.encode()).hexdigest(),
                      'firewall_loaded_sha256': hashlib.sha256(actual_rules.encode()).hexdigest()}))


if __name__ == '__main__':
    main()
