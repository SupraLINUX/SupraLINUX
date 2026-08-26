#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-clean-rootfs.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEB_DIR="${ROOT_DIR}/build/debs"
ROOTFS="${ROOT_DIR}/build/rootfs"
MIRROR="${AURORA_UBUNTU_MIRROR:-http://archive.ubuntu.com/ubuntu}"

required_tools=(debootstrap chroot dpkg-query apt-get apt-cache)
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

rm -rf "${ROOTFS}"
mkdir -p "${ROOTFS}"

echo "==> Creating clean Ubuntu 26.04 minbase rootfs"
deBootstrapLog="${ROOT_DIR}/build/debootstrap.log"
if ! debootstrap --variant=minbase --arch=amd64 resolute "${ROOTFS}" "${MIRROR}" >"${deBootstrapLog}" 2>&1; then
  cat "${deBootstrapLog}" >&2
  exit 1
fi

cat >"${ROOTFS}/etc/apt/sources.list" <<'EOF'
deb http://archive.ubuntu.com/ubuntu resolute main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu resolute-updates main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu resolute-security main restricted universe multiverse
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

echo "==> Updating clean rootfs package metadata"
run_in_rootfs apt-get update

echo "==> Installing SupraLINUX Snap policy before the rest of the system"
run_in_rootfs apt-get install -y /tmp/supralinux/supralinux-snap-policy_*.deb

echo "==> Verifying Snap is blocked before installing Aurora layers"
snap_policy="$(run_in_rootfs apt-cache policy snapd)"
printf '%s\n' "${snap_policy}"
grep -Fq 'Candidate: (none)' <<<"${snap_policy}"

echo "==> Installing supralinux-base + supralinux-desktop into the clean rootfs"
run_in_rootfs apt-get install -y \
  /tmp/supralinux/supralinux-base_*.deb \
  /tmp/supralinux/supralinux-desktop_*.deb

run_in_rootfs apt-get check

assert_installed() {
  local package="$1"
  local status
  status="$(run_in_rootfs dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  if [[ "${status}" != "ii " ]]; then
    echo "Expected installed package '${package}', got status '${status:-missing}'." >&2
    exit 1
  fi
}

assert_absent() {
  local package="$1"
  if run_in_rootfs dpkg-query -W -f='${db:Status-Abbrev}' "${package}" >/dev/null 2>&1; then
    echo "Forbidden package '${package}' is present in the clean Aurora rootfs." >&2
    exit 1
  fi
}

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
rootfs_size="$(du -sh "${ROOTFS}" | awk '{print $1}')"

echo "Aurora clean-rootfs validation passed."
echo "Installed packages: ${installed_count}"
echo "Rootfs size: ${rootfs_size}"
