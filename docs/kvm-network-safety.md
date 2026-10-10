# Host network safety

Current SupraLINUX gates use QEMU SLIRP with a private guest-only
`10.203.0.0/24` subnet. They create no host bridge, TAP, DHCP server, route or
libvirt network. The guest MAC exists only inside QEMU; external connections use
ordinary host sockets. Passt defaults, LAN bridges, direct interfaces, forwarded
host ports, extra interfaces and QEMU network overrides are rejected.

Boot with the virtual link disabled. Through the local guest-agent channel,
configure the disposable guest's nftables output/forward guards before enabling
that link or registering a JIT runner. Preserve guest
loopback and only the internal SLIRP DNS/DHCP services; reject external private,
link-local, multicast and IPv6 destinations. The operator clarified on
2026-10-10 that safe network configuration is required and Internet speed caps
are unnecessary. New provisioning therefore defaults to both traffic values
being zero, meaning no bandwidth limit. It installs no tc shaper/policer and
verifies their absence; guest isolation remains mandatory. Positive historical
256/64 KiB/s controls remain supported for intentional reproduction, with their
original ceilings and receipts preserved. No physical-interface tc/firewall
setting is changed. The new default is certified by the bounded real KVM probe
`slirp-unlimited-startup-20261010` on `ba4adc5c` and the fresh LibKSysGuard input
preflight 38 on that same source. Both verify zero configured bandwidth limits,
the absence of guest shaper/policer rules, private TCP rejection and bounded
HTTPS connectivity before runner registration. The unchanged guest nftables
source has SHA-256 `8f46d111dc8fe895a27c29ac7ba899f70fb4a31f5f4ed2d796d3e95b3d63b982`.
Direct checks confirm both owned VMs, runners 265/266 and writable overlays were
removed; golden and milestone images remain intact. The small probe has 12
kernel/carrier observations and one late gateway observation; preflight 38 has
54 kernel/carrier and 13 gateway observations. No hang, carrier loss or sampled
gateway failure was observed. This scoped result does not establish the cause
of the earlier wired outage. Complete sealed inputs restore offline unchanged.
No throughput stress test is authorized.

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

The historical golden-image builder still requires the retired libvirt
transport and must not execute. The preparation lifecycle has been adapted to
offline NoCloud boot with no virtual NIC and is certified by the actual
`offline-golden-lifecycle-20261010` probe on `f5e3392f`. The signed Ubuntu source
image remains byte-identical, the guest persists its PASS marker and powers off,
and direct checks confirm VM, overlay and temporary seed ISO absence. All 19
original source/host/operator proof files restore offline unchanged. This
synthetic lifecycle certification does not admit the legacy full golden-image
builder. Existing sealed images remain unchanged.

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

The repaired mechanism is certified PASS by `slirp-probe3` on `b9a8d86d`.
The actual KVM guest receives `10.203.0.15/24`, verifies the 256/64 KiB/s
policer/shaper, rejects both private TCP probes with separate guest-local
counter increments, completes a bounded HTTPS request and brings JIT runner
259 online without triggering a workflow. The host monitor records no hardware
hang or physical link loss during this small probe. Direct post-gate checks
confirm VM, runner and writable overlay absence, preserved golden image,
no libvirt networks, and TSO/GSO still off. Complete sealed host/observer evidence
restores offline unchanged. The two original infrastructure failures remain
append-only. This limited certification permits the fresh package input
preflight; it does not prove the cause of the earlier wired outage or certify
package compilation and application tests.

The following package gate on `4977c700` repeated those small controls but
stalled in Actions job setup with connection timeouts. A bounded 10,370-byte
TLS read succeeded in 2.33 seconds while the ingress policer recorded three
additional drops. The run was intentionally cancelled before checkout or
package preparation. Original GitHub job metadata, the empty workspace,
sealed host, monitor, diagnostic and direct runner 260/VM/overlay cleanup are
retained as an INFRA_INVALID startup observation, not an original package result.
No package Attempt was consumed and the campaign remains in preflight mode.

The 8 KiB bucket can reject coalesced TCP payloads even below the average
rate. The proposed guest-only repair keeps the 256/64 KiB/s rates, explicitly
admits packet accounting up to 65,535 bytes and uses a bounded 128 KiB ingress
bucket. This is half a second of the admitted download rate, not a higher rate
or reserved physical bandwidth. The next small certification additionally
requires a bounded 4–16 KiB HTTPS body without any policer drop during that read,
then JIT startup and owned cleanup. The earlier limited certification and all
failure observations remain immutable; this revised bulk-delivery path is not
yet admitted. See [Linux policing implementation](https://github.com/torvalds/linux/blob/master/net/sched/act_police.c).

The revised path is certified PASS by `slirp-probe4` on `56bd9204`.
The same 10,370-byte HTTPS body completes in 0.223 seconds with zero additional
policer drops, compared with 2.333 seconds and three drops in the earlier
diagnostic. Actual average limits remain 256/64 KiB/s and the loaded ingress
bucket is 128 KiB. Both private probes increment their guest rejection counters;
JIT runner 261 comes online, then direct cleanup verifies runner/VM/overlay
absence. The complete sealed evidence restores offline unchanged. The host
monitor sees no hardware hang or carrier loss. This closes the scoped delivery
repair and permits a new clean package input preflight; it is not a physical
network stress test or a package/application certification.

Sources: [libvirt SLIRP domain format](https://libvirt.org/formatdomain.html#userspace-connection-using-slirp),
[QEMU user networking](https://www.qemu.org/docs/master/system/qemu-manpage.html),
[upstream e1000e NAT/TSO report](https://lists.openwall.net/netdev/2019/05/09/40),
[Intel maintainer's scope caveat](https://lists.openwall.net/netdev/2019/05/22/65).

The following real input preflight starts its original input execution on `653323d4`
but stops at predecessor archive transport: its shared API reader imposes a
30-second total timeout on a 13,510,034-byte binary body. Even the maximum
admitted download rate requires more than 51 seconds for that body; actual
reads receive roughly 2.2–2.4 MB before timeout. This is a read-budget mismatch,
not a candidate build result. Network controls remain unchanged. Exact artifact
URLs receive a finite 900-second budget with at most three attempts and a
60-second low-speed guard; ordinary metadata reads keep their 30-second limit.
Failed partial bodies are withheld and Python failures report only transport
exit status. The preflight's original evidence remains immutable; actual new
artifact transport and baseline tests are required for current admission.
