#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERTIFIER = ROOT / "scripts/certify-supralinux-proposed-signing.py"
BUILDER = ROOT / "scripts/build-supralinux-proposed.py"
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"
CONTENT_CERTIFICATION = ROOT / "manifests/supralinux-proposed-content-certification.json"
CONFIG = ROOT / "manifests/supralinux-proposed.json"

certifier = CERTIFIER.read_text()
builder = BUILDER.read_text()
broker = BROKER.read_text()
compile(certifier, str(CERTIFIER), "exec")

for token in (
    '"--signed-certification"',
    '"GNUPGHOME"',
    '"--quick-generate-key"',
    '"ed25519"',
    '"gpgv"',
    '"certification-public-key.gpg"',
    '"signed certification plan differs from sealed unsigned content plan"',
    '"signed proposed Packages digest differs from sealed content"',
    '"signed proposed Sources digest differs from sealed content"',
    '"signed proposed Release digest differs from sealed content"',
    '"signature_verification": "PASS"',
    '"builder_activation_eligible": False',
    '"production_activation_eligible": False',
    '"repository_active": False',
    '"ephemeral_signing_key": True',
    '"private_signing_key_retained": False',
    '"stable_publication_authorized": False',
    '"package_attempt_consumed": False',
    '"sbuild_invoked": False',
    '"vm_created": False',
    '"jit_invoked": False',
    '"network_required": False',
):
    if token not in certifier:
        raise SystemExit(f"missing proposed signing certification contract: {token}")

for forbidden in ("apt-key", "trusted=yes", "allow-unauthenticated", "execute-and-publish-pass"):
    if forbidden in certifier:
        raise SystemExit(f"unsafe proposed signing certification behavior: {forbidden}")

for token in (
    'parser.add_argument("--signed-certification", action="store_true")',
    '"signed certification requires --signing-key"',
    '"certification_mode": certification_mode',
    '"activation_eligible": signing is not None and not args.signed_certification',
):
    if token not in builder:
        raise SystemExit(f"builder misses signed-certification isolation: {token}")

for token in (
    'if request["mode"] == "certify-proposed-signing":',
    '"scope=supralinux-proposed-signing-certification"',
    '"repository_active=no"',
    '"production_activation_eligible=no"',
    '"private_signing_key_retained=no"',
    '"stable_publication_authorized=no"',
    '"vm_created=no"',
    '"jit_invoked=no"',
    '"sbuild_invoked=no"',
    '"package_attempt_effect=none"',
):
    if token not in broker:
        raise SystemExit(f"broker misses proposed signing certification contract: {token}")

signing_pos = broker.index('if request["mode"] == "certify-proposed-signing":')
kvm_pos = broker.index('libvirt_group = pwd.getpwnam("libvirt-qemu").pw_gid')
if signing_pos >= kvm_pos:
    raise SystemExit("proposed signing certification must return before KVM admission")

content = json.loads(CONTENT_CERTIFICATION.read_text())
if not (
    content["state"] == "PASS"
    and content["rollout"]["phase_completed"] == "unsigned-content-certification"
    and content["invariants"]["signed"] is False
    and content["invariants"]["repository_active"] is False
):
    raise SystemExit("signed certification requires sealed unsigned content PASS")

config = json.loads(CONFIG.read_text())
if config["rollout"]["phase_3"] != "sign ephemeral certification repo with dedicated test key":
    raise SystemExit("SupraLINUX-proposed phase 3 contract drifted")
if config["active"] is not False:
    raise SystemExit("SupraLINUX-proposed became active before signing certification")

print("SupraLINUX-proposed ephemeral signing certification contract: PASS")
