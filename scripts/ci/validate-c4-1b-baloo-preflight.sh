#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-c4-1b-baloo-preflight.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
KERNEL="${BUILD_DIR}/aurora-c4-0-vmlinuz"
INITRD="${BUILD_DIR}/aurora-c4-0-initrd.img"
C4_0_KCM_INVENTORY="${BUILD_DIR}/c4-0-inventory/actual-kcms.txt"
MOUNT_DIR="${BUILD_DIR}/aurora-c4-1b-preflight-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c4-1b-preflight-serial.log"
SESSION_LOG="${BUILD_DIR}/aurora-c4-1b-preflight-wayland-session.log"
OUT_DIR="${BUILD_DIR}/c4-1b-preflight-evidence"
BOOT_TIMEOUT="${AURORA_C4_1B_BOOT_TIMEOUT:-600}"
CI_USER="auroraci"

for file in "${IMAGE}" "${KERNEL}" "${INITRD}" "${C4_0_KCM_INVENTORY}"; do
  [[ -f "${file}" ]] || { echo "Missing C4.1b prerequisite file: ${file}" >&2; exit 1; }
done
for tool in mount umount mountpoint qemu-system-x86_64 timeout; do
  command -v "${tool}" >/dev/null 2>&1 || { echo "Missing required tool: ${tool}" >&2; exit 1; }
done

mkdir -p "${BUILD_DIR}" "${MOUNT_DIR}"
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
rm -f "${SERIAL_LOG}" "${SESSION_LOG}"

surface_row="$(awk -F '\t' '$1 == "baloofile" && $4 == "AUR-KCM-003" { print; exit }' "${C4_0_KCM_INVENTORY}")"
[[ -n "${surface_row}" ]] || {
  echo "Accepted C4.0 runtime inventory does not expose baloofile as AUR-KCM-003." >&2
  exit 1
}
printf '%s\n' "${surface_row}" >"${OUT_DIR}/c4-0-baloofile-surface.txt"

cleanup() {
  set +e
  if mountpoint -q "${MOUNT_DIR}"; then
    umount "${MOUNT_DIR}" >/dev/null 2>&1 || umount -l "${MOUNT_DIR}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

mount -o loop,rw "${IMAGE}" "${MOUNT_DIR}"
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
rm -f "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1b-preflight.timer"
rm -f "${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1b-preflight.service"
rm -f "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1b-preflight"
rm -rf "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b-preflight"

mkdir -p "${MOUNT_DIR}/usr/local/libexec" "${MOUNT_DIR}/etc/systemd/system/timers.target.wants" "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b-preflight"
printf '%s\n' "${surface_row}" >"${MOUNT_DIR}/var/lib/aurora-ci-c4-1b-preflight/c4-0-baloofile-surface.txt"
cat >"${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1b-preflight" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"
OUT="/var/lib/aurora-ci-c4-1b-preflight"
current_stage="INIT"
ci_uid=""
ci_home=""
runtime_dir=""
session_id=""
original_indexing=""
original_runner=""

mkdir -p "${OUT}"
stage() { current_stage="$1"; echo "AURORA_C4_1B_PREFLIGHT_STAGE=${current_stage}"; }

run_user() {
  runuser -u "${CI_USER}" -- env \
    HOME="${ci_home}" USER="${CI_USER}" LOGNAME="${CI_USER}" \
    XDG_RUNTIME_DIR="${runtime_dir}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime_dir}/bus" \
    "$@"
}

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
  wait_until 30 run_user busctl --user --no-pager list >/dev/null 2>&1
}

baloo_bus_present() {
  run_user busctl --user --no-pager list 2>/dev/null | awk '{print $1}' | grep -Fxq org.kde.baloo
}

record_snapshot() {
  local name="$1"
  {
    echo "== package state =="
    dpkg-query -W -f='${Package}\t${Version}\t${db:Status-Abbrev}\n' plasma-desktop libkf6baloo6 baloo6 2>&1 || true
    echo "== package owner / KCM =="
    dpkg-query -S '*kcm_baloofile.so' 2>&1 || true
    echo "== executable/backend files =="
    for cmd in balooctl6 baloosearch6 kcmshell6 kreadconfig6 kwriteconfig6; do
      printf '%s\t' "${cmd}"; command -v "${cmd}" 2>/dev/null || echo MISSING
    done
    find /usr/lib /usr/bin -xdev \( -name baloo_file -o -name 'kde-baloo.service' -o -name balooctl6 -o -name baloosearch6 \) -print 2>/dev/null | sort
    echo "== user unit =="
    run_user systemctl --user status kde-baloo.service --no-pager --full 2>&1 || true
    run_user systemctl --user cat kde-baloo.service 2>&1 || true
    echo "== dbus =="
    run_user busctl --user --no-pager list 2>&1 | grep -E 'org\.kde\.baloo' || true
    echo "== process =="
    pgrep -a -u "${ci_uid}" -f 'baloo_file' || true
    echo "== baloofilerc =="
    cat "${ci_home}/.config/baloofilerc" 2>/dev/null || true
    echo "== krunnerrc Plugins =="
    sed -n '/^\[Plugins\]/,/^\[/p' "${ci_home}/.config/krunnerrc" 2>/dev/null || true
  } >"${OUT}/${name}.txt"
}

restore_state() {
  set +e
  [[ -n "${original_indexing}" ]] && run_user kwriteconfig6 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" --type bool "${original_indexing}" >/dev/null 2>&1 || true
  [[ -n "${original_runner}" ]] && run_user kwriteconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --type bool "${original_runner}" >/dev/null 2>&1 || true
}

fail() {
  local message="$*"
  trap - ERR
  set +e
  echo "AURORA_C4_1B_PREFLIGHT_FAILURE: ${current_stage}: ${message}"
  record_snapshot failure || true
  systemctl --failed --no-pager --plain || true
  run_user systemctl --user --failed --no-pager --plain || true
  restore_state
  sync
  systemctl poweroff --no-block || true
  exit 1
}
trap 'status=$?; fail "unexpected shell error status ${status} at line ${BASH_LINENO[0]:-unknown}"' ERR

echo "AURORA_C4_1B_PREFLIGHT_START"
stage SESSION
ci_uid="$(id -u "${CI_USER}" 2>/dev/null || true)"
ci_home="$(getent passwd "${CI_USER}" | awk -F: '{print $6}')"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable user is missing"
bind_live_session || fail "Plasma Wayland session did not become ready"

stage SURFACE
awk -F '\t' '$1 == "baloofile" && $4 == "AUR-KCM-003" { found=1 } END { exit !found }' "${OUT}/c4-0-baloofile-surface.txt" || fail "accepted C4.0 inventory no longer proves the File Search surface"
dpkg-query -S '*kcm_baloofile.so' >"${OUT}/kcm-owner.txt" 2>&1 || fail "File Search KCM package owner is unresolved"
grep -Fq 'plasma-desktop:' "${OUT}/kcm-owner.txt" || fail "File Search KCM is not owned by the expected Plasma package"

stage BASELINE
original_indexing="$(run_user kreadconfig6 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" --default true)"
original_runner="$(run_user kreadconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --default true)"
printf 'Indexing-Enabled=%s\nbaloosearchEnabled=%s\n' "${original_indexing}" "${original_runner}" >"${OUT}/baseline-settings.txt"
record_snapshot baseline

stage ENABLE
run_user kwriteconfig6 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" --type bool true
run_user kwriteconfig6 --file krunnerrc --group Plugins --key baloosearchEnabled --type bool true
set +e
run_user systemctl --user start kde-baloo.service >"${OUT}/service-start.txt" 2>&1
start_status=$?
set -e
printf 'status=%s\n' "${start_status}" >>"${OUT}/service-start.txt"
record_snapshot after-enable
[[ "${start_status}" -eq 0 ]] || fail "the exposed File Search enable path has no startable kde-baloo.service backend"
wait_until 30 run_user systemctl --user is-active --quiet kde-baloo.service || fail "kde-baloo.service did not become active"
wait_until 30 baloo_bus_present || fail "org.kde.baloo did not register after enabling File Search"
run_user busctl --user --no-pager introspect org.kde.baloo / >"${OUT}/baloo-dbus.txt" 2>&1 || fail "org.kde.baloo main interface is unavailable"
pgrep -a -u "${ci_uid}" -f 'baloo_file' >"${OUT}/baloo-process.txt" || fail "Baloo service is active but no baloo_file process exists"

stage RESTORE
restore_state
record_snapshot restored

stage COMPLETE
echo "AURORA_C4_1B_PREFLIGHT_BACKEND_PRESENT"
echo "AURORA_C4_1B_PREFLIGHT_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${MOUNT_DIR}/usr/local/libexec/aurora-ci-c4-1b-preflight"

cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1b-preflight.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C4.1b File Search/Baloo backend preflight
After=graphical.target sddm.service systemd-logind.service
[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c4-1b-preflight
TimeoutStartSec=300
SERVICE
cat >"${MOUNT_DIR}/etc/systemd/system/aurora-ci-c4-1b-preflight.timer" <<'TIMER'
[Timer]
OnBootSec=20s
AccuracySec=1s
Unit=aurora-ci-c4-1b-preflight.service
[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c4-1b-preflight.timer "${MOUNT_DIR}/etc/systemd/system/timers.target.wants/aurora-ci-c4-1b-preflight.timer"

sync
umount "${MOUNT_DIR}"
qemu_accel=(-accel tcg -cpu max)
if [[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then qemu_accel=(-enable-kvm -cpu host); fi

set +e
timeout --signal=TERM --kill-after=15 "${BOOT_TIMEOUT}" \
  qemu-system-x86_64 -machine q35 "${qemu_accel[@]}" -smp 4 -m 4096 -no-reboot \
    -display none -monitor none -serial stdio -vga none -device virtio-vga \
    -kernel "${KERNEL}" -initrd "${INITRD}" \
    -append "root=/dev/vda rw rootfstype=ext4 console=ttyS0,115200n8 systemd.unit=graphical.target systemd.show_status=true systemd.log_target=console panic=-1" \
    -drive "file=${IMAGE},format=raw,if=virtio,cache=unsafe" -device virtio-rng-pci \
    2>&1 | tee "${SERIAL_LOG}"
qemu_status=${PIPESTATUS[0]}
set -e

mount -o loop,ro "${IMAGE}" "${MOUNT_DIR}"
if [[ -d "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b-preflight" ]]; then cp -a "${MOUNT_DIR}/var/lib/aurora-ci-c4-1b-preflight/." "${OUT_DIR}/"; fi
if [[ -f "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" ]]; then cp "${MOUNT_DIR}/home/${CI_USER}/.local/share/sddm/wayland-session.log" "${SESSION_LOG}"; else : >"${SESSION_LOG}"; fi
umount "${MOUNT_DIR}"
chmod 0644 "${SERIAL_LOG}" "${SESSION_LOG}" 2>/dev/null || true
find "${OUT_DIR}" -type f -exec chmod 0644 {} + 2>/dev/null || true

[[ "${qemu_status}" -eq 0 ]] || { echo "C4.1b preflight QEMU exited with ${qemu_status}." >&2; exit 1; }
if grep -Fq 'AURORA_C4_1B_PREFLIGHT_FAILURE:' "${SERIAL_LOG}"; then echo "C4.1b preflight guest reported failure." >&2; exit 1; fi
if ! tr -d '\r' <"${SERIAL_LOG}" | grep -Fxq 'AURORA_C4_1B_PREFLIGHT_SUCCESS'; then echo "C4.1b preflight success marker missing." >&2; exit 1; fi

echo "Aurora C4.1b Baloo backend preflight passed."
