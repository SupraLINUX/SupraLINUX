#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="${ROOT}/build/ksq-1/full"
DEBS="${STATE}/debs"
EVIDENCE="${STATE}/kwallet-pam-validation"
SNAPSHOT_ENV="${ROOT}/scripts/ci/aurora-ksq-snapshot-release.env"
PREPARED_CONTROL="${AURORA_KSQ_1_KWALLET_PREPARED_CONTROL:-${STATE}/chunk-061-065/evidence/65-kwallet-pam/debian-control}"
ROOTFS="${AURORA_KSQ_1_KWALLET_ROOTFS:-/tmp/aurora-ksq1-kwallet-rootfs-${GITHUB_RUN_ID:-local}}"
STAGE="${AURORA_KSQ_1_KWALLET_STAGE:-/tmp/aurora-ksq1-kwallet-debs-${GITHUB_RUN_ID:-local}}"

fail() { echo "AURORA_KSQ_1_KWALLET_LOCAL_FAILURE: $*" >&2; exit 1; }

[[ -f "${SNAPSHOT_ENV}" ]] || fail "canonical snapshot pointer missing"
set -a
# shellcheck disable=SC1090
. "${SNAPSHOT_ENV}"
set +a
[[ "${AURORA_KSQ_SNAPSHOT_RELEASE_STATUS}" == INDEPENDENTLY_VALIDATED ]] || fail "snapshot not independently validated"
[[ "${AURORA_KSQ_SNAPSHOT_SLICE_ID}" == 20260829T022000Z-r2 ]] || fail "unexpected slice"
[[ "${AURORA_KSQ_UBUNTU_SNAPSHOT}" == 20260829T022000Z ]] || fail "unexpected Ubuntu snapshot"
[[ "${AURORA_KSQ_SNAPSHOT_ARCH}" == amd64 ]] || fail "unexpected architecture"
[[ "${AURORA_KSQ_SNAPSHOT_ARCH_VARIANTS}" == disabled ]] || fail "architecture variants enabled"
[[ "${AURORA_KSQ_SNAPSHOT_INSTALL_RECOMMENDS}" == default ]] || fail "unexpected Recommends policy"

SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${AURORA_KSQ_SNAPSHOT_SLICE_ID}}"
SOURCES="${ROOT}/build/ksq-0/apt/resolute.sources"
[[ "$(id -u)" -ne 0 ]] || fail "validator must run unprivileged"
if [[ -r /proc/self/attr/current ]]; then
  [[ "$(cat /proc/self/attr/current)" != *supralinux-ksq-unshare* ]] || fail "legacy custom AppArmor active"
fi
for legacy in scripts/ci/ksq-docker-builder.py scripts/ci/install-ksq-apparmor-profile.sh scripts/ci/apparmor/supralinux-ksq-unshare scripts/ci/configure-ksq-uidmap-filecaps.sh; do
  [[ ! -e "${ROOT}/${legacy}" ]] || fail "legacy path present: ${legacy}"
done
for command in dpkg-deb mmdebstrap sha256sum awk; do command -v "${command}" >/dev/null || fail "missing ${command}"; done
[[ -d "${DEBS}" ]] || fail "accumulated DEBs missing"
[[ -f "${PREPARED_CONTROL}" ]] || fail "prepared kwallet-pam control missing"
[[ -f "${SLICE_ROOT}/COMPLETE" ]] || fail "slice incomplete"
[[ -f "${SOURCES}" ]] || fail "local sources missing"
! grep -RqsE 'https?://' "${SOURCES}" || fail "remote URI leaked into sources"
grep -qF "file:${SLICE_ROOT}/ubuntu" "${SOURCES}" || fail "slice file URI absent"

find_deb() {
  local wanted="$1" file package found=""
  while IFS= read -r -d '' file; do
    package="$(dpkg-deb -f "${file}" Package)"
    if [[ "${package}" == "${wanted}" ]]; then
      [[ -z "${found}" ]] || fail "multiple DEBs for ${wanted}"
      found="${file}"
    fi
  done < <(find "${DEBS}" -maxdepth 1 -type f -name '*.deb' -print0)
  [[ -n "${found}" ]] || fail "DEB for ${wanted} missing"
  printf '%s\n' "${found}"
}

COMMON_DEB="$(find_deb libpam-kwallet-common)"
PAM_DEB="$(find_deb libpam-kwallet5)"
KWALLET_DEB="$(find_deb kwallet6)"
DATA_DEB="$(find_deb libkf6wallet-data)"
LIB_DEB="$(find_deb libkf6wallet6)"
BACKEND_DEB="$(find_deb libkf6walletbackend6)"
PAM_VERSION="$(dpkg-deb -f "${PAM_DEB}" Version)"
COMMON_VERSION="$(dpkg-deb -f "${COMMON_DEB}" Version)"
KWALLET_VERSION="$(dpkg-deb -f "${KWALLET_DEB}" Version)"
[[ "${PAM_VERSION}" == '4:6.7.4-0ubuntu3~supra26.04.1' ]] || fail "unexpected PAM version ${PAM_VERSION}"
[[ "${COMMON_VERSION}" == "${PAM_VERSION}" ]] || fail "PAM binary versions differ"
[[ "${KWALLET_VERSION}" == '6.29.0-0ubuntu1~supra26.04.1' ]] || fail "unexpected KWallet version"
for deb in "${DATA_DEB}" "${LIB_DEB}" "${BACKEND_DEB}"; do
  [[ "$(dpkg-deb -f "${deb}" Version)" == "${KWALLET_VERSION}" ]] || fail "KWallet runtime version mismatch"
done

grep -Fq 'debhelper-compat (= 13)' "${PREPARED_CONTROL}" || fail "compat 13 absent"
! grep -Fq 'debhelper-compat (= 14)' "${PREPARED_CONTROL}" || fail "compat 14 leaked"
! grep -Fq 'dh-sequence-plasma' "${PREPARED_CONTROL}" || fail "Ubuntu no-dh-sequence-plasma delta lost"
for token in '${misc:Depends}' '${qml6:Depends}' '${shlibs:Depends}'; do grep -Fq "${token}" "${PREPARED_CONTROL}" || fail "missing ${token}"; done

PAM_DEPENDS="$(dpkg-deb -f "${PAM_DEB}" Depends)"
COMMON_DEPENDS="$(dpkg-deb -f "${COMMON_DEB}" Depends)"
KWALLET_DEPENDS="$(dpkg-deb -f "${KWALLET_DEB}" Depends)"
for required in kwallet6 libpam-kwallet-common libpam-runtime libc6 libgcrypt20 libpam0g; do
  printf '%s\n' "${PAM_DEPENDS}" | grep -Eq "(^|, )[[:space:]]*${required}([[:space:](,]|$)" || fail "libpam-kwallet5 missing ${required}"
done
printf '%s\n' "${COMMON_DEPENDS}" | grep -Eq '(^|, )[[:space:]]*socat([[:space:](,]|$)' || fail "common package missing socat"
printf '%s\n' "${KWALLET_DEPENDS}" | grep -Fq "libkf6wallet-data (= ${KWALLET_VERSION})" || fail "kwallet6 data relation wrong"
printf '%s\n' "${KWALLET_DEPENDS}" | grep -Fq "libkf6walletbackend6 (= ${KWALLET_VERSION})" || fail "kwallet6 backend relation wrong"
[[ "${PAM_DEPENDS}${COMMON_DEPENDS}${KWALLET_DEPENDS}" != *'${'* ]] || fail "unexpanded substvar in binary control"

rm -rf "${EVIDENCE}" "${STAGE}"
mkdir -p "${EVIDENCE}" "${STAGE}"
chmod 0755 "${STAGE}"
cp -a "${PREPARED_CONTROL}" "${EVIDENCE}/prepared-debian-control"
candidate_debs=("${COMMON_DEB}" "${PAM_DEB}" "${KWALLET_DEB}" "${DATA_DEB}" "${LIB_DEB}" "${BACKEND_DEB}")
staged=()
for deb in "${candidate_debs[@]}"; do target="${STAGE}/$(basename "${deb}")"; cp -a "${deb}" "${target}"; chmod 0644 "${target}"; staged+=("${target}"); done
(
  cd "${STATE}"
  for deb in "${candidate_debs[@]}"; do sha256sum "debs/$(basename "${deb}")"; done
) > "${EVIDENCE}/kwallet-binaries.sha256"
{
  for deb in "${candidate_debs[@]}"; do
    echo "Package: $(dpkg-deb -f "${deb}" Package)"
    echo "Version: $(dpkg-deb -f "${deb}" Version)"
    echo "Depends: $(dpkg-deb -f "${deb}" Depends 2>/dev/null || true)"
    echo
  done
} > "${EVIDENCE}/binary-control-audit.txt"

cleanup_rootfs() {
  [[ ! -e "${ROOTFS}" ]] || mmdebstrap --unshare-helper rm -rf "${ROOTFS}" >/dev/null 2>&1 || true
}
cleanup_all() {
  cleanup_rootfs
  rm -rf "${STAGE}" || true
}
trap cleanup_all EXIT
cleanup_rootfs
mkdir -p "${ROOTFS}"
include_args=(); for deb in "${staged[@]}"; do include_args+=("--include=${deb}"); done

set +e
DEBIAN_FRONTEND=noninteractive mmdebstrap \
  --mode=unshare --variant=minbase --architectures=amd64 \
  "${include_args[@]}" \
  --hook-dir=/usr/share/mmdebstrap/hooks/file-mirror-automount \
  --aptopt='Acquire::Check-Valid-Until "false";' \
  --aptopt='Acquire::http::Proxy "http://127.0.0.1:9";' \
  --aptopt='Acquire::https::Proxy "http://127.0.0.1:9";' \
  resolute "${ROOTFS}" "${SOURCES}" 2>&1 | tee "${EVIDENCE}/mmdebstrap-install.log"
rcs=("${PIPESTATUS[@]}")
set -e
printf 'MMDEBSTRAP_RC=%s\nTEE_RC=%s\n' "${rcs[0]}" "${rcs[1]}" > "${EVIDENCE}/mmdebstrap-command.env"
[[ "${rcs[0]}" -eq 0 && "${rcs[1]}" -eq 0 ]] || fail "mmdebstrap installation failed"
! grep -E '^(Get|Hit|Ign|Err):[0-9]+ https?://' "${EVIDENCE}/mmdebstrap-install.log" || fail "remote package transport occurred"

mmdebstrap --unshare-helper /usr/sbin/chroot "${ROOTFS}" apt-get check | tee "${EVIDENCE}/apt-check.txt"
mmdebstrap --unshare-helper /usr/sbin/chroot "${ROOTFS}" dpkg-query -W \
  libpam-kwallet-common libpam-kwallet5 kwallet6 libkf6wallet-data libkf6wallet6 libkf6walletbackend6 \
  | sort | tee "${EVIDENCE}/installed-versions.tsv"
installed_version() { awk -v p="$1" '$1 == p {print $2}' "${EVIDENCE}/installed-versions.tsv"; }
[[ "$(installed_version libpam-kwallet5)" == "${PAM_VERSION}" ]] || fail "installed PAM mismatch"
[[ "$(installed_version libpam-kwallet-common)" == "${COMMON_VERSION}" ]] || fail "installed common mismatch"
for package in kwallet6 libkf6wallet-data libkf6wallet6 libkf6walletbackend6; do [[ "$(installed_version "${package}")" == "${KWALLET_VERSION}" ]] || fail "installed ${package} mismatch"; done

bash "${ROOT}/scripts/ci/validate-kwallet-pam-installation.sh" "${ROOTFS}" | tee "${EVIDENCE}/pam-registration.txt"
for pam_file in common-auth common-session; do grep -nE 'pam_kwallet5\.so' "${ROOTFS}/etc/pam.d/${pam_file}" > "${EVIDENCE}/${pam_file}-kwallet.txt"; done

cat > "${EVIDENCE}/status.env" <<EOF
AURORA_KSQ_1_KWALLET_VERSION=${PAM_VERSION}
AURORA_KSQ_1_KWALLET_RUNTIME_VERSION=${KWALLET_VERSION}
AURORA_KSQ_1_KWALLET_COMPAT=13
AURORA_KSQ_1_KWALLET_SUBSTVARS_RESTORED=misc+qml6+shlibs
AURORA_KSQ_1_KWALLET_BINARY_RUNTIME_DEPS=PASS
AURORA_KSQ_1_KWALLET_PAM_INSTALLATION=PASS
AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED=no
AURORA_KSQ_1_KWALLET_INSTALL_BACKEND=mmdebstrap-unshare-local-debs
AURORA_KSQ_1_KWALLET_SLICE=${AURORA_KSQ_SNAPSHOT_SLICE_ID}
AURORA_KSQ_1_KWALLET_UBUNTU_SNAPSHOT=${AURORA_KSQ_UBUNTU_SNAPSHOT}
AURORA_KSQ_1_KWALLET_REMOTE_FALLBACK=forbidden-loopback-proxy
AURORA_KSQ_1_KWALLET_VALIDATOR_MODE=native-unprivileged
AURORA_KSQ_1_KWALLET_DOCKER_USED=0
AURORA_KSQ_1_KWALLET_CUSTOM_APPARMOR_USED=0
EOF
cat "${EVIDENCE}/status.env"
echo AURORA_KSQ_1_KWALLET_LOCAL_SUCCESS
