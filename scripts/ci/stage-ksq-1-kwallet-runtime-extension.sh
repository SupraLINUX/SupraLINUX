#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POINTER="${ROOT}/scripts/ci/aurora-ksq-kwallet-runtime-extension.env"
EXTENSION_ROOT="${1:-}"
SOLVER="${2:-}"
CLOSURE="${3:-}"
EVIDENCE="${4:-}"

fail() { echo "AURORA_KSQ_1_KWALLET_RUNTIME_STAGE_FAILURE: $*" >&2; exit 1; }

[[ -n "${EXTENSION_ROOT}" && -d "${EXTENSION_ROOT}" ]] || fail "validated extension root missing"
[[ -d "${SOLVER}/archives" ]] || fail "solver archives directory missing"
[[ -d "${CLOSURE}" ]] || fail "local closure directory missing"
[[ -d "${EVIDENCE}" ]] || fail "evidence directory missing"
[[ -f "${POINTER}" ]] || fail "canonical runtime extension pointer missing"

set -a
# shellcheck disable=SC1090
. "${POINTER}"
set +a

[[ "${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STATUS}" == INDEPENDENTLY_VALIDATED ]] || fail "runtime extension not independently validated"
[[ "${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID}" == 20260829T022000Z-kwallet-runtime-r1 ]] || fail "unexpected runtime extension identity"
[[ "${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT}" == 20260829T022000Z ]] || fail "runtime extension snapshot mismatch"
[[ "${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES}" == 3 ]] || fail "unexpected runtime extension package count"
[[ "${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES_LIST}" == lsb-base,libwrap0,socat ]] || fail "unexpected runtime extension package set"

grep -qx "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID=${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID}" "${EXTENSION_ROOT}/provenance.env" || fail "extracted extension identity mismatch"
grep -qx "AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT=${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT}" "${EXTENSION_ROOT}/provenance.env" || fail "extracted extension snapshot mismatch"
python3 "${ROOT}/scripts/ci/ksq-kwallet-runtime-extension.py" validate --root "${EXTENSION_ROOT}" \
  | tee "${EVIDENCE}/runtime-extension-validation.log"

declare -A EXPECTED_VERSION=(
  [lsb-base]='11.6build1'
  [libwrap0]='7.6.q-36build2'
  [socat]='1.8.1.1-1ubuntu0.1'
)
declare -A EXPECTED_ARCH=(
  [lsb-base]='all'
  [libwrap0]='amd64'
  [socat]='amd64'
)

declare -A FOUND=()
printf 'package\tversion\tarchitecture\tfilename\tsolver_cache\tmmdebstrap_local_include\n' > "${EVIDENCE}/runtime-extension-staging.tsv"
while IFS= read -r -d '' deb; do
  package="$(dpkg-deb -f "${deb}" Package)"
  version="$(dpkg-deb -f "${deb}" Version)"
  arch="$(dpkg-deb -f "${deb}" Architecture)"
  [[ -n "${EXPECTED_VERSION[${package}]:-}" ]] || fail "unexpected extension package ${package}"
  [[ -z "${FOUND[${package}]:-}" ]] || fail "duplicate extension package ${package}"
  [[ "${version}" == "${EXPECTED_VERSION[${package}]}" ]] || fail "extension version mismatch for ${package}: ${version}"
  [[ "${arch}" == "${EXPECTED_ARCH[${package}]}" ]] || fail "extension architecture mismatch for ${package}: ${arch}"
  basename="$(basename "${deb}")"
  solver_target="${SOLVER}/archives/${basename}"
  closure_target="${CLOSURE}/${basename}"
  [[ ! -e "${solver_target}" && ! -e "${closure_target}" ]] || fail "runtime extension target already exists: ${basename}"
  install -m 0644 "${deb}" "${solver_target}"
  install -m 0644 "${deb}" "${closure_target}"
  FOUND["${package}"]=1
  printf '%s\t%s\t%s\t%s\tyes\tyes\n' "${package}" "${version}" "${arch}" "${basename}" \
    >> "${EVIDENCE}/runtime-extension-staging.tsv"
done < <(find "${EXTENSION_ROOT}/packages" -maxdepth 1 -type f -name '*.deb' -print0 | sort -z)

[[ "${#FOUND[@]}" -eq 3 ]] || fail "expected exactly three staged runtime extension packages"
for package in lsb-base libwrap0 socat; do
  [[ "${FOUND[${package}]:-}" == 1 ]] || fail "runtime extension package not staged: ${package}"
done

(
  cd "${EXTENSION_ROOT}"
  sha256sum -c packages.sha256
) | tee "${EVIDENCE}/runtime-extension-packages-sha256-check.txt"
sha256sum "${POINTER}" > "${EVIDENCE}/runtime-extension-pointer.sha256"
cp "${POINTER}" "${EVIDENCE}/runtime-extension-pointer.env"
cp "${EXTENSION_ROOT}/provenance.env" "${EXTENSION_ROOT}/gap-status.env" \
   "${EXTENSION_ROOT}/runtime-gap.tsv" "${EXTENSION_ROOT}/packages.sha256" \
   "${EXTENSION_ROOT}/snapshot-metadata.sha256" "${EVIDENCE}/"

cat > "${EVIDENCE}/runtime-extension-stage-status.env" <<EOF
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STAGE=PASS
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STATUS=${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STATUS}
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID=${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_ID}
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT=${AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_UBUNTU_SNAPSHOT}
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_PACKAGES=3
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_SOLVER_CACHE=preseeded-local-debs
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_MMDEBSTRAP_INPUT=individual-local-debs
AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_NETWORK_USED=0
EOF

echo AURORA_KSQ_1_KWALLET_RUNTIME_EXTENSION_STAGE_SUCCESS
