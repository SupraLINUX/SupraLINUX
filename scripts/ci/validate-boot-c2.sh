#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-boot-c2.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c2-rootfs.img"
ROOTFS="${BUILD_DIR}/aurora-c2-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c2-serial.log"
IMAGE_SIZE="${AURORA_C2_IMAGE_SIZE:-10G}"
BOOT_TIMEOUT="${AURORA_C2_BOOT_TIMEOUT:-600}"

required_tools=(mkfs.ext4 mount umount mountpoint blkid qemu-system-x86_64 timeout)
for tool in "${required_tools[@]}"; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Missing required tool: ${tool}" >&2
    exit 1
  }
done

mkdir -p "${BUILD_DIR}" "${ROOTFS}"
rm -f "${IMAGE}" "${SERIAL_LOG}" "${BUILD_DIR}/aurora-c2-vmlinuz" "${BUILD_DIR}/aurora-c2-initrd.img"

cleanup() {
  set +e
  if mountpoint -q "${ROOTFS}"; then
    umount "${ROOTFS}" >/dev/null 2>&1 || umount -l "${ROOTFS}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Creating sparse ${IMAGE_SIZE} ext4 disk image"
truncate -s "${IMAGE_SIZE}" "${IMAGE}"
mkfs.ext4 -F -L AURORA_C2 "${IMAGE}" >/dev/null
mount -o loop "${IMAGE}" "${ROOTFS}"

echo "==> Installing Aurora into the C2 boot disk"
AURORA_ROOTFS_DIR="${ROOTFS}" bash "${ROOT_DIR}/scripts/ci/validate-clean-rootfs.sh"

rm -f "${ROOTFS}/usr/sbin/policy-rc.d"
rm -rf "${ROOTFS}/tmp/supralinux"

echo aurora-c2 >"${ROOTFS}/etc/hostname"
cat >"${ROOTFS}/etc/hosts" <<'HOSTS'
127.0.0.1 localhost
127.0.1.1 aurora-c2
::1 localhost ip6-localhost ip6-loopback
HOSTS

root_uuid="$(blkid -s UUID -o value "${IMAGE}")"
if [[ -z "${root_uuid}" ]]; then
  echo "Could not determine the ext4 filesystem UUID." >&2
  exit 1
fi
cat >"${ROOTFS}/etc/fstab" <<FSTAB
UUID=${root_uuid} / ext4 defaults 0 1
FSTAB

mkdir -p "${ROOTFS}/usr/local/libexec" "${ROOTFS}/etc/systemd/system/timers.target.wants"
cat >"${ROOTFS}/usr/local/libexec/aurora-ci-c2-check" <<'GUEST'
#!/usr/bin/env bash
set -euo pipefail
exec >/dev/ttyS0 2>&1

dump_diagnostics() {
  echo "AURORA_C2_DIAGNOSTICS_START"
  systemctl --failed --no-pager --plain || true
  systemctl status sddm.service --no-pager --full || true
  systemctl status systemd-logind.service --no-pager --full || true
  loginctl seat-status seat0 --no-pager || true
  echo "--- /dev/dri ---"
  ls -la /dev/dri 2>&1 || true
  echo "--- sddm processes ---"
  if id sddm >/dev/null 2>&1; then
    pgrep -a -u "$(id -u sddm)" || true
  fi
  echo "--- display-server processes ---"
  pgrep -a -f 'kwin_wayland|sddm-greeter|Xorg|Xwayland' || true
  echo "--- sddm journal ---"
  journalctl -b -u sddm.service --no-pager -n 250 || true
  echo "AURORA_C2_DIAGNOSTICS_END"
}

fail() {
  echo "AURORA_C2_FAILURE: $*"
  dump_diagnostics
  systemctl poweroff --no-block || true
  exit 1
}

echo "AURORA_C2_CHECK_START"

[[ "$(cat /proc/1/comm)" == "systemd" ]] || fail "PID 1 is not systemd"
systemctl is-active --quiet graphical.target || fail "graphical.target is not active"
systemctl is-active --quiet multi-user.target || fail "multi-user.target is not active"

if systemctl is-active --quiet emergency.target; then
  fail "emergency.target is active"
fi
if systemctl is-active --quiet rescue.target; then
  fail "rescue.target is active"
fi

root_opts="$(findmnt -n -o OPTIONS /)"
root_opts_lines="$(tr ',' '\n' <<<"${root_opts}")"
grep -Fxq rw <<<"${root_opts_lines}" || fail "root filesystem is not read/write (${root_opts})"

apt-get check >/dev/null || fail "apt-get check failed after graphical boot"

for package in supralinux-snap-policy supralinux-base supralinux-settings supralinux-desktop plasma-desktop plasma-workspace plasma-session-wayland kwin-wayland xwayland layer-shell-qt sddm; do
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  [[ "${status}" == "ii " ]] || fail "required package ${package} has status ${status:-missing}"
done

for package in snapd plasma-discover-backend-snap plasma-session-x11; do
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  if [[ -n "${status}" && "${status:1:1}" != "n" ]]; then
    fail "forbidden package ${package} has dpkg status ${status}"
  fi
  if [[ "${package}" != "plasma-session-x11" ]]; then
    policy="$(apt-cache policy "${package}")"
    grep -Fq 'Candidate: (none)' <<<"${policy}" || fail "${package} has an APT candidate"
  fi
done

[[ ! -e /usr/share/xsessions/plasmax11.desktop ]] || fail "Plasma X11 session desktop entry is present"
[[ ! -e /usr/bin/startplasma-x11 ]] || fail "startplasma-x11 is present"

sddm_wayland_conf=/etc/sddm.conf.d/10-supralinux-wayland.conf
[[ -f "${sddm_wayland_conf}" ]] || fail "SupraLINUX SDDM Wayland configuration is missing"
grep -Fxq 'DisplayServer=wayland' "${sddm_wayland_conf}" || fail "SDDM greeter is not configured for Wayland"
grep -Fq 'CompositorCommand=kwin_wayland ' "${sddm_wayland_conf}" || fail "SDDM greeter is not configured to use KWin Wayland"

[[ -L /etc/systemd/system/display-manager.service ]] || fail "display-manager.service is not configured"
[[ "$(basename "$(readlink -f /etc/systemd/system/display-manager.service)")" == "sddm.service" ]] || fail "SDDM is not the configured display manager"

systemctl is-active --quiet systemd-logind.service || fail "systemd-logind.service is not active"
[[ -e /dev/dri/card0 ]] || fail "virtual graphics device /dev/dri/card0 is missing"

seat_graphical="$(loginctl show-seat seat0 -p CanGraphical --value 2>/dev/null || true)"
[[ "${seat_graphical}" == "yes" ]] || fail "seat0 is not graphical (CanGraphical=${seat_graphical:-unknown})"

sddm_uid="$(id -u sddm 2>/dev/null || true)"
[[ -n "${sddm_uid}" ]] || fail "SDDM system user is missing"

sddm_ready=0
for _ in $(seq 1 45); do
  if systemctl is-active --quiet sddm.service \
    && pgrep -u "${sddm_uid}" -f 'kwin_wayland' >/dev/null 2>&1 \
    && pgrep -u "${sddm_uid}" -f 'sddm-greeter' >/dev/null 2>&1; then
    sddm_ready=1
    break
  fi
  sleep 1
done
[[ "${sddm_ready}" -eq 1 ]] || fail "SDDM did not reach a KWin Wayland greeter state"

if systemctl is-failed --quiet sddm.service; then
  fail "sddm.service is failed"
fi

echo "AURORA_C2_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${ROOTFS}/usr/local/libexec/aurora-ci-c2-check"

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c2-check.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C2 graphical boot validation probe
After=graphical.target sddm.service systemd-logind.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c2-check
TimeoutStartSec=120
SERVICE

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c2-check.timer" <<'TIMER'
[Unit]
Description=Run SupraLINUX Aurora C2 graphical boot validation probe

[Timer]
OnBootSec=15s
AccuracySec=1s
Unit=aurora-ci-c2-check.service

[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c2-check.timer "${ROOTFS}/etc/systemd/system/timers.target.wants/aurora-ci-c2-check.timer"

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

cp "${ROOTFS}/boot/${kernel_path}" "${BUILD_DIR}/aurora-c2-vmlinuz"
cp "${ROOTFS}/boot/${initrd_path}" "${BUILD_DIR}/aurora-c2-initrd.img"
sync
umount "${ROOTFS}"

echo "==> Booting Aurora C2 VM with kernel ${kernel_version}"
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
    -display none \
    -monitor none \
    -serial stdio \
    -vga none \
    -device virtio-vga \
    -kernel "${BUILD_DIR}/aurora-c2-vmlinuz" \
    -initrd "${BUILD_DIR}/aurora-c2-initrd.img" \
    -append "root=/dev/vda rw rootfstype=ext4 console=ttyS0,115200n8 systemd.unit=graphical.target systemd.show_status=true systemd.log_target=console panic=-1" \
    -drive "file=${IMAGE},format=raw,if=virtio,cache=unsafe" \
    -device virtio-rng-pci \
    2>&1 | tee "${SERIAL_LOG}"
qemu_status=${PIPESTATUS[0]}
set -e

if [[ ${qemu_status} -eq 124 ]]; then
  echo "Aurora C2 VM timed out after ${BOOT_TIMEOUT} seconds." >&2
  exit 1
fi
if [[ ${qemu_status} -ne 0 ]]; then
  echo "Aurora C2 QEMU exited with status ${qemu_status}." >&2
  exit 1
fi

success_count="$(grep -Fc 'AURORA_C2_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C2 success marker, observed ${success_count}." >&2
  exit 1
fi
if grep -Fq 'AURORA_C2_FAILURE:' "${SERIAL_LOG}"; then
  echo "Aurora C2 guest probe reported failure." >&2
  exit 1
fi

echo "Aurora C2 boot validation passed."
