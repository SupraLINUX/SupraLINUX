#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
INVENTORY_DIR="${BUILD_DIR}/c4-0-inventory"
IMAGE="${BUILD_DIR}/aurora-c4-0-rootfs.img"
MOUNT_DIR="${BUILD_DIR}/aurora-c4-0-reconcile-rootfs"
MATRIX="${ROOT_DIR}/docs/PLASMA_INTEGRATION_MATRIX.md"

KCM_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-kcm-coverage.tsv"
DEPENDENCY_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-dependency-coverage.tsv"
PORTAL_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-portal-coverage.tsv"
KWIN_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-kwin-coverage.tsv"
INTEGRATION_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-integration-coverage.tsv"
RECOMMENDS_MANIFEST="${ROOT_DIR}/tests/c4/c4.0-plasma-recommends-coverage.tsv"

for file in \
  "${MATRIX}" \
  "${KCM_MANIFEST}" \
  "${DEPENDENCY_MANIFEST}" \
  "${PORTAL_MANIFEST}" \
  "${KWIN_MANIFEST}" \
  "${INTEGRATION_MANIFEST}" \
  "${RECOMMENDS_MANIFEST}"; do
  [[ -s "${file}" ]] || {
    echo "AURORA_C4_0_RECONCILE_FAILURE=missing-contract:${file}" >&2
    exit 1
  }
done

[[ -d "${INVENTORY_DIR}" ]] || {
  echo "AURORA_C4_0_RECONCILE_FAILURE=inventory-missing" >&2
  exit 1
}
[[ -f "${IMAGE}" ]] || {
  echo "AURORA_C4_0_RECONCILE_FAILURE=image-missing" >&2
  exit 1
}

mkdir -p "${MOUNT_DIR}"

cleanup() {
  set +e
  if mountpoint -q "${MOUNT_DIR}"; then
    sudo umount "${MOUNT_DIR}" >/dev/null 2>&1 || sudo umount -l "${MOUNT_DIR}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

fail=0

compare_simple_lists() {
  local label="$1"
  local actual="$2"
  local expected="$3"
  local unknown="${INVENTORY_DIR}/unknown-${label}.txt"
  local missing="${INVENTORY_DIR}/missing-${label}.txt"

  comm -23 "${actual}" "${expected}" >"${unknown}"
  comm -13 "${actual}" "${expected}" >"${missing}"

  if [[ -s "${unknown}" || -s "${missing}" ]]; then
    echo "AURORA_C4_0_RECONCILE_MISMATCH=${label}"
    fail=1
  else
    echo "AURORA_C4_0_RECONCILE_MATCH=${label}"
  fi
}

echo "AURORA_C4_0_RECONCILE_STAGE=OWNERSHIP"
for file in \
  unresolved-kcm-owners.txt \
  unresolved-portal-owners.txt \
  unresolved-kwin-surface-owners.txt \
  unresolved-plasma-applet-plugin-owners.txt \
  unresolved-plasma-surface-owners.txt \
  unresolved-kded-plugin-owners.txt \
  unresolved-kio-surface-owners.txt; do
  [[ -f "${INVENTORY_DIR}/${file}" ]] || {
    echo "AURORA_C4_0_RECONCILE_FAILURE=missing-owner-inventory:${file}"
    fail=1
    continue
  }
  if [[ -s "${INVENTORY_DIR}/${file}" ]]; then
    echo "AURORA_C4_0_RECONCILE_UNRESOLVED=${file}"
    fail=1
  fi
done

echo "AURORA_C4_0_RECONCILE_STAGE=KWIN"
awk -F '\t' 'NR>1 && NF>=2 {print $1 "\t" $2}' "${INVENTORY_DIR}/kwin-surface-files.tsv" \
  | sort -u >"${INVENTORY_DIR}/actual-kwin-surfaces.txt"
awk -F '\t' '!/^#/ && NF>=2 {print $1 "\t" $2}' "${KWIN_MANIFEST}" \
  | sort -u >"${INVENTORY_DIR}/expected-kwin-surfaces.txt"
compare_simple_lists kwin-surfaces \
  "${INVENTORY_DIR}/actual-kwin-surfaces.txt" \
  "${INVENTORY_DIR}/expected-kwin-surfaces.txt"

echo "AURORA_C4_0_RECONCILE_STAGE=INTEGRATIONS"
{
  for file in \
    plasma-applet-plugin-surfaces.tsv \
    plasma-plasmoid-surfaces.tsv \
    kded-plugin-surfaces.tsv \
    kio-plugin-surfaces.tsv \
    kio-service-menu-surfaces.tsv; do
    awk -F '\t' 'NR>1 && NF>=2 {print $1 "\t" $2}' "${INVENTORY_DIR}/${file}"
  done
} | sort -u >"${INVENTORY_DIR}/actual-integration-surfaces.txt"
awk -F '\t' '!/^#/ && NF>=2 {print $1 "\t" $2}' "${INTEGRATION_MANIFEST}" \
  | sort -u >"${INVENTORY_DIR}/expected-integration-surfaces.txt"
compare_simple_lists integration-surfaces \
  "${INVENTORY_DIR}/actual-integration-surfaces.txt" \
  "${INVENTORY_DIR}/expected-integration-surfaces.txt"

echo "AURORA_C4_0_RECONCILE_STAGE=PLASMA_RECOMMENDS"
sudo mount -o loop,ro "${IMAGE}" "${MOUNT_DIR}"
DPKG_ADMINDIR="${MOUNT_DIR}/var/lib/dpkg"
[[ -r "${DPKG_ADMINDIR}/status" ]] || {
  echo "AURORA_C4_0_RECONCILE_FAILURE=dpkg-status-missing"
  exit 1
}

dpkg-query --admindir="${DPKG_ADMINDIR}" -W -f='${Recommends}\n' plasma-desktop \
  | tr ',' '\n' \
  | sed -E 's/[[:space:]]*\([^)]*\)//g; s/[[:space:]]*\|.*$//; s/:any$//; s/^[[:space:]]+//; s/[[:space:]]+$//' \
  | grep -Ev '^$' \
  | sort -u >"${INVENTORY_DIR}/actual-plasma-recommends.txt"
awk -F '\t' '!/^#/ && NF {print $1}' "${RECOMMENDS_MANIFEST}" \
  | sort -u >"${INVENTORY_DIR}/expected-plasma-recommends.txt"
compare_simple_lists plasma-recommends \
  "${INVENTORY_DIR}/actual-plasma-recommends.txt" \
  "${INVENTORY_DIR}/expected-plasma-recommends.txt"

: >"${INVENTORY_DIR}/plasma-recommend-versions.tsv"
while IFS=$'\t' read -r package capability classification; do
  [[ -n "${package}" && "${package}" != \#* ]] || continue
  version="$(dpkg-query --admindir="${DPKG_ADMINDIR}" -W -f='${Version}' "${package}" 2>/dev/null || true)"
  status="$(dpkg-query --admindir="${DPKG_ADMINDIR}" -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "${package}" "${version:-MISSING}" "${status:-MISSING}" "${capability}" "${classification}" \
    >>"${INVENTORY_DIR}/plasma-recommend-versions.tsv"
done <"${RECOMMENDS_MANIFEST}"

sudo umount "${MOUNT_DIR}"

echo "AURORA_C4_0_RECONCILE_STAGE=MATRIX_IDS"
grep -oE 'AUR-[A-Z0-9-]+' "${MATRIX}" | sort -u >"${INVENTORY_DIR}/matrix-capability-ids.txt"
{
  grep -hEv '^[[:space:]]*(#|$)' \
    "${KCM_MANIFEST}" \
    "${DEPENDENCY_MANIFEST}" \
    "${PORTAL_MANIFEST}" \
    "${KWIN_MANIFEST}" \
    "${INTEGRATION_MANIFEST}" \
    "${RECOMMENDS_MANIFEST}" \
    | grep -oE 'AUR-[A-Z0-9-]+' || true
} | sort -u >"${INVENTORY_DIR}/manifest-capability-ids.txt"

comm -23 \
  "${INVENTORY_DIR}/manifest-capability-ids.txt" \
  "${INVENTORY_DIR}/matrix-capability-ids.txt" \
  >"${INVENTORY_DIR}/manifest-capability-ids-missing-from-matrix.txt"
if [[ -s "${INVENTORY_DIR}/manifest-capability-ids-missing-from-matrix.txt" ]]; then
  echo "AURORA_C4_0_RECONCILE_MISMATCH=MATRIX_IDS"
  fail=1
fi

if [[ "${fail}" -ne 0 ]]; then
  echo "AURORA_C4_0_RECONCILE_FAILURE=surface-contract-mismatch"
  exit 1
fi

echo "AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-002"
echo "AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-003"
echo "AURORA_C4_0_HOST_CAPABILITY_PASS=AUR-COVER-006"
echo "AURORA_C4_0_RECONCILE_SUCCESS"
