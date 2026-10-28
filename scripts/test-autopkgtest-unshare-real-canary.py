#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/certify-autopkgtest-unshare-real-canary.sh"
WORKFLOW = ROOT / ".github/workflows/runner-contract.yml"

script = SCRIPT.read_text()
for token in (
    'NODE="ocean-sound-theme"',
    'VERSION="6.7.5-0supralinux1"',
    'ARTIFACT_ID="11317894456"',
    'ARTIFACT_SHA256="9243fe8efcf9a24b659ed3ec76954cca4263a08dd71e7613f12f20b57cddc2f2"',
    'ARTIFACT_SOURCE_COMMIT="d999e3f9cdf28bc52a50587b3fc157f4f8aa2ac9"',
    'API_VERSION="2022-11-28"',
    'DOWNLOAD_HEADERS="${WORK}/artifact-download.headers"',
    'GitHub artifact API did not return a signed Location header',
    'curl --fail --location --silent --show-error',
    'unset SIGNED_URL',
    '"package_attempt_consumed": False',
    '"sbuild_invoked": False',
    '"candidate_rebuilt": False',
    '"canonical_package_state_effect": "none"',
    'expected = {"sound-resources", "ubuntu-upgrade"}',
    'run_backend qemu',
    'run_backend unshare',
    'UNSHARE_PRIVATE_DIR="/usr/local/libexec/supralinux-autopkgtest"',
    'PATH="${UNSHARE_PRIVATE_DIR}:${PATH}"',
):
    assert token in script, f"real canary missing contract: {token}"

for forbidden in (
    "sbuild ",
    "dpkg-buildpackage",
    "execute-and-publish-pass",
    "package_execution_authorized",
    "--fail --location --silent --show-error \\\n    -H \"Authorization:",
):
    assert forbidden not in script, f"real canary crosses package boundary: {forbidden}"

workflow = WORKFLOW.read_text()
assert "actions: read" in workflow
assert "Certify unshare on retained real Plasma PASS" in workflow
assert "scripts/certify-autopkgtest-unshare-real-canary.sh" in workflow
assert "GITHUB_TOKEN: ${{ github.token }}" in workflow
synthetic = workflow.index("Certify autopkgtest unshare backend equivalence")
canary = workflow.index("Certify unshare on retained real Plasma PASS")
assert synthetic < canary, "real canary must run only after synthetic A/B"

print("Retained real-package unshare canary contract: PASS")
