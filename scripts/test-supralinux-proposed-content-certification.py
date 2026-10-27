#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/certify-supralinux-proposed-content.py"
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"

helper = HELPER.read_text()
broker = BROKER.read_text()

for token in (
    '"--unsigned-certification"',
    '"artifact_root_persistent": True',
    '"--frameworks-archive"',
    '"frameworks_archive_host_root": str(frameworks_archive)',
    '"frameworks_archive_logical_root": retained["archive_root"]',
    '"frameworks_artifacts_verified": verified_frameworks',
    '"frameworks_requires_github_for_restore": False',
    '"manifests/retained-package-artifacts.json"',
    'sha256(frameworks_index) != retained["archive_index_sha256"]',
    'archive_path.parts != ("sha256", f"{digest}.zip")',
    '"network_required": False',
    '"package_attempt_consumed": False',
    '"sbuild_invoked": False',
    '"vm_created": False',
    '"jit_invoked": False',
    '"activation_eligible": False',
    '"repository_active": False',
    '"stable_publication_authorized": False',
    '"canonical_package_state_effect": "none"',
    '"dpkg-deb"',
    '"git"',
    "scripts/plan-supralinux-proposed.py",
    "scripts/build-supralinux-proposed.py",
    'if built != planned:',
):
    if token not in helper:
        raise SystemExit(f"missing proposed content certification contract: {token}")

for forbidden in ("apt-ftparchive", "curl", "wget", "gh api", "--signing-key"):
    if forbidden in helper:
        raise SystemExit(f"proposed content certification must remain offline/unsigned: {forbidden}")

for token in (
    'if request["mode"] == "certify-proposed-content":',
    '"gate=supralinux-proposed"',
    '"scope=supralinux-proposed-content-certification"',
    '"repository_active=no"',
    '"stable_publication_authorized=no"',
    '"vm_created=no"',
    '"jit_invoked=no"',
    '"sbuild_invoked=no"',
    '"package_attempt_effect=none"',
    'PERSISTENT_ARTIFACT_ROOT',
    'FRAMEWORKS_RETAINED_ARTIFACT_ROOT = Path("/var/lib/supralinux/milestone-cache/frameworks-6.30/retained-artifacts")',
    '"--frameworks-archive", str(FRAMEWORKS_RETAINED_ARTIFACT_ROOT)',
    'prepare_control_checkout(proposed_checkout)',
):
    if token not in broker:
        raise SystemExit(f"missing proposed host certification contract: {token}")

cert_pos = broker.index('if request["mode"] == "certify-proposed-content":')
kvm_pos = broker.index('libvirt_group = pwd.getpwnam("libvirt-qemu").pw_gid')
if cert_pos >= kvm_pos:
    raise SystemExit("proposed content certification must return before KVM admission")

print("SupraLINUX-proposed content certification contract: PASS")
