#!/usr/bin/env bash
set -Eeuo pipefail

KERNEL_VERSION="${SUPRALINUX_LIBGUESTFS_KERNEL_VERSION:-$(uname -r)}"
SOURCE_KERNEL="${SUPRALINUX_LIBGUESTFS_SOURCE_KERNEL:-/boot/vmlinuz-${KERNEL_VERSION}}"
MODULES_PATH="${SUPRALINUX_LIBGUESTFS_MODULES:-/lib/modules/${KERNEL_VERSION}}"
RUNTIME_ROOT="${SUPRALINUX_LIBGUESTFS_RUNTIME_ROOT:-/var/lib/supralinux/images/libguestfs-runtime}"
RUNTIME_DIR="${RUNTIME_ROOT}/${KERNEL_VERSION}"
KERNEL_COPY="${RUNTIME_DIR}/vmlinuz"
CACHE_DIR="${RUNTIME_DIR}/cache"
PROVENANCE="${RUNTIME_DIR}/provenance.txt"

fail(){ printf 'libguestfs runtime: %s\n' "$*" >&2; exit 1; }
field(){ local key="$1" count; count="$(grep -c "^${key}=" "${PROVENANCE}" 2>/dev/null || true)"; [[ "${count}" -eq 1 ]] || fail "provenance field must occur exactly once: ${key}"; sed -n "s/^${key}=//p" "${PROVENANCE}"; }

[[ -f "${SOURCE_KERNEL}" ]] || fail "host kernel image is missing: ${SOURCE_KERNEL}"
[[ -d "${MODULES_PATH}" && -f "${MODULES_PATH}/modules.dep" ]] || fail "kernel modules are incomplete: ${MODULES_PATH}"
[[ -f "${PROVENANCE}" ]] || fail "prepared runtime provenance is missing: ${PROVENANCE}"
[[ -r "${KERNEL_COPY}" ]] || fail "prepared private kernel is missing/unreadable: ${KERNEL_COPY}"

RECORDED_VERSION="$(field kernel_version)"
RECORDED_SOURCE="$(field source_kernel)"
RECORDED_SOURCE_STAT="$(field source_kernel_stat)"
RECORDED_KERNEL_SHA256="$(field kernel_sha256)"
RECORDED_MODULES="$(field modules_path)"
RECORDED_MODULES_DEP_SHA256="$(field modules_dep_sha256)"

[[ "${RECORDED_VERSION}" == "${KERNEL_VERSION}" ]] || fail "prepared kernel version is stale; run scripts/prepare-libguestfs-runtime.sh"
[[ "${RECORDED_SOURCE}" == "${SOURCE_KERNEL}" ]] || fail "prepared source-kernel path does not match current contract"
[[ "${RECORDED_MODULES}" == "${MODULES_PATH}" ]] || fail "prepared modules path does not match current contract"

CURRENT_SOURCE_STAT="$(stat -c '%s:%Y:%Z:%i' "${SOURCE_KERNEL}")"
[[ "${CURRENT_SOURCE_STAT}" == "${RECORDED_SOURCE_STAT}" ]] || fail "host kernel metadata changed; rerun scripts/prepare-libguestfs-runtime.sh"
CURRENT_KERNEL_SHA256="$(sha256sum "${KERNEL_COPY}" | awk '{print $1}')"
[[ "${CURRENT_KERNEL_SHA256}" == "${RECORDED_KERNEL_SHA256}" ]] || fail "private kernel copy hash mismatch; rerun scripts/prepare-libguestfs-runtime.sh"
CURRENT_MODULES_DEP_SHA256="$(sha256sum "${MODULES_PATH}/modules.dep" | awk '{print $1}')"
[[ "${CURRENT_MODULES_DEP_SHA256}" == "${RECORDED_MODULES_DEP_SHA256}" ]] || fail "kernel modules changed; rerun scripts/prepare-libguestfs-runtime.sh"

mkdir -p "${CACHE_DIR}"
chmod 0700 "${RUNTIME_DIR}" "${CACHE_DIR}"
export SUPERMIN_KERNEL="${KERNEL_COPY}"
export SUPERMIN_KERNEL_VERSION="${KERNEL_VERSION}"
export SUPERMIN_MODULES="${MODULES_PATH}"
export LIBGUESTFS_CACHEDIR="${CACHE_DIR}"

if [[ "${1:-}" == "--describe" ]]; then
    printf 'kernel_version=%s\nsource_kernel=%s\nsource_kernel_stat=%s\nkernel_copy=%s\nkernel_sha256=%s\nmodules_path=%s\nmodules_dep_sha256=%s\ncache_dir=%s\n'       "${KERNEL_VERSION}" "${SOURCE_KERNEL}" "${CURRENT_SOURCE_STAT}" "${KERNEL_COPY}" "${CURRENT_KERNEL_SHA256}" "${MODULES_PATH}" "${CURRENT_MODULES_DEP_SHA256}" "${CACHE_DIR}"
    exit 0
fi
(( $# > 0 )) || fail 'usage: with-libguestfs-runtime.sh command [args...]'
exec "$@"
