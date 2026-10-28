#!/usr/bin/env python3
import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"manifests/supralinux-proposed-integration.json"
PREPARE=ROOT/"scripts/prepare-supralinux-proposed-integration-payload.py"
RUNNER=ROOT/"scripts/run-authoritative-supralinux-proposed-integration.sh"
JIT=ROOT/"scripts/run-kvm-jit-gate-core.sh"
BROKER=ROOT/"scripts/supralinux-authoritative-host-broker.py"
WORKFLOW=ROOT/".github/workflows/authoritative-supralinux-proposed-integration.yml"
manifest=json.loads(MANIFEST.read_text()); prepare=PREPARE.read_text(); runner=RUNNER.read_text(); jit=JIT.read_text(); broker=BROKER.read_text(); workflow=WORKFLOW.read_text(); ast.parse(prepare)
if not (manifest["state"]=="prepared-inactive" and manifest["gate"]=="supralinux-proposed-integration" and manifest["base_checkpoint"]=="frameworks-6.30-pass" and manifest["proposed_candidates"]==24 and manifest["frameworks_pass_nodes"]==65 and manifest["promotion"]["authorized"] is False and manifest["invariants"]["package_attempt_consumed"] is False and manifest["invariants"]["sbuild_invoked"] is False):
    raise SystemExit("invalid proposed integration manifest contract")
for gate in ("upgrade_from_ubuntu","abi_and_plugins","representative_apps","wayland_session","integration_image"):
    if manifest["certification_scope"][gate]!="NOT_RUN": raise SystemExit(f"future integration gate was silently pre-certified: {gate}")
for token in ("manifests/supralinux-proposed-signing-certification.json","scripts/check-frameworks-milestone-image.sh","frameworks-milestone-execution-cache","framework_packages_preinstalled_in_sbuild_rootfs","scripts/plan-supralinux-proposed.py","--signed-certification","gpgv","private_signing_key_retained","production_activation_eligible","install-seed.json","frameworks-versions.json"):
    if token not in prepare: raise SystemExit(f"integration payload preparer misses contract: {token}")
for forbidden in ("trusted=yes","allow-unauthenticated","apt-key"):
    if forbidden in prepare.lower() or forbidden in runner.lower(): raise SystemExit(f"unsafe APT integration behavior remains: {forbidden}")
for token in ("Signed-By:","Pin-Priority: 1001","Acquire::AllowInsecureRepositories=false","APT::Get::AllowUnauthenticated=false","apt-get -s","apt-get -y","apt-get check",'"apt_solvability":"PASS"', '"dependency_closure":"PASS"', '"clean_install":"PASS"', '"upgrade_from_ubuntu":"NOT_RUN"', '"wayland_session":"NOT_RUN"', '"package_attempt_consumed":False', '"sbuild_invoked":False'):
    if token not in runner: raise SystemExit(f"integration guest runner misses contract: {token}")
if "sbuild " in runner or " sbuild" in runner: raise SystemExit("integration guest runner must not invoke sbuild")
for token in ("supralinux-proposed-integration","ci:supralinux-proposed-integration","SUPRALINUX_PERSISTENT_ARTIFACT_ROOT","prepare-supralinux-proposed-integration-payload.py","virt-copy-in","frameworks-6.30-pass"):
    if token not in jit: raise SystemExit(f"JIT integration route misses contract: {token}")
for token in ('"supralinux-proposed-integration"','"SUPRALINUX_PERSISTENT_ARTIFACT_ROOT"'):
    if token not in broker: raise SystemExit(f"host broker misses integration route: {token}")
for token in ("types: [labeled]","ci:supralinux-proposed-integration","Checkout exact authorized PR head","run-authoritative-supralinux-proposed-integration.sh","Retain proposed integration evidence"):
    if token not in workflow: raise SystemExit(f"integration workflow misses contract: {token}")
print("SupraLINUX-proposed authoritative integration contract: PASS")
