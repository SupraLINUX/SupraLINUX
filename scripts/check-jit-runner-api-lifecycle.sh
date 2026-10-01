#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="${SUPRALINUX_REPOSITORY:-SupraLINUX/SupraLINUX}"
RUNNER_ORGANIZATION="${SUPRALINUX_RUNNER_ORGANIZATION:-${REPOSITORY%%/*}}"
RUNNER_GROUP_ID="${SUPRALINUX_RUNNER_GROUP_ID:-}"
API_VERSION="2026-03-10"
HOST_GITHUB_TOKEN="${SUPRALINUX_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"
EVIDENCE_ROOT="${SUPRALINUX_JIT_PREFLIGHT_EVIDENCE_ROOT:-/var/lib/supralinux/evidence/jit-api-preflight}"

if [[ -z "${HOST_GITHUB_TOKEN}" ]]; then
    printf 'SUPRALINUX_GITHUB_TOKEN (or GITHUB_TOKEN) must be supplied.\n' >&2
    exit 1
fi
if [[ -z "${RUNNER_GROUP_ID}" || ! "${RUNNER_GROUP_ID}" =~ ^[0-9]+$ ]]; then
    printf 'SUPRALINUX_RUNNER_GROUP_ID must be numeric.\n' >&2
    exit 1
fi
if [[ ! "${REPOSITORY}" =~ ^[^/]+/[^/]+$ ]]; then
    printf 'SUPRALINUX_REPOSITORY must use owner/repo form.\n' >&2
    exit 1
fi
REPOSITORY_OWNER="${REPOSITORY%%/*}"
if [[ "${RUNNER_ORGANIZATION}" != "${REPOSITORY_OWNER}" ]]; then
    printf 'Runner organization %s does not own repository %s.\n' "${RUNNER_ORGANIZATION}" "${REPOSITORY}" >&2
    exit 1
fi
for command_name in curl jq sed tail date mkdir; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing command: %s\n' "${command_name}" >&2
        exit 1
    }
done

api() {
    local method="$1"
    local path="$2"
    curl --fail-with-body --silent --show-error --location \
        --request "${method}" \
        --header 'Accept: application/vnd.github+json' \
        --header "Authorization: Bearer ${HOST_GITHUB_TOKEN}" \
        --header "X-GitHub-Api-Version: ${API_VERSION}" \
        "https://api.github.com${path}"
}

api_allow_404() {
    local method="$1"
    local path="$2"
    local body_file http_code
    body_file="$(mktemp)"
    http_code="$(curl --silent --show-error --location \
        --request "${method}" \
        --header 'Accept: application/vnd.github+json' \
        --header "Authorization: Bearer ${HOST_GITHUB_TOKEN}" \
        --header "X-GitHub-Api-Version: ${API_VERSION}" \
        --output "${body_file}" \
        --write-out '%{http_code}' \
        "https://api.github.com${path}")"
    if [[ "${http_code}" != "200" && "${http_code}" != "204" && "${http_code}" != "404" ]]; then
        cat "${body_file}" >&2
        rm -f "${body_file}"
        return 1
    fi
    cat "${body_file}"
    rm -f "${body_file}"
}

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
RUNNER_NAME="supralinux-jit-api-preflight-${RUN_ID,,}"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${RUN_ID}"
mkdir -p "${EVIDENCE_DIR}"

cleanup_named_runner() {
    local runners matching runner_id cleanup_failed=0
    runners="$(api GET "/orgs/${RUNNER_ORGANIZATION}/actions/runners?per_page=100")" || return 1
    matching="$(jq -c --arg name "${RUNNER_NAME}" '[.runners[]? | select(.name == $name) | {id,name,status,busy}]' <<<"${runners}")"
    printf '%s\n' "${matching}" > "${EVIDENCE_DIR}/matching-runners.json"
    while IFS= read -r runner_id; do
        [[ -n "${runner_id}" ]] || continue
        api_allow_404 DELETE "/orgs/${RUNNER_ORGANIZATION}/actions/runners/${runner_id}" >/dev/null || cleanup_failed=1
    done < <(jq -r '.[].id' <<<"${matching}")
    return "${cleanup_failed}"
}

REPO_JSON="$(api GET "/repos/${REPOSITORY}")"
REPO_ID="$(jq -r '.id // empty' <<<"${REPO_JSON}")"
GROUP_JSON="$(api GET "/orgs/${RUNNER_ORGANIZATION}/actions/runner-groups/${RUNNER_GROUP_ID}")"
GROUP_NAME="$(jq -r '.name // empty' <<<"${GROUP_JSON}")"
GROUP_VISIBILITY="$(jq -r '.visibility // empty' <<<"${GROUP_JSON}")"
if [[ -z "${REPO_ID}" || -z "${GROUP_NAME}" ]]; then
    printf 'Could not establish repository/runner-group identity.\n' >&2
    exit 1
fi
if [[ "${GROUP_VISIBILITY}" == "selected" ]]; then
    SELECTED_JSON="$(api GET "/orgs/${RUNNER_ORGANIZATION}/actions/runner-groups/${RUNNER_GROUP_ID}/repositories")"
    if ! jq -e --argjson id "${REPO_ID}" '.repositories[]? | select(.id == $id)' <<<"${SELECTED_JSON}" >/dev/null; then
        printf 'Repository %s is not selected for runner group %s.\n' "${REPOSITORY}" "${RUNNER_GROUP_ID}" >&2
        exit 1
    fi
fi

PAYLOAD="$(jq -nc \
    --arg name "${RUNNER_NAME}" \
    --argjson group "${RUNNER_GROUP_ID}" \
    '{name:$name,runner_group_id:$group,labels:["self-hosted","linux","x64","supralinux-jit-api-preflight"],work_folder:"_work"}')"

raw="" curl_rc=0
raw="$(curl --silent --show-error --location \
    --request POST \
    --header 'Accept: application/vnd.github+json' \
    --header "Authorization: Bearer ${HOST_GITHUB_TOKEN}" \
    --header "X-GitHub-Api-Version: ${API_VERSION}" \
    --header 'Content-Type: application/json' \
    --data "${PAYLOAD}" \
    --write-out $'\n__SUPRALINUX_HTTP_STATUS__=%{http_code}' \
    "https://api.github.com/orgs/${RUNNER_ORGANIZATION}/actions/runners/generate-jitconfig")" || curl_rc=$?

http_code="$(tail -n 1 <<<"${raw}" | sed -n 's/^__SUPRALINUX_HTTP_STATUS__=//p')"
body="$(sed '$d' <<<"${raw}")"
printf 'curl_exit_code=%s\nhttp_status=%s\n' "${curl_rc}" "${http_code:-missing}" > "${EVIDENCE_DIR}/transport.txt"

if (( curl_rc != 0 )) || [[ "${http_code}" != "201" ]]; then
    unset body raw
    cleanup_named_runner || true
    printf 'status=INFRA_INVALID\nreason=ambiguous-jit-create\n' > "${EVIDENCE_DIR}/result.txt"
    printf 'JIT API lifecycle synthetic preflight: INFRA_INVALID (curl=%s HTTP=%s)\n' "${curl_rc}" "${http_code:-missing}" >&2
    exit 1
fi

RUNNER_ID="$(jq -r '.runner.id // empty' <<<"${body}")"
JIT_CONFIG="$(jq -r '.encoded_jit_config // empty' <<<"${body}")"
if [[ ! "${RUNNER_ID}" =~ ^[0-9]+$ || -z "${JIT_CONFIG}" ]]; then
    unset JIT_CONFIG body raw
    cleanup_named_runner || true
    printf 'status=INFRA_INVALID\nreason=incomplete-jit-response\n' > "${EVIDENCE_DIR}/result.txt"
    printf 'JIT API lifecycle synthetic preflight: INFRA_INVALID (incomplete response)\n' >&2
    exit 1
fi
unset JIT_CONFIG body raw

api_allow_404 DELETE "/orgs/${RUNNER_ORGANIZATION}/actions/runners/${RUNNER_ID}" >/dev/null
REMAINING="$(api GET "/orgs/${RUNNER_ORGANIZATION}/actions/runners?per_page=100")"
if jq -e --argjson id "${RUNNER_ID}" '.runners[]? | select(.id == $id)' <<<"${REMAINING}" >/dev/null; then
    printf 'status=INFRA_INVALID\nreason=runner-cleanup-failed\nrunner_id=%s\n' "${RUNNER_ID}" > "${EVIDENCE_DIR}/result.txt"
    printf 'JIT API lifecycle synthetic preflight: INFRA_INVALID (runner cleanup failed)\n' >&2
    exit 1
fi

printf 'status=PASS\nrepository=%s\nrunner_organization=%s\nrunner_group_id=%s\nrunner_group_name=%s\nrunner_id=%s\nhttp_status=201\ncleanup=PASS\n' \
    "${REPOSITORY}" "${RUNNER_ORGANIZATION}" "${RUNNER_GROUP_ID}" "${GROUP_NAME}" "${RUNNER_ID}" \
    > "${EVIDENCE_DIR}/result.txt"

printf 'JIT API lifecycle synthetic preflight: PASS\n'
printf 'evidence=%s\n' "${EVIDENCE_DIR}"
