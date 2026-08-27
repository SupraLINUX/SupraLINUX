#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "validate-c4-0-surface.sh must run as root." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
ROOTFS="${BUILD_DIR}/aurora-c4-0-rootfs"
SERIAL_LOG="${BUILD_DIR}/aurora-c4-0-serial.log"
SESSION_LOG="${BUILD_DIR}/aurora-c4-0-wayland-session.log"
INVENTORY_DIR="${BUILD_DIR}/c4-0-inventory"
IMAGE_SIZE="${AURORA_C4_0_IMAGE_SIZE:-12G}"
BOOT_TIMEOUT="${AURORA_C4_0_BOOT_TIMEOUT:-900}"
CI_USER="auroraci"

KCM_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-kcm-coverage.tsv"
DEPENDENCY_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-dependency-coverage.tsv"
PORTAL_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-portal-coverage.tsv"

for manifest in "${KCM_MANIFEST}" "${DEPENDENCY_MANIFEST}" "${PORTAL_MANIFEST}"; do
  [[ -r "${manifest}" ]] || {
    echo "Missing C4.0 coverage manifest: ${manifest}" >&2
    exit 1
  }
done

required_tools=(mkfs.ext4 mount umount mountpoint blkid qemu-system-x86_64 timeout chroot)
for tool in "${required_tools[@]}"; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "Missing required tool: ${tool}" >&2
    exit 1
  }
done

mkdir -p "${BUILD_DIR}" "${ROOTFS}"
rm -rf "${INVENTORY_DIR}"
mkdir -p "${INVENTORY_DIR}"
rm -f "${IMAGE}" "${SERIAL_LOG}" "${SESSION_LOG}" \
  "${BUILD_DIR}/aurora-c4-0-vmlinuz" "${BUILD_DIR}/aurora-c4-0-initrd.img"

cleanup() {
  set +e
  if mountpoint -q "${ROOTFS}"; then
    umount "${ROOTFS}" >/dev/null 2>&1 || umount -l "${ROOTFS}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Creating sparse ${IMAGE_SIZE} ext4 disk image"
truncate -s "${IMAGE_SIZE}" "${IMAGE}"
mkfs.ext4 -F -L AURORA_C4_0 "${IMAGE}" >/dev/null
mount -o loop "${IMAGE}" "${ROOTFS}"

echo "==> Installing Aurora into the C4.0 boot disk"
AURORA_ROOTFS_DIR="${ROOTFS}" bash "${ROOT_DIR}/scripts/ci/validate-clean-rootfs.sh"

rm -f "${ROOTFS}/usr/sbin/policy-rc.d"
rm -rf "${ROOTFS}/tmp/supralinux"

if [[ ! -x "${ROOTFS}/usr/sbin/update-locale" ]]; then
  echo "update-locale is unavailable in the Aurora rootfs." >&2
  exit 1
fi
chroot "${ROOTFS}" /usr/sbin/update-locale LANG=C.UTF-8

echo aurora-c4-0 >"${ROOTFS}/etc/hostname"
cat >"${ROOTFS}/etc/hosts" <<'HOSTS'
127.0.0.1 localhost
127.0.1.1 aurora-c4-0
::1 localhost ip6-localhost ip6-loopback
HOSTS

root_uuid="$(blkid -s UUID -o value "${IMAGE}")"
[[ -n "${root_uuid}" ]] || {
  echo "Could not determine the ext4 filesystem UUID." >&2
  exit 1
}
cat >"${ROOTFS}/etc/fstab" <<FSTAB
UUID=${root_uuid} / ext4 defaults 0 1
FSTAB

echo "==> Creating disposable C4.0 desktop user"
chroot "${ROOTFS}" useradd --create-home --shell /bin/bash "${CI_USER}"
ci_uid="$(chroot "${ROOTFS}" id -u "${CI_USER}")"
[[ -n "${ci_uid}" ]] || {
  echo "Could not determine disposable C4.0 user UID." >&2
  exit 1
}

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
echo "==> C4.0 autologin session: ${plasma_wayland_session}"

cat >"${ROOTFS}/etc/sddm.conf.d/99-aurora-ci-c4-0-autologin.conf" <<EOF_AUTLOGIN
[Autologin]
User=${CI_USER}
Session=${plasma_wayland_session}
Relogin=false
EOF_AUTLOGIN

mkdir -p "${ROOTFS}/usr/local/share/aurora-ci/c4-0"
cp "${KCM_MANIFEST}" "${ROOTFS}/usr/local/share/aurora-ci/c4-0/kcm-coverage.tsv"
cp "${DEPENDENCY_MANIFEST}" "${ROOTFS}/usr/local/share/aurora-ci/c4-0/dependency-coverage.tsv"
cp "${PORTAL_MANIFEST}" "${ROOTFS}/usr/local/share/aurora-ci/c4-0/portal-coverage.tsv"
chmod 0644 "${ROOTFS}/usr/local/share/aurora-ci/c4-0/"*.tsv

mkdir -p "${ROOTFS}/usr/local/libexec" "${ROOTFS}/etc/systemd/system/timers.target.wants"
cat >"${ROOTFS}/usr/local/libexec/aurora-ci-c4-0-check" <<'GUEST'
#!/usr/bin/env bash
set -Eeuo pipefail
exec >/dev/ttyS0 2>&1

CI_USER="auroraci"
OUT="/var/lib/aurora-ci-c4-0"
MANIFEST_DIR="/usr/local/share/aurora-ci/c4-0"
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

mkdir -p "${OUT}"

stage() {
  current_stage="$1"
  echo "AURORA_C4_0_STAGE=${current_stage}"
}

capability_pass() {
  echo "AURORA_C4_0_CAPABILITY_PASS=$1"
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
    LC_ALL="${session_lang}" \
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

dump_diagnostics() {
  echo "AURORA_C4_0_DIAGNOSTICS_START"
  echo "AURORA_C4_0_LAST_STAGE=${current_stage}"
  systemctl --failed --no-pager --plain || true
  systemctl status sddm.service --no-pager --full || true
  loginctl list-sessions --no-pager || true
  if [[ -n "${session_id}" ]]; then
    loginctl session-status "${session_id}" --no-pager || true
    loginctl show-session "${session_id}" --all --no-pager || true
  fi
  if [[ -n "${ci_uid}" ]]; then
    echo "--- disposable user processes ---"
    pgrep -a -u "${ci_uid}" || true
  fi
  if [[ -n "${runtime_dir}" && -S "${runtime_dir}/bus" ]]; then
    echo "--- user failed units ---"
    run_user systemctl --user --failed --no-pager --plain || true
    echo "--- user bus names ---"
    run_user busctl --user --no-pager list || true
  fi
  echo "--- C4.0 inventory files ---"
  find "${OUT}" -maxdepth 1 -type f -printf '%f\n' 2>/dev/null | sort || true
  for file in unknown-kcms.txt missing-kcms.txt unknown-dependencies.txt missing-dependencies.txt unknown-portals.txt missing-portals.txt; do
    if [[ -f "${OUT}/${file}" ]]; then
      echo "--- ${file} ---"
      cat "${OUT}/${file}" || true
    fi
  done
  echo "--- SDDM journal ---"
  journalctl -b -u sddm.service --no-pager -n 250 || true
  echo "--- user Wayland session log ---"
  cat "/home/${CI_USER}/.local/share/sddm/wayland-session.log" 2>/dev/null || true
  echo "AURORA_C4_0_DIAGNOSTICS_END"
}

fail() {
  local message="$*"
  trap - ERR
  set +e
  echo "AURORA_C4_0_FAILURE: ${current_stage}: ${message}"
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
  echo "AURORA_C4_0_FAILURE: ${current_stage}: unexpected shell error status ${status} at line ${line}"
  dump_diagnostics
  sync
  systemctl poweroff --no-block || true
  exit "${status}"
}
trap unexpected_error ERR

echo "AURORA_C4_0_CHECK_START"

stage SESSION
[[ "$(cat /proc/1/comm)" == "systemd" ]] || fail "PID 1 is not systemd"
systemctl is-active --quiet graphical.target || fail "graphical.target is not active"
command -v runuser >/dev/null 2>&1 || fail "runuser is unavailable"
command -v kcmshell6 >/dev/null 2>&1 || fail "kcmshell6 is unavailable"

ci_uid="$(id -u "${CI_USER}" 2>/dev/null || true)"
passwd_entry="$(getent passwd "${CI_USER}" 2>/dev/null || true)"
ci_home="$(awk -F: '{print $6}' <<<"${passwd_entry}")"
[[ -n "${ci_uid}" && -n "${ci_home}" ]] || fail "disposable C4.0 user is missing"
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
[[ "${session_ready}" -eq 1 ]] || fail "disposable user did not obtain an active Wayland login session"

user_bus_ready=0
for ((i = 0; i < 30; i++)); do
  if [[ -S "${runtime_dir}/bus" ]] && run_user busctl --user --no-pager list >/dev/null 2>&1; then
    user_bus_ready=1
    break
  fi
  sleep 1
done
[[ "${user_bus_ready}" -eq 1 ]] || fail "user D-Bus session did not become usable"

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
echo "${xdg_current_desktop}" >"${OUT}/xdg-current-desktop.txt"
grep -Eq '(^|:)KDE(:|$)' <<<"${xdg_current_desktop}" || fail "XDG_CURRENT_DESKTOP does not identify KDE (${xdg_current_desktop:-missing})"
[[ -n "${wayland_display}" ]] || fail "WAYLAND_DISPLAY is missing from the live Plasma session"
[[ -S "${runtime_dir}/${wayland_display}" ]] || fail "Wayland display socket ${runtime_dir}/${wayland_display} is missing"
[[ -n "${display}" ]] || fail "DISPLAY is missing from the live Plasma session"
[[ -n "${xauthority}" ]] || fail "XAUTHORITY is missing from the live Plasma session"
runuser -u "${CI_USER}" -- test -r "${xauthority}" || fail "Xauthority file ${xauthority} is not readable by the Plasma user"
[[ -n "${session_lang}" ]] || fail "LANG is missing from the live Plasma session"
[[ -n "${xdg_config_dirs}" ]] || xdg_config_dirs="/etc/xdg"
[[ -n "${xdg_data_dirs}" ]] || xdg_data_dirs="/usr/local/share:/usr/share"

stage KCMS
run_user_session kcmshell6 --list >"${OUT}/kcmshell6-list.txt" 2>&1 \
  || fail "kcmshell6 --list failed inside the live Plasma session environment"
awk '
  /^[[:space:]]*[[:alnum:]_.-]+[[:space:]]+-[[:space:]]+/ {
    line=$0
    sub(/^[[:space:]]*/, "", line)
    split(line, fields, /[[:space:]]+/)
    print fields[1]
  }
' "${OUT}/kcmshell6-list.txt" | sort -u >"${OUT}/actual-kcms.txt"
awk -F '\t' '!/^#/ && NF {print $1}' "${MANIFEST_DIR}/kcm-coverage.tsv" | sort -u >"${OUT}/expected-kcms.txt"
comm -23 "${OUT}/actual-kcms.txt" "${OUT}/expected-kcms.txt" >"${OUT}/unknown-kcms.txt"
comm -13 "${OUT}/actual-kcms.txt" "${OUT}/expected-kcms.txt" >"${OUT}/missing-kcms.txt"

stage DEPENDENCIES
dpkg-query -W -f='${Depends}\n' supralinux-desktop >"${OUT}/desktop-dependencies-raw.txt"
tr ',' '\n' <"${OUT}/desktop-dependencies-raw.txt" \
  | sed -E 's/[[:space:]]*\([^)]*\)//g; s/[[:space:]]*\|.*$//; s/:any$//; s/^[[:space:]]+//; s/[[:space:]]+$//' \
  | grep -Ev '^$' \
  | sort -u >"${OUT}/actual-dependencies.txt"
awk -F '\t' '!/^#/ && NF {print $1}' "${MANIFEST_DIR}/dependency-coverage.tsv" | sort -u >"${OUT}/expected-dependencies.txt"
comm -23 "${OUT}/actual-dependencies.txt" "${OUT}/expected-dependencies.txt" >"${OUT}/unknown-dependencies.txt"
comm -13 "${OUT}/actual-dependencies.txt" "${OUT}/expected-dependencies.txt" >"${OUT}/missing-dependencies.txt"

: >"${OUT}/product-dependency-versions.tsv"
while IFS=$'\t' read -r package capability owner; do
  [[ -n "${package}" && "${package}" != \#* ]] || continue
  version="$(dpkg-query -W -f='${Version}' "${package}" 2>/dev/null || true)"
  status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  printf '%s\t%s\t%s\t%s\t%s\n' "${package}" "${version:-MISSING}" "${status:-MISSING}" "${capability}" "${owner}" >>"${OUT}/product-dependency-versions.tsv"
done <"${MANIFEST_DIR}/dependency-coverage.tsv"

stage PORTALS
mkdir -p "${OUT}/portal-files"
if [[ -d /usr/share/xdg-desktop-portal/portals ]]; then
  find /usr/share/xdg-desktop-portal/portals -maxdepth 1 -type f -name '*.portal' -printf '%f\n' \
    | sed 's/\.portal$//' | sort -u >"${OUT}/actual-portals.txt"
  cp -a /usr/share/xdg-desktop-portal/portals/. "${OUT}/portal-files/" 2>/dev/null || true
else
  : >"${OUT}/actual-portals.txt"
fi
awk -F '\t' '!/^#/ && NF {print $1}' "${MANIFEST_DIR}/portal-coverage.tsv" | sort -u >"${OUT}/expected-portals.txt"
comm -23 "${OUT}/actual-portals.txt" "${OUT}/expected-portals.txt" >"${OUT}/unknown-portals.txt"
comm -13 "${OUT}/actual-portals.txt" "${OUT}/expected-portals.txt" >"${OUT}/missing-portals.txt"

: >"${OUT}/portal-routing-files.txt"
for base in \
  "${ci_home}/.config/xdg-desktop-portal" \
  /etc/xdg/xdg-desktop-portal \
  /usr/local/etc/xdg-desktop-portal \
  /usr/local/share/xdg-desktop-portal \
  /usr/share/xdg-desktop-portal; do
  [[ -d "${base}" ]] || continue
  while IFS= read -r file; do
    echo "===== ${file} =====" >>"${OUT}/portal-routing-files.txt"
    cat "${file}" >>"${OUT}/portal-routing-files.txt" 2>/dev/null || true
    echo >>"${OUT}/portal-routing-files.txt"
  done < <(find "${base}" -maxdepth 1 -type f \( -name 'portals.conf' -o -name '*-portals.conf' \) -print | sort)
done

portal_config_count="$(grep -c '^===== .*portals\.conf =====$' "${OUT}/portal-routing-files.txt" 2>/dev/null || true)"

stage AUXILIARY
systemctl list-unit-files --no-pager \
  | grep -Ei 'NetworkManager|bluetooth|cups|udisks|power|ModemManager|switcheroo|sddm' \
  >"${OUT}/relevant-system-unit-files.txt" || true
run_user systemctl --user list-unit-files --no-pager \
  | grep -Ei 'plasma|pipewire|wireplumber|portal|polkit|kwallet|kio|krdp' \
  >"${OUT}/relevant-user-unit-files.txt" || true
busctl --system --no-pager list >"${OUT}/system-bus-names.txt" 2>&1 || true
run_user busctl --user --no-pager list >"${OUT}/user-bus-names.txt" 2>&1 || true

for package in kdenetwork-filesharing kio-extras kde-config-flatpak krdp print-manager bluedevil plasma-nm plasma-pa powerdevil kde-config-sddm plasma-disks; do
  echo "===== ${package} =====" >>"${OUT}/integration-package-files.txt"
  dpkg -L "${package}" >>"${OUT}/integration-package-files.txt" 2>&1 || true
  echo >>"${OUT}/integration-package-files.txt"
done

stage COVERAGE
coverage_failure=0

if [[ -s "${OUT}/unknown-kcms.txt" || -s "${OUT}/missing-kcms.txt" ]]; then
  echo "AURORA_C4_0_COVERAGE_MISMATCH=KCMS"
  coverage_failure=1
else
  capability_pass AUR-COVER-001
  capability_pass AUR-COVER-002
fi

if [[ -s "${OUT}/unknown-dependencies.txt" || -s "${OUT}/missing-dependencies.txt" ]]; then
  echo "AURORA_C4_0_COVERAGE_MISMATCH=DEPENDENCIES"
  coverage_failure=1
else
  capability_pass AUR-COVER-003
  capability_pass AUR-COVER-004
fi

if [[ -s "${OUT}/unknown-portals.txt" || -s "${OUT}/missing-portals.txt" || "${portal_config_count}" -lt 1 ]]; then
  echo "AURORA_C4_0_COVERAGE_MISMATCH=PORTALS"
  coverage_failure=1
else
  capability_pass AUR-COVER-005
fi

if [[ "${coverage_failure}" -ne 0 ]]; then
  fail "runtime surface differs from the versioned C4.0 coverage manifests"
fi

stage STABILITY
sleep 5
kill -0 "${kwin_pid}" >/dev/null 2>&1 || fail "KWin Wayland did not remain stable through C4.0"
kill -0 "${plasma_pid}" >/dev/null 2>&1 || fail "plasmashell did not remain stable through C4.0"
[[ "$(first_user_pid kwin_wayland)" == "${kwin_pid}" ]] || fail "KWin Wayland restarted during C4.0"
[[ "$(first_user_pid plasmashell)" == "${plasma_pid}" ]] || fail "plasmashell restarted during C4.0"

stage COMPLETE
echo "AURORA_C4_0_SUCCESS"
sync
systemctl poweroff --no-block
GUEST
chmod 0755 "${ROOTFS}/usr/local/libexec/aurora-ci-c4-0-check"

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c4-0-check.service" <<'SERVICE'
[Unit]
Description=SupraLINUX Aurora C4.0 surface and contract inventory probe
After=graphical.target sddm.service systemd-logind.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/aurora-ci-c4-0-check
TimeoutStartSec=420
SERVICE

cat >"${ROOTFS}/etc/systemd/system/aurora-ci-c4-0-check.timer" <<'TIMER'
[Unit]
Description=Run SupraLINUX Aurora C4.0 surface and contract inventory probe

[Timer]
OnBootSec=20s
AccuracySec=1s
Unit=aurora-ci-c4-0-check.service

[Install]
WantedBy=timers.target
TIMER
ln -s ../aurora-ci-c4-0-check.timer "${ROOTFS}/etc/systemd/system/timers.target.wants/aurora-ci-c4-0-check.timer"

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
[[ -f "${ROOTFS}/boot/${initrd_path}" ]] || {
  echo "Matching initramfs ${initrd_path} is missing." >&2
  exit 1
}

cp "${ROOTFS}/boot/${kernel_path}" "${BUILD_DIR}/aurora-c4-0-vmlinuz"
cp "${ROOTFS}/boot/${initrd_path}" "${BUILD_DIR}/aurora-c4-0-initrd.img"
sync
umount "${ROOTFS}"

echo "==> Booting Aurora C4.0 VM with kernel ${kernel_version}"
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
    -kernel "${BUILD_DIR}/aurora-c4-0-vmlinuz" \
    -initrd "${BUILD_DIR}/aurora-c4-0-initrd.img" \
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
if [[ -d "${ROOTFS}/var/lib/aurora-ci-c4-0" ]]; then
  cp -a "${ROOTFS}/var/lib/aurora-ci-c4-0/." "${INVENTORY_DIR}/"
fi
umount "${ROOTFS}"
chmod 0644 "${SERIAL_LOG}" "${SESSION_LOG}"
find "${INVENTORY_DIR}" -type f -exec chmod 0644 {} + 2>/dev/null || true

if [[ ${qemu_status} -eq 124 ]]; then
  echo "Aurora C4.0 VM timed out after ${BOOT_TIMEOUT} seconds." >&2
  exit 1
fi
if [[ ${qemu_status} -ne 0 ]]; then
  echo "Aurora C4.0 QEMU exited with status ${qemu_status}." >&2
  exit 1
fi

success_count="$(grep -Fc 'AURORA_C4_0_SUCCESS' "${SERIAL_LOG}" || true)"
if [[ "${success_count}" -ne 1 ]]; then
  echo "Expected exactly one Aurora C4.0 success marker, observed ${success_count}." >&2
  exit 1
fi
if grep -Fq 'AURORA_C4_0_FAILURE:' "${SERIAL_LOG}"; then
  echo "Aurora C4.0 guest probe reported failure." >&2
  exit 1
fi

for capability in AUR-COVER-001 AUR-COVER-002 AUR-COVER-003 AUR-COVER-004 AUR-COVER-005; do
  capability_count="$(grep -Fc "AURORA_C4_0_CAPABILITY_PASS=${capability}" "${SERIAL_LOG}" || true)"
  if [[ "${capability_count}" -ne 1 ]]; then
    echo "Expected exactly one Aurora C4.0 ${capability} PASS marker, observed ${capability_count}." >&2
    exit 1
  fi
done

for required_stage in SESSION KCMS DEPENDENCIES PORTALS AUXILIARY COVERAGE STABILITY COMPLETE; do
  stage_count="$(grep -Fc "AURORA_C4_0_STAGE=${required_stage}" "${SERIAL_LOG}" || true)"
  if [[ "${stage_count}" -ne 1 ]]; then
    echo "Expected exactly one Aurora C4.0 ${required_stage} stage marker, observed ${stage_count}." >&2
    exit 1
  fi
done

echo "Aurora C4.0 surface and contract inventory validation passed."
