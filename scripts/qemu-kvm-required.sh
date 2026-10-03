#!/usr/bin/env bash
set -Eeuo pipefail

QEMU="${SUPRALINUX_QEMU_SYSTEM_X86_64:-/usr/bin/qemu-system-x86_64}"

if [[ ! -x "${QEMU}" ]]; then
    printf 'Required QEMU executable is missing or not executable: %s\n' "${QEMU}" >&2
    exit 127
fi

normalize_machine() {
    local value="$1"
    local field
    local seen_accel=0
    local -a fields normalized=()

    IFS=',' read -r -a fields <<< "${value}"
    for field in "${fields[@]}"; do
        if [[ "${field}" == accel=* ]]; then
            normalized+=("accel=kvm")
            seen_accel=1
        else
            normalized+=("${field}")
        fi
    done

    if (( ! seen_accel )); then
        normalized+=("accel=kvm")
    fi

    local IFS=,
    printf '%s' "${normalized[*]}"
}

args=("$@")
machine_present=0

for arg in "${args[@]}"; do
    case "${arg}" in
        -machine|-M|-machine=*|-M=*)
            machine_present=1
            ;;
    esac
done

normalized_args=()

for ((i=0; i<${#args[@]}; i++)); do
    arg="${args[i]}"
    case "${arg}" in
        -enable-kvm)
            # autopkgtest 5.55 adds this automatically when /dev/kvm exists.
            # Drop it here because this wrapper emits one canonical KVM selector.
            ;;
        -accel)
            if (( i + 1 >= ${#args[@]} )); then
                printf 'QEMU -accel option is missing its value.\n' >&2
                exit 2
            fi
            ((i+=1))
            ;;
        -accel=*)
            ;;
        -machine|-M)
            if (( i + 1 >= ${#args[@]} )); then
                printf 'QEMU %s option is missing its value.\n' "${arg}" >&2
                exit 2
            fi
            machine_value="$(normalize_machine "${args[i+1]}")"
            normalized_args+=("${arg}" "${machine_value}")
            ((i+=1))
            ;;
        -machine=*|-M=*)
            prefix="${arg%%=*}"
            machine_value="$(normalize_machine "${arg#*=}")"
            normalized_args+=("${prefix}=${machine_value}")
            ;;
        *)
            normalized_args+=("${arg}")
            ;;
    esac
done

if (( ! machine_present )); then
    normalized_args=("-accel" "kvm" "${normalized_args[@]}")
fi

exec "${QEMU}" "${normalized_args[@]}"
