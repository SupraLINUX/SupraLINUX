#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
builder = (ROOT / "scripts/build-authoritative-runner-image.sh").read_text()
preflight = (ROOT / "scripts/check-golden-build-network-preflight.sh").read_text()
guest = (ROOT / "scripts/configure-golden-bootstrap-network.py").read_text()
channel = (ROOT / "scripts/golden-bootstrap-channel.py").read_text()
activation = (ROOT / "scripts/activate-golden-bootstrap-network.py").read_text()
injector = (ROOT / "scripts/inject-golden-bootstrap-network.sh").read_text()
guard_unit = (ROOT / "ops/golden-bootstrap/supralinux-golden-bootstrap-guard.service").read_text()
verify_unit = (ROOT / "ops/golden-bootstrap/supralinux-golden-bootstrap-verify.service").read_text()
digest = (ROOT / "scripts/golden-image-input-digest.sh").read_text()
broker = (ROOT / "scripts/supralinux-authoritative-host-broker.py").read_text()

for name, source in (("builder", builder), ("preflight", preflight)):
    for token in (
        "user,model=virtio,mac=52:54:00:53:55:01,link.state=down",
        "org.supralinux.bootstrap.0",
        "bootstrap-channel.sock",
        "scripts/inject-golden-bootstrap-network.sh",
        "scripts/activate-golden-bootstrap-network.py",
        "--channel-socket",
        "10.203.0.1",
        "network-config=",
    ):
        if token not in source:
            raise SystemExit(f"{name}: missing controlled golden-network contract: {token}")
    if "network=default" in source or "LIBVIRT_NETWORK},model=virtio" in source:
        raise SystemExit(f"{name}: retired libvirt NAT transport reintroduced")
    if "org.qemu.guest_agent.0" in source:
        raise SystemExit(f"{name}: bootstrap must not depend on qemu-guest-agent")

for token in (
    "socket.AF_UNIX",
    '"READY"',
    '"VERIFIED"',
    '"domif-setlink"',
    'MAC, "up"',
    '"network-live-domain.xml"',
    '"network-live-domain-enabled.xml"',
):
    if token not in activation:
        raise SystemExit(f"activation controller missing ordering contract: {token}")
if "qemu-agent-command" in activation or "org.qemu.guest_agent.0" in activation:
    raise SystemExit("activation controller must not depend on qemu-guest-agent")
if activation.index('read_message(client, "READY"') >= activation.index('"domif-setlink"'):
    raise SystemExit("guest guard READY must be received before the host enables SLIRP")
if activation.index('"domif-setlink"') >= activation.index('read_message(client, "VERIFIED"'):
    raise SystemExit("connectivity verification must be received only after host link activation")

for token in (
    "--phase",
    "guard_phase",
    "verify_phase",
    "private_ipv4_and_external_ipv6_blocked",
    "private_reject_counter_delta",
    "bootstrap_cleanup",
    "/dev/virtio-ports/org.supralinux.bootstrap.0",
):
    if token not in channel:
        raise SystemExit(f"guest bootstrap channel missing contract: {token}")

for token in (
    "virt-customize",
    "--no-network",
    "supralinux-configure-golden-bootstrap-network.py",
    "supralinux-golden-bootstrap-channel.py",
    "supralinux-golden-bootstrap-guard.service",
    "supralinux-golden-bootstrap-verify.service",
    "command -v nft",
    "command -v tc",
):
    if token not in injector:
        raise SystemExit(f"offline bootstrap injector missing contract: {token}")

for token in (
    "DefaultDependencies=no",
    "Before=network-pre.target",
    "--phase guard",
    "WantedBy=sysinit.target",
    "RemainAfterExit=yes",
):
    if token not in guard_unit:
        raise SystemExit(f"guard unit missing early-boot contract: {token}")

for token in (
    "After=supralinux-golden-bootstrap-guard.service network.target",
    "--phase verify",
    "WantedBy=multi-user.target",
):
    if token not in verify_unit:
        raise SystemExit(f"verification unit missing post-link contract: {token}")

if "--activate-link" in guest or "networkctl', 'up'" in guest:
    raise SystemExit("golden guest network helper must not be able to enable the hypervisor link")
if "Golden bootstrap mode is valid only before runner installation" not in guest:
    raise SystemExit("golden helper must remain restricted to pre-runner source guests")

for path in (
    "scripts/configure-golden-bootstrap-network.py",
    "scripts/golden-bootstrap-channel.py",
    "scripts/activate-golden-bootstrap-network.py",
    "scripts/inject-golden-bootstrap-network.sh",
    "ops/golden-bootstrap/supralinux-golden-bootstrap-guard.service",
    "ops/golden-bootstrap/supralinux-golden-bootstrap-verify.service",
):
    if path not in digest:
        raise SystemExit(f"golden fingerprint missing execution input: {path}")

preflight_pos = broker.index('["scripts/check-golden-build-network-preflight.sh"]')
builder_pos = broker.index('["scripts/build-authoritative-runner-image.sh"]')
if preflight_pos >= builder_pos:
    raise SystemExit("small golden-network certification must run before full golden rebuild")
if '"golden_rebuild_started=no"' not in broker:
    raise SystemExit("failed network preflight must prove the full rebuild did not start")

print("Golden builder controlled SLIRP bootstrap contract: PASS")
