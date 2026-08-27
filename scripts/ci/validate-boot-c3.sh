#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-boot-c3.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c3-rootfs.img"
ROOTFS="${BUILD_DIR}/aurora-c3-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c3-serial.log"
SESSION_LOG="${BUILD_DIR}/aurora-c3-wayland-session.log"
IMAGE_SIZE="${AURORA_C3_IMAGE_SIZE:-12G}"
BOOT_TIMEOUT="${AURORA_C3_BOOT_TIMEOUT:-900}"
CI_USER="auroraci"

required_tools=(mkfs.ext4 mount umount mountpoint blkid qemu-system-x86_64 timeout chroot)
for tool in "${required_tools[@]}"; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Missing required tool: ${tool}" >&2
    exit 1
  }
done

mkdir -p "${BUILD_DIR}" "${ROOTFS}"
rm -f "${IMAGE}" "${SERIAL_LOG}" "${SESSION_LOG}" \
  "${BUILD_DIR}/aurora-c3-vmlinuz" "${BUILD_DIR}/aurora-c3-initrd.img"

cleanup() {
  set +e
  if mountpoint -q "${ROOTFS}"; then
    umount "${ROOTFS}" >/dev/null 2>&1 || umount -l "${ROOTFS}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Creating sparse ${IMAGE_SIZE} ext4 disk image"
truncate -s "${IMAGE_SIZE}" "${IMAGE}"
mkfs.ext4 -F -L AURORA_C3 "${IMAGE}" >/dev/null
mount -o loop "${IMAGE}" "${ROOTFS}"

echo "==> Installing Aurora into the C3 boot disk"
AURORA_ROOTFS_DIR="${ROOTFS}" bash "${ROOT_DIR}/scripts/ci/validate-clean-rootfs.sh"

rm -f "${ROOTFS}/usr/sbin/policy-rc.d"
rm -rf "${ROOTFS}/tmp/supralinux"

echo aurora-c3 >"${ROOTFS}/etc/hostname"
cat >"${ROOTFS}/etc/hosts" <<'HOSTS'
127.0.0.1 localhost
127.0.1.1 aurora-c3
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

echo "==> Creating disposable C3 desktop user"
chroot "${ROOTFS}" useradd --create-home --shell /bin/bash "${CI_USER}"
ci_uid="$(chroot "${ROOTFS}" id -u "${CI_USER}")"
if [[ -z "${ci_uid}" ]]; then
  echo "Could not determine disposable C3 user UID." >&2
  exit 1
fi

mapfile -t plasma_wayland_sessions < <(
  grep -lE '^Exec=.*startplasma-wayland([[:space:]]|$)' \
    "${ROOTFS}"/usr/share/wayland-sessions/*.desktop 2>/dev/null || true
)
if [[ "${#plasma_wayland_sessions[@]}" -ne 1 ]]; then
  echo "Expected exactly one Plasma Wayland session desktop file, found ${#plasma_wayland_sessions[@]}." >&2
  printf 'Candidate: %s\n' "${plasma_wayland_sessions[@]:-none}" >&2
  exit 1
fi
plasma_wayland_session="$(basename "${plasma_wayland_sessions[0]}")"
echo "==> C3 autologin session: ${plasma_wayland_session}"

cat >"${ROOTFS}/etc/sddm.conf.d/99-aurora-ci-c3-autologin.conf" <<EOF
[Autologin]
User=${CI_USER}
Session=${plasma_wayland_session}
Relogin=false
EOF

mkdir -p "${ROOTFS}/usr/local/libexec" "${ROOTFS}/etc/systemd/system/timers.target.wants"
cat >"${ROOTFS}/usr/local/libexec/aurora-ci-c3-check" <<'GUEST'
#!/usr/bin/env bash
set -euo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"

session_id=""
ci_uid=""
ci_home=""
runtime_dir=""

run_user() {
  runuser -u "${CI_USER}" -- env \
    HOME="${ci_home}" \
    USER="${CI_USER}" \
    LOGNAME="${CI_USER}" \
    XDG_RUNTIME_DIR="${runtime_dir}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime_dir}/bus" \
    "$@"
}

dump_diagnostics() {
  echo "AURORA_C3_DIAGNOSTICS_START"
  systemctl --failed --no-pager --plain || true
  systemctl status sddm.service --no-pager --full || true
  systemctl status systemd-logind.service --no-pager --full || true
  loginctl list-sessions --no-pager || true
  if [[ -n "${session_id}" ]]; then
    loginctl session-status "${session_id}" --no-pager || true
    loginctl show-session "${session_id}" --all --no-pager || true
  fi
  echo "--- C3 user processes ---"
  if [[ -n "${ci_uid}" ]]; then
    pgrep -a -u "${ci_uid}" || true
  fi
  echo "--- graphical/Xwayland processes ---"
  pgrep -a -f 'kwin_wayland|plasmashell|Xwayland|systemsettings|xdg-desktop-portal|polkit-kde|pipewire|wireplumber' || true
  if [[ -n "${runtime_dir}" && -S "${runtime_dir}/bus" ]]; then
    echo "--- user systemd failed units ---"
    run_user systemctl --user --failed --no-pager --plain || true
    echo "--- user systemd Plasma units ---"
    run_user systemctl --user list-units 'plasma*' --no-pager --plain || true
    echo "--- user bus names ---"
    run_user busctl --user --no-pager list || true
  fi
  echo "--- SDDM journal ---"
  journalctl -b -u sddm.service --no-pager -n 300 || true
  echo "--- disposable user Wayland session log ---"
  cat "/home/${CI_USER}/.local/share/sddm/wayland-session.log" 2>/dev/null || true
  echo "AURORA_C3_DIAGNOSTICS_END"
}

fail() {
  echo "AURORA_C3_FAILURE: $*"
  dump_diagnostics
  systemctl poweroff --no-block || true
  exit 1
}

echo "AURORA_C3_CHECK_START"

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

apt-get check >/dev/null || fail "apt-get check failed after C3 boot"

for package in supralinux-snap-policy supralinux-base supralinux-settings supralinux-desktop plasma-desktop plasma-workspace plasma-session-wayland kwin-wayland xwayland sddm xdg-desktop-portal xdg-desktop-portal-kde pipewire-audio wireplumber polkit-kde-agent-1 systemsettings; do
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  [[ "${status}" == "ii " ]] || fail "required package ${package} has status ${status:-missing}"
done

for package in snapd plasma-discover-backend-snap plasma-session-x11; do
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  if [[ -n "${status}" && "${status:1:1}" != "n" ]]; then
    fail "forbidden package ${package} has dpkg status ${status}"
  fi
done

[[ ! -e /usr/share/xsessions/plasmax11.desktop ]] || fail "Plasma X11 session desktop entry is present"
[[ ! -e /usr/bin/startplasma-x11 ]] || fail "startplasma-x11 is present"

command -v runuser >/dev/null 2>&1 || fail "runuser is unavailable"

ci_uid="$(id -u "${CI_USER}" 2>/dev/null || true)"
ci_home="$(getent passwd "${CI_USER}" | cut -d: -f6)"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable C3 user is missing"
runtime_dir="/run/user/${ci_uid}"

session_ready=0
for _ in $(seq 1 120); do
  session_id="$(
    loginctl list-sessions --no-legend 2>/dev/null \
      | awk -v uid="${ci_uid}" '$2 == uid { print $1; exit }'
  )"
  if [[ -n "${session_id}" ]] \
    && [[ "$(loginctl show-session "${session_id}" -p Type --value 2>/dev/null || true)" == "wayland" ]] \
    && [[ "$(loginctl show-session "${session_id}" -p Active --value 2>/dev/null || true)" == "yes" ]] \
    && pgrep -u "${ci_uid}" -x kwin_wayland >/dev/null 2>&1 \
    && pgrep -u "${ci_uid}" -x plasmashell >/dev/null 2>&1 \
    && [[ -S "${runtime_dir}/bus" ]]; then
    session_ready=1
    break
  fi
  sleep 1
done
[[ "${session_ready}" -eq 1 ]] || fail "Plasma Wayland user session did not become ready"

[[ "$(loginctl show-session "${session_id}" -p Name --value)" == "${CI_USER}" ]] || fail "login session belongs to unexpected user"
[[ "$(loginctl show-session "${session_id}" -p Type --value)" == "wayland" ]] || fail "login session is not Wayland"
[[ "$(loginctl show-session "${session_id}" -p Remote --value)" == "no" ]] || fail "C3 login unexpectedly reports a remote session"
[[ -S "${runtime_dir}/bus" ]] || fail "user D-Bus socket is missing"

kwin_pid="$(pgrep -u "${ci_uid}" -x kwin_wayland | head -n1)"
plasma_pid="$(pgrep -u "${ci_uid}" -x plasmashell | head -n1)"
[[ -n "${kwin_pid}" && -n "${plasma_pid}" ]] || fail "KWin Wayland or plasmashell process is missing"

plasma_env="$(tr '\0' '\n' <"/proc/${plasma_pid}/environ")"
grep -Fxq 'XDG_SESSION_TYPE=wayland' <<<"${plasma_env}" || fail "plasmashell environment is not Wayland"
wayland_display="$(awk -F= '$1=="WAYLAND_DISPLAY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
display="$(awk -F= '$1=="DISPLAY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
[[ -n "${wayland_display}" ]] || fail "WAYLAND_DISPLAY is missing from the Plasma session"
[[ -S "${runtime_dir}/${wayland_display}" ]] || fail "Wayland display socket ${runtime_dir}/${wayland_display} is missing"
[[ -n "${display}" ]] || fail "DISPLAY is missing; XWayland compatibility is unavailable"

run_user busctl --user --no-pager list >/dev/null || fail "user D-Bus session is not usable"
run_user systemctl --user is-active --quiet plasma-workspace-wayland.target || fail "plasma-workspace-wayland.target is not active"
run_user systemctl --user is-active --quiet plasma-workspace.target || fail "plasma-workspace.target is not active"
run_user systemctl --user is-active --quiet plasma-plasmashell.service || fail "plasma-plasmashell.service is not active"

run_user systemctl --user start pipewire.service wireplumber.service || fail "PipeWire/WirePlumber user services could not start"
run_user systemctl --user is-active --quiet pipewire.service || fail "pipewire.service is not active"
run_user systemctl --user is-active --quiet wireplumber.service || fail "wireplumber.service is not active"

run_user systemctl --user start plasma-polkit-agent.service || fail "Plasma Polkit agent service could not start"
run_user systemctl --user is-active --quiet plasma-polkit-agent.service || fail "plasma-polkit-agent.service is not active"

run_user busctl --user call \
  org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
  StartServiceByName su org.freedesktop.portal.Desktop 0 >/dev/null \
  || fail "xdg-desktop-portal could not be D-Bus activated"
run_user busctl --user call \
  org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
  StartServiceByName su org.freedesktop.impl.portal.desktop.kde 0 >/dev/null \
  || fail "KDE portal backend could not be D-Bus activated"

portal_ready=0
for _ in $(seq 1 20); do
  bus_names="$(run_user busctl --user --no-pager list 2>/dev/null || true)"
  if grep -Fq 'org.freedesktop.portal.Desktop' <<<"${bus_names}" \
    && grep -Fq 'org.freedesktop.impl.portal.desktop.kde' <<<"${bus_names}"; then
    portal_ready=1
    break
  fi
  sleep 1
done
[[ "${portal_ready}" -eq 1 ]] || fail "desktop portal or KDE portal backend did not register on the user bus"

echo "AURORA_C3_XWAYLAND_TEST_START"
set +e
runuser -u "${CI_USER}" -- env \
  HOME="${ci_home}" \
  USER="${CI_USER}" \
  LOGNAME="${CI_USER}" \
  XDG_RUNTIME_DIR="${runtime_dir}" \
  DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime_dir}/bus" \
  XDG_SESSION_TYPE=wayland \
  WAYLAND_DISPLAY="${wayland_display}" \
  DISPLAY="${display}" \
  QT_QPA_PLATFORM=xcb \
  QT_QUICK_BACKEND=software \
  LIBGL_ALWAYS_SOFTWARE=1 \
  systemsettings >/tmp/aurora-c3-x11-client.log 2>&1 &
x11_client_pid=$!
set -e

x11_client_ready=0
for _ in $(seq 1 30); do
  if kill -0 "${x11_client_pid}" >/dev/null 2>&1 \
    && pgrep -u "${ci_uid}" -f 'Xwayland' >/dev/null 2>&1; then
    x11_client_ready=1
    break
  fi
  sleep 1
done
if [[ "${x11_client_ready}" -ne 1 ]]; then
  cat /tmp/aurora-c3-x11-client.log || true
  fail "Qt X11 client did not stay running through XWayland"
fi

x11_env="$(tr '\0' '\n' <"/proc/${x11_client_pid}/environ" 2>/dev/null || true)"
grep -Fxq 'QT_QPA_PLATFORM=xcb' <<<"${x11_env}" || fail "X11 smoke-test client was not forced onto the Qt XCB platform"
echo "AURORA_C3_XWAYLAND_SUCCESS"

kill "${x11_client_pid}" >/dev/null 2>&1 || true
wait "${x11_client_pid}" 2>/dev/null || true

sleep 10
kill -0 "${kwin_pid}" >/dev/null 2>&1 || fail "KWin Wayland did not remain stable through the C3 probe"
kill -0 "${plasma_pid}" >/dev/null 2>&1 || fail "plasmashell did not remain stable through the C3 probe"
[[ "$(pgrep -u "${ci_uid}" -x kwin_wayland | head -n1)" == "${kwin_pid}" ]] || fail "KWin Wayland restarted during the C3 probe"
[[ "$(pgrep -u "${ci_uid}" -x plasmashell | head -n1)" == "${plasma_pid}" ]] || fail "plasmashell restarted during the C3 probe"

echo "AURORA_C3_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${ROOTFS}/usr/local/libexec/aurora-ci-c3-check"

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c3-check.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C3 Plasma Wayland session validation probe
After=graphical.target sddm.service systemd-logind.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c3-check
TimeoutStartSec=240
SERVICE

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c3-check.timer" <<'TIMER'
[Unit]
Description=Run SupraLINUX Aurora C3 Plasma Wayland session validation probe

[Timer]
OnBootSec=20s
AccuracySec=1s
Unit=aurora-ci-c3-check.service

[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c3-check.timer "${ROOTFS}/etc/systemd/system/timers.target.wants/aurora-ci-c3-check.timer"

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

cp "${ROOTFS}/boot/${kernel_path}" "${BUILD_DIR}/aurora-c3-vmlinuz"
cp "${ROOTFS}/boot/${initrd_path}" "${BUILD_DIR}/aurora-c3-initrd.img"
sync
umount "${ROOTFS}"

echo "==> Booting Aurora C3 VM with kernel ${kernel_version}"
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
    -smp 4 \
    -m 4096 \
    -no-reboot \
    -display none \
    -monitor none \
    -serial stdio \
    -vga none \
    -device virtio-vga \
    -kernel "${BUILD_DIR}/aurora-c3-vmlinuz" \
    -initrd "${BUILD_DIR}/aurora-c3-initrd.img" \
    -append "root=/dev/vda rw rootfstype=ext4 console=ttyS0,115200n8 systemd.unit=graphical.target systemd.show_status=true systemd.log_target=console panic=-1" \
    -drive "file=${IMAGE},format=raw,if=virtio,cache=unsafe" \
    -device virtio-rng-pci \
    2>&1 | tee "${SERIAL_LOG}"
qemu_status=${PIPESTATUS[0]}
set -e

mkdir -p "${ROOTFS}"
mount -o loop,ro "${IMAGE}" "${ROOTFS}"
if [[ -f "${ROOTFS}/home/${CI_USER}/.local/share/sddm/wayland-session.log" ]]; then
  cp "${ROOTFS}/home/${CI_USER}/.local/share/sddm/wayland-session.log" "${SESSION_LOG}"
else
  : >"${SESSION_LOG}"
fi
umount "${ROOTFS}"

if [[ ${qemu_status} -eq 124 ]]; then
  echo "Aurora C3 VM timed out after ${BOOT_TIMEOUT} seconds." >&2
  exit 1
fi
if [[ ${qemu_status} -ne 0 ]]; then
  echo "Aurora C3 QEMU exited with status ${qemu_status}." >&2
  exit 1
fi

success_count="$(grep -Fc 'AURORA_C3_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C3 success marker, observed ${success_count}." >&2
  exit 1
fi
if grep -Fq 'AURORA_C3_FAILURE:' "${SERIAL_LOG}"; then
  echo "Aurora C3 guest probe reported failure." >&2
  exit 1
fi
xwayland_success_count="$(grep -Fc 'AURORA_C3_XWAYLAND_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${xwayland_success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C3 XWayland success marker, observed ${xwayland_success_count}." >&2
  exit 1
fi

echo "Aurora C3 Plasma Wayland session validation passed."
