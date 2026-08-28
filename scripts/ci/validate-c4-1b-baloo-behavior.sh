#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-c4-1b-baloo-behavior.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
KERNEL="${BUILD_DIR}/aurora-c4-0-vmlinuz"
INITRD="${BUILD_DIR}/aurora-c4-0-initrd.img"
C4_0_KCM_INVENTORY="${BUILD_DIR}/c4-0-inventory/actual-kcms.txt"
C4_0_KCM_OWNERS="${BUILD_DIR}/c4-0-inventory/kcm-package-owners.tsv"
C4_0_KCM_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-kcm-coverage.tsv"
MOUNT_DIR="${BUILD_DIR}/aurora-c4-1b-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c4-1b-serial.log"
SESSION_LOG="${BUILD_DIR}/aurora-c4-1b-wayland-session.log"
OUT_DIR="${BUILD_DIR}/c4-1b-evidence"
BOOT_TIMEOUT="${AURORA_C4_1B_BOOT_TIMEOUT:-900}"
CI_USER="auroraci"

for file in "${IMAGE}" "${KERNEL}" "${INITRD}" "${C4_0_KCM_INVENTORY}" "${C4_0_KCM_OWNERS}" "${C4_0_KCM_MANIFEST}"; do
  [[ -f "${file}" ]] || { echo "Missing C4.1b prerequisite file: ${file}" >&2; exit 1; }
done
for tool in mount umount mountpoint qemu-system-x86_64 timeout; do
  command -v "${tool}" >/dev/null 2>&1 || { echo "Missing required tool: ${tool}" >&2; exit 1; }
done

mkdir -p "${BUILD_DIR}" "${MOUNT_DIR}"
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
rm -f "${SERIAL_LOG}" "${SESSION_LOG}"

grep -Fxq 'kcm_baloofile' "${C4_0_KCM_INVENTORY}" || { echo "Accepted C4.0 runtime inventory does not expose kcm_baloofile." >&2; exit 1; }
owner_row="$(awk -F '\t' '$1 == "KCM" && $2 == "kcm_baloofile" && $3 == "plasma-desktop" && $5 ~ /kcm_baloofile\.so$/ { print; exit }' "${C4_0_KCM_OWNERS}")"
[[ -n "${owner_row}" ]] || { echo "Accepted C4.0 ownership inventory does not map kcm_baloofile.so to plasma-desktop." >&2; exit 1; }
mapping_row="$(awk -F '\t' '$1 == "kcm_baloofile" && $2 == "AUR-KCM-003" && $3 == "C4.1" { print; exit }' "${C4_0_KCM_MANIFEST}")"
[[ -n "${mapping_row}" ]] || { echo "Versioned C4.0 KCM manifest does not map kcm_baloofile to AUR-KCM-003." >&2; exit 1; }
{
  echo 'surface_id=kcm_baloofile'
  printf 'owner=%s\n' "${owner_row}"
  printf 'mapping=%s\n' "${mapping_row}"
} >"${OUT_DIR}/c4-0-baloofile-surface.txt"

cleanup() {
  set +e
  if mountpoint -q "${MOUNT_DIR}"; then
    umount "${MOUNT_DIR}" >/dev/null 2>&1 || umount -l "${MOUNT_DIR}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

mount -o loop,rw "${IMAGE}" "${MOUNT_DIR}"

# Keep the accepted C4.0 image composition, but ensure only this gate owns the
# serial acceptance channel during its two boots.
for name in \
  aurora-ci-c4-0-check \
  aurora-ci-c4-1-discovery \
  aurora-ci-c4-1a-check \
  aurora-ci-c4-1b-preflight \
  aurora-ci-c4-1b-check; do
  rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/${name}.timer"
  rm -f "${MOUNT_DIR}/etc/systemd/system/${name}.service"
  rm -f "${MOUNT_DIR}/etc/systemd/system/${name}.timer"
  rm -f "${MOUNT_DIR}/usr/local/libexec/${name}"
done
rm -rf "${MOUNT_DIR}/var/lib/aurora-ci-c4-1-discovery" \
       "${MOUNT_DIR}/var/lib/aurora-ci-c4-1a" \
       "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b-preflight" \
       "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b"

mkdir -p "${MOUNT_DIR}/usr/local/libexec" "${MOUNT_DIR}/etc/systemd/system/timers.target.wants" "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b"
cp "${OUT_DIR}/c4-0-baloofile-surface.txt" "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b/c4-0-baloofile-surface.txt"

cat >"${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1b-check" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"
OUT="/var/lib/aurora-ci-c4-1b"
PHASE_FILE="${OUT}/phase"
STATE_FILE="${OUT}/phase-state"
BACKUP_DIR="${OUT}/config-backup"
current_stage="INIT"
phase=1
ci_uid=""
ci_home=""
runtime_dir=""
session_id=""
kwin_pid=""
plasma_pid=""
session_path=""
baloo_exe=""
root=""
exclude_dir=""
name_file=""
content_file=""
exclude_file=""
name_token=""
content_token=""
exclude_token=""
cleanup_done=0

mkdir -p "${OUT}"
if [[ -f "${PHASE_FILE}" && "$(cat "${PHASE_FILE}" 2>/dev/null || true)" == "2" ]]; then phase=2; fi

stage() { current_stage="$1"; echo "AURORA_C4_1B_STAGE=${current_stage}"; }
capability_pass() { echo "AURORA_C4_1B_CAPABILITY_PASS=$1"; }

run_user() {
  runuser -u "${CI_USER}" -- env \
    HOME="${ci_home}" USER="${CI_USER}" LOGNAME="${CI_USER}" \
    XDG_RUNTIME_DIR="${runtime_dir}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime_dir}/bus" \
    "$@"
}

first_user_pid() { pgrep -o -u "${ci_uid}" -x "$1" 2>/dev/null || true; }
wait_until() {
  local timeout_seconds="$1"; shift
  local i
  for ((i=0; i<timeout_seconds; i++)); do
    if "$@"; then return 0; fi
    sleep 1
  done
  return 1
}

bind_live_session() {
  local i sessions candidate
  session_id=""
  for ((i=0; i<120; i++)); do
    sessions="$(loginctl list-sessions --no-legend 2>/dev/null || true)"
    while read -r candidate _; do
      [[ -n "${candidate}" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p User --value 2>/dev/null || true)" == "${ci_uid}" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p Class --value 2>/dev/null || true)" == "user" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p Active --value 2>/dev/null || true)" == "yes" ]] || continue
      [[ "$(loginctl show-session "${candidate}" -p Type --value 2>/dev/null || true)" == "wayland" ]] || continue
      session_id="${candidate}"; break
    done <<<"${sessions}"
    [[ -n "${session_id}" ]] && break
    sleep 1
  done
  [[ -n "${session_id}" ]] || return 1
  runtime_dir="/run/user/${ci_uid}"
  wait_until 30 test -S "${runtime_dir}/bus" || return 1
  wait_until 30 run_user busctl --user --no-pager list >/dev/null 2>&1 || return 1
  wait_until 45 pgrep -u "${ci_uid}" -x kwin_wayland >/dev/null 2>&1 || return 1
  wait_until 45 pgrep -u "${ci_uid}" -x plasmashell >/dev/null 2>&1 || return 1
  kwin_pid="$(first_user_pid kwin_wayland)"
  plasma_pid="$(first_user_pid plasmashell)"
  [[ -n "${kwin_pid}" && -n "${plasma_pid}" ]] || return 1
  session_path="$(tr '\0' '\n' <"/proc/${plasma_pid}/environ" | sed -n 's/^PATH=//p' | head -n1)"
  [[ -n "${session_path}" ]] || return 1
  baloo_exe="$(run_user env PATH="${session_path}" sh -c 'command -v baloo_file' 2>/dev/null || true)"
  [[ -n "${baloo_exe}" && -x "${baloo_exe}" ]] || return 1
}

baloo_bus_present() {
  run_user busctl --user --no-pager list 2>/dev/null | awk '{print $1}' | grep -Fxq org.kde.baloo
}
baloo_process_present() { pgrep -u "${ci_uid}" -x baloo_file >/dev/null 2>&1; }
baloo_process_absent() { ! baloo_process_present; }
baloo_bus_absent() { ! baloo_bus_present; }

targeted_crashes() {
  journalctl -b --no-pager 2>/dev/null | \
    grep -Ei '(baloo_file|kwin_wayland|plasmashell).*(segfault|dumped core|core dumped|signal (6|11)|aborted|crashed)|(segfault|dumped core|core dumped|signal (6|11)|aborted|crashed).*(baloo_file|kwin_wayland|plasmashell)' || true
}
assert_no_targeted_crashes() {
  local evidence_file="$1"
  targeted_crashes >"${evidence_file}"
  [[ ! -s "${evidence_file}" ]]
}

apply_refresh() {
  run_user busctl --user call org.kde.baloo / org.kde.baloo.main updateConfig >/dev/null
}
apply_refresh_best_effort() {
  set +e
  run_user busctl --user call org.kde.baloo / org.kde.baloo.main updateConfig >/dev/null 2>&1
  local status=$?
  set -e
  return "${status}"
}
launch_baloo_like_kcm() {
  run_user env PATH="${session_path}" setsid -f "${baloo_exe}" >/dev/null 2>&1
}

status_is() {
  local file="$1" wanted_status="$2" wanted_indexing="$3" output
  output="$(run_user balooctl6 status --format json "${file}" 2>/dev/null || true)"
  grep -Fq '"status": "'"${wanted_status}"'"' <<<"${output}" && \
    grep -Fq '"indexing": "'"${wanted_indexing}"'"' <<<"${output}" && \
    grep -Fq '"file": "'"${file}"'"' <<<"${output}"
}
search_has_exact_path() {
  local token="$1" file="$2"
  run_user baloosearch6 "${token}" 2>/dev/null | tr -d '\r' | grep -Fxq -- "${file}"
}
search_lacks_exact_path() {
  local token="$1" file="$2"
  ! run_user baloosearch6 "${token}" 2>/dev/null | tr -d '\r' | grep -Fxq -- "${file}"
}

backup_configs() {
  rm -rf "${BACKUP_DIR}"
  mkdir -p "${BACKUP_DIR}"
  for cfg in baloofilerc krunnerrc; do
    if [[ -e "${ci_home}/.config/${cfg}" ]]; then
      printf 'present\n' >"${BACKUP_DIR}/${cfg}.state"
      cp -a "${ci_home}/.config/${cfg}" "${BACKUP_DIR}/${cfg}"
    else
      printf 'absent\n' >"${BACKUP_DIR}/${cfg}.state"
    fi
  done
}
restore_configs() {
  local cfg state
  mkdir -p "${ci_home}/.config"
  for cfg in baloofilerc krunnerrc; do
    state="$(cat "${BACKUP_DIR}/${cfg}.state" 2>/dev/null || true)"
    if [[ "${state}" == "present" ]]; then
      cp -a "${BACKUP_DIR}/${cfg}" "${ci_home}/.config/${cfg}"
      chown "${ci_uid}:${ci_uid}" "${ci_home}/.config/${cfg}"
    elif [[ "${state}" == "absent" ]]; then
      rm -f "${ci_home}/.config/${cfg}"
    fi
  done
}
configs_restored_exactly() {
  local cfg state
  for cfg in baloofilerc krunnerrc; do
    state="$(cat "${BACKUP_DIR}/${cfg}.state")"
    if [[ "${state}" == "present" ]]; then
      cmp -s "${BACKUP_DIR}/${cfg}" "${ci_home}/.config/${cfg}" || return 1
    else
      [[ ! -e "${ci_home}/.config/${cfg}" ]] || return 1
    fi
  done
}

record_snapshot() {
  local name="$1"
  {
    echo "phase=${phase}"
    echo "stage=${current_stage}"
    echo "session_path=${session_path}"
    echo "baloo_exe=${baloo_exe}"
    echo "== packages =="
    dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' plasma-desktop plasma-workspace kwin-wayland baloo6 libkf6baloo6 libkf6filemetadata3 2>&1 || true
    echo "== baloo service =="
    run_user systemctl --user status kde-baloo.service --no-pager --full 2>&1 || true
    run_user systemctl --user cat kde-baloo.service 2>&1 || true
    echo "== baloo process =="
    pgrep -a -u "${ci_uid}" -f baloo || true
    echo "== dbus =="
    run_user busctl --user --no-pager list 2>&1 | grep -E 'org\.kde\.baloo' || true
    echo "== config =="
    cat "${ci_home}/.config/baloofilerc" 2>/dev/null || true
    echo "== runner =="
    run_user kreadconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --default true 2>&1 || true
    echo "== folders =="
    run_user balooctl6 config show includeFolders 2>&1 || true
    run_user balooctl6 config show excludeFolders 2>&1 || true
    if [[ -n "${name_file}" && -e "${name_file}" ]]; then run_user balooctl6 status --format json "${name_file}" 2>&1 || true; fi
    if [[ -n "${content_file}" && -e "${content_file}" ]]; then run_user balooctl6 status --format json "${content_file}" 2>&1 || true; fi
    if [[ -n "${exclude_file}" && -e "${exclude_file}" ]]; then run_user balooctl6 status --format json "${exclude_file}" 2>&1 || true; fi
  } >"${OUT}/${name}.txt"
}

dump_diagnostics() {
  echo "AURORA_C4_1B_DIAGNOSTICS_START"
  record_snapshot failure || true
  systemctl --failed --no-pager --plain || true
  run_user systemctl --user --failed --no-pager --plain || true
  journalctl -b -u sddm.service --no-pager -n 250 || true
  journalctl -b _UID="${ci_uid:-0}" --no-pager -n 500 || true
  cat "/home/${CI_USER}/.local/share/sddm/wayland-session.log" 2>/dev/null || true
  echo "AURORA_C4_1B_DIAGNOSTICS_END"
}

best_effort_restore() {
  set +e
  if [[ -n "${ci_home}" && -d "${BACKUP_DIR}" ]]; then
    if [[ -n "${exclude_file}" && -e "${exclude_file}" ]]; then run_user balooctl6 clear "${exclude_file}" >/dev/null 2>&1 || true; fi
    if [[ -n "${content_file}" && -e "${content_file}" ]]; then run_user balooctl6 clear "${content_file}" >/dev/null 2>&1 || true; fi
    if [[ -n "${name_file}" && -e "${name_file}" ]]; then run_user balooctl6 clear "${name_file}" >/dev/null 2>&1 || true; fi
    [[ -n "${root}" ]] && rm -rf "${root}" || true
    restore_configs || true
    if [[ -S "${runtime_dir}/bus" ]] && baloo_bus_present; then apply_refresh_best_effort || true; fi
  fi
  cleanup_done=1
}

fail() {
  local message="$*"
  trap - ERR
  set +e
  echo "AURORA_C4_1B_FAILURE: ${current_stage}: ${message}"
  dump_diagnostics
  [[ "${cleanup_done}" -eq 1 ]] || best_effort_restore
  sync
  systemctl poweroff --no-block || true
  exit 1
}
unexpected_error() {
  local status=$? line="${BASH_LINENO[0]:-unknown}"
  trap - ERR
  set +e
  echo "AURORA_C4_1B_FAILURE: ${current_stage}: unexpected shell error status ${status} at line ${line}"
  dump_diagnostics
  [[ "${cleanup_done}" -eq 1 ]] || best_effort_restore
  sync
  systemctl poweroff --no-block || true
  exit "${status}"
}
trap unexpected_error ERR

if [[ "${phase}" -eq 1 ]]; then echo "AURORA_C4_1B_START"; else echo "AURORA_C4_1B_RESUME"; fi
stage SESSION
[[ "$(cat /proc/1/comm)" == "systemd" ]] || fail "PID 1 is not systemd"
systemctl is-active --quiet graphical.target || fail "graphical.target is not active"
for cmd in balooctl6 baloosearch6 kreadconfig6 kwriteconfig6 busctl runuser setsid; do command -v "${cmd}" >/dev/null 2>&1 || fail "required command ${cmd} is unavailable"; done
ci_uid="$(id -u "${CI_USER}" 2>/dev/null || true)"
ci_home="$(getent passwd "${CI_USER}" | awk -F: '{print $6}')"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable user is missing"
bind_live_session || fail "Plasma Wayland session or baloo_file in its real PATH did not become ready"
printf 'PATH=%s\nbaloo_file=%s\n' "${session_path}" "${baloo_exe}" >"${OUT}/session-executable-resolution.txt"

grep -Fxq 'surface_id=kcm_baloofile' "${OUT}/c4-0-baloofile-surface.txt" || fail "accepted C4.0 inventory no longer proves File Search surface"
grep -Fq $'mapping=kcm_baloofile\tAUR-KCM-003\tC4.1' "${OUT}/c4-0-baloofile-surface.txt" || fail "C4.0 manifest no longer maps File Search to AUR-KCM-003"

if [[ "${phase}" -eq 1 ]]; then
  stage BASELINE
  backup_configs
  original_indexing="$(run_user kreadconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --default true)"
  original_runner="$(run_user kreadconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --default true)"
  printf 'Indexing-Enabled=%s\nbaloosearchEnabled=%s\n' "${original_indexing}" "${original_runner}" >"${OUT}/baseline-settings.txt"
  record_snapshot baseline

  suffix="$(printf '%08x' $(( $(date +%s) ^ $$ )))"
  root="${ci_home}/Aurora-C4.1B-${suffix}"
  exclude_dir="${root}/excluded"
  name_token="aurorac41bname${suffix}"
  content_token="aurorac41bcontent${suffix}"
  exclude_token="aurorac41bexclude${suffix}"
  name_file="${root}/${name_token}-fixture.txt"
  content_file="${root}/content-fixture.txt"
  exclude_file="${exclude_dir}/excluded-fixture.txt"
  install -d -o "${ci_uid}" -g "${ci_uid}" "${exclude_dir}"

  stage ENABLE
  run_user kwriteconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --type bool true
  run_user kwriteconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --type bool true
  run_user balooctl6 config set contentIndexing true
  # Match Plasma 6.6.6 KCM save(): refresh the running daemon (if any), then
  # start baloo_file by the executable name resolved from the Plasma session.
  apply_refresh_best_effort || true
  launch_baloo_like_kcm
  wait_until 45 baloo_bus_present || fail "org.kde.baloo did not register after KCM-equivalent enable"
  wait_until 45 baloo_process_present || fail "baloo_file did not remain available after KCM-equivalent enable"
  apply_refresh
  [[ "$(run_user kreadconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --default false)" == "true" ]] || fail "Indexing-Enabled did not persist true"
  [[ "$(run_user kreadconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --default false)" == "true" ]] || fail "KRunner baloosearch plugin did not follow enabled state"

  stage INCLUDE_ROOT
  run_user balooctl6 config add includeFolders "${root}"
  apply_refresh
  run_user balooctl6 config show includeFolders >"${OUT}/include-folders-mutated.txt"
  grep -Fq "${root}/" "${OUT}/include-folders-mutated.txt" || fail "test root was not added to Baloo includeFolders"

  stage INDEXING
  printf 'filename token is deliberately absent from content\n' >"${name_file}"
  printf '%s\n' "${content_token}" >"${content_file}"
  printf '%s\n' "${exclude_token}" >"${exclude_file}"
  chown -R "${ci_uid}:${ci_uid}" "${root}"
  wait_until 120 status_is "${name_file}" done content || fail "filename fixture never reached done/content through normal scheduler"
  wait_until 120 status_is "${content_file}" done content || fail "content fixture never reached done/content through normal scheduler"
  wait_until 120 status_is "${exclude_file}" done content || fail "future exclusion fixture never reached done/content before exclusion"
  wait_until 60 search_has_exact_path "${name_token}" "${name_file}" || fail "filename search did not return exact fixture path"
  wait_until 60 search_has_exact_path "${content_token}" "${content_file}" || fail "content search did not return exact fixture path"
  wait_until 60 search_has_exact_path "${exclude_token}" "${exclude_file}" || fail "pre-exclusion search did not return exact fixture path"
  run_user balooctl6 status --format json "${name_file}" "${content_file}" "${exclude_file}" >"${OUT}/status-before-exclusion.json"
  run_user baloosearch6 "${name_token}" >"${OUT}/search-name-before-exclusion.txt"
  run_user baloosearch6 "${content_token}" >"${OUT}/search-content-before-exclusion.txt"
  run_user baloosearch6 "${exclude_token}" >"${OUT}/search-exclude-before-exclusion.txt"

  stage EXCLUSION
  run_user balooctl6 config add excludeFolders "${exclude_dir}"
  apply_refresh
  wait_until 30 status_is "${exclude_file}" disabled none || fail "excluded fixture did not become disabled/none in Baloo policy"
  wait_until 120 search_lacks_exact_path "${exclude_token}" "${exclude_file}" || fail "excluded fixture remained searchable after updateConfig"
  search_has_exact_path "${content_token}" "${content_file}" || fail "unrelated indexed content regressed after exclusion"
  run_user balooctl6 status --format json "${exclude_file}" >"${OUT}/status-after-exclusion.json"
  run_user baloosearch6 "${exclude_token}" >"${OUT}/search-exclude-after-exclusion.txt" || true
  run_user balooctl6 config show excludeFolders >"${OUT}/exclude-folders-mutated.txt"
  grep -Fq "${exclude_dir}/" "${OUT}/exclude-folders-mutated.txt" || fail "excluded folder did not persist in configuration"

  assert_no_targeted_crashes "${OUT}/targeted-crashes-boot1.txt" || fail "targeted Baloo/Plasma crash evidence appeared during boot 1"

  stage PERSISTENCE_WRITE
  {
    printf 'root=%q\n' "${root}"
    printf 'exclude_dir=%q\n' "${exclude_dir}"
    printf 'name_file=%q\n' "${name_file}"
    printf 'content_file=%q\n' "${content_file}"
    printf 'exclude_file=%q\n' "${exclude_file}"
    printf 'name_token=%q\n' "${name_token}"
    printf 'content_token=%q\n' "${content_token}"
    printf 'exclude_token=%q\n' "${exclude_token}"
    printf 'original_indexing=%q\n' "${original_indexing}"
    printf 'original_runner=%q\n' "${original_runner}"
  } >"${STATE_FILE}"
  sync
  grep -Fq "${exclude_dir}" "${ci_home}/.config/baloofilerc" || fail "exclusion did not reach persistent baloofilerc"
  printf '2\n' >"${PHASE_FILE}"
  sync
  stage PHASE1_COMPLETE
  echo "AURORA_C4_1B_PHASE1_SUCCESS"
  systemctl poweroff --no-block
  exit 0
fi

[[ -r "${STATE_FILE}" ]] || fail "phase state is missing on boot 2"
# shellcheck disable=SC1090
source "${STATE_FILE}"
for value in root exclude_dir name_file content_file exclude_file name_token content_token exclude_token; do [[ -n "${!value:-}" ]] || fail "phase state field ${value} is missing"; done

stage PERSISTENCE_READ
wait_until 45 baloo_bus_present || fail "Baloo did not return after complete reboot"
wait_until 45 baloo_process_present || fail "baloo_file did not return after complete reboot"
[[ "$(run_user kreadconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --default false)" == "true" ]] || fail "enabled state did not persist across reboot"
[[ "$(run_user kreadconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --default false)" == "true" ]] || fail "KRunner search state did not persist across reboot"
wait_until 60 status_is "${name_file}" done content || fail "filename fixture state did not persist across reboot"
wait_until 60 status_is "${content_file}" done content || fail "content fixture state did not persist across reboot"
status_is "${exclude_file}" disabled none || fail "excluded fixture policy did not persist across reboot"
wait_until 60 search_has_exact_path "${name_token}" "${name_file}" || fail "filename search failed after reboot"
wait_until 60 search_has_exact_path "${content_token}" "${content_file}" || fail "content search failed after reboot"
search_lacks_exact_path "${exclude_token}" "${exclude_file}" || fail "excluded content reappeared after reboot"
run_user balooctl6 status --format json "${name_file}" "${content_file}" "${exclude_file}" >"${OUT}/status-after-reboot.json"

stage EXCLUSION_REVERSE
run_user balooctl6 config remove excludeFolders "${exclude_dir}"
apply_refresh
wait_until 120 status_is "${exclude_file}" done content || fail "previously excluded fixture did not re-enter index after removing exclusion"
wait_until 60 search_has_exact_path "${exclude_token}" "${exclude_file}" || fail "previously excluded fixture did not become searchable again"
run_user balooctl6 status --format json "${exclude_file}" >"${OUT}/status-after-exclusion-reverse.json"
run_user baloosearch6 "${exclude_token}" >"${OUT}/search-exclude-after-reverse.txt"

stage DISABLE
run_user kwriteconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --type bool false
run_user kwriteconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --type bool false
run_user busctl --user call org.kde.baloo / org.kde.baloo.main quit >/dev/null
wait_until 45 baloo_process_absent || fail "baloo_file did not quit after KCM-equivalent disable"
wait_until 45 baloo_bus_absent || fail "org.kde.baloo remained registered after disable"
[[ "$(run_user kreadconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --default true)" == "false" ]] || fail "disabled state did not persist"
[[ "$(run_user kreadconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --default true)" == "false" ]] || fail "KRunner search plugin did not disable with File Search"
record_snapshot disabled

stage REENABLE
run_user kwriteconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' --type bool true
run_user kwriteconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --type bool true
apply_refresh_best_effort || true
launch_baloo_like_kcm
wait_until 45 baloo_bus_present || fail "org.kde.baloo did not recover after KCM-equivalent re-enable"
wait_until 45 baloo_process_present || fail "baloo_file did not recover after KCM-equivalent re-enable"
wait_until 120 status_is "${content_file}" done content || fail "content fixture did not recover after re-enable"
wait_until 60 search_has_exact_path "${content_token}" "${content_file}" || fail "content search did not recover after re-enable"
record_snapshot reenabled

stage CLEANUP
for file in "${name_file}" "${content_file}" "${exclude_file}"; do
  run_user balooctl6 clear "${file}" >/dev/null 2>&1 || fail "balooctl6 clear failed for ${file}"
done
rm -rf "${root}"
restore_configs
configs_restored_exactly || fail "Baloo/KRunner config files were not restored byte-for-byte"
# Apply the restored runtime state. If the baseline had indexing disabled, use
# the KCM quit path; otherwise refresh/start exactly as the KCM does.
if [[ "${original_indexing}" == "true" ]]; then
  apply_refresh_best_effort || true
  launch_baloo_like_kcm
  wait_until 45 baloo_bus_present || fail "original enabled Baloo runtime state was not restored"
else
  if baloo_bus_present; then run_user busctl --user call org.kde.baloo / org.kde.baloo.main quit >/dev/null 2>&1 || true; fi
  wait_until 45 baloo_process_absent || fail "original disabled Baloo runtime state was not restored"
fi
configs_restored_exactly || fail "restored runtime handling changed the original Baloo/KRunner configuration"
# The test entries must no longer be retrievable from the index. Search output
# may contain no results and return a non-zero status, which is acceptable.
for pair in "${name_token}|${name_file}" "${content_token}|${content_file}" "${exclude_token}|${exclude_file}"; do
  token="${pair%%|*}"; file="${pair#*|}"
  search_lacks_exact_path "${token}" "${file}" || fail "test index trace remained after clear/cleanup: ${file}"
done
cleanup_done=1
record_snapshot final

stage STABILITY
sleep 5
kill -0 "${kwin_pid}" >/dev/null 2>&1 || fail "KWin exited during File Search certification"
kill -0 "${plasma_pid}" >/dev/null 2>&1 || fail "plasmashell exited during File Search certification"
[[ "$(first_user_pid kwin_wayland)" == "${kwin_pid}" ]] || fail "KWin restarted unexpectedly during boot 2"
[[ "$(first_user_pid plasmashell)" == "${plasma_pid}" ]] || fail "plasmashell restarted unexpectedly during boot 2"
systemctl --failed --no-pager --plain >"${OUT}/system-failed-units.txt" 2>&1 || true
run_user systemctl --user --failed --no-pager --plain >"${OUT}/user-failed-units.txt" 2>&1 || true
system_failed_count="$(systemctl --failed --no-legend 2>/dev/null | sed '/^[[:space:]]*$/d' | wc -l)"
user_failed_count="$(run_user systemctl --user --failed --no-legend 2>/dev/null | sed '/^[[:space:]]*$/d' | wc -l)"
[[ "${system_failed_count}" -eq 0 ]] || fail "system failed units remain after C4.1b"
[[ "${user_failed_count}" -eq 0 ]] || fail "user failed units remain after C4.1b"
journalctl -b _UID="${ci_uid}" --no-pager >"${OUT}/user-journal-boot2.txt" 2>&1 || true
journalctl -b -u sddm.service --no-pager >"${OUT}/sddm-journal-boot2.txt" 2>&1 || true
assert_no_targeted_crashes "${OUT}/targeted-crashes-boot2.txt" || fail "targeted Baloo/Plasma crash evidence appeared during boot 2"
dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' plasma-desktop plasma-workspace kwin-wayland baloo6 libkf6baloo6 libkf6filemetadata3 >"${OUT}/package-versions.tsv" 2>&1 || true

capability_pass AUR-KCM-003
stage COMPLETE
echo "AURORA_C4_1B_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1b-check"

cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1b-check.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C4.1b File Search functional certification
After=graphical.target sddm.service systemd-logind.service
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c4-1b-check
TimeoutStartSec=840
SERVICE
cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1b-check.timer" <<'TIMER'
[Unit]
Description=Run SupraLINUX Aurora C4.1b File Search functional certification
[Timer]
OnBootSec=20s
AccuracySec=1s
Unit=aurora-ci-c4-1b-check.service
[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c4-1b-check.timer "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1b-check.timer"

sync
umount "${MOUNT_DIR}"

qemu_accel=(-accel tcg -cpu max)
if [[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then qemu_accel=(-enable-kvm -cpu host); fi
count_serial_marker() {
  local marker="$1"
  awk -v marker="${marker}" '{ sub(/\r$/, ""); if ($0 == marker) count++ } END { print count + 0 }' "${SERIAL_LOG}"
}

: >"${SERIAL_LOG}"
host_failure=""
completed_phases=0
for boot_phase in 1 2; do
  echo "==> C4.1b guest boot phase ${boot_phase}"
  set +e
  timeout --signal=TERM --kill-after=15 "${BOOT_TIMEOUT}" \
    qemu-system-x86_64 -machine q35 "${qemu_accel[@]}" -smp 4 -m 4096 -no-reboot \
      -display none -monitor none -serial stdio -vga none -device virtio-vga \
      -kernel "${KERNEL}" -initrd "${INITRD}" \
      -append "root=/dev/vda rw rootfstype=ext4 console=ttyS0,115200n8 systemd.unit=graphical.target systemd.show_status=true systemd.log_target=console panic=-1" \
      -drive "file=${IMAGE},format=raw,if=virtio,cache=unsafe" -device virtio-rng-pci \
      2>&1 | tee -a "${SERIAL_LOG}"
  qemu_status=${PIPESTATUS[0]}
  set -e
  if [[ ${qemu_status} -eq 124 ]]; then host_failure="guest boot phase ${boot_phase} timed out after ${BOOT_TIMEOUT} seconds"; break; fi
  if [[ ${qemu_status} -ne 0 ]]; then host_failure="guest boot phase ${boot_phase} QEMU exited with status ${qemu_status}"; break; fi
  if grep -Fq 'AURORA_C4_1B_FAILURE:' "${SERIAL_LOG}"; then host_failure="guest reported C4.1b failure during boot phase ${boot_phase}"; break; fi
  completed_phases=${boot_phase}
  if [[ ${boot_phase} -eq 1 ]]; then
    phase1_count="$(count_serial_marker 'AURORA_C4_1B_PHASE1_SUCCESS')"
    [[ "${phase1_count}" -eq 1 ]] || { host_failure="expected exactly one C4.1b phase-1 success marker, observed ${phase1_count}"; break; }
  fi
done

mount -o loop,ro "${IMAGE}" "${MOUNT_DIR}"
if [[ -d "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b" ]]; then cp -a "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b/." "${OUT_DIR}/"; fi
if [[ -f "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" ]]; then cp "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" "${SESSION_LOG}"; else : >"${SESSION_LOG}"; fi
umount "${MOUNT_DIR}"
chmod 0644 "${SERIAL_LOG}" "${SESSION_LOG}" 2>/dev/null || true
find "${OUT_DIR}" -type f -exec chmod 0644 {} + 2>/dev/null || true

if [[ -n "${host_failure}" ]]; then echo "Aurora C4.1b host failure: ${host_failure}." >&2; exit 1; fi
[[ "${completed_phases}" -eq 2 ]] || { echo "Expected both C4.1b boot phases, completed ${completed_phases}." >&2; exit 1; }
[[ "$(count_serial_marker 'AURORA_C4_1B_SUCCESS')" -eq 1 ]] || { echo "Expected exactly one C4.1b success marker." >&2; exit 1; }
[[ "$(count_serial_marker 'AURORA_C4_1B_CAPABILITY_PASS=AUR-KCM-003')" -eq 1 ]] || { echo "Expected exactly one AUR-KCM-003 pass marker." >&2; exit 1; }
if grep -Fq 'AURORA_C4_1B_FAILURE:' "${SERIAL_LOG}"; then echo "Aurora C4.1b guest reported failure." >&2; exit 1; fi
for required_stage in SESSION BASELINE ENABLE INCLUDE_ROOT INDEXING EXCLUSION PERSISTENCE_WRITE PHASE1_COMPLETE PERSISTENCE_READ EXCLUSION_REVERSE DISABLE REENABLE CLEANUP STABILITY COMPLETE; do
  stage_count="$(count_serial_marker "AURORA_C4_1B_STAGE=${required_stage}")"
  expected=1
  if [[ "${required_stage}" == "SESSION" ]]; then expected=2; fi
  [[ "${stage_count}" -eq "${expected}" ]] || { echo "Expected ${expected} C4.1b ${required_stage} stage marker(s), observed ${stage_count}." >&2; exit 1; }
done
for evidence in \
  c4-0-baloofile-surface.txt session-executable-resolution.txt baseline-settings.txt \
  status-before-exclusion.json status-after-exclusion.json status-after-reboot.json status-after-exclusion-reverse.json \
  search-name-before-exclusion.txt search-content-before-exclusion.txt search-exclude-before-exclusion.txt \
  search-exclude-after-exclusion.txt search-exclude-after-reverse.txt disabled.txt reenabled.txt final.txt \
  system-failed-units.txt user-failed-units.txt targeted-crashes-boot1.txt targeted-crashes-boot2.txt package-versions.tsv; do
  [[ -f "${OUT_DIR}/${evidence}" ]] || { echo "Missing required C4.1b evidence: ${evidence}" >&2; exit 1; }
done

echo "Aurora C4.1b File Search functional certification passed."
