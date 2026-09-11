#!/usr/bin/env bash
set -Eeuo pipefail

LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
LIBVIRT_NETWORK="${SUPRALINUX_LIBVIRT_NETWORK:-default}"
FAILED=0

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    FAILED=1
}

pass() {
    printf 'PASS: %s\n' "$*"
}

printf '=== SupraLINUX KVM host preflight ===\n'
printf 'checked_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'user=%s\n' "${USER}"
printf 'kernel=%s\n' "$(uname -r)"
printf 'architecture=%s\n' "$(uname -m)"
printf 'outer_virtualization=%s\n' "$(systemd-detect-virt --vm 2>/dev/null || printf 'none')"

if [[ "$(uname -m)" != "x86_64" ]]; then
    fail 'current authoritative host recipe requires x86_64/amd64'
else
    pass 'host architecture is x86_64'
fi

if grep -Eq '\b(vmx|svm)\b' /proc/cpuinfo; then
    pass 'CPU virtualization extension is visible (vmx/svm)'
else
    fail 'vmx/svm is not visible; verify CPU/BIOS virtualization settings or outer hypervisor exposure'
fi

if [[ -c /dev/kvm ]]; then
    pass '/dev/kvm exists'
else
    fail '/dev/kvm is missing'
fi
if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    pass '/dev/kvm is readable/writable by the current user'
else
    fail '/dev/kvm is not readable/writable by the current user; a new login may be required after kvm-group provisioning'
fi

if grep -qw kvm <<<"$(id -nG)"; then
    pass 'current user belongs to kvm group'
else
    fail 'current user is not in kvm group'
fi
if grep -qw libvirt <<<"$(id -nG)"; then
    pass 'current user belongs to libvirt group'
else
    fail 'current user is not in libvirt group'
fi

NESTED_FILE=""
if [[ -r /sys/module/kvm_intel/parameters/nested ]]; then
    NESTED_FILE=/sys/module/kvm_intel/parameters/nested
elif [[ -r /sys/module/kvm_amd/parameters/nested ]]; then
    NESTED_FILE=/sys/module/kvm_amd/parameters/nested
fi

if [[ -n "${NESTED_FILE}" ]]; then
    NESTED_VALUE="$(tr '[:lower:]' '[:upper:]' < "${NESTED_FILE}" | tr -d '[:space:]')"
    printf 'nested_parameter=%s\n' "${NESTED_FILE}"
    printf 'nested_value=%s\n' "${NESTED_VALUE}"
    case "${NESTED_VALUE}" in
        Y|1) pass 'nested KVM is enabled in the loaded vendor KVM module' ;;
        *) fail "nested KVM is not enabled (${NESTED_FILE}=${NESTED_VALUE})" ;;
    esac
else
    fail 'could not read kvm_intel/kvm_amd nested parameter'
fi

required=(
    virsh
    virt-install
    virt-cat
    virt-copy-out
    virt-sysprep
    qemu-img
    qemu-system-x86_64
    genisoimage
    curl
    jq
    base64
    sha256sum
    gpgv
)
for command_name in "${required[@]}"; do
    if command -v "${command_name}" >/dev/null 2>&1; then
        pass "command available: ${command_name}"
    else
        fail "missing command: ${command_name}"
    fi
done

if command -v qemu-system-x86_64 >/dev/null 2>&1; then
    if qemu-system-x86_64 -accel help 2>&1 | grep -q '^kvm$'; then
        pass 'QEMU exposes KVM accelerator'
    else
        fail 'QEMU does not expose KVM accelerator'
    fi
fi

if command -v virsh >/dev/null 2>&1; then
    if virsh --connect "${LIBVIRT_URI}" uri >/dev/null 2>&1; then
        pass "libvirt system connection works (${LIBVIRT_URI})"
        net_info="$(mktemp)"
        if virsh --connect "${LIBVIRT_URI}" net-info "${LIBVIRT_NETWORK}" > "${net_info}" 2>/dev/null; then
            if grep -Eq '^Active:[[:space:]]+yes$' "${net_info}"; then
                pass "libvirt network is active: ${LIBVIRT_NETWORK}"
            else
                fail "libvirt network exists but is not active: ${LIBVIRT_NETWORK}"
            fi
        else
            fail "libvirt network is unavailable: ${LIBVIRT_NETWORK}"
        fi
        rm -f "${net_info}"
    else
        fail "cannot connect to libvirt system URI: ${LIBVIRT_URI}"
    fi
fi

if (( FAILED )); then
    printf 'KVM host preflight: FAIL\n' >&2
    exit 1
fi
printf 'KVM host preflight: PASS\n'
