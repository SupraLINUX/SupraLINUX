#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/docs" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier2-package-batch5-needed.sh" "${TMP}/scripts/"
echo '#!/usr/bin/env bash' > "${TMP}/scripts/run-kde-tier2-package-batch5.sh"
echo 'print("plan")' > "${TMP}/scripts/plan-kde-tier2-package-batch5.py"
echo 'print("inputs")' > "${TMP}/scripts/validate-kde-tier2-batch5-retained-inputs.py"
echo 'name: batch5' > "${TMP}/.github/workflows/kde-tier2-package-batch5.yml"
cat > "${TMP}/manifests/kde-tier2-package-campaign-batch5.json" <<'JSON'
{"schema":1,"batch":"tier2-batch-5","state":"prepared-pending-build","canonical_snapshot":"x","selected_nodes":["kmime"],"shared_predecessors":{"extra_cmake_modules":{"version":"1"}},"retained_predecessors":{"kcodecs":{"version":"1","artifact_id":1}},"nodes":{"kmime":{"package_version":"1","source_sha256":"a","materialization":{"dsc_sha256":"d"},"predecessors":["kcodecs"],"state":"prepared-pending-build","last_result":null,"downstream_eligible":false}}}
JSON
echo '{"schema":1}' > "${TMP}/manifests/kde-tier2-package-batch5-attempts.json"
for p in kde-tier2-package-contracts.json kde-frameworks-tier2.json kde-frameworks-tier2-dependencies.json kde-frameworks-tier1.json kde-dag.json; do echo '{"schema":1}' > "${TMP}/manifests/$p"; done
echo x > "${TMP}/docs/x.md"
chmod +x "${TMP}/scripts/"*.sh
git -C "${TMP}" init -q; git -C "${TMP}" config user.name test; git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .; git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc(){ local want="$1" before="$2" after="$3" label="$4" rc; set +e; "${TMP}/scripts/kde-tier2-package-batch5-needed.sh" "${before}" "${after}" >"${TMP}/${label}.log" 2>&1; rc=$?; set -e; [[ "${rc}" -eq "${want}" ]] || { cat "${TMP}/${label}.log" >&2; echo "${label}: expected ${want}, got ${rc}" >&2; exit 1; }; }
echo more >> "${TMP}/docs/x.md"; git -C "${TMP}" add .; git -C "${TMP}" commit -qm docs; DOCS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${BASE}" "${DOCS}" docs
python3 - "${TMP}/manifests/kde-tier2-package-batch5-attempts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["x"]=1; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .; git -C "${TMP}" commit -qm ledger; LEDGER="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${DOCS}" "${LEDGER}" ledger
python3 - "${TMP}/manifests/kde-tier2-package-campaign-batch5.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["kmime"]["state"]="PASS"; d["nodes"]["kmime"]["last_result"]="PASS"; d["state"]="PASS"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .; git -C "${TMP}" commit -qm evidence; E="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${LEDGER}" "${E}" evidence
echo '# maintenance' >> "${TMP}/scripts/run-kde-tier2-package-batch5.sh"; git -C "${TMP}" add .; git -C "${TMP}" commit -qm runner-pass; RP="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${E}" "${RP}" no_runnable_runner
python3 - "${TMP}/manifests/kde-tier2-package-campaign-batch5.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); n=d["nodes"]["kmime"]; n["state"]="remediation-pending-build"; n["package_version"]="2"; d["state"]="remediation-pending-build"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .; git -C "${TMP}" commit -qm remediation; R="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${RP}" "${R}" remediation
echo "KDE Tier 2 Batch 5 semantic scope: PASS"
