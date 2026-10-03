#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${1:-${SUPRALINUX_FRAMEWORKS_MILESTONE_IMAGE:-/var/lib/supralinux/images/milestones/frameworks-6.30-pass.qcow2}}"
PROVENANCE="${IMAGE}.provenance.txt"

[[ -f "${IMAGE}" ]] || { printf 'Missing Frameworks milestone image: %s\n' "${IMAGE}" >&2; exit 1; }
[[ -f "${PROVENANCE}" ]] || { printf 'Missing Frameworks milestone provenance: %s\n' "${PROVENANCE}" >&2; exit 1; }

get_value() {
    awk -F= -v key="$1" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "${PROVENANCE}"
}

[[ "$(get_value kind)" == "frameworks-milestone-execution-cache" ]]
[[ "$(get_value cache_only)" == "yes" ]]
[[ "$(get_value canonical_source_of_truth)" == "no" ]]
[[ "$(get_value frameworks_series)" == "6.30.0" ]]
[[ "$(get_value pass_nodes)" == "65" ]]
[[ "$(get_value framework_packages_preinstalled_in_sbuild_rootfs)" == "no" ]]
[[ "$(get_value source_golden_sha256)" == "a0b88447d9a9ecd9785087390cf499abaf9416291864fe1be4d63d9a334b2acd" ]]

EXPECTED="$(get_value milestone_image_sha256)"
ACTUAL="$(sha256sum "${IMAGE}" | awk '{print $1}')"
if [[ ! "${EXPECTED}" =~ ^[0-9a-f]{64}$ || "${EXPECTED}" != "${ACTUAL}" ]]; then
    printf 'Frameworks milestone image SHA mismatch. expected=%s actual=%s\n' "${EXPECTED:-missing}" "${ACTUAL}" >&2
    exit 1
fi

CURRENT_PLAN="$(mktemp)"
trap 'rm -f "${CURRENT_PLAN}"' EXIT
python3 "${ROOT}/scripts/plan-frameworks-milestone.py" > "${CURRENT_PLAN}"
CURRENT_PLAN_SHA="$(sha256sum "${CURRENT_PLAN}" | awk '{print $1}')"
if [[ "$(get_value artifact_plan_sha256)" != "${CURRENT_PLAN_SHA}" ]]; then
    printf 'Frameworks milestone artifact plan is stale for the current canonical Frameworks state.\n' >&2
    exit 1
fi

qemu-img check "${IMAGE}" >/dev/null
printf 'Frameworks milestone execution cache: PASS\n'
printf 'image=%s\nsha256=%s\nartifact_plan_sha256=%s\n' "${IMAGE}" "${ACTUAL}" "${CURRENT_PLAN_SHA}"
