#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-clean-rootfs.sh must run as root." >&2
  exit 1
fi

# Keep chroot mounts isolated from the runner's mount namespace. The package
# installation needs /proc, /sys and /dev to behave like a real Ubuntu system,
# but those mounts must never leak back into the CI host.
if [[ "${AURORA_ROOTFS_MOUNT_NAMESPACE:-0}" != "1" ]]; then
  command -v unshare >/dev/null 2>&1 || {
    echo "Missing required tool: unshare" >&2
    exit 1
  }
  exec unshare --mount --propagation private /usr/bin/env \
    AURORA_ROOTFS_MOUNT_NAMESPACE=1 \
    bash "$0" "$@"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEB_DIR="${ROOT_DIR}/build/debs"
ROOTFS="${ROOT_DIR}/build/rootfs"
MIRROR="${AURORA_UBUNTU_MIRROR:-http://archive.ubuntu.com/ubuntu}"
SECURITY_MIRROR="${AURORA_UBUNTU_SECURITY_MIRROR:-http://security.ubuntu.com/ubuntu}"

required_tools=(debootstrap chroot dpkg-query apt-get apt-cache mount umount mountpoint)
for tool in "${required_tools[@]}"; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Missing required tool: ${tool}" >&2
    exit 1
  }
done

shopt -s nullglob
snap_policy_debs=("${DEB_DIR}"/supralinux-snap-policy_*.deb)
base_debs=("${DEB_DIR}"/supralinux-base_*.deb)
desktop_debs=("${DEB_DIR}"/supralinux-desktop_*.deb)

if [[ ${#snap_policy_debs[@]} -ne 1 || ${#base_debs[@]} -ne 1 || ${#desktop_debs[@]} -ne 1 ]]; then
  echo "Expected exactly one built .deb for snap-policy, base and desktop." >&2
  exit 1
fi

snap_policy_name="$(basename "${snap_policy_debs[0]}")"
base_name="$(basename "${base_debs[0]}")"
desktop_name="$(basename "${desktop_debs[0]}")"

rm -rf "${ROOTFS}"
mkdir -p "${ROOTFS}"

echo "==> Creating clean Ubuntu 26.04 minbase rootfs"
deBootstrapLog="${ROOT_DIR}/build/debootstrap.log"
if ! debootstrap --variant=minbase --arch=amd64 resolute "${ROOTFS}" "${MIRROR}" >"${deBootstrapLog}" 2>&1; then
  cat "${deBootstrapLog}" >&2
  exit 1
fi

cleanup_rootfs_mounts() {
  set +e
  if mountpoint -q "${ROOTFS}/dev"; then
    umount -R "${ROOTFS}/dev" >/dev/null 2>&1 || umount -l "${ROOTFS}/dev" >/dev/null 2>&1 || true
  fi
  if mountpoint -q "${ROOTFS}/sys"; then
    umount "${ROOTFS}/sys" >/dev/null 2>&1 || umount -l "${ROOTFS}/sys" >/dev/null 2>&1 || true
  fi
  if mountpoint -q "${ROOTFS}/proc"; then
    umount "${ROOTFS}/proc" >/dev/null 2>&1 || umount -l "${ROOTFS}/proc" >/dev/null 2>&1 || true
  fi
}
trap cleanup_rootfs_mounts EXIT

# Maintainer scripts, systemd-tmpfiles and dracut expect these pseudo
# filesystems. /proc and /sys are intentionally read-only so package scripts
# cannot alter the CI runner's kernel state while running inside the chroot.
mkdir -p "${ROOTFS}/proc" "${ROOTFS}/sys" "${ROOTFS}/dev"
mount -t proc -o ro,nosuid,nodev,noexec proc "${ROOTFS}/proc"
mount -t sysfs -o ro,nosuid,nodev,noexec sysfs "${ROOTFS}/sys"
mount --rbind /dev "${ROOTFS}/dev"
mount --make-rslave "${ROOTFS}/dev"

cat >"${ROOTFS}/etc/apt/sources.list" <<EOF
deb ${MIRROR} resolute main restricted universe multiverse
deb ${MIRROR} resolute-updates main restricted universe multiverse
deb ${SECURITY_MIRROR} resolute-security main restricted universe multiverse
EOF

rm -f "${ROOTFS}/etc/resolv.conf"
cp -L /etc/resolv.conf "${ROOTFS}/etc/resolv.conf"

cat >"${ROOTFS}/usr/sbin/policy-rc.d" <<'EOF'
#!/bin/sh
exit 101
EOF
chmod 0755 "${ROOTFS}/usr/sbin/policy-rc.d"

mkdir -p "${ROOTFS}/tmp/supralinux"
cp "${snap_policy_debs[0]}" "${base_debs[0]}" "${desktop_debs[0]}" "${ROOTFS}/tmp/supralinux/"

run_in_rootfs() {
  chroot "${ROOTFS}" /usr/bin/env \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    "$@"
}

package_status() {
  local package="$1"
  run_in_rootfs dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true
}

assert_installed() {
  local package="$1"
  local status
  status="$(package_status "${package}")"
  if [[ "${status}" != "ii " ]]; then
    echo "Expected installed package '${package}', got status '${status:-missing}'." >&2
    exit 1
  fi
}

assert_absent() {
  local package="$1"
  local status
  status="$(package_status "${package}")"

  # dpkg-query may return success for packages known to dpkg even when their
  # status is "not-installed" (for example "un "). Treat every dpkg state
  # whose status character is 'n' as absent; reject installed, unpacked,
  # half-configured and config-files-only states.
  if [[ -z "${status}" || "${status:1:1}" == "n" ]]; then
    return 0
  fi

  echo "Forbidden package '${package}' has dpkg status '${status}' in the clean Aurora rootfs." >&2
  exit 1
}

echo "==> Updating clean rootfs package metadata"
run_in_rootfs apt-get update

echo "==> Installing SupraLINUX Snap policy before the rest of the system"
run_in_rootfs apt-get install -y "/tmp/supralinux/${snap_policy_name}"
assert_installed supralinux-snap-policy

if [[ ! -f "${ROOTFS}/etc/apt/preferences.d/supralinux-no-snap.pref" ]]; then
  echo "SupraLINUX Snap APT preference was not installed by supralinux-snap-policy." >&2
  exit 1
fi

echo "==> Verifying Snap is blocked before installing Aurora layers"
snap_policy="$(run_in_rootfs apt-cache policy snapd)"
printf '%s\n' "${snap_policy}"
grep -Fq 'Candidate: (none)' <<<"${snap_policy}"

echo "==> Installing supralinux-base + supralinux-desktop into the clean rootfs"
run_in_rootfs apt-get install -y \
  "/tmp/supralinux/${base_name}" \
  "/tmp/supralinux/${desktop_name}"

run_in_rootfs apt-get check

required_packages=(
  supralinux-snap-policy
  supralinux-base
  supralinux-desktop
  ubuntu-minimal
  ubuntu-standard
  linux-generic
  plasma-desktop
  plasma-workspace
  plasma-session-wayland
  kwin-wayland
  systemsettings
  sddm
  polkit-kde-agent-1
  pipewire-audio
  network-manager
  plasma-nm
  bluez
  bluedevil
  xdg-desktop-portal-kde
  flatpak
  kde-config-flatpak
  krdp
  cups
  print-manager
  kdenetwork-filesharing
  samba
  powerdevil
  kscreen
  libpam-kwallet5
)

for package in "${required_packages[@]}"; do
  assert_installed "${package}"
done

forbidden_packages=(
  snapd
  plasma-discover-backend-snap
  ubuntu-desktop
  ubuntu-desktop-minimal
  kubuntu-desktop
  kubuntu-desktop-minimal
  gnome-shell
)

for package in "${forbidden_packages[@]}"; do
  assert_absent "${package}"
done

if [[ ! -f "${ROOTFS}/etc/apt/preferences.d/supralinux-no-snap.pref" ]]; then
  echo "SupraLINUX Snap APT preference is missing from the installed rootfs." >&2
  exit 1
fi

echo "==> Verifying Snap remains blocked after the complete installation"
for package in snapd plasma-discover-backend-snap; do
  output="$(run_in_rootfs apt-cache policy "${package}")"
  printf '%s\n' "${output}"
  if ! grep -Fq 'Candidate: (none)' <<<"${output}"; then
    echo "${package} became installable in the complete Aurora rootfs." >&2
    exit 1
  fi
done

echo "==> Verifying Discover remains resolvable without Snap"
discover_log="${ROOT_DIR}/build/rootfs-discover-simulation.log"
if ! run_in_rootfs apt-get --simulate --no-remove install plasma-discover >"${discover_log}" 2>&1; then
  cat "${discover_log}" >&2
  exit 1
fi
if grep -Eq '^Inst (snapd|plasma-discover-backend-snap)( |$)' "${discover_log}"; then
  cat "${discover_log}" >&2
  echo "Discover would pull Snap into the clean Aurora rootfs." >&2
  exit 1
fi

installed_count="$(run_in_rootfs dpkg-query -W -f='${db:Status-Abbrev}\n' | grep -c '^ii ' || true)"
rootfs_size="$(du -shx "${ROOTFS}" | awk '{print $1}')"

echo "Aurora clean-rootfs validation passed."
echo "Installed packages: ${installed_count}"
echo "Rootfs size: ${rootfs_size}"
