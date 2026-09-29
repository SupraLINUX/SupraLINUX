#!/usr/bin/env bash
set -Eeuo pipefail

QEMU="${SUPRALINUX_QEMU_SYSTEM_X86_64:-/usr/bin/qemu-system-x86_64}"

if [[ ! -x "${QEMU}" ]]; then
    printf 'Required QEMU executable is missing or not executable: %s\n' "${QEMU}" >&2
    exit 127
fi

exec "${QEMU}" -accel kvm "$@"
