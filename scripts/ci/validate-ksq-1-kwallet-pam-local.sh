#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="${ROOT}/build/ksq-1/full"
DEBS="${STATE}/debs"
EVIDENCE="${STATE}/kwallet-pam-validation"
SNAPSHOT_ENV="${ROOT}/scripts/ci/aurora-ksq-snapshot-release.env"
PREPARED_CONTROL="${AURORA_KSQ_1_KWALLET_PREPARED_CONTROL:-${STATE}/chunk-061-065/evidence/65-kwallet-pam/debian-control}"
ROOTFS="${AURORA_KSQ_1_KWALLET_ROOTFS:-/tmp/aurora-ksq1-kwallet-pam-rootfs-${GITHUB_RUN_ID:-local}}"
STAGE="${AURORA_KSQ_1_KWALLET_STAGE:-/tmp/aurora-ksq1-kwallet-pam-debs-${GITHUB_RUN_ID:-local}}"

fail() {
  echo "AURORA_KSQ_1_KWALLET_LOCAL_FAILURE: $*" >&2
  exit 1
}

[[ -f "${SNAPSHOT_ENV}" ]] || fail "canonical snapshot pointer missing"
# shellcheck disable=SC1090
set -a
. "${SNAPSHOT_ENV}"
set +a

[[ "${AURORA_KSQ_SNAPSHOT_RELEASE_STATUS}" == "INDEPENDENTLY_VALIDATED" ]] \
  || fail "snapshot release is not independently validated"
[[ "${AURORA_KSQ_SNAPSHOT_SLICE_ID}" == "20260829T022000Z-r2" ]] \
  || fail "unexpected snapshot slice ${AURORA_KSQ_SNAPSHOT_SLICE_ID}"
[[ "${AURORA_KSQ_UBUNTU_SNAPSHOT}" == "20260829T022000Z" ]] \
  || fail "unexpected Ubuntu snapshot ${AURORA_KSQ_UBUNTU_SNAPSHOT}"
[[ "${AURORA_KSQ_SNAPSHOT_ARCH}" == "amd64" ]] || fail "unexpected snapshot architecture"
[[ "${AURORA_KSQ_SNAPSHOT_ARCH_VARIANTS}" == "disabled" ]] || fail "architecture variants enabled"
[[ "${AURORA_KSQ_SNAPSHOT_INSTALL_RECOMMENDS}" == "default" ]] || fail "unexpected Recommends policy"

SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${AURORA_KSQ_SNAPSHOT_SLICE_ID}}"
SOURCES="${ROOT}/build/ksq-0/apt/resolute.sources"

# The maintained KSQ builder is unprivileged. Reject accidental regression to
# the old Docker/root/custom-AppArmor validator contract instead of adapting to it.
[[ "$(id -u)" -ne 0 ]] || fail "validator must run as the unprivileged native runner user"
if [[ -r /proc/self/attr/current ]]; then
  current_profile="$(cat /proc/self/attr/current)"
  [[ "${current_profile}" != *supralinux-ksq-unshare* ]] \
    || fail "legacy custom AppArmor profile is active"
fi
for legacy in \
  "${ROOT}/scripts/ci/ksq-docker-builder.py" \
  "${ROOT}/scripts/ci/install-ksq-apparmor-profile.sh" \
  "${ROOT}/scripts/ci/apparmor/supralinux-ksq-unshare" \
  "${ROOT}/scripts/ci/configure-ksq-uidmap-filecaps.sh"; do
  [[ ! -e "${legacy}" ]] || fail "legacy Docker/AppArmor path present: ${legacy}"
done

for command in dpkg-deb mmdebstrap sha256sum awk chroot; do
  command -v "${command}" >/dev/null || fail "missing command ${command}"
done
[[ -d "${DEBS}" ]] || fail "accumulated DEB directory missing"
[[ -f "${PREPARED_CONTROL}" ]] || fail "prepared kwallet-pam control missing"
[[ -f "${SLICE_ROOT}/COMPLETE" ]] || fail "local snapshot slice incomplete"
[[ -f "${SOURCES}" ]] || fail "local Resolute sources missing"
if grep -RqsE 'https?://' "${SOURCES}"; then
  fail "remote URI leaked into local Resolute sources"
fi
grep -qF "file:${SLICE_ROOT}/ubuntu" "${SOURCES}" || fail "snapshot file URI absent"

find_deb_by_package() {
  local wanted="$1" file package found=""
  while IFS= read -r -d '' file; do
    package="$(dpkg-deb -f "${file}" Package)"
    if [[ "${package}" == "${wanted}" ]]; then
      [[ -z "${found}" ]] || fail "multiple accumulated DEBs for ${wanted}"
      found="${file}"
    fi
  done < <(find "${DEBS}" -maxdepth 1 -type f -name '*.deb' -print0)
  [[ -n "${found}" ]] || fail "accumulated DEB for ${wanted} not found"
  printf '%s\n' "${found}"
}

COMMON_DEB="$(find_deb_by_package libpam-kwallet-common)"
PAM_DEB="$(find_deb_by_package libpam-kwallet5)"
KWALLET_DEB="$(find_deb_by_package kwallet6)"
KWALLET_DATA_DEB="$(find_deb_by_package libkf6wallet-data)"
KWALLET_LIB_DEB="$(find_deb_by_package libkf6wallet6)"
KWALLET_BACKEND_DEB="$(find_deb_by_package libkf6walletbackend6)"

COMMON_VERSION="$(dpkg-deb -f "${COMMON_DEB}" Version)"
PAM_VERSION="$(dpkg-deb -f "${PAM_DEB}" Version)"
KWALLET_VERSION="$(dpkg-deb -f "${KWALLET_DEB}" Version)"
[[ "${COMMON_VERSION}" == "${PAM_VERSION}" ]] || fail "PAM binary versions differ"
[[ "${PAM_VERSION}" == '4:6.7.4-0ubuntu3~supra26.04.1' ]] || fail "unexpected kwallet-pam version ${PAM_VERSION}"
[[ "${KWALLET_VERSION}" == '6.29.0-0ubuntu1~supra26.04.1' ]] || fail "unexpected kwallet6 version ${KWALLET_VERSION}"
for runtime_deb in "${KWALLET_DATA_DEB}" "${KWALLET_LIB_DEB}" "${KWALLET_BACKEND_DEB}"; do
  [[ "$(dpkg-deb -f "${runtime_deb}" Version)" == "${KWALLET_VERSION}" ]] \
    || fail "KWallet runtime binary version mismatch: $(basename "${runtime_deb}")"
done

# Preserve the exact source-level adaptation contract before installation.
grep -Fq 'debhelper-compat (= 13)' "${PREPARED_CONTROL}" || fail "prepared source is not compat 13"
! grep -Fq 'debhelper-compat (= 14)' "${PREPARED_CONTROL}" || fail "compat 14 leaked into prepared source"
! grep -Fq 'dh-sequence-plasma' "${PREPARED_CONTROL}" || fail "intentional Ubuntu no-dh-sequence-plasma delta was lost"
for substvar in '${misc:Depends}' '${qml6:Depends}' '${shlibs:Depends}'; do
  grep -Fq "${substvar}" "${PREPARED_CONTROL}" || fail "prepared source lacks ${substvar}"
done

PAM_DEPENDS="$(dpkg-deb -f "${PAM_DEB}" Depends)"
COMMON_DEPENDS="$(dpkg-deb -f "${COMMON_DEB}" Depends)"
KWALLET_DEPENDS="$(dpkg-deb -f "${KWALLET_DEB}" Depends)"
for required in libpam-kwallet-common libc6 libgcrypt20 libpam0g; do
  printf '%s\n' "${PAM_DEPENDS}" \
    | grep -Eq "(^|, )[[:space:]]*${required}([[:space:](,]|$)" \
    || fail "libpam-kwallet5 missing runtime dependency ${required}"
done
printf '%s\n' "${COMMON_DEPENDS}" \
  | grep -Eq '(^|, )[[:space:]]*socat([[:space:](,]|$)' \
  || fail "libpam-kwallet-common missing socat dependency"
printf '%s\n' "${KWALLET_DEPENDS}" | grep -Fq "libkf6wallet-data (= ${KWALLET_VERSION})" \
  || fail "kwallet6 does not require the rebuilt data package exactly"
printf '%s\n' "${KWALLET_DEPENDS}" | grep -Fq "libkf6walletbackend6 (= ${KWALLET_VERSION})" \
  || fail "kwallet6 does not require the rebuilt backend package exactly"
[[ "${PAM_DEPENDS}" != *'${'* && "${COMMON_DEPENDS}" != *'${'* && "${KWALLET_DEPENDS}" != *'${'* ]] \
  || fail "unexpanded substvar leaked into binary control"

rm -rf "${EVIDENCE}" "${STAGE}"
mkdir -p "${EVIDENCE}" "${STAGE}"
chmod 0755 "${STAGE}"
cp -a "${PREPARED_CONTROL}" "${EVIDENCE}/prepared-debian-control"

candidate_debs=(
  "${COMMON_DEB}" "${PAM_DEB}" "${KWALLET_DEB}"
  "${KWALLET_DATA_DEB}" "${KWALLET_LIB_DEB}" "${KWALLET_BACKEND_DEB}"
)
staged_debs=()
for candidate_deb in "${candidate_debs[@]}"; do
  target="${STAGE}/$(basename "${candidate_deb}")"
  cp -a "${candidate_deb}" "${target}"
  chmod 0644 "${target}"
  staged_debs+=("${target}")
done

(
  cd "${STATE}"
  for candidate_deb in "${candidate_debs[@]}"; do
    sha256sum "debs/$(basename "${candidate_deb}")"
  done
) > "${EVIDENCE}/kwallet-binaries.sha256"

{
  for candidate_deb in "${candidate_debs[@]}"; do
    echo "Package: $(dpkg-deb -f "${candidate_deb}" Package)"
    echo "Version: $(dpkg-deb -f "${candidate_deb}" Version)"
    echo "Depends: $(dpkg-deb -f "${candidate_deb}" Depends 2>/dev/null || true)"
    echo
  done
} > "${EVIDENCE}/binary-control-audit.txt"

cleanup_rootfs() {
  if [[ -e "${ROOTFS}" ]]; then
    mmdebstrap --unshare-helper rm -rf "${ROOTFS}" >/dev/null 2>&1 || true
  fi
  rm -rf "${STAGE}" || true
}
trap cleanup_rootfs EXIT
cleanup_rootfs
mkdir -p "${ROOTFS}"

include_args=()
for staged_deb in "${staged_debs[@]}"; do
  include_args+=("--include=${staged_deb}")
done

# The canonical source list contains file: only. Proxies deliberately point any
# accidental HTTP(S) request at a dead loopback endpoint, so remote fallback is
# fail-closed even though mmdebstrap itself is not run in sbuild's build netns.
set +e
DEBIAN_FRONTEND=noninteractive mmdebstrap \
  --mode=unshare \
  --variant=minbase \
  --architectures=amd64 \
  "${include_args[@]}" \
  --hook-dir=/usr/share/mmdebstrap/hooks/file-mirror-automount \
  --aptopt='Acquire::Check-Valid-Until "false";' \
  --aptopt='Acquire::http::Proxy "http://127.0.0.1:9";' \
  --aptopt='Acquire::https::Proxy "http://127.0.0.1:9";' \
  resolute "${ROOTFS}" "${SOURCES}" \
  2>&1 | tee "${EVIDENCE}/mmdebstrap-install.log"
pipe_status=("${PIPESTATUS[@]}")
set -e
printf 'MMDEBSTRAP_RC=%s\nTEE_RC=%s\n' "${pipe_status[0]}" "${pipe_status[1]}" \
  > "${EVIDENCE}/mmdebstrap-command.env"
[[ "${pipe_status[0]}" -eq 0 ]] || fail "mmdebstrap install failed"
[[ "${pipe_status[1]}" -eq 0 ]] || fail "mmdebstrap evidence tee failed"

if grep -E '^(Get|Hit|Ign|Err):[0-9]+ https?://' "${EVIDENCE}/mmdebstrap-install.log"; then
  fail "remote package transport occurred during KWallet installation"
fi

mmdebstrap --unshare-helper /usr/sbin/chroot "${ROOTFS}" apt-get check \
  | tee "${EVIDENCE}/apt-check.txt"
mmdebstrap --unshare-helper /usr/sbin/chroot "${ROOTFS}" \
  dpkg-query -W libpam-kwallet-common libpam-kwallet5 kwallet6 libkf6wallet-data libkf6wallet6 libkf6walletbackend6 \
  | sort | tee "${EVIDENCE}/installed-versions.tsv"

installed_version() {
  local package="$1"
  awk -v wanted="${package}" '$1 == wanted {print $2}' "${EVIDENCE}/installed-versions.tsv"
}
[[ "$(installed_version libpam-kwallet5)" == "${PAM_VERSION}" ]] || fail "installed libpam-kwallet5 mismatch"
[[ "$(installed_version libpam-kwallet-common)" == "${COMMON_VERSION}" ]] || fail "installed common package mismatch"
for package in kwallet6 libkf6wallet-data libkf6wallet6 libkf6walletbackend6; do
  [[ "$(installed_version "${package}")" == "${KWALLET_VERSION}" ]] \
    || fail "installed ${package} does not match rebuilt KWallet candidate"
done

bash "${ROOT}/scripts/ci/validate-kwallet-pam-installation.sh" "${ROOTFS}" \
  | tee "${EVIDENCE}/pam-registration.txt"
for pam_file in common-auth common-session; do
  grep -nE 'pam_kwallet5\.so' "${ROOTFS}/etc/pam.d/${pam_file}" \
    > "${EVIDENCE}/${pam_file}-kwallet.txt"
done

{
  echo "AURORA_KSQ_1_KWALLET_SOURCE=4:6.7.4-0ubuntu3"
  echo "AURORA_KSQ_1_KWALLET_VERSION=${PAM_VERSION}"
  echo "AURORA_KSQ_1_KWALLET_RUNTIME_VERSION=${KWALLET_VERSION}"
  echo "AURORA_KSQ_1_KWALLET_RUNTIME_PACKAGES=kwallet6+libkf6wallet-data+libkf6wallet6+libkf6walletbackend6"
  echo "AURORA_KSQ_1_KWALLET_COMPAT=13"
  echo "AURORA_KSQ_1_KWALLET_SUBSTVARS_RESTORED=misc+qml6+shlibs"
  echo "AURORA_KSQ_1_KWALLET_BINARY_RUNTIME_DEPS=PASS"
  echo "AURORA_KSQ_1_KWALLET_PAM_INSTALLATION=PASS"
  echo "AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED=no"
  echo "AURORA_KSQ_1_KWALLET_INSTALL_BACKEND=mmdebstrap-unshare-local-debs"
  echo "AURORA_KSQ_1_KWALLET_SLICE=${AURORA_KSQ_SNAPSHOT_SLICE_ID}"
  echo "AURORA_KSQ_1_KWALLET_UBUNTU_SNAPSHOT=${AURORA_KSQ_UBUNTU_SNAPSHOT}"
  echo "AURORA_KSQ_1_KWALLET_REMOTE_FALLBACK=forbidden-loopback-proxy"
  echo "AURORA_KSQ_1_KWALLET_VALIDATOR_MODE=native-unprivileged"
  echo "AURORA_KSQ_1_KWALLET_DOCKER_USED=0"
  echo "AURORA_KSQ_1_KWALLET_CUSTOM_APPARMOR_USED=0"
} > "${EVIDENCE}/status.env"

cat "${EVIDENCE}/status.env"
echo "AURORA_KSQ_1_KWALLET_LOCAL_SUCCESS"
