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
    'curl --fail --show-error --location --output "${ARCHIVE}" "${DOWNLOAD_URL}"',
    'sha256sum --check --strict',
    'sudo chown "${TARGET_USER}:${TARGET_GROUP}" "${TMP_DIR}" "${ARCHIVE}"',
    'sudo chmod 0700 "${TMP_DIR}"',
    'sudo chmod 0600 "${ARCHIVE}"',
    'sudo -u "${TARGET_USER}" tar -xzf "${ARCHIVE}" -C "${INSTALL_DIR}"',
]
for token in required:
    if token not in text:
        raise SystemExit(f"missing installer staging contract: {token}")

download_pos = text.index('curl --fail --show-error --location --output "${ARCHIVE}"')
verify_pos = text.index('sha256sum --check --strict')
chown_pos = text.index('sudo chown "${TARGET_USER}:${TARGET_GROUP}" "${TMP_DIR}" "${ARCHIVE}"')
tar_pos = text.index('sudo -u "${TARGET_USER}" tar -xzf')
if not (download_pos < verify_pos < chown_pos < tar_pos):
    raise SystemExit("runner staging must download+verify as caller before ownership transfer and non-root extraction")
if "trap 'sudo rm -rf --" not in text:
    raise SystemExit("runner staging cleanup must remain valid after ownership transfer")
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
