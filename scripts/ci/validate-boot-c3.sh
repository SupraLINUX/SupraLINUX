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

echo "==> Configuring C3 guest locale"
if [[ ! -x "${ROOTFS}/usr/sbin/update-locale" ]]; then
  echo "update-locale is unavailable in the Aurora rootfs." >&2
  exit 1
fi
chroot "${ROOTFS}" /usr/sbin/update-locale LANG=C.UTF-8

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

cat >"${ROOTFS}/etc/sddm.conf.d/99-aurora-ci-c3-autologin.conf" <<EOF_AUTLOGIN
[Autologin]
User=${CI_USER}
Session=${plasma_wayland_session}
Relogin=false
EOF_AUTLOGIN

mkdir -p "${ROOTFS}/usr/local/libexec" "${ROOTFS}/etc/systemd/system/timers.target.wants"
cat >"${ROOTFS}/usr/local/libexec/aurora-ci-c3-check" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"

session_id=""
ci_uid=""
ci_home=""
runtime_dir=""
current_stage="INIT"

stage() {
  current_stage="$1"
  echo "AURORA_C3_STAGE=${current_stage}"
}

run_user() {
  runuser -u "${CI_USER}" -- env \
    HOME="${ci_home}" \
    USER="${CI_USER}" \
    LOGNAME="${CI_USER}" \
    XDG_RUNTIME_DIR="${runtime_dir}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime_dir}/bus" \
    "$@"
}

first_user_pid() {
  local process_name="$1"
  pgrep -o -u "${ci_uid}" -x "${process_name}" 2>/dev/null || true
}

wait_for_user_process() {
  local process_name="$1"
  local timeout_seconds="$2"
  local i
  for ((i = 0; i < timeout_seconds; i++)); do
    if pgrep -u "${ci_uid}" -x "${process_name}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_user_unit() {
  local unit="$1"
  local timeout_seconds="$2"
  local i
  for ((i = 0; i < timeout_seconds; i++)); do
    if run_user systemctl --user is-active --quiet "${unit}"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

dump_diagnostics() {
  echo "AURORA_C3_DIAGNOSTICS_START"
  echo "AURORA_C3_LAST_STAGE=${current_stage}"
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
    echo "--- user environment ---"
    run_user systemctl --user show-environment || true
    echo "--- user systemd failed units ---"
    run_user systemctl --user --failed --no-pager --plain || true
    echo "--- graphical session target ---"
    run_user systemctl --user status graphical-session.target --no-pager --full || true
    echo "--- Plasma session targets/services ---"
    run_user systemctl --user status plasma-workspace-wayland.target plasma-workspace.target plasma-plasmashell.service --no-pager --full || true
    echo "--- desktop integration services ---"
    run_user systemctl --user status xdg-desktop-portal.service xdg-desktop-portal-kde.service pipewire.service wireplumber.service plasma-polkit-agent.service --no-pager --full || true
    echo "--- user systemd Plasma units ---"
    run_user systemctl --user list-units 'plasma*' --no-pager --plain || true
    echo "--- user bus names ---"
    run_user busctl --user --no-pager list || true
  fi
  echo "--- SDDM journal ---"
  journalctl -b -u sddm.service --no-pager -n 300 || true
  echo "--- disposable user Wayland session log ---"
  cat "/home/${CI_USER}/.local/share/sddm/wayland-session.log" 2>/dev/null || true
  echo "--- Xresources query log ---"
  cat /tmp/aurora-c3-xrdb-query.log 2>/dev/null || true
  echo "--- XWayland smoke-test client log ---"
  cat /tmp/aurora-c3-x11-client.log 2>/dev/null || true
  echo "AURORA_C3_DIAGNOSTICS_END"
}

fail() {
  local message="$*"
  trap - ERR
  set +e
  echo "AURORA_C3_FAILURE: ${current_stage}: ${message}"
  dump_diagnostics
  systemctl poweroff --no-block || true
  exit 1
}

unexpected_error() {
  local status=$?
  local line="${BASH_LINENO[0]:-unknown}"
  trap - ERR
  set +e
  echo "AURORA_C3_FAILURE: ${current_stage}: unexpected shell error status ${status} at line ${line}"
  dump_diagnostics
  systemctl poweroff --no-block || true
  exit "${status}"
}
trap unexpected_error ERR

echo "AURORA_C3_CHECK_START"

stage SYSTEM
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
passwd_entry="$(getent passwd "${CI_USER}" 2>/dev/null || true)"
ci_home="$(awk -F: '{print $6}' <<<"${passwd_entry}")"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable C3 user is missing"
runtime_dir="/run/user/${ci_uid}"

stage LOGIN
session_ready=0
for ((i = 0; i < 120; i++)); do
  sessions="$(loginctl list-sessions --no-legend 2>/dev/null || true)"
  session_id="$(awk -v uid="${ci_uid}" '$2 == uid { print $1; exit }' <<<"${sessions}")"
  if [[ -n "${session_id}" ]] \
    && [[ "$(loginctl show-session "${session_id}" -p Active --value 2>/dev/null || true)" == "yes" ]]; then
    session_ready=1
    break
  fi
  sleep 1
done
[[ "${session_ready}" -eq 1 ]] || fail "disposable user did not obtain an active login session"
session_name="$(loginctl show-session "${session_id}" -p Name --value 2>/dev/null || true)"
session_remote="$(loginctl show-session "${session_id}" -p Remote --value 2>/dev/null || true)"
[[ "${session_name}" == "${CI_USER}" ]] || fail "login session belongs to unexpected user (${session_name:-unknown})"
[[ "${session_remote}" == "no" ]] || fail "C3 login unexpectedly reports a remote session (${session_remote:-unknown})"

stage WAYLAND
session_type="$(loginctl show-session "${session_id}" -p Type --value 2>/dev/null || true)"
[[ "${session_type}" == "wayland" ]] || fail "login session is not Wayland (${session_type:-unknown})"

stage USER_DBUS
user_bus_ready=0
for ((i = 0; i < 30; i++)); do
  if [[ -S "${runtime_dir}/bus" ]] && run_user busctl --user --no-pager list >/dev/null 2>&1; then
    user_bus_ready=1
    break
  fi
  sleep 1
done
[[ "${user_bus_ready}" -eq 1 ]] || fail "user D-Bus session did not become usable"

stage GRAPHICAL_SESSION
wait_for_user_unit graphical-session.target 60 || fail "graphical-session.target did not become active"

stage KWIN
wait_for_user_process kwin_wayland 30 || fail "KWin Wayland did not become ready"
kwin_pid="$(first_user_pid kwin_wayland)"
[[ -n "${kwin_pid}" ]] || fail "KWin Wayland process is missing"

stage PLASMASHELL
wait_for_user_process plasmashell 30 || fail "plasmashell did not become ready"
plasma_pid="$(first_user_pid plasmashell)"
[[ -n "${plasma_pid}" ]] || fail "plasmashell process is missing"

plasma_env="$(tr '\0' '\n' <"/proc/${plasma_pid}/environ" 2>/dev/null || true)"
grep -Fxq 'XDG_SESSION_TYPE=wayland' <<<"${plasma_env}" || fail "plasmashell environment is not Wayland"
grep -Fxq 'LANG=C.UTF-8' <<<"${plasma_env}" || fail "plasmashell did not inherit LANG=C.UTF-8"
wayland_display="$(awk -F= '$1=="WAYLAND_DISPLAY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
display="$(awk -F= '$1=="DISPLAY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
xauthority="$(awk -F= '$1=="XAUTHORITY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
[[ -n "${wayland_display}" ]] || fail "WAYLAND_DISPLAY is missing from the Plasma session"
[[ -S "${runtime_dir}/${wayland_display}" ]] || fail "Wayland display socket ${runtime_dir}/${wayland_display} is missing"
[[ -n "${display}" ]] || fail "DISPLAY is missing; XWayland compatibility is unavailable"
[[ -n "${xauthority}" ]] || fail "XAUTHORITY is missing from the Plasma session"
runuser -u "${CI_USER}" -- test -r "${xauthority}" || fail "Xauthority file ${xauthority} is not readable by the Plasma user"

stage PLASMA_TARGETS
wait_for_user_unit plasma-workspace-wayland.target 30 || fail "plasma-workspace-wayland.target did not become active"
wait_for_user_unit plasma-workspace.target 30 || fail "plasma-workspace.target did not become active"
wait_for_user_unit plasma-plasmashell.service 30 || fail "plasma-plasmashell.service did not become active"

stage LOOKANDFEEL_DEFAULTS
look_and_feel_package="$(run_user kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage 2>/dev/null || true)"
if [[ -z "${look_and_feel_package}" ]]; then
  look_and_feel_package="org.kde.breeze.desktop"
fi
look_and_feel_state="${ci_home}/.config/kdedefaults/package"
look_and_feel_state_ready=0
for ((i = 0; i < 20; i++)); do
  if runuser -u "${CI_USER}" -- test -r "${look_and_feel_state}"; then
    look_and_feel_state_value="$(runuser -u "${CI_USER}" -- cat "${look_and_feel_state}" 2>/dev/null || true)"
    if [[ "${look_and_feel_state_value}" == "${look_and_feel_package}" ]]; then
      look_and_feel_state_ready=1
      break
    fi
  fi
  sleep 1
done
[[ "${look_and_feel_state_ready}" -eq 1 ]] \
  || fail "Plasma did not persist kdedefaults/package for configured LookAndFeelPackage ${look_and_feel_package}"
echo "AURORA_C3_LOOKANDFEEL_DEFAULTS_SUCCESS"

stage XRESOURCES
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
  XAUTHORITY="${xauthority}" \
  xrdb -query >/tmp/aurora-c3-xrdb-query.log 2>&1
xrdb_status=$?
set -e
[[ "${xrdb_status}" -eq 0 ]] || fail "xrdb could not query the live XWayland resource database"
grep -Eq '^Xft\.dpi:[[:space:]]*[0-9]+([.][0-9]+)?[[:space:]]*$' /tmp/aurora-c3-xrdb-query.log \
  || fail "Xft.dpi is missing from the live XWayland resource database"
echo "AURORA_C3_XRESOURCES_SUCCESS"

stage PIPEWIRE
run_user systemctl --user start pipewire.service || fail "pipewire.service could not start"
wait_for_user_unit pipewire.service 20 || fail "pipewire.service did not become active"

stage WIREPLUMBER
run_user systemctl --user start wireplumber.service || fail "wireplumber.service could not start"
wait_for_user_unit wireplumber.service 20 || fail "wireplumber.service did not become active"

stage POLKIT
run_user systemctl --user start plasma-polkit-agent.service || fail "Plasma Polkit agent service could not start"
wait_for_user_unit plasma-polkit-agent.service 20 || fail "plasma-polkit-agent.service did not become active"

stage PORTAL
run_user busctl --user call \
  org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
  StartServiceByName su org.freedesktop.portal.Desktop 0 >/dev/null \
  || fail "xdg-desktop-portal could not be D-Bus activated"
run_user busctl --user call \
  org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
  StartServiceByName su org.freedesktop.impl.portal.desktop.kde 0 >/dev/null \
  || fail "KDE portal backend could not be D-Bus activated"

portal_ready=0
for ((i = 0; i < 30; i++)); do
  bus_names="$(run_user busctl --user --no-pager list 2>/dev/null || true)"
  if grep -Fq 'org.freedesktop.portal.Desktop' <<<"${bus_names}" \
    && grep -Fq 'org.freedesktop.impl.portal.desktop.kde' <<<"${bus_names}"; then
    portal_ready=1
    break
  fi
  sleep 1
done
[[ "${portal_ready}" -eq 1 ]] || fail "desktop portal or KDE portal backend did not register on the user bus"

stage XWAYLAND
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
  XAUTHORITY="${xauthority}" \
  QT_QPA_PLATFORM=xcb \
  QT_QUICK_BACKEND=software \
  LIBGL_ALWAYS_SOFTWARE=1 \
  systemsettings >/tmp/aurora-c3-x11-client.log 2>&1 &
x11_launcher_pid=$!
set -e

x11_client_pid=""
x11_client_ready=0
for ((i = 0; i < 30; i++)); do
  x11_client_pid="$(pgrep -n -u "${ci_uid}" -x systemsettings 2>/dev/null || true)"
  if [[ -n "${x11_client_pid}" ]] \
    && kill -0 "${x11_client_pid}" >/dev/null 2>&1 \
    && pgrep -u "${ci_uid}" -f 'Xwayland' >/dev/null 2>&1; then
    x11_client_ready=1
    break
  fi
  sleep 1
done
if [[ "${x11_client_ready}" -ne 1 ]]; then
  fail "Qt X11 client did not stay running through XWayland"
fi

x11_env="$(tr '\0' '\n' <"/proc/${x11_client_pid}/environ" 2>/dev/null || true)"
grep -Fxq 'QT_QPA_PLATFORM=xcb' <<<"${x11_env}" || fail "X11 smoke-test client was not forced onto the Qt XCB platform"
grep -Fxq "XAUTHORITY=${xauthority}" <<<"${x11_env}" || fail "X11 smoke-test client did not inherit the Plasma Xauthority file"
echo "AURORA_C3_XWAYLAND_SUCCESS"

kill "${x11_client_pid}" >/dev/null 2>&1 || true
kill "${x11_launcher_pid}" >/dev/null 2>&1 || true
wait "${x11_launcher_pid}" 2>/dev/null || true

stage STABILITY
sleep 10
kill -0 "${kwin_pid}" >/dev/null 2>&1 || fail "KWin Wayland did not remain stable through the C3 probe"
kill -0 "${plasma_pid}" >/dev/null 2>&1 || fail "plasmashell did not remain stable through the C3 probe"
[[ "$(first_user_pid kwin_wayland)" == "${kwin_pid}" ]] || fail "KWin Wayland restarted during the C3 probe"
[[ "$(first_user_pid plasmashell)" == "${plasma_pid}" ]] || fail "plasmashell restarted during the C3 probe"

stage COMPLETE
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
TimeoutStartSec=540
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

mapfile -t kernel_candidates < <(
  find "${ROOTFS}/boot" -maxdepth 1 -type f -name 'vmlinuz-*' -printf '%f\n'
)
if [[ "${#kernel_candidates[@]}" -eq 0 ]]; then
  echo "No installed Ubuntu kernel found in the Aurora rootfs." >&2
  exit 1
fi
mapfile -t sorted_kernels < <(printf '%s\n' "${kernel_candidates[@]}" | sort -V)
kernel_path="${sorted_kernels[${#sorted_kernels[@]}-1]}"
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
chmod 0644 "${SERIAL_LOG}" "${SESSION_LOG}"

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
lookandfeel_success_count="$(grep -Fc 'AURORA_C3_LOOKANDFEEL_DEFAULTS_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${lookandfeel_success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C3 Look-and-Feel defaults success marker, observed ${lookandfeel_success_count}." >&2
  exit 1
fi
xresources_success_count="$(grep -Fc 'AURORA_C3_XRESOURCES_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${xresources_success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C3 Xresources success marker, observed ${xresources_success_count}." >&2
  exit 1
fi
xwayland_success_count="$(grep -Fc 'AURORA_C3_XWAYLAND_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${xwayland_success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C3 XWayland success marker, observed ${xwayland_success_count}." >&2
  exit 1
fi

for required_stage in SYSTEM LOGIN WAYLAND USER_DBUS GRAPHICAL_SESSION KWIN PLASMASHELL PLASMA_TARGETS LOOKANDFEEL_DEFAULTS XRESOURCES PIPEWIRE WIREPLUMBER POLKIT PORTAL XWAYLAND STABILITY COMPLETE; do
  stage_count="$(grep -Fc "AURORA_C3_STAGE=${required_stage}" "${SERIAL_LOG}" || true)"
  if [[ "${stage_count}" -ne 1 ]]; then
    echo "Expected exactly one Aurora C3 ${required_stage} stage marker, observed ${stage_count}." >&2
    exit 1
  fi
done

echo "Aurora C3 Plasma Wayland session validation passed."
