#!/usr/bin/env python3
"""Admit current bridge-free SLIRP; retain the historical NAT checker for replay."""
import argparse
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
    parser.add_argument('--domain-xml', type=Path, help='check generated/live guest XML instead of host network admission')
    args = parser.parse_args()
    if args.userspace:
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
