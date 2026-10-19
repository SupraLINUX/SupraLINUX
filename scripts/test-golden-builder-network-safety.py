#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
builder = (ROOT / "scripts/build-authoritative-runner-image.sh").read_text()
preflight = (ROOT / "scripts/check-golden-build-network-preflight.sh").read_text()
guest = (ROOT / "scripts/configure-golden-bootstrap-network.py").read_text()
activation = (ROOT / "scripts/activate-golden-bootstrap-network.py").read_text()
digest = (ROOT / "scripts/golden-image-input-digest.sh").read_text()
broker = (ROOT / "scripts/supralinux-authoritative-host-broker.py").read_text()

for name, source in (("builder", builder), ("preflight", preflight)):
    for token in (
        "user,model=virtio,mac=52:54:00:53:55:01,link.state=down",
        "--channel unix,target.type=virtio,target.name=org.qemu.guest_agent.0",
        "scripts/activate-golden-bootstrap-network.py",
        "10.203.0.1",
        "network-config=",
    ):
        if token not in source:
            raise SystemExit(f"{name}: missing controlled golden-network contract: {token}")
    if "network=default" in source or "LIBVIRT_NETWORK},model=virtio" in source:
        raise SystemExit(f"{name}: retired libvirt NAT transport reintroduced")
    if "--activate-link" in source:
        raise SystemExit(f"{name}: guest must not control the hypervisor link")

for token in (
    '"down"',
    '"network-live-domain.xml"',
    '"--bootstrap"',
    '"domif-setlink"',
    'MAC, "up"',
    '"network-live-domain-enabled.xml"',
    '"--verify-network"',
):
    if token not in activation:
        raise SystemExit(f"activation controller missing ordering contract: {token}")
if activation.index('["golden-network", "--bootstrap"]') >= activation.index('"domif-setlink"'):
    raise SystemExit("guest isolation must PASS before the host enables SLIRP")
if activation.index('"domif-setlink"') >= activation.index('["golden-network", "--bootstrap", "--verify-network"]'):
    raise SystemExit("connectivity verification must run only after host link activation")

if "--activate-link" in guest or "networkctl', 'up'" in guest:
    raise SystemExit("golden guest helper must not be able to enable the hypervisor link")
if "Golden bootstrap mode is valid only before runner installation" not in guest:
    raise SystemExit("golden helper must remain restricted to pre-runner source guests")

for path in (
    "scripts/configure-golden-bootstrap-network.py",
    "scripts/activate-golden-bootstrap-network.py",
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
