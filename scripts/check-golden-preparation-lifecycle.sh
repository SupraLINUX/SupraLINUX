#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_IMAGE="${SUPRALINUX_SOURCE_IMAGE:-/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img}"
SOURCE_PROVENANCE="${SOURCE_IMAGE}.provenance.txt"
LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
LIBVIRT_NETWORK="${SUPRALINUX_LIBVIRT_NETWORK:-default}"
LIBVIRT_QEMU_USER="${SUPRALINUX_LIBVIRT_QEMU_USER:-libvirt-qemu}"
STATE_ROOT="${SUPRALINUX_GOLDEN_LIFECYCLE_STATE_DIR:-/var/lib/supralinux/golden-lifecycle-preflight}"
EVIDENCE_ROOT="${SUPRALINUX_GOLDEN_LIFECYCLE_EVIDENCE_ROOT:-/var/lib/supralinux/evidence/golden-lifecycle-preflight}"
VM_MEMORY_MIB="${SUPRALINUX_GOLDEN_LIFECYCLE_MEMORY_MIB:-1024}"
VM_VCPUS="${SUPRALINUX_GOLDEN_LIFECYCLE_VCPUS:-1}"
TIMEOUT_SECONDS="${SUPRALINUX_GOLDEN_LIFECYCLE_TIMEOUT_SECONDS:-900}"

required=(
    chgrp
    chmod
    id
    jq
    qemu-img
    sha256sum
    stat
    sudo
    timeout
    virsh
    virt-cat
    virt-install
)
for command_name in "${required[@]}"; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing host command: %s\n' "${command_name}" >&2
        exit 1
    }
done

"${ROOT}/scripts/check-kvm-host.sh"

if ! id "${LIBVIRT_QEMU_USER}" >/dev/null 2>&1; then
    printf 'Configured libvirt QEMU user does not exist: %s\n' "${LIBVIRT_QEMU_USER}" >&2
    exit 1
fi
LIBVIRT_QEMU_GROUP="$(id -gn "${LIBVIRT_QEMU_USER}")"

if [[ ! -f "${SOURCE_IMAGE}" || ! -f "${SOURCE_PROVENANCE}" ]]; then
    printf 'Verified Ubuntu source image/provenance is missing.\n' >&2
    exit 1
fi

BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
VM_NAME="supralinux-golden-lifecycle-${BUILD_ID,,}"
BUILD_DIR="${STATE_ROOT}/${BUILD_ID}"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${BUILD_ID}"
WORK_DISK="${BUILD_DIR}/lifecycle-work.qcow2"
USER_DATA="${BUILD_DIR}/user-data"
META_DATA="${BUILD_DIR}/meta-data"
SUCCESS=0
VM_DEFINED=0

mkdir -p "${BUILD_DIR}" "${EVIDENCE_DIR}"
sudo chgrp "${LIBVIRT_QEMU_GROUP}" "${BUILD_DIR}"
chmod 0710 "${BUILD_DIR}"

cleanup() {
    local rc="$?"
    trap - EXIT INT TERM
    set +e
    if (( VM_DEFINED )); then
        virsh --connect "${LIBVIRT_URI}" dumpxml "${VM_NAME}" > "${EVIDENCE_DIR}/domain.xml" 2>/dev/null || true
        state="$(LC_ALL=C virsh --connect "${LIBVIRT_URI}" domstate "${VM_NAME}" 2>/dev/null || true)"
        if grep -Eq '^(running|paused|in shutdown)$' <<<"${state}"; then
            virsh --connect "${LIBVIRT_URI}" destroy "${VM_NAME}" >/dev/null 2>&1 || true
        fi
        virsh --connect "${LIBVIRT_URI}" undefine "${VM_NAME}" >/dev/null 2>&1 || true
    fi
    if (( SUCCESS )); then
        rm -rf "${BUILD_DIR}"
    else
        printf 'Synthetic lifecycle preflight failed; preserving work state at %s\n' "${BUILD_DIR}" >&2
    fi
    exit "${rc}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"${ROOT}/scripts/verify-ubuntu-cloud-image-provenance.sh" \
    "${SOURCE_IMAGE}" \
    "${SOURCE_PROVENANCE}" \
    | tee "${EVIDENCE_DIR}/source-image-verification.txt"

SOURCE_FORMAT="$(qemu-img info --output=json "${SOURCE_IMAGE}" | jq -r '.format')"
qemu-img create -f qcow2 -F "${SOURCE_FORMAT}" -b "${SOURCE_IMAGE}" "${WORK_DISK}"
sudo chgrp "${LIBVIRT_QEMU_GROUP}" "${WORK_DISK}"
chmod 0660 "${WORK_DISK}"

{
    printf 'libvirt_qemu_user=%s\n' "${LIBVIRT_QEMU_USER}"
    printf 'libvirt_qemu_group=%s\n' "${LIBVIRT_QEMU_GROUP}"
    stat -c 'build_dir_mode=%a owner=%U group=%G path=%n' "${BUILD_DIR}"
    stat -c 'work_disk_mode=%a owner=%U group=%G path=%n' "${WORK_DISK}"
} > "${EVIDENCE_DIR}/libvirt-storage-access.txt"

cat > "${META_DATA}" <<EOF_META
instance-id: ${VM_NAME}
local-hostname: ${VM_NAME}
EOF_META

cat > "${USER_DATA}" <<'EOF_USER'
#cloud-config
write_files:
  - path: /var/lib/supralinux/golden-lifecycle-preflight.txt
    owner: root:root
    permissions: '0644'
    content: |
      status=PASS
power_state:
  delay: now
  mode: poweroff
  message: SupraLINUX golden lifecycle synthetic preflight complete
  timeout: 30
  condition: true
EOF_USER

printf 'Starting synthetic golden-preparation lifecycle VM...\n'
VM_DEFINED=1
if ! LC_ALL=C timeout --foreground "${TIMEOUT_SECONDS}" virt-install \
    --connect "${LIBVIRT_URI}" \
    --name "${VM_NAME}" \
    --memory "${VM_MEMORY_MIB}" \
    --vcpus "${VM_VCPUS}" \
    --cpu host-passthrough \
    --import \
    --disk "path=${WORK_DISK},format=qcow2,bus=virtio,cache=none" \
    --network "network=${LIBVIRT_NETWORK},model=virtio" \
    --graphics none \
    --noautoconsole \
    --osinfo detect=on,require=off \
    --cloud-init "user-data=${USER_DATA},meta-data=${META_DATA},disable=on" \
    --noreboot \
    --wait=-1 |& tee "${EVIDENCE_DIR}/virt-install.txt"; then
    printf 'Synthetic lifecycle VM did not complete successfully.\n' >&2
    exit 1
fi

DOMAIN_STATE="$(LC_ALL=C virsh --connect "${LIBVIRT_URI}" domstate "${VM_NAME}")"
printf '%s\n' "${DOMAIN_STATE}" > "${EVIDENCE_DIR}/domain-state.txt"
if [[ "${DOMAIN_STATE}" != "shut off" ]]; then
    printf 'Synthetic lifecycle VM must remain shut off after virt-install; got: %s\n' "${DOMAIN_STATE}" >&2
    exit 1
fi

MARKER="$(virt-cat -a "${WORK_DISK}" /var/lib/supralinux/golden-lifecycle-preflight.txt 2>/dev/null || true)"
printf '%s\n' "${MARKER}" > "${EVIDENCE_DIR}/guest-marker.txt"
if ! grep -qx 'status=PASS' <<<"${MARKER}"; then
    printf 'Synthetic lifecycle VM did not persist the expected guest marker.\n' >&2
    exit 1
fi

{
    printf 'checked_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'vm_name=%s\n' "${VM_NAME}"
    printf 'domain_state=%s\n' "${DOMAIN_STATE}"
    printf 'source_image_sha256='; sha256sum "${SOURCE_IMAGE}" | awk '{print $1}'
    printf 'result=PASS\n'
} > "${EVIDENCE_DIR}/result.txt"

SUCCESS=1
printf 'Golden preparation lifecycle synthetic preflight: PASS\n'
printf 'Evidence: %s\n' "${EVIDENCE_DIR}"
