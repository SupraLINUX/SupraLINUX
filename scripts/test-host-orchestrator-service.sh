#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP="${ROOT}/scripts/bootstrap-host-orchestrator.sh"

python3 - "${BOOTSTRAP}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text()

required = [
    'cd "$1"',
    'exec ./config.sh "$@"',
    'if [[ ! -f "${RUNNER_DIR}/.service" ]]; then',
    'cd "${RUNNER_DIR}"',
    'sudo ./svc.sh install "${RUNNER_USER}"',
    'sudo ./svc.sh start',
    'sudo -u "${RUNNER_USER}" -H sudo -n -l',
    'NOPASSWD: ${BROKER}',
]
for token in required:
    if token not in text:
        raise SystemExit(f"missing host-orchestrator service contract: {token}")

if 'sudo "${RUNNER_DIR}/svc.sh" install' in text:
    raise SystemExit("svc.sh install must not run outside the runner root")
if 'sudo "${RUNNER_DIR}/svc.sh" start' in text:
    raise SystemExit("svc.sh start must not run outside the runner root")

print("Host orchestrator service/root and passwordless broker contract: PASS")
PY
