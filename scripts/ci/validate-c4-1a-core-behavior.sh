#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-c4-1a-core-behavior.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
KERNEL="${BUILD_DIR}/aurora-c4-0-vmlinuz"
INITRD="${BUILD_DIR}/aurora-c4-0-initrd.img"
MOUNT_DIR="${BUILD_DIR}/aurora-c4-1a-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c4-1a-serial.log"
SESSION_LOG="${BUILD_DIR}/aurora-c4-1a-wayland-session.log"
OUT_DIR="${BUILD_DIR}/c4-1a-evidence"
BOOT_TIMEOUT="${AURORA_C4_1A_BOOT_TIMEOUT:-600}"
CI_USER="auroraci"

for file in "${IMAGE}" "${KERNEL}" "${INITRD}"; do
  [[ -f "${file}" ]] || {
    echo "Missing C4.1a prerequisite file: ${file}" >&2
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

# C4.0 is the accepted composition/surface prerequisite. Its runtime timer is
# disabled for the C4.1a boots so only this gate owns the serial acceptance
# channel. C4.1a deliberately uses two complete boots of the same disk: boot 1
# mutates and proves the configuration reached persistent storage; boot 2
# proves Plasma/KWin consume that persisted state, then restores the baseline.
rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-0-check.timer"
rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1-discovery.timer"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1-discovery.service"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1-discovery.timer"
rm -f "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1-discovery"
rm -rf "${MOUNT_DIR}/var/lib/aurora-ci-c4-1-discovery"
rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1a-check.timer"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1a-check.service"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1a-check.timer"
rm -f "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1a-check"
rm -rf "${MOUNT_DIR}/var/lib/aurora-ci-c4-1a"
rm -f "${MOUNT_DIR}/etc/sddm.conf.d/99-aurora-ci-c4-1a-relogin.conf"

mkdir -p "${MOUNT_DIR}/usr/local/libexec" "${MOUNT_DIR}/etc/systemd/system/timers.target.wants"
cat >"${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1a-check" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"
OUT="/var/lib/aurora-ci-c4-1a"
PHASE_FILE="${OUT}/phase"
STATE_FILE="${OUT}/phase-state"
ACTIVITY_NAME="Aurora-C4.1A-Test-Activity"
DESKTOP_NAME="Aurora-C4.1A-Test-Desktop"
INVALID_ID="00000000-0000-0000-0000-000000000000"
current_stage="INIT"
ci_uid=""
ci_home=""
runtime_dir=""
session_id=""
kwin_pid=""
plasma_pid=""
activity_id=""
desktop_id=""
baseline_activity=""
baseline_desktop=""
baseline_count=""
mutated_count=""
cleanup_done=0
phase=1

mkdir -p "${OUT}"
if [[ -f "${PHASE_FILE}" && "$(cat "${PHASE_FILE}" 2>/dev/null || true)" == "2" ]]; then
  phase=2
fi

stage() {
  current_stage="$1"
  echo "AURORA_C4_1A_STAGE=${current_stage}"
}

capability_pass() {
  echo "AURORA_C4_1A_CAPABILITY_PASS=$1"
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
  pgrep -o -u "${ci_uid}" -x "$1" 2>/dev/null || true
}

wait_until() {
  local timeout_seconds="$1"
  shift
  local i
  for ((i = 0; i < timeout_seconds; i++)); do
    if "$@"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

activity_call() {
  local method="$1"
  shift
  run_user qdbus6 \
    org.kde.ActivityManager \
    /ActivityManager/Activities \
    "org.kde.ActivityManager.Activities.${method}" \
    "$@"
}

activity_present() {
  activity_call ListActivities 2>/dev/null | grep -Fxq -- "$1"
}

activity_current_is() {
  [[ "$(activity_call CurrentActivity 2>/dev/null || true)" == "$1" ]]
}

vdm_property() {
  run_user busctl --user --no-pager get-property \
    org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager "$1"
}

vdm_count() {
  vdm_property count | awk '{print $2}'
}

vdm_current() {
  vdm_property current | sed -nE 's/^s "(.*)"$/\1/p'
}

vdm_count_is() {
  [[ "$(vdm_count)" == "$1" ]]
}

vdm_current_is() {
  [[ "$(vdm_current)" == "$1" ]]
}

vdm_dump() {
  vdm_property desktops
}

vdm_desktop_id_by_name() {
  local target_name="$1"
  vdm_dump | awk -v needle="\"${target_name}\"" '{for (i=2; i<=NF; i++) if ($i == needle) {gsub(/^"|"$/, "", $(i-1)); print $(i-1); exit}}'
}

bind_live_session() {
  local i sessions candidate
  session_id=""

  for ((i = 0; i < 120; i++)); do
    sessions="$(loginctl list-sessions --no-legend 2>/dev/null || true)"
    while read -r candidate _; do
      [[ -n "${candidate}" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p User --value 2>/dev/null || true)" == "${ci_uid}" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p Class --value 2>/dev/null || true)" == "user" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p Active --value 2>/dev/null || true)" == "yes" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p Type --value 2>/dev/null || true)" == "wayland" ]] || continue
      session_id="${candidate}"
      break
    done <<<"${sessions}"
    [[ -n "${session_id}" ]] && break
    sleep 1
  done
  [[ -n "${session_id}" ]] || return 1

  runtime_dir="/run/user/${ci_uid}"
  for ((i = 0; i < 30; i++)); do
    if [[ -S "${runtime_dir}/bus" ]] && run_user busctl --user --no-pager list >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  [[ -S "${runtime_dir}/bus" ]] || return 1

  wait_until 45 pgrep -u "${ci_uid}" -x kwin_wayland >/dev/null 2>&1 || return 1
  wait_until 45 pgrep -u "${ci_uid}" -x plasmashell >/dev/null 2>&1 || return 1
  kwin_pid="$(first_user_pid kwin_wayland)"
  plasma_pid="$(first_user_pid plasmashell)"
  [[ -n "${kwin_pid}" && -n "${plasma_pid}" ]] || return 1

  wait_until 30 run_user busctl --user --no-pager introspect org.kde.ActivityManager /ActivityManager/Activities >/dev/null 2>&1 || return 1
  wait_until 30 run_user busctl --user --no-pager introspect org.kde.KWin /VirtualDesktopManager >/dev/null 2>&1 || return 1
  return 0
}

activity_persisted_to_disk() {
  local config_file="${ci_home}/.config/kactivitymanagerdrc"
  local state_file="${ci_home}/.local/state/kactivitymanagerdstaterc"
  [[ -f "${config_file}" && -f "${state_file}" ]] || return 1
  grep -Fqx -- "${activity_id}=${ACTIVITY_NAME}" "${config_file}" 2>/dev/null || return 1
  grep -Fqx -- "currentActivity=${activity_id}" "${state_file}" 2>/dev/null || return 1
}

activity_removed_from_disk() {
  local config_file="${ci_home}/.config/kactivitymanagerdrc"
  [[ -f "${config_file}" ]] || return 1
  ! grep -Fq -- "${activity_id}=" "${config_file}" 2>/dev/null
}

virtual_desktop_persisted_to_disk() {
  local config_file="${ci_home}/.config/kwinrc"
  local index
  [[ -f "${config_file}" ]] || return 1
  index="$(sed -nE "s/^Id_([0-9]+)=${desktop_id}$/\\1/p" "${config_file}" | head -n1)"
  [[ -n "${index}" ]] || return 1
  grep -Fqx -- "Name_${index}=${DESKTOP_NAME}" "${config_file}" 2>/dev/null || return 1
  grep -Fqx -- "Number=${mutated_count}" "${config_file}" 2>/dev/null || return 1
}

virtual_desktop_removed_from_disk() {
  local config_file="${ci_home}/.config/kwinrc"
  [[ -f "${config_file}" ]] || return 1
  ! grep -Fq -- "=${desktop_id}" "${config_file}" 2>/dev/null
}

best_effort_restore() {
  set +e
  if [[ -n "${runtime_dir}" && -S "${runtime_dir}/bus" ]]; then
    if [[ -n "${baseline_activity}" ]]; then
      activity_call SetCurrentActivity "${baseline_activity}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${activity_id}" ]] && activity_present "${activity_id}"; then
      activity_call RemoveActivity "${activity_id}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${baseline_desktop}" ]]; then
      run_user busctl --user set-property \
        org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
        current s "${baseline_desktop}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${desktop_id}" ]]; then
      run_user busctl --user call \
        org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
        removeDesktop s "${desktop_id}" >/dev/null 2>&1 || true
    fi
  fi
  cleanup_done=1
}

dump_diagnostics() {
  echo "AURORA_C4_1A_DIAGNOSTICS_START"
  echo "AURORA_C4_1A_PHASE=${phase}"
  echo "AURORA_C4_1A_LAST_STAGE=${current_stage}"
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
    activity_call ListActivities || true
    activity_call CurrentActivity || true
    vdm_property count || true
    vdm_property current || true
    vdm_dump || true
  fi
  echo "--- kactivitymanagerdrc ---"
  cat "${ci_home}/.config/kactivitymanagerdrc" 2>/dev/null || true
  echo "--- kactivitymanagerdstaterc ---"
  cat "${ci_home}/.local/state/kactivitymanagerdstaterc" 2>/dev/null || true
  echo "--- kwinrc desktops ---"
  sed -n '/^\[Desktops\]/,/^\[/p' "${ci_home}/.config/kwinrc" 2>/dev/null || true
  journalctl -b -u sddm.service --no-pager -n 300 || true
  journalctl -b _UID="${ci_uid:-0}" --no-pager -n 400 || true
  cat "/home/${CI_USER}/.local/share/sddm/wayland-session.log" 2>/dev/null || true
  echo "AURORA_C4_1A_DIAGNOSTICS_END"
}

fail() {
  local message="$*"
  trap - ERR
  set +e
  echo "AURORA_C4_1A_FAILURE: ${current_stage}: ${message}"
  dump_diagnostics
  [[ "${cleanup_done}" -eq 1 ]] || best_effort_restore
  sync
  systemctl poweroff --no-block || true
  exit 1
}

unexpected_error() {
  local status=$?
  local line="${BASH_LINENO[0]:-unknown}"
  trap - ERR
  set +e
  echo "AURORA_C4_1A_FAILURE: ${current_stage}: unexpected shell error status ${status} at line ${line}"
  dump_diagnostics
  [[ "${cleanup_done}" -eq 1 ]] || best_effort_restore
  sync
  systemctl poweroff --no-block || true
  exit "${status}"
}
trap unexpected_error ERR

if [[ "${phase}" -eq 1 ]]; then
  echo "AURORA_C4_1A_START"
  stage SESSION
else
  echo "AURORA_C4_1A_RESUME"
  stage SESSION_RELOAD
fi

[[ "$(cat /proc/1/comm)" == "systemd" ]] || fail "PID 1 is not systemd"
systemctl is-active --quiet graphical.target || fail "graphical.target is not active"
command -v qdbus6 >/dev/null 2>&1 || fail "qdbus6 is unavailable"
command -v busctl >/dev/null 2>&1 || fail "busctl is unavailable"
command -v runuser >/dev/null 2>&1 || fail "runuser is unavailable"
ci_uid="$(id -u "${CI_USER}" 2>/dev/null || true)"
ci_home="$(getent passwd "${CI_USER}" | awk -F: '{print $6}')"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable user is missing"
bind_live_session || fail "Plasma Wayland session did not become ready"

if [[ "${phase}" -eq 1 ]]; then
  stage BASELINE
  activity_call ListActivities | sort >"${OUT}/activities-baseline.txt"
  baseline_activity="$(activity_call CurrentActivity)"
  [[ -n "${baseline_activity}" ]] || fail "ActivityManager returned no current activity"
  activity_present "${baseline_activity}" || fail "current activity is not present in ActivityManager list"
  vdm_dump >"${OUT}/virtual-desktops-baseline.txt"
  vdm_property count >"${OUT}/virtual-desktop-count-baseline.txt"
  vdm_property current >"${OUT}/virtual-desktop-current-baseline.txt"
  baseline_desktop="$(vdm_current)"
  baseline_count="$(vdm_count)"
  [[ -n "${baseline_desktop}" && "${baseline_count}" =~ ^[1-9][0-9]*$ ]] || fail "invalid virtual desktop baseline"
  cp "${ci_home}/.config/kwinrc" "${OUT}/kwinrc-baseline" 2>/dev/null || true
  cp "${ci_home}/.config/kactivitymanagerdrc" "${OUT}/kactivitymanagerdrc-baseline" 2>/dev/null || true
  cp "${ci_home}/.local/state/kactivitymanagerdstaterc" "${OUT}/kactivitymanagerdstaterc-baseline" 2>/dev/null || true

  stage ACTIVITIES
  activity_id="$(activity_call AddActivity "${ACTIVITY_NAME}")"
  [[ -n "${activity_id}" && "${activity_id}" != "${baseline_activity}" ]] || fail "AddActivity did not return a new activity ID"
  wait_until 20 activity_present "${activity_id}" || fail "created activity never appeared in ActivityManager"
  [[ "$(activity_call ActivityName "${activity_id}")" == "${ACTIVITY_NAME}" ]] || fail "created activity name does not match"
  [[ "$(activity_call SetCurrentActivity "${activity_id}")" == "true" ]] || fail "could not switch to created activity"
  wait_until 20 activity_current_is "${activity_id}" || fail "created activity never became current"
  set +e
  invalid_activity_result="$(activity_call SetCurrentActivity "${INVALID_ID}" 2>&1)"
  invalid_activity_status=$?
  set -e
  printf 'status=%s\n%s\n' "${invalid_activity_status}" "${invalid_activity_result}" >"${OUT}/activities-invalid-switch.txt"
  activity_current_is "${activity_id}" || fail "invalid activity switch changed current activity"
  activity_call ListActivities | sort >"${OUT}/activities-mutated.txt"

  stage VIRTUAL_DESKTOPS
  mutated_count=$((baseline_count + 1))
  run_user busctl --user call \
    org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
    createDesktop us "${baseline_count}" "${DESKTOP_NAME}" >"${OUT}/virtual-desktop-create.txt"
  wait_until 20 vdm_count_is "${mutated_count}" || fail "virtual desktop count did not increase"
  desktop_id="$(vdm_desktop_id_by_name "${DESKTOP_NAME}")"
  [[ -n "${desktop_id}" ]] || fail "created virtual desktop ID could not be resolved"
  run_user busctl --user set-property \
    org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
    current s "${desktop_id}"
  wait_until 20 vdm_current_is "${desktop_id}" || fail "created virtual desktop never became current"
  set +e
  invalid_desktop_output="$(run_user busctl --user set-property \
    org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
    current s "${INVALID_ID}" 2>&1)"
  invalid_desktop_status=$?
  set -e
  printf 'status=%s\n%s\n' "${invalid_desktop_status}" "${invalid_desktop_output}" >"${OUT}/virtual-desktop-invalid-switch.txt"
  vdm_current_is "${desktop_id}" || fail "invalid virtual desktop switch changed current desktop"
  vdm_dump >"${OUT}/virtual-desktops-mutated.txt"
  vdm_property count >"${OUT}/virtual-desktop-count-mutated.txt"
  vdm_property current >"${OUT}/virtual-desktop-current-mutated.txt"

  stage PERSISTENCE_WRITE
  # Plasma 6.6 kactivitymanagerd intentionally batches KConfig sync through a
  # one-shot timer. Do not race logout/poweroff: require the exact state to be
  # observable on persistent storage before ending boot 1.
  wait_until 15 activity_persisted_to_disk || fail "activity state did not reach persistent KConfig storage"
  wait_until 15 virtual_desktop_persisted_to_disk || fail "virtual desktop state did not reach persistent KWin config"
  cp "${ci_home}/.config/kactivitymanagerdrc" "${OUT}/kactivitymanagerdrc-mutated"
  cp "${ci_home}/.local/state/kactivitymanagerdstaterc" "${OUT}/kactivitymanagerdstaterc-mutated"
  cp "${ci_home}/.config/kwinrc" "${OUT}/kwinrc-mutated"

  {
    printf 'activity_id=%q\n' "${activity_id}"
    printf 'desktop_id=%q\n' "${desktop_id}"
    printf 'baseline_activity=%q\n' "${baseline_activity}"
    printf 'baseline_desktop=%q\n' "${baseline_desktop}"
    printf 'baseline_count=%q\n' "${baseline_count}"
    printf 'mutated_count=%q\n' "${mutated_count}"
  } >"${STATE_FILE}"
  printf '2\n' >"${PHASE_FILE}"
  sync
  stage PHASE1_COMPLETE
  echo "AURORA_C4_1A_PHASE1_SUCCESS"
  systemctl poweroff --no-block
  exit 0
fi

[[ -r "${STATE_FILE}" ]] || fail "phase state is missing on boot 2"
# shellcheck disable=SC1090
source "${STATE_FILE}"
[[ -n "${activity_id}" && -n "${desktop_id}" && -n "${baseline_activity}" && -n "${baseline_desktop}" ]] || fail "phase state is incomplete"
[[ "${baseline_count}" =~ ^[1-9][0-9]*$ && "${mutated_count}" =~ ^[1-9][0-9]*$ ]] || fail "phase state desktop counts are invalid"
[[ "$((baseline_count + 1))" -eq "${mutated_count}" ]] || fail "phase state desktop count relation is invalid"

stage PERSISTENCE_READ
activity_present "${activity_id}" || fail "created activity did not persist across complete reboot"
[[ "$(activity_call ActivityName "${activity_id}")" == "${ACTIVITY_NAME}" ]] || fail "persisted activity name changed across reboot"
activity_current_is "${activity_id}" || fail "current activity did not persist across complete reboot"
[[ "$(vdm_count)" == "${mutated_count}" ]] || fail "virtual desktop count did not persist across complete reboot"
[[ "$(vdm_desktop_id_by_name "${DESKTOP_NAME}")" == "${desktop_id}" ]] || fail "created virtual desktop identity did not persist across complete reboot"
activity_persisted_to_disk || fail "activity persistent files do not match runtime state after reboot"
virtual_desktop_persisted_to_disk || fail "virtual desktop persistent file does not match runtime state after reboot"
activity_call ListActivities | sort >"${OUT}/activities-after-reboot.txt"
vdm_dump >"${OUT}/virtual-desktops-after-reboot.txt"
vdm_property count >"${OUT}/virtual-desktop-count-after-reboot.txt"
vdm_property current >"${OUT}/virtual-desktop-current-after-reboot.txt"
cp "${ci_home}/.config/kactivitymanagerdrc" "${OUT}/kactivitymanagerdrc-after-reboot"
cp "${ci_home}/.local/state/kactivitymanagerdstaterc" "${OUT}/kactivitymanagerdstaterc-after-reboot"
cp "${ci_home}/.config/kwinrc" "${OUT}/kwinrc-after-reboot"

# Re-exercise both APIs after reboot so PASS proves the newly started services
# consume the persisted objects, rather than merely finding stale files.
[[ "$(activity_call SetCurrentActivity "${baseline_activity}")" == "true" ]] || fail "could not leave persisted test activity after reboot"
wait_until 20 activity_current_is "${baseline_activity}" || fail "baseline activity did not become current after reboot"
[[ "$(activity_call SetCurrentActivity "${activity_id}")" == "true" ]] || fail "persisted activity could not be selected after reboot"
wait_until 20 activity_current_is "${activity_id}" || fail "persisted activity did not become current after reboot"
run_user busctl --user set-property \
  org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
  current s "${desktop_id}"
wait_until 20 vdm_current_is "${desktop_id}" || fail "persisted virtual desktop could not be selected after reboot"

stage CLEANUP
[[ "$(activity_call SetCurrentActivity "${baseline_activity}")" == "true" ]] || fail "could not restore baseline current activity"
wait_until 20 activity_current_is "${baseline_activity}" || fail "baseline activity did not become current during cleanup"
activity_call RemoveActivity "${activity_id}"
removed=0
for ((i = 0; i < 20; i++)); do
  if ! activity_present "${activity_id}"; then
    removed=1
    break
  fi
  sleep 1
done
[[ "${removed}" -eq 1 ]] || fail "created activity could not be removed"
wait_until 15 activity_removed_from_disk || fail "removed activity remained in persistent KConfig"

run_user busctl --user set-property \
  org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
  current s "${baseline_desktop}"
wait_until 20 vdm_current_is "${baseline_desktop}" || fail "could not restore baseline current desktop"
run_user busctl --user call \
  org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager \
  removeDesktop s "${desktop_id}" >"${OUT}/virtual-desktop-remove.txt"
wait_until 20 vdm_count_is "${baseline_count}" || fail "virtual desktop count did not return to baseline"
[[ -z "$(vdm_desktop_id_by_name "${DESKTOP_NAME}")" ]] || fail "test virtual desktop remains after cleanup"
wait_until 15 virtual_desktop_removed_from_disk || fail "removed virtual desktop remained in persistent KWin config"

activity_call ListActivities | sort >"${OUT}/activities-final.txt"
vdm_dump >"${OUT}/virtual-desktops-final.txt"
vdm_property count >"${OUT}/virtual-desktop-count-final.txt"
vdm_property current >"${OUT}/virtual-desktop-current-final.txt"
cp "${ci_home}/.config/kactivitymanagerdrc" "${OUT}/kactivitymanagerdrc-final"
cp "${ci_home}/.local/state/kactivitymanagerdstaterc" "${OUT}/kactivitymanagerdstaterc-final"
cp "${ci_home}/.config/kwinrc" "${OUT}/kwinrc-final"
cmp -s "${OUT}/activities-baseline.txt" "${OUT}/activities-final.txt" || fail "activity list was not restored exactly"
cmp -s "${OUT}/virtual-desktops-baseline.txt" "${OUT}/virtual-desktops-final.txt" || fail "virtual desktop topology was not restored exactly"
activity_current_is "${baseline_activity}" || fail "current activity was not restored"
vdm_current_is "${baseline_desktop}" || fail "current virtual desktop was not restored"
cleanup_done=1

stage STABILITY
sleep 5
kill -0 "${kwin_pid}" >/dev/null 2>&1 || fail "KWin exited after functional tests"
kill -0 "${plasma_pid}" >/dev/null 2>&1 || fail "plasmashell exited after functional tests"
[[ "$(first_user_pid kwin_wayland)" == "${kwin_pid}" ]] || fail "KWin restarted unexpectedly during boot 2"
[[ "$(first_user_pid plasmashell)" == "${plasma_pid}" ]] || fail "plasmashell restarted unexpectedly during boot 2"
systemctl --failed --no-pager --plain >"${OUT}/system-failed-units.txt" 2>&1 || true
run_user systemctl --user --failed --no-pager --plain >"${OUT}/user-failed-units.txt" 2>&1 || true
system_failed_count="$(systemctl --failed --no-legend 2>/dev/null | sed '/^[[:space:]]*$/d' | wc -l)"
user_failed_count="$(run_user systemctl --user --failed --no-legend 2>/dev/null | sed '/^[[:space:]]*$/d' | wc -l)"
[[ "${system_failed_count}" -eq 0 ]] || fail "system failed units remain after C4.1a"
[[ "${user_failed_count}" -eq 0 ]] || fail "user failed units remain after C4.1a"
journalctl -b -u sddm.service --no-pager >"${OUT}/sddm-journal-boot2.txt" 2>&1 || true
journalctl -b _UID="${ci_uid}" --no-pager >"${OUT}/user-journal-boot2.txt" 2>&1 || true
run_user busctl --user --no-pager introspect org.kde.ActivityManager /ActivityManager/Activities >"${OUT}/activitymanager-final-introspection.txt" 2>&1
run_user busctl --user --no-pager introspect org.kde.KWin /VirtualDesktopManager >"${OUT}/kwin-vdm-final-introspection.txt" 2>&1

dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' \
  plasma-desktop plasma-workspace kwin-wayland kactivitymanagerd qdbus-qt6 \
  >"${OUT}/package-versions.tsv" 2>&1 || true

capability_pass AUR-KCM-002
capability_pass AUR-KWIN-004
stage COMPLETE
echo "AURORA_C4_1A_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1a-check"

cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1a-check.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C4.1a Activities and virtual desktop functional certification
After=graphical.target sddm.service systemd-logind.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c4-1a-check
TimeoutStartSec=480
SERVICE

cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1a-check.timer" <<'TIMER'
[Unit]
Description=Run SupraLINUX Aurora C4.1a functional certification

[Timer]
OnBootSec=20s
AccuracySec=1s
Unit=aurora-ci-c4-1a-check.service

[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c4-1a-check.timer "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1a-check.timer"

sync
umount "${MOUNT_DIR}"

echo "==> Booting Aurora C4.1a functional certification VM"
qemu_accel=(-accel tcg -cpu max)
if [[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
  qemu_accel=(-enable-kvm -cpu host)
fi

count_serial_marker() {
  local marker="$1"
  awk -v marker="${marker}" '{ sub(/\r$/, ""); if ($0 == marker) count++ } END { print count + 0 }' "${SERIAL_LOG}"
}

: >"${SERIAL_LOG}"
host_failure=""
completed_phases=0
for boot_phase in 1 2; do
  echo "==> C4.1a guest boot phase ${boot_phase}"
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
      2>&1 | tee -a "${SERIAL_LOG}"
  qemu_status=${PIPESTATUS[0]}
  set -e

  if [[ ${qemu_status} -eq 124 ]]; then
    host_failure="guest boot phase ${boot_phase} timed out after ${BOOT_TIMEOUT} seconds"
    break
  fi
  if [[ ${qemu_status} -ne 0 ]]; then
    host_failure="guest boot phase ${boot_phase} QEMU exited with status ${qemu_status}"
    break
  fi
  if grep -Fq 'AURORA_C4_1A_FAILURE:' "${SERIAL_LOG}"; then
    host_failure="guest reported a C4.1a failure during boot phase ${boot_phase}"
    break
  fi

  completed_phases=${boot_phase}
  if [[ ${boot_phase} -eq 1 ]]; then
    phase1_count="$(count_serial_marker 'AURORA_C4_1A_PHASE1_SUCCESS')"
    if [[ "${phase1_count}" -ne 1 ]]; then
      host_failure="expected exactly one C4.1a phase-1 success marker, observed ${phase1_count}"
      break
    fi
  fi
done

mount -o loop,ro "${IMAGE}" "${MOUNT_DIR}"
if [[ -d "${MOUNT_DIR}/var/lib/aurora-ci-c4-1a" ]]; then
  cp -a "${MOUNT_DIR}/var/lib/aurora-ci-c4-1a/." "${OUT_DIR}/"
fi
if [[ -f "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" ]]; then
  cp "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" "${SESSION_LOG}"
else
  : >"${SESSION_LOG}"
fi
umount "${MOUNT_DIR}"

chmod 0644 "${SERIAL_LOG}" "${SESSION_LOG}" 2>/dev/null || true
find "${OUT_DIR}" -type f -exec chmod 0644 {} + 2>/dev/null || true

if [[ -n "${host_failure}" ]]; then
  echo "Aurora C4.1a host failure: ${host_failure}." >&2
  exit 1
fi
[[ "${completed_phases}" -eq 2 ]] || {
  echo "Expected both C4.1a boot phases, completed ${completed_phases}." >&2
  exit 1
}

success_count="$(count_serial_marker 'AURORA_C4_1A_SUCCESS')"
[[ "${success_count}" -eq 1 ]] || {
  echo "Expected exactly one C4.1a success marker, observed ${success_count}." >&2
  exit 1
}
if grep -Fq 'AURORA_C4_1A_FAILURE:' "${SERIAL_LOG}"; then
  echo "Aurora C4.1a guest reported failure." >&2
  exit 1
fi

for required_stage in \
  SESSION BASELINE ACTIVITIES VIRTUAL_DESKTOPS PERSISTENCE_WRITE PHASE1_COMPLETE \
  SESSION_RELOAD PERSISTENCE_READ CLEANUP STABILITY COMPLETE; do
  stage_count="$(count_serial_marker "AURORA_C4_1A_STAGE=${required_stage}")"
  [[ "${stage_count}" -eq 1 ]] || {
    echo "Expected exactly one C4.1a ${required_stage} stage marker, observed ${stage_count}." >&2
    exit 1
  }
done

for capability in AUR-KCM-002 AUR-KWIN-004; do
  pass_count="$(count_serial_marker "AURORA_C4_1A_CAPABILITY_PASS=${capability}")"
  [[ "${pass_count}" -eq 1 ]] || {
    echo "Expected exactly one C4.1a pass marker for ${capability}, observed ${pass_count}." >&2
    exit 1
  }
done

for evidence in \
  activities-baseline.txt activities-mutated.txt activities-after-reboot.txt activities-final.txt \
  virtual-desktops-baseline.txt virtual-desktops-mutated.txt virtual-desktops-after-reboot.txt virtual-desktops-final.txt \
  activities-invalid-switch.txt virtual-desktop-invalid-switch.txt \
  kactivitymanagerdrc-mutated kactivitymanagerdstaterc-mutated kwinrc-mutated \
  kactivitymanagerdrc-after-reboot kactivitymanagerdstaterc-after-reboot kwinrc-after-reboot \
  kactivitymanagerdrc-final kactivitymanagerdstaterc-final kwinrc-final \
  system-failed-units.txt user-failed-units.txt package-versions.tsv; do
  [[ -f "${OUT_DIR}/${evidence}" ]] || {
    echo "Missing required C4.1a evidence: ${evidence}" >&2
    exit 1
  }
done

echo "Aurora C4.1a Activities and virtual desktop functional certification passed."
