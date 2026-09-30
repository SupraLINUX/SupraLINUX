#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${ROOT}/scripts/with-libguestfs-runtime.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
KVER=test-kernel
SOURCE="${TMP}/source-vmlinuz"
MODULES="${TMP}/modules"
RUNTIME="${TMP}/runtime"
DIR="${RUNTIME}/${KVER}"
mkdir -p "${MODULES}" "${DIR}/cache"
printf 'kernel-bytes\n' > "${SOURCE}"
printf 'modules-dep\n' > "${MODULES}/modules.dep"
cp "${SOURCE}" "${DIR}/vmlinuz"
chmod 0600 "${DIR}/vmlinuz"
SOURCE_STAT="$(stat -c '%s:%Y:%Z:%i' "${SOURCE}")"
KERNEL_SHA="$(sha256sum "${DIR}/vmlinuz" | awk '{print $1}')"
MODULES_SHA="$(sha256sum "${MODULES}/modules.dep" | awk '{print $1}')"
cat > "${DIR}/provenance.txt" <<EOF
kernel_version=${KVER}
source_kernel=${SOURCE}
source_kernel_stat=${SOURCE_STAT}
kernel_sha256=${KERNEL_SHA}
modules_path=${MODULES}
modules_dep_sha256=${MODULES_SHA}
EOF
OUT="$(SUPRALINUX_LIBGUESTFS_KERNEL_VERSION="${KVER}" SUPRALINUX_LIBGUESTFS_SOURCE_KERNEL="${SOURCE}" SUPRALINUX_LIBGUESTFS_MODULES="${MODULES}" SUPRALINUX_LIBGUESTFS_RUNTIME_ROOT="${RUNTIME}" "${WRAPPER}" /usr/bin/env)"
grep -qx "SUPERMIN_KERNEL=${DIR}/vmlinuz" <<<"${OUT}"
grep -qx "SUPERMIN_KERNEL_VERSION=${KVER}" <<<"${OUT}"
grep -qx "SUPERMIN_MODULES=${MODULES}" <<<"${OUT}"
grep -qx "LIBGUESTFS_CACHEDIR=${DIR}/cache" <<<"${OUT}"
printf 'changed\n' >> "${SOURCE}"
set +e
SUPRALINUX_LIBGUESTFS_KERNEL_VERSION="${KVER}" SUPRALINUX_LIBGUESTFS_SOURCE_KERNEL="${SOURCE}" SUPRALINUX_LIBGUESTFS_MODULES="${MODULES}" SUPRALINUX_LIBGUESTFS_RUNTIME_ROOT="${RUNTIME}" "${WRAPPER}" true >/dev/null 2>&1
RC=$?
set -e
[[ "${RC}" -ne 0 ]] || { printf 'Wrapper accepted changed host-kernel metadata.\n' >&2; exit 1; }
printf 'Libguestfs private-kernel runtime wrapper functional test: PASS\n'
