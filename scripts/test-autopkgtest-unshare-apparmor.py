#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "ops/apparmor/supralinux-autopkgtest-virt-unshare"
PROVISION = ROOT / "scripts/provision-authoritative-runner-guest.sh"
DIGEST = ROOT / "scripts/golden-image-input-digest.sh"

profile = PROFILE.read_text()
for token in (
    "abi <abi/5.0>,",
    "profile supralinux-autopkgtest-virt-unshare /usr/bin/autopkgtest-virt-unshare",
    "flags=(attach_disconnected mediate_deleted)",
    "allow all,",
    "@{exec_path} mrix,",
    "/usr/bin/unshare ix,",
    "userns,",
):
    assert token in profile, f"missing AppArmor contract: {token}"
for forbidden in (
    "flags=(unconfined)",
    "deny userns",
    "kernel.apparmor_restrict_unprivileged_userns=0",
):
    assert forbidden not in profile, f"unsafe AppArmor profile construct: {forbidden}"

provision = PROVISION.read_text()
for token in (
    "apparmor \\\\",
    "command -v newuidmap",
    "command -v newgidmap",
    "count >= 65536",
    'APPARMOR_PROFILE_SOURCE="${ROOT}/ops/apparmor/supralinux-autopkgtest-virt-unshare"',
    'sudo apparmor_parser -Q "${APPARMOR_PROFILE_SOURCE}"',
    'sudo apparmor_parser -r "${APPARMOR_PROFILE_TARGET}"',
    'test "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns)" = "1"',
    "sudo aa-status | grep -Fq \'supralinux-autopkgtest-virt-unshare\'",
):
    assert token in provision, f"golden provisioning misses userns contract: {token}"
assert "kernel.apparmor_restrict_unprivileged_userns=0" not in provision
assert "sysctl -w kernel.apparmor_restrict_unprivileged_userns=0" not in provision

digest = DIGEST.read_text()
assert "ops/apparmor/supralinux-autopkgtest-virt-unshare" in digest

print("Autopkgtest unshare AppArmor golden-image contract: PASS")
