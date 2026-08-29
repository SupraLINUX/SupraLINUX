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

DEBIAN_WAYLAND_BASE='https://deb.debian.org/debian/pool/main/w/wayland-protocols'
for file in \
  wayland-protocols_1.48-1.dsc \
  wayland-protocols_1.48.orig.tar.xz \
  wayland-protocols_1.48.orig.tar.xz.asc \
  wayland-protocols_1.48-1.debian.tar.xz; do
  curl --fail --location --silent --show-error "${DEBIAN_WAYLAND_BASE}/${file}" -o "${DOWNLOADS}/${file}"
done
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

DEBIAN_KWALLET_BASE='https://deb.debian.org/debian/pool/main/k/kwallet-pam'
curl --fail --location --silent --show-error \
  "${DEBIAN_KWALLET_BASE}/kwallet-pam_6.7.4-3.debian.tar.xz" \
  -o "${DOWNLOADS}/kwallet-pam_6.7.4-3.debian.tar.xz"
printf '%s  %s\n' \
  '3a639fd37e4b4d65e66dc6121b4d5313c09e9345dcfb0fa9859d4db8154c380f' \
  'kwallet-pam_6.7.4-3.debian.tar.xz' > "${OUT}/kwallet-pam-debian-6.7.4-3.sha256"
(
  cd "${DOWNLOADS}"
  sha256sum -c "${OUT}/kwallet-pam-debian-6.7.4-3.sha256"
)

mkdir -p "${UNPACK}/kwallet-ubuntu" "${UNPACK}/kwallet-debian-reference"
dpkg-source -x "${DOWNLOADS}/kwallet-pam_6.7.4-0ubuntu3.dsc" "${UNPACK}/kwallet-ubuntu" >/dev/null
tar -xJf "${DOWNLOADS}/kwallet-pam_6.7.4-3.debian.tar.xz" -C "${UNPACK}/kwallet-debian-reference"

KW_DEBIAN="${UNPACK}/kwallet-ubuntu/debian"
[[ -d "${KW_DEBIAN}" ]] || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet debian directory missing" >&2; exit 1; }
grep -Eq 'libpam-runtime' "${KW_DEBIAN}/control" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks libpam-runtime dependency" >&2; exit 1; }
grep -Rqs 'pam-auth-update' "${KW_DEBIAN}" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks pam-auth-update integration" >&2; exit 1; }
grep -Rqs 'pam-auth-update' "${KW_DEBIAN}"/*postinst || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet postinst lacks pam-auth-update" >&2; exit 1; }
grep -Rqs 'pam-auth-update' "${KW_DEBIAN}"/*prerm || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet prerm lacks pam-auth-update" >&2; exit 1; }
grep -Rqs 'Password' "${KW_DEBIAN}" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks PAM Password stanza/profile" >&2; exit 1; }
grep -Rqs 'pam-configs' "${KW_DEBIAN}" || { echo "AURORA_KSQ_0_SOURCE_AUDIT_FAILURE: kwallet lacks pam-configs installation" >&2; exit 1; }

{
  echo 'AURORA_KSQ_0_KWALLET_SOURCE=4:6.7.4-0ubuntu3'
  echo 'AURORA_KSQ_0_KWALLET_PAM_AUTH_UPDATE=present'
  echo 'AURORA_KSQ_0_KWALLET_LIBPAM_RUNTIME=present'
  echo 'AURORA_KSQ_0_KWALLET_PASSWORD_PROFILE=present'
  echo '--- Ubuntu 0ubuntu3 PAM-related files ---'
  find "${KW_DEBIAN}" -maxdepth 2 -type f -print | sort | while read -r file; do
    if grep -qsE 'pam-auth-update|pam-configs|Password' "$file"; then
      echo "### ${file#${UNPACK}/kwallet-ubuntu/}"
      cat "$file"
      echo
    fi
  done
  echo '--- Debian 6.7.4-3 PAM-related reference files ---'
  find "${UNPACK}/kwallet-debian-reference/debian" -maxdepth 2 -type f -print | sort | while read -r file; do
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
