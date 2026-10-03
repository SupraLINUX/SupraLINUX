#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
if [[ -z "${NODE}" ]]; then
    echo "Usage: $0 <node>" >&2
    exit 2
fi

RUNNER="${ROOT}/scripts/run-kde-tier1-package-batch2-preflight.sh"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-package-preflight/${NODE}"
OUT_DIR="${ROOT}/.work/kde-tier1-package-preflight/${NODE}/out"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
SBUILD_LOG="${EVIDENCE_DIR}/sbuild.log"
DAG_NODE="${EVIDENCE_DIR}/dag-node.txt"

"${RUNNER}" "${NODE}"

test -s "${RESULT_JSON}"
test -s "${SBUILD_LOG}"

fail_gate() {
    local stage="$1"
    local reason="$2"
    rm -f "${DAG_NODE}"
    python3 - "${RESULT_JSON}" "${stage}" "${reason}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["state"] = "FAIL"
data["exit_code"] = 1
data["stage"] = sys.argv[2]
data["validated_result"] = "FAIL"
data["gate_reason"] = sys.argv[3]
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
    echo "${reason}" >&2
    exit 1
}

if grep -Eq '^Lintian:[[:space:]]+fail[[:space:]]*$' "${SBUILD_LOG}"; then
    grep -E '^(E:|Lintian:)' "${SBUILD_LOG}" > "${EVIDENCE_DIR}/sbuild-lintian-failures.txt" || true
    fail_gate "sbuild-lintian" "sbuild reported a Lintian failure"
fi

mapfile -t DDEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
if (( ${#DDEBS[@]} > 0 )); then
    cp -a "${DDEBS[@]}" "${EVIDENCE_DIR}/"
    sha256sum "${DDEBS[@]}" > "${EVIDENCE_DIR}/debug-artifact-sha256.txt"
fi

mapfile -t DSCS < <(find "${EVIDENCE_DIR}" -maxdepth 1 -type f -name '*.dsc' -print | sort)
mapfile -t CHANGES < <(find "${EVIDENCE_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
if (( ${#DSCS[@]} != 1 || ${#CHANGES[@]} != 1 )); then
    fail_gate "lintian-inputs" "expected exactly one .dsc and one .changes for Lintian validation"
fi

if ! lintian --fail-on error "${DSCS[0]}" "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian-source-binary.log"; then
    fail_gate "lintian-source-binary" "source/binary Lintian error gate failed"
fi

python3 - "${RESULT_JSON}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["validated_result"] = "PASS"
data["lintian_gate"] = "sbuild-summary-plus-dsc-plus-changes"
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

echo "KDE Tier 1 node ${NODE}: validated PASS"
