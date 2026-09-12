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
RUNNER_CONTRACT_WORKFLOW="Authoritative runner contract"
PACKAGE_PROOF_WORKFLOW="Phase 1 authoritative KVM package proof"

case "${GATE}" in
    runner-contract)
        GATE_LABEL="ci:runner-contract"
        WORKFLOW_NAME="${RUNNER_CONTRACT_WORKFLOW}"
        ;;
    authoritative-package-proof)
        GATE_LABEL="ci:authoritative-package-proof"
        WORKFLOW_NAME="${PACKAGE_PROOF_WORKFLOW}"
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
    flock
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

GOLDEN_PROVENANCE="${GOLDEN_IMAGE}.provenance.txt"
if [[ ! -f "${GOLDEN_IMAGE}" ]]; then
    printf 'Golden image not found: %s\n' "${GOLDEN_IMAGE}" >&2
    exit 1
fi
if [[ ! -f "${GOLDEN_PROVENANCE}" ]]; then
    printf 'Golden image provenance is missing: %s\n' "${GOLDEN_PROVENANCE}" >&2
    exit 1
fi
GOLDEN_SHA256="$(sha256sum "${GOLDEN_IMAGE}" | awk '{print $1}')"
PROVENANCE_SHA256="$(awk -F= '$1 == "golden_image_sha256" {print $2; exit}' "${GOLDEN_PROVENANCE}")"
if [[ ! "${PROVENANCE_SHA256}" =~ ^[0-9a-fA-F]{64}$ || "${PROVENANCE_SHA256,,}" != "${GOLDEN_SHA256,,}" ]]; then
    printf 'Golden image SHA-256 does not match its provenance. image=%s provenance=%s\n' \
        "${GOLDEN_SHA256}" "${PROVENANCE_SHA256:-missing}" >&2
    exit 1
fi
if ! grep -qx 'source_checkout_removed=yes' "${GOLDEN_PROVENANCE}"; then
    printf 'Golden image provenance does not confirm source checkout cleanup.\n' >&2
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

SAFE_REPOSITORY="${REPOSITORY//[^a-zA-Z0-9._-]/-}"
SAFE_GATE="${GATE//[^a-zA-Z0-9-]/-}"
mkdir -p "${STATE_DIR}/.locks"
LOCK_FILE="${STATE_DIR}/.locks/${SAFE_REPOSITORY}-authoritative.lock"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    printf 'Another SupraLINUX authoritative JIT orchestration is already active on this host: %s\n' "${LOCK_FILE}" >&2
    exit 1
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
VM_NAME="supralinux-${SAFE_GATE}-${RUN_ID,,}"
RUN_DIR="${STATE_DIR}/${VM_NAME}"
OVERLAY="${RUN_DIR}/disk.qcow2"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${VM_NAME}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUNNER_ID=""
GUEST_RUNNER_PID=""
WORKFLOW_RUN_ID=""
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

    printf '{\n  "gate": %s,\n  "exit_code": %d,\n  "workflow_run_id": %s,\n  "finished_at": %s\n}\n' \
        "$(jq -Rn --arg v "${GATE}" '$v')" \
        "${rc}" \
        "$(jq -Rn --arg v "${WORKFLOW_RUN_ID}" '$v')" \
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
PR_HEAD_BRANCH="$(jq -r '.head.ref // empty' <<<"${PR_JSON}")"
if [[ "${PR_STATE}" != "open" ]]; then
    printf 'PR #%s is not open.\n' "${PR_NUMBER}" >&2
    exit 1
fi
if [[ "${PR_HEAD_REPO}" != "${REPOSITORY}" ]]; then
    printf 'Authoritative self-hosted gates refuse fork PRs: %s\n' "${PR_HEAD_REPO}" >&2
    exit 1
fi
if [[ ! "${PR_HEAD_SHA}" =~ ^[0-9a-fA-F]{40}$ ]]; then
    printf 'Could not resolve a valid PR head SHA.\n' >&2
    exit 1
fi

printf 'Checking for stale/active authoritative workflow runs before creating a runner...\n'
ACTIVE_RUNS_JSON="$(api GET "/repos/${REPOSITORY}/actions/runs?event=pull_request&per_page=100")"
ACTIVE_AUTHORITATIVE="$(jq -c \
    --arg runner_contract "${RUNNER_CONTRACT_WORKFLOW}" \
    --arg package_proof "${PACKAGE_PROOF_WORKFLOW}" \
    '[.workflow_runs[] | select((.name == $runner_contract or .name == $package_proof) and .status != "completed")]' \
    <<<"${ACTIVE_RUNS_JSON}")"
if (( $(jq 'length' <<<"${ACTIVE_AUTHORITATIVE}") > 0 )); then
    printf 'Refusing to create a JIT runner while another authoritative workflow is active or queued:\n' >&2
    jq -r '.[] | "  id=\(.id) name=\(.name) status=\(.status) url=\(.html_url)"' <<<"${ACTIVE_AUTHORITATIVE}" >&2
    exit 1
fi

BASELINE_RUNS_JSON="$(api GET "/repos/${REPOSITORY}/actions/runs?event=pull_request&head_sha=${PR_HEAD_SHA}&per_page=100")"
BASELINE_RUN_IDS="$(jq -c --arg workflow "${WORKFLOW_NAME}" '[.workflow_runs[] | select(.name == $workflow) | .id]' <<<"${BASELINE_RUNS_JSON}")"
printf '%s\n' "${BASELINE_RUN_IDS}" > "${EVIDENCE_DIR}/workflow-baseline-ids.json"

{
    printf 'started_at=%s\n' "${STARTED_AT}"
    printf 'repository=%s\n' "${REPOSITORY}"
    printf 'pr_number=%s\n' "${PR_NUMBER}"
    printf 'pr_head_sha=%s\n' "${PR_HEAD_SHA}"
    printf 'pr_head_branch=%s\n' "${PR_HEAD_BRANCH}"
    printf 'gate=%s\n' "${GATE}"
    printf 'gate_label=%s\n' "${GATE_LABEL}"
    printf 'workflow_name=%s\n' "${WORKFLOW_NAME}"
    printf 'vm_name=%s\n' "${VM_NAME}"
    printf 'golden_image=%s\n' "${GOLDEN_IMAGE}"
    printf 'golden_image_sha256=%s\n' "${GOLDEN_SHA256}"
    printf 'golden_provenance=%s\n' "${GOLDEN_PROVENANCE}"
    printf 'local_lock=%s\n' "${LOCK_FILE}"
    printf 'libvirt_uri=%s\n' "${LIBVIRT_URI}"
    printf 'libvirt_network=%s\n' "${LIBVIRT_NETWORK}"
    printf 'vm_memory_mib=%s\n' "${VM_MEMORY_MIB}"
    printf 'vm_vcpus=%s\n' "${VM_VCPUS}"
    printf 'vm_disk_size_gib=%s\n' "${VM_DISK_SIZE_GIB}"
    printf '\ngolden_provenance_contents:\n'
    cat "${GOLDEN_PROVENANCE}"
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

guest_runner_status() {
    [[ -n "${GUEST_RUNNER_PID}" ]] || return 0
    qga "$(jq -nc --argjson pid "${GUEST_RUNNER_PID}" '{execute:"guest-exec-status",arguments:{pid:$pid}}')"
}

fail_if_guest_runner_exited() {
    local status
    status="$(guest_runner_status)"
    if [[ -n "${status}" && "$(jq -r '.return.exited // false' <<<"${status}")" == "true" ]]; then
        printf '%s\n' "${status}" > "${EVIDENCE_DIR}/guest-runner-exited.json"
        printf 'Guest Actions runner process exited before the expected lifecycle point.\n' >&2
        return 1
    fi
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

START_COMMAND="chown ${RUNNER_USER}:${RUNNER_USER} /run/supralinux-jit-config && chmod 600 /run/supralinux-jit-config && : > /var/log/supralinux-actions-runner-console.log && chown ${RUNNER_USER}:${RUNNER_USER} /var/log/supralinux-actions-runner-console.log && exec su --login --shell /bin/bash --command 'cd /opt/actions-runner && config=\"\$(cat /run/supralinux-jit-config)\" && rm -f /run/supralinux-jit-config && exec ./run.sh --jitconfig \"\$config\" >>/var/log/supralinux-actions-runner-console.log 2>&1' ${RUNNER_USER}"
EXEC_PAYLOAD="$(jq -nc --arg cmd "${START_COMMAND}" '{execute:"guest-exec",arguments:{path:"/bin/bash",arg:["-lc",$cmd],"capture-output":false}}')"
EXEC_RESULT="$(qga "${EXEC_PAYLOAD}")"
printf '%s\n' "${EXEC_RESULT}" > "${EVIDENCE_DIR}/guest-runner-exec.json"
GUEST_RUNNER_PID="$(jq -r '.return.pid // empty' <<<"${EXEC_RESULT}")"
if [[ ! "${GUEST_RUNNER_PID}" =~ ^[0-9]+$ ]]; then
    printf 'qemu-guest-agent did not return a valid runner process PID.\n' >&2
    exit 1
fi

runner_snapshot() {
    api GET "/repos/${REPOSITORY}/actions/runners?per_page=100" \
        | jq -c --argjson id "${RUNNER_ID}" '.runners[]? | select(.id == $id)'
}

printf 'Waiting for JIT runner to become online...\n'
DEADLINE=$(( $(date +%s) + ONLINE_TIMEOUT_SECONDS ))
while true; do
    fail_if_guest_runner_exited || exit 1
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
    fail_if_guest_runner_exited || exit 1
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

printf 'Resolving the newly-created workflow run by exact PR head SHA...\n'
DEADLINE=$(( $(date +%s) + 120 ))
while true; do
    RUNS_JSON="$(api GET "/repos/${REPOSITORY}/actions/runs?event=pull_request&head_sha=${PR_HEAD_SHA}&per_page=100")"
    CANDIDATES="$(jq -c \
        --arg workflow "${WORKFLOW_NAME}" \
        --arg sha "${PR_HEAD_SHA}" \
        --argjson baseline "${BASELINE_RUN_IDS}" \
        '[.workflow_runs[]
          | select(.name == $workflow and .head_sha == $sha)
          | select(.id as $id | ($baseline | index($id) | not))]' \
        <<<"${RUNS_JSON}")"
    CANDIDATE_COUNT="$(jq 'length' <<<"${CANDIDATES}")"
    if (( CANDIDATE_COUNT > 1 )); then
        printf '%s\n' "${CANDIDATES}" > "${EVIDENCE_DIR}/workflow-run-ambiguous.json"
        printf 'More than one new authoritative workflow run appeared for the exact PR head SHA; refusing ambiguous attribution.\n' >&2
        exit 1
    fi
    if (( CANDIDATE_COUNT == 1 )); then
        WORKFLOW_RUN_ID="$(jq -r '.[0].id' <<<"${CANDIDATES}")"
        printf '%s\n' "$(jq -c '.[0]' <<<"${CANDIDATES}")" > "${EVIDENCE_DIR}/workflow-run-created.json"
        break
    fi
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Could not resolve the new workflow run for %s at head %s.\n' "${WORKFLOW_NAME}" "${PR_HEAD_SHA}" >&2
        exit 1
    fi
    sleep 2
done

printf 'Bound gate to workflow run ID %s. Waiting for the JIT runner to finish and deregister...\n' "${WORKFLOW_RUN_ID}"
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

printf 'Waiting for bound workflow run %s to complete...\n' "${WORKFLOW_RUN_ID}"
DEADLINE=$(( $(date +%s) + 180 ))
while true; do
    WORKFLOW_RUN="$(api GET "/repos/${REPOSITORY}/actions/runs/${WORKFLOW_RUN_ID}")"
    if [[ "$(jq -r '.head_sha // empty' <<<"${WORKFLOW_RUN}")" != "${PR_HEAD_SHA}" || \
          "$(jq -r '.name // empty' <<<"${WORKFLOW_RUN}")" != "${WORKFLOW_NAME}" || \
          "$(jq -r '.event // empty' <<<"${WORKFLOW_RUN}")" != "pull_request" ]]; then
        printf 'Bound workflow run identity changed or does not match the requested gate.\n' >&2
        exit 1
    fi
    if [[ "$(jq -r '.status' <<<"${WORKFLOW_RUN}")" == "completed" ]]; then
        printf '%s\n' "${WORKFLOW_RUN}" > "${EVIDENCE_DIR}/workflow-run.json"
        break
    fi
    if (( $(date +%s) >= DEADLINE )); then
        printf 'Timed out waiting for workflow run %s to reach completed state.\n' "${WORKFLOW_RUN_ID}" >&2
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
