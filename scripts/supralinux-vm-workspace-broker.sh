#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ $# -eq 0 ]] || { printf 'This broker accepts its request on stdin only.\n' >&2; exit 2; }
[[ "${EUID}" -eq 0 ]] || { printf 'Workspace broker must run through its restricted sudo rule.\n' >&2; exit 1; }

ORCHESTRATOR_USER="${SUDO_USER:-}"
EXPECTED_ORCHESTRATOR_USER="supralinux-orchestrator"
[[ "${ORCHESTRATOR_USER}" == "${EXPECTED_ORCHESTRATOR_USER}" ]] || {
    printf 'Unexpected caller: %s\n' "${ORCHESTRATOR_USER:-missing}" >&2
    exit 1
}

GOLDEN_IMAGE="/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2"
GOLDEN_PROVENANCE="${GOLDEN_IMAGE}.provenance.txt"
STATE_ROOT="/var/lib/supralinux/workspace-vms"
RESULT_ROOT="/var/lib/supralinux/workspace-results"
NETWORK_HELPER="/usr/local/libexec/supralinux-configure-kvm-guest-network.py"
LIBGUESTFS_HELPER="/usr/local/libexec/supralinux-with-libguestfs-runtime"
LIBVIRT_URI="qemu:///system"
LIBVIRT_QEMU_USER="libvirt-qemu"
MAX_REQUEST_BYTES=700000
VM_MEMORY_MIB=12288
VM_VCPUS=6
VM_DISK_SIZE_GIB=80
ONLINE_TIMEOUT_SECONDS=300
TASK_TIMEOUT_SECONDS=7200

for command_name in awk base64 chgrp chmod chown date flock grep head id install jq mktemp python3 qemu-img seq sha256sum sleep virsh virt-install wc; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing host command: %s\n' "${command_name}" >&2
        exit 1
    }
done
[[ -x "${LIBGUESTFS_HELPER}" ]] || { printf 'Missing immutable libguestfs helper.\n' >&2; exit 1; }
[[ -r "${NETWORK_HELPER}" ]] || { printf 'Missing immutable guest network helper.\n' >&2; exit 1; }
[[ -f "${GOLDEN_IMAGE}" && -f "${GOLDEN_PROVENANCE}" ]] || {
    printf 'Certified golden image or provenance missing.\n' >&2
    exit 1
}
[[ -c /dev/kvm ]] || { printf '/dev/kvm is missing on host.\n' >&2; exit 1; }

REQUEST_FILE="$(mktemp)"
SCRIPT_FILE="$(mktemp)"
trap 'rm -f "${REQUEST_FILE}" "${SCRIPT_FILE}"' EXIT INT TERM

head -c $((MAX_REQUEST_BYTES + 1)) > "${REQUEST_FILE}"
REQUEST_BYTES="$(wc -c < "${REQUEST_FILE}")"
(( REQUEST_BYTES > 0 && REQUEST_BYTES <= MAX_REQUEST_BYTES )) || {
    printf 'Invalid request size: %s\n' "${REQUEST_BYTES}" >&2
    exit 2
}
jq -e . "${REQUEST_FILE}" >/dev/null

SCHEMA="$(jq -r '.schema // empty' "${REQUEST_FILE}")"
TASK_ID="$(jq -r '.task_id // empty' "${REQUEST_FILE}")"
RUN_ID="$(jq -r '.run_id // empty' "${REQUEST_FILE}")"
SOURCE_COMMIT="$(jq -r '.source_commit // empty' "${REQUEST_FILE}")"

[[ "${SCHEMA}" == "1" ]] || { printf 'Unsupported request schema.\n' >&2; exit 2; }
[[ "${TASK_ID}" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || { printf 'Invalid task_id.\n' >&2; exit 2; }
[[ "${RUN_ID}" =~ ^[0-9]+$ ]] || { printf 'Invalid run_id.\n' >&2; exit 2; }
[[ "${SOURCE_COMMIT}" =~ ^[0-9a-f]{40}$ ]] || { printf 'Invalid source_commit.\n' >&2; exit 2; }

python3 - "${REQUEST_FILE}" "${SCRIPT_FILE}" <<'PY'
import json, sys
from pathlib import Path
request = json.loads(Path(sys.argv[1]).read_text())
script = request.get("script")
assert isinstance(script, str)
data = script.encode()
assert 0 < len(data) <= 500_000
assert b"\0" not in data
Path(sys.argv[2]).write_bytes(data)
PY
SCRIPT_BYTES="$(wc -c < "${SCRIPT_FILE}")"
SCRIPT_SHA256="$(sha256sum "${SCRIPT_FILE}" | awk '{print $1}')"

PROVENANCE_SHA256="$(awk -F= '$1 == "golden_image_sha256" {print $2; exit}' "${GOLDEN_PROVENANCE}")"
[[ "${PROVENANCE_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]] || {
    printf 'Golden provenance SHA-256 is missing or malformed.\n' >&2
    exit 1
}
grep -qx 'source_checkout_removed=yes' "${GOLDEN_PROVENANCE}" || {
    printf 'Golden provenance does not confirm source checkout cleanup.\n' >&2
    exit 1
}
GOLDEN_SHA256="$(sha256sum "${GOLDEN_IMAGE}" | awk '{print $1}')"
[[ "${GOLDEN_SHA256,,}" == "${PROVENANCE_SHA256,,}" ]] || {
    printf 'Golden image digest differs from provenance.\n' >&2
    exit 1
}

install -d -m 0755 "${STATE_ROOT}" "${RESULT_ROOT}"
LOCK_FILE="${STATE_ROOT}/.workspace.lock"
exec 9>"${LOCK_FILE}"
flock -n 9 || { printf 'Another workspace VM is active.\n' >&2; exit 1; }

RESULT_DIR="${RESULT_ROOT}/${RUN_ID}"
[[ ! -e "${RESULT_DIR}" ]] || { printf 'Result directory already exists: %s\n' "${RESULT_DIR}" >&2; exit 1; }
install -d -m 0700 "${RESULT_DIR}"

RUN_DIR="${STATE_ROOT}/${RUN_ID}"
install -d -m 0700 "${RUN_DIR}"
LIBVIRT_QEMU_GROUP="$(id -gn "${LIBVIRT_QEMU_USER}")"
chgrp "${LIBVIRT_QEMU_GROUP}" "${RUN_DIR}"
chmod 0710 "${RUN_DIR}"
OVERLAY="${RUN_DIR}/disk.qcow2"
VM_NAME="supralinux-workspace-${RUN_ID}"
VM_CREATED=0
TASK_STARTED=0
TASK_EXIT_CODE=125

# shellcheck disable=SC2329
cleanup() {
    local rc="$?"
    trap - EXIT INT TERM
    set +e
    rm -f "${REQUEST_FILE}" "${SCRIPT_FILE}"

    if (( VM_CREATED )); then
        virsh --connect "${LIBVIRT_URI}" dumpxml "${VM_NAME}" > "${RESULT_DIR}/domain.xml" 2>/dev/null || true
        virsh --connect "${LIBVIRT_URI}" shutdown "${VM_NAME}" >/dev/null 2>&1 || true
        for _ in $(seq 1 30); do
            if ! LC_ALL=C virsh --connect "${LIBVIRT_URI}" domstate "${VM_NAME}" 2>/dev/null | grep -Eq 'running|paused|in shutdown'; then
                break
            fi
            sleep 2
        done
        if LC_ALL=C virsh --connect "${LIBVIRT_URI}" domstate "${VM_NAME}" 2>/dev/null | grep -Eq 'running|paused|in shutdown'; then
            virsh --connect "${LIBVIRT_URI}" destroy "${VM_NAME}" >/dev/null 2>&1 || true
        fi

        install -d -m 0700 "${RESULT_DIR}/guest"
        "${LIBGUESTFS_HELPER}" virt-copy-out \
            -a "${OVERLAY}" /var/lib/supralinux/workspace "${RESULT_DIR}/guest" \
            > "${RESULT_DIR}/guest-copy-out.log" 2>&1 || true

        virsh --connect "${LIBVIRT_URI}" undefine "${VM_NAME}" >/dev/null 2>&1 || true
    fi

    if [[ -f "${OVERLAY}" ]]; then
        qemu-img info --output=json "${OVERLAY}" > "${RESULT_DIR}/overlay-info.json" 2>/dev/null || true
        sha256sum "${OVERLAY}" > "${RESULT_DIR}/overlay-sha256.txt" 2>/dev/null || true
        rm -f "${OVERLAY}"
    fi
    rmdir "${RUN_DIR}" >/dev/null 2>&1 || true

    jq -n \
        --arg task_id "${TASK_ID}" \
        --arg run_id "${RUN_ID}" \
        --arg source_commit "${SOURCE_COMMIT}" \
        --arg script_sha256 "${SCRIPT_SHA256}" \
        --arg golden_image_sha256 "${GOLDEN_SHA256}" \
        --argjson broker_exit_code "${rc}" \
        --argjson task_started "${TASK_STARTED}" \
        --argjson task_exit_code "${TASK_EXIT_CODE}" \
        '{
          schema:1,
          scope:"non-authoritative-disposable-workspace",
          task_id:$task_id,
          run_id:$run_id,
          source_commit:$source_commit,
          script_sha256:$script_sha256,
          golden_image_sha256:$golden_image_sha256,
          broker_exit_code:$broker_exit_code,
          task_started:($task_started == 1),
          task_exit_code:$task_exit_code,
          package_attempt_effect:"none"
        }' > "${RESULT_DIR}/host-result.json"

    (
        cd "${RESULT_DIR}" &&
        find . -type f ! -name evidence-sha256.txt -print0 |
            sort -z |
            xargs -0 sha256sum
    ) > "${RESULT_DIR}/evidence-sha256.txt" 2>/dev/null || true

    chown -R "${ORCHESTRATOR_USER}:$(id -gn "${ORCHESTRATOR_USER}")" "${RESULT_DIR}" 2>/dev/null || true
    chmod -R u+rwX,go-rwx "${RESULT_DIR}" 2>/dev/null || true

    exit "${rc}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if virsh --connect "${LIBVIRT_URI}" dominfo "${VM_NAME}" >/dev/null 2>&1; then
    printf 'Refusing pre-existing VM name: %s\n' "${VM_NAME}" >&2
    exit 1
fi

BACKING_FORMAT="$(qemu-img info --output=json "${GOLDEN_IMAGE}" | jq -r '.format')"
qemu-img create -f qcow2 -F "${BACKING_FORMAT}" -b "${GOLDEN_IMAGE}" "${OVERLAY}" >/dev/null
qemu-img resize "${OVERLAY}" "${VM_DISK_SIZE_GIB}G" >/dev/null
chgrp "${LIBVIRT_QEMU_GROUP}" "${OVERLAY}"
chmod 0660 "${OVERLAY}"

{
    printf 'scope=non-authoritative-disposable-workspace\n'
    printf 'task_id=%s\n' "${TASK_ID}"
    printf 'run_id=%s\n' "${RUN_ID}"
    printf 'source_commit=%s\n' "${SOURCE_COMMIT}"
    printf 'script_sha256=%s\n' "${SCRIPT_SHA256}"
    printf 'script_bytes=%s\n' "${SCRIPT_BYTES}"
    printf 'golden_image=%s\n' "${GOLDEN_IMAGE}"
    printf 'golden_image_sha256=%s\n' "${GOLDEN_SHA256}"
    printf 'vm_name=%s\n' "${VM_NAME}"
    printf 'host_payload_execution=no\n'
} > "${RESULT_DIR}/host-environment.txt"

VM_CREATED=1
virt-install \
    --connect "${LIBVIRT_URI}" \
    --name "${VM_NAME}" \
    --memory "${VM_MEMORY_MIB}" \
    --vcpus "${VM_VCPUS}" \
    --cpu host-passthrough \
    --qemu-commandline='-global host-x86_64-cpu.kvm-asyncpf=off -global host-x86_64-cpu.kvm-asyncpf-int=off' \
    --import \
    --disk "path=${OVERLAY},format=qcow2,bus=virtio,cache=none" \
    --network 'user,model=virtio,mac=52:54:00:53:55:01,link.state=down,xpath1.set=./ip/@family=ipv4,xpath2.set=./ip/@address=10.203.0.1,xpath3.set=./ip/@prefix=24' \
    --channel unix,target.type=virtio,target.name=org.qemu.guest_agent.0 \
    --graphics none \
    --noautoconsole \
    --osinfo detect=on,require=off

qga() {
    virsh --connect "${LIBVIRT_URI}" qemu-agent-command "${VM_NAME}" "$1"
}

qga_exec_status() {
    local payload="$1"
    local timeout_seconds="$2"
    local result pid status deadline
    result="$(qga "${payload}")"
    pid="$(jq -r '.return.pid // empty' <<<"${result}")"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
    deadline=$(( $(date +%s) + timeout_seconds ))
    while true; do
        status="$(qga "$(jq -nc --argjson pid "${pid}" '{execute:"guest-exec-status",arguments:{pid:$pid}}')")"
        if [[ "$(jq -r '.return.exited // false' <<<"${status}")" == "true" ]]; then
            printf '%s\n' "${status}"
            return 0
        fi
        (( $(date +%s) < deadline )) || return 124
        sleep 1
    done
}

DEADLINE=$(( $(date +%s) + ONLINE_TIMEOUT_SECONDS ))
until qga '{"execute":"guest-ping"}' >/dev/null 2>&1; do
    (( $(date +%s) < DEADLINE )) || { printf 'Timed out waiting for qemu-guest-agent.\n' >&2; exit 1; }
    sleep 2
done

network_payload() {
    local verify="$1"
    python3 - "${NETWORK_HELPER}" "${verify}" <<'PY'
import base64, json, sys
from pathlib import Path
source = base64.b64encode(Path(sys.argv[1]).read_bytes()).decode()
args = ["guest-network"] + (["--verify-network"] if sys.argv[2] == "1" else [])
code = "import base64,sys;sys.argv=%r;exec(compile(base64.b64decode(%r),'guest-network','exec'))" % (args, source)
print(json.dumps({"execute":"guest-exec","arguments":{"path":"/usr/bin/python3","arg":["-c",code],"capture-output":True}}))
PY
}

NETWORK_STATUS="$(qga_exec_status "$(network_payload 0)" 60)" || {
    printf 'Guest network policy failed.\n' >&2
    exit 1
}
printf '%s\n' "${NETWORK_STATUS}" > "${RESULT_DIR}/network-policy-execution.json"
[[ "$(jq -r '.return.exitcode // 1' <<<"${NETWORK_STATUS}")" == "0" ]] || exit 1
jq -er '.return["out-data"]' <<<"${NETWORK_STATUS}" | base64 -d > "${RESULT_DIR}/network-policy.json"
jq -e '.state == "PASS" and .host_network_modified == false and .private_ipv4_and_external_ipv6_blocked == true' \
    "${RESULT_DIR}/network-policy.json" >/dev/null

virsh --connect "${LIBVIRT_URI}" domif-setlink "${VM_NAME}" 52:54:00:53:55:01 up
virsh --connect "${LIBVIRT_URI}" dumpxml "${VM_NAME}" > "${RESULT_DIR}/domain-network-enabled.xml"

NETWORK_VERIFY_STATUS="$(qga_exec_status "$(network_payload 1)" 75)" || {
    printf 'Guest connectivity verification failed.\n' >&2
    exit 1
}
printf '%s\n' "${NETWORK_VERIFY_STATUS}" > "${RESULT_DIR}/network-connectivity-execution.json"
[[ "$(jq -r '.return.exitcode // 1' <<<"${NETWORK_VERIFY_STATUS}")" == "0" ]] || exit 1
jq -er '.return["out-data"]' <<<"${NETWORK_VERIFY_STATUS}" | base64 -d > "${RESULT_DIR}/network-connectivity.json"
jq -e '.state == "PASS" and .host_network_modified == false and .private_reject_counter_delta >= 2' \
    "${RESULT_DIR}/network-connectivity.json" >/dev/null

PREP_PAYLOAD="$(jq -nc '{
  execute:"guest-exec",
  arguments:{
    path:"/usr/bin/install",
    arg:["-d","-m","0700","/run/supralinux-workspace","/var/lib/supralinux/workspace","/var/lib/supralinux/workspace/artifacts"],
    "capture-output":true
  }
}')"
PREP_STATUS="$(qga_exec_status "${PREP_PAYLOAD}" 30)"
[[ "$(jq -r '.return.exitcode // 1' <<<"${PREP_STATUS}")" == "0" ]] || exit 1

GUEST_SCRIPT="/run/supralinux-workspace/task.sh"
OPEN_RESULT="$(qga "$(jq -nc --arg path "${GUEST_SCRIPT}" '{execute:"guest-file-open",arguments:{path:$path,mode:"w"}}')")"
HANDLE="$(jq -r '.return // empty' <<<"${OPEN_RESULT}")"
[[ "${HANDLE}" =~ ^[0-9]+$ ]] || { printf 'Could not open guest payload file.\n' >&2; exit 1; }

WRITTEN=0
while IFS= read -r CHUNK; do
    WRITE_RESULT="$(qga "$(jq -nc --argjson handle "${HANDLE}" --arg data "${CHUNK}" \
        '{execute:"guest-file-write",arguments:{handle:$handle,"buf-b64":$data}}')")"
    COUNT="$(jq -r '.return.count // 0' <<<"${WRITE_RESULT}")"
    [[ "${COUNT}" =~ ^[0-9]+$ ]] || exit 1
    WRITTEN=$((WRITTEN + COUNT))
done < <(python3 - "${SCRIPT_FILE}" <<'PY'
import base64, sys
from pathlib import Path
data = Path(sys.argv[1]).read_bytes()
for offset in range(0, len(data), 32768):
    print(base64.b64encode(data[offset:offset+32768]).decode())
PY
)
qga "$(jq -nc --argjson handle "${HANDLE}" '{execute:"guest-file-flush",arguments:{handle:$handle}}')" >/dev/null
qga "$(jq -nc --argjson handle "${HANDLE}" '{execute:"guest-file-close",arguments:{handle:$handle}}')" >/dev/null
[[ "${WRITTEN}" -eq "${SCRIPT_BYTES}" ]] || { printf 'Incomplete guest payload write.\n' >&2; exit 1; }

CHMOD_STATUS="$(qga_exec_status "$(jq -nc --arg path "${GUEST_SCRIPT}" \
    '{execute:"guest-exec",arguments:{path:"/usr/bin/chmod",arg:["0700",$path],"capture-output":true}}')" 30)"
[[ "$(jq -r '.return.exitcode // 1' <<<"${CHMOD_STATUS}")" == "0" ]] || exit 1

TASK_COMMAND="$(cat <<'TASK'
set +e
export SUPRALINUX_WORKSPACE_ROOT=/var/lib/supralinux/workspace
export SUPRALINUX_SOURCE_COMMIT="$2"
export SUPRALINUX_TASK_ID="$1"
cd /var/lib/supralinux/workspace
/bin/bash /run/supralinux-workspace/task.sh >stdout.log 2>stderr.log
rc=$?
printf '{"schema":1,"task_id":"%s","source_commit":"%s","exit_code":%d}\n' "$1" "$2" "$rc" > task-result.json
exit "$rc"
TASK
)"

TASK_PAYLOAD="$(jq -nc \
    --arg cmd "${TASK_COMMAND}" \
    --arg task "${TASK_ID}" \
    --arg source "${SOURCE_COMMIT}" \
    '{execute:"guest-exec",arguments:{path:"/bin/bash",arg:["-lc",$cmd,"supralinux-workspace",$task,$source],"capture-output":false}}')"
TASK_STARTED=1
set +e
TASK_STATUS="$(qga_exec_status "${TASK_PAYLOAD}" "${TASK_TIMEOUT_SECONDS}")"
TASK_POLL_RC=$?
set -e
if (( TASK_POLL_RC != 0 )); then
    TASK_EXIT_CODE=124
    printf 'Workspace task monitoring failed or timed out.\n' >&2
    exit 1
fi
TASK_EXIT_CODE="$(jq -r '.return.exitcode // 125' <<<"${TASK_STATUS}")"
[[ "${TASK_EXIT_CODE}" =~ ^[0-9]+$ ]] || TASK_EXIT_CODE=125

printf 'Workspace task %s completed with exit code %s\n' "${TASK_ID}" "${TASK_EXIT_CODE}"
printf 'source_commit=%s\n' "${SOURCE_COMMIT}"
printf 'script_sha256=%s\n' "${SCRIPT_SHA256}"

exit "${TASK_EXIT_CODE}"
