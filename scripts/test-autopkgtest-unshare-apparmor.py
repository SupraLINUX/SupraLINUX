#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "ops/apparmor/supralinux-autopkgtest-virt-unshare"
PROVISION = ROOT / "scripts/provision-authoritative-runner-guest.sh"
DIGEST = ROOT / "scripts/golden-image-input-digest.sh"

profile = PROFILE.read_text()
for token in (
    "abi <abi/5.0>,",
    "profile supralinux-autopkgtest-virt-unshare /usr/bin/autopkgtest-virt-unshare flags=(unconfined)",
    "userns,",
):
    assert token in profile, f"missing AppArmor contract: {token}"
for forbidden in (
    "deny userns",
    "kernel.apparmor_restrict_unprivileged_userns=0",
    "profile supralinux-autopkgtest-virt-unshare /usr/bin/unshare",
    "/usr/bin/unshare ix,",
    "mount,",
    "pivot_root,",
):
    assert forbidden not in profile, f"unsafe AppArmor profile construct: {forbidden}"

provision = PROVISION.read_text()
package_start = provision.index("sudo DEBIAN_FRONTEND=noninteractive apt-get install -y")
package_end = provision.index("if ! grep -q", package_start)
package_block = provision[package_start:package_end]
assert any(
    line.strip().rstrip("\\").strip() == "apparmor"
    for line in package_block.splitlines()
), "golden provisioning must install the AppArmor package"

for token in (
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

certifier = (ROOT / "scripts/certify-autopkgtest-unshare-backend.sh").read_text()
for token in (
    "unshare --arch amd64 --tarball",
    "profile_attachment=/usr/bin/autopkgtest-virt-unshare",
    "profile_mode=unconfined-with-userns-exception",
):
    assert token in certifier, f"certifier misses path-attached AppArmor contract: {token}"
for forbidden in (
    "aa-exec",
    "active_profile_probe=",
    "unshare-mount-preflight",
):
    assert forbidden not in certifier, f"stale explicit AppArmor transition remains: {forbidden}"

digest = DIGEST.read_text()
assert "ops/apparmor/supralinux-autopkgtest-virt-unshare" in digest

print("Autopkgtest unshare AppArmor golden-image contract: PASS")
