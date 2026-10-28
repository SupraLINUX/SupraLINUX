#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISK="${1:-}"
EVIDENCE_DIR="${2:-}"
CHANNEL_HELPER="${ROOT}/scripts/golden-bootstrap-channel.py"
NETWORK_HELPER="${ROOT}/scripts/configure-golden-bootstrap-network.py"
GUARD_UNIT="${ROOT}/ops/golden-bootstrap/supralinux-golden-bootstrap-guard.service"
VERIFY_UNIT="${ROOT}/ops/golden-bootstrap/supralinux-golden-bootstrap-verify.service"

if [[ -z "${DISK}" || -z "${EVIDENCE_DIR}" ]]; then
    printf 'Usage: %s DISK EVIDENCE_DIR\n' "$0" >&2
    exit 2
fi
if [[ ! -f "${DISK}" ]]; then
    printf 'Golden bootstrap injection disk is missing: %s\n' "${DISK}" >&2
    exit 1
fi
for path in "${CHANNEL_HELPER}" "${NETWORK_HELPER}" "${GUARD_UNIT}" "${VERIFY_UNIT}"; do
    [[ -f "${path}" ]] || {
        printf 'Golden bootstrap injection input is missing: %s\n' "${path}" >&2
        exit 1
    }
done
command -v virt-customize >/dev/null 2>&1 || {
    printf 'Missing host command: virt-customize\n' >&2
    exit 1
}

mkdir -p "${EVIDENCE_DIR}"
LOG="${EVIDENCE_DIR}/bootstrap-injection.log"
RESULT="${EVIDENCE_DIR}/bootstrap-injection.txt"
INPUTS="${EVIDENCE_DIR}/bootstrap-injection-inputs.sha256"

sha256sum \
    "${CHANNEL_HELPER}" \
    "${NETWORK_HELPER}" \
    "${GUARD_UNIT}" \
    "${VERIFY_UNIT}" \
    > "${INPUTS}"

"${ROOT}/scripts/with-libguestfs-runtime.sh" virt-customize \
    --no-network \
    -a "${DISK}" \
    --mkdir /usr/local/libexec \
    --upload "${NETWORK_HELPER}:/usr/local/libexec/supralinux-configure-golden-bootstrap-network.py" \
    --chmod 0755:/usr/local/libexec/supralinux-configure-golden-bootstrap-network.py \
    --upload "${CHANNEL_HELPER}:/usr/local/libexec/supralinux-golden-bootstrap-channel.py" \
    --chmod 0755:/usr/local/libexec/supralinux-golden-bootstrap-channel.py \
    --upload "${GUARD_UNIT}:/etc/systemd/system/supralinux-golden-bootstrap-guard.service" \
    --chmod 0644:/etc/systemd/system/supralinux-golden-bootstrap-guard.service \
    --upload "${VERIFY_UNIT}:/etc/systemd/system/supralinux-golden-bootstrap-verify.service" \
    --chmod 0644:/etc/systemd/system/supralinux-golden-bootstrap-verify.service \
    --mkdir /etc/systemd/system/sysinit.target.wants \
    --mkdir /etc/systemd/system/multi-user.target.wants \
    --run-command 'set -eu; PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH; command -v python3 >/dev/null; command -v nft >/dev/null; command -v tc >/dev/null; ln -sfn ../supralinux-golden-bootstrap-guard.service /etc/systemd/system/sysinit.target.wants/supralinux-golden-bootstrap-guard.service; ln -sfn ../supralinux-golden-bootstrap-verify.service /etc/systemd/system/multi-user.target.wants/supralinux-golden-bootstrap-verify.service' \
    |& tee "${LOG}"

{
    printf 'state=PASS\n'
    printf 'scope=offline-golden-bootstrap-guard-injection\n'
    printf 'disk=%s\n' "${DISK}"
    printf 'libguestfs_network=disabled\n'
    printf 'bootstrap_transport=virtio-serial-unix-channel\n'
    printf 'host_network_modified=no\n'
    printf 'package_attempt_effect=none\n'
} > "${RESULT}"

printf 'Golden bootstrap guard injection: PASS\n'
