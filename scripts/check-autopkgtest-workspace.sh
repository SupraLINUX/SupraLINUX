#!/usr/bin/env bash
set -Eeuo pipefail

WORK_ROOT="${1:-${AUTOPKGTEST_QEMU_WORK_ROOT:-/var/lib/supralinux/autopkgtest/work}}"
MIN_FREE_BYTES="${AUTOPKGTEST_QEMU_MIN_WORK_FREE_BYTES:-21474836480}"

fail() {
    printf 'autopkgtest workspace: %s\n' "$*" >&2
    exit 1
}

for command_name in df findmnt; do
    command -v "${command_name}" >/dev/null 2>&1 || fail "missing required command: ${command_name}"
done

[[ -d "${WORK_ROOT}" ]] || fail "work root does not exist: ${WORK_ROOT}"
[[ -w "${WORK_ROOT}" ]] || fail "work root is not writable by the current user: ${WORK_ROOT}"
[[ "${MIN_FREE_BYTES}" =~ ^[0-9]+$ ]] || fail "minimum free bytes is not an unsigned integer: ${MIN_FREE_BYTES}"

FS_TYPE="$(findmnt -n -o FSTYPE -T "${WORK_ROOT}" 2>/dev/null || true)"
if [[ "${FS_TYPE}" == "tmpfs" || "${FS_TYPE}" == "ramfs" ]]; then
    fail "work root is memory-backed (${FS_TYPE}); use persistent guest storage instead of /tmp"
fi

FREE_BYTES="$(df -B1 --output=avail "${WORK_ROOT}" | tail -n 1 | tr -d '[:space:]')"
[[ "${FREE_BYTES}" =~ ^[0-9]+$ ]] || fail "could not determine available bytes for ${WORK_ROOT}"
if (( FREE_BYTES < MIN_FREE_BYTES )); then
    fail "insufficient free space in ${WORK_ROOT}: available=${FREE_BYTES} required=${MIN_FREE_BYTES}"
fi

printf 'work_root=%s\n' "${WORK_ROOT}"
printf 'filesystem_type=%s\n' "${FS_TYPE:-unknown}"
printf 'free_bytes=%s\n' "${FREE_BYTES}"
printf 'minimum_free_bytes=%s\n' "${MIN_FREE_BYTES}"
printf 'status=PASS\n'
