#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERTIFIER = ROOT / "scripts/certify-supralinux-proposed-signing.py"
BUILDER = ROOT / "scripts/build-supralinux-proposed.py"
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"
CONTENT_CERTIFICATION = ROOT / "manifests/supralinux-proposed-content-certification.json"
SIGNING_CERTIFICATION = ROOT / "manifests/supralinux-proposed-signing-certification.json"
SIGNING_EVIDENCE = ROOT / "manifests/evidence/infrastructure/supralinux-proposed-signing-certification-20261028/result.json"
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


sealed_signing = json.loads(SIGNING_CERTIFICATION.read_text())
signing_evidence_bytes = SIGNING_EVIDENCE.read_bytes()
signing_evidence = json.loads(signing_evidence_bytes)

if sealed_signing["state"] != "PASS":
    raise SystemExit("sealed proposed signing certification is not PASS")
if sealed_signing["certification"]["workflow_run_id"] != 40639991710:
    raise SystemExit("unexpected proposed signing certification run")
if sealed_signing["certification"]["workflow_job_id"] != 122656052744:
    raise SystemExit("unexpected proposed signing certification job")
if sealed_signing["certification"]["artifact_id"] != 12794773020:
    raise SystemExit("unexpected proposed signing certification artifact")
if sealed_signing["certification"]["artifact_sha256"] != "a2fcbd57760c50ecd91544793502f88d03b80d6dfe3e12cce77791216e9eac96":
    raise SystemExit("unexpected proposed signing certification artifact digest")
if hashlib.sha256(signing_evidence_bytes).hexdigest() != sealed_signing["certification"]["result_sha256"]:
    raise SystemExit("proposed signing certification evidence digest mismatch")

for key in (
    "repository_manifest_sha256",
    "plan_sha256",
    "packages_sha256",
    "sources_sha256",
    "release_sha256",
    "public_key_sha256",
    "inrelease_sha256",
    "release_gpg_sha256",
    "signing_fingerprint",
):
    if signing_evidence[key] != sealed_signing["certification"][key]:
        raise SystemExit(f"proposed signing certification field mismatch: {key}")

if signing_evidence["sealed_content_result_sha256"] != sealed_signing["sealed_content"]["result_sha256"]:
    raise SystemExit("signed certification no longer chains to sealed unsigned content")
if signing_evidence["sealed_content_source_commit"] != sealed_signing["sealed_content"]["source_commit"]:
    raise SystemExit("signed certification content source commit mismatch")
if signing_evidence["candidate_count"] != sealed_signing["sealed_content"]["candidate_count"] != 24:
    raise SystemExit("signed certification candidate count drifted")
if signing_evidence["frameworks_pass_nodes"] != sealed_signing["sealed_content"]["frameworks_pass_nodes"] != 65:
    raise SystemExit("signed certification Frameworks base drifted")

for key, expected in (
    ("signed", True),
    ("ephemeral_signing_key", True),
    ("private_signing_key_retained", False),
    ("builder_activation_eligible", False),
    ("production_activation_eligible", False),
    ("repository_active", False),
    ("stable_publication_authorized", False),
    ("package_attempt_consumed", False),
    ("sbuild_invoked", False),
    ("vm_created", False),
    ("jit_invoked", False),
    ("network_required", False),
):
    if signing_evidence[key] is not expected:
        raise SystemExit(f"proposed signing certification invariant mismatch: {key}")
if signing_evidence["signature_verification"] != "PASS":
    raise SystemExit("proposed signing certification signature verification is not PASS")
if signing_evidence["canonical_package_state_effect"] != "none":
    raise SystemExit("proposed signing certification changed canonical package state")
if sealed_signing["verification"]["artifact_contains_private_key_material"] is not False:
    raise SystemExit("sealed proposed signing artifact claims private key material")
if sealed_signing["rollout"]["phase_completed"] != "ephemeral-signing-certification":
    raise SystemExit("proposed signing certification rollout phase drifted")
if sealed_signing["rollout"]["production_activation_changed"] is not False:
    raise SystemExit("proposed signing certification changed production activation")

print("SupraLINUX-proposed ephemeral signing certification contract: PASS")
