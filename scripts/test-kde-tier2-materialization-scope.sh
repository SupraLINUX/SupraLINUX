#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/docs" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier2-materialization-needed.sh" "${TMP}/scripts/"
echo '# materializer' > "${TMP}/scripts/materialize_kde_tier2_package.py"
echo '#!/usr/bin/env bash' > "${TMP}/scripts/run-kde-tier2-package-materialization.sh"
echo 'name: materialize' > "${TMP}/.github/workflows/kde-tier2-package-materialization.yml"
cat > "${TMP}/manifests/kde-tier2-package-contracts.json" <<'JSON'
{"schema":1,"state":"reference-capture-pass","selected_nodes":["kcrash"],"nodes":{"kcrash":{"source_sha256":"src","technical_references":{"debian":{"debian_tar_sha256":"tree"}}}},"materialization":{"status":"pending-ci","method":"kde-authority-source-plus-pinned-debian-tree"},"reference_evidence":{"workflow_run":1}}
JSON
echo docs > "${TMP}/docs/x.md"
chmod +x "${TMP}/scripts/"*.sh
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .; git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"

expect_rc(){ local want="$1" before="$2" after="$3" label="$4" rc; set +e; "${TMP}/scripts/kde-tier2-materialization-needed.sh" "${before}" "${after}" >"${TMP}/${label}.log" 2>&1; rc=$?; set -e; [[ "${rc}" -eq "${want}" ]] || { cat "${TMP}/${label}.log" >&2; exit 1; }; }

echo more >> "${TMP}/docs/x.md"; git -C "${TMP}" add .; git -C "${TMP}" commit -qm docs
DOCS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${BASE}" "${DOCS}" docs

python3 - "${TMP}/manifests/kde-tier2-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["materialization"]["status"]="PASS"; d["materialization"]["evidence"]={"artifact":1}; d["state"]="materialized"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .; git -C "${TMP}" commit -qm evidence
EVIDENCE="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${DOCS}" "${EVIDENCE}" evidence_only

python3 - "${TMP}/manifests/kde-tier2-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["kcrash"]["source_sha256"]="changed"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .; git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${EVIDENCE}" "${SEM}" semantic

echo "KDE Tier 2 materialization semantic scope: PASS"
