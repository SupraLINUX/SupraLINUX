#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"
git init -q
git config user.email test@supralinux.invalid
git config user.name SupraLINUX-Test
mkdir -p manifests scripts packages/kde/kguiaddons/debian .github/workflows
cp "${ROOT}/manifests/kde-tier1-package-campaign-batch8.json" manifests/
cp "${ROOT}/scripts/kde-tier1-package-batch8-needed.sh" scripts/
printf 'baseline\n' > packages/kde/kguiaddons/debian/control
printf 'baseline\n' > .github/workflows/kde-tier1-package-batch8.yml
printf '#!/usr/bin/env bash\n' > scripts/run-kde-tier1-package-batch8-preflight.sh
git add .
git commit -qm baseline
BASE="$(git rev-parse HEAD)"

# Planning-only state changes must not rebuild.
python3 - <<'PY'
import json
from pathlib import Path
p=Path('manifests/kde-tier1-package-campaign-batch8.json'); d=json.loads(p.read_text())
d['state']='PASS'; d['nodes']['kguiaddons']['state']='PASS'; d['nodes']['kguiaddons']['last_result']='PASS'; d['nodes']['kguiaddons']['downstream_eligible']=True
d['canonical_snapshot']['state']='planning-only-test'; p.write_text(json.dumps(d,indent=2)+'\n')
PY
git add manifests; git commit -qm planning-only
PLANNING="$(git rev-parse HEAD)"
if scripts/kde-tier1-package-batch8-needed.sh "${BASE}" "${PLANNING}"; then
  echo "planning-only delta incorrectly triggered Batch 8" >&2; exit 1
else
  rc=$?; [[ "${rc}" -eq 1 ]] || exit "${rc}"
fi

# A real node contract change must rebuild.
git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('manifests/kde-tier1-package-campaign-batch8.json'); d=json.loads(p.read_text())
d['nodes']['kguiaddons']['source_sha256']='0'*64; p.write_text(json.dumps(d,indent=2)+'\n')
PY
git add manifests; git commit -qm contract-change
scripts/kde-tier1-package-batch8-needed.sh "${BASE}" "$(git rev-parse HEAD)"

# Package metadata changes must rebuild.
git reset --hard -q "${BASE}"; printf 'changed\n' >> packages/kde/kguiaddons/debian/control
git add packages; git commit -qm package-change
scripts/kde-tier1-package-batch8-needed.sh "${BASE}" "$(git rev-parse HEAD)"

# Runner changes must rebuild.
git reset --hard -q "${BASE}"; printf '# changed\n' >> scripts/run-kde-tier1-package-batch8-preflight.sh
git add scripts; git commit -qm runner-change
scripts/kde-tier1-package-batch8-needed.sh "${BASE}" "$(git rev-parse HEAD)"

# Unrelated documentation must not rebuild at lane scope either.
git reset --hard -q "${BASE}"; mkdir -p docs; printf 'note\n' > docs/note.md
git add docs; git commit -qm docs-only
if scripts/kde-tier1-package-batch8-needed.sh "${BASE}" "$(git rev-parse HEAD)"; then
  echo "documentation-only delta incorrectly triggered Batch 8" >&2; exit 1
else
  rc=$?; [[ "${rc}" -eq 1 ]] || exit "${rc}"
fi

echo "KDE Tier 1 Batch 8 scope selector: PASS"
