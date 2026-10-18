#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP="${ROOT}/scripts/bootstrap-host-orchestrator.sh"

python3 - "${BOOTSTRAP}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text()

required = [
    'if ! sudo test -f "${RUNNER_DIR}/.runner"; then',
    'cd "$1"',
    'exec ./config.sh "$@"',
    'if ! sudo test -f "${RUNNER_DIR}/.service"; then',
    'exec ./svc.sh install "$2"',
    'exec ./svc.sh start',
    "ALL=(ALL) NOPASSWD: ALL",
    'sudo -u "${RUNNER_USER}" -H sudo -n true',
]
for token in required:
    if token not in text:
        raise SystemExit(f"missing host-orchestrator service contract: {token}")

for forbidden in (
    '[[ ! -f "${RUNNER_DIR}/.runner" ]]',
    '[[ ! -f "${RUNNER_DIR}/.service" ]]',
    '(\n        cd "${RUNNER_DIR}"',
    '(\n    cd "${RUNNER_DIR}"',
    'sudo "${RUNNER_DIR}/svc.sh" install',
    'sudo "${RUNNER_DIR}/svc.sh" start',
):
    if forbidden in text:
        raise SystemExit(
            "runner-private directory must never require caller traversal: "
            + repr(forbidden)
        )

workflow = (Path(sys.argv[1]).parents[1] / ".github/workflows/host-workspace.yml").read_text()
for token in (
    "Refresh versioned host orchestration helpers",
    "sudo -n install -o root -g root -m 0755",
    "scripts/supralinux-vm-workspace-broker.sh",
    "/usr/local/libexec/supralinux-vm-workspace-broker",
):
    if token not in workflow:
        raise SystemExit(f"missing self-refresh workspace contract: {token}")

print("Host orchestrator private-root/service and unrestricted passwordless sudo contract: PASS")
PY
