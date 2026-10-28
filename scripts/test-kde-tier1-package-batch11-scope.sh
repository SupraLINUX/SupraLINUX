#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; SEL="${ROOT}/scripts/kde-tier1-package-batch11-needed.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"; git init -q; git config user.email test@example.invalid; git config user.name test
mkdir -p scripts manifests packages/kde/kuserfeedback packages/kde/prison .github/workflows
cp "${SEL}" scripts/; echo "# runner" > scripts/run-kde-tier1-package-batch11-preflight.sh; echo "# audit" > scripts/audit-kde-development-contract.py
cat > manifests/kde-tier1-package-campaign-batch11.json <<'JSON'
{"schema":2,"frameworks_series":"6.30.0","authority":"kde-upstream","provider_platform":"ubuntu-resolute","lane":"multi-surface-optional","selected_nodes":["kuserfeedback","prison"],"shared_predecessors":{"extra_cmake_modules":{"version":"x"},"packaging_trees":{"x":1}},"nodes":{"kuserfeedback":{"package_version":"1","source_sha256":"a","state":"prepared-pending-build"},"prison":{"package_version":"1","source_sha256":"b","state":"prepared-pending-build"}}}
JSON
echo a > packages/kde/kuserfeedback/a; echo b > packages/kde/prison/b; echo w > .github/workflows/kde-tier1-package-batch11.yml
git add .; git commit -qm base; BASE=$(git rev-parse HEAD)
python3 - <<'PY'
import json
p='manifests/kde-tier1-package-campaign-batch11.json'; d=json.load(open(p)); d['nodes']['kuserfeedback']['state']='FAIL'; d['nodes']['kuserfeedback']['last_failure_evidence']={'workflow_run':1}; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm result; R=$(git rev-parse HEAD)
if bash "${SEL}" kuserfeedback "${BASE}" "${R}"; then exit 1; fi
if bash "${SEL}" prison "${BASE}" "${R}"; then exit 1; fi
echo c >> packages/kde/kuserfeedback/a; git add .; git commit -qm kuf; K=$(git rev-parse HEAD)
bash "${SEL}" kuserfeedback "${R}" "${K}"
if bash "${SEL}" prison "${R}" "${K}"; then echo "KUserFeedback change rebuilt Prison" >&2; exit 1; fi
echo c >> packages/kde/prison/b; git add .; git commit -qm prison; P=$(git rev-parse HEAD)
bash "${SEL}" prison "${K}" "${P}"
if bash "${SEL}" kuserfeedback "${K}" "${P}"; then echo "Prison change rebuilt KUserFeedback" >&2; exit 1; fi
echo '#x' >> scripts/run-kde-tier1-package-batch11-preflight.sh; git add .; git commit -qm shared; S=$(git rev-parse HEAD)
bash "${SEL}" kuserfeedback "${P}" "${S}"; bash "${SEL}" prison "${P}" "${S}"
echo '#x' >> scripts/audit-kde-development-contract.py; git add .; git commit -qm audit; A=$(git rev-parse HEAD)
bash "${SEL}" kuserfeedback "${S}" "${A}"; bash "${SEL}" prison "${S}" "${A}"
echo "KDE Tier 1 Batch 11 scope selector: PASS"
