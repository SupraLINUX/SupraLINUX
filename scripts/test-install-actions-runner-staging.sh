#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALLER="${ROOT}/scripts/install-actions-runner.sh"

for command_name in python3 sudo tar mktemp useradd userdel; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing test command: %s\n' "${command_name}" >&2
        exit 1
    }
done

python3 - "${INSTALLER}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text()
required = [
    'TARGET_GROUP="$(id -gn "${TARGET_USER}")"',
    'sudo chown "${TARGET_USER}:${TARGET_GROUP}" "${TMP_DIR}"',
    'sudo chmod 0700 "${TMP_DIR}"',
    'sudo -u "${TARGET_USER}" tar -xzf "${ARCHIVE}" -C "${INSTALL_DIR}"',
]
for token in required:
    if token not in text:
        raise SystemExit(f"missing installer staging contract: {token}")

chown_pos = text.index('sudo chown "${TARGET_USER}:${TARGET_GROUP}" "${TMP_DIR}"')
tar_pos = text.index('sudo -u "${TARGET_USER}" tar -xzf')
if chown_pos >= tar_pos:
    raise SystemExit("staging ownership must precede non-root extraction")
PY

TEST_USER="sl-stage-$$"
TMP="$(mktemp -d)"
PAYLOAD="$(mktemp -d)"
trap 'sudo userdel "${TEST_USER}" >/dev/null 2>&1 || true; sudo rm -rf "${TMP}"; rm -rf "${PAYLOAD}"' EXIT

sudo useradd --system --no-create-home --shell /usr/sbin/nologin "${TEST_USER}"
TEST_GROUP="$(id -gn "${TEST_USER}")"

printf 'staging-contract\n' > "${PAYLOAD}/marker.txt"
tar -czf "${TMP}/runner.tar.gz" -C "${PAYLOAD}" marker.txt

sudo chown "${TEST_USER}:${TEST_GROUP}" "${TMP}"
sudo chmod 0700 "${TMP}"
sudo chown "${TEST_USER}:${TEST_GROUP}" "${TMP}/runner.tar.gz"
sudo chmod 0600 "${TMP}/runner.tar.gz"

sudo -u "${TEST_USER}" tar -tzf "${TMP}/runner.tar.gz" | grep -qx 'marker.txt'

printf 'Actions runner non-root staging functional test: PASS\n'
