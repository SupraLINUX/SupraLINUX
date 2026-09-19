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
echo a > packages/kde/kirigami/a; echo b > packages/kde/kquickcharts/b; echo doc > docs/x.md; echo 'print(1)' > scripts/validate_x.py
git add .; git commit -qm base; BASE=$(git rev-parse HEAD)
echo more >> docs/x.md; git add .; git commit -qm docs; D=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$BASE" "$D"; then echo "docs delta unexpectedly requested reusable CI" >&2; exit 1; fi
echo '# validator' >> scripts/validate_x.py; git add .; git commit -qm validator; V=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$D" "$V"; then echo "validator-only delta unexpectedly requested reusable CI" >&2; exit 1; fi
python3 - <<'PY'
import json
p='manifests/kde-tier1-package-batch10-attempts.json'; d=json.load(open(p)); d['attempts']['x']=1; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm ledger; L=$(git rev-parse HEAD)
if bash scripts/pr-ci-router-needed.sh "$V" "$L"; then echo "attempt-ledger delta unexpectedly requested reusable CI" >&2; exit 1; fi
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
echo "PR CI semantic evidence router: PASS"
