# Host network safety

Current SupraLINUX gates use QEMU SLIRP with a private guest-only
`10.203.0.0/24` subnet. They create no host bridge, TAP, DHCP server, route or
libvirt network. The guest MAC exists only inside QEMU; external connections use
ordinary host sockets. Passt defaults, LAN bridges, direct interfaces, forwarded
host ports, extra interfaces and QEMU network overrides are rejected.

Boot with the virtual link disabled. Through the local guest-agent channel,
configure the disposable guest's nftables output/forward guards and traffic
controls before enabling that link or registering a JIT runner. Preserve guest
loopback and only the internal SLIRP DNS/DHCP services; reject external private,
link-local, multicast and IPv6 destinations. Apply guest egress TBF and an ingress
policer with maximum settings of 256 KiB/s download and 64 KiB/s upload. The
download policer uses TCP backpressure/retransmission; it is not a claim that
remote servers cannot send an initial burst. No bandwidth is reserved on the
physical host and no physical-interface tc/firewall setting is changed.

The observed e1000e host must have TSO and GSO disabled before any guest traffic.
The operator applied `sudo ethtool -K eno1 tso off gso off`; read-only verification
confirmed both off. This is a reversible runtime mitigation, not a kernel fix or
persistent host configuration. Revalidate after reboot; gates fail closed if
either feature is on. Do not change the physical NIC, modem, LAN addressing or
Docker networks from VM provisioning.
Host package installation and host firewall changes require the operator's
specific permission. The host provisioner fails closed without its explicit
installation flag, which an agent must not supply from general development
authorization. Existing host tools suffice for the current work. Guest nftables
and tc already exist in the preserved guest image; no host installation or host
firewall is needed for this policy.

On 2026-10-09 the user reported that both wired computers lost all connectivity
while modem Wi-Fi retained internet. The retained previous-boot journal contains
5,033 e1000e Hardware Unit Hang records: first at 13:19:21 UTC, last at
16:07:05 UTC. LibKSysGuard preflight finished at 13:19:17 UTC, four seconds before
the first hang, followed by Actions retention/host DNS timeouts. This timing
supports investigating transmit/NAT/offload behavior; it does not prove the exact
cause of the modem's wired outage. The upstream driver discussion reports TSO
workarounds for affected older e1000e devices; applicability to this I219-V host
remains a hypothesis, supported here by an actual matching hang symptom.

All 34 retained domain XML files available for this audit use libvirt network
interfaces. None has the MAC from the reported stale LAN ARP entry. This narrows
the audit and does not establish ownership or age of that neighbor entry.
The project-used `default` NAT definition, autostart and `virbr0` were removed
after checking the VM registry was empty and backing up XML. Stable LAN addresses
and routes were verified unchanged. Golden images, milestone caches, sealed gate
evidence and unrelated Docker networks remain preserved.

Original host journals, interface/route snapshots and domain/MAC inventory are
retained locally with hashes and a complete empty offline byte restore. Public
evidence records the findings and control hashes; the private host dumps remain
local. LibKSysGuard preflight 34's original PASS and complete sources/logs were
recovered unchanged from the sealed host after failed Actions transport. It
consumed no package Attempt and does not admit execution under the changed
network policy. Certify a small disposable KVM infrastructure probe, its internet
and private-network rejection, traffic controls and cleanup before a fresh
package preflight. No intentional network stress test is authorized by this fix.

Historical golden-image creation/lifecycle entrypoints still require the retired
libvirt transport. Do not execute them until their preparation path is adapted
and certified with the same policy. Existing sealed images remain unchanged.

The first small SLIRP probe on `446ec2e` ended INFRA_INVALID before link
activation: iproute2's police JSON omits its rate field. TBF JSON does contain
that field. The complete failure and cleanup are retained in
`manifests/evidence/host-network-safety/slirp-probe1`. No runner was registered,
no workflow or package execution started, and the host monitor observed no hang
or link loss. Verify the ingress policer's exact IEC text rate and JSON drop
action together before repeating the small probe; do not weaken its limit.

The second probe on `a4ea7898` verifies the actual 256/64 KiB/s controls but
fails at counter inspection before any private TCP or Internet probe. The
single-dash `nft -json` combines short flags, including stateless `-s`, yielding
null counters. Use the documented `--json` option and require real nonnegative
integer counter values. Both failures, exact stages, offline restores and owned
resource cleanup remain retained. No host hang or physical link loss was observed.
After these consecutive infrastructure failures, stop retries and certify the
diagnosed parser repair with a small owned probe before package execution.
See [nft output flags](https://netfilter.org/projects/nftables/manpage.html).

Sources: [libvirt SLIRP domain format](https://libvirt.org/formatdomain.html#userspace-connection-using-slirp),
[QEMU user networking](https://www.qemu.org/docs/master/system/qemu-manpage.html),
[upstream e1000e NAT/TSO report](https://lists.openwall.net/netdev/2019/05/09/40),
[Intel maintainer's scope caveat](https://lists.openwall.net/netdev/2019/05/22/65).
