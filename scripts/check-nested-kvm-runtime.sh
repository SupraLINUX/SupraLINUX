#!/usr/bin/env bash
set -Eeuo pipefail

EVIDENCE_PATH="${1:-/tmp/supralinux-nested-kvm-runtime.txt}"
PROBE_SECONDS="${SUPRALINUX_KVM_PROBE_SECONDS:-2}"

if [[ ! "${PROBE_SECONDS}" =~ ^[1-9][0-9]*$ ]]; then
    printf 'SUPRALINUX_KVM_PROBE_SECONDS must be a positive integer.\n' >&2
    exit 2
fi

for command_name in qemu-system-x86_64 timeout; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ ! -c /dev/kvm || ! -r /dev/kvm || ! -w /dev/kvm ]]; then
    printf '/dev/kvm is not readable/writable by the current user.\n' >&2
    exit 1
fi

mkdir -p "$(dirname "${EVIDENCE_PATH}")"

{
    printf 'checked_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'user=%s\n' "${USER}"
    printf 'kernel=%s\n' "$(uname -r)"
    printf 'virtualization=%s\n' "$(systemd-detect-virt --vm 2>/dev/null || printf 'unknown')"
    printf 'kvm_device='; ls -l /dev/kvm
    printf 'qemu_version='; qemu-system-x86_64 --version | head -1
    for nested in /sys/module/kvm_intel/parameters/nested /sys/module/kvm_amd/parameters/nested; do
        if [[ -r "${nested}" ]]; then
            printf '%s=' "${nested}"
            cat "${nested}"
        fi
    done
    printf 'probe_command=qemu-system-x86_64 -machine q35 -accel kvm -cpu host -m 128 -smp 1 -nodefaults -display none -serial none -monitor none -S\n'
} > "${EVIDENCE_PATH}"

set +e
timeout --signal=TERM --kill-after=2s "${PROBE_SECONDS}s" \
    qemu-system-x86_64 \
    -machine q35 \
    -accel kvm \
    -cpu host \
    -m 128 \
    -smp 1 \
    -nodefaults \
    -display none \
    -serial none \
    -monitor none \
    -S \
    >> "${EVIDENCE_PATH}" 2>&1
RC=$?
set -e

printf 'probe_exit_code=%d\n' "${RC}" >> "${EVIDENCE_PATH}"

# A successfully initialized, paused QEMU process has no natural exit here;
# timeout(1) terminating it after the probe window is therefore the expected PASS result.
if [[ "${RC}" -ne 124 ]]; then
    printf 'nested_kvm_runtime=FAIL\n' >> "${EVIDENCE_PATH}"
    printf 'Nested KVM runtime probe failed (QEMU exit %d). Evidence: %s\n' "${RC}" "${EVIDENCE_PATH}" >&2
    exit 1
fi

printf 'nested_kvm_runtime=PASS\n' >> "${EVIDENCE_PATH}"
printf 'Nested KVM runtime probe: PASS (%s)\n' "${EVIDENCE_PATH}"
