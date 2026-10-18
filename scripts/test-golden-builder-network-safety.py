#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
builder = (ROOT / "scripts/build-authoritative-runner-image.sh").read_text()
preflight = (ROOT / "scripts/check-golden-build-network-preflight.sh").read_text()
guest = (ROOT / "scripts/configure-kvm-guest-network.py").read_text()
digest = (ROOT / "scripts/golden-image-input-digest.sh").read_text()
broker = (ROOT / "scripts/supralinux-authoritative-host-broker.py").read_text()

for name, source in (("builder", builder), ("preflight", preflight)):
    for token in (
        "activation-mode: manual",
        "--bootstrap, --activate-link",
        "--bootstrap --verify-network",
        "user,model=virtio,mac=52:54:00:53:55:01",
        "10.203.0.1",
        "network-config=",
    ):
        if token not in source:
            raise SystemExit(f"{name}: missing controlled golden-network contract: {token}")
    if "LIBVIRT_NETWORK},model=virtio" in source or "network=default" in source:
        raise SystemExit(f"{name}: retired libvirt NAT transport reintroduced")

if "SUPRALINUX_LIBVIRT_NETWORK" not in builder or "refuses libvirt network overrides" not in builder:
    raise SystemExit("builder must fail closed on libvirt network overrides")
if "scripts/configure-kvm-guest-network.py" not in digest:
    raise SystemExit("golden fingerprint must include the guest network guard")
for token in ("--bootstrap", "--activate-link",
              "Golden bootstrap mode is valid only before runner installation",
              "networkctl', 'up'"):
    if token not in guest:
        raise SystemExit(f"guest guard missing golden bootstrap contract: {token}")

preflight_pos = broker.index('["scripts/check-golden-build-network-preflight.sh"]')
builder_pos = broker.index('["scripts/build-authoritative-runner-image.sh"]')
if preflight_pos >= builder_pos:
    raise SystemExit("small golden-network certification must run before full golden rebuild")
if '"golden_rebuild_started=no"' not in broker:
    raise SystemExit("failed network preflight must prove the full rebuild did not start")

print("Golden builder controlled SLIRP bootstrap contract: PASS")
