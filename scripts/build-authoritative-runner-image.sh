#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_URL="${SUPRALINUX_REPOSITORY_URL:-https://github.com/SupraLINUX/SupraLINUX.git}"
SOURCE_COMMIT="${SUPRALINUX_SOURCE_COMMIT:-$(git -C "${ROOT}" rev-parse HEAD)}"
SOURCE_IMAGE="${SUPRALINUX_SOURCE_IMAGE:-/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img}"
TARGET_IMAGE="${SUPRALINUX_GOLDEN_IMAGE:-/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2}"
LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
LIBVIRT_NETWORK="${SUPRALINUX_LIBVIRT_NETWORK:-default}"
RUNNER_USER="${SUPRALINUX_RUNNER_USER:-ubuntu}"
VM_MEMORY_MIB="${SUPRALINUX_GOLDEN_BUILD_MEMORY_MIB:-12288}"
VM_VCPUS="${SUPRALINUX_GOLDEN_BUILD_VCPUS:-6}"
VM_DISK_SIZE_GIB="${SUPRALINUX_GOLDEN_BUILD_DISK_SIZE_GIB:-80}"
BUILD_TIMEOUT_SECONDS="${SUPRALINUX_GOLDEN_BUILD_TIMEOUT_SECONDS:-10800}"
REPLACE="${SUPRALINUX_REPLACE_GOLDEN_IMAGE:-0}"
STATE_ROOT="${SUPRALINUX_GOLDEN_BUILD_STATE_DIR:-/var/lib/supralinux/golden-builds}"
EVIDENCE_ROOT="${SUPRALINUX_HOST_EVIDENCE_ROOT:-/var/lib/supralinux/evidence/golden-build}"

if [[ ! "${SOURCE_COMMIT}" =~ ^[0-9a-fA-F]{40}$ ]]; then
    printf 'SUPRALINUX_SOURCE_COMMIT must be a full 40-hex commit SHA; got: %s\n' "${SOURCE_COMMIT}" >&2
    exit 2
fi
if [[ ! "${RUNNER_USER}" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]]; then
    printf 'Invalid runner user name: %s\n' "${RUNNER_USER}" >&2
    exit 2
fi

required=(
    git
    jq
    qemu-img
    sha256sum
    timeout
    virsh
    virt-cat
    virt-copy-out
    virt-install
    virt-sysprep
)
for command_name in "${required[@]}"; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing host command: %s\n' "${command_name}" >&2
        exit 1
    }
done

"${ROOT}/scripts/check-kvm-host.sh"

if [[ ! -f "${SOURCE_IMAGE}" ]]; then
    printf 'Verified Ubuntu source image is missing: %s\n' "${SOURCE_IMAGE}" >&2
    printf 'Run scripts/fetch-ubuntu-26.04-cloud-image.sh first, or set SUPRALINUX_SOURCE_IMAGE.\n' >&2
    exit 1
fi
if [[ ! -f "${SOURCE_IMAGE}.provenance.txt" ]]; then
    printf 'Source-image provenance is missing: %s.provenance.txt\n' "${SOURCE_IMAGE}" >&2
    exit 1
fi
if [[ -e "${TARGET_IMAGE}" && "${REPLACE}" != "1" ]]; then
    printf 'Refusing to replace existing golden image without SUPRALINUX_REPLACE_GOLDEN_IMAGE=1: %s\n' "${TARGET_IMAGE}" >&2
    exit 1
fi

export LIBVIRT_DEFAULT_URI="${LIBVIRT_URI}"

BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)-${SOURCE_COMMIT:0:12}-$$"
VM_NAME="supralinux-golden-${BUILD_ID,,}"
BUILD_DIR="${STATE_ROOT}/${BUILD_ID}"
EVIDENCE_DIR="${EVIDENCE_ROOT}/${BUILD_ID}"
WORK_DISK="${BUILD_DIR}/golden-work.qcow2"
USER_DATA="${BUILD_DIR}/user-data"
META_DATA="${BUILD_DIR}/meta-data"
TARGET_TMP="${TARGET_IMAGE}.tmp-${BUILD_ID}"
SOURCE_FORMAT="$(qemu-img info --output=json "${SOURCE_IMAGE}" | jq -r '.format')"
SUCCESS=0
VM_DEFINED=0

mkdir -p "${BUILD_DIR}" "${EVIDENCE_DIR}" "$(dirname "${TARGET_IMAGE}")"
chmod 0700 "${BUILD_DIR}"

cleanup() {
    local rc="$?"
    trap - EXIT INT TERM
    set +e
    if (( VM_DEFINED )); then
        if virsh domstate "${VM_NAME}" 2>/dev/null | grep -Eq 'running|paused|in shutdown'; then
            virsh destroy "${VM_NAME}" >/dev/null 2>&1 || true
        fi
        virsh dumpxml "${VM_NAME}" > "${EVIDENCE_DIR}/domain.xml" 2>/dev/null || true
        virsh undefine "${VM_NAME}" >/dev/null 2>&1 || true
    fi
    rm -f "${TARGET_TMP}"
    if (( SUCCESS )); then
        rm -rf "${BUILD_DIR}"
    else
        printf 'Golden-image build failed; preserving work state at %s\n' "${BUILD_DIR}" >&2
    fi
    exit "${rc}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Creating preparation overlay from verified Ubuntu 26.04 image...\n'
qemu-img create -f qcow2 -F "${SOURCE_FORMAT}" -b "${SOURCE_IMAGE}" "${WORK_DISK}"
qemu-img resize "${WORK_DISK}" "${VM_DISK_SIZE_GIB}G"
qemu-img info --output=json "${WORK_DISK}" > "${EVIDENCE_DIR}/work-disk-before.json"

cat > "${META_DATA}" <<EOF_META
instance-id: ${VM_NAME}
local-hostname: ${VM_NAME}
EOF_META

cat > "${USER_DATA}" <<EOF_USER
#cloud-config
package_update: true
packages:
  - ca-certificates
  - git
write_files:
  - path: /usr/local/sbin/supralinux-golden-build
    owner: root:root
    permissions: '0755'
    content: |
      #!/usr/bin/env bash
      set -Eeuo pipefail
      mkdir -p /var/lib/supralinux/evidence
      exec > >(tee -a /var/log/supralinux-golden-build.log) 2>&1
      result=/var/lib/supralinux/evidence/golden-build-result.txt
      finish() {
          rc=\$?
          {
              printf 'finished_at=%s\\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)"
              printf 'source_commit=%s\\n' '${SOURCE_COMMIT}'
              printf 'exit_code=%d\\n' "\${rc}"
          } > "\${result}"
          exit "\${rc}"
      }
      trap finish EXIT
      rm -rf /opt/supralinux-src
      git clone --filter=blob:none '${REPOSITORY_URL}' /opt/supralinux-src
      git -C /opt/supralinux-src checkout --detach '${SOURCE_COMMIT}'
      git -C /opt/supralinux-src rev-parse HEAD | grep -qx '${SOURCE_COMMIT}'
      SUPRALINUX_RUNNER_USER='${RUNNER_USER}' /opt/supralinux-src/scripts/provision-authoritative-runner-guest.sh
      sudo -iu '${RUNNER_USER}' bash -lc 'cd /opt/supralinux-src && ./scripts/prepare-autopkgtest-qemu-image.sh'
      SUPRALINUX_RUNNER_USER='${RUNNER_USER}' /opt/supralinux-src/scripts/seal-authoritative-runner-image.sh
      rm -rf /opt/supralinux-src
      {
          printf 'completed_at=%s\\n' "\$(date -u +%Y-%m-%dT%H:%M:%SZ)"
          printf 'source_commit=%s\\n' '${SOURCE_COMMIT}'
          printf 'runner_user=%s\\n' '${RUNNER_USER}'
          printf 'source_checkout_removed=yes\\n'
      } > /var/lib/supralinux/evidence/golden-build-complete.txt
runcmd:
  - [ /usr/local/sbin/supralinux-golden-build ]
power_state:
  delay: now
  mode: poweroff
  message: SupraLINUX golden image build complete
  timeout: 30
  condition: true
EOF_USER

{
    printf 'started_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'source_commit=%s\n' "${SOURCE_COMMIT}"
    printf 'repository_url=%s\n' "${REPOSITORY_URL}"
    printf 'source_image=%s\n' "${SOURCE_IMAGE}"
    printf 'source_image_sha256='; sha256sum "${SOURCE_IMAGE}" | awk '{print $1}'
    printf 'source_image_format=%s\n' "${SOURCE_FORMAT}"
    printf 'vm_name=%s\n' "${VM_NAME}"
    printf 'memory_mib=%s\n' "${VM_MEMORY_MIB}"
    printf 'vcpus=%s\n' "${VM_VCPUS}"
    printf 'disk_size_gib=%s\n' "${VM_DISK_SIZE_GIB}"
    printf 'user_data_sha256='; sha256sum "${USER_DATA}" | awk '{print $1}'
    printf 'meta_data_sha256='; sha256sum "${META_DATA}" | awk '{print $1}'
    printf '\nsource_image_provenance:\n'
    cat "${SOURCE_IMAGE}.provenance.txt"
} > "${EVIDENCE_DIR}/build-inputs.txt"

printf 'Booting Ubuntu 26.04 preparation VM with cloud-init...\n'
VM_DEFINED=1
if ! timeout --foreground "${BUILD_TIMEOUT_SECONDS}" virt-install \
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
    --wait=-1; then
    printf 'Preparation VM did not complete successfully within the configured timeout.\n' >&2
    exit 1
fi

if virsh domstate "${VM_NAME}" 2>/dev/null | grep -Eq 'running|paused|in shutdown'; then
    printf 'Preparation VM is unexpectedly still running after virt-install returned.\n' >&2
    exit 1
fi

printf 'Extracting guest preparation evidence...\n'
mkdir -p "${EVIDENCE_DIR}/guest"
virt-copy-out -a "${WORK_DISK}" /var/lib/supralinux/evidence "${EVIDENCE_DIR}/guest"
virt-copy-out -a "${WORK_DISK}" /var/log/supralinux-golden-build.log "${EVIDENCE_DIR}/guest" 2>/dev/null || true

RESULT_TEXT="$(virt-cat -a "${WORK_DISK}" /var/lib/supralinux/evidence/golden-build-result.txt 2>/dev/null || true)"
COMPLETE_TEXT="$(virt-cat -a "${WORK_DISK}" /var/lib/supralinux/evidence/golden-build-complete.txt 2>/dev/null || true)"
printf '%s\n' "${RESULT_TEXT}" > "${EVIDENCE_DIR}/golden-build-result.txt"
printf '%s\n' "${COMPLETE_TEXT}" > "${EVIDENCE_DIR}/golden-build-complete.txt"

if ! grep -qx 'exit_code=0' <<<"${RESULT_TEXT}"; then
    printf 'Guest provisioning did not record exit_code=0.\n' >&2
    exit 1
fi
if ! grep -qx "source_commit=${SOURCE_COMMIT}" <<<"${COMPLETE_TEXT}"; then
    printf 'Guest completion evidence does not match requested source commit.\n' >&2
    exit 1
fi
if ! grep -qx 'source_checkout_removed=yes' <<<"${COMPLETE_TEXT}"; then
    printf 'Guest completion evidence does not confirm removal of the build checkout.\n' >&2
    exit 1
fi

printf 'Applying explicit offline clone-safety operations...\n'
SUPPORTED_OPS="$(virt-sysprep --list-operations | awk '{print $1}')"
SYSPREP_OPS=(machine-id ssh-hostkeys dhcp-client-state logfiles tmp-files)
for op in "${SYSPREP_OPS[@]}"; do
    grep -qx "${op}" <<<"${SUPPORTED_OPS}" || {
        printf 'Host virt-sysprep does not support required operation: %s\n' "${op}" >&2
        exit 1
    }
done
OPS_CSV="$(IFS=,; echo "${SYSPREP_OPS[*]}")"
virt-sysprep -a "${WORK_DISK}" --operations "${OPS_CSV}" |& tee "${EVIDENCE_DIR}/virt-sysprep.log"

printf 'Flattening the prepared overlay into a standalone golden qcow2...\n'
qemu-img convert -p -O qcow2 "${WORK_DISK}" "${TARGET_TMP}" |& tee "${EVIDENCE_DIR}/qemu-img-convert.log"
qemu-img check "${TARGET_TMP}" |& tee "${EVIDENCE_DIR}/qemu-img-check.log"
qemu-img info --output=json "${TARGET_TMP}" > "${EVIDENCE_DIR}/golden-image-info.json"
GOLDEN_SHA256="$(sha256sum "${TARGET_TMP}" | awk '{print $1}')"
printf '%s  %s\n' "${GOLDEN_SHA256}" "$(basename "${TARGET_IMAGE}")" > "${EVIDENCE_DIR}/golden-image-sha256.txt"

if [[ -e "${TARGET_IMAGE}" && "${REPLACE}" == "1" ]]; then
    mv "${TARGET_IMAGE}" "${TARGET_IMAGE}.previous-${BUILD_ID}"
fi
mv "${TARGET_TMP}" "${TARGET_IMAGE}"
chmod 0644 "${TARGET_IMAGE}"

PROVENANCE_TMP="$(mktemp)"
{
    printf 'created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'source_commit=%s\n' "${SOURCE_COMMIT}"
    printf 'repository_url=%s\n' "${REPOSITORY_URL}"
    printf 'source_image=%s\n' "${SOURCE_IMAGE}"
    printf 'source_image_sha256='; sha256sum "${SOURCE_IMAGE}" | awk '{print $1}'
    printf 'golden_image=%s\n' "${TARGET_IMAGE}"
    printf 'golden_image_sha256=%s\n' "${GOLDEN_SHA256}"
    printf 'virt_sysprep_operations=%s\n' "${OPS_CSV}"
    printf 'source_checkout_removed=yes\n'
    printf '\nqemu_image_info:\n'
    qemu-img info "${TARGET_IMAGE}"
} > "${PROVENANCE_TMP}"
mv "${PROVENANCE_TMP}" "${TARGET_IMAGE}.provenance.txt"

SUCCESS=1
printf 'Prepared standalone golden runner image: %s\n' "${TARGET_IMAGE}"
printf 'SHA-256: %s\n' "${GOLDEN_SHA256}"
printf 'Evidence: %s\n' "${EVIDENCE_DIR}"
