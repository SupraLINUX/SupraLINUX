#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEL="${ROOT}/scripts/kde-tier1-package-batch10-needed.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"; git init -q; git config user.email test@example.invalid; git config user.name test
mkdir -p scripts manifests packages/kde/kirigami packages/kde/kquickcharts .github/workflows docs
cp "${SEL}" scripts/
cat > manifests/kde-tier1-package-campaign-batch10.json <<'JSON'
{"schema":2,"frameworks_series":"6.30.0","authority":"kde-upstream","provider_platform":"ubuntu-resolute","lane":"qml-multisurface","selected_nodes":["kirigami","kquickcharts"],"shared_predecessors":{"extra_cmake_modules":{"version":"x"},"packaging_trees":{"x":1},"binary_contracts":{"x":1}},"nodes":{"kirigami":{"package_version":"1","source_sha256":"a","binary_contracts":[],"qml_contracts":[],"state":"prepared-pending-build"},"kquickcharts":{"package_version":"1","source_sha256":"b","binary_contracts":[],"qml_contracts":[],"state":"prepared-pending-build","package_validation_dependencies":[{"node":"kirigami"}]}}}
JSON
echo a > packages/kde/kirigami/a; echo b > packages/kde/kquickcharts/b; echo w > .github/workflows/kde-tier1-package-batch10.yml
git add .; git commit -qm base; BASE=$(git rev-parse HEAD)
python3 - <<'PY'
import json
p='manifests/kde-tier1-package-campaign-batch10.json'; d=json.load(open(p)); d['nodes']['kirigami']['state']='PASS'; d['nodes']['kirigami']['pass_evidence']={'artifact_id':1,'workflow_run':2}; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm result; R=$(git rev-parse HEAD)
if bash "$SEL" kirigami "$BASE" "$R"; then echo "result-only campaign change rebuilt kirigami" >&2; exit 1; fi
if bash "$SEL" kquickcharts "$BASE" "$R"; then echo "result-only campaign change rebuilt kquickcharts" >&2; exit 1; fi
echo c >> packages/kde/kquickcharts/b; git add .; git commit -qm qc; Q=$(git rev-parse HEAD)
if bash "$SEL" kirigami "$R" "$Q"; then echo "QuickCharts-only change rebuilt kirigami" >&2; exit 1; fi
bash "$SEL" kquickcharts "$R" "$Q"
echo c >> packages/kde/kirigami/a; git add .; git commit -qm kir; K=$(git rev-parse HEAD)
bash "$SEL" kirigami "$Q" "$K"; bash "$SEL" kquickcharts "$Q" "$K"
echo '#x' >> scripts/run-kde-tier1-package-batch10-preflight.sh; git add .; git commit -qm shared; S=$(git rev-parse HEAD)
bash "$SEL" kirigami "$K" "$S"; bash "$SEL" kquickcharts "$K" "$S"
echo "KDE Tier 1 Batch 10 scope selector: PASS"
