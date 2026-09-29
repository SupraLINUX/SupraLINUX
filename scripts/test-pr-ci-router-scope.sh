#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROUTER="${ROOT}/scripts/pr-ci-router-needed.sh"; BATCH10="${ROOT}/scripts/kde-tier1-package-batch10-needed.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"; git init -q; git config user.email test@example.invalid; git config user.name test
mkdir -p scripts manifests packages/kde/kirigami packages/kde/kquickcharts docs .github/workflows
cp "${ROUTER}" scripts/pr-ci-router-needed.sh; cp "${BATCH10}" scripts/kde-tier1-package-batch10-needed.sh
cat > manifests/kde-tier1-package-campaign-batch10.json <<'JSON'
{"schema":2,"frameworks_series":"6.30.0","authority":"kde-upstream","provider_platform":"ubuntu-resolute","lane":"qml-multisurface","selected_nodes":["kirigami","kquickcharts"],"shared_predecessors":{"extra_cmake_modules":{"version":"x"},"packaging_trees":{"x":1},"binary_contracts":{"x":1}},"nodes":{"kirigami":{"package_version":"1","source_sha256":"a","binary_contracts":[],"qml_contracts":[],"state":"prepared-pending-build"},"kquickcharts":{"package_version":"1","source_sha256":"b","binary_contracts":[],"qml_contracts":[],"state":"prepared-pending-build","package_validation_dependencies":[{"node":"kirigami"}]}}}
JSON
echo '{"attempts":{}}' > manifests/kde-tier1-package-batch10-attempts.json
cat > manifests/kde-frameworks-tier1.json <<'JSON'
{"schema":1,"authority":"kde-upstream","frameworks_series":"6.30.0","nodes":[{"id":"kirigami","source_sha256":"src","depends_on":["extra-cmake-modules"],"packaging":{"state":"pending"},"state":"pending"}]}
JSON
cat > manifests/kde-dag.json <<'JSON'
{"schema":1,"frameworks_series":"6.30.0","authority":"kde-upstream","states":["PASS","FAIL","BLOCKED","pending"],"nodes":{}}
JSON
cat > manifests/kde-tier1-global-discovery.json <<'JSON'
{"schema":1,"scope":"kde-frameworks-tier1-6.30","authority":"kde-upstream","provider_platform":"ubuntu-resolute","strategy":"dag-global-discovery","canonical_tier1_manifest":"manifests/kde-frameworks-tier1.json","policy":{"blocked_is_not_fail":true},"readiness_state_model":{"runnable":"x"},"promoted_snapshot":{"pass":25,"pending":4},"lanes":{"qml-multisurface":{"nodes":["kirigami"]}},"nodes":{"kirigami":{"readiness":"runnable"}},"next_actions":["x"]}
JSON
cat > manifests/kde-frameworks-tier1-packaging-tree-evidence.json <<'JSON'
{"schema":1,"authority":"technical-reference-only","role":"reference","selected_kde":"6.30.0","status":"PASS","evidence":{"artifact_id":1}}
JSON
echo '{"schema":1,"nodes":{"kirigami":{"qt":{"required":["Core"]}}}}' > manifests/kde-frameworks-tier1-dependencies.json
cat > manifests/kde-frameworks-tier2.json <<'JSON'
{"schema":1,"frameworks_series":"6.30.0","tier":2,"nodes":[{"id":"kcrash","source_sha256":"src","kde_framework_dependencies":{"required":["kcoreaddons"]},"state":"pending","planning":{"readiness":"package-lane-pending","provider_audit":"required-before-materialization","package_contract":"not-materialized"}}]}
JSON
cat > manifests/kde-frameworks-tier2-dependencies.json <<'JSON'
{"schema":1,"nodes":{"kcrash":{"frameworks":{"required":["kcoreaddons"]},"qt":{"required":["Core"]},"provider_audit":"pending-ci"}}}
JSON
echo 'name: Tier2 provider audit' > .github/workflows/kde-tier2-provider-audit.yml
echo '#!/usr/bin/env bash' > scripts/run-kde-tier2-provider-audit.sh
echo '#!/usr/bin/env bash' > scripts/kde-tier2-provider-audit-needed.sh
echo '{"schema":1}' > manifests/kde-tier2-campaign-plan.json
echo 'name: Repository policy' > .github/workflows/repository-policy.yml
echo 'print("compiler")' > scripts/compile_kde_tier2_campaign.py
echo a > packages/kde/kirigami/a; echo b > packages/kde/kquickcharts/b; echo doc > docs/x.md; echo 'print(1)' > scripts/validate_x.py
cat > manifests/kde-frameworks-tier3.json <<'JSON'
{"schema":1,"as_of":"2026-09-26","discovery_policy":{"phase":"diagnostic","dependencies":"x","provider_audit":"PASS","package_contracts":"PASS","package_builds":"tier3-round21-diagnostic-pending","remediation":"round21-pending"},"active_remediation":{"status":"round21-pending","next_gate":"g21","execution_authorized":false,"level1_execution_authorized":false,"candidate_package_versions":{"kio":"6.30.0-0supralinux8"}},"nodes":[{"id":"kio","packaging":{"package_version":"6.30.0-0supralinux8"}}]}
JSON
cat > manifests/kde-tier3-build-level1.json <<'JSON'
{"schema":1,"state":"attempt8-closed-mixed","next_gate":"g21","execution_authorized":false,"active_remediation":{"status":"round21-pending","next_gate":"g21","execution_authorized":false,"candidate_package_versions":{"kio":"6.30.0-0supralinux8"}}}
JSON
cat > manifests/kde-tier3-package-contracts.json <<'JSON'
{"schema":1,"active_remediation":{"status":"round21-pending","next_gate":"g21","execution_authorized":false,"level1_execution_authorized":false,"candidate_package_versions":{"kio":"6.30.0-0supralinux8"}}}
JSON
cat > manifests/kde-tier3-materialization.json <<'JSON'
{"schema":1,"state":"PASS","active_remediation":{"status":"round21-pending","next_gate":"g21","candidate_package_versions":{"kio":"6.30.0-0supralinux8"}}}
JSON
git add .; git commit -qm base; BASE=$(git rev-parse HEAD)
echo more >> docs/x.md; git add .; git commit -qm docs; D=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$BASE" "$D"; then echo "docs delta unexpectedly requested reusable CI" >&2; exit 1; fi
echo '# validator' >> scripts/validate_x.py; git add .; git commit -qm validator; V=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$D" "$V"; then echo "validator-only delta unexpectedly requested reusable CI" >&2; exit 1; fi
echo '# policy' >> .github/workflows/repository-policy.yml; git add .; git commit -qm policy; RP=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$V" "$RP"; then echo "repository-policy-only delta unexpectedly requested reusable CI" >&2; exit 1; fi
echo 'name: PR CI router' > .github/workflows/pr-ci-router.yml; git add .; git commit -qm router-self; RS=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$RP" "$RS"; then echo "router-self delta unexpectedly requested reusable CI" >&2; exit 1; fi
echo '# compiler' >> scripts/compile_kde_tier2_campaign.py; git add .; git commit -qm compiler; CP=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$RS" "$CP"; then echo "Tier2 compiler-only delta unexpectedly requested reusable CI" >&2; exit 1; fi
echo '{"schema":1,"generated":true}' > manifests/kde-tier2-campaign-plan.json; git add .; git commit -qm generated-plan; GP=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$CP" "$GP"; then echo "generated Tier2 plan unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier2.json'; d=json.load(open(p)); d['nodes'][0]['planning']['note']='planning-only'; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier2-planning; TP=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$GP" "$TP"; then echo "Tier2 planning-only delta unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier2.json'; d=json.load(open(p)); n=d['nodes'][0]; n['package_identity']={'source_package':'kf6-kcrash','package_version_candidate':'6.30.0-0supralinux1','status':'materialized'}; n['packaging']={'state':'pending','reason':'awaiting-build'}; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier2-materialized-identity; TMI=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$TP" "$TMI"; then echo "pending Tier2 materialized identity unexpectedly requested legacy reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier2-dependencies.json'; d=json.load(open(p)); d['nodes']['kcrash']['qt']['test']=['Test']; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier2-provider-profile; TDP=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$TMI" "$TDP"; then echo "unmaterialized Tier2 dependency profile unexpectedly requested reusable CI" >&2; exit 1; fi
echo '# audit workflow maintenance' >> .github/workflows/kde-tier2-provider-audit.yml
git add .; git commit -qm tier2-audit-workflow; TAW=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$TDP" "$TAW"; then echo "Tier2 provider-audit workflow unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier2.json'; d=json.load(open(p)); d['nodes'][0]['planning']['package_contract']='materialized'; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier2-contract; TCM=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$TAW" "$TCM"; then echo "Tier2 contract-state-only delta unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier2-dependencies.json'; d=json.load(open(p)); d['nodes']['kcrash']['qt']['test']=['Test','Widgets']; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier2-materialized-provider; TMP=$(git rev-parse HEAD)
bash scripts/pr-ci-router-needed.sh "$TCM" "$TMP"
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier2.json'; d=json.load(open(p)); d['nodes'][0]['source_sha256']='changed'; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier2-build-input; TBI=$(git rev-parse HEAD)
bash scripts/pr-ci-router-needed.sh "$TMP" "$TBI"
python3 - <<'PY'
import json
p='manifests/kde-tier1-package-batch10-attempts.json'; d=json.load(open(p)); d['attempts']['x']=1; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm ledger; L=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$TBI" "$L"; then echo "attempt-ledger delta unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-tier1-package-campaign-batch10.json'; d=json.load(open(p)); d['nodes']['kirigami']['state']='PASS'; d['nodes']['kirigami']['pass_evidence']={'artifact_id':1}; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm evidence; E=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$L" "$E"; then echo "result-only campaign delta unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier1.json'; d=json.load(open(p)); d['nodes'][0]['state']='PASS'; d['nodes'][0]['packaging']={'state':'PASS','evidence':[{'artifact_id':1}]}; open(p,'w').write(json.dumps(d))
p='manifests/kde-dag.json'; d=json.load(open(p)); d['nodes']['kirigami']={'state':'PASS','evidence':[{'artifact_id':1}]}; open(p,'w').write(json.dumps(d))
p='manifests/kde-tier1-global-discovery.json'; d=json.load(open(p)); d['promoted_snapshot']={'pass':26,'pending':3}; d['lanes']['qml-multisurface']['nodes']=[]; d['nodes'].pop('kirigami'); d['next_actions']=['next']; open(p,'w').write(json.dumps(d))
p='manifests/kde-frameworks-tier1-packaging-tree-evidence.json'; d=json.load(open(p)); d['evidence']={'artifact_id':2,'promotion':'PASS'}; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm canonical-promotion; C=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$E" "$C"; then echo "canonical state/evidence promotion unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier1.json'; d=json.load(open(p)); d['nodes'][0]['source_sha256']='changed'; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm canonical-input; CI=$(git rev-parse HEAD)
bash scripts/pr-ci-router-needed.sh "$C" "$CI"
echo c >> packages/kde/kquickcharts/b; git add .; git commit -qm package; P=$(git rev-parse HEAD); bash scripts/pr-ci-router-needed.sh "$CI" "$P"
python3 - <<'PY'
import json
p='manifests/kde-tier1-package-campaign-batch10.json'; d=json.load(open(p)); d['nodes']['kquickcharts']['package_version']='2'; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm input; I=$(git rev-parse HEAD); bash scripts/pr-ci-router-needed.sh "$P" "$I"
mkdir -p .github/workflows
echo 'name: batch2' > .github/workflows/kde-tier2-package-batch2.yml
echo '#!/usr/bin/env bash' > scripts/run-kde-tier2-package-batch2.sh
echo 'print("batch2")' > scripts/plan-kde-tier2-package-batch2.py
echo '#!/usr/bin/env bash' > scripts/kde-tier2-package-batch2-needed.sh
echo '{"schema":1}' > manifests/kde-tier2-package-campaign-batch2.json
echo '{"schema":1}' > manifests/kde-tier2-package-batch2-attempts.json
git add .; git commit -qm tier2-batch2-dedicated; B2=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$I" "$B2"; then echo "dedicated Tier2 Batch2 inputs unexpectedly requested legacy reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
for p in ('manifests/kde-frameworks-tier3.json','manifests/kde-tier3-build-level1.json','manifests/kde-tier3-package-contracts.json','manifests/kde-tier3-materialization.json'):
    d=json.load(open(p))
    if p.endswith('kde-frameworks-tier3.json'):
        d['discovery_policy']['package_builds']='tier3-round22-diagnostic-pending'; d['discovery_policy']['remediation']='round22-pending'
    if p.endswith('kde-tier3-build-level1.json'):
        d['next_gate']='g22'
    d['active_remediation']['status']='round22-pending'; d['active_remediation']['next_gate']='g22'
    open(p,'w').write(json.dumps(d))
PY
echo 'name: Round22 diagnostic' > .github/workflows/kde-tier3-kio-round22-diagnostic.yml
echo '#!/usr/bin/env bash' > scripts/run-kde-tier3-kio-round22-diagnostic.sh
echo '#!/usr/bin/env bash' > scripts/run-kde-tier3-kio-round22-hook.sh
echo '{"schema":1,"round":22}' > manifests/kde-tier3-kio-round22-diagnostic.json
git add .; git commit -qm tier3-diagnostic-lifecycle; TD=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$B2" "$TD"; then echo "Tier3 diagnostic lifecycle unexpectedly requested full reusable CI" >&2; exit 1; fi
echo 'name: Diagnostic infrastructure preflight' > .github/workflows/diagnostic-infrastructure-preflight.yml
echo '#!/usr/bin/env bash' > scripts/run-diagnostic-infrastructure-preflight.sh
echo '{"schema":1,"scope":"diagnostic-infrastructure-preflight"}' > manifests/diagnostic-infrastructure-preflight.json
git add .; git commit -qm diagnostic-infrastructure-preflight; DIP=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$TD" "$DIP"; then echo "diagnostic infrastructure preflight unexpectedly requested full reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-frameworks-tier3.json'; d=json.load(open(p)); d['nodes'][0]['packaging']['package_version']='6.30.0-0supralinux9'; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm tier3-package-semantic; TPS=$(git rev-parse HEAD)
bash scripts/pr-ci-router-needed.sh "$DIP" "$TPS"
echo "PR CI semantic evidence router: PASS"
