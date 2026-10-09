#!/usr/bin/env python3
"""Reject network choices that could interfere with the operator's connection."""
import copy
import importlib.machinery
import unittest
from pathlib import Path

MODULE = importlib.machinery.SourceFileLoader('network_guard', str(Path(__file__).with_name('check-kvm-network.py'))).load_module()
GUEST = importlib.machinery.SourceFileLoader('guest_guard', str(Path(__file__).with_name('configure-kvm-guest-network.py'))).load_module()
NETWORK = """<network><name>default</name><forward mode='nat'/><bridge name='virbr0'/>
<ip address='192.168.122.1' netmask='255.255.255.0'><dhcp>
<range start='192.168.122.2' end='192.168.122.254'/></dhcp></ip></network>"""
DOMAIN = """<domain><devices><interface type='network'><source network='default'/>
<model type='virtio'/><target dev='vnet7'/><bandwidth><inbound average='256' peak='256'/>
<outbound average='128'/></bandwidth></interface></devices></domain>"""
USER_DOMAIN = """<domain><devices><interface type='user'><mac address='52:54:00:53:55:01'/>
<model type='virtio'/><ip family='ipv4' address='10.203.0.1' prefix='24'/><link state='down'/>
</interface></devices></domain>"""


class NetworkTests(unittest.TestCase):
    def test_police_rate_is_verified_from_exact_iec_text_when_json_omits_it(self):
        filters = [{'options': {'actions': [{'kind': 'police', 'control_action': {'type': 'drop'}}]}}]
        text = 'action order 1: police 0x1 rate 2Mibit burst 8Kb mtu 2Kb action drop/ok'
        GUEST.verify_police(filters, text, 256 * 1024)
        for invalid in [text.replace('2Mibit', '4Mibit'), text.replace('2Mibit', '2097Kbit'), '', text+'\n'+text]:
            with self.subTest(text=invalid), self.assertRaises(AssertionError):
                GUEST.verify_police(filters, invalid, 256 * 1024)
        filters[0]['options']['actions'][0]['control_action']['type'] = 'ok'
        with self.assertRaises(AssertionError):
            GUEST.verify_police(filters, text, 256 * 1024)

    def fixture(self):
        addresses = [{'ifname': 'virbr0', 'addr_info': [{'family': 'inet', 'local': '192.168.122.1', 'prefixlen': 24}]},
                     {'ifname': 'eno1', 'addr_info': [{'family': 'inet', 'local': '192.168.1.41', 'prefixlen': 24}]}]
        routes = [{'dst': 'default', 'dev': 'eno1'}, {'dst': '192.168.1.0/24', 'dev': 'eno1'},
                  {'dst': '192.168.122.0/24', 'dev': 'virbr0'}]
        links = [{'ifname': 'virbr0', 'ifindex': 3, 'linkinfo': {'info_kind': 'bridge'}},
                 {'ifname': 'eno1', 'ifindex': 2}]
        return addresses, routes, links

    def check(self, xml=NETWORK, values=None):
        return MODULE.check_network(xml, 'default', *(values or self.fixture()))

    def test_existing_nat_and_guest_ports_are_admitted_without_mutation(self):
        values = self.fixture()
        values[2].append({'ifname': 'vnet7', 'ifindex': 7, 'master': 'virbr0', 'linkinfo': {'info_kind': 'tun'}})
        before = copy.deepcopy(values)
        report = self.check(values=values)
        self.assertEqual(report['subnets'], ['192.168.122.0/24'])
        self.assertFalse(report['host_network_modified'])
        self.assertEqual(before, values)

    def test_bridge_route_and_direct_modes_are_rejected(self):
        for mode in ['bridge', 'route', 'open', 'hostdev', 'passthrough', 'private']:
            with self.subTest(mode=mode), self.assertRaises(AssertionError):
                self.check(NETWORK.replace("mode='nat'", f"mode='{mode}'"))

    def test_overlapping_lan_and_vpn_are_rejected(self):
        for kind in ['address', 'route']:
            values = self.fixture()
            if kind == 'address':
                values[0][1]['addr_info'][0]['local'] = '192.168.122.41'
            else:
                values[1].append({'dst': '192.168.0.0/16', 'dev': 'tun0'})
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                self.check(values=values)

    def test_physical_bridge_port_and_host_default_route_are_rejected(self):
        for kind in ['port', 'default']:
            values = self.fixture()
            if kind == 'port':
                values[2][1]['master'] = 3
            else:
                values[1][0]['dev'] = 'virbr0'
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                self.check(values=values)

    def test_missing_or_different_bridge_is_rejected(self):
        for kind in ['missing', 'wrong-kind', 'wrong-address']:
            values = self.fixture()
            if kind == 'missing':
                values[2].pop(0)
            elif kind == 'wrong-kind':
                values[2][0]['linkinfo']['info_kind'] = 'vlan'
            else:
                values[0][0]['addr_info'][0]['prefixlen'] = 16
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                self.check(values=values)

    def test_dhcp_escape_ipv6_and_public_subnet_are_rejected(self):
        for xml in [NETWORK.replace("end='192.168.122.254'", "end='192.168.1.254'"),
                    NETWORK.replace('<ip address=', "<ip family='ipv6' address="),
                    NETWORK.replace('192.168.122.', '203.0.113.')]:
            with self.subTest(xml=xml), self.assertRaises(AssertionError):
                self.check(xml)

    def test_unsafe_network_name_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.check_network(NETWORK, 'default,bridge=eno1', *self.fixture())

    def test_zero_negative_fractional_or_expression_rate_is_rejected(self):
        for value in ['0', '-1', '1.5', '256,bridge=eno1', '1e3']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.rate(value)

    def test_generated_and_live_xml_have_both_guest_limits(self):
        report = MODULE.check_domain(DOMAIN, 'default', 256, 128)
        self.assertEqual(report['tap'], 'vnet7')
        self.assertEqual(report['guest_download_kib_per_second'], 256)
        self.assertEqual(report['guest_upload_kib_per_second'], 128)

    def test_wrong_network_multiple_interfaces_or_missing_limits_fail_closed(self):
        for xml in [DOMAIN.replace("network='default'", "network='lan'"),
                    DOMAIN.replace('</devices>', "<interface type='direct'/></devices>"),
                    DOMAIN.replace("<outbound average='128'/>", ''),
                    DOMAIN.replace("peak='256'", "peak='1024'"),
                    DOMAIN.replace("average='128'", "average='512'")]:
            with self.subTest(xml=xml), self.assertRaises(AssertionError):
                MODULE.check_domain(xml, 'default', 256, 128)

    def test_bridge_free_domain_does_not_require_host_networks(self):
        report = MODULE.check_userspace_domain(USER_DOMAIN)
        self.assertFalse(report['host_bridge_or_tap_required'])
        self.assertEqual(report['guest_link'], 'down')
        report = MODULE.check_userspace_host(self.fixture()[0][1:], self.fixture()[1][:2])
        self.assertFalse(report['host_network_modified'])

    def test_current_domain_rejects_lan_modes_forwarding_and_overrides(self):
        for xml in [USER_DOMAIN.replace("type='user'", f"type='{mode}'") for mode in ['network', 'bridge', 'direct', 'ethernet', 'hostdev', 'vhostuser']]:
            with self.subTest(xml=xml), self.assertRaises(AssertionError):
                MODULE.check_userspace_domain(xml)
        for extra in ["<backend type='passt'/>", "<target dev='vnet1'/>", "<source network='default'/>",
                      "<portForward proto='tcp'/>", "<bandwidth/>"]:
            with self.subTest(extra=extra), self.assertRaises(AssertionError):
                MODULE.check_userspace_domain(USER_DOMAIN.replace('</interface>', extra+'</interface>'))
        xml=USER_DOMAIN.replace('<domain>', '<domain xmlns:qemu="http://libvirt.org/schemas/domain/qemu/1.0">')
        for override in ['-netdev', '-nic', 'hostfwd=tcp::22-:22']:
            with self.subTest(override=override), self.assertRaises(AssertionError):
                MODULE.check_userspace_domain(xml.replace('</domain>', f'<qemu:commandline><qemu:arg value="{override}"/></qemu:commandline></domain>'))

    def test_current_domain_rejects_foreign_mac_subnet_and_extra_nics(self):
        for xml in [USER_DOMAIN.replace('52:54:00:53:55:01','2e:fe:7b:59:a5:6f'),
                    USER_DOMAIN.replace('10.203.0.1','192.168.1.36'),
                    USER_DOMAIN.replace('</devices>', '<interface type="user"/></devices>'),
                    USER_DOMAIN.replace('</devices>', '<hostdev/></devices>')]:
            with self.subTest(xml=xml), self.assertRaises(AssertionError):
                MODULE.check_userspace_domain(xml)

    def test_current_guest_subnet_rejects_host_and_vpn_overlap(self):
        for addresses,routes in [([{'ifname':'vpn','addr_info':[{'family':'inet','local':'10.203.0.10','prefixlen':24}]}],[]),
                                 ([],[{'dst':'10.0.0.0/8','dev':'vpn'}])]:
            with self.subTest(addresses=addresses,routes=routes), self.assertRaises(AssertionError):
                MODULE.check_userspace_host(addresses,routes)

    def test_runtime_rates_cannot_repeat_previous_large_overrides(self):
        self.assertEqual(MODULE.safe_rates(256,64),(256,64))
        for down,up in [(4096,512),(257,64),(256,65),(0,64),(256,-1)]:
            with self.subTest(down=down,up=up), self.assertRaises((AssertionError,ValueError)):
                MODULE.safe_rates(down,up)

    def test_observed_e1000e_hang_requires_runtime_mitigation(self):
        off='tcp-segmentation-offload: off\ngeneric-segmentation-offload: off\n'
        MODULE.check_nic_features('e1000e',off)
        for features in [off.replace('tcp-segmentation-offload: off','tcp-segmentation-offload: on'),
                         off.replace('generic-segmentation-offload: off','generic-segmentation-offload: on'),'']:
            with self.subTest(features=features), self.assertRaises(AssertionError):
                MODULE.check_nic_features('e1000e',features)


if __name__ == '__main__':
    unittest.main()
