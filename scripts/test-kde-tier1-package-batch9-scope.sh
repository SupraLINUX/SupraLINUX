#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"; git init -q; git config user.email test@supralinux.invalid; git config user.name SupraLINUX-Test
mkdir -p manifests scripts packages/kde/{kconfig,ki18n,sonnet}/debian .github/workflows docs
cp "${ROOT}/manifests/kde-tier1-package-campaign-batch9.json" manifests/
cp "${ROOT}/scripts/kde-tier1-package-batch9-needed.sh" scripts/
printf '# runner\n' > scripts/run-kde-tier1-package-batch9-preflight.sh
printf 'workflow\n' > .github/workflows/kde-tier1-package-batch9.yml
for n in kconfig ki18n sonnet; do printf 'baseline\n' > "packages/kde/${n}/debian/control"; done
git add .; git commit -qm baseline; BASE="$(git rev-parse HEAD)"
# Result/state-only changes do not rebuild any node.
python3 - <<'PY'
import json
from pathlib import Path
p=Path('manifests/kde-tier1-package-campaign-batch9.json'); d=json.loads(p.read_text())
d['state']='PASS'
for n in d['selected_nodes']:
 d['nodes'][n]['state']='PASS'; d['nodes'][n]['last_result']='PASS'; d['nodes'][n]['downstream_eligible']=True; d['nodes'][n]['pass_evidence']={'workflow_run':1}
p.write_text(json.dumps(d,indent=2)+'\n')
PY
git add manifests; git commit -qm state-only; STATE="$(git rev-parse HEAD)"
for n in kconfig ki18n sonnet; do if scripts/kde-tier1-package-batch9-needed.sh "$n" "$BASE" "$STATE"; then echo "$n state-only delta rebuilt" >&2; exit 1; else rc=$?; [[ "$rc" -eq 1 ]]; fi; done
# One node package change must rebuild only that node.
git reset --hard -q "$BASE"; printf 'changed\n' >> packages/kde/ki18n/debian/control; git add packages; git commit -qm ki18n-change; CH="$(git rev-parse HEAD)"
if scripts/kde-tier1-package-batch9-needed.sh kconfig "$BASE" "$CH"; then echo 'kconfig rebuilt for KI18n-only change' >&2; exit 1; else rc=$?; [[ "$rc" -eq 1 ]]; fi
scripts/kde-tier1-package-batch9-needed.sh ki18n "$BASE" "$CH"
if scripts/kde-tier1-package-batch9-needed.sh sonnet "$BASE" "$CH"; then echo 'sonnet rebuilt for KI18n-only change' >&2; exit 1; else rc=$?; [[ "$rc" -eq 1 ]]; fi
# Shared runner change rebuilds every node.
git reset --hard -q "$BASE"; printf '# change\n' >> scripts/run-kde-tier1-package-batch9-preflight.sh; git add scripts; git commit -qm runner; CH="$(git rev-parse HEAD)"
for n in kconfig ki18n sonnet; do scripts/kde-tier1-package-batch9-needed.sh "$n" "$BASE" "$CH"; done
# Documentation-only change rebuilds none.
git reset --hard -q "$BASE"; printf 'doc\n' > docs/x.md; git add docs; git commit -qm docs; CH="$(git rev-parse HEAD)"
for n in kconfig ki18n sonnet; do if scripts/kde-tier1-package-batch9-needed.sh "$n" "$BASE" "$CH"; then echo "$n rebuilt for docs-only" >&2; exit 1; else rc=$?; [[ "$rc" -eq 1 ]]; fi; done
echo 'KDE Tier 1 Batch 9 scope selector: PASS'
