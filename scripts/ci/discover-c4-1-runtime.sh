#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "discover-c4-1-runtime.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
KERNEL="${BUILD_DIR}/aurora-c4-0-vmlinuz"
INITRD="${BUILD_DIR}/aurora-c4-0-initrd.img"
MOUNT_DIR="${BUILD_DIR}/aurora-c4-1-discovery-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c4-1-discovery-serial.log"
SESSION_LOG="${BUILD_DIR}/aurora-c4-1-discovery-wayland-session.log"
OUT_DIR="${BUILD_DIR}/c4-1-discovery"
BOOT_TIMEOUT="${AURORA_C4_1_BOOT_TIMEOUT:-600}"
CI_USER="auroraci"

for file in "${IMAGE}" "${KERNEL}" "${INITRD}"; do
  [[ -f "${file}" ]] || {
    echo "Missing C4.1 prerequisite file: ${file}" >&2
    exit 1
  }
done

for tool in mount umount mountpoint qemu-system-x86_64 timeout; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Missing required tool: ${tool}" >&2
    exit 1
  }
done

mkdir -p "${BUILD_DIR}" "${MOUNT_DIR}"
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
rm -f "${SERIAL_LOG}" "${SESSION_LOG}"

cleanup() {
  set +e
  if mountpoint -q "${MOUNT_DIR}"; then
    umount "${MOUNT_DIR}" >/dev/null 2>&1 || umount -l "${MOUNT_DIR}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

mount -o loop,rw "${IMAGE}" "${MOUNT_DIR}"

# The accepted C4.0 timer is a prerequisite probe, not part of the product.
# Disable it for the second boot so C4.1 discovery has sole ownership of the
# serial success/failure channel.
rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-0-check.timer"
rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1-discovery.timer"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1-discovery.service"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1-discovery.timer"
rm -f "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1-discovery"
rm -rf "${MOUNT_DIR}/var/lib/aurora-ci-c4-1-discovery"

mkdir -p "${MOUNT_DIR}/usr/local/libexec" "${MOUNT_DIR}/etc/systemd/system/timers.target.wants"
cat >"${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1-discovery" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"
OUT="/var/lib/aurora-ci-c4-1-discovery"
current_stage="INIT"
session_id=""
ci_uid=""
ci_home=""
runtime_dir=""
kwin_pid=""
plasma_pid=""
wayland_display=""
display=""
xauthority=""
session_lang=""
xdg_current_desktop=""
xdg_config_dirs=""
xdg_data_dirs=""

mkdir -p "${OUT}" "${OUT}/command-help" "${OUT}/dbus" "${OUT}/config"

stage() {
  current_stage="$1"
  echo "AURORA_C4_1_DISCOVERY_STAGE=${current_stage}"
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

run_user_session() {
  runuser -u "${CI_USER}" -- env \
    HOME="${ci_home}" \
    USER="${CI_USER}" \
    LOGNAME="${CI_USER}" \
    LANG="${session_lang}" \
    XDG_RUNTIME_DIR="${runtime_dir}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime_dir}/bus" \
    XDG_SESSION_TYPE=wayland \
    XDG_CURRENT_DESKTOP="${xdg_current_desktop}" \
    XDG_CONFIG_DIRS="${xdg_config_dirs}" \
    XDG_DATA_DIRS="${xdg_data_dirs}" \
    WAYLAND_DISPLAY="${wayland_display}" \
    DISPLAY="${display}" \
    XAUTHORITY="${xauthority}" \
    QT_QPA_PLATFORM=wayland \
    "$@"
}

first_user_pid() {
  pgrep -o -u "${ci_uid}" -x "$1" 2>/dev/null || true
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

dump_diagnostics() {
  echo "AURORA_C4_1_DISCOVERY_DIAGNOSTICS_START"
  echo "AURORA_C4_1_DISCOVERY_LAST_STAGE=${current_stage}"
  systemctl --failed --no-pager --plain || true
  systemctl status sddm.service --no-pager --full || true
  loginctl list-sessions --no-pager || true
  if [[ -n "${session_id}" ]]; then
    loginctl session-status "${session_id}" --no-pager || true
    loginctl show-session "${session_id}" --all --no-pager || true
  fi
  if [[ -n "${ci_uid}" ]]; then
    pgrep -a -u "${ci_uid}" || true
  fi
  if [[ -n "${runtime_dir}" && -S "${runtime_dir}/bus" ]]; then
    run_user systemctl --user --failed --no-pager --plain || true
    run_user busctl --user --no-pager list || true
  fi
  journalctl -b -u sddm.service --no-pager -n 250 || true
  cat "/home/${CI_USER}/.local/share/sddm/wayland-session.log" 2>/dev/null || true
  echo "AURORA_C4_1_DISCOVERY_DIAGNOSTICS_END"
}

fail() {
  local message="$*"
  trap - ERR
  set +e
  echo "AURORA_C4_1_DISCOVERY_FAILURE: ${current_stage}: ${message}"
  dump_diagnostics
  sync
  systemctl poweroff --no-block || true
  exit 1
}

unexpected_error() {
  local status=$?
  local line="${BASH_LINENO[0]:-unknown}"
  trap - ERR
  set +e
  echo "AURORA_C4_1_DISCOVERY_FAILURE: ${current_stage}: unexpected shell error status ${status} at line ${line}"
  dump_diagnostics
  sync
  systemctl poweroff --no-block || true
  exit "${status}"
}
trap unexpected_error ERR

echo "AURORA_C4_1_DISCOVERY_START"

stage SESSION
[[ "$(cat /proc/1/comm)" == "systemd" ]] || fail "PID 1 is not systemd"
systemctl is-active --quiet graphical.target || fail "graphical.target is not active"
command -v runuser >/dev/null 2>&1 || fail "runuser is unavailable"
command -v busctl >/dev/null 2>&1 || fail "busctl is unavailable"

ci_uid="$(id -u "${CI_USER}" 2>/dev/null || true)"
passwd_entry="$(getent passwd "${CI_USER}" 2>/dev/null || true)"
ci_home="$(awk -F: '{print $6}' <<<"${passwd_entry}")"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable C4.1 user is missing"
runtime_dir="/run/user/${ci_uid}"

session_ready=0
for ((i = 0; i < 120; i++)); do
  sessions="$(loginctl list-sessions --no-legend 2>/dev/null || true)"
  session_id="$(awk -v uid="${ci_uid}" '$2 == uid { print $1; exit }' <<<"${sessions}")"
  if [[ -n "${session_id}" ]] \
    && [[ "$(loginctl show-session "${session_id}" -p Active --value 2>/dev/null || true)" == "yes" ]] \
    && [[ "$(loginctl show-session "${session_id}" -p Type --value 2>/dev/null || true)" == "wayland" ]]; then
    session_ready=1
    break
  fi
  sleep 1
done
[[ "${session_ready}" -eq 1 ]] || fail "disposable user did not obtain an active Wayland session"

user_bus_ready=0
for ((i = 0; i < 30; i++)); do
  if [[ -S "${runtime_dir}/bus" ]] && run_user busctl --user --no-pager list >/dev/null 2>&1; then
    user_bus_ready=1
    break
  fi
  sleep 1
done
[[ "${user_bus_ready}" -eq 1 ]] || fail "user D-Bus did not become usable"

wait_for_user_process kwin_wayland 30 || fail "KWin Wayland did not become ready"
wait_for_user_process plasmashell 30 || fail "plasmashell did not become ready"
kwin_pid="$(first_user_pid kwin_wayland)"
plasma_pid="$(first_user_pid plasmashell)"
[[ -n "${kwin_pid}" && -n "${plasma_pid}" ]] || fail "Plasma session processes are incomplete"

plasma_env="$(tr '\0' '\n' <"/proc/${plasma_pid}/environ" 2>/dev/null || true)"
printf '%s\n' "${plasma_env}" | sort >"${OUT}/plasma-environment.txt"
xdg_current_desktop="$(awk -F= '$1=="XDG_CURRENT_DESKTOP" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
wayland_display="$(awk -F= '$1=="WAYLAND_DISPLAY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
display="$(awk -F= '$1=="DISPLAY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
xauthority="$(awk -F= '$1=="XAUTHORITY" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
session_lang="$(awk -F= '$1=="LANG" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
xdg_config_dirs="$(awk -F= '$1=="XDG_CONFIG_DIRS" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
xdg_data_dirs="$(awk -F= '$1=="XDG_DATA_DIRS" {sub(/^[^=]*=/, ""); print; exit}' <<<"${plasma_env}")"
[[ -n "${session_lang}" ]] || session_lang=C.UTF-8
[[ -n "${xdg_config_dirs}" ]] || xdg_config_dirs=/etc/xdg
[[ -n "${xdg_data_dirs}" ]] || xdg_data_dirs=/usr/local/share:/usr/share
grep -Eq '(^|:)KDE(:|$)' <<<"${xdg_current_desktop}" || fail "XDG_CURRENT_DESKTOP does not identify KDE"
[[ -n "${wayland_display}" && -S "${runtime_dir}/${wayland_display}" ]] || fail "live Wayland socket is missing"
[[ -n "${display}" ]] || fail "DISPLAY is missing"
[[ -n "${xauthority}" && -f "${xauthority}" ]] || fail "XAUTHORITY is missing"

stage COMMANDS
commands=(
  kcmshell6 kreadconfig6 kwriteconfig6 kpackagetool6
  balooctl6 kscreen-doctor
  plasma-apply-lookandfeel plasma-apply-colorscheme plasma-apply-cursortheme
  plasma-apply-desktoptheme plasma-apply-wallpaperimage lookandfeeltool
  plasma-interactiveconsole systemsettings
  xdg-mime kioclient6 qdbus6 qdbus
)
: >"${OUT}/command-paths.tsv"
for command_name in "${commands[@]}"; do
  command_path="$(command -v "${command_name}" 2>/dev/null || true)"
  if [[ -n "${command_path}" ]]; then
    printf '%s\t%s\n' "${command_name}" "${command_path}" >>"${OUT}/command-paths.tsv"
    timeout 8s "${command_path}" --help >"${OUT}/command-help/${command_name}.txt" 2>&1 || true
  else
    printf '%s\tMISSING\n' "${command_name}" >>"${OUT}/command-paths.tsv"
  fi
done

if command -v plasma-apply-lookandfeel >/dev/null 2>&1; then
  run_user_session timeout 10s plasma-apply-lookandfeel --list >"${OUT}/lookandfeel-list.txt" 2>&1 || true
fi
if command -v plasma-apply-colorscheme >/dev/null 2>&1; then
  run_user_session timeout 10s plasma-apply-colorscheme --list-schemes >"${OUT}/colorscheme-list.txt" 2>&1 || true
fi
if command -v plasma-apply-cursortheme >/dev/null 2>&1; then
  run_user_session timeout 10s plasma-apply-cursortheme --list-themes >"${OUT}/cursortheme-list.txt" 2>&1 || true
fi
if command -v plasma-apply-desktoptheme >/dev/null 2>&1; then
  run_user_session timeout 10s plasma-apply-desktoptheme --list-themes >"${OUT}/desktoptheme-list.txt" 2>&1 || true
fi

stage DBUS
run_user busctl --user --no-pager list >"${OUT}/user-bus-names.txt" 2>&1 || true
busctl --system --no-pager list >"${OUT}/system-bus-names.txt" 2>&1 || true

services=(
  org.kde.KWin
  org.kde.ActivityManager
  org.kde.kglobalaccel
  org.kde.plasmashell
  org.kde.KScreen
  org.freedesktop.ScreenSaver
)
: >"${OUT}/dbus/service-presence.tsv"
for service in "${services[@]}"; do
  safe_name="${service//./_}"
  if grep -Eq "^${service}[[:space:]]" "${OUT}/user-bus-names.txt"; then
    printf '%s\tPRESENT\n' "${service}" >>"${OUT}/dbus/service-presence.tsv"
    run_user timeout 15s busctl --user --no-pager tree "${service}" >"${OUT}/dbus/${safe_name}-tree.txt" 2>&1 || true
    : >"${OUT}/dbus/${safe_name}-introspection.txt"
    while IFS= read -r object_path; do
      [[ -n "${object_path}" ]] || continue
      echo "===== ${service} ${object_path} =====" >>"${OUT}/dbus/${safe_name}-introspection.txt"
      run_user timeout 10s busctl --user --no-pager introspect "${service}" "${object_path}" \
        >>"${OUT}/dbus/${safe_name}-introspection.txt" 2>&1 || true
      echo >>"${OUT}/dbus/${safe_name}-introspection.txt"
    done < <(sed -nE 's#^[^/]*(/[^[:space:]]*).*#\1#p' "${OUT}/dbus/${safe_name}-tree.txt" | sort -u)
  else
    printf '%s\tABSENT\n' "${service}" >>"${OUT}/dbus/service-presence.tsv"
  fi
done

stage STATE
if command -v kscreen-doctor >/dev/null 2>&1; then
  run_user_session timeout 15s kscreen-doctor -o >"${OUT}/kscreen-doctor-output.txt" 2>&1 || true
fi
if command -v balooctl6 >/dev/null 2>&1; then
  run_user_session timeout 15s balooctl6 status >"${OUT}/baloo-status.txt" 2>&1 || true
fi
if command -v kpackagetool6 >/dev/null 2>&1; then
  run_user_session timeout 15s kpackagetool6 --type=KWin/Script --list --global >"${OUT}/kwin-scripts-global.txt" 2>&1 || true
  run_user_session timeout 15s kpackagetool6 --type=KWin/Script --list >"${OUT}/kwin-scripts-user.txt" 2>&1 || true
fi
if command -v kcmshell6 >/dev/null 2>&1; then
  run_user_session timeout 15s kcmshell6 --list >"${OUT}/kcmshell6-list.txt" 2>&1 || true
fi

run_user systemctl --user --failed --no-pager --plain >"${OUT}/user-failed-units.txt" 2>&1 || true
systemctl --failed --no-pager --plain >"${OUT}/system-failed-units.txt" 2>&1 || true
run_user systemctl --user list-unit-files --no-pager >"${OUT}/user-unit-files.txt" 2>&1 || true

find "${ci_home}/.config" -maxdepth 2 -type f -printf '%P\n' 2>/dev/null | sort >"${OUT}/user-config-files.txt" || true
config_files=(
  kdeglobals kwinrc kglobalshortcutsrc baloofilerc kxkbrc kscreenlockerrc
  plasmarc ksmserverrc krunnerrc plasmanotifyrc kcminputrc
  plasma-org.kde.plasma.desktop-appletsrc
)
for config_name in "${config_files[@]}"; do
  source_file="${ci_home}/.config/${config_name}"
  if [[ -f "${source_file}" ]]; then
    cp "${source_file}" "${OUT}/config/${config_name}"
  fi
done

stage PACKAGES
packages=(
  plasma-desktop plasma-workspace kwin-wayland kscreen systemsettings
  kactivitymanagerd baloo6 plasma-workspace-wayland
)
: >"${OUT}/package-versions.tsv"
for package in "${packages[@]}"; do
  version="$(dpkg-query -W -f='${Version}' "${package}" 2>/dev/null || true)"
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  printf '%s\t%s\t%s\n' "${package}" "${version:-MISSING}" "${status:-MISSING}" >>"${OUT}/package-versions.tsv"
done

stage STABILITY
sleep 5
kill -0 "${kwin_pid}" >/dev/null 2>&1 || fail "KWin Wayland exited during discovery"
kill -0 "${plasma_pid}" >/dev/null 2>&1 || fail "plasmashell exited during discovery"
[[ "$(first_user_pid kwin_wayland)" == "${kwin_pid}" ]] || fail "KWin Wayland restarted during discovery"
[[ "$(first_user_pid plasmashell)" == "${plasma_pid}" ]] || fail "plasmashell restarted during discovery"

stage COMPLETE
echo "AURORA_C4_1_DISCOVERY_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1-discovery"

cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1-discovery.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C4.1 runtime contract discovery
After=graphical.target sddm.service systemd-logind.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c4-1-discovery
TimeoutStartSec=360
SERVICE

cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1-discovery.timer" <<'TIMER'
[Unit]
Description=Run SupraLINUX Aurora C4.1 runtime contract discovery

[Timer]
OnBootSec=20s
AccuracySec=1s
Unit=aurora-ci-c4-1-discovery.service

[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c4-1-discovery.timer "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1-discovery.timer"

sync
umount "${MOUNT_DIR}"

echo "==> Booting Aurora C4.1 runtime discovery VM"
qemu_accel=(-accel tcg -cpu max)
if [[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
  qemu_accel=(-enable-kvm -cpu host)
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
    -kernel "${KERNEL}" \
    -initrd "${INITRD}" \
    -append "root=/dev/vda rw rootfstype=ext4 console=ttyS0,115200n8 systemd.unit=graphical.target systemd.show_status=true systemd.log_target=console panic=-1" \
    -drive "file=${IMAGE},format=raw,if=virtio,cache=unsafe" \
    -device virtio-rng-pci \
    2>&1 | tee "${SERIAL_LOG}"
qemu_status=${PIPESTATUS[0]}
set -e

mount -o loop,ro "${IMAGE}" "${MOUNT_DIR}"
if [[ -d "${MOUNT_DIR}/var/lib/aurora-ci-c4-1-discovery" ]]; then
  cp -a "${MOUNT_DIR}/var/lib/aurora-ci-c4-1-discovery/." "${OUT_DIR}/"
fi
if [[ -f "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" ]]; then
  cp "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" "${SESSION_LOG}"
else
  : >"${SESSION_LOG}"
fi
umount "${MOUNT_DIR}"

chmod 0644 "${SERIAL_LOG}" "${SESSION_LOG}" 2>/dev/null || true
find "${OUT_DIR}" -type f -exec chmod 0644 {} + 2>/dev/null || true

if [[ ${qemu_status} -eq 124 ]]; then
  echo "Aurora C4.1 discovery VM timed out after ${BOOT_TIMEOUT} seconds." >&2
  exit 1
fi
if [[ ${qemu_status} -ne 0 ]]; then
  echo "Aurora C4.1 discovery QEMU exited with status ${qemu_status}." >&2
  exit 1
fi

success_count="$(grep -Fc 'AURORA_C4_1_DISCOVERY_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${success_count}" -ne 1 ]]; then
  echo "Expected exactly one C4.1 discovery success marker, observed ${success_count}." >&2
  exit 1
fi
if grep -Fq 'AURORA_C4_1_DISCOVERY_FAILURE:' "${SERIAL_LOG}"; then
  echo "Aurora C4.1 runtime discovery reported failure." >&2
  exit 1
fi

for required_stage in SESSION COMMANDS DBUS STATE PACKAGES STABILITY COMPLETE; do
  stage_count="$(grep -Fc "AURORA_C4_1_DISCOVERY_STAGE=${required_stage}" "${SERIAL_LOG}" || true)"
  if [[ "${stage_count}" -ne 1 ]]; then
    echo "Expected exactly one C4.1 discovery ${required_stage} stage marker, observed ${stage_count}." >&2
    exit 1
  fi
done

[[ -s "${OUT_DIR}/command-paths.tsv" ]] || {
  echo "C4.1 command inventory is missing." >&2
  exit 1
}
[[ -s "${OUT_DIR}/dbus/service-presence.tsv" ]] || {
  echo "C4.1 D-Bus service inventory is missing." >&2
  exit 1
}

echo "Aurora C4.1 runtime contract discovery completed successfully."
