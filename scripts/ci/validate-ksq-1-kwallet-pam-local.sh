#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE="${ROOT}/build/ksq-1/full"
DEBS="${STATE}/debs"
EVIDENCE="${STATE}/kwallet-pam-validation"
SNAPSHOT="20260829T022000Z"
SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${SNAPSHOT}}"
SOURCES="${ROOT}/build/ksq-0/apt/resolute.sources"
PREPARED_CONTROL="${STATE}/chunk-061-080/evidence/65-kwallet-pam/debian-control"
ROOTFS="${STATE}/kwallet-pam-test-rootfs"

fail() {
  echo "AURORA_KSQ_1_KWALLET_LOCAL_FAILURE: $*" >&2
  exit 1
}

[[ "$(id -u)" -eq 0 ]] || fail "must run as root inside the scoped builder"
grep -Eq '^supralinux-ksq-unshare( \(enforce\))?$' /proc/self/attr/current \
  || fail "scoped AppArmor profile is not enforcing"
cap_eff="$(awk '/^CapEff:/ {print $2}' /proc/self/status)"
cap_eff_val=$((16#${cap_eff}))
(( (cap_eff_val & (1 << 21)) == 0 )) || fail "outer builder unexpectedly has CAP_SYS_ADMIN"
if find /sys/class/net -mindepth 1 -maxdepth 1 ! -name lo -print -quit 2>/dev/null | grep -q .; then
  fail "non-loopback network interface exists"
fi

for command in dpkg-deb mmdebstrap sha256sum su; do
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
COMMON_VERSION="$(dpkg-deb -f "${COMMON_DEB}" Version)"
PAM_VERSION="$(dpkg-deb -f "${PAM_DEB}" Version)"
[[ "${COMMON_VERSION}" == "${PAM_VERSION}" ]] || fail "PAM binary versions differ"
[[ "${PAM_VERSION}" == '4:6.7.4-0ubuntu3~supra26.04.1' ]] || fail "unexpected kwallet-pam version ${PAM_VERSION}"

# Preserve the source-level adaptation contract before installation.
grep -Fq 'debhelper-compat (= 13)' "${PREPARED_CONTROL}" || fail "prepared source is not compat 13"
! grep -Fq 'debhelper-compat (= 14)' "${PREPARED_CONTROL}" || fail "compat 14 leaked into prepared source"
! grep -Fq 'dh-sequence-plasma' "${PREPARED_CONTROL}" || fail "intentional Ubuntu no-dh-sequence-plasma delta was lost"
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
[[ "${PAM_DEPENDS}" != *'${'* && "${COMMON_DEPENDS}" != *'${'* ]] || fail "unexpanded substvar leaked into binary control"

rm -rf "${EVIDENCE}"
mkdir -p "${EVIDENCE}"
chmod a+rX "${COMMON_DEB}" "${PAM_DEB}"
cp -a "${PREPARED_CONTROL}" "${EVIDENCE}/prepared-debian-control"
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

# A directory created by mmdebstrap --mode=unshare has shifted ownership when
# viewed from the outer namespace. Use mmdebstrap's documented --unshare-helper
# whenever executing a command inside it, and remove it through the same mapping.
cleanup_rootfs() {
  if [[ -e "${ROOTFS}" ]]; then
    su -s /bin/bash ubuntu -c \
      "mmdebstrap --unshare-helper rm -rf '${ROOTFS}'" >/dev/null 2>&1 || true
  fi
}
trap cleanup_rootfs EXIT
cleanup_rootfs
mkdir -p "${ROOTFS}"
chown ubuntu:ubuntu "${ROOTFS}"
chmod 0755 "${ROOTFS}"

# mmdebstrap documents that --include accepts exact package=version expressions
# and local .deb paths, and that file-mirror-automount makes both file: mirrors
# and included .deb objects available in unshare mode. The two PAM packages are
# therefore installed exactly from the accumulated SupraLINUX build artifacts;
# all remaining runtime dependencies resolve only from the certified local slice.
set +e
su -s /bin/bash ubuntu -c \
  "DEBIAN_FRONTEND=noninteractive mmdebstrap \
    --mode=unshare \
    --variant=minbase \
    --architectures=amd64 \
    --include='${COMMON_DEB}' \
    --include='${PAM_DEB}' \
    --hook-dir=/usr/share/mmdebstrap/hooks/file-mirror-automount \
    --aptopt='Acquire::Check-Valid-Until \"false\";' \
    resolute '${ROOTFS}' '${SOURCES}'" \
  2>&1 | tee "${EVIDENCE}/mmdebstrap-install.log"
pipe_status=("${PIPESTATUS[@]}")
set -e
printf 'MMDEBSTRAP_RC=%s\nTEE_RC=%s\n' "${pipe_status[0]}" "${pipe_status[1]}" \
  > "${EVIDENCE}/mmdebstrap-command.env"
[[ "${pipe_status[0]}" -eq 0 ]] || fail "mmdebstrap install failed"
[[ "${pipe_status[1]}" -eq 0 ]] || fail "mmdebstrap evidence tee failed"

# URL-looking package metadata is not transport evidence. Evaluate only APT
# acquisition-status lines; the outer builder also has no non-loopback network.
if grep -E '^(Get|Hit|Ign|Err):[0-9]+ https?://' "${EVIDENCE}/mmdebstrap-install.log"; then
  fail "remote package transport occurred during KWallet installation"
fi

run_in_rootfs() {
  su -s /bin/bash ubuntu -c \
    "mmdebstrap --unshare-helper /usr/sbin/chroot '${ROOTFS}' $*"
}

run_in_rootfs 'apt-get check' | tee "${EVIDENCE}/apt-check.txt"
run_in_rootfs "dpkg-query -W -f='\${Package}\\t\${Version}\\n' libpam-kwallet-common libpam-kwallet5 kwallet6" \
  | sort | tee "${EVIDENCE}/installed-versions.tsv"

installed_pam_version="$(run_in_rootfs "dpkg-query -W -f='\${Version}' libpam-kwallet5")"
installed_common_version="$(run_in_rootfs "dpkg-query -W -f='\${Version}' libpam-kwallet-common")"
[[ "${installed_pam_version}" == "${PAM_VERSION}" ]] || fail "installed libpam-kwallet5 ${installed_pam_version} != built ${PAM_VERSION}"
[[ "${installed_common_version}" == "${COMMON_VERSION}" ]] || fail "installed libpam-kwallet-common ${installed_common_version} != built ${COMMON_VERSION}"

bash "${ROOT}/scripts/ci/validate-kwallet-pam-installation.sh" "${ROOTFS}" \
  | tee "${EVIDENCE}/pam-registration.txt"
for pam_file in common-auth common-session; do
  grep -nE 'pam_kwallet5\.so' "${ROOTFS}/etc/pam.d/${pam_file}" \
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
  echo "AURORA_KSQ_1_KWALLET_INSTALL_BACKEND=mmdebstrap-unshare-local-debs"
  echo "AURORA_KSQ_1_KWALLET_SNAPSHOT=${SNAPSHOT}"
  echo "AURORA_KSQ_1_KWALLET_REMOTE_FALLBACK=forbidden"
} > "${EVIDENCE}/status.env"

cat "${EVIDENCE}/status.env"
echo "AURORA_KSQ_1_KWALLET_LOCAL_SUCCESS"
