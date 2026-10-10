#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="${ROOT}/scripts/check-autopkgtest-workspace.sh"
PREP="${ROOT}/scripts/prepare-autopkgtest-qemu-image.sh"
PROVISION="${ROOT}/scripts/provision-authoritative-runner-guest.sh"
SEAL="${ROOT}/scripts/seal-authoritative-runner-image.sh"

TMP="$(mktemp -d "${ROOT}/.autopkgtest-workspace-test.XXXXXX")"
trap 'rm -rf "${TMP}"' EXIT

AUTOPKGTEST_QEMU_MIN_WORK_FREE_BYTES=1 "${CHECKER}" "${TMP}" > "${TMP}/pass.txt"
grep -qx 'status=PASS' "${TMP}/pass.txt"

set +e
AUTOPKGTEST_QEMU_MIN_WORK_FREE_BYTES=999999999999999999 "${CHECKER}" "${TMP}" >"${TMP}/fail.out" 2>"${TMP}/fail.err"
RC=$?
set -e
[[ "${RC}" -ne 0 ]] || {
    printf 'Workspace checker accepted impossible free-space requirement.\n' >&2
    exit 1
}
grep -q 'insufficient free space' "${TMP}/fail.err"

python3 - "${PREP}" "${PROVISION}" "${SEAL}" <<'PY'
from pathlib import Path
import sys

prep = Path(sys.argv[1]).read_text()
provision = Path(sys.argv[2]).read_text()
seal = Path(sys.argv[3]).read_text()

for token in (
    'AUTOPKGTEST_QEMU_WORK_ROOT:-/var/lib/supralinux/autopkgtest/work',
    'scripts/check-autopkgtest-workspace.sh',
    'genisoimage',
    '--disk-size="${DISK_SIZE}"',
    'AUTOPKGTEST_QEMU_RAM_MIB:-2048',
    'AUTOPKGTEST_QEMU_BUILD_SWAP_MIB:-4096',
    'sudo swapon "${BUILD_SWAP_FILE}"',
    'sudo swapoff "${BUILD_SWAP_FILE}"',
    'autopkgtest-build-resources.txt',
    '--ram-size="${RAM_SIZE}"',
):
    if token not in prep:
        raise SystemExit(f"missing autopkgtest preparation contract: {token}")

for token in (
    'genisoimage',
    '/var/lib/supralinux/autopkgtest/work',
    '-o "${TARGET_USER}"',
):
    if token not in provision:
        raise SystemExit(f"missing guest provisioning contract: {token}")

for token in (
    'AUTOPKGTEST_QEMU_BUILD_SWAP_FILE:-/var/lib/supralinux/autopkgtest/.build.swap',
    'swapon --show=NAME --noheadings',
    'temporary_build_swap_absent=yes',
):
    if token not in seal:
        raise SystemExit(f"missing golden seal temporary-swap contract: {token}")
PY

printf 'Autopkgtest persistent-workspace contract test: PASS\n'
