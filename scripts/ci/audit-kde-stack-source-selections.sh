#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/build/ksq-0/source-audit"
APT_ROOT="${ROOT}/build/ksq-0/apt"
DOWNLOADS="${OUT}/downloads"
UNPACK="${OUT}/unpack"

. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: runner is not Resolute" >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == "amd64" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: runner is not amd64" >&2; exit 1; }
command -v dpkg-source >/dev/null || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: dpkg-source unavailable" >&2; exit 1; }
command -v curl >/dev/null || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: curl unavailable" >&2; exit 1; }

rm -rf "${OUT}"
mkdir -p "${DOWNLOADS}" "${UNPACK}"
chmod 0755 "${OUT}" "${DOWNLOADS}" "${UNPACK}"

apt_opts=(
  -o "Dir::Etc::sourcelist=${APT_ROOT}/stonking.sources"
  -o "Dir::Etc::sourceparts=-"
  -o "Dir::State::lists=${APT_ROOT}/stonking-lists"
  -o "Dir::State::status=${APT_ROOT}/empty-status"
  -o "Dir::Cache=${APT_ROOT}/stonking-cache"
  -o "APT::Architecture=amd64"
  -o "APT::Architectures=amd64"
  -o "Acquire::Languages=none"
)

(
  cd "${DOWNLOADS}"
  apt-get "${apt_opts[@]}" source --download-only \
    'plasma-wayland-protocols=1.21.0-1' \
    'qtkeychain=0.17.0-1' \
    'kwallet-pam=4:6.7.4-0ubuntu3'
)

for required in \
  plasma-wayland-protocols_1.21.0-1.dsc \
  qtkeychain_0.17.0-1.dsc \
  kwallet-pam_6.7.4-0ubuntu3.dsc; do
  [[ -f "${DOWNLOADS}/${required}" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: missing ${required}" >&2; exit 1; }
done

grep -Fq 'Build-Depends:' "${DOWNLOADS}/plasma-wayland-protocols_1.21.0-1.dsc"
grep -Fq 'debhelper-compat (= 13)' "${DOWNLOADS}/plasma-wayland-protocols_1.21.0-1.dsc"
grep -Fq 'Build-Depends:' "${DOWNLOADS}/qtkeychain_0.17.0-1.dsc"
grep -Fq 'debhelper-compat (= 13)' "${DOWNLOADS}/qtkeychain_0.17.0-1.dsc"
grep -Fq 'debhelper-compat (= 14)' "${DOWNLOADS}/kwallet-pam_6.7.4-0ubuntu3.dsc"

# Debian Snapshot serves immutable files directly by their SHA-1 identity.
# SHA-1 values and SHA-256 values below come from the accepted source uploads;
# the second digest check protects content identity independently of transport.
DEBIAN_SNAPSHOT_FILE='https://snapshot.debian.org/file'
curl --fail --location --silent --show-error \
  "${DEBIAN_SNAPSHOT_FILE}/6be63f02c5dbf851a22cef09c3f2b33074bd78d2" \
  -o "${DOWNLOADS}/wayland-protocols_1.48-1.dsc"
curl --fail --location --silent --show-error \
  "${DEBIAN_SNAPSHOT_FILE}/61a9d1f8454fa612a70f3a35b3a5f99471cba4ba" \
  -o "${DOWNLOADS}/wayland-protocols_1.48.orig.tar.xz"
curl --fail --location --silent --show-error \
  "${DEBIAN_SNAPSHOT_FILE}/3f1d50a88477db8193debab281be9ca0b64d0dce" \
  -o "${DOWNLOADS}/wayland-protocols_1.48.orig.tar.xz.asc"
curl --fail --location --silent --show-error \
  "${DEBIAN_SNAPSHOT_FILE}/7eebc38bb402028be3de4e3d815037e3b601d25d" \
  -o "${DOWNLOADS}/wayland-protocols_1.48-1.debian.tar.xz"

cat > "${OUT}/wayland-protocols-1.48.sha256" <<'EOF_HASHES'
f0b19a01b59a7501baef8360af45153d340997fa36e44ba322ff3d20b9ec253a  wayland-protocols_1.48-1.dsc
398036ac0eb6484982ddbde7ff86848d753231f9cdeeae983f06b52946625aa1  wayland-protocols_1.48.orig.tar.xz
421104518b8d370888d6a2f36c46281c1c9bc1203b69a12eeafe06ca38be4808  wayland-protocols_1.48.orig.tar.xz.asc
d4dc3f6dd27526cb0993908707961511d80e952e1bf5c6635d3ba8c58f7faeac  wayland-protocols_1.48-1.debian.tar.xz
EOF_HASHES
(
  cd "${DOWNLOADS}"
  sha256sum -c "${OUT}/wayland-protocols-1.48.sha256"
)
grep -Fq 'libwayland-dev (>= 1.23.0)' "${DOWNLOADS}/wayland-protocols_1.48-1.dsc"
grep -Fq 'debhelper-compat (= 13)' "${DOWNLOADS}/wayland-protocols_1.48-1.dsc"

curl --fail --location --silent --show-error \
  "${DEBIAN_SNAPSHOT_FILE}/d55713ce26a9b25d69f6604cf9e4accf63464ce8" \
  -o "${DOWNLOADS}/kwallet-pam_6.7.4-3.debian.tar.xz"
printf '%s  %s\n' \
  '3a639fd37e4b4d65e66dc6121b4d5313c09e9345dcfb0fa9859d4db8154c380f' \
  'kwallet-pam_6.7.4-3.debian.tar.xz' > "${OUT}/kwallet-pam-debian-6.7.4-3.sha256"
(
  cd "${DOWNLOADS}"
  sha256sum -c "${OUT}/kwallet-pam-debian-6.7.4-3.sha256"
)

rm -rf "${UNPACK}/kwallet-ubuntu" "${UNPACK}/kwallet-debian-reference"
mkdir -p "${UNPACK}/kwallet-debian-reference"
dpkg-source -x "${DOWNLOADS}/kwallet-pam_6.7.4-0ubuntu3.dsc" "${UNPACK}/kwallet-ubuntu" >/dev/null
tar -xJf "${DOWNLOADS}/kwallet-pam_6.7.4-3.debian.tar.xz" -C "${UNPACK}/kwallet-debian-reference"

KW_UBUNTU="${UNPACK}/kwallet-ubuntu/debian"
KW_DEBIAN="${UNPACK}/kwallet-debian-reference/debian"
[[ -d "${KW_UBUNTU}" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: Ubuntu kwallet debian directory missing" >&2; exit 1; }
[[ -d "${KW_DEBIAN}" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: Debian kwallet reference directory missing" >&2; exit 1; }

grep -Eq 'libpam-runtime' "${KW_UBUNTU}/control" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks libpam-runtime dependency" >&2; exit 1; }
grep -Rqs 'pam-auth-update' "${KW_UBUNTU}" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks pam-auth-update integration" >&2; exit 1; }
grep -Rqs 'pam-auth-update' "${KW_UBUNTU}"/*postinst || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet postinst lacks pam-auth-update" >&2; exit 1; }
grep -Rqs 'pam-auth-update' "${KW_UBUNTU}"/*prerm || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet prerm lacks pam-auth-update" >&2; exit 1; }
grep -Rqs 'Password' "${KW_UBUNTU}" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks PAM Password stanza/profile" >&2; exit 1; }
grep -Rqs 'pam-configs' "${KW_UBUNTU}" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks pam-configs installation" >&2; exit 1; }

# Ubuntu 0ubuntu3 claims to sync the Debian 6.7.4-3 PAM integration.  Require
# the functional packaging files to be byte-identical so our compat-level
# adaptation cannot silently regress auto-unlock or PAM registration.
for file in \
  libpam-kwallet-common.install \
  libpam-kwallet-common.postinst \
  libpam-kwallet-common.prerm \
  pam-configs/kde-kwallet; do
  cmp -s "${KW_UBUNTU}/${file}" "${KW_DEBIAN}/${file}" || {
    echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet PAM file diverges from Debian 6.7.4-3: ${file}" >&2
    diff -u "${KW_DEBIAN}/${file}" "${KW_UBUNTU}/${file}" || true
    exit 1
  }
done

DEBIAN_TEST="${KW_DEBIAN}/tests/control"
[[ -f "${DEBIAN_TEST}" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: Debian kwallet PAM autopkgtest missing" >&2; exit 1; }
grep -Fq 'grep pam_kwallet5\.so /etc/pam.d/common-session && grep pam_kwallet5\.so /etc/pam.d/common-auth' "${DEBIAN_TEST}" || {
  echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: Debian kwallet PAM autopkgtest contract changed" >&2
  exit 1
}

{
  echo 'AURORA_KSQ_0_KWALLET_SOURCE=4:6.7.4-0ubuntu3'
  echo 'AURORA_KSQ_0_KWALLET_PAM_AUTH_UPDATE=present'
  echo 'AURORA_KSQ_0_KWALLET_LIBPAM_RUNTIME=present'
  echo 'AURORA_KSQ_0_KWALLET_PASSWORD_PROFILE=present'
  echo 'AURORA_KSQ_0_KWALLET_PAM_FILES_MATCH_DEBIAN_6_7_4_3=yes'
  echo 'AURORA_KSQ_0_KWALLET_INSTALL_TEST_CONTRACT=common-session+common-auth'
  echo '--- Ubuntu 0ubuntu3 PAM-related files ---'
  find "${KW_UBUNTU}" -maxdepth 2 -type f -print | sort | while read -r file; do
    if grep -qsE 'pam-auth-update|pam-configs|Password' "$file"; then
      echo "### ${file#${UNPACK}/kwallet-ubuntu/}"
      cat "$file"
      echo
    fi
  done
  echo '--- Debian 6.7.4-3 PAM-related reference files ---'
  find "${KW_DEBIAN}" -maxdepth 2 -type f -print | sort | while read -r file; do
    if grep -qsE 'pam-auth-update|pam-configs|Password' "$file"; then
      echo "### ${file#${UNPACK}/kwallet-debian-reference/}"
      cat "$file"
      echo
    fi
  done
} > "${OUT}/kwallet-pam-integration-audit.txt"

find "${DOWNLOADS}" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > "${OUT}/selected-source-files.sha256"

printf 'AURORA_KSQ_0_SOURCE_AUDIT_PLASMA_WAYLAND_PROTOCOLS=1.21.0-1\n'
printf 'AURORA_KSQ_0_SOURCE_AUDIT_QTKEYCHAIN=0.17.0-1\n'
printf 'AURORA_KSQ_0_SOURCE_AUDIT_WAYLAND_PROTOCOLS=1.48-1\n'
printf 'AURORA_KSQ_0_SOURCE_AUDIT_KWALLET_PAM=4:6.7.4-0ubuntu3\n'
printf 'AURORA_KSQ_0_SOURCE_AUDIT_SUCCESS\n'
