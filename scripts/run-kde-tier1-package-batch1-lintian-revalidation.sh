#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign.json"
BASE_RUNNER="${ROOT}/scripts/run-kde-tier1-package-preflight.sh"
NODE="${1:-}"

case "${NODE}" in
    kcodecs|kdbusaddons|threadweaver) ;;
    *)
        echo "Usage: $0 <kcodecs|kdbusaddons|threadweaver>" >&2
        exit 2
        ;;
esac

EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-package-preflight/${NODE}"
OUT_DIR="${ROOT}/.work/kde-tier1-package-preflight/${NODE}/out"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
SBUILD_LOG="${EVIDENCE_DIR}/sbuild.log"
DAG_NODE="${EVIDENCE_DIR}/dag-node.txt"
CAMPAIGN_BACKUP="$(mktemp)"
cp -a "${CAMPAIGN}" "${CAMPAIGN_BACKUP}"
CAMPAIGN_SHA256="$(sha256sum "${CAMPAIGN}" | awk '{print $1}')"

restore_campaign() {
    cp -a "${CAMPAIGN_BACKUP}" "${CAMPAIGN}"
    rm -f "${CAMPAIGN_BACKUP}"
}
trap restore_campaign EXIT

python3 - "${CAMPAIGN}" "${NODE}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
node_id = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
node = data["nodes"][node_id]
if node["state"] != "PASS" or node.get("last_result") != "PASS":
    raise SystemExit(f"Revalidation requires an existing PASS node, got {node['state']}/{node.get('last_result')}")
if not node.get("downstream_eligible"):
    raise SystemExit("Revalidation requires retained downstream-eligible PASS evidence")
node["state"] = "remediation-pending-build"
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

"${BASE_RUNNER}" "${NODE}"

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
data["revalidation"] = "source-plus-binary-lintian-v2"
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
    fail_gate "lintian-inputs" "expected exactly one .dsc and one .changes for Lintian revalidation"
fi

if ! lintian --fail-on error "${DSCS[0]}" "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian-source-binary.log"; then
    fail_gate "lintian-source-binary" "Batch 1 source/binary Lintian revalidation failed"
fi

printf '%s  manifests/kde-tier1-package-campaign.json\n' "${CAMPAIGN_SHA256}" > "${EVIDENCE_DIR}/canonical-campaign-sha256.txt"
cat > "${EVIDENCE_DIR}/revalidation.txt" <<EOF
node=${NODE}
canonical_state_before=PASS
package_revision=unchanged
revalidation=source-plus-binary-lintian-v2
canonical_campaign_sha256=${CAMPAIGN_SHA256}
EOF

python3 - "${RESULT_JSON}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["validated_result"] = "PASS"
data["revalidation"] = "source-plus-binary-lintian-v2"
data["lintian_gate"] = "sbuild-summary-plus-dsc-plus-changes"
data["canonical_package_state"] = "PASS-retained-pending-revalidation-recording"
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

echo "KDE Tier 1 Batch 1 node ${NODE}: source+binary Lintian revalidation PASS"
