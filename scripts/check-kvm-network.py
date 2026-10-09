#!/usr/bin/env python3
"""Admit current bridge-free SLIRP; retain the historical NAT checker for replay."""
import argparse
import hashlib
import importlib.machinery
import ipaddress
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

PRIVATE_IPV4 = tuple(ipaddress.ip_network(value) for value in
                     ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
USER_SUBNET = ipaddress.ip_network('10.203.0.0/24')
USER_MAC = '52:54:00:53:55:01'


def check_retained_probes(root):
    paths = sorted((root/'manifests/evidence/host-network-safety').glob('slirp-probe*/verification.json'))
    for path in paths:
        proof = json.loads(path.read_text())
        assert proof['state'] in {'PASS', 'INFRA_INVALID'}
        assert proof['scope'] == 'synthetic bridge-free KVM guest network isolation and JIT startup'
        assert proof['package_attempt_consumed'] is proof['package_execution_started'] is proof['workflow_triggered'] is False
        assert proof['host_network_modified'] is proof['host_packages_installed'] is proof['host_firewall_modified'] is False
        assert proof['hardware_hang_observed'] is False and proof['physical_link_retained'] is True
        assert proof['cleanup_verified'] is proof['offline_restore_verified'] is True
        for name, digest in proof['files_sha256'].items():
            file = path.parent/name
            assert file.resolve().is_relative_to(path.parent.resolve())
            assert hashlib.sha256(file.read_bytes()).hexdigest() == digest
        assert proof['files_sha256']['evidence-sha256.txt'] == proof['host_evidence_seal_sha256']
        cleanup = json.loads((path.parent/'cleanup.json').read_text())
        assert cleanup['source_commit'] == proof['source_commit'] and cleanup['workflow_run_id'] is None
        assert all(cleanup[k] is True for k in ['vm_absent', 'runner_absent', 'overlay_absent', 'golden_image_preserved', 'execution_backing_image_preserved'])
        health = [json.loads(line) for line in (path.parent/'host-health.jsonl').read_text().splitlines()]
        assert len(health) == proof['host_health_samples'] and health
        assert all(x['journal_exit_code'] in (0, 1) and not x['hardware_hang_seen'] and x['eno1_carrier'] == '1' for x in health)
        host = json.loads((path.parent/'host-result.json').read_text())
        assert host['workflow_run_id'] == ''
        domain = check_userspace_domain((path.parent/'network-live-domain.xml').read_text())
        assert domain['guest_link'] == 'down'
        kvm = json.loads((path.parent/'qemu-cpu-policy.json').read_text())['kvm']
        assert kvm['enabled'] is kvm['present'] is True
        if proof['state'] == 'INFRA_INVALID':
            assert host['exit_code'] != 0 and proof['guest_link_enabled'] is proof['runner_registered'] is False
            assert proof['original_guest_exit_code'] != 0 and proof['original_error'] and proof['repair']
            continue
        assert host['exit_code'] == 0
        assert check_userspace_domain((path.parent/'network-live-domain-enabled.xml').read_text())['guest_link'] == 'up'
        limits = json.loads((path.parent/'network-guest-safety.json').read_text())
        assert limits['state'] == 'PASS' and limits['host_network_modified'] is False
        down, up = safe_rates(limits['download_kib_per_second'], limits['upload_kib_per_second'])
        shaper = next(x for x in limits['qdisc'] if x.get('root') and x['kind'] == 'tbf')
        assert shaper['options']['rate'] == up * 1024
        guest = importlib.machinery.SourceFileLoader('guest_network_proof', str(root/'scripts/configure-kvm-guest-network.py')).load_module()
        guest.verify_police(limits['ingress_filters'], limits['ingress_filter_iec_text'], down * 1024)
        connectivity = json.loads((path.parent/'network-guest-connectivity.json').read_text())
        assert connectivity['state'] == 'PASS' and connectivity['host_network_modified'] is False
        assert connectivity['private_reject_counter_delta'] == 2 and len(connectivity['private_probes']) == 2
        assert connectivity['internet_status'] == 200 and 0 < connectivity['internet_payload_bytes'] <= 1024
        marker = dict(line.split('=', 1) for line in (path.parent/'jit-startup-preflight-result.txt').read_text().splitlines())
        assert marker['status'] == marker['cleanup'] == 'PASS' and marker['workflow_triggered'] == 'no'
    return {'state': 'PASS', 'retained_network_probes': len(paths)}


def safe_rates(download, upload):
    download, upload = rate(download), rate(upload)
    assert download <= 256 and upload <= 64, 'Traffic exceeds the conservative host safety ceilings (256/64 KiB/s)'
    return download, upload


def check_userspace_host(addresses, routes):
    for interface in addresses:
        for item in interface.get('addr_info', []):
            if item.get('family') == 'inet':
                other = ipaddress.ip_network(f"{item['local']}/{item['prefixlen']}", strict=False)
                assert not USER_SUBNET.overlaps(other), 'SLIRP subnet overlaps a host address'
    for route in routes:
        if route.get('dst') not in (None, 'default'):
            other = ipaddress.ip_network(route['dst'], strict=False)
            assert not USER_SUBNET.overlaps(other), 'SLIRP subnet overlaps a host/VPN route'
    return {'state': 'PASS', 'backend': 'slirp', 'guest_subnet': str(USER_SUBNET),
            'host_network_modified': False, 'host_bridge_or_tap_required': False,
            'host_default_interfaces': sorted({r['dev'] for r in routes if r.get('dst') == 'default' and r.get('dev')})}


def check_userspace_domain(xml):
    root = ET.fromstring(xml)
    interfaces = root.findall('devices/interface')
    assert len(interfaces) == 1, 'Exactly one userspace guest interface required'
    interface = interfaces[0]
    assert interface.get('type') == 'user', 'Bridge, TAP, network, direct and passthrough interfaces are forbidden'
    assert interface.find('model') is not None and interface.find('model').get('type') == 'virtio'
    assert interface.find('mac') is not None and interface.find('mac').get('address') == USER_MAC, 'Unexpected guest MAC'
    ips = interface.findall('ip')
    assert len(ips) == 1 and ips[0].attrib == {'family': 'ipv4', 'address': '10.203.0.1', 'prefix': '24'}
    for name in ['source', 'target', 'backend', 'bandwidth', 'portForward', 'virtualport']:
        assert interface.find(name) is None, f'Forbidden userspace interface element: {name}'
    assert root.find('devices/hostdev') is None, 'Host device passthrough forbidden on build guests'
    ns = {'qemu': 'http://libvirt.org/schemas/domain/qemu/1.0'}
    args = [item.get('value', '') for item in root.findall('qemu:commandline/qemu:arg', ns)]
    assert not any(any(token in arg for token in ['-netdev', '-nic', '-net', 'hostfwd', 'guestfwd']) for arg in args), 'Unreviewed QEMU network override'
    return {'state': 'PASS', 'backend': 'slirp', 'guest_subnet': str(USER_SUBNET),
            'guest_mac': USER_MAC, 'host_bridge_or_tap_required': False,
            'guest_link': interface.find('link').get('state') if interface.find('link') is not None else 'up'}


def check_nic_features(driver, features):
    if driver == 'e1000e':
        for name in ['tcp-segmentation-offload', 'generic-segmentation-offload']:
            assert re.search(r'^' + name + r': off(?:\s|$)', features, re.M), 'Observed e1000e hang: TSO/GSO must be disabled before any guest network traffic'


def rate(value):
    if not re.fullmatch(r'[1-9][0-9]*', str(value)):
        raise ValueError('Guest bandwidth must be a positive integer in KiB/s')
    return int(value)


def check_network(xml, network, addresses, routes, links):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', network):
        raise ValueError('Use a simple libvirt network name')
    root = ET.fromstring(xml)
    assert root.tag == 'network' and root.findtext('name') == network
    forward = root.find('forward')
    assert forward is not None and forward.get('mode') == 'nat', 'Only private NAT is admitted'
    bridge = root.find('bridge')
    assert bridge is not None and bridge.get('name'), 'NAT bridge missing'
    bridge = bridge.get('name')
    link = next((item for item in links if item['ifname'] == bridge), None)
    assert link and link.get('linkinfo', {}).get('info_kind') == 'bridge', 'NAT bridge not present'
    # A libvirt NAT bridge must not contain a physical LAN interface.
    ports = [item for item in links if item.get('master') in (bridge, link['ifindex'])]
    assert all(item.get('linkinfo', {}).get('info_kind') == 'tun' for item in ports), 'NAT bridge has non-guest ports'
    assert not any(item.get('dev') == bridge and item.get('dst') == 'default' for item in routes), 'NAT bridge carries the host default route'
    ips = root.findall('ip')
    assert ips and all(item.get('family', 'ipv4') == 'ipv4' for item in ips), 'Reviewed runner network requires IPv4 NAT'
    subnets = []
    for item in ips:
        address = item.get('address')
        prefix = item.get('prefix') or item.get('netmask')
        assert address and prefix, 'Explicit NAT address and prefix required'
        subnet = ipaddress.ip_network(f'{address}/{prefix}', strict=False)
        assert subnet.version == 4 and any(subnet.subnet_of(private) for private in PRIVATE_IPV4), 'NAT must use RFC1918 space'
        assert not any(subnet.overlaps(other) for other in subnets), 'Overlapping NAT subnets'
        subnets.append(subnet)
        ranges = item.findall('dhcp/range')
        assert ranges, 'Runner network needs an existing DHCP range'
        for interval in ranges:
            first, last = (ipaddress.ip_address(interval.get(key)) for key in ('start', 'end'))
            assert first in subnet and last in subnet and first <= last, 'DHCP range outside NAT subnet'
        actual = next((entry for entry in addresses if entry['ifname'] == bridge), {})
        assert any(entry.get('family') == 'inet' and entry.get('local') == address and
                   ipaddress.ip_network(f"{entry['local']}/{entry['prefixlen']}", strict=False) == subnet
                   for entry in actual.get('addr_info', [])), 'Live bridge address differs from libvirt'
    for interface in addresses:
        if interface['ifname'] == bridge:
            continue
        for item in interface.get('addr_info', []):
            if item.get('family') != 'inet':
                continue
            other = ipaddress.ip_network(f"{item['local']}/{item['prefixlen']}", strict=False)
            assert not any(other.overlaps(subnet) for subnet in subnets), f"NAT overlaps host interface {interface['ifname']}"
    for route in routes:
        if route.get('dev') == bridge or route.get('dst') in (None, 'default'):
            continue
        other = ipaddress.ip_network(route['dst'], strict=False)
        if other.version == 4:
            assert not any(other.overlaps(subnet) for subnet in subnets), 'NAT overlaps a host/VPN route'
    return {'state': 'PASS', 'network': network, 'forward': 'nat', 'bridge': bridge,
            'subnets': [str(subnet) for subnet in subnets], 'host_network_modified': False,
            'host_default_interfaces': sorted({route['dev'] for route in routes
                                               if route.get('dst') == 'default' and route.get('dev')})}


def check_domain(xml, network, download, upload):
    interfaces = ET.fromstring(xml).findall('devices/interface')
    assert len(interfaces) == 1, 'Runner must have exactly one network interface'
    interface = interfaces[0]
    assert interface.get('type') == 'network' and interface.find('source').get('network') == network
    assert interface.find('model').get('type') == 'virtio'
    inbound, outbound = interface.find('bandwidth/inbound'), interface.find('bandwidth/outbound')
    assert inbound is not None and outbound is not None, 'Guest bandwidth limits missing'
    assert inbound.get('average') == inbound.get('peak') == str(rate(download))
    assert outbound.get('average') == str(rate(upload))
    assert inbound.get('floor') is None, 'Guest limits must not reserve shared network bandwidth'
    target = interface.find('target')
    return {'state': 'PASS', 'network': network,
            'tap': target.get('dev') if target is not None else None,
            'guest_download_kib_per_second': rate(download),
            'guest_upload_kib_per_second': rate(upload), 'scope': 'one-disposable-guest-interface'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', default='default')
    parser.add_argument('--libvirt-uri', default='qemu:///system')
    parser.add_argument('--download-kib', type=rate, default=256)
    parser.add_argument('--upload-kib', type=rate, default=64)
    parser.add_argument('--userspace', action='store_true', help='current bridge-free SLIRP policy')
    parser.add_argument('--evidence', action='store_true', help='validate retained synthetic network probes without host access')
    parser.add_argument('--domain-xml', type=Path, help='check generated/live guest XML instead of host network admission')
    args = parser.parse_args()
    if args.evidence:
        report = check_retained_probes(Path(__file__).resolve().parents[1])
    elif args.userspace:
        safe_rates(args.download_kib, args.upload_kib)
        if args.domain_xml:
            report = check_userspace_domain(args.domain_xml.read_text())
        else:
            addresses = json.loads(subprocess.check_output(['ip', '-json', 'address', 'show'], text=True))
            routes = json.loads(subprocess.check_output(['ip', '-json', 'route', 'show', 'table', 'all'], text=True))
            report = check_userspace_host(addresses, routes)
            for device in report['host_default_interfaces']:
                driver = subprocess.check_output(['ethtool', '-i', device], text=True)
                if re.search(r'^driver: e1000e$', driver, re.M):
                    check_nic_features('e1000e', subprocess.check_output(['ethtool', '-k', device], text=True))
            report['e1000e_runtime_mitigation_checked'] = True
        report.update(guest_download_kib_per_second=args.download_kib, guest_upload_kib_per_second=args.upload_kib)
    elif args.domain_xml:
        report = check_domain(args.domain_xml.read_text(), args.network, args.download_kib, args.upload_kib)
    else:
        def read(*command):
            return subprocess.check_output(command, text=True)
        report = check_network(read('virsh', '--connect', args.libvirt_uri, 'net-dumpxml', args.network),
                               args.network, json.loads(read('ip', '-json', 'address', 'show')),
                               json.loads(read('ip', '-json', 'route', 'show', 'table', 'all')),
                               json.loads(read('ip', '-details', '-json', 'link', 'show')))
        report.update(guest_download_kib_per_second=args.download_kib,
                      guest_upload_kib_per_second=args.upload_kib)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
