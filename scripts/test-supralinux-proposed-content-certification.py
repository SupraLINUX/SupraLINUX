#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/certify-supralinux-proposed-content.py"
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"
CERTIFICATION_MANIFEST = ROOT / "manifests/supralinux-proposed-content-certification.json"
CERTIFICATION_EVIDENCE = ROOT / "manifests/evidence/infrastructure/supralinux-proposed-content-certification-20261028/result.json"

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
    'PREFERRED_FRAMEWORKS_RETAINED_ARTIFACT_ROOT = Path("/var/lib/supralinux/milestone-cache/frameworks-6.30/retained-artifacts")',
    'Path(operator.pw_dir) / "src/SupraLINUX/.artifacts/frameworks-6.30"',
    'def resolve_frameworks_retained_artifact_root() -> Path:',
    'frameworks_archive = resolve_frameworks_retained_artifact_root()',
    '"--frameworks-archive", str(frameworks_archive)',
    'prepare_control_checkout(proposed_checkout)',
):
    if token not in broker:
        raise SystemExit(f"missing proposed host certification contract: {token}")

cert_pos = broker.index('if request["mode"] == "certify-proposed-content":')
kvm_pos = broker.index('libvirt_group = pwd.getpwnam("libvirt-qemu").pw_gid')
if cert_pos >= kvm_pos:
    raise SystemExit("proposed content certification must return before KVM admission")


certification = json.loads(CERTIFICATION_MANIFEST.read_text())
evidence_bytes = CERTIFICATION_EVIDENCE.read_bytes()
evidence = json.loads(evidence_bytes)
assert certification["state"] == "PASS"
assert certification["certification"]["workflow_run_id"] == 40637977168
assert certification["certification"]["workflow_job_id"] == 122649711388
assert certification["certification"]["artifact_id"] == 12794456859
assert certification["certification"]["artifact_sha256"] == "82a4dfa6bc2688ef3e2ebaa65fbf2279596a6aa4f862f1b085b9b29a0e78a5c1"
assert certification["certification"]["source_commit"] == "f0b30cb58ab690f59133e69bf385fdb17fef38dd"
assert certification["certification"]["evidence_path"] == str(CERTIFICATION_EVIDENCE.relative_to(ROOT))
assert hashlib.sha256(evidence_bytes).hexdigest() == certification["certification"]["result_sha256"]
for key in (
    "plan_sha256",
    "repository_manifest_sha256",
    "packages_sha256",
    "sources_sha256",
    "release_sha256",
):
    assert evidence[key] == certification["certification"][key]
assert evidence["state"] == "PASS"
assert evidence["candidate_count"] == certification["coverage"]["plasma_candidates"] == 24
assert evidence["excluded_count"] == certification["coverage"]["excluded_candidates"] == 3
assert evidence["frameworks_pass_nodes"] == certification["coverage"]["frameworks_pass_nodes"] == 65
assert evidence["frameworks_artifacts_verified"] == certification["coverage"]["frameworks_artifacts_verified"] == 65
assert evidence["signed"] is certification["invariants"]["signed"] is False
assert evidence["activation_eligible"] is certification["invariants"]["activation_eligible"] is False
assert evidence["repository_active"] is certification["invariants"]["repository_active"] is False
assert evidence["stable_publication_authorized"] is certification["invariants"]["stable_publication_authorized"] is False
assert evidence["canonical_package_state_effect"] == certification["invariants"]["canonical_package_state_effect"] == "none"
assert evidence["package_attempt_consumed"] is certification["invariants"]["package_attempt_consumed"] is False
assert evidence["sbuild_invoked"] is certification["invariants"]["sbuild_invoked"] is False
assert evidence["vm_created"] is certification["invariants"]["vm_created"] is False
assert evidence["jit_invoked"] is certification["invariants"]["jit_invoked"] is False
assert evidence["network_required"] is certification["invariants"]["network_required"] is False
assert certification["rollout"]["production_activation_changed"] is False
assert certification["rollout"]["phase_completed"] == "unsigned-content-certification"

print("SupraLINUX-proposed content certification contract: PASS")
