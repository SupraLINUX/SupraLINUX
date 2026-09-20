#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/docs" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier2-provider-audit-needed.sh" "${TMP}/scripts/"
printf '#!/usr/bin/env bash\nexit 0\n' > "${TMP}/scripts/run-kde-tier2-provider-audit.sh"
printf 'name: test\n' > "${TMP}/.github/workflows/kde-tier2-provider-audit.yml"
printf '{"provider_audit":{"nodes":["kcrash"]}}\n' > "${TMP}/manifests/kde-frameworks-tier2-dependencies.json"
printf '{"next_provider_audit_batch":["kcrash"],"canonical_snapshot":{"pass":1,"pending":14}}\n' > "${TMP}/manifests/kde-tier2-campaign-plan.json"
printf 'base\n' > "${TMP}/docs/x.md"
chmod +x "${TMP}/scripts/"*.sh
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .
git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"

expect_rc() {
    local expected="$1" before="$2" after="$3" label="$4" rc
    set +e
    "${TMP}/scripts/kde-tier2-provider-audit-needed.sh" "${before}" "${after}" >"${TMP}/${label}.log" 2>&1
    rc=$?
    set -e
    if [[ "${rc}" -ne "${expected}" ]]; then
        cat "${TMP}/${label}.log" >&2
        echo "${label}: expected ${expected}, got ${rc}" >&2
        exit 1
    fi
}

echo more >> "${TMP}/docs/x.md"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm docs
DOCS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${BASE}" "${DOCS}" docs

python3 - "${TMP}/manifests/kde-tier2-campaign-plan.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["canonical_snapshot"]["pending"]=13; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm plan-evidence
PLAN_EVIDENCE="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${DOCS}" "${PLAN_EVIDENCE}" plan_evidence

python3 - "${TMP}/manifests/kde-tier2-campaign-plan.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["next_provider_audit_batch"]=["knotifications"]; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm batch
BATCH="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${PLAN_EVIDENCE}" "${BATCH}" batch

python3 - "${TMP}/manifests/kde-frameworks-tier2-dependencies.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["provider_audit"]["nodes"]=["knotifications"]; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm deps
DEPS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${BATCH}" "${DEPS}" deps

echo '# change' >> "${TMP}/scripts/run-kde-tier2-provider-audit.sh"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm runner
RUNNER="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${DEPS}" "${RUNNER}" runner
echo "KDE Tier 2 provider-audit semantic scope: PASS"
