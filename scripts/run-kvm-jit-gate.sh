#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="${SUPRALINUX_REPOSITORY:-SupraLINUX/SupraLINUX}"
PR_NUMBER="${SUPRALINUX_PR_NUMBER:-1}"
GATE="${1:-${SUPRALINUX_GATE:-}}"
RUNNER_GROUP_ID="${SUPRALINUX_RUNNER_GROUP_ID:-}"
GOLDEN_IMAGE="${SUPRALINUX_GOLDEN_IMAGE:-/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2}"
STATE_DIR="${SUPRALINUX_KVM_STATE_DIR:-/var/lib/supralinux/ephemeral-runners}"
EVIDENCE_ROOT="${SUPRALINUX_HOST_EVIDENCE_ROOT:-/var/lib/supralinux/evidence/host-kvm}"
RUNNER_USER="${SUPRALINUX_RUNNER_USER:-ubuntu}"
LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
LIBVIRT_NETWORK="${SUPRALINUX_LIBVIRT_NETWORK:-default}"
VM_MEMORY_MIB="${SUPRALINUX_VM_MEMORY_MIB:-12288}"
VM_VCPUS="${SUPRALINUX_VM_VCPUS:-6}"
VM_DISK_SIZE_GIB="${SUPRALINUX_VM_DISK_SIZE_GIB:-80}"
ONLINE_TIMEOUT_SECONDS="${SUPRALINUX_ONLINE_TIMEOUT_SECONDS:-300}"
BUSY_TIMEOUT_SECONDS="${SUPRALINUX_BUSY_TIMEOUT_SECONDS:-300}"
JOB_TIMEOUT_SECONDS="${SUPRALINUX_JOB_TIMEOUT_SECONDS:-7200}"
API_VERSION="2026-03-10"
HOST_GITHUB_TOKEN="${SUPRALINUX_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"

case "${GATE}" in
    runner-contract)
        GATE_LABEL="ci:runner-contract"
        WORKFLOW_NAME="Authoritative runner contract"
        ;;
    authoritative-package-proof)
        GATE_LABEL="ci:authoritative-package-proof"
        WORKFLOW_NAME="Phase 1 authoritative KVM package proof"
        ;;
    *)
        printf 'Usage: %s {runner-contract|authoritative-package-proof}\n' "$0" >&2
        exit 2
        ;;
esac

if [[ -z "${HOST_GITHUB_TOKEN}" ]]; then
    printf 'SUPRALINUX_GITHUB_TOKEN (or GITHUB_TOKEN) must be supplied in the host environment.\n' >&2
    exit 1
fi
if [[ -z "${RUNNER_GROUP_ID}" || ! "${RUNNER_GROUP_ID}" =~ ^[0-9]+$ ]]; then
    printf 'SUPRALINUX_RUNNER_GROUP_ID must be the numeric runner group ID allowed to serve this repository.\n' >&2
    exit 1
fi
if [[ ! "${RUNNER_USER}" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]]; then
    printf 'SUPRALINUX_RUNNER_USER is not a valid simple Linux user name: %s\n' "${RUNNER_USER}" >&2
    exit 1
fi
if [[ ! "${PR_NUMBER}" =~ ^[0-9]+$ ]]; then
    printf 'SUPRALINUX_PR_NUMBER must be numeric.\n' >&2
    exit 1
fi

required_commands=(
    base64
    curl
    jq
    qemu-img
    sha256sum
    virsh
    virt-copy-out
    virt-install
)
for command_name in "${required_commands[@]}"; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing host command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ ! -f "${GOLDEN_IMAGE}" ]]; then
    printf 'Golden image not found: %s\n' "${GOLDEN_IMAGE}" >&2
    exit 1
fi
if [[ ! -c /dev/kvm || ! -r /dev/kvm || ! -w /dev/kvm ]]; then
    printf '/dev/kvm is not usable by the host orchestration user.\n' >&2
    exit 1
fi
if ! grep -Eq '\b(vmx|svm)\b' /proc/cpuinfo; then
    printf 'CPU virtualization extensions are not visible on the host.\n' >&2
    exit 1
fi

export LIBVIRT_DEFAULT_URI="${LIBVIRT_URI}"
if ! virsh net-info "${LIBVIRT_NETWORK}" 2>/dev/null | grep -Eq '^Active:[[:space:]]+yes$'; then
    printf 'libvirt network %s is not active.\n' "${LIBVIRT_NETWORK}" >&2
    exit 1
fi

OWNER="${REPOSITORY%%/*}"
REPO="${REPOSITORY#*/}"
if [[ -z "${OWNER}" || -z "${REPO}" || "${OWNER}" == "${REPO}" ]]; then
    printf 'SUPRALINUX_REPOSITORY must use owner/repo form.\n' >&2
    exit 1
fi

api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local args=(
        --fail-with-body
        --silent
        --show-error
        --location
        --request "${method}"
        --header 'Accept: application/vnd.github+json'
        --header "Authorization: Bearer ${HOST_GITHUB_TOKEN}"
        --header "X-GitHub-Api-Version: ${API_VERSION}"
    )
    if [[ -n "${data}" ]]; then
        args+=(--header 'Content-Type: application/json' --data "${data}")
    fi
    curl "${args[@]}" "https://api.github.com${path}"
}

api_allow_404() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local body_file http_code
    body_file="$(mktemp)"
    local args=(
        --silent
        --show-error
        --location
        --request "${method}"
        --header 'Accept: application/vnd.github+json'
        --header "Authorization: Bearer ${HOST_GITHUB_TOKEN}"
        --header "X-GitHub-Api-Version: ${API_VERSION}"
        --output "${body_file}"
        --write-out '%{http_code}'
    )
    if [[ -n "${data}" ]]; then
        args+=(--header 'Content-Type: application/json' --data "${data}")
    fi
    http_code="$(curl "${args[@]}" "https://api.github.com${path}")"
    if [[ "${http_code}" != "200" && "${http_code}" != "201" && "${http_code}" != "204" && "${http_code}" != "404" ]]; then
        cat "${body_file}" >&2
        rm -f "${body_file}"
        return 1
    fi
    cat "${body_file}"
    rm -f "${body_file}"
    return 0
}

label_uri() {
    jq -rn --arg value "$1" '$value|@uri'
}

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
SAFE_GATE="${GATE//[^a-zA-Z0-9-]/-}"
VM_NAME="supralinux-${SAFE_GATE}-${RUN_ID,,}"
RUN_DIR="${STATE_DIR}/${VM_NAME}"
OVERLAY="${RUN_DIR}/disk.qcow2"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${VM_NAME}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUNNER_ID=""
LABEL_ADDED=0
VM_CREATED=0

mkdir -p "${RUN_DIR}" "${EVIDENCE_DIR}"
chmod 0700 "${RUN_DIR}"

cleanup() {
    local rc="$?"
    trap - EXIT INT TERM
    set +e

    if (( LABEL_ADDED )); then
        encoded_label="$(label_uri "${GATE_LABEL}")"
        api_allow_404 DELETE "/repos/${REPOSITORY}/issues/${PR_NUMBER}/labels/${encoded_label}" >/dev/null 2>&1 || true
    fi

    if [[ -n "${RUNNER_ID}" ]]; then
        api_allow_404 DELETE "/repos/${REPOSITORY}/actions/runners/${RUNNER_ID}" >/dev/null 2>&1 || true
    fi

    if (( VM_CREATED )); then
        virsh dumpxml "${VM_NAME}" > "${EVIDENCE_DIR}/domain.xml" 2>/dev/null || true
        virsh shutdown "${VM_NAME}" >/dev/null 2>&1 || true
        for _ in $(seq 1 30); do
            if ! virsh domstate "${VM_NAME}" 2>/dev/null | grep -Eq 'running|paused|in shutdown'; then
                break
            fi
            sleep 2
        done
        if virsh domstate "${VM_NAME}" 2>/dev/null | grep -Eq 'running|paused|in shutdown'; then
            virsh destroy "${VM_NAME}" >/dev/null 2>&1 || true
        fi

        mkdir -p "${EVIDENCE_DIR}/guest-files"
        virt-copy-out -a "${OVERLAY}" /opt/actions-runner/_diag "${EVIDENCE_DIR}/guest-files" >/dev/null 2>&1 || true
        virt-copy-out -a "${OVERLAY}" /var/lib/supralinux/evidence "${EVIDENCE_DIR}/guest-files" >/dev/null 2>&1 || true
        virt-copy-out -a "${OVERLAY}" /var/log/supralinux-actions-runner-console.log "${EVIDENCE_DIR}/guest-files" >/dev/null 2>&1 || true
        virsh undefine "${VM_NAME}" >/dev/null 2>&1 || true
    fi

    if [[ -f "${OVERLAY}" ]]; then
        qemu-img info --output=json "${OVERLAY}" > "${EVIDENCE_DIR}/overlay-info.json" 2>/dev/null || true
        sha256sum "${OVERLAY}" > "${EVIDENCE_DIR}/overlay-sha256.txt" 2>/dev/null || true
        rm -f "${OVERLAY}"
    fi
    rmdir "${RUN_DIR}" >/dev/null 2>&1 || true

    printf '{\n  "gate": %s,\n  "exit_code": %d,\n  "finished_at": %s\n}\n' \
        "$(jq -Rn --arg v "${GATE}" '$v')" \
        "${rc}" \
        "$(jq -Rn --arg v "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '$v')" \
        > "${EVIDENCE_DIR}/host-result.json"
    exit "${rc}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Validating pull request and preparing gate %s...\n' "${GATE}"
PR_JSON="$(api GET "/repos/${REPOSITORY}/pulls/${PR_NUMBER}")"
PR_STATE="$(jq -r '.state' <<<"${PR_JSON}")"
PR_HEAD_REPO="$(jq -r '.head.repo.full_name // empty' <<<"${PR_JSON}")"
PR_HEAD_SHA="$(jq -r '.head.sha // empty' <<<"${PR_JSON}")"
if [[ "${PR_STATE}" != "open" ]]; then
    printf 'PR #%s is not open.\n' "${PR_NUMBER}" >&2
    exit 1
fi
if [[ "${PR_HEAD_REPO}" != "${REPOSITORY}" ]]; then
    printf 'Authoritative self-hosted gates refuse fork PRs: %s\n' "${PR_HEAD_REPO}" >&2
    exit 1
fi
if [[ -z "${PR_HEAD_SHA}" ]]; then
    printf 'Could not resolve PR head SHA.\n' >&2
    exit 1
fi

{
    printf 'started_at=%s\n' "${STARTED_AT}"
    printf 'repository=%s\n' "${REPOSITORY}"
    printf 'pr_number=%s\n' "${PR_NUMBER}"
    printf 'pr_head_sha=%s\n' "${PR_HEAD_SHA}"
    printf 'gate=%s\n' "${GATE}"
    printf 'gate_label=%s\n' "${GATE_LABEL}"
    printf 'workflow_name=%s\n' "${WORKFLOW_NAME}"
    printf 'vm_name=%s\n' "${VM_NAME}"
    printf 'golden_image=%s\n' "${GOLDEN_IMAGE}"
    printf 'golden_image_sha256='; sha256sum "${GOLDEN_IMAGE}" | awk '{print $1}'
    printf 'libvirt_uri=%s\n' "${LIBVIRT_URI}"
    printf 'libvirt_network=%s\n' "${LIBVIRT_NETWORK}"
    printf 'vm_memory_mib=%s\n' "${VM_MEMORY_MIB}"
    printf 'vm_vcpus=%s\n' "${VM_VCPUS}"
    printf 'vm_disk_size_gib=%s\n' "${VM_DISK_SIZE_GIB}"
} > "${EVIDENCE_DIR}/host-environment.txt"

printf 'Ensuring trigger label exists and is currently absent...\n'
ENCODED_LABEL="$(label_uri "${GATE_LABEL}")"
if ! api_allow_404 GET "/repos/${REPOSITORY}/labels/${ENCODED_LABEL}" | jq -e '.name? // empty' >/dev/null 2>&1; then
    api POST "/repos/${REPOSITORY}/labels" \
        "$(jq -nc --arg name "${GATE_LABEL}" --arg description 'SupraLINUX controlled authoritative CI gate' '{name:$name,color:"5319e7",description:$description}')" \
        >/dev/null
fi
api_allow_404 DELETE "/repos/${REPOSITORY}/issues/${PR_NUMBER}/labels/${ENCODED_LABEL}" >/dev/null 2>&1 || true

printf 'Creating ephemeral overlay and KVM VM...\n'
BACKING_FORMAT="$(qemu-img info --output=json "${GOLDEN_IMAGE}" | jq -r '.format')"
qemu-img create -f qcow2 -F "${BACKING_FORMAT}" -b "${GOLDEN_IMAGE}" "${OVERLAY}"
qemu-img resize "${OVERLAY}" "${VM_DISK_SIZE_GIB}G"
qemu-img info --output=json "${OVERLAY}" > "${EVIDENCE_DIR}/overlay-info-before-boot.json"

VM_CREATED=1
virt-install \
    --connect "${LIBVIRT_URI}" \
    --name "${VM_NAME}" \
    --memory "${VM_MEMORY_MIB}" \
    --vcpus "${VM_VCPUS}" \
    --cpu host-passthrough \
    --import \
    --disk "path=${OVERLAY},format=qcow2,bus=virtio,cache=none" \
    --network "network=${LIBVIRT_NETWORK},model=virtio" \
    --channel unix,target.type=virtio,target.name=org.qemu.guest_agent.0 \
    --graphics none \
    --noautoconsole \
    --osinfo detect=on,require=off

qga() {
    virsh qemu-agent-command "${VM_NAME}" "$1"
}

printf 'Waiting for qemu-guest-agent...\n'
DEADLINE=$(( $(date +%s) + ONLINE_TIMEOUT_SECONDS ))
until qga '{"execute":"guest-ping"}' >/dev/null 2>&1; do
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Timed out waiting for qemu-guest-agent.\n' >&2
        exit 1
    fi
    sleep 2
done

printf 'Requesting repository-scoped GitHub JIT runner configuration...\n'
JIT_PAYLOAD="$(jq -nc \
    --arg name "${VM_NAME}" \
    --argjson group "${RUNNER_GROUP_ID}" \
    '{name:$name,runner_group_id:$group,labels:["self-hosted","linux","x64","supralinux","ubuntu-26.04","kvm","ephemeral"],work_folder:"_work"}')"
JIT_JSON="$(api POST "/repos/${REPOSITORY}/actions/runners/generate-jitconfig" "${JIT_PAYLOAD}")"
RUNNER_ID="$(jq -r '.runner.id // empty' <<<"${JIT_JSON}")"
JIT_CONFIG="$(jq -r '.encoded_jit_config // empty' <<<"${JIT_JSON}")"
if [[ -z "${RUNNER_ID}" || -z "${JIT_CONFIG}" ]]; then
    printf 'GitHub did not return runner.id and encoded_jit_config.\n' >&2
    exit 1
fi
printf 'runner_id=%s\n' "${RUNNER_ID}" >> "${EVIDENCE_DIR}/host-environment.txt"

printf 'Injecting JIT configuration into guest tmpfs...\n'
OPEN_PAYLOAD="$(jq -nc --arg path '/run/supralinux-jit-config' '{execute:"guest-file-open",arguments:{path:$path,mode:"w"}}')"
HANDLE="$(qga "${OPEN_PAYLOAD}" | jq -r '.return')"
WRITE_PAYLOAD="$(jq -nc --argjson handle "${HANDLE}" --arg data "$(printf '%s' "${JIT_CONFIG}" | base64 -w0)" \
    '{execute:"guest-file-write",arguments:{handle:$handle,"buf-b64":$data}}')"
qga "${WRITE_PAYLOAD}" >/dev/null
qga "$(jq -nc --argjson handle "${HANDLE}" '{execute:"guest-file-close",arguments:{handle:$handle}}')" >/dev/null
unset JIT_CONFIG JIT_JSON

START_COMMAND="chown ${RUNNER_USER}:${RUNNER_USER} /run/supralinux-jit-config && chmod 600 /run/supralinux-jit-config && : > /var/log/supralinux-actions-runner-console.log && chown ${RUNNER_USER}:${RUNNER_USER} /var/log/supralinux-actions-runner-console.log && exec su -s /bin/bash - ${RUNNER_USER} -c 'cd /opt/actions-runner && config=\"\$(cat /run/supralinux-jit-config)\" && rm -f /run/supralinux-jit-config && exec ./run.sh --jitconfig \"\$config\" >>/var/log/supralinux-actions-runner-console.log 2>&1'"
EXEC_PAYLOAD="$(jq -nc --arg cmd "${START_COMMAND}" '{execute:"guest-exec",arguments:{path:"/bin/bash",arg:["-lc",$cmd],"capture-output":false}}')"
qga "${EXEC_PAYLOAD}" > "${EVIDENCE_DIR}/guest-runner-exec.json"

runner_snapshot() {
    api GET "/repos/${REPOSITORY}/actions/runners?per_page=100" \
        | jq -c --argjson id "${RUNNER_ID}" '.runners[]? | select(.id == $id)'
}

printf 'Waiting for JIT runner to become online...\n'
DEADLINE=$(( $(date +%s) + ONLINE_TIMEOUT_SECONDS ))
while true; do
    SNAPSHOT="$(runner_snapshot)"
    if [[ -n "${SNAPSHOT}" && "$(jq -r '.status' <<<"${SNAPSHOT}")" == "online" ]]; then
        printf '%s\n' "${SNAPSHOT}" > "${EVIDENCE_DIR}/runner-online.json"
        break
    fi
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Timed out waiting for JIT runner %s to become online.\n' "${RUNNER_ID}" >&2
        exit 1
    fi
    sleep 3
done

printf 'Triggering the PR gate by adding %s...\n' "${GATE_LABEL}"
api POST "/repos/${REPOSITORY}/issues/${PR_NUMBER}/labels" \
    "$(jq -nc --arg label "${GATE_LABEL}" '{labels:[$label]}')" >/dev/null
LABEL_ADDED=1

printf 'Waiting for GitHub to assign the single JIT job...\n'
DEADLINE=$(( $(date +%s) + BUSY_TIMEOUT_SECONDS ))
while true; do
    SNAPSHOT="$(runner_snapshot)"
    if [[ -n "${SNAPSHOT}" && "$(jq -r '.busy' <<<"${SNAPSHOT}")" == "true" ]]; then
        printf '%s\n' "${SNAPSHOT}" > "${EVIDENCE_DIR}/runner-busy.json"
        break
    fi
    if [[ -z "${SNAPSHOT}" ]]; then
        printf 'JIT runner disappeared before a busy state was observed.\n' >&2
        exit 1
    fi
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Timed out waiting for GitHub to assign the gate job.\n' >&2
        exit 1
    fi
    sleep 3
done

printf 'Waiting for the JIT runner to complete its one job and deregister...\n'
DEADLINE=$(( $(date +%s) + JOB_TIMEOUT_SECONDS ))
while true; do
    SNAPSHOT="$(runner_snapshot)"
    if [[ -z "${SNAPSHOT}" ]]; then
        break
    fi
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Timed out waiting for the JIT runner job to finish.\n' >&2
        exit 1
    fi
    sleep 5
done

printf 'Resolving workflow conclusion...\n'
DEADLINE=$(( $(date +%s) + 120 ))
WORKFLOW_RUN=""
while true; do
    RUNS_JSON="$(api GET "/repos/${REPOSITORY}/actions/runs?event=pull_request&per_page=100")"
    WORKFLOW_RUN="$(jq -c \
        --arg workflow "${WORKFLOW_NAME}" \
        --arg branch "$(jq -r '.head.ref' <<<"${PR_JSON}")" \
        --arg started "${STARTED_AT}" \
        '[.workflow_runs[] | select(.name == $workflow and .head_branch == $branch and .created_at >= $started)] | sort_by(.created_at) | last // empty' \
        <<<"${RUNS_JSON}")"
    if [[ -n "${WORKFLOW_RUN}" && "$(jq -r '.status' <<<"${WORKFLOW_RUN}")" == "completed" ]]; then
        printf '%s\n' "${WORKFLOW_RUN}" > "${EVIDENCE_DIR}/workflow-run.json"
        break
    fi
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Could not resolve a completed workflow run for %s.\n' "${WORKFLOW_NAME}" >&2
        exit 1
    fi
    sleep 3
done

CONCLUSION="$(jq -r '.conclusion // empty' <<<"${WORKFLOW_RUN}")"
RUN_URL="$(jq -r '.html_url // empty' <<<"${WORKFLOW_RUN}")"
printf 'Workflow conclusion: %s\n%s\n' "${CONCLUSION}" "${RUN_URL}"
if [[ "${CONCLUSION}" != "success" ]]; then
    exit 1
fi

printf 'Authoritative KVM gate %s: PASS\n' "${GATE}"
