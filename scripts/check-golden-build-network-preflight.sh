#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_IMAGE="${SUPRALINUX_SOURCE_IMAGE:-/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img}"
SOURCE_PROVENANCE="${SOURCE_IMAGE}.provenance.txt"
LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
if [[ -n "${SUPRALINUX_LIBVIRT_NETWORK:-}" ]]; then
    printf 'Golden network preflight refuses libvirt network overrides.\n' >&2
    exit 2
fi
LIBVIRT_QEMU_USER="${SUPRALINUX_LIBVIRT_QEMU_USER:-libvirt-qemu}"
STATE_ROOT="${SUPRALINUX_GOLDEN_NETWORK_STATE_DIR:-/var/lib/supralinux/golden-builds/network-preflight}"
EVIDENCE_ROOT="${SUPRALINUX_GOLDEN_NETWORK_EVIDENCE_ROOT:-/var/lib/supralinux/evidence/golden-network-preflight}"
VM_MEMORY_MIB="${SUPRALINUX_GOLDEN_NETWORK_MEMORY_MIB:-1536}"
VM_VCPUS="${SUPRALINUX_GOLDEN_NETWORK_VCPUS:-1}"
TIMEOUT_SECONDS="${SUPRALINUX_GOLDEN_NETWORK_TIMEOUT_SECONDS:-900}"

required=(chgrp chmod id jq qemu-img sha256sum timeout virsh virt-install)
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
grep -qw "${LIBVIRT_QEMU_GROUP}" <<<"$(id -nG)" || {
    printf 'Current user is not in the effective libvirt QEMU group: %s\n' "${LIBVIRT_QEMU_GROUP}" >&2
    exit 1
}

"${ROOT}/scripts/with-libguestfs-runtime.sh" true
"${ROOT}/scripts/verify-ubuntu-cloud-image-provenance.sh" "${SOURCE_IMAGE}" "${SOURCE_PROVENANCE}" >/dev/null

BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
VM_NAME="supralinux-golden-network-${BUILD_ID,,}"
BUILD_DIR="${STATE_ROOT}/${BUILD_ID}"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${BUILD_ID}"
WORK_DISK="${BUILD_DIR}/network-work.qcow2"
USER_DATA="${BUILD_DIR}/user-data"
META_DATA="${BUILD_DIR}/meta-data"
NETWORK_CONFIG="${BUILD_DIR}/network-config"
VM_DEFINED=0

mkdir -p "${BUILD_DIR}" "${EVIDENCE_DIR}"
chgrp "${LIBVIRT_QEMU_GROUP}" "${BUILD_DIR}"
chmod 0710 "${BUILD_DIR}"

cleanup() {
    local rc="$?"
    trap - EXIT INT TERM
    set +e
    if [[ "${VM_NAME}" != supralinux-golden-network-* || "${BUILD_DIR}" != "${STATE_ROOT}/"* ]]; then
        printf 'Refusing golden-network cleanup outside owned namespace.\n' >&2
        exit 1
    fi
    if (( VM_DEFINED )); then
        virsh --connect "${LIBVIRT_URI}" dumpxml "${VM_NAME}" > "${EVIDENCE_DIR}/domain-final.xml" 2>/dev/null || true
        state="$(LC_ALL=C virsh --connect "${LIBVIRT_URI}" domstate "${VM_NAME}" 2>/dev/null || true)"
        if grep -Eq '^(running|paused|in shutdown)$' <<<"${state}"; then
            virsh --connect "${LIBVIRT_URI}" destroy "${VM_NAME}" >/dev/null 2>&1 || true
        fi
        virsh --connect "${LIBVIRT_URI}" undefine "${VM_NAME}" >/dev/null 2>&1 || true
    fi
    if virsh --connect "${LIBVIRT_URI}" dominfo "${VM_NAME}" >/dev/null 2>&1; then
        printf 'Owned golden-network VM still exists; preserving overlay.\n' >&2
        exit 1
    fi
    rm -rf -- "${BUILD_DIR}"
    [[ ! -e "${WORK_DISK}" ]] || rc=1
    exit "${rc}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

SOURCE_FORMAT="$(qemu-img info --output=json "${SOURCE_IMAGE}" | jq -r '.format')"
qemu-img create -f qcow2 -F "${SOURCE_FORMAT}" -b "${SOURCE_IMAGE}" "${WORK_DISK}"
qemu-img resize "${WORK_DISK}" 8G
chgrp "${LIBVIRT_QEMU_GROUP}" "${WORK_DISK}"
chmod 0660 "${WORK_DISK}"

cat > "${META_DATA}" <<EOF_META
instance-id: ${VM_NAME}
local-hostname: ${VM_NAME}
EOF_META
cat > "${USER_DATA}" <<'EOF_USER'
#cloud-config
package_update: false
package_upgrade: false
EOF_USER
cat > "${NETWORK_CONFIG}" <<'EOF_NETWORK'
version: 2
ethernets:
  supranet0:
    match:
      macaddress: "52:54:00:53:55:01"
    set-name: supranet0
    dhcp4: true
    dhcp6: false
    accept-ra: false
EOF_NETWORK
cp "${USER_DATA}" "${META_DATA}" "${NETWORK_CONFIG}" "${EVIDENCE_DIR}/"

VM_DEFINED=1
virt-install     --connect "${LIBVIRT_URI}"     --name "${VM_NAME}"     --memory "${VM_MEMORY_MIB}"     --vcpus "${VM_VCPUS}"     --cpu host-passthrough     --import     --disk "path=${WORK_DISK},format=qcow2,bus=virtio,cache=none"     --network 'user,model=virtio,mac=52:54:00:53:55:01,link.state=down,xpath1.set=./ip/@family=ipv4,xpath2.set=./ip/@address=10.203.0.1,xpath3.set=./ip/@prefix=24'     --channel unix,target.type=virtio,target.name=org.qemu.guest_agent.0     --graphics none     --noautoconsole     --osinfo detect=on,require=off     --cloud-init "user-data=${USER_DATA},meta-data=${META_DATA},network-config=${NETWORK_CONFIG},disable=on"

python3 "${ROOT}/scripts/activate-golden-bootstrap-network.py"     --vm-name "${VM_NAME}"     --evidence-dir "${EVIDENCE_DIR}"     --libvirt-uri "${LIBVIRT_URI}"     --timeout 180     | tee "${EVIDENCE_DIR}/network-activation-result.json"

virsh --connect "${LIBVIRT_URI}" shutdown "${VM_NAME}" >/dev/null
DEADLINE=$(( $(date +%s) + TIMEOUT_SECONDS ))
while LC_ALL=C virsh --connect "${LIBVIRT_URI}" domstate "${VM_NAME}" 2>/dev/null | grep -Eq '^(running|paused|in shutdown)$'; do
    (( $(date +%s) < DEADLINE )) || {
        printf 'Timed out waiting for golden-network preflight shutdown.\n' >&2
        exit 1
    }
    sleep 2
done

printf 'state=PASS\nscope=golden-build-network-preflight\nhost_network_modified=no\npackage_attempt_effect=none\n'     > "${EVIDENCE_DIR}/result.txt"
printf 'Golden build network preflight: PASS\n'
