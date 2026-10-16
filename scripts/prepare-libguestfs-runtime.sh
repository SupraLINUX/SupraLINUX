#!/usr/bin/env bash
set -Eeuo pipefail

TARGET_USER="${SUPRALINUX_HOST_USER:-${SUDO_USER:-${USER}}}"
KERNEL_VERSION="${SUPRALINUX_LIBGUESTFS_KERNEL_VERSION:-$(uname -r)}"
SOURCE_KERNEL="${SUPRALINUX_LIBGUESTFS_SOURCE_KERNEL:-/boot/vmlinuz-${KERNEL_VERSION}}"
MODULES_PATH="${SUPRALINUX_LIBGUESTFS_MODULES:-/lib/modules/${KERNEL_VERSION}}"
RUNTIME_ROOT="${SUPRALINUX_LIBGUESTFS_RUNTIME_ROOT:-/var/lib/supralinux/images/libguestfs-runtime}"
RUNTIME_DIR="${RUNTIME_ROOT}/${KERNEL_VERSION}"
KERNEL_COPY="${RUNTIME_DIR}/vmlinuz"
CACHE_DIR="${RUNTIME_DIR}/cache"
PROVENANCE="${RUNTIME_DIR}/provenance.txt"

if [[ "${EUID}" -eq 0 && -z "${SUDO_USER:-}" && -z "${SUPRALINUX_HOST_USER:-}" ]]; then
    printf 'Run as the intended host orchestration user with sudo access, or set SUPRALINUX_HOST_USER.\n' >&2
    exit 1
fi
id "${TARGET_USER}" >/dev/null 2>&1 || { printf 'Host orchestration user does not exist: %s\n' "${TARGET_USER}" >&2; exit 1; }
TARGET_GROUP="$(id -gn "${TARGET_USER}")"

for command_name in id install sha256sum stat sudo; do
    command -v "${command_name}" >/dev/null 2>&1 || { printf 'Missing host command: %s\n' "${command_name}" >&2; exit 1; }
done

[[ -f "${SOURCE_KERNEL}" ]] || { printf 'Current host kernel image is missing: %s\n' "${SOURCE_KERNEL}" >&2; exit 1; }
[[ -d "${MODULES_PATH}" && -f "${MODULES_PATH}/modules.dep" ]] || { printf 'Current host kernel modules are incomplete: %s\n' "${MODULES_PATH}" >&2; exit 1; }

install -d -m 0700 "${RUNTIME_ROOT}" "${RUNTIME_DIR}" "${CACHE_DIR}"

SOURCE_KERNEL_STAT="$(stat -c '%s:%Y:%Z:%i' "${SOURCE_KERNEL}")"
SOURCE_KERNEL_SHA256="$(sudo sha256sum "${SOURCE_KERNEL}" | awk '{print $1}')"
MODULES_DEP_SHA256="$(sha256sum "${MODULES_PATH}/modules.dep" | awk '{print $1}')"

KERNEL_TMP="${RUNTIME_DIR}/vmlinuz.tmp.$$"
trap 'rm -f "${KERNEL_TMP}"' EXIT
sudo install -o "${TARGET_USER}" -g "${TARGET_GROUP}" -m 0600 "${SOURCE_KERNEL}" "${KERNEL_TMP}"
COPY_SHA256="$(sha256sum "${KERNEL_TMP}" | awk '{print $1}')"
[[ "${COPY_SHA256}" == "${SOURCE_KERNEL_SHA256}" ]] || { printf 'Private libguestfs kernel copy does not match the host kernel.\n' >&2; exit 1; }
mv -f "${KERNEL_TMP}" "${KERNEL_COPY}"
trap - EXIT

PROVENANCE_TMP="${RUNTIME_DIR}/provenance.tmp.$$"
{
    printf 'prepared_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'host_user=%s\n' "${TARGET_USER}"
    printf 'kernel_version=%s\n' "${KERNEL_VERSION}"
    printf 'source_kernel=%s\n' "${SOURCE_KERNEL}"
    printf 'source_kernel_stat=%s\n' "${SOURCE_KERNEL_STAT}"
    printf 'kernel_sha256=%s\n' "${SOURCE_KERNEL_SHA256}"
    printf 'modules_path=%s\n' "${MODULES_PATH}"
    printf 'modules_dep_sha256=%s\n' "${MODULES_DEP_SHA256}"
    printf 'kernel_copy=%s\n' "${KERNEL_COPY}"
    printf 'cache_dir=%s\n' "${CACHE_DIR}"
} > "${PROVENANCE_TMP}"
chmod 0600 "${PROVENANCE_TMP}"
mv -f "${PROVENANCE_TMP}" "${PROVENANCE}"

printf 'Prepared private libguestfs kernel runtime: %s\n' "${RUNTIME_DIR}"
printf 'Kernel version: %s\n' "${KERNEL_VERSION}"
printf 'Kernel SHA-256: %s\n' "${SOURCE_KERNEL_SHA256}"
printf 'Provenance: %s\n' "${PROVENANCE}"
