#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run-authoritative-plasma-package.sh"
POLICY = ROOT / "scripts/autopkgtest-backend-policy.py"

runner = RUNNER.read_text()
for token in (
    'UNSHARE_PRIVATE_DIR="/usr/local/libexec/supralinux-autopkgtest"',
    'python3 "${ROOT}/scripts/autopkgtest-backend-policy.py" "${TEST_CONTROL}"',
    'AUTOPKGTEST_BACKEND=',
    'if [[ "${AUTOPKGTEST_BACKEND}" == "unshare" ]]',
    'SYSTEM_TEST_BACKEND="autopkgtest-unshare"',
    'SYSTEM_TEST_ACCELERATION="outer-kvm-userns"',
    'PATH="${UNSHARE_PRIVATE_DIR}:${PATH}"',
    'unshare --arch amd64 --tarball "${CHROOT}"',
    'SYSTEM_TEST_BACKEND="autopkgtest-qemu"',
    'SYSTEM_TEST_ACCELERATION="nested-kvm"',
    'qemu --qemu-command="${ROOT}/scripts/qemu-kvm-required.sh"',
    'STAGE="retained-package-upgrade"',
):
    assert token in runner, f"missing production backend rollout contract: {token}"

normal_unshare = runner.index('if [[ "${AUTOPKGTEST_BACKEND}" == "unshare" ]]')
retained = runner.index('STAGE="retained-package-upgrade"')
assert normal_unshare < retained
retained_tail = runner[retained:]
assert 'qemu --qemu-command="${ROOT}/scripts/qemu-kvm-required.sh"' in retained_tail
assert 'unshare --arch amd64 --tarball "${CHROOT}"' not in retained_tail

policy = POLICY.read_text()
for restriction in (
    "breaks-testbed",
    "isolation-container",
    "isolation-machine",
    "needs-reboot",
    "needs-reboot-without-mark",
):
    assert f'"{restriction}"' in policy
assert 'backend = "qemu" if qemu_reasons or unknown_restrictions else "unshare"' in policy

print("Production autopkgtest backend rollout contract: PASS")
