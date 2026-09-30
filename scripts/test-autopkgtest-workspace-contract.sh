#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="${ROOT}/scripts/check-autopkgtest-workspace.sh"
PREP="${ROOT}/scripts/prepare-autopkgtest-qemu-image.sh"
PROVISION="${ROOT}/scripts/provision-authoritative-runner-guest.sh"

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

python3 - "${PREP}" "${PROVISION}" <<'PY'
from pathlib import Path
import sys

prep = Path(sys.argv[1]).read_text()
provision = Path(sys.argv[2]).read_text()

for token in (
    'AUTOPKGTEST_QEMU_WORK_ROOT:-/var/lib/supralinux/autopkgtest/work',
    'scripts/check-autopkgtest-workspace.sh',
    'genisoimage',
    '--disk-size="${DISK_SIZE}"',
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
PY

printf 'Autopkgtest persistent-workspace contract test: PASS\n'
