#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY="${SUPRALINUX_REPOSITORY:-SupraLINUX/SupraLINUX}"
TOKEN="${SUPRALINUX_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "${TOKEN}" ]] && command -v gh >/dev/null 2>&1; then
    TOKEN="$(gh auth token 2>/dev/null || true)"
fi
GOLDEN_IMAGE="${SUPRALINUX_GOLDEN_IMAGE:-/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2}"
TARGET_IMAGE="${SUPRALINUX_FRAMEWORKS_MILESTONE_IMAGE:-/var/lib/supralinux/images/milestones/frameworks-6.30-pass.qcow2}"
STATE_ROOT="${SUPRALINUX_MILESTONE_STATE_DIR:-/var/lib/supralinux/milestone-cache/frameworks-6.30}"
EVIDENCE_ROOT="${SUPRALINUX_HOST_EVIDENCE_ROOT:-/var/lib/supralinux/evidence}"
REPLACE="${SUPRALINUX_REPLACE_MILESTONE_IMAGE:-0}"
MIRROR="${SBUILD_MIRROR:-http://archive.ubuntu.com/ubuntu}"
API_VERSION="2026-03-10"

if [[ -z "${TOKEN}" ]]; then
    printf 'GitHub token unavailable. Authenticate with gh auth login or export SUPRALINUX_GITHUB_TOKEN.\n' >&2
    exit 1
fi
if [[ "${REPLACE}" != "0" && "${REPLACE}" != "1" ]]; then
    printf 'SUPRALINUX_REPLACE_MILESTONE_IMAGE must be 0 or 1.\n' >&2
    exit 1
fi

for command_name in curl dpkg-deb dpkg-scanpackages gzip install jq mmdebstrap qemu-img sha256sum unzip; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing host command: %s\n' "${command_name}" >&2
        exit 1
    }
done

"${ROOT}/scripts/with-libguestfs-runtime.sh" true
for command_name in virt-copy-in; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing libguestfs command: %s\n' "${command_name}" >&2
        exit 1
    }
done

LOCAL_HEAD="$(git -C "${ROOT}" rev-parse HEAD)"
if [[ -n "$(git -C "${ROOT}" status --porcelain --untracked-files=normal)" ]]; then
    printf 'Host checkout must be clean before building a milestone image.\n' >&2
    exit 1
fi

TARGET_USER="${SUPRALINUX_HOST_USER:-${SUDO_USER:-${USER}}}"
if ! id "${TARGET_USER}" >/dev/null 2>&1; then
    printf 'Milestone host user does not exist: %s\n' "${TARGET_USER}" >&2
    exit 1
fi
TARGET_GROUP="$(id -gn "${TARGET_USER}")"

if [[ "${EUID}" -eq 0 ]]; then
    ROOT_CMD=()
else
    command -v sudo >/dev/null 2>&1 || {
        printf 'sudo is required to create the dedicated milestone directories under /var/lib/supralinux.\n' >&2
        exit 1
    }
    ROOT_CMD=(sudo)
fi

# These are dedicated cache/evidence directories. Provision them before
# check-golden-image-provenance.sh writes its admission record.
"${ROOT_CMD[@]}" install -d -o "${TARGET_USER}" -g "${TARGET_GROUP}" -m 0750     "${STATE_ROOT}"     "$(dirname "${TARGET_IMAGE}")"     "${EVIDENCE_ROOT}/milestone-frameworks-6.30"

"${ROOT}/scripts/check-golden-image-provenance.sh" "${GOLDEN_IMAGE}" "${STATE_ROOT}/golden-admission.txt"
GOLDEN_SHA256="$(sha256sum "${GOLDEN_IMAGE}" | awk '{print $1}')"
if [[ "${GOLDEN_SHA256}" != "a0b88447d9a9ecd9785087390cf499abaf9416291864fe1be4d63d9a334b2acd" ]]; then
    printf 'Unexpected admitted golden image SHA-256: %s\n' "${GOLDEN_SHA256}" >&2
    exit 1
fi

if [[ -e "${TARGET_IMAGE}" && "${REPLACE}" != "1" ]]; then
    printf 'Milestone image already exists; refusing replacement without SUPRALINUX_REPLACE_MILESTONE_IMAGE=1: %s\n' "${TARGET_IMAGE}" >&2
    exit 1
fi

BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
BUILD_DIR="${STATE_ROOT}/build-${BUILD_ID}"
DOWNLOAD_DIR="${STATE_ROOT}/downloads"
EXTRACT_DIR="${BUILD_DIR}/artifacts"
PAYLOAD_PARENT="${BUILD_DIR}/payload"
PAYLOAD_DIR="${PAYLOAD_PARENT}/milestones/frameworks-6.30"
REPO_DIR="${PAYLOAD_DIR}/repo"
POOL_DIR="${REPO_DIR}/pool"
ROOTFS_DIR="${PAYLOAD_DIR}/sbuild"
PLAN="${PAYLOAD_DIR}/artifact-plan.json"
PACKAGE_MANIFEST="${PAYLOAD_DIR}/package-pool.json"
WORK_IMAGE="${BUILD_DIR}/frameworks-milestone-work.qcow2"
TARGET_TMP="${TARGET_IMAGE}.tmp-${BUILD_ID}"
EVIDENCE_DIR="${EVIDENCE_ROOT}/milestone-frameworks-6.30/${BUILD_ID}"

mkdir -p "${BUILD_DIR}" "${DOWNLOAD_DIR}" "${EXTRACT_DIR}" "${POOL_DIR}" "${ROOTFS_DIR}" "${EVIDENCE_DIR}" "$(dirname "${TARGET_IMAGE}")"
python3 "${ROOT}/scripts/plan-frameworks-milestone.py" > "${PLAN}"
cp "${PLAN}" "${EVIDENCE_DIR}/artifact-plan.json"

download_artifact() {
    local node="$1" artifact_id="$2" expected="$3"
    local zip="${DOWNLOAD_DIR}/${artifact_id}.zip"
    local actual
    if [[ -s "${zip}" ]]; then
        actual="$(sha256sum "${zip}" | awk '{print $1}')"
        if [[ "${actual}" == "${expected}" ]]; then
            printf 'Reusing verified artifact %s for %s\n' "${artifact_id}" "${node}"
            printf '%s\n' "${zip}"
            return 0
        fi
        rm -f "${zip}"
    fi
    local tmp="${zip}.tmp"
    rm -f "${tmp}"
    printf 'Downloading Frameworks PASS artifact %s for %s...\n' "${artifact_id}" "${node}" >&2
    curl --fail-with-body --silent --show-error --location         --header 'Accept: application/vnd.github+json'         --header "Authorization: Bearer ${TOKEN}"         --header "X-GitHub-Api-Version: ${API_VERSION}"         "https://api.github.com/repos/${REPOSITORY}/actions/artifacts/${artifact_id}/zip"         --output "${tmp}"
    actual="$(sha256sum "${tmp}" | awk '{print $1}')"
    if [[ "${actual}" != "${expected}" ]]; then
        printf 'Artifact digest mismatch for %s: expected=%s actual=%s\n' "${artifact_id}" "${expected}" "${actual}" >&2
        rm -f "${tmp}"
        exit 1
    fi
    mv "${tmp}" "${zip}"
    printf '%s\n' "${zip}"
}

while IFS=$'\t' read -r node artifact_id digest; do
    zip="$(download_artifact "${node}" "${artifact_id}" "${digest}")"
    node_dir="${EXTRACT_DIR}/${node}"
    rm -rf "${node_dir}"
    mkdir -p "${node_dir}"
    unzip -qq "${zip}" -d "${node_dir}"
    found=0
    while IFS= read -r -d '' deb; do
        found=1
        base="$(basename "${deb}")"
        dest="${POOL_DIR}/${base}"
        if [[ -e "${dest}" ]]; then
            old="$(sha256sum "${dest}" | awk '{print $1}')"
            new="$(sha256sum "${deb}" | awk '{print $1}')"
            if [[ "${old}" != "${new}" ]]; then
                printf 'Conflicting binary package filename in retained artifacts: %s\n' "${base}" >&2
                exit 1
            fi
        else
            cp -a "${deb}" "${dest}"
        fi
    done < <(find "${node_dir}" -type f -name '*.deb' -print0)
    if (( found == 0 )); then
        printf 'PASS artifact for %s contains no .deb files.\n' "${node}" >&2
        exit 1
    fi
done < <(jq -r '.items[] | [.node, (.artifact_id|tostring), .artifact_sha256] | @tsv' "${PLAN}")

(
    cd "${REPO_DIR}"
    dpkg-scanpackages -m pool /dev/null > Packages
    gzip -9c Packages > Packages.gz
)

python3 - "${POOL_DIR}" "${PACKAGE_MANIFEST}" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

pool = Path(sys.argv[1])
out = Path(sys.argv[2])
items = []
names = {}
for path in sorted(pool.glob("*.deb")):
    def field(name):
        return subprocess.check_output(["dpkg-deb", "-f", str(path), name], text=True).strip()
    package = field("Package")
    version = field("Version")
    arch = field("Architecture")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    key = (package, arch)
    if key in names and names[key] != version:
        raise SystemExit(f"multiple retained versions for {package}:{arch}: {names[key]} vs {version}")
    names[key] = version
    items.append({
        "file": path.name,
        "package": package,
        "version": version,
        "architecture": arch,
        "sha256": digest,
        "size": path.stat().st_size,
    })
out.write_text(json.dumps({
    "schema": 1,
    "kind": "frameworks-6.30-binary-pool",
    "package_count": len(items),
    "packages": items,
}, indent=2, sort_keys=True) + "\n")
PY

ROOTFS="${ROOTFS_DIR}/resolute-amd64.tar"
ROOTFS_CACHE="${STATE_ROOT}/rootfs/resolute-amd64.tar"
mkdir -p "$(dirname "${ROOTFS_CACHE}")"
if [[ ! -s "${ROOTFS_CACHE}" ]]; then
    printf 'Creating reusable Resolute sbuild rootfs once...\n'
    tmp_rootfs="${ROOTFS_CACHE}.tmp"
    rm -f "${tmp_rootfs}"
    mmdebstrap         --mode=unshare         --variant=buildd         --architectures=amd64         --components=main,universe         --skip=output/mknod         --format=tar         resolute         "${tmp_rootfs}"         "${MIRROR}"
    mv "${tmp_rootfs}" "${ROOTFS_CACHE}"
fi
cp --reflink=auto "${ROOTFS_CACHE}" "${ROOTFS}"
chmod 0644 "${ROOTFS}"

{
    printf 'frameworks_series=6.30.0\n'
    printf 'source_commit=%s\n' "${LOCAL_HEAD}"
    printf 'source_golden_image=%s\n' "${GOLDEN_IMAGE}"
    printf 'source_golden_sha256=%s\n' "${GOLDEN_SHA256}"
    printf 'artifact_plan_sha256='; sha256sum "${PLAN}" | awk '{print $1}'
    printf 'package_pool_sha256='; sha256sum "${PACKAGE_MANIFEST}" | awk '{print $1}'
    printf 'packages_index_sha256='; sha256sum "${REPO_DIR}/Packages" | awk '{print $1}'
    printf 'sbuild_rootfs_sha256='; sha256sum "${ROOTFS}" | awk '{print $1}'
    printf 'pass_nodes=65\n'
    printf 'cache_only=yes\n'
    printf 'framework_packages_preinstalled_in_sbuild_rootfs=no\n'
} > "${PAYLOAD_DIR}/checkpoint-manifest.txt"
cp "${PACKAGE_MANIFEST}" "${EVIDENCE_DIR}/package-pool.json"
cp "${PAYLOAD_DIR}/checkpoint-manifest.txt" "${EVIDENCE_DIR}/checkpoint-manifest.txt"

printf 'Creating Frameworks milestone qcow2 from admitted golden image...\n'
qemu-img create -f qcow2 -F qcow2 -b "${GOLDEN_IMAGE}" "${WORK_IMAGE}" >/dev/null
"${ROOT}/scripts/with-libguestfs-runtime.sh" virt-copy-in     -a "${WORK_IMAGE}" "${PAYLOAD_PARENT}/milestones" /var/lib/supralinux

printf 'Flattening milestone cache image...\n'
qemu-img convert -p -O qcow2 "${WORK_IMAGE}" "${TARGET_TMP}"
qemu-img check "${TARGET_TMP}" | tee "${EVIDENCE_DIR}/qemu-img-check.txt"
MILESTONE_SHA256="$(sha256sum "${TARGET_TMP}" | awk '{print $1}')"

PROVENANCE_TMP="${TARGET_IMAGE}.provenance.txt.tmp-${BUILD_ID}"
{
    printf 'kind=frameworks-milestone-execution-cache\n'
    printf 'cache_only=yes\n'
    printf 'canonical_source_of_truth=no\n'
    printf 'created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'source_commit=%s\n' "${LOCAL_HEAD}"
    printf 'source_golden_image=%s\n' "${GOLDEN_IMAGE}"
    printf 'source_golden_sha256=%s\n' "${GOLDEN_SHA256}"
    printf 'frameworks_series=6.30.0\n'
    printf 'pass_nodes=65\n'
    printf 'artifact_plan_sha256='; sha256sum "${PLAN}" | awk '{print $1}'
    printf 'package_pool_sha256='; sha256sum "${PACKAGE_MANIFEST}" | awk '{print $1}'
    printf 'packages_index_sha256='; sha256sum "${REPO_DIR}/Packages" | awk '{print $1}'
    printf 'sbuild_rootfs_sha256='; sha256sum "${ROOTFS}" | awk '{print $1}'
    printf 'framework_packages_preinstalled_in_sbuild_rootfs=no\n'
    printf 'milestone_image_sha256=%s\n' "${MILESTONE_SHA256}"
} > "${PROVENANCE_TMP}"

if [[ -e "${TARGET_IMAGE}" && "${REPLACE}" == "1" ]]; then
    mv "${TARGET_IMAGE}" "${TARGET_IMAGE}.previous-${BUILD_ID}"
    [[ -e "${TARGET_IMAGE}.provenance.txt" ]] && mv "${TARGET_IMAGE}.provenance.txt" "${TARGET_IMAGE}.provenance.txt.previous-${BUILD_ID}"
fi
mv "${TARGET_TMP}" "${TARGET_IMAGE}"
mv "${PROVENANCE_TMP}" "${TARGET_IMAGE}.provenance.txt"
chmod 0644 "${TARGET_IMAGE}" "${TARGET_IMAGE}.provenance.txt"

cp "${TARGET_IMAGE}.provenance.txt" "${EVIDENCE_DIR}/milestone-provenance.txt"
sha256sum "${TARGET_IMAGE}" > "${EVIDENCE_DIR}/milestone-image-sha256.txt"
(
    cd "${EVIDENCE_DIR}"
    find . -type f ! -name evidence-sha256.txt -print0 | sort -z | xargs -0 sha256sum
) > "${EVIDENCE_DIR}/evidence-sha256.txt"

printf '\nFrameworks milestone execution cache: PASS\n'
printf 'IMAGE=%s\n' "${TARGET_IMAGE}"
printf 'SHA256=%s\n' "${MILESTONE_SHA256}"
printf 'EVIDENCE_DIR=%s\n' "${EVIDENCE_DIR}"
printf 'This image is a cache only; retained artifacts/manifests remain canonical.\n'
