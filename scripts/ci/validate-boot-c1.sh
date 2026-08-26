#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-boot-c1.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c1-rootfs.img"
ROOTFS="${BUILD_DIR}/aurora-c1-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c1-serial.log"
IMAGE_SIZE="${AURORA_C1_IMAGE_SIZE:-10G}"
BOOT_TIMEOUT="${AURORA_C1_BOOT_TIMEOUT:-600}"

required_tools=(mkfs.ext4 mount umount mountpoint blkid qemu-system-x86_64 timeout)
for tool in "${required_tools[@]}"; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Missing required tool: ${tool}" >&2
    exit 1
  }
done

mkdir -p "${BUILD_DIR}" "${ROOTFS}"
rm -f "${IMAGE}" "${SERIAL_LOG}" "${BUILD_DIR}/aurora-c1-vmlinuz" "${BUILD_DIR}/aurora-c1-initrd.img"

cleanup() {
  set +e
  if mountpoint -q "${ROOTFS}"; then
    umount "${ROOTFS}" >/dev/null 2>&1 || umount -l "${ROOTFS}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Creating sparse ${IMAGE_SIZE} ext4 disk image"
truncate -s "${IMAGE_SIZE}" "${IMAGE}"
mkfs.ext4 -F -L AURORA_C1 "${IMAGE}" >/dev/null
mount -o loop "${IMAGE}" "${ROOTFS}"

# Reuse the already-proven package/rootfs composition, but build directly into
# the mounted disk image so CI does not need a second multi-gigabyte copy.
echo "==> Installing Aurora into the boot disk"
AURORA_ROOTFS_DIR="${ROOTFS}" \
  bash "${ROOT_DIR}/scripts/ci/validate-clean-rootfs.sh"

# policy-rc.d exists only to keep package maintainer scripts from trying to
# start services while composing the chroot. It is not part of the booted
# product state.
rm -f "${ROOTFS}/usr/sbin/policy-rc.d"
rm -rf "${ROOTFS}/tmp/supralinux"

echo aurora-c1 >"${ROOTFS}/etc/hostname"
cat >"${ROOTFS}/etc/hosts" <<'EOF'
127.0.0.1 localhost
127.0.1.1 aurora-c1
::1 localhost ip6-localhost ip6-loopback
EOF

root_uuid="$(blkid -s UUID -o value "${IMAGE}")"
if [[ -z "${root_uuid}" ]]; then
  echo "Could not determine the ext4 filesystem UUID." >&2
  exit 1
fi
cat >"${ROOTFS}/etc/fstab" <<EOF
UUID=${root_uuid} / ext4 defaults 0 1
EOF

# CI-only boot probe. None of these files belongs in SupraLINUX product
# packages. A timer triggers the probe after boot; the service itself is ordered
# after multi-user.target so the marker cannot be emitted before C1 is reached.
mkdir -p "${ROOTFS}/usr/local/libexec" "${ROOTFS}/etc/systemd/system/timers.target.wants"
cat >"${ROOTFS}/usr/local/libexec/aurora-ci-c1-check" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec >/dev/ttyS0 2>&1

fail() {
  echo "AURORA_C1_FAILURE: $*"
  systemctl poweroff --no-block || true
  exit 1
}

echo "AURORA_C1_CHECK_START"

[[ "$(cat /proc/1/comm)" == "systemd" ]] || fail "PID 1 is not systemd"
systemctl is-active --quiet multi-user.target || fail "multi-user.target is not active"

if systemctl is-active --quiet emergency.target; then
  fail "emergency.target is active"
fi
if systemctl is-active --quiet rescue.target; then
  fail "rescue.target is active"
fi

root_opts="$(findmnt -n -o OPTIONS /)"
tr ',' '\n' <<<"${root_opts}" | grep -Fxq rw || fail "root filesystem is not read/write (${root_opts})"

apt-get check >/dev/null || fail "apt-get check failed after boot"

for package in supralinux-snap-policy supralinux-base supralinux-desktop plasma-desktop plasma-workspace plasma-session-wayland kwin-wayland sddm; do
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  [[ "${status}" == "ii " ]] || fail "required package ${package} has status ${status:-missing}"
done

for package in snapd plasma-discover-backend-snap; do
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  if [[ -n "${status}" && "${status:1:1}" != "n" ]]; then
    fail "forbidden package ${package} has dpkg status ${status}"
  fi
  apt-cache policy "${package}" | grep -Fq 'Candidate: (none)' || fail "${package} has an APT candidate"
done

[[ -L /etc/systemd/system/display-manager.service ]] || fail "display-manager.service is not configured"
[[ "$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")" == "sddm.service" ]] || fail "SDDM is not the configured display manager"

echo "AURORA_C1_SUCCESS"
sync
systemctl poweroff --no-block
EOF
chmod 0755 "${ROOTFS}/usr/local/libexec/aurora-ci-c1-check"

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c1-check.service" <<'EOF'
[Unit]
Description=SupraLINUX Aurora C1 boot validation probe
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c1-check
TimeoutStartSec=90
EOF

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c1-check.timer" <<'EOF'
[Unit]
Description=Run SupraLINUX Aurora C1 boot validation probe

[Timer]
OnBootSec=8s
AccuracySec=1s
Unit=aurora-ci-c1-check.service

[Install]
WantedBy=timers.target
EOF
ln -s ../aurora-ci-c1-check.timer "${ROOTFS}/etc/systemd/system/timers.target.wants/aurora-ci-c1-check.timer"

kernel_path="$(find "${ROOTFS}/boot" -maxdepth 1 -type f -name 'vmlinuz-*' -printf '%f\n' | sort -V | tail -n1)"
if [[ -z "${kernel_path}" ]]; then
  echo "No installed Ubuntu kernel found in the Aurora rootfs." >&2
  exit 1
fi
kernel_version="${kernel_path#vmlinuz-}"
initrd_path="initrd.img-${kernel_version}"
if [[ ! -f "${ROOTFS}/boot/${initrd_path}" ]]; then
  echo "Matching initramfs ${initrd_path} is missing." >&2
  exit 1
fi

cp "${ROOTFS}/boot/${kernel_path}" "${BUILD_DIR}/aurora-c1-vmlinuz"
cp "${ROOTFS}/boot/${initrd_path}" "${BUILD_DIR}/aurora-c1-initrd.img"
sync
umount "${ROOTFS}"

echo "==> Booting Aurora C1 VM with kernel ${kernel_version}"
qemu_accel=(-accel tcg -cpu max)
if [[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
  echo "==> KVM acceleration available"
  qemu_accel=(-enable-kvm -cpu host)
else
  echo "==> KVM unavailable; using QEMU TCG fallback"
fi

set +e
timeout --signal=TERM --kill-after=15 "${BOOT_TIMEOUT}" \
  qemu-system-x86_64 \
    -machine q35 \
    "${qemu_accel[@]}" \
    -smp 2 \
    -m 2048 \
    -no-reboot \
    -nographic \
    -serial mon:stdio \
    -kernel "${BUILD_DIR}/aurora-c1-vmlinuz" \
    -initrd "${BUILD_DIR}/aurora-c1-initrd.img" \
    -append "root=/dev/vda rw rootfstype=ext4 console=ttyS0,115200n8 systemd.unit=multi-user.target systemd.show_status=true systemd.log_target=console panic=-1" \
    -drive "file=${IMAGE},format=raw,if=virtio,cache=unsafe" \
    -device virtio-rng-pci \
    2>&1 | tee "${SERIAL_LOG}"
qemu_status=${PIPESTATUS[0]}
set -e

if [[ ${qemu_status} -eq 124 ]]; then
  echo "Aurora C1 VM timed out after ${BOOT_TIMEOUT} seconds." >&2
  exit 1
fi
if ! grep -Fq 'AURORA_C1_SUCCESS' "${SERIAL_LOG}"; then
  echo "Aurora C1 success marker was not observed on the serial console." >&2
  exit 1
fi
if grep -Fq 'AURORA_C1_FAILURE:' "${SERIAL_LOG}"; then
  echo "Aurora C1 guest probe reported failure." >&2
  exit 1
fi

echo "Aurora C1 boot validation passed."
