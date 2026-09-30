#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY="${SUPRALINUX_REPOSITORY:-SupraLINUX/SupraLINUX}"
PR_NUMBER="${SUPRALINUX_PR_NUMBER:-1}"
HOST_GITHUB_TOKEN="${SUPRALINUX_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"
RUNNER_GROUP_ID="${SUPRALINUX_RUNNER_GROUP_ID:-}"
API_VERSION="2026-03-10"
SOURCE_IMAGE="${SUPRALINUX_SOURCE_IMAGE:-/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img}"
GOLDEN_IMAGE="${SUPRALINUX_GOLDEN_IMAGE:-/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2}"
EVIDENCE_BASE="${SUPRALINUX_CERTIFICATION_EVIDENCE_ROOT:-/var/lib/supralinux/evidence/authoritative-certification}"
REBUILD_GOLDEN="${SUPRALINUX_REBUILD_GOLDEN:-0}"

STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CERT_DIR=""
PR_HEAD_SHA=""
GOLDEN_SHA256=""
GOLDEN_SOURCE_COMMIT=""
GOLDEN_INPUT_DIGEST=""

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

for command_name in awk curl env find git jq python3 sha256sum tee; do
    command -v "${command_name}" >/dev/null 2>&1 || die "Missing required command: ${command_name}"
done

[[ -n "${HOST_GITHUB_TOKEN}" ]] || die "SUPRALINUX_GITHUB_TOKEN (or GITHUB_TOKEN) is required."
[[ "${RUNNER_GROUP_ID}" =~ ^[0-9]+$ ]] || die "SUPRALINUX_RUNNER_GROUP_ID must be the numeric runner group ID."
[[ "${PR_NUMBER}" =~ ^[0-9]+$ ]] || die "SUPRALINUX_PR_NUMBER must be numeric."
[[ "${REPOSITORY}" == */* ]] || die "SUPRALINUX_REPOSITORY must use owner/repo form."
[[ "${REBUILD_GOLDEN}" == "0" || "${REBUILD_GOLDEN}" == "1" ]] || die "SUPRALINUX_REBUILD_GOLDEN must be 0 or 1."

api_get() {
    local path="$1"
    curl \
        --fail-with-body \
        --silent \
        --show-error \
        --location \
        --header 'Accept: application/vnd.github+json' \
        --header "Authorization: Bearer ${HOST_GITHUB_TOKEN}" \
        --header "X-GitHub-Api-Version: ${API_VERSION}" \
        "https://api.github.com${path}"
}

STAGE="resolve-pr-head"
PR_JSON="$(api_get "/repos/${REPOSITORY}/pulls/${PR_NUMBER}")"
[[ "$(jq -r '.state' <<<"${PR_JSON}")" == "open" ]] || die "PR #${PR_NUMBER} is not open."
[[ "$(jq -r '.head.repo.full_name // empty' <<<"${PR_JSON}")" == "${REPOSITORY}" ]] || die "Authoritative certification refuses fork PRs."
PR_HEAD_SHA="$(jq -r '.head.sha // empty' <<<"${PR_JSON}")"
[[ "${PR_HEAD_SHA}" =~ ^[0-9a-fA-F]{40}$ ]] || die "Could not resolve a valid PR head SHA."

LOCAL_HEAD="$(git -C "${ROOT}" rev-parse HEAD)"
[[ "${LOCAL_HEAD,,}" == "${PR_HEAD_SHA,,}" ]] || {
    printf 'Local checkout does not match the PR head.\n' >&2
    printf 'Local HEAD: %s\n' "${LOCAL_HEAD}" >&2
    printf 'PR head:    %s\n' "${PR_HEAD_SHA}" >&2
    printf 'Update the host checkout to the exact PR head before certifying.\n' >&2
    exit 1
}
if [[ -n "$(git -C "${ROOT}" status --porcelain --untracked-files=normal)" ]]; then
    die "Host checkout is not clean; authoritative certification requires an exact clean PR checkout."
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${PR_HEAD_SHA:0:12}-$$"
CERT_DIR="${EVIDENCE_BASE}/${RUN_ID}"
mkdir -p "${CERT_DIR}"
chmod 0700 "${CERT_DIR}"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [[ -n "${CERT_DIR}" ]]; then
        python3 - "${CERT_DIR}/certification-result.json" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" "${REPOSITORY}" "${PR_NUMBER}" "${PR_HEAD_SHA}" "${GOLDEN_SHA256}" "${GOLDEN_SOURCE_COMMIT}" "${GOLDEN_INPUT_DIGEST}" <<'PY'
import json
import sys
from pathlib import Path

path,state,rc,stage,started,finished,repository,pr_number,head,golden,golden_source,golden_inputs=sys.argv[1:]
payload={
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "repository": repository,
    "pr_number": int(pr_number),
    "pr_head_sha": head,
    "golden_image_sha256": golden or None,
    "golden_source_commit": golden_source or None,
    "golden_input_digest": golden_inputs or None,
    "canonical_state_effect": "none",
    "stable_publication_authorized": False,
}
Path(path).write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
PY
    fi
}
trap write_result EXIT

{
    printf 'started_at=%s\n' "${STARTED_AT}"
    printf 'repository=%s\n' "${REPOSITORY}"
    printf 'pr_number=%s\n' "${PR_NUMBER}"
    printf 'pr_head_sha=%s\n' "${PR_HEAD_SHA}"
    printf 'local_head=%s\n' "${LOCAL_HEAD}"
    printf 'source_image=%s\n' "${SOURCE_IMAGE}"
    printf 'golden_image=%s\n' "${GOLDEN_IMAGE}"
    printf 'rebuild_golden=%s\n' "${REBUILD_GOLDEN}"
    printf 'current_golden_input_digest=%s\n' "$("${ROOT}/scripts/golden-image-input-digest.sh" "${PR_HEAD_SHA}")"
} > "${CERT_DIR}/certification-inputs.txt"

STAGE="host-kvm-preflight"
"${ROOT}/scripts/check-kvm-host.sh" |& tee "${CERT_DIR}/host-kvm-preflight.txt"

STAGE="ubuntu-source-image"
if [[ ! -f "${SOURCE_IMAGE}" ]]; then
    DEFAULT_SOURCE="/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img"
    [[ "${SOURCE_IMAGE}" == "${DEFAULT_SOURCE}" ]] || die "Custom SUPRALINUX_SOURCE_IMAGE is missing: ${SOURCE_IMAGE}"
    "${ROOT}/scripts/fetch-ubuntu-26.04-cloud-image.sh" |& tee "${CERT_DIR}/source-image-fetch.txt"
fi
"${ROOT}/scripts/verify-ubuntu-cloud-image-provenance.sh" \
    "${SOURCE_IMAGE}" "${SOURCE_IMAGE}.provenance.txt" \
    |& tee "${CERT_DIR}/source-image-verification.txt"

golden_source_commit() {
    awk -F= '$1 == "source_commit" {print $2; exit}' "${GOLDEN_IMAGE}.provenance.txt"
}

golden_input_digest() {
    awk -F= '$1 == "golden_input_digest" {print $2; exit}' "${GOLDEN_IMAGE}.provenance.txt"
}

STAGE="golden-image-admission"
NEED_BUILD=0
if [[ ! -f "${GOLDEN_IMAGE}" || ! -f "${GOLDEN_IMAGE}.provenance.txt" ]]; then
    NEED_BUILD=1
else
    if ! SUPRALINUX_GOLDEN_COMPAT_COMMIT="${PR_HEAD_SHA}" \
        "${ROOT}/scripts/check-golden-image-provenance.sh" \
        "${GOLDEN_IMAGE}" "${CERT_DIR}/golden-provenance-before.txt"; then
        [[ "${REBUILD_GOLDEN}" == "1" ]] || die "Existing golden image failed provenance or golden-input compatibility validation. Set SUPRALINUX_REBUILD_GOLDEN=1 only after reviewing the preserved evidence."
        NEED_BUILD=1
    fi
fi

if (( NEED_BUILD )); then
    BUILD_EVIDENCE="${CERT_DIR}/golden-build"
    mkdir -p "${BUILD_EVIDENCE}"
    build_env=(
        "SUPRALINUX_SOURCE_COMMIT=${PR_HEAD_SHA}"
        "SUPRALINUX_SOURCE_IMAGE=${SOURCE_IMAGE}"
        "SUPRALINUX_GOLDEN_IMAGE=${GOLDEN_IMAGE}"
        "SUPRALINUX_HOST_EVIDENCE_ROOT=${BUILD_EVIDENCE}"
    )
    if [[ -e "${GOLDEN_IMAGE}" ]]; then
        [[ "${REBUILD_GOLDEN}" == "1" ]] || die "Golden replacement requires SUPRALINUX_REBUILD_GOLDEN=1."
        build_env+=("SUPRALINUX_REPLACE_GOLDEN_IMAGE=1")
    fi
    env "${build_env[@]}" "${ROOT}/scripts/build-authoritative-runner-image.sh" \
        |& tee "${CERT_DIR}/golden-build-console.txt"
fi

SUPRALINUX_GOLDEN_COMPAT_COMMIT="${PR_HEAD_SHA}" \
    "${ROOT}/scripts/check-golden-image-provenance.sh" \
    "${GOLDEN_IMAGE}" "${CERT_DIR}/golden-provenance.txt" \
    |& tee "${CERT_DIR}/golden-provenance-console.txt"
GOLDEN_SOURCE_COMMIT="$(golden_source_commit)"
GOLDEN_INPUT_DIGEST="$(golden_input_digest)"
GOLDEN_SHA256="$(sha256sum "${GOLDEN_IMAGE}" | awk '{print $1}')"

run_gate() {
    local gate="$1"
    local gate_log="${CERT_DIR}/${gate}.console.txt"
    STAGE="gate-${gate}"
    env \
        SUPRALINUX_REPOSITORY="${REPOSITORY}" \
        SUPRALINUX_PR_NUMBER="${PR_NUMBER}" \
        SUPRALINUX_GITHUB_TOKEN="${HOST_GITHUB_TOKEN}" \
        SUPRALINUX_RUNNER_GROUP_ID="${RUNNER_GROUP_ID}" \
        SUPRALINUX_GOLDEN_IMAGE="${GOLDEN_IMAGE}" \
        SUPRALINUX_HOST_EVIDENCE_ROOT="${CERT_DIR}/gates" \
        "${ROOT}/scripts/run-kvm-jit-gate.sh" "${gate}" \
        |& tee "${gate_log}"
}

run_gate runner-contract
run_gate authoritative-package-proof
run_gate frameworks-sample-proof

STAGE="collect-gate-evidence"
mapfile -t HOST_RESULTS < <(find "${CERT_DIR}/gates" -type f -name host-result.json -print | sort)
[[ "${#HOST_RESULTS[@]}" -eq 3 ]] || die "Expected exactly three host-result.json files; found ${#HOST_RESULTS[@]}."

python3 - "${CERT_DIR}/gate-results.json" "${HOST_RESULTS[@]}" <<'PY'
import json
import sys
from pathlib import Path

out=Path(sys.argv[1])
rows=[]
for item in sys.argv[2:]:
    p=Path(item)
    data=json.loads(p.read_text())
    data["evidence_path"]=str(p.parent)
    rows.append(data)
expected=["runner-contract","authoritative-package-proof","frameworks-sample-proof"]
by_gate={row.get("gate"):row for row in rows}
if set(by_gate)!=set(expected):
    raise SystemExit(f"unexpected gate set: {sorted(by_gate)}")
ordered=[by_gate[x] for x in expected]
for row in ordered:
    if row.get("exit_code") != 0:
        raise SystemExit(f"gate did not pass: {row}")
    if not str(row.get("workflow_run_id","")).isdigit():
        raise SystemExit(f"gate lacks workflow_run_id: {row}")
out.write_text(json.dumps({"gates":ordered},indent=2)+"\n",encoding="utf-8")
PY

STATE="PASS"
STAGE="complete"
printf 'Authoritative KVM certification sequence: PASS\n'
printf 'pr_head_sha=%s\n' "${PR_HEAD_SHA}"
printf 'golden_image_sha256=%s\n' "${GOLDEN_SHA256}"
printf 'golden_source_commit=%s\n' "${GOLDEN_SOURCE_COMMIT}"
printf 'golden_input_digest=%s\n' "${GOLDEN_INPUT_DIGEST}"
printf 'evidence=%s\n' "${CERT_DIR}"
printf 'Canonical package state was not modified. Stable publication remains unauthorized.\n'
