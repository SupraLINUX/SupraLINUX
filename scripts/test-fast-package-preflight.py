#!/usr/bin/env python3
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "scripts/run-fast-package-preflight.sh"
SCANNER = ROOT / "scripts/scan-upstream-test-network.py"

lane = LANE.read_text()
scanner = SCANNER.read_text()
ast.parse(scanner)

for token in (
    "scripts/validate_plasma_package_build.py",
    "scripts/test-reviewed-package-contract.py",
    "sha256sum --check --strict",
    "gpgv --status-fd 1",
    "scripts/prepare-plasma-package.py",
    "dpkg-source --before-build",
    "dpkg-source --after-build",
    "autopkgtest --validate",
    "scripts/scan-upstream-test-network.py",
    '"package_attempt_consumed": False',
    '"sbuild_invoked": False',
    '"kvm_created": False',
):
    assert token in lane, f"FAST lane missing contract: {token}"

for forbidden in (
    " sbuild ",
    "run-kvm-jit-gate",
    "virt-install",
    "autopkgtest-virt-qemu",
    "qemu-system",
):
    assert forbidden not in lane, f"FAST lane crosses authoritative boundary: {forbidden}"

for token in (
    '"blocking": False',
    '"candidate_count"',
    '"upstream-test-live-network-static-review"',
):
    assert token in scanner, f"network scanner missing contract: {token}"

print("FAST package preflight contract: PASS")
