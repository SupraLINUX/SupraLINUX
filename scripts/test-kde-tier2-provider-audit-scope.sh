#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/docs" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier2-provider-audit-needed.sh" "${TMP}/scripts/"
printf '#!/usr/bin/env bash\nexit 0\n' > "${TMP}/scripts/run-kde-tier2-provider-audit.sh"
printf 'name: test\n' > "${TMP}/.github/workflows/kde-tier2-provider-audit.yml"
cat > "${TMP}/manifests/kde-frameworks-tier2-dependencies.json" <<'JSON'
{"provider_registry":{"inherited_from":"tier1"},"provider_audit":{"batch":"b1","status":"pending-ci","nodes":["kcrash"],"source_authority":"kde-upstream-v6.30.0","provider_platform":"ubuntu-resolute"},"nodes":{"kcrash":{"frameworks":{"required":["kcoreaddons"]},"qt":{"required":["Core"]},"external":{},"selected_linux_profile":{"BUILD_TESTING":true},"provider_audit":"pending-ci"}}}
JSON
cat > "${TMP}/manifests/kde-tier2-campaign-plan.json" <<'JSON'
{"next_provider_audit_batch":["kcrash"],"package_contract_ready":[],"canonical_snapshot":{"pass":1,"pending":14}}
JSON
echo base > "${TMP}/docs/x.md"
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

echo docs >> "${TMP}/docs/x.md"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm docs
DOCS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${BASE}" "${DOCS}" docs

python3 - "${TMP}/manifests/kde-frameworks-tier2-dependencies.json" "${TMP}/manifests/kde-tier2-campaign-plan.json" <<'PY'
import json,sys
dp,pp=sys.argv[1:]
d=json.load(open(dp)); d["provider_audit"]["status"]="PASS"; d["provider_audit"]["evidence"]={"result":"PASS","artifact_id":1}; d["nodes"]["kcrash"]["provider_audit"]="PASS"; open(dp,"w").write(json.dumps(d)+"\n")
p=json.load(open(pp)); p["next_provider_audit_batch"]=["knotifications"]; p["package_contract_ready"]=["kcrash"]; open(pp,"w").write(json.dumps(p)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence-promotion
EVIDENCE="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${DOCS}" "${EVIDENCE}" evidence_only

echo '# closed runner maintenance' >> "${TMP}/scripts/run-kde-tier2-provider-audit.sh"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm closed-runner
CLOSED_RUNNER="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${EVIDENCE}" "${CLOSED_RUNNER}" runner_after_pass

python3 - "${TMP}/manifests/kde-frameworks-tier2-dependencies.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["provider_audit"]={"batch":"b2","status":"pending-ci","nodes":["knotifications"],"source_authority":"kde-upstream-v6.30.0","provider_platform":"ubuntu-resolute"}
d["nodes"]["knotifications"]={"frameworks":{"required":["kconfig"]},"qt":{"required":["Gui"]},"external":{},"selected_linux_profile":{"BUILD_TESTING":True},"provider_audit":"pending-ci"}
open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm active-profile
ACTIVE="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${CLOSED_RUNNER}" "${ACTIVE}" active_profile

echo '# active runner maintenance' >> "${TMP}/scripts/run-kde-tier2-provider-audit.sh"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm active-runner
ACTIVE_RUNNER="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${ACTIVE}" "${ACTIVE_RUNNER}" active_runner

echo docs2 >> "${TMP}/docs/x.md"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm pending-docs-rescue
PENDING_DOCS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${ACTIVE_RUNNER}" "${PENDING_DOCS}" pending_rescue

echo "KDE Tier 2 provider-audit semantic scope: PASS"
