#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="${ROOT}/build/ksq-1/full"
DEBS="${STATE}/debs"
EVIDENCE="${STATE}/kwallet-pam-validation"
SNAPSHOT_ENV="${ROOT}/tests/kde-stack/apt-metadata-snapshot.env"
PREPARED_CONTROL="${STATE}/chunk-061-080/evidence/65-kwallet-pam/debian-control"

fail() {
  echo "AURORA_KSQ_1_KWALLET_FAILURE: $*" >&2
  exit 1
}

for command in dpkg-deb dpkg-scanpackages mmdebstrap gzip sudo; do
  command -v "${command}" >/dev/null || fail "missing command ${command}"
done
[[ -d "${DEBS}" ]] || fail "accumulated DEB directory missing"
[[ -f "${PREPARED_CONTROL}" ]] || fail "prepared kwallet-pam control missing"

# shellcheck disable=SC1090
. "${SNAPSHOT_ENV}"
SNAPSHOT="${AURORA_KSQ_0_APT_SNAPSHOT:?missing snapshot}"

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
COMMON_VERSION="$(dpkg-deb -f "${COMMON_DEB}" Version)"
PAM_VERSION="$(dpkg-deb -f "${PAM_DEB}" Version)"
[[ "${COMMON_VERSION}" == "${PAM_VERSION}" ]] || {
  fail "kwallet PAM binary versions differ: ${COMMON_VERSION} vs ${PAM_VERSION}"
}
[[ "${PAM_VERSION}" == '4:6.7.4-0ubuntu3~supra26.04.1' ]] || {
  fail "unexpected kwallet-pam version ${PAM_VERSION}"
}

grep -Fq 'debhelper-compat (= 13)' "${PREPARED_CONTROL}" || fail "prepared source is not compat 13"
! grep -Fq 'debhelper-compat (= 14)' "${PREPARED_CONTROL}" || fail "compat 14 leaked into prepared source"
! grep -Fq 'dh-sequence-plasma' "${PREPARED_CONTROL}" || {
  fail "Ubuntu intentional no-dh-sequence-plasma delta was lost"
}
for substvar in '${misc:Depends}' '${qml6:Depends}' '${shlibs:Depends}'; do
  grep -Fq "${substvar}" "${PREPARED_CONTROL}" || fail "prepared source lacks ${substvar}"
done

PAM_DEPENDS="$(dpkg-deb -f "${PAM_DEB}" Depends)"
COMMON_DEPENDS="$(dpkg-deb -f "${COMMON_DEB}" Depends)"
for required in kwallet6 libpam-kwallet-common libpam-runtime libc6 libgcrypt20 libpam0g; do
  printf '%s\n' "${PAM_DEPENDS}" \
    | grep -Eq "(^|, )[[:space:]]*${required}([[:space:](,]|$)" \
    || fail "libpam-kwallet5 missing runtime dependency ${required}"
done
printf '%s\n' "${COMMON_DEPENDS}" \
  | grep -Eq '(^|, )[[:space:]]*socat([[:space:](,]|$)' \
  || fail "libpam-kwallet-common missing socat dependency"
[[ "${PAM_DEPENDS}" != *'${'* && "${COMMON_DEPENDS}" != *'${'* ]] || {
  fail "unexpanded substvar leaked into binary control"
}

rm -rf "${EVIDENCE}"
mkdir -p "${EVIDENCE}/repo"
cp -a "${DEBS}"/*.deb "${EVIDENCE}/repo/"
(
  cd "${EVIDENCE}/repo"
  dpkg-scanpackages . /dev/null > Packages
  gzip -n -9 -c Packages > Packages.gz
)
(
  cd "${STATE}"
  sha256sum "debs/$(basename "${COMMON_DEB}")" "debs/$(basename "${PAM_DEB}")" \
    > "${EVIDENCE}/kwallet-binaries.sha256"
)
{
  echo "Package: libpam-kwallet-common"
  echo "Version: ${COMMON_VERSION}"
  echo "Depends: ${COMMON_DEPENDS}"
  echo
  echo "Package: libpam-kwallet5"
  echo "Version: ${PAM_VERSION}"
  echo "Depends: ${PAM_DEPENDS}"
} > "${EVIDENCE}/binary-control-audit.txt"
cp -a "${PREPARED_CONTROL}" "${EVIDENCE}/prepared-debian-control"

SOURCES="${EVIDENCE}/resolute-snapshot.sources"
cat > "${SOURCES}" <<EOF_SOURCES
Types: deb
URIs: https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF_SOURCES

ROOTFS="${STATE}/kwallet-pam-test-rootfs"
cleanup() {
  sudo rm -rf "${ROOTFS}" >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

sudo mmdebstrap \
  --mode=root \
  --variant=minbase \
  --architectures=amd64 \
  --include=ca-certificates,ubuntu-keyring \
  --aptopt='Acquire::Check-Valid-Until "false";' \
  resolute "${ROOTFS}" "${SOURCES}"

sudo mkdir -p "${ROOTFS}/opt/supralinux-ksq1-repo" "${ROOTFS}/etc/apt/sources.list.d"
sudo cp -a "${EVIDENCE}/repo/." "${ROOTFS}/opt/supralinux-ksq1-repo/"
cat > "${EVIDENCE}/supralinux-ksq1-local.list" <<'EOF_LOCAL'
deb [trusted=yes] file:/opt/supralinux-ksq1-repo ./
EOF_LOCAL
sudo cp "${EVIDENCE}/supralinux-ksq1-local.list" \
  "${ROOTFS}/etc/apt/sources.list.d/supralinux-ksq1-local.list"
printf '#!/bin/sh\nexit 101\n' | sudo tee "${ROOTFS}/usr/sbin/policy-rc.d" >/dev/null
sudo chmod 0755 "${ROOTFS}/usr/sbin/policy-rc.d"

if sudo grep -RqsE '(^|[/:])(archive\.ubuntu\.com|security\.ubuntu\.com)([/:]|$)|[[:space:]]stonking([[:space:]]|$)' \
  "${ROOTFS}/etc/apt"; then
  sudo grep -RnsE 'archive\.ubuntu\.com|security\.ubuntu\.com|[[:space:]]stonking([[:space:]]|$)' \
    "${ROOTFS}/etc/apt" >&2 || true
  fail "uncontrolled repository leaked into KWallet install rootfs"
fi
sudo grep -RqsF "https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/" "${ROOTFS}/etc/apt" \
  || fail "pinned snapshot absent from KWallet install rootfs"

sudo chroot "${ROOTFS}" apt-get update
sudo chroot "${ROOTFS}" apt-cache policy \
  libpam-kwallet5 libpam-kwallet-common kwallet6 | tee "${EVIDENCE}/apt-policy.txt"
sudo chroot "${ROOTFS}" env DEBIAN_FRONTEND=noninteractive \
  apt-get install -y --no-install-recommends "libpam-kwallet5=${PAM_VERSION}" \
  | tee "${EVIDENCE}/apt-install.txt"
sudo chroot "${ROOTFS}" apt-get check
bash "${ROOT}/scripts/ci/validate-kwallet-pam-installation.sh" "${ROOTFS}" \
  | tee "${EVIDENCE}/pam-registration.txt"

sudo chroot "${ROOTFS}" dpkg-query -W -f='${Package}\t${Version}\n' \
  libpam-kwallet-common libpam-kwallet5 kwallet6 \
  | sort | tee "${EVIDENCE}/installed-versions.tsv"

installed_pam_version="$(sudo chroot "${ROOTFS}" dpkg-query -W -f='${Version}' libpam-kwallet5)"
[[ "${installed_pam_version}" == "${PAM_VERSION}" ]] || {
  fail "installed libpam-kwallet5 ${installed_pam_version} != built ${PAM_VERSION}"
}
installed_common_version="$(sudo chroot "${ROOTFS}" dpkg-query -W -f='${Version}' libpam-kwallet-common)"
[[ "${installed_common_version}" == "${COMMON_VERSION}" ]] || {
  fail "installed libpam-kwallet-common ${installed_common_version} != built ${COMMON_VERSION}"
}

for pam_file in common-auth common-session; do
  sudo grep -nE 'pam_kwallet5\.so' "${ROOTFS}/etc/pam.d/${pam_file}" \
    > "${EVIDENCE}/${pam_file}-kwallet.txt"
done

{
  echo "AURORA_KSQ_1_KWALLET_SOURCE=4:6.7.4-0ubuntu3"
  echo "AURORA_KSQ_1_KWALLET_VERSION=${PAM_VERSION}"
  echo "AURORA_KSQ_1_KWALLET_COMPAT=13"
  echo "AURORA_KSQ_1_KWALLET_SUBSTVARS_RESTORED=misc+qml6+shlibs"
  echo "AURORA_KSQ_1_KWALLET_BINARY_RUNTIME_DEPS=PASS"
  echo "AURORA_KSQ_1_KWALLET_PAM_INSTALLATION=PASS"
  echo "AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED=no"
} > "${EVIDENCE}/status.env"

rm -rf "${EVIDENCE}/repo"
cat "${EVIDENCE}/status.env"
echo "AURORA_KSQ_1_KWALLET_SUCCESS"
