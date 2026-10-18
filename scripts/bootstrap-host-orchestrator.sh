#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY="SupraLINUX/SupraLINUX"
RUNNER_USER="supralinux-orchestrator"
RUNNER_HOME="/var/lib/supralinux/host-runner"
RUNNER_DIR="/opt/supralinux-host-runner"
RUNNER_NAME="supralinux-host-orchestrator-$(hostname -s)"
BROKER="/usr/local/libexec/supralinux-vm-workspace-broker"
NETWORK_HELPER="/usr/local/libexec/supralinux-configure-kvm-guest-network.py"
LIBGUESTFS_HELPER="/usr/local/libexec/supralinux-with-libguestfs-runtime"
SUDOERS="/etc/sudoers.d/supralinux-host-orchestrator"
EVIDENCE_ROOT="/var/lib/supralinux/evidence/host-orchestrator-bootstrap"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${RUN_ID}"

[[ "${EUID}" -ne 0 ]] || {
    printf 'Run this bootstrap as the normal host user, not as root.\n' >&2
    exit 1
}

for command_name in gh git jq sudo visudo; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

cd "${ROOT}"
git diff --quiet
git diff --cached --quiet
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] || {
    printf 'Bootstrap requires a clean checkout.\n' >&2
    exit 1
}
gh auth status --hostname github.com >/dev/null

printf '=== Host orchestrator bootstrap ===\n'
printf 'repository=%s\n' "${REPOSITORY}"
printf 'runner_name=%s\n' "${RUNNER_NAME}"

if ! id "${RUNNER_USER}" >/dev/null 2>&1; then
    sudo useradd \
        --system \
        --create-home \
        --home-dir "${RUNNER_HOME}" \
        --shell /bin/bash \
        "${RUNNER_USER}"
fi

for forbidden_group in sudo kvm libvirt libvirt-qemu; do
    if id -nG "${RUNNER_USER}" | tr ' ' '\n' | grep -qx "${forbidden_group}"; then
        printf 'Runner user unexpectedly belongs to privileged group: %s\n' "${forbidden_group}" >&2
        exit 1
    fi
done

sudo install -d -o root -g root -m 0755 /usr/local/libexec
sudo install -o root -g root -m 0755 \
    "${ROOT}/scripts/supralinux-vm-workspace-broker.sh" "${BROKER}"
sudo install -o root -g root -m 0644 \
    "${ROOT}/scripts/configure-kvm-guest-network.py" "${NETWORK_HELPER}"
sudo install -o root -g root -m 0755 \
    "${ROOT}/scripts/with-libguestfs-runtime.sh" "${LIBGUESTFS_HELPER}"

SUDOERS_TMP="$(mktemp)"
trap 'rm -f "${SUDOERS_TMP}"' EXIT
printf '%s ALL=(root) NOPASSWD: %s\n' "${RUNNER_USER}" "${BROKER}" > "${SUDOERS_TMP}"
sudo install -o root -g root -m 0440 "${SUDOERS_TMP}" "${SUDOERS}"
sudo visudo -cf "${SUDOERS}"
rm -f "${SUDOERS_TMP}"
trap - EXIT

if ! sudo test -f "${RUNNER_DIR}/.runner"; then
    SUPRALINUX_RUNNER_USER="${RUNNER_USER}" \
    SUPRALINUX_ACTIONS_RUNNER_DIR="${RUNNER_DIR}" \
    SUPRALINUX_EVIDENCE_DIR="${EVIDENCE_ROOT}" \
        "${ROOT}/scripts/install-actions-runner.sh"

    REGISTRATION_TOKEN="$(gh api \
        --method POST \
        "repos/${REPOSITORY}/actions/runners/registration-token" \
        --jq '.token')"
    [[ -n "${REGISTRATION_TOKEN}" ]] || {
        printf 'Could not obtain a repository runner registration token.\n' >&2
        exit 1
    }

    sudo -u "${RUNNER_USER}" -H bash -c '
        set -euo pipefail
        cd "$1"
        shift
        exec ./config.sh "$@"
    ' bash "${RUNNER_DIR}" \
        --unattended \
        --url "https://github.com/${REPOSITORY}" \
        --token "${REGISTRATION_TOKEN}" \
        --name "${RUNNER_NAME}" \
        --labels "supralinux-host-orchestrator" \
        --work "_work" \
        --replace
    unset REGISTRATION_TOKEN
fi

if ! sudo test -f "${RUNNER_DIR}/.service"; then
    sudo bash -c '
        set -euo pipefail
        cd "$1"
        exec ./svc.sh install "$2"
    ' bash "${RUNNER_DIR}" "${RUNNER_USER}"
fi

sudo bash -c '
    set -euo pipefail
    cd "$1"
    exec ./svc.sh start
' bash "${RUNNER_DIR}"

sudo install -d -o root -g root -m 0755 "${EVIDENCE_ROOT}"
sudo install -d -o "${RUNNER_USER}" -g "$(id -gn "${RUNNER_USER}")" -m 0700 \
    /var/lib/supralinux/workspace-results

sudo -l -U "${RUNNER_USER}" | grep -F "${BROKER}" >/dev/null
sudo -u "${RUNNER_USER}" -H sudo -n -l | grep -F "(root) NOPASSWD: ${BROKER}" >/dev/null

DEADLINE=$(( $(date +%s) + 90 ))
while true; do
    RUNNER_JSON="$(gh api "repos/${REPOSITORY}/actions/runners?per_page=100" \
        --jq ".runners[] | select(.name == \"${RUNNER_NAME}\") | {id,name,status,busy,labels}")"
    if [[ -n "${RUNNER_JSON}" ]] && jq -e \
        '.status == "online" and any(.labels[]; .name == "supralinux-host-orchestrator")' \
        <<<"${RUNNER_JSON}" >/dev/null; then
        break
    fi
    (( $(date +%s) < DEADLINE )) || {
        printf 'Runner did not become online within the bootstrap window.\n' >&2
        exit 1
    }
    sleep 3
done

sudo install -d -o "${USER}" -g "$(id -gn)" -m 0700 "${EVIDENCE_DIR}"
{
    printf 'state=PASS\n'
    printf 'installed_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'repository=%s\n' "${REPOSITORY}"
    printf 'runner_user=%s\n' "${RUNNER_USER}"
    printf 'runner_name=%s\n' "${RUNNER_NAME}"
    printf 'runner_dir=%s\n' "${RUNNER_DIR}"
    printf 'broker=%s\n' "${BROKER}"
    printf 'runner_privileged_groups=none\n'
    printf 'sudo_scope=%s\n' "${BROKER}"
    printf 'payload_execution_boundary=disposable-kvm-only\n'
    printf 'checkout_head=%s\n' "$(git rev-parse HEAD)"
} > "${EVIDENCE_DIR}/result.txt"
printf '%s\n' "${RUNNER_JSON}" > "${EVIDENCE_DIR}/runner.json"
sha256sum "${BROKER}" "${NETWORK_HELPER}" "${LIBGUESTFS_HELPER}" \
    > "${EVIDENCE_DIR}/installed-files.sha256"

printf '\nHOST_ORCHESTRATOR_BOOTSTRAP=PASS\n'
printf 'RUNNER_NAME=%s\n' "${RUNNER_NAME}"
printf 'RUNNER_STATUS=online\n'
printf 'RUNNER_USER=%s\n' "${RUNNER_USER}"
printf 'PAYLOAD_EXECUTION_BOUNDARY=disposable-kvm-only\n'
printf 'EVIDENCE_DIR=%s\n' "${EVIDENCE_DIR}"
